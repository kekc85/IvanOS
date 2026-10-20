"""Поведение на лимитах. Отдельный файл, потому что это отдельный класс отказа.

Лимит не ошибка, а расписание: площадка называет срок, движок обязан его
услышать и отложить ровно на него, а не гадать и не долбиться повторно
"""

from __future__ import annotations

import time

import pytest

from autopost import config, runner
from autopost.net import Reply
from autopost.platforms.base import Permanent, RateLimited, Temporary
from autopost.platforms.instagram import InstagramAdapter
from autopost.platforms.telegram import TelegramAdapter
from autopost.platforms.vk import VkAdapter


def test_telegram_429_carries_retry_after(fake_http, item_factory):
    http = fake_http(
        lambda method, url, kwargs: Reply(429, {"ok": False, "description": "Too Many Requests", "parameters": {"retry_after": 17}})
    )
    item = item_factory(kind="text", text="слишком часто")
    with pytest.raises(RateLimited) as caught:
        TelegramAdapter(config.telegram(), http).publish(item)
    assert caught.value.retry_after == 17


def test_instagram_quota_code_is_rate_limited(fake_http, item_factory):
    http = fake_http(
        lambda method, url, kwargs: Reply(200, {"error": {"code": 4, "message": "Application request limit reached"}})
    )
    item = item_factory(platform="instagram", kind="photo", media=["https://kartinki.example/a.jpg"])
    with pytest.raises(RateLimited) as caught:
        InstagramAdapter(config.instagram(), http, sleep=lambda _: None).publish(item)
    assert caught.value.retry_after > 0


def test_vk_flood_code_is_rate_limited(fake_http, item_factory):
    http = fake_http(
        lambda method, url, kwargs: Reply(200, {"error": {"error_code": 9, "error_msg": "Flood control"}})
    )
    item = item_factory(platform="vk", kind="text", text="слишком часто")
    with pytest.raises(RateLimited):
        VkAdapter(config.vk(), http).publish(item)


def test_runner_postpones_exactly_by_requested_delay(queue, fake_http, monkeypatch):
    """Главное в лимите: движок ждёт СТОЛЬКО, СКОЛЬКО СКАЗАЛИ"""

    class Limited:
        name = "telegram"

        def publish(self, item):
            raise RateLimited("подожди", retry_after=120)

    monkeypatch.setattr(runner, "build_adapter", lambda name, http: Limited())
    item_id, _ = queue.add("telegram", "text", "упрёмся в лимит", [], 0.0)

    before = time.time()
    outcomes = runner.run_once(queue, fake_http())

    assert [o.status for o in outcomes] == ["retry"]
    item = queue.get(item_id)
    assert item.status == "retry"
    assert 110 <= item.publish_at - before <= 130, "отложено не на названный площадкой срок"
    assert queue.due(now=before) == [], "строка снова стала готовой раньше времени"


def test_runner_marks_failed_on_permanent(queue, fake_http, monkeypatch):
    class Broken:
        name = "telegram"

        def publish(self, item):
            raise Permanent("токен отозван")

    monkeypatch.setattr(runner, "build_adapter", lambda name, http: Broken())
    item_id, _ = queue.add("telegram", "text", "сломано по сути", [], 0.0)
    runner.run_once(queue, fake_http())
    assert queue.get(item_id).status == "failed"


def test_runner_gives_up_after_max_attempts(queue, fake_http, monkeypatch):
    class Flaky:
        name = "telegram"

        def publish(self, item):
            raise Temporary("моргнула сеть")

    monkeypatch.setattr(runner, "build_adapter", lambda name, http: Flaky())
    item_id, _ = queue.add("telegram", "text", "моргает и моргает", [], 0.0)

    for _ in range(runner.MAX_ATTEMPTS + 1):
        queue.conn.execute("UPDATE posts SET publish_at = 0 WHERE id = ?", (item_id,))
        runner.run_once(queue, fake_http())

    item = queue.get(item_id)
    assert item.status == "failed"
    assert "попытки кончились" in item.last_error


def test_unknown_platform_fails_loudly(queue, fake_http):
    queue.add("odnoklassniki", "text", "такой площадки в движке нет", [], 0.0)
    outcomes = runner.run_once(queue, fake_http())
    assert outcomes[0].status == "failed"
    assert "неизвестна" in outcomes[0].detail
