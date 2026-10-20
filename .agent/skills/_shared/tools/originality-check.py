#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
originality-check.py - измеримая проверка оригинальности черновика статьи.

Превращает «оригинально на глаз» в число: насколько текст черновика совпадает с
уже опубликованными материалами (или с эталонным корпусом). Считаем по КАЖДОМУ
документу корпуса и берём максимум - так ловим самоповтор даже против одной
похожей статьи, а не «в среднем по больнице».

Метрики:
  - cosine    - TF-IDF косинус по СОДЕРЖАТЕЛЬНЫМ словам (смысловая близость,
                каннибализация темы: та же фактура, свои слова).
  - ngram     - Jaccard по словесным n-граммам полного текста (дословные куски
                подряд, по умолч. 5).
  - jaccard   - Jaccard по множеству содержательных слов (общий пул, справочно).

Пороги (берутся из config.yaml → CLI → дефолт):
  tools.originality.max_cosine   (по умолч. 0.50)
  tools.originality.max_ngram    (по умолч. 0.30)
  tools.originality.ngram_n      (по умолч. 5)
PASS, если cosine ≤ max_cosine И ngram ≤ max_ngram. Иначе FAIL (клон-риск → переписать).

────────────────────────────────────────────────────────────────────────────────
🔴 ЧЕМ СЧИТАЕТСЯ БЛИЗОСТЬ И ПОЧЕМУ ИМЕННО ТАК (калибровка по решению автора)

Было. Косинус считался по СЫРЫМ токенам, а «idf» строился по паре документов:
df ∈ {1,2} → вес 1.405 у слова из одного текста и 1.0 у слова из обоих. Это не
idf, а почти константа, то есть фактически косинус по сырым частотам. Плюс
служебные слова из словаря не вычитались. Итог: похожесть набирали предлоги и
частицы. Разложение боевой пары (черновик «как пользоваться нейросетью» против
«что такое нейросеть», косинус 0.6244): «не» 24.4%, «на» 14.8%, «по» 6.1%,
«из» 6.0%, «что» 5.2% - пять служебных слов дают 56.4% похожести, топ-30 даёт
83.2%, дословных совпадений при этом НОЛЬ (ngram-5 jaccard = 0.0). Гейт краснел
на том, что оба текста написаны по-русски.

Стало - три вычитания, каждое закрывает свою причину:
  1. СТОП-СЛОВА. Из косинуса вычитаются служебные слова русского и английского
     (предлоги, союзы, частицы, местоимения, связки, модальные). Список строго
     ГРАММАТИЧЕСКИЙ: доменных слов («нейросеть», «промпт», «claude») в нём нет
     сознательно - ими занимается пункт 2.
  2. IDF ПО КОРПУСУ, а не по паре. df считается по ВСЕМУ пулу сравнения
     (черновик + все эталоны). Слово, которое есть у всех статей корпуса, само
     теряет вес - руками в стоп-лист его вносить не надо. Тот же приём уже
     работает в отборе соседей (`article_gates.topic_cosine_ranker`), теперь
     «похоже» значит одно и то же на обоих слоях движка.
  3. ЦИФРОВЫЕ ТОКЕНЫ (годы, номера пунктов) из косинуса убраны - то же правило,
     что в отборе соседей.

Чего сознательно НЕ сделали: сублинейный tf (1+log tf). Он выглядит правильным
по учебнику, но проверка негативной фикстурой его отвергла. Замер: перефразированная
почти-копия опубликованной статьи (та же структура, та же фактура, свои слова)
даёт 0.683 на принятой формуле и 0.591 с сублинейным tf, то есть С НИМ ГЕЙТ
ПЕРЕСТАЁТ ЛОВИТЬ НАСТОЯЩУЮ КАННИБАЛИЗАЦИЮ при пороге 0.60. Частотный профиль
терминов - это и есть главная улика пересказа, сглаживать его нельзя.

Замер по корпусу (54 черновика, принятые владельцем и опубликованные) при
неизменном пороге 0.60:
  было  - 20 из 54 красных (37% принятого корпуса), то есть гейт блокировал
          собственный корпус; медиана 0.572, максимум 0.854
  стало - 1 из 54 красных, медиана 0.297, p90 0.437; и этот единственный красный
          НЕ ложный: `guide-claude-corps` (0.677) действительно поглощён живой
          страницей `guide-uzel-korpus`, у неё те же разделы про Claude Corps
Негативные фикстуры при том же пороге: дословная копия 0.996 · склейка пополам с
донором 0.871 · перефразированная почти-копия 0.683 - все три ловятся.
Порог 0.60 НЕ трогали: после починки формулы он сам лёг в зазор между принятым
корпусом (потолок 0.463 без учёта настоящего дубля) и самой мягкой из
негативных фикстур (0.683).

ПОЧЕМУ NGRAM СЧИТАЕТСЯ ПО ПОЛНОМУ ТЕКСТУ, А НЕ ПО СОДЕРЖАТЕЛЬНЫМ СЛОВАМ.
Дословное заимствование включает служебные слова, они часть цитаты. Если их
выкинуть, соседние по смыслу, но далёкие по тексту слова склеятся в н-грамму,
которой в оригинале не было, - метрика начнёт находить списывание там, где его
нет. Поэтому стоп-слова вычитаются ТОЛЬКО из косинуса.

ЗАВИСИМОСТЬ ОТ РАЗМЕРА ПУЛА. idf считается по переданному корпусу, поэтому при
одном эталонном файле пункт 2 вырождается (n=2) и работают только пункты 1 и 3.
Это безопасно: замер по корпусу на одних лишь стоп-словах даёт тот же 1 красный
из 54. Стоп-лист - гарантированный пол, idf по корпусу - добавка, растущая с
числом соседей.
────────────────────────────────────────────────────────────────────────────────

ЧЕСТНОЕ ОГРАНИЧЕНИЕ (скрипт сам его репортит):
  Лексические метрики осмысленны ТОЛЬКО когда черновик и эталон на одном языке.
  Если эталон на другом языке (другой алфавит) - косинус тривиально ≈0 и это НЕ
  доказывает оригинальность смысла. В таком случае ставится cross_language=true,
  вердикт уходит человеку/агенту (оценить структурную близость: порядок мыслей,
  свои примеры), а не решается этим скриптом.

ЧЕГО ФОРМУЛА НЕ ЛОВИТ (границы честно, чтобы на неё не полагались сверх меры):
  - пересказ ДРУГИМИ ТЕРМИНАМИ: если тот же смысл изложен другим словарём
    («поручение» вместо «промпт», «сервис» вместо «нейросеть»), лексический
    косинус падает. Пересечение структуры и порядка мыслей это не мерит;
  - заимствование не у соседа по корпусу, а у внешнего источника - сравнение
    идёт только с тем, что передали в corpus;
  - совпадение СТРУКТУРЫ при своей фактуре (те же H2 в том же порядке) - это
    отдельная ось, её закрывает не этот скрипт;
  - очень короткие тексты (< 200 содержательных слов): косинус на них шумный,
    скрипт помечает это в выводе полем short_text.

Зависимости: только стандартная библиотека Python 3 (re, json, math, os, argparse).
PyYAML не требуется - если config.yaml есть, читается встроенным мини-парсером.

Использование:
  python3 tools/originality-check.py <черновик.md> <корпус/>            # папка с эталонами
  python3 tools/originality-check.py <черновик.md> <эталон.txt>          # один файл
  python3 tools/originality-check.py <черновик.md> <корпус/> --max-cosine 0.45 --json
  python3 tools/originality-check.py <черновик.md> --config ./config.yaml <корпус/>
  python3 tools/originality-check.py <черновик.md> <корпус/> --legacy-cosine # формула ДО по решению автора
  python3 tools/originality-check.py --selftest

Коды выхода: 0 = PASS, 1 = FAIL, 2 = разные языки (решение отдано человеку), 3 = ошибка ввода.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter

try:
    import _config as cfgmod
except ImportError:  # запуск из другой директории - добавим папку скрипта в путь
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _config as cfgmod

CYRILLIC = re.compile(r"[а-яё]")
LATIN = re.compile(r"[a-z]")
# слово = последовательность букв (кириллица/латиница) и цифр длиной ≥ 2
TOKEN = re.compile(r"[a-zа-яё0-9]{2,}", re.IGNORECASE)

# дефолты (используются, если нет ни config.yaml, ни CLI-флага)
DEFAULT_COSINE_MAX = 0.50
DEFAULT_NGRAM_MAX = 0.30
DEFAULT_NGRAM_N = 5
# ниже этого числа содержательных слов косинус шумный - помечаем в отчёте
SHORT_TEXT_WORDS = 200

TEXT_EXTS = (".md", ".markdown", ".txt", ".mdx", ".html", ".htm", ".rst", ".text")

# ── стоп-слова: ТОЛЬКО грамматика ───────────────────────────────────────────
# Предлоги, союзы, частицы, местоимения, связки, модальные, общие количественные
# и временные наречия. Доменных слов здесь нет сознательно: «нейросеть», «промпт»,
# «claude» одинаково часты во всём корпусе, и вес у них снимает idf по корпусу,
# а не ручной список. Список общеязыковой - привязки к автору и нише в нём нет.
RU_STOP = frozenset("""
без более больше будем будет будете будешь буду будут будучи будь бы был была
были было быть вам вами вас ваш ваша ваше ваши вдруг ведь весь вниз внизу во
вокруг вот впрочем все всё всегда всего всей всем всеми всему всех всею вся всю
всякий вы где да давай даже далее далеко дальше даром для до довольно долго
должен должна должно должны другая другие другим других другое другой ему если
есть ещё еще же зато зачем здесь значит из или им ими имя иногда их итак каждая
каждое каждый каждые как какая какие каким какое какой кем когда кого ком кому
которая которого которое которой котором которому которую которые который
которых кто куда ли либо лишь мало между меля меня мне мной много многое многие
мог могут мож может можем можете можешь можно мои мой моя моё мы на над надо
назад наиболее наконец нам нами нас наш наша наше наши не него неё ней нельзя
нет нею ни нибудь никогда никто ним ними них ничего но ну нужно нх об оба однако
он она они оно от от ото очень перед по под пожалуйста позже пока получается
помимо поскольку после потом потому почему почти при про просто против пусть
разве разные ради ранее раньше сам сама сами самим самими самих само самого
самой самом самому саму свое своей своего своей своем своём своему свои своих
свою своя себе себя сегодня сейчас сказал сколько скорее слишком снова со собой
совсем сразу стал стала стали стало стать стоит так такая также таки такие такое
такой там те тебе тебя тем теми теперь тех то тобой тобою тогда того тоже той
только том тому тот тою три ту туда тут ты тут тебе уж уже хоть хотя чаще чего
чем через чтоб чтобы что чуть эта эти этим этими этих это этого этой этом этому
этот эту я
""".split())

EN_STOP = frozenset("""
about above after again against all also am an and any are as at be because been
before being below between both but by can cannot could did do does doing done
down during each few for from further had has have having he her here hers him
his how however if in into is it its itself just may me might more most must my
no nor not now of off on once only or other others ought our ours out over own
same shall she should so some such than that the their theirs them then there
these they this those through to too under until up very was we were what when
where which while who whom why will with would you your yours
""".split())

STOPWORDS = RU_STOP | EN_STOP


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_markup(text):
    """Снять markup/служебную разметку, чтобы сравнивать смысл, а не синтаксис."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)          # код-блоки
    text = re.sub(r"`[^`]*`", " ", text)                             # inline-код
    text = re.sub(r"<[^>]+>", " ", text)                             # html-теги
    text = re.sub(r"^---\n.*?\n---\n", " ", text, flags=re.DOTALL)   # yaml-фронтматтер
    text = re.sub(r"^\s*#{1,6}\s*", " ", text, flags=re.MULTILINE)   # заголовки
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)                # картинки
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)             # ссылки → текст
    text = re.sub(r"[*_>|#~]", " ", text)                            # маркеры разметки
    text = re.sub(r"\d{1,2}:\d{2}", " ", text)                       # тайм-коды 0:15
    return text


def tokens(text):
    return [t.lower() for t in TOKEN.findall(text)]


def content_tokens(toks):
    """Только содержательные слова: без служебных и без чисто цифровых токенов.

    Идёт в косинус и в справочный word_jaccard. В n-граммы НЕ идёт - там нужен
    полный текст, иначе далёкие слова склеятся в несуществующую цитату.
    """
    return [t for t in toks if t not in STOPWORDS and not t.isdigit()]


def detect_lang(toks):
    cyr = sum(1 for t in toks if CYRILLIC.search(t))
    lat = sum(1 for t in toks if LATIN.search(t))
    total = cyr + lat
    if total == 0:
        return "unknown"
    ratio = cyr / total
    if ratio >= 0.6:
        return "ru"
    if ratio <= 0.4:
        return "en"
    return "mixed"


def corpus_idf(docs):
    """Сглаженный idf по ВСЕМУ пулу сравнения → (таблица, вес незнакомого слова).

    docs - список списков токенов (черновик + все эталоны). Формула стандартная
    сглаженная: ln((1+N)/(1+df)) + 1. Слово из всех документов пула получает
    минимальный вес, слово из одного - максимальный.
    """
    df = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1
    n = len(docs) or 1
    table = {t: math.log((1 + n) / (1 + df[t])) + 1.0 for t in df}
    return table, math.log(1 + n) + 1.0


def tfidf_cosine(toks_a, toks_b, idf=None, unknown=1.0):
    """Косинус по TF-IDF. idf=None - построить по этой же паре (legacy-режим)."""
    ca, cb = Counter(toks_a), Counter(toks_b)
    if not ca or not cb:
        return 0.0
    if idf is None:
        vocab = set(ca) | set(cb)
        idf, unknown = {}, 1.0
        for term in vocab:
            df = (1 if term in ca else 0) + (1 if term in cb else 0)
            idf[term] = math.log((1 + 2) / (1 + df)) + 1.0  # сглаженный idf по паре
    va = {t: ca[t] * idf.get(t, unknown) for t in ca}
    vb = {t: cb[t] * idf.get(t, unknown) for t in cb}
    dot = sum(v * vb.get(t, 0.0) for t, v in va.items())
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def ngram_jaccard(toks_a, toks_b, n):
    def grams(toks):
        if len(toks) < n:
            return set()
        return set(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))
    ga, gb = grams(toks_a), grams(toks_b)
    if not ga or not gb:
        return 0.0
    union = len(ga | gb)
    return len(ga & gb) / union if union else 0.0


def matching_ngrams(toks_a, toks_b, n, limit=10):
    """Вернуть до limit совпадающих словесных n-грамм (для отчёта - что именно списано)."""
    if len(toks_a) < n or len(toks_b) < n:
        return []
    ga = set(tuple(toks_a[i:i + n]) for i in range(len(toks_a) - n + 1))
    gb = set(tuple(toks_b[i:i + n]) for i in range(len(toks_b) - n + 1))
    common = ga & gb
    return [" ".join(g) for g in list(common)[:limit]]


def word_jaccard(toks_a, toks_b):
    sa, sb = set(toks_a), set(toks_b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def top_terms(toks_a, toks_b, idf, unknown, limit=8):
    """Какие СОДЕРЖАТЕЛЬНЫЕ слова набрали похожесть - чтобы вердикт был читаемым."""
    ca, cb = Counter(toks_a), Counter(toks_b)
    va = {t: ca[t] * idf.get(t, unknown) for t in ca}
    vb = {t: cb[t] * idf.get(t, unknown) for t in cb}
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    if not na or not nb:
        return []
    вклад = {t: v * vb[t] / (na * nb) for t, v in va.items() if t in vb}
    return [{"term": t, "share": round(v, 4), "tf_draft": ca[t], "tf_ref": cb[t]}
            for t, v in sorted(вклад.items(), key=lambda x: -x[1])[:limit]]


def collect_reference_files(path):
    """Папка → список текстовых файлов внутри (рекурсивно). Файл → [файл]."""
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path):
        out = []
        for root, _, names in os.walk(path):
            for name in sorted(names):
                if name.lower().endswith(TEXT_EXTS) and not name.startswith("."):
                    out.append(os.path.join(root, name))
        return out
    return []


def analyse(draft_raw, refs, ngram_n, legacy=False):
    """Ядро проверки. refs = [(имя, сырой текст)] → словарь с метриками.

    Отдельная функция, потому что её же гоняет --selftest: тест обязан щупать
    ту самую математику, а не свою копию.
    """
    dt = tokens(strip_markup(draft_raw))
    dc = content_tokens(dt)
    готовые = []
    for имя, raw in refs:
        rt = tokens(strip_markup(raw))
        if len(rt) < 20:
            continue
        готовые.append((имя, rt, content_tokens(rt)))
    if not готовые:
        return None
    if legacy:
        idf, unknown = None, 1.0
    else:
        idf, unknown = corpus_idf([dc] + [c for _, _, c in готовые])

    per_file, worst = [], None
    for имя, rt, rc in готовые:
        if legacy:
            cos = tfidf_cosine(dt, rt) # формула ДО по решению автора: сырые токены, idf по паре
        else:
            cos = tfidf_cosine(dc, rc, idf, unknown)
        ngr = ngram_jaccard(dt, rt, ngram_n)    # n-граммы ВСЕГДА по полному тексту
        rec = {"file": имя, "lang": detect_lang(rt), "cosine": round(cos, 4),
               "ngram": round(ngr, 4), "_rt": rt, "_rc": rc}
        per_file.append(rec)
        if worst is None or cos > worst["cosine"]:
            worst = rec
    return {"dt": dt, "dc": dc, "per_file": per_file, "worst": worst,
            "idf": idf, "unknown": unknown, "corpus_docs": len(готовые) + 1}


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="originality-check.py",
        description="Проверка оригинальности черновика статьи: TF-IDF косинус по "
                    "содержательным словам + Jaccard по n-граммам против корпуса.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Пороги: config.yaml (tools.originality.*) → флаги CLI → дефолты "
               "(cosine 0.50, ngram 0.30, n=5). Коды выхода: 0=PASS, 1=FAIL, "
               "2=разные языки, 3=ошибка ввода.",
    )
    p.add_argument("draft", nargs="?",
                   help="файл черновика статьи (.md/.txt/.html и т.п.)")
    p.add_argument("corpus", nargs="?",
                   help="папка с уже опубликованными статьями ИЛИ один эталонный файл")
    p.add_argument("--config", default=None,
                   help="путь к config.yaml (по умолчанию ищется ./config.yaml)")
    p.add_argument("--max-cosine", type=float, default=None,
                   help="порог косинуса (перебивает config.yaml)")
    p.add_argument("--max-ngram", type=float, default=None,
                   help="порог Jaccard по n-граммам (перебивает config.yaml)")
    p.add_argument("--ngram-n", type=int, default=None,
                   help="длина словесной n-граммы (перебивает config.yaml)")
    p.add_argument("--legacy-cosine", action="store_true",
                   help="ДИАГНОСТИКА: считать косинус формулой ДО по решению автора (сырые токены "
                        "со служебными словами, idf по паре). Нужен, чтобы "
                        "воспроизвести «было/стало» на любой паре")
    p.add_argument("--json", action="store_true", help="вывод машинно-читаемым JSON")
    p.add_argument("--selftest", action="store_true",
                   help="прогнать встроенные кейсы (позитив, негатив, стоп-слова, "
                        "пустой текст) и выйти")
    return p.parse_args(argv)


def main():
    args = parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.draft or not args.corpus:
        sys.stderr.write("нужны два аргумента: <черновик> <корпус> "
                         "(либо флаг --selftest)\n")
        sys.exit(3)
    cfg = cfgmod.load_config(args.config or cfgmod.find_config())

    cosine_max = args.max_cosine if args.max_cosine is not None \
        else float(cfgmod.get(cfg, "tools.originality.max_cosine", DEFAULT_COSINE_MAX))
    ngram_max = args.max_ngram if args.max_ngram is not None \
        else float(cfgmod.get(cfg, "tools.originality.max_ngram", DEFAULT_NGRAM_MAX))
    ngram_n = args.ngram_n if args.ngram_n is not None \
        else int(cfgmod.get(cfg, "tools.originality.ngram_n", DEFAULT_NGRAM_N))

    try:
        draft_raw = read(args.draft)
    except OSError as e:
        sys.stderr.write(f"ошибка чтения черновика: {e}\n")
        sys.exit(3)

    ref_files = collect_reference_files(args.corpus)
    if not ref_files:
        sys.stderr.write(
            f"в '{args.corpus}' не найдено эталонных текстов "
            f"({', '.join(TEXT_EXTS)}). Нечего сравнивать.\n")
        sys.exit(3)

    refs = []
    for rf in ref_files:
        try:
            refs.append((rf, read(rf)))
        except OSError:
            continue

    a = analyse(draft_raw, refs, ngram_n, legacy=args.legacy_cosine)
    if a is None:
        sys.stderr.write("эталоны слишком короткие (< 20 слов) - сравнение невозможно\n")
        sys.exit(3)

    dt, dc, worst = a["dt"], a["dc"], a["worst"]
    if len(dt) < 50:
        sys.stderr.write("предупреждение: черновик < 50 слов - метрики ненадёжны\n")
    lang_d = detect_lang(dt)
    lang_r = worst["lang"]
    cross = (lang_d in ("ru", "en") and lang_r in ("ru", "en") and lang_d != lang_r)
    cosine, ngram = worst["cosine"], worst["ngram"]
    jacc = round(word_jaccard(dc, worst["_rc"]), 4)
    shared = matching_ngrams(dt, worst["_rt"], ngram_n)
    вклад = ([] if args.legacy_cosine
             else top_terms(dc, worst["_rc"], a["idf"], a["unknown"]))
    short = len(dc) < SHORT_TEXT_WORDS

    if cross:
        verdict, passed, code = "CROSS_LANG", None, 2
        note = (f"Черновик ({lang_d}) и ближайший эталон ({lang_r}) на разных языках. "
                f"Лексический косинус неинформативен. Структурную близость "
                f"(порядок мыслей, свои примеры) оценивает человек/агент, не скрипт.")
    else:
        passed = (cosine <= cosine_max) and (ngram <= ngram_max)
        verdict = "PASS" if passed else "FAIL"
        code = 0 if passed else 1
        if passed:
            note = "Оригинал: по содержательным словам разошёлся с корпусом."
        else:
            чем = (", ".join(t["term"] for t in вклад[:5]) if вклад else "-")
            note = (f"Клон-риск против '{os.path.basename(worst['file'])}': "
                    f"cosine {cosine} (порог ≤{cosine_max}) / ngram {ngram} "
                    f"(порог ≤{ngram_max}). Похожесть набрали: {чем}. "
                    f"Переписать угол, дать свою фактуру.")

    result = {
        "draft": args.draft,
        "draft_words": len(dt),
        "draft_content_words": len(dc),
        "short_text": short,
        "lang_draft": lang_d,
        "corpus_files": len(a["per_file"]),
        "corpus_idf_docs": (1 if args.legacy_cosine else a["corpus_docs"]),
        "formula": ("legacy (сырые токены, idf по паре)" if args.legacy_cosine
                    else "содержательные слова, idf по корпусу"),
        "closest_file": worst["file"],
        "lang_closest": lang_r,
        "cosine": cosine, "cosine_max": cosine_max,
        "ngram_jaccard": ngram, "ngram_max": ngram_max, "ngram_n": ngram_n,
        "word_jaccard": jacc,
        "cross_language": cross,
        "shared_ngrams": shared,
        "top_terms": вклад,
        "verdict": verdict, "passed": passed, "note": note,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Оригинальность: {verdict}")
        print(f"  ближайший эталон  : {os.path.basename(worst['file'])} "
              f"(из {len(a['per_file'])} файлов)")
        print(f"  cosine (TF-IDF)   : {cosine}  (порог ≤{cosine_max})"
              f"{'  [legacy-формула]' if args.legacy_cosine else ''}")
        print(f"  ngram-{ngram_n} jaccard   : {ngram}  (порог ≤{ngram_max})")
        print(f"  word jaccard      : {jacc}")
        print(f"  язык черн./эталон : {lang_d}/{lang_r}"
              f"{'  (РАЗНЫЕ ЯЗЫКИ)' if cross else ''}")
        print(f"  слов в черновике  : {len(dt)} (содержательных {len(dc)})"
              f"{'  ← короткий текст, косинус шумный' if short else ''}")
        if вклад and not passed:
            print("  похожесть набрали :")
            for t in вклад[:6]:
                print(f"     • {t['term']} - {100 * t['share']:.1f}% "
                      f"(в черновике {t['tf_draft']}, в эталоне {t['tf_ref']})")
        if shared and not passed:
            print("  совпавшие n-граммы:")
            for g in shared[:6]:
                print(f"     • …{g}…")
        print(f"  → {note}")
    sys.exit(code)


# ── селфтест ─────────────────────────────────────────────────────────────────
# Кейсы бьют ровно по тому, что чинили по решению автора: служебные слова не должны делать
# похожесть, содержательное совпадение - должно.
#
# 🔴 ПОЧЕМУ ФИКСТУРЫ ГЕНЕРИРУЮТСЯ, А НЕ НАПИСАНЫ АБЗАЦЕМ. Дефект живёт в
# ЧАСТОТНОМ ПРОФИЛЕ настоящей статьи: у боевого черновика 4029 слов, 1643
# уникальных, служебные слова 27% массы и сидят наверху (на 80, не 77, что 49),
# а каждое содержательное слово встречается 1-3 раза (максимум 30 на 1438
# уникальных). Короткий абзац, повторённый N раз, такой асимметрии НЕ создаёт:
# там частота содержательного слова равна частоте служебного, и на нём гейт
# зелёный при любой формуле - тест проходил бы, ничего не проверяя (пойман на
# первой версии этого селфтеста: legacy-косинус на рукописной фикстуре дал 0.03
# вместо боевых 0.6). Поэтому тексты собираются из пулов: словарь широкий,
# каждое содержательное слово редкое, служебные частые - профиль как у статьи.
# Генератор детерминированный (свой Random со своим зерном), тест воспроизводим.

# Основы двух РАЗНЫХ тем. Пересечения между темами нет: всё, что у такой пары
# текстов общего, - только служебные слова.
_ОСНОВЫ_ТЕМА = """
промпт поручение роль контекст задача формат тон запрет модель нейросеть ответ
черновик правка фактура пример шаблон заготовка структура абзац таблица список
пункт критерий приёмка проверка прогон итерация цепочка вывод ошибка источник
цитата ссылка датасет обучение генерация токен лимит квота подписка терминал
команда флаг ключ файл каталог репозиторий скрипт лог отладка редактор рассылка
пост письмо статья доклад лонгрид заголовок интонация словарь связка ритм
предложение длина объём сокращение адресат получатель клиент коллега аудитория
читатель голос стиль сервис чат вкладка браузер регистрация вход аккаунт профиль
настройка инструкция память проект папка вложение скриншот разметка сцена деталь
""".split()

_ОСНОВЫ_ЧУЖОЙ = """
ипотека ставка банк взнос срок договор страховка квартира жильё оценщик платёж
график погашение заёмщик залог субсидия льгота недвижимость метраж этаж
планировка ремонт отделка застройщик дольщик сделка нотариус регистратор выписка
обременение задаток аванс комиссия кредит переплата аннуитет остаток списание
справка доход поручитель созаёмщик одобрение отказ анкета скоринг новостройка
вторичка агент риелтор объявление показ торг скидка счётчик управляйка капремонт
квитанция долг пеня перепланировка кадастр обмер лифт подъезд двор парковка
""".split()

# Словоформы. Лемматизатора в инструменте нет и не будет: «нейросеть» и
# «нейросети» для него РАЗНЫЕ токены (видно в боевом замере). Значит и словарь
# фикстуры обязан быть словарём СЛОВОФОРМ, иначе профиль не тот.
_ФОРМЫ = ("", "а", "ы", "ов", "ом", "ами", "ах", "ный", "ного", "ности", "ную", "ать")


def _словарь(основы):
    return [о + ф for о in основы for ф in _ФОРМЫ]


# Скелеты: 8 содержательных слотов на 3-4 служебных слова. Так служебное слово
# набирает tf в сотню на весь текст, а каждая словоформа - две-три штуки. Это и
# есть асимметрия настоящей статьи, ради которой фикстура и строится.
_СКЕЛЕТЫ = (
    "{0} {1} и {2} {3} - это не {4} {5}, а {6} {7}",
    "{0} {1} без {2} {3} даёт {4} {5} и {6} {7}",
    "Не {0} {1}, а {2} {3} решает, каким выйдет {4} {5} у {6} {7}",
    "{0} {1} по {2} {3}: {4} {5}, {6} {7}",
    "Когда {0} {1} готов, {2} {3} и {4} {5} закрывают {6} {7}",
)


def _синт(словарь, n, seed, доля_общего=0.0, донор=None):
    """Текст с частотным профилем статьи: широкий словарь, редкие термины.

    доля_общего + донор задают «почти-копию»: часть содержательных слов берётся
    из донорского текста (та же фактура), остальное своё.
    """
    import random
    rnd = random.Random(seed)
    слова = []
    for _ in range(n * 8):
        if донор and rnd.random() < доля_общего:
            слова.append(rnd.choice(донор))
        else:
            слова.append(rnd.choice(словарь))
    строки = []
    for i in range(n):
        восьмёрка = слова[i * 8:i * 8 + 8]
        строки.append(_СКЕЛЕТЫ[rnd.randrange(len(_СКЕЛЕТЫ))].format(*восьмёрка))
    return ". ".join(строки) + "."


_СЛОВАРЬ_ТЕМА = _словарь(_ОСНОВЫ_ТЕМА)
_СЛОВАРЬ_ЧУЖОЙ = _словарь(_ОСНОВЫ_ЧУЖОЙ)
# половинки словаря темы: одна тема, но РАЗНОЕ наполнение - как две честные
# статьи одного кластера, у которых общий домен и своя фактура
_ПОЛОВИНА_A = _СЛОВАРЬ_ТЕМА[:int(len(_СЛОВАРЬ_ТЕМА) * 0.6)]
_ПОЛОВИНА_B = _СЛОВАРЬ_ТЕМА[int(len(_СЛОВАРЬ_ТЕМА) * 0.55):]

# базовый «донор»: статья по теме
_ТЕКСТ_A = _синт(_ПОЛОВИНА_A, 180, seed=1)
_СЛОВА_A = content_tokens(tokens(_ТЕКСТ_A))
# та же тема, СВОЁ наполнение (другая выборка словаря): обязан проходить
_ТЕКСТ_ПОЗИТИВ = _синт(_ПОЛОВИНА_B, 180, seed=77)
# ЧУЖАЯ тема теми же служебными словами: обязан проходить.
# Это и есть кейс, из-за которого чинили гейт - раньше такая пара давала 0.6+
_ТЕКСТ_СТОП = _синт(_СЛОВАРЬ_ЧУЖОЙ, 180, seed=5)
# почти-копия: 80% содержательных слов донора в другом порядке и других
# предложениях. Настоящая каннибализация без дословных совпадений - обязан краснеть
_ТЕКСТ_ПЕРЕФРАЗ = _синт(_ПОЛОВИНА_A, 180, seed=9, доля_общего=0.8, донор=_СЛОВА_A)


def selftest():
    случаи = []

    def проверить(имя, ок, деталь=""):
        случаи.append((имя, bool(ок), деталь))

    def прогон(draft, refs, n=5, legacy=False):
        a = analyse(draft, refs, n, legacy=legacy)
        if a is None:
            return None
        return a["worst"]["cosine"], a["worst"]["ngram"], a["worst"]["file"]

    порог = 0.60  # боевое число владельца, тест обязан щупать именно его

    # 1. позитив: та же тема своими словами
    поз = прогон(_ТЕКСТ_ПОЗИТИВ, [("донор", _ТЕКСТ_A)])
    проверить("позитив: та же тема своими словами проходит порог 0.60",
              поз[0] <= порог, f"cosine={поз[0]}")

    # 2. негатив: дословная копия
    коп = прогон(_ТЕКСТ_A, [("донор", _ТЕКСТ_A)])
    проверить("негатив: дословная копия = косинус около 1.0", коп[0] > 0.99,
              f"cosine={коп[0]}")
    проверить("негатив: дословная копия видна и по n-граммам", коп[1] > 0.9,
              f"ngram={коп[1]}")

    # 3. негатив: перефразированный пересказ (каннибализация без дословности)
    пер = прогон(_ТЕКСТ_ПЕРЕФРАЗ, [("донор", _ТЕКСТ_A)])
    проверить("негатив: перефразированный пересказ краснеет при 0.60",
              пер[0] > порог, f"cosine={пер[0]}")
    проверить("негатив: у пересказа дословных совпадений почти нет "
              "(ловит именно косинус, не n-граммы)", пер[1] < 0.20, f"ngram={пер[1]}")

    # 4. стоп-слова: чужая тема на том же языке
    стоп = прогон(_ТЕКСТ_СТОП, [("донор", _ТЕКСТ_A)])
    проверить("стоп-слова: чужая тема по-русски НЕ краснеет", стоп[0] <= порог,
              f"cosine={стоп[0]}")
    стоп_л = прогон(_ТЕКСТ_СТОП, [("донор", _ТЕКСТ_A)], legacy=True)
    проверить("стоп-слова: та же пара на legacy-формуле краснела "
              "(иначе чинить было нечего)", стоп_л[0] > порог,
              f"legacy cosine={стоп_л[0]}")
    проверить("стоп-слова: новая формула ниже legacy на той же паре",
              стоп[0] < стоп_л[0], f"{стоп[0]} vs {стоп_л[0]}")

    # 5. стоп-слова вычитаются только из косинуса, n-граммы считаются по полному
    #    тексту: иначе далёкие слова склеились бы в несуществующую цитату
    склейка = " ".join(["роль контекст задача формат тон запреты"] * 40)
    ск = прогон(склейка, [("донор", _ТЕКСТ_A)])
    проверить("n-граммы по полному тексту: набор терминов без связок "
              "НЕ даёт дословных совпадений", ск[1] < 0.05, f"ngram={ск[1]}")

    # 6. пустой и почти пустой вход
    проверить("пустой черновик: анализ отдаёт нули, а не падает",
              прогон("", [("донор", _ТЕКСТ_A)])[0] == 0.0)
    проверить("пустой корпус: анализ честно возвращает None (нечего сравнивать)",
              analyse(_ТЕКСТ_A, [], 5) is None)
    проверить("слишком короткий эталон (< 20 слов) отбрасывается",
              analyse(_ТЕКСТ_A, [("короткий", "три слова тут")], 5) is None)
    проверить("оба пустые: нулей достаточно, исключения нет",
              analyse("", [("пусто", "")], 5) is None)

    # 7. content_tokens: контракт фильтра
    проверить("content_tokens вычитает служебные слова",
              content_tokens(tokens("не на по что это как нейросеть")) == ["нейросеть"],
              str(content_tokens(tokens("не на по что это как нейросеть"))))
    проверить("content_tokens вычитает английские служебные",
              content_tokens(tokens("the of and to claude")) == ["claude"],
              str(content_tokens(tokens("the of and to claude"))))
    проверить("content_tokens вычитает чисто цифровые токены",
              content_tokens(tokens("2026 год 12 шагов")) == ["год", "шагов"],
              str(content_tokens(tokens("2026 год 12 шагов"))))
    проверить("content_tokens не трогает доменные слова "
              "(их вес снимает idf по корпусу, не список)",
              set(content_tokens(tokens("нейросеть промпт claude модель")))
              == {"нейросеть", "промпт", "claude", "модель"})

    # 8. idf по корпусу: слово из всех документов пула весит меньше редкого
    idf, _ = corpus_idf([["альфа", "бета"], ["альфа", "гамма"], ["альфа", "дельта"]])
    проверить("idf по корпусу: слово из всех документов весит меньше редкого",
              idf["альфа"] < idf["бета"], f"альфа={idf['альфа']:.3f} бета={idf['бета']:.3f}")
    проверить("idf по корпусу: у пары документов формула вырождается в прежнюю",
              abs(corpus_idf([["а", "б"], ["а", "в"]])[0]["а"]
                  - (math.log(3 / 3) + 1.0)) < 1e-9)

    # 9. разные языки: косинус неинформативен, решает человек
    en = ("The prompt consists of six blocks: role, context, task, format, tone "
          "and restrictions. Each block closes its own gap in the answer. ") * 8
    a_en = analyse(en, [("донор", _ТЕКСТ_A)], 5)
    проверить("разные языки: косинус около нуля (вердикт уходит человеку)",
              a_en["worst"]["cosine"] < 0.1, f"cosine={a_en['worst']['cosine']}")

    ок = 0
    for имя, good, деталь in случаи:
        print(f"  {'OK  ' if good else 'FAIL'} {имя}"
              + (f"  [{деталь}]" if деталь and not good else ""))
        ок += 1 if good else 0
    print(f"selftest originality-check: {ок}/{len(случаи)} прошло")
    return 0 if ок == len(случаи) else 1


if __name__ == "__main__":
    main()
