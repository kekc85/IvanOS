#!/usr/bin/env python3
"""
qc_check.py - детерминированная приёмка финального ролика.

Usage:
    qc_check.py <final.mp4> [--expect-dur X] [--lufs -14] [--tol 1.5]

Печатает "PASS/FAIL имя: детали" на каждую проверку, exit 0 если все PASS иначе exit 1.
"""

import sys
import os
import json
import argparse
import subprocess

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def ffprobe_json(video_path):
    """Полный ffprobe вывод в json (потоки + формат)."""
    cmd = [FFPROBE, "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe упал: {result.stderr[-1000:]}")
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="QC приёмка финального ролика")
    parser.add_argument("final_mp4")
    parser.add_argument("--expect-dur", type=float, default=None)
    parser.add_argument("--lufs", type=float, default=-14.0)
    parser.add_argument("--tol", type=float, default=1.5)
    args = parser.parse_args()

    results = []  # (name, passed, details)

    # 1. файл существует, размер > 1MB
    path = args.final_mp4
    exists = os.path.exists(path)
    size_ok = False
    size_bytes = 0
    if exists:
        size_bytes = os.path.getsize(path)
        size_ok = size_bytes > 1 * 1024 * 1024
    passed = exists and size_ok
    results.append(("файл_существует_и_размер", passed,
                     f"exists={exists}, size={size_bytes} байт (нужно >1MB)"))

    if not passed:
        # без файла дальше проверять нечего
        print_results(results)
        sys.exit(1)

    # получить метаданные один раз
    try:
        meta = ffprobe_json(path)
    except RuntimeError as e:
        results.append(("ffprobe_метаданные", False, str(e)))
        print_results(results)
        sys.exit(1)

    streams = meta.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # 2. видео-поток 1080x1920, fps 29-31
    video_ok = False
    video_details = "видео-поток не найден"
    if video_streams:
        v = video_streams[0]
        w = v.get("width")
        h = v.get("height")
        fps_raw = v.get("r_frame_rate", "0/1")
        try:
            num, den = fps_raw.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        video_ok = (w == 1080 and h == 1920 and 29.0 <= fps <= 31.0)
        video_details = f"{w}x{h} @ {fps:.2f}fps (нужно 1080x1920, fps 29-31)"
    results.append(("видео_поток_1080x1920", video_ok, video_details))

    # 3. есть аудио-поток
    audio_ok = len(audio_streams) > 0
    results.append(("аудио_поток_присутствует", audio_ok,
                     f"найдено аудио-потоков: {len(audio_streams)}"))

    # 4. длительность
    fmt = meta.get("format", {})
    duration = float(fmt.get("duration", 0.0))
    if args.expect_dur is not None:
        dur_ok = abs(duration - args.expect_dur) <= 0.5
        results.append(("длительность", dur_ok,
                         f"факт {duration:.2f}с, ожидание {args.expect_dur:.2f}с (±0.5с)"))
    else:
        results.append(("длительность", True, f"факт {duration:.2f}с (проверка пропущена, --expect-dur не задан)"))

    # 5. полный декод без ошибок
    decode_cmd = [FFMPEG, "-v", "error", "-i", path, "-f", "null", "-"]
    decode_result = subprocess.run(decode_cmd, capture_output=True, text=True)
    stderr_clean = decode_result.stderr.strip()
    decode_ok = (decode_result.returncode == 0) and (stderr_clean == "")
    results.append(("полный_декод_без_ошибок", decode_ok,
                     "stderr пуст" if decode_ok else f"stderr: {stderr_clean[:500]}"))

    # 6. громкость через loudnorm
    loud_cmd = [FFMPEG, "-i", path, "-af",
                "loudnorm=print_format=json", "-f", "null", "-"]
    loud_result = subprocess.run(loud_cmd, capture_output=True, text=True)
    loud_ok = False
    loud_details = "не удалось распарсить loudnorm json"
    try:
        stderr_text = loud_result.stderr
        json_start = stderr_text.rfind("{")
        json_end = stderr_text.rfind("}") + 1
        loud_json = json.loads(stderr_text[json_start:json_end])
        input_i = float(loud_json.get("input_i", "0"))
        loud_ok = abs(input_i - args.lufs) <= args.tol
        loud_details = f"input_i={input_i:.2f} LUFS, цель {args.lufs}±{args.tol}"
    except (ValueError, json.JSONDecodeError):
        pass
    results.append(("громкость_loudnorm", loud_ok, loud_details))

    print_results(results)

    all_pass = all(p for _, p, _ in results)
    sys.exit(0 if all_pass else 1)


def print_results(results):
    for name, passed, details in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status} {name}: {details}")


if __name__ == "__main__":
    main()
