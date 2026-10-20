"""Планировщик: берёт из очереди то, чему пришло время, и отдаёт адаптеру.

Разделение простое. Очередь знает КОГДА и НЕ ДВАЖДЫ, адаптер знает КАК,
раннер знает ЧТО ДЕЛАТЬ С ОТКАЗОМ:

  RateLimited  площадка назвала срок - откладываем ровно на него, не гадаем
  Temporary    моргнуло - откладываем с нарастающей паузой, пока не кончатся попытки
  Permanent    сломано по сути - помечаем упавшим и пишем понятную причину

Раннер сам в сеть не ходит и про площадки ничего не знает
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .platforms import Permanent, RateLimited, Temporary, build as build_adapter

MAX_ATTEMPTS = 5
BASE_BACKOFF = 60.0


@dataclass
class Outcome:
    item_id: str
    platform: str
    status: str
    detail: str = ""
    url: str = ""

    def line(self) -> str:
        tail = " %s" % self.url if self.url else (" %s" % self.detail if self.detail else "")
        return "%s %-9s %s%s" % (self.item_id, self.platform, self.status, tail)


def run_once(queue, http, now: float | None = None, platform: str = "", log=None) -> list[Outcome]:
    now = float(now if now is not None else time.time())
    outcomes: list[Outcome] = []
    adapters: dict = {}

    for item in queue.due(now=now, platform=platform):
        if not queue.claim(item.id):
            # строку уже забрала другая копия движка либо она уже опубликована
            continue
        fresh = queue.get(item.id) or item
        try:
            adapter = adapters.get(fresh.platform) or build_adapter(fresh.platform, http)
        except ValueError as exc:
            queue.mark_failed(fresh.id, str(exc))
            outcomes.append(Outcome(fresh.id, fresh.platform, "failed", str(exc)))
            continue
        adapters[fresh.platform] = adapter

        try:
            result = adapter.publish(fresh)
        except RateLimited as exc:
            queue.mark_retry(fresh.id, exc.retry_after, str(exc))
            outcomes.append(Outcome(fresh.id, fresh.platform, "retry", str(exc)))
        except Temporary as exc:
            if fresh.attempts >= MAX_ATTEMPTS:
                queue.mark_failed(fresh.id, "попытки кончились: %s" % exc)
                outcomes.append(Outcome(fresh.id, fresh.platform, "failed", str(exc)))
            else:
                delay = BASE_BACKOFF * (2 ** max(0, fresh.attempts - 1))
                queue.mark_retry(fresh.id, delay, str(exc))
                outcomes.append(Outcome(fresh.id, fresh.platform, "retry", str(exc)))
        except Permanent as exc:
            queue.mark_failed(fresh.id, str(exc))
            outcomes.append(Outcome(fresh.id, fresh.platform, "failed", str(exc)))
        else:
            queue.mark_published(fresh.id, result.remote_id, result.url)
            outcomes.append(Outcome(fresh.id, fresh.platform, "published", result.remote_id, result.url))

        if log:
            log(outcomes[-1].line())
    return outcomes


def run_forever(queue, http, interval: float = 60.0, log=None, sleep=time.sleep, stop_after: int = 0):
    """Вечный цикл для расписания. stop_after задаётся только тестами"""
    ticks = 0
    while True:
        run_once(queue, http, log=log)
        ticks += 1
        if stop_after and ticks >= stop_after:
            return ticks
        sleep(interval)
