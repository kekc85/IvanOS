#!/usr/bin/env python3
"""WAM (weekly After-action Model) - разбор недели.

Запускается ВЕЧЕРОМ СУББОТЫ (воскресенье - защищённый день, разбор туда не ставим).

Считает execution score недели, сравнивает с порогом 85%, кричит явно если
две недели подряд ниже порога, считает личный коэффициент недооценки
(actual/est), перечисляет задачи needsDecision, считает часы по дорожкам.

Три вещи, которые здесь починены:

1. ИМЯ ФАЙЛА ВСЕГДА ОТ ОКНА, А НЕ ОТ СЕГОДНЯШНЕЙ ДАТЫ. Раньше окно бралось из
   sprint.weekStart, а имя - от текущей недели: при протухшем weekStart разбор
   писал ЧУЖОЕ содержимое в файл соседней недели. Плюс перед записью проверяем
   маркер окна в уже существующем файле и не затираем чужое.

2. «СРАВНИТЬ НЕ С ЧЕМ» - ЭТО НЕ «ВСЁ ХОРОШО». Правило двух недель ниже порога
   раньше рвалось молча: нет файла прошлой недели, битый маркер, пустая неделя -
   и ни строки об этом. Теперь причина пишется явно.

3. МАШИННЫЕ РИТУАЛЫ ВНЕ СЧЁТА. Событие «Разбор недели» человек не отмечает
   никогда - в знаменателе score ему не место.

Читает: tasks/sprint.json, tasks/reviews/ (для сравнения с прошлой неделей).
Пишет: tasks/reviews/weekly-YYYY-Wnn.md + печать в stdout. sprint.json НЕ трогает.
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLANNER_JSON, REVIEWS_DIR, load_json, today, now, write_report, sync_pulse,
    notify, run_ritual, is_planned, is_fixed, ritual_code, dur_min,
    GOALS_CYCLE_JSON,
)

THRESHOLD = 85.0
SCORE_COMMENT_RE = re.compile(r"<!--\s*score=([\d.]+|none)\s*-->")
WINDOW_COMMENT_RE = re.compile(r"<!--\s*window=(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})\s*-->")
DECIDE_CMD = "python3 ~/planner/rituals/decide.py"


def iso_week_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def review_path_for_window(week_start: date) -> Path:
    """Имя файла - от НАЧАЛА ОКНА, которое разбираем. Так содержимое и имя
    не могут разъехаться."""
    return REVIEWS_DIR / f"weekly-{iso_week_label(week_start)}.md"


def read_marker(path: Path):
    """(score, (start, end), text) из файла разбора. score = None если маркера нет
    или он битый; окно = None если маркера окна нет (файл от старой версии)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, None, None
    m = SCORE_COMMENT_RE.search(text)
    score = None
    if m and m.group(1) != "none":
        try:
            score = float(m.group(1))
        except ValueError:
            score = None
    w = WINDOW_COMMENT_RE.search(text)
    window = None
    if w:
        try:
            window = (date.fromisoformat(w.group(1)), date.fromisoformat(w.group(2)))
        except ValueError:
            window = None
    return score, window, text


def resolve_window(sprint: dict, d: date):
    """Окно недели + диагноз его состояния."""
    raw = sprint.get("weekStart")
    notes = []
    week_start = None
    if raw:
        try:
            week_start = date.fromisoformat(raw)
        except (ValueError, TypeError):
            notes.append(f"weekStart в sprint.json битый ({raw!r}) - взял текущую календарную неделю")
    else:
        notes.append("weekStart в sprint.json отсутствует - взял текущую календарную неделю")
    if week_start is None:
        week_start = d - timedelta(days=d.weekday())
    week_end = week_start + timedelta(days=6)
    if not (week_start <= d <= week_end):
        notes.append(
            f"weekStart протух: окно {week_start.isoformat()}..{week_end.isoformat()} "
            f"не содержит сегодня ({d.isoformat()}). Разбор считаю по окну из файла, "
            "и файл называю по нему же - чужую неделю не трогаю."
        )
    return week_start, week_end, notes




# ---------------------------------------------------------------------------
# ЗАДАЧИ СЛЕДУЮЩЕЙ НЕДЕЛИ ЦИКЛА. Методология владельца: план недели рождается в
# субботнем WAM из тактик цикла (mastery/planning/СИСТЕМА.md:145), а северная
# задача выбирается фокусирующим вопросом Келлера (там же, :63). Ритуал
# ПЕРЕЧИСЛЯЕТ задачи и отдельно называет те, под которыми нет ни одного действия.
# Владелец при этом ничего не нажимает: он читает готовый список.
# ---------------------------------------------------------------------------

def cycle_week_numbers(goals, days):
    c = (goals or {}).get("cycle") or {}
    try:
        start = date.fromisoformat(str(c.get("start")))
        total = int(c.get("weeks") or 0)
    except (TypeError, ValueError):
        return set()
    out = set()
    for d in days:
        diff = (d - start).days
        if diff >= 0 and 1 <= diff // 7 + 1 <= total:
            out.add(diff // 7 + 1)
    return out


def next_week_task_lines(sprint, week_start):
    nxt = [week_start + timedelta(days=7 + i) for i in range(7)]
    keys = {x.isoformat() for x in nxt}
    lines = ["## Задачи цикла на следующую неделю (%s - %s)"
             % (nxt[0].isoformat(), nxt[-1].isoformat())]
    goals, err = load_json(GOALS_CYCLE_JSON)
    if err:
        lines += ["Цели цикла не прочитаны: %s" % err, ""]
        return lines
    weeks = cycle_week_numbers(goals, nxt)
    rows = []
    for g in goals.get("goals", []):
        for t in g.get("tasks", []):
            if t.get("done") is True:
                continue
            if any(int(n) in weeks for n in (t.get("weeks") or []) if isinstance(n, int)):
                rows.append((g, t))
    if not rows:
        c = goals.get("cycle") or {}
        lines += ["Незакрытых задач цикла на эту неделю нет (цикл «%s», старт %s)."
                  % (c.get("name", "?"), c.get("start", "?")), ""]
        return lines
    events = [e for e in sprint.get("events", []) if isinstance(e, dict)]
    bare = []
    lines.append("Номера недель цикла в этом окне: %s" % ", ".join(str(x) for x in sorted(weeks)))
    for g, t in rows:
        acts = [e for e in events if e.get("taskId") == t.get("id") and e.get("date") in keys]
        mark = "🔴" if not acts else "·"
        lines.append("- %s `%s` %s - цель «%s», действий в календаре: %d"
                     % (mark, t.get("id"), t.get("title"), g.get("title"), len(acts)))
        if not acts:
            bare.append(t)
    lines.append("")
    if bare:
        lines.append("Под этими задачами НЕТ ни одного действия в следующей неделе: %s"
                     % ", ".join("`%s`" % t.get("id") for t in bare))
        lines.append("Северная задача недели по фокусирующему вопросу: `%s` %s"
                     % (rows[0][1].get("id"), rows[0][1].get("title")))
        lines.append("Вытянуть их в календарь можно на вкладке «Неделя»: полоса «Задачи цикла» над сеткой.")
    else:
        lines.append("Под каждой задачей следующей недели уже стоит хотя бы одно действие.")
    lines.append("")
    return lines


def main():
    d = today()
    sync_pulse()

    sprint, err = load_json(PLANNER_JSON)
    if err:
        out_path = REVIEWS_DIR / f"weekly-{iso_week_label(d)}.md"
        text = f"<!-- score=none -->\n# WAM {iso_week_label(d)}\n\nНет данных спринта: {err}\n"
        write_report(out_path, text)
        notify("🔴 Разбор недели без данных", str(err), level="critical")
        print(text)
        return

    events = [e for e in sprint.get("events", []) if isinstance(e, dict)]
    tracks = sprint.get("tracks", {}) or {}

    def track_label(code):
        tr = tracks.get(code) if isinstance(tracks, dict) else None
        if isinstance(tr, dict) and tr.get("label"):
            return tr["label"]
        return code or "?"

    week_start, week_end, window_notes = resolve_window(sprint, d)
    week_label = iso_week_label(week_start)
    out_path = review_path_for_window(week_start)

    def in_week(e):
        ds = e.get("date")
        if not isinstance(ds, str):
            return False
        try:
            ed = date.fromisoformat(ds)
        except ValueError:
            return False
        return week_start <= ed <= week_end

    week_planned = [e for e in events if in_week(e) and is_planned(e)]
    week_rituals = [e for e in week_planned if ritual_code(e)]
    week_human = [e for e in week_planned if not ritual_code(e)]
    done = [e for e in week_human if e.get("done") is True]
    score = (len(done) / len(week_human) * 100) if week_human else None

    # ---- Две недели подряд ниже порога: либо сравнение, либо честное «не с чем»
    prev_start = week_start - timedelta(days=7)
    prev_path = review_path_for_window(prev_start)
    prev_score, prev_window, _prev_text = read_marker(prev_path)
    compare_blockers = []
    if not prev_path.exists():
        compare_blockers.append(f"файла прошлой недели нет ({prev_path.name})")
    else:
        if prev_window is None:
            compare_blockers.append(
                f"в {prev_path.name} нет маркера окна (файл от старой версии) - "
                "беру score на веру, окно подтвердить нечем"
            )
        elif prev_window[0] != prev_start:
            compare_blockers.append(
                f"{prev_path.name} описывает другое окно "
                f"({prev_window[0].isoformat()}..{prev_window[1].isoformat()}), а нужно "
                f"{prev_start.isoformat()}..{(prev_start + timedelta(days=6)).isoformat()}"
            )
        if prev_score is None:
            compare_blockers.append(f"в {prev_path.name} нет читаемого score (маркер отсутствует или битый)")
    if score is None:
        compare_blockers.append("у ТЕКУЩЕЙ недели нет ни одной активной задачи человека - score не считается")

    hard_blockers = [b for b in compare_blockers if "беру score на веру" not in b]
    two_weeks_low = (
        not hard_blockers
        and score is not None
        and prev_score is not None
        and score < THRESHOLD
        and prev_score < THRESHOLD
    )

    # ---- Личный коэффициент недооценки
    pairs = []
    for pool in (events, sprint.get("backlog", []) or []):
        for e in pool:
            if not isinstance(e, dict):
                continue
            est, actual = e.get("est"), e.get("actual")
            if (
                isinstance(est, (int, float)) and not isinstance(est, bool)
                and isinstance(actual, (int, float)) and not isinstance(actual, bool)
                and est
            ):
                pairs.append(actual / est)
    coef = sum(pairs) / len(pairs) if pairs else None

    stuck = [e for e in events if e.get("needsDecision") is True]
    fixed_unmarked = [e for e in week_planned if is_fixed(e) and e.get("done") is not True and
                      (date.fromisoformat(e["date"]) <= d if isinstance(e.get("date"), str) else False)]

    hours_by_track = {}
    for e in week_planned:
        tr = e.get("track", "?")
        hours_by_track[tr] = hours_by_track.get(tr, 0) + dur_min(e) / 60

    # ---- Сборка отчёта
    lines = []
    lines.append(f"<!-- score={score:.1f} -->" if score is not None else "<!-- score=none -->")
    lines.append(f"<!-- window={week_start.isoformat()}..{week_end.isoformat()} -->")
    lines.append(f"# WAM {week_label} ({week_start.isoformat()} - {week_end.isoformat()})")
    lines.append("")

    if window_notes:
        lines.append("## ⚠️ Окно недели")
        for n_ in window_notes:
            lines.append(f"- {n_}")
        lines.append("")

    lines.append("## Execution score недели")
    if week_human:
        lines.append(f"Закрыто {len(done)} из {len(week_human)} активных задач человека - {score:.0f}%")
        lines.append(f"Порог {THRESHOLD:.0f}% {'выполнен' if score >= THRESHOLD else 'НЕ выполнен'}")
    else:
        lines.append("На неделе не было запланированных активных задач человека.")
    if week_rituals:
        lines.append(
            f"_Вне счёта {len(week_rituals)} машинных ритуалов: "
            + ", ".join(e.get("title", "?") for e in week_rituals) + "_"
        )
    lines.append("")

    lines.append("## Правило двух недель ниже порога")
    if two_weeks_low:
        lines.append("### 🔴 Пора пересматривать план, а не стараться сильнее")
        lines.append(f"Две недели подряд ниже {THRESHOLD:.0f}%: прошлая {prev_score:.0f}%, эта {score:.0f}%.")
    elif hard_blockers:
        lines.append("⚠️ **Сравнить не с чем - это НЕ «всё хорошо».** Причина:")
        for b in compare_blockers:
            lines.append(f"- {b}")
        lines.append("Правило двух недель на этой итерации не сработало. Знай об этом.")
    else:
        soft = [b for b in compare_blockers if b not in hard_blockers]
        prev_txt = f"{prev_score:.0f}%" if prev_score is not None else "нет"
        lines.append(f"Сравнение состоялось: прошлая неделя {prev_txt}, эта {score:.0f}%. Двух провалов подряд нет.")
        for b in soft:
            lines.append(f"- оговорка: {b}")
    lines.append("")

    lines.append("## Оценка против факта")
    if coef is not None:
        lines.append(f"Личный коэффициент недооценки: {coef:.2f} (по {len(pairs)} парам est/actual)")
        lines.append("Новые оценки времени умножать на этот коэффициент.")
    else:
        lines.append(
            "Пар est/actual нет: поле actual не проставлено ни у одного события. "
            "Пока коэффициент мёртв, оценки времени остаются inside view."
        )
    lines.append("")

    lines.append("## 🔒 Жёсткие слоты недели без отметки")
    if fixed_unmarked:
        for e in fixed_unmarked:
            lines.append(
                f"- [{track_label(e.get('track'))}] **{e.get('title')}** {e.get('date')} "
                f"{e.get('start', '')} - прошло без отметки, проверь"
            )
    else:
        lines.append("Таких нет.")
    lines.append("")

    lines.append("## 🔴 Задачи, требующие решения (движок стоит)")
    if stuck:
        for e in stuck:
            lines.append(
                f"- `{e.get('id', '?')}` [{track_label(e.get('track'))}] {e.get('title')} - "
                f"перенесена {e.get('moved', '?')} раз(а), висит с {e.get('stuckSince', '?')}"
            )
        lines.append("")
        lines.append("```")
        lines.append(f"{DECIDE_CMD} <id> do | drop | delegate | someday")
        lines.append("```")
    else:
        lines.append("Таких задач нет.")
    lines.append("")

    lines.extend(next_week_task_lines(sprint, week_start))

    lines.append("## Часы по дорожкам за неделю")
    if hours_by_track:
        for tr, hrs in sorted(hours_by_track.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {track_label(tr)}: {hrs:.1f} ч")
    else:
        lines.append("Нет данных по часам.")
    lines.append("")

    text = "\n".join(lines) + "\n"

    # ---- Защита от затирания чужого файла
    if out_path.exists():
        _s, existing_window, _t = read_marker(out_path)
        if existing_window is not None and existing_window[0] != week_start:
            alt = REVIEWS_DIR / (
                f"weekly-{week_label}-window-{week_start.isoformat()}-{now().strftime('%H%M%S')}.md"
            )
            text = text.replace(
                f"# WAM {week_label}",
                f"# WAM {week_label}\n\n> ⚠️ Файл {out_path.name} занят разбором другого окна "
                f"({existing_window[0].isoformat()}..{existing_window[1].isoformat()}), он НЕ перезаписан.",
                1,
            )
            out_path = alt
            notify(
                "⚠️ Разбор недели: конфликт окон",
                f"{out_path.name} - чужой файл не перезаписан",
                level="warn",
            )

    write_report(out_path, text)
    print(text)
    print(f"_Отчёт: {out_path}_")

    if two_weeks_low:
        notify(
            "🔴 Планировщик: две недели ниже порога",
            f"прошлая {prev_score:.0f}%, эта {score:.0f}%. План пересматривать, а не стараться сильнее.",
            level="critical",
        )
    elif hard_blockers:
        notify(
            "⚠️ Разбор недели: сравнить не с чем",
            "; ".join(hard_blockers),
            level="warn",
        )


if __name__ == "__main__":
    run_ritual("wam", main)
