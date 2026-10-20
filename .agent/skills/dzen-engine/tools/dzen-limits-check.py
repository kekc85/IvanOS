#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Механический чекер дзен-статьи: лимиты площадки + эмпирика топов + формат-тройка.

Владелец правил - dzen-engine/knowledge/platform-rules.md. При расхождении значений
прав YAML-профиль в том файле, а не этот скрипт.

Использование:
  python3 dzen-limits-check.py work/<slug>/adapted.md --own-domain example.com
  python3 dzen-limits-check.py work/<slug>/adapted.md --own-domain example.com --json

Коды возврата: 0 = всё OK (WARN допустим), 1 = есть FAIL, 2 = файл не прочитан.
"""

import argparse
import json
import os
import re
import sys

# --- лимиты и эмпирика (источник: knowledge/platform-rules.md, проверено в даты запуска.2026) ---
DZEN = {
    "title_max": 140,            # официальный лимит заголовка статьи
    "title_opt_min": 45,         # эмпирика живых топов: 46-117 зн., медиана 70
    "title_opt_max": 90,         # выше 90 - только холиварные, до 120
    "title_hard_low": 40,        # ни одного живого топа короче 44
    "body_limit": 100000,        # статья до 100 000 знаков с пробелами
    "links_max": 2,              # норма движка: 1 на полную версию + макс 1 на источник
    "gallery_max": 30,
    "attachments_max": 100,
    "longread_min": 9000,        # стандарт лонгрида-топа 9-13К знаков
    "longread_max": 13000,
    "detonator_max": 2500,       # новость-детонатор ~1 минута
}

OK, WARN, FAIL = "OK", "WARN", "FAIL"

CLICKBAIT_MARKERS = ["!!!", "???", "!?", "ШОК", "СЕНСАЦИЯ", "срочно!!!"]


# ------------------------------------------------------------------ разбор текста

def strip_yaml_frontmatter(text):
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)


def strip_code_fences(text):
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def extract_title(text):
    """Первый H1 или первая непустая строка. Возвращает (title, line)."""
    for ln in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", ln)
        if m:
            return m.group(1).strip(), ln
    for ln in text.splitlines():
        if ln.strip():
            return ln.strip().lstrip("#").strip(), ln
    return "", None


def find_urls(text):
    return re.findall(r"https?://[^\s)\]>\"']+", text)


def url_domain(url):
    m = re.match(r"https?://([^/\s]+)", url)
    return re.sub(r"^www\.", "", m.group(1).lower()) if m else ""


def clean_body_text(text, title_line):
    """Чистый текст тела без markdown-синтаксиса, URL и строки заголовка."""
    body = strip_code_fences(strip_yaml_frontmatter(text))
    lines, title_skipped = [], False
    for ln in body.splitlines():
        if not title_skipped and title_line is not None and ln == title_line:
            title_skipped = True
            continue
        lines.append(ln)
    body = "\n".join(lines)

    body = re.sub(r"!\[(.*?)\]\((.*?)\)", r"\1", body)
    body = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", body)
    body = re.sub(r"https?://[^\s)\]>\"']+", "", body)
    body = re.sub(r"^#{1,6}\s+", "", body, flags=re.M)
    body = re.sub(r"^>\s?", "", body, flags=re.M)
    body = re.sub(r"^\s*[-*+]\s+", "", body, flags=re.M)
    body = re.sub(r"^\s*\d+\.\s+", "", body, flags=re.M)
    body = re.sub(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", "", body, flags=re.M)
    body = body.replace("|", " ")
    body = re.sub(r"[*_`]", "", body)
    body = re.sub(r"^\s*(---+|\*\*\*+)\s*$", "", body, flags=re.M)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in body.splitlines()]
    return "\n".join([ln for ln in lines if ln])


def paragraphs(text):
    """Абзацы вне кода и YAML: список списков (строка, номер)."""
    raw = text.splitlines()
    in_fence, fence_mask = False, []
    for ln in raw:
        if re.match(r"^\s*```", ln):
            in_fence = not in_fence
            fence_mask.append(True)
        else:
            fence_mask.append(in_fence)
    yaml_end = 0
    if raw and raw[0].strip() == "---":
        for i in range(1, len(raw)):
            if raw[i].strip() == "---":
                yaml_end = i + 1
                break
    paras, cur = [], []
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
    return paras


def prose_paragraphs(paras):
    """Только прозаические абзацы: без заголовков, таблиц, списков, хеш-строк."""
    out = []
    for para in paras:
        s = para[-1][0].strip()
        if re.match(r"^#{1,6}\s", s):
            continue
        if s.startswith("|") or re.match(r"^[\s:|-]+$", s):
            continue
        if all(t.startswith("#") for t in s.split()):
            continue
        out.append(para)
    return out


def is_two_part_title(title):
    """
    Двухчастность заголовка Дзена: [факт/установка] + [эмоция/вопрос].
    Признак - разделитель внутри заголовка (не в самом конце): . ? ! : ; - ...
    """
    core = title.strip().rstrip(".!?…")
    if not core:
        return False
    inner = core[:-1] if core else core
    return bool(re.search(r"[.!?:;…]|\s[-–—]\s", inner))


# ------------------------------------------------------------------------ проверки

def run_checks(text, own_domain):
    checks = []

    def add(name, status, detail, **extra):
        c = {"name": name, "status": status, "detail": detail}
        c.update(extra)
        checks.append(c)

    body_src = strip_yaml_frontmatter(text)
    title, title_line = extract_title(body_src)
    tlen = len(title)

    # 1. Длина заголовка
    if tlen > DZEN["title_max"]:
        add("title_length", FAIL,
            f"заголовок {tlen} зн. - лимит Дзена {DZEN['title_max']}", length=tlen)
    elif tlen > DZEN["title_opt_max"]:
        add("title_length", WARN,
            f"заголовок {tlen} зн. - выше рабочих {DZEN['title_opt_min']}-{DZEN['title_opt_max']}; "
            f"допустимо только для холиварного захода", length=tlen)
    elif tlen < DZEN["title_hard_low"]:
        add("title_length", WARN,
            f"заголовок {tlen} зн. - короче 40; ни одного живого топа короче 44 зн. "
            f"(официальные 15-25 опровергнуты замером по решению автора)", length=tlen)
    elif tlen < DZEN["title_opt_min"]:
        add("title_length", WARN,
            f"заголовок {tlen} зн. - чуть ниже рабочего диапазона {DZEN['title_opt_min']}-{DZEN['title_opt_max']}",
            length=tlen)
    else:
        add("title_length", OK, f"заголовок {tlen} зн. - в рабочем диапазоне 45-90", length=tlen)

    # 2. Двухчастность заголовка
    if title:
        if is_two_part_title(title):
            add("title_structure", OK, "заголовок двухчастный [факт] + [эмоция/вопрос]")
        else:
            add("title_structure", WARN,
                "заголовок односоставный - конструкция топов Дзена двухчастная: "
                "[факт или установка] + [эмоция или вопрос]")

    # 3. Ссылки и кликбейт в заголовке
    if title and find_urls(title):
        add("title_links", FAIL, "гиперссылки в заголовке Дзена запрещены")
    if title:
        caps_words = [w for w in title.split() if len(w) > 2 and w.isupper()]
        marker_hit = [m for m in CLICKBAIT_MARKERS if m.lower() in title.lower()]
        if caps_words or marker_hit:
            add("title_clickbait", WARN,
                "признаки кликбейт-карточки в заголовке ("
                + ", ".join(caps_words + marker_hit)
                + ") - санкция Дзена: показ только подписчикам")

    # 4. Объём тела
    body = clean_body_text(text, title_line)
    blen = len(body)
    if blen > DZEN["body_limit"]:
        add("body_length", FAIL, f"тело {blen} зн. - лимит статьи {DZEN['body_limit']}", length=blen)
    elif blen <= DZEN["detonator_max"]:
        add("body_length", OK,
            f"тело {blen} зн. - формат новости-детонатора (до {DZEN['detonator_max']})", length=blen)
    elif DZEN["longread_min"] <= blen <= DZEN["longread_max"]:
        add("body_length", OK,
            f"тело {blen} зн. - стандарт лонгрида-топа ({DZEN['longread_min']}-{DZEN['longread_max']})",
            length=blen)
    elif blen > DZEN["longread_max"]:
        add("body_length", WARN,
            f"тело {blen} зн. - длиннее эталонного лонгрида ({DZEN['longread_max']}), "
            f"риск падения дочитываний", length=blen)
    else:
        add("body_length", WARN,
            f"тело {blen} зн. - «середина» между детонатором (до {DZEN['detonator_max']}) "
            f"и лонгридом (от {DZEN['longread_min']}); по эмпирике топов середина проседает",
            length=blen)

    # 5. Структура: подзаголовки и оглавление
    subheads = [ln for ln in body_src.splitlines() if re.match(r"^#{2,4}\s+", ln)]
    proses = prose_paragraphs(paragraphs(body_src))
    if blen > DZEN["detonator_max"]:
        if not subheads:
            add("structure_subheads", FAIL,
                "подзаголовков нет - лонгрид без разбивки не дочитывают")
        else:
            ratio = len(proses) / max(len(subheads), 1)
            if ratio > 4:
                add("structure_subheads", WARN,
                    f"{len(subheads)} подзаголовков на {len(proses)} абзацев "
                    f"(~{ratio:.1f} абзаца на подзаголовок) - норма Дзена каждые 2-3",
                    subheads=len(subheads), paragraphs=len(proses))
            else:
                add("structure_subheads", OK,
                    f"{len(subheads)} подзаголовков на {len(proses)} абзацев",
                    subheads=len(subheads), paragraphs=len(proses))
        if blen >= DZEN["longread_min"]:
            has_toc = bool(re.search(r"^\s*#{2,4}\s*(оглавление|содержание)", body_src,
                                     re.I | re.M))
            add("structure_toc", OK if has_toc else WARN,
                "оглавление есть" if has_toc
                else "оглавления нет - у лонгридов-топов Дзена оно стандарт")

    # 6. Длинные абзацы (темп чтения)
    long_paras = []
    for para in proses:
        ptext = " ".join(t for t, _ in para)
        if len(ptext) > 600:
            long_paras.append((para[0][1], len(ptext)))
    if long_paras:
        add("paragraph_rhythm", WARN,
            f"длинных абзацев (>600 зн.): {len(long_paras)}, строки "
            + ", ".join(str(n) for n, _ in long_paras[:8])
            + " - аудитория Дзена массовая, абзац держим в 2-4 строки",
            count=len(long_paras))
    else:
        add("paragraph_rhythm", OK, "длинных абзацев нет")

    # 7. Ссылки в теле
    urls = find_urls(strip_code_fences(body_src))
    own, external = [], []
    for u in urls:
        dom = url_domain(u)
        if own_domain and dom.endswith(own_domain.lower()):
            own.append(u)
        else:
            external.append(u)
    if not own_domain:
        add("own_domain", WARN,
            "--own-domain не передан: все ссылки считаются внешними, "
            "домен берётся из config.md")
    total = len(own) + len(external)
    if total > DZEN["links_max"]:
        add("links", WARN,
            f"ссылок {total} (своих {len(own)}, внешних {len(external)}) - норма движка "
            f"{DZEN['links_max']}: 1 на полную версию + максимум 1 на источник",
            count=total)
    else:
        add("links", OK, f"ссылок {total} (своих {len(own)}, внешних {len(external)})", count=total)
    if own_domain and not own:
        add("own_link", WARN,
            f"ссылки на полную версию у себя ({own_domain}) нет - дзен-статья должна вести на канон")

    # 8. Формат-тройка (закон донора №2)
    dashes = [(i + 1, ln) for i, ln in enumerate(text.splitlines()) if "—" in ln or "–" in ln]
    if dashes:
        add("format_dash", FAIL,
            f"длинные тире в {len(dashes)} строках: "
            + ", ".join(str(n) for n, _ in dashes[:10]) + " - только дефис",
            count=len(dashes))
    else:
        add("format_dash", OK, "длинных тире нет")

    bad_period = []
    for para in proses:
        last_text, last_no = para[-1]
        s = last_text.strip()
        if s.endswith(".") and not s.endswith("..."):
            bad_period.append(last_no)
    if bad_period:
        add("format_period", FAIL,
            f"точка в конце абзаца в {len(bad_period)} местах: строки "
            + ", ".join(str(n) for n in bad_period[:10]),
            count=len(bad_period))
    else:
        add("format_period", OK, "точек в конце абзацев нет")

    # 9. Вложения (галерея)
    images = re.findall(r"!\[.*?\]\(.*?\)", body_src)
    if len(images) > DZEN["gallery_max"]:
        add("images", WARN,
            f"картинок в тексте {len(images)} - галерея Дзена до {DZEN['gallery_max']}",
            count=len(images))
    else:
        add("images", OK, f"картинок в тексте {len(images)}", count=len(images))

    return checks


# ---------------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(
        description="Чекер лимитов и эмпирики Дзена для dzen-engine",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("article", help="путь к adapted.md")
    p.add_argument("--own-domain", default=None,
                   help="свой домен из config.md (без него все ссылки считаются внешними)")
    p.add_argument("--json", action="store_true", help="вывод в JSON")
    args = p.parse_args()

    try:
        with open(args.article, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"НЕ ПРОЧИТАН: {e}", file=sys.stderr)
        return 2

    checks = run_checks(text, args.own_domain)
    fails = [c for c in checks if c["status"] == FAIL]
    warns = [c for c in checks if c["status"] == WARN]

    if args.json:
        print(json.dumps({
            "platform": "dzen",
            "file": args.article,
            "verdict": FAIL if fails else (WARN if warns else OK),
            "checks": checks,
        }, ensure_ascii=False, indent=2))
        return 1 if fails else 0

    print(f"Лимиты площадки: dzen · файл: {os.path.basename(args.article)}")
    print("-" * 72)
    for c in checks:
        mark = {OK: "OK  ", WARN: "WARN", FAIL: "FAIL"}[c["status"]]
        print(f"[{mark}] {c['name']}: {c['detail']}")
    print("-" * 72)
    if fails:
        print(f"ВЕРДИКТ: FAIL - {len(fails)} блокирующих, {len(warns)} предупреждений")
    elif warns:
        print(f"ВЕРДИКТ: OK с {len(warns)} предупреждениями - разобрать каждое, не пропускать молча")
    else:
        print("ВЕРДИКТ: OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
