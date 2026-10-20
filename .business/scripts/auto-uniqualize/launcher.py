#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Кроссплатформенный автодетект браузера + запуск на CDP (порт 9222) для рендера каруселей.
Win + Mac + Linux. Ученик выбирает браузер, скрипт сам находит его и поднимает с
remote-debugging. Драйвер потом цепляется connect_over_cdp к этому же порту.

Использование:
  python3 launcher.py --list                 # показать найденные браузеры (JSON)
  python3 launcher.py --launch [--browser N] [--port 9222] [--profile PATH]
  python3 launcher.py --wait  [--port 9222]  # дождаться живого CDP (health-check)
Ничего не скрапит. Только запускает локальный браузер для твоей же сессии ChatGPT.
"""
import argparse, json, os, platform, subprocess, sys, time, urllib.request
from pathlib import Path

OS = platform.system()  # 'Darwin' | 'Windows' | 'Linux'

def _pf(*envs):
    for e in envs:
        v = os.environ.get(e)
        if v:
            yield v

# Кандидаты по ОС: имя -> список возможных путей исполняемого файла
def candidates():
    if OS == "Darwin":
        return {
            "Chrome":   ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "Edge":     ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
            "Brave":    ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
            "Chromium": ["/Applications/Chromium.app/Contents/MacOS/Chromium"],
        }
    if OS == "Windows":
        pf  = list(_pf("PROGRAMFILES", "ProgramW6432")) + [r"C:\Program Files"]
        pfx = list(_pf("PROGRAMFILES(X86)")) + [r"C:\Program Files (x86)"]
        lad = list(_pf("LOCALAPPDATA")) + [str(Path.home()/ "AppData"/"Local")]
        def j(bases, *tail): return [str(Path(b, *tail)) for b in bases]
        return {
            "Chrome":   j(pf,  "Google","Chrome","Application","chrome.exe")
                      + j(pfx, "Google","Chrome","Application","chrome.exe")
                      + j(lad, "Google","Chrome","Application","chrome.exe"),
            "Edge":     j(pfx, "Microsoft","Edge","Application","msedge.exe")
                      + j(pf,  "Microsoft","Edge","Application","msedge.exe"),
            "Brave":    j(pf,  "BraveSoftware","Brave-Browser","Application","brave.exe")
                      + j(pfx, "BraveSoftware","Brave-Browser","Application","brave.exe"),
        }
    # Linux
    return {
        "Chrome":   ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/opt/google/chrome/chrome"],
        "Edge":     ["/usr/bin/microsoft-edge"],
        "Brave":    ["/usr/bin/brave-browser"],
        "Chromium": ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"],
    }

def detect():
    found = []
    for name, paths in candidates().items():
        for p in paths:
            if p and Path(p).exists():
                found.append({"name": name, "path": p})
                break
    return found

def default_profile():
    return str(Path.home()/ ".carousel-cdp-profile")

def cdp_alive(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def launch(path, port, profile):
    Path(profile).mkdir(parents=True, exist_ok=True)
    args = [path, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
            "--no-first-run", "--no-default-browser-check", "--restore-last-session=false"]
    kw = {}
    if OS == "Windows":
        kw["creationflags"] = 0x00000008  # DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)

def wait_cdp(port, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cdp_alive(port):
            return True
        time.sleep(1)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--launch", action="store_true")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--browser")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--profile", default=default_profile())
    a = ap.parse_args()

    found = detect()
    if a.list:
        print(json.dumps(found, ensure_ascii=False))
        return 0
    if a.wait:
        return 0 if wait_cdp(a.port) else 2
    if a.launch:
        if cdp_alive(a.port):
            print(f"CDP уже живой на {a.port}")
            return 0
        if not found:
            sys.stderr.write("Не нашёл ни одного браузера (Chrome/Edge/Brave/Chromium). Установи любой и повтори.\n")
            return 2
        pick = None
        if a.browser:
            pick = next((b for b in found if b["name"].lower() == a.browser.lower()), None)
        pick = pick or found[0]
        launch(pick["path"], a.port, a.profile)
        ok = wait_cdp(a.port)
        print(f"{'OK' if ok else 'НЕ ПОДНЯЛСЯ'}: {pick['name']} на CDP {a.port} (профиль {a.profile})")
        return 0 if ok else 2
    ap.print_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
