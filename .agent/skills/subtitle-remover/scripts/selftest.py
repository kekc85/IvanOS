#!/usr/bin/env python3
"""Machine quality gate for subtitle removal. Runs EAST on the caption band of
the CLEANED output and fails if caption-like text / ghosts remain.

Truth is the artifact, not words: this is what lets the skill say "clean" only
when it is actually clean.

Usage: selftest.py <clean_frames_or_video> <report_dir> [orig_masks_dir]
Env: EAST_MODEL, BAND_TOP=0.40, BAND_BOT=0.96, EAST_CONF=0.5,
     SAMPLE=8 (take every Nth frame), MAX_BAND_HITS=0.06 (fail above this ratio)
Exit code 0 = PASS, 2 = FAIL.
"""
import sys, os, glob, json, tempfile, subprocess
import cv2
import numpy as np

SRC, REPORT = sys.argv[1], sys.argv[2]
os.makedirs(REPORT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
EAST_PATH = os.environ.get("EAST_MODEL", os.path.join(HERE, "..", "models", "frozen_east_text_detection.pb"))
BAND_TOP = float(os.environ.get("BAND_TOP", "0.40"))
BAND_BOT = float(os.environ.get("BAND_BOT", "0.96"))
EAST_CONF = float(os.environ.get("EAST_CONF", "0.5"))
SAMPLE = int(os.environ.get("SAMPLE", "8"))
MAX_BAND_HITS = float(os.environ.get("MAX_BAND_HITS", "0.06"))

# gather frames (from dir or by extracting from a video)
tmp = None
if os.path.isdir(SRC):
    frames = sorted(glob.glob(os.path.join(SRC, "*.png")))
else:
    tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-i", SRC, "-vf", f"fps=30,select=not(mod(n\\,{SAMPLE}))",
                    "-vsync", "0", os.path.join(tmp, "%04d.png")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames = sorted(glob.glob(os.path.join(tmp, "*.png")))

net = cv2.dnn.readNet(EAST_PATH)
LAYERS = ["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"]


def band_text_boxes(img, y0, y1):
    H, W = img.shape[:2]
    nW = 320; nH = max(32, int(round(H * (nW / float(W)) / 32)) * 32)
    rW, rH = W / float(nW), H / float(nH)
    blob = cv2.dnn.blobFromImage(img, 1.0, (nW, nH), (123.68, 116.78, 103.94), True, False)
    net.setInput(blob); scores, geo = net.forward(LAYERS)
    boxes, confs = [], []
    for y in range(scores.shape[2]):
        s = scores[0, 0, y]; d0, d1, d2, d3, ang = (geo[0, j, y] for j in range(5))
        for x in range(scores.shape[3]):
            if s[x] < EAST_CONF:
                continue
            ox, oy = x * 4.0, y * 4.0; a = ang[x]; cs, sn = np.cos(a), np.sin(a)
            hh = d0[x] + d2[x]; ww = d1[x] + d3[x]
            ex = int(ox + cs * d1[x] + sn * d2[x]); ey = int(oy - sn * d1[x] + cs * d2[x])
            boxes.append([int(ex - ww), int(ey - hh), int(ww), int(hh)]); confs.append(float(s[x]))
    idx = cv2.dnn.NMSBoxes(boxes, confs, EAST_CONF, 0.3) if boxes else []
    hits = []
    for i in np.array(idx).reshape(-1):
        x, y, w, h = boxes[i]
        cy = (y + h / 2.0) * rH
        if y0 <= cy <= y1 and w * rW > W * 0.06:
            hits.append([int(x * rW), int(y * rH), int(w * rW), int(h * rH)])
    return hits


checked = 0; band_hit_frames = 0; worst = []
for fp in frames[::SAMPLE]:
    img = cv2.imread(fp)
    if img is None:
        continue
    H, W = img.shape[:2]; y0, y1 = int(H * BAND_TOP), int(H * BAND_BOT)
    hits = band_text_boxes(img, y0, y1)
    checked += 1
    if hits:
        band_hit_frames += 1
        if len(worst) < 6:
            ov = img.copy()
            for (x, y, w, h) in hits:
                cv2.rectangle(ov, (x, y), (x + w, y + h), (0, 0, 255), 3)
            outp = os.path.join(REPORT, "residual_" + os.path.basename(fp))
            cv2.imwrite(outp, ov); worst.append(outp)

ratio = band_hit_frames / max(checked, 1)
verdict = "PASS" if ratio <= MAX_BAND_HITS else "FAIL"
report = {"verdict": verdict, "frames_checked": checked,
          "frames_with_residual_band_text": band_hit_frames,
          "residual_ratio": round(ratio, 3), "threshold": MAX_BAND_HITS,
          "evidence": worst}
with open(os.path.join(REPORT, "selftest.json"), "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if verdict == "PASS" else 2)
