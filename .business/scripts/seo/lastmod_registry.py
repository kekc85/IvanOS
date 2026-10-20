#!/usr/bin/env python3
"""Реестр содержимого страниц: честный lastmod для карты сайта.

ЗАЧЕМ (дефект приёмки волны 3, по решению автора).
sitemap_rebuild.py брал lastmod из ФАЙЛА: позднее из dateModified в разметке и
заголовка Last-Modified прода. Заголовок двигает ЛЮБАЯ перезаливка - волна CSS,
передеплой того же байт-в-байт содержимого, правка разметки. В итоге по решению автора в живой
карте оказалось 215 страниц с датой 2026-08-04, хотя ТЕКСТ у большинства не менялся
с этой редакции-по решению автора (у главной sha живого текста совпадает со слепком, а lastmod уехал).

Это ровно тот антипаттерн, который в бенчмарке подписан как «никогда не меняйте
только дату» (Ahrefs, зафиксировано в ресёрч-portals-2026-08-04.md): дата в
карте, за которой нет правки содержания, обесценивает даты всего сайта.

ЧТО ДЕЛАЕМ. Дату свежести определяет не файл, а СОДЕРЖАНИЕ. Реестр
content-sha-registry.json хранит на каждый URL пару {sha256_content, lastmod}:
  • sha живого содержимого совпал с реестром -> lastmod берём из реестра (сколько бы
    раз файл ни перезаливали);
  • sha разошёлся -> содержание правда изменилось, lastmod = сегодня, реестр обновлён;
  • URL в реестре нет -> новая страница, lastmod = сегодня, запись заводится.

ЧТО СЧИТАЕМ «СОДЕРЖАНИЕМ» (нормализация, функция content_sha).
Хэшируется ВИДИМЫЙ ТЕКСТ страницы плюс title и meta description. Из расчёта
выброшены:
  • <script> (вместе с JSON-LD: там сидит dateModified - иначе подъём даты сам себя
    объявлял бы содержательной правкой, замкнутый круг),
  • <style> (волна CSS - техническая по определению плана),
  • <noscript>, HTML-комментарии,
  • <time> и <span class="updated"> (видимая строка «Обновлено: 3 августа 2026»),
  • все теги и атрибуты (class, alt, data-*), различия в пробелах и переводах строк.
Так sha меняется на переписанном H2, новом абзаце, другом title - и НЕ меняется на
перевёрстке, новом CSS, правке разметки, подъёме самой даты.

Честная граница нормализации: замена картинки без правки текста sha не сдвинет
(теги выброшены). Это осознанный перекос в сторону «лучше не поднять дату, чем
поднять её впустую» - ровно то, за что бенчмарк наказывает.

🔴 РЕЕСТР - РАЗДЕЛЯЕМЫЙ ФАЙЛ, ПИСАТЬ ТОЛЬКО ПОД КЛЕЙМОМ.
content-sha-registry.json стоит в одном ряду с sitemap.xml, blog.html, rss.xml и
llms.txt: его пишет не один хозяин, а любая волна - статьи, фиксы, приёмки, и
ОТДЕЛЬНО sitemap_rebuild.py, который дёргает resolve() и сохраняет реестр ВНУТРИ
своего прогона (глава про lastmod). Из-за этого «я же только карту пересобрал»
на деле означает «я переписал реестр».

Прецедент, ради которого правило стало кодом (приёмка слоя ответов по решению автора):
карту и реестр пересобрали в 08:36, а в 08:43 та же волна дописала абзацы с
ссылками в 14 страниц-доноров. Реестр остался со старыми sha - следующая
пересборка увидела бы «содержание изменилось» и подняла lastmod 14 страницам,
хотя правка была технической. Клейма на реестре не было, конфликт никто не заметил.

Как правильно (любой вызывающий скрипт):
    with lastmod_registry.claimed("имя-волны", agent="кто"):
        reg = lastmod_registry.load_registry()
        ...
        lastmod_registry.save_registry(reg)
или снаружи (волну объявляем ОБОИМ шагам, иначе писать нечем доказать владение):
    export SEO_WAVE="имя-волны"
    python3 _rebuild/claim_gate.py claim   <путь к реестру> "$SEO_WAVE" --agent <кто>
    ... прогон ...
    python3 _rebuild/claim_gate.py release <путь к реестру> "$SEO_WAVE" --agent <кто>

save_registry() без активного клейма ПАДАЕТ (RuntimeError) и печатает готовые
команды. Осознанный обход - только SEO_REGISTRY_CLAIM_WAIVER='причина', она
печатается в лог прогона. Тот, кто клеймит реестр, обязан клеймить и карту:
одна волна двигает их вместе.

🔴 ПИСАТЬ МОЖЕТ ТОЛЬКО ВОЛНА-ВЛАДЕЛЕЦ (скептик-E, E1, по решению автора). Клейм есть -
это ещё не «клейм мой». Раньше запись проходила под ЛЮБЫМ живым клеймом, в том
числе чужим: волна «чужая-волна» держит реестр, `claim_gate check` чужой волне
даёт exit 2 и стопит заливку, а save_registry в ту же секунду пишет файл. Теперь
писатель обязан объявить себя - аргументом wave=, контекстом claimed() или
переменной SEO_WAVE; чужая волна и необъявленный писатель получают RuntimeError.
Ряд-противоречие и дубль рядов на один канон-ключ останавливают запись
безусловно, WAIVER их не снимает (E2/E3).

Запуск:
  python3 lastmod_registry.py --seed        первичное наполнение честными датами
  python3 lastmod_registry.py --seed --dry  то же, но без записи файла
  python3 lastmod_registry.py --show URL    что лежит в реестре по адресу
  python3 lastmod_registry.py --selftest    проверка клейм-гейта (позитив+негатив)

ПОЛЕ datePublished (Р.1а, ревизионный контур, по решению автора).
Запись реестра умеет нести ВТОРУЮ дату - datePublished (когда страница впервые
вышла), отдельно от lastmod (когда в последний раз менялось содержание). Нужна
для revision_queue.py: возраст страницы с публикации - один из входов очереди
ревизий. Источник по приоритету:
  1. rost-статья (URL со статусом «опубликовано» в state.json темы[]) и поле
     опубликовано непустое -> дата ОТТУДА (это дата решения движка, самая
     честная);
  2. иначе - JSON-LD datePublished из локального HTML-слепка (первый узел
     @graph с этим полем), с проверкой правдоподобия (не раньше
     MIN_PLAUSIBLE_DATE_PUBLISHED - на живом корпусе по решению автора нашлись 2 страницы
     с datePublished=2026-06-26 в разметке при lastmod 08.2026, то есть
     заведомый мусор/шаблонная дата, а сайт живёт с конца июля 2026 - такие
     значения ОТБРАСЫВАЕМ, а не пишем);
  3. ни того, ни другого -> поле НЕ проставляется, URL уходит в отчёт как
     пробел (не выдумываем).
Запуск:
  python3 lastmod_registry.py --backfill-datepublished --dry
      прогон-разведка без записи, полный отчёт (сколько откуда, что пропущено)
  SEO_WAVE=<волна> SEO_AGENT=<агент> python3 lastmod_registry.py \\
      --backfill-datepublished
      боевая запись под клеймом (внутри - claimed(), claim+release одним прогоном)
  python3 lastmod_registry.py --backfill-datepublished --corpus <путь>
      явно указать каталог HTML-слепка вместо автоподбора свежайшего
"""
import argparse
import datetime
import hashlib
import html as htmllib
import json
import os
import re
import subprocess
import sys
import urllib.parse

TOOLS = os.path.expanduser("~/.claude/skills/_shared/tools")
sys.path.insert(0, TOOLS)

SEO_DIR = os.path.expanduser(".business/growth/seo")
REGISTRY = os.path.join(SEO_DIR, "content-sha-registry.json")

# База честных дат: карта, собранная по решению автора ДО технических волн по решению автора
BASE_SITEMAP = os.path.join(SEO_DIR, "phase8-raw", "sitemap.xml")
BASE_PAGES = os.path.join(SEO_DIR, "phase8-raw", "pages")
BASE_MAP = os.path.join(SEO_DIR, "phase8-raw", "url_slug_map.tsv")
# Слепок по решению автора - для разбора «содержание разошлось, а чем именно»
SNAP_MANIFEST = os.path.join(SEO_DIR, "corpus-2026-08-04", "_manifest-2026-08-04.tsv")

MSK = datetime.timezone(datetime.timedelta(hours=3))

COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.S | re.I)
NOSCRIPT_RE = re.compile(r"<noscript\b[^>]*>.*?</noscript>", re.S | re.I)
TIME_RE = re.compile(r"<time\b[^>]*>.*?</time>", re.S | re.I)
UPDATED_RE = re.compile(r'<span\b[^>]*class="[^"]*\bupdated\b[^"]*"[^>]*>.*?</span>', re.S | re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
DESC_RE = re.compile(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', re.I)
DESC_RE2 = re.compile(r'<meta[^>]+content="([^"]*)"[^>]+name="description"', re.I)
TAG_RE = re.compile(r"<[^>]+>")

# Типографика к одному виду. Волна замены длинных тире на дефис (канон формата: «—»
# и «–» - маркер ИИ), сборка NBSP по зонам крошек, единый вид кавычек и многоточия -
# это МЕХАНИЧЕСКИЕ волны того же класса, что пробелы и вёрстка: читателю нового смысла
# не прибавилось. Замер на живом корпусе по решению автора: свёртка типографики возвращает в разряд
# «содержание не менялось» 8 страниц из 248 (41 -> 49), включая главную, у которой весь
# диф со слепком по решению автора - три длинных тире. Считать такое содержательной правкой значит
# заново нарисовать ту же ложную свежесть, из-за которой реестр и заводится.
FOLD = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
    "―": "-", "−": "-", "­": "",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    "​": "", "‌": "", "‍": "", "﻿": "",
    "«": '"', "»": '"', "“": '"', "”": '"', "„": '"',
    "‟": '"', "″": '"', "‘": "'", "’": "'", "‚": "'",
    "′": "'", "…": "...",
}
FOLD_TABLE = str.maketrans(FOLD)


def _flat(s):
    return re.sub(r"\s+", " ", htmllib.unescape(s or "").translate(FOLD_TABLE)).strip()


def content_text(raw):
    """HTML -> нормализованный текст, по которому считается sha (см. шапку)."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    t = TITLE_RE.search(raw)
    d = DESC_RE.search(raw) or DESC_RE2.search(raw)
    head_bits = [_flat(t.group(1)) if t else "", _flat(d.group(1)) if d else ""]

    body = raw
    for rx in (COMMENT_RE, SCRIPT_RE, STYLE_RE, NOSCRIPT_RE, UPDATED_RE, TIME_RE):
        body = rx.sub(" ", body)
    m = re.search(r"<body[^>]*>", body, re.I)
    if m:
        body = body[m.end():]
    body = TAG_RE.sub(" ", body)
    body = _flat(body)
    return "\n".join(["T:" + head_bits[0], "D:" + head_bits[1], "B:" + body])


def content_sha(raw):
    """sha256 нормализованного содержимого страницы (стабилен к перезаливке)."""
    return hashlib.sha256(content_text(raw).encode("utf-8")).hexdigest()


def today_msk():
    return datetime.datetime.now(MSK).strftime("%Y-%m-%d")


def load_registry(path=REGISTRY):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CLAIM_GATE = os.path.expanduser(".business/growth/seo/_rebuild/claim_gate.py")


# 🔴 КТО Я. Мьютекс без сравнения владельца мьютексом не является (скептик-E,
# E1, по решению автора): require_claim пропускал запись, если реестр держала ЛЮБАЯ
# волна, в том числе ЧУЖАЯ. Живая проба: волна «чужая-волна» захватывает реестр,
# `claim_gate check` чужой волне печатает «ЗАНЯТО» и exit 2 - а save_registry в
# ту же секунду спокойно пишет файл. Гейт стоял на дверях заливки и отсутствовал
# на дверях записи.
#
# Чтобы сравнивать владельца, писатель обязан ОБЪЯВИТЬ, кто он - ПАРОЙ
# «волна + агент», а не одной волной (скептик-G, M9b: клейм с именем агента
# пробивался знанием одного имени волны). Три источника по убыванию силы:
#   1) явный аргумент  save_registry(reg, wave="моя-волна", agent="кто")
#   2) контекст        with lastmod_registry.claimed("моя-волна", agent="кто"):
#   3) окружение       SEO_WAVE='моя-волна' SEO_AGENT='кто' python3 script.py
# Ничего не объявлено, а реестр кем-то захвачен -> запись ОТБИВАЕТСЯ: доказать
# владение нечем, значит по умолчанию волна чужая. Имя SEO_WAVE в движке уже
# каноническое - sitemap_rebuild.py читает его тем же способом.
# Агента можно не называть ровно в двух случаях: клейм взят БЕЗ имени агента
# (claim_gate по умолчанию пишет пустое поле) либо клейм взят этим же процессом
# через claimed() - там имя уже лежит в _MY_CLAIMS.
_MY_CLAIMS = {}          # канон-ключ -> список (волна, агент), стек контекстов


def _cg():
    """Единственная точка проверки ряда - модуль claim_gate (см. Е-E2/E3)."""
    sys.path.insert(0, os.path.dirname(CLAIM_GATE))
    import claim_gate as cg
    return cg


def agent_id(tool):
    """Личность писателя = ПРОЦЕСС, а не инструмент (Т-1б, по решению автора).

    Раньше вызывающие подставляли сюда имя файла: agent="sitemap_rebuild",
    "scoped_lastmod_resolve", "skeptik9". Два честных прогона одного инструмента
    в одной волне приходили под ОДНИМ именем - гейт видел одного писателя,
    пропускал второго, и правка первого пропадала молча. Определение живёт в
    claim_gate (он и есть гейт), здесь только переиздание, чтобы писателям
    реестра не приходилось тащить второй импорт."""
    return _cg().agent_id(tool)


def registry_state(path=REGISTRY):
    """Состояние ресурса ОДНИМ ответом: {key, holder, problem}.

    Через неё обязаны ходить ВСЕ входы модуля - claim_holder, require_claim,
    claimed. Раньше `inconsistent()` знал только claim/release/check самого
    гейта, поэтому на противоречивом ряду заливка стояла, а ЗАПИСЬ В РЕЕСТР
    шла (скептик-E, E2). Теперь причина остановки одна и та же на всех дверях.
    """
    try:
        cg = _cg()
        key = cg.canon_path(path)
        data = cg._load(cg._registry_path())
    except Exception as exc:
        return {"key": str(path), "holder": None,
                "problem": f"реестр захвата нечитаем: {exc}"}
    rows = cg._rows_for(data, key)
    problem = cg.row_problem(rows, key)
    holder = None
    for row in reversed(rows):
        if row.get("status") == "claimed":
            holder = (row.get("wave"), row.get("agent"))
            break
    return {"key": key, "holder": holder, "problem": problem}


def claim_holder(path=REGISTRY, strict=False):
    """Кто СЕЙЧАС держит реестр по claim_gate: (волна, агент) или None.

    🔴 КЛЮЧ ОДИН И ОБЩИЙ С ГЕЙТОМ (Д-D1б, по решению автора). Раньше здесь сверялось
    ИМЯ ФАЙЛА, а `claim_gate check` сверял путь целиком - и две точки входа
    давали противоположные ответы про один и тот же файл: check по абсолютному
    пути к content-sha-registry.json печатал «свободен (released)», а этот
    claim_holder в ту же секунду - «держит волна d2-title-drift». Сверка по
    имени файла к тому же роняла бы вместе `blog.html` сайта и одноимённый
    локальный файл. Теперь обе точки зовут одну функцию `claim_gate.canon_path`.

    strict=True - поднять исключение на противоречивом ряду или дубле рядов
    (так зовут все ПИШУЩИЕ входы). По умолчанию функция остаётся справкой «кто
    держит» и на битом ряду громко ругается в stderr, но не падает.
    """
    st = registry_state(path)
    if st["problem"]:
        if strict:
            raise RuntimeError(f"реестр захвата противоречив по {st['key']}: {st['problem']}")
        print(f"🔴 {st['key']}: {st['problem']}", file=sys.stderr)
    return st["holder"]


def _declared_identity(key, wave=None, agent=None):
    """Кем себя объявил писатель: (волна, агент). Агент None = НЕ объявлен.

    🔴 ПОЛОВИНА ИМЕНИ - НЕ ИМЯ (скептик-G, M9b, по решению автора). Прежняя версия
    подставляла вместо необъявленного агента строку-заглушку «lastmod_registry»
    на ветке явного аргумента и None на ветке окружения. Из-за None сравнение
    агентов в require_claim просто пропускалось: реестр держит волна «G-alpha»
    агентом «agent-1», а любой посторонний процесс, который знает ТОЛЬКО имя
    волны (`SEO_WAVE=G-alpha`), спокойно писал файл. Мьютекс, который пускает
    неизвестного агента под именем чужой волны, мьютексом не является: имя волны
    в движке не секрет, оно лежит в логах и в реестре захвата.
    Теперь агент возвращается КАК ЕСТЬ (None, если не объявлен), а решение
    «пускать или нет» принимает require_claim: под клеймом с ИМЕНЕМ агента
    необъявленный писатель отбивается.
    Свой же контекст остаётся достаточным доказательством: если этот процесс
    сам взял клейм через `claimed()`, агент известен из стека и объявлять его
    вторично аргументом не нужно.
    """
    stack = _MY_CLAIMS.get(key) or []
    if wave:
        if agent:
            return wave, agent
        for held_wave, held_agent in reversed(stack):
            if held_wave == wave:            # клейм взят этим же процессом
                return wave, held_agent
        return wave, os.environ.get("SEO_AGENT") or None
    if stack:
        return stack[-1]
    env_wave = os.environ.get("SEO_WAVE")
    if env_wave:
        return env_wave, agent or os.environ.get("SEO_AGENT") or None
    return None, None


class claimed:
    """Контекст «реестр захвачен волной»: claim на входе, release на выходе.

        with lr.claimed("моя-волна", agent="я"):
            ...  reg = lr.load_registry(); lr.resolve(...); lr.save_registry(reg)

    Внутри контекста писателю больше ничего объявлять не нужно: контекст сам
    кладёт (волна, агент) в _MY_CLAIMS, и save_registry доказывает владение им.
    """

    def __init__(self, wave, agent=None, path=REGISTRY):
        # Дефолт БОЛЬШЕ НЕ ИМЯ МОДУЛЯ (Т-1б): раньше было agent="lastmod_registry",
        # и всякий, кто не назвался, приходил под одной и той же строкой - два
        # честных прогона сливались в одного писателя. Теперь безымянный вход
        # получает личность процесса.
        self.wave, self.agent, self.path = wave, agent or agent_id("lastmod_registry"), path
        self.mine = False
        self.key = None

    def __enter__(self):
        st = registry_state(self.path)
        self.key = st["key"]
        if st["problem"]:
            # ровно тот же стоп-сигнал, что у claim_gate check: ряд врёт
            raise RuntimeError(
                f"claimed('{self.wave}') не входит: {st['problem']}\n"
                f"  починить: python3 {CLAIM_GATE} release {self.path} <волна> "
                f"--reason 'ручной release без переворота статуса'")
        held = st["holder"]
        if held and held[0] == self.wave:
            # 🔴 ВТОРАЯ ДВЕРЬ ТОГО ЖЕ КЛАССА (Т-1, по решению автора). claim_gate теперь
            # отбивает захват чужим агентом той же волны - но сюда этот путь и не
            # заходил: при совпадении имени волны контекст ПОДСАЖИВАЛСЯ на чужой
            # клейм, записывал в _MY_CLAIMS имя ВЛАДЕЛЬЦА (`held[1] or self.agent`)
            # и дальше require_claim сравнивал агента сам с собой. Живая проба до
            # правки: волна W агент agent-A держит реестр, вторая сессия той же
            # волны с agent-B входит в claimed() и пишет файл - «запись ПРОШЛА
            # чужим агентом». Гард в одной ветке гардом не является.
            # Анонимный клейм (агента не назвали вовсе) остаётся проходимым - это
            # уже описанная граница G-M9b, там сравнивать нечего.
            if held[1] and self.agent and held[1] != self.agent:
                raise RuntimeError(
                    f"ЧУЖОЙ АГЕНТ: {os.path.basename(self.path)} держит волна "
                    f"«{held[0]}» агентом «{held[1]}», в claimed() входит агент "
                    f"«{self.agent}» той же волны - вход отбит (одна волна, два "
                    f"писателя = гонка).\n"
                    f"  дождаться release владельца либо войти его именем: "
                    f"with lastmod_registry.claimed('{held[0]}', agent='{held[1]}')")
            _MY_CLAIMS.setdefault(self.key, []).append((self.wave, held[1] or self.agent))
            return self
        # Проигравший гонку обязан получить ту же ОСМЫСЛЕННУЮ ошибку, что и
        # любой другой отказ гейта (скептик-G, M6'): раньше здесь стоял
        # check=True, и параллельная волна падала голым CalledProcessError -
        # причина «ЗАНЯТО другой волной» оставалась только в stderr подпроцесса,
        # а вызывающий код видел код возврата без текста.
        r = subprocess.run([sys.executable, CLAIM_GATE, "claim", self.path, self.wave,
                            "--agent", self.agent], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"claimed('{self.wave}') не входит: клейм не взят "
                f"(claim_gate exit {r.returncode})\n"
                + (r.stdout + r.stderr).strip())
        if r.stdout:
            print(r.stdout.rstrip())
        self.mine = True
        _MY_CLAIMS.setdefault(self.key, []).append((self.wave, self.agent))
        return self

    def __exit__(self, *exc):
        stack = _MY_CLAIMS.get(self.key) or []
        if stack:
            stack.pop()
        if self.mine:
            subprocess.run([sys.executable, CLAIM_GATE, "release", self.path, self.wave,
                            "--agent", self.agent], check=False)
        return False


def save_registry(reg, path=REGISTRY, wave=None, agent=None):
    """Запись реестра. КОД-ГЕЙТ: писать может ТОЛЬКО волна-владелец.

    Почему гейт, а не памятка. content-sha-registry.json - разделяемый файл того
    же класса, что sitemap.xml: его пишет и волна статей, и sitemap_rebuild.py
    (внутри своего прогона, попутно), и любой post_deploy. Приёмка по решению автора нашла
    ровно то, чего и ждали от неклеймленной записи: карту пересобрали в 08:36,
    14 страниц правили в 08:43, реестр остался со старыми sha - следующая
    пересборка подняла бы lastmod у 14 страниц без единой правки содержания.
    Правило «писать реестр только под claim» жило промптом и не сработало,
    поэтому теперь оно живёт здесь.

    Скептик-E (по решению автора) добрал вторую половину: мало проверить, что клейм ЕСТЬ,
    надо проверить, что он МОЙ. Отсюда wave/agent - см. блок «КТО Я» выше.
    """
    require_claim(path, wave=wave, agent=agent)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def require_claim(path=REGISTRY, wave=None, agent=None):
    """Тот же гейт для тех, кто пишет реестр СВОИМ json.dump, а не save_registry.

    Такие писатели в движке есть (skeptik*/post_deploy*.py, tw-out/merge_content_sha.py).
    Им достаточно одной строки в начале записи:
        lastmod_registry.require_claim(wave="моя-волна")
    либо запуска под окружением SEO_WAVE='моя-волна'.

    Порядок отказов (сверху вниз, первый сработавший побеждает):
      1. ряд реестра захвата противоречив или на ключ приходится дубль рядов ->
         СТОП безусловно, WAIVER не спасает: неизвестно, занят ресурс или нет;
      2. реестр держит ДРУГАЯ волна -> СТОП;
      3. реестр кем-то держится, а писатель себя не объявил -> СТОП (доказать
         владение нечем, по умолчанию волна чужая);
      4. клейм держит ИМЕНОВАННЫЙ агент, а писатель назвал только волну -> СТОП
         (скептик-G, M9b: имя волны не секрет, владения оно не доказывает);
      5. та же волна, но ДРУГОЙ агент -> СТОП (одна волна, два писателя = гонка);
      6. клейма нет вовсе -> СТОП, снимается осознанным SEO_REGISTRY_CLAIM_WAIVER.
    """
    st = registry_state(path)
    key, held, problem = st["key"], st["holder"], st["problem"]
    if problem:
        raise RuntimeError(
            f"реестр {os.path.basename(path)} НЕ пишется: {problem}\n"
            f"  посмотреть: python3 {CLAIM_GATE} audit\n"
            f"  починить:   python3 {CLAIM_GATE} release {path} <волна> "
            f"--reason 'ручной release без переворота статуса'\n"
            f"  дубли:      python3 {CLAIM_GATE} dedupe --apply")
    my_wave, my_agent = _declared_identity(key, wave, agent)
    if held:
        if not my_wave:
            raise RuntimeError(
                f"реестр {os.path.basename(path)} держит волна «{held[0]}» "
                f"(агент {held[1]}), а пишущий себя НЕ ОБЪЯВИЛ - запись отбита.\n"
                f"  объявить в коде:  lastmod_registry.save_registry(reg, "
                f"wave='{held[0]}', agent='<кто>')\n"
                f"  или контекстом:   with lastmod_registry.claimed('<волна>', "
                f"agent='<кто>'): ...\n"
                f"  или окружением:   SEO_WAVE='<волна>' python3 <скрипт>")
        if my_wave != held[0]:
            raise RuntimeError(
                f"ЧУЖОЙ КЛЕЙМ: реестр {os.path.basename(path)} держит волна "
                f"«{held[0]}» (агент {held[1]}), пишет волна «{my_wave}» - "
                f"запись отбита.\n"
                f"  дождаться освобождения либо: python3 {CLAIM_GATE} check "
                f"{path} {my_wave}")
        if held[1] and not my_agent:
            raise RuntimeError(
                f"АГЕНТ НЕ ОБЪЯВЛЕН: реестр {os.path.basename(path)} держит волна "
                f"«{held[0]}» ИМЕНОВАННЫМ агентом «{held[1]}», а пишущий назвал "
                f"только волну - запись отбита. Имя волны не доказывает владение: "
                f"оно лежит в логах и в реестре захвата, назвать его может кто "
                f"угодно.\n"
                f"  объявить пару:    lastmod_registry.save_registry(reg, "
                f"wave='{held[0]}', agent='{held[1]}')\n"
                f"  или окружением:   SEO_WAVE='{held[0]}' SEO_AGENT='{held[1]}' "
                f"python3 <скрипт>\n"
                f"  или контекстом:   with lastmod_registry.claimed('{held[0]}', "
                f"agent='{held[1]}'): ...")
        if my_agent and held[1] and my_agent != held[1]:
            raise RuntimeError(
                f"ЧУЖОЙ АГЕНТ: реестр {os.path.basename(path)} держит волна "
                f"«{held[0]}» агентом «{held[1]}», пишет агент «{my_agent}» той "
                f"же волны - запись отбита (одна волна, два агента = гонка).")
        print(f"claim ok: реестр держит МОЯ волна «{held[0]}» (агент {held[1]})")
        return True
    waiver = os.environ.get("SEO_REGISTRY_CLAIM_WAIVER")
    if not waiver:
        raise RuntimeError(
            f"реестр {os.path.basename(path)} пишется БЕЗ клейма.\n"
            f"  захватить:  python3 {CLAIM_GATE} claim {path} <волна> --agent <кто>\n"
            f"  отпустить:  python3 {CLAIM_GATE} release {path} <волна> --agent <кто>\n"
            f"  или в коде: with lastmod_registry.claimed('<волна>'): ...\n"
            f"  осознанный обход (пишется в лог): "
            f"SEO_REGISTRY_CLAIM_WAIVER='причина' <команда>")
    print(f"⚠️  реестр пишется в обход клейма, причина: {waiver}")
    return True


def resolve(reg, url, raw, today=None):
    """Решить lastmod для одного URL по живому HTML.

    Возвращает (lastmod, status, sha), status - одно из:
      'same'    содержание не менялось, дата взята из реестра
      'changed' содержание разошлось с реестром, дата = сегодня
      'new'     адреса в реестре не было, дата = сегодня
    Реестр меняется НА МЕСТЕ (вызывающий сам решает, когда сохранить).
    """
    today = today or today_msk()
    sha = content_sha(raw)
    rec = reg.get(url)
    if rec and rec.get("sha256_content") == sha and rec.get("lastmod"):
        return rec["lastmod"], "same", sha
    status = "changed" if rec else "new"
    new_rec = {
        "sha256_content": sha,
        "lastmod": today,
        "source": status,
        "updated_at": today,
    }
    # datePublished переживает 'changed': правка содержания не отменяет дату
    # первой публикации. Раньше запись полностью пересобиралась заново - поле,
    # проставленное backfill-datepublished, молча терялось на первой же
    # содержательной правке страницы после него.
    if rec and rec.get("datePublished"):
        new_rec["datePublished"] = rec["datePublished"]
    reg[url] = new_rec
    return today, status, sha


# ------------------------------------------------------------- datePublished
STATE_JSON = os.path.join(SEO_DIR, "state.json")
LDJSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Сайт живёт с конца июля 2026 (честный минимум lastmod в реестре на момент этой редакции -
# 2026-07-23). Дата раньше этого порога в JSON-LD - заведомый мусор/шаблонное
# значение, не настоящая дата первой публикации (живая проба по решению автора: у
# guide-nejrofoto и guide-gugel datePublished=2026-06-26 в разметке при
# lastmod 2026-08-02/2026-08-08). Такие значения ОТБРАСЫВАЕМ, а не пишем -
# лучше пробел в отчёте, чем выдуманная дата.
MIN_PLAUSIBLE_DATE_PUBLISHED = "2026-07-15"


def extract_date_published(raw):
    """datePublished из первого узла JSON-LD, где оно есть, или None.

    Разбирает все <script type="application/ld+json"> блоки страницы,
    заходит в @graph (или берёт сам объект, если @graph нет), возвращает
    ПЕРВОЕ найденное значение datePublished, обрезанное до даты YYYY-MM-DD
    (в разметке оно может прийти как чистая дата или ISO-datetime).
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    for block in LDJSON_RE.findall(raw):
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            nodes = data.get("@graph", [data])
        elif isinstance(data, list):
            nodes = data
        else:
            continue
        for node in nodes:
            if not isinstance(node, dict):
                continue
            val = node.get("datePublished")
            if not val:
                continue
            val = str(val)[:10]
            if ISO_DATE_RE.match(val):
                return val
    return None


def _plausible_date_published(d):
    return bool(d) and ISO_DATE_RE.match(d) and d >= MIN_PLAUSIBLE_DATE_PUBLISHED


def _rost_published_map(path=STATE_JSON):
    """url -> дата 'опубликовано' для тем со статусом 'опубликовано' в state.json.

    Значение может быть None (7 статей были опубликованы ДО того, как поле
    завели - живая проба по решению автора) - вызывающий обязан это учесть отдельным
    веткой, а не считать пустую строку/None валидной датой.
    """
    out = {}
    if not os.path.exists(path):
        return out
    data = json.load(open(path, encoding="utf-8"))
    for t in data.get("темы", []):
        if t.get("статус") == "опубликовано" and t.get("url"):
            out[t["url"]] = t.get("опубликовано")
    return out


def _corpus_url_from_filename(fname, domain="<твой-домен>"):
    """Обратное преобразование к build7.py:out_name() (лежит рядом, в
    _rebuild/r4/skeptik7/build7.py): url.replace('https://','').replace('/','__') + '.html'.
    Здесь - тот же контракт задом наперёд, НЕ новое соглашение об именах."""
    if not fname.endswith(".html"):
        return None
    body = fname[:-len(".html")]
    if body.startswith(domain):
        return "https://" + body.replace("__", "/")
    # 🔴 ВТОРАЯ ЖИВАЯ КОНВЕНЦИЯ ИМЁН (по решению автора). Канонный сборщик слепка
    # `corpus_from_mirror.sh` пишет файлы процентным кодированием полного URL
    # (`urllib.parse.quote(url, safe="") + ".html"`), а не по схеме build7.py.
    # Пока декодер знал только одну схему, индекс по такому слепку выходил
    # ПУСТЫМ, и backfill datePublished молча отвечал «нет слепка корпуса» на
    # каждую страницу - при живом слепке в 439 страниц рядом. Следствие ловилось
    # аж на гейте artifacts-post: без datePublished свежая статья считалась
    # легаси и требовала артефакты чужого маршрута. Это не новое соглашение об
    # именах, а признание уже существующего: обе схемы читаются, ни одна не
    # ломается.
    if "%3A%2F%2F" in body or body.startswith("https%3A"):
        try:
            decoded = urllib.parse.unquote(body)
        except (ValueError, AttributeError):
            return None
        if decoded.startswith("https://" + domain) or decoded.startswith("http://" + domain):
            return decoded
    return None


def _corpus_url_index(corpus_dir):
    """url -> путь к HTML-слепку для каталога corpus_dir (плоский, без вложенности)."""
    out = {}
    if not corpus_dir or not os.path.isdir(corpus_dir):
        return out
    for fname in os.listdir(corpus_dir):
        if not fname.endswith(".html"):
            continue
        url = _corpus_url_from_filename(fname)
        if url:
            out[url] = os.path.join(corpus_dir, fname)
    return out


def find_corpus_dir(explicit=None):
    """Свежайший локальный HTML-слепок корпуса (>=100 ДЕКОДИРУЕМЫХ страниц).

    🔴 ЖИВАЯ ПРОБА по решению автора (не гипотеза): пока писался этот backfill, ПАРАЛЛЕЛЬНЫЙ
    агент волны той же сессии как раз снимал свежий слепок в
    _rebuild/r5/corpus-20260812/ (Фаза П.1) - директория БЫЛА, файлов >=100
    БЫЛО, но naming-конвенция там ДРУГАЯ (`slug_index.html`, не
    `<твой-домен>__slug__.html` как у build7.py/skeptik7). Первая версия
    этой функции считала «html-файлов >= 100» и подхватила бы недописанный/
    несовместимый каталог просто по свежести mtime - на выходе 0 декодируемых
    URL и backfill молча ушёл бы в «нет данных» почти по всему корпусу.
    Порог теперь мерит НЕ количество .html-файлов, а количество файлов, которые
    _corpus_url_index() реально умеет превратить в известный URL сайта - так
    каталог с чужой/недописанной раскладкой сам себя исключает, гонки не
    нужно ловить отдельной эвристикой по времени.
    Смотрит ТОЛЬКО в известные дома слепков (не рекурсирует в lead-magnit-work -
    та папка физически лежит внутри growth/seo/ и рекурсия туда была бы
    случайным попаданием в рабочие черновики, не в снятый слепок прода).
    Явный --corpus всегда побеждает.
    """
    if explicit:
        return explicit
    roots = [
        SEO_DIR,
        os.path.join(SEO_DIR, "_rebuild"),
        os.path.join(SEO_DIR, "_rebuild", "r4"),
        os.path.join(SEO_DIR, "_rebuild", "r4", "skeptik7"),
        os.path.join(SEO_DIR, "_rebuild", "r5"),
    ]
    candidates = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if "corpus" not in name.lower() or ".bak" in name.lower():
                continue
            full = os.path.join(root, name)
            if not os.path.isdir(full):
                continue
            n_decoded = len(_corpus_url_index(full))
            if n_decoded >= 100:
                candidates.append((os.path.getmtime(full), full, n_decoded))
    default = os.path.join(SEO_DIR, "_rebuild", "r4", "skeptik7", "live-corpus")
    if not candidates:
        return default if os.path.isdir(default) else None
    candidates.sort()
    return candidates[-1][1]


def backfill_datepublished(dry=False, corpus=None, wave=None, agent=None,
                            force=False, path=REGISTRY, state_path=STATE_JSON):
    """Проставить datePublished во ВСЕХ живых записях реестра (см. правило
    источников в шапке модуля). Пишет только под claim - см. save_registry.

    state_path - подмена state.json для тестов (боевой вызов его не передаёт).
    Возвращает отчёт-словарь (тоже печатает его человекочитаемо в stdout).
    """
    wave = wave or os.environ.get("SEO_WAVE")
    agent = agent or os.environ.get("SEO_AGENT")
    corpus_dir = find_corpus_dir(corpus)
    reg = load_registry(path)
    rost_map = _rost_published_map(state_path)
    corpus_index = _corpus_url_index(corpus_dir)

    report = {
        "corpus_dir": corpus_dir,
        "corpus_html_files": len(corpus_index),
        "from_state_json": [],
        "from_jsonld": [],
        "already_set_skipped": [],
        "retired_skipped": [],
        "no_data": [],          # (url, причина)
        "implausible_rejected": [],  # (url, значение, причина)
    }

    for url in sorted(reg):
        rec = reg[url]
        if rec.get("retired"):
            report["retired_skipped"].append(url)
            continue
        if rec.get("datePublished") and not force:
            report["already_set_skipped"].append(url)
            continue

        candidate, source = None, None
        if url in rost_map and rost_map[url]:
            candidate, source = rost_map[url], "state.json:темы[].опубликовано"
        else:
            fp = corpus_index.get(url)
            if fp:
                try:
                    raw = open(fp, encoding="utf-8", errors="replace").read()
                except OSError:
                    raw = ""
                found = extract_date_published(raw)
                if found:
                    candidate, source = found, f"jsonld:{os.path.basename(corpus_dir or '')}"

        if candidate is None:
            why = ("rost без даты в state.json и без слепка/JSON-LD"
                   if url in rost_map else "нет слепка корпуса или в нём нет datePublished")
            report["no_data"].append((url, why))
            continue
        if not _plausible_date_published(candidate):
            report["implausible_rejected"].append(
                (url, candidate, f"раньше порога {MIN_PLAUSIBLE_DATE_PUBLISHED} - похоже на "
                                  f"мусорное/шаблонное значение в разметке, не проставляем"))
            continue

        rec["datePublished"] = candidate
        rec["datePublished_source"] = source
        if source.startswith("state.json"):
            report["from_state_json"].append((url, candidate))
        else:
            report["from_jsonld"].append((url, candidate))

    print(f"корпус-слепок: {corpus_dir} ({len(corpus_index)} html-файлов)")
    print(f"из state.json (rost, дата решения движка): {len(report['from_state_json'])}")
    print(f"из JSON-LD слепка: {len(report['from_jsonld'])}")
    print(f"уже стояло (пропущено, --force чтобы пересчитать): {len(report['already_set_skipped'])}")
    print(f"retired (пропущено): {len(report['retired_skipped'])}")
    print(f"отброшено как неправдоподобное: {len(report['implausible_rejected'])}")
    for u, v, why in report["implausible_rejected"]:
        print(f"   ⚠️  {u}  datePublished={v}  {why}")
    print(f"без данных вовсе (не проставлено): {len(report['no_data'])}")
    for u, why in report["no_data"]:
        print(f"   -  {u}  ({why})")
    total_written = len(report["from_state_json"]) + len(report["from_jsonld"])
    print(f"итого проставлено в этом прогоне: {total_written}")

    if dry:
        print("режим --dry, файл не записан")
        return report
    if total_written == 0:
        print("нечего писать (0 новых значений), файл не трогаю")
        return report
    if not wave:
        sys.exit("СТОП: нужна волна для клейма - передай --wave или задай "
                 "SEO_WAVE в окружении (см. шапку модуля)")
    with claimed(wave, agent=agent, path=path):
        save_registry(reg, path=path, wave=wave, agent=agent)
    print(f"реестр записан под клеймом волна «{wave}» агент «{agent}»: {path}")
    return report


# ------------------------------------------------------------------ первичный засев
def _base_dates():
    """URL -> lastmod из карты по решению автора (честные даты ДО технических волн по решению автора)."""
    out = {}
    if not os.path.exists(BASE_SITEMAP):
        return out
    src = open(BASE_SITEMAP, encoding="utf-8").read()
    for block in re.findall(r"<url>.*?</url>", src, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if loc and lm:
            out[loc.group(1)] = lm.group(1)
    return out


def _base_pages():
    """URL -> путь к HTML-слепку по решению автора."""
    out = {}
    if not os.path.exists(BASE_MAP):
        return out
    for line in open(BASE_MAP, encoding="utf-8"):
        bits = line.rstrip("\n").split("\t")
        if len(bits) != 2:
            continue
        p = os.path.join(BASE_PAGES, bits[1] + ".html")
        if os.path.exists(p):
            out[bits[0]] = p
    return out


def _snap_pages():
    """URL -> путь к HTML-слепку по решению автора (corpus-2026-08-04)."""
    out = {}
    if not os.path.exists(SNAP_MANIFEST):
        return out
    for line in open(SNAP_MANIFEST, encoding="utf-8"):
        bits = line.rstrip("\n").split("\t")
        if len(bits) == 3 and bits[0] == "200" and os.path.exists(bits[2]):
            out[bits[1]] = bits[2]
    return out


def header_date(url):
    """Дата Last-Modified прода по Москве (YYYY-MM-DD) или None."""
    import subprocess
    try:
        r = subprocess.run(["curl", "-sSI", "--max-time", "30", url],
                           capture_output=True, timeout=60)
        if r.returncode != 0:
            return None
        m = re.search(r"(?im)^last-modified:\s*(.+)$", r.stdout.decode("utf-8", "replace"))
        if not m:
            return None
        d = datetime.datetime.strptime(m.group(1).strip(), "%a, %d %b %Y %H:%M:%S %Z")
        return d.replace(tzinfo=datetime.timezone.utc).astimezone(MSK).strftime("%Y-%m-%d")
    except Exception:
        return None


def seed(live_pages, dry=False, path=REGISTRY):
    """Первичное наполнение реестра честными датами.

    live_pages - список (url, raw_html) живого корпуса.

    Правило даты (по убыванию доверия):
      1. текст живой страницы == текст слепка по решению автора -> дата из карты по решению автора
         (техническую перезаливку по решению автора игнорируем - содержание то же)
      2. текст разошёлся со слепком по решению автора -> дата Last-Modified прода
         (правка реальная, дата файла для неё честная; выше сегодня не поднимаем)
      3. слепка по решению автора нет (новый URL: хабы /tema/*) -> дата Last-Modified прода
      4. заголовка нет                               -> сегодня
    """
    today = today_msk()
    base_d, base_p, snap_p = _base_dates(), _base_pages(), _snap_pages()
    reg, rows = {}, []
    for url, raw in live_pages:
        sha = content_sha(raw)
        bp = base_p.get(url)
        base_sha = content_sha(open(bp, encoding="utf-8", errors="replace").read()) if bp else None
        sp_ = snap_p.get(url)
        snap_sha = content_sha(open(sp_, encoding="utf-8", errors="replace").read()) if sp_ else None

        if base_sha and sha == base_sha:
            lm, why = base_d.get(url) or today, "unchanged-since-0803"
        else:
            hdr = header_date(url)
            lm = min(hdr, today) if hdr else today
            if base_sha is None:
                why = "new-url"
            elif snap_sha is not None and sha == snap_sha:
                why = "content-changed-0804"
            elif snap_sha is not None:
                why = "content-changed-after-snapshot"
            else:
                why = "content-changed-no-snapshot"
        reg[url] = {"sha256_content": sha, "lastmod": lm, "source": why, "updated_at": today}
        rows.append((url, lm, why))

    if not dry:
        save_registry(reg, path)
    return reg, rows


def _selftest():
    """Клейм-гейт обязан ПАДАТЬ без клейма и пропускать под клеймом."""
    import tempfile
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        reg_path = os.path.join(tmp, "content-sha-registry.json")
        claims = os.path.join(tmp, "wave-claims-test.json")
        os.environ["WAVE_CLAIMS_REGISTRY"] = claims
        for mod in ("claim_gate",):
            sys.modules.pop(mod, None)

        try:
            save_registry({"https://x/": {"lastmod": "2026-01-01"}}, reg_path)
            fails.append("без клейма запись ПРОШЛА")
            print("  FAIL без клейма запись прошла")
        except RuntimeError as exc:
            print(f"  ok   без клейма запись отбита: {str(exc).splitlines()[0]}")

        # R214 (круг 4, класс R212/R213 «работает у автора, ломается у ученика»).
        # claim_gate.py - внутренний мьютекс-инструмент автора (~/IvanOS/…/_rebuild/),
        # в пакет не входит и не может входить (та же причина, что uborka_bez_udaleniya:
        # личная инфраструктура, не продуктовый код). Проверка ВЫШЕ уже доказала
        # главное свойство закона - без клейма запись честно отбивается ДАЖЕ когда
        # claim_gate.py недоступен (фолбэк «не могу проверить владение -> считаю
        # чужим» сработал сам). Всё, что ниже, гоняет CLAIM_GATE ПРЯМЫМ subprocess
        # без try/except - без файла это НЕОБРАБОТАННЫЙ traceback, а не честный
        # SKIP. Тест становится класс-осведомлённым: у автора (файл на месте) идёт
        # ПОЛНЫЙ прогон как раньше, у ученика - честный SKIP вместо падения.
        if not os.path.isfile(CLAIM_GATE):
            print("  SKIP: claim_gate.py не входит в пакет (личный мьютекс-инструмент "
                  "автора) - кросс-процессный claim/release не проверяется. "
                  "Фолбэк «нельзя проверить владение -> отбить запись» уже "
                  "подтверждён проверкой выше и работает независимо от файла.")
            print("\nlastmod_registry клейм-гейт: провалов %d (частичный прогон, "
                  "claim_gate.py недоступен)" % len(fails))
            return 0 if not fails else 1

        subprocess.run([sys.executable, CLAIM_GATE, "claim", reg_path, "тест-волна",
                        "--agent", "selftest"], check=True, capture_output=True)
        # 🔴 ИЗМЕНЕНИЕ КОНТРАКТА (скептик-E, E1): «клейм есть» больше не равно
        # «клейм мой». Писатель обязан объявить себя - иначе доказать владение
        # нечем и волна по умолчанию считается чужой.
        try:
            save_registry({"https://x/": {"lastmod": "2026-01-01"}}, reg_path)
            fails.append("под чужим клеймом БЕЗ объявления запись ПРОШЛА")
            print("  FAIL под клеймом без объявления волны запись прошла")
        except RuntimeError as exc:
            print(f"  ok   под клеймом БЕЗ объявления волны запись отбита: "
                  f"{str(exc).splitlines()[0]}")
        try:
            save_registry({"https://x/": {"lastmod": "2026-01-01"}}, reg_path,
                          wave="тест-волна", agent="selftest")
            print("  ok   под СВОИМ объявленным клеймом запись прошла")
        except RuntimeError as exc:
            fails.append(f"под своим объявленным клеймом запись отбита: {exc}")
            print(f"  FAIL под своим объявленным клеймом запись отбита: {exc}")
        subprocess.run([sys.executable, CLAIM_GATE, "release", reg_path, "тест-волна",
                        "--agent", "selftest"], check=True, capture_output=True)

        try:
            save_registry({"https://x/": {"lastmod": "2026-01-02"}}, reg_path)
            fails.append("после release запись ПРОШЛА")
            print("  FAIL после release запись прошла")
        except RuntimeError:
            print("  ok   после release запись снова отбита")

        os.environ["SEO_REGISTRY_CLAIM_WAIVER"] = "самотест"
        try:
            save_registry({"https://x/": {"lastmod": "2026-01-03"}}, reg_path)
            print("  ok   осознанный обход WAIVER работает и печатается")
        except RuntimeError as exc:
            fails.append(f"WAIVER не сработал: {exc}")
            print(f"  FAIL WAIVER не сработал: {exc}")
        del os.environ["SEO_REGISTRY_CLAIM_WAIVER"]

        with claimed("контекст-волна", agent="selftest", path=reg_path):
            try:
                save_registry({"https://x/": {"lastmod": "2026-01-04"}}, reg_path)
                print("  ok   контекст-менеджер claimed() пропускает запись")
            except RuntimeError as exc:
                fails.append(f"claimed() не пропустил: {exc}")
                print(f"  FAIL claimed() не пропустил: {exc}")
        try:
            save_registry({"https://x/": {"lastmod": "2026-01-05"}}, reg_path)
            fails.append("после выхода из claimed() запись ПРОШЛА")
            print("  FAIL после выхода из claimed() запись прошла")
        except RuntimeError:
            print("  ok   после выхода из claimed() клейм снят, запись отбита")

        # ── ДОБОР СКЕПТИКА-E (по решению автора) ─────────────────────────────────
        cg_dir = os.path.dirname(CLAIM_GATE)
        sys.path.insert(0, cg_dir)
        import claim_gate as cg
        sys.modules["claim_gate"] = cg

        def _check(name, ok, note=""):
            print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f": {note}" if note else ""))
            if not ok:
                fails.append(name)

        def _wrote(**kw):
            try:
                save_registry({"https://x/": {"lastmod": "2026-02-01"}}, reg_path, **kw)
                return True, ""
            except RuntimeError as exc:
                return False, str(exc).splitlines()[0]

        # E1. ЧУЖАЯ волна держит реестр - запись обязана отбиться
        subprocess.run([sys.executable, CLAIM_GATE, "claim", reg_path, "чужая-волна",
                        "--agent", "другой-агент"], check=True, capture_output=True)
        ok, note = _wrote()
        _check("E1 запись при ЧУЖОМ клейме без объявления себя отбита", not ok, note)
        ok, note = _wrote(wave="моя-волна")
        _check("E1 запись ЧУЖОЙ волной (wave= явно) отбита", not ok, note)
        os.environ["SEO_WAVE"] = "моя-волна"
        ok, note = _wrote()
        _check("E1 запись при чужом клейме и SEO_WAVE=другая отбита", not ok, note)
        # 🔴 ПЕРЕСМОТР ПРЕЖНЕГО ОЖИДАНИЯ (скептик-G, M9b, по решению автора). Здесь
        # стояло «позитив: SEO_WAVE = волна-владелец, запись прошла» - и это была
        # дыра: клейм держит ИМЕНОВАННЫЙ агент «другой-агент», а посторонний
        # процесс проходил, назвав одну волну. Имя волны владения не доказывает.
        # Новый закон: под именованным клеймом объявляется ПАРА волна+агент.
        os.environ["SEO_WAVE"] = "чужая-волна"
        ok, note = _wrote()
        _check("G-M9b SEO_WAVE владельца БЕЗ агента под именованным клеймом отбит",
               not ok and "АГЕНТ НЕ ОБЪЯВЛЕН" in note, note)
        os.environ["SEO_AGENT"] = "другой-агент"
        ok, note = _wrote()
        _check("G-M9b позитив: SEO_WAVE + SEO_AGENT владельца пишут", ok, note)
        os.environ["SEO_AGENT"] = "самозванец"
        ok, note = _wrote()
        _check("G-M9b SEO_AGENT чужого агента отбит",
               not ok and "ЧУЖОЙ АГЕНТ" in note, note)
        del os.environ["SEO_AGENT"]
        ok, note = _wrote(wave="чужая-волна")
        _check("G-M9b явный wave= без agent= под именованным клеймом отбит",
               not ok and "АГЕНТ НЕ ОБЪЯВЛЕН" in note, note)
        del os.environ["SEO_WAVE"]
        ok, note = _wrote(wave="чужая-волна", agent="другой-агент")
        _check("E1 позитив: явные wave+agent владельца, запись прошла", ok, note)
        ok, note = _wrote(wave="чужая-волна", agent="третий-агент")
        _check("E1 та же волна ДРУГИМ агентом отбита", not ok, note)
        # WAIVER не должен снимать чужой клейм: обход существует для «клейма нет»
        os.environ["SEO_REGISTRY_CLAIM_WAIVER"] = "проба обхода на чужом клейме"
        ok, note = _wrote()
        del os.environ["SEO_REGISTRY_CLAIM_WAIVER"]
        _check("E1 WAIVER НЕ снимает чужой клейм", not ok, note)
        subprocess.run([sys.executable, CLAIM_GATE, "release", reg_path, "чужая-волна",
                        "--agent", "другой-агент", "--reason", "selftest"],
                       check=True, capture_output=True)

        # G-M9b границы нового отказа: строгость не должна ломать штатную работу.
        # (а) клейм взят БЕЗ имени агента - назвать одну волну по-прежнему хватает;
        # (б) свой же контекст claimed() ничего объявлять повторно не обязан.
        # T-O1 (по решению автора) закрыл ДВЕРЬ, а не правило: новых безымянных клеймов
        # CLI больше не создаёт (два честных безымянных процесса неотличимы), но
        # СТАРЫЕ ряды в боевом реестре остались, и правило «клейм без имени
        # агента -> назвать волну достаточно» для них обязано работать. Поэтому
        # ряд теперь заводится так, как он единственно и может теперь возникнуть:
        # он уже лежит в файле.
        cg_mod = _cg()
        _key = cg_mod.canon_path(reg_path)
        _claims = cg_mod._load(claims)
        _row = next((r for r in _claims["claims"] if r.get("path") == _key), None)
        if _row is None:
            _row = {"path": _key}
            _claims["claims"].append(_row)
        _row.update({"wave": "волна-без-агента", "agent": "",
                     "ts": "2026-08-01 00:00:00", "status": "claimed"})
        _row.pop("released_by", None)
        _row.pop("release_reason", None)
        cg_mod._save(claims, _claims)
        ok, note = _wrote(wave="волна-без-агента")
        _check("G-M9b клейм без имени агента: одной волны достаточно", ok, note)
        r = subprocess.run([sys.executable, CLAIM_GATE, "claim", reg_path, "волна-без-агента"],
                           capture_output=True, text=True)
        _check("T-O1 CLI больше НЕ заводит безымянный клейм",
               r.returncode == 2 and "БЕЗ ИМЕНИ" in (r.stdout + r.stderr),
               (r.stdout + r.stderr).strip()[:120])
        # Легаси-ряд без имени владельца снимается ЯВНЫМ угоном с причиной -
        # тем же путём, что и висяк умершего процесса. Причина уезжает в реестр,
        # молчаливого снятия безымянного клейма нет.
        r = subprocess.run([sys.executable, CLAIM_GATE, "release", reg_path,
                            "волна-без-агента", "--agent", "мигратор", "--steal",
                            "--reason", "легаси-ряд без имени, selftest"],
                           capture_output=True, text=True)
        _check("T-O1 легаси безымянный клейм снимается --steal с причиной",
               r.returncode == 0, (r.stdout + r.stderr).strip()[:120])
        with claimed("волна-контекст", agent="ctx-агент", path=reg_path):
            ok, note = _wrote()
            _check("G-M9b свой контекст claimed(): агента объявлять не нужно", ok, note)

        # Т-1. Вторая дверь того же класса: подсадка на клейм СВОЕЙ волны, но
        # ЧУЖИМ агентом. До правки контекст входил молча и писал файл параллельно
        # с владельцем; claim_gate такой захват уже отбивает, значит и здесь отказ.
        subprocess.run([sys.executable, CLAIM_GATE, "claim", reg_path, "W-два-агента",
                        "--agent", "agent-A"], check=True, capture_output=True)
        try:
            with claimed("W-два-агента", agent="agent-B", path=reg_path):
                piggy = True
        except RuntimeError as exc:
            piggy, note = False, str(exc).splitlines()[0]
        _check("Т-1 claimed() ЧУЖИМ агентом своей волны не входит", not piggy, note)
        ok, note = _wrote(wave="W-два-агента", agent="agent-A")
        _check("Т-1 владелец пары (волна, агент) пишет по-прежнему", ok, note)
        subprocess.run([sys.executable, CLAIM_GATE, "release", reg_path, "W-два-агента",
                        "--agent", "agent-A", "--reason", "selftest cleanup"],
                       check=True, capture_output=True)

        # E2. Противоречивый ряд: заливка стоит - значит и запись стоит
        subprocess.run([sys.executable, CLAIM_GATE, "claim", reg_path, "W-против",
                        "--agent", "a"], check=True, capture_output=True)
        d = json.load(open(claims, encoding="utf-8"))
        d["claims"][-1]["released_by"] = "orchestrator-руками"
        json.dump(d, open(claims, "w", encoding="utf-8"), ensure_ascii=False)
        rc = subprocess.run([sys.executable, CLAIM_GATE, "check", reg_path, "W-против"],
                            capture_output=True).returncode
        ok, note = _wrote(wave="W-против")
        _check("E2 противоречивый ряд: check стоп И запись стоп",
               rc != 0 and not ok, f"check rc={rc} · {note}")
        try:
            with claimed("W-против", agent="a", path=reg_path):
                ctx = True
        except RuntimeError:
            ctx = False
        _check("E2 claimed() на противоречивом ряду не входит", not ctx)
        try:
            claim_holder(reg_path, strict=True)
            strict_raised = False
        except RuntimeError:
            strict_raised = True
        soft = claim_holder(reg_path)
        _check("E2 claim_holder(strict=True) падает на битом ряду, "
               "справочный вызов отвечает", strict_raised and soft is not None)
        os.environ["SEO_REGISTRY_CLAIM_WAIVER"] = "проба обхода на битом ряду"
        ok, note = _wrote(wave="W-против")
        del os.environ["SEO_REGISTRY_CLAIM_WAIVER"]
        _check("E2 WAIVER НЕ снимает противоречивый ряд", not ok, note)
        subprocess.run([sys.executable, CLAIM_GATE, "release", reg_path, "W-против",
                        "--agent", "a", "--reason", "selftest cleanup"],
                       check=True, capture_output=True)

        # E3. Дубль рядов на один канон-ключ: обе точки входа стоят
        d = json.load(open(claims, encoding="utf-8"))
        key = cg.canon_path(reg_path)
        d["claims"].append({"path": key, "wave": "W-живая", "agent": "b",
                            "ts": "2026-08-10 00:00:00", "status": "claimed"})
        json.dump(d, open(claims, "w", encoding="utf-8"), ensure_ascii=False)
        rc = subprocess.run([sys.executable, CLAIM_GATE, "check", reg_path, "ДРУГАЯ"],
                            capture_output=True).returncode
        rc_audit = subprocess.run([sys.executable, CLAIM_GATE, "audit"],
                                  capture_output=True).returncode
        ok, note = _wrote(wave="W-живая")
        _check("E3 дубль рядов: check стоп, audit видит, запись стоп",
               rc != 0 and rc_audit == 2 and not ok, f"check rc={rc} · audit rc={rc_audit}")
        try:
            with claimed("W-живая", agent="b", path=reg_path):
                ctx = True
        except RuntimeError:
            ctx = False
        _check("E3 claimed() на дубле рядов не входит", not ctx)
        rc = subprocess.run([sys.executable, CLAIM_GATE, "dedupe", "--apply"],
                            capture_output=True).returncode
        rows = cg._rows_for(cg._load(claims), key)
        _check("E3 миграция dedupe схлопнула дубль в один ряд",
               rc == 0 and len(rows) == 1, f"рядов на ключ: {len(rows)}")

        # ── Р.1а: datePublished (по решению автора) - позитив И негатив ──────────
        ld_html_ok = (
            '<html><head><title>т</title>'
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"Article","datePublished":"2026-08-01T10:00:00+03:00",'
            '"dateModified":"2026-08-05"}]}'
            '</script></head><body>текст</body></html>'
        )
        _check("extract_date_published: @graph + ISO-datetime -> дата без времени",
               extract_date_published(ld_html_ok) == "2026-08-01")
        _check("extract_date_published: нет <script> -> None",
               extract_date_published("<html><body>пусто</body></html>") is None)
        ld_html_broken_then_ok = (
            '<script type="application/ld+json">{битый json</script>'
            '<script type="application/ld+json">{"datePublished":"2026-07-25"}</script>'
        )
        _check("extract_date_published: битый JSON-LD пропускается, следующий блок читается",
               extract_date_published(ld_html_broken_then_ok) == "2026-07-25")

        _check("_plausible_date_published: дата на границе порога проходит",
               _plausible_date_published(MIN_PLAUSIBLE_DATE_PUBLISHED))
        _check("_plausible_date_published: дата раньше порога (мусор в разметке) отбита",
               not _plausible_date_published("2026-06-26"))
        _check("_plausible_date_published: None отбит", not _plausible_date_published(None))

        for u in ("https://<твой-домен>/",
                  "https://<твой-домен>/guide-claude-code/",
                  "https://<твой-домен>/about.html",
                  "https://<твой-домен>/slovar/mcp/"):
            fname = u.replace("https://", "").replace("/", "__") + ".html"
            _check(f"_corpus_url_from_filename обратим для {u}",
                   _corpus_url_from_filename(fname) == u, fname)

        rr = {}
        _lm1, st1, _sha1 = resolve(rr, "https://x/", "<html><title>a</title><body>1</body></html>",
                                   today="2026-08-01")
        _check("resolve(): 'new' без datePublished не выдумывает поле",
               st1 == "new" and "datePublished" not in rr["https://x/"])
        rr["https://x/"]["datePublished"] = "2026-07-20"
        _lm2, st2, _sha2 = resolve(rr, "https://x/", "<html><title>a</title><body>2 другой</body></html>",
                                   today="2026-08-02")
        _check("resolve(): 'changed' СОХРАНЯЕТ проставленный datePublished",
               st2 == "changed" and rr["https://x/"].get("datePublished") == "2026-07-20")

        # интеграция backfill_datepublished на синтетике (без сети, без боевого реестра)
        bf_dir = os.path.join(tmp, "bf")
        corpus_dir = os.path.join(bf_dir, "corpus")
        os.makedirs(corpus_dir)
        # 🔴 ИМЯ НАРОЧНО НЕ "content-sha-registry.json": claim_gate.canon_path
        # аliasит ЛЮБОЙ локальный файл с этим именем на боевой продовый путь
        # (LOCAL_ALIASES) - тестовый claim столкнулся бы с претензией на
        # РЕАЛЬНЫЙ ресурс. Имя файла в этом блоке специально другое, чтобы
        # тест бил по изолированному ключу, а не по продовому.
        bf_reg_path = os.path.join(bf_dir, "test-registry.json")
        bf_state_path = os.path.join(bf_dir, "test-state.json")
        json.dump({
            "https://<твой-домен>/guide-rost/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test"},
            "https://<твой-домен>/guide-old/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test"},
            "https://<твой-домен>/guide-musor/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test"},
            "https://<твой-домен>/guide-dyra/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test"},
            "https://<твой-домен>/guide-uzhe/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test",
                "datePublished": "2026-01-01"},
            "https://<твой-домен>/guide-retired/": {
                "sha256_content": "x", "lastmod": "2026-08-01", "source": "test",
                "retired": True},
        }, open(bf_reg_path, "w", encoding="utf-8"))
        json.dump({"темы": [
            {"статус": "опубликовано", "url": "https://<твой-домен>/guide-rost/",
             "опубликовано": "2026-08-01"},
        ]}, open(bf_state_path, "w", encoding="utf-8"))
        for slug, dp in (("guide-old", "2026-07-28"), ("guide-musor", "2026-06-01")):
            fn = f"<твой-домен>__{slug}__.html"
            open(os.path.join(corpus_dir, fn), "w", encoding="utf-8").write(
                '<script type="application/ld+json">'
                f'{{"@type":"Article","datePublished":"{dp}"}}</script>')

        rep = backfill_datepublished(dry=True, corpus=corpus_dir, path=bf_reg_path,
                                     state_path=bf_state_path)
        _check("backfill dry: rost получил дату из state.json",
               ("https://<твой-домен>/guide-rost/", "2026-08-01") in rep["from_state_json"])
        _check("backfill dry: не-rost получил дату из JSON-LD слепка",
               ("https://<твой-домен>/guide-old/", "2026-07-28") in rep["from_jsonld"])
        _check("backfill dry: мусорная ранняя дата отброшена, НЕ записана",
               any(u == "https://<твой-домен>/guide-musor/"
                   for u, _, _ in rep["implausible_rejected"]))
        _check("backfill dry: страница без слепка и без rost-даты - в пробелах",
               any(u == "https://<твой-домен>/guide-dyra/" for u, _ in rep["no_data"]))
        _check("backfill dry: уже проставленное поле не трогается без --force",
               "https://<твой-домен>/guide-uzhe/" in rep["already_set_skipped"])
        _check("backfill dry: retired пропущен",
               "https://<твой-домен>/guide-retired/" in rep["retired_skipped"])
        on_disk = json.load(open(bf_reg_path, encoding="utf-8"))
        _check("backfill dry: --dry НИЧЕГО не пишет на диск",
               "datePublished" not in on_disk["https://<твой-домен>/guide-rost/"])

        _saved_wave = os.environ.pop("SEO_WAVE", None)
        _saved_agent = os.environ.pop("SEO_AGENT", None)
        try:
            raised = False
            try:
                backfill_datepublished(dry=False, corpus=corpus_dir, path=bf_reg_path,
                                       state_path=bf_state_path, wave=None, agent=None)
            except SystemExit:
                raised = True
            _check("backfill без --dry и без волны/клейма падает (SystemExit), не пишет молча",
                   raised)
        finally:
            if _saved_wave is not None:
                os.environ["SEO_WAVE"] = _saved_wave
            if _saved_agent is not None:
                os.environ["SEO_AGENT"] = _saved_agent
        on_disk2 = json.load(open(bf_reg_path, encoding="utf-8"))
        _check("после падения без клейма файл НЕ изменился",
               "datePublished" not in on_disk2["https://<твой-домен>/guide-rost/"])

        backfill_datepublished(dry=False, corpus=corpus_dir, path=bf_reg_path,
                               state_path=bf_state_path, wave="bf-волна", agent="bf-агент")
        on_disk3 = json.load(open(bf_reg_path, encoding="utf-8"))
        _check("backfill боевой прогон под своей волной: rost записан на диск",
               on_disk3["https://<твой-домен>/guide-rost/"].get("datePublished") == "2026-08-01")
        _check("backfill боевой прогон: retired-запись не тронута полем",
               "datePublished" not in on_disk3["https://<твой-домен>/guide-retired/"])
        _check("backfill боевой прогон: клейм снят после записи (release)",
               claim_holder(bf_reg_path) is None)

        os.environ.pop("WAVE_CLAIMS_REGISTRY", None)

    print(f"\nlastmod_registry клейм-гейт: провалов {len(fails)}")
    sys.exit(1 if fails else 0)


def main():
    ap = argparse.ArgumentParser(description="Реестр содержимого для честного lastmod")
    ap.add_argument("--selftest", action="store_true", help="проверка клейм-гейта")
    ap.add_argument("--seed", action="store_true", help="первичное наполнение из живого корпуса")
    ap.add_argument("--dry", action="store_true", help="не записывать файл реестра")
    ap.add_argument("--show", help="показать запись реестра по URL")
    ap.add_argument("--backfill-datepublished", action="store_true",
                    help="проставить datePublished: rost из state.json, остальные из JSON-LD слепка")
    ap.add_argument("--corpus", help="каталог HTML-слепка для JSON-LD (иначе автоподбор свежайшего)")
    ap.add_argument("--wave", help="волна для клейма записи (иначе SEO_WAVE из окружения)")
    ap.add_argument("--agent", help="агент для клейма записи (иначе SEO_AGENT из окружения)")
    ap.add_argument("--force", action="store_true",
                    help="с --backfill-datepublished: пересчитать даже там, где уже стоит")
    ap.add_argument("--поток", dest="workers", type=int, default=8)
    ap.add_argument("--из-кэша", dest="from_cache",
                    help="каталог со снятым корпусом (_index.json: url -> файл) вместо "
                         "нового сплошного обхода прода - правило сессии: сплошной "
                         "замер корпуса делается один раз")
    a = ap.parse_args()

    if a.selftest:
        # R214 (круг 4): без этого return поток проваливался в "нужен --seed"
        # ниже и выходил кодом 2 ДАЖЕ после успешного самотеста - документированная
        # ученику команда `--selftest` без спутников превращала честный SKIP/PASS
        # в ложный красный. --show и --backfill-datepublished уже возвращаются
        # сразу после своего действия, --selftest была единственным исключением.
        return _selftest()

    if a.show:
        rec = load_registry().get(a.show)
        print(json.dumps(rec, ensure_ascii=False, indent=1) if rec else "нет записи")
        return

    if a.backfill_datepublished:
        backfill_datepublished(dry=a.dry, corpus=a.corpus, wave=a.wave, agent=a.agent,
                               force=a.force)
        return

    if not a.seed:
        ap.error("нужен --seed, --show или --backfill-datepublished")

    if a.from_cache:
        idx = json.load(open(os.path.join(a.from_cache, "_index.json"), encoding="utf-8"))
        urls = list(idx)
        raws = [open(idx[u] if os.path.isabs(idx[u]) else os.path.join(a.from_cache, os.path.basename(idx[u])),
                     encoding="utf-8", errors="replace").read() for u in urls]
        print(f"корпус взят из кэша {a.from_cache}: {len(urls)} страниц")
    else:
        import seo_publish as sp
        from concurrent.futures import ThreadPoolExecutor
        cfg = sp.load_config(None)
        live = sp.fetch(f'{cfg["domain"]}/sitemap.xml').decode("utf-8", "replace")
        urls = re.findall(r"<loc>(.*?)</loc>", live)
        urls = [u for u in urls if u.startswith(cfg["domain"])]
        print(f"адресов в живой карте: {len(urls)}")

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            raws = list(ex.map(lambda u: sp.fetch(u).decode("utf-8", "replace"), urls))
    empty = [u for u, r in zip(urls, raws) if len(r) < 500]
    if empty:
        sys.exit(f"СТОП: {len(empty)} страниц вернули пустое тело - засев по дырам не делаю: {empty[:5]}")

    reg, rows = seed(list(zip(urls, raws)), dry=a.dry)
    by_date, by_why = {}, {}
    for _, lm, why in rows:
        by_date[lm] = by_date.get(lm, 0) + 1
        by_why[why] = by_why.get(why, 0) + 1
    print(f"записей в реестре: {len(reg)}")
    print("распределение lastmod:")
    for d in sorted(by_date):
        print(f"   {d}  {by_date[d]}")
    print("почему такая дата:")
    for w, n in sorted(by_why.items(), key=lambda x: -x[1]):
        print(f"   {w}: {n}")
    print(("режим --dry, файл не записан" if a.dry else f"реестр записан: {REGISTRY}"))


if __name__ == "__main__":
    main()
