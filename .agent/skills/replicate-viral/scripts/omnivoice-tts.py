#!/usr/bin/env python3

# CYRILLIC_TRANSLIT_GUARD (автор ×2): англицизмы в TTS — ЛАТИНИЦЕЙ,
# кириллическая транслитерация брендов = кривое ударение. exit 2 до загрузки модели.
import re as _re, sys as _sys
_BAD = ['джи пи ти', 'джи-пи-ти', 'джипити', 'чат гпт', 'чатгпт', 'хиггсфилд', 'хейген', 'эм би ти ай', 'эмбити']
def _translit_guard(text):
    low = text.lower()
    hits = [b for b in _BAD if b in low]
    if hits:
        _sys.stderr.write('BLOCKED (translit-guard): кириллическая транслитерация бренда в TTS-тексте: '
                          + ', '.join(hits) + '. Пиши латиницей (ChatGPT, Claude, Higgsfield, MBTI) — '
                          'память feedback_tts_anglicisms_in_latin\n')
        _sys.exit(2)

"""OmniVoice TTS — обёртка скилла replicate-viral над прототипом clone.py.

Клонирует голос автора из референса и генерит озвучку адаптированного скрипта.
Бесплатно, локально на M4 Max (MPS). Голос-референс готовится ОДИН раз.

Usage:
  python3 omnivoice-tts.py "<текст>" <ref_voice.wav> <ref_text.txt> <out.wav> [ru|en]

Запускать из venv: ~/_venvs/omnivoice-venv (как clone.py).
Прототип-эталон: ~/.business/processes/omnivoice-test/clone.py
"""
import sys
import time
import soundfile as sf
import torch
from omnivoice import OmniVoice

HF_REPO = "k2-fsa/OmniVoice"


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    text = sys.argv[1]
    _translit_guard(text)
    ref_audio = sys.argv[2]
    ref_text = open(sys.argv[3]).read().strip()
    out = sys.argv[4]
    lang = sys.argv[5] if len(sys.argv) > 5 else "ru"

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "mps" else torch.float32
    print(f"[1/3] loading {HF_REPO} on {device}/{dtype}...", flush=True)
    model = OmniVoice.from_pretrained(HF_REPO, torch_dtype=dtype).to(device).eval()

    print("[2/3] voice clone prompt from ref...", flush=True)
    prompt = model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text)

    print(f"[3/3] generating ({lang})...", flush=True)
    t0 = time.time()
    with torch.no_grad():
        audio_list = model.generate(text=text, voice_clone_prompt=prompt, language=lang)
    audio = audio_list[0]
    sr = 24000
    sf.write(out, audio, sr)
    print(f"DONE -> {out} ({len(audio)/sr:.1f}s in {time.time()-t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()