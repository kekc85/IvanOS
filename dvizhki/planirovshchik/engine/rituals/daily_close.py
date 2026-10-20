#!/usr/bin/env python3
"""Вечерний ритуал: счёт дня, перенос несделанного, счётчик переносов.

Что здесь важно и почему именно так:

1. ЦЕЛЕВОЙ ДЕНЬ ОПРЕДЕЛЯЕТСЯ ПО ФАКТУ, а не по календарю. Ритуал стоит на 22:30,
   ноут в это время часто спит, launchd догоняет пропуск после пробуждения - и
   «сегодня» уже другой день. Раньше вчерашние несделанные задачи сиротели на
   прошлой дате. Теперь закрываются ВСЕ незакрытые дни по порядку, а сегодняшний
   день закрывается только после PLANNER_CLOSE_AFTER (по умолчанию 20:00).

2. ЖЁСТКИЕ СЛОТЫ НЕ ПЕРЕНОСЯТСЯ. Событие с fixed:true (эфир, суд, встреча)
   машина не двигает никогда - только докладывает «прошло без отметки, проверь».

3. МАШИННЫЕ РИТУАЛЫ В СЧЁТ НЕ ИДУТ. «Разбор недели» человек не отмечает никогда,
   раньше он переносился вечно и топил score.

4. ПЕРЕНОС УЧИТЫВАЕТ ЗАГРУЗКУ ДНЯ. Пятница больше не сваливает всё на субботу,
   где уже стоят эфир и разбор недели.

5. ФАЙЛ ПИШЕТСЯ, ТОЛЬКО ЕСЛИ ЧТО-ТО РЕАЛЬНО ИЗМЕНИЛОСЬ. Безусловная запись
   sprint.json делала сторожа слепым: порог свежести не мог сработать никогда.

Читает: tasks/sprint.json, tasks/profile.json (для protectedDays и ёмкости).
Пишет: tasks/daily/YYYY-MM-DD-close.md, и только при реальных изменениях -
tasks/sprint.json (атомарно, после бэкапа в sprint/backups/).
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLANNER_JSON, DAILY_DIR, load_json, load_profile, now,
    backup_and_write_sprint, write_report, dumps_sprint_style, read_pulse,
    sync_pulse, note_machine_write, record_day_closed, notify, run_ritual,
    is_planned, is_fixed, ritual_code, dur_min, parse_hhmm, next_free_day,
    load_days, human_closed_at, TRACKER_JSON, today,
    available_habits, day_adherence, device_state, write_adherence_mark, ENGINE_MARKS,
    ADHERENCE_THRESHOLD,
)

MOVE_LIMIT = 3          # пережил 3 переноса - дальше не двигаем, нужен выбор человека
LOOKBACK_DAYS = 7       # глубже в прошлое догонять не лезем
CLOSE_AFTER_DEFAULT = "20:00"

DECIDE_CMD = "python3 ~/planner/rituals/decide.py"


def safe_int(v, default=0):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def close_after_min() -> int:
    raw = os.environ.get("PLANNER_CLOSE_AFTER", CLOSE_AFTER_DEFAULT)
    m = parse_hhmm(raw)
    return m if m is not None else parse_hhmm(CLOSE_AFTER_DEFAULT)


def days_to_close(sprint: dict, pulse: dict, n) -> list:
    """Все незакрытые дни по порядку. Сегодня входит в список только после
    времени закрытия - иначе ночной догон схлопнул бы ещё не прожитый день."""
    t = n.date()
    closed = pulse.get("days") or {}

    cur_min = n.hour * 60 + n.minute
    end = t if cur_min >= close_after_min() else t - timedelta(days=1)

    last_closed = pulse.get("lastClosedDate")
    start = None
    if last_closed:
        try:
            start = date.fromisoformat(last_closed) + timedelta(days=1)
        except ValueError:
            start = None
    if start is None:
        # Первый запуск: журнала закрытых дней ещё нет. Задним числом всю неделю
        # не схлопываем - иначе каскад переносов сразу выбросит все задачи
        # в needsDecision. Закрываем только текущий целевой день, дальше работает журнал.
        start = end

    floor = t - timedelta(days=LOOKBACK_DAYS)
    if start < floor:
        start = floor

    out = []
    d = start
    while d <= end:
        d_str = d.isoformat()
        already = d_str in closed or (DAILY_DIR / f"{d_str}-close.md").exists()
        out.append((d, already))
        d += timedelta(days=1)
    return out


def close_one_day(sprint: dict, profile: dict, d: date, is_catchup: bool, moved_in_run: set):
    """Закрывает один день. Возвращает (текст отчёта, статистика).

    moved_in_run - id задач, которые уже двинули в ЭТОМ прогоне. Догон нескольких
    пропущенных дней не должен накручивать счётчик переносов: человек отложил
    задачу один раз, а не столько раз, сколько ноут проспал."""
    d_str = d.isoformat()
    events = sprint.get("events", [])
    tracks = sprint.get("tracks", {}) or {}
    protected_days = profile.get("protectedDays", ["sun"]) or []

    def track_label(code):
        tr = tracks.get(code) if isinstance(tracks, dict) else None
        if isinstance(tr, dict) and tr.get("label"):
            return tr["label"]
        return code or "?"

    planned = [e for e in events if is_planned(e) and e.get("date") == d_str]
    rituals = [e for e in planned if ritual_code(e)]
    human = [e for e in planned if not ritual_code(e)]

    done = [e for e in human if e.get("done") is True]
    undone = [e for e in human if e.get("done") is not True]
    fixed_undone = [e for e in undone if is_fixed(e)]
    movable = [e for e in undone if not is_fixed(e)]
    score = (len(done) / len(human) * 100) if human else None

    moved_rows = []
    stuck_new = []
    for e in movable:
        eid = e.get("id")
        repeat_in_run = eid is not None and eid in moved_in_run
        current = safe_int(e.get("moved"), 0)
        if current >= MOVE_LIMIT and not repeat_in_run:
            # пережила MOVE_LIMIT переносов - дальше не двигаем, нужен выбор человека
            e["needsDecision"] = True
            e.setdefault("stuckSince", d_str)
            stuck_new.append(e)
            continue
        target, load_after, norm, overloaded = next_free_day(
            d, protected_days, events, profile, add_min=dur_min(e)
        )
        if not repeat_in_run:
            e["moved"] = current + 1
            if eid is not None:
                moved_in_run.add(eid)
        e["date"] = target.isoformat()
        moved_rows.append((e, target, load_after, norm, overloaded))

    all_stuck = [e for e in events if isinstance(e, dict) and e.get("needsDecision") is True]

    lines = [f"# Вечер {d_str}", ""]
    if is_catchup:
        lines.append(
            f"⚠️ Догон: день закрыт задним числом {now().strftime('%Y-%m-%d %H:%M')} "
            "(ритуал не отработал вовремя - ноут спал). Задачи этого дня не осиротели."
        )
        lines.append("")

    lines.append("## Счёт дня")
    if human:
        lines.append(f"Закрыто {len(done)} из {len(human)} - execution score {score:.0f}%")
    else:
        lines.append("На этот день активных задач человека в sprint.json не было.")
    if rituals:
        lines.append(
            "_Вне счёта (машинные ритуалы, человек их не отмечает): "
            + ", ".join(e.get("title", "?") for e in rituals) + "_"
        )
    lines.append("")

    lines.append("## Перенесено")
    if moved_rows:
        for e, target, load_after, norm, overloaded in moved_rows:
            tail = ""
            if norm is not None:
                tail = f" - день после переноса {load_after/60:.1f} ч при норме {norm/60:.1f} ч"
                if overloaded:
                    tail += ", СВОБОДНОГО ДНЯ В ГОРИЗОНТЕ НЕТ, выбран наименее загруженный"
            elif overloaded:
                tail = " - свободного дня в горизонте нет"
            lines.append(
                f"- [{track_label(e.get('track'))}] {e.get('title')} → {target.isoformat()} "
                f"(перенос №{e['moved']}){tail}"
            )
    else:
        lines.append("Ничего не перенесено.")
    lines.append("")

    lines.append("## 🔒 Жёсткие слоты без отметки (машина их НЕ двигает)")
    if fixed_undone:
        for e in fixed_undone:
            lines.append(
                f"- [{track_label(e.get('track'))}] **{e.get('title')}** {d_str} "
                f"{e.get('start', '')} - прошло без отметки, проверь. Слот жёсткий, остаётся на месте."
            )
    else:
        lines.append("Таких нет.")
    lines.append("")

    lines.append("## 🔴 Требует решения (пережила 3 переноса, автоматика остановлена)")
    if all_stuck:
        for e in all_stuck:
            mark = " ← новое" if any(e is s for s in stuck_new) else ""
            lines.append(
                f"- `{e.get('id', '?')}` [{track_label(e.get('track'))}] {e.get('title')} - "
                f"перенесена {e.get('moved', '?')} раз(а), висит с {e.get('stuckSince', '?')}{mark}"
            )
        lines.append("")
        lines.append("Снять флаг (движок стоит, пока не решишь):")
        lines.append("```")
        lines.append(f"{DECIDE_CMD} list")
        lines.append(f"{DECIDE_CMD} <id> do        # делаю, вернуть в сетку")
        lines.append(f"{DECIDE_CMD} <id> drop      # удалить")
        lines.append(f"{DECIDE_CMD} <id> delegate  # делегировать, уходит в бэклог")
        lines.append(f"{DECIDE_CMD} <id> someday   # в someday с TTL 30 дней")
        lines.append("```")
    else:
        lines.append("Таких задач нет.")
    lines.append("")

    lines.extend(habits_block(d_str))

    stats = {
        "planned": len(human),
        "done": len(done),
        "moved": len(moved_rows),
        "fixedUnmarked": len(fixed_undone),
        "stuckNew": len(stuck_new),
        "score": round(score, 1) if score is not None else None,
        "catchup": bool(is_catchup),
    }
    return "\n".join(lines) + "\n", stats


HABITS_CMD = "python3 ~/planner/tools/habits.py"


def habits_block(d_str):
    """Строки отчёта про привычки за день.

    Смысл блока: владелец трекер руками не ведёт и не должен - за него отмечает
    ассистент с его слов. Значит в вечернем отчёте обязана быть видна ровно одна
    вещь: собраны привычки за этот день или нет, и чем их добрать. Без этой строки
    несобранный день выглядит так же, как собранный, и трекер тихо умирает - он
    уже простоял с нулём отмеченных дней при живом списке.

    Ошибку чтения глотаем в строку отчёта: вечерний ритуал не должен падать
    целиком из-за трекера."""
    out = ["## Привычки"]
    try:
        with open(TRACKER_JSON, encoding="utf-8") as f:
            track = json.load(f)
        # ЗНАМЕНАТЕЛЬ равен множеству, которое ритуал РЕАЛЬНО спрашивает.
        # Что здесь было: done_n считался по ВСЕМ активным, а open_rows только по
        # спрашиваемым. На новом списке это дало бы «Отмечено 17 из 23» и следом
        # «День собран полностью» - две несовместимые строки подряд, и строки
        # «Не собрано» при этом не было бы вовсе. Теперь обе строки считаются по
        # одному и тому же множеству available_habits(): доступные сегодня единицы.
        # Привычки прибора до первого входа владельца в знаменатель НЕ входят -
        # иначе мета-порог 85 процентов красный по конструкции с первого дня.
        #
        # 🔴 ВТОРАЯ половина той же арифметики, и она чинилась отдельно. Знаменатель
        # уже был приведён к available_habits(), а строка «Не собрано» продолжала
        # считаться по source == "ask": движковая строка стояла В ЗНАМЕНАТЕЛЕ и не
        # появлялась ни среди отмеченных, ни среди несобранных. Владелец читал
        # «Отмечено 0 из 16» и следом «Не собрано 15», а шестнадцатая не была
        # названа нигде и закрыть её было негде. Теперь несобранное считается по
        # ТОМУ ЖЕ множеству, что знаменатель, и держится тождество
        # done_n + len(undone) == avail_n, а машинные незакрытые называются
        # поимённо вместе с адресом, где они закрываются.
        rows = available_habits(track, d_str)
        log = (track.get("log") or {}).get(d_str, {})
        undone = [h for h in rows if not log.get(h["id"])]
        open_rows = [h for h in undone if h.get("source") == "ask"]
        open_machine = [h for h in undone if h.get("source") != "ask"]
        done_n, avail_n, pct = day_adherence(track, d_str)
        state = device_state(track)
        out.append(f"Отмечено {done_n} из {avail_n} доступных сегодня ({pct}%).")
        # ЗДЕСЬ движок ставит мета-порог сам - это код за `source: engine` у строки
        # adherence_85. Раньше строка обещала «ставит трекер», а писать её было
        # нечему, и ячейка оставалась бы пустой навсегда
        try:
            mark = write_adherence_mark(d_str)
            if mark is not None:
                _ok = mark[0]
                out.append(f"Мета-порог adherence_85 за день поставлен движком: "
                           f"{'взят' if _ok else 'не взят'} ({pct}% при пороге {ADHERENCE_THRESHOLD}%).")
        except Exception as e:  # noqa: BLE001 - отметка мета-порога не роняет отчёт
            out.append(f"Мета-порог поставить не вышло: {e}")
        if state != "ok":
            skipped = [h for h in track.get("habits", [])
                       if not h.get("archived") and h.get("source") in ("device", "device")]
            out.append(f"Привычки прибора ({len(skipped)}) в состоянии «{state}» и в счёт дня не идут: "
                       "зелёным по протухшим данным никто не притворяется.")
        if undone:
            out.append(
                f"Не собрано {len(undone)} из {avail_n}: "
                + ", ".join(h["name"] for h in undone[:8])
                + ("..." if len(undone) > 8 else "")
            )
        if open_machine:
            for h in open_machine:
                # владельцу идёт человеческая половина значения, после « · »:
                # адрес в коде ему не нужен, ему нужен адрес на экране
                where = ENGINE_MARKS.get(h["id"], "движок, адрес не назван").split(" · ")[-1]
                out.append(f"Машинная строка «{h['name']}» за день не закрыта. "
                           f"Руками она не отмечается, её закрывает {where}")
        if open_rows:
            out.append("")
            out.append("Добрать со слов владельца:")
            out.append("```")
            out.append(f"{HABITS_CMD} --date {d_str} ask")
            out.append(f"{HABITS_CMD} --date {d_str} set <id или слова через запятую>")
            out.append("```")
        elif done_n == avail_n and avail_n:
            out.append("День собран полностью, спрашивать нечего.")
        elif undone:
            out.append("Спрашивать нечего: всё оставшееся закрывает движок, см. строки выше.")
    except Exception as e:  # noqa: BLE001 - отчёт важнее причины сбоя
        out.append(f"Трекер прочитать не вышло: {e}")
    out.append("")
    return out


def close_one_day_human(sprint: dict, d: date, closed_at: str, is_catchup: bool):
    """День уже закрыт человеком руками из интерфейса (days.json[d].closedAt заполнен).
    По каждой открытой задаче человек уже решил сам - машина НЕ переносит их повторно
    и НЕ трогает moved (второй перенос за день = лимит трёх переносов выбирается вдвое
    быстрее, ровно баг W1 из реестра). Функция read-only: sprint не мутируется вообще,
    цифры done/planned - только для отчёта и для журнала pulse."""
    d_str = d.isoformat()
    events = sprint.get("events", [])
    planned = [e for e in events if is_planned(e) and e.get("date") == d_str]
    human = [e for e in planned if not ritual_code(e)]
    done = [e for e in human if e.get("done") is True]
    score = (len(done) / len(human) * 100) if human else None

    lines = [f"# Вечер {d_str}", ""]
    if is_catchup:
        lines.append(
            f"⚠️ Догон: ритуал добрался до этого дня только {now().strftime('%Y-%m-%d %H:%M')} "
            "(ноут спал), но день уже был закрыт человеком раньше."
        )
        lines.append("")
    lines.append(f"День закрыл владелец в {closed_at}, машине нечего делать.")
    if human:
        lines.append(
            f"Отмечено {len(done)} из {len(human)}"
            + (f" - {score:.0f}%" if score is not None else "")
            + ". Задачи не переносились, счётчик переносов не тронут - по каждой открытой уже решил человек."
        )
    lines.append("")

    lines.extend(habits_block(d_str))

    stats = {
        "planned": len(human),
        "done": len(done),
        "moved": 0,
        "fixedUnmarked": 0,
        "stuckNew": 0,
        "score": round(score, 1) if score is not None else None,
        "catchup": bool(is_catchup),
        "closedByHuman": True,
        "humanClosedAt": closed_at,
    }
    return "\n".join(lines) + "\n", stats


def main():
    n = now()
    t = n.date()
    sync_pulse()

    sprint, err = load_json(PLANNER_JSON)
    if err:
        out_path = DAILY_DIR / f"{t.isoformat()}-close.md"
        text = f"# Вечер {t.isoformat()}\n\nНет данных спринта: {err}\n"
        write_report(out_path, text)
        notify("🔴 Вечерний ритуал без данных", str(err), level="critical")
        print(text)
        return

    profile = load_profile()
    pulse = read_pulse()
    days_map = load_days()

    before = dumps_sprint_style(sprint)

    plan = days_to_close(sprint, pulse, n)
    fresh = [(d, already) for d, already in plan if not already]
    preexisting = [d for d, already in plan if already]

    for d in preexisting:
        days = (read_pulse().get("days") or {})
        if d.isoformat() not in days:
            # отчёт уже был (старый прогон), в журнал его заносим нулевым,
            # чтобы догон не пытался закрыть день повторно
            record_day_closed(d, {"planned": 0, "done": 0, "moved": 0, "preexisting": True})

    if not fresh:
        cur_min = n.hour * 60 + n.minute
        msg = [
            f"# Вечер {t.isoformat()}",
            "",
            "Закрывать нечего: все прошедшие дни уже закрыты"
            + (
                f", сегодняшний закрывается после {os.environ.get('PLANNER_CLOSE_AFTER', CLOSE_AFTER_DEFAULT)}"
                f" (сейчас {n.strftime('%H:%M')})"
                if cur_min < close_after_min() else ""
            )
            + ".",
            "",
            "_sprint.json не тронут - сторож должен видеть настоящую свежесть данных._",
        ]
        print("\n".join(msg))
        return

    reports = []
    all_stats = []
    moved_in_run = set()
    for d, _already in fresh:
        is_catchup = d < t
        closed_at = human_closed_at(days_map, d.isoformat())
        if closed_at:
            text, stats = close_one_day_human(sprint, d, closed_at, is_catchup)
        else:
            text, stats = close_one_day(sprint, profile, d, is_catchup, moved_in_run)
        out_path = DAILY_DIR / f"{d.isoformat()}-close.md"
        write_report(out_path, text)
        reports.append((d, text, out_path))
        all_stats.append((d, stats))

    after = dumps_sprint_style(sprint)
    changed = after != before
    backup_path = None
    if changed:
        backup_path = backup_and_write_sprint(sprint)
        note_machine_write(PLANNER_JSON)

    for d, stats in all_stats:
        record_day_closed(d, stats)

    for d, text, out_path in reports:
        print(text)
        print(f"_Отчёт: {out_path}_")
        print()

    if changed:
        print(f"sprint.json обновлён. Бэкап: {backup_path}")
    else:
        print("sprint.json не менялся: переносить было нечего. Сторож видит настоящую свежесть.")

    total_stuck = sum(s.get("stuckNew", 0) for _d, s in all_stats)
    total_fixed = sum(s.get("fixedUnmarked", 0) for _d, s in all_stats)
    catchup_days = [d.isoformat() for d, s in all_stats if s.get("catchup")]

    parts = []
    # Привычки едут В САМО УВЕДОМЛЕНИЕ, а не только в md-файл. Строка «не собрано N»
    # в файле, который никто не открывает, тревогой не является: владелец видит
    # уведомление и не видит отчёт
    try:
        with open(TRACKER_JSON, encoding="utf-8") as f:
            _tr = json.load(f)
        _done, _avail, _pct = day_adherence(_tr, today().isoformat())
        if _avail and _done < _avail:
            parts.append("привычки: отмечено %d из %d доступных (%d%%)" % (_done, _avail, _pct))
        elif _avail:
            parts.append("привычки: день собран полностью")
    except Exception:                                   # noqa: BLE001 - отчёт важнее причины
        parts.append("привычки: трекер не прочитан")
    if catchup_days:
        parts.append("догнал дни: " + ", ".join(catchup_days))
    if total_fixed:
        parts.append(f"жёстких слотов без отметки: {total_fixed}")
    if total_stuck:
        parts.append(f"требуют решения: {total_stuck}")
    if parts:
        notify(
            "Вечерний ритуал планировщика",
            "; ".join(parts) + ". Добрать: habits.py ask. Отчёт в tasks/daily/",
            level="critical" if total_stuck else "warn",
        )


if __name__ == "__main__":
    run_ritual("daily_close", main)
