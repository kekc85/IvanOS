#!/usr/bin/env python3
"""Сторож живости планировщика.

Прежняя система умерла молча месяц: обои транслировали протухший горизонт,
никто не проверял свежесть. Этот скрипт - единственная работа которого
кричать, если система перестала дышать.

🔴 ГЛАВНОЕ ИСПРАВЛЕНИЕ: СТОРОЖ БОЛЬШЕ НЕ МЕРЯЕТ САМ СЕБЯ.
Раньше он смотрел на mtime sprint.json, а sprint.json безусловно переписывал
вечерний ритуал - то есть датчик показывал работу МАШИНЫ. Пока жив launchd,
порог свежести не мог сработать никогда, а четыре дня отсутствия владельца
давали «ВСЁ ХОРОШО» каждый день. Это буквально тот дефект, который убил
прошлую систему: предохранитель питался от датчика, который отключается первым.

Теперь два независимых датчика:
  ЧЕЛОВЕК  - след человеческого действия (pulse): отметка выполнения, правка
             через интерфейс, решение через decide.py. Записи, сделанные
             ритуалами, в этот счёт не входят по конструкции (машина после
             своей записи снимает отпечаток данных).
  МАШИНА   - отработали ли сами ритуалы (есть ли отчёты дня и разбор недели).
Оба должны быть живы. Один зелёный при мёртвом другом = тревога.

Доставка: тревога уходит СИСТЕМНЫМ УВЕДОМЛЕНИЕМ macOS, а при затяжной тревоге
(2+ дня) ещё и модальным окном. ALERT.md остаётся протоколом, но каналом
доставки он не является: крик в файл, который никто не открывает, тревогой
не считается.

Выход: 1 при проблемах, 0 если всё дышит.
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    PLANNER_JSON, REVIEWS_DIR, TASKS_DIR, DAILY_DIR, ALERT_FILE, DATA_FILES,
    load_json, today, now, sync_pulse, read_pulse, write_pulse, notify,
    run_ritual, is_planned, ritual_code, hours_since_human, atomic_write_text,
    STATE_DIR, TRACKER_JSON, SYNC_FRESH_HOURS, MACHINE_SOURCES,
)

HUMAN_STALE_DAYS = 3        # столько без единого человеческого действия = тревога
NO_DONE_DAYS = 3            # столько закрытых дней подряд без единой отметки = тревога
DECISION_STALE_DAYS = 2     # столько висит needsDecision - движок реально стоит
MTIME_STALE_DAYS = 3
REVIEW_DUE_AFTER_DAYS = 7
REVIEW_FRESH_WITHIN_DAYS = 9
ESCALATE_AFTER_DAYS = 2     # тревога висит столько - показываем модальное окно
CONFLICT_MARKER = "<<<<<<<"

DECIDE_CMD = "python3 ~/planner/rituals/decide.py"


def mtime_of(path: Path):
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def check_human(pulse, problems, info):
    """Датчик №1: жив ли человек. Только он решает, работает система или крутится вхолостую."""
    hrs = hours_since_human(pulse)
    if hrs is None:
        info.append("след человека: ещё не заведён (первый запуск сторожа)")
        return
    days = hrs / 24.0
    info.append(
        f"след человека: {pulse.get('lastHumanAt')} ({days:.1f} дн. назад) - {pulse.get('lastHumanWhat', '?')}"
    )
    if days >= HUMAN_STALE_DAYS:
        problems.append((
            "critical",
            f"ЧЕЛОВЕКА НЕТ {days:.1f} дн.: ни одной отметки выполнения, правки через интерфейс "
            f"или решения (порог {HUMAN_STALE_DAYS} дн.). Ритуалы при этом продолжают крутиться "
            "вхолостую - именно так умерла прошлая система"
        ))


def check_done_marks(pulse, problems, info):
    """Датчик №1b: закрытые дни подряд, где было что делать и не отмечено ничего."""
    days = pulse.get("days") or {}
    real = [
        (k, v) for k, v in sorted(days.items(), reverse=True)
        if isinstance(v, dict) and not v.get("preexisting") and (v.get("planned") or 0) > 0
    ]
    if not real:
        info.append("журнал закрытых дней: пока нет дней с запланированными задачами")
        return
    streak = []
    for k, v in real:
        if (v.get("done") or 0) == 0:
            streak.append(k)
        else:
            break
    last_k, last_v = real[0]
    info.append(
        f"последний закрытый день с задачами: {last_k} - отмечено {last_v.get('done')} из {last_v.get('planned')}"
    )
    if len(streak) >= NO_DONE_DAYS:
        problems.append((
            "critical",
            f"{len(streak)} закрытых дней подряд без единой отметки выполнения "
            f"({', '.join(reversed(streak))}) - план есть, исполнения нет"
        ))


def check_rituals(problems, info, t):
    """Датчик №2: отрабатывают ли сами ритуалы. Отдельно от человека."""
    y = t - timedelta(days=1)
    close_y = DAILY_DIR / f"{y.isoformat()}-close.md"
    open_t = DAILY_DIR / f"{t.isoformat()}-open.md"
    if close_y.exists():
        info.append(f"вечерний ритуал: отчёт за {y.isoformat()} на месте")
    else:
        problems.append((
            "warn",
            f"нет отчёта вечернего ритуала за {y.isoformat()} ({close_y.name}) - "
            "launchd-юнит com.ivan.sprint-daily-close не отработал и не догнал пропуск"
        ))
    cur_min = now().hour * 60 + now().minute
    if open_t.exists():
        info.append(f"утренний ритуал: сводка за {t.isoformat()} на месте")
    elif cur_min >= 12 * 60:
        problems.append((
            "warn",
            f"нет утренней сводки за {t.isoformat()} ({open_t.name}) - "
            "com.ivan.sprint-daily-open не отработал или упал"
        ))


def check_files(problems, info):
    for label, path in DATA_FILES.items():
        mt = mtime_of(path)
        if mt is None:
            if label == "sprint.json":
                problems.append(("critical", "sprint.json не создан - планировщику не с чем работать"))
            else:
                info.append(f"{label}: не создан")
            continue
        age_days = (now() - mt).days
        info.append(f"{label}: последнее изменение {mt.strftime('%Y-%m-%d %H:%M')} ({age_days} дн. назад)")
        if label == "sprint.json" and age_days > MTIME_STALE_DAYS:
            # теперь это ВТОРИЧНЫЙ признак: файл трогает и машина, и человек
            problems.append((
                "warn",
                f"sprint.json не менялся {age_days} дн. (порог {MTIME_STALE_DAYS}) - "
                "не двигается ни машина, ни человек"
            ))


def check_device_sync(problems, info):
    """Сторож забора прибора. Обещан был в ДВУХ местах и не существовал нигде.

    Шаг 12 ТЗ дословно приведён ответ владельца. Докстринг самого инструмента
    повторял это владельцу как факт. В стороже при этом не было ни слова про
    забор, то есть молча умерший синк не поднял бы тревогу ниоткуда, а громкое
    падение срабатывало только когда синк кто-то запускал руками. Это ровно
    «мягкая деградация как молча выключенный барьер».

    Три исхода, и молчаливого среди них нет:
      строк прибора в трекере нет      -> сторожить нечего, строка в info;
      забора не было ни разу           -> info: владелец ещё не входил в Прибор;
      забор был и протух / упал        -> problems, уровень по возрасту.
    """
    status_file = STATE_DIR / "device-last-sync.json"
    try:
        track = json.loads(TRACKER_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        info.append(f"забор прибора: трекер не прочитан ({exc}), сторожить нечего")
        return
    device_rows = [h for h in track.get("habits", [])
                   if not h.get("archived") and h.get("source") in ("device", "device")]
    if not device_rows:
        info.append("забор прибора: строк прибора в активном списке нет, сторожить нечего")
        return
    if not status_file.exists():
        info.append(f"забор прибора: не запускался ни разу ({len(device_rows)} строк ждут "
                    "первого входа владельца в Прибор). Это не тревога, это «нет данных»")
        return
    try:
        st = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problems.append(("warn", f"состояние забора прибора нечитаемо: {status_file} ({exc})"))
        return
    at = st.get("at") or ""
    try:
        age_h = (now() - datetime.fromisoformat(at)).total_seconds() / 3600.0
    except (TypeError, ValueError):
        problems.append(("warn", f"в {status_file.name} нет разбираемого времени забора: {at!r}"))
        return
    info.append("забор прибора: последний ответ %s назад, ok=%s"
                % (f"{age_h:.1f} ч", st.get("ok")))
    if not st.get("ok"):
        problems.append(("critical",
                         "забор прибора упал и не восстановился: %s. Привычки прибора (%d) стоят "
                         "в «нет данных», зелёным никто не притворяется"
                         % (str(st.get("reason") or "причина не записана")[:160], len(device_rows))))
        return
    if age_h > SYNC_FRESH_HOURS:
        problems.append(("critical",
                         "последний УСПЕШНЫЙ забор прибора был %.1f ч назад при пороге %d ч: "
                         "синк умер молча, %d строк прибора уходят в «протухли»"
                         % (age_h, SYNC_FRESH_HOURS, len(device_rows))))


def maybe_run_device_sync(info):
    """Забор на РАСПИСАНИИ без единого нового юнита launchd.

    Сторож уже стоит в 12:00 и 21:00 - ровно та частота, которую ТЗ назвало для
    проверки свежести забора. Своего юнита у забора нет намеренно: пока владелец
    не вошёл в Прибор, юнит дважды в сутки падал бы с critical и приучал бы к
    красному, а критерий 12 ТЗ отдельно требует, чтобы список launchd за круг не
    вырос ни на строку. Поэтому забор цепляется к уже загруженному сторожу и
    запускается ТОЛЬКО когда токен физически есть, то есть после первого входа.
    """
    token = STATE_DIR / "device-token.json"
    if not token.exists():
        info.append("забор прибора: токена нет, запуск не пробуем (владелец ещё не входил в Прибор)")
        return
    # с этой версии выгрузку делает релей (tools/device_fetch_relay.py, кроны 12:00 и
    # 21:00 МСК на боевом релее владельца), Мак только принимает снапшоты и ставит
    # отметки - поэтому сторож зовёт приёмник, а не прямой забор
    tool = Path(__file__).resolve().parent.parent / "tools" / "device_pull.py"
    if not tool.exists():
        info.append(f"забор прибора: инструмент не найден по пути {tool}")
        return
    try:
        r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, timeout=180)
        info.append("приём снапшотов Прибор с релея запущен сторожем, код выхода %d" % r.returncode)
    except subprocess.TimeoutExpired:
        info.append("приём снапшотов Прибор не уложился в 180 секунд, снят по таймауту")
    except OSError as exc:
        info.append(f"забор прибора не запустился: {exc}")


def check_decisions(sprint, problems, info, t):
    events = [e for e in (sprint.get("events") or []) if isinstance(e, dict)]
    stuck = [e for e in events if e.get("needsDecision") is True]
    if not stuck:
        info.append("флагов «требует решения» нет")
        return
    oldest_days = 0
    for e in stuck:
        ss = e.get("stuckSince")
        try:
            oldest_days = max(oldest_days, (t - date.fromisoformat(ss)).days) if ss else oldest_days
        except (ValueError, TypeError):
            continue
    titles = ", ".join(f"{e.get('id', '?')} {e.get('title', '?')}" for e in stuck[:4])
    level = "critical" if oldest_days >= DECISION_STALE_DAYS else "warn"
    problems.append((
        level,
        f"движок остановлен: {len(stuck)} задач(а) ждут решения "
        f"(старшая висит {oldest_days} дн.): {titles}. Снять: {DECIDE_CMD} <id> do|drop|delegate|someday"
    ))


def check_conflicts(problems, info):
    conflicted = []
    for md in sorted(TASKS_DIR.glob("*.md")):
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if CONFLICT_MARKER in content:
            conflicted.append(md.name)
    if conflicted:
        problems.append(("warn", "неразрешённые git-конфликты в: " + ", ".join(conflicted)))
    else:
        info.append("git-конфликтов в tasks/*.md не найдено")


def check_horizon(sprint, problems, info, t):
    """Протухший горизонт. Раньше проверка была всегда зелёной: несделанные
    задачи ритуал переносил вперёд, и «будущие события» находились всегда."""
    events = [e for e in (sprint.get("events") or []) if isinstance(e, dict)]
    planned = [e for e in events if is_planned(e)]
    if not planned:
        problems.append(("critical", "в sprint.json нет ни одного запланированного события"))
        return
    dates = []
    for e in planned:
        ds = e.get("date")
        if not isinstance(ds, str):
            continue
        try:
            dates.append((date.fromisoformat(ds), e))
        except ValueError:
            continue
    if not dates:
        problems.append(("critical", "у событий sprint.json нет ни одной валидной даты"))
        return
    future = [(dt, e) for dt, e in dates if dt >= t]
    if not future:
        problems.append((
            "critical",
            f"все события sprint.json в прошлом (последнее {max(dt for dt, _ in dates).isoformat()}) - горизонт протух"
        ))
        return
    fresh_future = [
        (dt, e) for dt, e in future
        if not e.get("moved") and not ritual_code(e)
    ]
    if not fresh_future:
        problems.append((
            "warn",
            "впереди только перенесённый хвост: ни одного НОВОГО запланированного события. "
            "Горизонт держится на переносах, а не на плане"
        ))
    else:
        info.append(
            f"горизонт: {len(fresh_future)} непереносных событий впереди, последнее "
            f"{max(dt for dt, _ in future).isoformat()}"
        )


def check_week_and_review(sprint, problems, info, t):
    raw = sprint.get("weekStart")
    week_start = None
    if raw:
        try:
            week_start = date.fromisoformat(raw)
        except (ValueError, TypeError):
            problems.append(("warn", f"weekStart в sprint.json битый: {raw!r}"))
    if week_start:
        week_end = week_start + timedelta(days=6)
        if not (week_start <= t <= week_end):
            problems.append((
                "warn",
                f"неделя в sprint.json протухла: окно {week_start.isoformat()}..{week_end.isoformat()} "
                f"не содержит сегодня ({t.isoformat()})"
            ))
        else:
            info.append(f"окно недели: {week_start.isoformat()}..{week_end.isoformat()}, сегодня внутри")

        if (t - week_start).days >= REVIEW_DUE_AFTER_DAYS:
            latest = None
            if REVIEWS_DIR.exists():
                files = sorted(REVIEWS_DIR.glob("weekly-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
                if files:
                    latest = files[0]
            if latest is None:
                problems.append(("warn", "нет ни одного файла разбора недели в reviews/, хотя цикл идёт больше недели"))
            else:
                age = (now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
                info.append(f"последний разбор недели: {latest.name} ({age} дн. назад)")
                if age > REVIEW_FRESH_WITHIN_DAYS:
                    problems.append((
                        "warn",
                        f"последний разбор недели старше {REVIEW_FRESH_WITHIN_DAYS} дн. ({latest.name}) - WAM не отрабатывает"
                    ))
        else:
            info.append("разбор недели пока не должен был случиться (неделя младше 7 дней)")
    else:
        info.append("weekStart не задан - проверка недели и разбора пропущена")


def main():
    t = today()
    pulse = sync_pulse()
    problems = []
    info = []

    check_human(pulse, problems, info)
    check_done_marks(pulse, problems, info)
    check_rituals(problems, info, t)
    check_files(problems, info)
    check_conflicts(problems, info)
    maybe_run_device_sync(info)
    check_device_sync(problems, info)

    sprint, err = load_json(PLANNER_JSON)
    if err:
        problems.append(("critical", f"sprint.json недоступен: {err}"))
    else:
        check_decisions(sprint, problems, info, t)
        check_horizon(sprint, problems, info, t)
        check_week_and_review(sprint, problems, info, t)

    stamp = now().strftime("%Y-%m-%d %H:%M")
    pulse = read_pulse()

    if problems:
        critical = [p for lvl, p in problems if lvl == "critical"]
        warns = [p for lvl, p in problems if lvl != "critical"]

        since = pulse.get("alertSince")
        if not since:
            since = now().isoformat(timespec="seconds")
            pulse["alertSince"] = since
        try:
            since_days = (now() - datetime.fromisoformat(since)).days
        except (ValueError, TypeError):
            since_days = 0
        pulse["alertLastAt"] = now().isoformat(timespec="seconds")
        write_pulse(pulse)

        lines = [
            "# 🔴 ALERT: сторож нашёл проблему",
            "",
            f"Проверка: {stamp}. Тревога висит с {since} ({since_days} дн.).",
            "",
        ]
        if critical:
            lines.append("## Критично")
            lines += [f"- {p}" for p in critical]
            lines.append("")
        if warns:
            lines.append("## Предупреждения")
            lines += [f"- {p}" for p in warns]
            lines.append("")
        lines += ["## Справочно"]
        lines += [f"- {i}" for i in info]
        lines += ["", "Почини и перезапусти watchdog.py вручную, чтобы снять флаг."]
        text = "\n".join(lines) + "\n"
        atomic_write_text(ALERT_FILE, text)

        head = critical[0] if critical else warns[0]
        more = len(problems) - 1
        message = head + (f" (и ещё {more})" if more > 0 else "")
        channel = notify(
            "🔴 Планировщик: сторож" if critical else "⚠️ Планировщик: сторож",
            message,
            level="critical" if critical else "warn",
            modal=bool(critical) and since_days >= ESCALATE_AFTER_DAYS,
        )

        print(text)
        print("=" * 40)
        print(f"СТОРОЖ: {len(problems)} проблема(ы), из них критичных {len(critical)}.")
        print(f"Доставка: {channel}. Протокол: {ALERT_FILE}")
        sys.exit(1)

    if ALERT_FILE.exists():
        # Снятая тревога не стирается (правило владельца номер ноль), а уезжает
        # датированным файлом рядом: история срабатываний сторожа читаема
        snyatye = ALERT_FILE.parent / "alerty-snyatye"
        snyatye.mkdir(parents=True, exist_ok=True)
        os.replace(str(ALERT_FILE),
                   str(snyatye / f"ALERT-{now().strftime('%Y%m%d-%H%M%S')}.md"))
        notify("✅ Планировщик ожил", f"Тревога снята {stamp}", level="info")
    if pulse.get("alertSince"):
        pulse.pop("alertSince", None)
        pulse.pop("alertLastAt", None)
        write_pulse(pulse)
    print(f"Проверка {stamp}: всё хорошо.")
    for i in info:
        print(f"- {i}")


if __name__ == "__main__":
    run_ritual("watchdog", main)
