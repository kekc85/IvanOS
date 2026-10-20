"""Очередь публикаций. SQLite, потому что она уже есть в питоне и живёт файлом.

Главная гарантия слоя - идемпотентность. Она стоит на двух замках:

  замок 1 (на входе)   уникальный ключ единицы. Один и тот же пост, добавленный
                       второй раз, не создаёт вторую строку, а возвращает первую
  замок 2 (на выдаче)  захват строки атомарным UPDATE со сверкой статуса. Две
                       параллельные копии движка не заберут одну единицу дважды,
                       и повторный запуск не отправит уже опубликованное

Статусы: queued -> sending -> published | retry | failed
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id          TEXT PRIMARY KEY,
    idem_key    TEXT NOT NULL UNIQUE,
    platform    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    media       TEXT NOT NULL DEFAULT '[]',
    publish_at  REAL NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT NOT NULL DEFAULT '',
    remote_id   TEXT NOT NULL DEFAULT '',
    remote_url  TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_due ON posts (status, publish_at);
"""

ACTIVE = ("queued", "retry")


@dataclass
class Item:
    id: str
    idem_key: str
    platform: str
    kind: str
    text: str
    media: list[str]
    publish_at: float
    status: str
    attempts: int
    last_error: str
    remote_id: str
    remote_url: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Item":
        return cls(
            id=row["id"],
            idem_key=row["idem_key"],
            platform=row["platform"],
            kind=row["kind"],
            text=row["text"],
            media=json.loads(row["media"] or "[]"),
            publish_at=row["publish_at"],
            status=row["status"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            remote_id=row["remote_id"],
            remote_url=row["remote_url"],
        )


def make_idem_key(platform: str, kind: str, text: str, media: Iterable[str], publish_at: float) -> str:
    """Отпечаток единицы. Тот же пост в ту же минуту на ту же площадку = тот же ключ.

    Минута, а не секунда: человек, повторивший команду через пару секунд,
    имел в виду ту же публикацию, а не вторую такую же
    """
    payload = "|".join(
        [platform, kind, text, "\n".join(sorted(media)), str(int(publish_at // 60))]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


class Queue:
    def __init__(self, path: Path | str):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ── вход ─────────────────────────────────────────────────────────────
    def add(
        self,
        platform: str,
        kind: str,
        text: str = "",
        media: Iterable[str] | None = None,
        publish_at: float | None = None,
        idem_key: str | None = None,
    ) -> tuple[str, bool]:
        """Кладёт единицу в очередь. Возвращает (id, создана_ли_новая)"""
        media_list = list(media or [])
        when = float(publish_at if publish_at is not None else time.time())
        key = idem_key or make_idem_key(platform, kind, text, media_list, when)
        found = self.conn.execute("SELECT id FROM posts WHERE idem_key = ?", (key,)).fetchone()
        if found:
            return found["id"], False
        now = time.time()
        new_id = uuid.uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO posts (id, idem_key, platform, kind, text, media, publish_at,"
            " status, attempts, last_error, remote_id, remote_url, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,'queued',0,'','','',?,?)",
            (new_id, key, platform, kind, text, json.dumps(media_list, ensure_ascii=False), when, now, now),
        )
        return new_id, True

    # ── выдача ───────────────────────────────────────────────────────────
    def due(self, now: float | None = None, platform: str = "") -> list[Item]:
        now = float(now if now is not None else time.time())
        sql = (
            "SELECT * FROM posts WHERE status IN (?,?) AND publish_at <= ?"
            + (" AND platform = ?" if platform else "")
            + " ORDER BY publish_at ASC"
        )
        args: list[Any] = [ACTIVE[0], ACTIVE[1], now]
        if platform:
            args.append(platform)
        return [Item.from_row(r) for r in self.conn.execute(sql, args)]

    def claim(self, item_id: str) -> bool:
        """Атомарный захват: строку можно забрать, только пока она ещё активна.

        Это и есть второй замок идемпотентности. Опубликованную строку
        не заберёт ни повтор запуска, ни вторая параллельная копия движка
        """
        cur = self.conn.execute(
            "UPDATE posts SET status='sending', attempts = attempts + 1, updated_at = ?"
            " WHERE id = ? AND status IN (?,?)",
            (time.time(), item_id, ACTIVE[0], ACTIVE[1]),
        )
        return cur.rowcount == 1

    # ── итоги ────────────────────────────────────────────────────────────
    def mark_published(self, item_id: str, remote_id: str = "", remote_url: str = "") -> None:
        self.conn.execute(
            "UPDATE posts SET status='published', remote_id=?, remote_url=?, last_error='',"
            " updated_at=? WHERE id=?",
            (remote_id, remote_url, time.time(), item_id),
        )

    def mark_retry(self, item_id: str, delay: float, error: str) -> None:
        self.conn.execute(
            "UPDATE posts SET status='retry', publish_at=?, last_error=?, updated_at=? WHERE id=?",
            (time.time() + max(0.0, delay), error[:500], time.time(), item_id),
        )

    def mark_failed(self, item_id: str, error: str) -> None:
        self.conn.execute(
            "UPDATE posts SET status='failed', last_error=?, updated_at=? WHERE id=?",
            (error[:500], time.time(), item_id),
        )

    def revive(self, item_id: str = "") -> int:
        """Вернуть упавшее в очередь. Без аргумента - всё упавшее"""
        if item_id:
            cur = self.conn.execute(
                "UPDATE posts SET status='queued', publish_at=?, updated_at=? WHERE id=? AND status IN ('failed','sending')",
                (time.time(), time.time(), item_id),
            )
        else:
            cur = self.conn.execute(
                "UPDATE posts SET status='queued', publish_at=?, updated_at=? WHERE status IN ('failed','sending')",
                (time.time(), time.time()),
            )
        return cur.rowcount

    # ── чтение ───────────────────────────────────────────────────────────
    def get(self, item_id: str) -> Item | None:
        row = self.conn.execute("SELECT * FROM posts WHERE id = ?", (item_id,)).fetchone()
        return Item.from_row(row) if row else None

    def all(self, limit: int = 50) -> list[Item]:
        rows = self.conn.execute(
            "SELECT * FROM posts ORDER BY publish_at DESC LIMIT ?", (limit,)
        )
        return [Item.from_row(r) for r in rows]

    def counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) c FROM posts GROUP BY status")
        return {r["status"]: r["c"] for r in rows}


def human_time(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
