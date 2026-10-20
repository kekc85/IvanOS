#!/usr/bin/env python3
"""scarcity-counter-audit.py — машинный аудит фейк-счётчика дефицита в рендере сайта.

. Прецедент workshop.html: «занято 160 из 1000»
показывалось ДО открытия реги, потому что массив дата→осталось был заякорен в прошлое.

Контракт (вызывается из website-review-gate.sh › check_scarcity):
  argv[1] = путь к index.html (рендер)
  опц: --open-date YYYY-MM-DD[THH:MM]   --event-start YYYY-MM-DD[THH:MM]
  exit 0 = счётчика нет / счётчик корректен / НЕДОСТАТОЧНО данных для уверенного вердикта
           (сознательно НЕ ложно-блокируем — автор ненавидит ложные блоки)
  exit 3 = ДОКАЗАННЫЙ фейк-дефицит (BLOCK), причина в stdout
  exit 1 НЕ используется.

Источник даты открытия: аргументы → scarcity.open_at / open_at: в blueprint.md (или offer-canon.md)
рядом с index.html. Нет источника → НЕ блок (advisory), enforcement включается когда Blueprint
запер open_at — так новый поток ученика защищён, а легаси-сайты без blueprint.md не ловятся ложно.
"""
import sys
import os
import re
from datetime import datetime, timedelta

MARKERS = re.compile(r"остал[ои]сь|занят|мест\b|seats?|spots?|remaining|sold\s*out", re.I)
DYNAMIC = re.compile(r"setInterval|setTimeout|new Date|Date\.now|textContent|innerText|requestAnimationFrame", re.I)


def parse_dt(s):
    if not s:
        return None
    s = str(s).strip().strip("\"'")
    s = re.sub(r"(Z|[+-]\d\d:?\d\d)$", "", s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
                "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def find_open_dt(base, arg):
    d = parse_dt(arg)
    if d:
        return d, "аргумент --open-date"
    for name in ("blueprint.md", "offer-canon.md", "Design.md"):
        p = os.path.join(base, name)
        if not os.path.isfile(p):
            continue
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = re.search(r"open[_-]?at[\"'\s:=]+([0-9][0-9T :/.\-]{7,18})", t, re.I)
        if m:
            dd = parse_dt(m.group(1))
            if dd:
                return dd, name
    return None, None


def find_event_dt(base, arg):
    d = parse_dt(arg)
    if d:
        return d
    for name in ("blueprint.md", "offer-canon.md"):
        p = os.path.join(base, name)
        if not os.path.isfile(p):
            continue
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = re.search(r"(?:event[_-]?start|starts?[_-]?at|start[_-]?at)[\"'\s:=]+([0-9][0-9T :/\-]{7,18})", t, re.I)
        if m:
            dd = parse_dt(m.group(1))
            if dd:
                return dd
    return None


def main():
    args = sys.argv[1:]
    html_path = None
    open_arg = event_arg = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--open-date" and i + 1 < len(args):
            open_arg = args[i + 1]; i += 2; continue
        if a == "--event-start" and i + 1 < len(args):
            event_arg = args[i + 1]; i += 2; continue
        if html_path is None and not a.startswith("--"):
            html_path = a
        i += 1

    if not html_path or not os.path.isfile(html_path):
        sys.exit(0)
    try:
        html = open(html_path, encoding="utf-8", errors="ignore").read()
    except Exception:
        sys.exit(0)

    # 1. Есть ли вообще динамический счётчик дефицита? Нет → неприменимо.
    if not (MARKERS.search(html) and DYNAMIC.search(html)):
        sys.exit(0)

    now = datetime.now()
    base = os.path.dirname(os.path.abspath(html_path))
    open_dt, open_src = find_open_dt(base, open_arg)
    event_dt = find_event_dt(base, event_arg)

    # 2. Зашитые в JS даты-якоря СЧЁТЧИКА. Исключаем посторонние ЦИТИРОВАННЫЕ даты
    #    (JSON-LD/schema.org datePublished/startDate, даты отзывов) — это НЕ якорь счётчика,
    # иначе честный счётчик с микроразметкой ложно блокируется (ре-ревью по решению автора).
    scan = re.sub(r'(?is)<script[^>]*application/ld\+json[^>]*>.*?</script>', " ", html)
    SCHEMA_KEYS = re.compile(
        r"(datePublished|dateModified|dateCreated|startDate|endDate|datePosted|"
        r"uploadDate|reviewDate|validFrom|validThrough)", re.I)
    dates = []
    for m in re.finditer(r"new Date\(\s*[\"']([0-9][0-9T :/\-]{7,18})[\"']", scan):
        d = parse_dt(m.group(1))
        if d:
            dates.append(d)
    DATE_LIT = re.compile(
        r"[\"'](\d{4}[-/.]\d{2}[-/.]\d{2}(?:[T ]\d{2}:\d{2})?|\d{2}[.\-/]\d{2}[.\-/]\d{4})[\"']")
    for m in DATE_LIT.finditer(scan):  # dash/slash/dotted + DD.MM.YYYY (обход круга 3)
        if SCHEMA_KEYS.search(scan[max(0, m.start() - 50):m.start()]):
            continue
        d = parse_dt(m.group(1))
        if d:
            dates.append(d)

    problems = []

    # Дата открытия неизвестна → advisory (НЕ блок), чтобы не ловить легаси/чужие сайты ложно.
    if not open_dt:
        print("ℹ️  scarcity: дата ОТКРЫТИЯ реги не найдена (нет --open-date и open_at в blueprint.md рядом). "
              "Аудит привязки счётчика пропущен — задай scarcity.open_at в Blueprint, чтобы включить машинную "
              "защиту от фейк-дефицита до открытия.")
        sys.exit(0)

    # (а) Якорь счётчика РАНЬШЕ даты открытия → к открытию места уже «отмотаны» (занято>0 при нуле реги).
    past_before_open = [d for d in dates if d < open_dt - timedelta(hours=1)]
    if past_before_open:
        earliest = min(past_before_open)
        problems.append(
            f"(а) якорь счётчика ({earliest:%Y-%m-%d %H:%M}) РАНЬШЕ даты открытия реги "
            f"({open_dt:%Y-%m-%d %H:%M}, источник: {open_src}) → к открытию счётчик уже отмотал места = "
            "занято>0 при нуле реальных регистраций.")

    # (б) Реги ещё НЕ открыта (now < open) — а в рендере уже занятость > 0.
    if now < open_dt:
        occ = re.search(r"занят[оы]?\D{0,12}(\d{1,4})", html, re.I)
        pair = re.search(r"(\d{1,4})\s*(?:из|/|of)\s*(\d{1,4})", html)
        if occ and int(occ.group(1)) > 0:
            problems.append(
                f"(б) реги откроется {open_dt:%Y-%m-%d %H:%M}, а в рендере уже «занято {occ.group(1)}» — "
                "фейк-занятость до старта продаж = ложь + палево фейка.")
        elif pair and int(pair.group(1)) < int(pair.group(2)):
            problems.append(
                f"(б) реги ещё не открыта, а счётчик показывает «{pair.group(1)} из {pair.group(2)}» "
                "(часть мест уже «занята») до старта продаж.")

    if problems:
        out = ["Аудит счётчика дефицита — ДОКАЗАННЫЕ НАРУШЕНИЯ:"]
        out += ["  - " + p for p in problems]
        out.append("Правило: старт счётчика = дата ОТКРЫТИЯ реги (M мест, занято = 0), плавный спуск "
                   "к ~0 к старту мероприятия.")
        # Эталонная плавная кривая как улика «как должно быть»
        if event_dt and event_dt > open_dt:
            cap_m = re.search(r"(?:из|/|of)\s*(\d{2,4})", html) or re.search(r"\b(\d{3,4})\s*мест", html, re.I)
            M = int(cap_m.group(1)) if cap_m else 1000
            span = (event_dt - open_dt).total_seconds()
            out.append("Эталон (плавно M→~0):")
            for frac, label in ((0.0, "открытие"), (0.25, "+¼"), (0.5, "середина"), (0.75, "+¾"), (1.0, "старт события")):
                t = open_dt + timedelta(seconds=span * frac)
                left = round(M * (1 - frac))
                out.append(f"    {t:%Y-%m-%d %H:%M}  осталось ≈ {left}/{M}")
        print("\n".join(out))
        sys.exit(3)

    sys.exit(0)


if __name__ == "__main__":
    main()