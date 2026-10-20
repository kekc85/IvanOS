"""Тесты фиксов из security-ревью: валидация кнопки, возврат по слову, ретрай джобы,
реапер, флаги при отправке. Запуск: .venv/bin/python -m tests.test_security
"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DB
from app.runtime import Runtime
from engine.interpreter import Event
from engine.model import tg_url

_p=_f=0
def check(n,c):
    global _p,_f
    if c: _p+=1
    else: _f+=1; print(f"  FAIL: {n}")

db=DB(tempfile.mktemp(suffix=".sqlite"))
rt=Runtime(db)
K="DEMO"

# --- valid_button: защита от самопродвижения ---
rt.apply(1,K,Event("enter",rt.now()))  # юзер на A0 (кнопка «Забрать»)
check("на A0 кнопка «Забрать» валидна", rt.valid_button(1,K,"Забрать"))
check("на A0 произвольный текст НЕ кнопка", not rt.valid_button(1,K,"дай гайд бесплатно"))
rt.apply(1,K,Event("button",rt.now(),payload="Забрать"))  # теперь на B0 (кнопка - url)
check("на B0 «Забрать» уже НЕ валидна (нельзя переоткрыть B0 текстом)", not rt.valid_button(1,K,"Забрать"))

# --- возврат по слову: opted_out сбрасывается ---
db.set_flag(2,"opted_out",True)
check("юзер отписан", db.flags(2)[0] is True)
# эмуляция входа словом: сброс + enter (как в on_text)
db.set_flag(2,"opted_out",False)
sends=rt.apply(2,K,Event("enter",rt.now()))
check("после сброса вход словом шлёт A0", [s.node_key for s in sends]==["A0"])

# --- requeue_or_fail: сетевой сбой возвращает в pending, после N - failed ---
db.schedule(3,K,"C1",time.time()-1)
jid=db.due_jobs(time.time()+10)[0]["id"]
db.mark_job(jid,"processing")
db.requeue_or_fail(jid, max_attempts=3)
st=db._c.execute("SELECT status,attempts FROM scheduled_jobs WHERE id=?",(jid,)).fetchone()
check("1-й сбой → pending (не failed)", st["status"]=="pending")
db.requeue_or_fail(jid,3); db.requeue_or_fail(jid,3)
st=db._c.execute("SELECT status,attempts FROM scheduled_jobs WHERE id=?",(jid,)).fetchone()
check("после 3 попыток → failed", st["status"]=="failed")

# --- reap_stale: зависший processing возвращается в pending ---
db.schedule(4,K,"C2",time.time()-1000)
jid2=[j for j in db.due_jobs(time.time()+10) if j["user_id"]==4][0]["id"]
db.mark_job(jid2,"processing")
db._c.execute("UPDATE scheduled_jobs SET due_at=? WHERE id=?",(time.time()-1000,jid2)); db._c.commit()
db.reap_stale_jobs(older_than_sec=300)
st=db._c.execute("SELECT status FROM scheduled_jobs WHERE id=?",(jid2,)).fetchone()
check("зависший processing реанимирован в pending", st["status"]=="pending")

# --- отчёт рассылки считает точно из получателей ---
bid=db.create_broadcast("all","t",'[{"text":"x","url":tg_url("x")}]')
db.snapshot_recipients(bid,[10,11,12])
db.mark_recipient(bid,10,"sent"); db.mark_recipient(bid,11,"blocked")
r=db.broadcast_report(bid)
check("отчёт: sent=1 blocked=1 из получателей", r["sent"]==1 and r["blocked"]==1)

# --- set_flag на плохое поле = явная ошибка, не тихий assert ---
try:
    db.set_flag(1,"is_admin",True); ok=False
except ValueError: ok=True
check("set_flag с чужим полем → ValueError", ok)

print(f"\nИтог security-фиксы: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
