#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kill-switch каруселей, кроссплатформенный (Win + Mac + Linux).
Гасит: CDP-браузер, поднятый под профиль каруселей, и активные драйверы рендера.
Использование: python3 stop.py
Замена Mac-only stop.sh (pkill).
"""
import os, platform, subprocess, sys
from pathlib import Path

OS = platform.system()
PROFILE_MARK = ".carousel-cdp-profile"          # чем помечен наш браузер (user-data-dir)
DRIVER_MARK  = ("driver_parallel.py", "driver.py")

def _kill_unix():
    killed = 0
    try:
        out = subprocess.run(["ps", "axo", "pid,command"], capture_output=True, text=True).stdout
    except Exception:
        return killed
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        pid, _, cmd = line.partition(" ")
        if PROFILE_MARK in cmd or any(m in cmd for m in DRIVER_MARK):
            try:
                os.kill(int(pid), 9); killed += 1
            except Exception:
                pass
    return killed

def _kill_windows():
    killed = 0
    try:
        out = subprocess.run(
            ["wmic", "process", "get", "ProcessId,CommandLine", "/FORMAT:LIST"],
            capture_output=True, text=True).stdout
    except Exception:
        out = ""
    cur = {}
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.startswith("CommandLine="):
            cur["cmd"] = ln[len("CommandLine="):]
        elif ln.startswith("ProcessId="):
            cur["pid"] = ln[len("ProcessId="):]
            cmd = cur.get("cmd", "")
            if PROFILE_MARK in cmd or any(m in cmd for m in DRIVER_MARK):
                try:
                    subprocess.run(["taskkill", "/F", "/PID", cur["pid"]],
                                   capture_output=True); killed += 1
                except Exception:
                    pass
            cur = {}
    return killed

def main():
    killed = _kill_windows() if OS == "Windows" else _kill_unix()
    print(f"🛑 Остановлено процессов каруселей: {killed}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
