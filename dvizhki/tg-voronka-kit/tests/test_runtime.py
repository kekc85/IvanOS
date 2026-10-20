"""E2E через реальный слой БД (runtime + sqlite + interpreter).
Проверяет, что состояние, теги, джобы и гварды переживают запись/чтение в БД.
Запуск: .venv/bin/python -m tests.test_runtime
"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import DB
from app.runtime import Runtime
from engine.interpreter import Event
from engine.timing import MSK
from datetime import datetime
from engine.model import deeplink as _dl

_p = _f = 0
def check(name, cond):
    global _p, _f
    if cond: _p += 1
    else: _f += 1; print(f"  FAIL: {name}")

db = DB(tempfile.mktemp(suffix=".sqlite"))
rt = Runtime(db)
for _i in rt.interp.values(): _i.registered_by_click = True  # тест клик-прокси режима (не дефолт с 09.07)
key = "DEMO"
uid = 12345

# 1) вход → A0 отправлен, тег источника, состояние в БД
sends = rt.apply(uid, key, Event("enter", rt.now()))
check("вход шлёт A0", [s.node_key for s in sends] == ["A0"])
check("тег источника проставлен", f"f_{key}" in db.tags(uid))
check("состояние = A0 в БД", db.get_state(uid, key) == "A0")

# 2) нажал «Забрать» → B0, запланирован TECH? нет - TECH по клику. B0 отправлен
sends = rt.apply(uid, key, Event("button", rt.now(), payload="Забрать"))
check("кнопка Забрать шлёт B0", [s.node_key for s in sends] == ["B0"])
check("состояние = B0", db.get_state(uid, key) == "B0")

# 3) клик по ссылке гайда → TECH (не шлётся) + запланирован C1
gift = rt.funnels[key].nodes["B0"].url_button.url
sends = rt.apply(uid, key, Event("click", rt.now(), payload=gift))
check("клик по гайду ничего не шлёт (TECH служебный)", sends == [])
pend = db.due_jobs(time.time() + 10**9)
check("запланирован C1 после клика", any(j["node"] == "C1" for j in pend))

# 4) прогон джоб по времени (эмуляция планировщика) → полный дожим
def drain():
    got = []
    for _ in range(50):
        due = db.due_jobs(time.time() + 10**9)
        if not due: break
        j = min(due, key=lambda x: x["due_at"])
        db.mark_job(j["id"], "done")
        s = rt.apply(j["user_id"], j["funnel_key"], Event("timeout", rt.now(), node_key=j["node"]))
        got += [x.node_key for x in s]
    return got
chain = drain()
check("дожим прошёл C1..C4,D1..D7", chain == ["C1","C2","C3","C4","D1","D2","D3","D4","D5","D6","D7"])

# 5) новый юзер: регистрируется на событие на C2 → дожим обрывается
uid2 = 777
rt.apply(uid2, key, Event("enter", rt.now()))
rt.apply(uid2, key, Event("button", rt.now(), payload="Забрать"))
rt.apply(uid2, key, Event("click", rt.now(), payload=gift))
# докрутить до C2
for _ in range(3):
    due = db.due_jobs(time.time()+10**9);
    js=[j for j in due if j["user_id"]==uid2]
    if not js: break
    j=min(js,key=lambda x:x["due_at"]); db.mark_job(j["id"],"done")
    rt.apply(uid2,key,Event("timeout",rt.now(),node_key=j["node"]))
    if j["node"]=="C2": break
# клик событие
rt.apply(uid2, key, Event("click", rt.now(), payload=_dl("KEY")))
check("registered проставлен", "registered" in db.tags(uid2))
left = [j for j in db.due_jobs(time.time()+10**9) if j["user_id"]==uid2]
check("после регистрации pending-джобы погашены", left == [])

# 6) /stop гасит всё
uid3 = 888
rt.apply(uid3, key, Event("enter", rt.now()))
rt.apply(uid3, key, Event("button", rt.now(), payload="Забрать"))
rt.apply(uid3, key, Event("click", rt.now(), payload=gift))
rt.apply(uid3, key, Event("stop", rt.now()))
opt,_ = db.flags(uid3)
check("opted_out выставлен", opt)
check("джобы после stop погашены", [j for j in db.due_jobs(time.time()+10**9) if j["user_id"]==uid3] == [])

# 7) дедуп джоб: повторная постановка того же узла не плодит дубль
before = len(db.due_jobs(time.time()+10**9))
db.schedule(uid, key, "D3", time.time()+100)
db.schedule(uid, key, "D3", time.time()+100)
after = len([j for j in db.due_jobs(time.time()+10**9) if j["node"]=="D3" and j["user_id"]==uid])
check("дедуп: один pending D3, не два", after <= 1)

# 8) deep-link source-тег: разбор payload + резолв funnel-части (не ломает вход)
from app.runtime import parse_start_payload
check("payload без тега = (слово, '')", parse_start_payload("event") == ("event", ""))
check("payload с тегом → база + тег lower", parse_start_payload("event-cpZAPAS") == ("event", "cpzapas"))
check("payload пустой", parse_start_payload("") == ("", ""))
check("payload registered без дефиса не режется", parse_start_payload("registered") == ("registered", ""))
check("несколько дефисов → тег целиком", parse_start_payload("event-cp-zapas") == ("event", "cp-zapas"))
# funnel-часть тегированного payload резолвится так же, как голая
b_bare, _ = parse_start_payload("demo")
b_tag, tg = parse_start_payload("demo-igreel")
check("тегированный payload резолвит ту же воронку, что голый",
      rt.resolve(b_bare) == rt.resolve(b_tag) == key and tg == "igreel")

print(f"\nИтог runtime: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
