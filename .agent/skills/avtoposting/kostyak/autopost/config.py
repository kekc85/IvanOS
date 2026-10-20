"""Конфигурация движка: одно место, где читаются переменные окружения.

Правило: секреты живут ТОЛЬКО в .env рядом с костяком либо в переменных
окружения. В коде и в репозитории их нет никогда. Рабочие данные (база очереди,
логи) лежат вне папки движка - в AUTOPOST_HOME, по умолчанию ~/.autopost
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

KOSTYAK_DIR = Path(__file__).resolve().parent.parent


def load_env(dotenv: Path | None = None) -> None:
    """Подтягивает .env, не перетирая уже выставленные переменные окружения.

    Свой мини-парсер вместо python-dotenv: у ученика может не быть библиотеки,
    а формат нам нужен ровно один - KEY=value построчно
    """
    path = dotenv or (KOSTYAK_DIR / ".env")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def home() -> Path:
    """Каталог рабочих данных. Намеренно ВНЕ папки движка: обновление движка
    не должно затирать очередь, а раздача движка не должна тащить чужие данные"""
    value = os.environ.get("AUTOPOST_HOME", "").strip()
    path = Path(value).expanduser() if value else Path.home() / ".autopost"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return home() / "queue.db"


def log_path() -> Path:
    return home() / "autopost.log"


def media_dir() -> Path:
    path = home() / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    chat_id: str
    api_base: str

    @property
    def ready(self) -> bool:
        return bool(self.token and self.chat_id)


@dataclass(frozen=True)
class InstagramConfig:
    user_id: str
    token: str
    api_base: str
    api_version: str

    @property
    def ready(self) -> bool:
        return bool(self.user_id and self.token)


@dataclass(frozen=True)
class VkConfig:
    token: str
    group_id: str
    api_base: str
    api_version: str

    @property
    def ready(self) -> bool:
        return bool(self.token and self.group_id)


@dataclass(frozen=True)
class NetConfig:
    proxy: str
    timeout: float
    retries: int


def telegram() -> TelegramConfig:
    # api_base отдельной переменной: из РФ облачный адрес режется по SNI,
    # лечится своим local Bot API server, и тогда меняется ровно эта строка
    return TelegramConfig(
        token=env("TELEGRAM_BOT_TOKEN"),
        chat_id=env("TELEGRAM_CHAT_ID"),
        api_base=env("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/"),
    )


def instagram() -> InstagramConfig:
    # graph.instagram.com - маршрут Instagram Login (вход по инстаграм-логину,
    # без привязки к странице Facebook). graph.facebook.com - маршрут FB Login
    return InstagramConfig(
        user_id=env("IG_USER_ID"),
        token=env("IG_ACCESS_TOKEN"),
        api_base=env("IG_API_BASE", "https://graph.instagram.com").rstrip("/"),
        api_version=env("IG_API_VERSION", "v23.0"),
    )


def vk() -> VkConfig:
    return VkConfig(
        token=env("VK_ACCESS_TOKEN"),
        group_id=env("VK_GROUP_ID"),
        api_base=env("VK_API_BASE", "https://api.vk.com").rstrip("/"),
        api_version=env("VK_API_VERSION", "5.199"),
    )


def net() -> NetConfig:
    try:
        timeout = float(env("AUTOPOST_TIMEOUT", "30"))
    except ValueError:
        timeout = 30.0
    try:
        retries = int(env("AUTOPOST_RETRIES", "2"))
    except ValueError:
        retries = 2
    return NetConfig(proxy=env("AUTOPOST_PROXY"), timeout=timeout, retries=retries)
