"""Расчёт таймингов переходов. Часовой пояс воронок = Europe/Moscow (как в конструкторе воронок)."""
from __future__ import annotations
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")


def next_daily(from_dt: datetime, hh: int, mm: int) -> datetime:
    """Следующий календарный день в hh:mm по МСК, строго после from_dt.

    Семантика конструктора воронок send_date=next_day: всегда следующий день, даже если
    сейчас раньше hh:mm. Возвращает aware-datetime в МСК.
    """
    local = from_dt.astimezone(MSK)
    target_date = (local + timedelta(days=1)).date()
    return datetime.combine(target_date, time(hh, mm), tzinfo=MSK)


def parse_hhmm(send_time: str) -> tuple[int, int]:
    hh, mm = send_time.split(":")
    return int(hh), int(mm)


def clamp_send_window(dt: datetime, start_h: int = 10, end_h: int = 21) -> datetime:
    """Окно отправки дожима 10:00-21:00 МСК (фронт-цепочка событие).

    Дозревание ночью/рано утром → сегодня в start_h:05; поздним вечером →
    завтра в start_h:05. Внутри окна - без изменений.
    """
    local = dt.astimezone(MSK)
    if local.hour < start_h:
        return local.replace(hour=start_h, minute=5, second=0, microsecond=0)
    if local.hour >= end_h:
        nxt = (local + timedelta(days=1)).replace(hour=start_h, minute=5, second=0, microsecond=0)
        return nxt
    return dt
