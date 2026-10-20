#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_health.py - чекер здоровья картинок страницы: собирает ВСЕ ссылки на
изображения, которые страница реально запрашивает у браузера, и проверяет, что
каждая из них резолвится в существующий файл.

ЗАЧЕМ ЭТОТ ФАЙЛ СУЩЕСТВУЕТ.
Постфлайт деплоя проверяет ЗАЛИТЫЕ ФАЙЛЫ: положили картинку по адресу X, curl X
вернул 200, значит всё хорошо. Но браузер запрашивает не то, что мы залили, а то,
что НАПИСАНО В HTML, и адрес он считает ОТНОСИТЕЛЬНО URL, по которому отдаётся
страница. Между этими двумя множествами есть щель, и в неё уезжает целый класс
дефектов: файл на проде лежит, curl по нему зелёный, а на странице дыра.

КЛАСС ДЕФЕКТА «relative-path-mismatch» (ради него всё и написано).
У страницы есть две раскладки:

  КАТАЛОЖНАЯ:  страница /<slug>/index.html, картинки /<slug>/assets/x.webp
               в HTML пишется относительный путь  assets/x.webp
               браузер на /<slug>/ резолвит его в /<slug>/assets/x.webp  → 200

  ПЛОСКАЯ:     страница <slug>.html (или отдаётся по /<slug>/ через редирект),
               а картинки лежат в ОБЩЕМ корневом каталоге /assets/<slug>/x.webp
               в HTML тот же относительный путь  assets/<slug>/x.webp
               браузер на /<slug>/ резолвит его в /<slug>/assets/<slug>/x.webp → 404

Один и тот же текст ссылки при первой раскладке верный, при второй битый. Файл
при этом существует, деплой зелёный, никакой гейт не срабатывает. Лечится одним
символом: ведущий слэш, assets/<slug>/x.webp → /assets/<slug>/x.webp.

ПОЧЕМУ ДЫРА НЕ ВИДНА ГЛАЗАМИ. Внутри <picture> промах <source srcset> НЕ
откатывается на <img src>: браузер выбирает source по type/media, и если
выбранный кандидат не скачался, картинки нет вообще, хотя jpeg-фолбэк в <img>
прописан абсолютным путём и живой. То есть достаточно ошибиться в ОДНОМ srcset,
чтобы hero-картинка пропала при исправном <img>.

ЧТО СОБИРАЕТСЯ (всё, чем страница может попросить картинку):
  img[src], img[srcset] (КАЖДЫЙ кандидат), source[srcset] (каждый кандидат),
  source[src] с картиночным расширением, video[poster],
  link rel=preload as=image: href + КАЖДЫЙ кандидат imagesrcset,
  a[href] с картиночным расширением (полноразмерная картинка лайтбокса и любая
    прямая ссылка на файл: запрашивает её не парсер разметки, а клик читателя,
    и битой она видна только ему - поэтому судим её тем же путём),
  meta og:image / og:image:url / og:image:secure_url / twitter:image,
  link rel=icon | shortcut icon | apple-touch-icon | mask-icon,
  url(...) в style="" и в <style> (только с картиночным расширением).
  data:-URI пропускается (это не ссылка, дефектом не является).
  <base href> учитывается, как учитывает его браузер.
  Правило охвата одно и оно НЕ про имена классов вёрстки: решает расширение
  файла в ссылке, поэтому «.fig a.zoom» конкретной темы тут не хардкодится.

ДВА РЕЖИМА.

  --live   вход: URL, файл со списком URL, --sitemap <url>.
           Качает страницу, базой для резолва берёт КАНОНИЧЕСКИЙ адрес (после
           редиректов, с учётом <base>), каждую ссылку проверяет по HTTP
           (HEAD, при отказе метода - range-GET), запросы параллелит.
           Для каждого битого относительного пути дополнительно пробует
           корневой вариант и, если он живой, печатает готовую подсказку фикса.
           🔴 Дефект = ТОЛЬКО ответ сервера вне 2xx/3xx. Молчание транспорта
           (таймаут, обрыв, DNS) - повтор (--retries), и если ответа так и нет,
           ссылка уходит в класс unchecked: это НЕ дефект, exit не роняет,
           считается отдельной цифрой в шапке и в --json (unchecked_total).

  --local  вход: каталог статьи или конкретный index.html + раскладка
           (--page-url /<slug>/ и --assets-remote <префикс на проде>).
           Резолвит ссылку так, как она ляжет на проде, и проверяет, что
           соответствующий ЛОКАЛЬНЫЙ файл существует. Ловит дефект ДО заливки,
           без сети. Это и есть предполётный гейт для движка публикации.

           Как читается --assets-remote (ОДНА семантика с движком публикации,
           значение можно копировать из его шапки дословно):
             значение = remote-путь каталога картинок ОТ КОРНЯ САЙТА,
             ведущий слэш необязателен: assets/<slug> == /assets/<slug>
             флаг не задан = каталожная раскладка <каталог страницы>/assets/
                             (дефолт движка; та же форма явно - ./assets)
             ./… или ../… = ЯВНАЯ форма «относительно каталога страницы»
           Раньше значение без слэша здесь читалось как относительное, то есть
           ПРОТИВОПОЛОЖНО деплою: скопированный из шапки движка `--assets-remote
           assets/<slug>` давал exit 0 «чисто» на боевом дефекте. Теперь нет.
           Что именно получилось, инструмент печатает в шапке отчёта.

           🔴 Судится РАСКЛАДКА. Отсутствие локального файла под СВОЕЙ КОРНЕВОЙ
           ссылкой вердиктом не является (на заливке «только страница» картинки
           уже живут на проде) - идёт отдельной цифрой класса
           local-file-unknown, exit не роняет. Вернуть жёсткое суждение:
           --require-local-files. Относительные ссылки как требовали файл рядом,
           так и требуют - это контракт заливки, он не менялся.

EXIT-КОДЫ: 0 чисто, 1 есть дефекты, 2 ошибка запуска (плохие аргументы, нет
цели, ни одна страница не скачалась). --json - машинный вывод в stdout, весь
человеческий лог при этом уходит в stderr.

СЕЛФТЕСТ: python3 image_health.py --selftest - офлайн, без сети, на синтетических
мини-страницах. Ненулевой exit при любом провале.

ПОРТИРУЕМОСТЬ. В коде нет ни одного домена, слага и ключа: домен по желанию
берётся из ~/.config/seo-publish.json (тот же конфиг, что у деплоя), всё
остальное приходит аргументами. Зависимостей вне stdlib нет.
"""

import argparse
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener

def отложить(путь, ignore_errors=False):
    """ЗАКОН №0 владельца (по решению автора, дословно «вообще ничего не удаляй, пусть лежит»).

    Обратимая замена сноса: путь ПЕРЕИМЕНОВЫВАЕТСЯ в датированного соседа
    `<имя>.otlozheno-<ГГГГММДД-ЧЧММСС>`. Прежнее имя после вызова свободно,
    байты остаются на диске и возвращаются обратным переименованием.
    Заведено по решению автора: страж удалений не давал ЗАПУСТИТЬ инструмент,
    в теле которого лежал вызов удаления.
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


TOOL = "image_health"
DEFAULT_CONFIG = os.path.expanduser("~/.config/seo-publish.json")
UA = "Mozilla/5.0 (compatible; image-health/1.0; +local-qa)"

IMG_EXT = (".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".avif",
           ".ico", ".bmp", ".jfif", ".apng", ".tif", ".tiff")

# классы результата по одной ссылке
OK = "ok"                       # ссылка живая / файл на месте
SKIP_DATA = "data-uri"          # data: - не ссылка, пропуск
SKIP_SCHEME = "non-http"        # javascript:, about:, mailto:, #anchor
EXTERNAL = "external"           # чужой домен (счётчики, CDN) - отдельный класс
OUTSIDE = "outside-article"     # наш домен, но вне артефактов статьи (local)

# классы дефекта
D_RELMISMATCH = "relative-path-mismatch"
D_MISSING_LOCAL = "missing-local-file"
D_HTTP = "http-error"
D_EMPTY = "empty-ref"
D_PAGE = "page-fetch-failed"
DEFECT_CLASSES = (D_RELMISMATCH, D_MISSING_LOCAL, D_HTTP, D_EMPTY, D_PAGE)

# 🔴 КЛАССЫ «УЛИКИ НЕТ» - в DEFECT_CLASSES НЕ входят и exit не роняют.
#
# ЗАКОН УЛИК (по решению автора). Ложный блок публикации хуже отсутствия гейта: гейт,
# который краснеет на сетевой икоте и на живой картинке с прода, отключают в
# первый же день, и вместе с ним уходит настоящая находка. Поэтому дефектом
# считается только ДОКАЗАННОЕ, а недоказанное честно называется непокрытием и
# считается ОТДЕЛЬНОЙ цифрой - её видно и человеку в шапке, и сторожу в --json.
#
#   UNCHECKED (live)  транспорт не ответил (таймаут, обрыв, DNS) даже после
#                     повторов: код ответа сервера так и не получен, судить
#                     нечем. Тот же закон уже работал в постфлайте движка
#                     публикации, вниз, в сам чекер, спущен этой правкой.
#   NOLOCAL (local)   своя КОРНЕВАЯ ссылка, под которую рядом со страницей нет
#                     файла. На заливке «ТОЛЬКО СТРАНИЦА» это норма: картинки
#                     давно живут на проде. Набор заливки и живой прод есть
#                     только у предполёта ftp_publish - он и судит факт файла.
#                     Вернуть жёсткое суждение: --require-local-files.
UNCHECKED = "unchecked"
NOLOCAL = "local-file-unknown"
SOFT_CLASSES = (UNCHECKED, NOLOCAL)

WS = " \t\n\r\f"


# ── мелкая утилита вывода ────────────────────────────────────────────────────

def log(msg):
    print(msg, file=sys.stderr)


def die(msg, code=2):
    print(f"[{TOOL}] СТОП: {msg}", file=sys.stderr)
    sys.exit(code)


# ── разбор srcset ────────────────────────────────────────────────────────────

def parse_srcset(value):
    """Кандидаты srcset по алгоритму HTML, а НЕ split(',').

    Разделитель кандидатов - пробел + запятая, а не запятая: URL сам может
    содержать запятые (data:-URI, подписанные CDN-адреса), и наивный split
    режет его пополам, порождая два фантомных «битых» пути.
    Дескрипторы (720w, 2x) отбрасываются, остаются только URL.
    """
    out = []
    i, n = 0, len(value or "")
    while i < n:
        while i < n and (value[i] in WS or value[i] == ","):
            i += 1
        if i >= n:
            break
        start = i
        while i < n and value[i] not in WS:
            i += 1
        url = value[start:i]
        if url.endswith(","):
            url = url.rstrip(",")
        else:
            while i < n and value[i] != ",":
                i += 1
        if url:
            out.append(url)
    return out


def has_img_ext(url):
    path = urlsplit(url).path if "://" in url or url.startswith("//") else url.split("?")[0].split("#")[0]
    return path.lower().endswith(IMG_EXT)


# ── парсер страницы ──────────────────────────────────────────────────────────

class Ref(object):
    """Одна ссылка на изображение, как она написана в HTML."""

    __slots__ = ("kind", "raw", "line")

    def __init__(self, kind, raw, line):
        self.kind = kind
        self.raw = raw
        self.line = line

    def as_dict(self):
        return {"kind": self.kind, "raw": self.raw, "line": self.line}


CSS_URL_RE = re.compile(r"""url\(\s*(?:'([^']*)'|"([^"]*)"|([^)'"]*))\s*\)""", re.I)
META_IMG_KEYS = ("og:image", "og:image:url", "og:image:secure_url",
                 "twitter:image", "twitter:image:src")
ICON_RELS = ("icon", "shortcut icon", "apple-touch-icon",
             "apple-touch-icon-precomposed", "mask-icon", "fluid-icon")


class ImageRefParser(HTMLParser):
    """Собирает ссылки на изображения + <base href> + canonical/og:url."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.refs = []
        self.base_href = None
        self.canonical = None
        self.og_url = None
        self._style_buf = None

    # -- служебное
    def _add(self, kind, raw):
        if raw is None:
            return
        self.refs.append(Ref(kind, raw.strip(), self.getpos()[0]))

    def _css_urls(self, css, kind):
        for m in CSS_URL_RE.finditer(css or ""):
            raw = (m.group(1) or m.group(2) or m.group(3) or "").strip()
            if raw and (raw.startswith("data:") or has_img_ext(raw)):
                self._add(kind, raw)

    # -- HTMLParser API
    def handle_starttag(self, tag, attrs):
        a = {}
        for k, v in attrs:
            a[k.lower()] = v if v is not None else ""

        if tag == "base" and a.get("href") and self.base_href is None:
            self.base_href = a["href"].strip()

        elif tag == "img":
            if "src" in a:
                self._add("img-src", a["src"])
            for cand in parse_srcset(a.get("srcset", "")):
                self._add("img-srcset", cand)

        elif tag == "source":
            for cand in parse_srcset(a.get("srcset", "")):
                self._add("source-srcset", cand)
            src = a.get("src", "")
            if src and (src.startswith("data:") or has_img_ext(src)):
                self._add("source-src", src)

        elif tag == "video" and a.get("poster"):
            self._add("video-poster", a["poster"])

        elif tag == "a":
            # Полноразмерная картинка лайтбокса: JS по клику подставляет href в
            # img.src, то есть это НАСТОЯЩАЯ ссылка страницы на изображение, а не
            # навигация. Отбор по расширению файла, а не по классу вёрстки: имя
            # класса у каждой темы своё, расширение у картинки одно.
            # Пустой href = обычная якорная заглушка разметки, а не битая
            # картинка - его тут не судим (в отличие от img[src]="").
            href = a.get("href", "")
            if href.strip() and has_img_ext(href.strip()):
                self._add("a-href", href)

        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").strip().lower()
            if key in META_IMG_KEYS and a.get("content"):
                kind = "meta-twitter-image" if key.startswith("twitter") else "meta-og-image"
                self._add(kind, a["content"])
            elif key == "og:url" and a.get("content") and self.og_url is None:
                self.og_url = a["content"].strip()

        elif tag == "link":
            rels = (a.get("rel") or "").strip().lower()
            rel_set = set(rels.split())
            if rels == "canonical" and a.get("href") and self.canonical is None:
                self.canonical = a["href"].strip()
            elif "preload" in rel_set and (a.get("as") or "").strip().lower() == "image":
                # Предзагрузка хиро - самый ранний запрос страницы: браузер идёт
                # за ней ДО разбора <body>. Битый preload = дыра в первом экране.
                if a.get("href") is not None:
                    self._add("link-preload", a["href"])
                for cand in parse_srcset(a.get("imagesrcset", "")):
                    self._add("link-preload-srcset", cand)
            elif rels in ICON_RELS or "icon" in rel_set:
                if a.get("href"):
                    self._add("link-icon", a["href"])

        elif tag == "style":
            self._style_buf = []

        if a.get("style"):
            self._css_urls(a["style"], "style-attr-url")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "style":
            self._style_buf = None

    def handle_data(self, data):
        if self._style_buf is not None:
            self._style_buf.append(data)

    def handle_endtag(self, tag):
        if tag == "style" and self._style_buf is not None:
            self._css_urls("".join(self._style_buf), "style-block-url")
            self._style_buf = None

    def close(self):
        HTMLParser.close(self)
        if self._style_buf is not None:
            self._css_urls("".join(self._style_buf), "style-block-url")
            self._style_buf = None


def parse_page(html):
    p = ImageRefParser()
    p.feed(html)
    p.close()
    return p


# ── классификация сырой ссылки ───────────────────────────────────────────────

def ref_kind_of_raw(raw):
    """(класс, причина) для ссылок, которые проверять не нужно, иначе (None, None)."""
    if raw == "":
        return D_EMPTY, "пустой атрибут: браузер запросит саму страницу как картинку"
    low = raw.lower()
    if low.startswith("data:"):
        return SKIP_DATA, None
    if low.startswith("#"):
        return SKIP_SCHEME, "якорь"
    for pref in ("javascript:", "about:", "mailto:", "tel:", "blob:", "{{", "${"):
        if low.startswith(pref):
            return SKIP_SCHEME, pref.rstrip(":")
    return None, None


def is_relative(raw):
    """Относительный путь = без схемы, без //host и без ведущего слэша."""
    if raw.startswith("//") or raw.startswith("/"):
        return False
    return not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", raw)


def norm_url(u):
    """URL без фрагмента (браузер фрагмент к картинке не тащит)."""
    s = urlsplit(u)
    return urlunsplit((s.scheme, s.netloc, s.path, s.query, ""))


# ── HTTP-слой ────────────────────────────────────────────────────────────────

class Http(object):
    def __init__(self, timeout=20, workers=12):
        self.timeout = timeout
        self.workers = max(1, workers)
        self.opener = build_opener()
        self.cache = {}

    def _open(self, url, method, extra=None):
        headers = {"User-Agent": UA, "Accept": "*/*"}
        if extra:
            headers.update(extra)
        req = Request(url, headers=headers, method=method)
        return self.opener.open(req, timeout=self.timeout)

    def status(self, url):
        """(код|None, финальный_url, причина_ошибки|None). HEAD, при отказе - range-GET."""
        if url in self.cache:
            return self.cache[url]
        res = None
        try:
            r = self._open(url, "HEAD")
            res = (r.status, r.geturl(), None)
            r.close()
        except HTTPError as e:
            if e.code in (400, 403, 405, 406, 501):
                res = None  # метод не понравился, добираем range-GET
            else:
                res = (e.code, url, None)
        except URLError as e:
            res = (None, url, f"сеть: {e.reason}")
        except Exception as e:  # noqa: BLE001 - любой отказ транспорта = причина
            res = (None, url, f"сбой запроса: {e}")

        if res is None:
            try:
                r = self._open(url, "GET", {"Range": "bytes=0-0"})
                res = (r.status, r.geturl(), None)
                r.read(1)
                r.close()
            except HTTPError as e:
                res = (e.code, url, None)
            except URLError as e:
                res = (None, url, f"сеть: {e.reason}")
            except Exception as e:  # noqa: BLE001
                res = (None, url, f"сбой запроса: {e}")

        self.cache[url] = res
        return res

    def status_many(self, urls):
        todo = [u for u in dict.fromkeys(urls) if u not in self.cache]
        if todo:
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                list(ex.map(self.status, todo))
        return {u: self.cache[u] for u in urls}

    def get_text(self, url):
        """(текст, финальный_url) или die-ошибка строкой в (None, причина)."""
        try:
            r = self._open(url, "GET")
            raw = r.read()
            final = r.geturl()
            ctype = r.headers.get("Content-Type", "")
            r.close()
        except HTTPError as e:
            return None, f"HTTP {e.code}"
        except URLError as e:
            return None, f"сеть: {e.reason}"
        except Exception as e:  # noqa: BLE001
            return None, f"сбой запроса: {e}"
        enc = "utf-8"
        m = re.search(r"charset=([\w\-]+)", ctype or "", re.I)
        if m:
            enc = m.group(1)
        return (raw.decode(enc, errors="replace"), final)


# ── повтор по молчащему транспорту ───────────────────────────────────────────

def значащий_код(status):
    """True = сервер ОТВЕТИЛ и ответ плохой. None (транспорт молчит) - не улика.

    2xx и 3xx одинаково означают «файл отдаётся»: HTTP-слой идёт за редиректами
    сам, значит видимый 3xx - это конечный ответ, а не промах файла.
    """
    if status is None:
        return False
    try:
        code = int(status)
    except (TypeError, ValueError):
        return False
    return not (200 <= code < 400)


def код_живой(status):
    """True = сервер ответил 2xx/3xx (файл на месте)."""
    if status is None:
        return False
    try:
        return 200 <= int(status) < 400
    except (TypeError, ValueError):
        return False


def recheck_silent(http, urls, попыток=2, пауза=1.5):
    """{url: (код, причина)} после повторов - для ссылок, где транспорт промолчал.

    Разовый таймаут не весит столько же, сколько честный 404: у молчания улики
    нет вовсе. Повтор идёт ЧЕРЕЗ ТОТ ЖЕ интерфейс status_many (его реализует и
    боевой Http, и фейки вызывающих), кэш перед повтором сбрасывается - иначе
    повтор вернул бы из кэша ровно то же молчание.
    """
    итог = {}
    осталось = list(dict.fromkeys(urls))
    for u in осталось:
        итог[u] = (None, None)
    for i in range(max(1, попыток)):
        if not осталось:
            break
        if i and пауза:
            time.sleep(пауза)
        cache = getattr(http, "cache", None)
        if isinstance(cache, dict):
            for u in осталось:
                cache.pop(u, None)
        try:
            коды = http.status_many(осталось) or {}
        except Exception as e:  # noqa: BLE001 - отказ транспорта = «не ответило»
            for u in осталось:
                итог[u] = (None, f"сбой запроса: {e}")
            break
        ещё = []
        for u in осталось:
            code, _fin, err = коды.get(u, (None, None, "не проверено"))
            итог[u] = (code, err)
            if code is None:
                ещё.append(u)
        осталось = ещё
    return итог


# ── общий результат по одной ссылке ──────────────────────────────────────────

def finding(page, ref, resolved, status, klass, reason=None, hint=None):
    return {
        "page": page,
        "kind": ref.kind,
        "raw": ref.raw,
        "line": ref.line,
        "resolved": resolved,
        "status": status,
        "class": klass,
        "reason": reason,
        "hint": hint,
    }


# ── режим LIVE ───────────────────────────────────────────────────────────────

def check_live_page(url, http, strict_external=False, попыток=2, пауза=1.5):
    """Отчёт по одной живой странице: список findings (и дефекты, и норма).

    🔴 ЗАКОН УЛИК (правка 24.08.2026). В defect-класс (http-error /
    relative-path-mismatch) идёт ТОЛЬКО ответ сервера вне 2xx/3xx. Молчание
    транспорта (таймаут, обрыв, DNS) - это отсутствие улики: по такой ссылке
    делается повтор, и если сервер так и не ответил, она уходит в класс
    UNCHECKED, который НЕ дефект и exit не роняет.

    Так было раньше и почему это регресс: status=None классифицировался как
    жёсткий дефект и получал подсказку «абсолютный путь ведёт в никуда: файл не
    залит или переименован». Повторов не делалось ни одного. Режим --live гоняет
    по всему sitemap ежедневный сторож - одна сетевая икота давала выдуманный
    дефект с ложным диагнозом, отправляющим чинить целый файл. Тот же закон уже
    был написан в движке публикации (постфлайт), вниз он спущен этой правкой.
    """
    html, final = http.get_text(url)
    if html is None:
        ref = Ref("page", url, 0)
        return [finding(url, ref, url, None, D_PAGE, reason=final)], url

    page = parse_page(html)
    base = final
    if page.base_href:
        base = urljoin(final, page.base_href)
    host = urlsplit(base).netloc.lower()

    out = []
    to_check = []
    for ref in page.refs:
        klass, reason = ref_kind_of_raw(ref.raw)
        if klass == D_EMPTY:
            out.append(finding(final, ref, None, None, D_EMPTY, reason=reason))
            continue
        if klass is not None:
            out.append(finding(final, ref, None, None, klass, reason=reason))
            continue
        resolved = norm_url(urljoin(base, ref.raw))
        rhost = urlsplit(resolved).netloc.lower()
        if rhost and rhost != host:
            out.append(finding(final, ref, resolved, None, EXTERNAL))
            if strict_external:
                to_check.append((ref, resolved))
            continue
        to_check.append((ref, resolved))

    codes = http.status_many([r for _, r in to_check])

    # молчащие адреса - на повтор ДО всякой классификации: пока сервер не
    # ответил, ни дефекта, ни нормы у нас нет
    молчащие = [r for _, r in to_check if codes.get(r, (None,))[0] is None]
    повтор = (recheck_silent(http, молчащие, попыток=попыток, пауза=пауза)
              if молчащие else {})

    checked = {}
    for ref, resolved in to_check:
        code, _fin, err = codes[resolved]
        if resolved in повтор:
            code2, err2 = повтор[resolved]
            code, err = code2, (err2 or err)
        checked[(ref.kind, ref.raw, ref.line)] = (code, err)
        if код_живой(code):
            out.append(finding(final, ref, resolved, code, OK))
            continue
        rhost = urlsplit(resolved).netloc.lower()
        if rhost and rhost != host:
            out.append(finding(final, ref, resolved, code, EXTERNAL, reason=err))
            continue
        if code is None:
            # улики нет: транспорт молчал и на повторах. Не дефект и не «ок» -
            # честное непокрытие отдельной цифрой (сторож видит дыру в охвате)
            out.append(finding(
                final, ref, resolved, None, UNCHECKED,
                reason=f"проверить нечем: транспорт не ответил ({err or 'нет ответа'}) "
                       f"после повторов ({max(1, попыток)})"))
            continue
        klass = D_RELMISMATCH if is_relative(ref.raw) else D_HTTP
        out.append(finding(final, ref, resolved, code, klass, reason=err))

    # подсказка фикса: битый относительный путь + живой корневой вариант.
    # Сюда попадают только ссылки С КОДОМ ответа - у молчащих класс UNCHECKED
    broken_rel = [f for f in out if f["class"] == D_RELMISMATCH]
    if broken_rel:
        root = urlunsplit(urlsplit(base)[:2] + ("/", "", ""))
        cand = {}
        for f in broken_rel:
            cand[f["raw"]] = norm_url(urljoin(root, "/" + f["raw"].lstrip("/")))
        cand_codes = http.status_many(list(cand.values()))
        for f in broken_rel:
            c = cand[f["raw"]]
            code, _fin, _err = cand_codes[c]
            if код_живой(code):
                f["hint"] = ("добавить ведущий слэш: "
                             f"{f['raw']} -> /{f['raw'].lstrip('/')} (живой: {c})")
            elif code is not None:
                f["hint"] = ("относительный путь резолвится в "
                             f"{f['resolved']}; корневой вариант /{f['raw'].lstrip('/')} "
                             f"тоже не отвечает (HTTP {code}) - искать реальный адрес файла")
            else:
                # про корневой вариант мы не знаем НИЧЕГО - так и говорим
                f["hint"] = ("относительный путь резолвится в "
                             f"{f['resolved']}; корневой вариант /{f['raw'].lstrip('/')} "
                             "проверить нечем (транспорт не ответил) - проверить руками")
    for f in out:
        # подсказку даём ТОЛЬКО когда код есть: без кода она врала («файл не
        # залит или переименован» на обычном таймауте - ложный диагноз, который
        # отправлял чинить целый файл)
        if f["class"] == D_HTTP and f["hint"] is None and f["status"] is not None:
            f["hint"] = "абсолютный путь ведёт в никуда: файл не залит или переименован"
    return out, final


# ── режим LOCAL ──────────────────────────────────────────────────────────────

def page_url_from_html(page):
    """Канонический путь страницы из неё самой (canonical, иначе og:url)."""
    for val in (page.canonical, page.og_url):
        if val:
            s = urlsplit(val)
            return (urlunsplit(("", "", s.path or "/", "", "")),
                    urlunsplit((s.scheme, s.netloc, "", "", "")) if s.netloc else "")
    return None, ""


def dir_of(url_path):
    if url_path.endswith("/"):
        return url_path
    return posixpath.dirname(url_path).rstrip("/") + "/"


def assets_prefix_from(page_dir, assets_remote):
    """Куда лягут картинки статьи на проде. ОДНА семантика с движком публикации.

    Значение --assets-remote читается КАК У ДЕПЛОЯ: это remote-путь каталога
    картинок ОТ КОРНЯ САЙТА (у движка - от ftp_root), ведущий слэш необязателен.
    `assets/<slug>` и `/assets/<slug>` - одно и то же место /assets/<slug>/.
    Так строка из шапки движка (`--assets-remote assets/<slug>`) означает здесь
    ровно то же, что там, и скопированный дословно флаг не даёт ложного «чисто».

    Редкий случай «каталог картинок относительно каталога страницы» задаётся
    ЯВНОЙ относительной формой - с `./` или `../` в начале (`./assets`,
    `../shared/assets`). Флаг не задан вообще = каталожная раскладка
    `<каталог страницы>/assets/` (то же, что `./assets`) - дефолт движка.
    """
    ar = (assets_remote or "").strip()
    if not ar:
        return urljoin(page_dir, "assets/")            # дефолт: каталожная раскладка
    if ar.startswith("./") or ar.startswith("../") or ar in (".", ".."):
        return urljoin(page_dir, ar.rstrip("/") + "/")  # явная относительная форма
    core = ar.strip("/")
    return "/" + core + "/" if core else "/"            # путь от корня сайта


def assets_remote_mode(assets_remote):
    """Как прочитано значение флага - строкой для шапки отчёта (гадать не нужно)."""
    ar = (assets_remote or "").strip()
    if not ar:
        return "флаг не задан - каталожная раскладка (дефолт движка)"
    if ar.startswith("./") or ar.startswith("../") or ar in (".", ".."):
        return "явная форма ./ - относительно каталога страницы"
    return "путь от корня сайта (та же семантика, что у движка публикации)"


def build_layout(article_dir, page_url, assets_remote):
    """Карта «путь на проде -> локальный каталог», длинные префиксы первыми."""
    page_dir = dir_of(page_url)
    assets_prefix = assets_prefix_from(page_dir, assets_remote)
    maps = [(assets_prefix, os.path.join(article_dir, "assets"))]
    if page_dir != "/":
        # файлы рядом со страницей (каталожная раскладка, --include-loose у деплоя)
        maps.append((page_dir, article_dir))
    maps.sort(key=lambda t: len(t[0]), reverse=True)
    return maps, assets_prefix, page_dir


def local_path_for(prod_path, maps, page_dir=None):
    """(локальный файл, «под каталогом страницы, но НЕ уедет туда»).

    Второй элемент - причина, по которой карта раскладки ссылку НЕ приняла, хотя
    формально та попала под каталог страницы. Разница принципиальная:

      None, False - ссылка ведёт ВНЕ артефактов статьи (общий файл сайта).
                    Локально её судить нечем, это не дефект.
      None, True  - ссылка ведёт ВНУТРЬ каталога страницы, но по вложенному
                    пути, которого в заливке не будет: рядом со страницей движок
                    кладёт РОВНО верхний уровень каталога статьи (collect_files
                    идёт по os.listdir без рекурсии, --include-loose такой же
                    плоский), а всё вложенное уезжает только через assets_prefix.

    Ради второй ветки правка и сделана. Раньше карта «page_dir -> article_dir»
    проглатывала ЛЮБОЙ путь под каталогом страницы, и при плоской раскладке
    (страница отдаётся по /<slug>/, картинки живут в общем /assets/<slug>/)
    относительный `assets/hero.webp` резолвился в /<slug>/assets/hero.webp,
    находил локальный файл в article_dir/assets и печатался как ok - при том,
    что на прод по этому адресу не уедет ничего и браузер получит 404. Это ровно
    тот класс (relative-path-mismatch), ради которого написан весь инструмент.
    """
    for prefix, root in maps:
        if prod_path.startswith(prefix):
            rel = prod_path[len(prefix):]
            if rel in ("", "/"):
                return None, False
            if page_dir is not None and prefix == page_dir and "/" in rel.strip("/"):
                return None, True
            return os.path.join(root, *rel.split("/")), False
    return None, False


def suggest_fix(article_dir, raw, assets_prefix, page_dir):
    """Где файл лежит НА САМОМ ДЕЛЕ и каким должен быть путь на странице."""
    rel = raw.split("?")[0].split("#")[0].lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if not parts:
        return None
    cands = []
    cands.append((os.path.join(article_dir, "assets", parts[-1]),
                  assets_prefix + parts[-1]))
    if parts[0] == "assets" and len(parts) > 1:
        tail = "/".join(parts[1:])
        cands.append((os.path.join(article_dir, "assets", *parts[1:]),
                      assets_prefix + tail))
    cands.append((os.path.join(article_dir, *parts), page_dir + "/".join(parts)))
    for local, prod in cands:
        if os.path.isfile(local):
            return prod, local
    return None


def check_local_page(index_html, article_dir, page_url, assets_remote,
                     base_url="", http=None, check_outside=False,
                     require_local_files=False):
    """Findings по локальному каталогу статьи против раскладки прода.

    🔴 ЧТО ЗДЕСЬ ДОКАЗУЕМО, А ЧТО НЕТ (правка 24.08.2026). Режим --local судит
    РАСКЛАДКУ: куда ссылка попадёт на проде и кладёт ли туда что-нибудь заливка.
    Это выводится из самого каталога и остаётся жёстким вердиктом.

    А вот «своей КОРНЕВОЙ ссылки нет рядом локального файла» - НЕ вердикт этого
    прогона. На заливке «ТОЛЬКО СТРАНИЦА» (каталог = index.html, картинки давно
    живут на проде) таких ссылок весь лист, и раньше --local краснел на каждой:
    exit 1 на здоровой статье. Ровно этот класс уже признан ложным и снят в
    article_gates.py (гейт image-refs, правило 5) - сюда закон спущен этой
    правкой. Ответ знают только двое, и у обоих он есть:
      относительные ссылки - контракт не менялся: файл обязан лежать рядом,
                             отсутствие остаётся ЖЁСТКИМ missing-local-file;
      корневые ссылки      - предполёт ftp_publish: у него И набор заливки,
                             И живой прод, только он отличает «файла нет нигде»
                             от «файл уже на проде».
    require_local_files=True возвращает старое жёсткое суждение - для вызова
    оттуда, где каталог гарантированно самодостаточен. По умолчанию ВЫКЛЮЧЕНО:
    та же семантика и то же имя, что у флага --require-local-files гейта
    article_gates.py.
    """
    try:
        with open(index_html, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    except OSError as e:
        ref = Ref("page", index_html, 0)
        return [finding(index_html, ref, None, None, D_PAGE, reason=str(e))], page_url

    page = parse_page(html)
    if not page_url:
        page_url, host_from_page = page_url_from_html(page)
        if not base_url:
            base_url = host_from_page
    if not page_url:
        ref = Ref("page", index_html, 0)
        return [finding(index_html, ref, None, None, D_PAGE,
                        reason="в странице нет canonical/og:url, а --page-url не задан")], ""

    maps, assets_prefix, page_dir = build_layout(article_dir, page_url, assets_remote)
    base_for_join = urljoin(base_url + "/", page_url) if base_url else page_url
    host = urlsplit(base_for_join).netloc.lower()
    if page.base_href:
        base_for_join = urljoin(base_for_join, page.base_href)

    out = []
    outside = []
    for ref in page.refs:
        klass, reason = ref_kind_of_raw(ref.raw)
        if klass is not None:
            out.append(finding(page_url, ref, None, None, klass, reason=reason))
            continue
        resolved_full = norm_url(urljoin(base_for_join, ref.raw))
        s = urlsplit(resolved_full)
        if s.netloc and host and s.netloc.lower() != host:
            out.append(finding(page_url, ref, resolved_full, None, EXTERNAL))
            continue
        if s.netloc and not host:
            out.append(finding(page_url, ref, resolved_full, None, EXTERNAL))
            continue
        prod_path = s.path
        local, вложенный = local_path_for(prod_path, maps, page_dir)
        if local is None and not вложенный:
            f = finding(page_url, ref, prod_path, None, OUTSIDE,
                        reason="вне артефактов статьи (общий файл сайта), локально не проверяется")
            out.append(f)
            outside.append((f, resolved_full))
            continue
        if local is not None and os.path.isfile(local):
            out.append(finding(page_url, ref, prod_path, "file", OK))
            continue
        fix = suggest_fix(article_dir, ref.raw, assets_prefix, page_dir)
        if fix and is_relative(ref.raw):
            prod, real_local = fix
            out.append(finding(
                page_url, ref, prod_path, "нет файла", D_RELMISMATCH,
                reason=(f"относительный путь при этой раскладке резолвится в {prod_path}, "
                        f"а файл лежит по {prod} (локально {real_local})"),
                hint=f"путь на странице: {ref.raw} -> {prod}"))
        elif fix:
            prod, real_local = fix
            out.append(finding(
                page_url, ref, prod_path, "нет файла", D_MISSING_LOCAL,
                reason=f"по {prod_path} файла нет, похожий найден по {prod}",
                hint=f"путь на странице: {ref.raw} -> {prod}"))
        elif вложенный:
            out.append(finding(
                page_url, ref, prod_path, "нет файла", D_MISSING_LOCAL,
                reason=(f"{prod_path} лежит под каталогом страницы, но заливка кладёт "
                        f"туда только верхний уровень каталога статьи - по этому "
                        f"вложенному адресу на проде не будет ничего"),
                hint=f"картинки статьи уезжают в {assets_prefix} - писать путь туда"))
        elif is_relative(ref.raw) or require_local_files:
            out.append(finding(
                page_url, ref, prod_path, "нет файла", D_MISSING_LOCAL,
                reason=f"локально нет файла {local}"
                       + ("" if is_relative(ref.raw)
                          else " (судим по требованию вызвавшего: --require-local-files)"),
                hint="картинка не создана или лежит не в assets/ каталога статьи"))
        else:
            # своя КОРНЕВАЯ ссылка без локального файла: не дефект этого прогона
            out.append(finding(
                page_url, ref, prod_path, "локально нет", NOLOCAL,
                reason=(f"локально нет файла {local} - это НЕ вердикт --local: файл "
                        f"может уже лежать на проде или ехать из другого каталога. "
                        f"Факт файла судит предполёт ftp_publish (у него и набор "
                        f"заливки, и живой прод)"),
                hint="требовать локальный файл прямо здесь: --require-local-files"))

    if check_outside and http is not None and base_url:
        urls = [u for _f, u in outside if urlsplit(u).netloc]
        codes = http.status_many(urls)
        for f, u in outside:
            if u not in codes:
                continue
            code, _fin, err = codes[u]
            if code is not None and 200 <= code < 300:
                f["status"] = code
            else:
                f["class"] = D_HTTP
                f["status"] = code
                f["reason"] = err or "общий файл сайта не отвечает"
                f["hint"] = "файл вне статьи, чинится там, где он публикуется"
    return out, page_url


# ── отчёт ────────────────────────────────────────────────────────────────────

def summarize(findings):
    counts = {}
    for f in findings:
        counts[f["class"]] = counts.get(f["class"], 0) + 1
    defects = [f for f in findings if f["class"] in DEFECT_CLASSES]
    return counts, defects


def report(findings, mode, header_lines, as_json, stream=sys.stdout):
    counts, defects = summarize(findings)
    pages = sorted({f["page"] for f in findings})
    непроверенные = [f for f in findings if f["class"] == UNCHECKED]
    без_файла = [f for f in findings if f["class"] == NOLOCAL]
    payload = {
        "tool": TOOL,
        "mode": mode,
        "pages": pages,
        "refs_total": len(findings),
        "counts": counts,
        "defects": defects,
        # 🔴 отдельные цифры непокрытия: НЕ дефекты (exit не роняют), но и не
        # тишина - сторож обязан видеть, что часть ссылок судить было нечем
        "unchecked_total": len(непроверенные),
        "unchecked": непроверенные,
        "local_file_unknown_total": len(без_файла),
        "local_file_unknown": без_файла,
        "ok": len(defects) == 0,
    }
    if as_json:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    else:
        for line in header_lines:
            print(line, file=stream)
        print(f"страниц: {len(pages)} · ссылок на картинки: {len(findings)}", file=stream)
        order = ([OK, EXTERNAL, OUTSIDE, SKIP_DATA, SKIP_SCHEME]
                 + list(DEFECT_CLASSES) + list(SOFT_CLASSES))
        parts = [f"{k}={counts[k]}" for k in order if counts.get(k)]
        print("классы: " + (", ".join(parts) if parts else "пусто"), file=stream)
        # непокрытие - отдельной строкой шапки, до списка дефектов: это не
        # дефект и не «чисто», это «судить было нечем», и адресат у каждой
        # цифры свой
        if непроверенные:
            print(f"ПРОВЕРИТЬ НЕЧЕМ: {len(непроверенные)} ссылок - транспорт не "
                  f"ответил даже с повторов. Это НЕ дефект и не «чисто», это дыра "
                  f"в покрытии: связь/таймаут на нашей стороне, ссылку никто не "
                  f"судил", file=stream)
        if без_файла:
            print(f"БЕЗ ЛОКАЛЬНОГО ФАЙЛА: {len(без_файла)} своих корневых ссылок - "
                  f"не вердикт --local (файл может уже лежать на проде). Факт файла "
                  f"судит предполёт ftp_publish: у него и набор заливки, и живой "
                  f"прод. Требовать файл здесь: --require-local-files", file=stream)
        if defects:
            print("", file=stream)
            print(f"ДЕФЕКТЫ ({len(defects)}):", file=stream)
            by_page = {}
            for f in defects:
                by_page.setdefault(f["page"], []).append(f)
            for pg in sorted(by_page):
                print(f"\n  {pg}", file=stream)
                for f in by_page[pg]:
                    print(f"    [{f['class']}] {f['kind']} строка {f['line']}", file=stream)
                    print(f"      сырой путь : {f['raw']}", file=stream)
                    if f["resolved"]:
                        print(f"      резолв     : {f['resolved']}", file=stream)
                    if f["status"] is not None:
                        print(f"      результат  : {f['status']}", file=stream)
                    if f["reason"]:
                        print(f"      причина    : {f['reason']}", file=stream)
                    if f["hint"]:
                        print(f"      подсказка  : {f['hint']}", file=stream)
            print(f"\nИТОГ: ДЕФЕКТЫ, {len(defects)} шт"
                  + (f" · плюс проверить нечем: {len(непроверенные)}"
                     if непроверенные else "")
                  + (f" · без локального файла: {len(без_файла)}"
                     if без_файла else ""), file=stream)
        else:
            хвост = ""
            if непроверенные or без_файла:
                куски = []
                if непроверенные:
                    куски.append(f"проверить нечем {len(непроверенные)}")
                if без_файла:
                    куски.append(f"без локального файла {len(без_файла)}")
                хвост = " (покрытие неполное: " + ", ".join(куски) + ")"
            print("\nИТОГ: чисто, битых ссылок на картинки нет" + хвост, file=stream)
    return 1 if defects else 0


# ── сбор целей ───────────────────────────────────────────────────────────────

def load_config(path):
    try:
        with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 - конфига может не быть, это норма
        return {}


def targets_from_args(values, http, sitemap=None, flt=None, limit=0):
    urls = []
    for v in values or []:
        if os.path.isfile(v):
            with open(v, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        else:
            urls.append(v)
    if sitemap:
        text, err = http.get_text(sitemap)
        if text is None:
            die(f"sitemap не скачался: {err}")
        urls.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text))
    if flt:
        rx = re.compile(flt)
        urls = [u for u in urls if rx.search(u)]
    urls = list(dict.fromkeys(urls))
    if limit:
        urls = urls[:limit]
    return urls


# ── селфтест (офлайн) ────────────────────────────────────────────────────────

CANON = "https://example.test"

CAT_PAGE = """<!doctype html><html><head>
<link rel="canonical" href="{canon}/demo/" />
<meta property="og:image" content="{canon}/assets/site-og.jpg" />
<link rel="icon" href="/favicon.ico" />
<style>.b{{background-image:url('assets/bg.png')}}</style>
</head><body>
<figure><picture>
  <source type="image/webp" srcset="assets/hero-720.webp 720w, assets/hero.webp 1200w" />
  <source type="image/avif" srcset="assets/hero.avif 1200w" />
  <img src="assets/hero.jpg" srcset="assets/hero.jpg 1x, assets/hero-2x.jpg 2x" alt="a" />
</picture></figure>
<img src="data:image/svg+xml;utf8,<svg/>" alt="inline" />
<img srcset="data:image/svg+xml,<svg/>,x 1x, assets/hero.jpg 2x" alt="mixed" />
<img src="/assets/root-shared.webp" alt="shared" />
<img src="assets/missing.webp" alt="missing" />
<div style="background:url(assets/bg.png) no-repeat"></div>
</body></html>"""

FLAT_REL_PAGE = """<!doctype html><html><head>
<link rel="canonical" href="{canon}/demo/" />
</head><body><picture>
  <source type="image/webp" srcset="assets/demo/hero-720.webp 720w, assets/demo/hero.webp 1200w" />
  <img src="/assets/demo/hero.jpg" alt="a" />
</picture></body></html>"""

FLAT_ABS_PAGE = """<!doctype html><html><head>
<link rel="canonical" href="{canon}/demo/" />
</head><body><picture>
  <source type="image/webp" srcset="/assets/demo/hero-720.webp 720w, /assets/demo/hero.webp 1200w" />
  <img src="/assets/demo/hero.jpg" alt="a" />
</picture></body></html>"""


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\x00")


def selftest():
    cases = []

    def check(name, cond, detail=""):
        cases.append((name, bool(cond), detail))

    tmp = tempfile.mkdtemp(prefix="image-health-selftest-")
    try:
        # --- каталожная раскладка -------------------------------------------
        cat = os.path.join(tmp, "cat")
        for n in ("hero.jpg", "hero-2x.jpg", "hero-720.webp", "hero.webp",
                  "hero.avif", "bg.png"):
            _touch(os.path.join(cat, "assets", n))
        idx = os.path.join(cat, "index.html")
        with open(idx, "w", encoding="utf-8") as fh:
            fh.write(CAT_PAGE.format(canon=CANON))

        # флаг не задан = дефолт = каталожная раскладка (та же, что у движка)
        f_cat, _ = check_local_page(idx, cat, "", None)
        by_cls = {}
        for f in f_cat:
            by_cls.setdefault(f["class"], []).append(f)
        kinds = [f["kind"] for f in f_cat]

        check("1. относительный путь при каталожной раскладке = ok",
              all(f["class"] == OK for f in f_cat
                  if f["raw"].startswith("assets/") and "missing" not in f["raw"]),
              detail=str([(f["raw"], f["class"]) for f in f_cat
                          if f["raw"].startswith("assets/")]))
        check("4a. data:-URI в img[src] пропущен, не дефект",
              any(f["class"] == SKIP_DATA and f["kind"] == "img-src" for f in f_cat))
        check("4b. data:-URI внутри srcset пропущен",
              any(f["class"] == SKIP_DATA and f["kind"] == "img-srcset" for f in f_cat))
        check("5a. srcset с дескрипторами w: оба кандидата собраны",
              sorted([f["raw"] for f in f_cat if f["kind"] == "source-srcset"]) ==
              ["assets/hero-720.webp", "assets/hero.avif", "assets/hero.webp"],
              detail=str([f["raw"] for f in f_cat if f["kind"] == "source-srcset"]))
        check("5b. srcset с дескрипторами x: оба кандидата собраны",
              "assets/hero-2x.jpg" in [f["raw"] for f in f_cat if f["kind"] == "img-srcset"])
        check("6. picture с несколькими source: собраны все",
              len([f for f in f_cat if f["kind"] == "source-srcset"]) == 3)
        check("7. отсутствующий локальный файл = дефект",
              any(f["class"] == D_MISSING_LOCAL and f["raw"] == "assets/missing.webp"
                  for f in f_cat),
              detail=str([(f["raw"], f["class"]) for f in by_cls.get(D_MISSING_LOCAL, [])]))
        check("8. og:image собран как ссылка",
              "meta-og-image" in kinds)
        check("8б. og:image вне статьи = не дефект локально",
              all(f["class"] == OUTSIDE for f in f_cat if f["kind"] == "meta-og-image"))
        check("9. запятая внутри data:-URI не рвёт srcset на два кандидата",
              parse_srcset('data:image/svg+xml,<svg/>,x 1x, assets/hero.jpg 2x') ==
              ["data:image/svg+xml,<svg/>,x", "assets/hero.jpg"],
              detail=str(parse_srcset('data:image/svg+xml,<svg/>,x 1x, assets/hero.jpg 2x')))
        check("10a. url() в <style> собран",
              any(f["kind"] == "style-block-url" and f["class"] == OK for f in f_cat))
        check("10b. url() в style=\"\" собран",
              any(f["kind"] == "style-attr-url" and f["class"] == OK for f in f_cat))
        check("10в. link rel=icon собран",
              "link-icon" in kinds)
        check("11a. каталожная страница даёт ровно один дефект (missing)",
              len([f for f in f_cat if f["class"] in DEFECT_CLASSES]) == 1,
              detail=str([(f["raw"], f["class"]) for f in f_cat
                          if f["class"] in DEFECT_CLASSES]))

        # --- плоская раскладка, относительный путь --------------------------
        flat = os.path.join(tmp, "flat")
        for n in ("hero.jpg", "hero-720.webp", "hero.webp"):
            _touch(os.path.join(flat, "assets", n))
        fidx = os.path.join(flat, "index.html")
        with open(fidx, "w", encoding="utf-8") as fh:
            fh.write(FLAT_REL_PAGE.format(canon=CANON))
        f_flat, _ = check_local_page(fidx, flat, "/demo/", "/assets/demo")
        rel_defects = [f for f in f_flat if f["class"] == D_RELMISMATCH]
        check("2. тот же относительный путь при плоской раскладке = relative-path-mismatch",
              len(rel_defects) == 2,
              detail=str([(f["raw"], f["class"], f["resolved"]) for f in f_flat]))
        check("2б. подсказка называет корневой путь с ведущим слэшем",
              rel_defects and all("/assets/demo/" in (f["hint"] or "") for f in rel_defects),
              detail=str([f["hint"] for f in rel_defects]))
        check("2в. резолв показан как на проде (/demo/assets/demo/...)",
              rel_defects and all(f["resolved"].startswith("/demo/assets/demo/")
                                  for f in rel_defects),
              detail=str([f["resolved"] for f in rel_defects]))
        check("11b. плоская страница с относительным путём = exit 1",
              report(f_flat, "local", [], True, stream=open(os.devnull, "w")) == 1)

        # --- плоская раскладка, абсолютный путь -----------------------------
        aidx = os.path.join(flat, "abs.html")
        with open(aidx, "w", encoding="utf-8") as fh:
            fh.write(FLAT_ABS_PAGE.format(canon=CANON))
        f_abs, _ = check_local_page(aidx, flat, "/demo/", "/assets/demo")
        check("3. абсолютный путь при плоской раскладке = ok",
              all(f["class"] == OK for f in f_abs if f["kind"].startswith(("img-", "source-"))),
              detail=str([(f["raw"], f["class"]) for f in f_abs]))
        check("11c. чистая страница = exit 0",
              report(f_abs, "local", [], True, stream=open(os.devnull, "w")) == 0)

        # --- резолв live-режима (офлайн, только urljoin) ---------------------
        base = f"{CANON}/demo/"
        check("12a. live-резолв относительного пути = URL внутри каталога страницы",
              norm_url(urljoin(base, "assets/demo/hero.webp")) ==
              f"{CANON}/demo/assets/demo/hero.webp")
        check("12b. live-резолв корневого пути = URL от корня сайта",
              norm_url(urljoin(base, "/assets/demo/hero.webp")) ==
              f"{CANON}/assets/demo/hero.webp")
        check("12в. чужой домен опознаётся как external",
              urlsplit(urljoin(base, "https://cdn.other.test/x.png")).netloc == "cdn.other.test")

        # --- пустой атрибут --------------------------------------------------
        eidx = os.path.join(flat, "empty.html")
        with open(eidx, "w", encoding="utf-8") as fh:
            fh.write('<html><head><link rel="canonical" href="%s/demo/"></head>'
                     '<body><img src="" alt="x"></body></html>' % CANON)
        f_empty, _ = check_local_page(eidx, flat, "/demo/", "/assets/demo")
        check("13. пустой src = дефект empty-ref",
              any(f["class"] == D_EMPTY for f in f_empty))

        # --- семантика --assets-remote едина с движком публикации ------------
        # Как тот же аргумент читает ftp_publish (моделируем вычислением, без
        # импорта движка): assets_remote = args.assets_remote.strip("/"), файл
        # уезжает в f"{prefix}/{имя}" ОТ ftp_root, значит URL = /{prefix}/{имя}.
        def ftp_assets_prefix(value):
            prefix = (value or "").strip("/")
            return "/" + prefix + "/" if prefix else "/"

        def ih_assets_prefix(value, page_dir="/guide-demo/"):
            return build_layout(flat, page_dir, value)[1]

        check("14a. значение без слэша = ТА ЖЕ раскладка, что у ftp_publish",
              ih_assets_prefix("assets/guide-demo") == ftp_assets_prefix("assets/guide-demo")
              == "/assets/guide-demo/",
              detail=f'чекер {ih_assets_prefix("assets/guide-demo")} · '
                     f'движок {ftp_assets_prefix("assets/guide-demo")}')
        check("14b. ведущий слэш ничего не меняет (обе формы = одно место)",
              ih_assets_prefix("/assets/guide-demo") == ih_assets_prefix("assets/guide-demo")
              == ftp_assets_prefix("/assets/guide-demo"),
              detail=f'{ih_assets_prefix("/assets/guide-demo")} vs '
                     f'{ih_assets_prefix("assets/guide-demo")}')
        check("14в. флаг не задан = каталожная раскладка (дефолт не изменился)",
              ih_assets_prefix(None) == "/guide-demo/assets/"
              == ftp_assets_prefix("guide-demo/assets"),
              detail=str(ih_assets_prefix(None)))
        check("14г. явная относительная форма ./assets = тот же дефолт",
              ih_assets_prefix("./assets") == ih_assets_prefix(None) == "/guide-demo/assets/",
              detail=str(ih_assets_prefix("./assets")))
        check("14д. ../ поднимается на уровень выше каталога страницы",
              ih_assets_prefix("../shared", "/a/b/") == "/a/shared/",
              detail=str(ih_assets_prefix("../shared", "/a/b/")))

        # боевой дефект: значение скопировано из шапки движка дословно
        mix = os.path.join(tmp, "mix")
        for n in ("hero.webp", "hero.jpg"):
            _touch(os.path.join(mix, "assets", n))
        midx = os.path.join(mix, "index.html")
        with open(midx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/">'
                     '</head><body><picture>'
                     '<source type="image/webp" srcset="assets/guide-demo/hero.webp">'
                     '<img src="/assets/guide-demo/hero.jpg" alt="a">'
                     '</picture></body></html>' % CANON)
        f_mix, _ = check_local_page(midx, mix, "/guide-demo/", "assets/guide-demo")
        check("14е. значение из шапки движка ловит боевой дефект (srcset без слэша)",
              any(f["class"] == D_RELMISMATCH and f["raw"] == "assets/guide-demo/hero.webp"
                  for f in f_mix),
              detail=str([(f["raw"], f["class"]) for f in f_mix]))
        check("14ж. и даёт exit 1, а не ложное «чисто»",
              report(f_mix, "local", [], True, stream=open(os.devnull, "w")) == 1,
              detail=str([(f["raw"], f["class"]) for f in f_mix]))

        # --- 15. полноразмерная картинка лайтбокса: a[href] --------------------
        # Её запрашивает не разбор разметки, а клик читателя, поэтому битой её
        # видит только он. Отбор по расширению файла, класс вёрстки не участвует.
        zoom = os.path.join(tmp, "zoom")
        _touch(os.path.join(zoom, "assets", "shot.webp"))
        _touch(os.path.join(zoom, "assets", "shot-full.jpg"))
        zidx = os.path.join(zoom, "index.html")
        with open(zidx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/"></head><body>'
                     '<figure class="fig">'
                     '<a class="zoom" href="assets/net-takogo.jpg">'
                     '<img src="assets/shot.webp" alt="a"></a></figure>'
                     '<figure><a class="lupa" href="assets/shot-full.jpg">'
                     '<img src="assets/shot.webp" alt="b"></a></figure>'
                     '<p><a href="/guide-drugoy/">обычная ссылка</a> и '
                     '<a href="#верх">якорь</a> и '
                     '<a href="assets/gajd.pdf">файл не картинка</a></p>'
                     '</body></html>' % CANON)
        f_zoom, _ = check_local_page(zidx, zoom, "", None)
        zoom_kinds = [f for f in f_zoom if f["kind"] == "a-href"]
        check("15a. a[href] с картиночным расширением собран (лайтбокс)",
              sorted(f["raw"] for f in zoom_kinds) ==
              ["assets/net-takogo.jpg", "assets/shot-full.jpg"],
              detail=str([(f["raw"], f["class"]) for f in zoom_kinds]))
        check("15б. битый href лайтбокса = дефект",
              any(f["class"] in DEFECT_CLASSES and f["raw"] == "assets/net-takogo.jpg"
                  for f in zoom_kinds),
              detail=str([(f["raw"], f["class"]) for f in zoom_kinds]))
        check("15в. живой href лайтбокса = ok",
              any(f["class"] == OK and f["raw"] == "assets/shot-full.jpg"
                  for f in zoom_kinds))
        check("15г. навигация, якорь и не-картинка в a[href] НЕ собираются",
              not any(f["raw"] in ("/guide-drugoy/", "#верх", "assets/gajd.pdf")
                      for f in f_zoom),
              detail=str([f["raw"] for f in f_zoom]))
        check("15д. битый лайтбокс роняет прогон в exit 1",
              report(f_zoom, "local", [], True, stream=open(os.devnull, "w")) == 1)

        # --- 16. предзагрузка хиро: link[rel=preload][as=image] ---------------
        pre = os.path.join(tmp, "preload")
        _touch(os.path.join(pre, "assets", "hero.webp"))
        pidx = os.path.join(pre, "index.html")
        with open(pidx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/">'
                     '<link rel="preload" as="image" href="assets/net-hiro.webp" '
                     'imagesrcset="assets/net-hiro-720.webp 720w, assets/hero.webp 1200w">'
                     '<link rel="preload" as="font" href="/assets/fonts/x.woff2" '
                     'crossorigin>'
                     '</head><body><img src="assets/hero.webp" alt="a"></body></html>'
                     % CANON)
        f_pre, _ = check_local_page(pidx, pre, "", None)
        pre_refs = [f for f in f_pre if f["kind"].startswith("link-preload")]
        check("16a. preload as=image собран: href + каждый кандидат imagesrcset",
              sorted(f["raw"] for f in pre_refs) ==
              ["assets/hero.webp", "assets/net-hiro-720.webp", "assets/net-hiro.webp"],
              detail=str([(f["kind"], f["raw"]) for f in pre_refs]))
        check("16б. битый preload-хиро = дефект",
              len([f for f in pre_refs if f["class"] in DEFECT_CLASSES]) == 2,
              detail=str([(f["raw"], f["class"]) for f in pre_refs]))
        check("16в. preload шрифта НЕ считается картинкой",
              not any(f["raw"] == "/assets/fonts/x.woff2" for f in f_pre),
              detail=str([f["raw"] for f in f_pre]))
        check("16г. битый preload роняет прогон в exit 1",
              report(f_pre, "local", [], True, stream=open(os.devnull, "w")) == 1)

        # --- 17. ПЛОСКИЙ деплой + обычная каталожная ссылка БЕЗ слага ---------
        # Общий случай того же класса, ради которого написан инструмент: страница
        # отдаётся по /<slug>/, картинки уезжают в общий /assets/<slug>/, а на
        # странице стоит `assets/hero.webp`. Резолв даёт /<slug>/assets/hero.webp,
        # куда заливка не кладёт НИЧЕГО (рядом со страницей едет только верхний
        # уровень каталога статьи). Раньше карта раскладки уводила резолв в
        # локальный article_dir/assets и печатала ok.
        f2 = os.path.join(tmp, "flat2")
        for n in ("hero.webp", "hero-720.webp", "hero.jpg"):
            _touch(os.path.join(f2, "assets", n))
        f2idx = os.path.join(f2, "index.html")
        with open(f2idx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/"></head><body>'
                     '<picture>'
                     '<source srcset="assets/hero-720.webp 720w, assets/hero.webp 1200w">'
                     '<img src="assets/hero.jpg" alt="a"></picture>'
                     '</body></html>' % CANON)
        f_f2, _ = check_local_page(f2idx, f2, "/guide-demo/", "assets/guide-demo")
        check("17a. плоский деплой + относительная ссылка БЕЗ слага = "
              "relative-path-mismatch, а не ok",
              len([f for f in f_f2 if f["class"] == D_RELMISMATCH]) == 3
              and not any(f["class"] == OK for f in f_f2),
              detail=str([(f["raw"], f["class"]) for f in f_f2]))
        check("17б. подсказка называет реальный адрес картинок на проде",
              all("/assets/guide-demo/" in (f["hint"] or "")
                  for f in f_f2 if f["class"] == D_RELMISMATCH),
              detail=str([f["hint"] for f in f_f2]))
        check("17в. и это exit 1, а не ложное «чисто»",
              report(f_f2, "local", [], True, stream=open(os.devnull, "w")) == 1)
        # обратная сторона: каталожную раскладку правка не тронула
        f_f2cat, _ = check_local_page(f2idx, f2, "/guide-demo/", None)
        check("17г. та же страница при КАТАЛОЖНОЙ раскладке по-прежнему чиста",
              all(f["class"] == OK for f in f_f2cat),
              detail=str([(f["raw"], f["class"]) for f in f_f2cat]))
        # и плоский файл РЯДОМ со страницей (один сегмент) остаётся ok
        _touch(os.path.join(f2, "ryadom.png"))
        looseidx = os.path.join(f2, "loose.html")
        with open(looseidx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/"></head>'
                     '<body><img src="ryadom.png" alt="a"></body></html>' % CANON)
        f_loose, _ = check_local_page(looseidx, f2, "/guide-demo/", "assets/guide-demo")
        check("17д. файл РЯДОМ со страницей (один сегмент) остаётся ok",
              all(f["class"] == OK for f in f_loose),
              detail=str([(f["raw"], f["class"]) for f in f_loose]))

        # --- 18. ЗАКОН УЛИК В --live: МОЛЧАНИЕ ТРАНСПОРТА - НЕ ДЕФЕКТ ---------
        # Находка скептика по решению автора: status=None (таймаут, обрыв, DNS) уезжал в
        # http-error / relative-path-mismatch и получал подсказку «файл не залит
        # или переименован». Повторов не делалось ни одного, а --live гоняет по
        # всему sitemap ежедневный сторож - выдуманный дефект каждую икоту сети.
        живая_стр = ('<html><head><meta charset="utf-8">'
                     '<link rel="canonical" href="%s/guide-demo/"></head><body>'
                     '<img src="/assets/demo/hero.webp" alt="корневая">'
                     '<img src="assets/demo/vtoroy.webp" alt="относительная">'
                     '</body></html>' % CANON)

        class ФейкМолчит(object):
            """Страница качается, картинки не отвечают (code=None) N раз подряд."""

            def __init__(self, html, отвечает_с=None):
                self.html, self.отвечает_с, self.n = html, отвечает_с, 0

            def get_text(self, _url):
                return self.html, f"{CANON}/guide-demo/"

            def status_many(self, urls):
                self.n += 1
                if self.отвечает_с is not None and self.n >= self.отвечает_с:
                    return {u: (200, u, None) for u in urls}
                return {u: (None, u, "сеть: timed out") for u in urls}

        class ФейкКоды(object):
            """Сервер ОТВЕЧАЕТ: тут улика есть, и дефект обязан остаться дефектом."""

            def __init__(self, html, коды, дефолт=404):
                self.html, self.коды, self.дефолт = html, коды, дефолт

            def get_text(self, _url):
                return self.html, f"{CANON}/guide-demo/"

            def status_many(self, urls):
                return {u: (self.коды.get(u, self.дефолт), u, None) for u in urls}

        ф18 = ФейкМолчит(живая_стр)
        f_18, _ = check_live_page(f"{CANON}/guide-demo/", ф18, пауза=0)
        нем = [f for f in f_18 if f["class"] == UNCHECKED]
        check("18. молчащий транспорт = класс unchecked, а не http-error/"
              "relative-path-mismatch",
              len(нем) == 2 and not any(f["class"] in DEFECT_CLASSES for f in f_18),
              detail=str([(f["raw"], f["class"]) for f in f_18]))
        check("18а. unchecked НЕ входит в DEFECT_CLASSES и не роняет exit",
              UNCHECKED not in DEFECT_CLASSES
              and report(f_18, "live", [], True, stream=open(os.devnull, "w")) == 0)
        check("18б. подсказки «файл не залит или переименован» на молчании нет",
              all(f["hint"] is None for f in нем)
              and not any("не залит или переименован" in (f["hint"] or "")
                          for f in f_18),
              detail=str([f["hint"] for f in f_18]))
        check("18в. причина названа честно: проверить нечем, транспорт не ответил",
              нем and all("проверить нечем" in (f["reason"] or "") for f in нем),
              detail=str([f["reason"] for f in нем]))
        check("18г. повторы делаются (раньше не было ни одного)",
              ф18.n >= 2, detail=f"зовов status_many: {ф18.n}")
        ф18д = ФейкМолчит(живая_стр, отвечает_с=2)
        f_18д, _ = check_live_page(f"{CANON}/guide-demo/", ф18д, пауза=0)
        check("18д. ответил 200 со ВТОРОЙ попытки - это ok, не дефект",
              all(f["class"] == OK for f in f_18д),
              detail=str([(f["raw"], f["class"]) for f in f_18д]))
        # ПАРА: сервер ОТВЕТИЛ плохо - улика есть, дефект остаётся дефектом
        f_18е, _ = check_live_page(
            f"{CANON}/guide-demo/",
            ФейкКоды(живая_стр, {f"{CANON}/assets/demo/hero.webp": 404,
                                 f"{CANON}/guide-demo/assets/demo/vtoroy.webp": 404,
                                 f"{CANON}/assets/demo/vtoroy.webp": 200}), пауза=0)
        клс18е = sorted(f["class"] for f in f_18е)
        check("18е. ПАРА к 18: честный 404 остаётся жёстким дефектом "
              "(http-error + relative-path-mismatch)",
              клс18е == [D_HTTP, D_RELMISMATCH]
              and report(f_18е, "live", [], True, stream=open(os.devnull, "w")) == 1,
              detail=str([(f["raw"], f["class"], f["status"]) for f in f_18е]))
        check("18ж. и подсказки на месте: и «ведущий слэш», и «не залит»",
              any("ведущий слэш" in (f["hint"] or "") for f in f_18е)
              and any("не залит или переименован" in (f["hint"] or "") for f in f_18е),
              detail=str([f["hint"] for f in f_18е]))
        check("18з. 3xx = живой ответ (HTTP-слой сам идёт за редиректом), не дефект",
              all(f["class"] == OK for f in check_live_page(
                  f"{CANON}/guide-demo/",
                  ФейкКоды(живая_стр, {}, дефолт=301), пауза=0)[0]))
        # цифра непокрытия отдельно: и человеку в шапке, и сторожу в --json
        буф = tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False,
                                          suffix=".txt")
        report(f_18, "live", [], False, stream=буф)
        буф.seek(0)
        текст18 = буф.read()
        буф.close()
        отложить(буф.name, ignore_errors=True)   # закон №0: не сносим, откладываем
        check("18и. в шапке отчёта непокрытие отдельной цифрой",
              "ПРОВЕРИТЬ НЕЧЕМ: 2" in текст18 and "покрытие неполное" in текст18,
              detail=текст18.strip()[-200:])
        jбуф = tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False,
                                           suffix=".json")
        report(f_18, "live", [], True, stream=jбуф)
        jбуф.seek(0)
        j18 = json.load(jбуф)
        jбуф.close()
        отложить(jбуф.name, ignore_errors=True)   # закон №0: не сносим, откладываем
        check("18к. и в --json своим полем (сторож видит дыру, а не дефект)",
              j18["unchecked_total"] == 2 and j18["defects"] == [] and j18["ok"] is True,
              detail=str({k: j18[k] for k in ("unchecked_total", "ok")}))

        # --- 19. --local: ЗАЛИВКА «ТОЛЬКО СТРАНИЦА» НЕ КРАСНЕЕТ ---------------
        # Находка скептика по решению автора: ссылка резолвится внутрь ассетов статьи,
        # локального файла рядом нет, а файл давно живёт на проде. Ровно этот
        # класс снят в article_gates.py (image-refs, правило 5) - здесь он
        # оставался жёстким, и --local краснел на здоровой статье целым листом.
        только_стр = os.path.join(tmp, "tolko-stranica")
        os.makedirs(os.path.join(только_стр, "assets"), exist_ok=True)
        tsidx = os.path.join(только_стр, "index.html")
        with open(tsidx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/"></head><body>'
                     '<picture>'
                     '<source type="image/webp" srcset="/assets/guide-demo/hero.webp">'
                     '<img src="/assets/guide-demo/hero.jpg" alt="a"></picture>'
                     '</body></html>' % CANON)
        f_ts, _ = check_local_page(tsidx, только_стр, "/guide-demo/", "assets/guide-demo")
        check("19. корневая ссылка без локального файла = local-file-unknown, "
              "а не missing-local-file",
              all(f["class"] == NOLOCAL for f in f_ts)
              and not any(f["class"] in DEFECT_CLASSES for f in f_ts),
              detail=str([(f["raw"], f["class"]) for f in f_ts]))
        check("19а. и это exit 0: ложный блок публикации хуже отсутствия гейта",
              report(f_ts, "local", [], True, stream=open(os.devnull, "w")) == 0)
        check("19б. в причине назван тот, кто ЗА НЕЁ отвечает (предполёт ftp_publish)",
              all("ftp_publish" in (f["reason"] or "") for f in f_ts),
              detail=str([f["reason"] for f in f_ts]))
        f_ts_req, _ = check_local_page(tsidx, только_стр, "/guide-demo/",
                                       "assets/guide-demo", require_local_files=True)
        check("19в. --require-local-files возвращает старое жёсткое суждение",
              all(f["class"] == D_MISSING_LOCAL for f in f_ts_req)
              and report(f_ts_req, "local", [], True,
                         stream=open(os.devnull, "w")) == 1,
              detail=str([(f["raw"], f["class"]) for f in f_ts_req]))
        # ПАРА: ОТНОСИТЕЛЬНАЯ ссылка без файла - контракт заливки, остаётся жёсткой
        отн_нет = os.path.join(tmp, "otn-net")
        os.makedirs(os.path.join(отн_нет, "assets"), exist_ok=True)
        onidx = os.path.join(отн_нет, "index.html")
        with open(onidx, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><head>'
                     '<link rel="canonical" href="%s/guide-demo/"></head><body>'
                     '<img src="assets/hero.webp" alt="a"></body></html>' % CANON)
        f_on, _ = check_local_page(onidx, отн_нет, "/guide-demo/", None)
        check("19г. ПАРА к 19: ОТНОСИТЕЛЬНАЯ ссылка без файла рядом - "
              "по-прежнему жёсткий missing-local-file (контракт заливки не менялся)",
              any(f["class"] == D_MISSING_LOCAL for f in f_on)
              and report(f_on, "local", [], True, stream=open(os.devnull, "w")) == 1,
              detail=str([(f["raw"], f["class"]) for f in f_on]))
        check("19д. и раскладочные дефекты корневых ссылок не ослабли: "
              "вложенный путь под каталогом страницы остаётся дефектом",
              any(f["class"] in DEFECT_CLASSES for f in check_local_page(
                  f2idx, f2, "/guide-demo/", "assets/guide-demo")[0]))
        сводка_ts = summarize(f_ts)[0]
        check("19е. цифра непокрытия видна отдельным классом в counts",
              сводка_ts.get(NOLOCAL) == 2 and not any(
                  k in DEFECT_CLASSES for k in сводка_ts),
              detail=str(сводка_ts))
    finally:
        # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
        pass

    ok = sum(1 for _n, good, _d in cases if good)
    for name, good, detail in cases:
        mark = "ok  " if good else "FAIL"
        print(f"  [{mark}] {name}" + (f"\n         {detail}" if not good and detail else ""))
    print(f"селфтест image_health: {ok}/{len(cases)} прошло")
    return 0 if ok == len(cases) else 1


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="image_health.py",
        description="Проверка ссылок на изображения: живые страницы (--live) "
                    "и каталог статьи до заливки (--local).")
    ap.add_argument("targets", nargs="*",
                    help="URL, файл со списком URL (--live) либо каталог статьи "
                         "или index.html (--local)")
    ap.add_argument("--live", action="store_true", help="режим живых страниц")
    ap.add_argument("--local", action="store_true", help="режим локального каталога")
    ap.add_argument("--sitemap", default=None, help="--live: взять URL из sitemap")
    ap.add_argument("--filter", default=None, help="--live: regex-фильтр по URL")
    ap.add_argument("--limit", type=int, default=0, help="--live: не больше N страниц")
    ap.add_argument("--page-url", default=None,
                    help="--local: путь, по которому страница отдаётся (/<slug>/); "
                         "по умолчанию берётся из canonical/og:url самой страницы")
    ap.add_argument("--assets-remote", default=None,
                    help="--local: remote-каталог картинок ОТ КОРНЯ САЙТА - ровно то "
                         "же значение и та же семантика, что у движка публикации "
                         "(ведущий слэш необязателен: assets/<slug> == /assets/<slug>). "
                         "Без флага - каталожная раскладка <каталог страницы>/assets/. "
                         "Каталог картинок ОТНОСИТЕЛЬНО страницы задаётся явной "
                         "формой с ./ или ../ (напр. ./assets)")
    ap.add_argument("--base-url", default=None,
                    help="схема+домен сайта (для --local нужен только с --check-outside); "
                         "по умолчанию domain из конфига")
    ap.add_argument("--check-outside", action="store_true",
                    help="--local: общие файлы сайта вне статьи проверить по HTTP")
    ap.add_argument("--require-local-files", action="store_true",
                    dest="require_local_files",
                    help="--local: требовать локальный файл и под СВОИ КОРНЕВЫЕ "
                         "ссылки (та же семантика и то же имя, что у флага "
                         "article_gates.py). По умолчанию выключено: на заливке "
                         "«только страница» картинки уже живут на проде, и "
                         "«файла нет рядом» здесь ничего не доказывает - факт "
                         "файла судит предполёт ftp_publish. Без флага цифра "
                         "печатается в шапке, но exit не роняет")
    ap.add_argument("--strict-external", action="store_true",
                    help="--live: считать дефектом и картинки с чужих доменов")
    ap.add_argument("--retries", type=int, default=2,
                    help="--live: повторов по ссылке, на которой транспорт "
                         "промолчал (молчание - не улика, дефект только с кодом "
                         "ответа сервера)")
    ap.add_argument("--retry-pause", type=float, default=1.5, dest="retry_pause",
                    help="--live: пауза между повторами, сек")
    ap.add_argument("--workers", type=int, default=12, help="параллельных запросов")
    ap.add_argument("--timeout", type=int, default=20, help="таймаут запроса, сек")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="машинный вывод в stdout")
    ap.add_argument("--config", default=None,
                    help="путь к seo-publish.json (дефолт ~/.config/)")
    ap.add_argument("--selftest", action="store_true",
                    help="офлайн-селфтест без сети")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    cfg = load_config(args.config)
    base_url = (args.base_url or cfg.get("domain") or "").rstrip("/")

    if args.live and args.local:
        die("--live и --local вместе не работают: раскладка проверяется по-разному")
    if not args.live and not args.local:
        # режим выводится из цели: путь на диске = local, иначе live
        if args.targets and all(os.path.exists(t) for t in args.targets) \
                and any(os.path.isdir(t) or t.endswith(".html") for t in args.targets):
            args.local = True
        else:
            args.live = True

    http = Http(timeout=args.timeout, workers=args.workers)
    findings = []
    header = []

    if args.live:
        urls = targets_from_args(args.targets, http, args.sitemap, args.filter, args.limit)
        if not urls:
            die("нет ни одной цели: передай URL, файл со списком или --sitemap")
        header.append(f"[{TOOL}] режим live, страниц на проверку: {len(urls)}")
        fetched = 0
        for u in urls:
            page_findings, final = check_live_page(
                u, http, args.strict_external,
                попыток=max(1, args.retries), пауза=max(0.0, args.retry_pause))
            if not any(f["class"] == D_PAGE for f in page_findings):
                fetched += 1
            findings.extend(page_findings)
            if not args.as_json and len(urls) > 1:
                bad = len([f for f in page_findings if f["class"] in DEFECT_CLASSES])
                тёмных = len([f for f in page_findings if f["class"] == UNCHECKED])
                log(f"  {final}: ссылок {len(page_findings)}, дефектов {bad}"
                    + (f", проверить нечем {тёмных}" if тёмных else ""))
        if fetched == 0:
            die("ни одна страница не скачалась - проверять нечего")
    else:
        if not args.targets:
            die("нет цели: передай каталог статьи или путь к index.html")
        header.append(f"[{TOOL}] режим local, целей: {len(args.targets)}")
        for t in args.targets:
            t = os.path.expanduser(t)
            if os.path.isdir(t):
                index_html = os.path.join(t, "index.html")
                article_dir = t
                if not os.path.isfile(index_html):
                    candidates = [n for n in sorted(os.listdir(t)) if n.endswith(".html")
                                  and not n.endswith(".bak")]
                    if len(candidates) != 1:
                        die(f"в каталоге нет index.html и однозначной страницы: {t}")
                    index_html = os.path.join(t, candidates[0])
            elif os.path.isfile(t):
                index_html = t
                article_dir = os.path.dirname(os.path.abspath(t))
            else:
                die(f"нет такого пути: {t}")
            page_findings, page_url = check_local_page(
                index_html, article_dir, args.page_url or "", args.assets_remote,
                base_url=base_url, http=http, check_outside=args.check_outside,
                require_local_files=bool(args.require_local_files))
            _maps, assets_prefix, page_dir = build_layout(
                article_dir, page_url or "/", args.assets_remote)
            header.append(f"  страница {index_html}")
            header.append(f"  адрес на проде: {page_url or '(не выведен)'}")
            header.append(f"  картинки статьи на проде: {assets_prefix}"
                          f"  (локально {os.path.join(article_dir, 'assets')})")
            header.append(f"  --assets-remote прочитан как: "
                          f"{assets_remote_mode(args.assets_remote)}")
            header.append("  свои корневые ссылки без локального файла: "
                          + ("СУДИМ (--require-local-files)"
                             if args.require_local_files
                             else "считаем цифрой, exit не роняем "
                                  "(факт файла судит предполёт ftp_publish)"))
            findings.extend(page_findings)

    return report(findings, "live" if args.live else "local", header, args.as_json)


if __name__ == "__main__":
    sys.exit(main())
