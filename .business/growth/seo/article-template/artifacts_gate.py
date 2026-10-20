#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
artifacts_gate.py - КОД-ГЕЙТ артефактов статьи. Два уровня, один эталон.

ЗАКОН. Публикация без следов конвейера запрещена. Раньше сверка артефактов жила
пунктом чек-листа («Этап 16.1: ls | diff»), то есть промптом - и на пачке в даты запуска
её просто не звали: в каталогах статей нет ни research, ни gates.json, ни retro.
Критичный маршрут = код-гейт, не промпт.

ТРИ УРОВНЯ × ДВА МАРШРУТА (эталон - seo-engine/checklists/_EXPECTED-ARTIFACTS.txt,
секции #@MIN · #@MIN-LEGACY · #@POST · #@FULL):
  --min (по умолчанию) - ОБЯЗАТЕЛЬНЫЙ МИНИМУМ ПЕРЕД ДЕПЛОЕМ, вшит в дверь
                         ftp_publish.py --dir. Роняет деплой.
  --post               - минимум + следы, которые появляются ТОЛЬКО после
                         публикации. Вшит в article_gates --stage publish и в
                         rost.py готово. Роняет отметку «опубликовано».
  --full               - ПОЛНЫЙ 16-этапный след. ЗАМЕР ДОЛГА: печатает, чего нет,
                         и ВСЕГДА выходит с 0. Гейт, роняющий весь корпус, -
                         регресс, его перестают звать.

🔴 ПРОФИЛЬ РЕВИЗИИ (Б10, по решению автора). Гейт был калиброван по РАСКЛАДКЕ $WORK - и
валил ВЕСЬ ревизионный контур. У ревизии раскладка другая: песочница патча несёт
РОВНО `index.html` (пилот перелинковки `_rebuild/r5/interlink-pilot/<slug>/`,
каркас рефреша `_rebuild/r4/refresh-out/<slug>/`), а у страницы, выпущенной до этой редакции, источника в $WORK нет ВООБЩЕ - страница сама себе источник. Требовать с
неё `draft.md|spec.json` значит требовать файл, которого не существует в природе:
замер до фикса - пилот interlink 3/3 FAIL, каркас рефреша 6/6 FAIL, при этом
`artifacts_gate <slug>` по тем же самым страницам давал PASS. Дверь заливки
(`ftp_publish --dir <каталог>`) получает именно ПУТЬ песочницы, поэтому весь
ревизионный маршрут стоял.
  Признак профиля ДЕТЕРМИНИРОВАННЫЙ и не подделывается отсутствием файла:
    каталог лежит внутри $WORK                        → СТАТЬЯ (маршрут new/legacy)
    вне $WORK, но несёт draft.md|spec.json|make_spec.py → СТАТЬЯ (сборка не в $WORK)
    вне $WORK и без источника сборки                  → РЕВИЗИЯ → секция MIN-REVISION
  С ревизии спрашивается ровно две вещи: сама страница `index.html` И
  СВИДЕТЕЛЬСТВО РЕВИЗИИ (что именно и от какой базы патчится). Свидетельство
  ищется в каталоге И в его РОДИТЕЛЕ - на одну пачку патчей его выписывают один
  раз (`interlink-pilot/plan-r5-*.json` покрывает все каталоги пачки).
  Голый каталог с одним `index.html` и без свидетельства = FAIL: иначе профиль
  ревизии становится дырой, через которую едет что угодно, и гейт декоративен.

МАРШРУТ СТАТЬИ (калибровка по решению автора, дефект Б2: один MIN ронял 33 каталога из 38).
Признак ДЕТЕРМИНИРОВАННЫЙ и лежит ВНЕ каталога статьи - отсутствием файла его не
подделать (наличие gates.json как признак было бы круговым: новая статья без
прогона гейтов притворилась бы легаси и уехала мимо замка). Ключ - адрес статьи в
`content-sha-registry.json` (slug → /<page_prefix><slug>/, плюс плоский .html и
список `redirected` из конфига):
  есть в реестре, datePublished >= new_route_since  → НОВЫЙ маршрут  → секция MIN
  есть в реестре, datePublished < new_route_since   → LEGACY         → MIN-LEGACY
  есть в реестре, datePublished не проставлен       → LEGACY         → MIN-LEGACY
  в реестре нет (не публиковалась)                  → НОВЫЙ маршрут  → MIN (fail-closed)
Порог - ключ `new_route_since` конфига (по умолчанию 2026-08-12). Явный `--route`
перебивает автоопределение, `--full` от маршрута не зависит.

СИНТАКСИС ЭТАЛОНА (разбирается здесь, читается глазами там же):
  имя.md        обязателен ровно этот файл/каталог
  a.md|b.md     засчитывается любой из перечисленных (историческое имя ИЛИ новое)
  etap-11-*.png маска fnmatch по содержимому каталога статьи
  имя.md?       условный: канон разрешает законный SKIP, отсутствие не роняет гейт
  @witness:a|b  свидетельство пачки: ищется в каталоге И в его РОДИТЕЛЕ (одно
                свидетельство выписывается на всю пачку патчей, а не на каталог)

МАРКЕР ПРИЗНАННОГО ДОЛГА `*-DOLG.md` (Б6, по решению автора). У пачки в даты запуска ресёрч
ВЁЛСЯ живьём (факты верифицированы оркестратором, журнал plans/2026-08-11-…:76-84),
а файла-артефакта не осталось: Opus лежал, конвейер шёл деградированным. Выдумывать
research.md задним числом запрещено, поэтому в каталоге лежит честная расписка долга
`research-DOLG.md` с датой ревизии. Чтобы расписка не стала дырой в замке:
  · маркер засчитывается ТОЛЬКО у статьи, чей выпуск не позже порога new_route_since
    (datePublished <= порога, а также легаси и redirected);
  · datePublished СТРОГО позже порога = новая статья: она собирается по полному
    конвейеру, маркер долга ей не засчитывается;
  · статьи нет в реестре (не публиковалась) = новая: маркер не в счёт (fail-closed).

ТРИ ПОСТ-АРТЕФАКТА ТОЖЕ ЧИТАЮТСЯ ВНУТРИ (П1, по решению автора, дыра приёмки).
Секция POST закрывалась ИМЕНАМИ ФАЙЛОВ, хотя закон «по содержимому, а не по имени»
для `gates.json`/`index.html` действовал с этой редакции. Живая улика: у `guide-ii-prilozhenie`
внутри `etap-13-geo.md` стоит «Вердикт 13.4a: FAIL» (ось citation[] красная), а
`artifacts_gate --post` печатал «вердикт: PASS» и пропускал статью на выдачу.
Теперь по каждому из трёх:
  · `etap-13-geo.md`  - вердикт Этапа 13.4a внутри обязан быть PASS. FAIL, отсутствие
    строки вердикта, меньше трёх осей или «PASS при красной оси» (расписка спорит
    сама с собой) - строка НЕ закрыта. Ловятся обе живые формы подписи:
    `**Вердикт 13.4a: PASS**` (geo_check.py) и `## Вердикт подэтапа …: PASS` (r9);
  · `etap-12a-index-legs.md` - обязан нести хотя бы ОДИН след реальной отправки
    (`task_id`, `sent_at`/`SENT`, `нога Яндекс: отправлено N>0`, `indexlegs rc=0`,
    код IndexNow 200/202, запись в очередь GSC). Пустой файл, одна шапка,
    незаполненный шаблон (`TODO`/`<URL>`/«заполнить после») и «отправлено 0» -
    пункт НЕ закрыт;
  · `etap-12b-get.txt` - код GET-приёмки обязан быть 200. Кода нет, 404/500/000
    внутри или `size` меньше килобайта - строка НЕ закрыта.

АРТЕФАКТ ЗАСЧИТЫВАЕТСЯ ПО СОДЕРЖИМОМУ, А НЕ ПО ИМЕНИ (В8, по решению автора).
`gates.json` раньше закрывал строку эталона самим фактом существования - то есть
файл с красным вердиктом внутри открывал дверь деплоя. Теперь читаются вердикты:
  · стадия `page` (последний прогон, он же единственная запись стадии) - БЛОКИРУЮЩАЯ:
    verdict != PASS или стадии нет вовсе → артефакт НЕ засчитан, печатается
    «gates.json есть, но page=FAIL»;
  · стадии `draft` и `publish` у опубликованных статей ИНФОРМАЦИОННЫЕ (решение
    фикс-волны 1): печатаются строкой, гейт ими не роняется.

РАСПИСКА ГЕЙТОВ ПРИВЯЗАНА К БАЙТАМ СТРАНИЦЫ (Б16, по решению автора, фикс-волна 13).
Зелёного вердикта мало: он не говорил, ПО КАКОЙ странице выписан. Стадия `page`
теперь несёт `page_sha256` (пишет article_gates), и он обязан совпасть с ЖИВЫМ
index.html рядом. Не совпал или поля нет вовсе (расписка старого формата) -
артефакт НЕ засчитан с одним лечением: `article_gates.py <slug> --stage page`.
Это последнее незавязанное звено цепи доверия: соседние (gates-manifest.json у
ftp_publish, article_verify у stage_to_relay) подписаны содержимым давно.

Запуск:
  python3 artifacts_gate.py <slug|путь-к-каталогу>            # MIN по маршруту
  python3 artifacts_gate.py <slug> --post                     # + post-publish следы
  python3 artifacts_gate.py <slug> --full                     # полный след, exit 0
  python3 artifacts_gate.py <slug> --route legacy             # маршрут вручную
  python3 artifacts_gate.py <путь-к-песочнице-патча>          # профиль ревизии сам
  python3 artifacts_gate.py <slug> --json out.json --quiet
  python3 artifacts_gate.py --selftest                        # позитив + негативы

Коды выхода:
  0 - все обязательные артефакты уровня на месте (или уровень --full: он не роняет);
  1 - чего-то не хватает (список в выводе);
  2 - ошибка входа: нет каталога статьи, нет/пуст эталон, битый аргумент.

Пути (сначала конфиг ~/.config/seo-publish.json, потом канонный фолбэк):
  work_dir             - каталог прогонов (там лежит <slug>/); ещё раньше - переменная $WORK
  expected_artifacts   - файл эталона _EXPECTED-ARTIFACTS.txt
  content_sha_registry - реестр публикаций (по нему определяется маршрут)
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
import tempfile
import time


def отложить(путь, ignore_errors=False):
    """ЗАКОН №0 владельца (по решению автора, дословно «вообще ничего не удаляй, пусть лежит»).

    Обратимая замена сноса: путь ПЕРЕИМЕНОВЫВАЕТСЯ в датированного соседа
    `<имя>.otlozheno-<ГГГГММДД-ЧЧММСС>`. Прежнее имя после вызова свободно -
    ровно тот эффект, ради которого раньше звался снос, - а байты остаются на
    диске и возвращаются обратным переименованием.

    Заведено по решению автора волной 2: страж no-entity-deletion-gate.sh не давал
    ЗАПУСТИТЬ этот гейт из Bash, потому что в теле лежали вызовы удаления
    фикстур селфтеста. Родня по замыслу - такая же функция в article_gates.py,
    image_health.py, uniq.py и ftp_publish.py (патч закона №0 того же дня).
    """
    try:
        if not путь or not os.path.exists(путь):
            return None
        метка = time.strftime("%Y%m%d-%H%M%S")
        цель = "%s.otlozheno-%s" % (путь, метка)
        n = 0
        while os.path.exists(цель):
            n += 1
            цель = "%s.otlozheno-%s-%d" % (путь, метка, n)
        os.rename(путь, цель)
        return цель
    except OSError:
        if ignore_errors:
            return None
        raise


CONFIG_PATH = os.path.expanduser("~/.config/seo-publish.json")

# канонные фолбэки: этот скрипт живёт в доме сборки (не раздаётся ученикам),
# поэтому знать канонные пути ему можно. Раздаваемые артефакты (ftp_publish.py)
# такого права не имеют и ходят ТОЛЬКО через конфиг.
FALLBACK_WORK = os.path.expanduser("~/.business/growth/seo/lead-magnit-work")
FALLBACK_EXPECTED = os.path.expanduser(
    "~/.claude/skills/lead-magnit/seo-engine/checklists/_EXPECTED-ARTIFACTS.txt")
FALLBACK_REGISTRY = os.path.expanduser(
    "~/.business/growth/seo/content-sha-registry.json")

SECTION_MIN = "MIN"
SECTION_MIN_LEGACY = "MIN-LEGACY"
SECTION_MIN_REVISION = "MIN-REVISION"
SECTION_POST = "POST"
SECTION_FULL = "FULL"
SECTIONS = (SECTION_MIN, SECTION_MIN_LEGACY, SECTION_MIN_REVISION,
            SECTION_POST, SECTION_FULL)

LEVELS = ("min", "post", "full")
ROUTES = ("new", "legacy", "revision")
# Б10: признак «это каталог статьи, а не песочница патча». Достаточно ОДНОГО -
# у пачек в даты запуска источник истины = spec.json (генератор make_spec.py рядом),
# у нового конвейера - draft.md. Отсутствие ВСЕХ трёх ВНЕ $WORK и есть ревизия.
ARTICLE_SOURCE_MARKERS = ("draft.md", "spec.json", "make_spec.py")
# префикс строки эталона, которую ищем ещё и в родительском каталоге
WITNESS_PREFIX = "@witness:"
# маркер ПРИЗНАННОГО долга: файл-расписка вместо артефакта, которого физически не
# существует (см. шапку). Класс, а не одно имя: `research-DOLG.md`, `retro-DOLG.md`…
DEBT_SUFFIX = "-DOLG.md"
# машинный отчёт раннера гейтов: засчитывается по вердиктам внутри, не по имени
GATES_JSON = "gates.json"
GATES_BLOCKING_STAGE = "page"      # стадия собранной страницы - она и есть замок
GATES_INFO_STAGES = ("draft", "publish")  # информационные (решение фикс-волны 1)
# порог нового маршрута: статья, выпущенная с этой датой и позже, обязана нести
# полный след конвейера. Всё, что выпущено раньше, конвейера в этом виде не знало
NEW_ROUTE_SINCE = "2026-08-12"
# сама страница: она обязана быть не только на месте, но и НЕПУСТОЙ (фикс-6)
PAGE_HTML = "index.html"
PAGE_MIN_BYTES = 1024
# сколько байт свидетельства читаем, чтобы найти в нём слаг (план пачки ~24 КБ)
WITNESS_READ_LIMIT = 4 * 1024 * 1024

# ── ТРИ ПОСТ-АРТЕФАКТА ЧИТАЮТСЯ ВНУТРИ (П1, по решению автора) ─────────────────────
# Пост-отчёты закрывали строку эталона САМИМ ФАКТОМ СУЩЕСТВОВАНИЯ - ровно тот
# дефект, что уже закрыт у gates.json (В8) и у index.html (фикс-6), просто не
# доведённый до конца секции POST. Живая улика: `guide-ii-prilozhenie` несёт
# внутри `etap-13-geo.md` строку «Вердикт 13.4a: FAIL» (ось citation[] красная),
# а `artifacts_gate --post` печатал «вердикт: PASS» и пропускал статью на выдачу.
# Закон один на весь файл: артефакт засчитывается по СОДЕРЖИМОМУ, а не по имени.
GEO_REPORT = "etap-13-geo.md"          # Этап 13.4a - извлекаемость на проде
INDEX_LEGS = "etap-12a-index-legs.md"  # Этап 12a - обе ноги уведомления
GET_PROBE = "etap-12b-get.txt"         # Этап 12b - GET-приёмка боевого URL
POST_READ_LIMIT = 1 * 1024 * 1024      # отчёты - килобайты, читаем с запасом
# Этап 13.4a пишет РОВНО три оси (geo_check.py::report). Отчёт, в котором осей
# меньше, - не отчёт, а огрызок: вердикт «логическое И трёх осей» под ним не
# стоит ни на чём. Порог = замок от подмены содержимого на заглушку с одной
# зелёной строкой.
GEO_AXES_REQUIRED = 3
# GET-приёмка: канон Этапа 12b ждёт ровно 200. 404/500 - страницы нет или она
# сломана, 000 - curl вообще не доехал (эти три и ловились глазами в отчётах).
GET_OK_CODE = 200


# ── конфиг ───────────────────────────────────────────────────────────────────

def load_cfg(path=None):
    """~/.config/seo-publish.json в dict. Нет файла или битый - пустой dict."""
    p = os.path.expanduser(path or CONFIG_PATH)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {}
    except (ValueError, OSError):
        return {}


def cfg_path(cfg, key, fallback):
    """Путь из конфига по ключу, иначе канонный фолбэк. ~ раскрывается всегда."""
    v = cfg.get(key)
    if isinstance(v, str) and v.strip():
        return os.path.expanduser(v.strip())
    return os.path.expanduser(fallback)


def work_dir(cfg, explicit=None):
    """Каталог прогонов: явный аргумент → $WORK → конфиг → канон."""
    if explicit:
        return os.path.expanduser(explicit)
    env = os.environ.get("WORK")
    if env and env.strip():
        return os.path.expanduser(env.strip())
    return cfg_path(cfg, "work_dir", FALLBACK_WORK)


# ── разбор эталона ───────────────────────────────────────────────────────────

def parse_expected(text):
    """Текст эталона → {"MIN": [entry, ...], "FULL": [entry, ...]}.

    entry = {"raw": строка, "alts": [маска, ...], "optional": bool, "witness": bool}.
    Строки до первого маркера секции считаются MIN: эталон без маркеров
    (старая версия файла) не должен молча выдавать пустой минимум.
    """
    out = {s: [] for s in SECTIONS}
    section = SECTION_MIN
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            tag = s[1:].strip()
            if tag.startswith("@"):
                name = tag[1:].strip().upper()
                if name in out:
                    section = name
            continue
        witness = s.startswith(WITNESS_PREFIX)
        if witness:
            s = s[len(WITNESS_PREFIX):].strip()
        optional = s.endswith("?")
        if optional:
            s = s[:-1].strip()
        alts = [a.strip() for a in s.split("|") if a.strip()]
        if not alts:
            continue
        out[section].append({"raw": s, "alts": alts, "optional": optional,
                             "witness": witness})
    return out


def load_expected(path):
    with open(path, encoding="utf-8") as f:
        return parse_expected(f.read())


# ── профиль каталога (статья / ревизионная песочница) ────────────────────────

def dir_profile(article_dir, cfg=None, work=None):
    """('article'|'revision', улика) - ЧТО нам дали проверить (Б10).

    Гейт зовут двумя способами, и раскладка у них разная:
      · `<slug>` или путь внутри $WORK - КАТАЛОГ СТАТЬИ: там живёт источник
        (draft.md/spec.json), ресёрч, gates.json - с него и спрашивается след;
      · путь к ПЕСОЧНИЦЕ ПАТЧА (`_rebuild/r5/interlink-pilot/<slug>/`,
        `_rebuild/r4/refresh-out/<slug>/`) - там по контракту лежит ровно
        `index.html`, а у страницы, выпущенной до порога, источника в $WORK нет
        вообще: правится УЖЕ опубликованная страница, она сама себе источник.
    Признак вне содержимого-которое-можно-не-положить: сначала МЕСТО каталога
    (внутри $WORK = статья, что бы в нём ни лежало - иначе полупустой каталог
    статьи притворился бы песочницей и уехал мимо замка), потом наличие
    источника сборки. Ни то ни другое - ревизия.
    """
    d = os.path.abspath(os.path.expanduser(str(article_dir))).rstrip(os.sep)
    w = os.path.abspath(work_dir(cfg or {}, work)).rstrip(os.sep)
    rd, rw = os.path.realpath(d), os.path.realpath(w)
    if rd == rw or rd.startswith(rw + os.sep):
        return "article", f"каталог лежит внутри $WORK ({w}) - это каталог статьи"
    try:
        names = set(os.listdir(d))
    except OSError:
        names = set()
    found = [m for m in ARTICLE_SOURCE_MARKERS if m in names]
    if found:
        return "article", (f"вне $WORK, но несёт источник сборки ({', '.join(found)}) - "
                           "каталог статьи, спрашиваю след конвейера")
    return "revision", (f"вне $WORK ({w}) и без источника сборки "
                        f"({'|'.join(ARTICLE_SOURCE_MARKERS)}) - ревизионная песочница: "
                        "правится уже опубликованная страница, источника в $WORK у неё нет")


# ── маршрут статьи (новый конвейер / легаси) ─────────────────────────────────

def registry_keys(cfg, slug):
    """Адреса, под которыми slug может лежать в реестре публикаций, + remote-dir.

    Правило приставки то же, что в ftp_publish.plan_files: каталог `frontir`
    уезжает на прод как /guide-frontir/. Разойдутся правила - маршрут определится
    не по той странице.
    """
    dom = (cfg.get("domain") or "").strip().rstrip("/")
    pref = cfg.get("page_prefix", "guide-")
    rd = slug if slug.startswith(pref) else pref + slug
    if not dom:
        return [], rd
    keys = [f"{dom}/{rd}/", f"{dom}/{rd}.html"]
    if rd != slug:
        keys += [f"{dom}/{slug}/", f"{dom}/{slug}.html"]
    return keys, rd


def registry_lookup(slug, cfg, registry=None):
    """(ключ, запись, ошибка) из реестра публикаций. Не нашли - (None, None, причина)."""
    path = os.path.expanduser(registry) if registry \
        else cfg_path(cfg, "content_sha_registry", FALLBACK_REGISTRY)
    keys, rd = registry_keys(cfg, slug)
    if not os.path.isfile(path):
        return None, None, f"реестра публикаций нет ({path})"
    try:
        with open(path, encoding="utf-8") as f:
            reg = json.load(f)
    except (ValueError, OSError) as e:
        return None, None, f"реестр публикаций не читается ({e})"
    if not isinstance(reg, dict):
        return None, None, "реестр публикаций не словарь"
    for k in keys:
        rec = reg.get(k)
        if isinstance(rec, dict):
            return k, rec, None
    red = cfg.get("redirected") or []
    if isinstance(red, list) and (slug in red or rd in red):
        return f"redirected:{slug}", {}, None
    shown = ", ".join(keys) if keys else "<в конфиге нет domain>"
    return None, None, f"в реестре публикаций нет ни одного адреса из [{shown}]"


def is_published(slug, cfg, registry=None):
    """(опубликована ли, улика). Реестр публикаций - единственный источник факта."""
    key, rec, err = registry_lookup(slug, cfg, registry)
    if key is None:
        return False, f"{err} - статью считаю неопубликованной"
    dp = (rec.get("datePublished") or "").strip()
    return True, (f"{key} в реестре публикаций"
                  + (f", datePublished {dp}" if dp else ", datePublished не проставлен"))


def route_of(slug, cfg, registry=None):
    """(маршрут, улика). Неизвестность = НОВЫЙ маршрут: гейт закрывается, не открывается."""
    since = (cfg.get("new_route_since") or NEW_ROUTE_SINCE).strip()
    key, rec, err = registry_lookup(slug, cfg, registry)
    if key is None:
        return "new", f"{err} - статья не публиковалась, спрашиваю полный MIN (fail-closed)"
    if key.startswith("redirected:"):
        return "legacy", f"«{slug}» в списке redirected конфига - страница выпускалась до {since}"
    dp = (rec.get("datePublished") or "").strip()
    if not dp:
        return "legacy", f"{key} в реестре, datePublished не проставлен - выпуск до порога {since}"
    # ГРАНИЦА == ПОРОГУ разведена явной веткой (М14, по решению автора). На дате, равной
    # порогу, истинны СРАЗУ ДВА правила: маршрут НОВЫЙ (полный MIN) и расписка
    # долга ЗАСЧИТЫВАЕТСЯ. Это не противоречие и не описка, а осознанная развязка
    # под пачку по решению автора: статьи выпущены уже по новому конвейеру, поэтому спрос с
    # них полный, но ресёрч у них вёлся живьём при лежащем Opus и файла-артефакта
    # не осталось - расписка `research-DOLG.md` закрывает ровно эту дырку и
    # ровно у этого дня. Свёрнутые `>=` и `<=` читались как случайное совпадение
    # краёв, поэтому обе границы теперь названы вслух в обеих функциях.
    if dp == since:
        return "new", (f"{key}: datePublished {dp} РОВНО порог {since} - пачка порога "
                       "идёт по НОВОМУ маршруту (полный MIN)")
    if dp > since:
        return "new", f"{key}: datePublished {dp} > порога {since}"
    return "legacy", f"{key}: datePublished {dp} < порога {since}"


def debt_markers_allowed(slug, cfg, registry=None):
    """(можно ли засчитывать маркеры `*-DOLG.md`, улика).

    Расписка долга - это признание по УЖЕ ВЫПУЩЕННОЙ статье, а не способ собрать
    новую без ресёрча. Поэтому право на неё даёт та же детерминированная улика вне
    каталога, что и маршрут: дата выпуска в реестре публикаций.
      выпуск <= порога new_route_since (в т.ч. == порогу, пачка по решению автора)  → можно
      выпуск СТРОГО позже порога                                        → нельзя
      в реестре нет (статья не публиковалась)                           → нельзя
    """
    since = (cfg.get("new_route_since") or NEW_ROUTE_SINCE).strip()
    key, rec, err = registry_lookup(slug, cfg, registry)
    if key is None:
        return False, (f"{err} - статья не выпускалась, признавать долг нечему: "
                       "новая статья собирается по полному конвейеру")
    if key.startswith("redirected:"):
        return True, f"«{slug}» в списке redirected конфига - выпуск до порога {since}"
    dp = (rec.get("datePublished") or "").strip()
    if not dp:
        return True, f"{key} в реестре, datePublished не проставлен - выпуск до порога {since}"
    # ГРАНИЦА == ПОРОГУ (М14): ровно порог = ПАЧКА ПОРОГА, ей расписка положена,
    # и это ЕДИНСТВЕННЫЙ день, когда новый маршрут и признанный долг сходятся на
    # одной статье (обоснование - в комментарии route_of выше). Ветка стоит
    # ОТДЕЛЬНО от `dp < since`, чтобы сдвиг порога в конфиге не растворил
    # исключение пачки внутри общего `<=` и не выдал его новому дню молча.
    if dp == since:
        return True, (f"{key}: datePublished {dp} РОВНО порог {since} - пачка порога, "
                      "признанный долг (единственный день, где новый маршрут и "
                      "расписка сходятся)")
    if dp > since:
        return False, (f"{key}: datePublished {dp} строго позже порога {since} - "
                       "это новая статья, маркер долга ей не засчитывается")
    return True, f"{key}: datePublished {dp} < порога {since} - легаси, долг признан"


def is_debt_marker(name):
    """Имя (или маска эталона) - расписка признанного долга?"""
    return bool(name) and name.endswith(DEBT_SUFFIX)


def file_sha256(path):
    """sha256 файла или None (нет файла / не читается)."""
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


# 🔴 ОДНА ФОРМУЛИРОВКА ОТКАЗА НА ВСЮ ЦЕПЬ (Б16, скептик-13, по решению автора).
# И здесь, и в ftp_publish отказ по расхождению байтов обязан читаться одинаково
# и называть ОДНО лечение: расписку не «чинят», её перегоняют.
GATES_BYTES_FIX = "перегони article_gates.py <slug> --stage page"


def gates_json_state(path, page_path=None):
    """(засчитан ли gates.json, пояснение) - по ВЕРДИКТАМ и БАЙТАМ, не по имени.

    Блокирует только стадия `page`: она про собранную страницу, которая уезжает на
    прод. Записи стадий перезаписываются каждым прогоном, поэтому `verdict` стадии
    и есть ПОСЛЕДНИЙ вердикт. `draft`/`publish` у опубликованной статьи печатаются
    справочно и гейт не роняют - иначе замок деплоя ронял бы весь корпус.

    🔴 Б16 (скептик-13, по решению автора). ВЕРДИКТА МАЛО - НУЖНЫ БАЙТЫ. Расписка
    говорила «page=PASS» и молчала о том, ПО КАКОЙ СТРАНИЦЕ она выписана:
    пересборка index.html + впись мусора + переминт давали зелёную бумагу на
    байты, которые обязательный гейт стадии (strip_notes) отвергает, а gates.json
    от этой редакции 17:48 рядом с index.html от этой редакции никого не смущал. Теперь запись
    стадии несёт `page_sha256` (пишет article_gates), и он обязан совпасть с
    ЖИВЫМ index.html рядом. Поля нет (расписка старого формата) - тот же отказ:
    «гонялись на неизвестных байтах» - это ровно то же самое, что «гонялись на
    других», и лечится одной командой перегона.
    """
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (ValueError, OSError) as e:
        return False, f"{GATES_JSON} есть, но не читается ({e})"
    if not isinstance(doc, dict):
        return False, f"{GATES_JSON} есть, но это не словарь прогонов"
    stages = doc.get("stages")
    if not isinstance(stages, dict) or not stages:
        return False, f"{GATES_JSON} есть, но прогонов в нём нет (stages пуст)"
    info = []
    for s in GATES_INFO_STAGES:
        rec = stages.get(s)
        if isinstance(rec, dict) and rec.get("verdict"):
            info.append(f"{s}={rec.get('verdict')}")
    tail = f"; информационно: {', '.join(info)}" if info else ""
    st = stages.get(GATES_BLOCKING_STAGE)
    if not isinstance(st, dict):
        return False, (f"{GATES_JSON} есть, но стадии {GATES_BLOCKING_STAGE} в нём нет "
                       f"(прогоны: {', '.join(sorted(stages))}){tail} - "
                       "собранная страница гейтами не проверена")
    verdict = str(st.get("verdict") or "").upper() or "?"
    if verdict != "PASS":
        return False, f"{GATES_JSON} есть, но {GATES_BLOCKING_STAGE}={verdict}{tail}"
    # ── Б16: вердикт зелёный. Теперь - НА КАКИХ БАЙТАХ он получен ──
    page = page_path or os.path.join(os.path.dirname(os.path.abspath(path)), PAGE_HTML)
    подписано = st.get("page_sha256")
    живой = file_sha256(page)
    if not подписано:
        return False, (f"{GATES_JSON}: {GATES_BLOCKING_STAGE}=PASS, но записи стадии "
                       f"нечем подписаться - поля page_sha256 в ней нет (расписка "
                       f"старого формата, до этой редакции). Гейты гонялись на "
                       f"НЕИЗВЕСТНЫХ байтах: {GATES_BYTES_FIX}{tail}")
    if живой is None:
        return False, (f"{GATES_JSON}: {GATES_BLOCKING_STAGE}=PASS на sha "
                       f"{str(подписано)[:12]}, а живой {PAGE_HTML} рядом не читается "
                       f"({page}) - сверять расписку не с чем{tail}")
    if живой != подписано:
        return False, (f"{GATES_JSON}: гейты гонялись на ДРУГИХ байтах - стадия "
                       f"{GATES_BLOCKING_STAGE} подписана sha {str(подписано)[:12]} "
                       f"(прогон {st.get('ran_at')}), а живой {PAGE_HTML} сейчас "
                       f"{живой[:12]}. Страницу пересобирали после гейтов: "
                       f"{GATES_BYTES_FIX}{tail}")
    return True, (f"{GATES_JSON}: {GATES_BLOCKING_STAGE}=PASS на живых байтах "
                  f"(sha {живой[:12]}){tail}")


def page_state(path):
    """(засчитана ли страница, пояснение) - index.html обязан быть НЕПУСТЫМ.

    Фикс-6, по решению автора. У профиля ревизии эталон спрашивает ровно две строки, и
    одна из них - сама страница. Пока строка закрывалась фактом существования
    файла, пустой (или обрезанный на середине заливки) `index.html` открывал
    дверь: `touch index.html` в песочнице давал PASS. Порог намеренно грубый -
    1 КБ: любая реальная страница корпуса весит от 100 КБ, а 0-1 КБ это либо
    пусто, либо обрывок.
    """
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return False, f"{PAGE_HTML} не прочитать ({e})"
    if size <= PAGE_MIN_BYTES:
        return False, (f"{PAGE_HTML} есть, но он пустой/обрезанный ({size} б <= "
                       f"{PAGE_MIN_BYTES} б) - заливать нечего")
    return True, ""


def witness_mentions_slug(path, slug):
    """(упоминает ли свидетельство ЭТОТ каталог, пояснение) - фикс-6.

    Свидетельство из РОДИТЕЛЯ раньше засчитывалось любому каталогу-соседу: файл
    `plan-r5-20260812.json` лежит уровнем выше, значит `mkdir chuzhaya-papka &&
    cp index.html` рядом с пачкой получал PASS по чужому плану. Свидетельство
    обязано ГОВОРИТЬ ПРО ЭТУ страницу: у плана патча - слаг в списке страниц, у
    `changes.md` - слаг в тексте. Не упоминает = свидетельства на этот каталог
    нет, строка не закрыта.
    Проверка только для находки В РОДИТЕЛЕ: файл, лежащий В САМОМ каталоге, и так
    относится только к нему.
    """
    try:
        with open(path, "rb") as f:
            raw = f.read(WITNESS_READ_LIMIT)
    except OSError as e:
        return False, f"свидетельство не прочитать ({e})"
    text = raw.decode("utf-8", "replace")
    # план пачки: слаг обязан быть В СПИСКЕ СТРАНИЦ, а не где-нибудь в примечании.
    # Сверяем именно АДРЕСА страниц, а не любую строку внутри плана: в записи
    # страницы лежат готовые команды деплоя с абсолютными путями, и подстрока
    # «source-patches» из чужого пути делала бы соседний каталог «упомянутым»
    try:
        doc = json.loads(text)
    except ValueError:
        doc = None
    if isinstance(doc, dict) and doc.get("pages") is not None:
        адреса = page_identities(doc.get("pages"))
        if slug in адреса:
            return True, ""
        return False, (f"свидетельство есть, но в его списке страниц (pages) нет "
                       f"{slug} - оно выписано на ЧУЖУЮ пачку "
                       f"({', '.join(sorted(адреса)[:5]) or 'адресов не разобрать'})")
    if re.search(r"(?<![0-9A-Za-zА-Яа-я_-])" + re.escape(slug)
                 + r"(?![0-9A-Za-zА-Яа-я_-])", text):
        return True, ""
    return False, (f"свидетельство есть, но про {slug} в нём не сказано ни слова - "
                   "оно выписано на другой каталог")


def page_identities(pages):
    """Множество слагов, которые план патча реально называет СТРАНИЦАМИ.

    Форма плана бывает разной: dict «адрес → запись» (пилот перелинковки) или
    список записей/строк. Берём только то, что является АДРЕСОМ страницы -
    ключи словаря, а у записей поля slug/url/path/page. Вложенные команды и пути
    внутри записи не в счёт: там лежат готовые строки деплоя, и любая из них
    сделала бы «упомянутым» кого угодно.
    """
    из = set()

    def _добавить(v):
        if not isinstance(v, str) or not v.strip():
            return
        сегмент = v.split("#")[0].split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        if сегмент.endswith(".html"):
            сегмент = сегмент[:-5]
        if сегмент:
            из.add(сегмент)

    if isinstance(pages, dict):
        for k, v in pages.items():
            _добавить(str(k))
            if isinstance(v, dict):
                for поле in ("slug", "url", "path", "page"):
                    _добавить(v.get(поле))
    elif isinstance(pages, (list, tuple)):
        for item in pages:
            if isinstance(item, str):
                _добавить(item)
            elif isinstance(item, dict):
                for поле in ("slug", "url", "path", "page"):
                    _добавить(item.get(поле))
    return из


# ── содержимое трёх пост-артефактов (П1, по решению автора) ────────────────────────
#
# 🔴 ПОЧЕМУ ЭТО БЛОКИРУЕТ, А НЕ ПРЕДУПРЕЖДАЕТ. Канон движка уже решил этот
# вопрос дважды и одинаково: `gates.json` с красным вердиктом внутри строку НЕ
# закрывает (В8), пустой `index.html` строку НЕ закрывает (фикс-6). Секция POST
# - тот же класс: её три файла и есть «третий замок» методологии (12b GET-приёмка,
# 13.4a извлекаемость, 12a обе ноги уведомления). Громкий WARN тут был бы хуже
# декоративного гейта: строка «вердикт: PASS» в машинном отчёте стадии publish
# читается автоматикой выше (rost.py готово, отметка «опубликовано»), а не
# глазами, и никакой WARN её не остановит.

def _read_text(path, limit=POST_READ_LIMIT):
    """(текст, ошибка). Читаем терпимо к кодировке - отчёты пишут разные волны."""
    try:
        with open(path, "rb") as f:
            raw = f.read(limit)
    except OSError as e:
        return None, str(e)
    return raw.decode("utf-8", "replace"), None


# Строка итога Этапа 13.4a. Двумя формами она живёт в корпусе, и обе законные:
#   `**Вердикт 13.4a: PASS** (логическое И трёх осей)` - пишет geo_check.py
#   `## Вердикт подэтапа (логическое И): PASS`         - рукописная форма r9
# Ловим ОБЕ: узкий regex под одну форму сделал бы десять статей r9 «без вердикта».
GEO_VERDICT_RE = re.compile(r"вердикт[^\n:]{0,80}:\s*\**\s*([A-Za-zА-Яа-я]{2,12})", re.I)
# Ось отчёта: `## 1. FAQPage дословно равна видимому тексту - OK`
GEO_AXIS_RE = re.compile(r"(?m)^##\s*(\d+)\.\s*(.+?)\s*[-–—]\s*(OK|FAIL|SKIP)\s*$")


def geo_report_state(path):
    """(засчитан ли etap-13-geo.md, пояснение) - по ВЕРДИКТУ внутри, не по имени.

    Живой дефект по решению автора: `guide-ii-prilozhenie` несёт «Вердикт 13.4a: FAIL»
    (ось 3, citation[] отражает 3 источника из 5), а гейт печатал PASS.
    Отчёт про извлекаемость контента поисковиками - смысл SEO-статьи целиком:
    красный вердикт внутри = статья на выдаче не читается машинами, и «готово»
    по ней произносить нельзя.

    Три отказа, каждый со своей причиной:
      · вердикта в отчёте нет вовсе → отчёт не доведён до вывода (или заглушка);
      · вердикт FAIL → строка не закрыта, названы красные оси;
      · вердикт PASS, но какая-то ось FAIL → отчёт спорит сам с собой (вердикт
        по канону = логическое И трёх осей), верим осям, а не подписи.
    """
    text, err = _read_text(path)
    if text is None:
        return False, f"{GEO_REPORT} не прочитать ({err})"
    axes = GEO_AXIS_RE.findall(text)
    красные = [f"ось {n} ({name})" for n, name, mark in axes if mark == "FAIL"]
    хвост = (f"; оси: " + ", ".join(f"{n}={mark}" for n, _, mark in axes)) if axes else ""
    verdicts = [m.group(1).upper() for m in GEO_VERDICT_RE.finditer(text)]
    verdicts = [v for v in verdicts if v in ("PASS", "FAIL", "SKIP")]
    if not verdicts:
        return False, (f"{GEO_REPORT} есть, но строки вердикта в нём нет - Этап 13.4a "
                       f"не доведён до вывода{хвост}. Лечение: python3 "
                       f"article-template/geo_check.py <slug> --work <WORK> --write")
    verdict = verdicts[-1]
    if verdict == "FAIL":
        return False, (f"{GEO_REPORT}: внутри «Вердикт 13.4a: FAIL» - извлекаемость "
                       f"боевой страницы не закрыта"
                       + (f" ({', '.join(красные)})" if красные else "") + хвост)
    if len(axes) < GEO_AXES_REQUIRED:
        return False, (f"{GEO_REPORT}: вердикт {verdict}, но осей в отчёте "
                       f"{len(axes)} из {GEO_AXES_REQUIRED} - подпись стоит не на "
                       f"проверках, а на пустом месте{хвост}")
    if красные:
        return False, (f"{GEO_REPORT}: подпись говорит {verdict}, а оси - нет "
                       f"({', '.join(красные)}). Вердикт 13.4a по канону = логическое "
                       f"И трёх осей, значит расписка спорит сама с собой{хвост}")
    if verdict != "PASS":
        return False, (f"{GEO_REPORT}: вердикт {verdict} - это не PASS, "
                       f"извлекаемость не подтверждена{хвост}")
    return True, f"{GEO_REPORT}: Вердикт 13.4a PASS{хвост}"


# Признаки РЕАЛЬНОЙ отправки (Этап 12a). Достаточно одного - каналов у ноги
# несколько и пишут они по-разному, а вот заглушка не даёт ни одного:
#   `нога Яндекс: отправлено N`      - машинный вывод ftp_publish --index-legs
#   `task_id <uuid>` / `sent_at`     - реестр переобхода yandex_recrawl.py
#   `SENT` / `SENT-API` / `sent_via` - журналы отправки Яндекса и GSC
#   `indexlegs rc=0`                 - код возврата ноги внутри эстафеты
#   `"pinged"` / IndexNow 200|202    - живой ответ эндпоинтов IndexNow
#   `очередь GSC: добавлено N ... всего M` - вторая нога, запись в очередь
INDEX_LEGS_SIGNS = (
    (re.compile(r"нога\s+Яндекс[^\n]*отправлено\s+([1-9]\d*)", re.I), "нога Яндекс: отправлено"),
    (re.compile(r"task_id[\"'\s:=]+([0-9a-f]{8}-[0-9a-f-]{8,})", re.I), "task_id заявки переобхода"),
    (re.compile(r"\bsent_at\b|\bSENT-API\b|\bSENT:\b|\bsent_via\b"), "запись отправки (sent_at/SENT)"),
    (re.compile(r"indexlegs\s+rc\s*=\s*0"), "indexlegs rc=0"),
    (re.compile(r"\"pinged\"|indexnow[\"'\s:/]*[^\n]{0,80}\"?(200|202)\"?", re.I), "ответ IndexNow"),
    (re.compile(r"очередь\s+GSC:\s*добавлено\s+\d+[^\n]*всего\s+\d+", re.I), "запись в очередь GSC"),
)
# Заглушка/шаблон: расписка, которую ещё не заполнили. Ловим отдельно от
# «признаков нет» - причина отказа разная, и лечение тоже разное.
#
# 🔴 РЕГИСТР ЗДЕСЬ НЕСУЩИЙ, А НЕ КОСМЕТИКА (ловля ложной красноты по решению автора).
# Первая редакция гнала эти маркеры через re.I - и покрасила ВОСЕМЬ здоровых
# отчётов на литерале `<url>`: внутри 12a лежит УЛИКА из живой карты сайта
# (`<url><loc>https://…</loc><lastmod>…`), то есть обычный XML-тег sitemap, а не
# незаполненный плейсхолдер. Плейсхолдеры шаблона пишут КАПСОМ (`<URL>`, `TODO`),
# XML-теги - строчными, и этого различия достаточно. Русские формулировки
# регистру не подчиняются, поэтому они вынесены во вторую половину с re.I.
INDEX_LEGS_STUB_UPPER = re.compile(
    r"\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|<URL>|<SLUG>|<СЛАГ>|<ЗАПОЛНИТЬ")
INDEX_LEGS_STUB_RU = re.compile(
    r"заглушк|плейсхолдер|заполнить\s+после|шаблон\s+отчёта|подставить\s+сюда", re.I)
# Явный негатив: нога не закрылась. Ноль отправок - это не «отправка», это отчёт
# о провале, и строку эталона он закрывать не имеет права
INDEX_LEGS_ZERO = re.compile(r"нога\s+Яндекс[^\n]*отправлено\s+0(?!\d)", re.I)
INDEX_LEGS_MIN_BYTES = 60


def index_legs_state(path):
    """(засчитан ли etap-12a-index-legs.md, пояснение) - по СЛЕДАМ отправки.

    Пустой файл или незаполненный шаблон = пункт НЕ закрыт: обе ноги уведомления
    поисковиков либо ушли и оставили улику (task_id, время, статус, код ответа),
    либо не ушли. Форма отчёта у волн разная (машинный вывод ftp_publish, выписка
    из реестра переобхода, сводка эстафеты) - поэтому спрашивается не формат, а
    наличие хотя бы одного НЕПОДДЕЛЬНОГО следа отправки.
    """
    text, err = _read_text(path)
    if text is None:
        return False, f"{INDEX_LEGS} не прочитать ({err})"
    тело = "\n".join(l for l in text.splitlines()
                     if l.strip() and not l.strip().startswith("#"))
    if len(тело.encode("utf-8")) < INDEX_LEGS_MIN_BYTES:
        return False, (f"{INDEX_LEGS} есть, но он пустой/один заголовок "
                       f"({len(тело.encode('utf-8'))} б без шапки) - обе ноги "
                       f"уведомления ничем не подтверждены")
    if INDEX_LEGS_ZERO.search(text):
        return False, (f"{INDEX_LEGS}: внутри «нога Яндекс: отправлено 0» - нога не "
                       f"закрылась ни на одном эндпоинте, это отчёт о провале")
    заглушка = INDEX_LEGS_STUB_UPPER.search(text) or INDEX_LEGS_STUB_RU.search(text)
    if заглушка:
        return False, (f"{INDEX_LEGS}: это незаполненный шаблон, а не отчёт "
                       f"(маркер «{заглушка.group(0)}») - пункт не закрыт")
    нашли = [имя for rx, имя in INDEX_LEGS_SIGNS if rx.search(text)]
    if not нашли:
        return False, (f"{INDEX_LEGS} есть, но ни одного следа реальной отправки в "
                       f"нём нет (ждём task_id / sent_at / «нога Яндекс: отправлено N» / "
                       f"«очередь GSC: добавлено N» / код IndexNow) - пункт не закрыт")
    return True, f"{INDEX_LEGS}: следы отправки на месте ({', '.join(нашли)})"


# Код ответа GET-приёмки. Формы, встречающиеся у волн: `HTTP=200 size=...`
# (наш пробник), `HTTP/1.1 200 OK` и `http_code=200` (сырой curl).
GET_CODE_RE = re.compile(r"(?:HTTP\s*/\s*[\d.]+\s+|HTTP[\s=:]+|http_code[\s=:]+|"
                         r"код[\s=:]+)(\d{3})\b", re.I)
GET_SIZE_RE = re.compile(r"\bsize[\s=:]+(\d+)\b", re.I)


def get_probe_state(path):
    """(засчитан ли etap-12b-get.txt, пояснение) - код ответа обязан быть 200.

    Канон Этапа 12b: «GET-приёмка боевого URL, ожидаем HTTP=200. Без него слово
    "готово" не произносится ни в чате, ни в чек-листе». Пока строка закрывалась
    именем файла, приёмка с 404 (страницы нет), 500 (движок лёг) или 000 (curl
    не доехал вовсе) уезжала на выдачу под зелёной распиской.
    """
    text, err = _read_text(path)
    if text is None:
        return False, f"{GET_PROBE} не прочитать ({err})"
    коды = [int(c) for c in GET_CODE_RE.findall(text)]
    if not коды:
        return False, (f"{GET_PROBE} есть, но кода ответа в нём нет (ждём строку вида "
                       f"«HTTP={GET_OK_CODE} size=… time=…») - приёмка не проведена")
    плохие = sorted({c for c in коды if c != GET_OK_CODE})
    if плохие:
        return False, (f"{GET_PROBE}: код ответа "
                       f"{', '.join(str(c) for c in плохие)} вместо {GET_OK_CODE} - "
                       f"боевой URL приёмку не прошёл"
                       + (" (000 = запрос вообще не доехал)" if 0 in плохие else ""))
    размеры = [int(s) for s in GET_SIZE_RE.findall(text)]
    пустые = [s for s in размеры if s <= PAGE_MIN_BYTES]
    if пустые:
        return False, (f"{GET_PROBE}: код {GET_OK_CODE}, но тело ответа {пустые[0]} б "
                       f"(<= {PAGE_MIN_BYTES} б) - по адресу лежит пустышка, а не статья")
    return True, (f"{GET_PROBE}: HTTP={GET_OK_CODE}"
                  + (f", тело {размеры[0]} б" if размеры else ""))


# Одна таблица на все проверки содержимого: имя артефакта → функция (годен, почему).
# Держим списком, а не цепочкой if - чтобы новый пост-артефакт нельзя было
# завести в эталоне и забыть про его содержимое (селфтест сверяет обе стороны).
CONTENT_CHECKS = {
    GATES_JSON: gates_json_state,
    PAGE_HTML: page_state,
    GEO_REPORT: geo_report_state,
    INDEX_LEGS: index_legs_state,
    GET_PROBE: get_probe_state,
}


def validate_hit(article_dir, hit):
    """(годен ли найденный артефакт, пояснение). Пусто - проверять нечего по имени."""
    check = CONTENT_CHECKS.get(hit)
    if check:
        return check(os.path.join(article_dir, hit))
    return True, ""


def entries_for(expected, level, route):
    """Строки эталона под уровень и маршрут. Дубли между секциями схлопываются."""
    if route == "revision":
        base = expected[SECTION_MIN_REVISION]
    elif route == "legacy":
        base = expected[SECTION_MIN_LEGACY]
    else:
        base = expected[SECTION_MIN]
    if level == "min":
        rows = list(base)
    elif level == "post":
        rows = list(base) + list(expected[SECTION_POST])
    else:
        # full - ЗАМЕР ДОЛГА КАТАЛОГА СТАТЬИ, маршрут на состав не влияет.
        # MIN-REVISION сюда НЕ входит намеренно: свидетельство ревизии - это след
        # песочницы патча, а не след 16-этапного конвейера. Втащив его в --full,
        # мы бы дописали всем 47 каталогам корпуса долг, которого у них нет.
        rows = (list(expected[SECTION_MIN]) + list(expected[SECTION_MIN_LEGACY])
                + list(expected[SECTION_POST]) + list(expected[SECTION_FULL]))
    seen, out = set(), []
    for e in rows:
        if e["raw"] in seen:
            continue
        seen.add(e["raw"])
        out.append(e)
    return out


# ── сверка ───────────────────────────────────────────────────────────────────

def match_entry(entry, names, debt_ok=True):
    """Какое имя из каталога закрыло строку эталона (или None).

    `debt_ok=False` - маркеры признанного долга (`*-DOLG.md`) не засчитываются:
    ни как альтернатива эталона, ни как файл, подошедший под маску.
    """
    for pat in entry["alts"]:
        if is_debt_marker(pat) and not debt_ok:
            continue
        if pat in names and not (is_debt_marker(pat) and not debt_ok):
            return pat
        hits = sorted(n for n in names if fnmatch.fnmatch(n, pat)
                      and not (is_debt_marker(n) and not debt_ok))
        if hits:
            return hits[0]
    return None


def parent_names(article_dir):
    """(путь родителя, имена в нём). Нечитаемый родитель - пустое множество.

    Свидетельство ревизии выписывается НА ПАЧКУ патчей, а не на каждый каталог:
    `interlink-pilot/plan-r5-20260812.json` один на три каталога пачки. Ровно
    ОДИН уровень вверх - дальше начинается чужая волна.
    """
    parent = os.path.dirname(os.path.abspath(str(article_dir).rstrip(os.sep)))
    if not parent or parent == os.path.abspath(str(article_dir).rstrip(os.sep)):
        return parent, set()
    try:
        return parent, set(os.listdir(parent))
    except OSError:
        return parent, set()


def check_dir(article_dir, entries, debt_ok=True):
    """[(entry, найденное_имя|None, пояснение)] по содержимому каталога статьи.

    Артефакт, найденный по имени, ещё проверяется по СОДЕРЖИМОМУ (В8): красный
    вердикт внутри `gates.json` строку эталона не закрывает.
    Строка-свидетельство (`@witness:`) ищется в каталоге, а если там нет - в его
    родителе (Б10: свидетельство пачки лежит рядом с каталогами пачки).
    """
    names = set(os.listdir(article_dir))
    slug = os.path.basename(os.path.abspath(str(article_dir).rstrip(os.sep)))
    rows = []
    parent = pnames = None
    for e in entries:
        hit = match_entry(e, names, debt_ok)
        where = article_dir
        note = ""
        if not hit and e.get("witness"):
            if pnames is None:
                parent, pnames = parent_names(article_dir)
            up = match_entry(e, pnames, debt_ok)
            if up:
                # фикс-6: чужой план пачки на соседний каталог не распространяется
                годно, почему = witness_mentions_slug(os.path.join(parent, up), slug)
                if годно:
                    hit, where = up, parent
                else:
                    note = f"{up} (родитель {parent}): {почему}"
        if hit:
            ok, note = validate_hit(where, hit)
            if not ok:
                hit = None
            elif e.get("witness"):
                note = (f"свидетельство ревизии: {hit}"
                        + (f" (в родительском каталоге {where}, упоминает {slug})"
                           if where != article_dir else ""))
        rows.append((e, hit, note))
    return rows


def run(article_dir, expected, level, route="new", route_why="",
        debt_ok=True, debt_why="", profile="", profile_why=""):
    """Свод по уровню и маршруту. `full` считает долг и вердиктом не роняет."""
    entries = entries_for(expected, level, route)
    checked = check_dir(article_dir, entries, debt_ok)
    rows = [(e, hit) for e, hit, _ in checked]
    notes = [n for _, _, n in checked if n]
    found = [(e, hit) for e, hit in rows if hit]
    missing = [e for e, hit in rows if not hit and not e["optional"]]
    skipped = [e for e, hit in rows if not hit and e["optional"]]
    verdict = "PASS" if not missing else "FAIL"
    if level == "full":
        # замер долга: печатаем всё как есть, но вердикт не красный - иначе гейт
        # роняет весь архив и его перестают звать (тот же регресс, что чиним)
        verdict = "DEBT" if missing else "PASS"
    return {"dir": article_dir, "level": level, "route": route, "route_why": route_why,
            "profile": profile, "profile_why": profile_why,
            "debt_markers": bool(debt_ok), "debt_why": debt_why,
            "total": len(rows), "found": len(found),
            "missing": [e["raw"] for e in missing],
            "conditional_missing": [e["raw"] for e in skipped],
            "matched": {e["raw"]: hit for e, hit in found},
            "notes": notes,
            "verdict": verdict}


def report(res, quiet=False):
    if quiet:
        if res["verdict"] not in ("PASS",):
            tag = "ДОЛГ" if res["verdict"] == "DEBT" else "НЕТ"
            print(f"артефакты {res['level'].upper()} [{res['route']}]: "
                  f"{tag} {len(res['missing'])} - " + ", ".join(res["missing"]))
            for n in res.get("notes") or []:
                print(f"  {n}")
        return
    slug = os.path.basename(res["dir"].rstrip("/"))
    print(f"артефакты [{res['level'].upper()} · маршрут {res['route']}] {slug}: "
          f"{res['found']}/{res['total']} на месте")
    if res.get("profile_why"):
        print(f"  профиль каталога: {res.get('profile') or '?'} - {res['profile_why']}")
    if res.get("route_why"):
        print(f"  маршрут по признаку: {res['route_why']}")
    if res.get("debt_why"):
        print(f"  маркер долга {'*' + DEBT_SUFFIX}: "
              f"{'засчитывается' if res.get('debt_markers') else 'НЕ засчитывается'} - "
              f"{res['debt_why']}")
    for n in res.get("notes") or []:
        print(f"  содержимое: {n}")
    if res["missing"]:
        head = "ДОЛГ" if res["verdict"] == "DEBT" else "НЕТ"
        print(f"  {head} ({len(res['missing'])}):")
        for m in res["missing"]:
            print(f"    - {m}")
    if res["conditional_missing"]:
        print(f"  условно нет ({len(res['conditional_missing'])}, законный SKIP по канону): "
              + ", ".join(res["conditional_missing"]))
    if res["verdict"] == "DEBT":
        print("  вердикт: ДОЛГ ЗАМЕРЕН (уровень --full не роняет, exit 0)")
    else:
        print(f"  вердикт: {res['verdict']}")


# ── selftest ─────────────────────────────────────────────────────────────────

SELFTEST_EXPECTED = """
# заголовок-комментарий
#@MIN
draft.md|spec.json
research.md|research-external.md|research-DOLG.md
index.html
#@MIN-LEGACY
index.html
draft.md|spec.json
#@MIN-REVISION
index.html
@witness:changes.md|base_sha*|plan-*.json
#@POST
etap-12a-index-legs.md
#@FULL
retro.md
etap-11-desktop*.png?
briefs
"""


# ── фикстуры пост-отчётов (П1): формы сняты с ЖИВЫХ файлов корпуса ──────────
# Форматы не выдуманы: geo - вывод geo_check.py (`guide-ii-navyki`), 12a - вывод
# `ftp_publish --index-legs` (`guide-chto-takoe-neyroset`) плюс выписка реестра
# переобхода (`guide-claude-code`), 12b - наш пробник (весь корпус).
GEO_FIXTURE_PASS = """# Этап 13.4a - три проверки извлекаемости на боевом снимке

Слаг: {slug} · снимок: prod-snapshot.html (168052 б, GET с релея, HTTP 200)

## 1. FAQPage дословно равна видимому тексту - OK

```
FAQPage=1 пар=7 расхождений строгих=0 из них по существу=0 битых JSON-LD=0
```

## 2. Быстрый ответ ровно один - OK

```
блоков quick-answer: 1
```

## 3. citation[] из видимого блока «Источники» - {mark3}

```
citation в Article: 10 · видимых внешних источников: 10 · не отражено в citation: 0
```

**Вердикт 13.4a: {verdict}** (логическое И трёх осей)
"""
INDEX_LEGS_FIXTURE = (
    "очередь GSC: добавлено 1 новых, всего 33 в ~/.business/growth/seo/gsc-pending.json\n"
    "нога Яндекс: отправлено 2 / нога Google: в очереди 33, старейшая неотправленная 1 дней\n")
GET_FIXTURE = "HTTP=200 size=168052 time=0.759798s\n"


def _post_body(name, slug="pos"):
    """Тело фикстуры пост-артефакта под его собственную проверку содержимого.

    До П1 селфтест клал сюда байт «x» - и это была та же слепота, что чиним:
    фикстура изображала имя файла, а не отчёт. Теперь фикстура ЧЕСТНАЯ, то есть
    существующие позитивы (Б3 и др.) проверяют настоящий класс.
    """
    if name == GEO_REPORT:
        return GEO_FIXTURE_PASS.format(slug=slug, verdict="PASS", mark3="OK")
    if name == INDEX_LEGS:
        return INDEX_LEGS_FIXTURE
    if name == GET_PROBE:
        return GET_FIXTURE
    return None


def _touch(d, name):
    """Файл-фикстура. `index.html` кладём ПОЛНОВЕСНЫМ: страница засчитывается по
    размеру (фикс-6), а фикстура обязана изображать реальную страницу, а не
    нулевой байт - иначе селфтест проверял бы не тот класс. Пост-отчёты (П1) -
    по той же причине с настоящим содержимым, см. `_post_body`."""
    p = os.path.join(d, name)
    body = _post_body(name, os.path.basename(str(d).rstrip("/")))
    if body is None:
        body = ("<html><body>" + "страница " * 200 + "</body></html>"
                if name == PAGE_HTML else "x")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


def _gates(d, sign=True, **stages):
    """Фикстура машинного отчёта раннера: _gates(dir, page="PASS", draft="FAIL").

    sign=True (как в жизни с этой редакции) - стадия page подписывается sha256
    ЛЕЖАЩЕЙ РЯДОМ страницы, ровно так, как это делает article_gates.
    sign=False изображает расписку СТАРОГО формата (поля нет) - это отдельный
    полюс Б16, а не «нормальный» отчёт.
    """
    doc = {"slug": os.path.basename(d.rstrip("/")),
           "stages": {k: {"ran_at": "2026-08-12T00:00:00", "verdict": v}
                      for k, v in stages.items() if v}}
    if sign:
        sha = file_sha256(os.path.join(d, PAGE_HTML))
        for st in ("page", "publish"):
            if st in doc["stages"] and sha:
                doc["stages"][st]["page_sha256"] = sha
    p = os.path.join(d, GATES_JSON)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    return p


def selftest():
    exp = parse_expected(SELFTEST_EXPECTED)
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    # разбор
    check("разбор: MIN 3 строки", len(exp[SECTION_MIN]) == 3, str(len(exp[SECTION_MIN])))
    check("разбор: MIN-LEGACY 2 строки", len(exp[SECTION_MIN_LEGACY]) == 2,
          str(len(exp[SECTION_MIN_LEGACY])))
    check("разбор: MIN-REVISION 2 строки", len(exp[SECTION_MIN_REVISION]) == 2,
          str(len(exp[SECTION_MIN_REVISION])))
    check("разбор: @witness: снимается с raw и поднимает флаг witness",
          exp[SECTION_MIN_REVISION][1]["witness"] is True
          and exp[SECTION_MIN_REVISION][1]["raw"] == "changes.md|base_sha*|plan-*.json"
          and exp[SECTION_MIN_REVISION][0]["witness"] is False,
          str(exp[SECTION_MIN_REVISION]))
    check("разбор: POST 1 строка", len(exp[SECTION_POST]) == 1, str(len(exp[SECTION_POST])))
    check("разбор: FULL 3 строки", len(exp[SECTION_FULL]) == 3, str(len(exp[SECTION_FULL])))
    check("разбор: `?` = условный",
          exp[SECTION_FULL][1]["optional"] is True and exp[SECTION_FULL][0]["optional"] is False)
    check("разбор: `|` = альтернативы", exp[SECTION_MIN][0]["alts"] == ["draft.md", "spec.json"])
    check("разбор: MIN и FULL не пересекаются",
          not ({e["raw"] for e in exp[SECTION_MIN]} & {e["raw"] for e in exp[SECTION_FULL]}))
    check("уровни: --full схлопывает дубли MIN и MIN-LEGACY",
          len(entries_for(exp, "full", "new")) == 7, str(len(entries_for(exp, "full", "new"))))
    check("уровни: --post = MIN маршрута + POST",
          [e["raw"] for e in entries_for(exp, "post", "legacy")]
          == ["index.html", "draft.md|spec.json", "etap-12a-index-legs.md"],
          str([e["raw"] for e in entries_for(exp, "post", "legacy")]))

    root = tempfile.mkdtemp(prefix="artifacts_gate_selftest_")

    # ПОЗИТИВ: полный минимум на месте
    d1 = os.path.join(root, "pos")
    os.makedirs(d1)
    for n in ("draft.md", "research.md", "index.html"):
        _touch(d1, n)
    r1 = run(d1, exp, "min")
    check("позитив: MIN PASS", r1["verdict"] == "PASS", str(r1["missing"]))

    # ПОЗИТИВ: альтернатива закрывает строку (spec.json вместо draft.md)
    d2 = os.path.join(root, "alt")
    os.makedirs(d2)
    for n in ("spec.json", "research-external.md", "index.html"):
        _touch(d2, n)
    r2 = run(d2, exp, "min")
    check("позитив: альтернатива засчитана", r2["verdict"] == "PASS", str(r2["missing"]))

    # НЕГАТИВ: пустой каталог
    d3 = os.path.join(root, "empty")
    os.makedirs(d3)
    r3 = run(d3, exp, "min")
    check("негатив: пусто = FAIL", r3["verdict"] == "FAIL" and len(r3["missing"]) == 3,
          str(r3["missing"]))

    # НЕГАТИВ: не хватает ровно одного
    d4 = os.path.join(root, "part")
    os.makedirs(d4)
    for n in ("draft.md", "index.html"):
        _touch(d4, n)
    r4 = run(d4, exp, "min")
    check("негатив: один пропуск ловится",
          r4["verdict"] == "FAIL" and r4["missing"] == ["research.md|research-external.md|research-DOLG.md"],
          str(r4["missing"]))

    # ПОЗИТИВ: маска fnmatch + условный не роняет
    d5 = os.path.join(root, "full")
    os.makedirs(d5)
    for n in ("draft.md", "research.md", "index.html", "retro.md",
              "etap-12a-index-legs.md", "etap-11-desktop-183126.png"):
        _touch(d5, n)
    os.makedirs(os.path.join(d5, "briefs"))
    r5 = run(d5, exp, "full")
    check("позитив: FULL PASS (маска + каталог)", r5["verdict"] == "PASS", str(r5["missing"]))
    check("позитив: маска нашла файл со штампом",
          r5["matched"].get("etap-11-desktop*.png") == "etap-11-desktop-183126.png",
          str(r5["matched"]))

    # НЕГАТИВ: условный отсутствует - FULL всё равно PASS
    d6 = os.path.join(root, "cond")
    os.makedirs(d6)
    for n in ("draft.md", "research.md", "index.html", "retro.md",
              "etap-12a-index-legs.md"):
        _touch(d6, n)
    os.makedirs(os.path.join(d6, "briefs"))
    r6 = run(d6, exp, "full")
    check("негатив: условный пропуск не роняет",
          r6["verdict"] == "PASS" and r6["conditional_missing"] == ["etap-11-desktop*.png"],
          str(r6["conditional_missing"]))

    # НЕГАТИВ: FULL ловит то, что MIN пропускает - но вердиктом не роняет
    d7 = os.path.join(root, "mixed")
    os.makedirs(d7)
    for n in ("draft.md", "research.md", "index.html"):
        _touch(d7, n)
    check("негатив: FULL видит долг, которого MIN не видит",
          run(d7, exp, "min")["verdict"] == "PASS"
          and run(d7, exp, "full")["verdict"] == "DEBT"
          and run(d7, exp, "full")["missing"],
          str(run(d7, exp, "full")["verdict"]))

    # Б2 МАРШРУТ: тот же каталог легаси проходит, по новому маршруту падает
    d8 = os.path.join(root, "legacy")
    os.makedirs(d8)
    for n in ("index.html", "draft.md"):
        _touch(d8, n)
    check("Б2: легаси-каталог (страница + источник) = PASS",
          run(d8, exp, "min", "legacy")["verdict"] == "PASS",
          str(run(d8, exp, "min", "legacy")["missing"]))
    check("Б2: тот же каталог по новому маршруту = FAIL (нет ресёрча)",
          run(d8, exp, "min", "new")["verdict"] == "FAIL"
          and run(d8, exp, "min", "new")["missing"] == ["research.md|research-external.md|research-DOLG.md"],
          str(run(d8, exp, "min", "new")["missing"]))

    # Б3 ДЕДЛОК: post-publish артефакт не спрашивается до деплоя и спрашивается после
    d9 = os.path.join(root, "predeploy")
    os.makedirs(d9)
    for n in ("draft.md", "research.md", "index.html"):
        _touch(d9, n)
    _gates(d9, page="PASS")
    check("Б3: --min не требует etap-12a (иначе дедлок)",
          run(d9, exp, "min", "new")["verdict"] == "PASS",
          str(run(d9, exp, "min", "new")["missing"]))
    check("Б3: --post требует etap-12a",
          run(d9, exp, "post", "new")["verdict"] == "FAIL"
          and run(d9, exp, "post", "new")["missing"] == ["etap-12a-index-legs.md"],
          str(run(d9, exp, "post", "new")["missing"]))
    _touch(d9, "etap-12a-index-legs.md")
    check("Б3: с обеими ногами --post = PASS",
          run(d9, exp, "post", "new")["verdict"] == "PASS")

    # Б2 ПРИЗНАК МАРШРУТА: детерминированный, вне каталога статьи
    reg = os.path.join(root, "registry.json")
    with open(reg, "w", encoding="utf-8") as f:
        json.dump({"https://dom.test/guide-old/": {"datePublished": "2026-08-02"},
                   "https://dom.test/guide-new/": {"datePublished": "2026-08-12"},
                   "https://dom.test/guide-nodate/": {"lastmod": "2026-07-01"},
                   "https://dom.test/guide-frontir/": {"datePublished": "2026-08-02"}}, f)
    rc_cfg = {"domain": "https://dom.test", "page_prefix": "guide-",
              "redirected": ["claude-razban"]}
    check("маршрут: datePublished < порога = legacy",
          route_of("guide-old", rc_cfg, reg)[0] == "legacy", str(route_of("guide-old", rc_cfg, reg)))
    check("маршрут: datePublished >= порога = new",
          route_of("guide-new", rc_cfg, reg)[0] == "new", str(route_of("guide-new", rc_cfg, reg)))
    check("маршрут: в реестре без datePublished = legacy",
          route_of("guide-nodate", rc_cfg, reg)[0] == "legacy",
          str(route_of("guide-nodate", rc_cfg, reg)))
    check("маршрут: приставка page_prefix (каталог frontir → /guide-frontir/)",
          route_of("frontir", rc_cfg, reg)[0] == "legacy", str(route_of("frontir", rc_cfg, reg)))
    check("маршрут: список redirected = legacy",
          route_of("claude-razban", rc_cfg, reg)[0] == "legacy",
          str(route_of("claude-razban", rc_cfg, reg)))
    check("маршрут: нет в реестре = new (fail-closed, не legacy)",
          route_of("guide-net-takogo", rc_cfg, reg)[0] == "new",
          str(route_of("guide-net-takogo", rc_cfg, reg)))
    check("маршрут: нет реестра = new (fail-closed)",
          route_of("guide-old", rc_cfg, os.path.join(root, "нет-реестра.json"))[0] == "new")
    check("маршрут: битый реестр = new (fail-closed)",
          route_of("guide-old", rc_cfg, _touch(root, "битый.json"))[0] == "new")
    check("маршрут: улика печатается всегда",
          all(route_of(s, rc_cfg, reg)[1] for s in ("guide-old", "guide-new", "guide-net")))

    # ── Б6 МАРКЕР ПРИЗНАННОГО ДОЛГА `*-DOLG.md` ─────────────────────────────
    # право на расписку даёт та же улика вне каталога: дата выпуска в реестре
    check("долг: выпуск == порогу (пачка по решению автора) - маркер засчитывается",
          debt_markers_allowed("guide-new", rc_cfg, reg)[0] is True,
          str(debt_markers_allowed("guide-new", rc_cfg, reg)))
    check("долг: выпуск раньше порога (легаси) - маркер засчитывается",
          debt_markers_allowed("guide-old", rc_cfg, reg)[0] is True,
          str(debt_markers_allowed("guide-old", rc_cfg, reg)))
    check("долг: datePublished не проставлен - маркер засчитывается",
          debt_markers_allowed("guide-nodate", rc_cfg, reg)[0] is True)
    check("долг: redirected - маркер засчитывается",
          debt_markers_allowed("claude-razban", rc_cfg, reg)[0] is True)
    reg2 = os.path.join(root, "registry-later.json")
    with open(reg2, "w", encoding="utf-8") as f:
        json.dump({"https://dom.test/guide-zavtra/": {"datePublished": "2026-08-13"}}, f)
    check("долг: выпуск СТРОГО позже порога - маркер НЕ засчитывается (новая статья)",
          debt_markers_allowed("guide-zavtra", rc_cfg, reg2)[0] is False,
          str(debt_markers_allowed("guide-zavtra", rc_cfg, reg2)))
    check("долг: статьи нет в реестре - маркер НЕ засчитывается (fail-closed)",
          debt_markers_allowed("guide-net-takogo", rc_cfg, reg)[0] is False)
    check("долг: улика печатается всегда",
          all(debt_markers_allowed(s, rc_cfg, reg)[1]
              for s in ("guide-old", "guide-new", "guide-net-takogo")))

    # ── М14 ГРАНИЦА new_route_since: три случая (<, ==, >) названы вслух ───────
    reg_b = os.path.join(root, "registry-granica.json")
    with open(reg_b, "w", encoding="utf-8") as f:
        json.dump({"https://dom.test/guide-do/": {"datePublished": "2026-08-11"},
                   "https://dom.test/guide-rovno/": {"datePublished": "2026-08-12"},
                   "https://dom.test/guide-posle/": {"datePublished": "2026-08-13"}}, f)
    гр = {s: (route_of(s, rc_cfg, reg_b), debt_markers_allowed(s, rc_cfg, reg_b))
          for s in ("guide-do", "guide-rovno", "guide-posle")}
    check("М14 «<»: выпуск ДО порога = legacy + долг признан",
          гр["guide-do"][0][0] == "legacy" and гр["guide-do"][1][0] is True,
          str(гр["guide-do"]))
    check("М14 «==»: РОВНО порог = new-маршрут И долг признан (осознанная развязка пачки)",
          гр["guide-rovno"][0][0] == "new" and гр["guide-rovno"][1][0] is True,
          str(гр["guide-rovno"]))
    check("М14 «>»: выпуск ПОСЛЕ порога = new-маршрут, долг НЕ признан",
          гр["guide-posle"][0][0] == "new" and гр["guide-posle"][1][0] is False,
          str(гр["guide-posle"]))
    check("М14: обе улики границы == называют её словом «РОВНО», а не прячут в >=/<=",
          "РОВНО" in гр["guide-rovno"][0][1] and "РОВНО" in гр["guide-rovno"][1][1],
          str((гр["guide-rovno"][0][1], гр["guide-rovno"][1][1])))

    d10 = os.path.join(root, "dolg")
    os.makedirs(d10)
    for n in ("draft.md", "index.html", "research-DOLG.md"):
        _touch(d10, n)
    check("долг: research-DOLG.md закрывает строку ресёрча, когда долг признан",
          run(d10, exp, "min", "new", "", True)["verdict"] == "PASS",
          str(run(d10, exp, "min", "new", "", True)["missing"]))
    check("долг: тот же каталог без права на долг = FAIL (новая статья)",
          run(d10, exp, "min", "new", "", False)["verdict"] == "FAIL"
          and run(d10, exp, "min", "new", "", False)["missing"]
          == ["research.md|research-external.md|research-DOLG.md"],
          str(run(d10, exp, "min", "new", "", False)["missing"]))
    check("долг: настоящий research.md годится и без права на долг",
          (lambda: (_touch(d10, "research.md"),
                    run(d10, exp, "min", "new", "", False)["verdict"])[1])() == "PASS")
    отложить(os.path.join(d10, "research.md"))   # закон №0: не сносим, откладываем
    # маска не должна протаскивать маркер долга в обход запрета
    exp_mask = parse_expected("#@MIN\nresearch*.md\nindex.html\ndraft.md\n")
    check("долг: маска research*.md не протаскивает маркер, когда долг не признан",
          run(d10, exp_mask, "min", "new", "", False)["verdict"] == "FAIL"
          and run(d10, exp_mask, "min", "new", "", True)["verdict"] == "PASS",
          str(run(d10, exp_mask, "min", "new", "", False)["missing"]))

    # ── В8 gates.json ЗАСЧИТЫВАЕТСЯ ПО ВЕРДИКТАМ, А НЕ ПО ИМЕНИ ───────────────
    exp_g = parse_expected("#@MIN\ndraft.md\nindex.html\ngates.json\n")
    d11 = os.path.join(root, "verdicts")
    os.makedirs(d11)
    for n in ("draft.md", "index.html"):
        _touch(d11, n)
    _gates(d11, page="PASS")
    r_pass = run(d11, exp_g, "min", "new")
    check("вердикты: page=PASS засчитывает gates.json",
          r_pass["verdict"] == "PASS" and any("page=PASS" in n for n in r_pass["notes"]),
          str(r_pass["notes"]))
    _gates(d11, page="FAIL")
    r_fail = run(d11, exp_g, "min", "new")
    check("вердикты: page=FAIL НЕ засчитывает gates.json (печать причины)",
          r_fail["verdict"] == "FAIL" and r_fail["missing"] == ["gates.json"]
          and any("gates.json есть, но page=FAIL" in n for n in r_fail["notes"]),
          str(r_fail["notes"]))
    _gates(d11, page="PASS", draft="FAIL", publish="FAIL")
    r_info = run(d11, exp_g, "min", "new")
    check("вердикты: draft/publish информационные - красный draft не роняет",
          r_info["verdict"] == "PASS"
          and any("draft=FAIL" in n and "publish=FAIL" in n for n in r_info["notes"]),
          str(r_info["notes"]))
    _gates(d11, draft="PASS")
    r_nopage = run(d11, exp_g, "min", "new")
    check("вердикты: стадии page нет вовсе = НЕ засчитан (страница не проверена)",
          r_nopage["verdict"] == "FAIL" and r_nopage["missing"] == ["gates.json"],
          str(r_nopage["notes"]))
    with open(os.path.join(d11, GATES_JSON), "w", encoding="utf-8") as f:
        f.write("{битый")
    r_broken = run(d11, exp_g, "min", "new")
    check("вердикты: битый gates.json = НЕ засчитан",
          r_broken["verdict"] == "FAIL" and r_broken["missing"] == ["gates.json"],
          str(r_broken["notes"]))
    with open(os.path.join(d11, GATES_JSON), "w", encoding="utf-8") as f:
        json.dump({"slug": "x", "stages": {}}, f)
    check("вердикты: пустые stages = НЕ засчитан",
          run(d11, exp_g, "min", "new")["verdict"] == "FAIL")

    # ── Б16 ЗВЕНО ЦЕПИ: ВЕРДИКТ ЗАСЧИТЫВАЕТСЯ ТОЛЬКО НА СВОИХ БАЙТАХ ──────────
    # Полюс 1 (уже проверен выше): подписанный page=PASS на живой странице = PASS.
    # Полюс 2: страницу пересобрали после гейтов - расписка про ДРУГИЕ байты.
    d16 = os.path.join(root, "b16-bytes")
    os.makedirs(d16)
    for n in ("draft.md", PAGE_HTML):
        _touch(d16, n)
    _gates(d16, page="PASS")
    r16_ok = run(d16, exp_g, "min", "new")
    check("Б16 ПОЛЮС+: page=PASS, подписанный ЖИВЫМИ байтами, засчитан",
          r16_ok["verdict"] == "PASS"
          and any("на живых байтах" in n for n in r16_ok["notes"]),
          str(r16_ok["notes"]))
    with open(os.path.join(d16, PAGE_HTML), "a", encoding="utf-8") as f:
        f.write("<!-- мусор, вписанный после прогона гейтов -->")
    r16_bad = run(d16, exp_g, "min", "new")
    check("Б16 ПОЛЮС-: страницу пересобрали после гейтов = gates.json НЕ засчитан",
          r16_bad["verdict"] == "FAIL" and r16_bad["missing"] == [GATES_JSON]
          and any("гонялись на ДРУГИХ байтах" in n for n in r16_bad["notes"]),
          str(r16_bad["notes"]))
    check("Б16: отказ называет ОДНО лечение - перегон стадии page",
          any(GATES_BYTES_FIX in n for n in r16_bad["notes"]), str(r16_bad["notes"]))
    # перегон гейтов по новым байтам - дверь снова открыта (одна команда лечит)
    _gates(d16, page="PASS")
    check("Б16: перегон гейтов на новых байтах возвращает PASS",
          run(d16, exp_g, "min", "new")["verdict"] == "PASS")
    # расписка СТАРОГО формата (поля нет вовсе) - тот же отказ, и это правильно
    _gates(d16, sign=False, page="PASS")
    r16_old = run(d16, exp_g, "min", "new")
    check("Б16: gates.json старого формата (без page_sha256) = тот же отказ",
          r16_old["verdict"] == "FAIL" and r16_old["missing"] == [GATES_JSON]
          and any("page_sha256" in n and GATES_BYTES_FIX in n for n in r16_old["notes"]),
          str(r16_old["notes"]))
    # прямая проверка функции: без страницы рядом сверять не с чем = отказ
    d16b = os.path.join(root, "b16-nopage")
    os.makedirs(d16b)
    _touch(d16b, PAGE_HTML)
    _gates(d16b, page="PASS")
    отложить(os.path.join(d16b, PAGE_HTML))   # закон №0: не сносим, откладываем
    ok16, why16 = gates_json_state(os.path.join(d16b, GATES_JSON))
    check("Б16: страницы рядом нет - расписку сверять не с чем, отказ",
          ok16 is False and "не читается" in why16, why16)

    # ── Б10 ПРОФИЛЬ РЕВИЗИИ: раскладка песочницы патча, а не раскладка $WORK ──
    # позитив 1: каркас рефреша - свидетельство лежит В КАТАЛОГЕ (changes.md + base_sha)
    work_root = os.path.join(root, "WORKDIR")
    os.makedirs(work_root)
    reb = os.path.join(root, "_rebuild", "refresh-out")
    d12 = os.path.join(reb, "guide-legacy")
    os.makedirs(d12)
    for n in ("index.html", "changes.md", "base_sha"):
        _touch(d12, n)
    cfg_w = {"work_dir": work_root}
    p12, why12 = dir_profile(d12, cfg_w)
    check("Б10: каталог вне $WORK без источника сборки = профиль revision",
          p12 == "revision", f"{p12} / {why12}")
    r12 = run(d12, exp, "min", "revision")
    check("Б10 ПОЗИТИВ: каркас рефреша (index.html + changes.md) = PASS",
          r12["verdict"] == "PASS", str(r12["missing"]))
    check("Б10: тот же каталог по MIN-LEGACY = FAIL (это и был блокер)",
          run(d12, exp, "min", "legacy")["verdict"] == "FAIL"
          and run(d12, exp, "min", "legacy")["missing"] == ["draft.md|spec.json"],
          str(run(d12, exp, "min", "legacy")["missing"]))

    # позитив 2: пилот перелинковки - свидетельство пачки лежит В РОДИТЕЛЕ
    pilot = os.path.join(root, "_rebuild", "interlink-pilot")
    d13 = os.path.join(pilot, "guide-grok")
    os.makedirs(d13)
    _touch(d13, "index.html")
    план = os.path.join(pilot, "plan-r5-20260812.json")
    with open(план, "w", encoding="utf-8") as f:
        json.dump({"_meta": {"волна": "r5"},
                   "pages": {"/guide-grok/": {"вставок": 2}}}, f, ensure_ascii=False)
    r13 = run(d13, exp, "min", "revision")
    check("Б10 ПОЗИТИВ: план пачки в РОДИТЕЛЬСКОМ каталоге закрывает свидетельство",
          r13["verdict"] == "PASS"
          and any("родительском" in n for n in r13["notes"]),
          str((r13["missing"], r13["notes"])))

    # ── фикс-6: свидетельство из РОДИТЕЛЯ обязано говорить про ЭТОТ каталог ──
    # негатив: каталог-сосед лёг рядом с пачкой и присвоил себе чужой план
    d13b = os.path.join(pilot, "guide-chuzhoy")
    os.makedirs(d13b)
    _touch(d13b, "index.html")
    r13b = run(d13b, exp, "min", "revision")
    check("фикс-6 НЕГАТИВ: сосед пачки не засчитывает чужой план (его нет в pages)",
          r13b["verdict"] == "FAIL"
          and r13b["missing"] == ["changes.md|base_sha*|plan-*.json"],
          str((r13b["missing"], r13b["notes"])))
    check("фикс-6: причина отказа названа, а не молча пропущена",
          any("pages" in n and "guide-chuzhoy" in n for n in r13b["notes"]),
          str(r13b["notes"]))
    # ЛОЖНЫЙ ПОЗИТИВ, пойманный живьём: в записи страницы лежат готовые команды
    # деплоя с абсолютными путями, и подстрока чужого каталога в них делала бы
    # соседа «упомянутым». Считаем ТОЛЬКО адреса страниц
    d13f = os.path.join(pilot, "source-patches")
    os.makedirs(d13f)
    _touch(d13f, "index.html")
    with open(план, "w", encoding="utf-8") as f:
        json.dump({"pages": {"/guide-grok/": {
            "deploy": {"cmd": "ftp_publish.py --dir /…/interlink-pilot/source-patches"},
            "slug": "guide-grok"}}}, f, ensure_ascii=False)
    r13f = run(d13f, exp, "min", "revision")
    check("фикс-6 НЕГАТИВ: путь каталога внутри команды деплоя - НЕ упоминание страницы",
          r13f["verdict"] == "FAIL", str((r13f["missing"], r13f["notes"])))
    check("фикс-6: в отказе перечислены реальные страницы пачки",
          any("guide-grok" in n for n in r13f["notes"]), str(r13f["notes"]))
    check("фикс-6: page_identities берёт адреса из ключей и из поля slug",
          page_identities({"/guide-a/": {"slug": "guide-a"}}) == {"guide-a"}
          and page_identities(["/guide-b/", {"url": "https://x/guide-c.html"}])
          == {"guide-b", "guide-c"},
          str(page_identities(["/guide-b/", {"url": "https://x/guide-c.html"}])))
    check("фикс-6 ПОЗИТИВ: страница пачки по-прежнему засчитана тем же планом",
          run(d13, exp, "min", "revision")["verdict"] == "PASS")
    # позитив: свидетельство-НЕ-json (changes.md пачки) засчитывается по упоминанию
    пачка_md = os.path.join(root, "_rebuild", "md-pачка")
    d13c = os.path.join(пачка_md, "guide-tekstom")
    os.makedirs(d13c)
    _touch(d13c, "index.html")
    with open(os.path.join(пачка_md, "changes.md"), "w", encoding="utf-8") as f:
        f.write("# правки пачки\n- guide-tekstom: 3 вставки от базы abc123\n")
    r13c = run(d13c, exp, "min", "revision")
    check("фикс-6 ПОЗИТИВ: changes.md пачки засчитан - слаг в тексте упомянут",
          r13c["verdict"] == "PASS" and any("упоминает guide-tekstom" in n
                                            for n in r13c["notes"]),
          str((r13c["missing"], r13c["notes"])))
    d13d = os.path.join(пачка_md, "guide-nenazvannyy")
    os.makedirs(d13d)
    _touch(d13d, "index.html")
    check("фикс-6 НЕГАТИВ: тот же changes.md соседу без упоминания НЕ засчитан",
          run(d13d, exp, "min", "revision")["verdict"] == "FAIL",
          str(run(d13d, exp, "min", "revision")["notes"]))
    # свидетельство В САМОМ каталоге проверку на упоминание не проходит и не должно
    check("фикс-6: свидетельство В КАТАЛОГЕ засчитывается как раньше (d12)",
          run(d12, exp, "min", "revision")["verdict"] == "PASS")

    # ── фикс-6: страница засчитывается по РАЗМЕРУ, а не по факту существования ──
    d13e = os.path.join(root, "_rebuild", "pustaya", "guide-pustaya-stranica")
    os.makedirs(d13e)
    open(os.path.join(d13e, "index.html"), "w", encoding="utf-8").close()
    with open(os.path.join(d13e, "changes.md"), "w", encoding="utf-8") as f:
        f.write("guide-pustaya-stranica: патч\n")
    r13e = run(d13e, exp, "min", "revision")
    check("фикс-6 НЕГАТИВ: пустой index.html (0 б) не закрывает строку страницы",
          r13e["verdict"] == "FAIL" and r13e["missing"] == ["index.html"],
          str((r13e["missing"], r13e["notes"])))
    check("фикс-6: причина пустой страницы названа размером",
          any("пустой/обрезанный" in n for n in r13e["notes"]), str(r13e["notes"]))
    with open(os.path.join(d13e, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html>" + "тело " * 500 + "</html>")
    check("фикс-6 ПОЗИТИВ: та же песочница с полновесной страницей = PASS",
          run(d13e, exp, "min", "revision")["verdict"] == "PASS")

    # негатив 1: голый каталог с одним index.html - гейт обязан краснеть
    d14 = os.path.join(root, "_rebuild", "goliy", "guide-nagoy")
    os.makedirs(d14)
    _touch(d14, "index.html")
    r14 = run(d14, exp, "min", "revision")
    check("Б10 НЕГАТИВ: голый index.html без свидетельства = FAIL (иначе гейт декоративен)",
          r14["verdict"] == "FAIL"
          and r14["missing"] == ["changes.md|base_sha*|plan-*.json"],
          str(r14["missing"]))

    # негатив 2: свидетельство есть, а страницы нет - заливать нечего
    d15 = os.path.join(root, "_rebuild", "bezstranicy", "guide-nopage")
    os.makedirs(d15)
    _touch(d15, "changes.md")
    check("Б10 НЕГАТИВ: свидетельство без index.html = FAIL (заливать нечего)",
          run(d15, exp, "min", "revision")["verdict"] == "FAIL"
          and run(d15, exp, "min", "revision")["missing"] == ["index.html"],
          str(run(d15, exp, "min", "revision")["missing"]))

    # признак профиля: МЕСТО каталога сильнее содержимого - полупустой каталог
    # СТАТЬИ внутри $WORK не смеет притвориться песочницей
    d16 = os.path.join(work_root, "guide-pustoy")
    os.makedirs(d16)
    _touch(d16, "index.html")
    p16, why16 = dir_profile(d16, cfg_w)
    check("Б10: каталог ВНУТРИ $WORK всегда article, даже без draft/spec",
          p16 == "article", f"{p16} / {why16}")
    d17 = os.path.join(root, "_rebuild", "sborka-vne-work")
    os.makedirs(d17)
    for n in ("index.html", "spec.json"):
        _touch(d17, n)
    p17, why17 = dir_profile(d17, cfg_w)
    check("Б10: вне $WORK, но со spec.json = article (сборка просто не в $WORK)",
          p17 == "article", f"{p17} / {why17}")
    check("Б10: улика профиля печатается всегда",
          all(dir_profile(d, cfg_w)[1] for d in (d12, d13, d16, d17)))
    check("Б10: MIN-REVISION НЕ входит в --full (долг статьи не про песочницу)",
          len(entries_for(exp, "full", "revision")) == 7
          and "changes.md|base_sha*|plan-*.json"
          not in [e["raw"] for e in entries_for(exp, "full", "revision")],
          str([e["raw"] for e in entries_for(exp, "full", "revision")]))

    # ── П1 (по решению автора): ТРИ ПОСТ-АРТЕФАКТА ЧИТАЮТСЯ ВНУТРИ ──────────────────
    # 🔴 КОНТРОЛЬ НА СЛЕПОТУ. Четыре полюса на каждый артефакт: (а) честный PASS
    # проходит · (б) красный вердикт внутри валится · (в) подмена содержимого на
    # заглушку валится · (г) отсутствие файла валится как раньше. Без полюса (а)
    # тест доказывал бы только «гейт умеет краснеть», без (в) - открывал бы дверь
    # `touch etap-13-geo.md`, ровно ту, что чиним.
    exp_p = parse_expected("#@MIN\nindex.html\n#@POST\netap-13-geo.md\n"
                           "etap-12a-index-legs.md\netap-12b-get.txt\n")

    def _post_dir(имя, **файлы):
        d = os.path.join(root, "post-" + имя)
        os.makedirs(d, exist_ok=True)
        _touch(d, PAGE_HTML)
        for n in (GEO_REPORT, INDEX_LEGS, GET_PROBE):
            тело = файлы.get(n, _post_body(n, имя))
            if тело is None:
                continue
            with open(os.path.join(d, n), "w", encoding="utf-8") as f:
                f.write(тело)
        return run(d, exp_p, "post", "new")

    # (а) ПОЗИТИВ: честный PASS внутри всех трёх отчётов
    r_pa = _post_dir("chestno")
    check("П1 (а) ПОЗИТИВ: честный PASS внутри трёх пост-отчётов = PASS",
          r_pa["verdict"] == "PASS", str(r_pa["missing"]) + str(r_pa["notes"]))
    check("П1 (а): улика содержимого печатается и на зелёном (вердикт видно)",
          any("Вердикт 13.4a PASS" in n for n in r_pa["notes"])
          and any("HTTP=200" in n for n in r_pa["notes"])
          and any("следы отправки" in n for n in r_pa["notes"]), str(r_pa["notes"]))

    # (б) НЕГАТИВ: FAIL внутри geo - ровно живой случай guide-ii-prilozhenie
    r_pb = _post_dir("geofail", **{GEO_REPORT: GEO_FIXTURE_PASS.format(
        slug="geofail", verdict="FAIL", mark3="FAIL")})
    check("П1 (б) НЕГАТИВ: «Вердикт 13.4a: FAIL» внутри geo роняет стадию",
          r_pb["verdict"] == "FAIL" and r_pb["missing"] == [GEO_REPORT],
          str(r_pb["missing"]))
    check("П1 (б): причина названа осью, а не общими словами",
          any("Вердикт 13.4a: FAIL" in n and "ось 3" in n for n in r_pb["notes"]),
          str(r_pb["notes"]))
    # тот же файл, но подпись перекрашена в PASS при красной оси: расписка спорит
    # сама с собой, и верить надо осям (вердикт по канону = логическое И трёх)
    r_pb2 = _post_dir("geolie", **{GEO_REPORT: GEO_FIXTURE_PASS.format(
        slug="geolie", verdict="PASS", mark3="FAIL")})
    check("П1 (б) НЕГАТИВ: подпись PASS при красной оси НЕ засчитана",
          r_pb2["verdict"] == "FAIL" and r_pb2["missing"] == [GEO_REPORT],
          str(r_pb2["notes"]))
    # вторая живая форма подписи (рукописные отчёты r9) обязана читаться тоже
    r_pb3 = _post_dir("geor9", **{GEO_REPORT: GEO_FIXTURE_PASS.format(
        slug="geor9", verdict="PASS", mark3="OK").replace(
        "**Вердикт 13.4a: PASS** (логическое И трёх осей)",
        "## Вердикт подэтапа (логическое И): PASS")})
    check("П1: форма подписи r9 («Вердикт подэтапа») читается как PASS",
          r_pb3["verdict"] == "PASS", str(r_pb3["notes"]))
    r_pb4 = _post_dir("geor9f", **{GEO_REPORT: GEO_FIXTURE_PASS.format(
        slug="geor9f", verdict="FAIL", mark3="FAIL").replace(
        "**Вердикт 13.4a: FAIL** (логическое И трёх осей)",
        "## Вердикт подэтапа (логическое И): FAIL")})
    check("П1: форма подписи r9 с FAIL роняет так же",
          r_pb4["verdict"] == "FAIL" and r_pb4["missing"] == [GEO_REPORT],
          str(r_pb4["notes"]))

    # (в) НЕГАТИВ: подмена содержимого на заглушку по каждому из трёх
    r_pv1 = _post_dir("geostub", **{GEO_REPORT: "x"})
    check("П1 (в) НЕГАТИВ: geo подменён заглушкой (нет вердикта) = FAIL",
          r_pv1["verdict"] == "FAIL" and r_pv1["missing"] == [GEO_REPORT],
          str(r_pv1["notes"]))
    r_pv1b = _post_dir("geoodna", **{GEO_REPORT: "# Этап 13.4a\n\n**Вердикт 13.4a: PASS**\n"})
    check("П1 (в) НЕГАТИВ: одна зелёная строка без трёх осей НЕ засчитана",
          r_pv1b["verdict"] == "FAIL" and r_pv1b["missing"] == [GEO_REPORT],
          str(r_pv1b["notes"]))
    r_pv2 = _post_dir("legstub", **{INDEX_LEGS: "# Этап 12a - обе ноги уведомления\n"
                                                "\nНога 1: TODO\nНога 2: TODO\n"})
    check("П1 (в) НЕГАТИВ: 12a - незаполненный шаблон (TODO) = FAIL",
          r_pv2["verdict"] == "FAIL" and r_pv2["missing"] == [INDEX_LEGS],
          str(r_pv2["notes"]))
    r_pv2b = _post_dir("legempty", **{INDEX_LEGS: "# Этап 12a - обе ноги уведомления\n"})
    check("П1 (в) НЕГАТИВ: 12a - одна шапка без тела = FAIL",
          r_pv2b["verdict"] == "FAIL" and r_pv2b["missing"] == [INDEX_LEGS],
          str(r_pv2b["notes"]))
    r_pv2c = _post_dir("legproza", **{INDEX_LEGS: "Обе ноги уведомления поисковиков "
                                                  "закрыты, всё хорошо, публикуем "
                                                  "статью дальше по конвейеру.\n"})
    check("П1 (в) НЕГАТИВ: 12a - проза «всё закрыто» без следов отправки = FAIL",
          r_pv2c["verdict"] == "FAIL" and r_pv2c["missing"] == [INDEX_LEGS],
          str(r_pv2c["notes"]))
    r_pv2d = _post_dir("legzero", **{INDEX_LEGS: INDEX_LEGS_FIXTURE.replace(
        "нога Яндекс: отправлено 2", "нога Яндекс: отправлено 0")})
    check("П1 (в) НЕГАТИВ: 12a - «нога Яндекс: отправлено 0» = FAIL",
          r_pv2d["verdict"] == "FAIL" and r_pv2d["missing"] == [INDEX_LEGS],
          str(r_pv2d["notes"]))
    # 🔴 КОНТРОЛЬ НА ЛОЖНУЮ КРАСНОТУ (поймано на корпусе по решению автора). Внутри 12a лежит
    # улика из живой карты сайта - строка `<url><loc>…</loc><lastmod>…`. Это
    # XML-тег sitemap, а не незаполненный плейсхолдер `<URL>`: восемь здоровых
    # отчётов краснели на нём, пока маркеры шли через re.I
    check("П1 ЛОЖНЯК: `<url><loc>` из карты сайта - улика, а не заглушка",
          _post_dir("legsitemap", **{INDEX_LEGS: INDEX_LEGS_FIXTURE + "\n"
                                     "<url><loc>https://dom.test/guide-x/</loc>"
                                     "<lastmod>2026-08-21</lastmod></url>\n"}
                    )["verdict"] == "PASS")
    check("П1: но КАПСОВЫЙ `<URL>` из шаблона по-прежнему ловится",
          _post_dir("legcaps", **{INDEX_LEGS: INDEX_LEGS_FIXTURE
                                  + "\nURL: <URL>\n"})["verdict"] == "FAIL")
    check("П1 ПОЗИТИВ: 12a - выписка реестра переобхода (task_id/sent_at) годится",
          _post_dir("legtask", **{INDEX_LEGS: '# Этап 12a\n\n{"task_id": '
                                              '"9c61f260-9c1f-11f1-9934-210dd5398de0", '
                                              '"sent_at": "2026-08-20T01:45:00+03:00", '
                                              '"state": "DONE"}\n'})["verdict"] == "PASS")
    check("П1 ПОЗИТИВ: 12a - сводка эстафеты (indexlegs rc=0) годится",
          _post_dir("legrc", **{INDEX_LEGS: "# Обе ноги индексации\n\n- Нога Яндекс "
                                            "(IndexNow): отправлена внутри эстафеты, "
                                            "`--- indexlegs rc=0`\n- Нога Google: URL "
                                            "в очереди переобхода\n"})["verdict"] == "PASS")
    for код in ("404", "500", "000", "503"):
        r_pv3 = _post_dir("get" + код, **{GET_PROBE: f"HTTP={код} size=0 time=0.1s\n"})
        check(f"П1 (в) НЕГАТИВ: 12b - код {код} вместо 200 = FAIL",
              r_pv3["verdict"] == "FAIL" and r_pv3["missing"] == [GET_PROBE],
              str(r_pv3["notes"]))
    r_pv3b = _post_dir("getnone", **{GET_PROBE: "приёмка проведена, всё в порядке\n"})
    check("П1 (в) НЕГАТИВ: 12b - кода ответа в файле нет вовсе = FAIL",
          r_pv3b["verdict"] == "FAIL" and r_pv3b["missing"] == [GET_PROBE],
          str(r_pv3b["notes"]))
    r_pv3c = _post_dir("getpusto", **{GET_PROBE: "HTTP=200 size=12 time=0.1s\n"})
    check("П1 (в) НЕГАТИВ: 12b - 200 на теле в 12 б (пустышка по адресу) = FAIL",
          r_pv3c["verdict"] == "FAIL" and r_pv3c["missing"] == [GET_PROBE],
          str(r_pv3c["notes"]))
    check("П1 ПОЗИТИВ: 12b - сырой curl (`HTTP/1.1 200 OK`) читается как 200",
          _post_dir("getraw", **{GET_PROBE: "HTTP/1.1 200 OK\ncontent-length: 168052\n"}
                    )["verdict"] == "PASS")

    # (г) РЕГРЕСС: отсутствие файла валится как раньше, все три поимённо
    d_pg = os.path.join(root, "post-net-faylov")
    os.makedirs(d_pg)
    _touch(d_pg, PAGE_HTML)
    r_pg = run(d_pg, exp_p, "post", "new")
    check("П1 (г) РЕГРЕСС: нет ни одного пост-файла = FAIL, все три названы",
          r_pg["verdict"] == "FAIL"
          and sorted(r_pg["missing"]) == sorted([GEO_REPORT, INDEX_LEGS, GET_PROBE]),
          str(r_pg["missing"]))
    check("П1 (г) РЕГРЕСС: --min пост-файлов не спрашивает (дедлок Б3 не вернулся)",
          run(d_pg, exp_p, "min", "new")["verdict"] == "PASS",
          str(run(d_pg, exp_p, "min", "new")["missing"]))

    # замок от рецидива: каждый пост-артефакт боевого эталона обязан иметь
    # проверку содержимого. Заведут четвёртый и забудут - селфтест покраснеет
    check("П1: таблица CONTENT_CHECKS покрывает все три пост-артефакта",
          all(n in CONTENT_CHECKS for n in (GEO_REPORT, INDEX_LEGS, GET_PROBE)),
          str(sorted(CONTENT_CHECKS)))

    # НЕГАТИВ: боевой эталон не пуст и секции разведены
    live = None
    for p in (cfg_path(load_cfg(), "expected_artifacts", FALLBACK_EXPECTED),):
        if os.path.isfile(p):
            live = load_expected(p)
    if live is not None:
        check("боевой эталон: MIN не пуст", len(live[SECTION_MIN]) >= 3, str(len(live[SECTION_MIN])))
        check("боевой эталон: MIN-LEGACY не пуст", len(live[SECTION_MIN_LEGACY]) >= 2,
              str(len(live[SECTION_MIN_LEGACY])))
        check("боевой эталон: POST не пуст", len(live[SECTION_POST]) >= 1,
              str(len(live[SECTION_POST])))
        # 🔴 П1, ЗАМОК ОТ РЕЦИДИВА НА БОЕВОМ ЭТАЛОНЕ. Каждая строка секции POST
        # обязана иметь проверку СОДЕРЖИМОГО: пока её нет, файл закрывает пункт
        # именем - ровно дыра приёмки по решению автора. Заведут четвёртый пост-артефакт и
        # забудут дописать чекер - селфтест покраснеет здесь и назовёт строку.
        post_raw = [a for e in live[SECTION_POST] for a in e["alts"]]
        без_чекера = [a for a in post_raw if a not in CONTENT_CHECKS]
        check("боевой эталон: у КАЖДОГО пост-артефакта есть проверка содержимого",
              not без_чекера, "без чекера: " + ", ".join(без_чекера))
        check("боевой эталон: FULL не пуст", len(live[SECTION_FULL]) >= 10,
              str(len(live[SECTION_FULL])))
        check("боевой эталон: MIN и FULL не пересекаются",
              not ({e["raw"] for e in live[SECTION_MIN]} & {e["raw"] for e in live[SECTION_FULL]}))
        # Б3, замок от рецидива: post-publish артефакт обратно в pre-deploy MIN
        # не заезжает ни правкой эталона, ни мержем
        min_raw = {e["raw"] for e in live[SECTION_MIN]} | {e["raw"] for e in live[SECTION_MIN_LEGACY]}
        check("боевой эталон: etap-12a НЕ в pre-deploy MIN (дедлок Б3)",
              not any("etap-12a" in r for r in min_raw), str(sorted(min_raw)))
        check("боевой эталон: etap-12a живёт в POST",
              any("etap-12a" in e["raw"] for e in live[SECTION_POST]),
              str([e["raw"] for e in live[SECTION_POST]]))
        # Б6: альтернатива-расписка живёт в боевом эталоне и ровно в строке ресёрча
        res_rows = [e["raw"] for e in live[SECTION_MIN] if "research" in e["raw"]]
        check("боевой эталон: строка ресёрча знает research-DOLG.md",
              len(res_rows) == 1 and "research-DOLG.md" in res_rows[0], str(res_rows))
        check("боевой эталон: маркер долга больше нигде не альтернатива",
              sum(1 for sec in SECTIONS for e in live[sec]
                  if any(is_debt_marker(a) for a in e["alts"])) == 1)
        # Б10: секция ревизии существует, спрашивает страницу И свидетельство,
        # и НЕ спрашивает источник сборки - иначе блокер возвращается
        rev_raw = [e["raw"] for e in live[SECTION_MIN_REVISION]]
        check("боевой эталон: MIN-REVISION не пуст", len(rev_raw) >= 2, str(rev_raw))
        check("боевой эталон: MIN-REVISION спрашивает index.html",
              "index.html" in rev_raw, str(rev_raw))
        check("боевой эталон: MIN-REVISION несёт строку-свидетельство @witness:",
              any(e.get("witness") for e in live[SECTION_MIN_REVISION]), str(rev_raw))
        check("боевой эталон: MIN-REVISION НЕ спрашивает draft.md|spec.json (Б10, замок от рецидива)",
              not any("draft.md" in r or "spec.json" in r or "research" in r for r in rev_raw),
              str(rev_raw))
        check("боевой эталон: свидетельство знает имена живых раскладок по решению автора",
              all(any(pat in r for r in rev_raw)
                  for pat in ("changes.md", "base_sha", "plan-")), str(rev_raw))
        check("боевой эталон: MIN-LEGACY - подмножество MIN + index.html",
              {e["raw"] for e in live[SECTION_MIN_LEGACY]}
              <= ({e["raw"] for e in live[SECTION_MIN]}),
              str([e["raw"] for e in live[SECTION_MIN_LEGACY]]))
    else:
        check("боевой эталон найден", False, "файл эталона не найден")

    ok = 0
    for name, good, detail in results:
        print(f"  {'OK  ' if good else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not good else ""))
        ok += 1 if good else 0
    print(f"selftest artifacts_gate: {ok}/{len(results)} прошло")
    return 0 if ok == len(results) else 1


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="artifacts_gate.py",
        description="Гейт артефактов статьи: MIN (замок публикации) и FULL (замер долга)")
    ap.add_argument("slug", nargs="?", help="slug статьи или путь к каталогу статьи")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--min", dest="level", action="store_const", const="min",
                   help="минимум перед деплоем по маршруту статьи (по умолчанию)")
    g.add_argument("--post", dest="level", action="store_const", const="post",
                   help="минимум + следы, появляющиеся после публикации")
    g.add_argument("--full", dest="level", action="store_const", const="full",
                   help="полный 16-этапный след (замер долга, exit 0 всегда)")
    ap.add_argument("--route", choices=ROUTES, default=None,
                    help="маршрут статьи вручную (иначе по реестру публикаций)")
    ap.add_argument("--work", default=None, help="каталог прогонов (иначе $WORK/конфиг/канон)")
    ap.add_argument("--expected", default=None, help="файл эталона (иначе конфиг/канон)")
    ap.add_argument("--registry", default=None,
                    help="реестр публикаций для определения маршрута (иначе конфиг/канон)")
    ap.add_argument("--config", default=None, help="путь к seo-publish.json")
    ap.add_argument("--json", dest="json_out", default=None, help="куда сложить машинный отчёт")
    ap.add_argument("--quiet", action="store_true", help="печатать только провал")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.slug:
        ap.error("нужен <slug> или путь к каталогу статьи")

    cfg = load_cfg(a.config)
    exp_path = os.path.expanduser(a.expected) if a.expected \
        else cfg_path(cfg, "expected_artifacts", FALLBACK_EXPECTED)
    if not os.path.isfile(exp_path):
        print(f"artifacts_gate: нет файла эталона: {exp_path}", file=sys.stderr)
        return 2
    expected = load_expected(exp_path)
    if not expected[SECTION_MIN]:
        print(f"artifacts_gate: в эталоне пуст обязательный минимум: {exp_path}", file=sys.stderr)
        return 2

    cand = os.path.expanduser(a.slug)
    article_dir = cand if os.path.isdir(cand) else os.path.join(work_dir(cfg, a.work), a.slug)
    if not os.path.isdir(article_dir):
        print(f"artifacts_gate: нет каталога статьи: {article_dir}", file=sys.stderr)
        return 2
    slug = os.path.basename(article_dir.rstrip("/"))

    level = a.level or "min"
    profile, profile_why = dir_profile(article_dir, cfg, a.work)
    if a.route:
        route, why = a.route, "задан явно флагом --route"
    elif profile == "revision":
        # Б10: у песочницы патча раскладка НЕ $WORK-овская, реестр публикаций
        # здесь не при чём - спрашиваем страницу и свидетельство ревизии
        route, why = "revision", profile_why
    else:
        route, why = route_of(slug, cfg, a.registry)
    debt_ok, debt_why = debt_markers_allowed(slug, cfg, a.registry)
    if a.route == "legacy" and not debt_ok:
        debt_ok, debt_why = True, "задан --route legacy вручную - маркер долга признаётся"
    if level != "min" and not expected[SECTION_POST] and level == "post":
        print(f"artifacts_gate: в эталоне пуста секция POST: {exp_path}", file=sys.stderr)
        return 2
    if route == "revision" and not expected[SECTION_MIN_REVISION]:
        # fail-closed: профиль ревизии определён, а спрашивать по эталону нечего -
        # молча пропустить нельзя, это открытая дверь
        print(f"artifacts_gate: профиль ревизии, но в эталоне пуста секция "
              f"{SECTION_MIN_REVISION}: {exp_path}", file=sys.stderr)
        return 2

    res = run(article_dir, expected, level, route, why, debt_ok, debt_why,
              profile, profile_why)
    res["expected_file"] = exp_path
    report(res, quiet=a.quiet)
    if a.json_out:
        with open(os.path.expanduser(a.json_out), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    if level == "full":
        return 0  # замер долга не роняет никогда
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
