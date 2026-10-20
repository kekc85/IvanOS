#!/usr/bin/env python3
"""
journey-map-audit.py — МАШИННЫЙ ПОЛ Фазы 10 (макро-ревью сайта как системы).

Детерминированно валидирует Customer Journey Map (.site-review.json `journey[]`) против
карты экранов (.website-state.json `screens[]`). Это «Слой 1» межэкранной проверки: меряемое
в журнале не должно проскочить на вкус. Покрывает машинную часть осей B (лестница
осознанности) и C (информационный аромат) рубрики `references/macro-rubric.md`.

Что проверяет (любое нарушение → exit 3):
  1. ПОКРЫТИЕ: множество экранов в journey == множеству screens[] (нет пропущенных/фантомных).
  2. ПОРЯДОК: journey идёт в том же порядке, что screens[] (рассуждение об аромате/осознанности
     опирается на реальный порядок скролла).
  3. ПОЛЯ: каждая строка имеет screen, awareness(1-5 int), question_raised(str),
     answered_by(str), cta(str ∈ primary/secondary/none).
  4. ОСОЗНАННОСТЬ НЕ УБЫВАЕТ (ось B): awareness по порядку экранов не идёт назад; финал = max.
  5. НЕТ ВИСЯЧИХ ПЕТЕЛЬ (ось C): каждый непустой question_raised → answered_by это имя
     БОЛЕЕ ПОЗДНЕГО экрана (ответ выше по странице / в никуда = висячая петля).
  6. ARC-СКЕЛЕТ: есть хотя бы один cta=="primary" (воронка ведёт к действию).

Использование:
    python3 journey-map-audit.py <DIR>     # DIR = папка проекта (где оба .json)
Exit: 0 = журнал сходится; 3 = есть нарушение (печатает какие); 2 = не смог запустить
(нет/битый файл — гейт проверяет существование отдельно, поэтому 2 ≠ блок).
Safe-by-design: 2 на отсутствии файлов, чтобы не блокировать ложно вне контекста сайта.
"""
import json
import os
import sys

AW_MIN, AW_MAX = 1, 5
VALID_CTA = {"primary", "secondary", "none"}


def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: journey-map-audit.py <project-dir>\n")
        sys.exit(2)
    d = os.path.expanduser(sys.argv[1])
    if d.endswith(".website-state.json") or d.endswith(".site-review.json"):
        d = os.path.dirname(d)

    state = load(os.path.join(d, ".website-state.json"))
    review = load(os.path.join(d, ".site-review.json"))
    if not isinstance(state, dict) or not isinstance(review, dict):
        # гейт проверяет существование сам; здесь 2 = «не наш случай», не блок
        sys.exit(2)

    screens = [str(s.get("name", "")).strip() for s in state.get("screens", []) or []
               if isinstance(s, dict) and str(s.get("name", "")).strip()]
    journey = review.get("journey", []) or []

    # C1 (ревью): привязка журнала к РЕНДЕРУ. Без index.html журнал = JSON, который агент
    # сам сочинил, и «машинный пол» проверяет выдумку саму на себя. Читаем рендер и сверяем.
    html_lower = ""
    idx = os.path.join(d, "index.html")
    if os.path.exists(idx):
        try:
            html_lower = open(idx, encoding="utf-8", errors="ignore").read().lower()
        except Exception:
            html_lower = ""

    errs = []
    warns = []

    if not screens:
        # карта экранов пуста — нечего сверять (стадия A/B), не блокируем здесь
        sys.exit(2)
    if not isinstance(journey, list) or not journey:
        print("🛑 ЖУРНАЛ: .site-review.json без journey[] — карта пути клиента не построена.\n"
              "Фаза 10 Шаг 10.1: одна строка на КАЖДЫЙ экран в порядке скролла.")
        sys.exit(3)

    j_names = [str(r.get("screen", "")).strip() for r in journey if isinstance(r, dict)]

    # 1) ПОКРЫТИЕ
    set_s, set_j = set(screens), set(n for n in j_names if n)
    miss = set_s - set_j
    phantom = set_j - set_s
    if miss:
        errs.append(f"журнал НЕ покрывает экраны: {sorted(miss)} (каждый экран = строка журнала)")
    if phantom:
        errs.append(f"в журнале фантомные экраны (нет в screens[]): {sorted(phantom)}")

    # 2) ПОРЯДОК (только если покрытие совпадает по составу)
    if not miss and not phantom and j_names != screens:
        errs.append(f"порядок журнала ≠ порядку экранов:\n   screens: {screens}\n   journey: {j_names}")

    # 3) ПОЛЯ + сбор osознанности по порядку
    aw_seq = []
    order_index = {n: i for i, n in enumerate(j_names)}
    for i, r in enumerate(journey):
        if not isinstance(r, dict):
            errs.append(f"строка {i} журнала не объект")
            continue
        name = str(r.get("screen", "")).strip() or f"#{i}"
        aw = r.get("awareness")
        if not isinstance(aw, int) or not (AW_MIN <= aw <= AW_MAX):
            errs.append(f"«{name}»: awareness={aw!r} не целое 1-5 (стадия Schwartz)")
        else:
            aw_seq.append((name, aw))
        if "question_raised" not in r:
            errs.append(f"«{name}»: нет поля question_raised")
        if "answered_by" not in r:
            errs.append(f"«{name}»: нет поля answered_by")
        cta = str(r.get("cta", "")).strip().lower()
        if cta not in VALID_CTA:
            errs.append(f"«{name}»: cta={r.get('cta')!r} не из {sorted(VALID_CTA)}")

    # 4) ОСОЗНАННОСТЬ НЕ УБЫВАЕТ (ось B)
    for k in range(1, len(aw_seq)):
        (pn, pa), (cn, ca) = aw_seq[k - 1], aw_seq[k]
        if ca < pa:
            errs.append(f"осознанность УБЫЛА: «{pn}»(stage {pa}) → «{cn}»(stage {ca}) — "
                        f"прыжок назад по лестнице Schwartz (ось B)")
    if aw_seq:
        last_name, last_aw = aw_seq[-1]
        max_aw = max(a for _, a in aw_seq)
        if last_aw < max_aw:
            errs.append(f"финальный экран «{last_name}»(stage {last_aw}) НЕ на максимуме "
                        f"осознанности ({max_aw}) — воронка не доводит до покупки (ось B)")

    # 5) НЕТ ВИСЯЧИХ ПЕТЕЛЬ (ось C)
    for i, r in enumerate(journey):
        if not isinstance(r, dict):
            continue
        name = str(r.get("screen", "")).strip() or f"#{i}"
        q = str(r.get("question_raised", "")).strip()
        ans = str(r.get("answered_by", "")).strip().lower()
        if not q:
            continue
        if ans in ("", "none"):
            errs.append(f"«{name}»: поднял вопрос «{q[:40]}», но answered_by=none — "
                        f"висячая петля любопытства (ось C: Sugarman slippery slide)")
            continue
        # answered_by должен быть БОЛЕЕ ПОЗДНИМ экраном
        ai = order_index.get(str(r.get("answered_by", "")).strip())
        if ai is None:
            errs.append(f"«{name}»: answered_by «{r.get('answered_by')}» — нет такого экрана")
        elif ai <= i:
            errs.append(f"«{name}»: вопрос закрывается экраном «{r.get('answered_by')}» ВЫШЕ/"
                        f"на себе (нужен более поздний) — аромат не тянет вперёд (ось C)")

    # 6) ARC-СКЕЛЕТ: хотя бы один primary CTA
    has_primary = any(str(r.get("cta", "")).strip().lower() == "primary"
                      for r in journey if isinstance(r, dict))
    if not has_primary:
        errs.append("нет ни одного cta=primary — воронка не ведёт к целевому действию (ось E/F)")

    # 7) ДУБЛИ ИМЁН (ревью L1): дубль в screens[]/journey ломает order_index (last-wins
    #    скрывает петлю назад) и покрытие. Имена экранов обязаны быть уникальны.
    for label, names in (("screens[]", screens), ("journey", j_names)):
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            errs.append(f"дубли имён в {label}: {dups} - имена экранов обязаны быть уникальны")

    # 8) ПРИВЯЗКА К РЕНДЕРУ (ревью C1): журнал не должен быть оторван от index.html.
    #    Экран локализуем, если его имя (или dom_id строки) есть в рендере как id/data-screen/
    #    name/anchor ИЛИ просто встречается в html. ZERO локализованных при наличии index.html
    #    = журнал фикция -> HARD BLOCK. Частичный недобор -> WARNING (имена могут отличаться).
    if html_lower and j_names:
        def locatable(row):
            cands = [str(row.get("screen", "")).strip().lower(),
                     str(row.get("dom_id", "")).strip().lower()]
            for c in cands:
                if not c:
                    continue
                if (f'id="{c}"' in html_lower or f"id='{c}'" in html_lower
                        or f'data-screen="{c}"' in html_lower or f'href="#{c}"' in html_lower
                        or f'name="{c}"' in html_lower):
                    return True
                if len(c) >= 3 and c in html_lower:  # мягкий фолбэк: имя встречается в рендере
                    return True
            return False
        located = [r for r in journey if isinstance(r, dict) and locatable(r)]
        if len(located) == 0:
            errs.append("журнал ПОЛНОСТЬЮ оторван от index.html - ни один экран не найден в "
                        "рендере (id/data-screen/anchor/текст). Журнал = фикция, не выведен из "
                        "сайта (ревью C1). Привяжи строки к секциям (dom_id) или перестрой журнал.")
        elif len(located) < len(j_names):
            missing_dom = [str(r.get("screen", "")) for r in journey
                           if isinstance(r, dict) and not locatable(r)]
            warns.append(f"экраны журнала НЕ найдены в index.html: {missing_dom} - проверь, что "
                         f"журнал отражает реальный рендер (укажи dom_id строки или переименуй).")

    if warns and not errs:
        print("⚠️ ЖУРНАЛ - предупреждения (не блок, но проверь):")
        for w in warns:
            print("  • " + w)

    if errs:
        print("🛑 ЖУРНАЛ ПУТИ КЛИЕНТА не сходится (Фаза 10, машинный пол):")
        for e in errs:
            print("  • " + e)
        print("\nПочини журнал/порядок экранов (REORDER/ADD/CONNECT) и перепрогони. "
              "Рубрика: references/macro-rubric.md.")
        sys.exit(3)

    print(f"✅ ЖУРНАЛ сходится: {len(screens)} экранов покрыты, осознанность растёт без "
          f"прыжков, петли закрываются ниже, путь ведёт к CTA.")
    sys.exit(0)


if __name__ == "__main__":
    main()