"""Кросс-инстанс операции с БД соседнего бота (MUTE_DB_PATH).

Два инстанса (движок воронок @ubf1cc5 и бот событие
@event_bot) живут на одном сервере с раздельными SQLite.
tg user_id общий, поэтому вход во фронт-цепочку / отказ / регистрация
должны глушить дожимы И у соседа - иначе человек получит два дожима
о событие за одни сутки.

Подключение строго file:...?mode=rw - опечатка в пути даёт громкую ошибку,
а не молча созданный пустой .sqlite (подтверждённая находка ревью).
"""
import sqlite3, time, logging

from .config import MUTE_DB_PATH

log = logging.getLogger("voronka")

REQUIRED_TABLES = {"scheduled_jobs", "tags"}


def check_on_startup():
    """MUTE_DB_PATH задан → БД соседа обязана существовать и иметь нужные
    таблицы, иначе fail-fast при старте: тихий no-op мьюта хуже падения."""
    if not MUTE_DB_PATH:
        return
    try:
        conn = sqlite3.connect(f"file:{MUTE_DB_PATH}?mode=rw", uri=True, timeout=2)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
    except Exception as e:
        raise SystemExit(f"MUTE_DB_PATH={MUTE_DB_PATH} не открывается: {e}")
    missing = REQUIRED_TABLES - tables
    if missing:
        raise SystemExit(f"MUTE_DB_PATH={MUTE_DB_PATH}: нет таблиц {sorted(missing)} - это не БД движка воронок")


def _conn():
    conn = sqlite3.connect(f"file:{MUTE_DB_PATH}?mode=rw", uri=True, timeout=2)
    conn.execute("PRAGMA busy_timeout=2000")
    return conn


def cancel_neighbor(user_id):
    """Гасит pending-дожимы юзера в БД соседа (вход во фронт-цепочку)."""
    if not MUTE_DB_PATH:
        return
    try:
        conn = _conn()
        try:
            conn.execute("UPDATE scheduled_jobs SET status='cancelled' "
                         "WHERE user_id=? AND status='pending'", (user_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning("сосед: cancel не прошёл (user %s): %s", user_id, e)


def neighbor_live_state(user_id):
    """Состояние юзера в воронках живого события у соседа: (funnel_key, node) или None.

    Зачем читать чужую базу. Человек мог войти в воронку живого события у соседнего
    бота, а написать сюда. В своей базе он числится узлом старой воронки, и ответчик
    уводил бы его на уже пройденный шаг. Правда про живое событие лежит в БД соседа
    (воронки LIVE*) - читаем её, чтобы модель знала реальную стадию человека.
    Read-only, любой сбой = None (деградируем к старому поведению, бот не падает).
    """
    if not MUTE_DB_PATH:
        return None
    try:
        conn = sqlite3.connect(f"file:{MUTE_DB_PATH}?mode=ro", uri=True, timeout=2)
        try:
            conn.execute("PRAGMA busy_timeout=2000")
            row = conn.execute(
                "SELECT funnel_key, node FROM funnel_state "
                "WHERE user_id=? AND funnel_key LIKE 'LIVE%' "
                "ORDER BY entered_at DESC LIMIT 1", (user_id,)).fetchone()
        finally:
            conn.close()
    except Exception as e:
        log.warning("сосед: статус живого события не прочитан (user %s): %s", user_id, e)
        return None
    return (row[0], row[1]) if row else None


def tag_neighbor(user_id, tag):
    """Ставит юзеру тег у соседа (registered / event_optout) + гасит pending.
    Гвард соседа по этим тегам подавляет и будущие продающие узлы."""
    if not MUTE_DB_PATH:
        return
    try:
        conn = _conn()
        try:
            conn.execute("UPDATE scheduled_jobs SET status='cancelled' "
                         "WHERE user_id=? AND status='pending'", (user_id,))
            conn.execute("INSERT OR IGNORE INTO tags(user_id, tag, set_at) VALUES(?,?,?)",
                         (user_id, tag, time.time()))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning("сосед: тег %s не прошёл (user %s): %s", tag, user_id, e)
