#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read-aloud-check.py - механическая проверка текста «на язык» (читаемость вслух).

Хороший текст статьи читается легко: его можно произнести и не запнуться. Часть
«спотыканий» ловится механически, не дожидаясь, пока живой человек реально
запнётся при чтении. Скрипт флагает:

  1. Длинные предложения   - длиннее N слов трудно прочесть на одном дыхании.
  2. Скопления согласных    - 5+ согласных подряд = скороговорка.
  3. Очень длинные слова     - длиннее N букв тяжелы вслух.
  4. Канцелярит / причастия   - суффиксы -вшись/-ующ/-явш и т.п. спотыкают.
  5. Голые цифры              - «4-6» вместо «четыре-шесть»: вслух неоднозначно.

Это НЕ замена чтению вслух живым человеком (финальный судья - он). Это сито,
которое снимает грубые куски до вычитки. Заточено под русский текст.

Пороги (берутся из config.yaml → CLI → дефолт):
  tools.read_aloud.max_sentence_words   (по умолч. 28)
  tools.read_aloud.max_word_len         (по умолч. 17)
  tools.read_aloud.max_consonant_run    (по умолч. 5)

Зависимости: только стандартная библиотека Python 3 (re, json, os, argparse).
PyYAML не требуется.

Использование:
  python3 tools/read-aloud-check.py <статья.md>
  python3 tools/read-aloud-check.py <статья.md> --max-sentence 24 --json
  python3 tools/read-aloud-check.py <статья.md> --config ./config.yaml

Коды выхода: 0 = чисто, 1 = есть флаги (не блокер, список на правку), 3 = ошибка ввода.
"""
import argparse
import html
import json
import os
import re
import sys

try:
    import _config as cfgmod
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _config as cfgmod

VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
CONS = "бвгджзйклмнпрстфхцчшщБВГДЖЗЙКЛМНПРСТФХЦЧШЩ"

DEFAULT_MAX_SENTENCE_WORDS = 28
DEFAULT_MAX_WORD_LEN = 17
DEFAULT_CONS_RUN = 5

# Спотыкаемые формы. Деепричастия (-вшись/-ясь) и страдательные причастия
# (-уемых/-ируемых) ловим всегда - они тяжелы вслух. Активные причастия на
# -ующ/-ающ/-ивш ловим ТОЛЬКО в длинных словах (≥12 букв), чтобы не флагать
# обычные читаемые «следующий», «существующий», «текущий».
CLUNKY_SUFFIX = re.compile(
    r"\w+(?:вшись|явшись|ившись|уясь|аясь|ируем\w*|уем\w*|ляем\w*|"
    r"вшихся|вшийся|вшегося)\w*"
    r"|[а-яё]{8,}(?:ующ|ающ|ивш|явш|ующих|ающих)\w*",
    re.IGNORECASE)
# полный числовой токен: 19.99 / 3.6 / 2026 / 0-25 берутся ЦЕЛИКОМ, а не осколками
# («19» и «99» отдельно) - калибровка по решению автора по принятым владельцем страницам
DIGIT_TOKEN = re.compile(r"(?<!\w)\d+(?:[.,:]\d+)*(?:[\-–]\d+(?:[.,:]\d+)*)?(?!\w)")
WORD = re.compile(r"[а-яёa-z]+", re.IGNORECASE)


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def looks_like_html(text):
    """Собранная страница, а не markdown-черновик."""
    return bool(re.search(r"<!doctype html|<html\b", text[:2000], re.I))


def strip_html_chrome(text):
    """Из СОБРАННОЙ страницы оставить только то, что человек читает вслух.

    🔴 Правка по решению автора (диагностика «гейт красит REVIEW весь корпус, включая
    страницы, принятые владельцем»). Раньше html снимался одной строкой
    `re.sub(r"<[^>]+>", " ")` - она убирает ТЕГИ, но не СОДЕРЖИМОЕ script/style.
    В результате в «текст статьи» попадали CSS и JS: `@font-face{...}` считался
    предложением на 53-68 слов, `getBoundingClientRect` и `isAccessibleForFree`
    из JSON-LD - длинными словами, юникод-escape вида \\u0301 - голыми цифрами.
    На типовой статье-гайде замер давал 12018 слов и 1438 предложений против 2760 слов и
    288 предложений живой прозы: три четверти «текста» - машинная разметка. Гейт
    из-за этого выдавал REVIEW ВСЕГДА, независимо от качества текста - то есть
    не мерил ничего.

    Порядок: выкинуть блоки с непроизносимым содержимым (script/style/noscript/
    svg/template/iframe) вместе с внутренностью → выкинуть комментарии → взять
    тело статьи <article>/<main>, если оно есть (шапка, оглавление, боковая
    панель и подвал - навигация шаблона, вслух её не читают) → выкинуть листинги
    <pre>/<code> (тот же закон, что для ``` в markdown: команду не декламируют) →
    снять оставшиеся теги → вернуть html-сущности буквами.
    """
    for tag in ("script", "style", "noscript", "svg", "template", "iframe"):
        text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", " ", text,
                      flags=re.DOTALL | re.I)
        # незакрытый блок такого тега съедает остаток документа и в браузере -
        # значит и вслух его никто не прочтёт
        text = re.sub(rf"<{tag}\b[^>]*>.*\Z", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # ячейки и строки таблиц - не связная речь: без разделителя ряд «Текст |
    # claude | 1506 | $17-20/мес» склеивается в псевдопредложение на 40+ слов
    # (ложняк long_sentence на страницах с таблицами, калибровка по решению автора)
    text = re.sub(r"</(?:td|th|tr|li|h[1-6]|caption|figcaption)\s*>", ". ", text, flags=re.I)
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}\b[^>]*>(.*)</{tag}\s*>", text, re.DOTALL | re.I)
        if m:
            text = m.group(1)
            break
    text = re.sub(r"<pre\b[^>]*>.*?</pre\s*>", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<code\b[^>]*>.*?</code\s*>", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def strip_for_speech(text):
    """Оставить только произносимое: убрать markup, код, html, ссылки, тайм-коды."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    if looks_like_html(text):
        text = strip_html_chrome(text)
    else:
        text = re.sub(r"<[^>]+>", " ", text)                          # html-теги
    text = re.sub(r"^---\n.*?\n---\n", " ", text, flags=re.DOTALL)    # yaml-фронтматтер
    text = re.sub(r"^\s*#{1,6}.*$", " ", text, flags=re.MULTILINE)    # заголовки-секции
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)                 # картинки
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)              # ссылки → текст
    text = re.sub(r"\d{1,2}:\d{2}", " ", text)                        # тайм-коды
    text = re.sub(r"[*_>|#~]", " ", text)
    return text


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip() and WORD.search(p)]


def max_cons_run(word):
    run = best = 0
    for ch in word:
        if ch in CONS:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def _selftest_extraction():
    """Селфтест экстракции произносимого текста (правка 12.08.2026).

    Проверяет ровно то, из-за чего гейт красил REVIEW весь корпус: в замер
    попадала машинная разметка. Плюс негатив-контроль - что гейт после починки
    не оглох и живое длинное предложение по-прежнему ловит.
    """
    css = ("@font-face{font-family:'Spectral';font-style:normal;font-weight:300;"
           "font-display:swap;src:url(/assets/f.woff2) format('woff2');"
           "unicode-range:U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116}")
    jsonld = ('{"@type":"CollegeOrUniversity","isAccessibleForFree":true,'
              '"primaryImageOfPage":"/a.jpg"}')
    js = "document.querySelectorAll('h2').forEach(function(n){n.getBoundingClientRect()})"
    page = (f"<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            f"<style>{css}</style>"
            f"<script type=\"application/ld+json\">{jsonld}</script></head><body>"
            f"<header><nav><a href=\"/\">Главная</a></nav></header>"
            f"<main><article><h2>Раздел</h2>"
            f"<p>Нейросеть подбирает следующее слово. Это вся её работа.</p>"
            f"<pre><code>pip install --upgrade requests</code></pre>"
            f"<p>Открой вкладку и нажми &laquo;Отправить&raquo;.</p>"
            f"</article></main><footer><p>Подвал сайта</p></footer>"
            f"<script>{js}</script></body></html>")

    long_prose = "Мы " + " ".join(f"слово{i}" for i in range(1, 46)) + "."
    page_long = (f"<!doctype html><html><body><main><article>"
                 f"<p>{long_prose}</p></article></main></body></html>")

    md = ("# Заголовок\n\nОбычная фраза здесь.\n\n```\n@font-face{font-weight:300}\n```\n"
          "Ещё фраза с `inline-кодом` внутри.\n")

    checks = []

    txt = strip_for_speech(page)
    sents = split_sentences(txt)
    words = sum(len(WORD.findall(s)) for s in sents)
    checks.append(("CSS @font-face не считается предложением",
                   "@font-face" not in txt, txt[:120]))
    checks.append(("JSON-LD не считается текстом",
                   "CollegeOrUniversity" not in txt and "isAccessibleForFree" not in txt,
                   txt[:120]))
    checks.append(("JS не считается текстом",
                   "getBoundingClientRect" not in txt, txt[:120]))
    checks.append(("листинг <pre><code> не читается вслух",
                   "pip install" not in txt, txt[:200]))
    checks.append(("шапка и подвал шаблона не идут в замер",
                   "Главная" not in txt and "Подвал сайта" not in txt, txt[:200]))
    checks.append(("html-сущности вернулись буквами",
                   "«Отправить»" in txt and "&laquo;" not in txt, txt[:300]))
    checks.append((f"осталась только проза: предложений {len(sents)}, слов {words}",
                   len(sents) == 4 and 10 <= words <= 25, # 4: заголовок h2 - отдельная фраза (границы ячеек/заголовков, по решению автора)
                   f"{sents}"))
    checks.append(("флагов на здоровом куске нет",
                   not any(len(WORD.findall(s)) > 40 for s in sents), f"{sents}"))

    txt2 = strip_for_speech(page_long)
    s2 = split_sentences(txt2)
    checks.append(("живое длинное предложение всё ещё ловится (гейт не оглох)",
                   any(len(WORD.findall(s)) > 40 for s in s2),
                   f"{[len(WORD.findall(s)) for s in s2]}"))

    txt3 = strip_for_speech(md)
    checks.append(("markdown-режим не изменился: fence и inline-код сняты",
                   "@font-face" not in txt3 and "inline-кодом" not in txt3
                   and "Обычная фраза здесь." in txt3, txt3.strip()[:160]))

    failed = 0
    for name, ok, evidence in checks:
        if not ok:
            failed += 1
        print(f"  [{'OK  ' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"         улика: {evidence}")
    print(f"\nСелфтест экстракции: проверок {len(checks)}, провалов {failed}")
    return 0 if failed == 0 else 1


def parse_args():
    p = argparse.ArgumentParser(
        prog="read-aloud-check.py",
        description="Механическая проверка читаемости текста вслух: длинные "
                    "предложения, скопления согласных, длинные слова, канцелярит, "
                    "голые цифры. Заточено под русский текст.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Пороги: config.yaml (tools.read_aloud.*) → флаги CLI → дефолты "
               "(28 слов / 17 букв / 5 согласных). Коды выхода: 0=чисто, "
               "1=есть флаги, 3=ошибка ввода.",
    )
    p.add_argument("article", nargs="?", help="файл статьи (.md/.txt/.html и т.п.)")
    p.add_argument("--config", default=None,
                   help="путь к config.yaml (по умолчанию ищется ./config.yaml)")
    p.add_argument("--max-sentence", type=int, default=None,
                   help="макс. слов в предложении (перебивает config.yaml)")
    p.add_argument("--max-word-len", type=int, default=None,
                   help="макс. длина слова в буквах (перебивает config.yaml)")
    p.add_argument("--max-consonant-run", type=int, default=None,
                   help="макс. согласных подряд (перебивает config.yaml)")
    p.add_argument("--json", action="store_true", help="вывод машинно-читаемым JSON")
    p.add_argument("--selftest-extraction", action="store_true",
                   help="прогнать селфтест экстракции произносимого текста "
                        "(CSS/JS/JSON-LD/листинги/шапка-подвал не идут в замер) и выйти")
    args = p.parse_args()
    if not args.selftest_extraction and not args.article:
        p.error("нужен файл статьи (либо флаг --selftest-extraction)")
    return args


def main():
    args = parse_args()
    if args.selftest_extraction:
        sys.exit(_selftest_extraction())
    cfg = cfgmod.load_config(args.config or cfgmod.find_config())

    max_sent = args.max_sentence if args.max_sentence is not None \
        else int(cfgmod.get(cfg, "tools.read_aloud.max_sentence_words",
                            DEFAULT_MAX_SENTENCE_WORDS))
    max_word = args.max_word_len if args.max_word_len is not None \
        else int(cfgmod.get(cfg, "tools.read_aloud.max_word_len", DEFAULT_MAX_WORD_LEN))
    cons_run = args.max_consonant_run if args.max_consonant_run is not None \
        else int(cfgmod.get(cfg, "tools.read_aloud.max_consonant_run", DEFAULT_CONS_RUN))

    try:
        raw = read(args.article)
    except OSError as e:
        sys.stderr.write(f"ошибка чтения: {e}\n")
        sys.exit(3)

    text = strip_for_speech(raw)
    sentences = split_sentences(text)
    flags = {"long_sentence": [], "consonant_cluster": [], "long_word": [],
             "clunky_morphology": [], "bare_digits": []}

    total_words = 0
    for s in sentences:
        words = WORD.findall(s)
        total_words += len(words)
        snippet = (s[:90] + "…") if len(s) > 90 else s
        if len(words) > max_sent:
            flags["long_sentence"].append({"words": len(words), "text": snippet})
        for w in words:
            if len(w) > max_word:
                flags["long_word"].append(w)
            if max_cons_run(w) >= cons_run:
                flags["consonant_cluster"].append(w)
        for m in CLUNKY_SUFFIX.finditer(s):
            flags["clunky_morphology"].append(m.group(0))
        for m in DIGIT_TOKEN.finditer(s):
            flags["bare_digits"].append(m.group(0))

    for k in ("long_word", "consonant_cluster", "clunky_morphology", "bare_digits"):
        flags[k] = sorted(set(flags[k]))

    # Калибровка по принятым владельцем образцам (по решению автора):
    # - bare_digits - advisory: канон статей требует цифру в каждой строке, в вердикт не входит;
    # - long_word + clunky_morphology - единичные «зарегистрироваться»/«оставшихся» на
    #   принятой странице = шум; в вердикт идёт только превышение допуска 2 на страницу;
    # - long_sentence и consonant_cluster - жёстко, без допуска.
    word_axes = len(flags["long_word"]) + len(flags["clunky_morphology"])
    total_flags = (len(flags["long_sentence"]) + len(flags["consonant_cluster"])
                   + max(0, word_axes - 2))
    avg_ws = round(total_words / len(sentences), 1) if sentences else 0
    result = {
        "article": args.article,
        "sentences": len(sentences), "total_words": total_words,
        "avg_words_per_sentence": avg_ws,
        "thresholds": {"max_sentence_words": max_sent, "max_word_len": max_word,
                       "max_consonant_run": cons_run},
        "flag_count": total_flags, "flags": flags,
        "verdict": "CLEAN" if total_flags == 0 else "REVIEW",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Чтение вслух: {result['verdict']}  ({total_flags} флагов, "
              f"средн. {avg_ws} слов/предложение, {len(sentences)} предложений)")
        if flags["long_sentence"]:
            print(f"\n  ! Длинные предложения (>{max_sent} слов) - режь на дыхание:")
            for f in flags["long_sentence"][:12]:
                print(f"     [{f['words']}] {f['text']}")
        if flags["consonant_cluster"]:
            print(f"\n  ! Скопления согласных (≥{cons_run}) - скороговорка: "
                  + ", ".join(flags["consonant_cluster"][:15]))
        if flags["long_word"]:
            print(f"\n  ! Длинные слова (>{max_word} букв): "
                  + ", ".join(flags["long_word"][:15]))
        if flags["clunky_morphology"]:
            print("\n  ! Причастия/канцелярит (спотыкают вслух): "
                  + ", ".join(flags["clunky_morphology"][:15]))
        if flags["bare_digits"]:
            print("\n  · Голые цифры (advisory, в вердикт не входит): "
                  + ", ".join(flags["bare_digits"][:15]))
        if total_flags == 0:
            print("  Грубых спотыканий нет. Финальная проверка - чтение вслух человеком.")
    sys.exit(0 if total_flags == 0 else 1)


if __name__ == "__main__":
    main()
