#!/usr/bin/env python3
"""schema-generator.py - JSON-LD граф для статьи 2.0 <твой-домен>

Вход: JSON-файл с полями статьи (или stdin при "-"):
  title          str  ОБЯЗАТЕЛЬНО  заголовок статьи
  description    str  ОБЯЗАТЕЛЬНО  мета-описание
  url            str  ОБЯЗАТЕЛЬНО  канонический URL статьи
  image          str  ОБЯЗАТЕЛЬНО  абсолютный URL og/hero картинки
  datePublished  str  ОПЦИОНАЛЬНО  YYYY-MM-DD - честная дата ПЕРВОЙ публикации.
                                    Честного источника нет (типичный случай для
                                    ретрофита старых страниц) - НЕ передавать вовсе,
                                    поле в графе будет отсутствовать (как у about.html).
                                    Подставлять сюда дату из реестра content-sha lastmod
                                    ЗАПРЕЩЕНО - это дата ПОСЛЕДНЕЙ правки контента, а не
                                    первой публикации (баг волны 5, 49 страниц получили
                                    чужую дату как будто вышли только что).
  datePublishedSource str ОБЯЗАТЕЛЬНО, если передан datePublished. Гейт validate()
                                    требует один из ЛЕГАЛЬНЫХ префиксов (код-гейт, не
                                    доверие к формулировке), иначе сборка падает:
                                      "wayback:<timestamp14>:<snapshot_url>" - самый
                                        ранний снимок Wayback CDX API со statuscode:200
                                        (верхняя граница публикации, аудируема по URL)
                                      "sitemap-history:<file>:<date>" - страница есть в
                                        датированном срезе sitemap.xml/corpus (запасной
                                        источник, когда Wayback снимков нет вовсе)
                                      "spec.date_published" / "build_page.spec.date_published"
                                      свободная форма "...проверка сайта YYYY-MM-DD"
                                    Без источника или с нераспознанным префиксом
                                    datePublished передавать нельзя - гейт рубит сборку,
                                    чтобы класс бага волны 5 не вернулся.
  dateModified   str  ОБЯЗАТЕЛЬНО  YYYY-MM-DD - честная дата последней правки контента
                                    (обычно из content-sha-registry.json)
  faq            list ОПЦИОНАЛЬНО  [{"q": "...", "a": "..."}] -> FAQPage
  steps          list ОПЦИОНАЛЬНО  [{"name": "...", "text": "..."}] -> HowTo
  author         dict ОПЦИОНАЛЬНО  переопределение Person (name, url, image, sameAs...)
  pageKind       str  ОПЦИОНАЛЬНО  "article" (дефолт) | "profile"
  breadcrumbs    list ОПЦИОНАЛЬНО  [{"name": "...", "item": "https://..."}] - своя цепочка
  citation       list ОПЦИОНАЛЬНО  [{"name": "...", "url": "https://..."}] -> Article.citation[]
                                    (CreativeWork). Брать РОВНО из того же видимого блока
                                    «Источники», который уже отрисован на странице - не
                                    выдумывать источники, которых в статье нет
  wordCount      int  ОПЦИОНАЛЬНО  Article.wordCount - реальный счёт слов статьи (не прикидка)
  articleSection str  ОПЦИОНАЛЬНО  Article.articleSection - из уже существующей рубрики
                                    статьи; нет рубрики - поле не передавать

  Article ВСЕГДА получает isAccessibleForFree: true (контент открыт без пэйвола).

Выход: валидный JSON-LD @graph в stdout (или в файл через -o):
  pageKind=article (дефолт):
    Article + WebPage + WebSite + ImageObject + BreadcrumbList + Person + Organization
    + FAQPage (если faq) + HowTo (если steps)
  pageKind=profile (страница «Об авторе»):
    WebPage/ProfilePage (mainEntity -> Person) + WebSite + ImageObject + BreadcrumbList
    + Person + Organization + FAQPage (если faq). Узла Article нет: страница-профиль
    не статья, Article на ней вводит поисковик в заблуждение

Связность (эталон - живая /guide-neyropoisk/): узлов-сирот нет, каждая ссылка
{"@id": ...} резолвится в узел @graph. Article.isPartOf и mainEntityOfPage
указывают на #webpage, WebPage.isPartOf - на #website, картинка вынесена
в ImageObject #primaryimage, FAQPage/HowTo подшиты к #webpage.
Самопроверка связности встроена (build_graph -> assert_resolvable).

Использование:
  python3 schema-generator.py article.json
  python3 schema-generator.py article.json -o schema.json
  cat article.json | python3 schema-generator.py -

Person/sameAs - ТОЛЬКО подтверждённые профили с живых страниц
<твой-домен> и канона (не выдумывать новые)
"""

import json
import re
import sys

SITE = "https://<твой-домен>"
# КАНОН по решению автора (матрица ГР ресёрч-portals-2026-08-04.md, пункт Г7/6):
# 7 из 8 целевых порталов держат отдельную страницу автора, и Person.@id ведёт
# ИМЕННО на неё (HubSpot /marketing/author/slug, Ahrefs /blog/author/,
# Investopedia /contributors/ и т.д.). До этой правки @id вёл на главную
# (SITE + "/#person") - у нас "страница автора" фактически не существовала как
# отдельный узел. Теперь она есть: /avtor/ (слаг - транслит по канону сайта,
# см. остальные слаги corpus - guide-obuchenie-neyrosetyam, guide-neyroset-klod
# и т.п.: везде транслит русского, не английское слово "author").
# Меняет ТОЛЬКО дефолт для БУДУЩИХ сборок (build_page.py зовёт этот файл заново
# при каждой публикации) - уже задеплоенные страницы несут свою старую разметку,
# пока их не пересоберут отдельной волной (не в этой правке).
AUTHOR_URL = SITE + "/avtor/"
PERSON_ID = AUTHOR_URL + "#person"
ORG_ID = SITE + "/#organization"
WEBSITE_ID = SITE + "/#website"

REQUIRED = ["title", "description", "url", "image", "dateModified"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PAGE_KINDS = ("article", "profile")

# Только ЖИВЫЕ профили, проверенные HTTP 200 (по решению автора):
#   <твой-tg-канал> - с живых страниц <твой-домен>
#   instagram.com/<твой-бренд> - канонический хэндл из бизнес-канона
# <твой-домен> УБРАН волной 2 ретрофита по решению автора: домен отдаёт 301 на .com,
# зеркало-редирект не является отдельным профилем сущности и в sameAs не идёт.
# Появится третий живой профиль (YouTube / VK / Дзен) - дописать сюда и поднять MIN_SAMEAS.
MIN_SAMEAS = 2

# ГЕЙТ datePublishedSource - легальные источники (по решению автора, волна 8 доразметки).
# Раньше validate() принимал ЛЮБУЮ непустую строку как источник - защищало только от
# ПУСТОГО источника, не от произвольной прозы под видом источника. Теперь источник
# обязан начинаться с одного из распознанных префиксов - код-гейт вместо доверия к
# формулировке. Два новых префикса добавлены волной 8 (правка датировки 49 страниц
# разметочной волны через внешние источники, задача - честный datePublished):
#   wayback:<timestamp14>:<snapshot_url> - самый ранний снимок Wayback CDX API с
#       HTTP 200 (http://web.archive.org/cdx/search/cdx?url=...&filter=statuscode:200);
#       подтверждённая ВЕРХНЯЯ ГРАНИЦА публикации - страница физически существовала
#       на дату снимка. timestamp14 = YYYYMMDDHHMMSS из ответа CDX (аудируемо).
#   sitemap-history:<file>:<snapshot_date> - страница присутствует в датированном
#       историческом срезе sitemap.xml/corpus (напр. phase8-raw/sitemap.xml от
#       по решению автора или corpus/ от этой редакции) - тоже верхняя граница, слабее wayback (снимок
#       файловой системы, не публичный HTTP-снимок), используется как запасной
#       источник только когда в Wayback нет ни одного снимка страницы.
# Старые форматы (spec.date_published, "...проверка сайта YYYY-MM-DD") оставлены
# для обратной совместимости с build_page.py и уже описанным в докстринге контрактом.
DATE_SOURCE_PREFIXES = ("wayback:", "sitemap-history:", "spec.date_published",
                        "build_page.spec.date_published")


def _legal_date_source(dps):
    if dps.startswith(DATE_SOURCE_PREFIXES):
        return True
    # свободная форма, задокументированная в докстринге с самого начала (уже
    # использовалась build_page.py) - "...проверка сайта YYYY-MM-DD"
    return bool(re.search(r"проверка сайта \d{4}-\d{2}-\d{2}", dps))
DEFAULT_PERSON = {
    "@type": "Person",
    "@id": PERSON_ID,
    "name": "автор",
    "alternateName": "<your name>",
    "jobTitle": [
        "<твоя специализация>",
        "<твоя вторая специализация>",
    ],
    "url": AUTHOR_URL,
    "mainEntityOfPage": AUTHOR_URL,
    "image": SITE + "/assets/ivan-square.jpg",
    "sameAs": [
        "https://<твой-tg-канал>",
        "https://www.instagram.com/<твой-бренд>",
    ],
    "birthDate": "<год рождения>",
    "birthPlace": {"@type": "Place", "name": "<город>, Россия"},
    "homeLocation": {"@type": "Place", "name": "<город>, Россия"},
    "description": (
        "<твоё описание для JSON-LD: кто ты и что делаешь, 1-2 предложения>"
    ),
    "alumniOf": [
        {"@type": "CollegeOrUniversity", "name": "<твой вуз>", "sameAs": "<ссылка-на-вуз>"},
    ],
    "knowsAbout": [
        "вайбкодинг",
        "вайбмаркетинг",
        "создание цифровых продуктов через Claude",
        "нейросети для экспертов",
        "органический контент-завод",
        "AI-подписи (нейроописания)",
        "запуски цифровых продуктов",
        "монетизация экспертизы через ИИ",
    ],
    "knowsLanguage": ["ru", "en"],
}

ORGANIZATION = {
    "@type": "Organization",
    "@id": ORG_ID,
    "name": "автор",
    "url": SITE + "/",
    "logo": {
        "@type": "ImageObject",
        "url": SITE + "/assets/ivan-square.jpg",
    },
    "founder": {"@id": PERSON_ID},
}


def fail(msg):
    sys.exit("ОШИБКА schema-generator: " + msg)


def load_input(argv):
    if len(argv) < 2:
        fail("не передан входной JSON. Использование: python3 schema-generator.py article.json [-o out.json]")
    path = argv[1]
    try:
        if path == "-":
            raw = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
    except OSError as e:
        fail("не могу прочитать входной файл %s: %s" % (path, e))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail("входной файл %s - не валидный JSON: %s" % (path, e))
    if not isinstance(data, dict):
        fail("вход должен быть JSON-объектом с полями статьи, получен %s" % type(data).__name__)
    return data


def validate(data):
    required = list(REQUIRED)
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        fail("не хватает обязательных полей: %s. Обязательны: %s" % (", ".join(missing), ", ".join(required)))
    for k in ("datePublished", "dateModified"):
        if not str(data.get(k, "")).strip():
            continue
        if not DATE_RE.match(str(data[k]).strip()):
            fail("поле %s = %r, ожидается формат YYYY-MM-DD" % (k, data[k]))
    # ГЕЙТ (внедрён после дефекта волны 5: 49 страниц получили datePublished из
    # content-sha-registry.json lastmod - дата ПОСЛЕДНЕЙ правки выдана за дату ПЕРВОЙ
    # публикации, каждая старая статья представлена поисковику как только что вышедшая).
    # datePublished без явного подтверждённого источника собирать запрещено: если
    # честной даты первой публикации нет - поле просто не передаётся (страница выходит
    # без datePublished, как about.html), а не заполняется чем попало под руку.
    dp = str(data.get("datePublished", "")).strip()
    dps = str(data.get("datePublishedSource", "")).strip()
    if dp and not dps:
        fail("datePublished = %r передан без datePublishedSource. Источник даты первой "
             "публикации обязателен - иначе легко подставить дату из реестра content-sha "
             "lastmod (дата ПОСЛЕДНЕЙ правки) как будто это дата публикации (класс дефекта "
             "волны 5, 49 страниц). Нет честного источника даты первой публикации - "
             "не передавай datePublished вовсе, поле останется отсутствующим в графе" % dp)
    if dp and dps and not _legal_date_source(dps):
        fail("datePublishedSource = %r не распознан как легальный источник. Легальные "
             "префиксы: %s, или свободная форма «...проверка сайта YYYY-MM-DD». "
             "Источник обязан быть аудируемым (снимок/спека/живая проверка), а не "
             "произвольной прозой - иначе гейт не защищает ни от чего (волна 8)"
             % (dps, ", ".join(DATE_SOURCE_PREFIXES)))
    for k in ("url", "image"):
        if not str(data[k]).startswith("http"):
            fail("поле %s = %r, ожидается абсолютный URL (https://...)" % (k, data[k]))
    faq = data.get("faq") or []
    if not isinstance(faq, list):
        fail("faq должен быть списком объектов {\"q\": ..., \"a\": ...}")
    for i, item in enumerate(faq):
        if not isinstance(item, dict) or not str(item.get("q", "")).strip() or not str(item.get("a", "")).strip():
            fail("faq[%d] неполный: нужны непустые поля q и a" % i)
    steps = data.get("steps") or []
    if not isinstance(steps, list):
        fail("steps должен быть списком объектов {\"name\": ..., \"text\": ...}")
    for i, item in enumerate(steps):
        if not isinstance(item, dict) or not str(item.get("name", "")).strip() or not str(item.get("text", "")).strip():
            fail("steps[%d] неполный: нужны непустые поля name и text" % i)
    author = data.get("author")
    if author is not None and not isinstance(author, dict):
        fail("author должен быть объектом (переопределение полей Person)")
    kind = str(data.get("pageKind", "article")).strip() or "article"
    if kind not in PAGE_KINDS:
        fail("pageKind = %r, допустимы: %s" % (kind, ", ".join(PAGE_KINDS)))
    if kind == "profile" and (data.get("steps") or []):
        fail("pageKind=profile не собирает HowTo: убери steps или переключись на article")
    crumbs = data.get("breadcrumbs")
    if crumbs is not None:
        if not isinstance(crumbs, list) or not crumbs:
            fail("breadcrumbs должен быть непустым списком {\"name\": ..., \"item\": ...}")
        for i, c in enumerate(crumbs):
            if not isinstance(c, dict) or not str(c.get("name", "")).strip() or not str(c.get("item", "")).strip():
                fail("breadcrumbs[%d] неполный: нужны непустые поля name и item" % i)
    citation = data.get("citation")
    if citation is not None:
        if not isinstance(citation, list) or not citation:
            fail("citation должен быть непустым списком {\"name\": ..., \"url\": ...} (нет источников - не передавай поле вовсе)")
        for i, c in enumerate(citation):
            if not isinstance(c, dict) or not str(c.get("name", "")).strip() or not str(c.get("url", "")).strip():
                fail("citation[%d] неполный: нужны непустые поля name и url" % i)
            if not str(c["url"]).strip().startswith("http"):
                fail("citation[%d].url = %r, ожидается абсолютный URL (https://...)" % (i, c["url"]))
    if "wordCount" in data and data["wordCount"] is not None:
        try:
            wc = int(data["wordCount"])
        except (TypeError, ValueError):
            fail("wordCount = %r, ожидается целое число (реальный счёт слов статьи)" % (data["wordCount"],))
        if wc <= 0:
            fail("wordCount = %d, ожидается положительное число" % wc)
    if str(data.get("articleSection", "")).strip() == "" and "articleSection" in data and data.get("articleSection") is not None:
        fail("articleSection передан пустым - убери поле вовсе, если рубрики нет")


def build_graph(data):
    title = data["title"].strip()
    url = data["url"].strip()
    kind = str(data.get("pageKind", "article")).strip() or "article"

    # КАНОН по решению автора: Person - ОДИН на весь сайт и одинаковый на всех страницах.
    # До этого /about.html отдавала богатого Person (knowsAbout, jobTitle массивом),
    # а статьи - урезанного с тем же @id: одна сущность противоречила сама себе.
    # Постраничное переопределение Person запрещено.
    person = dict(DEFAULT_PERSON)
    if isinstance(data.get("author"), dict):
        fail("Person переопределять постранично запрещено: он один на весь сайт "
             "(правь DEFAULT_PERSON в schema-generator.py)")
    if len(person.get("sameAs") or []) < MIN_SAMEAS:
        fail("Person.sameAs должен содержать минимум %d подтверждённых живых профиля" % MIN_SAMEAS)
    bad = [u for u in person["sameAs"] if "<твой-домен>" in u]
    if bad:
        fail("в sameAs домен-зеркало %s: он отдаёт 301 на .com, это не отдельный профиль" % bad)

    webpage_id = url + "#webpage"
    image_id = url + "#primaryimage"

    article = {
        "@type": "Article",
        "@id": url + "#article",
        "headline": title,
        "description": data["description"].strip(),
        "url": url,
        "image": {"@id": image_id},
    }
    # datePublished - ТОЛЬКО если честно передан (см. гейт datePublishedSource в
    # validate()). Нет источника - ключа в графе не будет вовсе, как у about.html.
    # Раньше здесь стояло str(data.get("datePublished", "")).strip() безусловно -
    # ключ уезжал в граф даже пустой строкой, и заполнить его откуда попало было
    # соблазнительно (баг волны 5, 49 страниц).
    if str(data.get("datePublished", "")).strip():
        article["datePublished"] = str(data["datePublished"]).strip()
    article.update({
        "dateModified": data["dateModified"].strip(),
        "inLanguage": "ru",
        "isPartOf": {"@id": webpage_id},
        "mainEntityOfPage": {"@id": webpage_id},
        "breadcrumb": {"@id": url + "#breadcrumbs"},
        "author": {"@id": PERSON_ID},
        "publisher": {"@id": ORG_ID},
        # контент открыт без пэйвола на всех статьях - константа, не поле входа
        "isAccessibleForFree": True,
    })
    kw = data.get("keywords", "")
    if isinstance(kw, (list, tuple)):
        # str() от списка давал repr "['a', 'b']" в живом JSON-LD (класс N1, по решению автора)
        kw = ", ".join(str(x).strip() for x in kw if str(x).strip())
    if str(kw).strip():
        article["keywords"] = str(kw).strip()
    if str(data.get("alternativeHeadline", "")).strip():
        article["alternativeHeadline"] = str(data["alternativeHeadline"]).strip()
    if str(data.get("articleSection", "")).strip():
        article["articleSection"] = str(data["articleSection"]).strip()
    if data.get("wordCount") is not None:
        article["wordCount"] = int(data["wordCount"])
    citation_in = data.get("citation") or []
    if citation_in:
        article["citation"] = [
            {"@type": "CreativeWork", "name": c["name"].strip(), "url": c["url"].strip()}
            for c in citation_in
        ]

    webpage = {
        "@type": ["WebPage", "ProfilePage"] if kind == "profile" else "WebPage",
        "@id": webpage_id,
        "url": url,
        "name": title,
        "description": data["description"].strip(),
        "inLanguage": "ru",
        "isPartOf": {"@id": WEBSITE_ID},
        "breadcrumb": {"@id": url + "#breadcrumbs"},
        "primaryImageOfPage": {"@id": image_id},
        "dateModified": data["dateModified"].strip(),
    }
    if str(data.get("datePublished", "")).strip():
        webpage["datePublished"] = str(data["datePublished"]).strip()
    if kind == "profile":
        # страница-профиль: главная сущность страницы - сам человек
        webpage["mainEntity"] = {"@id": PERSON_ID}
        webpage["about"] = {"@id": PERSON_ID}

    website = {
        "@type": "WebSite",
        "@id": WEBSITE_ID,
        "url": SITE + "/",
        "name": "автор",
        "inLanguage": "ru",
        "publisher": {"@id": ORG_ID},
        "author": {"@id": PERSON_ID},
    }

    primary_image = {
        "@type": "ImageObject",
        "@id": image_id,
        "url": data["image"].strip(),
        "contentUrl": data["image"].strip(),
        "width": int(data.get("imageWidth", 1200)),
        "height": int(data.get("imageHeight", 630)),
    }

    # 🔴 Хаб гайдов - /blog/, а НЕ /blog.html (по решению автора, переезд на чистые адреса).
    # /blog.html отдаёт 301 на /blog/. Крошка на переадресацию в расширенный сниппет
    # не склеивается, поэтому дефолт обязан вести на адрес, отвечающий 200. Именно
    # отсюда /blog.html разъехался по 233 живым страницам корпуса.
    # 🔴 ДЕФОЛТНАЯ КРОШКА-НА-СЕБЯ НАЗЫВАЕТСЯ ВИДИМЫМ ЗАГОЛОВКОМ (по решению автора,
    # круг 3, R20/R69). Разметка обязана описывать ВИДИМЫЙ текст: после
    # CTR-ретайтла `title` уезжает в сниппет, а в дорожке на странице человек
    # видит `h1`. Парный дефолт - `article_build.spec["breadcrumbs"]`; штатный
    # путь всё равно передаёт крошки явно (`build_page.build_jsonld` берёт их из
    # того же списка, который рендерит видимую дорожку), этот список - страховка
    # для прямых вызовов генератора.
    crumbs_in = data.get("breadcrumbs") or [
        {"name": "Главная", "item": SITE + "/"},
        {"name": "Гайды", "item": SITE + "/blog/"},
        {"name": str(data.get("h1") or title), "item": url},
    ]
    breadcrumbs = {
        "@type": "BreadcrumbList",
        "@id": url + "#breadcrumbs",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": c["name"].strip(), "item": c["item"].strip()}
            for i, c in enumerate(crumbs_in)
        ],
    }

    graph = [webpage, website, primary_image, breadcrumbs]
    if kind == "article":
        graph.insert(0, article)

    # 🔴 В41 (по решению автора): ИМЕНА ЭТИХ ДВУХ УЗЛОВ - ПРОИЗВОДНЫЕ ОТ `title`.
    # `FAQPage.name` по умолчанию = метка «Частые вопросы: » + title,
    # `HowTo.name` = сам title. Значит при CTR-ретайтле они обязаны переезжать
    # вместе с заголовком, иначе страница уезжает с новым title в сниппете и
    # старым в разметке (живой случай `/guide-klyuchi-nvidia/`). Двигает их
    # `scripts/seo/retitle.py` (`patch_schema_names`), сверяет `gate_retitle` в
    # `ftp_publish.py`. Меняя ЗДЕСЬ форму имени по умолчанию (метку, порядок,
    # язык) - правь распознавание метки там же, иначе ретайтл перестанет
    # узнавать конвенцию и молча запишет узел в «собственные имена».
    faq = data.get("faq") or []
    if faq:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "url": url,
            "name": data.get("faqName", "Частые вопросы: " + title).strip(),
            "inLanguage": "ru",
            "isPartOf": {"@id": webpage_id},
            "mainEntityOfPage": {"@id": webpage_id},
            "author": {"@id": PERSON_ID},
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["q"].strip(),
                    "acceptedAnswer": {"@type": "Answer", "text": item["a"].strip()},
                }
                for item in faq
            ],
        })

    steps = data.get("steps") or []
    if steps:
        graph.append({
            "@type": "HowTo",
            "@id": url + "#howto",
            "name": data.get("howtoName", title).strip(),
            "inLanguage": "ru",
            "isPartOf": {"@id": webpage_id},
            "mainEntityOfPage": {"@id": webpage_id},
            "author": {"@id": PERSON_ID},
            "step": [
                dict({
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": item["name"].strip(),
                    "text": item["text"].strip(),
                }, **({"url": item["url"].strip()} if str(item.get("url", "")).strip() else {}))
                for i, item in enumerate(steps)
            ],
        })
        if str(data.get("howtoTotalTime", "")).strip():
            graph[-1]["totalTime"] = str(data["howtoTotalTime"]).strip()

    graph.append(person)
    graph.append(ORGANIZATION)
    doc = {"@context": "https://schema.org", "@graph": graph}
    assert_resolvable(doc)
    return doc


def assert_resolvable(doc):
    """Гейт связности: ни одной висячей ссылки {"@id": ...} и ни одного сироты."""
    nodes = {n["@id"] for n in doc["@graph"] if "@id" in n}
    refs = []

    def walk(o, top=False):
        if isinstance(o, dict):
            if "@id" in o and "@type" not in o and not top:
                refs.append(o["@id"])
            for k, v in o.items():
                if k == "@id":
                    continue
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    outgoing = {}
    for n in doc["@graph"]:
        before = len(refs)
        walk(n, top=True)
        outgoing[n["@id"]] = len(refs) - before
    dangling = sorted(set(refs) - nodes)
    if dangling:
        fail("висячие ссылки @id (нет узла в @graph): %s" % ", ".join(dangling))
    linked = set(refs)
    # сирота = узел, который ни на кого не ссылается и на который никто не ссылается
    orphans = sorted(n["@id"] for n in doc["@graph"]
                     if n["@id"] not in linked and not outgoing[n["@id"]])
    if orphans:
        fail("узлы-сироты (ни входящих, ни исходящих связей): %s" % ", ".join(orphans))


def self_check(doc, data):
    """Содержательная самопроверка графа ПЕРЕД записью.

    Раньше здесь стояло json.dumps -> json.loads: вывод json.dumps парсится
    обратно всегда, красной такая проверка не бывает по конструкции. Проверяем
    то, что реально может сломаться при правке build_graph: набор обязательных
    узлов, подтверждённые профили Person и совпадение url графа с canonical входа.
    """
    graph = doc.get("@graph") or []
    by_type = {}
    for n in graph:
        t = n.get("@type")
        for one in (t if isinstance(t, list) else [t]):
            by_type.setdefault(one, []).append(n)
        if not t:
            fail("самопроверка: узел без @type (@id=%s)" % n.get("@id"))

    kind = str(data.get("pageKind", "article")).strip() or "article"
    required = ["Person", "Organization", "WebSite", "WebPage", "ImageObject"]
    if kind == "article":
        required.append("Article")
    if data.get("faq"):
        required.append("FAQPage")
    if data.get("steps"):
        required.append("HowTo")
    if data.get("breadcrumbs"):
        required.append("BreadcrumbList")
    missing = [t for t in required if t not in by_type]
    if missing:
        fail("самопроверка: в @graph нет обязательных узлов: %s (есть: %s)"
             % (", ".join(missing), ", ".join(sorted(by_type))))

    person = by_type["Person"][0]
    same = person.get("sameAs") or []
    if not isinstance(same, list) or len(same) < 1:
        fail("самопроверка: Person.sameAs пуст - сущность нечем подтвердить")
    if len(same) < MIN_SAMEAS:
        fail("самопроверка: Person.sameAs = %d профиля, минимум %d" % (len(same), MIN_SAMEAS))

    url = data["url"].strip()
    page = by_type["WebPage"][0]
    if page.get("url") != url:
        fail("самопроверка: WebPage.url = %r, а canonical входа = %r" % (page.get("url"), url))
    if page.get("@id") != url + "#webpage":
        fail("самопроверка: WebPage.@id = %r, ожидался %r" % (page.get("@id"), url + "#webpage"))
    if kind == "article":
        art = by_type["Article"][0]
        if art.get("@id") != url + "#article":
            fail("самопроверка: Article.@id = %r, ожидался %r" % (art.get("@id"), url + "#article"))
        for k in ("datePublished", "dateModified"):
            v = art.get(k)
            if v is not None and not DATE_RE.match(str(v)):
                fail("самопроверка: Article.%s = %r, ожидается YYYY-MM-DD" % (k, v))

    text = json.dumps(doc, ensure_ascii=False, indent=1)
    json.loads(text)
    return text


def main(argv):
    out_path = None
    if "-o" in argv:
        i = argv.index("-o")
        if i + 1 >= len(argv):
            fail("после -o нужен путь выходного файла")
        out_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]

    data = load_input(argv)
    validate(data)
    doc = build_graph(data)

    # самопроверка: обязательные узлы на месте, Person подтверждён профилями,
    # url графа совпадает с canonical входа (см. self_check)
    text = self_check(doc, data)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        types = ["/".join(n["@type"]) if isinstance(n["@type"], list) else n["@type"]
                 for n in doc["@graph"]]
        print("OK: %s (%d узлов: %s)" % (out_path, len(types), ", ".join(types)))
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
