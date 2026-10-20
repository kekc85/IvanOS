#!/usr/bin/env python3
"""Снятие метрик постов канала «автор Официальный» из Telegram Web (CDP :9222).

Читает видимые посты открытого канала (просмотры + реакции), печатает markdown-таблицу
для журнала `references/post-performance-log.md` и пишет снапшот в
`references/.metrics-snapshots/YYYY-MM-DD.json` (история для сравнения динамики).
Каталог снапшотов создаётся скриптом при первом прогоне (`os.makedirs(exist_ok=True)`)
и лежит в `.gitignore` - ученикам история метрик автора не раздаётся.

READ-ONLY: сам журнал не редактирует - сопоставление строк делает агент
(строки старше 48ч = зрелые, обновить охват/реакции; новые посты = добавить).

Требования: Chrome с CDP на 127.0.0.1:9222, вкладка web.telegram.org/k/ под
burner-аккаунтом, вступившим в канал (см. memory reference_tg_public_er_parsing_method).
Если канал не открыт во вкладке - скрипт пытается открыть его кликом по списку чатов.

Запуск: python3 tg-metrics-refresh.py [--json]
"""
import websocket  # pip: websocket-client
import json, urllib.request, time, sys, os
from datetime import datetime, timezone

CDP = "http://127.0.0.1:9222"
CHANNEL_MARK = "Официальный"
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", ".metrics-snapshots")

def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

def find_tab():
    try:
        tabs = json.load(urllib.request.urlopen(f"{CDP}/json/list", timeout=8))
    except Exception as e:
        fail(f"CDP :9222 недоступен ({e}). Рендер-браузер закрыт - открой Chrome с --remote-debugging-port=9222")
    return next((t for t in tabs if t.get("url", "").startswith("https://web.telegram.org/k") and t.get("type") == "page"), None)

def connect():
    tab = find_tab()
    if not tab:
        # вкладку закрыли  - откроем сами, сессия живёт в профиле
        req = urllib.request.Request(f"{CDP}/json/new?https://web.telegram.org/k/", method="PUT")
        urllib.request.urlopen(req, timeout=10)
        time.sleep(12)
        tab = find_tab()
        if not tab:
            fail("вкладка web.telegram.org/k не открылась даже после PUT /json/new")
    return websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=40)

MID = [0]
def send(ws, method, params):
    MID[0] += 1
    ws.send(json.dumps({"id": MID[0], "method": method, "params": params}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == MID[0]:
            return r.get("result", {})

def ev(ws, expr):
    res = send(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    if "exceptionDetails" in res:
        raise RuntimeError(str(res["exceptionDetails"])[:300])
    return res.get("result", {}).get("value")

# критерий «нужный канал открыт»: в топбаре активного чата есть маркер канала,
# НЕ просто наличие .post-views (аккаунт состоит и в других каналах - «Гормоны & Стресс»)
IS_OPEN = f"""(() => {{
  const title = document.querySelector('.chat.active .peer-title, .topbar .peer-title');
  return !!(title && title.innerText.includes('{CHANNEL_MARK}')
            && document.querySelectorAll('.post-views').length > 0);
}})()"""

def ensure_channel_open(ws):
    if ev(ws, IS_OPEN):
        return True
    box = ev(ws, f"""(() => {{
      const rows = [...document.querySelectorAll('.chatlist-chat')];
      const t = rows.find(r => (r.querySelector('.user-title, .peer-title')?.innerText || '').includes('{CHANNEL_MARK}'));
      if (!t) return null;
      const b = t.getBoundingClientRect();
      return b.width > 0 ? JSON.stringify({{x: b.x + b.width/2, y: b.y + b.height/2}}) : null;
    }})()""")
    if not box:
        fail("канал не открыт и строка в списке чатов не кликабельна - открой канал во вкладке руками")
    b = json.loads(box)
    for typ in ["mousePressed", "mouseReleased"]:
        send(ws, "Input.dispatchMouseEvent", {"type": typ, "x": b["x"], "y": b["y"], "button": "left", "clickCount": 1})
    time.sleep(5)
    return bool(ev(ws, IS_OPEN))

HARVEST = """(() => {
  const out = [];
  // ТОЛЬКО активный контейнер канала: в document живут бабблы ранее открытых чатов,
  // включая ДРУГИЕ каналы с .post-views - глобальный обход смешал бы каналы
  const scs = [...document.querySelectorAll('.scrollable')].filter(s => s.querySelector('.post-views'));
  const root = scs[scs.length-1];
  if (!root) return '[]';
  for (const b of root.querySelectorAll('.bubble[data-mid]')) {
    const pv = b.querySelector('.post-views');
    const ts = b.dataset.timestamp ? parseInt(b.dataset.timestamp) : 0;
    if (!pv || !ts) continue;
    const msg = b.querySelector('.message');
    let text = '';
    if (msg) {
      const clone = msg.cloneNode(true);
      clone.querySelectorAll('.time, .post-views, reactions-element, .web').forEach(x => x.remove());
      text = clone.innerText || '';
    }
    const reactions = [...b.querySelectorAll('reaction-element')].map(r => {
      const c = r.querySelector('.reaction-counter');
      if (c) return parseInt(c.textContent.replace(/[^0-9]/g, '')) || 1;
      const m = (r.textContent || '').match(/(\\d+)\\s*$/);
      return m ? parseInt(m[1]) : 1;
    });
    out.push({mid: b.dataset.mid, ts, text: text.slice(0, 300),
              views: pv.textContent || null, reactions_total: reactions.reduce((a,x)=>a+x,0)});
  }
  return JSON.stringify(out);
})()"""

def num(s):
    if not s: return None
    s = s.strip().replace(",", "")
    if s.endswith("K"): return int(float(s[:-1]) * 1000)
    if s.endswith("M"): return int(float(s[:-1]) * 1000000)
    try: return int(float(s))
    except ValueError: return None

def main():
    ws = connect()
    if not ensure_channel_open(ws):
        fail("не удалось открыть канал")
    posts = {}
    for _ in range(12):  # немного проскроллить вверх, чтобы захватить ~2 недели
        for p in json.loads(ev(ws, HARVEST)):
            posts[p["mid"]] = p
        ev(ws, """(() => {
          const scs = [...document.querySelectorAll('.scrollable')].filter(s => s.querySelector('.post-views'));
          const sc = scs[scs.length-1];
          if (sc) sc.scrollTop = Math.max(0, sc.scrollTop - 2200);
        })()""")
        time.sleep(1.2)
    ws.close()

    rows = sorted(posts.values(), key=lambda p: p["ts"])
    now = datetime.now(timezone.utc)
    os.makedirs(SNAP_DIR, exist_ok=True)
    snap_path = os.path.join(SNAP_DIR, now.strftime("%Y-%m-%d") + ".json")
    with open(snap_path, "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    print(f"# Снапшот {now:%Y-%m-%d %H:%M} UTC - {len(rows)} постов (сохранён: {snap_path})\n")
    print("| Дата поста | Возраст | Просмотры | Реакции | ERV | Первая строка |")
    print("|---|---|---|---|---|---|")
    for p in rows:
        d = datetime.fromtimestamp(p["ts"], tz=timezone.utc)
        age_h = int((now - d).total_seconds() // 3600)
        v = num(p["views"])
        erv = f"{p['reactions_total']/v*100:.2f}%" if v else "-"
        mature = "" if age_h >= 48 else " ⏳<48ч"
        first = (p["text"] or "").split("\n")[0][:50]
        print(f"| {d:%Y-%m-%d %H:%M} | {age_h}ч{mature} | {v} | {p['reactions_total']} | {erv} | {first} |")

if __name__ == "__main__":
    main()