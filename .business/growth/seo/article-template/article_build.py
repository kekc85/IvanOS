#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article_build.py - ЕДИНСТВЕННЫЙ шов draft.md -> spec.json.

    python3 article_build.py draft.md -o spec.json
    python3 article_build.py draft.md --force      # перезаписать spec.json рядом
    python3 article_build.py --selftest

Без -o спека пишется рядом с черновиком и ТОЛЬКО если её там ещё нет: боевая
spec.json - источник истины статьи пачки, молча затирать её сборкой нельзя
(гейт после такой перезаписи сверял бы файл сам с собой). Нужна перезапись -
скажи --force вслух.

Дальше спеку берёт build_page.py (он же владелец обвязки: нумерация, TOC,
JSON-LD, CSS). Между черновиком и страницей больше нет одноразовых скриптов:
до этой редакции их было 23 штуки на 7855 строк (make_spec.py / build_spec.py /
build_content.py в каждой папке статьи), и каждый нёс свою копию экранирования,
своё оформление таблиц и свой набор дефектов. Класс закрыт: текст живёт в одном
месте (draft.md), правка едет в один файл, фикс приезжает сразу во все статьи.

──────────────────────────────────────────────────────────────────────────────
КОНТРАКТ draft.md
──────────────────────────────────────────────────────────────────────────────
1. FRONT-MATTER - YAML между строками «---» в самом верху файла.
   ПЕРВАЯ обязательная строка - маркер контракта:

       engine: article_build

   Он не украшение: в рабочем каталоге лежат 24 ЛЕГАСИ-черновика со СВОИМ
   front-matter (meta_title / hero_image / cta_url / status), собранные
   одноразовыми конвертерами. Без маркера конвейер принимал бы их за свои и
   молча собирал спеку по чужой схеме. Легаси-черновики - архив (их источник
   истины = spec.json), маркер им не приписываем.

   Обязательное: engine, slug, title, description, h1, date_published.
   Необязательное: kind (guide), assets_base, keywords, eyebrow, og_image,
   og_image_alt, date_modified (по умолчанию сегодня), canonical_path,
   breadcrumbs, hero, toc_labels, faq_title, related_title, sources_intro,
   articleSection, author, utm_source, utm_content, codeword, figures,
   steps, extra_css_file, share.

2. MARKDOWN несёт то, что умеет: «# H1», разделы «## Заголовок {#anchor}»,
   абзацы, списки «- »/«1. », таблицы «| a | b |», заборы ``` (в <pre><code>,
   ЭКРАНИРОВАНИЕ ОДНОЙ РЕАЛИЗАЦИЕЙ - функция listing() ниже), ссылки
   [текст](url), **жирный**, `код`. Блок, чья первая строка начинается с «<»,
   уезжает в тело как готовый HTML без переработки.

   ЦИТАТА - подряд идущие строки «> текст». Последняя строка может быть
   подписью, и тогда она начинается с дефиса:

       > «Claude treats them as context, not enforced configuration»
       > - Anthropic, документация Claude Code, [раздел Memory](https://…)

   Собирается в <blockquote> с <p> на каждый абзац и <cite> на подпись - ровно
   та разметка, которую ждёт tokens.css разд. 12b. Пустая строка «>» внутри
   цитаты делит её на абзацы; markdown внутри (ссылки, **жирный**, `код`)
   работает как везде. Цитата без слов (одни «>») и цитата из одной подписи
   без текста - отказ сборки с именем черновика и номером строки, а не тихий
   абзац со стрелкой в теле страницы (класс закрыт по решению автора: до этого «>»
   был обычным символом абзаца и уезжал в готовую страницу буквой).

   Готовый <blockquote> руками в черновике (так написаны цитаты трёх статей
   волны) идёт как был: у блока первая строка с «<», значит для сборщика это
   готовый HTML, и второй раз он не заворачивается.

   «>» ВНУТРИ листинга - содержимое, а не цитата: строки :::pre, забора ``` и
   вывод терминала (diff, grep) этот разбор не видит - они уходят в listing()
   целиком и экранируются.

3. БЛОЧНЫЕ ДИРЕКТИВЫ - для того, чего markdown не несёт. Формат один:

       :::имя ключ=значение ключ2="значение с пробелами"
       тело
       :::

   Параметры машинные (идентификаторы, числа, флаги) - в открывающей строке.
   Человеческий текст - в теле: либо строки «поле: значение» в НАЧАЛЕ тела,
   либо markdown-содержимое. Директивы:

   :::figure slug=NAME w=1600 h=2342 [own=measure] [ext=jpg|png] [class=fig]
     alt: ...            <- обязателен, 50-125 знаков (гейт alt-вилки)
     caption: ...
   :::

   :::table [hint="Таблица прокручивается вбок →"] [fit=narrow]
     | Шапка | Шапка |
     |---|---|
     | ячейка | ячейка |
   :::                   (голая markdown-таблица в теле даёт то же самое)
                         fit= - узкая таблица без бокового скролла: садится
                         по ширине обёртки, на 390px видны ВСЕ колонки.
                         Ставится вместе с hint="" (скроллить нечего).

   :::pre [own=measure]
     $ wc -l landing.html
     67
   :::                   (то же, что забор ```; own= ставит data-own)

   🔴 ДВЕ РАВНОПРАВНЫЕ ФОРМЫ own-БЛОКА (r15, по решению автора). Пометка собственного
   замера живёт не только в директиве. Блок сырого HTML (п.2: строка на «<»
   уезжает в тело как есть) несёт ту же пометку атрибутом, и это ЛЕГАЛЬНАЯ,
   массово используемая форма:

       <div class="vizblock vizsteps"   data-own="measure"> … </div>
       <div class="vizblock vizcompare" data-own="measure"> … </div>
       <p data-own="measure">По собственному прогону по решению автора …</p>

   Обе формы проверяет ОДИН гейт own-evidence (own-evidence-check.py) и считает
   одна ось own-blocks (structure-check.py). До правки r15 оба знали только
   директиву и печатали по сырой форме «блоков нет, N/A, PASS» - ложный зелёный
   на 9 блоках в 4 статьях. Атрибут `data-own` - контракт, класс `vizblock` -
   оформление: гейт смотрит на атрибут, не на класс.

   :::checklist
     title: Памятка: деньги на сайтах
     intro: Семь строк пути
     - пункт
   :::

   :::faq
     ### Вопрос?
     Ответ абзацем
   :::                   (то же делает раздел «## Частые вопросы» с h3 внутри)

   :::sources [intro="..."]
     - строка источника
   :::                   (то же делает раздел «## Источники»)

   :::related
     href: /guide-sayt.html
     thumb: assets/thumb-guide-sayt.webp
     alt: ...
     title: ...
     desc: ...
                          <- пустая строка разделяет карточки
     href: ...
   :::

   :::cta place=compact|mid|final [anchor="Текст заголовка раздела"]
     eyebrow: Следующий шаг
     heading: Заголовок промо
     button: Текст кнопки
     Абзац промо
   :::
   place=final: закрывает статью призывом на оффер. Автодописи блока код-слова
   БОЛЬШЕ НЕТ (правка владельца, см. блок КОД-СЛОВО ниже).
   place=mid + anchor=: врезка встаёт СРАЗУ ПОСЛЕ названного раздела, а не в
   конце тела. Якорем служит текст «## Заголовок» либо его «{#идентификатор}» -
   что удобнее. Без anchor= место прежнее: штатный слот шаблона после всего
   тела. Опечатка в якоре роняет сборку со списком разделов статьи, тихого
   переезда врезки в конец страницы не бывает.

   КОД-СЛОВО: в ТЕКСТЕ СТАТЬИ ЕГО НЕТ ВООБЩЕ (решение владельца).
   Основной трафик статьи - Яндекс и Google: человек из поиска ни про какую
   карусель и ни про какое слово не знает, и абзац «код-слово этой статьи -
   СВОД» читает как обрывок чужой переписки в самой конверсионной точке
   страницы. Функционально блок был пустой: вход открывает КНОПКА, слово никуда
   не вводится. Связка карусель→статья продолжает жить в реестрах
   (CAROUSEL-REGISTRY.md, codewords.py) и в front-matter «codeword:» - это
   метаданные атрибуции, они на страницу не выводятся.
   Любая из подстановок {{codeword}} / {{codeword_span}} / {{codeword_block}}
   в черновике = отказ сборки (гейт gate_no_codeword_in_text).

4. АВТОРСКАЯ СПЕЦИФИКА В ЧЕРНОВИКЕ НЕ ЖИВЁТ. Домен, адрес оффера, гайд
   установки, продукт и код-слово приходят ТОЛЬКО из config.md скилла
   lead-magnit. В тексте стоят подстановки:

       {{domain}} {{site}} {{target_url}} {{cta_url}} {{install_guide_url}}
       {{target_product}}

   Подстановки код-слова ({{codeword}}, {{codeword_span}}, {{codeword_block}})
   ВЫВЕДЕНЫ ИЗ ОБОРОТА по решению автора: они разворачиваются в пустоту, а сама попытка
   поставить их в текст роняет сборку (gate_no_codeword_in_text). Слово живёт в
   front-matter как метаданные атрибуции и на страницу не попадает.

   Код-гейт трёхсторонний: (а) литерал домена или пути оффера В ЧЕРНОВИКЕ =
   отказ сборки с подсказкой, какую подстановку взять; (б) в готовой спеке
   литерал домена/оффера допустим ТОЛЬКО если пришёл из config - иначе отказ;
   (в) литералы из cta.forbidden_literals запрещены и в черновике, и в
   собранной спеке, НЕЗАВИСИМО от того, что стоит в target_url (старый маршрут
   не должен воскресать после переезда CTA на другой адрес) - С ОДНИМ
   ИСКЛЮЧЕНИЕМ (правка 16.08.2026, дефект С3): без cta.invites_map (фолбэк-режим,
   машина ученика без карты) CTA = сам target_url, и литерал, РАВНЫЙ текущему
   target_url конфига, гейт не ловит - иначе автор без карты не может собрать
   СОБСТВЕННЫЙ действующий лендинг. Карта задана - исключения нет, литерал
   ловится как прежде (см. gate_no_forbidden_literals).
   Так один и тот же черновик у другого автора собирается на его домен, а
   раздаваемый слой не тащит чужие ссылки.

   Адрес {{cta_url}}: задан ключ cta.invites_map - берётся ИМЕННОЙ инвайт
   канала для слага статьи (без utm, атрибуция = сам инвайт), слага нет в
   карте = отказ сборки. Ключа нет - прежний маршрут target_url + utm.

5. STEPS -> узел HowTo (JSON-LD), НЕОБЯЗАТЕЛЬНО. Список шагов лежит в
   front-matter, а не в теле - тот же приём, что у breadcrumbs/hero/figures:

       steps:
         - {name: "Открыть страницу проекта", text: "Найти кнопку Code над списком файлов"}
         - {name: "Выбрать способ под задачу", text: "Нужны обновления - клон, разовый снимок - ZIP"}
         - {name: "...", text: "...", url: "#svoy-yakor"}   <- url необязателен, у каждого шага свой

   Front-matter, а не :::-директива, ПОТОМУ ЧТО build_page.py:980 кладёт
   spec["steps"] в JSON-LD БЕЗ обработки (в отличие от faq, где текст чистит
   ld_text()) - значит name/text обязаны прийти уже ЧИСТЫМ текстом. inline()
   сюда не зовём: markdown-разметка **/[]()/`код` уехала бы буквами прямо в
   структурированные данные.

   Обязательны непустые name и text у КАЖДОГО шага. Число шагов - в вилке
   2-20 (STEPS_MIN/STEPS_MAX): меньше не тянет на инструкцию из нескольких
   шагов, больше обычно значит, что в steps по ошибке уехал чек-лист или
   список другой природы. Нарушение любого условия - отказ сборки с именем
   черновика, индексом шага и что не так (не молчаливый пропуск).

   Поле не заполнили вовсе - узел HowTo просто не соберётся, это НЕ ошибка:
   HowTo нужен не каждой статье, только пошаговым гайдам (schema-generator.py
   и build_page.py:980-981 уже готовы принять поле - молчал ровно этот шов).

──────────────────────────────────────────────────────────────────────────────
"""

import argparse
import collections
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_PAGE = os.path.join(HERE, "build_page.py")
TESTS = os.path.join(HERE, "tests")
DEFAULT_CONFIG = os.path.expanduser("~/.claude/skills/lead-magnit/config.md")

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e",
    "ю": "yu", "я": "ya",
}

ENGINE_MARK = "article_build"        # маркер контракта в front-matter черновика
OWN_KINDS = ("screenshot", "measure", "quote", "number", "artifact")
FAQ_HEADINGS = ("частые вопросы", "faq", "вопросы и ответы")
SOURCES_HEADINGS = ("источники", "sources")
TABLE_HINT = "Таблица прокручивается вбок →"


class BuildError(Exception):
    pass


def fail(msg):
    raise BuildError(msg)


def slugify(text, words=6):
    t = re.sub(r"\s+", " ", text or "").strip().lower()
    out = "".join(TRANSLIT.get(ch, ch) for ch in t)
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return "-".join([x for x in out.split("-") if x][:words]) or "razdel"


# ── ОДНА реализация экранирования листингов ──────────────────────────────────

def listing(text, own=None):
    """<pre><code> с экранированием. ЕДИНСТВЕННОЕ место, где оно происходит.

    Раньше копия жила в каждом конвертере, и в половине её просто не было:
    сырой <style>/<!DOCTYPE> внутри <pre> браузер читает как настоящий тег и
    гасит остаток статьи, а сборщик теряет на нём разделы (класс закрыт
    по решению автора, КАНОН 23 build_page.py). Отступов внутрь листинга не добавляем
    никогда: пробел в <pre> - это содержимое, а не форматирование.
    """
    if own and own not in OWN_KINDS:
        fail("own=%s не из канона %s" % (own, "|".join(OWN_KINDS)))
    own_attr = ' data-own="%s"' % own if own else ""
    return "<pre%s><code>%s</code></pre>" % (own_attr, html.escape(text, quote=False))


# ── config.md ────────────────────────────────────────────────────────────────

def _yaml_block(raw):
    m = re.search(r"```ya?ml\s*\n(.*?)```", raw, re.S)
    return m.group(1) if m else None


def load_config(path=None):
    """Портируемые значения автора. Один источник, никаких литералов в коде."""
    path = os.path.expanduser(path or os.environ.get("LEAD_MAGNIT_CONFIG") or DEFAULT_CONFIG)
    if not os.path.exists(path):
        fail("не найден config.md скилла lead-magnit: %s "
             "(передай --config или задай LEAD_MAGNIT_CONFIG)" % path)
    raw = open(path, encoding="utf-8").read()
    block = _yaml_block(raw)
    if not block:
        fail("в %s нет yaml-блока с настройками автора" % path)
    data = {}
    try:
        import yaml
        data = yaml.safe_load(block) or {}
    except ImportError:
        for line in block.split("\n"):
            m = re.match(r"^([a-z_]+):\s*(\S.*?)\s*(?:#.*)?$", line)
            if m:
                data[m.group(1)] = m.group(2)
    for key in ("domain", "target_url"):
        if not data.get(key):
            fail("в config.md нет обязательного поля %s" % key)
    dom = str(data["domain"]).strip().rstrip("/")
    host = re.sub(r"^https?://", "", dom)
    cfg = {
        "path": path,
        "domain": host,
        "site": "https://" + host,
        "target_url": str(data["target_url"]).strip(),
        "install_guide_url": str(data.get("install_guide_url") or "").strip(),
        "target_product": str(data.get("target_product") or "").strip(),
        "author_card": data.get("author_card"),
        "codeword_block": data.get("codeword_block"),
    }
    p = re.sub(r"^https?://[^/]+", "", cfg["target_url"]) or "/"
    cfg["target_path"] = p.split("?")[0]
    # блок cta: вложенный, и это тот случай, где резервный разбор без PyYAML
    # обязан кричать, а не молчать. Регексный фолбэк выше читает ТОЛЬКО плоские
    # «ключ: значение» - секцию cta он не увидит вовсе, и сборка тихо ушла бы на
    # старый маршрут (лендинг+utm) при живой карте инвайтов в конфиге
    cta = data.get("cta") if isinstance(data.get("cta"), dict) else {}
    if not cta and re.search(r"(?m)^cta:\s*$", block):
        fail("в %s есть секция cta:, но разобрать её нечем - нет PyYAML "
             "(pip3 install pyyaml). Без разбора секции сборка ушла бы на старый "
             "маршрут CTA молча" % path)
    cfg["accepted_prefixes"] = [str(x).strip() for x in (cta.get("accepted_prefixes") or [])
                                if str(x).strip()]
    cfg["forbidden_literals"] = [str(x).strip() for x in (cta.get("forbidden_literals") or [])
                                 if str(x).strip()]
    im = str(cta.get("invites_map") or "").strip()
    cfg["invites_map"] = os.path.expanduser(im) if im else ""
    cfg["invites"] = load_invites_map(cfg["invites_map"]) if cfg["invites_map"] else None
    return cfg


# ── карта «страница → именной инвайт канала» ─────────────────────────────────
#
# ЗАЧЕМ (мандат автора). CTA статьи ведёт не на общий лендинг оффера,
# а в закрытый канал по ИМЕННОЙ ссылке ЭТОЙ страницы: имя инвайта = метка
# атрибуции (тег src:<слаг> на стороне бота), поэтому utm к нему не клеится -
# ссылка и есть метка. Карта - данные проекта, путь приезжает из config.md
# (cta.invites_map). Ключа нет - поведение прежнее (target_url + utm), и это
# рабочий режим для любого автора, у которого именных инвайтов нет.


def load_invites_map(path):
    """{слаг: адрес инвайта}. Битая/пустая карта = отказ, а не тихий фолбэк."""
    if not os.path.exists(path):
        fail("cta.invites_map указывает на несуществующий файл: %s. Либо положи "
             "карту по этому пути, либо убери ключ из config.md (тогда CTA "
             "собирается по-старому: target_url + utm)" % path)
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        fail("карта инвайтов %s не читается как JSON: %s" % (path, e))
    if not isinstance(raw, dict) or not raw:
        fail("карта инвайтов %s пустая или не объект {слаг: …}" % path)
    out = {}
    for k, v in raw.items():
        k = str(k).strip()
        if k.startswith("_"):        # служебные поля карты (комментарий, версия)
            continue
        link = v.get("link") if isinstance(v, dict) else v
        link = str(link or "").strip()
        if link:
            out[k] = link
    if not out:
        fail("в карте инвайтов %s нет ни одной ссылки (ждём {слаг: {link: …}} "
             "либо {слаг: адрес})" % path)
    return out


def invite_keys(slug):
    """Порядок ключей карты для слага: полный → guide-слаг → без guide- → 25 симв.

    Хвост порядка - не украшение: реестр инвайтов на стороне бота хранит имя
    БЕЗ префикса «guide-» и обрезанным до 25 символов (ограничение поля), а
    страница живёт под полным слагом. Один слаг = один инвайт в любой из форм.
    """
    bare = re.sub(r"^guide-", "", slug)
    out = []
    for k in (slug, "guide-" + bare, bare, bare[:25]):
        if k and k not in out:
            out.append(k)
    return out


def invite_for_slug(cfg, slug):
    """Именной инвайт страницы. Нет в карте - ГРОМКИЙ отказ сборки."""
    inv = cfg.get("invites") or {}
    tried = invite_keys(slug)
    for k in tried:
        if inv.get(k):
            return inv[k]
    fail("слага «%s» нет в карте инвайтов %s (пробовал ключи: %s). CTA этой "
         "статьи вести некуда, а тихо подставить лендинг оффера нельзя - именно "
         "это и правим. Лечение: заведи инвайт страницы в боте канала, обнови "
         "карту свежим TSV и пересобери"
         % (slug, cfg.get("invites_map"), " · ".join(tried)))


def config_tokens(cfg, slug, utm_source="guide", utm_content=None, codeword=""):
    """Подстановки {{...}} -> значения из config. Единственный канал специфики."""
    # ── адрес CTA ────────────────────────────────────────────────────────────
    # Задана карта инвайтов - CTA статьи = ИМЕННАЯ ссылка канала этой страницы,
    # и utm к ней НЕ клеится: t.me не читает query-хвост как метку, а атрибуцию
    # несёт сам инвайт (он уникален на страницу). Карты нет - прежний маршрут:
    # адрес оффера из config + utm.
    if cfg.get("invites") is not None:
        cta = invite_for_slug(cfg, slug)
    else:
        sep = "&amp;" if "?" in cfg["target_url"] else "?"
        cta = cfg["target_url"]
        if utm_source:
            cta = "%s%sutm_source=%s&amp;utm_content=%s" % (
                cta, sep, utm_source, utm_content or slug)
    product = cfg["target_product"] or "продукт автора"
    short = product.split("(")[0].strip().rstrip(",").strip() or product
    # КОД-СЛОВА В ТЕКСТЕ СТАТЬИ НЕТ (решение владельца). Обе формы
    # оставлены как ПУСТЫЕ подстановки, чтобы старый черновик не падал на
    # «неизвестный токен», а разворачивался в ничто; сама попытка их применить
    # ловится гейтом gate_no_codeword_in_text ещё до сборки страницы.
    # Читатель статьи приходит из Яндекса и Google: слова он не знает, вход
    # открывает кнопка, а связка карусель→статья живёт в реестрах, не в тексте
    span = ""
    block = ""
    return {
        "domain": cfg["domain"],
        "site": cfg["site"],
        "target_url": cfg["target_url"],
        "cta_url": cta,
        "install_guide_url": cfg["install_guide_url"],
        "target_product": product,
        "target_product_short": short,
        "codeword": codeword or "",
        "codeword_span": span,
        "codeword_block": block,
    }


TOKEN_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def substitute(value, tokens, seen=None):
    """Рекурсивная подстановка по всей спеке. Делается ПОСЛЕДНИМ шагом."""
    if isinstance(value, dict):
        return {k: substitute(v, tokens) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, tokens) for v in value]
    if not isinstance(value, str):
        return value
    out, guard = value, 0
    while TOKEN_RE.search(out) and guard < 5:
        def one(m):
            k = m.group(1)
            if k not in tokens:
                fail("неизвестная подстановка {{%s}} - канон: %s"
                     % (k, ", ".join(sorted(tokens))))
            return str(tokens[k])
        out = TOKEN_RE.sub(one, out)
        guard += 1
    return out


# ── гейт специфики ───────────────────────────────────────────────────────────

HINT = ("специфика автора живёт ТОЛЬКО в config.md скилла lead-magnit. "
        "В черновике ставь подстановку: {{domain}} · {{site}} · {{target_url}} · "
        "{{cta_url}} (адрес CTA: именной инвайт канала по карте cta.invites_map, "
        "а без карты - адрес оффера с utm) · {{install_guide_url}} · "
        "{{target_product}} · {{codeword}} · {{codeword_span}} · {{codeword_block}}")


def gate_draft_has_no_specifics(raw, cfg, where="draft.md"):
    bad = []
    for m in re.finditer(re.escape(cfg["domain"]), raw):
        bad.append(("домен " + cfg["domain"], raw[max(0, m.start() - 40):m.start() + 40]))
    tp = cfg["target_path"]
    if tp and tp != "/":
        for m in re.finditer(re.escape(tp), raw):
            bad.append(("путь оффера " + tp, raw[max(0, m.start() - 40):m.start() + 40]))
    if bad:
        what, ctx = bad[0]
        fail("в %s захардкожена %s (всего мест: %d). %s\nПервое место: …%s…"
             % (where, what, len(bad), HINT, re.sub(r"\s+", " ", ctx).strip()))


# ── гейт запрещённых литералов: НЕ зависит от target_url ─────────────────────
#
# ЗАЧЕМ (по решению автора). Гейт выше ловит ровно то, что СЕЙЧАС стоит в target_url:
# пока адресом оффера был лендинг, литерал лендинга ловился им заодно. CTA
# переехал на именные инвайты канала - и защита от старого маршрута уехала
# вместе с target_path, молча. Список литералов живёт в config.md
# (cta.forbidden_literals) и проверяется САМ ПО СЕБЕ: старый лендинг, чужой бот,
# любой адрес, которого в статье быть не должно. Пустой список = проверять
# нечего (нормальный режим автора, у которого прошлых маршрутов не было).
#
# 🔴 ИСКЛЮЧЕНИЕ ДЛЯ ФОЛБЭК-РЕЖИМА (правка 16.08.2026, дефект С3). Автор без
# cta.invites_map (ученик без карты - обычная, легитимная машина) собирает CTA
# прежним маршрутом: {{cta_url}} = target_url + utm. Если его forbidden_literals
# при этом содержит литерал, равный ЕГО ЖЕ target_url (типичный случай -
# скопировал секцию cta целиком с чужим списком, где старый маршрут = его же
# текущий лендинг), гейт ловил собственный действующий CTA как «запрещённый
# маршрут», и сборка падала на собственном лендинге - тупик без другого адреса.
# literal_matches_own_target() сравнивает ЗНАЧЕНИЕ литерала с cfg["target_url"]/
# cfg["target_path"] (все формы forbidden_forms) и, ТОЛЬКО когда карты инвайтов
# нет (cfg.get("invites") is None), гейт этот КОНКРЕТНЫЙ литерал пропускает -
# остальные литералы списка (чужой бот, старый лендинг ДРУГОГО автора) ловятся
# как прежде. Карта задана - исключения нет НИКОГДА: CTA уже не на target_url,
# и его литерал в тексте - это ровно воскресший старый маршрут, от которого
# гейт и защищает (см. ЗАЧЕМ выше).


def literal_matches_own_target(lit, cfg):
    """Литерал (в любой форме) равен ТЕКУЩЕМУ target_url/target_path конфига.

    Сравнение по ЗНАЧЕНИЮ, не по позиции в тексте: обе стороны прогоняются
    через forbidden_forms (без хвостового слеша, url-encoded), иначе
    «/<твой-продукт>/» и «/<твой-продукт>» считались бы разными литералами и исключение не
    сработало бы на ровном месте.
    """
    own = {str(cfg.get("target_url") or "").strip(),
           str(cfg.get("target_path") or "").strip()}
    own = {o for o in own if o}
    if not own:
        return False
    lit_forms = {f.lower() for f in forbidden_forms(lit)}
    own_forms = set()
    for o in own:
        own_forms |= {f.lower() for f in forbidden_forms(o)}
    return bool(lit_forms & own_forms)

def forbidden_forms(lit):
    """Формы ОДНОГО литерала: как есть · без хвостового слеша · url-encoded.

    Маршрут прячется в странице не одной записью: путь `/<твой-продукт>/` живёт там же
    как `<домен>/<твой-продукт>` без хвостового слеша и как `%2F<твой-продукт>%2F` внутри
    параметра ссылки-шаринга. Ведущий слеш во всех формах СОХРАНЯЕТСЯ - иначе
    якорь `id="<твой-продукт>"` и то же слово в тексте краснели бы зря.
    """
    forms = []

    def add(x):
        if x and x not in forms:
            forms.append(x)

    add(lit)
    if lit.endswith("/") and len(lit.rstrip("/")) > 1:
        add(lit.rstrip("/"))
    for f in list(forms):
        enc = urllib.parse.quote(f, safe="")
        if enc != f:
            add(enc)
    return forms


def forbidden_hits(text, lit):
    """[(форма, позиция)] вхождений литерала любой формой, регистр не важен.

    Длинные формы разбираются первыми, и уже засчитанный кусок текста второй
    раз не считается: иначе одно `/<твой-продукт>/` давало бы два попадания (полная
    форма и она же без хвостового слеша), и счётчик в отказе врал бы вдвое.
    """
    low = text.lower()
    занято, out = [], []
    for f in sorted(forbidden_forms(lit), key=len, reverse=True):
        fl, n = f.lower(), len(f)
        i = low.find(fl)
        while i >= 0:
            if not any(a <= i < b for a, b in занято):
                занято.append((i, i + n))
                out.append((f, i))
            i = low.find(fl, i + 1)
    return sorted(out, key=lambda x: x[1])


def gate_no_forbidden_literals(text, cfg, where):
    lits = cfg.get("forbidden_literals") or []
    # фолбэк-режим (нет cta.invites_map): CTA = target_url, и литерал, равный
    # ему же, не считается «старым маршрутом» - см. С3 в шапке файла
    fallback = cfg.get("invites") is None
    bad = []
    for lit in lits:
        if fallback and literal_matches_own_target(lit, cfg):
            continue
        for форма, i in forbidden_hits(text, lit):
            bad.append((lit if форма == lit else "%s (форма «%s»)" % (lit, форма),
                        text[max(0, i - 40):i + 40]))
    if bad:
        сколько = collections.Counter(l for l, _ in bad)
        lit, ctx = bad[0]
        fail("в %s стоит запрещённый литерал «%s» (всего мест: %d; по литералам: "
             "%s). Список задан в config.md, ключ cta.forbidden_literals - это "
             "маршруты, которых в статье быть не должно. Веди CTA подстановкой "
             "{{cta_url}}.\nПервое место: …%s…"
             % (where, lit, len(bad),
                " · ".join("%s ×%d" % (k, n) for k, n in sorted(сколько.items())),
                re.sub(r"\s+", " ", ctx).strip()))


# ── гейт жаргона уровня страницы: ЧЕРНОВИК, а не только собранная страница ───
#
# ЗАЧЕМ (по решению автора, дефект С2). Уровень страницы §4.6 закона (старое
# позиционирование оффера - «вечнозелён»/«эвергрин»/«смена в записи»/«VIP 990»/
# «All Inclusive»/«живое мероприятие») ловил только article_gates.py на стадии
# page - ПОСЛЕ полной сборки страницы. Автор узнавал о жаргоне последним швом
# конвейера, хотя слово сидело в черновике с самого начала. Список ОДИН на оба
# гейта: article_gates.py читает его отсюда (article_build.CTA_JARGON), второй
# копии в другом файле нет - см. те же грабли, разобранные в шапке cta-гейта
# article_gates.py («второй список... сделал бы ровно тот дубль»).
#
# Уровень CTA-БЛОКА (служебные слова «оффер»/«тариф»/«воронка» и т.п.) сюда
# НЕ входит: он легален в теле статьи и ловится ТОЛЬКО внутри разметки промо
# (класс cta/btn-cta) - у черновика .md этой разметки ещё нет, различать «тело
# vs CTA-блок» на уровне markdown нечем. Эта проверка - для СОБРАННОЙ страницы
# (article_gates.cta_findings, уровень CTA-блока), не для черновика.
#
# 🔴 КАНОН - РЕГЕКС, НЕ ПЛОСКИЕ ЛИТЕРАЛЫ (правка 16.08.2026, скептик раунд-2,
# дефект О1). Подстрочные литералы пропускали словоформы:
#   • « смена в записи» (с ведущим пробелом, чтобы не ловить середину слова) -
#     не матчила «Онлайн-смена в записи»: перед «смена» дефис, не пробел.
#   • «VIP 990» - точная цена; «VIP 1990» / «VIP 2990» проходили мимо.
# Лечение - словоформы регексом: \b перед «смена» ловит ЛЮБУЮ границу слова
# (дефис, пробел, начало строки - юникодный \w в Python включает кириллицу),
# \d+ у VIP - любую цену. Добавлены формы «доступ в записи» и «дни?\s+в\s+
# записи» (о продукте). ГОЛОЕ «в записи» НАМЕРЕННО не добавлено - ложная
# тревога на «10 медиа в записи» (формулировка ВКонтакте, отмечена скептиком
# отдельно): без слова-триггера перед ним это не жаргон, а обычный русский.
# CTA_ONLY_JARGON (уровень CTA-блока, article_gates.py) - словоформы НЕ нужны:
# «оффер»/«тариф»/«воронк» и т.п. уже ловятся подстрокой (падежи - тот же
# корень), отдельно проверено скептиком и подтверждено ok.
#
# 🔴 ДЫРА №2 - СЛОВОФОРМЫ «СМЕНА» МИМО «СМЕНА В ЗАПИСИ» (закрыта по решению автора,
# найдена агентом на живом корпусе). `\bсмена\s+в\s+записи` требует ИМЕННО
# именительный падеж «смена» ПЕРЕД «в записи» - и пропускал два реальных
# случая с проды guide-google-ai-studio:
#   • «…эту работу мы разбираем на смене» - слова «в записи» вообще нет рядом
#   • «учим ... на смене в записи» - перед «в записи» стоит «смене» (дательный/
#     предложный падеж), не «смена» - регекс требовал буквально «смена»
# Плюс три кнопки того же корня мимо словаря вообще: «Посмотреть смену»,
# «Открыть смену», «Перейти к смене» (кнопка = отдельная поверхность, там
# слова канона нет никакого - см. §5.1 CTA-STRATEGIYA.md, дословно «Забрать
# путёвку в <твой-продукт> →»).
#
# ЛЕЧЕНИЕ - узкий падеж, не голый корень. «на смене» (дательный/предложный,
# «мы разбираем НА СМЕНЕ») ловится точечно; «на смену» (винительный) НЕ
# трогаем - это легальный русский оборот «прийти НА СМЕНУ», «заявка на смену
# региона», «запрет на смену планировки», «наём человека на смену» (пример из
# живого корпуса, guide-genspark/guide-neyroset-dizayn-interera/guide-sozdat-
# telegram-bota/guide-antigravity - 5 находок, ни одна не жаргон продукта).
# Калибровка по решению автора (весь корпус lead-magnit-work, draft.md + index.html):
# `на\s+смене` - 0 срабатываний ДО фикса (жаргон уже правился соседом),
# `на\s+смену` (более широкий вариант) дал бы 5 ложных - поэтому падеж УЗКИЙ.
# Кнопочные формы даны по каждому наблюдённому глаголу отдельно (разная
# управляемая форма: «Посмотреть/Открыть/Забрать/Записаться на» берут
# винительный «смену» БЕЗ предлога, «Перейти к» требует предлог «к» +
# дательный «смене») - калибровка та же: 0 срабатываний по всему корпусу.

CTA_JARGON = (
    r"вечнозелён",
    r"вечнозелен",
    r"эвергрин",
    r"\bсмена\s+в\s+записи",     # ловит и «Онлайн-смена в записи» (дефис = граница слова)
    r"на\s+смене\b",              # «разбираем/учим ... на смене» - НЕ «на смену» (см. выше)
    r"(?:Посмотреть|Открыть|Забрать|Записаться\s+на)\s+смену\b",  # кнопка вместо канона §5.1
    r"Перейти\s+к\s+смене\b",      # кнопка вместо канона §5.1
    r"доступ\s+в\s+записи",
    r"дни?\s+в\s+записи",        # «день в записи» / «дни в записи»
    r"VIP\s*\d+",                 # любая цена, не только «990»
    r"All Inclusive",
    r"Живое мероприятие",
)
CTA_JARGON_RE = tuple((p, re.compile(p, re.IGNORECASE)) for p in CTA_JARGON)


def jargon_hits(text):
    """[(форма-паттерн, найденный текст, позиция)] по ВСЕМ формам CTA_JARGON,
    отсортировано по позиции. ЕДИНАЯ функция для обоих гейтов (черновик здесь,
    страница - article_gates.cta_findings через article_build.jargon_hits) -
    второй копии словаря/логики сравнения нет нигде.
    """
    text = text or ""
    out = []
    for pat, rx in CTA_JARGON_RE:
        for m in rx.finditer(text):
            out.append((pat, m.group(0), m.start()))
    return sorted(out, key=lambda x: x[2])


def gate_no_page_jargon(text, where):
    hits = jargon_hits(text)
    if hits:
        _, слово, i = hits[0]
        формы = len({h[0] for h in hits})
        fail("в %s стоит жаргон уровня страницы «%s» (мест: %d, форм словаря: "
             "%d). Это старое позиционирование оффера - вечнозелёный доступ / "
             "смена в записи / VIP-тариф / All Inclusive / живое мероприятие -"
             " канон продукта другой, перепиши абзац своими словами.\n"
             "Первое место: …%s…"
             % (where, слово, len(hits), формы,
                re.sub(r"\s+", " ", text[max(0, i - 40):i + 40]).strip()))


def gate_spec_specifics_from_config(spec, cfg, tokens):
    """В готовой спеке литерал домена/оффера допустим ТОЛЬКО из config."""
    derived = sorted({str(v) for v in tokens.values() if isinstance(v, str) and len(str(v)) > 3},
                     key=len, reverse=True)
    derived += [cfg["site"] + "/", cfg["site"], cfg["domain"]]
    needles = [cfg["domain"]]
    if cfg["target_path"] and cfg["target_path"] != "/":
        needles.append(cfg["target_path"])
    bad = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, "%s.%s" % (path, k))
            return
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (path, i))
            return
        if not isinstance(node, str):
            return
        rest = node
        for d in derived:
            rest = rest.replace(d, " ")
        for n in needles:
            if n in rest:
                bad.append((path, n, node[:120]))

    walk(spec, "spec")
    if bad:
        p, n, sample = bad[0]
        fail("в спеке литерал «%s» не выведен из config (%s, всего мест: %d). %s"
             % (n, p, len(bad), HINT))


# ── markdown ─────────────────────────────────────────────────────────────────

INLINE_CODE_RE = re.compile(r"`([^`]+)`")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


INTERNAL_HREF_RE = re.compile(r"^(?:\{\{\s*(?:site|domain|install_guide_url|target_url)\s*\}\}|/(?!/))")


def is_internal_href(u, cfg=None):
    """Ссылка ведёт на свой сайт? Токен {{site}}/… , свой домен или «/путь».

    Подстановки {{…}} раскрываются ПОСЛЕДНИМ шагом (substitute), поэтому на
    момент разбора инлайна внутренняя ссылка черновика выглядит как
    «{{site}}/guide-…/», а не как адрес с доменом. Считать её внешней нельзя:
    именно на неё вешается класс тап-слоя (см. inline ниже).
    """
    u = (u or "").strip()
    if u.startswith("#") or u.startswith("mailto:") or u.startswith("tel:"):
        return False
    if INTERNAL_HREF_RE.match(u):
        return True
    return bool(cfg) and bool(re.match(r"^https?://", u)) and cfg["domain"] in u


# Класс внутренней ссылки тела статьи. НЕ декоративный: `a.ln` входит в
# селектор тап-слоя 44px в tokens.css (`…a.ln, nav a.rounded-full, summary
# { min-height:var(--tap-min) … }`), и он же снимает ссылку с общего правила
# `footer a:not(.ln)::after`. Конвенция живого корпуса - 74 страницы из 346,
# все внутренние ссылки тела там несут ровно эту пару классов. Одноразовые
# конвертеры ставили её руками в HTML; шов draft.md->spec.json её терял, и
# собранная страница уносила внутренние ссылки без тап-цели (улика по решению автора:
# guide-gemini, 15 ссылок тела без класса против 10 из 10 с классом на проде).
INTERNAL_LINK_CLASS = "ln text-accent"


def inline(text, cfg=None):
    """Инлайн-разметка. Внешняя ссылка получает nofollow, внутренняя - класс."""
    keep = []

    def stash(s):
        keep.append(s)
        return "\x00%d\x00" % (len(keep) - 1)

    text = INLINE_CODE_RE.sub(lambda m: stash("<code>%s</code>" % html.escape(m.group(1))), text)

    def link(m):
        t, u = m.group(1), m.group(2)
        ext = bool(re.match(r"^https?://", u)) and not (cfg and cfg["domain"] in u)
        rel = ' rel="noopener nofollow" target="_blank"' if ext else ""
        cls = ' class="%s"' % INTERNAL_LINK_CLASS if is_internal_href(u, cfg) else ""
        return stash('<a href="%s"%s%s>%s</a>' % (u, cls, rel, inline(t, cfg)))

    text = LINK_RE.sub(link, text)
    text = BOLD_RE.sub(lambda m: "<strong>%s</strong>" % m.group(1), text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
    return text


def md_table(lines, hint=TABLE_HINT, cfg=None, fit=None):
    """fit= - опциональная УЗКАЯ таблица: помещается в экран целиком.

    По умолчанию таблица держит min-width (520px от table.fix и 34rem от
    .table-scroll) и на мобиле скроллится вбок внутри своей обёртки. Это
    правильно для широких сравнений, но ломает таблицу-указатель на 3
    коротких колонки: на 390px обёртка 350px, таблица 544px, и ТРЕТЬЯ
    колонка не видна вовсе (дефект В-Н2, скептик r12 r2 по guide-obrabotka-
    foto - страница обещала «видишь сервис и цену», а цены на экране не было).
    fit= снимает оба min-width инлайном (инлайн бьёт таблицу стилей без
    !important) - таблица садится по ширине обёртки, ячейки переносятся.
    Атрибут ОПЦИОНАЛЬНЫЙ: без него разметка прежняя байт в байт.
    hint="" убирает подпись про боковую прокрутку - у узкой таблицы её нет.
    """
    rows = [l for l in lines if l.strip().startswith("|")]
    if len(rows) < 2:
        fail("таблица короче двух строк: %s" % (lines[0] if lines else ""))
    head = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = []
    for r in rows[2:]:
        body.append([c.strip() for c in r.strip().strip("|").split("|")])
    th = "".join("<th>%s</th>" % inline(c, cfg) for c in head)
    tb = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c, cfg) for c in r)
                 for r in body)
    box = "tablebox tablefit" if fit else "tablebox"
    # ТОЛЬКО снятие min-width. Принудительный перенос (overflow-wrap:anywhere)
    # тут пробовался и отвергнут: он режет min-content до одного знака, ширины
    # раздаются по max-content и имена рвутся посреди слова («Cleanup.p|ictures»,
    # «Шедевру|м»). Без него таблица садится по сумме min-content колонок, слова
    # целые; если содержимое не влезает - таблица честно скроллится, как раньше
    style = ' style="min-width:0;width:100%"' if fit else ""
    hint_html = '  <p class="tablehint">%s</p>\n' % hint if hint else ""
    return ('<div class="%s">\n'
            '  <div class="tablewrap"><table class="fix"%s>\n'
            '    <thead><tr>%s</tr></thead>\n'
            '    <tbody>%s</tbody>\n'
            '  </table></div>\n'
            '%s'
            '</div>' % (box, style, th, tb, hint_html))


# ── ПОДЗАГОЛОВОК ВНУТРИ РАЗДЕЛА ──────────────────────────────────────────────
#
# 🔴 ЗАЧЕМ (дефект «сырая разметка на живой странице», по решению автора).
# split_sections режет тело статьи ТОЛЬКО по H2 - это её работа, разделы страницы
# и есть H2. Подзаголовок третьего уровня («### Шаг 1. Одна строка запускает
# установку», «### Грабля 2. Пост читается как машинный») остаётся внутри тела
# раздела обычной строкой, доезжает до render_md_block, а там ветки на «#» не было
# вовсе - строка падала в последний return и уезжала на страницу буквально:
# `<p>### Шаг 1. Одна строка запускает установку {#shag-1}</p>`. Читатель видел
# решётки и фигурные скобки прямо в тексте статьи. Живые улики на проде по решению автора:
# /guide-claude-code-windows/ (8 штук), /guide-mobilnoe-prilozhenie/,
# /guide-opensource-zamena-saas/; дома то же ещё у пяти страниц корпуса.
# Круг r14 (по решению автора) закрыл только ПОЛОВИНУ класса - служебную метку перед
# директивой («### Источники {#istochniki}» перед :::sources:::) он молча дропает,
# см. ниже по коду. Но подзаголовок с СОДЕРЖАНИЕМ дропать нельзя, его надо
# отрисовать: `article h3` и `article h4` в tokens.css существуют и оформлены,
# ссылка-якорь у h3[id] ставится скриптом page-template.html, оглавление берётся
# только из H2 (build_page.number_sections) - то есть форма для подзаголовка в
# движке уже готова, не хватало ровно разбора.
# УРОВНИ: только 3-6. «#» и «##» сюда не попадают намеренно - H1 у страницы один и
# приезжает из front-matter, а H2 разбирает split_sections; если «##» всё-таки
# доехал до разбора блоков, значит он внутри забора или директивы, и трогать его
# нельзя. Ниже h4 движок не опускается: h5/h6 в tokens.css не оформлены, поэтому
# «#####» и «######» рисуются тем же h4, а не безымянным тегом без стиля.
HEAD_RE = re.compile(r"^(#{3,6})\s+(\S.*?)\s*$")

# own-АБЗАЦ ЧЕРЕЗ КОММЕНТАРИЙ (novice-standard.md §4: «own-абзацем (<!-- own:measure -->
# над абзацем → data-own="measure" в собранной странице)»). До правки r21 (по решению автора,
# фиксер guide-neyroset-dlya-risovaniya) первая строка блока «<!-- own:X -->» ловилась
# общим правилом «первая строка с «<» - готовый HTML» (render_md_block) и весь блок,
# включая абзац за комментарием, уезжал В СОБРАННУЮ СТРАНИЦУ БУКВОЙ: без <p>, без
# инлайн-обработки (обратные кавычки не становились <code>), а сам комментарий срезал
# strip_notes.py на последней миле - то есть атрибут data-own терялся вовсе. Живой
# пример дефекта - guide-neyroset-dlya-risovaniya/index.html:1569 ДО фикса. Комментарий
# без абзаца следом или own-вид не из канона OWN_KINDS - отказ сборки, а не тихий
# пропуск.
OWN_PARA_RE = re.compile(r"^<!--\s*own:([a-z]+)\s*-->$")


def md_blocks(lines):
    """Черновик -> блоки. Забор ```, директива ::: и цитата «>» держатся целиком.

    Цитата режется в СВОЙ блок, а не по пустым строкам, как абзац: подпись
    источника («> - Автор, издание») стоит следующей строкой без пустой между,
    и без отдельного блока она склеилась бы с текстом цитаты в один абзац.
    Внутрь готового HTML-блока (первая строка с «<») разбор цитаты не лезет:
    там «>» бывает хвостом собственного тега.

    ЗАГОЛОВОК «### Текст» ТОЖЕ РЕЖЕТСЯ В СВОЙ БЛОК (по решению автора, дефект видимой
    разметки). split_sections режет тело только по H2, значит подзаголовок H3+
    приезжает сюда обычной строкой и без отдельного блока склеивается с
    соседним абзацем в один <p>. Отдельный блок = render_md_block видит его
    первой строкой и отдаёт <h3>. Внутрь готового HTML-блока (первая строка с
    «<») разбор не лезет по той же причине, что и цитата.
    """
    blocks, cur, fence, direc, quote = [], [], None, None, None
    for ln in lines:
        s = ln.strip()
        if direc is not None:
            direc.append(ln)
            if s == ":::":
                blocks.append(("directive", direc))
                direc = None
            continue
        if fence is not None:
            cur.append(ln)
            if s.startswith("```"):
                blocks.append(("fence", cur))
                cur, fence = [], None
            continue
        if quote is not None:
            if s.startswith(">"):
                quote.append(ln)
                continue
            blocks.append(("md", quote))
            quote = None
        if s.startswith(":::") and s != ":::":
            if cur:
                blocks.append(("md", cur))
                cur = []
            direc = [ln]
            continue
        if s.startswith("```"):
            if cur:
                blocks.append(("md", cur))
                cur = []
            cur, fence = [ln], True
            continue
        if s.startswith(">") and not (cur and cur[0].strip().startswith("<")):
            if cur:
                blocks.append(("md", cur))
                cur = []
            quote = [ln]
            continue
        if HEAD_RE.match(s) and not (cur and cur[0].strip().startswith("<")):
            if cur:
                blocks.append(("md", cur))
                cur = []
            blocks.append(("md", [ln]))
            continue
        if not s:
            if cur:
                blocks.append(("md", cur))
                cur = []
            continue
        cur.append(ln)
    if fence is not None:
        fail("незакрытый забор ``` в черновике")
    if direc is not None:
        fail("незакрытая директива ::: в черновике")
    if quote:
        blocks.append(("md", quote))
    if cur:
        blocks.append(("md", cur))
    return blocks


ATTR_RE = re.compile(r"""([a-z_]+)=(?:"([^"]*)"|'([^']*)'|(\S+))""")


def parse_directive(lines):
    head = lines[0].strip()
    m = re.match(r"^:::([a-z]+)\s*(.*)$", head)
    if not m:
        fail("не разобрана директива: %s" % head)
    name, rest = m.group(1), m.group(2)
    attrs = {}
    for a in ATTR_RE.finditer(rest):
        attrs[a.group(1)] = a.group(2) or a.group(3) or a.group(4) or ""
    body = lines[1:-1]
    return name, attrs, body


FIELD_RE = re.compile(r"^\s*([a-z_]+):\s*(.*)$")


def head_fields(body, allowed):
    """Строки «поле: значение» В НАЧАЛЕ тела. Остальное - содержимое.

    Ограничение «только в начале и только из белого списка» намеренное: иначе
    абзац вида «Срок: черновик через два дня» уехал бы в поля, а не в текст.
    """
    fields, i = {}, 0
    while i < len(body):
        s = body[i]
        if not s.strip():
            if fields:
                i += 1
                continue
            break
        m = FIELD_RE.match(s)
        if not m or m.group(1) not in allowed:
            break
        fields[m.group(1)] = m.group(2).strip()
        i += 1
    return fields, body[i:]


def md_list_items(lines, cfg=None):
    items, cur = [], None
    for ln in lines:
        s = ln.strip()
        m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", s)
        if m:
            if cur is not None:
                items.append(cur)
            cur = m.group(1)
        elif s and cur is not None:
            cur += " " + s
    if cur is not None:
        items.append(cur)
    return [inline(x, cfg) for x in items]


QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
CITE_RE = re.compile(r"^[-–—]\s+(.+)$")

# Где в черновике лежит блок. md_blocks режет текст на блоки БЕЗ нумерации
# (номер строки там никому не нужен), а отказ по цитате обязан назвать место -
# иначе автор ищет одну «>» на 500 строк глазами. Цитата состоит из ДОСЛОВНЫХ
# строк исходника, поэтому место находим поиском этой последовательности в
# файле: одно совпадение = точный номер, иначе честно называем файл и первую
# строку, а не выдуманный номер. Кладёт сюда build_spec: шов однопоточный,
# на процесс собирается один черновик.
SRC = {"name": "draft.md", "lines": []}


def src_place(lines):
    """«draft.md:147» для блока, если такие строки в черновике ровно одни."""
    src, n = SRC.get("lines") or [], len(lines)
    hits = [i for i in range(len(src) - n + 1) if src[i:i + n] == lines]
    if len(hits) == 1:
        return "%s:%d" % (SRC["name"], hits[0] + 1)
    return "%s (строка «%s»)" % (SRC["name"], lines[0].strip()[:70])


def render_quote(lines, cfg=None):
    """Строки «> …» -> <blockquote><p>текст</p><cite>подпись</cite></blockquote>.

    Подпись - ПОСЛЕДНЯЯ строка цитаты, начатая с дефиса («> - Anthropic, …»):
    именно так подписаны цитаты во всей пачке, пустой строки перед подписью
    там нет. Значит снимаем её ДО склейки абзацев, иначе она приклеилась бы к
    последнему предложению цитаты. Уходит в <cite>, потому что tokens.css
    разд. 12b красит подпись только там.
    """
    bodies = []
    for ln in lines:
        m = QUOTE_RE.match(ln)
        bodies.append((m.group(1) if m else ln).strip())
    while bodies and not bodies[-1]:
        bodies.pop()
    cite = ""
    if bodies:
        m = CITE_RE.match(bodies[-1])
        if m:
            cite = m.group(1).strip()
            bodies.pop()
    paras, cur = [], []
    for body in bodies:
        if body:
            cur.append(body)
        elif cur:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    if not any(re.search(r"\w", p) for p in paras):
        if cite:
            fail("цитата в %s состоит из одной подписи «%s» без самой цитаты. "
                 "Канон: сначала строки «> слова источника», последней строкой "
                 "«> - Автор, издание»" % (src_place(lines), cite[:70]))
        fail("пустая цитата в %s: строки «>» без текста. Цитата несёт слова "
             "источника, пустой блок на странице - полоса без содержимого"
             % src_place(lines))
    out = ["<blockquote>"]
    out += ["  <p>%s</p>" % inline(p, cfg) for p in paras]
    if cite:
        out.append("  <cite>%s</cite>" % inline(cite, cfg))
    out.append("</blockquote>")
    return "\n".join(out)


def render_md_block(lines, cfg):
    first = lines[0].strip()
    own_c = OWN_PARA_RE.match(first)
    if own_c:
        kind = own_c.group(1)
        if kind not in OWN_KINDS:
            fail("<!-- own:%s --> не из канона %s" % (kind, "|".join(OWN_KINDS)))
        rest = [l for l in lines[1:] if l.strip()]
        if not rest:
            fail("<!-- own:%s --> без абзаца следом" % kind)
        return '<p data-own="%s">%s</p>' % (
            kind, inline(" ".join(l.strip() for l in rest), cfg))
    h = HEAD_RE.match(first) if not first.startswith("<") else None
    if h:
        # Подзаголовок раздела. Якорь «{#свой-якорь}» - необязательный: есть -
        # уезжает в id (ссылка-решётка у h3[id] ставится скриптом страницы,
        # входящие ссылки на него держатся), нет - тег без id, и это нормально:
        # оглавление собирается из H2, подзаголовку якорь нужен не всегда.
        lvl = min(len(h.group(1)), 4)
        text = h.group(2)
        anc = ANCHOR_RE.search(text)
        idattr = ""
        if anc:
            idattr = ' id="%s"' % anc.group(1)
            text = ANCHOR_RE.sub("", text).strip()
        if not text:
            fail("подзаголовок «%s» без текста - остался один якорь" % first)
        rest = [l for l in lines[1:] if l.strip()]
        head = "<h%d%s>%s</h%d>" % (lvl, idattr, inline(text, cfg), lvl)
        if not rest:
            return head
        # Абзац, приклеенный к заголовку без пустой строки - разбираем следом,
        # иначе он утонул бы в заголовке и пропал со страницы
        return head + "\n" + render_md_block(rest, cfg)
    if first.startswith("```"):
        own = None
        info = first[3:].strip()
        a = ATTR_RE.search(info)
        if a and a.group(1) == "own":
            own = a.group(2) or a.group(3) or a.group(4)
        return listing("\n".join(lines[1:-1]), own)
    if first.startswith(">"):
        return render_quote(lines, cfg)
    if first.startswith("|"):
        return md_table(lines, TABLE_HINT, cfg)
    if first.startswith("<"):
        return "\n".join(lines)
    if re.match(r"^\d+\.\s", first):
        return "<ol>\n%s\n</ol>" % "\n".join("  <li>%s</li>" % i
                                             for i in md_list_items(lines, cfg))
    if re.match(r"^[-*]\s", first):
        return "<ul>\n%s\n</ul>" % "\n".join("  <li>%s</li>" % i
                                             for i in md_list_items(lines, cfg))
    return "<p>%s</p>" % inline(" ".join(l.strip() for l in lines), cfg)


# ── директивы ────────────────────────────────────────────────────────────────

ALT_MIN, ALT_MAX = 50, 125


def check_alt(alt, where):
    """Вилка alt - ОДНА на все картинки страницы: фигуры, hero, карточки related.

    Раньше её сторожил постскриптум в main() каждого одноразового конвертера
    (и только для части картинок), поэтому вилка держалась не везде.
    """
    n = len(alt or "")
    if not (ALT_MIN <= n <= ALT_MAX):
        fail("%s: alt %d знаков, вилка канона %d-%d" % (where, n, ALT_MIN, ALT_MAX))


def real_image_size(path):
    """Реальные пиксели смонтированного файла, если он физически лежит на диске.

    ФИКС (по решению автора, волна r21, дефект major «width/height атрибута не
    совпадает с реальным файлом»): w=/h= в директиве и в front-matter «hero»
    писатель печатает руками, и это годится как ТРЕБОВАНИЕ (без размера кадр
    в производство не идёт), но copy-paste шаблонных 1440x900 из прошлой
    статьи молча уезжал на страницу с портретным кадром 562x1238 - реальный
    файл никто не сверял. Файл уже смонтирован - его пиксели побеждают то,
    что написано в директиве; нет файла или нет Pillow - тихий откат на
    заявленные w=/h=, сборка драфта без готовых кадров не должна падать.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    if not path or not os.path.isfile(path):
        return None
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def render_figure(attrs, body, ctx):
    fields, _ = head_fields(body, {"alt", "caption"})
    need = [k for k in ("slug", "w", "h") if not attrs.get(k)]
    if need:
        fail(":::figure без %s" % ", ".join(need))
    if not fields.get("alt"):
        fail(":::figure slug=%s без строки «alt:»" % attrs["slug"])
    check_alt(fields["alt"], ":::figure slug=%s" % attrs["slug"])
    ext = attrs.get("ext", "jpg")
    own = ' data-own="%s"' % attrs["own"] if attrs.get("own") else ""
    if attrs.get("own") and attrs["own"] not in OWN_KINDS:
        fail("own=%s не из канона %s" % (attrs["own"], "|".join(OWN_KINDS)))
    base = "%s/%s-%s" % (ctx["assets_dir"], ctx["assets_base"], attrs["slug"])
    w, h = attrs["w"], attrs["h"]
    draft_dir = ctx.get("draft_dir")
    if draft_dir:
        real = real_image_size(os.path.join(draft_dir, "%s.%s" % (base, ext)))
        if real and (str(real[0]), str(real[1])) != (str(w), str(h)):
            print("article_build: :::figure slug=%s - заявлено %sx%s, реальный файл "
                  "%sx%s, беру реальные пиксели" % (attrs["slug"], w, h, real[0], real[1]),
                  file=sys.stderr)
            w, h = real
    cap = ("\n  <figcaption>%s</figcaption>" % inline(fields["caption"], ctx["cfg"])
           if fields.get("caption") else "")
    return ('<figure class="%s"%s>\n'
            '  <picture>\n'
            '    <source srcset="%s.webp" type="image/webp">\n'
            '    <img src="%s.%s" alt="%s" width="%s" height="%s" '
            'loading="lazy" decoding="async">\n'
            '  </picture>%s\n'
            '</figure>') % (attrs.get("class", "fig"), own, base, base, ext,
                            html.escape(fields["alt"], quote=True),
                            w, h, cap)


CTA_FIELD_RE = re.compile(r"^\s*(eyebrow|heading|button):\s*(.+?)\s*$")


def render_cta(attrs, body, ctx):
    """Промо-блок. Поля eyebrow/heading/button читаются В ЛЮБОМ МЕСТЕ тела.

    Тут намеренно НЕ head_fields: у промо кнопка почти всегда стоит ПОСЛЕ
    абзаца, и правило «поля только в начале» тихо превращало бы её в строку
    текста - промо оставалось бы без ссылки на оффер. Ключи английские, поэтому
    спутать их с русской прозой нельзя.
    """
    place = attrs.get("place")
    if place not in ("compact", "mid", "final"):
        fail(":::cta без place=compact|mid|final")
    parts, chunk = [], []

    def flush():
        if not any(x.strip() for x in chunk):
            del chunk[:]
            return
        for kind, lines in md_blocks(chunk):
            if kind == "directive":
                fail(":::cta не вкладывает другие директивы")
            parts.append(render_md_block(lines, ctx["cfg"]))
        del chunk[:]

    for ln in body:
        m = CTA_FIELD_RE.match(ln)
        if not m:
            chunk.append(ln)
            continue
        flush()
        key, val = m.group(1), inline(m.group(2), ctx["cfg"])
        if key == "eyebrow":
            parts.append('<p class="eyebrow">%s</p>' % val)
        elif key == "heading":
            parts.append("<h3>%s</h3>" % val)
        else:
            parts.append('<p><a class="btn-cta" href="{{cta_url}}">%s</a></p>' % val)
    flush()
    body_html = "".join(parts)
    if place in ("compact", "mid", "final") and "btn-cta" not in body_html:
        fail(":::cta place=%s без строки «button:» - промо без ссылки на оффер "
             "(КАНОН: каждый промо-блок ведёт на цель)" % place)
    # АВТОДОПИСЬ БЛОКА КОД-СЛОВА УБРАНА по решению автора (решение владельца). Раньше
    # каждый финальный CTA получал сюда «Код-слово этой статьи - СЛОВО…» - для
    # читателя из поиска это шум ровно там, где он решает, жать кнопку или уйти
    return place, body_html


def render_related(body, ctx):
    cards, group = [], []
    allowed = {"href", "thumb", "alt", "title", "desc", "tag"}
    for ln in body + [""]:
        if ln.strip():
            group.append(ln)
            continue
        if not group:
            continue
        f, rest = head_fields(group, allowed)
        if rest and any(x.strip() for x in rest):
            fail(":::related: строка не разобрана как поле: %s" % rest[0].strip())
        for k in ("href", "thumb", "alt", "title", "desc"):
            if not f.get(k):
                fail(":::related: карточка без поля «%s»" % k)
        check_alt(f["alt"], ":::related href=%s" % f["href"])
        cards.append({k: f[k] for k in allowed if k in f})
        group = []
    if not cards:
        fail(":::related пустая")
    return cards


def render_faq(body, ctx):
    out, q, ans = [], None, []
    for ln in body + ["### "]:
        m = re.match(r"^\s*###\s+(.*)$", ln)
        if m:
            if q:
                if not ans:
                    fail(":::faq: у вопроса «%s» нет ответа" % q)
                out.append({"q": q, "a": "".join(ans)})
            q, ans = m.group(1).strip(), []
            continue
        if q is None:
            if ln.strip():
                fail(":::faq: текст до первого «### Вопрос»: %s" % ln.strip())
            continue
        ans.append(ln)
    res = []
    for x in out:
        blocks = md_blocks(x["a"].split("\n"))
        html_a = "".join(render_md_block(l, ctx["cfg"]) for k, l in blocks if k != "directive")
        res.append({"q": x["q"], "a": html_a})
    if not res:
        fail(":::faq пустая")
    return res


def render_checklist(body, ctx):
    f, rest = head_fields(body, {"title", "intro"})
    if not f.get("title"):
        fail(":::checklist без строки «title:»")
    items = md_list_items(rest, ctx["cfg"])
    if not items:
        fail(":::checklist без пунктов списка")
    cl = {"title": f["title"], "items": items}
    if f.get("intro"):
        cl["intro"] = f["intro"]
    return cl


def render_sources(attrs, body, ctx):
    items = md_list_items(body, ctx["cfg"])
    if not items:
        fail(":::sources без пунктов списка")
    return items, attrs.get("intro", "")


STEPS_MIN, STEPS_MAX = 2, 20


def parse_steps(raw_steps, where):
    """front-matter «steps» -> spec.json["steps"] для узла HowTo.

    Формат - список объектных карт, тот же приём что у breadcrumbs/hero/figures
    (front-matter, а не :::-директива - см. КОНТРАКТ, пункт 5 в шапке файла).
    build_page.py:980 кладёт spec["steps"] в JSON-LD БЕЗ обработки, поэтому
    name/text тут - чистый текст: inline() не зовём, markdown/HTML не несём.
    """
    if not isinstance(raw_steps, list):
        fail("%s: front-matter «steps» должен быть списком объектов "
             "{name: ..., text: ...}, пришло: %s" % (where, type(raw_steps).__name__))
    n = len(raw_steps)
    if not (STEPS_MIN <= n <= STEPS_MAX):
        fail("%s: front-matter «steps» - %d шагов, канон HowTo держит вилку %d-%d "
             "(меньше не тянет на пошаговую инструкцию, больше обычно значит, что в "
             "steps по ошибке уехал чек-лист или список другой природы)"
             % (where, n, STEPS_MIN, STEPS_MAX))
    out = []
    for i, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            fail("%s: front-matter «steps[%d]» не объект {name: .., text: ..}, "
                 "пришло: %r" % (where, i, item))
        name = str(item.get("name") or "").strip()
        text = str(item.get("text") or "").strip()
        if not name:
            fail("%s: front-matter «steps[%d]» без поля «name»" % (where, i))
        if not text:
            fail("%s: front-matter «steps[%d]» («%s») без поля «text»" % (where, i, name))
        step = {"name": name, "text": text}
        url = str(item.get("url") or "").strip()
        if url:
            step["url"] = url
        out.append(step)
    return out


# ── разбор черновика ─────────────────────────────────────────────────────────

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
H2_RE = re.compile(r"^##\s+(?!#)(.*?)\s*$")
ANCHOR_RE = re.compile(r"\{#([A-Za-z0-9_-]+)\}\s*$")


def parse_front_matter(raw):
    m = FM_RE.match(raw)
    if not m:
        fail("в черновике нет front-matter (блок YAML между «---» в самом верху)")
    try:
        import yaml
    except ImportError:
        fail("для разбора front-matter нужен PyYAML (pip install pyyaml)")
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception as e:
        fail("front-matter не разобрался как YAML: %s\nЧастая причина - двоеточие "
             "внутри значения без кавычек (title: «Тема: подзаголовок» -> "
             'title: "Тема: подзаголовок")' % str(e).split("\n")[0])
    if not isinstance(fm, dict):
        fail("front-matter не разобрался в словарь")
    return fm, raw[m.end():]


def split_sections(body):
    """Тело -> [(heading, anchor|None, [строки])]. Всё до первого H2 - пролог."""
    lines = body.split("\n")
    pre, out, cur = [], [], None
    fence, direc = None, None
    for ln in lines:
        s = ln.strip()
        if direc:
            (cur[2] if cur else pre).append(ln)
            if s == ":::":
                direc = None
            continue
        if fence:
            (cur[2] if cur else pre).append(ln)
            if s.startswith("```"):
                fence = None
            continue
        if s.startswith(":::") and s != ":::":
            direc = True
            (cur[2] if cur else pre).append(ln)
            continue
        if s.startswith("```"):
            fence = True
            (cur[2] if cur else pre).append(ln)
            continue
        m = H2_RE.match(ln)
        if m:
            if cur:
                out.append(cur)
            title = m.group(1)
            anc = ANCHOR_RE.search(title)
            aid = anc.group(1) if anc else None
            if anc:
                title = ANCHOR_RE.sub("", title).strip()
            cur = [title, aid, []]
            continue
        (cur[2] if cur else pre).append(ln)
    if cur:
        out.append(cur)
    return pre, out


def match_figures(fig_specs, sections):
    """Подвязка фигур к разделам ПОДСТРОКОЙ заголовка.

    Урок guide-grok по решению автора: точное равенство не работает - заголовки несут
    префиксы («Шаг 3. Как открыть…»), суффиксы и знак вопроса. Матчим подстрокой
    по нормализованному заголовку; 0 или >1 совпадений = отказ, а не тихий
    промах, иначе картинка молча не доедет до страницы.
    """
    res = {}
    norm = [re.sub(r"\s+", " ", s[0]).strip().lower() for s in sections]
    for spec in fig_specs:
        key = str(spec.get("match", "")).strip()
        if not key:
            fail("figures: запись без поля match")
        k = re.sub(r"\s+", " ", key).lower()
        hits = [i for i, h in enumerate(norm) if k in h or h.endswith(k)]
        if not hits:
            fail("figures: «%s» не нашлось ни в одном заголовке H2" % key)
        if len(hits) > 1:
            fail("figures: «%s» подходит к %d заголовкам (%s) - уточни match"
                 % (key, len(hits), ", ".join(sections[i][0] for i in hits)))
        res.setdefault(hits[0], []).append(spec)
    return res


def figure_from_manifest(spec, ctx):
    attrs = {k: str(spec[k]) for k in ("slug", "w", "h", "own", "ext", "class")
             if spec.get(k) is not None}
    body = ["alt: %s" % spec.get("alt", "")]
    if spec.get("caption"):
        body.append("caption: %s" % spec["caption"])
    return render_figure(attrs, body, ctx)


def build_spec(raw, cfg, draft_path="draft.md"):
    SRC["name"], SRC["lines"] = os.path.basename(draft_path), raw.split("\n")
    fm, body = parse_front_matter(raw)
    if str(fm.get("engine", "")).strip() != ENGINE_MARK:
        fail("в front-matter нет маркера «engine: %s». Черновики старой схемы "
             "(meta_title / hero_image / cta_url / status) конвейер не собирает: "
             "они архив, их источник истины - spec.json рядом. Новый черновик "
             "пишется по контракту в шапке article_build.py" % ENGINE_MARK)
    gate_draft_has_no_specifics(raw, cfg, os.path.basename(draft_path))
    gate_no_forbidden_literals(raw, cfg, os.path.basename(draft_path))
    gate_no_page_jargon(raw, os.path.basename(draft_path))

    for k in ("slug", "title", "description", "h1", "date_published"):
        if not fm.get(k):
            fail("front-matter без обязательного поля «%s»" % k)
    slug = str(fm["slug"]).strip("/")
    assets_base = str(fm.get("assets_base") or re.sub(r"^guide-", "", slug))
    ctx = {"cfg": cfg, "assets_base": assets_base,
           "assets_dir": str(fm.get("assets_dir", "assets")),
           # реальные пиксели смонтированного файла бьют шаблонные w=/h= -
           # см. real_image_size(); путь нужен АБСОЛЮТНЫМ, чтобы не зависеть
           # от cwd вызова (тот же приём, что и extra_css_file ниже)
           "draft_dir": os.path.dirname(os.path.abspath(draft_path))}

    pre, sections = split_sections(body)
    if not sections:
        fail("в черновике нет ни одного раздела «## Заголовок»")

    figs_by_section = match_figures(fm.get("figures") or [], sections)

    spec = {"kind": str(fm.get("kind", "guide"))}
    faq, sources, sources_intro, checklist, related = [], [], "", None, None
    ctas = {}
    cta_anchors = {}          # place -> якорь врезки (см. :::cta place=mid anchor=)
    used_ids, parts = set(), []
    section_titles, section_ids = [], []

    # Директивы до первого H2 (пролог). Канонично тут стоит ТОЛЬКО
    # :::cta place=compact - см. фразу ниже про anchor=: «у compact и final
    # место в шаблоне жёсткое (начало и конец страницы)». Раньше pre вообще
    # не обходился на директивы - split_sections складывал его строки как
    # есть, а лид-цикл ниже (md_blocks(plines) if k != "directive") молча
    # выбрасывал директивный блок целиком. Итог: :::cta place=compact в
    # начале черновика улетал в никуда без единой ошибки - живая улика
    # lead-magnit-work/guide-kak-sdelat-neyroset/draft.md:40 по решению автора
    # (ключа cta_compact нет в spec.json, 0 вхождений в index.html, а гейт
    # cta зелёный - он не сверял количество). Любая другая директива в
    # прологе (figure/table/pre/faq/related/sources/checklist, и cta с
    # place=mid|final тоже) - брак черновика: их место либо внутри
    # раздела, либо жёстко зашито в другом конце страницы, поэтому громкий
    # fail с именем директивы вместо молчаливой потери контента.
    for kind, blines in md_blocks(pre):
        if kind != "directive":
            continue
        name, attrs, dbody = parse_directive(blines)
        if name != "cta":
            fail("директива :::%s до первого H2: перенеси внутрь раздела "
                 "(в прологе статьи разрешена только :::cta place=compact)" % name)
        if attrs.get("place") != "compact":
            fail("директива :::cta place=%s до первого H2: перенеси внутрь раздела "
                 "(здесь можно только :::cta place=compact - у mid и final своё "
                 "жёсткое место: mid внутри раздела по anchor=, final в конце "
                 "страницы)" % attrs.get("place"))
        place, chtml = render_cta(attrs, dbody, ctx)
        if place in ctas:
            fail("две директивы :::cta place=%s" % place)
        ctas[place] = chtml

    for idx, (title, aid, lines) in enumerate(sections):
        low = re.sub(r"[^\wа-яё ]", "", title.lower()).strip()
        if low in FAQ_HEADINGS:
            faq = render_faq([re.sub(r"^###", "###", x) for x in lines], ctx)
            continue
        if low in SOURCES_HEADINGS:
            txt = [x for x in lines if x.strip()]
            intro = [x for x in txt if not re.match(r"^\s*[-*]\s", x)]
            sources = md_list_items(lines, cfg)
            if intro:
                # «> примечание» перед списком источников встречается в пачке
                # (guide-neyroset-dizayn-interera). Блока цитаты тут быть не
                # может - build_page кладёт intro внутрь <p>, - поэтому маркер
                # снимаем, а текст остаётся текстом. Без этого стрелка уезжала
                # в страницу тем же литералом, что и в теле статьи.
                intro = [QUOTE_RE.sub(r"\1", x.strip()) for x in intro]
                sources_intro = inline(" ".join(x.strip() for x in intro), cfg)
            continue

        sid = aid or slugify(title)
        if sid in used_ids:
            fail("два раздела с одним якорем #%s - задай «{#свой-якорь}»" % sid)
        used_ids.add(sid)

        inner = []
        for kind, blines in md_blocks(lines):
            if kind == "directive":
                name, attrs, dbody = parse_directive(blines)
                if name == "figure":
                    inner.append(render_figure(attrs, dbody, ctx))
                elif name == "table":
                    inner.append(md_table(dbody, attrs.get("hint", TABLE_HINT), cfg,
                                          fit=attrs.get("fit")))
                elif name == "pre":
                    inner.append(listing("\n".join(dbody), attrs.get("own")))
                elif name == "checklist":
                    checklist = render_checklist(dbody, ctx)
                elif name == "faq":
                    faq = render_faq(dbody, ctx)
                elif name == "related":
                    related = render_related(dbody, ctx)
                elif name == "sources":
                    sources, sources_intro = render_sources(attrs, dbody, ctx)
                elif name == "cta":
                    place, chtml = render_cta(attrs, dbody, ctx)
                    if place in ctas:
                        fail("две директивы :::cta place=%s" % place)
                    ctas[place] = chtml
                    if attrs.get("anchor"):
                        if place != "mid":
                            fail("anchor= бывает только у :::cta place=mid: у compact и "
                                 "final место в шаблоне жёсткое (начало и конец страницы)")
                        cta_anchors[place] = attrs["anchor"].strip()
                else:
                    fail("неизвестная директива :::%s (канон: figure, table, pre, "
                         "checklist, faq, related, sources, cta)" % name)
                continue
            # СЛУЖЕБНАЯ H3-МЕТКА ПЕРЕД ДИРЕКТИВОЙ (r14, круг 3, по решению автора): черновик
            # часто маркирует директиву визуальным заголовком - «### Источники
            # {#istochniki}» перед :::sources:::, «### Частые вопросы» перед
            # :::faq::: - но split_sections режет тело только по H2, а render_md_block
            # не умеет H3+, поэтому голая строка падала в inner как есть и текла на
            # страницу буквальным текстом «### Источники {#istochniki}»: сама
            # директива ниже уже кладёт заголовок раздела САМА (SOURCES_TITLE в
            # build_page.py / «### Вопрос» внутри render_faq), метка в теле черновика
            # нужна ТОЛЬКО черновик-гейту structure-check (сканит сырой текст на
            # «##/### Источники»), собранной странице она не нужна и не должна там
            # быть. Живая улика: guide-neyroset-ozhivit-foto/index.html:1735
            # `<p>### Источники {#istochniki}</p>` последним абзацем раздела
            # chto-menyaet - и тот же паттерн живьём тёк ещё в 7 черновиках волны
            # (guide-claude-code-windows, guide-lokalnye-neyroseti,
            # guide-mobilnoe-prilozhenie, guide-klyuchi-nvidia, guide-kit,
            # guide-opensource-zamena-saas, guide-terminal - у всех то же «### Источники
            # {#istochniki}» перед :::sources:::). Метка = ОДНА голая строка «#{2,6}
            # Текст» без прочего содержимого в блоке, и текст - ровно зарезервированное
            # слово (FAQ_HEADINGS/SOURCES_HEADINGS): такую строку молча дропаем, любой
            # другой заголовок (в т.ч. с прилагательным, «Что делать, если источник
            # недоступен») остаётся обычным текстом.
            if (kind == "md" and len(blines) == 1
                    and re.match(r"^#{2,6}\s+\S", blines[0].strip())):
                htext = re.sub(r"^#{2,6}\s+", "", blines[0].strip())
                htext = ANCHOR_RE.sub("", htext).strip()
                hlow = re.sub(r"[^\wа-яё ]", "", htext.lower()).strip()
                if hlow in FAQ_HEADINGS or hlow in SOURCES_HEADINGS:
                    continue
            inner.append(render_md_block(blines, cfg))
        for f in figs_by_section.get(idx, []):
            inner.append(figure_from_manifest(f, ctx))
        if not inner:
            fail("раздел «%s» пустой" % title)
        indented = "\n  ".join(b.replace("\n", "\n  ") if "<pre" not in b else b
                               for b in inner)
        section_titles.append(title.strip())
        section_ids.append(sid)
        parts.append('<section id="%s">\n  <h2>%s</h2>\n  %s\n</section>'
                     % (sid, inline(title, cfg), indented))

    # Пролог до первого H2 - лид статьи (front-matter «lead:» перебивает его).
    # Абзацы лида НЕ склеиваются: раньше пролог сшивался в одну строку через
    # " ".join, и лид из двух абзацев молча превращался в один - на живой пачке
    # это ровно тот случай, где вводка отделена от «ниже разложено» (2 статьи из
    # 13). Пролог идёт через тот же md_blocks, что и тело статьи.
    lead_src = str(fm.get("lead") or "").strip()
    plines = (lead_src.split("\n") if lead_src
              else [x for x in pre if not x.strip().startswith("#")])
    lead_blocks = [render_md_block(l, cfg) for k, l in md_blocks(plines) if k != "directive"]

    site = cfg["site"]
    canonical = site + str(fm.get("canonical_path") or ("/%s/" % slug))
    spec.update({
        "title": str(fm["title"]),
        "description": str(fm["description"]),
        "canonical": canonical,
        "og_image": str(fm.get("og_image") or
                        "%s/%s/%s/%s-og.jpg" % (site, slug, ctx["assets_dir"], assets_base)),
        "date_published": str(fm["date_published"]),
        "date_modified": str(fm.get("date_modified") or datetime.date.today().isoformat()),
        "nav_cta_url": "{{cta_url}}",
        # 🔴 Хаб гайдов - /blog/, а НЕ /blog.html (по решению автора, переезд на чистые
        # адреса): /blog.html отдаёт 301, видимая крошка «Гайды» вела читателя и
        # поисковик через переадресацию. Парный дефолт в schema-generator.py.
        # 🔴 ПОСЛЕДНЯЯ КРОШКА НАЗЫВАЕТСЯ ВИДИМЫМ ЗАГОЛОВКОМ (H1), А НЕ `title`
        # (по решению автора, круг 3, записи R20/R29/R69). До этого дефолт брал `title`.
        # Пока страница новая, title и h1 совпадают, и разницы не видно. После
        # CTR-ретайтла они РАСХОДЯТСЯ намеренно: `title` это строка сниппета, а
        # `h1` остаётся прежним по канону исполнителя («H1 не меняешь ни на одной
        # странице волны»). Живой прод после ретайтла показывает в дорожке ИМЕННО
        # h1, а пересборка из источника подставляла сюда новый title - и судья
        # «прод против источника» краснел на КАЖДОЙ ретайтленной странице
        # (`prod_source_verify`, 8 из 8 прогонов круга 2). Разница не техническая:
        # пересборка молча переписала бы человеку видимую дорожку.
        # Крошка - ВИДИМЫЙ элемент, значит и называется она видимым заголовком.
        # Из этого же значения собирается `BreadcrumbList` (`build_page.build_jsonld`
        # берёт имена ОТСЮДА), поэтому разметка и видимое остаются одним текстом.
        "breadcrumbs": fm.get("breadcrumbs") or [
            {"name": "Главная", "href": "/"},
            {"name": "Гайды", "href": "/blog/"},
            {"name": str(fm.get("h1") or fm["title"])},
        ],
        "h1": str(fm["h1"]),
        "content": "\n\n".join(parts),
    })
    if fm.get("og_image_alt"):
        spec["og_image_alt"] = str(fm["og_image_alt"])
    if fm.get("date_published"):
        # префикс из белого списка schema-generator.DATE_SOURCE_PREFIXES
        spec["date_published_source"] = str(
            fm.get("date_published_source")
            or "build_page.spec.date_published: дата из front-matter draft.md")
    if fm.get("keywords"):
        spec["keywords"] = fm["keywords"]
    if fm.get("articleSection"):
        spec["articleSection"] = str(fm["articleSection"])
    if fm.get("eyebrow"):
        spec["eyebrow"] = str(fm["eyebrow"])
    if lead_blocks:
        spec["lead_html"] = "\n".join("      " + b for b in lead_blocks)
    if fm.get("quick_answer"):
        spec["quick_answer"] = "        <p>%s</p>" % inline(str(fm["quick_answer"]), cfg)
    hero = fm.get("hero")
    if hero:
        check_alt(hero.get("alt"), "hero")
        h = dict(hero)
        if h.get("slug"):
            h["webp"] = "%s/%s-%s.webp" % (ctx["assets_dir"], assets_base, h["slug"])
            h["jpg"] = "%s/%s-%s.%s" % (ctx["assets_dir"], assets_base, h["slug"],
                                        h.get("ext", "jpg"))
            # реальные пиксели монтированного hero-файла бьют шаблонные w/h
            # front-matter - тот же класс дефекта, что и у :::figure, см.
            # real_image_size()
            real = real_image_size(os.path.join(ctx["draft_dir"], h["jpg"]))
            if real and (str(real[0]), str(real[1])) != (str(h.get("w")), str(h.get("h"))):
                print("article_build: hero slug=%s - заявлено %sx%s, реальный файл "
                      "%sx%s, беру реальные пиксели"
                      % (hero["slug"], h.get("w"), h.get("h"), real[0], real[1]),
                      file=sys.stderr)
                h["w"], h["h"] = real
            h.pop("slug", None)
            h.pop("ext", None)
        spec["hero"] = h
    if checklist:
        spec["checklist"] = checklist
    if faq:
        spec["faq"] = faq
        spec["faq_title"] = str(fm.get("faq_title", "Частые вопросы"))
    if sources:
        spec["sources"] = sources
        if sources_intro or fm.get("sources_intro"):
            spec["sources_intro"] = sources_intro or str(fm["sources_intro"])
    author = cfg.get("author_card") or fm.get("author")
    if author:
        spec["author"] = author
    if related:
        spec["related"] = related
        spec["related_title"] = str(fm.get("related_title", "Читайте также"))
    if fm.get("steps") is not None:
        spec["steps"] = parse_steps(fm["steps"], os.path.basename(draft_path))
    if ctas.get("compact"):
        spec["cta_compact"] = ctas["compact"]
    if ctas.get("mid"):
        spec["cta_mid"] = ctas["mid"]
        if cta_anchors.get("mid"):
            # якорь врезки. Ловим опечатку ЗДЕСЬ, где под рукой список разделов:
            # build_page уронит сборку тем же законом, но без имён-кандидатов
            a = cta_anchors["mid"]
            if a not in section_titles and a not in section_ids:
                fail("anchor=\"%s\" не совпал ни с одним разделом черновика. "
                     "Якорем служит ТЕКСТ заголовка «## …» либо его «{#идентификатор}». "
                     "Разделы статьи: %s"
                     % (a, " · ".join("«%s»%s" % (t, (" {#%s}" % i) if i else "")
                                      for t, i in zip(section_titles, section_ids))))
            spec["cta_mid_anchor"] = a
    if ctas.get("final"):
        spec["cta_final"] = ctas["final"]
    if fm.get("toc_labels"):
        spec["toc_labels"] = fm["toc_labels"]
    if fm.get("share") is not None:
        spec["share"] = bool(fm["share"])
    if fm.get("extra_css_file"):
        p = os.path.join(os.path.dirname(os.path.abspath(draft_path)),
                         str(fm["extra_css_file"]))
        if not os.path.exists(p):
            fail("extra_css_file не найден: %s" % p)
        spec["extra_css"] = open(p, encoding="utf-8").read()

    tokens = config_tokens(cfg, slug,
                           utm_source=str(fm.get("utm_source", "guide")),
                           utm_content=fm.get("utm_content"),
                           codeword=str(fm.get("codeword", "")))
    blob = json.dumps(spec, ensure_ascii=False)
    gate_no_codeword_in_text(blob, os.path.basename(draft_path))
    spec = substitute(spec, tokens)
    gate_spec_specifics_from_config(spec, cfg, tokens)
    # тот же список литералов по СОБРАННОЙ спеке: черновик мог прийти чистым, а
    # литерал приехать подстановкой (например {{target_url}} в теле статьи, пока
    # адрес оффера - старый лендинг). Спека и есть содержимое будущей страницы
    gate_no_forbidden_literals(json.dumps(spec, ensure_ascii=False),
                               cfg, "собранной спеке %s" % os.path.basename(draft_path))
    gate_no_codeword_in_text(json.dumps(spec, ensure_ascii=False),
                             "собранной спеке %s" % os.path.basename(draft_path))
    return spec


# ── гейт код-слова: в тексте статьи его НЕТ ВООБЩЕ ───────────────────────────
#
# ЗАЧЕМ (решение владельца). Статью читает человек из Яндекса и
# Google. Он не видел ни карусели, ни рилза, слова не знает - и упирается в
# «Код-слово этой статьи - СВОД. Если ты пришёл по нему…» ровно там, где решает,
# жать кнопку или закрыть вкладку. Пользы блок не нёс: вход открывает КНОПКА,
# слово никуда не вводится. Атрибуция карусель→статья живёт в реестрах
# (CAROUSEL-REGISTRY.md, codewords.py) и в front-matter «codeword:» - это
# метаданные, они на страницу не выводятся. До этой правки сборщик дописывал
# блок САМ в каждый финальный CTA, поэтому одной прозы канона мало: правило
# держит код.
#
# ЧЕМ ЛОВИМ. Три подстановки-источника ({{codeword}} / {{codeword_span}} /
# {{codeword_block}}), полный открывающий тег `<span class="kw">` (внутри
# листинга он невозможен: `<` всегда уезжает в `&lt;`, поэтому статья про
# подсветку синтаксиса гейт не красит) и сами зачины блока в прозе - статья
# вправе написать свой абзац руками, обойдя подстановки.
CODEWORD_MARK = '<span class="kw">'
CODEWORD_TOKENS = ("{{codeword}}", "{{codeword_span}}", "{{codeword_block}}")
# зачины блока в прозе: писатель может собрать тот же абзац руками
CODEWORD_PHRASES = ("код-слово этой статьи", "код-слово этого разбора",
                    "код-слово статьи", "слово для входа",
                    "пришёл из карусели за", "пришел из карусели за")
# «…по слову ПАМЯТКА», «за словом СВОД», «Слово ДУША привело» - слово КАПСОМ
# рядом с приглашением. Голое «по слову» без капса не ловим: это нормальная
# русская речь («поиск по слову», «судить по слову»), гейт не должен её валить
CODEWORD_PROSE_RE = re.compile(
    r"(?:[Пп]о|[Зз]а|[Пп]од)\s+слов\w*\s+[«\"']?[А-ЯЁ]{3,}|"
    r"[Сс]лов[оа]\s+[«\"']?[А-ЯЁ]{3,}[»\"']?\s+привел|"
    r"[Сс]кажи\s+[«\"']?[А-ЯЁ]{3,}", re.U)


def gate_no_codeword_in_text(blob, where):
    """Ни подстановок, ни разметки, ни прозы про код-слово в тексте статьи."""
    низ = blob.lower()
    найдено = [t for t in CODEWORD_TOKENS if t in blob]
    if CODEWORD_MARK in blob:
        найдено.append(CODEWORD_MARK)
    найдено += ["«%s…»" % p.strip() for p in CODEWORD_PHRASES if p in низ]
    найдено += ["«%s…»" % m.group(0) for m in CODEWORD_PROSE_RE.finditer(blob)]
    if найдено:
        fail("код-слово в тексте (%s): %s. Блок код-слова убран из статей "
             "по решению автора - читатель приходит из поиска, слова он не знает, а вход "
             "открывает кнопка. Слово оставь в front-matter «codeword:» "
             "(метаданные атрибуции) и в реестрах, из текста убери"
             % (where, " · ".join(dict.fromkeys(найдено))))


# ── selftest ─────────────────────────────────────────────────────────────────

_CODE_INNER_RE = re.compile(r"<code\b[^>]*>(.*?)</code\s*>", re.S | re.I)
_RAW_TAG_RE = re.compile(r"<\s*[a-zA-Z!/]")


def raw_tag_in_listing(body):
    """Тот же признак, что держит КАНОН 23 в build_page: сырой тег в листинге."""
    for m in _CODE_INNER_RE.finditer(body):
        if _RAW_TAG_RE.search(m.group(1)):
            return m.group(1)[:80]
    return None


def _run_build_page(spec_path, out_path):
    p = subprocess.run([sys.executable, BUILD_PAGE, spec_path, "-o", out_path],
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


# ── песочница CTA для selftest ───────────────────────────────────────────────
#
# Боевая карта инвайтов знает БОЕВЫЕ слаги, слага фикстуры в ней нет и быть не
# должно. Поэтому selftest подменяет карту СВОЕЙ (tests/fixture-invites-map.json)
# двумя каналами сразу: в памяти - для прямых вызовов build_spec, файлом-копией
# config.md - для тех тестов, что зовут article_build.py отдельным процессом.
# Иначе первый же прогон на машине с картой падал бы «слага нет в карте», и
# selftest мерил бы конфиг автора вместо контракта сборщика.

FIXTURE_INVITES = os.path.join(TESTS, "fixture-invites-map.json")
# синтетические литералы на случай, если у автора cta.forbidden_literals пуст:
# негативные тесты обязаны идти всегда, а не «пропускаться, раз не настроено»
FALLBACK_FORBIDDEN = ["/staryy-lending-offera/", "chuzhoy_bot_voronki"]


def _selftest_cfg(config_path):
    """(cfg с фикстурной картой, cfg без карты, путь config-копии для подпроцессов)."""
    live = load_config(config_path)
    with_map = dict(live)
    with_map["invites_map"] = FIXTURE_INVITES
    with_map["invites"] = load_invites_map(FIXTURE_INVITES)
    if not with_map.get("forbidden_literals"):
        with_map["forbidden_literals"] = list(FALLBACK_FORBIDDEN)
    # ветка «карты нет» проверяет ровно ОДНО: старый маршрут CTA (target_url +
    # utm) цел. Список литералов ей отключён намеренно: у автора, который уже
    # переехал на инвайты, прошлый адрес оффера стоит и в target_url, и в
    # запрещённых литералах разом - это не противоречие конфига, а желаемое
    # поведение (снял карту - сборка КРИЧИТ, а не тихо возвращает лендинг).
    # Сам гейт литералов проверяют негативы-20/21/22 ниже
    no_map = dict(live)
    no_map["invites_map"], no_map["invites"] = "", None
    no_map["forbidden_literals"] = []
    return with_map, no_map


def _selftest_config_file(src_path, dst_dir):
    """Копия config.md автора, где карта инвайтов заменена фикстурной.

    Ключа нет (машина ученика) - копия равна оригиналу, и подпроцесс идёт
    прежним маршрутом target_url + utm: тест остаётся зелёным и там.
    """
    src = os.path.expanduser(src_path or os.environ.get("LEAD_MAGNIT_CONFIG")
                             or DEFAULT_CONFIG)
    raw = open(src, encoding="utf-8").read()
    raw = re.sub(r"(?m)^(\s*invites_map:)[^\n]*$",
                 lambda m: "%s %s" % (m.group(1), FIXTURE_INVITES), raw, count=1)
    dst = os.path.join(dst_dir, "config-selftest.md")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(raw)
    return dst


def selftest(config_path=None):
    checks, failed = [], 0

    def ok(name, cond, detail=""):
        nonlocal failed
        checks.append(("OK  " if cond else "FAIL", name, detail))
        if not cond:
            failed += 1

    cfg, cfg_nomap = _selftest_cfg(config_path)
    good = os.path.join(TESTS, "fixture-draft.md")
    bad = os.path.join(TESTS, "fixture-draft-hardcoded-domain.md")
    for p in (good, bad, FIXTURE_INVITES):
        if not os.path.exists(p):
            fail("нет фикстуры %s" % p)

    tmp = tempfile.mkdtemp(prefix="article_build_selftest_")
    try:
        # подпроцессы идут по КОПИИ конфига автора с фикстурной картой инвайтов
        sub_cfg = _selftest_config_file(config_path, tmp)
        # ── позитив ──
        spec = build_spec(open(good, encoding="utf-8").read(), cfg, good)
        sp = os.path.join(tmp, "spec.json")
        json.dump(spec, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        blob = json.dumps(spec, ensure_ascii=False)

        ok("листинг экранирован (нет сырого тега внутри <code>)",
           not raw_tag_in_listing(spec["content"]))
        ok("&lt; в листинге есть (директива :::pre отработала)", "&lt;!DOCTYPE" in blob)
        ok("data-own=measure проставлен", 'data-own=\\"measure\\"' in blob
           or 'data-own="measure"' in spec["content"])
        ok("таблица в канон-обёртке tablebox/tablewrap/tablehint",
           'class="tablebox"' in spec["content"] and 'class="tablehint"' in spec["content"])
        # fit=narrow (правка волны r12, по решению автора): атрибут приехал в md_table
        # БЕЗ своего теста - дефект нашёл скептик r3 по guide-obrabotka-foto.
        # Держим ОБЕ ветки, каждую своей проверкой: позитив - с атрибутом
        # приезжает класс tablefit и инлайновое снятие min-width (иначе на 390px
        # третья колонка уезжает за экран, дефект В-Н2); негатив - без атрибута
        # разметка ПРЕЖНЯЯ байт в байт, то есть соседи волны от правки движка не
        # шевелятся. Одной склеенной единицей их держать нельзя: провал любой
        # ветки печатался бы одинаково, а лечится он в разных местах md_table.
        _fit_rows = ["| Что сделать | Куда идти | Цена |",
                     "|---|---|---|",
                     "| Убрать фон | Erase.bg | 0 ₽ |"]
        _tbl_plain = md_table(list(_fit_rows), TABLE_HINT, cfg)
        _tbl_fit = md_table(list(_fit_rows), "", cfg, fit="narrow")
        _fit_pos = ('class="tablebox tablefit"' in _tbl_fit
                    and 'style="min-width:0;width:100%"' in _tbl_fit
                    and 'class="tablehint"' not in _tbl_fit)
        _fit_neg = ('<div class="tablebox">' in _tbl_plain
                    and "tablefit" not in _tbl_plain
                    and "min-width:0" not in _tbl_plain
                    and 'class="tablehint"' in _tbl_plain)
        ok("fit=narrow ПОЗИТИВ: класс tablefit, инлайновое min-width:0, подписи про скролл нет",
           _fit_pos, _tbl_fit[:120])
        ok("fit=narrow НЕГАТИВ: без атрибута обёртка tablebox прежняя, ни tablefit, ни min-width",
           _fit_neg, _tbl_plain[:120])
        ok("фигура из :::figure собрана", 'srcset="assets/fixture-shema.webp"' in spec["content"])
        ok("фигура из манифеста figures подвязана подстрокой к «Шаг 2.»",
           'fixture-manifest.webp' in spec["content"]
           and spec["content"].index("fixture-manifest.webp") > spec["content"].index('id="shag-2"'))
        ok("чек-лист поднят в spec.checklist", bool(spec.get("checklist"))
           and len(spec["checklist"]["items"]) == 3)
        ok("FAQ поднят из markdown-раздела", len(spec.get("faq") or []) == 2)
        ok("источники подняты из markdown-раздела", len(spec.get("sources") or []) == 2)
        ok("related собран", len(spec.get("related") or []) == 1)
        ok("явный якорь {#svoy-yakor} сохранён", 'id="svoy-yakor"' in spec["content"])
        ok("подстановка домена приехала из config", cfg["site"] in spec["canonical"])

        # ── ПОДЗАГОЛОВОК ВНУТРИ РАЗДЕЛА (по решению автора) ──────────────────────────
        # Класс дефекта: «### Шаг 1. Одна строка запускает установку {#shag-1}»
        # уезжал на живую страницу буквальным текстом внутри <p> - читатель видел
        # решётки и фигурные скобки. Тест держит ОБА конца: подзаголовок с
        # содержанием рисуется тегом, служебная метка перед директивой по-прежнему
        # молча дропается, и НИ В ОДНОМ случае решётка не остаётся в тексте.
        h3_blocks = md_blocks(["### Шаг 1. Одна строка {#shag-1}",
                               "Абзац сразу под заголовком, без пустой строки",
                               "",
                               "#### Уровень четыре",
                               "",
                               "###### Уровень шесть опускается до h4"])
        h3_html = "\n".join(render_md_block(b, cfg) for k, b in h3_blocks)
        ok("подзаголовок ### стал <h3> с якорем из {#…}",
           '<h3 id="shag-1">Шаг 1. Одна строка</h3>' in h3_html, h3_html[:160])
        ok("абзац, приклеенный к подзаголовку без пустой строки, не съеден",
           "<p>Абзац сразу под заголовком, без пустой строки</p>" in h3_html)
        ok("#### стал <h4>", "<h4>Уровень четыре</h4>" in h3_html)
        ok("###### опускается до h4 (h5/h6 в tokens.css не оформлены)",
           "<h4>Уровень шесть опускается до h4</h4>" in h3_html)
        ok("после разбора в HTML не осталось ни одной сырой решётки",
           "<p>#" not in h3_html and "{#" not in h3_html, h3_html[:200])
        # end-to-end по фикстуре: тот же черновик + подзаголовок в разделе
        h3_draft = open(good, encoding="utf-8").read().replace(
            "- пункт маркированного списка",
            "### Подзаголовок раздела {#podzagolovok}\n\n"
            "- пункт маркированного списка", 1)
        h3_spec = build_spec(h3_draft, cfg, good)
        ok("сборка целиком: подзаголовок раздела вышел тегом, а не текстом",
           '<h3 id="podzagolovok">Подзаголовок раздела</h3>' in h3_spec["content"]
           and "<p>### " not in h3_spec["content"])
        # служебная метка перед директивой - прежнее поведение (дроп, r14)
        lbl_draft = open(good, encoding="utf-8").read().replace(
            ":::related", "### Источники {#istochniki}\n\n:::related", 1)
        lbl_spec = build_spec(lbl_draft, cfg, good)
        ok("служебная метка «### Источники» перед директивой по-прежнему дропается",
           "Источники {#istochniki}" not in lbl_spec["content"]
           and "<h3 id=\"istochniki\">" not in lbl_spec["content"])
        # ── адрес CTA: БЕЛЫЙ СПИСОК, а не один зашитый адрес ──────────────────
        # До этой редакции ассерт требовал в CTA ровно target_url - и первый же
        # переезд канона (CTA в закрытый канал именным инвайтом) ронял selftest
        # на ровном месте. Закон теперь один и тот же у сборщика и у гейта:
        # адрес CTA = target_url ЛИБО любой из cta.accepted_prefixes.
        def cta_addr_ok(url):
            if not url:
                return False
            base = cfg["target_url"].split("?")[0]
            return (base and base in url) or any(p in url
                                                 for p in cfg.get("accepted_prefixes") or [])

        fx_invite = load_invites_map(FIXTURE_INVITES)["guide-fixture"]
        ok("cta_url - адрес из белого списка (target_url или cta.accepted_prefixes)",
           cta_addr_ok(spec["nav_cta_url"]), spec["nav_cta_url"])
        ok("карта инвайтов задана - cta_url = ИМЕННОЙ инвайт слага статьи",
           spec["nav_cta_url"] == fx_invite, spec["nav_cta_url"])
        ok("к инвайту t.me не приклеен utm-хвост",
           "utm_source=" not in spec["nav_cta_url"], spec["nav_cta_url"])
        # решение владельца: финальный CTA закрывает статью кнопкой,
        # блока код-слова в нём НЕТ - до правки эти же три проверки требовали
        # обратного (сборщик дописывал абзац сам в каждую статью)
        ok("финальный CTA НЕ несёт код-слова статьи",
           "ФИКСТУРА" not in (spec.get("cta_final") or ""),
           (spec.get("cta_final") or "")[-200:])
        ok("автодописи блока код-слова нет (span.kw в финальном CTA отсутствует)",
           'class="kw"' not in (spec.get("cta_final") or ""))
        ok("зачина «Код-слово этой статьи» в финальном CTA нет",
           "Код-слово этой статьи" not in (spec.get("cta_final") or ""),
           (spec.get("cta_final") or "")[-200:])
        ok("кнопка финального CTA ведёт на адрес из белого списка",
           'class="btn-cta"' in (spec.get("cta_final") or "")
           and cta_addr_ok(re.search(r'class="btn-cta" href="([^"]+)"',
                                     spec.get("cta_final") or "").group(1)
                           if re.search(r'class="btn-cta" href="([^"]+)"',
                                        spec.get("cta_final") or "") else ""),
           (spec.get("cta_final") or "")[-160:])
        ok("кнопка финального CTA = тот же инвайт, что и nav_cta_url",
           fx_invite in (spec.get("cta_final") or ""))

        # ── без карты инвайтов (машина ученика) поведение ПРЕЖНЕЕ ─────────────
        spec_nm = build_spec(open(good, encoding="utf-8").read(), cfg_nomap, good)
        ok("без cta.invites_map cta_url = адрес оффера с utm (старое поведение цело)",
           cfg_nomap["target_url"].split("?")[0] in spec_nm["nav_cta_url"]
           and "utm_source=" in spec_nm["nav_cta_url"], spec_nm["nav_cta_url"])

        # ── порядок ключей карты: полный → guide- → без guide- → 25 символов ──
        ok("ключи слага пробуются в каноническом порядке",
           invite_keys("guide-tema") == ["guide-tema", "tema"]
           and invite_keys("tema-bez-prefiksa")[:2] == ["tema-bez-prefiksa",
                                                        "guide-tema-bez-prefiksa"]
           and invite_keys("guide-obrezannyy-do-25-simvolov-hvost")[-1]
           == "obrezannyy-do-25-simvolov",
           str(invite_keys("guide-obrezannyy-do-25-simvolov-hvost")))
        ok("инвайт находится по слагу БЕЗ префикса guide-",
           invite_for_slug(cfg, "guide-bez-prefiksa-guide")
           == "https://t.me/+FXinvite000000003")
        ok("инвайт находится по слагу, обрезанному до 25 символов",
           invite_for_slug(cfg, "guide-obrezannyy-do-25-simvolov-hvost")
           == "https://t.me/+FXinvite000000004")
        ok("кнопка промо в теле (place=compact) отрисована, а не съедена как текст",
           'class="btn-cta"' in (spec.get("cta_compact") or "")
           and "button:" not in (spec.get("cta_compact") or ""))

        # ── р9 (по решению автора): директивы в ПРОЛОГЕ (до первого H2) ──────────────
        # живая улика - lead-magnit-work/guide-kak-sdelat-neyroset/draft.md:40,
        # :::cta place=compact в прологе молча выбрасывался (split_sections
        # относила пролог к «pre», а pre на директивы вообще не обходился).
        # Позитив: compact - КАНОННОЕ место директивы (см. render_cta: «у
        # compact и final место в шаблоне жёсткое, начало и конец страницы»),
        # переносим её из «## Ссылки и промо» в пролог и требуем, чтобы она
        # всё равно доехала до spec.cta_compact.
        raw_р9 = open(good, encoding="utf-8").read()
        compact_in_section = (
            "2. второй пункт нумерованного списка\n\n"
            ":::cta place=compact\n"
            "Промо-врезка в теле статьи: заголовок промо опускается до h3 и в "
            "оглавление не идёт.\n"
            "button: Забрать доступ\n"
            ":::\n\n"
            "## Что дальше")
        prolog_marker = ("Пролог до первого H2 уезжает в лид статьи, если "
                         "front-matter не задал поле lead отдельно.\n\n"
                         "## Короткий ответ")
        assert compact_in_section in raw_р9 and prolog_marker in raw_р9, (
            "фикстура fixture-draft.md изменилась - обнови целевые строки р9-теста")
        raw_pre_compact = (
            raw_р9.replace(compact_in_section, "2. второй пункт нумерованного списка\n\n"
                                               "## Что дальше", 1)
               .replace(prolog_marker,
                        "Пролог до первого H2 уезжает в лид статьи, если "
                        "front-matter не задал поле lead отдельно.\n\n"
                        ":::cta place=compact\n"
                        "Промо в прологе - тест р9: канонное место compact - "
                        "начало страницы.\n"
                        "button: Забрать доступ\n"
                        ":::\n\n"
                        "## Короткий ответ", 1))
        spec_pre_compact = build_spec(raw_pre_compact, cfg, good)
        cc = spec_pre_compact.get("cta_compact") or ""
        ok("р9 позитив: :::cta place=compact ДО первого H2 доезжает до spec.cta_compact",
           'class="btn-cta"' in cc and "Забрать доступ" in cc, cc[:160])
        ok("р9 позитив: секция «Ссылки и промо» без compact больше не падает "
           "«две директивы cta place=compact»",
           "svoy-yakor" in spec_pre_compact["content"])

        # Негатив: ЛЮБАЯ другая директива в прологе (не :::cta place=compact) -
        # брак черновика, громкий fail с именем директивы, а не молчаливая потеря
        raw_bad_figure = raw_р9.replace(
            prolog_marker,
            "Пролог до первого H2 уезжает в лид статьи, если front-matter не "
            "задал поле lead отдельно.\n\n"
            ":::figure slug=probniy w=100 h=100\n"
            "alt: тестовая фигура в прологе\n"
            ":::\n\n"
            "## Короткий ответ", 1)
        try:
            build_spec(raw_bad_figure, cfg, good)
            ok("р9 негатив: :::figure ДО первого H2 роняет сборку", False,
               "сборка НЕ упала")
        except BuildError as e:
            ok("р9 негатив: :::figure ДО первого H2 роняет сборку",
               ":::figure" in str(e) and "до первого H2" in str(e), str(e)[:160])

        # Негатив: :::cta place=mid в прологе - тоже брак (её место НЕ тут,
        # anchor= работает только внутри раздела)
        raw_bad_mid = raw_р9.replace(
            prolog_marker,
            "Пролог до первого H2 уезжает в лид статьи, если front-matter не "
            "задал поле lead отдельно.\n\n"
            ":::cta place=mid\n"
            "Врезка не на своём месте.\n"
            "button: Мимо\n"
            ":::\n\n"
            "## Короткий ответ", 1)
        try:
            build_spec(raw_bad_mid, cfg, good)
            ok("р9 негатив: :::cta place=mid ДО первого H2 роняет сборку", False,
               "сборка НЕ упала")
        except BuildError as e:
            ok("р9 негатив: :::cta place=mid ДО первого H2 роняет сборку",
               "place=mid" in str(e) and "до первого H2" in str(e), str(e)[:160])

        ok("FAQ/Источники не остались разделами тела",
           "Частые вопросы" not in spec["content"] and "Источники" not in spec["content"])
        ok("steps не заданы во фикстуре - spec.json без поля steps (HowTo опционален)",
           "steps" not in spec)

        rc, out = _run_build_page(sp, os.path.join(tmp, "index.html"))
        ok("build_page собрал страницу из спеки", rc == 0, out.strip()[-300:])
        page = ""
        if rc == 0:
            page = open(os.path.join(tmp, "index.html"), encoding="utf-8").read()
            n_h2 = len(re.findall(r"<h2\b", page))
            n_num = len(re.findall(r'<h2[^>]*class="[^"]*\bnum\b', page))
            aside = re.search(r'<aside class="toc-desktop".*?</aside>', page, re.S)
            n_toc = len(re.findall(r'<li><a href="#', aside.group(0) if aside else ""))
            ok("КАНОН 13: num у всех 4 разделов тела (h2 всего %d)" % n_h2, n_num == 4,
               "num=%d" % n_num)
            ok("TOC = 4 раздела + чек-лист + FAQ = 6", n_toc == 6, "toc=%d" % n_toc)
            ok("JSON-LD валиден", bool(re.search(r'application/ld\+json', page)))
            ok("без steps узел HowTo в JSON-LD не появляется",
               '"@type": "HowTo"' not in page)

        # ── негатив 1: домен захардкожен в черновике ──
        # маркеры фикстуры подменяются ЖИВЫМИ значениями config: сам файл
        # фикстуры не содержит ни одного чужого домена, тест работает у любого
        bad_raw = (open(bad, encoding="utf-8").read()
                   .replace("__DOMAIN__", cfg["domain"])
                   .replace("__TARGET_PATH__", cfg["target_path"]))
        try:
            build_spec(bad_raw, cfg, bad)
            ok("негатив: черновик с литералом домена падает", False, "сборка НЕ упала")
        except BuildError as e:
            msg = str(e)
            ok("негатив: черновик с литералом домена падает", True)
            ok("негатив: в тексте отказа есть подсказка про подстановку",
               "{{cta_url}}" in msg and "config.md" in msg, msg[:160])

        # ── негатив 2: сырой тег в :::pre всё равно экранируется ──
        raw = open(good, encoding="utf-8").read()
        s2 = build_spec(raw, cfg, good)
        ok("негатив-2: сырой тег из ```-забора экранирован, а не уехал разметкой",
           not raw_tag_in_listing(s2["content"]) and "&lt;style&gt;" in s2["content"])

        # ── негатив 3: неизвестная директива ──
        try:
            build_spec(raw.replace(":::pre own=measure", ":::nesuschestvuet"), cfg, good)
            ok("негатив-3: неизвестная директива падает", False)
        except BuildError as e:
            ok("негатив-3: неизвестная директива падает", "неизвестная директива" in str(e))

        # ── негатив 4: alt вне вилки 50-125 ──
        try:
            build_spec(raw.replace("alt: Схема фикстуры: три шага сборки страницы из "
                                   "черновика в спеку и в готовую страницу",
                                   "alt: коротко"), cfg, good)
            ok("негатив-4: короткий alt падает", False)
        except BuildError as e:
            ok("негатив-4: короткий alt падает", "вилка канона 50-125" in str(e))

        # ── негатив 5: фигура манифеста без совпадения заголовка ──
        try:
            build_spec(raw.replace('match: "Шаг 2."', 'match: "Такого заголовка нет"'),
                       cfg, good)
            ok("негатив-5: figures без совпадения падает", False)
        except BuildError as e:
            ok("негатив-5: figures без совпадения падает", "не нашлось ни в одном" in str(e))

        # ── негатив 5б: легаси-черновик чужой схемы (нет маркера engine) ──
        try:
            build_spec(raw.replace("engine: article_build\n", "", 1), cfg, good)
            ok("негатив-5б: черновик без маркера engine падает", False)
        except BuildError as e:
            ok("негатив-5б: черновик без маркера engine падает",
               "engine: article_build" in str(e) and "архив" in str(e))

        # ── негатив 6: промо без кнопки = промо без ссылки на оффер ──
        try:
            build_spec(raw.replace("button: Забрать путёвку", "Забрать путёвку"), cfg, good)
            ok("негатив-6: :::cta без button падает", False)
        except BuildError as e:
            ok("негатив-6: :::cta без button падает", "без ссылки на оффер" in str(e))

        # ── негатив 7: alt карточки related вне вилки ──
        try:
            build_spec(raw.replace(
                "alt: Превью статьи про сборку сайта: лендинг одной командой "
                "в терминальном агенте", "alt: превью"), cfg, good)
            ok("негатив-7: короткий alt в :::related падает", False)
        except BuildError as e:
            ok("негатив-7: короткий alt в :::related падает", ":::related" in str(e))

        # ── цитата «> текст» -> <blockquote> (класс закрыт по решению автора) ──────
        # До фикса «>» был обычным символом абзаца: в собранной странице стояло
        # «<p>> «цитата» > - Автор</p>» - стрелка перед цитатой и вторая перед
        # подписью. Якорь вставки один на все кейсы - абзац в «Шаг 2.».
        QA = "Ниже к этому разделу подвязана фигура"

        def with_md(md):
            return build_spec(raw.replace(QA, md + "\n\n" + QA), cfg, good)

        one = with_md("> «Одна строка цитаты без подписи»")["content"]
        ok("цитата: одиночная строка «>» стала <blockquote> с одним <p>",
           "<blockquote>" in one and "<p>«Одна строка цитаты без подписи»</p>" in one
           and "<cite>" not in one and ">> " not in one,
           re.search(r"<blockquote>.*?</blockquote>", one, re.S).group(0)[:160]
           if "<blockquote>" in one else one[:160])
        ok("цитата: стрелка «>» не осталась в тексте страницы",
           "<p>&gt;" not in one and "<p>> " not in one)

        many = with_md("> Первая строка длинной цитаты,\n"
                       "> вторая строка той же мысли.\n"
                       ">\n"
                       "> Второй абзац цитаты.\n"
                       "> - Автор источника, издание")["content"]
        block = re.search(r"<blockquote>.*?</blockquote>", many, re.S)
        block = block.group(0) if block else ""
        ok("цитата: многострочная склеилась в абзац, пустая «>» разделила абзацы",
           block.count("<p>") == 2
           and "Первая строка длинной цитаты, вторая строка той же мысли." in block,
           block[:200])
        ok("цитата: подпись с дефиса уехала в <cite>, а не в текст",
           "<cite>Автор источника, издание</cite>" in block
           and "- Автор источника" not in block, block[-160:])

        lnk = with_md("> «Цитата со [ссылкой внутри](https://example.org/quote)»\n"
                      "> - Автор, [раздел Memory](https://example.org/memory)")["content"]
        ok("цитата: markdown-ссылка работает и в тексте, и в подписи",
           lnk.count('href="https://example.org/quote"') == 1
           and 'rel="noopener nofollow"' in lnk
           and '<cite>Автор, <a href="https://example.org/memory"' in lnk,
           lnk[lnk.find("<blockquote>"):lnk.find("</blockquote>")][:200])

        ok("цитата: соседний абзац остался абзацем, а не влез в <blockquote>",
           "<p>Ниже к этому разделу подвязана фигура" in one)

        # ── «>» внутри листингов - содержимое, а не цитата ──
        pre_q = build_spec(raw.replace(
            "$ wc -l landing.html\n67",
            "$ diff a.html b.html | grep '^[<>]'\n< 84:    font-size:24px;\n"
            "> 84:    font-size:28px;"), cfg, good)["content"]
        ok("«>» внутри :::pre остался содержимым листинга (экранирован, не цитата)",
           "&gt; 84:    font-size:28px;" in pre_q and "<blockquote>" not in pre_q,
           pre_q[pre_q.find("<pre"):pre_q.find("</pre>")][:200])
        fence_q = build_spec(raw.replace(
            '<html lang="ru">',
            '<html lang="ru">\n> вывод терминала внутри забора'), cfg, good)["content"]
        ok("«>» внутри забора ``` остался содержимым листинга",
           "&gt; вывод терминала внутри забора" in fence_q
           and "<blockquote>" not in fence_q)

        # ── готовый <blockquote> руками не заворачивается второй раз ──
        HAND = ('<blockquote><p>«Готовая цитата написана руками»</p>'
                '<cite>Источник волны, 2026</cite></blockquote>')
        hand = with_md(HAND)["content"]
        ok("рукописный <blockquote> уехал в страницу как был",
           HAND.replace("<blockquote>", "").split("</blockquote>")[0] in hand
           and hand.count("<blockquote>") == 1, hand.count("<blockquote>"))
        ok("рукописный <blockquote> не задвоился обёрткой",
           "<blockquote>\n  <p><blockquote>" not in hand
           and "<p>&lt;blockquote&gt;" not in hand)

        # ── «>» во вводке к «## Источники»: слот шаблона - <p>, не цитата ──
        src_q = build_spec(raw.replace("Фикстура собрана 12.08.2026",
                                       "> Фикстура собрана 12.08.2026"), cfg, good)
        ok("вводка «## Источники» с «>» очищена от маркера, текст цел",
           src_q.get("sources_intro", "").startswith("Фикстура собрана 12.08.2026")
           and ">" not in src_q.get("sources_intro", "")
           and len(src_q.get("sources") or []) == 2,
           repr(src_q.get("sources_intro"))[:160])

        # ── негатив-17: цитата без текста (одни «>») ──
        try:
            with_md(">\n>")
            ok("негатив-17: пустая цитата падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-17: пустая цитата падает", "пустая цитата" in str(e), str(e)[:160])
            ok("негатив-17: в отказе имя черновика и номер строки",
               bool(re.search(r"fixture-draft\.md:\d+", str(e))), str(e)[:160])

        # ── негатив-18: одна подпись без самой цитаты ──
        try:
            with_md("> - Anthropic, документация Claude Code")
            ok("негатив-18: цитата из одной подписи падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-18: цитата из одной подписи падает",
               "одной подписи" in str(e) and re.search(r"fixture-draft\.md:\d+", str(e)),
               str(e)[:160])

        # ── лид из двух абзацев не склеивается в один ──
        two = build_spec(raw.replace(
            "Пролог до первого H2 уезжает в лид статьи, если front-matter не задал "
            "поле lead отдельно.",
            "Первый абзац пролога держит вводку.\n\nВторой абзац пролога говорит, "
            "что разложено ниже."), cfg, good)
        ok("лид из двух абзацев пролога остаётся ДВУМЯ абзацами",
           (two.get("lead_html") or "").count("<p>") == 2,
           repr(two.get("lead_html"))[:160])
        ok("лид из одного абзаца по-прежнему один абзац",
           (spec.get("lead_html") or "").count("<p>") == 1)

        # ── КОД-СЛОВА В ТЕКСТЕ НЕТ (решение владельца) ──
        # Раньше здесь проверялось, что {{codeword_span}} разворачивается в
        # span.kw, а сборщик дописывает блок сам. Теперь противопоставление
        # обратное: ровно тот же черновик обязан РОНЯТЬ сборку
        ok("автодописи блока код-слова в финальном CTA больше нет",
           "class=\"kw\"" not in (spec.get("cta_final") or "")
           and "Код-слово этой статьи" not in (spec.get("cta_final") or ""),
           (spec.get("cta_final") or "")[-200:])
        for имя, кусок in (("{{codeword_span}}", "Код-слово фикстуры - {{codeword_span}}"),
                           ("{{codeword_block}}", "{{codeword_block}}"),
                           ("{{codeword}}", "Слово статьи - {{codeword}}")):
            try:
                build_spec(raw.replace("button: Забрать путёвку",
                                       "button: Забрать путёвку\n" + кусок),
                           cfg, good)
                ok("негатив-8: подстановка %s роняет сборку" % имя, False,
                   "сборка НЕ упала")
            except BuildError as e:
                ok("негатив-8: подстановка %s роняет сборку" % имя,
                   "код-слово в тексте" in str(e), str(e)[:140])
        try:
            build_spec(raw.replace(
                "Внутренняя ссылка ведёт на",
                "Код-слово этой статьи - СВОД. Внутренняя ссылка ведёт на"),
                cfg, good)
            ok("негатив-9: блок код-слова прозой (без подстановок) роняет сборку",
               False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-9: блок код-слова прозой (без подстановок) роняет сборку",
               "код-слово в тексте" in str(e), str(e)[:160])
        try:
            build_spec(raw.replace(
                "Внутренняя ссылка ведёт на",
                "Показываю кухню вживую, вход по слову ФИКСТУРА. Внутренняя ссылка ведёт на"),
                cfg, good)
            ok("негатив-9б: код-слово хвостом в живом предложении роняет сборку",
               False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-9б: код-слово хвостом в живом предложении роняет сборку",
               "код-слово в тексте" in str(e), str(e)[:160])
        # позитив: живая речь «по слову» без капса и листинг с классом kw внутри
        # кода статью ронять НЕ должны - иначе гейт красит статью про подсветку
        живая = build_spec(raw.replace(
            "Внутренняя ссылка ведёт на",
            "Искать в файле можно по слову или по фразе. Внутренняя ссылка ведёт на"),
            cfg, good)
        ok("позитив: живая речь «по слову» без капса проходит",
           bool(живая.get("content")))

        # ── Б2: :::cta place=mid anchor= доезжает до спеки и сверяется с разделами ──
        mid_ok = build_spec(raw.replace(
            ":::cta place=compact", ':::cta place=mid anchor="Ссылки и промо"', 1),
            cfg, good)
        ok("Б2: anchor= врезки доехал в спеку",
           mid_ok.get("cta_mid_anchor") == "Ссылки и промо", str(mid_ok.get("cta_mid_anchor")))
        try:
            build_spec(raw.replace(
                ":::cta place=compact", ':::cta place=mid anchor="Нет такого раздела"', 1),
                cfg, good)
            ok("негатив-10: anchor мимо разделов падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-10: anchor мимо разделов падает",
               "не совпал ни с одним разделом" in str(e) and "Ссылки и промо" in str(e),
               str(e)[:160])
        try:
            build_spec(raw.replace(
                ":::cta place=compact", ':::cta place=compact anchor="Ссылки и промо"', 1),
                cfg, good)
            ok("негатив-11: anchor у compact падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-11: anchor у compact падает", "только у :::cta place=mid" in str(e),
               str(e)[:120])

        # ── HowTo: front-matter «steps» -> spec.json["steps"] -> JSON-LD ──
        STEPS_ANCHOR = "author:\n  photo: /assets/avatar-150.webp"
        STEPS_OK = (
            'steps:\n'
            '  - {name: "Открыть форму на странице", text: "Найти кнопку Начать в шапке фикстуры"}\n'
            '  - {name: "Заполнить поля формы", text: "Ввести данные и подтвердить отправку"}\n'
            '  - {name: "Проверить результат отправки", text: "Свериться с ответом на экране", url: "#svoy-yakor"}\n'
        )
        steps_spec = build_spec(raw.replace(STEPS_ANCHOR, STEPS_OK + STEPS_ANCHOR), cfg, good)
        ok("steps: 3 шага поднялись в spec.json как name/text(/url)",
           steps_spec.get("steps") == [
               {"name": "Открыть форму на странице", "text": "Найти кнопку Начать в шапке фикстуры"},
               {"name": "Заполнить поля формы", "text": "Ввести данные и подтвердить отправку"},
               {"name": "Проверить результат отправки", "text": "Свериться с ответом на экране",
                "url": "#svoy-yakor"},
           ], str(steps_spec.get("steps"))[:300])

        sp_steps = os.path.join(tmp, "spec-steps.json")
        json.dump(steps_spec, open(sp_steps, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        rc_steps, out_steps = _run_build_page(sp_steps, os.path.join(tmp, "index-steps.html"))
        ok("сквозной прогон: build_page собрал страницу со steps", rc_steps == 0,
           out_steps.strip()[-300:])
        if rc_steps == 0:
            page_steps = open(os.path.join(tmp, "index-steps.html"), encoding="utf-8").read()
            ok("сквозной прогон: узел HowTo появился в JSON-LD", '"@type": "HowTo"' in page_steps)
            ok("сквозной прогон: все 3 HowToStep пришли в JSON-LD",
               page_steps.count('"@type": "HowToStep"') == 3,
               "count=%d" % page_steps.count('"@type": "HowToStep"'))
            ok("сквозной прогон: имя шага и url третьего шага доехали в JSON-LD дословно",
               '"name": "Открыть форму на странице"' in page_steps
               and '"url": "#svoy-yakor"' in page_steps)

        # ── негатив-12: steps не список ──
        try:
            build_spec(raw.replace(STEPS_ANCHOR, 'steps: "не список"\n' + STEPS_ANCHOR), cfg, good)
            ok("негатив-12: steps не списком падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-12: steps не списком падает", "должен быть списком" in str(e), str(e)[:160])

        # ── негатив-13: шаг без поля name ──
        NO_NAME = ('steps:\n'
                    '  - {text: "Шаг без поля name - невалидный"}\n'
                    '  - {name: "Второй шаг валиден", text: "Текст второго шага"}\n')
        try:
            build_spec(raw.replace(STEPS_ANCHOR, NO_NAME + STEPS_ANCHOR), cfg, good)
            ok("негатив-13: шаг без «name» падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-13: шаг без «name» падает",
               "steps[0]" in str(e) and "«name»" in str(e) and "fixture-draft.md" in str(e),
               str(e)[:160])

        # ── негатив-14: шаг с пустым text ──
        EMPTY_TEXT = ('steps:\n'
                       '  - {name: "Шаг с пустым текстом", text: ""}\n'
                       '  - {name: "Второй шаг валиден", text: "Текст второго шага"}\n')
        try:
            build_spec(raw.replace(STEPS_ANCHOR, EMPTY_TEXT + STEPS_ANCHOR), cfg, good)
            ok("негатив-14: пустой «text» падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-14: пустой «text» падает",
               "steps[0]" in str(e) and "«text»" in str(e), str(e)[:160])

        # ── негатив-15: шагов меньше вилки (1 < STEPS_MIN) ──
        ONE_STEP = 'steps:\n  - {name: "Единственный шаг", text: "Инструкция из одного шага - не HowTo"}\n'
        try:
            build_spec(raw.replace(STEPS_ANCHOR, ONE_STEP + STEPS_ANCHOR), cfg, good)
            ok("негатив-15: 1 шаг (меньше вилки) падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-15: 1 шаг (меньше вилки) падает",
               "вилку 2-20" in str(e) or "2-20" in str(e), str(e)[:160])

        # ── негатив-16: шагов больше вилки (> STEPS_MAX) ──
        TOO_MANY = "steps:\n" + "".join(
            '  - {name: "Шаг номер %d", text: "Текст шага номер %d для проверки потолка"}\n'
            % (i, i) for i in range(1, 25))
        try:
            build_spec(raw.replace(STEPS_ANCHOR, TOO_MANY + STEPS_ANCHOR), cfg, good)
            ok("негатив-16: 24 шага (больше вилки) падает", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-16: 24 шага (больше вилки) падает",
               "24 шагов" in str(e) and "2-20" in str(e), str(e)[:160])

        # ── негатив-19: слага нет в карте инвайтов -> сборка ПАДАЕТ ──────────
        # Тихого отката на адрес оффера тут быть не должно: именно молчаливый
        # фолбэк и печёт статью с кнопкой на лендинг вместо канала
        cfg_чужая_карта = dict(cfg)
        cfg_чужая_карта["invites"] = {"sovsem-drugoy-slag": "https://t.me/+DRUGOY"}
        try:
            build_spec(raw, cfg_чужая_карта, good)
            ok("негатив-19: слаг вне карты инвайтов роняет сборку", False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-19: слаг вне карты инвайтов роняет сборку",
               "нет в карте инвайтов" in str(e), str(e)[:160])
            ok("негатив-19: в отказе назван слаг и перечислены опробованные ключи",
               "guide-fixture" in str(e) and "пробовал ключи" in str(e), str(e)[:200])

        # ── негатив-20/21: запрещённые литералы НЕЗАВИСИМО от target_url ─────
        # Ключевая часть: target_url у cfg_лит намеренно НЕ содержит литерал
        # (адрес CTA уехал на инвайт) - значит краснеет именно новый гейт, а не
        # старая проверка пути оффера
        лит = list(cfg.get("forbidden_literals") or FALLBACK_FORBIDDEN)
        cfg_лит = dict(cfg)
        cfg_лит["target_url"] = "https://t.me/+FXinvite000000001"
        cfg_лит["target_path"] = "/+FXinvite000000001"
        for i, литерал in enumerate(лит[:2]):
            try:
                build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                       "Старый маршрут %s остался в тексте. "
                                       "Внутренняя ссылка ведёт на" % литерал),
                           cfg_лит, good)
                ok("негатив-2%d: литерал «%s» в черновике роняет сборку" % (i, литерал),
                   False, "сборка НЕ упала")
            except BuildError as e:
                ok("негатив-2%d: литерал «%s» в черновике роняет сборку" % (i, литерал),
                   "запрещённый литерал" in str(e) and литерал in str(e), str(e)[:200])
                ok("негатив-2%d: отказ называет ключ config, а не путь оффера" % i,
                   "cta.forbidden_literals" in str(e), str(e)[:200])

        # ── негатив-22: литерал приехал ПОДСТАНОВКОЙ - краснеет собранная спека ──
        cfg_подст = dict(cfg_лит)
        cfg_подст["install_guide_url"] = лит[0]
        try:
            build_spec(raw, cfg_подст, good)
            ok("негатив-22: литерал из подстановки роняет сборку по собранной спеке",
               False, "сборка НЕ упала")
        except BuildError as e:
            ok("негатив-22: литерал из подстановки роняет сборку по собранной спеке",
               "запрещённый литерал" in str(e) and "собранной спеке" in str(e), str(e)[:200])

        # ── негатив-23: формы литерала (без хвостового слеша, url-encoded) ───
        путь = next((x for x in лит if x.startswith("/") and x.endswith("/")), None)
        if путь:
            формы = forbidden_forms(путь)
            ok("формы литерала: как есть + без хвостового слеша + url-encoded",
               путь in формы and путь.rstrip("/") in формы
               and any("%2F" in f or "%2f" in f for f in формы), str(формы))
            for форма in [x for x in формы if x != путь]:
                try:
                    build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                           "Хвост маршрута %s. Внутренняя ссылка ведёт на"
                                           % форма), cfg_лит, good)
                    ok("негатив-23: форма «%s» роняет сборку" % форма, False,
                       "сборка НЕ упала")
                except BuildError as e:
                    ok("негатив-23: форма «%s» роняет сборку" % форма,
                       "запрещённый литерал" in str(e), str(e)[:160])
            ok("формы литерала: одно вхождение считается ОДИН раз, не дважды",
               len(forbidden_hits("текст %s хвост" % путь, путь)) == 1,
               str(forbidden_hits("текст %s хвост" % путь, путь)))
            якорь = 'id="%s"' % путь.strip("/")
            ok("формы литерала: якорь id=«имя» без слеша ложно не ловится",
               not forbidden_hits("<h2 %s>заголовок</h2>" % якорь, путь), якорь)

        # ── позитив: чистый черновик с непустым списком литералов проходит ────
        ok("список литералов не роняет чистый черновик",
           bool(build_spec(raw, cfg_лит, good).get("content")))

        # ── С2: жаргон уровня страницы ловится уже в ЧЕРНОВИКЕ (по решению автора) ────
        # До фикса это ловил только article_gates.py на СОБРАННОЙ странице -
        # автор узнавал о жаргоне последним швом конвейера, после полной сборки
        try:
            build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                   "Это вечнозелёная смена в записи. "
                                   "Внутренняя ссылка ведёт на"),
                       cfg, good)
            ok("С2 негатив: «вечнозелёная смена в записи» в черновике роняет сборку",
               False, "сборка НЕ упала")
        except BuildError as e:
            ok("С2 негатив: «вечнозелёная смена в записи» в черновике роняет сборку",
               "жаргон уровня страницы" in str(e) and "вечнозелён" in str(e),
               str(e)[:200])
        ok("С2 позитив: чистый черновик без жаргона по-прежнему собирается",
           bool(build_spec(raw, cfg, good).get("content")))

        # ── О1: обход словоформ жаргона, скептик раунд-2 (по решению автора) ─────────
        # Три формулировки скептика: дефисное сращение («Онлайн-смена» вместо
        # « смена» с пробелом), другая цена у VIP, форма «доступ в записи» без
        # слова «смена». Все три роняют сборку ЧЕРНОВИКА (не только страницы)
        О1_ФОРМУЛИРОВКИ = ("Онлайн-смена в записи начинается по будням.",
                          "Тариф VIP 1990 включает разбор домашних заданий.",
                          "Доступ в записи открывается сразу после оплаты.")
        for формулировка in О1_ФОРМУЛИРОВКИ:
            try:
                build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                       формулировка + " Внутренняя ссылка ведёт на"),
                           cfg, good)
                ok(f"О1 негатив: «{формулировка}» в черновике роняет сборку",
                   False, "сборка НЕ упала")
            except BuildError as e:
                ok(f"О1 негатив: «{формулировка}» в черновике роняет сборку",
                   "жаргон уровня страницы" in str(e), str(e)[:200])
        # позитив скептика: «10 медиа в записи» (формулировка ВКонтакте) -
        # голое «в записи» без слова-триггера ЖАРГОНОМ не считается
        spec_О1 = build_spec(raw.replace(
            "Внутренняя ссылка ведёт на",
            "ВКонтакте показывает 10 медиа в записи одним альбомом. "
            "Внутренняя ссылка ведёт на"), cfg, good)
        ok("О1 позитив: «10 медиа в записи» (ВКонтакте) НЕ жаргон, черновик собирается",
           bool(spec_О1.get("content")))
        ok("О1: jargon_hits видит все три формы разом (дефис/цена/без «смена»)",
           len({h[0] for h in jargon_hits(
               "Онлайн-смена в записи. Тариф VIP 1990. Доступ в записи.")}) == 3,
           str(jargon_hits("Онлайн-смена в записи. Тариф VIP 1990. Доступ в записи.")))
        ok("О1: голое «10 медиа в записи» jargon_hits не считает жаргоном",
           jargon_hits("ВКонтакте показывает 10 медиа в записи одним альбомом") == [],
           str(jargon_hits("ВКонтакте показывает 10 медиа в записи одним альбомом")))

        # ── Д2: словоформы «смена» мимо «смена в записи» (по решению автора) ─────────
        # Найдено агентом на живом корпусе: guide-google-ai-studio уехал на прод
        # с «разбираем на смене» / «учим на смене в записи» / кнопками
        # «Посмотреть/Открыть смену», «Перейти к смене» - ни одна форма не
        # содержит буквально «смена в записи», старый регекс всех пропустил
        Д2_ЖАРГОН = ("Эту работу мы разбираем на смене.",
                    "Этому мы учим на смене в записи, доступ открывается сразу.",
                    "Посмотреть смену",
                    "Открыть смену",
                    "Забрать смену прямо сейчас",
                    "Записаться на смену можно в один клик",
                    "Перейти к смене")
        for формулировка in Д2_ЖАРГОН:
            try:
                build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                       формулировка + " Внутренняя ссылка ведёт на"),
                           cfg, good)
                ok(f"Д2 негатив: «{формулировка}» в черновике роняет сборку",
                   False, "сборка НЕ упала")
            except BuildError as e:
                ok(f"Д2 негатив: «{формулировка}» в черновике роняет сборку",
                   "жаргон уровня страницы" in str(e), str(e)[:200])
        # позитив: легальный русский оборот «на смену» (винительный - «прийти
        # на замену/смену») - НЕ жаргон продукта. Все четыре взяты дословно из
        # живого корпуса (guide-genspark/guide-neyroset-dizayn-interera/
        # guide-sozdat-telegram-bota/guide-antigravity), калибровка по решению автора:
        # с узким падежом «на смене» ни одна не красится
        Д2_ЛЕГАЛЬНО = (
            "У новой версии Super Agent (пришла на смену Classic) три отличия.",
            "Отсутствие запрета на смену планировки - модель двигает окно.",
            "Всё это без наёма человека на смену и без стороннего сервиса.",
            "Подать заявку на смену региона можно на странице настроек.",
        )
        for фраза in Д2_ЛЕГАЛЬНО:
            spec_д2 = build_spec(raw.replace("Внутренняя ссылка ведёт на",
                                             фраза + " Внутренняя ссылка ведёт на"),
                                 cfg, good)
            ok(f"Д2 позитив: «{фраза[:50]}…» легальный оборот, НЕ жаргон",
               bool(spec_д2.get("content")),
               str(jargon_hits(фраза)))
        ok("Д2: jargon_hits видит словоформу «на смене» и все кнопочные формы",
           len({h[0] for h in jargon_hits(
               "Разбираем на смене. Посмотреть смену. Открыть смену. "
               "Перейти к смене. Записаться на смену.")}) == 3,
           str(jargon_hits("Разбираем на смене. Посмотреть смену. Открыть смену. "
                           "Перейти к смене. Записаться на смену.")))
        ok("Д2: «на смену» (винительный, легальный оборот) jargon_hits не ловит",
           jargon_hits("У новой версии Super Agent (пришла на смену Classic).") == [],
           str(jargon_hits("У новой версии Super Agent (пришла на смену Classic).")))
        ok("Д2: пустой/чистый черновик по-прежнему собирается",
           bool(build_spec(raw, cfg, good).get("content")))

        # ── C3: литерал-гейт против ЕГО ЖЕ target_url (по решению автора) ────────────
        # ЗАЧЕМ. Фолбэк-режим (нет cta.invites_map) легитимно ведёт CTA на
        # target_url - если forbidden_literals при этом содержит литерал, равный
        # ЭТОМУ ЖЕ target_url (типично: список литералов не переопределён под
        # себя), гейт ловил собственный действующий CTA как «старый маршрут», и
        # сборка падала на собственном лендинге без другого адреса. Литерал
        # приезжает в спеку ПОДСТАНОВКОЙ (nav_cta_url = target_url + utm), не
        # текстом в черновике - раскладка теста повторяет негатив-22
        own_lit = (cfg_nomap.get("target_path")
                   if cfg_nomap.get("target_path") not in ("", "/", None)
                   else cfg_nomap["target_url"])
        cfg_фолбэк_свой = dict(cfg_nomap)
        cfg_фолбэк_свой["forbidden_literals"] = [own_lit]
        try:
            spec_фолбэк = build_spec(raw, cfg_фолбэк_свой, good)
            ok("С3 позитив: фолбэк без карты собирается, когда forbidden_literals "
               "= его же target_url (гейт не ругается на собственный CTA)",
               bool(spec_фолбэк.get("content")))
            ok("С3 позитив: CTA фолбэка остался target_url + utm (исключение "
               "тронуло только гейт, не сам маршрут)",
               cfg_nomap["target_url"].split("?")[0] in spec_фолбэк["nav_cta_url"],
               spec_фолбэк["nav_cta_url"])
        except BuildError as e:
            ok("С3 позитив: фолбэк без карты собирается, когда forbidden_literals "
               "= его же target_url (гейт не ругается на собственный CTA)",
               False, str(e)[:200])
            ok("С3 позитив: CTA фолбэка остался target_url + utm (исключение "
               "тронуло только гейт, не сам маршрут)", False, "сборка упала раньше")

        # Негатив: карта инвайтов ЗАДАНА - исключения нет. Тот же приём (литерал,
        # равный ТЕКУЩЕМУ target_url ЭТОГО конфига, приехавший подстановкой
        # install_guide_url), но invites не None - С3 сузил гейт только для
        # фолбэк-режима, не отключил его вовсе
        cfg_карта_свой = dict(cfg_лит)   # invites present, свой синтетический target_url
        own_lit_карта = (cfg_лит.get("target_path")
                         if cfg_лит.get("target_path") not in ("", "/", None)
                         else cfg_лит["target_url"])
        cfg_карта_свой["forbidden_literals"] = [own_lit_карта]
        cfg_карта_свой["install_guide_url"] = own_lit_карта
        try:
            build_spec(raw, cfg_карта_свой, good)
            ok("С3 негатив: с картой инвайтов литерал = target_url всё равно "
               "роняет сборку (исключение только у фолбэк-режима)",
               False, "сборка НЕ упала")
        except BuildError as e:
            ok("С3 негатив: с картой инвайтов литерал = target_url всё равно "
               "роняет сборку (исключение только у фолбэк-режима)",
               "запрещённый литерал" in str(e) and "собранной спеке" in str(e),
               str(e)[:200])

        # ── В10: дефолт -o не имеет права затирать боевую spec.json ──
        art = os.path.join(tmp, "article")
        os.makedirs(art, exist_ok=True)
        shutil.copyfile(good, os.path.join(art, "draft.md"))
        live_spec = os.path.join(art, "spec.json")
        with open(live_spec, "w", encoding="utf-8") as f:
            f.write('{"боевая":"спека пачки"}')
        base = [sys.executable, os.path.join(HERE, "article_build.py"),
                os.path.join(art, "draft.md"), "--config", sub_cfg]
        p = subprocess.run(base, capture_output=True, text=True)
        keep = open(live_spec, encoding="utf-8").read()
        ok("В10: без -o сборка ОТКАЗЫВАЕТ, когда spec.json уже есть",
           p.returncode != 0, "rc=%d" % p.returncode)
        ok("В10: боевая spec.json осталась нетронутой", keep == '{"боевая":"спека пачки"}',
           keep[:80])
        ok("В10: в отказе названы оба выхода (-o и --force)",
           "-o " in (p.stdout + p.stderr) and "--force" in (p.stdout + p.stderr),
           (p.stdout + p.stderr).strip()[:200])
        p = subprocess.run(base + ["--force"], capture_output=True, text=True)
        ok("В10: --force перезаписывает осознанно", p.returncode == 0
           and json.load(open(live_spec, encoding="utf-8")).get("h1"),
           (p.stdout + p.stderr).strip()[-200:])
        fresh = os.path.join(tmp, "fresh")
        os.makedirs(fresh, exist_ok=True)
        shutil.copyfile(good, os.path.join(fresh, "draft.md"))
        p = subprocess.run([sys.executable, os.path.join(HERE, "article_build.py"),
                            os.path.join(fresh, "draft.md"), "--config", sub_cfg],
                           capture_output=True, text=True)
        ok("В10: на чистой папке дефолт по-прежнему работает без флагов",
           p.returncode == 0 and os.path.exists(os.path.join(fresh, "spec.json")),
           (p.stdout + p.stderr).strip()[-200:])
    finally:
        # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
        pass

    print("── selftest article_build.py ──")
    for st, name, detail in checks:
        print("  %s %s%s" % (st, name, ("  <- " + detail) if detail and st == "FAIL" else ""))
    print("итог: %d проверок, провалов %d" % (len(checks), failed))
    return 1 if failed else 0


OVERWRITE_HINT = (
    "рядом с черновиком уже лежит БОЕВАЯ спека %s. Без -o шов затёр бы её "
    "результатом сборки, а спека пачки - источник истины статьи (в ней осели "
    "фикс-волны, черновик рядом мог отстать). Выбери явно:\n"
    "  • песочница   python3 article_build.py %s -o /tmp/spec-v2.json\n"
    "  • перезапись  python3 article_build.py %s --force")


def resolve_out(draft, out, force):
    """Куда писать спеку. Молчаливой перезаписи боевого файла тут нет.

    Дефолт «пишем spec.json рядом» стоил бы ровно одного невнимательного
    прогона: миграция статьи гоняется с ЖИВОЙ папкой, и первый же вызов без
    -o подменил бы эталон сравнения тем, что сам же и собрал - гейт после
    этого сверял бы файл сам с собой и всегда печатал PASS.
    """
    if out:
        return out
    target = os.path.join(os.path.dirname(os.path.abspath(draft)), "spec.json")
    if os.path.exists(target) and not force:
        fail(OVERWRITE_HINT % (target, draft, draft))
    return target


def main():
    ap = argparse.ArgumentParser(description="draft.md -> spec.json (единственный шов)")
    ap.add_argument("draft", nargs="?", help="путь к draft.md")
    ap.add_argument("-o", "--out", help="куда писать spec.json (без него - рядом с "
                                        "draft, и ТОЛЬКО если файла там ещё нет)")
    ap.add_argument("--force", action="store_true",
                    help="разрешить перезапись существующей spec.json рядом с черновиком")
    ap.add_argument("--config", help="config.md скилла lead-magnit")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        try:
            return selftest(a.config)
        except BuildError as e:
            print("ОШИБКА selftest: %s" % e)
            return 2
    if not a.draft:
        ap.error("укажи draft.md или --selftest")
    try:
        out = resolve_out(a.draft, a.out, a.force)
        cfg = load_config(a.config)
        spec = build_spec(open(a.draft, encoding="utf-8").read(), cfg, a.draft)
    except BuildError as e:
        sys.exit("ОШИБКА article_build: %s" % e)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    n_sec = spec["content"].count("<section id=")
    print("spec.json записан: %s" % out)
    print("разделов: %d · FAQ: %d · источников: %d · related: %d · чек-лист: %s"
          % (n_sec, len(spec.get("faq") or []), len(spec.get("sources") or []),
             len(spec.get("related") or []), "да" if spec.get("checklist") else "нет"))
    print("description знаков: %d" % len(spec["description"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
