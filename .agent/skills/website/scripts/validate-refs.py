#!/usr/bin/env python3
"""
ВАЛИДАТОР КАЧЕСТВА РЕФЕРЕНСОВ — считает ТОЛЬКО квалифицированные эталоны.

Зачем (автор): скилл брал 3-4 случайных сайта, не из нашей ниши, не
понимал их, и врал про охват «10 референсов». Правила в фаз-файлах были, но
ПАССИВНЫЕ — машина не считала качество. Лечение: референс засчитывается, ТОЛЬКО
если он (а) живой URL, (б) скрин лежит на диске, (в) разобран — есть `why_works`
(почему работает, ≥60 симв), (г) обоснована релевантность нашей нише/типу
(`niche_relevant`, ≥20 симв), (д) верный тип/блок. Мусор-добивка без разбора НЕ
считается → подделать число нельзя. Не набрал target эталонов — обязан объявить
честный `shortfall` (сколько нашёл, где искал, почему мало), и ЭТО показывается
автору вместо вранья. «Не можешь найти — скажи, но не ври» (распоряжение автора).

Применение:
    python3 validate-refs.py <manifest.json> [--target N] [--block hero]
    # site-level:  refs/_manifest.json
    # per-screen:  refs/<screen>/_manifest.json   (--block <тип блока>)

Манифест (расширение существующей схемы, обратносовместимо):
{
  "site_type": "expert-personal-brand-paid-course",   // site-level
  "block": "hero",                                      // per-screen: тип блока
  "target": 10,
  "exemplars": [
    {"name":"Миллер","url":"example-etalon.ru/training","type":"...","block":"hero",
     "screenshot":"miller-hero.png",
     "why_works":"≥60 симв: что именно в блоке работает и за счёт чего",
     "niche_relevant":"≥20 симв: почему это эталон ИМЕННО для нашей ниши/типа"}
  ],
  "shortfall": {"found":4,"target":10,"reason":"…","searched":["…","…"]}  // если <target
}

Exit: 0 = PASS (≥target квалифицированных ИЛИ честный shortfall);
      3 = FAIL (мусор/добивка: есть записи, но недобор и нет честного shortfall);
      0 = манифеста нет (это ловит другой гейт — тут не дублируем).
Печатает человекочитаемый отчёт в stdout + машинный итог последней строкой.
"""
import json
import os
import sys

WHY_MIN = 60        # «почему работает» — реальный разбор, не «красиво»
REL_MIN = 20        # обоснование релевантности нише/типу
DEFAULT_TARGET = 10
SEARCHED_MIN = 4    # сколько мест поиска минимум для валидного shortfall
# Ключевые экраны — эталоны заведомо существуют у любого живого лендинга, поэтому
# «редкая ниша, не нашёл» тут = ложь. Shortfall на них допустим ТОЛЬКО при found≥6.
KEY_BLOCKS = {"hero", "offer", "pricing"}
KEY_SHORTFALL_MIN = 6


def _domain(s):
    """Грубо вытащить домен из строки места поиска (URL / «искал на site.com»).
    Возвращает нормализованный непустой токен-домен или '' если домена нет."""
    import re
    s = (str(s) or "").strip().lower()
    if not s:
        return ""
    # срезаем схему и путь
    s = re.sub(r'^[a-z]+://', '', s)
    # ищем доменоподобный токен (есть точка, латиница/цифры/дефис)
    m = re.search(r'([a-z0-9][a-z0-9.-]*\.[a-z]{2,})', s)
    if m:
        host = m.group(1).rstrip('/.')
        # отрезаем www.
        host = re.sub(r'^www\.', '', host)
        return host
    return ""


def qualify(ex, manifest_dir, want_block):
    """Вернуть (ok, reasons[]) — почему референс НЕ квалифицирован.

    want_block задан → ПЕР-ЭКРАННЫЙ режим (строгий: скрин на диске обязателен у
    КАЖДОГО образца + тип блока). want_block=None → режим доски (скрин не у каждого
    образца, т.к. наличие скринов в папке доски проверяет хук отдельно).
    Понимание/релевантность принимаются из новых полей why_works/niche_relevant
    ИЛИ из legacy-поля note (back-compat: доски до v1.6 несут разбор в note)."""
    bad = []
    per_screen = bool(want_block)
    if not (ex.get("url") or "").strip():
        bad.append("нет url")

    note = (ex.get("note") or "").strip()
    why = (ex.get("why_works") or "").strip() or note
    if len(why) < WHY_MIN:
        bad.append(f"разбор (why_works/note) < {WHY_MIN} симв (не понят)")
    rel = (ex.get("niche_relevant") or "").strip() or note
    if len(rel) < REL_MIN:
        bad.append(f"релевантность (niche_relevant/note) < {REL_MIN} симв (не доказана)")

    shot = (ex.get("screenshot") or "").strip()
    if shot:
        p = shot if os.path.isabs(shot) else os.path.join(manifest_dir, shot)
        if not os.path.exists(os.path.expanduser(p)):
            bad.append(f"скрин не найден на диске ({shot})")
    elif per_screen:
        bad.append("нет поля screenshot (per-screen: скрин обязателен у каждого образца)")
    # board-режим без поля screenshot — ок (скрины доски проверяет хук отдельно)

    if per_screen:
        b = (ex.get("block") or "").strip().lower()
        if b != want_block.lower():
            bad.append(f"block='{b or '—'}' ≠ '{want_block}' (не тот тип блока)")
    return (len(bad) == 0, bad)


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: validate-refs.py <manifest.json> [--target N] [--block hero]")
        sys.exit(0)
    manifest = os.path.expanduser(args[0])
    target = None
    want_block = None
    for i, a in enumerate(args):
        if a == "--target" and i + 1 < len(args):
            target = int(args[i + 1])
        if a == "--block" and i + 1 < len(args):
            want_block = args[i + 1]

    if not os.path.exists(manifest):
        print(f"(манифеста нет: {manifest} — проверка качества пропущена, ловит другой гейт)")
        sys.exit(0)

    try:
        m = json.load(open(manifest, encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: манифест не читается: {e}")
        print("RESULT FAIL 0/0")
        sys.exit(3)

    mdir = os.path.dirname(manifest) or "."
    if target is None:
        # та же логика дефолта, что у хука: явный target → board_target → min_exemplars → 10
        target = int(m.get("target") or m.get("board_target")
                     or m.get("min_exemplars") or DEFAULT_TARGET)
    if want_block is None:
        want_block = m.get("block")

    scope = m.get("block") or m.get("site_type") or "?"
    # только образцы (role==exemplar по умолчанию); методы-линзы (role:method) — не образцы
    exemplars = [e for e in (m.get("exemplars", []) or [])
                 if str(e.get("role", "exemplar")).lower() == "exemplar"]

    qualified, disq = [], []
    for ex in exemplars:
        ok, reasons = qualify(ex, mdir, want_block)
        (qualified if ok else disq).append((ex, reasons))

    nq = len(qualified)
    print(f"━━ Валидатор референсов · scope='{scope}' · цель={target} ━━")
    print(f"Квалифицировано: {nq}/{target}   ·   записей всего: {len(exemplars)}")
    if qualified:
        print("  ✅ зачтены:")
        for ex, _ in qualified:
            print(f"     • {ex.get('name','?')} — {ex.get('url','')}")
    if disq:
        print("  ⛔ НЕ зачтены (мусор/недоразбор):")
        for ex, reasons in disq:
            print(f"     • {ex.get('name','?')} — {'; '.join(reasons)}")

    if nq >= target:
        print(f"RESULT PASS {nq}/{target}")
        sys.exit(0)

    # недобор — проверяем честный shortfall
    sf = m.get("shortfall")
    if isinstance(sf, dict):
        reason = (sf.get("reason") or "").strip()
        searched = sf.get("searched") or []
        found = sf.get("found")
        problems = []
        if not reason:
            problems.append("нет reason")
        # searched: считаем УНИКАЛЬНЫЕ непустые домены, не сырые строки (4 копии одной
        # строки / 4 пустышки = не доказан реальный поиск, прежняя лазейка).
        if not isinstance(searched, list):
            problems.append(f"searched < {SEARCHED_MIN} мест (не доказан реальный поиск)")
        else:
            uniq_domains = {dom for dom in (_domain(s) for s in searched) if dom}
            if len(uniq_domains) < SEARCHED_MIN:
                problems.append(
                    f"searched < {SEARCHED_MIN} УНИКАЛЬНЫХ доменов "
                    f"(нашёл {len(uniq_domains)}: {', '.join(sorted(uniq_domains)) or '—'}) "
                    "— дубли/пустышки не считаются, не доказан реальный поиск")
        if found is not None and found != nq:
            problems.append(f"found={found} ≠ реально квалифицировано {nq} (несходится)")
        # Ключевой экран (hero/offer/pricing): эталоны заведомо есть → shortfall с
        # found<KEY_SHORTFALL_MIN = ложь, запрещаем независимо от честности оформления.
        scope_block = (want_block or m.get("block") or "").strip().lower()
        if scope_block in KEY_BLOCKS and nq < KEY_SHORTFALL_MIN:
            problems.append(
                f"экран '{scope_block}' — КЛЮЧЕВОЙ: эталоны hero/offer/pricing есть у "
                f"любого лендинга, shortfall при found={nq}<{KEY_SHORTFALL_MIN} не принимается "
                f"(добери минимум {KEY_SHORTFALL_MIN})")
        if not problems:
            print(f"⚠️  SHORTFALL принят: нашёл {nq}/{target} эталонов, объявлено честно.")
            print(f"     причина: {reason}")
            print(f"     искал в: {', '.join(map(str, searched))}")
            print(f"RESULT PASS-SHORTFALL {nq}/{target}")
            sys.exit(0)
        print("  ⛔ shortfall НЕвалиден: " + "; ".join(problems))

    print(
        f"\n🛑 FAIL: квалифицировано {nq}/{target}, честного shortfall нет.\n"
        "   Это и есть «3-4 случайных сайта + враньё про охват». Варианты:\n"
        "   (1) добрать до цели РЕАЛЬНЫЕ эталоны нашей ниши/типа (скрин на диск + "
        "why_works ≥60 + niche_relevant), либо\n"
        "   (2) объявить честный shortfall {found,reason,searched[≥4]} — где искал и "
        "почему эталонов меньше. Врать (падить мусором) нельзя."
    )
    print(f"RESULT FAIL {nq}/{target}")
    sys.exit(3)


if __name__ == "__main__":
    main()