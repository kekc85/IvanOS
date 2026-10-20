#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
article_gates.py - ЕДИНЫЙ РАННЕР ГЕЙТОВ статьи. Один вызов = все проверки стадии.

ЗАЧЕМ. Гейты конвейера жили россыпью команд по трём файлам канона (03-content §10,
04-handoff Шаг 2, 05-deliver §3), плюс четыре гейта не были задокументированы нигде
(strip_notes, claim_gate, reflections_gate, hub_counts). Исполнитель звал те, что
помнил, вердикт собирал глазами, а машинного следа «что прогнали и чем кончилось»
не оставалось вовсе. Здесь чекеры НЕ переписываются - они оркеструются: один вызов,
один exit-код, один машинный отчёт $WORK/<slug>/gates.json.

СТАДИИ (что проверяем на каком шве):
  draft   - по черновику: структура, ритм AI-почерка, читаемость вслух, оригинальность,
            формула сниппета (гейт title-ctr: длина title, счётчик-число, равенство с
            H1, брендовый хвост, запрещённые формулы, description, капсула ответа)
  page    - по СОБРАННОЙ странице: визуальные оси, рендер, оглавление, служебные
            комментарии, ритм по телу черновика (канон 04-handoff, Шаг 2), плюс та же
            формула сниппета по живым байтам + таблицы и раскрытость FAQ, плюс гейт
            cta (маршрут CTA: именной инвайт слага по карте cta.invites_map, ноль
            запрещённых литералов cta.forbidden_literals, ноль внутреннего жаргона),
            плюс гейт infra-leak (утечка служебной инфраструктуры автора - IP/хост/
            логин деплой-релея - список литералов infra-secrets.txt; файла нет =
            гейт SKIP громко, а не тихий PASS - инцидент р9, по решению автора),
            плюс гейт image-refs (БИТАЯ КАРТИНКА - инцидент по решению автора: ссылка
            на изображение обязана резолвиться в той раскладке, по которой
            страница поедет на прод, каталожной /<slug>/assets/ или плоской
            /assets/<slug>/; отдельно и громко ловится СМЕШАННАЯ раскладка
            внутри одного <picture> - img[src] корневой, source[srcset]
            относительный: промах <source> НЕ откатывается на <img>, и читатель
            видит битый кадр при живом фолбэке. Раскладка приходит флагами
            --page-layout/--assets-remote, дефолт auto - выводится из самой
            страницы. Пара к assets-exist и ровно его слепая зона: тот
            спрашивает «файл на диске есть», этот - «по какому адресу ссылка
            попадёт на проде»),
            плюс гейт frame-density (что ВНУТРИ кадра: пустой блок block_pct >= 40,
            мёртвая полоса band_pct >= 40 и текст-плашка empty_pct >= 80 при
            block_pct < 20 и без признаков кадра-контента; зона block_pct 25-40 -
            ЗАМЕЧАНИЕ глазами, стадию не роняет; метрика - порт emptiness-scan.py,
            пороги - калибровка аудита кадров r10, перекалибровка по решению автора),
            плюс гейт cta-position (МЕСТО финального призыва в хвосте: памятка
            section#checklist -> призыв .cta-final -> частые вопросы section#faq;
            правка владельца - призыв стоял в подвале ЗА FAQ),
            плюс гейт frame-provenance (ОТКУДА кадр: у каждого контентного кадра
            статьи - хиро, кадр тела, og-обложка - обязана быть запись в
            shots-manifest.json рядом со страницей, класс result/step/own-run/
            inherited И режим съёмки mode из external/relay/url/scenario, а текст
            записи не должен называть канал, закрытый законом (og_hero, cover.py,
            meme, illustration, gpt_render, мокап, плашка, фотосток); закон
            владельца «только ультра-реализм и только
            ценность». По умолчанию МЯГКО - WARN, стадию не роняет; замок
            включается флагом --provenance-hard и роняет ЧЕТЫРЕ признака: кадр
            без записи, запись без mode (сделана не shot.py), закрытый канал в
            тексте записи и class=result с адресом корня сервиса («скрин
            главной» вместо результата функции); режим --provenance-report меряет
            корпус и не роняет ничего)
  novice - стандарт «понятно новичку» (рв даты запуска.2026), стоит на ОБЕИХ стадиях
            draft и page: жаргон на 1000 слов видимого текста по чистому счёту
            (без pre/code, без атрибутов и ссылок, без объяснённых в том же
            предложении терминов), свалка код-блоков без обвязки «вставь ->
            нажми -> увидишь», терминальные скрины и мокапы окна терминала с
            shell-командами. Пороги - калибровка по срезу corpus-r10-20260818
            (302 guide-страницы), см. THRESHOLDS в novice-check.py. Обход для
            легаси-операций - флаг --skip-novice (уходит в отчёт как SKIP с
            причиной, тихого PASS не бывает)
  publish - перед выдачей: артефакты-минимум, байт-лок дверей, захват разделяемых
            файлов, отражения корпуса, числа хабов

Запуск:
  python3 article_gates.py <slug> --stage draft
  python3 article_gates.py <slug> --stage draft --draft draft-v2.md   # кандидат миграции
  python3 article_gates.py <slug> --stage page [--revision]
  python3 article_gates.py <slug> --stage publish
  python3 article_gates.py <slug> --stage draft --no-write   # диагностика без записи
  python3 article_gates.py <slug> --stage page --provenance-hard  # замок происхождения кадров
  python3 article_gates.py --frame-provenance <каталог> --provenance-report  # замер корпуса
  python3 article_gates.py --gate-set page # эталонный набор имён гейтов стадии (JSON)
  python3 article_gates.py --list          # какие гейты входят в какую стадию
  python3 article_gates.py --selftest      # позитив + негативы на фикстурах

ОТЧЁТ gates.json (формат с этой редакции, фикс-волна 1, дефект В7). Раньше в шапке
лежал один ключ `verdict_last` - вердикт ПОСЛЕДНЕГО ПО ВРЕМЕНИ прогона любой
стадии, и диагностический прогон draft затирал в шапке живой PASS стадии page.
Теперь шапка несёт:
  verdicts              - последний вердикт КАЖДОЙ стадии отдельно (+ время, применимость)
  verdict_publish_ready - PASS, только если draft, page и publish зелёные в своих
                          последних прогонах (неприменимая стадия не блокирует)

ОТПЕЧАТОК НАБОРА ГЕЙТОВ (правка 22.08.2026). Запись КАЖДОЙ стадии несёт поле
`gate_set` - сортированный список имён гейтов, которые в этом прогоне реально
были. Без него расписка говорила «page=PASS» и молчала о том, КАКИМИ гейтами:
добавили в стадию новый гейт - и страницы с готовым зелёным вердиктом от
ПРОШЛОГО набора уезжали в прод мимо него. Эталон набора отдаёт сам раннер
(`article_gates.py --gate-set page`, JSON-строка) - второго списка имён гейтов
в проекте нет, разойтись с кодом ему негде.

РАСПИСКА ПОДПИСЫВАЕТ БАЙТЫ СТРАНИЦЫ (правка 13.08.2026, фикс-волна 13, дефект
Б16). Записи стадий `page` и `publish` несут `page_sha256` - sha256 файла
index.html НА МОМЕНТ ПРОГОНА (плюс `page` и `page_bytes`). Без этого поля
gates.json был распиской ни на что: пересобрал страницу, вписал в неё что
угодно - вердикт «page=PASS» от вчерашнего прогона продолжал открывать двери,
хотя обязательный гейт стадии эти байты отверг бы. Читатели расписки
(artifacts_gate.gates_json_state, ftp_publish перед минтом и заливкой) обязаны
сверять поле с живым index.html; расхождение или отсутствие поля = отказ с
одним лечением - `article_gates.py <slug> --stage page`.

ПРИМЕНИМОСТЬ СТАДИИ draft РЕШАЕТ КОНТРАКТ ЧЕРНОВИКА, А НЕ ФАКТ ПУБЛИКАЦИИ
(правка 12.08.2026, фикс-волна 3, дефект Б1).

  • Черновик НОВОГО контракта (front-matter несёт `engine: article_build`) -
    ЗАМОК ВСЕГДА, опубликована статья или нет. Такой черновик и есть источник
    истины статьи: из него собирается спека, из спеки страница. Красная стадия
    draft тут = красная статья, диагностикой её объявлять нечем.
  • ЛЕГАСИ-черновик (без маркера) У ОПУБЛИКОВАННОЙ статьи - ДИАГНОСТИКА.
    Признак публикации - реестр публикаций (artifacts_gate.is_published), не
    догадка. Причина: у статей старой схемы источник истины - spec.json рядом, а
    draft.md заморожен до фикс-волн; часть блоков живёт только в СОБРАННОЙ
    странице (CTA на оффер build_page подставляет из spec.json), и
    structure-check по такому draft.md обязан краснеть «нет ссылки на оффер» -
    это ложняк стадии, а не дефект статьи (улика по решению автора: draft.md
    guide-ii-pomoshchnik - 0 вхождений адреса оффера, index.html - 7, spec.json - 4).
  • ЛЕГАСИ-черновик НЕопубликованной статьи - замок (как и было).

Диагностический прогон пишется в отчёт с `applicable: false`, печатается как
диагностический, вердикт стадии сохраняется как есть, но код выхода 0 и
publish-ready он не блокирует. Стадии page и publish - замок ВСЕГДА и для всех.

Почему замок вернули. До фикса Б1 черновик нового контракта не мог пройти
structure-check в принципе (адрес оффера в нём стоит подстановкой {{cta_url}}
или выражен директивой :::cta - гейт искал литерал), и «понизить стадию до
информационной» было лечением симптома: замок снимали со ВСЕХ статей, чтобы не
краснела одна. Теперь чекер читает контракт, и стадии вернули её работу.

Цель стадии по умолчанию - draft.md. Флаг --draft <файл> гонит стадию по другому
черновику: во время миграции кандидат лежит рядом под именем draft-v2.md, и
проверять надо ЕГО, а не замороженный легаси-файл.

Коды выхода:
  0 - все ОБЯЗАТЕЛЬНЫЕ гейты стадии PASS (WARN и SKIP не роняют), либо стадия
      неприменима к этой статье (диагностический прогон);
  1 - хотя бы один обязательный гейт FAIL/ERROR в применимой стадии;
  2 - ошибка входа: нет каталога статьи, нет цели стадии, битый аргумент.

Статусы гейта: PASS · WARN (мягкое замечание, вердикт не роняет) · FAIL ·
SKIP (условный гейт легитимно неприменим к ДАННЫМ этого прогона: нет соседей
для сверки оригинальности, нет draft.md у spec.json-статьи, гейт вне волны -
роняет ли вердикт, обязательность НЕ меняет: SKIP не роняет никогда) ·
ERROR (инструмент не найден/упал/завис, ИЛИ обязательному условному гейту не
настроено ОКРУЖЕНИЕ - нет канона дверей, нет corpus_snapshot/corpus_status -
дефект р7-по решению автора: раньше такой гейт молча уходил в SKIP при зелёном вердикте
стадии, теперь громко ERROR с именем недостающего ключа - обязательный гейт
роняет вердикт).

ПУТИ. Сначала ключи ~/.config/seo-publish.json, потом канонный фолбэк:
  work_dir · lm_tools · template_dir · seo_scripts       (каталоги)
  artifacts_gate · claim_gate · door_gate · door_canon   (точные файлы)
  corpus_snapshot · corpus_status · shared_files         (вход условных гейтов)
  lead_magnit_config                                     (config.md скилла: закон
                                                          CTA; фолбэк - сосед lm_tools)
  infra_secrets                                          (список запрещённых
                                                          литералов инфраструктуры -
                                                          infra-secrets.txt, автор-дом,
                                                          не раздаётся; файла нет -
                                                          гейт infra-leak SKIP громко)
Волна и агент для claim-гейта берутся из окружения: SEO_WAVE, SEO_AGENT.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import html
import importlib.util
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def отложить(путь, ignore_errors=False):
    """ЗАКОН №0 владельца (по решению автора, дословно «вообще ничего не удаляй, пусть лежит»).

    Обратимая замена сноса: путь ПЕРЕИМЕНОВЫВАЕТСЯ в датированного соседа
    `<имя>.otlozheno-<ГГГГММДД-ЧЧММСС>`. Прежнее имя после вызова свободно -
    ровно тот эффект, ради которого раньше звался снос, - а байты остаются на
    диске и возвращаются обратным переименованием. Каталог откладывается рядом
    с собой, файл - рядом с собой же в том же каталоге: имя перестаёт совпадать
    с любой маской вида `*.json` / `*.png` / `index.html`, поэтому отложенное
    не подхватывают ни глобы, ни белые списки заливки.

    Заведено по решению автора: страж no-entity-deletion-gate.sh не давал ЗАПУСТИТЬ
    инструмент, в теле которого лежал вызов удаления, и приёмка контура была
    физически неисполнима.
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

from artifacts_gate import (  # noqa: E402  (сосед по каталогу)
    load_cfg, cfg_path, work_dir, is_published)
# сборщик статьи: у гейта cta и у сборщика ОДИН разбор config.md и ОДИН резолвер
# слага по карте инвайтов - второй экземпляр закона тут заводить нельзя
import article_build  # noqa: E402  (сосед по каталогу)

# канонные фолбэки. Файл живёт в доме сборки и ученикам не раздаётся - знать
# канонные пути ему можно; раздаваемые артефакты ходят ТОЛЬКО через конфиг.
FALLBACK = {
    "lm_tools": "~/.claude/skills/lead-magnit/tools",
    "template_dir": "~/.business/growth/seo/article-template",
    "seo_scripts": "~/.business/scripts/seo",
    "artifacts_gate": "~/.business/growth/seo/article-template/artifacts_gate.py",
    "claim_gate": "~/.business/growth/seo/_rebuild/claim_gate.py",
    "door_gate": "~/.business/growth/seo/_rebuild/r4/transform/door_gate.py",
    "door_canon": "~/.business/growth/seo/door-titles-canon.json",
    # инцидент р9 (по решению автора): IP деплой-релея утёк в видимый текст 6 статей,
    # ни один гейт это не поймал. Список ЛИТЕРАЛОВ - НЕ здесь (см. докстринг
    # infra_leak_matches): файл живёт рядом, в автор-доме, ученикам не раздаётся
    "infra_secrets": "~/.business/growth/seo/infra-secrets.txt",
}

STAGES = ("draft", "page", "publish")
# маркер контракта сборки в front-matter черновика (тот же, что у article_build)
ENGINE_MARK = "article_build"
ENGINE_MARK_RE = re.compile(r"^engine:\s*%s\s*$" % ENGINE_MARK, re.M)
TIMEOUT = 600
TAIL_LINES = 25
TAIL_CHARS = 2500
# строки, ради которых гейт и краснеет: жёсткие замечания чекеров, отказы гейтов.
# Хвост вывода их не гарантирует - у structure-check жёсткая строка идёт ПЕРЕД
# пачкой мягких, и в отчёт уезжали одни soft-строки при вердикте FAIL
HARD_PREFIX = ("!", "✗", "ОШИБКА", "ЗАНЯТО", "ЗАЛИВКА СТОП", "НЕТ (", "- ", "ДВЕРЬ")


# ── разрешение путей ─────────────────────────────────────────────────────────

def tool(cfg, key, dir_key=None, name=None):
    """Путь инструмента: точный ключ конфига → каталог из конфига + имя → канон."""
    v = cfg.get(key)
    if isinstance(v, str) and v.strip():
        return os.path.expanduser(v.strip())
    if dir_key and name:
        d = cfg_path(cfg, dir_key, FALLBACK[dir_key])
        return os.path.join(d, name)
    return os.path.expanduser(FALLBACK[key])


def existing(path):
    return bool(path) and os.path.isfile(path)


def config_gap_reason(prefix, checks):
    """Собрать текст «гейт не настроен» из списка (условие_выполнено, текст_если_нет).

    Один читаемый ключ X сразу называет ВСЕ недостающие входы разом - починка
    в один заход, а не по одному циклу «поправил-перегнал-нашёл следующий».
    """
    missing = [text for ok, text in checks if not ok]
    return f"{prefix}: " + "; ".join(missing) if missing else None


# ── звено цепи доверия: расписка гейтов подписывает БАЙТЫ страницы (Б16) ─────
#
# 🔴 ЗАЧЕМ (скептик-13, по решению автора). gates.json был распиской НИ НА ЧТО: он
# говорил «стадия page = PASS» и не говорил, ПО КАКИМ БАЙТАМ. Пересобрал
# index.html, вписал в него что угодно, переминтил расписку - и обязательный
# гейт стадии (strip_notes) эти байты отверг бы, а зелёный gates.json от
# по решению автора 17:48 рядом с index.html от этой редакции никого не смущал: сверять было нечем.
# Все соседние звенья цепи уже подписаны содержимым (gates-manifest.json несёт
# page_sha256, article_verify сверяет источник со страницей), незавязанным
# оставалось ровно это.
# Теперь запись стадии несёт sha256 страницы НА МОМЕНТ ПРОГОНА, и любой, кто
# читает gates.json как расписку, обязан сверить его с живым index.html.
def page_sha256(path):
    """(sha256 файла, размер) или (None, None) - файла нет / не читается."""
    if not existing(path):
        return None, None
    h = hashlib.sha256()
    size = 0
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
    except OSError:
        return None, None
    return h.hexdigest(), size


def draft_is_new_contract(draft_path):
    """Черновик собирается конвейером article_build (маркер в front-matter).

    Читаем только шапку файла: маркер стоит в YAML-блоке сверху, тащить в память
    20 000 знаков статьи незачем. Нет файла - контракта нет.
    """
    if not existing(draft_path):
        return False
    try:
        with open(draft_path, encoding="utf-8") as f:
            head = f.read(4000)
    except OSError:
        return False
    return bool(ENGINE_MARK_RE.search(head))


# ── гейт title-ctr: формула сниппета (Т2-Т4, Т6 из _rebuild/r7/serp-bench.md) ─
#
# 🔴 ЗАЧЕМ. Замер СОБСТВЕННОГО корпуса, 44 страницы, контроль по позиции внутри
# бакета 4-10 (serp-bench.md, раздел Т2): title со счётчиком-числом даёт CTR
# 2.46% при средней позиции 7.14, без счётчика - 1.09% при 7.36. Разница 2.26x
# ПРИ ОДИНАКОВОЙ позиции, то есть это ось КЛИКОВ, а не ранжирования. Раздел 4.2
# того же файла, строки 2-3: «нет гейта на формулу title, 28 из 44 страниц без
# счётчика», «title длиннее 60 символов у 22 из 44, максимум 90» - оба помечены
# как ДОКАЗАННОЕ. Гейта на формулу title в раннере не было вообще.
#
# ЧТО ПРОВЕРЯЕТ (каждая ось - отдельная строка вердикта, чтобы автор видел, ЧТО
# именно не так, а не «title плохой»):
# 1 длина title в вилке 51-66 верх поднят с 60 до 66 по решению автора, разбор ниже
#                                      («ПОЧЕМУ ВЕРХ ВИЛКИ 66, А НЕ 60»)
#   2 счётчик-число, НЕ год и НЕ версия продукта («Claude 5», «GPT 5.6» - не счётчик)
#   3 title == H1 символ в символ      clickrank.ai 2026: совпадение снижает
#                                      переписывание примерно до 20.6%
#   4 нет брендового хвоста            наши 4 страницы с хвостом: 1.25% против 2.26%
#   5 нет запрещённых формул           /guide-claude-code/ - 369 показов, 0 кликов
#   6 description: длина + первые 90 знаков не дублируют начало title
# 7 капсула ответа 40-60 слов с цифрой или <code> Contently по решению автора
#   8 таблиц не меньше трёх (стадия page)             Contently: таблицы - «очень
#                                                     высокая» надёжность извлечения
#   9 FAQ раскрыт: <details> столько же, сколько <details open> (стадия page)
#
# ТЯЖЕСТЬ. Механизм ровно тот же, что у оси tool-article у structure-visual:
# жёсткий флаг (`--tc-hard`) КОМАНДЕ ГЕЙТА добавляется только когда статья НЕ
# ревизия. Прогон с --revision печатает те же замечания, но выходит кодом 2 =
# WARN: иначе весь старый корпус (28 из 44 страниц без счётчика) встал бы
# красным в первый же день.
#
# 🔴 ПОЧЕМУ ВЕРХ ВИЛКИ 66, А НЕ 60 (правка 23.08.2026).
# Конфликт правил: гейт требовал 51-60, а волна CTR-ретайтла осознанно шила
# 56-66 знаков под ФОРМУЛУ ПОИСКОВОГО ЗАПРОСА (заголовок обязан нести слова так,
# как их набирают). Из-за этого страница краснела ровно в тот момент, когда в
# источник возвращали ЖИВОЙ заголовок, который уже стоит в выдаче и уже собирает
# клики. Ломать работающие заголовки ради гейта нельзя - поднят верх вилки.
# Цифра 66 выведена, а не назначена:
#   • ГДЕ РЕЖЕТ GOOGLE. Десктопная ссылка заголовка обрезается по ПИКСЕЛЯМ (~600px,
#     на практике многоточие появляется уже с 525-535px), а не по знакам. Замер
#     нашего кириллического корпуса в шрифте выдачи (Arial 20px, 163 страницы):
#     средний знак 9.94px, то есть 600px = 60.3 знака. Отсюда и родилась старая
#     верхняя граница 60 - она верна ДЛЯ GOOGLE.
#   • ГДЕ РЕЖЕТ ЯНДЕКС. Видимая часть заголовка - примерно 68 знаков без пробелов
#     и до 74 с пробелами (жирные слова запроса съедают часть). До 66 знаков хвост
#     в выдаче виден целиком.
#   • ЧЕЙ КОРПУС. Клики корпуса приходят из Яндекса (замер per-url Вебмастера);
#     в Google проиндексирована меньшая часть. Верх вилки держим по движку,
#     который реально даёт клики.
# • СВОЙ ЗАМЕР, КОНТРОЛЬ ПО ПОЗИЦИИ (окно в даты запуска.2026, 300 URL с живым title,
#     показов от 50): бакет 4-7 - полоса 51-60 даёт CTR 2.77% при позиции 5.97,
#     полоса 61-66 даёт 5.33% при позиции 6.41. Бакет 7.5-10 - 1.41% при 8.49
#     против 2.01% при 8.19. Длинная полоса НЕ проваливается, она впереди: в ней
#     сидят заголовки, собранные под формулу запроса.
#   • ПОЧЕМУ НЕ ШИРЕ. Выше 66 знаков Яндекс начинает съедать хвост, а собственная
#     выборка там - десяток страниц, законодательствовать не на чем. 66 - живой
#     потолок волны ретайтла, то есть ни один работающий заголовок не ломается.
# Ось не ослаблена: 61-66 печатает МЯГКУЮ справку про обрезку в Google (строка
# `~ soft`), чтобы автор видел размен, а не думал, что 66 знаков бесплатны.
#
# ГДЕ ПОРОГИ. `tools.title_ctr.*` в конфиге скилла (seo-config-reference.yaml),
# читаются тем же `_config.py`, что и пороги structure/visual/cadence. Дефолты
# ниже - страховка на случай, когда конфиг не найден.
# 🔒 Брендовый хвост в РАЗДАВАЕМЫЙ ученикам конфиг не вписан: имя автора берётся
# из личного ~/.config/seo-publish.json (ключ `author_name`) и приезжает в гейт
# флагом `--tc-brand-tail`. У ученика своё имя - у него оно и проверится.

# граница обрезки заголовка в десктопной выдаче Google: 600px при 9.94px на знак
# кириллицы в шрифте выдачи = 60 знаков. НЕ вердикт, только мягкая справка
TC_GOOGLE_CUT = 60

TC_DEFAULTS = {
    "min_len": 51,
    "max_len": 66,
    "desc_min_len": 130,
    "desc_max_len": 165,
    "desc_dup_prefix_chars": 30,
    "capsule_min_words": 40,
    "capsule_max_words": 60,
    # 🔴 ПОРОГ ПЕРЕСЕЧЕНИЯ КАПСУЛЫ И БЫСТРОГО ОТВЕТА (по решению автора, круг 3, R102).
    # Доля значимых слов капсулы, встретившихся в блоке `quick-answer`. Порог
    # 0.45 снят с живых страниц транша, а не назначен: у страницы, где тексты
    # разведены по работе, пересечение 0.12-0.28 (общая терминология темы никуда
    # не денется), у страницы со смысловым дублем - выше 0.5. Считаются только
    # значимые слова длиннее трёх букв, служебные выброшены
    "capsule_qa_overlap_max": 0.45,
    "min_tables": 3,
    "banned_formulas": ["что это и как пользоваться", "все пути",
                        "полное руководство", "полный гайд"],
    "banned_tails": [],
    "version_brands": ["claude", "gpt", "chatgpt", "gemini", "grok", "llama",
                       "qwen", "kimi", "glm", "mistral", "deepseek", "sora",
                       "midjourney", "copilot", "cursor", "windows", "iphone",
                       "ios", "android", "python", "node", "php", "excel",
                       "word", "office", "v", "версия", "версии", "версию"],
}
TC_INT_KEYS = ("min_len", "max_len", "desc_min_len", "desc_max_len",
               "desc_dup_prefix_chars", "capsule_min_words",
               "capsule_max_words", "min_tables")
# дробные пороги живут отдельно: приведение их к int обнулило бы порог
TC_FLOAT_KEYS = ("capsule_qa_overlap_max",)
TC_LIST_KEYS = ("banned_formulas", "banned_tails", "version_brands")
# служебные слова: русское слово после числа = «чего именно N штук», но предлог
# и союз - не предмет счёта. «Kimi 2 для новичка» остаётся версией, «10 команд»
# становится счётчиком
TC_RU_STOP = {"для", "и", "в", "во", "на", "с", "со", "от", "по", "к", "ко",
              "за", "из", "у", "о", "об", "при", "до", "под", "над", "без",
              "же", "ли", "или", "а", "но", "что", "как", "это"}
TC_NUM_RE = re.compile(r"\d+")
TC_WORD_TAIL_RE = re.compile(r"([A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-]*)[\s\-]*\Z")
TC_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
TC_MD_SKIP = (":::", "<!--", "#", "|", ">", "- ", "* ", "![", "<", "{{", "```")


def tc_yaml_cfg(path, tools_dir=None):
    """(конфиг, пояснение). Парсер берём чужой: сначала `_config.py` скилла (он
    сам умеет и PyYAML, и свой мини-YAML), потом PyYAML, потом дефолты."""
    if not existing(path):
        return {}, f"конфиг порогов не найден ({path or 'путь не задан'}), идём на дефолтах"
    if tools_dir and os.path.isdir(tools_dir):
        added = tools_dir not in sys.path
        if added:
            sys.path.insert(0, tools_dir)
        try:
            from _config import load_config  # noqa: E402  (инструмент скилла)
            data = load_config(path)
            if isinstance(data, dict):
                return data, f"пороги из {path} (_config.py скилла)"
        except Exception:  # noqa: BLE001  - парсер опционален, ниже ещё две ветки
            pass
        finally:
            if added and tools_dir in sys.path:
                sys.path.remove(tools_dir)
    try:
        import yaml  # noqa: E402
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data, f"пороги из {path} (PyYAML)"
    except Exception as e:  # noqa: BLE001
        return {}, f"конфиг {path} не разобран ({e}), идём на дефолтах"
    return {}, f"конфиг {path} пуст, идём на дефолтах"


def tc_thresholds(cfg, extra_tails=()):
    """Дефолты, поверх - `tools.title_ctr.*` из конфига, поверх - хвосты извне."""
    th = {k: (list(v) if isinstance(v, list) else v) for k, v in TC_DEFAULTS.items()}
    node = cfg.get("tools") if isinstance(cfg, dict) else None
    node = node.get("title_ctr") if isinstance(node, dict) else None
    if isinstance(node, dict):
        for k, v in node.items():
            if k in th and v is not None:
                th[k] = v
    for k in TC_INT_KEYS:
        try:
            th[k] = int(th[k])
        except (TypeError, ValueError):
            th[k] = TC_DEFAULTS[k]
    for k in TC_FLOAT_KEYS:
        try:
            th[k] = float(th[k])
        except (TypeError, ValueError):
            th[k] = TC_DEFAULTS[k]
    for k in TC_LIST_KEYS:
        v = th[k]
        th[k] = ([str(x).strip() for x in v if str(x).strip()]
                 if isinstance(v, list) else list(TC_DEFAULTS[k]))
    th["banned_tails"] = th["banned_tails"] + [
        str(t).strip() for t in (extra_tails or ()) if str(t).strip()]
    return th


def tc_numbers(title, brands=()):
    """Разметка ВСЕХ чисел title: счётчик / год / версия / длинное число.

    Тут легче всего получить ложный зелёный: «Claude 5» и «GPT 5.6» - имя модели,
    а не обещание «пять штук». Правила отсева, по порядку:
      • 4+ знака            - год (2026) либо просто длинное число, не счётчик;
      • сосед по точке      - «5.6», «4.5» - номер версии;
      • склеено с буквой    - «GPT5», «o3», «v2»;
      • перед числом бренд  - «Claude 5», «Gemini 3»; исключение - когда сразу
                              за числом идёт русское СЛОВО-предмет («Claude 10
                              команд»), тогда это всё-таки счётчик.
    """
    brands = {str(b).lower() for b in (brands or ())}
    out = []
    for m in TC_NUM_RE.finditer(title or ""):
        tok, s, e = m.group(0), m.start(), m.end()
        before, after = title[:s], title[e:]
        shown = tok + ("+" if after[:1] == "+" else "")
        if len(tok) >= 4:
            kind = "год" if re.fullmatch(r"(19|20)\d\d", tok) else "длинное число"
            why = "год в title ничего не обещает" if kind == "год" else "не счётчик"
        elif re.match(r"^[.,]\d", after) or re.search(r"\d[.,]\Z", before):
            kind, why = "версия", "номер версии через точку"
        elif re.search(r"[A-Za-zА-Яа-яЁё]\Z", before):
            kind, why = "версия", "число склеено с названием продукта"
        else:
            w = TC_WORD_TAIL_RE.search(before)
            brand = w.group(1) if w else ""
            nxt = re.match(r"[\s ]*([А-Яа-яЁё]+)", after)
            noun = bool(nxt) and nxt.group(1).lower() not in TC_RU_STOP
            if brand.lower() in brands and not noun:
                kind, why = "версия", f"номер версии продукта «{brand}»"
            else:
                kind, why = "счётчик", "счётчик"
        out.append({"text": shown, "kind": kind, "why": why})
    return out


def tc_words(text):
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


# служебные слова, которые есть в любом русском тексте и о смысловом совпадении
# двух абзацев не говорят ничего
TC_PUSTYE = {
    "что", "как", "это", "для", "или", "все", "уже", "его", "она", "они", "оно",
    "тот", "той", "тех", "там", "тут", "так", "над", "под", "без", "при", "про",
    "если", "чтобы", "когда", "потом", "затем", "тоже", "также", "ещё", "еще",
    "только", "даже", "может", "можно", "надо", "нужно", "быть", "есть", "был",
    "была", "было", "были", "будет", "свой", "своя", "свои", "этот", "эта",
    "эти", "того", "этом", "этой", "вами", "тебя", "себя", "него", "неё",
}


def tc_znachimye(text):
    """Значимые слова текста: длиннее трёх букв, без служебных. Множество."""
    сл = re.findall(r"[а-яёa-z0-9]{4,}", (text or "").lower())
    return {w for w in сл if w not in TC_PUSTYE}


def tc_peresechenie(a, b):
    """(доля, общих, всего). Доля значимых слов ПЕРВОГО текста, встретившихся во
    втором. Считается от первого, а не от объединения: предмет вопроса - «капсулу
    ли пересказали ниже», а не «похожи ли тексты вообще»."""
    са, сб = tc_znachimye(a), tc_znachimye(b)
    if not са:
        return 0.0, 0, 0
    общих = len(са & сб)
    return общих / float(len(са)), общих, len(са)


def tc_norm(s):
    return re.sub(r"[\s ]+", " ", (s or "")).strip()


def tc_strip_tags(s):
    return tc_norm(html.unescape(re.sub(r"<[^>]+>", " ", s or "")))


def tc_read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def tc_front_matter(text):
    """(словарь front-matter, тело). Разбор - PyYAML, иначе скаляры регуляркой."""
    m = TC_FM_RE.match(text or "")
    if not m:
        return {}, text or ""
    block, body = m.group(1), text[m.end():]
    data = {}
    try:
        import yaml  # noqa: E402
        loaded = yaml.safe_load(block)
        if isinstance(loaded, dict):
            data = loaded
    except Exception:  # noqa: BLE001
        data = {}
    if not data:
        for line in block.splitlines():
            mm = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(\S.*?)[ \t]*$", line)
            if mm:
                v = mm.group(2)
                if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
                    v = v[1:-1]
                data.setdefault(mm.group(1), v)
    return data, body


def tc_strip_fences(body):
    """Выключить содержимое ```-блоков, сохранив разбивку на абзацы.

    🔴 Иначе комментарий шелла из листинга («# в ~/.claude/settings.json заменить
    два значения») читается как H1 черновика, и гейт краснеет «title и H1
    расходятся» на статье, у которой H1 в порядке (улика по решению автора: guide-karta).
    """
    out, fence = [], None
    for line in (body or "").splitlines():
        m = re.match(r"^\s*(```|~~~)", line)
        if m:
            tok = m.group(1)
            fence = tok if fence is None else (None if tok == fence else fence)
            out.append("")
            continue
        out.append("" if fence else line)
    return "\n".join(out)


def tc_capsule_md(body):
    """Первый содержательный абзац после H1 черновика (директивы и списки - мимо)."""
    m = re.search(r"^#\s+.+$", body or "", re.M)
    rest = body[m.end():] if m else (body or "")
    for blk in re.split(r"\n\s*\n", rest):
        b = blk.strip()
        if not b or b.startswith(TC_MD_SKIP):
            continue
        return b
    return ""


def tc_fields_draft(draft_path, spec_path=None):
    """Поля черновика. У ЛЕГАСИ-черновика без front-matter источник истины -
    spec.json рядом (см. шапку файла): читаем его, а не краснеем на пустоте."""
    text = tc_read(draft_path)
    fm, body = tc_front_matter(text)
    body = tc_strip_fences(body)
    src = os.path.basename(draft_path)
    title = tc_norm(str(fm.get("title") or ""))
    h1 = tc_norm(str(fm.get("h1") or ""))
    desc = tc_norm(str(fm.get("description") or fm.get("meta_description") or ""))
    md_h1 = ""
    m = re.search(r"^#\s+(.+)$", body, re.M)
    if m:
        md_h1 = tc_norm(m.group(1))
    capsule = tc_capsule_md(body)
    spec = {}
    if spec_path and existing(spec_path):
        try:
            with open(spec_path, encoding="utf-8") as f:
                loaded = json.load(f)
            spec = loaded if isinstance(loaded, dict) else {}
        except (ValueError, OSError):
            spec = {}
    # ЛЕГАСИ-черновик несёт не все поля: у части статей h1/description живут
    # только в spec.json, из которого собирается страница. Добираем ПОКАЗАТЕЛЬНО
    # по одному полю, иначе гейт краснеет «H1 не найден» там, где H1 есть
    добрано = []
    if spec:
        for ключ, значение in (("title", title), ("h1", h1), ("description", desc)):
            if значение:
                continue
            взято = tc_norm(str(spec.get(ключ)
                                or (spec.get("meta_description")
                                    if ключ == "description" else "") or ""))
            if not взято:
                continue
            добрано.append(ключ)
            if ключ == "title":
                title = взято
            elif ключ == "h1":
                h1 = взято
            else:
                desc = взято
    if not capsule and spec.get("lead_html"):
        capsule = tc_strip_tags(str(spec.get("lead_html")))
        добрано.append("капсула")
    if добрано:
        src = f"{src} + spec.json ({', '.join(добрано)})"
    if not h1:
        h1 = md_h1
    capsule_txt = tc_norm(re.sub(r"\]\([^)]*\)", "]", capsule))
    return {"title": title, "h1": h1, "description": desc,
            "capsule": capsule_txt,
            "capsule_code": "`" in capsule,
            "md_h1": md_h1, "source": src, "tables": None,
            "details": None, "details_open": None}


def tc_strip_comments(text):
    """Снять HTML- и JS-комментарии перед подсчётом тегов.

    Баг-фикс по решению автора: шаблон page-template.html несёт постоянный JS-комментарий
    про мобильную пилюлю оглавления, и внутри него текстом упомянут `<details>`
    («открывает ТОТ ЖЕ <details> шторкой»). Наивный re.findall(r"<details\\b", t)
    считал эту прозу восьмым блоком, из-за чего details=8/details_open=7 на КАЖДОЙ
    статье волны с корректно раскрытым FAQ (details_open реально 7 из 7) - гейт
    title-ctr стадии page становился непроходимым системно, не по вине черновика.
    Комментарии из подсчёта тегов исключаем, остальной разбор (title/h1/desc) эта
    функция не трогает - используется только там, где считаются <table>/<details>.
    """
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return text


def tc_fields_page(page_path):
    """Поля СОБРАННОЙ страницы: то, что реально уедет в выдачу."""
    t = tc_read(page_path)
    t_tags = tc_strip_comments(t)
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    title = tc_strip_tags(m.group(1)) if m else ""
    desc = ""
    dm = re.search(r"<meta\b[^>]*name=[\"']description[\"'][^>]*>", t, re.I)
    if dm:
        cm = re.search(r"content=[\"'](.*?)[\"']", dm.group(0), re.S)
        desc = tc_norm(html.unescape(cm.group(1))) if cm else ""
    hm = re.search(r"<h1\b[^>]*>(.*?)</h1>", t, re.S | re.I)
    h1 = tc_strip_tags(hm.group(1)) if hm else ""
    caps_raw = ""
    if hm:
        pm = re.search(r"<p\b[^>]*>(.*?)</p>", t[hm.end():], re.S | re.I)
        caps_raw = pm.group(1) if pm else ""
    # 🔴 БЫСТРЫЙ ОТВЕТ РЯДОМ С КАПСУЛОЙ (по решению автора, круг 3, запись R102). Первый
    # экран статьи несёт ДВА текста подряд: капсулу (первый абзац после H1) и блок
    # `quick-answer`. Оба обязательны по канону, оба пишутся про одно и то же, и
    # шаблон производства ничем не мешает им совпасть по смыслу - дубль поедет в
    # КАЖДУЮ новую статью, пока его не судит гейт. Поэтому текст блока достаётся
    # здесь и дальше сравнивается с капсулой на пересечение слов
    qa_raw = ""
    qm = re.search(r"<(div|section|aside)\b[^>]*class=[\"'][^\"']*quick-answer"
                   r"[^\"']*[\"'][^>]*>(.*?)</\1>", t, re.S | re.I)
    if qm:
        qa_raw = qm.group(2)
    return {"title": title, "h1": h1, "description": desc,
            "capsule": tc_strip_tags(caps_raw),
            "capsule_code": bool(re.search(r"<code\b", caps_raw, re.I)),
            "quick_answer": tc_strip_tags(qa_raw),
            "md_h1": "", "source": os.path.basename(page_path),
            "tables": len(re.findall(r"<table\b", t_tags, re.I)),
            "details": len(re.findall(r"<details\b", t_tags, re.I)),
            "details_open": len(re.findall(r"<details\b[^>]*\bopen\b", t_tags, re.I))}


# 🔴 ТОЧЕЧНАЯ ДОБАВКА - капсула для РЕВИЗИОННОГО ПУТИ (P3, конвейер
# seo-dvizhok-x4, круг 1 фаза 1, по решению автора). `snippet_revise.py` чинит
# сниппет-пакет уже опубликованной страницы (капсулу/служебную строку), но НЕ
# переписывает title/H1 - это отдельно решает `retitle.py` в Фазе 2. Гнать
# такую страницу через полный `tc_findings` (title+H1+description+таблицы)
# избыточно и даёт ложные BLOCKER по осям, которых ревизия не касается. Эта
# функция ПЕРЕИСПОЛЬЗУЕТ ту же вилку (`tc_fields_page`, `tc_thresholds`,
# `tc_words`), не заводит параллельного счёта капсулы.
def tc_capsule_check_page(page_path, cfg=None):
    """Проверка ТОЛЬКО оси «капсула ответа» на собранной странице.

    Возвращает (ok, слов, capsule, detail): ok=False, если капсулы нет
    (первого <p> после H1) или её длина вне вилки `capsule_min_words`-
    `capsule_max_words` (дефолт 40-60, см. TC_DEFAULTS). `detail` - пустая
    строка, когда ok=True."""
    f = tc_fields_page(page_path)
    th = tc_thresholds(cfg or {})
    capsule = f.get("capsule") or ""
    слов = tc_words(capsule)
    if not capsule:
        return False, 0, "", "капсула ответа не найдена: первого абзаца после H1 нет"
    if not th["capsule_min_words"] <= слов <= th["capsule_max_words"]:
        return False, слов, capsule, (
            f"капсула ответа {слов} слов вне вилки {th['capsule_min_words']}-"
            f"{th['capsule_max_words']}")
    return True, слов, capsule, ""


def tc_findings(f, th, stage):
    """(жёсткие замечания, справочные строки). Одна ось - одна строка."""
    bad, info = [], []
    title, h1 = f.get("title") or "", f.get("h1") or ""
    desc, capsule = f.get("description") or "", f.get("capsule") or ""
    nums = tc_numbers(title, th["version_brands"])
    info.append(f"источник полей: {f.get('source')}")
    info.append(f"title ({len(title)} знаков, вилка {th['min_len']}-{th['max_len']}): "
                f"«{title or 'НЕТ'}»")
    info.append("числа в title: " + (", ".join(f"{n['text']} - {n['why']}"
                                               for n in nums) or "нет ни одного"))
    info.append(f"H1: «{h1 or 'НЕТ'}»")
    info.append(f"description ({len(desc)} знаков, вилка {th['desc_min_len']}-"
                f"{th['desc_max_len']}): «{desc[:90] or 'НЕТ'}…»")
    info.append(f"капсула: {tc_words(capsule)} слов "
                f"(вилка {th['capsule_min_words']}-{th['capsule_max_words']}), "
                f"цифра/код внутри: "
                f"{'да' if (re.search(r'[0-9]', capsule) or f.get('capsule_code')) else 'НЕТ'}")

    # 1. длина title
    if not title:
        bad.append("нет title: проверять формулу сниппета нечем "
                   f"(источник {f.get('source')})")
    elif not th["min_len"] <= len(title) <= th["max_len"]:
        bad.append(
            f"длина title {len(title)} знаков вне вилки {th['min_len']}-{th['max_len']}: "
            + ("короче вилки - недоиспользован показ в выдаче"
               if len(title) < th["min_len"]
               else "длиннее вилки - хвост не влезает даже в Яндекс (видно около 68 "
                    "знаков), а Google переписывает title в 76% случаев "
                    "(Zyppy, 80 959 URL)"))
    elif len(title) > TC_GOOGLE_CUT:
        # вердикт НЕ роняем: см. «ПОЧЕМУ ВЕРХ ВИЛКИ 66» в шапке гейта. Автор
        # обязан видеть размен - в Яндексе хвост виден, в Google уже нет
        info.append(
            f"~ soft: title {len(title)} знаков - в Яндексе виден целиком, в Google "
            f"десктопная ссылка режется примерно на 600px (это около "
            f"{TC_GOOGLE_CUT} знаков кириллицей), хвост уедет в многоточие. "
            f"Держать длину выше {TC_GOOGLE_CUT} стоит только ради формулы запроса")
    # 2. счётчик-число
    if title:
        counters = [n for n in nums if n["kind"] == "счётчик"]
        if not counters:
            прочее = ", ".join(f"«{n['text']}» - {n['why']}" for n in nums)
            bad.append(
                "в title нет числа-счётчика (CTR 2.46% против 1.09% в одном бакете "
                "позиций, замер 44 страниц)"
                + (f"; найденные числа счётчиком не считаются: {прочее} - нужно ДРУГОЕ "
                   "число" if прочее else ""))
    # 3. title == H1
    if title and not h1:
        bad.append("H1 не найден: сравнить title с H1 не с чем")
    elif title and title != h1:
        bad.append(f"title и H1 расходятся (совпадение снижает переписывание примерно "
                   f"до 20.6%, clickrank.ai 2026): title «{title}» против H1 «{h1}»")
    elif title and f.get("md_h1") and f["md_h1"] != title:
        info.append(f"~ soft: H1 в теле черновика («{f['md_h1']}») не равен title, но "
                    f"страницу собирают из поля h1 - в выдачу уедет оно")
    # 4. брендовый хвост
    for tail in th["banned_tails"]:
        if tail.lower() in title.lower():
            bad.append(f"брендовый хвост «{tail}» в title: съедает знаки из 60 и не "
                       f"ищется (наши 4 страницы с хвостом - CTR 1.25% против 2.26%)")
    # 5. запрещённые формулы
    for формула in th["banned_formulas"]:
        if формула.lower() in title.lower():
            bad.append(f"запрещённая формула «{формула}» в title (замер r7: страницы с "
                       f"такой формулой дают 0-0.05% CTR)")
    # 6. description
    if not desc:
        bad.append("нет meta description: сниппет соберёт поисковик сам")
    else:
        if not th["desc_min_len"] <= len(desc) <= th["desc_max_len"]:
            bad.append(f"длина description {len(desc)} знаков вне вилки "
                       f"{th['desc_min_len']}-{th['desc_max_len']}")
        head, tnorm = desc.lower()[:90], title.lower()
        общий = 0
        for a, b in zip(head, tnorm):
            if a != b:
                break
            общий += 1
        if tnorm and tnorm in head:
            bad.append("первые 90 знаков description содержат title целиком: мобильная "
                       "выдача режет описание примерно на 90 знаках, туда надо класть "
                       "то, чего в title НЕТ")
        elif общий >= th["desc_dup_prefix_chars"]:
            bad.append(f"description начинается тем же текстом, что и title (совпало "
                       f"{общий} знаков подряд при пороге {th['desc_dup_prefix_chars']}): "
                       f"первые 90 знаков дублируют заголовок")
    # 7. капсула ответа
    слов = tc_words(capsule)
    if not capsule:
        bad.append("капсула ответа не найдена: первого абзаца после H1 нет")
    else:
        if not th["capsule_min_words"] <= слов <= th["capsule_max_words"]:
            bad.append(f"капсула ответа {слов} слов вне вилки {th['capsule_min_words']}-"
                       f"{th['capsule_max_words']} (44.2% цитат ИИ-ответов берутся из "
                       f"первых 30% текста, Contently по решению автора)")
        if not re.search(r"[0-9]", capsule) and not f.get("capsule_code"):
            bad.append("в капсуле ответа нет ни одной цифры и ни одного code-фрагмента: "
                       "определённые формулировки цитируются в 1.8 раза чаще осторожных")
    # 7-бис. СМЫСЛОВОЙ ДУБЛЬ КАПСУЛЫ И БЫСТРОГО ОТВЕТА (круг 3, R102)
    qa = f.get("quick_answer") or ""
    if capsule and qa:
        доля, общих, всего_кап = tc_peresechenie(capsule, qa)
        info.append(f"капсула против быстрого ответа: пересечение {доля:.0%} "
                    f"({общих} значимых слов из {всего_кап}, порог "
                    f"{th['capsule_qa_overlap_max']:.0%})")
        if доля > th["capsule_qa_overlap_max"]:
            bad.append(
                f"КАПСУЛА И БЫСТРЫЙ ОТВЕТ ДУБЛИРУЮТ ДРУГ ДРУГА: пересечение "
                f"{доля:.0%} значимых слов при пороге "
                f"{th['capsule_qa_overlap_max']:.0%}. Это два текста ПОДРЯД на "
                f"первом экране, и читатель получает одну и ту же мысль дважды. "
                f"Развести по работе: капсула отвечает на запрос одной мыслью, "
                f"быстрый ответ даёт СЛЕДУЮЩИЙ шаг - что из этого делать")
    # 8-9. только по собранной странице
    if stage == "page":
        info.append(f"таблиц: {f.get('tables')} (минимум {th['min_tables']}) · "
                    f"details: {f.get('details')}, из них open: {f.get('details_open')}")
        if (f.get("tables") or 0) < th["min_tables"]:
            bad.append(f"таблиц на странице {f.get('tables')} при минимуме "
                       f"{th['min_tables']}: таблицы дают «очень высокую» надёжность "
                       f"извлечения в ИИ-ответы (Contently по решению автора)")
        if (f.get("details") or 0) != (f.get("details_open") or 0):
            bad.append(f"FAQ свёрнут: блоков <details> {f.get('details')}, раскрытых "
                       f"{f.get('details_open')} - свёрнутый по умолчанию ответ рискует "
                       f"не попасть в Нейро и AI Overviews")
    else:
        info.append("· таблицы и раскрытость FAQ проверяются на стадии page "
                    "(в черновике вёрстки ещё нет)")
    return bad, info


def title_ctr_run(adir, stage, draft_path=None, hard=True, yaml_path=None,
                  tools_dir=None, tails=()):
    """(rc, строки вывода). rc: 0 чисто · 1 замечания жёстко · 2 замечания мягко
    (ревизия) · 3 проверять нечего."""
    cfg, note = tc_yaml_cfg(yaml_path, tools_dir)
    th = tc_thresholds(cfg, tails)
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    lines = [f"title-ctr [{stage}] {slug}", f"  · {note}"]
    if stage == "draft":
        target = draft_path or os.path.join(adir, "draft.md")
        if not existing(target):
            lines.append(f"  ОШИБКА: нет черновика {target}")
            return 3, lines
        f = tc_fields_draft(target, os.path.join(adir, "spec.json"))
    else:
        target = os.path.join(adir, "index.html")
        if not existing(target):
            lines.append(f"  ОШИБКА: нет собранной страницы {target}")
            return 3, lines
        f = tc_fields_page(target)
    bad, info = tc_findings(f, th, stage)
    lines += [f"  {x}" for x in info]
    if not bad:
        lines.append("  OK. Формула сниппета в норме по всем осям.")
        return 0, lines
    lines.append(f"  Замечаний: {len(bad)} "
                 f"({'HARD' if hard else 'soft, ревизия старой страницы'})")
    lines += [f"  ! {x}" for x in bad]
    return (1 if hard else 2), lines


# ── гейт cta: маршрут CTA собранной страницы ─────────────────────────────────
#
# ЗАЧЕМ (мандат автора). CTA статьи ведёт в закрытый канал ИМЕННОЙ
# ссылкой ЭТОЙ страницы, а не на общий лендинг оффера: имя инвайта = метка
# атрибуции. Сборщик (article_build.config_tokens) печёт такой адрес сам, но
# страница живёт дольше сборки - её правят волнами, патчами, руками. Гейт
# спрашивает у ГОТОВЫХ БАЙТОВ три вещи: (а) старых маршрутов нет ни одного,
# (б) каждая CTA-ссылка = инвайт ЭТОГО слага по карте, (в) внутреннего жаргона
# в видимом тексте нет.
#
# ГДЕ ЗАКОН. Список допустимых форм адреса (cta.accepted_prefixes), карта
# инвайтов (cta.invites_map) и список запрещённых литералов
# (cta.forbidden_literals) живут в config.md скилла, ОДНИМ экземпляром: второй
# список префиксов в этом файле сделал бы ровно тот дубль, из-за которого
# «гейт зелёный, а канон другой». Разбор конфига и резолвер слага берутся у
# сборщика (article_build) - тот же код, что печёт адрес, его же и проверяет.
#
# ЧТО НЕ СЧИТАЕТСЯ CTA. Ссылки-шаринг (t.me/share/url?...) и публичный канал
# автора в подвале под белый список не подпадают по построению: они не несут
# префикс именного инвайта. Отдельного исключения по имени канала тут нет и не
# нужно - иначе имя канала автора пришлось бы хардкодить в общий файл.
#
# ДВА УРОВНЯ ЖАРГОНА (правка 16.08.2026, дефект С1). §4.6 закона запрещает
# БОЛЬШЕ, чем ловил один плоский список:
#   • УРОВЕНЬ СТРАНИЦЫ (CTA_JARGON) - формы О ПРОДУКТЕ («вечнозелён», «эвергрин»,
#     «смена в записи» с любой границей слова, «VIP» + любая цена, «All
#     Inclusive», «живое мероприятие»): такое неуместно НИГДЕ на странице, это
#     старое позиционирование оффера целиком, не только в промо-блоке. Канон -
#     РЕГЕКС (правка 16.08.2026, скептик раунд-2, дефект О1: плоские литералы
#     пропускали «Онлайн-смена в записи» и «VIP 1990»), см. article_build.
#     CTA_JARGON. Словарь и функция поиска (jargon_hits) - ОДНИ на оба гейта
#     (дефект С2): article_build режет жаргон уже на стадии черновика, здесь
#     только вызов той же функции - второй копии словаря/логики не заводим.
#   • УРОВЕНЬ CTA-БЛОКА (CTA_ONLY_JARGON) - служебные слова конвейера («оффер»,
#     «тариф», «воронка», «трипваер», «лид-магнит», «марафон»): ЛЕГАЛЬНЫ в теле
#     статьи (страница вправе разбирать чужие тарифы - «тарифы Kling», сравнение
#     подписок и т.п.), но выдают внутреннюю кухню, если попадают в САМ призыв
#     к действию. Ищутся ТОЛЬКО внутри блоков с маркером класса cta/btn-cta
#     (cta-final/cta-mid/cta-inline/btn-cta/nav-drop-cta - см. CTA_BLOCK_RE),
#     не по всей странице. Уровня черновика у этого списка нет: markdown-текст
#     ещё не несёт разметки cta/btn-cta, различать «тело vs CTA-блок» нечем
#     (см. пояснение рядом с article_build.gate_no_page_jargon).

CTA_JARGON = article_build.CTA_JARGON
# слова уровня CTA-блока: стемы русских слов ловят падежи подстрокой («тариф»
# -> тарифы/тарифа/тарифный), полные слова - там, где падеж не меняет корень
CTA_ONLY_JARGON = ("оффер", "офер", "тариф", "воронк", "трипваер",
                   "лид-магнит", "марафон")
# ФРАЗЫ СТАРОГО МАРШРУТА. Канал-модель: код-слово - маркер статьи, вход
# открывает КНОПКА. Дефолт блока код-слова сборщик уже печёт правильно, но
# статья вправе написать свой абзац через {{codeword_span}} - и там старая
# формула «по нему открывается вход» живёт дальше (по снимку корпуса по решению автора -
# 40 живых страниц). Текст видит только этот гейт, поэтому фразы ловятся здесь
CTA_BANNED_PHRASES = ("по нему открывается вход", "по код-слову открывается",
                      "введи код-слово", "назови слово боту")
CTA_SHARE_MARK = "t.me/share"
_HREF_RE = re.compile(r'href\s*=\s*["\']([^"\']+)["\']')
_SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
# блок промо: тег с классом, несущим слово «cta» (word-boundary ловит и
# cta-final/cta-mid/cta-inline, и btn-cta/nav-drop-cta - «-» не входит в \w,
# значит служит границей слова с обеих сторон). Обратная ссылка \1 закрывает
# ТЕМ ЖЕ тегом: вложенных одноимённых тегов внутри промо-блоков в шаблоне нет
# (cta-final/cta-mid/cta-inline несут только <p>/<h3>/<a> без вложенных копий)
CTA_BLOCK_RE = re.compile(
    r'<(section|aside|div|nav|a)\b[^>]*\bclass\s*=\s*"[^"]*\bcta\b[^"]*"[^>]*>'
    r'(.*?)</\1\s*>', re.S | re.I)
# парити количества (р9, по решению автора) - счёт по <article>…</article>, НЕ по
# странице целиком: правый рельс (aside.rail, канон Д.2) несёт СВОЙ
# .btn-cta «На <твой-продукт>» вне статьи, он есть на КАЖДОЙ странице независимо
# от директив черновика - если считать по всей странице, этот рельсовый
# блок постоянно сдвигает счёт и парити никогда не сойдётся. Калибровка -
# guide-neyroset-otzyvy/index.html: 2 директивы (mid+final) -> 2 .btn-cta
# внутри <article>, 3-й .btn-cta - рельс, вне <article>. codeword_block
# (дефолт article_build.config_tokens) - это <p><span class="kw">…</span>
# …</p> без своего <a>, второго btn-cta не добавляет.
_ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article\s*>", re.S | re.I)
_BTN_CTA_RE = re.compile(r'class\s*=\s*"[^"]*\bbtn-cta\b[^"]*"', re.I)


def codeword_findings(page):
    """Блока код-слова на странице быть не должно (решение владельца).

    Читатель статьи приходит из Яндекса и Google: ни карусели, ни слова он не
    видел, а абзац «Код-слово этой статьи - СВОД» стоял ровно в точке решения
    «жать кнопку или уйти». Вход открывает КНОПКА, слово никуда не вводится -
    блок был чистым шумом. Считаем по видимому тексту страницы плюс по полному
    открывающему тегу `<span class="kw">` ВНУТРИ CTA-блоков: в листинге кода тот
    же класс живёт легально (подсветка синтаксиса), поэтому за пределами промо
    его не трогаем.
    """
    bad = []
    видимый = _TAG_RE.sub(" ", _SCRIPT_RE.sub(" ", page or ""))
    видимый = re.sub(r"\s+", " ", видимый)
    низ = видимый.lower()
    for ph in article_build.CODEWORD_PHRASES:
        n = низ.count(ph)
        if n:
            i = низ.find(ph)
            bad.append(f"блок код-слова на странице («{ph}» ×{n}): "
                       f"…{видимый[max(0, i - 40):i + 120]}… - убран из статей "
                       f"по решению автора, читатель приходит из поиска и слова не знает")
    for m in article_build.CODEWORD_PROSE_RE.finditer(видимый):
        bad.append(f"приглашение по код-слову в тексте страницы: «{m.group(0)}» - "
                   f"вход открывает кнопка, слово читателю из поиска ничего не говорит")
    for m in CTA_BLOCK_RE.finditer(page or ""):
        if article_build.CODEWORD_MARK in m.group(2):
            bad.append("разметка код-слова <span class=\"kw\"> внутри CTA-блока - "
                       "блок код-слова из статей убран")
    return bad


def cta_parity(adir, page):
    """(жёсткие замечания, справочные строки) - счёт директив/ключей/блоков CTA.

    Живой дефект р9 (по решению автора): article_build.build_spec() шёл циклом ТОЛЬКО
    по sections = split_sections(body)[1] - всё, что стоит ДО первого H2
    (пролог, «pre»), директивы не обходило вовсе. Лид-блок ниже строился через
    md_blocks(pre) с фильтром «if k != "directive"», который директивный блок
    молча выбрасывал. Итог: канонический ":::cta place=compact" (его место
    по канону - НАЧАЛО страницы) в прологе черновика улетал в никуда -
    lead-magnit-work/guide-kak-sdelat-neyroset/draft.md:40 несла директиву,
    spec.json не получил ключ cta_compact, index.html не получил блока, а
    cta_findings() выше был зелёным - она сверяет МАРШРУТ (адрес/жаргон/
    формулы) существующих CTA, а не их КОЛИЧЕСТВО. Эта функция считает три
    независимых источника одного факта и требует их равенства.
    """
    bad, info = [], []
    draft_path = os.path.join(adir, "draft.md")
    spec_path = os.path.join(adir, "spec.json")

    n_draft = None
    if existing(draft_path):
        raw = open(draft_path, encoding="utf-8").read()
        try:
            fm, body = article_build.parse_front_matter(raw)
        except article_build.BuildError:
            fm, body = None, raw
        # только черновик ТЕКУЩЕГО контракта (engine: article_build) - реальный
        # источник этой сборки. Легаси-схема (engine отсутствует, статьи старой
        # волны - см. шапку article_build.py) - НЕ то, из чего собран этот
        # index.html/spec.json, сверять её директивы с готовой страницей нечестно
        if isinstance(fm, dict) and str(fm.get("engine", "")).strip() == article_build.ENGINE_MARK:
            n_draft = 0
            for kind, blines in article_build.md_blocks(body.split("\n")):
                if kind != "directive":
                    continue
                name, _attrs, _dbody = article_build.parse_directive(blines)
                if name == "cta":
                    n_draft += 1

    n_spec = None
    if existing(spec_path):
        try:
            spec_data = json.load(open(spec_path, encoding="utf-8"))
        except Exception as e:
            info.append(f"· парити CTA: spec.json не читается как JSON ({e}) - "
                        "сверку по нему пропускаю")
            spec_data = None
        if isinstance(spec_data, dict):
            n_spec = sum(1 for k in ("cta_compact", "cta_mid", "cta_final")
                        if spec_data.get(k))

    m = _ARTICLE_RE.search(page or "")
    article_html = m.group(1) if m else (page or "")
    n_page = len(_BTN_CTA_RE.findall(article_html))

    hint = " · ".join(x for x in (
        (f"в draft {n_draft}" if n_draft is not None else None),
        (f"в spec {n_spec}" if n_spec is not None else None),
        f"в page {n_page}",
    ) if x)
    info.append(f"· парити количества CTA ({hint})"
                + ("" if n_draft is not None else " - draft.md нет или он "
                   "легаси-схемы (без «engine: article_build»), сверяю то, что "
                   "есть"))

    counts = [x for x in (n_draft, n_spec, n_page) if x is not None]
    if len(set(counts)) > 1:
        детали = ", ".join(x for x in (
            (f"в draft {n_draft}" if n_draft is not None else None),
            (f"в spec {n_spec}" if n_spec is not None else None),
            f"в page {n_page}",
        ) if x)
        bad.append(f"расхождение количества CTA: {детали} - директива есть, а "
                   "ключа в spec.json/блока на странице нет (или наоборот): "
                   "молчаливая потеря CTA (класс дефекта р9 по решению автора - "
                   "директива до первого H2 терялась при сборке)")
    return bad, info


def cta_visible_text(page):
    """Видимый текст страницы: без скриптов, стилей, тегов и сущностей."""
    t = _SCRIPT_RE.sub(" ", page or "")
    t = _TAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def cta_block_texts(page):
    """[видимый текст] КАЖДОГО блока с маркером класса cta/btn-cta в разметке.

    Уровень CTA-блока (см. ДВА УРОВНЯ ЖАРГОНА выше) не читает страницу
    целиком - только то, что реально стоит внутри промо-разметки, иначе
    легальное упоминание «тарифов» стороннего сервиса в теле статьи красило
    бы гейт так же, как жаргон в самом призыве к действию.
    """
    return [cta_visible_text(m.group(2)).strip() for m in CTA_BLOCK_RE.finditer(page or "")]


def cta_findings(page, slug, cfg):
    """(жёсткие замечания, справочные строки) по собранной странице."""
    bad, info = [], []
    lits = cfg.get("forbidden_literals") or []
    prefixes = cfg.get("accepted_prefixes") or []
    invites = cfg.get("invites")

    # (а) запрещённые литералы - по ВСЕМ байтам страницы, не только по ссылкам
    info.append(f"запрещённых литералов в config: {len(lits)}"
                + (f" ({' · '.join(lits)})" if lits else " - проверять нечего"))
    for lit in lits:
        # формы литерала (без хвостового слеша, url-encoded) - у сборщика, один
        # закон на движок и на гейт
        hits = article_build.forbidden_hits(page, lit)
        if hits:
            формы = sorted({f for f, _ in hits})
            i = hits[0][1]
            bad.append(f"запрещённый литерал «{lit}» на странице ×{len(hits)} "
                       f"(формы: {' · '.join(формы)}): "
                       f"…{re.sub(r'[ ]+', ' ', page[max(0, i - 60):i + 60])}…")

    # (б) адреса CTA
    hrefs = [html.unescape(h).strip() for h in _HREF_RE.findall(page)]
    share = [h for h in hrefs if CTA_SHARE_MARK in h]
    # что считать CTA-ссылкой: адрес по белому списку форм из config. Список
    # пуст, но карта задана - CTA считаем по самому инвайту (иначе гейт у такого
    # автора краснел бы всегда, ничего при этом не проверив)
    if prefixes:
        cta = [h for h in hrefs if any(p in h for p in prefixes) and CTA_SHARE_MARK not in h]
    elif invites is not None:
        ссылки = set(invites.values())
        cta = [h for h in hrefs if h.rstrip("/") in {x.rstrip("/") for x in ссылки}]
    else:
        cta = []
    tme_прочие = [h for h in hrefs if "t.me/" in h and h not in cta and h not in share]
    info.append(f"ссылок на странице: {len(hrefs)} · CTA по белому списку: {len(cta)} "
                f"· шаринг: {len(share)} · прочие t.me (канал автора и т.п.): "
                f"{len(tme_прочие)}")
    if not prefixes:
        info.append("· cta.accepted_prefixes в config пуст - форму адреса CTA не проверяю")
    if invites is None:
        info.append("· cta.invites_map в config не задан - сверку «адрес = инвайт слага» "
                    "НЕ проводил (у автора без именных инвайтов это штатно)")
    else:
        try:
            invite = article_build.invite_for_slug(cfg, slug)
        except article_build.BuildError as e:
            invite = None
            bad.append(f"слаг вне карты инвайтов: {e}")
        if invite:
            info.append(f"инвайт слага по карте: {invite}")
            if not cta:
                bad.append("на странице нет ни одной CTA-ссылки на именной инвайт "
                           f"(ждём {invite}): статья не ведёт в канал вовсе")
            for h in sorted(set(cta)):
                if h.rstrip("/") != invite.rstrip("/"):
                    bad.append(f"CTA-ссылка «{h}» не равна инвайту этой страницы "
                               f"({invite}): именной инвайт = метка атрибуции, чужой "
                               f"адрес ломает замер и заводит читателя не туда")

    # (в) жаргон в ВИДИМОМ тексте - канон и поиск ОДНИ на оба гейта (О1, С2):
    # article_build.jargon_hits читает те же регекс-формы, что и черновик
    text = cta_visible_text(page)
    low = text.lower()
    by_pattern = {}
    for pat, found, i in article_build.jargon_hits(text):
        by_pattern.setdefault(pat, []).append((found, i))
    for occs in by_pattern.values():
        found0, i0 = occs[0]
        bad.append(f"внутренний жаргон «{found0}» в тексте страницы ×{len(occs)}: "
                   f"…{text[max(0, i0 - 60):i0 + 60]}…")

    # (г) фразы старого маршрута: «вход открывает слово» вместо «вход открывает кнопка»
    for ph in CTA_BANNED_PHRASES:
        n = low.count(ph)
        if n:
            i = low.find(ph)
            bad.append(f"фраза старого маршрута «{ph}» в тексте страницы ×{n}: "
                       f"код-слово - маркер статьи, вход открывает КНОПКА выше: "
                       f"…{text[max(0, i - 60):i + 60]}…")

    # (д) служебный жаргон ТОЛЬКО внутри блоков cta/btn-cta (С1) - в теле
    # статьи «оффер»/«тариф»/«воронка» легальны (страница вправе разбирать
    # чужие тарифы), в самом призыве к действию - выдают внутреннюю кухню
    блоки = cta_block_texts(page)
    info.append(f"CTA-блоков по маркеру класса (cta/btn-cta): {len(блоки)}"
                + (f" · слов служебного жаргона в списке: {len(CTA_ONLY_JARGON)}"
                   if блоки else " - жаргон уровня CTA-блока проверять негде"))
    for идx, блок in enumerate(блоки):
        low_блок = блок.lower()
        for w in CTA_ONLY_JARGON:
            n = low_блок.count(w.lower())
            if n:
                i = low_блок.find(w.lower())
                bad.append(f"служебный жаргон «{w}» ВНУТРИ CTA-блока №{идx + 1} ×{n} "
                           f"(в теле статьи слово легально, в призыве к действию - "
                           f"выдаёт внутреннюю кухню): "
                           f"…{блок[max(0, i - 60):i + 60]}…")
    return bad, info


def cta_run(adir, config_path=None, page_path=None):
    """(rc, строки). rc: 0 чисто · 1 замечания · 2 ошибка входа · 3 проверять нечем."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    target = page_path or os.path.join(adir, "index.html")
    lines = [f"cta [page] {slug}"]
    if not existing(target):
        lines.append(f"  ОШИБКА: нет собранной страницы {target}")
        return 2, lines
    try:
        cfg = article_build.load_config(config_path)
    except article_build.BuildError as e:
        lines.append(f"  ОШИБКА: config.md скилла не читается: {e}")
        return 2, lines
    lines.append(f"  · закон CTA из {cfg['path']}")
    page = open(target, encoding="utf-8").read()
    bad, info = cta_findings(page, slug, cfg)
    lines += [f"  {x}" for x in info]
    # парити количества (р9, по решению автора) - независимая ось от литералов/карты
    # инвайтов выше: гоняется ВСЕГДА, даже если секция cta в config.md пуста,
    # потому что молчаливая потеря CTA-директивы - брак сборки, а не вопрос
    # закона конкретного автора
    parity_bad, parity_info = cta_parity(adir, page)
    lines += [f"  {x}" for x in parity_info]
    bad += parity_bad
    # блок код-слова убран из статей по решению автора: ловим его на СОБРАННОЙ странице
    # тоже, а не только в черновике - страницу правят и руками
    bad += codeword_findings(page)
    config_empty = not (cfg.get("forbidden_literals") or cfg.get("accepted_prefixes")
                        or cfg.get("invites"))
    if config_empty and not bad:
        lines.append("  ГЕЙТ НИЧЕГО НЕ ПРОВЕРИЛ: в config.md пуста вся секция cta "
                     "(invites_map / accepted_prefixes / forbidden_literals). "
                     "Зелёным это считать нельзя")
        return 3, lines
    if not bad:
        lines.append("  OK. Маршрут CTA, литералы, жаргон, формулы код-слова и "
                     "количество CTA чисты.")
        return 0, lines
    lines.append(f"  Замечаний: {len(bad)}")
    lines += [f"  ! {x}" for x in bad]
    return 1, lines


# ── ЕДИНЫЙ РАЗБОР СТРАНИЦЫ: парсер image_health.py, а не свои регулярки ──────
#
# 🔴 ЗАЧЕМ (круг 2, по решению автора). Первый круг барьера картинок родил ДВА разбора
# HTML: настоящий (html.parser) в чекере `image_health.py` и второй, наскоро
# написанный регулярками, здесь. Скептик пробил второй насквозь пятью дырами
# ОДНОГО корня - регулярка не умеет читать разметку:
#   1. `<(?:img|source)\b[^>]*>` обрывает тег на первом '>' ВНУТРИ значения
#      атрибута. `<img alt="меню Файл > Открыть" src="assets/x.webp">` - и src
#      не виден вовсе; на странице гайда по интерфейсу такой alt напрашивается.
# Проверено по решению автора: imgref_page_refs на этой строке возвращал [] и гейт
#      печатал OK на комплекте <picture> со СМЕШАННОЙ раскладкой
#   2. `\bsrc=` матчит `data-src=` (дефис не словесный символ), а `.search()`
#      берёт ПЕРВОЕ совпадение: на lazy-load разметке судился плейсхолдер.
#      Значение без кавычек (`src=assets/x.webp`) не видно вообще
#   3. `srcset` резался `split(",")`: `data:`-URI и подписанный CDN-адрес с
#      запятой внутри давали ДВЕ фантомные ссылки и ложную «смешанную раскладку»
#   4. `<img>` внутри HTML-комментария считался настоящей ссылкой
#   5. `video[poster]` и `url()` в CSS не собирались вовсе
# Все пять закрываются ОДНИМ ходом: разбор берётся из image_health.py, где он
# написан на html.parser и покрыт селфтестом. Второго закона разбора в системе
# нет - здесь только ПОДКЛАСС, который добавляет две вещи, чекеру не нужные:
# номер комплекта <picture> (без него не судить смешанную раскладку) и
# `link[rel=preload][as=image]` (чекер его не собирает).
#
# ЕСЛИ ПАРСЕРА НЕТ. Молчаливого зелёного не будет: гейты, которым нечем читать
# страницу, отдают rc=3 = ERROR с честной строкой «разбирать нечем» и списком
# просмотренных путей. Сам article_gates при этом не падает - импорт мягкий,
# остальные ~40 гейтов работают как работали.
IMGREF_PARSER_PATH = None    # откуда взят разбор (для строки отчёта)
IMGREF_PARSER_WHY = ""       # почему не взят, если не взят
IMGREF_PARSER_TRIED = []     # какие пути просмотрены


def _imgref_load_parser_module():
    """Мягко подгружает image_health.py. Возврат: модуль или None.

    Порядок: переменная окружения IMAGE_HEALTH_PY (файл или каталог) →
    канонный каталог инструментов lead-magnit → сосед по каталогу шаблона.
    автор-специфики нет: все три - универсальные формы, домен/слаг/код тут
    не участвуют.
    """
    global IMGREF_PARSER_PATH, IMGREF_PARSER_WHY, IMGREF_PARSER_TRIED
    env = (os.environ.get("IMAGE_HEALTH_PY") or "").strip()
    cands = []
    if env:
        e = os.path.expanduser(env)
        cands.append(e if e.lower().endswith(".py")
                     else os.path.join(e, "image_health.py"))
    cands.append(os.path.join(os.path.expanduser(FALLBACK["lm_tools"]),
                              "image_health.py"))
    cands.append(os.path.join(HERE, "image_health.py"))
    IMGREF_PARSER_TRIED = list(dict.fromkeys(cands))
    беды = []
    for p in IMGREF_PARSER_TRIED:
        if not os.path.isfile(p):
            continue
        try:
            spec = importlib.util.spec_from_file_location("lm_image_health", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:                                    # noqa: BLE001
            беды.append(f"{p}: не загрузился ({type(e).__name__}: {e})")
            continue
        нет = [имя for имя in ("ImageRefParser", "parse_srcset")
               if not hasattr(mod, имя)]
        if нет:
            беды.append(f"{p}: в модуле нет {', '.join(нет)}")
            continue
        IMGREF_PARSER_PATH = p
        return mod
    IMGREF_PARSER_WHY = ("; ".join(беды) if беды
                         else "файла нет ни по одному из путей")
    return None


IH = _imgref_load_parser_module()
_IMGREF_CLASS = None


class ImgrefParserMissing(RuntimeError):
    """Разбирать страницу нечем: image_health.py не найден или негоден."""


def imgref_parser_note():
    """Строка отчёта: чем именно разобрана страница (улика, а не обещание).

    Ветку выбирает ЖИВОЕ состояние модуля, а не запомненный путь: иначе после
    сбоя загрузки в отчёте осталась бы стоять бодрая строка про парсер, которого
    в руках уже нет.
    """
    if IH is not None and IMGREF_PARSER_PATH:
        return f"разбор страницы: html.parser из {IMGREF_PARSER_PATH}"
    почему = IMGREF_PARSER_WHY or "модуль разбора недоступен"
    просмотрено = (f"; просмотрено: {', '.join(IMGREF_PARSER_TRIED)}"
                   if IMGREF_PARSER_TRIED else "")
    return f"разбор страницы: НЕЧЕМ ({почему}){просмотрено}"


def _imgref_parser_class():
    """ПОДКЛАСС ImageRefParser из image_health.py. None - модуля нет.

    Добавляет ровно ОДНУ вещь, которой у чекера нет и быть не должно:
      · номер комплекта <picture> у каждой ссылки - им судится смешанная
        раскладка (промах <source> не откатывается на <img> именно внутри
        комплекта)
    Мета-картинки (og:image/twitter:image) и фавиконки отбрасываются здесь же:
    элементами страницы они не являются, их судят frame-provenance и сверка с
    продом (та же граница охвата, что записана в шапке гейта image-refs).

    БЫЛО И ПОЧЕМУ УБРАНО (круг 3, по решению автора). Раньше подкласс САМ добавлял
    `link[rel=preload][as=image]`, потому что чекер его не собирал. Теперь
    собирает (и href, и каждый кандидат imagesrcset), а вместе с ним `a[href]`
    полноразмерной картинки лайтбокса. Своё добавление здесь стало ДУБЛЕМ:
    на странице с одним preload гейт печатал 5 ссылок вместо 4. Закон разбора
    остаётся один, и живёт он в image_health.py - здесь только надстройка.
    """
    global _IMGREF_CLASS
    if _IMGREF_CLASS is not None:
        return _IMGREF_CLASS
    if IH is None:
        return None

    class _Разбор(IH.ImageRefParser):
        # вне охвата гейта статьи: мета-теги и общесайтовые иконки
        ВНЕ_ОХВАТА = ("meta-og-image", "meta-twitter-image", "link-icon")
        # kind чекера -> (как назвать тег в замечании, какой это атрибут)
        ИМЕНА = {
            "img-src": ("img", "src"),
            "img-srcset": ("img", "srcset"),
            "source-src": ("source", "src"),
            "source-srcset": ("source", "srcset"),
            "video-poster": ("video", "poster"),
            "link-preload": ("link[preload]", "href"),
            "link-preload-srcset": ("link[preload]", "imagesrcset"),
            "a-href": ("a", "href"),
            "style-attr-url": ("style=", "url()"),
            "style-block-url": ("<style>", "url()"),
        }

        def __init__(self):
            self._pic_no = 0
            self._pic_cur = None
            self._pic_depth = 0
            self.page_refs = []          # [(сырой_url, тег, атрибут, №picture)]
            IH.ImageRefParser.__init__(self)

        def _add(self, kind, raw):
            было = len(self.refs)
            IH.ImageRefParser._add(self, kind, raw)
            if kind in self.ВНЕ_ОХВАТА:
                return
            тег, attr = self.ИМЕНА.get(kind, (kind, "src"))
            for r in self.refs[было:]:
                self.page_refs.append((r.raw, тег, attr, self._pic_cur))

        def handle_starttag(self, tag, attrs):
            if tag == "picture":
                if self._pic_depth == 0:
                    self._pic_no += 1
                    self._pic_cur = self._pic_no
                self._pic_depth += 1
            было_refs = len(self.refs)
            IH.ImageRefParser.handle_starttag(self, tag, attrs)
            # СТРАХОВКА СОВМЕСТИМОСТИ, а не второй закон разбора. Свежий чекер
            # preload собирает сам - тогда эта ветка молчит (иначе ссылка ушла бы
            # в отчёт дважды). Рядом может лежать чекер ПРОШЛОЙ версии (машина
            # ученика, релей до синка) - там preload не собирается вовсе, и гейт
            # обязан видеть его всё равно: битый preload-хиро = дыра в первом
            # экране. Судим по ФАКТУ добавления, не по версии файла.
            if tag == "link":
                уже = any(r.kind == "link-preload" for r in self.refs[было_refs:])
                a = {(k or "").lower(): (v or "") for k, v in attrs}
                rels = set((a.get("rel") or "").lower().split())
                if (not уже
                        and "preload" in rels
                        and (a.get("as") or "").strip().lower() == "image"
                        and a.get("href") is not None):
                    self._add("link-preload", a["href"])

        def handle_startendtag(self, tag, attrs):
            IH.ImageRefParser.handle_startendtag(self, tag, attrs)
            self._закрыть_picture(tag)

        def handle_endtag(self, tag):
            IH.ImageRefParser.handle_endtag(self, tag)
            self._закрыть_picture(tag)

        def _закрыть_picture(self, tag):
            if tag == "picture" and self._pic_depth > 0:
                self._pic_depth -= 1
                if self._pic_depth == 0:
                    self._pic_cur = None

    _IMGREF_CLASS = _Разбор
    return _IMGREF_CLASS


def imgref_parse_page(html_text):
    """[(сырой_url, тег, атрибут, №picture)] по всей странице. Один разбор на все
    гейты картинок этого файла. Кидает ImgrefParserMissing, если разбора нет."""
    cls = _imgref_parser_class()
    if cls is None:
        raise ImgrefParserMissing(IMGREF_PARSER_WHY or "image_health.py не найден")
    p = cls()
    p.feed(html_text or "")
    p.close()
    return list(p.page_refs)


# ── гейт assets-exist: локальные ассеты собранной страницы физически на диске ─
#
# ЗАЧЕМ (дыра скептика волны р9, по решению автора). Собранный index.html свободно
# ссылается на assets/thumb-*.webp, которых на диске нет - ни один гейт стадии
# page это не ловил (structure-check/title-ctr/strip-notes/cta читают ТЕКСТ и
# РАЗМЕТКУ, не ходят на диск за каждым файлом), битые картинки уезжали бы в
# прод зелёным корпусом. Живой пример: guide-ii-perevodchik тянул 3 таких
# thumb-файла при полностью зелёных гейтах (проверено `ls`, все три MISSING).
#
# ЧТО СЧИТАЕТ ЛОКАЛЬНЫМ. img/source (src + srcset) и href preload-картинок
# (rel=preload as=image) - ТОЛЬКО относительные пути вида assets/… внутри
# каталога СТАТЬИ. Абсолютные http(s)/protocol-relative/data: URL и КОРНЕВЫЕ
# пути (/assets/fonts/…, /favicon.png) сюда не идут - это общесайтовые
# ресурсы (шрифты, фавикон) ИЛИ ссылки на другие страницы сайта, гейт статьи
# им не судья.
# 🔴 РЕГУЛЯРОК ПО ТЕГАМ ЗДЕСЬ БОЛЬШЕ НЕТ (круг 2, по решению автора). Пять штук -
# ASSETS_IMG_TAG_RE, ASSETS_SOURCE_TAG_RE, ASSETS_PRELOAD_TAG_RE,
# ASSETS_HREF_RE, ASSETS_AS_IMAGE_RE - удалены вместе с IMGREF_TAG_RE и
# IMGREF_PICTURE_RE: именно они дали пять дыр скептика. Разбор идёт через
# imgref_parse_page (парсер image_health.py). Если понадобится «быстренько
# достать атрибут регуляркой» - не надо: так и появился второй разбор.
#
# Пережившие две регулярки ниже работают на ОДНОЙ УЖЕ ВЫРЕЗАННОЙ строке тега в
# гейте frame-provenance (prov_tag_refs), где разбор позиционный - он режет
# страницу по спанам .vizblock/<figure>. Это отдельный гейт и отдельная задача;
# переводить и его на общий парсер - работа со своим замером, не этот круг.
ASSETS_SRC_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.I)
ASSETS_SRCSET_RE = re.compile(r'\bsrcset=["\']([^"\']+)["\']', re.I)


def assets_local_refs(html_text):
    """Дедуплицированный список ЛОКАЛЬНЫХ путей ассетов (относительно каталога
    статьи), на которые ссылается собранная страница. Порядок первого
    появления, дубли схлопнуты.

    Разбор - ОБЩИЙ (imgref_parse_page, парсер image_health.py). Своих регулярок
    здесь больше нет: `\\bsrc=` матчил `data-src=` и брал только первое
    совпадение, а `[^>]*>` рвал тег на '>' внутри alt (круг 2, по решению автора).
    """
    raw = [u for u, _, _, _ in imgref_parse_page(html_text)]

    seen, local = set(), []
    for u in raw:
        u = html.unescape(u).strip()
        if not u or u.startswith(("http://", "https://", "//", "data:", "/")):
            continue  # абсолютный URL / общесайтовый корневой путь - не наш файл
        u = u.split("#", 1)[0].split("?", 1)[0]
        if not u or u in seen:
            continue
        seen.add(u)
        local.append(u)
    return local


def assets_exist_run(adir, page_path=None):
    """(rc, строки). rc: 0 - все локальные ассеты физически на диске ·
    1 - хотя бы один отсутствует (поимённый список) · 3 - страницы нечем
    проверять (нет index.html ИЛИ нет разбора: image_health.py не найден)."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    lines = [f"assets-exist [page] {slug}"]
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 3, lines
    try:
        refs = assets_local_refs(tc_read(page))
    except ImgrefParserMissing:
        # молчаливого зелёного не будет: разбирать нечем = ERROR, не PASS
        lines.append(f"  ОШИБКА: {imgref_parser_note()}")
        return 3, lines
    # ПУСТОЙ атрибут: своего файла у него нет, но это не «ссылки нет» - это
    # битая картинка, которую браузер уже нарисует дырой. Раньше такое значение
    # просто выпадало из разбора, и страница выглядела как страница без ссылки.
    try:
        пустые = imgref_empty_refs(tc_read(page))
    except ImgrefParserMissing:
        пустые = []
    lines.append(f"  локальных ссылок на ассеты (img/source src+srcset, "
                f"href preload-картинок, дубли схлопнуты): {len(refs)}"
                + (f" · ПУСТЫХ атрибутов: {len(пустые)}" if пустые else ""))
    missing = [u for u in refs if not os.path.isfile(os.path.join(adir, u))]
    if not missing and not пустые:
        lines.append("  OK. Все локальные ассеты страницы физически на диске.")
        return 0, lines
    for тег, attr, pic in пустые:
        где = f" (внутри <picture> №{pic})" if pic is not None else ""
        lines.append(f"  ! {тег}[{attr}]{где}: ПУСТОЙ атрибут - файла под ним нет "
                     f"и быть не может, браузер запросит саму страницу вместо "
                     f"картинки")
    if missing:
        lines.append(f"  Отсутствует на диске: {len(missing)}")
        lines += [f"  ! {u} -> нет файла {os.path.join(adir, u)}" for u in missing]
    return 1, lines


# ── гейт image-refs: битая картинка - ссылка не резолвится в РАСКЛАДКЕ прода ─
#
# 🔴 ЗАЧЕМ (инцидент по решению автора). Владелец открыл свою же статью из поиска и
# увидел на месте хиро битую картинку. Замер живого корпуса: 43 битые ссылки на
# ДВУХ страницах, все одной породы - относительный путь `assets/<slug>/имя.webp`
# в `img[srcset]` и `source[srcset]`, при том что файлы физически лежат в
# КОРНЕВОМ `/assets/<slug>/` и по абсолютному пути отдают 200. Страница живёт по
# адресу-каталогу, поэтому относительный путь резолвится в
# `/<slug>/assets/<slug>/имя.webp` = 404.
#
# ПОЧЕМУ ЭТО НЕ ПОЙМАЛ НИ ОДИН ГЕЙТ. У assets-exist контракт «локальный файл
# физически на диске», и он НАМЕРЕННО пропускает всё, что начинается со слэша
# (общесайтовые ресурсы - шрифт, фавикон, аватар автора, превьюшки соседей: им
# статья не судья). То есть ось «а по какому адресу эта ссылка попадёт НА ПРОДЕ»
# не проверял никто: файл на диске есть, значит зелено.
#
# ДВЕ РАСКЛАДКИ ПРОДА (обе живут в ftp_publish.py, шапка файла):
#   КАТАЛОЖНАЯ - каталог статьи уезжает целиком в /<slug>/, картинки внутри:
#                относительный `assets/имя.webp` -> /<slug>/assets/имя.webp ✅
#   ПЛОСКАЯ    - страница отдельно, картинки в ОБЩЕМ каталоге /<assets_remote>/
#                (по умолчанию /assets/<slug>/): верен ТОЛЬКО корневой путь
#                `/assets/<slug>/имя.webp`, относительный в этой раскладке битый
# Раскладка - свойство ПРОГОНА, а не статьи, поэтому приходит параметром
# (--page-layout / --assets-remote). Дефолт `auto`: раскладка выводится из самой
# страницы, и гейт судит ВНУТРЕННЮЮ НЕПРОТИВОРЕЧИВОСТЬ - именно ею дефект и был.
#
# ГЛАВНОЕ ПРАВИЛО, РАДИ КОТОРОГО ГЕЙТ И ЗАВЕДЁН: СМЕШАННАЯ РАСКЛАДКА ВНУТРИ
# ОДНОГО <picture>. Дословный вид дефекта:
#   <source srcset="assets/<slug>/hero-720.webp 720w, ...">   ← относительный
#   <img src="/assets/<slug>/hero.jpg">                        ← корневой
# Браузер выбирает <source> ПЕРВЫМ и на промахе НЕ откатывается на <img>: jpeg по
# живому абсолютному пути рядом, а читатель видит битый кадр. Поэтому комплект
# одной картинки обязан быть в ОДНОЙ раскладке, и это FAIL, а не замечание:
# битая картинка на проде - брак, который видит читатель из поиска.
#
# ГРАНИЦА С СОСЕДЯМИ (второго источника истины не заводим):
#   assets-exist    - ФАКТ локального файла у ОТНОСИТЕЛЬНЫХ ссылок (корневые
#                     пропускает по контракту). Существование относительных
#                     остаётся ему, здесь оно не переспрашивается
#   image-refs      - АДРЕС: та же ссылка на проде, согласованность комплекта
#                     <picture> и резолв СВОИХ корневых ссылок, которых
#                     assets-exist не видит вовсе
#   frame-density   - что ВНУТРИ кадра · frame-provenance - ОТКУДА кадр
#
# 🔴 ГРАНИЦА ОХВАТА (круг 2, по решению автора - раньше была устной, теперь письменная).
# ГЕЙТ СУДИТ: img[src] · img[srcset] · source[src] · source[srcset] ·
# video[poster] · link[rel=preload][as=image] · url() в атрибуте style= и в
# блоке <style> (последние четыре добрали в круге 2: раньше гейт их не собирал
# вовсе, а битый poster читатель видит ровно так же, как битый <img>).
# ГЕЙТ НЕ СУДИТ, СОЗНАТЕЛЬНО: og:image/twitter:image (не элемент страницы; их
# судят frame-provenance и сверка с продом) · link[rel=icon]/apple-touch-icon
# (общесайтовая иконка, у статьи её не спросишь) · внешние http(s) и data: URL ·
# общесайтовые корневые пути вне ассетов статьи (шрифт, аватар, превью соседей).
# ФАКТ ФАЙЛА НА ДИСКЕ гейт тоже НЕ судит - см. правило 5 ниже: это зона
# assets-exist (относительные) и предполёта ftp_publish (всё остальное).
IMGREF_ASSETS_DIR = "assets"     # имя каталога картинок ВНУТРИ каталога статьи
IMGREF_LAYOUTS = ("auto", "dir", "flat")


def imgref_clean(u):
    """Сырой атрибут -> путь без HTML-сущностей, без ?query и #hash."""
    u = html.unescape(u or "").strip()
    if not u:
        return ""
    return u.split("#", 1)[0].split("?", 1)[0].strip()


def imgref_kind(u):
    """external (чужой домен/протокол-относительный) | data | root | rel."""
    if u.startswith(("http://", "https://", "//")):
        return "external"
    if u.startswith("data:"):
        return "data"
    return "root" if u.startswith("/") else "rel"


def imgref_page_refs(html_text):
    """[(url, тег, атрибут, номер_picture|None)] по всей собранной странице.

    Разбор ОБЩИЙ (imgref_parse_page - подкласс парсера image_health.py). Своего
    разбора регулярками здесь больше нет: он терял src при '>' внутри alt,
    путал data-src со src, рвал srcset по запятой внутри data:-URI и считал
    настоящей ссылкой <img> из HTML-комментария (круг 2, по решению автора).

    Номер <picture> нужен ровно для правила смешанной раскладки: судить надо
    КОМПЛЕКТ одной картинки (source + img), а не страницу целиком - промах
    <source> не откатывается на <img> именно внутри комплекта.
    """
    refs = []
    for raw, тег, attr, pic in imgref_parse_page(html_text):
        u = imgref_clean(raw)
        if u:
            refs.append((u, тег, attr, pic))
    return refs


def imgref_empty_refs(html_text):
    """[(тег, атрибут, №picture)] по ПУСТЫМ атрибутам ссылок на изображения.

    🔴 ЗАЧЕМ ОТДЕЛЬНАЯ ФУНКЦИЯ (круг 3, по решению автора). `<img src="">` - это
    гарантированно битая картинка, видимая читателю без всякой раскладки:
    браузер на пустом src запрашивает САМУ СТРАНИЦУ как изображение и рисует
    дыру в кадре. Соседний чекер image_health.py судит этот случай отдельным
    классом D_EMPTY и роняет exit 1, а гейты стадии page молча выбрасывали
    пустое значение фильтром `if u:` и печатали OK. Разбор был один, вердикт
    разошёлся - ровно та рассинхронизация, ради которой разбор и сводили в один
    источник. Улика: живой файл конвейера с `<img src="" alt="автор">`
    давал gate rc=0 при image_health exit=1; по дереву seo таких страниц 30.

    Тот же корень глушил `link[rel=preload][as=image][href=""]`, поэтому
    смотрим ВСЕ виды ссылок парсера, а не только img[src].
    """
    пустые = []
    for raw, тег, attr, pic in imgref_parse_page(html_text):
        if not imgref_clean(raw):
            пустые.append((тег, attr, pic))
    return пустые


def imgref_remote(slug, assets_remote=None):
    """Каталог картинок статьи НА ПРОДЕ в плоской раскладке, без слэшей по краям.

    автор-специфики тут нет и быть не может: слаг приходит параметром, дефолт -
    универсальная форма `assets/<slug>`, ровно та, что документирует ftp_publish.
    """
    remote = assets_remote if isinstance(assets_remote, str) and assets_remote.strip() \
        else f"{IMGREF_ASSETS_DIR}/{slug}"
    return remote.strip().strip("/")


def imgref_layout_of(u, slug, assets_remote=None):
    """Какую раскладку прода подразумевает ссылка: dir | flat | None.

    None - ссылка НЕ про ассеты этой статьи: внешний URL, data:, общесайтовый
    корневой ресурс (шрифт, фавикон, аватар, /assets/thumbs/… соседей). Политика
    та же, что у assets_local_refs: чужим ресурсам статья не судья.
    """
    k = imgref_kind(u)
    if k in ("external", "data"):
        return None
    if k == "root":
        if u.startswith("/" + imgref_remote(slug, assets_remote) + "/"):
            return "flat"
        if u.startswith(f"/{slug}/{IMGREF_ASSETS_DIR}/"):
            return "dir"
        return None
    # относительная ссылка резолвится ОТ АДРЕСА СТРАНИЦЫ - это каталожная
    # раскладка по определению: файл обязан лежать рядом со страницей
    return "dir"


def imgref_remote_shaped(u, slug, assets_remote=None):
    """Относительная ссылка, написанная по ПЛОСКОЙ раскладке - гарантированный 404.

    Форма `assets/<slug>/имя.webp` относительна, а адрес в ней корневой: со
    страницы /<slug>/ она уходит в /<slug>/assets/<slug>/имя.webp, которого нет
    ни в одной раскладке. Ровно эта форма дала битый хиро по решению автора.
    """
    if imgref_kind(u) != "rel":
        return False
    remote = imgref_remote(slug, assets_remote)
    return u.startswith(remote + "/")


def imgref_local_candidates(adir, u, slug, assets_remote=None):
    """Кандидаты локального файла для СВОЕЙ ссылки, по порядку предпочтения.

    Локальная раскладка каталога статьи одна: <adir>/assets/<имя>. Корневой путь
    прода (обеих форм) отображается в неё же - это и есть тот самый файл, который
    ftp_publish зальёт под этим адресом.
    """
    k = imgref_kind(u)
    remote = imgref_remote(slug, assets_remote)
    cands = []
    if k == "rel":
        cands.append(os.path.join(adir, u))
        if u.startswith(remote + "/"):
            cands.append(os.path.join(adir, IMGREF_ASSETS_DIR, u[len(remote) + 1:]))
    elif k == "root":
        tail = ""
        if u.startswith("/" + remote + "/"):
            tail = u[len(remote) + 2:]
        elif u.startswith(f"/{slug}/{IMGREF_ASSETS_DIR}/"):
            tail = u[len(f"/{slug}/{IMGREF_ASSETS_DIR}/"):]
        if tail:
            cands.append(os.path.join(adir, IMGREF_ASSETS_DIR, tail))
    out, seen = [], set()
    for p in cands:
        p = os.path.normpath(p)
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def imgref_findings(html_text, adir, slug, layout="auto", assets_remote=None,
                    require_files=False):
    """[(строка_замечания, …)] по собранной странице + сводка.

    Возврат: (замечания, сводка) - сводка это dict со счётчиками для отчёта.
    Замечания только ЖЁСТКИЕ: каждое означает картинку, битую на проде.

    require_files - существование локального файла под СВОЮ КОРНЕВУЮ ссылку.
    По умолчанию ВЫКЛЮЧЕНО, см. правило 5: включать имеет право только тот, кто
    держит в руках весь набор заливки (предполёт ftp_publish).
    """
    refs = imgref_page_refs(html_text)
    own, чужие = [], 0
    for u, тег, attr, pic in refs:
        if imgref_layout_of(u, slug, assets_remote) is None:
            чужие += 1
        else:
            own.append((u, тег, attr, pic))

    bad = []

    # ── 0. ПУСТОЙ АТРИБУТ - дефект ДО всякой раскладки ───────────────────────
    # Идёт первым правилом намеренно: он не зависит ни от раскладки, ни от
    # набора заливки, ни от прода. Пустой src браузер резолвит в АДРЕС САМОЙ
    # СТРАНИЦЫ и пытается нарисовать HTML как картинку - дыра в кадре у каждого
    # читателя. Раньше такое значение выбрасывалось фильтром `if u:` и страница
    # получала OK, хотя соседний чекер на ней же давал exit 1.
    пустые = imgref_empty_refs(html_text)
    for тег, attr, pic in пустые:
        где = f" (внутри <picture> №{pic})" if pic is not None else ""
        bad.append(f"! {тег}[{attr}]{где}: ПУСТОЙ атрибут - браузер запросит саму "
                   f"страницу вместо картинки и нарисует дыру в кадре. Вписать "
                   f"реальный путь или убрать тег целиком")

    раскладки = {}
    for u, тег, attr, pic in own:
        раскладки.setdefault(imgref_layout_of(u, slug, assets_remote), []).append(
            (u, тег, attr, pic))

    # ── 1. СМЕШАННАЯ РАСКЛАДКА ВНУТРИ ОДНОГО <picture> (то, ради чего гейт) ──
    по_картинкам = {}
    for u, тег, attr, pic in own:
        if pic is not None:
            по_картинкам.setdefault(pic, []).append(
                (u, тег, attr, imgref_layout_of(u, slug, assets_remote)))
    смешанных = 0
    for pic in sorted(по_картинкам):
        комплект = по_картинкам[pic]
        виды = {l for _, _, _, l in комплект}
        if len(виды) > 1:
            смешанных += 1
            bad.append(f"! <picture> №{pic}: СМЕШАННАЯ РАСКЛАДКА внутри одного "
                       f"комплекта - {', '.join(sorted(виды))}. Браузер берёт "
                       f"<source> первым и на промахе НЕ откатывается на <img>: "
                       f"читатель видит битый кадр, даже когда фолбэк живой")
            for u, тег, attr, l in комплект:
                bad.append(f"!   {тег}[{attr}] ({l}): {u}")

    # ── 2. РАСКЛАДКА СТРАНИЦЫ РАСЩЕПЛЕНА (те же ассеты двумя способами) ──────
    if len(раскладки) > 1:
        bad.append("! раскладка страницы РАСЩЕПЛЕНА: свои ассеты статьи "
                   "адресуются и каталожно, и плоско - на проде верна ровно одна "
                   "из двух, вторая половина ссылок битая")
        for l in sorted(раскладки):
            имена = sorted({u for u, _, _, _ in раскладки[l]})
            bad.append(f"!   {l}: {len(имена)} шт., напр. {имена[0]}")

    # ── 3. ПЛОСКАЯ ФОРМА, ОСТАВЛЕННАЯ ОТНОСИТЕЛЬНОЙ (дословный вид дефекта) ──
    плоские_отн = sorted({u for u, _, _, _ in own
                          if imgref_remote_shaped(u, slug, assets_remote)})
    for u in плоские_отн:
        bad.append(f"! {u}: путь написан по ПЛОСКОЙ раскладке, но оставлен "
                   f"относительным - со страницы уйдёт в "
                   f"/{slug}/{u} и вернёт 404. Верная форма: /{u}")

    # ── 4. РАСКЛАДКА ПРОГОНА ОБЪЯВЛЕНА ЯВНО - ссылки обязаны ей соответствовать
    if layout in ("dir", "flat"):
        чужой = sorted({u for u, _, _, _ in own
                        if imgref_layout_of(u, slug, assets_remote) != layout})
        for u in чужой:
            bad.append(f"! {u}: прогон объявлен раскладкой {layout}, а ссылка "
                       f"написана по другой - на проде она не резолвится")

    # ── 5. СВОЯ КОРНЕВАЯ ССЫЛКА: судим РАСКЛАДКУ, а не наличие файла ─────────
    #
    # 🔴 БЫЛО и почему снято (круг 2, по решению автора). Правило роняло FAIL на каждой
    # своей корневой ссылке, под которую рядом со страницей нет файла. На
    # заливке «ТОЛЬКО СТРАНИЦА» (каталог = index.html + пустой assets/, картинки
    # уже живут на проде) это ложный FAIL по всему листу. Улика скептика,
    # перепроверена по решению автора живьём: три deploy-каталога одной статьи, 31 своя
    # корневая ссылка, локально в assets/ ноль файлов, при этом 27 проверенных
    # адресов отдают на проде 200. Гейт, который краснеет на 31 живой картинке,
    # обесценивает сам себя - его перестают читать, и настоящая находка тонет.
    #
    # ПОЧЕМУ ЭТО НЕ ДЫРА, А ПЕРЕДАЧА ПО ПРИНАДЛЕЖНОСТИ. Стадия page не знает
    # НАБОРА ЗАЛИВКИ: картинка может ехать из другого каталога, лежать на проде
    # с прошлого раза, подставляться шаблоном (карточки «Читайте также»,
    # --card-thumb, каталог гайдов). «Файла нет рядом со страницей» на этой
    # стадии не значит НИЧЕГО. Ответ знают только двое, и у обоих он уже есть:
    #   assets-exist   - ОТНОСИТЕЛЬНЫЕ ссылки: файл обязан лежать рядом (контракт
    #                    не менялся, там существование как было, так и есть)
    #   ftp_publish    - предполёт gate_image_health: у него на руках И набор
    #                    заливки, И живой прод, он единственный может отличить
    #                    «файла нет нигде» от «файл уже на проде»
    # Здесь остаётся ось, которую не проверяет больше никто: КУДА ссылка попадёт.
    # Она закрыта правилами 1-4 (комплект <picture>, расщеплённая раскладка,
    # плоская форма относительной ссылкой, соответствие объявленной раскладке).
    #
    # require_files=True возвращает старую проверку - для вызова из барьера, где
    # каталог гарантированно самодостаточен. По умолчанию ВЫКЛЮЧЕНО.
    корневые = sorted({u for u, _, _, _ in own if imgref_kind(u) == "root"})
    нет_файла = []
    for u in корневые:
        cands = imgref_local_candidates(adir, u, slug, assets_remote)
        if not any(os.path.isfile(p) for p in cands):
            нет_файла.append((u, cands))
    if require_files:
        for u, cands in нет_файла:
            куда = ", ".join(cands) if cands else "локального адреса не выводится"
            bad.append(f"! {u}: своя корневая ссылка, но файла под неё нет ({куда}) "
                       f"- на прод под этим адресом заливать нечего")

    сводка = {"всего": len(refs), "своих": len(own), "общесайтовых": чужие,
              "пустых": len(пустые),
              "picture": len(по_картинкам), "смешанных_picture": смешанных,
              "раскладки": {k: len(v) for k, v in sorted(раскладки.items())},
              "корневых": len(корневые), "корневых_без_файла": len(нет_файла),
              "файлы_судим": bool(require_files)}
    return bad, сводка


def image_refs_run(adir, page_path=None, slug=None, layout="auto", assets_remote=None,
                   require_files=False):
    """(rc, строки). rc: 0 - каждая ссылка на изображение резолвится в раскладке,
    по которой страница поедет на прод · 1 - есть битые (FAIL) · 2 - вход негоден
    (неизвестная раскладка) · 3 - проверять нечем: нет index.html ЛИБО нет
    разбора страницы (image_health.py не найден)."""
    slug = slug or os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    remote = imgref_remote(slug, assets_remote)
    lines = [f"image-refs [page] {slug}"]
    if layout not in IMGREF_LAYOUTS:
        lines.append(f"  ОШИБКА: неизвестная раскладка {layout!r}, "
                     f"известны {', '.join(IMGREF_LAYOUTS)}")
        return 2, lines
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 3, lines

    try:
        bad, s = imgref_findings(tc_read(page), adir, slug, layout=layout,
                                 assets_remote=assets_remote,
                                 require_files=require_files)
    except ImgrefParserMissing:
        # мягкая деградация с ЧЕСТНОЙ пометкой: article_gates не падает,
        # но и зелёного вердикта на неразобранной странице не выдаёт
        lines.append(f"  ОШИБКА: {imgref_parser_note()}")
        lines.append("  Вердикт не выносится: разобрать страницу нечем. Положите "
                     "image_health.py рядом с article_gates.py, в каталог "
                     "инструментов lead-magnit или укажите путь в IMAGE_HEALTH_PY.")
        return 3, lines
    lines.append("  " + imgref_parser_note())
    lines.append(f"  раскладка прогона: {layout}"
                 + ("  (выводится из самой страницы)" if layout == "auto" else "")
                 + f" · каталожная = /{slug}/{IMGREF_ASSETS_DIR}/<имя>"
                   f" · плоская = /{remote}/<имя>")
    lines.append(f"  ссылок на изображения: {s['всего']} "
                 f"(своих ассетов статьи {s['своих']}, общесайтовых/внешних "
                 f"{s['общесайтовых']}) · комплектов <picture>: {s['picture']}"
                 + (f" · ПУСТЫХ атрибутов: {s['пустых']}" if s.get("пустых") else ""))
    if s["раскладки"]:
        lines.append("  своих ссылок по раскладкам: "
                     + ", ".join(f"{k}={v}" for k, v in s["раскладки"].items()))
    # своя корневая ссылка без локального файла - НЕ вердикт этой стадии, но и
    # не молчание: цифра печатается всегда, с именем того, кто за неё отвечает
    if s["корневых"]:
        if s["файлы_судим"]:
            lines.append(f"  свои корневые ссылки: {s['корневых']}, из них без "
                         f"локального файла {s['корневых_без_файла']} "
                         f"(судим по требованию вызвавшего: --require-local-files)")
        else:
            lines.append(f"  свои корневые ссылки: {s['корневых']}, из них без "
                         f"локального файла {s['корневых_без_файла']} - это НЕ "
                         f"вердикт стадии page (файл может уже лежать на проде "
                         f"или ехать из другого каталога). Факт файла судят "
                         f"assets-exist (относительные) и предполёт ftp_publish "
                         f"(там есть и набор заливки, и живой прод)")
    if not bad:
        lines.append("  OK. Смешанной раскладки внутри <picture> нет, все свои "
                     "ссылки адресуются одной раскладкой и попадают на прод по "
                     "тому адресу, по которому их туда кладёт заливка.")
        return 0, lines
    lines.append(f"  БИТЫЕ КАРТИНКИ: замечаний {len(bad)}"
                 + (f", смешанных комплектов <picture>: {s['смешанных_picture']}"
                    if s["смешанных_picture"] else ""))
    lines += ["  " + b for b in bad]
    return 1, lines


# ── гейт frame-density: плотность кадра (пустой блок / текст-плашка) ─────────
#
# ЗАЧЕМ (разнос владельца). Дословно, по хиро guide-deepseek: «че это
# за треш вместо картинок? переделать все и НИКОГДА такое говно не ставить». На
# скрине - карточки прижаты к верху, две трети кадра пустая градиент-заливка.
# «НИКОГДА» держал только текст правила в каноне: ни один гейт стадии page не
# ходил в САМ ПИКСЕЛЬ - structure-check считает <figure>, assets-exist проверяет
# факт файла на диске, и оба одинаково зелены на пустом градиенте и на плотном
# скриншоте. Аудит кадров по решению автора (75 кадров корпуса волн r10+r11, отчёт
# growth/seo/_rebuild/r10/audit-kadrov.md) нашёл 22 брака и 17 пограничных при
# полностью зелёных гейтах. Здесь та же машинная метрика вшита В КОД.
#
# МЕТРИКА (порт growth/seo/_rebuild/r10/emptiness-scan.py, числа совпадают
# байт-в-байт с аудитом - алгоритм скопирован, не переписан). Кадр режется на
# тайлы 16x16, тайл считается ПУСТЫМ, если СКО яркости внутри него ниже 12.
# Плоская заливка и градиент дают низкое СКО в окне 16 px и ловятся как пустота,
# текст и интерфейс - нет. Считается два числа:
#   empty_pct - доля пустых тайлов во всём кадре
#   block_pct - САМЫЙ КРУПНЫЙ СПЛОШНОЙ пустой прямоугольник, доля площади кадра
#
# ДВЕ ВЕТКИ, потому что дефект двух разных пород (обе калиброваны аудитом):
#   1. ПУСТОЙ БЛОК: block_pct >= 25. Ровно то, на что ругался владелец - один
#      большой мёртвый кусок кадра. Калибровка: тот самый хиро deepseek в виде,
#      в каком его увидел владелец, дал block_pct 61.5 (первое место по корпусу
#      из 75), второе место 54.8 тоже оказалось браком глазами. empty_pct как
#      гейт бесполезен: у плотного скриншота доки он тоже 80%+, межстрочные
#      интервалы считаются пустотой.
#   2. ТЕКСТ-ПЛАШКА: empty_pct >= 80 ПРИ block_pct < 20. Сверстанная картинка с
# карточками текста (запрещённый класс с этой редакции: схемы, чек-листы и
#      сравнения делать HTML-блоками .vizblock, картинкой остаётся только
#      реальный скрин). Первая ветка её НЕ ловит - пустота размазана между
#      карточками, а не собрана в один блок: у guide-gemini-rezhimy.png
#      block_pct всего 14.7 при 50% пустоты на глаз.
#
# ЧТО СКАНИРУЕТСЯ. Кадры САМОЙ статьи: локальные ассеты-картинки из img/source
# (src + srcset) плюс og-обложка (og:image / twitter:image), если она указывает
# в assets/ этой же статьи. НЕ сканируются:
#   · thumb-* - превьюшки карточек «Читайте также». Это кадры ДРУГИХ статей,
#     обрезанные до 480x270 под карточку; у всех шести на живой странице
#     block_pct 33-37 при абсолютно здоровом оригинале. Аудит их тоже не считал
#     (13 кадров у guide-kakaya-neyroset-luchshe = ассеты статьи без thumb-*).
#     Без этого исключения гейт красит ВЕСЬ корпус и перестаёт что-либо значить
#   · абсолютные http(s)-URL чужих доменов, data:, корневые /assets/… -
#     общесайтовые ресурсы (аватар автора, фавикон), статья им не судья
#   · не-картинки (svg/ico и прочее, что не открывается растром)
# Один КАДР = одно имя без расширения: у пары hero.jpg + hero.webp метрика
# одинаковая (проверено на корпусе - расхождение в десятых), меряется один файл
# по порядку предпочтения jpg > jpeg > png > webp, чтобы отчёт совпадал с
# аудитом по счёту кадров, а не двоился.
FRAME_TILE = 16
FRAME_VAR_SD = 12.0          # СКО внутри тайла ниже -> тайл пустой
FRAME_DOWNSCALE_W = 1400     # даунскейл широких кадров: скорость + единая шкала
# 🔴 ПОРОГИ - калибровка аудита кадров, growth/seo/_rebuild/r10/audit-kadrov.md,
# раздел «Порог, который можно зашивать в код-гейт». Меняются только осознанным
# решением владельца по НОВОЙ калибровке на корпусе, а не задним числом под
# конкретную страницу, которая не проходит.
#
# ПЕРЕКАЛИБРОВКА по решению автора (волна р13). Первая редакция гейта зашила порог 25 как
# FAIL и этим стёрла среднюю зону аудита. Дословно аудит (таблица порогов):
#   БРАК         block_pct >= 40 ИЛИ band_pct >= 40 ИЛИ cband_pct >= 55 - не публиковать
#   ПОГРАНИЧНЫЙ  block_pct 25-40                                        - «глазами, решение человека»
#   ПЛОТНЫЙ      block_pct < 25                                         - пропускать
# Гейт с порогом 25 красил всю зону «решение человека» в FAIL и заблокировал 70 из
# 78 страниц корпус-волны репозиции CTA (улика: _rebuild/r13/cta-corpus-A-otchet.md,
# «Блокер 1»), причём по кадрам, которые волной не менялись ни на байт. Гейт,
# блокирующий весь корпус, не защищает качество, а останавливает работу - калибруем
# по принятому образцу. Зона 25-40 теперь WARN: видна в отчёте глазами, стадию не
# роняет, решение остаётся за человеком - ровно как написал аудит.
FRAME_BLOCK_FAIL = 40.0      # БРАК: один большой мёртвый кусок кадра
FRAME_BLOCK_WARN = 25.0      # ПОГРАНИЧНЫЙ 25-40: глазами, стадию НЕ роняет
FRAME_BAND_FAIL = 40.0       # БРАК: мёртвая горизонтальная полоса во всю ширину
FRAME_PLASHKA_EMPTY = 80.0   # ветка 2: пустоты столько, что это не скрин
FRAME_PLASHKA_BLOCK = 20.0   # ветка 2: и при этом она РАЗМАЗАНА (не один блок)

# 🔴 ПОЛ ПО ЧИСЛУ СОБСТВЕННЫХ КАДРОВ (по решению автора, круг 3, дефект T21/R71/R116).
# Раньше гейт судил КАЧЕСТВО кадра и молчал про их ЧИСЛО - страница с одним
# хиро и пустым телом проходила плотность зелёной. Живой замер по 245
# собранным страницам корпуса: медиана `<figure>` = 3, p25 = 2, p75 = 5, max 13,
# и распределение имеет явное дно (14 страниц с нулём, 31 с одной). Пять статей
# транша круга 2 несут ровно ПО ОДНОЙ figure каждая - ниже собственного p25.
# Эталон того же жанра держит 5-6 картинок на статью. Пол ставится на медиане
# СВОЕГО корпуса, а не на эталоне: медиана достижима без выдумывания кадров, и
# она уже вдвое выше того, что дал транш. Судится только НОВОЕ производство
# (стадия page у страницы со свежим манифестом съёмки): старому корпусу пол
# задним числом не выставляется.
#
# 🔴 ПОРОГ ВЫНЕСЕН В КОНФИГ (по решению автора, круг 4, дефект R128). Канон визуального
# слоя раздаваемого модуля объявляет ключ `tools.visual.frame_count_min` рядом с
# `min_images`, и ключ обязан РАБОТАТЬ, а не быть обещанием в тексте: канон,
# который называет ручку, которой в коде нет, - это ровно тот класс расхождения
# «канон против кода», из-за которого в круге 3 всплыли восемь инстансов R129.
# Значение по умолчанию остаётся 3 (медиана своего корпуса), у ученика со своим
# жанром - своё число в его конфиге
FRAME_COUNT_MIN = 3


def frame_count_min(yaml_path=None, tools_dir=None):
    """Пол по числу собственных кадров: `tools.visual.frame_count_min` конфига,
    иначе дефолт. Возвращает (число, пояснение) - пояснение печатается в отчёт,
    чтобы читатель видел, ОТКУДА взялся порог, которым его уронили."""
    if not yaml_path:
        return FRAME_COUNT_MIN, "порог по умолчанию (конфиг не передан)"
    cfg, note = tc_yaml_cfg(yaml_path, tools_dir)
    node = cfg.get("tools") if isinstance(cfg, dict) else None
    node = node.get("visual") if isinstance(node, dict) else None
    v = node.get("frame_count_min") if isinstance(node, dict) else None
    if v is None:
        return FRAME_COUNT_MIN, f"порог по умолчанию ({note}, ключа нет)"
    try:
        return int(v), f"порог из конфига tools.visual.frame_count_min ({note})"
    except (TypeError, ValueError):
        return FRAME_COUNT_MIN, (f"значение tools.visual.frame_count_min={v!r} "
                                 "не число, идём на дефолте")
# ИСКЛЮЧЕНИЕ АУДИТА: «терминал с текстом - это контент, а не пустота». Дословно:
# «Признак терминала: тёмный фон, моноширинный текст, три кружка в заголовке окна.
# Для таких кадров правило cband_pct не применять, оставить только block_pct и
# band_pct». Три кружка и моноширинность 16-пиксельными тайлами не различить, зато
# машинно проверяется СВОЙСТВО, которое исключение и защищает: чернила размазаны по
# всей площади кадра (строки текста идут по всей высоте и ширине), а не собраны в
# 2-4 крупные карточки с широкими полями. Калибровка - размеченный образец самого
# аудита, разделение чистое с большим зазором:
#   терминалы/скрины, которые аудит зовёт ПЛОТНЫМИ, в зоне 25-40:
#     ink_rows >= 42.6, ink_cols >= 54.7 (zapusk 42.6/59.8 · obezlichivanie 61.5/56.0
#     · lokalnyy-progon 51.3/60.0 · doctor 52.9/54.7 · ustanovka 46.3/60.0
#     · gallyucinacii 59.3/77.4)
#   кадры той же зоны, которые аудит зовёт ПОГРАНИЧНЫМИ:
#     ink_rows <= 32.1, ink_cols <= 28.7 (bolt-new-vhod 32.1/28.7 · shot-alice 17.3/12.6)
# Пороги поставлены в зазор. Исключение НЕ трогает ветку БРАКА: у терминала block_pct
# и band_pct работают в полную силу, как и требует аудит.
FRAME_CONTENT_INK_ROWS = 38.0
FRAME_CONTENT_INK_COLS = 45.0

FRAME_EXT_ORDER = (".jpg", ".jpeg", ".png", ".webp")
FRAME_OG_TAG_RE = re.compile(
    r'<meta\b[^>]*\b(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*>', re.I)
FRAME_CONTENT_RE = re.compile(r'\bcontent=["\']([^"\']+)["\']', re.I)


def frame_analyze(path):
    """Метрики пустоты одного кадра. Порт emptiness-scan.py (r10), алгоритм и
    константы те же, поэтому числа сходятся с аудитом кадров по решению автора."""
    from PIL import Image  # локальный импорт: без картинок гейта нет смысла
    im = Image.open(path).convert("L")
    W, H = im.size
    if W > FRAME_DOWNSCALE_W:
        k = float(FRAME_DOWNSCALE_W) / W
        im = im.resize((int(W * k), int(H * k)), Image.LANCZOS)
        W, H = im.size
    px = im.load()
    cols, rows = W // FRAME_TILE, H // FRAME_TILE
    grid, empty, total = [], 0, 0
    for ry in range(rows):
        line = []
        for rx in range(cols):
            s = s2 = n = 0
            x0, y0 = rx * FRAME_TILE, ry * FRAME_TILE
            for y in range(y0, y0 + FRAME_TILE, 2):
                for x in range(x0, x0 + FRAME_TILE, 2):
                    v = px[x, y]
                    s += v
                    s2 += v * v
                    n += 1
            mean = s / n
            sd = math.sqrt(max(0.0, s2 / n - mean * mean))
            is_empty = sd < FRAME_VAR_SD
            line.append(1 if is_empty else 0)
            empty += 1 if is_empty else 0
            total += 1
        grid.append(line)
    pct = 100.0 * empty / total if total else 0.0

    # крупнейший СПЛОШНОЙ пустой прямоугольник (максимальный прямоугольник в
    # гистограмме высот, построчно) - ловит «две трети кадра заливка»
    best = 0
    heights = [0] * cols
    for ry in range(rows):
        for rx in range(cols):
            heights[rx] = heights[rx] + 1 if grid[ry][rx] else 0
        stack = []
        for rx in range(cols + 1):
            h = heights[rx] if rx < cols else 0
            start = rx
            while stack and stack[-1][1] >= h:
                st, hh = stack.pop()
                best = max(best, hh * (rx - st))
                start = st
            stack.append((start, h))
    block = 100.0 * best / total if total else 0.0

    # band_pct / cband_pct - вторая и третья ноги БРАКА в аудите. Порт того же
    # emptiness-scan.py (r10): самая широкая полоса ПОДРЯД идущих почти пустых
    # строк тайлов (>= 90% пусто) по вертикали и по горизонтали. Числа сходятся
    # с аудитом до десятой (сверено на его же кадрах: zapusk 30.4/7.4/34.5,
    # ollama-show 47.6/10.3/64.0, obezlichivanie 35.9/10.3/41.3)
    band = cur = 0
    for ry in range(rows):
        if sum(grid[ry]) >= 0.9 * cols:
            cur += 1
            band = max(band, cur)
        else:
            cur = 0
    cband = cur = 0
    for rx in range(cols):
        if sum(grid[ry][rx] for ry in range(rows)) >= 0.9 * rows:
            cur += 1
            cband = max(cband, cur)
        else:
            cur = 0
    # распределение ЧЕРНИЛ - машинный признак исключения «терминал/скрин с
    # текстом = контент»: доля рядов и столбцов тайлов, где чернил хотя бы на
    # 10% длины. У терминала текст идёт по всей площади, у текст-плашки собран
    # в несколько карточек с широкими полями
    ink_rows = sum(1 for ry in range(rows) if (cols - sum(grid[ry])) >= 0.10 * cols)
    ink_cols = sum(1 for rx in range(cols)
                   if (rows - sum(grid[ry][rx] for ry in range(rows))) >= 0.10 * rows)
    return {"size": f"{W}x{H}",
            "empty_pct": round(pct, 1),
            "block_pct": round(block, 1),
            "band_pct": round(100.0 * band / rows, 1) if rows else 0.0,
            "cband_pct": round(100.0 * cband / cols, 1) if cols else 0.0,
            "ink_rows_pct": round(100.0 * ink_rows / rows, 1) if rows else 0.0,
            "ink_cols_pct": round(100.0 * ink_cols / cols, 1) if cols else 0.0}


def frame_is_content(m):
    """Кадр-КОНТЕНТ (терминал, скрин доки, таблица): чернила по всей площади.

    Машинный вид исключения аудита «терминал с текстом - это контент, а не
    пустота» и его же третьего условия у ветки текст-плашки («отсутствие хрома
    интерфейса»). Калибровка и зазор - в комментарии к FRAME_CONTENT_INK_*.
    Старые кадры без этих полей (метрика посчитана прошлой редакцией) контентом
    не считаются: молчаливое исключение опаснее лишней строки в отчёте.
    """
    return (m.get("ink_rows_pct", 0.0) >= FRAME_CONTENT_INK_ROWS
            and m.get("ink_cols_pct", 0.0) >= FRAME_CONTENT_INK_COLS)


def frame_density_verdict(m):
    """Причина БРАКА кадра или None. Три ветки, все из калибровки аудита.

    Контракт (причина, деталь) прежний - на нём стоят селфтесты первой редакции.
    Зона 25-40 сюда БОЛЬШЕ НЕ ПОПАДАЕТ, она ушла в frame_density_warn().
    """
    if m["block_pct"] >= FRAME_BLOCK_FAIL:
        return ("пустой блок в кадре",
                f"block_pct {m['block_pct']} >= {FRAME_BLOCK_FAIL:g}")
    if m.get("band_pct", 0.0) >= FRAME_BAND_FAIL:
        return ("мёртвая полоса во всю ширину",
                f"band_pct {m['band_pct']} >= {FRAME_BAND_FAIL:g}")
    if (m["empty_pct"] >= FRAME_PLASHKA_EMPTY and m["block_pct"] < FRAME_PLASHKA_BLOCK
            and not frame_is_content(m)):
        return ("подозрение на текст-плашку",
                f"empty_pct {m['empty_pct']} >= {FRAME_PLASHKA_EMPTY:g} "
                f"при block_pct {m['block_pct']} < {FRAME_PLASHKA_BLOCK:g}")
    return None


def frame_density_warn(m):
    """Причина ЗАМЕЧАНИЯ (зона ПОГРАНИЧНЫЙ аудита) или None. Стадию не роняет.

    Аудит про эту зону: «глазами, решение человека». Гейт показывает кадр с
    числами и идёт дальше - решение остаётся за человеком, а не за порогом.
    Кадр-контент (терминал, скрин доки) сюда не попадает: аудит такие кадры
    прямо зовёт ПЛОТНЫМИ (guide-vaybkoding-kurs-zapusk.jpg, block_pct 30.4).
    """
    if frame_density_verdict(m):
        return None                      # уже брак, замечание поверх не нужно
    if m["block_pct"] >= FRAME_BLOCK_WARN and not frame_is_content(m):
        return ("пограничная пустота, глазами",
                f"block_pct {m['block_pct']} в зоне {FRAME_BLOCK_WARN:g}-"
                f"{FRAME_BLOCK_FAIL:g} - решение человека, стадию не роняет")
    return None


def frame_density_refs(html_text, slug):
    """Кадры САМОЙ статьи: локальные пути картинок из img/source (src+srcset) и
    og-обложка, если она указывает в assets/ этого же слага. thumb-*, чужие
    домены, корневые пути и не-растры отсеяны. Один кадр = одно имя без
    расширения (порядок предпочтения FRAME_EXT_ORDER)."""
    raw = list(assets_local_refs(html_text))
    for tag in FRAME_OG_TAG_RE.findall(html_text):
        m = FRAME_CONTENT_RE.search(tag)
        if not m:
            continue
        u = html.unescape(m.group(1)).strip().split("#", 1)[0].split("?", 1)[0]
        if u.startswith(("http://", "https://", "//")):
            own = re.search(r"/%s/(assets/.+)$" % re.escape(slug), u)
            if not own:
                continue      # обложка чужого домена/чужой страницы - не наш кадр
            u = own.group(1)
        elif u.startswith(("data:", "/")):
            continue
        if u:
            raw.append(u)

    by_stem = {}
    for u in raw:
        base = os.path.basename(u)
        stem, ext = os.path.splitext(base)
        ext = ext.lower()
        if ext not in FRAME_EXT_ORDER:
            continue          # svg/ico и прочее растром не открывается
        if base.startswith("thumb-"):
            continue          # превью карточек «Читайте также» - кадры чужих статей
        key = os.path.join(os.path.dirname(u), stem)
        rank = FRAME_EXT_ORDER.index(ext)
        if key not in by_stem or rank < by_stem[key][0]:
            by_stem[key] = (rank, u)
    seen, out = set(), []
    for key in by_stem:
        u = by_stem[key][1]
        if u not in seen:
            seen.add(u)
            out.append(u)
    return sorted(out)


def frame_density_run(adir, page_path=None, yaml_path=None, tools_dir=None):
    """(rc, строки). rc: 0 - все кадры статьи плотные · 1 - хотя бы один кадр
    красный (поимённо, с причиной и числами) · 2 - нет собранной страницы ·
    3 - проверить нечем (нет Pillow / кадр не читается растром). Тихого PASS
    при неисправном инструменте не бывает: молчаливый SKIP обязательного гейта
    и есть зелёная ложь."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    lines = [f"frame-density [page] {slug}"]
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 2, lines
    try:
        from PIL import Image  # noqa: F401
    except Exception as e:     # noqa: BLE001
        lines.append(f"  ОШИБКА: нет Pillow, кадры проверить нечем ({e})")
        return 3, lines

    refs = frame_density_refs(tc_read(page), slug)
    lines.append(f"  кадров статьи (img/source + og-обложка, без thumb-*, "
                 f"один кадр = одно имя): {len(refs)}")
    lines.append(f" пороги (калибровка аудита r10, перекалибровка по решению автора): "
                 f"БРАК при block_pct >= {FRAME_BLOCK_FAIL:g} либо band_pct >= "
                 f"{FRAME_BAND_FAIL:g} либо empty_pct >= {FRAME_PLASHKA_EMPTY:g} и "
                 f"block_pct < {FRAME_PLASHKA_BLOCK:g} · ЗАМЕЧАНИЕ (стадию не роняет) "
                 f"при block_pct {FRAME_BLOCK_WARN:g}-{FRAME_BLOCK_FAIL:g}")
    lines.append(f"  исключение аудита: кадр-контент (терминал/скрин с текстом, "
                 f"чернила ink_rows >= {FRAME_CONTENT_INK_ROWS:g} и ink_cols >= "
                 f"{FRAME_CONTENT_INK_COLS:g}) в зону замечаний не идёт")
    bad, warn, broken = [], [], []
    for u in refs:
        p = os.path.join(adir, u)
        if not os.path.isfile(p):
            continue           # существование файлов - работа гейта assets-exist
        try:
            m = frame_analyze(p)
        except Exception as e:  # noqa: BLE001
            broken.append(f"  ! {u} -> кадр не читается растром: {e}")
            continue
        v = frame_density_verdict(m)
        w = None if v else frame_density_warn(m)
        mark = "  ! " if v else ("  ~ " if w else "    ")
        note = (f" <- {v[0]}: {v[1]}" if v else
                (f" <- ЗАМЕЧАНИЕ {w[0]}: {w[1]}" if w else
                 (" <- кадр-контент (терминал/скрин с текстом), исключение аудита"
                  if m["block_pct"] >= FRAME_BLOCK_WARN else "")))
        lines.append(f"{mark}{u}  {m['size']}  empty_pct={m['empty_pct']} "
                     f"block_pct={m['block_pct']} band_pct={m.get('band_pct')} "
                     f"cband_pct={m.get('cband_pct')} ink={m.get('ink_rows_pct')}/"
                     f"{m.get('ink_cols_pct')}{note}")
        if v:
            bad.append((u, v))
        elif w:
            warn.append((u, w))
    # 🔴 ПОЛ ПО ЧИСЛУ СОБСТВЕННЫХ КАДРОВ (круг 3, T21/R71/R116) считается ДО веток
    # брака и пограничной зоны: иначе страница с одним кадром в пограничной зоне
    # уезжала бы веткой rc=4, не дойдя до пола вовсе - тот же класс, что «барьер,
    # меряющий не свой предмет». Судится только НОВОЕ производство: признак
    # включается там, где рядом со страницей лежит манифест съёмки, у старого
    # корпуса манифеста нет и пол ему задним числом не выставляется
    манифест = os.path.join(os.path.dirname(os.path.abspath(page)),
                            PROV_MANIFEST_NAME)
    фигур = len(re.findall(r"<figure\b", tc_read(page), re.I))
    пол, откуда_пол = frame_count_min(yaml_path, tools_dir)
    пол_провален = False
    if existing(манифест):
        lines.append(f"  собственных кадров в теле (<figure>): {фигур}, "
                     f"пол {пол} - {откуда_пол}; дефолт снят с живого корпуса "
                     "245 страниц (замер: медиана 3, p25 2, p75 5)")
        пол_провален = фигур < пол
    else:
        lines.append(f"  собственных кадров в теле (<figure>): {фигур}; пол по "
                     "числу кадров НЕ применяется - манифеста съёмки рядом нет, "
                     "значит это страница старого корпуса, а не новое производство")
    if пол_провален:
        lines.append(
            f"  ! КАДРОВ МЕНЬШЕ ПОЛА: {фигур} против {пол}. "
            "Страница с одной обложкой и пустым телом читается как заготовка: "
            "у эталона того же жанра 5-6 картинок, у нашего собственного корпуса "
            "медиана 3, а p25 равен 2 - то есть одна картинка ниже нижней четверти "
            "СВОЕГО же корпуса.")
        # 🔴 ЧТО ДЕЛАТЬ, ЧЕСТНО (круг 4, R128). Прежний текст обещал выход
        # «либо закрыть ось .vizblock.vizsteps» - а счёт выше берёт ТОЛЬКО
        # <figure>, и ни один .vizblock его не двигает. Сообщение, зовущее в
        # тупик, стоит дороже молчания: производитель делает лишний круг и
        # получает тот же FAIL. Здесь печатается лестница, которая реально
        # снимает красный, ровно как в законе 22 канона
        lines.append(
            "    Лестница добора (закон 22): 1) снять кадр функции инструментом "
            "съёмки shot.py --url/--scenario, класс result/step; 2) не снимается "
            "(логин, капча, стоп-лист) - чужой реальный кадр движком imgsrc.py, "
            "класс sourced с паспортом источника; 3) own-run - свой прогон. "
            "Каждый кадр обязан попасть В ТЕЛО страницы как <figure>: файл в "
            "assets/ без блока в теле пол не двигает. Взять hero второй раз под "
            "другим именем нельзя - два одинаковых байта это один кадр")
    if broken:
        lines += broken
        lines.append(f"  Кадров не прочиталось: {len(broken)}")
        return 3, lines
    if пол_провален:
        if bad:
            lines.append(f"  Плюс красных кадров: {len(bad)}")
            lines += [f"  ! {u} -> {v[0]} ({v[1]})" for u, v in bad]
        return 1, lines
    if bad:
        lines.append(f"  Красных кадров: {len(bad)}")
        lines += [f"  ! {u} -> {v[0]} ({v[1]})" for u, v in bad]
        if warn:
            lines.append(f"  Плюс кадров в пограничной зоне: {len(warn)}")
        return 1, lines
    if warn:
        lines.append(f"  Брака нет. Кадров в пограничной зоне {FRAME_BLOCK_WARN:g}-"
                     f"{FRAME_BLOCK_FAIL:g}: {len(warn)} - аудит про эту зону говорит "
                     "«глазами, решение человека», поэтому стадию не роняем")
        lines += [f"  ~ {u} -> {w[0]} ({w[1]})" for u, w in warn]
        return 4, lines
    lines.append("  OK. Пустых блоков, мёртвых полос и текст-плашек в кадрах нет, "
                 "число собственных кадров не ниже пола.")
    return 0, lines


# ── гейт frame-provenance: ПРОИСХОЖДЕНИЕ кадра (манифест съёмки) ─────────────
#
# ЗАЧЕМ (закон владельца 22.08.2026, план 2026-08-22-seo-images-ultrarealism).
# Картинка в статье имеет право быть ТОЛЬКО ультра-реалистичной и ТОЛЬКО ценной.
# frame-density меряет, что ВНУТРИ кадра (пустота, мёртвая полоса, текст-плашка),
# и одинаково зелен на честном скрине результата и на сгенерированной сцене-
# декорации: пиксельная метрика происхождение кадра не видит, а детектор
# генеративности по пикселям ненадёжен (отвергнут планом). Проверяемая улика
# происхождения - ЗАПИСЬ О СЪЁМКЕ рядом со страницей: какой файл, какого класса,
# по какому адресу и когда снят. Нет записи - кадр непроверяем.
#
# ЛЕГАЛЬНЫЕ КЛАССЫ КАДРА (план, раздел «Цель»):
#   result    - кейс-превью: РЕЗУЛЬТАТ функции сервиса в реальном интерфейсе
#   step      - путь клика: реальный интерфейс, шаг клиента, аннотация «жми сюда»
#   own-run   - свой прогон: наш реальный экран (окно-чат, веб-панель результата)
#   inherited - кадр, перенесённый с уже существующей страницы при её ревизии;
#               съёмку инструмент не подтверждал. Переходный класс: его счётчик
#               печатается отдельно, по нему видно, сколько корпуса не переснято
#
# ЗАПИСЬ - НЕ САМОДЕКЛАРАЦИЯ (р8-по решению автора, находка панели Ф6). Первая редакция
# гейта читала из записи ровно class/url/shot_at: рукописная строка была для неё
# неотличима от записи shot.py. На ЕДИНСТВЕННОМ манифесте корпуса это сразу и
# выстрелило - три записи из трёх стояли легальными классами, называя закрытый
# канал своим же текстом (обложка `og_hero.py --variant paper` как own-run,
# HTML-мокап как own-run, сток Wikimedia как inherited), а гейт печатал полный
# зелёный: с_записью=3, замечаний=0, rc=0. Поэтому судится САМА ЗАПИСЬ, ещё по
# двум признакам:
#   · РЕЖИМ СЪЁМКИ mode из PROV_MODES (external|relay|url|scenario). Его пишет
#     manifest_add в shot.py на КАЖДОМ канале (url/scenario - живая съёмка,
#     external/relay - регистрация кадра, снятого вне инструмента). Записи без
#     mode инструмент не создаёт вовсе: нет поля - строка рукописная, съёмкой не
#     подтверждена, кадр считается непокрытым
#   · ЗАКРЫТЫЙ КАНАЛ в тексте записи (PROV_CLOSED_CHANNELS по полям note/how/file):
#     генератор обложек, код-рендер сцены, мем, генеративная иллюстрация, мокап,
#     текст-плашка, фотосток. Такой текст - признание брака закона, а не улика
#     съёмки, и молчать о нём нельзя. Лечится пересъёмкой либо .vizblock, а НЕ
#     правкой формулировки записи
# Оба признака мягко = WARN, под --provenance-hard = FAIL. Судится текст записи, а
# не пиксели: детектор генеративности по картинке отвергнут планом как ненадёжный.
#
# ЗАКРЫТЫЙ КАНАЛ ЛОВИТСЯ И ПО ИМЕНИ КАДРА (р9-по решению автора, находка панели Ф6-2).
# Пока признак висел только на ТЕКСТЕ ЗАПИСИ, он держался на самой слабой улике:
# запись необязательна, и первый же живой прецедент это показал - вместо пересъёмки
# кадров у слага удалили сам манифест, признак погас, гейт напечатал мягкое «записи
# нет», страница уехала. Удаление улики не должно быть дешевле пересъёмки. Поэтому
# PROV_CLOSED_NAME_TOKENS прогоняется по ФАКТИЧЕСКОМУ ПУТИ кадра страницы (тот же
# ref, что уже печатается в отчёте) НЕЗАВИСИМО от манифеста: имя `...-illustration`,
# `...-mokap-...`, `...-meme-...` называет закрытый канал прямым текстом.
#   · словарь имени - ЛАТИНИЦА/ТРАНСЛИТ: файлы корпуса зовутся латиницей (mokap,
#     plashka), кириллические стемы словаря записи (мокап/плашк) по именам не
#     срабатывают вовсе
#   · совпадение только с ЛЕВОЙ ГРАНИЦЫ токена (перед ним не буква и не цифра):
#     иначе `meshy-discover` краснел бы от токена cover. Хвост свободен - стем
#     plashk закрывает и plashka, и plashki
# · СЕГМЕНТЫ СЛАГА ИЗ МАТЧИНГА ИСКЛЮЧЕНЫ (рв даты запуска.2026, находка панели Ф6-3).
#     Имя кадра начинается со слага статьи, поэтому тема, чьё слово стоит в
#     словаре, красила бы КАЖДЫЙ свой честный кадр: guide-unsplash-alternativy ->
#     unsplash, guide-memes-shablon -> meme, guide-coverage-audit -> cover. Такой
#     статьи в корпусе сегодня нет, но пять слагов очереди волны про сервисы
#     картинок к ней вплотную, а WARN, который врёт, учат не читать. Поэтому имя
#     режется на сегменты по не-буквенно-цифровому, сегменты, входящие в слаг,
#     выбрасываются, и словарь судит только ОСТАТОК. Цена решения названа прямо:
#     статья про закрытый канал в самом слаге (условный guide-meme-generator)
#     своего кадра `-meme-2` уже не покрасит - её судит человек по осям A8-A9
#   · тот же замер по корпусу подтверждает узость словаря: karta дал бы 11 ложных
#     срабатываний на честных кадрах статьи guide-karta, chatgpt - 11 на
#     guide-chatgpt-*, поэтому слов темы в самом словаре нет вовсе
# Цена перехода известна заранее и измерена: краснеет 11 кадров корпуса
# (illustration 9 · mokap 1 · meme 1) - это честное число долга, а не регресс.
# Признак по имени судится ПЕРВЫМ: диагноз уже поставлен, запись такой кадр не
# отмывает, и в непокрытые он попадает ровно один раз.
#
# МЯГКО ПО УМОЛЧАНИЮ. Гейт рождается при живом корпусе, где манифеста нет НИ У
# ОДНОЙ страницы: жёсткий с первого дня он остановил бы конвейер целиком - ровно
# то, чем кончился порог 25 у frame-density (см. перекалибровку выше). Поэтому
# дефолт - WARN: замечание видно глазами и в gates.json, стадию не роняет. Замок
# включает --provenance-hard, а --provenance-report печатает машинную строку
# сводки и не роняет ничего - им меряется корпус ДО ужесточения (два числа:
# сколько краснеет / сколько настоящих дефектов).
#
# «СКРИН ГЛАВНОЙ» ПОД ЗАМКОМ = FAIL (р5-по решению автора, находка панели ревью). Класс
# result обязан показывать РЕЗУЛЬТАТ функции; запись с адресом КОРНЯ сервиса -
# ровно то, что закон владельца называет полумерой («скрин просто сервиса»).
# Раньше этот признак жил только замечанием и не ронял статью НИКОГДА, даже под
# замком: единственным судьёй оставался человек, а в рантайме волны кадр судит
# тот же агент, который его снял (класс дефекта самопроверки). Теперь под
# --provenance-hard корневой url класса result = FAIL. Узко и намеренно: признак
# «у кейс-превью не назван адрес функции» замком НЕ ловится (пустой url бывает у
# честной съёмки собственного экрана) и остаётся WARN в обоих режимах, а мягкий
# режим по обоим признакам как был замечанием, так и остался.
#
# ЗОНА ГЕЙТА - контентные кадры САМОЙ статьи: локальные растровые ассеты из
# img/source (src + srcset) плюс og-обложка, если она указывает в assets/ этого
# же слага. ВНЕ ЗОНЫ (кадр не наш либо не кадр вовсе):
#   · rc-thumb / thumb-* - превью карточек «Читайте также», кадры ДРУГИХ статей
#   · всё внутри .vizblock - это свёрстанный HTML-блок, а не снимок
#   · пиксель метрики, аватар автора, фавикон - абсолютные и корневые адреса
#   · инлайн-иконки и вектор: svg/ico растром не открываются и кадром не считаются
# Один КАДР = одно имя без расширения (hero.jpg и hero.webp - один кадр): ровно
# тот же счёт, что у frame-density, иначе два гейта считали бы разное. По этому же
# имени кадр ищется в манифесте - запись на .webp закрывает и парный .jpg.
#
# ШИРИННЫЕ СТУПЕНИ srcset - ТОТ ЖЕ КАДР (р3-по решению автора). Канон сборки требует у
# каждой картинки шире 760px две ступени: `assets/<кадр>-720.webp 720w,
# assets/<кадр>.webp 1440w` - это ОДНА съёмка, порезанная конвертером под
# responsive, а не два снимка. Гейт берёт пути и из srcset, поэтому наивный счёт
# по имени файла требовал бы отдельную запись на каждую ступень: собранная строго
# по документации статья давала вечный WARN на каждом кадре тела (живьём: кадров
# 3, без_записи 1), а WARN, который врёт, учат не читать. Правило схлопывания:
# стем вида <база>-<NNN>, где NNN - 3-4 цифры И сама <база> присутствует среди
# кадров страницы или записей манифеста, считается АЛИАСОМ базового кадра, своей
# записи о съёмке не требует. Оба условия обязательны:
#   · 3-4 цифры - ширины конвертера (720/1080/1440/2560). Нумерация кадров
#     (<slug>-result-1, одна цифра) ступенью НЕ считается: это разные съёмки
#   · живая база - иначе `guide-deepseek-cdn-403` (кадр про ошибку 403, базы
#     `guide-deepseek-cdn` на странице нет) молча остался бы без проверки. Такой
#     кадр остаётся самостоятельным и свою запись обязан иметь
# Запись, зарегистрированную на ФАЙЛ ступени, гейт тоже принимает - ищет сперва
# по базовому ключу, потом по ключам схлопнутых ступеней.
#
# МАНИФЕСТ ЛЕЖИТ РЯДОМ СО СТРАНИЦЕЙ, А НЕ В assets/ (контракт плана): каталог
# assets/ уезжает на релей и на прод целиком, манифест туда попасть не должен.
#
# СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА = ИМЕННОЙ ПРИЗНАК (рв даты запуска.2026, находка панели
# Ф6-3). Мягкий дефолт гейта держится на одном допущении: манифеста нет, потому
# что страница старая, снятая до закона. Пока это допущение не проверялось,
# оставался самый дешёвый способ обмана: вместо пересъёмки кадров удалить сам
# манифест - и брак сегодняшней сборки печатался тем же мягким «записи нет», что и
# честный долг корпуса (воспроизведено живьём: страница собрана по решению автора, манифест
# снят, вердикт стадии PASS 12 · WARN 1 · FAIL 0).
# ЧТО СУДИТСЯ: дата сборки страницы (mtime index.html) в день закона или позже И
# хотя бы ОДИН кадр зоны, чей ФАЙЛ лежит на диске с той же датой или свежее, при
# отсутствии манифеста рядом. Два условия, а не одно, - это калибровка по живому
# корпусу, а не осторожность: одна только дата index.html даёт 115 срабатываний из
# 146 страниц (корпус массово пересобирается волной, mtime страницы = дата
# пересборки, а не съёмки), и WARN, который врёт на трёх четвертях корпуса, учат не
# читать. Свежий ФАЙЛ КАДРА - улика самой съёмки: shot.py кладёт кадр и запись
# одним ходом, поэтому кадр, появившийся на диске после закона без записи, - это
# брак сегодняшнего дня. Замер той же связкой: 16 страниц из 146, у остальных 113
# кадры лежат с датой до закона (честный долг корпуса, признак молчит).
# Печатается именная строка с виновным кадром и счётчик свежая_без_манифеста в
# СВОДКЕ, мягко WARN, под --provenance-hard FAIL. Кадров в зоне ноль (ось закрыта
# .vizblock) либо файлов кадров на диске нет - признака нет: подтверждать нечего.
PROV_MANIFEST_NAME = "shots-manifest.json"
PROV_LAW_DATE = datetime.date(2026, 8, 22)
PROV_CLASSES = ("result", "step", "own-run", "inherited", "sourced")
# режимы съёмки, которые пишет manifest_add в shot.py: url/scenario - живая съёмка
# инструментом, external/relay - регистрация кадра, снятого вне его. Поля нет =
# запись рукописная (см. «ЗАПИСЬ - НЕ САМОДЕКЛАРАЦИЯ» в шапке гейта).
# sourced - режим движка чужих кадров scripts/seo/images/imgsrc.py (по решению автора):
# кадр не снят нами вовсе, он ВЗЯТ у источника, и его улика - паспорт источника
PROV_MODES = ("external", "relay", "url", "scenario", "sourced")
# ── КЛАСС sourced (закон владельца 28.08.2026: «ты можешь брать картинки в
# интернете у других людей») ────────────────────────────────────────────────
# Съёмки у такого кадра НЕТ, поэтому улику даёт не она, а ПАСПОРТ ИСТОЧНИКА.
# Поля обязательны ВСЕ: нет любого - кадр считается непокрытым, как если бы
# записи не было вовсе. shot_at у класса несёт ДАТУ ПУБЛИКАЦИИ ИСТОЧНИКА
# (source_date), а не дату находки: дата находки не говорит о свежести кадра.
PROV_SOURCED_FIELDS = ("source_url", "source_page", "license", "license_url",
                       "author", "provider", "channel", "rights_basis",
                       "source_date", "sha256")
# правовое основание - закрытый список, пятого значения нет.
# found-image добавлено требованием владельца («это просто в Google
# или в Яндекс поиск по картинкам, это же тоже можно делать»): у кадра из
# поисковой выдачи своей лицензии CC нет вовсе, и легальность держится на
# НАЗВАННОЙ атрибуции носителя плюс рычаге замены кадра по имени через реестр.
# Послабление ровно одно: отсутствие лицензии CC перестаёт быть причиной отказа.
# Всё остальное строже: у этого основания обязательны ПОЛЯ НОСИТЕЛЯ ниже, и
# отсутствие любого из них делает кадр непокрытым
PROV_RIGHTS_BASIS = ("cc", "vendor-page", "vendor-press", "found-image")
# Поля, без которых основание found-image недействительно. Дубль списка живёт в
# движке (scripts/seo/images/imgsrc.py, якорь ПОЛЯ_НОСИТЕЛЯ): движок такой кадр
# не вставит, гейт такой кадр не пропустит. `engine` называет движок канала
# поиска по картинкам (yandex/ddg/bing) - без него нельзя повторить добычу
PROV_FOUND_IMAGE_FIELDS = ("source_page", "source_url", "author", "provider",
                           "license", "license_url", "source_date", "engine")
# ОДИН ДОМ словаря закрытых каналов (закон владельца 22.08.2026): генератор
# обложек, код-рендер сцены, мем, генеративная иллюстрация, компилятор промптов,
# мокап, текст-плашка, фотосток. Сравнение подстрокой в нижнем регистре по полям
# note/how/file записи; кириллица стоит стемом (мокап/мокапы, плашк/плашка/
# плашки), латиница - целым токеном. Родня по замыслу: SHOT_SRC_TOKENS в
# novice-check.py (тот режет терминал по имени файла, этот - канал по тексту записи)
PROV_CLOSED_CHANNELS = ("og_hero", "cover.py", "meme", "illustration",
                        "gpt_render", "chatgpt_cover", "prompt_compiler",
                        "мокап", "плашк", "wikimedia", "unsplash", "pexels")
# ТОЧЕЧНАЯ классо-зависимость словаря ТЕКСТА ЗАПИСИ (по решению автора, класс sourced).
# У взятого кадра источник называется СЛОВАМИ в note - иначе человек, читающий
# манифест, не видит откуда кадр. Для класса sourced снимается запрет РОВНО на
# один токен - wikimedia: это источник, который может нести реальный скрин
# интерфейса с чистой лицензией и датой источника. Декоративные стоки
# (unsplash, pexels) и ВСЕ генеративные токены остаются закрытыми и для sourced.
# Словарь ИМЁН PROV_CLOSED_NAME_TOKENS классо-зависимым НЕ становится: он
# судится первым и независимо от записи (фикс р9-по решению автора), и послабление по
# имени тут не нужно вовсе - канон имён кадра (<slug>-result-N / <slug>-hero)
# ни одного токена словаря не содержит.
PROV_CLOSED_CHANNELS_SOURCED = tuple(t for t in PROV_CLOSED_CHANNELS
                                     if t != "wikimedia")
# ТОТ ЖЕ ЗАКОН, НО ПО ИМЕНИ ФАЙЛА КАДРА (см. «ЗАКРЫТЫЙ КАНАЛ ЛОВИТСЯ И ПО ИМЕНИ
# КАДРА» в шапке гейта). Отдельный словарь, а не общий с записью, по двум причинам:
# имена корпуса латиницей (кириллические стемы записи тут мертвы), а сравнение идёт
# не подстрокой, а от левой границы токена. Проверено по 3491 имени корпуса:
# `cover` ловит cover-grid-hero (рендер генератора обложек) и НЕ ловит meshy-discover
PROV_CLOSED_NAME_TOKENS = ("illustration", "mokap", "mockup", "plashk", "meme",
                           "cover", "wikimedia", "unsplash", "pexels")
# левая граница токена: перед ним начало строки, дефис, слэш, точка - что угодно,
# кроме буквы и цифры. Хвост свободен: стем plashk закрывает plashka/plashki
PROV_CLOSED_NAME_RE = re.compile(
    "(?<![a-zа-яё0-9])(%s)" % "|".join(PROV_CLOSED_NAME_TOKENS), re.I)
# сегменты имени: всё, что не буква и не цифра, - граница (дефис, слэш, точка,
# подчёркивание). Ими же режется слаг статьи, чтобы выбросить его слова из матчинга
PROV_NAME_SEG_RE = re.compile(r"[^a-zа-яё0-9]+", re.I)
PROV_NAME_WORD_RE = re.compile(r"[a-zа-яё0-9]+", re.I)
PROV_TAG_RE = re.compile(r"<(?:img|source)\b[^>]*>", re.I)
PROV_RCTHUMB_RE = re.compile(r'\bclass=["\'][^"\']*\brc-thumb\b', re.I)
PROV_FIGURE_RE = re.compile(r"(<figure\b[^>]*>)(.*?)</figure\s*>", re.S | re.I)
PROV_HERO_RE = re.compile(r'\bclass=["\'][^"\']*\barticle-hero\b', re.I)
PROV_VIZBLOCK_OPEN_RE = re.compile(
    r'<div\b[^>]*\bclass=["\'][^"\']*\bvizblock(?=["\s])[^>]*>', re.I)
PROV_DIV_RE = re.compile(r"<div\b|</div\s*>", re.I)
PROV_URL_RE = re.compile(r"^(?:https?:)?//[^/]+(/.*)?$", re.I)
# ступень srcset: хвост из 3-4 цифр после дефиса (720/1080/1440/2560). Ленивая
# <база> и якорь конца строки: `foo-12345` (5 цифр) и `foo-1` (одна) не ступени
PROV_STEP_SUFFIX_RE = re.compile(r"^(?P<base>.+?)-(?P<w>\d{3,4})$")
PROV_ROLES = {"hero": "хиро", "figure": "кадр тела", "img": "кадр вне figure",
              "og": "og-обложка"}

# ── ЧЬЯ СТРАНИЦА В КАДРЕ (класс-фикс рв даты запуска.2026, дефект T1 круга 2) ───────
#
# ЧТО СЛУЧИЛОСЬ. Гейт судил НАЛИЧИЕ записи о съёмке и не судил, ЧЬЯ страница в
# кадре. На этом в живой прод уехала статья `/guide-chatgpt-ucheba-2026/`, у
# которой и хиро, и og-обложка - целиком страница КОНКУРЕНТА `explainx.ai`: его
# логотип, его навигация (Trending / News / Pathways / Skills / Explore /
# Pricing), его счётчик рассылки, его промо-полоса «16 free interactive AI
# pathways - START LEARNING FREE», его оглавление и попап Google «Add explainx.ai
# as a preferred source». Это первый визуал нашей страницы и картинка, которая
# уходит в репост. Гейт напечатал OK, потому что запись в манифесте была
# легальной по всем прежним признакам: класс result, режим url, дата, note.
#
# ЧТО СУДИТСЯ ТЕПЕРЬ - ДВА ПРИЗНАКА СРАЗУ, и оба обязаны совпасть:
#   (1) ХОСТ адреса из записи НЕ УЗНАН. Узнан - значит принадлежит нам (домен из
#       config.md) либо предмету статьи: домен-токен хоста (второй уровень без
#       TLD и без www) встречается в слаге, <title>, h1 или meta keywords, ЛИБО
#       хотя бы один сегмент ПУТИ адреса встречается там же. Второе условие
#       обязательно: первоисточник часто живёт на платформе-носителе, и
#       `github.com/openai/codex/blob/.../persistent_mode.md` в статье
#       `guide-codex-persistent-2026` узнаётся именно путём (`codex`,
#       `persistent`), а не хостом
#   (2) АДРЕС ВЫГЛЯДИТ СТРАНИЦЕЙ ЧУЖОГО ИЗДАНИЯ: в пути стоит сегмент публикации
#       (`/blog/`, `/news/`, `/article(s)/`, `/post(s)/`, `/insights/`,
#       `/stories/`, `/magazine/`, `/press/`, `/newsroom/`) либо датированный
#       адрес новости вида `/2026/08/29/`
#
# ПОЧЕМУ ДВА, А НЕ ОДИН. Одного «хост не узнан» мало - он даёт ложный красный на
# честных кадрах и убивает доверие к гейту. Живая проверка по пяти статьям
# транша: один признак покрасил `github.com` (первоисточник кода Codex, кадр
# который контролёр отдельно назвал чистым) и `yookassa.ru/platezhi-dlya-
# samozanyatyh/` (страница самого сервиса, о котором статья). Оба - не витрины
# конкурента, а именно первоисточники. Пара признаков оставляет красным ровно
# тот случай, ради которого гейт написан: чужое ИЗДАНИЕ, пишущее О НАШЕМ
# предмете, вместо страницы самого предмета.
#
# ПРЕДЕЛ ПРИЗНАКА НАЗВАН ВСЛУХ. Скриншот ГЛАВНОЙ страницы конкурента (без
# сегмента публикации в пути) этой парой не ловится - его ловит соседний признак
# «class=result с адресом корня сервиса» и человек на приёмке. Расширять первый
# признак до одиночного значит вернуть ложные красные, а WARN, который врёт,
# учат не читать.
#
# Оба признака совпали - кадр снят с ЧУЖОЙ ВИТРИНЫ, и дальше по роли кадра:
#   · хиро и og - FAIL В ЛЮБОМ РЕЖИМЕ, включая мягкий. Обоснование узкое и
#     проверяемое: признак судится ТОЛЬКО когда запись о съёмке есть и в ней
# есть url, то есть только на кадрах, снятых после закона по решению автора.
#     Старый корпус без манифестов под него не попадает вовсе (там срабатывает
#     ветка «записи нет»), поэтому жёсткость не останавливает конвейер - тот
#     самый довод, которым мягкость дефолта оправдана для остальных признаков
#   · кадр тела - WARN мягко, FAIL под --provenance-hard: внутри статьи чужой
#     скриншот бывает уместен как иллюстрация чужого продукта, но объявить его
#     нужно осознанно
#
# ЧЕГО ПРИЗНАК НЕ ДЕЛАЕТ. Он не читает пиксели и не распознаёт логотипы: это
# отвергнуто планом как ненадёжное. Он судит АДРЕС, с которого кадр снят, и
# сравнивает его с предметом статьи - обе величины машинные и воспроизводимые.
PROV_HOST_RE = re.compile(r"^(?:https?:)?//([^/:?#]+)", re.I)
# TLD и служебные уровни, которые домен-токеном не считаются
PROV_TLD_STOP = {
    "com", "net", "org", "io", "ai", "app", "dev", "co", "me", "ru", "su", "рф",
    "info", "biz", "pro", "tech", "cloud", "site", "online", "store", "studio",
    "www", "blog", "docs", "help", "support", "news", "web", "page", "xyz",
}


def prov_host_tokens(url):
    """Домен-токены хоста адреса: всё, кроме www и служебных уровней с TLD.

    `https://explainx.ai/blog/x` -> {'explainx'}; `https://ltx.studio/pricing` ->
    {'ltx'}; `https://blog.example-donor.com/a` -> {'example-donor'}. Токен `studio` в
    списке служебных намеренно: он бывает доменной зоной, и без этого хост
    `ltx.studio` узнавался бы по слову «studio» в любой статье про студии.
    """
    m = PROV_HOST_RE.match((url or "").strip())
    if not m:
        return set()
    host = m.group(1).lower().strip(".")
    части = [ч for ч in host.split(".") if ч]
    токены = {ч for ч in части if ч not in PROV_TLD_STOP and len(ч) > 1}
    # хост целиком из служебных уровней (условный `blog.ru`) - берём последний
    # значащий уровень, иначе множество пустое и признак молчит на всём подряд
    if not токены and части:
        токены = {части[0]}
    return токены


def prov_predmet_tokens(page_text, slug):
    """Слова, которыми страница называет свой ПРЕДМЕТ: слаг, title, h1, keywords.

    Читается собранная страница, а не спека: судить надо то, что реально уехало
    на прод. Всё в нижнем регистре, разрезано по не-буквенно-цифровому.
    """
    куски = [slug or ""]
    for rx in (r"<title[^>]*>(.*?)</title\s*>",
               r"<h1\b[^>]*>(.*?)</h1\s*>"):
        for m in re.finditer(rx, page_text or "", re.S | re.I):
            куски.append(re.sub(r"<[^>]+>", " ", m.group(1)))
    for m in re.finditer(
            r'<meta\b[^>]*\bname=["\']keywords["\'][^>]*\bcontent=["\']([^"\']*)',
            page_text or "", re.I):
        куски.append(m.group(1))
    слова = set()
    for к in куски:
        for w in PROV_NAME_WORD_RE.findall(к.lower()):
            if len(w) > 1:
                слова.add(w)
    return слова


# сегменты пути, которыми издание помечает СВОЮ публикацию
PROV_IZDANIE_SEGMENTS = ("blog", "news", "article", "articles", "post", "posts",
                         "insights", "stories", "story", "magazine", "press",
                         "newsroom", "novosti", "statyi")
PROV_IZDANIE_PATH_RE = re.compile(
    r"//[^/]+(?:/[^/]*)*?/(?:%s)(?:/|$)" % "|".join(PROV_IZDANIE_SEGMENTS), re.I)
# датированный адрес новости: `/2026/08/29/...` - подпись ленты издания
PROV_IZDANIE_DATA_RE = re.compile(r"//[^/]+/(?:[^/]+/)*?\d{4}/\d{1,2}/", re.I)


def prov_izdanie_url(url):
    """Адрес выглядит страницей ЧУЖОГО ИЗДАНИЯ (второй признак чужой витрины)."""
    u = (url or "").strip()
    if not u:
        return False
    return bool(PROV_IZDANIE_PATH_RE.search(u) or PROV_IZDANIE_DATA_RE.search(u))


def prov_chuzhaya_vitrina(url, предмет, свой_домен):
    """Кадр снят со страницы ЧУЖОГО ИЗДАНИЯ о нашем предмете -> (True, хост, токены).

    Оба признака обязаны совпасть (см. шапку раздела): хост И путь не узнаются
    предметом статьи, И сам адрес выглядит публикацией издания. Пустой url
    признак не поднимает: «адрес функции не назван» - отдельное, уже
    существующее замечание, и вешать на него второй приговор нельзя.
    """
    u = (url or "").strip()
    if not u or u == "-":
        return False, "", set()
    m = PROV_HOST_RE.match(u)
    host = m.group(1).lower() if m else ""
    if not host:
        return False, "", set()
    # ЗАРЕЗЕРВИРОВАННЫЕ ТЕСТОВЫЕ ДОМЕНЫ вне признака (RFC 2606 и RFC 6761):
    # `.test`, `.example`, `.invalid`, `.localhost` по стандарту не существуют в
    # публичной сети, значит витриной конкурента быть физически не могут - это
    # фикстуры. Без исключения признак краснел бы на 24 собственных фикстурах
    # селфтеста, и его пришлось бы либо отключать, либо подгонять под них слаги
    if re.search(r"\.(test|example|invalid|localhost)$", host):
        return False, host, set()
    if свой_домен and (host == свой_домен or host.endswith("." + свой_домен)):
        return False, host, set()
    токены = prov_host_tokens(u)
    if not токены:
        return False, host, set()
    предмет = предмет or set()
    if токены & предмет:
        return False, host, токены
    # 🔴 ПОРЯДОК ПРОВЕРОК ЗДЕСЬ - САМ ПРЕДМЕТ, а не стиль. Признак ИЗДАНИЯ идёт
    # РАНЬШЕ спасения по пути, и вот почему: чужая публикация о нашей теме несёт
    # нашу тему прямо в своём адресе. `explainx.ai/blog/chatgpt-for-teens-safety-
    # study-mode` содержит `chatgpt`, то есть спасение по пути пропустило бы
    # ровно тот кадр, ради которого гейт написан. Проверено живьём: при обратном
    # порядке гейт печатал по этой статье чужая_витрина=0
    if prov_izdanie_url(u):
        return True, host, токены
    # ПУТЬ называет предмет: первоисточник живёт на платформе-носителе
    # (github.com/openai/codex/blob/.../persistent_mode.md), и по хосту он
    # неотличим от чужого блога. Спасение работает только для НЕ-издательских
    # адресов, см. порядок выше
    путь = u.split("//", 1)[-1]
    путь = путь[путь.find("/"):] if "/" in путь else ""
    путь_токены = {w for w in PROV_NAME_WORD_RE.findall(путь.lower()) if len(w) > 1}
    if путь_токены & предмет:
        return False, host, токены
    # ни один признак не сработал: одиночного «хост не узнан» для приговора мало
    return False, host, токены


def prov_vizblock_spans(text):
    """Диапазоны HTML-блоков .vizblock (с учётом вложенных div) - зона ВНЕ гейта.

    Блок не закрыт к концу документа - диапазон НЕ растягивается до конца файла:
    иначе одна битая вёрстка выключила бы гейт для всей нижней половины страницы
    (молчаливый пропуск опаснее лишней строки в отчёте). Такой блок считается
    пустым, а незакрытый div - работа оси рендер-целостности structure-check.
    """
    spans = []
    for m in PROV_VIZBLOCK_OPEN_RE.finditer(text):
        depth, end = 0, None
        for t in PROV_DIV_RE.finditer(text, m.start()):
            if t.group(0).startswith("</"):
                depth -= 1
                if depth <= 0:
                    end = t.end()
                    break
            else:
                depth += 1
        if end:
            spans.append((m.start(), end))
    return spans


def prov_in_spans(pos, spans):
    return any(a <= pos < b for a, b in spans)


def prov_tag_refs(tag, slug=""):
    """Локальные пути картинок из ОДНОГО тега img/source (src + srcset).

    Фильтр тот же, что у assets_local_refs: абсолютные http(s)/protocol-relative/
    data: и КОРНЕВЫЕ пути отсеиваются - это общесайтовые ресурсы и чужие домены
    (пиксель метрики, аватар, фавикон), кадром статьи они не являются.

    ИСКЛЮЧЕНИЕ - СВОЙ ЖЕ КАДР АБСОЛЮТНЫМ АДРЕСОМ (рв даты запуска.2026, находка панели
    Ф6-3): `https://<домен>/<slug>/assets/...` под описание «общесайтовый ресурс»
    не подходит, а отбрасывался вместе с ними - и такой кадр выпадал из зоны гейта
    целиком (ни записи с него не спросят, ни имени). Ровно ту же форму соседняя
    og-ветка prov_page_frames уже узнаёт и переписывает в относительный путь;
    здесь делается то же самое, чтобы две ветки одного гейта считали одинаково.
    """
    raw = []
    m = ASSETS_SRC_RE.search(tag)
    if m:
        raw.append(m.group(1))
    m = ASSETS_SRCSET_RE.search(tag)
    if m:
        for piece in m.group(1).split(","):
            token = piece.strip().split()[0] if piece.strip() else ""
            if token:
                raw.append(token)
    out = []
    for u in raw:
        u = html.unescape(u).strip().split("#", 1)[0].split("?", 1)[0]
        if not u or u.startswith("data:"):
            continue
        if u.startswith(("http://", "https://", "//", "/")):
            own = (re.search(r"/%s/(assets/.+)$" % re.escape(slug), u)
                   if slug else None)
            if not own:
                continue           # чужой домен / общесайтовый ресурс - не наш кадр
            u = own.group(1)       # свой кадр, записанный абсолютным адресом
        out.append(u)
    return out


def prov_frame_key(ref):
    """Ключ кадра: имя файла без расширения, регистр не важен."""
    return os.path.splitext(os.path.basename(ref or ""))[0].strip().lower()


def prov_step_base(key):
    """<база> для ключа ширинной СТУПЕНИ srcset (`guide-x-720` -> `guide-x`) или None.

    Ступень - хвост из 3-4 цифр после дефиса: ровно те ширины, что кладёт в srcset
    конвертер. Нумерация кадров (`<slug>-result-1`, одна цифра) сюда НЕ попадает -
    это отдельные съёмки, каждая со своей записью в манифесте. Одного этого
    признака мало: живая ли <база>, решает prov_collapse_steps.
    """
    m = PROV_STEP_SUFFIX_RE.match((key or "").strip().lower())
    return m.group("base") if m else None


def prov_collapse_steps(raw, known_keys=None):
    """Схлопывает ширинные ступени srcset в БАЗОВЫЙ кадр (см. шапку гейта).

    raw - кадры в порядке появления, дубли по имени уже сняты. known_keys - ключи
    записей манифеста: база могла не встретиться на странице (в srcset живёт одна
    ступень), но быть заснятой и записанной.

    Ступень схлопывается ТОЛЬКО при живой базе; иначе кадр остаётся собой и свою
    запись обязан иметь. В отчёте у схлопнутого кадра показывается базовый файл, а
    ступени перечисляются отдельно - по строке видно, что именно закрыла запись.
    """
    базовые = {fr["key"] for fr in raw} | {k for k in (known_keys or ()) if k}
    out, поз = [], {}
    for fr in raw:
        база = prov_step_base(fr["key"])
        ключ = база if (база and база in базовые) else fr["key"]
        i = поз.get(ключ)
        if i is None:
            поз[ключ] = len(out)
            запись = {"key": ключ, "ref": fr["ref"], "role": fr["role"],
                      "aliases": [], "widths": []}
            if fr["key"] != ключ:
                запись["aliases"].append(fr["key"])
                запись["widths"].append(fr["key"][len(ключ) + 1:])
            out.append(запись)
            continue
        prev = out[i]
        if fr["key"] == ключ:
            prev["ref"] = fr["ref"]    # в отчёте показываем базовый файл, не ступень
        elif fr["key"] not in prev["aliases"]:
            prev["aliases"].append(fr["key"])
            prev["widths"].append(fr["key"][len(ключ) + 1:])
    return out


def prov_frame_entry(idx, fr):
    """Запись манифеста для кадра: сперва по базовому ключу, потом по ключам
    схлопнутых ступеней - съёмку могли зарегистрировать на файл ступени."""
    e = idx.get(fr.get("key"))
    if e is not None:
        return e
    for k in fr.get("aliases") or ():
        e = idx.get(k)
        if e is not None:
            return e
    return None


def prov_frame_label(fr):
    """Путь кадра для отчёта; схлопнутые ступени srcset названы отдельно."""
    свой = prov_frame_key(fr.get("ref"))
    ш = [w for a, w in zip(fr.get("aliases") or (), fr.get("widths") or ()) if a != свой]
    return fr["ref"] + (" (+ступени srcset: %s)" % ", ".join(ш) if ш else "")


def prov_page_frames(html_text, slug, known_keys=None):
    """[{key, ref, role, aliases, widths}] контентных кадров страницы по порядку.

    role - только для читаемости отчёта: hero (кадр в figure.article-hero),
    figure (кадр тела в <figure>), img (растр вне figure), og (обложка).
    known_keys - ключи манифеста, ими же питается схлопывание ступеней srcset.
    """
    dead = prov_vizblock_spans(html_text)
    figs = [(m.start(), m.end(), "hero" if PROV_HERO_RE.search(m.group(1)) else "figure")
            for m in PROV_FIGURE_RE.finditer(html_text)]
    out, seen = [], set()

    def add(ref, role):
        ext = os.path.splitext(ref)[1].lower()
        if ext not in FRAME_EXT_ORDER:
            return                     # svg/ico - иконка/вектор, не кадр
        if os.path.basename(ref).startswith("thumb-"):
            return                     # превью карточек «Читайте также»
        key = prov_frame_key(ref)
        if not key or key in seen:
            return                     # один кадр = одно имя без расширения
        seen.add(key)
        out.append({"key": key, "ref": ref, "role": role})

    for m in PROV_TAG_RE.finditer(html_text):
        if prov_in_spans(m.start(), dead):
            continue                   # внутри .vizblock - вёрстка, а не снимок
        tag = m.group(0)
        if PROV_RCTHUMB_RE.search(tag):
            continue                   # карточка «Читайте также»
        role = "img"
        for a, b, r in figs:
            if a <= m.start() < b:
                role = r
                break
        for ref in prov_tag_refs(tag, slug):
            add(ref, role)

    for tag in FRAME_OG_TAG_RE.findall(html_text):
        m = FRAME_CONTENT_RE.search(tag)
        if not m:
            continue
        u = html.unescape(m.group(1)).strip().split("#", 1)[0].split("?", 1)[0]
        if u.startswith(("http://", "https://", "//")):
            own = re.search(r"/%s/(assets/.+)$" % re.escape(slug), u)
            if not own:
                continue               # обложка чужого домена/страницы - не наш кадр
            u = own.group(1)
        elif u.startswith(("data:", "/")):
            continue
        add(u, "og")
    return prov_collapse_steps(out, known_keys)


def prov_frame_format_siblings(html_text, slug, base_dir):
    """{ключ кадра: [(путь, mtime), ...]} по ВСЕМ форматам, на которые ссылается страница.

    🔴 ЗАЧЕМ (по решению автора, круг 2, дефект T1/R65). prov_page_frames схлопывает
    `<имя>.webp` и `<имя>.jpg` в ОДИН ключ («один кадр = одно имя без расширения»),
    и это правильно для вопроса «есть ли запись о съёмке». Но у вопроса «а тот ли
    файл лежит» схлопывание оказалось дырой: hero статьи переснимался, `.webp` и
    `.png` заменились, а `.jpg`-фолбэк того же <picture> остался от прошлой съёмки -
    страницей конкурента. Гейт видел один ключ, одну запись манифеста и печатал
    зелёное, при том что на живом проде фолбэк отдавал чужую витрину целиком.

    Здесь форматы НЕ схлопываются: собираем все локальные растры, на которые
    ссылается страница, и группируем по ключу. Судить их разъезд будет вызывающий.
    """
    dead = prov_vizblock_spans(html_text)
    груп = {}

    def add(ref):
        ext = os.path.splitext(ref)[1].lower()
        if ext not in FRAME_EXT_ORDER:
            return
        if os.path.basename(ref).startswith("thumb-"):
            return
        ключ = prov_frame_key(ref)
        if not ключ:
            return
        путь = os.path.join(base_dir, ref)
        if not existing(путь):
            return                      # факт файла судят assets-exist и предполёт
        try:
            mt = os.path.getmtime(путь)
        except OSError:
            return
        груп.setdefault(ключ, {})[os.path.abspath(путь)] = mt

    for m in PROV_TAG_RE.finditer(html_text):
        if prov_in_spans(m.start(), dead):
            continue
        tag = m.group(0)
        if PROV_RCTHUMB_RE.search(tag):
            continue
        for ref in prov_tag_refs(tag, slug):
            add(ref)

    for tag in FRAME_OG_TAG_RE.findall(html_text):
        m = FRAME_CONTENT_RE.search(tag)
        if not m:
            continue
        u = html.unescape(m.group(1)).strip().split("#", 1)[0].split("?", 1)[0]
        if u.startswith(("http://", "https://", "//")):
            own = re.search(r"/%s/(assets/.+)$" % re.escape(slug), u)
            if not own:
                continue
            u = own.group(1)
        elif u.startswith(("data:", "/")):
            continue
        add(u)

    return {k: sorted(v.items(), key=lambda x: x[1]) for k, v in груп.items()}


# Порог расхождения форматов одного кадра.
#
# 🔴 СУДИМ ПРЕДМЕТ, А НЕ ПРОКСИ. Первая редакция этой проверки мерила разницу
# mtime, и она немедленно дала ложный красный на СВОЁМ ЖЕ фиксе: `.jpg` был
# перегенерён из того же `.png` часом позже, картинка одна, а метки времени
# разные. Метка времени - имя, а не предмет; урок системы
# feedback_barrier_measuring_name_not_substance_gives_false_green.
# Поэтому сравниваются ПИКСЕЛИ: оба растра приводятся к 32x32 в оттенках серого
# и считается средняя абсолютная разница яркости (0-255). Одна съёмка в двух
# форматах даёт единицы (потери webp/jpeg), разные съёмки - десятки.
PROV_FORMAT_DIFF_MAX = 12.0
#
# 🔴 ПОЧИНКА МЕТОДА (по решению автора, круг 3, дефект T12/R113). Средняя по 32x32
# СЛЕПА к локальной правке кадра. Живой контрпример, на котором барьер дал
# ложный зелёный: `lovable-ocenka-2026-hero.jpg` от 00:15 несёт куки-модалку
# сервиса, `.png` и `.webp` того же кадра пересняты в 02:47 и чисты. Замер:
#   32x32 средняя яркость .png против .jpg  = 0.766 при пороге 12.0  → «норма»
#   полное разрешение, пикселей с разницей >40 = 25 015 из 5 184 000 = 0.4825%
#   та же пара .png против .webp (ОДНА съёмка) = 0 пикселей = 0.0000%
# Модалка занимает 0.5% площади, среднюю по всему кадру она почти не двигает,
# поэтому судить нужно ДОЛЮ РАСХОЖДЕНИЯ на ПОЛНОМ разрешении, а не среднюю на
# миниатюре. Порог 0.1% разводит эти два случая с запасом в 4.8 раза вверх и в
# бесконечность вниз (у одной съёмки ровно ноль).
PROV_FORMAT_PIXEL_DELTA = 40      # разница яркости, с которой пиксель «другой»
PROV_FORMAT_PIXEL_SHARE = 0.001   # 0.1% таких пикселей = кадры разные
# Прокси по mtime. Раньше включался ТОЛЬКО когда Pillow нет - и именно из-за
# этого пропустил свой случай: разрыв .jpg и .png был 2 ч 32 мин при пороге 1 ч,
# то есть «глупый» путь поймал бы то, что «умный» проспал. Теперь он работает
# ВСЕГДА и складывается с пиксельным: барьер судит по объединению признаков.
PROV_FORMAT_SKEW_SEC = 3600


def prov_frame_signature(path, side=32):
    """Подпись растра: список яркостей side*side или None, если посмотреть нечем."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("L").resize((side, side))
            return list(im.getdata())
    except Exception:
        return None


def prov_frame_diff(a, b):
    """Средняя абсолютная разница яркости двух подписей, либо None."""
    if not a or not b or len(a) != len(b):
        return None
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def prov_frame_pixel_share(path_a, path_b, delta=PROV_FORMAT_PIXEL_DELTA):
    """Доля пикселей ПОЛНОГО разрешения, где яркость расходится больше `delta`.

    Возвращает (доля, разошлось, всего) либо (None, None, None), если растр
    посмотреть нечем. Это и есть починка метода T12/R113: локальная модалка на
    0.5% площади среднюю по 32x32 не двигает, а долю расхождения двигает сразу.
    Размеры разные - меньший приводится к большему: формат-фолбэк обязан быть
    ТЕМ ЖЕ кадром, а не другим кропом.
    """
    try:
        from PIL import Image, ImageChops
    except Exception:
        return None, None, None
    try:
        with Image.open(path_a) as ia, Image.open(path_b) as ib:
            a = ia.convert("L")
            b = ib.convert("L")
            if a.size != b.size:
                b = b.resize(a.size)
            гист = ImageChops.difference(a, b).histogram()
            всего = a.size[0] * a.size[1]
            разошлось = sum(гист[delta + 1:])
            if not всего:
                return None, None, None
            return разошлось / float(всего), разошлось, всего
    except Exception:
        return None, None, None


def prov_manifest_load(path):
    """([записи], ошибка). Файла нет - ([], None): это НЕ ошибка формата, а
    отсутствие манифеста, оно и так видно по числу непокрытых кадров."""
    if not existing(path):
        return [], None
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (ValueError, OSError) as e:
        return [], f"манифест съёмки не читается: {e}"
    frames = doc.get("frames") if isinstance(doc, dict) else None
    if not isinstance(frames, list):
        return [], "в манифесте съёмки нет списка frames"
    return [x for x in frames if isinstance(x, dict)], None


def prov_index(entries):
    """{ключ кадра: запись}. Дубли: побеждает ПОСЛЕДНЯЯ запись (свежая съёмка
    дописывается в хвост манифеста)."""
    idx = {}
    for e in entries:
        key = prov_frame_key(e.get("file"))
        if key:
            idx[key] = e
    return idx


def prov_url_is_root(url):
    """Адрес ведёт на КОРЕНЬ сервиса (главную), а не на функцию.

    Ровно то, что запрещено классу result: «скрин просто сервиса/главной» вместо
    результата функции. Не адрес (пусто, «-», кривая строка) сюда не попадает -
    это отдельная ветка отчёта.
    """
    u = (url or "").strip()
    if not u or u == "-":
        return False
    m = PROV_URL_RE.match(u)
    if not m:
        return False
    path = (m.group(1) or "/").split("#", 1)[0].split("?", 1)[0]
    return path in ("", "/")


def prov_closed_channels(e, slug=""):
    """Токены закрытых каналов, названные ТЕКСТОМ САМОЙ ЗАПИСИ (note/how/file).

    Сравнение подстрокой в нижнем регистре: `og_hero.py --variant paper` ловится
    токеном og_hero, «HTML-мокап чека НПД» - стемом мокап, ссылка на сток -
    токеном wikimedia, легаси-имя файла `...-illustration.webp` - токеном
    illustration. Судится текст записи, а не пиксели кадра: детектор
    генеративности по картинке планом отвергнут как ненадёжный.

    ИЗ ПОЛЯ file СЛОВА СЛАГА ВЫРЕЗАНЫ (рв даты запуска.2026): поле несёт путь кадра,
    который начинается со слага статьи, поэтому у темы про закрытый канал
    (guide-unsplash-alternativy) КАЖДАЯ честная запись краснела бы по собственному
    имени файла. Из note и how не вырезается ничего: там то же слово - признание,
    а не механика имени.
    """
    текст = " ".join([str(e.get("note") or ""), str(e.get("how") or ""),
                      prov_strip_slug_segments(str(e.get("file") or ""),
                                               slug)]).lower()
    # ТОЧЕЧНАЯ классо-зависимость (по решению автора): у класса sourced из словаря
    # выпадает ровно токен wikimedia, остальные одиннадцать в силе. Все прежние
    # срабатывания на result/step/own-run/inherited сохраняются без изменений
    словарь = (PROV_CLOSED_CHANNELS_SOURCED
               if str(e.get("class") or "").strip() == "sourced"
               else PROV_CLOSED_CHANNELS)
    return [t for t in словарь if t in текст]


def prov_name_segments(text):
    """Сегменты имени в нижнем регистре: `assets/guide-x-mokap.webp` -> assets,
    guide, x, mokap, webp. Ими режется и имя кадра, и слаг статьи."""
    return [s for s in PROV_NAME_SEG_RE.split((text or "").lower()) if s]


def prov_strip_slug_segments(text, slug):
    """Слова СЛАГА, вычеркнутые из строки-имени, с сохранением её структуры:
    `assets/guide-unsplash-alternativy-plashka.webp` при слаге
    guide-unsplash-alternativy -> `assets/·····-········-···········-plashka.webp`.

    Вычёркиваются ЦЕЛЫЕ сегменты (между не-буквенно-цифровыми), поэтому границы
    слов не меняются: замена стоит ровно там, где и так был отдельный сегмент, и
    новых левых границ внутри слова не появляется. Слаг пустой - строка как была.
    """
    свои = set(prov_name_segments(slug))
    if not свои or not text:
        return text or ""
    return PROV_NAME_WORD_RE.sub(
        lambda m: "·" * len(m.group(0)) if m.group(0).lower() in свои else m.group(0),
        text)


def prov_closed_in_name(fr, slug=""):
    """Токены закрытых каналов, названные ИМЕНЕМ САМОГО КАДРА страницы.

    Читается фактический путь кадра (ref), его ключ и схлопнутые ступени srcset -
    всё, что гейт и так держит в руках. Записи для этого не нужно: удаление
    манифеста больше не гасит признак (см. шапку гейта, р9-по решению автора).

    СЕГМЕНТЫ СЛАГА В МАТЧИНГЕ НЕ УЧАСТВУЮТ (рв даты запуска.2026): имя кадра начинается
    со слага статьи, поэтому у темы, чьё слово стоит в словаре, краснел бы каждый
    честный кадр (guide-unsplash-alternativy -> unsplash, guide-memes-shablon ->
    meme, guide-coverage-audit -> cover). Слаг режется теми же сегментами, его
    слова выбрасываются, словарь судит остаток.

    Совпадение - от левой границы сегмента-остатка, поэтому `meshy-discover` от
    токена cover не краснеет, а `guide-x-mokap-y` от токена mokap краснеет.
    """
    текст = " ".join(
        prov_strip_slug_segments(str(кусок or ""), slug)
        for кусок in ([fr.get("ref"), fr.get("key")]
                      + list(fr.get("aliases") or ()))).lower()
    найдено = {m.group(1).lower() for m in PROV_CLOSED_NAME_RE.finditer(текст)}
    return [t for t in PROV_CLOSED_NAME_TOKENS if t in найдено]


def prov_page_built_on(page):
    """Дата СБОРКИ страницы (mtime index.html) или None, если файла нет.

    Судится именно mtime собранного файла: другой отметки «когда эта страница
    появилась» у гейта нет, а исходник черновика лежит в другом дереве.
    """
    try:
        return datetime.date.fromtimestamp(os.path.getmtime(page))
    except OSError:
        return None


def frame_provenance_run(adir, page_path=None, hard=False, report=False,
                         lm_config=None):
    """(rc, строки). rc: 0 - у каждого кадра зоны есть запись легального класса ·
    1 - при замке --provenance-hard: непокрытые кадры (записи нет, класс вне
    списка, запись без режима mode, закрытый канал в ИМЕНИ кадра или в тексте
    записи), свежая сборка без манифеста рядом ЛИБО
    class=result с адресом корня сервиса («скрин главной» вместо результата
    функции) · 2 - нет собранной страницы · 4 - те же замечания в МЯГКОМ режиме
    плюс «у кейс-превью не назван адрес функции» в ЛЮБОМ режиме (WARN, стадию не
    роняет).
    Режим --provenance-report всегда 0: он меряет корпус, а не судит статью."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    замок = bool(hard) and not report      # судит только замок вне режима отчёта
    режим = ("ОТЧЁТ (--provenance-report, ничего не роняет)" if report
             else ("ЗАМОК (--provenance-hard: непокрытый кадр и class=result с "
                   "адресом корня сервиса = FAIL)" if hard
                   else "МЯГКИЙ (по умолчанию: непокрытый кадр = WARN)"))
    lines = [f"frame-provenance [page] {slug}", f"  режим: {режим}"]
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 2, lines

    mpath = os.path.join(adir, PROV_MANIFEST_NAME)
    entries, merr = prov_manifest_load(mpath)
    idx = prov_index(entries)
    if merr:
        lines.append(f"  ! {merr} ({mpath})")
    elif entries:
        lines.append(f"  манифест съёмки: {mpath} (записей {len(entries)})")
    else:
        lines.append(f"  манифеста съёмки рядом нет ({PROV_MANIFEST_NAME}) - "
                     "происхождение кадров подтвердить нечем")

    frames = prov_page_frames(tc_read(page), slug, known_keys=idx.keys())
    # СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА (см. шапку): мягкость дефолта оправдана только
    # долгом СТАРОГО корпуса. Судятся ДВЕ даты - сборки страницы и файла кадра:
    # одна дата страницы на живом корпусе врёт (массовая пересборка волной)
    собрана = prov_page_built_on(page)
    свежие_кадры = []
    if not entries and not merr and собрана and собрана >= PROV_LAW_DATE:
        база = os.path.dirname(os.path.abspath(page))
        for fr in frames:
            снят = prov_page_built_on(os.path.join(база, fr["ref"]))
            if снят and снят >= PROV_LAW_DATE:
                свежие_кадры.append((fr, снят))
    свежая_без_манифеста = bool(свежие_кадры)
    if свежая_без_манифеста:
        назван = "; ".join(f"{fr['ref']} ({д})" for fr, д in свежие_кадры[:2])
        lines.append(
            f"  ! СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА: страница собрана {собрана}, файлы "
            f"кадров легли на диск в день закона или позже ({назван}"
            + (f", всего таких кадров {len(свежие_кадры)}"
               if len(свежие_кадры) > 2 else "")
            + f"), а {PROV_MANIFEST_NAME} рядом нет. Закон доказательного кадра "
            f"действует с {PROV_LAW_DATE}: это брак сегодняшней съёмки, а НЕ долг "
            "старого корпуса. Манифест не удаляют - он и есть улика; кадры "
            "переснять shot.py (запись он пишет сам) либо закрыть ось .vizblock"
            + ("" if замок else " [под --provenance-hard = FAIL]"))
    # 🔴 РАЗЪЕХАВШИЕСЯ ФОРМАТЫ ОДНОГО КАДРА (по решению автора, круг 2, дефект T1/R65).
    # Смотрим НЕ схлопнутый список: у одного ключа кадра могут лежать .webp, .png и
    # .jpg, и страница ссылается на все три (<source> + <img>-фолбэк + og). Если они
    # сняты в РАЗНОЕ время, значит переснимали не все - и читатель без webp видит
    # старый кадр. Именно так страница конкурента прожила на живом проде 13 часов
    # под свежей записью манифеста про наш собственный экран.
    формат_разъехался, формат_по_mtime = [], False
    база_кадров = os.path.dirname(os.path.abspath(page))
    for ключ, файлы in sorted(prov_frame_format_siblings(
            tc_read(page), slug, база_кадров).items()):
        if len(файлы) < 2:
            continue
        подписи = [(f, mt, prov_frame_signature(f)) for f, mt in файлы]
        видно = [x for x in подписи if x[2]]
        причины_кадра = []
        if len(видно) >= 2:
            эталон = видно[0]
            худшая, худший_файл = 0.0, None
            for f, mt, sig in видно[1:]:
                d = prov_frame_diff(эталон[2], sig)
                if d is not None and d > худшая:
                    худшая, худший_файл = d, f
            if худшая > PROV_FORMAT_DIFF_MAX:
                причины_кадра.append(
                    "разные КАРТИНКИ: %s против %s дают среднюю разницу яркости "
                    "%.1f при пороге %.1f" % (
                        os.path.basename(эталон[0]),
                        os.path.basename(худший_файл or ""), худшая,
                        PROV_FORMAT_DIFF_MAX))
            # 🔴 ПОЛНОЕ РАЗРЕШЕНИЕ (T12/R113): средняя по 32x32 слепа к локальной
            # модалке, доля расходящихся пикселей - нет. Считается по КАЖДОЙ паре,
            # берётся худшая: разъехаться может любой из форматов, не только второй.
            худ_доля, худ_файл2, худ_чисел = 0.0, None, None
            for f, mt, _sig in видно[1:]:
                доля, разошлось, всего = prov_frame_pixel_share(эталон[0], f)
                if доля is not None and доля > худ_доля:
                    худ_доля, худ_файл2, худ_чисел = доля, f, (разошлось, всего)
            if худ_доля > PROV_FORMAT_PIXEL_SHARE:
                причины_кадра.append(
                    "ЛОКАЛЬНОЕ РАСХОЖДЕНИЕ на полном разрешении: %s против %s - "
                    "%d пикселей из %d расходятся больше чем на %d по яркости, "
                    "это %.4f%% при пороге %.2f%%" % (
                        os.path.basename(эталон[0]),
                        os.path.basename(худ_файл2 or ""),
                        (худ_чисел or (0, 0))[0], (худ_чисел or (0, 0))[1],
                        PROV_FORMAT_PIXEL_DELTA, худ_доля * 100.0,
                        PROV_FORMAT_PIXEL_SHARE * 100.0))
            пиксели_видно = True
        else:
            # Pillow нет - предмет посмотреть нечем, барьер ослаблен и это названо
            формат_по_mtime = True
            пиксели_видно = False
        # 🔴 mtime считается ВСЕГДА и ВСЕГДА печатается (T12/R113), но роняет
        # только когда пиксели посмотреть нечем. Иначе барьер даёт ложный КРАСНЫЙ
        # на честной перекодировке: живой замер этого круга по четырём hero-парам
        # даёт 0 расходящихся пикселей из 5 184 000 у трёх файлов, перегенерённых
        # из того же png спустя 11.6 ч, и 24 739 (0.477%) у настоящей половинчатой
        # пересъёмки. Судим предмет (пиксели), прокси называем вслух.
        разрыв = файлы[-1][1] - файлы[0][1]
        if разрыв > PROV_FORMAT_SKEW_SEC:
            текст_mtime = (
                "РАЗНОЕ ВРЕМЯ СЪЁМКИ: файлы одного кадра разъехались на %.1f ч "
                "при пороге %.0f ч" % (разрыв / 3600.0, PROV_FORMAT_SKEW_SEC / 3600.0))
            if not пиксели_видно:
                причины_кадра.append(текст_mtime + " (Pillow нет, пиксели не "
                                     "сравнить - прокси решает один)")
            elif причины_кадра:
                причины_кадра.append(текст_mtime)
            else:
                lines.append(
                    "  ⚠️ ПЕРЕКОДИРОВКА, не пересъёмка: «%s» - %s, но пиксели "
                    "полного разрешения совпали (расходящихся 0). Прокси по "
                    "времени назван вслух и НЕ роняет: предмет посмотрели"
                    % (ключ, текст_mtime.lower()))
        if причины_кадра:
            формат_разъехался.append((ключ, файлы, "; ".join(причины_кадра)))
    if формат_по_mtime:
        lines.append(
            "  ⚠️ сравнение форматов кадра идёт ЗАПАСНЫМ путём по mtime: Pillow на "
            "этой машине не поднялся, пиксели сравнить нечем. Это не «проверено», "
            "это ослабленная проверка, и она названа вслух")
    for ключ, файлы, почему in формат_разъехался:
        назван = ", ".join(
            "%s (%s)" % (os.path.basename(f),
                         time.strftime("%Y-%m-%d %H:%M", time.localtime(mt)))
            for f, mt in файлы)
        lines.append(
            f"  ! ФОРМАТЫ ОДНОГО КАДРА РАЗЪЕХАЛИСЬ: «{ключ}» - {назван}. {почему}. "
            "Страница ссылается на все эти файлы, значит часть читателей видит "
            "кадр ПРОШЛОЙ съёмки, а запись манифеста описывает нынешнюю. "
            "Пересобрать все форматы кадра из одного источника (shot.py либо "
            "конвертер), а не править запись")

    ступеней = sum(len(fr.get("aliases") or ()) for fr in frames)
    lines.append(f"  кадров в зоне (figure/хиро/og, без rc-thumb, .vizblock, "
                 f"пикселя метрики и иконок): {len(frames)}"
                 + (f" (ширинных ступеней srcset схлопнуто в базовый кадр: "
                    f"{ступеней})" if ступеней else ""))
    lines.append(f"  легальные классы: {', '.join(PROV_CLASSES)}")

    нет_записи, чужой_класс, замечания, корень_сервиса = [], [], [], []
    нет_режима, закрытый_канал, закрытый_канал_имя = [], [], []
    неполный_источник = []
    # чужая витрина: хост кадра не узнан ни нами, ни предметом статьи (рв даты запуска)
    чужая_витрина, чужая_витрина_облож = [], []
    предмет_слова = prov_predmet_tokens(tc_read(page), slug)
    свой_домен = (vn_domain(lm_config) or "").lower()
    покрыто, унаследованных = 0, 0
    по_классам = collections.Counter()
    for fr in frames:
        e = prov_frame_entry(idx, fr)
        роль = PROV_ROLES.get(fr["role"], fr["role"])
        метка = prov_frame_label(fr)
        # ИМЯ КАДРА судится ПЕРВЫМ и независимо от манифеста: признак, который
        # гаснет от удаления записи, ловит только честного (р9-по решению автора)
        имя_закрыто = prov_closed_in_name(fr, slug)
        if имя_закрыто:
            закрытый_канал.append((fr, имя_закрыто))
            закрытый_канал_имя.append(fr)
            lines.append(f"  ! закрытый канал в имени кадра: {метка} [{роль}] -> "
                         f"{', '.join(имя_закрыто)} - канал закрыт законом "
                         "по решению автора; манифест тут ни при чём. Кадр честный, а имя "
                         "совпало - лечится ПЕРЕИМЕНОВАНИЕМ кадра (assets_base без "
                         "токена), не пересъёмкой; кадр действительно из закрытого "
                         "канала - пересъёмка shot.py либо .vizblock")
            continue
        if e is None:
            нет_записи.append(fr)
            lines.append(f"  ! {метка} [{роль}] -> записи в {PROV_MANIFEST_NAME} нет")
            continue
        кл = str(e.get("class") or "").strip()
        url = str(e.get("url") or "").strip()
        снят = str(e.get("shot_at") or "").strip() or "дата не указана"
        режим = str(e.get("mode") or "").strip().lower()
        закрытые = prov_closed_channels(e, slug)
        # порядок признаков: сперва самый громкий - запись сама называет канал,
        # закрытый законом. Легальный класс поверх такого текста ничего не отмывает
        if закрытые:
            закрытый_канал.append((fr, закрытые))
            lines.append(f"  ! {метка} [{роль}] -> закрытый канал в записи: "
                         f"{', '.join(закрытые)} (class={кл or 'пусто'}) - канал "
                         "закрыт законом по решению автора, запись это не улика съёмки")
            continue
        if кл not in PROV_CLASSES:
            чужой_класс.append((fr, кл))
            lines.append(f"  ! {метка} [{роль}] -> класс «{кл or 'пусто'}» вне "
                         f"списка {', '.join(PROV_CLASSES)}")
            continue
        if режим not in PROV_MODES:
            нет_режима.append((fr, режим))
            lines.append(f"  ! {метка} [{роль}] -> режим съёмки "
                         f"«{режим or 'поля mode нет'}» вне списка "
                         f"{', '.join(PROV_MODES)}: запись сделана не shot.py, "
                         "съёмка не подтверждена")
            continue
        # ── КЛАСС sourced: улика не съёмка, а ПАСПОРТ ИСТОЧНИКА ──────────────
        if кл == "sourced":
            дыры = [п for п in PROV_SOURCED_FIELDS
                    if not str(e.get(п) or "").strip()]
            осн = str(e.get("rights_basis") or "").strip().lower()
            if осн and осн not in PROV_RIGHTS_BASIS:
                дыры.append("rights_basis вне списка "
                            + "/".join(PROV_RIGHTS_BASIS))
            if осн == "vendor-press" and not str(e.get("permission_url") or "").strip():
                дыры.append("permission_url (обязателен при rights_basis=vendor-press)")
            if осн == "found-image":
                # поля, которые уже названы общим списком класса, второй раз не
                # печатаются: сообщение читает человек, и дубль в нём выглядит
                # как две разные дыры вместо одной
                дыры += [f"{п} (обязательно при rights_basis=found-image)"
                         for п in PROV_FOUND_IMAGE_FIELDS
                         if п not in PROV_SOURCED_FIELDS
                         and not str(e.get(п) or "").strip()]
            лиц = str(e.get("license") or "").lower()
            if re.search(r"(?<![a-z])(nc|nd)(?![a-z])", лиц):
                дыры.append("лицензия несёт метку NC или ND - коммерческому сайту "
                            "такой кадр не годится")
            if дыры:
                неполный_источник.append((fr, дыры))
                lines.append(f"  ! {метка} [{роль}] -> class=sourced без паспорта "
                             f"источника: не хватает {', '.join(дыры)}. У взятого "
                             "кадра съёмки нет, улика - поля источника; нет поля = "
                             "кадр непокрыт")
                continue
            if снят != str(e.get("source_date") or "").strip():
                замечания.append((fr, "shot_at не равен source_date"))
                lines.append(f"  ~ {метка} [{роль}] -> ЗАМЕЧАНИЕ: shot_at={снят} "
                             f"не равен source_date={e.get('source_date')} - у "
                             "класса sourced в shot_at уезжает ДАТА ИСТОЧНИКА")
        # ── ЧЬЯ СТРАНИЦА В КАДРЕ (рв даты запуска.2026). Судится ПОСЛЕ проверок
        # записи и ДО зачёта покрытия: запись легальна по форме, но кадр снят
        # с чужой витрины - это отдельный приговор, а не оттенок замечания
        чужая, хост, хтокены = prov_chuzhaya_vitrina(url, предмет_слова, свой_домен)
        if чужая:
            обложка = fr["role"] in ("hero", "og")
            чужая_витрина.append((fr, хост))
            if обложка:
                чужая_витрина_облож.append(fr)
            lines.append(
                f"  ! {метка} [{роль}] -> ЧУЖАЯ ВИТРИНА: кадр снят с {хост}, "
                f"а предмет статьи этот домен не называет (ни слаг, ни title, "
                f"ни h1, ни keywords не содержат {'/'.join(sorted(хтокены))}). "
                + ("Хиро и og - первый визуал и картинка репоста: чужой бренд, "
                   "чужая навигация и чужие призывы уходят от нашего имени. "
                   "FAIL в любом режиме" if обложка
                   else "Кадр тела: WARN мягко, FAIL под --provenance-hard")
                + ". Лечится пересъёмкой по адресу ПЕРВОИСТОЧНИКА темы или "
                  "своего экрана, а не правкой записи")
            if обложка:
                continue
            # кадр тела в мягком режиме не роняет стадию, но и молча не проезжает
            замечания.append((fr, "чужая витрина в кадре тела"))
        покрыто += 1
        по_классам[кл] += 1
        if кл == "inherited":
            унаследованных += 1
        пометка = ""
        if кл == "result" and prov_url_is_root(url):
            пометка = (" <- %s: адрес корня сервиса - нужен результат функции, "
                       "не главная" % ("БРАК" if замок else "ЗАМЕЧАНИЕ"))
            корень_сервиса.append((fr, "url корня сервиса"))
            замечания.append((fr, "url корня сервиса"))
        elif кл == "result" and (not url or url == "-"):
            пометка = " <- ЗАМЕЧАНИЕ: у кейс-превью не назван адрес функции"
            замечания.append((fr, "адрес функции не назван"))
        mark = "  ~ " if пометка else "    "
        lines.append(f"{mark}{метка} [{роль}] -> class={кл} mode={режим} "
                     f"url={url or '-'} снят {снят}{пометка}")

    lines.append(f"  унаследованных кадров (class=inherited): {унаследованных}"
                 + (" - переходный класс, эти кадры ждут пересъёмки"
                    if унаследованных else ""))
    if по_классам:
        lines.append("  по классам: "
                     + " · ".join(f"{k}={по_классам[k]}" for k in PROV_CLASSES
                                  if по_классам.get(k)))
    # машинная строка сводки: ею меряется корпус одним грепом по прогону
    lines.append(
        f"  СВОДКА slug={slug} манифест={'есть' if entries else ('битый' if merr else 'нет')} "
        f"кадров={len(frames)} с_записью={покрыто} без_записи={len(нет_записи)} "
        f"чужой_класс={len(чужой_класс)} без_режима={len(нет_режима)} "
        f"закрытый_канал={len(закрытый_канал)} "
        f"закрытый_канал_имя={len(закрытый_канал_имя)} inherited={унаследованных} "
        f"sourced={по_классам.get('sourced', 0)} "
        f"неполный_источник={len(неполный_источник)} "
        f"замечаний={len(замечания)} корень_сервиса={len(корень_сервиса)} "
        f"чужая_витрина={len(чужая_витрина)} "
        f"чужая_витрина_обложка={len(чужая_витрина_облож)} "
        f"свежая_без_манифеста={1 if свежая_без_манифеста else 0} "
        f"формат_разъехался={len(формат_разъехался)}")

    if report:
        return 0, lines
    # чужая витрина В ОБЛОЖКЕ роняет статью независимо от замка: признак судится
    # только там, где запись о съёмке есть, то есть на новом производстве, и
    # старый корпус без манифестов под него не попадает вовсе
    # Разъезд форматов роняет НЕЗАВИСИМО от замка и по той же причине, что и чужая
    # витрина в обложке: это не долг старого корпуса, а брак сегодняшней пересъёмки,
    # и виден он только там, где часть форматов уже переснята.
    if формат_разъехался:
        lines.append(
            f"  ! ФОРМАТЫ КАДРА РАЗЪЕХАЛИСЬ: {len(формат_разъехался)} - переснята "
            "часть форматов одного кадра, остальные остались от прошлой съёмки. "
            "FAIL жёсткий и в мягком режиме: сравниваются файлы, на которые "
            "ссылается САМА страница, поэтому ложного срабатывания на старом "
            "корпусе без пересъёмки быть не может")
        return 1, lines
    if чужая_витрина_облож:
        lines.append(
            f"  ! ЧУЖАЯ ВИТРИНА В ОБЛОЖКЕ: {len(чужая_витрина_облож)} - хиро либо "
            "og сняты с домена, которого предмет статьи не называет. Это первый "
            "визуал страницы и картинка, которая уходит в репост: чужой логотип, "
            "чужое меню и чужой призыв показываются от нашего имени. FAIL жёсткий "
            "и в мягком режиме тоже: признак срабатывает только при наличии записи "
            "о съёмке, то есть на кадрах после закона по решению автора, и долг старого "
            "корпуса под него не попадает")
        return 1, lines
    непокрыто = (len(нет_записи) + len(чужой_класс) + len(нет_режима)
                 + len(закрытый_канал) + len(неполный_источник)
                 + (len(чужая_витрина) if hard else 0)
                 + (1 if merr else 0)
                 + (1 if свежая_без_манифеста else 0))
    if непокрыто:
        if закрытый_канал:
            lines.append(f"  ! закрытый канал: {len(закрытый_канал)} "
                         f"(в имени кадра {len(закрытый_канал_имя)}, "
                         f"в тексте записи {len(закрытый_канал) - len(закрытый_канал_имя)}) - "
                         "запись подтверждает ПРОИСХОЖДЕНИЕ, а не законность "
                         "кадра. В тексте записи лечится пересъёмкой shot.py либо "
                         ".vizblock, в имени кадра - переименованием через "
                         "assets_base, а НЕ правкой формулировки записи и не "
                         "удалением манифеста")
        if нет_режима:
            lines.append(f"  ! записей без режима съёмки (mode): {len(нет_режима)} - "
                         "рукописная строка уликой съёмки не считается, кадр "
                         "перерегистрировать через shot.py")
        if неполный_источник:
            lines.append(f"  ! кадров class=sourced без полного паспорта источника: "
                         f"{len(неполный_источник)} - лечится перерегистрацией "
                         "через scripts/seo/images/imgsrc.py --vstavka (на машине "
                         "владельца), а не дописыванием поля руками")
        lines.append(f"  Кадров без легальной записи о съёмке: "
                     f"{len(нет_записи) + len(чужой_класс) + len(нет_режима) + len(закрытый_канал) + len(неполный_источник)}"
                     + (" (плюс манифест не читается)" if merr else ""))
        if hard:
            return 1, lines
        lines.append("  Мягкий режим: замечание видно в отчёте, стадию не роняем. "
                     "Замок включается флагом --provenance-hard")
        return 4, lines
    if замечания:
        if корень_сервиса and замок:
            lines.append(
                f"  ! class=result с адресом КОРНЯ сервиса: {len(корень_сервиса)} - "
                "это «скрин главной» вместо результата функции. Под замком "
                "--provenance-hard = FAIL: снять кадр по адресу самой функции "
                "(вход -> интерфейс -> готовый выход) либо сменить класс кадра")
            return 1, lines
        lines.append(f"  Записи есть у всех кадров, но есть замечания к классу "
                     f"result: {len(замечания)} - стадию не роняем"
                     + (" (замок --provenance-hard поднял бы корневой url до FAIL)"
                        if корень_сервиса else ""))
        return 4, lines
    if not frames:
        lines.append("  OK. Кадров в зоне гейта нет (ось закрыта .vizblock) - "
                     "подтверждать нечего.")
        return 0, lines
    lines.append("  OK. У каждого кадра статьи есть запись о съёмке легального класса.")
    return 0, lines


# ── гейт infra-leak: утечка служебной инфраструктуры автора в собранной странице
# (р9-по решению автора). ИНЦИДЕНТ: IP деплой-релея 203.0.113.10 утёк в ВИДИМЫЙ текст
# 6 статей (3 уже жили на проде) - ни один гейт стадии page это не поймал, потому
# что такого гейта не было вовсе. Список запрещённых литералов НЕ хардкожен здесь
# (article_gates.py - автор-дом, но правило «список отдельно от кода» держим и
# тут): читается из infra-secrets.txt рядом, по строке на литерал, # -комментарии
# и пустые строки пропускаются.
INFRA_LEAK_ROOT_RE = re.compile(r"root@(?:\d|msk)")
INFRA_LEAK_SEOSITE_RE = re.compile(r"ssh\s+seo-site\b")


def infra_leak_literals(path):
    """Список запрещённых литералов из infra-secrets.txt: одна непустая строка,
    не начинающаяся с #, - один литерал. Порядок как в файле, дубли не схлопывает
    (их и не бывает - файл маленький, ведёт его человек)."""
    out = []
    for line in tc_read(path).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def infra_leak_matches(text, literals):
    """[(литерал, номер_строки, фрагмент)] запрещённых литералов, найденных в
    СОБРАННОЙ странице (сырые байты index.html, не только видимый текст - IP мог
    утечь и в HTML-комментарий, и в script/meta).

    Большинство литералов (IP-адреса, домен хостинга, короткое имя сервера) -
    точная подстрока (без учёта регистра): у боевого хоста/IP нет легитимного
    двойника в обучающей статье, любое совпадение = утечка.

    ДВА литерала - ИСКЛЮЧЕНИЕ, голая подстрока дала бы ложные срабатывания на
    легитимных примерах внутри самих же SEO-статей (гайды учат SSH и хостингу):
      root@    - статьи сплошь несут generic-форму `ssh root@ваш-сервер` /
                 `root@example.com` как учебный пример - это НЕ утечка. Матчим
                 ТОЛЬКО «root@<цифра>» (IP/номер, форма реального адреса) или
                 «root@msk» (частый префикс хоста релея) - ровно форма
                 настоящей утечки, а не форма примера.
      seo-site - слово встречается безобидно в тексте вида «у твоего SEO-сайта»
                 / «seo-site-конструктор». Матчим ТОЛЬКО «ssh seo-site» (алиас
                 Host из ~/.ssh/config релея, реальная команда подключения),
                 не голое упоминание слова.
    Оба сужения - по САМОЙ ФОРМЕ утечки (реальный адрес/реальная команда), а не
    по контексту статьи, поэтому не зависят от темы конкретного гайда.
    """
    lines = text.splitlines()
    out = []
    for lit in literals:
        if lit == "root@":
            pattern = INFRA_LEAK_ROOT_RE
        elif lit == "seo-site":
            pattern = INFRA_LEAK_SEOSITE_RE
        else:
            pattern = re.compile(re.escape(lit), re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            m = pattern.search(line)
            if not m:
                continue
            frag = line.strip()
            if len(frag) > 160:
                start = max(0, m.start() - 40)
                frag = ("…" if start else "") + line[start:start + 160].strip() + "…"
            out.append((lit, i, frag))
    return out


def infra_leak_run(adir, secrets_path, page_path=None):
    """(rc, строки). rc: 0 - ни один запрещённый литерал не найден в СОБРАННОЙ
    странице · 1 - хотя бы один найден (поимённо: литерал + номер строки) ·
    2 - нет собранной страницы · 3 - список литералов не настроен (файла нет /
    файл пуст) - ГРОМКИЙ SKIP, не тихий PASS: молчаливое «нечем проверять» -
    ровно та дыра, из-за которой утёк IP релея (см. докстринг infra_leak_matches).
    """
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    lines = [f"infra-leak [page] {slug}"]
    if not existing(secrets_path):
        lines.append(f"  список запретных литералов не найден: {secrets_path}")
        lines.append("  ГЕЙТ SKIP - защиты от утечки служебной инфраструктуры на "
                     "этом прогоне НЕТ")
        return 3, lines
    literals = infra_leak_literals(secrets_path)
    if not literals:
        lines.append(f"  список запретных литералов пуст: {secrets_path}")
        lines.append("  ГЕЙТ SKIP - защиты от утечки служебной инфраструктуры на "
                     "этом прогоне НЕТ")
        return 3, lines
    page = page_path or os.path.join(adir, "index.html")
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 2, lines
    hits = infra_leak_matches(tc_read(page), literals)
    if not hits:
        lines.append(f"  OK. Ни один из {len(literals)} запрещённых литералов "
                     "не найден в собранной странице.")
        return 0, lines
    lines.append(f"  Найдено вхождений: {len(hits)}")
    lines += [f"  ! {lit} -> строка {ln}: {frag}" for lit, ln, frag in hits]
    return 1, lines


# ── гейт cta-position: место финального призыва в хвосте статьи ──────────────
#
# ЗАЧЕМ (правка владельца, волна р13). Финальный призыв стоял в самом
# подвале, ЗА частыми вопросами: /guide-bolt-new/index.html - источники 107898,
# памятка 109529, FAQ 110254, призыв 113852, дальше подвал. Читатель, дочитавший
# памятку, уже на пике готовности, а FAQ уводит его в сторону - призыв доставался
# только долиставшим до конца. Канон стал: памятка -> призыв -> частые вопросы.
#
# ПОЧЕМУ ГЕЙТ, А НЕ СТРОЧКА В КАНОНЕ. Порядок хвоста рождается ОДНОЙ строкой
# сборщика (build_page.build -> tail_parts). Текст правила такое не держит: любая
# соседняя волна, правящая тот же список, молча вернёт призыв в подвал, и ни один
# гейт стадии page этого не увидит - structure-check считает блоки, cta проверяет
# АДРЕС ссылки, frame-density смотрит в пиксель, и все трое одинаково зелены на
# любом порядке. Здесь проверяются ПОЗИЦИИ в собранных байтах.
#
# УНИВЕРСАЛЬНОСТЬ. Гейт знает только КЛАССЫ блоков шаблона (section#checklist,
# .cta-final, section#faq). Ни названия запуска, ни слова «<твой-продукт>», ни ссылок в
# нём нет: файл раздаётся ученикам, и у них та же оснастка статьи со своим
# оффером внутри призыва.

CTAPOS_CHK = "section#checklist"
CTAPOS_FIN = ".cta-final"
CTAPOS_FAQ = "section#faq"
CTAPOS_HUMAN = {CTAPOS_CHK: "памятка", CTAPOS_FIN: "блок финального призыва",
                CTAPOS_FAQ: "частые вопросы"}
CTAPOS_BLOCKS = (
    (CTAPOS_CHK, re.compile(r"""<section\b[^>]*\bid\s*=\s*["']checklist["']""", re.I)),
    (CTAPOS_FIN, re.compile(
        r"""<(?:section|aside|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bcta-final\b[^"']*["']""",
        re.I)),
    (CTAPOS_FAQ, re.compile(r"""<section\b[^>]*\bid\s*=\s*["']faq["']""", re.I)),
)


def ctapos_dead_spans(text):
    """Диапазоны, где разметки нет: HTML-комментарии, <style>, <script>.

    Тот же класс дефекта, что фикс по решению автора у tc_strip_comments: шаблон
    page-template.html несёт длинные комментарии с ПРИМЕРАМИ разметки, а инлайн-CSS
    и JS - имена классов строками. Наивный поиск считал бы прозу четвёртым блоком.
    Позиции меряются по ОРИГИНАЛУ (иначе числа в отчёте не сойдутся с грепом по
    файлу), поэтому не вырезаем, а выбрасываем совпадения, попавшие внутрь.
    """
    spans = []
    for rx in (r"<!--.*?-->", r"<style\b.*?</style\s*>", r"<script\b.*?</script\s*>"):
        spans += [(m.start(), m.end()) for m in re.finditer(rx, text, re.S | re.I)]
    return spans


def ctapos_positions(text, rx):
    """Позиции живых (не закомментированных) вхождений блока в порядке документа."""
    dead = ctapos_dead_spans(text)
    return [m.start() for m in rx.finditer(text)
            if not any(a <= m.start() < b for a, b in dead)]


def cta_position_run(adir, page_path=None):
    """(rc, строки). rc: 0 - порядок памятка < призыв < частые вопросы ·
    1 - блок отсутствует либо стоит не там (поимённо, с позициями) ·
    2 - нет собранной страницы. Тихого PASS не бывает: молчаливый пропуск
    обязательного гейта и есть зелёная ложь."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    lines = [f"cta-position [page] {slug}"]
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 2, lines
    page_text = tc_read(page)
    lines.append(" канон хвоста (правка владельца): памятка "
                 f"{CTAPOS_CHK} -> финальный призыв {CTAPOS_FIN} -> частые "
                 f"вопросы {CTAPOS_FAQ}")
    поз = {}
    for имя, rx in CTAPOS_BLOCKS:
        поз[имя] = ctapos_positions(page_text, rx)
        lines.append(f"  {имя} ({CTAPOS_HUMAN[имя]}): найдено {len(поз[имя])}"
                     + (", позиции: " + ", ".join(str(x) for x in поз[имя])
                        if поз[имя] else " - НЕТ НИ ОДНОГО"))
    bad = []
    нет = [имя for имя, _ in CTAPOS_BLOCKS if not поз[имя]]
    for имя in нет:
        bad.append(f"ОТСУТСТВУЕТ: {имя} ({CTAPOS_HUMAN[имя]}) - на собранной "
                   "странице нет ни одного такого блока, порядок проверять не на чем")
    if not нет:
        p_chk, p_faq = поз[CTAPOS_CHK][0], поз[CTAPOS_FAQ][0]
        if p_chk > p_faq:
            bad.append(f"ПОРЯДОК: {CTAPOS_CHK} на {p_chk} стоит ПОСЛЕ {CTAPOS_FAQ} "
                       f"на {p_faq} - хвост собран задом наперёд")
        for p in поз[CTAPOS_FIN]:
            if p < p_chk:
                bad.append(f"ПОРЯДОК: {CTAPOS_FIN} на {p} стоит ДО {CTAPOS_CHK} на "
                           f"{p_chk} - призыв раньше памятки, читатель ещё не дошёл "
                           "до пика готовности")
            elif p > p_faq:
                bad.append(f"ПОРЯДОК: {CTAPOS_FIN} на {p} стоит ПОСЛЕ {CTAPOS_FAQ} на "
                           f"{p_faq} - призыв в подвале, канон требует его МЕЖДУ "
                           "памяткой и частыми вопросами")
    if not bad:
        lines.append(f"  OK. Порядок хвоста канонный: {CTAPOS_CHK}("
                     f"{поз[CTAPOS_CHK][0]}) < {CTAPOS_FIN}("
                     + ", ".join(str(x) for x in поз[CTAPOS_FIN])
                     + f") < {CTAPOS_FAQ}({поз[CTAPOS_FAQ][0]}).")
        return 0, lines
    lines.append(f"  Дефектов: {len(bad)}")
    lines += [f"  ! {x}" for x in bad]
    return 1, lines


# ── гейт toc-mobile: удалённое оглавление-кнопка не вернулось ────────────────
#
# ЗАЧЕМ (канон волны р13, по решению автора). В теле статьи стоял
# details.toc-mobile - раскрывающееся оглавление, которое надо раскрывать
# нажатием, и внизу экрана его же пилюля-кнопка «Содержание». Такое оглавление
# признано неудобным для читателя и выведено из канона целиком: блок,
# пилюля, шторка и все их правила из движка вырезаны; оглавление на странице
# осталось РОВНО ОДНО - липкая колонка aside.toc-desktop, её не надо раскрывать.
#
# ПОЧЕМУ ГЕЙТ-НЕГАТИВ, А НЕ СТРОЧКА В КАНОНЕ. Ровно та же логика, что у
# cta-position: блок рождался ОДНИМ токеном шаблона и ОДНИМ куском сборщика.
# Соседняя волна, правящая ту же обвязку (или откат из любого .bak), молча
# вернёт его - и ни один прежний гейт этого не увидит: structure-check считает
# паритет пунктов (одно оглавление вместо двух ему законно), cta смотрит АДРЕС
# ссылки, frame-density - в пиксель. Здесь проверяются БАЙТЫ собранной страницы.
#
# ЧТО ИМЕННО ЛОВИТ. Живой (не в комментарии, не в <style>, не в <script>) тег с
# классом toc-mobile - в любой обёртке, не только <details>: возврат «тем же по
# смыслу блоком под другим тегом» - тот же самый дефект. Инертный JS и мёртвые
# CSS-правила на СТАРЫХ страницах гейт намеренно НЕ ловит: без блока разметки
# пилюля не создаётся (скрипт выходит на первом же querySelector), человек не
# видит ничего, а нож корпуса toc_mobile_strip.py режет РОВНО блок и обязан
# после реза получить у этого гейта чистый PASS.
#
# УНИВЕРСАЛЬНОСТЬ. Гейт знает только КЛАСС блока оснастки. Ни названия запуска,
# ни ссылок, ни имён ботов в нём нет: файл раздаётся ученикам, и у них та же
# оснастка статьи.

TOCM_BLOCK = "details.toc-mobile"
TOCM_DESK = "aside.toc-desktop"
TOCM_RE = re.compile(
    r"""<(?:details|nav|aside|div|section|ul|ol)\b[^>]*\bclass\s*=\s*["'][^"']*"""
    r"""\btoc-mobile\b[^"']*["']""", re.I)
TOCM_DESK_RE = re.compile(
    r"""<(?:aside|nav|div|section)\b[^>]*\bclass\s*=\s*["'][^"']*"""
    r"""\btoc-desktop\b[^"']*["']""", re.I)


# ── гейт retract-sync (r14 круг 15, по решению автора) ───────────────────────────────
#
# 🔴 ДЫРА, которую он закрывает. Приёмка правит ТЕКСТ по улике и на этом
# останавливается, а файл, ОТКУДА утверждение приехало в текст (research.md),
# остаётся нетронутым. Живой случай guide-neyroset-kandinskiy: выдуманную точку
# замера «сеть США» сняли из статьи кругом 11, а строка «Веб-фетчер Claude
# (сеть США)» до круга 15 стояла в research.md - откуда однажды уже переехала в
# draft.md и продержалась шесть раундов приёмки. Ни один гейт в research.md не
# заглядывал вовсе.
#
# КОНТРАКТ, простой и машинный. Отзыв утверждения оформляется в логе прогона
# одной строкой: `ОТОЗВАНО-ФРАЗА: «дословная снятая формулировка»`. Гейт
# собирает такие строки по terminal-outputs/ и ищет эти формулировки в
# draft.md, research.md и index.html. Нашёл там, где рядом (в пределах 400
# знаков перед местом) НЕТ пометки отзыва - красный: снятое утверждение живёт
# и вернётся в текст следующим кругом.
#
# ПОЧЕМУ ОКНО, А НЕ СТРОКА. В md текст переносится по ширине, отозванная цитата
# спокойно ложится на две-три строки; пометка отзыва стоит перед ней абзацем.
# Поэтому сверяется нормализованный поток, а не построчный grep.
RETRACT_DECL_RE = re.compile(
    r"^\s*ОТОЗВАНО-ФРАЗА\s*:\s*[«\"](?P<p>.+?)[»\"]\s*$", re.M)
RETRACT_MARK_RE = re.compile(r"отозван|не мерялась|подмена|снял[аи]?\b", re.I)
RETRACT_TARGETS = ("draft.md", "research.md", "index.html")
RETRACT_WINDOW = 400


def retract_norm(s):
    """Нормализация для сверки: без markdown-подчёркиваний, один пробел, регистр."""
    s = re.sub(r"[*`_]+", "", s or "")
    s = s.replace("ё", "е").replace("Ё", "Е")
    return re.sub(r"\s+", " ", s).strip().lower()


def retract_norm_map(text):
    """(нормализованный поток, [номер строки на каждый его символ])."""
    out, lines = [], []
    prev_space = True
    ln = 1
    for ch in (text or ""):
        if ch == "\n":
            ln += 1
            ch = " "
        if ch in "*`_":
            continue
        if ch in "ёЁ":
            ch = "е" if ch == "ё" else "Е"
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            lines.append(ln)
            prev_space = True
            continue
        out.append(ch.lower())
        lines.append(ln)
        prev_space = False
    return "".join(out), lines


def retract_phrases(to_dir):
    """[(фраза, файл лога)] - реестр отозванных формулировок. Строки-комментарии
    (начинаются с #) не берутся: там живёт описание контракта, а не отзыв."""
    found = []
    if not to_dir or not os.path.isdir(to_dir):
        return found
    for name in sorted(os.listdir(to_dir)):
        if not name.lower().endswith((".log", ".txt", ".md")) or ".bak" in name:
            continue
        p = os.path.join(to_dir, name)
        if not os.path.isfile(p):
            continue
        try:
            raw = tc_read(p)
        except OSError:
            continue
        for line in raw.splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = RETRACT_DECL_RE.match(line)
            if m and len(m.group("p").strip()) >= 10:
                found.append((m.group("p").strip(), name))
    return found


def st_klass_stati(adir, fm):
    """Отнесена ли статья к классу «свежая узкая тема».

    Два независимых источника, любого достаточно: поле front-matter черновика
    (`klass`/`класс`) и поле `кластер` в `spec.json` рядом. Ни одного - гейт
    не применяется и говорит об этом вслух, а не молчит."""
    for ключ in ("klass", "класс", "class", "cluster", "кластер"):
        v = str(fm.get(ключ) or "").strip().lower()
        if v and ("свеж" in v or "инфоповод" in v or "svezh" in v or "infopovod" in v):
            return True, "front-matter %s: %s" % (ключ, v)
    сп = os.path.join(adir, "spec.json")
    if os.path.isfile(сп):
        try:
            d = json.load(open(сп, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {}
        for ключ in ("кластер", "cluster", "класс", "klass"):
            v = str((d or {}).get(ключ) or "").strip().lower()
            if v and ("свеж" in v or "инфоповод" in v or "svezh" in v):
                return True, "spec.json %s: %s" % (ключ, v)
    return False, "ни в front-matter, ни в spec.json класс не назван"


def st_golova(fm, body):
    """Голова темы: front-matter, иначе первый H1 тела."""
    for ключ in ("tema", "тема", "title", "head", "golova", "голова"):
        v = str(fm.get(ключ) or "").strip()
        if v:
            return v
    m = re.search(r"^#\s+(.+)$", body or "", re.M)
    return m.group(1).strip() if m else ""


def st_decil(голова):
    """Признаки П1 и П2 из radar_to_queue.py - ОДИН источник правила на два
    места (вход темы и гейт черновика). Модуль недоступен - ГРОМКИЙ отказ
    (ERROR), а не тихий пропуск: барьер, который молча выключился, хуже
    отсутствующего."""
    путь = os.path.expanduser("~/.business/scripts/seo")
    if путь not in sys.path:
        sys.path.insert(0, путь)
    try:
        from radar_to_queue import г4_decil  # noqa: E402
    except ImportError:
        # ПАКЕТ БЕЗ СБОРЩИКА ОЧЕРЕДИ ТЕМ. Признаки верхнего дециля живут в
        # твоём скрипте-сборщике очереди тем: его собирает Клод по инструкции
        # скилла seo-dvizhok, в поставку он не входит. Пока скрипта нет, C3
        # не проверяется, и об этом сказано вслух - C1 и C2 продолжают судить
        return None, "правило верхнего дециля недоступно: нет скрипта-сборщика очереди тем", []
    return г4_decil(голова)


def svezhaya_tema_run(adir, draft_path=None):
    """Гейт закона 25: подача статьи класса «свежая узкая тема».

    Три проверки, каждая - строка закона:
      C1 событие названо и ДАТИРОВАНО в первых 300 знаках тела
      C2 есть свой слой поверх источника, а не пересказ новости
      C3 голова темы проходит признаки верхнего дециля П1 и П2
    """
    lines = []
    путь = draft_path or os.path.join(adir, "draft.md")
    if not os.path.isfile(путь):
        return 2, ["svezhaya-tema: нет черновика %s" % путь]
    текст = tc_read(путь)
    fm, body = tc_front_matter(текст)
    класс, почему = st_klass_stati(adir, fm)
    if not класс:
        lines.append("svezhaya-tema: НЕ ПРИМЕНИМ - %s" % почему)
        lines.append("  гейт судит только класс «свежая узкая тема»; "
                     "статьи класса «голова спроса» он не касается")
        return 0, lines
    lines.append("svezhaya-tema: класс подтверждён (%s)" % почему)
    тело = tc_strip_fences(body)
    тело_бз = re.sub(r"^#{1,6}\s*", "", тело, flags=re.M)
    голова = st_golova(fm, body)
    плохо = []

    окно = тело_бз.strip()[:ST_ОКНО_ЗНАКОВ]
    m = ST_ДАТА.search(окно)
    if m:
        lines.append("  C1 дата события в первых %d знаках: «%s»"
                     % (ST_ОКНО_ЗНАКОВ, m.group(0)))
    else:
        плохо.append("C1: в первых %d знаках тела нет даты события. Читатель "
                     "пришёл из выдачи проверить, правда ли это, и подводка "
                     "перед фактом убивает страницу" % ST_ОКНО_ЗНАКОВ)

    низ = тело.lower()
    свои = [s for s in ST_СВОЙ_СЛОЙ if s in низ]
    if свои:
        lines.append("  C2 свой слой поверх источника: %s" % ", ".join(свои[:3]))
    else:
        плохо.append("C2: нет своего слоя поверх источника. Донор в теме - "
                     "ориентир по интенту, а не образец текста: нужен раздел "
                     "«что это меняет», «что теперь делать», «где ломается» "
                     "или собственная проверка")

    if not голова:
        плохо.append("C3: голова темы не найдена ни во front-matter, ни в H1")
    else:
        try:
            ок, причина, признаки = st_decil(голова)
        except Exception as e:  # noqa: BLE001
            return 2, lines + ["  C3 ОШИБКА: правило верхнего дециля недоступно "
                               "(%s). Гейт не притворяется зелёным" % e]
        if ок is None:
            lines.append("  C3 НЕ ПРОВЕРЕН: %s. Гейт судит C1 и C2" % причина)
        elif ок:
            lines.append("  C3 голова «%s»: %s (%s)"
                         % (голова, причина, "; ".join(признаки)))
        else:
            плохо.append("C3: голова «%s» не проходит признаки верхнего дециля "
                         "класса - %s. Замер по решению автора: страницы без этих признаков "
                         "дали 0.0000 клика в день" % (голова, причина))

    for п in плохо:
        lines.append("  🔴 " + п)
    if плохо:
        lines.append("svezhaya-tema: FAIL, нарушений %d" % len(плохо))
        return 1, lines
    lines.append("svezhaya-tema: PASS, три правила класса соблюдены")
    return 0, lines


# ── гейты дельты топ-3 (волна 3 захода 2026-08-29-seo-x4-kanon) ──────────────
#
# ЗАЧЕМ. Побайтовая дельта 24 живых пар «его страница в топ-3 против нашей
# ниже» (MODEL-TRAFIKA-KONKURENTOV.md, раздел «Механика топ-3») дала из 18
# факторов ровно ДВА в пользу конкурентов, остальные 16 у нас уже лучше:
#   год в title            38% у них против 0% у нас, дельта +38 пп
#   внутренних ссылок      медиана 40 у них против 30 у нас, x1.31
# Третья гипотеза (title точнее зеркалит запрос) замерена волной 3 отдельно и
# НЕ подтвердилась - наши заголовки точнее (0.6696 против 0.5109), поэтому
# третьего гейта здесь нет и не будет: канон получает только измеренное.
#
# ПОЧЕМУ КОДОМ. Правило, которое держит инструкция, отваливается на третьей
# статье подряд - тот же довод, по которому кодом стал закон 25.

RC_TITLE_GOD = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}
TG_ГОД = re.compile(r"\b20\d\d\b")
# Тема, ответ на которую живёт во времени. Год требуется ТОЛЬКО у неё: на
# вечнозелёной теме год в title лишь состарит сниппет через четыре месяца.
# Класс определяет машина по маркерам темы, а не память агента.
TG_МАРКЕРЫ = (
    ("релиз/версия", ("релиз", "верси", "обновлен", "апдейт", "вышел", "вышла",
                      "вышло", "анонс", "запустил", "открыл доступ", "отключ")),
    ("цена/доступ", ("цена", "цены", "стоимост", "сколько стоит", "тариф",
                     "подписк", "оплат", "купить", "из россии", "доступ")),
    ("рейтинг/подборка", ("лучш", "топ-", "топ ", "рейтинг", "подборк",
                          "сравнен", "альтернатив", "аналог")),
    ("актуальность", ("работает ли", "актуальн", "сейчас", "все еще",
                      "еще работает", "в этом году")),
)


def tg_нормализовать(строка):
    return (строка or "").lower().replace("ё", "е")


def tg_datiruemaya(*строки):
    """(датируемая ли тема, список сработавших групп с маркерами)."""
    низ = " · ".join(tg_нормализовать(s) for s in строки if s)
    сработали = []
    for группа, маркеры in TG_МАРКЕРЫ:
        нашлись = [m for m in маркеры if m in низ]
        if нашлись:
            сработали.append("%s: %s" % (группа, ", ".join(нашлись[:3])))
    return bool(сработали), сработали


def tg_title_i_klyuchi(adir, fm, body):
    """title статьи и строка ключей, по которым судится класс темы."""
    title = str(fm.get("title") or "").strip()
    if not title:
        m = re.search(r"^#\s+(.+)$", body or "", re.M)
        title = m.group(1).strip() if m else ""
    куски = [title, str(fm.get("h1") or ""), st_golova(fm, body)]
    kw = fm.get("keywords")
    if isinstance(kw, (list, tuple)):
        куски += [str(x) for x in kw]
    elif kw:
        куски.append(str(kw))
    сп = os.path.join(adir, "spec.json")
    if os.path.isfile(сп):
        try:
            d = json.load(open(сп, encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            d = {}
        for ключ in ("title", "h1", "тема", "tema"):
            if d.get(ключ):
                куски.append(str(d[ключ]))
    return title, куски


def title_god_run(adir, draft_path=None):
    """Гейт «год в title у датируемой темы».

    0 - PASS (год стоит либо тема вечнозелёная) · 1 - FAIL · 2 - ERROR.
    Тема вечнозелёная - гейт говорит «НЕ ПРИМЕНИМ» вслух, а не молчит зелёным.
    """
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    путь = draft_path or os.path.join(adir, "draft.md")
    if not os.path.isfile(путь):
        return 2, ["title-god: нет черновика %s" % путь]
    fm, body = tc_front_matter(tc_read(путь))
    title, куски = tg_title_i_klyuchi(adir, fm, body)
    lines = ["title-god [draft] %s" % slug, "  · title: «%s»" % title]
    if not title:
        return 2, lines + ["  ОШИБКА: у статьи нет ни title во front-matter, "
                           "ни H1 в теле - судить нечего"]
    # 🔴 ГОД В СЛАГЕ ЗАПРЕЩЁН (по решению автора, круг 2, запись R72). Правило судится
    # ВСЕГДА, до и независимо от вопроса о датируемости: title переписывается
    # бесплатно хоть каждый январь, а слаг не переписывается никогда - у него
    # внешние ссылки, история индексации и закон владельца о неудалении. Эталон
    # держит год в title и НЕ держит в URL, и это правильный размен.
    # Исключение одно и оно про ПРЕДМЕТ: если годы и есть тема статьи
    # (диапазон вида `2026-2035`), слаг честно их несёт.
    год_в_слаге = re.search(r"-(20\d\d)$", slug)
    диапазон_лет = re.search(r"-20\d\d-20\d\d(?:$|-)", slug)
    if год_в_слаге and not диапазон_лет:
        lines.append("  🔴 ГОД В СЛАГЕ: «%s» кончается на «%s». Год обязан стоять "
                     "в title и НЕ обязан в URL: title обновляется бесплатно, слаг "
                     "не переписывается никогда (внешние ссылки, история индексации, "
                     "закон неудаления). Замер: эталон держит год в title "
                     "«Claude Code: подписка, цена и как купить из России в 2026» и "
                     "НЕ держит в URL «/guides/claude-code-podpiska/»."
                     % (slug, год_в_слаге.group(1)))
        lines.append("  Чинить ДО публикации переименованием слага: после выхода "
                     "на прод URL уже не меняют, там остаётся редирект и потеря "
                     "сигналов")
        lines.append("title-god: FAIL, нарушений 1")
        return 1, lines

    датируемая, группы = tg_datiruemaya(*куски)
    if not датируемая:
        lines.append("  НЕ ПРИМЕНИМ: тема вечнозелёная, ни один маркер "
                     "изменчивости во времени не сработал (релиз/версия, "
                     "цена/доступ, рейтинг/подборка, актуальность)")
        lines.append("  год в title тут не требуется: он только состарит сниппет")
        return 0, lines
    lines.append("  тема датируемая: " + " | ".join(группы))
    m = TG_ГОД.search(title)
    if m:
        lines.append("  OK. Год «%s» стоит в title." % m.group(0))
        return 0, lines
    lines.append("  🔴 в title датируемой темы нет года. Замер 24 живых пар "
                 "топ-3: год в title стоит у 38% страниц, которые нас "
                 "обходят, и у 0% наших (MODEL-TRAFIKA-KONKURENTOV.md, "
                 "раздел «Механика топ-3»)")
    lines.append("  ФОРМА ГОДА: пиши «2026 года» или «в 2026 году», а не голое "
                 "«2026» в хвосте заголовка. Барьер русского заголовка в "
                 "цепочке публикации требует за КАЖДЫМ числом считаемое "
                 "существительное и роняет голый год (живой отказ по решению автора "
                 "на первой же статье транша)")
    lines.append("title-god: FAIL, нарушений 1")
    return 1, lines


# ── ГЕЙТ own-run-shagi: учу только тому, куда заходил (рв даты запуска.2026) ───────
#
# ЗАЧЕМ (урок владельца, дословно: «чему ты человека можешь научить,
# если ты внутрь не заходил?»). Круг 1 конвейера выпустил в живой прод три
# статьи из пяти, где обучающий раздел написан СНАРУЖИ витрины, а капсула первой
# строкой утверждает «Проверил по решению автора живьём». Живой случай: `guide-ltx-studio-
# 2026` несёт четыре шага по интерфейсу («Куда нажать: открой сервис и найди
# поле для описания проекта. Оно первое на экране, мимо не пройдёшь», «открой
# любую сцену из списка», «Что увидишь: кадры сцены, описание каждого и
# настройки движения камеры»), а его собственный `research.md` говорит: живьём
# снята ТОЛЬКО страница тарифов. Внутрь продукта никто не заходил, регистрации
# не было, все три кадра статьи - одна и та же страница `/pricing`.
#
# ЧТО СУДИТСЯ. Черновик, который ВЕДЁТ ЧИТАТЕЛЯ ПО ИНТЕРФЕЙСУ, обязан иметь в
# манифесте съёмки хотя бы один кадр класса `own-run` - наш собственный экран.
# «Ведёт по интерфейсу» определяется машиной по маркерам-инструкциям («куда
# нажать», «что увидишь», «открой», «нажми», «мимо не пройдёшь»), а не по
# самоощущению агента. Порог два разных маркера: одиночная фраза «что увидишь»
# бывает и в разборе чужого скриншота, а пара разных маркеров - это уже
# пошаговая инструкция.
#
# ВТОРОЙ ПРЕДМЕТ ГЕЙТА - ЗАЯВЛЕНИЕ О ЖИВОЙ ПРОВЕРКЕ. Формулировка «проверил
# живьём» в теле требует того же кадра: она и есть обещание читателю, что автор
# был внутри. Заявление без единого own-run кадра - ровно тот регресс, за
# который заплачено по решению автора.
#
# ЧЕГО ГЕЙТ НЕ ДЕЛАЕТ. Он не решает за автора, ЧТО описывать: статья про сервис,
# внутрь которого не попасть бесплатно, проходит гейт двумя законными путями -
# либо снять свой экран на доступном участке (регистрация, бесплатный вход,
# публичная демка), либо УБРАТЬ пошаговые маркеры и писать «по документации» и
# «по странице тарифов». Обе дороги честные, и гейт ровно это и оставляет.
ORS_МАРКЕРЫ = (
    ("куда нажать", ("куда нажать", "куда жать", "где нажать")),
    ("что увидишь", ("что увидишь", "что ты увидишь", "увидишь на экране",
                     "что появится на экране")),
    ("прямая команда", ("открой ", "нажми ", "введи ", "выбери ", "перетащи ",
                        "кликни ", "зайди в ")),
    ("мимо не пройдёшь", ("мимо не пройдешь", "мимо не пройдёшь",
                          "не промахнешься", "не промахнёшься",
                          "первое на экране", "сразу увидишь")),
)
ORS_ЖИВЬЁМ = re.compile(
    r"проверил[а]?\s+(?:[^\n]{0,40}?)?жив[ьъ]?[её]м|проверено\s+жив[ьъ]?[её]м|"
    r"зашел внутрь|зашёл внутрь|прошел путь сам|прошёл путь сам", re.I)
RC_ORS = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}


def ors_markery(body):
    """Сработавшие группы маркеров пошаговой инструкции по интерфейсу."""
    низ = tg_нормализовать(body)
    сработали = []
    for группа, маркеры in ORS_МАРКЕРЫ:
        нашлись = [m for m in маркеры if m in низ]
        if нашлись:
            сработали.append((группа, нашлись))
    return сработали


def own_run_shagi_run(adir, draft_path=None):
    """Гейт «пошаговая инструкция требует кадра со своего экрана».

    0 - PASS (инструкции нет либо own-run кадр есть) · 1 - FAIL · 2 - ERROR.
    """
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    путь = draft_path or os.path.join(adir, "draft.md")
    if not os.path.isfile(путь):
        return 2, ["own-run-shagi: нет черновика %s" % путь]
    fm, body = tc_front_matter(tc_read(путь))
    lines = ["own-run-shagi [draft] %s" % slug]
    группы = ors_markery(body)
    заявление = ORS_ЖИВЬЁМ.search(body or "")
    нужен = len(группы) >= 2 or bool(заявление)
    if группы:
        lines.append("  маркеры пошаговой инструкции: "
                     + " | ".join("%s (%s)" % (г, ", ".join(м[:2]))
                                  for г, м in группы))
    else:
        lines.append("  маркеров пошаговой инструкции по интерфейсу нет")
    if заявление:
        lines.append("  заявление о живой проверке в теле: «%s»"
                     % заявление.group(0).strip())
    if not нужен:
        lines.append("  НЕ ПРИМЕНИМ: статья читателя по интерфейсу не ведёт и "
                     "живой проверки не заявляет - свой экран тут не обязателен")
        return 0, lines
    mpath = os.path.join(adir, PROV_MANIFEST_NAME)
    entries, merr = prov_manifest_load(mpath)
    if merr:
        return 2, lines + ["  ОШИБКА: манифест съёмки не читается: %s" % merr]
    свои = [e for e in (entries or [])
            if str(e.get("class") or "").strip() == "own-run"]
    lines.append("  кадров own-run в %s: %d из %d записей"
                 % (PROV_MANIFEST_NAME, len(свои), len(entries or [])))
    if свои:
        lines.append("  OK. Свой экран есть: "
                     + ", ".join(str(e.get("file") or "?") for e in свои[:3]))
        return 0, lines
    lines.append("  🔴 статья ведёт читателя по интерфейсу (либо заявляет живую "
                 "проверку), а в манифесте съёмки НЕТ ни одного кадра класса "
                 "own-run - своего экрана. Урок владельца: «чему ты "
                 "человека можешь научить, если ты внутрь не заходил?»")
    lines.append("  две законные дороги: (1) зайти самому на доступном участке и "
                 "снять свой экран через shot.py --class own-run; (2) убрать "
                 "маркеры «куда нажать / что увидишь / мимо не пройдёшь» и "
                 "заявление о живой проверке, а раздел переписать честно - по "
                 "документации, по странице тарифов, по публичному первоисточнику")
    lines.append("own-run-shagi: FAIL, нарушений 1")
    return 1, lines


RC_VNUTR = {0: "PASS", 1: "FAIL", 2: "ERROR", 4: "WARN", None: "ERROR"}
# Порог взят НИЖНЕЙ планкой, а не медианой топ-3 (40): канон отвечает за пол,
# а не за среднее. Прежний хард-минимум structure-check был 3.
# 🔴 ПОДНЯТ по решению автора (дефект T6 круга 1) с 12 до 20. Причина числом: прогон
# прежнего порога по десяти СТАРЫМ страницам прода дал 8 · 26 · 22 · 29 · 17 ·
# 17 · 16 · 16 · 5 · 18, то есть восемь из десяти проходили гейт БЕЗ ЕДИНОЙ
# ПРАВКИ, и в регрессии он не уронил ни одной статьи. Барьер, который живой
# корпус проходит с запасом, стандарт не двигает - он только выглядит барьером.
# Новый пол 20 взят между нашим живым уровнем (медиана 28.5 по документу, 17-18
# по телу main) и медианой топ-3 (40): это пол, а не среднее, и он роняет 4 из
# 10 старых страниц, то есть реально режет нижнюю половину корпуса.
VN_МИНИМУМ = 20
VN_ОБВЯЗКА = re.compile(r"(?is)<(nav|header|footer|aside)\b.*?</\1>")


def vn_domain(config_path=None):
    """Свой домен из config.md скилла. Путь приходит СНАРУЖИ, а не резолвится
    молча к боевому файлу: иначе селфтест ходил бы в конфиг машины и песочница
    перестала бы быть герметичной (тот же контракт, что у cta_run)."""
    try:
        cfg = article_build.load_config(config_path)
    except Exception:  # noqa: BLE001
        return ""
    return str(cfg.get("domain") or "").strip()


def vn_svoya(href, domain):
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return False
    if href.startswith("//"):
        return bool(domain) and href[2:].startswith(domain)
    if href.startswith("/"):
        return True
    if domain and domain in href:
        return True
    return False


def vn_schitat_draft(body, domain):
    return [m.group(1) for m in re.finditer(r"\]\(([^)\s]+)", body or "")
            if vn_svoya(m.group(1), domain)]


def vn_telo_stranicy(page):
    """Тело страницы без служебной обвязки: меню, шапка, подвал, сайдбар.

    Считать ссылки по всему документу нельзя - тогда порог берётся одним
    меню, и гейт становится украшением: он бы горел зелёным на статье с нулём
    контекстных ссылок."""
    m = re.search(r"(?is)<main\b[^>]*>(.*?)</main>", page or "")
    if not m:
        m = re.search(r"(?is)<article\b[^>]*>(.*?)</article>", page or "")
    кусок = m.group(1) if m else (page or "")
    return VN_ОБВЯЗКА.sub(" ", кусок)


def vn_schitat_page(page, domain):
    тело = vn_telo_stranicy(page)
    return [m.group(1) for m in
            re.finditer(r"(?is)<a\b[^>]*?\bhref\s*=\s*[\"']([^\"']+)[\"']", тело)
            if vn_svoya(m.group(1), domain)]


def vnutrennie_ssylki_run(adir, stage="draft", draft_path=None, page_path=None,
                          minimum=VN_МИНИМУМ, config_path=None, revision=False):
    """Гейт «минимум внутренних ссылок в теле новой страницы».

    0 - PASS · 1 - FAIL · 2 - ERROR (нечего читать).
    Ссылки считаются в ТЕЛЕ: у черновика это весь текст после front-matter,
    у собранной страницы - main/article без меню, шапки, подвала и сайдбара.
    """
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    domain = vn_domain(config_path)
    lines = ["vnutrennie-ssylki [%s] %s" % (stage, slug),
             "  · свой домен для счёта: %s" % (domain or "не прочитан из config.md, "
                                               "считаются только корневые пути")]
    if stage == "page":
        цель = page_path or os.path.join(adir, "index.html")
        if not os.path.isfile(цель):
            return 2, lines + ["  ОШИБКА: нет собранной страницы %s" % цель]
        ссылки = vn_schitat_page(tc_read(цель), domain)
    else:
        цель = draft_path or os.path.join(adir, "draft.md")
        if not os.path.isfile(цель):
            return 2, lines + ["  ОШИБКА: нет черновика %s" % цель]
        _fm, body = tc_front_matter(tc_read(цель))
        ссылки = vn_schitat_draft(tc_strip_fences(body), domain)
    уник = sorted(set(ссылки))
    lines.append("  внутренних ссылок в теле: %d (уникальных адресов %d), "
                 "минимум %d" % (len(ссылки), len(уник), minimum))
    lines.append("  первые адреса: " + (", ".join(уник[:6]) if уник else "нет"))
    if len(ссылки) >= minimum:
        lines.append("  OK. Перелинковка держит канон дельты топ-3.")
        return 0, lines
    lines.append("  🔴 перелинковки не хватает: %d из %d. Замер 24 живых пар "
                 "топ-3 дал медиану 40 внутренних ссылок у страниц, которые "
                 "нас обходят, против наших 30 (x1.31); на обеих парах с "
                 "якорем владельца - 40/22 и 48/41"
                 % (len(ссылки), minimum))
    # 🔴 ЖЁСТКОСТЬ СНИМАЕТ --revision (по решению автора, круг 2, запись R69) - тем же
    # приёмом, что у title-ctr, tool-article и novice. Гейт заведён, чтобы
    # поднять пол НОВОГО производства, и на новой странице он остаётся жёстким.
    # Но у него была дыра: на РЕВИЗИИ старой страницы он тоже краснел намертво,
    # а ревизия - это единственный законный способ поставить входящую ссылку на
    # новую страницу. Получалось, что гейт перелинковки САМ ЗАПРЕЩАЛ чинить
    # перелинковку: старая страница написана до порога 20, ссылку в неё не
    # добавить, и новая страница остаётся без входящих. Живой случай по решению автора:
    # guide-bolt-new, guide-neyroset-dlya-ucheby и guide-ceny-neyrosetey не
    # пускались на прод с одной добавленной контекстной ссылкой.
    if revision:
        lines.append("  РЕВИЗИЯ: старая страница писалась до этого порога, "
                     "замечание не роняет стадию. На НОВОЙ странице тот же "
                     "случай остаётся FAIL")
        lines.append("vnutrennie-ssylki: WARN (режим ревизии), нарушений 1")
        return 4, lines
    lines.append("vnutrennie-ssylki: FAIL, нарушений 1")
    return 1, lines


def retract_sync_run(adir, targets=RETRACT_TARGETS):
    """(rc, строки). rc: 0 - живых отозванных формулировок нет · 1 - найдены ·
    2 - нет каталога статьи. Реестра нет вовсе -> 0 и явная строка об этом:
    гейт не выдумывает отзывы, он держит уже объявленные."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    lines = [f"retract-sync [draft] {slug}"]
    if not os.path.isdir(adir):
        lines.append(f"  ОШИБКА: нет каталога статьи {adir}")
        return 2, lines
    to_dir = os.path.join(adir, "terminal-outputs")
    reestr = retract_phrases(to_dir)
    lines.append(f"  реестр отозванных формулировок: {len(reestr)} строк "
                 f"«ОТОЗВАНО-ФРАЗА: «…»» в terminal-outputs/")
    if not reestr:
        lines.append("  · отзывов не объявлено - сверять нечего (PASS). Отзыв "
                     "оформляется в логе строкой «ОТОЗВАНО-ФРАЗА: «…»»")
        return 0, lines
    bad = []
    for target in targets:
        path = os.path.join(adir, target)
        if not existing(path):
            continue
        try:
            text = tc_read(path)
        except OSError:
            continue
        flow, lmap = retract_norm_map(text)
        for phrase, log_name in reestr:
            needle = retract_norm(phrase)
            if not needle:
                continue
            start = 0
            while True:
                i = flow.find(needle, start)
                if i < 0:
                    break
                start = i + 1
                window = flow[max(0, i - RETRACT_WINDOW):i]
                if RETRACT_MARK_RE.search(window):
                    continue
                bad.append((target, lmap[i] if i < len(lmap) else 0,
                            phrase, log_name))
    for target, ln, phrase, log_name in bad:
        lines.append(f"  🔴 {target}:{ln} держит ОТОЗВАННУЮ формулировку "
                     f"«{phrase[:90]}» (отозвана в {log_name}), и рядом нет "
                     f"пометки отзыва")
    if bad:
        lines.append("  Правка текста по улике закрывается только вместе с "
                     "правкой файла, ОТКУДА улика пришла: иначе снятое "
                     "утверждение возвращается следующим раундом. Либо снеси "
                     "формулировку, либо оставь её ЦИТАТОЙ под пометкой отзыва "
                     "(«🔴 ОТОЗВАНО: …»), как это сделано в логах.")
        return 1, lines
    lines.append(f"  · проверено файлов: "
                 f"{', '.join(t for t in targets if existing(os.path.join(adir, t)))}"
                 f" - живых отозванных формулировок нет")
    return 0, lines


def tocm_positions(text):
    """Позиции ЖИВЫХ блоков class="toc-mobile" в порядке документа.

    Приманки те же, что у cta-position: примеры разметки в комментариях шаблона,
    имена классов строками в инлайн-CSS и JS. Мёртвые диапазоны считает та же
    ctapos_dead_spans - закон один, копии не заводим.
    """
    return ctapos_positions(text, TOCM_RE)


def toc_mobile_run(adir, page_path=None):
    """(rc, строки). rc: 0 - мобильного оглавления на странице нет ·
    1 - блок найден (поимённо, с позициями и куском тега) · 2 - нет собранной
    страницы. Тихого PASS не бывает: молчаливый пропуск и есть зелёная ложь."""
    slug = os.path.basename(os.path.abspath(adir).rstrip("/"))
    page = page_path or os.path.join(adir, "index.html")
    lines = [f"toc-mobile [page] {slug}"]
    if not existing(page):
        lines.append(f"  ОШИБКА: нет собранной страницы {page}")
        return 2, lines
    page_text = tc_read(page)
    lines.append(" канон оглавления (волна р13, по решению автора): на странице "
                 f"РОВНО ОДНО оглавление - липкая колонка {TOCM_DESK}. "
                 f"Раскрывающийся {TOCM_BLOCK} и его пилюля «Содержание» удалены "
                 "с движка и со всех статей, замены взамен нет")
    поз = tocm_positions(page_text)
    десктоп = ctapos_positions(page_text, TOCM_DESK_RE)
    lines.append(f"  {TOCM_DESK} (липкая колонка, справочно): найдено {len(десктоп)}"
                 + (", позиции: " + ", ".join(str(x) for x in десктоп) if десктоп
                    else " - нет (законно для страниц без разделов, напр. /about/)"))
    lines.append(f"  class=\"toc-mobile\" (живых блоков в разметке): найдено {len(поз)}"
                 + (", позиции: " + ", ".join(str(x) for x in поз) if поз else ""))
    if not поз:
        lines.append("  OK. Мобильного оглавления-кнопки на странице нет.")
        return 0, lines
    lines.append(f"  Дефектов: {len(поз)}")
    for p in поз:
        кусок = page_text[p:p + 90].split("\n")[0]
        lines.append(f"  ! ВЕРНУЛСЯ {TOCM_BLOCK}: живой блок на позиции {p} - "
                     f"{кусок!r}. Владелец приказал по решению автора убрать его "
                     "полностью с движка и со всех статей; ставить оглавление "
                     "в тело страницы нельзя ни под каким тегом")
    return 1, lines


# ── описание гейтов ──────────────────────────────────────────────────────────
# rc_map: код возврата -> статус. Ключ None - «всё остальное».

# ── гейт svezhaya-tema (закон 25 ZAKONY-SEO.md, замер) ─────────
# Класс «свежая узкая тема» входит в производство не через гейт спроса, а через
# четыре ступени radar_to_queue.py, и подача у него другая. До этой редакции эти правила
# держала только инструкция, а закон, который держит одна инструкция,
# отваливается на третьей статье подряд. Здесь он становится кодом.
# 0 - PASS · 1 - FAIL (правило класса нарушено) · 2 - ERROR (нечем проверить)
RC_SVEZHAYA = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}
# Дату события ищем в первых стольких знаках тела: читатель пришёл из выдачи
# проверить, правда ли это, и подводка перед фактом убивает страницу
ST_ОКНО_ЗНАКОВ = 300
ST_ДАТА = re.compile(
    r"(\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}\s+(январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|"
    r"октябр|ноябр|декабр)[а-яё]*)", re.I)
# Свой слой поверх источника: раздел, которого у новости-донора нет
ST_СВОЙ_СЛОЙ = ("что это меняет", "что теперь делать", "что делать",
                "как проверить", "где ломается", "что это значит для",
                "как это касается", "проверил сам", "мой замер")

RC_STD = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}
RC_CADENCE = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "ERROR", None: "ERROR"}
RC_ADVISORY = {0: "PASS", 1: "WARN", None: "WARN"}
RC_ORIGINALITY = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "ERROR", None: "ERROR"}
# title-ctr: 1 - замечания при жёстком прогоне (новая статья), 2 - те же
# замечания при --revision (мягко, старый корпус не краснеет), 3 - нечего читать
RC_TITLE = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "ERROR", None: "ERROR"}
# cta: 3 - секция cta в config.md пуста целиком (у автора без именных инвайтов и
# без прошлых маршрутов проверять нечего). Это WARN, а не тихий PASS: гейт
# ГРОМКО говорит, что не проверил ничего, но корпус ученика не краснеет
RC_CTA = {0: "PASS", 1: "FAIL", 2: "ERROR", 3: "WARN", None: "ERROR"}
# frame-density: 2 - нет собранной страницы, 3 - проверить нечем (нет Pillow /
# кадр не читается). Оба ERROR, а не WARN: гейт про ПИКСЕЛЬ, и «инструмент не
# заработал» обязан ронять стадию, иначе брак уезжает под зелёной распиской.
# 4 (перекалибровка по решению автора) - брака нет, есть кадры пограничной зоны 25-40:
# аудит про неё пишет «глазами, решение человека», поэтому WARN - он виден в
# отчёте и в gates.json, но стадию не роняет
RC_FRAME = {0: "PASS", 1: "FAIL", 2: "ERROR", 3: "ERROR", 4: "WARN", None: "ERROR"}
# cta-position: 2 - нет собранной страницы. ERROR, а не WARN: main() уже
# отказывает стадии page без index.html ДО build_gates(), значит до этого кода
# доходят только поломкой окружения, и тихий зелёный тут был бы враньём
RC_CTAPOS = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}
# toc-mobile: 2 - нет собранной страницы. ERROR по той же причине, что у
# cta-position: main() отказывает стадии page без index.html ДО build_gates(),
# значит сюда доходят только поломкой окружения, и тихий зелёный был бы враньём
RC_TOCM = {0: "PASS", 1: "FAIL", 2: "ERROR", None: "ERROR"}
# image-refs: 1 - битая картинка (FAIL, не WARN: битый кадр на проде видит
# читатель из поиска, это брак, а не вкусовая оснастка). 2 - неизвестная
# раскладка на входе, 3 - нет собранной страницы; оба ERROR по той же причине,
# что у cta-position/toc-mobile: main() отказывает стадии page без index.html ДО
# build_gates(), значит сюда доходят только поломкой окружения
RC_IMGREF = {0: "PASS", 1: "FAIL", 2: "ERROR", 3: "ERROR", None: "ERROR"}
# novice: 2 - жёлтая зона хотя бы по одной оси (жаргон/сырые блоки/легаси-кадры
# при --revision). WARN, а не FAIL: пороги калиброваны так, что жёлтое - это
# верхняя четверть корпуса, где решение принимает человек, а красное - худшая
# десятая часть. 3 - читать нечего (нет файла/пусто) = ERROR: молчаливый
# зелёный на несуществующем входе и есть зелёная ложь
RC_NOVICE = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "ERROR", None: "ERROR"}
# own-evidence (правка r15, по решению автора): 2 - own=measure блоков нет НИ В ОДНОЙ
# форме (ни директива :::, ни сырая HTML data-own="measure"), но статья заявляет
# собственный замер (непустой terminal-outputs/, слова «мой замер»/«прогнал»/
# «проверил сам»). WARN, а не тихий PASS и не FAIL: гейту физически нечего
# сверять ровно там, где сверять и надо - это видно в отчёте и в gates.json,
# решение (пометить блок или снять заявку) принимает человек. До этой правки
# такой случай печатался как «гейт неприменим (N/A, PASS)» и уезжал в зелёный.
# 3 - файла нет = ERROR
RC_OWN_EVIDENCE = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "ERROR", None: "ERROR"}
# qa-freshness (круг 13, по решению автора): свежесть скрин-приёмки против index.html.
# Класс возвращался ТРИЖДЫ на одной волне (круги 5, 7, 12) - расписку «смотрел
# глазами» писали по кадрам ПРОШЛОЙ сборки, - и каждый раз проезжал бесплатно,
# потому что qa_freshness.py не звал ни один гейт: правило держалось только на
# дисциплине фиксера, и она не удержалась.
#   1 - кадры есть, но старше страницы -> FAIL: отгружается сборка, которой не
#       видел глазами ни один человек;
#   3 - расписка называет кадр, которого нет на диске -> FAIL, тот же класс
#       (улика названа, улики нет);
# 2 - приёмку не снимали вовсе -> WARN, не FAIL: калибровка по решению автора по 136
#       статьям lead-magnit-work даёт 113 таких, это легаси без приёмки, а не
#       свежий брак. Тихим PASS быть тоже не может - причина видна в gates.json.
RC_QAFRESH = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "FAIL", None: "ERROR"}
# --revision снимает жёсткость тем же приёмом, что у title-ctr/tool-article/
# novice: у переиздаваемой легаси-страницы протухшая приёмка - известная
# стоимость переиздания, а не брак этого прогона. Калибровка: жёстко корпус даёт
# 19 FAIL (кадры в qa-screenshots/ старше страницы) + 2 FAIL по расписке;
# под --revision те же статьи дают WARN и вердикт не роняют
RC_QAFRESH_SOFT = {0: "PASS", 1: "WARN", 2: "WARN", 3: "WARN", None: "ERROR"}
# frame-provenance (по решению автора): 4 - у кадров нет ЛЕГАЛЬНОЙ записи о съёмке в
# МЯГКОМ режиме (дефолт) - записи нет вовсе, класс вне списка, нет режима mode
# (р8-по решению автора: рукописная строка вместо записи shot.py) либо текст записи сам
# называет закрытый канал; это WARN - замечание видно в отчёте и в gates.json,
# стадию не роняет.
# 1 - те же кадры при замке --provenance-hard = FAIL, туда же (р5-по решению автора)
# class=result с адресом КОРНЯ сервиса: «скрин главной» вместо результата функции.
# «Адрес функции не назван» замком не ловится и остаётся WARN. 2 - нет собранной страницы:
# ERROR по той же причине, что у cta-position/toc-mobile (main() отказывает стадии
# page без index.html ДО build_gates, значит сюда доходят только поломкой окружения)
RC_PROV = {0: "PASS", 1: "FAIL", 2: "ERROR", 4: "WARN", None: "ERROR"}
# prod-vs-source: rc=3 - «страницы нет на проде». Это НЕ расхождение и НЕ авария
# инструмента, это отдельный факт, и мешать его с FAIL значит врать в расписке.
# Но и в PASS его сваливать нельзя: гейт стоит на стадии publish, то есть ПОСЛЕ
# заливки статьи, которая ЧИСЛИТСЯ ОПУБЛИКОВАННОЙ в реестре (иначе гейт вовсе
# SKIP) - 404 у такой страницы это боевая поломка, а не тишина.
RC_PRODSRC = {0: "PASS", 1: "FAIL", 2: "ERROR", 3: "FAIL", None: "ERROR"}


def build_gates(cfg, ctx):
    """[(stage, gate)] по всем стадиям. gate несёт cmd/условие/обязательность.

    cmd = None означает «гейт не запускается»: причина в поле skip.
    """
    slug, adir = ctx["slug"], ctx["dir"]
    # цель стадии draft: draft.md либо кандидат миграции, названный --draft
    draft = ctx.get("draft") or os.path.join(adir, "draft.md")
    page = os.path.join(adir, "index.html")
    py = sys.executable or "python3"

    t_structure = tool(cfg, "structure_check", "lm_tools", "structure-check.py")
    t_cadence = tool(cfg, "cadence_check", "lm_tools", "ai-cadence-check.py")
    t_orig = tool(cfg, "originality_check", "lm_tools", "originality-check.py")
    t_aloud = tool(cfg, "read_aloud_check", "lm_tools", "read-aloud-check.py")
    t_own_evidence = tool(cfg, "own_evidence_check", "lm_tools", "own-evidence-check.py")
    t_novice = tool(cfg, "novice_check", "lm_tools", "novice-check.py")
    # судья класса нулевой терпимости под флагом --skip-novice (наряд R-48)
    t_novice_zero = tool(cfg, "novice_zero", "template_dir", "novice_zero.py")
    t_strip = tool(cfg, "strip_notes", "template_dir", "strip_notes.py")
    t_artifacts = tool(cfg, "artifacts_gate")
    t_claim = tool(cfg, "claim_gate")
    t_door = tool(cfg, "door_gate")
    door_canon = tool(cfg, "door_canon")
    t_refl = tool(cfg, "reflections_gate", "seo_scripts", "reflections_gate.py")
    t_hub = tool(cfg, "hub_counts", "seo_scripts", "hub_counts.py")
    t_hubmem = tool(cfg, "hub_membership", "seo_scripts", "hub_membership.py")

    snapshot = cfg.get("corpus_snapshot")
    status = cfg.get("corpus_status")
    snapshot = os.path.expanduser(snapshot) if snapshot else None
    status = os.path.expanduser(status) if status else None

    # title-ctr гоняется этим же файлом отдельным процессом: чекера-соседа под
    # эту ось нет, а заводить второй способ «как гейт попадает в отчёт» - плодить
    # сущность. Так запись в gates.json несёт полную команду прогона, как у всех.
    self_py = os.path.abspath(__file__)
    lm_dir = cfg_path(cfg, "lm_tools", FALLBACK["lm_tools"])
    tc_yaml = cfg.get("skill_config")
    tc_yaml = (os.path.expanduser(tc_yaml.strip())
               if isinstance(tc_yaml, str) and tc_yaml.strip()
               else os.path.join(os.path.dirname(lm_dir.rstrip("/")),
                                 "seo-engine", "seo-config-reference.yaml"))
    # config.md скилла (закон CTA: карта инвайтов, префиксы, литералы). Ключ
    # lead_magnit_config, фолбэк - сосед каталога tools, тем же приёмом, что tc_yaml
    lm_config = cfg.get("lead_magnit_config")
    lm_config = (os.path.expanduser(lm_config.strip())
                 if isinstance(lm_config, str) and lm_config.strip()
                 else os.path.join(os.path.dirname(lm_dir.rstrip("/")), "config.md"))
    # 🔒 брендовый хвост - из ЛИЧНОГО конфига машины, не из раздаваемого скилла
    tc_tails = [x for x in ([cfg.get("author_name")]
                            + list(cfg.get("brand_tails") or []))
                if isinstance(x, str) and x.strip()]

    def tc_cmd(is_draft):
        c = [py, self_py, "--title-ctr", adir,
             "--tc-stage", "draft" if is_draft else "page",
             "--tc-yaml", tc_yaml, "--tc-tools", lm_dir]
        if is_draft:
            c += ["--tc-draft", draft]
        for t in tc_tails:
            c += ["--tc-brand-tail", t]
        # ровно тот же механизм, что у оси tool-article: жёсткость снимает
        # --revision, чтобы ревизия старой страницы не краснела всем корпусом
        if not ctx.get("revision"):
            c.append("--tc-hard")
        return c

    # novice (рв даты запуска.2026, стандарт владельца «понятно новичку»): жаргон/1k,
    # свалка код-блоков, терминальные скрины. Тем же приёмом, что tc_cmd: одна
    # сборка команды на обе стадии, меняется только цель.
    # 🔒 --doors подаётся УСЛОВНО: канон дверей - автор-дом, на машине ученика его
    # нет, и путь в самом novice-check.py не зашит (см. его load_product_whitelist).
    # Файла нет - гейт работает без белого списка, а не падает.
    def novice_cmd(target):
        c = [py, t_novice, target]
        if existing(door_canon):
            c += ["--doors", door_canon]
        # жёсткость снимает --revision (тот же приём, что у title-ctr и
        # tool-article): у легаси-страницы терминальный скрин - известная
        # стоимость переиздания, а не свежий брак новой статьи
        if ctx.get("revision"):
            c.append("--revision")
        return c

    # обход волной легаси-операций: --skip-novice. НЕ config_gap (окружение тут
    # ни при чём) - это признак КОНКРЕТНОГО прогона, как SEO_WAVE у claim-shared,
    # поэтому SKIP с поимённой причиной, видимой в gates.json
    # ДЫРА ОБХОДА ЗАКРЫТА (наряд R-48, волна peredelka-E по решению автора). Раньше эта
    # ветка гасила ВЕСЬ гейт: флаг снимал и пороговые оси (плотность жаргона,
    # сырые блоки, терминальные скрины - законная стоимость легаси), и КЛАСС
    # НУЛЕВОЙ ТЕРПИМОСТИ «тех-деталь для продвинутых», у которого порога нет
    # вовсе. То есть легаси-операция могла законно провезти на прод «код 403» и
    # «три узла» - ровно тот класс, который владелец велел закрыть
    # навсегда. Теперь флаг НЕ снимает гейт, а СУЖАЕТ его до novice_zero.py:
    # пороговые оси не судятся, ось 4 судится и роняет стадию. Причина сужения
    # видна в расписке gates.json строкой ниже, а не молча.
    novice_narrow = ("обход --skip-novice: пороговые оси легаси сняты, класс "
                     "нулевой терпимости (тех-деталь для продвинутых) судится "
                     "по-прежнему") if ctx.get("skip_novice") else None
    novice_skip = None

    def novice_zero_cmd(target):
        c = [py, t_novice_zero, target, "--tool", t_novice]
        if existing(door_canon):
            c += ["--doors", door_canon]
        return c

    g = []

    # config_gap - строка причины, ЕСЛИ у обязательного гейта нет cmd потому что
    # СТРУКТУРНО не настроено окружение (ключ конфига не прописан вовсе, канон/
    # слепок не на диске) - тогда run_gate() отдаёт не тихий SKIP, а громкий
    # ERROR (роняет вердикт стадии, дефект р7-по решению автора). Оставлять None там, где
    # причина - легитимное состояние ДАННЫХ/ПРОГОНА (нет соседей для сверки,
    # нет draft.md у spec.json-статьи, гейт не в волне) - это НЕ дефект окружения.
    def add(stage, name, what, cmd, required=True, rc_map=None, skip=None, tool_path=None,
            config_gap=None):
        g.append({"stage": stage, "name": name, "what": what, "cmd": cmd,
                  "required": required, "rc_map": rc_map or RC_STD,
                  "skip": skip, "tool": tool_path, "config_gap": config_gap})

    # ── стадия draft ─────────────────────────────────────────────────────────
    add("draft", "structure", "структура черновика: H2, чанки, first-sentence, оффер",
        [py, t_structure, draft], tool_path=t_structure)
    add("draft", "cadence", "плотность AI-маркеров на 1000 слов",
        [py, t_cadence, draft], rc_map=RC_CADENCE, tool_path=t_cadence)
    add("draft", "read-aloud", "читаемость вслух (advisory, вердикт не роняет)",
        [py, t_aloud, draft], required=False, rc_map=RC_ADVISORY, tool_path=t_aloud)
    # own-evidence (r8, по решению автора): каждый own=measure блок сверяется с
    # terminal-outputs/ - structure-check СЧИТАЕТ такие блоки, own-evidence
    # СВЕРЯЕТ их содержимое с уликами. Обязательный: калибровка по всем 30
    # статьям lead-magnit-work/ с own=measure (159 блоков) - 1,3% (2 блока/2
    # статьи) не подтверждено, оба проверены руками, настоящие дефекты (см.
    # докстринг own-evidence-check.py).
    # 🔴 r15 (по решению автора): гейт знает ОБЕ формы own-блока - директиву
    # (:::pre/:::figure own=measure) И сырую HTML (любой элемент с
    # data-own="measure", напр. <div class="vizblock" data-own="measure">).
    # До правки сырая форма была НЕВИДИМА, и статьи, где own-блоки только
    # сырые, печатали «блоков нет, N/A, PASS» - ложный зелёный, найденный
    # дважды скептиками волны r12 (9 блоков в 4 статьях проехали мимо).
    # rc=2 (WARN) - блоков нет ни в одной форме, но замер в статье заявлен.
    terminal_outputs = os.path.join(adir, "terminal-outputs")
    add("draft", "own-evidence",
        "own=measure блоки ОБЕИХ форм (:::pre/:::figure и сырой data-own) "
        "подтверждены логами terminal-outputs/",
        [py, t_own_evidence, draft, "--terminal-outputs", terminal_outputs],
        rc_map=RC_OWN_EVIDENCE, tool_path=t_own_evidence)
    # retract-sync (r14 круг 15, по решению автора): снятое утверждение обязано быть
    # снято и в файле-ИСТОЧНИКЕ, а не только в тексте статьи. Гейт живёт в этом
    # файле, зовётся отдельным процессом - тем же приёмом, что assets-exist.
    # Молчит, пока в логах нет ни одной строки «ОТОЗВАНО-ФРАЗА: «…»», поэтому
    # на статьях, где отзывов не объявляли, он ничего не меняет (калибровка по
    # lead-magnit-work по решению автора: 134 статьи, реестр есть у одной, красных 0).
    add("draft", "retract-sync",
        "отозванные формулировки не живут в файлах-источниках "
        "(draft.md, research.md, index.html)",
        [py, self_py, "--retract-sync", adir], tool_path=self_py)
    # svezhaya-tema (закон 25, по решению автора) - тем же приёмом, что retract-sync:
    # гейт живёт в этом файле и зовётся отдельным процессом, поэтому в
    # gates.json уезжает полная команда прогона. На статьях класса «голова
    # спроса» печатает «НЕ ПРИМЕНИМ» и стадию не роняет
    add("draft", "svezhaya-tema",
        "класс «свежая узкая тема»: дата события в первых 300 знаках, свой слой "
        "поверх источника, голова проходит признаки верхнего дециля",
        [py, self_py, "--svezhaya-tema", adir]
        + (["--st-draft", draft] if ctx.get("draft") else []),
        rc_map=RC_SVEZHAYA, tool_path=self_py)
    add("draft", "title-ctr",
        "формула сниппета: длина title, счётчик, H1, description, капсула"
        + ("" if ctx.get("revision") else ", жёстко"),
        tc_cmd(True), rc_map=RC_TITLE, tool_path=self_py)
    # title-god и vnutrennie-ssylki (волна 3 захода 2026-08-29-seo-x4-kanon):
    # два ХАРД-правила, пришедшие из побайтовой дельты 24 пар топ-3. Живут в
    # этом файле, зовутся отдельным процессом - тем же приёмом, что
    # svezhaya-tema и retract-sync
    add("draft", "title-god",
        "год в title у датируемой темы (версия, релиз, цена, доступ, рейтинг, "
        "актуальность); вечнозелёная тема гейтом не судится",
        [py, self_py, "--title-god", adir]
        + (["--tg-draft", draft] if ctx.get("draft") else []),
        rc_map=RC_TITLE_GOD, tool_path=self_py)
    # own-run-shagi (рв даты запуска.2026, дефект T2 круга 2): статья, ведущая читателя
    # по интерфейсу, обязана иметь кадр СВОЕГО экрана. Тем же приёмом, что
    # title-god - гейт живёт здесь и зовётся отдельным процессом
    add("draft", "own-run-shagi",
        "пошаговая инструкция по интерфейсу («куда нажать / что увидишь / мимо "
        "не пройдёшь») и заявление «проверил живьём» требуют в манифесте хотя бы "
        "один кадр класса own-run - свой экран",
        [py, self_py, "--own-run-shagi", adir]
        + (["--ors-draft", draft] if ctx.get("draft") else []),
        rc_map=RC_ORS, tool_path=self_py)
    add("draft", "vnutrennie-ssylki",
        "минимум %d внутренних ссылок в теле черновика (медиана топ-3 - 40)"
        % VN_МИНИМУМ,
        [py, self_py, "--vnutrennie-ssylki", adir, "--vs-stage", "draft"]
        + (["--vs-config", lm_config] if existing(lm_config) else [])
        + (["--vs-draft", draft] if ctx.get("draft") else []),
        rc_map=RC_VNUTR, tool_path=self_py)
    add("draft", "novice",
        "стандарт «понятно новичку» по черновику: жаргон на 1000 слов, свалка "
        "код-блоков без обвязки «вставь/нажми/увидишь», терминальные кадры"
        + (" | " + novice_narrow if novice_narrow else ""),
        (novice_zero_cmd(draft) + ["--stage", "draft"] if novice_narrow
         else novice_cmd(draft)),
        rc_map=RC_NOVICE, tool_path=(t_novice_zero if novice_narrow else t_novice),
        skip=novice_skip)
    corpus = ctx.get("originality_corpus")
    add("draft", "originality", "оригинальность против соседних черновиков кластера",
        ([py, t_orig, draft, corpus] if corpus else None),
        rc_map=RC_ORIGINALITY, tool_path=t_orig,
        skip=None if corpus else "в каталоге прогонов нет соседних draft.md для сверки")

    # ── стадия page ──────────────────────────────────────────────────────────
    # 🔴 ВИЗУАЛЬНАЯ ОСЬ НА РЕВИЗИИ - ЗАМЕЧАНИЕМ, А НЕ ОТКАЗОМ (по решению автора, круг 2,
    # запись R69). У самого инструмента для этого есть штатный `--visual-warn`:
    # «те же визуальные проверки, но warning-ами». Почему это понадобилось: круг 2
    # поднял пол контентных H2 с 8 до 12 (замер эталона, R71/R76) и рядом написал,
    # что пол судит НОВОЕ производство и задним числом корпус не роняет. На первой
    # же ревизии выяснилось, что это было неправдой: страницы с 10 разделами
    # (guide-neyroset-dlya-ucheby, guide-ceny-neyrosetey, guide-chatgpt-plus) не
    # пускались на прод с ОДНОЙ добавленной контекстной ссылкой. Заявление
    # приведено к действительности здесь, а не переписано в комментарии.
    if ctx.get("revision"):
        page_flags = ["--visual-warn", "--render-hard", "--toc-hard"]
    else:
        page_flags = ["--visual", "--own-blocks-hard", "--render-hard",
                      "--toc-hard", "--tool-article-hard"]
    add("page", "structure-visual",
        "собранная страница: визуал, own-blocks, рендер, оглавление"
        + ("" if ctx.get("revision") else ", tool-article"),
        [py, t_structure, page] + page_flags, tool_path=t_structure)
    add("page", "title-ctr",
        "формула сниппета собранной страницы: title, счётчик, H1, description, "
        "капсула, таблицы, раскрытый FAQ"
        + ("" if ctx.get("revision") else ", жёстко"),
        tc_cmd(False), rc_map=RC_TITLE, tool_path=self_py)
    add("page", "vnutrennie-ssylki",
        "минимум %d внутренних ссылок в теле собранной страницы (main/article "
        "без меню, шапки, подвала и сайдбара)" % VN_МИНИМУМ,
        [py, self_py, "--vnutrennie-ssylki", adir, "--vs-stage", "page"]
        + (["--vs-config", lm_config] if existing(lm_config) else [])
        + (["--revision"] if ctx.get("revision") else []),
        rc_map=RC_VNUTR, tool_path=self_py)
    add("page", "strip-notes", "служебных комментариев в собранной странице нет",
        [py, t_strip, "--check", page], tool_path=t_strip)
    # assets-exist (р9-по решению автора, дыра скептика волны р9) - тем же приёмом, что
    # title-ctr/cta: гейт живёт в этом файле, зовётся отдельным процессом.
    # SKIP не нужен - main() уже отказывает стадии page без index.html ДО
    # вызова build_gates() (см. main(), проверка "нет index.html в <adir>"),
    # так что к этому месту страница гарантированно на диске
    add("page", "assets-exist",
        "локальные ассеты страницы (img/source src+srcset, href preload-картинок) "
        "физически на диске",
        [py, self_py, "--assets-exist", adir], tool_path=self_py)
    # image-refs (инцидент по решению автора: владелец открыл свою статью из поиска и
    # увидел битый хиро) - тем же приёмом, что assets-exist: гейт живёт в этом
    # файле, зовётся отдельным процессом, поэтому в gates.json уезжает полная
    # команда прогона. ПАРА к assets-exist и ровно его слепая зона:
    # assets-exist спрашивает «файл на диске есть?» и по контракту пропускает
    # всё корневое, image-refs спрашивает «а по какому адресу эта ссылка попадёт
    # НА ПРОДЕ» - согласован ли комплект одного <picture> и резолвятся ли свои
    # корневые пути. Раскладка - свойство прогона, не статьи: приходит флагами
    # --page-layout/--assets-remote, дефолт auto (выводится из самой страницы).
    # SKIP не нужен: main() уже отказывает стадии page без index.html
    imgref_cmd = [py, self_py, "--image-refs", adir]
    if ctx.get("page_layout") and ctx["page_layout"] != "auto":
        imgref_cmd += ["--page-layout", ctx["page_layout"]]
    if ctx.get("assets_remote"):
        imgref_cmd += ["--assets-remote", ctx["assets_remote"]]
    add("page", "image-refs",
        "битая картинка: смешанная раскладка внутри одного <picture> (промах "
        "<source> НЕ откатывается на <img>), расщеплённая раскладка страницы, "
        "плоский путь оставленный относительным и несоответствие объявленной "
        "раскладке (факт файла - у assets-exist и предполёта заливки)"
        + (f" | раскладка прогона объявлена: {ctx['page_layout']}"
           if ctx.get("page_layout") and ctx["page_layout"] != "auto" else ""),
        imgref_cmd, rc_map=RC_IMGREF, tool_path=self_py)
    # frame-density (рв даты запуска.2026, разнос владельца по хиро guide-deepseek) -
    # тем же приёмом, что assets-exist: гейт живёт в этом файле, зовётся
    # отдельным процессом, поэтому в gates.json уезжает полная команда прогона.
    # assets-exist проверяет ФАКТ файла, этот - что ВНУТРИ файла: пустой блок
    # (block_pct >= 25) и текст-плашка (empty_pct >= 80 при block_pct < 20).
    # SKIP не нужен по той же причине: main() уже отказывает стадии page без
    # index.html, страница к этому месту гарантированно на диске
    add("page", "frame-density",
        "плотность кадров статьи: пустой блок, мёртвая полоса и текст-плашка "
        "вместо реального скрина (метрика emptiness-scan, пороги аудита r10, "
        "перекалибровка по решению автора: БРАК от 40, зона 25-40 - замечание глазами) "
        "плюс ПОЛ по числу собственных кадров <figure> у нового производства",
        [py, self_py, "--frame-density", adir,
         "--frame-yaml", tc_yaml, "--frame-tools", lm_dir],
        rc_map=RC_FRAME, tool_path=self_py)
    # frame-provenance (по решению автора, закон владельца об ультра-реализме) - тем же
    # приёмом, что frame-density: гейт живёт в этом файле и зовётся отдельным
    # процессом, поэтому в gates.json уезжает полная команда прогона. Пара к
    # frame-density: тот меряет, что ВНУТРИ кадра, этот - ОТКУДА кадр взялся.
    # МЯГКИЙ по умолчанию (WARN), замок - флагом --provenance-hard прогона:
    # манифеста съёмки нет ни у одной страницы живого корпуса, жёсткий с первого
    # дня остановил бы конвейер целиком (риск 4 плана, исполнитель 10:45).
    # SKIP не нужен: main() уже отказывает стадии page без index.html
    prov_cmd = [py, self_py, "--frame-provenance", adir]
    if ctx.get("provenance_hard"):
        prov_cmd.append("--provenance-hard")
    add("page", "frame-provenance",
        "происхождение кадров статьи: у каждого кадра (хиро, кадр тела, og) есть "
        "запись в shots-manifest.json классом result/step/own-run/inherited, с "
        "режимом съёмки mode, и ни в ИМЕНИ кадра, ни в тексте записи нет закрытого "
        "канала"
        + (", ЗАМОК (--provenance-hard: непокрытый кадр, запись без mode, "
           "закрытый канал в имени или в записи и class=result с адресом корня "
           "сервиса = FAIL)"
           if ctx.get("provenance_hard")
           else " (мягко: замечание, стадию не роняет)"),
        prov_cmd, rc_map=RC_PROV, tool_path=self_py)
    # infra-leak (р9-по решению автора, инцидент - IP деплой-релея утёк в 6 статей, ни
    # один гейт это не ловил) - тем же приёмом, что assets-exist/cta/title-ctr:
    # гейт живёт в этом файле, зовётся отдельным процессом. Список литералов -
    # ключ infra_secrets, канонный фолбэк - сосед этого файла (infra-secrets.txt,
    # автор-дом, не раздаётся). Файла нет = SKIP ГРОМКО (не тихий зелёный PASS):
    # так решено намеренно для ЭТОГО гейта - в отличие от door-titles/corpus,
    # где отсутствие канона окружения роняет вердикт ERROR'ом, тут промах
    # окружения не должен красить СТАДИЮ в FAIL на каждой машине без файла,
    # но обязан быть виден глазами в отчёте (out несёт точную причину)
    infra_secrets = tool(cfg, "infra_secrets")
    infra_secrets_ok = existing(infra_secrets)
    add("page", "infra-leak",
        "утечка служебной инфраструктуры автора (IP/хост/логин деплой-релея) в "
        "СОБРАННОЙ странице - список литералов infra-secrets.txt",
        ([py, self_py, "--infra-leak-gate", adir, "--infra-secrets", infra_secrets]
         if infra_secrets_ok else None),
        tool_path=self_py,
        skip=None if infra_secrets_ok
        else f"список запретных литералов не найден: {infra_secrets}")
    # cta - тем же приёмом, что title-ctr: гейт живёт в этом файле и зовётся
    # отдельным процессом, поэтому в gates.json уезжает полная команда прогона.
    # Закон (карта инвайтов, префиксы, запрещённые литералы) - из config.md
    # скилла: ключ lead_magnit_config, иначе config.md рядом с каталогом tools
    cta_ok = os.path.isfile(page) and existing(lm_config)
    add("page", "cta",
        "маршрут CTA: именной инвайт слага, запрещённые литералы, жаргон и фразы "
        "старого маршрута",
        ([py, self_py, "--cta-gate", adir, "--cta-config", lm_config] if cta_ok else None),
        rc_map=RC_CTA, tool_path=self_py,
        skip=None if cta_ok else ("нет index.html - страница ещё не собрана"
                                  if existing(lm_config) else "нет config.md скилла"),
        config_gap=None if existing(lm_config) else config_gap_reason(
            "cta", [(existing(lm_config),
                     f"ключ lead_magnit_config указывает не на файл ({lm_config})")]))
    # cta-position (рв даты запуска.2026, правка владельца) - тем же приёмом, что
    # assets-exist/frame-density: гейт живёт в этом файле и зовётся отдельным
    # процессом, поэтому в gates.json уезжает полная команда прогона. SKIP не
    # нужен: main() уже отказывает стадии page без index.html ДО build_gates(),
    # страница к этому месту гарантированно на диске. Обязательный: место
    # призыва - решение владельца по деньгам, а не вкусовая оснастка
    add("page", "cta-position",
        "место финального призыва в хвосте: памятка -> призыв -> частые вопросы "
        "(section#checklist < .cta-final < section#faq по байтам страницы)",
        [py, self_py, "--cta-position", adir], rc_map=RC_CTAPOS, tool_path=self_py)
    # toc-mobile (рв даты запуска.2026, оснастка выведена из канона целиком) - тем же
    # приёмом. ГЕЙТ-НЕГАТИВ: он не требует блока, он
    # требует его ОТСУТСТВИЯ. Обязательный: удалённая по канону оснастка,
    # вернувшаяся соседней волной или откатом из .bak, обязана ронять стадию,
    # а не уезжать в прод под зелёной распиской
    add("page", "toc-mobile",
        "мобильное оглавление-кнопка НЕ вернулось: живого class=\"toc-mobile\" "
        "в байтах страницы нет ни под каким тегом (оглавление одно - "
        "липкая колонка aside.toc-desktop)",
        [py, self_py, "--toc-mobile", adir], rc_map=RC_TOCM, tool_path=self_py)
    # novice на собранной странице: черновика у 2/3 корпуса нет вовсе (источник
    # истины - spec.json), поэтому замок стандарта обязан стоять и на байтах
    # страницы, иначе безисточниковая статья проходит мимо оси целиком.
    # SKIP не нужен: main() уже отказывает стадии page без index.html
    add("page", "novice",
        "стандарт «понятно новичку» по собранной странице: жаргон на 1000 слов "
        "видимого текста, сырые код-блоки, терминальные скрины и мокапы"
        + (" | " + novice_narrow if novice_narrow else ""),
        (novice_zero_cmd(page) + ["--stage", "page"] if novice_narrow
         else novice_cmd(page)),
        rc_map=RC_NOVICE, tool_path=(t_novice_zero if novice_narrow else t_novice),
        skip=novice_skip)
    # qa-freshness (круг 13, по решению автора) - ОСЬ ПРИЁМКИ, а не текста. Отвечает на
    # один вопрос: видел ли живой человек глазами ТУ сборку, которая уедет
    # читателю. Инструмент - qa_freshness.py, сосед этого файла (ключ
    # qa_freshness, фолбэк template_dir). SKIP не нужен: main() уже отказывает
    # стадии page без index.html ДО build_gates(). Обязательный: расписка о
    # приёмке - это заявление о проверке, а заявление без улики волна уже
    # ловила и на текстовых осях.
    t_qa_fresh = tool(cfg, "qa_freshness", "template_dir", "qa_freshness.py")
    add("page", "qa-freshness",
        "скрин-приёмка не старше собранной страницы, и каждый названный в "
        "отчёте кадр лежит на диске"
        + (" (advisory: --revision)" if ctx.get("revision") else ""),
        [py, t_qa_fresh, adir],
        rc_map=RC_QAFRESH_SOFT if ctx.get("revision") else RC_QAFRESH,
        required=not ctx.get("revision"), tool_path=t_qa_fresh)
    add("page", "cadence-body", "ритм по телу черновика (канон 04-handoff, Шаг 2)",
        ([py, t_cadence, draft] if os.path.isfile(draft) else None),
        rc_map=RC_CADENCE, tool_path=t_cadence,
        skip=None if os.path.isfile(draft) else "нет draft.md (источник статьи - spec.json)")
    # howto-text-match (круг 2, волна r21-20260829, найден контролёром поиска,
    # перемерен исполнителем по решению автора по живому слепку: 133 из 466 страниц
    # (29%) несут узел HowTo, и в 133 из 133 затронутых - расхождение текста
    # шага, 685 из 686 шагов). Причина: article_build.py кладёт front-matter
    # «steps» в JSON-LD БЕЗ обработки (докстринг файла, пункт 5), а писатель
    # годами вписывал туда СВОЙ пересказ шага вместо цитаты из тела. Google
    # требует дословное присутствие текста шага HowTo в видимом тексте
    # страницы и гасит ВСЮ структурированную разметку страницы за расхождение
    # хотя бы одного шага - включая безупречно собранный рядом FAQPage.
    # Инструмент - howto_text_match.py, сосед этого файла (ключ
    # howto_text_match, фолбэк template_dir). SKIP не нужен: если узла HowTo в
    # разметке нет (front-matter «steps» не заполнено), инструмент сам
    # печатает «проверять нечего» и отдаёт rc 0 - это то же зелёное состояние,
    # что и «HowTo собрался и весь совпал», разводить их гейту незачем.
    t_howto_text = tool(cfg, "howto_text_match", "template_dir", "howto_text_match.py")
    add("page", "howto-text-match",
        "текст КАЖДОГО непустого step.name и step.text узла HowTo дословно "
        "присутствует в видимом тексте собранной страницы (без тегов, с "
        "раскрытыми html-сущностями &nbsp;/&amp;/&quot;/&laquo;/&raquo;/"
        "&mdash;) - расхождение гасит ВСЮ структурированную разметку страницы "
        "в поиске, не только HowTo",
        [py, t_howto_text, adir], tool_path=t_howto_text)

    # ── стадия publish ───────────────────────────────────────────────────────
    # уровень --post, а не --min: стадия гонится ПОСЛЕ публикации, и здесь уже
    # обязаны быть следы, которых физически не могло быть до заливки (обе ноги
    # уведомления). В pre-deploy их держать нельзя - это дедлок (дефект Б3)
    add("publish", "artifacts-post",
        "минимум артефактов конвейера + следы, появляющиеся после публикации",
        [py, t_artifacts, adir, "--post"], tool_path=t_artifacts)

    # р7-по решению автора: канон дверей (t_door/door_canon) - ЧАСТЬ ОКРУЖЕНИЯ, одна и та же
    # для любой статьи; если он не настроен - это не про ДАННЫЕ этой статьи,
    # молчаливый SKIP тут врал бы точно как у reflections/hub-counts. А вот
    # отсутствие index.html - состояние ЭТОЙ статьи на ЭТОМ прогоне (страницу
    # ещё не собрали), легитимная причина, роняющая гейт незачем - остаётся SKIP.
    canon_ok = existing(t_door) and existing(door_canon)
    door_ok = canon_ok and os.path.isfile(page)
    add("publish", "door-titles", "байт-лок <title> кодословных дверей",
        ([py, t_door, "--canon", door_canon, page] if door_ok else None),
        tool_path=t_door,
        skip=None if door_ok else ("нет index.html - страница ещё не собрана"
                                    if canon_ok else "нет канона дверей/гейта"),
        config_gap=None if canon_ok else config_gap_reason(
            "door-titles", [
                (existing(t_door), f"ключ door_gate указывает не на файл ({t_door})"),
                (existing(door_canon), f"ключ door_canon указывает не на файл ({door_canon})")]))

    # prod-vs-source (по решению автора, класс «правка мимо источника») - ВТОРАЯ ПОЛОВИНА
    # закона К.4. Первую держит article_verify: «сборка из источника == ЛОКАЛЬНЫЙ
    # index.html», обе сравниваемые вещи лежат ДОМА. Про то, что реально отдаёт
    # читателю боевой сайт, ни один из 17 гейтов не знал ничего - и в эту дыру
    # уехали волны, которые правили ПРОД напрямую HTML-патчами
    # (_rebuild/f3b-work/<slug>/patch.json, _rebuild/r14/ctr-retayt/) и не
    # возвращали правку в draft.md/spec.json. Итог на момент этой редакции: у 35 страниц корпуса
    # прод несёт текст, которого в источнике нет вовсе (микрокопия под кнопкой
    # CTA, блоки волн, свежие title), и любая пересборка стирает это молча.
    # Обнаружилось РУКАМИ, при разборе, а не гейтом.
    # ПОЧЕМУ ИМЕННО ЗДЕСЬ: стадия publish гонится ПОСЛЕ заливки (см. блок выше) -
    # только тут вопрос «что реально отдаёт прод» вообще имеет ответ. Волна,
    # пропатчившая прод мимо источника, краснеет на СВОЁМ прогоне. Симметричный
    # барьер ДО заливки (не дать пересборке стереть живой текст) стоит на двери
    # stage_to_relay.sh, шаг 2.6 - тем же инструментом.
    # ОБЯЗАТЕЛЬНЫЙ: расхождение прод↔источник - это отложенная потеря текста, а
    # мягкая заметка такой класс уже пропускала. Обход - --skip-prod-source,
    # уходит в расписку как SKIP С ПРИЧИНОЙ, а не тихий PASS.
    t_psv = tool(cfg, "prod_source_verify", "template_dir", "prod_source_verify.py")
    psv_work = work_dir(cfg)
    psv_has_source = (existing(os.path.join(adir, "draft.md"))
                      or existing(os.path.join(adir, "spec.json")))
    psv_published, psv_why = (False, "реестр публикаций не прочитан")
    try:
        psv_published, psv_why = is_published(slug, cfg)
    except Exception as e:                                  # noqa: BLE001
        psv_why = f"реестр публикаций не прочитан: {type(e).__name__}: {e}"
    if ctx.get("skip_prod_source"):
        psv_skip = ("обход --skip-prod-source: сверка с продом на этом прогоне "
                    "не выполнялась")
    elif not psv_has_source:
        psv_skip = ("нет источника (ни draft.md, ни spec.json) - чистая легаси, "
                    "пересобирать нечем, стереть нечего")
    elif not psv_published:
        psv_skip = f"страница ещё не опубликована ({psv_why}) - прода нет, сверять нечего"
    else:
        psv_skip = None
    add("publish", "prod-vs-source",
        "видимый текст ЖИВОГО прода == сборка из источника (что есть на проде и "
        "нет в draft.md/spec.json - следующая пересборка сотрёт)",
        ([py, t_psv, slug, "--work", psv_work, "--via", "relay", "--show", "6"]
         if (psv_skip is None and existing(t_psv)) else None),
        rc_map=RC_PRODSRC, tool_path=t_psv,
        skip=psv_skip if psv_skip is not None else (
            None if existing(t_psv) else f"инструмент не найден: {t_psv}"),
        config_gap=None if (psv_skip is not None or existing(t_psv)) else config_gap_reason(
            "prod-vs-source", [(existing(t_psv),
                                f"ключ prod_source_verify указывает не на файл ({t_psv})")]))

    # claim-shared НЕ входит в класс config_gap (р7-по решению автора): SEO_WAVE - не
    # прописываемый ключ конфига, а признак КОНКРЕТНОГО прогона («я сейчас
    # часть оркестрованной волны параллельных агентов»). Ручной/диагностический
    # прогон одной статьи вне волны легитимно не в ней - SKIP тут не врёт про
    # ненастроенное окружение, а честно говорит «сейчас нечего защищать от гонки».
    wave = os.environ.get("SEO_WAVE", "").strip()
    shared = ctx.get("shared_files") or []
    claim_ok = existing(t_claim) and wave and shared
    add("publish", "claim-shared",
        "разделяемые файлы не заняты чужой волной (проверка, не захват)",
        ([py, t_claim, "check", shared[0], wave] if claim_ok else None),
        tool_path=t_claim,
        skip=None if claim_ok else "нет SEO_WAVE / claim_gate / списка разделяемых файлов")
    # остальные разделяемые файлы - тем же гейтом, отдельными строками отчёта
    if claim_ok:
        for extra in shared[1:]:
            add("publish", f"claim-shared:{os.path.basename(extra)}",
                f"захват {extra}", [py, t_claim, "check", extra, wave], tool_path=t_claim)

    # р7-по решению автора (отчёт _rebuild/r7/obshchesaytovoe-otchet.md, «что стоит поднять
    # в канон» п.1): corpus_snapshot/corpus_status - ключи ГЛОБАЛЬНОГО конфига,
    # у них нет фолбэка (в отличие от originality, где neighbour_corpus сам
    # находит свежий corpus-ГГГГ-ММ-ДД). Пока ключей нет в seo-publish.json,
    # эти два ОБЯЗАТЕЛЬНЫХ гейта не исполнятся НИ НА ОДНОЙ статье НИКОГДА -
    # ровно класс «ненастроенное окружение», не данные конкретного прогона.
    def corpus_gap(name, t):
        return config_gap_reason(name, [
            (existing(t), "инструмент не найден"),
            (bool(snapshot), "нет ключа corpus_snapshot в seo-publish.json"),
            (snapshot is None or os.path.isdir(snapshot),
             f"corpus_snapshot указывает не на каталог ({snapshot})"),
            (bool(status), "нет ключа corpus_status в seo-publish.json"),
            (status is None or existing(status),
             f"corpus_status указывает не на файл ({status})")])

    snap_ok = existing(t_refl) and snapshot and os.path.isdir(snapshot) and existing(status)
    add("publish", "reflections", "отражения страницы в карте сайта, ленте, llms.txt",
        ([py, t_refl, "--check", "--snapshot", snapshot, "--status", status]
         if snap_ok else None),
        tool_path=t_refl,
        skip=None if snap_ok else "нет слепка корпуса (corpus_snapshot/corpus_status)",
        config_gap=None if snap_ok else corpus_gap("reflections", t_refl))

    hub_ok = existing(t_hub) and snapshot and os.path.isdir(snapshot) and existing(status)
    add("publish", "hub-counts", "числа хабов и чипы главной сходятся с корпусом",
        ([py, t_hub, "--check", "--snapshot", snapshot, "--status", status]
         if hub_ok else None),
        tool_path=t_hub,
        skip=None if hub_ok else "нет слепка корпуса (corpus_snapshot/corpus_status)",
        config_gap=None if hub_ok else corpus_gap("hub-counts", t_hub))

    # по решению автора: hub_counts отвечает «сколько карточек и сходится ли число»,
    # и на вопрос «а есть ли эта статья в хабе вообще» не отвечает НИКАК -
    # число согласовано при любом составе. Так 42 живые статьи уехали мимо всех
    # восьми хабов: ни одной входящей ссылки из структуры, робот доходил до них
    # только из карты сайта. Гейт состава - отдельная ось и отдельный носитель.
    hubmem_ok = existing(t_hubmem) and snapshot and os.path.isdir(snapshot) and existing(status)
    add("publish", "hub-membership",
        "статья входит в тематический хаб /tema/* и в его ItemList",
        ([py, t_hubmem, "--page", slug, "--snapshot", snapshot, "--status", status]
         if hubmem_ok else None),
        tool_path=t_hubmem,
        skip=None if hubmem_ok else "нет слепка корпуса (corpus_snapshot/corpus_status)",
        config_gap=None if hubmem_ok else corpus_gap("hub-membership", t_hubmem))

    return g


# ── прогон ───────────────────────────────────────────────────────────────────

def tail(text):
    lines = [l for l in (text or "").splitlines() if l.strip()]
    out = "\n".join(lines[-TAIL_LINES:])
    return out[-TAIL_CHARS:]


def hard_lines(text, limit=6):
    """Жёсткие строки вывода - то, из-за чего гейт красный."""
    out = []
    for l in (text or "").splitlines():
        s = l.strip()
        if s.startswith(HARD_PREFIX) and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


# ── замер оригинальности: число и порог видны ВСЕГДА, включая PASS ──────────
#
# 🔴 ЗАЧЕМ (калибровка r8, по решению автора). Фикс соседей сменил СОСТАВ корпуса
# сравнения - и распределение косинуса поехало вверх, а понять по зелёному
# гейту, НАСКОЛЬКО он зелёный и каким порогом мерили, было нечем: строки вывода
# чекера печатались только при FAIL/WARN. Порог живёт в конфиге скилла
# (tools.originality.max_cosine), и разрешает его САМ originality-check - здесь
# число и порог только СНИМАЮТСЯ с его вывода. Второго места, где порог задан,
# заводить нельзя: это ровно тот дубль, из-за которого калибровку и пришлось
# делать вслепую.
ORIG_COSINE_RE = re.compile(
    r"(?m)^\s*cosine \(TF-IDF\)\s*:\s*([0-9.]+)\s*\(порог\s*≤\s*([0-9.]+)\)")
ORIG_NGRAM_RE = re.compile(
    r"(?m)^\s*ngram-(\d+) jaccard\s*:\s*([0-9.]+)\s*\(порог\s*≤\s*([0-9.]+)\)")
ORIG_CLOSEST_RE = re.compile(r"(?m)^\s*ближайший эталон\s*:\s*(.+?)\s*\(из\s")


def originality_measure(out):
    """Числа и пороги гейта оригинальности из вывода originality-check.py.

    Снимается с ПОЛНОГО вывода до усечения tail(): иначе на длинном выводе
    строка с числом теряется и замер молча пропадает.
    """
    m = {}
    c = ORIG_COSINE_RE.search(out or "")
    if c:
        m["cosine"], m["max_cosine"] = float(c.group(1)), float(c.group(2))
    n = ORIG_NGRAM_RE.search(out or "")
    if n:
        m["ngram_n"] = int(n.group(1))
        m["ngram"], m["max_ngram"] = float(n.group(2)), float(n.group(3))
    f = ORIG_CLOSEST_RE.search(out or "")
    if f:
        m["closest"] = f.group(1).strip()
    return m or None


def measure_lines(rec):
    """Строка «замер: число (порог)» - в печать гейта и рядом с ней в gates.json.

    Печатается при ЛЮБОМ статусе. Нога, из-за которой гейт красный, называется
    явно: у гейта их две (косинус темы и дословные n-граммы), и без пометки
    непонятно, какую именно чинить.
    """
    m = rec.get("measure")
    if not isinstance(m, dict) or "cosine" not in m:
        return []
    части = []
    провал = []
    мк = m.get("max_cosine")
    части.append(f"cosine {m['cosine']} (порог ≤{мк})")
    if мк is not None and m["cosine"] > мк:
        провал.append("косинус темы")
    if "ngram" in m:
        мн = m.get("max_ngram")
        части.append(f"ngram-{m.get('ngram_n', '?')} {m['ngram']} (порог ≤{мн})")
        if мн is not None and m["ngram"] > мн:
            провал.append("дословные n-граммы")
    строка = "замер оригинальности: " + " · ".join(части)
    if m.get("closest"):
        строка += f" · ближайший {m['closest']}"
    out = [строка]
    if провал:
        out.append(f"  ↳ порог пробит: {', '.join(провал)}")
    return out


def run_gate(gate):
    """Запустить один гейт. Возврат - запись для gates.json."""
    rec = {"name": gate["name"], "what": gate["what"], "required": gate["required"],
           "cmd": None, "rc": None, "status": None, "out": ""}
    if gate["cmd"] is None:
        # дефект р7-по решению автора: обязательный гейт без cmd молча уходил в SKIP, даже
        # когда причина - НЕ данные статьи, а окружение, которое никто не
        # настроил (ключ конфига не прописан, канон/слепок не на диске). Такой
        # гейт физически не может исполниться сейчас и никогда не исполнится
        # без правки конфига - зелёный вердикт стадии при этом врал. Громкий
        # ERROR с именем недостающего ключа роняет вердикт (verdict_of уже
        # считает ERROR = FAIL для обязательных гейтов) и виден глазами в счётчике.
        if gate.get("config_gap"):
            rec["status"] = "ERROR"
            rec["out"] = f"гейт не настроен: {gate['config_gap']}"
            return rec
        rec["status"] = "SKIP"
        rec["out"] = gate["skip"] or "гейт неприменим"
        return rec
    if gate.get("tool") and not existing(gate["tool"]):
        rec["status"] = "ERROR"
        rec["cmd"] = " ".join(gate["cmd"])
        rec["out"] = f"инструмент не найден: {gate['tool']}"
        return rec
    rec["cmd"] = " ".join(gate["cmd"])
    started = datetime.datetime.now()
    try:
        p = subprocess.run(gate["cmd"], capture_output=True, text=True, timeout=TIMEOUT)
        rc = p.returncode
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    except subprocess.TimeoutExpired:
        rec["status"] = "ERROR"
        rec["out"] = f"таймаут {TIMEOUT}с"
        return rec
    except OSError as e:
        rec["status"] = "ERROR"
        rec["out"] = f"не запустился: {e}"
        return rec
    rec["rc"] = rc
    rec["status"] = gate["rc_map"].get(rc, gate["rc_map"].get(None, "ERROR"))
    # замер снимается с ПОЛНОГО вывода, до усечения tail()
    if gate["name"] == "originality":
        m = originality_measure(out)
        if m:
            rec["measure"] = m
    rec["out"] = tail(out)
    rec["flags"] = hard_lines(out)
    rec["seconds"] = round((datetime.datetime.now() - started).total_seconds(), 2)
    return rec


def verdict_of(records):
    bad = [r for r in records if r["required"] and r["status"] in ("FAIL", "ERROR")]
    return "FAIL" if bad else "PASS"


# ── отпечаток НАБОРА гейтов: расписка обязана говорить, ЧТО именно прогоняли ──
#
# 🔴 ЗАЧЕМ (план 2026-08-22, ключевое решение). Расписка стадии подписывала БАЙТЫ
# страницы (Б16) и молчала о том, КАКИМИ гейтами эти байты проверяли. Дыра видна
# на этой же волне: в стадию page добавляется новый гейт, а 47 слагов очереди
# лежат с готовым зелёным page=PASS от прошлого набора - они уехали бы в прод
# мимо нового гейта, и ни одна дверь этого не заметила бы. Теперь запись стадии
# несёт `gate_set` - сортированный список имён гейтов, которые в ней РЕАЛЬНО
# прогонялись; читатель расписки (ftp_publish) сверяет его с эталоном стадии и
# при расхождении требует перегона.
#
# ЭТАЛОН НАБОРА - ЕДИНСТВЕННЫЙ ИСТОЧНИК. Второго списка имён нигде нет: эталон
# спрашивается у того же build_gates(), что и гоняет гейты (режим --gate-set),
# поэтому набор физически не может разойтись с кодом.
def gate_set_of(records):
    """Отпечаток прогона: сортированный список имён гейтов, которые в нём были."""
    return sorted({r["name"] for r in records})


def stage_gate_set(cfg, stage, ctx=None):
    """Эталонный набор имён гейтов стадии - из build_gates(), без второго списка.

    Имена гейтов стадий draft и page от КОНКРЕТНОЙ статьи не зависят (условия
    решают только cmd/skip, но не состав), поэтому эталон считается на нейтральном
    ctx. У стадии publish есть динамические имена claim-shared:<файл> - они зависят
    от списка разделяемых файлов ЭТОГО прогона и эталоном набора быть не могут,
    поэтому из эталона выбрасываются.
    """
    ctx = ctx or {"slug": "-", "shared_files": [],
                  "dir": os.path.join(tempfile.gettempdir(), "article_gates-gate-set")}
    names = [g["name"] for g in build_gates(cfg, ctx) if g["stage"] == stage]
    return sorted({n for n in names if not n.startswith("claim-shared:")})


def counts_of(records):
    c = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0, "ERROR": 0}
    for r in records:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return c


def publish_ready(doc):
    """(вердикт, блокеры). PASS - если все три стадии зелёные в СВОИХ последних прогонах.

    Неприменимая стадия (applicable: false) не блокирует: её прогон - диагностика.
    Стадия, которую не гнали вовсе, блокирует - «не прогоняли» это не «прошло».
    """
    blockers = []
    for st in STAGES:
        rec = (doc.get("stages") or {}).get(st)
        if not isinstance(rec, dict):
            blockers.append(f"{st}: стадия не прогонялась")
            continue
        if rec.get("applicable") is False:
            continue
        if rec.get("verdict") != "PASS":
            blockers.append(f"{st}: последний прогон {rec.get('verdict')} "
                            f"от {rec.get('ran_at')}")
    return ("PASS" if not blockers else "FAIL"), blockers


def build_doc(doc, slug, stage, records, extra):
    """Свежая шапка отчёта поверх накопленных стадий (без записи на диск)."""
    doc = doc if isinstance(doc, dict) else {}
    doc["slug"] = slug
    if not isinstance(doc.get("stages"), dict):
        doc["stages"] = {}
    doc["stages"][stage] = {
        "ran_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "wave": os.environ.get("SEO_WAVE") or None,
        "agent": os.environ.get("SEO_AGENT") or None,
        "verdict": verdict_of(records),
        "counts": counts_of(records),
        "gates": records,
        **extra,
    }
    doc["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # последний вердикт КАЖДОЙ стадии отдельно. Прежний одиночный `verdict_last`
    # держал вердикт последнего по времени прогона любой стадии - диагностический
    # прогон draft затирал в шапке живой PASS стадии page (дефект В7)
    doc["verdicts"] = {
        st: {"verdict": rec.get("verdict"), "ran_at": rec.get("ran_at"),
             "applicable": rec.get("applicable", True),
             "counts": rec.get("counts")}
        for st, rec in doc["stages"].items() if isinstance(rec, dict)}
    v, blockers = publish_ready(doc)
    doc["verdict_publish_ready"] = {
        "verdict": v, "stages_required": list(STAGES), "blockers": blockers}
    doc.pop("verdict_last", None)  # ключ снят: врал про состояние статьи
    return doc


def write_report(path, slug, stage, records, extra):
    """gates.json НАКАПЛИВАЕТ стадии: прогон page не стирает результат draft."""
    old = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("stages"), dict):
                old = loaded
        except (ValueError, OSError):
            old = {}
    doc = build_doc(old, slug, stage, records, extra)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return doc


# ── корпус для originality: соседи ПО СМЫСЛУ, а не по времени файла ──────────
#
# 🔴 ЗАЧЕМ (разбор волны r7, улика - plans/2026-08-14-seo-10-statey-r7.md, раздел
# «САМОЕ ТЯЖЁЛОЕ»). Прежняя neighbour_corpus брала ТРИ САМЫХ СВЕЖИХ по mtime
# черновика каталога прогонов. Это соседи по ВРЕМЕНИ, а не по СМЫСЛУ: статья
# «ии написать статью» дословно повторила два предложения живой страницы
# /guide-neyroset-napisat-tekst/ и перенесла 6 из 13 H2 к соседям, а гейт в это
# время сравнивал её со случайными по времени файлами и молчал.
#
# ЧТО ИЗМЕНИЛОСЬ. Кандидатов теперь два источника: (1) ВСЕ черновики каталога
# прогонов, а не три свежих, (2) страницы слепка живого корпуса (corpus_snapshot
# из конфига, иначе самый свежий corpus-ГГГГ-ММ-ДД рядом с каталогом прогонов).
# Из этого пула отбираются top-N ближайших ПО ТЕМЕ: title / H1 / description /
# keywords / H2 сводятся в «профиль темы», профили сравниваются косинусом по
# TF-IDF с грубой русской нормализацией окончаний.
#
# ЧЕГО НЕ ТРОГАЛИ. Пороги гейта (max_cosine 0.60 / max_ngram 0.30) остались как
# были: originality-check как брал МАКСИМУМ по корпусу, так и берёт. Изменился
# только СОСТАВ корпуса - и он стал ближе к правде, то есть гейт стал строже, а
# не удобнее.
#
# ФОЛБЭК. Если смыслового сигнала нет вовсе (все кандидаты ниже порога похожести
# - например, первая статья в пустом каталоге прогонов), отбор честно
# откатывается на ПРЕЖНЕЕ поведение (top-N по mtime) и помечает это в выводе
# гейта и в gates.json: selected_by = "mtime-fallback". Молчаливого пропуска нет.

PROFILE_CAP = 200_000            # знаков файла на профиль темы (хвост не нужен)
MIN_TOPIC_SCORE = 0.08           # ниже - «смыслового сигнала не нашлось»
NEIGHBOURS_DEFAULT = 5           # прежний дефолт был 3; больше файлов = строже
CORPUS_ROOT_FALLBACK = "~/.business/growth/seo"
CORPUS_DIR_RE = re.compile(r"^corpus-\d{4}-\d{2}-\d{2}$")
TOPIC_TOKEN = re.compile(r"[a-zа-яё0-9]{3,}")
# служебные слова: несут нуль темы, но встречаются у всех и размывают косинус
TOPIC_STOP = frozenset("""
для что как так все еще уже или его ему них она они это этот эта эти том тем
там где когда чтобы если бы же ли не ни на по из от до за над под при про без
без через между перед после вместо кроме около раз два три шаг шаги шагов
гайд статья инструкция руководство пример примеры август сентябрь июль
""".split())
# грубая нормализация окончаний: лемматизатора в проекте нет и тянуть его сюда
# незачем - для РАНЖИРОВАНИЯ соседей хватает отсечения хвоста словоформы.
# Вердикт по этим числам никто не выносит, вердикт выносит originality-check.
TOPIC_SUFFIXES = ("иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими", "ей",
                  "ов", "ев", "ий", "ый", "ая", "ое", "ые", "ых", "ой", "ам",
                  "ям", "ах", "ях", "ом", "ем", "ть", "ся", "и", "ы", "а", "я",
                  "о", "е", "у", "ю", "ь")


def topic_stem(tok):
    """Отсечь хвост словоформы, стем короче 4 знаков не строим (шум)."""
    for suf in TOPIC_SUFFIXES:
        if len(tok) - len(suf) >= 4 and tok.endswith(suf):
            return tok[:-len(suf)]
    return tok


def topic_tokens(text):
    out = []
    for t in TOPIC_TOKEN.findall((text or "").lower()):
        if t in TOPIC_STOP or t.isdigit():
            continue
        out.append(topic_stem(t))
    return out


def read_head(path, cap=PROFILE_CAP):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(cap)
    except OSError:
        return ""


def html_body_text(text):
    """Тело статьи из собранной страницы: без скриптов, стилей, шапки и подвала.

    Обвязка страницы (навигация, футер, JSON-LD) одинакова у ВСЕХ наших страниц
    и к теме отношения не имеет - в профиль и в корпус сравнения она не едет.
    """
    t = re.sub(r"(?is)<script.*?</script>", " ", text or "")
    t = re.sub(r"(?is)<style.*?</style>", " ", t)
    t = re.sub(r"(?is)<svg.*?</svg>", " ", t)
    m = re.search(r"(?is)<main[^>]*>(.*?)</main>", t)
    if m:
        t = m.group(1)
    t = re.sub(r"(?is)<(nav|header|footer|form)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def profile_of_markdown(text):
    """Профиль темы черновика: поля шапки + все заголовки тела."""
    parts = []
    fm = re.match(r"^---\n(.*?)\n---\n", text or "", re.S)
    body = text or ""
    if fm:
        head = fm.group(1)
        body = text[fm.end():]
        for key in ("title", "h1", "description", "keywords", "codeword"):
            for m in re.finditer(r"(?m)^%s:\s*(.+)$" % key, head):
                parts.append(m.group(1).strip().strip('"\'[]'))
        for m in re.finditer(r"(?m)^\s*-\s+(?:name|text):\s*(.+)$", head):
            parts.append(m.group(1).strip().strip('"\''))
        for m in re.finditer(r"\{name:\s*\"([^\"]+)\"", head):
            parts.append(m.group(1))
    for m in re.finditer(r"(?m)^#{1,3}\s+(.+)$", body):
        parts.append(m.group(1).strip())
    return " \n".join(p for p in parts if p)


def profile_of_html(text):
    parts = []
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", text or "")
    if m:
        parts.append(re.sub(r"<[^>]+>", " ", m.group(1)))
    m = re.search(r'(?is)<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                  text or "")
    if m:
        parts.append(m.group(1))
    for tag in ("h1", "h2", "h3"):
        for m in re.finditer(r"(?is)<%s[^>]*>(.*?)</%s>" % (tag, tag), text or ""):
            parts.append(re.sub(r"<[^>]+>", " ", m.group(1)))
    return " \n".join(html.unescape(re.sub(r"\s+", " ", p)).strip()
                      for p in parts if p and p.strip())


def topic_profile(path):
    """«О чём этот текст» одной строкой. Пусто - профиль снять не удалось."""
    raw = read_head(path)
    if not raw:
        return ""
    if path.lower().endswith((".html", ".htm")):
        return profile_of_html(raw)
    return profile_of_markdown(raw)


def topic_cosine_ranker(profiles):
    """Замыкание score(profile_tokens) -> косинус по TF-IDF над пулом кандидатов.

    IDF считается по ПУЛУ: слова, которые есть у всех статей корпуса («claude»,
    «нейросеть»), сами теряют вес - руками их в стоп-лист вносить не надо.
    """
    docs = [collections.Counter(p) for p in profiles]
    df = collections.Counter()
    for d in docs:
        for term in d:
            df[term] += 1
    total = len(docs) or 1
    idf = {t: math.log((1 + total) / (1 + df[t])) + 1.0 for t in df}

    def vec(toks):
        c = collections.Counter(toks)
        return {t: c[t] * idf.get(t, math.log(1 + total) + 1.0) for t in c}

    def cos(a, b):
        if not a or not b:
            return 0.0
        dot = sum(v * b.get(t, 0.0) for t, v in a.items())
        na = sum(v * v for v in a.values()) ** 0.5
        nb = sum(v * v for v in b.values()) ** 0.5
        return (dot / (na * nb)) if na and nb else 0.0

    return vec, cos


def corpus_snapshot_dir(cfg, work=None):
    """Слепок живого корпуса: ключ конфига → самый свежий corpus-ГГГГ-ММ-ДД.

    Отдельная функция, а НЕ переиспользование `snapshot` из build_gates: там
    ключ управляет гейтами reflections/hub-counts, и их поведение (SKIP без
    слепка) менять нельзя. Здесь слепок - лишь источник кандидатов в соседи.
    """
    v = (cfg or {}).get("corpus_snapshot")
    if isinstance(v, str) and v.strip():
        p = os.path.expanduser(v.strip())
        return p if os.path.isdir(p) else None
    roots = []
    if work:
        roots.append(os.path.dirname(os.path.abspath(work.rstrip("/"))))
    roots.append(os.path.expanduser(CORPUS_ROOT_FALLBACK))
    for root in roots:
        if not os.path.isdir(root):
            continue
        names = sorted(n for n in os.listdir(root) if CORPUS_DIR_RE.match(n))
        if names:
            return os.path.join(root, names[-1])
    return None


def headline_of(path):
    """Заголовок текста: h1/title черновика или <h1>/<title> собранной страницы."""
    raw = read_head(path, 20_000)
    if not raw:
        return ""
    if path.lower().endswith((".html", ".htm")):
        m = (re.search(r"(?is)<h1[^>]*>(.*?)</h1>", raw)
             or re.search(r"(?is)<title[^>]*>(.*?)</title>", raw))
        val = m.group(1) if m else ""
        val = html.unescape(re.sub(r"<[^>]+>", " ", val))
    else:
        m = (re.search(r'(?m)^h1:\s*(.+?)\s*$', raw)
             or re.search(r'(?m)^title:\s*(.+?)\s*$', raw)
             or re.search(r'(?m)^#\s+(.+?)\s*$', raw))
        val = m.group(1) if m else ""
    return re.sub(r"\s+", " ", val).strip().strip('"\'')


def headline_words(text):
    return {w for w in re.split(r"[^0-9a-zа-яё]+", (text or "").lower()) if len(w) > 1}


def same_article_headline(a, b, порог=0.7):
    """Один и тот же заголовок с точностью до ретайтла (Jaccard по словам)."""
    wa, wb = headline_words(a), headline_words(b)
    if not wa or not wb:
        return 0.0
    j = len(wa & wb) / len(wa | wb)
    return j if j >= порог else 0.0


def article_identities(work, slug, cfg=None, draft_path=None):
    """Все имена, под которыми эта же статья может лежать в живом корпусе.

    🔴 ЗАЧЕМ. Имя каталога прогонов и slug опубликованной страницы совпадают
    ДАЛЕКО не всегда: `article-case-skilly-system` вышел как
    `/guide-unikalizaciya-viralnyh-karuselej/`, `glm-5-2-claude-code` - как
    `/guide-glm/`. Без этой сверки статья сравнивалась бы С СОБОЙ ЖЕ
    (замер: косинус 0.92-0.98) и краснела бы вечно.
    """
    prefix = (cfg or {}).get("page_prefix") or ""
    ids = {slug, prefix + slug}
    if prefix and slug.startswith(prefix):
        ids.add(slug[len(prefix):])
    кандидаты = [draft_path or os.path.join(work, slug, "draft.md")]
    spec = os.path.join(work, slug, "spec.json")
    if os.path.isfile(spec):
        try:
            with open(spec, encoding="utf-8") as f:
                d = json.load(f)
            for key in ("slug", "url", "canonical", "page_url"):
                v = d.get(key)
                if isinstance(v, str) and v.strip():
                    ids.add(v.strip("/ ").split("/")[-1].replace(".html", ""))
        except (ValueError, OSError):
            pass
    for p in кандидаты:
        if not os.path.isfile(p):
            continue
        m = re.search(r'(?m)^slug:\s*"?([^"\n]+)"?\s*$', read_head(p, 4000))
        if m:
            s = m.group(1).strip()
            ids.update({s, prefix + s})
            if prefix and s.startswith(prefix):
                ids.add(s[len(prefix):])
    return {i for i in ids if i}


def _normalize_page_slug_for_selfcheck(page_slug):
    """page_slug живой страницы → голый последний сегмент пути (для сравнения с ids).

    🔴 ФИКС (пилот guide-besplatnye-zameny, по решению автора). Живой корпус
    (`corpus_snapshot` из seo-publish.json) хранит страницы файлами вида
    `https%3A%2F%2Fdomain%2F<slug>%2F.html`; после отсечения ".html" в
    `neighbour_candidates()` page_slug остаётся URL-кодированным полным
    адресом и НИКОГДА не совпадает с голым slug из `article_identities()`
    - самоисключение молчало, черновик сравнивался САМ С СОБОЙ (замер:
    косинус 0.68 при ngram-5 0.05). Только для этого сравнения: unquote →
    взять последний непустой сегмент пути. Отбор соседей и label (что
    видно в отчёте) не меняются - если page_slug и так был голым именем
    каталога, unquote+split возвращает его без изменений (no-op).
    """
    decoded = urllib.parse.unquote(page_slug or "")
    сегменты = [s for s in decoded.split("/") if s]
    return сегменты[-1] if сегменты else decoded


def neighbour_candidates(work, slug, cfg=None, draft_path=None):
    """([(label, path, mtime, source)], [исключённые как своя же страница])."""
    out, свои = [], []
    if os.path.isdir(work):
        for name in sorted(os.listdir(work)):
            if name == slug or name.startswith("_") or name.startswith("."):
                continue
            p = os.path.join(work, name, "draft.md")
            if os.path.isfile(p):
                out.append((f"wave-{name}", p, os.path.getmtime(p), "черновик волны"))
    snap = corpus_snapshot_dir(cfg, work)
    if snap:
        ids = article_identities(work, slug, cfg, draft_path)
        свой_h1 = headline_of(draft_path or os.path.join(work, slug, "draft.md"))
        for name in sorted(os.listdir(snap)):
            if name.startswith("_") or name.startswith("."):
                continue
            full = os.path.join(snap, name)
            page, page_slug = None, None
            if os.path.isdir(full) and os.path.isfile(os.path.join(full, "index.html")):
                page, page_slug = os.path.join(full, "index.html"), name
            elif name.lower().endswith(".html"):
                page, page_slug = full, name[:-5]
            if not page:
                continue
            # своя же живая страница в корпус сравнения не едет: это дало бы
            # косинус около 1.0 и вечный FAIL (та же причина, по которой из
            # корпуса исключается собственный draft.md). Сверка двойная -
            # по slug И по заголовку, потому что имя каталога прогонов и slug
            # опубликованной страницы совпадают не всегда, а заголовок при
            # публикации мог быть переписан ретайтлом (потому Jaccard, не ==)
            if _normalize_page_slug_for_selfcheck(page_slug) in ids:
                свои.append(f"live-{page_slug} (slug статьи)")
                continue
            похоже = same_article_headline(свой_h1, headline_of(page))
            if похоже:
                свои.append(f"live-{page_slug} (заголовок совпал на {похоже:.2f})")
                continue
            out.append((f"live-{page_slug}", page, os.path.getmtime(page),
                        "живая страница корпуса"))
    return out, свои


def neighbour_corpus(work, slug, limit=NEIGHBOURS_DEFAULT, cfg=None, draft_path=None):
    """(каталог-времянка с соседями | None, справка об отборе).

    Свой draft.md в корпус попасть НЕ должен: originality-check рекурсивно
    забирает всю папку, и собственный текст дал бы косинус 1.0 и вечный FAIL.
    """
    limit = max(1, int(limit or NEIGHBOURS_DEFAULT))
    draft_path = draft_path or os.path.join(work, slug, "draft.md")
    meta = {"selected_by": "none", "limit": limit, "picks": [],
            "candidates": {"черновики волны": 0, "живые страницы": 0},
            "corpus_snapshot": corpus_snapshot_dir(cfg, work),
            "excluded_self": [], "note": ""}
    cands, свои = neighbour_candidates(work, slug, cfg, draft_path)
    meta["excluded_self"] = свои
    meta["candidates"]["черновики волны"] = sum(1 for c in cands if c[3].startswith("черновик"))
    meta["candidates"]["живые страницы"] = sum(1 for c in cands if c[3].startswith("живая"))
    if not cands:
        meta["note"] = "кандидатов в соседи нет: пуст каталог прогонов и слепок корпуса"
        return None, meta

    draft_prof = topic_tokens(topic_profile(draft_path)) if os.path.isfile(draft_path) else []
    profs = [topic_tokens(topic_profile(p)) for _, p, _, _ in cands]
    scores = [0.0] * len(cands)
    if draft_prof and any(profs):
        vec, cos = topic_cosine_ranker(profs + [draft_prof])
        dv = vec(draft_prof)
        scores = [cos(dv, vec(p)) if p else 0.0 for p in profs]

    rows = [{"label": c[0], "path": c[1], "mtime": c[2], "source": c[3],
             "score": round(scores[i], 4)} for i, c in enumerate(cands)]
    by_topic = sorted(rows, key=lambda r: (-r["score"], -r["mtime"], r["label"]))
    if not draft_prof:
        meta["selected_by"] = "mtime-fallback"
        meta["note"] = (f"профиль темы черновика не снялся ({os.path.basename(draft_path)}: "
                        f"нет шапки/заголовков) - отбор откатился на прежнее поведение, "
                        f"{limit} самых свежих по времени файла")
    elif by_topic[0]["score"] < MIN_TOPIC_SCORE:
        meta["selected_by"] = "mtime-fallback"
        meta["note"] = (f"смысловых соседей не нашлось (лучший косинус тем "
                        f"{by_topic[0]['score']} < порога {MIN_TOPIC_SCORE}) - отбор "
                        f"откатился на прежнее поведение, {limit} самых свежих по "
                        f"времени файла")
    else:
        meta["selected_by"] = "topic"
        meta["note"] = (f"top-{limit} по близости темы (title/H1/description/keywords/H2, "
                        f"косинус TF-IDF) из {len(cands)} кандидатов")
    picks = (by_topic[:limit] if meta["selected_by"] == "topic"
             else sorted(rows, key=lambda r: (-r["mtime"], r["label"]))[:limit])

    tmp = tempfile.mkdtemp(prefix="article_gates_corpus_")
    written = []
    for r in picks:
        dst = os.path.join(tmp, f"{r['label']}.md")
        body = (html_body_text(read_head(r["path"]))
                if r["path"].lower().endswith((".html", ".htm"))
                else read_head(r["path"]))
        if not body.strip():
            continue
        with open(dst, "w", encoding="utf-8") as f:
            f.write(body)
        written.append({"label": r["label"], "source": r["source"],
                        "score": r["score"], "path": r["path"],
                        "weak": bool(r["score"] < MIN_TOPIC_SCORE)})
    meta["picks"] = written
    if not written:
        # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
        pass
        meta["note"] = (meta["note"] + " · " if meta["note"] else "") + \
            "у отобранных соседей пустое тело - сравнивать не с чем"
        meta["selected_by"] = "none"
        return None, meta
    return tmp, meta


def neighbour_lines(meta, short=False):
    """Строки «с кем сравнивали и почему» - в вывод гейта и в gates.json."""
    if not isinstance(meta, dict):
        return []
    how = {"topic": "по смыслу", "mtime-fallback": "ФОЛБЭК по времени файла",
           "none": "соседей нет"}.get(meta.get("selected_by"), "?")
    picks = meta.get("picks") or []
    if short:
        names = ", ".join(f"{p['label']}({p['score']})" for p in picks) or "-"
        return [f"соседи originality [{how}]: {names}"]
    c = meta.get("candidates") or {}
    out = [f"соседи для сравнения выбраны {how}: {meta.get('note') or '-'}",
           f"кандидатов: черновиков волны {c.get('черновики волны', 0)}, "
           f"живых страниц корпуса {c.get('живые страницы', 0)}"
           + (f" (слепок {meta['corpus_snapshot']})" if meta.get("corpus_snapshot") else
              " (слепка корпуса нет)")]
    for p in picks:
        out.append(f"  · {p['label']} - {p['source']}, близость темы {p['score']}"
                   + ("  ← слабый сигнал, добор" if p.get("weak") else ""))
    # молчаливых исключений в корпусе быть не должно: кого выкинули как «свою же
    # опубликованную страницу» - видно поимённо, иначе это дыра для самообмана
    for x in meta.get("excluded_self") or []:
        out.append(f"  ✕ не сравниваем со своей же опубликованной страницей: {x}")
    return out


# ── печать ───────────────────────────────────────────────────────────────────

MARK = {"PASS": "OK  ", "WARN": "~   ", "FAIL": "FAIL", "SKIP": "-   ", "ERROR": "ERR "}


def print_records(stage, slug, records, report_path, applicable=True, note=""):
    print(f"гейты [{stage}] {slug}" + ("" if applicable else "  · ДИАГНОСТИКА"))
    for r in records:
        flag = "" if r["required"] else " (advisory)"
        rc = "" if r["rc"] is None else f" rc={r['rc']}"
        print(f"  {MARK.get(r['status'], '?   ')} {r['name']}{rc}{flag} - {r['what']}")
        # число и порог - ПЕРВОЙ строкой под гейтом и при PASS тоже: сначала
        # «сколько намерили и чем мерили», потом «по каким текстам»
        for line in measure_lines(r):
            print(f"        {line}")
        for line in neighbour_lines(r.get("neighbours")):
            print(f"        {line}")
        if r["status"] in ("FAIL", "ERROR", "WARN", "SKIP") and r["out"]:
            shown = r.get("flags") or r["out"].splitlines()[-4:]
            for line in shown:
                print(f"        {line}")
    c = counts_of(records)
    print(f"  итог: PASS {c['PASS']} · WARN {c['WARN']} · FAIL {c['FAIL']} · "
          f"ERROR {c['ERROR']} · SKIP {c['SKIP']}")
    print(f"  отчёт: {report_path}")
    if applicable:
        print(f"  вердикт стадии: {verdict_of(records)}")
    else:
        print(f"  вердикт стадии: {verdict_of(records)} (ДИАГНОСТИЧЕСКИЙ, стадия неприменима)")
        print(f"        {note}")


def print_list(cfg):
    ctx = {"slug": "<slug>", "dir": "<$WORK>/<slug>", "originality_corpus": "<соседи>",
           "shared_files": ["<разделяемый-файл>"]}
    gates = build_gates(cfg, ctx)
    for stage in STAGES:
        rows = [g for g in gates if g["stage"] == stage]
        print(f"\nСТАДИЯ {stage} ({len(rows)} гейтов)")
        for g in rows:
            kind = "обязательный" if g["required"] else "advisory"
            base = os.path.basename(g["tool"]) if g["tool"] else "-"
            print(f"  · {g['name']:<22} [{kind}] {base} - {g['what']}")
    print("\nвердикт стадии = PASS, если ни один обязательный гейт не FAIL/ERROR "
          "(WARN и SKIP не роняют). Обязательный гейт без cmd отдаёт ERROR "
          "(не SKIP), если причина - НЕНАСТРОЕННОЕ ОКРУЖЕНИЕ (нет канона "
          "дверей/слепка корпуса); легитимный SKIP по данным прогона "
          "(нет соседей, гейт вне волны) вердикт не роняет")
    return 0


# ── selftest ─────────────────────────────────────────────────────────────────

STUB = ("#!/usr/bin/env python3\nimport sys\n"
        "sys.stdout.write({out!r})\nsys.exit({rc})\n")


def _stub(path, rc=0, out="stub\n"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(STUB.format(rc=rc, out=out))
    os.chmod(path, 0o755)


# ── эталонная статья песочницы ───────────────────────────────────────────────
# Гейт title-ctr - НЕ стаб, он считает по настоящим байтам. Значит фикстура
# обязана быть ПРАВИЛЬНОЙ статьёй, иначе позитивные тесты стадий (draft PASS,
# page PASS, три зелёные стадии = publish-ready) краснели бы не по делу.
FX_TITLE = "7 шагов сборки фикстуры: команды, проверки и живой вывод"
FX_DESC = ("Собрали фикстуру за 7 шагов: какие команды дать раннеру, что искать в "
           "выводе стадии и как понять, что расписка подписана живыми байтами")
FX_CAPSULE = (
    "Фикстура собирается за 7 шагов и держит все девять осей формулы сниппета "
    "сразу: длину заголовка, счётчик в нём, равенство с H1, обещание в описании, "
    "капсулу ответа, три таблицы и раскрытый FAQ. Ниже команды по порядку и живой "
    "вывод раннера, по которому видно каждую ось отдельной строкой")
# Перелинковка фикстуры (волна 3, по решению автора; порог поднят до 20 кругом 2
# по решению автора - дефект T6). Канон поднял хард-минимум
# внутренних ссылок с 3 до 12 по замеру дельты топ-3 (медиана у них 40, у нас
# 30), значит фикстура ПРАВИЛЬНОЙ статьи обязана нести 12 ссылок - иначе
# позитивные прогоны стадий краснели бы не по делу, ровно по той же причине,
# по которой фикстура несёт настоящий title и настоящий CTA-хвост
FX_LINKS = tuple("/guide-fixture-sosed-%d/" % i for i in range(1, 22))
FX_LINKS_MD = " ".join("[материал %d](%s)" % (i + 1, u)
                       for i, u in enumerate(FX_LINKS))
FX_LINKS_HTML = "<p>" + " ".join('<a href="%s">материал %d</a>' % (u, i + 1)
                                 for i, u in enumerate(FX_LINKS)) + "</p>"
FX_DRAFT_BODY = (f"# {FX_TITLE}\n\n{FX_CAPSULE}\n\n## Раздел\n\nтекст\n\n"
                 f"{FX_LINKS_MD}\n")
FX_DRAFT_FM = (f'title: "{FX_TITLE}"\nh1: "{FX_TITLE}"\n'
               f'description: "{FX_DESC}"\nslug: guide-fixture\n')
_FX_TABLE = "<table><tr><th>что</th><td>значение</td></tr></table>"
# ── CTA песочницы ────────────────────────────────────────────────────────────
# Правильная страница фикстуры несёт ТРИ вида t.me-ссылок сразу: именной инвайт
# (его и сверяет гейт), шаринг и публичный канал автора. Так позитивный прогон
# доказывает не только «инвайт совпал», но и «шаринг с каналом гейт не трогает»
FX_INVITE = "https://t.me/+FXinvite000000000001"
FX_SHARE = "https://t.me/share/url?url=https%3A%2F%2Ffx.test%2Fguide-fixture%2F"
FX_CHANNEL = "https://t.me/fx_kanal_avtora"
FX_LITERALS = ["/staryy-lending-fixtury/", "fx_chuzhoy_bot"]
# ── infra-secrets песочницы (гейт infra-leak, р9-по решению автора) ────────────────
# RFC 5737 - зарезервированный ДЛЯ ДОКУМЕНТАЦИИ диапазон 203.0.113.0/24, не
# боевой IP ни при каких обстоятельствах. Ни один из двух литералов не входит
# в FX_PAGE - позитивный прогон фикстуры остаётся PASS по умолчанию
FX_INFRA_LITERALS = ["203.0.113.77", "fx-relay.fixture.test"]
FX_CTA_HTML = (f'<p><a class="btn-cta" href="{FX_INVITE}">Забрать путёвку</a></p>'
               f'<a class="share-btn" href="{FX_SHARE}">Telegram</a>'
               f'<a href="{FX_CHANNEL}">Канал автора</a>')
# ── хвост песочницы по КАНОНУ 4 build_page (правка владельца) ─────
# Памятка -> финальный призыв -> частые вопросы. Без этих трёх блоков ПОЗИТИВНЫЕ
# прогоны стадии page («page PASS», «три стадии зелёные») краснели бы на новом
# обязательном гейте cta-position не по делу: фикстура обязана быть ПРАВИЛЬНОЙ
# страницей, ровно по той же причине, по которой она несёт настоящий title
FX_CHECKLIST = ('<section id="checklist"><h2>Памятка сборки фикстуры</h2>'
                '<ul class="checklist"><li>шаг один</li><li>шаг два</li></ul></section>')
FX_FAQ_OPEN = '<section id="faq"><h2>Частые вопросы</h2>'
FX_FAQ_CLOSE = "</section>"


def _fx_cta_final(html_блок):
    """Промо-блок фикстуры в обёртке .cta-final, если её ещё нет."""
    if "cta-final" in html_блок:
        return html_блок
    return '<section class="cta cta-final">' + html_блок + "</section>"


def _fx_page(body_extra="", cta_html=None):
    return (
        "<html><head>"
        f"<title>{FX_TITLE}</title>"
        f'<meta name="description" content="{FX_DESC}" />'
        "</head><body>"
        f'<h1 class="article-h1">{FX_TITLE}</h1>'
        '<div class="article-meta"><span>Обновлено: 14 августа 2026</span></div>'
        f"<p>{FX_CAPSULE}</p>"
        + _FX_TABLE * 3
        + FX_LINKS_HTML
        + FX_CHECKLIST
        # промо-блок фикстуры встаёт МЕЖДУ памяткой и FAQ. Если тест подал свой
        # cta_html, УЖЕ несущий .cta-final (так делают негативы жаргона уровня
        # CTA-блока), второй раз не оборачиваем - вложенных cta-final на живой
        # странице не бывает, и CTA_BLOCK_RE на них считал бы блоки дважды
        + (_fx_cta_final(FX_CTA_HTML if cta_html is None else cta_html))
        + FX_FAQ_OPEN
        + "<details open><summary>Вопрос один</summary><p>ответ</p></details>"
          "<details open><summary>Вопрос два</summary><p>ответ</p></details>"
        + FX_FAQ_CLOSE
        + body_extra
        + "</body></html>")


FX_PAGE = _fx_page()
# конфиг порогов песочницы: те же значения, что дефолты, плюс СВОЯ запрещённая
# формула - по ней видно, что подпроцесс гейта реально читает конфиг, а не
# только зашитые дефолты
FX_FORMULA = "формула из конфига фикстуры"
FX_YAML = f"""tools:
  title_ctr:
    min_len: 51
    max_len: 66
    desc_min_len: 130
    desc_max_len: 165
    desc_dup_prefix_chars: 30
    capsule_min_words: 40
    capsule_max_words: 60
    min_tables: 3
    banned_formulas:
      - "{FX_FORMULA}"
      - "полный гайд"
    banned_tails: []
    version_brands:
      - claude
      - gpt
"""


def _fixture(root, codes=None, published=False, corpus_ready=True, page=None,
             cta_ready=True, infra_secrets=True):
    """Песочница: свои tools/ со стабами, свой work/<slug>, свой конфиг.

    corpus_ready (р7-по решению автора, фикс SKIP->ERROR): True (дефолт) - канон дверей,
    claim_gate И слепок корпуса настроены стабами, ЧЕТЫРЕ условных гейта
    publish (door-titles/claim-shared/reflections/hub-counts/hub-membership) реально
    ИСПОЛНЯЮТСЯ, а не тихо SKIP - иначе позитивные тесты (B7 «три стадии
    зелёные») проверяли бы дырявый по конструкции прогон. False - старое
    поведение (ключи не настроены вовсе) для теста именно ЭТОГО дефекта.

    infra_secrets (р9-по решению автора, гейт infra-leak): True (дефолт) - песочница
    несёт СВОЙ infra-secrets.txt с литералами FX_INFRA_LITERALS (ни один не
    входит в FX_PAGE, гейт реально исполняется и PASS по умолчанию); False -
    ключ конфига указывает на несуществующий файл, для теста ветки «список
    не настроен» (SKIP). БЕЗ этого ключа тест ушёл бы искать канонный
    ~/.business/growth/seo/infra-secrets.txt (боевой файл машины) -
    ровно та же дыра герметичности, что у corpus_ready/дверей выше.
    """
    codes = codes or {}
    tools = os.path.join(root, "tools")
    tpl = os.path.join(root, "tpl")
    work = os.path.join(root, "work")
    slug = "guide-fixture"
    adir = os.path.join(work, slug)
    for d in (tools, tpl, adir, os.path.join(work, "guide-sosed")):
        os.makedirs(d, exist_ok=True)
    for n, key in (("structure-check.py", "structure"), ("ai-cadence-check.py", "cadence"),
                   ("originality-check.py", "originality"), ("read-aloud-check.py", "aloud"),
                   ("own-evidence-check.py", "own_evidence"),
                   # novice (рв даты запуска.2026) стабится ровно как соседи: песочница
                   # обязана оставаться герметичной, а боевой novice-check.py
                   # проверяется отдельным блоком тестов на СВОИХ фикстурах
                   ("novice-check.py", "novice")):
        _stub(os.path.join(tools, n), codes.get(key, 0))
    _stub(os.path.join(tpl, "strip_notes.py"), codes.get("strip", 0))
    # судья класса нулевой терпимости под --skip-novice (наряд R-48): стабится
    # как сосед по шаблону, боевой novice_zero.py проверяется своим блоком ниже
    _stub(os.path.join(tpl, "novice_zero.py"), codes.get("novice_zero", 0))
    _stub(os.path.join(tpl, "artifacts_gate.py"), codes.get("artifacts", 0))
    # qa-freshness (круг 13, по решению автора) стабится ровно как strip_notes: он тоже
    # сосед шаблона, а песочница обязана оставаться герметичной - боевой
    # qa_freshness.py проверяется своими прогонами на реальных каталогах статей
    _stub(os.path.join(tpl, "qa_freshness.py"), codes.get("qa_freshness", 0))
    # howto-text-match (круг 2, волна r21-20260829, в даты запуска.2026) - тем же
    # приёмом: сосед шаблона, песочница герметична, боевой howto_text_match.py
    # проверяется своими прогонами на живых страницах (контрпример - см. его
    # докстринг и 2-rabota-krug2-howto.md). Без этого стаба гейт ERROR'ил на
    # КАЖДОМ прогоне selftest (инструмент не найден в песочнице) - найдено и
    # закрыто в этом же круге, тем же прогоном --selftest, что нашёл дефект.
    _stub(os.path.join(tpl, "howto_text_match.py"), codes.get("howto_text_match", 0))
    # reflections/hub-counts/hub-membership стабятся ВСЕГДА (инструмент - не то, что чинит
    # corpus_ready=False): дефект р7-по решению автора - именно про отсутствие
    # corpus_snapshot/corpus_status при ЖИВОМ инструменте, не про его файл
    _stub(os.path.join(tools, "reflections_gate.py"), codes.get("reflections", 0))
    _stub(os.path.join(tools, "hub_counts.py"), codes.get("hub_counts", 0))
    _stub(os.path.join(tools, "hub_membership.py"), codes.get("hub_membership", 0))
    # door-titles/claim-shared - стабы, а не «нет-такого-файла», ТОЛЬКО когда
    # corpus_ready=True: только так позитивный прогон стадии publish
    # проверяет, что гейты РЕАЛЬНО ЗОВУТ инструмент (не молчаливый SKIP)
    corpus_snap = os.path.join(root, "corpus-slepok")
    corpus_status = os.path.join(root, "corpus-status.tsv")
    door_canon = os.path.join(root, "door-canon.json")
    if corpus_ready:
        _stub(os.path.join(tools, "door_gate.py"), codes.get("door", 0))
        _stub(os.path.join(tools, "claim_gate.py"), codes.get("claim", 0))
        os.makedirs(corpus_snap, exist_ok=True)
        with open(door_canon, "w", encoding="utf-8") as fh:
            fh.write("{}")
        with open(corpus_status, "w", encoding="utf-8") as fh:
            fh.write("")
    # draft.md - легаси-схема (без маркера), draft-v2.md - новый контракт:
    # применимость стадии draft решает именно он (см. шапку файла)
    for f, body in ((os.path.join(adir, "draft.md"),
                     f"---\n{FX_DRAFT_FM}---\n\n{FX_DRAFT_BODY}"),
                    (os.path.join(adir, "draft-v2.md"),
                     f"---\nengine: article_build\n{FX_DRAFT_FM}---\n\n{FX_DRAFT_BODY}"),
                    (os.path.join(adir, "index.html"), page or FX_PAGE),
                    (os.path.join(work, "guide-sosed", "draft.md"), "# сосед\n\nтекст\n")):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(body)
    # парсер конфига берём у скилла, если он на машине есть: так порог из
    # песочницы читается и без PyYAML. САМИ пороги - только из песочницы
    real_cfg_py = os.path.join(os.path.expanduser(FALLBACK["lm_tools"]), "_config.py")
    if os.path.isfile(real_cfg_py):
        shutil.copyfile(real_cfg_py, os.path.join(tools, "_config.py"))
    fx_yaml = os.path.join(root, "seo-config-fixture.yaml")
    with open(fx_yaml, "w", encoding="utf-8") as fh:
        fh.write(FX_YAML)
    # config.md песочницы + своя карта инвайтов: гейт cta обязан читать закон из
    # конфига, а не из зашитых значений, и в selftest этот конфиг СВОЙ - боевой
    # config.md автора сюда не подмешивается (герметичность песочницы)
    fx_invites = os.path.join(root, "fx-invites.json")
    with open(fx_invites, "w", encoding="utf-8") as fh:
        json.dump({slug: {"slug": slug, "link": FX_INVITE}}, fh, ensure_ascii=False)
    fx_lm_cfg = os.path.join(root, "lead-magnit-config.md")
    with open(fx_lm_cfg, "w", encoding="utf-8") as fh:
        fh.write("# config песочницы\n\n```yaml\n"
                 "domain: fx.test\n"
                 "target_url: https://fx.test/offer/\n"
                 "target_product: Продукт песочницы\n"
                 "cta:\n"
                 "  accepted_prefixes:\n"
                 "    - t.me/+\n"
                 + (f"  invites_map: {fx_invites}\n" if cta_ready else "")
                 + "  forbidden_literals:\n"
                 + "".join(f"    - {x}\n" for x in FX_LITERALS)
                 + "```\n")
    # infra-secrets.txt песочницы (гейт infra-leak, р9-по решению автора) - см.
    # докстринг параметра infra_secrets выше про герметичность
    fx_infra_secrets = os.path.join(root, "infra-secrets-fixture.txt")
    if infra_secrets:
        with open(fx_infra_secrets, "w", encoding="utf-8") as fh:
            fh.write("# литералы песочницы, не боевые (RFC 5737)\n\n"
                     + "".join(f"{x}\n" for x in FX_INFRA_LITERALS)
                     + "root@\nseo-site\n")
    cfg_file = os.path.join(root, "seo-publish.json")
    # реестр публикаций фикстуры: пустой = статья не опубликована (стадия draft
    # применима), с записью = опубликована (стадия draft уходит в диагностику)
    reg_file = os.path.join(root, "registry.json")
    with open(reg_file, "w", encoding="utf-8") as fh:
        json.dump({"https://fx.test/guide-fixture/": {"datePublished": "2026-08-12"}}
                  if published else {}, fh)
    # песочница обязана быть герметичной: без явных путей условные гейты
    # (двери/claim/корпус/реестр) нашли бы по канонному фолбэку БОЕВЫЕ файлы
    # машины и прогнались бы по фикстуре - selftest перестал бы быть
    # воспроизводимым. corpus_ready=False намеренно указывает на
    # НЕСУЩЕСТВУЮЩИЕ файлы (старое поведение) и не задаёт corpus_status вовсе -
    # ровно дефект р7-по решению автора, который тест «гейт без конфига» и проверяет
    cfg = {"work_dir": work, "lm_tools": tools, "template_dir": tpl,
           "artifacts_gate": os.path.join(tpl, "artifacts_gate.py"),
           "seo_scripts": os.path.join(root, "нет-скриптов"),
           "door_gate": (os.path.join(tools, "door_gate.py") if corpus_ready
                         else os.path.join(root, "нет-door_gate.py")),
           "door_canon": (door_canon if corpus_ready
                          else os.path.join(root, "нет-канона.json")),
           "claim_gate": (os.path.join(tools, "claim_gate.py") if corpus_ready
                          else os.path.join(root, "нет-claim_gate.py")),
           "reflections_gate": os.path.join(tools, "reflections_gate.py"),
           "hub_counts": os.path.join(tools, "hub_counts.py"),
           "hub_membership": os.path.join(tools, "hub_membership.py"),
           "domain": "https://fx.test", "page_prefix": "guide-",
           "content_sha_registry": reg_file,
           "skill_config": fx_yaml,
           "lead_magnit_config": fx_lm_cfg,
           # 🔴 БЕЗ этого ключа отбор соседей ушёл бы искать самый свежий
           # corpus-ГГГГ-ММ-ДД по канонному фолбэку и втянул бы в песочницу
           # БОЕВОЙ корпус машины - selftest перестал бы быть воспроизводимым
           "corpus_snapshot": (corpus_snap if corpus_ready
                               else os.path.join(root, "нет-слепка-корпуса")),
           "shared_files": ["/sitemap.xml"],
           "infra_secrets": (fx_infra_secrets if infra_secrets
                              else os.path.join(root, "нет-infra-secrets.txt"))}
    if corpus_ready:
        cfg["corpus_status"] = corpus_status
    with open(cfg_file, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    return {"work": work, "slug": slug, "dir": adir, "config": cfg_file,
            "tools": tools, "registry": reg_file, "yaml": fx_yaml,
            "lm_config": fx_lm_cfg, "invites": fx_invites,
            "corpus_snapshot": corpus_snap, "corpus_status": corpus_status,
            "infra_secrets": cfg["infra_secrets"]}


# ── песочница отбора соседей (фикс r8: соседи по смыслу, не по времени) ──────
# Тема песочницы - «промпты для нейросети». Близкие по теме тексты сделаны САМЫМИ
# СТАРЫМИ по времени файла, чужие по теме - самыми свежими: прежний отбор по
# mtime взял бы ровно не тех, и разница видна тестом, а не на глаз.

_NB_ТЕМА = ("промпт для нейросети роль контекст формат ответа проверка результата "
            "запрос модель шаблон промпта примеры уточнение")


def _nb_черновик(slug, title, разделы, тело):
    h2 = "\n\n".join(f"## {x}\n\nтекст раздела {x.lower()}" for x in разделы)
    return (f"---\nengine: {ENGINE_MARK}\ntitle: \"{title}\"\nh1: \"{title}\"\n"
            f"description: \"{title}\"\nslug: {slug}\n---\n\n# {title}\n\n{тело}\n\n{h2}\n")


def _nb_страница(title, тело, шум=True):
    мусор = ('<script>var СЕКРЕТНЫЙ_СКРИПТ=1;</script>'
             '<nav>МЕНЮ_САЙТА главная блог автор</nav>') if шум else ""
    h2 = "".join(f"<h2>{x}</h2><p>{x}</p>" for x in ("Роль", "Контекст", "Формат"))
    return (f"<html><head><title>{title}</title>"
            f'<meta name="description" content="{title}" /></head><body>'
            f"<main>{мусор}<h1>{title}</h1>{h2}<p>{тело}</p></main>"
            f"<footer>МЕНЮ_САЙТА подвал</footer></body></html>")


# донор: его кусок дословно списывает негативная фикстура
_NB_ДОНОР_ТЕЛО = (
    "Промпт для нейросети собирается из четырёх частей: роль, контекст, задача и "
    "формат ответа. Роль задаёт, кем модель себя считает во время работы. Контекст "
    "даёт факты, без которых ответ будет общим и бесполезным. Задача формулируется "
    "одним действием, а не списком пожеланий. Формат ответа описывает, что именно "
    "вернуть: таблицу, список шагов или короткий абзац. Проверка результата идёт "
    "по тем же четырём частям, и переписывать промпт надо ровно ту часть, которая "
    "дала слабый ответ, а не весь запрос целиком.")


def _песочница_соседей(root):
    """work + слепок корпуса + две фикстуры черновика (копия / свои слова)."""
    work = os.path.join(root, "work")
    snap = os.path.join(root, "snapshot")
    for d in (work, snap):
        os.makedirs(d, exist_ok=True)
    свежие = ("ипотека ставка банк первоначальный взнос",
              "рецепт теста духовка выпечка мука",
              "велосипед цепь звёзды переключатель скорость")
    файлы = []
    # близкие по теме - старые; чужие по теме - свежие (прежний отбор брал их)
    for slug, title, тело in (
            ("guide-blizkiy-po-teme", "Как писать промпты для нейросети", _NB_ТЕМА),
            ("guide-tozhe-po-teme", "Шаблон промпта: роль, контекст, формат", _NB_ТЕМА)):
        os.makedirs(os.path.join(work, slug), exist_ok=True)
        p = os.path.join(work, slug, "draft.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(_nb_черновик(slug, title, ("Роль", "Контекст", "Формат ответа"), тело))
        файлы.append((p, 1_000_000))
    for i, тема in enumerate(свежие, start=1):
        slug = f"guide-svezhiy-{i}"
        os.makedirs(os.path.join(work, slug), exist_ok=True)
        p = os.path.join(work, slug, "draft.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(_nb_черновик(slug, тема.split()[0].capitalize(),
                                  тема.split()[:3], тема))
        файлы.append((p, 2_000_000 + i))
    # своя статья: её draft.md и её же живая страница в корпус попасть не должны
    os.makedirs(os.path.join(work, "guide-tema"), exist_ok=True)
    draft = os.path.join(work, "guide-tema", "draft.md")
    with open(draft, "w", encoding="utf-8") as fh:
        fh.write(_nb_черновик("guide-tema", "Промпты для нейросети: 7 шагов",
                              ("Роль", "Контекст", "Формат ответа", "Проверка"),
                              _NB_ТЕМА))
    файлы.append((draft, 1_500_000))
    # spec.json: опубликованный slug статьи НЕ равен имени каталога прогонов
    # (боевой случай: article-case-skilly-system вышел как
    # /guide-unikalizaciya-viralnyh-karuselej/)
    with open(os.path.join(work, "guide-tema", "spec.json"), "w", encoding="utf-8") as fh:
        json.dump({"slug": "guide-drugoe-imya"}, fh)
    for slug, title, тело in (
            ("guide-donor", "Промпт для нейросети: роль, контекст, формат",
             _NB_ДОНОР_ТЕЛО),
            ("guide-chuzhoy", "Ипотека и первоначальный взнос",
             "ставка банк договор страховка платёж график"),
            # своя же страница под ДРУГИМ slug (сверка по spec.json)
            ("guide-drugoe-imya", "Промпты для нейросети: 7 шагов", _NB_ТЕМА),
            # своя же страница после РЕТАЙТЛА (сверка по заголовку, не по slug)
            ("guide-posle-retitle", "Промпты для нейросети: 7 шагов и проверка",
             _NB_ТЕМА),
            ("guide-tema", "Промпты для нейросети: 7 шагов", _NB_ТЕМА)):
        os.makedirs(os.path.join(snap, slug), exist_ok=True)
        p = os.path.join(snap, slug, "index.html")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(_nb_страница(title, тело))
        файлы.append((p, 900_000))
    for p, ts in файлы:
        os.utime(p, (ts, ts))
    # негативная фикстура: дословный кусок страницы guide-donor
    копия = os.path.join(root, "draft-kopiya.md")
    with open(копия, "w", encoding="utf-8") as fh:
        fh.write(_nb_черновик("guide-tema", "Промпты для нейросети: 7 шагов",
                              ("Роль", "Контекст", "Формат ответа"),
                              _NB_ДОНОР_ТЕЛО))
    # позитивная: та же тема, свои слова и своя фактура
    свои = os.path.join(root, "draft-svoimi-slovami.md")
    with open(свои, "w", encoding="utf-8") as fh:
        fh.write(_nb_черновик(
            "guide-tema", "Промпты для нейросети: 7 шагов",
            ("Роль", "Контекст", "Формат ответа"),
            "Я держу отдельный файл заготовок и складываю туда каждую удачную "
            "формулировку сразу после прогона. Замер по своим 40 прогонам: короткое "
            "поручение с одним действием и приложенным файлом фактов даёт годный "
            "черновик с первого раза в 31 случае, длинное пожелание списком - в 9. "
            "Поэтому я сначала пишу, что должно получиться на выходе, потом сокращаю "
            "поручение до одного глагола, и только затем прикладываю фактуру."))
    return {"work": work, "snapshot": snap, "draft": draft, "root": root,
            "копия": копия, "свои": свои,
            "cfg": {"corpus_snapshot": snap, "page_prefix": "guide-"}}


def боевой_порог_косинуса(по_умолчанию=0.80):
    """Порог косинуса, как его увидит БОЕВОЙ originality-check: из конфига скилла.

    🔴 Своего значения тут нет и быть не должно. Порог живёт ровно в одном месте -
    `tools.originality.max_cosine` конфига скилла (seo-engine/
    seo-config-reference.yaml, поверх него config.md автора). Второй источник
    порога = ровно та дыра, из-за которой калибровку r8 пришлось делать вслепую:
    вывод гейта показывал одно число, а тест сверялся с другим, зашитым в код.
    Здесь порог ЧИТАЕТСЯ тем же парсером и тем же поиском конфига, что у чекера,
    поэтому откат остаётся правкой ОДНОГО ключа - тесты едут за ним.
    """
    tools = os.path.expanduser(FALLBACK["lm_tools"])
    добавили = False
    try:
        if tools not in sys.path:
            sys.path.insert(0, tools)
            добавили = True
        import _config as cfgmod
        cfg = cfgmod.load_config(cfgmod.find_config())
        v = cfgmod.get(cfg, "tools.originality.max_cosine", None)
        return float(v) if v is not None else по_умолчанию
    except (ImportError, TypeError, ValueError, OSError):
        return по_умолчанию
    finally:
        if добавили and tools in sys.path:
            sys.path.remove(tools)


# ── фикстура «полоса принятой нормы» (калибровка r8, по решению автора) ─────────────
#
# 🔴 ЗАЧЕМ. Дефект, который гейт обязан ловить, - ДОСЛОВНОЕ заимствование, и его
# ловит нога max_ngram. Косинус же меряет БЛИЗОСТЬ ТЕМЫ, и после смены состава
# корпуса (соседи по смыслу вместо случайных по времени) он у нормального текста
# закономерно вырос. Замер по решению автора по 239 опубликованным страницам: медиана
# косинуса 0.606, p95 0.814 - то есть старый порог 0.60 лёг на медиану ПРИНЯТОГО
# владельцем корпуса и красил половину. Ниже - воспроизводимая фикстура ровно
# этой формы: словарь темы общий (косинус в полосе 0.6-0.8), дословных цепочек
# нет вовсе (ngram 0). Она пришпиливает калибровку: сдвинешь порог обратно вниз -
# тест назовёт это возвратом регресса, а не промолчит.
_НБ_ОБЩИЕ = ("промпт нейросеть роль контекст задача формат ответ модель факты "
             "действие список шаги таблица абзац проверка результат запрос часть "
             "переписать слабый").split()
_НБ_СВОИ_A = ("замер прогон черновик заготовка файл глагол выход сокращение "
              "поручение случай сорок тридцать один девять формулировка удачная "
              "складываю держу отдельный сразу").split()
_НБ_СВОИ_B = ("витрина карточка магазин цена доставка отзыв рейтинг склад остаток "
              "скидка акция бренд категория поиск фильтр корзина оплата возврат "
              "курьер пункт").split()


def _текст_полосы_нормы(seed, свои, доля=0.7, слов=300):
    """«Та же тема, свои слова»: общий словарь темы + собственная фактура.

    Генератор детерминированный (random.Random(seed) - Mersenne Twister, ряд
    зафиксирован спецификацией), поэтому числа фикстуры воспроизводятся на любой
    машине и в любой сборке Python 3.
    """
    r = random.Random(seed)
    return " ".join(r.choice(_НБ_ОБЩИЕ if r.random() < доля else свои)
                    for _ in range(слов))


def _прогон_пары(инструмент, текст_a, текст_b, max_cosine, max_ngram=0.30):
    """Прогнать НАСТОЯЩИЙ originality-check по паре текстов. (rc, вывод, замер)."""
    root = tempfile.mkdtemp(prefix="article_gates_pair_")
    try:
        draft = os.path.join(root, "draft.md")
        corp = os.path.join(root, "corpus")
        os.makedirs(corp, exist_ok=True)
        with open(draft, "w", encoding="utf-8") as f:
            f.write(текст_a)
        with open(os.path.join(corp, "etalon.md"), "w", encoding="utf-8") as f:
            f.write(текст_b)
        p = subprocess.run([sys.executable or "python3", инструмент, draft, corp,
                            "--max-cosine", str(max_cosine),
                            "--max-ngram", str(max_ngram), "--ngram-n", "5"],
                           capture_output=True, text=True, timeout=120)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out, (originality_measure(out) or {})
    finally:
        # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
        pass


def _прогон_оригинальности(nb, инструмент, черновик, max_cosine=None):
    """Отобрать соседей по этому черновику и прогнать НАСТОЯЩИЙ originality-check.

    Порог косинуса по умолчанию - БОЕВОЙ, из конфига скилла (см.
    боевой_порог_косинуса): тест обязан проверять то же число, которым меряет
    боевой прогон, иначе калибровка и тесты разъезжаются молча.
    """
    max_cosine = боевой_порог_косинуса() if max_cosine is None else max_cosine
    corp, _ = neighbour_corpus(nb["work"], "guide-tema", limit=3, cfg=nb["cfg"],
                               draft_path=черновик)
    if not corp:
        return 3, "корпус соседей не собрался"
    try:
        p = subprocess.run([sys.executable or "python3", инструмент, черновик, corp,
                            "--max-cosine", str(max_cosine), "--max-ngram", "0.30",
                            "--ngram-n", "5"],
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    finally:
        отложить(corp, ignore_errors=True)   # закон №0: не сносим, откладываем


def selftest():
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    def call(fx, *argv):
        return main(list(argv) + ["--config", fx["config"], "--quiet"])

    root = tempfile.mkdtemp(prefix="article_gates_selftest_")

    # 1. ПОЗИТИВ: все стабы зелёные -> стадия draft PASS, отчёт написан
    fx = _fixture(os.path.join(root, "pos"))
    rc = call(fx, fx["slug"], "--stage", "draft")
    rep = os.path.join(fx["dir"], "gates.json")
    doc = json.load(open(rep, encoding="utf-8")) if os.path.isfile(rep) else {}
    check("позитив: draft PASS, rc=0", rc == 0, f"rc={rc}")
    check("позитив: gates.json написан", os.path.isfile(rep))
    # 4 гейта было до этой редакции; пятым встал title-ctr (формула сниппета),
    # седьмым - novice (стандарт «понятно новичку», рв даты запуска.2026),
    # восьмым - retract-sync (отозванная формулировка не живёт в файле-
    # источнике, r14 круг в даты запуска.2026)
    # девятым - svezhaya-tema (закон 25 канона, класс «свежая узкая тема», по решению автора)
    # десятым и одиннадцатым - title-god и vnutrennie-ssylki (дельта топ-3,
    # волна 3 захода 2026-08-29-seo-x4-kanon)
    check("позитив: в отчёте 12 гейтов стадии draft (четвёртый исторический + "
          "title-ctr + own-evidence r8 + novice r14 + retract-sync r14к15 + "
          "svezhaya-tema по решению автора + title-god и vnutrennie-ssylki по решению автора волна 3 + "
          "own-run-shagi по решению автора круг 2)",
          len(doc.get("stages", {}).get("draft", {}).get("gates", [])) == 12,
          str(len(doc.get("stages", {}).get("draft", {}).get("gates", []))))
    check("позитив: originality увидел соседа (не SKIP)",
          [g for g in doc["stages"]["draft"]["gates"]
           if g["name"] == "originality"][0]["status"] == "PASS")

    # 2. НАКОПЛЕНИЕ: page не стирает draft
    rc2 = call(fx, fx["slug"], "--stage", "page")
    doc2 = json.load(open(rep, encoding="utf-8"))
    check("позитив: page PASS, rc=0", rc2 == 0, f"rc={rc2}")
    check("накопление: в gates.json обе стадии",
          set(doc2.get("stages", {})) == {"draft", "page"}, str(list(doc2.get("stages", {}))))

    # 3. НЕГАТИВ: структурный чекер валится -> стадия FAIL, rc=1
    fx2 = _fixture(os.path.join(root, "neg-structure"), codes={"structure": 1})
    rc3 = call(fx2, fx2["slug"], "--stage", "draft")
    d3 = json.load(open(os.path.join(fx2["dir"], "gates.json"), encoding="utf-8"))
    gr = [g for g in d3["stages"]["draft"]["gates"] if g["name"] == "structure"][0]
    check("негатив: FAIL чекера роняет стадию", rc3 == 1, f"rc={rc3}")
    check("негатив: rc чекера записан в отчёт", gr["rc"] == 1 and gr["status"] == "FAIL",
          str(gr))

    # 4. НЕГАТИВ: advisory-гейт (read-aloud) с rc=1 НЕ роняет вердикт
    fx3 = _fixture(os.path.join(root, "advisory"), codes={"aloud": 1})
    rc4 = call(fx3, fx3["slug"], "--stage", "draft")
    d4 = json.load(open(os.path.join(fx3["dir"], "gates.json"), encoding="utf-8"))
    ga = [g for g in d4["stages"]["draft"]["gates"] if g["name"] == "read-aloud"][0]
    check("позитив: advisory rc=1 = WARN, вердикт стоит",
          rc4 == 0 and ga["status"] == "WARN", f"rc={rc4} status={ga['status']}")

    # 4b. НЕГАТИВ: own-evidence (r8) валится -> стадия FAIL (обязательный, не advisory)
    fx3b = _fixture(os.path.join(root, "own-evidence-fail"), codes={"own_evidence": 1})
    rc4b = call(fx3b, fx3b["slug"], "--stage", "draft")
    d4b = json.load(open(os.path.join(fx3b["dir"], "gates.json"), encoding="utf-8"))
    goe = [g for g in d4b["stages"]["draft"]["gates"] if g["name"] == "own-evidence"][0]
    check("негатив: own-evidence FAIL (rc=1) роняет стадию draft (гейт обязательный)",
          rc4b == 1 and goe["status"] == "FAIL", f"rc={rc4b} status={goe['status']}")

    # 4c. own-evidence rc=2 (r15, по решению автора) - own=measure блоков нет ни в одной
    #     форме, но статья заявляет собственный замер. WARN, а не тихий PASS и не
    #     FAIL: гейт ГРОМКО пишет, что сверять было нечего ровно там, где надо,
    #     но вердикт стадии не роняет - решение за человеком
    fx3c = _fixture(os.path.join(root, "own-evidence-warn"), codes={"own_evidence": 2})
    rc4c = call(fx3c, fx3c["slug"], "--stage", "draft")
    d4c = json.load(open(os.path.join(fx3c["dir"], "gates.json"), encoding="utf-8"))
    gow = [g for g in d4c["stages"]["draft"]["gates"] if g["name"] == "own-evidence"][0]
    check("own-evidence rc=2 (блоков нет, но замер заявлен) = WARN, вердикт стоит",
          rc4c == 0 and gow["status"] == "WARN" and RC_OWN_EVIDENCE[2] == "WARN",
          f"rc={rc4c} status={gow['status']}")

    # 5. НЕГАТИВ: обязательный инструмент отсутствует -> ERROR, стадия FAIL
    fx4 = _fixture(os.path.join(root, "no-tool"))
    отложить(os.path.join(fx4["tools"], "structure-check.py"))   # закон №0
    rc5 = call(fx4, fx4["slug"], "--stage", "draft")
    d5 = json.load(open(os.path.join(fx4["dir"], "gates.json"), encoding="utf-8"))
    ge = [g for g in d5["stages"]["draft"]["gates"] if g["name"] == "structure"][0]
    check("негатив: нет инструмента = ERROR + FAIL стадии",
          rc5 == 1 and ge["status"] == "ERROR", f"rc={rc5} status={ge['status']}")

    # 6. НЕГАТИВ: артефактный гейт валится -> publish FAIL, соседние гейты
    # независимы (не каскадируют в FAIL просто потому что artifacts-post упал).
    # Фикстура corpus_ready=True (дефолт): door-titles/reflections/hub-counts/hub-membership
    # НАСТОЯЩИЕ, реально исполняются (стаб rc=0) - claim-shared легитимно SKIP
    # (нет SEO_WAVE в окружении selftest, вне волны это не дефект, см. р7-по решению автора)
    fx5 = _fixture(os.path.join(root, "no-artifacts"), codes={"artifacts": 1})
    rc6 = call(fx5, fx5["slug"], "--stage", "publish")
    d6 = json.load(open(os.path.join(fx5["dir"], "gates.json"), encoding="utf-8"))
    by_name6 = {g["name"]: g for g in d6["stages"]["publish"]["gates"]}
    check("негатив: publish без артефактов = FAIL",
          rc6 == 1 and by_name6["artifacts-post"]["status"] == "FAIL",
          f"rc={rc6} status={by_name6['artifacts-post']['status']}")
    check("настроенные условные гейты publish РЕАЛЬНО ИСПОЛНЯЮТСЯ (не каскадный FAIL "
          "и не SKIP), независимо от соседнего artifacts-post",
          all(by_name6[n]["status"] == "PASS"
              for n in ("door-titles", "reflections", "hub-counts", "hub-membership")),
          str({n: by_name6[n]["status"] for n in ("door-titles", "reflections", "hub-counts", "hub-membership")}))
    check("claim-shared вне волны (SEO_WAVE не задан) - легитимный SKIP, это не "
          "класс config_gap (нет ключа, который можно прописать - это про прогон)",
          by_name6["claim-shared"]["status"] == "SKIP", str(by_name6["claim-shared"]))

    # 6б. р7-по решению автора (obshchesaytovoe-otchet.md «что поднять в канон» п.1):
    # ОБЯЗАТЕЛЬНЫЙ гейт без своего конфига (нет corpus_snapshot/corpus_status,
    # нет канона дверей) -> ГРОМКИЙ ERROR, а НЕ тихий SKIP, и вердикт стадии
    # ПАДАЕТ. До фикса эти три гейта тут были SKIP при вердикте PASS - молчаливая
    # дыра, которую усиленный прогон r7 вскрыл только вручную (2 SKIP из 5)
    fx5b = _fixture(os.path.join(root, "no-corpus-config"), corpus_ready=False)
    rc6b = call(fx5b, fx5b["slug"], "--stage", "publish")
    d6b = json.load(open(os.path.join(fx5b["dir"], "gates.json"), encoding="utf-8"))
    by_name6b = {g["name"]: g for g in d6b["stages"]["publish"]["gates"]}
    check("гейт без настроенного окружения = rc 1 (вердикт стадии падает, не PASS)",
          rc6b == 1, f"rc={rc6b}")
    check("гейт без настроенного окружения = ERROR, а не тихий SKIP "
          "(door-titles/reflections/hub-counts/hub-membership)",
          all(by_name6b[n]["status"] == "ERROR"
              for n in ("door-titles", "reflections", "hub-counts", "hub-membership")),
          str({n: by_name6b[n]["status"] for n in ("door-titles", "reflections", "hub-counts", "hub-membership")}))
    check("ERROR называет НЕДОСТАЮЩИЙ КЛЮЧ конфига поимённо (лечение видно глазами)",
          "corpus_snapshot" in by_name6b["reflections"]["out"]
          and "corpus_status" in by_name6b["reflections"]["out"]
          and "door_gate" in by_name6b["door-titles"]["out"]
          and "door_canon" in by_name6b["door-titles"]["out"],
          str({"reflections": by_name6b["reflections"]["out"],
               "door-titles": by_name6b["door-titles"]["out"]}))
    check("вердикт стадии publish = FAIL при ERROR обязательного условного гейта "
          "(верно и по verdict_of, и по печатному вердикту стадии)",
          d6b["stages"]["publish"]["verdict"] == "FAIL", str(d6b["stages"]["publish"]["verdict"]))

    # 6в. Контраст: тот же класс гейта, но окружение НАСТРОЕНО (слепок и канон
    # заданы, инструмент существует) - гейт исполняется по-настоящему (PASS
    # стабом), это НЕ SKIP и НЕ ERROR. Доказывает, что фикс не сделал гейт
    # вечно красным - он просто перестал молчать, когда входа нет
    fx5c = _fixture(os.path.join(root, "corpus-present"), corpus_ready=True)
    rc6c = call(fx5c, fx5c["slug"], "--stage", "publish")
    d6c = json.load(open(os.path.join(fx5c["dir"], "gates.json"), encoding="utf-8"))
    by_name6c = {g["name"]: g for g in d6c["stages"]["publish"]["gates"]}
    check("гейт СО слепком/каноном реально исполняется -> PASS (не SKIP, не ERROR)",
          rc6c == 0 and all(by_name6c[n]["status"] == "PASS"
                            for n in ("door-titles", "reflections", "hub-counts", "hub-membership")),
          f"rc={rc6c} " + str({n: by_name6c[n]["status"]
                               for n in ("door-titles", "reflections", "hub-counts", "hub-membership")}))
    check("гейт СО слепком реально зовёт инструмент со снятыми путями (cmd несёт "
          "--snapshot и --status слепка, а не пустой None)",
          "--snapshot" in by_name6c["reflections"]["cmd"]
          and fx5c["corpus_snapshot"] in by_name6c["reflections"]["cmd"]
          and fx5c["corpus_status"] in by_name6c["reflections"]["cmd"],
          str(by_name6c["reflections"]["cmd"]))

    # 7. НЕГАТИВ: нет каталога статьи -> rc=2 (ошибка входа, не «всё хорошо»)
    rc7 = call(fx, "guide-net-takogo", "--stage", "draft")
    check("негатив: нет каталога = rc 2", rc7 == 2, f"rc={rc7}")

    # 8. НЕГАТИВ: стадия page без index.html -> rc=2
    fx6 = _fixture(os.path.join(root, "no-page"))
    отложить(os.path.join(fx6["dir"], "index.html"))   # закон №0
    rc8 = call(fx6, fx6["slug"], "--stage", "page")
    check("негатив: нет index.html = rc 2", rc8 == 2, f"rc={rc8}")

    # 9. НЕГАТИВ: стадия draft без draft.md -> rc=2
    fx7 = _fixture(os.path.join(root, "no-draft"))
    отложить(os.path.join(fx7["dir"], "draft.md"))   # закон №0
    rc9 = call(fx7, fx7["slug"], "--stage", "draft")
    check("негатив: нет draft.md = rc 2", rc9 == 2, f"rc={rc9}")

    # 10. --list печатает все три стадии и не требует статьи
    buf = os.path.join(root, "list.txt")
    old = sys.stdout
    try:
        with open(buf, "w", encoding="utf-8") as fh:
            sys.stdout = fh
            rc10 = main(["--list", "--config", fx["config"]])
    finally:
        sys.stdout = old
    txt = open(buf, encoding="utf-8").read()
    check("--list: все три стадии, rc=0",
          rc10 == 0 and all(f"СТАДИЯ {s}" in txt for s in STAGES), f"rc={rc10}")

    # 10б. Наблюдение скептика-18: прогон ПО ИМЕНИ пишет в БОЕВОЙ каталог, и
    # предупреждение об этом стоит ПЕРВОЙ строкой - после прогона читать поздно
    def _печать(fx_, *argv):
        p = os.path.join(root, "out-%d.txt" % len(results))
        o = sys.stdout
        try:
            with open(p, "w", encoding="utf-8") as fh:
                sys.stdout = fh
                main(list(argv) + ["--config", fx_["config"], "--quiet"])
        finally:
            sys.stdout = o
        return open(p, encoding="utf-8").read()

    fx_w = _fixture(os.path.join(root, "warn"))
    _txt_w = _печать(fx_w, fx_w["slug"], "--stage", "page")
    # НАБЛЮДЕНИЕ-1 скептика-20: печатается РАЗРЕШЁННЫЙ realpath, не сырой
    # `fx_w["dir"]` - на этой машине /var сам симлинк на /private/var, так что
    # проверка литерального `fx_w["dir"]` молча перестала бы что-либо ловить,
    # если бы код тихо вернулся к сырому пути (регресс был бы невидим тестом).
    check("скептик-18: <slug> без явного пути ПРЕДУПРЕЖДАЕТ первой строкой, что "
          "отчёт уйдёт в боевой $WORK/<slug>/gates.json (НАБЛЮДЕНИЕ-1: путь - "
          "разрешённый realpath, не сырой ввод)",
          _txt_w.splitlines()[0].startswith("⚠️ article_gates: отчёт уйдёт в БОЕВОЙ")
          and os.path.join(os.path.realpath(fx_w["dir"]), "gates.json") in _txt_w
          and "--no-write" in _txt_w, _txt_w[:200])
    check("скептик-18: --no-write предупреждения НЕ печатает (боевой отчёт не "
          "трогается - предупреждать не о чем)",
          "уйдёт в БОЕВОЙ" not in _печать(fx_w, fx_w["slug"], "--stage", "page",
                                          "--no-write"))
    # 10в. Наблюдение скептика-19 (3/3, по решению автора): старая проверка сравнивала
    # `os.path.isdir(cand)` - СЫРУЮ строку аргумента, а не РЕАЛЬНЫЙ каталог.
    # Относительный вызов из cwd=$WORK (bare slug совпадает с настоящим
    # подкаталогом cwd) резолвился в тот же боевой каталог, но `isdir(cand)`
    # читал это как «явный путь дан» и предупреждение молчало. Сравнение теперь
    # через `os.path.realpath`: неважно, КАК записан путь (по имени, относительно
    # cwd, полным дублирующим абсолютным путём) - предупреждение спрашивает
    # КУДА он физически указывает.
    _cwd_старый19 = os.getcwd()
    try:
        os.chdir(fx_w["work"])
        _txt_rel19 = _печать(fx_w, fx_w["slug"], "--stage", "page")
    finally:
        os.chdir(_cwd_старый19)
    # НАБЛЮДЕНИЕ-1 скептика-20: РОВНО этот вызов (bare-имя, cwd=$WORK) раньше
    # печатал `adir` КАК ЗАДАН - голое "guide-fixture/gates.json" без единой
    # директории контекста (`adir = cand`, `cand` = сырой относительный
    # аргумент). Теперь путь - ВСЕГДА разрешённый realpath, вне зависимости
    # от того, каким был ввод.
    check("скептик-19 (3/3, полюс А) + М35-набл.1: относительный вызов из "
          "cwd=$WORK (старая isdir(cand)-проверка эту дыру не видела) ТОЖЕ "
          "предупреждает, и путь в сообщении - ПОЛНЫЙ realpath, а не голое "
          "относительное имя «guide-fixture/gates.json»",
          _txt_rel19.splitlines()[0].startswith("⚠️ article_gates: отчёт уйдёт в БОЕВОЙ")
          and os.path.join(os.path.realpath(fx_w["dir"]), "gates.json") in _txt_rel19
          and "БОЕВОЙ %s/gates.json" % fx_w["slug"] not in _txt_rel19,
          _txt_rel19[:200])

    _txt_abs19 = _печать(fx_w, fx_w["dir"], "--stage", "page")
    check("скептик-19 (3/3, полюс Б): полный АБСОЛЮТНЫЙ путь, который РЕАЛЬНО "
          "указывает на тот же $WORK/<slug>, предупреждает не меньше вызова по "
          "имени - предупреждение спрашивает КУДА указывает путь, а не КАК он "
          "записан (старый тест ошибочно принимал этот путь за «диагностику на "
          "копии», хотя это ровно боевой каталог)",
          _txt_abs19.splitlines()[0].startswith("⚠️ article_gates: отчёт уйдёт в БОЕВОЙ"),
          _txt_abs19[:200])

    _копия19 = os.path.join(root, "копия-guide-fixture")
    shutil.copytree(fx_w["dir"], _копия19)
    check("скептик-19 (3/3, полюс В): путь на НАСТОЯЩУЮ копию (другой реальный "
          "каталог, физически не $WORK/<slug>) молчит - предупреждение не "
          "срабатывает вслепую на любом непустом пути",
          "уйдёт в БОЕВОЙ" not in _печать(fx_w, _копия19, "--stage", "page"))

    check("скептик-19 (3/3, полюс Г): явный --report по-прежнему молчит "
          "(диагностика уходит НЕ в боевой gates.json, поведение --report не "
          "затронуто фиксом)",
          "уйдёт в БОЕВОЙ" not in _печать(
              fx_w, fx_w["slug"], "--stage", "page",
              "--report", os.path.join(root, "копия-gates.json")))

    # 11. В7: словарь verdicts вместо одиночного verdict_last. Диагностический
    # прогон draft НЕ затирает в шапке живой PASS стадии page
    fx8 = _fixture(os.path.join(root, "verdicts"))
    call(fx8, fx8["slug"], "--stage", "page")           # page PASS
    rep8 = os.path.join(fx8["dir"], "gates.json")
    page_at = json.load(open(rep8, encoding="utf-8"))["stages"]["page"]["ran_at"]
    # тот же каталог, но структурный чекер теперь красный: гоним draft
    _stub(os.path.join(fx8["tools"], "structure-check.py"), 1)
    call(fx8, fx8["slug"], "--stage", "draft")          # draft FAIL
    d8 = json.load(open(rep8, encoding="utf-8"))
    check("В7: ключа verdict_last больше нет", "verdict_last" not in d8, str(list(d8)))
    check("В7: verdicts несёт вердикт КАЖДОЙ стадии",
          d8["verdicts"]["page"]["verdict"] == "PASS"
          and d8["verdicts"]["draft"]["verdict"] == "FAIL",
          str(d8.get("verdicts")))
    check("В7: время прогона page не сдвинулось прогоном draft",
          d8["verdicts"]["page"]["ran_at"] == page_at, str(d8["verdicts"]["page"]))
    check("В7: publish-ready = FAIL, блокеры названы поимённо",
          d8["verdict_publish_ready"]["verdict"] == "FAIL"
          and any(b.startswith("draft:") for b in d8["verdict_publish_ready"]["blockers"])
          and any(b.startswith("publish:") for b in d8["verdict_publish_ready"]["blockers"]),
          str(d8["verdict_publish_ready"]))

    # 12. В7: publish-ready зелёный только когда все три стадии зелёные
    fx9 = _fixture(os.path.join(root, "ready"))
    for st in ("draft", "page", "publish"):
        call(fx9, fx9["slug"], "--stage", st)
    d9 = json.load(open(os.path.join(fx9["dir"], "gates.json"), encoding="utf-8"))
    check("В7: три зелёные стадии = publish-ready PASS",
          d9["verdict_publish_ready"]["verdict"] == "PASS", str(d9["verdict_publish_ready"]))
    # р7-по решению автора: claim-shared здесь легитимно SKIP (selftest гонится вне волны,
    # SEO_WAVE не задан) - и вердикт СТАДИИ publish всё равно PASS. Это ровно
    # доказывает границу фикса: НЕ каждый SKIP обязательного гейта роняет
    # вердикт - падает только config_gap (см. тест 6б), а легитимный
    # операционный SKIP (вне волны) вердикт стадии не трогает, как и раньше
    claim9 = [gt for gt in d9["stages"]["publish"]["gates"] if gt["name"] == "claim-shared"][0]
    check("SKIP легитимного (не config_gap) гейта НЕ роняет вердикт стадии publish",
          claim9["status"] == "SKIP" and d9["stages"]["publish"]["verdict"] == "PASS",
          f"claim-shared={claim9['status']} вердикт={d9['stages']['publish']['verdict']}")

    # 13. В7: --no-write не создаёт и не трогает отчёт
    fx10 = _fixture(os.path.join(root, "nowrite"))
    rep10 = os.path.join(fx10["dir"], "gates.json")
    rc_nw = main([fx10["slug"], "--stage", "draft", "--config", fx10["config"],
                  "--quiet", "--no-write"])
    check("В7: --no-write не создал gates.json",
          rc_nw == 0 and not os.path.isfile(rep10), f"rc={rc_nw} exists={os.path.isfile(rep10)}")
    call(fx10, fx10["slug"], "--stage", "page")
    before = open(rep10, encoding="utf-8").read()
    main([fx10["slug"], "--stage", "draft", "--config", fx10["config"],
          "--quiet", "--no-write"])
    check("В7: --no-write не изменил существующий gates.json",
          open(rep10, encoding="utf-8").read() == before)

    # 14. В7: стадия draft на ОПУБЛИКОВАННОЙ статье = диагностика (rc 0, не блокер)
    fx11 = _fixture(os.path.join(root, "published"), codes={"structure": 1}, published=True)
    rc11 = call(fx11, fx11["slug"], "--stage", "draft")
    d11 = json.load(open(os.path.join(fx11["dir"], "gates.json"), encoding="utf-8"))
    check("В7: draft опубликованной статьи = rc 0 при FAIL чекера",
          rc11 == 0 and d11["stages"]["draft"]["verdict"] == "FAIL", f"rc={rc11}")
    check("В7: диагностический прогон помечен applicable false + причина",
          d11["stages"]["draft"]["applicable"] is False
          and "опубликована" in d11["stages"]["draft"].get("applicability_note", ""),
          str(d11["stages"]["draft"].get("applicability_note")))
    check("В7: неприменимая стадия не блокирует publish-ready",
          not any(b.startswith("draft:") for b in d11["verdict_publish_ready"]["blockers"]),
          str(d11["verdict_publish_ready"]["blockers"]))
    fx12 = _fixture(os.path.join(root, "unpublished"), codes={"structure": 1})
    rc12 = call(fx12, fx12["slug"], "--stage", "draft")
    check("В7: у НЕопубликованной статьи draft остаётся замком (rc 1)", rc12 == 1, f"rc={rc12}")

    # 14б. Б1: у ЧЕРНОВИКА НОВОГО КОНТРАКТА стадия draft - ЗАМОК даже на
    # опубликованной статье: этот файл и есть источник истины статьи
    fx13 = _fixture(os.path.join(root, "new-contract-published"),
                    codes={"structure": 1}, published=True)
    rc13 = call(fx13, fx13["slug"], "--stage", "draft", "--draft", "draft-v2.md")
    d13 = json.load(open(os.path.join(fx13["dir"], "gates.json"), encoding="utf-8"))
    check("Б1: draft нового контракта у опубликованной статьи = ЗАМОК (rc 1)",
          rc13 == 1, f"rc={rc13}")
    check("Б1: прогон нового контракта помечен applicable true",
          d13["stages"]["draft"].get("applicable") is True,
          str(d13["stages"]["draft"].get("applicable")))
    check("Б1: неприменимой стадия нового контракта не объявляется",
          "applicability_note" not in d13["stages"]["draft"])
    # тот же каталог, но легаси-черновик -> диагностика (поведение не тронуто)
    rc13b = call(fx13, fx13["slug"], "--stage", "draft")
    check("Б1: легаси-черновик опубликованной статьи остался диагностикой (rc 0)",
          rc13b == 0, f"rc={rc13b}")

    # 14в. --draft: стадия гонится по НАЗВАННОМУ файлу, а не по draft.md
    fx14 = _fixture(os.path.join(root, "draft-flag"))
    call(fx14, fx14["slug"], "--stage", "draft", "--draft", "draft-v2.md")
    d14 = json.load(open(os.path.join(fx14["dir"], "gates.json"), encoding="utf-8"))
    cmds = " ".join(g.get("cmd") or "" for g in d14["stages"]["draft"]["gates"])
    check("--draft: чекеры получили draft-v2.md, а не draft.md",
          "draft-v2.md" in cmds and cmds.count("draft.md") == 0, cmds[:200])
    rc14 = call(fx14, fx14["slug"], "--stage", "draft", "--draft", "нет-такого.md")
    check("--draft: нет названного черновика = rc 2", rc14 == 2, f"rc={rc14}")

    # 15. Б3: стадия publish спрашивает уровень --post, а не --min
    cmd_pub = [g for g in build_gates({}, {"slug": "s", "dir": "/tmp/s"})
               if g["name"] == "artifacts-post"][0]["cmd"]
    check("Б3: publish зовёт artifacts_gate с --post", cmd_pub[-1] == "--post", str(cmd_pub))

    # 16. --revision снимает жёсткую ось tool-article
    ctx = {"slug": "s", "dir": "/tmp/s", "revision": True}
    cmd_rev = [g for g in build_gates({}, ctx) if g["name"] == "structure-visual"][0]["cmd"]
    ctx["revision"] = False
    cmd_new = [g for g in build_gates({}, ctx) if g["name"] == "structure-visual"][0]["cmd"]
    check("--revision: tool-article-hard только у новой статьи",
          "--tool-article-hard" in cmd_new and "--tool-article-hard" not in cmd_rev)

    # ── 17. Б16: ЗАПИСЬ СТАДИИ ПОДПИСЫВАЕТ БАЙТЫ СТРАНИЦЫ ───────────────────
    # Расписка «page=PASS» без sha страницы - расписка ни на что: пересобрал
    # index.html, вписал мусор, переминтил - и вердикт вчерашнего прогона
    # продолжал открывать двери. Проверяем оба полюса: поле есть и оно ВЕРНОЕ;
    # после пересборки страницы оно с живыми байтами РАСХОДИТСЯ.
    fx16 = _fixture(os.path.join(root, "b16-sha"))
    страница = os.path.join(fx16["dir"], "index.html")
    call(fx16, fx16["slug"], "--stage", "page")
    d16 = json.load(open(os.path.join(fx16["dir"], "gates.json"), encoding="utf-8"))
    зап16 = d16["stages"]["page"]
    факт16 = hashlib.sha256(open(страница, "rb").read()).hexdigest()
    check("Б16: стадия page несёт page_sha256 ЭТОЙ страницы",
          зап16.get("page_sha256") == факт16,
          f"в отчёте {str(зап16.get('page_sha256'))[:12]}, факт {факт16[:12]}")
    check("Б16: стадия page несёт имя и размер страницы",
          зап16.get("page") == "index.html"
          and зап16.get("page_bytes") == os.path.getsize(страница),
          f"{зап16.get('page')} / {зап16.get('page_bytes')}")
    # стадия draft байты страницы не подписывает - ей нечего подписывать
    call(fx16, fx16["slug"], "--stage", "draft")
    d16b = json.load(open(os.path.join(fx16["dir"], "gates.json"), encoding="utf-8"))
    check("Б16: стадия draft поля page_sha256 не заводит (подписывать нечего)",
          "page_sha256" not in d16b["stages"]["draft"]
          and d16b["stages"]["page"].get("page_sha256") == факт16)
    # пересборка страницы БЕЗ перегона гейтов: поле осталось на старых байтах
    with open(страница, "w", encoding="utf-8") as fh:
        fh.write("<html><body>x<!-- мусор после гейтов --></body></html>")
    d16c = json.load(open(os.path.join(fx16["dir"], "gates.json"), encoding="utf-8"))
    новый16 = hashlib.sha256(open(страница, "rb").read()).hexdigest()
    check("Б16: страницу пересобрали - подпись стадии с живыми байтами разошлась",
          d16c["stages"]["page"].get("page_sha256") != новый16)
    # перегон стадии page - подпись снова про живые байты (одна команда лечения)
    call(fx16, fx16["slug"], "--stage", "page")
    d16d = json.load(open(os.path.join(fx16["dir"], "gates.json"), encoding="utf-8"))
    check("Б16: перегон --stage page переподписывает расписку на живые байты",
          d16d["stages"]["page"].get("page_sha256") == новый16,
          f"{str(d16d['stages']['page'].get('page_sha256'))[:12]} vs {новый16[:12]}")
    # стадия publish - тот же закон
    fx17 = _fixture(os.path.join(root, "b16-publish"))
    call(fx17, fx17["slug"], "--stage", "publish")
    d17 = json.load(open(os.path.join(fx17["dir"], "gates.json"), encoding="utf-8"))
    check("Б16: стадия publish тоже подписывает байты страницы",
          d17["stages"]["publish"].get("page_sha256")
          == hashlib.sha256(open(os.path.join(fx17["dir"], "index.html"), "rb").read()).hexdigest())

    # ── 18. ГЕЙТ title-ctr: позитив И негатив на КАЖДУЮ из девяти осей ──────
    # Оси считает чистая функция tc_findings, её и зовём напрямую: так тест
    # проверяет ПРАВИЛО, а не обвязку. Обвязку (стадии, --revision, конфиг,
    # коды выхода) проверяет блок 19 сквозными прогонами.
    TH = tc_thresholds({})

    def _поля(**kw):
        f = {"title": FX_TITLE, "h1": FX_TITLE, "description": FX_DESC,
             "capsule": FX_CAPSULE, "capsule_code": False, "md_h1": "",
             "source": "тест", "tables": 3, "details": 2, "details_open": 2}
        f.update(kw)
        return f

    def _замечания(stage="page", th=None, **kw):
        bad, _ = tc_findings(_поля(**kw), th or TH, stage)
        return bad

    def _есть(bad, кусок):
        return any(кусок in b for b in bad)

    базовые = _замечания()
    check("title-ctr ПОЗИТИВ (общий): правильная статья не даёт ни одного замечания "
          "по всем девяти осям", базовые == [], str(базовые))

    # ось 1 - длина title
    check("ось 1 позитив: длина 56 знаков в вилке 51-66 - молчит",
          not _есть(базовые, "длина title"))
    короткий = _замечания(title=FX_TITLE[:50], h1=FX_TITLE[:50])
    check("ось 1 негатив: 50 знаков - «короче вилки»",
          _есть(короткий, "длина title 50 знаков вне вилки 51-66")
          and _есть(короткий, "недоиспользован показ"), str(короткий))
    длинный_t = FX_TITLE + " и ещё немного"
    длинный = _замечания(title=длинный_t, h1=длинный_t)
    check("ось 1 негатив: 70 знаков - вне вилки, «переписывает в 76% случаев»",
          len(длинный_t) == 70
          and _есть(длинный, "длина title 70 знаков вне вилки 51-66")
          and _есть(длинный, "76%"), str(длинный))
    # ── границы новой вилки (правка 23.08.2026, конфликт с волной CTR-ретайтла) ─
    # Ровно 66 знаков - живой потолок волны (её самый длинный заголовок), он ОБЯЗАН
    # быть зелёным. 67 знаков - уже красный: полосу подняли на измеренную величину,
    # а не «отключили ось».
    гр66 = FX_TITLE + " раннера"          # 56 + 8 = 64
    гр66 = гр66 + "ab"                    # ровно 66
    гр67 = гр66 + "в"                     # ровно 67
    зам66 = _замечания(title=гр66, h1=гр66)
    зам67 = _замечания(title=гр67, h1=гр67)
    check("ось 1 граница: ровно 66 знаков (потолок живой волны ретайтла) - вилку "
          "проходит",
          len(гр66) == 66 and not _есть(зам66, "длина title"), str(зам66))
    check("ось 1 граница: 67 знаков - красный (вилка поднята, а не снята)",
          len(гр67) == 67 and _есть(зам67, "длина title 67 знаков вне вилки 51-66"),
          str(зам67))
    check("ось 1 граница: 50 знаков остались красными и после подъёма верха "
          "(низ вилки не трогали)",
          _есть(короткий, "вне вилки 51-66"))
    # мягкая справка про обрезку в Google живёт в info, вердикт не роняет
    _, инфо66 = tc_findings(_поля(title=гр66, h1=гр66), TH, "page")
    _, инфо56 = tc_findings(_поля(), TH, "page")
    check("ось 1: 61-66 знаков печатают МЯГКУЮ справку про обрезку в Google "
          "(автор видит размен), но замечанием это не становится",
          any("~ soft" in s and "600px" in s for s in инфо66)
          and not any("600px" in s for s in инфо56), str(инфо66[-1])[:120])

    # ось 2 - счётчик-число, НЕ год и НЕ версия продукта
    check("ось 2 позитив: «7 шагов» размечено счётчиком",
          [n["kind"] for n in tc_numbers(FX_TITLE, TH["version_brands"])] == ["счётчик"]
          and not _есть(базовые, "нет числа-счётчика"))
    без_числа = "Сборка фикстуры без счётчика: команды и живой вывод"
    б2 = _замечания(title=без_числа, h1=без_числа)
    check("ось 2 негатив: title без единого числа",
          _есть(б2, "нет числа-счётчика") and not _есть(б2, "нужно ДРУГОЕ"), str(б2))
    год_t = "Сборка фикстуры 2026: команды раннера и живой вывод"
    б2г = _замечания(title=год_t, h1=год_t)
    check("ось 2 негатив: год 2026 счётчиком не считается (ложный зелёный №1)",
          _есть(б2г, "нет числа-счётчика") and _есть(б2г, "«2026» - год")
          and _есть(б2г, "нужно ДРУГОЕ число"), str(б2г))
    вер_t = "Claude 5 в сборке фикстуры: команды и живой вывод раннера"
    б2в = _замечания(title=вер_t, h1=вер_t)
    check("ось 2 негатив: «Claude 5» - номер версии продукта, а не счётчик "
          "(ложный зелёный №2), гейт требует ДРУГОЕ число",
          _есть(б2в, "нет числа-счётчика") and _есть(б2в, "номер версии продукта")
          and _есть(б2в, "нужно ДРУГОЕ число"), str(б2в))
    виды = {n["text"]: n["kind"]
            for n in tc_numbers("GPT 5.6 против Claude 5: 7 промптов и 80+ моделей "
                                "в 2026", TH["version_brands"])}
    check("ось 2 разметка: версия через точку, версия по бренду, год - мимо; "
          "«7» и «80+» - счётчики",
          виды == {"5": "версия", "6": "версия", "7": "счётчик",
                   "80+": "счётчик", "2026": "год"}, str(виды))
    смеш = "GPT 5.6: 7 промптов для сборки фикстуры и живого вывода"
    check("ось 2 позитив: у статьи про модель с цифрой засчитан ДРУГОЙ счётчик",
          not _есть(_замечания(title=смеш, h1=смеш), "нет числа-счётчика"))
    check("ось 2 позитив: «10 минут» после бренда - всё-таки счётчик "
          "(русское слово-предмет после числа)",
          [n["kind"] for n in tc_numbers("Claude 10 команд", TH["version_brands"])]
          == ["счётчик"])

    # ось 3 - title == H1 символ в символ
    check("ось 3 позитив: title и H1 совпадают - молчит",
          not _есть(базовые, "title и H1 расходятся"))
    check("ось 3 негатив: H1 отличается одним словом",
          _есть(_замечания(h1=FX_TITLE.replace("живой", "сухой")),
                "title и H1 расходятся"))
    check("ось 3 негатив: H1 не найден вовсе",
          _есть(_замечания(h1=""), "H1 не найден"))

    # ось 4 - брендовый хвост
    TH_хвост = tc_thresholds({}, ("Автор Тестов",))
    хвост_t = "7 шагов сборки фикстуры: команды и вывод - Автор Тестов"
    check("ось 4 позитив: хвоста в title нет - молчит",
          not _есть(_замечания(th=TH_хвост), "брендовый хвост"))
    check("ось 4 негатив: хвост автора в title",
          _есть(_замечания(th=TH_хвост, title=хвост_t, h1=хвост_t),
                "брендовый хвост «Автор Тестов»"))
    check("ось 4: хвост подставляется извне, а не зашит в раздаваемый конфиг",
          TC_DEFAULTS["banned_tails"] == []
          and _замечания(title=хвост_t, h1=хвост_t) == [])

    # ось 5 - запрещённые формулы
    check("ось 5 позитив: формулы нет - молчит",
          not _есть(базовые, "запрещённая формула"))
    форм_t = "Полный гайд по фикстуре: 7 команд и живой вывод раннера"
    check("ось 5 негатив: «полный гайд» ловится независимо от регистра",
          _есть(_замечания(title=форм_t, h1=форм_t), "запрещённая формула «полный гайд»"))

    # ось 6 - description
    check("ось 6 позитив: 135 знаков и своё начало - молчит",
          not _есть(базовые, "description"))
    check("ось 6 негатив: описание короче вилки",
          _есть(_замечания(description="Короткое описание фикстуры"),
                "длина description 26 знаков вне вилки 130-165"))
    check("ось 6 негатив: описание длиннее вилки",
          _есть(_замечания(description=FX_DESC + " и ещё полсотни знаков сверху, "
                                                 "чтобы вылезти за верхнюю границу"),
                "длина description 198 знаков вне вилки 130-165"))
    дубль = FX_TITLE + ", а дальше уже расшифровка обещания статьи для читателя"
    check("ось 6 негатив: первые 90 знаков описания начинаются самим title",
          _есть(_замечания(description=дубль), "description содержат title целиком"))

    # ось 7 - капсула ответа
    check("ось 7 позитив: 46 слов и цифра внутри - молчит",
          not _есть(базовые, "капсула"))
    check("ось 7 негатив: капсула короче 40 слов",
          _есть(_замечания(capsule="Ниже по шагам: что нужно до старта и какой "
                                   "промпт вставить"), "вне вилки 40-60"))
    check("ось 7 негатив: капсула длиннее 60 слов",
          _есть(_замечания(capsule=FX_CAPSULE + " " + FX_CAPSULE), "вне вилки 40-60"))
    без_цифр = re.sub(r"[0-9]", "", FX_CAPSULE)
    check("ось 7 негатив: в капсуле нет ни цифры, ни code",
          _есть(_замечания(capsule=без_цифр), "нет ни одной цифры"))
    check("ось 7 позитив: цифры нет, но есть тег code - засчитано",
          not _есть(_замечания(capsule=без_цифр, capsule_code=True), "нет ни одной цифры"))

    # ось 8 - таблицы (только собранная страница)
    check("ось 8 позитив: три таблицы - молчит", not _есть(базовые, "таблиц на странице"))
    check("ось 8 негатив: две таблицы при минимуме три",
          _есть(_замечания(tables=2), "таблиц на странице 2 при минимуме 3"))
    check("ось 8: на стадии draft таблицы не спрашиваются (вёрстки ещё нет)",
          not _есть(_замечания(stage="draft", tables=None), "таблиц на странице"))

    # ось 9 - раскрытый FAQ (только собранная страница)
    check("ось 9 позитив: все details раскрыты - молчит", not _есть(базовые, "FAQ свёрнут"))
    check("ось 9 негатив: восемь details, раскрыт один",
          _есть(_замечания(details=8, details_open=1),
                "блоков <details> 8, раскрытых 1"))
    check("ось 9: на стадии draft раскрытость FAQ не спрашивается",
          not _есть(_замечания(stage="draft", details=None, details_open=None),
                    "FAQ свёрнут"))

    # пороги действительно берутся из конфига, а не только из дефолтов
    TH_кфг = tc_thresholds({"tools": {"title_ctr": {"min_len": 10, "max_len": 20,
                                                    "min_tables": 9}}})
    check("пороги: значения конфига перекрывают дефолты",
          (TH_кфг["min_len"], TH_кфг["max_len"], TH_кфг["min_tables"]) == (10, 20, 9)
          and TH_кфг["capsule_min_words"] == 40, str(TH_кфг)[:120])
    check("пороги: битое значение в конфиге откатывается на дефолт, гейт не падает",
          tc_thresholds({"tools": {"title_ctr": {"min_len": "ерунда"}}})["min_len"] == 51)

    # чтение полей черновика: листинги и легаси-схема (оба ложняка найдены на
    # живом корпусе по решению автора - guide-karta и guide-kimi)
    поле_дир = os.path.join(root, "tc-fields")
    os.makedirs(поле_дир, exist_ok=True)
    листинг = (f'---\ntitle: "{FX_TITLE}"\nh1: "{FX_TITLE}"\n'
               f'description: "{FX_DESC}"\n---\n\n# {FX_TITLE}\n\n{FX_CAPSULE}\n\n'
               "```bash\n# в ~/.claude/settings.json заменить два значения\n"
               "ANTHROPIC_BASE_URL=https://api.example.ru\n```\n")
    п1 = os.path.join(поле_дир, "draft.md")
    with open(п1, "w", encoding="utf-8") as fh:
        fh.write(листинг)
    f_лист = tc_fields_draft(п1)
    check("чтение черновика: комментарий шелла из ```-листинга не читается как H1 "
          "(ложняк guide-karta по решению автора)",
          f_лист["md_h1"] == FX_TITLE and f_лист["capsule"].startswith("Фикстура"),
          f"md_h1={f_лист['md_h1'][:40]}")
    легаси = os.path.join(поле_дир, "draft-legacy.md")
    with open(легаси, "w", encoding="utf-8") as fh:
        fh.write(f'---\ntitle: "{FX_TITLE}"\nslug: x\n---\n\n{FX_CAPSULE}\n')
    спека = os.path.join(поле_дир, "spec.json")
    with open(спека, "w", encoding="utf-8") as fh:
        json.dump({"h1": FX_TITLE, "description": FX_DESC}, fh, ensure_ascii=False)
    f_лег = tc_fields_draft(легаси, спека)
    check("чтение черновика: у легаси-схемы h1 и description добираются из "
          "spec.json (источник истины такой статьи), источник назван в отчёте",
          f_лег["h1"] == FX_TITLE and f_лег["description"] == FX_DESC
          and "spec.json (h1, description)" in f_лег["source"], str(f_лег["source"]))
    check("чтение черновика: пустой spec.json ничего не выдумывает",
          tc_fields_draft(легаси)["h1"] == "")

    # ── 19. ГЕЙТ title-ctr: обвязка (стадии, --revision, конфиг, коды выхода) ─
    def _черновик(title, desc=FX_DESC, capsule=FX_CAPSULE):
        # перелинковка обязательна и здесь: черновик этого помощника
        # «правильный во всём, кроме проверяемой оси», а канон волны 3 поднял
        # хард-минимум внутренних ссылок до 12 (гейт vnutrennie-ssylki)
        return (f'---\ntitle: "{title}"\nh1: "{title}"\ndescription: "{desc}"\n'
                f'slug: guide-fixture\n---\n\n# {title}\n\n{capsule}\n\n'
                f'## Раздел\n\nтекст\n\n{FX_LINKS_MD}\n')

    def _положить(fx_, имя, тело):
        with open(os.path.join(fx_["dir"], имя), "w", encoding="utf-8") as fh:
            fh.write(тело)

    def _гейт(fx_, стадия, имя="title-ctr"):
        d = json.load(open(os.path.join(fx_["dir"], "gates.json"), encoding="utf-8"))
        return [g for g in d["stages"][стадия]["gates"] if g["name"] == имя][0]

    # состав команды: жёсткость снимается ровно так же, как ось tool-article
    ctx_tc = {"slug": "s", "dir": "/tmp/s", "draft": "/tmp/s/draft.md"}
    cmd_tc_new = [g for g in build_gates({}, ctx_tc)
                  if g["name"] == "title-ctr" and g["stage"] == "draft"][0]["cmd"]
    ctx_tc["revision"] = True
    cmd_tc_rev = [g for g in build_gates({}, ctx_tc)
                  if g["name"] == "title-ctr" and g["stage"] == "page"][0]["cmd"]
    check("title-ctr стоит в обеих стадиях, и в draft, и в page",
          {g["stage"] for g in build_gates({}, {"slug": "s", "dir": "/tmp/s"})
           if g["name"] == "title-ctr"} == {"draft", "page"})
    check("--revision снимает --tc-hard (тот же механизм, что у tool-article)",
          "--tc-hard" in cmd_tc_new and "--tc-hard" not in cmd_tc_rev,
          str(cmd_tc_rev))

    fx_tc = _fixture(os.path.join(root, "tc-clean"))
    rc_ок, вывод_ок = title_ctr_run(fx_tc["dir"], "page", hard=True,
                                    yaml_path=fx_tc["yaml"], tools_dir=fx_tc["tools"])
    check("сквозной позитив: правильная страница = rc 0 и «формула в норме»",
          rc_ок == 0 and any("OK. Формула сниппета в норме" in l for l in вывод_ок),
          f"rc={rc_ок}")
    check("сквозной позитив: пороги прочитаны из конфига песочницы, не из дефолтов",
          any(fx_tc["yaml"] in l and "пороги из" in l for l in вывод_ок), вывод_ок[1])

    _положить(fx_tc, "index.html", FX_PAGE.replace(_FX_TABLE * 3, _FX_TABLE * 2))
    rc_hard, _ = title_ctr_run(fx_tc["dir"], "page", hard=True,
                               yaml_path=fx_tc["yaml"], tools_dir=fx_tc["tools"])
    rc_soft, стр_soft = title_ctr_run(fx_tc["dir"], "page", hard=False,
                                      yaml_path=fx_tc["yaml"], tools_dir=fx_tc["tools"])
    check("коды выхода: замечания жёстко = rc 1, те же замечания ревизией = rc 2",
          (rc_hard, rc_soft) == (1, 2)
          and any("soft, ревизия" in l for l in стр_soft), f"{rc_hard}/{rc_soft}")
    rc_нет, стр_нет = title_ctr_run(os.path.join(root, "tc-clean"), "page", hard=True)
    check("нечего читать (нет index.html) = rc 3 -> ERROR, а не зелёный вердикт",
          rc_нет == 3 and any("ОШИБКА" in l for l in стр_нет), f"rc={rc_нет}")

    # сквозной прогон стадии: битый title роняет draft, ревизия его только желтит
    fx_bad = _fixture(os.path.join(root, "tc-draft-bad"))
    _положить(fx_bad, "draft.md", _черновик("Сборка фикстуры без счётчика: "
                                            "команды и живой вывод"))
    rc_bad = call(fx_bad, fx_bad["slug"], "--stage", "draft")
    g_bad = _гейт(fx_bad, "draft")
    check("сквозной негатив: title без счётчика роняет стадию draft (rc 1, FAIL)",
          rc_bad == 1 and g_bad["status"] == "FAIL", f"rc={rc_bad} {g_bad['status']}")
    check("сквозной негатив: в отчёт уехала ИМЕННО причина, а не хвост вывода",
          any("нет числа-счётчика" in s for s in g_bad.get("flags", [])),
          str(g_bad.get("flags")))
    check("сквозной негатив: соседние гейты стадии не покраснели за компанию",
          all(g["status"] == "PASS" for g in json.load(
              open(os.path.join(fx_bad["dir"], "gates.json"), encoding="utf-8")
          )["stages"]["draft"]["gates"] if g["name"] != "title-ctr"))
    rc_rev = call(fx_bad, fx_bad["slug"], "--stage", "draft", "--revision")
    g_rev = _гейт(fx_bad, "draft")
    check("--revision: та же статья = WARN и rc 0 (старый корпус не краснеет весь)",
          rc_rev == 0 and g_rev["status"] == "WARN", f"rc={rc_rev} {g_rev['status']}")

    fx_bp = _fixture(os.path.join(root, "tc-page-bad"))
    _положить(fx_bp, "index.html",
              FX_PAGE.replace("<details open>", "<details>", 1))
    rc_bp = call(fx_bp, fx_bp["slug"], "--stage", "page")
    g_bp = _гейт(fx_bp, "page")
    check("сквозной негатив: свёрнутый FAQ роняет стадию page (rc 1, FAIL)",
          rc_bp == 1 and g_bp["status"] == "FAIL"
          and any("FAQ свёрнут" in s for s in g_bp.get("flags", [])),
          f"rc={rc_bp} {g_bp['status']} {g_bp.get('flags')}")

    # конфиг и личный хвост доезжают до подпроцесса гейта
    fx_cfg = _fixture(os.path.join(root, "tc-config"))
    _положить(fx_cfg, "draft.md",
              _черновик(f"7 шагов сборки: {FX_FORMULA} в заголовке"))
    rc_cfg = call(fx_cfg, fx_cfg["slug"], "--stage", "draft")
    g_cfg = _гейт(fx_cfg, "draft")
    check("конфиг доезжает: СВОЯ запрещённая формула из yaml песочницы роняет гейт",
          rc_cfg == 1 and any(FX_FORMULA in s for s in g_cfg.get("flags", [])),
          f"rc={rc_cfg} {g_cfg.get('flags')}")

    fx_tail = _fixture(os.path.join(root, "tc-tail"))
    with open(fx_tail["config"], encoding="utf-8") as fh:
        _c = json.load(fh)
    _c["author_name"] = "Автор Тестов"
    with open(fx_tail["config"], "w", encoding="utf-8") as fh:
        json.dump(_c, fh)
    _положить(fx_tail, "draft.md", _черновик(хвост_t))
    rc_tail = call(fx_tail, fx_tail["slug"], "--stage", "draft")
    g_tail = _гейт(fx_tail, "draft")
    check("хвост из ЛИЧНОГО ~/.config/seo-publish.json (author_name) доезжает до гейта",
          rc_tail == 1 and any("брендовый хвост «Автор Тестов»" in s
                               for s in g_tail.get("flags", [])),
          f"rc={rc_tail} {g_tail.get('flags')}")

    # ── отбор соседей для originality (фикс r8, по решению автора) ──────────────────
    # Песочница герметична: свой work, свой слепок «корпуса», боевые файлы машины
    # не читаются. Проверяем ровно то, ради чего фикс: соседа выбирает ТЕМА, а не
    # время файла; кандидаты берутся из ОБОИХ источников; фолбэк честно помечен.
    nb_root = os.path.join(root, "neighbours")
    nb = _песочница_соседей(nb_root)

    corp, meta = neighbour_corpus(nb["work"], "guide-tema", limit=3,
                                  cfg=nb["cfg"], draft_path=nb["draft"])
    имена = [p["label"] for p in meta["picks"]]
    check("соседи: тема бьёт свежесть - профильный черновик взят, хотя он самый старый",
          "wave-guide-blizkiy-po-teme" in имена, f"{meta['selected_by']} {имена}")
    check("соседи: отбор идёт ПО СМЫСЛУ (selected_by=topic), а не по mtime",
          meta["selected_by"] == "topic", meta["selected_by"])
    check("соседи: свежие по времени, но чужие по теме, в тройку НЕ попали",
          not any(l.startswith("wave-guide-svezhiy") for l in имена), str(имена))
    check("соседи: прежний отбор по mtime этого соседа НЕ брал (иначе чинить нечего)",
          "guide-blizkiy-po-teme" not in [
              n for _, n, _ in sorted(
                  [(os.path.getmtime(os.path.join(nb["work"], d, "draft.md")), d,
                    os.path.join(nb["work"], d, "draft.md"))
                   for d in os.listdir(nb["work"]) if d != "guide-tema"],
                  reverse=True)[:3]])
    check("соседи: живая страница слепка корпуса - тоже кандидат",
          any(l.startswith("live-") for l in имена), str(имена))
    check("соседи: у живой страницы источник назван «живая страница корпуса»",
          all(p["source"] == "живая страница корпуса"
              for p in meta["picks"] if p["label"].startswith("live-")))
    check("соседи: своя же живая страница (тот же slug) в корпус сравнения не едет",
          "live-guide-tema" not in имена, str(имена))
    исключено = " · ".join(meta.get("excluded_self") or [])
    check("соседи: своя же страница под ДРУГИМ slug (из spec.json) исключена",
          "live-guide-drugoe-imya" not in имена
          and "guide-drugoe-imya" in исключено, исключено)
    check("соседи: своя же страница ПОСЛЕ РЕТАЙТЛА исключена по заголовку",
          "live-guide-posle-retitle" not in имена
          and "guide-posle-retitle (заголовок совпал" in исключено, исключено)
    check("соседи: чужая страница на ту же тему за «свою» НЕ принята (донор остался)",
          "live-guide-donor" in имена and "guide-donor" not in исключено,
          f"{имена} | {исключено}")
    check("соседи: свой draft.md в корпус не едет (иначе косинус 1.0 и вечный FAIL)",
          "wave-guide-tema" not in имена and not os.path.isfile(
              os.path.join(corp or nb_root, "wave-guide-tema.md")), str(имена))
    check("соседи: число соседей = limit (дефолт не меньше прежних трёх)",
          len(meta["picks"]) == 3 and NEIGHBOURS_DEFAULT >= 3,
          f"{len(meta['picks'])} / дефолт {NEIGHBOURS_DEFAULT}")
    строки = neighbour_lines(meta)
    check("соседи: вывод гейта называет, С КЕМ сравнивали и ПОЧЕМУ выбрали этих",
          any("по смыслу" in s for s in строки)
          and all(any(l in s for s in строки) for l in имена), str(строки))
    check("соседи: исключения печатаются поимённо, молчаливого выброса нет",
          sum(1 for s in строки if s.startswith("  ✕")) == len(meta["excluded_self"])
          and len(meta["excluded_self"]) == 3,
          str([s for s in строки if s.startswith("  ✕")]))
    # обвязка страницы (скрипты, навигация, футер) в корпус сравнения не едет
    живой = [p for p in meta["picks"] if p["label"].startswith("live-")]
    тело = read_head(os.path.join(corp, живой[0]["label"] + ".md")) if живой and corp else ""
    check("соседи: из живой страницы в корпус уехало ТЕЛО, а не скрипты и меню",
          "СЕКРЕТНЫЙ_СКРИПТ" not in тело and "МЕНЮ_САЙТА" not in тело
          and "промпт" in тело.lower(), тело[:120])
    отложить(corp, ignore_errors=True)   # закон №0: не сносим, откладываем

    # ФОЛБЭК: черновик без профиля темы -> честная пометка + прежнее поведение
    пустой = os.path.join(nb["work"], "guide-tema", "draft-bez-shapki.md")
    with open(пустой, "w", encoding="utf-8") as fh:
        fh.write("просто текст без шапки и без заголовков\n" * 5)
    corp_fb, meta_fb = neighbour_corpus(nb["work"], "guide-tema", limit=3,
                                        cfg=nb["cfg"], draft_path=пустой)
    check("фолбэк: нет профиля темы -> selected_by=mtime-fallback, не молчаливый пропуск",
          meta_fb["selected_by"] == "mtime-fallback" and meta_fb["note"],
          f"{meta_fb['selected_by']} {meta_fb['note']}")
    check("фолбэк: пометка видна в выводе гейта (ФОЛБЭК по времени файла)",
          any("ФОЛБЭК" in s for s in neighbour_lines(meta_fb)),
          str(neighbour_lines(meta_fb)))
    check("фолбэк: соседи те же, что брал прежний код - три самых свежих",
          [p["label"] for p in meta_fb["picks"]][:1] == ["wave-guide-svezhiy-3"],
          str([p["label"] for p in meta_fb["picks"]]))
    отложить(corp_fb, ignore_errors=True)   # закон №0: не сносим, откладываем

    check("соседи: справка об отборе уехала в gates.json рядом с гейтом originality",
          isinstance(_гейт(fx, "draft", "originality").get("neighbours"), dict)
          and _гейт(fx, "draft", "originality")["neighbours"].get("picks") is not None,
          str(_гейт(fx, "draft", "originality").get("neighbours"))[:120])

    # ── СКВОЗНОЕ с НАСТОЯЩИМ originality-check (не стабом) ───────────────────
    # Негативная фикстура: текст дословно повторяет кусок конкретной страницы
    # корпуса - обязан ловиться. Позитивная: та же тема своими словами - проходит.
    настоящий = os.path.join(os.path.expanduser(FALLBACK["lm_tools"]),
                             "originality-check.py")
    if os.path.isfile(настоящий):
        rc_копия, вых_копия = _прогон_оригинальности(nb, настоящий, nb["копия"])
        rc_свой, вых_свой = _прогон_оригинальности(nb, настоящий, nb["свои"])
        check("негативная фикстура: дословная копия куска страницы корпуса = FAIL",
              rc_копия == 1, f"rc={rc_копия} {вых_копия.strip().splitlines()[-1:]}")
        check("негативная фикстура: в вердикте назван ИМЕННО тот донор, что списан",
              "guide-donor" in вых_копия, вых_копия[-200:])
        check("позитивная фикстура: та же тема своими словами = PASS",
              rc_свой == 0, f"rc={rc_свой} {вых_свой.strip().splitlines()[-1:]}")

        # ── КАЛИБРОВКА ПОРОГА (r8, по решению автора) ───────────────────────────────
        порог = боевой_порог_косинуса()
        check("калибровка: боевой порог косинуса читается из конфига скилла, "
              "а не зашит в код гейта",
              isinstance(порог, float) and 0.3 <= порог <= 1.0, f"порог={порог}")

        # 🔴 ГЛАВНАЯ УЛИКА калибровки: дословную копию держит нога max_ngram, а
        # НЕ косинус. Поэтому поднять порог косинуса до верха полосы принятой
        # нормы можно, не ослабив ловлю заимствования ни на грамм.
        rc_шире, вых_шире = _прогон_оригинальности(nb, настоящий, nb["копия"],
                                                   max_cosine=0.99)
        зам_копия = originality_measure(вых_копия) or {}
        check("калибровка: дословная копия остаётся FAIL даже при max_cosine 0.99 - "
              "заимствование держит нога max_ngram, а не косинус",
              rc_шире == 1, f"rc={rc_шире} {вых_шире.strip().splitlines()[-1:]}")
        check("калибровка: у дословной копии обе ноги пробиты с запасом "
              "(косинус ~0.87, ngram ~0.69 при пороге 0.30)",
              зам_копия.get("cosine", 0) > 0.80 and зам_копия.get("ngram", 0) > 0.60,
              str(зам_копия))

        # Полоса принятой нормы: одна тема, свои слова, дословных цепочек НЕТ.
        # Ровно эта форма и краснела массово на старом пороге 0.60.
        норма_a = _текст_полосы_нормы(1, _НБ_СВОИ_A)
        норма_b = _текст_полосы_нормы(2, _НБ_СВОИ_B)
        rc_н, вых_н, зам_н = _прогон_пары(настоящий, норма_a, норма_b, порог)
        rc_н60, _, _ = _прогон_пары(настоящий, норма_a, норма_b, 0.60)
        check("калибровка: фикстура «полоса нормы» и правда в полосе "
              "(косинус 0.60-0.80) и БЕЗ дословных цепочек (ngram 0)",
              0.60 < зам_н.get("cosine", 0) < 0.80 and зам_н.get("ngram", 1) == 0.0,
              str(зам_н))
        check("калибровка: на СТАРОМ пороге 0.60 «одна тема, свои слова» краснела - "
              "это и есть регресс, ради которого калибровали",
              rc_н60 == 1, f"rc={rc_н60} {зам_н}")
        if порог >= 0.80:
            check("калибровка: на боевом пороге «одна тема, свои слова» проходит "
                  "(принятый владельцем корпус не краснеет массово)",
                  rc_н == 0, f"порог={порог} rc={rc_н} {зам_н}")
        else:
            check(f"калибровка: порог откачен на {порог} - регресс вернулся "
                  f"осознанно, «одна тема, свои слова» снова красная",
                  rc_н == 1, f"порог={порог} rc={rc_н} {зам_н}")

        # ── ЧИСЛО И ПОРОГ ВИДНЫ В ВЫВОДЕ ГЕЙТА (в том числе при PASS) ────────
        зам_свой = originality_measure(вых_свой) or {}
        check("вывод: замер снимается и с ЗЕЛЁНОГО прогона тоже "
              "(число + порог + ближайший эталон)",
              "cosine" in зам_свой and "max_cosine" in зам_свой
              and "ngram" in зам_свой and зам_свой.get("closest"), str(зам_свой))
        check("вывод: порог в замере - тот самый, которым мерил боевой прогон",
              abs(зам_свой.get("max_cosine", -1) - порог) < 1e-9,
              f"{зам_свой.get('max_cosine')} против {порог}")
        строки_зам = measure_lines({"measure": зам_свой})
        check("вывод: строка гейта несёт И число, И порог",
              len(строки_зам) == 1
              and str(зам_свой["cosine"]) in строки_зам[0]
              and f"≤{зам_свой['max_cosine']}" in строки_зам[0]
              and f"≤{зам_свой['max_ngram']}" in строки_зам[0], str(строки_зам))
        check("вывод: у ЗЕЛЁНОГО гейта строки «порог пробит» нет",
              not any("порог пробит" in s for s in строки_зам), str(строки_зам))
        строки_кр = measure_lines({"measure": зам_копия})
        check("вывод: у КРАСНОГО гейта названа нога, из-за которой он красный",
              any("порог пробит" in s and "дословные n-граммы" in s
                  for s in строки_кр), str(строки_кр))
        check("вывод: замер по не-originality гейту не выдумывается",
              measure_lines({"measure": None}) == []
              and measure_lines({}) == [], "")
    else:
        check("сквозное с настоящим originality-check", False,
              f"инструмент не найден: {настоящий}")

    # ── 20. ГЕЙТ cta: маршрут CTA собранной страницы (по решению автора) ────────────
    # Позитив уже прогнан выше (стадия page в п.2 идёт по FX_PAGE с инвайтом,
    # шарингом и каналом автора). Здесь - что гейт стоит в стадии, что он
    # РЕАЛЬНО исполняется, и по одному негативу на каждую ось.
    fx_cta = _fixture(os.path.join(root, "cta-pos"))
    call(fx_cta, fx_cta["slug"], "--stage", "page")
    d_cta = json.load(open(os.path.join(fx_cta["dir"], "gates.json"), encoding="utf-8"))
    g_cta = [g for g in d_cta["stages"]["page"]["gates"] if g["name"] == "cta"]
    check("cta: гейт стоит в стадии page и реально исполнился (не SKIP)",
          len(g_cta) == 1 and g_cta[0]["status"] == "PASS", str(g_cta[:1]))
    check("cta: правильная страница проходит - шаринг и канал автора нарушением "
          "не считаются", "OK." in (g_cta[0]["out"] if g_cta else ""),
          (g_cta[0]["out"] if g_cta else "")[-200:])
    check("cta: в выводе видно, ЧЕМ мерили (инвайт слага из карты)",
          FX_INVITE in (g_cta[0]["out"] if g_cta else ""),
          (g_cta[0]["out"] if g_cta else "")[:300])

    def _cta_прогон(имя, page, cta_ready=True, slug_dir=None):
        f = _fixture(os.path.join(root, имя), page=page, cta_ready=cta_ready)
        adir = f["dir"] if slug_dir is None else slug_dir
        rc, lines = cta_run(adir, config_path=f["lm_config"])
        return rc, "\n".join(lines), f

    rc_lit, out_lit, _ = _cta_прогон(
        "cta-literal", _fx_page(f'<p>Ссылка старого маршрута {FX_LITERALS[0]} '
                                f'осталась в тексте</p>'))
    check("cta негатив: запрещённый литерал на странице = FAIL",
          rc_lit == 1 and "запрещённый литерал" in out_lit and FX_LITERALS[0] in out_lit,
          out_lit[-300:])
    rc_bot, out_bot, _ = _cta_прогон(
        "cta-bot", _fx_page(f'<p><a href="https://t.me/{FX_LITERALS[1]}?start=x">'
                            f'бот</a></p>'))
    check("cta негатив: второй литерал (чужой бот воронки) = FAIL",
          rc_bot == 1 and FX_LITERALS[1] in out_bot, out_bot[-300:])

    rc_чуж, out_чуж, _ = _cta_прогон(
        "cta-chuzhoy", _fx_page(cta_html='<p><a class="btn-cta" '
                                         'href="https://t.me/+CHUZHOYinvite00001">Забрать</a></p>'))
    check("cta негатив: CTA ведёт на ЧУЖОЙ именной инвайт = FAIL",
          rc_чуж == 1 and "не равна инвайту этой страницы" in out_чуж, out_чуж[-300:])

    rc_нет, out_нет, _ = _cta_прогон(
        "cta-net-cta", _fx_page(cta_html=f'<a class="share-btn" href="{FX_SHARE}">'
                                         f'Telegram</a>'))
    check("cta негатив: страницы без CTA-ссылки на инвайт (только шаринг) = FAIL",
          rc_нет == 1 and "нет ни одной CTA-ссылки" in out_нет, out_нет[-300:])

    rc_жарг, out_жарг, _ = _cta_прогон(
        "cta-jargon", _fx_page("<p>Это вечнозелёная смена в записи, тариф VIP 990 ₽</p>"))
    check("cta негатив: внутренний жаргон в видимом тексте = FAIL",
          rc_жарг == 1 and "жаргон" in out_жарг, out_жарг[-300:])
    rc_е, out_е, _ = _cta_прогон(
        "cta-jargon-e", _fx_page("<p>Это вечнозеленая смена, доступ сразу</p>"))
    check("cta негатив: жаргон в написании без «ё» тоже красный",
          rc_е == 1 and "вечнозелен" in out_е, out_е[-300:])

    # ── С1: два уровня жаргона (по решению автора) ───────────────────────────────────
    # Уровень страницы - новые формы о продукте, добавленные §4.6 закона
    rc_ai, out_ai, _ = _cta_прогон(
        "cta-jargon-allinc", _fx_page("<p>Формат All Inclusive для новых участников</p>"))
    check("cta негатив (уровень страницы): «All Inclusive» = FAIL",
          rc_ai == 1 and "All Inclusive" in out_ai, out_ai[-300:])
    rc_жм, out_жм, _ = _cta_прогон(
        "cta-jargon-live-event", _fx_page("<p>Это живое мероприятие для узкого круга</p>"))
    check("cta негатив (уровень страницы): «Живое мероприятие» = FAIL",
          rc_жм == 1 and "живое мероприятие" in out_жм.lower(), out_жм[-300:])

    # Уровень CTA-блока - служебные слова конвейера ЛЕГАЛЬНЫ в теле статьи,
    # но выдают внутреннюю кухню, если попали в сам призыв к действию
    cta_l2_html = (f'<section class="cta cta-final"><p><a class="btn-cta" '
                  f'href="{FX_INVITE}">Забрать оффер по спеццене</a></p>'
                  f'<p>Это специальный тариф для новых участников</p></section>')
    rc_l2, out_l2, _ = _cta_прогон("cta-jargon-block", _fx_page(cta_html=cta_l2_html))
    check("cta негатив (уровень CTA-блока): «оффер»/«тариф» ВНУТРИ блока cta-final = FAIL",
          rc_l2 == 1 and "ВНУТРИ CTA-блока" in out_l2 and "«оффер»" in out_l2,
          out_l2[-300:])
    rc_l2b, out_l2b, _ = _cta_прогон(
        "cta-jargon-block-voronka",
        _fx_page(cta_html=f'<div class="cta-inline"><p><a class="btn-cta" '
                          f'href="{FX_INVITE}">В воронку продукта</a></p></div>'))
    check("cta негатив (уровень CTA-блока): «воронк» ловится и в cta-inline "
          "(стем ловит падежи)",
          rc_l2b == 1 and "«воронк»" in out_l2b, out_l2b[-300:])

    # ── О1: обход словоформ жаргона, скептик раунд-2 (по решению автора) - те же три
    # формулировки, но на СОБРАННОЙ странице (не в черновике)
    rc_дефис, out_дефис, _ = _cta_прогон(
        "cta-jargon-o1-defis",
        _fx_page("<p>Онлайн-смена в записи начинается по будням.</p>"))
    check("cta негатив (О1): «Онлайн-смена в записи» (дефис вместо пробела) = FAIL",
          rc_дефис == 1 and "жаргон" in out_дефис, out_дефис[-300:])
    rc_cena, out_cena, _ = _cta_прогон(
        "cta-jargon-o1-price",
        _fx_page("<p>Тариф VIP 1990 включает разбор домашних заданий.</p>"))
    check("cta негатив (О1): «VIP 1990» (другая цена) = FAIL",
          rc_cena == 1 and "жаргон" in out_cena, out_cena[-300:])
    rc_dostup, out_dostup, _ = _cta_прогон(
        "cta-jargon-o1-dostup",
        _fx_page("<p>Доступ в записи открывается сразу после оплаты.</p>"))
    check("cta негатив (О1): «Доступ в записи» = FAIL",
          rc_dostup == 1 and "жаргон" in out_dostup, out_dostup[-300:])
    rc_vk, out_vk, _ = _cta_прогон(
        "cta-jargon-o1-vk-ok",
        _fx_page("<p>ВКонтакте показывает 10 медиа в записи одним альбомом.</p>"))
    check("cta позитив (О1): «10 медиа в записи» (ВКонтакте) НЕ жаргон, гейт зелёный",
          rc_vk == 0 and "OK." in out_vk, out_vk[-300:])

    # Позитив: те же слова В ТЕЛЕ статьи (вне CTA-блока) - легальны, гейт зелёный
    rc_тело, out_тело, _ = _cta_прогон(
        "cta-jargon-body-ok",
        _fx_page("<p>Сравнение тарифов Kling: Standard дешевле Pro, но качество "
                 "ниже. Разбор оффера сервиса - в отдельном разделе ниже.</p>"))
    check("cta позитив: «тарифы Kling»/«оффер» в ТЕЛЕ статьи (вне CTA-блока) "
          "гейт не валит",
          rc_тело == 0 and "OK." in out_тело
          and "ВНУТРИ CTA-блока" not in out_тело, out_тело[-300:])

    # MEDIUM-1: блока код-слова на странице нет ВООБЩЕ (решение владельца
    # по решению автора). Раньше здесь стоял позитивный тест «канонная формула
    # проходит» - теперь ровно та же формула обязана падать: читатель приходит
    # из поиска, слова он не знает, а вход открывает кнопка
    for фраза in CTA_BANNED_PHRASES:
        rc_ф, out_ф, _ = _cta_прогон(
            "cta-phrase-" + str(abs(hash(фраза)) % 10000),
            _fx_page(f'<p>Код-слово этой статьи - <span class="kw">СЛОВО</span>. '
                     f'{фраза.capitalize()} в продукт</p>'))
        check(f"cta негатив: фраза старого маршрута «{фраза}» = FAIL",
              rc_ф == 1 and ("фраза старого маршрута" in out_ф
                             or "блок код-слова" in out_ф), out_ф[-300:])
    rc_кс, out_кс, _ = _cta_прогон(
        "cta-codeword-block",
        _fx_page('<p>Код-слово этой статьи - <span class="kw">СЛОВО</span>. Если ты '
                 'пришёл по нему - ты на месте: вход открывает кнопка выше</p>'))
    check("cta негатив: БЫВШАЯ канонная формула код-слова теперь = FAIL",
          rc_кс == 1 and "блок код-слова" in out_кс, out_кс[-300:])
    rc_хв, out_хв, _ = _cta_прогон(
        "cta-codeword-tail",
        _fx_page('<p>Показываю кухню вживую вместе с прогонами, вход по слову '
                 'НАДЗОР</p>'))
    check("cta негатив: код-слово хвостом в живом предложении = FAIL",
          rc_хв == 1 and "код-слов" in out_хв, out_хв[-300:])
    rc_чист, out_чист, _ = _cta_прогон(
        "cta-codeword-clean",
        _fx_page('<p>Искать в файле можно по слову или по фразе, разницы нет</p>'))
    check("cta позитив: живая речь «по слову» без капса гейт не валит",
          rc_чист == 0, out_чист[-300:])

    # LOW-3: формы литерала - без хвостового слеша и url-encoded
    путь_лит = FX_LITERALS[0]
    for форма in article_build.forbidden_forms(путь_лит)[1:]:
        rc_ф, out_ф, _ = _cta_прогон(
            "cta-form-" + str(abs(hash(форма)) % 10000),
            _fx_page(f'<p>Хвост маршрута {форма} в теле страницы</p>'))
        check(f"cta негатив: форма литерала «{форма}» = FAIL",
              rc_ф == 1 and "запрещённый литерал" in out_ф, out_ф[-300:])
    rc_як, out_як, _ = _cta_прогон(
        "cta-anchor-ok",
        _fx_page(f'<h2 id="{путь_лит.strip("/")}">Заголовок с якорем</h2>'))
    check("cta позитив: якорь id=«имя» без слеша ложной тревоги не даёт",
          rc_як == 0, out_як[-300:])

    f_нослага = _fixture(os.path.join(root, "cta-no-slug"))
    чужой_каталог = os.path.join(os.path.dirname(f_нослага["dir"]), "guide-sosed")
    shutil.copyfile(os.path.join(f_нослага["dir"], "index.html"),
                    os.path.join(чужой_каталог, "index.html"))
    rc_слаг, стр_слаг = cta_run(чужой_каталог, config_path=f_нослага["lm_config"])
    check("cta негатив: слага нет в карте инвайтов = FAIL, а не тихий пропуск",
          rc_слаг == 1 and "вне карты инвайтов" in "\n".join(стр_слаг),
          "\n".join(стр_слаг)[-300:])

    f_пусто = _fixture(os.path.join(root, "cta-empty-cfg"), cta_ready=True)
    with open(f_пусто["lm_config"], "w", encoding="utf-8") as fh:
        fh.write("```yaml\ndomain: fx.test\ntarget_url: https://fx.test/offer/\n```\n")
    rc_пусто, стр_пусто = cta_run(f_пусто["dir"], config_path=f_пусто["lm_config"])
    check("cta: пустая секция cta в конфиге = ГРОМКОЕ «ничего не проверил» (rc 3 = "
          "WARN), а не зелёный PASS",
          rc_пусто == 3 and "ГЕЙТ НИЧЕГО НЕ ПРОВЕРИЛ" in "\n".join(стр_пусто),
          "\n".join(стр_пусто)[-200:])
    # тот же случай, но РЕАЛЬНОЙ стадией: словарь RC_CTA сам по себе ничего не
    # доказывает - смотрим статус гейта в отчёте и вердикт стадии целиком
    rc_ст = call(f_пусто, f_пусто["slug"], "--stage", "page")
    d_пусто = json.load(open(os.path.join(f_пусто["dir"], "gates.json"), encoding="utf-8"))
    g_пусто = {g["name"]: g for g in d_пусто["stages"]["page"]["gates"]}
    check("cta: rc 3 в РЕАЛЬНОЙ стадии = статус WARN у гейта, вердикт стадии PASS, "
          "код выхода 0",
          rc_ст == 0 and g_пусто["cta"]["status"] == "WARN"
          and d_пусто["stages"]["page"]["verdict"] == "PASS",
          f"rc={rc_ст} status={g_пусто['cta']['status']} "
          f"verdict={d_пусто['stages']['page']['verdict']}")
    check("cta: «ничего не проверил» видно в расписке gates.json, а не только в консоли",
          "ГЕЙТ НИЧЕГО НЕ ПРОВЕРИЛ" in g_пусто["cta"]["out"], g_пусто["cta"]["out"][-160:])

    f_безкарты = _fixture(os.path.join(root, "cta-no-map"), cta_ready=False)
    rc_бк, стр_бк = cta_run(f_безкарты["dir"], config_path=f_безкарты["lm_config"])
    check("cta: без карты инвайтов (машина ученика) гейт зелёный, но ГОВОРИТ, что "
          "сверку адреса не делал",
          rc_бк == 0 and "НЕ проводил" in "\n".join(стр_бк), "\n".join(стр_бк)[-200:])

    check("cta: жаргон ищется в ВИДИМОМ тексте (скрипты и стили не считаются)",
          cta_visible_text("<script>var x='вечнозелён';</script><p>чистый текст</p>")
          .strip() == "чистый текст",
          repr(cta_visible_text("<script>var x='вечнозелён';</script><p>чистый текст</p>")))

    check("cta_block_texts: ловит cta-mid/cta-final/cta-inline/btn-cta/nav-drop-cta "
          "по маркеру класса, обычный <div> без класса cta - мимо",
          cta_block_texts(
              '<aside class="cta cta-mid"><p>А</p></aside>'
              '<section class="cta cta-final"><p>Б</p></section>'
              '<div class="cta-inline"><p>В</p></div>'
              '<a class="btn-cta" href="#">Г</a>'
              '<a class="nav-drop-cta" href="#">Д</a>'
              '<div class="prose"><p>вне CTA, мимо</p></div>')
          == ["А", "Б", "В", "Г", "Д"],
          str(cta_block_texts(
              '<aside class="cta cta-mid"><p>А</p></aside>'
              '<section class="cta cta-final"><p>Б</p></section>'
              '<div class="cta-inline"><p>В</p></div>'
              '<a class="btn-cta" href="#">Г</a>'
              '<a class="nav-drop-cta" href="#">Д</a>'
              '<div class="prose"><p>вне CTA, мимо</p></div>')))

    # ── 21. ГЕЙТ assets-exist: локальные ассеты собранной страницы физически
    # на диске (р9-по решению автора, дыра скептика волны р9 - guide-ii-perevodchik
    # ссылался на 3 несуществующих assets/thumb-*.webp при полностью зелёных
    # гейтах, ни один их не ловил) ────────────────────────────────────────────
    def _страница_ассеты(теги):
        return f"<html><head><title>t</title></head><body>{теги}</body></html>"

    # ПОЗИТИВ: img+source+srcset+preload-картинка, все файлы физически на
    # месте, плюс абсолютный http(s)/корневой путь/preload-шрифт рядом - они
    # НЕ должны требовать файла на диске (иначе гейт душил бы общесайтовые
    # ресурсы вроде шрифтов и фавикона)
    ax_pos = os.path.join(root, "assets-pos")
    os.makedirs(os.path.join(ax_pos, "assets"), exist_ok=True)
    for имя in ("hero.jpg", "hero.webp", "thumb-a.webp"):
        open(os.path.join(ax_pos, "assets", имя), "w").close()
    with open(os.path.join(ax_pos, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_страница_ассеты(
            '<link rel="preload" as="image" href="assets/thumb-a.webp">'
            '<link rel="preload" href="/assets/fonts/x.woff2" as="font">'
            '<picture><source srcset="assets/hero.webp" type="image/webp">'
            '<img src="assets/hero.jpg" srcset="assets/hero.webp 1x"></picture>'
            '<img src="https://cdn.example.com/x.jpg">'
            '<img src="/favicon.png">'))
    rc_ax_pos, вых_ax_pos = assets_exist_run(ax_pos)
    check("assets-exist ПОЗИТИВ: все локальные ассеты (img/source src+srcset, "
          "href preload-картинки) физически на диске -> PASS, rc=0",
          rc_ax_pos == 0 and "OK." in "\n".join(вых_ax_pos), "\n".join(вых_ax_pos))
    check("assets-exist ПОЗИТИВ: абсолютный http(s)-URL, корневой путь и "
          "preload-шрифт НЕ считаются локальными ссылками каталога статьи",
          "cdn.example.com" not in "\n".join(вых_ax_pos)
          and "favicon.png" not in "\n".join(вых_ax_pos)
          and "fonts/x.woff2" not in "\n".join(вых_ax_pos), "\n".join(вых_ax_pos))

    # НЕГАТИВ: один путь физически отсутствует - живой дефект guide-ii-perevodchik
    # (assets/thumb-*.webp в разметке, файла на диске нет). Тот же путь дан ДВАЖДЫ
    # (source srcset + img src) - дубль обязан схлопнуться в ОДНО замечание
    ax_neg = os.path.join(root, "assets-neg")
    os.makedirs(os.path.join(ax_neg, "assets"), exist_ok=True)
    open(os.path.join(ax_neg, "assets", "hero.jpg"), "w").close()
    with open(os.path.join(ax_neg, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_страница_ассеты(
            '<img src="assets/hero.jpg">'
            '<picture><source srcset="assets/thumb-nikogda-ne-bylo.webp" '
            'type="image/webp">'
            '<img class="rc-thumb" src="assets/thumb-nikogda-ne-bylo.webp"></picture>'))
    rc_ax_neg, вых_ax_neg = assets_exist_run(ax_neg)
    check("assets-exist НЕГАТИВ: отсутствующий на диске assets/thumb-*.webp роняет "
          "гейт в FAIL с ПОИМЁННЫМ указанием файла",
          rc_ax_neg == 1 and "thumb-nikogda-ne-bylo.webp" in "\n".join(вых_ax_neg),
          "\n".join(вых_ax_neg))
    бэд_строки = [l for l in вых_ax_neg if l.strip().startswith("!")]
    check("assets-exist НЕГАТИВ: дубль одного пропавшего пути (source srcset + img "
          "src на тот же файл) даёт РОВНО одно замечание, не два",
          len(бэд_строки) == 1, "\n".join(вых_ax_neg))

    # ОШИБКА ВХОДА: нет собранной страницы вовсе
    ax_нет = os.path.join(root, "assets-net-page")
    os.makedirs(ax_нет, exist_ok=True)
    rc_ax_нет, вых_ax_нет = assets_exist_run(ax_нет)
    check("assets-exist: нет index.html - гейт не выдумывает вердикт, rc=3",
          rc_ax_нет == 3, "\n".join(вых_ax_нет))

    # ── 21б. ГЕЙТ image-refs: БИТАЯ КАРТИНКА (инцидент по решению автора - владелец
    # открыл свою статью из поиска и увидел битый хиро; 43 битые ссылки на двух
    # страницах живого корпуса при полностью зелёном assets-exist) ─────────────
    ирс_слаг = "guide-primer"

    def _папка_картинок(имя, тело, файлы=("hero.jpg", "hero.webp", "hero-720.webp")):
        d = os.path.join(root, имя)
        os.makedirs(os.path.join(d, "assets"), exist_ok=True)
        for f in файлы:
            open(os.path.join(d, "assets", f), "w").close()
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(_страница_ассеты(тело))
        return d

    # ПОЗИТИВ (каталожная раскладка - так собирает конвейер): весь комплект
    # <picture> относительный, рядом общесайтовые ресурсы, которым статья не
    # судья (превьюшка соседа /assets/thumbs/…, фавикон, внешний CDN, шрифт)
    ир_pos = _папка_картинок(
        "imgrefs-pos",
        '<link rel="preload" as="image" href="assets/hero.webp">'
        '<link rel="preload" href="/assets/fonts/x.woff2" as="font">'
        '<picture><source type="image/webp" srcset="assets/hero-720.webp 720w, '
        'assets/hero.webp 1200w"><img src="assets/hero.jpg"></picture>'
        '<img src="/assets/thumbs/guide-sosed-thumb.webp">'
        '<img src="https://cdn.example.com/x.jpg">'
        '<img src="data:image/gif;base64,R0lGOD">')
    rc_ир_pos, вых_ир_pos = image_refs_run(ир_pos, slug=ирс_слаг)
    check("image-refs ПОЗИТИВ: каталожная раскладка, весь комплект <picture> "
          "относительный -> PASS, rc=0",
          rc_ир_pos == 0 and "OK." in "\n".join(вых_ир_pos), "\n".join(вых_ир_pos))
    check("image-refs ПОЗИТИВ: общесайтовый /assets/thumbs/, внешний CDN, data: "
          "и preload-шрифт НЕ считаются ассетами статьи",
          "своих ассетов статьи 4" in "\n".join(вых_ир_pos), "\n".join(вых_ир_pos))

    # 🔴 НЕГАТИВ-1, ГЛАВНЫЙ: СМЕШАННАЯ РАСКЛАДКА ВНУТРИ ОДНОГО <picture> -
    # дословный вид дефекта с прода (source[srcset] относительный, img[src]
    # корневой). Промах <source> не откатывается на <img>: кадр битый при
    # живом jpeg-фолбэке
    ир_mix = _папка_картинок(
        "imgrefs-mixed",
        f'<picture><source type="image/webp" srcset="assets/{ирс_слаг}/hero-720.webp '
        f'720w, assets/{ирс_слаг}/hero.webp 1200w">'
        f'<img src="/assets/{ирс_слаг}/hero.jpg"></picture>')
    rc_ир_mix, вых_ир_mix = image_refs_run(ир_mix, slug=ирс_слаг)
    т_mix = "\n".join(вых_ир_mix)
    check("image-refs НЕГАТИВ: смешанная раскладка внутри одного <picture> "
          "роняет гейт в FAIL (rc=1), а не в WARN",
          rc_ир_mix == 1 and RC_IMGREF[1] == "FAIL", т_mix)
    check("image-refs НЕГАТИВ: замечание НАЗЫВАЕТ комплект <picture> и объясняет, "
          "почему фолбэк не спасает",
          "СМЕШАННАЯ РАСКЛАДКА" in т_mix and "<picture> №1" in т_mix
          and "НЕ откатывается" in т_mix, т_mix)
    check("image-refs НЕГАТИВ: поимённо назван относительный путь плоской формы "
          "и дана ВЕРНАЯ форма с ведущим слэшем",
          f"! assets/{ирс_слаг}/hero-720.webp" in т_mix
          and f"Верная форма: /assets/{ирс_слаг}/hero-720.webp" in т_mix, т_mix)
    check("image-refs НЕГАТИВ: жёсткие строки уезжают в flags отчёта "
          "(префикс '!' из HARD_PREFIX)",
          any(l.strip().startswith("!") for l in вых_ир_mix), т_mix)

    # 🔴 ЗАЛИВКА «ТОЛЬКО СТРАНИЦА»: своя КОРНЕВАЯ ссылка без локального файла.
    # Круг 2 (по решению автора): это НЕ вердикт стадии page - файл может уже лежать на
    # проде или ехать из другого каталога. Ложный FAIL мерялся живьём: три
    # deploy-каталога, 31 корневая ссылка, локально 0 файлов, 27 проверенных
    # адресов отдают на проде 200. Гейт обязан пропустить и НАЗВАТЬ цифру
    ир_root = _папка_картинок(
        "imgrefs-root-no-file",
        f'<img src="/assets/{ирс_слаг}/na-prode-uzhe-lezhit.webp">', файлы=())
    rc_ир_root, вых_ир_root = image_refs_run(ир_root, slug=ирс_слаг)
    т_root = "\n".join(вых_ир_root)
    check("image-refs ЗАЛИВКА ТОЛЬКО СТРАНИЦЫ: своя корневая ссылка без "
          "локального файла - PASS (rc=0), а не ложный FAIL",
          rc_ир_root == 0, т_root)
    check("image-refs: цифра «корневых без файла» всё равно НАЗВАНА и назван "
          "хозяин проверки (assets-exist / предполёт заливки)",
          "из них без локального файла 1" in т_root
          and "предполёт ftp_publish" in т_root, т_root)
    # ...а вызывающий, у которого весь набор заливки на руках, включает проверку
    # флагом и получает поимённый FAIL - способность не потеряна, а передана
    rc_ир_root_req, вых_ир_root_req = image_refs_run(ир_root, slug=ирс_слаг,
                                                     require_files=True)
    check("image-refs: require_files=True возвращает поимённый FAIL по корневой "
          "ссылке без файла (для вызова, который держит весь набор заливки)",
          rc_ир_root_req == 1
          and "na-prode-uzhe-lezhit.webp" in "\n".join(вых_ир_root_req),
          "\n".join(вых_ир_root_req))
    rc_ax_root, _ = assets_exist_run(ир_root)
    check("image-refs: контракт соседа не тронут - assets-exist на корневой "
          "ссылке по-прежнему PASS (он судит только относительные)",
          rc_ax_root == 0, f"assets-exist rc={rc_ax_root}")

    # НЕГАТИВ-3: раскладка прогона объявлена ЯВНО (--page-layout flat), а
    # страница собрана каталожно - на проде картинок не будет ни одной
    ир_decl = _папка_картинок(
        "imgrefs-declared-flat",
        '<picture><source srcset="assets/hero.webp"><img src="assets/hero.jpg"></picture>')
    rc_ир_decl, вых_ир_decl = image_refs_run(ир_decl, slug=ирс_слаг, layout="flat")
    check("image-refs НЕГАТИВ: объявлена плоская раскладка, а ссылки каталожные "
          "-> FAIL с поимённым перечнем",
          rc_ир_decl == 1 and "объявлен раскладкой flat" in "\n".join(вых_ир_decl),
          "\n".join(вых_ир_decl))
    # ...и та же страница при каталожной раскладке (как её и собирают) - PASS
    rc_ир_decl_ok, _ = image_refs_run(ир_decl, slug=ирс_слаг, layout="dir")
    check("image-refs: та же страница при объявленной каталожной раскладке - PASS "
          "(гейт судит СООТВЕТСТВИЕ раскладке, а не форму пути саму по себе)",
          rc_ир_decl_ok == 0, f"rc={rc_ир_decl_ok}")

    # ПОЗИТИВ-2: ЧЕСТНАЯ плоская раскладка - все свои ссылки корневые, файлы на
    # месте. Гейт обязан пропустить: битая не «корневая ссылка», а РАССОГЛАСОВАНИЕ
    ир_flat = _папка_картинок(
        "imgrefs-flat-ok",
        f'<picture><source type="image/webp" srcset="/assets/{ирс_слаг}/hero.webp">'
        f'<img src="/assets/{ирс_слаг}/hero.jpg"></picture>')
    rc_ир_flat, вых_ир_flat = image_refs_run(ир_flat, slug=ирс_слаг, layout="flat")
    check("image-refs ПОЗИТИВ: честная плоская раскладка (все свои ссылки "
          "корневые, файлы на месте) - PASS, гейт не запрещает корневые пути",
          rc_ир_flat == 0, "\n".join(вых_ир_flat))

    # ОШИБКИ ВХОДА: нет страницы · неизвестная раскладка
    ир_нет = os.path.join(root, "imgrefs-net-page")
    os.makedirs(ир_нет, exist_ok=True)
    rc_ир_нет, вых_ир_нет = image_refs_run(ир_нет, slug=ирс_слаг)
    check("image-refs: нет index.html - гейт не выдумывает вердикт, rc=3 (ERROR)",
          rc_ир_нет == 3 and RC_IMGREF[3] == "ERROR", "\n".join(вых_ир_нет))
    rc_ир_bad, _ = image_refs_run(ир_pos, slug=ирс_слаг, layout="ploskaya")
    check("image-refs: неизвестная раскладка на входе - rc=2 (ERROR), не тихий PASS",
          rc_ир_bad == 2 and RC_IMGREF[2] == "ERROR", f"rc={rc_ир_bad}")

    # 🔴 НЕГАТИВ-4, ПУСТОЙ АТРИБУТ (круг 3, по решению автора). `<img src="">` - битая
    # картинка, видимая читателю без всякой раскладки: браузер запрашивает саму
    # страницу как изображение. Оба гейта стадии page выбрасывали пустое
    # значение фильтром `if u:` и печатали OK, тогда как соседний чекер тот же
    # случай называл классом empty-ref и ронял exit 1. Разбор один, вердикт
    # разошёлся. Улика находки: живой файл конвейера с `<img src="" alt="автор
    #">` - gate rc=0 при image_health exit=1; таких страниц по дереву 30
    ир_empty = _папка_картинок(
        "imgrefs-empty-attr",
        '<picture><img src="" alt="hero"></picture>'
        '<img src="assets/hero.jpg" alt="живая">')
    rc_ир_empty, вых_ир_empty = image_refs_run(ир_empty, slug=ирс_слаг)
    т_empty = "\n".join(вых_ир_empty)
    check("image-refs НЕГАТИВ: пустой <img src=\"\"> роняет гейт в FAIL (rc=1), "
          "а не выбрасывается из разбора с вердиктом OK",
          rc_ир_empty == 1 and RC_IMGREF[1] == "FAIL", т_empty)
    check("image-refs НЕГАТИВ: улика поимённая - назван тег, атрибут и что "
          "именно сделает браузер",
          "! img[src]" in т_empty and "ПУСТОЙ атрибут" in т_empty
          and "запросит саму страницу" in т_empty, т_empty)
    check("image-refs НЕГАТИВ: жёсткая строка уезжает в flags отчёта (префикс '!')",
          any(l.strip().startswith("!") and "ПУСТОЙ" in l for l in вых_ир_empty),
          т_empty)
    check("image-refs: пустой атрибут посчитан в шапке отчёта отдельной цифрой",
          "ПУСТЫХ атрибутов: 1" in т_empty, т_empty)
    # сосед по стадии обязан сойтись в вердикте: тот же случай, тот же FAIL
    rc_ax_empty, вых_ax_empty = assets_exist_run(ир_empty)
    check("assets-exist НЕГАТИВ: тот же пустой атрибут - тоже FAIL (rc=1), "
          "а не «ссылки нет» с вердиктом OK",
          rc_ax_empty == 1 and "ПУСТОЙ атрибут" in "\n".join(вых_ax_empty),
          "\n".join(вых_ax_empty))
    # и разошедшийся вердикт с чекером закрыт: оба судят пустое одинаково
    check("вердикт сошёлся с чекером: у image_health тот же случай = класс "
          "empty-ref (один разбор - один приговор)",
          IH is not None and getattr(IH, "D_EMPTY", None) == "empty-ref"
          and bool(IH.ref_kind_of_raw("")[0] == IH.D_EMPTY),
          str(IH.ref_kind_of_raw("")) if IH else "IH=None")
    # ПОЗИТИВ-рядом: непустая страница цифру «пустых» не печатает и остаётся PASS
    check("image-refs ПОЗИТИВ: на странице без пустых атрибутов цифра не "
          "печатается вовсе (шум не растёт)",
          "ПУСТЫХ атрибутов" not in "\n".join(вых_ир_pos), "\n".join(вых_ир_pos))

    # 🔴 НЕГАТИВ-5, ЛАЙТБОКС И PRELOAD В ОХВАТЕ (круг 3, по решению автора). Оба класса
    # ссылок теперь собирает чекер, значит их видит и гейт: битый href лайтбокса
    # ловил раньше только живой читатель кликом
    ир_zoom = _папка_картинок(
        "imgrefs-zoom-preload",
        f'<link rel="preload" as="image" href="assets/{ирс_слаг}/hero.webp">'
        f'<figure class="fig"><a class="zoom" href="assets/{ирс_слаг}/hero.jpg">'
        f'<img src="assets/hero.jpg"></a></figure>'
        f'<p><a href="/guide-sosed/">обычная ссылка</a></p>')
    rc_ир_zoom, вых_ир_zoom = image_refs_run(ир_zoom, slug=ирс_слаг)
    т_zoom = "\n".join(вых_ир_zoom)
    check("image-refs НЕГАТИВ: href лайтбокса написан плоской формой, но оставлен "
          "относительным -> FAIL, поимённо",
          rc_ир_zoom == 1 and f"! assets/{ирс_слаг}/hero.jpg" in т_zoom, т_zoom)
    check("image-refs: preload-хиро в той же плоской форме тоже назван",
          f"! assets/{ирс_слаг}/hero.webp" in т_zoom, т_zoom)
    check("image-refs: обычная навигационная ссылка <a href> картинкой НЕ "
          "считается (отбор по расширению файла, не по классу вёрстки)",
          "/guide-sosed/" not in т_zoom, т_zoom)
    check("разбор: preload собран РОВНО один раз (подкласс больше не дублирует "
          "то, что теперь собирает сам чекер)",
          len([1 for u, _t, _a, _p in imgref_parse_page(
              '<link rel="preload" as="image" href="assets/hero.webp">')
              if u == "assets/hero.webp"]) == 1,
          str(imgref_parse_page(
              '<link rel="preload" as="image" href="assets/hero.webp">')))

    # ── 21в. РАЗБОР СТРАНИЦЫ: пять дыр регулярок, закрытых переходом на парсер
    # image_health.py (круг 2, по решению автора). Каждая проверка = одна находка
    # скептика, воспроизведённая ДОСЛОВНО на старом коде ────────────────────────
    check("разбор: источник разбора НАЗВАН путём, а не обещанием "
          "(один источник истины - парсер image_health.py)",
          IMGREF_PARSER_PATH and IMGREF_PARSER_PATH.endswith("image_health.py")
          and "image_health.py" in imgref_parser_note(), imgref_parser_note())

    def _url(html_кусок):
        return [u for u, _, _, _ in imgref_page_refs(html_кусок)]

    # НАХОДКА 1: '>' внутри значения атрибута. Старая регулярка обрывала тег на
    # первом '>' и теряла src целиком - страница давала 0 ссылок и вердикт OK
    гт = '<img alt="меню Файл > Открыть" src="assets/hero.webp">'
    check("разбор Н1: '>' внутри alt НЕ обрывает тег - src виден "
          "(на старой регулярке страница давала ноль ссылок и OK)",
          _url(гт) == ["assets/hero.webp"], repr(_url(гт)))
    # ...и главное: за этим обрывом пряталась НАСТОЯЩАЯ смешанная раскладка
    ир_alt = _папка_картинок(
        "imgrefs-alt-gt",
        f'<picture><source srcset="assets/hero-720.webp 720w">'
        f'<img alt="скрин: Файл > Сохранить как" src="/assets/{ирс_слаг}/hero.jpg">'
        f'</picture>')
    rc_ир_alt, вых_ир_alt = image_refs_run(ир_alt, slug=ирс_слаг)
    check("разбор Н1: смешанная раскладка, спрятанная за '>' в alt, теперь "
          "ловится в FAIL (это и был ложный зелёный)",
          rc_ир_alt == 1 and "СМЕШАННАЯ РАСКЛАДКА" in "\n".join(вых_ир_alt),
          "\n".join(вых_ир_alt))

    # НАХОДКА 2: data-src / порядок атрибутов / значение без кавычек
    check("разбор Н2: data-src НЕ подменяет src (регулярка \\bsrc= матчила "
          "дефисный префикс и судила плейсхолдер)",
          _url('<img data-src="assets/lenivy.gif" src="assets/nastoyashiy.webp">')
          == ["assets/nastoyashiy.webp"],
          repr(_url('<img data-src="assets/lenivy.gif" src="assets/nastoyashiy.webp">')))
    check("разбор Н2: data-srcset НЕ подменяет srcset",
          _url('<source data-srcset="assets/lenivy.gif 1w" '
               'srcset="assets/nastoyashiy.webp 720w">') == ["assets/nastoyashiy.webp"],
          repr(_url('<source data-srcset="assets/lenivy.gif 1w" '
                    'srcset="assets/nastoyashiy.webp 720w">')))
    check("разбор Н2: значение атрибута БЕЗ кавычек видно (старая регулярка "
          "требовала кавычки и не видела ссылку вовсе)",
          _url("<img src=assets/hero.webp>") == ["assets/hero.webp"],
          repr(_url("<img src=assets/hero.webp>")))
    check("разбор Н2: у одного тега берутся ОБА атрибута, а не первое "
          "совпадение регулярки",
          _url('<img srcset="assets/hero-720.webp 720w" src="assets/hero.jpg">')
          == ["assets/hero.jpg", "assets/hero-720.webp"],
          repr(_url('<img srcset="assets/hero-720.webp 720w" src="assets/hero.jpg">')))

    # НАХОДКА 4: srcset режется по алгоритму HTML, а не split(",")
    check("разбор Н4: data:-URI в srcset остаётся ОДНОЙ ссылкой "
          "(split(',') рвал его пополам и порождал фантом)",
          _url('<img srcset="data:image/svg+xml;base64,AAAB= 1x, assets/hero.webp 2x">')
          == ["data:image/svg+xml;base64,AAAB=", "assets/hero.webp"],
          repr(_url('<img srcset="data:image/svg+xml;base64,AAAB= 1x, '
                    'assets/hero.webp 2x">')))
    check("разбор Н4: подписанный CDN-адрес с запятой внутри не распадается "
          "на два фантома",
          _url('<img srcset="https://cdn.example.com/i/w_100,h_200/x.webp 1x">')
          == ["https://cdn.example.com/i/w_100,h_200/x.webp"],
          repr(_url('<img srcset="https://cdn.example.com/i/w_100,h_200/x.webp 1x">')))
    # ...и последствие фантома: ложная «смешанная раскладка» на здоровой странице
    ир_ds = _папка_картинок(
        "imgrefs-datauri-srcset",
        '<picture><source srcset="data:image/svg+xml;base64,AAAB= 1x, '
        'assets/hero-720.webp 720w"><img src="assets/hero.jpg"></picture>')
    rc_ир_ds, вых_ир_ds = image_refs_run(ир_ds, slug=ирс_слаг)
    check("разбор Н4: здоровая страница с data:-URI в srcset - PASS, без "
          "ложной смешанной раскладки",
          rc_ир_ds == 0, "\n".join(вых_ир_ds))

    # НАХОДКА 5: тег внутри HTML-комментария - не ссылка
    check("разбор Н5: <img> внутри HTML-комментария НЕ считается ссылкой",
          _url('<!-- <img src="/assets/prizrak/net.webp"> -->'
               '<img src="assets/hero.webp">') == ["assets/hero.webp"],
          repr(_url('<!-- <img src="/assets/prizrak/net.webp"> -->'
                    '<img src="assets/hero.webp">')))
    # ...и следствие: закомментированный черновой путь не роняет живую страницу
    ир_com = _папка_картинок(
        "imgrefs-comment",
        f'<!-- было: <img src="/assets/{ирс_слаг}/staryy.jpg"> -->'
        f'<picture><source srcset="assets/hero-720.webp 720w">'
        f'<img src="assets/hero.jpg"></picture>')
    rc_ир_com, вых_ир_com = image_refs_run(ир_com, slug=ирс_слаг)
    check("разбор Н5: закомментированный старый путь не даёт ложной "
          "расщеплённой раскладки - PASS",
          rc_ир_com == 0, "\n".join(вых_ир_com))

    # НАХОДКА 6: охват добран - video[poster] и url() в CSS
    check("разбор Н6: video[poster] попадает в охват (битый постер читатель "
          "видит так же, как битый <img>)",
          _url('<video poster="assets/poster.webp"></video>') == ["assets/poster.webp"],
          repr(_url('<video poster="assets/poster.webp"></video>')))
    check("разбор Н6: url() в атрибуте style= и в блоке <style> попадают в охват",
          _url('<div style="background:url(assets/fon.webp)"></div>'
               '<style>.h{background-image:url("assets/shapka.webp")}</style>')
          == ["assets/fon.webp", "assets/shapka.webp"],
          repr(_url('<div style="background:url(assets/fon.webp)"></div>'
                    '<style>.h{background-image:url("assets/shapka.webp")}</style>')))
    # ...и битый постер теперь роняет гейт, а не проезжает молча
    ир_pos6 = _папка_картинок(
        "imgrefs-poster-mixed",
        f'<picture><source srcset="assets/hero-720.webp 720w">'
        f'<img src="assets/hero.jpg"></picture>'
        f'<video poster="assets/{ирс_слаг}/poster.webp"></video>')
    rc_ир_pos6, вых_ир_pos6 = image_refs_run(ир_pos6, slug=ирс_слаг)
    check("разбор Н6: постер, написанный плоской формой относительным путём, "
          "роняет гейт (раньше он был вне охвата и проезжал молча)",
          rc_ир_pos6 == 1 and "poster.webp" in "\n".join(вых_ир_pos6),
          "\n".join(вых_ир_pos6))

    # ГРАНИЦА ОХВАТА: мета-картинки и фавиконки сознательно НЕ судятся
    check("разбор: og:image/twitter:image и link[rel=icon] вне охвата гейта "
          "статьи (их судят frame-provenance и сверка с продом)",
          _url('<meta property="og:image" content="/assets/og/x.jpg">'
               '<meta name="twitter:image" content="/assets/og/x.jpg">'
               '<link rel="icon" href="/favicon.svg">'
               '<img src="assets/hero.webp">') == ["assets/hero.webp"],
          repr(_url('<meta property="og:image" content="/assets/og/x.jpg">'
                    '<link rel="icon" href="/favicon.svg">'
                    '<img src="assets/hero.webp">')))
    check("разбор: link[rel=preload][as=image] в охвате, а preload шрифта - нет",
          _url('<link rel="preload" as="image" href="assets/hero.webp">'
               '<link rel="preload" as="font" href="/assets/fonts/x.woff2">')
          == ["assets/hero.webp"],
          repr(_url('<link rel="preload" as="image" href="assets/hero.webp">'
                    '<link rel="preload" as="font" href="/assets/fonts/x.woff2">')))

    # НЕТ ПАРСЕРА = ЧЕСТНЫЙ ERROR, а не молчаливый зелёный
    _сохр_класс, _сохр_ih = _IMGREF_CLASS, IH
    try:
        globals()["_IMGREF_CLASS"] = None
        globals()["IH"] = None
        rc_ир_нп, вых_ир_нп = image_refs_run(ир_pos, slug=ирс_слаг)
        rc_ax_нп, вых_ax_нп = assets_exist_run(ир_pos)
    finally:
        globals()["IH"] = _сохр_ih
        globals()["_IMGREF_CLASS"] = _сохр_класс
    check("разбор: image_health.py недоступен - image-refs отдаёт rc=3 (ERROR) "
          "с честной пометкой, а НЕ тихий PASS",
          rc_ир_нп == 3 and RC_IMGREF[3] == "ERROR"
          and "НЕЧЕМ" in "\n".join(вых_ир_нп), "\n".join(вых_ир_нп))
    check("разбор: та же деградация у assets-exist - rc=3, и article_gates при "
          "этом не падает (импорт мягкий)",
          rc_ax_нп == 3 and "НЕЧЕМ" in "\n".join(вых_ax_нп), "\n".join(вых_ax_нп))

    # ── гейт retract-sync: отозванная формулировка не живёт в файле-ИСТОЧНИКЕ
    # (r14 круг в даты запуска.2026; строку про «сеть США» сняли из статьи кругом
    # 11, а в research.md она простояла до круга 15 и однажды уже переезжала
    # обратно в текст) ─────────────────────────────────────────────────────────
    def _папка_отзыва(имя, research, log_lines):
        d = os.path.join(root, имя)
        os.makedirs(os.path.join(d, "terminal-outputs"), exist_ok=True)
        with open(os.path.join(d, "research.md"), "w", encoding="utf-8") as fh:
            fh.write(research)
        with open(os.path.join(d, "terminal-outputs", "01.log"), "w",
                  encoding="utf-8") as fh:
            fh.write(log_lines)
        return d

    рс_лог = ('--- зарубежная точка выхода: НЕ МЕРЯЛАСЬ ---\n'
              '# контракт описан строкой ОТОЗВАНО-ФРАЗА: «пример из комментария»\n'
              'ОТОЗВАНО-ФРАЗА: «Веб-фетчер Claude (сеть США)»\n')
    рс_neg = _папка_отзыва(
        "retract-neg",
        "| Точка проверки | Что вернулось |\n"
        "| Веб-фетчер Claude (сеть США) | connect ECONNREFUSED |\n", рс_лог)
    rc_рс_neg, вых_рс_neg = retract_sync_run(рс_neg)
    check("retract-sync НЕГАТИВ: отозванная формулировка живёт в research.md -> "
          "FAIL, rc=1, с именем файла лога, где объявлен отзыв",
          rc_рс_neg == 1 and "research.md" in "\n".join(вых_рс_neg)
          and "01.log" in "\n".join(вых_рс_neg), "\n".join(вых_рс_neg))
    check("retract-sync: строка-комментарий (#) в реестр отзывов НЕ идёт - иначе "
          "описание контракта само стало бы отозванной фразой",
          "пример из комментария" not in "\n".join(вых_рс_neg),
          "\n".join(вых_рс_neg))

    рс_pos = _папка_отзыва(
        "retract-pos",
        "| 🔴 ОТОЗВАНО КРУГОМ 15: строка «Веб-фетчер Claude (сеть США)» | "
        "замера с зарубежной точки не было |\n", рс_лог)
    rc_рс_pos, вых_рс_pos = retract_sync_run(рс_pos)
    check("retract-sync ПОЗИТИВ: та же формулировка ПОД пометкой отзыва - "
          "законная цитата, гейт молчит, rc=0",
          rc_рс_pos == 0, "\n".join(вых_рс_pos))

    рс_wrap = _папка_отзыва(
        "retract-wrap",
        "🔴 ОТОЗВАНО КРУГОМ 15. Тут стоял вывод: «в потребительском продукте\n"
        "на момент этой редакции официально живёт именно **3.1**». Так пишет справка.\n",
        'ОТОЗВАНО-ФРАЗА: «в потребительском продукте на момент этой редакции официально '
        'живёт именно 3.1»\n')
    rc_рс_wrap, вых_рс_wrap = retract_sync_run(рс_wrap)
    check("retract-sync: цитата, разорванная переносом строки и markdown-"
          "звёздочками, сверяется по нормализованному потоку и пометку отзыва "
          "НЕ теряет (построчный grep тут дал бы ложный красный)",
          rc_рс_wrap == 0, "\n".join(вых_рс_wrap))

    рс_нет = os.path.join(root, "retract-net")
    os.makedirs(os.path.join(рс_нет, "terminal-outputs"), exist_ok=True)
    with open(os.path.join(рс_нет, "research.md"), "w", encoding="utf-8") as fh:
        fh.write("обычный ресёрч без единого отзыва\n")
    rc_рс_нет, вых_рс_нет = retract_sync_run(рс_нет)
    check("retract-sync: отзывов не объявлено - PASS и явная строка об этом "
          "(гейт держит объявленные отзывы, а не выдумывает свои)",
          rc_рс_нет == 0 and "отзывов не объявлено" in "\n".join(вых_рс_нет),
          "\n".join(вых_рс_нет))

    # ── ГЕЙТ svezhaya-tema (закон 25 канона, по решению автора) ─────────────────────
    # Позитив, три контрпримера и проверка неприменимости. Контрпример здесь
    # обязателен по построению: гейт, у которого нет ни одного падающего
    # черновика в селфтесте, доказывает только то, что он умеет печатать PASS
    def ст_стенд(имя, черновик, спек=None):
        d = os.path.join(tempfile.mkdtemp(prefix="gates-st-"), имя)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "draft.md"), "w", encoding="utf-8") as f:
            f.write(черновик)
        if спек is not None:
            with open(os.path.join(d, "spec.json"), "w", encoding="utf-8") as f:
                json.dump(спек, f, ensure_ascii=False)
        return d

    ХОРОШИЙ = (
        "---\nklass: свежая узкая тема\ntema: OpenAI отключила Codex в VS Code\n---\n\n"
        "# OpenAI отключила Codex в VS Code\n\n"
        "29.08.2026 OpenAI закрыла доступ к Codex внутри VS Code для аккаунтов "
        "из России. Расширение остаётся установленным, но любой запрос "
        "возвращает ошибку авторизации.\n\n"
        "## Что теперь делать\n\nПереключить редактор на локальную модель "
        "или сменить способ доступа.\n\n"
        "## Где ломается\n\nПривязка к платёжному профилю аккаунта.\n")
    ст_ок = ст_стенд("svezhaya-ok", ХОРОШИЙ)
    rc_ст, вых_ст = svezhaya_tema_run(ст_ок)
    check("svezhaya-tema ПОЗИТИВ: класс, дата в первых 300 знаках, свой слой, "
          "голова проходит верхний дециль - PASS",
          rc_ст == 0 and "PASS, три правила" in "\n".join(вых_ст),
          "rc=%s\n%s" % (rc_ст, "\n".join(вых_ст)))

    # КОНТРПРИМЕР 1: даты события нет - статья-нарушитель ОБЯЗАНА падать
    БЕЗ_ДАТЫ = ХОРОШИЙ.replace("29.08.2026 OpenAI закрыла", "Недавно OpenAI закрыла")
    rc_д, вых_д = svezhaya_tema_run(ст_стенд("svezhaya-bez-daty", БЕЗ_ДАТЫ))
    check("svezhaya-tema КОНТРПРИМЕР 1: без даты события в первых 300 знаках - FAIL",
          rc_д == 1 and "C1" in "\n".join(вых_д),
          "rc=%s\n%s" % (rc_д, "\n".join(вых_д)))

    # КОНТРПРИМЕР 2: пересказ донора без своего слоя
    БЕЗ_СЛОЯ = (
        "---\nklass: свежая узкая тема\ntema: OpenAI отключила Codex в VS Code\n---\n\n"
        "# OpenAI отключила Codex в VS Code\n\n"
        "29.08.2026 OpenAI закрыла доступ к Codex внутри VS Code для аккаунтов "
        "из России.\n\n## Как было раньше\n\nРаньше расширение работало.\n")
    rc_с, вых_с = svezhaya_tema_run(ст_стенд("svezhaya-bez-sloya", БЕЗ_СЛОЯ))
    check("svezhaya-tema КОНТРПРИМЕР 2: пересказ донора без своего слоя - FAIL",
          rc_с == 1 and "C2" in "\n".join(вых_с),
          "rc=%s\n%s" % (rc_с, "\n".join(вых_с)))

    # КОНТРПРИМЕР 3: голое имя релиза в голове - ровно те страницы корпуса,
    # у которых замер дал ноль кликов за 28 дней
    ГОЛОЕ = (
        "---\nklass: свежая узкая тема\ntema: Gemini 3.7 Flash\n---\n\n"
        "# Gemini 3.7 Flash\n\n29.08.2026 вышла модель Gemini 3.7 Flash.\n\n"
        "## Что теперь делать\n\nПопробовать в своём проекте.\n")
    rc_г, вых_г = svezhaya_tema_run(ст_стенд("svezhaya-goloe", ГОЛОЕ))
    _вых_г = "\n".join(вых_г)
    # R213 (круг 4): без личного сборщика очереди тем (radar_to_queue.py, класс
    # R191/R212) C3 у ученика НЕДОСТУПЕН по построению ([5c3d/6] объявляет это
    # вслух) - требовать от контрпримера живого FAIL по C3 там, где C3 не судит
    # вообще, значит требовать невозможного и красить исправный пакет красным.
    # Тест стал класс-осведомлённым: у автора (C3 доступен) проверка СТРОГАЯ
    # прежняя, у ученика (C3 недоступен) проверяется честное объявление вслух.
    if "C3 НЕ ПРОВЕРЕН" in _вых_г:
        check("svezhaya-tema КОНТРПРИМЕР 3: без сборщика очереди тем C3 объявлен "
              "недоступным явно, C1/C2 продолжают судить",
              rc_г == 0 and "C3 НЕ ПРОВЕРЕН" in _вых_г,
              "rc=%s\n%s" % (rc_г, _вых_г))
    else:
        check("svezhaya-tema КОНТРПРИМЕР 3: голова из голого имени релиза - FAIL "
              "по признакам верхнего дециля",
              rc_г == 1 and "C3" in _вых_г,
              "rc=%s\n%s" % (rc_г, _вых_г))

    # НЕПРИМЕНИМОСТЬ: статья класса «голова спроса» гейтом не судится, и он
    # говорит это вслух, а не молчит зелёным
    ГОЛОВА = ("---\ntema: как оплатить подписку из России\n---\n\n"
              "# Как оплатить подписку из России\n\nПошагово.\n")
    rc_н, вых_н = svezhaya_tema_run(ст_стенд("golova-sprosa", ГОЛОВА))
    check("svezhaya-tema: статья другого класса - PASS и явная строка "
          "«НЕ ПРИМЕНИМ», а не тихий зелёный",
          rc_н == 0 and "НЕ ПРИМЕНИМ" in "\n".join(вых_н),
          "rc=%s\n%s" % (rc_н, "\n".join(вых_н)))

    # класс берётся и из spec.json, а не только из front-matter
    ИЗ_СПЕКИ = ХОРОШИЙ.replace("klass: свежая узкая тема\n", "")
    rc_сп, вых_сп = svezhaya_tema_run(
        ст_стенд("svezhaya-spec", ИЗ_СПЕКИ, спек={"кластер": "инфоповод"}))
    check("svezhaya-tema: класс распознан по spec.json (второй независимый источник)",
          rc_сп == 0 and "spec.json" in "\n".join(вых_сп),
          "rc=%s\n%s" % (rc_сп, "\n".join(вых_сп)))

    # ── ГЕЙТ title-god (дельта топ-3, волна 3, по решению автора) ───────────────────
    # Позитив, контрпример-нарушитель и неприменимость на вечнозелёной теме.
    # Контрпример обязателен: гейт без падающего черновика в селфтесте
    # доказывает только то, что умеет печатать PASS
    ТГ_ХОРОШИЙ = (
        "---\ntitle: \"Сколько стоит подписка на нейросеть в 2026 году\"\n"
        "keywords: [\"цена подписки\", \"сколько стоит\"]\n---\n\n"
        "# Сколько стоит подписка на нейросеть в 2026 году\n\nТекст.\n")
    тг_ок = ст_стенд("titlegod-ok", ТГ_ХОРОШИЙ)
    rc_тг, вых_тг = title_god_run(тг_ок)
    check("title-god ПОЗИТИВ: датируемая тема (цена/доступ) и год в title - PASS",
          rc_тг == 0 and "Год «2026» стоит" in "\n".join(вых_тг),
          "rc=%s\n%s" % (rc_тг, "\n".join(вых_тг)))

    ТГ_БЕЗ_ГОДА = ТГ_ХОРОШИЙ.replace(" в 2026 году", "")
    rc_тгб, вых_тгб = title_god_run(ст_стенд("titlegod-bez-goda", ТГ_БЕЗ_ГОДА))
    check("title-god КОНТРПРИМЕР: датируемая тема БЕЗ года в title - FAIL",
          rc_тгб == 1 and "нет года" in "\n".join(вых_тгб),
          "rc=%s\n%s" % (rc_тгб, "\n".join(вых_тгб)))

    ТГ_ВЕЧНЫЙ = ("---\ntitle: \"Как объяснить ребёнку таблицу умножения\"\n---\n\n"
                 "# Как объяснить ребёнку таблицу умножения\n\nТекст.\n")
    rc_тгв, вых_тгв = title_god_run(ст_стенд("titlegod-vechniy", ТГ_ВЕЧНЫЙ))
    check("title-god: вечнозелёная тема - PASS и явная строка «НЕ ПРИМЕНИМ», "
          "а не тихий зелёный (год бы только состарил сниппет)",
          rc_тгв == 0 and "НЕ ПРИМЕНИМ" in "\n".join(вых_тгв),
          "rc=%s\n%s" % (rc_тгв, "\n".join(вых_тгв)))

    # ── ГЕЙТ own-run-shagi (рв даты запуска.2026, дефект T2 круга 2) ───────────────
    # Пара стендов на одном признаке. Дословная строка расхождения объявлена:
    # «own-run-shagi: FAIL, нарушений 1»
    ОРС_ВНЕШНИЙ = (
        "---\nengine: article_build\nslug: guide-servis-2026\ntitle: \"Сервис\"\n---\n\n"
        "# Сервис\n\nПроверил по решению автора живьём: сервис делает ролик из текста\n\n"
        "## Шаг 1\n\nКуда нажать: открой сервис и найди поле. Оно первое на "
        "экране, мимо не пройдёшь\n\nЧто увидишь: список сцен\n")
    ОРС_ЧЕСТНЫЙ = (
        "---\nengine: article_build\nslug: guide-servis-2026\ntitle: \"Сервис\"\n---\n\n"
        "# Сервис\n\nПо странице тарифов и документации на момент этой редакции сервис "
        "собирает ролик из текста\n\n## Что даёт бесплатный план\n\nНа странице "
        "тарифов стоит 800 кредитов разово и лицензия только для личных проектов\n")

    def орс_стенд(имя, текст, манифест=None):
        d = os.path.join(root, имя)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "draft.md"), "w", encoding="utf-8") as fh:
            fh.write(текст)
        if манифест is not None:
            with open(os.path.join(d, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
                json.dump({"frames": манифест}, fh, ensure_ascii=False)
        return d

    # Стенд А, НЕИСПРАВЛЕННАЯ половина: пошаговая инструкция плюс «проверил
    # живьём», а в манифесте только кадры чужой витрины - ни одного own-run
    орс_плохо = орс_стенд("ors-vneshniy", ОРС_ВНЕШНИЙ, [
        {"file": "assets/shot-pricing.webp", "class": "result", "mode": "url",
         "url": "https://site.test/pricing", "steps": 1, "shot_at": "2026-08-30",
         "note": "страница тарифов"}])
    rc_орс_п, вых_орс_п = own_run_shagi_run(орс_плохо)
    check("own-run-shagi КОНТРПРИМЕР (стенд А): 4-шаговая инструкция по "
          "интерфейсу плюс «Проверил по решению автора живьём», а кадров own-run в "
          "манифесте ноль - FAIL, и маркеры названы поимённо",
          rc_орс_п == 1
          and "own-run-shagi: FAIL, нарушений 1" in "\n".join(вых_орс_п)
          and "куда нажать" in "\n".join(вых_орс_п)
          and "кадров own-run" in "\n".join(вых_орс_п),
          f"rc={rc_орс_п}\n" + "\n".join(вых_орс_п))

    # Стенд Б-1, ИСПРАВЛЕННАЯ половина дорогой (1): тот же текст, но свой экран снят
    орс_свой = орс_стенд("ors-svoy-ekran", ОРС_ВНЕШНИЙ, [
        {"file": "assets/shot-pricing.webp", "class": "result", "mode": "url",
         "url": "https://site.test/pricing", "steps": 1, "shot_at": "2026-08-30",
         "note": "страница тарифов"},
        {"file": "assets/moy-ekran.webp", "class": "own-run", "mode": "scenario",
         "url": "https://site.test/app", "steps": 3, "shot_at": "2026-08-30",
         "note": "мой прогон внутри"}])
    rc_орс_с, вых_орс_с = own_run_shagi_run(орс_свой)
    check("own-run-shagi ПОЗИТИВ (стенд Б-1): та же инструкция, но в манифесте "
          "есть кадр own-run - PASS, строки FAIL в выводе нет",
          rc_орс_с == 0
          and "own-run-shagi: FAIL" not in "\n".join(вых_орс_с)
          and "OK. Свой экран есть" in "\n".join(вых_орс_с),
          f"rc={rc_орс_с}\n" + "\n".join(вых_орс_с))

    # Стенд Б-2, ИСПРАВЛЕННАЯ половина дорогой (2): маркеры и заявление убраны,
    # раздел переписан по документации - гейт НЕ ПРИМЕНИМ, свой экран не нужен
    орс_честно = орс_стенд("ors-chestniy", ОРС_ЧЕСТНЫЙ, [
        {"file": "assets/shot-pricing.webp", "class": "result", "mode": "url",
         "url": "https://site.test/pricing", "steps": 1, "shot_at": "2026-08-30",
         "note": "страница тарифов"}])
    rc_орс_ч, вых_орс_ч = own_run_shagi_run(орс_честно)
    check("own-run-shagi ПОЗИТИВ (стенд Б-2): пошаговых маркеров и заявления о "
          "живой проверке нет, статья написана по тарифам и документации - "
          "«НЕ ПРИМЕНИМ», PASS без кадра own-run",
          rc_орс_ч == 0
          and "НЕ ПРИМЕНИМ" in "\n".join(вых_орс_ч)
          and "own-run-shagi: FAIL" not in "\n".join(вых_орс_ч),
          f"rc={rc_орс_ч}\n" + "\n".join(вых_орс_ч))

    rc_орс_н, вых_орс_н = own_run_shagi_run(os.path.join(root, "ors-net-takogo"))
    check("own-run-shagi: нет черновика - ERROR, а не молчаливый зелёный",
          rc_орс_н == 2, f"rc={rc_орс_н}\n" + "\n".join(вых_орс_н))

    rc_тгн, вых_тгн = title_god_run(os.path.join(root, "titlegod-net-takogo"))
    check("title-god: нет черновика - ERROR, а не молчаливый зелёный",
          rc_тгн == 2, "rc=%s\n%s" % (rc_тгн, "\n".join(вых_тгн)))

    # ── ГЕЙТ vnutrennie-ssylki (дельта топ-3, волна 3, по решению автора) ───────────
    ВН_ССЫЛКИ = "".join("[текст%d](/guide-tema-%d/) " % (i, i) for i in range(1, 22))
    ВН_ХОРОШИЙ = ("---\ntitle: \"Статья\"\n---\n\n# Статья\n\n" + ВН_ССЫЛКИ + "\n")
    rc_вн, вых_вн = vnutrennie_ssylki_run(ст_стенд("vnutr-ok", ВН_ХОРОШИЙ))
    check("vnutrennie-ssylki ПОЗИТИВ: 21 внутренняя ссылка в теле черновика при пороге 20 - PASS",
          rc_вн == 0 and "OK." in "\n".join(вых_вн),
          "rc=%s\n%s" % (rc_вн, "\n".join(вых_вн)))

    ВН_МАЛО = ("---\ntitle: \"Статья\"\n---\n\n# Статья\n\n"
               "[раз](/guide-a/) [два](/guide-b/) [три](/guide-c/)\n")
    rc_внм, вых_внм = vnutrennie_ssylki_run(ст_стенд("vnutr-malo", ВН_МАЛО))
    check("vnutrennie-ssylki КОНТРПРИМЕР: 3 ссылки (прежний минимум "
          "structure-check) при новом пороге 12 - FAIL",
          rc_внм == 1 and "перелинковки не хватает" in "\n".join(вых_внм),
          "rc=%s\n%s" % (rc_внм, "\n".join(вых_внм)))

    ВН_ЧУЖИЕ = ("---\ntitle: \"Статья\"\n---\n\n# Статья\n\n"
                + "".join("[внешняя%d](https://example.com/x%d) " % (i, i)
                          for i in range(1, 20)) + "\n")
    rc_внч, вых_внч = vnutrennie_ssylki_run(ст_стенд("vnutr-chuzhie", ВН_ЧУЖИЕ))
    check("vnutrennie-ssylki КОНТРПРИМЕР 2: 19 ЧУЖИХ ссылок за внутренние не "
          "считаются - FAIL (иначе порог брался бы источниками)",
          rc_внч == 1, "rc=%s\n%s" % (rc_внч, "\n".join(вых_внч)))

    # СТРАНИЦА: обвязка (меню/подвал) в счёт не идёт - иначе порог брался бы
    # одним меню и гейт горел бы зелёным на статье с нулём контекстных ссылок
    ВН_СТР_ПЛОХО = ("<html><body><nav>"
                    + "".join('<a href="/guide-nav-%d/">n</a>' % i for i in range(1, 31))
                    + "</nav><main><p>Текст без ссылок</p></main>"
                    '<footer><a href="/about/">о нас</a></footer></body></html>')
    д_стр = ст_стенд("vnutr-stranica", "---\ntitle: x\n---\n\n# x\n")
    with open(os.path.join(д_стр, "index.html"), "w", encoding="utf-8") as f:
        f.write(ВН_СТР_ПЛОХО)
    rc_внс, вых_внс = vnutrennie_ssylki_run(д_стр, stage="page")
    check("vnutrennie-ssylki КОНТРПРИМЕР 3: 30 ссылок в меню НЕ закрывают порог, "
          "потому что считается только тело main - FAIL",
          rc_внс == 1, "rc=%s\n%s" % (rc_внс, "\n".join(вых_внс)))

    ВН_СТР_ОК = ("<html><body><nav><a href=\"/x/\">n</a></nav><main>"
                 + "".join('<a href="/guide-tema-%d/">т</a>' % i for i in range(1, 22))
                 + "</main></body></html>")
    with open(os.path.join(д_стр, "index.html"), "w", encoding="utf-8") as f:
        f.write(ВН_СТР_ОК)
    rc_внсо, вых_внсо = vnutrennie_ssylki_run(д_стр, stage="page")
    check("vnutrennie-ssylki ПОЗИТИВ страницы: 21 ссылка в теле main при пороге 20 - PASS",
          rc_внсо == 0, "rc=%s\n%s" % (rc_внсо, "\n".join(вых_внсо)))

    # ИНТЕГРАЦИЯ: гейт реально стоит в стадии page конвейера (build_gates) и
    # исполняется (не SKIP) - переиспользуем отчёт fx_cta из раздела 20, там
    # FX_PAGE без единого img/source/preload даёт 0 ссылок, что законный PASS
    g_ax_wired = [g for g in d_cta["stages"]["page"]["gates"] if g["name"] == "assets-exist"]
    check("assets-exist: гейт стоит в стадии page реального конвейера и реально "
          "исполнился (не SKIP)",
          len(g_ax_wired) == 1 and g_ax_wired[0]["status"] == "PASS",
          str(g_ax_wired[:1]))

    # ИНТЕГРАЦИЯ image-refs: тот же приём и тот же отчёт fx_cta - FX_PAGE без
    # единого img/source/preload даёт 0 ссылок, что законный PASS
    g_ир_wired = [g for g in d_cta["stages"]["page"]["gates"] if g["name"] == "image-refs"]
    check("image-refs: гейт стоит в стадии page реального конвейера и реально "
          "исполнился (не SKIP)",
          len(g_ир_wired) == 1 and g_ир_wired[0]["status"] == "PASS",
          str(g_ир_wired[:1]))
    check("image-refs: гейт ОБЯЗАТЕЛЬНЫЙ - битая картинка роняет стадию page, "
          "а не уезжает замечанием",
          len(g_ир_wired) == 1 and g_ир_wired[0]["required"] is True,
          str(g_ир_wired[:1]))

    # ── 22. ГЕЙТ infra-leak: утечка служебной инфраструктуры автора в собранной
    # странице (р9-по решению автора, ИНЦИДЕНТ - IP деплой-релея 203.0.113.10 утёк в
    # видимый текст 6 статей, 3 уже жили на проде, НИ ОДИН гейт это не поймал) ──
    def _страница_инфра(тело):
        return f"<html><head><title>t</title></head><body>{тело}</body></html>"

    secrets_ok = os.path.join(root, "infra-secrets-ok.txt")
    with open(secrets_ok, "w", encoding="utf-8") as fh:
        fh.write("# комментарий - не литерал\n\n"
                 "203.0.113.10\n95.12.115.148\nroot@\nseo-site\n"
                 "fx-host.fixture.test\nfx-login-01\n")
    check("infra_leak_literals: комментарии и пустые строки не литералы, "
          "6 боевых литералов прочитаны по порядку",
          infra_leak_literals(secrets_ok) ==
          ["203.0.113.10", "95.12.115.148", "root@", "seo-site",
           "fx-host.fixture.test", "fx-login-01"],
          str(infra_leak_literals(secrets_ok)))

    # ПОЗИТИВ: чистая страница - generic-примеры SSH/«seo-site» словом, ни один
    # РЕАЛЬНЫЙ литерал не встречается
    ix_pos = os.path.join(root, "infra-pos")
    os.makedirs(ix_pos, exist_ok=True)
    with open(os.path.join(ix_pos, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_страница_инфра(
            "<p>Подключаемся по SSH: ssh root@example.com, а свой seo-site "
            "правим в панели хостинга - это generic-пример из учебника.</p>"))
    rc_ix_pos, вых_ix_pos = infra_leak_run(ix_pos, secrets_ok)
    check("infra-leak ПОЗИТИВ: generic root@example.com и слово «seo-site» без "
          "формы утечки -> PASS, rc=0",
          rc_ix_pos == 0 and "OK." in "\n".join(вых_ix_pos), "\n".join(вых_ix_pos))

    # НЕГАТИВ: реальный IP деплой-релея в тексте - сам инцидент р9
    ix_neg = os.path.join(root, "infra-neg")
    os.makedirs(ix_neg, exist_ok=True)
    with open(os.path.join(ix_neg, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_страница_инфра(
            "<p>Пример из практики: сервер отвечал по адресу 203.0.113.10, "
            "туда я и деплоил статью.</p>"))
    rc_ix_neg, вых_ix_neg = infra_leak_run(ix_neg, secrets_ok)
    check("infra-leak НЕГАТИВ: IP деплой-релея в тексте -> FAIL с литералом и "
          "номером строки",
          rc_ix_neg == 1 and "203.0.113.10" in "\n".join(вых_ix_neg)
          and "строка" in "\n".join(вых_ix_neg), "\n".join(вых_ix_neg))

    # НЕГАТИВ: узкие формы root@<хост-релея> и «ssh seo-site» (реальные команды,
    # не generic-примеры) - тоже ловятся
    ix_narrow = os.path.join(root, "infra-narrow")
    os.makedirs(ix_narrow, exist_ok=True)
    with open(os.path.join(ix_narrow, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_страница_инфра(
            "<p>Реальная команда из моей практики: ssh root@msk-relay-01, а ещё "
            "я хожу через алиас ssh seo-site.</p>"))
    rc_ix_narrow, вых_ix_narrow = infra_leak_run(ix_narrow, secrets_ok)
    check("infra-leak НЕГАТИВ: узкие формы root@msk.. и «ssh seo-site» (реальные "
          "команды) ловятся так же",
          rc_ix_narrow == 1 and "root@" in "\n".join(вых_ix_narrow)
          and "seo-site" in "\n".join(вых_ix_narrow), "\n".join(вых_ix_narrow))

    # СПИСОК НЕ НАСТРОЕН: файла нет -> ГРОМКИЙ SKIP (rc=3), не тихий PASS
    rc_ix_нет, вых_ix_нет = infra_leak_run(
        ix_pos, os.path.join(root, "нет-infra-secrets.txt"))
    check("infra-leak: infra-secrets.txt на диске нет -> SKIP (rc=3), громкая "
          "строка «список запретных литералов не найден»",
          rc_ix_нет == 3
          and "список запретных литералов не найден" in "\n".join(вых_ix_нет),
          "\n".join(вых_ix_нет))

    # ИНТЕГРАЦИЯ-ПОЗИТИВ: гейт реально стоит в стадии page конвейера, литералы
    # фикстуры (FX_INFRA_LITERALS) в FX_PAGE не встречаются -> PASS, не SKIP
    g_ix_wired = [g for g in d_cta["stages"]["page"]["gates"] if g["name"] == "infra-leak"]
    check("infra-leak: гейт стоит в стадии page реального конвейера и реально "
          "исполнился (не SKIP)",
          len(g_ix_wired) == 1 and g_ix_wired[0]["status"] == "PASS",
          str(g_ix_wired[:1]))

    # ИНТЕГРАЦИЯ-НЕГАТИВ: литерал фикстуры в СОБРАННОЙ странице роняет стадию
    # page целиком (полный сквозной прогон через main(), не прямой вызов функции)
    fx_ix_neg = _fixture(os.path.join(root, "infra-wired-neg"))
    _положить(fx_ix_neg, "index.html",
              FX_PAGE.replace("</body>",
                              f"<p>сервер {FX_INFRA_LITERALS[0]}</p></body>"))
    rc_ix_wired_neg = call(fx_ix_neg, fx_ix_neg["slug"], "--stage", "page")
    g_ix_wired_neg = _гейт(fx_ix_neg, "page", "infra-leak")
    check("infra-leak: литерал в собранной странице роняет РЕАЛЬНУЮ стадию page "
          "целиком (rc=1, FAIL)",
          rc_ix_wired_neg == 1 and g_ix_wired_neg["status"] == "FAIL"
          and any(FX_INFRA_LITERALS[0] in s for s in g_ix_wired_neg.get("flags", [])),
          f"rc={rc_ix_wired_neg} {g_ix_wired_neg.get('flags')}")

    # ИНТЕГРАЦИЯ-SKIP: машина без infra-secrets.txt (инструмент ученика/фикс) -
    # гейт SKIP громко, вердикт стадии page ЭТО НЕ РОНЯЕТ (required=True, но
    # SKIP не считается провалом - см. verdict_of), сама расписка несёт причину
    fx_ix_skip = _fixture(os.path.join(root, "infra-wired-skip"), infra_secrets=False)
    rc_ix_wired_skip = call(fx_ix_skip, fx_ix_skip["slug"], "--stage", "page")
    g_ix_wired_skip = _гейт(fx_ix_skip, "page", "infra-leak")
    check("infra-leak: список не настроен (машина без infra-secrets.txt) -> "
          "SKIP, вердикт стадии PASS, причина видна в расписке",
          rc_ix_wired_skip == 0 and g_ix_wired_skip["status"] == "SKIP"
          and "список запретных литералов не найден" in g_ix_wired_skip["out"],
          f"rc={rc_ix_wired_skip} status={g_ix_wired_skip['status']} "
          f"out={g_ix_wired_skip['out'][:120]}")

    # ── 23. ГЕЙТ frame-density: плотность кадра (рв даты запуска.2026, разнос
    # владельца по хиро guide-deepseek - «че это за треш вместо картинок?
    # переделать все и НИКОГДА такое говно не ставить»). Три СИНТЕТИЧЕСКИХ
    # кадра, по одному на каждый исход: плотный / пустой блок / текст-плашка.
    # Синтетика, а не живые файлы корпуса, специально: живой кадр завтра
    # переснимут и тест начнёт мерить чужую работу, а не логику гейта ────────
    fd_dir = os.path.join(root, "frame-density")
    fd_assets = os.path.join(fd_dir, "assets")
    os.makedirs(fd_assets, exist_ok=True)

    def _fd_кадры():
        """(плотный, пустота, плашка) - три PNG в assets фикстуры. Генератор
        детерминированный (фиксированное зерно), метрики не плавают."""
        from PIL import Image
        rnd = random.Random(20260818)
        # 1. ПЛОТНЫЙ: шум по всему кадру - так меряется живой скриншот
        # интерфейса или терминала, где контент до краёв
        плотный = Image.new("L", (320, 320))
        плотный.putdata([rnd.randrange(256) for _ in range(320 * 320)])
        плотный.save(os.path.join(fd_assets, "fd-plotnyy.png"))
        # 2. ПУСТОТА: контент полоской сверху (6 тайл-рядов), ниже ровная
        # заливка - ровно дефект из разноса владельца, только синтетикой
        пустота = Image.new("L", (320, 320), 200)
        px = пустота.load()
        for y in range(96):
            for x in range(320):
                px[x, y] = rnd.randrange(256)
        пустота.save(os.path.join(fd_assets, "fd-pustota.png"))
        # webp-близнец того же кадра: на живой странице он приезжает в
        # <source srcset>, и гейт обязан посчитать это ОДНИМ кадром
        пустота.save(os.path.join(fd_assets, "fd-pustota.webp"))
        # 3. ПЛАШКА: пустота РАЗМАЗАНА между «карточками» (сетка полос через
        # каждые 12 тайлов) - одного большого блока нет, первая ветка слепа
        плашка = Image.new("L", (512, 512), 235)
        px = плашка.load()
        for t in (0, 12, 24):
            for y in range(t * 16, t * 16 + 16):
                for x in range(512):
                    px[x, y] = rnd.randrange(256)
            for x in range(t * 16, t * 16 + 16):
                for y in range(512):
                    px[x, y] = rnd.randrange(256)
        плашка.save(os.path.join(fd_assets, "fd-plashka.png"))
        # та же плашка под именем превьюшки «Читайте также» - гейт обязан её
        # ПРОПУСТИТЬ: это кадр ЧУЖОЙ статьи, обрезанный под карточку
        плашка.save(os.path.join(fd_assets, "thumb-fd-chuzhaya.png"))

    _fd_кадры()

    м_плотный = frame_analyze(os.path.join(fd_assets, "fd-plotnyy.png"))
    м_пустота = frame_analyze(os.path.join(fd_assets, "fd-pustota.png"))
    м_плашка = frame_analyze(os.path.join(fd_assets, "fd-plashka.png"))

    check("frame-density КЕЙС 1 (плотный): кадр без пустоты -> вердикта нет",
          frame_density_verdict(м_плотный) is None
          and м_плотный["block_pct"] < FRAME_BLOCK_FAIL,
          str(м_плотный))
    check("frame-density КЕЙС 2 (пустота): один большой мёртвый блок -> ветка 1 "
          "«пустой блок в кадре» по block_pct",
          (frame_density_verdict(м_пустота) or ("", ""))[0] == "пустой блок в кадре"
          and м_пустота["block_pct"] >= FRAME_BLOCK_FAIL,
          str(м_пустота))
    check("frame-density КЕЙС 3 (плашка): пустота размазана между карточками - "
          "ветка 1 слепа (block_pct < 20), ловит ветка 2 по empty_pct",
          (frame_density_verdict(м_плашка) or ("", ""))[0] == "подозрение на текст-плашку"
          and м_плашка["block_pct"] < FRAME_PLASHKA_BLOCK
          and м_плашка["empty_pct"] >= FRAME_PLASHKA_EMPTY,
          str(м_плашка))

    def _fd_страница(теги):
        with open(os.path.join(fd_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(f"<html><head><title>t</title>{теги[0]}</head>"
                    f"<body>{теги[1]}</body></html>")

    # ПОЗИТИВ: страница с одним плотным кадром + превьюшка чужой статьи
    # (thumb-*, плашка по метрике) + чужой домен в og - гейт зелёный
    _fd_страница((
        '<meta property="og:image" content="https://example.com/chuzhoy/og.jpg" />',
        '<img src="assets/fd-plotnyy.png">'
        '<img class="rc-thumb" src="assets/thumb-fd-chuzhaya.png">'))
    rc_fd_pos, вых_fd_pos = frame_density_run(fd_dir)
    check("frame-density ПОЗИТИВ: плотный кадр -> PASS, rc=0",
          rc_fd_pos == 0 and "OK." in "\n".join(вых_fd_pos), "\n".join(вых_fd_pos))
    check("frame-density ПОЗИТИВ: thumb-* (превью карточки «Читайте также») и "
          "og чужого домена в счёт кадров статьи не идут",
          "thumb-fd-chuzhaya" not in "\n".join(вых_fd_pos)
          and "example.com" not in "\n".join(вых_fd_pos), "\n".join(вых_fd_pos))

    # НЕГАТИВ: обе породы брака сразу, причём плашка приезжает КАК og-обложка
    # абсолютным URL своего слага (og мимо img/source не прошла бы вовсе)
    _fd_страница((
        '<meta property="og:image" content="https://site.test/'
        'frame-density/assets/fd-plashka.png" />',
        '<picture><source srcset="assets/fd-pustota.webp" type="image/webp">'
        '<img src="assets/fd-pustota.png"></picture>'))
    rc_fd_neg, вых_fd_neg = frame_density_run(fd_dir)
    текст_fd_neg = "\n".join(вых_fd_neg)
    check("frame-density НЕГАТИВ: пустой блок роняет гейт в FAIL с ПОИМЁННЫМ "
          "кадром и числами",
          rc_fd_neg == 1 and "fd-pustota.png" in текст_fd_neg
          and "пустой блок в кадре" in текст_fd_neg, текст_fd_neg)
    check("frame-density НЕГАТИВ: og-обложка СВОЕГО слага абсолютным URL "
          "проверяется наравне с img и ловится как текст-плашка",
          "fd-plashka.png" in текст_fd_neg
          and "подозрение на текст-плашку" in текст_fd_neg, текст_fd_neg)
    _fd_refs = frame_density_refs(
        tc_read(os.path.join(fd_dir, "index.html")), "frame-density")
    check("frame-density НЕГАТИВ: пара png (img src) + webp (source srcset) на "
          "один кадр меряется ОДИН раз, и меряется png (порядок jpg>jpeg>png>webp)",
          _fd_refs.count("assets/fd-pustota.png") == 1
          and "assets/fd-pustota.webp" not in _fd_refs
          and len(_fd_refs) == 2, str(_fd_refs))

    # ОШИБКА ВХОДА: нет собранной страницы вовсе - вердикт не выдумывается
    fd_нет = os.path.join(root, "frame-density-net-page")
    os.makedirs(fd_нет, exist_ok=True)
    rc_fd_нет, вых_fd_нет = frame_density_run(fd_нет)
    check("frame-density: нет index.html - гейт не выдумывает вердикт, rc=2",
          rc_fd_нет == 2, "\n".join(вых_fd_нет))

    # ИНТЕГРАЦИЯ: гейт реально стоит в стадии page конвейера и исполняется -
    # переиспользуем отчёт fx_cta из раздела 20 (FX_PAGE без единой картинки =
    # 0 кадров, законный PASS)
    g_fd_wired = [g for g in d_cta["stages"]["page"]["gates"] if g["name"] == "frame-density"]
    check("frame-density: гейт стоит в стадии page реального конвейера и реально "
          "исполнился (не SKIP)",
          len(g_fd_wired) == 1 and g_fd_wired[0]["status"] == "PASS",
          str(g_fd_wired[:1]))

    # ── 24-бис. ПОЛ ПО ЧИСЛУ СОБСТВЕННЫХ КАДРОВ (круг 4, R128) ────────────────
    # В круге 3 пол вшили в код без единого теста: ни контрпримера, ни позитива,
    # ни проверки, что он вообще применяется. Здесь закрыты все четыре ветки -
    # старый корпус без манифеста, недобор, норма и порог из конфига.
    fdp_dir = os.path.join(root, "frame-pol")
    fdp_assets = os.path.join(fdp_dir, "assets")
    os.makedirs(fdp_assets, exist_ok=True)
    for имя in ("fp-1.png", "fp-2.png", "fp-3.png"):
        shutil.copyfile(os.path.join(fd_assets, "fd-plotnyy.png"),
                        os.path.join(fdp_assets, имя))

    def _fdp_страница(фигур):
        тело = "".join(
            f'<figure><img src="assets/fp-{i + 1}.png"></figure>' for i in range(фигур))
        with open(os.path.join(fdp_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(f"<html><head><title>t</title></head><body>{тело}</body></html>")

    манифест_fdp = os.path.join(fdp_dir, PROV_MANIFEST_NAME)

    # ВЕТКА 1: манифеста нет - это старый корпус, пол НЕ применяется
    _fdp_страница(1)
    rc_fdp_старый, вых_fdp_старый = frame_density_run(fdp_dir)
    check("frame-density ПОЛ: страница БЕЗ манифеста съёмки (старый корпус) - пол "
          "не применяется, один кадр проходит",
          rc_fdp_старый == 0
          and "пол по числу кадров НЕ применяется" in "\n".join(вых_fdp_старый),
          "\n".join(вых_fdp_старый))

    # ВЕТКА 2 (КОНТРПРИМЕР): манифест есть, кадр один - обязан упасть
    with open(манифест_fdp, "w", encoding="utf-8") as fh:
        json.dump({"frames": [{"file": "assets/fp-1.png", "class": "result"}]},
                  fh, ensure_ascii=False)
    rc_fdp_мало, вых_fdp_мало = frame_density_run(fdp_dir)
    т_fdp_мало = "\n".join(вых_fdp_мало)
    check("frame-density ПОЛ КОНТРПРИМЕР: новое производство с ОДНИМ кадром "
          "роняет стадию, rc=1, число названо",
          rc_fdp_мало == 1 and "КАДРОВ МЕНЬШЕ ПОЛА: 1 против 3" in т_fdp_мало,
          т_fdp_мало)
    check("frame-density ПОЛ: сообщение об отказе печатает РАБОЧУЮ лестницу "
          "добора и не обещает выход через .vizblock (круг 4, R128)",
          "Лестница добора" in т_fdp_мало and "imgsrc.py" in т_fdp_мало
          and ".vizblock.vizsteps" not in т_fdp_мало, т_fdp_мало)

    # ВЕТКА 3: три кадра - норма пройдена
    _fdp_страница(3)
    rc_fdp_норма, вых_fdp_норма = frame_density_run(fdp_dir)
    check("frame-density ПОЛ ПОЗИТИВ: три собственных кадра при манифесте - PASS",
          rc_fdp_норма == 0
          and "собственных кадров в теле (<figure>): 3" in "\n".join(вых_fdp_норма),
          "\n".join(вых_fdp_норма))

    # ВЕТКА 4: порог берётся ИЗ КОНФИГА, а не только из константы. Канон
    # раздаваемого модуля объявляет ключ tools.visual.frame_count_min - здесь
    # доказано, что ключ рабочий, а не обещание в тексте
    fdp_yaml = os.path.join(fdp_dir, "cfg.yaml")
    with open(fdp_yaml, "w", encoding="utf-8") as fh:
        fh.write("tools:\n  visual:\n    frame_count_min: 4\n")
    rc_fdp_cfg, вых_fdp_cfg = frame_density_run(fdp_dir, yaml_path=fdp_yaml)
    т_fdp_cfg = "\n".join(вых_fdp_cfg)
    check("frame-density ПОЛ: порог читается из tools.visual.frame_count_min "
          "конфига - при 4 те же три кадра падают, источник порога назван",
          rc_fdp_cfg == 1 and "КАДРОВ МЕНЬШЕ ПОЛА: 3 против 4" in т_fdp_cfg
          and "порог из конфига" in т_fdp_cfg, т_fdp_cfg)
    def _fdp_cmd(g):
        c = g.get("cmd")
        return c if isinstance(c, str) else " ".join(c or [])

    check("frame-density ПОЛ: стадия page реального конвейера передаёт гейту "
          "конфиг порогов (--frame-yaml), а не молча идёт на дефолте",
          any("--frame-yaml" in _fdp_cmd(g) for g in d_cta["stages"]["page"]["gates"]
              if g["name"] == "frame-density"),
          str([_fdp_cmd(g) for g in d_cta["stages"]["page"]["gates"]
               if g["name"] == "frame-density"]))

    # ── 25. ПЕРЕКАЛИБРОВКА frame-density по аудиту r10 (рв даты запуска.2026) ───────
    # Первая редакция гейта зашила порог 25 как FAIL и стёрла среднюю зону
    # аудита («ПОГРАНИЧНЫЙ 25-40 - глазами, решение человека»). Итог: 70 из 78
    # страниц корпус-волны репозиции CTA не публикуемы по кадрам, которых волна
    # не касалась. Здесь проверяется КАЖДАЯ граница отдельно и исключение
    # аудита «терминал с текстом - это контент, а не пустота».
    # Кадры СИНТЕТИЧЕСКИЕ с фиксированным зерном: живой кадр завтра переснимут,
    # и тест начнёт мерить чужую работу вместо логики порогов
    fdr_dir = os.path.join(root, "frame-recal")
    fdr_assets = os.path.join(fdr_dir, "assets")
    os.makedirs(fdr_assets, exist_ok=True)
    _fdr_rnd = random.Random(20260819)

    def _fdr_кадр(имя, чернила, W=320, H=320):
        """Кадр 20x20 тайлов: где чернила() истинны - шум, иначе ровная заливка."""
        from PIL import Image
        im = Image.new("L", (W, H), 200)
        px = im.load()
        cols, rows = W // FRAME_TILE, H // FRAME_TILE
        for ry in range(rows):
            for rx in range(cols):
                if чернила(rx, ry, cols, rows):
                    for y in range(ry * FRAME_TILE, ry * FRAME_TILE + FRAME_TILE):
                        for x in range(rx * FRAME_TILE, rx * FRAME_TILE + FRAME_TILE):
                            px[x, y] = _fdr_rnd.randrange(256)
        p = os.path.join(fdr_assets, имя)
        im.save(p)
        return frame_analyze(p)

    # ── ПОЗИТИВ: плотный кадр как был, так и остался чистым ──────────────────
    м_fdr_плотн = _fdr_кадр("fdr-plotnyy.png", lambda rx, ry, c, r: True)
    check("frame-recal ПОЗИТИВ: плотный кадр - ни брака, ни замечания",
          frame_density_verdict(м_fdr_плотн) is None
          and frame_density_warn(м_fdr_плотн) is None
          and м_fdr_плотн["block_pct"] < FRAME_BLOCK_WARN, str(м_fdr_плотн))

    # ── ГРАНИЦА: block_pct 35 = зона 25-40 -> ЗАМЕЧАНИЕ, не брак ─────────────
    # пятно контента посреди пустых полей - форма реального пограничного кадра
    # корпуса (guide-bolt-new-vhod.jpg: модалка на размытом фоне, block 25.7)
    м_fdr_warn = _fdr_кадр("fdr-warn.png",
                           lambda rx, ry, c, r: 7 <= rx <= 12 and 7 <= ry <= 12)
    check("frame-recal ГРАНИЦА: block_pct 35 (зона 25-40) - ЗАМЕЧАНИЕ, не брак. "
          "Первая редакция роняла такой кадр в FAIL по порогу 25",
          frame_density_verdict(м_fdr_warn) is None
          and (frame_density_warn(м_fdr_warn) or ("",))[0] == "пограничная пустота, глазами"
          and FRAME_BLOCK_WARN <= м_fdr_warn["block_pct"] < FRAME_BLOCK_FAIL,
          str(м_fdr_warn))

    # ── НЕГАТИВ: block_pct >= 40 = БРАК, и исключение его НЕ спасает ─────────
    # пустая правая треть при чернилах по всей высоте: кадр проходит признак
    # контента, но аудит про ветку брака говорит «оставить block_pct и band_pct»
    м_fdr_блок = _fdr_кадр("fdr-blok.png", lambda rx, ry, c, r: rx < 11)
    check("frame-recal НЕГАТИВ: block_pct 45 >= 40 = БРАК, rc-ветка FAIL",
          (frame_density_verdict(м_fdr_блок) or ("",))[0] == "пустой блок в кадре"
          and м_fdr_блок["block_pct"] >= FRAME_BLOCK_FAIL, str(м_fdr_блок))
    check("frame-recal НЕГАТИВ: исключение «кадр-контент» НЕ спасает от брака - "
          "у терминала block_pct и band_pct работают в полную силу (так в аудите)",
          frame_is_content(м_fdr_блок) and frame_density_verdict(м_fdr_блок) is not None,
          f"контент={frame_is_content(м_fdr_блок)} {м_fdr_блок}")

    # ── НЕГАТИВ: вторая нога брака - мёртвая полоса band_pct >= 40 ──────────
    # девять почти пустых рядов (по одному тайлу чернил в разных столбцах):
    # сплошного блока нет (block 9), а полоса есть - ветку видно изолированно
    м_fdr_полоса = _fdr_кадр(
        "fdr-polosa.png",
        lambda rx, ry, c, r: (rx == (ry * 7) % c) if ry < 9 else True)
    check("frame-recal НЕГАТИВ: band_pct 45 >= 40 = БРАК отдельной ногой "
          "(block_pct всего 9, первая ветка слепа)",
          (frame_density_verdict(м_fdr_полоса) or ("",))[0] == "мёртвая полоса во всю ширину"
          and м_fdr_полоса["band_pct"] >= FRAME_BAND_FAIL
          and м_fdr_полоса["block_pct"] < FRAME_BLOCK_FAIL, str(м_fdr_полоса))

    # ── ИСКЛЮЧЕНИЕ АУДИТА: терминал/скрин с текстом = контент ───────────────
    # 1) кадр той же зоны 25-40, но чернила по всей высоте с рваным правым краем
    #    (ровно форма терминала: guide-vaybkoding-kurs-zapusk.jpg block 30.4,
    #    аудит зовёт его ПЛОТНЫМ, а первая редакция роняла в FAIL)
    м_fdr_терм = _fdr_кадр("fdr-terminal.png", lambda rx, ry, c, r: rx < 14)
    check("frame-recal ИСКЛЮЧЕНИЕ: терминал с рваным правым краем (block 30, зона "
          "25-40) - контент, ни брака, ни замечания",
          frame_is_content(м_fdr_терм)
          and frame_density_verdict(м_fdr_терм) is None
          and frame_density_warn(м_fdr_терм) is None
          and FRAME_BLOCK_WARN <= м_fdr_терм["block_pct"] < FRAME_BLOCK_FAIL,
          str(м_fdr_терм))
    # 2) ветка текст-плашки: у аудита ТРИ условия, третье - «отсутствие хрома
    #    интерфейса». В первой редакции его не было, и ветка роняла терминалы:
    #    psiholog-dostup-moskva.jpg (empty 80.3, block 18.9) аудит зовёт ПЛОТНЫМ
    м_fdr_редк = _fdr_кадр("fdr-terminal-redkiy.png",
                           lambda rx, ry, c, r: ry % 2 == 0 and (rx * 7 + ry) % 3 == 0)
    check("frame-recal ИСКЛЮЧЕНИЕ: редкие строки текста по всей площади "
          "(empty >= 80, block < 20) - терминал, а НЕ текст-плашка",
          м_fdr_редк["empty_pct"] >= FRAME_PLASHKA_EMPTY
          and м_fdr_редк["block_pct"] < FRAME_PLASHKA_BLOCK
          and frame_is_content(м_fdr_редк)
          and frame_density_verdict(м_fdr_редк) is None, str(м_fdr_редк))
    # 3) настоящая плашка (чернила собраны в несколько карточек) ветку сохраняет
    check("frame-recal ИСКЛЮЧЕНИЕ не слепое: настоящая текст-плашка (чернила "
          "собраны в карточки, не размазаны) по-прежнему БРАК",
          not frame_is_content(м_плашка)
          and (frame_density_verdict(м_плашка) or ("",))[0] == "подозрение на текст-плашку",
          f"контент={frame_is_content(м_плашка)} {м_плашка}")

    # ── ПРОГОН: страница только с пограничным кадром -> rc=4, стадию не роняет ─
    def _fdr_страница(теги):
        with open(os.path.join(fdr_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(f"<html><head><title>t</title></head><body>{теги}</body></html>")

    _fdr_страница('<img src="assets/fdr-warn.png">')
    rc_fdr_w, вых_fdr_w = frame_density_run(fdr_dir)
    текст_fdr_w = "\n".join(вых_fdr_w)
    check("frame-recal ПРОГОН: страница с одним пограничным кадром -> rc=4 "
          "(WARN), в отчёте кадр назван поимённо с числами",
          rc_fdr_w == 4 and "fdr-warn.png" in текст_fdr_w
          and "пограничной зоне" in текст_fdr_w, текст_fdr_w)
    check("frame-recal ПРОГОН: rc=4 в карте кодов - это WARN, а WARN стадию не "
          "роняет (RC_FRAME)",
          RC_FRAME.get(4) == "WARN", str(RC_FRAME))
    _fdr_страница('<img src="assets/fdr-terminal.png">')
    rc_fdr_t, вых_fdr_t = frame_density_run(fdr_dir)
    check("frame-recal ПРОГОН: страница с терминальным кадром той же зоны -> "
          "rc=0, в отчёте видно, что сработало исключение аудита",
          rc_fdr_t == 0 and "исключение аудита" in "\n".join(вых_fdr_t),
          "\n".join(вых_fdr_t))
    _fdr_страница('<img src="assets/fdr-blok.png">')
    rc_fdr_b, вых_fdr_b = frame_density_run(fdr_dir)
    check("frame-recal ПРОГОН: кадр с block_pct 45 по-прежнему роняет гейт, rc=1",
          rc_fdr_b == 1 and "пустой блок в кадре" in "\n".join(вых_fdr_b),
          "\n".join(вых_fdr_b))

    # ── СТАДИЯ ЦЕЛИКОМ: пограничный кадр не блокирует публикацию ─────────────
    # Это и есть смысл перекалибровки: зона «решение человека» видна в расписке,
    # но конвейер по ней не встаёт
    fx_fdr = _fixture(os.path.join(root, "fdr-stage"),
                      page=FX_PAGE.replace("</body>",
                                           '<img src="assets/fdr-warn.png"></body>', 1))
    os.makedirs(os.path.join(fx_fdr["dir"], "assets"), exist_ok=True)
    shutil.copyfile(os.path.join(fdr_assets, "fdr-warn.png"),
                    os.path.join(fx_fdr["dir"], "assets", "fdr-warn.png"))
    rc_fdr_st = call(fx_fdr, fx_fdr["slug"], "--stage", "page")
    g_fdr_st = _гейт(fx_fdr, "page", "frame-density")
    d_fdr_st = json.load(open(os.path.join(fx_fdr["dir"], "gates.json"), encoding="utf-8"))
    check("frame-recal СТАДИЯ: пограничный кадр даёт гейту статус WARN, стадия "
          "page остаётся PASS и rc=0 - корпус-волна по этой зоне больше не стоит",
          g_fdr_st["status"] == "WARN"
          and d_fdr_st["stages"]["page"]["verdict"] == "PASS" and rc_fdr_st == 0,
          f"rc={rc_fdr_st} гейт={g_fdr_st['status']} "
          f"стадия={d_fdr_st['stages']['page']['verdict']}")

    # ── 24. ГЕЙТ cta-position: место финального призыва в хвосте (рв даты запуска.2026,
    # правка владельца - призыв стоял в подвале ЗА частыми вопросами). Фикстуры
    # СИНТЕТИЧЕСКИЕ, а не живые страницы корпуса: живую завтра пересоберут, и
    # тест начнёт мерить чужую работу вместо логики гейта ─────────────────────
    cp_dir = os.path.join(root, "cta-position")
    os.makedirs(cp_dir, exist_ok=True)
    _CP_CHK = ('<section id="checklist"><h2>Памятка</h2>'
               '<ul class="checklist"><li>шаг</li></ul></section>')
    _CP_CTA = ('<section class="cta cta-final"><h3>Дальше</h3>'
               '<p><a class="btn-cta" href="https://t.me/+cpFIXTURE">Кнопка</a></p></section>')
    _CP_FAQ = ('<section id="faq"><h2>Частые вопросы</h2>'
               '<details open><summary>вопрос</summary><p>ответ</p></details></section>')
    # ПРИМАНКИ. Ровно тот класс дефекта, что чинил tc_strip_comments по решению автора: в
    # page-template.html комментарии несут ПРИМЕРЫ разметки, а инлайн-CSS и JS -
    # имена классов строками. Обе приманки стоят ДО памятки: если гейт их
    # засчитает, позитивный кейс развалится в «призыв раньше памятки»
    _CP_ПРИМАНКИ = ('<!-- пример хвоста: <section class="cta cta-final">…</section> -->'
                    '<style>.cta-final{margin-top:0}</style>'
                    '<script>var шаблон = \'<div class="cta-final"></div>\';</script>')

    def _cp_страница(тело):
        путь = os.path.join(cp_dir, "index.html")
        with open(путь, "w", encoding="utf-8") as fh:
            fh.write("<html><head><title>t</title></head><body><article>"
                     + _CP_ПРИМАНКИ + тело + "</article></body></html>")
        return путь

    # ПОЗИТИВ: канонный порядок памятка -> призыв -> частые вопросы
    путь_поз = _cp_страница(_CP_CHK + _CP_CTA + _CP_FAQ)
    rc_cp_pos, вых_cp_pos = cta_position_run(cp_dir)
    текст_cp_pos = "\n".join(вых_cp_pos)
    check("cta-position ПОЗИТИВ: памятка -> призыв -> частые вопросы = PASS, rc=0",
          rc_cp_pos == 0 and "Порядок хвоста канонный" in текст_cp_pos, текст_cp_pos)
    _cp_сырьё = tc_read(путь_поз)
    _cp_фин = ctapos_positions(_cp_сырьё, dict(CTAPOS_BLOCKS)[CTAPOS_FIN])
    check("cta-position ПОЗИТИВ: приманки (пример разметки в комментарии, "
          ".cta-final в <style> и в строке <script>) за блоки не считаются - "
          "живых блоков 1 из 4 вхождений в байтах",
          rc_cp_pos == 0 and _cp_сырьё.count("cta-final") == 4
          and _cp_фин == [_cp_сырьё.rfind('<section class="cta cta-final"')],
          f"вхождений cta-final в байтах {_cp_сырьё.count('cta-final')}, "
          f"живых блоков {_cp_фин}\n{текст_cp_pos}")
    _cp_живой = tc_read(путь_поз)
    _cp_ожид = _cp_живой.find('<section id="checklist"')
    check("cta-position ПОЗИТИВ: позиции в отчёте - РЕАЛЬНЫЕ смещения в файле "
          "(сходятся с прямым поиском по байтам страницы)",
          _cp_ожид > 0 and f"позиции: {_cp_ожид}" in текст_cp_pos,
          f"ждали {_cp_ожид}\n{текст_cp_pos}")

    # НЕГАТИВ 1: БОЕВОЙ порядок дефекта - памятка, FAQ, и призыв в подвале
    _cp_страница(_CP_CHK + _CP_FAQ + _CP_CTA)
    rc_cp_neg, вых_cp_neg = cta_position_run(cp_dir)
    текст_cp_neg = "\n".join(вых_cp_neg)
    check("cta-position НЕГАТИВ (боевой порядок guide-bolt-new): призыв ПОСЛЕ "
          "частых вопросов роняет гейт в FAIL, rc=1",
          rc_cp_neg == 1 and "стоит ПОСЛЕ section#faq" in текст_cp_neg
          and "призыв в подвале" in текст_cp_neg, текст_cp_neg)
    check("cta-position НЕГАТИВ: причина поимённая и с ПОЗИЦИЯМИ обоих блоков",
          all(str(x) in текст_cp_neg for x in
              (ctapos_positions(tc_read(os.path.join(cp_dir, "index.html")),
                                dict(CTAPOS_BLOCKS)[CTAPOS_FIN])[0],
               ctapos_positions(tc_read(os.path.join(cp_dir, "index.html")),
                                dict(CTAPOS_BLOCKS)[CTAPOS_FAQ])[0])), текст_cp_neg)

    # НЕГАТИВ 2: призыв РАНЬШЕ памятки - вторая ветка порядка
    _cp_страница(_CP_CTA + _CP_CHK + _CP_FAQ)
    rc_cp_rano, вых_cp_rano = cta_position_run(cp_dir)
    check("cta-position НЕГАТИВ: призыв ДО памятки = FAIL с той же поимённой причиной",
          rc_cp_rano == 1 and "стоит ДО section#checklist" in "\n".join(вых_cp_rano),
          "\n".join(вых_cp_rano))

    # НЕГАТИВ 3: второй экземпляр призыва уехал в подвал (первый на месте)
    _cp_страница(_CP_CHK + _CP_CTA + _CP_FAQ + _CP_CTA)
    rc_cp_два, вых_cp_два = cta_position_run(cp_dir)
    check("cta-position НЕГАТИВ: ВТОРОЙ призыв в подвале ловится, хотя первый "
          "стоит канонно (проверяется каждый блок, не только первый)",
          rc_cp_два == 1 and "найдено 2" in "\n".join(вых_cp_два)
          and "призыв в подвале" in "\n".join(вых_cp_два), "\n".join(вых_cp_два))

    # НЕГАТИВ 4-6: отсутствие каждого из трёх блоков по очереди
    for имя_кейса, тело, ждём in (
            ("нет призыва", _CP_CHK + _CP_FAQ, CTAPOS_FIN),
            ("нет памятки", _CP_CTA + _CP_FAQ, CTAPOS_CHK),
            ("нет частых вопросов", _CP_CHK + _CP_CTA, CTAPOS_FAQ)):
        _cp_страница(тело)
        rc_cp_н, вых_cp_н = cta_position_run(cp_dir)
        check(f"cta-position НЕГАТИВ ({имя_кейса}): FAIL с поимённым «ОТСУТСТВУЕТ "
              f"{ждём}», rc=1",
              rc_cp_н == 1 and f"ОТСУТСТВУЕТ: {ждём}" in "\n".join(вых_cp_н),
              "\n".join(вых_cp_н))

    # ОШИБКА ВХОДА: нет собранной страницы вовсе - вердикт не выдумывается
    cp_нет = os.path.join(root, "cta-position-net-page")
    os.makedirs(cp_нет, exist_ok=True)
    rc_cp_нет, вых_cp_нет = cta_position_run(cp_нет)
    check("cta-position: нет index.html - гейт не выдумывает вердикт, rc=2",
          rc_cp_нет == 2, "\n".join(вых_cp_нет))

    # ИНТЕГРАЦИЯ: гейт реально стоит в стадии page конвейера и исполняется -
    # переиспользуем отчёт fx_cta из раздела 20 (FX_PAGE несёт канонный хвост)
    g_cp_wired = [g for g in d_cta["stages"]["page"]["gates"]
                  if g["name"] == "cta-position"]
    check("cta-position: гейт стоит в стадии page реального конвейера, обязателен "
          "и реально исполнился на фикстуре (не SKIP)",
          len(g_cp_wired) == 1 and g_cp_wired[0]["status"] == "PASS"
          and g_cp_wired[0]["required"] is True, str(g_cp_wired[:1]))

    # ── 24а. ГЕЙТ-НЕГАТИВ toc-mobile: удалённое оглавление-кнопка не вернулось
    # (рв даты запуска.2026, оснастка выведена из канона целиком).
    # Фикстуры СИНТЕТИЧЕСКИЕ по той же причине, что у cta-position ───
    tm_dir = os.path.join(root, "toc-mobile")
    os.makedirs(tm_dir, exist_ok=True)
    _TM_DESK = ('<aside class="toc-desktop" aria-label="Содержание">'
                '<p class="toc-title">Содержание</p><ul class="toc-list">'
                '<li><a href="#s1">Раздел один</a></li>'
                '<li><a href="#s2">Раздел два</a></li></ul></aside>')
    _TM_BLOCK = ('<details class="toc-mobile" open><summary>Содержание</summary>'
                 '<ul class="toc-list"><li><a href="#s1">Раздел один</a></li>'
                 '<li><a href="#s2">Раздел два</a></li></ul></details>')
    # ПРИМАНКИ: тумбстоун-комментарий шаблона, мёртвое правило в инлайн-CSS и
    # строка в JS. Ровно то, что остаётся на СТАРЫХ страницах после ножа корпуса:
    # если гейт их засчитает, ни одна вылеченная страница не получит PASS
    _TM_ПРИМАНКИ = ('<!-- по решению автора: тут стоял <details class="toc-mobile"> - удалён -->'
                    '<style>.toc-mobile{display:none}.toc-fab{opacity:0}</style>'
                    '<script>var tocm = document.querySelector(\'.toc-mobile\');</script>')

    def _tm_страница(тело):
        путь = os.path.join(tm_dir, "index.html")
        with open(путь, "w", encoding="utf-8") as fh:
            fh.write("<html><head><title>t</title></head><body>" + _TM_ПРИМАНКИ
                     + тело + '<article><section id="s1"><h2>Раздел один</h2></section>'
                       '<section id="s2"><h2>Раздел два</h2></section></article>'
                       "</body></html>")
        return путь

    # ПОЗИТИВ: одна липкая колонка, мобильного блока нет - при трёх приманках
    путь_tm_поз = _tm_страница(_TM_DESK)
    rc_tm_pos, вых_tm_pos = toc_mobile_run(tm_dir)
    текст_tm_pos = "\n".join(вых_tm_pos)
    _tm_сырьё = tc_read(путь_tm_поз)
    check("toc-mobile ПОЗИТИВ: страница с одним aside.toc-desktop = PASS, rc=0, "
          "и приманки (тумбстоун-комментарий, правило в <style>, строка в "
          "<script>) блоком НЕ считаются - иначе вылеченные страницы корпуса "
          "никогда не дали бы PASS",
          rc_tm_pos == 0 and "Мобильного оглавления-кнопки на странице нет"
          in текст_tm_pos and _tm_сырьё.count("toc-mobile") == 3,
          f"вхождений toc-mobile в байтах {_tm_сырьё.count('toc-mobile')}\n{текст_tm_pos}")
    check("toc-mobile ПОЗИТИВ: липкая колонка видна гейту справочно (её удалять "
          "НЕ приказывали - без этой строки нельзя отличить «мобильного нет» от "
          "«оглавления нет вовсе»)",
          f"{TOCM_DESK} (липкая колонка, справочно): найдено 1" in текст_tm_pos,
          текст_tm_pos)

    # НЕГАТИВ 1: боевой блок вернулся в тело
    _tm_страница(_TM_DESK + _TM_BLOCK)
    rc_tm_neg, вых_tm_neg = toc_mobile_run(tm_dir)
    текст_tm_neg = "\n".join(вых_tm_neg)
    # rfind, а не find: ПЕРВОЕ вхождение этой подстроки в байтах - приманка в
    # тумбстоун-комментарии, и гейт обязан назвать позицию ЖИВОГО блока
    _tm_ждём = tc_read(os.path.join(tm_dir, "index.html")).rfind('<details class="toc-mobile"')
    check("toc-mobile НЕГАТИВ: вернувшийся details.toc-mobile роняет гейт в FAIL, "
          "rc=1, причина с РЕАЛЬНОЙ позицией в байтах",
          rc_tm_neg == 1 and "ВЕРНУЛСЯ details.toc-mobile" in текст_tm_neg
          and str(_tm_ждём) in текст_tm_neg, f"ждали {_tm_ждём}\n{текст_tm_neg}")

    # НЕГАТИВ 2: тот же блок под ДРУГИМ тегом - возврат по смыслу, не по тегу
    _tm_страница(_TM_DESK + _TM_BLOCK.replace("details", "nav").replace(
        "<summary>Содержание</summary>", "<p>Содержание</p>"))
    rc_tm_nav, вых_tm_nav = toc_mobile_run(tm_dir)
    check("toc-mobile НЕГАТИВ: тот же блок под <nav class=\"toc-mobile\"> тоже "
          "FAIL - гейт ловит КЛАСС оснастки, а не один тег",
          rc_tm_nav == 1 and "ВЕРНУЛСЯ" in "\n".join(вых_tm_nav), "\n".join(вых_tm_nav))

    # НЕГАТИВ 3: два блока разом - считается каждый, не только первый
    _tm_страница(_TM_DESK + _TM_BLOCK + _TM_BLOCK)
    rc_tm_два, вых_tm_два = toc_mobile_run(tm_dir)
    check("toc-mobile НЕГАТИВ: ДВА блока = FAIL и оба названы поимённо",
          rc_tm_два == 1 and "найдено 2" in "\n".join(вых_tm_два)
          and "\n".join(вых_tm_два).count("ВЕРНУЛСЯ") == 2, "\n".join(вых_tm_два))

    # ОШИБКА ВХОДА: нет собранной страницы вовсе
    tm_нет = os.path.join(root, "toc-mobile-net-page")
    os.makedirs(tm_нет, exist_ok=True)
    rc_tm_нет, вых_tm_нет = toc_mobile_run(tm_нет)
    check("toc-mobile: нет index.html - гейт не выдумывает вердикт, rc=2",
          rc_tm_нет == 2, "\n".join(вых_tm_нет))

    # ИНТЕГРАЦИЯ: гейт реально стоит в стадии page конвейера и исполняется
    g_tm_wired = [g for g in d_cta["stages"]["page"]["gates"]
                  if g["name"] == "toc-mobile"]
    check("toc-mobile: гейт стоит в стадии page реального конвейера, обязателен "
          "и реально исполнился на фикстуре (не SKIP)",
          len(g_tm_wired) == 1 and g_tm_wired[0]["status"] == "PASS"
          and g_tm_wired[0]["required"] is True, str(g_tm_wired[:1]))

    # ── 24-бис. ГЕЙТ frame-provenance: происхождение кадра (по решению автора) ───────
    # Фикстуры СИНТЕТИЧЕСКИЕ по той же причине, что у cta-position/toc-mobile:
    # гейт читает РАЗМЕТКУ и json рядом, никаких пикселей ему не нужно.
    print(" --- frame-provenance: происхождение кадров (закон по решению автора) ---")
    pv_dir = os.path.join(root, "provenance")
    os.makedirs(pv_dir, exist_ok=True)
    _PV_PAGE = (
        '<html><head><title>t</title>'
        '<meta property="og:image" content="https://site.test/provenance/assets/pv-og.jpg" />'
        '</head><body>'
        # ВНЕ ЗОНЫ: пиксель метрики (чужой домен)
        '<img src="https://mc.yandex.ru/watch/1" alt="" />'
        '<figure class="article-hero"><picture>'
        '<source type="image/webp" srcset="assets/pv-hero.webp" />'
        '<img src="assets/pv-hero.jpg" alt="хиро" /></picture></figure>'
        '<figure class="fig"><img src="assets/pv-step1.jpg" alt="шаг" /></figure>'
        # ВНЕ ЗОНЫ: кадр внутри .vizblock - это свёрстанный блок, а не снимок
        '<div class="vizblock vizsteps"><p class="vizblock-title">шаги</p>'
        '<img src="assets/pv-vnutri-vizbloka.jpg" alt="вёрстка" /></div>'
        # ВНЕ ЗОНЫ: превью карточки «Читайте также», корневой путь, вектор-иконка
        '<img class="rc-thumb" src="assets/thumb-sosed.webp" alt="карточка" />'
        '<img src="/assets/avatar.png" alt="аватар" />'
        '<img src="assets/icon-strelka.svg" alt="иконка" />'
        '</body></html>')
    _pv_page_path = os.path.join(pv_dir, "index.html")
    with open(_pv_page_path, "w", encoding="utf-8") as fh:
        fh.write(_PV_PAGE)

    def _pv_manifest(frames):
        with open(os.path.join(pv_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
            json.dump({"frames": frames}, fh, ensure_ascii=False)

    _pv_кадры = prov_page_frames(_PV_PAGE, "provenance")
    check("frame-provenance ЗОНА: считаны ровно три кадра (хиро, кадр тела, og); "
          "пиксель метрики, .vizblock, rc-thumb, корневой путь и svg-иконка - вне зоны",
          [f["key"] for f in _pv_кадры] == ["pv-hero", "pv-step1", "pv-og"],
          str([(f["key"], f["role"]) for f in _pv_кадры]))
    check("frame-provenance: hero.webp и hero.jpg - ОДИН кадр (один кадр = одно "
          "имя без расширения, тот же счёт, что у frame-density)",
          sum(1 for f in _pv_кадры if f["key"] == "pv-hero") == 1,
          str([f["ref"] for f in _pv_кадры]))

    rc_pv_нет, вых_pv_нет = frame_provenance_run(pv_dir)
    check("frame-provenance МЯГКО (дефолт): манифеста нет - rc=4, а RC_PROV[4] = "
          "WARN, то есть стадию НЕ роняет (живой корпус без манифестов остаётся "
          "зелёным, риск 4 плана)",
          rc_pv_нет == 4 and RC_PROV.get(4) == "WARN"
          and "без_записи=3" in "\n".join(вых_pv_нет),
          f"rc={rc_pv_нет}\n" + "\n".join(вых_pv_нет))
    rc_pv_замок, _ = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance ЗАМОК: тот же вход под --provenance-hard = rc=1 (FAIL)",
          rc_pv_замок == 1 and RC_PROV.get(1) == "FAIL", f"rc={rc_pv_замок}")
    rc_pv_отчёт, вых_pv_отчёт = frame_provenance_run(pv_dir, hard=True, report=True)
    check("frame-provenance ОТЧЁТ: --provenance-report не роняет ничего даже "
          "поверх замка (rc=0) и печатает машинную строку СВОДКА - ею меряется корпус",
          rc_pv_отчёт == 0 and any(l.strip().startswith("СВОДКА") for l in вых_pv_отчёт),
          f"rc={rc_pv_отчёт}")

    # ПОЗИТИВ: записи есть у всех трёх кадров, поиск идёт ПО ИМЕНИ БЕЗ РАСШИРЕНИЯ
    # (в манифесте .webp, на странице .jpg - это один кадр)
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "result", "mode": "url",
         "url": "https://site.test/app/result", "steps": 3, "shot_at": "2026-08-22"},
        {"file": "assets/pv-step1.webp", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22"},
        {"file": "assets/pv-og.jpg", "class": "inherited", "mode": "relay",
         "url": "-", "steps": 0, "shot_at": "2026-08-19"}])
    rc_pv_ок, вых_pv_ок = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance ПОЗИТИВ: у каждого кадра запись легального класса = "
          "rc=0 даже под замком, и счётчик унаследованных кадров печатается",
          rc_pv_ок == 0
          and "унаследованных кадров (class=inherited): 1" in "\n".join(вых_pv_ок),
          f"rc={rc_pv_ок}\n" + "\n".join(вых_pv_ок))

    # НЕГАТИВ: класс вне списка = кадр непокрыт (генеративная сцена и любой
    # самодельный класс сюда же)
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "generated", "mode": "url", "url": "-"},
        {"file": "assets/pv-step1.jpg", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "url", "url": "-"}])
    rc_pv_класс, вых_pv_класс = frame_provenance_run(pv_dir)
    check("frame-provenance НЕГАТИВ: класс вне списка result/step/own-run/"
          "inherited считается кадром без легальной записи (мягко rc=4), и "
          "чужой класс назван поимённо",
          rc_pv_класс == 4 and "чужой_класс=1" in "\n".join(вых_pv_класс)
          and "«generated»" in "\n".join(вых_pv_класс), "\n".join(вых_pv_класс))

    # КОРЕНЬ СЕРВИСА: result показывает главную вместо результата функции - то, что
    # закон владельца называет полумерой. Р5-по решению автора: под замком это FAIL (раньше
    # признак не ронял статью никогда, судьёй оставался тот же агент, что снимал
    # кадр), в мягком режиме - по-прежнему замечание
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "result", "mode": "url",
         "url": "https://site.test/"},
        {"file": "assets/pv-step1.jpg", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "url", "url": "-"}])
    rc_pv_корень, вых_pv_корень = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance ЗАМОК: class=result с адресом КОРНЯ сервиса = FAIL "
          "(rc=1) - «скрин главной» вместо результата функции, кадры при этом "
          "покрыты все (без_записи=0)",
          rc_pv_корень == 1 and RC_PROV.get(1) == "FAIL"
          and "с_записью=3" in "\n".join(вых_pv_корень)
          and "корень_сервиса=1" in "\n".join(вых_pv_корень)
          and "не главная" in "\n".join(вых_pv_корень),
          f"rc={rc_pv_корень}\n" + "\n".join(вых_pv_корень))
    rc_pv_корень_м, вых_pv_корень_м = frame_provenance_run(pv_dir)
    check("frame-provenance МЯГКО: тот же корневой url = WARN (rc=4) - конвейер "
          "живого корпуса замком по умолчанию не останавливаем",
          rc_pv_корень_м == 4 and RC_PROV.get(4) == "WARN"
          and "корень_сервиса=1" in "\n".join(вых_pv_корень_м)
          and "стадию не роняем" in "\n".join(вых_pv_корень_м),
          f"rc={rc_pv_корень_м}\n" + "\n".join(вых_pv_корень_м))

    # УЗОСТЬ правки: второй признак того же класса - «у кейс-превью не назван адрес
    # функции» - замком НЕ ловится (пустой url бывает у честной съёмки своего
    # экрана) и остаётся WARN в обоих режимах
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "result", "mode": "url", "url": "-"},
        {"file": "assets/pv-step1.jpg", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "url", "url": "-"}])
    rc_pv_безадреса, вых_pv_безадреса = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance УЗОСТЬ: «у кейс-превью не назван адрес функции» под "
          "замком остаётся WARN (rc=4), корень_сервиса=0 - замок поднимает ровно "
          "один признак, а не все замечания класса result",
          rc_pv_безадреса == 4 and "корень_сервиса=0" in "\n".join(вых_pv_безадреса)
          and "замечаний=1" in "\n".join(вых_pv_безадреса)
          and "не назван адрес функции" in "\n".join(вых_pv_безадреса),
          f"rc={rc_pv_безадреса}\n" + "\n".join(вых_pv_безадреса))

    # САМОДЕКЛАРАЦИЯ (р8-по решению автора, находка панели Ф6): легального класса мало.
    # Проверяются оба новых признака записи и ОБРАТНАЯ сторона - что чистая запись
    # shot.py от них не краснеет (гейт, который врёт, учат не читать)
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "result", "mode": "url",
         "url": "https://site.test/app/result", "steps": 3, "shot_at": "2026-08-22"},
        # запись рукописная: shot.py поле mode пишет всегда, здесь его нет
        {"file": "assets/pv-step1.jpg", "class": "step",
         "url": "https://site.test/app/upload", "shot_at": "2026-08-22"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "url", "url": "-",
         "steps": 0, "shot_at": "2026-08-22"}])
    rc_pv_безрежима, вых_pv_безрежима = frame_provenance_run(pv_dir)
    rc_pv_безрежима_з, _ = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance САМОДЕКЛАРАЦИЯ: запись без поля mode = кадр непокрыт "
          "(мягко rc=4 / замок rc=1) - рукописная строка от записи shot.py "
          "отделена, легального класса на ней мало",
          rc_pv_безрежима == 4 and rc_pv_безрежима_з == 1
          and "без_режима=1" in "\n".join(вых_pv_безрежима)
          and "с_записью=2" in "\n".join(вых_pv_безрежима)
          and "запись сделана не shot.py" in "\n".join(вых_pv_безрежима),
          f"rc={rc_pv_безрежима}/{rc_pv_безрежима_з}\n" + "\n".join(вых_pv_безрежима))

    # ЗАКРЫТЫЙ КАНАЛ: живой прецедент корпуса - hero класса own-run, а текст записи
    # сам называет генератор обложек. Легальный класс поверх такого текста ничего
    # не отмывает: закон по решению автора канал закрыл
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "own-run", "mode": "url", "url": "-",
         "steps": 0, "shot_at": "2026-08-22",
         "note": "фирменная обложка 1200x630, собрана локально: og_hero.py --variant paper"},
        {"file": "assets/pv-step1.jpg", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "url", "url": "-",
         "steps": 0, "shot_at": "2026-08-22"}])
    rc_pv_канал, вых_pv_канал = frame_provenance_run(pv_dir)
    rc_pv_канал_з, _ = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance ЗАКРЫТЫЙ КАНАЛ: текст записи называет og_hero - кадр "
          "непокрыт при легальном классе own-run (мягко rc=4 / замок rc=1), канал "
          "назван поимённо",
          rc_pv_канал == 4 and rc_pv_канал_з == 1
          and "закрытый_канал=1" in "\n".join(вых_pv_канал)
          and "закрытый канал в записи: og_hero" in "\n".join(вых_pv_канал)
          and "с_записью=2" in "\n".join(вых_pv_канал),
          f"rc={rc_pv_канал}/{rc_pv_канал_з}\n" + "\n".join(вых_pv_канал))

    # ОБРАТНАЯ СТОРОНА: честная запись shot.py (класс, режим, шаги, дата, живая
    # заметка о результате функции) проходит замок насквозь - словарь закрытых
    # каналов не красит нормальную съёмку
    _pv_manifest([
        {"file": "assets/pv-hero.webp", "class": "result", "mode": "url",
         "url": "https://site.test/app/result", "steps": 1, "shot_at": "2026-08-22",
         "note": "результат функции: счётчик 3 014 752 -> 34 199, снято shot.py"},
        {"file": "assets/pv-step1.jpg", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22",
         "note": "путь клика: рамка «жми сюда» на кнопке загрузки"},
        {"file": "assets/pv-og.jpg", "class": "own-run", "mode": "external",
         "url": "-", "steps": 0, "shot_at": "2026-08-22",
         "note": "кроп 1200x630 с того же кадра, вшитого текста нет"}])
    rc_pv_честно, вых_pv_честно = frame_provenance_run(pv_dir, hard=True)
    check("frame-provenance ЧИСТАЯ ЗАПИСЬ shot.py: класс + mode + живая заметка "
          "проходят даже под замком (rc=0, закрытый_канал=0, без_режима=0) - новые "
          "признаки честную съёмку не красят",
          rc_pv_честно == 0
          and "закрытый_канал=0" in "\n".join(вых_pv_честно)
          and "без_режима=0" in "\n".join(вых_pv_честно)
          and "с_записью=3" in "\n".join(вых_pv_честно),
          f"rc={rc_pv_честно}\n" + "\n".join(вых_pv_честно))

    # ЗАКРЫТЫЙ КАНАЛ В ИМЕНИ КАДРА (р9-по решению автора): признак не должен зависеть от
    # манифеста - живой прецедент показал, что удалить запись дешевле, чем
    # переснять кадр. Фикстура даёт кадру ЛЕГАЛЬНУЮ и чистую запись shot.py: если
    # гейт судит только запись, он промолчит
    pv_имя_dir = os.path.join(root, "provenance-imya")
    os.makedirs(pv_имя_dir, exist_ok=True)
    _PV_NAME_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero"><img src="assets/nm-hero.webp" alt="хиро" /></figure>'
        '<figure class="fig"><img src="assets/nm-mokap-moy-nalog.webp" alt="мокап" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_имя_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_NAME_PAGE)
    with open(os.path.join(pv_имя_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/nm-hero.webp", "class": "result", "mode": "url",
             "url": "https://site.test/app/result", "steps": 1,
             "shot_at": "2026-08-23", "note": "результат функции"},
            {"file": "assets/nm-mokap-moy-nalog.webp", "class": "step",
             "mode": "scenario", "url": "https://site.test/app/step", "steps": 2,
             "shot_at": "2026-08-23", "note": "путь клика"}]}, fh, ensure_ascii=False)
    rc_nm, вых_nm = frame_provenance_run(pv_имя_dir)
    rc_nm_з, _ = frame_provenance_run(pv_имя_dir, hard=True)
    check("frame-provenance ИМЯ КАДРА: `-mokap-` в имени = закрытый канал даже при "
          "чистой записи shot.py (мягко rc=4 / замок rc=1), признак не гасится "
          "манифестом и назван поимённо",
          rc_nm == 4 and rc_nm_з == 1
          and "закрытый_канал_имя=1" in "\n".join(вых_nm)
          and "закрытый канал в имени кадра" in "\n".join(вых_nm)
          and "mokap" in "\n".join(вых_nm)
          and "с_записью=1" in "\n".join(вых_nm),
          f"rc={rc_nm}/{rc_nm_з}\n" + "\n".join(вых_nm))

    # ОБРАТНАЯ СТОРОНА: честное имя не краснеет. Оба кадра - ближние промахи
    # словаря: `karta` слово СЛАГА статьи (11 таких кадров в корпусе), а в
    # `meshy-discover` токен cover сидит ВНУТРИ слова - левая граница его не пускает
    pv_чимя_dir = os.path.join(root, "provenance-chestnoe-imya")
    os.makedirs(pv_чимя_dir, exist_ok=True)
    _PV_OK_NAME_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero"><img src="assets/guide-karta-hero.webp" alt="хиро" /></figure>'
        '<figure class="fig"><img src="assets/meshy-discover.webp" alt="экран" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_чимя_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_OK_NAME_PAGE)
    with open(os.path.join(pv_чимя_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/guide-karta-hero.webp", "class": "result", "mode": "url",
             "url": "https://site.test/app/result", "steps": 1,
             "shot_at": "2026-08-23", "note": "результат функции"},
            {"file": "assets/meshy-discover.webp", "class": "own-run",
             "mode": "external", "url": "-", "steps": 0, "shot_at": "2026-08-23",
             "note": "свой экран"}]}, fh, ensure_ascii=False)
    rc_чимя, вых_чимя = frame_provenance_run(pv_чимя_dir, hard=True)
    check("frame-provenance ЧЕСТНОЕ ИМЯ: слово слага (guide-karta-hero) и токен "
          "внутри слова (meshy-discover) закрытым каналом НЕ считаются - rc=0 под "
          "замком, закрытый_канал_имя=0",
          rc_чимя == 0
          and "закрытый_канал_имя=0" in "\n".join(вых_чимя)
          and "с_записью=2" in "\n".join(вых_чимя),
          f"rc={rc_чимя}\n" + "\n".join(вых_чимя))

    # ── ЧУЖАЯ ВИТРИНА В ОБЛОЖКЕ (рв даты запуска.2026, дефект T1 круга 2) ──────────
    # Пара стендов на ОДНОМ признаке: неисправленная половина и исправленная.
    # Дословная строка расхождения объявлена заранее: «ЧУЖАЯ ВИТРИНА»
    #
    # Стенд А, НЕИСПРАВЛЕННАЯ половина: живой прод-случай в фикстуре. Статья про
    # учёбу с ChatGPT, а хиро и og сняты со страницы стороннего издания
    # explainx.ai. Запись о съёмке ЛЕГАЛЬНА по всем прежним признакам: класс
    # result, режим url, дата, note - именно поэтому прежний гейт печатал OK
    pv_чуж_dir = os.path.join(root, "guide-chatgpt-ucheba-2026")
    os.makedirs(pv_чуж_dir, exist_ok=True)
    _PV_CHUZH_PAGE = (
        '<html><head><title>Учёба с ChatGPT: что поменялось в 2026 году</title>'
        '<meta name="keywords" content="chatgpt учёба, режим учёбы, родительский контроль" />'
        '</head><body><h1>Учёба с ChatGPT</h1>'
        '<figure class="article-hero">'
        '<img src="assets/chatgpt-ucheba-2026-hero.webp" alt="хиро" /></figure>'
        '<figure class="fig"><img src="assets/shot-teens.webp" alt="кадр" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_чуж_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_CHUZH_PAGE)
    with open(os.path.join(pv_чуж_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/chatgpt-ucheba-2026-hero.webp", "class": "result",
             "mode": "url", "steps": 1, "shot_at": "2026-08-30",
             "url": "https://explainx.ai/blog/chatgpt-for-teens-safety-study-mode",
             "note": "страница разбора выхода подростковой версии"},
            {"file": "assets/shot-teens.webp", "class": "result", "mode": "url",
             "steps": 1, "shot_at": "2026-08-30",
             "url": "https://explainx.ai/blog/chatgpt-for-teens-safety-study-mode",
             "note": "тот же разбор"}]}, fh, ensure_ascii=False)
    rc_чуж, вых_чуж = frame_provenance_run(pv_чуж_dir)
    rc_чуж_з, _ = frame_provenance_run(pv_чуж_dir, hard=True)
    check("frame-provenance ЧУЖАЯ ВИТРИНА (стенд А, неисправленная половина): "
          "хиро снят с explainx.ai, а предмет статьи этот домен не называет - "
          "FAIL (rc=1) И В МЯГКОМ РЕЖИМЕ тоже, хост назван поимённо. Прежние "
          "признаки при этом зелёные: запись есть, класс легальный, режим url",
          rc_чуж == 1 and rc_чуж_з == 1
          and "ЧУЖАЯ ВИТРИНА" in "\n".join(вых_чуж)
          and "explainx.ai" in "\n".join(вых_чуж)
          and "чужая_витрина_обложка=1" in "\n".join(вых_чуж),
          f"rc={rc_чуж}/{rc_чуж_з}\n" + "\n".join(вых_чуж))

    # Стенд Б, ИСПРАВЛЕННАЯ половина: те же кадры, но сняты у ПЕРВОИСТОЧНИКА
    # темы (openai.com). Домен-токен `openai` предмет статьи называет - keywords
    # и h1. Строки «ЧУЖАЯ ВИТРИНА» в выводе быть не должно
    pv_свой_dir = os.path.join(root, "guide-chatgpt-ucheba-ispravlennaya")
    os.makedirs(pv_свой_dir, exist_ok=True)
    _PV_SVOY_PAGE = (
        '<html><head><title>Учёба с ChatGPT от OpenAI: что поменялось</title>'
        '<meta name="keywords" content="chatgpt учёба, openai, режим учёбы" />'
        '</head><body><h1>Учёба с ChatGPT от OpenAI</h1>'
        '<figure class="article-hero">'
        '<img src="assets/chatgpt-ucheba-hero.webp" alt="хиро" /></figure>'
        '<figure class="fig"><img src="assets/shot-teens.webp" alt="кадр" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_свой_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_SVOY_PAGE)
    with open(os.path.join(pv_свой_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/chatgpt-ucheba-hero.webp", "class": "result",
             "mode": "url", "steps": 1, "shot_at": "2026-08-30",
             "url": "https://openai.com/index/chatgpt-study-mode/",
             "note": "страница первоисточника про режим учёбы"},
            {"file": "assets/shot-teens.webp", "class": "own-run", "mode": "url",
             "steps": 1, "shot_at": "2026-08-30",
             "url": "https://openai.com/index/chatgpt-study-mode/",
             "note": "тот же первоисточник"}]}, fh, ensure_ascii=False)
    rc_свой, вых_свой = frame_provenance_run(pv_свой_dir, hard=True)
    check("frame-provenance ЧУЖАЯ ВИТРИНА (стенд Б, исправленная половина): кадры "
          "сняты у первоисточника openai.com, домен назван в keywords и h1 - "
          "rc=0 под замком, строки «ЧУЖАЯ ВИТРИНА» в выводе НЕТ, "
          "чужая_витрина_обложка=0",
          rc_свой == 0
          and "ЧУЖАЯ ВИТРИНА" not in "\n".join(вых_свой)
          and "чужая_витрина_обложка=0" in "\n".join(вых_свой)
          and "с_записью=2" in "\n".join(вых_свой),
          f"rc={rc_свой}\n" + "\n".join(вых_свой))

    # Стенд В: чужой кадр в ТЕЛЕ статьи - мягко WARN, под замком FAIL. Обложка
    # чиста, поэтому жёсткого приговора в мягком режиме тут быть не должно
    pv_тело_dir = os.path.join(root, "guide-sravnenie-servisov-2026")
    os.makedirs(pv_тело_dir, exist_ok=True)
    _PV_TELO_PAGE = (
        '<html><head><title>Сравнение сервисов сборки сайтов в 2026</title>'
        '<meta name="keywords" content="lovable, сборка сайта" /></head><body>'
        '<h1>Сравнение сервисов</h1>'
        '<figure class="article-hero"><img src="assets/lovable-hero.webp" alt="х" /></figure>'
        '<figure class="fig"><img src="assets/chuzhoy-razbor.webp" alt="к" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_тело_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_TELO_PAGE)
    with open(os.path.join(pv_тело_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/lovable-hero.webp", "class": "result", "mode": "url",
             "steps": 1, "shot_at": "2026-08-30",
             "url": "https://lovable.dev/pricing", "note": "тарифы предмета"},
            {"file": "assets/chuzhoy-razbor.webp", "class": "result", "mode": "url",
             "steps": 1, "shot_at": "2026-08-30",
             "url": "https://techcrunch.com/2026/08/29/lovable-round/",
             "note": "чужой разбор"}]}, fh, ensure_ascii=False)
    rc_тело, вых_тело = frame_provenance_run(pv_тело_dir)
    rc_тело_з, _ = frame_provenance_run(pv_тело_dir, hard=True)
    check("frame-provenance ЧУЖАЯ ВИТРИНА В ТЕЛЕ: кадр тела с techcrunch.com даёт "
          "WARN (rc=4) мягко и FAIL (rc=1) под замком, обложка при этом чистая "
          "(lovable.dev назван предметом) - чужая_витрина=1, обложка=0",
          rc_тело == 4 and rc_тело_з == 1
          and "чужая_витрина=1" in "\n".join(вых_тело)
          and "чужая_витрина_обложка=0" in "\n".join(вых_тело)
          and "techcrunch.com" in "\n".join(вых_тело),
          f"rc={rc_тело}/{rc_тело_з}\n" + "\n".join(вых_тело))

    # СЛОВО СЛОВАРЯ В САМОМ СЛАГЕ (рв даты запуска.2026): слаг про фотосток. Кадр снят
    # честно, имя начинается со слага - сегменты слага из матчинга выброшены, и
    # честная съёмка не краснеет. Второй кадр той же страницы несёт токен, которого
    # в слаге НЕТ, - он обязан покраснеть, иначе исключение выключило бы признак
    pv_слаг_dir = os.path.join(root, "guide-unsplash-alternativy")
    os.makedirs(pv_слаг_dir, exist_ok=True)
    _PV_SLUG_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero">'
        '<img src="assets/guide-unsplash-alternativy-hero.webp" alt="хиро" /></figure>'
        '<figure class="fig">'
        '<img src="assets/guide-unsplash-alternativy-step-1.webp" alt="шаг" /></figure>'
        '<figure class="fig">'
        '<img src="assets/guide-unsplash-alternativy-plashka.webp" alt="плашка" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_слаг_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_SLUG_PAGE)
    with open(os.path.join(pv_слаг_dir, PROV_MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"frames": [
            {"file": "assets/guide-unsplash-alternativy-hero.webp", "class": "result",
             "mode": "url", "url": "https://site.test/app/result", "steps": 1,
             "shot_at": "2026-08-23", "note": "результат функции"},
            {"file": "assets/guide-unsplash-alternativy-step-1.webp", "class": "step",
             "mode": "scenario", "url": "https://site.test/app/step", "steps": 2,
             "shot_at": "2026-08-23", "note": "путь клика"},
            {"file": "assets/guide-unsplash-alternativy-plashka.webp", "class": "step",
             "mode": "scenario", "url": "https://site.test/app/step", "steps": 2,
             "shot_at": "2026-08-23", "note": "путь клика"}]}, fh, ensure_ascii=False)
    rc_слаг, вых_слаг = frame_provenance_run(pv_слаг_dir)
    check("frame-provenance СЛАГ-ИСКЛЮЧЕНИЕ: токен словаря, стоящий в САМОМ слаге "
          "(guide-unsplash-alternativy), честные кадры не красит ни по имени, ни "
          "через поле file записи, а токен вне слага (-plashka) краснеет: кадров 3, "
          "с_записью=2, закрытый_канал_имя=1",
          rc_слаг == 4
          and "кадров=3 с_записью=2" in "\n".join(вых_слаг)
          and "закрытый_канал=1 закрытый_канал_имя=1" in "\n".join(вых_слаг)
          and "-> plashk" in "\n".join(вых_слаг)
          and "закрытый канал в записи" not in "\n".join(вых_слаг)
          and "ПЕРЕИМЕНОВАНИЕМ кадра" in "\n".join(вых_слаг),
          f"rc={rc_слаг}\n" + "\n".join(вых_слаг))

    # СВОЙ КАДР АБСОЛЮТНЫМ АДРЕСОМ (рв даты запуска.2026): `https://<домен>/<slug>/assets/`
    # в <figure> выпадал из зоны гейта целиком - ни записи с него не спрашивали, ни
    # имени. Чужой домен и общесайтовый корневой путь при этом обязаны остаться вне
    pv_абс_dir = os.path.join(root, "guide-abs")
    os.makedirs(pv_абс_dir, exist_ok=True)
    _PV_ABS_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero">'
        '<img src="https://site.test/guide-abs/assets/guide-abs-plashka.webp" alt="хиро" />'
        '</figure>'
        '<figure class="fig"><img src="https://chuzhoy.test/img/foto.webp" alt="чужой" />'
        '</figure>'
        '<figure class="fig"><img src="/assets/avatar.png" alt="аватар" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_абс_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_ABS_PAGE)
    _pv_абс_кадры = prov_page_frames(_PV_ABS_PAGE, "guide-abs")
    rc_абс, вых_абс = frame_provenance_run(pv_абс_dir, hard=True)
    check("frame-provenance ЗОНА: свой кадр АБСОЛЮТНЫМ адресом в figure остаётся в "
          "зоне гейта (чужой домен и корневой /assets/ - вне), и словарь имени по "
          "нему отрабатывает: замок = FAIL",
          [f["key"] for f in _pv_абс_кадры] == ["guide-abs-plashka"]
          and rc_абс == 1
          and "закрытый_канал_имя=1" in "\n".join(вых_абс),
          f"rc={rc_абс} кадры={[f['key'] for f in _pv_абс_кадры]}\n"
          + "\n".join(вых_абс))

    # СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА (рв даты запуска.2026): удалить манифест было дешевле,
    # чем переснять кадр, - брак сегодняшней сборки печатался тем же мягким «записи
    # нет», что и честный долг корпуса. Судятся ДВЕ даты (страница + файл кадра), и
    # на одной фикстуре проверяются все три состояния: свежая съёмка, пересборка
    # легаси (страница свежая, кадры старые - замер по корпусу: 113 страниц из 146)
    # и полное легаси
    pv_свеж_dir = os.path.join(root, "guide-svezhaya")
    os.makedirs(os.path.join(pv_свеж_dir, "assets"), exist_ok=True)
    _PV_FRESH_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero"><img src="assets/sv-hero.webp" alt="хиро" /></figure>'
        '</body></html>')
    _pv_свеж_страница = os.path.join(pv_свеж_dir, "index.html")
    _pv_свеж_кадр = os.path.join(pv_свеж_dir, "assets", "sv-hero.webp")
    with open(_pv_свеж_страница, "w", encoding="utf-8") as fh:
        fh.write(_PV_FRESH_PAGE)
    with open(_pv_свеж_кадр, "wb") as fh:
        fh.write(b"")              # гейт читает разметку и даты, не пиксели
    _pv_свеж_ts = datetime.datetime.combine(
        PROV_LAW_DATE + datetime.timedelta(days=1), datetime.time(12, 0)).timestamp()
    _pv_стар_ts = datetime.datetime.combine(
        datetime.date(2026, 8, 8), datetime.time(12, 0)).timestamp()
    os.utime(_pv_свеж_страница, (_pv_свеж_ts, _pv_свеж_ts))
    os.utime(_pv_свеж_кадр, (_pv_свеж_ts, _pv_свеж_ts))
    rc_свеж, вых_свеж = frame_provenance_run(pv_свеж_dir)
    rc_свеж_з, _ = frame_provenance_run(pv_свеж_dir, hard=True)
    check("frame-provenance СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА: страница собрана после "
          "по решению автора И файл кадра лёг на диск тогда же, манифеста рядом нет - "
          "именная строка, счётчик свежая_без_манифеста=1, мягко rc=4 / замок rc=1",
          rc_свеж == 4 and rc_свеж_з == 1
          and "свежая_без_манифеста=1" in "\n".join(вых_свеж)
          and "СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА" in "\n".join(вых_свеж)
          and "assets/sv-hero.webp" in "\n".join(вых_свеж)
          and "НЕ долг старого корпуса" in "\n".join(вых_свеж),
          f"rc={rc_свеж}/{rc_свеж_з}\n" + "\n".join(вых_свеж))
    os.utime(_pv_свеж_кадр, (_pv_стар_ts, _pv_стар_ts))
    rc_пересб, вых_пересб = frame_provenance_run(pv_свеж_dir)
    check("frame-provenance ПЕРЕСБОРКА ЛЕГАСИ: index.html свежий, но файл кадра "
          "лежит с даты до закона - признака НЕТ (иначе волна красила бы 115 "
          "страниц корпуса из 146), остался прежний мягкий WARN",
          rc_пересб == 4
          and "свежая_без_манифеста=0" in "\n".join(вых_пересб)
          and "СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА" not in "\n".join(вых_пересб),
          f"rc={rc_пересб}\n" + "\n".join(вых_пересб))
    os.utime(_pv_свеж_страница, (_pv_стар_ts, _pv_стар_ts))
    rc_стар, вых_стар = frame_provenance_run(pv_свеж_dir)
    check("frame-provenance ЛЕГАСИ: та же страница с датой сборки ДО закона "
          "(по решению автора) признака не поднимает - свежая_без_манифеста=0, прежний "
          "мягкий WARN про долг корпуса остался как был (rc=4)",
          rc_стар == 4
          and "свежая_без_манифеста=0" in "\n".join(вых_стар)
          and "СВЕЖАЯ СБОРКА БЕЗ МАНИФЕСТА" not in "\n".join(вых_стар)
          and "без_записи=1" in "\n".join(вых_стар),
          f"rc={rc_стар}\n" + "\n".join(вых_стар))

    # СТУПЕНИ srcset (р3-по решению автора): канон требует у картинки шире 760px две
    # ступени - `<кадр>-720.webp 720w, <кадр>.webp 1440w`. Это ОДНА съёмка, и
    # своей записи ступень не требует. Проверяются обе стороны правила: схлопнуть
    # ступень при живой базе И НЕ схлопнуть то, что ступенью не является
    # (`-403` без базы = самостоятельный кадр про ошибку, `-1` = нумерация кадров)
    pv_st_dir = os.path.join(root, "provenance-stupeni")
    os.makedirs(pv_st_dir, exist_ok=True)
    _PV_ST_PAGE = (
        '<html><head><title>t</title></head><body>'
        '<figure class="article-hero"><picture>'
        '<source type="image/webp" sizes="(min-width: 1200px) 720px, 100vw" '
        'srcset="assets/st-hero-720.webp 720w, assets/st-hero.webp 1440w" />'
        '<img src="assets/st-hero.jpg" alt="хиро" /></picture></figure>'
        # ступень БЕЗ базы: базы st-siro на странице и в манифесте нет
        '<figure class="fig"><img src="assets/st-siro-720.webp" alt="без базы" /></figure>'
        '<figure class="fig"><img src="assets/st-result.webp" alt="кадр" /></figure>'
        # нумерация кадров: одна цифра - НЕ ступень, отдельная съёмка
        '<figure class="fig"><img src="assets/st-result-1.webp" alt="кадр 1" /></figure>'
        '</body></html>')
    with open(os.path.join(pv_st_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_PV_ST_PAGE)

    def _pv_st_manifest(frames):
        with open(os.path.join(pv_st_dir, PROV_MANIFEST_NAME), "w",
                  encoding="utf-8") as fh:
            json.dump({"frames": frames}, fh, ensure_ascii=False)

    _pv_st_кадры = prov_page_frames(_PV_ST_PAGE, "provenance-stupeni")
    check("frame-provenance СТУПЕНИ: `-720` при живой базе схлопнут в базовый кадр, "
          "а `-720` БЕЗ базы и нумерация `-1` остаются самостоятельными кадрами",
          [f["key"] for f in _pv_st_кадры] == ["st-hero", "st-siro-720",
                                               "st-result", "st-result-1"]
          and _pv_st_кадры[0]["aliases"] == ["st-hero-720"]
          and _pv_st_кадры[0]["widths"] == ["720"],
          str([(f["key"], f["aliases"]) for f in _pv_st_кадры]))

    _pv_st_manifest([
        {"file": "assets/st-hero.webp", "class": "result", "mode": "url",
         "url": "https://site.test/app/result", "steps": 3, "shot_at": "2026-08-22"},
        {"file": "assets/st-siro-720.webp", "class": "own-run", "mode": "url",
         "url": "https://site.test/app/panel", "steps": 1, "shot_at": "2026-08-22"},
        {"file": "assets/st-result.webp", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22"},
        {"file": "assets/st-result-1.webp", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22"}])
    rc_st_ок, вых_st_ок = frame_provenance_run(pv_st_dir, hard=True)
    check("frame-provenance СТУПЕНИ: страница, собранная по канону (две ступени на "
          "кадр) при записи на БАЗОВЫЙ файл = rc=0 даже под замком, без_записи=0 - "
          "вечного WARN на каждом кадре тела больше нет",
          rc_st_ок == 0 and "без_записи=0" in "\n".join(вых_st_ок)
          and "кадров=4" in "\n".join(вых_st_ок)
          and "ступеней srcset схлопнуто в базовый кадр: 1" in "\n".join(вых_st_ок),
          f"rc={rc_st_ок}\n" + "\n".join(вых_st_ок))

    # запись сделана на ФАЙЛ СТУПЕНИ (st-hero-720) - кадр всё равно покрыт;
    # при этом запись на st-result НЕ закрывает st-result-1: это разные съёмки
    _pv_st_manifest([
        {"file": "assets/st-hero-720.webp", "class": "result", "mode": "url",
         "url": "https://site.test/app/result", "steps": 3, "shot_at": "2026-08-22"},
        {"file": "assets/st-siro-720.webp", "class": "own-run", "mode": "url",
         "url": "https://site.test/app/panel", "steps": 1, "shot_at": "2026-08-22"},
        {"file": "assets/st-result.webp", "class": "step", "mode": "scenario",
         "url": "https://site.test/app/upload", "steps": 2, "shot_at": "2026-08-22"}])
    rc_st_нум, вых_st_нум = frame_provenance_run(pv_st_dir)
    check("frame-provenance СТУПЕНИ: запись на файл ступени закрывает базовый кадр, "
          "а нумерация кадров не схлопывается - st-result-1 требует своей записи "
          "(мягко rc=4, назван поимённо)",
          rc_st_нум == 4 and "без_записи=1" in "\n".join(вых_st_нум)
          and "с_записью=3" in "\n".join(вых_st_нум)
          and "st-result-1.webp [кадр тела] -> записи" in "\n".join(вых_st_нум),
          f"rc={rc_st_нум}\n" + "\n".join(вых_st_нум))

    pv_нет_стр = os.path.join(root, "provenance-net-page")
    os.makedirs(pv_нет_стр, exist_ok=True)
    rc_pv_бн, _ = frame_provenance_run(pv_нет_стр)
    check("frame-provenance: нет index.html - гейт не выдумывает вердикт, rc=2",
          rc_pv_бн == 2, f"rc={rc_pv_бн}")

    # ИНТЕГРАЦИЯ: гейт реально стоит в стадии page конвейера и исполняется
    g_pv_wired = [g for g in d_cta["stages"]["page"]["gates"]
                  if g["name"] == "frame-provenance"]
    check("frame-provenance: гейт стоит в стадии page реального конвейера, "
          "обязателен и реально исполнился на фикстуре (не SKIP)",
          len(g_pv_wired) == 1 and g_pv_wired[0]["required"] is True
          and g_pv_wired[0]["status"] == "PASS", str(g_pv_wired[:1]))

    # ── 24-тер. ОТПЕЧАТОК НАБОРА ГЕЙТОВ (gate_set) ────────────────────────────
    # Дыра, которую он закрывает: расписка говорила «page=PASS» и молчала о том,
    # КАКИМИ гейтами - страницы с зелёным вердиктом от ПРОШЛОГО набора уезжали
    # мимо только что добавленного гейта.
    _gs_запись = d_cta["stages"]["page"]
    _gs_эталон = stage_gate_set(load_cfg(fx_cta["config"]), "page")
    check("gate_set: расписка стадии несёт сортированный список имён гейтов "
          "прогона и совпадает с эталоном стадии из build_gates()",
          _gs_запись.get("gate_set") == _gs_эталон
          and _gs_запись["gate_set"] == sorted(_gs_запись["gate_set"]),
          f"в расписке {_gs_запись.get('gate_set')}\nэталон {_gs_эталон}")
    check("gate_set: новый гейт frame-provenance входит и в расписку, и в эталон "
          "стадии page - расписка ПРОШЛОГО набора с этим эталоном не сойдётся",
          "frame-provenance" in _gs_запись.get("gate_set", [])
          and "frame-provenance" in _gs_эталон, str(_gs_эталон))
    check("gate_set: новый гейт image-refs (по решению автора) входит и в расписку, и в "
          "эталон стадии page - расписки корпуса, выписанные ДО него, дверь "
          "ftp_publish отвергнет и перегонит стадию сама",
          "image-refs" in _gs_запись.get("gate_set", [])
          and "image-refs" in _gs_эталон, str(_gs_эталон))
    check("gate_set: эталон стадии publish не тянет динамические имена "
          "claim-shared:<файл> - они зависят от списка разделяемых файлов "
          "КОНКРЕТНОГО прогона и эталоном набора быть не могут",
          not [n for n in stage_gate_set(load_cfg(fx_cta["config"]), "publish")
               if n.startswith("claim-shared:")],
          str(stage_gate_set(load_cfg(fx_cta["config"]), "publish")))

    # ── 25. ГЕЙТ novice: стандарт «понятно новичку» (рв даты запуска.2026) ──────────
    # Проверяется ДВОЙКОЙ: (а) проводка в конвейере - гейт есть на обеих
    # стадиях, обязателен, обходится флагом --skip-novice в SKIP, а не в тихий
    # PASS; (б) сам инструмент на СВОИХ фикстурах - боевым novice-check.py, а
    # не стабом, иначе тест доказывал бы работу заглушки.
    nv_tool = os.path.join(os.path.expanduser(FALLBACK["lm_tools"]), "novice-check.py")

    fx_nv = _fixture(os.path.join(root, "novice-wiring"))
    rc_nv = call(fx_nv, fx_nv["slug"], "--stage", "draft")
    d_nv = json.load(open(os.path.join(fx_nv["dir"], "gates.json"), encoding="utf-8"))
    g_nv = [g for g in d_nv["stages"]["draft"]["gates"] if g["name"] == "novice"]
    check("novice: гейт стоит в стадии draft, обязателен и реально исполнился "
          "(не SKIP)",
          rc_nv == 0 and len(g_nv) == 1 and g_nv[0]["required"] is True
          and g_nv[0]["status"] == "PASS", str(g_nv[:1]))
    rc_nv_p = call(fx_nv, fx_nv["slug"], "--stage", "page")
    d_nv_p = json.load(open(os.path.join(fx_nv["dir"], "gates.json"), encoding="utf-8"))
    g_nv_p = [g for g in d_nv_p["stages"]["page"]["gates"] if g["name"] == "novice"]
    check("novice: тот же гейт стоит и в стадии page (у 2/3 корпуса черновика "
          "нет вовсе, замок обязан быть на байтах страницы)",
          rc_nv_p == 0 and len(g_nv_p) == 1 and g_nv_p[0]["status"] == "PASS",
          str(g_nv_p[:1]))

    # ── qa-freshness (круг 13, по решению автора) ───────────────────────────────────
    # Класс возвращался ТРИЖДЫ на волне r14 (круги 5, 7, 12): расписка «смотрел
    # глазами» стояла по кадрам ПРОШЛОЙ сборки. Каждый раз проезжал бесплатно,
    # потому что qa_freshness.py не звал ни один гейт. Тесты ниже держат две
    # вещи: (1) ось реально стоит в стадии page и обязательна, (2) красный код
    # инструмента РОНЯЕТ стадию, а --revision его смягчает.
    fx_qf = _fixture(os.path.join(root, "qafresh"), codes={"qa_freshness": 1})
    rc_qf = call(fx_qf, fx_qf["slug"], "--stage", "page")
    d_qf = json.load(open(os.path.join(fx_qf["dir"], "gates.json"), encoding="utf-8"))
    g_qf = [g for g in d_qf["stages"]["page"]["gates"] if g["name"] == "qa-freshness"]
    check("qa-freshness: ось стоит в стадии page, обязательна, и протухшая "
          "приёмка (rc=1) РОНЯЕТ стадию - страница, которую никто не видел "
          "глазами в этой сборке, не может получить PASS",
          rc_qf == 1 and len(g_qf) == 1 and g_qf[0]["required"] is True
          and g_qf[0]["status"] == "FAIL", str(g_qf[:1]))

    fx_qfr = _fixture(os.path.join(root, "qafresh-rev"), codes={"qa_freshness": 1})
    rc_qfr = call(fx_qfr, fx_qfr["slug"], "--stage", "page", "--revision")
    d_qfr = json.load(open(os.path.join(fx_qfr["dir"], "gates.json"), encoding="utf-8"))
    g_qfr = [g for g in d_qfr["stages"]["page"]["gates"] if g["name"] == "qa-freshness"]
    check("qa-freshness: --revision смягчает ТОЛЬКО эту ось - у легаси-страницы "
          "протухшая приёмка даёт WARN и вердикт не роняет (калибровка по решению автора: "
          "жёстко корпус даёт 21 красную статью из 136, это переиздания)",
          rc_qfr == 0 and len(g_qfr) == 1 and g_qfr[0]["status"] == "WARN",
          f"rc={rc_qfr} {g_qfr[:1]}")

    fx_qf3 = _fixture(os.path.join(root, "qafresh-claim"), codes={"qa_freshness": 3})
    rc_qf3 = call(fx_qf3, fx_qf3["slug"], "--stage", "page")
    check("qa-freshness: расписка на кадр, которого нет на диске (rc=3), - тот "
          "же класс «улика названа, улики нет», стадия тоже краснеет",
          rc_qf3 == 1 and RC_QAFRESH[3] == "FAIL", f"rc={rc_qf3}")

    fx_qf2 = _fixture(os.path.join(root, "qafresh-none"), codes={"qa_freshness": 2})
    rc_qf2 = call(fx_qf2, fx_qf2["slug"], "--stage", "page")
    check("qa-freshness: приёмку не снимали вовсе (rc=2) - WARN, не FAIL: таких "
          "в корпусе 113 из 136, ось не топит легаси, но причина видна в отчёте",
          rc_qf2 == 0 and RC_QAFRESH[2] == "WARN", f"rc={rc_qf2}")

    # обход волной легаси-операций: SKIP с причиной, стадия не краснеет
    fx_nv_sk = _fixture(os.path.join(root, "novice-skip"), codes={"novice": 1})
    rc_sk_off = call(fx_nv_sk, fx_nv_sk["slug"], "--stage", "draft")
    check("novice: без обхода красный гейт РОНЯЕТ стадию (иначе обходить нечего)",
          rc_sk_off == 1, f"rc={rc_sk_off}")
    rc_sk = call(fx_nv_sk, fx_nv_sk["slug"], "--stage", "draft", "--skip-novice")
    d_sk = json.load(open(os.path.join(fx_nv_sk["dir"], "gates.json"), encoding="utf-8"))
    g_sk = [g for g in d_sk["stages"]["draft"]["gates"] if g["name"] == "novice"][0]
    check("novice: --skip-novice снимает ПОРОГОВЫЕ оси легаси - стадия зелёная, "
          "когда класс нулевой терпимости чист",
          rc_sk == 0 and g_sk["status"] == "PASS", f"rc={rc_sk} {g_sk['status']}")

    # ── дыра обхода закрыта (наряд R-48): флаг не снимает класс нулевой
    # терпимости. Стаб novice_zero=1 играет роль страницы, на которой ось 4
    # красная: под флагом гейт обязан УПАСТЬ, а не уйти в SKIP.
    fx_nv_zero = _fixture(os.path.join(root, "novice-skip-zero"),
                          codes={"novice": 1, "novice_zero": 1})
    rc_zero = call(fx_nv_zero, fx_nv_zero["slug"], "--stage", "draft", "--skip-novice")
    d_zero = json.load(open(os.path.join(fx_nv_zero["dir"], "gates.json"), encoding="utf-8"))
    g_zero = [g for g in d_zero["stages"]["draft"]["gates"] if g["name"] == "novice"][0]
    check("novice: --skip-novice НЕ снимает класс нулевой терпимости - красная "
          "ось 4 роняет стадию даже под флагом (дыра обхода R-48)",
          rc_zero == 1 and g_zero["status"] == "FAIL", f"rc={rc_zero} {g_zero['status']}")
    check("novice: причина сужения видна в расписке gates.json («что судим» "
          "называет класс нулевой терпимости), а не молча",
          "класс нулевой терпимости" in (g_zero.get("what") or "")
          and "novice_zero.py" in (g_zero.get("cmd") if isinstance(g_zero.get("cmd"), str)
                                   else " ".join(g_zero.get("cmd") or [])),
          f"{g_zero.get('what')!r} | {str(g_zero.get('cmd'))[:160]!r}")
    rc_zero_p = call(fx_nv_zero, fx_nv_zero["slug"], "--stage", "page", "--skip-novice")
    d_zero_p = json.load(open(os.path.join(fx_nv_zero["dir"], "gates.json"), encoding="utf-8"))
    g_zero_p = [g for g in d_zero_p["stages"]["page"]["gates"] if g["name"] == "novice"][0]
    check("novice: тот же запрет обхода стоит и на стадии page, а не только draft",
          rc_zero_p == 1 and g_zero_p["status"] == "FAIL",
          f"rc={rc_zero_p} {g_zero_p['status']}")

    # ── боевой novice_zero.py на СВОИХ текстах: оба случая наряда R-48 ────────
    nz_tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novice_zero.py")
    nz_dir = os.path.join(root, "novice-zero-tool")
    os.makedirs(nz_dir, exist_ok=True)

    def nz_run(name, text):
        p = os.path.join(nz_dir, name)
        open(p, "w", encoding="utf-8").write(text)
        return subprocess.run([sys.executable, nz_tool, p, "--tool", nv_tool,
                               "--stage", "draft"], capture_output=True, text=True)

    r_nz_bad = nz_run("bad.md", "# Проверка\n\nЯ прогнал адрес: сайт вернул код 403 "
                                "со всех трёх узлов, а второй адрес отдал код 200.\n")
    check("novice-zero: тех-деталь для продвинутых роняет прогон (порога нет)",
          r_nz_bad.returncode == 1 and "класс нулевой терпимости" in r_nz_bad.stdout,
          f"rc={r_nz_bad.returncode} {r_nz_bad.stdout[:200]!r}")
    r_nz_ok = nz_run("ok.md", "# Проверка\n\nЯ проверил сайт из трёх мест в России: "
                              "страница открылась везде, а один адрес не пустил.\n")
    check("novice-zero: чистый по классу текст проходит, даже если пороговые оси "
          "легаси были бы красными",
          r_nz_ok.returncode == 0 and "класс чист" in r_nz_ok.stdout,
          f"rc={r_nz_ok.returncode} {r_nz_ok.stdout[:200]!r}")

    # ── сам инструмент, боевой, на своих фикстурах ───────────────────────────
    nv_dir = os.path.join(root, "novice-tool")
    os.makedirs(nv_dir, exist_ok=True)

    def nv_run(name, text, *extra):
        p = os.path.join(nv_dir, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        pr = subprocess.run([sys.executable, nv_tool, p] + list(extra),
                            capture_output=True, text=True)
        return pr.returncode, (pr.stdout or "") + (pr.stderr or "")

    if not existing(nv_tool):
        check("novice: боевой novice-check.py на месте", False, nv_tool)
    else:
        # объём фикстуры взят с запасом (~1300 слов): ось 2 меряет ПЛОТНОСТЬ
        # блоков на 1000 слов, и на коротком тексте восемь блоков дали бы 40/1k
        # то есть красный по второй ноге оси - тест проверял бы не то, что хотел
        чисто = ("Открой браузер и нажми большую кнопку «Начать». Увидишь окно, "
                 "где словами пишешь задачу. Это как разговор с помощником: "
                 "говоришь, что нужно, и получаешь ответ. ") * 80
        rc_c, out_c = nv_run("clean.html", f"<html><body><main><p>{чисто}</p></main></body></html>")
        check("novice ПОЗИТИВ: живой текст без жаргона, кода и кадров = PASS, rc=0",
              rc_c == 0 and "-> PASS" in out_c, f"rc={rc_c}")

        жаргон = ("Открой терминал и поставь репозиторий через npm. Дальше "
                  "конфиг, деплой на сервер, эндпоинт и токен в переменной "
                  "окружения. ") * 6
        rc_j, out_j = nv_run("jargon.html", f"<html><body><main><p>{жаргон}</p></main></body></html>")
        check("novice НЕГАТИВ: плотность жаргона выше порога роняет гейт, rc=1, "
              "и в отчёте названы САМИ слова с числом",
              rc_j == 1 and "жаргон" in out_j and "терминал ×" in out_j, f"rc={rc_j}")

        # чистый счёт: те же слова ВНУТРИ <pre> не считаются жаргоном прозы
        внутри = "<pre>" + жаргон + "</pre>"
        rc_p, out_p = nv_run("incode.html",
                             f"<html><body><main><p>{чисто}</p>"
                             f"<p>Скопируй этот блок и нажми Enter, увидишь ответ</p>"
                             f"{внутри}</main></body></html>")
        check("novice ЧИСТЫЙ СЧЁТ: тот же жаргон внутри <pre> в ось не идёт "
              "(иначе гейт красил бы статью по собственным примерам кода)",
              rc_p == 0 and "0.00/1k" in out_p, f"rc={rc_p}")

        # объясняющая конструкция того же предложения снимает вхождение
        объясн = ("Репозиторий - это просто папка с файлами программы в интернете. " * 20)
        rc_e, out_e = nv_run("explain.html", f"<html><body><main><p>{объясн}</p></main></body></html>")
        check("novice ЧИСТЫЙ СЧЁТ: термин, объяснённый в ТОМ ЖЕ предложении "
              "(«X - это …»), не считается - канон требует ровно этого",
              rc_e == 0, f"rc={rc_e}")

        # ось 3: скриншот терминала. Жёстко - брак, с --revision - замечание
        кадр = ('<figure><img src="assets/shot.webp" alt="Терминал: вывод команды '
                'после установки"></figure>')
        rc_t, out_t = nv_run("shot.html",
                             f"<html><body><main><p>{чисто}</p>{кадр}</main></body></html>")
        check("novice НЕГАТИВ: терминальный скрин в НОВОЙ статье = FAIL, rc=1, "
              "улика поимённая",
              rc_t == 1 and "Терминал" in out_t, f"rc={rc_t}")
        rc_tr, out_tr = nv_run("shot2.html",
                               f"<html><body><main><p>{чисто}</p>{кадр}</main></body></html>",
                               "--revision")
        check("novice: --revision снимает жёсткость ТОЛЬКО с этой оси - легаси "
              "даёт WARN (rc=2), а WARN стадию не роняет",
              rc_tr == 2 and RC_NOVICE[2] == "WARN", f"rc={rc_tr}")

        # ось 3: мокап окна терминала судится по СОДЕРЖИМОМУ, не по классу
        мокап_кода = ('<div class="term"><span class="term-title">поставь одной '
                      'строкой</span><pre>brew install node\nnpm i -g claude</pre></div>')
        мокап_промпта = ('<div class="term"><span class="term-title">скопируй и '
                         'вставь перед своей задачей</span><pre>Разбери мою задачу '
                         'как систему и покажи связи между частями</pre></div>')
        rc_m1, _ = nv_run("mock1.html",
                          f"<html><body><main><p>{чисто}</p>{мокап_кода}</main></body></html>")
        rc_m2, out_m2 = nv_run("mock2.html",
                               f"<html><body><main><p>{чисто}</p>{мокап_промпта}</main></body></html>")
        check("novice: мокап окна с shell-командами внутри = терминальный кадр (FAIL)",
              rc_m1 == 1, f"rc={rc_m1}")
        check("novice: тот же класс мокапа, но внутри ТЕКСТ промпта с подписью "
              "«скопируй и вставь» - легальный копи-блок канона, PASS",
              rc_m2 == 0, f"rc={rc_m2}")

        # ось 2: обвязка ищется по РЕНДЕРУ, а не по конкретному тегу
        # десять блоков, а не семь: первые два в цепочке легально обвязаны
        # соседним абзацем сверху («нажми», «Увидишь»), сырыми остаются восемь -
        # это и есть перебор красного порога 7
        сырые = "".join(f"<div><pre>echo шаг{i}</pre></div>" for i in range(10))
        обвязан = "".join(
            f"<details><summary>Промпт {i} - скопировать и вставить</summary>"
            f"<pre>Собери план на неделю по теме {i}</pre></details>" for i in range(10))
        rc_r, out_r = nv_run("raw.html",
                             f"<html><body><main><p>{чисто}</p>{сырые}</main></body></html>")
        rc_w, out_w = nv_run("wrapped.html",
                             f"<html><body><main><p>{чисто}</p>{обвязан}</main></body></html>")
        check("novice НЕГАТИВ: свалка блоков без обвязки роняет гейт, rc=1, и "
              "соседний <pre> НЕ считается «абзацем-обвязкой» (иначе один абзац "
              "сверху легализовал бы всю свалку)",
              rc_r == 1 and "сырых" in out_r, f"rc={rc_r}")
        check("novice ПОЗИТИВ: те же блоки с подписью в <summary> "
              "(«скопировать и вставить») сырыми НЕ считаются - обвязка ищется "
              "по РЕНДЕРУ, а не по списку тегов",
              rc_w == 0, f"rc={rc_w}")

        rc_n, out_n = nv_run("empty.md", "")
        check("novice: пустой вход - ERROR (rc=3), а не выдуманный зелёный",
              rc_n == 3 and RC_NOVICE[3] == "ERROR", f"rc={rc_n}")

        rc_d, out_d = nv_run(
            "draft.md",
            "---\nengine: article_build\nhero:\n  alt: 'Терминал с выводом установки'\n---\n\n"
            + чисто)
        check("novice ЧЕРНОВИК: терминал в alt ГЛАВНОГО кадра из YAML-шапки "
              "ловится на стадии draft, до сборки страницы",
              rc_d == 1 and "hero" in out_d, f"rc={rc_d}")

    # ── СМЫСЛОВОЙ ДУБЛЬ КАПСУЛЫ И БЫСТРОГО ОТВЕТА (круг 3, R102) ──
    # Порог снят с живых страниц, а не назначен. Замер по решению автора по пяти
    # страницам транша: разведённые по работе дают 30%, 33%, 38%; смысловые
    # дубли - 48% и 80%. Порог 45% стоит В РАЗРЫВЕ между этими группами
    тг = tc_thresholds({})
    _кап = ("по решению автора вышла отдельная версия помощника для подростков 13-17 лет, "
            "и это первый раз, когда помощник ведёт себя со школьником иначе, чем "
            "со взрослым. Раскатка шла две недели. Главное там не запреты, а режим "
            "учёбы: вместо готового ответа помощник задаёт наводящие вопросы")
    _дубль = ("по решению автора вышла отдельная версия помощника для подростков 13-17 лет. "
              "Главное в ней - режим учёбы: вместо готового ответа помощник задаёт "
              "наводящие вопросы и ведёт по шагам. Раскатка шла две недели")
    _развед = ("Проверь три вещи до того, как отдашь ребёнку общий аккаунт: возраст "
               "в профиле, тихие часы и привязку родительского телефона. Без них "
               "школьник получит взрослую версию, а не учебную")
    д_дубль, _, _ = tc_peresechenie(_кап, _дубль)
    д_развед, _, _ = tc_peresechenie(_кап, _развед)
    check("R102 КОНТРПРИМЕР: пересказ капсулы в быстром ответе ловится порогом",
          д_дубль > тг["capsule_qa_overlap_max"],
          f"пересечение={д_дубль:.2f} порог={тг['capsule_qa_overlap_max']}")
    check("R102: разведённый по работе быстрый ответ порог НЕ роняет "
          "(ложного красного на общей терминологии темы нет)",
          д_развед <= тг["capsule_qa_overlap_max"],
          f"пересечение={д_развед:.2f}")
    _зам = _замечания(capsule=_кап, quick_answer=_дубль, capsule_code=True)
    check("R102: гейт печатает дубль поимённо, а не молчит",
          any("ДУБЛИРУЮТ ДРУГ ДРУГА" in x for x in _зам), str(_зам)[:160])
    _зам2 = _замечания(capsule=_кап, quick_answer=_развед, capsule_code=True)
    check("R102: на разведённой паре гейт молчит",
          not any("ДУБЛИРУЮТ ДРУГ ДРУГА" in x for x in _зам2), str(_зам2)[:160])

    # ── РАЗЪЕХАВШИЕСЯ ФОРМАТЫ ОДНОГО КАДРА: починка метода (круг 3, T12/R113) ──
    # Контрпример строится ровно на той геометрии, которая обманула барьер:
    # локальная модалка на ~0.5% площади кадра. Старый метод (средняя яркость на
    # 32x32) обязан её ПРОСПАТЬ - это и доказывает, что порог был не при чём, а
    # слеп был метод. Новый метод (доля пикселей полного разрешения) обязан её
    # поймать. Плюс живая пара того самого кадра, если она лежит на машине.
    try:
        from PIL import Image as _PILImage, ImageDraw as _PILDraw
    except Exception:
        _PILImage = None
    if _PILImage is not None:
        кадр_дир = os.path.join(root, "format-skew")
        os.makedirs(кадр_дир, exist_ok=True)
        Ш, В = 2880, 1800
        база = _PILImage.new("RGB", (Ш, В), (238, 240, 244))
        d = _PILDraw.Draw(база)
        for y in range(0, В, 90):                     # фактура, чтобы кадр не был пустым
            d.rectangle([0, y, Ш, y + 45], fill=(214, 219, 228))
        чистый = os.path.join(кадр_дир, "hero.png")
        база.save(чистый)
        # модалка: 230x230 = 52 900 из 5 184 000 = 1.02% площади, светлая панель
        # поверх светлой страницы - геометрия и контраст живого случая (там доля
        # разошедшихся пикселей вышла 0.48%, средняя по 32x32 всего 0.77)
        с_модалкой = база.copy()
        dm = _PILDraw.Draw(с_модалкой)
        dm.rectangle([2500, 1450, 2730, 1680], fill=(170, 174, 182))
        грязный = os.path.join(кадр_дир, "hero.jpg")
        с_модалкой.save(грязный, quality=88)
        та_же_съёмка = os.path.join(кадр_дир, "hero.webp")
        база.save(та_же_съёмка, quality=86)

        ср_грязн = prov_frame_diff(prov_frame_signature(чистый),
                                   prov_frame_signature(грязный))
        доля_грязн, разошлось_г, всего_г = prov_frame_pixel_share(чистый, грязный)
        доля_чист, разошлось_ч, _всего_ч = prov_frame_pixel_share(чистый, та_же_съёмка)
        check("КОНТРПРИМЕР T12: старый метод (средняя 32x32) локальную модалку "
              "ПРОСПАЛ - значит слеп был метод, а не порог",
              ср_грязн is not None and ср_грязн <= PROV_FORMAT_DIFF_MAX,
              f"средняя={ср_грязн} порог={PROV_FORMAT_DIFF_MAX}")
        check("КОНТРПРИМЕР T12: новый метод (доля пикселей полного разрешения) "
              "модалку ЛОВИТ",
              доля_грязн is not None and доля_грязн > PROV_FORMAT_PIXEL_SHARE,
              f"доля={доля_грязн} ({разошлось_г}/{всего_г}) порог={PROV_FORMAT_PIXEL_SHARE}")
        check("КОНТРПРИМЕР T12: одна съёмка в двух форматах новый метод НЕ роняет "
              "(ложного красного нет)",
              доля_чист is not None and доля_чист <= PROV_FORMAT_PIXEL_SHARE,
              f"доля={доля_чист} ({разошлось_ч})")

        # живая пара того самого кадра - условное чтение, машины без неё не падают
        живой_чистый = os.path.expanduser(
            "~/.business/growth/seo/lead-magnit-work/"
            "guide-lovable-ocenka-2026/assets/lovable-ocenka-2026-hero.png")
        живой_грязный = живой_чистый[:-4] + ".jpg"
        if os.path.isfile(живой_чистый) and os.path.isfile(живой_грязный):
            ж_доля, ж_разошлось, ж_всего = prov_frame_pixel_share(живой_чистый,
                                                                  живой_грязный)
            ж_ср = prov_frame_diff(prov_frame_signature(живой_чистый),
                                   prov_frame_signature(живой_грязный))
            check("живой кадр lovable: пара .png/.jpg судится новым методом "
                  "(доля названа числом)",
                  ж_доля is not None,
                  f"доля={ж_доля} ({ж_разошлось}/{ж_всего}) средняя32={ж_ср}")

    ok = 0
    for name, good, detail in results:
        print(f"  {'OK  ' if good else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not good else ""))
        ok += 1 if good else 0
    print(f"selftest article_gates: {ok}/{len(results)} прошло")
    return 0 if ok == len(results) else 1


# ── CLI ──────────────────────────────────────────────────────────────────────

def default_shared(cfg):
    """Разделяемые файлы под claim-проверку: конфиг или канонный набор."""
    v = cfg.get("shared_files")
    if isinstance(v, list) and v:
        return [os.path.expanduser(x) for x in v if isinstance(x, str) and x.strip()]
    base = os.path.dirname(cfg_path(cfg, "work_dir", "~/.business/growth/seo/lead-magnit-work"))
    # /blog/ вместо /blog.html (по решению автора): хаб гайдов переехал на чистый адрес,
    # клеймить надо тот файл, который публикация реально правит.
    return ["/sitemap.xml", "/blog/",
            os.path.join(base, "content-sha-registry.json"),
            os.path.join(base, "state.json")]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="article_gates.py",
        description="Единый раннер гейтов статьи: draft | page | publish")
    ap.add_argument("slug", nargs="?", help="slug статьи или путь к каталогу статьи")
    ap.add_argument("--stage", choices=STAGES, help="какую стадию гнать")
    ap.add_argument("--revision", action="store_true",
                    help="статья - ревизия старой (ось tool-article не жёсткая)")
    ap.add_argument("--skip-novice", dest="skip_novice", action="store_true",
                    help="не гнать гейт novice (легаси-операция: техническая "
                         "пересборка/переклейка страницы без правки текста). "
                         "В gates.json уходит SKIP с причиной, а не тихий PASS")
    ap.add_argument("--skip-prod-source", dest="skip_prod_source", action="store_true",
                    help="не гнать гейт prod-vs-source (сверку живого прода со "
                         "сборкой из источника): прогон без сети / разбор офлайн. "
                         "В gates.json уходит SKIP с причиной, а не тихий PASS")
    ap.add_argument("--draft", default=None,
                    help="имя/путь черновика для стадии draft (по умолчанию draft.md; "
                         "во время миграции кандидат лежит рядом как draft-v2.md)")
    ap.add_argument("--work", default=None, help="каталог прогонов (иначе $WORK/конфиг/канон)")
    ap.add_argument("--config", default=None, help="путь к seo-publish.json")
    ap.add_argument("--report", default=None, help="куда писать отчёт (иначе <каталог>/gates.json)")
    ap.add_argument("--neighbours", type=int, default=NEIGHBOURS_DEFAULT,
                    help=f"сколько БЛИЖАЙШИХ ПО ТЕМЕ соседей брать в корпус originality "
                         f"(дефолт {NEIGHBOURS_DEFAULT}; кандидаты - весь каталог прогонов "
                         f"+ слепок живого корпуса)")
    ap.add_argument("--quiet", action="store_true", help="печатать только итог стадии")
    ap.add_argument("--no-write", dest="no_write", action="store_true",
                    help="диагностика: прогнать и напечатать, gates.json НЕ трогать")
    ap.add_argument("--list", action="store_true", help="какие гейты входят в какую стадию")
    ap.add_argument("--gate-set", dest="gate_set", choices=STAGES, default=None,
                    help="напечатать ЭТАЛОННЫЙ набор имён гейтов стадии одной "
                         "JSON-строкой и выйти. Этим набором читатели расписки "
                         "(ftp_publish) проверяют, что gates.json выписан текущим "
                         "составом гейтов, а не прошлым - второго списка имён "
                         "нигде нет, эталон отдаёт сам раннер")
    ap.add_argument("--selftest", action="store_true")
    # ── замок происхождения кадров: и для стадии page, и для служебного режима
    # --frame-provenance. Дефолт мягкий (WARN) - см. RC_PROV и докстринг гейта ──
    ap.add_argument("--provenance-hard", dest="provenance_hard", action="store_true",
                    help="ЗАМОК гейта frame-provenance: кадр без записи о съёмке "
                         "И class=result с адресом корня сервиса («скрин главной») "
                         "= FAIL (по умолчанию - WARN, стадию не роняет)")
    # ── служебный режим: сам гейт title-ctr (его зовёт build_gates отдельным
    # процессом; руками полезен для диагностики одной статьи) ────────────────
    ap.add_argument("--title-ctr", dest="title_ctr", default=None,
                    help="прогнать ТОЛЬКО гейт формулы сниппета по каталогу статьи")
    ap.add_argument("--tc-stage", dest="tc_stage", choices=("draft", "page"),
                    default="draft", help="по чему смотреть: черновик или собранная страница")
    ap.add_argument("--tc-draft", dest="tc_draft", default=None,
                    help="путь черновика для --title-ctr --tc-stage draft")
    ap.add_argument("--tc-hard", dest="tc_hard", action="store_true",
                    help="замечания = FAIL (новая статья). Без флага - WARN (ревизия)")
    ap.add_argument("--tc-yaml", dest="tc_yaml", default=None,
                    help="конфиг порогов tools.title_ctr.* (иначе дефолты)")
    ap.add_argument("--tc-tools", dest="tc_tools", default=None,
                    help="каталог инструментов скилла (оттуда берётся парсер _config.py)")
    ap.add_argument("--tc-brand-tail", dest="tc_tails", action="append", default=None,
                    help="брендовый хвост, которого не должно быть в title (можно повторять)")
    # ── служебный режим: сам гейт cta (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу) ──────────
    ap.add_argument("--cta-gate", dest="cta_gate", default=None,
                    help="прогнать ТОЛЬКО гейт маршрута CTA по каталогу статьи")
    ap.add_argument("--cta-config", dest="cta_config", default=None,
                    help="config.md скилла с секцией cta (иначе канонный путь скилла)")
    ap.add_argument("--cta-page", dest="cta_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    # ── служебный режим: сам гейт assets-exist (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу) ───────────
    # ── служебный режим: сам гейт svezhaya-tema (закон 25) ───────────────────
    ap.add_argument("--svezhaya-tema", dest="svezhaya_tema", default=None,
                    help="прогнать ТОЛЬКО гейт класса «свежая узкая тема» по "
                         "каталогу статьи")
    ap.add_argument("--st-draft", dest="st_draft", default=None,
                    help="путь черновика для --svezhaya-tema (иначе draft.md)")
    # ── служебные режимы: гейты дельты топ-3 (волна 3) ───────────────────────
    ap.add_argument("--title-god", dest="title_god", default=None,
                    help="прогнать ТОЛЬКО гейт «год в title у датируемой темы» "
                         "по каталогу статьи")
    ap.add_argument("--tg-draft", dest="tg_draft", default=None,
                    help="путь черновика для --title-god (иначе draft.md)")
    ap.add_argument("--own-run-shagi", dest="own_run_shagi", default=None,
                    help="прогнать ТОЛЬКО гейт «пошаговая инструкция требует "
                         "кадра своего экрана» по каталогу статьи")
    ap.add_argument("--ors-draft", dest="ors_draft", default=None,
                    help="путь черновика для --own-run-shagi (иначе draft.md)")
    ap.add_argument("--vnutrennie-ssylki", dest="vnutrennie_ssylki", default=None,
                    help="прогнать ТОЛЬКО гейт минимума внутренних ссылок по "
                         "каталогу статьи")
    ap.add_argument("--vs-stage", dest="vs_stage", choices=["draft", "page"],
                    default="draft", help="что читать гейту ссылок: черновик или страницу")
    ap.add_argument("--vs-draft", dest="vs_draft", default=None,
                    help="путь черновика для --vnutrennie-ssylki (иначе draft.md)")
    ap.add_argument("--vs-page", dest="vs_page", default=None,
                    help="путь страницы для --vnutrennie-ssylki (иначе index.html)")
    ap.add_argument("--vs-min", dest="vs_min", type=int, default=VN_МИНИМУМ,
                    help="порог минимума внутренних ссылок (дефолт %d)" % VN_МИНИМУМ)
    ap.add_argument("--vs-config", dest="vs_config", default=None,
                    help="config.md скилла для --vnutrennie-ssylki (свой домен); "
                         "без него считаются только корневые пути")
    ap.add_argument("--assets-exist", dest="assets_exist", default=None,
                    help="прогнать ТОЛЬКО гейт существования локальных ассетов "
                         "страницы по каталогу статьи")
    ap.add_argument("--assets-page", dest="assets_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    # ── РАСКЛАДКА ПРОДА: свойство ПРОГОНА, а не статьи. Читают гейт image-refs
    # и его служебный режим. Дефолт auto - раскладка выводится из самой
    # страницы, и судится её внутренняя непротиворечивость ─────────────────────
    ap.add_argument("--page-layout", dest="page_layout", choices=IMGREF_LAYOUTS,
                    default="auto",
                    help="раскладка, по которой страница поедет на прод: "
                         "dir (каталог статьи целиком в /<slug>/, картинки "
                         "внутри) · flat (картинки в общем каталоге, верен "
                         "только корневой путь) · auto (по умолчанию: вывести "
                         "из самой страницы и судить непротиворечивость)")
    ap.add_argument("--assets-remote", dest="assets_remote", default=None,
                    help="каталог картинок статьи НА ПРОДЕ для плоской "
                         "раскладки, без слэшей по краям (дефолт assets/<slug>) "
                         "- тот же смысл и то же имя, что у ftp_publish")
    # ── служебный режим: сам гейт image-refs (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу) ───────────
    ap.add_argument("--image-refs", dest="image_refs", default=None,
                    help="прогнать ТОЛЬКО гейт битых картинок по каталогу "
                         "статьи: смешанная раскладка внутри <picture>, "
                         "расщеплённая раскладка страницы, плоский путь "
                         "оставленный относительным, несоответствие объявленной "
                         "раскладке")
    ap.add_argument("--image-refs-page", dest="image_refs_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    ap.add_argument("--image-refs-slug", dest="image_refs_slug", default=None,
                    help="слаг статьи (иначе имя каталога) - им резолвятся "
                         "адреса обеих раскладок прода")
    ap.add_argument("--require-local-files", dest="require_local_files",
                    action="store_true",
                    help="дополнительно требовать локальный файл под КАЖДУЮ свою "
                         "корневую ссылку. По умолчанию выключено: на стадии page "
                         "набор заливки неизвестен, и «файла нет рядом» не значит "
                         "«картинка битая». Включать имеет право только вызов, у "
                         "которого весь набор на руках (предполёт заливки)")
    # ── служебный режим: сам гейт frame-density (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы промерить кадры одной живой страницы) ───
    ap.add_argument("--frame-density", dest="frame_density", default=None,
                    help="прогнать ТОЛЬКО гейт плотности кадров по каталогу статьи")
    ap.add_argument("--frame-page", dest="frame_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    ap.add_argument("--frame-yaml", dest="frame_yaml", default=None,
                    help="конфиг порогов (tools.visual.frame_count_min) для пола "
                         "по числу собственных кадров; без него - дефолт 3")
    ap.add_argument("--frame-tools", dest="frame_tools", default=None,
                    help="каталог tools раздаваемого модуля (парсер конфига)")
    # ── служебный режим: сам гейт frame-provenance (его зовёт build_gates
    # отдельным процессом; руками полезен, чтобы промерить корпус) ─────────────
    ap.add_argument("--frame-provenance", dest="frame_provenance", default=None,
                    help="прогнать ТОЛЬКО гейт происхождения кадров по каталогу "
                         "статьи (манифест съёмки shots-manifest.json рядом)")
    ap.add_argument("--provenance-page", dest="provenance_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    ap.add_argument("--provenance-report", dest="provenance_report", action="store_true",
                    help="режим ОТЧЁТА гейта происхождения: напечатать сводку и "
                         "выйти с 0 в любом случае (им меряется корпус до "
                         "ужесточения, ничего не роняет)")
    # ── служебный режим: сам гейт infra-leak (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу) ───────────
    ap.add_argument("--infra-leak-gate", dest="infra_leak_gate", default=None,
                    help="прогнать ТОЛЬКО гейт утечки служебной инфраструктуры "
                         "по каталогу статьи")
    ap.add_argument("--infra-secrets", dest="infra_secrets", default=None,
                    help="infra-secrets.txt со списком запрещённых литералов "
                         "(иначе канонный путь автор-дома)")
    ap.add_argument("--infra-leak-page", dest="infra_leak_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    # ── служебный режим: сам гейт cta-position (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу) ──────────
    ap.add_argument("--cta-position", dest="cta_position", default=None,
                    help="прогнать ТОЛЬКО гейт места финального призыва в хвосте "
                         "по каталогу статьи")
    ap.add_argument("--cta-position-page", dest="cta_position_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    # ── служебный режим: сам гейт toc-mobile (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы прогнать одну живую страницу и чтобы им
    # же закрывался нож корпуса toc_mobile_strip.py) ───────────────────────────
    ap.add_argument("--toc-mobile", dest="toc_mobile", default=None,
                    help="прогнать ТОЛЬКО гейт-негатив мобильного оглавления "
                         "(class=\"toc-mobile\") по каталогу статьи")
    ap.add_argument("--toc-mobile-page", dest="toc_mobile_page", default=None,
                    help="проверить конкретный файл страницы, а не <каталог>/index.html")
    # ── служебный режим: сам гейт retract-sync (его зовёт build_gates отдельным
    # процессом; руками полезен, чтобы проверить одну живую папку статьи) ─────
    ap.add_argument("--retract-sync", dest="retract_sync", default=None,
                    help="прогнать ТОЛЬКО гейт синхронизации отзывов: живут ли "
                         "в draft.md/research.md/index.html формулировки, "
                         "объявленные в логах строкой «ОТОЗВАНО-ФРАЗА: «…»»")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if a.svezhaya_tema:
        adir = os.path.expanduser(a.svezhaya_tema)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = svezhaya_tema_run(
            adir, draft_path=(os.path.expanduser(a.st_draft) if a.st_draft else None))
        for line in lines:
            print(line)
        return rc
    if a.title_god:
        adir = os.path.expanduser(a.title_god)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = title_god_run(
            adir, draft_path=(os.path.expanduser(a.tg_draft) if a.tg_draft else None))
        for line in lines:
            print(line)
        return rc
    if a.own_run_shagi:
        adir = os.path.expanduser(a.own_run_shagi)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = own_run_shagi_run(
            adir, draft_path=(os.path.expanduser(a.ors_draft) if a.ors_draft else None))
        for line in lines:
            print(line)
        return rc
    if a.vnutrennie_ssylki:
        adir = os.path.expanduser(a.vnutrennie_ssylki)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = vnutrennie_ssylki_run(
            adir, stage=a.vs_stage,
            draft_path=(os.path.expanduser(a.vs_draft) if a.vs_draft else None),
            page_path=(os.path.expanduser(a.vs_page) if a.vs_page else None),
            minimum=a.vs_min,
            config_path=(os.path.expanduser(a.vs_config) if a.vs_config else None),
            revision=bool(a.revision))
        for line in lines:
            print(line)
        return rc
    if a.assets_exist:
        adir = os.path.expanduser(a.assets_exist)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = assets_exist_run(
            adir, page_path=(os.path.expanduser(a.assets_page) if a.assets_page else None))
        for line in lines:
            print(line)
        return rc
    if a.image_refs:
        adir = os.path.expanduser(a.image_refs)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = image_refs_run(
            adir,
            page_path=(os.path.expanduser(a.image_refs_page) if a.image_refs_page else None),
            slug=a.image_refs_slug, layout=a.page_layout,
            assets_remote=a.assets_remote,
            require_files=bool(a.require_local_files))
        for line in lines:
            print(line)
        return rc
    if a.retract_sync:
        adir = os.path.expanduser(a.retract_sync)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = retract_sync_run(adir)
        for line in lines:
            print(line)
        return rc
    if a.frame_density:
        adir = os.path.expanduser(a.frame_density)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = frame_density_run(
            adir, page_path=(os.path.expanduser(a.frame_page) if a.frame_page else None),
            yaml_path=(os.path.expanduser(a.frame_yaml) if a.frame_yaml else None),
            tools_dir=(os.path.expanduser(a.frame_tools) if a.frame_tools else None))
        for line in lines:
            print(line)
        return rc
    if a.frame_provenance:
        adir = os.path.expanduser(a.frame_provenance)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = frame_provenance_run(
            adir,
            page_path=(os.path.expanduser(a.provenance_page) if a.provenance_page else None),
            hard=bool(a.provenance_hard), report=bool(a.provenance_report),
            lm_config=(os.path.expanduser(a.vs_config) if a.vs_config else None))
        for line in lines:
            print(line)
        return rc
    if a.cta_position:
        adir = os.path.expanduser(a.cta_position)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = cta_position_run(
            adir, page_path=(os.path.expanduser(a.cta_position_page)
                             if a.cta_position_page else None))
        for line in lines:
            print(line)
        return rc
    if a.toc_mobile:
        adir = os.path.expanduser(a.toc_mobile)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = toc_mobile_run(
            adir, page_path=(os.path.expanduser(a.toc_mobile_page)
                             if a.toc_mobile_page else None))
        for line in lines:
            print(line)
        return rc
    if a.infra_leak_gate:
        adir = os.path.expanduser(a.infra_leak_gate)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        secrets = (os.path.expanduser(a.infra_secrets) if a.infra_secrets
                  else os.path.expanduser(FALLBACK["infra_secrets"]))
        rc, lines = infra_leak_run(
            adir, secrets,
            page_path=(os.path.expanduser(a.infra_leak_page) if a.infra_leak_page else None))
        for line in lines:
            print(line)
        return rc
    if a.cta_gate:
        adir = os.path.expanduser(a.cta_gate)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 2
        rc, lines = cta_run(
            adir,
            config_path=(os.path.expanduser(a.cta_config) if a.cta_config else None),
            page_path=(os.path.expanduser(a.cta_page) if a.cta_page else None))
        for line in lines:
            print(line)
        return rc
    if a.title_ctr:
        adir = os.path.expanduser(a.title_ctr)
        if not os.path.isdir(adir):
            print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
            return 3
        rc, lines = title_ctr_run(
            adir, a.tc_stage,
            draft_path=(os.path.expanduser(a.tc_draft) if a.tc_draft else None),
            hard=a.tc_hard, yaml_path=(os.path.expanduser(a.tc_yaml) if a.tc_yaml else None),
            tools_dir=(os.path.expanduser(a.tc_tools) if a.tc_tools else None),
            tails=a.tc_tails or ())
        for line in lines:
            print(line)
        return rc
    cfg = load_cfg(a.config)
    if a.gate_set:
        # машинный вход: эталон набора спрашивают у САМОГО раннера, второго
        # списка имён гейтов в проекте нет (см. докстринг stage_gate_set)
        print(json.dumps({"stage": a.gate_set,
                          "gate_set": stage_gate_set(cfg, a.gate_set)},
                         ensure_ascii=False))
        return 0
    if a.list:
        return print_list(cfg)
    if not a.slug or not a.stage:
        ap.error("нужен <slug> и --stage draft|page|publish (или --list / --selftest)")

    cand = os.path.expanduser(a.slug)
    work = work_dir(cfg, a.work)
    # 🔴 КОЛЛИЗИЯ ИМЕНИ В cwd ПРОТИВ ЯВНОГО --work (запись R118, проба круга 4).
    # `<slug>` трактуется как путь, если такой каталог есть В ТЕКУЩЕЙ директории.
    # Значит вызов `cd <куда угодно с папкой guide-x> && article_gates.py guide-x
    # --work /боевой/каталог` МОЛЧА судил чужую копию, а флаг `--work`
    # игнорировался целиком: гейты отрабатывали по не тому объекту и печатали
    # зелёный отчёт про него. Тихая деградация в барьере опаснее его отсутствия
    # (память `soft_degradation_is_a_silently_disabled_gate`), поэтому здесь
    # ОТКАЗ, а не выбор наугад.
    if (a.work and os.path.isdir(cand)
            and os.path.realpath(cand)
            != os.path.realpath(os.path.join(work, a.slug))):
        print("🔴 article_gates: КОЛЛИЗИЯ ИМЕНИ. В текущем каталоге есть "
              f"«{a.slug}» ({os.path.realpath(cand)}), но задан явный --work "
              f"({work}), где лежит другой каталог "
              f"({os.path.realpath(os.path.join(work, a.slug))}). Раньше флаг "
              "молча игнорировался и судилась копия из cwd. Уточни, что судить: "
              "полный путь первым аргументом либо прогон не из этого каталога",
              file=sys.stderr)
        return 2
    adir = cand if os.path.isdir(cand) else os.path.join(work, a.slug)
    if not os.path.isdir(adir):
        print(f"article_gates: нет каталога статьи: {adir}", file=sys.stderr)
        return 2
    slug = os.path.basename(adir.rstrip("/"))

    # 🔴 Наблюдение скептика-18 (по решению автора): КУДА УЙДЁТ ОТЧЁТ - ПЕРВОЙ СТРОКОЙ.
    # `article_gates.py <slug>` (по имени, без явного пути) молча пишет расписку
    # в БОЕВОЙ $WORK/<slug>/gates.json. Диагностический прогон - «просто
    # посмотреть, что скажут гейты» - тем самым перетирает расписку рабочего
    # каталога, а её читают как утверждение о байтах страницы (artifacts_gate,
    # ftp_publish перед минтом). Предупреждение стоит РАНЬШЕ прогона: после
    # него читать поздно, файл уже перезаписан.
    #
    # 🔴 Наблюдение скептика-19 (3/3, по решению автора): проверка `os.path.isdir(cand)`
    # сравнивала СЫРУЮ строку аргумента, а не РЕАЛЬНЫЙ каталог - вызов
    # ОТНОСИТЕЛЬНЫМ путём из $WORK (`cd $WORK && article_gates.py guide-x ...`)
    # тоже даёт `isdir(cand)=True` (относительно cwd), читается как «явный путь
    # дан», и предупреждение молчит - хотя `adir` физически указывает РОВНО на
    # тот же боевой каталог. Сравнение нормализовано через `os.path.realpath`:
    # предупреждение спрашивает не КАК был записан путь, а КУДА он указывает.
    _боевой_каталог = os.path.realpath(os.path.join(work, slug))
    if (os.path.realpath(adir) == _боевой_каталог
            and not a.report and not a.no_write):
        # 🔴 НАБЛЮДЕНИЕ-1 скептика-20 (по решению автора): печатали `adir` КАК ЗАДАН
        # (bare-имя при относительном вызове из cwd=$WORK даёт голое
        # "guide-x/gates.json" без единой директории контекста - выглядит
        # странно и бесполезно, если строку скопировать в другое место).
        # Сравнение УЖЕ решает вопрос «куда путь физически указывает» через
        # `_боевой_каталог` (realpath) - печатаем РАЗРЕШЁННЫЙ путь, а не
        # сырой ввод: сообщение остаётся верным независимо от того, КАК был
        # вызван скрипт (по имени / относительно / дублирующим абсолютным).
        print(f"⚠️ article_gates: отчёт уйдёт в БОЕВОЙ "
              f"{os.path.join(_боевой_каталог, 'gates.json')} (расписку читают "
              f"artifacts_gate и ftp_publish). Диагностика на копии - явным "
              f"путём: --report <путь> либо --no-write")

    # цель стадии обязана существовать: гнать гейты по отсутствующему файлу -
    # это зелёный отчёт ни о чём
    draft_path = os.path.join(adir, "draft.md")
    if a.draft:
        cand_draft = os.path.expanduser(a.draft)
        draft_path = cand_draft if os.path.isabs(cand_draft) else os.path.join(adir, cand_draft)
    if a.stage == "draft" and not os.path.isfile(draft_path):
        print(f"article_gates: нет {os.path.basename(draft_path)} в {adir} - "
              f"стадию draft гнать не по чему", file=sys.stderr)
        return 2
    if a.stage == "page" and not os.path.isfile(os.path.join(adir, "index.html")):
        print(f"article_gates: нет index.html в {adir} - стадию page гнать не по чему",
              file=sys.stderr)
        return 2

    # Б16: байты страницы снимаются ДО прогона - это ровно те байты, которые
    # читали чекеры. Если страницу правили во время прогона, sha в отчёте
    # останется «доправочным» и следующая же сверка (artifacts_gate/ftp_publish)
    # честно упрётся: гейты гонялись на других байтах, нужен перегон.
    page_path = os.path.join(adir, "index.html")
    page_sha, page_bytes = page_sha256(page_path)

    ctx = {"slug": slug, "dir": adir, "revision": a.revision, "draft": draft_path,
           "skip_novice": bool(getattr(a, "skip_novice", False)),
           "skip_prod_source": bool(getattr(a, "skip_prod_source", False)),
           "provenance_hard": bool(getattr(a, "provenance_hard", False)),
           "page_layout": getattr(a, "page_layout", "auto") or "auto",
           "assets_remote": getattr(a, "assets_remote", None),
           "shared_files": default_shared(cfg)}
    corpus, corpus_meta = None, None
    if a.stage == "draft":
        corpus, corpus_meta = neighbour_corpus(work, slug, a.neighbours, cfg=cfg,
                                               draft_path=draft_path)
        ctx["originality_corpus"] = corpus

    # применимость стадии решает КОНТРАКТ ЧЕРНОВИКА (шапка файла, раздел
    # «ПРИМЕНИМОСТЬ СТАДИИ draft»). Черновик нового контракта - источник истины
    # статьи, стадия по нему ЗАМОК всегда. Легаси-черновик опубликованной статьи
    # заморожен до фикс-волн, его источник истины - spec.json: там стадия
    # диагностическая, замок собранной страницы - стадия page.
    applicable, note = True, ""
    if a.stage == "draft" and not draft_is_new_contract(draft_path):
        pub, why = is_published(slug, cfg)
        if pub:
            applicable = False
            note = (f"статья опубликована ({why}), а черновик {os.path.basename(draft_path)} "
                    f"легаси-схемы (нет «engine: {ENGINE_MARK}»): его источник истины - "
                    f"spec.json рядом, оффер и служебные блоки живут в СОБРАННОЙ "
                    f"странице. Замок собранной страницы - стадия page")

    try:
        gates = [g for g in build_gates(cfg, ctx) if g["stage"] == a.stage]
        records = [run_gate(g) for g in gates]
    finally:
        if corpus:
            отложить(corpus, ignore_errors=True)   # закон №0: не сносим, откладываем
    # 🔴 С КЕМ СРАВНИВАЛИ - в расписку и в печать, ВСЕГДА, а не только при FAIL.
    # Без этого проверить отбор соседей нечем: гейт зелёный, а по каким текстам
    # он зелёный - знал только удалённый каталог-времянка (дефект волны r7)
    if corpus_meta is not None:
        for r in records:
            if r["name"] == "originality":
                r["neighbours"] = corpus_meta

    report_path = os.path.expanduser(a.report) if a.report else os.path.join(adir, "gates.json")
    extra = {"revision": bool(a.revision), "dir": adir, "applicable": applicable,
             # отпечаток НАБОРА гейтов прогона: без него зелёная расписка молчит
             # о том, каким составом гейтов её выписали (см. gate_set_of)
             "gate_set": gate_set_of(records)}
    # Б16: стадии, которые говорят о СОБРАННОЙ странице, подписывают её байты.
    # У стадии draft страницы может не быть вовсе - там поле не появляется, и
    # спрашивать его с draft никто не будет (блокирующая стадия расписки - page).
    if a.stage in ("page", "publish"):
        extra["page"] = os.path.basename(page_path)
        extra["page_sha256"] = page_sha
        extra["page_bytes"] = page_bytes
    if not applicable:
        extra["applicability_note"] = note
    if a.no_write:
        report_path = f"НЕ ЗАПИСАН (--no-write): {report_path}"
    else:
        write_report(report_path, slug, a.stage, records, extra)
    if a.quiet:
        c = counts_of(records)
        print(f"гейты [{a.stage}] {slug}: {verdict_of(records)}"
              + ("" if applicable else " (ДИАГНОСТИКА, стадия неприменима)")
              + f" (PASS {c['PASS']}, WARN {c['WARN']}, FAIL {c['FAIL']}, "
                f"ERROR {c['ERROR']}, SKIP {c['SKIP']}) -> {report_path}")
        # даже в тихом режиме видно, ЧЕМ мерили и по каким текстам зелёная
        # оригинальность: вердикт без числа и порога непроверяем
        for r in records:
            if r["name"] == "originality":
                for line in measure_lines(r):
                    print(f"  {line}")
        for line in neighbour_lines(corpus_meta, short=True):
            print(f"  {line}")
    else:
        print_records(a.stage, slug, records, report_path, applicable, note)
    if not applicable:
        return 0
    return 0 if verdict_of(records) == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
