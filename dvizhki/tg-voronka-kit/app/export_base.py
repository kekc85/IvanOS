"""Экспорт базы контактов движка воронок в универсальный CSV/JSON.

Формат совместим с импортом обратно (round-trip) И с переносом в платформу курса / конструктор воронок /
любой сервис: колонки user_id, username, first_name, source_funnel, tags, opted_out,
banned_bot, joined_at. Теги через «;». Один контакт = одна строка.

Запуск: python3 -m app.export_base [csv|json] [путь]
  по умолчанию: CSV в export-YYYYMMDD.csv рядом с БД
"""
import sys, csv, json, io, time


COLUMNS = ["user_id", "username", "first_name", "source_funnel",
           "tags", "opted_out", "banned_bot", "joined_at"]


def rows(db):
    tags_by_user = {}
    for r in db._c.execute("SELECT user_id, tag FROM tags"):
        tags_by_user.setdefault(r["user_id"], []).append(r["tag"])
    for c in db._c.execute("SELECT * FROM contacts ORDER BY user_id"):
        yield {
            "user_id": c["user_id"],
            "username": c["username"] or "",
            "first_name": c["first_name"] or "",
            "source_funnel": c["source_funnel"] or "",
            "tags": ";".join(sorted(tags_by_user.get(c["user_id"], []))),
            "opted_out": int(c["opted_out"] or 0),
            "banned_bot": int(c["banned_bot"] or 0),
            "joined_at": c["joined_at"] or 0,
        }


def to_csv(db):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS)
    w.writeheader()
    n = 0
    for row in rows(db):
        w.writerow(row); n += 1
    return buf.getvalue(), n


def to_json(db):
    data = list(rows(db))
    return json.dumps({"contacts": data}, ensure_ascii=False, indent=1), len(data)


def main():
    fmt = sys.argv[1] if len(sys.argv) > 1 else "csv"
    from .db import DB
    from .config import DB_PATH
    import os
    db = DB(DB_PATH)
    default = os.path.join(os.path.dirname(DB_PATH), f"export-{time.strftime('%Y%m%d-%H%M')}.{fmt}")
    path = sys.argv[2] if len(sys.argv) > 2 else default
    text, n = (to_csv(db) if fmt == "csv" else to_json(db))
    open(path, "w", encoding="utf-8").write(text)
    print(f"экспортировано контактов: {n} → {path}")
    print("формат универсальный: колонки user_id/username/first_name/source_funnel/tags/...")
    print("грузится обратно (import_base) и в платформу курса / конструктор воронок (маппинг колонок)")


if __name__ == "__main__":
    main()
