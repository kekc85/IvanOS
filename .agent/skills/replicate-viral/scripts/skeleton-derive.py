#!/usr/bin/env python3
"""
skeleton-derive.py — Фаза 1 «montage skeleton binding»: ВЫВОД СКЕЛЕТА МОНТАЖА из деконструкции.

Превращает верифицированную покадровую деконструкцию источника (`deconstruction.md`,
markdown-таблица формата knowledge/source-deconstruction.md) в детерминированный
`scene-skeleton.json` — нормализованный костяк битов (layout/motion в enum + роль аватара
на бит). Это связующее звено deconstruction → scene.spec: реплика строится по СКЕЛЕТУ
эталона (та же раскладка/динамика/где лицо), а не из догадки (анти Build-on-guess RC-A).

Ключевая логика avatar_role: говорящая голова допустима ТОЛЬКО на букендах (хук/cta,
первый/последний бит) или как continuous-anchor (layout=anchor-rotate); в середине
talking-demo лицо off-screen (absent) — несущая сила = футаж инструмента, не голова
.

usage:
  skeleton-derive.py <deconstruction.md> [--out scene-skeleton.json] [--project DIR]
exit: 0 = OK (скелет выведен), 1 = ошибка (нет файла / нет таблицы) — понятно в stderr.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout_enum import canonical_set as _layout_canonical_set  # ЕДИНЫЙ источник enum (L3)

REQUIRED_COLS = ["t_start", "t_end", "frame", "layout", "shows", "motion", "text", "sfx", "block", "bench"]

# Порядок проб LAYOUT_RULES важен (специфичное раньше общего), поэтому держим УПОРЯДОЧЕННЫЙ
# список вывода скелета. Все его значения ОБЯЗАНЫ быть валидны по единому layout_enum
# (full-demo принимается как алиас full-broll) — assert ниже.
LAYOUT_ENUM = ["full-demo", "split", "full-ui", "full-head", "anchor-rotate"]
assert set(LAYOUT_ENUM) <= _layout_canonical_set(), "LAYOUT_ENUM рассинхронён с layout_enum.py"
LAYOUT_DEFAULT = "full-head"
# Порядок проб важен: специфичное раньше общего (split/full-ui раньше "demo"->full-demo,
# anchor раньше всего общего). Каждый кортеж: (нужные-подстроки-ВСЕ, enum).
LAYOUT_RULES = [
    (["anchor"], "anchor-rotate"),
    (["continuous"], "anchor-rotate"),
    (["full-head"], "full-head"),
    (["talking"], "full-head"),
    (["split"], "split"),
    (["pip"], "split"),
    (["5050"], "split"),
    (["full-ui"], "full-ui"),
    (["demo", "ui"], "full-ui"),
    (["full-broll"], "full-demo"),
    (["full-demo"], "full-demo"),
    (["b-roll"], "full-demo"),
    (["broll"], "full-demo"),
    (["hero"], "full-demo"),
    (["demo"], "full-demo"),
    (["screen"], "full-ui"),
    (["ui"], "full-ui"),
    (["head"], "full-head"),
]

MOTION_ENUM = ["push-in", "cut", "micro-state", "ken-burns", "cursor-trace",
               "highlight-sweep", "static", "video"]
MOTION_DEFAULT = "static"
MOTION_RULES = [
    (["push-in"], "push-in"),
    (["push"], "push-in"),
    (["zoom"], "push-in"),
    (["ken-burns"], "ken-burns"),
    (["ken"], "ken-burns"),
    (["cursor-trace"], "cursor-trace"),
    (["cursor"], "cursor-trace"),
    (["highlight-sweep"], "highlight-sweep"),
    (["highlight"], "highlight-sweep"),
    (["sweep"], "highlight-sweep"),
    (["micro-state"], "micro-state"),
    (["micro"], "micro-state"),
    (["cut"], "cut"),
    (["video"], "video"),
    (["static"], "static"),
]

# Токены, означающие краевой бит (хук/cta). M1-фикс: применяются ТОЛЬКО как ТОЧНОЕ
# равенство bench (после снятия маркеров ★*), НЕ как подстрока — иначе составная метка
# в середине (напр. '★showcase-hook' на бите 2/5) ложно делалась bookend и протаскивала
# говорящую голову в середину. Подстрочное совпадение в середине = НЕ bookend.
BOOKEND_BENCH_TOKENS = ("hook", "cta", "затравка", "хук", "цта")


def normalize(raw, rules, enum, default):
    """Регистронезависимо по подстроке. (норм-значение, известно?)."""
    s = (raw or "").strip().lower()
    if not s or s in ("-", "—"):
        return default, False
    for needles, val in rules:
        if all(n in s for n in needles):
            return val, True
    return default, False


def parse_table(path):
    """Найти markdown-таблицу с нужными колонками (тот же подход, что в deconstruction-check.py).
    Вернуть (rows, header_error)."""
    lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|") and all(c in ln for c in ("t_start", "t_end", "frame", "block")):
            header_idx = i
            break
    if header_idx is None:
        return None, "не найдена таблица деконструкции с колонками %s (источник не табличный?)" % REQUIRED_COLS
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


def clean(v):
    v = (v or "").strip()
    return None if v in ("", "-", "—") else v


def derive(rows):
    """rows -> (skeleton_dict_partial, warnings). Падать НЕ должны — кривые t_* пропускаем."""
    warnings = []
    parsed = []
    for n, r in enumerate(rows):
        try:
            t0 = float(r["t_start"]); t1 = float(r["t_end"])
        except (ValueError, KeyError):
            warnings.append("строка %d: t_start/t_end не число (%r/%r) — пропущена"
                            % (n, r.get("t_start"), r.get("t_end")))
            continue
        parsed.append((t0, t1, r))

    if not parsed:
        return None, warnings, "нет ни одной валидной строки деконструкции (t_start/t_end не распознаны)"

    parsed.sort(key=lambda x: x[0])
    n_beats = len(parsed)
    beats = []
    for i, (t0, t1, r) in enumerate(parsed):
        layout, l_known = normalize(r.get("layout"), LAYOUT_RULES, LAYOUT_ENUM, LAYOUT_DEFAULT)
        if not l_known and clean(r.get("layout")) is not None:
            warnings.append("beat %d: неизвестный layout '%s' → %s" % (i, r.get("layout").strip(), LAYOUT_DEFAULT))
        motion, m_known = normalize(r.get("motion"), MOTION_RULES, MOTION_ENUM, MOTION_DEFAULT)
        if not m_known and clean(r.get("motion")) is not None:
            warnings.append("beat %d: неизвестный motion '%s' → %s" % (i, r.get("motion").strip(), MOTION_DEFAULT))

        bench = clean(r.get("bench"))
        bench_l = (bench or "").lower()
        # M1-фикс: bench-bookend ТОЛЬКО если bench строго РАВЕН токену (после снятия ★*),
        # не in-подстрока. Middle-бит с составной меткой ('★showcase-hook') -> НЕ bookend.
        bench_token = bench_l.strip().lstrip("★* ").strip()
        is_edge = (i == 0 or i == n_beats - 1)
        if is_edge or bench_token in BOOKEND_BENCH_TOKENS:
            avatar_role = "bookend"
        elif layout == "anchor-rotate":
            avatar_role = "anchor"
        else:
            avatar_role = "absent"

        beats.append({
            "i": i,
            "t0": t0,
            "t1": t1,
            "layout": layout,
            "motion": motion,
            "avatar_role": avatar_role,
            "bench": bench,
            "shows": (r.get("shows") or "").strip(),
            "text": (r.get("text") or "").strip(),
            "block": clean(r.get("block")),
        })

    duration = parsed[-1][1]
    return {"n_beats": n_beats, "duration": duration, "beats": beats}, warnings, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deconstruction")
    ap.add_argument("--out", default=None)
    ap.add_argument("--project", default=None)
    a = ap.parse_args()

    if not os.path.isfile(a.deconstruction):
        print("ОШИБКА: нет файла %s" % a.deconstruction, file=sys.stderr)
        return 1

    base_dir = a.project or os.path.dirname(os.path.abspath(a.deconstruction))
    out_path = a.out or os.path.join(base_dir, "scene-skeleton.json")

    try:
        rows, herr = parse_table(a.deconstruction)
    except Exception as e:  # робастность: любой сбой парсинга = понятная ошибка, не стектрейс
        print("ОШИБКА: не удалось прочитать таблицу из %s: %s" % (a.deconstruction, e), file=sys.stderr)
        return 1
    if herr:
        print("ОШИБКА: %s" % herr, file=sys.stderr)
        return 1

    skel, warnings, derr = derive(rows)
    if derr:
        print("ОШИБКА: %s" % derr, file=sys.stderr)
        return 1

    out = {"source": os.path.basename(a.deconstruction)}
    out.update(skel)
    if warnings:
        out["warnings"] = warnings

    try:
        json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print("ОШИБКА: не удалось записать %s: %s" % (out_path, e), file=sys.stderr)
        return 1

    print("\n  SKELETON-DERIVE: %s — %d битов, %.2fс" % (out["source"], out["n_beats"], out["duration"]))
    roles = {}
    for b in skel["beats"]:
        roles[b["avatar_role"]] = roles.get(b["avatar_role"], 0) + 1
    print("   avatar: " + ", ".join("%s=%d" % (k, v) for k, v in sorted(roles.items())))
    if warnings:
        for w in warnings:
            print("   ! %s" % w)
    print("   -> %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
