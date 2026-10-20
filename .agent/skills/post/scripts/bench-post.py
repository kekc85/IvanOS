#!/usr/bin/env python3
"""
bench-post.py - скоринг поста против R3-benchmark-spec.md по классу формы.

AC7 (спека ~/specs/2026-08-04-post-skill-v2.md): скорит пост по классу против
порогов R3 (форма/конкретика/вода/устная речь/анти-паттерны). Пороги ПО ЦЕЛИ
(form_goal читается ДО порога, R3 предупреждение 3 - плотность конкретики
меняет знак). Выход - человекочитаемый отчёт + блок JSON + вердикт
PASS/WARN/FAIL. Режим --against-etalons сравнивает метрики поста с 11
эталонами ТРЁХ доноров (uid Донор-А:504/492/433/440, Донор-Б:1372/1455/1579,
Донор-Б:1833, Донор-В:213/102/165 из corpus-12m.json, извлечены один
раз в scripts/etalons.json) и печатает строку микса доноров по классу.
🔴 razbor-эталон Донор-Б: по решению автора дефектом Д19 скептик-раунда 3 в класс
были внесены Донор-Б:2034/2014, и тем же днём дефектом Д23 раунда 4 оба
СНЯТЫ - к ним применили тот же критерий, каким размечали mech_manual у
третьего донора, и оба упали: 2034 несёт «разобрать систему, как что
работает? – ⚡️» и вдобавок fresh (<7 дней, вне корпуса по _scope.md), 2014
несёт «надо вам такое? – ⚡️» и 351 зн. против нижнего коридора класса 402.
Замена - Донор-Б:1833 (er_idx 1.02, 988 зн., хвост чист): топ по er_idx
среди чистых нефрешевых razbor-кандидатов донора длиной >= 402. Ручной
проход по всем 56 razbor-кандидатам трёх доноров и критерий отбора -
`.business/growth/content-archive/Доноры стиля/_research/
_etalon-selection-note-2026-08-07.md`.
🔴 ДЛИНА ПРИ ОТБОРЕ ЭТАЛОНА - НИЗ ЖЁСТКИЙ, ВЕРХ МЯГКИЙ (Д25 раунда 5,
по решению автора): низ коридора класса отсекает жёстко (razbor 402 - короче не
берём), верх допускает до 1.5 коридора (razbor 990 × 1.5 = 1485). Поэтому
Донор-А:433 при 1359 зн. эталоном стоит, а Донор-В:203 при 3075 зн. отсеян -
и причина в MISSING_REASONS названа мягким верхом, а не коридором 990.
Пороги коридора мерят ГОТОВЫЙ ПОСТ, отбор эталона мерит ОБРАЗЕЦ ФОРМЫ, и
длинный образец форму не ломает. Источник - та же нота отбора по решению автора.
🔴 ОБЛАСТЬ ПРАВИЛА «НИЗ ЖЁСТКИЙ» (уточнено Д54 раунда 13, по решению автора): это
критерий ПЕРЕСЕВОВ и НОВЫХ эталонов - он введён раундом 4 на классе razbor и
на весь исторический набор задним числом не распространяется. Исходное ядро
v2.0 (7 эталонов: Донор-А:504/492/433/440, Донор-Б:1372/1455/1579)
отбиралось по ER-топам ДО рождения правила, поэтому в нём есть известные
легаси-исключения: Донор-А:440 (430 зн. против низа sales 759) и
Донор-А:492 (358 зн. против низа narrative 362). Они оставлены сознательно -
пересев ядра тянет каскад по green-фикстурам, admission-числам и покрытию
микса, и стоит дороже выгоды. Заявлять «низ жёсткий по всему набору» - ложь;
правило держит будущее, а не прошлое. Машинный страж - `run-tests.py`
test_etalon_floor_discipline: любой эталон ВНЕ этого списка из 7 обязан быть
не короче нижнего коридора своего класса, легаси печатаются строкой
«известные исключения ядра».

Отличие от lint-post.py: lint - БИНАРНЫЙ гейт (HARD/WARN построчно, exit
0/1 для post-phase-gate.sh). bench - ПОЛНЫЙ скоринг-отчёт против R3-таблиц
(насколько пост похож на верх доноров по каждой метрике), для качественной
сверки перед публикацией серии (AC7 «серия постов проходит bench + сверку
с 7 эталонами» - цифра спеки от этой редакции, набор с этой редакции расширен до 10 за
счёт третьего донора, потом до 12 за счёт razbor-эталонов Донор-Б, и в тот
же день сведён к 11 дефектом Д23 - см. блок про razbor выше). Использует ТЕ ЖЕ словари/функции, что и lint-post.py
(единый источник истины - reuse через importlib, не копия).

Usage:
    python3 bench-post.py FILE --form-goal reactions --form-class narrative
    python3 bench-post.py FILE --form-goal sales --against-etalons
    cat post.txt | python3 bench-post.py - --form-goal forwards

Exit code: 0 (PASS/WARN), 1 (FAIL - серьёзные расхождения с R3 верхом).
"""

import sys
import os
import json
import argparse
import importlib.util
import statistics as st


def _load_lint_module():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("lint_post_v2", os.path.join(here, "lint-post.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LINT = _load_lint_module()

HERE = os.path.dirname(os.path.abspath(__file__))
ETALONS_PATH = os.path.join(HERE, "etalons.json")


def read_input(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _etalon_missing_keys(e):
    """Обязательные ключи записи эталона: `text` (непустая строка), `id`,
    `author`, `form_class`. Опциональные (не проверяются здесь): `uid`,
    `er_idx`, `cls`. Возвращает список имён отсутствующих/пустых обязательных
    ключей (пустой список = запись валидна)."""
    if not isinstance(e, dict):
        return ["<не объект>"]
    missing = []
    text = e.get("text")
    if not isinstance(text, str) or not text.strip():
        missing.append("text")
    if e.get("id") is None:
        missing.append("id")
    for k in ("author", "form_class"):
        v = e.get(k)
        if not isinstance(v, str) or not v.strip():
            missing.append(k)
    return missing


def load_etalons():
    """🔴 МЯГКАЯ ДЕГРАДАЦИЯ (по решению автора, обоснование уточнено по дефекту Д5,
    доведена до ПЕР-ЗАПИСИ дефектом Д62 скептик-раунда 17 по решению автора).
    Хук post-phase-gate.sh раздаётся ученикам и гонит бенч с --against-etalons
    ВСЕГДА. Сам etalons.json в раздачу входит - но рассчитывать на него как на
    константу нельзя: файл может ОТСУТСТВОВАТЬ или быть ЗАМЕНЁН (санитайзер
    раздачи вырезает персональный корпус, ученик подставляет свой набор
    эталонов, файл пуст / битый JSON / не список после ручной правки, ОДНА
    запись внутри валидного списка потеряла ключ при ручной правке).
    Ни один из этих случаев не имеет права уронить скоринг: возвращаем список
    только валидных записей (может быть пустым), main печатает причину,
    ВЕРДИКТ и exit-код считаются ровно как без флага.

    Схема записи (обязательные ключи - см. `_etalon_missing_keys`):
        text        str, непустая  - текст поста-эталона
        id          любой не-None  - id поста у донора
        author      str, непустая  - имя донора
        form_class  str, непустая  - класс формы (narrative/razbor/sales/...)
    Опциональные ключи: `uid` (человекочитаемый `Автор:id`, иначе строится
    из author+id в compare_to_etalons), `er_idx` (engagement rate донора),
    `cls` (человекочитаемая метка класса для людей, не читается кодом).

    Д62: ЛЮБАЯ запись без обязательного ключа раньше валила compare_to_etalons
    KeyError-ом (exit 1, ВЕРДИКТ не печатался, хук post-phase-gate.sh грепает
    строку «ВЕРДИКТ:» и давал ложный BLOCK «ИНФРАСТРУКТУРА» на КАЖДОЙ выдаче).
    Теперь битая запись в набор просто не попадает - остальные валидные
    работают, а причина отсева печатается одной строкой [INFO]."""
    if not os.path.exists(ETALONS_PATH):
        return []
    try:
        with open(ETALONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    if not isinstance(data, list):
        return []
    valid, dropped = [], []
    for idx, e in enumerate(data):
        missing = _etalon_missing_keys(e)
        if missing:
            label = (e.get("uid") or e.get("id") if isinstance(e, dict) else None) or f"idx {idx}"
            dropped.append(f"{label} (нет: {', '.join(missing)})")
            continue
        valid.append(e)
    if dropped:
        print(f"[INFO] эталоны: отброшено {len(dropped)} записей без обязательных "
              f"ключей (text/id/author/form_class): {'; '.join(dropped)}")
    return valid


# R3 §A - целевые медианы формы по классу (та же таблица, что FORM_PROFILES
# в lint-post.py, но здесь читаем ЦЕЛИКОМ для отчёта, не только гейты).
R3_FORM_TARGETS = {
    "narrative": {"chars": 671, "chars_q1": 362, "chars_q3": 1242, "nonempty_lines": 10,
                  "air": 0.86, "air_floor": 0.65, "chars_per_line": 59, "bold_n": 1,
                  "bold_share_pct": 12.2, "links": 0, "lines_per_para": 1.00},
    "razbor": {"chars": 542, "chars_q1": 402, "chars_q3": 990, "nonempty_lines": 9,
               "air": 0.87, "air_floor": 0.65, "chars_per_line": 64, "bold_n": 1.5,
               "bold_share_pct": 13.9, "links": 0, "lines_per_para": 1.00},
    "sales": {"chars": 1489, "chars_q1": 759, "chars_q3": 2248, "nonempty_lines": 19,
              "air": 0.78, "air_floor": None, "chars_per_line": 56, "bold_n": 4.5,
              "bold_share_pct": 13.9, "links": None, "lines_per_para": 1.19},
    "forwards": {"chars": 1159, "chars_q1": 838, "chars_q3": 1695, "nonempty_lines": 18,
                 "air": 0.80, "air_floor": None, "chars_per_line": 56, "bold_n": 3,
                 "bold_share_pct": 13.3, "links": 1, "lines_per_para": 1.19},
}

# R3 §E - устная речь (разделяет квартили В НАРРАТИВЕ).
R3_VOICE_NARRATIVE = {
    "double_bracket_pct": 81, "ellipsis_pct": 78, "particle_pct": 0.61,
    "sentence_p25": 4, "sentence_p75": 12, "sentence_median_lo": 6, "sentence_median_hi": 8,
    "sentence_spread_lo": 2, "sentence_spread_hi": 25,
}


def measure_form(text):
    """R3 §A метрики формы - переиспользует lint-post.py где возможно."""
    paragraphs = LINT.split_paragraphs(text)
    plain = LINT._strip_md_plain(text)
    lines = text.splitlines()
    ne = [l for l in lines if l.strip()]
    m = {
        "chars": len(plain),
        "nonempty_lines": len(ne),
        "air": LINT.check_air(text),
        "chars_per_line": st.median([len(LINT._strip_md_plain(l)) for l in ne]) if ne else 0,
        "bold_n": LINT.check_bold_count(text),
        "links": len(LINT.check_links(text)[0]),
        "lines_per_para_median": LINT.check_paragraph_line_median(paragraphs),
        "sentence_median": LINT.check_sentence_median(text),
        "sentence_spread": LINT.check_sentence_monotony(text),
    }
    # --- волна 15: ритм в СЛОВАХ (граница предложения = знак конца ИЛИ перенос
    # строки; в формате автора точки в конце абзаца нет, старый сплит склеивал
    # абзац в одно «предложение» - см. блок ВОЛНА 15 в lint-post.py).
    rh = LINT.check_rhythm_words(text)
    m["w15_sentence_median_words"] = rh["median"] if rh else None
    m["w15_sentence_min_words"] = rh["min"] if rh else None
    m["w15_punch_sentences"] = rh["punch"] if rh else None
    glue = LINT.check_glue_density(text)
    m["w15_glue_k"] = round(glue["k"], 2) if glue else None
    md_bold = __import__("re").findall(r"\*\*(.+?)\*\*", text, __import__("re").S)
    bold_chars = sum(len(b) for b in md_bold)
    m["bold_share_pct"] = 100 * bold_chars / max(len(plain), 1)

    # --- ЭЛЕМЕНТЫ ФОРМЫ (по решению автора). Бенч был СЛЕПОЙ к ним: он мерил длину,
    # воздух, жирные и ссылки, а весь слой элементов копирайтинга (опись, капс,
    # стрелки, курсив, прямая речь, вопросы, эмодзи-хвосты, панч-строки) в
    # отчёт не попадал вовсе - оператор сравнивал пост с донорами по четырём
    # числам и не видел ровно того, за что владелец разнёс выдачу по решению автора.
    # Счёт НЕ дублируется: берём ту же функцию lint-post.py, что держит гейт
    # (единый источник истины, как и у остальных метрик этого файла).
    # 🔴 Пороговых вердиктов тут НЕТ и не заводить: бенч показывает, гейт судит.
    el = LINT.check_element_types(text)
    ec = el["counts"]
    m["element_types_n"] = el["types"]
    # 🔴 по решению автора: бенч видит и СИГНАТУРНЫЙ счёт - именно он теперь судит
    # текстуру (счёт «типов из 15» бесплатен, шесть категорий ставит канон формы)
    m["element_sig_n"] = el["sig_types"]
    m["caps_n"] = ec["caps_word"]
    m["dash_blocks"] = ec["dash_list"]
    m["arrows_n"] = ec["arrow"]
    m["italic_n"] = ec["italic"]
    m["direct_speech"] = 1 if ec["direct_speech"] else 0
    m["questions_n"] = ec["question"]
    m["emoji_n"] = ec["emoji_count"]
    m["emoji_tail_n"] = ec["emoji_tail"]
    m["short_punch_n"] = ec["short_punch"]
    return m, paragraphs


def measure_voice(text):
    """R3 §E - устная речь (только разделяет квартили в нарративе, INFO для остальных)."""
    import re
    m = {}
    m["double_bracket"] = text.count("))")
    m["ellipsis"] = text.count("…") + len(re.findall(r"\.\.\.", text))
    words = LINT._words(LINT._strip_md_plain(text))
    particles = {"ну", "вот", "короче", "блин", "прям", "ребят"}
    p_hits = sum(1 for w in words if w in particles)
    m["particle_pct"] = 100 * p_hits / max(len(words), 1)
    return m


def score_metric(value, lo, hi, label):
    """Простая PASS/WARN оценка попадания в коридор [lo, hi] (None = не проверяем)."""
    if value is None:
        return "INFO", f"{label}: н/д"
    if lo is not None and value < lo:
        return "WARN", f"{label}: {value:.2f} < {lo} (ниже целевого коридора R3)"
    if hi is not None and value > hi:
        return "WARN", f"{label}: {value:.2f} > {hi} (выше целевого коридора R3)"
    return "PASS", f"{label}: {value:.2f} (в коридоре R3)"


def bench_post(text, form_goal, form_class):
    """Главный скоринг. Возвращает dict с полным отчётом + вердикт."""
    form_profile, form_key = LINT.resolve_form_profile(form_goal, form_class)
    resolved_class = form_key[1] if form_profile is not None else form_class
    form_m, paragraphs = measure_form(text)
    voice_m = measure_voice(text)
    water = LINT.check_water(text)
    conc = LINT.check_concreteness(text)
    collocations = LINT.check_banned_collocations(text)
    placeholders = LINT.check_placeholders(text)
    price = LINT.check_price_digit(text)

    report = {"scores": [], "warnings": [], "hard_fails": []}

    def add(status, msg):
        report["scores"].append({"status": status, "msg": msg})
        if status == "WARN":
            report["warnings"].append(msg)
        if status == "FAIL":
            report["hard_fails"].append(msg)

    targets = R3_FORM_TARGETS.get(resolved_class)
    if targets:
        s, msg = score_metric(form_m["chars"], targets["chars_q1"], targets["chars_q3"], "длина (знаков)")
        add(s, msg)
        s, msg = score_metric(form_m["air"], targets.get("air_floor"), None, "воздух")
        add(s, msg)
        s, msg = score_metric(form_m["lines_per_para_median"], None, 2, "медиана строк/абзац")
        add(s, msg)
        if resolved_class == "narrative" and form_m["links"] > 0:
            add("FAIL", f"ссылок в нарративе: {form_m['links']} (R3 §A: 0 HARD, 89% верха)")
        elif resolved_class == "forwards" and form_m["links"] == 0:
            add("FAIL", f"ссылок в носителе: 0 (R3 §A: обязательна, 92% верха)")
        else:
            add("PASS", f"ссылок: {form_m['links']}")

    # вода (R3 §C)
    s = "FAIL" if (water["kanc_k"] > 0 or water["cliche_k"] > 0) else "PASS"
    add(s, f"вода-канцелярит/клише: kanc={water['kanc_k']:.2f} cliche={water['cliche_k']:.2f} (потолок 0)")
    s = "WARN" if water["sum_k"] > 2.5 else "PASS"
    add(s, f"вода суммарно: {water['sum_k']:.2f}/1000 (потолок 2.5)")

    # конкретика по классу (R3 §B, знак от цели)
    if resolved_class == "narrative":
        s = "WARN" if conc["num_k"] > 4.4 else "PASS"
        add(s, f"конкретика-числа (нарратив): {conc['num_k']:.2f}/1000 (потолок 4.4)")
    elif resolved_class == "forwards":
        s = "WARN" if conc["num_k"] < 5.0 else "PASS"
        add(s, f"конкретика-числа (носитель): {conc['num_k']:.2f}/1000 (пол 5.0)")
    elif resolved_class == "razbor":
        s = "WARN" if conc["tools_k"] > 0 else "PASS"
        add(s, f"инструменты-перечень (разбор): {conc['tools_k']:.2f}/1000 (желательно 0 - объяснять механизм)")
    else:
        add("INFO", f"конкретика-числа: {conc['num_k']:.2f}/1000 (гейт не вешаем, R3 §B продажа)")

    # обороты / плейсхолдеры / цена (законы-якоря, всегда HARD)
    if collocations:
        add("FAIL", f"несуществующие обороты: {len(collocations)}")
    else:
        add("PASS", "несуществующие обороты: 0")
    if placeholders:
        add("FAIL", f"плейсхолдеры: {len(placeholders)}")
    else:
        add("PASS", "плейсхолдеры: 0")
    if price:
        add("FAIL", f"цена цифрой: {len(price)}")
    else:
        add("PASS", "цена цифрой: 0")

    # устная речь (R3 §E, только INFO/WARN в нарративе - разделяет квартили)
    if resolved_class == "narrative":
        s = "WARN" if voice_m["double_bracket"] == 0 else "PASS"
        add(s, f"скобка )): {voice_m['double_bracket']} вхожд. (цель >=1, 81% TOP vs 48% BOT, R3 §E)")
        if form_m["sentence_spread"] is not None:
            # 🔴 п.10 (скептик-раунд 4, по решению автора): печать врала. Стояло «разброс 2-25»,
            # как будто это проверяемый коридор, а гейт сравнивает ровно с ПОЛОМ 6
            # (строкой выше). 2-25 - наблюдённый разброс корпуса R3 §E, не порог.
            s = "WARN" if form_m["sentence_spread"] < 6 else "PASS"
            add(s, f"разброс длин предложений: {form_m['sentence_spread']} слов "
                   f"(пол 6, R3 §E; ровный поток = генератор)")

    # --- ВОЛНА 15 (судья бенчмарка по решению автора): ритм в СЛОВАХ, клей, живой слой -
    # для ВСЕХ классов, а не только для нарратива. Статусы здесь только WARN/PASS:
    # bench - скоринг-отчёт, блокирующие пороги живут в lint-post.py (там же весь
    # admission на 7 донорах + 3 финалах владельца).
    med_w = form_m.get("w15_sentence_median_words")
    if med_w is not None:
        s = "WARN" if med_w > LINT.W15_SENT_MEDIAN_WARN else "PASS"
        add(s, f"ритм: медиана {med_w:.1f} слов в предложении (потолок доноров "
               f"{LINT.W15_SENT_MEDIAN_WARN}, HARD в линтере {LINT.W15_SENT_MEDIAN_HARD}; "
               f"нарратив 9-13 · разбор 11 · продажа 4.5-5), минимальное предложение "
               f"{form_m.get('w15_sentence_min_words')} слов")
        punch = form_m.get("w15_punch_sentences")
        s = "WARN" if punch < LINT.W15_PUNCH_MIN_COUNT else "PASS"
        add(s, f"ударных предложений (<= {LINT.W15_PUNCH_MAX_WORDS} слов): {punch} "
               f"(минимум {LINT.W15_PUNCH_MIN_COUNT}, у доноров 0-25)")
    glue_k = form_m.get("w15_glue_k")
    if glue_k is None:
        add("INFO", f"клей («, а » + «который»): пост короче {LINT.W15_GLUE_MIN_WORDS} слов, не меряется")
    else:
        s = "WARN" if glue_k > LINT.W15_GLUE_WARN_K else "PASS"
        add(s, f"клей: {glue_k:.1f}/1000 слов (порог {LINT.W15_GLUE_WARN_K}, максимум green-корпуса 17.9)")
    oral = LINT.check_oral_layer(text)
    oral_on = [f"{k} ×{v}" for k, v in oral.items() if v > 0]
    s = "WARN" if not oral_on else "PASS"
    add(s, f"живой слой (все классы): {', '.join(oral_on) if oral_on else 'НЕТ ни одного знака устной речи'} "
           f"(в линтере это HARD, admission 10/10 green)")

    verdict = "PASS"
    if report["hard_fails"]:
        verdict = "FAIL"
    elif report["warnings"]:
        verdict = "WARN"

    return {
        "form_goal": form_goal, "form_class": resolved_class,
        "form_metrics": {k: v for k, v in form_m.items() if k != "lines_per_para_median" or True},
        "voice_metrics": voice_m,
        "water": {k: v for k, v in water.items() if not k.endswith("_hits")},
        "concreteness": conc,
        "scores": report["scores"],
        "warnings": report["warnings"],
        "hard_fails": report["hard_fails"],
        "verdict": verdict,
    }


def compare_to_etalons(text, resolved_class):
    """--against-etalons: сравнить метрики поста с эталонами доноров того же
    класса (или со всем набором, если класс не совпал ни с одним).

    Возвращает None, если набор эталонов недоступен (нет файла / пуст / битый) -
    это НЕ ошибка, main печатает причину и идёт дальше (мягкая деградация)."""
    etalons = load_etalons()
    if not etalons:
        return None
    in_class = [e for e in etalons if e.get("form_class") == resolved_class]
    fallback = not in_class
    same_class = in_class or etalons
    post_m, _ = measure_form(text)
    rows = []
    for e in same_class:
        # Д62 (скептик-раунд 17): после пер-записи валидации в load_etalons()
        # ключи text/id/author гарантированы для всего, что дошло сюда - но
        # .get() держит защиту на будущее (правка выше по коду, ручная
        # подмена набора), не меняя значений на валидных данных (uid уже
        # шёл через .get - остальные три приведены к тому же виду).
        em, _ = measure_form(e.get("text", ""))
        rows.append({
            "id": e.get("id"), "uid": e.get("uid") or f"{e.get('author')}:{e.get('id')}",
            "author": e.get("author"), "er_idx": e.get("er_idx"),
            "chars": em["chars"], "air": round(em["air"], 2),
            "bold_n": em["bold_n"], "links": em["links"],
            # по решению автора: элементы формы рядом с донором - иначе сверка молчит
            # ровно про тот слой, за который владелец разнёс выдачу. Три поля
            # после числа типов - САМЫЕ РАЗЛИЧАЮЩИЕ по замеру по решению автора (разрыв
            # green против доноров: панч-строка 8%/69%, эмодзи-хвост 0%/51%,
            # курсив 0%/45%).
            "element_types_n": em["element_types_n"], "italic_n": em["italic_n"],
            "emoji_tail_n": em["emoji_tail_n"], "short_punch_n": em["short_punch_n"],
        })
    return {"post": {"chars": post_m["chars"], "air": round(post_m["air"], 2),
                      "bold_n": post_m["bold_n"], "links": post_m["links"],
                      "element_types_n": post_m["element_types_n"],
                      "italic_n": post_m["italic_n"],
                      "emoji_tail_n": post_m["emoji_tail_n"],
                      "short_punch_n": post_m["short_punch_n"]},
            "etalons": rows,
            "mix": build_mix(etalons, same_class, resolved_class, fallback)}


# 🔴 Д23 скептик-раунда 4 (по решению автора): причина отсутствия донора в классе
# печаталась ОДНОЙ фразой «корпус не дал кандидата» на любой случай. Для
# Донор-В в классе razbor это было ложью: кандидаты у донора ЕСТЬ, но они
# отсеяны конкретными критериями. Здесь лежит точная причина по паре
# (класс, донор); чего в словаре нет - печатается прежняя общая формулировка.
# Правило: добавляя/снимая эталон, правь и эту строку, иначе отчёт снова
# начнёт объяснять отсев причиной, которой не было.
# 🔴 Д25 скептик-раунда 5 (по решению автора): причина по 203 ссылалась на «верхний
# коридор 990», который принятый эталон Донор-А:433 (1359 зн.) сам нарушает -
# читалось как двойной стандарт. Реальное правило отбора - НИЗ ЖЁСТКИЙ, ВЕРХ
# МЯГКИЙ (см. докстринг модуля): 433 при 1359 внутри мягкого верха 1485,
# 203 при 3075 - вдвое за ним. Формулировка приведена к правилу.
# 🔴 Д76 скептик-раунда 24 (по решению автора): «118 - 321 зн.» было сырым полем
# corpus-12m.json (len(text) до зачистки md), а «203 - 3075 зн.» рядом уже было
# меркой бенча measure_form() (сырое поле у 203 - 3087). Единицы в одной фразе
# разъехались. measure_form(текст 118)["chars"] = 320 (markdown-полужирный
# внутри поста короче на 1 знак после _strip_md_plain) - оба числа теперь в
# одной мерке, полускобка отмечает это один раз на фразу.
MISSING_REASONS = {
    ("razbor", "Донор-В"): (
        "razbor-топы донора несут реакция-механику либо вне коридора класса "
        "(109 - «собираем 500 единорогов 🦄», 161 - «огоньку плиз 🔥», "
        "70 - просьба о коммент-поздравлении и 391 зн., 118 - 320 зн. "
        "(мерка бенча) ниже нижнего коридора 402, 203 - 3075 зн. против "
        "мягкого верха эталонов 1485 (1.5 × коридор 990))"
    ),
}


def build_mix(all_etalons, same_class, resolved_class, fallback):
    """Строка микса доноров по классу: показывает, чьими эталонами реально
    меряется класс, и честно называет донора, которого корпус в этот класс не
    дал (иначе перекос набора невидим - сверка идёт «с эталонами», а по факту
    с одним автором)."""
    order = []
    for e in all_etalons:  # порядок доноров = порядок первого появления в наборе
        a = e.get("author")
        if a and a not in order:
            order.append(a)
    counts = {a: 0 for a in order}
    for e in same_class:
        a = e.get("author")
        if a in counts:
            counts[a] += 1
        elif a:
            order.append(a)
            counts[a] = 1
    missing = [a for a in order if counts.get(a, 0) == 0]
    return {"class": resolved_class, "fallback": fallback,
            "counts": counts, "order": order, "missing": missing}


def format_mix_line(mix):
    """`микс эталонов: <класс> - Донор-А N · Донор-Б N · Донор-В N` (+ хвост
    про доноров, которых корпус в этот класс не дал).

    🔴 Fallback-ветка честно называет цену подстановки (Д19 скептик-раунда 3,
    по решению автора). Раньше при отсутствии эталонов класса печатался счёт по ВСЕМУ
    набору - строка читалась как богатый микс доноров, хотя сравнение шло с
    ЧУЖИМИ классами (пост класса gate/event мерился нарративом и продажей).
    Теперь приписка говорит это прямо: цифры остаются, статус меняется.

    🔴 Причина отсутствия донора берётся из MISSING_REASONS по паре
    (класс, донор) - Д23 раунда 4: общая фраза «корпус не дал кандидата»
    врала там, где кандидаты у донора были, но не прошли критерий."""
    body = " · ".join(f"{a} {mix['counts'].get(a, 0)}" for a in mix["order"])
    if mix["fallback"]:
        line = (f"микс эталонов: {mix['class']} - эталонов этого класса в наборе нет, "
                f"сверка идёт по всему набору (счёт против ЧУЖИХ классов - "
                f"ориентир, не мерило): {body}")
    else:
        line = f"микс эталонов: {mix['class']} - {body}"
    for a in mix["missing"]:
        why = MISSING_REASONS.get((mix["class"], a), "корпус не дал кандидата")
        line += f" (нет эталона {a} в классе {mix['class']}: {why})"
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="путь к файлу с постом или '-' для stdin")
    ap.add_argument("--form-goal", choices=["reactions", "forwards", "sales", "gate"], required=True,
                    help="AC7: цель поста - порог читается ПОСЛЕ goal (R3 предупреждение 3).")
    # Д8 (по решению автора): класс event принимается наравне с остальными - иначе хук
    # post-phase-gate.sh, который зовёт бенч тем же флагом, что и линтер, ронял
    # бы бенч в argparse-ошибку и печатал «вердикт не напечатан» вместо скоринга.
    # R3-таблиц по событию нет (как и по классу gate) - блок целевых метрик
    # тогда молча пропускается, это штатная мягкая деградация bench_post.
    ap.add_argument("--form-class", choices=["narrative", "razbor", "sales", "gate", "event"], default=None,
                    help="класс при --form-goal reactions (narrative/razbor).")
    ap.add_argument("--against-etalons", action="store_true",
                    help="сравнить метрики поста с эталонами трёх доноров (scripts/etalons.json, "
                         "11 постов; файла нет - сверка мягко пропускается, вердикт не меняется).")
    args = ap.parse_args()

    if args.form_goal == "reactions" and args.form_class is None:
        print("[WARN] --form-class не передан, скорю как narrative (default=None -> narrative, "
              "razbor молча скорится чужим профилем без явного флага)")

    text = read_input(args.file)
    result = bench_post(text, args.form_goal, args.form_class)

    print("=" * 56)
    print(f"BENCH-POST: {args.form_goal}/{result['form_class']}")
    print("=" * 56)
    # 🔴 Д83 скептик-раунда 27 (по решению автора, рецидив класса Д79): эта строка жила
    # ТОЛЬКО внутри блока `if args.against_etalons`, хотя bench_post() (вызов
    # выше) резолвит форм-профиль и пишет LINT.LAST_FORM_COERCION на КАЖДОМ
    # прогоне, флаг тут ни при чём. Оператор гонял нелегальную пару БЕЗ
    # --against-etalons (например `reactions×sales` быстрым прогоном без
    # сверки с донорами) и коэрцию профиля не видел вовсе - тот же дефект
    # Д79 в другом месте того же файла. Печатается безусловно, тем же
    # форматом, что у lint-post.py main() (единый источник факта -
    # модульная LAST_FORM_COERCION).
    if LINT.LAST_FORM_COERCION is not None:
        _decl, _goal, _took = LINT.LAST_FORM_COERCION
        print(f"[ФОРМА-КОЭРЦИЯ] класс «{_decl}» несовместим с целью «{_goal}» - "
              f"профиль взят «{_took}» (канон пар: 01-router Шаг 0.49)")
    for item in result["scores"]:
        print(f"[{item['status']}] {item['msg']}")

    if args.against_etalons:
        print("-" * 56)
        print("СРАВНЕНИЕ С ЭТАЛОНАМИ ДОНОРОВ (--against-etalons)")
        print("-" * 56)
        cmp = compare_to_etalons(text, result["form_class"])
        if cmp is None:
            # мягкая деградация: файла эталонов нет / пуст / битый. Вердикт и
            # exit-код от этого не меняются - см. докстринг load_etalons().
            print("[INFO] эталоны недоступны, сверка с донорами пропущена "
                  f"(ожидался список постов в {ETALONS_PATH})")
            result["etalon_comparison"] = None
        else:
            p = cmp["post"]
            print(f"пост: {p['chars']} зн., воздух {p['air']}, жирных {p['bold_n']}, "
                  f"ссылок {p['links']} | типов элементов {p['element_types_n']}/15, "
                  f"курсив {p['italic_n']}, эмодзи-хвостов {p['emoji_tail_n']}, "
                  f"панч-строк {p['short_punch_n']}")
            for e in cmp["etalons"]:
                print(f"  донор {e['uid']} (er={e['er_idx']}): {e['chars']} зн., "
                      f"воздух {e['air']}, жирных {e['bold_n']}, ссылок {e['links']} | "
                      f"типов {e['element_types_n']}/15, курсив {e['italic_n']}, "
                      f"эмодзи-хвостов {e['emoji_tail_n']}, панч-строк {e['short_punch_n']}")
            # 🔴 Д79 скептик-раунда 26 (по решению автора): resolve_form_profile() внутри
            # bench_post() коэрцит нелегальную пару form_goal×form_class МОЛЧА -
            # ту же подмену lint-post.py кричит строкой [ФОРМА-КОЭРЦИЯ] (Д71
            # раунда 22), а bench-post.py её проглатывал (0 вхождений до фикса
            # р26). 🔴 Д83 скептик-раунда 27: печать самой строки ПЕРЕЕХАЛА выше
            # (сразу после заголовка BENCH-POST, безусловно - см. комментарий
            # там) - здесь она больше НЕ дублируется, чтобы на выдаче с
            # --against-etalons строка не печаталась дважды. Микс по-прежнему
            # печатается только тут (внутри блока сверки с донорами).
            print(format_mix_line(cmp["mix"]))
            result["etalon_comparison"] = cmp

    print("=" * 56)
    print("ВЕРДИКТ:", result["verdict"])
    print("=" * 56)
    print("JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(1 if result["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
