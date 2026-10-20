"""Тесты статистики воронок и админ-операций по контакту.
Запуск: .venv/bin/python -m tests.test_stats
"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DB
from app.runtime import Runtime
from engine.interpreter import Event
from engine.model import deeplink as _dl

_p=_f=0
def check(n,c):
    global _p,_f
    if c: _p+=1
    else: _f+=1; print(f"  FAIL: {n}")

db=DB(tempfile.mktemp(suffix=".sqlite"))
rt=Runtime(db)
for _i in rt.interp.values(): _i.registered_by_click = True  # тест клик-прокси режима (не дефолт с 09.07)
K="DEMO"

def full_pass(uid, register=False):
    """Прогнать юзера: вход → Забрать → клик гайда (+опц. рег)."""
    for s in rt.apply(uid,K,Event("enter",rt.now())): db.event(uid,"send",f"{K}/{s.node_key}")
    for s in rt.apply(uid,K,Event("button",rt.now(),payload="Забрать")): db.event(uid,"send",f"{K}/{s.node_key}")
    gift=rt.funnels[K].nodes["B0"].url_button.url
    db.event(uid,"click",f"{K}/B0")
    rt.apply(uid,K,Event("click",rt.now(),payload=gift))
    if register:
        rt.apply(uid,K,Event("click",rt.now(),payload=_dl("KEY")))

# 3 вошли, 2 забрали гайд+кликнули, 1 зарегался
full_pass(1, register=True)
full_pass(2)
# третий только вошёл (A0), не нажал Забрать
for s in rt.apply(3,K,Event("enter",rt.now())): db.event(3,"send",f"{K}/{s.node_key}")

s=db.funnel_stats(K)
check("вошло 3", s["entered"]==3)
check("гайд забрали 2 (B0)", s["got_b0"]==2)
check("кликнули гайд 2", s["clicked_guide"]==2)
check("зарегался 1", s["registered"]==1)
check("by_node содержит распределение", isinstance(s["by_node"],dict) and sum(s["by_node"].values())>=3)

# карточка контакта
card=db.contact_card(1)
check("карточка: registered в тегах", "registered" in card["tags"])
check("карточка: состояние в воронке есть", any(st["funnel_key"]==K for st in card["states"]))

# reset
db.reset_contact(1, K)
check("после reset: состояние снято", db.get_state(1,K) is None)
check("после reset: registered снят", "registered" not in db.tags(1))
check("после reset: opted_out=0", db.flags(1)[0] is False)

# теги
db.add_tag(9,"vip"); check("добавлен тег", "vip" in db.tags(9))
db.remove_tag(9,"vip"); check("снят тег", "vip" not in db.tags(9))

print(f"\nИтог статистика: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
