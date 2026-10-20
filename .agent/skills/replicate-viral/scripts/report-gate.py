#!/usr/bin/env python3
"""
report-gate.py — МАШИННОЕ принуждение ЕДИНОЙ СТРУКТУРЫ ОТЧЁТНОСТИ (автор).

Канон структуры: knowledge/reporting-structure.md. Два требования автора:
  A. ПОСЛЕ КАЖДОЙ фазы — отчёт фазы в <project>/reports/f<slug>-report.md
  B. НА ВЫДАЧЕ ролика — многослойный ревью в <project>/reports/DELIVERY-REVIEW.md

Гейт НЕ верит словам «отчёт дал» — проверяет ФАЙЛЫ-улики (feedback_enforcement_machine_reverifies_not_flags):
  • per-phase: для КАЖДОЙ фазы со статусом PASS в .phase-ledger.json обязан быть отчёт-файл
    ≥MIN_PHASE симв, ссылающийся на ≥1 реально существующий путь-артефакт.
  • delivery: при наличии финального рендера обязан быть DELIVERY-REVIEW.md ≥MIN_DELIV симв,
    упоминающий ВСЕ слои L0–L7, ссылающийся на реальный render, с ≥MIN_PANEL строками панели L5.

Backward-compat: нет.phase-ledger.json (legacy-проект до этой редакции) → per-phase не проверяем (WARN).
DELIVERY-REVIEW требуется только когда есть рендер (момент выдачи) — это и есть новый мандат.

usage:
  report-gate.py <project-dir>                 # проверить оба требования -> .report-verdict.json
  report-gate.py <project-dir> --render r.mp4  # явно указать финальный рендер
exit 0 = PASS, 1 = есть незакрытый отчёт (FAIL), 2 = ошибка использования.
"""
import json, os, re, sys

MIN_PHASE = 200      # симв — отчёт фазы не должен быть заглушкой
MIN_DELIV = 600      # симв — ревью на выдаче существенно длиннее
MIN_PANEL = 9        # строк панели критиков L5 (как chunk-review-gate MIN_AXES)
L_LAYERS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]


def phase_slug(pid):
    """Ф1->f1, Ф2c->f2c, Ф4.6->f46, Ф6->f6 (id без 'Ф' и точек, в нижнем регистре)."""
    return "f" + pid.replace("Ф", "").replace(".", "").lower()


def read(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


def refs_real_path(text, root):
    """В тексте есть ≥1 токен-путь, который реально существует на диске (отн. root или абс.)."""
    for tok in re.split(r"[\s`()\[\]<>|]+", text):
        t = tok.strip(".,;:!?\"'")
        if "/" in t or t.endswith((".md", ".mp4", ".png", ".jpg", ".json", ".wav", ".flag", ".txt")):
            p = t if os.path.isabs(t) else os.path.join(root, t)
            if os.path.isfile(p) or os.path.isdir(p):
                return True
    return False


def find_render(root, explicit):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    cands = []
    for dp, _, fns in os.walk(root):
        if any(s in dp for s in ("/node_modules", "/.git", "/public", "/src", "/_chunks")):
            continue
        for fn in fns:
            if fn.endswith(".mp4") and not re.search(r"avatar|voice|source|input", fn, re.I):
                fp = os.path.join(dp, fn)
                try:
                    cands.append((os.path.getmtime(fp), fp))
                except OSError:
                    pass
    return max(cands)[1] if cands else None


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 2
    root = a[0].rstrip("/")
    explicit = a[a.index("--render") + 1] if "--render" in a and a.index("--render") + 1 < len(a) else None
    if not os.path.isdir(root):
        print("ОШИБКА: нет папки проекта %s" % root, file=sys.stderr); return 2

    fails, warns, facts = [], [], []
    rep_dir = os.path.join(root, "reports")

    # --- A. ОТЧЁТЫ ФАЗ (per-phase) ---
    ledger_p = os.path.join(root, ".phase-ledger.json")
    if os.path.isfile(ledger_p):
        try:
            phases = json.load(open(ledger_p, encoding="utf-8")).get("phases", {})
        except Exception as e:
            phases = {}; warns.append("phase-ledger не читается (%s) — отчёты фаз не сверены" % e)
        pass_phases = [pid for pid, e in phases.items() if e.get("status") == "PASS"]
        have, miss = [], []
        for pid in pass_phases:
            rp = os.path.join(rep_dir, "%s-report.md" % phase_slug(pid))
            txt = read(rp)
            if len(txt) < MIN_PHASE:
                miss.append("%s (нет %s-report.md ≥%d симв)" % (pid, phase_slug(pid), MIN_PHASE))
            elif not refs_real_path(txt, root):
                miss.append("%s (отчёт не ссылается на реальный артефакт-улику)" % pid)
            else:
                have.append(pid)
        facts.append("отчёты фаз: %d/%d закрыто [%s]" % (len(have), len(pass_phases), ",".join(have) or "-"))
        for m in miss:
            fails.append("НЕТ ОТЧЁТА ФАЗЫ: %s — структура A (knowledge/reporting-structure.md)" % m)
    else:
        warns.append("нет .phase-ledger.json (legacy/прогон не начат) — отчёты фаз не проверены машинно")

    # --- B. РЕВЬЮ НА ВЫДАЧЕ (delivery) — обязателен при наличии рендера ---
    render = find_render(root, explicit)
    if render:
        dpath = os.path.join(rep_dir, "DELIVERY-REVIEW.md")
        txt = read(dpath)
        rbase = os.path.basename(render)
        if len(txt) < MIN_DELIV:
            fails.append("НЕТ РЕВЬЮ ВЫДАЧИ: reports/DELIVERY-REVIEW.md отсутствует/короче %d симв — "
                         "выложить многослойный чек-лист (структура B). Рендер есть (%s), ревью нет = "
                         "«ничего не дал»" % (MIN_DELIV, rbase))
        else:
            miss_l = [l for l in L_LAYERS if l not in txt]
            if miss_l:
                fails.append("РЕВЬЮ ВЫДАЧИ НЕПОЛНЫЙ: нет упоминания слоёв %s (нужны все L0–L7)" % miss_l)
            if rbase not in txt and render not in txt:
                fails.append("РЕВЬЮ ВЫДАЧИ не ссылается на финальный рендер %s" % rbase)
            # панель L5: ≥MIN_PANEL содержательных строк-таблицы (строки с ≥3 разделителями '|')
            panel = [ln for ln in txt.splitlines()
                     if ln.count("|") >= 3 and not re.search(r"---|Категория|Слой|Фаза", ln)]
            if len(panel) < MIN_PANEL:
                fails.append("ПАНЕЛЬ L5 НЕ РАСПИСАНА: %d<%d строк критиков в DELIVERY-REVIEW "
                             "(категория×вердикт×якорь-эталон)" % (len(panel), MIN_PANEL))
            if not refs_real_path(txt, root):
                fails.append("РЕВЬЮ ВЫДАЧИ не ссылается ни на один реальный артефакт-улику")
            facts.append("delivery-review: %d симв, слои %d/8, панель %d строк (%s)"
                         % (len(txt), len(L_LAYERS) - len([l for l in L_LAYERS if l not in txt]),
                            len(panel), rbase))
    else:
        facts.append("финального рендера нет — ревью выдачи ещё не требуется (фаза производства)")

    verdict = "FAIL" if fails else "PASS"
    json.dump({"verdict": verdict, "fails": fails, "warns": warns, "facts": facts,
               "render": render or ""},
              open(os.path.join(root, ".report-verdict.json"), "w"), ensure_ascii=False, indent=1)

    print("\n  REPORT-GATE: %s — %s" % (os.path.basename(root), verdict))
    print("  " + "-" * 60)
    for f in facts:
        print("  · %s" % f)
    for w in warns:
        print("  ⚠ %s" % w)
    for f in fails:
        print("  ✗ %s" % f)
    print("  verdict: %s\n" % os.path.join(root, ".report-verdict.json"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())