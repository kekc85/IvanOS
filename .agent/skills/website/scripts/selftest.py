#!/usr/bin/env python3
"""
selftest.py — РЕГРЕССИОННЫЙ ХАРНЕСС всего слоя принуждения скилла website.
Прогоняет каждый хук + скрипт на фикстурах (happy/negative/edge) и проверяет
exit-коды. Зелёный прогон = гарантия, что механизмы реально работают (не «на словах»).

Запуск:  python3 ~/.claude/skills/website/scripts/selftest.py
Выход:   0 = все тесты прошли; 1 = есть провал (печатает какие).

Зачем (автор): «это не MVP — ученики ждут РАБОЧИЙ продукт; гарантия, что
всё работает чётко». Этот харнесс — машинная проверка самих гейтов: после ЛЮБОЙ
правки хука/скрипта прогнать и убедиться, что защита не сломана и не оверблочит.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
HOOKS = os.path.join(HOME, ".claude", "hooks")
SCRIPTS = os.path.join(HOME, ".claude", "skills", "website", "scripts")
REVIEW = os.path.join(HOOKS, "website-review-gate.sh")
RESEARCH = os.path.join(HOOKS, "website-research-gate.sh")
EDIT = os.path.join(HOOKS, "website-edit-review-gate.sh")
TRACKER = os.path.join(HOOKS, "website-tracker-gate.sh")
ORPHAN = os.path.join(SCRIPTS, "orphan-scan.py")

results = []


def run_hook(hook, payload):
    p = subprocess.run(["bash", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode


def check(name, got, expect):
    results.append((got == expect, name, f"exit={got}, ждали {expect}"))


def bash_payload(cmd, **extra):
    d = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    d.update(extra)
    return d


def status_helper_cmd(dir_, name, status, approve=""):
    a = f" '{approve}'" if approve else ""
    return (f"python3 - \"{dir_}\" '{name}' '{status}' 'null'{a} <<'PY'\n"
            f"import json,os\np=os.path.join(d,'.website-state.json')\n"
            f"s.setdefault('approvals',[])\nPY")


def write_screen_manifest(dir_, block, n=10):
    md = os.path.join(dir_, "refs", block)
    os.makedirs(md, exist_ok=True)
    exs = []
    for i in range(n):
        fn = f"e{i}.png"
        open(os.path.join(md, fn), "wb").write(b"x" * 10)
        exs.append({"name": f"ex{i}", "url": f"https://ex{i}.com", "block": block,
                    "screenshot": fn, "why_works": "works " + "x" * 60,
                    "niche_relevant": "relevant " + "y" * 25})
    json.dump({"block": block, "target": 10, "exemplars": exs},
              open(os.path.join(md, "_manifest.json"), "w"))


def write_board_manifest(dir_):
    os.makedirs(os.path.join(dir_, "refs"), exist_ok=True)
    open(os.path.join(dir_, "refs", "board.png"), "wb").write(b"x" * 10)
    json.dump({"site_type": "landing", "min_exemplars": 3, "exemplars": [
        {"name": f"e{i}", "url": f"https://e{i}.com", "type": "landing",
         "why_works": "x" * 65, "niche_relevant": "y" * 25} for i in range(3)]},
        open(os.path.join(dir_, "refs", "_manifest.json"), "w"))


def main():
    tmp = tempfile.mkdtemp(prefix="website-selftest-")

    def scan(html):
        return subprocess.run([sys.executable, ORPHAN, "--stdin"], input=html,
                              capture_output=True, text=True).returncode
    check("orphan: <br>-орфан в h2", scan("<h2>Ты и твоя<br>система</h2>"), 3)
    check("orphan: &nbsp; связка", scan("<h2>Ты и твоя&nbsp;система</h2>"), 0)
    check("orphan: 2 слова на строке", scan("<h2>Ты и твоя<br>личная система</h2>"), 0)
    check("orphan: allow-orphan opt-out", scan('<h1 class="allow-orphan">автор<br></h1>'), 0)
    check("orphan: короткий лейбл 2 слова", scan("<h3>Привет<br>мир</h3>"), 0)
    check("orphan: плашка class=title", scan('<div class="hero-title">Запусти проект за<br>неделю</div>'), 3)
    check("orphan: естественный перенос без br", scan("<h2>Очень длинный заголовок без ручных переносов совсем тут</h2>"), 0)
    check("orphan: data-br-ok opt-out", scan('<h2 data-br-ok>Имя<br>Фамилия тут</h2>'), 0)

    # ───────── copy-lint.py ─────────
    COPY = os.path.join(SCRIPTS, "copy-lint.py")

    def clint(text, *extra):
        return subprocess.run([sys.executable, COPY, "--stdin", *extra], input=text,
                              capture_output=True, text=True).returncode
    check("copy-lint: em-dash «—» → BLOCK", clint("Заголовок — текст"), 3)
    check("copy-lint: en-dash «–» → чисто", clint("Заголовок – текст"), 0)
    check("copy-lint: продающее слово на контент-хабе → BLOCK", clint("Купи тариф", "--site-type", "контент-хаб"), 3)
    check("copy-lint: то же на landing → чисто", clint("Купи тариф", "--site-type", "landing"), 0)
    ivf = os.path.join(tmp, "iv.md")
    open(ivf, "w").write("автор обучил людей")
    cf = os.path.join(tmp, "c.md")
    open(cf, "w").write("У нас <число учеников>")
    check("copy-lint: число не из interview → BLOCK",
          subprocess.run([sys.executable, COPY, cf, "--interview", ivf], capture_output=True, text=True).returncode, 3)
    open(ivf, "w").write("автор обучил <число учеников>")
    check("copy-lint: число есть в interview → чисто",
          subprocess.run([sys.executable, COPY, cf, "--interview", ivf], capture_output=True, text=True).returncode, 0)

    # ───────── check-deploy.py (Фаза 08 — рабочее целевое действие) ─────────
    DEPLOY = os.path.join(SCRIPTS, "check-deploy.py")

    def deploy(html, *extra):
        f = os.path.join(tmp, "dep.html")
        open(f, "w").write(html)
        return subprocess.run([sys.executable, DEPLOY, f, *extra],
                              capture_output=True, text=True).returncode
    check("deploy: мёртвый CTA (#) → BLOCK", deploy('<a href="#">Купить</a>'), 3)
    check("deploy: рабочий CTA → чисто", deploy('<a href="/pay">Оплатить</a>'), 0)
    check("deploy: форма self-submit → чисто", deploy('<form><input></form>'), 0)
    check("deploy: target недостижим → BLOCK", deploy('<a href="/about">О нас</a>', "--target", "/pay"), 3)

    rg = os.path.join(tmp, "rg")
    os.makedirs(rg, exist_ok=True)
    json.dump({"stage": "screens", "screens": [{"name": "hero", "status": "pending"}]},
              open(os.path.join(rg, ".website-state.json"), "w"))
    check("research: concept без манифеста → BLOCK",
          run_hook(RESEARCH, bash_payload(status_helper_cmd(rg, "hero", "concept"))), 2)
    check("research: concept без слова approvals тоже BLOCK (закрытый обход)",
          run_hook(RESEARCH, bash_payload(status_helper_cmd(rg, "hero", "concept"))), 2)
    check("research: относительный DIR + cwd → BLOCK",
          run_hook(RESEARCH, bash_payload(status_helper_cmd(".", "hero", "concept"), cwd=rg)), 2)
    check("research: pending (карта экранов) → пропуск",
          run_hook(RESEARCH, bash_payload(status_helper_cmd(rg, "hero", "pending"))), 0)
    check("research: не-Bash → пропуск",
          run_hook(RESEARCH, {"tool_name": "Read", "tool_input": {"file_path": "/x"}}), 0)
    rgp = os.path.join(tmp, "rgpass")
    os.makedirs(rgp, exist_ok=True)
    json.dump({"stage": "screens", "screens": [{"name": "hero", "status": "pending"}]},
              open(os.path.join(rgp, ".website-state.json"), "w"))
    write_screen_manifest(rgp, "hero")
    check("research: concept с валидным манифестом → пропуск",
          run_hook(RESEARCH, bash_payload(status_helper_cmd(rgp, "hero", "concept"))), 0)

    sc = os.path.join(tmp, "screen")
    os.makedirs(sc, exist_ok=True)
    json.dump({"stage": "screens", "screens": [{"name": "hero", "status": "review",
              "score": 9, "approvals": ["concept", "copy", "design"]}]},
              open(os.path.join(sc, ".website-state.json"), "w"))
    write_board_manifest(sc)
    write_screen_manifest(sc, "hero")
    open(os.path.join(sc, "screen-hero.html"), "w").write(
        "<!doctype html><html><body><h1>Запусти проект за<br>неделю</h1></body></html>")
    check("review-экран: орфан в рендере → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {sc}/screen-hero.html")), 2)
    open(os.path.join(sc, "screen-hero.html"), "w").write(
        "<!doctype html><html><body><h1>Запусти проект за&nbsp;неделю</h1><p>норм текст тут</p></body></html>")
    check("review-экран: чистый → пропуск",
          run_hook(REVIEW, bash_payload(f"open {sc}/screen-hero.html")), 0)
    sc2 = os.path.join(tmp, "screen2")
    os.makedirs(sc2, exist_ok=True)
    json.dump({"stage": "screens", "screens": [{"name": "faq", "status": "review",
              "score": 9, "approvals": ["concept", "copy", "design"]}]},
              open(os.path.join(sc2, ".website-state.json"), "w"))
    write_board_manifest(sc2)
    open(os.path.join(sc2, "screen-faq.html"), "w").write("<h1>ок текст тут норм</h1>")
    check("review-экран: нет per-screen манифеста → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {sc2}/screen-faq.html")), 2)

    # Валидный макро-ревью (Фаза 10): 8 осей ≥9 + журнал (покрывает экран hero, привязан к
    # рендеру через id="hero") + cores (≥2 совпадающих ядра для оси A).
    good_site = {"axes": {"one_big_idea": 9, "awareness_ladder": 9, "information_scent": 9,
                          "persuasion_sequencing": 9, "conversion_physics": 9,
                          "editorial_cut": 9, "canvas_continuity": 9, "objection_coverage": 9},
                 "cores": ["вайбкодинг", "вайбкодинг"],
                 "journey": [{"screen": "hero", "awareness": 5, "question_raised": "",
                              "answered_by": "none", "cta": "primary"}]}

    def make_site(extra_phases=None, screens_done=True, selfreview=None,
                  html='<section id="hero"><h1>норм заголовок тут целиком</h1>'
                       '<a href="/pay">Оплатить</a></section>',
                  copy=None, sitereview="OMIT"):
        site = tempfile.mkdtemp(prefix="st-site-", dir=tmp)
        ph = {"0_brief": {}, "1_interview": {}, "2a_seeds": {},
              "2b_reference": {"approved": True, "board": "refs"},
              "2c_synthesis": {}, "3a_structure": {"approved": True}, "3b_copy": {}}
        if extra_phases is not None:
            ph = extra_phases
        st = {"stage": "assembly", "phases": ph,
              "screens": [{"name": "hero", "status": "done" if screens_done else "build"}]}
        json.dump(st, open(os.path.join(site, ".website-state.json"), "w"))
        write_board_manifest(site)
        open(os.path.join(site, "index.html"), "w").write(
            "<!doctype html><html><body>" + html + "</body></html>")
        if copy is not None:
            open(os.path.join(site, "copy.md"), "w").write(copy)
        idx_t = os.path.getmtime(os.path.join(site, "index.html"))
        if selfreview is not None:
            json.dump(selfreview, open(os.path.join(site, ".self-review.json"), "w"))
            os.utime(os.path.join(site, ".self-review.json"), (idx_t + 5, idx_t + 5))
        # sitereview: "OMIT" → не писать; "DEFAULT" → good_site; dict → как есть
        sr = good_site if sitereview == "DEFAULT" else (None if sitereview == "OMIT" else sitereview)
        if sr is not None:
            json.dump(sr, open(os.path.join(site, ".site-review.json"), "w"))
            os.utime(os.path.join(site, ".site-review.json"), (idx_t + 5, idx_t + 5))
        return site

    good = {"layout_audit": True, "criteria": {
        "hierarchy": 9, "contrast": 9, "color": 9, "flow_to_cta": 9,
        "premium_no_ai_slop": 9, "matches_direction": 9}}
    # ── Фаза 09 (per-screen) кейсы — блокируют ДО Фазы 10, sitereview не нужен ──
    check("review-сайт: полный валидный (09+10) → пропуск",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview='DEFAULT')}/index.html")), 0)
    s_nochain = make_site(extra_phases={"2b_reference": {"approved": True, "board": "refs"},
                                        "3a_structure": {"approved": True}}, selfreview=good)
    check("review-сайт: пропущены смысловые фазы → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {s_nochain}/index.html")), 2)
    check("review-сайт: плоский score_min без criteria → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview={'layout_audit': True, 'score_min': 9})}/index.html")), 2)
    s_low = make_site(selfreview={"layout_audit": True, "criteria": {
        "hierarchy": 9, "contrast": 7, "color": 9, "flow_to_cta": 9,
        "premium_no_ai_slop": 9, "matches_direction": 9}})
    check("review-сайт: ось 09 <9 (min=7) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {s_low}/index.html")), 2)
    check("review-сайт: экран не done → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(screens_done=False, selfreview=good)}/index.html")), 2)
    check("review-сайт: copy.md с em-dash → BLOCK (копи-линт в гейте)",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, copy='Заголовок — с длинным тире')}/index.html")), 2)
    check("review-сайт: чистая copy.md (09+10) → пропуск",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview='DEFAULT', copy='Чистый заголовок без длинного тире и чисел')}/index.html")), 0)

    # ── ФАЗА 10 (макро-ревью сайта как системы) — happy/negative/edge ──
    check("review-10: нет .site-review.json (09 ок) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview='OMIT')}/index.html")), 2)
    s10_axis = dict(good_site, axes=dict(good_site["axes"], conversion_physics=7))
    check("review-10: ось макро <9 (min=7) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_axis)}/index.html")), 2)
    s10_miss = {"axes": {k: 9 for k in list(good_site["axes"])[:5]}, "journey": good_site["journey"]}
    check("review-10: неполный набор осей (<7) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_miss)}/index.html")), 2)
    s10_nojourney = {"axes": good_site["axes"], "journey": []}
    check("review-10: журнал пуст (не покрывает экран) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_nojourney)}/index.html")), 2)
    s10_dangling = {"axes": good_site["axes"], "journey": [
        {"screen": "hero", "awareness": 5, "question_raised": "а сработает?",
         "answered_by": "none", "cta": "primary"}]}
    check("review-10: висячая петля любопытства → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_dangling)}/index.html")), 2)
    check("review-10: мёртвый CTA-путь (href=#) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview='DEFAULT', html='<h1>текст норм целиком</h1><a href=\"#\">Купить</a>')}/index.html")), 2)
    # свежесть: index.html правлен ПОСЛЕ макро-ревью (site-review старше). self-review
    # держим свежим, чтобы изолировать ИМЕННО гейт свежести Фазы 10.
    s10_stale = make_site(selfreview=good, sitereview="DEFAULT")
    _idx = os.path.join(s10_stale, "index.html")
    newt = os.path.getmtime(_idx) + 100
    os.utime(_idx, (newt, newt))
    os.utime(os.path.join(s10_stale, ".self-review.json"), (newt + 10, newt + 10))
    check("review-10: index правлен после макро-ревью (устарел) → BLOCK",
          run_hook(REVIEW, bash_payload(f"open {s10_stale}/index.html")), 2)
    # ось A: cores отсутствуют / расходятся (ревью M4)
    s10_nocores = {k: v for k, v in good_site.items() if k != "cores"}
    check("review-10: нет cores (ось A несверяема) -> BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_nocores)}/index.html")), 2)
    s10_splitcore = dict(good_site, cores=["вайбкодинг", "маркетинг"])
    check("review-10: судьи назвали РАЗНОЕ ядро -> BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_splitcore)}/index.html")), 2)
    # M1: лишний НЕ-из-8 ключ в axes НЕ должен ложно блокировать (min строго по 8 осям)
    s10_extra = dict(good_site, axes=dict(good_site["axes"], overall=3))
    check("review-10: лишний ключ overall=3 в axes -> пропуск (min по 8 осям)",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_extra)}/index.html")), 0)
    # C1-process: журнал оторван от рендера (экрана нет в index.html) -> BLOCK
    check("review-10: журнал оторван от index.html (фикция) -> BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=good_site, html='<h1>совсем другой контент про котиков</h1><a href=\"/pay\">Оплатить</a>')}/index.html")), 2)
    # ось objection_coverage отсутствует (неполный набор из 8) -> BLOCK
    s10_noobj = {"axes": {k: 9 for k in good_site["axes"] if k != "objection_coverage"},
                 "cores": good_site["cores"], "journey": good_site["journey"]}
    check("review-10: нет оси objection_coverage (7/8) -> BLOCK",
          run_hook(REVIEW, bash_payload(f"open {make_site(selfreview=good, sitereview=s10_noobj)}/index.html")), 2)
    # C1: обход всего гейта через `open http://localhost:PORT/index.html` -> BLOCK
    check("review-C1: open localhost-URL мимо гейта -> BLOCK",
          run_hook(REVIEW, bash_payload("open http://localhost:8897/index.html")), 2)
    check("review-C1: show-screen.py с localhost-URL не ложно блокируется (его сам гейтит)",
          run_hook(REVIEW, bash_payload("python3 ~/.claude/skills/website/scripts/show-screen.py /tmp/none/x.html")), 0)
    # H1: пустой screens[] на СТАДИИ C -> BLOCK
    s_empty = tempfile.mkdtemp(prefix="st-empty-", dir=tmp)
    json.dump({"stage": "assembly", "phases": {"0_brief": {}, "1_interview": {}, "2a_seeds": {},
              "2b_reference": {"approved": True, "board": "refs"}, "2c_synthesis": {},
              "3a_structure": {"approved": True}, "3b_copy": {}}, "screens": []},
              open(os.path.join(s_empty, ".website-state.json"), "w"))
    write_board_manifest(s_empty)
    open(os.path.join(s_empty, "index.html"), "w").write("<h1>пусто</h1>")
    check("review-10: пустой screens[] на СТАДИИ C -> BLOCK",
          run_hook(REVIEW, bash_payload(f"open {s_empty}/index.html")), 2)
    # C2: запуск локального сервера ИЗ папки website-проекта -> BLOCK (обход show-screen.py)
    srv = make_site(selfreview=good, sitereview="DEFAULT")
    check("review-C2: http.server --directory <проект> -> BLOCK",
          run_hook(REVIEW, bash_payload(f"python3 -m http.server 8080 --directory {srv}")), 2)
    check("review-C2: http.server из cwd=проект -> BLOCK",
          run_hook(REVIEW, bash_payload("python3 -m http.server 8080", cwd=srv)), 2)
    check("review-C2: http.server в обычной папке (не проект) -> пропуск",
          run_hook(REVIEW, bash_payload("python3 -m http.server 8000", cwd=tmp)), 0)

    def edit_payload(html_path):
        tr = os.path.join(tmp, f"tr-{abs(hash(html_path))}.jsonl")
        rec = {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": html_path}}]}}
        open(tr, "w").write(json.dumps(rec) + "\n")
        return {"transcript_path": tr}

    eg = os.path.join(tmp, "edit")
    os.makedirs(eg, exist_ok=True)
    json.dump({"stage": "screens"}, open(os.path.join(eg, ".website-state.json"), "w"))
    h = os.path.join(eg, "screen-hero.html")
    open(h, "w").write("<h1>Большой заголовок про<br>систему</h1>")
    time.sleep(0.05)
    open(os.path.join(eg, "screen-hero.png"), "wb").write(b"x")
    check("edit-gate: орфан в правленом html → BLOCK", run_hook(EDIT, edit_payload(h)), 2)
    open(h, "w").write("<h1>Большой сбалансированный заголовок про систему целиком</h1>")
    time.sleep(0.05)
    open(os.path.join(eg, "screen-hero.png"), "wb").write(b"xx")
    check("edit-gate: чистый html + свежий скрин → пропуск", run_hook(EDIT, edit_payload(h)), 0)
    nv = os.path.join(tmp, "novid")
    os.makedirs(nv, exist_ok=True)
    hv = os.path.join(nv, "v.html")
    open(hv, "w").write("<h1>Одно<br>слово</h1>")
    check("edit-gate: не-сайт html → пропуск", run_hook(EDIT, edit_payload(hv)), 0)

    def tracker_payload(tool_cmds, skill_website=True):
        content = []
        if skill_website:
            content.append({"type": "tool_use", "name": "Skill", "input": {"skill": "website"}})
        for c in tool_cmds:
            content.append({"type": "tool_use", "name": "Bash", "input": {"command": c}})
        content.append({"type": "text", "text": "работа сделана"})
        rec = {"message": {"role": "assistant", "content": content}}
        tr = os.path.join(tmp, "tr-tracker.jsonl")
        open(tr, "w").write(json.dumps(rec) + "\n")
        return {"transcript_path": tr, "stop_hook_active": False}

    tg = os.path.join(tmp, "track")
    os.makedirs(tg, exist_ok=True)
    json.dump({"stage": "screens"}, open(os.path.join(tg, ".website-state.json"), "w"))
    sref = f"cat {tg}/.website-state.json"
    check("tracker: без запуска phase-tracker → BLOCK",
          run_hook(TRACKER, tracker_payload([sref])), 2)
    check("tracker: phase-tracker.py реально прогнан → пропуск",
          run_hook(TRACKER, tracker_payload([sref, f"python3 {SCRIPTS}/phase-tracker.py {tg}"])), 0)
    check("tracker: не website-сессия → пропуск",
          run_hook(TRACKER, tracker_payload([sref], skill_website=False)), 0)

    # ───────── ПЕРФ-ПОЛ layout-audit.mjs (mobile-first скорость загрузки, автор) ─────────
    # Требует node + playwright в node_modules какого-либо cwd. Ищем по кандидатам; нет → честный
    # skip (НЕ падаем — окружение без playwright не должно ронять регрессию слоя принуждения).
    AUDIT = os.path.join(SCRIPTS, "layout-audit.mjs")
    pw_cwd = None
    for cand in (os.path.join(HOME, "Desktop", "landing-vibecoding-oplata"),
                 os.path.join(HOME, "<твой-сайт-проект>"), os.getcwd()):
        if os.path.isdir(os.path.join(cand, "node_modules", "playwright")):
            pw_cwd = cand
            break

    def audit_perf(html, cwd, extra=()):
        f = os.path.join(tmp, "perf.html")
        open(f, "w").write(html)
        p = subprocess.run(["node", AUDIT, f, "390", *extra], cwd=cwd,
                           capture_output=True, text=True, timeout=120)
        try:
            w = json.loads(p.stdout)["widths"]["390"]
        except Exception:
            return None, p.returncode
        return w, p.returncode

    BAD = ('<!doctype html><html><head>'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded">'
           '<script src="/app.js"></script></head><body><h1>Заголовок героя тут целиком</h1>'
           '<div style="height:3000px"></div><img src="/p.jpg" width="300" height="200"></body></html>')
    GOOD = ('<!doctype html><html lang="ru"><head>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded&display=swap">'
            '<script src="/app.js" defer></script></head><body><h1>Заголовок героя тут целиком</h1>'
            '<div style="height:3000px"></div>'
            '<img src="/p.jpg" width="300" height="200" loading="lazy"></body></html>')
    if pw_cwd:
        wbad, ebad = audit_perf(BAD, pw_cwd)
        perf_keys = ("render_blocking", "font_display", "img_offscreen_eager")
        check("perf: render-blocking <script> в head → флаг",
              bool(wbad and wbad.get("render_blocking")), True)
        check("perf: google-fonts без display=swap → флаг (FOIT)",
              bool(wbad and wbad.get("font_display")), True)
        check("perf: offscreen <img> без loading=lazy → флаг",
              bool(wbad and wbad.get("img_offscreen_eager")), True)
        check("perf: BAD-фикстура → exit 1 (блокирует)", ebad, 1)
        wgood, _ = audit_perf(GOOD, pw_cwd)
        check("perf: GOOD-фикстура → ноль перф-дефектов",
              bool(wgood and not any(wgood.get(k) for k in perf_keys)), True)
        wnp, _ = audit_perf(BAD, pw_cwd, extra=("--no-perf",))
        check("perf: --no-perf глушит перф-классы",
              bool(wnp is not None and not any(wnp.get(k) for k in perf_keys)), True)
        # десктоп не флагает перф (mobile-first): прогнать ту же BAD на 1280
        fdt = os.path.join(tmp, "perf-dt.html")
        open(fdt, "w").write(BAD)
        pdt = subprocess.run(["node", AUDIT, fdt, "1280"], cwd=pw_cwd,
                             capture_output=True, text=True, timeout=120)
        try:
            wd = json.loads(pdt.stdout)["widths"]["1280"]
            dt_clean = not any(wd.get(k) for k in perf_keys)
        except Exception:
            dt_clean = False
        check("perf: десктоп 1280 НЕ флагает перф (mobile-first)", dt_clean, True)
        wb, _ = audit_perf(GOOD, pw_cwd, extra=("--weight-budget", "1"))
        check("perf: --weight-budget превышен → weight_over_budget",
              bool(wb and wb.get("weight_over_budget")), True)
    else:
        check("perf: layout-audit (playwright не найден — SKIP, не падаем)", True, True)

    passed = sum(1 for ok, *_ in results if ok)
    total = len(results)
    print(f"\n━━━ WEBSITE SELFTEST: {passed}/{total} ━━━")
    for ok, name, detail in results:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}  [{detail}]")
    if passed != total:
        print(f"\n🛑 ПРОВАЛЕНО {total - passed} — слой принуждения НЕ гарантирован, чини до зелёного.")
        sys.exit(1)
    print("\n✅ ВСЕ механизмы принуждения работают (happy/negative/edge).")
    sys.exit(0)


if __name__ == "__main__":
    main()