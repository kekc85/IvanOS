#!/usr/bin/env python3
"""Round-trip проверка озвучки (Гейт Озвучки, шаг 2/3 — Фаза 4 replicate-viral).

Прогоняет сгенерированный WAV обратно через whisper и сравнивает со словами
исходного текста. Ловит класс дефектов «модель произнесла не то слово»
. Ударение напрямую не меряется —
финальный судья ударений = прослушка автором (шаг 3/3), этот гейт снимает
дешёво ловимую часть до неё.

ДОБАВЛЕНО по решению автора: автодетект ЯЗЫКА whisper'ом (-dl) ДО форс-ru транскрипта.
Печатает «detected lang=XX p=Y.YY»; p(expected)<0.9 = WARN жирным. Это НЕ ловля
фонетики — фонетику/ударения судит ТОЛЬКО ухо (гейт шаг 3/3).

Usage: tts-verify.py <audio.wav> <source-text-file> [--max-miss 0.08] [--expect-lang ru]
Exit 0 = PASS (расхождение ≤ порога), exit 2 = FAIL + список слов.
Требует: whisper-cli + ~/whisper-models/ggml-large-v3-turbo.bin + ffmpeg.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

MODEL = os.path.expanduser('~/whisper-models/ggml-large-v3-turbo.bin')
BOLD = '\033[1m'
RST = '\033[0m'


def norm_words(text: str):
    text = text.lower().replace('ё', 'е')
    # числа и латиница остаются как есть; пунктуация долой
    return [w for w in re.findall(r'[a-zа-я0-9\-]+', text) if w]


def detect_language(wav16):
    # whisper -dl: автодетект языка + p, выход после детекта. Парсим:
    #   "auto-detected language: ru (p = 0.987654)"
    # Возвращает (lang, p) или (None, None) если не распарсилось.
    try:
        r = subprocess.run(['whisper-cli', '-m', MODEL, '-f', wav16, '-dl'],
                           capture_output=True, text=True)
    except Exception:
        return None, None
    blob = (r.stderr or '') + (r.stdout or '')
    m = re.search(r'auto-detected language:\s*([a-z]{2,3})\s*\(p\s*=\s*([0-9.]+)\)', blob, re.I)
    if not m:
        return None, None
    return m.group(1).lower(), float(m.group(2))


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1
    wav, src_path = sys.argv[1], sys.argv[2]
    max_miss = 0.08
    expect_lang = 'ru'
    if '--max-miss' in sys.argv:
        max_miss = float(sys.argv[sys.argv.index('--max-miss') + 1])
    if '--expect-lang' in sys.argv:
        expect_lang = sys.argv[sys.argv.index('--expect-lang') + 1].lower()

    src_words = norm_words(open(src_path, encoding='utf-8').read())

    with tempfile.TemporaryDirectory() as td:
        wav16 = os.path.join(td, 'a16.wav')
        out = os.path.join(td, 'tr')
        subprocess.run(['ffmpeg', '-y', '-i', wav, '-ar', '16000', '-ac', '1', wav16],
                       capture_output=True, check=True)
        # --- ШАГ 0: автодетект языка ДО форс-ru транскрипта ---
        lang, p = detect_language(wav16)
        if lang is None:
            print('tts-verify: detected lang=?? p=?.?? (whisper -dl не распарсился) — '
                  'детект языка пропущен, продолжаю round-trip')
        else:
            print(f'tts-verify: detected lang={lang} p={p:.2f} (ожидался {expect_lang})')
            if lang != expect_lang or p < 0.9:
                print(f'{BOLD}WARN (tts-verify): язык озвучки lang={lang} p={p:.2f} '
                      f'не совпал с ожидаемым {expect_lang} при p>=0.90 — переслушать, '
                      f'возможно озвучка уехала не в тот язык{RST}', file=sys.stderr)

        subprocess.run(['whisper-cli', '-m', MODEL, '-f', wav16, '-l', 'ru',
                        '-ojf', '-of', out], capture_output=True, check=True)
        data = json.load(open(out + '.json', encoding='utf-8'))

    heard_text = ' '.join(s['text'] for s in data.get('transcription', []))
    heard = norm_words(heard_text)

    # односторонний diff: какие слова исходника whisper не услышал такими же
    heard_set = {}
    for w in heard:
        heard_set[w] = heard_set.get(w, 0) + 1
    missing = []
    for w in src_words:
        if heard_set.get(w, 0) > 0:
            heard_set[w] -= 1
        else:
            missing.append(w)

    ratio = len(missing) / max(len(src_words), 1)
    print(f'tts-verify: слов в тексте {len(src_words)}, не совпало {len(missing)} '
          f'({ratio:.0%}, порог {max_miss:.0%})')
    if missing:
        print('  расхождения (текст → не услышано так же):', ', '.join(missing[:20]))
    if ratio > max_miss:
        print('FAIL (tts-verify): озвучка расходится с текстом — переслушать/перегенерить '
              'проблемные предложения ДО HeyGen', file=sys.stderr)
        return 2
    print('tts-verify: PASS (детект языка ≠ ловля фонетики — фонетику/ударения судит ТОЛЬКО ухо, гейт шаг 3/3)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
