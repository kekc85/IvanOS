#!/usr/bin/env python3
"""
split_detector.py — машинно классифицирует ролик: настоящий SPLIT-SCREEN донор или нет.
Настоящий split (под replicate-viral) = постоянная двухпанель: лицо стабильно в НИЖНЕЙ зоне,
сверху UI/скринкаст инструмента (не кожа). Отличается от talking-head с врезками (чередование
FULL лицо-весь-кадр ↔ content только-экран, мало стабильного split).
Плюс проверка размера субтитров (узкие = перекрываются плашкой; крупные = брак).

Переиспользует движок зрения replicate-viral (source_vision.analyze: YuNet/Haar лица + caption).
Использование: python3 split_detector.py <video.mp4|dir> [--step 6] [--json]
"""
import sys, os, json, statistics

SKILL = os.path.expanduser("~/.claude/skills/replicate-viral/scripts")
sys.path.insert(0, SKILL)
import source_vision as sv

# Пороги (откалиброваны на разметке автора: split=DZfX4L7tWhz/DZpavmHNRtd/DZu6rKUvgTB, не-split=DZeAM3MMNsW, субтитры-фейл=DZkYwF7Nz4A)
TOP_SKIN_MAX    = 0.05     # сверху UI/скринкаст → кожи почти нет
BOT_SKIN_MIN    = 0.06     # снизу человек/спикер → кожа есть
TOP_UI_MIN      = 0.60     # сверху СТАБИЛЬНО UI (а не лицо на весь кадр) — главный признак split
BOT_HUMAN_MIN   = 0.15     # снизу есть человек (отсекает чистый screencast без лица)
CAP_H_RATIO_MAX = 0.060    # высота субтитра / высота кадра: узкие субтитры

def detect(path, step=6):
    import cv2
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("видео не открылось")
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1920
    top_y1 = int(H * 0.45); bot_y0 = int(H * 0.55)
    data = []; caps = []; prev_er = None; idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if step > 1 and (idx % step) != 0:
            idx += 1; continue
        top = sv.skin_frac(fr, 0, top_y1)
        bot = sv.skin_frac(fr, bot_y0, H)
        best, prev_er = sv.detect_caption(fr, prev_er, sv.CAP_YMIN, sv.CAP_YMAX)
        if best:
            caps.append(best[1])
        data.append((top, bot))
        idx += 1
    cap.release()
    n = len(data) or 1
    frac_split     = sum(1 for t, b in data if t < TOP_SKIN_MAX and b > BOT_SKIN_MIN) / n
    frac_top_ui    = sum(1 for t, b in data if t < TOP_SKIN_MAX) / n
    frac_bot_human = sum(1 for t, b in data if b > BOT_SKIN_MIN) / n
    cap_h = statistics.median(caps) if caps else 0.0
    cap_h_ratio = cap_h / H

    is_split = (frac_top_ui >= TOP_UI_MIN) and (frac_bot_human >= BOT_HUMAN_MIN)
    subs_ok  = cap_h_ratio <= CAP_H_RATIO_MAX
    return {
        "is_split": bool(is_split),
        "subs_narrow": bool(subs_ok),
        "ideal": bool(is_split and subs_ok),
        "split_ratio": round(frac_split, 2),
        "top_ui_ratio": round(frac_top_ui, 2),
        "bot_human_ratio": round(frac_bot_human, 2),
        "cap_h_px": round(cap_h, 1),
        "cap_h_ratio": round(cap_h_ratio, 3),
        "n": n,
    }

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    step = 6
    if "--step" in sys.argv:
        step = int(sys.argv[sys.argv.index("--step") + 1])
    as_json = "--json" in sys.argv
    target = args[0]
    paths = []
    if os.path.isdir(target):
        paths = sorted(os.path.join(target, f) for f in os.listdir(target) if f.endswith(".mp4"))
    else:
        paths = [target]
    for p in paths:
        try:
            v = detect(p, step=step)
        except Exception as e:
            print(f"{os.path.basename(p)}\t#ERR {str(e)[:60]}"); continue
        name = os.path.basename(p).replace(".mp4", "")
        if as_json:
            print(json.dumps({"name": name, **v}, ensure_ascii=False))
        else:
            mark = "✅SPLIT+узкие" if v["ideal"] else ("◻split,субтитры-крупные" if v["is_split"] else "❌не-split")
            print(f"{name:14} | {mark:24} | split={v['split_ratio']} topUI={v['top_ui_ratio']} botHuman={v['bot_human_ratio']} | capH={v['cap_h_ratio']}")
