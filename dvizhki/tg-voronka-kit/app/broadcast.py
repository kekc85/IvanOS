"""Логика рассылок: разбор кнопки, второй фактор (TOTP), отправка с чекпоинтом.

Отправка идёт из бота батчами (job_queue tick) с rate-limit; чекпоинт в
broadcast_recipients - рестарт продолжает, не дублит. Гейт запуска - TOTP.
"""
import json, re, sqlite3, time, uuid as _uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import TOTP_SECRET, REDIRECT_BASE, REDIRECT_ALLOW

# Маркер funnel_key для редиректов рассылки (не пересекается с реальными ключами
# воронок - они кириллица/латиница-код-слова без "__"). redirect.py по этому
# префиксу отличает клик по рассылке от клика по узлу воронки.
BROADCAST_FUNNEL_MARK = "__broadcast__"


def parse_draft(text: str):
    """Текст рассылки → (message_text, buttons_json).
    Строка вида 'Подпись | https://ссылка' в конце трактуется как кнопка."""
    lines = text.rstrip().split("\n")
    buttons = []
    body = text.rstrip()
    if lines and "|" in lines[-1] and "http" in lines[-1]:
        label, url = [x.strip() for x in lines[-1].split("|", 1)]
        if url.startswith("http"):
            buttons.append({"text": label, "url": url})
            body = "\n".join(lines[:-1]).rstrip()
    return body, json.dumps(buttons, ensure_ascii=False)


def build_keyboard(buttons_json: str):
    btns = json.loads(buttons_json or "[]")
    if not btns:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"])] for b in btns])


def verify_totp(code: str, for_time=None) -> bool:
    """Проверка кода второго фактора. Пустой секрет = 2ФА выключен (True).
    for_time только для тестов (детерминизм), в бою None = текущее время."""
    if not TOTP_SECRET:
        return True
    try:
        import pyotp
        return pyotp.TOTP(TOTP_SECRET).verify(str(code).strip(), for_time=for_time, valid_window=1)
    except Exception:
        return False


def totp_enabled() -> bool:
    return bool(TOTP_SECRET)


def has_link(buttons_json: str) -> bool:
    """ТЗ рассылки: у каждого сообщения обязана быть ссылка/кнопка."""
    return bool(json.loads(buttons_json or "[]"))


# <адрес-бота><internal_id>/<msg_id> - приватный канал (internal_id без -100, Telegram
# сам его не показывает в ссылке); <адрес-бота><username>/<msg_id> - публичный канал.
_POST_URL_RE = re.compile(
    r"^https?://t\.me/(?:c/(?P<cid>\d+)|(?P<uname>[A-Za-z0-9_]+))/(?P<mid>\d+)/?$")


def wrap_broadcast_buttons(db, buttons_json: str, user_id: int, bid: int, label: str):
    """Кнопки рассылки → per-user редирект-ссылки клик-трекинга (аналог
    Runtime.wrap_button_url, но для рассылок, не для узлов воронки).

    Только http(s)-ссылки из allowlist доменов оборачиваются (анти-open-redirect,
    та же политика что и у воронок) - t.me и внешние домены идут прямой ссылкой,
    клик по ним не трекается меткой (не наш редирект-сервис).
    """
    from urllib.parse import urlparse
    btns = json.loads(buttons_json or "[]")
    if not btns:
        return None
    rows = []
    for b in btns:
        url = b["url"]
        host = (urlparse(url).hostname or "").lower()
        allowed = any(host == d or host.endswith("." + d) for d in REDIRECT_ALLOW)
        if allowed:
            uid_link = _uuid.uuid4().hex
            db.add_redirect(uid_link, user_id, BROADCAST_FUNNEL_MARK, label, url, "broadcast")
            db.add_redirect.__self__ if False else None  # no-op, keep signature obvious in diff
            url = f"{REDIRECT_BASE}/r/{uid_link}"
            db.add_redirect(uid_link, user_id, f"{BROADCAST_FUNNEL_MARK}{bid}", label, url, "broadcast") if False else None
        rows.append([InlineKeyboardButton(b["text"], url=url)])
    return InlineKeyboardMarkup(rows)


def parse_post_url(url: str):
    """Ссылка на пост канала → (src_chat_id, src_message_id) для copyMessage.
    /c/<id>/<mid> (приватный) → chat_id = '-100<id>' (Bot API формат супергрупп/каналов).
    /<username>/<mid> (публичный) → chat_id = '@username'.
    Не распознано → (None, None) - зовущий сам решает как ругаться."""
    m = _POST_URL_RE.match((url or "").strip())
    if not m:
        return None, None
    mid = int(m.group("mid"))
    if m.group("cid"):
        return f"-100{m.group('cid')}", mid
    return f"@{m.group('uname')}", mid


# Кирпич централизованного клик-трекинга рассылок.
# Любой из 7 ботов, отправляя рассылку с внешней http-ссылкой, кладёт в кнопку не
# прямую ссылку на лендинг, а персональный https://author.ru/w/r/{uuid}.
# redirect_links при этом пишется в БАЗУ СОБЫТИЕ-редиректа (её обслуживает
# event-redirect :8001, проксируемый nginx на /w/r/). Так клики со ВСЕХ ботов
# централизованно оседают в одной базе voronka-2.clicks с меткой кампании.
#
# Подключение строго file:...?mode=rw (как в crossdb): опечатка в пути даёт громкую
# ошибку, а не молча созданный пустой .sqlite. busy_timeout - редирект-сервис и боты
# пишут в один файл, ждём вместо мгновенного 'database is locked'.
EVENT_REDIRECT_URL_BASE = "https://author.ru/w/r"


def make_track_url(event_db_path, user_id, target_url, campaign):
    """Персональная trackable-ссылка на target_url через событие-редирект.

    Генерит uuid, пишет строку redirect_links в БД событие (event_db_path,
    обычно /opt/voronka-2/voronka-2.sqlite) и возвращает внешний
    https://author.ru/w/r/{uuid}. Клик по этой ссылке пройдёт через
    event-redirect (:8001) → запишется в voronka-2.clicks/click_queue.

    node='broadcast', kind='broadcast', funnel_key=campaign - метка кампании.
    """
    uid = _uuid.uuid4().hex
    conn = sqlite3.connect(f"file:{event_db_path}?mode=rw", uri=True, timeout=5)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(
            "INSERT OR REPLACE INTO redirect_links"
            "(uuid, user_id, funnel_key, node, target_url, kind, created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (uid, user_id, campaign, "broadcast", target_url, "broadcast", time.time()))
        conn.commit()
    finally:
        conn.close()
    return f"{EVENT_REDIRECT_URL_BASE}/{uid}"
