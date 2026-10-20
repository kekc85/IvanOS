"""Тесты общего реестра исключений (suppression list, все 7 ботов).
Проверяем логику модуля app/suppression.py напрямую на временных .sqlite -
никакого Telegram/сети. Запуск: .venv/bin/python -m tests.test_suppression
"""
import sys, os, tempfile, time, threading, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import suppression

_p = _f = 0
def check(n, c):
    global _p, _f
    if c: _p += 1
    else: _f += 1; print(f"  FAIL: {n}")


def _fresh_db():
    """Свежий временный путь + сброс модульного кэша, чтобы тесты не текли
    друг в друга (кэш is_suppressed живёт в модульной переменной)."""
    path = tempfile.mktemp(suffix=".sqlite")
    suppression.DB_PATH = path
    with suppression._cache_lock:
        suppression._cache["ids"] = frozenset()
        suppression._cache["loaded_at"] = 0.0
    return path


# --- добавление / проверка / удаление ---
_fresh_db()
check("новый юзер не в реестре", not suppression.is_suppressed(111))
suppression.add(111, "flagman", "платформы курса")
check("после add() is_suppressed видит сразу (кэш инвалидирован)", suppression.is_suppressed(111))
check("count()==1 после первого add", suppression.count() == 1)
rec = suppression.get(111)
check("get() возвращает reason/source", rec["reason"] == "flagman" and rec["source"] == "платформы курса")

suppression.remove(111)
check("после remove() is_suppressed видит сразу", not suppression.is_suppressed(111))
check("count()==0 после remove", suppression.count() == 0)


# --- идемпотентность add() ---
_fresh_db()
suppression.add(222, "registered", "bot_a")
suppression.add(222, "registered", "bot_b")   # повторно, другой source (симулирует 2-й бот)
check("повторный add того же user_id не плодит вторую строку (PK)", suppression.count() == 1)
check("повторный add ОБНОВИЛ source (последний источник побеждает)",
      suppression.get(222)["source"] == "bot_b")


# --- add_many идемпотентность + отчёт по добавленным/уже было ---
_fresh_db()
suppression.add(1, "flagman", "import")
before = suppression.count()
suppression.add_many([(1, "flagman", "import"), (2, "flagman", "import"), (3, "flagman", "import")])
after = suppression.count()
check("add_many: 1 уже был, 2 и 3 новые -> count вырос на 2", after - before == 2)
check("add_many записал все три", suppression.is_suppressed(1) and suppression.is_suppressed(2)
      and suppression.is_suppressed(3))
# повторный прогон того же батча - без изменений (идемпотентность массового импорта)
before2 = suppression.count()
suppression.add_many([(1, "flagman", "import"), (2, "flagman", "import"), (3, "flagman", "import")])
check("повторный add_many того же набора не меняет count", suppression.count() == before2)


# --- list_by_reason / count_by_reason ---
_fresh_db()
suppression.add(10, "flagman", "s"); suppression.add(11, "flagman", "s")
suppression.add(12, "registered", "s"); suppression.add(13, "manual", "s")
check("list_by_reason('flagman') = [10,11]", sorted(suppression.list_by_reason("flagman")) == [10, 11])
by_reason = suppression.count_by_reason()
check("count_by_reason разбивка верна",
      by_reason.get("flagman") == 2 and by_reason.get("registered") == 1 and by_reason.get("manual") == 1)


# --- кэш: TTL не даёт увидеть запись, сделанную В ОБХОД add() (напрямую в БД), сразу ---
_fresh_db()
suppression.is_suppressed(999)   # прогреваем кэш (loaded_at=now, пусто)
conn = sqlite3.connect(suppression.DB_PATH)
conn.execute("INSERT INTO suppressed(user_id,reason,source,added_at) VALUES(999,'manual','raw',0)")
conn.commit(); conn.close()
check("сразу после прямой записи мимо add() кэш ЕЩЁ не видит (TTL держит старое значение)",
      not suppression.is_suppressed(999))
with suppression._cache_lock:
    suppression._cache["loaded_at"] = 0.0   # симулируем истечение TTL
check("после истечения TTL кэш перечитался и видит запись", suppression.is_suppressed(999))


# --- graceful degradation: реестр недоступен -> is_suppressed=False, не исключение ---
_fresh_db()
suppression.add(500, "flagman", "s")
check("до порчи файла - suppressed", suppression.is_suppressed(500))
with suppression._cache_lock:
    suppression._cache["loaded_at"] = 0.0
bad_path = tempfile.mktemp(suffix=".sqlite")
with open(bad_path, "w") as f:
    f.write("это не sqlite файл, а мусор")   # повреждённый "файл БД"
suppression.DB_PATH = bad_path
try:
    result = suppression.is_suppressed(500)
    check("is_suppressed на повреждённом файле НЕ бросает исключение, возвращает False", result is False)
except Exception as e:
    check(f"is_suppressed на повреждённом файле НЕ должен падать, упал: {e}", False)

# путь в несуществующей директории без прав на создание - тоже must-not-crash
with suppression._cache_lock:
    suppression._cache["loaded_at"] = 0.0
suppression.DB_PATH = "/root/no_access_dir_xyz/suppression.sqlite"
try:
    result2 = suppression.is_suppressed(500)
    check("is_suppressed на недоступном пути НЕ бросает исключение, возвращает False", result2 is False)
except Exception as e:
    check(f"is_suppressed на недоступном пути НЕ должен падать, упал: {e}", False)


# --- конкурентная запись из двух соединений (2 "бота" пишут почти одновременно) ---
_fresh_db()
errors = []
def _writer(uid, reason):
    try:
        suppression.add(uid, reason, f"writer_{uid}")
    except Exception as e:
        errors.append(e)

threads = [threading.Thread(target=_writer, args=(uid, "registered")) for uid in range(2000, 2050)]
for t in threads: t.start()
for t in threads: t.join()
check("конкурентная запись 50 потоков не уронила ни одной (WAL+busy_timeout держат)", not errors)
check("все 50 записей реально попали в реестр", suppression.count() == 50)


# --- то же самое, но из ДВУХ независимых sqlite-соединений напрямую (не через add) ---
_fresh_db()
def _raw_writer(uid):
    conn = sqlite3.connect(f"file:{suppression.DB_PATH}?mode=rwc&_txlock=immediate", uri=True, timeout=3)
    conn.execute("PRAGMA busy_timeout=3000")
    conn.execute("CREATE TABLE IF NOT EXISTS suppressed(user_id INTEGER PRIMARY KEY, reason TEXT, source TEXT, added_at REAL)")
    try:
        conn.execute("INSERT OR IGNORE INTO suppressed(user_id,reason,source,added_at) VALUES(?,?,?,?)",
                     (uid, "manual", "raw", time.time()))
        conn.commit()
    finally:
        conn.close()

errors2 = []
def _safe_raw(uid):
    try:
        _raw_writer(uid)
    except Exception as e:
        errors2.append(e)

threads2 = [threading.Thread(target=_safe_raw, args=(uid,)) for uid in range(3000, 3030)]
for t in threads2: t.start()
for t in threads2: t.join()
check("конкурентная запись из 2 независимых raw-соединений не уронила запись", not errors2)
check("все 30 raw-записей попали (busy_timeout дождался очереди)", suppression.count() == 30)


# --- resolve_and_suppress_by_username: поиск по НЕСКОЛЬКИМ временным "базам" ---
def _make_contacts_db(path, rows):
    """rows: [(user_id, username), ...] - минимальная contacts-таблица под тест
    (реальная схема шире, но lookup читает только user_id/username)."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE contacts(user_id INTEGER PRIMARY KEY, username TEXT)")
    conn.executemany("INSERT INTO contacts(user_id, username) VALUES(?,?)", rows)
    conn.commit()
    conn.close()


_fresh_db()
db1 = tempfile.mktemp(suffix=".sqlite")
db2 = tempfile.mktemp(suffix=".sqlite")
db3_missing = tempfile.mktemp(suffix=".sqlite")   # НЕ создаём - симулирует битую/отсутствующую БД
_make_contacts_db(db1, [(701, "ua15f8b"), (702, "other_user")])
_make_contacts_db(db2, [(701, "ua15f8b")])   # тот же человек написал второму боту - найдётся в обеих
suppression.SUPPRESSION_LOOKUP_DBS = [db1, db2, db3_missing]

res = suppression.resolve_and_suppress_by_username("@ua15f8b", "registered", "platform_site")
check("resolve_and_suppress_by_username находит user_id в НЕСКОЛЬКИХ базах", res["ok"] and res["matched_ids"] == [701])
check("count==1 (один и тот же uid найден в двух базах, но это один человек)", res["count"] == 1)
check("после resolve юзер 701 в общем реестре (add вызван)", suppression.is_suppressed(701))

# нормализация: @ua15f8b / ua15f8b / UA15F8B -> один и тот же результат
_fresh_db()
suppression.SUPPRESSION_LOOKUP_DBS = [db1, db2, db3_missing]
for variant in ("@ua15f8b", "ua15f8b", "UA15F8B", "  @UA15F8B  "):
    r = suppression.resolve_and_suppress_by_username(variant, "registered", "platform_site")
    check(f"нормализация варианта {variant!r} находит того же user_id 701", r["matched_ids"] == [701])

# username не найден ни в одной базе - ok=True, count=0 (НЕ ошибка, некому слать)
_fresh_db()
suppression.SUPPRESSION_LOOKUP_DBS = [db1, db2, db3_missing]
r_missing = suppression.resolve_and_suppress_by_username("no_such_nick_zzz", "registered", "platform_site")
check("username не найден нигде -> ok=True", r_missing["ok"] is True)
check("username не найден нигде -> count=0", r_missing["count"] == 0)
check("username не найден нигде -> matched_ids=[]", r_missing["matched_ids"] == [])

# пустой/невалидный username - ошибка, не ищем
_fresh_db()
r_empty = suppression.resolve_and_suppress_by_username("   ", "registered", "platform_site")
check("пустой username -> ok=False с error", r_empty["ok"] is False and "error" in r_empty)
r_empty2 = suppression.resolve_and_suppress_by_username("@", "registered", "platform_site")
check("username из одного '@' (после strip пусто) -> ok=False", r_empty2["ok"] is False)

# битая БД в списке (не sqlite-файл вовсе) не должна ронять поиск по остальным
_fresh_db()
bad_lookup_db = tempfile.mktemp(suffix=".sqlite")
with open(bad_lookup_db, "w") as f:
    f.write("мусор, не sqlite")
suppression.SUPPRESSION_LOOKUP_DBS = [db1, bad_lookup_db, db2]
try:
    r_broken = suppression.resolve_and_suppress_by_username("ua15f8b", "registered", "platform_site")
    check("битая БД в списке не роняет resolve, остальные базы отрабатывают",
          r_broken["ok"] and r_broken["matched_ids"] == [701])
except Exception as e:
    check(f"resolve_and_suppress_by_username НЕ должен падать на битой БД в списке, упал: {e}", False)


print(f"\nИтог suppression: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
