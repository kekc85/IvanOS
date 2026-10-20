"""Адаптер VK на подменённом транспорте: ни одного живого соединения.

Живой публикации в VK в этом круге не было (нет выданного сообщества и токена),
поэтому набор кроет ровно то, что можно доказать без живого доступа: форму
запроса, знак минус у сообщества, трёхходовую загрузку фото и разбор ошибок,
которые VK присылает телом ответа с кодом 200
"""

from __future__ import annotations

import pytest

from autopost import config
from autopost.net import Reply
from autopost.platforms.base import Permanent, RateLimited, Temporary
from autopost.platforms.vk import VkAdapter


def adapter(http):
    return VkAdapter(config.vk(), http)


def test_wall_post_goes_from_group_with_minus_owner(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: Reply(200, {"response": {"post_id": 55}}))
    item = item_factory(platform="vk", kind="text", text="запись на стене")

    result = adapter(http).publish(item)

    payload = http.sent("wall.post")[0]
    assert payload["owner_id"] == "-222", "сообщество адресуется отрицательным числом"
    assert payload["from_group"] == "1", "запись обязана выйти от имени сообщества"
    assert payload["message"] == "запись на стене"
    assert result.remote_id == "55"
    assert result.url.endswith("wall-222_55")


def test_empty_post_is_refused_before_network(fake_http, item_factory):
    """С августа 2025 пустая запись у площадки запрещена, ловим это у себя"""
    http = fake_http()
    item = item_factory(platform="vk", kind="text", text="", media=[])
    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "пустую запись" in str(caught.value)
    assert http.calls == []


def test_photo_goes_three_steps_and_becomes_attachment(fake_http, item_factory, tmp_path):
    picture = tmp_path / "kartinka.jpg"
    picture.write_bytes(b"\xff\xd8\xff\xe0 test")

    def handler(method, url, kwargs):
        if "getWallUploadServer" in url:
            return Reply(200, {"response": {"upload_url": "https://zagruzka.example/upload"}})
        if "zagruzka.example" in url:
            return Reply(200, {"server": 1, "photo": "[]", "hash": "hh"})
        if "saveWallPhoto" in url:
            return Reply(200, {"response": [{"id": 900, "owner_id": -222}]})
        return Reply(200, {"response": {"post_id": 56}})

    http = fake_http(handler)
    item = item_factory(platform="vk", kind="photo", text="с картинкой", media=[str(picture)])

    adapter(http).publish(item)

    urls = http.urls()
    assert any("getWallUploadServer" in u for u in urls)
    assert any("zagruzka.example" in u for u in urls)
    assert any("saveWallPhoto" in u for u in urls)
    assert http.sent("wall.post")[0]["attachments"] == "photo-222_900"


def test_missing_file_is_named_plainly(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: Reply(200, {"response": {"upload_url": "https://zagruzka.example/u"}}))
    item = item_factory(platform="vk", kind="photo", text="есть текст", media=["/net/takogo/faila.jpg"])
    with pytest.raises(Permanent) as caught:
        adapter(http).publish(item)
    assert "нет на диске" in str(caught.value)


def test_api_version_and_token_go_with_every_call(fake_http, item_factory):
    http = fake_http(lambda method, url, kwargs: Reply(200, {"response": {"post_id": 1}}))
    item = item_factory(platform="vk", kind="text", text="проверка полей")
    adapter(http).publish(item)
    payload = http.sent("wall.post")[0]
    assert payload["v"] == "5.199"
    assert payload["access_token"] == "TESTVKTOKEN"


def test_fatal_code_is_permanent(fake_http, item_factory):
    http = fake_http(
        lambda method, url, kwargs: Reply(200, {"error": {"error_code": 5, "error_msg": "User authorization failed"}})
    )
    item = item_factory(platform="vk", kind="text", text="токен протух")
    with pytest.raises(Permanent):
        adapter(http).publish(item)


def test_unknown_code_is_temporary(fake_http, item_factory):
    http = fake_http(
        lambda method, url, kwargs: Reply(200, {"error": {"error_code": 10, "error_msg": "Internal server error"}})
    )
    item = item_factory(platform="vk", kind="text", text="моргнуло")
    with pytest.raises(Temporary):
        adapter(http).publish(item)


def test_doctor_names_missing_variables(fake_http, monkeypatch):
    monkeypatch.delenv("VK_ACCESS_TOKEN", raising=False)
    diagnosis = adapter(fake_http()).check()
    assert diagnosis.verdict == "not_configured"
    assert "VK_ACCESS_TOKEN" in diagnosis.detail


def test_doctor_sees_live_group(fake_http):
    http = fake_http(lambda method, url, kwargs: Reply(200, {"response": {"groups": [{"name": "Моё сообщество"}]}}))
    diagnosis = adapter(http).check()
    assert diagnosis.verdict == "ok"
    assert "Моё сообщество" in diagnosis.detail
