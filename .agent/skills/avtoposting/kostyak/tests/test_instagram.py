"""Адаптер Instagram на подменённом транспорте: ни одного живого соединения.

Проверяется главное, на чём спотыкается первый запуск: двухшаговость,
ожидание готовности контейнера, карусель детьми и понятный отказ, когда
медиа лежит не в вебе
"""

from __future__ import annotations

import pytest

from autopost import config
from autopost.net import Reply
from autopost.platforms.base import Permanent, Temporary
from autopost.platforms.instagram import InstagramAdapter

KARTINKA = "https://kartinki.example/a.jpg"


def adapter(http, sleep=None):
    return InstagramAdapter(config.instagram(), http, sleep=sleep or (lambda _: None))


def scripted(container_status="FINISHED"):
    """Сценарий обычной публикации: контейнер, статус, публикация, постоянная ссылка"""
    state = {"containers": 0}

    def handler(method, url, kwargs):
        if url.endswith("/media") and method == "POST":
            state["containers"] += 1
            return Reply(200, {"id": "cont%d" % state["containers"]})
        if url.endswith("/media_publish"):
            return Reply(200, {"id": "media777"})
        if "cont" in url and method == "GET":
            return Reply(200, {"status_code": container_status})
        if url.endswith("media777"):
            return Reply(200, {"permalink": "https://kartinki.example/p/XYZ/"})
        return Reply(200, {})

    return handler


def test_photo_is_published_in_two_steps(fake_http, item_factory):
    http = fake_http(scripted())
    item = item_factory(platform="instagram", kind="photo", text="подпись", media=[KARTINKA])

    result = adapter(http).publish(item)

    urls = http.urls()
    assert any(u.endswith("/media") for u in urls), "не создан контейнер"
    assert any(u.endswith("/media_publish") for u in urls), "контейнер не опубликован"
    assert urls.index([u for u in urls if u.endswith("/media")][0]) < urls.index(
        [u for u in urls if u.endswith("/media_publish")][0]
    ), "публикация ушла раньше контейнера"
    assert result.remote_id == "media777"
    assert result.url.endswith("/p/XYZ/")


def test_publish_carries_creation_id_of_container(fake_http, item_factory):
    http = fake_http(scripted())
    item = item_factory(platform="instagram", kind="photo", media=[KARTINKA])
    adapter(http).publish(item)
    assert http.sent("media_publish")[0]["creation_id"] == "cont1"


def test_carousel_makes_child_container_per_picture(fake_http, item_factory):
    http = fake_http(scripted())
    media = ["https://kartinki.example/%d.jpg" % n for n in range(3)]
    item = item_factory(platform="instagram", kind="carousel", text="карусель", media=media)

    adapter(http).publish(item)

    payloads = http.sent("/media")
    children = [p for p in payloads if p.get("is_carousel_item") == "true"]
    parent = [p for p in payloads if p.get("media_type") == "CAROUSEL"]
    assert len(children) == 3
    assert len(parent) == 1
    assert parent[0]["children"] == "cont1,cont2,cont3"


def test_carousel_over_ten_is_refused(fake_http, item_factory):
    http = fake_http(scripted())
    media = ["https://kartinki.example/%d.jpg" % n for n in range(11)]
    item = item_factory(platform="instagram", kind="carousel", media=media)
    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "не больше 10" in str(caught.value)


def test_reels_goes_as_video_container(fake_http, item_factory):
    http = fake_http(scripted())
    item = item_factory(platform="instagram", kind="reels", media=["https://kartinki.example/v.mp4"])
    adapter(http).publish(item)
    payload = http.sent("/media")[0]
    assert payload["media_type"] == "REELS"
    assert payload["video_url"].endswith(".mp4")


def test_waits_until_container_is_ready(fake_http, item_factory):
    """Первые ответы «ещё готовлю», публикация уходит только после готовности"""
    answers = ["IN_PROGRESS", "IN_PROGRESS", "FINISHED"]
    seen = {"n": 0}

    def handler(method, url, kwargs):
        if url.endswith("/media") and method == "POST":
            return Reply(200, {"id": "cont1"})
        if url.endswith("cont1") and method == "GET":
            status = answers[min(seen["n"], len(answers) - 1)]
            seen["n"] += 1
            return Reply(200, {"status_code": status})
        if url.endswith("/media_publish"):
            assert seen["n"] == 3, "публикация ушла до готовности контейнера"
            return Reply(200, {"id": "media9"})
        return Reply(200, {"permalink": ""})

    item = item_factory(platform="instagram", kind="photo", media=[KARTINKA])
    result = adapter(fake_http(handler)).publish(item)
    assert result.remote_id == "media9"


def test_broken_container_gives_plain_reason(fake_http, item_factory):
    def handler(method, url, kwargs):
        if url.endswith("/media") and method == "POST":
            return Reply(200, {"id": "cont1"})
        return Reply(200, {"status_code": "ERROR", "status": "формат не поддержан"})

    item = item_factory(platform="instagram", kind="photo", media=[KARTINKA])
    with pytest.raises(Permanent) as caught:
        adapter(fake_http(handler)).publish(item)
    assert "не смог обработать медиа" in str(caught.value)


def test_local_file_is_refused_with_instruction(fake_http, item_factory):
    """Площадка качает файл сама, значит локальный путь не годится физически"""
    item = item_factory(platform="instagram", kind="photo", media=["~/Desktop/kartinka.jpg"])
    with pytest.raises(Permanent) as caught:
        adapter(fake_http(scripted())).publish(item)
    text = str(caught.value)
    assert "лежит не в вебе" in text
    assert "media put" in text


def test_dead_public_link_is_refused_before_publishing(fake_http, item_factory):
    http = fake_http(scripted(), head=(False, 404, ""))
    item = item_factory(platform="instagram", kind="photo", media=[KARTINKA])
    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "не отвечает" in str(caught.value)
    assert not any(u.endswith("/media_publish") for u in http.urls())


def test_html_instead_of_picture_is_refused(fake_http, item_factory):
    http = fake_http(scripted(), head=(True, 200, "text/html"))
    item = item_factory(platform="instagram", kind="photo", media=[KARTINKA])
    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "не медиа" in str(caught.value)


def test_post_without_media_is_refused(fake_http, item_factory):
    item = item_factory(platform="instagram", kind="photo", text="только текст", media=[])
    with pytest.raises(Permanent) as caught:
        adapter(fake_http()).publish(item)
    assert "без медиа" in str(caught.value)


def test_doctor_reads_daily_quota(fake_http):
    def handler(method, url, kwargs):
        if url.endswith("/me"):
            return Reply(200, {"id": "111", "username": "moy_akkaunt", "account_type": "BUSINESS"})
        if "content_publishing_limit" in url:
            return Reply(200, {"data": [{"quota_usage": 3, "config": {"quota_total": 100}}]})
        return Reply(200, {})

    diagnosis = adapter(fake_http(handler)).check()
    assert diagnosis.verdict == "ok"
    assert "3 из 100" in diagnosis.detail


def test_doctor_names_missing_scope(fake_http):
    def handler(method, url, kwargs):
        if url.endswith("/me"):
            return Reply(200, {"id": "111", "username": "moy_akkaunt", "account_type": "MEDIA_CREATOR"})
        return Reply(200, {"error": {"code": 10, "message": "Application does not have permission"}})

    diagnosis = adapter(fake_http(handler)).check()
    assert diagnosis.verdict == "broken"
    assert "instagram_business_content_publish" in diagnosis.next_step
