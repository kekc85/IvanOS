"""Реестр адаптеров. Добавить площадку = добавить файл и строку сюда"""

from __future__ import annotations

from .. import config
from .base import Adapter, Diagnosis, Permanent, PublishResult, RateLimited, Temporary
from .instagram import InstagramAdapter
from .telegram import TelegramAdapter
from .vk import VkAdapter

NAMES = ("instagram", "telegram", "vk")


def build(name: str, http):
    name = name.lower().strip()
    if name == "telegram":
        return TelegramAdapter(config.telegram(), http)
    if name == "instagram":
        return InstagramAdapter(config.instagram(), http)
    if name == "vk":
        return VkAdapter(config.vk(), http)
    raise ValueError(
        "площадка «%s» движку неизвестна. Есть: %s" % (name, ", ".join(NAMES))
    )


def build_all(http) -> list:
    return [build(name, http) for name in NAMES]


__all__ = [
    "Adapter",
    "Diagnosis",
    "InstagramAdapter",
    "NAMES",
    "Permanent",
    "PublishResult",
    "RateLimited",
    "TelegramAdapter",
    "Temporary",
    "VkAdapter",
    "build",
    "build_all",
]
