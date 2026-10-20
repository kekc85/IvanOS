#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-cadence-check.py — механический детектор AI-почерка в русском тексте.

Ловит то, что вычитка пропускает «на глаз»: накопительную плотность симметрий и
шаблонов, которыми нейросеть выдаёт себя. Живой автор пишет криво и асимметрично;
модель — гладко и симметрично. Считаем ПЛОТНОСТЬ на 1000 слов (а не «подряд / не
подряд»): одна антитеза на абзац по всему тексту — это уже почерк.

Категории маркеров:
  A) антитезы «не X, а Y» / разорванная «Это не А. Это Б» / стартовое «а не …»
  B) одиночные слова через точку («Просто. Понятно. Эффективно.»)
  C) литературные обороты («эпоха X закончилась», «настоящая революция», «фундаментально»…)
  D) канцелярит («таким образом», «важно отметить», «следует учитывать»…)
  E) безличные конструкции / крючки-подзаголовки («вы узнаете», «и самое мощное»…)
  F) длинное тире (—) и en-dash (–) — типографика, которую любит генерация
     (частный случай слоя A, см. категорию I)
  G) параллельные пары — два предложения подряд с одинаковым контентным стартом
  H) label-stamp — повтор одинакового ярлыка-метки первым блоком раздела
     («Коротко:», «TL;DR:», «Если коротко:», «Итого:»…). Семейство резюме — не
     более ОДНОГО на страницу (второе вхождение = hard-флаг); любой другой
     одинаковый ярлык — не более 3 (4+ = hard-флаг; порог согласован со
     structure-check, где та же ось роняет прогон, — один критерий, один вердикт).
  I) Слой A методологии (Этап 15) — юникод-маркеры, 9 классов: em dash U+2014,
     en dash U+2013, тире-двойники (весь остаток Unicode-категории Pd «Dash
     Punctuation» — figure dash U+2012, horizontal bar U+2015, two/three-em
     dash U+2E3A/U+2E3B, small em dash U+FE58, fullwidth hyphen-minus U+FF0D
     и т.д. — см. DASH_LOOKALIKES ниже), многоточие U+2026, типографские
     кавычки U+201C/201D, апострофы U+2018/2019, ZWSP U+200B, ZWNJ/ZWJ/BOM
     U+200C/200D/FEFF, NBSP U+00A0. Восемь первых классов в теле текста =
     hard-флаг. NBSP — вайтлист ПО ЗОНЕ, а не по символу: в шапке, меню,
     футере и строке хлебных крошек он приходит из шаблона сайта и легален;
     NBSP в теле = SOFT WARN.
     Легальные исключения из Pd (НЕ маркеры): обычный дефис-минус U+002D
     (весь язык на нём стоит) и словообразующие U+2010/U+2011 (HYPHEN /
     NON-BREAKING HYPHEN — типографски верный дефис ВНУТРИ слова, «Санкт‑
     Петербург», перенос строки); их блокировка ловила бы корректный текст,
     а не AI-почерк. em/en dash (U+2013/U+2014) уже свои отдельные классы —
     в DASH_LOOKALIKES не дублируются.

ГДЕ СЧИТАЕМ. Все оси считаются по ЧИСТОЙ ПРОЗЕ: сначала strip_nontext() снимает
<style>/<script>/HTML-комментарии, потом strip_markup() снимает теги. Без этого
инлайн-CSS попадает в знаменатель как «слова», а CSS-переменные — в числитель как
«параллельные пары» (замер: на одной странице 9279 «слов» против 3825
чистых и 48 «параллелей» против 8). Типографику (слой A) дополнительно проверяем в
title и meta description — это тоже авторский текст, его видно в выдаче. Слой A
(включая ellipsis) считается ещё и без <pre>/<code> — strip_code_blocks() снимает
примеры кода/промптов перед подсчётом (хвост по решению автора, см. strip_code_blocks()).

Главная метрика — СУММАРНАЯ плотность маркеров A–E,G на 1000 слов (категории H и I
считаются отдельно как флаги: повтор ярлыка и типографика). Порог:
  tools.cadence.max_per_1k   (по умолч. 8.0)

Порог 8.0 пересчитан на чистом знаменателе по решению автора по слепку корпуса из 209
страниц. Распределение почти не сдвинулось: медиана 3.54 (raw) -> 3.58 (clean),
p75 5.02 -> 5.32, p90 6.52 -> 6.90; поднялся только хвост (p95 7.41 -> 8.39).
Поэтому значение оставлено прежним: на чистом тексте оно ловит 11 страниц вместо
6, то есть гейт стал строже, а не слабее. Эталоны остались CLEAN по плотности:
длинная статья-инструкция 3.82 -> 3.59, страница-словарь 2.73 -> 4.48.

Калибровка под себя (опционально). Если у вас есть папка с собственными текстами
(`config.voice.source` или флаг --baseline-dir), можно прогнать её и увидеть, какая
плотность маркеров у ВАШЕГО живого письма — и выставить порог чуть выше неё. Папка
ваша, не зашита в скрипт.

Зависимости: только стандартная библиотека Python 3 (re, json, os, argparse).
PyYAML не требуется.

Использование:
  python3 tools/ai-cadence-check.py <статья.md>
  python3 tools/ai-cadence-check.py <статья.md> --max-per-1k 6 --json
  python3 tools/ai-cadence-check.py <статья.md> --config ./config.yaml
  python3 tools/ai-cadence-check.py --baseline-dir ./my-texts/   # печать плотностей корпуса
  python3 tools/ai-cadence-check.py --baseline <файл.txt>        # печать плотностей файла

Коды выхода (как объявляет методология, Этап 15):
  0 = CLEAN     — чисто
  1 = REVIEW    — HARD BLOCK: превышен порог плотности, юникод-маркер слоя A
                  (кроме NBSP) или повтор ярлыка-метки
  2 = SOFT WARN — блокирующих осей нет, но есть замечание (NBSP в теле текста)
  3 = ошибка запуска
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

# Подтверждён на чистом знаменателе по решению автора (замер корпуса — см. шапку файла).
DEFAULT_MAX_PER_1K = 8.0

TEXT_EXTS = (".md", ".markdown", ".txt", ".mdx", ".html", ".htm", ".rst", ".text")

# ── Слой A методологии (Этап 15): юникод-маркеры ────────────────────────────────
# Восемь классов ниже = HARD. Девятый класс, NBSP, вынесен отдельно: он приходит из
# шаблона сайта (шапка «автор&nbsp;», крошки «Гайды&nbsp;/&nbsp;…») и по
# слепку корпуса стоит на 204 из 210 страниц — блокировать по символу нельзя,
# вайтлист строится ПО ЗОНЕ.
#
# DASH_LOOKALIKES — adversarial-фикс по решению автора: гейт по em/en-dash ловил ровно ДВА
# символа, и весь остальной Unicode General_Category=Pd («Dash Punctuation») спокойно
# проходил гейт как замена длинного тире — тот же визуальный AI-почерк, другой code
# point (U+2012 figure dash, U+2015 horizontal bar, U+2E3A/U+2E3B two/three-em dash,
# U+FE58 small em dash, U+FF0D fullwidth hyphen-minus и весь блок Pd обходили точечный
# класс). Набор ниже = ПОЛНЫЙ список символов категории Pd МИНУС уже свои классы
# (U+2013 en-dash, U+2014 em-dash) МИНУС легальные в русском тексте: U+002D (обычный
# дефис-минус, ASCII, весь язык на нём стоит) и U+2010/U+2011 (HYPHEN /
# NON-BREAKING HYPHEN — типографски верный дефис ВНУТРИ слова и при переносе строки,
# не замена тире; блокировка ловила бы корректный текст, а не AI-почерк).
# Экзотические скриптовые дефисы (армянский, иврит, канадские слоговые, монгольский,
# японская wave dash) в русской прозе легитимно не встречаются вообще — держим их в
# hard-классе без риска ложных срабатываний.
DASH_LOOKALIKES = (
    "\u2012\u2015"                          # figure dash, horizontal bar
    "\u2e17\u2e1a\u2e3a\u2e3b\u2e40"      # dbl oblique hyphen, hyphen+diaeresis, two/three-em dash, dbl hyphen
    "\u301c\u3030\u30a0"                    # wave dash, wavy dash, katakana-hiragana dbl hyphen
    "\ufe31\ufe32\ufe58\ufe63"             # presentation vert em/en dash, small em dash, small hyphen-minus
    "\uff0d"                                  # fullwidth hyphen-minus
    "\u058a\u05be\u1400\u1806"             # armenian hyphen, hebrew maqaf, canadian syll. hyphen, mongolian soft hyphen
)

UNICODE_HARD_CLASSES = (
    ("em-dash",      "\u2014",                     "длинное тире (U+2014)"),
    ("en-dash",      "\u2013",                     "en-dash (U+2013)"),
    ("dash-lookalikes", DASH_LOOKALIKES,             "тире-двойник Unicode Pd (не U+002D/U+2010/U+2011)"),
    ("ellipsis",     "\u2026",                     "многоточие одним символом (U+2026)"),
    ("smart-quotes", "\u201c\u201d",               "типографские кавычки (U+201C/201D)"),
    ("apostrophes",  "\u2018\u2019",               "типографские апострофы (U+2018/2019)"),
    ("zwsp",         "\u200b",                     "zero-width space (U+200B)"),
    ("zwj-bom",      "\u200c\u200d\ufeff",         "ZWNJ/ZWJ/BOM (U+200C/200D/FEFF)"),
)
NBSP_LABEL = "неразрывный пробел (U+00A0)"

# NBSP приходит и литералом, и сущностью — считаем обе формы.
NBSP_ANY = re.compile("\u00a0|&nbsp;|&#0*160;|&#[xX]0*a0;")

# Зоны шаблона, где типографика легальна: шапка, меню, футер.
TEMPLATE_ZONE = re.compile(r"<(header|footer|nav)\b[^>]*>.*?</\1>", re.S | re.I)
# Абзац-кандидат в хлебные крошки (без вложенных <p>).
P_BLOCK = re.compile(r"<p\b[^>]*>((?:(?!</p>)[\s\S])*)</p>", re.I)
# Разделитель цепочки крошек. Класс узкий намеренно: «»» и «>» встречаются в живой
# прозе, и широкий гард выбрасывал бы из проверки обычные абзацы.
CRUMB_SEP = re.compile(r"(?:^|\s)[/›→](?:\s|$)")
CRUMB_MAX_CHARS = 120
# Крошки стоят до H1. Дальше по странице короткий абзац со ссылкой и слэшем — это
# уже проза («жми Файл / Экспорт»), её вырезать нельзя.
H1_TAG = re.compile(r"<h1\b", re.I)
CRUMB_FALLBACK_LIMIT = 4000

# Авторский текст, который живёт в атрибутах и виден в выдаче: его типографику
# тоже проверяем, иначе strip_markup выбросит его вместе с тегом.
META_TAG = re.compile(r"<meta\b[^>]*>", re.I)
META_ATTR = re.compile(r"([\w:.\-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
META_KEYS = {"description", "og:title", "og:description",
             "twitter:title", "twitter:description"}
TITLE_TAG = re.compile(r"<title\b[^>]*>(.*?)</title>", re.S | re.I)

# Разговорные/служебные старты — их повтор в начале предложений НЕ считаем
# параллелизмом (это нормальная связка, а не AI-симметрия).
# «если» из этого списка УБРАНО по решению автора: пара «Если коротко: …» / «Если коротко: …»
# амнистировалась как обычная связка, и штамп-резюме был невидим сразу по двум осям.
CONNECTOR_STARTS = {
    "и", "а", "но", "ну", "вот", "да", "нет", "так", "это", "я", "ты", "мы",
    "он", "она", "они", "потому", "что", "значит", "то", "тут", "там",
    "когда", "ещё", "еще", "или", "уже", "также", "тоже", "здесь", "при",
}

# Короткие предложения, которые в норме — живые реплики, а не AI-«панчи».
# «коротко» из белого списка УБРАНО по решению автора: оно амнистировало ярлык-метку резюме.
ALLOWED_SHORT = {
    "именно", "точно", "наоборот", "и наоборот", "первое", "второе", "третье",
    "например", "итог", "вывод", "кстати", "и всё", "вот так",
}

# H) Ярлык-метка резюме первым блоком раздела. Форма забракована владельцем
# по решению автора («выглядит как нейрослоп, супер шаблонно»): ответ несёт первая фраза
# раздела, подпись над ней не ставится. Семейство — не более ОДНОГО на страницу.
SUMMARY_LABELS = {
    "если коротко", "коротко", "кратко", "tl;dr", "итого", "вывод", "главное",
    "резюме", "суть", "что запомнить", "короче", "итоги",
}

# Нумерованные семейства — навигация, а не штамп: из подсчёта исключаются.
NUMBERED_LABEL = re.compile(
    r"^(?:шаг|часть|способ|блок|группа|этап|раздел|урок|вариант|пример|уровень|день|"
    r"step|part|way)\s*[№#]?\s*(?:\d+|[ivxlIVXL]+|[a-zа-я])\b",
    re.I,
)

# Начало блока: старт строки (с markdown-префиксами) ИЛИ сразу за открывающим тегом.
_BLOCK_START = r"(?:^[\s>*_#•\-]*|<(?:strong|b|em|i|p|div|span|li|dt|h[1-6])\b[^<>]*>\s*)"
_SP = r"(?:\s|&nbsp;| )"  # пробел, в т.ч. неразрывный и как HTML-сущность

# Семейство резюме ловим независимо от выделения: «<p class="tldr">Если коротко: …»
# метки в теге не имеет вовсе, а это ровно тот случай, который и просочился в прод.
# Граница метки: двоеточие/тире/точка-разделитель ЛИБО конец своего тега
# («<strong …>Коротко</strong>Работаешь 25 минут…», «<p class="eyebrow">Если коротко</p>»).
RE_SUMMARY_STAMP = re.compile(
    _BLOCK_START + r"(если" + _SP + r"+коротко|коротко|кратко|короче|tl;?dr|итоги|итого|"
    r"вывод|главное|резюме|суть|что" + _SP + r"+запомнить)" + _SP + r"*"
    r"(?:[:\-—–··]|</[a-z])",
    re.I | re.M,
)

# Та же метка без всякой пунктуации, приклеенная к тексту («TL;DR всё, что нужно…»).
# Только однозначные ярлыки: «главное/суть/вывод» так начинают и живую прозу.
RE_SUMMARY_LEADIN = re.compile(
    _BLOCK_START + r"(если" + _SP + r"+коротко|коротко|кратко|tl;?dr)" + _SP + r"+(?=[а-яё])",
    re.I | re.M,
)

# Любой другой ярлык считаем только если он ВЫДЕЛЕН (в этом и смысл метки):
# <strong>Зачем:</strong>, **Что менять:**, <em>Важно:</em>.
RE_OTHER_STAMP = re.compile(
    r"(?:<(?:strong|b|em|i)\b[^<>]*>|\*\*|__)\s*([^<>*_:\n]{2,30}?)\s*:",
    re.M,
)

# C) Литературные обороты и пафос (методология, Раздел 4 + Раздел 8/9).
LITERARY = [
    r"эпоха\s+\w+\s+(?:закончил|заканчивает|ушл|прошл)",
    r"эра\s+(?:ушл|закончил|настал|пришл)",
    r"настала\s+эра", r"наступила\s+эра", r"новая\s+эра",
    r"настоящая\s+революция", r"революция\s+в\s+мире",
    r"в\s+мире,?\s+где", r"в\s+эпоху",
    r"новая\s+грамотность",
    r"\bфундаментальн", r"\bкардинальн", r"\bрадикальн",
    r"по-настоящему", r"\bистина\b",
    r"будущее\s+за\s+теми,?\s+кто",
    r"это\s+меняет\s+всё", r"меняет\s+всё\b",
    r"навсегда\s+изменил", r"изменил\s+мир",
]

# D) Канцелярит и связки-штампы (методология, Раздел 5).
CLERICAL = [
    r"\bоднако\b", r"таким\s+образом", r"важно\s+отметить", r"стоит\s+отметить",
    r"стоит\s+сказать", r"следует\s+понимать", r"необходимо\s+учитывать",
    r"следует\s+учитывать", r"как\s+было\s+сказано\s+выше", r"вышеупомянут",
    r"кроме\s+того", r"более\s+того", r"при\s+этом\s+важно", r"также\s+стоит",
    r"в\s+заключение", r"подвед[ёе]м\s+итог", r"в\s+современном\s+мире",
    r"играет\s+(?:ключевую|важную)\s+роль", r"представляет\s+собой",
    r"является\s+неотъемлемой", r"с\s+одной\s+стороны.*?с\s+другой\s+стороны",
]

# E) Безличные конструкции, крючки-подзаголовки, шаблонные старты/финалы
#    (методология, Разделы 6, 7, 10).
IMPERSONAL = [
    r"вам\s+расскаж", r"вы\s+узнаете", r"здесь\s+объясн", r"здесь\s+покаж",
    r"давайте\s+разбер[ёе]м", r"давайте\s+рассмотрим", r"рассмотрим\s+подробнее",
    r"обратите\s+внимание", r"следует\s+помнить", r"важно\s+понимать,?\s+что",
    r"и\s+самое\s+(?:мощное|важное|интересное)", r"вот\s+в\s+ч[ёе]м\s+суть",
    r"а\s+теперь\s+представьте", r"и\s+тут\s+начинается\s+интересное",
    r"самое\s+(?:интересное|важное|мощное)\b",
    r"в\s+этой\s+статье\s+вы\s+узнаете", r"сегодня\s+поговорим",
    r"сегодня\s+я\s+хочу\s+поделиться",
    r"спасибо\s+за\s+внимание", r"и\s+теперь\s+вы\s+понимаете",
]


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_markup(text):
    """Снять markup/код/html, но СОХРАНИТЬ тире и пунктуацию (их мы и проверяем)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^---\n.*?\n---\n", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # маркеры списков/заголовков убираем, но НЕ трогаем «—» и «–»
    text = re.sub(r"^\s*#{1,6}\s*", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[*_>|~`]", " ", text)
    return text


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def first_word(sent):
    m = re.match(r"[«»\"'\-—–\s]*([a-zа-яё]+)", sent.lower())
    return m.group(1) if m else ""


def count_antithesis(text, sentences):
    n, hits = 0, []
    low = text.lower()
    # «не X, а Y» — негация, затем «, а » в пределах ~45 символов
    for m in re.finditer(r"(?<![a-zа-яё])не\s+[^,.!?:;]{1,45}?,\s+а\s+", low):
        n += 1
        hits.append("«не…, а…»: …" + low[m.start():m.end()].strip())
    # стартовое «а не …» отдельным предложением
    for s in sentences:
        if re.match(r"^[«»\"'\-—–\s]*а\s+не\s+", s.lower()):
            n += 1
            hits.append("стартовое «а не …»: " + s[:50])
    # разорванная «это не … . это …» через границу предложений
    for i in range(len(sentences) - 1):
        s1, s2 = sentences[i].lower(), sentences[i + 1].lower()
        if re.search(r"\bэто\s+не\b", s1) and \
           re.match(r"^[«»\"'\-—–\s]*(?:и\s+|а\s+)?это\b", s2):
            n += 1
            hits.append("«это не…/это…»: " + sentences[i][:32] + " || " + sentences[i + 1][:32])
    return n, hits


def count_single_word_period(sentences):
    """Одиночные слова-предложения, идущие цепочкой («Просто. Понятно. Эффективно.»)."""
    n, hits = 0, []
    run = 0
    chain = []
    for s in sentences:
        core = re.sub(r"[«»\"'\-—–.,:;!?…]", "", s).strip().lower()
        words = core.split()
        is_single = (len(words) == 1 and len(core) >= 3
                     and s.rstrip().endswith(".") and core not in ALLOWED_SHORT
                     and re.fullmatch(r"[а-яё]+", core) is not None)
        if is_single:
            run += 1
            chain.append(s.strip())
        else:
            if run >= 3:  # 3+ одиночных подряд = классический AI-стаккато
                n += run
                hits.append("одиночные через точку: " + " ".join(chain[:5]))
            run = 0
            chain = []
    if run >= 3:
        n += run
        hits.append("одиночные через точку: " + " ".join(chain[:5]))
    return n, hits


def count_patterns(text, patterns, label):
    n, hits = 0, []
    low = text.lower()
    for pat in patterns:
        for m in re.finditer(pat, low, flags=re.DOTALL):
            n += 1
            frag = re.sub(r"\s+", " ", low[m.start():m.end()]).strip()
            hits.append(f"{label}: " + frag[:60])
    return n, hits


def count_parallel(sentences):
    n, hits = 0, []
    for i in range(len(sentences) - 1):
        w1, w2 = first_word(sentences[i]), first_word(sentences[i + 1])
        if not w1 or w1 != w2:
            continue
        if len(w1) < 2 or w1 in CONNECTOR_STARTS:
            continue
        n += 1
        hits.append("параллель «%s…/%s…»: %s || %s" % (
            w1, w1, sentences[i][:28], sentences[i + 1][:28]))
    return n, hits


def strip_template_zones(html_text):
    """Убрать зоны шаблона, где типографика приходит не от автора.

    Это шапка/меню/футер (<header>, <nav>, <footer>) и строка хлебных крошек.
    Крошки в вёрстке размечены обычным <p> без своего класса, поэтому опознаём их
    по форме: короткая цепочка со ссылкой и разделителем («Гайды / Название»).
    Нужно ровно для одного: NBSP в этих зонах легален (он из шаблона), а в теле
    текста — замечание. Вайтлист по ЗОНЕ, а не по символу: иначе краснеют 204 из
    210 страниц корпуса.
    """
    t = TEMPLATE_ZONE.sub(" ", html_text)
    h1 = H1_TAG.search(t)
    limit = h1.start() if h1 else CRUMB_FALLBACK_LIMIT

    def drop_crumbs(m):
        if m.start() >= limit:
            return m.group(0)  # ниже H1 короткий абзац со слэшем — это уже проза
        inner = m.group(1)
        if "<a " not in inner.lower():
            return m.group(0)
        txt = NBSP_ANY.sub(" ", re.sub(r"<[^>]+>", " ", inner))
        txt = re.sub(r"\s+", " ", html.unescape(txt)).strip()
        if len(txt) <= CRUMB_MAX_CHARS and CRUMB_SEP.search(txt):
            return " "
        return m.group(0)

    return P_BLOCK.sub(drop_crumbs, t)


def meta_prose(raw):
    """Авторский текст из <title> и meta description/og — его видно в выдаче.

    strip_markup() выбрасывает его вместе с тегом, поэтому для слоя A (типографика)
    достаём отдельно: длинное тире в title — такой же маркер, как в абзаце.
    """
    parts = []
    m = TITLE_TAG.search(raw)
    if m:
        parts.append(re.sub(r"<[^>]+>", " ", m.group(1)))
    for tag in META_TAG.finditer(raw):
        attrs = {}
        for a in META_ATTR.finditer(tag.group(0)):
            val = a.group(2) if a.group(2) is not None else a.group(3)
            attrs[a.group(1).lower()] = val
        key = (attrs.get("name") or attrs.get("property") or "").lower()
        if key in META_KEYS and attrs.get("content"):
            parts.append(attrs["content"])
    return "\n".join(parts)


def count_unicode_markers(text):
    """Слой A методологии (Этап 15): 9 классов юникод-маркеров.

    Вход — ТЕЛО текста (зоны шаблона уже сняты) плюс title/meta. Возвращает
    (hard_total, nbsp_total, by_class, hits):
      hard_total — сумма по восьми блокирующим классам;
      nbsp_total — NBSP вне зон шаблона (SOFT WARN, не блокирует);
      by_class   — {класс: N} по всем девяти классам, включая нулевые не пишем.
    Сущности (&mdash;, &hellip;, &#8212;) раскрываем: закодированный маркер —
    тот же маркер, глазами его не отличить.
    """
    decoded = html.unescape(text)
    by_class, hits = {}, []
    hard_total = 0
    for name, chars, label in UNICODE_HARD_CLASSES:
        n = sum(decoded.count(ch) for ch in chars)
        if n:
            by_class[name] = n
            hard_total += n
            hits.append(f"{label} ×{n}")
    # NBSP считаем по НЕ раскодированному тексту тоже: html.unescape уже перевёл
    # &nbsp; в U+00A0, но числовые формы могли прийти в редком виде — NBSP_ANY
    # покрывает обе записи разом.
    nbsp = len(NBSP_ANY.findall(text))
    if nbsp:
        by_class["nbsp"] = nbsp
        hits.append(f"{NBSP_LABEL} ×{nbsp} в теле текста [soft]")
    return hard_total, nbsp, by_class, hits


def strip_nontext(raw):
    """Убрать то, что не является текстом страницы: style, script, HTML-комментарии.

    Именно там жил ложный след: инлайн-CSS страниц содержит и селектор `.tldr`, и
    комментарий разработчика со словом TL;DR.
    """
    t = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<script\b[^>]*>.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return t


def strip_code_blocks(html_text):
    """Убрать содержимое <pre>/<code> — это код/промпт-примеры, не авторская проза.

    Хвост по решению автора: ось ellipsis красила гейт по многоточиям ВНУТРИ кода страницы
    (примеры промптов в <pre><code>…</code></pre>) — ложные красные на
    /guide-promt-eto/ и /ustanovka-claude/. strip_nontext() снимает только
    style/script/комментарии, pre/code не трогает. Применяется ТОЧЕЧНО к ветке
    юникод-оси (слой A, включая ellipsis) — на axes A-G (антитезы/литобороты/
    канцелярит/…) и на плотность per_1k не влияет: их калибровка (см. шапку файла)
    считана на текущем словаре, трогать его вне этой правки не входит в периметр
    сессии. Многоточие в живой прозе ВНЕ <pre>/<code> остаётся под гейтом — это
    честный сигнал, не баг.
    """
    t = re.sub(r"<pre\b[^>]*>.*?</pre>", " ", html_text, flags=re.S | re.I)
    t = re.sub(r"<code\b[^>]*>.*?</code>", " ", t, flags=re.S | re.I)
    # Хвост r12, по решению автора (слепое пятно того же класса, что r15 у own-evidence).
    # Гейт знал листинг ТОЛЬКО в HTML-форме <pre>/<code>, а стадия draft читает
    # draft.md, где листинг живёт в MARKDOWN-форме: директива ":::pre" движка
    # article_build и забор ```. Итог: дословная цитата лога (а лог сам режет
    # длинные строки символом U+2026) красила ось ellipsis, и «зелёный» гейт
    # получался ТОЛЬКО переписыванием улики - ровно то, что скептик волны r12
    # поймал на guide-claude-brauzernyy-agent как фабрикацию. Правило прежнее и
    # не ослаблено: типографика в ЖИВОЙ ПРОЗЕ вне листинга остаётся под гейтом.
    t = re.sub(r"^:::pre\b[^\n]*\n.*?^:::[ \t]*$", " ", t, flags=re.S | re.M)
    t = re.sub(r"^```[^\n]*\n.*?^```[ \t]*$", " ", t, flags=re.S | re.M)
    return t


def count_label_stamps(raw):
    """H) Одинаковые ярлыки-метки, стоящие ПЕРВЫМ блоком раздела.

    Возвращает (summary, other, hits):
      summary — {метка: N} по семейству резюме (порог 1 на страницу, hard-флаг);
      other   — {метка: N} по любым другим ОДИНАКОВЫМ выделенным ярлыкам (порог 3,
                soft warn); нумерованные семейства («Шаг 3:», «Часть II:») исключены.
    """
    text = strip_nontext(raw)
    summary, other, hits = {}, {}, []

    seen_spans = set()
    for rx in (RE_SUMMARY_STAMP, RE_SUMMARY_LEADIN):
        for m in rx.finditer(text):
            if m.start(1) in seen_spans:
                continue  # одна позиция = одна метка, дубли по позиции снимаем
            seen_spans.add(m.start(1))
            key = re.sub(r"(?:&nbsp;|\s| )+", " ", m.group(1).strip().lower()).strip()
            key = "tl;dr" if key.replace(";", "") == "tldr" else key
            summary[key] = summary.get(key, 0) + 1

    for m in RE_OTHER_STAMP.finditer(text):
        raw_label = re.sub(r"\s+", " ", m.group(1).strip())
        key = raw_label.lower().strip(" .,;!?»«\"'")
        if not key or m.start(1) in seen_spans:
            continue
        if key in SUMMARY_LABELS or key.replace(";", "") == "tldr":
            continue  # уже посчитано в семействе резюме
        if NUMBERED_LABEL.match(key):
            continue  # навигация, а не штамп
        if len(key.split()) > 3 or len(key) > 30:
            continue  # это фраза, а не ярлык
        other[key] = other.get(key, 0) + 1

    total_summary = sum(summary.values())
    if total_summary:
        parts = ", ".join(f"«{k}» ×{v}" for k, v in
                          sorted(summary.items(), key=lambda kv: -kv[1]))
        hits.append(f"семейство резюме: {parts} (порог 1 на страницу)")
    for k, v in sorted(other.items(), key=lambda kv: -kv[1]):
        if v >= 4:
            hits.append(f"одинаковый ярлык «{k}» ×{v} (порог 3, soft warn)")
    return summary, other, hits


def analyse(raw, max_per_1k):
    # ЧИСТАЯ ПРОЗА — единственный вход для всех осей. Без strip_nontext() инлайн-CSS
    # шёл в знаменатель как «слова», а CSS-переменные (--ink: …; --ink-soft: …) —
    # в числитель как «параллельные пары».
    clean = strip_nontext(raw)
    text = strip_markup(clean)
    words = len(re.findall(r"[a-zа-яёA-ZА-ЯЁ]+", text))
    sentences = split_sentences(text)
    if words == 0:
        return None

    a, a_hits = count_antithesis(text, sentences)
    b, b_hits = count_single_word_period(sentences)
    c, c_hits = count_patterns(text, LITERARY, "литоборот")
    d, d_hits = count_patterns(text, CLERICAL, "канцелярит")
    e, e_hits = count_patterns(text, IMPERSONAL, "безличное/крючок")
    g, g_hits = count_parallel(sentences)
    # Слой A: тело текста без зон шаблона и без <pre>/<code> (хвост по решению автора — ellipsis
    # красил код примеров) + авторский текст из title/meta.
    body = strip_markup(strip_template_zones(strip_code_blocks(clean))) + "\n" + meta_prose(raw)
    uni_hard, nbsp, uni_by_class, uni_hits = count_unicode_markers(body)
    st_sum, st_other, st_hits = count_label_stamps(raw)  # ярлыки — по разметке

    marker_total = a + b + c + d + e + g  # H (ярлык) и I (юникод) — отдельные флаги
    per1k = round(marker_total * 1000.0 / words, 2)
    stamps_summary = sum(st_sum.values())
    stamps_other_max = max(st_other.values()) if st_other else 0
    # "dashes" = em/en dash + весь набор тире-двойников Pd (см. DASH_LOOKALIKES) —
    # печатаем и считаем их одной строкой, это один и тот же почерк разными code point.
    dashes = (uni_by_class.get("em-dash", 0) + uni_by_class.get("en-dash", 0)
              + uni_by_class.get("dash-lookalikes", 0))

    return {
        "words": words, "sentences": len(sentences),
        "antithesis": a, "single_word_period": b, "literary": c,
        "clerical": d, "impersonal": e, "parallel": g, "dashes": dashes,
        "unicode_hard": uni_hard, "unicode_nbsp_body": nbsp,
        "unicode_by_class": uni_by_class,
        "stamps_summary": stamps_summary, "stamps_summary_by_label": st_sum,
        "stamps_other_max": stamps_other_max, "stamps_other_by_label": st_other,
        "marker_total": marker_total, "per_1k": per1k, "max_per_1k": max_per_1k,
        "_hits": {"antithesis": a_hits, "single_word_period": b_hits,
                  "literary": c_hits, "clerical": d_hits, "impersonal": e_hits,
                  "parallel": g_hits, "unicode": uni_hits, "label_stamp": st_hits},
    }


def collect_text_files(path):
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        out = []
        for root, _, names in os.walk(path):
            for name in sorted(names):
                if name.lower().endswith(TEXT_EXTS) and not name.startswith("."):
                    out.append(os.path.join(root, name))
        return out
    return []


def run_baseline(target, max_per_1k):
    """Печать сырых плотностей для калибровки по своему корпусу (папка или файл)."""
    files = collect_text_files(target)
    if not files:
        sys.stderr.write(f"в '{target}' нет текстов для калибровки\n")
        sys.exit(3)
    rows = []
    for fp in files:
        try:
            m = analyse(read(fp), max_per_1k)
        except OSError:
            continue
        if m and m["words"] >= 50:
            rows.append((fp, m))
    if not rows:
        sys.stderr.write("файлы слишком короткие для калибровки (< 50 слов)\n")
        sys.exit(3)
    print(f"Калибровка по {len(rows)} файлам (плотность маркеров /1000 слов):")
    total_per1k = 0.0
    for fp, m in rows:
        total_per1k += m["per_1k"]
        print(f"  {m['per_1k']:6.2f}  {os.path.basename(fp)}  "
              f"(слов {m['words']}, тире {m['dashes']})")
    avg = round(total_per1k / len(rows), 2)
    print(f"\nСредняя плотность по корпусу: {avg} /1k")
    print(f"Рекомендация: max_per_1k ≈ {round(avg + 2, 1)} "
          f"(чуть выше вашего живого письма, чтобы не ловить ложные срабатывания).")
    sys.exit(0)


def parse_args():
    p = argparse.ArgumentParser(
        prog="ai-cadence-check.py",
        description="Детектор AI-почерка в русском тексте: антитезы «не X, а Y», "
                    "«это не А. это Б», одиночные слова через точку, литобороты, "
                    "канцелярит, безличные конструкции, длинное тире, параллелизмы. "
                    "Плотность на 1000 слов против порога.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Порог: config.yaml (tools.cadence.max_per_1k) → флаг CLI → дефолт 8.0. "
               "Калибровка под себя: --baseline-dir <ваша_папка>. "
               "Коды выхода: 0=CLEAN, 1=REVIEW (hard), 2=SOFT WARN, 3=ошибка.",
    )
    p.add_argument("article", nargs="?", help="файл статьи для проверки")
    p.add_argument("--config", default=None,
                   help="путь к config.yaml (по умолчанию ищется ./config.yaml)")
    p.add_argument("--max-per-1k", type=float, default=None,
                   help="порог суммарной плотности маркеров на 1000 слов")
    p.add_argument("--baseline", metavar="FILE",
                   help="режим калибровки: печать плотностей одного файла")
    p.add_argument("--baseline-dir", metavar="DIR",
                   help="режим калибровки: печать плотностей всех текстов в папке "
                        "(например, config.voice.source)")
    p.add_argument("--json", action="store_true", help="вывод машинно-читаемым JSON")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = cfgmod.load_config(args.config or cfgmod.find_config())
    max_per_1k = args.max_per_1k if args.max_per_1k is not None \
        else float(cfgmod.get(cfg, "tools.cadence.max_per_1k", DEFAULT_MAX_PER_1K))

    # режим калибровки
    base_target = args.baseline_dir or args.baseline
    if not base_target and args.baseline_dir is None and args.baseline is None:
        # возможно, папка калибровки задана только в конфиге — но запускать её
        # самостоятельно не будем: калибровка только по явному флагу
        pass
    if args.baseline_dir or args.baseline:
        run_baseline(args.baseline_dir or args.baseline, max_per_1k)

    if not args.article:
        sys.stderr.write("укажите файл статьи (или --baseline-dir для калибровки). "
                         "Подробнее: --help\n")
        sys.exit(3)

    try:
        raw = read(args.article)
    except OSError as e:
        sys.stderr.write(f"ошибка чтения: {e}\n")
        sys.exit(3)

    m = analyse(raw, max_per_1k)
    if m is None:
        sys.stderr.write("пустой файл\n")
        sys.exit(3)

    fail_density = m["per_1k"] > max_per_1k
    fail_unicode = m["unicode_hard"] > 0           # hard: слой A без NBSP
    fail_dashes = m["dashes"] > 0                  # подмножество слоя A, печатаем отдельно
    fail_stamps = m["stamps_summary"] > 1          # hard: семейство резюме, порог 1
    # Ярлык-повтор: hard при >=4. Тот же критерий и тот же вердикт, что в
    # structure-check.py — одна ось не может давать два разных приговора.
    fail_stamps_other = m["stamps_other_max"] >= 4
    warn_nbsp = m["unicode_nbsp_body"] > 0         # soft: NBSP вне зон шаблона
    fails = []
    if fail_density:
        fails.append("density")
    if fail_unicode:
        fails.append("unicode")
    if fail_stamps:
        fails.append("label-stamp")
    if fail_stamps_other:
        fails.append("label-stamp-other")
    warns = ["nbsp-body"] if warn_nbsp else []
    # 0 = чисто, 1 = HARD BLOCK, 2 = SOFT WARN, 3 = ошибка (Этап 15 методологии)
    exit_code = 1 if fails else (2 if warns else 0)
    verdict = "REVIEW" if fails else ("SOFT WARN" if warns else "CLEAN")

    if args.json:
        out = {k: v for k, v in m.items() if k != "_hits"}
        out["article"] = args.article
        out["verdict"] = verdict
        out["fails"] = fails
        out["warns"] = warns
        out["exit_code"] = exit_code
        out["examples"] = {k: v[:6] for k, v in m["_hits"].items() if v}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(exit_code)

    print(f"AI-каденция: {verdict}  ({m['words']} слов, {m['sentences']} предложений)")
    print(f"  антитезы «не X,а Y»/«это не…это»/«а не…» : {m['antithesis']:3d}")
    print(f"  одиночные слова через точку              : {m['single_word_period']:3d}")
    print(f"  литобороты «эпоха X закончилась»…        : {m['literary']:3d}")
    print(f"  канцелярит «таким образом»…              : {m['clerical']:3d}")
    print(f"  безличное/крючки «вы узнаете»…           : {m['impersonal']:3d}")
    print(f"  параллельные пары (одинак. старт)        : {m['parallel']:3d}")
    print(f"  ─ сумма маркеров                         : {m['marker_total']:3d}  "
          f"= {m['per_1k']:.2f} /1k  (порог ≤{max_per_1k}){'  ! ПРЕВЫШЕНО' if fail_density else ''}")
    print(f"  тире и двойники (—/–/Pd-блок) [hard-флаг] : {m['dashes']:3d}"
          f"{'  ! ЕСТЬ — заменить на дефис' if fail_dashes else ''}")
    other_uni = ", ".join(f"{k} ×{v}" for k, v in m["unicode_by_class"].items()
                          if k not in ("em-dash", "en-dash", "dash-lookalikes", "nbsp"))
    print(f"  юникод слоя A, прочее [hard-флаг]        : "
          f"{m['unicode_hard'] - m['dashes']:3d}"
          f"{('  ! ' + other_uni) if other_uni else ''}")
    print(f"  NBSP вне шапки/крошек [SOFT WARN]        : "
          f"{m['unicode_nbsp_body']:3d}"
          f"{'  ! в теле текста' if warn_nbsp else ''}")
    stamp_note = ""
    if fail_stamps:
        by = m["stamps_summary_by_label"]
        top = ", ".join(f"«{k}» ×{v}" for k, v in
                        sorted(by.items(), key=lambda kv: -kv[1]))
        stamp_note = f"  ! ПОВТОР — {top} (порог 1 на страницу)"
    print(f"  метка-резюме, повтор [hard-флаг]         : {m['stamps_summary']:3d}"
          f"{stamp_note}")
    if fail_stamps_other:
        by = m["stamps_other_by_label"]
        top = ", ".join(f"«{k}» ×{v}" for k, v in
                        sorted(by.items(), key=lambda kv: -kv[1]) if v >= 4)
        print(f"  одинаковый ярлык, повтор [hard-флаг]     : {top} (порог 3)")
    if fails or warns:
        print("\n  Примеры (первые по сработавшим осям):")
        order = ["antithesis", "single_word_period", "literary", "clerical",
                 "impersonal", "parallel", "unicode", "label_stamp"]
        for key in order:
            hits = m["_hits"].get(key, [])
            # показываем примеры, если ось вносит вклад в вердикт
            if (fail_density and key not in ("unicode", "label_stamp") and hits) or \
               ((fail_unicode or warn_nbsp) and key == "unicode" and hits) or \
               ((fail_stamps or fail_stamps_other) and key == "label_stamp" and hits):
                for h in hits[:5]:
                    print("   • " + h)
    else:
        print("\n  В пределах порога. Финальная вычитка — за человеком.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
