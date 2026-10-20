"""Redirect-сервис клик-трекинга (свой аналог link_was_pressed конструктора воронок).

GET /r/<uuid>:
  - неизвестный uuid → 404
  - target не из allowlist доменов → 404 (анти-open-redirect)
  - User-Agent Telegram-превью-бота → 302 БЕЗ засчитывания клика (иначе превью
    дёрнет ссылку и TECH сработает у всех сразу)
  - реальный юзер → записать клик (дедуп) + положить в очередь клика (бот
    продвинет воронку) → 302 на target

Запуск: uvicorn app.redirect:app  (за nginx+TLS). Слушает только localhost.
"""
import hmac, time as _time
from collections import deque
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse

from .config import DB_PATH, REDIRECT_ALLOW, GC_WEBHOOK_TOKEN
from . import crossdb
from . import suppression
from .db import DB

app = FastAPI()
db = DB(DB_PATH)

# Сигнатуры link-preview ботов. Голый "bot" убран: он ложно ловил реальных
# юзеров/клиентов со строкой "bot" в UA и НЕ засчитывал их клик (воронка не
# двигалась). Telegram-превью = "TelegramBot (like TwitterBot)" - ловится точными.
PREVIEW_UA = ("telegrambot", "twitterbot", "facebookexternalhit", "whatsapp",
              "vkshare", "linkpreview", "crawler", "spider")


def _allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in REDIRECT_ALLOW)


@app.get("/")
def health():
    return PlainTextResponse("ok")


_hook_hits = deque()   # ts запросов вебхука за последнюю минуту (анти-перебор)


@app.post("/hooks/gc-registered")
async def gc_registered(request: Request):
    """Вебхук регистрации платформы курса: честный сигнал registered вместо клик-прокси.

    Технарь настраивает в GC POST-вызов /hooks/gc-registered:
      токен - в заголовке X-GC-Token (или form-поле token), НЕ в query-string
      tg_id - form-поле (если проброшен из бота, числовой) ИЛИ
      username - form-поле (с сайта события: человек вписывает свой @ник в TG,
        сайт tg_id не знает - это НОВЫЙ путь, старый tg_id не убираем, он всё
        ещё нужен для проброса из самого бота)
    Хотя бы одно из двух полей обязано быть. Ставит тег registered (свой +
    соседний инстанс) + гасит pending-дожимы для КОНТАКТОВ СВОЕЙ базы (redirect
    работает в контексте одного инстанса и не пишет в чужие SQLite - это не его
    забота). Общий suppression-реестр метится ВСЕГДА (гасит рассылку во всех 7
    ботах разом), независимо от того, в чьей базе контакт нашёлся.
    Endpoint выключен, пока GC_WEBHOOK_TOKEN пуст.
    """
    if not GC_WEBHOOK_TOKEN:
        return PlainTextResponse("disabled", status_code=404)

    params = {}
    try:
        params = dict(await request.form())
    except Exception:
        pass
    token = request.headers.get("x-gc-token", "") or str(params.get("token", ""))
    if not hmac.compare_digest(token, GC_WEBHOOK_TOKEN):
        return PlainTextResponse("forbidden", status_code=403)
    # rate-limit считаем ТОЛЬКО аутентифицированные запросы (после проверки токена):
    # иначе аноним без токена флудом выедал окно 30/мин и легитимный вебхук платформы курса
    # получал 429 → тег registered не ставился, дожим 'зарегистрируйся' не гас.
    now = _time.time()
    while _hook_hits and now - _hook_hits[0] > 60:
        _hook_hits.popleft()
    if len(_hook_hits) >= 30:
        return PlainTextResponse("too many", status_code=429)
    _hook_hits.append(now)

    raw_tg_id = str(params.get("tg_id", "")).strip()
    raw_username = str(params.get("username", "")).strip()
    if not raw_tg_id and not raw_username:
        return PlainTextResponse("bad request: need tg_id or username", status_code=400)

    matched = 0

    if raw_tg_id:
        try:
            tg_id = int(raw_tg_id)
        except ValueError:
            return PlainTextResponse("bad tg_id", status_code=400)
        if db.has_contact(tg_id):
            db.add_tag(tg_id, "registered")
            db.cancel_all(tg_id)
            db.event(tg_id, "registered", "gc_webhook")
            crossdb.tag_neighbor(tg_id, "registered")
            suppression.add_safe(tg_id, "registered", "gc_webhook")  # гасит рассылки во ВСЕХ 7 ботах
            matched += 1

    if raw_username:
        res = suppression.resolve_and_suppress_by_username(raw_username, "registered", "platform_site")
        if not res.get("ok"):
            return PlainTextResponse("bad username", status_code=400)
        for uid in res["matched_ids"]:
            # дожимы гасим только там, где этот uid - контакт СВОЕЙ базы (redirect
            # инстанса не имеет права писать в чужие SQLite - только в общий реестр,
            # который уже проставлен внутри resolve_and_suppress_by_username выше)
            if db.has_contact(uid):
                db.add_tag(uid, "registered")
                db.cancel_all(uid)
                db.event(uid, "registered", "gc_webhook_username")
                crossdb.tag_neighbor(uid, "registered")
        matched += res["count"]

    if matched == 0:
        return PlainTextResponse("unknown", status_code=404)
    return PlainTextResponse(f"ok matched={matched}")


@app.get("/r/{uuid}")
def redirect(uuid: str, request: Request):
    link = db.redirect(uuid)
    if not link:
        return PlainTextResponse("not found", status_code=404)
    target = link["target_url"]
    if not _allowed(target):
        return PlainTextResponse("blocked", status_code=404)

    ua = request.headers.get("user-agent", "").lower()
    is_preview = any(sig in ua for sig in PREVIEW_UA)

    if not is_preview:
        # реальный клик: дедуп + постановка в очередь продвижения ОДНОЙ транзакцией
        # (атомарно - иначе краш между записями терял клик безвозвратно)
        first = db.record_and_enqueue_click(uuid, link["user_id"], link["funnel_key"], target)
        if first:
            db.event(link["user_id"], "click", f"{link['funnel_key']}/{link['node']}")
    return RedirectResponse(target, status_code=302)
