#!/usr/bin/env python3
"""
Единый контроль кодовых слов лид-магнитов.

Закон (см. used_codewords.md):
  1) одна строка-слово <-> один магнит (никогда не переиспользовать строку под другой магнит);
  2) один магнит <-> одно активное слово (для известного магнита берём существующее слово, не плодим новое).

Команды:
  check СЛОВО                         -> exit 2 если строка уже занята (active/legacy/competitor/conflict/carousel-registry)
  for-magnet "описание магнита"       -> печатает активное слово этого магнита, если есть
  reserve --magnet "..." --word X     -> валидирует и добавляет; exit 2 на конфликте
        [--lang ru|en] [--channel ..]
  conflicts                           -> магниты, под которыми вышло >1 слова
  validate                            -> целостность реестра (для хука); exit 2 при нарушении
  list                                -> весь burn-list
  selftest                            -> прогон встроенных проверок сверки с CAROUSEL-REGISTRY
                                          + разбора секции «Конфликты» (позитив/негатив)

Реестр (markdown-таблицы): ~/.business/scripts/auto-uniqualize/used_codewords.md
Парсятся секции, начинающиеся с:
  '## Активные'  -> magnet->word (активный индекс) + burn
  '## Легаси'    -> burn
  '## Слова конкурентов' -> burn
  '## ⚠️ Конфликты' -> burn ТОЛЬКО (не в активный индекс, "какое слово реально
     настроено в боте" по-прежнему решает автор, не парсер). Секция физически
     содержит ТРИ формата таблиц вперемешку (посчитано построчно по решению автора):
       A) 4 колонки, магнит первым: | Магнит | Слова, что выходили |
          Выставлено активным | Подтвердить/поменять | (4 строки данных)
       B) 5 колонок, слово первым, как активная таблица: | Слово | Магнит
          или "-" | Канал | Дата | Язык | (47 строк данных)
       C) 5 колонок, shortcode первым, слово в 3-й колонке:
          | shortcode | дата | код-слово | донор | тема | (1 строка данных)
     Формат-агностичный разбор по ФОРМЕ ячейки (код-слово = капс без
     пробелов), см. _conflict_row(). Прецедент по решению автора (волна r14): агент
     чуть не задвоил слово ПОДПИСКА на новый лид-магнит, потому что вся
     секция игнорировалась целиком вместе с колонкой «Выставлено активным»,
     где ПОДПИСКА уже жила за магнитом guide-claude-kupit-podpisku. Добивка
     по решению автора: первый заход по решению автора переписал только докстринг, разбор
     физически не был подключён (`_section_kind()` не знал заголовок
     секции, `_conflict_row()` не существовал) - ПОДПИСКА оставалась
     СВОБОДНО. Здесь разбор реально подключён под все 3 формы.
Прочие секции игнорируются.

Второй, независимый реестр :
  ~/.business/CAROUSEL-REGISTRY.md  ("## Карта код-слов", таблица
  | **СЛОВО** | Тип | Тул/тема | Статья | Live | Кол-во |)
check и reserve ДОПОЛНИТЕЛЬНО сверяются с этим файлом. Если слово там уже есть -
ЗАНЯТО/ОТКАЗ с указанием чем именно (статья или тип+«без живой статьи»), exit 2.
Файла нет на машине -> сверка молча пропускается, поведение как раньше.
"""
import argparse
import json
import os
import re
import sys
import tempfile

REGISTRY = os.path.expanduser("~/.business/scripts/auto-uniqualize/used_codewords.md")
# второй, независимый источник истины (карусель/рилз -> код-слово -> статья);
# см. докстринг модуля. Читается УСЛОВНО: нет файла на машине - сверка пропускается.
CAROUSEL_REGISTRY = os.path.expanduser("~/.business/CAROUSEL-REGISTRY.md")
CAROUSEL_TABLE_HEADER = "## Карта код-слов"

# ТРЕТИЙ независимый источник истины - очередь код-слов SEO-конвейера.
# Прецедент по решению автора (волна r20): волна r19 записала свои слова ТОЛЬКО сюда,
# и `check` отдавал по ним «СВОБОДНО» - ложный зелёный, за которым следующая
# волна берёт занятое слово. Читается УСЛОВНО: нет файла - сверка пропускается.
SEO_QUEUE = os.path.expanduser(
    ".business/growth/seo/lead-magnit-work/_registry/codewords.jsonl")

SEC_ACTIVE = "active"
SEC_BURN = "burn"
SEC_CONFLICT = "conflict"
SEC_SKIP = "skip"


def _norm_word(w: str) -> str:
    return w.strip().strip("«»\"'`*").strip().casefold()


def _norm_magnet(m: str) -> str:
    m = m.strip().casefold()
    m = re.sub(r"\s+", " ", m)
    return m


def _section_kind(header: str) -> str:
    h = header.lower()
    if h.startswith("## активные"):
        return SEC_ACTIVE
    if h.startswith("## легаси") or h.startswith("## слова конкурентов"):
        return SEC_BURN
    if h.startswith("##") and "конфликты" in h:
        return SEC_CONFLICT
    return SEC_SKIP


_WORD_SHAPE_RE = re.compile(r"^[A-ZА-ЯЁ][A-ZА-ЯЁ0-9-]*$")


def _looks_like_word(cell: str) -> bool:
    """Код-слово = одно слово капсом (кириллица/латиница), без пробелов.
    Магнит/фраза/shortcode = пробелы и/или строчные буквы. Опорное правило
    различения форм секции «Конфликты», см. докстринг модуля."""
    c = cell.strip().strip("«»\"'`*").strip()
    if not c or " " in c:
        return False
    return bool(_WORD_SHAPE_RE.match(c))


def _conflict_row(cells):
    """Возвращает [(display_word, magnet_display), ...] для ВСЕХ код-слов,
    найденных в одной строке секции «⚠️ Конфликты» - секция физически
    содержит 3 разные формы таблиц вперемешку (A/B/C, см. докстринг модуля).
    Различение по ФОРМЕ ячейки, не по номеру колонки. Форма A может дать
    НЕСКОЛЬКО слов из одной строки (все исторические + активное - решение
    не принято автором, значит жжём все кандидаты, не только один).
    Нераспознанная форма (заголовок/мусор) -> [] - ничего не теряем и
    ничего не жжём ошибочно."""
    n = len(cells)
    if n == 4:
        magnet, words_list, active_word = cells[0], cells[1], cells[2]
        out = []
        for w in words_list.split(","):
            w = w.strip()
            if _looks_like_word(w):
                out.append((w, magnet))
        aw = active_word.strip()
        if _looks_like_word(aw) and aw not in [o[0] for o in out]:
            out.append((aw, magnet))
        return out
    if n == 5:
        first, second, third = cells[0], cells[1], cells[2]
        if _looks_like_word(first):
            # форма B: слово первым, магнит во 2-й колонке (может быть "-")
            magnet = second if second and second != "-" else (third or "конфликт")
            return [(first, magnet)]
        if _looks_like_word(third):
            # форма C: shortcode | дата | СЛОВО | донор | тема
            magnet = cells[4] if len(cells) > 4 and cells[4] else (cells[3] if len(cells) > 3 else "конфликт")
            return [(third, magnet)]
        return []
    return []


def parse(path: str = REGISTRY):
    """Возвращает (burn, active) где
    burn = { norm_word: (display_word, magnet, kind) }  все занятые строки
    active = list of (norm_word, display_word, magnet_raw, lang)  только активные
    """
    burn = {}
    active = []
    if not os.path.exists(path):
        return burn, active
    kind = SEC_SKIP
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if s.startswith("## "):
                kind = _section_kind(s)
                continue
            if kind == SEC_SKIP:
                continue
            if not s.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            w_raw = cells[0]
            # пропустить заголовок таблицы и разделитель (общее для всех форм)
            if set(w_raw) <= set("-: ") and w_raw:
                continue
            if w_raw.lower() in ("слово", "codeword", "код-слово", "word", "магнит", "shortcode"):
                continue

            if kind == SEC_CONFLICT:
                # секция физически содержит 3 формы таблиц вперемешку —
                # см. _conflict_row(). Слово из ЛЮБОЙ формы уходит ТОЛЬКО в
                # burn, никогда в active (какое слово реально подключено в
                # боте — решает автор, не парсер).
                for w_disp, m_disp in _conflict_row(cells):
                    nw2 = _norm_word(w_disp)
                    if not nw2:
                        continue
                    burn.setdefault(
                        nw2,
                        (
                            w_disp.strip(),
                            m_disp.strip() if m_disp else "конфликт (used_codewords.md, под решение автора)",
                            SEC_CONFLICT,
                        ),
                    )
                continue

            magnet = cells[1]
            nw = _norm_word(w_raw)
            if not nw:
                continue
            lang = cells[4] if len(cells) >= 5 else ""
            burn.setdefault(nw, (w_raw.strip(), magnet, kind))
            if kind == SEC_ACTIVE:
                active.append((nw, w_raw.strip(), magnet, lang.strip().lower()))
    return burn, active


def parse_carousel_registry(path: str = CAROUSEL_REGISTRY):
    """Читает CAROUSEL-REGISTRY.md, только таблицу под заголовком '## Карта код-слов':
      | **СЛОВО** | Тип | Тул/тема | Статья | Live | Кол-во |
    Возвращает { norm_word: (display_word, type_, article_url, live_mark) }.
    Условное чтение: файла нет на этой машине -> {} (сверку вызывающий код молча
    пропускает), чтение сломано -> {} (не роняем check/reserve).
    Сравнение — ТОЛЬКО по точному совпадению нормализованного слова (не по
    подстроке), иначе «СТУДИЯ» ловила бы «СТУДИЙНЫЙ» и подобное.
    """
    reg = {}
    if not os.path.exists(path):
        return reg
    try:
        in_table = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.rstrip("\n")
                if s.startswith("## "):
                    in_table = s.strip() == CAROUSEL_TABLE_HEADER
                    continue
                if not in_table or not s.lstrip().startswith("|"):
                    continue
                cells = [c.strip() for c in s.strip().strip("|").split("|")]
                if len(cells) < 5:
                    continue
                w_raw = cells[0]
                if set(w_raw) <= set("-: ") and w_raw:
                    continue  # разделитель таблицы (|---|---|...)
                if _norm_word(w_raw) in ("код-слово", "codeword", "word"):
                    continue  # шапка таблицы
                nw = _norm_word(w_raw)  # снимает ** и casefold — раскладка регистра не важна
                if not nw:
                    continue
                type_ = cells[1] if len(cells) > 1 else ""
                article = cells[3] if len(cells) > 3 else ""
                live = cells[4] if len(cells) > 4 else ""
                disp = w_raw.strip().strip("*").strip()  # снять markdown-жирность для вывода
                reg.setdefault(nw, (disp, type_, article, live))
    except OSError:
        return {}
    return reg


def _carousel_conflict_note(nw: str, path: str = CAROUSEL_REGISTRY):
    """Если nw занято в CAROUSEL-REGISTRY — вернуть готовую строку-пояснение
    «чем именно занято», иначе None."""
    creg = parse_carousel_registry(path)
    if nw not in creg:
        return None
    disp, type_, article, live = creg[nw]
    where = article if article and article != "—" else f"{type_ or 'карусель'} (без живой статьи в карте)"
    return f"«{disp}» -> {where} [CAROUSEL-REGISTRY, live={live or '—'}]"


def parse_seo_queue(path: str = SEO_QUEUE):
    """Очередь код-слов SEO-конвейера (jsonl). Возвращает {норм_слово: (показ, чем занято)}.

    Две формы строки живут в файле одновременно и обе легальны:
      · новая  - {"resource": "codeword", "value": "СЛОВО", "keyword": ..., "slug": ...}
      · старая - {"codeword": "СЛОВО", "target_keyword": ..., "slug": ...}
    Строка со `status` = released освобождает слово, всё остальное занимает.
    Файла нет или он битый - пусто, а не падение: инструмент раздаётся и на машины
    без SEO-конвейера.
    """
    reg = {}
    if not path or not os.path.exists(path):
        return reg
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return reg
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        word = row.get("value") if row.get("resource") == "codeword" else None
        if not word:
            word = row.get("codeword")
        if not word:
            continue
        nw = _norm_word(str(word))
        if not nw:
            continue
        status = str(row.get("status") or "").lower()
        if status == "released":
            reg.pop(nw, None)
            continue
        magnet = (row.get("keyword") or row.get("target_keyword")
                  or row.get("slug") or "тема SEO-очереди")
        slug = row.get("slug") or ""
        where = f"{magnet}" + (f" ({slug})" if slug and slug != magnet else "")
        reg[nw] = (str(word).strip(), where)
    return reg


def _seo_conflict_note(nw: str, path: str = SEO_QUEUE):
    """Занято ли nw в очереди SEO-конвейера - готовая строка-пояснение, иначе None."""
    reg = parse_seo_queue(path)
    if nw not in reg:
        return None
    disp, where = reg[nw]
    return f"«{disp}» -> {where} [SEO-очередь codewords.jsonl]"


def _magnet_match(query: str, magnet: str) -> bool:
    q, m = _norm_magnet(query), _norm_magnet(magnet)
    if not q or not m:
        return False
    # плейсхолдер вместо магнита («-», «—» и т.п.) не должен матчиться с чем угодно
    if not re.search(r"\w", q) or not re.search(r"\w", m):
        return False
    if q in m or m in q:
        return True
    qt = set(re.findall(r"\w+", q))
    mt = set(re.findall(r"\w+", m))
    # стоп-слова слагов: генерик-префиксы не несут смысла магнита - без этого
    # два разных guide-слага с ОДНИМ общим словом склеивались в «тот же магнит»
    # 
    stop = {"guide", "гайд", "dlya", "для"}
    qt = {t for t in qt if len(t) > 2 and t not in stop}
    mt = {t for t in mt if len(t) > 2 and t not in stop}
    if not qt:
        return False
    overlap = qt & mt
    return len(overlap) >= max(2, len(qt) // 2)


def cmd_check(args):
    burn, _ = parse()
    nw = _norm_word(args.word)
    if nw in burn:
        disp, magnet, kind = burn[nw]
        print(f"ЗАНЯТО: «{disp}» -> {magnet} [{kind}]")
        return 2
    note = _carousel_conflict_note(nw)
    if note:
        print(f"ЗАНЯТО: {note}")
        return 2
    note = _seo_conflict_note(nw)
    if note:
        print(f"ЗАНЯТО: {note}")
        return 2
    print(f"СВОБОДНО: «{args.word.strip()}»")
    return 0


def cmd_for_magnet(args):
    _, active = parse()
    hits = [(d, m, lang) for (_, d, m, lang) in active if _magnet_match(args.magnet, m)]
    if args.lang:
        hits = [h for h in hits if h[2] == args.lang.lower()] or hits
    if hits:
        for d, m, lang in hits:
            print(f"ЕСТЬ: «{d}» -> {m} ({lang or '—'})  ПЕРЕИСПОЛЬЗУЙ это слово")
        return 0
    print("НЕТ активного слова под этот магнит — можно резервировать новое")
    return 3


def cmd_reserve(args):
    burn, active = parse()
    nw = _norm_word(args.word)
    if not nw or not re.fullmatch(r"[a-zа-яё-]{3,}", nw):
        print(f"ОТКАЗ: «{args.word}» не похоже на код-слово (нужно ≥3 букв, одно слово)")
        return 2
    # 1) у магнита уже есть активное слово?
    existing = [(d, m) for (_, d, m, _l) in active if _magnet_match(args.magnet, m)]
    if existing:
        d, m = existing[0]
        if _norm_word(d) == nw:
            print(f"OK: «{d}» уже закреплено за этим магнитом ({m})")
            return 0
        print(f"ОТКАЗ: у магнита «{m}» уже активно слово «{d}». "
              f"ПЕРЕИСПОЛЬЗУЙ «{d}», не плоди новое.")
        return 2
    # 2) строка уже занята под что-то другое?
    if nw in burn:
        disp, magnet, kind = burn[nw]
        print(f"ОТКАЗ: «{disp}» уже занято под «{magnet}» [{kind}]. Выбери другое.")
        return 2
    # 2b) занято в CAROUSEL-REGISTRY (второй независимый источник истины —
    # прецедент по решению автора: СТУДИЯ была занята живой каруселью, но не видна
    # этому скрипту из его собственного used_codewords.md)
    note = _carousel_conflict_note(nw)
    if note:
        print(f"ОТКАЗ: {note}. Выбери другое.")
        return 2
    # 2в) занято в очереди SEO-конвейера (третий источник, прецедент по решению автора)
    note = _seo_conflict_note(nw)
    if note:
        print(f"ОТКАЗ: {note}. Выбери другое.")
        return 2
    # 3) свободно -> добавить строку в активную таблицу нужного языка
    lang = (args.lang or "ru").lower()
    channel = args.channel or "carousel"
    date = args.date or ""
    row = f"| {args.word.strip()} | {args.magnet.strip()} | {channel} | {date} | {lang} |"
    if not _append_active_row(row, lang):
        print("ОТКАЗ: не нашёл активную таблицу для языка — добавь строку вручную:")
        print(row)
        return 1
    print(f"ЗАБРОНИРОВАНО: «{args.word.strip()}» -> {args.magnet.strip()} ({lang})")
    return 0


def _append_active_row(row: str, lang: str) -> bool:
    with open(REGISTRY, encoding="utf-8") as f:
        lines = f.readlines()
    want = "ru" if lang != "en" else "en"
    hdr_re = re.compile(r"^## Активные слова .*\b(RU|EN)\b", re.I)
    target_idx = None
    cur = None
    for i, ln in enumerate(lines):
        m = hdr_re.match(ln.strip())
        if m:
            cur = m.group(1).lower()
        if cur == want and ln.lstrip().startswith("|"):
            target_idx = i  # последняя строка таблицы нужного языка
        elif cur == want and target_idx is not None and not ln.lstrip().startswith("|") and ln.strip():
            break
    if target_idx is None:
        return False
    lines.insert(target_idx + 1, row + "\n")
    with open(REGISTRY, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def cmd_conflicts(args):
    burn, active = parse()
    by_magnet = {}
    for nw, d, m, _l in active:
        by_magnet.setdefault(_norm_magnet(m), []).append(d)
    # добить легаси к тем же магнитам
    for nw, (d, m, kind) in burn.items():
        if kind == SEC_BURN:
            key = _norm_magnet(m)
            if key in by_magnet and d not in by_magnet[key]:
                by_magnet[key].append(d + " (легаси)")
    bad = {k: v for k, v in by_magnet.items() if len({w.split(" (")[0] for w in v}) > 1}
    if not bad:
        print("Конфликтов нет: каждый магнит = одно слово.")
        return 0
    print("КОНФЛИКТЫ (магнит -> несколько слов):")
    for k, v in bad.items():
        print(f"  • {k}: {', '.join(v)}")
    return 2


def cmd_validate(args):
    burn, active = parse()
    problems = []
    # инвариант: одна строка-слово под максимум один магнит в активных
    seen = {}
    for nw, d, m, _l in active:
        if nw in seen and _norm_magnet(seen[nw]) != _norm_magnet(m):
            problems.append(f"строка «{d}» активна под двумя магнитами: «{seen[nw]}» и «{m}»")
        seen[nw] = m
    # дубль активного слова (одинаковая строка дважды активна)
    counts = {}
    for nw, d, m, _l in active:
        counts.setdefault(nw, []).append(m)
    for nw, ms in counts.items():
        if len(ms) > 1 and len({_norm_magnet(x) for x in ms}) == 1 and len(ms) > 1:
            # одинаковый магнит дважды — тоже дубль строки
            problems.append(f"строка «{nw}» добавлена в активные {len(ms)} раз")
    if problems:
        print("РЕЕСТР НЕВАЛИДЕН:")
        for p in problems:
            print("  ✗ " + p)
        return 2
    print(f"Реестр валиден: {len(active)} активных, {len(burn)} занятых строк.")
    return 0


# --- detector для хука: ловит код-слово-CTA в публикуемом тексте ---
_VERB = r"(?:напиш\w*|пиш\w*|пришл\w*|отправ\w*|кин\w*|комментир\w*|коммент\w*|write|comment|send|drop|dm)"
_CTX = r"(?:бот\w*|директ\w*|личк\w*|коммент\w*|\bdm\b|ссылк\w*|получ\w*|пришл\w*|скин\w*|вышл\w*|в\s+ответ|magnet|lead|лид-?магнит)"
# глагол регистронезависим, а САМ токен — строго ЗАГЛАВНЫЙ; токен ищем кодом в окне после глагола
_VERB_RE = re.compile(r"(?i:" + _VERB + r")")
_CAPS_RE = re.compile(r"([А-ЯЁA-Z]{3,}[А-ЯЁA-Z-]*)")
# «кодовое слово ТОКЕН» / «код-слово ТОКЕН» / «codeword TOKEN» — токен сразу после фразы
_KW_RE = re.compile(r"(?i:кодов\w*\s+слов\w*|код-?слов\w*|code\s?word)[\s«»\"“„':\-—]+([А-ЯЁA-Z]{3,}[А-ЯЁA-Z-]*)")
# не код-слова: техно/служебные капс-токены
_ALLOW = {
    "cta", "dm", "pdf", "ai", "url", "tg", "ig", "ftp", "html", "css", "json",
    "api", "ok", "ru", "en", "usa", "gpt", "mcp", "seo", "faq", "vpn", "llm",
    "png", "jpg", "mp4", "csv", "xml", "http", "https", "id", "ux", "ui",
    "стоп", "ага", "ого", "вау",
}


def cmd_scan(args):
    """Читает текст со stdin. Если в нём публикуется НЕзарегистрированное код-слово
    в CTA-контексте — exit 2 с подсказкой. Иначе exit 0. Используется хуком."""
    text = sys.stdin.read()
    if not text.strip():
        return 0
    low = text.lower()
    has_codeword_kw = ("кодов" in low) or ("код-слов" in low) or ("codeword" in low) or ("code word" in low)
    burn, _ = parse()
    violations = []
    # паттерн «кодовое слово ТОКЕН» (токен сразу после фразы, до/без глагола)
    for km in _KW_RE.finditer(text):
        token = km.group(1)
        nt = _norm_word(token)
        if nt in _ALLOW or len(nt) < 3 or nt in burn:
            continue
        if token not in violations:
            violations.append(token)
    for vm in _VERB_RE.finditer(text):
        window = text[vm.end():vm.end() + 30]   # первый ЗАГЛАВНЫЙ токен в окне после глагола
        cm = _CAPS_RE.search(window)
        if not cm:
            continue
        token = cm.group(1)
        nt = _norm_word(token)
        if nt in _ALLOW or len(nt) < 3:
            continue
        tok_end = vm.end() + cm.end()
        tail = text[tok_end:tok_end + 70]
        # сильный сигнал: рядом контекст бота/лид-магнита ИЛИ в тексте есть «кодовое слово»
        if not (has_codeword_kw or re.search(_CTX, tail, re.I | re.U)):
            continue
        if nt in burn:
            continue  # зарегистрировано — ок
        if token not in violations:
            violations.append(token)
    if violations:
        sys.stderr.write(
            "🛑 BLOCKED (код-слова): в публикуемом тексте код-слово(а) "
            + ", ".join(f"«{v}»" for v in violations)
            + " НЕ в реестре. Это и есть конфликт — слово могло быть занято или "
            "магнит уже имеет своё слово.\n"
            "Сделай ДО публикации:\n"
            "  python3 ~/.business/scripts/codewords.py for-magnet \"<что выдаём>\"  "
            "# уже есть слово под магнит? переиспользуй\n"
            "  python3 ~/.business/scripts/codewords.py reserve --magnet \"<...>\" --word "
            + violations[0]
            + " --lang ru   # забронировать новое\n"
            "Реестр: ~/.business/scripts/auto-uniqualize/used_codewords.md\n"
        )
        return 2
    return 0


def cmd_list(args):
    burn, _ = parse()
    for nw in sorted(burn):
        d, m, kind = burn[nw]
        print(f"{d:<14} [{kind:<8}] {m}")
    return 0


_SELFTEST_FIXTURE = """# fixture
## Карта код-слов

| Код-слово | Тип | Тул/тема | Статья | Live | Кол-во |
|---|---|---|---|---|---|
| **СТУДИЯ** | микс | тест | https://example.com/guide-studiya/ | ✅ | 2 |
| **СТУДИЙНЫЙ** | карусель | тест на ложную подстроку | — | 🔨 нет в карте | 1 |
| **ГАП** | карусель | тест без живой статьи | — | 🔨 нет в карте | 1 |

## 🔨 ПРОБЕЛЫ — код-слова без живой статьи (СОБРАТЬ):
- **ГАП** — тест → —
"""

# фикстура секции «⚠️ Конфликты» - три реальные формы таблиц вперемешку
# (добивка по решению автора, см. докстринг модуля и _conflict_row()).
_CONFLICT_FIXTURE = """# fixture-conflicts
## Активные слова — RU (один магнит = одно слово)

| Слово | Магнит | Канал | Дата | Язык |
|---|---|---|---|---|
| ФИКСАКТИВ | обычный активный магнит теста | carousel | 2026-01-01 | ru |

## ⚠️ Конфликты под решение автора (какое слово реально настроено в боте)

| Магнит | Слова, что выходили | Выставлено активным | Подтвердить/поменять |
|---|---|---|---|
| тестовый магнит формы А | ФИКССТАРОЕ, ФИКСНОВОЕ | ФИКСНОВОЕ | ? |

| ФИКСФОРМАБ | магнит формы Б, слово первым | карусель |  | ru |
| ФИКСДЕФИС | - | рилз |  | ru |

| shortcode | дата | код-слово | донор | тема |
| ABc123xY_z | по решению автора | ФИКСФОРМАВ | @someone | тестовая тема формы В |
"""


def cmd_selftest(args):
    """Минимальный встроенный прогон гарда CAROUSEL-REGISTRY: занятое слово,
    свободное слово, слово с подстрокой-ловушкой, отсутствующий файл реестра."""
    ok = True

    def check(name, cond):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [{status}] {name}")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(_SELFTEST_FIXTURE)
        fixture_path = tf.name
    try:
        print("selftest: занятое реестром слово (СТУДИЯ, точное совпадение)")
        reg = parse_carousel_registry(fixture_path)
        check("СТУДИЯ найдена в фикстуре", _norm_word("СТУДИЯ") in reg)
        note = _carousel_conflict_note(_norm_word("СТУДИЯ"), fixture_path)
        check("conflict-note не пустая и содержит ссылку на статью",
              bool(note) and "example.com/guide-studiya" in note)

        print("selftest: слово без живой статьи в карте (ГАП) — всё равно занято")
        note_gap = _carousel_conflict_note(_norm_word("ГАП"), fixture_path)
        check("ГАП распознан как занятый (без URL статьи)", bool(note_gap))

        print("selftest: ложная подстрока — СТУДИЯ не должна ловить СТУДИЙНЫЙ и наоборот")
        check(
            "«СТУДИЯ» и «СТУДИЙНЫЙ» — разные ключи реестра",
            _norm_word("СТУДИЯ") != _norm_word("СТУДИЙНЫЙ")
            and _norm_word("СТУДИЙНЫЙ") in reg,
        )
        note_free = _carousel_conflict_note(_norm_word("НЕТТАКОГОСЛОВАВООБЩЕ"), fixture_path)
        check("явно свободное слово не даёт конфликта", note_free is None)

        print("selftest: раскладка/оформление — нижний регистр и без **")
        check(
            "casefold + без ** совпадает с «**СТУДИЯ**»",
            _carousel_conflict_note(_norm_word("студия"), fixture_path) is not None,
        )
    finally:
        os.unlink(fixture_path)

    print("selftest: файла реестра нет на машине — сверка молча пропускается, не падает")
    missing_path = fixture_path + ".does-not-exist"
    reg_missing = parse_carousel_registry(missing_path)
    check("несуществующий путь -> {} без исключения", reg_missing == {})
    check(
        "conflict-note на несуществующем файле -> None (не блокирует check/reserve)",
        _carousel_conflict_note(_norm_word("СТУДИЯ"), missing_path) is None,
    )

    print("selftest: ТРЕТИЙ источник - очередь SEO-конвейера (jsonl)")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as jf:
        jf.write(
            '{"resource":"codeword","value":"ФИКСНОВАЯ","keyword":"тема новой формы",'
            '"slug":"guide-fiksnovaya","status":"queued"}\n'
            '{"codeword":"ФИКССТАРАЯ","target_keyword":"тема старой формы",'
            '"slug":"guide-fiksstaraya","status":"queued"}\n'
            '{"resource":"codeword","value":"ФИКСОТДАННАЯ","keyword":"тема отданная",'
            '"slug":"guide-fiksotdannaya","status":"queued"}\n'
            '{"resource":"codeword","value":"ФИКСОТДАННАЯ","keyword":"тема отданная",'
            '"slug":"guide-fiksotdannaya","status":"released"}\n'
            'это не json, строка обязана быть пропущена без падения\n'
            '{"resource":"article","slug":"guide-ne-kodoslovo","status":"queued"}\n'
        )
        jpath = jf.name
    try:
        qreg = parse_seo_queue(jpath)
        check("новая форма записи (value) прочитана",
              _norm_word("ФИКСНОВАЯ") in qreg)
        check("старая форма записи (codeword) прочитана",
              _norm_word("ФИКССТАРАЯ") in qreg)
        check("status=released ОСВОБОЖДАЕТ слово",
              _norm_word("ФИКСОТДАННАЯ") not in qreg)
        check("строка не-codeword (resource=article) словом не считается",
              len(qreg) == 2)
        note_q = _seo_conflict_note(_norm_word("ФИКСНОВАЯ"), jpath)
        check("нота занятости называет и тему, и слаг",
              bool(note_q) and "guide-fiksnovaya" in note_q and "SEO-очередь" in note_q)
        check("свободное слово по очереди не конфликтует",
              _seo_conflict_note(_norm_word("НЕТТАКОГОСЛОВАВОЧЕРЕДИ"), jpath) is None)
        check("битая строка не роняет разбор", True)
    finally:
        os.unlink(jpath)

    print("selftest: очереди SEO нет на машине - сверка молча пропускается")
    check("несуществующий путь очереди -> {} без исключения",
          parse_seo_queue(jpath + ".does-not-exist") == {})
    check("нота на несуществующей очереди -> None",
          _seo_conflict_note(_norm_word("ФИКСНОВАЯ"), jpath + ".does-not-exist") is None)

    print("selftest: реальный CAROUSEL_REGISTRY этой машины (если есть)")
    if os.path.exists(CAROUSEL_REGISTRY):
        real = parse_carousel_registry()
        print(f"  прочитано записей: {len(real)} из {CAROUSEL_REGISTRY}")
        check("реальный реестр не пустой", len(real) > 0)
    else:
        print(f"  {CAROUSEL_REGISTRY} отсутствует на этой машине — пропуск (ожидаемо)")

    print("selftest: секция «⚠️ Конфликты» — 3 формы таблиц вперемешку (добивка по решению автора)")
    check(
        "НЕГАТИВНЫЙ: _section_kind() распознаёт заголовок секции конфликтов",
        _section_kind("## ⚠️ Конфликты под решение автора (какое слово реально настроено в боте)")
        == SEC_CONFLICT,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(_CONFLICT_FIXTURE)
        conflict_fixture_path = tf.name
    try:
        cburn, cactive = parse(conflict_fixture_path)

        print("  форма A (4 колонки, магнит первым) — оба слова строки жгутся")
        check("НЕГАТИВНЫЙ: ФИКССТАРОЕ (форма A, список «что выходили») занято",
              _norm_word("ФИКССТАРОЕ") in cburn)
        check("НЕГАТИВНЫЙ: ФИКСНОВОЕ (форма A, «выставлено активным») занято",
              _norm_word("ФИКСНОВОЕ") in cburn)

        print("  форма B (5 колонок, слово первым, как активная таблица)")
        check("НЕГАТИВНЫЙ: ФИКСФОРМАБ (форма B) занято", _norm_word("ФИКСФОРМАБ") in cburn)
        check("ФИКСДЕФИС (форма B, магнит-плейсхолдер «-») занято", _norm_word("ФИКСДЕФИС") in cburn)

        print("  форма C (5 колонок, shortcode первым, слово в 3-й колонке)")
        check("НЕГАТИВНЫЙ: ФИКСФОРМАВ (форма C, слово НЕ в 1-й колонке) занято",
              _norm_word("ФИКСФОРМАВ") in cburn)
        check(
            "shortcode ABc123xY_z НЕ принят за код-слово (форма C не путает колонку 1)",
            _norm_word("ABc123xY_z") not in cburn,
        )

        print("  заголовки таблиц секции не протекают в burn как слова")
        check("«Магнит» (заголовок формы A) не в burn", _norm_word("Магнит") not in cburn)
        check("«код-слово» (заголовок формы C) не в burn", _norm_word("код-слово") not in cburn)

        print("  соседние секции и закон «конфликт -> только burn, не active» не пострадали")
        check("ФИКСАКТИВ (обычная активная секция) по-прежнему занято",
              _norm_word("ФИКСАКТИВ") in cburn)
        check(
            "ФИКСАКТИВ попал в active-индекс (магнит-матчинг вне конфликтов не сломан)",
            any(nw == _norm_word("ФИКСАКТИВ") for nw, *_ in cactive),
        )
        check(
            "ни одно слово секции конфликтов не попало в active-индекс (решает автор, не парсер)",
            not any(
                nw in {_norm_word(w) for w in ("ФИКССТАРОЕ", "ФИКСНОВОЕ", "ФИКСФОРМАБ", "ФИКСФОРМАВ")}
                for nw, *_ in cactive
            ),
        )
        check("заведомо свободное слово в фикстуре свободно",
              _norm_word("НИГДЕНЕТТАКОГОСЛОВАФИКС") not in cburn)
    finally:
        os.unlink(conflict_fixture_path)

    print("selftest: реальный used_codewords.md — ПОДПИСКА ")
    real_burn, _ = parse()
    check(
        "НЕГАТИВНЫЙ: ПОДПИСКА (форма B, реальная секция конфликтов) определена занятой",
        _norm_word("ПОДПИСКА") in real_burn,
    )
    check(
        "АРСЕНАЛ (упомянуто в форме A секции конфликтов, само тоже активное) по-прежнему занято",
        _norm_word("АРСЕНАЛ") in real_burn,
    )
    check(
        "КЛУБ (слово из обычной секции активных, вне конфликтов) по-прежнему занято",
        _norm_word("КЛУБ") in real_burn,
    )
    print("  волна r14 — все 10 забронированных слов целы")
    for wave_word in ("ОЖИВЛЕНИЕ", "ЛОКАЛКА", "ГОЛОС", "ГОСТЬ", "ДИАЛОГ",
                      "ГЕНЕРАЦИЯ", "ШТРИХ", "ПОВОД", "СЮЖЕТ", "ПРИМЕРКА"):
        check(f"волна r14: {wave_word} по-прежнему занято", _norm_word(wave_word) in real_burn)

    print("ИТОГ:", "ВСЕ PASS" if ok else "ЕСТЬ FAIL")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="Контроль кодовых слов")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check"); c.add_argument("word"); c.set_defaults(fn=cmd_check)
    c = sub.add_parser("for-magnet"); c.add_argument("magnet"); c.add_argument("--lang"); c.set_defaults(fn=cmd_for_magnet)
    c = sub.add_parser("reserve")
    c.add_argument("--magnet", required=True); c.add_argument("--word", required=True)
    c.add_argument("--lang"); c.add_argument("--channel"); c.add_argument("--date")
    c.set_defaults(fn=cmd_reserve)
    c = sub.add_parser("conflicts"); c.set_defaults(fn=cmd_conflicts)
    c = sub.add_parser("validate"); c.set_defaults(fn=cmd_validate)
    c = sub.add_parser("scan"); c.set_defaults(fn=cmd_scan)
    c = sub.add_parser("list"); c.set_defaults(fn=cmd_list)
    c = sub.add_parser("selftest"); c.set_defaults(fn=cmd_selftest)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
