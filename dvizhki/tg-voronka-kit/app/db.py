"""Персистенция на SQLite для спайка/локалки (на VPS - PostgreSQL, слой тот же).

Хранит контактов, состояние в воронке, теги, отложенные джобы, клики, аудит.
Дедуп джоб через UNIQUE(user_id,funnel_key,node) среди pending.
"""
import sqlite3, json, threading, time as _time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts(
  user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
  source_funnel TEXT, joined_at REAL, opted_out INTEGER DEFAULT 0, banned_bot INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS tags(
  user_id INTEGER, tag TEXT, set_at REAL, UNIQUE(user_id, tag));
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS funnel_state(
  user_id INTEGER, funnel_key TEXT, node TEXT, entered_at REAL,
  PRIMARY KEY(user_id, funnel_key));
CREATE TABLE IF NOT EXISTS scheduled_jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, funnel_key TEXT,
  node TEXT, due_at REAL, status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup
  ON scheduled_jobs(user_id, funnel_key, node) WHERE status='pending';
CREATE INDEX IF NOT EXISTS idx_jobs_due ON scheduled_jobs(due_at, status);
CREATE TABLE IF NOT EXISTS redirect_links(
  uuid TEXT PRIMARY KEY, user_id INTEGER, funnel_key TEXT, node TEXT, target_url TEXT, kind TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS clicks(
  uuid TEXT, user_id INTEGER, clicked_at REAL, UNIQUE(uuid, user_id));
CREATE TABLE IF NOT EXISTS click_queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, funnel_key TEXT,
  target_url TEXT, created_at REAL, processed INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_clickq ON click_queue(processed, id);
CREATE TABLE IF NOT EXISTS events(
  ts REAL, user_id INTEGER, kind TEXT, payload_min TEXT);
CREATE TABLE IF NOT EXISTS broadcasts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, segment TEXT, text TEXT, buttons TEXT,
  status TEXT DEFAULT 'draft', total INTEGER DEFAULT 0, sent INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0, blocked INTEGER DEFAULT 0, created_at REAL);
-- mode/src_chat_id/src_message_id: режим copyMessage (рассылка точной копией поста
-- из канала). CREATE TABLE тут не поможет существующим БД (таблица уже есть) -
-- колонки доливает _ensure_column ниже (ALTER TABLE, безопасно на старой базе).
CREATE TABLE IF NOT EXISTS broadcast_recipients(
  broadcast_id INTEGER, user_id INTEGER, status TEXT DEFAULT 'pending',
  error TEXT, sent_at REAL, PRIMARY KEY(broadcast_id, user_id));
CREATE INDEX IF NOT EXISTS idx_br_pending ON broadcast_recipients(broadcast_id, status);
CREATE TABLE IF NOT EXISTS ai_dialog(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, text TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS idx_ai_dialog_user ON ai_dialog(user_id, id);
CREATE TABLE IF NOT EXISTS ai_kv(k TEXT PRIMARY KEY, v TEXT);
"""


class DB:
    def __init__(self, path):
        self.path = path
        self._c = sqlite3.connect(path, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        self._c.execute("PRAGMA journal_mode=WAL")
        # два процесса (bot + redirect) пишут в один файл. WAL сериализует писателей,
        # busy_timeout заставляет второго ЖДАТЬ до 5с вместо мгновенного 'database is locked'
        self._c.execute("PRAGMA busy_timeout=5000")
        self._c.executescript(SCHEMA)
        self._c.commit()
        # CREATE TABLE IF NOT EXISTS не долива колонки в УЖЕ существующую таблицу
        # (прод-база жила без режима copyMessage) - добираем ALTER TABLE, каждая
        # колонка отдельно и best-effort (SQLite падает, если колонка уже есть)
        self._ensure_column("broadcasts", "mode", "TEXT DEFAULT 'text'")
        self._ensure_column("broadcasts", "src_chat_id", "TEXT")
        self._ensure_column("broadcasts", "src_message_id", "INTEGER")
        # label: сквозная метка аналитики <бот>__<кампания>__<пост>__<действие> собирается
        # в create_broadcast (см. app/config.py BOT_LABEL/CAMPAIGN). Пусто на старых записях.
        self._ensure_column("broadcasts", "label", "TEXT")
        self._c.commit()
        # ВНУТРИ процесса connection ОДИН и check_same_thread=False. redirect-сервис
        # (sync-эндпоинт /r/{uuid}) uvicorn гонит в threadpool → несколько потоков
        # делят один self._c с одной неявной транзакцией: rollback одного потока
        # откатывал незакоммиченный INSERT другого (потеря/дубль кликов при залпе).
        # RLock сериализует записи одного процесса; WAL+busy_timeout держат МЕЖпроцессную.
        self._lock = threading.RLock()

    def _ensure_column(self, table, col, decl):
        """ALTER TABLE ADD COLUMN, если колонки ещё нет. Идемпотентно на каждом
        старте (PRAGMA table_info дешёвый), безопасно на старой базе без неё."""
        cols = {r[1] for r in self._c.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            self._c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    @contextmanager
    def _tx(self):
        with self._lock:
            cur = self._c.cursor()
            try:
                yield cur
                self._c.commit()
            except Exception:
                self._c.rollback()
                raise

    # --- контакты/теги ---
    def upsert_contact(self, user_id, username, first_name, source_funnel):
        # source_funnel=COALESCE: строка могла родиться раньше upsert'а (set_flag в
        # on_start идёт первым) с source_funnel=NULL - такой контакт выпадал из
        # сегментов all/not_registered (они фильтруют IS NOT NULL). Дозаполняем
        # первым реальным источником, уже заполненный не перетираем (ревью)
        with self._tx() as c:
            c.execute("""INSERT INTO contacts(user_id,username,first_name,source_funnel,joined_at)
                         VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                         username=excluded.username, first_name=excluded.first_name,
                         source_funnel=COALESCE(contacts.source_funnel, excluded.source_funnel)""",
                      (user_id, username, first_name, source_funnel, _time.time()))

    def add_tag(self, user_id, tag):
        with self._tx() as c:
            c.execute("INSERT OR IGNORE INTO tags(user_id,tag,set_at) VALUES(?,?,?)",
                      (user_id, tag, _time.time()))

    def tags(self, user_id):
        return {r["tag"] for r in self._c.execute("SELECT tag FROM tags WHERE user_id=?", (user_id,))}

    def set_flag(self, user_id, field, val):
        if field not in ("opted_out", "banned_bot"):   # не assert: не гаснет под python -O
            raise ValueError(f"bad flag field: {field}")
        # upsert: /stop и блокировка обязаны фиксироваться даже если контакта ещё нет
        with self._tx() as c:
            c.execute(f"""INSERT INTO contacts(user_id,{field}) VALUES(?,?)
                          ON CONFLICT(user_id) DO UPDATE SET {field}=excluded.{field}""",
                      (user_id, 1 if val else 0))

    def flags(self, user_id):
        r = self._c.execute("SELECT opted_out,banned_bot FROM contacts WHERE user_id=?", (user_id,)).fetchone()
        return (bool(r["opted_out"]), bool(r["banned_bot"])) if r else (False, False)

    def get_first_name(self, user_id):
        r = self._c.execute("SELECT first_name FROM contacts WHERE user_id=?", (user_id,)).fetchone()
        return (r["first_name"] or "").strip() if r else ""

    def has_contact(self, user_id):
        return self._c.execute("SELECT 1 FROM contacts WHERE user_id=?",
                               (user_id,)).fetchone() is not None

    # --- состояние воронки ---
    def set_state(self, user_id, funnel_key, node):
        with self._tx() as c:
            c.execute("""INSERT INTO funnel_state(user_id,funnel_key,node,entered_at)
                         VALUES(?,?,?,?) ON CONFLICT(user_id,funnel_key) DO UPDATE SET
                         node=excluded.node, entered_at=excluded.entered_at""",
                      (user_id, funnel_key, node, _time.time()))

    def get_state(self, user_id, funnel_key):
        r = self._c.execute("SELECT node FROM funnel_state WHERE user_id=? AND funnel_key=?",
                            (user_id, funnel_key)).fetchone()
        return r["node"] if r else None

    # --- джобы ---
    def schedule(self, user_id, funnel_key, node, due_at, delete_others=False):
        with self._tx() as c:
            if delete_others:
                c.execute("UPDATE scheduled_jobs SET status='cancelled' WHERE user_id=? AND funnel_key=? AND status='pending'",
                          (user_id, funnel_key))
            c.execute("""INSERT OR IGNORE INTO scheduled_jobs(user_id,funnel_key,node,due_at)
                         VALUES(?,?,?,?)""", (user_id, funnel_key, node, due_at))

    def cancel_all(self, user_id, funnel_key=None):
        with self._tx() as c:
            if funnel_key:
                c.execute("UPDATE scheduled_jobs SET status='cancelled' WHERE user_id=? AND funnel_key=? AND status='pending'",
                          (user_id, funnel_key))
            else:
                c.execute("UPDATE scheduled_jobs SET status='cancelled' WHERE user_id=? AND status='pending'", (user_id,))

    def cancel_pending_node(self, user_id, funnel_key, node):
        """Погасить конкретный pending-узел юзера. Зовётся когда родитель узла так и
        не доставлен (failed): его потомки, запланированные оптимистичным apply, надо
        снять, иначе юзер получит следующее звено без предыдущего (разрыв цепочки)."""
        with self._tx() as c:
            c.execute("UPDATE scheduled_jobs SET status='cancelled' "
                      "WHERE user_id=? AND funnel_key=? AND node=? AND status='pending'",
                      (user_id, funnel_key, node))

    def cancel_other_funnels(self, user_id, keep_key):
        """Гасит pending-дожимы ВСЕХ воронок юзера, кроме keep_key. Вход в новую
        воронку не должен наслаивать второй параллельный дожим на первый."""
        with self._tx() as c:
            c.execute("UPDATE scheduled_jobs SET status='cancelled' "
                      "WHERE user_id=? AND funnel_key!=? AND status='pending'", (user_id, keep_key))

    def has_pending(self, user_id, funnel_key):
        """Есть ли активный (pending) дожим по этой воронке у юзера."""
        r = self._c.execute("SELECT 1 FROM scheduled_jobs WHERE user_id=? AND funnel_key=? "
                            "AND status='pending' LIMIT 1", (user_id, funnel_key)).fetchone()
        return r is not None

    def due_jobs(self, now_ts, limit=500):
        return [dict(r) for r in self._c.execute(
            "SELECT * FROM scheduled_jobs WHERE status='pending' AND due_at<=? ORDER BY due_at LIMIT ?",
            (now_ts, limit))]

    def mark_job(self, job_id, status):
        # attempts НЕ трогаем: раньше mark_job('processing') делал +1, и requeue_or_fail
        # тоже +1 → один цикл ретрая сжигал 2 попытки (бюджет 3→2, а серия рестартов в
        # залп 07:01 добивала джобу до failed без единой доставки). Счётчик ведёт
        # ТОЛЬКО requeue_or_fail — по одной реальной неудачной отправке.
        with self._tx() as c:
            c.execute("UPDATE scheduled_jobs SET status=? WHERE id=?", (status, job_id))

    def requeue_or_fail(self, job_id, max_attempts=3):
        """Сетевой сбой отправки: вернуть в pending для ретрая, после N попыток - failed.
        Иначе временная ошибка сети = тихая потеря звена дожима."""
        with self._tx() as c:
            r = c.execute("SELECT attempts FROM scheduled_jobs WHERE id=?", (job_id,)).fetchone()
            att = (r["attempts"] if r else 0) + 1
            status = "pending" if att < max_attempts else "failed"
            c.execute("UPDATE scheduled_jobs SET status=?, attempts=? WHERE id=?", (status, att, job_id))
        return status   # 'pending' (ещё ретраим) или 'failed' (сдались) - зовущий гасит потомков

    def reap_stale_jobs(self, older_than_sec=300):
        """Джобы, зависшие в 'processing' (краш между processing и done) → обратно в pending.
        older_than_sec оставлен для совместимости вызова, но НЕ используется (см. ниже)."""
        with self._tx() as c:
            # processing живёт только ВНУТРИ одного синхронного тика (scheduler_tick,
            # max_instances=1). Любая processing-джоба, видимая в начале следующего
            # тика = зависла на краше между mark(processing) и mark(done). Порог по
            # due_at УБРАН: свежая (due_at≈now) зависшая джоба иначе не реанимируется
            # никогда → тихая потеря звена дожима у юзера.
            c.execute("UPDATE scheduled_jobs SET status='pending' WHERE status='processing'")

    # --- клики / редиректы ---
    def add_redirect(self, uuid, user_id, funnel_key, node, target_url, kind):
        with self._tx() as c:
            c.execute("INSERT OR REPLACE INTO redirect_links VALUES(?,?,?,?,?,?,?)",
                      (uuid, user_id, funnel_key, node, target_url, kind, _time.time()))

    def redirect(self, uuid):
        r = self._c.execute("SELECT * FROM redirect_links WHERE uuid=?", (uuid,)).fetchone()
        return dict(r) if r else None

    def record_click(self, uuid, user_id):
        """Записать клик. True если новый (первый), False если повтор."""
        try:
            with self._tx() as c:
                c.execute("INSERT INTO clicks(uuid,user_id,clicked_at) VALUES(?,?,?)",
                          (uuid, user_id, _time.time()))
            return True
        except sqlite3.IntegrityError:
            return False

    # --- очередь кликов (redirect пишет, бот обрабатывает и двигает воронку) ---
    def enqueue_click(self, user_id, funnel_key, target_url):
        with self._tx() as c:
            c.execute("INSERT INTO click_queue(user_id,funnel_key,target_url,created_at) VALUES(?,?,?,?)",
                      (user_id, funnel_key, target_url, _time.time()))

    def record_and_enqueue_click(self, uuid, user_id, funnel_key, target_url):
        """Атомарно: дедуп-строка клика + постановка в очередь продвижения воронки.
        Обе вставки в ОДНОЙ транзакции. Раньше это были две отдельные: краш/локбетвин
        оставлял дедуп занятым (clicks), а click_queue пустым → повтор клика возвращал
        False и продвижение воронки терялось безвозвратно. Возвращает True если клик
        новый (поставлен в очередь), False если повтор (дедуп сработал)."""
        try:
            with self._tx() as c:
                c.execute("INSERT INTO clicks(uuid,user_id,clicked_at) VALUES(?,?,?)",
                          (uuid, user_id, _time.time()))
                c.execute("INSERT INTO click_queue(user_id,funnel_key,target_url,created_at) VALUES(?,?,?,?)",
                          (user_id, funnel_key, target_url, _time.time()))
            return True
        except sqlite3.IntegrityError:
            return False

    def pending_clicks(self, limit=200):
        return [dict(r) for r in self._c.execute(
            "SELECT * FROM click_queue WHERE processed=0 ORDER BY id LIMIT ?", (limit,))]

    def mark_click_done(self, cid):
        with self._tx() as c:
            c.execute("UPDATE click_queue SET processed=1 WHERE id=?", (cid,))

    # --- аудит ---
    def event(self, user_id, kind, payload_min=""):
        with self._tx() as c:
            c.execute("INSERT INTO events(ts,user_id,kind,payload_min) VALUES(?,?,?,?)",
                      (_time.time(), user_id, kind, str(payload_min)[:80]))

    # --- рассылки ---
    def segment_users(self, preset):
        """Именованный сегмент → список user_id. Живые = не отписан и не заблокировал бота.
        Пресеты: all | registered | not_registered | funnel:<КЛЮЧ> | tag:<ИМЯ>."""
        live = "opted_out=0 AND banned_bot=0"
        if preset == "all":
            # только те, кто реально вошёл в воронку (бот с ними в диалоге).
            # органические подписчики канала (source_funnel пуст) исключены - им
            # бот писать не может (нет открытого диалога), рассылка ушла бы в 403.
            rows = self._c.execute(f"SELECT user_id FROM contacts WHERE {live} AND source_funnel IS NOT NULL")
        elif preset == "registered":
            rows = self._c.execute(f"""SELECT c.user_id FROM contacts c
                JOIN tags t ON t.user_id=c.user_id AND t.tag='registered' WHERE c.{live}""")
        elif preset == "not_registered":
            rows = self._c.execute(f"""SELECT c.user_id FROM contacts c
                WHERE c.{live} AND c.source_funnel IS NOT NULL
                AND c.user_id NOT IN (SELECT user_id FROM tags WHERE tag='registered')""")
        elif preset.startswith("funnel:"):
            key = preset.split(":", 1)[1]
            rows = self._c.execute(f"""SELECT c.user_id FROM contacts c
                JOIN tags t ON t.user_id=c.user_id AND t.tag=? WHERE c.{live}""", (f"f_{key}",))
        elif preset.startswith("tag:"):
            # произвольный тег как есть, без префикса f_ (funnel: - для воронок,
            # tag: - для ручных/сторонних тегов типа "vip", "registered" и т.п.)
            tag = preset.split(":", 1)[1]
            rows = self._c.execute(f"""SELECT c.user_id FROM contacts c
                JOIN tags t ON t.user_id=c.user_id AND t.tag=? WHERE c.{live}""", (tag,))
        else:
            return []
        return [r[0] for r in rows]

    def create_broadcast(self, segment, text, buttons, mode="text", src_chat_id=None, src_message_id=None):
        # mode/src_* с дефолтами: старые вызовы (три позиционных аргумента) не ломаются -
        # обычный текстовый режим как раньше, copy-режим передаёт их явно (см. cmd_go)
        with self._tx() as c:
            cur = c.execute(
                "INSERT INTO broadcasts(segment,text,buttons,mode,src_chat_id,src_message_id,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (segment, text, buttons, mode, src_chat_id, src_message_id, _time.time()))
            bid = cur.lastrowid
            # label = <бот>__<кампания>__p<номер поста>__ (действие дописывается на месте
            # события - клик/рег). Пост: src_message_id для copy-режима (номер поста в
            # канале), иначе id самой рассылки (текстовый режим не привязан к посту канала).
            # BOT_LABEL пуст (легаси-инстанс без метки) -> label пуст, аналитика не пишется.
            from .config import BOT_LABEL, CAMPAIGN
            if BOT_LABEL:
                post = src_message_id if (mode == "copy" and src_message_id) else bid
                label = f"{BOT_LABEL}__{CAMPAIGN}__p{post}"
                c.execute("UPDATE broadcasts SET label=? WHERE id=?", (label, bid))
            return bid

    def snapshot_recipients(self, bid, user_ids):
        """Зафиксировать получателей рассылки (чекпоинт-курсор). Идемпотентно."""
        with self._tx() as c:
            c.executemany("INSERT OR IGNORE INTO broadcast_recipients(broadcast_id,user_id) VALUES(?,?)",
                          [(bid, u) for u in user_ids])
            c.execute("UPDATE broadcasts SET total=?, status='running' WHERE id=?", (len(user_ids), bid))

    def broadcast_batch(self, bid, limit=50):
        return [r[0] for r in self._c.execute(
            "SELECT user_id FROM broadcast_recipients WHERE broadcast_id=? AND status='pending' ORDER BY user_id LIMIT ?",
            (bid, limit))]

    def mark_recipient(self, bid, user_id, status, error=None):
        with self._tx() as c:
            c.execute("UPDATE broadcast_recipients SET status=?, error=?, sent_at=? WHERE broadcast_id=? AND user_id=?",
                      (status, error, _time.time(), bid, user_id))
            col = {"sent": "sent", "failed": "failed", "blocked": "blocked"}.get(status)
            if col:
                c.execute(f"UPDATE broadcasts SET {col}={col}+1 WHERE id=?", (bid,))

    def reap_orphan_sending(self, bid):
        """Осиротевшие 'sending' (краш между send и пометкой 'sent') → 'failed'.
        at-most-once: получатель уже мог получить сообщение, поэтому НЕ дослать
        (пометить failed), чтобы не продублировать реальному юзеру. Возвращает число.
        Зовётся на старте каждого broadcast_tick: тик синхронный (max_instances=1),
        так что любой 'sending' на старте = осколок прошлого краша, не in-flight."""
        with self._tx() as c:
            n = c.execute("SELECT COUNT(*) FROM broadcast_recipients WHERE broadcast_id=? AND status='sending'",
                          (bid,)).fetchone()[0]
            if n:
                c.execute("UPDATE broadcast_recipients SET status='failed', error='orphan-sending-reaped' "
                          "WHERE broadcast_id=? AND status='sending'", (bid,))
                c.execute("UPDATE broadcasts SET failed=failed+? WHERE id=?", (n, bid))
            return n

    def label_stats(self, limit=30):
        """Сводка по меткам аналитики: payload_min содержащий '__' (метка вида
        бот__кампания__пост__действие) сгруппирован по точной строке payload_min,
        топ по количеству событий. Легаси-события (payload_min без '__') не попадают -
        это не метки, а старые произвольные пометки (funnel_key/node и т.п.)."""
        rows = self._c.execute(
            "SELECT payload_min, COUNT(*) AS n FROM events WHERE payload_min LIKE '%\\_\\_%' ESCAPE '\\' "
            "GROUP BY payload_min ORDER BY n DESC LIMIT ?", (limit,)).fetchall()
        return [(r["payload_min"], r["n"]) for r in rows]

    def broadcast_report(self, bid):
        r = self._c.execute("SELECT * FROM broadcasts WHERE id=?", (bid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        # счётчики считаем ИЗ получателей (точно), а не из денормализованного агрегата
        for st in ("sent", "failed", "blocked"):
            d[st] = self._c.execute(
                "SELECT COUNT(*) FROM broadcast_recipients WHERE broadcast_id=? AND status=?",
                (bid, st)).fetchone()[0]
        return d

    def set_broadcast_status(self, bid, status):
        with self._tx() as c:
            c.execute("UPDATE broadcasts SET status=? WHERE id=?", (status, bid))

    def running_broadcast(self):
        r = self._c.execute("SELECT id FROM broadcasts WHERE status='running' ORDER BY id DESC LIMIT 1").fetchone()
        return r[0] if r else None

    def funnel_stats(self, funnel_key):
        """Воронка по шагам: вошло → получил A0/B0 → кликнул гайд → registered + где сейчас."""
        q1 = lambda sql, *a: self._c.execute(sql, a).fetchone()[0]
        entered = q1("SELECT COUNT(*) FROM tags WHERE tag=?", f"f_{funnel_key}")
        entrants = {r[0] for r in self._c.execute("SELECT user_id FROM tags WHERE tag=?", (f"f_{funnel_key}",))}

        def sent_node(node):
            return q1("SELECT COUNT(DISTINCT user_id) FROM events WHERE kind='send' AND payload_min=?",
                      f"{funnel_key}/{node}")

        got_b0 = sent_node("B0")
        clicked_guide = q1("SELECT COUNT(DISTINCT user_id) FROM events WHERE kind='click' AND payload_min=?",
                           f"{funnel_key}/B0")
        registered = q1("""SELECT COUNT(*) FROM tags t WHERE t.tag='registered'
                           AND t.user_id IN (SELECT user_id FROM tags WHERE tag=?)""", f"f_{funnel_key}")
        opted = q1("""SELECT COUNT(*) FROM contacts WHERE opted_out=1
                      AND user_id IN (SELECT user_id FROM tags WHERE tag=?)""", f"f_{funnel_key}")
        # где сейчас (по текущему узлу funnel_state)
        by_node = {}
        for r in self._c.execute("SELECT node, COUNT(*) FROM funnel_state WHERE funnel_key=? GROUP BY node",
                                 (funnel_key,)):
            by_node[r[0]] = r[1]
        return {"funnel": funnel_key, "entered": entered, "got_b0": got_b0,
                "clicked_guide": clicked_guide, "registered": registered,
                "opted_out": opted, "by_node": by_node}

    def contact_card(self, user_id):
        c = self._c.execute("SELECT * FROM contacts WHERE user_id=?", (user_id,)).fetchone()
        states = [dict(r) for r in self._c.execute(
            "SELECT funnel_key,node,entered_at FROM funnel_state WHERE user_id=?", (user_id,))]
        jobs = self._c.execute("SELECT COUNT(*) FROM scheduled_jobs WHERE user_id=? AND status='pending'",
                               (user_id,)).fetchone()[0]
        return {"contact": dict(c) if c else None, "tags": sorted(self.tags(user_id)),
                "states": states, "pending_jobs": jobs}

    def remove_tag(self, user_id, tag):
        with self._tx() as c:
            c.execute("DELETE FROM tags WHERE user_id=? AND tag=?", (user_id, tag))

    def reset_contact(self, user_id, funnel_key):
        """Сброс контакта в воронке: снять состояние/джобы/registered, чтобы прошёл заново."""
        with self._tx() as c:
            c.execute("DELETE FROM funnel_state WHERE user_id=? AND funnel_key=?", (user_id, funnel_key))
            c.execute("UPDATE scheduled_jobs SET status='cancelled' WHERE user_id=? AND funnel_key=? AND status='pending'",
                      (user_id, funnel_key))
            c.execute("UPDATE contacts SET opted_out=0 WHERE user_id=?", (user_id,))
            c.execute("DELETE FROM tags WHERE user_id=? AND tag='registered'", (user_id,))

    # --- ИИ-ответчик: диалог + kill-switch (см. app/ai_responder.py) ---
    def ai_log(self, user_id, role, text):
        """role: 'user' (лид) | 'assistant' (ИИ) | 'owner' (владелец вручную через /dm).
        text обрезаем до 2000 - это лог, не источник для дальних выборок."""
        if role not in ("user", "assistant", "owner"):
            raise ValueError(f"bad ai_dialog role: {role}")
        with self._tx() as c:
            c.execute("INSERT INTO ai_dialog(user_id,role,text,ts) VALUES(?,?,?,?)",
                      (user_id, role, str(text)[:2000], _time.time()))

    def ai_history(self, user_id, limit=12):
        """Последние limit сообщений в хронологическом порядке, text обрезан до 800
        (бюджет промпта - см. generate_reply)."""
        rows = self._c.execute(
            "SELECT role, text FROM ai_dialog WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)).fetchall()
        return [{"role": r["role"], "text": (r["text"] or "")[:800]} for r in reversed(rows)]

    def ai_has_replied_before(self, user_id):
        """Отвечали ли этому человеку РАНЬШЕ (ИИ или владелец вручную) - по ВСЕЙ
        истории, не по окну ai_history(12): бот здоровался в каждом ответе, а на
        длинном диалоге окно может состоять из одних user-строк, и «первый ответ»
        определялся бы ложно. Здесь - точный факт из БД."""
        r = self._c.execute(
            "SELECT 1 FROM ai_dialog WHERE user_id=? AND role IN ('assistant','owner') LIMIT 1",
            (user_id,)).fetchone()
        return r is not None

    def ai_unanswered_with_ids(self, user_id):
        """(id, text) необработанных user-сообщений (id > answered_upto), в порядке id.
        ЕДИНЫЙ снимок для всего _ai_task: и промпт, и overflow-форвард, и граница курсора
        берутся из ОДНОГО этого списка. max_id = id последнего элемента (не MAX по всей
        БД) - иначе покрыл бы сообщения, записавшиеся ПОСЛЕ снимка, и они бы потерялись.
        Курсор в ai_kv, а НЕ «по последней assistant»: закрывает гонку, когда лид пишет Б
        пока идёт вызов Claude на А (А логирует assistant с id>Б)."""
        after = self.ai_answered_upto_get(user_id)
        rows = self._c.execute(
            "SELECT id, text FROM ai_dialog WHERE user_id=? AND role='user' AND id>? ORDER BY id",
            (user_id, after)).fetchall()
        return [(r["id"], r["text"]) for r in rows]

    def ai_unanswered(self, user_id):
        """Тексты необработанных user-сообщений (обёртка над ai_unanswered_with_ids).
        Дебаунс-коалесценция: несколько быстрых сообщений схлопываются в один вызов."""
        return [text for _id, text in self.ai_unanswered_with_ids(user_id)]

    def ai_max_user_id(self, user_id):
        """MAX(id) среди user-строк юзера СЕЙЧАС. Оставлен для совместимости, но в
        _ai_task больше НЕ используется (там max_id = id последнего из СНЯТОГО списка,
        см. ai_unanswered_with_ids) - MAX по всей БД покрыл бы записи после снимка."""
        r = self._c.execute(
            "SELECT MAX(id) FROM ai_dialog WHERE user_id=? AND role='user'", (user_id,)).fetchone()
        return r[0] or 0

    def ai_answered_upto_get(self, user_id):
        v = self.ai_kv_get(f"answered_upto:{user_id}")
        return int(v) if v is not None else 0

    def ai_answered_upto_set(self, user_id, max_id):
        """Сдвигать ТОЛЬКО не назад (защита от гонки: _ai_task под _ai_lock vs cmd_dm
        вне лока идут в РАЗНЫХ потоках пула to_thread, sqlite отпускает GIL). Read cur +
        compare + write ДОЛЖНЫ быть в одной транзакции, иначе курсор может уехать назад
        -> повторный ответ лиду. INSERT OR IGNORE создаёт строку, атомарный UPDATE с
        предикатом CAST(v)<? гарантирует монотонность под _lock."""
        k = f"answered_upto:{user_id}"
        with self._tx() as c:
            c.execute("INSERT OR IGNORE INTO ai_kv(k,v) VALUES(?,?)", (k, str(max_id)))
            c.execute("UPDATE ai_kv SET v=? WHERE k=? AND CAST(v AS INTEGER) < ?",
                      (str(max_id), k, max_id))

    def ai_counts(self, user_id):
        """(ответов ИИ юзеру за час, за 24ч у юзера, за 24ч глобально).
        Считаем по role='assistant' - сколько раз ИИ реально ответил (не сколько
        написал лид), это и есть лимитируемый ресурс."""
        now = _time.time()
        hour = self._c.execute(
            "SELECT COUNT(*) FROM ai_dialog WHERE user_id=? AND role='assistant' AND ts>?",
            (user_id, now - 3600)).fetchone()[0]
        day = self._c.execute(
            "SELECT COUNT(*) FROM ai_dialog WHERE user_id=? AND role='assistant' AND ts>?",
            (user_id, now - 86400)).fetchone()[0]
        glob = self._c.execute(
            "SELECT COUNT(*) FROM ai_dialog WHERE role='assistant' AND ts>?",
            (now - 86400,)).fetchone()[0]
        return (hour, day, glob)

    def ai_kv_get(self, k, default=None):
        r = self._c.execute("SELECT v FROM ai_kv WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default

    def ai_kv_set(self, k, v):
        with self._tx() as c:
            c.execute("INSERT INTO ai_kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                      (k, str(v)))
