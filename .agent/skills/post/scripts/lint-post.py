#!/usr/bin/env python3
"""
lint-post.py - детерминированный линтер поста для скилла `post`.

Закрывает класс ошибок "агент заявил проверку, которой не делал".
Проверяет ТОЛЬКО machine-checkable правила (то, что ловится кодом).
Семантику (метафоры, голос, живость) скрипт НЕ проверяет - это остаётся
на Gate Evidence Report в workflow/04-review.md с цитатами.

Прецедент 2026-05-29: пост выдан с точками в конце абзацев и без форматирования,
при этом был заявлен статус "3 слоя пройдено". Гейты 4.1.6.5 и 4.6.3 не прогонялись.

Usage:
    python3 lint-post.py <file>
    python3 lint-post.py <file> --max 2500 --min 1500
    cat post.txt | python3 lint-post.py - --max 1500

Exit code: 0 если все HARD-правила PASS, 1 если хоть один FAIL.
"""

import sys
import re
import os
import json
import glob
import argparse
import datetime
import unicodedata


# ===========================================================================
# ВНЕШНИЙ СЛОВАРЬ ВЛАДЕЛЬЦА (изоляция личного от раздаваемого).
# Скилл раздаётся ученикам целиком, поэтому запреты, завязанные на конкретный
# запуск и позиционирование владельца (запретное слово события, снятый концепт,
# запретный класс возражений), а также личные имена факт-базы, НЕ живут в этом
# файле. Они лежат в .business (не раздаётся) и читаются УСЛОВНО.
#   нет файла / битый JSON / нет записи -> пустые списки -> проверка печатает
#   [PASS] с нулём и никого не блокирует. У ученика линтер работает как обычно.
# Путь: env POST_OWNER_LEXICON -> .business/... -> ~/.business/...
# ===========================================================================
OWNER_LEXICON_CANDIDATES = (
    ".business/processes/lint-owner-lexicon.json",
    "~/.business/processes/lint-owner-lexicon.json",
)


def _load_owner_lexicon():
    paths = []
    env = os.environ.get("POST_OWNER_LEXICON")
    if env:
        paths.append(env)
    paths.extend(OWNER_LEXICON_CANDIDATES)
    for p in paths:
        fp = os.path.expanduser(p)
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}          # битый файл = как будто его нет, линтер не падает
    return {}


OWNER_LEXICON = _load_owner_lexicon()


def owner_banned_patterns(entry_id):
    """Регексы одного запрета владельца. Нет словаря/записи -> [] (проверка спит)."""
    for e in (OWNER_LEXICON.get("banned_words") or []):
        if isinstance(e, dict) and e.get("id") == entry_id:
            pats = e.get("patterns")
            if not pats and e.get("pattern"):
                pats = [e["pattern"]]
            return [p for p in (pats or []) if p]
    return []


def owner_banned_label(entry_id, default):
    """Человекочитаемое имя запрета для вывода. Берётся из словаря владельца,
    чтобы в раздаваемом коде не осталось ни самого слова, ни его обоснования."""
    for e in (OWNER_LEXICON.get("banned_words") or []):
        if isinstance(e, dict) and e.get("id") == entry_id:
            return e.get("label") or default
    return default


def owner_banned_note(entry_id):
    """Короткая приписка «почему нельзя» из словаря владельца. Нет - пусто."""
    for e in (OWNER_LEXICON.get("banned_words") or []):
        if isinstance(e, dict) and e.get("id") == entry_id:
            return e.get("fail_note") or ""
    return ""


def _owner_scan(entry_id, text, pad=25):
    """Общий сканер: собирает фрагменты вокруг совпадений регексов владельца.

    🔴 п.5 скептик Р3 (по решению автора): юникод-нормализация жила в _strip_md_plain,
    а сюда приходил СЫРОЙ text - все три запрета владельца снимались одной
    латинской буквой внутри слова («мaрафон» давал [PASS] 0). Нормализуем на
    входе (та же единая точка _strip_md_plain, что у остальных словарей: она
    же снимает markdown, т.е. «мар**афон**» тоже больше не обход), а сами
    регексы делаем слепыми к е/ё."""
    text = _strip_md_plain(text)
    rxs = []
    for pat in owner_banned_patterns(entry_id):
        try:
            rxs.append(re.compile(_yo_insensitive(pat), re.IGNORECASE))
        except re.error:
            continue           # кривой регекс в личном словаре не валит линтер

    def _scan(t):
        out = []
        for rx in rxs:
            for m in rx.finditer(t):
                s = max(0, m.start() - pad)
                out.append(t[s:m.end() + pad].replace("\n", " ").strip())
        return out

    hits = _scan(text)
    # 🔴 С13 скептик Р4: «мара-фон» и «мара_ф_он» разрывали слово разделителем и
    # снимали запрет. Второй проход идёт по копии БЕЗ внутрисловных разделителей,
    # находки вычитаются из первого прохода - честный текст не удваивается,
    # а легитимные дефисные слова («по-настоящему», «мастер-класс») в словарь
    # запретов всё равно не попадают.
    glued = _strip_inword_separators(text)
    if glued != text:
        hits += _dedup_second_pass(hits, _scan(glued),
                                   lambda h: _INWORD_SEP_RE.sub("", h).lower())
    return hits


def read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_paragraphs(text):
    # Абзац = блок, разделённый пустой строкой
    raw = re.split(r"\n\s*\n", text.strip())
    return [p for p in (b.strip() for b in raw) if p]


def check_paragraph_periods(paragraphs):
    """4.1.6.5 - HARD. Абзац не должен заканчиваться точкой.
    Допустимо: …, ?, эмодзи, :, ничего, ! (если общий счёт ! <= 1)."""
    failures = []
    for i, p in enumerate(paragraphs, 1):
        stripped = p.rstrip()
        if not stripped:
            continue
        # многоточие - ок
        if stripped.endswith("…") or stripped.endswith("..."):
            continue
        if stripped.endswith("."):
            tail = stripped[-60:].replace("\n", " ")
            failures.append((i, tail))
    return failures


def check_em_dash(text):
    """4.1.1 / 4.8.8 - HARD. Em-dash '—' внутри строки запрещён."""
    hits = []
    for ln, line in enumerate(text.splitlines(), 1):
        # разрешено только в самом начале строки как маркер списка
        if "—" in line:
            stripped = line.lstrip()
            if not stripped.startswith("—"):
                hits.append((ln, line.strip()[:70]))
            elif stripped.count("—") > 1:
                hits.append((ln, line.strip()[:70]))
    return hits


def check_exclamations(text):
    """4.1.4 - WARNING если > 1."""
    return text.count("!")


def check_lists(text):
    """4.1.5 - WARNING если > 1 list-блок."""
    bullet = re.findall(r"(?m)^\s*[-•*]\s", text)
    numbered = re.findall(r"(?m)^\s*\d+\.\s", text)
    return len(bullet) + len(numbered)


def check_no_rich_entities(text):
    """HARD. Rich-разметка запрещена: формат выдачи = донорский.

    Правка владельца  (дважды): «доп rich слой форматирования вообще не
    согласуется с новым каноном - его нужно убирать», «формат движка нового
    должен выдавать как у Донор-Б и Донор-А». Разрешено ровно: чистый текст,
    эмодзи + `**жирный заголовок целиком**`, жирные акценты по профилю цели,
    точечный курсив (PS-ACTION - вся строка), воздух, скобки-улыбки. Всё
    остальное - брак формата, а не «богатство».

    Ловим (каждое - FAIL):
      - строка-таблица `| a | b |` (>=3 пайпа в строке, начинающейся с `|`)
      - чек-бокс в НАЧАЛЕ строки ☐/☑/✅/✔/▢/⬜ или `- [ ]` (порог 1, не 2)
      - заголовки markdown `#`..`######` (H1-H6) внутри тела
      - спойлер `||...||` и `<tg-spoiler>`
      - подчёркивание HTML-тегом `<u>`/`<ins>` (underline-интент)
      - highlight/жёлтый маркер `==фраза==`, `<mark>`
      - центрирование `<center>`, `align="center"`, `[center]`

    НЕ ловим осознанно:
      - `__текст__` - в корпусе доноров это КУРСИВ клиентского markdown
        Telegram (donor-1455/1579/433 несут его штатно), а не underline;
        admission доноров важнее буквы формулировки.
      - `>` цитата-блок - уже живёт анти-паттерном №5 (ap5_quote_block_razbor),
        дубль здесь дал бы два FAIL на одном дефекте и завалил бы donor-1455.
    """
    hits = []

    table_rows = [ln for ln in text.splitlines()
                  if ln.strip().startswith("|") and ln.count("|") >= 3]
    if table_rows:
        hits.append(("таблица", f"{len(table_rows)} строк-таблицы: {table_rows[0].strip()[:60]}"))

    # 🔴 ПОРОГ 1 (скептик-раунд 4, по решению автора, п.8). Было >=2 «списком»: ОДИН чек-бокс
    # в начале строки - тот же rich-брак, а проходил. Якорь ^ обязателен: ✅ ВНУТРИ
    # строки (донорская «галочка по тексту») не ловится и ловиться не должна.
    checkbox_rows = re.findall(r"(?m)^\s*(?:[☐☑✅✔▢⬜⬛]|[-*]\s\[[ xX]\])\s*\S", text)
    if checkbox_rows:
        hits.append(("чек-боксы", f"{len(checkbox_rows)} строк(а) с чек-боксом в начале"))

    # 🔴 H1-H6 (было H1-H3): `####`/`#####`/`######` - такой же markdown-заголовок,
    # донорский формат их не знает, а прежний диапазон их пропускал.
    headings = re.findall(r"(?m)^\s*#{1,6}\s+\S.*$", text)
    if headings:
        hits.append(("заголовок H1-H6", f"{len(headings)}: {headings[0].strip()[:60]}"))

    spoilers = re.findall(r"\|\|[^\n|]+\|\||<tg-spoiler>", text)
    if spoilers:
        hits.append(("спойлер", f"{len(spoilers)}: {spoilers[0][:40]}"))

    underline = re.findall(r"</?(?:u|ins)>", text)
    if underline:
        hits.append(("подчёркивание", f"{len(underline)} тегов <u>/<ins>"))

    highlight = re.findall(r"==[^=\n]+==|</?mark>", text)
    if highlight:
        hits.append(("highlight/жёлтый маркер", f"{len(highlight)}: {highlight[0][:40]}"))

    centering = re.findall(r"</?center>|align\s*=\s*[\"']?center|\[/?center\]", text, re.I)
    if centering:
        hits.append(("центрирование", f"{len(centering)}: {centering[0][:40]}"))

    return hits


# --- ЭМОДЗИ: ОДИН НАБОР ДИАПАЗОНОВ НА ВЕСЬ ФАЙЛ (по решению автора).
# Было: класс символов жил инлайном внутри check_formatting_devices, и новому
# счётчику элементов пришлось бы завести ВТОРОЙ - две мерки одного знака в
# одном линтере. Набор вынесен сюда без единого изменения состава: ⬀-⯿ это
# U+2B00-2BFF, ✀-➿ (U+2700-27BF) целиком лежит внутри U+2600-27BF.
_EMOJI_RANGES_BASE = ("\U0001F300-\U0001FAFF\U00002600-\U000027BF"
                      "\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF")
# ровно то, что считал check_formatting_devices до выноса (селектор варианта
# U+FE0F внутри класса сохранён - поведение приёма 4.0.3 не тронуто)
_EMOJI_CHAR_CLASS = _EMOJI_RANGES_BASE + "️"
# счётчик элементов формы: тот же набор МИНУС селектор варианта (он модификатор,
# а не знак) ПЛЮС блок U+2300-23FF (⌛ ⏰ ⏳) - так эмодзи считал замер корпуса
# по решению автора, по которому взяты пол 3 и цель 6
ELEMENT_EMOJI_CLASS = _EMOJI_RANGES_BASE + "\U00002300-\U000023FF"


def check_formatting_devices(text):
    """4.0.3 - WARNING если приёмов выразительного форматирования мало.
    Прецедент 2026-05-29: пост выдан без жирного/курсива/капса - голая
    простыня. Telegram поддерживает разметку, её надо использовать по смыслу.

    🔴 по решению автора: спойлер / HTML-underline / HTML-спойлер убраны из списка
    приёмов - rich-слой снесён правкой владельца, эти сущности теперь HARD-брак
    (check_no_rich_entities), а не «богатство формата».

    🔴 по решению автора: hard_fail здесь по-прежнему СНЯТ (квота «≥4 приёма» отменена
    каноном §8.2), и это больше не дыра: настоящую защиту от голой простыни
    несёт check_element_types ниже (HARD-пол 3 разных типа элементов, замер
    корпуса по решению автора). Один источник правды - там, здесь остаётся видимость."""
    devices = {}
    # жирный **...** (Telegram client markdown — ДВЕ звезды, ручной постинг §по решению автора)
    devices["жирный **"] = len(re.findall(r"\*\*[^*\n]+\*\*", text))
    # жирный *...* (legacy одна звезда — backward compat для старых вызовов/бота)
    devices["жирный *"] = len(re.findall(r"(?<!\*)\*(?!\*)[^*\n]+\*(?!\*)", text))
    # курсив _..._ ИЛИ __...__ (Telegram client: __курсив__)
    devices["курсив _/__"] = (len(re.findall(r"(?<![\w_])_[^_\n]+_(?![\w_])", text))
                              + len(re.findall(r"__[^_\n]+__", text)))
    # HTML-разметка (§35 канона: пост выдаётся в HTML <b>/<i>, НЕ markdown **).
    # Telegram parse_mode=HTML — это предписанный формат выдачи, его и считаем приёмом.
    devices["HTML жирный <b>"] = len(re.findall(r"<b>.+?</b>", text, re.S))
    devices["HTML курсив <i>"] = len(re.findall(r"<i>.+?</i>", text, re.S))
    # КАПС-слова (>=3 заглавных подряд)
    devices["КАПС"] = len(re.findall(r"\b[А-ЯA-ZЁ]{3,}\b", text))
    # троеточие
    devices["троеточие"] = text.count("…") + len(re.findall(r"\.\.\.", text))
    # эмодзи (точечный приём в концах акцентных абзацев / заголовке / финале — §32 канона)
    devices["эмодзи"] = len(re.findall("[" + _EMOJI_CHAR_CLASS + "]", text))
    # NB: «одно слово на строку» НЕ считается приёмом форматирования.
    # Прецедент 2026-05-29: это поощряло рубку единого предложения на staccato
    # (главный AI-tic). Выразительность достигается разметкой, а не дроблением.
    total = sum(1 for v in devices.values() if v > 0)
    return devices, total


# ---------------------------------------------------------------------------
# ЭЛЕМЕНТЫ ФОРМЫ (по решению автора, разнос владельца: «нет элементов и выделений как
# у доноров... вообще нет никаких прикольных элементов... измени движок чтобы
# элементы копи были забраны и движок скилла их каждый раз давал мне»).
#
# ЗАМЕР (element-census.py, по решению автора): 608 донорских постов + 12 принятых
# владельцем green-ivan + 3 эталона A-telegram, 15 категорий элементов.
#   доноры    - медиана 6 разных типов на пост, q1 = 4
#   green-ivan- медиана 5, МИНИМУМ 3 (ivan-final-0/1/2: жирный + прямая речь + вопрос)
#   A-telegram- минимум 4
# Отсюда ДВА уровня, и разведение принципиальное (тот же закон калибровки, что
# у Д110): HARD ставится ТОЛЬКО там, где его переживает весь зелёный корпус, -
# это пол 3. Медиана доноров 6 остаётся ЦЕЛЬЮ (WARN): green её не держит
# (медиана 5), а правило, валящее зелёный, в этом файле запрещено.
#
# 🔴 ПЕРЕМЕР по решению автора ПОСЛЕ СТРОГИХ ДЕТЕКТОРОВ (Д1 жюри, `measure_sig.py`):
#   доноры (608)     min 0 · q1 4 · медиана 6 · q3 8 · max 13 · с нулём 6%
#   green-ivan (12)  min 2 · медиана 4 · max 5 · с нулём 0%
#   A-telegram (3)   min 5 · медиана 7 · max 8
# Пол 3 и цель 6 ОСТАВЛЕНЫ БЕЗ ИЗМЕНЕНИЙ, хотя green просел с min 3 до min 2
# (`ivan-final-1/2`). Причина - решение по калибровке по решению автора: владелец
# ПРЯМО забраковал уровень текстуры своих же выданных постов, поэтому на оси
# текстуры green-корпус расакцептован и порог по нему не понижается. Две
# просевшие фикстуры внесены в манифест-исключение (см. ELEMENTS_SIGNATURE ниже
# и `ELEMENT_FLOOR_LEGACY_FIXTURES` в `tests/run-tests.py`).
# ---------------------------------------------------------------------------

ELEMENT_TYPES_FLOOR = 3    # HARD, = минимум зелёного корпуса на замере по решению автора (см. перемер выше)
ELEMENT_TYPES_TARGET = 6   # WARN, = медиана доноров (строгий перемер по решению автора дал ту же 6)

# ---------------------------------------------------------------------------
# 🔴 СИГНАТУРНЫЙ ПОЛ (по решению автора, находка владельца «докажи, что движок правда
# применяет копирайтинг»). ДЕФЕКТ ПЕРВОЙ РЕДАКЦИИ ЭТОГО ГЕЙТА: счёт «типов из
# 15» оказался бесплатным. Шесть категорий несёт ЛЮБОЙ нормальный пост, потому
# что их ставит не копирайтер, а сам канон формы: жирный (заголовок обязан быть
# жирным), эмодзи (хук обязан начинаться эмодзи), вопрос (любой «?»), скобка
# `))` (живой слой, отдельный HARD выше), панч-строка (любая строка ≤25 знаков,
# например тот же короткий вопрос), эмодзи-хвост (любой абзац, кончающийся
# эмодзи). Живой репро: пост, который владелец разнёс как стерильный, набрал
# ими 6 типов и получил `[PASS] элементы формы: 6 типов из 15` - гейт похвалил
# ровно тот текст, ради которого писался.
#
# Отсюда ВТОРОЙ пол, на ПОДМНОЖЕСТВЕ: элементы, которые в посте появляются
# только решением автора. Замер по решению автора тем же методом:
#   green-ivan (12)  min 1 · медиана 2 · max 3 · постов с нулём 0%
#   A-telegram (3)   min 2 · медиана 2 · max 4 · постов с нулём 0%
#   доноры (608)     медиана 2 · q3 3 · max 8
#   стерильный пост владельца: 0        пересобранный: 4
# HARD-пол = 1: его переживает ВЕСЬ зелёный корпус (min 1, ноль постов с нулём)
# и он валит стерильный текст. Цель 2 = медиана и green, и доноров (WARN).
# ---------------------------------------------------------------------------
# 🔴 РЕДАКЦИЯ 3 (по решению автора, Д1+Д3 финального жюри). ДВЕ ПРАВКИ НАБОРА И ПОЛА:
#
# Д3 - `quote_block` ВЫВЕДЕН ИЗ НАБОРА (было 9 элементов, стало 8). Причина -
# конфликт совета и запрета: линтер советовал поставить цитата-блок (20% верха),
# а `formatting-skeleton.md` §4 держит на него потолок 0 с пометкой HARD-запрет,
# и анти-паттерн R3 №5 (`ap5_quote_block_razbor`) валит его в классе `razbor`.
# Пол обязан быть ДОСТИЖИМ в любом классе: элемент, который писателю запрещено
# ставить, не может быть членом множества «поставь хотя бы одно». Оставлять его
# в наборе и молча не советовать - значит держать в поле `<N>/9` знаменатель, на
# который писатель повлиять не может. В 15 категориях счётчика (перепись формы,
# не цель) `quote_block` остался: доноры его несут, мерить корпус надо честно.
#
# Д1 - ДЕТЕКТОРЫ СТАЛИ СТРОГИМИ, поэтому числа замера ниже ПЕРЕМЕРЕНЫ (по решению автора,
# `measure_sig.py`, тот же метод: живой модуль + три корпуса):
#   green-ivan (12)  min 0 · медиана 1 · q3 1 · max 2 · постов с нулём 42% (5 из 12)
#   A-telegram (3)   min 2 · медиана 2 · max 4 · постов с нулём 0%
#   доноры (608)     min 0 · медиана 2 · q3 3 · max 7 · постов с нулём 27%
#   стерильный пост владельца 0 · все 7 имитаций жюри 0
#
# 🔴 ПОЧЕМУ ПОЛ НЕ ОПУЩЕН ПОД GREEN. Обычный закон движка «HARD только там, где
# green не падает» на ЭТОЙ оси не действует. Владелец по решению автора ПРЯМО забраковал
# уровень текстуры собственных выданных постов («нет элементов и выделений как у
# доноров, вообще нет никаких прикольных элементов»), то есть green-корпус по
# оси текстуры им РАСАКЦЕПТОВАН - калибровать по нему значит цементировать ровно
# то, за что был разнос. Пол остаётся 1: это минимальное, что валит стерильный
# текст и все 7 имитаций жюри. Зелёные фикстуры, падающие на строгом счёте,
# порог НЕ понижают - они вынесены в явный манифест-исключение
# `ELEMENT_FLOOR_LEGACY_FIXTURES` (`tests/run-tests.py`), остальные гейты по ним
# работают как раньше.
ELEMENTS_SIGNATURE = [
    "caps_word", "italic", "dash_list", "numbered_list", "arrow",
    "direct_speech", "colon_reveal", "stretch",
]
# Элементы, которые счётчик мерит, но советовать писателю ЗАПРЕЩЕНО (см. Д3).
ELEMENTS_NEVER_ADVISE = {"quote_block"}
ELEMENT_SIG_FLOOR = 1    # HARD, минимальное, что валит стерильный текст и все 7 имитаций
ELEMENT_SIG_TARGET = 2   # WARN-цель = медиана 608 доноров на СТРОГОМ счёте (замер)

# Доля 608 доноров, несущих сигнатурный элемент, на СТРОГОМ счёте (замер,
# новыми детекторами). Не порог: по нему сортируется «поставь хотя бы одно»,
# чтобы писателю первым называли то, что доноры делают чаще всего.
ELEMENT_SIG_STRICT_SHARE = {
    "caps_word": 49, "italic": 45, "dash_list": 23, "numbered_list": 10,
    "arrow": 12, "direct_speech": 17, "colon_reveal": 21, "stretch": 5,
}

ELEMENTS_15 = [
    "bold", "caps_word", "stretch", "arrow", "dash_list", "numbered_list",
    "direct_speech", "question", "italic", "emoji_tail",
    "emoji_count", "short_punch", "quote_block", "colon_reveal",
]

ELEMENT_LABELS = {
    "bold": "жирный", "caps_word": "КАПС", "stretch": "растяжка гласной",
    "arrow": "стрелка", "dash_list": "тире-опись", "numbered_list": "нумерация",
    "direct_speech": "прямая речь", "question": "вопрос",
    "italic": "курсив",
    "emoji_tail": "эмодзи-хвост абзаца", "emoji_count": "эмодзи",
    "short_punch": "панч-строка", "quote_block": "цитата-блок",
    "colon_reveal": "двоеточие-раскрытие",
}

# Доля постов ВЕРХА, несущих элемент (замер). Источник у каждой доли
# назван, потому что срезы разные и смешивать их молча нельзя:
#   FWD - верх доноров цели forwards (по нему же взяты профильные WARN ниже)
#   ДОН - все 608 донорских постов
# Числа НЕ пороги: по ним сортируется список «чего не хватает», чтобы писателю
# первым называли то, что у верха встречается чаще всего.
ELEMENT_TOP_SHARE = {
    "bold": 96,            # FWD
    "emoji_count": 85,     # FWD
    "short_punch": 69,     # ДОН
    "question": 67,        # FWD
    "italic": 58,          # FWD
    "caps_word": 52,       # FWD
    "dash_list": 52,       # FWD
    "emoji_tail": 51,      # ДОН
    "colon_reveal": 27,    # ДОН
    "direct_speech": 25,   # ДОН
    "quote_block": 20,     # FWD
    "arrow": 18,           # FWD
    "numbered_list": 12,   # ДОН
    "stretch": 5,          # ДОН
}

_EL_BOLD = re.compile(r"\*\*[^*]+\*\*|<b>.*?</b>", re.S)
_EL_CAPS = re.compile(r"\b[А-ЯЁ]{3,}\b")
_EL_STRETCH = re.compile(r"([аеёиоуыэюя])\1{2,}", re.IGNORECASE)
_EL_ARROW = re.compile(r"->|—>|→|⟶|=>")
_EL_ITALIC = re.compile(
    r"__[^_]+__|<i>.*?</i>|(?<!\*)\*(?!\*)[^*\n]+(?<!\*)\*(?!\*)", re.S)
_EL_GUILLEMET = re.compile(r"«[^»]{15,}»")
_EL_SPEECH_VERBS = re.compile(
    r"\b(сказал\w*|говор\w*|спросил\w*|ответил\w*|подума\w*|воскликнул\w*|"
    r"прошептал\w*|крикнул\w*|произнес\w*|произнёс\w*|добавил\w*|заметил\w*|"
    r"признал\w*)\b",
    re.IGNORECASE,
)
_EL_EMOJI = re.compile("[" + ELEMENT_EMOJI_CLASS + "]")
_EL_KEYCAP = re.compile(r"[0-9]️?⃣|\U0001F51F")
_EL_END_EMOJI = re.compile(
    "(?:[" + ELEMENT_EMOJI_CLASS + r"]|[0-9]️?⃣|\U0001F51F)[️‍]*$")

# ---------------------------------------------------------------------------
# 🔴 СТРОГИЕ ДЕТЕКТОРЫ (по решению автора, Д1 финального жюри). ДЕФЕКТ ВТОРОЙ РЕДАКЦИИ
# ГЕЙТА: сигнатурный пол снимался ОДНИМ ФОРМАЛЬНЫМ ТОКЕНОМ. Живые улики жюри:
#   · 7 из 7 синтетических имитаций брали пол (одинокий курсив · служебное
#     двоеточие · нумерация из ОДНОГО пункта · кавычки вокруг оборота · стрелка
#     внутри 👉-строки · КАПС = «МСК» · тире-опись из ОДНОГО пункта)
#   · в зелёном корпусе владельца 8 постов из 12 держали сигнатурный пол
#     строкой `МСК` (таймзона в служебной строке эфира), 9 из 12 - кавычками
#     вокруг обычного оборота, а не репликой
# Значит счётчик мерил НЕ решение автора, а служебную типографику. Пять правок
# ниже обесценивают имитацию ВНУТРИ счётчика, состав 15 категорий не меняя.
# ---------------------------------------------------------------------------

# (1) КАПС. Фактическая аббревиатура - не выделение. Стоп-лист собран не на
# глаз: греп КАПС-токенов по green-ivan (там КАПС ровно один - `МСК`, 7 файлов
# из 12) и по 608 донорам (США 23 · СНГ 14 · НДС 4 · КМС 4 - остальное реальное
# выделение вроде БЕЗ/КОНТЕНТ/СМОТРЕТЬ). Латиница в счёт не идёт вовсе (регекс
# кириллический), поэтому BMW/M3/SEO/GPT не считаются по построению - латинские
# записи в списке держат сам список читаемым и страхуют смену регекса.
_EL_CAPS_STOP = {
    # время/гео
    "МСК", "ГМТ", "США", "РФ", "СНГ", "СССР", "ОАЭ", "ЕС", "МКАД", "СПБ",
    # орг-формы и госорганы
    "ООО", "ИП", "АО", "ЗАО", "ПАО", "НДС", "ОФД", "ЕГЭ", "МВД", "ФНС", "ЖКХ",
    "МФЦ", "ГИБДД", "ЦБ", "ЗАГС",
    # медиа/техника (кириллические записи)
    "СМИ", "ИИ", "СЕО", "ВПН", "КМС", "ТЗ", "ПО", "БД", "ОС", "ПК", "СМС",
    # латиница - на случай смены регекса на двухалфавитный
    "AI", "GPT", "LLM", "API", "SEO", "SMM", "HR", "PDF", "URL", "UTM", "TG",
    "IG", "VPN", "CRM", "CTA", "CTR", "ROI", "MVP", "SaaS", "USD", "EUR",
    "BMW", "M3", "IT", "UX", "UI", "KPI", "B2B", "B2C",
}
_EL_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")


def _el_caps_is_initials(word, text, start):
    """КАПС собран из первых букв СОСЕДНИХ слов («Единый Государственный
    Экзамен (ЕГЭ)») - это расшифровка аббревиатуры, а не выделение. Смотрим
    ровно два места: n слов вплотную ДО и n слов вплотную ПОСЛЕ токена."""
    n = len(word)
    before = _EL_WORD_RE.findall(text[max(0, start - 100):start])[-n:]
    after = _EL_WORD_RE.findall(text[start + n:start + n + 100])[:n]
    for run in (before, after):
        if len(run) == n and "".join(w[0] for w in run).upper() == word:
            return True
    return False


def _el_caps_hits(text):
    """Строгий КАПС: кириллическое слово ≥3 букв, НЕ в стоп-листе фактических
    аббревиатур, НЕ аббревиатура из первых букв соседних слов. `МСК+3` снимается
    самим стоп-листом (`МСК` уже в нём), отдельного правила на цифру рядом не
    нужно - регекс цифру в токен не берёт."""
    hits = []
    for m in _EL_CAPS.finditer(text):
        w = m.group(0)
        if w in _EL_CAPS_STOP:
            continue
        if _el_caps_is_initials(w, text, m.start()):
            continue
        hits.append(w)
    return hits


# (2) ОПИСЬ И НУМЕРАЦИЯ. Одиночная строка с тире или «1.» - не опись, а строка
# текста. Засчитывается только блок от ДВУХ пунктов подряд (пустая строка между
# пунктами блок не рвёт - доноры дают воздух внутри описи, проза рвёт).
_EL_DASH_ITEM = re.compile(r"^[-–—•]\s")
_EL_NUM_ITEM = re.compile(r"^\d+[.)]\s")


def _el_list_block_idx(lines, item_pred):
    """Индексы строк, ВХОДЯЩИХ в блок ≥2 пунктов подряд (одиночки не в счёт).
    Пустая строка блок не рвёт, любая прозаическая строка - рвёт."""
    idx, run = set(), []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if item_pred(s):
            run.append(i)
        else:
            if len(run) >= 2:
                idx.update(run)
            run = []
    if len(run) >= 2:
        idx.update(run)
    return idx


# (3) ПРЯМАЯ РЕЧЬ. Кавычки вокруг ТЕРМИНА или оборота («точка А»,
# «контент-завод», «нейросети это не магия») - типографика, не речь. Живая речь
# опознаётся по трём признакам: глагол речи рядом · строка ЦЕЛИКОМ реплика ·
# внутри закавыченного есть местоимение или глагол 1-2 лица.
_EL_LIVE_PRON = re.compile(
    r"\b(я|мне|меня|мной|мною|мы|нам|нас|нами|ты|тебе|тебя|тобой|тобою|"
    r"вы|вам|вас|вами|мо(?:й|я|ё|е|и|его|ей|их|ему|им|ём)|"
    r"тво(?:й|я|ё|е|и|его|ей|их|ему|им|ём)|наш(?:а|е|и|его|ей|их|ему|им|ем)?|"
    r"ваш(?:а|е|и|его|ей|их|ему|им|ем)?|"
    r"i|me|my|mine|we|us|our|ours|you|your|yours)\b", re.IGNORECASE)
# Окончания 2 лица берём только те, что не дают ложных существительных:
# `ешь/ёшь/ишь` при ≥3 буквах основы (слова от 7 знаков - «делаешь», «поймёшь»,
# «защитишь»; «лишь»/«мышь» под порог не проходят). `ете/ите` НЕ берём совсем -
# они рвут на «газете», «планете», «орбите», «защите».
_EL_LIVE_VERB = re.compile(
    r"\b[а-яё]{3,}(?:ешь|ёшь|ишь)\b|"
    r"\b(могу|хочу|знаю|думаю|делаю|вижу|беру|даю|скажу|буду|сделаю|смогу|"
    r"понял|поняла|помню|жду|иду|пойду|хотите|знаете|видите|помните|делаете|"
    r"давай|давайте|смотри|смотрите|слушай|слушайте|скажи|скажите|"
    r"представь|представьте|попробуй|попробуйте)\b", re.IGNORECASE)


def _el_is_live_speech(fragment):
    return bool(_EL_LIVE_PRON.search(fragment) or _EL_LIVE_VERB.search(fragment))


def _el_speech_hits(text, lines, dash_block_lines=frozenset()):
    """Строгая прямая речь. Возвращает число засчитанных реплик.

    `dash_block_lines` - индексы строк, входящих в тире-ОПИСЬ (блок ≥2 пунктов).
    Они из речи исключены: пункт описи с местоимением («- мне нужен ноутбук»)
    это перечень, а не реплика, и засчитан уже как `dash_list`."""
    hits = 0
    whole_line_quotes = set()
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        # (б) строка ЦЕЛИКОМ реплика: тире-реплика или «...» на всю строку
        if re.match(r"^[-–—]\s", s) and i not in dash_block_lines:
            body = s[2:].strip()
            if _EL_SPEECH_VERBS.search(s) or _el_is_live_speech(body):
                hits += 1
                continue
        if (s.startswith("«") and s.endswith("»")) or \
           (s.startswith('"') and s.endswith('"') and len(s) > 2):
            body = s[1:-1]
            if _EL_SPEECH_VERBS.search(s) or _el_is_live_speech(body):
                hits += 1
                whole_line_quotes.add(s)
            continue
    # закавыченный фрагмент внутри абзаца: (а) глагол речи рядом или
    # (в) местоимение/глагол 1-2 лица внутри кавычек
    for m in _EL_GUILLEMET.finditer(text):
        frag = m.group(0)
        if frag in whole_line_quotes:
            continue
        ctx = text[max(0, m.start() - 70):m.end() + 70]
        if _EL_SPEECH_VERBS.search(ctx) or _el_is_live_speech(frag):
            hits += 1
    return hits


# (5) СЛУЖЕБНАЯ 👉-CTA-СТРОКА ЦЕЛИКОМ ВНЕ АВТОРСКОГО СЧЁТА. Правка Д1 п.5 названа
# по стрелке, но 👉-строка несёт РОВНО тот же класс формальных токенов и по всем
# осям сразу: `👉 жми ->`, `👉 напиши «СТАРТ» в бот` (кавычки), `👉 пиши СТАРТ`
# (КАПС код-слово), `👉 *записаться*` (курсив), `👉 забирай тут:` (двоеточие). Это
# одна и та же служебная типографика воронки, а не текстура поста, поэтому из
# СИГНАТУРНЫХ детекторов 👉-строка исключается целиком, а не только по стрелке.
# Бесплатные категории (жирный, эмодзи, вопрос, скобка, панч, эмодзи-хвост) на
# полном тексте как считались, так и считаются - они и так пола не держат.
_EL_CTA_MARK = "\U0001F449"   # 👉


def _el_body_lines(lines):
    """Строки поста без служебных 👉-CTA-строк."""
    return [ln for ln in lines if not ln.strip().startswith(_EL_CTA_MARK)]


def check_element_types(text):
    """Два HARD-пола по элементам формы: 3 разных типа из 15 (замер)
    и 🔴 СИГНАТУРНЫЙ пол по подмножеству ELEMENTS_SIGNATURE (по решению автора).

    Категории - те же 15, по которым мерился корпус: жирный · КАПС · растяжка
    гласной · стрелка · тире-опись · нумерация · прямая речь · вопрос ·
    скобка `))` · курсив · эмодзи-хвост абзаца · эмодзи · панч-строка (не первая
    строка ≤25 знаков) · цитата-блок · строка на двоеточии. Возвращает dict:
    counts (по каждой), types (сколько типов присутствует), present, missing
    (отсортированы по доле верха, сначала самые частые у доноров), плюс
    sig_types / sig_present / sig_missing по сигнатурному подмножеству.

    🔴 ДЕТЕКТОРЫ СТРОГИЕ (Д1 жюри, по решению автора): КАПС не считает фактические
    аббревиатуры и расшифровки, опись и нумерация требуют блок ≥2 пунктов,
    прямая речь требует признак живой речи, двоеточие требует раскрытие
    следующей строкой, служебная 👉-CTA-строка целиком выведена из сигнатурных
    детекторов. До этой правки пол снимался одним формальным токеном - см. блок
    комментариев выше.

    Почему это отдельный гейт, а не ужесточение check_formatting_devices:
    старый счётчик мерит РАЗМЕТКУ (жирный/курсив/капс/троеточие/эмодзи) и его
    квота отменена каноном §8.2, а владелец разнёс выдачу за отсутствие
    ЭЛЕМЕНТОВ КОПИРАЙТИНГА - описи, панч-строки, прямой речи, эмодзи-хвостов.
    Это разные множества, и мерить их одним числом значит снова потерять то,
    из-за чего был разнос."""
    lines = text.split("\n")
    # тело = пост без служебных 👉-CTA-строк; по нему идут СИГНАТУРНЫЕ детекторы
    body_lines = _el_body_lines(lines)
    body_text = "\n".join(body_lines)

    counts = {}
    counts["bold"] = len(_EL_BOLD.findall(text))
    counts["caps_word"] = len(_el_caps_hits(body_text))
    counts["stretch"] = len(_EL_STRETCH.findall(body_text))
    counts["question"] = text.count("?")
    counts["italic"] = len(_EL_ITALIC.findall(body_text))
    counts["emoji_count"] = (len(_EL_EMOJI.findall(text))
                             + len(_EL_KEYCAP.findall(text)))
    counts["arrow"] = len(_EL_ARROW.findall(body_text))

    dash_idx = _el_list_block_idx(body_lines, lambda s: bool(_EL_DASH_ITEM.match(s)))
    num_idx = _el_list_block_idx(
        body_lines, lambda s: bool(_EL_NUM_ITEM.match(s)) or bool(_EL_KEYCAP.search(s)))
    counts["dash_list"] = len(dash_idx)
    counts["numbered_list"] = len(num_idx)
    counts["direct_speech"] = _el_speech_hits(body_text, body_lines, dash_idx)

    quote_block = colon_reveal = short_punch = emoji_tail = 0
    nonempty = [ln.strip() for ln in lines if ln.strip()]
    for idx, s in enumerate(nonempty):
        if s.startswith(">"):
            quote_block += 1
        # (4) двоеточие-раскрытие: следующая непустая строка обязана БЫТЬ
        # раскрытием - пункт описи/нумерации или короткая строка (<60 знаков).
        # Служебная 👉-CTA-строка с двоеточием не считается никогда.
        if s.endswith(":") and not s.startswith(_EL_CTA_MARK):
            nxt = nonempty[idx + 1] if idx + 1 < len(nonempty) else None
            if nxt is not None and (
                    _EL_DASH_ITEM.match(nxt) or _EL_NUM_ITEM.match(nxt)
                    or _EL_KEYCAP.search(nxt) or len(nxt) < 60):
                colon_reveal += 1
        if idx > 0 and len(s) <= 25:
            if _EL_EMOJI.sub("", s).strip():   # чисто-эмодзи строка панчем не считается
                short_punch += 1
        if _EL_END_EMOJI.search(s):
            emoji_tail += 1

    counts["quote_block"] = quote_block
    counts["colon_reveal"] = colon_reveal
    counts["short_punch"] = short_punch
    counts["emoji_tail"] = emoji_tail

    present = [k for k in ELEMENTS_15 if counts[k] > 0]
    missing = sorted([k for k in ELEMENTS_15
                      if counts[k] == 0 and k not in ELEMENTS_NEVER_ADVISE],
                     key=lambda k: -ELEMENT_TOP_SHARE[k])
    sig_present = [k for k in ELEMENTS_SIGNATURE if counts[k] > 0]
    sig_missing = sorted([k for k in ELEMENTS_SIGNATURE if counts[k] == 0],
                         key=lambda k: -ELEMENT_SIG_STRICT_SHARE[k])
    return {"counts": counts, "types": len(present),
            "present": present, "missing": missing,
            "sig_types": len(sig_present), "sig_present": sig_present,
            "sig_missing": sig_missing}


def element_missing_line(missing, limit=5):
    """«чего не хватает» с долями верха, самые частые у доноров - первыми."""
    return ", ".join(f"{ELEMENT_LABELS[k]} ({ELEMENT_TOP_SHARE[k]}% верха)"
                     for k in missing[:limit]) or "ничего"


def element_sig_missing_line(sig_missing, limit=5):
    """«поставь хотя бы одно» по СИГНАТУРНЫМ, отсортировано по строгой доле
    доноров (замер уже новыми детекторами, не старыми)."""
    return ", ".join(f"{ELEMENT_LABELS[k]} ({ELEMENT_SIG_STRICT_SHARE[k]}% доноров)"
                     for k in sig_missing[:limit]) or "ничего"


def _flag_note(msg):
    """🔴 Д5 (по решению автора, финальное жюри): НЕВИДИМОЕ ОСЛАБЛЕНИЕ.

    Применение флага-понижателя печаталось только в stdout, а хук на exit 0
    stdout не показывает - снятый HARD-пол не видел никто. По закону state
    факт применения флага обязан идти в stderr ДАЖЕ при exit 0. stdout-строка
    остаётся на месте (её читают глазами и грепает ревью), stderr - машинная
    улика ослабления."""
    sys.stderr.write("[ФЛАГ] " + msg + "\n")
    sys.stderr.flush()


def check_headline_bold(paragraphs):
    """WARN. Заголовок (первый абзац) у автора с 2026 = жирный (**...**), эмодзи
    вне звёзд: '🔒 **Текст**'. Прецедент 2026-06-13: выдал заголовок без жирного,
    автор 'почему в заголовок не жирный, нарушен мой подход к форматированию'.
    Эталон по решению автора: '😍 **Ого, за ночь...**'."""
    if not paragraphs:
        return False
    head = paragraphs[0]
    return bool(re.search(r"\*\*[^*\n]+\*\*", head) or re.search(r"<b>.+?</b>", head))


def check_baza(text):
    """HARD. 'база/базы/базе/базу/базой/базою' в значении аудитории = ВНУТРЕННИЙ
    маркетинговый термин: читатель не понимает слова, и людям неприятно числиться
    чьей-то 'базой'. В публичный текст НЕ выносить → подписчики / читатели / люди /
    аудитория. Прецедент 2026-06-13: автор ловил ≥5 раз ('я тебе говорил минимум
    пять раз'). Регэксп не трогает 'базовый / базируется / база данных-кода'."""
    hits = []
    for ln, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bбаз(?:а|ы|е|у|ой|ою)\b", line, re.IGNORECASE):
            hits.append((ln, line.strip()[:70]))
    return hits


def check_long_paragraphs(paragraphs, limit=250):
    """🔴 HARD с этой редакции (правка владельца: «всё равно большие абзацы, некоторые
    очень... в референсах таких абзацев нет»). Порог опущен 320 → 250 по ЖИВОМУ
    замеру донор-корпуса `corpus-12m.json` (6452 абзаца трёх доноров): медиана 78
    знаков, q3 110, p90 145, p95 167; абзацев длиннее 250 знаков у доноров 0.8%,
    длиннее 320 - 0.3%. Порог 320 пропускал то, чего в референсах практически нет,
    поэтому «простыня» доезжала до владельца раз за разом.

    Списочные пункты и строки-буллеты из счёта исключены: их длина - другой класс.
    Прецедент 2026-06-13: «ты не Лев Толстой, надо больше нормальных отступов»."""
    out = []
    for i, p in enumerate(paragraphs, 1):
        body = p.strip()
        if re.match(r"^[•\-–—*]|^\d+[.)]|^[0-9]\ufe0f?\u20e3", body):
            continue
        if len(body) > limit:
            out.append((i, len(body)))
    return out


def check_choppy_sentences(text):
    """Детектор рубленых фраз (AI-tic). Прецедент 2026-05-29: единое предложение
    разрублено точками на staccato «Без дизайнера. Без строчки кода».
    Ловит egregious-случаи: 3+ подряд предложений из 1-2 слов.
    Тонкую рубку (период вместо запятой) ловит только humaniser - он обязателен."""
    clean = re.sub(r"[*_|>#]", "", text)
    sentences = [s for s in re.split(r"[.!…]+", clean) if s.strip()]
    max_run = run = 0
    for s in sentences:
        if len(s.split()) <= 2:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def check_staccato(text):
    """WARN. Стаккато-декларации = мёртвый язык (автор : «пишешь как
    робот кусками, это не живая речь»). Ряд из 3+ коротких (<=7 слов)
    независимых клауз подряд, ни одна из которых не начинается со сцепки-союза
    (и/а/но/потому что/так что/пока/ведь/который...) = робот. Живая речь
    цепляет предложения союзами и интонацией, течёт волной разной длины.
    Ловит и точки, и запятые-сплайсы («живу в деревне, компьютер остался»)."""
    CONJ = {"и", "а", "но", "потому", "так", "когда", "пока", "чтобы", "ведь",
            "который", "которая", "которые", "что", "если", "хотя", "зато",
            "поэтому", "причём", "притом", "или", "либо", "только",
            "сколько", "как", "где", "куда", "откуда", "почему", "зачем"}
    clean = re.sub(r"[*_|>#]", "", text)
    flagged = []
    for para in clean.split("\n"):
        if not para.strip():
            continue
        clauses = [c.strip() for c in re.split(r"[.,;:…]+", para) if c.strip()]
        run, best = 0, 0
        for c in clauses:
            words = c.split()
            first = words[0].lower() if words else ""
            if 0 < len(words) <= 7 and first not in CONJ:
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= 4:
            flagged.append((best, para.strip()[:70]))
    return flagged


def check_stub_sentences(paragraphs):
    """Детектор одиночных предложений-обрубков (РОВНО 1 слово = акцент-нейрослоп).
    Прецедент 2026-06-13: «...110 рублей. Бесплатно» — обрубок «Бесплатно» = AI-tic
    (рубленая фраза для эффекта), humaniser его пропустил. Одиночное предложение
    из 1 слова ВНУТРИ абзаца (после точки) = FAIL. автор: 'жаргонизм, нейрослоп'."""
    hits = []
    for p in paragraphs:
        if "http" in p or "👉" in p:
            continue  # CTA-строки со ссылкой/стрелкой не предложения
        clean = re.sub(r"[*_|>#`]", "", p)
        sents = [s.strip() for s in re.split(r"[.!?…]+", clean) if s.strip()]
        if len(sents) <= 1:
            continue  # цельный абзац/заголовок без внутренней точки — не обрубок
        for s in sents:
            words = re.findall(r"[А-Яа-яЁёA-Za-z]+", s)
            if len(s.split()) == 1 and len(words) == 1 and len(words[0]) >= 3:
                hits.append(s.strip())
    return hits


def check_line_stacking(paragraphs):
    """HARD. Детектор рубки «строка-на-фразу» (главный AI-почерк, прецедент по решению автора).
    автор: «так пишет только нейросеть... в середине предложения разрывы, переносишь
    предложение, абзацы склеиваешь — кусок говна». В нормальной TG-прозе абзац = одна
    плотная строка (клиент сам переносит). Лесенка вставляет РУЧНЫЕ переносы, дробя
    фразы на столбик коротких строк. Ловим: блок (кроме заголовка/CTA) с ≥3 непустыми
    строками и средней длиной строки < 55 символов = лесенка → FAIL. Лечение —
    переписать блок цельными предложениями в один абзац."""
    hits = []
    for i, p in enumerate(paragraphs, 1):
        if i == 1:
            continue  # заголовок — отдельная строка, не лесенка
        if "http" in p or "👉" in p:
            continue  # CTA со ссылкой/стрелкой
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        # Буллет-список — НЕ лесенка: прохибиция 17 канона голоса ТРЕБУЕТ
        # перечисление маркерами по одному пункту на строку («сплошной перечень
        # без буллетов = нечитабельный огрызок»). Лесенка — это дробление ПРОЗЫ
        # ручными переносами, а не оформленный список. Прецедент по решению автора: буллеты
        # состояния окна в бот-касании Б6.3 давали ложный HARD FAIL, толкая
        # переписать их в простыню против канона.
        bullet_re = re.compile(r"^(?:[🔹🔸▪️◾️•·—–\-\*]|\d+[.)]|[1-9]️?⃣)\s+")
        if sum(1 for l in lines if bullet_re.match(l)) >= max(2, len(lines) - 1):
            continue
        mean_len = sum(len(l) for l in lines) / len(lines)
        if mean_len < 55:
            hits.append((i, len(lines), round(mean_len)))
    return hits


def check_banned_dev_objection(text):
    """HARD. Запрещённый класс «разработчик/программист/фрилансер».

    🔒 ИЗОЛЯЦИЯ: список слов НЕ хардкодится здесь - он приходит из внешнего
    словаря владельца (`banned_words[id=dev_objection]`, см. шапку модуля).
    Причина: запрет завязан на ЦА и позиционирование конкретного автора (у его
    аудитории нет возражения «нужен разработчик / нужен код»), у ученика ЦА
    другая и этот запрет ломал бы ему каждый пост. Нет словаря -> hits пусто.
    Обоснование и прецеденты живут в поле `reason` того же словаря."""
    import re as _re
    # Бренд-термины «вайбкодинг/вайбкодер/вайбкод…» РАЗРЕШЕНЫ (это бренд и тема автора) —
    # подстрока «кодинг» в них НЕ должна триггерить dev-класс (FP по решению автора: пост ПРО
    # вайбкодинг падал 3× на самом слове). Вырезаем бренд перед матчем; реальный фрейм
    # «разработчик/кодить/в коде/программист/верстальщик» по-прежнему ловится.
    text = _re.sub(r"вайб-?код\w*", " ", text, flags=_re.IGNORECASE)
    # 🔴 ФИКС ложного HARD (скептик-раунд 2, по решению автора): дефис - граница слова, поэтому
    # `\bкод\b` матчил «код-слово» - штатный термин воронок, который стоит в постах
    # постоянно. Пост с легальным «код-слово» ловил HARD dev-класс и не выдавался.
    # Лечится негативным lookahead на дефис у ВСЕХ падежных форм «код» (сами регексы
    # с lookahead лежат в словаре владельца, здесь только вырезание бренда).
    return _owner_scan("dev_objection", text)


def check_banned_marathon(text):
    """HARD-запрет слова, объявленного владельцем несовместимым с его событием.

    🔒 ИЗОЛЯЦИЯ (подэтап 4i): само слово НЕ хардкодится здесь. Оно приходит из
    внешнего словаря владельца (`banned_words[id=marathon]`, см. шапку модуля).
    Причина прямая: у владельца формат его бесплатного события называется строго
    одним словом, а соседнее для него брак. У УЧЕНИКА событие вполне может быть
    ровно тем форматом - и хардкод валил бы ему HARD каждый пост про его продукт.
    Нет словаря -> список пуст -> проверка печатает [PASS] 0 и не блокирует.
    Обоснование и прецедент живут в поле `reason` того же словаря.
    Снимается флагом --allow-marathon."""
    return _owner_scan("marathon", text)


def check_banned_perelivN(text):
    """HARD-запрет снятого контент-концепта владельца.

    🔒 ИЗОЛЯЦИЯ (подэтап 4i): регексы приходят из внешнего словаря владельца
    (`banned_words[id=perelivN]`, см. шапку модуля). Это износ конкретного
    запуска («убрать из всех файлов»), у ученика такого решения нет и быть не
    может. Нет словаря -> [PASS] 0. Обоснование - в поле `reason` словаря.
    Снимается флагом --allow-perelivN."""
    return _owner_scan("perelivN", text, pad=20)


def check_banned_category_word(text):
    """HARD. Категория-слово вместо ИМЕНИ реальной сущности.

    Класс тот же, что «робот/роботы» в workflow/_phases-state.md (под-класс 6
    блока «НЕ-РУССКИЙ ЯЗЫК»): обобщённое родовое слово ставится туда, где у
    сущности есть собственное имя, и текст звучит косноязычно. Лечится не
    синонимом, а именем: конкретное название модели/программы/сервиса.

    🔒 ИЗОЛЯЦИЯ: сами слова и падежные формы НЕ хардкодятся здесь - они
    приходят из внешнего словаря владельца (`banned_words[id=instrument_naming]`,
    см. шапку модуля). Причина: какое именно родовое слово для автора брак,
    решает его домен и его словарь; у ученика домен другой. Нет словаря ->
    hits пусто, проверка печатает [PASS] с нулём.
    Снимается флагом --allow-instrument."""
    return _owner_scan("instrument_naming", text)


def check_banned_cta_bridge(text):
    """HARD. Подводка-мостик перед оффером (клауза-вода в начале предложения).

    Класс: придаточное «кому/если ...,» открывает предложение и адресует
    оффер, ничего не добавляя. Тест отпускания: снял клаузу - смысл предложения
    не изменился, значит клауза была водой, и предложение обязано начинаться с
    самого оффера.

    🔒 ИЗОЛЯЦИЯ: регекс живёт во внешнем словаре владельца
    (`banned_words[id=cta_bridge]`, см. шапку модуля) - границу класса задаёт
    замер по корпусу конкретного автора, у ученика корпус свой. Нет словаря ->
    [PASS] 0. Обоснование и замер - в поле `reason` того же словаря.
    Снимается флагом --allow-cta-bridge."""
    return _owner_scan("cta_bridge", text, pad=15)


def check_colons(text):
    """HARD. Максимум 1 двоеточие на пост (автор : «ты в этом посте
    раза четыре двоеточие делаешь, максимум один раз на пост можешь»).
    Время (19:00) и URL (https://) не считаются. Снимается --allow-colons."""
    hits = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r":", line):
            i = m.start()
            if 0 < i and i + 1 < len(line) and line[i - 1].isdigit() and line[i + 1].isdigit():
                continue  # время 19:00
            if line[i + 1:i + 3] == "//":
                continue  # URL
            hits.append((ln, line.strip()[:70]))
    return hits


IMAGE_ROOTS = {
    "рук": "рука/руки (напр. «даёт руки» + «за руку» + «под рукой»)",
    "мозг": "мозг (напр. «второй мозг» в разных значениях)",
    "фундамент": "фундамент/стройка",
    "спотык": "спотыкание/ходьба",
    "корм": "кормление/еда",
    "топлив": "топливо/горючее",
    "мышц": "мышцы/качалка",
    "фильм": "кино/фильм",
    "конвейер": "конвейер/завод",
}


def check_image_collision(text):
    """WARN. Один образ-корень, повторённый в РАЗНЫХ значениях по тексту, даёт
    навязчивость и несовместимые картинки. Правки по одной находке особенно
    склонны это завозить: метафора не исчезает, а мигрирует.
    Прецедент по решению автора: три «руки» в одном посте («даёт нейросети руки» +
    «ведёт тебя за руку» + «у ИИ под рукой»), две завезены моими же правками.
    Порог: ≥3 вхождения корня = WARN (2 = норма, может быть осознанный повтор).
    Память: feedback_check_image_collision_across_whole_text."""
    hits = []
    low = text.lower()
    for root, label in IMAGE_ROOTS.items():
        found = []
        # 🔴 ФИКС (правка владельца): корень БЕЗ границы слова матчил внутри других слов
        # («стРУКтура», «инстРУКция» ловили «рук», хотя это не образ руки вообще).
        # \b перед корнем ограничивает матч НАЧАЛОМ слова - «руки»/«рука»/«рукой»
        # по-прежнему ловятся, случайная подстрока внутри другого слова - нет.
        pattern = r"\b" + root
        for ln, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(pattern, line.lower()):
                i = m.start()
                frag = line.strip()
                found.append((ln, frag[:60]))
        if len(found) >= 3:
            hits.append((label, found))
    return hits


def check_paragraph_openers(paragraphs):
    """WARN. Два+ соседних абзаца, начинающихся с одного слова, читаются как
    петля (прецедент по решению автора: два абзаца подряд с «А»)."""
    hits = []
    prev_word, prev_idx = None, None
    for idx, p in enumerate(paragraphs, 1):
        first = re.sub(r"^[^\w]+", "", p).split()
        if not first:
            prev_word = None
            continue
        w = first[0].lower().strip(".,!?:;")
        if prev_word and w == prev_word and len(w) <= 12:
            hits.append((prev_idx, idx, w))
        prev_word, prev_idx = w, idx
    return hits


# ---------------------------------------------------------------------------
# Канон формы v2 (.business/voice-corpus/_format-canon-v2.md) — L1-L5.
# Профильный слой ЦЕЛИ ФОРМЫ: активируется ТОЛЬКО флагом --form-goal.
# Без флага ни один профильный порог не читается — старое поведение линтера
# не меняется (правило безопасности плана внедрения: старое = fallback).
# ---------------------------------------------------------------------------

# 🔴 Д110 (разнос владельца ): «Форматирование по канону не внедрил -
# просто заголовок жирный и всё. Форматирование это ключевая база движка».
# ДЫРА: bold_target/bold_ceiling были ориентиром без ПОЛА - пост-простыня с
# ОДНИМ жирным заголовком и голым телом проходил линт зелёным в любом профиле.
# ФИКС: ключ `bold_body_min` - МАШИННЫЙ HARD-ПОЛ ЖИРНЫХ В ТЕЛЕ (тело = всё,
# кроме первого абзаца-заголовка). Числа взяты не из головы:
#   S (sales)  = 2 в теле при HARD-поле 3 всего. Канон §3.3: медиана жирных 4.5,
#                ≥4 держат 59% верха - то есть пол 3 лежит ЗАМЕТНО НИЖЕ цели
#                профиля и физически не может зарубить пост, написанный как верх.
#                Замер зелёных владельца (ivan-final-0/1/2, класс sales):
#                6 жирных всего / 5 в теле у каждого - запас втрое.
#   F (forwards) = 1 в теле. Канон §9 F-10 цель 3, ориентир 4 (≥3 держат 71%):
#                HARD на 3 канон запрещает (порог допуска 80%), но «ноль в теле»
#                = ровно та простыня, на которую жалуется владелец.
#   E (event)  = 1 в теле. Замер событийных зелёных: b17-3-0508 - 3 в теле,
#                inf18-0608 - 2 в теле.
#   R (нарратив/разбор) = None, ПОЛА НЕТ НАМЕРЕННО. Канон §3.1/§9 R-4: цель
#                нарратива - РОВНО 1 жирный (хук), у разбора 1-2. Плюс прямая
#                улика калибровки: зелёные владельца osn18-0608.txt и
#                zakr18-den-0608.txt несут 1 жирный ВСЕГО и 0 в теле - любой пол
#                в теле зарубил бы 2 из 12 зелёных. Правило, валящее зелёный,
#                сужается с именем образца - вот имена.
FORM_PROFILES = {
    # ключ = (form_goal, form_class). Числа — канон §3, §9 (медианы/коридоры верхнего
    # квартиля и статус HARD/WARN по покрытию). Где канон не различает — None.
    ("reactions", "narrative"): {
        "label": "R-нарратив",
        # Д110: пола нет - канон §9 R-4 цель РОВНО 1 (хук). См. шапку FORM_PROFILES
        "bold_min_total": None, "bold_body_min": None,
        "length_min": 362, "length_max": 1242, "length_target": 671,
        "bold_target": 1, "bold_ceiling": 2,
        "list_blocks_max": 0,            # HARD, канон §9 R-9 (93% верха)
        "colons_max": 2,   # 4c: перекалибровано по корпусу (канон п.44) - эталон владельца 6.08 несёт 2
        "sentence_median_min": None,     # не различает, канон §1
        "hook_digit_required": False,
        "numbered_list_allowed": False,  # WARN-анти-паттерн, канон §9 R-9
        "headline_bold_check": True,     # желателен, 85% против 63% (WARN)
    },
    ("reactions", "razbor"): {
        "label": "R-разбор",
        # Д110: пола нет - зелёные osn18-0608 и zakr18-den-0608 несут 0 жирных в теле
        "bold_min_total": None, "bold_body_min": None,
        "length_min": 402, "length_max": 990, "length_target": 542,
        "bold_target": 1, "bold_ceiling": 2,
        "list_blocks_max": 1,            # WARN, до 3 предикативных пунктов
        "colons_max": 2,   # 4c: перекалибровано по корпусу (канон п.44) - эталон владельца 6.08 несёт 2
        "sentence_median_min": 5,        # HARD-пол, держат 11/12 верха (канон §9 R-10)
        "hook_digit_required": False,
        "numbered_list_allowed": True,   # обратный знак 25% против 17%, канон §1
        "headline_bold_check": False,    # запрет и требование сняты, не различает (канон §1)
    },
    ("forwards", "forwards"): {
        "label": "F",
        # Д110: пол только против простыни; канон §9 F-10 цель 3, ориентир 4
        "bold_min_total": 2, "bold_body_min": 1,
        "length_min": 838, "length_max": 1695, "length_target": 1159,
        "bold_target": 3, "bold_ceiling": 4,
        "list_blocks_max": 2,             # опись 5-8 пунктов желательна
        "colons_max": 2,                  # опись-анонс на двоеточии, канон §8.2/L4
        "sentence_median_min": None,
        "hook_digit_required": True,      # WARN-желателен, 63% против 20%, канон §9 F-6
        "numbered_list_allowed": True,     # алгоритм 3-5 шагов, канон §9 F-8
        "headline_bold_check": False,      # жирность хука не проверяется в F
    },
    ("sales", "sales"): {
        "label": "S",
        # Д110 (владелец): HARD-пол. Канон §3.3 медиана 4.5, ≥4 у 59% верха;
        # зелёные ivan-final-0/1/2 несут 6 всего / 5 в теле - пол ниже втрое
        "bold_min_total": 3, "bold_body_min": 2,
        "length_min": 759, "length_max": 2248, "length_target": 1489,
        "bold_target": 4, "bold_ceiling": 5,
        "list_blocks_max": 1,
        "colons_max": 2,   # 4c: перекалибровано по корпусу (канон п.44) - эталон владельца 6.08 несёт 2
        "sentence_median_min": None,
        "hook_digit_required": False,
        "numbered_list_allowed": False,   # HARD, держат 88% верха, канон §9 S-13
        "headline_bold_check": False,
    },
    # --- Д8 (по решению автора): КЛАСС `event` ЗАВЕДЁН В КОДЕ.
    # Было: пятого класса у линтера не существовало, `--form-class event`
    # отбивался argparse, роутер (01-router.md 0.49-E) велел подменять его на
    # `sales` «ближайшим числовым профилем» - и событийный пост мерился чужими
    # порогами, а суть класса (плотность 4.DENS, дата/время события) держалась
    # только текстом 04-review. Ключ здесь один - ("event","event"): класс event
    # живёт при цели sales (окно запуска) и forwards (вне окна), числовой профиль
    # у него от цели НЕ зависит, поэтому resolve_form_profile сводит обе пары
    # сюда (см. функцию ниже).
    # Длины: канон п.45 - пол 500 знаков (событийный пост / финальный пуш),
    # 700 у касания каскада, ВЕРХНЕГО ПОТОЛКА НЕТ. Пол 500 уже стоит выше
    # абсолютным HARD (UNIT_LENGTH_HARD_FLOOR), поэтому коридор здесь None -
    # выдумывать верхнюю границу там, где канон её снял, запрещено.
    # bold/списки/нумерация: замер по событийным green-ivan (b17-3-0508: жирных 3,
    # списочных блоков 0; etalon-0608: жирных 2, нумерованный список на 2 пункта;
    # inf18-0608: жирных 3, блоков 1).
    ("event", "event"): {
        "label": "E-событие",
        # Д110: замер событийных зелёных b17-3-0508 (3 в теле) и inf18-0608 (2 в теле)
        "bold_min_total": 2, "bold_body_min": 1,
        "length_min": None, "length_max": None, "length_target": None,
        "bold_target": 3, "bold_ceiling": 5,
        "list_blocks_max": 1,
        "colons_max": 2,
        "sentence_median_min": None,
        "hook_digit_required": True,     # WARN: у события в хуке стоит время (эталон 6.08 «Сегодня в 19:00»)
        "numbered_list_allowed": True,   # эталон владельца 6.08 сам идёт нумерованным списком
        "headline_bold_check": False,    # etalon-0608 несёт заголовок БЕЗ жирного
    },
    ("gate", "gate"): {
        "label": "A",
        # Д110: у гейт-поста тело - сама просьба, канон §9 A порогов по жирному не даёт
        "bold_min_total": None, "bold_body_min": None,
        "length_min": None, "length_max": None, "length_target": None,
        "bold_target": None, "bold_ceiling": None,
        "list_blocks_max": None,
        "colons_max": 2,   # 4c: перекалибровано по корпусу (канон п.44) - эталон владельца 6.08 несёт 2
        "sentence_median_min": None,
        "hook_digit_required": False,
        "numbered_list_allowed": False,
        "headline_bold_check": False,
    },
}


# --- 4c/C9+F7 (канон п.45, «единая таблица длин по типу единицы»). BASELINE
# по решению автора, «функция-призрак» №4: порога длины по классу единицы в коде НЕ БЫЛО
# вовсе, огрызок ловился только если оператор вспомнил передать --min руками.
# C9-ogryzok (51 знак) и F7-starye-kanaly-ogryzkom (271) проходили чистыми.
#
# Два уровня, и это принципиально:
#   HARD-пол ОДИН для всех единиц = 500 знаков. Это нижняя строка таблицы
#     канона п.45 («событийный пост / финальный пуш - нижняя граница 500»),
#     то есть абсолютный минимум, ниже которого канон не опускается нигде.
#     владелец 6.08: «что за огрызки на две строчки? смыслов нет, это спам».
#   Норма КЛАССА (1500-1700) остаётся WARN. Улика, почему не HARD: канонная
#     таблица 6.08 строже реального одобренного корпуса - при её букве упали
#     бы osn17 (1541 < 1700), osn18 (1556 < 1700), star17 (1492 < 1700) и
#     zakr18 (1497 < 1500), а это посты, которые автор одобрил. Закон
#     калибровки этого файла запрещает HARD там, где падает green.
UNIT_LENGTH_HARD_FLOOR = 500
UNIT_LENGTH_CLASS_MIN = {          # канон п.45, WARN-норма по типу единицы
    "osn": 1700, "star": 1700, "zakr": 1500, "bot": 1500,
    "botreg": 700, "info": 1500,
}


# 🔴 Д71 (скептик-раунд 22, по решению автора): КОЭРЦИЯ КЛАССА СТАЛА ГРОМКОЙ.
# `resolve_form_profile` при цели != reactions КЛАСС ОТБРАСЫВАЕТ (`c = goal`), а при
# цели reactions коэрцит всё, что не narrative и не razbor, в narrative. Само по себе
# это разумный fallback (профиль обязан найтись всегда), но он был ПОЛНОСТЬЮ НЕМЫМ:
# оператор передавал `--form-goal sales --form-class narrative`, видел строку
# `[ФОРМА] цель=sales класс=sales` и не имел ни единого способа понять, что его класс
# отброшен, - строка честно печатает то, что взято, но не печатает, что было заявлено.
# Тот же немой канал уводил и микс `bench-post.py --against-etalons`: пост сверялся с
# эталонами класса, которого автор не объявлял.
# СТАЛО: коэрция ОСТАВЛЕНА (обратная совместимость - ручные прогоны и старые state
# продолжают работать), но факт подмены записывается сюда и печатается строкой
# `[ФОРМА-КОЭРЦИЯ]` рядом с `[ФОРМА]` в main(). ПОРОГИ И ВЕРДИКТ НЕ ТРОНУТЫ: это
# видимость, а не новое правило. Само правило (нелегальная пара = стоп) держит КОД
# хука `post-phase-gate.sh`, блок «ж3» - на боевой выдаче пара до линтера не доезжает,
# а строка тут ловит ручной прогон мимо конвейера.
LAST_FORM_COERCION = None   # (заявленный класс, цель, взятый класс) либо None


def resolve_form_profile(goal, cls):
    """L1. Канон формы v2 §2/§3/§9. goal=None (флаг не передан) → (None, None):
    весь профильный слой молчит, работают старые безусловные пороги (fallback).

    Побочный след (Д71): факт коэрции класса кладётся в модульную LAST_FORM_COERCION -
    её читает main() и печатает строкой [ФОРМА-КОЭРЦИЯ]. Возвращаемое значение и
    пороги от этого не меняются."""
    global LAST_FORM_COERCION
    LAST_FORM_COERCION = None
    if not goal:
        return None, None
    # Д8: класс event перекрывает цель. Роутер (0.49-E) разрешает его при
    # form_goal = sales (launch_window) и forwards (вне окна); числовой профиль
    # события один и тот же, поэтому обе пары сводятся к ключу ("event","event").
    # Политика ссылок ниже по main() по-прежнему ветвится по args.form_goal -
    # событие в окне остаётся продающей единицей и несёт дверь по закону 32.
    if cls == "event":
        key = ("event", "event")
        return FORM_PROFILES.get(key), key
    if goal == "reactions":
        c = cls if cls in ("narrative", "razbor") else "narrative"
    else:
        c = goal
    # Д71: класс БЫЛ заявлен и НЕ доехал - это и есть молчаливая подмена мерки.
    # Пустой класс подменой не считается: он легален (штатное состояние цели
    # forwards, канон 01-router Шаг 0.49), и профиль в этом случае честно
    # выводится из цели, а не отбирается у объявленного класса.
    if cls and c != cls:
        LAST_FORM_COERCION = (cls, goal, c)
    key = (goal, c)
    return FORM_PROFILES.get(key), key


def check_bold_count(text):
    """L5. Канон §9. Число выделений жирным: markdown **...** + HTML <b>...</b>.
    Профильный ориентир (bold_target/bold_ceiling), не абсолютная квота.

    🔴 Д106 (скептик-раунд 37, по решению автора): РЕГЕКС БЕЗ `re.S` НЕ СЧИТАЛ ЖИРНЫЙ,
    РАЗОРВАННЫЙ ГРАНИЦЕЙ АБЗАЦА - ЗНАК ПРОТИВОРЕЧИЛ bold_share_pct.
    ДЕФЕКТ: старый паттерн `\\*\\*[^*\\n]+\\*\\*` явно исключал перевод строки
    из содержимого - жирный, чьи открывающая и закрывающая `**` стоят на
    РАЗНЫХ строках (маркап-артефакт выгрузки донорского корпуса: одинокая
    строка `**` на границе абзаца, см. `_strip_stray_bold_lines` в
    `check_air` ниже - тот же класс артефакта, другая метрика), не
    засчитывался вовсе. Живое противоречие корпуса: эталон Донор-В:165
    (`scripts/etalons.json`) давал `bold_n=0` при `bold_share_pct=10.9%`
    (bench-post.py `measure_form`, СВОЙ регекс `\\*\\*(.+?)\\*\\*` С `re.S`) -
    число выделений противоречило доле их символов в тексте, сигнал был
    перевёрнут: топ-эталон донора выглядел текстом БЕЗ единого жирного, хотя
    жирного там больше десятой доли символов.
    ФИКС: паттерн приведён к ТОМУ ЖЕ виду и флагу, что уже держит
    `bold_share_pct` в `bench-post.py measure_form` - `\\*\\*(.+?)\\*\\*` +
    `re.S`. `bold_n` и `bold_share_pct` теперь считаются ПО ОДНОМУ И ТОМУ ЖЕ
    множеству совпадений (`bold_n` = число совпадений, `bold_share_pct` = доля
    их суммарной длины) - противоречие «bold_n=0 при share>0» структурно
    невозможно ни на одном тексте. Нормализация артефакта (лоне-строки `**`)
    здесь НЕ применяется намеренно: цена нормализации - потеря РЕАЛЬНОГО
    жирного текста (см. докстринг `_strip_stray_bold_lines`), а `re.S` уже
    закрывает счёт без этой цены."""
    md = len(re.findall(r"\*\*(.+?)\*\*", text, re.S))
    html = len(re.findall(r"<b>.+?</b>", text, re.S))
    return md + html


_BOLD_FRAG_RE = re.compile(r"\*\*(.+?)\*\*|<b>(.+?)</b>", re.S)


def bold_fragments(text):
    """Д110. Список текстов жирных фрагментов (markdown ** и HTML <b>) в порядке
    появления. Одно множество совпадений с `check_bold_count` - число фрагментов
    здесь и `bold_n` там структурно совпадают."""
    out = []
    for m in _BOLD_FRAG_RE.finditer(text):
        out.append((m.group(1) if m.group(1) is not None else m.group(2)).strip())
    return out


def check_bold_split(text):
    """🔴 Д110 (разнос владельца : «просто заголовок жирный и всё»).
    Разводит жирный ЗАГОЛОВКА и жирный ТЕЛА - это и есть та величина, которой у
    линтера не было. Заголовок = первый абзац (блок до первой пустой строки),
    ровно так же, как его берёт `check_headline_bold`. Возвращает
    (всего, в заголовке, в теле).

    Почему именно эта разбивка, а не «всего жирных»: пост-простыня несёт
    заголовок жирным и голое тело - по сумме он выглядит как «1 жирный есть»,
    и старый счётчик `check_bold_count` показывал 1, ничего не блокируя. Пол
    ставится на ТЕЛО (`bold_body_min` профиля), потому что жалоба владельца
    ровно про тело."""
    paragraphs = split_paragraphs(text)
    total = check_bold_count(text)
    if not paragraphs:
        return 0, 0, 0
    head = check_bold_count(paragraphs[0])
    return total, head, total - head


def check_bold_colon_stub(text):
    """Д110. Канон §9 R-4 (`HARD` на два края) и §4.5: **жирная служебная строка
    на двоеточии** - маркер низа в нарративе (4/27 верха против 13/27 низа):
    сильнейший инструмент выделения потрачен на служебное слово, и одновременно
    показан шов «тут кончается пост и начинается витрина». Плюс **жирный
    обрывок** - незаконченный кусок предложения жирным (эталон брака #1410,
    C-BOT er_idx 0.33).

    Возвращает (двоеточия, обрывки) списками фрагментов.
    Обрывок ловится узко и только по бесспорному признаку: фрагмент начинается
    со строчной буквы И заканчивается запятой/дефисом/предлогом-хвостом. Замер
    зелёных владельца: 0 попаданий на всех 12 (в них есть жирные, начинающиеся
    со строчной - «воронка ведёт его сама», osn17-0508 - но они законченные и
    хвостом-предлогом не кончаются, поэтому под правило не идут)."""
    colons, stubs = [], []
    _TAIL = ("и", "а", "но", "в", "на", "с", "к", "по", "из", "от", "до", "для",
             "что", "как", "или", "же", "то")
    for frag in bold_fragments(text):
        f = frag.strip()
        if not f:
            continue
        if f.endswith(":"):
            colons.append(f[:70])
            continue
        last = re.sub(r"[^\w]", "", f.split()[-1].lower()) if f.split() else ""
        if f.endswith(",") or f.endswith("-") or (f[:1].islower() and last in _TAIL):
            stubs.append(f[:70])
    return colons, stubs


# =============================================================================
# 🔴 Д111 (досыл владельца ): КЛАСС «БЕЗЫМЯННЫЙ НОСИТЕЛЬ».
# Прецедент - пост osn23: «Взял свои записи за десять месяцев и посмотрел не на
# лайки...». Дословно владелец: «Какие нахер записи? Про что речь? Про Reels?
# Про посты в Telegram?». Читатель не может опознать, о каком корпусе речь, и
# весь довод поста повисает.
#
# КАЛИБРОВКА (обязательная, 12 зелёных владельца). Широкое правило «любое из
# слов записи/посты/архив/ролики/карусели/блог/канал/публикации/сторис обязано
# нести площадку» валит 11 зелёных из 12 - это регресс всего корпуса, а не гейт.
# Поимённо, что именно оно рубило:
#   ivan-final-0/1/2  «В моих постах стоит код-слово», «Написал посты, собрал»
#   inf17-0508        «У меня ролики собираются с нуля, без камеры и без рук»
#   zakr18-den-0608   «Я не рисую карусели и не открываю редактор» (×6 вхождений)
#   inf18-0608        «Наталия собрала сайт и блог сама»
#   star17-0508       «портрет своего языка из реальных постов»
#   b17-3-0508        «когда пост хороший, а охваты слабые»
#   etalon-0608       «перестроить свой контент-завод и ИИ-блог»
# Вывод калибровки: слова, КОТОРЫЕ САМИ НАЗЫВАЮТ ФОРМУ (пост, ролик, карусель,
# сторис, рилс, блог, канал), читатель опознаёт без площадки - их правило не
# трогает. Дыра ровно в словах-КОРПУСАХ, которые формы не называют: записи,
# архив, публикации, материалы, контент, наработки. Их и ловим.
#
# ВТОРОЕ СУЖЕНИЕ, тоже по зелёным: голое слово «записи» легально. Зелёные
# ivan-final-0/1/2 несут «В <твой-продукт> показываю, как такие системы собираются
# словами - вход и записи открыты» - здесь «записи» это записи занятий, а не
# корпус контента. Поэтому HARD включается только когда слово-корпус ПРИСВОЕНО
# автором («свои / мои / наши записи») ИЛИ отмерено сроком («записи за десять
# месяцев») - то есть ровно когда оно подано как ИСТОЧНИК ДАННЫХ поста. В
# примере владельца сработали оба признака сразу.
# =============================================================================

# Слова-корпусы: формы не называют, читатель не может их опознать.
# 🔴 Хвост `(?![\w-])` обязателен: без него правило падало на зелёном
# etalon-0608.txt - «перестроить свой контент-завод и ИИ-блог» ловилось как
# безымянный «контент», хотя «контент-завод» это ИМЯ СИСТЕМЫ, а не корпус
# публикаций. Составное слово через дефис из класса выведено поимённо.
_CARRIER_VAGUE = (r"(?:запис(?:и|ей|ям|ями|ях)|архив(?:а|у|ом|е|ы|ов|ам)?|"
                  r"публикаци(?:я|и|й|ю|ям|ями|ях)|материал(?:ы|ов|ам|ами|ах)|"
                  r"контент(?:а|у|ом|е)?|наработк(?:а|и|ок|ам|ами|ах))(?![\w-])")
# Присвоение автором.
_CARRIER_POSS = r"(?:сво(?:и|их|им|ими|й|его|ему)|мо(?:и|их|им|ими|й|его|ему)|наш(?:и|их|им|ими))"
# Отмеренный срок рядом со словом = «это мой корпус за период».
_CARRIER_SPAN = (r"за\s+(?:\d+|один|два|три|четыре|пять|шесть|семь|восемь|девять|"
                 r"десять|одиннадцать|двенадцать|полгода|год)\s*"
                 r"(?:месяц\w*|год\w*|лет|дн\w*|недел\w*|полугод\w*)")
# Площадка названа явно.
_CARRIER_PLATFORM = (r"(?:нельзяграм\w*|инстаграм\w*|instagram|телеграм\w*|telegram|"
                     r"\bтг\b|t\.me|вконтакте|\bвк\b|рилс\w*|рилз\w*|reels|"
                     r"ютуб\w*|youtube|шортс\w*|shorts|тикток\w*|tiktok|дзен\w*|"
                     r"threads|линкедин\w*|linkedin)")
# Указательная привязка: читатель стоит внутри носителя и опознаёт его местом.
_CARRIER_DEIXIS = (r"(?:эт(?:от|ом|ого|и|их)\s+(?:канал\w*|блог\w*|пост\w*)|"
                   r"\bздесь\b|\bтут\b|в\s+канале|под\s+постом|в\s+этом\s+посте)")


def _carrier_sentences(text):
    """Границы предложения в формате владельца: точки в конце абзаца нет, поэтому
    режем и по [.!?…], и по переводу строки (тот же приём, что в волне 15)."""
    return [s for s in re.split(r"(?<=[.!?…])\s+|\n+", text) if s.strip()]


def check_unnamed_carrier(text):
    """Д111. HARD. Возвращает список (слово, фрагмент предложения) для КАЖДОГО
    присвоенного/отмеренного слова-корпуса, у которого в окне «это предложение +
    предыдущее» нет ни площадки, ни указательной привязки.

    Окно в две фразы, а не в одну: автор штатно называет площадку в подводке, а
    носитель берёт следующей фразой (зелёный osn17-0508: «13 июля я закончил
    пост здесь строкой…» - привязка «здесь» стоит в том же предложении;
    inf17-0508: «раз уж многие из вас выдохлись от рилсов» и следом «У меня
    ролики собираются с нуля»)."""
    sents = _carrier_sentences(text)
    hits = []
    poss_re = re.compile(_CARRIER_POSS + r"[\w\s]{0,20}?" + _CARRIER_VAGUE, re.I)
    span_re = re.compile(_CARRIER_VAGUE + r"[\w\s,]{0,25}?" + _CARRIER_SPAN, re.I)
    anchor_re = re.compile(_CARRIER_PLATFORM + "|" + _CARRIER_DEIXIS, re.I)
    for i, s in enumerate(sents):
        m = poss_re.search(s) or span_re.search(s)
        if not m:
            continue
        window = (sents[i - 1] + " " if i > 0 else "") + s
        if anchor_re.search(window):
            continue
        word = re.search(_CARRIER_VAGUE, m.group(0), re.I)
        hits.append(((word.group(0) if word else m.group(0)), s.strip()[:90]))
    return hits


def check_list_blocks(text):
    """L5. Канон §9. Список-БЛОК = связная группа строк-маркеров (буллет -/•/*, нумерация),
    а не сумма отдельных маркеров (это уже считает check_lists). Дырка, которую правка
    закрывает: без группировки в блоки профильный порог '0 блоков' / '≤1 блок' не к чему
    привязать — десять буллетов подряд и десять буллетов, раскиданных по посту, раньше
    давали одно и то же число."""
    bullet_re = re.compile(r"^\s*(?:[-•*]\s|\d+[.)]\s)")
    lines = text.splitlines()
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        if bullet_re.match(lines[i]):
            start = i
            count = 0
            j = i
            while j < n and (bullet_re.match(lines[j]) or not lines[j].strip()):
                if bullet_re.match(lines[j]):
                    count += 1
                j += 1
            blocks.append((start + 1, count))
            i = j
        else:
            i += 1
    return blocks


def check_numbered_list(text):
    """L5. Канон §9 R-9/S-13/F-8. Число пунктов нумерованного списка '1. '/'1) '."""
    return len(re.findall(r"(?m)^\s*\d+[.)]\s", text))


_LINK_RE = re.compile(r"https?://\S+|(?<!\w)t\.me/\S+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+|t\.me/[^\s)]+)\)")


def _normalize_url(u):
    """Канон §1 (метод якоря и дубля): хвостовая пунктуация и слэш снимаются."""
    u = u.rstrip(").,!?»\"'")
    u = u.rstrip("/")
    return u.lower()


def check_links(text):
    """L5. Канон §1/§9. Возвращает (список нормализованных адресов по вхождениям,
    Counter по адресу). markdown-ссылка `[текст](url)` считается за один якорь по URL
    внутри скобок; голый `https?://` и `t.me/` тоже якорь. Дубль = 2+ вхождения одного
    нормализованного адреса."""
    from collections import Counter
    urls = []
    consumed = []
    for m in _MD_LINK_RE.finditer(text):
        urls.append(_normalize_url(m.group(2)))
        consumed.append((m.start(), m.end()))
    for m in _LINK_RE.finditer(text):
        if any(s <= m.start() < e for s, e in consumed):
            continue
        urls.append(_normalize_url(m.group(0)))
    return urls, Counter(urls)


_BARE_DOMAIN_RE = re.compile(
    r"(?<![\w/@.])((?:[a-z0-9][a-z0-9-]*\.)+(?:ru|com|io|org|net|me|ai|app|co|dev|site|online|su|рф))(?![\w.-])",
    re.IGNORECASE,
)


def check_bare_domains(text):
    """L5. Голый домен без схемы (`proxys.io`, `2ip.ru`) Telegram автолинкует сам —
    в опубликованном посте это ТАКОЙ ЖЕ кликабельный якорь, как https://. До этой
    проверки такие домены не попадали в счёт якорей, и пост цели sales с одним
    «настоящим» адресом плюс упомянутым доменом выходил с двумя якорями мимо
    HARD-правила §9 S-4. Прецедент 2026-08-04: пост закрытого канала про антибан.
    Возвращает список нормализованных доменов, не входящих в уже найденные URL."""
    spans = []
    for m in _MD_LINK_RE.finditer(text):
        spans.append((m.start(), m.end()))
    for m in _LINK_RE.finditer(text):
        spans.append((m.start(), m.end()))
    out = []
    for m in _BARE_DOMAIN_RE.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue
        out.append(_normalize_url(m.group(1)))
    return out


# ═══ ЗАКОН 32: ЧТО СЧИТАЕТСЯ ДВЕРЬЮ (Д18, по решению автора, К3) ══════════════════
# Замер боевого корпуса `_pakety-*` (139 единиц, по решению автора) по формам двери:
#   66  продуктовая/лендинг-ссылка       - видел старый код
#   47  шаблон `{ссылка_эфира}` и родня  - подставляется движком рассылки при
#                                          отправке, в теле стоит именно он
#    7  только t.me-инвайт в комнату     - вырезался законом 29 и пост объявлялся
#                                          «БЕЗ ссылки на дверь»
#   13  датированное обещание двери      - «Ссылка на эфир появится здесь в 18:00»
#                                          (решение владельца 6.08, записано в шапке
#                                          _pakety-0608/osn18.md: до 18:00 http-двери
#                                          не даём, финал = обещание с часом)
#    6  двери нет вообще                 - настоящий дефект закона 32
# Обещание принимается ТОЛЬКО с часом: «ссылка будет позже» дверью не считается,
# читателю нужен проверяемый срок, а не отговорка.
_DOOR_TEMPLATE_RE = re.compile(r"\{\s*ссылка[_а-яёa-z0-9]*\s*\}", re.I)
_DOOR_PROMISE_RE = re.compile(
    r"(?:ссылк|комнат|эфир)\w*[^.\n]{0,90}?"
    r"(?:появ|будет|пришл|дам|отправ|откро|скину|прилет)\w*[^.\n]{0,40}?\d{1,2}[:.]\d{2}"
    r"|(?:появ|будет|пришл|дам|отправ|откро|скину)\w*[^.\n]{0,60}?"
    r"ссылк\w*[^.\n]{0,60}?\d{1,2}[:.]\d{2}", re.I)


def check_door_template(text):
    """Шаблонная дверь `{ссылка_эфира}` - её подставляет отправитель рассылки."""
    return _DOOR_TEMPLATE_RE.findall(text)


def check_door_promise(text):
    """Датированное обещание двери: «ссылка появится здесь в 18:00»."""
    m = _DOOR_PROMISE_RE.search(normalize_unicode_obfuscation(text))
    return m.group(0).strip() if m else None


def check_sentence_median(text):
    """L5. Канон §1/§9 R-10. Медиана числа слов в предложении (разметка и URL вырезаны)."""
    clean = re.sub(r"[*_|>#`]", "", text)
    clean = re.sub(r"https?://\S+", " ", clean)
    sentences = [s.strip() for s in re.split(r"[.!?…]+", clean) if s.strip()]
    lens = sorted(len(s.split()) for s in sentences if s.split())
    if not lens:
        return None
    n = len(lens)
    mid = n // 2
    if n % 2:
        return float(lens[mid])
    return (lens[mid - 1] + lens[mid]) / 2


def check_hook_digit(paragraphs):
    """L5. Канон §9 F-6. Первый абзац (хук) содержит цифру."""
    if not paragraphs:
        return False
    return bool(re.search(r"\d", paragraphs[0]))


# ---------------------------------------------------------------------------
# СКЕЛЕТ ПОСТА (анти-шаблон, прецедент по решению автора: два поста подряд в каркасе
# «жирный хук → курсивная строка → абзац → тире-список», владелец поймал шаблонность.
# Числовой профиль канона задаёт ЧИСЛА, не порядок блоков; порядок сверяем здесь
# с журналом последних выдач канала .skeleton-log.jsonl)
# ---------------------------------------------------------------------------

_DIGIT_EMOJI = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")


def classify_block(block):
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return "P"
    if all(re.match(r"^[-•*–—]\s", l) for l in lines):
        return "LIST"
    if all(re.match(r"^\d+[.)]\s", l) or l.startswith(_DIGIT_EMOJI) for l in lines):
        return "NUMLIST"
    if lines[0].startswith(">"):
        return "QUOTE"
    if len(lines) == 1:
        l = lines[0]
        if re.fullmatch(r"[^\w]*\*\*.+\*\*[^\w]*", l, re.S):
            return "HB"
        if re.fullmatch(r"[^\w]*__.+__[^\w]*", l, re.S):
            return "IT"
        if ("👉" in l or re.search(r"\[.+\]\(.+\)", l)) and len(l) <= 120:
            return "CTA"
    return "P"


def extract_skeleton(text):
    """Подпись поста = порядок типов блоков, соседние одинаковые схлопнуты."""
    sig = []
    for b in split_paragraphs(text):
        t = classify_block(b)
        if not sig or sig[-1] != t:
            sig.append(t)
    return sig


_EMOJI_CLUSTER = re.compile(
    "^(?:[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿⤴⤵]"
    "(?:[️\U0001F3FB-\U0001F3FF]|‍[\U0001F000-\U0001FAFF♀♂️])*"
    ")"
)


def check_hook_premium_emoji(text):
    """владелец: заголовок ВСЕГДА начинается с премиум-эмодзи в тему,
    потом пробел, потом жирный заголовок. В голом тексте стоит обычный
    эмодзи-плейсхолдер (custom emoji ставится при вставке из премиум-набора),
    остальные эмодзи в теле - обычные. Возвращает текст дефекта или None."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return "пост пуст"
    first = lines[0]
    m = _EMOJI_CLUSTER.match(first)
    if not m:
        return f"первая строка не начинается с эмодзи: «{first[:50]}»"
    rest = first[m.end():]
    if not rest.startswith(" "):
        return "после эмодзи-заголовка нет пробела"
    if not re.fullmatch(r"\s+\*\*.+\*\*[^\w]*", rest, re.S):
        return f"после эмодзи + пробела должен идти жирный заголовок целиком (**…**): «{first[:60]}»"
    return None


def check_consecutive_bold_blocks(text):
    """владелец: «Два абзаца подряд жирным, конечно, не выделяй никогда» -
    два соседних блока-акцента размывают акцент. HARD."""
    blocks = split_paragraphs(text)
    types = [classify_block(b) for b in blocks]
    hits = []
    for i in range(1, len(types)):
        if types[i] == "HB" and types[i - 1] == "HB":
            hits.append((blocks[i - 1].strip()[:50], blocks[i].strip()[:50]))
    return hits


def report_emotional_palette(text):
    """Видимость палитры (НЕ квота): капс-слова, растянутые гласные.
    Владелец по решению автора: эмоциональной окрашенности не хватает, капс и растяжка
    гласных уместны (Донор-А, канон #1901 «ОБЩИЙ МУЖИЦКИЙ СБОР!!»)."""
    caps = re.findall(r"\b[А-ЯЁ]{4,}\b", text)
    caps = [w for w in caps if w not in ("НИКОГДА",)]
    stretch = re.findall(r"\b\w*([а-яёa-z])\1{2,}\w*\b", text, re.I)
    return caps, stretch


def skeleton_conflict(sig, prev):
    if sig == prev:
        return "идентичен"
    k = 0
    for a, b in zip(sig, prev):
        if a != b:
            break
        k += 1
    if k >= 3:
        return f"общий зачин {k} блоков"
    return None


def load_skeleton_log(path, channel):
    import json, os
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("channel") == channel:
                entries.append(e)
    return entries


def append_skeleton_log(path, channel, slug, sig):
    import json, datetime
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "date": datetime.date.today().isoformat(),
            "channel": channel, "slug": slug, "skeleton": sig,
        }, ensure_ascii=False) + "\n")


# =============================================================================
# v2.0 ДОБАВЛЕНИЯ (Z1, зона scripts/*, спека ~/specs/2026-08-04-post-skill-v2.md)
# Источник числовых порогов: scratchpad/post-v2/R3-benchmark-spec.md (§A-E,
# «Механика письма по классам», «Анти-паттерны с нулём случаев в TOP»).
# Пороги ЦИТИРУЮТСЯ ДОСЛОВНО из R3 — канон §9 требует admission-тест (≥80%
# покрытия верхнего квартиля на corpus-12m.json) ТОЛЬКО для НОВОГО порога,
# которого нет в R3-таблицах. Каждый порог ниже указывает свою строку R3 —
# ни один не изобретён заново, поэтому отдельный admission-прогон не
# требуется (см. отчёт исполнителя Z1: карта порог→строка R3).
# Категориальные проверки (банк оборотов, плейсхолдеры, цена цифрой,
# факт-база) — не статистические пороги, admission-тест к ним неприменим
# (это законы-запреты, не разделяющая метрика верх/низ доноров).
# Классы R2 (R2-feedback-taxonomy.md) указаны в докстринге каждой функции.
# =============================================================================

# --- п.3 скептик Р2 (по решению автора): юникод-обфускация обходила ВСЕ словарные
# проверки (метафоры check_metaphor_roots, филлеры check_fillers, запреты
# check_banned_collocations/check_invented_verb_noun/check_rubricator_openers
# и т.д.) - они матчат корни буквальными regex по кириллице, а два тривиальных
# юникод-трюка рвут совпадение визуально незаметно:
#   1) zero-width пробел ВНУТРИ слова-мишени («д<ZWSP>верь») - слово физически
#      разрывается на два токена, \bдвер[ьияеёй]\w* не матчит ни один.
#   2) латинский гомоглиф ОДНОЙ буквы внутри кириллического слова («пyть» -
#      Latin y вместо Cyrillic у) - строка визуально неотличима от «путь»,
#      но байты другие, \bпут[ьи]\b не матчит.
# Фикс - нормализация ДО любого словарного матчинга, а не патч конкретного
# regex (тот же обход работал бы против любого следующего словаря).
# --- п.6 скептик Р3 (по решению автора): маппинг покрывал ТОЛЬКО латиницу, мимо
# проходили три класса того же обхода:
#   1) греческий двойник («двεрь», ε U+03B5) - хуже того, регекс слова
#      [a-zA-Zа-яёА-ЯЁ]+ не считал греческую букву буквой, поэтому символ
#      РАЗРЫВАЛ слово надвое и не матчилась ни одна половина;
#   2) soft hyphen U+00AD внутри слова («мара­фон») - невидим, к zero-width
#      классу не относился и не вычищался;
#   3) ё вместо е («двёрь») - лечится не подменой текста (в модуле есть
#      законные регексы С ё: «вперёд», «за счёт», «разберём»), а слепотой
#      САМОГО регекса к паре е/ё - см. _yo_insensitive ниже.
# Подход - таблица трансляции + strip формат-символов (дёшево, без внешних
# библиотек), а не полный confusables-справочник Unicode.
# --- 🔴 С13 скептик Р4 (по решению автора): таблица ниже была ПЕРЕЧИСЛЕНИЕМ символов,
# а не категорией Unicode, поэтому мимо шли ещё три невидимых обхода:
#   1) combining acute U+0301 («две́рь», «марафо́н») - категория Mn, глазом
#      неотличимо от обычного слова, а байты другие;
#   2) variation selector U+FE0F («д<VS16>верь») - тот же эффект;
#   3) внутрисловные разделители - курсив «д_в_ерь» и дефис «мара-фон».
# Первые два лечатся КАТЕГОРИЯМИ (Mn - несамостоятельные диакритики, Cf -
# формат-символы) плюс диапазонами селекторов начертания; третий - отдельным
# проходом по тексту без внутрисловных разделителей (см. _strip_inword_separators).
# Порядок важен: NFKC идёт ПЕРВЫМ, поэтому «й»/«ё» успевают сложиться в
# самостоятельные буквы и удалением Mn не рушатся.
_ZERO_WIDTH_CHARS = (
    "​‌‍﻿⁠"          # ZWSP·ZWNJ·ZWJ·BOM·WORD JOINER
    "­"                                   # SOFT HYPHEN (перенос, невидим)
    "᠎‎‏؜"                 # MONGOLIAN VOWEL SEP·LRM·RLM·ALM
    "⁡⁢⁣⁤"                 # невидимые математические
)
_ZERO_WIDTH_TRANS = {ord(ch): None for ch in _ZERO_WIDTH_CHARS}

# Диапазоны селекторов начертания (variation selectors): VS1-16 и дополнительные
# VS17-256. Категория у них Mn, но держим явно - читаемость важнее краткости.
_VARIATION_SELECTORS = [(0xFE00, 0xFE0F), (0xE0100, 0xE01EF)]


def _is_invisible_mark(ch):
    """Символ-невидимка: диакритика без собственной ширины (Mn), формат-символ
    (Cf, сюда попадают ZWSP/ZWNJ/soft hyphen) или селектор начертания."""
    cp = ord(ch)
    for lo, hi in _VARIATION_SELECTORS:
        if lo <= cp <= hi:
            return True
    return unicodedata.category(ch) in ("Mn", "Cf")


# Внутрисловный разделитель: дефис, подчёркивание, звёздочка, тильда МЕЖДУ
# буквами («мара-фон», «д_в_ерь», «мар*аф*он»). Снимается ТОЛЬКО во втором
# проходе словарных проверок, а не в самом тексте: глобальная склейка стирала бы
# границу слова и меняла смысл разбора («мастер-класс» -> «мастеркласс»).
_INWORD_SEP_RE = re.compile(r"(?<=[^\W\d_])[-_*~]+(?=[^\W\d_])")


def _strip_inword_separators(text):
    return _INWORD_SEP_RE.sub("", text) if text else text


def _dedup_second_pass(first, second, key):
    """Находки второго прохода (текст без внутрисловных разделителей) МИНУС то,
    что уже нашёл первый проход. Без вычитания честный текст удваивал бы каждое
    нарушение - оба прохода видели бы одно и то же."""
    from collections import Counter
    left = Counter(key(x) for x in first)
    extra = []
    for x in second:
        k = key(x)
        if left.get(k):
            left[k] -= 1
        else:
            extra.append(x)
    return extra

# Гомоглифы -> кириллица: латиница + греческий алфавит + двойники из самого
# кириллического блока (украинская і и т.п.). Применяется ТОЛЬКО внутри
# смешанного слова (см. ниже), поэтому чистое английское/греческое слово в
# тексте остаётся собой.
_HOMOGLYPH_TO_CYRILLIC = {
    # латиница
    "a": "а", "A": "А", "B": "В", "c": "с", "C": "С", "e": "е", "E": "Е",
    "H": "Н", "k": "к", "K": "К", "m": "м", "M": "М", "o": "о", "O": "О",
    "p": "р", "P": "Р", "t": "т", "T": "Т", "x": "х", "X": "Х", "y": "у",
    "Y": "У",
    # греческий
    "α": "а", "Α": "А", "β": "в", "Β": "В", "γ": "г", "Γ": "Г", "δ": "д",
    "ε": "е", "Ε": "Е", "ζ": "з", "Ζ": "З", "η": "н", "Η": "Н", "ι": "и",
    "Ι": "И", "κ": "к", "Κ": "К", "λ": "л", "μ": "м", "Μ": "М", "ν": "н",
    "Ν": "Н", "ο": "о", "Ο": "О", "π": "п", "Π": "П", "ρ": "р", "Ρ": "Р",
    "σ": "с", "Σ": "С", "τ": "т", "Τ": "Т", "υ": "у", "Υ": "У", "φ": "ф",
    "Φ": "Ф", "χ": "х", "Χ": "Х",
    # кириллический блок, но не русские буквы
    "і": "и", "І": "И", "ѕ": "с", "Ѕ": "С", "ј": "и", "Ј": "И", "ԛ": "к",
    "һ": "н", "Һ": "Н", "ө": "о", "Ө": "О", "ӏ": "и",
}
_CYRILLIC_LETTER_RE = re.compile(r"[а-яёА-ЯЁ]")
_FOREIGN_LETTERS = "".join(sorted(_HOMOGLYPH_TO_CYRILLIC))
_FOREIGN_LETTER_RE = re.compile("[A-Za-z" + re.escape(_FOREIGN_LETTERS) + "]")
# слово = непрерывная последовательность букв кириллицы И/ИЛИ латиницы И/ИЛИ
# любого символа-двойника из таблицы (иначе гомоглиф работал бы разделителем
# слова, а это и есть третий обход). Смешанное слово (несёт хотя бы одну
# русскую букву + хотя бы один чужой символ) - это и есть обфускация;
# ЧИСТОЕ английское слово гомоглифами не трогается вообще.
_MIXED_SCRIPT_WORD_RE = re.compile(
    "[a-zA-Zа-яёА-ЯЁ" + re.escape(_FOREIGN_LETTERS) + "]+")


def _delatinize_mixed_word(m):
    w = m.group(0)
    if _CYRILLIC_LETTER_RE.search(w) and _FOREIGN_LETTER_RE.search(w):
        return "".join(_HOMOGLYPH_TO_CYRILLIC.get(ch, ch) for ch in w)
    return w


def _yo_insensitive(pattern):
    """Делает регекс слепым к паре е/ё («двёрь» = «дверь», «кодёр» = «кодер»).

    Почему правится регекс, а не текст: в модуле есть законные словарные
    регексы С буквой ё («забегая вперёд», «за счёт», «разберём»), и подмена
    ё->е прямо в тексте сломала бы их. Разбор посимвольный, потому что наивная
    замена ломает символьный класс: `[ьияеёй]` -> `[ьия[её][её]й]` = битый
    регекс. Внутри класса достаточно, чтобы обе буквы в нём присутствовали."""
    out = []
    in_class = False
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\" and i + 1 < len(pattern):
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if ch == "[" and not in_class:
            in_class = True
        elif ch == "]" and in_class:
            in_class = False
        elif ch in "её":
            out.append("её" if in_class else "[её]")
            i += 1
            continue
        elif ch in "ЕЁ":
            out.append("ЕЁ" if in_class else "[ЕЁ]")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def normalize_unicode_obfuscation(text):
    """Юникод-нормализация ПЕРЕД любым словарным матчингом (метафоры/филлеры/
    запреты/рубрикаторы). Три шага: NFKC (схлопывает совместимые формы и
    полноширинные символы) -> удаление zero-width символов -> латинские
    гомоглифы к кириллице ВНУТРИ смешанного слова. Порядок важен: NFKC
    первым, чтобы редкие композиционные варианты тех же символов тоже
    схлопнулись до удаления zero-width/гомоглиф-замены."""
    if not text:
        return text
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ZERO_WIDTH_TRANS)
    # С13 (Р4): категорийная зачистка невидимок вместо перечисления символов -
    # combining acute U+0301 и variation selector U+FE0F в старой таблице
    # отсутствовали и снимали и метафоры, и запреты владельца
    if any(_is_invisible_mark(ch) for ch in text):
        text = "".join(ch for ch in text if not _is_invisible_mark(ch))
    text = _MIXED_SCRIPT_WORD_RE.sub(_delatinize_mixed_word, text)
    return text


def _strip_md_plain(text):
    """Снимает markdown/HTML-разметку для чистого подсчёта символов/слов
    (как strip_md в scratchpad/bench.py). Юникод-нормализация (см. выше)
    встроена сюда же - единая точка входа для ПОЧТИ всех словарных проверок
    модуля, чинить обфускацию в каждой функции по отдельности не нужно."""
    text = normalize_unicode_obfuscation(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.S)
    t = re.sub(r"__(.+?)__", r"\1", t, flags=re.S)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    return t


def _words(text):
    return re.findall(r"[а-яёА-ЯЁa-zA-Z]+", text.lower())


# --- AC2 / класс R2-1 (вода). Словари портированы дословно из scratchpad/bench.py
# (тот воспроизвёл эталонную таблицу канона знак в знак — единый источник словарей).
WATER_EVAL = set("""мощный мощная мощное мощные мощно крутой крутая крутое крутые круто невероятный невероятная невероятное невероятные невероятно
потрясающий потрясающая потрясающе уникальный уникальная уникальное уникальные эффективный эффективная эффективное эффективно
качественный качественная качественное профессиональный профессиональная инновационный инновационная современный современная
колоссальный колоссальная грандиозный масштабный масштабная топовый топовая топовое лучший лучшая лучшее идеальный идеальная идеальное
ключевой ключевая ключевое глобальный глобальная серьезный серьёзный серьезная серьёзная настоящий настоящая настоящее полноценный полноценная
значимый значимая мощнейший сильнейший важнейший невероятнейший потрясный шикарный шикарная офигенный офигенная
революционный прорывной феноменальный выдающийся впечатляющий впечатляющая эксклюзивный премиальный""".split())

WATER_INTENS = set("""очень крайне максимально невероятно безумно реально действительно буквально абсолютно полностью совершенно весьма
довольно достаточно практически фактически существенно значительно чрезвычайно исключительно поистине по-настоящему бесконечно
супер мега ультра гораздо намного крайней немало""".split())

WATER_KANC = [
    r'\bосуществл', r'\bреализов', r'\bпроизвод(ит|ят|ство)', r'\bданн(ый|ая|ое|ые|ого|ых)\b', r'\bявля(ет|ют)ся\b',
    r'представля(ет|ют) собой', r'\bв рамках\b', r'\bв целях\b', r'\bпосредством\b', r'\bнеобходимо\b',
    r'\bобеспечива(ет|ют)\b', r'\bв связи с\b', r'на сегодняшний день', r'в настоящее время',
    r'играет (важную|ключевую) роль', r'имеет место', r'\bс целью\b', r'при помощи', r'таким образом',
    r'в первую очередь', r'\bявляет\b', r'\bспособству(ет|ют)\b', r'в том числе',
    r'\bпозволя(ет|ют) (вам|тебе)\b', r'\bряд (факторов|причин)\b',
]

AI_CLICHE = [
    r'не просто [^,.\n]{1,30}, а ', r'в мире, где', r'давайте разбер', r'\bитак,', r'стоит отметить',
    r'важно понимать', r'ключевой момент', r'в современном мире', r'не секрет, что', r'как известно',
    r'подводя итог', r'\bкак говорится\b', r'в конечном (итоге|счете|счёте)', r'\bпогруз(имся|итесь)\b',
    r'\bоткрыва(ет|ют) (новые )?горизонт', r'\bэто не просто\b', r'\bдвигател(ь|и) прогресса\b',
    # 🔴 ДЫРА ПЕРЕКРЁСТНОЙ ПАРЫ (замер живого языка по решению автора, references/zhivoy-yazyk.md
    # разд.2). Словарь ловил «стоит отметить» и «важно понимать», но их зеркала
    # «важно отметить» и «стоит понимать» проходили насквозь - генератор ставит обе
    # формы одинаково часто. Замер: 0 вхождений на 1264 живых документа (608 постов
    # доноров + 15 финалов владельца + 634 ответа аудитории + 7 донор-эталонов).
    # Живут ЗДЕСЬ, а не в антисловаре живого языка: там ровно эти две записи убраны,
    # чтобы одно нарушение не печаталось двумя строками.
    r'важно отмет', r'стоит понима',
]


def check_water(text):
    """AC2, класс R2-1 (вода). R3 §C — пороги ДОСЛОВНО: WATER_EVAL потолок
    1.2/1000, WATER_INTENS потолок 1.7/1000 (WARN — R3 предупреждение 1:
    «вода НЕ разделяет верх/низ доноров», потолок против генератора, не
    разделяющий гейт силы). WATER_KANC и AI_CLICHE — HARD 0 (p90=0 у ВСЕХ
    top-групп доноров, R3 §C явно помечает HARD). Сумма — потолок 2.5/1000."""
    s = _strip_md_plain(text)
    # Закон дословности (правка владельца A7/6.1): текст в «ёлочках» - чужая
    # ДОСЛОВНАЯ цитата (голос опроса, слова ученика, самоцитата), править её
    # запрещено, поэтому и мерить её словарями воды/канцелярита нельзя
    # (прецедент 5.08: «вокальные данные» в дословной цитате Софьи ловилось
    # как канцелярит «данные»). Свой текст автора цитатами не оборачивается.
    s = re.sub(r"«[^»]*»", " ", s)
    n = max(len(s), 1)
    k = n / 1000.0
    w = _words(s)
    eval_hits = [x for x in w if x in WATER_EVAL]
    intens_hits = [x for x in w if x in WATER_INTENS]
    kanc_hits = []
    for pat in WATER_KANC:
        for m in re.finditer(pat, s, re.IGNORECASE):
            # Admission-фикс (прецедент green-фикстуры: пост владельца про
            # оферту/152-ФЗ): «данн(ый|ые|ых...)» матчит и канцелярит
            # («данный документ»), и легальный термин «персональные данные»
            # (152-ФЗ, обязательная юр-формулировка, НЕ канцелярит). Смотрим
            # 20 символов ДО совпадения на «персональн-»/«личн-» - паттерн
            # WATER_KANC (R3 §C) не трогаем, фильтруем только эту коллизию.
            if "данн" in m.group(0).lower():
                ctx = s[max(0, m.start() - 20):m.start()].lower()
                if "персональн" in ctx or "личн" in ctx:
                    continue
            kanc_hits.append(m.group(0))
    cliche_hits = []
    for pat in AI_CLICHE:
        cliche_hits += [m.group(0) for m in re.finditer(pat, s, re.IGNORECASE)]
    return {
        "eval_k": len(eval_hits) / k, "eval_hits": eval_hits,
        "intens_k": len(intens_hits) / k, "intens_hits": intens_hits,
        "kanc_k": len(kanc_hits) / k, "kanc_hits": kanc_hits,
        "cliche_k": len(cliche_hits) / k, "cliche_hits": cliche_hits,
        "sum_k": (len(eval_hits) + len(intens_hits) + len(kanc_hits) + len(cliche_hits)) / k,
    }


# --- AC3 / класс R2-5 (несуществующие словосочетания и метафоры-подмены).
# Банк ПОПОЛНЯЕМЫЙ — источник: memory feedback_no_invented_collocations_
# plain_words_only.md (по решению автора, эскалация «раз 50 говорил») + R3 §D
# (сконструированные поэтические метафоры, 0 в топе доноров) + прецедент
# владельца  («контент-завод 2.0» → метафора-подмена вместо «привлечь толпу»).
# Каждый новый пойманный прецедент дописывать СЮДА (закон файла-памяти п.по решению автора).
BANNED_COLLOCATIONS = [
    (r"стройка\s+держится", "«стройка держится» - стройка не держится, нету таких слов (по решению автора)"),
    (r"приборн(ая|ую|ой|ые)\s+панел", "«приборная панель» про аналитику - метафора-подмена (по решению автора)"),
    (r"два\s+разных\s+вида\s+спорта", "«два разных вида спорта» - выдуманная метафора (по решению автора)"),
    (r"станок,?\s+который\s+не\s+спрашивает", "«станок, который не спрашивает где хозяин» - выдумка (по решению автора)"),
    (r"переживает\s+зоопарк", "«система переживает зоопарк» - зоопарк не переживают (по решению автора)"),
    (r"список\s+заходов|заходы\s+сработали", "«заходы» в этом значении - не живой русский"),
    (r"бить\s+в\s+аудитори", "«бить в аудиторию» - выдуманный оборот"),
    (r"гоня(ю|ет|ешь|ем)\s+текст\w*\s+через", "«гонять тексты через приём» - гонять можно собак, не тексты (по решению автора)"),
    (r"скорость\s+перебора", "«скорость перебора» - набор звуков, так не говорят (по решению автора)"),
    (r"помер(ь|ить|яй)\s+числом\s+подач", "«померь числом подач» - набор звуков (по решению автора)"),
    (r"экзоскелет\s+мышления", "«экзоскелет мышления» - сконструированная поэтическая метафора (R3 §D, 0 в топе)"),
    (r"архитектур\w*\s+смысла", "«архитектура смысла» - сконструированная поэтическая метафора (R3 §D, 0 в топе)"),
    (r"контент[- ]завод\s*2\.0", "«контент-завод 2.0» как метафора-подмена вместо сути (владелец, пример класса б AC3)"),
]


def check_banned_collocations(text):
    """AC3(б), класс R2-5. Метафора-ПОДМЕНА: образ вместо сущности. Банк
    ловит ТОЛЬКО известные прецеденты (пополняемый список выше) - НОВЫЕ
    подмены ловит модельный тест независимого верификатора (AC3, последняя
    строка спеки), код не заменяет его, а закрывает рецидив."""
    hits = []
    for pat, why in BANNED_COLLOCATIONS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            s = max(0, m.start() - 20)
            hits.append((why, text[s:m.end() + 20].replace("\n", " ").strip()))
    return hits


# =============================================================================
# 4c (подэтап 4c плана 2026-08-06-content-engine-v3.md). Словарные детекторы
# канона правок v2.0. Каждый порог ниже - ЗАМЕР по корпусу фикстур, не вкус:
# green-ivan/ (12 постов, которые автор считает эталонными) + green/ (10
# донор-эталонов) + red-classes/ (47 фикстур брака). Действует закон
# калибровки этого файла (см. шапку волны 15, ~строка 1260): HARD ставится
# только там, где НИ ОДНА green-фикстура не падает; падает >=20% green - WARN.
# =============================================================================

# --- 4c/D1 (канон п.49). Метафора любая, включая бытовую: «поменять можно
# штаны. Механика поменять - это метафора» · «в ноль нельзя уйти» · «дешёвая
# дверь - непонятный набор звуков» (владелец 6.08, построчный разнос).
# 🔴 «контур» из канонного списка СНЯТ намеренно: п.20 того же канона ТРЕБУЕТ
# формулу «скилл замыкает контур целиком» («полностью юридический контур
# замкнёт для человека»). Два пункта канона противоречат друг другу, и ловить
# HARD-ом то, что соседний пункт предписывает, нельзя. Класс D2-фикстуры
# ловится без него - по «меняет механику» и «одной картиной».
METAPHOR_ROOTS = [
    (r"\bдвер[ьияеёй]\w*", "дверь"),
    (r"\bступен[ьияеёй]\w*", "ступени"),
    (r"\bлестниц\w+", "лестница"),
    (r"\bпут[ьи]\b", "путь"),
    (r"\bкарт[аыуеой]\b|\bкарту\b", "карта"),
    (r"\bдыр[аыуеой]\b|\bдыру\b", "дыра"),
    (r"\bмостик\w*", "мостик"),
    (r"\bфундамент\w*", "фундамент"),
    (r"\bв\s+ноль\b", "в ноль"),
    (r"\bменя\w+\s+механик\w+", "меняет механику"),
    (r"\bарк[аиуеой]\b", "арка"),
    (r"\bодной\s+картиной\b", "одной картиной"),
    (r"\bот\s+бана\s+до\s+потока\b", "от бана до потока"),
]

# Белый список БУКВАЛЬНЫХ употреблений (канон п.49, разрешение противоречия
# №4: образ ВМЕСТО сущности - нельзя, слово в прямом значении - можно).
# «карта» - имя реального артефакта, который скилл выдаёт («карта смыслов»,
# «карту сегментов», «карту продуктов»); улика по корпусу: green-ivan/
# inf18-0608.txt несёт «выдаёт карту от бесплатного к дорогому» и «Карту
# сегментов он вообще не построит» - это выход инструмента, не образ.
# Если пост ХОТЯ БЫ РАЗ называет артефакт полным именем, корень «карта»
# в этом посте считается служебным термином и не ловится.
METAPHOR_ARTIFACT_WHITELIST = re.compile(
    r"карт\w*\s+(?:смыслов|сегментов|продуктов|воронк\w+|контента|запуска|"
    r"канала|ниши|аудитории|источников|клиента|болей|возражений)", re.IGNORECASE)

# 🔴 по решению автора (ложный BLOCK на живом посте): БАНКОВСКАЯ карта - буквальный
# предмет, не образ. Канон <твой-продукт> дословно несёт «установка ... даже без
# иностранной карты» - гейт валил перенос канон-факта в пост. Исключение
# PER-HIT (не пост-левел, в отличие от WHITELIST выше): совпадение корня
# «карта» гасится, только если в ±30 знаках вокруг стоит банковский контекст.
# Метафора «покажу карту целиком» этим не спасается - у неё контекста нет.
METAPHOR_BANK_CARD_CTX = re.compile(
    r"иностранн\w*|банковск\w*|зарубежн\w*|виртуальн\w*|дебетов\w*|"
    r"кредитн\w*|оплат\w*|плат[её]ж\w*|привяза\w*", re.IGNORECASE)


def check_metaphor_roots(text):
    """4c/D1, канон п.49. HARD. Переносное значение вместо буквального.
    ADMISSION по корпусу: 12 green-ivan дают 3 срабатывания, из них 2 -
    служебное «карту сегментов/продуктов» в inf18 (гасится белым списком),
    остаётся 1 (b17-3-0508 «одной картиной», пост 5.08, СТАРШЕ правила
    п.49 от 6.08 - снимается флагом --allow-metaphor с печатью причины).
    Итог 1/12 = 8.3% < 20%, значит по закону калибровки статус HARD."""
    plain = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    artifact_ok = bool(METAPHOR_ARTIFACT_WHITELIST.search(plain))

    def _scan(t):
        out = []
        for pat, label in METAPHOR_ROOTS:
            if label == "карта" and artifact_ok:
                continue
            # _yo_insensitive - п.6 скептик Р3: «двёрь»/«ступёни» обходили корни,
            # у которых ё стоит в ОСНОВЕ, а не в окончании [ьияеёй].
            for m in re.finditer(_yo_insensitive(pat), t, re.IGNORECASE):
                s = max(0, m.start() - 30)
                snippet = t[s:m.end() + 30].replace("\n", " ").strip()
                # по решению автора: банковская карта - буквальный предмет (per-hit,
                # см. METAPHOR_BANK_CARD_CTX выше)
                if label == "карта" and METAPHOR_BANK_CARD_CTX.search(snippet):
                    continue
                out.append((label, snippet))
        return out

    hits = _scan(plain)
    # 🔴 С13 скептик Р4: курсив «д_в_ерь» и дефис «дв-ерь» рвали корень надвое.
    # Второй проход по копии без внутрисловных разделителей; корни здесь
    # привязаны к \b, поэтому склейка может только УБРАТЬ границу слова, но не
    # создать новое совпадение на честном тексте («мини-карта» -> «миникарта»
    # перестаёт матчить, а не начинает).
    glued = _strip_inword_separators(plain)
    if glued != plain:
        hits += _dedup_second_pass(
            hits, _scan(glued),
            lambda h: (h[0], _INWORD_SEP_RE.sub("", h[1]).lower()))
    return hits


# --- 4c/D3 (канон п.57, «гонять можно собак»). Выдуманная связка глагол +
# существительное. Пополняет тот же банк, что и D2 (метафора-подмена):
# оба класса печатаются одной строкой FAIL - это один закон «языка, которого
# нет», и разводить его на два блокирующих правила смысла нет.
INVENTED_VERB_NOUN = [
    (r"гоня(ю|ет|ешь|ем|ют)\s+пост\w*", "«гонять посты» - гонять можно собак (по решению автора, п.57)"),
    (r"кача(ю|ет|ешь|ем|ют)\s+довери", "«качать доверие» - выдуманная связка (п.57)"),
    (r"кру(чу|тит|тишь|тим|тят)\s+смысл\w*", "«крутить смыслы» - выдуманная связка (п.57)"),
    (r"охват\w*\s+(?:по)?ед(ет|ут)", "«охват поедет» - выдуманная связка (п.57)"),
    (r"лови(ть|шь|т)\s+внимани\w*\s+в\s+", "«ловить внимание в …» - выдуманная связка (п.57)"),
]


def check_invented_verb_noun(text):
    """4c/D3, канон п.57. HARD (в общей строке с D2). Глагол, который с этим
    существительным не сочетается. ADMISSION: 0/12 green-ivan, 0/10 донор-
    эталонов, ловит D3-фикстуру."""
    plain = _strip_md_plain(text)
    hits = []
    for pat, why in INVENTED_VERB_NOUN:
        for m in re.finditer(pat, plain, re.IGNORECASE):
            s = max(0, m.start() - 20)
            hits.append((why, plain[s:m.end() + 20].replace("\n", " ").strip()))
    return hits


# --- 4c/B20 (канон п.35). Филлеры: «эта вещь не несёт никакой пользы и
# ценности» (владелец 6.08). Каждое предложение обязано нести факт, действие,
# цифру или вывод.
FILLER_PATTERNS = [
    r"скажу\s+вещь", r"держи\s+инструмент", r"отдам\s+штуку",
    r"вам\s+в\s+самый\s+раз", r"тебе\s+в\s+самый\s+раз",
    r"коротко\s+и\s+по\s+делу", r"скажу\s+прямо", r"без\s+лишних\s+слов",
    r"что\s+тут\s+скажешь", r"забегая\s+вперёд", r"как\s+говорится",
    r"не\s+буду\s+ходить\s+вокруг", r"давайте\s+честно", r"будем\s+честны",
]


def check_fillers(text):
    """4c/B20, канон п.35. HARD. ADMISSION: 0/12 green-ivan и 0/10 донор-
    эталонов не несут ни одного филлера, B20-фикстура несёт три («Скажу
    вещь», «Держи инструмент», «вам в самый раз») - 0% падения green,
    статус HARD по закону калибровки."""
    plain = _strip_md_plain(text)
    hits = []
    for pat in FILLER_PATTERNS:
        for m in re.finditer(pat, plain, re.IGNORECASE):
            s = max(0, m.start() - 15)
            hits.append(plain[s:m.end() + 40].replace("\n", " ").strip())
    return hits


# =============================================================================
# МЁРТВЫЙ ЯЗЫК: ЛЕКСИКА (антисловарь абстракций, замер). Фаза 9.
# =============================================================================
# ПОЧЕМУ БЛОК ЕСТЬ. Владелец по решению автора дословно: «Очень много абстракций. Мёртвый
# язык. Мы должны говорить на РЕАЛЬНОМ языке, на котором люди пишут, говорят,
# спрашивают, комментарии пишут, думают, посты делают - а не на абстрактном».
# Рядом стоит блок «мёртвые конструкции К1-К11» - он ловит мёртвый СИНТАКСИС.
# Здесь ловятся мёртвые СЛОВА, и это отдельный класс: корпус red (68 фикстур
# брака) по этой лексике пуст ПОЛНОСТЬЮ, то есть до этой редакции машина не ловила её
# ничем - ни словарями воды, ни метафорами, ни филлерами, ни humaniser (кат. 4
# и 13 живут только в промпте, а промпт пропускается ровно тогда, когда модель
# уже сползла в абстракцию, см. memory feedback_critical_route_needs_code_gate).
#
# ЗАМЕР (по решению автора, воспроизведение - ресёрч 9.1 + references/zhivoy-yazyk.md):
#   донор     608 постов, 86 483 слова -> TIER-A: 0 вхождений (100% документов чисты)
#   владелец  15 док. (12 green-ivan + 3 эталона голоса) -> TIER-A: 0
#   green-fix 7 донор-эталонов тестового набора -> TIER-A: 0
#   survey    634 свободных ответа аудитории -> TIER-A: 0
#   ---------------------------------------------------------------- ИТОГО 1264
#   LLM       33 машинных черновика -> TIER-A в 8 из 33, максимум 8 на документ
#
# 🔴 Д114 (скептик-раунд 39, по решению автора). КАЛИБРОВОЧНЫЙ КОРПУС РАСШИРЕН
# ТЕХНО-ДОМЕНОМ - и первый же прогон нашёл РЕГРЕСС НА ПРИНЯТОМ ТЕКСТЕ.
# ЧТО БЫЛО НЕ ТАК С ЗАМЕРОМ ВЫШЕ. 1264 документа - это коучинг и маркетинг:
# доноры-инфобизнес, финалы владельца, ответы аудитории. Ниша владельца
# (вайбкодинг: код, боты, рендер, БД) в выборку не входила ВООБЩЕ, а восемь
# корней TIER-A стояли без правой/левой границы слова и резали законные слова
# именно этого домена. Ноль на 608 донор-постах не доказывал ничего про
# «набережную», «спецификацию» и «прозрачность фона» - он доказывал, что
# доноры про них не пишут.
# РАСШИРЕННЫЙ КОРПУС (замер, скрипт-репро - `r40_measure.py`,
# метод тот же: `check_dead_language` живого модуля, дедуп спанов, снятие
# кавычек):
#   + archive    17 файлов .business/voice-corpus/_post-skill-archive-
#                ivan/references-archive/*.md (батчи AI-tells с ДОСЛОВНЫМИ
#                постами владельца внутри + блюпринт + слепок голоса)
#   + A-telegram 3 эталона голоса владельца
#   ------------------------------------------------ ИТОГО 650 док. + survey
# ДО ФИКСА: 31 hard-hit на 7 файлах archive. Из них БРАК ГРАНИЦЫ КОРНЯ - 10
# уникальных вхождений: «набережной» ловилось корнем `бережн` 6 раз,
# «спецификацию»/«спецификации» корнем `специфик` 4 раза. Ещё 3 вхождения
# («специфики», «специфику») - НЕ брак границы, а само словарное слово; они
# сняты не границей, а понижением записи в TIER-B (см. там). В счёте
# `check_dead_language` те же находки дают 31 -> 16 из-за второго прохода по
# тексту без внутрисловных разделителей (Д111), который на архивных файлах
# со «склейками» даёт дубль-хит на то же слово. Гейт блокировал текст,
# который владелец УЖЕ ПРИНЯЛ И ОПУБЛИКОВАЛ (батч-7: целый пост про прогулку
# по набережной с 14 заявками).
# 🔴 ЗАКОН ГРАНИЦЫ (введён этим фиксом, применять к КАЖДОЙ новой записи):
# HARD-корень обязан ловить РОВНО заявленное слово. Срабатывание, где
# пойманная подстрока принадлежит ДРУГОМУ слову («набережной» != «бережный»,
# «спецификацию» != «специфика», «доставки» != «достижения», «темой» !=
# «тем, чтобы»), - брак регекса, чинится границей `\b` / negative-lookahead /
# полной фразой, а НЕ флагом `--allow-dead-lexicon` на выдаче.
# ПОСЛЕ ФИКСА: брак границы = 0 на всём расширенном корпусе (см. таблицу
# рекалибровки в `references/zhivoy-yazyk.md` разд.1).
# 🔴 ЧТО ОСТАЛОСЬ СРАБАТЫВАТЬ НА archive И ПОЧЕМУ ЭТО НЕ БРАК (называется
# поимённо, чтобы следующий раунд не чинил работу гейта как дефект):
# `методологи` x4 (LLM 10) · `инфраструктур` x2 (LLM 5) · `аутентичн` x3
# (только `_voice-TEMPLATE.md` - МЕТА-документ аналитика «маркер аутентичности»,
# не пост) · `в данном случае` x2 (мета-разбор AI-tells, не пост). Это САМИ
# СЛОВАРНЫЕ СЛОВА в своём прямом значении, то есть работа гейта. Довести
# archive до нуля можно было бы только выбросив `методологи` - ровно ту
# запись, на которой стоит контроль всего модуля (10 вхождений у машины
# против 4 у людей). Файлы `references-archive/*.md` - не посты и никогда не
# были green-фикстурой: это смешанные документы, где дословный пост владельца
# соседствует с мета-языком разбора. Гейт на них не гоняется.
# ПОНИЖЕНО В TIER-B ЗАМЕРОМ (не догадкой): `специфик`, `целостност`,
# `прозрачност` - обоснование поимённо у каждой записи в TIER-B ниже.
#
# ПОРОГИ И ЧЕМ ОБОСНОВАНЫ (закон калибровки модуля: HARD только там, где не
# падает НИ ОДНА green-фикстура):
#   1. лексический HARD: любое вхождение TIER-A = FAIL. MAX на принятом
#      корпусе 0.00 на ВСЕХ четырёх живых корпусах - запас бесконечный.
#   2. плотностный HARD: count(A+B+WARN) >= 4 на посте >= 500 знаков = FAIL.
#      MAX на живом корпусе 3 (donor-1558, 1432 знака), у владельца и
#      green-фикстур 0. Порог стоит на ЕДИНИЦУ выше абсолютного максимума
#      608 живых постов. Ниже 500 знаков плотность не различает (одно
#      вхождение на 242 знаках даёт 4.13), там работает только порог 1.
#   3. TIER-B и WARN поштучно = WARN с заменой. HARD тут был бы регрессом:
#      TIER-B срабатывает на 4.3% донор-корпуса, WARN на 2.6% (Д110, скептик-
#      раунд 38, по решению автора: было заявлено 4.6%/7.1%, живой пересчёт по
#      отгруженному словарю check_dead_language на corpus-12m.json, 608
#      постов, дедуп спанов + снятие кавычек = 4.3%/2.6%, страж -
#      test_dead_lex_b_warn_percentages_match_corpus в tests/run-tests.py)
#      (memory feedback_gate_blocking_whole_corpus_is_regression).
#
# ЧЕГО ЗДЕСЬ НЕТ И ПОЧЕМУ. 48 кандидатов отсеяно замером как ЖИВЫЕ, запрещать
# их нельзя: «точка А/точка Б» (8 у доноров, владелец назвал это примером
# абстракции - замер показал обратное), «ценность» (7 доноров + 4 владельца),
# «системный подход» (3), «новый уровень» (5), «понимание» (16 в survey),
# «видение»/«экосистема» (у владельца). Полный список - references/zhivoy-yazyk.md
# разд.5. Пересечений с существующими словарями нет: «на пути к»/«фундаментальный»
# держит METAPHOR_ROOTS, «эффективный»/«качественный» - WATER_EVAL, «в первую
# очередь» - WATER_KANC, «важно отметить»/«стоит понимать» - AI_CLICHE (туда они
# и дописаны по решению автора как перекрёстные пары, отсюда убраны).
#
# ИВАНО-СПЕЦИФИЧНОГО В СЛОВАРЕ НЕТ НИ ОДНОЙ ЗАПИСИ - блок раздаётся ученикам
# как есть и ничего в их постах не ломает (feedback_isolate_ivan_specific_...).
#
# Формат записи: (регекс, «мёртвое слово», живая замена, улика корпуса).
# Живая замена берётся ДОСЛОВНО из references/zhivoy-yazyk.md разд.4 - гейт не
# запрещает термин, а даёт целевой язык: переписывать будет модель, и ей нужно
# ЧЕМ заменить. Вычеркнутая без замены абстракция возвращается на следующей
# итерации (тот же закон, что у metaphor-to-literal.md для образов).

_DL_PLAN = ("«пошаговый план» / «вот план, делаешь пункт 1-2-3» / «схема»", "donor-2008, donor-231, donor-341")
_DL_AVTOMAT = ("«на автомате» / «работает как часы» / «продается на автомате»", "donor-59, donor-386, survey v4 стр53")
_DL_CIFRA = ("«20 постов в день за 2 часа» / «ушло 15 минут» / «в 10 раз быстрее»", "donor-1896, donor-341")
_DL_SKRIN = ("«показываю цифры и результаты» / «скрины выше» / «200-300к/мес на автомате»", "donor-85, donor-39")
_DL_MASHINA = ("«у меня работает целая машина: ИИ контент-завод» / «500+ единиц контента в месяц»", "donor-81")
_DL_KOMMENT = ("«8К комментариев» / «человек читает и пишет в ответ»", "donor-103, ivan-final-0")
_DL_STRAH = ("«было страшно» / «много неопределенности» / «иду в страх, иду в боль»", "donor-1421, donor-1623")
_DL_DOLGI = ("«Закрыл долги, убрал тревожность и построил себе доход» / «набрал 4.5к подписчиков»", "donor-257, survey v4 стр4")
_DL_SROK = ("«через год» / «через полгода» / «через 2 месяца» / «за 4 месяца»", "donor-1480, donor-1896, donor-81")
_DL_NEHVATAET = ("«Не хватает времени честно говоря» / «тону в структуре» / «включается перфекционист+самозванец»", "survey v4 стр14/стр27/стр9")
_DL_NISHA = ("«в моей нише» / «мне не подходит» / «99% информации не применимы ЗДЕСЬ и СЕЙЧАС»", "survey v4 стр42, donor-71")
_DL_HOCHU = ("«Хочу свой бизнес» / «Хочу чтобы его наконец-то начали покупать» / «Ускориться с подготовкой продукта»", "survey v4 стр52/стр47/стр79")
_DL_MOZHNO = ("«можно» / «получится» / «я пошёл завтракать, потому что ушло 15 минут»", "donor-1896")
_DL_RESHAET = ("«решает» / «главный»", "donor-79, donor-272")
_DL_PROBLEMA = ("«вот в чём проблема:» и дальше прямое двоеточие с фактом", "donor-52")
_DL_SDELAL = ("«собрал» / «поставил» / «настроил» / «сделал»", "survey v4 стр2")
_DL_VMESTE = ("«вместе» / «в одном месте»", "donor-47")
_DL_SHTUKA = ("«штука» / «момент» / «вещь» или перечисление конкретных пунктов", "donor-1474 (список из 18 пунктов вместо «аспектов»)")
_DL_OBYCHNO = ("«обычно» / «у меня было так:» / «я 8 лет в онлайн-продажах»", "donor-231")
_DL_KONEC = ("пост просто заканчивается фактом или вопросом, без итоговой рамки", "все 7 green-fix донор-эталонов: ни одного итогового оборота")

# --- TIER-A: HARD-ядро. 64 записей в коде (Д114, скептик-раунд 39,
# по решению автора: было 67, три записи - `специфик`, `целостност`, `прозрачност` -
# понижены в TIER-B замером по расширенному корпусу, обоснование у каждой
# записи там; счётчик ниже = живой len(DEAD_LEX_A), страж
# test_dead_lex_counts_match_docs держит ВСЕ ТРИ тира).
# Историческая справка Д109 (скептик-раунд 38, по решению автора): до Д114 в списке
# было 67 записей, а комментарий заявлял «66 + 67-я «важно отметить» живёт в
# AI_CLICHE» - «важно отметить» в этом списке НЕТ ни одной записи, оно только
# в AI_CLICHE, счёт правки был устаревшим, а не офсетом. С Д109 счётчик
# ОБЯЗАН равняться len() живого словаря во всех домах.
# 0 вхождений на 1264 живых документа - самая жёсткая улика в модуле.
DEAD_LEX_A = [
    (r'методологи',                     'методология',              *_DL_PLAN),
    (r'инфраструктур',                  'инфраструктура',           *_DL_MASHINA),
    # Д114: `бережн` -> `\bбережн`. БЕЗ левой границы корень резал «набережной»
    # (6 вхождений в принятых постах владельца, `references-archive/ai-tells-
    # batch-7.md` и `-8.md`, включая пост «прогулка по Геленджикской набережной
    # + 14 заявок»). С границей: 0 ложняков на расширенном корпусе, живое
    # срабатывание у машины сохранено («принцип бережного контекста»,
    # seo/guide-kontekst/draft.md - именно то, ради чего запись заведена).
    (r'\bбережн',                       'бережный',                 *_DL_STRAH),
    (r'ресурсност',                     'ресурсность',              *_DL_NEHVATAET),
    (r'\bресурсн',                      'ресурсный',                *_DL_NEHVATAET),
    (r'внутренн\w*\s+ресурс',           'внутренний ресурс',        *_DL_NEHVATAET),
    (r'синерги',                        'синергия',                 *_DL_VMESTE),
    # Д114: `целостност` понижен в TIER-B (см. там). Прилагательное остаётся
    # HARD - у него техно-омонима нет: «целостный подход» это абстракция
    # всегда, «целостность базы/данных/индекса» - стандартный термин БД.
    (r'целостн(ый|ая|ое|ые|ого|ым|ой)', 'целостный',                *_DL_VMESTE),
    (r'\bгармони(я|и|ю|ей)\b',          'гармония',                 *_DL_VMESTE),
    (r'гармоничн',                      'гармоничный',              *_DL_VMESTE),
    (r'комплексн\w*\s+подход',          'комплексный подход',       *_DL_PLAN),
    (r'комплексн',                      'комплексный',              *_DL_VMESTE),
    (r'проактивност',                   'проактивность',            *_DL_HOCHU),
    (r'целеполагани',                   'целеполагание',            *_DL_HOCHU),
    (r'самореализаци',                  'самореализация',           *_DL_HOCHU),
    (r'самоценност',                    'самоценность',             *_DL_HOCHU),
    (r'аутентичн',                      'аутентичный',              *_DL_HOCHU),
    (r'глубинн\w*\s+смысл',             'глубинные смыслы',         *_DL_HOCHU),
    (r'устойчивост',                    'устойчивость',             *_DL_SROK),
    (r'результативност',                'результативность',         *_DL_SKRIN),
    # Д114: `прозрачност` понижен в TIER-B (см. там) - «прозрачность фона 40%»
    # это CSS/дизайн, а не абстракция.
    (r'\bаспект',                       'аспект',                   *_DL_SHTUKA),
    (r'формировани(е|я|ю|ем)\b',        'формирование',             *_DL_SDELAL),
    (r'пользовательск\w*\s+опыт',       'пользовательский опыт',    *_DL_KOMMENT),
    (r'бесшовн',                        'бесшовный',                *_DL_KOMMENT),
    (r'всесторонн',                     'всесторонний',             *_DL_PLAN),
    (r'многогранн',                     'многогранный',             *_DL_PLAN),
    (r'индивидуальн\w*\s+подход',       'индивидуальный подход',    *_DL_PLAN),
    (r'грамотн\w*\s+подход',            'грамотный подход',         *_DL_PLAN),
    # Д114: обрубок `дост` ловил «инструмент для доступа к базе» и «инструмент
    # для доставки сообщений в канал» - оба буквальные и оба из ниши владельца.
    # Объект связки назван полностью.
    (r'инструмент\w*\s+для\s+достижени', 'инструмент для достижения', *_DL_PLAN),
    (r'в\s+основе\s+лежит',             'в основе лежит',           *_DL_PROBLEMA),
    (r'речь\s+идет\s+о\b',              'речь идёт о',              *_DL_PROBLEMA),
    (r'речь\s+о\s+том',                 'речь о том, что',          *_DL_PROBLEMA),
    (r'состо(ит|ят)\s+в\s+том',         'состоит в том, что',       *_DL_PROBLEMA),
    (r'на\s+практике\s+это\s+означа',   'на практике это означает', *_DL_PROBLEMA),
    (r'в\s+данном\s+случае',            'в данном случае',          *_DL_PROBLEMA),
    (r'раскры\w*\s+потенциал',          'раскрыть потенциал',       *_DL_DOLGI),
    (r'личностн\w*\s+рост',             'личностный рост',          *_DL_DOLGI),
    (r'квантов\w*\s+скач',              'квантовый скачок',         *_DL_DOLGI),
    (r'инвестиц\w*\s+в\s+себя',         'инвестиция в себя',        *_DL_DOLGI),
    (r'внедри\w*\s+в\s+жизн',           'внедрить в жизнь',         *_DL_SDELAL),
    (r'за\s+счет\s+грамотн',            'за счёт грамотного',       *_DL_SDELAL),
    (r'оптимизир\w*\s+процесс',         'оптимизировать процессы',  *_DL_CIFRA),
    (r'максимизир',                     'максимизировать',          *_DL_CIFRA),
    (r'в\s+долгосрочн\w*\s+перспектив', 'в долгосрочной перспективе', *_DL_SROK),
    (r'во\s+главу\s+угла',              'во главу угла',            *_DL_RESHAET),
    (r'имеет\s+значени',                'имеет значение',           *_DL_RESHAET),
    (r'представля\w*\s+интерес',        'представляет интерес',     *_DL_RESHAET),
    # 🔴 Д115 (скептик-раунд 39, по решению автора): КОД БАНИЛ ЧЕТЫРЕ ОБЪЕКТА, ДОК
    # ДОКУМЕНТИРОВАЛ ОДИН. Замер по расширенному корпусу (650 док. + 634
    # survey + 33 LLM-черновика): все ЧЕТЫРЕ связки дают 0 живых вхождений и 0
    # у машины, ни одну выбрасывать замер не велит. Поэтому чинится не код, а
    # РАСХОЖДЕНИЕ ДОМОВ: все четыре объекта названы поимённо в
    # `references/zhivoy-yazyk.md` разд.3.1, а у строки «направлен на» разд.5
    # («живое», 2-3 вхождения у доноров) стоит оговорка про эти четыре связки.
    # Половинка «направлен на» сама по себе живая и НЕ ловится - ловится
    # только связка. Плюс левая граница `\b`: без неё «перенаправление на …»
    # (donor-51) попадало под `направлен\w*` серединой слова - тот же класс
    # брака, что Д114.
    (r'\bнаправлен\w*\s+на\s+(?:достижени|повышени|формировани|развити)',
                                        'направлен на достижение',  *_DL_MOZHNO),
    (r'позволя\w*\s+дост(ич|игн)',      'позволяет достичь',        *_DL_MOZHNO),
    (r'да(ет|ют)\s+возможност',         'даёт возможность',         *_DL_MOZHNO),
    # Д114: `над\s+тем` без хвоста ловил «я работал над темой этого поста три
    # дня» - живая фраза владельца. Ловится ПОЛНАЯ связка с «чтобы», она и
    # есть мёртвая («работает над тем, чтобы улучшить...»); «над темой» мимо.
    (r'работа\w*\s+над\s+тем\s*,?\s*чтобы', 'работает над тем, чтобы', *_DL_MOZHNO),
    (r'наход(ит|ят)ся\s+в\s+процессе',  'находится в процессе',     *_DL_MOZHNO),
    (r'вовлека\w*\s+аудитор',           'вовлекать аудиторию',      *_DL_KOMMENT),
    (r'зон\w*\s+комфорт',               'зона комфорта',            *_DL_STRAH),
    (r'личн\w*\s+границ',               'личные границы',           *_DL_NEHVATAET),
    # «стоит понимать» вынесено в AI_CLICHE (перекрёстная пара к «важно понимать»)
    (r'следует\s+помнить|стоит\s+учитыва', 'следует помнить / стоит учитывать', *_DL_OBYCHNO),
    (r'как\s+показывает\s+практик',     'как показывает практика',  *_DL_OBYCHNO),
    (r'зачастую',                       'зачастую',                 *_DL_OBYCHNO),
    (r'\bтем\s+самым\b',                'тем самым',                *_DL_OBYCHNO),
    (r'\bболее\s+того\b',               'более того',               *_DL_OBYCHNO),
    (r'как\s+результат\b',              'как результат',            *_DL_OBYCHNO),
    # Д114: одна половина связки ловила буквальную сцену - «с одной стороны
    # экрана бот, с другой я в камеру». Мёртвая тут ПАРНАЯ риторическая
    # конструкция, её и требуем: вторая половина обязана найтись в пределах
    # 400 знаков. Проверка сделана ЗАГЛЯДЫВАНИЕМ (`(?=...)`), а не захватом,
    # намеренно: захват растянул бы спан совпадения на 400 знаков, и дедуп по
    # перекрытию в `_dead_lex_scan` (побеждает более ДЛИННОЕ совпадение) съел
    # бы все прочие находки внутри этого куска, занизив плотностный порог 2.
    (r'с\s+одной\s+стороны(?=[\s\S]{0,400}?с\s+другой\s+стороны)',
                                        'с одной стороны … с другой стороны', *_DL_OBYCHNO),
    (r'резюмируя|исходя\s+из\s+вышесказанн', 'резюмируя / исходя из вышесказанного', *_DL_KONEC),
    (r'в\s+итоге\s+можно\s+сказать',    'в итоге можно сказать',    *_DL_KONEC),
]

# --- TIER-B: 28 записей, 1-2 вхождения на 86 483 слова доноров, 0 у владельца
# и 0 в survey. Печатается WARN поштучно (в HARD не поднято: 4.3% срабатываний
# на донор-корпусе = регресс, Д110 скептик-раунда 38 - см. шапку модуля),
# но СЧИТАЕТСЯ в плотностном пороге 2.
# Улики живых вхождений (шутка, пародия, чужая прямая речь) - в
# references/zhivoy-yazyk.md разд.3.2.
# 🔴 Д114 (скептик-раунд 39, по решению автора): три записи ПОНИЖЕНЫ СЮДА из TIER-A
# замером по расширенному корпусу - у каждой в нише владельца есть законный
# техно-омоним, а доказательства мёртвого употребления нет ни в одном корпусе.
# Понижение, а не удаление: писателю по-прежнему печатается живая замена и
# слово по-прежнему считается в плотностном пороге 2, но честный технический
# текст больше не блокируется HARD-ом (memory
# feedback_gate_blocking_whole_corpus_is_regression).
DEAD_LEX_B = [
    # Д114. `специфик` без границ ловил «спецификацию» (4 вхождения в постах
    # владельца, `ai-tells-batch-8.md` - архив ВЫНЕСЕН ИЗ РАЗДАЧИ скилла,
    # живой путь на момент этой правки .business/voice-corpus/
    # _post-skill-archive-ivan/references-archive/, замер зафиксирован в
    # changelog v2.4-r39): «Claude генерит
    # спецификацию под Remotion»; 3 вхождения в LLM-черновиках - и все три
    # тоже про ТЗ, не про абстракцию). Границы добавлены: `\b` слева +
    # negative-lookahead на `аци`, «спецификация»/«спецификацию» мимо. После
    # сужения улик мёртвого употребления не осталось НИ ОДНОЙ (LLM 0), а
    # живое есть - «под их специфику» в посте владельца, batch-8. HARD без
    # улики = ложняк по построению, поэтому TIER-B.
    (r'\bспецифик(?!аци)',              'специфика',                *_DL_NISHA),
    # Д114. «целостность базы/данных/индекса» - стандартный термин БД, у
    # владельца это рабочее слово ниши. 0 вхождений в обоих направлениях на
    # 1284 живых документах и 33 LLM-черновиках: доказательства для HARD нет,
    # а цена ложняка - блок честного текста про код. Прилагательное
    # «целостный» осталось в TIER-A: у него техно-омонима нет.
    (r'целостност',                     'целостность',              *_DL_VMESTE),
    # Д114. «прозрачность фона 40%» - CSS/дизайн, «прозрачность» как
    # абстракция («прозрачность процессов») в корпусе не встретилась ни разу
    # (0/0, тот же замер). Тот же размен, что у целостности.
    (r'прозрачност',                    'прозрачность',             *_DL_SKRIN),
    (r'продуктивност',                  'продуктивность',           *_DL_CIFRA),
    (r'осознанност',                    'осознанность',             *_DL_HOCHU),
    (r'осознанн(ый|ая|ое|ые|ого|ым|ой|о)\b', 'осознанный',          *_DL_HOCHU),
    (r'осознани(е|я|ю|ем|и)\b',         'осознание',                *_DL_HOCHU),
    (r'релевантн',                      'релевантный',              *_DL_NISHA),
    (r'намерени(е|я|ю|ем|и)\b',         'намерение',                *_DL_HOCHU),
    (r'выстро\w*\s+систем',             'выстроить систему',        *_DL_AVTOMAT),
    (r'парадигм',                       'парадигма',                *_DL_PROBLEMA),
    (r'истинн\w*\s+(желани|ценност)',   'истинные желания / ценности', *_DL_HOCHU),
    (r'истинн',                         'истинный',                 *_DL_HOCHU),
    (r'правильн\w*\s+подход',           'правильный подход',        *_DL_PLAN),
    (r'изобили',                        'изобилие',                 *_DL_DOLGI),
    (r'\bмисси(я|и|ю|ей)\b',            'миссия',                   *_DL_HOCHU),
    (r'экологичн',                      'экологичный',              *_DL_SDELAL),
    (r'органичн',                       'органичный',               *_DL_SDELAL),
    (r'повы(с|ш)\w*\s+эффективност',    'повысить эффективность',   *_DL_CIFRA),
    (r'работ\w*\s+над\s+собой',         'работа над собой',         *_DL_STRAH),
    (r'не\s+менее\s+важно|немаловажн',  'не менее важно / немаловажно', *_DL_OBYCHNO),
    (r'стратеги\w*\s+роста',            'стратегия роста',          *_DL_SKRIN),
    (r'помога\w*\s+(понять|осознать)',  'помогает понять / осознать', *_DL_MOZHNO),
    (r'открыва\w*\s+возможност',        'открывает возможности',    *_DL_MOZHNO),
    (r'при\s+этом\s+важно',             'при этом важно',           *_DL_OBYCHNO),
    (r'заключа(ет|ют)ся\s+в\s+том',     'заключается в том, что',   *_DL_PROBLEMA),
    (r'в\s+свою\s+очередь',             'в свою очередь',           *_DL_OBYCHNO),
    (r'тем\s+не\s+менее',               'тем не менее',             *_DL_OBYCHNO),
]

# --- WARN-слой: 19 записей (Д109, скептик-раунд 38, по решению автора: было заявлено
# 18, живой len(DEAD_LEX_WARN) даёт 19 - «функционал/широкие возможности» и
# «что это даёт/главное понять» в справочнике сжаты в общие табличные строки
# через «·», а в коде это отдельные регекс-записи; число ниже = len() кода).
# У людей почти не встречаются, но регекс неизбежно ловит и ЗАКОННОЕ
# употребление (метрика, настройка, деталь продукта), поэтому HARD невозможен
# ни при каком замере. Считаются в плотностном пороге 2.
DEAD_LEX_WARN = [
    (r'параметр',                       'параметр',                 *_DL_SHTUKA),
    (r'критери(й|я|ю|ем|и|ев|ям|ями)\b', 'критерий',                *_DL_SHTUKA),
    (r'механизм',                       'механизм',                 *_DL_AVTOMAT),
    (r'\bэффект(ы|а|у|ом|е|ов|ам|ами|ах)?\b', 'эффект',             *_DL_SKRIN),
    (r'динамик',                        'динамика',                 *_DL_SKRIN),
    (r'планировани(е|я|ю|ем)\b',        'планирование',             *_DL_PLAN),
    (r'функционал',                     'функционал',               *_DL_SHTUKA),
    (r'широк\w*\s+возможност',          'широкие возможности',      *_DL_SHTUKA),
    (r'концепци',                       'концепция',                *_DL_PLAN),
    (r'философи',                       'философия',                *_DL_PROBLEMA),
    (r'кроме\s+того|помимо\s+этого',    'кроме того / помимо этого', *_DL_OBYCHNO),
    (r'апгрейд',                        'апгрейд',                  *_DL_SDELAL),
    (r'интегрир',                       'интегрировать',            *_DL_SDELAL),
    (r'прокачк',                        'прокачка',                 *_DL_DOLGI),
    (r'проработк',                      'проработка',               *_DL_SDELAL),
    (r'гибкост|универсальност|надежност', 'гибкость / универсальность / надёжность', *_DL_SHTUKA),
    (r'вовлеченност',                   'вовлечённость',            *_DL_KOMMENT),
    (r'что\s+это\s+дает',               'что это даёт',             *_DL_MOZHNO),
    (r'главное\s+понять',               'главное понять',           *_DL_PROBLEMA),
]

# Порог 2 (плотностный). Максимум на живом корпусе = 3 вхождения на пост,
# у владельца и green-фикстур = 0. Ставим на единицу выше максимума.
DEAD_LEX_DENSITY_MAX = 3
DEAD_LEX_MIN_CHARS = 500

_DEAD_LEX_TIERS = (("A", DEAD_LEX_A), ("B", DEAD_LEX_B), ("WARN", DEAD_LEX_WARN))
_DEAD_LEX_RANK = {"A": 0, "B": 1, "WARN": 2}


def _dead_lex_plain(text):
    """Очистка перед замером - ровно та же логика, что у check_water, ПЛЮС
    прямые кавычки. Доноры цитируют чужой мёртвый язык именно прямыми
    (`"качественный контент"`, donor-81 и donor-52), и без этого гейт наказывал
    бы пародию на мёртвый язык вместо самого мёртвого языка (ресёрч разд.3)."""
    s = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    s = re.sub(r"«[^»]*»", " ", s)
    s = re.sub(r"„[^“”]*[“”]", " ", s)
    s = re.sub(r"“[^”]*”", " ", s)
    s = re.sub(r'"[^"\n]{0,200}"', " ", s)
    s = re.sub(r"`[^`\n]{0,200}`", " ", s)
    return s


def _dead_lex_scan(plain):
    """Один проход антисловаря по уже очищенному тексту `plain` - раздельно
    вынесено из `check_dead_language` (Д111, скептик-раунд 38, по решению автора),
    чтобы второй проход (текст без внутрисловных разделителей, см. ниже)
    гонял РОВНО ТУ ЖЕ логику матч + дедуп-по-спанам, что и первый, а не
    копию, которая рассинхронится при следующей правке словаря.

    Возвращает список `(tier, label, live, evid, frag)`, уже дедупнутый по
    перекрытию спанов внутри САМОГО этого прохода (побеждает более ДЛИННОЕ
    совпадение, при равной длине - более сильный тир)."""
    raw = []
    for tier, table in _DEAD_LEX_TIERS:
        for pat, label, live, evid in table:
            for m in re.finditer(_yo_insensitive(pat), plain, re.IGNORECASE):
                raw.append((m.start(), m.end(), tier, label, live, evid))
    raw.sort(key=lambda x: (x[0], -(x[1] - x[0]), _DEAD_LEX_RANK[x[2]]))
    kept, spans = [], []
    for st, en, tier, label, live, evid in raw:
        if any(st < e and en > s for s, e in spans):
            continue
        spans.append((st, en))
        frag = plain[max(0, st - 30):en + 30].replace("\n", " ").strip()
        kept.append((tier, label, live, evid, frag))
    return kept


def check_dead_language(text):
    """Лексический слой живого языка (замер). Возвращает
    {'a': [...], 'b': [...], 'warn': [...], 'chars': N, 'total': N}, где каждый
    хит = (мёртвое слово, живая замена, улика, фрагмент).

    ADMISSION (порог 1): 0 срабатываний TIER-A на 1264 живых документа -
    608 постов доноров, 15 финалов владельца, 7 донор-эталонов green/,
    634 ответа аудитории. Ни одна green-фикстура не падает, значит HARD.

    Дедуп по перекрытию спанов (первый проход, `_dead_lex_scan`). Внутри
    самого антисловаря записи вложены («комплексный подход» матчит и
    `комплексн`, и `комплексн\\w*\\s+подход»), и без дедупа одно нарушение
    считалось бы дважды - плотностный порог 4 срабатывал бы на двух реальных
    словах вместо четырёх.

    🔴 Д111 (скептик-раунд 38, по решению автора, зеркало `check_metaphor_roots` -
    Р4 скептика, С13, «мини-карта»/«д_в_ерь»). У этой функции НЕ БЫЛО
    второго прохода по тексту без внутрисловных разделителей: «мето-
    дология»/«мето_дология» рвали корень TIER-A надвое (регекс `методологи`
    матчит слитное слово, а не половину по разные стороны дефиса), гейт
    живого языка их пропускал. ФИКС - тот же приём, что у метафор: второй
    скан по `_strip_inword_separators(plain)`, находки минус то, что уже
    нашёл первый проход (`_dedup_second_pass`). Дедуп ЗДЕСЬ идёт по КЛЮЧУ
    (tier, label, нормализованный фрагмент), а не по спану позиции - снятие
    разделителей СДВИГАЕТ офсеты всех совпадений правее точки склейки,
    span-дедуп первого прохода тут бесполезен ровно по той же причине, что
    у метафор (см. докстринг `_dedup_second_pass`)."""
    plain = _dead_lex_plain(text)
    kept = _dead_lex_scan(plain)
    glued = _strip_inword_separators(plain)
    if glued != plain:
        kept = kept + _dedup_second_pass(
            kept, _dead_lex_scan(glued),
            lambda h: (h[0], h[1], _INWORD_SEP_RE.sub("", h[4]).lower()))
    out = {"a": [], "b": [], "warn": [],
           "chars": len(plain), "total": len(kept)}
    for tier, label, live, evid, frag in kept:
        out[{"A": "a", "B": "b", "WARN": "warn"}[tier]].append((label, live, evid, frag))
    return out


# --- 4c (канон п.16). Ярлыки-рубрикаторы: смысловые слоты п.15 обязаны быть
# закрыты, но НЕ выведены в текст видимой рубрикой. Разбор эталона 6.08 п.3:
# «Никаких формульных блоков "раньше/теперь", "на вход/на выходе", "что
# забрать сегодня", "честная граница"».
# 🔴 РАУНД 1 (скептик по решению автора, находка 5): класс поднят WARN -> HARD.
# HARD-набор = ровно те рубрикаторы, что автор назвал ПОСТРОЧНО в разборе
# эталона 6.08 п.3 («никаких формульных блоков «раньше/теперь», «на вход/на
# выходе», «что забрать сегодня», «честная граница»») плюс «что делают вместо
# этого» и «было/стало» из того же перечня форм. Снимается --allow-rubricator
# с печатью причины (для архивных постов СТАРШЕ канона 6.08).
RUBRICATOR_OPENERS_HARD = [
    r"на\s+вход\b", r"на\s+выходе\b", r"что\s+забрать\s+сегодня",
    r"честная\s+граница", r"что\s+делают\s+вместо\s+этого",
    r"раньше\s*/\s*теперь", r"было\s*/\s*стало",
]
# Остаются WARN: автор их построчно не называл, детектор эвристический.
RUBRICATOR_OPENERS_SOFT = [
    r"отличаются\s+они\s+не", r"мысль\s+на\s+сегодня",
]
RUBRICATOR_OPENERS = RUBRICATOR_OPENERS_HARD + RUBRICATOR_OPENERS_SOFT


def check_rubricator_openers(paragraphs):
    """4c, канон п.16. Возвращает (idx, метка, зачин, hard: bool).

    🔴 РАУНД 1 (скептик по решению автора, находка 5): было WARN на весь класс, стало
    HARD на набор RUBRICATOR_OPENERS_HARD. Прежнее обоснование WARN -
    «ярлык живёт в 4 из 12 green-ivan (inf17 «На вход», star17 и
    ivan-final-0/2 «Честная граница»), 33% падения зелёного корпуса» -
    снято не отменой замера, а его переоценкой: все 4 поста написаны ДО
    разбора эталона 6.08, где автор построчно запретил формульные блоки.
    Зелёный корпус держится не понижением правила, а явной архивной
    оговоркой --allow-rubricator на этих 4 фикстурах (тот же приём, что
    _ARCH_PSA/_ARCH_META в tests/run-tests.py) - оговорка видна в выводе,
    а не спрятана в пороге."""
    hits = []
    for idx, p in enumerate(paragraphs, 1):
        head = re.sub(r"^[^\wА-Яа-яЁё]+", "", _strip_md_plain(p))[:60]
        for pat in RUBRICATOR_OPENERS:
            m = re.match(pat, head, re.IGNORECASE)
            if m:
                hits.append((idx, m.group(0), head[:50],
                             pat in RUBRICATOR_OPENERS_HARD))
                break
    return hits


# --- 4c/B19 (канон п.19). Плотность идей: «в каждом посте 90% вырезать»
# (владелец 6.08 устно) + эталон 6.08 п.2 «цифры и личные факты в каждом
# третьем предложении». Единица измерения ОДНА с верхним порогом (см.
# IDEA_DENSITY_CEILING рядом) - оба порога стоят здесь, в одном месте.
IDEA_DENSITY_FLOOR_K = 1.0
# 🔴 ВЕРХНЕГО ПОРОГА БОЛЬШЕ НЕТ (было: WARN «чисел > 4.4/1000 = перебор
# конкретики» для нарратива). Улика снятия: эталон владельца 6.08 несёт
# 7.50 чисел/1000, green-ivan/zakr18-den-06в даты запуска/1000, и оба
# считаются образцовыми. Канон п.19 прямо говорит «верхнего потолка нет».
# Правило ловило ровно то, что канон предписывает, поэтому снято, а не
# поднято: любое конечное число здесь снова начало бы врать.
IDEA_DENSITY_CEILING = None


def check_idea_density(text):
    """4c/B19, канон п.19. HARD-пол. Конкретика = цифры + имена собственные +
    латиница-названия + прямые цитаты в «ёлочках», на 1000 знаков чистого
    текста (URL вырезаются - метки utm давали бы фантомную плотность).

    ЗАМЕР ПО КОРПУСУ (12 green-ivan): min 1.15 (ivan-final-1), p25 3.20,
    медиана 6.99, max 19.42 (zakr18-den-0608). Брак B19-nizkaya-plotnost-
    idej.txt даёт РОВНО 0.00 - ни одной цифры, имени или названия на 696
    знаков. Порог взят как min зелёного корпуса, округлённый вниз: 1.0.
    Коридор односторонний, верхней границы нет (см. IDEA_DENSITY_CEILING).

    ЧЕСТНАЯ ГРАНИЦА: донор-эталоны green/ этот пол НЕ держат (donor-492
    даёт 0.00, donor-433 - 0.74). Это чужие тексты, а п.19 - закон автора
    про СВОИ посты, поэтому донорский корпус прогоняется с
    --allow-low-density, а не под порогом."""
    s = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    n = max(len(s), 1)
    nums = len(_NUM_RE.findall(s))
    names = len(_extract_proper_names(s))
    latin = len(re.findall(r"\b[A-Za-z][A-Za-z.\-]{2,}\b", s))
    quotes = len(re.findall(r"«[^»]{2,}»", s))
    total = nums + names + latin + quotes
    return {"k": total / n * 1000, "total": total, "chars": n,
            "nums": nums, "names": names, "latin": latin, "quotes": quotes}


# =============================================================================
# МЁРТВЫЕ КОНСТРУКЦИИ (анти-корпус, по решению автора). Классы К1-К11.
# =============================================================================
# ПОЧЕМУ БЛОК ЕСТЬ. Владелец по решению автора: «Ты полностью неживой, мёртвый язык даёшь,
# наполненный водой и метафорами. Тебе нужно прямо языковую модель создать
# полноценную». Словарь запрещённых СЛОВ к этому моменту уже стоял (owner
# lexicon, метафоры, филлеры, вода) и не помог: дефект живёт не в лексике, а
# в СИНТАКСИСЕ. Ниже - машинная половина закона; живая половина (заготовки,
# из которых конструкции берутся) лежит в слепке
# `.business/voice-corpus/_konstrukcii-zhivogo-yazyka.md` (+ .json).
#
# КАЛИБРОВКА (замер, три корпуса):
#   зелёный корпус автора  - 12 постов  -> 0 HARD (правило, валящее зелёный, сужается)
#   доноры corpus-12m.json - 608 постов -> HARD в 24 (3.9%), почти весь объём в К9
#   боевые посты запуска   - 87 постов  -> HARD в 41 (47%)
# Шесть примеров мёртвого языка, названных владельцем дословно, ловятся все
# (см. tests/run-tests.py, блок DEAD_OWNER_EXAMPLES).
#
# ЧТО НЕ СТАЛО HARD И ПОЧЕМУ. «это нормально» (К3-WARN) - 4 донор-поста;
# «звучит/читается как» (К4-WARN) - 4 донор-поста; «это не X, это Y» (К7) -
# 25 донор-постов и 1 зелёный, поэтому HARD только по плотности >=3 на пост;
# афоризм-каскад из ДВУХ предложений (К6-WARN) - 1 зелёный пост, HARD только
# от трёх. Зачин датой ЦИФРОЙ («11 июня я лёг спать») законен - он есть в
# зелёном корпусе; ловится только словесно-порядковая форма («Шестого августа
# я...»): 30 из 87 боевых, 0 из 12 зелёных, 0 из 608 донорских.

_DC_BULLET = re.compile(r'^\s*(?:[-–—•*>+]|\d+[.)]|[\U0001F300-\U0001FAFF☀-➿])')
_DC_DIGIT = re.compile(r'\d')
_DC_PROPER = re.compile(r'(?<=[а-яё]\s)[А-ЯЁA-Z][а-яёa-z]{2,}')
_DC_STOP = set(
    'и а но что как это то же не ни в на с у к о за по из от до для про я ты он она мы вы они '
    'мне тебе его её их так вот там тут где когда чем чём тот та те этот эта эти был была было '
    'были есть бы ли ещё уже только даже если или сам себя своё свой своя тебя меня нас вас '
    'надо нужно можно очень'.split())

_DC_MONTH = (r'(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)')
_DC_ORD = (r'(?:перв|втор|треть|четв[её]рт|пят|шест|седьм|восьм|девят|десят|одиннадцат|'
           r'двенадцат|тринадцат|четырнадцат|пятнадцат|шестнадцат|семнадцат|восемнадцат|'
           r'девятнадцат|двадцат|тридцат)')

# К8: зачин датой словом-порядковым
DC_DATE_OPENER = re.compile(r'^[^\wА-Яа-яЁё]{0,4}\s*' + _DC_ORD + r'\w*\s+' + _DC_MONTH + r'\w*\b', re.I)

# К1: симметрия «не потому X, а потому Y»
DC_K1 = re.compile(r'\bне\s+потому[,\s][^.!?…]{0,80}?\bа\s+потому\b', re.I)

# К2: обобщённый субъект + презенс всеобщности
DC_K2 = re.compile(
    r'\b(?:'
    r'решают\s+люди|люди\s+(?:редко|обычно|почти\s+всегда|как\s+правило|приходят\s+(?:за|не\s+за))|'
    r'человеку\s+(?:надо|нужно|требуется|свойственно)|'
    r'человек\s+(?:редко|обычно|почти\s+всегда|как\s+правило)|'
    r'(?:никто|все)\s+(?:не\s+)?(?:решает|решают|покупает|покупают)\s+(?:с\s+перв|сразу)'
    r')\b', re.I)

# К3: псевдо-утешение / заискивание
DC_K3_HARD = re.compile(
    r'\b(?:'
    r'никуда\s+(?:он|она|оно|они|это)\s+не\s+(?:денется|денутся)|'
    r'(?:это\s+)?не\s+страшно|ничего\s+страшного|не\s+переживай|не\s+волнуйся|'
    r'это\s+не\s+приговор|бывает\s+у\s+всех|с\s+кем\s+не\s+бывает'
    r')\b', re.I)
DC_K3_WARN = re.compile(r'\b(?:это\s+нормально|и\s+это\s+нормально|всё\s+в\s+порядке)\b', re.I)

# К4: сравнение состояний вместо факта
DC_K4_HARD = re.compile(
    r'\b(?:выглядит|звучит|ощущается|смотрится|читается|воспринимается)\s+'
    r'(?:одинаково|похоже|так\s+же|примерно\s+так\s+же)\b', re.I)
DC_K4_WARN = re.compile(
    r'\b(?:выглядит|звучит|ощущается|смотрится|читается|воспринимается)\s+'
    r'(?:как|словно|будто|так,?\s+будто)\b', re.I)

# К5: симметричный повтор головы «Дело не в A. Дело в B»
_DC_K5_HEADS = (r'дел[оа]|разниц\w+|вопрос|проблем\w+|секрет|суть|смысл|причин\w+|'
                r'сложност\w+|беда|фокус|ключ')
DC_K5_ONE = re.compile(
    r'\b(' + _DC_K5_HEADS + r')\s+не\s+в\s+[^.!?…]{1,70}?[.!?…,\-]\s*(?:а\s+)?(?:\1\w*\s+)?в\s+\w+', re.I)
_DC_K5_HEAD_ANY = re.compile(r'\b(' + _DC_K5_HEADS + r')\b', re.I)
_DC_K5_NEG = re.compile(r'\b(' + _DC_K5_HEADS + r')\s+не\s+в\b', re.I)

# К7: «это не X, это/а Y»
DC_K7 = re.compile(r'\bэто\s+не\s+[^.!?…]{1,45}?,\s*(?:это|а)\s+\w+', re.I)

# К10: абстрактное подлежащее-состояние
_DC_K10_SUBJ = (r'тишин\w+|молчани\w+|пустот\w+|ожидани\w+|неопредел[её]нност\w+|'
                r'усталост\w+|страх|сомнени\w+|отказ|согласи\w+')
DC_K10 = re.compile(
    r'\b(?:' + _DC_K10_SUBJ + r')\b[^.!?…]{0,60}?\b'
    r'(?:выглядит|звучит|читается|ощущается|означает|бывает|устроена?|устроено)\b', re.I)

# К11: псевдоточность «ровно»
DC_K11 = re.compile(r'\bровно\b', re.I)

# К9: заголовок
DC_H_DEIXIS = re.compile(
    r'\b(?:вчера|позавчера|сегодня|завтра|послезавтра|давеча|намедни|'
    r'вчерашн\w+|сегодняшн\w+|завтрашн\w+|в\s+полдень|в\s+полночь|под\s+вечер)\b', re.I)
DC_H_COUNT_ABSTRACT = re.compile(
    r'\b(?:один|одна|одно|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|\d+)\s+'
    r'(?:блок\w*|вещ\w+|штук\w*|момент\w*|участк\w*|участок|слой|слоя|слоёв|шаг\w*|пункт\w*|'
    r'кусок|куск\w+|порядк\w*|порядок|сло[тв]\w*|клетк\w*)\b', re.I)

DEAD_CLASS_LABEL = {
    "К1": "симметрия «не потому X, а потому Y»",
    "К2": "обобщённый субъект вместо конкретного человека",
    "К3": "псевдо-утешение",
    "К4": "сравнение состояний вместо факта",
    "К5": "симметричный повтор головы «X не в A. X в B»",
    "К6": "афоризм-пуант: каскад коротких предложений с лексическим повтором",
    "К7": "«это не X, это Y»",
    "К8": "серийный зачин датой словом-порядковым",
    "К9": "заголовок непонятен человеку с улицы",
    "К10": "абстрактное подлежащее-состояние",
    "К11": "псевдоточность «ровно»",
}


def _dc_words(s):
    return re.findall(r"[А-Яа-яЁёA-Za-z0-9$%]+(?:-[А-Яа-яЁёA-Za-z0-9]+)*", s)


def _dc_stems(s):
    return [w.lower().replace('ё', 'е')[:5] for w in _dc_words(s)
            if len(w) > 3 and w.lower() not in _DC_STOP]


def _dc_line_runs(text):
    """Предложения, сгруппированные по строкам. Последний фрагмент без
    терминатора - тоже предложение: у автора закон «без точки в конце абзаца»,
    и именно там сидит пуант («...Назвал я не то»)."""
    runs = []
    for p in split_paragraphs(text):
        for line in p.split('\n'):
            line = line.strip()
            if not line or _DC_BULLET.match(line):
                continue
            parts = [x.strip() for x in re.findall(r'[^.!?…]+(?:[.!?…]+|$)', line) if x.strip()]
            if len(parts) >= 2:
                runs.append(parts)
    return runs


def _dc_sentences(text):
    out = []
    for p in split_paragraphs(text):
        for line in p.split('\n'):
            line = line.strip()
            if not line:
                continue
            for s in re.findall(r'[^.!?…]+(?:[.!?…]+|$)', line):
                s = s.strip()
                if s:
                    out.append(s)
    return out


def dead_aphorism_cascades(text, maxw=8):
    """К6. Каскад коротких предложений, где каждое следующее ОТКРЫВАЕТСЯ словом,
    уже стоявшим в предыдущем (анафора или хиазм-инверсия), и во всём каскаде нет
    ни цифры, ни имени собственного. Цифра/имя = каскад несёт факт, это не пуант."""
    res = []
    for run in _dc_line_runs(text):
        i = 0
        while i < len(run) - 1:
            chain = [run[i]]
            j = i + 1
            while j < len(run):
                a, b = chain[-1], run[j]
                if not (2 <= len(_dc_words(b)) <= maxw and 2 <= len(_dc_words(a)) <= maxw):
                    break
                sa, sb = _dc_stems(a), _dc_stems(b)
                if not sa or not sb or sb[0] not in set(sa):
                    break
                chain.append(b)
                j += 1
            if len(chain) >= 2:
                frag = ' '.join(chain)
                if not _DC_DIGIT.search(frag) and not _DC_PROPER.search(frag):
                    res.append((len(chain), frag))
                i = j
            else:
                i += 1
    return res


def dead_symmetric_head(text):
    """К5. Пара «<голова> не в A» + та же голова «... в B» в этом же или следующем
    предложении. Одиночное «Дело не в тебе» (зелёный корпус, inf17) не ловится -
    ловится только СИММЕТРИЯ, то есть повтор головы во второй половине."""
    out = []
    runs = _dc_line_runs(text) + [[s] for s in _dc_sentences(text)]
    for run in runs:
        for i, s in enumerate(run):
            m = _DC_K5_NEG.search(s)
            if not m:
                continue
            head = m.group(1).lower()[:4]
            tail = s[m.end():]
            nxt = run[i + 1] if i + 1 < len(run) else ''
            for zone, is_next in ((tail, False), (nxt, True)):
                hit = False
                for hm in _DC_K5_HEAD_ANY.finditer(zone):
                    if hm.group(1).lower()[:4] != head:
                        continue
                    if re.match(r'\s*(?:в|во)\s+\w', zone[hm.end():hm.end() + 25], re.I):
                        out.append((s + (' ' + nxt if is_next else '')).strip())
                        hit = True
                        break
                if hit:
                    break
    for s in _dc_sentences(text):
        if DC_K5_ONE.search(s):
            out.append(s.strip())
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def dead_generalized_subject(text):
    """К2. Утверждение о людях вообще, в котором нет ни одного якоря -
    ни цифры, ни имени собственного. «Я/мне» якорем НЕ считается: первое лицо
    рядом не делает утверждение о людях конкретным."""
    out = []
    for s in _dc_sentences(text):
        m = DC_K2.search(s)
        if not m:
            continue
        if _DC_DIGIT.search(s) or _DC_PROPER.search(s):
            continue
        out.append(s.strip())
    return out


def dead_headline(text):
    """К9. Заголовок = первая содержательная строка (для писем - мимо
    служебных SUBJECT/PREHEADER/BODY)."""
    ps = split_paragraphs(text)
    if not ps:
        return None, []
    h = ps[0].split('\n')[0].strip()
    if h.upper() in ('SUBJECT', 'PREHEADER', 'BODY'):
        for p in ps:
            cand = p.split('\n')[0].strip()
            if cand.upper() not in ('SUBJECT', 'PREHEADER', 'BODY'):
                h = cand
                break
    defects = []
    if DC_H_DEIXIS.search(h) and not _DC_DIGIT.search(h) and not _DC_PROPER.search(h):
        defects.append(('HARD', 'дейктик времени («вчера/сегодня/в полдень») без единого якоря - '
                                'ни цифры, ни имени. Человек с улицы не поймёт, о чём это'))
    if DC_H_COUNT_ABSTRACT.search(h):
        defects.append(('WARN', 'счётный абстракт («три блока», «две вещи», «пять шагов») '
                                'вместо названного предмета'))
    return h, defects


def scan_dead_constructions(text):
    """Единый прогон анти-корпуса. -> список (класс, уровень, пояснение, фрагмент)."""
    res = []
    flat = _dc_sentences(text)

    for s in flat:
        m = DC_K1.search(s)
        if m:
            res.append(("К1", "HARD", DEAD_CLASS_LABEL["К1"], m.group(0)))

    for s in dead_generalized_subject(text):
        res.append(("К2", "HARD", DEAD_CLASS_LABEL["К2"], s))

    for s in flat:
        m = DC_K3_HARD.search(s)
        if m:
            res.append(("К3", "HARD", DEAD_CLASS_LABEL["К3"], m.group(0)))
        m = DC_K3_WARN.search(s)
        if m:
            res.append(("К3", "WARN", DEAD_CLASS_LABEL["К3"] + " (мягкая форма)", m.group(0)))

    for s in flat:
        if DC_K4_HARD.search(s):
            res.append(("К4", "HARD", DEAD_CLASS_LABEL["К4"], s))
        m = DC_K4_WARN.search(s)
        if m:
            res.append(("К4", "WARN", DEAD_CLASS_LABEL["К4"] + " («как/словно»)", m.group(0)))

    for s in dead_symmetric_head(text):
        res.append(("К5", "HARD", DEAD_CLASS_LABEL["К5"], s))

    for n, frag in dead_aphorism_cascades(text):
        lvl = "HARD" if n >= 3 else "WARN"
        res.append(("К6", lvl, DEAD_CLASS_LABEL["К6"] + f" ({n} подряд)", frag))

    k7 = [DC_K7.search(s).group(0) for s in flat if DC_K7.search(s)]
    if len(k7) >= 3:
        res.append(("К7", "HARD", DEAD_CLASS_LABEL["К7"] + f": {len(k7)} на пост (норма <=2)",
                    " | ".join(k7[:3])))
    elif k7:
        res.append(("К7", "WARN", DEAD_CLASS_LABEL["К7"] + f": {len(k7)}", k7[0]))

    for p in split_paragraphs(text)[:2]:
        first = re.match(r'[^.!?…]+', p.split('\n')[0].strip())
        cand = (first.group(0) if first else '').strip()
        if DC_DATE_OPENER.match(cand):
            res.append(("К8", "HARD", DEAD_CLASS_LABEL["К8"], cand))
            break

    h, hdefects = dead_headline(text)
    for lvl, why in hdefects:
        res.append(("К9", lvl, "заголовок: " + why, h))

    for s in flat:
        if DC_K10.search(s):
            res.append(("К10", "HARD", DEAD_CLASS_LABEL["К10"], s))

    n11 = len(DC_K11.findall(text))
    if n11 >= 2:
        res.append(("К11", "HARD", DEAD_CLASS_LABEL["К11"] + f": {n11} на пост (норма <=1)", "ровно"))
    elif n11 == 1:
        res.append(("К11", "WARN", DEAD_CLASS_LABEL["К11"] + ": 1", "ровно"))

    return res


def dead_date_opener_share(package_dir, this_text=None):
    """К8 на уровне ПАКЕТА. Владелец по решению автора: «в каждом посте говоришь, какого
    августа что-то случилось - в референсах у конкурентов такого почти нет».
    Замер: доноры 0.5% (2 из 608, оба ЦИФРОЙ), зелёный корпус автора 8.3%
    (1 из 12, тоже цифрой), боевой пакет 34.5% (30 из 87, все словом).
    Порог 15% = вдвое выше зелёного корпуса и в 30 раз выше доноров."""
    files = []
    for ext in ("*.md", "*.txt"):
        files += sorted(glob.glob(os.path.join(package_dir, ext)))
    files = [f for f in files if not os.path.basename(f).startswith("_")]
    total, hits = 0, []
    for f in files:
        try:
            raw = open(f, encoding="utf-8").read()
        except OSError:
            continue
        body = _package_post_body(raw)
        if not body or len(body) < 200:
            continue
        total += 1
        for p in split_paragraphs(body)[:2]:
            first = re.match(r'[^.!?…]+', p.split('\n')[0].strip())
            cand = (first.group(0) if first else '').strip()
            if DC_DATE_OPENER.match(cand):
                hits.append((os.path.basename(f), cand[:70]))
                break
    return total, hits


DEAD_DATE_OPENER_PACKAGE_MAX = 0.15


# =============================================================================
# Д8 (по решению автора): КЛАСС `event` В ИСПОЛНЯЕМОМ СЛОЕ.
# =============================================================================
# Дефект, который это закрывает (скептик-раунд 3, находка 8): класс `event`
# объявлен в workflow с закрытым набором из 12 гейтов фазы E3 (01-router.md
# 0.49-К), а слова `event` в коде было 0 вхождений - `--form-class event`
# отбивался argparse, post-phase-gate.sh молча ронял флаг. Ровно суть класса
# (плотность и конкретика события) оставалась декларацией.
#
# КАРТА 12 ГЕЙТОВ E3 -> ЧТО ДЕРЖИТ МАШИНА, ЧТО ОСТАЁТСЯ ТЕКСТОМ 04-review.md:
#   1  4.0.1  прогон линтера ................. МАШИНА (этот файл целиком)
#   2  4.0.2  Gate Evidence Report ........... текст 04-review (покрытие пунктов)
#   3  4.0.2b режим формы + rationale ........ хук post-phase-gate.sh (state)
#   4  4.DENS плотность идей, порог 3.0 ...... МАШИНА, ниже (check_dens_ratio)
#   5  4.ET   сравнение с эталоном автора .... текст 04-review (внешний файл + суждение)
#   6  4.SUB  метафора-подмена ............... МАШИНА частично (check_metaphors) + верификатор
#   7  W15-цепь, порог 3 звена ............... текст 04-review (звенья ЦИТАТАМИ, причинность)
#   8  4.R    референты ...................... текст 04-review
#   9  4.S    Sales Gate (при launch_window) . МАШИНА частично (UTM/дверь/закон 32) + текст
#  10  Checklist владельца A-F ................... текст 04-review (внешний файл)
#  11  4.M.2  независимый верификатор ........ субагент, проверяет хук
#  12  Humaniser + формат-тройка ............. МАШИНА частично (тире/точка/клише) + скилл
# Плюс машинный признак класса, которого в списке E3 нет, но без него класс
# не отличим от продажи: дата или время события в теле (0.49-E «признаки класса»,
# 02d «время в первой строке») - check_event_datetime ниже.
#
# «Запрещённые классу launch-элементы» держат гейты, которые в этом файле уже
# стоят БЕЗУСЛОВНО (для всех классов, event в том числе), их сюда не дублируем:
# цена цифрой (check_price_digit) · домашка и второе действие читателю
# (check_homework_action + check_second_action, закон-якорь №11) · отложенное
# обещание «расскажу на эфире» (check_deferred_promise) · перечисление
# программы события (check_program_enum, B12 «программу события не перечислять»).
# Единственное, что классу нужно отдельно: служебная launch-строка (счётчик мест,
# дедлайн, 👉-CTA, адрес двери) НЕ засчитывается носителем плотности - канон
# 4.DENS п.3 и канон правок п.18. Это и делает EVENT_SERVICE_LINE ниже.

EVENT_DENS_MAX = 3.0          # 04-review.md 4.DENS: `event` -> density <= 3.0, HARD

# Служебная launch-строка: 👉-CTA, адрес двери, счётчик мест, дедлайн заявок.
# Числа внутри неё идею не несут (канон п.18), поэтому строка целиком выносится
# из знаменателя D. Из S она НЕ выносится - предложением она быть не перестала.
EVENT_SERVICE_LINE = re.compile(
    r"(?:^\s*👉)|https?://|t\.me/|мест\w*\s+оста|остал\w+\s+\d+\s+мест|"
    r"заявк\w+\s+закрыва|дедлайн", re.IGNORECASE)

# Носители плотности сверх тех, что уже считает check_idea_density (цифры, имена
# собственные, латиница-названия, цитаты в «ёлочках»). Канон 4.DENS п.2 называет
# ещё два вида, и без них счёт врёт вниз на событийном посте:
#   - срок словами («сегодня», «завтра», месяц, день недели) - у события это
#     ровно та конкретика, ради которой пост написан;
#   - физический артефакт (скрин, файл, страница, письмо, кружок).
EVENT_DATEWORD = re.compile(
    r"\b(?:сегодня|завтра|послезавтра|вчера|понедельник\w*|вторник\w*|сред[ыуа]|"
    r"четверг\w*|пятниц\w*|суббот\w*|воскресень\w*|январ\w+|феврал\w+|март\w*|"
    r"апрел\w+|ма[йя]\b|июн\w+|июл\w+|август\w*|сентябр\w+|октябр\w+|ноябр\w+|"
    r"декабр\w+)\b", re.IGNORECASE)
EVENT_ARTIFACT = re.compile(
    r"\b(?:скрин\w*|файл\w*|страниц\w*|ссылк\w*|картинк\w*|кружок|кружк\w+|"
    r"письм\w+|папк\w+|экран\w*|таблиц\w+|шаблон\w+|документ\w*)\b", re.IGNORECASE)

# Дата или время события. Время HH:MM / HH.MM, дата цифрой с месяцем,
# «сегодня/завтра/послезавтра», день недели, месяц с числом.
EVENT_TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
EVENT_DATE_RE = re.compile(
    r"\b\d{1,2}\s*(?:январ\w+|феврал\w+|март\w*|апрел\w+|ма[йя]\b|июн\w+|июл\w+|"
    r"август\w*|сентябр\w+|октябр\w+|ноябр\w+|декабр\w+)|"
    r"\b(?:сегодня|завтра|послезавтра)\b|"
    r"\b(?:в\s+)?(?:понедельник|вторник|сред[уы]|четверг|пятниц[ыу]|суббот[ыу]|"
    r"воскресенье)\b", re.IGNORECASE)


def check_dens_ratio(text):
    """4.DENS в машинном виде (04-review.md sub-stage 4.DENS). Возвращает
    S (предложений), D (носителей конкретики) и density = S/D - сколько
    предложений приходится на один носитель. Порог класса `event` - 3.0, HARD.

    ГРАНИЦА ЧЕСТНАЯ. Канон перечисляет пять видов носителя, два из них машине
    недоступны точно: «имя человека С ПРЕДСТАВЛЕНИЕМ» (нужен NER) и «личный
    факт автора от первого лица» (нужно понимание). Здесь считается прокси:
    цифры + имена собственные + латиница-названия + цитаты в «ёлочках» + срок
    словами + физический артефакт. Прокси СКЛОНЕН СЧИТАТЬ ЩЕДРО (19:00 даёт две
    цифры вместо одного носителя), то есть ошибается в сторону PASS - для HARD-
    гейта это правильный знак ошибки: он не валит здоровый пост, а ловит пост,
    у которого конкретики нет вовсе. Точную оценку по всем пяти видам держит
    верификатор 4.M.2 строкой `4.DENS: S=.. D=.. density=..`.

    ADMISSION (событийные посты автора, green-ivan, порог 3.0):
      b17-3-0508  S=24 D=17 density=1.41
      inf18-0608  S=27 D=13 density=2.08
      etalon-0608 S=13 D=15 density=0.87
    Запас до порога у худшего из троих - 31%. Брак B19-nizkaya-plotnost-idej
    даёт D=0 -> density=inf -> FAIL."""
    sents = split_sentences_w15(text)
    S = len(sents)
    body_lines = [l for l in text.splitlines()
                  if l.strip() and not EVENT_SERVICE_LINE.search(l)]
    body = "\n".join(body_lines)
    plain = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", body))
    nums = len(_NUM_RE.findall(plain))
    names = len(_extract_proper_names(plain))
    latin = len(re.findall(r"\b[A-Za-z][A-Za-z.\-]{2,}\b", plain))
    quotes = len(re.findall(r"«[^»]{2,}»", plain))
    datewords = len(EVENT_DATEWORD.findall(plain))
    artifacts = len(EVENT_ARTIFACT.findall(plain))
    D = nums + names + latin + quotes + datewords + artifacts
    density = (S / D) if D else float("inf")
    return {"S": S, "D": D, "density": density, "nums": nums, "names": names,
            "latin": latin, "quotes": quotes, "datewords": datewords,
            "artifacts": artifacts}


def check_event_datetime(text):
    """Признак класса `event` (01-router.md 0.49-E): «в посте названы дата или
    время события». Событийный пост без даты и без времени - это не событийный
    пост, а продающий, объявленный событийным, чтобы уйти от порога доли скилла.
    Возвращает список найденных маркеров (пусто = FAIL для класса event).

    ADMISSION: все три событийных green-ivan несут «19:00» (b17-3-0508 плюс
    «Завтра», inf18-0608 и etalon-0608 плюс «Сегодня»)."""
    plain = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    return sorted(set(m.group(0).strip()
                      for m in list(EVENT_TIME_RE.finditer(plain))
                      + list(EVENT_DATE_RE.finditer(plain))))


# --- 4c (канон п.42 «связный рассказ, не набор лозунгов» + B10 «механика
# общими словами»). Причинные связки: если пост заявляет разбор инструмента,
# в нём обязана быть хотя бы одна причинная сцепка, иначе абзацы стоят
# рядом, но не вытекают друг из друга.
#
# 🔴 РАЗВЕДЕНИЕ п.42 / п.56 (Д10, по решению автора). БЫЛО: один список CAUSAL_LINKS
# нёс И содержательные связки («потому что», «из-за», «за счёт»), И ВЫВОДНЫЕ
# маркеры («поэтому», «значит», «так что», «получается», «выходит»). Пол п.42
# закрывался любым из них - в том числе выводным, который канон п.56
# («псевдо-причинная связка») запрещает ставить там, где реальной причины нет.
# Машина требовала ровно то, что другой пункт канона запрещает.
# СТАЛО: два списка. Пол п.42 закрывают ТОЛЬКО содержательные связки;
# выводные считаются отдельно и печатаются как объект ручной проверки п.56
# (улика на СВЯЗЬ, а не на факты - память no-pseudo-causal-glue-between-canon-facts).
# ADMISSION к разведению: 22/22 одобренных текста (7 донор-эталонов + 12
# green-ivan + 3 финала автора) несут минимум 1 СОДЕРЖАТЕЛЬНУЮ связку, ни один
# не держится на выводных (минимум donor-440 = 1, максимум e17-0508 = 13).
# (цифра «7 донор-эталонов» - замер admission от этой редакции; набор эталонов bench
# с этой редакции расширен до 10 (+3 Донор-В), затем до 12 (+Донор-Б:2034/2014
# razbor, дефект Д19) и в тот же день сведён к 11 (дефект Д23 раунда 4: пара
# 2034/2014 снята за реакция-механику и коридор, на замену Донор-Б:1833),
# admission-числа не пересчитывались)
SUBSTANTIVE_CAUSAL = re.compile(
    r"\bпотому\s+что\b|\bиз-за\b|\bв\s+результате\b|"
    r"\bпоскольку\b|\bблагодаря\b|\bраз\s+уж\b|\bчтобы\b|"
    r"\bиначе\b|\bза\s+счёт\b|\bтогда\b|"
    r"\bпричина\b|\bтак\s+как\b|\bдело\s+в\b|(?<!вот )\bпочему\b|\bесли\b|\bкогда\b|"
    r"\bдальше\b|\bпотом\b|\bсначала\b|\bа\s+следом\b", re.IGNORECASE)
# Выводные маркеры: заявляют вывод из предыдущего утверждения. Канон п.56 -
# каждый требует улику на связь в факт-базе/каноне, иначе снимается.
INFERENTIAL_LINKS = re.compile(
    r"\bпоэтому\b|\bа\s+значит\b|\bзначит\b|\bвот\s+почему\b|"
    r"\bтак\s+что\b|\bполучается\b|\bвыходит\b", re.IGNORECASE)
# Обратная совместимость: полный список (пол + выводные) под прежним именем.
CAUSAL_LINKS = re.compile(SUBSTANTIVE_CAUSAL.pattern + "|" + INFERENTIAL_LINKS.pattern,
                          re.IGNORECASE)


def check_causal_links(text):
    """4c, канон п.42. HARD при нуле. Считает ТОЛЬКО содержательные связки -
    выводные маркеры («поэтому», «значит», «так что») пол не закрывают, это
    предмет п.56 (см. check_inferential_links и комментарий выше).

    ЗАМЕР: 12 green-ivan дают минимум 2 связки (etalon-0608 - 2, ivan-final-2 -
    3, максимум 14 у e17), 10 донор-эталонов - минимум 1 (donor-440). Ноль
    связок не встречается ни в одном одобренном тексте. В красном корпусе ноль
    дают ровно C8-nabor-lozungov (тот самый «несвязный набор лозунгов», прямая
    цитата владельца ), C9-ogryzok, D5-ritm-generatora и
    F7-starye-kanaly-ogryzkom."""
    plain = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    return len(SUBSTANTIVE_CAUSAL.findall(plain))


def check_inferential_links(text):
    """Канон п.56 «псевдо-причинная связка». Возвращает список найденных
    выводных маркеров. Машина считает их и показывает списком; сама связь
    (есть ли причина в факт-базе) проверяется на ревью - это судейская ось,
    в коде её нет и заявлять обратное нельзя."""
    plain = _strip_md_plain(re.sub(r"(?:https?://|t\.me/)\S+", " ", text))
    return [m.group(0) for m in INFERENTIAL_LINKS.finditer(plain)]


# --- 4c/E6 (закон-якорь №11). Второе действие читателю. Единственное
# действие читателя в контенте запуска = РЕГИСТРАЦИЯ; реакция, репост,
# сохранение и «напиши слово в комментарии» - вторые действия, они уводят
# от двери и делят внимание.
SECOND_ACTION_PATTERNS = [
    (r"поставь?\s+реакци\w*", "поставить реакцию"),
    (r"перешл[иё]\w*\s+(?:этот\s+)?пост", "переслать пост"),
    (r"\bподелись\b", "поделиться"),
    (r"сохрани\s+(?:себе|пост|этот)", "сохранить пост"),
    (r"\bподпишись\b", "подписаться"),
    (r"напиши\s+в\s+комментар\w*", "написать в комментарии"),
    (r"ставь\s+плюс", "поставить плюс"),
    (r"отметь\s+в\s+комментар\w*", "отметить в комментариях"),
]


def check_second_action(text):
    """4c/E6, закон-якорь №11. HARD (общая строка с домашкой - это один и
    тот же закон «единственное действие читателя = регистрация»).
    BASELINE по решению автора фиксировал класс E6 как «М (есть)» в классификаторе,
    а функции в коде НЕ БЫЛО вовсе - здесь она появляется.
    ADMISSION: 0/12 green-ivan, 0/10 донор-эталонов."""
    plain = _strip_md_plain(text)
    hits = []
    for pat, label in SECOND_ACTION_PATTERNS:
        for m in re.finditer(pat, plain, re.IGNORECASE):
            s = max(0, m.start() - 20)
            hits.append((label, plain[s:m.end() + 30].replace("\n", " ").strip()))
    return hits


# --- 4c/C4 (канон п.39). Шаблон заголовка «НАЗВАНИЕ КАПСОМ - расшифровка».
CAPS_HEADLINE_TEMPLATE = re.compile(
    r"^\s*(?:\S+\s+)?\*{0,2}([А-ЯЁ][А-ЯЁ\s]{4,40}?)\s+-\s+\S")


def check_email_subjects(text):
    """4c/F8, канон п.77. HARD. У письма ровно ОДИН Subject - варианты на
    выбор автору не выдаются (правка владельца , п.16: «выбирай сам» = не
    доделанная работа). Считаем служебные блоки шапки письма: `**SUBJECT**`,
    `SUBJECT (вариант 2)`, `Subject:`.
    ADMISSION: green-ivan/e17-0508.txt (одобренное письмо) несёт ровно один,
    F8-фикстура - два. На постах молчит: блока SUBJECT там нет вовсе."""
    return [m.group(0).strip() for m in re.finditer(
        r"(?mi)^\s*\*{0,2}\s*subject\b[^\n]{0,40}", text)]


def caps_headline_template(headline):
    """4c/C4, канон п.39. Возвращает КАПС-часть шаблона или None.
    Правило серийное: «Регекс-шаблон в >=2 постах серии = FAIL», поэтому
    считается внутри --package (см. check_package_duplicates), а не на
    одиночном посте - один КАПС-заголовок в дне канон разрешает (п.38)."""
    m = CAPS_HEADLINE_TEMPLATE.match(headline or "")
    return m.group(1).strip() if m else None


# --- концретика/плотность (R3 §B). Регексы близки к scratchpad/bench.py,
# переиспользованы для единства измерения между lint и bench-post.py.
_MONEY_RE = re.compile(
    r"(\d[\d\s.,]*\s*(₽|руб|рубл|\$|долл|бакс|тыс|млн|k\b|К\b))|((\$|₽)\s*\d)", re.IGNORECASE)
_NUM_RE = re.compile(r"(?<![\w.,])\d+([.,]\d+)?(?![\w])")
TOOLS_PATTERNS = [
    r'chatgpt', r'\bgpt', r'claude', r'клод', r'midjourney', r'миджорни', r'sora', r'runway', r'\bveo\b', r'kling',
    r'heygen', r'elevenlabs', r'\bn8n\b', r'make\.com', r'zapier', r'notion', r'figma', r'canva', r'telegram', r'телеграм',
    r'youtube', r'ютуб', r'instagram', r'инстаграм', r'нельзяграм', r'tiktok', r'тикток', r'reels', r'рилс', r'threads',
    r'salebot', r'getcourse', r'геткурс', r'\bcursor\b', r'\bcodex\b', r'\bapi\b', r'\bcrm\b', r'\bstripe\b', r'\bpaypal\b',
    r'\bwordpress\b', r'\btilda\b', r'тильда', r'\bapify\b', r'\bperplexity\b', r'\bgemini\b', r'\bdeepseek\b', r'\bllama\b',
    r'\bwhisper\b', r'\bобсидиан\b', r'\bobsidian\b', r'\bskool\b', r'\bpatreon\b', r'\bkit\b', r'\bbeehiiv\b']


def check_concreteness(text):
    """R3 §B - сырые числа для профильной интерпретации в main() (ЗНАК
    меняется от form_goal, R3 предупреждение 3, читать goal ДО порога)."""
    s = _strip_md_plain(text)
    n = max(len(s), 1)
    k = n / 1000.0
    num_k = len(_NUM_RE.findall(s)) / k
    money_k = len(_MONEY_RE.findall(s)) / k
    tools_k = sum(len(re.findall(p, s, re.IGNORECASE)) for p in TOOLS_PATTERNS) / k
    return {"num_k": num_k, "money_k": money_k, "tools_k": tools_k}


# --- AC2 доп. / класс R2-1-b (вода-АБСТРАКЦИЯ без словарных маркеров). ДЕФЕКТ 2,
# раунд 9, по решению автора. Живой брак владельца: «Показываю, что у меня стоит, потому что
# дыра эта общая и все в неё проваливаются» - НОЛЬ совпадений с WATER_EVAL/INTENS/
# KANC/AI_CLICHE (словарь чист), вердикт владельца «в чем ценность этого абзаца? 0
# ценности просто вода». Вода тут - абзац БЕЗ конкретики (ни одного факта/детали/
# механики), а не абзац с плохими словами. check_water ловит ВТОРОЕ, не ПЕРВОЕ -
# два разных детектора закрывают два разных класса, один не заменяет другой.
SUBSTANCE_LONG_PARA_LEN = 120
SUBSTANCE_SHARE_WARN = 0.8  # доля абзацев >120 знаков без конкретика-токенов (см. admission ниже)
SUBSTANCE_CLASSES = ("razbor", "sales")  # применяется ТОЛЬКО к прикладным классам, см. admission


def _para_has_mid_sentence_capital(paragraph):
    """Заглавная буква НЕ первым словом предложения = имя собственное/название
    (заглавная ПЕРВЫМ словом - обычная грамматика, ничего не показывает)."""
    sentences = re.split(r"(?<=[.!?…])\s+", paragraph)
    for sent in sentences:
        words = sent.split()
        for idx, w in enumerate(words):
            if idx == 0:
                continue
            core = w.strip("«»\"'.,!?:;()-*_")
            if core and core[0].isupper() and any(c.isalpha() for c in core):
                return True
    return False


def _para_has_concreteness_token(p):
    """Конкретика-токен по докстрингу check_paragraph_substance: цифра, денежная
    сумма, ссылка, кавычки-цитата «», латиница-название, имя собственное
    (заглавная не первым словом предложения)."""
    if re.search(r"\d", p):
        return True
    if _MONEY_RE.search(p):
        return True
    if re.search(r"https?://|www\.\w", p, re.IGNORECASE):
        return True
    if "«" in p or "»" in p:
        return True
    if re.search(r"[A-Za-z]{2,}", p):
        return True
    if _para_has_mid_sentence_capital(p):
        return True
    return False


def check_paragraph_substance(paragraphs, form_class):
    """Абзац длиннее SUBSTANCE_LONG_PARA_LEN знаков БЕЗ единого конкретика-токена
    (цифра/деньги/ссылка/кавычки-цитата/латиница-название/имя собственное) считается
    АБСТРАКТНЫМ. Возвращает None, если проверка к этому form_class не применяется
    (см. ADMISSION ниже - narrative исключён осознанно).

    ADMISSION-ТЕСТ (раунд 9, по решению автора, ОБЯЗАТЕЛЕН ДО выбора статуса, прогнан на
    7 донор-эталонах scripts/etalons.json id 504/492/1372/433/1455/440/1579 + 3
    финалах владельца ivan-final-0/1/2.txt, детектор ровно этот,
    порог доли ровно SUBSTANCE_SHARE_WARN=0.8).

    🔴 ГДЕ ЛЕЖАТ ЭТИ ФИКСТУРЫ СЕЙЧАС (уточнено, дефект Д20 скептик-
    раунда 3). Путь `tests/fixtures/green/ivan-final-*.txt`, названный выше, на
    диске больше не существует: три финала автора вынесены в ПРИВАТНЫЙ корпус,
    из раздачи ученикам они исключены. Резолв - `run-tests.py`, функция
    `owner_fixture()` по цепочке `OWNER_FIXTURES_CANDIDATES`: env
    `POST_OWNER_FIXTURES` → `.business/processes/post-fixtures-ivan/green/`
    → `~/.business/processes/post-fixtures-ivan/green/`. Каталога нет (машина
    ученика) → группы с этими фикстурами уходят в [SKIP] с причиной, остальные
    тесты зелёные. Донор-эталоны (`scripts/etalons.json`) раздаются как были.
    ЧИСЛА ADMISSION НИЖЕ ПЕРЕСЧЁТУ НЕ ПОДЛЕЖАТ: это исторический замер раунда 9
    (по решению автора) на наборе эталонов ТОЙ даты. Сам набор с тех пор менялся -
    7 доноров на момент этой редакции → 10 (+3 Донор-В) → 12 (+Донор-Б:2034/2014 razbor,
    дефект Д19) → 11 в тот же день (2034/2014 сняты дефектом Д23 раунда 4 за
    реакция-механику и коридор, на замену Донор-Б:1833) - но замер ниже НЕ
    пересчитан ни на одном из промежуточных наборов (уточнено,
    дефект Д64 раунда 18: прежняя формулировка «менялось только их
    местоположение на диске» была ложной - менялся состав, не только путь):

      narrative (504/492/1372, "B-нарратив"): доля абстрактных абзацев 1.0/1.0/0.33
        - 0/3 постов БЕЗ абстрактных абзацев (0% admission «чисто»). У B-TOP-доноров
        нарратива абстрактный абзац - НОРМА ЖАНРА (лирика/сцена без цифр и имён по
        дизайну), проверка на него ложно сработала бы на лучших текстах корпуса ->
        КЛАСС NARRATIVE ИЗ-ПОД ПРОВЕРКИ ИСКЛЮЧЁН (SUBSTANCE_CLASSES).

      razbor (на момент замера раунда 9 - донор id 433, единственный экземпляр
        в тогдашнем etalons.json; с этой редакции в наборе два экземпляра -
        Донор-А:433 + Донор-Б:1833, уточнено дефектом Д64 раунда 18): доля
        1.0 (3/3 абзаца абстрактны) - даже эталонный разбор верхнего квартиля у
        этого узкого списка токенов даёт 100%: аргументация есть, но цифр/имён/
        ссылок/латиницы в абзацах нет. n=1 от раунда 9, статистически
        недостаточно для HARD; admission на Донор-Б:1833 не пересчитывался -
        статус WARN держится по историческому замеру n=1, при следующем
        пересеве набора пересчитать на актуальных двух экземплярах.

      sales (доноры 1455/440/1579 + финалы владельца 0/1/2, n=6): доли 0.0/0.0/0.75/
        0.57/0.57/0.57. При пороге 0.8 ВСЕ 6 проходят не зажигая WARN (100%
        admission формально ≥80%) - НО 3 из 6 это САМИ целевые green-фикстуры
        (self-referential: калибровать HARD-гейт на выборке, треть которой - это
        и есть тесты, которые тот же гейт обязан не завалить, значит подгонять
        порог под тесты, а не под независимый сигнал).

      РЕШЕНИЕ: статус WARN везде (не HARD) - для razbor admission формально 0%
      (однозначно ниже бара), для sales 100% но на тонкой самоссылающейся выборке
      n=6, из которой половина - целевые фикстуры; конвенция файла та же, что у
      ap13_final_door/check_water sum_k: «admission на новых данных недостаточна
      → консервативно WARN, а не HARD». Порог доли 0.8 подобран так, что НИ ОДИН
      реальный образец (максимум 0.75 у sales-донора 1579) не зажигает WARN, а
      полностью или почти полностью абстрактный брак (доля >= 0.8, брак владельца
      «показываю что у меня стоит» дал бы 1.0) - зажигает всегда."""
    if form_class not in SUBSTANCE_CLASSES:
        return None
    long_paras = [p for p in paragraphs if len(p) > SUBSTANCE_LONG_PARA_LEN]
    if not long_paras:
        return {"abstract": [], "total": 0, "share": 0.0, "warn": False}
    abstract = [p for p in long_paras if not _para_has_concreteness_token(p)]
    share = len(abstract) / len(long_paras)
    return {"abstract": abstract, "total": len(long_paras), "share": share,
            "warn": share >= SUBSTANCE_SHARE_WARN}


# --- Анти-паттерны R3 («Анти-паттерны с нулём случаев в TOP» + WARN-список).
# №1-12 HARD (0 случаев в TOP-корпусе), №13-18 HARD (покрытие ≥88%),
# №20-26 WARN. №4 (эмодзи-иконка носителя 1-м символом нарратива) НЕ
# реализован - конфликтует с более новым законом владельца 
# (check_hook_premium_emoji требует эмодзи ПЕРВЫМ символом ВСЕГДА); новый
# закон перекрывает старую R3-находку (AC11 - закон владельца не теряем, R3
# уступает). №10/11/12 уже закрыты AI_CLICHE/WATER_KANC/BANNED_COLLOCATIONS
# выше. №16 (ссылка в нарративе) и №18 (нумерация в продающем) уже HARD в
# существующем профильном блоке (check_links/check_numbered_list, main()).

def ap1_promise_first_line(paragraphs):
    """№1 HARD. Обещание выгоды читателю в 1-й строке (местоимение+сумма)."""
    if not paragraphs:
        return False
    head = paragraphs[0]
    has_pronoun = re.search(r"\b(ты|тебе|тебя|твой|твоя|твои|вам|вас|ваш|вы)\b", head, re.IGNORECASE)
    has_money = _MONEY_RE.search(head)
    return bool(has_pronoun and has_money)


def ap2_bez_stack(paragraphs):
    """№2 HARD (нарратив). Стек «без X, без Y, без Z» в первых 2 строках."""
    chunk = " ".join(paragraphs[:2])
    return len(re.findall(r"\bбез\s+\w+", chunk, re.IGNORECASE)) >= 3


def ap3_service_seam(paragraphs):
    """№3 HARD. Служебный шов 2-й строкой («Что внутри:», «В видео выше…»)."""
    if len(paragraphs) < 2:
        return False
    p2 = paragraphs[1].strip().lower()
    return bool(re.match(r"^(что внутри|в видео выше|в этом посте|сегодня разберём|погнали)", p2))


def ap5_quote_block_razbor(text, form_class):
    """№5 HARD (разбор). Цитатный блок > с выводом в разборе."""
    if form_class != "razbor":
        return False
    return bool(re.search(r"(?m)^\s*>\s+\S", text))


def ap6_list_item_no_verb(text):
    """№6 WARN (downgrade от R3-HARD: эвристика глагола регексом не
    admission-тестирована на новых данных - консервативно WARN, а не HARD,
    пока не проверена на большем массиве). Пункт списка без глагола -
    существительные-ярлыки в столбик, сигнал, что список = перечисление
    инструментов, а не действие."""
    bullet_re = re.compile(r"^\s*[-•*]\s+(.+)$")
    items = [bullet_re.match(ln).group(1) for ln in text.splitlines() if bullet_re.match(ln)]
    if len(items) < 3:
        return []
    verb_re = re.compile(r"[а-яё]+(ть|тся|ться|л[аои]?|ет|ют|ешь|им|ите|уй|ай)\b", re.IGNORECASE)
    no_verb = [it for it in items if not verb_re.search(it)]
    return no_verb if len(no_verb) == len(items) else []


def ap7_glossary_aside(text):
    """№7 HARD. Отступление-глоссарий («для тех, кто не в теме»)."""
    return bool(re.search(r"для\s+тех,?\s+кто\s+не\s+в\s+теме|поясн(ю|им)\s+термин|если\s+кто\s+не\s+знает",
                           text, re.IGNORECASE))


def ap8_colon_rubric(text):
    """№8 HARD. Двоеточие-рубрикация («Погнали смотреть:»)."""
    return bool(re.search(r"погнали\s+смотреть\s*:|смотрим\s*:|разбираем\s*:", text, re.IGNORECASE))


def ap9_smotret_caps(text):
    """№9 HARD. СМОТРЕТЬ капсом."""
    return bool(re.search(r"\bСМОТРЕТЬ\b|\bСМОТРИ\b|\bСМОТРИТЕ\b", text))


def ap13_final_door(paragraphs, form_class):
    """№13 (покрытие ≥88%, R3). Финал-дверь (ссылка/«жми» последней строкой)
    в нарративе/продаже - финал обязан быть жестом/репликой, не CTA-дверью.
    HARD для narrative (где это ЧИСТЫЙ анти-паттерн - ссылки там и так HARD=0
    отдельным правилом, ap13 тут ловит только «жми/жмите» без явной ссылки).
    Для sales СПЕЦИАЛЬНО downgrade до WARN в main() - admission-фикс,
    прецедент green-фикстуры (владельца 3 одобренных финала запуска по решению автора
    заканчиваются ИМЕННО ссылкой CTA): R3-находка про анонимных доноров без
    воронки конфликтует с законом-якорем владельца (Sales Gate 4.S/UTM/launch-
    money-layer ОБЯЗЫВАЮТ явную ссылку в конце launch-поста). R3 сам
    предупреждает («ВАЖНО для целей владельца»): жанр владельца - не жанр доноров,
    закон владельца перекрывает R3-находку (AC11), см. также ap4 (аналогичный
    прецедент, см. блок анти-паттернов выше)."""
    if form_class not in ("narrative", "sales"):
        return False
    if not paragraphs:
        return False
    tail = paragraphs[-1]
    return bool(re.search(r"https?://|t\.me/|\bжми\b|\bжмите\b", tail, re.IGNORECASE))


def ap14_enum_instead_thesis(text, form_class):
    """№14 HARD (разбор). Перечисление вместо тезиса: 3-10 равноправных
    пунктов открывают пост вместо причинного тезиса."""
    if form_class != "razbor":
        return False
    paras = split_paragraphs(text)
    if len(paras) < 2:
        return False
    p2 = paras[1]
    lines = [l for l in p2.splitlines() if re.match(r"^\s*[-•*]\s", l)]
    return 3 <= len(lines) <= 10


def ap15_tire_enum_narrative(text, form_class):
    """№15 HARD (нарратив). Тире-перечисление в нарративе."""
    if form_class != "narrative":
        return False
    return len(re.findall(r"(?m)^\s*[-–—]\s", text)) >= 3


def ap17_round_metric_first(paragraphs):
    """№17 HARD. Крупная круглая метрика первым словом / '+' первым знаком."""
    if not paragraphs:
        return False
    head = paragraphs[0].strip()
    head_plain = re.sub(r"^[^\w+\d]+", "", head)  # снять эмодзи-префикс
    return bool(re.match(r"^\+?\d{2,}[\s%₽$]", head_plain))


def ap20_caps_words(text, form_class):
    """№20 WARN (нарратив). 3+ капс-слова."""
    if form_class != "narrative":
        return 0
    return len(re.findall(r"\b[А-ЯЁ]{4,}\b", text))


def ap21_plita(paragraphs):
    """№21 WARN. Плита 4+ строк в одном блоке (визуально плотный кирпич)."""
    return [(i, n) for i, p in enumerate(paragraphs, 1)
            if (n := len([l for l in p.splitlines() if l.strip()])) >= 4]


def ap22_tail_showcase_bullets(paragraphs):
    """№22 WARN. Хвост-витрина с буллетами (список последним блоком)."""
    if len(paragraphs) < 2:
        return False
    tail = paragraphs[-1]
    return bool(re.match(r"^\s*[-•*]", tail))


def ap23_reproach(text):
    """№23 WARN. Наставление-упрёк."""
    return bool(re.search(r"ты\s+должен|пора\s+бы|почему\s+ты\s+до\s+сих\s+пор|сколько\s+можно",
                           text, re.IGNORECASE))


def ap25_money_in_narrative(text, form_class):
    """№25 WARN (нарратив). Деньги в нарративе (верх 15% постов, низ 56%)."""
    if form_class != "narrative":
        return 0
    return len(_MONEY_RE.findall(_strip_md_plain(text)))


# --- воздух / медиана строк в абзаце / монотонность предложений (R3 §A/§E).

# 🔴 Д106 (скептик-раунд 37, по решению автора): ОДИНОКАЯ СТРОКА `**` - МАРКАП-
# АРТЕФАКТ ВЫГРУЗКИ ДОНОРСКОГО КОРПУСА (жирный, разорванный границей абзаца
# при экспорте: закрывающая/открывающая `**` съехала на СВОЮ строку вместо
# того, чтобы остаться в пустой строке-разделителе абзацев). 4 эталона несут
# такие строки (`scripts/etalons.json`: Донор-Б:1455 - 1, Донор-А:440 - 1,
# Донор-Б:1579 - 3, Донор-В:165 - 2). `text.splitlines()` в `check_air`
# ниже видит строку `**` как НЕПУСТУЮ (`"**".strip()` не пуст) - она съедает
# место честной пустой строки-разделителя и растит ЗНАМЕНАТЕЛЬ (непустые
# строки), а не числитель: воздух ПАДАЕТ там, где в оригинале был пробел
# между абзацами. Живой пример - Донор-В:165: 0.69 вместо честных ~0.93
# (2 строки `**` вместо 2 пустых строк меняют nonempty 16->14, empty 11->13).
_STRAY_BOLD_LINE_RE = re.compile(r"(?m)^[ \t]*\*\*[ \t]*$")


def _strip_stray_bold_lines(text):
    """Убирает СОДЕРЖИМОЕ строк, состоящих ТОЛЬКО из `**` (возможно с
    пробелами) - маркап-артефакт выгрузки, не контент (см. шапку выше).
    Сама строка/перевод строки остаётся на месте - строка становится ПУСТОЙ,
    ровно как была ДО артефакта (это разделитель абзацев, не жирный текст).

    Используется ТОЛЬКО в `check_air` ниже. `check_bold_count` и
    `_strip_md_plain` эту функцию НЕ зовут: там дефект того же класса
    закрыт ДРУГИМ способом (`re.S` на регексе `**...**`, см. докстринг
    `check_bold_count`) - нормализация тут стёрла бы РЕАЛЬНЫЙ жирный текст,
    для которого одинокая `**` служит настоящей открывающей/закрывающей
    парой мультистрочного выделения."""
    return _STRAY_BOLD_LINE_RE.sub("", text)


def check_air(text):
    """R3 §A. Воздух = пустые/непустые строки. Донор-медиана: 0.86
    (нарратив) / 0.87 (разбор), ПОЛ 0.65 дан явно в R3 для обоих. WARN ниже
    пола. F/S (0.78/0.80) - без явного пола в R3, не проверяем HARD/WARN.

    🔴 Д106 (раунд 37): нормализация ПЕРЕД замером - одинокие строки `**`
    (маркап-артефакт выгрузки, см. `_strip_stray_bold_lines` выше) очищаются
    до пустых строк ДО подсчёта, иначе они считаются непустыми и рушат
    знаменатель (см. шапку выше, живой пример Донор-В:165)."""
    text = _strip_stray_bold_lines(text)
    lines = text.splitlines()
    ne = [l for l in lines if l.strip()]
    empty = len(lines) - len(ne)
    return empty / max(len(ne), 1)


def check_paragraph_line_median(paragraphs):
    """R3 §A. Медиана строк в абзаце у доноров = 1.00 (нижний квартиль
    доноров - абзац из 3-4 строк). WARN если медиана >2."""
    import statistics as st
    counts = [len([l for l in p.splitlines() if l.strip()]) for p in paragraphs]
    if not counts:
        return 0
    return st.median(counts)


def check_sentence_monotony(text):
    """R3 §E. Разброс длины предложения 2-25 слов внутри поста - «ровный
    поток = генератор». WARN если размах (max-min слов) < 6 при 3+
    предложениях (меньше данных недостаточно для суждения о разбросе)."""
    clean = re.sub(r"[*_|>#`]", "", text)
    sentences = [s.strip() for s in re.split(r"[.!?…]+", clean) if s.strip()]
    lens = [len(s.split()) for s in sentences if s.split()]
    if len(lens) < 3:
        return None
    return max(lens) - min(lens)


# =============================================================================
# ВОЛНА 15 (топ-3 находки судьи бенчмарка по решению автора, план
# plans/2026-08-04-post-skill-v2.md). Три системных разрыва серии из 6
# постов против 7 эталонов доноров (цифра замера от этой редакции, набор с этой редакции
# расширен до 10 за счёт третьего донора, потом до 12 razbor-эталонами
# Донор-Б и в тот же день сведён к 11 дефектом Д23 раунда 4 - находки волны
# 15 сняты на прежних 7 и не пересчитывались, пороги ниже к размеру набора не
# привязаны):
#   (1) СИНТАКСИС ГЕНЕРАТОРА - медиана 13-21 слово в предложении против 3.5-13
#       у доноров, ноль «ударных» коротких предложений, строки-простыни;
#   (2) МЁРТВАЯ УСТНАЯ РЕЧЬ вне нарратива - разборы без единого знака живого
#       голоса, глоссарные вставки «а это X» вместо ввода референта делом;
#   (3) МЕХАНИКА КЛАССА - витрина вместо квитанции в продаже, домашка читателю,
#       скелет-однообразие внутри одной волны.
#
# 🔴 ГРАНИЦА ПРЕДЛОЖЕНИЯ ЗДЕСЬ ДРУГАЯ, ЧЕМ У check_sentence_median ВЫШЕ.
# В формате автора точки в конце абзаца НЕТ (закон 4.1.6.5), поэтому сплит
# только по [.!?…] склеивает весь абзац в одно «предложение»: бенчмарк-пост
# narrative-1 давал медиану 135 слов, донор-1455 - 12, хотя реальные значения
# 22 и 5. Судья мерил доноров с переносом строки как границей и получил
# нарратив 9-13 / разбор 10 / продажа 3.5-5 - эти числа воспроизводятся здесь
# ровно (13/10/9 · 11 · 5/4.5/5). Старый check_sentence_median НЕ трогаем: на
# нём висит HARD-пол разбора (sentence_median_min=5), менять ему смысл задним
# числом = менять уже принятый гейт.
# =============================================================================

# Пороги волны 15. Каждое число - ADMISSION на 7 донор-эталонах + 3 финалах владельца
# (scripts/tests/fixtures/green/*), замер лежит в отчёте волны. Правило: HARD
# ставится только там, где НИ ОДНА green-фикстура не падает; падает >=20% - WARN.
W15_PUNCH_MAX_WORDS = 4       # «ударное» предложение = <= 4 слов
W15_PUNCH_MIN_COUNT = 2       # минимум ударных на пост
W15_SENT_MEDIAN_WARN = 13     # потолок доноров (нарратив 13/10/9, разбор 11, продажа 5/4.5/5)
W15_SENT_MEDIAN_HARD = 16     # +23% запаса над худшей green (13.0) - см. admission
W15_GLUE_MIN_WORDS = 120      # ниже этого объёма плотность клея = шум (донор-492: 55 слов)
W15_GLUE_WARN_K = 22.0        # выше максимума green с объёмом >=120 слов (17.9)
W15_CPL_CEIL = {"narrative": 115, "razbor": 115, "sales": 80, "forwards": 115, "gate": 115,
                # Д8: событие. 115, как у нарратива/разбора, а не 80 продажи.
                # Замер событийных green-ivan: b17-3-0508 - 132, inf18-0608 - 128,
                # etalon-0608 - 120, то есть все трое печатают WARN. Это осознанно:
                # гейт WARN и не выше (см. текст сообщения ниже - собственные финалы
                # владельца держат 174-243), он печатает факт, решение за автором.
                "event": 115}
W15_RECEIPT_MAX_CHARS = 50    # «квитанция факта про себя» первой строкой после заголовка

W15_ORAL_PARTICLES = {"ну", "вот", "короче", "блин", "прям", "ребят", "ребята"}


def split_sentences_w15(text):
    """Границей предложения считаем И знак конца, И перенос строки (см. блок выше)."""
    clean = re.sub(r"[*_|>#`]", "", text)
    clean = re.sub(r"https?://\S+", " ", clean)
    return [s.strip() for s in re.split(r"[.!?…\n]+", clean) if s.strip()]


def check_rhythm_words(text):
    """Ритм в СЛОВАХ. Возвращает медиану/мин/макс/число ударных предложений.

    ADMISSION (7 доноров + 3 финала владельца):
      медиана: 13 · 10 · 9 (нарратив) · 11 (разбор) · 5 · 4.5 · 5 (продажа-доноры)
               8 · 12 · 8 (продажа-финалы владельца) -> максимум green = 13.0
      ударных (<=4 слов): 0 · 1 · 4 · 5 · 11 · 4 · 25 · 5 · 6 · 3
    Отсюда: потолок медианы 13 = WARN (ровно на максимуме green), 16 = HARD
    (запас 23%, ни одна green не падает). Порог ударных >=2 роняет donor-504 (0)
    и donor-492 (1) - 2/10 = 20%, то есть ровно на границе правила admission,
    поэтому ударные остаются WARN и печатают факты."""
    import statistics as _st
    lens = [len(s.split()) for s in split_sentences_w15(text) if s.split()]
    if not lens:
        return None
    return {
        "median": _st.median(lens),
        "min": min(lens),
        "max": max(lens),
        "punch": sum(1 for l in lens if l <= W15_PUNCH_MAX_WORDS),
        "n": len(lens),
    }


def check_chars_per_line(text):
    """Медиана знаков на НЕПУСТУЮ строку (разметка снята). Донор-медианы:
    нарратив/разбор 55-89, продажа 21-33. Потолки = +30% над верхом доноров.

    ADMISSION: нарратив/разбор при потолке 115 - 0/4 падений (89/55/80/80).
    Продажа при потолке 80 - падают все три финала владельца (174/243/199), это
    3/10 корпуса = 30% >= 20%, поэтому потолок ОСТАЁТСЯ WARN и никогда не HARD:
    доноры-продажники пишут строкой-репликой, владелец - абзацем, и его собственные
    одобренные финалы это узаконили. WARN печатает оба ориентира."""
    import statistics as _st
    ne = [l for l in text.splitlines() if l.strip()]
    if not ne:
        return None
    return _st.median([len(_strip_md_plain(l)) for l in ne])


def check_glue_density(text):
    """Детектор клея: «, а » + «который/которая/которое/которых...» на 1000 слов.
    Признак генератора - предложение растёт присоединением, а не новой мыслью.

    ADMISSION: на постах >=120 слов максимум green = 17.9/1000 (ivan-final-2),
    порог 22.0 выше него на 23%. Посты короче 120 слов НЕ меряются: у донора-492
    (55 слов) две запятые дают 36.4/1000 - это шум малой выборки, не клей."""
    plain = _strip_md_plain(text)
    words = _words(plain)
    n = len(words)
    if n < W15_GLUE_MIN_WORDS:
        return None
    glue_a = len(re.findall(r",\s+а\s+", plain))
    kotor = len(re.findall(r"\bкотор(?:ый|ая|ое|ые|ых|ым|ыми|ого|ой|ую|ом|ому)\b", plain, re.I))
    return {
        "glue_a": glue_a, "kotor": kotor, "words": n,
        "k": 1000.0 * (glue_a + kotor) / n,
    }


def check_oral_layer(text):
    """Живой слой: хотя бы один знак устной речи на пост - скобка-улыбка `))`,
    многоточие, вопрос или разговорная частица (ну/вот/короче/блин/прям/ребят).

    🔴 4c, ПЕРЕСЧЁТ ADMISSION ПО КОРПУСУ. Старая формулировка «10/10 green
    несут знак, падений 0» на расширенном корпусе НЕПРАВДА: из 12 постов
    green-ivan знак отсутствует у ivan-final-1 (архив по решению автора, живых знаков
    вне URL ровно ноль). Честный замер - 11/12 = 8.3% падения, порог закона
    калибровки 20%, поэтому статус остаётся HARD, но обоснование теперь
    соответствует корпусу, а единственное падение снимается флагом
    --allow-no-oral с печатью причины (архив старше закона от этой редакции).

    URL-фикс по решению автора (находка проверки витрины): «?» из https://...?utm_source=...
    засчитывался как «вопрос ×1» - пост osn17 без единого живого знака проходил
    HARD на вопросе из UTM-ссылки. Перед подсчётом все URL вырезаются."""
    no_urls = re.sub(r"(?:https?://|t\.me/)\S+", " ", text)
    plain = _strip_md_plain(no_urls)
    # 🔴 ПРАВКА ВЛАДЕЛЬЦА по решению автора: скобка `))` ВЫВЕДЕНА из знаков живого слоя.
    # Причина дословно: «каждый раз ты мне эти странные скобочки ставишь, вообще их
    # неуместно ставишь в каждом посте, это шаблонность». Скобка стояла дешёвым
    # способом закрыть HARD-гейт живого слоя, поэтому писатель ставил её в КАЖДЫЙ
    # пост независимо от интонации места. Живой слой теперь закрывается многоточием,
    # вопросом или разговорной частицей - тем, что несёт смысл, а не оформление.
    marks = {
        "многоточие": no_urls.count("…") + len(re.findall(r"\.\.\.", no_urls)),
        "вопрос": no_urls.count("?"),
        "частица": sum(1 for w in _words(plain) if w in W15_ORAL_PARTICLES),
    }
    return marks


def check_glossary_insert(text):
    """Глоссарная вставка внутри предложения: «..., а это X» / «X это когда».
    Родила фикс висящих референтов - вместо ввода делом писатель приклеивает
    определение. ADMISSION: 0/10 green, ловится в 2 из 6 постов бенчмарка
    («Заявка это когда...», «...в SaleBot, а это платформа ботов»). WARN."""
    plain = _strip_md_plain(text)
    hits = []
    for m in re.finditer(r"[^.!?…\n]{3,80}?,\s+а\s+это\s+[^.!?…\n]{3,60}", plain, re.I):
        hits.append(m.group(0).strip())
    # `когда\b(?!-)` - иначе «это когда-то было» читается как определение
    for m in re.finditer(r"[А-ЯЁа-яё\w]+\s+это\s+когда\b(?!-)[^.!?…\n]{0,60}", plain, re.I):
        hits.append(m.group(0).strip())
    return hits


def check_homework_soft(text):
    """Домашка читателю, широкий слой (WARN). Узкий HARD-набор живёт в
    check_homework_action и ловит только прямые формулы («перепиши свой»,
    «сделай задание»). Прямой рецидив бенчмарка - «Возьми слово, которое звучит
    в твоих постах, и сделай под него статью» - мимо него прошёл.

    ADMISSION: 0/10 green (доноры-нарративы и финалы владельца таких оборотов не
    несут), 1/6 бенчмарк-постов (razbor-2, ровно тот рецидив). WARN, не HARD:
    закон-якорь №11 уже держит HARD узким набором, широкий слой обязан печатать
    факты, а не блокировать по эвристике."""
    plain = _strip_md_plain(text)
    pat = re.compile(
        r"возьми\s+[^.!?\n]{0,60}?\s+и\s+(?:сделай|перепиши|собери|попробуй|напиши|проверь|посчитай)|"
        r"\bперепиши\s+(?:свой|своё|свою|его|её|их|этот|тот)\b|"
        r"\bпопробуй\s+сам\b|\bсделай\s+сам\b|\bповтори\s+за\s+мной\b|"
        r"\bпроверь\s+(?:свой|свою|своё)\b|\bоткрой\s+(?:свой|свою|своё)\b|"
        r"\bпосчитай\s+(?:свой|свою|своё)\b|\bразбери\s+(?:свой|свою|своё)\b|"
        r"\bнапиши\s+(?:свой|свою|своё)\s+\w+\s+(?:по|под|как)\b",
        re.IGNORECASE)
    return [m.group(0).strip() for m in pat.finditer(plain)]


# --- Стоп-слова для сверки хука с именем героя (служебная лексика, не имя).
W15_HERO_STOPWORDS = {
    "скилл", "скилла", "скиллом", "пост", "поста", "постов", "сборка", "сборки",
    "новый", "новая", "новое", "через", "чтобы", "который", "которая", "одно",
    "одна", "один", "под", "для", "про", "как", "это", "того", "свой", "своя",
}


def check_showcase_hook(paragraphs, hero):
    """Механика продажи: хук-заголовок не должен быть ИМЕНЕМ ПРОДУКТА.
    Верх доноров открывает продажу квитанцией факта про себя («[+3 оплаты
    ночью]» -> «Я сплю - продажи идут.»), генератор открывает витриной
    («Воронка под одно кодовое слово»).

    Правило: если заголовок содержит значимое слово из --hero, спасает только
    квитанция - первая строка после заголовка короче 50 знаков. Возвращает
    (hit: bool, детали).

    ADMISSION: гейт молчит без --hero, поэтому на 10 green-фикстурах (ни одна не
    передаёт --hero: доноры чужие, финалы владельца архивные) падений 0 by design.
    Контроль ложного срабатывания сделан отдельно - все 6 продажных green
    прогнаны с чужим --hero «воронка под кодовое слово»: 0 срабатываний. Статус
    WARN: связь «имя героя в заголовке» - эвристика, решение за автором."""
    if not hero or not paragraphs:
        return False, ""
    head_plain = _strip_md_plain(paragraphs[0]).lower()
    hero_tokens = [w for w in re.findall(r"[a-zа-яё0-9\-]{4,}", str(hero).lower())
                   if w not in W15_HERO_STOPWORDS]
    matched = [w for w in hero_tokens if w in head_plain]
    if not matched:
        return False, ""
    second = _strip_md_plain(paragraphs[1]).strip() if len(paragraphs) > 1 else ""
    first_line = second.splitlines()[0].strip() if second else ""
    if first_line and len(first_line) <= W15_RECEIPT_MAX_CHARS:
        return False, f"имя героя в хуке ({', '.join(matched)}), но следом квитанция ({len(first_line)} зн.)"
    return True, (f"хук несёт имя героя ({', '.join(matched)}), а первая строка после него "
                  f"{len(first_line)} зн. (квитанция = <= {W15_RECEIPT_MAX_CHARS})")


# --- AC10/AC12, класс R2-12 (плейсхолдеры). HARD только на квадратные
# скобки-заглушки; фигурные {скобки} - легитимная механика бота (см. докстринг).

# Цель markdown-анкора СРАЗУ после `]`: живой URL либо ОДНА подстановка
# механики отправки в фигурных скобках ({spots}, {ссылка_анкеты}, {штаб}).
# Идентификатор без пробелов - именно форма подстановки, а не любой текст:
# `[Оставить заявку](впишу ссылку потом)` анкором не считается и ловится.
ANCHOR_TARGET_RE = re.compile(r"\(\s*(https?://|\{[^\s{}]{1,60}\}\s*\))")

# Словарь ЗАГЛУШКИ «впишу потом». Отменяет исключение «в скобке есть цифра»:
# `[живой факт по решению автора]` - заглушка с датой, а не квитанция факта.
PLACEHOLDER_WORDS_RE = re.compile(
    r"(живой\s+факт|факт\s+дня|пруф|скрин\w*\s+будет|вставить|вставлю|вписа\w+|"
    r"впиш\w+|подстав\w+|уточн\w+|добра\w+|добав\w*\s+потом|заглушк\w+|"
    r"плейсхолдер|позже|потом|TODO|TBD|FIXME|XXX)", re.IGNORECASE)


def check_placeholders(text):
    """Класс R2-12. HARD. Владелец: «[живой факт]», «[пруф дня]» - убирай
    полностью - ЭТО ВСЕГДА квадратные скобки (авторские заглушки «впишу
    потом»). Фигурные скобки {...} - подстановки МЕХАНИКИ отправки бота
    ({spots}, {ссылка_эфира}, {ИМЯ}, {VIP}...) - та же семантика, что и
    FUNNEL-маркеры в post-phase-gate.sh (там {имя}/{vip}/{кабинет}/{канал}
    уже распознаются как легитимная бот-механика, не брак). Admission-фикс
    (прецедент green-фикстуры: пост владельца с {ссылка_эфира} - системная
    переменная трансляции, не заглушка-«впишу-потом») - жёсткий белый
    список слов заменён на «любая {фигурная_скобка} легитимна», как и в
    остальном конвейере.

    🔴 РАУНД 1 (скептик по решению автора, новый дефект 4): правило ошибалось В ОБЕ
    СТОРОНЫ, оба края починены здесь.
    (а) ЛОЖНОЕ СРАБАТЫВАНИЕ. Исключение анкора было зашито как `](https?://`,
        поэтому легальный анкор с ПОДСТАНОВКОЙ отправки - `[Оставить
        заявку]({ссылка_анкеты})` - считался заглушкой. Замер боевого корпуса
        пакетов: 31 срабатывание класса, ВСЕ 31 - такие анкоры (0 настоящих
        заглушек). Теперь цель анкора легальна и как http(s)-URL, и как
        одиночная подстановка `{идентификатор}` (тот же белый список
        механики отправки: {spots}, {ссылка_эфира}, {штаб}...). Форма
        подстановки задана ФОРМОЙ (идентификатор без пробелов), а не
        перечнем имён: перечень был бы привязкой к запуску автора.
    (б) ЛОЖНЫЙ ПРОПУСК. Исключение «квитанция факта» было «в скобке есть
        цифра - пропускаем», и дословная жалоба автора `[живой факт]`
        переставала ловиться, стоило дописать дату: `[живой факт по решению автора]`.
        Теперь цифра спасает скобку ТОЛЬКО если внутри нет словаря
        заглушки (PLACEHOLDER_WORDS_RE: живой факт, пруф, вставить,
        уточнить, TODO...). Полностью снять «цифровое» исключение нельзя:
        green-фикстура донора D id=440 открывается квитанцией
        `**[+3 оплаты ночью]**` - это факт, а не «впишу потом», и удаление
        исключения красит зелёный корпус. Улика: tests/fixtures/green/
        donor-440.txt:1."""
    hits = []
    for m in re.finditer(r"\[[^\]\n]{2,60}\]", text):
        frag = m.group(0)
        if frag.lower() in ("[ ]", "[x]"):
            continue
        if re.search(r"\d", frag) and not PLACEHOLDER_WORDS_RE.search(frag):
            continue  # квитанция факта (число, но без словаря заглушки)
        # 🔴 4c: РЕДАКТОРСКАЯ ПОМЕТКА - не заглушка автора. Плейсхолдер это
        # «впишу потом» ВНУТРИ поста; пометка обрезки описывает состояние
        # ИСТОЧНИКА и живёт вне текста. Улика: green-ivan/etalon-0608.txt
        # (эталон владельца 6.08, снят со скрина) заканчивается на «[обрез скрина -
        # хвост поста добрать у владельца / из канала]» и падал HARD на этой
        # пометке, а не на своём дефекте (BASELINE §5, строка «плейсхолдеры»).
        if re.match(r"\[\s*(обрез|сокращ|пропущ|прим\.|ред\.|цитата\s+обрезан|"
                    r"фрагмент\s+обрезан)", frag, re.IGNORECASE):
            continue
        # Закон 29 (владелец 5.08, _pravki-ivana-kanon-2607.md): ссылки зашиваются
        # в слова markdown-анкором [текст](url) - анкор ссылки НЕ плейсхолдер.
        # Цель анкора легальна в двух формах: живой http(s)-URL И подстановка
        # механики отправки `{идентификатор}` (см. (а) в докстринге).
        if ANCHOR_TARGET_RE.match(text[m.end():m.end() + 80]):
            continue
        hits.append(frag)
    return hits


# --- класс R2-10, закон-якорь №7 «Цена цифрой - никогда». HARD.
_CURRENCY_RE = re.compile(
    r"\d[\d\s]*[.,]?\d*\s*(₽|руб\.?|рубл\w*|\$|долл\w*|usd|eur|евро|тыс\.?\s*(₽|руб)|k\s*(₽|\$)|тысяч\w*\s*рубл\w*)",
    re.IGNORECASE)
# Закон бьёт по ЦЕНЕ ОФФЕРА (то, что человек платит), НЕ по результату/доходу
# клиента ($500 заработал, +3 оплаты ночью - это факты-квитанции, разрешены,
# R3 «Механика письма по классам»/продажа). Контекст-слова цены - в радиусе
# 40 символов ДО суммы: без них денежная цифра не триггерит закон-якорь №7.
_PRICE_CONTEXT_RE = re.compile(
    r"(стоит|стоимост\w*|цена|цену|цены|тариф\w*|участи\w*\s+(стоит|за)|"
    r"вход\w*\s+(стоит|за)|оплат\w*\s+за\s+(доступ|участие|вход)|"
    r"плат\w*\s+(за\s+доступ|за\s+вход)|записаться\s+за|"
    r"билет\w*\s+(стоит|за)|абонемент\w*\s+(стоит|за))", re.IGNORECASE)


def check_price_digit(text):
    """Класс R2-10, закон-якорь №7. HARD. Ловит ЦЕНУ ОФФЕРА цифрой - число+
    валютный маркер рядом (1997₽, $97, 2997 руб, 97 тыс) С контекст-словом
    цены/тарифа/стоимости в предыдущих 40 символах. Admission-фикс
    :
    без контекст-слова денежная цифра описывает доход/результат, не цену -
    не триггерит. Время (19:00) не совпадает с валютным маркером."""
    hits = []
    for m in _CURRENCY_RE.finditer(text):
        window_start = max(0, m.start() - 40)
        window = text[window_start:m.start()]
        if not _PRICE_CONTEXT_RE.search(window):
            continue
        s = max(0, m.start() - 15)
        hits.append(text[s:m.end() + 10].replace("\n", " ").strip())
    return hits


# --- класс R2-7 (частичное машинное покрытие; полный гейт AC4 - Z2/04-review).
def check_deferred_promise(text):
    """Класс R2-7, чек-лист п.11. HARD. Запрет «расскажу позже/на эфире» -
    обрубание ценности заглушкой (тот же вердикт, что и реклама вместо
    ценности, R2 класс 2)."""
    return bool(re.search(
        r"расскажу\s+(на\s+эфире|позже|отдельно|в\s+следующий\s+раз)|"
        r"покажу\s+(позже|отдельно|в\s+другой\s+раз)|"
        r"это\s+отдельная\s+работа|"
        r"разберём\s+на\s+(созвоне|эфире)", text, re.IGNORECASE))


def check_homework_action(text):
    """Класс R2-7 / канон п.22. HARD. Единственное действие читателя =
    регистрация (закон-якорь №11).

    🔴 4c (BASELINE по решению автора, «функция-призрак» №2): узкий набор ловил ТОЛЬКО
    прямые формулы и пропускал живой брак B8-ruchnaya-domashka «Возьми свой
    последний пост, выпиши из него слово и перепиши описание руками. Потом
    сядь и составь табличку» - широкий слой check_homework_soft его видел,
    но печатал WARN и выдачу не блокировал. Теперь HARD-набор включает те же
    обороты, что и широкий слой: «возьми … и <глагол>», «составь табличку»,
    «сядь и …». ADMISSION замером: 0/12 green-ivan, 0/10 донор-эталонов."""
    return bool(re.search(
        r"перепиши\s+(?:свой|своё|свою)|возьми\s+свой\s+\w+\s+и|сделай\s+задание|"
        r"домашн\w+\s+задани|попробуй\s+сам\s+сделать|"
        r"возьми\s+[^.!?\n]{0,60}?\s+и\s+(?:сделай|перепиши|собери|попробуй|напиши|"
        r"проверь|посчитай|выпиши)|"
        r"составь\s+(?:табличку|таблицу|список)|сядь\s+и\s+\w+",
        text, re.IGNORECASE))


# --- класс R2-2 / канон п.24 (частичное покрытие; полный гейт AC4 - Z2/04-review).
def check_program_enum(text):
    """Класс R2-2 / B4. Перечисление программы события вместо ценности.

    🔴 4c (BASELINE по решению автора, «функция-призрак» №1): на своей же фикстуре
    B4-perechislenie-programmy функция возвращала 0. Словарь искал ТОЛЬКО
    строки «модуль N / день N / урок N», а живой брак выглядит иначе:
    «На эфире разберём: как поставить …, как собрать …, как выложить …,
    как считать … и как не сжечь …» - опись программы одной строкой через
    двоеточие. Добавлена вторая ось: глагол-анонс + двоеточие + 3 и более
    однотипных пункта «как/что …».
    ADMISSION второй оси: 0/12 green-ivan, 0/10 донор-эталонов. Эталон
    6.08 несёт «Я хочу разобрать две вещи детально:» - ДВА пункта, порог
    в три пункта его не задевает намеренно.

    Возвращает (кол-во строк-рубрик, список описей-одной-строкой)."""
    rubric_lines = len(re.findall(
        r"(?m)^\s*[-•*]?\s*(модуль|день|урок|блок)\s*\d+", text, re.IGNORECASE))
    inline = [m.group(0)[:120].replace("\n", " ") for m in re.finditer(
        r"(разбер|покаж|пройд|расскаж|будет)\w*[^.\n:]{0,40}:\s*"
        r"[^.\n]*?\b(как|что)\b[^.\n]*?,[^.\n]*?\b(как|что)\b[^.\n]*?,[^.\n]*?\b(как|что)\b",
        text, re.IGNORECASE)]
    return rubric_lines, inline


# --- AC5, класс R2-3/4 (огрызок / выдуманные факты), закон-якорь №1.
# Служебная лексика факт-чека имён (вынесена из check_factbase, чтобы стеммы
# считались один раз и список был виден снаружи).
# Универсальная часть (бренды-инструменты, одинаковы у всех) живёт в коде.
# 🔒 Личная часть - имена автора, его продуктов и его транслитераций - НЕ здесь:
# она приходит из внешнего словаря владельца (`factbase_common_words`, см. шапку
# модуля). Хардкод личных имён означал бы, что у ученика факт-чек молча пропускает
# ЧУЖИЕ имена и придирается к его собственным. Нет словаря -> только универсальные.
FACTBASE_COMMON_WORDS = {"Telegram", "Instagram", "Claude"} | {
    w for w in (OWNER_LEXICON.get("factbase_common_words") or []) if isinstance(w, str)
}

# Падежные окончания русского - длинные раньше коротких, иначе «ами» срежется как «и».
_RU_CASE_ENDINGS = ("ами", "ями", "ов", "ев", "ой", "ей", "ом", "ем", "ым", "им",
                    "ах", "ях", "а", "я", "у", "ю", "ы", "и", "е", "о")


def _stem_ru(word):
    """Лёгкий стеммер падежей для сверки имён поста с факт-базой (AC5в).
    Не морфология, а нормализатор: ё→е (Артём/Артем - одно имя), затем до двух
    проходов среза падежного окончания. Срез разрешён словам от 4 знаков и не
    укорачивает основу меньше 3 знаков - этого хватает на «Артёма»=«Артём» и
    «Вики»=«Вика» и не схлопывает разные имена (Марк, Марина, Донор-А)."""
    w = word.lower().replace("ё", "е")
    for _ in range(2):
        if len(w) < 4:
            break
        for e in _RU_CASE_ENDINGS:
            if w.endswith(e) and len(w) - len(e) >= 3:
                w = w[:-len(e)]
                break
        else:
            break
    return w


# Кандидат в имя собственное = слово с заглавной, стоящее НЕ в начале предложения.
# 🔴 ФИКС (скептик-раунд 4, по решению автора, БЛОКЕР 2). БЫЛО: `(?<![.!?«"\n])\s([А-ЯЁ]…)` -
# «не после точки/кавычки/перевода строки». Перед заглавной могло стоять что угодно
# ещё: эмодзи, закрывающая скобка, цифра. Из-за этого КАНОНИЧЕСКИЙ CTA
# «👉 Вписаться в смену» давал «имя собственное Вписаться», и пост валился факт-чеком
# AC5в за выдуманное имя, которого в тексте нет. Тот же ложный улов ловили
# «🔥 Забирай путёвку» и скобка-улыбка «)) Дальше». Тогда слева стали требовать
# СТРОЧНУЮ РУССКУЮ букву - и проверка ослепла на 8 из 10 реальных позиций имени.
#
# 🔴 ФИКС (скептик-раунд 5, по решению автора, ВАЖНО 3): ЛЕВЫЙ КОНТЕКСТ РАСШИРЕН ДО СПИСКА.
# Имя стоит после запятой («приехали Артём, Виталий и Вика»), после числа («3 Виталия»),
# после латиницы («config Виталий»), после тире/дефиса списка, после двоеточия, после
# закрывающей кавычки, сразу за открывающей скобкой - все эти позиции старая версия
# пропускала молча, то есть выдуманное имя в них проходило факт-чек AC5в насквозь.
# ЛОВИМ, если слева (через пробелы; для скобки - и без них) стоит:
#     строчная кириллица · строчная латиница · цифра · запятая · двоеточие ·
#     дефис/тире · закрывающая кавычка » или " · открывающая скобка (
# НЕ ЛОВИМ: начало строки · после . ! ? · после ) · после эмодзи и прочих символов.
#
# ⚠️ ЗАДОКУМЕНТИРОВАННАЯ ГРАНИЦА: имя ПОСЛЕ ТОЧКИ остаётся невидимым («Вчера всё
# решилось. Виталий позвонил сам»). Это НЕ недосмотр: после точки идёт начало предложения,
# где с заглавной пишется ЛЮБОЕ слово, и отличить там имя собственное от обычного слова
# без морфологии/NER невозможно. Ловить всё подряд дороже, чем пропустить: каждое ложное
# «имя» валит пост HARD-фейлом AC5в за выдумку, которой нет. Имена в начале предложения
# остаются на человеческом ревью 4.R (референты).
#
# 🔴 ФИКС (волна 6, по решению автора, ВАЖНО): ИМЯ СРАЗУ ЗА ОТКРЫВАЮЩЕЙ КАВЫЧКОЙ.
# БЫЛО: в левом классе-разрешителе стояли только ЗАКРЫВАЮЩИЕ кавычки (» и прямая ").
# Позиция «скилл «Гроубокс под код-слово» собирает» - имя собственное сразу за
# открывающей «ёлочкой» - была слепой зоной: между кавычкой и заглавной нет пробела,
# а сама открывающая кавычка в разрешителях отсутствовала. Названия продуктов, скиллов,
# каналов и кодовых слов пишутся в кавычках почти всегда, то есть класс R2-6 (висящее
# имя, которого нет в факт-базе) проезжал факт-чек AC5в в самой частой своей позиции.
# СТАЛО: открывающие « и “ добавлены разрешителем без обязательного пробела справа.
# Закрывающие » и " в списке остались как были.
# ⚠️ ГРАНИЦА КАВЫЧКИ (тот же закон, что у точки): кавычка засчитывается разрешителем
# ТОЛЬКО когда сама стоит В СЕРЕДИНЕ фразы - слева от неё строчная буква или цифра
# («скилл «Гроубокс» собирает»). Кавычка в начале строки
# открывает ПРЯМУЮ РЕЧЬ, и первое слово в ней пишется с заглавной по правилу начала
# предложения, а не потому что это имя («Каждый месяц всё заново» - эту фразу я
# слышу от экспертов, живой финал владельца от этой редакции). Ловить её = валить пост
# HARD-фейлом AC5в за выдумку, которой нет - ровно тот класс ложняка, из-за
# которого выше уже вырезаны эмодзи и точка.
#
# 🔴 ФИКС (волна 7, по решению автора, ВАЖНО 1): ПРЯМАЯ РЕЧЬ ПОСЛЕ ДВОЕТОЧИЯ И ЗАПЯТОЙ.
# БЫЛО: в кавычечной ветке (третья альтернатива) разрешителями слева от « стояли
# ещё двоеточие и запятая - `[а-яёa-z0-9,:]`. Но двоеточие и запятая перед открывающей
# кавычкой - это НЕ середина фразы, это КАНОНИЧЕСКАЯ ПОДАЧА ПРЯМОЙ РЕЧИ:
# «владелец сказал: «Каждый месяц всё заново»», «он пишет, «Так делают все»»,
# «мое правило: «Один пост = один скилл»». Первое слово внутри такой кавычки пишется
# с заглавной по правилу начала предложения, именем собственным оно не является -
# а пост валился HARD-фейлом AC5в за «выдуманное имя» Каждый / Так / Один, которого
# в факт-базе нет и быть не может. Тот же класс ложняка, из-за которого выше уже
# вырезаны эмодзи, точка и кавычка в начале строки.
# СТАЛО: слева от « остаётся ТОЛЬКО строчная буква (кириллица/латиница) или цифра,
# вплотную или через пробел - живой кейс «скилл «Гроубокс под код-слово» собирает»
# ловится как раньше. Двоеточие и запятая как разрешители ПЕРВОЙ ветки (запятая или
# двоеточие + пробел + заглавная: «приехали Артём, Виталий и Вика») НЕ тронуты -
# там кавычки нет, значит и подачи прямой речи нет.
_PROPER_NAME_RE = re.compile(
    r'(?:[а-яёa-z0-9,:»"–—-][ \t\u00a0]+|\([ \t]*|[а-яёa-z0-9][ \t\u00a0]*[«“][ \t]*)([А-ЯЁ][а-яё]{2,})'
)


def _extract_proper_names(text_plain):
    """Слова с заглавной НЕ в начале предложения = кандидаты в имена собственные.

    Левый контекст-разрешитель перечислен у `_PROPER_NAME_RE`: строчная буква
    (кириллица/латиница), цифра, запятая, двоеточие, тире, закрывающая кавычка,
    открывающая скобка, открывающая кавычка « или “ в СЕРЕДИНЕ фразы (волна 6;
    кавычка в начале строки = прямая речь, не имя). Перед « разрешена ТОЛЬКО
    строчная буква или цифра (волна 7): двоеточие и запятая перед кавычкой = подача
    прямой речи («сказал: «Каждый…»», «пишет, «Так…»»), а не имя собственное.
    Начало строки, позиция после `.!?`, после `)` и после
    эмодзи именем НЕ считаются; имя сразу после точки принципиально неразрешимо
    без NER и пропускается осознанно (см. границу в комментарии выше)."""
    return set(_PROPER_NAME_RE.findall(text_plain))


# =============================================================================
# ЧИСЛИТЕЛЬНЫЕ СЛОВАМИ В ФАКТ-ЧЕКЕ (волна 16, по решению автора). Уровень WARN.
# =============================================================================
# Дыра, которую это закрывает: гейт AC5б сверял с факт-базой только ЦИФРЫ (`\d`).
# Пост, написавший то же число ПРОПИСЬЮ («с пятого ролика», «двое суток»,
# «от пятидесяти до ста»), проезжал факт-чек насквозь - выдуманное число просто
# меняло начертание. Теперь слова-числительные нормализуются в значения и идут
# в ту же subset-сверку; факт-база нормализуется тем же кодом, поэтому «50-100»
# цифрами в источнике покрывает «от пятидесяти до ста» словами в посте.
#
# Уровень намеренно WARN, а не HARD: русское числительное омонимично обычному
# слову («одна из причин», «в первую очередь»), полный разбор требует морфологии,
# и ложный HARD валил бы здоровый пост. WARN печатает НАЙДЕННОЕ - решение за
# человеком в 04-review.
#
# БЕЛЫЙ СПИСОК идиом: обороты, где числительное не считает ничего. Список
# ПОПОЛНЯЕМЫЙ - новая идиома дописывается сюда одной строкой-регексом.
NUMERAL_IDIOMS = [
    r"в\s+один\s+заход",
    r"одним\s+словом",
    r"один\s+в\s+один",
    r"в\s+два\s+счёта|в\s+два\s+счета",
    r"на\s+пару\b",
    r"с\s+одной\s+стороны",
    r"ни\s+одн(?:ому|ого|ой|ому|им|их|а|о|у|и)?\b",
    r"\bодн(?:ому|ого|ой|им|их|ими|а|о|и|у)?\s+из\b",
    r"в\s+перв(?:ую|ой)\s+очередь",
    r"во-?\s?перв(?:ых|о)|во-?\s?втор(?:ых|о)|в-?\s?трет(?:ьих|ье)",
    # пополняемо ниже
    r"в\s+двух\s+словах",
    r"на\s+все\s+сто\b",
    r"перв(?:ым|ое)\s+дел(?:ом|о)",
    r"одн(?:о|а|и)\s+и\s+т(?:о|е)\s+же",
    r"с\s+перв(?:ого|ой)\s+(?:взгляда|попытки)",
]
_NUMERAL_IDIOM_RE = re.compile("|".join(NUMERAL_IDIOMS), re.IGNORECASE)


def _numeral_forms(stem, endings, value, rank):
    return {stem + e: (value, rank) for e in endings}


def _build_ru_numeral_map():
    """Словарь «словоформа → (значение, разряд)». Разряды: unit 1-9,
    teen 11-19, ten 20-90, hundred 100-900, mult (тысяча/миллион),
    ord (порядковые 1-10, в составные не складываются)."""
    m = {}
    # --- единицы (количественные + собирательные «двое/трое/четверо») ---
    units = {
        1: ["один", "одна", "одно", "одни", "одного", "одному", "одним", "одном",
            "одной", "одну", "одних", "одними"],
        2: ["два", "две", "двух", "двум", "двумя", "двое", "двоих", "двоим", "двоими"],
        3: ["три", "трёх", "трех", "трём", "трем", "тремя", "трое", "троих", "троим"],
        4: ["четыре", "четырёх", "четырех", "четырём", "четырем", "четырьмя",
            "четверо", "четверых", "четверым"],
        5: ["пять", "пяти", "пятью", "пятеро", "пятерых", "пятерым"],
        6: ["шесть", "шести", "шестью", "шестеро", "шестерых"],
        7: ["семь", "семи", "семью", "семеро", "семерых"],
        8: ["восемь", "восьми", "восемью", "восьмью", "восьмеро"],
        9: ["девять", "девяти", "девятью", "девятеро"],
        10: ["десять", "десяти", "десятью", "десятеро"],
    }
    for val, forms in units.items():
        for f in forms:
            m[f] = (val, "unit" if val < 10 else "teen")
    # --- 11-20 (регулярная парадигма «-ать / -ати / -атью») ---
    teens = {11: "одиннадцат", 12: "двенадцат", 13: "тринадцат", 14: "четырнадцат",
             15: "пятнадцат", 16: "шестнадцат", 17: "семнадцат", 18: "восемнадцат",
             19: "девятнадцат", 20: "двадцат"}
    for val, stem in teens.items():
        m.update(_numeral_forms(stem, ["ь", "и", "ью"], val,
                                "teen" if val < 20 else "ten"))
    # --- десятки ---
    m.update(_numeral_forms("тридцат", ["ь", "и", "ью"], 30, "ten"))
    m.update({"сорок": (40, "ten"), "сорока": (40, "ten")})
    for val, forms in {
        50: ["пятьдесят", "пятидесяти", "пятьюдесятью"],
        60: ["шестьдесят", "шестидесяти", "шестьюдесятью"],
        70: ["семьдесят", "семидесяти", "семьюдесятью"],
        80: ["восемьдесят", "восьмидесяти", "восемьюдесятью", "восьмьюдесятью"],
        90: ["девяносто", "девяноста"],
    }.items():
        for f in forms:
            m[f] = (val, "ten")
    # --- сотни ---
    for val, forms in {
        100: ["сто", "ста"],
        200: ["двести", "двухсот", "двумстам", "двумястами", "двухстах"],
        300: ["триста", "трёхсот", "трехсот", "трёмстам", "тремстам", "тремястами"],
        400: ["четыреста", "четырёхсот", "четырехсот", "четырёмстам", "четырьмястами"],
        500: ["пятьсот", "пятисот", "пятистам", "пятьюстами", "пятистах"],
        600: ["шестьсот", "шестисот", "шестистам", "шестьюстами"],
        700: ["семьсот", "семисот", "семистам", "семьюстами"],
        800: ["восемьсот", "восьмисот", "восьмистам", "восемьюстами"],
        900: ["девятьсот", "девятисот", "девятистам", "девятьюстами"],
    }.items():
        for f in forms:
            m[f] = (val, "hundred")
    # --- множители ---
    for f in ["тысяча", "тысячи", "тысяч", "тысяче", "тысячу", "тысячей", "тысячах"]:
        m[f] = (1000, "mult")
    for f in ["миллион", "миллиона", "миллионов", "миллиону", "миллионе",
              "миллионом", "миллионах"]:
        m[f] = (1000000, "mult")
    # --- порядковые 1-10 (отдельный разряд: в составные числа не складываются) ---
    ORD_END = ["ый", "ой", "ая", "ое", "ые", "ого", "ому", "ым", "ом", "ых", "ыми", "ую"]
    for val, stem in {1: "перв", 2: "втор", 4: "четвёрт", 5: "пят", 6: "шест",
                      7: "седьм", 8: "восьм", 9: "девят", 10: "десят"}.items():
        for f in _numeral_forms(stem, ORD_END, val, "ord"):
            m.setdefault(f, (val, "ord"))
    for f in _numeral_forms("четверт", ORD_END, 4, "ord"):
        m.setdefault(f, (4, "ord"))
    for f in ["третий", "третья", "третье", "третьи", "третьего", "третьему",
              "третьим", "третьей", "третью", "третьих", "третьими"]:
        m.setdefault(f, (3, "ord"))
    return m


RU_NUMERAL_WORDS = _build_ru_numeral_map()


def _combine_numeral_run(run):
    """Подряд идущие числительные → список (фраза, значение).
    Складываются только по УБЫВАНИЮ разряда («двадцать пять» = 25,
    «сто двадцать пять» = 125); «два три» - это ДВА числа, а не пять.
    Множитель умножает накопленное («две тысячи» = 2000).
    Порядковое всегда стоит отдельным числом."""
    out, cur_val, cur_words, prev_val = [], 0, [], None

    def flush():
        if cur_words:
            out.append((" ".join(cur_words), cur_val))

    for surf, val, rank in run:
        if rank == "ord":
            flush()
            cur_val, cur_words, prev_val = 0, [], None
            out.append((surf, val))
            continue
        if rank == "mult":
            cur_val = (cur_val or 1) * val
            cur_words.append(surf)
            out.append((" ".join(cur_words), cur_val))
            cur_val, cur_words, prev_val = 0, [], None
            continue
        if prev_val is not None and val >= prev_val:
            flush()
            cur_val, cur_words = 0, []
        cur_val += val
        cur_words.append(surf)
        prev_val = val
    flush()
    return out


def extract_word_numbers_seq(text):
    """Числительные ПРОПИСЬЮ → [(фраза, значение)]. Идиомы белого списка
    маскируются ДО разбора, поэтому «в первую очередь» числом не считается.
    Соседство слов учитывается: последовательность числительных, разделённых
    только пробелами, считается ОДНИМ числом («двадцать пять» = 25, не 20 и 5);
    любое другое слово между ними разрывает последовательность."""
    masked = _NUMERAL_IDIOM_RE.sub(lambda m: " " * len(m.group(0)), text)
    out = []
    run = []
    for tok in re.finditer(r"[А-Яа-яЁёA-Za-z0-9]+|\S", masked):
        w = tok.group(0)
        hit = RU_NUMERAL_WORDS.get(w.lower())
        if hit:
            run.append((w, hit[0], hit[1]))
        elif re.fullmatch(r"[А-Яа-яЁёA-Za-z0-9]+", w):
            out.extend(_combine_numeral_run(run))
            run = []
    out.extend(_combine_numeral_run(run))
    return out


def check_word_numerals(text_plain, fb_plain, fb_nums):
    """WARN-слой AC5б: значения числительных ПРОПИСЬЮ сверяются с той же
    факт-базой. Резолвится, если значение есть в базе цифрами (fb_nums) или
    прописью. Возвращает список (фраза, значение) БЕЗ покрытия."""
    fb_word_vals = {v for _, v in extract_word_numbers_seq(fb_plain)}
    missing, seen = [], set()
    for phrase, val in extract_word_numbers_seq(text_plain):
        if val in fb_word_vals or str(val) in fb_nums:
            continue
        key = (phrase.lower(), val)
        if key in seen:
            continue
        seen.add(key)
        missing.append((phrase, val))
    return missing


def factbase_body_len(factbase_text):
    """AC5 входной гейт объёма (02b-research-summary.md): длина факт-базы БЕЗ
    служебных markdown-заголовков. Метод очистки ровно тот, что описан в 02b -
    выбрасываются строки, начинающиеся с `#` (любой уровень). Возвращает знаки."""
    body = [ln for ln in factbase_text.splitlines() if not ln.lstrip().startswith("#")]
    return len("\n".join(body))


def load_factbase(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def check_factbase(text, factbase_text):
    """AC5. Входной гейт контекста КАК КОД. (а) объём факт-базы против объёма
    поста - СПРАВКА (Д18: HARD снят, см. main()); (б) каждое число поста есть
    в факт-базе; (в) каждое имя собственное поста есть в факт-базе. Провал
    (б)/(в) = HARD FAIL «выдуманный факт» (закрывает класс R2-4 кодом).
    Числа внутри адресов в (б) не участвуют (Д18, К4)."""
    text_plain = _strip_md_plain(text)
    fb_plain = _strip_md_plain(factbase_text)
    # 🔴 Д18 (по решению автора), К4. ЧИСЛА ВНУТРИ АДРЕСА - НЕ УТВЕРЖДЕНИЕ ПОСТА.
    # Закон 32 требует дверь, UTM-гейт требует у двери utm_source/utm_content,
    # а AC5б считал `id` и цифры домена/метки выдуманными числами: два правила
    # системы сталкивались на КАЖДОМ посте с дверью («выдуманные числа: 20260806,
    # 3311129»). Адрес - это адрес, факт-базой он не заверяется.
    _URL_RE = re.compile(r"https?://\S+|(?<![\w@])[\w.-]+\.[a-z]{2,}/\S*", re.I)
    text_nums_src = _URL_RE.sub(" ", text_plain)
    result = {
        "volume_ok": len(factbase_text) >= len(text),
        "fb_len": len(factbase_text), "post_len": len(text),
        "missing_numbers": [], "missing_names": [], "missing_word_numbers": [],
    }

    # --- (б) ЧИСЛА. 🔴 ФИКС ложного FAIL (скептик-раунд 2, по решению автора).
    # БЫЛО: `\d[\d\s.,]*\d` жевало «по решению автора» в ОДИН токен «20072026». Пост, который
    # честно пишет «в 2026 году» при факт-базе с датой «по решению автора», получал HARD
    # «выдуманное число 2026» - при том что число из базы и взято.
    # СТАЛО: у каждого найденного числа считаем ДВЕ формы - склеенную (как раньше) и
    # разбор на отдельные последовательности `\d+`; факт-база раскрывается в обе,
    # пост сверяется склеенной формой, а если её нет - по всем своим под-токенам.
    # Обратная совместимость сохранена в обе стороны: пост «1 500» при базе «1500»
    # проходит по склейке, пост «2026» при базе «по решению автора» - по под-токену.
    def _num_forms(raw):
        """Сырое число из текста → (склеенная форма, [под-токены \\d+])."""
        return re.sub(r"[\s.,]", "", raw), re.findall(r"\d+", raw)

    def extract_numbers(t):
        out = []
        for ln in t.splitlines():
            ln2 = re.sub(r"^\s*\d+[.)]\s+", "", ln)  # снять маркер нумерации списка
            for m in re.finditer(r"\d[\d\s.,]*\d|\d", ln2):
                out.append(_num_forms(m.group(0)))
        return out

    fb_nums = set()
    for glued, parts in extract_numbers(fb_plain):
        fb_nums.add(glued)
        for p in parts:
            fb_nums.add(p)
            if p.lstrip("0"):
                fb_nums.add(p.lstrip("0"))   # «05» из даты покрывает «5» в посте
    seen_nums = set()
    for glued, parts in extract_numbers(text_nums_src):
        if not glued or glued in seen_nums:
            continue
        seen_nums.add(glued)
        if glued in fb_nums:
            continue
        if parts and all(p in fb_nums for p in parts):
            continue   # число записано в базе по частям (или наоборот)
        result["missing_numbers"].append(glued)
    result["missing_numbers"].sort()

    # --- (в) ИМЕНА СОБСТВЕННЫЕ. 🔴 ФИКС ложного FAIL (скептик-раунд 2, по решению автора).
    # БЫЛО: точное сравнение множеств слов с заглавной. Пост живой и склоняет: «отдал
    # Артёма Вике» при факт-базе «Артём», «Вика» → HARD «висящие имена: Артёма, Вике»,
    # хотя оба имени взяты из базы. СТАЛО: обе стороны нормализуются лёгким стеммингом
    # русских падежных окончаний, сравниваются ОСНОВЫ.
    # Пороговая деталь: спека просила резать «до основы ≥4 символов», но на живом
    # обязательном кейсе «Вики»/«Вика» (обе формы 4 знака) порог 4 запрещает срез вообще
    # и кейс проваливается - проверено прогоном. Поэтому пол основы = 3 знака, а срез
    # разрешён только словам от 4 знаков и не более двух проходов: этого хватает на
    # «Артёма→артем→арте» = «Артём→артем→арте» и на «Вики→вик» = «Вика→вик», и мало
    # для схлопывания разных имён (Марк/Марина/Донор-А остаются различимыми).
    # Полностью отсутствующее в базе имя по-прежнему даёт HARD FAIL.
    fb_stems = {_stem_ru(x) for x in re.findall(r"[А-ЯЁ][а-яё]{2,}", fb_plain)}
    common_stems = {_stem_ru(w) for w in FACTBASE_COMMON_WORDS}
    for nm in sorted(_extract_proper_names(text_plain)):
        st = _stem_ru(nm)
        if st in fb_stems or st in common_stems:
            continue
        result["missing_names"].append(nm)

    # --- (г) ЧИСЛИТЕЛЬНЫЕ ПРОПИСЬЮ (волна 16, по решению автора). WARN, не HARD.
    # Та же subset-сверка, что у цифр: значение слова-числительного обязано
    # найтись в факт-базе - цифрами или тоже прописью. Факт-база нормализуется
    # ТЕМ ЖЕ кодом, поэтому «50-100» в источнике покрывает «от пятидесяти до ста».
    result["missing_word_numbers"] = check_word_numerals(text_plain, fb_plain, fb_nums)
    return result


# --- AC/класс R2-10 (UTM/PS-ACTION/поддержка по --channel).
def check_utm(text, channel):
    """Класс R2-10. HARD если есть ссылка БЕЗ utm_source/utm_content.
    Исключения: (1) t.me-ссылки в бот-канале (--channel bot) - там вход
    идёт код-словом/start=, не UTM-меткой; (2) t.me/+хэш (ПРИВАТНАЯ
    invite-ссылка Telegram-группы/канала) - Telegram не поддерживает
    query-параметры на invite-ссылках физически, UTM на них technically
    невозможен (admission-фикс, прецедент green-фикстуры: посты владельца с
    приватной ссылкой на закрытый канал приёма)."""
    urls, _ = check_links(text)
    bad = []
    for u in urls:
        # Закон 29/32 (владелец 5.08) + канон 1.3-UTM: t.me не пробрасывает
        # query-метки НИГДЕ - сегментация там через start-код. UTM-чек
        # применим только к http-лендингам вне Telegram.
        if "t.me/" in u:
            continue
        if "utm_source" not in u and "utm_content" not in u:
            bad.append(u)
    return bad


def check_bot_support_link(text, channel):
    """Класс R2-10 п.13. WARN. Ссылка поддержки в каждом сообщении
    бот-цепочки (--channel bot)."""
    if channel != "bot":
        return None
    return bool(re.search(r"поддержк|support|помощь\s+тут|вопрос\w*\s+сюда", text, re.IGNORECASE))


def check_ps_action(text, channel):
    """Класс R2-10 п.3. 🔒 ИЗОЛИРОВАНО от учеников (тот же паттерн, что и
    P.S.-Action блок в post-phase-gate.sh): читает ТОЛЬКО если существует
    личный канон-файл владельца. На машине ученика файла нет → 'NA', проверка
    молча пропускается (закон изоляции CLAUDE.md work). Приписка не
    ставится в бот-дуге (канон)."""
    import glob, os
    # 4c: приписка канонна не во всех каналах. Бот-дуга её не ставит (было),
    # письмо тоже - у него своя подпись и свой футер (green-ivan/e17-0508.txt
    # заканчивается «P.S. Пишу тебе сегодня…» + «владелец», приписки-fallback нет,
    # и это одобренная единица). Проверка применяется к публичным TG-каналам и
    # информерам, где дверь = лендинг и запасной вход реально нужен.
    if channel in ("bot", "email"):
        return "NA_BOT" if channel == "bot" else "NA_EMAIL"
    candidates = (glob.glob(os.path.expanduser(".business/запуски/*/PS-ACTION-канон.md"))
                  + glob.glob(os.path.expanduser("~/.business/запуски/*/PS-ACTION-канон.md")))
    if not candidates:
        return "NA_NOCANON"
    canon = open(candidates[0], encoding="utf-8").read().lower()
    # 🔴 ЕДИНЫЙ РАЗБОР КАНОН-ФАЙЛА С ХУКОМ (скептик-раунд 4, по решению автора, ВАЖНО 7).
    # БЫЛО: линтер знал только бот-маркеры (start=…, …_bot), а post-phase-gate.sh знал
    # ЕЩЁ И домены-лендинги запуска. Пост с основной дверью на лендинг
    # (вида your-landing.example/offer/) и без бот-кода линтер считал «не запуском» и печатал
    # «не применяется» - INFO врал, а проверка приписки не работала там, где нужнее всего.
    # СТАЛО: тот же разбор, что в хуке (боты + домены), в одном месте.
    markers = set(re.findall(r"start=[a-z0-9_]+", canon)) | set(re.findall(r"[a-z0-9_]+_bot", canon))
    for dom in re.findall(r"[a-z0-9-]+\.[a-z]{2,6}/[a-z0-9_-]+/?", canon):
        dom = dom.split("?")[0].rstrip("/")
        if len(dom) > 8 and "t.me" not in dom:
            markers.add(dom)
    tl = text.lower()
    if not any(m for m in markers if m and m in tl):
        return "NA_NOTLAUNCH"
    has_fallback = ("войти можно здесь" in tl) or ("без впн" in tl and "здесь" in tl)
    return "OK" if has_fallback else "MISSING"


# §6.3 упомянут для справки. Сами слова = личная лексика владельца, живут во внешнем
# словаре (`banned_words`); отдельный HARD выше их уже считает, здесь не дублируем.
BANNED_WORDS_5_0 = [p for _id in ("marathon",) for p in owner_banned_patterns(_id)]


# --- класс R2-8, подтипы 1+2+3 (журнал .used-anchors.jsonl).
def load_used_anchors(path):
    import json, os
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def append_used_anchor(path, entry):
    import json, datetime
    entry = dict(entry)
    entry.setdefault("date", datetime.date.today().isoformat())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def compute_headline_form(paragraphs):
    """Отпечаток ФОРМЫ заголовка (класс R2-8 подтип 3: «18/20 по одной
    формуле, одинаковый 📍»). Не текст, а форма.

    🔴 Фикс раунда 9 (по решению автора, ДЕФЕКТ 1): старый отпечаток был
    `первое_слово|N_слов|shape`. Первое слово ПОСЛЕ эмодзи почти всегда -
    варьирующийся слот НАЗВАНИЯ (продукта/скилла/героя), а не часть формы:
    «📍 **ChatGrid ускоряет план**» и «📍 **NeuroBoost ускоряет план**» - это
    ОДНА и та же форма («18/20 по одной формуле» кейс владельца), но со старым
    отпечатком first_word различался (chatgrid≠neuroboost) и повтор формы
    не ловился НИКОГДА для этого класса дублей - именно то, что было
    заявлено как поймано, но не проверялось.

    Новый отпечаток - ЧИСТО СТРУКТУРНЫЙ, без единого слова текста:
      EMOJI  - есть ли ведущий эмодзи перед заголовком (0/1)
      CAPS   - доля капса словами: none (нет капс-слов) / word (часть слов
               капсом) / all (все слова с буквами - капсом)
      WORDS  - число слов бакетом: 2-4 / 5-7 / 8+
      PLUS   - есть ли символ «+» в заголовке (0/1)
      COLON  - есть ли двоеточие в заголовке (0/1)
      BOLD   - весь видимый текст заголовка (после эмодзи) обёрнут в
               **жирный**/__жирный__ целиком (0/1)

    Проверено (раунд 9): «📍 **ChatGrid ускоряет план**» и «📍 **NeuroBoost
    ускоряет план**» → ОДИН отпечаток (EMOJI:1|CAPS:none|WORDS:2-4|PLUS:0|
    COLON:0|BOLD:1). «📍 УНИКАЛИЗАТОР РОЛИКОВ + ВЫХОД ИЗ БАНА» (капс, «+»,
    без жирного) даёт EMOJI:1|CAPS:all|WORDS:5-7|PLUS:1|COLON:0|BOLD:0 -
    отличается от «📍 **Собрал воронку за вечер**» (обычный регистр,
    глагольный, жирный целиком) EMOJI:1|CAPS:none|WORDS:2-4|PLUS:0|COLON:0|
    BOLD:1.

    🔴 Мягкая миграция журнала .used-anchors.jsonl: формат записи меняется,
    старые записи (первое_слово|Nw|shape) читаются load_used_anchors() как
    обычный JSON (headline_form - просто строка, парсер её не разбирает) -
    падать негде. При сравнении в check_anchor_dup строка старого формата
    физически не совпадёт со строкой нового формата (разные алфавиты токенов:
    "тест|3w|" vs "EMOJI:0|CAPS:..."), то есть несовпадение формата
    молча считается НЕ-совпадением, а не ложным дублем - ровно то, что
    требовалось. Гейт повтора формы остаётся WARN, как был."""
    if not paragraphs:
        return ""
    raw = paragraphs[0].strip()
    # Ведущий эмодзи/иконка - любой символ(ы) до первой буквы/цифры/* /_ /пробела.
    emoji_match = re.match(r"^([^\wа-яёА-ЯЁ*_\s]+)", raw)
    has_emoji = bool(emoji_match)
    after_emoji = raw[emoji_match.end():].strip() if emoji_match else raw
    # Жирный ЦЕЛИКОМ: весь остаток (без эмодзи) обёрнут в ** или __.
    fully_bold = bool(re.match(r"^\*\*.*\*\*$", after_emoji) or re.match(r"^__.*__$", after_emoji))
    head = re.sub(r"\*\*|__", "", after_emoji).strip()
    words = [w for w in re.split(r"\s+", head) if w]
    n_words = len(words)
    if n_words <= 4:
        words_bucket = "2-4"
    elif n_words <= 7:
        words_bucket = "5-7"
    else:
        words_bucket = "8+"

    def _is_allcaps(w):
        letters = [c for c in w if c.isalpha()]
        return len(letters) >= 2 and w == w.upper()

    alpha_words = [w for w in words if any(c.isalpha() for c in w)]
    cap_words = [w for w in alpha_words if _is_allcaps(w)]
    if not cap_words:
        caps = "none"
    elif len(cap_words) == len(alpha_words):
        caps = "all"
    else:
        caps = "word"
    has_plus = "+" in head
    has_colon = ":" in head
    return (f"EMOJI:{int(has_emoji)}|CAPS:{caps}|WORDS:{words_bucket}"
            f"|PLUS:{int(has_plus)}|COLON:{int(has_colon)}|BOLD:{int(fully_bold)}")


def check_anchor_dup(anchor, hero, headline_form, channel, entries, window_days=7,
                     exclude_slug=None):
    """Класс R2-8, подтипы 1+2+3. Дубль истории-якоря КРОСС-канально за 7
    дней; дубль скилла-героя КРОСС-канально за 7 дней; повтор формы
    заголовка В ПРЕДЕЛАХ канала за то же окно (закон-якорь №8: герой не
    повторяется два дня ни в каком канале).

    🔴 exclude_slug (фикс скептик-раунда 3, БЛОКЕР 2, по решению автора): записи журнала
    С ТЕМ ЖЕ слагом, что логируется сейчас, из сравнения ИСКЛЮЧАЮТСЯ. Иначе
    проверка ловит сама себя: повторный прогон линтера по ТОМУ ЖЕ посту (а он
    штатный - 04-review гоняет линтер, 05-publish гоняет его же с --log-anchor)
    находит собственную предыдущую запись и печатает «дубль якоря» на пустом
    месте. Дубль - это ДРУГОЙ пост с тем же якорем, а не тот же пост дважды."""
    import datetime
    hits = {"anchor": [], "hero": [], "headline_form": []}
    today = datetime.date.today()
    for e in entries:
        if exclude_slug and e.get("slug") == exclude_slug:
            continue
        try:
            d = datetime.date.fromisoformat(e.get("date", ""))
        except ValueError:
            continue
        if (today - d).days > window_days:
            continue
        if anchor and e.get("anchor") == anchor:
            hits["anchor"].append(e)
        if hero and e.get("hero") == hero:
            hits["hero"].append(e)
        if headline_form and e.get("headline_form") == headline_form and e.get("channel") == channel:
            hits["headline_form"].append(e)
    return hits


def _package_post_body(text):
    """Тело поста из карточки пакета. Файлы пакета дня - это КАРТОЧКИ: сверху
    служебная шапка (Порядок / Слот-время / Канал / Картинка / Статус / вывод
    линта), а сам пост лежит внутри ```-блока. Без этой распаковки все оси
    пакета (заголовок, ФОРМА заголовка, скелет) считались по служебной шапке:
    у 135 из 139 боевых карточек первый абзац - «Порядок: N…», отпечаток формы
    у всех одинаковый, и ось формы заголовка физически меряла метаданные, а не
    заголовки. Улика Д10 (по решению автора): по сырым файлам _pakety-0608 уникальных
    форм 2 на 21 единицу, по телам постов - 6.

    Правило: ровно один ```-блок → берём его; ноль или несколько (пост уже
    голым текстом, либо карточка нестандартная) → текст как есть."""
    blocks = re.findall(r"^```[^\n]*\n(.*?)^```", text, re.S | re.M)
    return blocks[0] if len(blocks) == 1 else text


# --- AC/класс R2-8 (кросс-постовые дубли внутри пакета, --package DIR).
def check_package_duplicates(this_text, package_dir, this_anchor=None, anchor_entries=None,
                             this_hero=None, allow_skeleton_repeat=None):
    """Сравнивает текущий пост с другими .md/.txt файлами каталога пакета
    (напр. серия информеров/каскад одного дня) по ТРЁМ осям (п.7 скептик-раунда 3,
    по решению автора - одного идентичного заголовка мало, серия уезжает в шаблон и при
    разных заголовках):

      1. заголовок идентичен (как было);
      2. ФОРМА заголовка совпадает (compute_headline_form: структурный отпечаток БЕЗ
         слов - эмодзи/капс/бакет числа слов/«+»/двоеточие/жирный-целиком, раунд 9
         ДЕФЕКТ 1) - «18/20 по одной формуле» класса R2-8;
      3. СКЕЛЕТ поста идентичен или совпадает зачином 3+ блоков (extract_skeleton +
         skeleton_conflict - те же функции, что у журнала скелетов, чтобы серия
         мерилась ровно тем же аршином, что и лента канала);
      4. якорь совпадает - если он доступен: `this_anchor` (флаг --anchor) против
         записи журнала якорей, чей `slug` равен имени файла пакета без расширения
         (единственный машинный способ связать файл пакета с его якорем; нет записи -
         ось молча пропускается, выдумывать связь запрещено);
      5. ГЕРОЙ совпадает (волна 15) - `this_hero` (флаг --hero) против записи журнала
         якорей по тому же slug=имя файла.

    ВОЛНА 15, статусы. Судья бенчмарка поймал «скелет-однообразие внутри волны»
    как системный дефект класса 8.2 - серия из 6 постов шла одним каркасом, а
    WARN никто не читал. Поэтому две оси подняты до FAIL:
      - СКЕЛЕТ совпадает с другим постом пакета -> FAIL (понижается до WARN
        флагом --allow-skeleton-repeat с причиной, ровно как у журнала канала);
      - ГЕРОЙ совпадает внутри пакета -> FAIL (закон-якорь №8: герой не
        повторяется; внутри одной волны - тем более).
    Заголовок/форма заголовка/якорь остаются WARN (серия может осознанно
    наследовать форму заголовка, решает автор).

    🔴 ЧЕСТНАЯ ГРАНИЦА. Требование судьи звучало «одинаковый скелет у двух постов
    ОДНОГО класса», но класс чужого файла пакета машине неизвестен: --form-class
    описывает ТЕКУЩИЙ пост, сайдкара с классом у файлов пакета нет, а угадывать
    класс по имени файла - выдумка. Поэтому гейт класс-агностичен: одинаковый
    каркас у двух постов пакета ловится независимо от класса. Это строже
    формулировки и не мягче её; ложное срабатывание снимается тем же
    --allow-skeleton-repeat с печатью причины.

    Возвращает список (path, why, severity), severity in {"WARN", "FAIL"}."""
    import os, glob
    hits = []
    this_text = _package_post_body(this_text)
    this_paras = split_paragraphs(this_text)
    this_head = this_paras[0] if this_paras else ""
    this_norm = re.sub(r"[^\wа-яё]", "", this_head.lower())
    this_form = compute_headline_form(this_paras)
    this_skel = extract_skeleton(this_text)
    skel_conflicts = 0     # Д18, К5: доля пакета, делящая каркас с этой единицей
    skel_total = 1
    form_counts = {this_form: 1} if this_form else {}
    by_slug = {}
    for e in (anchor_entries or []):
        if e.get("slug"):
            by_slug[e["slug"]] = e
    if not this_norm:
        return hits
    for fp in glob.glob(os.path.join(package_dir, "*.md")) + glob.glob(os.path.join(package_dir, "*.txt")):
        try:
            other = open(fp, encoding="utf-8").read()
        except OSError:
            continue
        other = _package_post_body(other)
        if other.strip() == this_text.strip():
            continue
        op = split_paragraphs(other)
        if not op:
            continue
        skel_total += 1
        other_norm = re.sub(r"[^\wа-яё]", "", op[0].lower())
        other_form = compute_headline_form(op)
        if other_form:
            form_counts[other_form] = form_counts.get(other_form, 0) + 1
        if this_norm == other_norm:
            hits.append((fp, "заголовок идентичен", "WARN"))
        elif this_form and other_form == this_form:
            hits.append((fp, f"форма заголовка совпадает: {this_form}", "WARN"))
        # 4c/C4 (канон п.39): шаблон «НАЗВАНИЕ КАПСОМ - расшифровка» в >=2
        # постах серии = FAIL. Один КАПС-заголовок в дне канон п.38 разрешает
        # («CAPS максимум у одного поста в дне»), поэтому ось живёт ТОЛЬКО
        # внутри пакета и молчит на одиночном прогоне.
        this_caps = caps_headline_template(this_head)
        other_caps = caps_headline_template(op[0])
        if this_caps and other_caps:
            hits.append((fp, f"шаблон заголовка «КАПС - расшифровка» повторяется серией: "
                             f"«{this_caps}» и «{other_caps}» (канон п.39)", "FAIL"))
        # 🔴 Д18 (по решению автора), К5. РАЗРЕШЕНИЕ ПОДПИСИ.
        # `extract_skeleton` схлопывает соседние одинаковые блоки, поэтому у
        # обычного повествовательного поста подпись вырождается в ОДИН символ
        # `P` («сплошная проза»), а у поста с жирным заголовком - в `HB→P`.
        # `skeleton_conflict` при этом отдаёт «идентичен» на любом равенстве, в
        # т.ч. `P` == `P`. Замер боевого корпуса `_pakety-*` до фикса: 182 пары
        # «идентичен» из 358, и почти все - вырожденные `P`/`HB→P`; в принятом
        # владельцем пакете Д18 так помечены 16 единиц из 21. Это не «один каркас на
        # серию», это «пост написан абзацами».
        # Ось судит ТОЛЬКО подписи с реальным разрешением: >= 3 блока у обеих
        # сторон - ровно тот же барьер, на котором стоит ветка «общий зачин 3+».
        other_skel = extract_skeleton(other)
        SKEL_MIN_RESOLUTION = 3
        verdict = (skeleton_conflict(this_skel, other_skel)
                   if (len(this_skel) >= SKEL_MIN_RESOLUTION
                       and len(other_skel) >= SKEL_MIN_RESOLUTION) else None)
        if verdict:
            # 🔴 Д18, К5: ОДНА пара больше не валит пакет. Алфавит блоков всего
            # пять букв (P/HB/CTA/IT/NUMLIST), поэтому «общий зачин 3 блоков» =
            # «пост начинается заголовком, текстом и призывом» и совпадает почти
            # у всех. FAIL считается ДОЛЕЙ, ниже по функции.
            skel_conflicts += 1
            why = f"скелет {verdict}: {'→'.join(other_skel)}"
            if allow_skeleton_repeat:
                why += f" (понижено: {allow_skeleton_repeat})"
            hits.append((fp, why, "WARN"))
        stem = os.path.splitext(os.path.basename(fp))[0]
        e = by_slug.get(stem)
        if this_anchor and e and e.get("anchor") and e["anchor"] == this_anchor:
            hits.append((fp, f"якорь совпадает: «{this_anchor}» (журнал якорей, slug={stem})", "WARN"))
        if this_hero and e and e.get("hero") and e["hero"] == this_hero:
            hits.append((fp, f"герой совпадает: «{this_hero}» (журнал якорей, slug={stem}; "
                             f"класс 8.2 - один скилл-герой на волну)", "FAIL"))

    # 🔴 Д10 (по решению автора), граница канона п.38 «повтор формы = FAIL».
    # БЫЛО: любой повтор формы = WARN (канон 6.08 поднял класс до FAIL, код
    # держал WARN - противоречие №9). Но и буквальный FAIL на ЛЮБОЙ повтор
    # физически непроходим: канон п.70 требует полную матрицу 8 каналов, это
    # 17-21 единица в дне, а живых форм заголовка канон п.38 перечисляет пять.
    # По принципу Дирихле повтор в таком пакете неизбежен, и пакет дня не
    # прошёл бы НИКОГДА.
    # СТАЛО: FAIL меряется ДОЛЕЙ одной формы в пакете. Замер боевых пакетов по
    # телам постов: принятые владельцем Д17/Д18 (_pakety-0508 / _pakety-0608) дают
    # 40% и 48% при 4 и 6 уникальных формах; серийный штамп - 100% (пара
    # одинаковых) и 67-70% на поздних машинных пакетах. Прецедент канона п.38 -
    # «18 заголовков из 20 по одной формуле» = 90%. Порог 50% пропускает
    # принятые пакеты и валит штамп.
    # 🔴 Д18 (по решению автора), К5. КАРКАС СЕРИИ = ДОЛЯ, А НЕ ОДНА ПАРА.
    # Замер по 10 боевым пакетам `_pakety-*` (доля пакета, делящая каркас с
    # самой «типовой» единицей, только подписи с разрешением >= 3 блока):
    #   принятые владельцем  Д18 10% · Д17 50%
    #   поздние машинные 0708 47% · 0808 26% · 0908 58% · 1108 80% · 1408 58%
    # Требование судьи волны 15 звучало «серия из 6 постов одним каркасом» =
    # 100%. Порог 60% пропускает оба принятых пакета и валит машинный штамп;
    # ниже порога совпадение остаётся WARN и печатается пофайлово.
    SKEL_SHARE_FAIL = 0.6
    SKEL_MIN_UNITS  = 3
    if (len(this_skel) >= 3 and skel_total >= SKEL_MIN_UNITS and not allow_skeleton_repeat
            and (skel_conflicts + 1) / skel_total > SKEL_SHARE_FAIL):
        hits.append((package_dir,
                     f"один каркас на серию: {skel_conflicts + 1} из {skel_total} единиц пакета "
                     f"({(skel_conflicts + 1) / skel_total:.0%} > {SKEL_SHARE_FAIL:.0%}) идут скелетом "
                     f"{'→'.join(this_skel)} (волна 15, класс 8.2)", "FAIL"))

    total_forms = sum(form_counts.values())
    same_form = form_counts.get(this_form, 0)
    if this_form and total_forms >= 2 and same_form >= 2 and same_form / total_forms > 0.5:
        hits.append((package_dir,
                     f"форма заголовка занимает {same_form} из {total_forms} единиц пакета "
                     f"({same_form / total_forms:.0%} > 50%) - канон п.38, владелец: «хватит "
                     f"заголовки везде капсом писать и один смайлик ставить». Форма: "
                     f"{this_form}", "FAIL"))
    return hits


# ===========================================================================
# СЦЕНА (workflow/02b1-scene-mining.md) - КОД-ГЕЙТ ДОБЫЧИ СЦЕНЫ.
#
# ЗАЧЕМ. Фаза 02b1 добывает под КАЖДУЮ единицу конкретный эпизод («кто, когда,
# что сделал, какое число, что сломалось, что появилось») и пишет его в
# `.post-state-<слаг>.json` корневым ключом `scene` вместе с `scene_mined_at`.
# До этого гейта фаза держалась дисциплиной агента: карточку можно было не
# добывать, а сочинить - и текст добирал объём обобщениями («люди», «обычно»,
# «многие»), ровно тот разрыв, который замерен в 02b1 (у эталонов автора 11-21
# числа в теле, у боевых единиц 0-2).
#
# ЧТО ПРОВЕРЯЕМ (контракт 02b1, раздел «Контракт для кода-гейта»), ровно 4:
#   П1. ключ `scene` есть, семь полей заполнены (кроме `broke`), и файл улики
#       `scene.evidence.file` существует на диске;
#   П2. строка `scene.evidence.line` этого файла непустая И содержит
#       `scene.evidence.quote` - это и есть анти-выдумка: сцену без реального
#       происхождения так не подделать (аналог `sed -n '<line>p' <file>` из Г2);
#   П3. `scene_mined_at` < `draft_at` - сцена добыта ДО текста, а не подобрана
#       под уже написанный (тот же принцип, что у `factbase_created_at`);
#   П4. в каталоге пакета `scene.id` не повторяется, и НАЗВАННЫЙ герой в поле
#       `who` не повторяется (закон «один герой = один раз за пакет», Г3).
# Провал любого = FAIL. Печать - строками `[FAIL] сцена/ПN: ...`.
#
# 🔴 ПОЧЕМУ `who` СУДИТСЯ НЕ ТАК ЖЁСТКО, КАК `id` (решение по данным боевого
# корпуса). Пакет дня несёт 9-22 единицы (замер `_pakety-0508…1408`: 10, 22,
# 17, 19, 19, 9, 10, 11, 11, 12). По определению 02b1 поле `who` = «я» либо
# «Имя, роль», и у автора подавляющая часть сцен - его собственные, то есть
# `who` = «я». Требование «who уникален среди всех единиц пакета» дословно
# означало бы «в пакете из 22 единиц ровно ОДНА может быть про автора» - пакет
# становится физически несобираемым, а гейт - тем, что обходят. Поэтому:
#   · `scene.id` уникален СТРОГО (это и есть «одна сцена = одна единица»),
#     плюс отпечаток улики (файл+строка+цитата) - чтобы переименование `id`
#     при той же сцене не проходило;
#   · `who` уникален строго для НАЗВАННОГО героя (третье лицо с именем) - это
#     ровно закон «один герой = один раз за пакет», тот же, что журнал якорей
#     держит флагом `--hero`;
#   · `who` = автор («я» / «I» / «автор» / «me») из проверки исключён: автор
#     присутствует в каждой единице по построению, это не «повтор героя».
#
# АРХИВ. Ключа `scene` нет у постов, собранных ДО внедрения фазы. Гейт печатает
# `[N/A] (state старого формата)` и НЕ блокирует, если state не несёт ни одной
# отметки конвейера (чистая машинная расписка хука - именно так выглядят все
# боевые `.post-state-*.json` пакетов) ЛИБО пост собран раньше SCENE_GATE_EPOCH.
# «Когда собран» берётся первой доступной отметкой: draft_at -> factbase_created_at
# -> scene_mined_at -> mtime самого state (замер 193 боевых файлов: 49 архивных
# state полного конвейера несут слои, но draft_at в них нет вовсе - по одной
# отметке весь архив уехал бы в FAIL; после фикса 193/193 идут N/A).
# Всё, что несёт отметки конвейера и написано после эпохи, обязано нести сцену.
# ЧЕСТНАЯ ГРАНИЦА: state вообще без отметок конвейера гейт не судит - агент,
# который не напишет ни `draft_at`, ни `factbase_created_at`, останется в
# N/A-ветке. Это цена совместимости с архивом, а не невидимость: отметки
# требует Stop-гейт выдачи (post-phase-gate.sh, блок «порядок фаз»).
#
# владелец-специфики нет: ни путей, ни имён, ни запусков - только ключи state.
# ===========================================================================

SCENE_GATE_EPOCH = "2026-08-07T23:50:00"   # момент внедрения гейта; раньше = архив

SCENE_REQUIRED_FIELDS = ("id", "who", "when", "did", "number", "result", "status")
# `broke` в обязательные НЕ входит - 02b1: «все обязательны, кроме broke»

# отметки, по которым видно, что state прошёл конвейер post (а не является
# чистой машинной распиской скоупа B хука)
SCENE_PIPELINE_MARKS = ("scene_mined_at", "draft_at", "factbase_created_at",
                        "factbase_path", "L1", "L2_voice", "L3_mastery",
                        "L4_empirics", "L5_review", "dry_report", "final")

# `who`, который означает самого автора: в проверке уникальности не участвует
SCENE_SELF_WHO_RE = re.compile(r"^(я|i|автор|author|me|myself|сам)\b")

# цитата короче этого подделывается тривиально («и», «на») - улика обязана быть
# опознаваемым куском строки. 02b1 просит 5-15 слов; код держит нижний пол.
SCENE_QUOTE_MIN_CHARS = 10
SCENE_QUOTE_MIN_WORDS = 2

# ===========================================================================
# П5-П7: ТРИ ПОЛЯ КАРТОЧКИ ОТ по решению автора (pain / novice_retell / audience_level)
#
# ЗАЧЕМ. П1-П4 доказывают, что сцена РЕАЛЬНА (улика резолвится, порядок фаз
# соблюдён). Они ничего не говорят о том, ПОНЯТНА ли она читателю: эпизод
# бывает настоящим, лицо есть, число есть, улика резолвится - и всё равно
# читается только тем, кто знает устройство проекта автора («расписка не
# сошлась с гейтом, перегнал линт по корпусу»). Второй корень 02b1. Поля
# закрывают ровно его: `pain` - чью боль сцена доказывает (с уликой),
# `novice_retell` - тот же эпизод словами человека с улицы, `audience_level` -
# вердикт гейта понятности, который сверяется с каналом единицы.
#
# СЛОВАРЬ ТЕРМИНОВ НЕ ДУБЛИРУЕТСЯ В КОДЕ. Контракт 02b1 («Контракт для судьи»)
# требует читать его ОТТУДА одним источником: список живёт в двух местах того
# же файла - чёрный список п.8 и блок обязательного перевода S7-S8. Копия в
# коде рассинхронилась бы с каноном в первый же раунд правок и зеленела бы на
# словаре, которого в каноне уже нет.
#
# ФАЙЛ СЛОВАРЯ НЕДОСТУПЕН = HARD FAIL, НЕ МЯГКАЯ ДЕГРАДАЦИЯ. Тот же контракт,
# что у справочника приёмов доноров (Д105 в post-phase-gate.sh): 02b1 -
# обязательная часть самого механизма гейта и раздаётся ВМЕСТЕ со скиллом, а
# не персональный корпус ученика (контраст - etalons.json в bench-post.py, там
# отсутствие штатно). Судить чистоту пересказа без словаря = выдавать
# непроверенное за проверенное.
#
# АРХИВ. Полей нет у карточек, собранных ДО по решению автора - замер боевого корпуса
# (233 файла `.post-state-*.json` в запусках, из них 80 несут ключ `scene`)
# показал: все 80 датированы по решению автора и ни в одной из них нет ни одного из трёх
# полей. Поэтому карточка без ВСЕХ трёх полей и старше эпохи получает пометку
# N/A внутри PASS-строки и не блокируется. Пометка идёт именно в PASS-строку, а
# не отдельной `[N/A]`-строкой: хук читает `[N/A]` как вердикт ВСЕЙ единицы, и
# отдельная строка обнулила бы честный PASS по П1-П4.
# ЧАСТИЧНОЕ заполнение (одно-два поля из трёх) архивом НЕ считается - карточка
# уже нового формата, и добирается она целиком.
#
# владелец-специфики нет: ни путей запусков, ни имён, ни кодовых слов - только
# ключи state и разбор файла воркфлоу, который раздаётся вместе со скиллом.
# ===========================================================================

SCENE_FIELDS_EPOCH = "2026-08-09T00:00:00"   # день, когда фаза начала писать три поля
SCENE_NEW_FIELDS = ("pain", "novice_retell", "audience_level")
SCENE_AUDIENCE_LEVELS = ("novice", "practitioner")

# источник словаря терминов внутренней кухни (и заодно самого контракта П5-П7)
SCENE_MINING_DOC = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "workflow",
    "02b1-scene-mining.md"))

# два якоря перечня в 02b1. Первый - чёрный список п.8 (термины в «ёлочках»),
# второй - блок обязательного перевода S7-S8 (термины через запятую).
SCENE_KITCHEN_ANCHOR_BLACKLIST = "Маркеры провала прямо из слов владельца:"
SCENE_KITCHEN_ANCHOR_TRANSLATE = ("Термины-маркеры, при появлении которых перевод "
                                  "считается несостоявшимся:")
# ниже этого числа разобранный перечень считается битым (якорь на месте, а
# список выкосили правкой) - тот же страж, что «23 подписи» у Д103
SCENE_KITCHEN_MIN_TERMS = 6

# термины-ОПИСАНИЯ, а не литералы: регуляркой их не поймать, в словарь берём с
# честной пометкой, а не молча выбрасываем
SCENE_KITCHEN_META_MARK = "тех-имя"

# окончания русского словоизменения: ими достраивается любой термин словаря,
# чтобы «расписка» ловила «расписку», а «дека» - «деки». Порядок в регулярке -
# от длинных к коротким (иначе короткая альтернатива съест начало длинной).
SCENE_RU_ENDINGS = ("ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими",
                    "ов", "ев", "ей", "ем", "ём", "ом", "ой", "ах", "ях",
                    "ам", "ям", "ых", "их", "ый", "ий", "ая", "яя", "ое",
                    "ее", "ые", "ие", "ью", "ея", "ею", "еи",
                    "а", "я", "у", "ю", "ы", "и", "е", "о", "й", "ь")

# каналы из карты болей 02b1. practitioner разрешён РОВНО в одной строке карты -
# ММ (сообщество практиков); все остальные каналы массовые и берут только novice.
SCENE_MM_TOKENS = ("mm", "мм", "мастермайнд", "mastermind")
# префикс имени единицы -> канал. Тот же разбор, что в post-layer-checkpoint-gate.sh
# (`PREFIX_RE`/`DEFAULTS`), но ММ здесь СВОЙ канал, а не `star`: хук схлопывает
# mm→star ради длины и UTM, а карта болей 02b1 держит для ММ отдельную строку с
# единственным допуском practitioner - схлопни их тут, и гейт судил бы ММ как
# «старые каналы», то есть блокировал бы единственный законный practitioner.
SCENE_SLUG_PREFIX_RE = re.compile(r"^(star|zakr|inf|osn|mm|b|r|e)[-_. ]?\d",
                                  re.IGNORECASE)
SCENE_PREFIX_CHANNEL = {"osn": "osn", "zakr": "zakr", "inf": "info", "mm": "mm",
                        "star": "star", "e": "email", "b": "bot", "r": "bot"}
SCENE_KNOWN_CHANNELS = ("botreg", "bot", "email", "info", "inf", "osn", "zakr",
                        "star", "mm")

_scene_kitchen_cache = {}


def _scene_parse_iso(value):
    """ISO-время из state → datetime (naive, локальная зона) | None | "BAD"."""
    s = str(value or "").strip().replace("Z", "+00:00")
    if not s:
        return None
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return "BAD"
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _scene_norm(s):
    """Нормализация для сверки цитаты со строкой источника.

    Снимаем ровно то, что различает ОДИН И ТОТ ЖЕ текст в файле и в карточке:
    юникод-форму, markdown-разметку строки, типографские кавычки и тире, «ё/е»,
    регистр и кратность пробелов. НЕ снимаем ни букв, ни цифр, ни смысловой
    пунктуации - иначе цитата «56 постов» совпала бы со строкой про «5 постов».
    Сопоставление остаётся ТОЧНЫМ вхождением подстроки, без fuzzy-похожести."""
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)                 # html-обёртки
    s = s.replace("**", "").replace("__", "").replace("~~", "").replace("`", "")
    s = re.sub(r"(?<!\*)\*(?!\*)", "", s)          # одиночный курсивный *
    s = re.sub(r"^[\s>#|]+", " ", s)               # ведущие цитата/заголовок/таблица
    s = re.sub(r"^\s*[-+•]\s+", " ", s)            # маркер списка (не дефис внутри слова)
    s = re.sub(r"^\s*\d+[.)]\s+", " ", s)          # номер списка
    for ch in "«»“”„‟‹›‘’‚'\"":
        s = s.replace(ch, '"')
    s = re.sub(r"[—–‒−‐‑]", "-", s)
    s = s.replace("ё", "е").replace("Ё", "Е")
    s = re.sub(r"[­​‌‍﻿]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().casefold()


def _scene_reference_time(state, state_path):
    """«Когда этот пост собирали» - для развилки архив/новый.

    🔴 Замер боевого корпуса (193 файла `.post-state-*.json` в запусках) показал,
    что одной отметки `draft_at` для развилки НЕ хватает: 49 архивных state
    полного конвейера несут слои L1/L5_review/final, но `draft_at` в них нет
    вовсе (его начали писать позже) - по одной этой отметке весь архив уехал бы
    в FAIL. Поэтому берём первую доступную из трёх, в порядке надёжности:
    draft_at -> factbase_created_at -> mtime самого файла state."""
    for key in ("draft_at", "factbase_created_at", "scene_mined_at"):
        t = _scene_parse_iso(_scene_pick(state, key))
        if isinstance(t, datetime.datetime):
            return t, key
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(state_path)), "mtime файла state"
    except Exception:
        return None, None


def _scene_pick(state, key):
    """Ключ ищется в корне, потом в brief/outline/L4_empirics - боевые state
    пишут отметки в разных местах, гейт не имеет права падать из-за места."""
    if not isinstance(state, dict):
        return None
    if state.get(key) not in (None, "", [], {}):
        return state[key]
    for cname in ("brief", "outline", "L4_empirics", "L4_empirica"):
        cont = state.get(cname)
        if isinstance(cont, dict) and cont.get(key) not in (None, "", [], {}):
            return cont[key]
    return None


def _scene_resolve_path(raw, *bases):
    """Путь улики: ~, абсолютный, иначе - от каталога пакета / каталога state."""
    p = os.path.expanduser(str(raw or "").strip())
    if not p:
        return ""
    if os.path.isabs(p):
        return p
    for b in bases:
        if not b:
            continue
        cand = os.path.normpath(os.path.join(b, p))
        if os.path.exists(cand):
            return cand
    return os.path.normpath(os.path.join(bases[0] if bases and bases[0] else ".", p))


def _scene_fingerprint(scene):
    """Отпечаток сцены по её УЛИКЕ: переименование `id` при той же улике не
    должно проходить проверку уникальности пакета (иначе П4 снимается одной
    правкой строки)."""
    ev = scene.get("evidence") if isinstance(scene, dict) else None
    if not isinstance(ev, dict):
        return None
    f = str(ev.get("file") or "").strip()
    ln = str(ev.get("line") or "").strip()
    q = _scene_norm(ev.get("quote"))
    if not (f and ln and q):
        return None
    return (os.path.basename(os.path.expanduser(f)).casefold(), ln, q)


def _scene_load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def _scene_kitchen_terms(doc_path=None):
    """Словарь терминов внутренней кухни ИЗ 02b1-scene-mining.md (один источник).

    Возвращает `(термины, мета, причина)`:
      · `термины` - список литералов для регулярки, `мета` - описания вроде
        «тех-имя скилла», которые регуляркой не ловятся и печатаются честной
        строкой, а не выбрасываются молча;
      · `термины is None` = словарь НЕДОСТУПЕН, `причина` объясняет почему.
        Вызывающая сторона обязана трактовать это как HARD FAIL, а не как
        «проверку тихо пропустили» (см. шапку блока П5-П7 выше: тот же
        контракт, что у Д105 со справочником приёмов).

    Перечень берётся из ДВУХ мест файла и объединяется: чёрный список п.8
    (термины в «ёлочках» после якоря) и блок обязательного перевода S7-S8
    (термины через запятую). Оба якоря обязаны найтись: пропал один - значит
    канон переписали, и словарь больше не тот, по которому судим."""
    path = doc_path or SCENE_MINING_DOC
    if path in _scene_kitchen_cache:
        return _scene_kitchen_cache[path]

    def _res(terms, meta, reason):
        _scene_kitchen_cache[path] = (terms, meta, reason)
        return terms, meta, reason

    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        return _res(None, [], "файл словаря «%s» не читается (%s)" % (path, e))

    raw = []
    # --- якорь 1: чёрный список п.8, термины в «ёлочках» до конца перечисления
    if SCENE_KITCHEN_ANCHOR_BLACKLIST not in src:
        return _res(None, [], "в «%s» нет якоря «%s» - чёрный список п.8 переписан "
                              "или удалён, судить чистоту пересказа нечем"
                              % (path, SCENE_KITCHEN_ANCHOR_BLACKLIST))
    seg = src.split(SCENE_KITCHEN_ANCHOR_BLACKLIST, 1)[1]
    seg = seg.split("\n", 1)[0]
    m_end = re.search(r"»\s*\.", seg)          # закрывающая ёлочка + точка = конец перечня
    if m_end:
        seg = seg[:m_end.end()]
    raw += re.findall(r"«([^«»]+)»", seg)

    # --- якорь 2: блок перевода S7-S8, термины через запятую
    if SCENE_KITCHEN_ANCHOR_TRANSLATE not in src:
        return _res(None, [], "в «%s» нет якоря «%s» - блок обязательного перевода "
                              "S7-S8 переписан или удалён, словарь неполон"
                              % (path, SCENE_KITCHEN_ANCHOR_TRANSLATE))
    seg2 = src.split(SCENE_KITCHEN_ANCHOR_TRANSLATE, 1)[1].split("\n", 1)[0]
    seg2 = seg2.strip().rstrip(".")
    raw += [t for t in seg2.split(",")]

    terms, meta, seen = [], [], set()
    for t in raw:
        t = t.strip().strip("«»\"'` ").strip()
        if not t:
            continue
        key = t.casefold().replace("ё", "е")
        if key in seen:
            continue
        seen.add(key)
        (meta if SCENE_KITCHEN_META_MARK in key else terms).append(t)

    if len(terms) < SCENE_KITCHEN_MIN_TERMS:
        return _res(None, meta, "в «%s» оба якоря на месте, но разобрано только %d "
                                "терминов при минимуме %d - перечень выкосили правкой "
                                "или сменили формат записи" % (path, len(terms),
                                                               SCENE_KITCHEN_MIN_TERMS))
    return _res(terms, meta, "")


def _scene_term_pattern(term):
    """Регулярка одного термина словаря: словоизменение + многословность.

    Каждое слово термина достраивается окончаниями `SCENE_RU_ENDINGS` и
    закрывается границей слова, поэтому «расписка» ловит «расписку/расписке», а
    «дека» - «деки/деками», но НЕ «декабрь» и НЕ «декорацию»: после базы «дек»
    остаток «абрь»/«орац» в окончания не входит, а пустое окончание упирается в
    отсутствие границы. Токен `NN` в термине («фаза NN») - место под число.
    Слова термина разделяются пробелом/дефисом (0-2 знака), чтобы «копи-блок»
    ловился и как «копи блок»."""
    endings = "|".join(sorted(SCENE_RU_ENDINGS, key=len, reverse=True))
    parts = []
    for w in re.split(r"[\s\-–—]+", term.strip()):
        w = w.strip().casefold().replace("ё", "е")
        if not w:
            continue
        if w == "nn" or w == "nn.":
            parts.append(r"\d{1,3}")
            continue
        base = w
        if len(w) > 3:
            for e in sorted(SCENE_RU_ENDINGS, key=len, reverse=True):
                if w.endswith(e) and len(w) - len(e) >= 3:
                    base = w[:-len(e)]
                    break
        parts.append(re.escape(base) + r"(?:" + endings + r")?")
    if not parts:
        return None
    body = r"[\s\-–—]{0,2}".join(parts)
    return re.compile(r"(?<![0-9a-zа-я])" + body + r"(?![0-9a-zа-я])",
                      re.IGNORECASE | re.UNICODE)


def _scene_kitchen_hits(text, terms):
    """Какие термины словаря реально встретились в тексте (список пар
    термин→найденный кусок). Пустой список = пересказ чист."""
    norm = str(text or "").replace("ё", "е").replace("Ё", "Е")
    hits = []
    for t in terms:
        rx = _scene_term_pattern(t)
        if rx is None:
            continue
        m = rx.search(norm)
        if m:
            hits.append((t, m.group(0)))
    return hits


def _scene_is_single_sentence(text):
    """Одно предложение или нет. Разрывом считается терминальный знак, за
    которым идёт пробел и заглавная буква - так «5.5 балла» и «т.е.» внутри
    предложения не считаются вторым, а «Сделал X. Потом Y» считается."""
    s = str(text or "").strip()
    s = re.sub(r"[.!?…]+$", "", s).strip()
    return re.search(r"[.!?…]+\s+[«\"(\[]?[А-ЯЁA-Z]", s) is None


def _scene_resolve_quote(block, pkg_dir, state_dir, field):
    """Резолв улики `{file, line, quote}` ТЕМ ЖЕ способом, что `scene.evidence`
    (02b1 Г4: «проверка та же, что у Г2»). Возвращает `(ok, сообщение)`."""
    if not isinstance(block, dict):
        return False, ("scene.%s не объект {quote, file, line} - улику боли "
                       "проверить нечем (02b1, Г4)" % field)
    f = str(block.get("file") or "").strip()
    q = str(block.get("quote") or "").strip()
    ln = block.get("line")
    if not f:
        return False, "scene.%s.file пуст - улики боли нет" % field
    if not q:
        return False, ("scene.%s.quote пуст - боль обязана стоять ДОСЛОВНОЙ "
                       "формулировкой из карты болей, а не пересказом" % field)
    try:
        ln = int(str(ln).strip())
    except Exception:
        return False, ("scene.%s.line не число - улика на файл БЕЗ номера строки "
                       "не принимается, она непроверяема (02b1, Г4)" % field)
    path = _scene_resolve_path(f, pkg_dir, state_dir, os.getcwd())
    if not os.path.isfile(path):
        return False, ("файла улики боли нет на диске - scene.%s.file «%s» "
                       "(искал «%s»)" % (field, f, path))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except Exception as e:
        return False, "файл улики боли «%s» не читается (%s)" % (path, e)
    if ln < 1 or ln > len(lines):
        return False, ("в файле «%s» строк %d, а карточка ссылается на строку %d - "
                       "`sed -n '%dp'` вернул бы пустоту" % (path, len(lines), ln, ln))
    src_line = lines[ln - 1]
    if not src_line.strip():
        return False, ("строка %d файла «%s» пустая - `sed -n '%dp'` вернул пустоту"
                       % (ln, path, ln))
    nq = _scene_norm(q)
    nw = len(re.findall(r"\w+", nq, re.UNICODE))
    if len(nq) < SCENE_QUOTE_MIN_CHARS or nw < SCENE_QUOTE_MIN_WORDS:
        return False, ("цитата боли «%s» короче порога (%d знаков / %d слов при "
                       "минимуме %d/%d) - такой обрывок совпадает с чем угодно"
                       % (q, len(nq), nw, SCENE_QUOTE_MIN_CHARS, SCENE_QUOTE_MIN_WORDS))
    if nq not in _scene_norm(src_line):
        return False, ("строка %d файла «%s» НЕ содержит цитату боли. В файле: «%s». "
                       "В карточке: «%s». Боль, сформулированная своими словами или "
                       "абстракцией («страх технологий»), не принимается - гейту "
                       "нечего проверять (02b1, Г4)"
                       % (ln, path, src_line.strip()[:160], q[:160]))
    return True, "боль резолвится: %s:%d" % (path, ln)


def _scene_channel(state_path, state):
    """Канал единицы для сверки с картой болей 02b1: `(канал, откуда)`.

    Порядок ровно тот, что назван контрактом: канал берётся ИЗ ИМЕНИ единицы
    (в `brief.channel` его нет - замер 233 боевых state дал 0 совпадений),
    тем же префиксом, каким его берёт `post-layer-checkpoint-gate.sh`. Дальше -
    имя файла поста из state и корневой ключ `channel`, если он там есть
    (33 state из 233 его несут, в том числе прозой вроде «МАСТЕРМАЙНД (ММ) …»).
    Ничего не опознали - возвращаем пустую строку: это НЕ разрешение, а незнание,
    и `practitioner` на незнании не проходит (см. П7)."""
    base = os.path.basename(str(state_path or ""))
    slug = base
    if slug.startswith(".post-state-"):
        slug = slug[len(".post-state-"):]
    slug = re.sub(r"\.json$", "", slug, flags=re.I)
    m = SCENE_SLUG_PREFIX_RE.match(slug)
    if m:
        pref = m.group(1).lower()
        return SCENE_PREFIX_CHANNEL.get(pref, pref), "префикс имени state «%s»" % slug

    for key in ("post_file", "slug", "file_slug"):
        v = os.path.basename(str(_scene_pick(state, key) or "").strip())
        m = SCENE_SLUG_PREFIX_RE.match(v)
        if m:
            pref = m.group(1).lower()
            return SCENE_PREFIX_CHANNEL.get(pref, pref), "префикс state.%s «%s»" % (key, v)

    raw = str(_scene_pick(state, "channel") or "").strip()
    if raw:
        low = raw.casefold().replace("ё", "е")
        for tok in SCENE_MM_TOKENS:
            if re.search(r"(?<![0-9a-zа-я])" + re.escape(tok) + r"(?![0-9a-zа-я])", low):
                return "mm", "state.channel «%s»" % raw[:60]
        for ch in SCENE_KNOWN_CHANNELS:
            if low.startswith(ch):
                return ("info" if ch == "inf" else ch), "state.channel «%s»" % raw[:60]
    return "", "канал не опознан (ни префикса имени, ни state.channel)"


def check_scene_state(state_path, package_dir=None, epoch=SCENE_GATE_EPOCH):
    """Гейт 02b1 по файлу state. Возвращает
    {"status": "PASS"|"FAIL"|"N/A", "lines": [строки печати], "scene_id", "who"}.
    Ничего не пишет и никуда не выходит - решение принимает вызывающий."""
    out = {"status": "N/A", "lines": [], "scene_id": None, "who": None}
    state_path = os.path.expanduser(str(state_path or ""))
    state_dir = os.path.dirname(os.path.abspath(state_path)) or "."
    pkg_dir = os.path.expanduser(str(package_dir or "")) or state_dir

    if not os.path.exists(state_path):
        out["lines"].append("[N/A] сцена: state «%s» на диске нет - "
                            "гейт 02b1 не применялся (state старого формата)" % state_path)
        return out
    state = _scene_load_state(state_path)
    if state is None:
        out["lines"].append("[N/A] сцена: state «%s» не читается как JSON-объект - "
                            "гейт 02b1 не применялся (state старого формата)" % state_path)
        return out

    scene = state.get("scene")
    if scene is None:
        marks = [k for k in SCENE_PIPELINE_MARKS if state.get(k) not in (None, "", [], {})]
        if not marks:
            out["lines"].append("[N/A] сцена: ключа scene нет и отметок конвейера в state нет "
                                "(чистая машинная расписка) - state старого формата, не блокирую")
            return out
        ref, ref_key = _scene_reference_time(state, state_path)
        ep = _scene_parse_iso(epoch)
        if isinstance(ref, datetime.datetime) and isinstance(ep, datetime.datetime) and ref < ep:
            out["lines"].append("[N/A] сцена: ключа scene нет, но пост собран %s (%s) - раньше "
                                "внедрения гейта (%s), архив, не блокирую"
                                % (ref.isoformat(), ref_key, epoch))
            return out
        out["status"] = "FAIL"
        out["lines"].append(
            "[FAIL] сцена/П1: ключа scene в state нет, а state несёт отметки конвейера (%s). "
            "Фаза 02b1-scene-mining.md обязана добыть эпизод (кто/когда/что делал/число/что "
            "сломалось/что появилось/улика) и записать его корневым ключом scene вместе с "
            "scene_mined_at. Без сцены тело добирает объём обобщениями - это и есть класс, "
            "который гейт ловит." % ", ".join(marks[:6]))
        return out

    fails = []
    oks = []

    # --- П1. Карточка заполнена, файл улики существует -----------------------
    if not isinstance(scene, dict):
        out["status"] = "FAIL"
        out["lines"].append("[FAIL] сцена/П1: ключ scene не объект - карточка сцены это "
                            "объект с полями id/who/when/did/number/broke/result/evidence/status "
                            "(02b1, «Формат карточки сцены»)")
        return out

    out["scene_id"] = str(scene.get("id") or "").strip() or None
    out["who"] = str(scene.get("who") or "").strip() or None

    empty = [f for f in SCENE_REQUIRED_FIELDS
             if not str(scene.get(f) or "").strip()]
    if empty:
        fails.append("[FAIL] сцена/П1: пустые обязательные поля карточки: %s. По 02b1 "
                     "обязательны все семь полей кроме broke - пустое поле значит, что "
                     "карточки нет и добыча продолжается со следующего источника S1→S8"
                     % ", ".join(empty))

    ev = scene.get("evidence")
    ev_file = ev_line = ev_quote = None
    if not isinstance(ev, dict):
        fails.append("[FAIL] сцена/П1: scene.evidence не объект {file, line, quote} - "
                     "улика непроверяема, карточка отклонена (02b1, Г2)")
    else:
        ev_file = str(ev.get("file") or "").strip()
        ev_quote = str(ev.get("quote") or "").strip()
        ev_line = ev.get("line")
        if not ev_file:
            fails.append("[FAIL] сцена/П1: scene.evidence.file пуст - улики происхождения нет")
        if not ev_quote:
            fails.append("[FAIL] сцена/П1: scene.evidence.quote пуст - сверять со строкой "
                         "источника нечего")
        try:
            ev_line = int(str(ev_line).strip())
        except Exception:
            ev_line = None
            fails.append("[FAIL] сцена/П1: scene.evidence.line не число - улика на файл БЕЗ "
                         "номера строки не принимается, она непроверяема (02b1, Г2)")

    ev_path = ""
    if ev_file:
        ev_path = _scene_resolve_path(ev_file, pkg_dir, state_dir, os.getcwd())
        if not os.path.isfile(ev_path):
            fails.append("[FAIL] сцена/П1: файла улики нет на диске - scene.evidence.file "
                         "«%s» (искал «%s»). Заявленная и не существующая улика = тот же "
                         "класс, что выдуманный факт" % (ev_file, ev_path))
        else:
            oks.append("улика-файл «%s» существует" % ev_path)

    # --- П2. Строка источника непустая и несёт цитату ------------------------
    if ev_path and os.path.isfile(ev_path) and ev_line and ev_quote:
        try:
            with open(ev_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except Exception as e:
            lines = None
            fails.append("[FAIL] сцена/П2: файл улики «%s» не читается (%s)" % (ev_path, e))
        if lines is not None:
            if ev_line < 1 or ev_line > len(lines):
                fails.append("[FAIL] сцена/П2: в файле улики «%s» строк %d, а карточка "
                             "ссылается на строку %d - `sed -n '%dp'` вернул бы пустоту. "
                             "Улика недействительна (02b1, Г2)"
                             % (ev_path, len(lines), ev_line, ev_line))
            else:
                src_line = lines[ev_line - 1]
                if not src_line.strip():
                    fails.append("[FAIL] сцена/П2: строка %d файла «%s» пустая - "
                                 "`sed -n '%dp'` вернул пустоту, улика недействительна"
                                 % (ev_line, ev_path, ev_line))
                else:
                    nq = _scene_norm(ev_quote)
                    nw = len(re.findall(r"\w+", nq, re.UNICODE))
                    if len(nq) < SCENE_QUOTE_MIN_CHARS or nw < SCENE_QUOTE_MIN_WORDS:
                        fails.append(
                            "[FAIL] сцена/П2: цитата «%s» короче порога (%d знаков / %d слов "
                            "при минимуме %d/%d). Слишком короткий кусок совпадает с чем "
                            "угодно и уликой не является - 02b1 просит дословную цитату "
                            "5-15 слов" % (ev_quote, len(nq), nw,
                                           SCENE_QUOTE_MIN_CHARS, SCENE_QUOTE_MIN_WORDS))
                    elif nq not in _scene_norm(src_line):
                        fails.append(
                            "[FAIL] сцена/П2: строка %d файла «%s» НЕ содержит цитату карточки. "
                            "В файле: «%s». В карточке: «%s». Это анти-выдумка: сцена без "
                            "реального происхождения через эту проверку не проходит"
                            % (ev_line, ev_path, src_line.strip()[:160], ev_quote[:160]))
                    else:
                        oks.append("строка %d резолвится и содержит цитату" % ev_line)

    # --- П3. Порядок: сцена добыта ДО черновика ------------------------------
    sm = _scene_parse_iso(_scene_pick(state, "scene_mined_at"))
    da = _scene_parse_iso(_scene_pick(state, "draft_at"))
    if sm is None or da is None:
        missing = []
        if sm is None:
            missing.append("scene_mined_at")
        if da is None:
            missing.append("draft_at")
        fails.append("[FAIL] сцена/П3: в state нет отметок %s - доказать, что сцена добыта ДО "
                     "текста, нечем. Класс, который это ловит: сцена подобрана под уже "
                     "написанный пост (тот же принцип, что у factbase_created_at). Фаза 02b1 "
                     "пишет scene_mined_at, 02f-polish - draft_at, обе ISO-временем"
                     % " и ".join(missing))
    elif sm == "BAD" or da == "BAD":
        fails.append("[FAIL] сцена/П3: отметки scene_mined_at / draft_at не парсятся как время "
                     "(нужен ISO: 2026-08-08T14:30:00) - порядок фаз недоказуем")
    elif sm >= da:
        fails.append("[FAIL] сцена/П3: scene_mined_at %s НЕ раньше draft_at %s - сцена добыта "
                     "после черновика, то есть подобрана под готовый текст. Закон 02b1: "
                     "сначала сцена, потом тело" % (sm.isoformat(), da.isoformat()))
    else:
        oks.append("порядок scene_mined_at %s < draft_at %s" % (sm.isoformat(), da.isoformat()))

    # --- П4. Уникальность в каталоге пакета ----------------------------------
    this_id = _scene_norm(scene.get("id"))
    this_who = _scene_norm(scene.get("who"))
    this_fp = _scene_fingerprint(scene)
    self_real = os.path.realpath(state_path)
    neighbours = 0
    try:
        siblings = sorted(glob.glob(os.path.join(pkg_dir, ".post-state-*.json")))
    except Exception:
        siblings = []
    for sp in siblings:
        try:
            if os.path.realpath(sp) == self_real:
                continue
        except Exception:
            pass
        nb = _scene_load_state(sp)
        if not nb:
            continue
        nsc = nb.get("scene")
        if not isinstance(nsc, dict):
            continue
        neighbours += 1
        if this_id and _scene_norm(nsc.get("id")) == this_id:
            fails.append("[FAIL] сцена/П4: сцена id=«%s» уже стоит в единице «%s» этого пакета. "
                         "Закон 02b1: одна сцена = одна единица, потраченную сцену вторая "
                         "единица не берёт - возвращайся в добычу S1→S8 за следующей"
                         % (scene.get("id"), os.path.basename(sp)))
        elif this_fp and _scene_fingerprint(nsc) == this_fp:
            fails.append("[FAIL] сцена/П4: у единицы «%s» этого пакета ДРУГОЙ scene.id, но ТА ЖЕ "
                         "улика (%s:%s · «%s») - это та же сцена под новым именем. "
                         "Переименование карточки уникальностью не считается"
                         % (os.path.basename(sp), this_fp[0], this_fp[1],
                            str(scene.get("evidence", {}).get("quote"))[:60]))
        if this_who and not SCENE_SELF_WHO_RE.match(this_who) \
                and _scene_norm(nsc.get("who")) == this_who:
            fails.append("[FAIL] сцена/П4: названный герой «%s» уже занят единицей «%s» этого "
                         "пакета - закон «один герой = один раз за пакет» (02b1, Г3). "
                         "Автор в роли who («я») под это правило не подпадает, названный "
                         "человек - подпадает" % (scene.get("who"), os.path.basename(sp)))
    if this_who and SCENE_SELF_WHO_RE.match(this_who):
        oks.append("who=«%s» - автор, под правило «один герой = один раз за пакет» не подпадает"
                   % scene.get("who"))
    oks.append("уникальность проверена против %d соседних state в «%s»" % (neighbours, pkg_dir))

    # --- П5-П7. Боль читателя, пересказ для новичка, уровень аудитории -------
    # Развилка архив/новый формат - см. шапку блока П5-П7 у констант выше.
    new_present = [f for f in SCENE_NEW_FIELDS
                   if scene.get(f) not in (None, "", [], {})]
    fields_epoch = _scene_parse_iso(SCENE_FIELDS_EPOCH)
    ref_t, ref_key = _scene_reference_time(state, state_path)
    archive_fields = (not new_present
                      and isinstance(ref_t, datetime.datetime)
                      and isinstance(fields_epoch, datetime.datetime)
                      and ref_t < fields_epoch)

    if archive_fields:
        oks.append("П5-П7 N/A: полей pain/novice_retell/audience_level в карточке нет, "
                   "но она собрана %s (%s) - раньше внедрения полей (%s), архив"
                   % (ref_t.isoformat(), ref_key, SCENE_FIELDS_EPOCH))
    else:
        missing_new = [f for f in SCENE_NEW_FIELDS
                       if scene.get(f) in (None, "", [], {})]
        if missing_new:
            fails.append(
                "[FAIL] сцена/П5-П7: в карточке нет полей %s. С %s фаза 02b1 кладёт в "
                "scene три поля: pain (дословная боль ЧИТАТЕЛЯ из карты болей + улика "
                "файл:строка), novice_retell (тот же эпизод ОДНИМ предложением для "
                "человека, который не знает проекта) и audience_level (novice|"
                "practitioner). Без них сцена бывает настоящей и при этом читаемой "
                "только изнутри проекта - это второй корень 02b1. Заполнено %d из 3: "
                "частичная карточка архивом не считается"
                % (", ".join(missing_new), SCENE_FIELDS_EPOCH[:10], len(new_present)))

        # П5. Боль читателя названа дословно и резолвится (02b1, Г4)
        if scene.get("pain") not in (None, "", [], {}):
            ok_pain, msg_pain = _scene_resolve_quote(scene.get("pain"), pkg_dir,
                                                     state_dir, "pain")
            (oks if ok_pain else fails).append(
                msg_pain if ok_pain else "[FAIL] сцена/П5: " + msg_pain)

        # П6. Пересказ для новичка: непустой, одно предложение, без терминов кухни
        retell = str(scene.get("novice_retell") or "").strip()
        if retell:
            if not _scene_is_single_sentence(retell):
                fails.append(
                    "[FAIL] сцена/П6: novice_retell длиннее одного предложения - «%s». "
                    "02b1 просит РОВНО одно: пересказ, который не влезает в предложение, "
                    "обычно и есть непереведённая кухня" % retell[:200])
            terms, meta, why = _scene_kitchen_terms()
            if terms is None:
                fails.append(
                    "[FAIL] сцена/П6: словарь терминов внутренней кухни недоступен - %s. "
                    "Это НЕ штатная деградация: 02b1-scene-mining.md раздаётся вместе со "
                    "скиллом и является частью самого механизма гейта (тот же контракт, "
                    "что у справочника приёмов доноров, Д105). Судить чистоту пересказа "
                    "без словаря значит выдавать непроверенное за проверенное. "
                    "🔧 ПОЧИНИ ТАК: восстанови файл на месте и перезапусти прогон" % why)
            else:
                hits = _scene_kitchen_hits(retell, terms)
                if hits:
                    fails.append(
                        "[FAIL] сцена/П6: в novice_retell стоят термины внутренней кухни "
                        "%s - пересказ не состоялся. Человек, который ни разу не открывал "
                        "Claude Code и не знает проекта, этого не поймёт, а оставить термин "
                        "«с пояснением в скобках» 02b1 запрещает. Перепиши тем, ЧТО человек "
                        "в итоге получает и какой его боли это касается. Словарь: %s (%d "
                        "терминов%s). Пересказ: «%s»"
                        % ("; ".join("«%s» → «%s»" % (t, g) for t, g in hits),
                           SCENE_MINING_DOC, len(terms),
                           (", плюс описания без регулярки: " + ", ".join(meta)) if meta else "",
                           retell[:200]))
                else:
                    oks.append("пересказ для новичка чист по словарю кухни (%d терминов)"
                               % len(terms))

        # П7. Уровень аудитории сходится с каналом единицы (02b1, Г5)
        lvl = str(scene.get("audience_level") or "").strip().casefold()
        if lvl:
            if lvl not in SCENE_AUDIENCE_LEVELS:
                fails.append(
                    "[FAIL] сцена/П7: audience_level «%s» - не из перечисления. Вердикт "
                    "гейта понятности принимает ровно два значения: novice (боль новичка) "
                    "или practitioner (боль продвинутого)" % scene.get("audience_level"))
            elif lvl == "practitioner":
                chan, chan_src = _scene_channel(state_path, state)
                if chan == "mm":
                    oks.append("канал %s, уровень practitioner, допуск по карте болей "
                               "(источник: %s)" % (chan, chan_src))
                else:
                    fails.append(
                        "[FAIL] сцена/П7: audience_level=practitioner, а канал единицы «%s» "
                        "(%s). По карте болей 02b1 продвинутая боль (реплеи, сегменты, "
                        "автовыдача доступов, пороги гейтов, устройство пайплайна) "
                        "разрешена РОВНО в одной строке - ММ, сообщество практиков. Все "
                        "остальные каналы читают преимущественно новички без ниши и берут "
                        "только боли новичка. Возьми следующую сцену по порядку S1→S8 либо "
                        "переселяй эту в свободный слот ММ"
                        % (chan or "не опознан", chan_src))
            else:
                chan, chan_src = _scene_channel(state_path, state)
                oks.append("канал %s, уровень novice, допуск по карте болей (источник: %s)"
                           % (chan or "не опознан", chan_src))

    if fails:
        out["status"] = "FAIL"
        out["lines"] = fails
    else:
        out["status"] = "PASS"
        out["lines"] = ["[PASS] сцена: id=«%s» · %s" % (scene.get("id"), " · ".join(oks))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=None,
                    help="путь к файлу с постом или '-' для stdin (не требуется с --factbase-only)")
    ap.add_argument("--max", type=int, default=None, help="макс. длина в символах")
    ap.add_argument("--min", type=int, default=None, help="мин. длина в символах")
    ap.add_argument("--allow-em-dash", action="store_true",
                    help="project-aware: разрешить em-dash '—' (напр. health). Дефолт = бан (автор).")
    ap.add_argument("--allow-marathon", action="store_true",
                    help="снять личный запрет слова события из словаря владельца (banned_words[id=marathon]).")
    ap.add_argument("--allow-perelivN", action="store_true",
                    help="снять личный запрет снятого концепта из словаря владельца (banned_words[id=perelivN]).")
    ap.add_argument("--allow-instrument", action="store_true",
                    help="снять личный запрет категории-слова из словаря владельца (banned_words[id=instrument_naming]).")
    ap.add_argument("--allow-cta-bridge", action="store_true",
                    help="снять личный запрет подводки-мостика из словаря владельца (banned_words[id=cta_bridge]).")
    ap.add_argument("--allow-end-period", action="store_true",
                    help="project-aware: разрешить точку в конце абзаца (напр. health). Дефолт = бан (автор).")
    ap.add_argument("--allow-colons", action="store_true",
                    help="снять лимит двоеточий (дефолт: максимум 1 на пост, автор ).")
    ap.add_argument("--form-goal", choices=["reactions", "forwards", "sales", "gate"], default=None,
                    help="канон формы v2 §2 (.business/voice-corpus/_format-canon-v2.md): "
                         "цель поста словом; без флага профильный слой не применяется, а пост в этом состоянии не выпускается.")
    ap.add_argument("--form-class", choices=["narrative", "razbor", "sales", "gate", "event"], default=None,
                    help="класс поста при --form-goal reactions (narrative/razbor); "
                         "для forwards/sales/gate класс = цели, флаг опционален; "
                         "event (Д8, по решению автора) - событийный пост, перекрывает цель и "
                         "включает свои гейты 4.DENS и «дата/время события».")
    ap.add_argument("--channel", default="osn",
                    help="канал выдачи (osn|zakr|info|bot|...) - для журнала скелетов И (v2.0) "
                         "для UTM/PS-ACTION/поддержки-в-бот-цепочке (дефолт osn = основной TG).")
    ap.add_argument("--skeleton-log", default=None,
                    help="путь к журналу скелетов (дефолт: .skeleton-log.jsonl рядом со скиллом).")
    ap.add_argument("--log-skeleton", metavar="SLUG",
                    help="после выдачи: дописать скелет этого поста в журнал под слагом SLUG.")
    ap.add_argument("--allow-skeleton-repeat", metavar="ПРИЧИНА", default=None,
                    help="понизить совпадение скелета до WARN с печатью причины "
                         "(законно только «скелет унаследован от источника по просьбе автора»).")
    ap.add_argument("--allow-no-premium-hook", metavar="ПРИЧИНА", default=None,
                    help="понизить отсутствие эмодзи-заголовка до WARN с печатью причины "
                         "(дефолт: заголовок = премиум-эмодзи + пробел + жирный, владелец).")
    ap.add_argument("--allow-no-oral", metavar="ПРИЧИНА", default=None,
                    help="волна 15: понизить отсутствие знаков устной речи (скобка ))/многоточие/"
                         "вопрос/частица) до WARN с печатью причины. Дефолт HARD - 10/10 "
                         "донор-эталонов и финалов владельца несут хотя бы один знак.")
    ap.add_argument("--allow-no-psa", metavar="ПРИЧИНА", default=None,
                    help="понизить отсутствие P.S.-Action приписки до WARN с печатью причины. "
                         "Законно ТОЛЬКО для архивных фикстур/перепроверки уже опубликованного "
                         "текста - для живой выдачи приписка обязательна (PS-ACTION-канон.md).")
    # --- 4c (подэтап 4c, план 2026-08-06-content-engine-v3.md) ---
    ap.add_argument("--allow-metaphor", metavar="ПРИЧИНА", default=None,
                    help="4c/D1: понизить метафору-корень (канон п.49) до WARN с печатью причины. "
                         "Законно для архивных фикстур СТАРШЕ правила от этой редакции - для живой "
                         "выдачи переносное значение переписывается буквально.")
    ap.add_argument("--allow-rubricator", metavar="ПРИЧИНА", default=None,
                    help="раунд 1 / канон п.16: понизить ярлык-рубрикатор в зачине абзаца "
                         "(«На вход», «Честная граница», «Что забрать сегодня»...) до WARN "
                         "с печатью причины. Законно ТОЛЬКО для архивных постов СТАРШЕ "
                         "разбора эталона 6.08, где формульные блоки запрещены построчно.")
    ap.add_argument("--allow-unnamed-carrier", metavar="ПРИЧИНА", default=None,
                    help="Д111: понизить «носитель без площадки» до WARN с печатью причины. "
                         "Законно только там, где площадка названа НЕ текстом (картинкой, "
                         "шапкой канала) - в живой выдаче площадка обязана быть словом.")
    ap.add_argument("--allow-dead-lang", metavar="ПРИЧИНА", default=None,
                    help="анти-корпус по решению автора: понизить классы мёртвых конструкций К1-К11 "
                         "до WARN с печатью причины (включая пакетный порог К8). Законно ТОЛЬКО "
                         "для архивных текстов СТАРШЕ правила и для ЧУЖИХ текстов (донор-корпус): "
                         "закон о конструкциях - закон автора про свои посты. Для живой выдачи "
                         "конструкция переписывается по слепку "
                         "voice-corpus/_konstrukcii-zhivogo-yazyka.md, а не понижается флагом.")
    ap.add_argument("--allow-dead-lexicon", metavar="ПРИЧИНА", default=None,
                    help="антисловарь абстракций по решению автора: понизить лексический слой живого "
                         "языка (TIER-A и плотностный порог) до WARN с печатью причины. "
                         "Отдельный флаг от --allow-dead-lang: тот про СИНТАКСИС (К1-К11), "
                         "этот про СЛОВА. Законно ТОЛЬКО для архивных текстов СТАРШЕ правила "
                         "и для ЧУЖИХ текстов. Для живой выдачи слово заменяется по "
                         "references/zhivoy-yazyk.md разд.4, а не понижается флагом.")
    ap.add_argument("--allow-element-floor", metavar="ПРИЧИНА", default=None,
                    help="элементы формы по решению автора: понизить до WARN ТОЛЬКО пол «3 разных "
                         "типа элементов из 15» (счёт переписи формы). Сигнатурный пол НЕ "
                         "снимает - у него свой флаг --allow-signature-floor (Д6 по решению автора: одна "
                         "причина на два закона запрещена, причина обязана называть, какой "
                         "именно пол снимается). Законно для ЧУЖИХ и архивных текстов: пол "
                         "снят с зелёного корпуса владельца, чужой текст ему не обязан. Для "
                         "живой выдачи элемент ставится, а не понижается флагом.")
    ap.add_argument("--allow-signature-floor", metavar="ПРИЧИНА", default=None,
                    help="сигнатурные элементы по решению автора: понизить до WARN ТОЛЬКО пол «1 "
                         "сигнатурный элемент из 8» (КАПС · курсив · тире-опись · нумерация · "
                         "стрелка · прямая речь · двоеточие-раскрытие · растяжка - то, что "
                         "ставит только автор). Отдельный флаг от --allow-element-floor: тот "
                         "про перепись 15 категорий, этот про авторскую текстуру. Законно "
                         "ТОЛЬКО для чужих и архивных текстов; на живой выдаче элемент "
                         "ставится, а не понижается флагом.")
    ap.add_argument("--allow-low-density", metavar="ПРИЧИНА", default=None,
                    help="4c/B19: понизить нижний порог плотности идей (канон п.19) до WARN "
                         "с печатью причины. Законно для ЧУЖИХ текстов (донор-корпус): п.19 - "
                         "закон автора про свои посты, чужой текст ему не обязан.")
    # --- v2.0 (AC1/AC5/AC6, спека 2026-08-04-post-skill-v2.md) ---
    ap.add_argument("--budget", type=int, default=None,
                    help="v2.0 AC1: цель длины - превышение = WARN с печатью, НЕ FAIL "
                         "(канон §3 запрещает блок выдачи по длине).")
    ap.add_argument("--factbase", default=None, metavar="FILE",
                    help="v2.0 AC5: путь к факт-базе поста. Проверяет (а) объём факт-базы >= "
                         "объёма поста, (б) каждое число поста есть в факт-базе, (в) каждое имя "
                         "собственное поста есть в факт-базе. Провал (б)/(в) = HARD «выдуманный факт».")
    ap.add_argument("--factbase-only", default=None, metavar="FILE",
                    help="v2.0 02b Шаг 4.5: проверить ТОЛЬКО объём факт-базы против --budget, "
                         "БЕЗ позиционного файла поста (поста ещё нет на фазе 02b, сравнивать не с "
                         "чем). Требует --budget. Печатает [PASS]/[WARN] факт-база и всегда exit 0 "
                         "(гейт длины факт-базы промптовый - решение «добрать/понизить» принимает "
                         "человек в 02b, не код). Не заменяет --factbase (тот сверяет числа/имена "
                         "готового поста с базой на 04-review, этот флаг работает раньше, до поста).")
    ap.add_argument("--package", default=None, metavar="DIR",
                    help="v2.0: каталог пакета постов (напр. серия информеров одного дня) - "
                         "кросс-постовые дубли заголовка внутри пакета, WARN.")
    ap.add_argument("--anchor", default=None,
                    help="v2.0 класс R2-8: якорь-история этого поста (для журнала .used-anchors.jsonl).")
    ap.add_argument("--hero", default=None,
                    help="v2.0 класс R2-8: скилл-герой этого поста (для журнала .used-anchors.jsonl).")
    ap.add_argument("--scene-state", default=None, metavar="FILE",
                    help="гейт 02b1 (добыча сцены): путь к .post-state-<слаг>.json. Проверяет "
                         "(П1) ключ scene заполнен и файл улики существует, (П2) строка улики "
                         "непустая и содержит дословную цитату карточки, (П3) scene_mined_at < "
                         "draft_at, (П4) scene.id и названный герой не повторяются в каталоге "
                         "пакета. Без позиционного файла поста работает отдельным режимом "
                         "(exit 1 при FAIL); вместе с файлом - добавочный HARD-гейт прогона. "
                         "Ключа scene нет и отметок конвейера нет - печатает N/A и не блокирует "
                         "(архив, посты до внедрения фазы).")
    ap.add_argument("--scene-package", default=None, metavar="DIR",
                    help="каталог пакета для проверки П4 (дефолт - каталог самого state).")
    ap.add_argument("--used-anchors-log", default=None,
                    help="путь к журналу якорей (дефолт: .used-anchors.jsonl рядом со скиллом).")
    ap.add_argument("--log-anchor", metavar="SLUG",
                    help="после выдачи: дописать якорь/герой/форму заголовка этого поста в журнал.")
    args = ap.parse_args()

    import os as _os
    if args.skeleton_log is None:
        args.skeleton_log = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "..", ".skeleton-log.jsonl")
    args.skeleton_log = _os.path.normpath(args.skeleton_log)
    if args.used_anchors_log is None:
        args.used_anchors_log = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)), "..", ".used-anchors.jsonl")
    args.used_anchors_log = _os.path.normpath(args.used_anchors_log)

    # --- --factbase-only: режим 02b Шаг 4.5, поста ещё нет, выходим ДО read_input(args.file).
    if args.factbase_only:
        print("=" * 56)
        print("LINT-POST: факт-база (--factbase-only, без файла поста)")
        print("=" * 56)
        if args.budget is None:
            print("[FAIL] --factbase-only требует --budget N")
            sys.exit(1)
        try:
            fb_text = load_factbase(args.factbase_only)
        except OSError as e:
            print(f"[FAIL] факт-база: не удалось прочитать {args.factbase_only} ({e})")
            sys.exit(1)
        fb_body = factbase_body_len(fb_text)
        if fb_body < args.budget:
            print(f"[WARN] факт-база: тело базы {fb_body} знаков < budget {args.budget} - "
                  f"риск воды (02b Шаг 4.5: добрать контекст из story-bank/карты смыслов/"
                  f"voice-corpus или явно понизить brief.budget; решение принимает человек здесь, "
                  f"не код - писать пост при непокрытом дефиците всё равно запрещено)")
        else:
            print(f"[PASS] факт-база: тело базы {fb_body} >= budget {args.budget}")
        print("=" * 56)
        sys.exit(0)

    # --- --scene-state БЕЗ файла поста: отдельный режим гейта 02b1. Хук доставки
    # зовёт его именно так - state существует раньше тела, и проверять сцену
    # нужно ДО того, как единица уедет файлом в пакет.
    if args.scene_state and args.file is None:
        print("=" * 56)
        print("LINT-POST: сцена (--scene-state, гейт 02b1)")
        print("=" * 56)
        _sc = check_scene_state(args.scene_state, args.scene_package)
        for _l in _sc["lines"]:
            print(_l)
        print("=" * 56)
        print("ИТОГ:", "FAIL (сцена не добыта или улика не резолвится)"
              if _sc["status"] == "FAIL" else
              ("N/A (state старого формата)" if _sc["status"] == "N/A" else "PASS (сцена чиста)"))
        print("=" * 56)
        sys.exit(1 if _sc["status"] == "FAIL" else 0)

    if args.file is None:
        ap.error("the following arguments are required: file (кроме режимов --factbase-only / "
                 "--scene-state)")

    text = read_input(args.file)
    paragraphs = split_paragraphs(text)
    length = len(text)

    form_profile, form_key = resolve_form_profile(args.form_goal, args.form_class)
    form_class = form_key[1] if form_profile is not None else None

    hard_fail = False
    print("=" * 56)
    print("LINT-POST: machine-checkable gates")
    print("=" * 56)
    if form_profile is not None:
        print(f"[ФОРМА] цель={args.form_goal} класс={form_key[1]} профиль={form_profile['label']} "
              f"(канон формы v2 §3/§9, L1-L5)")
        # 🔴 Д71 (раунд 22): заявленный класс отброшен/подменён - сказать это ВСЛУХ.
        # Строка выше печатает класс ВЗЯТЫЙ, и на несовместимой паре она совпадает с
        # целью - выглядит как норма. Без этой второй строки оператор ручного прогона
        # не мог отличить «класс доехал» от «класс выброшен, меряю чужим профилем».
        # Это ИНФО-строка: exit-код, пороги и вердикт не меняются (правило держит хук).
        if LAST_FORM_COERCION is not None:
            _decl, _goal, _took = LAST_FORM_COERCION
            print(f"[ФОРМА-КОЭРЦИЯ] класс «{_decl}» несовместим с целью «{_goal}» - "
                  f"профиль взят «{_took}» (канон пар: 01-router Шаг 0.49)")
    else:
        # 🔴 4c: БЫЛО тихое INFO - «профильный слой не применялся», exit 0, и пост
        # без цели формы уезжал как «чистый», хотя половина закона его не смотрела.
        # СТАЛО HARD: отсутствие цели формы это ошибка ЗАПУСКА линтера, а не
        # свойство текста. Хук post-phase-gate.sh цель всегда передаёт (он сам
        # блокирует пустой L4_empirics.form_mode.goal), так что на живой выдаче
        # эта ветка не срабатывает - она ловит ручной прогон мимо конвейера.
        hard_fail = True
        print("[FAIL] --form-goal не передан - профильный слой (L1-L5 канона формы v2) "
              "не применялся, значит пост проверен лишь наполовину. Вернись в 01-router "
              "Шаг 0.49 за целью и передай --form-goal reactions|forwards|sales|gate")

    # 4.1.6.5 точки в конце абзаца (HARD; project-aware override)
    if args.allow_end_period:
        print(f"[SKIP] 4.1.6.5 точка в конце абзаца — разрешено проектом (--allow-end-period)")
    else:
        period_fails = check_paragraph_periods(paragraphs)
        if period_fails:
            hard_fail = True
            print(f"[FAIL] 4.1.6.5 точка в конце абзаца: {len(period_fails)} наруш.")
            for idx, tail in period_fails:
                print(f"        абзац {idx}: ...{tail}")
        else:
            print(f"[PASS] 4.1.6.5 точка в конце абзаца (0/{len(paragraphs)} абзацев)")

    # 4.1.1 em-dash (HARD; project-aware override)
    if args.allow_em_dash:
        print("[SKIP] 4.1.1 em-dash '—' — разрешено проектом (--allow-em-dash)")
    else:
        em = check_em_dash(text)
        if em:
            hard_fail = True
            print(f"[FAIL] 4.1.1 em-dash '—' внутри строки: {len(em)} наруш.")
            for ln, frag in em:
                print(f"        строка {ln}: {frag}")
        else:
            print("[PASS] 4.1.1 em-dash '—' внутри строки (0)")

    # двоеточия: лимит из профиля цели (R/S — 1 как раньше; F — 2, опись-анонс на
    # двоеточии, канон формы v2 §8.2/L4). Без --form-goal лимит прежний — 1.
    if args.allow_colons:
        print("[SKIP] двоеточия — лимит снят (--allow-colons)")
    else:
        colons_limit = form_profile["colons_max"] if form_profile is not None else 1
        colons = check_colons(text)
        if len(colons) > colons_limit:
            hard_fail = True
            print(f"[FAIL] двоеточий в посте: {len(colons)} (лимит {colons_limit} на пост; автор )")
            for ln, frag in colons:
                print(f"        строка {ln}: {frag}")
        else:
            print(f"[PASS] двоеточия: {len(colons)} (лимит {colons_limit} на пост)")

    # стаккато-декларации = мёртвый язык (WARN; автор )
    stac = check_staccato(text)
    if stac:
        print(f"[WARN] стаккато-декларации (мёртвый язык): {len(stac)} абзац(ев) "
              f"с рядом 4+ коротких клауз без союзов-сцепок. Живая речь цепляет "
              f"предложения союзами (и/а/потому что/так что) и течёт волной")
        for n, frag in stac:
            print(f"        ряд {n}: {frag}")
    else:
        print("[PASS] стаккато-деклараций нет (речь связная, не рубленая)")

    # заголовок жирный (WARN; подход автора к форматированию, прецедент по решению автора).
    # L3, канон §1/§9 R-5: профильно — обязателен только --form-goal reactions +
    # narrative (85% против 63%); в razbor запрет и требование сняты (67% верха
    # тоже несёт жирный хук, преимущества не даёт). Без --form-goal — как раньше, всегда.
    if form_profile is not None and not form_profile.get("headline_bold_check", True):
        print(f"[INFO] форма-профиль {form_profile['label']}: жирность хука не проверяется (канон §9)")
    elif check_headline_bold(paragraphs):
        print("[PASS] заголовок жирный (**...**)")
    else:
        suffix = f" (профиль {form_profile['label']}: желательно, не блок)" if form_profile is not None else ""
        print("[WARN] заголовок НЕ жирный — оберни первую строку в **...** "
              "(эмодзи вне звёзд: '🔒 **Текст**'); подход автора с 2026" + suffix)

    # 'база' как аудитория (HARD; внутренний термin, прецедент по решению автора)
    baza = check_baza(text)
    if baza:
        hard_fail = True
        print(f"[FAIL] лексика: 'база' в значении аудитории: {len(baza)} наруш. "
              f"(внутренний термин — замени на подписчики/читатели/люди/аудитория)")
        for ln, frag in baza:
            print(f"        строка {ln}: {frag}")
    else:
        print("[PASS] лексика: 'база' в значении аудитории (0)")

    # 🔴 Д111 (досыл владельца ): БЕЗЫМЯННЫЙ НОСИТЕЛЬ. HARD.
    # Прецедент osn23: «Взял свои записи за десять месяцев…» - владелец: «Какие
    # нахер записи? Про что речь? Про Reels? Про посты в Telegram?». Слово-корпус,
    # присвоенное автором или отмеренное сроком, обязано нести в окне (это
    # предложение + предыдущее) площадку или указательную привязку. Ширина класса
    # и оба сужения откалиброваны на 12 зелёных владельца - см. шапку
    # check_unnamed_carrier.
    carriers = check_unnamed_carrier(text)
    if carriers and args.allow_unnamed_carrier:
        print(f"[WARN] носитель без площадки: {len(carriers)} - понижено флагом "
              f"(причина: {args.allow_unnamed_carrier})")
        for w, frag in carriers[:5]:
            print(f"        «{w}» :: {frag}")
    elif carriers:
        hard_fail = True
        for w, frag in carriers:
            print(f"[FAIL] носитель без площадки: «{w}» - читатель не понимает, о чём речь "
                  f"(владелец: «какие записи? Про Reels? Про посты в Telegram?»). "
                  f"Назови площадку в этом или предыдущем предложении")
            print(f"        {frag}")
    else:
        print("[PASS] носитель назван площадкой (безымянных корпусов 0)")

    # длина. Явные --min/--max — старое HARD-поведение без изменений (приоритет
    # у явного вызова). Без них, но с --form-goal — коридор из профиля цели,
    # канон формы v2 §3: WARN + строка обоснования, не блок (длина верха
    # разбросана слишком широко, чтобы блокировать — канон §3).
    # 🔴 4c: два прежних HARD-сайта (> max и < min) слиты в ОДИН - это одна
    # проверка коридора с двумя границами, а не два независимых правила.
    # Плюс зашит пол по типу единицы (см. UNIT_LENGTH_HARD_FLOOR выше):
    # раньше огрызок ловился только если оператор вручную вспомнил --min.
    if args.max is not None or args.min is not None:
        length_defect = None
        if args.max is not None and length > args.max:
            length_defect = f"длина {length} > max {args.max}"
        elif args.min is not None and length < args.min:
            length_defect = f"длина {length} < min {args.min}"
        if length_defect:
            hard_fail = True
            print(f"[FAIL] 4.1.6 {length_defect}")
        else:
            lim = f"(min {args.min} / max {args.max})" if (args.min or args.max) else ""
            print(f"[PASS] 4.1.6 длина {length} символов {lim}")
    elif length < UNIT_LENGTH_HARD_FLOOR:
        hard_fail = True
        print(f"[FAIL] 4.1.6 огрызок: длина {length} < {UNIT_LENGTH_HARD_FLOOR} знаков - "
              f"абсолютный пол таблицы длин (канон п.45; владелец 6.08: «что за огрызки на две "
              f"строчки? смыслов нет, это спам»). Пол един для всех типов единиц")
    elif form_profile is not None and form_profile.get("length_min") is not None:
        lo, hi, tgt = form_profile["length_min"], form_profile["length_max"], form_profile["length_target"]
        if length < lo or length > hi:
            print(f"[WARN] форма-профиль {form_profile['label']}: длина {length} вне коридора "
                  f"{lo}-{hi} (цель ~{tgt}, канон §3) — не блок, нужна строка обоснования")
        else:
            print(f"[PASS] форма-профиль {form_profile['label']}: длина {length} в коридоре {lo}-{hi} (цель ~{tgt})")
    else:
        print(f"[PASS] 4.1.6 длина {length} символов (профиль/предел не заданы)")

    # 4c: норма длины ПО ТИПУ ЕДИНИЦЫ (канон п.45) - WARN, не блок. Почему не
    # HARD: буква таблицы 6.08 строже одобренного корпуса (osn17=1541 и
    # star17=1492 при норме 1700, zakr18=1497 при норме 1500) - см. комментарий
    # у UNIT_LENGTH_CLASS_MIN. Блокирует только абсолютный пол 500 выше.
    _class_min = UNIT_LENGTH_CLASS_MIN.get(args.channel)
    if _class_min and length < _class_min:
        print(f"[WARN] длина по типу единицы: {length} < нормы {_class_min} для канала "
              f"'{args.channel}' (канон п.45, единая таблица длин) - не блок, но добери смысл")
    elif _class_min:
        print(f"[PASS] длина по типу единицы: {length} >= нормы {_class_min} "
              f"для канала '{args.channel}' (канон п.45)")

    # 4.1.4 восклицания (WARNING)
    exc = check_exclamations(text)
    tag = "WARN" if exc > 1 else "PASS"
    print(f"[{tag}] 4.1.4 восклицательных знаков: {exc}")

    # 4.1.5 списки (WARNING)
    lists = check_lists(text)
    tag = "WARN" if lists > 1 else "PASS"
    print(f"[{tag}] 4.1.5 list-маркеров: {lists}")

    # 4.0.3 выразительное форматирование. L2, канон формы v2 §8.2: квота «минимум
    # 4 приёма» ОТМЕНЕНА (сильный нарратив несёт 1 жирный против 3 у слабого — квота
    # заставляла добирать капсом/курсивом там, где эмпирика велит не ставить), поэтому
    # hard_fail при dev_total < 2 снят, вывод — INFO/WARN, не FAIL. Точное число
    # выделений жирным по профилю печатает check_bold_count ниже (при --form-goal).
    # 🔴 по решению автора: снятый тут HARD ЗАМЕНЁН на check_element_types (блок сразу
    # ниже) - один источник правды по «голой простыне». До этой правки снятие
    # квоты не имело замены вовсе, и пост без единого элемента уходил зелёным.
    devices, dev_total = check_formatting_devices(text)
    used = [f"{k}×{v}" for k, v in devices.items() if v > 0]
    dev_floor = 2  # ориентир разнообразия типов приёмов, не HARD
    tag = "INFO" if dev_total >= dev_floor else "WARN"
    print(f"[{tag}] 4.0.3 форматирование: {dev_total} типов приёмов "
          f"({', '.join(used) if used else 'НЕТ — голая простыня'})")
    if dev_total < dev_floor:
        print(f"        меньше {dev_floor} типов приёмов — не блок (канон §8.2 снял квоту ≥4),")
        print("        но профильное число жирных (bold_count) и голую простыню проверь на глаз.")

    # --- ЭЛЕМЕНТЫ ФОРМЫ (по решению автора, разнос владельца «нет никаких прикольных
    # элементов»). HARD-пол 3 типа = минимум зелёного корпуса, цель 6 = медиана
    # доноров (WARN). Это и есть настоящая защита от голой простыни: 4.0.3 выше
    # свою квоту потерял каноном §8.2 и остался видимостью.
    el = check_element_types(text)
    el_missing = element_missing_line(el["missing"])
    n_sig = len(ELEMENTS_SIGNATURE)
    if el["types"] < ELEMENT_TYPES_FLOOR and args.allow_element_floor:
        # 🔴 Д5 (по решению автора): применение флага печатается ЕЩЁ И В stderr. Хук на
        # exit 0 stdout не показывает, поэтому ослабление пола было невидимым.
        _flag_note(f"--allow-element-floor применён: пол «{ELEMENT_TYPES_FLOOR} типов из 15» "
                   f"понижен до WARN при факте {el['types']}. Причина: {args.allow_element_floor}")
        print(f"[WARN] элементы формы: {el['types']} типов из 15 < пола {ELEMENT_TYPES_FLOOR}, "
              f"понижено флагом --allow-element-floor (причина: {args.allow_element_floor}). "
              f"Не хватает: {el_missing}")
    elif el["types"] < ELEMENT_TYPES_FLOOR:
        hard_fail = True
        print(f"[FAIL] элементы формы: {el['types']} типов из 15 (HARD-пол {ELEMENT_TYPES_FLOOR}; "
              f"замер: green-ivan min 3, медиана доноров 6). "
              f"Не хватает: {el_missing}")
    elif el["types"] < ELEMENT_TYPES_TARGET:
        print(f"[WARN] элементы формы: {el['types']} типов (цель {ELEMENT_TYPES_TARGET} = медиана "
              f"доноров); нет: {el_missing}")
    else:
        print(f"[PASS] элементы формы: {el['types']} типов из 15")
    print("        есть: " + (", ".join(f"{ELEMENT_LABELS[k]}×{el['counts'][k]}"
                                        for k in el["present"]) or "НЕТ НИ ОДНОГО"))

    # 🔴 СИГНАТУРНЫЙ ПОЛ (по решению автора). Счёт «типов из 15» бесплатен: шесть
    # категорий ставит сам канон формы, а не копирайтер (см. блок констант
    # ELEMENTS_SIGNATURE). Настоящую текстуру доноров держит ЭТОТ пол, и с Д1
    # его детекторы строгие - формальный токен («МСК», кавычки вокруг оборота,
    # одиночное тире, служебное двоеточие, стрелка в 👉-строке) не засчитывается.
    sig_missing_line = element_sig_missing_line(el["sig_missing"])
    sig_have = ", ".join(f"{ELEMENT_LABELS[k]}×{el['counts'][k]}"
                         for k in el["sig_present"]) or "НЕТ НИ ОДНОГО"
    if el["sig_types"] < ELEMENT_SIG_FLOOR and args.allow_signature_floor:
        _flag_note(f"--allow-signature-floor применён: сигнатурный пол "
                   f"«{ELEMENT_SIG_FLOOR} из {n_sig}» понижен до WARN при факте "
                   f"{el['sig_types']}. Причина: {args.allow_signature_floor}")
        print(f"[WARN] сигнатурные элементы: {el['sig_types']} из {n_sig} < пола "
              f"{ELEMENT_SIG_FLOOR}, понижено флагом --allow-signature-floor "
              f"(причина: {args.allow_signature_floor}). Нет: {sig_missing_line}")
    elif el["sig_types"] < ELEMENT_SIG_FLOOR:
        hard_fail = True
        print(f"[FAIL] сигнатурные элементы: {el['sig_types']} из {n_sig} (HARD-пол "
              f"{ELEMENT_SIG_FLOOR}; замер строгим счётом: медиана доноров "
              f"{ELEMENT_SIG_TARGET}, стерильный текст 0). "
              f"Жирный/эмодзи/вопрос/скобка/панч ставит сам канон формы - они в счёт "
              f"НЕ идут; формальный токен (аббревиатура капсом, кавычки вокруг оборота, "
              f"одиночное тире, служебное двоеточие, знак → в служебной 👉-строке) тоже. "
              f"Поставь хотя бы одно: {sig_missing_line}")
    elif el["sig_types"] < ELEMENT_SIG_TARGET:
        print(f"[WARN] сигнатурные элементы: {el['sig_types']} из {n_sig} (цель "
              f"{ELEMENT_SIG_TARGET} = медиана доноров на строгом счёте); "
              f"нет: {sig_missing_line}")
    else:
        print(f"[PASS] сигнатурные элементы: {el['sig_types']} из {n_sig} - {sig_have}")

    # L5, канон §9: профильные метрики жирного/списков/ссылок/нумерации/медианы/цифры
    # в хуке. Активны ТОЛЬКО при --form-goal — без флага блок целиком пропускается.
    if form_profile is not None:
        # 🔴 Д110 (владелец): ЖИРНЫЙ В ТЕЛЕ - МАШИННЫЙ ПОЛ, НЕ ОРИЕНТИР.
        # Было: печаталось одно число «жирных N» без разбивки и без пола, поэтому
        # пост-простыня (жирный только в заголовке) уходил зелёным. Стало: считаем
        # ОТДЕЛЬНО заголовок и тело; профильный `bold_body_min`/`bold_min_total`
        # блокируют. Потолок как был - WARN (канон §9 блокировать по верху
        # запрещает: покрытия не хватает ни в одном профиле).
        if form_profile.get("bold_target") is not None:
            bc, bc_head, bc_body = check_bold_split(text)
            ceiling = form_profile.get("bold_ceiling")
            tgt = form_profile["bold_target"]
            body_min = form_profile.get("bold_body_min")
            total_min = form_profile.get("bold_min_total")
            defects = []
            if body_min is not None and bc_body < body_min:
                defects.append(f"жирных в теле {bc_body} при поле {body_min} профиля "
                               f"{form_profile['label']}")
            if total_min is not None and bc < total_min:
                defects.append(f"жирных всего {bc} при поле {total_min} профиля "
                               f"{form_profile['label']}")
            if defects:
                hard_fail = True
                print(f"[FAIL] форматирование-простыня: {' · '.join(defects)} "
                      f"(цель {tgt}, потолок {ceiling}; заголовок {bc_head} + тело {bc_body}). "
                      f"Владелец по решению автора: «форматирование это ключевая база движка, "
                      f"а не просто заголовок жирный»")
                print(f"        разметь в ТЕЛЕ ключевые точки остановки глаза: канон §4.5 - "
                      f"жирный в S/F/E работает навигацией и складывается в мини-пост")
            elif ceiling is not None and bc > ceiling:
                print(f"[WARN] форма-профиль {form_profile['label']}: жирных {bc} > потолок {ceiling} "
                      f"(цель {tgt}, канон §9; заголовок {bc_head} + тело {bc_body})")
            else:
                print(f"[PASS] форма-профиль {form_profile['label']}: жирных {bc} "
                      f"(заголовок {bc_head} + тело {bc_body}; цель {tgt}, потолок {ceiling}, "
                      f"пол тела {body_min if body_min is not None else '-'})")
            # разбор без вывода в теле: канон §3.1 «1, потолок 2, из них один -
            # вывод в теле». WARN, а не блок - улика калибровки: зелёные владельца
            # osn18-0608 и zakr18-den-0608 несут 0 жирных в теле и приняты автором.
            if body_min is None and form_key == ("reactions", "razbor") and bc_body == 0:
                print(f"[WARN] форма-профиль {form_profile['label']}: в теле нет ни одного жирного "
                      f"(канон §3.1: из 1-2 жирных один - вывод в теле). Не блок: зелёные "
                      f"osn18-0608 и zakr18-den-0608 приняты владельцем с 0 в теле")

        # Д110. Канон §9 R-4 HARD-края жирного: служебная строка на двоеточии и
        # жирный обрывок. В F та же конструкция работает НАОБОРОТ (§4.5:
        # 33/59 верха против 8/59 - там это навигация по описи), поэтому в F
        # печатается INFO и не блокирует.
        _b_colons, _b_stubs = check_bold_colon_stub(text)
        if _b_colons or _b_stubs:
            _in_fwd = form_key is not None and form_key[0] == "forwards"
            if _in_fwd and _b_colons and not _b_stubs:
                print(f"[INFO] жирная строка на двоеточии: {len(_b_colons)} - в профиле F это "
                      f"навигация по описи (канон §4.5, 33/59 верха), не дефект")
            else:
                hard_fail = True
                bad = ([f"на двоеточии: «{c}»" for c in _b_colons]
                       + [f"обрывок: «{s}»" for s in _b_stubs])
                print(f"[FAIL] жирный потрачен на служебное: {len(bad)} шт. (канон §9 R-4 HARD, "
                      f"§4.5: служебная строка на двоеточии - маркер низа 4/27 верха против 13/27, "
                      f"жирный обрывок - эталон брака #1410)")
                for b in bad[:5]:
                    print(f"        {b}")
        else:
            print("[PASS] жирный не потрачен на служебное (ни двоеточий, ни обрывков)")

        # списочные блоки (R-нарратив 0 = HARD 93% верха; остальные — WARN)
        if form_profile.get("list_blocks_max") is not None:
            blocks = check_list_blocks(text)
            limit = form_profile["list_blocks_max"]
            if len(blocks) > limit:
                if args.form_goal == "reactions" and form_key[1] == "narrative":
                    hard_fail = True
                    ltag = "FAIL"
                else:
                    ltag = "WARN"
                print(f"[{ltag}] форма-профиль {form_profile['label']}: списочных блоков {len(blocks)} "
                      f"> {limit} (канон §9)")
                for ln, size in blocks:
                    print(f"        блок со строки {ln}: {size} пункт(ов)")
            elif len(blocks) == 0 and form_key == ("forwards", "forwards"):
                # 🔴 по решению автора. Было: ноль блоков в F печатался как
                # `[PASS] ... списочных блоков 0 (потолок 2)` - потолок отчитывался
                # за цель, и отсутствие описи выглядело достижением. В F опись это
                # ЦЕЛЬ профиля (тире-опись у 52% FWD-верха, канон §9 F «опись 5-8
                # пунктов желательна»), поэтому её отсутствие печатается честно.
                # WARN, не FAIL: HARD ставится только там, где его держит зелёный
                # корпус, а зелёные владельца сами несут нули по этой оси.
                print(f"[WARN] описи нет: 0 блоков при цели профиля {form_profile['label']} "
                      f"(тире-опись у 52% FWD-верха, канон §9)")
            else:
                print(f"[PASS] форма-профиль {form_profile['label']}: списочных блоков {len(blocks)} "
                      f"(потолок {limit})")

        # 🔴 ПРОФИЛЬНЫЕ ОСИ ЦЕЛИ F (по решению автора, замер верха доноров цели forwards).
        # Цели, не потолки, и все три - WARN: HARD по ним запрещён законом
        # калибровки (зелёный корпус владельца несёт нули по эмодзи, курсиву и
        # капсу, а правило, валящее зелёный, в этом файле не живёт).
        if form_key == ("forwards", "forwards"):
            _el_f = check_element_types(text)
            for _key, _share in (("emoji_count", 85), ("italic", 58), ("caps_word", 52)):
                if _el_f["counts"][_key] == 0:
                    print(f"[WARN] профиль F: {ELEMENT_LABELS[_key]} 0 "
                          f"({_share}% FWD-верха несут его, канон §9) - цель профиля, не потолок")

        # нумерация: HARD-запрет вне F (канон §9 R-9/S-13), в F — разрешена как алгоритм
        numbered = check_numbered_list(text)
        if not form_profile.get("numbered_list_allowed", False):
            if numbered > 0:
                # 🔴 4c: HARD СНЯТ до WARN. Улика: эталон владельца 6.08
                # (green-ivan/etalon-0608.txt) сам построен на нумерованном
                # списке - «1. Как устроен вайбкодинг на Claude … 2. …», и
                # green-ivan/inf18-0608.txt повторяет эту форму осознанно
                # (пометка в источнике _pakety-0608/inf18.md). Правило
                # блокировало ровно ту форму, которую задаёт мерило качества.
                print(f"[WARN] форма-профиль {form_profile['label']}: нумерованный список "
                      f"{numbered} пункт(ов) (канон §9 не любит его вне F) - не блок с 4c: "
                      f"эталон владельца 6.08 сам идёт нумерованным списком")
            else:
                print(f"[PASS] форма-профиль {form_profile['label']}: нумерации нет")
        else:
            print(f"[INFO] форма-профиль {form_profile['label']}: нумерация разрешена, {numbered} пункт(ов)")

        # ссылки — профильная политика (канон §1/§9)
        urls, url_counts = check_links(text)
        bare = check_bare_domains(text)
        if bare:
            # Telegram автолинкует голый домен: для счёта якорей он равен https://
            print(f"[INFO] голых доменов (Telegram сделает их ссылками): {len(bare)} — {', '.join(sorted(set(bare)))}")
            for b in bare:
                urls.append(b)
                url_counts[b] += 1
        # Закон 29 (владелец 5.08): служебные t.me-двери (приписка-канон PS-ACTION
        # «войти можно здесь» и штаб) - инфраструктура, не продающий якорь.
        # В счёт якорей формы S идут только продуктовые/лендинг-адреса.
        # 🔴 Д18 (по решению автора), К3. РАЗВЕДЕНЫ ДВА СЧЁТА, раньше это был один.
        # `n_doors` - есть ли у поста ДВЕРЬ (закон 32). Дверью работает любая
        # ссылка входа, включая t.me-инвайт в комнату: на замере боевого корпуса
        # _pakety-* 7 единиц несут дверью ровно `👉 [Войти в канал](t.me/+…)`, и
        # закон 32 объявлял их «продающей единицей БЕЗ ссылки на дверь».
        # `n_links` - счёт ПРОДАЮЩИХ ЯКОРЕЙ (форма S, канон §9 S-4): тут t.me
        # по-прежнему инфраструктура и в счёт не идёт (закон 29, владелец 5.08).
        service = {u for u in url_counts if "t.me/" in u}
        n_doors = len(urls)
        for u in service:
            url_counts.pop(u, None)
        urls = [u for u in urls if u not in service]
        n_links = len(urls)
        n_unique = len(url_counts)
        dup = max(url_counts.values()) if url_counts else 0
        # 🔴 4c: ССЫЛОЧНАЯ ПОЛИТИКА ПРОФИЛЯ = ОДНО правило с взаимоисключающими
        # ветками, а не пять. Раньше было пять отдельных блокирующих входов
        # (R-нарратив / F / закон 32 / S-якоря / A) - пять строк в бюджете HARD,
        # хотя за один прогон может сработать РОВНО ОДНА ветка: профиль у поста
        # один. Поведение веток не тронуто, изменился только учёт.
        # ═══ ЗАКОН 32 ПО МАТРИЦЕ КАНАЛ×КЛАСС (Д18, по решению автора, К3) ═══════════
        # БЫЛО: закон 32 висел ВЕТКОЙ внутри `form_goal == sales`, то есть право
        # выйти без двери выдавала ЦЕЛЬ ФОРМЫ, которую пишет тот же, кто пишет
        # пост. Из 25 пар --form-goal/--form-class дверь требовали 5, а 8 пар
        # (`reactions`×{sales,event,razbor,gate} и `gate`×{sales,narrative,event,
        # razbor}) давали PASS единице без двери - шапка снимала закон каналу.
        # СТАЛО: право «ноль ссылок» решают КАНАЛ и КЛАСС единицы, цель формы на
        # него не влияет вообще. Матрица ниже выведена из зелёного корпуса
        # владельца (post-fixtures-ivan/green-ivan, манифест в run-tests.py):
        #   osn18-0608 (osn, razbor)       0 ссылок, принят
        #   etalon-0608 (osn, razbor)      0 ссылок, принят
        #   zakr18-den-0608 (zakr, razbor) 0 ссылок, принят  → и на закрытом канале
        #   ivan-final-0/1/2 (info, sales) по 1 ссылке       → sales всегда с дверью
        # Класс `event` (Д8) стоит рядом с sales: событие без входа бессмысленно.
        # Каналы С ДВЕРЬЮ - те, где единица запуска физически ведёт читателя ко
        # входу (список синхронен DOOR_CHANNELS хука post-layer-checkpoint-gate).
        DOOR_CHANNELS     = {"osn", "zakr", "star", "info", "email", "mm"}
        ZERO_DOOR_ALWAYS  = {"razbor"}              # улики выше: принят на osn и zakr
        ZERO_DOOR_OFFDOOR = {"narrative", "gate"}   # только вне каналов с дверью:
        # принятого нарратива/гейта БЕЗ двери на боевом канале запуска в корпусе
        # нет ни одного, а именно этой парой шапка снимала закон 32 в раунде 4.
        DOOR_FREE_CHANNELS = {"botreg"}   # цепочка регистрации: дверь выдаёт бот
        eff_class = (form_key[1] if form_key else None) or args.form_goal
        door_required = not (args.channel in DOOR_FREE_CHANNELS
                             or eff_class in ZERO_DOOR_ALWAYS
                             or (args.channel not in DOOR_CHANNELS
                                 and eff_class in ZERO_DOOR_OFFDOOR))
        door_tpl     = check_door_template(text)
        door_promise = check_door_promise(text)
        has_door = bool(n_doors or door_tpl or door_promise)
        door_kind = ("ссылка" if n_doors else
                     "шаблон %s" % door_tpl[0] if door_tpl else
                     "обещание «%s»" % door_promise if door_promise else "нет")

        link_defect = None
        if door_required and not has_door:
            link_defect = ("закон 32 (автор 5.08): единица класса '%s' на канале '%s' БЕЗ двери - "
                           "ни ссылки (включая t.me-инвайт), ни шаблона {ссылка_*}, ни датированного "
                           "обещания «ссылка появится здесь в 18:00». Право выйти без двери даёт "
                           "КАНАЛ+КЛАСС, а не --form-goal из шапки: класс razbor - на любом канале, "
                           "narrative/gate - только вне каналов с дверью (%s), канал botreg - всегда"
                           % (eff_class, args.channel, "/".join(sorted(DOOR_CHANNELS))))
        elif door_required:
            print(f"[PASS] закон 32: дверь есть ({door_kind}), класс '{eff_class}' канал '{args.channel}'")
        else:
            print(f"[PASS] закон 32: класс '{eff_class}' на канале '{args.channel}' "
                  f"вправе выйти без двери (дверь: {door_kind})")

        if link_defect:
            pass
        elif args.form_goal == "reactions" and form_key[1] == "narrative":
            if n_links > 0:
                link_defect = (f"форма-профиль R-нарратив: ссылок {n_links} "
                               f"(норма 0, HARD 89% верха, канон §9 R-3)")
            else:
                print("[PASS] форма-профиль R-нарратив: ссылок 0")
        elif args.form_goal == "reactions" and form_key[1] == "razbor":
            ltag = "WARN" if n_links > 0 else "PASS"
            print(f"[{ltag}] форма-профиль R-разбор: ссылок {n_links} (желателен 0, не блок — 67% верха, канон §9 R-3)")
        elif args.form_goal == "forwards":
            if n_links == 0:
                link_defect = "форма-профиль F: ссылка обязательна, найдено 0 (канон §9 F-2, 92% верха)"
            else:
                print(f"[PASS] форма-профиль F: ссылка есть ({n_links} вхожд.); повтор адреса {dup} "
                      f"(вреда не показано, канон §1)")
        elif args.form_goal == "sales":
            # закон 32 отсюда вынесен наверх, в матрицу канал×класс (Д18, К3):
            # здесь остаётся ТОЛЬКО форма S - сколько РАЗНЫХ продающих адресов
            if n_unique > 1:
                link_defect = (f"форма-профиль S: якорей на {n_unique} разных адреса — держат 0/1 адрес "
                               f"у 91% верха (канон §9 S-4)")
            elif dup >= 2:
                print(f"[WARN] форма-профиль S: повтор одного адреса {dup}× (канон §9 S-4, 2/34 против 7/34)")
            else:
                print(f"[PASS] форма-профиль S: якорей {n_links} (0 или 1 адрес)")
        elif args.form_goal == "gate":
            if n_links > 0:
                link_defect = (f"форма-профиль A: ссылок в гейте быть не должно, "
                               f"найдено {n_links} (канон §9 режим A п.1)")
            else:
                print("[PASS] форма-профиль A: ссылок 0")
        if link_defect:
            hard_fail = True
            print(f"[FAIL] {link_defect}")

        # медиана слов в предложении — HARD-пол только там, где измерено (R-разбор)
        if form_profile.get("sentence_median_min") is not None:
            med = check_sentence_median(text)
            floor = form_profile["sentence_median_min"]
            if med is not None and med < floor:
                hard_fail = True
                print(f"[FAIL] форма-профиль {form_profile['label']}: медиана слов в предложении "
                      f"{med} < {floor} (канон §9 R-10)")
            else:
                print(f"[PASS] форма-профиль {form_profile['label']}: медиана слов в предложении {med}")

        # цифра в хуке — желательна в F (WARN, не блок; канон §9 F-6)
        if form_profile.get("hook_digit_required"):
            has_digit = check_hook_digit(paragraphs)
            ltag = "PASS" if has_digit else "WARN"
            print(f"[{ltag}] форма-профиль {form_profile['label']}: цифра в хуке "
                  f"{'есть' if has_digit else 'нет'} (желательно, 63% против 20%, канон §9 F-6)")

    # 4.1.6.7 большие абзацы (WARN: простыня = брак, прецедент по решению автора 'не Лев Толстой')
    long_p = check_long_paragraphs(paragraphs)
    if long_p:
        hard_fail = True
        print(f"[FAIL] 4.1.6.7 большие абзацы: {len(long_p)} абз. > 250 симв. "
              f"(замер доноров: медиана 78, q3 110, p95 167; длиннее 250 - 0.8% абзацев)")
        for idx, ln in long_p:
            print(f"        абзац {idx}: {ln} симв.")
    else:
        print(f"[PASS] 4.1.6.7 большие абзацы (0/{len(paragraphs)} > 250 симв.)")

    # рубленые фразы (HARD: 3+ подряд предложений из 1-2 слов = staccato AI-tic)
    choppy = check_choppy_sentences(text)
    if choppy >= 3:
        # 🔴 4c: HARD СНЯТ до WARN как мёртвый дубль. Замер по всему корпусу
        # фикстур (91 файл: 12 green-ivan + 10 донор-эталонов + 47 red-classes
        # + 22 старых red): правило не сработало НИ РАЗУ. Тот же класс «рубка/
        # staccato» реально ловят два соседних правила, которые срабатывают -
        # check_line_stacking (3 раза) и check_stub_sentences (2 раза).
        # Третий блокирующий вход в один класс держал бюджет и ничего не ловил.
        print(f"[WARN] рубленые фразы: {choppy} подряд предложений из 1-2 слов "
              f"(staccato — AI-tic). Сшей в цельные предложения; блокируют этот класс "
              f"«рубка строка-на-фразу» и «обрубки-нейрослоп» ниже")
    else:
        print(f"[PASS] рубленые фразы: макс. серия коротких предложений = {choppy}")
    print("        NB: тонкую рубку (точка вместо запятой) ловит только humaniser.")

    # рубка «строка-на-фразу» (HARD: лесенка коротких строк = AI-почерк, прецедент по решению автора)
    stacking = check_line_stacking(paragraphs)
    if stacking:
        hard_fail = True
        print(f"[FAIL] рубка 'строка-на-фразу': {len(stacking)} абз. дроблены на столбик "
              f"коротких строк (AI-почерк). Сшей в цельные предложения и абзацы-прозу.")
        for idx, nlines, mlen in stacking:
            print(f"        абзац {idx}: {nlines} строк, средняя {mlen} симв.")
    else:
        print("[PASS] рубка 'строка-на-фразу': лесенки коротких строк нет")

    # обрубки-нейрослоп (HARD: одиночное предложение из 1 слова = акцент-AI-tic)
    stubs = check_stub_sentences(paragraphs)
    if stubs:
        hard_fail = True
        print(f"[FAIL] обрубки-нейрослоп: {len(stubs)} одиночн. предложений из 1 слова "
              f"({', '.join(repr(s) for s in stubs)}) — впиши в предложение или убери.")
    else:
        print("[PASS] обрубки-нейрослоп: одиночных предложений из 1 слова нет")

    # 🔒 ЛИЧНЫЕ ЗАПРЕТЫ ВЛАДЕЛЬЦА (HARD). Слова, регексы, названия и обоснования
    # живут во внешнем словаре (см. шапку модуля), здесь только механика печати.
    # Нет словаря (машина ученика) -> списки пусты -> все строки [PASS] с нулём.
    def _report_owner_ban(entry_id, hits, default_label):
        nonlocal_label = owner_banned_label(entry_id, default_label)
        if hits:
            note = owner_banned_note(entry_id)
            tail = f" ({note})" if note else ""
            print(f"[FAIL] {nonlocal_label}: {len(hits)} наруш.{tail}")
            for frag in hits:
                print(f"        ...{frag}...")
            return True
        print(f"[PASS] {nonlocal_label} (0)")
        return False

    if _report_owner_ban("dev_objection", check_banned_dev_objection(text),
                         "личный запрет класса возражений"):
        hard_fail = True

    if not args.allow_marathon:
        if _report_owner_ban("marathon", check_banned_marathon(text),
                             "личный запрет слова события"):
            hard_fail = True

    if not args.allow_perelivN:
        if _report_owner_ban("perelivN", check_banned_perelivN(text),
                             "личный запрет снятого концепта"):
            hard_fail = True

    if not args.allow_instrument:
        if _report_owner_ban("instrument_naming", check_banned_category_word(text),
                             "личный запрет категории-слова вместо имени"):
            hard_fail = True

    if not args.allow_cta_bridge:
        if _report_owner_ban("cta_bridge", check_banned_cta_bridge(text),
                             "личный запрет подводки-мостика перед оффером"):
            hard_fail = True

    # СТОЛКНОВЕНИЕ ОБРАЗОВ (WARN — прецедент по решению автора: три «руки» в одном посте,
    # две завезены точечными правками; метафора не исчезает, а мигрирует)
    collisions = check_image_collision(text)
    if collisions:
        for label, found in collisions:
            print(f"[WARN] столкновение образов: «{label}» — {len(found)} вхождений")
            for ln, frag in found:
                print(f"        строка {ln}: {frag}")
        print("        один корень в разных значениях = навязчивость; оставь ОДНО самое точное")
    else:
        print("[PASS] столкновения образов нет (один корень-метафора не повторён 3+ раз)")

    # ПОВТОР ЗАЧИНА СОСЕДНИХ АБЗАЦЕВ (WARN — прецедент по решению автора: два абзаца подряд с «А»)
    openers = check_paragraph_openers(paragraphs)
    if openers:
        for a, b, w in openers:
            print(f"[WARN] абзацы {a} и {b} начинаются одинаково: «{w}» — переформулируй один")
    else:
        print("[PASS] соседние абзацы начинаются по-разному")

    # ХУК: премиум-эмодзи + пробел + жирный заголовок (HARD — владелец)
    # 🔴 4c: HARD СНЯТ до WARN. Это правило валило БОЛЬШЕ ВСЕХ - 30 срабатываний
    # на 91 файле корпуса и, главное, 6 из 12 постов green-ivan, которые автор
    # считает эталонными: сам эталон 6.08 (etalon-0608 начинается «💎 Сегодня в
    # 19:00…» без жирного), inf18-0608, e17-0508 и все три финала ivan-final-*.
    # 50% падения green при пороге закона калибровки 20%. Канон п.36 требует,
    # чтобы заголовок был ВЫДЕЛЕН, а форма выделения - «по назначению» (п.38
    # прямо: «эмодзи не обязателен вообще»). Правило требовало одной формы там,
    # где канон требует разных, поэтому оно показывает, а не блокирует.
    hook_defect = check_hook_premium_emoji(text)
    if hook_defect:
        why = f" (снято флагом: {args.allow_no_premium_hook})" if args.allow_no_premium_hook else ""
        print(f"[WARN] хук-эмодзи: {hook_defect}{why}")
        print("        форма по решению автора «эмодзи + пробел + жирный заголовок» - ОДНА из "
              "рабочих, а не единственная (канон п.38: эмодзи не обязателен, CAPS максимум "
              "у одного поста в дне). Обязательно только само выделение заголовка (п.36)")
    else:
        print("[PASS] хук-эмодзи: эмодзи + пробел + жирный заголовок")

    # ДВА ЖИРНЫХ БЛОКА ПОДРЯД (HARD — владелец: акцент размывается).
    # 4c: правило поста НЕ применяется к письму. Улика: green-ivan/e17-0508.txt -
    # это ЕМАЙЛ (несёт блоки **SUBJECT** и **PREHEADER**, они физически стоят
    # двумя жирными блоками подряд), и он падал HARD на структуре формата,
    # а не на дефекте текста. Канон п.43 описывает воздух ПОСТА (структура
    # донора Донор-Б), email в п.45 идёт отдельной строкой таблицы.
    _is_email = args.channel == "email" or bool(
        re.search(r"(?m)^\s*\*{0,2}(SUBJECT|PREHEADER)\b", text))
    dbl_bold = check_consecutive_bold_blocks(text)
    if dbl_bold and _is_email:
        print(f"[INFO] два жирных абзаца подряд: {len(dbl_bold)} пар - не проверяется "
              f"у единицы-письма (SUBJECT/PREHEADER стоят жирными блоками по формату)")
    elif dbl_bold:
        hard_fail = True
        print(f"[FAIL] два жирных абзаца подряд: {len(dbl_bold)} пар (владелец: "
              "«не выделяй никогда» - непонятно, на что акцент)")
        for a, b in dbl_bold:
            print(f"        «{a}» + «{b}»")
    else:
        print("[PASS] жирные блоки не соседствуют")

    # 4c/F8 (канон п.77): у письма ровно один Subject. HARD.
    _subjects = check_email_subjects(text)
    if len(_subjects) > 1:
        hard_fail = True
        print(f"[FAIL] email: Subject-блоков {len(_subjects)}, должен быть РОВНО ОДИН "
              f"(канон п.77, правка владельца  п.16). Варианты на выбор = не доделанная "
              f"работа: выбор делает движок, а не читатель ТЗ")
        for s in _subjects:
            print(f"        {s}")
    elif _subjects:
        print("[PASS] email: Subject ровно один (канон п.77)")

    # ЭМОЦИОНАЛЬНАЯ ПАЛИТРА (INFO — видимость, НЕ квота; владелец)
    caps, stretch = report_emotional_palette(text)
    print(f"[INFO] эмоц. палитра: капс-слов {len(caps)}"
          f"{' (' + ', '.join(caps[:3]) + ')' if caps else ''}, растянутых гласных {len(stretch)}. "
          "Квоты нет - но если по всему посту ноль и пост эмоциональный, подумай про "
          "КАПС-слово / растяжку («ПОЕЕЕЕХАЛИИИ!»). Подчёркивание НЕ предлагать - "
          "rich-слой снят по решению автора, формат донорский")

    # СКЕЛЕТ vs последние выдачи канала (HARD — прецедент по решению автора)
    sig = extract_skeleton(text)
    # 🔴 ИСКЛЮЧЕНИЕ САМОГО СЕБЯ (фикс скептик-раунда 3, БЛОКЕР 2, по решению автора).
    # Записи журнала с ТЕМ ЖЕ слагом, что логируется сейчас (--log-skeleton SLUG),
    # из сравнения выбрасываются: иначе повторный прогон по тому же посту ловит
    # собственную вчерашнюю/предыдущую запись и печатает FAIL «скелет идентичен»
    # сам с собой, а при FAIL журналы вообще не пишутся - то есть один лишний
    # прогон навсегда запирал запись обоих журналов. До этого фикса лечилось
    # РУКАМИ (05-publish: «строку черновика удалить из журнала перед финальной
    # записью») - теперь лечится кодом.
    prev_entries = [e for e in load_skeleton_log(args.skeleton_log, args.channel)
                    if not (args.log_skeleton and e.get("slug") == args.log_skeleton)][-5:]
    sig_str = "→".join(sig)
    if not prev_entries:
        print(f"[WARN] скелет: журнал канала '{args.channel}' пуст ({args.skeleton_log}) - "
              f"сравнить не с чем. Текущий: {sig_str}")
    else:
        conflicts = []
        for e in prev_entries:
            verdict = skeleton_conflict(sig, e.get("skeleton", []))
            if verdict:
                conflicts.append((e, verdict))
        if conflicts:
            level = "WARN" if args.allow_skeleton_repeat else "FAIL"
            if not args.allow_skeleton_repeat:
                hard_fail = True
            print(f"[{level}] скелет повторяет прошлую выдачу канала '{args.channel}':")
            for e, verdict in conflicts:
                print(f"        {verdict} с {e.get('date')}/{e.get('slug')}: "
                      f"{'→'.join(e.get('skeleton', []))}")
            print(f"        текущий: {sig_str}")
            if args.allow_skeleton_repeat:
                print(f"        разрешено: {args.allow_skeleton_repeat}")
            else:
                print("        перестрой порядок блоков ПОСЛЕ заголовка (хук закреплён: эмодзи+жирный):"
                      " вторым блоком сцена/прямая речь/цитата вместо курсив-строки,"
                      " список↔абзацы, сместить список вглубь - факты и голос не трогать")
        else:
            print(f"[PASS] скелет отличается от последних {len(prev_entries)} выдач "
                  f"канала '{args.channel}': {sig_str}")

    # 🔴 ЗАПИСЬ СКЕЛЕТА ОТЛОЖЕНА В КОНЕЦ ПРОГОНА (фикс скептик-раунда 3, БЛОКЕР 2,
    # по решению автора). Раньше она стояла ровно здесь - то есть решение «пост выдан»
    # принималось по hard_fail, набранному только гейтами ВЫШЕ по файлу; все v2.0
    # гейты (вода, анти-паттерны, факт-база, цена, плейсхолдеры) идут НИЖЕ. Пост,
    # заваливший факт-базу, всё равно оставлял скелет в журнале, а якорь - нет:
    # журналы расходились, и один прогон с обоими флагами давал половинчатую
    # запись. Обе записи теперь живут рядом в конце и подчиняются ФИНАЛЬНОМУ
    # hard_fail - см. блок «ЖУРНАЛЫ» перед ИТОГом.

    # =========================================================================
    # v2.0 ГЕЙТЫ (Z1, спека 2026-08-04-post-skill-v2.md, «Слои кода»)
    # =========================================================================
    print("-" * 56)
    print("v2.0: вода / обороты / анти-паттерны / плейсхолдеры / факт-база")
    print("-" * 56)

    # --- ВОДА (AC2, класс R2-1). R3 §C: KANC/CLICHE HARD 0, EVAL/INTENS/сумма
    # потолок WARN (R3 предупреждение 1 - не разделяющий гейт силы).
    water = check_water(text)
    if water["kanc_hits"]:
        hard_fail = True
        print(f"[FAIL] вода-канцелярит (WATER_KANC): {water['kanc_k']:.2f}/1000 (потолок 0, R3 §C HARD) "
              f"- {', '.join(water['kanc_hits'][:5])}")
    else:
        print("[PASS] вода-канцелярит (WATER_KANC): 0/1000")
    if water["cliche_hits"]:
        hard_fail = True
        print(f"[FAIL] нейросетевые связки (AI_CLICHE): {water['cliche_k']:.2f}/1000 (потолок 0, R3 §C HARD) "
              f"- {', '.join(water['cliche_hits'][:5])}")
    else:
        print("[PASS] нейросетевые связки (AI_CLICHE): 0/1000")
    if water["eval_k"] > 1.2:
        print(f"[WARN] вода-оценочность (WATER_EVAL): {water['eval_k']:.2f}/1000 > потолок 1.2 "
              f"(R3 §C - потолок против генератора, не разделяющий гейт) - {', '.join(water['eval_hits'][:5])}")
    else:
        print(f"[PASS] вода-оценочность (WATER_EVAL): {water['eval_k']:.2f}/1000 (потолок 1.2)")
    if water["intens_k"] > 1.7:
        print(f"[WARN] вода-усилители (WATER_INTENS): {water['intens_k']:.2f}/1000 > потолок 1.7 (R3 §C) "
              f"- {', '.join(water['intens_hits'][:5])}")
    else:
        print(f"[PASS] вода-усилители (WATER_INTENS): {water['intens_k']:.2f}/1000 (потолок 1.7)")
    # --- ВОДА СУММАРНО. Двухуровневый гейт (п.8 скептик-раунда 2, по решению автора).
    # Было: только WARN на 2.5 - воде не хватало зубов, 03-dry мог отработать вхолостую
    # («снято 0») и пост с водой всё равно выдавался.
    # ADMISSION-ТЕСТ на живом корпусе R3 (нарезка _scope.md, файлы ER_B/ER_C/ER_D/FWD *_TOP.md,
    # 132 поста верхних квартилей, словари - те же, что в check_water):
    #   медиана sum_k 0.68/1000 · p75 1.47 · максимум 6.54
    #   > 2.0/1000 - 21/132 (15.9%) · > 2.5 - 15/132 (11.4%) · > 3.0 - 7/132 (5.3%)
    #   по классам >3.0: B-TOP 3/27 (11.1%), C-TOP 1/12 (8.3%), D-TOP 1/34 (2.9%), FWD-TOP 2/59 (3.4%)
    #   контроль, нижние квартили: >3.0 - 9/132 (6.8%)
    # 5.3% верха < допустимых 20% → порог 3.0 admission-safe, HARD ставится.
    # 2.5 остаётся WARN-целью канона (R3 §C) и целью итерации 03-dry.
    if water["sum_k"] > 3.0:
        hard_fail = True
        print(f"[FAIL] вода суммарно: {water['sum_k']:.2f}/1000 > HARD-потолок 3.0 (R3 §C; "
              f"admission на верхних квартилях R3: превышают 5.3%). Вернись в 03-dry и сними "
              f"воду - выдача с такой плотностью запрещена")
    elif water["sum_k"] > 2.5:
        print(f"[WARN] вода суммарно: {water['sum_k']:.2f}/1000 > потолок-цель 2.5 (R3 §C), "
              f"HARD-порог 3.0 не превышен")
    else:
        print(f"[PASS] вода суммарно: {water['sum_k']:.2f}/1000 (цель 2.5, HARD 3.0)")

    # --- БАНК НЕСУЩЕСТВУЮЩИХ ОБОРОТОВ (AC3, класс R2-5). HARD.
    # 4c: сюда же влит класс D3 «выдуманная связка глагол+существительное»
    # (канон п.57, «гонять можно собак»). Это тот же закон «языка, которого
    # нет», что и метафора-подмена D2, поэтому один блокирующий вход, а не два.
    banned_col = check_banned_collocations(text) + check_invented_verb_noun(text)
    if banned_col:
        hard_fail = True
        print(f"[FAIL] несуществующие словосочетания/метафоры-подмены: {len(banned_col)} наруш. "
              f"(AC3 + канон п.57, memory feedback_no_invented_collocations_plain_words_only.md)")
        for why, frag in banned_col:
            print(f"        {why}: ...{frag}...")
    else:
        print("[PASS] банк несуществующих оборотов (0) - новые подмены проверяет независимый верификатор")

    # --- 4c/D1 МЕТАФОРЫ-КОРНИ (канон п.49). HARD, снимается --allow-metaphor.
    meta_hits = check_metaphor_roots(text)
    if meta_hits and args.allow_metaphor:
        print(f"[WARN] метафоры (канон п.49): {len(meta_hits)} наруш., понижено флагом "
              f"--allow-metaphor (причина: {args.allow_metaphor})")
        for label, frag in meta_hits[:5]:
            print(f"        «{label}»: ...{frag}...")
    elif meta_hits:
        hard_fail = True
        print(f"[FAIL] метафоры (канон п.49): {len(meta_hits)} наруш. Владелец 6.08: «поменять "
              f"можно штаны. Механика поменять - это метафора» · «в ноль нельзя уйти» · "
              f"«дешёвая дверь - непонятный набор звуков». Тест каждого предложения: это "
              f"происходит ФИЗИЧЕСКИ БУКВАЛЬНО? Нет - переписать буквально")
        for label, frag in meta_hits[:8]:
            print(f"        «{label}»: ...{frag}...")
    else:
        print("[PASS] метафоры-корни (0; окрасочный эпитет РЯДОМ с конкретикой законен, "
              "канон п.49 - запрещён образ ВМЕСТО сущности)")

    # --- 4c/B20 ФИЛЛЕРЫ (канон п.35). HARD.
    fillers = check_fillers(text)
    if fillers:
        hard_fail = True
        print(f"[FAIL] филлеры: {len(fillers)} наруш. (канон п.35, владелец 6.08: «эта вещь не "
              f"несёт никакой пользы и ценности»). Каждое предложение несёт факт, действие, "
              f"цифру или вывод")
        for f in fillers[:5]:
            print(f"        ...{f}...")
    else:
        print("[PASS] филлеров нет (канон п.35)")

    # --- МЁРТВЫЙ ЯЗЫК: ЛЕКСИКА (антисловарь абстракций, владелец).
    # HARD, снимается --allow-dead-lexicon. Пара к блоку «мёртвые конструкции»
    # ниже: там синтаксис, здесь слова. Сообщение даёт ЖИВУЮ ЗАМЕНУ, а не
    # запрет - переписывать будет модель, и ей нужен целевой язык.
    dl = check_dead_language(text)
    _DL_OWNER = ("Владелец по решению автора: «Мы должны говорить на РЕАЛЬНОМ языке, на котором люди "
                 "пишут, говорят, спрашивают, комментарии пишут, думают, посты делают - а не "
                 "на абстрактном». Замер: этих слов НЕТ ни в 608 постах доноров, ни в 15 "
                 "финалах владельца, ни в 634 ответах аудитории")

    def _dl_print(items):
        for label, live, evid, frag in items[:8]:
            print(f"        «{label}» -> живой человек говорит: {live} ({evid})")
            print(f"          ...{frag}...")

    if dl["a"] and args.allow_dead_lexicon:
        print(f"[WARN] мёртвый язык (лексика): {len(dl['a'])} наруш. понижено флагом "
              f"--allow-dead-lexicon (причина: {args.allow_dead_lexicon})")
        _dl_print(dl["a"])
    elif dl["a"]:
        hard_fail = True
        print(f"[FAIL] мёртвый язык (лексика): {len(dl['a'])} наруш. {_DL_OWNER}. "
              f"Замена - references/zhivoy-yazyk.md разд.4 (не вычёркивать, а заменять)")
        _dl_print(dl["a"])
    else:
        print("[PASS] живой язык (0 абстракций из антисловаря TIER-A; "
              "замер: 0 вхождений на 1264 живых документа)")
    # Порог 2, плотностный. Максимум на живом корпусе 3 вхождения на пост
    # (donor-1558, 1432 знака), у владельца и green-фикстур 0.
    if dl["chars"] >= DEAD_LEX_MIN_CHARS and dl["total"] > DEAD_LEX_DENSITY_MAX:
        if args.allow_dead_lexicon:
            print(f"[WARN] плотность абстракций: {dl['total']} на {dl['chars']} зн. "
                  f"понижено флагом --allow-dead-lexicon (причина: {args.allow_dead_lexicon})")
        else:
            hard_fail = True
            print(f"[FAIL] плотность абстракций: {dl['total']} вхождений антисловаря на "
                  f"{dl['chars']} зн. (порог {DEAD_LEX_DENSITY_MAX + 1} при длине от "
                  f"{DEAD_LEX_MIN_CHARS}; максимум на 608 живых постах доноров = "
                  f"{DEAD_LEX_DENSITY_MAX}, у владельца и донор-эталонов = 0). "
                  f"Текст держится на свойствах вместо действий, цифр, сроков и предметов")
    # Порог 3: TIER-B и WARN поштучно, с заменой, без блокировки.
    for label, live, evid, frag in dl["b"][:6]:
        print(f"[WARN] мёртвый язык, TIER-B «{label}»: живой человек говорит {live} "
              f"({evid}) - ...{frag[:90]}...")
    for label, live, evid, frag in dl["warn"][:6]:
        print(f"[WARN] мёртвый язык, омонимия «{label}»: если это не метрика/настройка/"
              f"деталь продукта, живой человек говорит {live} - ...{frag[:90]}...")

    # --- 4c ЯРЛЫКИ-РУБРИКАТОРЫ (канон п.16). HARD на набор, названный автором
    # построчно (раунд 1, находка 5); снимается --allow-rubricator. Остальные
    # метки набора остаются WARN - см. докстринг check_rubricator_openers.
    rubr = check_rubricator_openers(paragraphs)
    rubr_hard = [r for r in rubr if r[3]]
    rubr_soft = [r for r in rubr if not r[3]]
    _RUBR_CANON = ("канон п.16 - смысловые слоты обязаны быть закрыты, но НЕ выведены "
                   "в текст рубрикой; разбор эталона 6.08 п.3: «никаких формульных блоков "
                   "«раньше/теперь», «на вход/на выходе», «что забрать сегодня», "
                   "«честная граница»»")
    if rubr_hard and args.allow_rubricator:
        print(f"[WARN] ярлыки-рубрикаторы в зачине абзаца: {len(rubr_hard)}, понижено флагом "
              f"--allow-rubricator (причина: {args.allow_rubricator})")
    elif rubr_hard:
        hard_fail = True
        print(f"[FAIL] ярлыки-рубрикаторы в зачине абзаца: {len(rubr_hard)} ({_RUBR_CANON})")
    for idx, mark, head, _h in rubr_hard:
        print(f"        абзац {idx}: «{mark}» - {head}")
    if rubr_soft:
        print(f"[WARN] ярлыки-рубрикаторы (эвристика, вне построчного перечня автора): "
              f"{len(rubr_soft)}")
        for idx, mark, head, _h in rubr_soft:
            print(f"        абзац {idx}: «{mark}» - {head}")
    if not rubr:
        print("[PASS] ярлыков-рубрикаторов нет (канон п.16)")

    # --- 4c/B19 ПЛОТНОСТЬ ИДЕЙ, НИЖНИЙ ПОРОГ (канон п.19). HARD.
    # 🔴 ПАРА ПОРОГОВ ОДНОЙ ЕДИНИЦЫ. Верхний потолок конкретики снят выше
    # (блок «конкретика по классу», см. комментарий 4c там же) - канон п.19
    # говорит «верхнего потолка нет». Здесь стоит второй порог той же
    # величины, нижний, и он единственный блокирующий. Раньше линтер имел
    # ТОЛЬКО верхний WARN 4.4/1000 и ловил эталон владельца (7.50) как «перебор»,
    # а брак с нулевой плотностью пропускал молча - знак был перевёрнут.
    dens = check_idea_density(text)
    if dens["k"] < IDEA_DENSITY_FLOOR_K and args.allow_low_density:
        print(f"[WARN] плотность идей: {dens['k']:.2f}/1000 < пола {IDEA_DENSITY_FLOOR_K}, "
              f"понижено флагом --allow-low-density (причина: {args.allow_low_density})")
    elif dens["k"] < IDEA_DENSITY_FLOOR_K:
        hard_fail = True
        print(f"[FAIL] плотность идей: {dens['k']:.2f} конкретики/1000 знаков < пола "
              f"{IDEA_DENSITY_FLOOR_K} (канон п.19, владелец 6.08: «в каждом посте 90% вырезать»; "
              f"эталон 6.08: «цифры и личные факты в каждом третьем предложении»). "
              f"Найдено: цифр {dens['nums']}, имён {dens['names']}, названий {dens['latin']}, "
              f"цитат {dens['quotes']} на {dens['chars']} знаков. Замер зелёного корпуса: "
              f"min 1.15 · медиана 6.99 · max 19.42")
    else:
        print(f"[PASS] плотность идей: {dens['k']:.2f} конкретики/1000 (пол "
              f"{IDEA_DENSITY_FLOOR_K}, верхнего потолка нет - канон п.19)")

    # --- 4c ПРИЧИННЫЕ СВЯЗКИ (канон п.42). HARD при нуле.
    causal_n = check_causal_links(text)
    if causal_n == 0:
        hard_fail = True
        print(f"[FAIL] содержательных причинных связок 0 (потому что / из-за / в результате / "
              f"за счёт / чтобы / иначе / если / когда). Абзацы стоят рядом, но не вытекают друг "
              f"из друга - канон п.42: «это несвязный набор лозунгов» (владелец). Замер: ни "
              f"один из 12 постов green-ivan и 10 донор-эталонов не идёт с нулём связок "
              f"(минимум 1). Выводные маркеры («поэтому», «значит», «так что») пол НЕ "
              f"закрывают - канон п.56")
    else:
        print(f"[PASS] содержательные причинные связки: {causal_n} (минимум по корпусу 1, "
              f"нужна хотя бы одна; канон п.42)")
    # --- канон п.56 (псевдо-причинная связка). Судейская ось: машина считает
    # маркеры и показывает их, улику на СВЯЗЬ ищет ревью, не код.
    infer = check_inferential_links(text)
    if infer:
        print(f"[INFO] выводных маркеров: {len(infer)} ({', '.join(sorted(set(infer)))}) - канон "
              f"п.56: на каждый нужна улика на СВЯЗЬ в факт-базе, а не на два факта по "
              f"отдельности. Ось судейская, машина её не решает")
    else:
        print("[INFO] выводных маркеров нет (канон п.56 нечего проверять)")

    # --- МЁРТВЫЕ КОНСТРУКЦИИ (анти-корпус К1-К11, владелец).
    # Живая половина закона - слепок конструкций в .business (см. шапку блока
    # детекторов выше). Здесь только машинная: синтаксис, который проходил
    # словарные гейты и всё равно читался мёртвым.
    dead = scan_dead_constructions(text)
    dead_hard = [d for d in dead if d[1] == "HARD"]
    dead_warn = [d for d in dead if d[1] == "WARN"]
    if dead_hard and args.allow_dead_lang:
        print(f"[WARN] мёртвые конструкции: {len(dead_hard)} HARD понижено флагом "
              f"--allow-dead-lang (причина: {args.allow_dead_lang})")
        for cls, _lvl, why, frag in dead_hard:
            print(f"        {cls} {why}: {frag[:120]}")
    elif dead_hard:
        hard_fail = True
        classes = sorted({d[0] for d in dead_hard}, key=lambda c: (len(c), c))
        print(f"[FAIL] мёртвые конструкции: {len(dead_hard)} наруш. в классах "
              f"{', '.join(classes)} (анти-корпус по решению автора; живые заготовки - слепок "
              f"voice-corpus/_konstrukcii-zhivogo-yazyka.md). Замер калибровки: "
              f"зелёный корпус автора 0/12, доноры 24/608, боевой пакет 41/87")
        for cls, _lvl, why, frag in dead_hard:
            print(f"        {cls} {why}: {frag[:130]}")
    else:
        print(f"[PASS] мёртвых конструкций нет (анти-корпус К1-К11, "
              f"{len(dead_warn)} WARN)")
    for cls, _lvl, why, frag in dead_warn:
        print(f"[WARN] мёртвая конструкция {cls}: {why} - {frag[:110]}")

    # --- К8 НА УРОВНЕ ПАКЕТА: серийный зачин датой. Работает только с --package.
    if args.package:
        _tot, _hits = dead_date_opener_share(args.package)
        if _tot:
            _share = len(_hits) / _tot
            if _share > DEAD_DATE_OPENER_PACKAGE_MAX and not args.allow_dead_lang:
                hard_fail = True
                print(f"[FAIL] К8 пакет: зачин датой в {len(_hits)} из {_tot} единиц "
                      f"({_share*100:.0f}% > порога {DEAD_DATE_OPENER_PACKAGE_MAX*100:.0f}%). "
                      f"Сцена с датой не обязана НАЧИНАТЬ пост - унеси дату внутрь абзаца. "
                      f"Замер: доноры 0.5%, зелёный корпус автора 8.3%")
                for fn, frag in _hits[:12]:
                    print(f"        {fn}: {frag}")
            else:
                print(f"[PASS] К8 пакет: зачин датой в {len(_hits)} из {_tot} единиц "
                      f"({_share*100:.0f}%, порог {DEAD_DATE_OPENER_PACKAGE_MAX*100:.0f}%)")

    # --- АНТИ-ПАТТЕРНЫ R3 (только при --form-goal, нужен form_class для scope)
    if form_profile is not None:
        ap_hard = []
        if ap1_promise_first_line(paragraphs):
            ap_hard.append("№1 обещание выгоды читателю в 1-й строке (местоимение+сумма)")
        if form_class == "narrative" and ap2_bez_stack(paragraphs):
            ap_hard.append("№2 стек «без X, без Y, без Z» в первых 2 строках нарратива")
        if ap3_service_seam(paragraphs):
            ap_hard.append("№3 служебный шов 2-й строкой («Что внутри:»...)")
        if ap5_quote_block_razbor(text, form_class):
            ap_hard.append("№5 цитатный блок > с выводом в разборе")
        if ap7_glossary_aside(text):
            ap_hard.append("№7 отступление-глоссарий («для тех, кто не в теме»)")
        if ap8_colon_rubric(text):
            ap_hard.append("№8 двоеточие-рубрикация («Погнали смотреть:»)")
        if ap9_smotret_caps(text):
            ap_hard.append("№9 СМОТРЕТЬ капсом")
        if form_class == "narrative" and ap13_final_door(paragraphs, form_class):
            ap_hard.append("№13 финал-дверь (ссылка/«жми» последней строкой) в нарративе")
        if ap14_enum_instead_thesis(text, form_class):
            ap_hard.append("№14 перечисление вместо тезиса в разборе (3-10 пунктов открывают пост)")
        if ap15_tire_enum_narrative(text, form_class):
            ap_hard.append("№15 тире-перечисление в нарративе")
        if ap17_round_metric_first(paragraphs):
            ap_hard.append("№17 крупная круглая метрика/«+» первым знаком поста")
        if ap_hard:
            hard_fail = True
            print(f"[FAIL] анти-паттерны R3 (0 случаев в TOP-корпусе доноров, покрытие ≥88% где применимо): "
                  f"{len(ap_hard)} наруш.")
            for a in ap_hard:
                print(f"        {a}")
        else:
            print("[PASS] анти-паттерны R3 №1/2/3/5/7/8/9/13/14/15/17 (0)")

        ap_warn = []
        no_verb = ap6_list_item_no_verb(text)
        if no_verb:
            ap_warn.append(f"№6 список без глаголов (существительные-ярлыки): {no_verb[:3]}")
        caps_n = ap20_caps_words(text, form_class)
        if caps_n >= 3:
            ap_warn.append(f"№20 капс-слов в нарративе: {caps_n} (потолок 3)")
        plita = ap21_plita(paragraphs)
        if plita:
            ap_warn.append(f"№21 плита 4+ строк: абзацы {[i for i, n in plita]}")
        if ap22_tail_showcase_bullets(paragraphs):
            ap_warn.append("№22 хвост-витрина с буллетами (список последним блоком)")
        if ap23_reproach(text):
            ap_warn.append("№23 наставление-упрёк")
        money_n = ap25_money_in_narrative(text, form_class)
        if money_n:
            ap_warn.append(f"№25 деньги в нарративе: {money_n} вхожд. (верх доноров 15% постов, R3 §B)")
        if form_class == "sales" and ap13_final_door(paragraphs, form_class):
            ap_warn.append("№13 финал-дверь в продаже - WARN, не HARD (downgrade: конфликтует с "
                            "законом владельца Sales Gate 4.S/UTM, launch-посты ОБЯЗАНЫ нести ссылку "
                            "в конце - см. докстринг ap13_final_door)")
        if ap_warn:
            print(f"[WARN] анти-паттерны R3 (WARN-класс, {len(ap_warn)}):")
            for a in ap_warn:
                print(f"        {a}")
        else:
            print("[PASS] анти-паттерны R3 №6/20/21/22/23/25 (0)")

        # --- КОНКРЕТИКА ПО КЛАССУ (R3 §B, предупреждение 3: знак от цели). WARN.
        conc = check_concreteness(text)
        if form_class == "narrative":
            # 🔴 4c: ВЕРХНИЙ ПОТОЛОК 4.4/1000 СНЯТ (был WARN «перебор конкретики
            # вредит близости»). Улика: эталон владельца 6.08 несёт 7.50 чисел/1000,
            # green-ivan/zakr18-den-06в даты запуска/1000, оба образцовые. Канон п.19
            # («в каждом посте 90% вырезать», «цифры и личные факты в каждом
            # третьем предложении») прямо говорит, что верхнего потолка нет -
            # правило ловило ровно то, что канон требует. Нижний порог той же
            # единицы стоит рядом, ниже по блоку (IDEA_DENSITY_FLOOR_K) - два
            # порога одной величины теперь согласованы и лежат в одном месте.
            print(f"[INFO] конкретика: чисел {conc['num_k']:.2f}/1000 (нарратив; верхнего "
                  f"потолка нет с 4c - канон п.19, эталон 6.08 несёт 7.50)")
        elif form_class == "forwards":
            if conc["num_k"] < 5.0:
                print(f"[WARN] конкретика: чисел {conc['num_k']:.2f}/1000 < 5.0 (носитель - верх доноров "
                      f"5-8.13/1000, низ 2.62, R3 §B)")
            else:
                print(f"[PASS] конкретика: чисел {conc['num_k']:.2f}/1000 (носитель, пол 5.0)")
        elif form_class == "razbor":
            if conc["tools_k"] > 0:
                print(f"[WARN] конкретика: перечисление инструментов {conc['tools_k']:.2f}/1000 (разбор - "
                      f"верх доноров ОБЪЯСНЯЕТ механизм вместо перечня, верх 33% постов vs низ 83%, R3 §B)")
            else:
                print("[PASS] конкретика: перечисления инструментов нет (разбор)")
        elif form_class == "sales":
            print(f"[INFO] конкретика: числа {conc['num_k']:.2f}/1000 - гейт НЕ вешаем (R3 §B: "
                  f"«конкретика не различает верх/низ у продажи», 7.74 vs 7.71)")

        # --- АБЗАЦЫ-АБСТРАКЦИИ (AC2 доп., класс R2-1-b, раунд 9 ДЕФЕКТ 2). WARN.
        # Только razbor/sales - см. ADMISSION в докстринге check_paragraph_substance
        # (narrative исключён: у B-TOP-доноров абстрактный абзац - норма жанра).
        subst = check_paragraph_substance(paragraphs, form_class)
        if subst is not None:
            if subst["warn"]:
                print(f"[WARN] абзацы-абстракции: {len(subst['abstract'])}/{subst['total']} "
                      f"({subst['share']*100:.0f}%) абзацев длиннее {SUBSTANCE_LONG_PARA_LEN} знаков "
                      f"без конкретика-токена (цифра/деньги/ссылка/цитата «»/латиница/имя собственное) "
                      f">= порог {int(SUBSTANCE_SHARE_WARN*100)}% (AC2 доп. - живой брак владельца "
                      f"«показываю что у меня стоит, потому что дыра эта общая» = 0 совпадений со "
                      f"словарями воды, вердикт владельца «0 ценности просто вода»; словарь ловит плохие "
                      f"слова, эта проверка - отсутствие фактов)")
                for p in subst["abstract"][:3]:
                    print(f"        ...{p[:100].replace(chr(10), ' ')}...")
            elif subst["total"]:
                print(f"[PASS] абзацы-абстракции: {len(subst['abstract'])}/{subst['total']} "
                      f"({subst['share']*100:.0f}%) < порог {int(SUBSTANCE_SHARE_WARN*100)}%")
            else:
                print("[PASS] абзацы-абстракции: длинных абзацев (>120 знаков) нет")

        # --- ВОЗДУХ / МЕДИАНА СТРОК / МОНОТОННОСТЬ (R3 §A/§E). WARN.
        if form_class in ("narrative", "razbor"):
            air = check_air(text)
            if air < 0.65:
                print(f"[WARN] воздух: {air:.2f} < пол 0.65 (R3 §A, донор-медиана 0.86/0.87)")
            else:
                print(f"[PASS] воздух: {air:.2f} (пол 0.65)")
        med_lines = check_paragraph_line_median(paragraphs)
        if med_lines > 2:
            print(f"[WARN] медиана строк в абзаце: {med_lines} > 2 (донор-медиана 1.00, R3 §A - "
                  f"нижний квартиль доноров = абзац из 3-4 строк)")
        else:
            print(f"[PASS] медиана строк в абзаце: {med_lines} (донор-медиана 1.00)")
        spread = check_sentence_monotony(text)
        if spread is not None and spread < 6:
            print(f"[WARN] монотонность предложений: размах {spread} слов < 6 (R3 §E - разброс 2-25 "
                  f"внутри поста, ровный поток = генератор)")
        elif spread is not None:
            print(f"[PASS] разброс длины предложений: {spread} слов (R3 §E разброс 2-25)")

        # =====================================================================
        # ВОЛНА 15: ритм в СЛОВАХ + живой слой + механика класса
        # (топ-3 находки судьи бенчмарка по решению автора). Все пороги - с admission
        # на 7 донорах + 3 финалах владельца, см. докстринги функций.
        # =====================================================================
        rh = check_rhythm_words(text)
        if rh is not None:
            med = rh["median"]
            if med > W15_SENT_MEDIAN_HARD:
                hard_fail = True
                print(f"[FAIL] ритм: медиана {med:.1f} слов в предложении > HARD-потолка "
                      f"{W15_SENT_MEDIAN_HARD} (доноры: нарратив 9-13, разбор 11, продажа 4.5-5; "
                      f"максимум green-корпуса 13.0). Это синтаксис генератора - режь длинные "
                      f"предложения на два, границу считаем и по переносу строки")
            elif med > W15_SENT_MEDIAN_WARN:
                print(f"[WARN] ритм: медиана {med:.1f} слов в предложении > потолка доноров "
                      f"{W15_SENT_MEDIAN_WARN} (HARD с {W15_SENT_MEDIAN_HARD}); мин {rh['min']} / "
                      f"макс {rh['max']} слов на {rh['n']} предложений")
            else:
                print(f"[PASS] ритм: медиана {med:.1f} слов в предложении (потолок доноров "
                      f"{W15_SENT_MEDIAN_WARN}); мин {rh['min']} / макс {rh['max']} / {rh['n']} предл.")
            if rh["punch"] < W15_PUNCH_MIN_COUNT:
                print(f"[WARN] ударных предложений (<= {W15_PUNCH_MAX_WORDS} слов): {rh['punch']} < "
                      f"{W15_PUNCH_MIN_COUNT} (у доноров 0-25, медиана 4; минимальное предложение "
                      f"донора 1-3 слова). Короткая реплика держит темп - добавь хотя бы две")
            else:
                print(f"[PASS] ударных предложений (<= {W15_PUNCH_MAX_WORDS} слов): {rh['punch']} "
                      f"(минимум {W15_PUNCH_MIN_COUNT})")

        cpl = check_chars_per_line(text)
        ceil_cpl = W15_CPL_CEIL.get(form_class)
        if cpl is not None and ceil_cpl:
            if cpl > ceil_cpl:
                print(f"[WARN] знаков на строку: медиана {cpl:.0f} > потолка {ceil_cpl} "
                      f"(доноры: нарратив/разбор 55-89, продажа 21-33; потолок = верх доноров "
                      f"+30%). Статус WARN и не выше: собственные финалы владельца держат 174-243, "
                      f"он пишет абзацем там, где донор пишет репликой - гейт печатает факт, "
                      f"решение за автором")
            else:
                print(f"[PASS] знаков на строку: медиана {cpl:.0f} (потолок {ceil_cpl})")

        glue = check_glue_density(text)
        if glue is None:
            print(f"[INFO] клей («, а » + «который»): пост короче {W15_GLUE_MIN_WORDS} слов - "
                  f"плотность не меряется (шум малой выборки)")
        elif glue["k"] > W15_GLUE_WARN_K:
            print(f"[WARN] клей: {glue['k']:.1f}/1000 слов > порога {W15_GLUE_WARN_K} "
                  f"(«, а » ×{glue['glue_a']} + «который» ×{glue['kotor']} на {glue['words']} слов; "
                  f"максимум green-корпуса 17.9). Предложение растёт присоединением, а не новой "
                  f"мыслью - рви на самостоятельные")
        else:
            print(f"[PASS] клей: {glue['k']:.1f}/1000 слов (порог {W15_GLUE_WARN_K}; "
                  f"«, а » ×{glue['glue_a']} + «который» ×{glue['kotor']})")

        oral = check_oral_layer(text)
        oral_present = [f"{k} ×{v}" for k, v in oral.items() if v > 0]
        # Правка владельца п.20 (в даты запуска) + 5.08: предэфирный ПУШ (короткое
        # каскадное звено <=700 зн) - «чистая конкретика без приёмов», знаки
        # устной речи там не требуются; владелец 5.08 отдельно ругал «))» возле
        # призыва. Для пушей живой слой = WARN, не блок.
        # Порядок проверки (подэтап 4-0, по решению автора): явный escape-клапан идёт ПЕРВЫМ,
        # а карв-аут пуша применяется только к единице БЕЗ объявленного класса
        # формы - раньше он гасил HARD у объявленного разбора/нарратива короче
        # 700 зн и делал причину понижения неразличимой в выводе.
        if not oral_present and args.allow_no_oral:
            print(f"[WARN] живой слой: ни одного знака устной речи, понижено до WARN флагом "
                  f"--allow-no-oral (причина: {args.allow_no_oral})")
        elif not oral_present and form_class is None and len(_strip_md_plain(text)) <= 700:
            print("[WARN] живой слой: пуш <=700 зн без знаков устной речи - "
                  "штатно для чистого пуша явки (правка 20), не блок")
        elif not oral_present:
            hard_fail = True
            print(f"[FAIL] живой слой: ни одного знака устной речи (скобка ))/многоточие/вопрос/"
                  f"частица ну-вот-короче-блин-прям-ребят). Требование для ВСЕХ классов - "
                  f"10/10 донор-эталонов и финалов владельца несут хотя бы один знак, а разборы "
                  f"бенчмарк-серии вышли мёртвыми и это никто не поймал")
        else:
            print(f"[PASS] живой слой: {', '.join(oral_present)}")

        if form_class == "sales":
            showcase, why = check_showcase_hook(paragraphs, args.hero)
            if showcase:
                print(f"[WARN] витрина вместо квитанции: {why}. Верх доноров открывает продажу "
                      f"фактом про себя («[+3 оплаты ночью]» -> «Я сплю - продажи идут.»), "
                      f"а не именем продукта")
            elif args.hero:
                print(f"[PASS] хук не витрина{': ' + why if why else ''}")
            else:
                print("[INFO] витрина-хук: --hero не передан, гейт не применялся")

        # =================================================================
        # Д8: ГЕЙТЫ КЛАССА `event` (карта 12 гейтов E3 - в блоке над
        # check_dens_ratio; там же перечислено, что осталось текстом 04-review).
        # =================================================================
        if form_class == "event":
            # 4.DENS (04-review sub-stage 4.DENS): порог события 3.0, HARD.
            # Это ЕДИНСТВЕННОЕ мерило качества событийного поста (канон п.17):
            # долю скилла с него требовать запрещено, значит гейт плотности -
            # не довесок, а замена выключенного 4.V.
            _ed = check_dens_ratio(text)
            _dens_str = (f"S={_ed['S']} D={_ed['D']} density="
                         f"{'∞' if _ed['D'] == 0 else format(_ed['density'], '.2f')} "
                         f"порог={EVENT_DENS_MAX} (класс event)")
            if _ed["density"] > EVENT_DENS_MAX:
                hard_fail = True
                print(f"[FAIL] 4.DENS плотность идей: {_dens_str} - на один носитель "
                      f"конкретики приходится больше {EVENT_DENS_MAX} предложений. У события "
                      f"доля скилла не меряется вообще (04-review B1c), поэтому плотность и "
                      f"есть мерило: цифра, имя, название или личный факт минимум в каждом "
                      f"третьем предложении (канон п.19 + эталон 6.08). Разбивка носителей: "
                      f"цифр {_ed['nums']}, имён {_ed['names']}, названий {_ed['latin']}, "
                      f"цитат {_ed['quotes']}, сроков {_ed['datewords']}, "
                      f"артефактов {_ed['artifacts']} (служебная launch-строка не в счёт, "
                      f"канон п.18)")
            else:
                print(f"[PASS] 4.DENS плотность идей: {_dens_str}")

            # Признак класса (0.49-E): дата или время события в теле. HARD.
            _when = check_event_datetime(text)
            if not _when:
                hard_fail = True
                print(f"[FAIL] событие без даты и времени: класс объявлен event, а в теле нет "
                      f"ни времени (19:00), ни даты, ни «сегодня/завтра», ни дня недели. "
                      f"Признак класса из 01-router 0.49-E: «в посте названы дата или время "
                      f"события»; 02d требует время в первой строке (эталон 6.08 «Сегодня в "
                      f"19:00»). Класс без своего признака = уход от порога доли скилла - "
                      f"либо назови время события, либо верни класс sales/razbor")
            else:
                print(f"[PASS] событие названо во времени: {', '.join(_when[:6])}")

            # Запрещённые классу launch-элементы держат безусловные гейты ниже
            # по этому же прогону (цена цифрой · домашка и второе действие ·
            # отложенное обещание · перечисление программы) - дублировать их
            # веткой класса нельзя, иначе два входа на один закон.
            print("[INFO] класс event: доля скилла НЕ меряется (04-review B1c); "
                  "запрещённые классу launch-элементы держат безусловные гейты "
                  "«цена цифрой», «действие-читателю мимо регистрации», «отложенное "
                  "обещание», «перечисление программы» ниже; текстом 04-review "
                  "остаются 4.ET, W15-цепь, 4.R, Checklist A-F, 4.M.2")

    # --- RICH-РАЗМЕТКА ЗАПРЕЩЕНА (правка владельца ). HARD, безусловно
    # (не под --form-goal: формат выдачи один для всех целей и классов).
    rich_hits = check_no_rich_entities(text)
    if rich_hits:
        hard_fail = True
        print(f"[FAIL] rich-разметка запрещена, формат = донорский: {len(rich_hits)} класс(ов)")
        for label, detail in rich_hits:
            print(f"        {label}: {detail}")
        print("        разрешено ровно: чистый текст, эмодзи + **жирный заголовок целиком**,")
        print("        жирные акценты по профилю цели, точечный курсив, воздух, скобки-улыбки")
    else:
        print("[PASS] rich-разметка (0: ни таблиц, ни чек-боксов, ни H1-H6, ни спойлеров, "
              "ни highlight, ни подчёркиваний, ни центрирования)")

    # --- ПЛЕЙСХОЛДЕРЫ (класс R2-12). HARD.
    placeholders = check_placeholders(text)
    if placeholders:
        hard_fail = True
        print(f"[FAIL] плейсхолдеры в тексте: {len(placeholders)} наруш. "
              f"(владелец: '[живой факт]'/'[пруф дня]' - убирай полностью; допустим только {{spots}})")
        for p in placeholders:
            print(f"        {p}")
    else:
        print("[PASS] плейсхолдеры (0, кроме белого списка {spots} и подстановок бота)")

    # --- ЦЕНА ЦИФРОЙ (класс R2-10, закон-якорь №7). HARD.
    price = check_price_digit(text)
    if price:
        hard_fail = True
        print(f"[FAIL] цена цифрой: {len(price)} наруш. (закон-якорь №7 «цену цифрой - никогда»)")
        for p in price:
            print(f"        ...{p}...")
    else:
        print("[PASS] цена цифрой (0)")

    # --- ОТЛОЖЕННОЕ ОБЕЩАНИЕ / ДОМАШКА (класс R2-7, частично). HARD.
    if check_deferred_promise(text):
        hard_fail = True
        print("[FAIL] отложенное обещание («расскажу позже/на эфире», «покажу отдельно») - "
              "класс R2-2/7, обрубание ценности заглушкой")
    else:
        print("[PASS] отложенных обещаний нет")
    # 4c: домашка и ВТОРОЕ ДЕЙСТВИЕ (класс E6) - один закон-якорь №11
    # «единственное действие читателя = регистрация», поэтому один вход.
    # BASELINE по решению автора фиксировал E6 как «М (есть)» в классификаторе, а функции
    # check_second_action в коде не было вовсе - теперь есть.
    _hw = check_homework_action(text)
    _second = check_second_action(text)
    if _hw or _second:
        hard_fail = True
        print("[FAIL] действие-читателю мимо регистрации (закон-якорь №11: единственное "
              "действие читателя = РЕГИСТРАЦИЯ; «действие» в посте это рассказ про МОИ "
              "действия и результаты, читатель вдохновляется сам)")
        if _hw:
            print("        домашка: императив ручной работы читателю (канон п.22 - "
                  "ручная работа противоречит вайбкодингу)")
        for label, frag in _second[:5]:
            print(f"        второе действие «{label}»: ...{frag}...")
    else:
        print("[PASS] домашки и второго действия читателю нет (закон-якорь №11)")

    # --- ДОМАШКА, ШИРОКИЙ СЛОЙ (волна 15). WARN. Узкий HARD выше пропускал
    # прямой рецидив бенчмарка «Возьми слово... и сделай под него статью».
    hw_soft = check_homework_soft(text)
    if hw_soft:
        print(f"[WARN] императив ручного действия читателю вне CTA-регистрации: {len(hw_soft)} "
              f"(закон-якорь №11 - единственное действие читателя это регистрация; "
              f"admission: 0/10 донор-эталонов и финалов владельца таких оборотов не несут)")
        for h in hw_soft[:3]:
            print(f"        «{h[:90]}»")
    else:
        print("[PASS] императивов ручного действия читателю нет (широкий слой, волна 15)")

    # --- ГЛОССАРНАЯ ВСТАВКА (волна 15). WARN. Референт вводится делом, не глоссарием.
    gloss = check_glossary_insert(text)
    if gloss:
        print(f"[WARN] глоссарная вставка внутри предложения: {len(gloss)} («а это X» / "
              f"«X это когда»). Референт вводится ДЕЛОМ и контекстом, а не определением "
              f"вставкой; admission: 0/10 green, 2/6 постов бенчмарк-серии")
        for g in gloss[:3]:
            print(f"        «...{g[:90]}...»")
    else:
        print("[PASS] глоссарных вставок нет («а это X» / «X это когда»)")

    # --- РЕКЛАМА-ПЕРЕЧИСЛЕНИЕ ПРОГРАММЫ (класс R2-2 / B4, канон п.24).
    # 4c: поднято WARN -> HARD. Причина не «строже лучше», а замер: класс B4
    # значится в классификаторе машинно-ловимым, а функция на своей же фикстуре
    # возвращала 0 и печатала PASS (BASELINE §5, «функция-призрак» №1). Чинить
    # словарь и оставлять WARN бессмысленно - анонс программы это ровно тот
    # «спам вместо ценности», ради которого класс заведён (владелец, п.5).
    prog_lines, prog_inline = check_program_enum(text)
    if prog_lines >= 3 or prog_inline:
        hard_fail = True
        print(f"[FAIL] перечисление программы вместо ценности (класс R2-2/B4, канон п.24): "
              f"строк-рубрик «модуль/день/урок N» {prog_lines}, описей одной строкой "
              f"{len(prog_inline)}")
        for frag in prog_inline[:3]:
            print(f"        ...{frag}...")
    else:
        print(f"[PASS] перечисления программы нет (строк-рубрик {prog_lines}, описей 0)")

    # --- БЮДЖЕТ ДЛИНЫ (AC1, --budget). WARN, НЕ FAIL (канон §3 запрещает блок по длине).
    if args.budget is not None:
        if length > args.budget:
            print(f"[WARN] бюджет длины: {length} > {args.budget} (AC1: цель, не блок - "
                  f"канон §3 запрещает FAIL по длине; сожми в 03-dry)")
        else:
            print(f"[PASS] бюджет длины: {length} <= {args.budget}")

    # --- ФАКТ-БАЗА (AC5, --factbase). HARD «выдуманный факт».
    if args.factbase:
        try:
            fb_text = load_factbase(args.factbase)
        except OSError as e:
            # 🔴 4c: это НЕ правило о тексте, а поломка окружения - файл не
            # читается, значит гейт вообще не смог проверить пост. Тот же
            # разбор, что в post-phase-gate.sh («поломка окружения, а не
            # доказанный брак поста»). Выходим сразу и говорим об этом прямо,
            # а не подмешиваем инфраструктурный сбой в список дефектов текста.
            print(f"[ОШИБКА ЗАПУСКА] факт-база: не удалось прочитать {args.factbase} ({e}) - "
                  f"проверка не выполнена, это не вердикт по посту")
            print("=" * 56)
            sys.exit(2)
        else:
            fb = check_factbase(text, fb_text)
            # 🔴 Д18 (по решению автора), К4. ТРЕБОВАНИЕ ДЛИНЫ СНЯТО (было HARD).
            # БЫЛО: `len(факт-базы) >= len(поста)` = FAIL. Правило создавало
            # перверсный стимул ровно под ту дыру, которую чинит сито дублей
            # рядом: самый дешёвый способ сделать факт-базу длиннее поста - это
            # взять сам пост. Честная короткая выписка (4 строки: сумма, срок,
            # фамилия) отбивалась, копия тела поста - проходила.
            # СТАЛО: длина печатается справкой. Дефицит контекста меряется там,
            # где он действительно измерим - входным гейтом против --budget
            # (ниже, 02b) и правилами самого поста (пол длины, плотность идей,
            # 4.DENS): огрызок ловится СВОИМ классом, а не длиной источника.
            if not fb["volume_ok"]:
                print(f"[INFO] факт-база короче поста: {fb['fb_len']} < {fb['post_len']} "
                      f"(не блок с Д18: выписка законно короче текста; дефицит контекста "
                      f"меряют --budget и правила самого поста)")
            else:
                print(f"[PASS] факт-база: объём {fb['fb_len']} >= поста {fb['post_len']}")
            # --- ВХОДНОЙ ГЕЙТ ОБЪЁМА (п.7 скептик-раунда 2, по решению автора).
            # 02b-research-summary.md требует «объём факт-базы >= brief.budget», но эта
            # проверка жила ТОЛЬКО в тексте фазы: код мерил факт-базу против длины
            # ГОТОВОГО поста, то есть после осушения дефицит контекста уже не виден.
            # Теперь при переданном --budget линтер меряет тело факт-базы (без заголовков
            # `#`, метод очистки - как в 02b) против бюджета. Уровень намеренно WARN:
            # HARD по-прежнему только против длины готового поста (выше), потому что
            # решение «добрать или понизить цель» принимается в 02b человеком, а не тут.
            if args.budget is not None:
                fb_body = factbase_body_len(fb_text)
                if fb_body < args.budget:
                    print(f"[WARN] факт-база меньше бюджета - риск воды: тело базы "
                          f"{fb_body} знаков < budget {args.budget} (AC5а входной гейт "
                          f"02b: добрать контекст из story-bank/карты смыслов/voice-corpus "
                          f"или явно понизить brief.budget - писать при дефиците запрещено)")
                else:
                    print(f"[PASS] факт-база покрывает бюджет: тело базы {fb_body} "
                          f">= budget {args.budget}")
            if fb["missing_numbers"]:
                hard_fail = True
                print(f"[FAIL] выдуманные числа: {len(fb['missing_numbers'])} - нет в факт-базе "
                      f"(AC5б, класс R2-4): {', '.join(fb['missing_numbers'][:10])}")
            else:
                print("[PASS] все числа поста есть в факт-базе")
            if fb["missing_names"]:
                hard_fail = True
                print(f"[FAIL] висящие имена: {len(fb['missing_names'])} - нет в факт-базе "
                      f"(AC5в, класс R2-4/6): {', '.join(fb['missing_names'][:10])}")
            else:
                print("[PASS] все имена собственные поста есть в факт-базе")
            # --- числительные ПРОПИСЬЮ (волна 16, по решению автора). WARN.
            # HARD-уровень намеренно не берём: русское числительное омонимично
            # обычному слову, и ложный блок валил бы здоровый пост. Печатаем
            # найденное - решение принимает человек в 04-review.
            if fb["missing_word_numbers"]:
                _wn = ", ".join(f"«{p}» (={v})" for p, v in fb["missing_word_numbers"][:10])
                print(f"[WARN] числительные словами вне факт-базы: "
                      f"{len(fb['missing_word_numbers'])} - {_wn} (AC5б-прописью: число "
                      f"написано словом, но такого значения в источнике нет ни цифрами, "
                      f"ни прописью. Сверь по факт-базе - либо добери факт, либо убери "
                      f"число. Идиома вроде «в первую очередь» сюда не попадает, для них "
                      f"есть белый список NUMERAL_IDIOMS)")
            else:
                print("[PASS] числительные словами: все значения есть в факт-базе")
    else:
        print("[INFO] --factbase не передан - AC5-гейт (выдуманные факты) не проверялся")

    # --- СЦЕНА (гейт 02b1, --scene-state вместе с файлом поста) --------------
    if args.scene_state:
        _sc = check_scene_state(args.scene_state, args.scene_package)
        for _l in _sc["lines"]:
            print(_l)
        if _sc["status"] == "FAIL":
            hard_fail = True
    else:
        print("[INFO] --scene-state не передан - гейт 02b1 (добыча сцены) не проверялся")

    # --- UTM / PS-ACTION / ПОДДЕРЖКА (класс R2-10, --channel). UTM-гейт HARD
    # действует ТОЛЬКО при --form-goal (тот же fallback-принцип L1, что и весь
    # профильный слой канона формы v2 выше) - иначе старый вызов БЕЗ новых
    # флагов ловил бы FAIL на любой тестовой/служебной ссылке без UTM, хотя
    # раньше (v1) такой проверки не было вовсе. PS-Action и ссылка поддержки
    # безопасны без этого гейта (они триггерятся только на реальных маркерах
    # запуска/канала bot, молчат на произвольном тексте) - остаются всегда.
    if form_profile is None:
        print("[INFO] UTM: --form-goal не передан - UTM-гейт (v2.0) не проверялся (fallback, как L1-L5)")
        utm_bad = []
    else:
        utm_bad = check_utm(text, args.channel)
    if utm_bad:
        hard_fail = True
        print(f"[FAIL] UTM: {len(utm_bad)} ссыл. без utm_source/utm_content: {', '.join(utm_bad[:5])}")
    elif form_profile is not None:
        print("[PASS] UTM: все ссылки размечены (или ссылок нет)")
    psa = check_ps_action(text, args.channel)
    if psa == "MISSING" and args.allow_no_psa:
        print(f"[WARN] P.S.-Action: приписки-fallback нет, понижено до WARN флагом "
              f"--allow-no-psa (причина: {args.allow_no_psa})")
    elif psa == "MISSING":
        hard_fail = True
        print("[FAIL] P.S.-Action: пост запуска без сквозной приписки-fallback (класс R2-10 п.3)")
    elif psa == "OK":
        print("[PASS] P.S.-Action: приписка на месте")
    elif psa == "NA_BOT":
        print("[INFO] P.S.-Action: не проверяется в бот-дуге (канон)")
    elif psa == "NA_EMAIL":
        print("[INFO] P.S.-Action: не проверяется у письма (4c: у email свой футер и подпись, "
              "приписка-fallback это норма публичных TG-каналов и информеров)")
    elif psa == "NA_NOCANON":
        print("[INFO] P.S.-Action: не применяется - личного канон-файла PS-ACTION на машине нет")
    else:
        print("[INFO] P.S.-Action: канон-файл на месте, но пост не опознан как пост запуска "
              "(нет ни start-кода/бота, ни домена-лендинга из канона) - проверка не применяется")
    support = check_bot_support_link(text, args.channel)
    if support is False:
        print("[WARN] ссылка поддержки не найдена (--channel bot, класс R2-10 п.13)")
    elif support is True:
        print("[PASS] ссылка поддержки есть (--channel bot)")

    # --- ПАКЕТ (--package DIR). WARN.
    if args.package:
        pkg_dup = check_package_duplicates(
            text, args.package, this_anchor=args.anchor,
            anchor_entries=load_used_anchors(args.used_anchors_log),
            this_hero=args.hero, allow_skeleton_repeat=args.allow_skeleton_repeat)
        pkg_fail = [h for h in pkg_dup if h[2] == "FAIL"]
        pkg_warn = [h for h in pkg_dup if h[2] != "FAIL"]
        if pkg_fail:
            hard_fail = True
            print(f"[FAIL] дубли внутри волны в пакете {args.package}: {len(pkg_fail)} "
                  f"(волна 15, класс 8.2 - один каркас/один герой на серию)")
            for fp, why, _ in pkg_fail:
                print(f"        {fp}: {why}")
        if pkg_warn:
            print(f"[WARN] кросс-постовые дубли в пакете {args.package}: {len(pkg_warn)}")
            for fp, why, _ in pkg_warn:
                print(f"        {fp}: {why}")
        if not pkg_dup:
            print(f"[PASS] дублей в пакете {args.package} не найдено")

    # --- ЯКОРЬ / ГЕРОЙ / ФОРМА ЗАГОЛОВКА (класс R2-8, .used-anchors.jsonl).
    headline_form = compute_headline_form(paragraphs)
    if args.anchor or args.hero:
        anchor_entries = load_used_anchors(args.used_anchors_log)
        # exclude_slug: тот же фикс самоловли, что у скелета выше (БЛОКЕР 2).
        anchor_hits = check_anchor_dup(args.anchor, args.hero, headline_form, args.channel,
                                       anchor_entries, exclude_slug=args.log_anchor)
        if anchor_hits["anchor"] or anchor_hits["hero"]:
            hard_fail = True
            print(f"[FAIL] дубль якоря/героя за 7 дней (класс R2-8, закон-якорь №8 "
                  f"«герой не повторяется два дня ни в каком канале»):")
            for e in anchor_hits["anchor"]:
                print(f"        якорь «{args.anchor}» уже был {e.get('date')}/{e.get('channel')}/{e.get('slug')}")
            for e in anchor_hits["hero"]:
                print(f"        герой «{args.hero}» уже был {e.get('date')}/{e.get('channel')}/{e.get('slug')}")
        else:
            print("[PASS] якорь/герой не повторяют выдачи последних 7 дней")
        if anchor_hits["headline_form"]:
            print(f"[WARN] форма заголовка повторяется в канале '{args.channel}' за 7 дней "
                  f"(класс R2-8 подтип 3): {headline_form}")
        else:
            print(f"[PASS] форма заголовка не повторяется в канале '{args.channel}' за 7 дней")
    else:
        print("[INFO] --anchor/--hero не переданы - дубль-гейт журнала якорей не проверялся")

    # =========================================================================
    # ЖУРНАЛЫ (оба - в конце прогона, по ФИНАЛЬНОМУ hard_fail). Один вызов
    # линтера с --log-skeleton И --log-anchor пишет обе записи (05-publish
    # Шаг 1c/1e слиты в один прогон, скептик-раунд 3 БЛОКЕР 2). Проверки дубля
    # обоих журналов исключают запись с тем же слагом (см. exclude_slug выше),
    # поэтому запись этого прогона не может поймать сама себя ни сейчас, ни при
    # повторном прогоне того же поста.
    # =========================================================================
    if args.log_skeleton and not hard_fail:
        append_skeleton_log(args.skeleton_log, args.channel, args.log_skeleton, sig)
        print(f"[LOG] скелет записан в журнал: {args.channel}/{args.log_skeleton} = {sig_str}")
    elif args.log_skeleton and hard_fail:
        print("[LOG] скелет НЕ записан: пост с hard-нарушениями не считается выданным")

    if args.log_anchor and not hard_fail:
        append_used_anchor(args.used_anchors_log, {
            "channel": args.channel, "slug": args.log_anchor,
            "anchor": args.anchor, "hero": args.hero, "headline_form": headline_form,
        })
        print(f"[LOG] якорь записан в журнал: {args.channel}/{args.log_anchor}")
    elif args.log_anchor and hard_fail:
        print("[LOG] якорь НЕ записан: пост с hard-нарушениями не считается выданным")

    print("=" * 56)
    print("ИТОГ:", "FAIL (есть hard-нарушения)" if hard_fail else "PASS (hard-правила чисты)")
    print("Семантику (метафоры/голос/живость) скрипт не проверяет -")
    print("см. Gate Evidence Report в workflow/04-review.md.")
    print("=" * 56)

    sys.exit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()