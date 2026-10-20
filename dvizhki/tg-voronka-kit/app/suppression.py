"""Общий реестр исключений (suppression list) для ВСЕХ 7 инстансов бота.

7 разных ботов (@ubf1cc5, @event_bot,
base-author/autoapprove/pr/team/secret) шлют рассылки из своих
SQLite независимо. Человек, который уже флагман/зарегистрировался/попросил
не писать через ЛЮБОЙ из них, не должен получать рассылку из ОСТАЛЬНЫХ шести -
для этого один общий файл-реестр (SUPPRESSION_DB_PATH), в который пишут все,
а перед каждой отправкой рассылки читают все.

Открытие: file:...?mode=rw как в crossdb.py - опечатка пути даёт громкую
ошибку при СТАРТЕ (check_on_startup), а не молча создаёт пустой .sqlite.
Но в отличие от crossdb.py (сосед, 2 инстанса) здесь 7 процессов ОДНОВРЕМЕННО
читают на каждый тик рассылки - при недоступности файла (сетевой диск моргнул,
права, повреждён) rw-конкретно ЭТА рассылка не должна встать колом.
Поэтому графация мягче: is_suppressed() при ЛЮБОЙ ошибке чтения логирует
WARNING и возвращает False - лучше отправить лишнему человеку (максимум
надоели рассылкой), чем уронить рассылку ВСЕМ семи ботам разом из-за одного
битого общего файла. add()/add_many() наоборот падают наверх (кто их вызвал -
тег 'registered' или админ-команда - должен узнать, что запись НЕ прошла).

Конкурентность: WAL + busy_timeout=3000 - 7 процессов-читателей и любой из
них как писатель (регистрация может прилететь из каждого бота одновременно).
"""
import os, sqlite3, time, logging, threading

from .config import SUPPRESSION_DB_PATH as DB_PATH
from .config import SUPPRESSION_LOOKUP_DBS

log = logging.getLogger("voronka")

SCHEMA = """
CREATE TABLE IF NOT EXISTS suppressed(
  user_id INTEGER PRIMARY KEY, reason TEXT, source TEXT, added_at REAL);
"""

# кэш is_suppressed(): рассылка дёргает эту функцию НА КАЖДОГО получателя батча
# (сотни-тысячи раз за прогон) - без кэша это лишний диск-хит на каждое сообщение
# рядом с уже существующей проверкой db.flags(uid). 5 сек - контакт, добавленный
# в реестр только что, попадёт под подавление максимум на 5с позже (рассылка и так
# идёт минуты), а разгрузка диска на порядки больше.
_CACHE_TTL = 5.0
_cache_lock = threading.Lock()
_cache = {"loaded_at": 0.0, "ids": frozenset(), "healthy": True}


# --- правка слоя кита (R154): один инициализатор на процесс ---
_BUSY_TIMEOUT_MS = 15000
_schema_lock = threading.Lock()
_schema_ready = set()   # пути баз, где схема уже поставлена в этом процессе


def _ensure_schema(conn):
    """Режим журнала и схема ставятся один раз на КАЖДЫЙ путь базы.

    Переключение journal_mode берёт эксклюзивную блокировку файла.
    Когда её брало каждое соединение, полсотни одновременных
    писателей давали `database is locked`, и часть записей
    терялась молча.

    Ключ - путь, а не один флаг на процесс: тесты и админ-инструменты
    переключают DB_PATH на новый файл, и флагом «уже готово» новая
    база осталась бы без таблиц."""
    path = DB_PATH
    if path in _schema_ready:
        return
    with _schema_lock:
        if path in _schema_ready:
            return
        for attempt in range(6):
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(SCHEMA)
                conn.commit()
                _schema_ready.add(path)
                return
            except sqlite3.OperationalError as e:
                if "locked" not in str(e) and "busy" not in str(e):
                    raise
                time.sleep(0.05 * (2 ** attempt))
        conn.executescript(SCHEMA)
        conn.commit()
        _schema_ready.add(path)


def _with_retry(fn, attempts=8):
    """Повтор записи при занятой базе. Без него первый же проигравший
    гонку писатель терял отписку, а вызывающий видел WARNING."""
    last = None
    for attempt in range(attempts):
        try:
            return fn()
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) and "busy" not in str(e):
                raise
            last = e
            time.sleep(0.05 * (2 ** attempt))
    raise last


def _connect():
    """mode=rwc (create-if-missing): в отличие от crossdb.py (сосед - чужая БД,
    которая ОБЯЗАНА уже существовать, опечатка пути там должна падать громко),
    здесь реестр - НОВЫЙ общий файл: кто из 7 инстансов стартует первым, тот его
    и создаёт. _txlock=immediate берёт write-lock сразу в начале транзакции
    (а не откладывает до первого INSERT) - при гонке двух ботов один сразу
    получит SQLITE_BUSY (который busy_timeout превращает в ожидание), а не
    полуприменённую запись где-то в середине транзакции."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=rwc&_txlock=immediate", uri=True,
                           timeout=_BUSY_TIMEOUT_MS / 1000.0)
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    _ensure_schema(conn)
    return conn


def _ensure_dir():
    d = os.path.dirname(DB_PATH)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _load_all_ids():
    """Снапшот всех user_id из реестра. Бросает исключение наверх при сбое -
    вызывающий (_refresh_cache) решает, что делать (graceful degradation)."""
    conn = _connect()
    try:
        return frozenset(r[0] for r in conn.execute("SELECT user_id FROM suppressed"))
    finally:
        conn.close()


def _refresh_cache():
    """Перечитать кэш, если устарел. При ошибке НЕ падаем: помечаем кэш нездоровым
    и логируем WARNING - is_suppressed() тогда честно отдаёт False, а НЕ последнее
    протухшее значение (реестр мог поменяться, стух он или нет - неизвестно).
    Рассылка не должна вставать из-за недоступности общего файла - HARD-требование."""
    now = time.time()
    with _cache_lock:
        if now - _cache["loaded_at"] < _CACHE_TTL and _cache["healthy"]:
            return
        try:
            ids = _load_all_ids()
            _cache["ids"] = ids
            _cache["loaded_at"] = now
            _cache["healthy"] = True
        except Exception as e:
            log.warning("suppression: реестр %s недоступен, отдаю False (%s)", DB_PATH, e)
            _cache["healthy"] = False
            # loaded_at НЕ трогаем - следующий вызов попробует снова сразу же,
            # не будет ждать полный TTL (иначе долгий сбой диска = долгая слепота)


def is_suppressed(user_id) -> bool:
    """Быстрая проверка (кэш 5с). При недоступном/повреждённом реестре - ВСЕГДА
    False (см. обоснование графации в шапке файла), а не последнее протухшее
    значение кэша: лучше лишний раз отправить, чем уронить рассылку во ВСЕХ
    7 ботах разом из-за одного общего файла."""
    _refresh_cache()
    with _cache_lock:
        if not _cache["healthy"]:
            return False
        return user_id in _cache["ids"]


def add(user_id, reason, source):
    """Добавить одного. reason: 'flagman' | 'registered' | 'manual'.
    Идемпотентно (PK user_id) - повторная запись просто обновляет reason/source."""
    _ensure_dir()

    def _write():
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO suppressed(user_id, reason, source, added_at) VALUES(?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,
                   source=excluded.source, added_at=excluded.added_at""",
                (user_id, reason, source, time.time()))
            conn.commit()
        finally:
            conn.close()

    _with_retry(_write)
    # инвалидация кэша: следующий is_suppressed() увидит свежую запись сразу,
    # не будет ждать TTL (важно для /suppress - админ ждёт немедленного эффекта)
    with _cache_lock:
        _cache["loaded_at"] = 0.0


def add_safe(user_id, reason, source):
    """Тот же add(), но НЕ бросает наружу - для точек интеграции внутри обычного
    пользовательского пути (клик по кнопке в runtime.apply, deep-link /start,
    вебхук платформы курса): запись в общий реестр - побочный эффект регистрации,
    а не она сама. Сбой общего файла (тот же класс проблем, что и is_suppressed)
    не должен ронять воронку/вебхук у живого юзера - логируем WARNING и идём
    дальше (симметрично crossdb.tag_neighbor, тот же принцип "сосед недоступен -
    не блокируем основной сценарий").
    Админ-команды (/suppress) и tools/suppress_import.py используют add()
    напрямую БЕЗ этой обёртки - там сбой обязан быть виден вызвавшему."""
    try:
        add(user_id, reason, source)
    except Exception as e:
        log.warning("suppression: add(%s,%s,%s) не прошёл (%s)", user_id, reason, source, e)


def add_many(pairs):
    """pairs: итерируемое (user_id, reason, source). Одна транзакция - массовый
    импорт tools/suppress_import.py на тысячах id не должен делать commit на каждый."""
    _ensure_dir()
    rows = [(uid, reason, source, time.time()) for uid, reason, source in pairs]

    def _write():
        conn = _connect()
        try:
            conn.executemany(
                """INSERT INTO suppressed(user_id, reason, source, added_at) VALUES(?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,
                   source=excluded.source, added_at=excluded.added_at""",
                rows)
            conn.commit()
        finally:
            conn.close()

    _with_retry(_write)
    with _cache_lock:
        _cache["loaded_at"] = 0.0


def remove(user_id):
    def _write():
        conn = _connect()
        try:
            conn.execute("DELETE FROM suppressed WHERE user_id=?", (user_id,))
            conn.commit()
        finally:
            conn.close()

    _with_retry(_write)
    with _cache_lock:
        _cache["loaded_at"] = 0.0


def count():
    """Общее число записей в реестре."""
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM suppressed").fetchone()[0]
    finally:
        conn.close()


def count_by_reason():
    """Разбивка по reason для /suppressed."""
    conn = _connect()
    try:
        return {r[0]: r[1] for r in conn.execute(
            "SELECT reason, COUNT(*) FROM suppressed GROUP BY reason")}
    finally:
        conn.close()


def list_by_reason(reason):
    conn = _connect()
    try:
        return [r[0] for r in conn.execute(
            "SELECT user_id FROM suppressed WHERE reason=?", (reason,))]
    finally:
        conn.close()


def get(user_id):
    """Одна запись реестра для юзера (для /who-подобных выводов), либо None."""
    conn = _connect()
    try:
        r = conn.execute(
            "SELECT user_id, reason, source, added_at FROM suppressed WHERE user_id=?",
            (user_id,)).fetchone()
        return {"user_id": r[0], "reason": r[1], "source": r[2], "added_at": r[3]} if r else None
    finally:
        conn.close()


def _find_user_ids_by_username(username):
    """Ищет tg user_id по username во ВСЕХ 7 базах SUPPRESSION_LOOKUP_DBS
    (сайт платформы курса знает только @ник, не tg_id - искать надо везде, где человек
    мог писать боту). Открываем read-only (file:...?mode=ro) - redirect-сервис
    работает в контексте СВОЕГО инстанса и не имеет права ничего писать в чужие
    SQLite (это забота suppression-реестра, не crossdb). Битая/недоступная одна
    БД из списка не должна ронять поиск по остальным шести - лог WARNING, дальше."""
    found = set()
    for path in SUPPRESSION_LOOKUP_DBS:
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
            try:
                rows = conn.execute(
                    "SELECT user_id FROM contacts WHERE lower(username)=?", (username,)).fetchall()
                found.update(r[0] for r in rows)
            finally:
                conn.close()
        except Exception as e:
            log.warning("suppression: lookup-БД %s недоступна при поиске username (%s)", path, e)
    return found


def resolve_and_suppress_by_username(username, reason, source):
    """Регистрация с сайта платформы курса приходит с @username (не tg_id, сайт его не
    знает). Находим tg user_id этого username во ВСЕХ 7 базах и добавляем КАЖДЫЙ
    найденный в общий реестр (реестр по user_id глушит рассылки сразу во всех
    ботах, поэтому достаточно add() один раз на найденный id - не нужно писать
    в семь suppression-вызовов). Ник мог совпасть в разных базах у разных людей
    (маловероятно, но чужой ник не гарантирует один и тот же tg_id) - собираем
    set, метим все.
    Возврат: {"ok": True, "username":.., "matched_ids": [...], "count": N} - даже
    если ничего не нашли (count=0), это НЕ ошибка: человек мог зарегистрироваться
    на сайте, ни разу не написав ни одному боту - тогда рассылать ему и так некому."""
    norm = (username or "").strip().lstrip("@").lower()
    if not norm:
        return {"ok": False, "error": "empty username"}
    ids = _find_user_ids_by_username(norm)
    for uid in ids:
        add(uid, reason, source)
    return {"ok": True, "username": norm, "matched_ids": sorted(ids), "count": len(ids)}
