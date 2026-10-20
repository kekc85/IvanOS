#!/usr/bin/env python3
"""
launch-status.py — детерминированный статус подфаз запуска ИЗ РЕАЛЬНЫХ артефактов.

Зачем: ручные метки в plans/*.md и tasks/projects/*.md ведутся отдельно и
систематически отстают от реальности (содержание подфазы часто живёт ВНУТРИ
зонтичного артефакта — матрицы/5.3/Воронки, а метка остаётся ⬜/⚠️).
Этот скрипт — ЕДИНСТВЕННЫЙ источник истины о статусе. Метки не читаем.

Статус:
  ✅ DONE        — есть доказательство (файл или маркер-содержание) БЕЗ плейсхолдеров
  ⚠️ PLACEHOLDER — артефакт/маркер есть, но внутри незаполненный плейсхолдер ({...}, TBD, «не указано»)
  🟡 PLANNED     — спланировано в зонтике, но готовый текст/артефакт не произведён
  ⬜ MISSING     — ни плана, ни производства

Зачем PLACEHOLDER: файл с {имя тарифа}/TBD раньше проходил как DONE — незаполненный
выход рапортовался закрытым и протекал downstream .

Использование:
  python3 launch-status.py [путь-к-папке-запуска]
  (по умолчанию — текущий активный запуск)
Пишет также STATUS.md рядом с manifest — его и читать первым в новой сессии.
"""
import json, re, sys, os

# Корень рабочего пространства ученика: $HOME/IvanOS (см. CLAUDE.md).
# Папку активного запуска можно передать первым аргументом; по умолчанию
# берём её из переменной окружения LAUNCH_DIR, иначе — общий каталог запусков
# внутри рабочего пространства. Никаких личных путей в коде нет — всё
# считается относительно $HOME, работает одинаково на Mac и Windows.
_WORKSPACE = os.environ.get(
    "IVANOS_WORKSPACE",
    os.path.join(os.path.expanduser("~"), "IvanOS"),
)
DEFAULT = os.environ.get(
    "LAUNCH_DIR",
    os.path.join(_WORKSPACE, ".business", "запуски", "активный-запуск"),
)

# Незаполненный выход: плейсхолдер методологии в фигурных скобках с кириллицей
# ({целевая цена основного тарифа}, {имя тарифа}), либо явные маркеры-заглушки.
# Кириллица в {} — чтобы не ловить JSON/код с ASCII-ключами (минимум ложных срабатываний).
PLACEHOLDER_RE = re.compile(
    r"\{[^}]*[А-Яа-яЁё][^}]*\}|\bTBD\b|\bTODO\b|не указано — требует уточнения|плейсхолдер|ПЛЕЙСХОЛДЕР"
)

def _has_placeholder(path):
    try:
        return bool(PLACEHOLDER_RE.search(open(path, encoding="utf-8", errors="ignore").read()))
    except Exception:
        return False

def check(item, root):
    if item["type"] == "manual":
        sp = os.path.join(root, "_state.json")
        if not os.path.isfile(sp):
            return (False, f'manual:{item["flag"]} (нет _state.json)')
        try:
            st = json.load(open(sp, encoding="utf-8", errors="ignore"))
        except Exception:
            return (False, f'manual:{item["flag"]} (ошибка _state.json)')
        return (bool(st.get(item["flag"])), f'manual:{item["flag"]} = {st.get(item["flag"])}')
    p = os.path.join(root, item["path"])
    if item["type"] == "file":
        if not os.path.isfile(p):
            return (False, item["path"])
        if _has_placeholder(p):
            return (False, item["path"] + " ⚠PLACEHOLDER")
        return (True, item["path"])
    # marker
    if not os.path.isfile(p):
        return (False, f'{item["path"]} (нет файла)')
    try:
        txt = open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return (False, f'{item["path"]} (ошибка чтения)')
    hit = re.search(item["pattern"], txt)
    if hit and PLACEHOLDER_RE.search(txt):
        return (False, f'{item["path"]} :: /{item["pattern"]}/ ⚠PLACEHOLDER')
    return (bool(hit), f'{item["path"]} :: /{item["pattern"]}/')

def evidences(items, root, mode="all"):
    """mode='all' — нужны ВСЕ доказательства; mode='any' — достаточно одного."""
    oks, ev = [], []
    for it in items:
        ok, label = check(it, root)
        oks.append(ok)
        ev.append(("✔" if ok else "✘") + " " + label)
    agg = (all(oks) and len(oks) > 0) if mode == "all" else any(oks)
    return (agg, ev)

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    mp = os.path.join(root, "_status-manifest.json")
    if not os.path.isfile(mp):
        print(f"\n  Нет _status-manifest.json в {root}")
        print("  → новый продукт: пройди фазу 0 (Установка) — она скопирует шаблон.\n")
        return
    man = json.load(open(mp, encoding="utf-8"))
    rows, lines = [], []
    lines.append(f"# STATUS — {man['launch']}")
    lines.append(f"_Автогенерация launch-status.py из артефактов. Метки plans/ — НЕ источник истины._\n")
    for ph in man["phases"]:
        kind = ph.get("kind", "done")
        if kind == "excluded":
            status = "⛔ EXCLUDED"
            detail = ["причина: " + ph.get("reason", "вне скоупа (решение автора)")]
        elif kind == "done":
            ok, ev = evidences(ph["done"], root)
            if ok:
                status = "✅ DONE"
            elif any("⚠PLACEHOLDER" in e for e in ev):
                status = "⚠️ PLACEHOLDER"
            else:
                status = "⬜ MISSING"
            detail = ev
        else:  # planned_vs_produced — для каждого слоя достаточно ОДНОГО доказательства
            planned_ok, p_ev = evidences(ph.get("planned", []), root, mode="any")
            produced_ok, q_ev = evidences(ph.get("produced", []), root, mode="any")
            if produced_ok:
                status = "✅ DONE"
            elif any("⚠PLACEHOLDER" in e for e in q_ev):
                status = "⚠️ PLACEHOLDER"
            elif planned_ok:
                status = "🟡 PLANNED"
            else:
                status = "⬜ MISSING"
            detail = ["план: " + ("; ".join(p_ev) if p_ev else "—"),
                      "произв.: " + ("; ".join(q_ev) if q_ev else "—")]
        rows.append((ph["id"], ph["name"], status))
        lines.append(f"## {ph['id']} {ph['name']} — {status}")
        for d in detail:
            lines.append(f"  - {d}")
        lines.append("")
    # консольная таблица
    w = max(len(n) for _, n, _ in rows)
    print(f"\n  СТАТУС ЗАПУСКА: {man['launch']}  (марафон {man.get('marathon_date','?')})")
    print("  " + "-" * (w + 22))
    for pid, name, st in rows:
        print(f"  {pid:<6} {name:<{w}}  {st}")
    print("  " + "-" * (w + 22))
    done = sum(1 for _,_,s in rows if s.startswith("✅"))
    ph_n = sum(1 for _,_,s in rows if s.startswith("⚠️"))
    plan = sum(1 for _,_,s in rows if s.startswith("🟡"))
    miss = sum(1 for _,_,s in rows if s.startswith("⬜"))
    excl = sum(1 for _,_,s in rows if s.startswith("⛔"))
    print(f"  Итог: ✅ {done}  ·  ⚠️ {ph_n}  ·  🟡 {plan}  ·  ⬜ {miss}  ·  ⛔ {excl}\n")
    out = os.path.join(root, "STATUS.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"  STATUS.md обновлён: {out}\n")

if __name__ == "__main__":
    main()
