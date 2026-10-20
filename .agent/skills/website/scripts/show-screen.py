#!/usr/bin/env python3
"""
ПОКАЗ экрана/сайта автору = печать КЛИКАБЕЛЬНОЙ VS Code-ссылки в чат (НЕ `open` в браузер).

Зачем (автор): автор работает в окне VS Code и хочет тыкнуть ссылку прямо в
чате, чтобы рендер открылся В ОКНЕ VS Code, а не во всплывающем системном браузере.
Проверено: единственный гарантированно кликабельный из чата Claude Code механизм —
markdown-ссылка на ФАЙЛ (`[текст](путь)`), она открывает файл в окне VS Code. Live
Preview (embedded) по открытию HTML предлагает отрендерить встроенно — без браузера.
(`command:`/`vscode://`/localhost-опенеры в песочнице чата не срабатывают — отсюда файл-ссылка.)

Контракт: показ экрана/сайта идёт ЧЕРЕЗ этот скрипт (Bash-вызов), а не `open`. Скрипт
сам гейтит (status/score/approvals для экрана; все-done + self-review для сайта) и
печатает готовую строку-ссылку, которую агент вставляет в чат. Параллельно хук
`website-review-gate.sh` (PreToolUse) гейтит и сам вызов этого скрипта (полная проверка
референсов/цепочки фаз) — обойти нельзя. Это сохраняет анти-саботаж-гейт при смене
носителя показа `open`→ссылка.

Использование:
    python3 show-screen.py <render-file>            # screen-<name>.html | index.html
    python3 show-screen.py <render-file> --root DIR  # корень для относительного пути (по умолч. $HOME)

Safe-by-design: не прошёл лёгкий гейт → stderr + exit 1 (ссылку НЕ печатает). Печатает
ссылку только когда показывать можно.
"""
import json
import os
import re
import sys

HOME = os.path.expanduser("~")


def _port_for(proj_dir):
    import hashlib
    h = int(hashlib.sha1(proj_dir.encode("utf-8")).hexdigest(), 16)
    return 8900 + (h % 80)  # детерминированный порт на проект, диапазон 8900-8979


def _is_serving(port, basename):
    import urllib.request
    from urllib.parse import quote
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/{quote(basename)}", timeout=0.7
        ) as r:
            return getattr(r, "status", r.getcode()) == 200
    except Exception:
        return False


def _port_free(port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def serve_url(proj_dir, basename):
    """Поднять (или переиспользовать) http.server из ПАПКИ ПРОЕКТА на чистом порту и
    вернуть КЛИКАБЕЛЬНЫЙ localhost-URL (автор: кликается только localhost-URL,
    не file-ссылка). Сервер из папки проекта на своём порту — не переиспользуем чужой."""
    import subprocess
    from urllib.parse import quote
    import time
    base_port = _port_for(proj_dir)
    cands = [base_port + i for i in range(6)]
    for c in cands:
        if _is_serving(c, basename):
            return f"http://localhost:{c}/{quote(basename)}"
    for c in cands:
        if _port_free(c):
            popen_kwargs = dict(
                cwd=proj_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if os.name != "nt":
                popen_kwargs["start_new_session"] = True
            subprocess.Popen(
                [sys.executable, "-m", "http.server", str(c), "--bind", "127.0.0.1"],
                **popen_kwargs,
            )
            for _ in range(12):
                time.sleep(0.3)
                if _is_serving(c, basename):
                    return f"http://localhost:{c}/{quote(basename)}"
            return f"http://localhost:{c}/{quote(basename)}"
    return None


def die(msg):
    sys.stderr.write("🛑 показ заблокирован: " + msg + "\n")
    sys.exit(1)


def rel_link_path(abs_path, root):
    """Путь для markdown-ссылки: относительный от root (workspace), если файл под root —
    так ссылка кликается в чате VS Code. Иначе абсолютный (фолбэк)."""
    try:
        if os.path.commonpath([abs_path, root]) == root:
            return os.path.relpath(abs_path, root)
    except ValueError:
        pass
    return abs_path


def show_screen(abs_path, proj_dir, name, root):
    state = os.path.join(proj_dir, ".website-state.json")
    if not os.path.exists(state):
        die(f"нет блокнота {state} (карта экранов пишется в конце фазы 3a).")
    try:
        st = json.load(open(state, encoding="utf-8"))
    except Exception as e:
        die(f"{state} нечитаем ({e}).")
    match = [s for s in st.get("screens", []) if str(s.get("name", "")).lower() == name]
    if not match:
        die(f"экрана «{name}» нет в screens[] блокнота — сначала карта экранов (фаза 3a).")
    s = match[0]
    if s.get("status") not in ("review", "done"):
        die(f"экран «{name}» не прошёл review (status={s.get('status')}). Дотяни 3 слоя ≥9.")
    if int(s.get("score") or 0) < 9:
        die(f"балл экрана «{name}» {s.get('score')}/10 < 9. Чини по находкам критика.")
    missing = {"concept", "copy", "design"} - set(s.get("approvals", []))
    if missing:
        die(f"экран «{name}» идёт мимо согласований: не согласовано {sorted(missing)} "
            "(концепция→копи→дизайн ✋ ДО сборки).")
    score = s.get("score")
    url = serve_url(proj_dir, os.path.basename(abs_path))
    if not url:
        die("не поднять локальный сервер (нет свободного порта 8900-8979).")
    print(f"▶ Экран «{name}» (ревью {score}/10) — кликабельный URL:")
    print(f"   {url}")


def show_site(abs_path, proj_dir, root):
    index = abs_path if abs_path.lower().endswith((".html", ".htm")) else os.path.join(proj_dir, "index.html")
    if not os.path.exists(index):
        die(f"нет собранного index.html ({index}).")
    state = os.path.join(proj_dir, ".website-state.json")
    marker = os.path.join(proj_dir, ".self-review.json")
    if not os.path.exists(state):
        die("показ сайта без .website-state.json (конвейер фаз не пройден).")
    try:
        st = json.load(open(state, encoding="utf-8"))
    except Exception as e:
        die(f"{state} нечитаем ({e}).")
    not_done = [str(x.get("name", "?")) for x in st.get("screens", []) if x.get("status") != "done"]
    if not_done:
        die(f"сайт с недоделанными экранами: {', '.join(not_done)} (СТАДИЯ B не закрыта).")
    if not os.path.exists(marker):
        die("нет .self-review.json (Фаза 09 self-review не пройдена).")
    # Балл из ОСЕЙ criteria/lenses (v2.0) — согласовано с website-review-gate; плоский
    # score_min отвергаем (его вписывали не прогнав критика).
    try:
        data = json.load(open(marker, encoding="utf-8"))
    except Exception:
        die(f"{marker} нечитаем — перепрогони Фазу 09.")
    axes = data.get("criteria") or data.get("lenses") or {}
    axes = {k: v for k, v in axes.items() if isinstance(v, (int, float))} if isinstance(axes, dict) else {}
    if len(axes) < 6:
        die("маркер без разложенных ОСЕЙ критика (criteria/lenses ≥6) — плоский score_min "
            "больше не принимается. Прогони Слой 3, запиши баллы по осям.")
    score = int(min(axes.values()))
    if score < 9:
        die(f"self-review min по осям {score}/10 < 9 — чини до ≥9 на каждой оси, потом показ.")
    url = serve_url(proj_dir, os.path.basename(index))
    if not url:
        die("не поднять локальный сервер (нет свободного порта 8900-8979).")
    print(f"▶ Собранный сайт (self-review {score}/10) — кликабельный URL:")
    print(f"   {url}")


def main():
    args = [a for a in sys.argv[1:] if a != "--root"]
    root = HOME
    if "--root" in sys.argv:
        i = sys.argv.index("--root")
        if i + 1 < len(sys.argv):
            root = os.path.abspath(os.path.expanduser(sys.argv[i + 1]))
            args = [a for a in args if a != sys.argv[i + 1]]
    if not args:
        die("укажи файл рендера: show-screen.py <screen-<name>.html | index.html>")
    abs_path = os.path.abspath(os.path.expanduser(args[0]))
    proj_dir = os.path.dirname(abs_path)
    base = os.path.basename(abs_path).lower()
    m = re.match(r"screen-(.+)\.(html?|png|jpe?g)$", base)
    if m:
        show_screen(abs_path, proj_dir, m.group(1), root)
    elif base in ("index.html", "index.htm"):
        show_site(abs_path, proj_dir, root)
    else:
        die(f"не распознал тип показа по имени «{base}» (ожидал screen-<name>.html или index.html).")


if __name__ == "__main__":
    main()