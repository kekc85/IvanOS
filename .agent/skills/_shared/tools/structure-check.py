#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
structure-check.py - механическая проверка структуры черновика статьи.

Проверяет то, что ловится без чтения смысла (дополняет ai-cadence-check.py,
который ловит AI-почерк):

  1. Ровно один H1 (# ) - заголовок страницы.
  2. У каждого H2 (## ) есть контент до следующего H2 (нет пустых разделов).
  3. Есть раздел «Источники» / «Sources» (доверие + SEO).
  4. Есть хотя бы один CTA - ссылка на ваш оффер (cta.url, фолбэк target_url).
  5. У всех картинок ![alt](url) непустой alt (доступность + SEO).
  6. Минимум внутренних ссылок (tools.structure.min_internal_links, дефолт 3).
  6b. Ось outbound-links (по решению автора): из этих внутренних - минимум
      tools.structure.min_internal_links (тот же порог, счёт отдельный) должны
      вести на СВОИ КОНТЕНТНЫЕ материалы кластера - /guide-*/ или /tema/*/.
      Шапка и подвал в счёт не идут по построению (тело берётся из
      article/main), а блок «Читайте также» (`section#related`, шаблонная
      навигация низа страницы, одинаковая на каждой статье) - решено НЕ
      считать, вместе с FAQ/источниками/чек-листом/CTA/share/автором: иначе
      ось не отличит статью без единой contextual-ссылки в прозе от честно
      перелинкованной, у обеих внизу один и тот же блок. Считаются только
      ссылки, которые автор вплёл в живой текст статьи.
  7. Ось first-sentence: первая фраза каждого контентного раздела (soft по умолчанию,
     hard за флагом --first-sentence-hard). Закон - ZAKONY-SEO.md §13.
  8. Ось own-blocks: >= 3 блоков собственного, невыводимого из модели материала
     (soft по умолчанию, hard за флагом --own-blocks-hard).
  9. Ось tool-article (И9.2): >= 3 справочно-прикладных блоков - чек-лист, таблица,
     код/команда с копи-кнопкой, нумерованные шаги (soft по умолчанию, hard за
     флагом --tool-article-hard). Правка автора: возвращаемость - качество
     статьи, а не подписка - к прикладным блокам возвращаются, к прозе нет.
 10. Ось chunk (чанк-слой под ИИ-выдачу): H2-раздел как самодостаточный пассаж -
     объём раздела в вилке и прямой ответ в первых предложениях, а не разгон
     (soft по умолчанию, hard за флагом --chunk-hard). Правило и целевая вилка
     150-400 слов - `seo-engine/checklists/seo-geo.md` §2.10.

Это советующая проверка структуры, а не смысла. Финальное решение - за человеком.

🔴 ДВА РЕЖИМА ВХОДА.
  • markdown (по умолчанию для .md) - черновик статьи;
  • html (авто для .html, форс флагом --html) - СОБРАННАЯ страница.
Визуальные гейты (--visual) считают картинки, alt и разделы по факту вёрстки, а в
markdown-черновике картинок и блока «Источники» может физически не быть (они
появляются на сборке шаблона). Поэтому визуальные гейты гонять по СОБРАННОЙ
странице: `structure-check.py $WORK/<slug>/index.html --visual`. Прогон --visual по
.md-черновику скрипт помечает как некорректный (подсказка в выводе).

🔴 КАК СЧИТАЮТСЯ H2 В HTML-РЕЖИМЕ (изменено по решению автора).
Контентный H2 = любой h2 внутри article/main, кроме служебных блоков шаблона (FAQ,
чек-лист, «читайте также», источники, финальный CTA, автор, шаринг - опознаются по
id/class секции-предка, плюс закрытый список канонических названий заголовков).
Якорем считается id на самом h2 ЛИБО id на секции-обёртке: у баннеров-«частей»
(`<section class="partbanner" id="part-vpn">`) h2 внутри голый, и раньше счётчик их
терял - живой лендинг показывал 13 разделов при 19 h2 в DOM и красил вилку
зелёным. Контентный h2 совсем без якоря = отдельное замечание (выпадает из TOC).
При --visual по HTML всегда печатается честная строка `H2: в теле … · контентных … ·
служебных …`, чтобы зелёная вилка была проверяемой.

🔴 CTA БЕЗ ТИХОЙ ДЕГРАДАЦИИ (правка 04.08.2026, находка разведки волны 1).
Раньше при пустом `cta.url` гейт молча падал на слабую проверку «есть хоть одна
внешняя ссылка http» - закон «финал ВСЕГДА ведёт на трипваер» машинно не
проверялся вообще (в config.md ключа cta нет, там target_url; в
seo-config-reference.yaml значение-заглушка вырезается _strip_placeholders).
Теперь: cta.url → фолбэк на target_url → если НЕТ ОБОИХ, это ошибка конфига,
а не мягкая проверка: скрипт останавливается с exit 2 и печатает, какой ключ
и в каком файле дописать.

🔴 ОСЬ ПЛОТНОСТИ ИЛЛЮСТРАЦИЙ - БАЗА СЧЁТА (правка 14.08.2026, волна r7).
Было: потребность считалась от ПОЛНОГО объёма собранной страницы (проза + таблицы
+ листинги + FAQ + чек-лист + источники + CTA). Канон при этом всегда говорил
«1 иллюстрация на ~300 слов ТЕКСТА ТЕЛА» - код канон не реализовывал. Замер
корпуса по решению автора по 44 ОПУБЛИКОВАННЫМ страницам: старая база красила красным 21 из
44 (48%), то есть блокировала половину принятого владельцем корпуса.
Стало - ось разложена на ДВА порога:
  • ПОЛ (правка 19.08.2026 - добавлен.vizblock; по решению автора - то же в ветке.md):
    минимум tools.visual.min_images единиц, единица = настоящая иллюстрация
    (<figure>) ИЛИ HTML-блок .vizblock (vizsteps/vizcheck/vizcompare - штатный
    визуал шага стандарта новичка, knowledge/novice-standard.md §5). Таблицами и
    листингами НЕ закрывается - именно он ловит полотно текста. Обе ветки (по
    собранной странице и по markdown-черновику) считают пол ОДИНАКОВО: до правки
    по решению автора черновик без единой картинки, но с тремя vizsteps, краснел по стадии
    draft и был зелёным по стадии page;
  • ПЛОТНОСТЬ: считается от объёма ПРОЗЫ и закрывается ВИЗУАЛЬНЫМИ БЛОКАМИ
    (иллюстрация + таблица + код-листинг), с потолком требования
    tools.visual.max_images_required.
Из объёма прозы вычитаются: <table>, <pre>, <figure>, служебные секции хвоста
(FAQ / чек-лист / источники / читайте также / CTA / share / автор - тот же
SERVICE_SECTION_RE, что у h2_index) и навигация (nav, оглавление, крошки).
Прежнее поведение байт-в-байт возвращает tools.visual.density_basis: full.
Полное обоснование - блок-комментарий над prose_words_html и отчёт волны r7
`_rebuild/r7/gate-density-otchet.md`. Селфтест: --selftest-density.

🔴 ЧЕРНОВИК НОВОГО КОНТРАКТА (`engine: article_build`, правка 12.08.2026, дефект Б1).
Черновик такого контракта - ШАБЛОН, а не готовая страница: адрес оффера, домен и
ссылка на гайд установки живут в конфиге автора и стоят в тексте подстановками
`{{cta_url}}` / `{{target_url}}` / `{{site}}` / `{{install_guide_url}}`, а сам
промо-блок часто выражен директивой `:::cta … button: …` - ссылку в неё подставляет
сборщик. Гейт, который ищет в таком файле готовый литерал адреса, краснеет ВСЕГДА:
стадия draft не могла стать зелёной в принципе, при этом собранная страница гейт
проходила. Признак контракта - строка `engine: article_build` в YAML-front-matter.
Для ТАКИХ файлов (и только для них) markdown-ветка:
  • разворачивает подстановки значениями ИЗ КОНФИГА и уже потом считает CTA,
    внутренние и контентные ссылки (ослабления нет: значения берутся из того же
    ключа, что и эталон проверки, чужой адрес сюда не попадёт);
  • засчитывает промо-директиву `:::cta` со строкой `button:` как ссылку на оффер -
    сборщик отказывает такому блоку без кнопки жёстко (article_build.render_cta),
    поэтому директива с кнопкой ДОКАЗЫВАЕТ ссылку, а не заменяет её обещанием;
  • H1 ищет в теле и в поле `h1:` front-matter, а `title:` считает МЕТА-заголовком
    (в этом контракте это два разных поля, и «задан дважды» тут ложняк); строки
    front-matter в счёт H1 не идут вовсе - `# …` внутри YAML это комментарий.
Файлы БЕЗ маркера (легаси-черновики, канон draft-skeleton) проверяются ровно как
раньше, байт-в-байт: ни один их вердикт этой правкой не сдвинут.

Выход: 0 - структура в порядке; 1 - есть замечания; 2 - ошибка входа/конфига
(нет файла черновика ИЛИ в конфиге нет ни cta.url, ни target_url).
Использование:
  python3 tools/structure-check.py $WORK/<slug>/draft.md
  python3 tools/structure-check.py $WORK/<slug>/index.html --visual
  python3 tools/structure-check.py draft.md --config config.yaml
  python3 tools/structure-check.py <page> --first-sentence-hard --own-blocks-hard --tool-article-hard
"""
import argparse
import os
import re
import sys
from html.parser import HTMLParser

try:
    from _config import load_config, find_config, get
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _config import load_config, find_config, get


def _label_stamp_counter():
    """Счётчик ярлыков-меток резюме из ai-cadence-check.py (один источник истины).

    Правило и пороги живут в ai-cadence-check.py; здесь только переиспользуем
    функцию, чтобы визуальный прогон по собранной странице ловил то же самое.
    Файл называется с дефисами, поэтому подключаем его по пути, а не import-ом.
    """
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ai-cadence-check.py")
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location("ai_cadence_check", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return getattr(mod, "count_label_stamps", None)


def strip_code_fences(text):
    """Убрать fenced-блоки ``` ``` - в коде свои # и ## не считаем заголовками."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


# ── CTA: cta.url → target_url → жёсткая ошибка конфига ───────────────────────

class ConfigError(Exception):
    """Конфиг не даёт ответа на обязательный вопрос. Не замечание к тексту -
    остановка прогона: молча проверять слабее нельзя."""


CONFIG_HELP_CTA = (
    "в конфиге не задан адрес целевого продукта: нет ни `cta.url`, ни `target_url`.\n"
    "Гейт «финал статьи ВСЕГДА ведёт на трипваер» без этого адреса непроверяем, а\n"
    "подмена его на «есть хоть какая-нибудь внешняя ссылка» - тихая деградация гейта.\n"
    "Почини так: открой config.md скилла (или свой config.yaml) и в yaml-блоке задай\n"
    "  target_url: https://<твой-домен>/<страница-трипваера>/\n"
    "либо явный блок\n"
    "  cta:\n"
    "    url: https://<твой-домен>/<страница-трипваера>/\n"
    "Значение-заглушка в угловых скобках (<...>) не считается заданным: такие поля\n"
    "_config.py вырезает специально, чтобы шаблон не выдавал себя за настройку."
)


def cta_present(text, cta_url):
    """Ссылка на целевой продукт есть на странице.

    Засчитываем и абсолютный адрес, и его относительную форму: относительный
    путь в href - та же самая ссылка на трипваер, что и абсолютная с доменом.
    Ослаблением это не является: путь берётся из САМОГО cta_url, чужая внешняя
    ссылка сюда не подходит.
    """
    if cta_url in text:
        return True
    path = re.sub(r"^https?://[^/]+", "", cta_url).rstrip("/")
    if not path or path == "":
        return False
    return bool(re.search(r'href="%s/?"' % re.escape(path), text))


def resolve_cta_url(cfg):
    """Адрес целевого продукта для проверки финального CTA.

    Порядок: cta.url (явный ключ) → target_url (то, что реально живёт в config.md
    скилла) → ошибка конфига. Возврата «пусто, проверим послабее» больше нет.
    """
    for key in ("cta.url", "target_url", "cta.target_url", "project.target_url"):
        val = get(cfg, key, "")
        if isinstance(val, str) and val.strip():
            return val.strip(), key
    raise ConfigError(CONFIG_HELP_CTA)


def resolve_cta_urls(cfg):
    """Список ВСЕХ допустимых адресов/префиксов оффера (приёмка по решению автора, MAJOR).

    Раньше гейт знал ровно один cta.url и падал, как только канон переходил на
    другую форму ссылки (например с общего лендинга на именной инвайт-префикс мессенджера на
    каждой странице). Теперь основной адрес (resolve_cta_url, как раньше) можно
    ДОПОЛНИТЬ списком альтернативных префиксов через `cta.accepted_prefixes` в
    config.md - целиком данные проекта, ни один префикс/домен в этом файле не
    хардкожен. Пустой/отсутствующий список = поведение не меняется (обратная
    совместимость со всеми конфигами без этого ключа)."""
    primary, key = resolve_cta_url(cfg)
    urls = [primary]
    extra = get(cfg, "cta.accepted_prefixes", None)
    if extra is None:
        # Ключ может отсутствовать в ПРОЕКТНОМ конфиге (find_config берёт ровно один
        # файл без мержа - скептик-раунд 2, MINOR: из cwd проекта гейт не видел
        # префиксы из корневого config.md скилла). Фолбэк ТОЛЬКО для этого ключа:
        # молча дочитываем config.md корня скилла. Нет и там - поведение прежнее.
        try:
            from _config import load_config as _lc
            _skill_cfg = _lc(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.md"))
            extra = get(_skill_cfg, "cta.accepted_prefixes", None)
        except Exception:
            extra = None
    if isinstance(extra, list):
        urls.extend(str(u).strip() for u in extra if str(u).strip())
    return urls, key


def cta_present_any(text, urls):
    """True если в тексте есть ссылка хотя бы на ОДИН из допустимых адресов/
    префиксов (resolve_cta_urls). Полноценный URL проверяется через cta_present
    (точное совпадение или его относительный путь). Префикс без протокола
    (например `<мессенджер>/+`, где хвост инвайта на каждой странице свой) засчитывается
    ТОЛЬКО внутри настоящего href-атрибута ссылки - скептик-раунд 2 показал, что
    подстрока по всему тексту тихо деградирует гейт (голый текст такого префикса без
    ссылки проходил). Остаточное ограничение задокументировано в config.md:
    префикс шире точной ссылки (любой инвайт по префиксу пройдёт), точная сверка
    «инвайт = карте страницы» живёт в волновой приёмке по карте, не здесь."""
    hrefs = None
    for u in urls:
        if not u:
            continue
        if u.startswith("http") and cta_present(text, u):
            return True
        if not u.startswith("http"):
            # префикс без протокола: cta_present сюда НЕ пускаем - его первая
            # ветка (`cta_url in text`) для префикса выродилась бы в ту самую
            # подстроку по всему тексту; считаем только настоящие href
            if hrefs is None:
                hrefs = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', text)
            if any(u in h for h in hrefs):
                return True
    return False


# ── черновик НОВОГО контракта (engine: article_build) ────────────────────────
# Полное «зачем» - в шапке файла, раздел «ЧЕРНОВИК НОВОГО КОНТРАКТА».
# Здесь НЕТ ни одного литерала автора: и признак контракта, и имена подстановок -
# часть публичного контракта сборщика, значения приезжают только из конфига.

FRONTMATTER_RE = re.compile(r"﻿?---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
ENGINE_MARK_RE = re.compile(r"^engine:\s*article_build\s*$", re.M)
DRAFT_TOKEN_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
# промо-директива черновика: `:::cta place=…` … `:::`, внутри обязана быть кнопка
CTA_DIRECTIVE_RE = re.compile(r"^:::cta\b[^\n]*\n(.*?)^:::[ \t]*$", re.M | re.S)
CTA_BUTTON_RE = re.compile(r"^\s*button:\s*\S", re.M)


def split_frontmatter(text):
    """(front-matter, тело). Нет front-matter - ("", исходный текст)."""
    m = FRONTMATTER_RE.match(text)
    return (m.group(1), text[m.end():]) if m else ("", text)


def is_article_build_draft(text):
    """Файл собирается новым конвейером: front-matter несёт `engine: article_build`."""
    fm, _ = split_frontmatter(text)
    return bool(fm) and bool(ENGINE_MARK_RE.search(fm))


def draft_token_values(cfg):
    """Значения подстановок черновика - ТОЛЬКО из конфига автора.

    Адрес оффера берётся тем же resolve_cta_url, что и эталон проверки CTA:
    подставить сюда чужой адрес нечем. utm-хвост, который сборщик дописывает к
    {{cta_url}}, гейту безразличен - он проверяет адрес оффера, а не его метки.
    """
    target, _key = resolve_cta_url(cfg)
    domain = get(cfg, "project.domain", "") or get(cfg, "domain", "")
    host = re.sub(r"^https?://", "", str(domain or "")).rstrip("/")
    vals = {
        "target_url": target,
        "cta_url": target,
        "domain": host,
        "site": ("https://" + host) if host else "",
        "install_guide_url": (get(cfg, "install_guide_url", "")
                              or get(cfg, "project.install_guide_url", "")),
        "target_product": get(cfg, "target_product", "") or get(cfg, "project.target_product", ""),
    }
    return {k: str(v) for k, v in vals.items() if isinstance(v, str) and v.strip()}


def resolve_draft_tokens(text, cfg):
    """Развернуть известные подстановки. Неизвестные остаются как есть -
    ловить их работа сборщика (article_build падает на неизвестном токене)."""
    vals = draft_token_values(cfg)
    if not vals:
        return text
    return DRAFT_TOKEN_RE.sub(lambda m: vals.get(m.group(1), m.group(0)), text)


def cta_directive_present(text):
    """В черновике есть промо-блок `:::cta` со строкой `button:`.

    Это не послабление: сборщик отказывает блоку `:::cta` без `button:` жёстко
    («промо без ссылки на оффер»), а кнопке подставляет ровно {{cta_url}}. То
    есть наличие директивы с кнопкой ДОКАЗЫВАЕТ ссылку на оффер в собранной
    странице так же надёжно, как литерал адреса в тексте.
    """
    return any(CTA_BUTTON_RE.search(m.group(1)) for m in CTA_DIRECTIVE_RE.finditer(text))


# ── Ось first-sentence: первая фраза раздела (ZAKONY-SEO.md §13) ──────────
# Закон: ярлык-резюме («Коротко», «TL;DR») запрещён, ответ на заголовок несёт
# ПЕРВОЕ ПРЕДЛОЖЕНИЕ раздела. Три критерия канона + запрет разгона - здесь они
# впервые проверяются машинно (до этой редакции правило жило в 5 файлах канона и
# не проверялось ни одним инструментом; замер корпуса: 73% разделов вне вилки).

FS_MIN_WORDS = 15
FS_MAX_WORDS = 40

# Первое слово-местоимение = субъект не назван, раздел не читается в отрыве.
# Список ЗАКРЫТЫЙ (личные, указательные, притяжательные, определительные).
# Вопросительные «что/кто/какой» сознательно НЕ включены: «Что делать, если…» -
# законное начало, это не потерянный субъект.
# Самостоятельные (замещают существительное): «Это значит…», «Он берёт…» -
# субъекта в фразе нет, всегда замечание.
FS_PRONOUNS = {
    "я", "ты", "он", "она", "оно", "мы", "вы", "они",
    "это", "то", "тут", "там", "здесь", "себя", "его", "её", "ее", "их",
}
# Признаковые (стоят ПРИ существительном): «Весь движок собирается в Claude Code» -
# субъект назван, замечания нет. Ловим их только когда следом идёт второе
# местоимение, то есть группа снова пустая: «Всё это…», «Все они…», «Тот самый…».
FS_PRONOUNS_ATTR = {
    "этот", "эта", "эти", "тот", "та", "те", "такой", "такая", "такое", "такие",
    "мой", "моя", "моё", "мое", "мои", "твой", "твоя", "твоё", "твое", "твои",
    "наш", "наша", "наше", "наши", "ваш", "ваша", "ваше", "ваши",
    "сам", "сама", "само", "сами", "всё", "все", "весь", "вся",
    "каждый", "любой", "который", "которая", "которое", "которые",
}

# Старты-разгоны: фраза начинается с подводки вместо ответа. Список закрытый,
# формулировки - из канона (methodology:521, :577, structure-skeleton.md:7).
FS_RUNUP = [
    "в этом разделе", "в этой части", "в этой главе", "в данном разделе",
    "давайте", "если коротко", "коротко говоря", "прежде чем", "перед тем как",
    "начнём с", "начнем с", "для начала", "поговорим", "разберёмся", "разберемся",
    "стоит отметить", "стоит сказать", "как известно", "ниже разберём",
    "ниже разберем", "сейчас разберём", "сейчас разберем", "как мы уже",
]
FS_RUNUP_RE = re.compile(r"^\s*(?:%s)\b" % "|".join(re.escape(x) for x in FS_RUNUP), re.I)

# Конкретика внутри фразы: число, латиница (название/команда), имя собственное
# в середине фразы, текст в кавычках, путь/флаг команды.
FS_CONCRETE = [
    (re.compile(r"\d"), "число"),
    (re.compile(r"[A-Za-z]{2,}"), "латиница (название/команда)"),
    (re.compile(r"[«\"'][^«»\"']{2,}[»\"']"), "кавычки"),
    (re.compile(r"(?:^|\s)(?:--?[a-z]|/[a-zа-яё])"), "команда/путь"),
    (re.compile(r"(?<=[\s(«])[А-ЯЁ][а-яё]{2,}"), "имя собственное"),
]

# Абзацы-НЕ-проза: метки, надзаголовки, моно-строки команд, подписи к картинкам.
# Первой фразой раздела считается первый ПРОЗАИЧЕСКИЙ абзац, метку пропускаем.
FS_SKIP_P_CLASS = re.compile(
    r"\b(eyebrow|kicker|label|caption|figcaption|meta|badge|tag|uppercase|font-mono)\b", re.I)

SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[«\"'(\[]?[A-ZА-ЯЁ0-9])")


def fs_words(sentence):
    """Слова фразы: токен считается словом, если в нём есть буква или цифра.
    Дефис-разделитель и одиночная пунктуация словами не считаются, а «robots.txt»
    и «VS Code» считаются так же, как их читает человек."""
    return [t for t in sentence.split() if re.search(r"[\wЀ-ӿ]", t)]


def first_sentence(paragraph):
    """Первое предложение абзаца (границы - точка/!/?/… + пробел + заглавная)."""
    p = re.sub(r"\s+", " ", paragraph).strip()
    if not p:
        return ""
    parts = SENT_SPLIT_RE.split(p)
    return parts[0].strip()


def check_first_sentence_items(items):
    """items = [(заголовок раздела, первый абзац|None)]. Вернуть список замечаний.

    Проверяем ровно то, что задано каноном:
      a) длина 15-40 слов;
      b) первое слово не местоимение (закрытый список FS_PRONOUNS);
      c) внутри есть конкретика (число / латиница / кавычки / команда / имя);
      d) фраза не начинается со старта-разгона (закрытый список FS_RUNUP).
    """
    out = []
    for title, para in items:
        tag = f"«{(title or '?')[:50]}»"
        if para is None:
            out.append(f"first-sentence {tag}: нет первого абзаца после H2 - "
                       "ответ на заголовок нести нечем")
            continue
        s = first_sentence(para)
        if not s:
            out.append(f"first-sentence {tag}: первый абзац пустой")
            continue
        words = fs_words(s)
        n = len(words)
        if not (FS_MIN_WORDS <= n <= FS_MAX_WORDS):
            out.append(f"first-sentence {tag}: {n} слов, вилка {FS_MIN_WORDS}-{FS_MAX_WORDS} "
                       f"(«{s[:70]}»)")
        def _norm(w):
            return re.sub(r"[^\wЀ-ӿ-]", "", w).lower()
        first_word = _norm(words[0]) if words else ""
        second_word = _norm(words[1]) if len(words) > 1 else ""
        bare = first_word in FS_PRONOUNS
        attr_empty = (first_word in FS_PRONOUNS_ATTR and
                      (second_word in FS_PRONOUNS or second_word in FS_PRONOUNS_ATTR))
        if bare or attr_empty:
            out.append(f"first-sentence {tag}: начинается с местоимения «{words[0]}» - "
                       "субъект не назван, раздел не читается в отрыве")
        if not any(rx.search(s) for rx, _ in FS_CONCRETE):
            out.append(f"first-sentence {tag}: нет конкретики (число / латиница / кавычки / "
                       f"команда / имя собственное): «{s[:70]}»")
        m = FS_RUNUP_RE.match(s)
        if m:
            out.append(f"first-sentence {tag}: старт-разгон «{m.group(0).strip()}» вместо "
                       "ответа на заголовок")
    return out


def first_paragraphs_html(text):
    """[(текст контентного H2, первый прозаический абзац|None)] по собранной странице.

    Служебные блоки шаблона (FAQ, «читайте также», источники, финальный CTA, автор,
    шаринг) в ось не идут: их H2 - часть шаблона, а не раздел статьи.
    """
    p = html_parts(text)
    body = p["body"]
    idx = p["h2_index"]
    parts = re.split(r"(<h2\b[^>]*>.*?</h2>)", body, flags=re.I | re.S)
    out, k = [], 0
    for i in range(1, len(parts), 2):
        meta = idx[k] if k < len(idx) else {"text": "", "service": False}
        k += 1
        if meta["service"]:
            continue
        rest = parts[i + 1] if i + 1 < len(parts) else ""
        rest = re.sub(r"<figure\b.*?</figure>", " ", rest, flags=re.S | re.I)
        para = None
        for pm in re.finditer(r"<p\b([^>]*)>(.*?)</p>", rest, re.S | re.I):
            cls = _attr(pm.group(1) + ">", "class")
            if FS_SKIP_P_CLASS.search(cls):
                continue
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", pm.group(2))).strip()
            if txt:
                para = txt
                break
        out.append((meta["text"], para))
    return out


def first_paragraphs_md(text):
    """[(текст H2, первый абзац|None)] по markdown-черновику."""
    body = strip_code_fences(text)
    lines = body.splitlines()
    h2_idx = [i for i, ln in enumerate(lines) if re.match(r"^##\s+\S", ln)]
    out = []
    for n, i in enumerate(h2_idx):
        end = h2_idx[n + 1] if n + 1 < len(h2_idx) else len(lines)
        title = lines[i].lstrip("#").strip()
        if SERVICE_H2_TEXT_RE.match(title):
            continue
        para = None
        for ln in lines[i + 1:end]:
            s = ln.strip()
            if not s:
                continue
            if re.match(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\||!\[|<!--)", s):
                continue  # список, таблица, цитата, картинка, комментарий - не абзац
            para = re.sub(r"!\[.*?\]\(.*?\)", " ", s)
            para = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", para)
            para = re.sub(r"[*_`]", "", para).strip()
            break
        out.append((title, para))
    return out


# ── Ось chunk: H2-раздел как самодостаточный чанк под ИИ-выдачу ──────────────
# Правило и целевая вилка живут в seo-engine/checklists/seo-geo.md §2.10 (там же
# требования, которые машина не проверяет: вопросная формулировка H2, цитируемое
# число с источником в разделе). Здесь - только две машинные оси:
#
#   a) ОБЪЁМ РАЗДЕЛА. Единица извлечения у ИИ-выдачи - пассаж, а не страница:
#      раздел короче нижней границы нечего цитировать (обрывок без контекста),
#      длиннее верхней - режется посередине и цитата искажается. Целевая вилка
#      письма 150-400 слов, машинная терпимость шире (дефолт 120-450), чтобы
#      гейт ловил провал, а не разброс.
#   b) РАЗГОН В ПЕРВЫХ ДВУХ ПРЕДЛОЖЕНИЯХ. Ось first-sentence уже запрещает
#      разгон в ПЕРВОЙ фразе; чанк-слой требует прямого ответа в первых 2-3
#      предложениях, поэтому здесь проверяется ВТОРОЕ предложение того же
#      абзаца (первое не дублируем - его вердикт несёт first-sentence).
#
# Что НЕ входит в объём: код-блоки <pre>/``` и подписи <figure> - это не проза
# раздела, длинный листинг иначе делал бы любой шаг-инструкцию «нормальным».
# Служебные блоки шаблона (FAQ, чек-лист, «читайте также», источники, CTA,
# автор, шаринг) в ось не идут - как и в first-sentence.

CHUNK_MIN_WORDS = 120
CHUNK_MAX_WORDS = 450
CHUNK_TARGET = "150-400"


def _md_words(fragment):
    """Слова markdown-фрагмента: снять картинки, ссылки, разметку, теги."""
    t = re.sub(r"!\[.*?\]\(.*?\)", " ", fragment)
    t = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", t)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[|>*_`#-]", " ", t)
    return len(re.findall(r"[\wЀ-ӿ]+", t))


def chunk_sections_html(text):
    """[(текст контентного H2, слов в разделе)] по собранной странице."""
    p = html_parts(text)
    idx = p["h2_index"]
    parts = re.split(r"(<h2\b[^>]*>.*?</h2>)", p["body"], flags=re.I | re.S)
    out, k = [], 0
    for i in range(1, len(parts), 2):
        meta = idx[k] if k < len(idx) else {"text": "", "service": False}
        k += 1
        if meta["service"]:
            continue
        rest = parts[i + 1] if i + 1 < len(parts) else ""
        frag = re.sub(r"<(pre|figure)\b.*?</\1>", " ", rest, flags=re.S | re.I)
        out.append((meta["text"], html_words(frag)))
    return out


def chunk_sections_md(text):
    """[(текст H2, слов в разделе)] по markdown-черновику."""
    body = strip_code_fences(text)
    lines = body.splitlines()
    h2_idx = [i for i, ln in enumerate(lines) if re.match(r"^##\s+\S", ln)]
    out = []
    for n, i in enumerate(h2_idx):
        end = h2_idx[n + 1] if n + 1 < len(h2_idx) else len(lines)
        title = lines[i].lstrip("#").strip()
        if SERVICE_H2_TEXT_RE.match(title):
            continue
        out.append((title, _md_words("\n".join(lines[i + 1:end]))))
    return out


def chunk_items(text, html_mode):
    """[(заголовок, слов в разделе, первый прозаический абзац|None)].

    Разбиение и отбраковка служебных блоков у chunk_sections_* и
    first_paragraphs_* одни и те же, поэтому списки идут в одном порядке;
    при рассинхроне (битая вёрстка) абзац просто не подставляется.
    """
    fs = first_paragraphs_html(text) if html_mode else first_paragraphs_md(text)
    sec = chunk_sections_html(text) if html_mode else chunk_sections_md(text)
    out = []
    for i, (title, words) in enumerate(sec):
        para = fs[i][1] if (i < len(fs) and fs[i][0] == title) else None
        out.append((title, words, para))
    return out


def check_chunk_items(items, cfg=None):
    """Замечания оси chunk: объём раздела + разгон во втором предложении."""
    lo = int(get(cfg, "tools.structure.chunk_min_words", CHUNK_MIN_WORDS)) if cfg \
        else CHUNK_MIN_WORDS
    hi = int(get(cfg, "tools.structure.chunk_max_words", CHUNK_MAX_WORDS)) if cfg \
        else CHUNK_MAX_WORDS
    out = []
    for title, words, para in items:
        tag = f"«{(title or '?')[:50]}»"
        if not (lo <= words <= hi):
            out.append(f"chunk {tag}: {words} слов в разделе, вилка {lo}-{hi} "
                       f"(целевая {CHUNK_TARGET}) - раздел не читается как "
                       "самодостаточный пассаж")
        if not para:
            continue
        p = re.sub(r"\s+", " ", para).strip()
        sents = [s for s in SENT_SPLIT_RE.split(p) if s.strip()]
        if len(sents) < 2:
            continue
        m = FS_RUNUP_RE.match(sents[1].strip())
        if m:
            out.append(f"chunk {tag}: второе предложение начинается с разгона "
                       f"«{m.group(0).strip()}» - прямой ответ должен уложиться "
                       "в первые 2-3 предложения раздела")
    return out


# ── Ось own-blocks: невыводимый из модели материал (И4.7) ────────────────────
# Задача гейта: статью нельзя собрать целиком из головы модели. Признак обязан
# быть МАШИННО ПРОВЕРЯЕМЫМ, поэтому засчитываем только то, что видно в разметке:
#
#   1) data-own="screenshot|measure|quote|number|artifact" на любом элементе -
#      явная пометка блока автором (в markdown: строка `<!-- own:screenshot -->`).
#      Это основной способ: он же документирует, ЧТО именно свой;
#   2) <blockquote cite="http...">  - цитата с машинно читаемым источником
#      (в markdown: строка-цитата `> …` со ссылкой [текст](http...));
#   3) абзац, где в ОДНОМ предложении стоит число и внешняя ссылка -
#      «число с inline-источником» (в markdown: цифра и [..](http..) рядом).
#
# Что НЕ считается: обычная иллюстрация конвейера, таблица без источника, любая
# ссылка без числа рядом - всё это модель выводит сама, доказательством не служит.

OWN_KINDS = ("screenshot", "measure", "quote", "number", "artifact")
OWN_DATA_RE = re.compile(r'data-own\s*=\s*"([^"]*)"', re.I)
OWN_MD_MARK_RE = re.compile(r"<!--\s*own:([a-z]+)\s*-->", re.I)
# 🔴 r15 (по решению автора): в РЕЖИМЕ MARKDOWN ось own-blocks видела ТОЛЬКО комментарий
# `<!-- own:kind -->` и была слепа к обеим живым формам, которыми пользуются
# черновики: директиве (":::pre own=measure", ":::figure … own=measure") и сырому
# HTML прямо в тексте (<div class="vizblock" data-own="measure">, <p
# data-own="measure">). Итог тот же, что у гейта own-evidence: на draft.md, где
# own-блоки ЕСТЬ, счётчик показывал 0-1 и печатал мягкое «ничего не найдено».
# На собранной странице (html_mode) обе формы уже считались - слепа была только
# ветка черновика.
OWN_DIRECTIVE_RE = re.compile(
    r"^:::(?:pre|figure|table|code)\b[^\n]*?\bown\s*=\s*\"?([a-zA-Z_]+)\"?",
    re.I | re.M)
OWN_BLOCKQUOTE_RE = re.compile(r"<blockquote\b[^>]*\bcite\s*=\s*\"https?://[^\"]+\"", re.I)
_SENT_PIECE_RE = re.compile(r"[^.!?…]+[.!?…]?")


def _num_with_source_html(body):
    """Абзацы, где число и внешняя ссылка стоят в одном предложении.

    Абзац с собственной пометкой data-own не считается второй раз: иначе два
    реальных блока давали бы три засчитанных - гейт бы ослаб сам собой.
    """
    n = 0
    for pm in re.finditer(r"<p\b([^>]*)>(.*?)</p>", body, re.S | re.I):
        if OWN_DATA_RE.search(pm.group(1)):
            continue
        inner = pm.group(2)
        for piece in _SENT_PIECE_RE.findall(re.sub(r"\s+", " ", inner)):
            if re.search(r"\d", re.sub(r"<[^>]+>", " ", piece)) and \
               re.search(r"<a\b[^>]*href=\"https?://", piece, re.I):
                n += 1
                break
    return n


def _num_with_source_md(text):
    n = 0
    for para in re.split(r"\n\s*\n", strip_code_fences(text)):
        one = re.sub(r"\s+", " ", para).strip()
        if one.startswith(">"):
            continue
        # абзац с собственной пометкой data-own уже посчитан явной пометкой -
        # второй раз не берём (та же защита, что в _num_with_source_html)
        if OWN_DATA_RE.search(one):
            continue
        for piece in _SENT_PIECE_RE.findall(one):
            if re.search(r"\d", piece) and re.search(r"\]\(https?://", piece):
                n += 1
                break
    return n


def own_blocks(text, html_mode):
    """(всего, детализация) блоков собственного материала. Признаки - см. выше."""
    detail = {}
    marks = OWN_MD_MARK_RE.findall(text)
    if html_mode:
        marks += [v for v in OWN_DATA_RE.findall(text)]
        body = html_parts(text)["body"]
        # цитата с data-own уже посчитана как явная пометка - второй раз не берём
        quotes = len([m for m in OWN_BLOCKQUOTE_RE.findall(body)
                      if not OWN_DATA_RE.search(m)])
        nums = _num_with_source_html(body)
    else:
        # r15: черновик несёт own-блоки в ДВУХ формах, обе - явная пометка
        # автора и обе обязаны считаться (см. OWN_DIRECTIVE_RE выше)
        marks += OWN_DIRECTIVE_RE.findall(text)
        marks += [v for v in OWN_DATA_RE.findall(text)]
        quotes = len([ln for ln in text.splitlines()
                      if ln.strip().startswith(">") and re.search(r"\]\(https?://", ln)])
        nums = _num_with_source_md(text)
    for m in marks:
        key = m.strip().lower().split()[0] if m.strip() else "?"
        detail[f"data-own:{key}"] = detail.get(f"data-own:{key}", 0) + 1
    if quotes:
        detail["цитата с источником"] = quotes
    if nums:
        detail["число с inline-источником"] = nums
    return sum(detail.values()), detail


def check_own_blocks(text, html_mode, cfg):
    """Замечание, если блоков собственного материала меньше порога."""
    need = int(get(cfg, "tools.structure.min_own_blocks", 3))
    total, detail = own_blocks(text, html_mode)
    if total >= need:
        return []
    got = ", ".join(f"{k} ×{v}" for k, v in sorted(detail.items())) or "ничего не найдено"
    return [f"own-blocks: блоков собственного материала {total}, нужно >= {need} "
            f"({got}). Засчитываются: data-own=\"{'|'.join(OWN_KINDS)}\" на блоке, "
            "цитата <blockquote cite=\"http...\">, число с inline-ссылкой на источник "
            "в одном предложении"]


# ── Ось «статья-инструмент» (И9.2, по решению автора) ───────────────────────────────
# Правка автора: возвращаемость - это КАЧЕСТВО статьи ("статьи полезны,
# прикладные, экшены и insightful, к ним хочется возвращаться"), не подписка.
# Машинный прокси до появления Метрики-токена: считаем справочно-прикладные
# блоки, к которым реально возвращаются - чек-лист, таблица, код/команда с
# копи-кнопкой, нумерованные шаги. Обычная иллюстрация или абзац прозы в счёт
# не идут: возвращаемость дают ГОТОВЫЕ К ПОВТОРНОМУ ИСПОЛЬЗОВАНИЮ куски, не текст.

_MD_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_MD_CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s+\S")
_MD_NUM_STEP_RE = re.compile(r"^\s*\d+[.)]\s+\S")
_MD_FENCE_RE = re.compile(r"^\s*```")

_HTML_CONTAINER_CLASS_RE = re.compile(r'<(?:div|section|ul)\b[^>]*\bclass="([^"]*)"', re.I)
_HTML_OL_RE = re.compile(r"<ol\b[^>]*>(.*?)</ol>", re.I | re.S)
_HTML_LI_RE = re.compile(r"<li\b", re.I)


def _md_contiguous_blocks(lines, line_re):
    """Считает БЛОКИ (не строки): сколько раз запускается прерывистая серия
    строк, подходящих под line_re. Пустая строка не рвёт серию (пункты списка
    в markdown иногда разделены визуальным отступом без пустой строки, а
    маркированный список часто и вовсе идёт слитно) - серию рвёт строка,
    которая явно НЕ относится к списку (не пустая и не подходит под паттерн)."""
    blocks = 0
    in_block = False
    for ln in lines:
        if line_re.match(ln):
            if not in_block:
                blocks += 1
                in_block = True
        elif ln.strip() == "":
            continue  # пустая строка внутри списка не считается разрывом
        else:
            in_block = False
    return blocks


def tool_blocks(text, html_mode):
    """(всего, детализация) справочно-прикладных блоков: чек-лист, таблица,
    код-блок с копией, нумерованные шаги. Возвращает счёт БЛОКАМИ, не строками
    (список из 5 шагов - один блок, не пять)."""
    detail = {}
    if html_mode:
        body = html_parts(text)["body"]
        checklists = 0
        for cls in _HTML_CONTAINER_CLASS_RE.findall(body):
            tokens = cls.lower().split()
            if "checklist" in tokens:
                checklists += 1
        tables = len(re.findall(r"<table\b", body, re.I))
        code_pre = len(re.findall(r"<pre\b", body, re.I))
        steps = sum(1 for m in _HTML_OL_RE.finditer(body)
                    if len(_HTML_LI_RE.findall(m.group(1))) >= 2)
    else:
        # чек-листы/таблицы/шаги считаем по тексту БЕЗ fenced-блоков (иначе
        # нумерованный пример команд внутри ``` кода задвоил бы счёт шагов),
        # а сами код-блоки - по СЫРОМУ тексту (strip_code_fences их как раз убирает)
        stripped = strip_code_fences(text)
        lines = stripped.splitlines()
        checklists = _md_contiguous_blocks(lines, _MD_CHECKBOX_RE)
        tables = 0
        for i, ln in enumerate(lines[:-1]):
            if "|" in ln and _MD_TABLE_SEP_RE.match(lines[i + 1] or ""):
                tables += 1
        steps = _md_contiguous_blocks(lines, _MD_NUM_STEP_RE)
        code_pre = len(re.findall(r"^\s*```", text, re.M)) // 2

    if checklists:
        detail["чек-лист"] = checklists
    if tables:
        detail["таблица"] = tables
    if code_pre:
        detail["код-блок с копией"] = code_pre
    if steps:
        detail["нумерованные шаги"] = steps
    return sum(detail.values()), detail


def check_tool_blocks(text, html_mode, cfg):
    """Замечание, если справочно-прикладных блоков меньше порога (норматив
    min_tool_blocks, дефолт 3 - тот же порог, что у own-blocks, для единства)."""
    need = int(get(cfg, "tools.structure.min_tool_blocks", 3))
    total, detail = tool_blocks(text, html_mode)
    if total >= need:
        return []
    got = ", ".join(f"{k} ×{v}" for k, v in sorted(detail.items())) or "ничего не найдено"
    return [f"tool-article: справочно-прикладных блоков {total}, нужно >= {need} "
            f"({got}). Засчитываются: чек-лист (checkbox-список / class=\"checklist\"), "
            "таблица, код/команда в <pre> с копи-кнопкой, нумерованные шаги (>=2 п.)"]


# ── HTML-режим: разбор СОБРАННОЙ страницы ────────────────────────────────────

def is_html(path, text):
    """Собранная страница или markdown-черновик."""
    if path.lower().endswith((".html", ".htm")):
        return True
    return bool(re.search(r"<!doctype html|<html\b", text[:2000], re.I))


def html_parts(text):
    """Разобрать страницу на части для проверок.

    Выкидываем то, что не является контентом статьи: script/style/noscript
    (там живёт пиксель Метрики - <img> без alt, это не иллюстрация), комментарии.
    Тело берём из <article>/<main>, если они есть: шапка, сайдбар-TOC и подвал
    в объём статьи не входят.
    """
    clean = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", text,
                   flags=re.DOTALL | re.I)
    clean = re.sub(r"<!--.*?-->", " ", clean, flags=re.DOTALL)
    body = clean
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", clean, re.DOTALL | re.I)
        if m:
            body = m.group(1)
            break
    return {
        "full": clean,
        "body": body,
        "h1": re.findall(r"<h1\b[^>]*>", body, re.I),
        # H2 считаем по РЕАЛЬНОМУ дереву секций, а не по наличию id на самом теге -
        # см. h2_index() ниже
        "h2_all": [m.group(0) for m in re.finditer(r"<h2\b[^>]*>", body, re.I)],
        "h2_index": h2_index(body),
        "imgs": [(_attr(t, "alt"), _attr(t, "src"))
                 for t in re.findall(r"<img\b[^>]*>", body, re.I)],
        "figures": re.findall(r"<figure\b", body, re.I),
        "links": re.findall(r"<a\b[^>]*?href=\"([^\"]+)\"", body, re.I),
    }


def _attr(tag, name):
    m = re.search(rf'{name}="([^"]*)"', tag, re.I)
    return m.group(1) if m else ""


# Служебные блоки страницы: FAQ, чек-лист, «читайте также» / «соседние», источники,
# финальный CTA, шаринг, карточка автора. Их H2 - часть шаблона, а не разделы статьи,
# и в вилку длины не идут. Опознаём по id/class ЛЮБОЙ секции-предка, не по тексту
# заголовка: текст автор пишет свободно («Хочешь ещё таких разборов?» - это CTA).
SERVICE_SECTION_RE = re.compile(
    r"(faq|chitayte-takzhe|read-also|related|sosedn|chek-list|check-list|checklist|"
    r"istochnik|sources|\bcta\b|share|author|podpis)", re.I)

# Вторая нога опознания: секция-обёртка размечена одними утилитарными классами и
# зацепиться не за что (так свёрстаны служебные блоки длинной статьи-инструкции). Тогда
# смотрим на сам заголовок, но ТОЛЬКО по закрытому списку канонических названий
# служебных блоков - свободный текст CTA сюда не попадает и честно останется
# «контентным H2 без якоря», то есть замечанием
SERVICE_H2_TEXT_RE = re.compile(
    r"^(читайте также|дальше по теме|соседн\w+|похож\w+|частые вопросы|вопросы и ответы|"
    r"faq|источник\w*|официальные источник\w*|sources|чек-?лист\b.*)", re.I)


def h2_index(body):
    """Каждый H2 тела статьи с его местом в дереве секций.

    Возвращает список словарей: text · has_id (якорь на самом h2) ·
    anchored (якорь на h2 ИЛИ на ближайшей секции-обёртке) · service (лежит внутри
    служебного блока шаблона).

    Зачем не `<h2 ... id=`: на живых страницах часть контентных H2 якоря на себе не
    несёт - у секций-«частей» (`<section class="partbanner" id="part-vpn">`) якорь
    висит на СЕКЦИИ, а h2 внутри голый. Старый счётчик их терял: на
    живом лендинге он видел 13 разделов при 19 h2 в DOM и красил вилку
    8-14 зелёным, хотя контентных разделов там 16 и вилка пробита.
    """
    tokens = re.finditer(r"<section\b[^>]*>|</section\s*>|<h2\b[^>]*>(.*?)</h2>",
                         body, re.I | re.S)
    stack = []          # [(id, class), ...] - открытые секции
    out = []
    for m in tokens:
        tag = m.group(0)
        low = tag[:9].lower()
        if low.startswith("</section"):
            if stack:
                stack.pop()
        elif low.startswith("<section"):
            stack.append((_attr(tag, "id"), _attr(tag, "class")))
        else:
            open_tag = tag[:tag.index(">") + 1]
            has_id = bool(re.search(r"\bid=", open_tag, re.I))
            near_id = bool(stack and stack[-1][0])
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
            service = (any(SERVICE_SECTION_RE.search(f"{sid} {scls}")
                           for sid, scls in stack)
                       or bool(SERVICE_H2_TEXT_RE.match(text)))
            out.append({
                "text": text,
                "has_id": has_id,
                "anchored": has_id or near_id,
                "service": service,
            })
    return out


def html_words(fragment):
    """Слова видимого текста: снять теги, посчитать словоформы."""
    return len(re.findall(r"[\wЀ-ӿ-]+", re.sub(r"<[^>]+>", " ", fragment)))


# ═════════════════════════════════════════════════════════════════════════════
# ОСЬ ПЛОТНОСТИ ИЛЛЮСТРАЦИЙ - база счёта (правка 14.08.2026, волна r7)
# ═════════════════════════════════════════════════════════════════════════════
#
# ЧТО БЫЛО. Потребность в иллюстрациях считалась как `html_words(body) //
# words_per_image`, то есть от ПОЛНОГО объёма собранной страницы: проза плюс
# таблицы, плюс код-листинги, плюс FAQ, чек-лист, «Источники», «Читайте также»
# и финальный CTA. Канон при этом всегда говорил другое - `knowledge/
# visual-layer.md`: «1 иллюстрация на ~300 слов ТЕКСТА ТЕЛА». Код канон не
# реализовывал, и разрыв рос ровно на тех статьях, которые волна r7 считает
# лучшими: чем больше в статье таблиц и листингов (норматив r7 - минимум
# 3 таблицы на статью, они дают извлекаемость в ИИ-ответах), тем краснее гейт.
# Живой прогон: guide-ii-dlya-prodazh - 5900 «слов» полного объёма при
# 2507-3599 словах прозы, требование 16 иллюстраций при 3 фактических.
#
# ПОЧЕМУ ЭТО БЫЛ ДЕФЕКТ НОРМЫ, А НЕ СТАТЬИ - три независимых довода:
#   1) таблица и код-листинг САМИ являются визуальными элементами: требовать
#      иллюстрацию «на каждые 350 слов таблицы» = требовать картинку к картинке;
# 2) правило владельца: «зачем генерировать текст картинкой - это
#      ухудшает загрузку и не даёт пользы». Единственный способ добить плотность
#      до 16 - штамповать текст-карточки, то есть делать ровно запрещённое;
# 3) замер корпуса по решению автора по 44 ОПУБЛИКОВАННЫМ (принятым владельцем)
#      страницам: старая норма красит красным 21 из 44 = 48% корпуса. Гейт,
#      блокирующий половину принятого корпуса, - регресс, а не строгость.
#
# ЧТО СТАЛО. Ось разложена на ДВА независимых порога:
#   • ПОЛ (правка 19.08.2026 - добавлен .vizblock): минимум
#     `tools.visual.min_images` единиц - настоящая иллюстрация (<figure>) ИЛИ
#     HTML-блок .vizblock (vizsteps/vizcheck/vizcompare, штатный визуал шага
#     стандарта новичка) - на статью, сколько бы ни было таблиц и листингов.
#     Именно он ловит голое полотно текста и страницу-заглушку;
#   • ПЛОТНОСТЬ: считается от объёма ПРОЗЫ (см. prose_words_html ниже), а
#     закрывается ВИЗУАЛЬНЫМИ БЛОКАМИ - иллюстрация, таблица, код-листинг.
#     Потолок требуемого - `tools.visual.max_images_required`: линейный рост
#     требования на длинной статье и есть та механика, из-за которой гейт
#     упирался в «нужно 16».
# Прежнее поведение байт-в-байт возвращается ключом
# `tools.visual.density_basis: full` (аварийный выход, не дефолт).
#
# ЧТО ИСКЛЮЧАЕТСЯ ИЗ ОБЪЁМА ПРОЗЫ и почему:
#   <table>            - сама визуальный элемент (довод 1) и норматив r7;
#   <pre>              - код-листинг, сам визуальный элемент, набирается моно-
#                        шрифтом и разрывает полотно не хуже картинки;
#   <figure>           - иллюстрация вместе с подписью: подпись к картинке не
#                        проза статьи и не может требовать ещё одной картинки;
#   служебные секции   - FAQ, чек-лист, «Источники», «Читайте также», финальный
#                        CTA, шаринг, карточка автора: это шаблон страницы, а не
#                        текст статьи (тот же список, что у h2_index - один
#                        источник истины, SERVICE_SECTION_RE);
#   навигация          - <nav>, оглавление (aside/details с классом *toc*),
#                        хлебные крошки, промо-врезка <aside class="cta …">.
# Всё остальное (абзацы, списки, врезки, цитаты, заголовки разделов) - проза.

# Служебные и навигационные обёртки, которые прозой не являются. Список смыслов
# тот же, что у SERVICE_SECTION_RE (FAQ, чек-лист, источники, «читайте также»,
# CTA, шаринг, автор), плюс навигация: оглавление aside.toc-desktop /
# details.toc-mobile и хлебные крошки.
#
# 🔴 ПОЧЕМУ ОТДЕЛЬНЫЙ РЕГЭКСП, А НЕ SERVICE_SECTION_RE НАПРЯМУЮ: там совпадение
# ищется ПОДСТРОКОЙ, а ось плотности режет из объёма ЦЕЛЫЕ секции - цена ложного
# срабатывания несопоставима. Прецедент по решению автора (поймано на калибровке):
# «toc» сидит подстрокой в транслите «kar-TOC-hka», и у guide-kartochki-
# marketpleys из объёма прозы улетело 5 контентных секций из 10 (3753 → 1589
# слов). Поэтому здесь границы слова: короткие и опасные токены (toc, cta)
# требуют границы с ОБЕИХ сторон, остальные - хотя бы слева.
DENSITY_SERVICE_RE = re.compile(
    r"(?<![a-zа-я])("
    r"(?:toc|cta)(?![a-z])"
    r"|faq|chitayte-takzhe|read-also|related|sosedn|chek-list|check-list"
    r"|checklist|istochnik|sources|share|author|podpis"
    r"|breadcrumb|crumbs|hlebn"
    r")", re.I)

# Блоки, которые сами несут визуальную нагрузку: в объём прозы не идут и при
# этом ЗАСЧИТЫВАЮТСЯ как визуальные блоки при проверке плотности.
DENSITY_VISUAL_TAGS = ("figure", "table", "pre")


def _strip_matching_blocks(text, tag, pred):
    """Вырезать парные блоки <tag …>…</tag>, чей ОТКРЫВАЮЩИЙ тег проходит pred.

    Вложенность считается внутри своего же семейства тегов: <section> внутри
    <section> - один блок, а не два. Разные семейства обрабатываются отдельными
    вызовами, поэтому служебный <aside> внутри контентной <section> тоже виден.
    """
    pat = re.compile(rf"<{tag}\b[^>]*>|</{tag}\s*>", re.I)
    stack, spans = [], []
    for m in pat.finditer(text):
        if m.group(0)[1] != "/":
            stack.append((m.start(), m.group(0)))
        elif stack:
            start, open_tag = stack.pop()
            if not stack and pred(open_tag):
                spans.append((start, m.end()))
    out = text
    for s, e in reversed(spans):
        out = out[:s] + " " + out[e:]
    return out


def prose_words_html(body):
    """Объём ПРОЗЫ тела статьи: слова без визуальных блоков и служебных обёрток.

    Возвращает (слов_прозы, что_вырезано) - второй элемент печатается в отчёте,
    чтобы зелёный вердикт был проверяемым, а не «просто зелёным».
    """
    def service(open_tag):
        return bool(DENSITY_SERVICE_RE.search(open_tag))

    b = _strip_matching_blocks(body, "section", service)
    b = _strip_matching_blocks(b, "aside", service)
    b = _strip_matching_blocks(b, "details", service)
    b = _strip_matching_blocks(b, "nav", lambda t: True)
    for tag in DENSITY_VISUAL_TAGS:
        b = _strip_matching_blocks(b, tag, lambda t: True)
    return html_words(b), html_words(body) - html_words(b)


def visual_blocks_html(body):
    """Визуальные блоки тела: иллюстрации, таблицы, код-листинги.

    Иллюстрация = <figure>; если <figure> на странице нет вовсе (шаблон 1.0),
    в счёт идут голые <img> - тот же фолбэк, что был у прежней нормы.
    Листинг считается ПО ВЕРХНЕМУ УРОВНЮ: <pre><code>…</code></pre> - один
    листинг, а не два.
    """
    figures = len(re.findall(r"<figure\b", body, re.I))
    imgs = len(re.findall(r"<img\b", body, re.I))
    tables = len(re.findall(r"<table\b", body, re.I))
    listings = len(_balanced_blocks(body, ("pre",)))
    # HTML-блоки-визуалы (правка владельца): бывшие текст-карточки
    # живут в теле классом .vizblock и разбивают полотно не хуже таблицы.
    # Граница слова после vizblock (конец кавычки или пробел перед модификатором,
    # правка 19.08.2026, фикс приёмки) - иначе паттерн совпадает и со штатной
    # подписью class="vizblock-title" (components.md), удваивая счёт контейнеров.
    vizblocks = len(re.findall(r'class="vizblock(?=["\s])', body, re.I))
    return {
        "figures": figures or imgs,
        "tables": tables,
        "listings": listings,
        "vizblocks": vizblocks,
        "total": (figures or imgs) + tables + listings + vizblocks,
    }


def density_norm(cfg):
    """Пороги оси плотности из конфига. Старый ключ words_per_image не сломан:
    он остаётся делителем, поменялась только БАЗА, к которой он применяется."""
    return {
        "per_words": int(get(cfg, "tools.visual.words_per_image", 350)),
        "min_images": int(get(cfg, "tools.visual.min_images", 3)),
        "basis": str(get(cfg, "tools.visual.density_basis", "prose") or "prose").lower(),
        "cap": int(get(cfg, "tools.visual.max_images_required", 10)),
        "blocks": bool(get(cfg, "tools.visual.count_visual_blocks", True)),
    }


def density_facts(body, cfg):
    """Всё, что нужно и оси, и отчёту: объёмы, блоки, требуемое число."""
    n = density_norm(cfg)
    full = html_words(body)
    prose, cut = prose_words_html(body)
    vis = visual_blocks_html(body)
    base = prose if n["basis"] == "prose" else full
    need = max(n["min_images"], base // max(n["per_words"], 1))
    if n["cap"] > 0:
        need = min(need, max(n["min_images"], n["cap"]))
    have = vis["total"] if n["blocks"] else vis["figures"]
    return {"norm": n, "full": full, "prose": prose, "cut": cut, "vis": vis,
            "base": base, "need": need, "have": have}


def density_report(body, cfg):
    """Честная строка про плотность. Печатается ВСЕГДА при --visual по HTML -
    без неё зелёный вердикт ничего не доказывает (та же логика, что у h2_report).
    """
    f = density_facts(body, cfg)
    n, v = f["norm"], f["vis"]
    basis = "проза" if n["basis"] == "prose" else "полный объём"
    return (f"Плотность: {basis} {f['base']} слов "
            f"(полный объём {f['full']}, вырезано {f['cut']}) · "
            f"нужно визуальных блоков {f['need']} "
            f"(1 на ~{n['per_words']}, потолок {n['cap'] or 'нет'}, "
            f"пол иллюстраций+vizblock {n['min_images']}) · "
            f"есть {f['have']} (иллюстраций {v['figures']} + vizblock-блоков "
            f"{v['vizblocks']} + таблиц {v['tables']} + листингов {v['listings']})")


# ── та же база плотности для markdown-черновика ──────────────────────────────
# Ветка .md ослаблена быть не должна: иначе один и тот же дефект виден одной
# командой и невидим другой (тот же принцип, что у оси ярлык-повтора).
_MD_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def _md_tables(text):
    """Markdown-таблицы БЛОКАМИ: строка с | , под ней строка-разделитель."""
    lines = strip_code_fences(text).splitlines()
    out = []
    for i, ln in enumerate(lines[:-1]):
        if "|" in ln and _MD_TABLE_SEP_RE.match(lines[i + 1] or ""):
            out.append(i)
    return out


def _md_strip_service_sections(text):
    """Вырезать служебные разделы хвоста черновика (FAQ, чек-лист, «Источники»,
    «Читайте также») по тому же закрытому списку названий, что у HTML-ветки."""
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if re.match(r"^#{2,3}\s+\S", ln)]
    drop = set()
    for k, i in enumerate(heads):
        title = lines[i].lstrip("#").strip()
        if SERVICE_H2_TEXT_RE.match(title) or _label_has_sources(title):
            end = heads[k + 1] if k + 1 < len(heads) else len(lines)
            drop.update(range(i, end))
    return "\n".join(ln for i, ln in enumerate(lines) if i not in drop)


def _internal(links, cfg):
    """Внутренние ссылки: корневые /… и абсолютные на СВОЙ домен.
    Share-ссылки соцсетей, где свой домен сидит внутри query, - чужие, не считаем."""
    domain = (get(cfg, "project.domain", "") or get(cfg, "domain", "") or "").strip("/")
    host = re.escape(domain.replace("https://", "").replace("http://", ""))
    n = 0
    for href in links:
        if href.startswith("/") and not href.startswith("//"):
            n += 1
        elif host and re.match(rf"https?://(www\.)?{host}(/|$)", href):
            n += 1
    return n


# Контентные материалы кластера: /guide-<slug>/ (лид-магнит-гайды) и
# /tema/<slug> (тематические хабы). Другие внутренние ссылки (CTA-бот,
# трипваер, соцсети, сама страница) в счёт ОСИ outbound-links не идут - ось
# меряет именно перелинковку на СВОИ ЖЕ материалы, ради которой её завели
# (см. ZAKONY-SEO.md §internal-links, Mueller "super critical").
CONTENT_LINK_RE = re.compile(r"^/(guide-[^/?#]+|tema/[^/?#]+|slovar(?:/[^/?#]+)?/?$)")


def _is_content_link(href, host_re):
    """href ведёт на /guide-*/ или /tema/*/ - свой контентный материал.
    Понимает и относительный путь, и полный URL на свой домен."""
    path = href
    if host_re:
        m = re.match(rf"https?://(www\.)?{host_re}(/.*)?$", href, re.I)
        if m:
            path = m.group(2) or "/"
    return bool(path.startswith("/") and CONTENT_LINK_RE.match(path))


def outbound_link_index(body):
    """Каждая ссылка `<a href=...>` тела статьи с флагом service - лежит ли
    она внутри служебной секции шаблона (FAQ/источники/чек-лист/«читайте
    также»/CTA/share/автор). То же дерево секций, что и в h2_index(): блок
    «Читайте также» на живом шаблоне - ИМЕННО `section#related`
    (knowledge/visual-layer.md), его якорь уже покрыт SERVICE_SECTION_RE."""
    tokens = re.finditer(
        r'<section\b[^>]*>|</section\s*>|<a\b[^>]*?href="([^"]+)"',
        body, re.I)
    stack = []
    out = []
    for m in tokens:
        tag = m.group(0)
        low = tag[:9].lower()
        if low.startswith("</section"):
            if stack:
                stack.pop()
        elif low.startswith("<section"):
            stack.append((_attr(tag, "id"), _attr(tag, "class")))
        else:
            service = any(SERVICE_SECTION_RE.search(f"{sid} {scls}")
                          for sid, scls in stack)
            out.append({"href": m.group(1), "service": service})
    return out


SOURCES_WORD = r"(источник\w*|sources)"
# слово ищем ВНУТРИ текста метки, а не только в её начале (см. _label_has_sources)
SOURCES_IN_TEXT = re.compile(rf"(?:^|[^\wЀ-ӿ]){SOURCES_WORD}(?:[^\wЀ-ӿ]|$)", re.I)
# заголовок раздела короткий; длинная фраза со словом «источник» внутри - это проза,
# а не метка блока, и в зелёный её красить нельзя
SOURCES_LABEL_MAX = 60


def _label_has_sources(inner_html):
    """Текст метки (без тегов) называет блок источников.

    Раньше искали `>\\s*(источник|sources)` - слово ОБЯЗАНО было стоять первым
    символом заголовка. Живая страница-лендинг имеет
    `<h2 id="oficialnye-istochniki">Официальные источники</h2>`: слово на втором
    месте, гейт писал «нет раздела Источники» и ронял exit 1 даже без флагов.
    Любой заголовок с прилагательным впереди («Полезные источники», «Источники и
    документация» - тут ок, а «Официальные источники» - нет) красился в красный.
    Теперь смотрим ВЕСЬ текст метки, но требуем, чтобы метка была короткой:
    иначе абзац-заголовок вида «Что делать, если источник данных недоступен»
    дал бы ложный зелёный.
    """
    text = re.sub(r"<[^>]+>", " ", inner_html)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > SOURCES_LABEL_MAX:
        return False
    return bool(SOURCES_IN_TEXT.search(text))


# ── Ось норматива перелинковки (И6.6, по решению автора) ────────────────────────────
# Матрица ГР п.6: >= 10 контекстных внутренних ссылок на статью - SOFT-стретч
# поверх HARD-минимума min_internal_links (дефолт 3, уже проверяется выше).
# Двери (кодословные) в подсчёт ВХОДЯТ, не исключаются: предупреждение не
# роняет exit, слабая перелинковка на двери всё равно должна быть видна в
# отчёте - в этом и цель мягкой оси, не в наказании.

def check_link_norm_html(text, cfg):
    """SOFT: контекстных внутренних ссылок в main/article >= норматив (дефолт 10)."""
    need = int(get(cfg, "tools.structure.link_norm_soft", 10))
    p = html_parts(text)
    internal = _internal(p["links"], cfg)
    if internal >= need:
        return []
    hard_min = int(get(cfg, "tools.structure.min_internal_links", 3))
    return [f"перелинковка: контекстных внутренних ссылок в main {internal}, "
            f"норматив >= {need} (soft-стретч поверх HARD-минимума {hard_min}; "
            "двери в подсчёт тоже идут, см. И6.6)"]


def check_link_norm_md(text, cfg):
    """SOFT-версия для .md-черновика: та же формула счёта, что HARD-ось п.6 в
    check_structure(), только порог выше и вердикт не роняет exit."""
    need = int(get(cfg, "tools.structure.link_norm_soft", 10))
    domain = get(cfg, "project.domain", "") or get(cfg, "domain", "")
    content_path = get(cfg, "project.content_path", "") or get(cfg, "content_path", "")
    internal = 0
    for m in re.finditer(r"\]\((.*?)\)", text):
        href = m.group(1)
        if href.startswith("/") or (domain and domain in href) or (content_path and content_path in href):
            internal += 1
    if internal >= need:
        return []
    hard_min = int(get(cfg, "tools.structure.min_internal_links", 3))
    return [f"перелинковка: внутренних ссылок в черновике {internal}, "
            f"норматив >= {need} (soft-стретч поверх HARD-минимума {hard_min}, см. И6.6)"]


def has_sources_block(clean_html):
    """Есть ли на СОБРАННОЙ странице блок «Источники».

    В шаблоне 2.0 служебные разделы (чек-лист, FAQ, источники, «Читайте также»)
    заголовком h2/h3 не размечаются - у них метка-надзаголовок
    `<p class="eyebrow">Источники</p>` (см. components.md шаблона, раздел
    «Нумерация шаговых разделов»). Поэтому ищем ЛЮБОЙ из трёх канонных вариантов:
    заголовок h2/h3, метку .eyebrow, секцию/заголовок с якорем istochnik*/sources.
    Раньше проверялся только h2/h3 с якорем в НАЧАЛЕ текста - гейт красил в красный
    реальные страницы, у которых блок источников на месте.
    """
    for m in re.finditer(r"<h[23]\b[^>]*>(.*?)</h[23]>", clean_html, re.I | re.DOTALL):
        if _label_has_sources(m.group(1)):
            return True
    for m in re.finditer(
            r'<([a-z]+)\b[^>]*class="[^"]*\beyebrow\b[^"]*"[^>]*>(.*?)</\1>',
            clean_html, re.I | re.DOTALL):
        if _label_has_sources(m.group(2)):
            return True
    # якорь блока: id="istochniki" / "oficialnye-istochniki" / "sources-h" и т.п.
    # Слово-слаг, а не любая подстрока: иначе id="resources" (ресурсы, не источники)
    # дал бы ложный зелёный. Поэтому перед словом либо начало id, либо дефис
    if re.search(r'<(section|div|h[23])\b[^>]*\bid="(?:[a-z0-9-]*-)?(istochnik|sources)[a-z0-9-]*"',
                 clean_html, re.I):
        return True
    return False


def check_structure_html(text, cfg):
    """Те же 6 проверок структуры, но по собранной странице."""
    issues = []
    p = html_parts(text)

    if len(p["h1"]) == 0:
        issues.append("нет H1 на странице")
    elif len(p["h1"]) > 1:
        issues.append(f"H1 несколько ({len(p['h1'])}), должен быть один")

    # H2 без контента
    chunks = re.split(r"<h2\b[^>]*>", p["body"], flags=re.I)[1:]
    for i, ch in enumerate(chunks):
        title = re.sub(r"<[^>]+>", "", ch.split("</h2>")[0]).strip()[:60]
        rest = ch.split("</h2>", 1)[1] if "</h2>" in ch else ""
        if html_words(rest) < 5:
            issues.append(f"пустой раздел H2: «{title}»")
    if not chunks:
        issues.append("нет ни одного H2 - статья без структуры разделов")

    if not has_sources_block(p["full"]):
        issues.append("нет раздела «Источники» / «Sources»")

    # CTA: адрес трипваера обязателен. Нет ни cta.url, ни target_url - это ошибка
    # конфига (ConfigError → exit 2), а не повод проверять слабее (см. шапку файла).
    # Принимаются ВСЕ адреса из resolve_cta_urls (основной + cta.accepted_prefixes).
    cta_urls, cta_key = resolve_cta_urls(cfg)
    if not cta_present_any(text, cta_urls):
        issues.append(f"нет ссылки на оффер ({cta_key}: {cta_urls[0]}, допустимо также: {cta_urls[1:]})")

    for alt, src in p["imgs"]:
        if not alt.strip():
            issues.append(f"картинка без alt-текста: ({src[:50]})")

    min_internal = int(get(cfg, "tools.structure.min_internal_links", 3))
    internal = _internal(p["links"], cfg)
    if internal < min_internal:
        issues.append(f"внутренних ссылок {internal}, минимум {min_internal} "
                      "(перелинковка на ваши же материалы)")

    # ось outbound-links: контентные (/guide-*/, /tema/*/), не блок «Читайте
    # также» и не остальная служебка - см. docstring файла, п.6b
    domain = (get(cfg, "project.domain", "") or get(cfg, "domain", "") or "").strip("/")
    host_re = re.escape(domain.replace("https://", "").replace("http://", ""))
    outbound = sum(1 for item in outbound_link_index(p["body"])
                   if not item["service"] and _is_content_link(item["href"], host_re))
    if outbound < min_internal:
        issues.append(f"контентных исходящих ссылок (/guide-*, /tema/*) {outbound}, "
                      f"минимум {min_internal} (перелинковка внутри текста статьи, "
                      "блок «Читайте также» и служебка в счёт не идут)")
    return issues


def h2_report(text):
    """Честная строка про H2: сколько в DOM, сколько контентных, сколько служебных.

    Печатается ВСЕГДА при --visual по HTML, в том числе когда вилка зелёная: без
    неё зелёный цвет ничего не доказывает - непонятно, что именно посчитано.
    """
    idx = html_parts(text)["h2_index"]
    content = [h for h in idx if not h["service"]]
    anchored = [h for h in content if h["anchored"]]
    return (f"H2: в теле {len(idx)} · контентных {len(content)} "
            f"(с якорем {len(anchored)}, без якоря {len(content) - len(anchored)}) · "
            f"служебных {len(idx) - len(content)}")


def check_visual_html(text, cfg):
    """Визуальные гейты 2.0 по СОБРАННОЙ странице (канон knowledge/visual-layer.md)."""
    issues = []
    p = html_parts(text)

    # ── ось плотности: ПОЛ иллюстраций + ПЛОТНОСТЬ визуальных блоков от прозы ──
    # (полное обоснование и что именно исключается - в блоке-комментарии над
    # prose_words_html; прежнее поведение возвращает density_basis: full)
    f = density_facts(p["body"], cfg)
    n, v = f["norm"], f["vis"]
    # ПОЛ - единица закрытия = иллюстрация (<figure>/<img>) ИЛИ HTML-блок
    # .vizblock (vizsteps/vizcheck/vizcompare) - правка 19.08.2026, приёмка
    # Фазы 1: .vizblock штатный визуал шага стандарта новичка (см. комментарий
    # выше «ОСЬ ПЛОТНОСТИ ИЛЛЮСТРАЦИЙ»), старая проверка `v["figures"] <
    # min_images` душила статьи без единой <figure>, у которых пол закрыт
    # vizblock-шагами.
    floor_units = v["figures"] + v["vizblocks"]
    if floor_units < n["min_images"]:
        issues.append(
            f"иллюстраций {v['figures']} + vizblock-блоков {v['vizblocks']} = "
            f"{floor_units}, нужно минимум {n['min_images']} - это ПОЛ оси "
            f"(иллюстрация ИЛИ .vizblock), он не закрывается ни таблицами, "
            f"ни листингами (таблиц {v['tables']}, листингов {v['listings']})")
    if f["have"] < f["need"]:
        what = ("визуальных блоков" if n["blocks"] else "иллюстраций")
        basis = "прозы" if n["basis"] == "prose" else "полного объёма"
        issues.append(
            f"{what} {f['have']}, нужно >= {f['need']} "
            f"({f['base']} слов {basis} = 1 на ~{n['per_words']}, "
            f"потолок требования {n['cap'] or 'нет'}; "
            f"есть иллюстраций {v['figures']} + vizblock-блоков {v['vizblocks']} "
            f"+ таблиц {v['tables']} + листингов {v['listings']})")

    # H2: считаем ВСЕ h2 тела статьи за вычетом служебных блоков шаблона.
    # Отдельно ругаемся на контентный H2 без якоря - он выпадает из TOC
    idx = p["h2_index"]
    content = [h for h in idx if not h["service"]]
    service = [h for h in idx if h["service"]]
    orphans = [h for h in content if not h["anchored"]]
    h2_n = len(content)
    # 🔴 ВИЛКА СНЯТА С ЭТАЛОНА, А НЕ ИЗ ГОЛОВЫ (по решению автора, круг 2, записи R71/R76).
    # Прежняя вилка 8-14 стояла НИЖЕ и эталона, и собственного живого корпуса, то есть
    # структурно запрещала новой странице собрать длинный хвост подынтентов - ровно ту
    # механику, которой конкурент нас обходит.
    # Замер (24 живые пары «наша против топ-3», delta-top3.json, снят по решению автора):
    #   топ-3 конкурентов, h2 всего: медиана 9.5 · p75 13 · p90 16.1 · max 21
    #   наш живой корпус, h2 всего: медиана 16 · p90 19 (14 страниц из 24 идут выше 14)
    #   лучшая страница эталона того же жанра (адрес донора держится в НЕраздаваемом
    #   каноне владельца движка - в раздаваемый файл чужой домен не вписывается):
    #     21 h2 всего = 19 КОНТЕНТНЫХ + 2 служебных, и хвост у неё именно подынтентовый
    #     («Что делать, если платёж не проходит», «Как отменить подписку и не платить
    #      лишнего», «Частые ошибки и как их избежать», «Как платить за Claude Code меньше»)
    # Отсюда потолок 20 = 19 контентных эталона плюс один слот запаса, пол 12 = выше
    # нынешних 9-10 нашего ближайшего по жанру аналога, но достижимо без воды.
    # Гейт зарегистрирован ТОЛЬКО на стадии page (article_gates.py, add("page", ...)),
    # поэтому пол судит НОВОЕ производство и задним числом корпус не роняет.
    h2_min = int(get(cfg, "tools.visual.h2_min", 12))
    h2_max = int(get(cfg, "tools.visual.h2_max", 20))
    log_h2 = (f"H2 в теле статьи {len(idx)} = контентных {h2_n} "
              f"(с якорем {len([h for h in content if h['anchored']])}, "
              f"без якоря {len(orphans)}) + служебных {len(service)}")
    if not (h2_min <= h2_n <= h2_max):
        issues.append(f"контентных H2 разделов {h2_n}, вилка {h2_min}-{h2_max}. {log_h2}")
    for h in orphans:
        issues.append(f"контентный H2 без якоря (не попадёт в TOC): «{h['text'][:60]}» - "
                      "дай id самому h2 или секции-обёртке")

    min_internal = int(get(cfg, "tools.visual.min_internal_links", 3))
    internal = _internal(p["links"], cfg)
    if internal < min_internal:
        issues.append(f"внутренних ссылок {internal}, визуальный норматив >= {min_internal}")

    alt_min = int(get(cfg, "tools.visual.alt_min", 50))
    alt_max = int(get(cfg, "tools.visual.alt_max", 125))
    for alt, src in p["imgs"]:
        n = len(alt.strip())
        if not (alt_min <= n <= alt_max):
            issues.append(f"alt {n} симв. (норма {alt_min}-{alt_max}): ({src[:50]})")

    # Ось ярлык-повтора отсюда УБРАНА (правка 04.08.2026): она считается всегда,
    # в main() через check_label_stamps(), а не только под --visual. Иначе один и
    # тот же дефект был виден одной командой и невидим другой.
    return issues


def check_label_stamps(text):
    """Ось ярлык-повтора. Единый вердикт (правка 04.08.2026): одинаковый ярлык
    первым блоком раздела 4 раза и больше = HARD, роняет exit; максимум 3.

    Считается ВСЕГДА, а не только под --visual: до правки один и тот же случай был
    soft в ai-cadence-check и hard здесь, а без флага не проверялся вообще -
    вердикт зависел от того, какую команду запустил агент.
    """
    issues = []
    counter = _label_stamp_counter()
    if counter is None:
        # гейт, который не смог загрузиться, обязан краснеть, а не молчать:
        # тихий пропуск ярлык-повтора уже давал зелёный отчёт при браке
        issues.append("ось ярлык-повтора не проверена: не загрузился "
                      "ai-cadence-check.py (count_label_stamps) рядом со скриптом - "
                      "почини импорт, пропускать эту ось нельзя")
    else:
        summary, other, _ = counter(text)
        total = sum(summary.values())
        if total > 1:
            top = ", ".join(f"«{k}» ×{v}" for k, v in
                            sorted(summary.items(), key=lambda kv: -kv[1]))
            issues.append(f"метка-резюме повторяется {total} раз ({top}), порог 1 на "
                          f"страницу: ответ несёт первая фраза раздела, ярлык-подпись "
                          f"и врезка-повтор в начале раздела не ставятся")
        for k, v in sorted(other.items(), key=lambda kv: -kv[1]):
            if v >= 4:
                issues.append(f"HARD одинаковый ярлык «{k}» ×{v} первым блоком раздела "
                              f"(максимум 3, четвёртое вхождение блокирует) - читается "
                              f"как разметка конвейера, а не как текст")
    return issues


# ==== Ось шаблонных H2 (правка 04.08.2026, И6.8 плана seo-dvizhok-3) ====
# Хвост волны замены дублей H2 (13.1д плана seo-dvizhok-2, карта замены -
# h2-map-2026-08-04.md/.json): пять информационных семейств заголовков
# штамповались слово-в-слово на десятках страниц корпуса и не несли предмета
# статьи (не отвечали на вопрос «про что этот раздел ИМЕННО в этой статье»).
# Ловим регэкспом ПО СОДЕРЖАНИЮ строки, а не по списку страниц - список устаревает
# на следующей же волне контента, а формулировка-клон нет. Родственная ось ярлык-
# повтора (label-stamp, count_label_stamps выше) ловит короткие ПОДПИСИ-метки
# первым блоком раздела; эта ось - буквальные ПОЛНЫЕ H2, слово-в-слово одинаковые
# на разных страницах. HARD: структурный брак заголовка (нет предмета), не
# стилевой выбор - как first-sentence/own-blocks, но без флага, всегда включена.
TEMPLATE_H2_FAMILIES = [
    ("N вещей, на которых застревают новички",
     re.compile(r"^(Три|Две|Одна)\s+вещ[а-я]*,\s*на\s+которых\s+застревают\s+новички$",
                re.I)),
    ("Что ты заберёшь из этого …",
     re.compile(r"^Что\s+ты\s+заберёшь\s+из\s+этого\s+(разбора|гайда|подборки)"
                r"(\s*\((TL;?DR|Коротко|Итого|Главное|Резюме|Суть)\))?$", re.I)),
    ("Коротко на возражения",
     re.compile(r"^Коротко\s+на\s+возражения$", re.I)),
    ("Частые затыки и трезвые ожидания",
     re.compile(r"^Частые\s+затыки(\s+и\s+трезвые\s+ожидания)?$", re.I)),
    ("Где в этой истории настоящие деньги",
     re.compile(r"^Где\s+в\s+этой\s+истории\s+настоящие\s+деньги$", re.I)),
]

# CTA-заголовок финального блока «Это первый шаг…» - тот же пересчёт 13.1д считает
# его дублем (12 страниц на момент этой редакции), но это закрывающая ПРОДАЮЩАЯ строка перед
# кнопкой оффера, а не информационный H2. Диверсифицировать закрывающий CTA пачкой
# страниц - решение владельца про конверсионный текст, не гейта (см. правило
# «закрытые решения владельца» в шапке плана seo-dvizhok-3). Поэтому эта строка
# ловится для видимости (advisory warning), но НЕ роняет exit, в отличие от пяти
# информационных семейств выше.
# Штамп CTA-заголовка - персональная настройка проекта: паттерн приходит из
# config (tools.structure.cta_stamp_re), в коде дефолта нет (инструмент раздаётся,
# чужой продукт/оффер здесь зашивать нельзя). Ключа нет - проверка молчит.
try:
    _cta_stamp = str(CFG.get("tools", {}).get("structure", {}).get("cta_stamp_re", "") or "")
except Exception:
    _cta_stamp = ""
TEMPLATE_H2_CTA = re.compile(_cta_stamp, re.I) if _cta_stamp else None


def extract_headings_for_template_check(text, html_mode):
    """Тексты H2 (и H3, где шаблон гнездится в TL;DR-врезке внутри H2-секции -
    живой лендинг: «Что ты заберёшь из этого разбора» сидело в h3)
    для оси шаблонных H2. HTML - снять теги из <h2>/<h3>; markdown - строки
    `## `/`### `.
    """
    out = []
    if html_mode:
        body = html_parts(text)["body"]
        for m in re.finditer(r"<h[23]\b[^>]*>(.*?)</h[23]>", body, re.I | re.S):
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
            if t:
                out.append(t)
    else:
        for ln in strip_code_fences(text).splitlines():
            m = re.match(r"^#{2,3}\s+(\S.*)$", ln)
            if m:
                out.append(m.group(1).strip())
    return out


def check_template_h2(text, html_mode):
    """Ось шаблонных H2. Возвращает (issues HARD, warnings advisory)."""
    issues = []
    warns = []
    for t in extract_headings_for_template_check(text, html_mode):
        matched = False
        for family, rx in TEMPLATE_H2_FAMILIES:
            if rx.match(t):
                issues.append(f"шаблонный H2 «{t}» (семейство «{family}») - заголовок не "
                              f"несёт предмета статьи, перепиши под конкретику раздела "
                              f"(инструмент/команда/число/действие из текста под ним), "
                              f"лучшая форма - вопрос, на который отвечает первое "
                              f"предложение раздела")
                matched = True
                break
        if not matched and TEMPLATE_H2_CTA and TEMPLATE_H2_CTA.match(t):
            warns.append(f"CTA-заголовок «{t}» совпадает со штампом из конфига "
                         f"(tools.structure.cta_stamp_re) - только предупреждение, гейт не роняет")
    return issues, warns


def frontmatter_title(text):
    """Заголовок из YAML-frontmatter черновика (канон draft-skeleton.md)."""
    m = re.match(r"﻿?---\s*\n(.*?)\n---\s*(\n|$)", text, re.DOTALL)
    if not m:
        return ""
    t = re.search(r"^title:\s*(.+?)\s*$", m.group(1), re.M)
    return t.group(1).strip().strip('"\'') if t else ""


def check_structure(text, cfg):
    issues = []
    # Черновик НОВОГО контракта - шаблон: подстановки разворачиваем значениями из
    # конфига ДО всех подсчётов (шапка файла, «ЧЕРНОВИК НОВОГО КОНТРАКТА»).
    # Легаси-черновик сюда не заходит вовсе - его текст не трогается.
    new_contract = is_article_build_draft(text)
    if new_contract:
        text = resolve_draft_tokens(text, cfg)
    body = strip_code_fences(text)
    lines = body.splitlines()

    # 1. Ровно один H1. В каноне черновика (`seo-engine/templates/draft-skeleton.md`)
    # заголовок живёт в frontmatter (`title:`), а не строкой `# ` - его рисует шаблон
    # страницы. Поэтому frontmatter-title засчитывается как H1, иначе гейт краснеет
    # на КАЖДОМ каноническом черновике.
    if new_contract:
        # у контракта article_build поля РАЗНЫЕ: `title:` - мета-заголовок вкладки,
        # `h1:` - заголовок страницы. Строки front-matter в счёт не идут: `# …`
        # внутри YAML это комментарий, а не H1 (дефект М3: спека-конвертер печатал
        # там 7 строк комментария, и гейт видел 8 заголовков H1).
        fm_raw, fm_body = split_frontmatter(text)
        body_lines = strip_code_fences(fm_body).splitlines()
        h1 = [ln for ln in body_lines if re.match(r"^#\s+\S", ln)]
        fm_h1 = re.search(r"^h1:\s*\S", fm_raw, re.M)
        if len(h1) > 1:
            issues.append(f"H1 несколько ({len(h1)}), должен быть один")
        elif not h1 and not fm_h1:
            issues.append("нет H1: ни строки `# Заголовок` в теле, ни поля h1 в frontmatter "
                          "(`title:` в этом контракте - мета-заголовок, не H1)")
    else:
        h1 = [ln for ln in lines if re.match(r"^#\s+\S", ln)]
        if len(h1) == 0 and not frontmatter_title(text):
            issues.append("нет H1: ни строки `# Заголовок`, ни поля title в frontmatter")
        elif len(h1) > 1:
            issues.append(f"H1 несколько ({len(h1)}), должен быть один")
        elif len(h1) == 1 and frontmatter_title(text):
            issues.append("заголовок задан дважды: и `title:` в frontmatter, и строка `# ` "
                          "в теле - на странице получится два H1")

    # 2. H2 без контента
    h2_idx = [i for i, ln in enumerate(lines) if re.match(r"^##\s+\S", ln)]
    for n, i in enumerate(h2_idx):
        end = h2_idx[n + 1] if n + 1 < len(h2_idx) else len(lines)
        chunk = "\n".join(lines[i + 1:end]).strip()
        if not chunk:
            issues.append(f"пустой раздел H2: «{lines[i].lstrip('# ').strip()}»")
    if not h2_idx:
        issues.append("нет ни одного H2 (## ) - статья без структуры разделов")

    # 3. Раздел источников. Слово ищем во ВСЁМ тексте заголовка, а не только
    # первым словом: «## Официальные источники» - такой же раздел источников,
    # как «## Источники» (тот же дефект, что был в HTML-ветке).
    if not any(_label_has_sources(ln.lstrip("#").strip())
               for ln in body.splitlines() if re.match(r"^#{2,3}\s+\S", ln)):
        issues.append("нет раздела «Источники» / «Sources»")

    # 4. CTA на оффер (тот же контракт, что в HTML-ветке: cta.url → target_url →
    # ошибка конфига; тихой деградации до «есть любая внешняя ссылка» больше нет).
    # Принимаются ВСЕ адреса из resolve_cta_urls (основной + cta.accepted_prefixes).
    cta_urls, cta_key = resolve_cta_urls(cfg)
    cta_ok = cta_present_any(text, cta_urls)
    if not cta_ok and new_contract:
        # промо-блок черновика нового контракта выражен директивой: ссылку в
        # кнопку подставляет сборщик, и без кнопки он такой блок не соберёт
        cta_ok = cta_directive_present(text)
    if not cta_ok:
        extra = (" · для черновика article_build годится и подстановка {{cta_url}}/"
                 "{{target_url}}, и промо-директива «:::cta … button: …»"
                 if new_contract else "")
        issues.append(f"нет ссылки на оффер ({cta_key}: {cta_urls[0]}, "
                      f"допустимо также: {cta_urls[1:]}){extra}")

    # 5. Alt у картинок
    for m in re.finditer(r"!\[(.*?)\]\((.*?)\)", text):
        if not m.group(1).strip():
            issues.append(f"картинка без alt-текста: ({m.group(2)[:50]})")

    # 6. Внутренние ссылки
    min_internal = int(get(cfg, "tools.structure.min_internal_links", 3))
    # домен берём и из project.domain (config.yaml), и из корневого domain (config.md скилла):
    # иначе при .md-конфиге счётчик внутренних ссылок всегда 0 и гейт врёт
    domain = get(cfg, "project.domain", "") or get(cfg, "domain", "")
    content_path = get(cfg, "project.content_path", "") or get(cfg, "content_path", "")
    internal = 0
    for m in re.finditer(r"\]\((.*?)\)", text):
        href = m.group(1)
        if href.startswith("/") or (domain and domain in href) or (content_path and content_path in href):
            internal += 1
    if internal < min_internal:
        issues.append(f"внутренних ссылок {internal}, минимум {min_internal} "
                      "(перелинковка на ваши же материалы)")

    # ось outbound-links: контентные (/guide-*/, /tema/*/) - см. docstring
    # файла, п.6b. В markdown-черновике служебной секции «Читайте также» ещё
    # нет физически (её ставит сборщик страницы при публикации, см.
    # HTML-ветку check_structure_html) - фильтр только по префиксу пути.
    host_re = re.escape((domain or "").replace("https://", "").replace("http://", ""))
    outbound = sum(1 for m in re.finditer(r"\]\((.*?)\)", text)
                   if _is_content_link(m.group(1), host_re))
    if outbound < min_internal:
        issues.append(f"контентных исходящих ссылок (/guide-*, /tema/*) {outbound}, "
                      f"минимум {min_internal} (перелинковка внутри текста статьи)")

    return issues


def check_visual(text, cfg):
    """Визуальный слой (шаблон 2.0). Включается ТОЛЬКО флагом --visual / --visual-warn:
    без флага поведение скрипта байт-в-байт старое.

      V1. ПОЛ единиц визуала (иллюстрация ИЛИ .vizblock, минимум min_images) и
          плотность визуальных блоков от объёма ПРОЗЫ - та же норма и тот же
          состав пола, что в HTML-ветке check_visual_html (выровнено по решению автора;
          см. блок-комментарий у prose_words_html).
      V2. H2 в вилке 8-14 (машинная вилка длины по интенту).
      V3. Внутренних ссылок >= 3 (перелинковка кластера).
      V4. alt у КАЖДОЙ картинки 50-125 символов (доступность + image-SEO).
    """
    issues = []
    body = strip_code_fences(text)

    # слова считаем по телу без code-fences и без markdown-картинок/ссылок-URL,
    # а с этой редакции - ещё и без markdown-таблиц и служебных разделов хвоста:
    # база плотности едина с HTML-веткой, иначе один и тот же дефект был бы
    # виден одной командой и невидим другой
    prose = re.sub(r"!\[.*?\]\(.*?\)", " ", body)
    prose = re.sub(r"\]\((.*?)\)", ")", prose)
    words_full = len(re.findall(r"[\wЀ-ӿ-]+", prose))
    prose = _md_strip_service_sections(prose)
    prose = _MD_TABLE_ROW_RE.sub(" ", prose)
    words = len(re.findall(r"[\wЀ-ӿ-]+", prose))

    imgs = re.findall(r"!\[(.*?)\]\((.*?)\)", text)
    imgs += [(m.group(1) or "", m.group(2) or "") for m in re.finditer(
        r'<img[^>]*?alt="([^"]*)"[^>]*?src="([^"]*)"', text)]
    n_img = len(imgs)
    n_table = len(_md_tables(text))
    n_listing = len(re.findall(r"^```", text, re.M)) // 2
    # .vizblock в ЧЕРНОВИКЕ - та же сырая HTML, что и на собранной странице
    # (проверено по корпусу: 55 черновиков lead-magnit-work несут блок формой
    # <div class="vizblock vizsteps">), поэтому и считается тем же паттерном,
    # что в HTML-ветке (visual_blocks_html) - второго закона счёта не заводим
    n_viz = len(re.findall(r'class="vizblock(?=["\s])', text, re.I))

    # V1: ПОЛ иллюстраций + плотность визуальных блоков от прозы
    n = density_norm(cfg)
    per_words, min_img = n["per_words"], n["min_images"]
    base = words if n["basis"] == "prose" else words_full
    need = max(min_img, base // max(per_words, 1))
    if n["cap"] > 0:
        need = min(need, max(min_img, n["cap"]))
    have = (n_img + n_table + n_listing + n_viz) if n["blocks"] else n_img
    # 🔴 ПОЛ ВЫРОВНЕН С HTML-ВЕТКОЙ (правка 22.08.2026). Единица закрытия пола -
    # иллюстрация ИЛИ .vizblock, ровно как в check_visual_html (там floor_units =
    # figures + vizblocks с этой редакции). Здесь vizblock не считался вовсе, и один
    # и тот же черновик стандарта новичка (шаги закрыты vizsteps, скринов нет)
    # краснел по стадии draft и был зелёным по стадии page - тот самый расход
    # веток, против которого написана вся эта ось («иначе один и тот же дефект
    # виден одной командой и невидим другой»).
    floor_units = n_img + n_viz
    if floor_units < min_img:
        issues.append(f"картинок {n_img} + vizblock-блоков {n_viz} = {floor_units}, "
                      f"нужно минимум {min_img} - это ПОЛ оси (иллюстрация ИЛИ "
                      f".vizblock), он не закрывается ни таблицами, ни листингами "
                      f"(таблиц {n_table}, листингов {n_listing})")
    if have < need:
        what = "визуальных блоков" if n["blocks"] else "картинок"
        basis = "прозы" if n["basis"] == "prose" else "полного объёма"
        issues.append(f"{what} {have}, нужно >= {need} "
                      f"({base} слов {basis} = 1 на ~{per_words}, потолок требования "
                      f"{n['cap'] or 'нет'}; есть картинок {n_img} + vizblock-блоков "
                      f"{n_viz} + таблиц {n_table} + листингов {n_listing})")

    # V2: вилка H2
    h2_n = len([ln for ln in body.splitlines() if re.match(r"^##\s+\S", ln)])
    # та же вилка, что и выше (замер эталона по решению автора, R71/R76): один источник чисел
    h2_min = int(get(cfg, "tools.visual.h2_min", 12))
    h2_max = int(get(cfg, "tools.visual.h2_max", 20))
    if not (h2_min <= h2_n <= h2_max):
        issues.append(f"H2 разделов {h2_n}, вилка {h2_min}-{h2_max}")

    # V3: внутренние ссылки >= 3 (та же логика счёта, что в базовой проверке)
    min_internal = int(get(cfg, "tools.visual.min_internal_links", 3))
    domain = get(cfg, "project.domain", "") or get(cfg, "domain", "")
    content_path = get(cfg, "project.content_path", "") or get(cfg, "content_path", "")
    internal = 0
    for m in re.finditer(r"\]\((.*?)\)", text):
        href = m.group(1)
        if href.startswith("/") or (domain and domain in href) or (content_path and content_path in href):
            internal += 1
    if internal < min_internal:
        issues.append(f"внутренних ссылок {internal}, визуальный норматив >= {min_internal}")

    # V4: длина alt
    alt_min = int(get(cfg, "tools.visual.alt_min", 50))
    alt_max = int(get(cfg, "tools.visual.alt_max", 125))
    for alt, src in imgs:
        n = len(alt.strip())
        if not (alt_min <= n <= alt_max):
            issues.append(f"alt {n} симв. (норма {alt_min}-{alt_max}): ({src[:50]})")

    return issues


# ═════════════════════════════════════════════════════════════════════════════
# ОСЬ «РЕНДЕР-ЦЕЛОСТНОСТЬ» - страница обязана дорендериться до конца
# ═════════════════════════════════════════════════════════════════════════════
#
# Все прочие оси читают ИСХОДНИК. Исходник бывает полным, а страница на экране -
# обрезанной: браузер читает содержимое raw-text элементов (style, script,
# textarea, title) не как разметку, а как сплошной текст до закрывающего тега.
# Один незакрытый (или неэкранированный) такой тег съедает всё, что ниже.
# Прецедент по решению автора: сырой <style> внутри листинга <pre><code> - разметка в
# файле есть, а 30% страницы до экрана не доехали, и ни одна ось этого не
# видела, потому что все они смотрели в исходник.
#
# Механика оси: гоняем страницу тем же стандартным html.parser, что лежит в
# основе браузерных парсеров по логике raw-text, и ловим три класса дефекта:
#   1) raw-text элемент открыт и не закрыт к концу документа;
#   2) в содержимом <pre>/<code> стоит СЫРОЙ открыватель raw-text элемента
#      (<style, <script, <textarea, <title) - класс «неэкранированный листинг»:
#      в листинге такой тег обязан быть экранирован (&lt;style ...);
#   3) видимый текст после ПОСЛЕДНЕГО <section id=...> пуст, хотя в исходнике
#      этой секции текст есть - страница обрывается раньше конца.

RAW_TEXT_TAGS = ("script", "style", "textarea", "title")
RAW_OPENER_RE = re.compile(r"<\s*(script|style|textarea|title)\b", re.I)
SECTION_ID_RE = re.compile(r'<section\b[^>]*\bid="([^"]+)"[^>]*>', re.I)


def _line_offsets(text):
    """Смещения начал строк: перевести (строка, колонка) парсера в позицию в файле."""
    offs, pos = [0], text.find("\n")
    while pos != -1:
        offs.append(pos + 1)
        pos = text.find("\n", pos + 1)
    return offs


def _balanced_blocks(text, tags):
    """Верхнеуровневые блоки <tag>…</tag> с учётом вложенности.

    Возвращает список (start, inner_start, inner_end, tag). Вложенные блоки того
    же семейства отдельно не отдаём: <pre><code>…</code></pre> - это ОДИН
    листинг, а не два, иначе один дефект отчитывался бы дважды.
    """
    alt = "|".join(tags)
    pat = re.compile(rf"<({alt})\b[^>]*>|</({alt})\s*>", re.I)
    stack, out = [], []
    for m in pat.finditer(text):
        if m.group(1):
            stack.append((m.group(1).lower(), m.start(), m.end()))
        elif stack:
            tag, start, inner_start = stack.pop()
            if not stack:
                out.append((start, inner_start, m.start(), tag))
    return out


def _section_spans(text):
    """Каждая <section id="…"> с границами по ПАРНОМУ </section> (учёт вложенности).

    Возвращает [(id, start, end), …] в документном порядке. Без парного
    закрывающего тега секция считается идущей до конца файла - это ровно тот
    случай, который ловит ось: хвост не дорисован.
    """
    spans = []
    for m in SECTION_ID_RE.finditer(text):
        depth, end = 0, len(text)
        for tok in re.finditer(r"<section\b[^>]*>|</section\s*>", text[m.start():], re.I):
            if tok.group(0)[1] == "/":
                depth -= 1
                if depth <= 0:
                    end = m.start() + tok.end()
                    break
            else:
                depth += 1
        spans.append((m.group(1), m.start(), end))
    return spans


class _RenderProbe(HTMLParser):
    """Проход страницы стандартным html.parser.

    Пишет две вещи: какие raw-text элементы остались открытыми к концу документа
    и на каких позициях исходника парсер выдал ВИДИМЫЙ текст. Содержимое
    script/style/textarea/title видимым текстом не считается (скип по стеку) -
    иначе CSS и JS выдавали бы себя за текст страницы.
    """

    def __init__(self, line_offsets):
        super().__init__(convert_charrefs=True)
        self._lines = line_offsets
        self.open_raw = []      # [(tag, offset)] - незакрытые raw-text элементы
        self.text_at = []       # [(offset, кусок видимого текста)]

    def _offset(self):
        line, col = self.getpos()
        idx = min(max(line - 1, 0), len(self._lines) - 1)
        return self._lines[idx] + col

    def handle_starttag(self, tag, attrs):
        if tag in RAW_TEXT_TAGS:
            self.open_raw.append((tag, self._offset()))

    def handle_endtag(self, tag):
        if tag in RAW_TEXT_TAGS:
            for i in range(len(self.open_raw) - 1, -1, -1):
                if self.open_raw[i][0] == tag:
                    del self.open_raw[i]
                    break

    def handle_data(self, data):
        if self.open_raw:
            return
        if data.strip():
            self.text_at.append((self._offset(), data))


def render_probe(text):
    """Прогнать страницу парсером. Возвращает (probe, ошибка_парсера|None)."""
    probe = _RenderProbe(_line_offsets(text))
    try:
        probe.feed(text)
        probe.close()
    except Exception as e:                                  # noqa: BLE001
        return probe, f"{e.__class__.__name__}: {e}"
    return probe, None


def check_render_integrity(text):
    """Ось «рендер-целостность»: страница обязана рендериться до конца."""
    findings = []
    probe, err = render_probe(text)
    if err:
        findings.append(f"рендер: html.parser не смог дочитать страницу ({err})")
        return findings

    # 1. незакрытый raw-text элемент - всё, что ниже, съедено
    for tag, off in probe.open_raw:
        findings.append(
            f"рендер: <{tag}> открыт в строке {text.count(chr(10), 0, off) + 1} и не "
            f"закрыт к концу документа - всё, что ниже, парсер читает как его "
            f"содержимое и на экран не выводит")

    # 2. неэкранированный листинг: сырой открыватель raw-text внутри <pre>/<code>
    for _start, inner_start, inner_end, tag in _balanced_blocks(text, ("pre", "code")):
        for hit in RAW_OPENER_RE.finditer(text[inner_start:inner_end]):
            off = inner_start + hit.start()
            findings.append(
                f"рендер: неэкранированный листинг - сырой «{hit.group(0)}» внутри "
                f"<{tag}> в строке {text.count(chr(10), 0, off) + 1}; в листинге его "
                f"надо писать как &lt;{hit.group(1).lower()}")

    # 3. хвост страницы не дорендерился
    spans = _section_spans(text)
    if spans:
        sid, start, end = spans[-1]
        src_visible = re.sub(r"<[^>]+>", " ", text[start:end]).strip()
        rendered = "".join(d for off, d in probe.text_at if start <= off < end).strip()
        if src_visible and not rendered:
            findings.append(
                f"рендер: последняя секция #{sid} в исходнике непустая "
                f"({len(src_visible)} симв. текста), но парсер не выдал из неё ни "
                f"одного видимого символа - страница обрывается раньше конца")
    return findings


# ═════════════════════════════════════════════════════════════════════════════
# ОСЬ «TOC-ПАРИТЕТ» - оглавление обязано совпадать с разделами страницы
# ═════════════════════════════════════════════════════════════════════════════
#
# Оглавление собирается отдельно от тела и потому легко отстаёт: разделы
# дописали, оглавление осталось прежним. Читатель видит короткий список и не
# знает про половину статьи, а поисковик берёт из TOC sitelinks. Три проверки:
#   1) каждый href="#x" имеет живой id="x" на странице (мёртвый якорь = обрыв);
#   2) паритет: пунктов в списке столько же, сколько секций <section id=…> с
#      <h2> в ОХВАЧЕННОМ этим списком диапазоне (от первой до последней секции,
#      на которую он ссылается). Дыры внутри диапазона называются поимённо.
#      Диапазон, а не «все секции страницы»: служебные хвосты вроде блока
#      «читайте также» в оглавление намеренно не кладут, и требовать их - ложняк;
#   3) если списков два (десктоп + мобильный), они обязаны совпадать по составу.
# Страницы без оглавления ось не трогает.

TOC_HINT_RE = re.compile(r"\btoc\b|table-of-contents|содержани|оглавлени|contents", re.I)
ANCHOR_HREF_RE = re.compile(r'<a\b[^>]*?href="([^"]+)"', re.I)
ID_ATTR_RE = re.compile(r'\bid="([^"]+)"', re.I)
NAME_ATTR_RE = re.compile(r'\bname="([^"]+)"', re.I)
TOC_MIN_ITEMS = 3


def toc_lists(text):
    """Списки-оглавления страницы.

    Оглавлением считаем <ul>/<ol>, где ВСЕ ссылки - якоря `#…` (минимум
    TOC_MIN_ITEMS штук) и контекст называет блок оглавлением: класс самого
    списка или обёртки содержит `toc`, либо рядом стоит подпись
    «Содержание»/«Оглавление»/«Contents». Список смешанных ссылок (часть на
    другие страницы) - это навигация, а не оглавление, и в ось не идёт.
    """
    out = []
    for start, inner_start, inner_end, _tag in _balanced_blocks(text, ("ul", "ol")):
        inner = text[inner_start:inner_end]
        hrefs = ANCHOR_HREF_RE.findall(inner)
        anchors = [h for h in hrefs if h.startswith("#")]
        if len(anchors) < TOC_MIN_ITEMS or len(anchors) != len(hrefs):
            continue
        context = text[max(0, start - 400):inner_start + 200]
        if not TOC_HINT_RE.search(context):
            continue
        out.append({"anchors": anchors, "line": text.count("\n", 0, start) + 1})
    return out


def check_toc_parity(text):
    """Ось «TOC-паритет»: оглавление == разделы страницы."""
    lists = toc_lists(text)
    if not lists:
        return []

    findings = []
    live_ids = set(ID_ATTR_RE.findall(text)) | set(NAME_ATTR_RE.findall(text))
    sec_ids = [sid for sid, start, end in _section_spans(text)
               if re.search(r"<h2\b", text[start:end], re.I)]
    order = {sid: i for i, sid in enumerate(sec_ids)}

    for lst in lists:
        # 1. мёртвые якоря
        for href in lst["anchors"]:
            target = href[1:]
            if target and target not in live_ids:
                findings.append(
                    f"TOC (список в строке {lst['line']}): якорь «{href}» ведёт в "
                    f"пустоту - id=\"{target}\" на странице нет")

        # 2. паритет пунктов и секций в охваченном диапазоне
        idx = [order[h[1:]] for h in lst["anchors"] if h[1:] in order]
        if not idx:
            continue
        covered = sec_ids[min(idx):max(idx) + 1]
        missing = [s for s in covered if ("#" + s) not in lst["anchors"]]
        if len(lst["anchors"]) != len(covered) or missing:
            msg = (f"TOC (список в строке {lst['line']}): пунктов "
                   f"{len(lst['anchors'])}, а секций с <h2> в охваченном диапазоне "
                   f"{len(covered)}")
            if missing:
                msg += "; не попали в оглавление: " + ", ".join("#" + s for s in missing)
            findings.append(msg)

    # 3. десктопный и мобильный списки обязаны совпадать по составу
    base = lists[0]["anchors"]
    for lst in lists[1:]:
        if lst["anchors"] != base:
            only_first = [a for a in base if a not in lst["anchors"]]
            only_this = [a for a in lst["anchors"] if a not in base]
            findings.append(
                f"TOC: списки оглавления расходятся (строки {lists[0]['line']} и "
                f"{lst['line']}): только в первом {only_first or '-'}, только во "
                f"втором {only_this or '-'}")
    return findings


# ── Селфтест обеих осей (позитив + негативы) ─────────────────────────────────

_ST_HEAD = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<title>Проверка</title><style>body{margin:0}</style></head><body>')
_ST_TAIL = "</article></main></body></html>"


def _st_toc(anchors, titles=None):
    items = "".join(f'<li><a href="#{a}">Раздел {a}</a></li>' for a in anchors)
    return ('<aside class="toc-desktop"><p class="toc-title">Содержание</p>'
            f'<ul class="toc-list">{items}</ul></aside>')


def _st_section(sid, body="<p>Живой текст раздела на несколько слов.</p>"):
    return f'<section id="{sid}"><h2>Заголовок {sid}</h2>{body}</section>'


def _selftest_render_toc():
    """Селфтест осей render-integrity и toc-parity: 1 позитив + 4 негатива."""
    cases = []

    # ── ПОЗИТИВ: здоровая страница, листинг экранирован, TOC полный ──────────
    ok = (_ST_HEAD + _st_toc(["a1", "a2", "a3"]) + "<main><article>"
          + _st_section("a1", "<p>Первый раздел.</p><pre><code>"
                              "&lt;style&gt;p{color:red}&lt;/style&gt;</code></pre>")
          + _st_section("a2") + _st_section("a3") + _ST_TAIL)
    cases.append(("позитив: здоровая страница", ok, [], []))

    # ── НЕГАТИВ 1: сырой <style> внутри <pre><code> ───
    bad_style = (_ST_HEAD + _st_toc(["a1", "a2", "a3"]) + "<main><article>"
                 + _st_section("a1", "<p>Первый раздел.</p><pre><code>"
                                     "<style>p{color:red}</code></pre>")
                 + _st_section("a2") + _st_section("a3") + _ST_TAIL)
    cases.append(("негатив: сырой <style> в листинге", bad_style,
                  ["не закрыт к концу документа", "неэкранированный листинг",
                   "обрывается раньше конца"], []))

    # ── НЕГАТИВ 2: TOC 7 пунктов при 12 секциях ──────────────────────────────
    ids12 = [f"s{i}" for i in range(1, 13)]
    thin_toc = (_ST_HEAD + _st_toc(["s1", "s2", "s3", "s4", "s5", "s11", "s12"])
                + "<main><article>" + "".join(_st_section(s) for s in ids12) + _ST_TAIL)
    cases.append(("негатив: TOC 7 пунктов при 12 секциях", thin_toc, [],
                  ["пунктов 7, а секций с <h2> в охваченном диапазоне 12",
                   "#s6", "#s10"]))

    # ── НЕГАТИВ 3: якорь на несуществующий id ────────────────────────────────
    dead = (_ST_HEAD + _st_toc(["a1", "a2", "net-takogo"]) + "<main><article>"
            + _st_section("a1") + _st_section("a2") + _st_section("a3") + _ST_TAIL)
    cases.append(("негатив: якорь на несуществующий id", dead, [],
                  ["ведёт в пустоту", 'id="net-takogo"']))

    # ── НЕГАТИВ 4: десктопный и мобильный TOC разошлись ──────────────────────
    split = (_ST_HEAD + _st_toc(["a1", "a2", "a3"])
             + '<details class="toc-mobile"><summary>Содержание</summary>'
               '<ul class="toc-list"><li><a href="#a1">1</a></li>'
               '<li><a href="#a2">2</a></li><li><a href="#a4">4</a></li></ul></details>'
             + "<main><article>" + _st_section("a1") + _st_section("a2")
             + _st_section("a3") + _st_section("a4") + _ST_TAIL)
    cases.append(("негатив: два TOC разошлись", split, [], ["списки оглавления расходятся"]))

    failed = 0
    for name, html, want_render, want_toc in cases:
        got_render = check_render_integrity(html)
        got_toc = check_toc_parity(html)
        errs = []
        if not want_render and got_render:
            errs.append(f"render должен молчать, а сказал: {got_render}")
        for needle in want_render:
            if not any(needle in f for f in got_render):
                errs.append(f"render не поймал «{needle}» (получено: {got_render})")
        if not want_toc and got_toc:
            errs.append(f"toc должен молчать, а сказал: {got_toc}")
        for needle in want_toc:
            if not any(needle in f for f in got_toc):
                errs.append(f"toc не поймал «{needle}» (получено: {got_toc})")
        status = "OK  " if not errs else "FAIL"
        if errs:
            failed += 1
        print(f"  [{status}] {name}")
        print(f"         render: {got_render or 'чисто'}")
        print(f"         toc:    {got_toc or 'чисто'}")
        for e in errs:
            print(f"         ! {e}")
    print(f"\nСелфтест render/toc: кейсов {len(cases)}, провалов {failed}")
    return 0 if failed == 0 else 1


# ═════════════════════════════════════════════════════════════════════════════
# СЕЛФТЕСТ ОСИ ПЛОТНОСТИ (правка 14.08.2026)
# ═════════════════════════════════════════════════════════════════════════════
# Кейсы построены так, чтобы каждый бил ровно в одно решение нормы: база счёта,
# пол иллюстраций, потолок требования, зачёт таблиц и листингов, аварийный
# возврат к прежнему поведению. Пороги в кейсах задаются явным cfg - селфтест не
# должен зависеть от того, какой config.yaml лежит рядом с прогоном.

_SD_HEAD = "<!doctype html><html><body><main><article>"
_SD_TAIL = "</article></main></body></html>"


def _sd_prose(n):
    """n слов чистой прозы абзацами по 50 слов."""
    para, out = " ".join(["слово"] * 50), []
    full, rest = divmod(n, 50)
    out += [f"<p>{para}</p>"] * full
    if rest:
        out.append("<p>" + " ".join(["слово"] * rest) + "</p>")
    return "".join(out)


def _sd_figs(n):
    return "".join(
        f'<figure><img src="a{i}.png" alt="Скриншот рабочего экрана с результатом '
        f'шага номер {i} подробно"><figcaption>Подпись к схеме {i}</figcaption>'
        f"</figure>" for i in range(n))


def _sd_vizblocks(n):
    """n HTML-блоков .vizblock.vizsteps - штатный визуал шага стандарта новичка
    (правка 19.08.2026, knowledge/novice-standard.md §5). Текст внутри нарочно
    однословный - иначе он раздувает объём ПРОЗЫ (div.vizblock не входит в
    DENSITY_VISUAL_TAGS и из прозы не вычитается) и калибровка кейсов поплывёт.
    Каждый блок несёт штатную подпись .vizblock-title (правка 19.08.2026, фикс
    дефекта счёта: незаякоренный regex совпадал и с ней) - селфтест обязан
    ловить именно этот класс дефекта, а не жить на разметке без подписи."""
    return "".join(
        f'<div class="vizblock vizsteps"><p class="vizblock-title">Заголовок{i}</p>'
        f'<ol><li>Шаг{i}</li></ol></div>'
        for i in range(n))


def _sd_tables(n, rows=6):
    cell = " ".join(["ячейка"] * 12)
    body = "".join(f"<tr><td>{cell}</td><td>{cell}</td></tr>" for _ in range(rows))
    return "".join(f"<table>{body}</table>" for _ in range(n))


def _sd_listings(n, lines=12):
    code = "\n".join(["python3 tools/script.py --flag value --other value"] * lines)
    return "".join(f"<pre><code>{code}</code></pre>" for _ in range(n))


def _sd_service(words=900):
    """Служебный хвост шаблона: FAQ, чек-лист, источники, «читайте также», CTA."""
    per = max(words // 5, 1)
    return ("".join(
        f'<section id="{sid}"><h2>{title}</h2>{_sd_prose(per)}</section>'
        for sid, title in (("faq", "Частые вопросы"),
                           ("checklist", "Чек-лист"),
                           ("istochniki", "Источники"),
                           ("related", "Читайте также")))
        + f'<section class="cta cta-final"><h2>Дальше</h2>{_sd_prose(per)}</section>')


def _sd_page(prose=0, figs=0, tables=0, listings=0, service=0, nav=False, vizblocks=0):
    parts = [_SD_HEAD]
    if nav:
        parts.append('<nav class="breadcrumbs"><a href="/">Главная</a> '
                     "<span>Гайды</span> <span>Эта статья</span></nav>"
                     '<details class="toc-mobile"><summary>Содержание</summary>'
                     "<ul><li><a href=\"#s1\">Первый длинный пункт оглавления</a></li>"
                     "<li><a href=\"#s2\">Второй длинный пункт оглавления</a></li>"
                     "</ul></details>")
    parts.append('<section id="s1"><h2>Раздел статьи</h2>')
    parts += [_sd_prose(prose), _sd_figs(figs), _sd_tables(tables),
              _sd_listings(listings), _sd_vizblocks(vizblocks), "</section>"]
    if service:
        parts.append(_sd_service(service))
    parts.append(_SD_TAIL)
    return "".join(parts)


def _sd_cfg(**over):
    v = {"min_images": 3, "words_per_image": 350, "density_basis": "prose",
         "max_images_required": 10, "count_visual_blocks": True}
    v.update(over)
    return {"tools": {"visual": v}}


def _selftest_density():
    """Селфтест оси плотности: 15 кейсов (позитивы + негативы + негатив-контроли).

    Проверяются ОБА полюса каждого решения: что норма пропускает и что она
    по-прежнему ловит. Замечания по alt/H2/ссылкам в кейсах не важны - смотрим
    только строки про плотность и про пол иллюстраций.
    """
    def density_issues(html, cfg):
        return [i for i in check_visual_html(html, cfg)
                if i.startswith(("иллюстраций", "визуальных блоков"))]

    cases = []

    # ── ПОЗИТИВ 1: класс дефекта из живого прогона по решению автора (guide-ii-dlya-prodazh) ──
    # 3600 слов прозы + 4 таблицы + 15 листингов + служебный хвост = по СТАРОЙ
    # норме «нужно 16 иллюстраций», по новой - визуальная нагрузка закрыта
    cases.append(("позитив: табличная статья волны r7 (3 фигуры, 4 таблицы, 15 листингов)",
                  _sd_page(prose=3600, figs=3, tables=4, listings=15,
                           service=900, nav=True), _sd_cfg(), []))

    # ── ПОЗИТИВ 2: та же страница по СТАРОЙ норме обязана краснеть ────────────
    # (доказывает, что зелёный из кейса 1 дала именно правка базы, а не случай)
    cases.append(("негатив-контроль: она же с density_basis=full = красная",
                  _sd_page(prose=3600, figs=3, tables=4, listings=15,
                           service=900, nav=True),
                  _sd_cfg(density_basis="full", count_visual_blocks=False),
                  ["иллюстраций 3, нужно >= 10"]))

    # ── НЕГАТИВ 1: голое полотно текста ───────────────────────────────────────
    cases.append(("негатив: полотно 3000 слов прозы с одной картинкой",
                  _sd_page(prose=3000, figs=1), _sd_cfg(),
                  ["нужно минимум 3", "визуальных блоков 1, нужно >= 8"]))

    # ── НЕГАТИВ 2: пол не закрывается таблицами и кодом ───────────────────────
    cases.append(("негатив: 0 иллюстраций при 6 таблицах и 10 листингах (пол)",
                  _sd_page(prose=2000, figs=0, tables=6, listings=10), _sd_cfg(),
                  ["иллюстраций 0 + vizblock-блоков 0", "нужно минимум 3"]))

    # ── НЕГАТИВ 3: тонкая страница-заглушка ───────────────────────────────────
    cases.append(("негатив: тонкая страница 900 слов без единого визуала",
                  _sd_page(prose=900, figs=0), _sd_cfg(),
                  ["иллюстраций 0 + vizblock-блоков 0", "визуальных блоков 0, нужно >= 3"]))

    # ── НЕГАТИВ 4: длинная проза без визуальной нагрузки ──────────────────────
    cases.append(("негатив: 4200 слов прозы, 4 иллюстрации, ни таблиц, ни кода",
                  _sd_page(prose=4200, figs=4), _sd_cfg(),
                  ["визуальных блоков 4, нужно >= 10"]))

    # ── ПОЗИТИВ 3: потолок требования держит длинную статью ───────────────────
    # 7000 слов прозы: без потолка норма потребовала бы 20 блоков
    cases.append(("позитив: 7000 слов прозы, потолок требования 10 закрыт 11 блоками",
                  _sd_page(prose=7000, figs=4, tables=3, listings=4), _sd_cfg(), []))
    cases.append(("негатив-контроль: тот же лист без потолка (cap=0) = красный",
                  _sd_page(prose=7000, figs=4, tables=3, listings=4),
                  _sd_cfg(max_images_required=0), ["нужно >= 20"]))

    # ── ПОЗИТИВ 4: служебный хвост в объём прозы не идёт ──────────────────────
    # 1000 слов статьи + 2500 слов служебного хвоста: старая норма требовала 10
    cases.append(("позитив: 1000 слов статьи и 2500 слов служебного хвоста",
                  _sd_page(prose=1000, figs=3, service=2500), _sd_cfg(), []))
    # needle - именно «слов полного объёма»: доказывает, что покраснела СТАРАЯ
    # база (служебный хвост учтён), а не потолок и не пол
    cases.append(("негатив-контроль: тот же хвост при density_basis=full = красный",
                  _sd_page(prose=1000, figs=3, service=2500),
                  _sd_cfg(density_basis="full", count_visual_blocks=False),
                  ["слов полного объёма"]))

    # ── ПОЗИТИВ 5: ровно на пороге - 3 иллюстрации при 1000 слов прозы ────────
    cases.append(("позитив: 1000 слов прозы и ровно 3 иллюстрации (пол = порог)",
                  _sd_page(prose=1000, figs=3), _sd_cfg(), []))

    # ── ПОЗИТИВ 6 (приёмка Фазы 1, П1-1): пол закрывается .vizblock БЕЗ единой
    # <figure> - новый стандарт новичка ставит vizsteps вместо скринов ─────────
    cases.append(("позитив: 0 иллюстраций, 3 .vizblock.vizsteps - пол закрыт стандартом новичка",
                  _sd_page(prose=1000, figs=0, vizblocks=3), _sd_cfg(), []))
    # ── НЕГАТИВ 6: vizblock тоже подчиняется полу, не освобождает от него ─────
    cases.append(("негатив: 0 иллюстраций, 2 .vizblock - пол НЕ закрыт (нужно 3 единицы)",
                  _sd_page(prose=1000, figs=0, vizblocks=2), _sd_cfg(),
                  ["иллюстраций 0 + vizblock-блоков 2"]))
    # ── ПОЗИТИВ 7: смешанный набор фигура + vizblock тоже закрывает пол ───────
    cases.append(("позитив: 1 иллюстрация + 2 .vizblock = 3 единицы, пол закрыт",
                  _sd_page(prose=1000, figs=1, vizblocks=2), _sd_cfg(), []))

    # ── НЕГАТИВ 5: КОНТЕНТНАЯ секция не должна опознаваться служебной ─────────
    # Прецедент калибровки по решению автора: «toc» подстрокой сидит в транслите
    # «kar-TOC-hka». Если границы слова сломать, из объёма улетят контентные
    # секции и полотно текста станет зелёным. Кейс это фиксирует:
    # 2800 слов прозы в секциях со «страшными» id, визуал только 2 иллюстрации.
    scary = "".join(
        f'<section id="{sid}"><h2>Раздел про {sid}</h2>{_sd_prose(700)}</section>'
        for sid in ("kartochka-tovara-i-neyroset",
                    "chastye-grabli-v-kartochkah",
                    "sostavlyaem-prospekt-vruchnuyu",
                    "octan-i-drugie-slova-lovushki"))
    cases.append(("негатив: контентные секции с «toc» внутри слова остаются прозой",
                  _SD_HEAD + scary + _sd_figs(2) + _SD_TAIL, _sd_cfg(),
                  ["иллюстраций 2 + vizblock-блоков 0", "нужно >= 8"]))

    failed = 0
    for name, html, cfg, want in cases:
        got = density_issues(html, cfg)
        errs = []
        if not want and got:
            errs.append(f"ось должна молчать, а сказала: {got}")
        for needle in want:
            if not any(needle in g for g in got):
                errs.append(f"не поймано «{needle}» (получено: {got})")
        if errs:
            failed += 1
        print(f"  [{'OK  ' if not errs else 'FAIL'}] {name}")
        print(f"         {density_report(html_parts(html)['body'], cfg)}")
        print(f"         замечания: {got or 'чисто'}")
        for e in errs:
            print(f"         ! {e}")
    print(f"\nСелфтест плотности: кейсов {len(cases)}, провалов {failed}")
    return 0 if failed == 0 else 1


EPILOG = """
Коды выхода: 0 - замечаний нет; 1 - есть замечания; 2 - ошибка входа или конфига
(нет файла; в конфиге нет ни cta.url, ни target_url).

ОСЬ first-sentence (закон ZAKONY-SEO.md §13 «ответ несёт первая фраза раздела»).
Для КАЖДОГО контентного H2 берётся первый прозаический абзац и его первое
предложение, дальше четыре машинных критерия:
  a) длина 15-40 слов;
  b) первое слово не местоимение (закрытый список: я/ты/он/она/мы/вы/они/это/
     этот/тот/такой/мой/твой/наш/ваш/его/её/их/себя/сам/весь/каждый/который/
     здесь/тут/там). Вопросительные «что/кто/какой» разрешены;
  c) внутри есть конкретика: число, латиница (название/команда), текст в
     кавычках, флаг/путь команды или имя собственное в середине фразы;
  d) фраза не начинается со старта-разгона (закрытый список: «в этом разделе»,
     «в этой части/главе», «давайте», «если коротко», «прежде чем», «перед тем
     как», «начнём с», «для начала», «поговорим», «разберёмся», «стоит
     отметить», «как известно», «ниже/сейчас разберём», «как мы уже»).
Служебные блоки шаблона (FAQ, «читайте также», источники, финальный CTA, автор,
шаринг) в ось не идут. По умолчанию ось SOFT: печатается как `~ soft`, на exit
не влияет. Флаг --first-sentence-hard делает её замечанием (exit 1).
🔴 Почему soft: замер корпуса по решению автора - 1331 раздел из 1818 (73%) вне вилки
15-40 слов, hard немедленно заблокировал бы весь корпус. Калибровка порогов и
переезд в hard - отдельным шагом после чистки корпуса.

ОСЬ own-blocks (гейт «>= 3 блоков собственного, невыводимого из модели материала»).
Машинно-проверяемый признак - только то, что видно в разметке:
  1) data-own="screenshot|measure|quote|number|artifact" на любом элементе -
     явная пометка собственного блока (скрин своего экрана, блок замера, своя
     цитата, число из своего опыта, свой артефакт). В markdown-черновике то же
     самое пишется строкой `<!-- own:screenshot -->` над блоком;
  2) <blockquote cite="https://..."> - цитата с машинно читаемым источником
     (в markdown: строка-цитата `> …` со ссылкой [текст](https://...));
  3) абзац, где ЧИСЛО и внешняя ссылка стоят в одном предложении - «число с
     inline-источником» (в markdown: цифра и [..](https://..) в том же
     предложении).
Не считаются: обычная иллюстрация конвейера, таблица без источника, ссылка без
числа рядом - всё это модель выводит сама и доказательством не служит.
Порог: tools.structure.min_own_blocks (дефолт 3). По умолчанию SOFT, флаг
--own-blocks-hard делает замечанием (exit 1).

ОСЬ tool-article (И9.2, гейт «статья-инструмент» - правка автора: «статьи
полезны, прикладные, экшены и insightful, к ним хочется возвращаться. Сбор
имейлов не сделает, чтобы человек вернулся» - возвращаемость это КАЧЕСТВО
статьи, не подписка). Считаются справочно-прикладные блоки БЛОКАМИ, не строками:
  1) чек-лист - в markdown серия строк `- [ ]`/`- [x]`, в HTML контейнер
     div/section/ul с классом ровно "checklist" (не "checklist-copy" - это кнопка);
  2) таблица - строка с `|`, за которой строка-разделитель `|---|---|` (markdown),
     или тег <table> (HTML);
  3) код/команда с копи-кнопкой - fenced-блок ``` ``` (markdown) или тег <pre>
     (HTML) - сайтовый шаблон вешает .copy-btn на КАЖДЫЙ <pre> в рантайме, поэтому
     достаточно факта <pre>, отдельный класс кнопки в статичной разметке не нужен;
  4) нумерованные шаги - серия строк `1. `/`1) ` минимум из 2 пунктов (markdown)
     или <ol> минимум с 2 <li> (HTML).
Не считаются: обычный маркированный список без чисел/чекбоксов, одиночная
таблица-заглушка, `<pre>` внутри блока источников (не наш случай - Источники
оформлены не кодом). Порог: tools.structure.min_tool_blocks (дефолт 3, тот же
что у own-blocks). По умолчанию SOFT, флаг --tool-article-hard делает
замечанием (exit 1). Калибровка по решению автора: длинная статья-инструкция (эталон,
8 <pre> + 2 <ol>) = 10 блоков, порог пройден; тонкая страница-заглушка
(0 <pre>/<ol>/<table>) = 0 блоков, порог не пройден - это и есть причина, почему
такие страницы называют "тонкими".

ОСЬ ярлык-повтора: одинаковый ярлык первым блоком раздела 4 раза и больше = HARD
(exit 1), максимум 3 вхождения. Единый вердикт с ai-cadence-check.py.

ОСЬ chunk (чанк-слой под ИИ-выдачу, правило - seo-engine/checklists/seo-geo.md
§2.10). Единица извлечения у ИИ-ответчиков и нейро-выдач - пассаж, а не страница,
поэтому каждый контентный H2 проверяется как самостоятельный чанк:
  a) объём раздела в вилке tools.structure.chunk_min_words -
     tools.structure.chunk_max_words (дефолт 120-450 при целевой письма 150-400).
     Код-блоки <pre>/``` и подписи <figure> в объём не входят: длинный листинг
     иначе делал бы «нормальным» любой шаг-инструкцию без прозы;
  b) второе предложение первого абзаца не начинается со старта-разгона (тот же
     закрытый список FS_RUNUP, что у оси first-sentence): прямой ответ обязан
     уложиться в первые 2-3 предложения раздела. Первое предложение здесь
     намеренно не проверяется второй раз - его вердикт несёт first-sentence.
Служебные блоки шаблона (FAQ, чек-лист, «читайте также», источники, CTA, автор,
шаринг) в ось не идут. По умолчанию SOFT, флаг --chunk-hard делает замечанием
(exit 1). Почему soft: ось заводится под НОВЫЕ статьи, старый корпус ей массово
не соответствует - hard заблокировал бы ревизии живых страниц.

ОСЬ render-integrity (только HTML). Все остальные оси читают ИСХОДНИК, а на
экран попадает РЕЗУЛЬТАТ разбора. Разница появляется на raw-text элементах
(style, script, textarea, title): их содержимое парсер читает как сплошной текст
до закрывающего тега, поэтому один незакрытый или неэкранированный такой тег
съедает всё, что ниже. Ось гоняет страницу стандартным html.parser
(convert_charrefs=True, содержимое script/style в видимый текст не идёт) и
флагает три класса:
  a) raw-text элемент открыт и не закрыт к концу документа;
  b) в содержимом <pre>/<code> стоит СЫРОЙ открыватель raw-text элемента
     (<style, <script, <textarea, <title) - «неэкранированный листинг»: в
     листинге он обязан быть записан как &lt;style ...;
  c) видимый текст после ПОСЛЕДНЕГО <section id=...> пуст, хотя исходник этой
     секции непустой - страница обрывается раньше конца.
Прецедент по решению автора: сырой <style> внутри <pre><code> съел 30% страницы -
разметка в файле была, на экране её не было, и ни одна ось этого не видела.
По умолчанию SOFT, флаг --render-hard делает замечанием (exit 1).

ОСЬ toc-parity (только HTML). Оглавление собирается отдельно от тела и легко
отстаёт: разделы дописали, оглавление осталось прежним. Оглавлением считается
<ul>/<ol>, где ВСЕ ссылки - якоря `#…` (минимум 3) и контекст называет блок
оглавлением (класс списка либо обёртки содержит `toc`, либо рядом подпись
«Содержание»/«Оглавление»/«Contents») - обычно это aside.toc-* и details.toc-*.
Проверяется:
  a) каждый href="#x" имеет живой id="x" (или name="x") на странице;
  b) паритет: пунктов в списке столько же, сколько секций <section id=...> с
     <h2> в ОХВАЧЕННОМ этим списком диапазоне - от первой до последней секции,
     на которую он ссылается. Дыры внутри диапазона называются поимённо.
     Диапазон, а не «все секции страницы»: служебные хвосты (блок «читайте
     также» после FAQ) в оглавление намеренно не кладут, требовать их - ложняк;
  c) если списков два (десктопный и мобильный) - они совпадают по составу якорей.
Страница без оглавления ось не трогает. По умолчанию SOFT, флаг --toc-hard
делает замечанием (exit 1).
Селфтест обеих осей: `python3 tools/structure-check.py --selftest-render-toc`
(позитив + 4 негатива: сырой <style> в листинге, TOC 7 пунктов при 12 секциях,
якорь на несуществующий id, разошедшиеся десктопный и мобильный списки).

ОСЬ ПЛОТНОСТИ ИЛЛЮСТРАЦИЙ (--visual). Два независимых порога:
  ПОЛ        - иллюстраций (<figure>; нет ни одной - считаем <img>) ПЛЮС
               HTML-блоков .vizblock (vizsteps/vizcheck/vizcompare - штатный
               визуал шага стандарта новичка, правка 19.08.2026) вместе не
               меньше tools.visual.min_images (дефолт 3). Ни таблицы, ни
               листинги его не закрывают: это защита от голого полотна текста;
  ПЛОТНОСТЬ  - визуальных блоков (иллюстрация + таблица + код-листинг) не меньше
               чем объём_прозы // tools.visual.words_per_image (дефолт 350),
               но не больше tools.visual.max_images_required (дефолт 10).
ОБЪЁМ ПРОЗЫ - тело статьи МИНУС <table>, <pre>, <figure>, служебные секции
хвоста (FAQ, чек-лист, источники, «читайте также», финальный CTA, шаринг,
автор) и навигация (nav, оглавление, хлебные крошки). Причина: таблица и
код-листинг сами являются визуальными элементами (требовать картинку на каждые
350 слов таблицы = требовать картинку к картинке), а служебный хвост - шаблон
страницы, а не текст статьи. Норматив волны r7 отдельно требует минимум
3 таблицы на статью - при старой базе два требования движка воевали друг с
другом: чем лучше статья по таблицам, тем краснее гейт визуала.
Ключи конфига (tools.visual): min_images · words_per_image · density_basis
(prose | full) · max_images_required (0 = без потолка) · count_visual_blocks.
`density_basis: full` + `count_visual_blocks: false` = прежнее поведение
байт-в-байт. Строка `Плотность: …` печатается при --visual ВСЕГДА, в том числе
на зелёном: без разложения «проза / полный объём / чем закрыто» зелёный вердикт
недоказуем. Селфтест: `--selftest-density` (15 кейсов - позитивы, негативы, негатив-контроли,
в том числе полотно 3000 слов с одной картинкой и контроль старой базы).
Все селфтесты разом: `--selftest`.
"""


def main():
    p = argparse.ArgumentParser(
        description="Механическая проверка структуры черновика статьи.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    p.add_argument("draft", nargs="?",
                   help="путь к черновику (.md) или собранной странице (.html)")
    p.add_argument("--config", default=None, help="путь к config.yaml (по умолч. ищется ./config.yaml)")
    p.add_argument("--visual", action="store_true",
                   help="добавить визуальные гейты 2.0 (картинки/H2/ссылки/alt) как замечания (влияют на exit); "
                        "гонять по СОБРАННОЙ странице index.html")
    p.add_argument("--visual-warn", action="store_true",
                   help="те же визуальные проверки, но warning-ами (на exit-код не влияют)")
    p.add_argument("--html", action="store_true",
                   help="форсировать HTML-режим (по умолчанию включается сам для .html)")
    p.add_argument("--first-sentence-hard", action="store_true",
                   help="ось first-sentence роняет exit 1 (по умолчанию soft-warn: "
                        "корпус на 73%% не соответствует, калибровка отдельным шагом)")
    p.add_argument("--own-blocks-hard", action="store_true",
                   help="ось own-blocks (>= 3 блоков собственного материала) роняет "
                        "exit 1 (по умолчанию soft-warn)")
    p.add_argument("--tool-article-hard", action="store_true",
                   help="ось tool-article (>= 3 справочно-прикладных блоков: чек-лист/"
                        "таблица/код с копией/шаги) роняет exit 1 (по умолчанию soft-warn)")
    p.add_argument("--chunk-hard", action="store_true",
                   help="ось chunk (объём H2-раздела в вилке + без разгона во втором "
                        "предложении) роняет exit 1 (по умолчанию soft-warn)")
    p.add_argument("--render-hard", action="store_true",
                   help="ось render-integrity (страница дорендеривается до конца: "
                        "незакрытый style/script, сырой тег в листинге, пустой хвост) "
                        "роняет exit 1 (по умолчанию soft-warn)")
    p.add_argument("--toc-hard", action="store_true",
                   help="ось toc-parity (оглавление совпадает с разделами, якоря живые, "
                        "десктоп и мобайл одинаковы) роняет exit 1 (по умолчанию soft-warn)")
    p.add_argument("--selftest-render-toc", action="store_true",
                   help="прогнать селфтест осей render-integrity и toc-parity "
                        "(позитив + 4 негатива) и выйти")
    p.add_argument("--selftest-density", action="store_true",
                   help="прогнать селфтест оси плотности иллюстраций "
                        "(база = проза, пол, потолок, зачёт таблиц и листингов) и выйти")
    p.add_argument("--selftest", action="store_true",
                   help="прогнать ВСЕ селфтесты скрипта подряд и выйти")
    args = p.parse_args()

    if args.selftest:
        rc = _selftest_render_toc()
        print()
        rc = _selftest_density() or rc
        sys.exit(rc)
    if args.selftest_render_toc:
        sys.exit(_selftest_render_toc())
    if args.selftest_density:
        sys.exit(_selftest_density())
    if not args.draft:
        p.error("нужен путь к черновику или странице (либо флаг --selftest-render-toc)")

    if not os.path.isfile(args.draft):
        sys.stderr.write(f"нет файла: {args.draft}\n")
        sys.exit(2)

    text = open(args.draft, encoding="utf-8").read()
    cfg_path = args.config or find_config()
    cfg = load_config(cfg_path)
    html_mode = args.html or is_html(args.draft, text)
    structure_fn = check_structure_html if html_mode else check_structure
    visual_fn = check_visual_html if html_mode else check_visual

    try:
        issues = structure_fn(text, cfg)
    except ConfigError as e:
        sys.stderr.write(f"ОШИБКА КОНФИГА (конфиг: {cfg_path or 'не найден'})\n{e}\n")
        sys.exit(2)
    if args.visual:
        issues += visual_fn(text, cfg)

    # Ось ярлык-повтора: HARD и БЕЗ флагов (единый вердикт с ai-cadence-check)
    issues += check_label_stamps(text)

    # Ось шаблонных H2: HARD и БЕЗ флагов, словарь пяти клонированных семейств
    # (И6.8, по решению автора); CTA-штамп - отдельно, advisory (см. комментарий у регэкспа)
    th_issues, th_warns = check_template_h2(text, html_mode)
    issues += th_issues

    # Оси-законы: считаются ВСЕГДА, вердикт зависит от флага (soft по умолчанию)
    fs_items = first_paragraphs_html(text) if html_mode else first_paragraphs_md(text)
    fs_findings = check_first_sentence_items(fs_items)
    own_findings = check_own_blocks(text, html_mode, cfg)
    tool_findings = check_tool_blocks(text, html_mode, cfg)
    softs = []
    if args.first_sentence_hard:
        issues += fs_findings
    else:
        softs += fs_findings
    if args.own_blocks_hard:
        issues += own_findings
    else:
        softs += own_findings
    if args.tool_article_hard:
        issues += tool_findings
    else:
        softs += tool_findings
    ch_items = chunk_items(text, html_mode)
    ch_findings = check_chunk_items(ch_items, cfg)
    if args.chunk_hard:
        issues += ch_findings
    else:
        softs += ch_findings

    # Оси рендер-целостности и TOC-паритета: смысл только у СОБРАННОЙ страницы -
    # в .md-черновике ни raw-text элементов, ни оглавления ещё нет
    render_findings = check_render_integrity(text) if html_mode else []
    toc_findings = check_toc_parity(text) if html_mode else []
    if args.render_hard:
        issues += render_findings
    else:
        softs += render_findings
    if args.toc_hard:
        issues += toc_findings
    else:
        softs += toc_findings

    # Ось норматива перелинковки (И6.6): ВСЕГДА soft, флага-эскалации до HARD
    # нет намеренно - это стретч-цель поверх HARD-минимума min_internal_links,
    # не отдельный обязательный порог публикации
    link_norm_fn = check_link_norm_html if html_mode else check_link_norm_md
    softs += link_norm_fn(text, cfg)

    print(f"Структура{' (HTML)' if html_mode else ''}: {os.path.basename(args.draft)}")
    # считаем разделы поштучно, а не парсим собственный текст замечаний:
    # одинаковые первые 50 символов заголовка и кавычки внутри названия иначе врут
    ok_fs = sum(1 for it in fs_items if not check_first_sentence_items([it]))
    print(f"  first-sentence: разделов {len(fs_items)} · без замечаний {ok_fs} · "
          f"замечаний {len(fs_findings)} "
          f"({'HARD' if args.first_sentence_hard else 'soft'})")
    own_total, own_detail = own_blocks(text, html_mode)
    print(f"  own-blocks: {own_total} "
          f"({', '.join(f'{k} ×{v}' for k, v in sorted(own_detail.items())) or 'нет'}) "
          f"({'HARD' if args.own_blocks_hard else 'soft'})")
    tool_total, tool_detail = tool_blocks(text, html_mode)
    print(f"  tool-article: {tool_total} "
          f"({', '.join(f'{k} ×{v}' for k, v in sorted(tool_detail.items())) or 'нет'}) "
          f"({'HARD' if args.tool_article_hard else 'soft'})")
    ch_lo = int(get(cfg, "tools.structure.chunk_min_words", CHUNK_MIN_WORDS))
    ch_hi = int(get(cfg, "tools.structure.chunk_max_words", CHUNK_MAX_WORDS))
    ch_in = sum(1 for _, w, _ in ch_items if ch_lo <= w <= ch_hi)
    ch_med = sorted(w for _, w, _ in ch_items)
    ch_med = ch_med[len(ch_med) // 2] if ch_med else 0
    print(f"  chunk: разделов {len(ch_items)} · в вилке {ch_lo}-{ch_hi} слов {ch_in} · "
          f"медиана {ch_med} · замечаний {len(ch_findings)} "
          f"({'HARD' if args.chunk_hard else 'soft'})")
    if html_mode:
        probe, perr = render_probe(text)
        raw_in_listing = sum(
            1 for _s, ist, iend, _t in _balanced_blocks(text, ("pre", "code"))
            for _h in RAW_OPENER_RE.finditer(text[ist:iend]))
        print(f"  render: незакрытых raw-text {len(probe.open_raw)} · листингов с "
              f"сырым тегом {raw_in_listing} · "
              f"{'парсер упал с ошибкой' if perr else 'парсер без ошибок'} · замечаний "
              f"{len(render_findings)} ({'HARD' if args.render_hard else 'soft'})")
        _toc = toc_lists(text)
        _sec = [s for s, st, en in _section_spans(text)
                if re.search(r"<h2\b", text[st:en], re.I)]
        print(f"  TOC: списков {len(_toc)} · пунктов "
              f"{[len(t['anchors']) for t in _toc] or 'нет TOC'} · секций с h2 "
              f"{len(_sec)} · замечаний {len(toc_findings)} "
              f"({'HARD' if args.toc_hard else 'soft'})")
    if (args.visual or args.visual_warn) and html_mode:
        # печатается ВСЕГДА, в том числе на зелёном: без разложения «проза /
        # полный объём / чем закрыто» зелёный вердикт оси плотности недоказуем
        print(f"  {density_report(html_parts(text)['body'], cfg)}")
        print(f"  {h2_report(text)}")
    if (args.visual or args.visual_warn) and not html_mode:
        print("  ~ визуальные гейты гоняются по СОБРАННОЙ странице: "
              "картинки и «Источники» живут в index.html, а не в .md-черновике")
    warnings = visual_fn(text, cfg) if (args.visual_warn and not args.visual) else []
    warnings += th_warns
    if not issues:
        print("  OK. Структурных замечаний нет.")
    else:
        print(f"  Замечаний: {len(issues)}")
        for it in issues:
            print(f"  ! {it}")
    for w in warnings:
        print(f"  ~ warning: {w}")
    for s in softs:
        print(f"  ~ soft: {s}")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
