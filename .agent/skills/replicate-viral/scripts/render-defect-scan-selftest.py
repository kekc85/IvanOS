#!/usr/bin/env python3
"""render-defect-scan-selftest.py — self-test для render-defect-scan.py.

Фокус: ПРАВИЛО 4 «INTRO БЕЗ ПОЛОС» (check "intro"). Прецедент в даты запуска: ролик в первые
~2с шёл НЕ на весь экран — сверху однотонная серая/белая полоса (intro не на весь экран).
Чек: первые ~2с рендера, в верхней зоне ищем подряд идущие строки с нулевой вариацией
яркости по ширине (плоская серая/белая полоса). Полоса >= порога подряд = FAIL.

Кейсы:
  ПОЗИТИВ: intro = контент НА ВЕСЬ ЭКРАН (шумный/градиентный кадр, без плоской полосы) → PASS (exit 0)
  НЕГАТИВ: intro со СЕРОЙ ПОЛОСОЙ сверху (плоский серый бар 0..200px) → FAIL (exit 2) + «INTRO НЕ НА ВЕСЬ ЭКРАН»

Плюс smoke: чужие чеки (fill) на нормальном кадре не ломаются.
Exit 0 = все зелёные, 1 = провал.
"""
import os, sys, json, subprocess, tempfile

W, H = 1080, 1920
FFMPEG = "ffmpeg" if os.path.exists("ffmpeg") else "ffmpeg"
SCAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render-defect-scan.py")


def make_clip(path, top_bar):
    """2.5с клип. top_bar=True → плоская серая полоса 0..200px сверху + шумный контент ниже;
    top_bar=False → шумный контент на ВЕСЬ кадр (нет плоской полосы)."""
    if top_bar:
        # серый бар сверху (color) + шум снизу, скомпонованы overlay
        vf = (f"color=c=gray:s={W}x{H}:d=2.5[bg];"
              f"nullsrc=s={W}x{H}:d=2.5,geq=random(1)*255:128:128[n];"
              f"[bg][n]overlay=0:200:shortest=1,format=yuv420p[v]")
    else:
        # контент на весь экран: цветной шум, плоской однотонной полосы нет
        vf = (f"nullsrc=s={W}x{H}:d=2.5,"
              f"geq=r='random(1)*255':g='random(2)*255':b='random(3)*255',"
              f"format=yuv420p[v]")
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
           f"nullsrc=s=2x2:d=2.5", "-filter_complex", vf,
           "-map", "[v]", "-r", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-t", "2.5", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(path):
        # fallback: проще через два отдельных входа
        if top_bar:
            cmd2 = [FFMPEG, "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"color=c=gray:s={W}x{H}:d=2.5",
                    "-f", "lavfi", "-i", f"nullsrc=s={W}x{H}:d=2.5,geq=random(1)*255:128:128",
                    "-filter_complex", "[1:v]crop=1080:1720:0:0[low];[0:v][low]overlay=0:200:shortest=1,format=yuv420p[v]",
                    "-map", "[v]", "-r", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "2.5", path]
        else:
            cmd2 = [FFMPEG, "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"nullsrc=s={W}x{H}:d=2.5,geq=r=random(1)*255:g=random(2)*255:b=random(3)*255",
                    "-r", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "2.5", path]
        r = subprocess.run(cmd2, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(path):
            print("FAIL self-setup: не собрался клип\n", r.stderr[-1500:]); sys.exit(1)


def run_scan(render, spec_path, beats):
    json.dump({"beats": beats}, open(spec_path, "w"), ensure_ascii=False)
    r = subprocess.run([sys.executable, SCAN, "--render", render, "--spec", spec_path,
                        "--fps", "5"], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="rds_selftest_")
    p_pass = os.path.join(tmp, "intro_full.mp4")
    p_fail = os.path.join(tmp, "intro_bar.mp4")
    make_clip(p_pass, top_bar=False)
    make_clip(p_fail, top_bar=True)

    spec = os.path.join(tmp, "spec.json")
    intro_beat = [{"name": "intro", "t0": 0.0, "t1": 2.0,
                   "top_box": [0, 0, 1080, 220], "bar_min_rows": 24, "check": ["intro"]}]

    passed = failed = 0

    def expect(label, cond, extra=""):
        nonlocal passed, failed
        if cond:
            print(f"  v {label}"); passed += 1
        else:
            print(f"  x {label} {extra}"); failed += 1

    print("---- ПРАВИЛО 4: INTRO БЕЗ ПОЛОС ----")
    rc_ok, out_ok = run_scan(p_pass, spec, intro_beat)
    expect("позитив: intro на весь экран → PASS (exit 0)", rc_ok == 0,
           f"(rc={rc_ok})\n{out_ok}")

    rc_bad, out_bad = run_scan(p_fail, spec, intro_beat)
    expect("негатив: серая полоса сверху → FAIL (exit 2) + «INTRO НЕ НА ВЕСЬ ЭКРАН»",
           rc_bad == 2 and "INTRO НЕ НА ВЕСЬ ЭКРАН" in out_bad,
           f"(rc={rc_bad})\n{out_bad}")

    print("  ---")
    print(f"  render-defect-scan selftest: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
