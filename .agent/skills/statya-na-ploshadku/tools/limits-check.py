#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limits-check.py - механический чекер адаптированной статьи под лимиты площадки.

Модель по памяти путает лимиты площадок и не умеет считать знаки -
этот скрипт считает точно. Проверяет:

  1. Длину заголовка (первый H1 или первая строка) против title_max.
  2. Длину тела в знаках (чистый текст без markdown-разметки и URL)
     против body_limit.
  3. Число ссылок (http/https) против links_max. Свой домен (--own-domain)
     исключается ТОЛЬКО на площадках с own_domain_exempt (сейчас tenchat:
     там ссылка на полную версию лимит не занимает). На vc/habr/dzen ссылки
     на свой сайт СЧИТАЮТСЯ в лимит - именно продвижение своих ресурсов
     ловят механики площадок («коммерческий аккаунт» VC и т.п.).
  4. Число хештегов (#слово в конце текста) против hashtags_max.
  5. Формат-тройку: длинные тире «—»/«–» (любое вхождение = FAIL) и
     точки в конце абзацев (кроме «?» «!» «:» «…»; код, YAML, таблицы
     и заголовки исключаются).

Использование:
  python3 limits-check.py <статья.md> --platform dzen|vc|tenchat|habr --own-domain <домен>
  python3 limits-check.py adapted.md --platform vc --own-domain example.com --json
  python3 limits-check.py adapted.md --platform tenchat --own-domain example.com

--own-domain брать из config.md скилла (ключ domain). Влияет только на площадки
с own_domain_exempt (tenchat): без него там ссылки на свой сайт посчитаются
внешними - чекер напечатает предупреждение, но не упадёт. Для остальных площадок
аргумент безвреден и ничего не меняет.

Коды выхода: 0 - все проверки OK/WARN; 1 - есть FAIL; 2 - ошибка аргументов.

Лимиты актуальны на 2026-07-30 (ресёрч площадок).
Лимиты дублируются в platforms/*.md - при расхождении прав YAML профиля.
"""
import argparse
import json
import os
import re
import sys

# Лимиты площадок. Источник - ресёрч по решению автора.
# None = лимита нет (или неизвестен). Дублируются в platforms/*.md -
# при расхождении прав YAML профиля площадки.
PLATFORMS = {
    "vc": {
        "title_max": None,        # официального лимита площадки НЕТ (живут заголовки до 190); FAIL только если заголовка нет вообще
        "title_warn_above": 140, # WARN если длиннее: оптимум 95-140 по замеру по решению автора
        "title_optimal_note": "жёсткого лимита vc нет, оптимум 95-140",
        "title_warn_below": 64,   # WARN если короче: потенциал заголовка VC не добит
        "body_limit": None,
        "links_max": 2,
        "hashtags_max": 0,        # хештеги не механика VC - норма скилла: не использовать (WARN)
    },
    "tenchat": {
        "title_max": 80,
        "title_warn_below": None,
        "body_limit": 7000,       # знаков ЧИСТОГО текста, без markdown-разметки
        "links_max": 1,
        "hashtags_max": 10,
        "own_domain_exempt": True,  # своя ссылка на полную версию лимит НЕ занимает (профиль tenchat.md)
    },
    "habr": {
        "title_max": None,
        "title_warn_below": None,
        "body_limit": None,
        "links_max": 1,
        "hashtags_max": None,
    },
    # 🔴 ДЗЕН ПЕРЕЕХАЛ в скилл dzen-engine (по решению автора). Канон значений и живой чекер:
    #    ~/.claude/skills/dzen-engine/tools/dzen-limits-check.py
    #    Профиль ниже оставлен для обратной совместимости старых прогонов.
    #    При расхождении прав dzen-engine, правки вносить ТАМ.
    "dzen": {
        "title_max": 140, # официальный лимит заголовка статьи (dzen.ru/help, по решению автора)
        "title_warn_above": 90, # WARN: эмпирика живых топов по решению автора - рабочий диапазон 45-90 (до 120 у холиварных)
        "title_optimal_note": "эмпирика топов 45-90 двухчастный, официальные 15-25 опровергнуты",
        "title_warn_below": 40, # WARN: ни одного живого топа короче 44 зн. (замер)
        "body_limit": 100000,      # статья до 100 000 знаков с пробелами
        "links_max": 2,            # норма скилла: 1 на полную версию + 1 на источник (запрета площадки нет)
        "hashtags_max": None,      # данных по хештегам Дзена нет - не проверяем
    },
}

# Свой домен ОБЯЗАН приходить через --own-domain (из config.md скилла).
# Дефолта нет: без флага все ссылки считаются внешними + печатается предупреждение.
DEFAULT_OWN_DOMAIN = None

OK, WARN, FAIL = "OK", "WARN", "FAIL"


# ---------------------------------------------------------------- разбор текста

def strip_yaml_frontmatter(text):
    """Убрать YAML-frontmatter в начале файла (--- ... ---)."""
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)


def strip_code_fences(text):
    """Убрать fenced-блоки ``` ``` целиком."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def extract_title(text):
    """Первый H1 (# ...) или первая непустая строка. Возвращает (title, line)."""
    for ln in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", ln)
        if m:
            return m.group(1).strip(), ln
    for ln in text.splitlines():
        if ln.strip():
            return ln.strip().lstrip("#").strip(), ln
    return "", None


def find_urls(text):
    """Все http/https URL в тексте (и в markdown-ссылках, и голые)."""
    return re.findall(r"https?://[^\s)\]>\"']+", text)


def url_domain(url):
    m = re.match(r"https?://([^/\s]+)", url)
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else ""


def trailing_hashtags(text):
    """Хештеги в конце текста: хвостовые строки, состоящие только из #слов."""
    tags = []
    lines = [ln for ln in text.splitlines()]
    i = len(lines) - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    while i >= 0:
        ln = lines[i].strip()
        if not ln:
            i -= 1
            continue
        tokens = ln.split()
        if tokens and all(re.match(r"^#[\wЀ-ӿ-]+$", t) for t in tokens):
            tags = tokens + tags
            i -= 1
        else:
            break
    return tags


def clean_body_text(text, title_line):
    """
    Чистый текст тела: без markdown-синтаксиса, без URL, без строки заголовка.
    Именно эти знаки считает площадка (TenChat: лимит 7000 на чистый текст).
    """
    body = strip_code_fences(strip_yaml_frontmatter(text))
    lines = []
    title_skipped = False
    for ln in body.splitlines():
        if not title_skipped and title_line is not None and ln == title_line:
            title_skipped = True
            continue
        lines.append(ln)
    body = "\n".join(lines)

    # картинки -> alt, ссылки -> анкор
    body = re.sub(r"!\[(.*?)\]\((.*?)\)", r"\1", body)
    body = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", body)
    # голые URL долой
    body = re.sub(r"https?://[^\s)\]>\"']+", "", body)
    # маркеры заголовков, цитат, списков
    body = re.sub(r"^#{1,6}\s+", "", body, flags=re.M)
    body = re.sub(r"^>\s?", "", body, flags=re.M)
    body = re.sub(r"^\s*[-*+]\s+", "", body, flags=re.M)
    body = re.sub(r"^\s*\d+\.\s+", "", body, flags=re.M)
    # разделители таблиц и пайпы
    body = re.sub(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", "", body, flags=re.M)
    body = body.replace("|", " ")
    # emphasis / inline-code
    body = re.sub(r"[*_`]", "", body)
    # горизонтальные линии
    body = re.sub(r"^\s*(---+|\*\*\*+)\s*$", "", body, flags=re.M)
    # схлопнуть пробелы построчно, убрать пустые строки из счёта
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in body.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def paragraphs_for_period_check(text):
    """
    Абзацы для проверки точки в конце: без кода, YAML, таблиц, заголовков.
    Возвращает список (последняя_строка_абзаца, номер_строки_в_файле).
    """
    raw = text.splitlines()
    # маска строк внутри code fence
    in_fence = False
    fence_mask = []
    for ln in raw:
        if re.match(r"^\s*```", ln):
            in_fence = True if not in_fence else False
            fence_mask.append(True)
        else:
            fence_mask.append(in_fence)
    # маска YAML-frontmatter
    yaml_end = 0
    if raw and raw[0].strip() == "---":
        for i in range(1, len(raw)):
            if raw[i].strip() == "---":
                yaml_end = i + 1
                break
    paras = []
    cur = []           # [(line_text, line_no)]
    for i, ln in enumerate(raw):
        skip = (i < yaml_end) or fence_mask[i]
        if ln.strip() and not skip:
            cur.append((ln, i + 1))
        else:
            if cur:
                paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)

    result = []
    for para in paras:
        last_text, last_no = para[-1]
        s = last_text.strip()
        # заголовки, таблицы, хеш-строки - не абзацы
        if re.match(r"^#{1,6}\s", s):
            continue
        if s.startswith("|") or re.match(r"^[\s:|-]+$", s):
            continue
        if all(t.startswith("#") for t in s.split()):
            continue
        result.append((s, last_no))
    return result


# ------------------------------------------------------------------- проверки

def run_checks(text, platform, own_domain):
    lim = PLATFORMS[platform]
    checks = []

    def add(name, status, detail, **extra):
        c = {"name": name, "status": status, "detail": detail}
        c.update(extra)
        checks.append(c)

    body_src = strip_yaml_frontmatter(text)

    # 1. Заголовок
    title, title_line = extract_title(body_src)
    tlen = len(title)
    tmax = lim["title_max"]
    twarn = lim.get("title_warn_below")
    twarn_above = lim.get("title_warn_above")
    if not title:
        add("title", FAIL, "заголовок не найден (нет H1 и непустых строк)", length=0)
    elif tmax is not None and tlen > tmax:
        add("title", FAIL,
            f"заголовок {tlen} зн. при лимите {tmax} - урезать на {tlen - tmax} зн.",
            length=tlen, limit=tmax)
    elif twarn_above and tlen > twarn_above:
        optimal = lim.get("title_optimal_note", f"рекомендация площадки - до {twarn_above} зн.")
        add("title", WARN,
            f"заголовок {tlen} зн. - длиннее warn-порога {twarn_above} ({optimal})",
            length=tlen, warn_above=twarn_above)
    elif twarn and tlen < twarn:
        add("title", WARN,
            f"заголовок {tlen} зн. - короче {twarn}, потенциал заголовка {platform} не добит",
            length=tlen, warn_below=twarn)
    elif tmax is None:
        add("title", OK, f"заголовок {tlen} зн. (жёсткого лимита для {platform} нет)", length=tlen)
    else:
        add("title", OK, f"заголовок {tlen} зн. (лимит {tmax})", length=tlen, limit=tmax)

    # 2. Тело
    body = clean_body_text(body_src, title_line)
    blen = len(body)
    bmax = lim["body_limit"]
    if bmax is None:
        add("body", OK, f"тело {blen} зн. чистого текста (лимита для {platform} нет)", length=blen)
    elif blen > bmax:
        add("body", FAIL,
            f"тело {blen} зн. при лимите {bmax} - урезать на {blen - bmax} зн.",
            length=blen, limit=bmax)
    else:
        add("body", OK, f"тело {blen} зн. чистого текста (лимит {bmax})", length=blen, limit=bmax)

    # 3. Внешние ссылки. Свой домен исключается ТОЛЬКО на площадках
    # с own_domain_exempt (tenchat) - на vc/habr/dzen свои ссылки СЧИТАЮТСЯ
    # в лимит: механики площадок ловят именно продвижение своих ресурсов
    urls = find_urls(strip_code_fences(body_src))
    if own_domain and lim.get("own_domain_exempt"):
        own = re.sub(r"^www\.", "", own_domain.lower())
        external = [u for u in urls
                    if not (url_domain(u) == own or url_domain(u).endswith("." + own))]
    else:
        external = list(urls)
    lmax = lim["links_max"]
    if lmax is None:
        add("links", OK,
            f"внешних ссылок {len(external)} (лимита для {platform} нет)", count=len(external))
    elif len(external) > lmax:
        add("links", FAIL,
            f"внешних ссылок {len(external)} при лимите {lmax} - убрать {len(external) - lmax}: "
            + ", ".join(url_domain(u) for u in external),
            count=len(external), limit=lmax)
    else:
        add("links", OK, f"внешних ссылок {len(external)} (лимит {lmax})",
            count=len(external), limit=lmax)

    # 4. Хештеги
    tags = trailing_hashtags(strip_code_fences(body_src))
    hmax = lim["hashtags_max"]
    if hmax is None:
        add("hashtags", OK, f"хештегов {len(tags)} (лимита для {platform} нет)", count=len(tags))
    elif hmax == 0 and tags:
        add("hashtags", WARN,
            f"хештегов {len(tags)} - хештеги не механика {platform} - убрать: " + " ".join(tags),
            count=len(tags), limit=0)
    elif len(tags) > hmax:
        add("hashtags", FAIL,
            f"хештегов {len(tags)} при лимите {hmax} - убрать {len(tags) - hmax}",
            count=len(tags), limit=hmax)
    else:
        add("hashtags", OK, f"хештегов {len(tags)} (лимит {hmax})", count=len(tags), limit=hmax)

    # 5а. Длинные тире
    dashes = [(i + 1, ln) for i, ln in enumerate(text.splitlines())
              if ("—" in ln or "–" in ln)]
    if dashes:
        where = ", ".join(f"строка {n}" for n, _ in dashes[:5])
        more = f" (+ ещё {len(dashes) - 5})" if len(dashes) > 5 else ""
        add("dashes", FAIL,
            f"длинные тире «—»/«–» найдены: {where}{more} - заменить на обычный дефис «-»",
            count=len(dashes))
    else:
        add("dashes", OK, "длинных тире «—»/«–» нет", count=0)

    # 5б. Точки в конце абзацев
    bad = []
    for last_line, line_no in paragraphs_for_period_check(text):
        tail = last_line.rstrip("*_`\"»)]'")
        if tail.endswith("...") or tail.endswith("…"):
            continue
        if tail.endswith("."):
            bad.append((line_no, last_line))
    if bad:
        where = ", ".join(f"строка {n}" for n, _ in bad[:5])
        more = f" (+ ещё {len(bad) - 5})" if len(bad) > 5 else ""
        add("paragraph_periods", FAIL,
            f"точка в конце абзаца: {where}{more} - убрать (допустимы «?» «!» «:» «…»)",
            count=len(bad))
    else:
        add("paragraph_periods", OK, "точек в конце абзацев нет", count=0)

    return checks


# ----------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(
        description="Механический чекер статьи под лимиты площадки.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Коды выхода: 0 - все OK; 1 - есть FAIL; 2 - ошибка аргументов.",
    )
    p.add_argument("article", help="путь к адаптированной статье (.md)")
    p.add_argument("--platform", required=True, choices=sorted(PLATFORMS),
                   help="площадка: " + "|".join(sorted(PLATFORMS)))
    p.add_argument("--own-domain", default=DEFAULT_OWN_DOMAIN,
                   help="свой домен из config.md (ключ domain); влияет только на площадки "
                        "с own_domain_exempt (tenchat) - там ссылки на него не считаются "
                        "внешними; для остальных площадок безвреден и ничего не меняет")
    p.add_argument("--json", action="store_true", help="вывод структурой JSON")
    args = p.parse_args()

    if not os.path.isfile(args.article):
        sys.stderr.write(f"нет файла: {args.article}\n")
        sys.exit(2)

    text = open(args.article, encoding="utf-8").read()
    checks = run_checks(text, args.platform, args.own_domain)
    fails = [c for c in checks if c["status"] == FAIL]
    warns = [c for c in checks if c["status"] == WARN]
    exit_code = 1 if fails else 0
    domain_warning = ("--own-domain не задан, ссылки на свой сайт посчитаются внешними"
                      if (not args.own_domain
                          and PLATFORMS[args.platform].get("own_domain_exempt"))
                      else None)

    if args.json:
        print(json.dumps({
            "file": args.article,
            "platform": args.platform,
            "own_domain_warning": domain_warning,
            "checks": checks,
            "fails": len(fails),
            "warns": len(warns),
            "exit": exit_code,
        }, ensure_ascii=False, indent=2))
        sys.exit(exit_code)

    print(f"Лимиты площадки: {args.platform} · файл: {os.path.basename(args.article)}")
    if domain_warning:
        print(f"  [WARN] {domain_warning}")
    for c in checks:
        print(f"  [{c['status']:4}] {c['detail']}")
    if fails:
        print(f"Итог: FAIL ({len(fails)} наруш.)" + (f", предупреждений: {len(warns)}" if warns else ""))
    else:
        print("Итог: OK" + (f", предупреждений: {len(warns)}" if warns else ""))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
