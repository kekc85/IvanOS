"""Сетевой слой. Один вход в сеть на весь движок.

Зачем отдельным слоем: площадки разные, а условия сети одни. Прокси, таймаут,
ретраи на разрыв связи, единая форма ответа. Плюс тесты подменяют ровно этот
объект и не ходят в сеть вообще
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any


class NetworkDown(Exception):
    """Связи нет: адрес не резолвится, соединение обрывается, таймаут"""


@dataclass
class Reply:
    status: int
    body: Any
    headers: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class Http:
    """Тонкая обёртка над httpx с прокси и ретраями.

    Ретраим только то, что имеет смысл повторить: обрыв связи и 5xx.
    429 НЕ ретраим здесь - у площадок разный способ сказать «подожди столько-то»,
    это знание адаптера, а не транспорта
    """

    def __init__(self, proxy: str = "", timeout: float = 30.0, retries: int = 2, sleep=time.sleep):
        self.proxy = proxy or ""
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self._sleep = sleep
        self._client = None
        self._client_v4 = None
        self.forced_v4 = False

    def _make_client(self, ipv4_only: bool):
        import httpx

        kwargs: dict[str, Any] = {"timeout": self.timeout, "follow_redirects": True}
        if ipv4_only:
            # привязка к любому IPv4-адресу заставляет брать только семейство v4
            kwargs["transport"] = httpx.HTTPTransport(local_address="0.0.0.0", retries=0)
        if self.proxy:
            # имя параметра разъехалось между версиями httpx: сначала пробуем новое
            try:
                return httpx.Client(proxy=self.proxy, **kwargs)
            except TypeError:
                return httpx.Client(proxies=self.proxy, **kwargs)
        return httpx.Client(**kwargs)

    def _client_or_new(self):
        if self._client is None:
            self._client = self._make_client(ipv4_only=False)
        return self._client

    def _client_v4_or_new(self):
        if self._client_v4 is None:
            self._client_v4 = self._make_client(ipv4_only=True)
        return self._client_v4

    def close(self) -> None:
        for name in ("_client", "_client_v4"):
            client = getattr(self, name)
            if client is not None:
                try:
                    client.close()
                finally:
                    setattr(self, name, None)

    def request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
        json_body: dict | None = None,
    ) -> Reply:
        import httpx

        client = self._client_v4_or_new() if self.forced_v4 else self._client_or_new()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = client.request(
                    method.upper(), url, params=params, data=data, files=files, json=json_body
                )
            except httpx.ConnectError as exc:
                # Отдельная ветка на «Network is unreachable»: у сервера в DNS есть
                # адрес IPv6, маршрута до него нет, и клиент честно падает на первом
                # же семействе. curl в той же сети проходит, потому что откатывается
                # на IPv4. Без этого отката доктор объявлял живой канал закрытым -
                # ложный диагноз хуже отсутствия диагноза
                if not self.forced_v4:
                    self.forced_v4 = True
                    client = self._client_v4_or_new()
                    continue
                last_error = exc
                if attempt < self.retries:
                    self._sleep(_backoff(attempt))
                    continue
                raise NetworkDown(f"{type(exc).__name__}: {exc}") from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self.retries:
                    self._sleep(_backoff(attempt))
                    continue
                raise NetworkDown(f"{type(exc).__name__}: {exc}") from exc
            if response.status_code >= 500 and attempt < self.retries:
                self._sleep(_backoff(attempt))
                continue
            return Reply(
                status=response.status_code,
                body=_decode(response),
                headers={k.lower(): v for k, v in response.headers.items()},
            )
        raise NetworkDown(str(last_error))

    def get(self, url: str, params: dict | None = None) -> Reply:
        return self.request("GET", url, params=params)

    def post(
        self,
        url: str,
        data: dict | None = None,
        files: dict | None = None,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> Reply:
        return self.request("POST", url, params=params, data=data, files=files, json_body=json_body)

    def head_ok(self, url: str) -> tuple[bool, int, str]:
        """Живой ли публичный адрес медиа. Возвращает (доступен, код, тип содержимого).

        Часть хранилищ на HEAD отвечает 405, но на GET отдаёт файл - тогда
        добираем GET, иначе ложно объявим рабочую ссылку мёртвой
        """
        try:
            reply = self.request("HEAD", url)
            if reply.status == 405:
                reply = self.get(url)
        except NetworkDown as exc:
            return False, 0, str(exc)
        return reply.ok, reply.status, reply.headers.get("content-type", "")


def _backoff(attempt: int) -> float:
    return min(8.0, (2**attempt)) + random.random() * 0.3


def _decode(response) -> Any:
    ctype = response.headers.get("content-type", "")
    if "json" in ctype:
        try:
            return response.json()
        except ValueError:
            return response.text
    try:
        return response.json()
    except Exception:
        return response.text


def build(cfg=None) -> Http:
    from . import config

    cfg = cfg or config.net()
    return Http(proxy=cfg.proxy, timeout=cfg.timeout, retries=cfg.retries)
