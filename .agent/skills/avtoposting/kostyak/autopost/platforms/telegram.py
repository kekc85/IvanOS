"""Адаптер Telegram. Бот-администратор публикует в канал.

Что знает про площадку:
  - методы sendMessage / sendPhoto / sendMediaGroup / sendVideo
  - альбом до 10 медиа и он считается ОДНИМ сообщением канального лимита
  - около 20 сообщений в минуту в один канал, около 30 в секунду суммарно
  - превышение приходит как HTTP 429 с parameters.retry_after в секундах,
    и это не ошибка, а расписание: столько ждать и повторить
  - облачный адрес API из некоторых сетей закрыт, поэтому база адреса вынесена
    в переменную TELEGRAM_API_BASE и меняется на свой local Bot API server
"""

from __future__ import annotations

import json

from ..net import NetworkDown
from .base import Adapter, Diagnosis, Permanent, PublishResult, RateLimited, Temporary

ALBUM_LIMIT = 10


class TelegramAdapter(Adapter):
    name = "telegram"

    def __init__(self, cfg, http):
        self.cfg = cfg
        self.http = http

    # ── служебное ────────────────────────────────────────────────────────
    def _url(self, method: str) -> str:
        return "%s/bot%s/%s" % (self.cfg.api_base, self.cfg.token, method)

    def _call(self, method: str, payload: dict) -> dict:
        try:
            reply = self.http.post(self._url(method), data=payload)
        except NetworkDown as exc:
            raise Temporary("сеть до Telegram не дошла: %s" % exc) from exc
        body = reply.body if isinstance(reply.body, dict) else {}
        if reply.status == 429:
            wait = float(body.get("parameters", {}).get("retry_after", 30))
            raise RateLimited("Telegram просит подождать %.0f с" % wait, retry_after=wait)
        if reply.status in (401, 403, 400):
            raise Permanent(
                "Telegram отказал (%s): %s" % (reply.status, body.get("description", reply.body))
            )
        if not reply.ok or not body.get("ok"):
            raise Temporary("Telegram ответил %s: %s" % (reply.status, body.get("description", reply.body)))
        return body.get("result", {})

    # ── диагноз ──────────────────────────────────────────────────────────
    def check(self) -> Diagnosis:
        if not self.cfg.ready:
            missing = []
            if not self.cfg.token:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not self.cfg.chat_id:
                missing.append("TELEGRAM_CHAT_ID")
            return Diagnosis(
                self.name,
                "not_configured",
                "нет переменных: %s" % ", ".join(missing),
                "шаг 2 распаковки: получи токен у BotFather и добавь бота админом в свой канал",
            )
        try:
            me = self._call("getMe", {})
        except (Permanent, Temporary, RateLimited) as exc:
            return Diagnosis(
                self.name,
                "broken",
                str(exc),
                "проверь токен; если сеть режет адрес API - подними свой Bot API server и"
                " пропиши его в TELEGRAM_API_BASE",
            )
        detail = "бот @%s, канал %s" % (me.get("username", "?"), self.cfg.chat_id)
        return Diagnosis(self.name, "ok", detail, "", {"bot_id": me.get("id")})

    # ── публикация ───────────────────────────────────────────────────────
    def publish(self, item) -> PublishResult:
        media = list(item.media or [])
        kind = item.kind or ("album" if len(media) > 1 else "photo" if media else "text")

        if kind == "text" or not media:
            result = self._call(
                "sendMessage",
                {"chat_id": self.cfg.chat_id, "text": item.text, "disable_web_page_preview": "true"},
            )
        elif kind == "video":
            result = self._call(
                "sendVideo",
                {"chat_id": self.cfg.chat_id, "video": media[0], "caption": item.text[:1024]},
            )
        elif kind == "album" or len(media) > 1:
            if len(media) > ALBUM_LIMIT:
                raise Permanent(
                    "в альбоме Telegram не больше %d медиа, прислано %d" % (ALBUM_LIMIT, len(media))
                )
            group = []
            for index, url in enumerate(media):
                part = {"type": "video" if _looks_video(url) else "photo", "media": url}
                if index == 0 and item.text:
                    part["caption"] = item.text[:1024]
                group.append(part)
            result = self._call(
                "sendMediaGroup",
                {"chat_id": self.cfg.chat_id, "media": json.dumps(group, ensure_ascii=False)},
            )
            result = result[0] if isinstance(result, list) and result else {}
        else:
            result = self._call(
                "sendPhoto",
                {"chat_id": self.cfg.chat_id, "photo": media[0], "caption": item.text[:1024]},
            )

        message_id = str(result.get("message_id", ""))
        return PublishResult(remote_id=message_id, url=_permalink(self.cfg.chat_id, result, message_id))


def _looks_video(url: str) -> bool:
    return url.lower().rsplit("?", 1)[0].endswith((".mp4", ".mov", ".m4v"))


def _permalink(chat_id: str, result: dict, message_id: str) -> str:
    """Публичная ссылка на сообщение собирается только для канала с адресом.

    У приватного канала адреса нет, и выдумывать его нельзя: движок вернёт
    пустую ссылку, а не правдоподобную выдумку
    """
    chat = result.get("chat", {}) if isinstance(result, dict) else {}
    username = chat.get("username") or (chat_id[1:] if chat_id.startswith("@") else "")
    if username and message_id:
        return "https://t.me/%s/%s" % (username, message_id)
    return ""
