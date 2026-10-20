#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Двусторонняя сверка версий: dzen-engine <-> SEO-движок 2.0 (lead-magnit/seo-engine).

Зачем: правила площадки живут в dzen-engine, общие законы и чекеры - в lead-magnit.
Скрипт ловит момент, когда одна сторона обновилась, а вторая продолжает работать
по вчерашнему канону. Договор сторон описан в CONTRACT.md, машинная часть - в
.engine-contract.json рядом с ним.

Режимы:
  --role engine    (по умолчанию) прогоняет dzen-engine: цел ли донор, не менялся ли он
  --role consumer  прогоняет lead-magnit / statya-na-ploshadku: не менялся ли движок Дзена
  --accept         зафиксировать текущее состояние обеих сторон как эталон (после ревизии)
  --json           машинный вывод

Коды возврата:
  0 - синхронно, работать дальше
  1 - другая сторона обновилась: прочитать изменённые файлы в ЭТОМ же прогоне, затем --accept
  2 - контракт нарушен: файла нет, работа не начинается
"""

import argparse
import hashlib
import json
import os
import re
import sys

SKILLS_ROOT = os.path.expanduser("~/.claude/skills")
ENGINE_DIR = os.path.join(SKILLS_ROOT, "dzen-engine")
CONTRACT_PATH = os.path.join(ENGINE_DIR, ".engine-contract.json")

OK, CHANGED, BROKEN = 0, 1, 2


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def frontmatter_version(skill_md):
    """Достать поле version из frontmatter SKILL.md. None, если файла или поля нет."""
    try:
        with open(skill_md, encoding="utf-8") as f:
            head = f.read(4096)
    except OSError:
        return None
    m = re.search(r"^version:\s*\"?([^\"\n]+)\"?\s*$", head, re.M)
    return m.group(1).strip() if m else None


def load_contract():
    try:
        with open(CONTRACT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        print(f"КОНТРАКТ НЕ ПРОЧИТАН: {e}", file=sys.stderr)
        sys.exit(BROKEN)
    except json.JSONDecodeError as e:
        print(f"КОНТРАКТ БИТЫЙ: {e}", file=sys.stderr)
        sys.exit(BROKEN)


def save_contract(data):
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


def scan(files_map, base=SKILLS_ROOT):
    """
    files_map: {относительный путь: ожидаемый sha256 или null}
    Возвращает (missing, changed, fresh_map)
    """
    missing, changed, fresh = [], [], {}
    for rel, expected in files_map.items():
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            missing.append(rel)
            fresh[rel] = None
            continue
        actual = sha256(path)
        fresh[rel] = actual
        if expected and expected != actual:
            changed.append(rel)
    return missing, changed, fresh


def report(title, missing, changed, soft_missing=None):
    print(title)
    print("-" * 72)
    if missing:
        print(f"[BROKEN] файлов нет ({len(missing)}):")
        for rel in missing:
            print(f"         {rel}")
    if soft_missing:
        print(f"[WARN]   мягкие зависимости отсутствуют ({len(soft_missing)}):")
        for rel in soft_missing:
            print(f"         {rel}")
    if changed:
        print(f"[CHANGED] изменились с последней сверки ({len(changed)}):")
        for rel in changed:
            print(f"         {rel}")
    if not missing and not changed:
        print("[OK]     все файлы на месте и не менялись")
    print("-" * 72)


def main():
    p = argparse.ArgumentParser(description="Сверка dzen-engine и SEO-движка 2.0")
    p.add_argument("--role", choices=["engine", "consumer"], default="engine")
    p.add_argument("--accept", action="store_true",
                   help="зафиксировать текущее состояние как эталон (после ревизии изменений)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    c = load_contract()
    up = c["upstream"]
    engine_version = c["engine"]["version"]
    upstream_skill = os.path.join(SKILLS_ROOT, up["skill_md"])
    upstream_version = frontmatter_version(upstream_skill)

    up_missing, up_changed, up_fresh = scan(up["files"])
    self_missing, self_changed, self_fresh = scan(c["self"]["files"])

    soft = c.get("soft_dependencies", {})
    soft_missing = [rel for rel in soft if not os.path.exists(os.path.join(SKILLS_ROOT, rel))]

    version_drift = (up.get("expected_version") is not None
                     and upstream_version is not None
                     and upstream_version != up["expected_version"])

    if args.accept:
        c["upstream"]["files"] = up_fresh
        c["upstream"]["expected_version"] = upstream_version or up.get("expected_version")
        c["self"]["files"] = self_fresh
        c["self"]["version"] = engine_version
        save_contract(c)
        print("ЗАФИКСИРОВАНО: снимок обеих сторон обновлён в .engine-contract.json")
        print(f"  донор {up['name']} v{upstream_version} · движок dzen-engine v{engine_version}")
        return OK

    if args.role == "engine":
        code = BROKEN if up_missing else (CHANGED if (up_changed or version_drift) else OK)
        payload = {
            "role": "engine",
            "engine_version": engine_version,
            "upstream": up["name"],
            "upstream_version_expected": up.get("expected_version"),
            "upstream_version_actual": upstream_version,
            "version_drift": version_drift,
            "missing": up_missing,
            "changed": up_changed,
            "soft_missing": soft_missing,
            "exit": code,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return code
        report(f"Сверка донора: {up['name']} (ожидается v{up.get('expected_version')}, "
               f"фактически v{upstream_version})",
               up_missing, up_changed, soft_missing)
        if version_drift:
            print(f"[CHANGED] версия донора изменилась: "
                  f"{up.get('expected_version')} -> {upstream_version}")
        if code == BROKEN:
            print("СТОП: донор неполон, конвейер Дзена не запускается")
        elif code == CHANGED:
            print("ДЕЙСТВИЕ: прочитать изменённые файлы донора в этом же прогоне,")
            print("          применить новое, затем: sync-check.py --accept")
        else:
            print("Синхронно - работать дальше")
        return code

    # role = consumer: смотрит на движок Дзена глазами lead-magnit / statya-na-ploshadku
    code = BROKEN if self_missing else (CHANGED if self_changed else OK)
    payload = {
        "role": "consumer",
        "engine": "dzen-engine",
        "engine_version": engine_version,
        "missing": self_missing,
        "changed": self_changed,
        "call": "Skill('dzen-engine')",
        "exit": code,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return code
    report(f"Сверка движка Дзена: dzen-engine v{engine_version}", self_missing, self_changed)
    if code == BROKEN:
        print("СТОП: движок Дзена неполон - дзен-задачу не выполнять по памяти")
    elif code == CHANGED:
        print("ДЕЙСТВИЕ: движок Дзена обновился - перечитать изменённые файлы,")
        print("          дзен-задачу вести через Skill('dzen-engine'), затем: sync-check.py --accept")
    else:
        print("Синхронно - дзен-задачу вести через Skill('dzen-engine')")
    return code


if __name__ == "__main__":
    sys.exit(main())
