"""Идемпотентность очереди: повтор не публикует дважды.

Два замка проверяются по отдельности, потому что ломаются они по-разному:
вход (одна и та же публикация не создаёт вторую строку) и выдача (строку
нельзя забрать дважды, даже двумя параллельными копиями движка)
"""

from __future__ import annotations

import time

import pytest

from autopost import runner, store
from autopost.net import Reply
from autopost.platforms.base import PublishResult


class CountingAdapter:
    """Считает, сколько раз его реально попросили опубликовать"""

    name = "telegram"

    def __init__(self):
        self.calls = 0

    def publish(self, item):
        self.calls += 1
        return PublishResult(remote_id=str(self.calls), url="")


@pytest.fixture
def counting(monkeypatch):
    adapter = CountingAdapter()
    monkeypatch.setattr(runner, "build_adapter", lambda name, http: adapter)
    return adapter


def test_idempotent_add_same_post_twice_creates_one_row(queue):
    when = time.time()
    first_id, first_created = queue.add("telegram", "text", "один и тот же пост", [], when)
    second_id, second_created = queue.add("telegram", "text", "один и тот же пост", [], when)

    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert len(queue.all()) == 1


def test_idempotent_add_different_text_creates_two_rows(queue):
    when = time.time()
    queue.add("telegram", "text", "первый", [], when)
    queue.add("telegram", "text", "второй", [], when)
    assert len(queue.all()) == 2


def test_idempotent_explicit_key_wins_over_content(queue):
    """Свой ключ важнее содержимого: два разных текста под одним ключом - одна публикация"""
    first_id, _ = queue.add("telegram", "text", "текст А", [], time.time(), idem_key="релиз-1")
    second_id, created = queue.add("telegram", "text", "текст Б", [], time.time(), idem_key="релиз-1")
    assert created is False
    assert first_id == second_id


def test_idempotent_run_twice_publishes_once(queue, fake_http, counting):
    queue.add("telegram", "text", "публикуем ровно один раз", [], 0.0)
    http = fake_http()

    first = runner.run_once(queue, http)
    second = runner.run_once(queue, http)

    assert [o.status for o in first] == ["published"]
    assert second == []
    assert counting.calls == 1


def test_idempotent_claim_taken_only_once(queue):
    item_id, _ = queue.add("telegram", "text", "гонка двух копий движка", [], 0.0)
    assert queue.claim(item_id) is True
    assert queue.claim(item_id) is False


def test_idempotent_published_row_is_not_due_again(queue):
    item_id, _ = queue.add("telegram", "text", "уже ушло", [], 0.0)
    queue.claim(item_id)
    queue.mark_published(item_id, "42", "")
    assert queue.due(now=time.time()) == []


def test_retry_returns_failed_row_to_queue(queue):
    item_id, _ = queue.add("telegram", "text", "упало", [], 0.0)
    queue.claim(item_id)
    queue.mark_failed(item_id, "токен протух")
    assert queue.due(now=time.time()) == []

    assert queue.revive() == 1
    assert [i.id for i in queue.due(now=time.time())] == [item_id]


def test_scheduled_post_waits_for_its_time(queue):
    later = time.time() + 3600
    queue.add("telegram", "text", "выйдет через час", [], later)
    assert queue.due(now=time.time()) == []
    assert len(queue.due(now=later + 1)) == 1


def test_human_time_is_readable(queue):
    assert len(store.human_time(time.time())) == 16
