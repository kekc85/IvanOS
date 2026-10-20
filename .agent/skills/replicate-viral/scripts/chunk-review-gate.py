#!/usr/bin/env python3
"""
chunk-review-gate.py — МАШИННОЕ принуждение посегментного ревью (блупринт REVIEW-METHODOLOGY).

🔴 ПРИНЦИП (автор): гейт НЕ верит флагу `verdict:PASS` (его можно напечатать, не
приступив к работе — прецедент скилла «пост»: «слой PASS», а слой не делался). Гейт
ПЕРЕПРОВЕРЯЕТ ПЕРВИЧНЫЕ УЛИКИ и заставляет ДЕЙСТВИЕ (`feedback_enforcement_machine_reverifies_not_flags`):
  • РЕНДЕР куска реально существует, декодируется, 1080x1920 (нельзя «сделать» без рендера)
  • audit/critic-вердикты привязаны к md5 ЭТОГО рендера (старый/чужой вердикт = stale = MISS)
  • бенчмарк-вердикт несёт опоры [A,B,C] И контакт-PNG реально лежат на диске (прогон был)
  • панель критиков: ≥9 осей, КАЖДАЯ с СОДЕРЖАТЕЛЬНОЙ заметкой (≥30 симв) + ссылкой на реальный
    кадр (пустые `{"axis":"x"}` НЕ считаются — это фабрикация)
  • plan-conformance: реально посчитанное совпадение блоков (matched_blocks непустой)
  • отчёт ссылается на реально существующий артефакт

Чанки выводятся ИЗ deconstruction.md (биты группируются в окна ≥ MIN_CHUNK сек). Каждый чанк =
<project>/_chunks/chunk_<i>/ с render.mp4 + слой-уликами. Пишет <project>/.chunk-ledger.json.
exit 0 = все чанки реально отревьюены, 1 = есть незакрытый слой/чанк/фабрикация.

ОСТАТОЧНЫЙ ПРЕДЕЛ (честно): само vision-СУЖДЕНИЕ критика машинно не докажешь — гейт гарантирует,
что оно вынесено ПРОТИВ реальных артефактов (рендер+кадры+PNG) и содержательно, но «хорошо/плохо»
остаётся за адверсар-критиком-Opus. Всё ВОКРУГ суждения сделано нефабрикуемым.

usage: chunk-review-gate.py <project-dir> [--deconstruction deconstruction.md] [--min-chunk 3.0]
"""
import argparse, hashlib, json, os, subprocess, sys

REQUIRED_BENCH_ANCHORS = ("A", "B", "C")
MIN_AXES = 9
MIN_NOTE_CHARS = 30
# Заметка оси обязана СВЕРЯТЬ с эталоном (montage-lexicon), а не быть «красиво» на глаз.
# Должна называть якорь-эталон ИЛИ источник, против которого сверяет.
ANCHOR_TOKENS = ("rpn", "cintas", "steve", "tan", "duqe", "канон", "эталон", "источник", "конкурент")
# Формат-канон спикера: гейт САМ гонит layout-contract-check (пропорция/рамка/окклюзия/динамика).
# env-override CHUNK_GATE_LAYOUT_CMD — для selftest (стаб).
LAYOUT_CMD = os.environ.get("CHUNK_GATE_LAYOUT_CMD",
    "python3 " + os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout-contract-check.py"))


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def decode_ok(p):
    if not (os.path.isfile(p) and os.path.getsize(p) > 1000):
        return False
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "null", "-"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        return r.returncode == 0
    except Exception:
        return False


def video_wh(p):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                              "-show_entries", "stream=width,height", "-of", "csv=p=0", p],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        w, h = out.split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


def exists_rel(cdir, path):
    if not path:
        return False
    p = path if os.path.isabs(path) else os.path.join(cdir, path)
    return os.path.isfile(p)


def parse_beats(path):
    beats = []
    if not path or not os.path.isfile(path):
        return beats
    for ln in open(path, encoding="utf-8", errors="ignore"):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        try:
            ts = float(cells[0]); te = float(cells[1])
        except ValueError:
            continue
        beats.append((ts, te))
    return sorted(beats)


def chunk_windows(beats, min_chunk):
    windows = []
    cur_start = None; cur_end = None
    for ts, te in beats:
        if cur_start is None:
            cur_start = ts
        cur_end = te
        if cur_end - cur_start >= min_chunk:
            windows.append((cur_start, cur_end)); cur_start = None
    if cur_start is not None:
        if windows:
            windows[-1] = (windows[-1][0], cur_end)
        else:
            windows.append((cur_start, cur_end))
    return windows


def check_chunk(cdir):
    """ПЕРЕПРОВЕРКА первичных улик (не trust-the-flag). Возвращает (status, layers)."""
    L = {}
    render = os.path.join(cdir, "render.mp4")
    # ПРЕДУСЛОВИЕ: рендер куска реально есть и декодируется (нельзя «сделать» без рендера)
    if not decode_ok(render):
        return "MISS", {"render": "нет/не декодируется render.mp4 — кусок НЕ отрендерен (работа не сделана)"}
    w, h = video_wh(render)
    if (w, h) != (1080, 1920):
        L["render"] = "MISS(%dx%d != 1080x1920)" % (w, h)
    else:
        L["render"] = "PASS"
    rmd5 = md5(render)

    # L-FORMAT — ФОРМАТ-КАНОН (как располагать спикера: пропорция full/half · рамка · окклюзия ·
    # динамика). КОРНЕВОЙ фикс по решению автора: раньше гейт НЕ запускал layout-contract-check → я строил
    # аватар мимо канона (cleanv с городом, без K3-рамки) и проходил. Теперь гейт САМ гонит чек
    # против contract.json проекта — пропустить формат-канон физически нельзя (анти-RC-C).
    root = os.path.dirname(os.path.dirname(os.path.abspath(cdir)))
    contract = os.path.join(root, "contract.json")
    if not os.path.isfile(contract):
        L["L-format layout"] = "MISS(нет contract.json — формат-канон спикера не объявлен)"
    else:
        cmd = LAYOUT_CMD.split() + ["--render", render, "--contract", contract]
        mpath = os.path.join(cdir, "mode.txt")   # per-chunk формат (full/half/ui) — эталон смешанный
        if os.path.isfile(mpath):
            mv = open(mpath).read().strip()
            if mv in ("full", "half", "ui"): cmd += ["--mode", mv]
        try:
            rc = subprocess.run(cmd, capture_output=True, timeout=300).returncode
        except Exception as e:
            rc = 99
        L["L-format layout"] = "PASS" if rc == 0 else ("MISS(layout-contract FAIL rc=%s: "
            "пропорция≠full/half / рамка не вокруг спикера / окклюзия / статика-вместо-видео)" % rc)

    # L0-L1 audit — привязан к md5 ЭТОГО рендера (старый/чужой = stale)
    av = load_json(os.path.join(cdir, "audit-verdict.json"))
    if not (av and av.get("verdict") == "PASS"):
        L["L0-L1 audit"] = "MISS"
    elif av.get("render_md5") != rmd5:
        L["L0-L1 audit"] = "MISS(stale: вердикт не на этом рендере, render_md5≠факт)"
    else:
        L["L0-L1 audit"] = "PASS"

    # L2 plan-conformance — реально посчитанное совпадение блоков с деконструкцией
    pc = load_json(os.path.join(cdir, "plan-conformance.json"))
    if pc and pc.get("verdict") == "PASS" and isinstance(pc.get("matched_blocks"), list) and pc["matched_blocks"]:
        L["L2 plan"] = "PASS"
    else:
        L["L2 plan"] = "MISS(нет посчитанного matched_blocks — соответствие плану не проверено)"

    # L3-L4 benchmark — опоры [A,B,C] И контакт-PNG реально на диске (прогон был)
    bm = load_json(os.path.join(cdir, "benchmark-verdict.json"))
    if not (bm and bm.get("verdict") == "PASS"):
        L["L3-L4 benchmark"] = "MISS"
    else:
        anchors = set(bm.get("anchors", []))
        miss_a = [a for a in REQUIRED_BENCH_ANCHORS if a not in anchors]
        sheets = [pr.get("contact_sheet") for pr in bm.get("pairs", []) if isinstance(pr, dict)]
        real_sheets = [s for s in sheets if exists_rel(cdir, s)]
        if miss_a:
            L["L3-L4 benchmark"] = "MISS(нет опор %s)" % miss_a
        elif not real_sheets:
            L["L3-L4 benchmark"] = "MISS(нет ни одного pair_*.png на диске — бенчмарк не прогонялся)"
        else:
            L["L3-L4 benchmark"] = "PASS"

    # L5 панель критиков — привязка к рендеру + СОДЕРЖАТЕЛЬНОСТЬ (пустые оси не считаются)
    cv = load_json(os.path.join(cdir, ".critic-verdict.json"))
    if not (cv and cv.get("verdict") == "PASS"):
        L["L5 critic-panel"] = "MISS"
    elif cv.get("render_md5") != rmd5:
        L["L5 critic-panel"] = "MISS(stale: критик не на этом рендере)"
    elif not cv.get("benchmark_reel"):
        L["L5 critic-panel"] = "MISS(нет benchmark_reel)"
    else:
        axes = cv.get("axes", [])
        substantive = [ax for ax in axes if isinstance(ax, dict)
                       and len(str(ax.get("note", ""))) >= MIN_NOTE_CHARS
                       and exists_rel(cdir, ax.get("frame"))
                       and any(tok in str(ax.get("note", "")).lower() for tok in ANCHOR_TOKENS)]
        if len(substantive) < MIN_AXES:
            L["L5 critic-panel"] = ("MISS(грунтованных осей %d<%d: каждая нужна с заметкой ≥%d симв "
                                    "+ реальным кадром + сверкой с эталоном/источником по montage-lexicon; "
                                    "пустые/безэталонные {axis} = фабрикация)"
                                    % (len(substantive), MIN_AXES, MIN_NOTE_CHARS))
        else:
            L["L5 critic-panel"] = "PASS"

    # L6 отчёт — непустой И ссылается на реально существующий артефакт
    rep = os.path.join(cdir, "report.md")
    if not (os.path.isfile(rep) and os.path.getsize(rep) >= 200):
        L["L6 report"] = "MISS(нет отчёта ≥200 симв)"
    else:
        txt = open(rep, encoding="utf-8", errors="ignore").read()
        toks = [t.strip(".,;:!?()`'\"") for t in txt.replace("(", " ").replace(")", " ").replace("`", " ").split()]
        refs = [t for t in toks if "/" in t or t.endswith((".png", ".mp4", ".jpg"))]
        if any(exists_rel(cdir, r) for r in refs):
            L["L6 report"] = "PASS"
        else:
            L["L6 report"] = "MISS(отчёт не ссылается на реальный артефакт — пустой доклад)"

    status = "PASS" if all(v == "PASS" for v in L.values()) else "MISS"
    return status, L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--deconstruction", default="deconstruction.md")
    ap.add_argument("--min-chunk", type=float, default=3.0)
    a = ap.parse_args()

    root = a.project.rstrip("/")
    if not os.path.isdir(root):
        print("ОШИБКА: нет папки проекта %s" % root, file=sys.stderr); return 1
    dpath = a.deconstruction if os.path.isabs(a.deconstruction) else os.path.join(root, a.deconstruction)
    beats = parse_beats(dpath)
    if not beats:
        print("ОШИБКА: нет битов в деконструкции %s — сначала deconstruction-check" % dpath, file=sys.stderr)
        return 1
    windows = chunk_windows(beats, a.min_chunk)

    # built = есть _chunks/chunk_i/render.mp4 (отрендерен); иначе PENDING (ещё не собран, не FAIL).
    # Блокируем только если ПОСТРОЕННЫЙ кусок — брак. Инкрементальный воркфлоу: кусок отдаётся по
    # мере готовности; «готово» всего ролика отдельно требует все куски PASS (verdict==PASS).
    ledger, built_fail, pending = [], [], []
    for i, (ws, we) in enumerate(windows):
        cdir = os.path.join(root, "_chunks", "chunk_%d" % i)
        if not (os.path.isdir(cdir) and os.path.isfile(os.path.join(cdir, "render.mp4"))):
            ledger.append({"chunk": i, "window": [ws, we], "status": "PENDING",
                           "layers": {"_build": "кусок ещё не собран (нет render.mp4)"}})
            pending.append(i); continue
        status, layers = check_chunk(cdir)
        ledger.append({"chunk": i, "window": [ws, we], "status": status, "layers": layers})
        if status != "PASS":
            built_fail.append(i)

    verdict = "FAIL" if built_fail else ("INCOMPLETE" if pending else "PASS")
    out = {"project": os.path.basename(root), "chunks_total": len(windows),
           "chunks_pass": sum(1 for e in ledger if e["status"] == "PASS"),
           "chunks_pending": len(pending), "verdict": verdict, "ledger": ledger}
    json.dump(out, open(os.path.join(root, ".chunk-ledger.json"), "w"), ensure_ascii=False, indent=1)

    print("\n  CHUNK-REVIEW-LEDGER: %s — %s (%d PASS · %d pending · %d total)" % (
        out["project"], verdict, out["chunks_pass"], out["chunks_pending"], out["chunks_total"]))
    print("  " + "-" * 66)
    for e in ledger:
        mark = {"PASS": "v", "PENDING": "·"}.get(e["status"], "x")
        print("  %s chunk_%d [%.1f-%.1fс] %s" % (mark, e["chunk"], e["window"][0], e["window"][1], e["status"]))
        for k, v in e["layers"].items():
            if v != "PASS":
                print("       %s %s: %s" % (mark, k, v))
    print("  " + "-" * 66)
    if built_fail:
        print("  НЕЛЬЗЯ показывать куски %s: ПОСТРОЕННЫЙ кусок — брак (ПЕРЕпроверка улик не пройдена)." % built_fail)
    elif pending:
        print("  Собранные куски PASS. Осталось собрать: %s. «Готово» всего ролика — после всех PASS." % pending)
    print("  ledger: %s\n" % os.path.join(root, ".chunk-ledger.json"))
    return 1 if built_fail else 0


if __name__ == "__main__":
    sys.exit(main())
