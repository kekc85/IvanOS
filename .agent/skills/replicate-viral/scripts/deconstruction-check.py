#!/usr/bin/env python3
"""
deconstruction-check.py — МАШИННЫЙ чек покадровой деконструкции источника (вход Фазы 2c).

Закрывает корневой брак Build-on-guess (RC-A): реплика идёт ИЗ ВЕРИФИЦИРОВАННЫХ КАДРОВ,
не из догадки. Парсит <project>/deconstruction.md (markdown-таблица формата
knowledge/source-deconstruction.md), валидирует покрытие/привязку/резолв, пишет
<project>/.deconstruction-verdict.json и (опц.) генерит pairs.json для benchmark-pairs.py
ИЗ ГРИДА деконструкции (анти-BENCH-1 «пары в голове агента»).

Проверки (AC2 спеки):
  (a) ПОКРЫТИЕ — биты сплошные от 0 до длительности источника, без дыр/нахлёстов;
      на первых 3.0с шаг (t_end-t_start) ≤ 0.5с (хук решает всё).
  (b) ПРИВЯЗКА — у КАЖДОЙ строки есть frame и файл реально существует (нет кадра = догадка).
  (c) АНТИ-ВЫДУМКА — block заявлен без frame = выдуманный эффект без улики (BENCH-2).
  (d) РЕЗОЛВ — block (если не '-') ∈ реальный каталог motion-blocks (иначе выдуман).

usage:
  deconstruction-check.py <deconstruction.md> [--project DIR] [--duration SEC]
        [--ref comp.mp4] [--our our.mp4] [--emit-pairs pairs.json]
exit: 0 = PASS, 1 = FAIL (как selftest ждёт).
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout_enum import normalize as layout_norm, is_valid as layout_valid, DYNAMIC_LAYOUTS  # единый enum

EPS = 0.06
HOOK_WINDOW = 3.0
HOOK_STEP_MAX = 0.5
DYNAMIC_BEAT_MAX = 1.0  # на динамичной зоне бит ДОЛЖЕН быть ≤1с (посекундная репликация)
from layout_enum import LAYOUT_ENUM as _LE
LAYOUT_HINT = "/".join(_LE)
REQUIRED_COLS = ["t_start", "t_end", "frame", "layout", "shows", "motion", "text", "sfx", "block", "bench"]
BLOCKS_INDEX = os.path.expanduser("~/.business/growth/assets/motion-blocks/_index.json")
FALLBACK_BLOCKS = {
    "E5-perspective-grid-floor", "K3-overlap-card-avatar", "O6-avatar-feathered-fill",
    "A18-title-strap-caps", "F5-ai-model-icon-row", "G24-repo-file-list", "G25-readme-card",
    "G26-glow-frame-highlight", "G27-command-input-typeon", "J5-word-stream-whisper-sync",
}


def load_valid_blocks():
    try:
        d = json.load(open(BLOCKS_INDEX, encoding="utf-8"))
        ids = {b["id"] for b in d if isinstance(b, dict) and b.get("id")}
        if ids:
            return ids
    except Exception:
        pass
    return set(FALLBACK_BLOCKS)


def ffprobe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except Exception:
        return None


def parse_table(path):
    """Найти markdown-таблицу с нужными колонками, вернуть (rows, header_error)."""
    lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and all(c in ln for c in ("t_start", "t_end", "frame", "block")):
            header_idx = i
            break
    if header_idx is None:
        return None, "не найдена таблица деконструкции с колонками %s" % REQUIRED_COLS
    header = [c.strip() for c in lines[header_idx].strip().strip("|").split("|")]
    miss = [c for c in REQUIRED_COLS if c not in header]
    if miss:
        return None, "в заголовке таблицы нет колонок %s (есть %s)" % (miss, header)
    rows = []
    for ln in lines[header_idx + 1:]:
        s = ln.strip()
        if not s.startswith("|"):
            break  # таблица кончилась
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue  # строка-разделитель |---|---|
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        rows.append({header[j]: cells[j] for j in range(len(header))})
    return rows, None


def validate(rows, proj_root, duration, valid_blocks):
    issues = []
    parsed = []
    for n, r in enumerate(rows, 1):
        try:
            ts = float(r["t_start"]); te = float(r["t_end"])
        except ValueError:
            issues.append("строка %d: t_start/t_end не число (%r/%r)" % (n, r["t_start"], r["t_end"]))
            continue
        if te <= ts:
            issues.append("строка %d: t_end <= t_start (%.2f<=%.2f)" % (n, te, ts))
        parsed.append((n, ts, te, r))

    if not parsed:
        issues.append("нет ни одной валидной строки деконструкции")
        return issues, []

    parsed.sort(key=lambda x: x[1])

    # (a) покрытие
    if abs(parsed[0][1]) > EPS:
        issues.append("покрытие: первый бит начинается с %.2f, а не с 0.0" % parsed[0][1])
    for k in range(len(parsed) - 1):
        _, _, te, _ = parsed[k]
        _, ts2, _, _ = parsed[k + 1]
        if ts2 - te > EPS:
            issues.append("покрытие: дыра %.2f→%.2f (незакрытый таймкод)" % (te, ts2))
        elif te - ts2 > EPS:
            issues.append("покрытие: нахлёст %.2f→%.2f" % (ts2, te))
    last_te = parsed[-1][2]
    if duration and abs(last_te - duration) > 0.5:
        issues.append("покрытие: последний бит кончается %.2f, длительность источника %.2f (не покрыт хвост)" % (last_te, duration))
    # (a) шаг хука ≤0.5с на первых 3с
    for n, ts, te, _ in parsed:
        if ts < HOOK_WINDOW - EPS and (te - ts) > HOOK_STEP_MAX + EPS:
            issues.append("хук: бит %.2f→%.2f шире %.1fс (первые %.0fс — шаг ≤%.1fс)" % (ts, te, HOOK_STEP_MAX, HOOK_WINDOW, HOOK_STEP_MAX))

    # (b/c/d) построчно
    anchors = []
    for n, ts, te, r in parsed:
        frame = r.get("frame", "").strip()
        block = r.get("block", "").strip()
        has_frame = False
        if frame and frame not in ("-", "—"):
            fp = frame if os.path.isabs(frame) else os.path.join(proj_root, frame)
            has_frame = os.path.isfile(fp)
        # (b) привязка
        if not has_frame:
            if block and block not in ("-", "—"):
                issues.append("строка %d (%.2f→%.2f): ВЫДУМКА — блок '%s' заявлен без кадра-улики (frame=%r)" % (n, ts, te, block, frame))
            else:
                issues.append("строка %d (%.2f→%.2f): нет кадра-улики (frame=%r) — догадка, не источник" % (n, ts, te, frame))
        # (d) резолв блока
        if block and block not in ("-", "—") and block not in valid_blocks:
            issues.append("строка %d (%.2f→%.2f): блок '%s' не существует в каталоге motion-blocks (выдуман)" % (n, ts, te, block))
        # обязательные непустые
        for col in ("layout", "shows", "motion", "text"):
            if not r.get(col, "").strip():
                issues.append("строка %d (%.2f→%.2f): пустая колонка '%s'" % (n, ts, te, col))
        # (e) ENUM layout: значение ∈ единый layout_enum (с учётом алиаса full-demo→full-broll)
        lay_raw = r.get("layout", "").strip()
        if lay_raw and not layout_valid(lay_raw):
            issues.append("строка %d (%.2f→%.2f): неизвестный layout '%s' — не из enum "
                          "%s (алиас full-demo→full-broll)" % (n, ts, te, lay_raw, LAYOUT_HINT))
        # якоря бенчмарка
        b = r.get("bench", "").strip()
        if b and b not in ("-", "—"):
            label = b.lstrip("★* ").strip() or ("anchor%d" % n)
            anchors.append({"label": label, "ref_t": round((ts + te) / 2, 2), "our_t": round((ts + te) / 2, 2)})

    # (f) ПОСЕКУНДНОЕ правило (AC1 по решению автора): на ДИНАМИЧНОЙ зоне бит >1с = провал реплики
    # 1:1. Зона динамична, если layout бита ∈ {full-head,split} ИЛИ соседний бит имеет
    # ДРУГОЙ layout (смена раскладки = монтажная динамика). Залипший длинный бит на
    # динамике нельзя реплицировать посекундно — нужно дробить мельче.
    norm_lay = [layout_norm(r.get("layout")) for (_n, _ts, _te, r) in parsed]
    for k, (n, ts, te, r) in enumerate(parsed):
        dur = te - ts
        if dur <= DYNAMIC_BEAT_MAX + EPS:
            continue
        cur = norm_lay[k]
        prev = norm_lay[k - 1] if k > 0 else None
        nxt = norm_lay[k + 1] if k < len(parsed) - 1 else None
        is_dynamic = (cur in DYNAMIC_LAYOUTS
                      or (prev is not None and prev != cur)
                      or (nxt is not None and nxt != cur))
        if is_dynamic:
            issues.append("бит %d (%.2f→%.2f, %.2fс, layout=%s) длиннее 1с на ДИНАМИКЕ — "
                          "разбей мельче для посекундной репликации (AC1)"
                          % (n, ts, te, dur, cur or r.get("layout", "").strip()))

    if not (3 <= len(anchors) <= 8):
        issues.append("якоря бенчмарка (bench=★): %d, ожидается 5-7 (мин 3) — нужны для pairs.json" % len(anchors))

    return issues, anchors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deconstruction")
    ap.add_argument("--project", default=None)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--our", default=None)
    ap.add_argument("--emit-pairs", default=None)
    a = ap.parse_args()

    if not os.path.isfile(a.deconstruction):
        print("ОШИБКА: нет файла %s" % a.deconstruction, file=sys.stderr)
        return 1
    proj_root = a.project or os.path.dirname(os.path.abspath(a.deconstruction))
    duration = a.duration if a.duration else (ffprobe_duration(a.ref) if a.ref else None)

    rows, herr = parse_table(a.deconstruction)
    if herr:
        print("FAIL: %s" % herr, file=sys.stderr)
        json.dump({"verdict": "FAIL", "issues": [herr]},
                  open(os.path.join(proj_root, ".deconstruction-verdict.json"), "w"), ensure_ascii=False, indent=1)
        return 1

    valid_blocks = load_valid_blocks()
    issues, anchors = validate(rows, proj_root, duration, valid_blocks)
    verdict = "FAIL" if issues else "PASS"

    out = {
        "verdict": verdict,
        "deconstruction": os.path.basename(a.deconstruction),
        "rows": len(rows),
        "duration_s": duration,
        "anchors": anchors,
        "issues": issues,
    }
    json.dump(out, open(os.path.join(proj_root, ".deconstruction-verdict.json"), "w"),
              ensure_ascii=False, indent=1)

    print("\n  DECONSTRUCTION-CHECK: %s — %s (%d строк, %d якорей)" % (
        os.path.basename(a.deconstruction), verdict, len(rows), len(anchors)))
    if issues:
        for it in issues:
            print("   x %s" % it)
    else:
        print("   v покрытие сплошное, каждый бит привязан к кадру, блоки резолвятся, %d якорей" % len(anchors))

    if a.emit_pairs and verdict == "PASS":
        pairs = {"ref": a.ref or "<comp.mp4>", "our": a.our or "<our.mp4>", "pairs": anchors}
        json.dump(pairs, open(a.emit_pairs, "w"), ensure_ascii=False, indent=1)
        print("   -> pairs.json: %s (%d пар из грида деконструкции)" % (a.emit_pairs, len(anchors)))

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())