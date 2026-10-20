"""Импортёр базы из конструктора воронок (или любой выгрузки) в контакты движка.

Гибкий: принимает CSV или JSON, сам находит колонки user_id / username / имя /
теги (разные выгрузки называют по-разному). Идемпотентен - повторный прогон не
дублит. Ставит source_funnel (чтобы контакт попал в сегменты рассылки).

🔴 Достижимость в ЛС: импорт кладёт контакта в БД, но написать боту можно только
тем, у кого УЖЕ открыт диалог с нашим ботом (тот же токен). У кого не открыт -
рассылка получит 403 и пометит banned_bot (это норма, отфильтруется само).

Запуск: python3 -m app.import_base <файл.csv|файл.json> [--funnel ИМЯ]
"""
import sys, csv, json, io

# синонимы колонок (нижний регистр)
ID_KEYS = ("user_id", "tg_id", "telegram_id", "telegram_user_id", "chat_id", "id", "uid")
USER_KEYS = ("username", "user_name", "login", "nick", "handle")
NAME_KEYS = ("first_name", "firstname", "name", "fio", "имя")
TAG_KEYS = ("tags", "tag", "labels", "метки", "теги")


def _pick(row, keys):
    low = {str(k).lower().strip(): v for k, v in row.items()}
    for k in keys:
        if k in low and str(low[k]).strip() not in ("", "None", "null"):
            return str(low[k]).strip()
    return None


def _rows(path):
    text = open(path, encoding="utf-8", errors="ignore").read()
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        data = json.loads(text)
        if isinstance(data, dict):
            # {"users":[...]} / {"contacts":[...]} / {"data":[...]}
            for k in ("users", "contacts", "data", "items", "result"):
                if isinstance(data.get(k), list):
                    data = data[k]; break
            else:
                data = [data]
        return data
    # CSV (авто-делимитер , или ;)
    delim = ";" if text.count(";") > text.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def run(path, db, default_funnel="imported"):
    rows = _rows(path)
    imported = skipped = tagged = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_id = _pick(row, ID_KEYS)
        if not raw_id or not str(raw_id).lstrip("-").isdigit():
            skipped += 1
            continue
        uid = int(raw_id)
        username = _pick(row, USER_KEYS)
        name = _pick(row, NAME_KEYS)
        db.upsert_contact(uid, username, name, default_funnel)
        imported += 1
        raw_tags = _pick(row, TAG_KEYS)
        if raw_tags:
            for t in str(raw_tags).replace(";", ",").split(","):
                t = t.strip()
                if t:
                    db.add_tag(uid, t); tagged += 1
    return {"imported": imported, "skipped": skipped, "tags_added": tagged, "total_rows": len(rows)}


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 -m app.import_base <файл.csv|json> [--funnel ИМЯ]")
        sys.exit(1)
    path = sys.argv[1]
    funnel = "imported"
    if "--funnel" in sys.argv:
        funnel = sys.argv[sys.argv.index("--funnel") + 1]
    from .db import DB
    from .config import DB_PATH
    db = DB(DB_PATH)
    r = run(path, db, funnel)
    print(f"импортировано: {r['imported']} из {r['total_rows']} строк | "
          f"пропущено (без id): {r['skipped']} | тегов добавлено: {r['tags_added']}")


if __name__ == "__main__":
    main()
