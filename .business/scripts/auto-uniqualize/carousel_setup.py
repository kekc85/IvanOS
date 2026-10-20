#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЕДИНЫЙ онбординг машины каруселей для ученика. Кроссплатформенный (Win + Mac + Linux).
Ставит зависимости, даёт выбрать браузер и ветку граба, создаёт config на Рабочем столе,
поднимает браузер для входа в ChatGPT (кастомка автора уже вписана). Замена Mac-only setup.sh.

Запуск (ученик): python3 carousel_setup.py
Флаги для авто-теста (без вопросов): --browser Chrome --grab apify --no-launch --no-pip
"""
import argparse, json, os, platform, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "launcher.py"
ACCOUNT = Path(os.path.expanduser("~/.claude/skills/_shared/bin/account.py"))
TEMPLATE = HERE / "config.json.template"
CONFIG = HERE / "config.json"
PIP_DEPS = ["playwright", "requests", "python-dotenv", "Pillow", "opencv-python-headless"]

def say(m): print(m, flush=True)

def ensure_deps():
    say("[1/5] Ставлю зависимости (playwright, requests, dotenv, Pillow, opencv)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", *PIP_DEPS])

def pick_browser(preset=None):
    say("[2/5] Ищу браузеры на твоём компьютере...")
    out = subprocess.run([sys.executable, str(LAUNCHER), "--list"],
                         capture_output=True, text=True).stdout.strip()
    found = json.loads(out or "[]")
    if not found:
        say("  Не нашёл ни одного браузера. Поставь Chrome (google.com/chrome) и запусти меня снова.")
        sys.exit(2)
    if preset:
        for b in found:
            if b["name"].lower() == preset.lower():
                say(f"  Браузер: {b['name']}")
                return b["name"]
    if len(found) == 1:
        say(f"  Нашёл один браузер: {found[0]['name']} - беру его")
        return found[0]["name"]
    say("  Нашёл несколько браузеров, выбери в каком работать:")
    for i, b in enumerate(found, 1):
        say(f"    {i}) {b['name']}")
    while True:
        c = input("  Номер: ").strip()
        if c.isdigit() and 1 <= int(c) <= len(found):
            return found[int(c) - 1]["name"]

def pick_grab(preset=None):
    say("[3/5] Как забирать чужие карусели для уникализации?")
    say("    1) Через свой Instagram-аккаунт (cookies) - быстро, но парсинг под своим аккаунтом")
    say("    2) Через Apify (свой бесплатный токен) - аккаунт вне риска, рекомендуется")
    choice = preset or ""
    if choice not in ("cookies", "apify"):
        while True:
            c = input("  Номер (1/2): ").strip()
            if c == "1": choice = "cookies"; break
            if c == "2": choice = "apify"; break
    service = "instagram" if choice == "cookies" else "apify"
    if ACCOUNT.exists():
        say(f"  Подключаю ветку «{choice}» через онбординг...")
        subprocess.run([sys.executable, str(ACCOUNT), "onboard", service])
    else:
        say(f"  (account.py не найден - пропускаю авто-онбординг, ветка выбрана: {choice})")
    return choice

def write_config(grab_mode):
    cfg = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    cfg["grab_mode"] = grab_mode
    # развернуть ~ и создать капку на Рабочем столе
    for k in ("queue_dir", "output_dir", "archive_dir", "log_file", "chrome_profile_dir"):
        cfg[k] = os.path.expanduser(cfg[k])
    for k in ("queue_dir", "output_dir", "archive_dir"):
        Path(cfg[k]).mkdir(parents=True, exist_ok=True)
    Path(cfg["log_file"]).parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"[4/5] Готово: папка каруселей на Рабочем столе -> {Path(cfg['output_dir']).parent}")
    return cfg

def launch_browser(browser):
    say("[5/5] Открываю браузер для входа в ChatGPT (кастомка автора уже подключена)...")
    r = subprocess.run([sys.executable, str(LAUNCHER), "--launch", "--browser", browser],
                       capture_output=True, text=True)
    say("  " + (r.stdout or r.stderr).strip())
    say("  -> В открытом окне: войди в свой ChatGPT (нужен Plus), можно ничего не настраивать.")
    say("     Кастомка рисуется на ТВОЕЙ подписке, ссылка уже в config.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser"); ap.add_argument("--grab")
    ap.add_argument("--no-launch", action="store_true")
    ap.add_argument("--no-pip", action="store_true")
    a = ap.parse_args()
    say(f"=== Онбординг машины каруселей ({platform.system()}) ===")
    if not a.no_pip:
        ensure_deps()
    browser = pick_browser(a.browser)
    grab = pick_grab(a.grab)
    write_config(grab)
    if not a.no_launch:
        launch_browser(browser)
    say("\n✅ Онбординг завершён. Дальше уникализация каруселей идёт через скилл carousel-uniqualizer.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
