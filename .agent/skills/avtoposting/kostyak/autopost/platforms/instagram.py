"""Адаптер Instagram по официальному Graph API.

Публикация тут двухшаговая и это не прихоть: сначала создаётся КОНТЕЙНЕР
(площадка забирает медиа по публичной ссылке и готовит его у себя), и только
потом контейнер публикуется по его creation_id. Между шагами есть пауза: у
видео и рилса контейнер какое-то время в статусе IN_PROGRESS

Что знает про площадку:
  - POST /<IG_ID>/media -> контейнер, POST /<IG_ID>/media_publish -> публикация
  - типы IMAGE, REELS, CAROUSEL (до 10 элементов, каждый своим контейнером)
  - медиа обязано лежать на ПУБЛИЧНОМ адресе в момент публикации: площадка
    качает файл со своей стороны, локальный путь и ссылка за паролем не годятся
  - лимит 100 публикаций за скользящие 24 часа, счётчик читается
    GET /<IG_ID>/content_publishing_limit
  - аккаунт обязан быть профессиональным (бизнес или автор)

Ни одного обращения к неофициальным путям: только Graph API и токен доступа
"""

from __future__ import annotations

import time

from ..net import NetworkDown
from .base import Adapter, Diagnosis, Permanent, PublishResult, RateLimited, Temporary

CAROUSEL_LIMIT = 10
CONTAINER_POLL_TRIES = 20
CONTAINER_POLL_DELAY = 3.0


class InstagramAdapter(Adapter):
    name = "instagram"

    def __init__(self, cfg, http, sleep=time.sleep):
        self.cfg = cfg
        self.http = http
        self._sleep = sleep

    # ── служебное ────────────────────────────────────────────────────────
    def _url(self, path: str) -> str:
        return "%s/%s/%s" % (self.cfg.api_base, self.cfg.api_version, path.lstrip("/"))

    def _call(self, method: str, path: str, params: dict) -> dict:
        payload = dict(params)
        payload["access_token"] = self.cfg.token
        try:
            if method == "GET":
                reply = self.http.get(self._url(path), params=payload)
            else:
                reply = self.http.post(self._url(path), data=payload)
        except NetworkDown as exc:
            raise Temporary("сеть до Graph API не дошла: %s" % exc) from exc

        body = reply.body if isinstance(reply.body, dict) else {}
        error = body.get("error") or {}
        if error:
            code = int(error.get("code") or 0)
            message = error.get("message", "")
            if code in (4, 17, 32, 613):
                raise RateLimited("Instagram упёрся в лимит: %s" % message, retry_after=900)
            if code in (190, 102, 10, 200, 803):
                raise Permanent("Instagram отказал (код %s): %s" % (code, message))
            if code in (1, 2):
                raise Temporary("Instagram временно недоступен (код %s): %s" % (code, message))
            raise Permanent("Instagram: %s" % (message or body))
        if reply.status == 429:
            raise RateLimited("Instagram ответил 429", retry_after=900)
        if not reply.ok:
            raise Temporary("Instagram ответил %s: %s" % (reply.status, reply.body))
        return body

    # ── диагноз ──────────────────────────────────────────────────────────
    def check(self) -> Diagnosis:
        if not self.cfg.ready:
            missing = [
                key
                for key, value in (("IG_USER_ID", self.cfg.user_id), ("IG_ACCESS_TOKEN", self.cfg.token))
                if not value
            ]
            return Diagnosis(
                self.name,
                "not_configured",
                "нет переменных: %s" % ", ".join(missing),
                "шаг 3 распаковки: переведи аккаунт в профессиональный, заведи приложение"
                " в кабинете разработчика и выпусти токен со скоупом публикации",
            )
        try:
            me = self._call("GET", "me", {"fields": "id,username,account_type"})
        except (Permanent, Temporary, RateLimited) as exc:
            return Diagnosis(
                self.name, "broken", str(exc), "перевыпусти токен: он живёт 60 дней и продлевается"
            )

        facts = {"username": me.get("username", ""), "account_type": me.get("account_type", "")}
        detail = "аккаунт @%s (%s)" % (facts["username"] or "?", facts["account_type"] or "?")
        try:
            limit = self._call("GET", "%s/content_publishing_limit" % self.cfg.user_id, {"fields": "quota_usage,config"})
            used = (limit.get("data") or [{}])[0]
            quota = used.get("quota_usage")
            cap = (used.get("config") or {}).get("quota_total", 100)
            if quota is not None:
                detail += ", израсходовано %s из %s публикаций за сутки" % (quota, cap)
                facts["quota_usage"] = quota
        except (Permanent, Temporary, RateLimited) as exc:
            return Diagnosis(
                self.name,
                "broken",
                detail + ", но счётчик публикаций закрыт: %s" % exc,
                "у токена нет скоупа публикации: перевыпусти токен, добавив"
                " instagram_business_content_publish",
            )
        return Diagnosis(self.name, "ok", detail, "", facts)

    # ── публикация ───────────────────────────────────────────────────────
    def publish(self, item) -> PublishResult:
        media = list(item.media or [])
        kind = (item.kind or "").lower()
        if not media:
            raise Permanent("Instagram не принимает пост без медиа: нужна минимум одна картинка")
        self._require_public(media)

        if kind == "carousel" or (kind in ("", "auto") and len(media) > 1):
            creation_id = self._carousel(media, item.text)
        elif kind in ("reels", "video"):
            creation_id = self._container({"media_type": "REELS", "video_url": media[0], "caption": item.text})
        else:
            creation_id = self._container({"image_url": media[0], "caption": item.text})

        self._wait_ready(creation_id)
        published = self._call("POST", "%s/media_publish" % self.cfg.user_id, {"creation_id": creation_id})
        media_id = str(published.get("id", ""))
        permalink = ""
        if media_id:
            try:
                permalink = str(self._call("GET", media_id, {"fields": "permalink"}).get("permalink", ""))
            except (Permanent, Temporary, RateLimited):
                permalink = ""
        return PublishResult(remote_id=media_id, url=permalink)

    # ── кирпичи ──────────────────────────────────────────────────────────
    def _container(self, params: dict) -> str:
        body = self._call("POST", "%s/media" % self.cfg.user_id, params)
        creation_id = str(body.get("id", ""))
        if not creation_id:
            raise Temporary("Instagram не вернул creation_id контейнера")
        return creation_id

    def _carousel(self, media: list[str], caption: str) -> str:
        if len(media) > CAROUSEL_LIMIT:
            raise Permanent(
                "в карусели Instagram не больше %d элементов, прислано %d" % (CAROUSEL_LIMIT, len(media))
            )
        children = []
        for url in media:
            params = {"is_carousel_item": "true"}
            if _looks_video(url):
                params["media_type"] = "VIDEO"
                params["video_url"] = url
            else:
                params["image_url"] = url
            children.append(self._container(params))
        return self._container(
            {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
        )

    def _wait_ready(self, creation_id: str) -> None:
        """Ждём, пока площадка дожуёт медиа. Публикация недожатого контейнера
        падает невнятной ошибкой, поэтому статус читаем явно"""
        for _ in range(CONTAINER_POLL_TRIES):
            body = self._call("GET", creation_id, {"fields": "status_code,status"})
            code = str(body.get("status_code", "")).upper()
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise Permanent(
                    "Instagram не смог обработать медиа: %s" % body.get("status", "без подробностей")
                )
            if code == "EXPIRED":
                raise Permanent("контейнер протух, соберите заново")
            self._sleep(CONTAINER_POLL_DELAY)
        raise Temporary("контейнер так и не дошёл до готовности, попробуем позже")

    def _require_public(self, media: list[str]) -> None:
        """Понятная ошибка вместо загадочной. Площадка качает файл САМА, значит
        локальный путь и ссылка за паролем не годятся физически"""
        for url in media:
            if not url.lower().startswith(("http://", "https://")):
                raise Permanent(
                    "медиа «%s» лежит не в вебе. Instagram качает файл со своей стороны,"
                    " поэтому нужна публичная ссылка. Положи файл в веб командой"
                    " cli.py media put <файл> и подставь полученный адрес" % url[:80]
                )
            ok, status, ctype = self.http.head_ok(url)
            if not ok:
                raise Permanent(
                    "публичный адрес медиа не отвечает (код %s): %s. Instagram скачает файл"
                    " сам, поэтому ссылка обязана открываться без пароля" % (status, url[:100])
                )
            if ctype and not (ctype.startswith("image/") or ctype.startswith("video/")):
                raise Permanent(
                    "по адресу %s лежит не медиа, а %s. Обычно так отвечает страница-обёртка"
                    " вместо прямой ссылки на файл" % (url[:80], ctype)
                )


def _looks_video(url: str) -> bool:
    return url.lower().rsplit("?", 1)[0].endswith((".mp4", ".mov", ".m4v"))
