#!/usr/bin/env python3
"""Финализация ролика: пилюля-CTA с cta_t0 до конца + двухпроходный loudnorm -14 LUFS + CFR.
Код проверен в бою (fable по решению автора). aresample async=1000:first_pts=0 обязателен:
loudnorm удлиняет аудио ~67мс и без ресемпла уводит синхрон (память feedback_reel_av_skew_after_loudnorm_fix).
Usage: finalize.py <in.mp4> <cta_t0> <pill.png> <out.mp4>"""
import json, re, subprocess, sys, os

FF, FP = "ffmpeg", "ffprobe"

if len(sys.argv) != 5:
    sys.exit(__doc__)
SRC, CTA, PILL, OUT = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
for f in (SRC, PILL):
    if not os.path.exists(f):
        sys.exit(f"FAIL: нет входа {f}")

VDUR = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=nk=1:nw=1", SRC], capture_output=True, text=True).stdout.strip())
if not (0 < CTA < VDUR):
    sys.exit(f"FAIL: cta_t0={CTA} вне ролика (длительность {VDUR:.2f})")

# шаг 1: пилюля поверх с CTA до конца
STEP1 = OUT + ".pill.mp4"
r = subprocess.run([FF, "-v", "error", "-y", "-i", SRC, "-loop", "1", "-t", f"{VDUR:.3f}", "-i", PILL,
                    "-filter_complex", f"[0:v][1:v]overlay=0:0:enable='between(t,{CTA},{VDUR})'[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy", "-t", f"{VDUR:.3f}", STEP1],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("PILL FAIL:\n" + r.stderr[-800:])

# шаг 2: loudnorm двухпроходный linear
r = subprocess.run([FF, "-hide_banner", "-i", STEP1,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True)
m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S)
if not m:
    sys.exit("LOUDNORM MEASURE FAIL:\n" + r.stderr[-800:])
meas = json.loads(m.group(0))
ln2 = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}"
       f":measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}"
       f":offset={meas['target_offset']}:linear=true")
r = subprocess.run([FF, "-v", "error", "-y", "-i", STEP1,
                    "-af", f"{ln2},aresample=async=1000:first_pts=0",
                    "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-vsync", "cfr", "-video_track_timescale", "30000",
                    "-t", f"{VDUR:.3f}", OUT], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit("LOUDNORM APPLY FAIL:\n" + r.stderr[-800:])
os.remove(STEP1)

# самопроверка: оба потока на месте, длительность совпала
streams = subprocess.run([FP, "-v", "error", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0", OUT], capture_output=True, text=True).stdout
if "video" not in streams or "audio" not in streams:
    sys.exit(f"FAIL: в финале не оба потока ({streams.strip()})")
d = float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nk=1:nw=1", OUT], capture_output=True, text=True).stdout.strip())
if abs(d - VDUR) > 0.5:
    sys.exit(f"FAIL: длительность финала {d:.2f} против {VDUR:.2f}")
print(f"OK финал {OUT}: {d:.2f}с, CTA@{CTA:.2f}, video+audio, loudnorm -14 применён")