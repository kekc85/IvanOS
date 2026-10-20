"""Юнит-тесты движка воронки. Запуск: python3 -m tests.test_engine"""
import sys, os, heapq
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from engine.timing import MSK, next_daily
from engine.importer import validate, load_valid, ETALON_PATH
from engine.interpreter import Interpreter, State, Event

FUNNELS = os.path.join(os.path.dirname(__file__), "..", "funnels")
ETALON = os.path.join(FUNNELS, "etalon.json")

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {name}")


def drive(funnel_path, register_at=None, stop_at=None):
    """Прогон полного пути, возвращает список отправленных узлов по порядку."""
    f = load_valid(funnel_path)
    interp = Interpreter(f)
    st = State(funnel_key=f.key)
    t0 = datetime(2026, 7, 3, 14, 0, tzinfo=MSK)
    sent = []
    pending = []
    seq = 0

    def apply(dec):
        nonlocal seq
        for s in dec.sends:
            sent.append((s.at, s.node_key))
        for _ in dec.cancels:
            pending.clear()
        for sc in dec.schedules:
            if sc.delete_others:
                pending.clear()
            seq += 1
            heapq.heappush(pending, (sc.due_at.timestamp(), seq, sc.node_key))

    apply(interp.handle(st, Event("enter", t0)))
    apply(interp.handle(st, Event("button", t0.fromtimestamp(t0.timestamp() + 120, tz=MSK), payload="Забрать")))
    gift = f.nodes["B0"].url_button.url
    apply(interp.handle(st, Event("click", t0.fromtimestamp(t0.timestamp() + 300, tz=MSK), payload=gift)))

    reg_done = False
    while pending:
        ts, _, nk = heapq.heappop(pending)
        now = datetime.fromtimestamp(ts, tz=MSK)
        if stop_at and now >= stop_at:
            apply(interp.handle(st, Event("stop", stop_at)))
            stop_at = None
            continue
        if register_at and not reg_done and now >= register_at:
            apply(interp.handle(st, Event("click", register_at, payload="https://x/event/")))
            reg_done = True
            continue
        apply(interp.handle(st, Event("timeout", now, node_key=nk)))
    return f, sent


# --- 1. Валидация против эталона ---
check("эталон валиден", validate(ETALON) == [])

# все 19 боевых воронок проходят валидацию
import glob
bad = []
for p in glob.glob(os.path.join(FUNNELS, "voronka-*.json")):
    e = validate(p)
    if e:
        bad.append((os.path.basename(p), e))
check(f"все боевые воронки валидны ({len(glob.glob(os.path.join(FUNNELS,'voronka-*.json')))} шт)", not bad)
for name, e in bad:
    print(f"    {name}: {e}")

# битый файл отклоняется
import json, tempfile
broken = json.load(open(ETALON, encoding="utf-8"))
broken["connections"] = broken["connections"][:-1]   # убрали связь
tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
json.dump(broken, tf, ensure_ascii=False); tf.close()
check("битая воронка (10 связей) отклонена", validate(tf.name) != [])
os.unlink(tf.name)

# --- 2. Полный дожим: 13 user-facing сообщений, TECH не шлётся ---
f, sent = drive(ETALON)
keys = [k for _, k in sent]
check("TECH не отправляется юзеру", "TECH" not in keys)
check("полная последовательность A0,B0,C1-C4,D1-D7 = 13 сообщений", len(sent) == 13)
check("порядок дожима верный",
      keys == ["A0", "B0", "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "D5", "D6", "D7"])

# --- 3. Тайминги первых переходов (TECH+30м→C1, +1ч→C2, +2ч→C3, +8ч→C4) ---
tmap = {k: dt for dt, k in sent}
check("C1 = A0 + ~35 мин (клик+30м)", abs((tmap["C1"] - tmap["A0"]).total_seconds() - 35 * 60) < 5)
check("C2 = C1 + 1 час", abs((tmap["C2"] - tmap["C1"]).total_seconds() - 3600) < 5)
check("C3 = C2 + 2 часа", abs((tmap["C3"] - tmap["C2"]).total_seconds() - 2 * 3600) < 5)
check("C4 = C3 + 8 часов", abs((tmap["C4"] - tmap["C3"]).total_seconds() - 8 * 3600) < 5)

# --- 4. D-цепочка строго в 07:01 МСК, каждый день следующий ---
d_times = [tmap[f"D{i}"] for i in range(1, 8)]
check("все D в 07:01 МСК", all(t.hour == 7 and t.minute == 1 for t in d_times))
check("D1..D7 идут по одному дню подряд",
      all((d_times[i+1].date() - d_times[i].date()).days == 1 for i in range(6)))

# --- 5. Гвард registered обрывает дожим ---
reg = datetime(2026, 7, 4, 9, 0, tzinfo=MSK)
_, sent_reg = drive(ETALON, register_at=reg)
keys_reg = [k for _, k in sent_reg]
check("после регистрации D-цепочка не приходит", not any(k.startswith("D") for k in keys_reg))
check("до регистрации C-цепочка прошла", "C4" in keys_reg)

# --- 6. /stop обрывает всё ---
stop = datetime(2026, 7, 3, 16, 0, tzinfo=MSK)   # посреди C-цепочки
_, sent_stop = drive(ETALON, stop_at=stop)
check("после /stop дожим не продолжается", len([k for _, k in sent_stop]) < 13)

# --- 7. next_daily корректно катит на следующий день ---
base = datetime(2026, 7, 3, 14, 0, tzinfo=MSK)
nd = next_daily(base, 7, 1)
check("next_daily → следующий день 07:01", nd.day == 4 and nd.hour == 7 and nd.minute == 1)
base_early = datetime(2026, 7, 3, 5, 0, tzinfo=MSK)   # раньше 07:01
nd2 = next_daily(base_early, 7, 1)
check("next_daily катит на СЛЕДУЮЩИЙ день даже если сейчас раньше 07:01", nd2.day == 4)

print(f"\nИтог: {_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
