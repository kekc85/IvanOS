#!/usr/bin/env python3
"""make-cue-sheet.py — выдать cue-sheet (тайминги битов) отрендеренного motion-элемента.

ЗАЧЕМ: звук рилзов мы НЕ имитируем синтезом/стоком (доказанный тупик, см.
). Скилл даёт визуал/motion + ЭТОТ cue-sheet,
а звук кладёт автор своим ухом (реюз low-voice беда рефа через demucs / его подбор).
Cue-sheet = точные секунды каждого визуального бита, чтобы класть звук за минуту, не на глаз.

Метод: покадровая разница средней яркости (ffmpeg signalstats YAVG) → пики = появления/смены.
Фолбэк: если детект пустой (ровный фон) — взять data-start/тайминги из params.json рядом с видео.

Usage: python3 make-cue-sheet.py <element.mp4> [out.md]
Output: markdown-таблица (сек | бит | предложенный тип звука) в stdout и в out.md.
"""
import subprocess, sys, re, os, json, tempfile

def luma_events(vid):
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
    subprocess.run(["ffmpeg", "-i", vid, "-vf",
                    f"scale=16x16,signalstats,metadata=print:file={tmp}",
                    "-an", "-f", "null", "-"], capture_output=True)
    t, v = [], []
    for line in open(tmp, errors="ignore"):
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m: t.append(float(m.group(1)))
        m = re.search(r"YAVG=([0-9.]+)", line)
        if m: v.append(float(m.group(1)))
    os.unlink(tmp)
    n = min(len(t), len(v))
    if n < 3: return []
    import statistics
    d = [0.0] + [abs(v[i] - v[i-1]) for i in range(1, n)]
    mean = sum(d) / n
    std = (statistics.pstdev(d)) or 1e-9
    thr = mean + 1.0 * std
    ev = []
    for i in range(1, n):
        if d[i] > thr and d[i] >= max(d[max(0, i-2):i+3]) - 1e-9:
            if not ev or t[i] - ev[-1] > 0.3:
                ev.append(round(t[i], 2))
    return ev

def params_fallback(vid):
    d = os.path.dirname(os.path.abspath(vid))
    p = os.path.join(d, "params.json")
    if not os.path.exists(p): return []
    try:
        j = json.load(open(p))
    except Exception:
        return []
    # часто тайминги в comments/steps; иначе равномерно по duration
    dur = float(j.get("duration", 8))
    n = len(j.get("comments", j.get("steps", []))) or 6
    return [round(dur * (i + 0.5) / n, 2) for i in range(n)]

def suggest_type(i, total):
    if i == total - 1: return "удар/реверс (кульминация)"
    if i == 0: return "вход/whoosh"
    return "tap/pop (появление)"

def main():
    if len(sys.argv) < 2:
        print("Usage: make-cue-sheet.py <element.mp4> [out.md]"); sys.exit(1)
    vid = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(vid)[0] + "-cue-sheet.md"
    ev = luma_events(vid)
    src = "яркостный детект"
    if not ev:
        ev = params_fallback(vid); src = "фолбэк params.json"
    lines = [f"# Cue-sheet: {os.path.basename(vid)}",
             f"_источник битов: {src} · звук кладёшь ухом (реюз low-voice беда / свой подбор), скилл звук НЕ имитирует_", "",
             "| # | секунда | бит | предложенный тип звука |",
             "|---|---|---|---|"]
    for i, t in enumerate(ev):
        lines.append(f"| {i+1} | {t:.2f}s | бит {i+1} | {suggest_type(i, len(ev))} |")
    md = "\n".join(lines)
    open(out, "w").write(md + "\n")
    print(md)
    print(f"\n→ сохранено: {out}  ({len(ev)} битов)")

if __name__ == "__main__":
    main()