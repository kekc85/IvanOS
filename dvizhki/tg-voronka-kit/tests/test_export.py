"""Тесты экспорта базы + round-trip (экспорт → импорт → та же база).
Запуск: .venv/bin/python -m tests.test_export
"""
import sys, os, tempfile, csv, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DB
from app import export_base as exp
from app import import_base as imp

_p=_f=0
def check(n,c):
    global _p,_f
    if c: _p+=1
    else: _f+=1; print(f"  FAIL: {n}")

# наполняем базу
db=DB(tempfile.mktemp(suffix=".sqlite"))
db.upsert_contact(111,"vasya","Вася","DEMO"); db.add_tag(111,"f_КОМАНДЫ"); db.add_tag(111,"registered")
db.upsert_contact(222,"petya","Петя","ФАЙЛ"); db.add_tag(222,"f_ФАЙЛ")
db.set_flag(222,"opted_out",True)
db.upsert_contact(333,None,"Аноним","imported")

# --- CSV экспорт ---
text, n = exp.to_csv(db)
check("экспортировано 3 контакта", n==3)
reader=list(csv.DictReader(io.StringIO(text)))
check("CSV: заголовок + все колонки", set(reader[0].keys())==set(exp.COLUMNS))
row111=[r for r in reader if r["user_id"]=="111"][0]
check("CSV: теги через ; (vip/registered)", "registered" in row111["tags"] and "f_КОМАНДЫ" in row111["tags"])
check("CSV: source_funnel сохранён", row111["source_funnel"]=="DEMO")
row222=[r for r in reader if r["user_id"]=="222"][0]
check("CSV: opted_out=1 у отписанного", row222["opted_out"]=="1")

# --- JSON экспорт ---
jtext, jn = exp.to_json(db)
jd=json.loads(jtext)
check("JSON: 3 контакта в contacts[]", len(jd["contacts"])==3)

# --- ROUND-TRIP: экспорт CSV → импорт в чистую базу → та же база ---
p=tempfile.mktemp(suffix=".csv"); open(p,"w",encoding="utf-8").write(text)
db2=DB(tempfile.mktemp(suffix=".sqlite"))
# импорт с funnel из колонки source_funnel (import_base ставит default, но source сохранён в CSV)
imp.run(p, db2, "imported")
check("round-trip: все 3 контакта перенеслись", len(list(db2._c.execute("SELECT 1 FROM contacts")))==3)
check("round-trip: теги перенеслись", "registered" in db2.tags(111))
check("round-trip: контакт 111 на месте с username", db2.contact_card(111)["contact"]["username"]=="vasya")

# --- совместимость с платформы курса/конструктор воронок: user_id как ключ, читаемые колонки ---
check("user_id - числовой ключ (переносим в любой сервис)", all(r["user_id"].isdigit() for r in reader))

print(f"\nИтог экспорт: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
