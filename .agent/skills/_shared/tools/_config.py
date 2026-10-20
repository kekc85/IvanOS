#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_config.py - крошечный загрузчик config.yaml для инструментов «Скилла статей».

Зачем отдельный модуль. Инструменты config-driven: пороги и пути берутся из
config.yaml проекта. Но ставить ради этого PyYAML - лишняя зависимость. Здесь
самодостаточный мини-парсер ПОДМНОЖЕСТВА YAML, которого хватает для нашего
конфига: вложенные секции через отступы, скаляры (строки/числа/булевы),
инлайн-списки `[a, b]` и блочные списки (`- item`). Чистый stdlib.

Если в проекте уже стоит PyYAML - модуль использует его (точнее и полнее).
Если нет - падает на встроенный мини-парсер и продолжает работать.

Поддерживаемая форма конфига (всё опционально, берутся только нужные ключи):

    tools:
      originality:
        max_cosine: 0.50      # порог косинуса TF-IDF: выше → клон-риск
        max_ngram: 0.30       # порог Jaccard по n-граммам (дословные куски)
        ngram_n: 5            # длина словесной n-граммы
      read_aloud:
        max_sentence_words: 28
        max_word_len: 17
        max_consonant_run: 5
      cadence:
        max_per_1k: 8.0       # суммарная плотность AI-маркеров на 1000 слов
    voice:
      source: "./voice-samples" # папка с образцами голоса (опц., для калибровки)

Все функции чистые, кроме чтения самого файла конфига.
"""
from __future__ import annotations

import os
import re


def find_config(explicit=None):
    """Найти конфиг. Порядок (старые пути первыми, поведение прежних вызовов не меняется):
    явный путь → ./config.yaml → рядом со скриптами → на уровень выше (корень скилла)
    → config.md в корне скилла (yaml-блок из markdown)
    → seo-engine/seo-config-reference.yaml в корне скилла."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.append(os.path.join(os.getcwd(), "config.yaml"))
    here = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(here)
    candidates.append(os.path.join(here, "config.yaml"))
    candidates.append(os.path.join(skill_root, "config.yaml"))
    candidates.append(os.path.join(skill_root, "config.md"))
    candidates.append(os.path.join(skill_root, "seo-engine", "seo-config-reference.yaml"))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def load_config(path):
    """Прочитать конфиг в dict. Нет файла или ошибка чтения - пустой dict (работаем на дефолтах).

    Плейсхолдеры (`<...>`) вырезаются на ЛЮБОМ найденном пути конфига - .yaml и .md
    одинаково (adversarial-дефект 2, по решению автора: find_config() ищет config.yaml раньше
    config.md, и раньше фильтр применялся только к .md-ветке - плейсхолдер вида
    `<твой-домен>` из config.yaml/seo-config-reference.yaml проходил как настоящий адрес).

    Для .md (config.md скилла) - берётся ПЕРВЫЙ ```yaml-блок из markdown (авторские
    значения), а как база дефолтов подмешивается seo-engine/seo-config-reference.yaml
    из того же корня скилла (там живут пороги tools.* - max_cosine, min_internal_links
    и т.д.). Авторские значения побеждают."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return {}
    if path.endswith(".md"):
        author = _strip_placeholders(_parse_yaml_text(_first_yaml_block(raw)))
        ref = os.path.join(os.path.dirname(os.path.abspath(path)),
                           "seo-engine", "seo-config-reference.yaml")
        base = _strip_placeholders(load_config(ref)) if os.path.isfile(ref) else {}
        return _deep_merge(base, author)
    return _strip_placeholders(_parse_yaml_text(raw))


def _strip_placeholders(d):
    """Выкинуть значения-заглушки вида `<твой-домен>/...` (шаблонные поля, не настроенные
    под автора): для инструментов такое значение хуже отсутствия - ловится ложный фейл.
    Применяется ко ВСЕМ форматам конфига, которые проходят через load_config (.yaml и .md
    одинаково) - см. load_config()."""
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            v2 = _strip_placeholders(v)
            if v2 is None and isinstance(v, str):
                continue
            out[k] = v2
        return out
    if isinstance(d, str) and re.search(r"<[^<>]+>", d):
        return None
    return d


def _parse_yaml_text(raw):
    """Разобрать YAML-текст: PyYAML если стоит, иначе встроенный мини-парсер."""
    if not raw:
        return {}
    # Если есть настоящий PyYAML - берём его, он надёжнее мини-парсера.
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return _mini_yaml(raw)


def _first_yaml_block(md_text):
    """Достать первый fenced-блок ```yaml из markdown (второй блок в config.md -
    пример-заглушка ученика, его не берём)."""
    m = re.search(r"```ya?ml\s*\n(.*?)```", md_text, re.DOTALL)
    return m.group(1) if m else ""


def _deep_merge(base, override):
    """Рекурсивно наложить override на base (dict-в-dict), не меняя исходники."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if override is not None else base
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get(cfg, dotted, default=None):
    """Достать вложенный ключ по точечному пути: get(cfg, 'tools.cadence.max_per_1k')."""
    node = cfg
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node if node is not None else default


# ── Мини-парсер YAML-подмножества (fallback, когда PyYAML недоступен) ────────────

def _scalar(token):
    """Привести строковый скаляр к bool/int/float/str/None, снять кавычки и хвостовой #комментарий."""
    s = token.strip()
    if not s:
        return ""
    # обрезать хвостовой комментарий, если значение не в кавычках
    if s[0] not in "\"'":
        hashpos = s.find(" #")
        if hashpos != -1:
            s = s[:hashpos].strip()
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", "none", ""):
        return None
    if re.fullmatch(r"[-+]?\d+", s):
        return int(s)
    if re.fullmatch(r"[-+]?\d*\.\d+", s):
        return float(s)
    return s


def _split_top_commas(s):
    """Разбить строку по запятым верхнего уровня, уважая кавычки."""
    out, buf, quote = [], [], None
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return [p.strip() for p in out]


def _inline_list(token):
    inner = token.strip()[1:-1].strip()
    if not inner:
        return []
    return [_scalar(p) for p in _split_top_commas(inner)]


def _mini_yaml(raw):
    """
    Разобрать вложенные секции / скаляры / списки по отступам.

    Модель: стек кадров [indent, parent_dict, key]. Каждый кадр описывает «куда
    кладётся содержимое этого уровня» - в parent_dict под key. Ключ с пустым
    значением открывает новый уровень: его наполнение (вложенные ключи ИЛИ
    блочный список `- item`) определяется первой строкой-потомком. Поэтому dict
    создаётся лениво - только когда реально приходит вложенный `key:`, а список -
    когда приходит `- `. Так `voice.forbidden:` + `  - item` корректно становится
    списком на любой глубине.

    Покрывает наш config.yaml; экзотику YAML (якоря, многострочные блоки `|`/`>`)
    сознательно не трогает.
    """
    root = {}
    # base-кадр: всё верхнего уровня кладётся в root[None]→root напрямую через _put
    stack = [[-1, {"__root__": root}, "__root__"]]

    def _container(frame):
        """Лениво вернуть dict, лежащий в parent[key], создав его при нужде."""
        parent, key = frame[1], frame[2]
        cur = parent.get(key)
        if not isinstance(cur, dict):
            cur = {}
            parent[key] = cur
        return cur

    def _list(frame):
        """Лениво вернуть list, лежащий в parent[key], создав его при нужде."""
        parent, key = frame[1], frame[2]
        cur = parent.get(key)
        if not isinstance(cur, list):
            cur = []
            parent[key] = cur
        return cur

    for rawline in raw.splitlines():
        if not rawline.strip() or rawline.lstrip().startswith("#"):
            continue
        indent = len(rawline) - len(rawline.lstrip(" "))
        line = rawline.strip()

        # подняться до кадра, чей уровень строго меньше текущего отступа
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        frame = stack[-1]

        # элемент блочного списка: «- value» - наполняет список текущего кадра
        if line.startswith("- ") or line == "-":
            item = _scalar(line[2:]) if len(line) > 2 else None
            _list(frame).append(item)
            continue

        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        container = _container(frame)  # вложенный ключ → текущий уровень это dict

        if rest == "":
            # открыть новый уровень; чем он наполнится (dict/список) - решит потомок
            stack.append([indent, container, key])
            continue

        if rest.startswith("[") and rest.endswith("]"):
            container[key] = _inline_list(rest)
            continue

        container[key] = _scalar(rest)

    return root
