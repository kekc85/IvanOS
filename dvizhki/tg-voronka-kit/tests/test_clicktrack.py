"""Тесты клик-трекинга: обёртка URL → редирект → клик → продвижение воронки.
Запуск: .venv/bin/python -m tests.test_clicktrack
"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import DB
from app.runtime import Runtime
from app.redirect import _allowed, PREVIEW_UA
from app.config import REDIRECT_BASE
from engine.interpreter import Event
from engine.model import tg_url
from engine.model import deeplink as _dl

_p = _f = 0
def check(name, cond):
    global _p, _f
    if cond: _p += 1
    else: _f += 1; print(f"  FAIL: {name}")

db = DB(tempfile.mktemp(suffix=".sqlite"))
rt = Runtime(db)
for _i in rt.interp.values(): _i.registered_by_click = True  # тест клик-прокси режима (не дефолт с 09.07)
key = "DEMO"
uid = 555

# --- 1. обёртка URL гайда → редирект per-user ---
gift = rt.funnels[key].nodes["B0"].url_button.url
wrapped = rt.wrap_button_url(uid, key, "B0", gift)
check("гайд-URL обёрнут в редирект", wrapped.startswith(REDIRECT_BASE + "/r/"))
ruuid = wrapped.rsplit("/", 1)[-1]
link = db.redirect(ruuid)
check("редирект-строка создана с user_id+target", link and link["user_id"] == uid and link["target_url"] == gift)
check("kind=article для гайда", link["kind"] == "article")

# --- 2. t.me (канал) НЕ оборачивается ---
tme = tg_url("+INVITE")
check("t.me остаётся прямой (не обёрнут)", rt.wrap_button_url(uid, key, "D7", tme) == tme)

# --- 3. событие → kind=event ---
ws = _dl("KEY")
w2 = rt.wrap_button_url(uid, key, "C1", ws)
check("событие обёрнут kind=event", db.redirect(w2.rsplit("/",1)[-1])["kind"] == "event")

# --- 4. дедуп клика ---
check("первый клик засчитан", db.record_click(ruuid, uid) is True)
check("повторный клик отсеян", db.record_click(ruuid, uid) is False)

# --- 5. клик по гайду двигает воронку до TECH→C1 ---
# заводим юзера в воронку сперва (enter+button), потом эмулируем клик через очередь
uid2 = 556
rt.apply(uid2, key, Event("enter", rt.now()))
rt.apply(uid2, key, Event("button", rt.now(), payload="Забрать"))
w = rt.wrap_button_url(uid2, key, "B0", gift)
db.record_click(w.rsplit("/",1)[-1], uid2)
db.enqueue_click(uid2, key, gift)
pend = db.pending_clicks()
check("клик попал в очередь", any(c["user_id"]==uid2 for c in pend))
# бот обрабатывает очередь → Event click → TECH → планирует C1
for c in db.pending_clicks():
    rt.apply(c["user_id"], c["funnel_key"], Event("click", rt.now(), payload=c["target_url"]))
    db.mark_click_done(c["id"])
jobs=[j for j in db.due_jobs(time.time()+10**9) if j["user_id"]==uid2]
check("после клика гайда запланирован C1", any(j["node"]=="C1" for j in jobs))
check("очередь кликов опустела", db.pending_clicks()==[])

# --- 6. клик по событие = registered + стоп ---
uid3 = 557
rt.apply(uid3, key, Event("enter", rt.now()))
rt.apply(uid3, key, Event("button", rt.now(), payload="Забрать"))
rt.apply(uid3, key, Event("click", rt.now(), payload=gift))  # дошёл до C-цепочки
rt.apply(uid3, key, Event("click", rt.now(), payload=_dl("KEY")))
check("клик событие ставит registered", "registered" in db.tags(uid3))
check("после событие-клика дожим погашен", [j for j in db.due_jobs(time.time()+10**9) if j["user_id"]==uid3]==[])

# --- 7. allowlist доменов (анти-open-redirect) ---
check("allow author.ru", _allowed("https://author.ru/guide-demo/"))
check("allow t.me", _allowed(tg_url("+abc")))
check("block чужой домен", not _allowed("https://evil-phish.com/x"))
check("block поддомен-обманка", not _allowed("https://author.ru.evil.com/x"))

# --- 8. детект превью-бота ---
check("TelegramBot UA распознан как превью", any(s in "telegrambot (like twitterbot)" for s in PREVIEW_UA))
check("обычный браузер не превью", not any(s in "mozilla/5.0 (iphone) safari" for s in PREVIEW_UA))

print(f"\nИтог клик-трекинг: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
