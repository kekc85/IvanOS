#!/usr/bin/env python3
"""Robust caption mask for subtitle removal — two passes.

PASS 1 (recall): EAST text-detection (any colour / no plate / off-centre) UNION
semi-transparent plate detection, restricted to the caption band. Catches every
caption regardless of style (fixes the old heuristic that missed ~26% of frames
and all yellow captions).

PASS 2 (precision): burned-in subtitles CHANGE content frame-to-frame while
static UI / persistent badges do NOT. We build a temporal-change map and keep
only mask regions that sit on changing pixels — so static screencast labels,
kanban pills and game badges in the same band are dropped, the caption is kept.

Usage: detect.py <frames_dir> <masks_dir> [overlay_dir]
Env: EAST_MODEL, BAND_TOP=0.40, BAND_BOT=0.96, EAST_CONF=0.45,
     CHANGE_THRESH=10 (mean temporal delta to count a region as "moving"),
     TEMPORAL=1 (set 0 to disable pass 2)
"""
import sys, os, glob
import cv2
import numpy as np

FRAMES, MASKS = sys.argv[1], sys.argv[2]
OVERLAY = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(MASKS, exist_ok=True)
if OVERLAY:
    os.makedirs(OVERLAY, exist_ok=True)

HERE = os.path.dirname(os.path.abspath(__file__))
EAST_PATH = os.environ.get("EAST_MODEL", os.path.join(HERE, "..", "models", "frozen_east_text_detection.pb"))
BAND_TOP = float(os.environ.get("BAND_TOP", "0.40"))
BAND_BOT = float(os.environ.get("BAND_BOT", "0.96"))
EAST_CONF = float(os.environ.get("EAST_CONF", "0.45"))
CHANGE_THRESH = float(os.environ.get("CHANGE_THRESH", "10"))
TEMPORAL = os.environ.get("TEMPORAL", "1") == "1"

net = cv2.dnn.readNet(EAST_PATH)
LAYERS = ["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"]


def east_boxes(img):
    H, W = img.shape[:2]
    nW = 320
    nH = max(32, int(round(H * (nW / float(W)) / 32)) * 32)
    rW, rH = W / float(nW), H / float(nH)
    blob = cv2.dnn.blobFromImage(img, 1.0, (nW, nH), (123.68, 116.78, 103.94), True, False)
    net.setInput(blob)
    scores, geo = net.forward(LAYERS)
    boxes, confs = [], []
    for y in range(scores.shape[2]):
        s = scores[0, 0, y]
        d0, d1, d2, d3, ang = geo[0, 0, y], geo[0, 1, y], geo[0, 2, y], geo[0, 3, y], geo[0, 4, y]
        for x in range(scores.shape[3]):
            if s[x] < EAST_CONF:
                continue
            ox, oy = x * 4.0, y * 4.0
            a = ang[x]; cos, sin = np.cos(a), np.sin(a)
            hh = d0[x] + d2[x]; ww = d1[x] + d3[x]
            ex = int(ox + cos * d1[x] + sin * d2[x]); ey = int(oy - sin * d1[x] + cos * d2[x])
            boxes.append([int(ex - ww), int(ey - hh), int(ww), int(hh)]); confs.append(float(s[x]))
    idx = cv2.dnn.NMSBoxes(boxes, confs, EAST_CONF, 0.3) if boxes else []
    return [(int(boxes[i][0] * rW), int(boxes[i][1] * rH), int(boxes[i][2] * rW), int(boxes[i][3] * rH))
            for i in np.array(idx).reshape(-1)]


def plate_mask(img, y0, y1):
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sat = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1]
    mid = ((gray > 12) & (gray < 205) & (sat < 80)).astype(np.uint8)
    core = cv2.erode(mid, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    core = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    plate = cv2.morphologyEx(core * 255, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (55, 11)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(plate, 8)
    m = np.zeros((H, W), np.uint8)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        cy = y + h / 2.0
        if a < 2500 or h < 30 or cy < y0 or cy > y1:
            continue
        ar = w / max(h, 1)
        if ar < 1.6 or ar > 14 or w < W * 0.12:
            continue
        m[lbl == i] = 255
    return m


frames = sorted(glob.glob(os.path.join(FRAMES, "*.png")))
if not frames:
    print("no frames"); sys.exit(0)
H, W = cv2.imread(frames[0]).shape[:2]
y0, y1 = int(H * BAND_TOP), int(H * BAND_BOT)
SS = 4  # downsample factor for the temporal-change map (cheap)

# ---- PASS 1: raw recall masks + accumulate band greyscale for change map ----
raw = []
band_small = []
for fp in frames:
    img = cv2.imread(fp)
    m = np.zeros((H, W), np.uint8)
    for (x, y, w, h) in east_boxes(img):
        cy = y + h / 2.0
        if cy < y0 or cy > y1 or w < W * 0.05 or w > W * 0.97 or h < 10 or h > H * 0.25:
            continue
        cv2.rectangle(m, (x, y), (x + w, y + h), 255, -1)
    m = cv2.bitwise_or(m, plate_mask(img, y0, y1))
    raw.append(m)
    if TEMPORAL:
        g = cv2.cvtColor(img[y0:y1, :], cv2.COLOR_BGR2GRAY)
        band_small.append(cv2.resize(g, (W // SS, (y1 - y0) // SS)))

# ---- SHOT-AWARE temporal-change maps ----
# A scene cut makes every pixel change, which would defeat a global std. So we
# split the clip into shots (big frame-to-frame jumps) and compute the change
# map WITHIN each shot: static UI stays flat, the cycling caption stands out.
CUT_THRESH = float(os.environ.get("CUT_THRESH", "22"))
per_frame_change = [None] * len(frames)
if TEMPORAL and len(band_small) >= 3:
    arr = np.stack(band_small).astype(np.float32)            # (T, h, w)
    diffs = np.abs(np.diff(arr, axis=0)).mean(axis=(1, 2))   # per-frame jump
    shots, start = [], 0
    for t in range(1, len(arr)):
        if diffs[t - 1] > CUT_THRESH:
            shots.append((start, t)); start = t
    shots.append((start, len(arr)))
    for (a, b) in shots:
        if b - a >= 2:
            chg = arr[a:b].std(axis=0)
        else:
            chg = np.full(arr.shape[1:], CHANGE_THRESH + 1, np.float32)  # single frame: keep
        chg_full = np.zeros((H, W), np.float32)
        chg_full[y0:y1, :] = cv2.resize(chg, (W, y1 - y0))
        for i in range(a, b):
            per_frame_change[i] = chg_full

# ---- PASS 2: keep only mask regions sitting on changing pixels (per shot) ----
for i, fp in enumerate(frames):
    mask = raw[i]
    chg = per_frame_change[i] if TEMPORAL else None
    if chg is not None:
        n, lbl, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
        kept = np.zeros((H, W), np.uint8)
        for k in range(1, n):
            comp = lbl == k
            if chg[comp].mean() >= CHANGE_THRESH:           # caption (content cycles)
                kept[comp] = 255
        mask = kept
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
    out = os.path.join(MASKS, os.path.splitext(os.path.basename(fp))[0] + ".png")
    cv2.imwrite(out, mask)
    if OVERLAY:
        img = cv2.imread(fp); ov = img.copy(); ov[mask > 0] = (0, 0, 255)
        cv2.imwrite(os.path.join(OVERLAY, os.path.basename(fp)),
                    cv2.addWeighted(img, 0.55, ov, 0.45, 0))
print(f"detect done ({len(frames)} frames, temporal={'on' if TEMPORAL else 'off'})")
