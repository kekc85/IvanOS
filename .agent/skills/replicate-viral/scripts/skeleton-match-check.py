#!/usr/bin/env python3
"""
skeleton-match-check.py — Фаза 3 «montage skeleton binding»: МАШИННЫЙ ГЕЙТ выдачи (hard).

Проверяет, что СОБРАННАЯ композиция воспроизводит ЗАМОРОЖЕННЫЙ скелет эталона
(scene-skeleton.json от skeleton-derive.py) — анти-монотонность ДО рендера. Это
дискриминатор «повтори один-в-один»: монотонная говорящая голова там, где у
эталона контент, становится машинно-невалидной.

Корень брака: Opus без Fable при свободной сборке выдаёт full-screen talking-head на
весь ролик (reel-DXBt1opj). Скелет несёт каденс эталона в ДАННЫХ; этот гейт принуждает
сборку его воспроизвести.

Проверки (AC3 спеки):
  (a) ЧИСЛО БИТОВ композиции == n_beats скелета.
  (b) LAYOUT каждого бита == layout скелета (по порядку).
  (c) AVATAR FULL-SCREEN (full-head / O6) — ТОЛЬКО на bookend/anchor-битах скелета.
      Бит, у которого скелет avatar_role==absent, НЕ должен нести говорящую голову.
  (d) НЕТ layout дольше скелет-бита: dur бита композиции ≤ скелета (+EPS).
  (e) АНТИ-МОНОТОН: если ≥60% битов композиции — один layout, а скелет требует ≥3 разных,
      → FAIL «композиция держит один layout, скелет эталона чередует».

Источник битов композиции (по приоритету):
  1) --spec scene.spec.json с beats[] (канон Ф2: beats = контракт сборки) — сверяем beats[].
  2) иначе пробуем вытащить биты из собранного HTML (data-beat/data-layout атрибуты).
  3) не вышло → FAIL с понятным сообщением «нужен --spec с beats[]».

Backward-compat: НЕТ scene-skeleton.json → SKIP (печать + exit 0), чтобы старые проекты
(до montage-skeleton-binding) не падали.

usage:
  skeleton-match-check.py --skeleton scene-skeleton.json --html <built/index.html>
        [--spec scene.spec.json] [--project DIR]
exit: 0 = PASS (или SKIP — нет скелета), 2 = FAIL (как ждёт selftest exit-affecting).
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skeleton_common import (  # ЕДИНЫЙ источник констант скелета (L3-фикс, не дублировать)
    AVATAR_FULLSCREEN_LAYOUT,
    AVATAR_BEARING_BLOCKS,
    AVATAR_OK_ROLES as AVATAR_FULLSCREEN_ROLES,
)

EPS = 0.05            # допуск длительности бита (как SKELETON_DUR_EPS в scene-assemble)
MONOTONE_FRAC = 0.60  # доля одинакового layout, при которой это «монотон»
SKELETON_DIVERSITY_MIN = 3  # ≥ стольких РАЗНЫХ layout у скелета → монотон композиции = FAIL


def load_json(path):
    return json.load(open(path, encoding="utf-8"))


def beat_bears_avatar(beat):
    """Бит композиции НЕСЁТ аватар (говорящую голову)?
    Сигнал: layout∈full-head (full-screen) ИЛИ block — аватар-несущий блок (O6 ИЛИ K3).
    C2-фикс: K3-overlap-card-avatar раньше протаскивал говорящую голову на absent-битах,
    т.к. детектор знал только full-head/O6."""
    if beat.get("layout") in AVATAR_FULLSCREEN_LAYOUT:
        return True
    blk = beat.get("block")
    if blk and blk in AVATAR_BEARING_BLOCKS:
        return True
    return False


def beats_from_spec(spec_path):
    """Вытащить beats[] из scene.spec.json. (beats|None, error|None)."""
    try:
        spec = load_json(spec_path)
    except Exception as ex:
        return None, "спека %s не читается как JSON: %s" % (spec_path, ex)
    beats = spec.get("beats")
    if beats is None:
        return None, ("в спеке %s НЕТ beats[] (контракт Ф2). Спека ОБЯЗАНА нести beats[] "
                      "по скелету эталона." % spec_path)
    if not isinstance(beats, list):
        return None, "в спеке %s beats не массив" % spec_path
    return beats, None


def beats_from_html(html_path):
    """Best-effort вытащить биты из собранного HTML по data-beat/data-layout атрибутам.
    Ассемблер пока их не эмитит → обычно вернёт []. (beats, error|None)."""
    try:
        html = open(html_path, encoding="utf-8", errors="ignore").read()
    except Exception as ex:
        return [], "HTML %s не читается: %s" % (html_path, ex)
    # ищем элементы с data-beat="N" и/или data-layout="..."; собираем по индексу бита
    out = {}
    for m in re.finditer(r'data-beat\s*=\s*["\'](\d+)["\']', html):
        out.setdefault(int(m.group(1)), {})
    # привязать layout/t0/t1, если есть рядом в том же теге — берём по простому скану тегов
    for tag in re.finditer(r"<[^>]*data-beat\s*=\s*[\"'](\d+)[\"'][^>]*>", html):
        i = int(tag.group(1))
        seg = tag.group(0)
        b = out.setdefault(i, {})
        lm = re.search(r'data-layout\s*=\s*["\']([a-z0-9-]+)["\']', seg)
        if lm:
            b["layout"] = lm.group(1)
        for attr in ("t0", "t1"):
            am = re.search(r'data-%s\s*=\s*["\']([0-9.]+)["\']' % attr, seg)
            if am:
                try:
                    b[attr] = float(am.group(1))
                except ValueError:
                    pass
        bm = re.search(r'data-block\s*=\s*["\']([A-Za-z0-9-]+)["\']', seg)
        if bm:
            b["block"] = bm.group(1)
    beats = [out[i] for i in sorted(out)]
    return beats, None


def beat_dur(beat):
    try:
        return float(beat.get("t1")) - float(beat.get("t0"))
    except (TypeError, ValueError):
        return None


def check(skel, comp_beats):
    """Сверить биты композиции (comp_beats) с битами скелета. Вернуть список issues (пуст = PASS)."""
    issues = []
    skel_beats = skel.get("beats") or []
    n_skel = skel.get("n_beats", len(skel_beats))

    # (a) число битов
    if len(comp_beats) != n_skel:
        issues.append("число битов композиции=%d != скелета=%d (композиция обязана "
                      "воспроизводить скелет побитно)" % (len(comp_beats), n_skel))

    # (b)(c)(d) побитная сверка по индексу/порядку
    pairs = min(len(comp_beats), len(skel_beats))
    for i in range(pairs):
        cb = comp_beats[i] if isinstance(comp_beats[i], dict) else {}
        kb = skel_beats[i] if isinstance(skel_beats[i], dict) else {}
        cl = cb.get("layout")
        kl = kb.get("layout")
        role = kb.get("avatar_role")

        # (b) layout совпадает
        if cl != kl:
            issues.append("бит %d: layout композиции '%s' != скелета '%s' "
                          "(монтаж обязан повторять раскладку эталона побитно)" % (i, cl, kl))

        # (c) аватар-несущий бит (full-head / O6 / K3) только на bookend/anchor
        if beat_bears_avatar(cb) and role not in AVATAR_FULLSCREEN_ROLES:
            blk = cb.get("block")
            blk_note = (", block %s" % blk) if blk in AVATAR_BEARING_BLOCKS else ""
            issues.append("бит %d: аватар (говорящая голова: layout '%s'%s) запрещён — у эталона тут "
                          "avatar_role='%s' (контент, не лицо). Говорящую голову "
                          "только на битах bookend/anchor (анти-монотонность)." % (i, cl, blk_note, role))

        # (d) не держится дольше скелет-бита (+ M2: нет t0/t1 при скелете с dur -> FAIL)
        cd = beat_dur(cb)
        kd = beat_dur(kb)
        if kd is not None and cd is None:
            issues.append("бит %d: нет t0/t1 — длительность не проверить, а у скелета она есть "
                          "(%.2fs). Бит композиции ОБЯЗАН нести t0/t1." % (i, kd))
        elif cd is not None and kd is not None and cd > kd + EPS:
            issues.append("бит %d: длительность композиции %.2fs > скелета %.2fs "
                          "(раскладка держится дольше эталон-бита = монотонность)" % (i, cd, kd))

    # (e) анти-монотон-сводка
    skel_layouts = {b.get("layout") for b in skel_beats if isinstance(b, dict) and b.get("layout")}
    comp_layouts = [b.get("layout") for b in comp_beats if isinstance(b, dict)]
    if comp_layouts and len(skel_layouts) >= SKELETON_DIVERSITY_MIN:
        counts = {}
        for lay in comp_layouts:
            counts[lay] = counts.get(lay, 0) + 1
        top_lay, top_n = max(counts.items(), key=lambda kv: kv[1])
        frac = top_n / len(comp_layouts)
        if frac >= MONOTONE_FRAC:
            issues.append("монотонность: %d%% битов композиции — один layout ('%s'), а скелет "
                          "эталона чередует %d разных %s (композиция держит один layout, "
                          "скелет эталона чередует)"
                          % (round(frac * 100), top_lay, len(skel_layouts), sorted(skel_layouts)))
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skeleton", required=True)
    ap.add_argument("--html", default=None)   # опционален: если дан --spec, HTML не нужен (биты из spec.beats[])
    ap.add_argument("--spec", default=None)
    ap.add_argument("--project", default=None)
    a = ap.parse_args()

    if not a.html and not a.spec:
        ap.error("нужен хотя бы один из --html или --spec (источник битов композиции)")

    _anchor = a.html or a.spec or a.skeleton
    proj_root = a.project or os.path.dirname(os.path.abspath(_anchor))
    verdict_path = os.path.join(proj_root, ".skeleton-match-verdict.json")

    # --- Backward-compat: нет скелета → SKIP (exit 0) ---
    if not os.path.isfile(a.skeleton):
        print("\n  SKELETON-MATCH: нет скелета (%s) — skeleton-match не проверяется (SKIP)" % a.skeleton)
        try:
            json.dump({"verdict": "SKIP", "issues": [], "reason": "нет scene-skeleton.json"},
                      open(verdict_path, "w"), ensure_ascii=False, indent=1)
        except Exception:
            pass
        return 0

    try:
        skel = load_json(a.skeleton)
    except Exception as ex:
        print("FAIL: скелет %s не читается как JSON: %s" % (a.skeleton, ex), file=sys.stderr)
        json.dump({"verdict": "FAIL", "issues": ["скелет не читается: %s" % ex]},
                  open(verdict_path, "w"), ensure_ascii=False, indent=1)
        return 2

    # --- источник битов композиции: spec.beats[] → html → FAIL ---
    comp_beats, source, src_err = None, None, None
    if a.spec:
        comp_beats, src_err = beats_from_spec(a.spec)
        source = "spec"
    if comp_beats is None and a.html and os.path.isfile(a.html):
        html_beats, herr = beats_from_html(a.html)
        if html_beats:
            comp_beats, source, src_err = html_beats, "html", None
        elif src_err is None:
            src_err = herr

    if comp_beats is None or len(comp_beats) == 0:
        msg = ("не удалось получить биты композиции — нужен --spec с beats[] или "
               "scene-skeleton соответствие. ")
        if src_err:
            msg += src_err
        elif source != "spec":
            msg += ("в собранном HTML нет data-beat/data-layout атрибутов — передай --spec "
                    "scene.spec.json с beats[].")
        print("\n  SKELETON-MATCH: FAIL — %s" % msg)
        json.dump({"verdict": "FAIL", "issues": [msg]},
                  open(verdict_path, "w"), ensure_ascii=False, indent=1)
        return 2

    issues = check(skel, comp_beats)
    verdict = "FAIL" if issues else "PASS"

    out = {
        "verdict": verdict,
        "skeleton": os.path.basename(a.skeleton),
        "source": source,
        "n_skel": skel.get("n_beats", len(skel.get("beats") or [])),
        "n_comp": len(comp_beats),
        "issues": issues,
    }
    json.dump(out, open(verdict_path, "w"), ensure_ascii=False, indent=1)

    print("\n  SKELETON-MATCH: %s — %s (биты композиции=%d из %s, скелет=%d битов)" % (
        os.path.basename(a.skeleton), verdict, len(comp_beats), source, out["n_skel"]))
    if issues:
        for it in issues:
            print("   x %s" % it)
    else:
        print("   v побитный layout совпадает, аватар full-screen только на bookend/anchor, "
              "нет раскладки дольше скелет-бита, монотонности нет")
    print("   -> %s" % verdict_path)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
