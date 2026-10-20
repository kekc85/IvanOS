#!/usr/bin/env python3
"""
copy-lint.py — МАШИННЫЙ детектор проверяемых дефектов КОПИ перед показом (без LLM).
Закрывает DEFERRED-пункты аудита по решению автора машинной проверкой на артефакте:

  A. EM-DASH «—» (U+2014) внутри текста — универсальный AI-tell + ToV автора (короткое
     тире «–»/дефис ок, длинное «—» — нет). / humaniser.
  B. РЕГИСТР КОПИ ≠ ТИП САЙТА — для контент-хаба/блога/newsletter продающие слова
     (купи/оплати/тариф/заказать/цена) в копи = брак регистра (прецедент: герой
     контент-хаба написали как продуктовый лендинг). Для landing/product — не триггерит.
  C. ПРОСЛЕЖИВАЕМОСТЬ ЧИСЕЛ — claim-число (деньги/проценты/крупный счёт/с единицей)
     в копи, которого НЕТ в interview.md (источник истины) = возможная выдумка под
     именем эксперта. Машина не проверяет ИСТИННОСТЬ, но требует ТРАССИРОВКУ к источнику.
  D. АНГЛИЦИЗМЫ-КАЛЬКИ — типовые кальки (онбординг/фреймворк/инсайт/воркфлоу/комьюнити…)
     в RU-копи → BLOCK с предложением русской замены. Whitelist собственных терминов
     читается из blueprint.md/glossary/config.md; нет файла → строгий режим (whitelist
     пуст).
  E. ВИСЯЧИЕ ТОЧКИ — короткая строка-копи (заголовок/буллет/CTA/плашка), оканчивающаяся
     одиночной «.» → BLOCK (ToV автора: точек в конце строк нет). Многострочные абзацы
     НЕ трогаем (высокий FP).
  F. РЕНДЕР-ЛИНТ — извлекаем ВИДИМЫЙ текст из index.html (без тегов) и прогоняем
     A/D/E ТАМ ЖЕ: пользователь видит рендер, не copy.md. (--html index.html)
  G. СОГЛАСОВАННОСТЬ ОФФЕРА — расхождение числа ЦЕНЫ между блоками hero/pricing/CTA
     внутри index.html → BLOCK (правил цену на одном экране, в другом старая). (--html)
  H. CLAIM-МАРКЕРЫ — текстовые маркеры доверия (единственный/первый/№1/работал с/
     N клиентов/гарантирую) в копи требуют source-tag в blueprint.md/interview.md,
     иначе BLOCK.

Использование:
    python3 copy-lint.py <copy.md> [--site-type "<type>"] [--interview <iv.md>]
                                   [--blueprint <bp.md>] [--html <index.html>]
    python3 copy-lint.py --stdin --site-type landing < text
Exit: 0 = чисто; 3 = найден дефект (печатает offenders); 2 = ошибка ввода.
Safe-by-design: нет файла/пустой ввод → exit 0. Каждый класс независим (A/D/E всегда;
B только при типе контент-хаб; C только если дан --interview; F/G только при --html;
H требует --blueprint/--interview как источник source-tag, иначе все маркеры = BLOCK).
"""
import re
import sys

EMDASH = "—"  # —  (длинное тире). НЕ трогаем «–» U+2013 (en-dash) и «-» дефис.

# Продающие слова, недопустимые в копи контент-хаба/блога/newsletter (регистр)
SELL_WORDS = ["купи", "купить", "оплати", "оплатить", "оплата", "тариф", "заказать",
              "заказ", "купи сейчас", "купить сейчас", "в корзину", "оформить заказ",
              "стоимость", "цена курса", "успей купить"]
HUB_TYPES = ("hub", "хаб", "контент", "blog", "блог", "newsletter", "рассылк", "media", "медиа")

# claim-число: деньги / проценты / крупный счёт (3+ цифр) / число с «единицей доверия»
MONEY = re.compile(r"[$€₽]\s?\d[\d  .,]*|\b\d[\d  .,]*\s?(?:руб|₽|\$|€|долл|usd|eur)\b", re.I)
PERCENT = re.compile(r"\b\d+[.,]?\d*\s?%")
UNIT = re.compile(r"\b(\d[\d  .,]*)\s?(?:учеников|клиентов|студентов|проектов|лет|год[ао]?в?|"
                  r"раз|млн|млрд|тыс|k|к|x|×|часов|дней|недель|месяцев)\b", re.I)
BIGNUM = re.compile(r"\b\d{3,}\b")
YEAR = re.compile(r"\b(19|20)\d{2}\b")

# ───────── D. Англицизмы-кальки → русская замена ─────────
ANGLICISMS = {
    "онбординг": "адаптация / вступление",
    "онбординга": "адаптации",
    "фреймворк": "система / каркас",
    "фреймворка": "системы / каркаса",
    "фреймворки": "системы / каркасы",
    "инсайт": "озарение / находка",
    "инсайты": "озарения / находки",
    "инсайтов": "озарений / находок",
    "воркфлоу": "процесс / рабочий поток",
    "комьюнити": "сообщество / клуб",
    "хайп": "ажиотаж / шум",
    "хайлайт": "ключевое / главное",
    "воркаут": "тренировка",
    "чек-лист": "список-проверка / памятка",
    "чеклист": "список-проверка / памятка",
    "митинг": "встреча / созвон",
    "дедлайн": "срок",
    "фидбэк": "обратная связь / отклик",
    "фидбек": "обратная связь / отклик",
    "скилл": "навык",
    "скиллы": "навыки",
    "юзер": "пользователь",
    "юзеры": "пользователи",
    "ивент": "событие / мероприятие",
    "колл": "созвон / звонок",
    "пайплайн": "конвейер / воронка",
    "роадмап": "дорожная карта / план",
    "перформанс": "результативность",
    "челлендж": "вызов / марафон-испытание",
    "ресёрч": "исследование",
    "ресерч": "исследование",
    "инсайтовый": "содержательный",
    "лайфхак": "приём / хитрость",
    "тренд": "тенденция",
    "юзкейс": "сценарий применения",
}
# граница «слова» с учётом дефиса (чек-лист — один токен)
_ANGL_TOKEN = re.compile(r"[а-яёa-z]+(?:-[а-яёa-z]+)*", re.I)

# ───────── E. Висячая точка: короткая строка ─────────
# Триггер только на КОРОТКИХ строках (≤ MAX_WORDS слов и ≤ MAX_CHARS симв.) —
# заголовок/буллет/CTA/плашка. Длинный абзац (предложение с прозой) не трогаем.
DANGLING_MAX_WORDS = 7
DANGLING_MAX_CHARS = 70
# буллет-маркеры в начале короткой строки
_BULLET = re.compile(r"^\s*(?:[-*•·–—]|\d+[.)])\s+")

# ───────── H. Claim-маркеры доверия ─────────
# Рыночный контекст: scope-маркеры первенства/превосходства считаем CLAIM только рядом с ним.
CLAIM_SCOPE = re.compile(
    r"в\s+(?:мире|росси|стране|нише|категори|индустри|сегмент|сфере|отрасл)"
    r"|на\s+рынке|\bрын(?:ок|ка|ке|ку|ком|ков)\b|сред[иь]\s+\w|номер\s+один|№\s?1", re.I)
# (rx, label, requires_scope). requires_scope=True → флагуем ТОЛЬКО при рыночном контексте
# в окне ±60 символов (иначе обычный порядковый «твой первый проект» = ложный блок,
# адверс-ревью по решению автора). requires_scope=False → прямой claim, флагуем всегда без source-tag.
CLAIM_MARKERS = [
    (re.compile(r"(?<![а-яё])единственн", re.I), "единственный", True),
    (re.compile(r"(?<![а-яё])перв(?:ый|ым|ые|ая)\b", re.I), "первый", True),
    (re.compile(r"лучш(?:ий|ая|ие)\b", re.I), "лучший", True),
    (re.compile(r"лидер\b|лидирующ", re.I), "лидер", True),
    (re.compile(r"№\s?1|\bno\.?\s?1\b|\b#1\b|номер\s+(?:один|1)\b", re.I), "№1", False),
    (re.compile(r"работал[аи]?\s+с\b|сотрудничал[аи]?\s+с\b", re.I), "работал с", False),
    # «N клиентов» как ПОХВАЛЬБА (более/уже/свыше/N+), не нейтральный счёт —
    # голый счёт «<число учеников>» трассирует режим C (число↔interview), не дублируем.
    (re.compile(r"(?:более|свыше|уже|больше)\s+\d[\d  .,]*\s*(?:клиент|ученик|студент)"
                r"|\b\d[\d  .,]*\+\s*(?:клиент|ученик|студент)", re.I), "более N клиентов", False),
    (re.compile(r"гарантиру", re.I), "гарантирую", False),
]


def _digits(s):
    return re.sub(r"[^\d]", "", s)


# ───────── F. Извлечение видимого текста из HTML ─────────
def html_visible_text(html):
    # выкинуть script/style/head целиком
    h = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", html)
    h = re.sub(r"(?is)<!--.*?-->", " ", h)
    # <br> → перенос строки (чтобы строки копи не слипались)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    # блочные теги → перенос (чтобы заголовки/li не слипались с соседями)
    h = re.sub(r"(?i)</(p|div|li|h[1-6]|section|header|footer|a|span|button|td|th|tr)>", "\n", h)
    # остальные теги вырезать
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    # html-entities (минимум)
    h = (h.replace("&nbsp;", " ").replace("&mdash;", "—").replace("&ndash;", "–")
         .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
         .replace("&quot;", '"').replace("&#39;", "'"))
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in h.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def html_copy_lines(html):
    """Извлечь ТОЛЬКО короткую копи (заголовки/CTA/буллеты/плашки) из html —
    цель: висячая точка проверяется на них, а не на абзацах прозы (анти-FP)."""
    h = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", html)
    out = []
    for m in re.finditer(
        r"(?is)<(h[1-6]|button|li)\b[^>]*>(.*?)</\1>"
        r"|<a\b[^>]*\bclass=\"[^\"]*\b(?:btn|button|cta)\b[^\"]*\"[^>]*>(.*?)</a>"
        r"|<(span|div|p)\b[^>]*\bclass=\"[^\"]*\b(?:title|heading|badge|cta|btn|button|tagline|label|eyebrow)\b[^\"]*\"[^>]*>(.*?)</\3>",
            h):
        inner = next((g for g in m.groups()[1:] if g), "") or ""
        txt = html_visible_text(inner)
        for ln in txt.splitlines():
            ln = ln.strip()
            if ln:
                out.append(ln)
    return "\n".join(out)


def check_emdash(text, where=""):
    out = []
    w = f"[{where}] " if where else ""
    for i, line in enumerate(text.splitlines(), 1):
        if EMDASH in line:
            out.append(f"{w}стр.{i}: длинное тире «—» — «{line.strip()[:60]}» (используй «–»/дефис/запятую)")
    return out


def check_register(text, site_type):
    st = (site_type or "").lower()
    if not any(h in st for h in HUB_TYPES):
        return []
    out = []
    low = text.lower()
    for w in SELL_WORDS:
        if re.search(r"(?<![а-яёa-z])" + re.escape(w) + r"(?![а-яёa-z])", low):
            out.append(f"продающее слово «{w}» в копи контент-хаба (тип='{site_type}') — "
                       "регистр должен быть обещание контента + подписка, не продажа")
    return out


def check_numbers(text, interview_text):
    if interview_text is None:
        return []
    # Разделители тысяч (пробел/NBSP/thin/NNBSP/figure-space МЕЖДУ группами цифр по 3): «1 500»→«1500».
    # Иначе BIGNUM ловит хвост «500» как ОТДЕЛЬНЫЙ orphan-claim → ложный блок легитимной русской
    # типографики чисел (ре-ревью по решению автора). Нормализуем и копи, и сырьё ДО регексов.
    def _denorm_thousands(s):
        return re.sub(r"(?<=\d)[\x20\xa0   ](?=\d{3}(?:\D|$))", "", s)
    text = _denorm_thousands(text)
    interview_text = _denorm_thousands(interview_text)
    # МНОЖЕСТВО полных числовых токенов сырья (нормализованных) — не склейка всех цифр в одну
    # строку (подстрочное вхождение = решето: «15» проходит как часть «1500». Адверс-ревью по решению автора).
    src_tokens = set()
    for t in re.findall(r"\d[\d  ., ]*\d|\d", interview_text):
        nd = _digits(t)
        if nd:
            src_tokens.add(nd)
    claims = set()
    for rx in (MONEY, PERCENT, UNIT, BIGNUM):
        for m in rx.finditer(text):
            tok = m.group(0)
            d = _digits(tok)
            if not d or len(d) < 2:
                continue
            if YEAR.fullmatch(tok.strip()):  # годы (2026) — не claim
                continue
            claims.add((tok.strip(), d))
    out = []
    for tok, d in sorted(claims):
        if d not in src_tokens:
            out.append(f"число «{tok}» НЕ прослеживается к interview.md "
                       "(нет в исходном сырье — выдумка под именем эксперта?)")
    return out


def check_anglicisms(text, whitelist, where=""):
    """D. Кальки-англицизмы (кроме whitelist собственных терминов) → замена."""
    w = f"[{where}] " if where else ""
    wl = {x.lower() for x in (whitelist or [])}
    seen = {}
    for m in _ANGL_TOKEN.finditer(text):
        tok = m.group(0)
        low = tok.lower()
        if low in wl:
            continue
        if low in ANGLICISMS:
            seen[low] = ANGLICISMS[low]
    out = []
    for tok, repl in sorted(seen.items()):
        out.append(f"{w}калька «{tok}» — заменить на «{repl}» (RU-копи без англицизмов)")
    return out


def check_dangling_periods(text, where=""):
    """E. Висячая «.» на КОРОТКОЙ строке (заголовок/буллет/CTA). Абзацы не трогаем."""
    w = f"[{where}] " if where else ""
    out = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        # снять буллет-маркер для подсчёта слов
        body = _BULLET.sub("", line)
        if not body.endswith("."):
            continue
        # игнор многоточия и сокращений «и т.д.» / инициалов (две и более точек подряд / точка внутри)
        if body.endswith(("..", "т.д.", "т.п.", "и др.")):
            continue
        # точка как часть аббревиатуры в конце (одиночная буква + точка) — пропускаем «г.», «руб.» неоднозначно;
        # ограничиваемся: строка короткая И не выглядит как полноценное предложение-абзац
        words = body.split()
        if len(words) > DANGLING_MAX_WORDS or len(body) > DANGLING_MAX_CHARS:
            continue  # длинный абзац/предложение — НЕ трогаем (анти-FP)
        # внутри короткой строки уже есть точка-разделитель предложений → это мини-абзац, пропускаем
        inner = body[:-1]
        if "." in inner:
            continue
        out.append(f"{w}стр.{i}: висячая точка в короткой строке-копи «{line[:50]}» "
                   "(ToV автора: без точки в конце заголовка/буллета/CTA)")
    return out


def _extract_prices(text):
    """Все денежные числа из текста как множество нормализованных значений."""
    vals = set()
    for m in MONEY.finditer(text):
        d = _digits(m.group(0))
        if d and len(d) >= 2:
            vals.add(d)
    return vals


def check_offer_consistency(html):
    """G. Расхождение цены между блоками hero/pricing/CTA внутри одного index.html."""
    out = []
    blocks = {}
    # вырезать секции по ключевым якорям/классам/id
    for tag, pats in (
        ("hero", [r'(?is)<(section|header|div)[^>]*\b(?:id|class)="[^"]*\bhero\b[^"]*"[^>]*>(.*?)</\1>']),
        ("pricing", [r'(?is)<(section|div)[^>]*\b(?:id|class)="[^"]*\b(?:pricing|price|tariff|тариф|оффер|offer)\b[^"]*"[^>]*>(.*?)</\1>']),
        ("cta", [r'(?is)<(section|div|a|button)[^>]*\b(?:id|class)="[^"]*\b(?:cta|buy|оплат|купить|checkout)\b[^"]*"[^>]*>(.*?)</\1>']),
    ):
        chunk = ""
        for p in pats:
            for m in re.finditer(p, html):
                chunk += " " + m.group(m.lastindex)
        if chunk.strip():
            blocks[tag] = _extract_prices(html_visible_text(chunk))
    # сравнить попарно непустые наборы цен
    present = {k: v for k, v in blocks.items() if v}
    if len(present) >= 2:
        union = set().union(*present.values())
        # если есть блок, чьё множество цен не пересекается с другим → расхождение
        keys = list(present.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = present[keys[i]], present[keys[j]]
                if a and b and a.isdisjoint(b):
                    out.append(f"цена расходится между блоками «{keys[i]}» ({sorted(a)}) и "
                               f"«{keys[j]}» ({sorted(b)}) — единый источник offer-canon, "
                               "поправь устаревший блок")
    return out


def check_claims(text, source_text):
    """H. Claim-маркеры доверия требуют source-tag в blueprint/interview."""
    out = []
    src = (source_text or "")
    has_source_tags = bool(re.search(r"source\s*[:=]|source-tag|подтверждено-экспертом|внешний-пруф", src, re.I))
    for rx, label, requires_scope in CLAIM_MARKERS:
        m = rx.search(text)
        if not m:
            continue
        if requires_scope:
            # рыночный контекст в окне ±60 симв вокруг маркера — иначе это обычное слово
            lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
            if not CLAIM_SCOPE.search(text[lo:hi]):
                continue
        # если есть источник И в нём встречается этот маркер с тегом — считаем покрытым
        covered = bool(has_source_tags and rx.search(src))
        if not covered:
            out.append(f"claim-маркер «{label}» в копи без source-tag в blueprint.md/interview.md "
                       "(публичный факт о силе/первенстве/результате — подтвердить, не заявлять с чужих слов)")
    return out


def load_whitelist(blueprint_text):
    """Читает whitelist собственных терминов из glossary блока blueprint.md.
    Формат гибкий: ищем строки whitelist[...] / 'whitelist:' список / 'собственные термины'.
    Нет файла → пустой whitelist (строгий режим)."""
    if not blueprint_text:
        return []
    wl = []
    # whitelist[…] или whitelist: a, b, c
    for m in re.finditer(r"whitelist\s*[:\[]\s*([^\]\n]*)", blueprint_text, re.I):
        body = m.group(1)
        for tok in re.split(r"[,;|/]", body):
            tok = tok.strip().strip("\"'` ").strip()
            if tok and _ANGL_TOKEN.fullmatch(tok):
                wl.append(tok)
    return wl


def main():
    args = sys.argv[1:]

    def popval(flag):
        if flag in args:
            i = args.index(flag)
            v = args[i + 1] if i + 1 < len(args) else ""
            del args[i:i + 2]
            return v
        return None

    site_type = popval("--site-type") or ""
    iv = popval("--interview")
    bp = popval("--blueprint")
    html_path = popval("--html")

    def _read(path):
        if not path:
            return None
        try:
            return open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            return None

    interview_text = _read(iv)
    blueprint_text = _read(bp)
    html_text = _read(html_path)
    whitelist = load_whitelist(blueprint_text)
    # источник source-tag для claim-маркеров = blueprint + interview
    source_text = "\n".join(t for t in (blueprint_text, interview_text) if t)

    try:
        if args and args[0] == "--stdin":
            text = sys.stdin.read()
        elif args:
            text = open(args[0], encoding="utf-8", errors="ignore").read()
        elif html_text is not None:
            text = ""  # только --html режим (рендер-линт)
        else:
            sys.stderr.write("usage: copy-lint.py <copy.md> [--site-type T] "
                             "[--interview F] [--blueprint F] [--html index.html]\n")
            sys.exit(2)
    except Exception:
        sys.exit(0)

    findings = []
    # ── copy.md (A, B, C, D, E, H) ──
    if text:
        findings += [("EM-DASH", x) for x in check_emdash(text)]
        findings += [("РЕГИСТР", x) for x in check_register(text, site_type)]
        findings += [("ЧИСЛО", x) for x in check_numbers(text, interview_text)]
        findings += [("КАЛЬКА", x) for x in check_anglicisms(text, whitelist)]
        findings += [("ТОЧКА", x) for x in check_dangling_periods(text)]
        findings += [("CLAIM", x) for x in check_claims(text, source_text)]

    # ── рендер index.html (F: A/D/E ТАМ ЖЕ + G: согласованность оффера) ──
    if html_text is not None:
        visible = html_visible_text(html_text)
        copy_lines = html_copy_lines(html_text)  # только короткая копи (заголовки/CTA/буллеты)
        findings += [("РЕНДЕР·EM-DASH", x) for x in check_emdash(visible, where="рендер")]
        findings += [("РЕНДЕР·КАЛЬКА", x) for x in check_anglicisms(visible, whitelist, where="рендер")]
        findings += [("РЕНДЕР·ТОЧКА", x) for x in check_dangling_periods(copy_lines, where="рендер")]
        findings += [("ОФФЕР", x) for x in check_offer_consistency(html_text)]
        # claim-маркеры в рендере тоже подлежат трассировке
        findings += [("РЕНДЕР·CLAIM", x) for x in check_claims(visible, source_text)]

    if not findings:
        sys.exit(0)
    print("🛑 КОПИ-ЛИНТ: проверяемые дефекты копи (humaniser/регистр/факты/рендер):")
    for cls, msg in findings:
        print(f"   • [{cls}] {msg}")
    print("\nПочини: «—»→«–»/запятая · продающие слова убрать (контент-хаб) · "
          "число из interview.md · кальку на русское · висячую точку убрать · "
          "цену свести к offer-canon · claim подтвердить source-tag (не выдумывать).")
    sys.exit(3)


if __name__ == "__main__":
    main()