"""Тесты импортёра базы: CSV/JSON, разные названия колонок, идемпотентность.
Запуск: .venv/bin/python -m tests.test_import
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DB
from app import import_base as imp

_p=_f=0
def check(n,c):
    global _p,_f
    if c: _p+=1
    else: _f+=1; print(f"  FAIL: {n}")

def tmp(content, suffix):
    p=tempfile.mktemp(suffix=suffix); open(p,"w",encoding="utf-8").write(content); return p

# --- CSV с нестандартными колонками (tg_id, login, fio) ---
csv1 = tmp("tg_id,login,fio,tags\n111,vasya,Вася,vip;paid\n222,petya,Петя,\n", ".csv")
db = DB(tempfile.mktemp(suffix=".sqlite"))
r = imp.run(csv1, db, "imported")
check("CSV: импортировано 2", r["imported"]==2)
check("CSV: контакт 111 создан", db.contact_card(111)["contact"] is not None)
check("CSV: теги разобраны (vip,paid)", {"vip","paid"} <= db.tags(111))
check("CSV: source_funnel=imported", db.contact_card(111)["contact"]["source_funnel"]=="imported")

# --- JSON вида {"users":[...]} с полем telegram_id ---
js = tmp('{"users":[{"telegram_id":333,"username":"kolya","first_name":"Коля"},{"telegram_id":444,"name":"Дима"}]}', ".json")
r2 = imp.run(js, db, "imported")
check("JSON: импортировано 2", r2["imported"]==2)
check("JSON: контакт 333 с username", db.contact_card(333)["contact"]["username"]=="kolya")

# --- пропуск строк без id ---
bad = tmp("user_id,name\n,БезИД\n555,Норм\n", ".csv")
r3 = imp.run(bad, db, "imported")
check("строка без id пропущена", r3["skipped"]==1 and r3["imported"]==1)

# --- идемпотентность: повторный импорт не дублит контакты ---
before = len(list(db._c.execute("SELECT 1 FROM contacts")))
imp.run(csv1, db, "imported")
after = len(list(db._c.execute("SELECT 1 FROM contacts")))
check("повторный импорт не плодит дубли контактов", before==after)

# --- импортированные попадают в сегмент рассылки ---
check("импортированные достижимы через сегмент all", 111 in db.segment_users("all"))

print(f"\nИтог импорт: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
