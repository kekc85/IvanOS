"""Общая оснастка тестов.

Главное правило набора: ни один тест не ходит в сеть. Транспорт подменяется
целиком объектом FakeHttp, который отвечает тем, что задал сам тест, и попутно
записывает все вызовы - по ним и проверяется, что адаптер собрал запрос верно
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

KOSTYAK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOSTYAK))
# без этого первый же импорт оставит в костяке каталоги с байткодом,
# а костяк раздаётся ученикам и обязан оставаться чистым
sys.dont_write_bytecode = True

from autopost import config, store  # noqa: E402
from autopost.net import Reply  # noqa: E402


class FakeHttp:
    """Подменённый транспорт. Ни одного настоящего соединения.

    handler(method, url, kwargs) -> Reply. Всё, что не описано тестом, падает
    явной ошибкой: молчаливая заглушка прячет ошибку сборки запроса
    """

    def __init__(self, handler=None, head=(True, 200, "image/jpeg")):
        self.handler = handler or (lambda method, url, kwargs: Reply(200, {"ok": True, "result": {}}))
        self.calls: list[tuple[str, str, dict]] = []
        self.head = head
        self.closed = False

    def request(self, method, url, **kwargs) -> Reply:
        self.calls.append((method.upper(), url, kwargs))
        return self.handler(method.upper(), url, kwargs)

    def get(self, url, params=None) -> Reply:
        return self.request("GET", url, params=params)

    def post(self, url, data=None, files=None, params=None, json_body=None) -> Reply:
        return self.request("POST", url, data=data, files=files, params=params, json_body=json_body)

    def head_ok(self, url):
        self.calls.append(("HEAD", url, {}))
        return self.head

    def close(self):
        self.closed = True

    # ── помощники для проверок ────────────────────────────────────────────
    def sent(self, needle: str) -> list[dict]:
        """Полезная нагрузка всех вызовов, чей адрес содержит подстроку"""
        out = []
        for _, url, kwargs in self.calls:
            if needle in url:
                out.append(kwargs.get("data") or kwargs.get("params") or {})
        return out

    def urls(self) -> list[str]:
        return [url for _, url, _ in self.calls]


@pytest.fixture
def fake_http():
    return FakeHttp


@pytest.fixture
def queue(tmp_path):
    q = store.Queue(tmp_path / "queue.db")
    yield q
    q.close()


@pytest.fixture
def item_factory(queue):
    def make(platform="telegram", kind="text", text="привет", media=None, publish_at=0.0):
        item_id, _ = queue.add(platform=platform, kind=kind, text=text, media=media or [], publish_at=publish_at)
        return queue.get(item_id)

    return make


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Каждый тест живёт в своём доме и со своими адресами.

    Адреса нарочно нейтральные: набор доказывает логику адаптера, а не
    доступность чужого сервера
    """
    monkeypatch.setenv("AUTOPOST_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("TELEGRAM_API_BASE", "https://tg.example")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TESTTOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@testkanal")
    monkeypatch.setenv("IG_API_BASE", "https://ig.example")
    monkeypatch.setenv("IG_API_VERSION", "v23.0")
    monkeypatch.setenv("IG_USER_ID", "111")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "TESTIGTOKEN")
    monkeypatch.setenv("VK_API_BASE", "https://vkontakte.example")
    monkeypatch.setenv("VK_ACCESS_TOKEN", "TESTVKTOKEN")
    monkeypatch.setenv("VK_GROUP_ID", "222")
    monkeypatch.setenv("MEDIA_MODE", "ready")
    yield


def pytest_sessionfinish(session, exitstatus):
    """Костяк раздаётся ученикам, поэтому набор убирает за собой сам.

    Кэш байткода и кэш прогона - рабочий мусор, в раздаваемой папке его быть
    не должно ни после одного прогона, ни после сотого
    """
    for junk in list(KOSTYAK.rglob("__pycache__")) + list(KOSTYAK.rglob(".pytest_cache")):
        shutil.rmtree(junk, ignore_errors=True)
