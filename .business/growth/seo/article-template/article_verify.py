#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""article_verify.py - гейт воспроизводимости страницы.

    python3 article_verify.py <slug>                     # источник определяется сам
    python3 article_verify.py <slug> --against /путь/index.html
    python3 article_verify.py <slug> --from spec --byte
    python3 article_verify.py --selftest

ЗАЧЕМ. Страница считается воспроизводимой, если её МОЖНО СОБРАТЬ ЗАНОВО ИЗ
ИСТОЧНИКА и получить то же самое. Пока такого гейта не было, руками правили
готовый index.html - и источник тихо расходился с выдачей. Живой прецедент
по решению автора: /guide-zarabotat-na-saytah/ уехал в прод с оглавлением на 14 пунктов
и нумерацией на 5 заголовках из 12 - оглавление кто-то дописал в HTML, а спека и
сборщик об этом не знали. Байтовый diff такое ловит поздно и шумно (у него
дрожит год в подвале и порядок CSS), поэтому здесь диффы СЕМАНТИЧЕСКИЕ:

  1. видимый текст - нормализация ОДНА на движок, берётся импортом из
     lastmod_registry.content_text (тот же текст, по которому считается
     content_sha и двигается lastmod: расходится он - расходится и дата);
  2. набор и порядок якорей оглавления;
  3. json.loads всех <script type="application/ld+json"> + сверка ключевых
     полей: headline, description, datePublished, dateModified;
  4. код-слово статьи (span.kw);
  5. счётчик инвайт-ссылок t.me;
  6. счётчик h2 с class="num" (разделы статьи по КАНОНУ 13 build_page).

Расхождение печатается предметно (что, где, чем отличается) и даёт exit 1.
--byte добавляет байтовое сравнение ИНФОРМАЦИОННО: оно не меняет вердикт, а
отвечает на вопрос «можно ли не передеплоивать».

Источник берётся так (--from auto):
  • draft.md с front-matter -> article_build -> spec -> build_page  (новые статьи)
  • иначе spec.json из папки статьи -> build_page                   (легаси-пачка,
    где spec несёт правки фикс-волн, а draft заморожен до них)
"""

import argparse
import difflib
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_PAGE = os.path.join(HERE, "build_page.py")
ARTICLE_BUILD = os.path.join(HERE, "article_build.py")
TESTS = os.path.join(HERE, "tests")
# ~/.business/growth/seo/article-template -> ~/.business/scripts/seo
SCRIPTS_SEO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                           "scripts", "seo")


def load_content_text():
    """Нормализация видимого текста - ОДНА на движок, импортом, не копией."""
    if SCRIPTS_SEO not in sys.path:
        sys.path.insert(0, SCRIPTS_SEO)
    try:
        import lastmod_registry
    except ImportError as e:
        sys.exit("ОШИБКА article_verify: не импортируется lastmod_registry из %s (%s). "
                 "Нормализация текста живёт там и копироваться сюда не должна."
                 % (SCRIPTS_SEO, e))
    return lastmod_registry.content_text


# ── съём признаков со страницы ───────────────────────────────────────────────

LD_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)
TOC_ASIDE_RE = re.compile(r'<aside class="toc-desktop".*?</aside>', re.S)
TOC_LI_RE = re.compile(r'<li><a href="#([^"]+)">(.*?)</a></li>', re.S)
KW_RE = re.compile(r'<span class="kw">(.*?)</span>', re.S)
TME_RE = re.compile(r'href="([^"]*t\.me/[^"]*)"', re.I)
H2_NUM_RE = re.compile(r'<h2[^>]*class="[^"]*\bnum\b[^"]*"[^>]*>', re.I)
H2_ANY_RE = re.compile(r"<h2\b", re.I)

LD_KEYS = ("headline", "description", "datePublished", "dateModified")


def _flat(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def ld_nodes(page):
    """Все узлы из всех ld+json, развёрнутые из @graph. Битый JSON - тоже находка."""
    nodes, broken = [], []
    for i, m in enumerate(LD_RE.finditer(page)):
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            broken.append("ld+json #%d не парсится: %s" % (i + 1, e))
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("@graph"), list):
                nodes.extend([x for x in it["@graph"] if isinstance(x, dict)])
            elif isinstance(it, dict):
                nodes.append(it)
    return nodes, broken


def ld_fields(page):
    nodes, broken = ld_nodes(page)
    out = {}
    for n in nodes:
        t = n.get("@type")
        types = t if isinstance(t, list) else [t]
        for k in LD_KEYS:
            if k in n and n[k] not in (None, ""):
                out.setdefault("%s|%s" % ("/".join(str(x) for x in types), k), str(n[k]))
    return out, broken, len(nodes)


def features(page, content_text):
    aside = TOC_ASIDE_RE.search(page)
    toc = [(a, _flat(b)) for a, b in TOC_LI_RE.findall(aside.group(0) if aside else "")]
    ld, broken, n_nodes = ld_fields(page)
    return {
        "text": content_text(page),
        "toc": toc,
        "ld": ld,
        "ld_broken": broken,
        "ld_nodes": n_nodes,
        "kw": [_flat(x) for x in KW_RE.findall(page)],
        "tme": TME_RE.findall(page),
        "h2_num": len(H2_NUM_RE.findall(page)),
        "h2_all": len(H2_ANY_RE.findall(page)),
    }


# ── сборка в песочницу ───────────────────────────────────────────────────────

def rebuild(article_dir, sandbox, source="auto", config=None):
    draft = os.path.join(article_dir, "draft.md")
    spec = os.path.join(article_dir, "spec.json")
    mode = source
    if mode == "auto":
        # источником считается ТОЛЬКО черновик с маркером контракта. Просто
        # «файл начинается с ---» не признак: 24 легаси-черновика корпуса несут
        # front-matter чужой схемы и собирались одноразовыми конвертерами - их
        # источник истины spec.json, а не draft.md
        mode = "draft" if os.path.exists(draft) and re.search(
            r"^engine:\s*article_build\s*$",
            open(draft, encoding="utf-8").read(4000), re.M) else "spec"
    if mode == "draft":
        if not os.path.exists(draft):
            sys.exit("ОШИБКА article_verify: нет %s" % draft)
        spec_out = os.path.join(sandbox, "spec.json")
        cmd = [sys.executable, ARTICLE_BUILD, draft, "-o", spec_out]
        if config:
            cmd += ["--config", config]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit("ОШИБКА article_verify: article_build упал\n" + (p.stdout + p.stderr).strip())
        spec_used = spec_out
    else:
        if not os.path.exists(spec):
            sys.exit("ОШИБКА article_verify: нет %s" % spec)
        spec_used = os.path.join(sandbox, "spec.json")
        shutil.copyfile(spec, spec_used)
    out = os.path.join(sandbox, "index.html")
    # build_page ходит по относительным путям спеки - собираем из папки статьи
    p = subprocess.run([sys.executable, BUILD_PAGE, spec_used, "-o", out],
                       capture_output=True, text=True, cwd=article_dir)
    if p.returncode != 0:
        sys.exit("ОШИБКА article_verify: build_page упал\n" + (p.stdout + p.stderr).strip())
    return mode, out


# ── дифф ─────────────────────────────────────────────────────────────────────

def first_divergence(a, b, width=90):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        return (i1,
                a[max(0, i1 - 40):i1 + width].replace("\n", "⏎"),
                b[max(0, j1 - 40):j1 + width].replace("\n", "⏎"))
    return None


def compare(new, ref, label_new="пересборка", label_ref="эталон"):
    """Возвращает список расхождений (пусто = семантик-PASS)."""
    bad = []

    if new["text"] != ref["text"]:
        d = first_divergence(ref["text"], new["text"])
        extra = ""
        if d:
            extra = ("\n      позиция %d\n      %s: …%s…\n      %s: …%s…"
                     % (d[0], label_ref, d[1], label_new, d[2]))
        bad.append("ВИДИМЫЙ ТЕКСТ разошёлся (знаков %s=%d, %s=%d)%s"
                   % (label_ref, len(ref["text"]), label_new, len(new["text"]), extra))

    if [x[0] for x in new["toc"]] != [x[0] for x in ref["toc"]]:
        only_ref = [x for x in [a for a, _ in ref["toc"]] if x not in [a for a, _ in new["toc"]]]
        only_new = [x for x in [a for a, _ in new["toc"]] if x not in [a for a, _ in ref["toc"]]]
        bad.append("ЯКОРЯ ОГЛАВЛЕНИЯ разошлись (%s=%d, %s=%d); только в %s: %s; только в %s: %s"
                   % (label_ref, len(ref["toc"]), label_new, len(new["toc"]),
                      label_ref, ", ".join(only_ref) or "-",
                      label_new, ", ".join(only_new) or "-"))
    else:
        for (a1, t1), (a2, t2) in zip(ref["toc"], new["toc"]):
            if t1 != t2:
                bad.append("ПОДПИСЬ ПУНКТА TOC #%s: %s «%s» vs %s «%s»"
                           % (a1, label_ref, t1, label_new, t2))

    for msg in ref["ld_broken"]:
        bad.append("JSON-LD %s: %s" % (label_ref, msg))
    for msg in new["ld_broken"]:
        bad.append("JSON-LD %s: %s" % (label_new, msg))
    keys = sorted(set(ref["ld"]) | set(new["ld"]))
    for k in keys:
        v1, v2 = ref["ld"].get(k), new["ld"].get(k)
        if v1 != v2:
            bad.append("JSON-LD %s: %s=%s vs %s=%s"
                       % (k, label_ref, json.dumps(v1, ensure_ascii=False)[:120],
                          label_new, json.dumps(v2, ensure_ascii=False)[:120]))

    if new["kw"] != ref["kw"]:
        bad.append("КОД-СЛОВО: %s=%s vs %s=%s"
                   % (label_ref, ref["kw"] or "нет", label_new, new["kw"] or "нет"))

    if len(new["tme"]) != len(ref["tme"]):
        bad.append("ИНВАЙТ-ССЫЛКИ t.me: %s=%d vs %s=%d"
                   % (label_ref, len(ref["tme"]), label_new, len(new["tme"])))
    elif sorted(new["tme"]) != sorted(ref["tme"]):
        bad.append("ИНВАЙТ-ССЫЛКИ t.me: одинаковое число, разные адреса (%s)"
                   % ", ".join(sorted(set(ref["tme"]) ^ set(new["tme"]))[:4]))

    if new["h2_num"] != ref["h2_num"] or new["h2_all"] != ref["h2_all"]:
        bad.append("h2.num (разделы статьи): %s=%d из %d h2 vs %s=%d из %d h2"
                   % (label_ref, ref["h2_num"], ref["h2_all"],
                      label_new, new["h2_num"], new["h2_all"]))
    return bad


def verify(article_dir, against, source="auto", config=None, byte=False, keep=False):
    content_text = load_content_text()
    if not os.path.exists(against):
        sys.exit("ОШИБКА article_verify: нет эталона %s" % against)
    sandbox = tempfile.mkdtemp(prefix="article_verify_")
    try:
        mode, built = rebuild(article_dir, sandbox, source, config)
        new_raw = open(built, encoding="utf-8").read()
        ref_raw = open(against, encoding="utf-8").read()
        bad = compare(features(new_raw, content_text), features(ref_raw, content_text))

        print("── article_verify ──")
        print("  источник      : %s (%s)" % (mode, article_dir))
        print("  эталон        : %s (%d КБ)" % (against, len(ref_raw.encode()) // 1024))
        print("  песочница     : %s (%d КБ)" % (built, len(new_raw.encode()) // 1024))
        if byte:
            same = new_raw == ref_raw
            print("  байт-в-байт   : %s%s"
                  % ("ДА" if same else "НЕТ",
                     "" if same else " (информационно: семантика решает вердикт, "
                                     "байтовая разница = повод передеплоить)"))
            if not same:
                dl = list(difflib.unified_diff(ref_raw.split("\n"), new_raw.split("\n"),
                                               "эталон", "пересборка", n=0, lineterm=""))
                print("  строк в diff  : %d" % max(0, len(dl) - 2))
        if bad:
            print("  ВЕРДИКТ       : FAIL, расхождений %d" % len(bad))
            for i, b in enumerate(bad, 1):
                print("   %d) %s" % (i, b))
            return 1
        print("  ВЕРДИКТ       : PASS (текст, TOC, JSON-LD, код-слово, t.me, h2.num сходятся)")
        return 0
    finally:
        if keep:
            print("  песочница оставлена: %s" % sandbox)
        else:
            # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
            pass


def resolve_work(work):
    if work:
        return os.path.expanduser(work)
    env = os.environ.get("WORK")
    if env:
        return os.path.expanduser(env)
    cfg = os.path.expanduser("~/.claude/skills/lead-magnit/config.md")
    if os.path.exists(cfg):
        m = re.search(r"^\s*path:\s*(\S+)\s*$", open(cfg, encoding="utf-8").read(),
                      re.M)
        if m:
            return os.path.expanduser(m.group(1))
    sys.exit("ОШИБКА article_verify: не найден рабочий каталог статей "
             "(передай --work или задай WORK)")


# ── selftest ─────────────────────────────────────────────────────────────────

def selftest(config=None):
    checks, failed = [], 0

    def ok(name, cond, detail=""):
        nonlocal failed
        checks.append(("OK  " if cond else "FAIL", name, detail))
        if not cond:
            failed += 1

    content_text = load_content_text()
    fixture = os.path.join(TESTS, "fixture-draft.md")
    if not os.path.exists(fixture):
        sys.exit("ОШИБКА selftest: нет фикстуры %s" % fixture)

    root = tempfile.mkdtemp(prefix="article_verify_selftest_")
    try:
        # боевая карта инвайтов знает БОЕВЫЕ слаги, слага фикстуры в ней нет и быть
        # не должно - без подмены карты селфтест падал на первом же прогоне
        # («слага guide-fixture нет в карте инвайтов»), то есть мерил конфиг автора
        # вместо контракта гейта. Подмена - тем же приёмом, что у article_build
        import article_build
        config = article_build._selftest_config_file(config, root)
        art = os.path.join(root, "guide-fixture")
        os.makedirs(art)
        shutil.copyfile(fixture, os.path.join(art, "draft.md"))

        # эталон = первая сборка из того же черновика
        sb = os.path.join(root, "sb0")
        os.makedirs(sb)
        mode, built = rebuild(art, sb, "auto", config)
        ok("источник определён как draft (front-matter есть)", mode == "draft", mode)
        ref = os.path.join(art, "index.html")
        shutil.copyfile(built, ref)

        # ── позитив: round-trip ──
        rc = verify(art, ref, "auto", config, byte=True)
        ok("round-trip на фикстуре: PASS", rc == 0, "exit=%s" % rc)

        page = open(ref, encoding="utf-8").read()
        f = features(page, content_text)
        ok("признаки сняты: h2.num=%d, TOC=%d, ld-узлов=%d"
           % (f["h2_num"], len(f["toc"]), f["ld_nodes"]),
           f["h2_num"] == 4 and len(f["toc"]) == 6 and f["ld_nodes"] > 0)

        # ── негативы: порча эталона по каждой оси ──
        cases = [
            ("видимый текст",
             lambda s: s.replace("markdown несёт текст и структуру",
                                 "markdown несёт совсем другое", 1),
             "ВИДИМЫЙ ТЕКСТ"),
            ("якоря оглавления",
             lambda s: s.replace('<li><a href="#svoy-yakor">', '<li><a href="#chuzhoy">'),
             "ЯКОРЯ ОГЛАВЛЕНИЯ"),
            ("JSON-LD dateModified",
             lambda s: s.replace('"dateModified": "2026-08-12"',
                                 '"dateModified": "2026-08-01"'),
             "JSON-LD"),
            ("код-слово",
             lambda s: s.replace('<span class="kw">ФИКСТУРА</span>',
                                 '<span class="kw">ДРУГОЕ</span>'),
             "КОД-СЛОВО"),
            ("h2.num (ручная правка класса в HTML)",
             lambda s: s.replace('<h2 class="num">', "<h2>", 2),
             "h2.num"),
        ]
        # 🔴 по решению автора: ось КОД-СЛОВА мертва по построению, и молчать об этом нельзя.
        # Волна по решению автора вывела блок код-слова из канона (article_build.py.bak-codeword-
        # removal-20260820: было 18 упоминаний class="kw", осталось 3 нерабочих), и на
        # по решению автора span.kw нет НИ НА ОДНОЙ из 141 страницы корпуса. Негатив по этой оси
        # физически нечем испортить. Прежний код печатал по нему FAIL «текст не
        # изменился» - то есть красил селфтест сообщением не про то. Теперь: если в
        # эталоне нет span.kw, случай ПРОПУСКАЕТСЯ С НАЗВАННОЙ ПРИЧИНОЙ, а не тихо и
        # не ложным провалом. Вернётся код-слово в канон - вернётся и негатив.
        ref_html = open(ref, encoding="utf-8").read()
        if not KW_RE.search(ref_html):
            cases = [c for c in cases if "код-слово" not in c[0]]
            checks.append(("SKIP", "негатив «код-слово»: в собранной странице нет span.kw "
                                   "(блок код-слова выведен из канона волной по решению автора) - "
                                   "ось не проверяется, портить нечего", ""))
        for name, mangle, needle in cases:
            broken = os.path.join(root, "broken.html")
            src = open(ref, encoding="utf-8").read()
            out = mangle(src)
            if out == src:
                ok("негатив «%s»: порча применилась" % name, False, "текст не изменился")
                continue
            open(broken, "w", encoding="utf-8").write(out)
            # сверяем ЧИСТУЮ пересборку с ИСПОРЧЕННЫМ эталоном
            bad = compare(features(src, content_text), features(out, content_text))
            hit = any(needle in b for b in bad)
            ok("негатив «%s»: гейт видит расхождение по оси" % name, hit,
               "; ".join(bad)[:160] if not hit else "")

        # ── негатив: испорченный эталон роняет exit ──
        broken = os.path.join(root, "broken-final.html")
        open(broken, "w", encoding="utf-8").write(
            open(ref, encoding="utf-8").read().replace('<h2 class="num">', "<h2>", 2))
        rc_bad = verify(art, broken, "auto", config)
        ok("испорченный эталон: FAIL c exit 1", rc_bad == 1, "exit=%s" % rc_bad)

        # ── негатив: битый ld+json замечен ──
        nodes, brk = ld_nodes('<script type="application/ld+json">{битый</script>')
        ok("битый ld+json пойман, а не проглочен", bool(brk))
    finally:
        # чистка своей временной папки снята по решению автора: закон владельца «ничего не удалять, пусть лежит», временный каталог подметает система
        pass

    print("── selftest article_verify.py ──")
    for st, name, detail in checks:
        print("  %s %s%s" % (st, name, ("  <- " + detail) if detail and st == "FAIL" else ""))
    print("итог: %d проверок, провалов %d" % (len(checks), failed))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description="гейт воспроизводимости страницы")
    ap.add_argument("slug", nargs="?", help="папка статьи в рабочем каталоге")
    ap.add_argument("--work", help="рабочий каталог статей (иначе $WORK или config.md)")
    ap.add_argument("--against", help="эталонный HTML (по умолчанию <work>/<slug>/index.html)")
    ap.add_argument("--from", dest="source", choices=("auto", "draft", "spec"), default="auto")
    ap.add_argument("--config", help="config.md скилла lead-magnit")
    ap.add_argument("--byte", action="store_true", help="байтовое сравнение (информационно)")
    ap.add_argument("--keep", action="store_true", help="не удалять песочницу")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest(a.config)
    if not a.slug:
        ap.error("укажи slug статьи или --selftest")
    art = a.slug if os.path.isdir(a.slug) else os.path.join(resolve_work(a.work), a.slug)
    if not os.path.isdir(art):
        sys.exit("ОШИБКА article_verify: нет папки статьи %s" % art)
    against = a.against or os.path.join(art, "index.html")
    return verify(art, against, a.source, a.config, a.byte, a.keep)


if __name__ == "__main__":
    sys.exit(main())
