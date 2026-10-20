"""Контракт адаптера площадки. Один на все площадки, без исключений.

Адаптер обязан уметь ровно три вещи:
  name     как его зовут в очереди и в докторе
  check()  диагноз: что настроено, что отвечает, что делать дальше
  publish()опубликовать единицу очереди и вернуть след публикации

Ошибки типизованы, потому что движок реагирует на них по-разному:
  RateLimited  площадка сказала «подожди столько-то» - откладываем ровно на это
  Temporary    моргнула сеть или сервис - пробуем позже
  Permanent    неверный токен, неподходящее медиа, нет прав - руками чинить
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PublishError(Exception):
    pass


class RateLimited(PublishError):
    def __init__(self, message: str, retry_after: float = 60.0):
        super().__init__(message)
        self.retry_after = float(retry_after)


class Temporary(PublishError):
    pass


class Permanent(PublishError):
    pass


@dataclass
class PublishResult:
    remote_id: str = ""
    url: str = ""


@dataclass
class Diagnosis:
    """Строка доктора по одной площадке. verdict: ok | not_configured | broken"""

    platform: str
    verdict: str
    detail: str = ""
    next_step: str = ""
    facts: dict = field(default_factory=dict)

    MARK = {"ok": "работает", "not_configured": "не настроено", "broken": "не отвечает"}

    def line(self) -> str:
        return "%-9s | %-13s | %s" % (self.platform, self.MARK.get(self.verdict, self.verdict), self.detail)


class Adapter:
    name = "base"

    def check(self) -> Diagnosis:  # pragma: no cover - переопределяют потомки
        raise NotImplementedError

    def publish(self, item) -> PublishResult:  # pragma: no cover
        raise NotImplementedError
