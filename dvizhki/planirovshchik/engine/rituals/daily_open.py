#!/usr/bin/env python3
"""Утренний ритуал: короткая сводка дня.

Big 3, часы дня против нормы из профиля, машинные ленты auto на сегодня,
точки запуска kind=launch (что нужно нажать руками), жёсткие слоты дня,
и - обязательно - хвост «требует решения», из-за которого движок стоит.

Раньше сводка падала TypeError'ом на событии с priority: null (сравнение None
с int при сортировке), файл дня не создавался, а трейс уходил в лог, который
никто не читает. Теперь сортировки терпят мусор, а падение ритуала бьёт
системным уведомлением.

Читает: tasks/sprint.json, tasks/profile.json.
Пишет: tasks/daily/YYYY-MM-DD-open.md + печать в stdout. sprint.json НЕ трогает.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLANNER_JSON, DAILY_DIR, ALERT_FILE, load_json, load_profile, today,
    parse_hhmm, write_report, sync_pulse, hours_since_human, notify, run_ritual,
    is_planned, is_fixed, ritual_code, dur_min, safe_start, safe_priority,
    capacity_norm_min, load_days, human_closed_at,
    GOALS_CYCLE_JSON,
    TRACKER_JSON, available_habits, device_state, ENGINE_MARKS,
    visual_duplicates, collapse_visual_duplicates,
)

DECIDE_CMD = "python3 ~/planner/rituals/decide.py"
BIG = float("inf")


def pick_big3(events_today):
    """Big 3 дня. Приоритет берём только у событий, где он действительно число:
    priority: null раньше валил сортировку."""
    active = [e for e in events_today if e.get("kind") == "active" and not ritual_code(e)]
    prioritized = sorted(
        [e for e in active if safe_priority(e) is not None],
        key=lambda e: (safe_priority(e), safe_start(e)),
    )
    rest = sorted([e for e in active if safe_priority(e) is None], key=safe_start)
    if prioritized:
        picked = (prioritized + rest)[:3]
        basis = "по приоритету" + (", добор по времени" if len(prioritized) < 3 and rest else "")
        return picked, basis
    return rest[:3], "первые по времени (числового priority ни у одной задачи нет)"



# ---------------------------------------------------------------------------
# СЛЕДУЮЩИЙ ШАГ. владелец обозначил приоритет явно. Значит утренний ритуал обязан назвать ОДНО
# конкретное действие ПО ИМЕНИ, а не показать сводку и промолчать. Та же строка
# рисуется в движке над сеткой недели (static/tab-week.js, renderNextStep).
# ---------------------------------------------------------------------------

def cycle_weeks_of_week(goals, days):
    """Номера недель цикла, накрывающие набор дат. Считаем ПО ДАТАМ, а не по одному
    номеру: календарная неделя движка начинается с понедельника, а неделя цикла со дня старта цикла - на одном номере часть задач терялась бы."""
    c = (goals or {}).get("cycle") or {}
    try:
        start = date.fromisoformat(str(c.get("start")))
        total = int(c.get("weeks") or 0)
    except (TypeError, ValueError):
        return set()
    out = set()
    for d in days:
        diff = (d - start).days
        if diff < 0:
            continue
        idx = diff // 7 + 1
        if 1 <= idx <= total:
            out.add(idx)
    return out


def tasks_of_week(goals, days):
    """[(цель, задача)] - незакрытые задачи целей, попадающие на эти дни."""
    weeks = cycle_weeks_of_week(goals, days)
    out = []
    for g in (goals or {}).get("goals", []):
        for t in g.get("tasks", []):
            if t.get("done") is True:
                continue
            if any(int(n) in weeks for n in (t.get("weeks") or []) if isinstance(n, int)):
                out.append((g, t))
    return out


def next_step_lines(events_today, sprint, d):
    """Одно конкретное действие по имени. Порядок: ближайшее незакрытое событие
    сегодня -> первая задача недели цикла, под которой нет ни одного действия."""
    lines = ["## Следующий шаг"]
    open_today = sorted(
        [e for e in events_today if e.get("done") is not True and e.get("kind") != "auto"],
        key=safe_start)
    if open_today:
        e = open_today[0]
        lines.append(f"**{safe_start(e)} · {e.get('title')}** - ближайшее незакрытое действие на сегодня.")
        if e.get("taskId"):
            lines.append(f"Оно привязано к задаче цели `{e['taskId']}`.")
        lines.append("")
        return lines
    goals, _err = load_json(GOALS_CYCLE_JSON)
    week_days = [d + timedelta(days=i - d.weekday()) for i in range(7)]
    rows = tasks_of_week(goals or {}, week_days)
    if not rows:
        c = ((goals or {}).get("cycle") or {})
        lines.append(f"На сегодня незакрытых действий нет, и задач цикла на эту неделю тоже "
                     f"(цикл «{c.get('name', '?')}» стартует {c.get('start', '?')}).")
        lines.append("")
        return lines
    keys = {(d + timedelta(days=i - d.weekday())).isoformat() for i in range(7)}
    events = (sprint or {}).get("events", [])
    bare = [(g, t) for g, t in rows
            if not [e for e in events if e.get("taskId") == t.get("id") and e.get("date") in keys]]
    g, t = (bare or rows)[0]
    lines.append(f"**{t.get('title')}** (`{t.get('id')}`, цель «{g.get('title')}») - "
                 + ("под ней в этой неделе нет ни одного действия."
                    if bare else "ближайшая задача цикла на эту неделю."))
    lines.append("Открой вкладку «Неделя» и вытяни эту строку из полосы задач цикла в календарь.")
    lines.append("")
    return lines


def main():
    d = today()
    d_str = d.isoformat()
    out_path = DAILY_DIR / f"{d_str}-open.md"

    pulse = sync_pulse()
    days_map = load_days()

    sprint, err = load_json(PLANNER_JSON)
    lines = [f"# Утро {d_str}", ""]

    # Первая строка сводки: вчера закрыл сам - не машинная формулировка вечернего
    # ритуала. Проверяем НЕЗАВИСИМО от sprint.json (days.json - отдельный ресурс).
    yesterday = d - timedelta(days=1)
    y_closed_at = human_closed_at(days_map, yesterday.isoformat())
    if y_closed_at:
        lines.append(f"Вчера ты закрыл день сам в {y_closed_at}.")
        lines.append("")

    if err:
        lines.append(f"Нет данных спринта: {err}")
        lines.append("Планировщик не может собрать сводку - создай sprint.json.")
        text = "\n".join(lines) + "\n"
        write_report(out_path, text)
        notify("🔴 Утренняя сводка без данных", str(err), level="critical")
        print(text)
        return

    profile = load_profile()
    tracks = sprint.get("tracks", {}) or {}
    events = [e for e in sprint.get("events", []) if isinstance(e, dict)]
    auto = [a for a in (sprint.get("auto", []) or []) if isinstance(a, dict)]
    events_today = [e for e in events if e.get("date") == d_str]

    def track_label(code):
        tr = tracks.get(code) if isinstance(tracks, dict) else None
        if isinstance(tr, dict) and tr.get("label"):
            return tr["label"]
        return code or "?"

    # Тревога сторожа - первой строкой, иначе её никто не увидит
    if ALERT_FILE.exists():
        lines.append("## 🔴 Сторож поднял тревогу")
        try:
            body = ALERT_FILE.read_text(encoding="utf-8")
        except OSError:
            body = ""
        for row in body.splitlines():
            if row.startswith("- "):
                lines.append(row)
        lines.append(f"_Подробно: {ALERT_FILE}_")
        lines.append("")

    # Хвост, из-за которого движок стоит
    stuck = [e for e in events if e.get("needsDecision") is True]
    if stuck:
        lines.append("## 🔴 Движок остановлен: ждёт твоего решения")
        for e in stuck:
            lines.append(
                f"- `{e.get('id', '?')}` [{track_label(e.get('track'))}] {e.get('title')} - "
                f"перенесена {e.get('moved', '?')} раз(а), висит с {e.get('stuckSince', '?')}"
            )
        lines.append("")
        lines.append("```")
        lines.append(f"{DECIDE_CMD} <id> do | drop | delegate | someday")
        lines.append("```")
        lines.append("")

    # Big 3
    # Визуально одинаковые записи схлопываются В ОТЧЁТЕ, а не в данных: дубль
    # лежит в sprint.json со времён до этих работ, удалять его нельзя, а читать
    # утром одну и ту же строку дважды владелец не должен
    dups = visual_duplicates(events_today)
    big3, basis = pick_big3(collapse_visual_duplicates(events_today))
    lines.append("## Три главные задачи")
    if not big3:
        lines.append("На сегодня в sprint.json нет активных задач.")
    else:
        lines.append(f"_Отбор: {basis}_")
        lines.append("")
        for e in big3:
            note = f" - {e['note']}" if e.get("note") else ""
            lines.append(f"- **{safe_start(e) if safe_start(e) != '99:99' else '?'}** [{track_label(e.get('track'))}] {e.get('title')}{note}")
    if dups:
        for (d, st, title), rows in sorted(dups.items(), key=lambda kv: str(kv[0][1])):
            ids = ", ".join(str(x.get("id", "?")) for x in rows)
            lines.append(f"_В данных эта запись лежит {len(rows)} раза: **{st} {title}**. "
                         f"id: {ids}. В отчёте показана один раз, из sprint.json ничего не "
                         f"удалено - лишнюю снимаешь сам_")
    lines.append("")

    # Жёсткие слоты дня
    fixed_today = sorted([e for e in collapse_visual_duplicates(events_today) if is_fixed(e)],
                         key=safe_start)
    lines.append("## 🔒 Жёсткие слоты сегодня (не двигаются)")
    if fixed_today:
        for e in fixed_today:
            state = "отмечено" if e.get("done") is True else "ждёт отметки"
            lines.append(f"- **{safe_start(e)}** {e.get('title')} ({state})")
    else:
        lines.append("Сегодня жёстких слотов нет.")
    lines.append("")

    # Часы дня против нормы
    active_today = [e for e in events_today if is_planned(e)]
    planned_min = sum(dur_min(e) for e in active_today)
    norm_min = capacity_norm_min(profile)
    capacity_pct = profile.get("capacityPercent", 60)
    ws, we = parse_hhmm(profile.get("workStart")), parse_hhmm(profile.get("workEnd"))

    lines.append("## Часы дня против нормы")
    if norm_min is None:
        lines.append(f"Запланировано: {planned_min/60:.1f} ч")
        lines.append(
            "🔴 Норму посчитать нельзя: в профиле рабочее окно противоречиво "
            f"(workStart={profile.get('workStart')}, workEnd={profile.get('workEnd')}). "
            "Правило ёмкости сегодня НЕ работает - почини профиль."
        )
    else:
        window_min = we - ws
        lines.append(
            f"Запланировано: {planned_min/60:.1f} ч из окна {window_min/60:.1f} ч "
            f"({profile.get('workStart')}-{profile.get('workEnd')})"
        )
        lines.append(f"Норма при ёмкости {capacity_pct}%: {norm_min/60:.1f} ч")
        if planned_min > norm_min:
            lines.append(
                f"🔴 Перегруз на {(planned_min - norm_min)/60:.1f} ч сверх нормы - буфера под реактив не остаётся"
            )
        else:
            lines.append(f"В норме, буфер {(norm_min - planned_min)/60:.1f} ч")
    lines.append("")

    lines.extend(next_step_lines(events_today, sprint, d))

    # Привычки в УТРЕННЕМ отчёте. Раньше утренний ритуал не знал о них ни строкой,
    # хотя часть галочек объявлена автоматической: владелец узнавал о трекере
    # только вечером, и то что прибор молчит - не узнавал никогда
    lines.append("## Привычки сегодня")
    track, terr = load_json(TRACKER_JSON)
    if terr:
        lines.append("Трекер прочитать не вышло: %s" % terr)
    else:
        # день передаётся явно: у строк с частотой по дням недели множество
        # доступного у понедельника и у воскресенья разное
        rows = available_habits(track, d_str)
        ask_rows = [h for h in rows if h.get("source") == "ask"]
        machine_rows = [h for h in rows if h.get("source") != "ask"]
        state = device_state(track)
        lines.append("Доступных сегодня единиц: %d, из них спрошу вечером %d." % (len(rows), len(ask_rows)))
        # остаток знаменателя называется по имени: иначе разницу между числами
        # владелец читает как «где-то потерялась единица»
        for h in machine_rows:
            lines.append("Не спрошу, ставит движок: «%s» - %s"
                         % (h["name"], ENGINE_MARKS.get(h["id"], "движок, адрес не назван").split(" · ")[-1]))
        dev = [h for h in track.get("habits", [])
               if not h.get("archived") and h.get("source") in ("device", "device")]
        if dev:
            lines.append("Привычки прибора (%d): состояние «%s». %s"
                         % (len(dev), state,
                            "В счёт дня не идут, зелёными не показываются." if state != "ok"
                            else "Ставятся сами, спрашивать не буду."))
    lines.append("")

    # Машинные ленты auto на сегодня
    lines.append("## Машинные ленты сегодня (auto)")
    running = [a for a in auto if str(a.get("from", "")) <= d_str <= str(a.get("to", ""))]
    if running:
        for a in running:
            note = f" - {a['note']}" if a.get("note") else ""
            lines.append(f"- [{track_label(a.get('track'))}] {a.get('title')} ({a.get('from')} -> {a.get('to')}){note}")
    else:
        lines.append("Сегодня ничего не идёт фоном.")
    lines.append("")

    # Точки запуска
    lines.append("## Точки запуска сегодня (нажать руками)")
    launches = sorted([e for e in events_today if e.get("kind") == "launch"], key=safe_start)
    if launches:
        for e in launches:
            note = f" - {e['note']}" if e.get("note") else ""
            lines.append(f"- **{safe_start(e)}** {e.get('title')}{note}")
    else:
        lines.append("Сегодня нет точек запуска.")
    lines.append("")

    # След человека - чтобы утром было видно, дышит ли система
    hrs = hours_since_human(pulse)
    lines.append("## След человека")
    if hrs is None:
        lines.append("Следа ещё нет (первый запуск).")
    else:
        lines.append(
            f"Последнее живое действие: {pulse.get('lastHumanAt')} ({hrs/24:.1f} дн. назад) - "
            f"{pulse.get('lastHumanWhat', '?')}"
        )
    lines.append("")

    text = "\n".join(lines) + "\n"
    write_report(out_path, text)
    print(text)

    if stuck:
        notify(
            "Планировщик: движок ждёт решения",
            f"{len(stuck)} задач(а) заблокированы после 3 переносов. {DECIDE_CMD} list",
            level="warn",
        )


if __name__ == "__main__":
    run_ritual("daily_open", main)
