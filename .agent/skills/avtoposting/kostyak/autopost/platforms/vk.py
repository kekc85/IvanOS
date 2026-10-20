"""Адаптер VK: запись на стену сообщества.

Что знает про площадку:
  - wall.post c owner_id сообщества, взятым со ЗНАКОМ МИНУС, и from_group=1,
    чтобы запись вышла от имени сообщества, а не от имени человека
  - пустая запись запрещена: обязателен текст либо вложение
  - картинка попадает на стену в три хода: photos.getWallUploadServer даёт
    одноразовый адрес загрузки, туда уходит файл, ответ передаётся в
    photos.saveWallPhoto, и уже сохранённое фото цепляется вложением
  - ошибки приезжают телом ответа с кодом 200, поэтому судим по полю error,
    а не по коду HTTP
"""

from __future__ import annotations

from pathlib import Path

from ..net import NetworkDown
from .base import Adapter, Diagnosis, Permanent, PublishResult, RateLimited, Temporary

RATE_CODES = {6: 3.0, 9: 900.0, 29: 3600.0}
FATAL_CODES = {5, 7, 15, 27, 28, 200, 214}


class VkAdapter(Adapter):
    name = "vk"

    def __init__(self, cfg, http):
        self.cfg = cfg
        self.http = http

    # ── служебное ────────────────────────────────────────────────────────
    def _call(self, method: str, params: dict) -> dict:
        payload = dict(params)
        payload.setdefault("access_token", self.cfg.token)
        payload.setdefault("v", self.cfg.api_version)
        url = "%s/method/%s" % (self.cfg.api_base, method)
        try:
            reply = self.http.post(url, data=payload)
        except NetworkDown as exc:
            raise Temporary("сеть до VK не дошла: %s" % exc) from exc
        body = reply.body if isinstance(reply.body, dict) else {}
        error = body.get("error")
        if error:
            code = int(error.get("error_code") or 0)
            message = error.get("error_msg", "")
            if code in RATE_CODES:
                raise RateLimited("VK просит подождать: %s" % message, retry_after=RATE_CODES[code])
            if code in FATAL_CODES:
                raise Permanent("VK отказал (код %s): %s" % (code, message))
            raise Temporary("VK ответил ошибкой (код %s): %s" % (code, message))
        if not reply.ok:
            raise Temporary("VK ответил %s" % reply.status)
        return body.get("response", body)

    def _owner_id(self) -> str:
        """Сообщество адресуется отрицательным числом. Ученик пишет номер как
        видит, минус ставим сами: это самая частая ошибка первого запуска"""
        raw = str(self.cfg.group_id).strip().lstrip("-")
        return "-%s" % raw

    # ── диагноз ──────────────────────────────────────────────────────────
    def check(self) -> Diagnosis:
        if not self.cfg.ready:
            missing = [
                key
                for key, value in (("VK_ACCESS_TOKEN", self.cfg.token), ("VK_GROUP_ID", self.cfg.group_id))
                if not value
            ]
            return Diagnosis(
                self.name,
                "not_configured",
                "нет переменных: %s" % ", ".join(missing),
                "шаг 5 распаковки: заведи отдельное приложение, выпусти токен с правом"
                " публикации в своём сообществе и возьми номер сообщества из его адреса",
            )
        try:
            groups = self._call("groups.getById", {"group_id": str(self.cfg.group_id).lstrip("-")})
        except (Permanent, Temporary, RateLimited) as exc:
            return Diagnosis(
                self.name, "broken", str(exc), "проверь, что токен выпущен под тем же сообществом и не истёк"
            )
        first = _first_group(groups)
        detail = "сообщество «%s» (%s)" % (first.get("name", "?"), self._owner_id())
        return Diagnosis(self.name, "ok", detail, "", {"group": first.get("name", "")})

    # ── публикация ───────────────────────────────────────────────────────
    def publish(self, item) -> PublishResult:
        media = list(item.media or [])
        if not item.text and not media:
            raise Permanent("VK не принимает пустую запись: нужен текст либо вложение")

        attachments = [self._upload_photo(path) for path in media if not _is_url(path)]
        attachments += [path for path in media if _is_url(path) and path.startswith("photo")]

        params = {"owner_id": self._owner_id(), "from_group": "1", "message": item.text}
        if attachments:
            params["attachments"] = ",".join(attachments)
        response = self._call("wall.post", params)
        post_id = str(response.get("post_id", "")) if isinstance(response, dict) else ""
        url = "https://vk.com/wall%s_%s" % (self._owner_id(), post_id) if post_id else ""
        return PublishResult(remote_id=post_id, url=url)

    def _upload_photo(self, path: str) -> str:
        server = self._call("photos.getWallUploadServer", {"group_id": str(self.cfg.group_id).lstrip("-")})
        upload_url = server.get("upload_url") if isinstance(server, dict) else ""
        if not upload_url:
            raise Temporary("VK не отдал адрес загрузки фото")
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise Permanent("файла нет на диске: %s" % path)
        try:
            with file_path.open("rb") as handle:
                reply = self.http.post(upload_url, files={"photo": (file_path.name, handle.read())})
        except NetworkDown as exc:
            raise Temporary("загрузка фото во VK не дошла: %s" % exc) from exc
        uploaded = reply.body if isinstance(reply.body, dict) else {}
        saved = self._call(
            "photos.saveWallPhoto",
            {
                "group_id": str(self.cfg.group_id).lstrip("-"),
                "photo": uploaded.get("photo", ""),
                "server": uploaded.get("server", ""),
                "hash": uploaded.get("hash", ""),
            },
        )
        first = saved[0] if isinstance(saved, list) and saved else saved
        if not isinstance(first, dict) or "id" not in first:
            raise Temporary("VK не сохранил фото на стене")
        return "photo%s_%s" % (first.get("owner_id"), first.get("id"))


def _is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://")) or value.startswith("photo")


def _first_group(response) -> dict:
    if isinstance(response, dict):
        groups = response.get("groups")
        if isinstance(groups, list) and groups:
            return groups[0]
        return response
    if isinstance(response, list) and response:
        return response[0]
    return {}
