#!/usr/bin/env python3
"""
Рендер ВИДИМОГО ТРЕКЕРА ФАЗ скилла website из блокнота `.website-state.json`.

Зачем (автор): диск-улики и хуки на `open`/Stop ловят саботаж, но автор
ДИСКА НЕ ВИДИТ (работает с телефона) — в чате агент может схлопывать фазы и мутить,
а инструмента поймать его в реальном времени нет. Лечение: КАЖДЫЙ ответ по сайту
заканчивается ТРЕКЕРОМ, и трекер генерится ИЗ ДИСКА (а не из слов агента) — цифры
подделать нельзя. Это «второй <твой-продукт>» ответа (первый = сама работа).

Контракт: агент запускает этот скрипт ПОСЛЕ записи улики текущей подфазы и вставляет
его вывод дословно в конец ответа. Stop-хук `website-tracker-gate.sh` блокирует
завершение ответа в активной website-сессии, если маркера трекера нет в чате.

Использование:
    python3 phase-tracker.py <DIR>     # DIR = папка проекта (где .website-state.json)
    python3 phase-tracker.py           # ищет .website-state.json в CWD

Safe-by-design: нет блокнота → печатает заглушку «СТАДИЯ A / фаза 0», exit 0.
Никогда не падает с ненулевым кодом — это рендер, не гейт.
"""
import json
import os
import sys

MARKER = "━━━ ТРЕКЕР ФАЗ (website) ━━━"

# Фундамент СТАДИИ A: ключ блокнота -> человекочитаемое имя.
# Порядок = порядок прохождения. Для approved-фаз ✅ только при approved==true.
FUNDAMENT = [
    ("0_brief", "Бриф (тип/цель/ЦА/оффер)", True),
    ("1_interview", "Реальное сырьё (без выдумок)", False),
    ("2a_seeds", "Семена-источники", False),
    ("2b_reference", "Референс-доска жанра (≥10 скринов)", True),
    ("2c_synthesis", "Синтез по 3 осям", False),
    ("3a_structure", "Структура + карта экранов", True),
    ("3b_copy", "Копи в регистре типа + humaniser", False),
    ("4_visual", "Визуал-направление", True),
    ("5_tokens", "Токены → Design.md", False),
]

# Микроцикл экрана (СТАДИЯ B). Подфазы со ✋ берутся из approvals[], сборочные — из status.
SCREEN_ORDER = ["pending", "concept", "copy", "design", "build", "review", "done"]


def mark(state):
    return {"done": "✅", "wip": "⏳", "todo": "⬜"}[state]


def fundament_cell(phases, key, needs_approved):
    rec = phases.get(key)
    if not isinstance(rec, dict):
        return mark("todo")
    if needs_approved:
        if rec.get("approved") is True:
            return mark("done")
        return mark("wip")  # запись есть, но не согласовано → в работе
    return mark("done")  # для не-approved фаз присутствие записи = сделано


def screen_refs(proj_dir, name):
    """Индикатор per-screen референсов для трекера (НЕ гейт — гейт это validate-refs/хук).
    Возвращает короткую строку: 'refs N/T', 'SHORTFALL N/T' или 'нет'."""
    man = os.path.join(proj_dir, "refs", name, "_manifest.json")
    if not os.path.exists(man):
        return "нет"
    try:
        m = json.load(open(man, encoding="utf-8"))
    except Exception:
        return "битый"
    target = int(m.get("target", 10))
    mdir = os.path.dirname(man)
    nq = 0        # полноценные эталоны (скрин на диске + разбор)
    analyzed = 0  # разобранные по содержимому (url + разбор), без требования скрина
    for ex in m.get("exemplars", []) or []:
        shot = (ex.get("screenshot") or "").strip()
        p = shot if os.path.isabs(shot) else os.path.join(mdir, shot)
        note = (ex.get("note") or "").strip()
        why = (ex.get("why_works") or "").strip() or note
        rel = (ex.get("niche_relevant") or "").strip() or note
        if ex.get("url") and len(why) >= 40:
            analyzed += 1
        if (ex.get("url") and shot and os.path.exists(os.path.expanduser(p))
                and len(why) >= 60 and len(rel) >= 20):
            nq += 1
    if nq >= target:
        return f"refs {nq}/{target} ✅"
    # research по содержимому есть, но скрины не сняты — показать честно, не «нет»
    if nq == 0 and analyzed > 0:
        return f"разбор {analyzed} (скрины не сняты)"
    if isinstance(m.get("shortfall"), dict):
        return f"SHORTFALL {nq}/{target}"
    return f"refs {nq}/{target} ⛔"


def research_cell(refs_str):
    """Строка screen_refs → символ ✅⏳⬜ для подфазы РЕСЁРЧА экрана.
    Ресёрч (10 эталонов блока) — ПЕРВАЯ подфаза экрана и самая проскакиваемая
    (прецедент: на course_program статус был `copy`, а эталоны «нет» — ресёрч
    проскочен и спрятан хвостом-индикатором). Делаем его видимой ФАЗОЙ.
    Маппинг:
      ✅ полный набор эталонов / честный shortfall;
      ⏳ есть разбор/частичный недобор (скрины не сняты или <target без shortfall);
      ⬜ не начат / битый манифест."""
    if refs_str in ("нет", "битый"):
        return mark("todo")
    if refs_str.endswith("✅") or refs_str.startswith("SHORTFALL"):
        return mark("done")
    # 'разбор N (скрины не сняты)' или 'refs N/T ⛔' → в работе
    return mark("wip")


def screen_cells(scr):
    """Вернуть {concept,copy,design,build,review} символы из status+approvals."""
    status = scr.get("status", "pending")
    approvals = scr.get("approvals") or []
    si = SCREEN_ORDER.index(status) if status in SCREEN_ORDER else 0

    def appr(name):
        if name in approvals:
            return mark("done")
        return mark("wip") if status == name else mark("todo")

    def stagecol(name, done_states):
        if status in done_states:
            return mark("done")
        return mark("wip") if status == name else mark("todo")

    return {
        "concept": appr("concept"),
        "copy": appr("copy"),
        "design": appr("design"),
        "build": stagecol("build", ("review", "done")),
        "review": stagecol("review", ("done",)),
    }


SITE_AXES = ["one_big_idea", "awareness_ladder", "information_scent",
             "persuasion_sequencing", "conversion_physics",
             "editorial_cut", "canvas_continuity", "objection_coverage"]


def macro_review_line(proj_dir):
    """Строка статуса Фазы 10 (макро-ревью сайта как системы) из .site-review.json.
    Показывает min по 8 осям + журнал ✅/⬜; худшие оси, если <9. НЕ гейт — рендер."""
    p = os.path.join(proj_dir, ".site-review.json")
    if not os.path.exists(p):
        return "**Фаза 10 · Макро-ревью (сайт как система)** — ⬜ не пройдено (8 осей, журнал)"
    try:
        sd = json.load(open(p, encoding="utf-8"))
    except Exception:
        return "**Фаза 10 · Макро-ревью** — ⚠️ маркер битый, перепрогони"
    axes = {k: v for k, v in (sd.get("axes") or {}).items() if isinstance(v, (int, float))}
    miss = [a for a in SITE_AXES if a not in axes]
    journey = "✅" if sd.get("journey") else "⬜"
    if miss:
        return (f"**Фаза 10 · Макро-ревью** — ⏳ неполный набор осей (нет {len(miss)}/8) · "
                f"журнал {journey}")
    mn = int(min(axes[a] for a in SITE_AXES))
    if mn >= 9:
        return f"**Фаза 10 · Макро-ревью** — ✅ 8 осей min {mn}/10 · журнал {journey}"
    worst = sorted(axes.items(), key=lambda kv: kv[1])[:2]
    worst_s = ", ".join(f"{k}={v}" for k, v in worst)
    return (f"**Фаза 10 · Макро-ревью** — ⏳ min {mn}/10 (<9) · журнал {journey} · "
            f"худшие: {worst_s}")


def render(path):
    out = [MARKER]
    if not os.path.exists(path):
        out += [
            "Стадия: **A — ФУНДАМЕНТ** · блокнот ещё не создан",
            "СЕЙЧАС: фаза 0 «бриф» (или ранний старт) — улики на диск ещё нет.",
            "→ Запиши улику первой подфазы helper'ом, дальше трекер пойдёт из диска.",
        ]
        print("\n".join(out))
        return

    try:
        st = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        out += [f"(не смог прочитать блокнот: {e})"]
        print("\n".join(out))
        return

    stage = st.get("stage", "site")
    phases = st.get("phases", {}) or {}
    screens = st.get("screens", []) or []
    site_review = st.get("site_review", {}) or {}

    # ── автор: в СТАДИИ ЭКРАНОВ показываем ТОЛЬКО текущий экран ──
    # «не нужно мне этапы 2 и 3, не нужно другие экраны — только текущий, с которым
    # работаем». Без макро-дуги и без списка чужих экранов. Активный экран = active_screen.
    if stage == "screens" and screens:
        active = st.get("active_screen")
        cur = None
        if active:
            cur = next((s for s in screens if s.get("name") == active), None)
        if cur is None:
            cur = next((s for s in screens if s.get("status") != "done"), None)
        if cur is not None:
            c = screen_cells(cur)
            sname = cur.get("name", "?")
            score = cur.get("score")
            score_s = f"   ·   балл {score}/10" if score is not None else ""
            refs = screen_refs(os.path.dirname(path), sname)
            rc = research_cell(refs)
            out.append(f"▶ Экран: **{sname}**{score_s}")
            out.append("    подфазы (по порядку, ничего не пропускать):")
            out.append(f"    {rc} ресёрч — 10 эталонов блока  ({refs})")
            out.append(f"    {c['concept']} концепция  ✋")
            out.append(f"    {c['copy']} копи  ✋")
            out.append(f"    {c['design']} дизайн  ✋")
            out.append(f"    {c['build']} сборка кода")
            out.append(f"    {c['review']} ревью (3 слоя, до ≥9)")
            out.append("")
            now = _now_line(stage, phases, screens, active, os.path.dirname(path))
            out.append(f"**СЕЙЧАС:** {now}")
        else:
            out.append("Все экраны готовы → СТАДИЯ C (сборка сайта).")
        print("\n".join(out))
        return

    stage_name = {
        "site": "A — ФУНДАМЕНТ (сайт, 1 раз)",
        "screens": "B — ЦИКЛ ПО ЭКРАНАМ",
        "assembly": "C — СБОРКА САЙТА (финал)",
        "done": "ГОТОВО",
    }.get(stage, stage)

    out.append(f"Стадия: **{stage_name}**   ·   проект: `{os.path.dirname(path) or '.'}`")
    out.append("")

    # ── МАКРО-СВОДКА: один путь, одна строка на этап (видна вся дуга) ───
    # Принцип (автор): фундамент проходится ОДИН раз. Как только сессия
    # ушла в экраны/сборку — фундамент по определению закрыт (в них нельзя войти, не
    # пройдя стадию A). Поэтому НЕ перепечатываем 9 строк и НЕ пересчитываем их из
    # сырых флагов диска (там бывают непроставленные approved / отсутствующие записи →
    # вечное ложное «6/9»). Свернуть в ✅. Разворачиваем подробно ТОЛЬКО активный этап.
    if stage == "site":
        fund_done = sum(1 for k, _, na in FUNDAMENT if fundament_cell(phases, k, na) == "✅")
        out.append(f"**ЭТАП 1 · Фундамент** — в работе {fund_done}/{len(FUNDAMENT)}")
    else:
        # Фундамент проходится 1 раз и сворачивается. НО research (референс-доска
        # 2b) — главный проскакиваемый шаг (прецедент: флагман из головы мимо
        # reference). Сверяем по САМОЙ УЛИКЕ на диске — наличию скринов доски, а
        # НЕ по флагу approved (он часто не проставлен при реально сделанном
        # ресёрче → иначе ловушка v1.7 «ложная тревога на непроставленный флаг»).
        # Скринов доски нет вообще → НЕ врём «✅», флагуем возможный пропуск.
        ref = phases.get("2b_reference")
        ref = ref if isinstance(ref, dict) else {}
        bdir = os.path.join(os.path.dirname(path), ref.get("board") or "refs")
        has_shots = os.path.isdir(bdir) and any(
            f.lower().endswith(".png") for f in os.listdir(bdir))
        if has_shots:
            out.append("**ЭТАП 1 · Фундамент** — ✅ пройден (стадия A, 1 раз)")
        else:
            out.append("**ЭТАП 1 · Фундамент** — ✅ пройден, ⚠️ но РЕСЁРЧ-ДОСКА (2b) "
                       "пуста/не найдена на диске → проверь, не пропущен ли ресёрч")

    if screens:
        scr_done = sum(1 for s in screens if s.get("status") == "done")
        out.append(f"**ЭТАП 2 · Экраны** — {scr_done}/{len(screens)} готово")
    else:
        out.append("**ЭТАП 2 · Экраны** — карта экранов ещё не записана (конец фазы 3a)")

    sr = site_review.get("score_min", 0)
    if stage == "assembly":
        la = "✅" if site_review.get("layout_audit") else "⬜"
        out.append(f"**ЭТАП 3 · Сборка** — Фаза 09 (экраны) {sr}/10 · layout {la}")
        out.append("  " + macro_review_line(os.path.dirname(path)))
    else:
        out.append("**ЭТАП 3 · Сборка сайта** — после всех экранов (Фаза 09 + Фаза 10 макро)")
    out.append("")

    # ── ДЕТАЛЬ: разворачиваем ТОЛЬКО активный этап ─────────────────────
    if stage == "site":
        out.append("Фундамент по подфазам:")
        for key, label, na in FUNDAMENT:
            out.append(f"  {fundament_cell(phases, key, na)} {label}")
        out.append("")
    elif stage == "screens" and screens:
        # текущий экран = active_screen из блокнота (если ведём экран вне порядка),
        # иначе первый не-done. Разворачиваем подфазы ТОЛЬКО его.
        active = st.get("active_screen")
        idx, cur = None, None
        if active:
            for i, s in enumerate(screens):
                if s.get("name") == active:
                    idx, cur = i, s
                    break
        if cur is None:
            for i, s in enumerate(screens):
                if s.get("status") != "done":
                    idx, cur = i, s
                    break
        if cur is not None:
            c = screen_cells(cur)
            sname = cur.get("name", "?")
            score = cur.get("score")
            score_s = f"   ·   балл {score}/10" if score is not None else ""
            refs = screen_refs(os.path.dirname(path), sname)
            rc = research_cell(refs)
            out.append(f"▶ Текущий экран {idx + 1}/{len(screens)}: **{sname}**{score_s}")
            out.append("    подфазы экрана (по порядку, ничего не пропускать):")
            out.append(f"    {rc} ресёрч — 10 эталонов блока  ({refs})")
            out.append(f"    {c['concept']} концепция  ✋")
            out.append(f"    {c['copy']} копи  ✋")
            out.append(f"    {c['design']} дизайн  ✋")
            out.append(f"    {c['build']} сборка кода")
            out.append(f"    {c['review']} ревью (3 слоя, до ≥9)")
            out.append("")
        else:
            out.append("Все экраны готовы → переход к СТАДИИ C (сборка сайта).")
            out.append("")

    # ── СЕЙЧАС: одна строка «где мы / чего жду» ─────────────────────────
    now = _now_line(stage, phases, screens, st.get("active_screen"),
                    os.path.dirname(path))
    out.append(f"**СЕЙЧАС:** {now}")

    print("\n".join(out))


def _now_line(stage, phases, screens, active=None, proj_dir=None):
    if stage in ("site",) or not screens:
        # первая незакрытая фаза фундамента
        for key, label, na in FUNDAMENT:
            if fundament_cell(phases, key, na) != "✅":
                tail = " — ✋ жду твоё «ок»" if na else " — делаю сам, улика на диск"
                return f"СТАДИЯ A, «{label}»{tail}"
        return "СТАДИЯ A закрыта → перехожу к экранам (СТАДИЯ B)"
    if stage == "screens":
        cur = None
        if active:
            cur = next((s for s in screens if s.get("name") == active), None)
        if cur is None:
            cur = next((s for s in screens if s.get("status") != "done"), None)
        if cur is not None:
            status = cur.get("status", "pending")
            # Ресёрч экрана (10 эталонов блока) — ПЕРВАЯ подфаза. Не собран → это
            # ПРОСКОЧЕННЫЙ шаг, всплывает раньше всего до сборки (прецедент:
            # status=copy при «эталоны: нет» = ресёрч проскочили и спрятали).
            if proj_dir is not None and status in ("pending", "concept", "copy", "design"):
                if research_cell(screen_refs(proj_dir, cur.get("name", ""))) != "✅":
                    return (f"экран «{cur.get('name','?')}» → ⚠️ РЕСЁРЧ НЕ СОБРАН — "
                            f"10 эталонов блока (скрины + манифест) ДО концепции; не пропускать")
            appr = cur.get("approvals") or []
            nxt = {
                "pending": "концепция — соберу и ✋ покажу",
                "concept": "концепция — ✋ жду твоё «ок»" if "concept" not in appr
                           else "копи — собираю",
                "copy": "копи — ✋ жду твоё «ок»" if "copy" not in appr
                        else "дизайн — собираю",
                "design": "дизайн — ✋ жду твоё «ок»" if "design" not in appr
                          else "сборка — делаю сам",
                "build": "сборка кода — делаю сам, молча",
                "review": "готовый экран — ✋ жду твоё «ок»/правки",
            }.get(status, status)
            return f"экран «{cur.get('name','?')}» → подфаза {nxt}"
        return "все экраны готовы → СТАДИЯ C (сборка сайта)"
    if stage == "assembly":
        return "СТАДИЯ C — собираю сайт + макро-review, ✋ финал покажу"
    return "готово"


def main():
    if len(sys.argv) > 1:
        d = os.path.expanduser(sys.argv[1])
    else:
        d = os.getcwd()
    path = d if d.endswith(".website-state.json") else os.path.join(d, ".website-state.json")
    render(path)


if __name__ == "__main__":
    main()