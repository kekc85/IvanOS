#!/usr/bin/env python3
"""
viral-content-prep (secondary режим): преобразует ingest split-screen tutorial Reel в готовый пакет для Custom GPT уникализатор.

Usage:
    python3 prep.py <ingest-dir>

Input:
    ingest-dir/
      scene-types.json    — scene classification + ui_zone_y координаты
      transcript.json     — whisper output с тайм-кодами
      transcript.txt      — plain text
      frames/             — f_001.jpg ... f_NNN.jpg
      {video_id}.info.json — yt-dlp metadata

Output:
    ~/Desktop/viral-content/{video_id}/
      cover-frame.png
      ui-crops/step-01.png ... step-N.png
      transcript.txt
      structure.json
      README.md
"""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image


def main(ingest_dir: str) -> int:
    src = Path(ingest_dir).resolve()
    if not src.is_dir():
        print(f"ERR: ingest-dir не найден: {src}", file=sys.stderr)
        return 1

    scene_types_path = src / "scene-types.json"
    transcript_json_path = src / "transcript.json"
    transcript_txt_path = src / "transcript.txt"
    frames_dir = src / "frames"

    for f in (scene_types_path, transcript_json_path, transcript_txt_path, frames_dir):
        if not f.exists():
            print(f"ERR: отсутствует {f}", file=sys.stderr)
            return 1

    with open(scene_types_path) as fh:
        scene_data = json.load(fh)
    with open(transcript_json_path) as fh:
        transcript_data = json.load(fh)

    reel_id = scene_data.get("source_id") or src.name.split("-", 3)[-1]
    duration = float(scene_data.get("duration_sec", 0))
    layout = scene_data.get("source_layout_notes", {})
    ui_zone_y_native = layout.get("ui_zone_y", [0, 0])
    native_res = scene_data.get("native_resolution", [1080, 1920])
    native_h = native_res[1] if len(native_res) >= 2 else 1920
    scenes = scene_data.get("scenes", [])

    info_path = next(src.glob("*.info.json"), None)
    creator = "unknown"
    reel_url = ""
    language = "EN"
    if info_path:
        with open(info_path) as fh:
            info = json.load(fh)
        creator = info.get("channel") or info.get("uploader_id") or "unknown"
        reel_url = info.get("webpage_url", "")
    language = transcript_data.get("result", {}).get("language", "EN").upper()

    # fps
    frame_files = sorted(frames_dir.glob("f_*.jpg"))
    if not frame_files:
        print("ERR: пустая frames/ папка", file=sys.stderr)
        return 1
    fps = len(frame_files) / duration if duration > 0 else 2.0

    # output
    out_root = Path.home() / "Desktop" / "viral-content"
    out = out_root / reel_id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shutil.copy(transcript_txt_path, out / "transcript.txt")

    # Сегментация: группируем подряд идущие сцены ui_only/slide
    segments = []
    cur = None
    for sc in scenes:
        s_type = sc["type"]
        sec = sc["sec"]
        if s_type in ("ui_only", "slide"):
            if cur and cur["type"] == s_type:
                cur["end"] = sec
            else:
                if cur:
                    segments.append(cur)
                cur = {"type": s_type, "start": sec, "end": sec}
        else:
            if cur:
                segments.append(cur)
                cur = None
    if cur:
        segments.append(cur)

    # Дедупликация: per-segment один представительный кадр (середина)
    # Plus дедупликация между сегментами через md5 downsampled hash
    seen_hashes = set()
    steps = []
    step_idx = 0
    for seg in segments:
        mid_sec = (seg["start"] + seg["end"]) // 2
        frame_idx = max(0, min(len(frame_files) - 1, int(mid_sec * fps)))
        frame_path = frame_files[frame_idx]
        img = Image.open(frame_path).convert("RGB")
        W, H = img.size

        # Crop UI zone (top portion). ui_zone_y_native в координатах native_h, frames downsampled.
        scale_y = H / native_h
        ui_top = max(0, min(H, int(ui_zone_y_native[0] * scale_y)))
        ui_bot = max(ui_top + 1, min(H, int(ui_zone_y_native[1] * scale_y)))
        ui_crop = img.crop((0, ui_top, W, ui_bot))

        # Hash для дедупа (32x32 grayscale → md5)
        h = hashlib.md5(ui_crop.resize((32, 32)).convert("L").tobytes()).hexdigest()[:12]
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        step_idx += 1
        out_name = f"step-{step_idx:02d}.png"
        out_path = out / out_name

        # Resize to width 1080 preserving aspect (для подачи в split-screen верх)
        crop_w, crop_h = ui_crop.size
        new_w = 1080
        new_h = int(crop_h * (new_w / crop_w))
        ui_crop = ui_crop.resize((new_w, new_h), Image.LANCZOS)
        ui_crop.save(out_path)

        # Связный transcript для этой секции
        seg_text = transcript_in_range(transcript_data, seg["start"], seg["end"])

        steps.append({
            "id": step_idx,
            "ui_crop": out_name,
            "transcript": seg_text,
            "sec_start": seg["start"],
            "sec_end": seg["end"],
            "frame_source": frame_path.name,
        })

    # Cover-frame: первый face_only кадр где есть лицо
    cover_sec = None
    for sc in scenes:
        if sc["type"] == "face_only":
            cover_sec = sc["sec"]
            break
    if cover_sec is None:
        cover_sec = 0
    frame_idx = max(0, min(len(frame_files) - 1, int(cover_sec * fps)))
    cover_img = Image.open(frame_files[frame_idx]).convert("RGB")
    # Полный кадр (1080x1920) сохраняем как cover — Custom GPT решит как кропать под 1080x1350
    cover_img.save(out / "cover-frame.png")

    # Хук transcript: первая фраза
    hook = ""
    for seg in transcript_data.get("transcription", []):
        hook = seg.get("text", "").strip()
        if hook:
            break

    # CTA: последняя фраза
    cta_text = ""
    for seg in reversed(transcript_data.get("transcription", [])):
        cta_text = seg.get("text", "").strip()
        if cta_text:
            break
    # Code-word подсказка: ищем заглавное слово или явный action
    code_word = guess_code_word(cta_text, info_path)

    structure = {
        "reel_id": reel_id,
        "reel_url": reel_url,
        "creator": creator,
        "duration_sec": duration,
        "language": language,
        "cover": {
            "frame": "cover-frame.png",
            "transcript_hook": hook,
        },
        "steps": steps,
        "cta_hint": {
            "transcript": cta_text,
            "code_word_suggestion": code_word,
        },
    }
    with open(out / "structure.json", "w") as fh:
        json.dump(structure, fh, indent=2, ensure_ascii=False)

    write_readme(out, structure)

    print(f"OK viral-content-prep (secondary) complete: {out}")
    print(f"  steps: {len(steps)}")
    print(f"  cover: cover-frame.png ({cover_sec}s)")
    print(f"  language: {language}")
    print(f"  code_word_hint: {code_word}")
    return 0


def transcript_in_range(transcript_data: dict, sec_start: int, sec_end: int) -> str:
    """Вытащить связный текст из transcript.json по диапазону секунд."""
    parts = []
    for seg in transcript_data.get("transcription", []):
        offs = seg.get("offsets", {})
        seg_start = offs.get("from", 0) / 1000.0
        seg_end = offs.get("to", 0) / 1000.0
        # overlap
        if seg_end >= sec_start and seg_start <= sec_end + 1:
            txt = seg.get("text", "").strip()
            if txt:
                parts.append(txt)
    return " ".join(parts)


def guess_code_word(cta_text: str, info_path) -> str:
    """Попытка вытащить код-слово из CTA или caption."""
    if not cta_text:
        return ""
    # Известные паттерны: 'comment X', "type X", 'write X', 'send X'
    import re
    text = cta_text.lower()
    patterns = [
        r"comment\s+['\"]?(\w+)",
        r"type\s+['\"]?(\w+)",
        r"write\s+['\"]?(\w+)",
        r"напиши\s+['\"]?(\w+)",
        r"пиши\s+['\"]?(\w+)",
        r"send\s+['\"]?(\w+)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).upper()
    # Fallback на caption из info.json
    if info_path:
        with open(info_path) as fh:
            info = json.load(fh)
        desc = (info.get("description", "") or "").lower()
        for p in patterns:
            m = re.search(p, desc)
            if m:
                return m.group(1).upper()
    return ""


def write_readme(out: Path, structure: dict) -> None:
    md = [
        f"# Reel→Carousel Package: {structure['reel_id']}",
        "",
        f"Creator: @{structure['creator']}",
        f"URL: {structure['reel_url']}",
        f"Duration: {structure['duration_sec']}s",
        f"Language: {structure['language']}",
        f"Steps extracted: {len(structure['steps'])}",
        f"Code-word hint: {structure['cta_hint']['code_word_suggestion'] or '(none detected — задай вручную)'}",
        "",
        "## Файлы",
        "",
        "- `cover-frame.png` — кадр автора для cover-слайда",
        "- `step-01.png ... step-N.png` — реальные UI-кропы (плоско в этой папке)",
        "- `transcript.txt` — полный транскрипт",
        "- `structure.json` — машинно-читаемая структура",
        "",
        "## Как передать в Custom GPT уникализатор",
        "",
        "1. Открой Custom GPT уникализатор IG",
        "2. Загрузи в чат: cover-frame.png + все ui-crops/step-NN.png",
        "3. Вставь команду:",
        "",
        "```",
        f"reel mode +CTA. Язык: {structure['language']}.",
        f"Hook автора: «{structure['cover']['transcript_hook']}»",
        "Steps:",
    ]
    for s in structure["steps"]:
        md.append(f'  Step {s["id"]} (step-{s["id"]:02d}.png): «{s["transcript"]}»')
    md.append(f'CTA hint автора: «{structure["cta_hint"]["transcript"]}»')
    if structure["cta_hint"]["code_word_suggestion"]:
        md.append(f'Можно использовать слово автора: {structure["cta_hint"]["code_word_suggestion"]}')
    md.append("Конкретная выгода: [ТЫ ВВОДИШЬ ВРУЧНУЮ — что пришлёшь по код-слову]")
    md.append("```")
    md.append("")
    md.append("4. Custom GPT соберёт cover (image gen по hook) → N body-слайдов (Code Interpreter pastes реальный UI-кроп + drawtext под ним) → CTA + watermark на каждом.")
    (out / "README.md").write_text("\n".join(md))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: prep.py <ingest-dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))