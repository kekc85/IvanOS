"""Прогон эталона КЛОД через движок в ускоренном времени.

Симулирует полный путь юзера: заявка → «Забрать» → клик по гайду → 7-дневный
дожим (юзер НЕ регистрируется). Печатает всю ленту с временами. Это proof, что
интерпретатор разворачивает нашу воронку 1:1 (Фаза 3, критерий).

Запуск: python3 -m tests.simulate_klod
"""
import sys, os, heapq
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from engine.timing import MSK
from engine.importer import load_valid
from engine.interpreter import Interpreter, State, Event
from engine.model import deeplink as _dl


def run(funnel_path: str, register_at=None):
    f = load_valid(funnel_path)
    interp = Interpreter(f)
    st = State(funnel_key=f.key)

    t0 = datetime(2026, 7, 3, 14, 0, tzinfo=MSK)   # заявка в 14:00 МСК
    timeline = []                                   # (dt, node_key, кнопки)
    pending = []                                    # мини-очередь: (due_ts, node_key, delete_others)
    seq = 0

    def apply(dec, now):
        nonlocal seq
        for s in dec.sends:
            btn = " · ".join(f"[{b.text}]" for b in s.buttons) or "-"
            timeline.append((s.at, s.node_key, btn))
        for c in dec.cancels:
            pending.clear()
        for sc in dec.schedules:
            if sc.delete_others:
                pending.clear()
            seq += 1
            heapq.heappush(pending, (sc.due_at.timestamp(), seq, sc.node_key))

    # 1) заявка → A0
    apply(interp.handle(st, Event("enter", t0)), t0)
    # 2) нажал «Забрать» через 2 мин → B0
    t_btn = t0.fromtimestamp(t0.timestamp() + 120, tz=MSK)
    apply(interp.handle(st, Event("button", t_btn, payload="Забрать")), t_btn)
    # 3) клик по ссылке гайда через 5 мин → TECH (+ вся дальнейшая цепочка по таймерам)
    b0 = f.nodes["B0"]
    gift_url = b0.url_button.url
    t_click = t0.fromtimestamp(t0.timestamp() + 300, tz=MSK)
    apply(interp.handle(st, Event("click", t_click, payload=gift_url)), t_click)

    # 4) крутим очередь таймеров (опционально с регистрацией в заданный момент)
    registered_done = False
    while pending:
        due_ts, _, node_key = heapq.heappop(pending)
        now = datetime.fromtimestamp(due_ts, tz=MSK)
        if register_at and not registered_done and now >= register_at:
            apply(interp.handle(st, Event("click", register_at,
                  payload=_dl("KEY"))), register_at)
            registered_done = True
            timeline.append((register_at, "→ КЛИК СОБЫТИЕ (registered, дожим стоп)", "-"))
            continue
        apply(interp.handle(st, Event("timeout", now, node_key=node_key)), now)

    return f, timeline


def print_timeline(title, f, timeline):
    print(f"\n{'='*70}\n{title}  (воронка: {f.key})\n{'='*70}")
    for dt, node, btn in timeline:
        stamp = dt.strftime("%a %d.%m %H:%M")
        print(f"  {stamp}  {node:<6}  кнопка: {btn}")
    print(f"  всего отправок: {sum(1 for _,n,_ in timeline if len(n)<=4)}")


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "funnels", "etalon.json")

    f, tl = run(path)
    print_timeline("СЦЕНАРИЙ 1: юзер НЕ регистрируется - полный дожим 7 дней", f, tl)

    reg = datetime(2026, 7, 4, 9, 0, tzinfo=MSK)   # регистрируется на 2-й день утром
    f2, tl2 = run(path, register_at=reg)
    print_timeline("СЦЕНАРИЙ 2: юзер регистрируется на 2-й день - дожим обрывается", f2, tl2)
