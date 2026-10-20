#!/usr/bin/env python3
"""Verify an Omni Flash output clip against its source. Machine gate before delivery.

Checks (exit 1 on any FAIL, prints JSON verdict):
  - aspect ratio matches source within tolerance (NEVER stretch - project rule)
  - output has an audio stream (source voice must be preserved)
  - output duration within tolerance of source

Usage: verify_output.py --src input.mp4 --out result.mp4 [--dur-tol 0.6] [--ar-tol 0.02]
"""
import argparse
import json
import subprocess
import sys


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"ffprobe failed for {path}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        raise SystemExit(f"no video stream in {path}")
    return {
        "w": int(v["width"]),
        "h": int(v["height"]),
        "ar": int(v["width"]) / int(v["height"]),
        "has_audio": a is not None,
        "dur": float(d["format"].get("duration", 0) or 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur-tol", type=float, default=0.6, help="доп. отклонение длительности, доля")
    ap.add_argument("--ar-tol", type=float, default=0.02, help="доп. отклонение соотношения сторон, доля")
    a = ap.parse_args()

    src, out = probe(a.src), probe(a.out)
    checks = []

    ar_dev = abs(out["ar"] - src["ar"]) / src["ar"]
    checks.append(("aspect_ratio_no_stretch", ar_dev <= a.ar_tol,
                   f"src {src['w']}x{src['h']} ({src['ar']:.4f}) vs out {out['w']}x{out['h']} ({out['ar']:.4f}), dev {ar_dev:.3f}"))

    checks.append(("audio_preserved", out["has_audio"],
                   "audio stream present" if out["has_audio"] else "NO audio stream in output"))

    if src["dur"] > 0:
        dur_dev = abs(out["dur"] - src["dur"]) / src["dur"]
        checks.append(("duration_match", dur_dev <= a.dur_tol,
                       f"src {src['dur']:.2f}s vs out {out['dur']:.2f}s, dev {dur_dev:.3f}"))

    ok = all(c[1] for c in checks)
    print(json.dumps({
        "ok": ok,
        "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in checks],
    }, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()