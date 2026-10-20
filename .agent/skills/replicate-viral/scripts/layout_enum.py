#!/usr/bin/env python3
"""
layout_enum.py — ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ для layout-enum раскладок кадра.

Раньше enum дублировался и РАССИНХРОНИЛСЯ: knowledge/source-deconstruction.md
писал `full-broll`, а skeleton-derive.py / skeleton_common.py / scene-spec.schema
писали `full-demo` — один и тот же слой назван двумя именами. Любая проверка
«layout == layout эталона» дырявилась на этом стыке (full-broll НЕ равно full-demo,
хотя это одно и то же). Теперь ОДИН словарь.

Канон (автор): **full-broll** (раскадровка/деконструкция читает автор).
`full-demo` сохранён как АЛИАС для обратной совместимости со scene-spec.schema.json
и skeleton-match-check (там в спеках исторически `full-demo`). Нормализация
схлопывает алиас в канон, поэтому посекундное сравнение layout перестаёт врать.

Использование:
    from layout_enum import LAYOUT_ENUM, ALIASES, normalize, is_valid, canonical_set
"""

# Канонический список раскладок кадра (порядок: специфичное → общее, важно для проб).
# full-broll = канон (НЕ full-demo). Один источник на весь скилл.
LAYOUT_ENUM = ["full-head", "split", "full-ui", "full-broll", "anchor-rotate"]

# Обратная совместимость: старое имя слоя → канон. Оба ВАЛИДНЫ на входе,
# но нормализуются в одно значение для сравнения «1:1 посекундно».
ALIASES = {"full-demo": "full-broll"}

# Динамичные раскладки: на этих зонах бит ДОЛЖЕН быть мелким (≤1с) для посекундной
# репликации (лицо/сплит = быстрый монтаж у эталонов; залипшая раскладка = провал).
DYNAMIC_LAYOUTS = {"full-head", "split"}


def normalize(v):
    """Привести raw-значение layout к канону через алиас-маппинг.
    Возвращает канон-строку, если значение валидно (∈ enum ИЛИ алиас), иначе None."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s or s in ("-", "—"):
        return None
    s = ALIASES.get(s, s)
    return s if s in LAYOUT_ENUM else None


def is_valid(v):
    """True, если raw-значение распознаётся как валидный layout (с учётом алиасов)."""
    return normalize(v) is not None


def canonical_set():
    """Множество ВСЕХ принимаемых на входе значений (канон + алиас-ключи) — для
    обратной совместимости с потребителями, ждущими set (skeleton_common)."""
    return set(LAYOUT_ENUM) | set(ALIASES.keys())


if __name__ == "__main__":
    # smoke
    assert normalize("full-demo") == "full-broll"
    assert normalize("FULL-BROLL") == "full-broll"
    assert normalize("split") == "split"
    assert normalize("bogus") is None
    assert is_valid("full-demo") and not is_valid("xxx")
    print("layout_enum OK:", LAYOUT_ENUM, "aliases", ALIASES)
