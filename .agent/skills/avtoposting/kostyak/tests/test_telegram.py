"""Адаптер Telegram на подменённом транспорте: ни одного живого соединения"""

from __future__ import annotations

import json

import pytest

from autopost import config
from autopost.net import Reply
from autopost.platforms.base import Permanent
from autopost.platforms.telegram import TelegramAdapter


def ok(result):
    return Reply(200, {"ok": True, "result": result})


def adapter(http):
    return TelegramAdapter(config.telegram(), http)


def test_text_post_goes_as_send_message(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: ok({"message_id": 7, "chat": {"username": "testkanal"}}))
    item = item_factory(kind="text", text="первый пост движка")

    result = adapter(http).publish(item)

    assert "sendMessage" in http.urls()[0]
    assert http.sent("sendMessage")[0]["text"] == "первый пост движка"
    assert result.remote_id == "7"
    assert result.url.endswith("/testkanal/7")


def test_single_photo_goes_as_send_photo(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: ok({"message_id": 8, "chat": {"username": "testkanal"}}))
    item = item_factory(kind="photo", text="подпись", media=["https://kartinki.example/a.jpg"])

    adapter(http).publish(item)

    payload = http.sent("sendPhoto")[0]
    assert payload["photo"] == "https://kartinki.example/a.jpg"
    assert payload["caption"] == "подпись"


def test_album_goes_one_request_and_caption_only_on_first(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: ok([{"message_id": 9, "chat": {"username": "testkanal"}}]))
    media = ["https://kartinki.example/%d.jpg" % n for n in range(3)]
    item = item_factory(kind="album", text="альбом", media=media)

    adapter(http).publish(item)

    assert len([u for u in http.urls() if "sendMediaGroup" in u]) == 1
    group = json.loads(http.sent("sendMediaGroup")[0]["media"])
    assert len(group) == 3
    assert group[0]["caption"] == "альбом"
    assert "caption" not in group[1]


def test_album_over_ten_is_refused_with_plain_reason(fake_http, item_factory):
    http = fake_http()
    item = item_factory(kind="album", media=["https://kartinki.example/%d.jpg" % n for n in range(11)])

    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "не больше 10" in str(caught.value)


def test_video_goes_as_send_video(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: ok({"message_id": 10, "chat": {"username": "testkanal"}}))
    item = item_factory(kind="video", text="ролик", media=["https://kartinki.example/v.mp4"])

    adapter(http).publish(item)

    assert http.sent("sendVideo")[0]["video"].endswith(".mp4")


def test_private_channel_gets_no_invented_link(fake_http, item_factory):
    """У канала без адреса публичной ссылки не существует, и выдумывать её нельзя"""
    http = fake_http(lambda method, url, kwargs: ok({"message_id": 11, "chat": {"id": -100123}}))
    item = item_factory(kind="text", text="в закрытый канал")

    import os

    os.environ["TELEGRAM_CHAT_ID"] = "-100123"
    result = TelegramAdapter(config.telegram(), http).publish(item)
    assert result.url == ""


def test_doctor_line_says_what_is_missing(fake_http, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    diagnosis = adapter(fake_http()).check()
    assert diagnosis.verdict == "not_configured"
    assert "TELEGRAM_BOT_TOKEN" in diagnosis.detail
    assert diagnosis.next_step


def test_doctor_sees_live_bot(fake_http):
    http = fake_http(lambda method, url, kwargs: ok({"id": 1, "username": "moy_bot"}))
    diagnosis = adapter(http).check()
    assert diagnosis.verdict == "ok"
    assert "moy_bot" in diagnosis.detail
