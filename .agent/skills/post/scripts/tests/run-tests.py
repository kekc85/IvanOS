#!/usr/bin/env python3
"""
run-tests.py - раннер red/green фикстур для lint-post.py v2 + bench-post.py.

AC6-тест (спека ~/specs/2026-08-04-post-skill-v2.md): на каждый из 13
классов R2-feedback-taxonomy.md - red-фикстура (lint обязан завалить HARD)
+ green-фикстура (НЕ должна падать ни на одном v2.0 HARD-гейте). Правило
admission важнее фикстуры: если green падает на новом v2.0 гейте, порог в
lint-post.py чинится (см. комментарии "Admission-фикс" в коде), фикстура
не подгоняется под порог.

RED-классы (машинно-ловимые классом R2): каждый red проверяется через
lint-post.py --form-goal/--form-class (+ --factbase где нужно) и ОБЯЗАН
дать exit 1 с конкретной строкой [FAIL] по своему классу.

GREEN-фикстуры: 7 донор-постов (corpus-12m.json uid Донор-А:504/492/433/440,
Донор-Б:1372/1455/1579) + 3 одобренных финала владельца (запуск по решению автора).
🔴 Это НЕ то же самое, что набор bench-эталонов: с этой редакции в
scripts/etalons.json лежит 11 постов ТРЁХ доноров (+ Донор-В:213/102/165,
+ Донор-Б:1833 razbor - он пришёл дефектом Д23 раунда 4 на замену паре
Донор-Б:2034/2014, внесённой дефектом Д19 и снятой в тот же день за
реакция-механику `⚡️` и коридор класса), и эти четыре поста в
green-корпус НЕ приняты - они падают на законах автора о СВОИХ постах (пол
500 знаков, причинные связки, рубка строкой), а послаблений под эти классы
у донор-корпуса нет. Бенч-сверке линт не нужен: она
меряет длину/воздух/жирные/ссылки эталона, а не гоняет его через гейты. Критерий
"чисто" - в РАЗДЕЛЕ "v2.0: ..." вывода lint НЕТ ни одной строки [FAIL].
Старые (v1) HARD-гейты (премиум-эмодзи заголовка, лимит двоеточий и т.д.)
намеренно НЕ входят в этот критерий - донор-тексты физически не несут
Владелец-специфичного форматирования (эмодзи-заголовок, УТМ, факт-базу) и не
обязаны проходить его; это не регресс, это разные слои закона (v1 - формат
Владельца, v2.0 - общие пороги R3). Полный прогон лежит на связке 04-review.

Хвост: класс R2-11 (процессные) владеет post-phase-gate.sh (Z1-зона хука),
не lint-post.py - тестируется отдельным HOOK-блоком ниже. 🔴 Формулировка про
"маркеры в транскрипте" снята как ложная (дефект Д45, раунд 10): греп-маркеры
("ИТОГ: PASS", "bench-post.py прогнан", "факт-база: объём") хук ТРЕБОВАТЬ
перестал - они подделываемы по устройству, литералы лежат в файлах самого
скилла, и любое их чтение кладёт след в транскрипт. HOOK-блок теперь ЗАПРЕЩАЕТ
эти греп-условия (test_hook_no_forgeable_greps) и проверяет, что хук САМ гоняет
lint/bench (test_hook_executes_checks_itself), сам разбирает класс поста
(Д8-тесты) и сам держит гейт donor-devices (test_hook_donordev_gate, Д45).

Exit 0 - все red поймали свой класс И все green чисты И хук отрабатывает
маркеры. Exit 1 - хоть один провал (печатается читаемый отчёт по каждому).
"""

import subprocess
import sys
import os
import json
import tempfile
import datetime
import shutil
import re
import itertools
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
LINT = os.path.join(SCRIPTS, "lint-post.py")
BENCH = os.path.join(SCRIPTS, "bench-post.py")
HOOK = os.environ.get("POST_HOOK_OVERRIDE") or os.path.expanduser(
    "~/.claude/hooks/post-phase-gate.sh")
# ^ NEW (verify-FIX-R39.sh, Д108 скептик-раунда 38, по решению автора): override
# теста ТОЛЬКО, тем же приёмом, что POST_OWNER_FIXTURES - позволяет прогнать
# ПОЛНЫЙ run-tests.py против ПАТЧЕННОЙ КОПИИ хука, не трогая живой файл
# (сухая проверка патча ДО того, как владелец применит его к реальному
# ~/.claude/hooks/post-phase-gate.sh). Без переменной поведение не меняется -
# путь ровно тот же, что был.

PASS_COLOR = ""
FAIL_COLOR = ""

results = []


skipped = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    tag = "OK  " if ok else "FAIL"
    print(f"[{tag}] {name}" + (f" - {detail}" if detail and not ok else ""))


def skip(name, reason):
    """Группа тестов, для которой на этой машине нет ВХОДНЫХ ДАННЫХ.

    Это не провал и не «замолчали дефект»: сама проверка цела, отсутствует
    приватный корпус владельца. Пишем в отдельный список - в ИТОГ он не идёт
    ни плюсом, ни минусом, но печатается явной строкой с причиной."""
    skipped.append((name, reason))
    print(f"[SKIP] {name} - {reason}")


# ===========================================================================
# 🔒 4i: КОРПУС ПОСТОВ ВЛАДЕЛЬЦА ЖИВЁТ ВНЕ РАЗДАВАЕМОГО СКИЛЛА.
# Фикстуры green-ivan/ и green/ivan-final-* это ДОСЛОВНЫЕ посты автора: его
# тексты, его запуск, его ссылки. В пакете ученика их нет и быть не должно.
# Раньше они лежали прямо в скилле; теперь - в .business (не раздаётся), а
# раннер ищет их условно и без них просто пропускает СВОИ группы.
#   есть каталог  -> группы гоняются как обычно (у автора счёт не меняется)
#   нет каталога  -> [SKIP] с причиной, остальные тесты зелёные, exit 0
# Путь: env POST_OWNER_FIXTURES -> .business/... -> ~/.business/...
# ===========================================================================
OWNER_FIXTURES_CANDIDATES = (
    os.environ.get("POST_OWNER_FIXTURES") or "",
    ".business/processes/post-fixtures-ivan",
    "~/.business/processes/post-fixtures-ivan",
)


def _resolve_owner_fixtures():
    for p in OWNER_FIXTURES_CANDIDATES:
        if not p:
            continue
        fp = os.path.expanduser(p)
        if os.path.isdir(fp):
            return fp
    return None


OWNER_FIXTURES = _resolve_owner_fixtures()
NO_OWNER_CORPUS = ("приватный корпус постов владельца не подключён "
                   "(POST_OWNER_FIXTURES / ~/.business/processes/post-fixtures-ivan); "
                   "проверки целы, отсутствуют только входные тексты автора")


def owner_fixture(subdir, fname):
    """Путь к фикстуре владельца или None, если корпус не подключён."""
    if not OWNER_FIXTURES:
        return None
    p = os.path.join(OWNER_FIXTURES, subdir, fname)
    return p if os.path.isfile(p) else None


def is_owner_green(fname):
    """green-фикстура из личного корпуса автора (а не донорский текст)."""
    return fname.startswith("ivan-final-")


# ===========================================================================
# 🔴 ELEMENT_FLOOR_LEGACY_FIXTURES (по решению автора, Д1 финального жюри).
#
# РАСАКЦЕПТОВАНЫ ВЛАДЕЛЬЦЕМ по решению автора ПО ОСИ ТЕКСТУРЫ, ПОРОГ ПО НИМ НЕ
# КАЛИБРУЕТСЯ.
#
# Обычный закон движка - «HARD ставится только там, где его переживает весь
# зелёный корпус». На оси ЭЛЕМЕНТОВ ФОРМЫ этот закон не действует, и причина
# названа самим владельцем: «нет элементов и выделений как у доноров,
# вообще нет никаких прикольных элементов» - забракован уровень текстуры его
# СОБСТВЕННЫХ выданных постов. Значит по этой одной оси green-корпус
# расакцептован: калибровать по нему порог значило бы зацементировать ровно то,
# за что был разнос. Пол остаётся минимальным из осмысленных (1 сигнатурный
# элемент из 8 - его не берут ни стерильный текст, ни 7 имитаций жюри), а
# фикстуры, которые на СТРОГОМ счёте под него не проходят, живут здесь явным
# списком с их измеренным счётом.
#
# ЧТО ЭТОТ СПИСОК ДЕЛАЕТ: тесты на element-floor (`[FAIL] элементы формы` и
# `[FAIL] сигнатурные элементы`) по этим файлам пропускаются. ЧТО НЕ ДЕЛАЕТ:
# ВСЕ остальные гейты по ним работают как раньше, ни одна другая строка [FAIL]
# не прощается. Список закрытый: новый файл сюда не дописывается - живая выдача
# обязана нести элемент, а не попадать в исключения.
#
# Замер по решению автора (`check_element_types` живого модуля, строгие детекторы):
ELEMENT_FLOOR_LEGACY_FIXTURES = {
    # файл                  сигнатурных / типов из 15   (пол: 1 / 3)
    "b17-3-0508.txt":      {"sig": 0, "types": 3},
    "inf17-0508.txt":      {"sig": 0, "types": 4},
    "osn17-0508.txt":      {"sig": 0, "types": 4},
    "ivan-final-1.txt":    {"sig": 0, "types": 2},
    "ivan-final-2.txt":    {"sig": 0, "types": 2},
}
# Строки-вердикты обоих полов элементов - их и только их прощает манифест.
ELEMENT_FLOOR_FAIL_MARKS = ("[FAIL] элементы формы", "[FAIL] сигнатурные элементы")


def drop_element_floor_fails(fail_lines, fname):
    """Убирает строки element-floor из списка [FAIL], если файл в манифесте
    расакцептованных. Для всех прочих файлов список возвращается как есть."""
    if fname not in ELEMENT_FLOOR_LEGACY_FIXTURES:
        return fail_lines
    return [l for l in fail_lines
            if not any(l.strip().startswith(m) for m in ELEMENT_FLOOR_FAIL_MARKS)]


def green_path(fname):
    """green/<file>: донор лежит в скилле, финал автора - в его приватном корпусе."""
    if is_owner_green(fname):
        return owner_fixture("green", fname)
    return os.path.join(FIXTURES, "green", fname)


def run_lint(fixture, extra_args=None, use_temp_journals=True):
    extra_args = extra_args or []
    cmd = [sys.executable, LINT, os.path.join(FIXTURES, "red", fixture)]
    if use_temp_journals:
        cmd += ["--skeleton-log", TMP_SKELETON_LOG, "--used-anchors-log", TMP_ANCHOR_LOG]
    cmd += extra_args
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def run_lint_file(path, extra_args=None, use_temp_journals=True):
    extra_args = extra_args or []
    cmd = [sys.executable, LINT, path]
    if use_temp_journals:
        cmd += ["--skeleton-log", TMP_SKELETON_LOG, "--used-anchors-log", TMP_ANCHOR_LOG]
    cmd += extra_args
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def v2_section(output):
    """Вырезает раздел 'v2.0: ...' из вывода lint (между разделителями)."""
    lines = output.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.startswith("v2.0:"):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("ИТОГ"):
            end = i
            break
    return "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# RED-фикстуры: 13 классов R2 (R2-feedback-taxonomy.md)
# ---------------------------------------------------------------------------

def test_red_water():
    """Класс R2-1 (вода)."""
    rc, out = run_lint("01-water.txt", ["--form-goal", "reactions", "--form-class", "narrative"])
    ok = rc == 1 and ("вода-канцелярит" in out and "[FAIL] вода-канцелярит" in out)
    record("R2-1 вода (01-water.txt)", ok, out[-300:] if not ok else "")


def test_red_ad_not_value():
    """Класс R2-2 (реклама вместо ценности, частично - отложенное обещание)."""
    rc, out = run_lint("02-ad-not-value.txt", ["--form-goal", "reactions", "--form-class", "narrative"])
    ok = rc == 1 and "отложенное обещание" in out
    record("R2-2 реклама/отложенное обещание (02-ad-not-value.txt)", ok, out[-300:] if not ok else "")


def test_red_ogryzok():
    """Класс R2-3 (огрызок) ловится СВОИМ классом, а не длиной факт-базы.

    🔴 Д18 (по решению автора), К4: требование «факт-база длиннее поста» снято. Оно
    толкало ровно в ту дыру, которую чинит сито дублей факт-базы: самый дешёвый
    способ сделать базу длиннее поста - взять сам пост. Честная выписка из
    четырёх строк отбивалась, копия тела проходила. Огрызок обязан падать своим
    классом (пол длины / плотность / вода), а строка объёма стала справкой."""
    fb = os.path.join(FIXTURES, "red", "03-ogryzok.factbase.txt")
    rc, out = run_lint("03-ogryzok.txt", ["--factbase", fb])
    fails = [l for l in out.splitlines() if l.strip().startswith("[FAIL]")]
    ok = (rc == 1 and fails
          and "факт-база: объём" not in out
          and not any("факт-база" in l and "объём" in l for l in fails))
    record("R2-3 огрызок ловится своим классом, длина факт-базы не блок (Д18 К4)", ok,
           ("rc=%s\n" % rc) + "\n".join(fails)[:400] if not ok else "")


def test_factbase_short_honest_passes():
    """Д18 К4: ЧЕСТНАЯ факт-база КОРОЧЕ поста проходит AC5.

    Прецедент из отчёта раунда 5: выписка «257000 руб., 317 дней, бухгалтер
    Донор-Б» (106 знаков) против поста 893 знака давала [FAIL] «дефицит
    контекста». Теперь длина - справка, а числа/имена по-прежнему сверяются."""
    post = ("**Итог спора**\n\n"
            "Бухгалтер Донор-Б вернул 257000 рублей за 317 дней, и это заняло у нас "
            "ровно столько времени, сколько занимает обычная переписка с банком\n\n"
            "Разбирал по документам, а не по памяти, поэтому цифры тут ровно из выписки")
    fb = "Выписка по делу\n257000 руб.\n317 дней\nбухгалтер Донор-Б\n"
    pd, pp = tempfile.mkstemp(prefix="post-fb-short-", suffix=".txt")
    with os.fdopen(pd, "w", encoding="utf-8") as f:
        f.write(post)
    fd, fbp = tempfile.mkstemp(prefix="post-fb-src-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(fb)
    rc, out = run_lint_file(pp, ["--factbase", fbp])
    fb_fails = [l for l in out.splitlines()
                if l.strip().startswith("[FAIL]") and ("факт-баз" in l or "выдуманные числа" in l
                                                       or "висящие имена" in l)]
    ok = not fb_fails and "[INFO] факт-база короче поста" in out
    record("AC5: честная факт-база короче поста проходит (Д18 К4)", ok,
           "\n".join(fb_fails)[:400] if not ok else out[-300:] if not ok else "")


def test_red_invented_facts():
    """Класс R2-4 (выдуманные факты - AC5 числа не в факт-базе)."""
    fb = os.path.join(FIXTURES, "red", "04-invented-facts.factbase.txt")
    rc, out = run_lint("04-invented-facts.txt", ["--factbase", fb])
    ok = rc == 1 and "выдуманные числа" in out and "25000" in out
    record("R2-4 выдуманные факты (04-invented-facts.txt)", ok, out[-400:] if not ok else "")


def test_red_collocation():
    """Класс R2-5 (несуществующие обороты)."""
    rc, out = run_lint("05-invented-collocation.txt")
    ok = rc == 1 and "несуществующие словосочетания" in out
    record("R2-5 несуществующие обороты (05-invented-collocation.txt)", ok, out[-400:] if not ok else "")


def test_red_dangling_referent():
    """Класс R2-6 (висящие референты - AC5 имена не в факт-базе, проксирует К6)."""
    fb = os.path.join(FIXTURES, "red", "06-dangling-referent.factbase.txt")
    rc, out = run_lint("06-dangling-referent.txt", ["--factbase", fb])
    ok = rc == 1 and "висящие имена" in out and "Екатерин" in out
    record("R2-6 висящие референты (06-dangling-referent.txt)", ok, out[-400:] if not ok else "")


def test_red_homework():
    """Класс R2-7 (домашка / действие-читателю)."""
    rc, out = run_lint("07-homework.txt")
    ok = rc == 1 and "домашка" in out
    record("R2-7 домашка (07-homework.txt)", ok, out[-300:] if not ok else "")


def test_red_anchor_dup():
    """Класс R2-8 (повтор якоря/героя кросс-канально за 7 дней, .used-anchors.jsonl).

    🔴 4c: критерий сменён с ГЛОБАЛЬНОГО rc на СВОЮ строку правила. Причина -
    08-anchor-dup.txt это микро-фикстура на 87 знаков, собранная под одну ось
    (журнал якорей). После 4c такой обрубок законно падает ещё и по трём чужим
    правилам (пол длины 500, плотность идей, ноль причинных связок), и тест
    начал краснеть не из-за своего класса. Подгонять фикстуру под пороги
    запрещено (шапка модуля), поэтому тест теперь спрашивает ровно то, ради
    чего написан: на первом прогоне строки дубля НЕТ, на втором ЕСТЬ."""
    fixture = os.path.join(FIXTURES, "red", "08-anchor-dup.txt")
    common = ["--form-goal", "reactions", "--form-class", "razbor",
              "--anchor", "ночь-перед-запуском", "--hero", "test-skill", "--channel", "test-ch",
              "--skeleton-log", TMP_SKELETON_LOG,
              "--allow-skeleton-repeat", "test", "--allow-no-premium-hook", "test-fixture-no-emoji"]
    # Журнал засевается НАПРЯМУЮ, а не первым прогоном линтера: линтер пишет
    # журнал только при чистом прогоне (`if args.log_anchor and not hard_fail`),
    # а микро-фикстура на 87 знаков после 4c законно падает по полу длины -
    # то есть «посев прогоном» проверял бы не дубль-гейт, а посторонние правила.
    fd, seeded = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"date": datetime.date.today().isoformat(), "channel": "test-ch",
                            "slug": "run1", "anchor": "ночь-перед-запуском",
                            "hero": "test-skill"}, ensure_ascii=False) + "\n")
    # чистый журнал -> строки дубля быть не должно
    fd2, empty = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd2)
    p1 = subprocess.run([sys.executable, LINT, fixture] + common + ["--used-anchors-log", empty],
                        capture_output=True, text=True)
    first_ok = "дубль якоря/героя" not in p1.stdout
    # тот же якорь/герой в пределах 7 дней -> HARD FAIL
    p2 = subprocess.run([sys.executable, LINT, fixture] + common + ["--used-anchors-log", seeded],
                        capture_output=True, text=True)
    second_ok = p2.returncode == 1 and "[FAIL] дубль якоря/героя" in p2.stdout
    ok = first_ok and second_ok
    detail = f"пустой журнал дубль={not first_ok} / засеянный rc={p2.returncode}\n{p2.stdout[-400:]}"
    record("R2-8 дубль якоря/героя (.used-anchors.jsonl)", ok, detail if not ok else "")


def test_red_form():
    """Класс R2-9 (форма - существующий v1 гейт, точка в конце абзаца)."""
    rc, out = run_lint("09-form.txt")
    ok = rc == 1 and "точка в конце абзаца" in out
    record("R2-9 форма (09-form.txt, v1 гейт)", ok, out[-300:] if not ok else "")


def test_red_price_digit():
    """Класс R2-10 (CTA/деньги - цена цифрой)."""
    rc, out = run_lint("10-price-digit.txt")
    ok = rc == 1 and "цена цифрой" in out and "[FAIL] цена цифрой" in out
    record("R2-10 цена цифрой (10-price-digit.txt)", ok, out[-300:] if not ok else "")


def test_red_process_hook():
    """Класс R2-11 (процессные) - владеет post-phase-gate.sh, не lint. См. HOOK-блок ниже."""
    ok = os.path.exists(HOOK)
    record("R2-11 процессные (владелец - hook, см. test_hook_* ниже)", ok,
           "хук не найден" if not ok else "")


def test_red_placeholder():
    """Класс R2-12 (плейсхолдеры)."""
    rc, out = run_lint("12-placeholder.txt")
    ok = rc == 1 and "плейсхолдеры в тексте" in out and "[пруф дня]" in out
    record("R2-12 плейсхолдеры (12-placeholder.txt)", ok, out[-300:] if not ok else "")


def test_red_push_corridor():
    """Класс R2-13 (email/пуши) - вне скилла post; в post только --budget WARN
    (канон §3 запрещает FAIL по длине), поэтому это ЕДИНСТВЕННЫЙ red-класс,
    где ожидаемый результат - exit 0 С печатью WARN (не HARD FAIL) - так и
    задумано AC1: "давление длины - вниз к цели, через сжатие, не через блок"."""
    # 4c: критерий сменён с глобального rc на «бюджет длины не блокирует».
    # Пол огрызка (канон п.45, 500 знаков) - ОТДЕЛЬНЫЙ закон, он и обязан
    # ронять снипет на 362 знака; утверждение AC1 касается только --budget.
    rc, out = run_lint("13-push-corridor.txt", ["--form-goal", "reactions", "--form-class", "razbor",
                                                 "--budget", "300", "--allow-no-premium-hook",
                                                 "test-fixture-no-emoji"])
    ok = "[WARN] бюджет длины" in out and "[FAIL] бюджет длины" not in out
    record("R2-13 пуш-коридор WARN, не блок (13-push-corridor.txt, --budget)", ok, out[-300:] if not ok else "")


def test_red_word_numerals():
    """Волна 16: числительное ПРОПИСЬЮ вне факт-базы. Уровень WARN (не HARD):
    русское числительное омонимично обычному слову, ложный блок валил бы
    здоровый пост. Проверяем ровно то, что описано в спеке: «с пятого ролика»
    при базе без пятёрки ловится, а «двое суток» (в базе «2 суток»), «первый»
    (в базе «1 ролика») и идиомы белого списка («ни одного», «один из») НЕ ловятся."""
    fb = os.path.join(FIXTURES, "red", "22-word-numerals.factbase.txt")
    # 4c: --form-goal стал обязательным (иначе профильный слой молча не
    # применяется - HARD-ошибка запуска), а глобальный rc больше не критерий:
    # снипет на 286 знаков законно падает по полу длины. Утверждение теста -
    # про УРОВЕНЬ WARN у числительных, его и проверяем.
    rc, out = run_lint("22-word-numerals.txt", ["--form-goal", "reactions",
                                                "--form-class", "razbor", "--factbase", fb])
    warn = [ln for ln in out.splitlines() if "числительные словами вне факт-базы" in ln]
    # список найденного = часть строки ДО пояснения «(AC5б-прописью…)»: само
    # пояснение цитирует идиому «в первую очередь» как пример, и наивный поиск
    # подстроки по всей строке ловил бы её как находку
    found = warn[0].split("(AC5б")[0] if warn else ""
    ok = (len(warn) == 1 and "«пятого» (=5)" in found
          and "вне факт-базы: 1 " in found
          and "двое" not in found.lower() and "перв" not in found.lower().replace("«пятого»", ""))
    record("волна16 числительные прописью: «пятого» вне базы = WARN, идиомы и покрытые числа молчат",
           ok, out[-500:] if not ok else "")


def test_word_numerals_silent_without_factbase():
    """Волна 16, admission: БЕЗ --factbase детектор не печатает НИЧЕГО.
    Прогон по всем 7 донор-фикстурам и 3 финалам владельца - там числительные
    прописью есть, а сверять их не с чем, и молчание тут обязательно:
    иначе слой шумел бы на каждом обычном прогоне линтера."""
    noisy = []
    for name in sorted(os.listdir(os.path.join(FIXTURES, "green"))):
        if not name.endswith(".txt"):
            continue
        _, out = run_lint_file(os.path.join(FIXTURES, "green", name))
        if "числительные словами" in out:
            noisy.append(name)
    record("волна16 числительные прописью: без --factbase молчит на 7 донорах + 3 финалах владельца",
           not noisy, "печатал на: " + ", ".join(noisy) if noisy else "")


RED_TESTS = [
    test_red_water, test_red_ad_not_value, test_red_ogryzok, test_factbase_short_honest_passes,
    test_red_invented_facts,
    test_red_collocation, test_red_dangling_referent, test_red_homework, test_red_anchor_dup,
    test_red_form, test_red_price_digit, test_red_process_hook, test_red_placeholder,
    test_red_push_corridor, test_red_word_numerals, test_word_numerals_silent_without_factbase,
]


# ---------------------------------------------------------------------------
# ВОЛНА 15 (топ-3 находки судьи бенчмарка по решению автора): ритм в словах, живой
# слой, механика класса. Отдельная секция - это не новые классы таксономии R2,
# а новые гейты внутри существующих классов (R2-1/R2-7/R2-9).
# ---------------------------------------------------------------------------

def test_w15_rhythm_median():
    """HARD: медиана 19 слов в предложении > потолка 16 (максимум green-корпуса 13.0)."""
    rc, out = run_lint("15-rhythm-median.txt", ["--form-goal", "reactions", "--form-class", "narrative"])
    ok = rc == 1 and "[FAIL] ритм: медиана" in out and "HARD-потолка 16" in out
    record("W15 ритм: медиана слов > 16 = HARD (15-rhythm-median.txt)", ok, out[-400:] if not ok else "")


def test_w15_punch_warn():
    """WARN: ноль ударных предложений <=4 слов при минимуме 2 (та же фикстура)."""
    rc, out = run_lint("15-rhythm-median.txt", ["--form-goal", "reactions", "--form-class", "narrative"])
    ok = "[WARN] ударных предложений" in out
    record("W15 ударные предложения: 0 < 2 = WARN (15-rhythm-median.txt)", ok, out[-400:] if not ok else "")


def test_w15_glue_warn():
    """WARN: плотность клея выше 22.0/1000 у бенчмарк-поста. Проверяется на самой
    плотной фикстуре корпуса - тексте с «, а » в каждом предложении."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_glue", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    text = ("Слово. " * 5) + " ".join(
        ["Первая половина ведёт за руку командами в копи-блоках, а вторая греет к платному шагу." ] * 12)
    glue = lp.check_glue_density(text)
    ok = glue is not None and glue["k"] > lp.W15_GLUE_WARN_K
    record("W15 клей: плотность выше порога ловится (синтетический текст)", ok,
           f"glue={glue}" if not ok else "")


def test_w15_glossary_warn():
    """WARN: глоссарные вставки «X это когда» и «..., а это X» (0/10 green)."""
    # 4c: критерий сменён с глобального rc на «свой класс не блокирует».
    # 16-glossary.txt - снипет на 276 знаков под одну ось; после 4c он законно
    # падает по полу длины (канон п.45), и глобальный rc перестал что-либо
    # говорить о глоссарных вставках. Спрашиваем ровно своё: WARN есть, FAIL нет.
    rc, out = run_lint("16-glossary.txt", ["--form-goal", "reactions", "--form-class", "narrative"])
    ok = "[WARN] глоссарная вставка" in out and "[FAIL] глоссарная вставка" not in out
    record("W15 глоссарная вставка = WARN, не блок (16-glossary.txt)", ok, out[-400:] if not ok else "")


def test_w15_showcase_hook():
    """WARN: продажа открыта именем героя, квитанции после заголовка нет."""
    rc, out = run_lint("17-showcase-hook.txt", ["--form-goal", "sales", "--form-class", "sales",
                                                 "--hero", "воронка под кодовое слово"])
    ok = "[WARN] витрина вместо квитанции" in out
    record("W15 витрина вместо квитанции (17-showcase-hook.txt, --hero)", ok, out[-400:] if not ok else "")


def test_w15_no_oral():
    """HARD: разбор без единого знака устной речи (admission 10/10 green несут знак)."""
    rc, out = run_lint("18-no-oral.txt", ["--form-goal", "reactions", "--form-class", "razbor"])
    ok = rc == 1 and "[FAIL] живой слой" in out
    record("W15 живой слой: 0 знаков устной речи = HARD (18-no-oral.txt)", ok, out[-400:] if not ok else "")


def test_w15_no_oral_downgrade():
    """--allow-no-oral <причина> понижает тот же случай до WARN (escape-клапан)."""
    rc, out = run_lint("18-no-oral.txt", ["--form-goal", "reactions", "--form-class", "razbor",
                                           "--allow-no-oral", "архивная фикстура"])
    ok = "[WARN] живой слой" in out and "архивная фикстура" in out
    record("W15 живой слой: --allow-no-oral понижает до WARN", ok, out[-400:] if not ok else "")


def test_w15_homework_soft():
    """4c: рецидив бенчмарка теперь ловит и УЗКИЙ HARD-набор, не только широкий слой.

    БЫЛО (волна 15): тест утверждал `soft=True and hard=False` - то есть
    фиксировал ДЫРУ как норму: «Возьми слово, которое звучит в твоих постах,
    и сделай под него статью» печаталось WARN-ом и выдачу не блокировало.
    BASELINE по решению автора назвал это «функцией-призраком» №2 (check_homework_action
    ловит только soft-случаи мимо HARD). 4c залатал словарь узкого набора,
    поэтому тест перевёрнут: теперь оба слоя обязаны видеть рецидив, а
    блокирует его HARD. ADMISSION к расширению - 0/12 green-ivan и
    0/10 green-фикстур (7 донор-постов + 3 финала автора) таких оборотов
    не несут."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_hw", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    src = "Возьми слово, которое звучит в твоих постах, и сделай под него статью"
    clean = "Ночью посчитал, во сколько мне обходится один лид, и записал 110 рублей"
    ok = (bool(lp.check_homework_soft(src)) and lp.check_homework_action(src)
          and not lp.check_homework_action(clean))
    record("4c домашка: рецидив бенчмарка ловит и узкий HARD (была функция-призрак)", ok,
           f"soft={lp.check_homework_soft(src)} hard={lp.check_homework_action(src)} "
           f"clean_hard={lp.check_homework_action(clean)}" if not ok else "")


# 🔴 Д18 (по решению автора), К5. Оба теста ниже переписаны на подписи С РАЗРЕШЕНИЕМ.
# Раньше они строились на `18-no-oral.txt`, чей скелет = `HB→P` (две буквы), и
# после калибровки К5 ось скелета такие подписи не судит вовсе - вырожденная
# подпись «пост написан абзацами» повторяется почти у всех. Тест на факт FAIL
# при этом ПРОХОДИЛ мимо предмета: подстрока «скелет» находилась в чужой строке
# `[PASS] скелет отличается от последних 5 выдач канала`. Теперь тела строятся
# синтетически, со скелетом `HB→P→CTA→P` (четыре блока), и проверяется СВОЯ
# строка вердикта.
_W15_SKEL_BODY = (
    "**{head}**\n\n"
    "Первый абзац разбора, в котором есть содержательная мысль и конкретика, "
    "потому что иначе пост не о чем. Цифра в нём тоже есть, скажем 17 штук\n\n"
    "👉 Открыть комнату https://example.org/room\n\n"
    "Финальный абзац, который закрывает мысль и не повторяет заголовок дословно"
)


def _w15_pkg(head_self, head_twin):
    """Каталог пакета из двух близнецов + путь к телу самой единицы.

    Близнецов ДВА, потому что ось «один каркас на серию» считает ДОЛЮ и по
    построению молчит на пакете меньше трёх единиц: серия - это от трёх."""
    pkg = tempfile.mkdtemp(prefix="post-w15-pkg-")
    with open(os.path.join(pkg, "twin.txt"), "w", encoding="utf-8") as f:
        f.write(_W15_SKEL_BODY.format(head=head_twin))
    with open(os.path.join(pkg, "twin2.txt"), "w", encoding="utf-8") as f:
        f.write(_W15_SKEL_BODY.format(head=head_twin + ", третья единица серии"))
    fd, self_path = tempfile.mkstemp(prefix="post-w15-self-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_W15_SKEL_BODY.format(head=head_self))
    return pkg, self_path


def test_w15_package_wave_fail():
    """FAIL: один каркас на серию (доля пакета > 60%, калибровка Д18 К5)."""
    pkg, self_path = _w15_pkg("Заголовок первой единицы серии",
                              "Совсем другой заголовок второй единицы этой же серии")
    rc, out = run_lint_file(self_path, ["--form-goal", "reactions", "--form-class", "razbor",
                                        "--package", pkg])
    ok = rc == 1 and "[FAIL] дубли внутри волны" in out and "один каркас на серию" in out
    record("W15 пакет: один каркас на серию (доля > 60%) = FAIL", ok, out[-600:] if not ok else "")


def test_w15_package_low_resolution_no_fail():
    """Д18 К5: вырожденная подпись (`HB→P`, два блока) осью скелета НЕ судится.

    Улика калибровки: в принятом владельцем пакете Д18 (_pakety-0608, 21 единица)
    так помечались 16 единиц из 21, и пакет целиком уходил в BLOCKED. «Пост
    написан абзацами» - это не «один каркас на серию»."""
    pkg = tempfile.mkdtemp(prefix="post-w15-pkg-lowres-")
    src = os.path.join(FIXTURES, "red", "18-no-oral.txt")
    twin = open(src, encoding="utf-8").read().replace(
        "Разбор без единого знака живого голоса",
        "Другой заголовок другой формы для проверки только одной оси скелета")
    with open(os.path.join(pkg, "twin.txt"), "w", encoding="utf-8") as f:
        f.write(twin)
    rc, out = run_lint("18-no-oral.txt", ["--form-goal", "reactions", "--form-class", "razbor",
                                          "--package", pkg])
    ok = "один каркас на серию" not in out and "скелет идентичен" not in out
    record("W15 пакет: вырожденный скелет HB→P осью не судится (Д18 К5)", ok,
           out[-600:] if not ok else "")


def test_w15_package_downgrade():
    """--allow-skeleton-repeat <причина> понижает пакетный скелет обратно до WARN.

    🔴 Д10 (по решению автора): заголовок близнеца сделан ДРУГОЙ ФОРМЫ (8+ слов против
    5-7 у оригинала). Причина - у пакета появилась вторая независимая ось FAIL
    (доля одной формы заголовка > 50%, канон п.38), и близнец «той же формы» в
    пакете из двух единиц давал 100% = честный FAIL по п.38, который глушил
    предмет ЭТОГО теста - понижение СКЕЛЕТА. Один тест меряет одну ось."""
    pkg, self_path = _w15_pkg("Заголовок первой единицы серии",
                              "Совсем другой заголовок второй единицы этой же серии")
    rc, out = run_lint_file(self_path, ["--form-goal", "reactions", "--form-class", "razbor",
                                        "--package", pkg, "--allow-skeleton-repeat",
                                        "серия наследует каркас по просьбе автора"])
    ok = "[WARN] кросс-постовые дубли" in out and "[FAIL] дубли внутри волны" not in out
    record("W15 пакет: --allow-skeleton-repeat понижает до WARN", ok, out[-500:] if not ok else "")


def _kanon38_pkg(forms):
    """Пакет из N постов с заданными заголовками (тело одно и то же).

    Скелет у всех одинаковый намеренно: ось скелета глушится флагом
    --allow-skeleton-repeat, чтобы тест мерил РОВНО долю формы заголовка."""
    pkg = tempfile.mkdtemp(prefix="post-kanon38-")
    src = open(os.path.join(FIXTURES, "red", "18-no-oral.txt"), encoding="utf-8").read()
    for i, head in enumerate(forms):
        body = src.replace("🧱 **Разбор без единого знака живого голоса**", head, 1)
        with open(os.path.join(pkg, f"p{i}.txt"), "w", encoding="utf-8") as f:
            f.write(body)
    return pkg


_K38_ARGS = ["--form-goal", "reactions", "--form-class", "razbor",
             "--allow-skeleton-repeat", "тест оси формы заголовка"]


def test_kanon38_stamp_fails():
    """Канон п.38: серийный штамп (одна форма заголовка > 50% пакета) = FAIL.

    Пакет-штамп: 5 соседей ОДНОЙ формы с проверяемым постом = 6/6 = 100%.
    Это тот самый кейс владельца «18 заголовков из 20 по одной формуле»."""
    stamp = ["🧱 **Первый заголовок ровно той же формы**",
             "🧱 **Второй заголовок ровно той же формы**",
             "🧱 **Третий заголовок ровно той же формы**",
             "🧱 **Четвёртый заголовок той же формы**",
             "🧱 **Пятый заголовок ровно той же формы**"]
    pkg = _kanon38_pkg(stamp)
    rc, out = run_lint("18-no-oral.txt", _K38_ARGS + ["--package", pkg])
    ok = rc == 1 and "форма заголовка занимает" in out and "> 50%" in out
    record("канон п.38: штамп (одна форма > 50% пакета) = FAIL", ok, out[-600:] if not ok else "")


def test_kanon38_real_package_passes():
    """Канон п.38 × п.70: пакет дня из ЖИВЫХ форм проходит.

    Формы взяты из принятого владельцем пакета Д18 (_pakety-0608, замер Д10:
    6 уникальных форм на 21 единицу, максимальная доля 48%). Здесь 6 соседей
    четырёх разных форм: доля формы проверяемого поста 2/7 = 29% - повтор в
    пакете ЕСТЬ (иначе при 8 каналах и 17-21 единице он неизбежен по Дирихле),
    но штампа нет, и FAIL по п.38 не выносится."""
    live = ["Четыре документа, без которых нельзя брать деньги через интернет",
            "Обычный вопрос нейросети даёт обычный ответ",
            "🔔 **Что происходит, когда человек пишет тебе в директ, а ты спишь**",
            "📬 **Три цифры, из-за которых письма не открывают**",
            "🎛 **Я не рисую карусели и не открываю редактор совсем**",
            "🧱 **Ещё один заголовок формы проверяемого поста**"]
    pkg = _kanon38_pkg(live)
    rc, out = run_lint("18-no-oral.txt", _K38_ARGS + ["--package", pkg])
    ok = "форма заголовка занимает" not in out
    record("канон п.38: живой пакет дня (повтор есть, штампа нет) не валится", ok,
           out[-600:] if not ok else "")


def test_kanon38_card_body_unwrapped():
    """Ось формы меряет ЗАГОЛОВОК ПОСТА, а не служебную шапку карточки пакета.

    Боевые файлы пакета - карточки: сверху «Порядок / Слот-время / Канал…»,
    пост внутри ```-блока. До Д10 отпечаток формы считался по шапке, у всех
    карточек он одинаковый (замер: 2 уникальные формы на 21 файл вместо 6),
    то есть ось физически меряла метаданные."""
    pkg = tempfile.mkdtemp(prefix="post-kanon38-card-")
    src = open(os.path.join(FIXTURES, "red", "18-no-oral.txt"), encoding="utf-8").read()
    card = ("Порядок: 2\nСлот-время: 12:00\nКанал: ЗАКР\nКартинка: нет\n\n"
            "```\n" + src.replace("🧱 **Разбор без единого знака живого голоса**",
                                  "Совсем другая форма заголовка строчными без эмодзи", 1)
            + "```\n")
    with open(os.path.join(pkg, "card.md"), "w", encoding="utf-8") as f:
        f.write(card)
    rc, out = run_lint("18-no-oral.txt", _K38_ARGS + ["--package", pkg])
    ok = "форма заголовка занимает" not in out and "форма заголовка совпадает" not in out
    record("канон п.38: форма считается по телу поста из карточки, не по шапке", ok,
           out[-600:] if not ok else "")


def test_kanon42_56_inferential_does_not_close_floor():
    """Канон п.42 × п.56: выводной маркер не закрывает пол причинных связок.

    До Д10 один список нёс и содержательные связки, и выводные («поэтому»,
    «значит»), поэтому пост на одних выводных проходил п.42 - ровно то, что
    запрещает п.56. Теперь пол закрывают только содержательные."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("lp", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    only_infer = "Система работает. Поэтому лиды идут. Значит, так что всё получается"
    substantive = "Лиды идут, потому что система работает"
    ok = (lp.check_causal_links(only_infer) == 0
          and len(lp.check_inferential_links(only_infer)) >= 3
          and lp.check_causal_links(substantive) >= 1)
    record("канон п.42/п.56: выводные маркеры пол не закрывают, считаются отдельно", ok,
           f"infer_floor={lp.check_causal_links(only_infer)} "
           f"markers={lp.check_inferential_links(only_infer)} "
           f"subst={lp.check_causal_links(substantive)}" if not ok else "")


W15_TESTS = [test_w15_rhythm_median, test_w15_punch_warn, test_w15_glue_warn,
             test_w15_glossary_warn, test_w15_showcase_hook, test_w15_no_oral,
             test_w15_no_oral_downgrade, test_w15_homework_soft,
             test_w15_package_wave_fail, test_w15_package_low_resolution_no_fail,
             test_w15_package_downgrade,
             test_kanon38_stamp_fails, test_kanon38_real_package_passes,
             test_kanon38_card_body_unwrapped,
             test_kanon42_56_inferential_does_not_close_floor]


# ---------------------------------------------------------------------------
# ДЕФЕКТ 2 (раунд 9, по решению автора) - класс R2-1-b, абзацы-абстракции без
# словарных маркеров (check_paragraph_substance, lint-post.py). Не входит в
# счёт "13 классов R2" выше - это ДОПОЛНЕНИЕ к R2-1 (вода), не новый класс
# из R2-feedback-taxonomy.md, отдельная секция намеренно.
# ---------------------------------------------------------------------------

def test_red_substance_abstraction():
    """RED: «пост из абстрактных абзацев брака владельца» - 14-substance-abstraction.txt
    воспроизводит живой брак дословно («Показываю, что у меня стоит, потому что
    дыра эта общая...», вердикт владельца «0 ценности просто вода») + 3 абзаца той же
    формы. 4/4 длинных абзаца без конкретика-токена -> доля 1.0 >= порога 0.8 ->
    ОБЯЗАН ворнить по substance в классе razbor (WARN, не HARD - см. admission в
    докстринге check_paragraph_substance; "падать/ворнить" - оба исхода допустимы,
    здесь конкретно WARN)."""
    rc, out = run_lint("14-substance-abstraction.txt", ["--form-goal", "reactions", "--form-class", "razbor"])
    ok = "[WARN] абзацы-абстракции" in out and "4/4" in out
    record("R2-1-b абзацы-абстракции razbor (14-substance-abstraction.txt)", ok, out[-500:] if not ok else "")


def test_green_substance_narrative_excluded():
    """GREEN-контроль: donor-492 (narrative, "B-нарратив", лучший образец жанра) НЕ
    должен падать/ворнить по substance - класс narrative исключён из проверки
    осознанно (admission-тест: 0% донор-нарративов без абстрактных абзацев -
    абстракция там норма жанра, см. докстринг check_paragraph_substance)."""
    fixture = os.path.join(FIXTURES, "green", "donor-492.txt")
    rc, out = run_lint_file(fixture, ["--form-goal", "reactions", "--form-class", "narrative"]
                             + COMMON_GREEN_FLAGS)
    ok = "абзацы-абстракции" not in out
    record("green-контроль: donor-492 narrative не трогается substance-проверкой (не применяется к narrative)",
           ok, out[-500:] if not ok else "")

# ---------------------------------------------------------------------------
# GREEN-фикстуры: 7 донор-постов (Донор-А/Донор-Б) + 3 финала владельца. Критерий -
# ноль [FAIL] в разделе "v2.0: ..." вывода lint (см. докстринг модуля).
# Набор bench-эталонов ШИРЕ этого манифеста - 11 постов трёх доноров в
# scripts/etalons.json; третий донор и razbor-эталон Донор-Б (1833)
# в green не приняты (см. докстринг модуля).
# ---------------------------------------------------------------------------

GREEN_MANIFEST = [
    {"file": "donor-504.txt", "form_goal": "reactions", "form_class": "narrative"},
    {"file": "donor-492.txt", "form_goal": "reactions", "form_class": "narrative"},
    {"file": "donor-1372.txt", "form_goal": "reactions", "form_class": "narrative"},
    {"file": "donor-433.txt", "form_goal": "reactions", "form_class": "razbor"},
    {"file": "donor-1455.txt", "form_goal": "sales", "form_class": "sales"},
    {"file": "donor-440.txt", "form_goal": "sales", "form_class": "sales"},
    {"file": "donor-1579.txt", "form_goal": "sales", "form_class": "sales"},
    {"file": "ivan-final-0.txt", "form_goal": "sales", "form_class": "sales"},
    {"file": "ivan-final-1.txt", "form_goal": "sales", "form_class": "sales"},
    {"file": "ivan-final-2.txt", "form_goal": "sales", "form_class": "sales"},
]

# 🔴 РАЗДЕЛЕНИЕ ФЛАГОВ (п.10 скептик-раунда 3, по решению автора). Раньше ОДИН набор
# COMMON_GREEN_FLAGS с `--allow-no-premium-hook` вешался на все 10 green-фикстур
# разом - и маска молча покрывала оба разных случая. Теперь честно:
#   COMMON_GREEN_FLAGS - общие послабления донорского корпуса (чужие тексты
#     физически не обязаны нести форматные законы автора: em-dash, точки в конце
#     абзаца, двоеточия, повтор скелета между донорами одного канала).
#   IVAN_FINAL_ONLY_FLAGS - `--allow-no-premium-hook` ТОЛЬКО для ivan-final-*, и
#     это задокументированное историческое исключение: открыт источник
# приватный корпус владельца, файл финалов по решению автора - у всех трёх
#     финалов первая строка `**жирный заголовок**` БЕЗ эмодзи, потому что правило
# «эмодзи + пробел + жирный» автор ввёл по решению автора, ПОЗЖЕ этих постов.
#     Дописать эмодзи в фикстуру = подогнать архивный факт под более поздний закон.
# Доноры (donor-*) прогоняются БЕЗ этой маски: если донор упадёт на хук-эмодзи -
# это должно быть видно, а не спрятано под общим флагом.
COMMON_GREEN_FLAGS = ["--allow-em-dash", "--allow-end-period", "--allow-colons",
                      "--allow-skeleton-repeat", "green-fixture",
                      # 🔴 4c (по решению автора). Два новых закона АВТОРА про СВОИ посты,
                      # которым чужой донор-текст не обязан - ровно та же логика, что
                      # у --allow-em-dash/--allow-end-period выше.
                      #   плотность идей (канон п.19, «в каждом посте 90% вырезать»):
                      #     замер донор-корпуса - donor-492 даёт 0.00 конкретики/1000,
                      #     donor-433 - 0.74, при поле 1.0. Это чужие тексты 2024-2025,
                      # закон п.19 сформулирован владельцем.
                      #   метафоры (канон п.49): donor-1455 несёт «это тоже путь»,
                      #     donor-1579 - «открываю дверь». Тотальный запрет переносных
                      # значений - личное правило владельца от этой редакции, донору оно не закон.
                      # На green-ivan/ (посты САМОГО владельца) обе маски НЕ вешаются: там
                      # оба порога держатся честно, кроме одного архивного случая
                      # b17-3-0508 (см. GREEN_IVAN_MANIFEST ниже).
                      "--allow-low-density",
                      "донор-корпус: чужие тексты, закон п.19 (по решению автора) о постах автора",
                      "--allow-metaphor",
                      "донор-корпус: чужие тексты, закон п.49 (по решению автора) о постах автора"]

IVAN_FINAL_ONLY_FLAGS = ["--allow-no-premium-hook",
                         "историческое исключение: финалы по решению автора старше правила "
                         "«эмодзи + пробел + жирный заголовок» (введено по решению автора)",
                         # 🔴 по решению автора (скептик-раунд 4, ВАЖНО 7). До этого дня
                         # check_ps_action знал из канон-файла только бот-маркеры
                         # (start=…/…_bot) и на этих трёх постах возвращал «не
                         # применяется»: их дверь - домен-лендинг. Логика хука
                         # (боты + домены) портирована в линтер, и проверка на них
                         # ЗАРАБОТАЛА - показав, что приписки в них действительно нет.
                         # УЛИКА: источник приватный корпус владельца, 
                         # файл финалов по решению автора приватного корпуса, блоки INF·K1/K2/K3 (стр. 1-63) - у всех
                         # трёх последние строки это CTA + голый URL лендинга, строки
                         # «…без впн… войти можно здесь» нет ни в одном. Фикстура =
                         # архивный факт того, что автор одобрил, поэтому дописать в неё
                         # приписку значит подделать архив. Маска узкая (только
                         # ivan-final-*), а работоспособность самой проверки держит
                         # отдельный позитивный тест test_ps_action_landing ниже.
                         "--allow-no-psa",
                         "архивные финалы по решению автора (INF·K1/K2/K3) выданы без приписки; "
                         "фикстура повторяет источник финалов по решению автора в приватном корпусе дословно",
                         # 🔴 по решению автора (URL-фикс живого слоя, проверка витрины).
                         # До фикса «?» внутри https://...?utm_source=... засчитывался
                         # как «вопрос ×1» - на этом ivan-final-1 проходил живой слой.
                         # После вырезания URL честный замер: у финала по решению автора живых
                         # знаков НОЛЬ (проверено: скобки 0, многоточия 0, вопросы 0
                         # вне URL). Закон живого слоя введён по решению автора - ПОЗЖЕ архива;
                         # дописать скобку в фикстуру = подделать архив. Маска узкая,
                         # новые посты идут под HARD без исключений (хук --allow-no-oral
                         # через state не пропускает).
                         "--allow-no-oral",
                         "архивный финал по решению автора старше закона живого слоя (по решению автора); "
                         "живых знаков вне URL в источнике ноль - факт архива",
                         # 🔴 по решению автора, раунд 1 (находка 5). Класс «ярлыки-
                         # рубрикаторы» поднят WARN -> HARD: автор запретил формульные
                         # блоки построчно в разборе эталона 6.08. Финалы по решению автора старше
                         # запрета и несут «Честная граница» абзацем (ivan-final-0 и -2,
                         # улика - прогон check_rubricator_openers по корпусу). Дописать
                         # абзац в фикстуру значит подделать архив, поэтому оговорка, а
                         # не понижение порога. Маска узкая: новые посты идут под HARD.
                         "--allow-rubricator",
                         "архивные финалы старше разбора эталона по решению автора, где "
                         "формульные блоки «честная граница» запрещены построчно"]


def green_flags(entry):
    """Флаги под конкретную green-фикстуру (см. комментарий выше)."""
    flags = list(COMMON_GREEN_FLAGS)
    if entry["file"].startswith("ivan-final-"):
        flags += IVAN_FINAL_ONLY_FLAGS
    return flags


def test_green(entry):
    path = green_path(entry["file"])
    if path is None:
        skip(f"green {entry['file']} (v2.0-гейты чисты)", NO_OWNER_CORPUS)
        return
    args = ["--form-goal", entry["form_goal"]]
    if entry.get("form_class"):
        args += ["--form-class", entry["form_class"]]
    args += green_flags(entry)
    rc, out = run_lint_file(path, args)
    section = v2_section(out)
    hard_fails = [l for l in section.splitlines() if l.strip().startswith("[FAIL]")]
    ok = len(hard_fails) == 0
    detail = "\n".join(hard_fails)
    record(f"green {entry['file']} (v2.0-гейты чисты)", ok, detail)


def test_green_ivan_full(entry):
    """Финалы владельца БЕЗ маски класса «код-слово» (п.11 скептик-раунда 2, по решению автора).

    Критерий здесь строже, чем у test_green: ноль [FAIL] во ВСЁМ выводе lint, а не
    только в разделе v2.0. Прецедент: `check_banned_dev_objection` ловил штатный
    термин воронок «код-слово» (дефис = граница слова у `\\bкод\\b`) - три одобренных
    Владельцем финала по решению автора падали HARD на легальном слове, и это не было видно,
    потому что green-критерий смотрел только раздел v2.0. Регекс починен
    (`\\bкод\\b(?!-)`), тест держит починку.

    🔴 Маска `--allow-no-premium-hook` ОСТАЁТСЯ, и это честно: открыт источник
    финалов по решению автора в приватном корпусе владельца - у всех трёх (INF·K1/K2/K3)
    первая строка это `**жирный заголовок**` БЕЗ эмодзи.
    Правило «эмодзи + пробел + жирный заголовок» автор ввёл по решению автора (05-publish
    п.1d), то есть ПОЗЖЕ этих постов. Дописывать эмодзи в фикстуру = подгонять
    архивный факт под более поздний закон, поэтому фикстуры оставлены как в
    источнике, а класс снят флагом. С этой редакции этот флаг живёт отдельным
    набором IVAN_FINAL_ONLY_FLAGS и на доноров не распространяется."""
    path = green_path(entry["file"])
    if path is None:
        skip(f"финал автора без маски «код-слово»: {entry['file']}", NO_OWNER_CORPUS)
        return
    args = ["--form-goal", entry["form_goal"], "--form-class", entry["form_class"]]
    args += green_flags(entry)
    rc, out = run_lint_file(path, args)
    hard_fails = [l for l in out.splitlines() if l.strip().startswith("[FAIL]")]
    hard_fails = drop_element_floor_fails(hard_fails, entry["file"])
    record(f"ivan-final без маски «код-слово»: {entry['file']} (ноль [FAIL] во всём выводе)",
           not hard_fails, "\n".join(hard_fails))


def test_ps_action_landing():
    """ВАЖНО 7 (скептик-раунд 4, по решению автора): P.S.-Action РАБОТАЕТ на посте, чья дверь -
    домен-лендинг из канон-файла, а не бот-код.

    Раньше `check_ps_action` брал из PS-ACTION-канон.md только `start=…`/`…_bot`, а
    доменную часть знал ТОЛЬКО хук - линтер печатал «не применяется» и это была ложь:
    ровно посты запуска с лендингом в CTA проверку и не проходили. Тест позитивный:
    берём ivan-final-0 (в нём голый URL лендинга), убеждаемся, что БЕЗ приписки гейт
    ловит MISSING, а С припиской - OK. Если личного канон-файла на машине нет
    (ученик), тест самоустраняется - проверка изолирована by design."""
    import glob as _glob
    canon = (_glob.glob(os.path.expanduser(".business/запуски/*/PS-ACTION-канон.md"))
             + _glob.glob(os.path.expanduser("~/.business/запуски/*/PS-ACTION-канон.md")))
    if not canon:
        skip("ps_action на лендинге", "личного канон-файла PS-ACTION на машине нет, "
                                      "проверка изолирована by design")
        return
    fixture = owner_fixture("green", "ivan-final-0.txt")
    if fixture is None:
        skip("ps_action на лендинге", NO_OWNER_CORPUS)
        return
    sys.path.insert(0, SCRIPTS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_mod", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    src = open(fixture, encoding="utf-8").read()
    got_bare = lp.check_ps_action(src, "osn")
    got_with = lp.check_ps_action(
        src + "\nСайт быстрее открывается без впн, а если не работает то войти можно здесь\n",
        "osn")
    record("ps_action на лендинге: без приписки MISSING, с припиской OK "
           "(доменные маркеры канона портированы из хука)",
           got_bare == "MISSING" and got_with == "OK",
           f"без приписки={got_bare}, с припиской={got_with}")


def test_bench_smoke(entry):
    """Дополнительно: bench-post.py прогоняется на каждом green без исключения (smoke)."""
    path = green_path(entry["file"])
    if path is None:
        skip(f"bench-post smoke {entry['file']}", NO_OWNER_CORPUS)
        return
    # 🔴 --against-etalons с этой редакции гонят ВСЕ ПЯТЬ точек прогона бенча (03-dry
    # Шаг 3.5 · 01d-rewrite Шаг 3.6 · процедурный шаг E3 (0.49-К) · 05-publish Шаг
    # 1c-bis серийная выдача (дописано Д63 раунда 18 - без счётчика-слова свип Р16
    # её пропустил) · `_bench_args` хука post-phase-gate.sh, авто на каждом маршруте),
    # поэтому smoke обязан ходить тем же путём - иначе ветка сверки с донор-эталонами
    # и печать строки микса живут без единого теста и ломаются молча.
    args = [sys.executable, BENCH, path, "--form-goal", entry["form_goal"], "--against-etalons"]
    if entry.get("form_class"):
        args += ["--form-class", entry["form_class"]]
    # bench-post.py не принимает --allow-* флагов, поэтому green_flags тут не нужны
    p = subprocess.run(args, capture_output=True, text=True)
    # 🔴 п.12 (скептик-раунд 4, по решению автора): было `returncode in (0, 1)` - то есть
    # ПРОВАЛ бенча (rc=1) засчитывался как успех smoke-теста, и тест не мог покраснеть
    # никогда. Это green-фикстуры: у них бенч обязан отработать чисто.
    ok = (p.returncode == 0) and ("ВЕРДИКТ: FAIL" not in p.stdout)
    # контракт --against-etalons: либо строка микса доноров, либо честная строка
    # мягкой деградации. Молчание = флаг проглочен и сверки не было.
    etalon_line = ("микс эталонов:" in p.stdout) or ("эталоны недоступны" in p.stdout)
    ok = ok and etalon_line
    detail = ""
    if not ok:
        detail = f"rc={p.returncode}; микс/деградация напечатаны: {etalon_line}; " + " / ".join(
            l for l in p.stdout.splitlines() if l.startswith(("[FAIL]", "ВЕРДИКТ")))[:400]
    record(f"bench-post smoke {entry['file']}", ok, detail)


def test_bench_pair_coercion_loud():
    """Д79 скептик-раунда 26 (по решению автора, «две руки»-дефект). lint-post.py кричит
    подмену класса строкой [ФОРМА-КОЭРЦИЯ] (Д71 раунда 22, см.
    test_lint_pair_coercion_loud) - bench-post.py резолвит ТОТ ЖЕ профиль через
    LINT.resolve_form_profile (bench-post.py:244) и молчал о коэрции: модульная
    LAST_FORM_COERCION нигде в bench-post.py не читалась (grep до фикса - 0
    вхождений). Оператор видел «микс эталонов: narrative - ...» на паре
    reactions×sales и не мог узнать, что brief.form_class=sales был отброшен, а
    сверка шла классом narrative. Проверяем ОБА конца: нелегальная пара печатает
    строку РЯДОМ с миксом (до него), легальная пара - не печатает ничего.

    🔴 Д83 скептик-раунда 27 (по решению автора, рецидив Д79 внутри того же файла):
    печать строки жила ВНУТРИ ветки `if args.against_etalons`, а подмена
    профиля (и пороги, которые она подставляет) считается на КАЖДОМ прогоне
    `bench_post()` независимо от флага - оператор, гонявший нелегальную пару
    БЕЗ `--against-etalons` (например быстрый прогон reactions×sales без
    сверки с донорами), видел WARN/FAIL по чужому коридору класса без единого
    сигнала о подмене. Третий прогон ниже (`bad_noflag`) повторяет нелегальную
    пару БЕЗ флага и требует строку - тем же способом, каким test_lint_pair_-
    coercion_loud проверяет lint-post.py."""
    p = _tmp_post(EVENT_POST_OK)
    try:
        bad = subprocess.run([sys.executable, BENCH, p, "--form-goal", "reactions",
                               "--form-class", "sales", "--against-etalons"],
                              capture_output=True, text=True)
        bad_noflag = subprocess.run([sys.executable, BENCH, p, "--form-goal", "reactions",
                                      "--form-class", "sales"],
                                     capture_output=True, text=True)
        ok_run = subprocess.run([sys.executable, BENCH, p, "--form-goal", "reactions",
                                  "--form-class", "narrative", "--against-etalons"],
                                 capture_output=True, text=True)
    finally:
        os.unlink(p)
    bad_out = bad.stdout + bad.stderr
    noflag_out = bad_noflag.stdout + bad_noflag.stderr
    ok_out = ok_run.stdout + ok_run.stderr
    bad_lines = bad_out.splitlines()
    said = [l.strip() for l in bad_lines if l.startswith("[ФОРМА-КОЭРЦИЯ]")]
    said_noflag = [l.strip() for l in noflag_out.splitlines() if l.startswith("[ФОРМА-КОЭРЦИЯ]")]
    leaked = [l.strip() for l in ok_out.splitlines() if l.startswith("[ФОРМА-КОЭРЦИЯ]")]
    mix_idx = next((i for i, l in enumerate(bad_lines) if l.startswith("микс эталонов:")), None)
    coercion_idx = next((i for i, l in enumerate(bad_lines) if l.startswith("[ФОРМА-КОЭРЦИЯ]")), None)
    before_mix = coercion_idx is not None and mix_idx is not None and coercion_idx < mix_idx
    good = (len(said) == 1 and "«sales»" in said[0] and "«narrative»" in said[0]
            and mix_idx is not None and before_mix and not leaked
            and len(said_noflag) == 1 and "«sales»" in said_noflag[0] and "«narrative»" in said_noflag[0])
    record("Д79/Д83 бенч: reactions×sales печатает [ФОРМА-КОЭРЦИЯ] до строки микса "
           "С флагом, РОВНО ОДИН РАЗ БЕЗ флага --against-etalons, "
           "reactions×narrative - ни одной строки",
           good,
           ("на подмене+флаг: %s (микс найден=%s, коэрция до микса=%s); "
            "на подмене БЕЗ флага: %s; на легальной паре: %s"
            % (said or "СТРОКИ НЕТ", mix_idx is not None, before_mix,
               said_noflag or "СТРОКИ НЕТ", leaked or "чисто")))


# ---------------------------------------------------------------------------
# 🔴 Д54 (скептик-раунд 13, по решению автора): «НИЗ ЖЁСТКИЙ» ОБЪЯВЛЕН НА ВЕСЬ НАБОР,
# А ЯДРО ЕГО НАРУШАЕТ. Правило «низ коридора класса отсекает жёстко» родилось
# раундом 4 на пересеве razbor, но записано было как свойство ВСЕГО набора
# эталонов (SKILL.md, докстринг bench-post.py, 02d Шаг 0.5). При этом исходное
# ядро v2.0 отбиралось по ER-топам ДО правила, и две его записи низ пробивают:
# Донор-А:440 (430 зн. против низа sales 759) и Донор-А:492 (358 против 362).
# Решение оркестратора: ядро НЕ пересеиваем (каскад по green-фикстурам,
# admission-числам и покрытию микса дороже выгоды), область правила уточняем
# честно, а КЛАСС закрываем стражем ниже - будущий эталон ниже низа не пролезет.
# Легаси-исключения печатаются строкой, но FAIL не дают.
# ---------------------------------------------------------------------------

ETALONS_JSON = os.path.join(SCRIPTS, "etalons.json")

# Ядро v2.0 - те самые 7 записей, что стояли в наборе до третьего донора и до
# пересевов раундов 4-5 (докстринг bench-post.py, SKILL.md changelog v2.2).
# Список ЯВНЫЙ и закрытый: всё, чего в нём нет, - новый эталон, и он обязан
# держать низ своего класса.
ETALON_LEGACY_CORE_V20 = (
    "Донор-А:504", "Донор-А:492", "Донор-А:433", "Донор-А:440",
    "Донор-Б:1372", "Донор-Б:1455", "Донор-Б:1579",
)


def _etalon_floor(lp, cls):
    """Нижний коридор класса из ЖИВЫХ FORM_PROFILES линтера (не из копии чисел).

    Цель выводится так же, как её выводит resolve_form_profile: reactions
    различает narrative/razbor, остальные классы совпадают с целью."""
    goal = "reactions" if cls in ("narrative", "razbor") else cls
    prof, _key = lp.resolve_form_profile(goal, cls)
    if not prof:
        return None
    return prof.get("length_min")


def test_etalon_floor_discipline():
    """Д54: каждый НЕ легаси-эталон >= нижнего коридора своего класса.

    Длина меряется ровно тем же способом, каким её меряет bench-post.py
    (`_strip_md_plain`), иначе страж и боевая мерка разошлись бы на разметке."""
    if not os.path.isfile(ETALONS_JSON):
        record("Д54 дисциплина низа: новые эталоны не короче коридора класса",
               False, "нет %s - набор эталонов раздаётся со скиллом, "
                      "его отсутствие = поломка пакета" % ETALONS_JSON)
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_floor", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    with open(ETALONS_JSON, encoding="utf-8") as f:
        etalons = json.load(f)

    problems, legacy_notes, checked = [], [], 0
    for e in etalons:
        uid = e.get("uid") or f"id:{e.get('id')}"
        cls = e.get("form_class")
        floor = _etalon_floor(lp, cls)
        chars = len(lp._strip_md_plain(e.get("text", "")))
        if floor is None:
            continue  # у event/gate/forwards нижнего коридора в профиле нет
        if uid in ETALON_LEGACY_CORE_V20:
            if chars < floor:
                legacy_notes.append(f"{uid} ({cls}: {chars} < {floor})")
            continue
        checked += 1
        if chars < floor:
            problems.append(f"{uid} - класс {cls}, {chars} зн. против низа {floor}: "
                            "правило «низ жёсткий» действует на НОВЫЕ эталоны, "
                            "легаси-ядро v2.0 сюда не относится")
    if not checked:
        problems.append("ни один НЕ легаси-эталон не проверен - список "
                        "ETALON_LEGACY_CORE_V20 накрыл весь набор, страж обезоружен")
    if legacy_notes:
        print("       известные исключения ядра: " + " · ".join(legacy_notes)
              + " (ядро v2.0 отбиралось по ER-топам до правила, не FAIL)")
    record("Д54 дисциплина низа: новые эталоны не короче коридора класса "
           f"(проверено {checked}, легаси {len(legacy_notes)})",
           not problems, " · ".join(problems))


# ===========================================================================
# 🔴 Д106 (скептик-раунд 37, по решению автора): ОДИНОКИЕ СТРОКИ `**` (МАРКАП-
# АРТЕФАКТ ВЫГРУЗКИ) ЛОМАЛИ check_air И check_bold_count РАЗНЫМИ СПОСОБАМИ.
# ===========================================================================
# 4 эталона `scripts/etalons.json` несут строки, состоящие ТОЛЬКО из `**`
# (жирный, разорванный границей абзаца при экспорте донорского корпуса) -
# Донор-Б:1455 (1), Донор-А:440 (1), Донор-Б:1579 (3), Донор-В:165 (2).
# check_air считал такую строку НЕПУСТОЙ - она съедала место честной пустой
# строки-разделителя и рушила воздух (Донор-В:165: 0.69 вместо ~0.93).
# check_bold_count регексом без `re.S` не считал жирный, чьи `**` стоят на
# РАЗНЫХ строках - Донор-В:165 давал bold_n=0 при bold_share_pct=10.9%
# (bench-post.py measure_form, свой регекс С `re.S`) - число выделений
# противоречило доле их символов, сигнал был перевёрнут.
# ФИКС (см. lint-post.py): (а) check_air нормализует одинокие строки `**` в
# пустые ПЕРЕД замером (`_strip_stray_bold_lines`); (б) check_bold_count
# переведён на ТОТ ЖЕ паттерн+флаг, что уже держит bold_share_pct -
# `\*\*(.+?)\*\*` + `re.S` - оба числа считаются по ОДНОМУ множеству
# совпадений, противоречие «bold_n=0 при share>0» структурно невозможно.
# `_strip_md_plain` (длина эталона) НЕ тронута - оба фикса живут только в
# check_air/check_bold_count, длина эталонов в каскаде не сдвигается
# (проверено живым прогоном при правке: Донор-А:433 - 1359, как и было).
# ===========================================================================

_D106_AFFECTED_ETALONS = ("Донор-Б:1455", "Донор-А:440", "Донор-Б:1579",
                           "Донор-В:165")


def test_d106_stray_bold_line_normalization():
    """Д106: одинокие строки `**` (маркап-артефакт выгрузки) не портят
    check_air/check_bold_count - синтетический кейс + живой корпус.

    Три проверки:
      (1) СИНТЕТИКА air: текст с одинокой строкой `**` НА МЕСТЕ честной
          пустой строки-разделителя даёт ТОТ ЖЕ воздух, что текст с этой
          строкой действительно пустой (артефакт не должен отличаться от
          отсутствия артефакта).
      (2) СИНТЕТИКА bold: жирный, чьи `**` стоят на разных строках (реальный
          многоабзацный жирный, не артефакт), обязан засчитываться - раньше
          такой span давал `bold_n=0`.
      (3) ЖИВОЙ КОРПУС: на всех 4 задетых эталонах `scripts/etalons.json`
          противоречие «bold_n=0 при bold_share_pct>0» отсутствует, а
          Донор-В:165 (эталон с максимальным перекосом) даёт воздух >= 0.9
          и bold_n >= 2 (живой замер после фикса: air=0.93, bold_n=2)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_d106", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)

    problems = []

    # --- (1) синтетика air: строка "**" на месте пустой строки-разделителя ---
    clean_air = ("первая строка абзаца один\n"
                 "\n"
                 "вторая строка после честной пустой\n"
                 "\n"
                 "третья строка после ещё одной честной пустой\n")
    dirty_air = clean_air.replace("\nвторая", "**\nвторая", 1)
    a_clean = lp.check_air(clean_air)
    a_dirty = lp.check_air(dirty_air)
    if abs(a_clean - a_dirty) > 1e-9:
        problems.append(f"check_air: чистый текст={a_clean:.4f}, тот же текст со "
                        f"строкой ** вместо пустой={a_dirty:.4f} - должны совпасть "
                        "(артефакт не контент)")

    # --- (2) синтетика bold: жирный текст через границу абзаца ---
    bold_two_para = "**жирный текст первой части\n\nи второй части того же выделения**"
    bc = lp.check_bold_count(bold_two_para)
    if bc < 1:
        problems.append(f"check_bold_count: жирный текст через границу абзаца "
                        f"не посчитан ({bc}, ждали >= 1)")

    # --- (3) живой корпус: 4 задетых эталона + опорный Донор-В:165 ---
    if not os.path.isfile(ETALONS_JSON):
        problems.append("нет %s - набор эталонов раздаётся со скиллом, "
                        "живая половина теста не прогнана" % ETALONS_JSON)
    else:
        with open(ETALONS_JSON, encoding="utf-8") as f:
            etalons = json.load(f)
        by_uid = {e.get("uid"): e for e in etalons if isinstance(e, dict)}
        for uid in _D106_AFFECTED_ETALONS:
            e = by_uid.get(uid)
            if e is None:
                problems.append(f"эталон {uid} не найден в наборе - состав "
                                "etalons.json изменился, страж Д106 сверяет "
                                "устаревший список")
                continue
            text = e.get("text", "")
            plain = lp._strip_md_plain(text)
            bold_n = lp.check_bold_count(text)
            bold_chars = sum(len(m) for m in re.findall(r"\*\*(.+?)\*\*", text, re.S))
            bold_share = 100 * bold_chars / max(len(plain), 1)
            if bold_share > 0 and bold_n < 1:
                problems.append(f"{uid}: bold_n={bold_n} при bold_share_pct="
                                f"{bold_share:.1f} - противоречие живо (Д106 не "
                                "закрыт)")
        top = by_uid.get("Донор-В:165")
        if top is not None:
            air_top = lp.check_air(top.get("text", ""))
            bold_top = lp.check_bold_count(top.get("text", ""))
            if air_top < 0.9:
                problems.append(f"Донор-В:165: воздух={air_top:.3f}, ждали >= 0.9 "
                                "(живой замер после фикса - 0.93)")
            if bold_top < 2:
                problems.append(f"Донор-В:165: bold_n={bold_top}, ждали >= 2 "
                                "(живой замер после фикса - 2)")

    record("Д106: одинокие строки ** (маркап-артефакт выгрузки) не портят "
           "check_air/check_bold_count (синтетика + 4 задетых эталона живого корпуса)",
           not problems, " · ".join(problems))


# ===========================================================================
# Д62 (скептик-раунд 17, по решению автора): ПЕР-ЗАПИСЬ ВАЛИДАЦИЯ `load_etalons()`
# ===========================================================================
# Прецедент: `load_etalons()` ловил только «файла нет / не парсится / не
# список», но `compare_to_etalons` брал `e["text"]`/`e["id"]`/`e["author"]`
# БЕЗ `.get()` - одна запись без любого из ключей валила бенч KeyError-ом
# (exit 1, ВЕРДИКТ не печатался), а хук `post-phase-gate.sh` грепает строку
# «ВЕРДИКТ:» и на её отсутствие даёт ложный BLOCK «ИНФРАСТРУКТУРА» на КАЖДОЙ
# выдаче. Фикс - пер-записи валидация в `load_etalons()` (обязательные ключи
# `text`/`id`/`author`/`form_class`, битые записи отбрасываются с [INFO],
# ВЕРДИКТ и exit-код не меняются ни в одном случае).
#
# Тесты ниже гоняют bench-post.py во ВРЕМЕННОЙ ИЗОЛИРОВАННОЙ копии (свой
# bench-post.py + lint-post.py + подменный etalons.json в tempdir) - живой
# `scripts/etalons.json` скилла (11 эталонов) ни при каком исходе теста не
# читается и не пишется.

_D62_TEST_POST = (
    "**Тестовый нарратив для проверки дефекта Д62.**\n\n"
    "Это временный текст поста, собранный только ради прогона bench-post.py "
    "в изолированной копии скрипта против подменного etalons.json - живой "
    "набор эталонов скилла этот прогон не трогает ни при каком исходе.\n\n"
    "Строка нужна ради длины и формы, содержательного смысла тут нет."
)


def _etalon_row(**overrides):
    """Базовая ВАЛИДНАЯ запись эталона (несёт все обязательные + опциональные
    ключи схемы load_etalons). overrides перекрывают/добавляют поля; чтобы
    сделать запись битой - `del row["ключ"]` после вызова."""
    row = {"id": 1, "uid": "Тест:1", "author": "Тест", "form_class": "narrative",
           "er_idx": 1.0, "cls": "B-нарратив",
           "text": "Валидный текст эталона для проверки дефекта Д62 " * 6}
    row.update(overrides)
    return row


def _bench_with_etalons(records, form_class="narrative", form_goal="reactions"):
    """Гоняет bench-post.py --against-etalons в изолированном tempdir со СВОЕЙ
    копией bench-post.py + lint-post.py (importlib грузит lint-post.py по
    пути РЯДОМ с собой) и подменным etalons.json. Живой etalons.json скилла
    не трогается - тест работает над копией, не над оригиналом."""
    tmp = tempfile.mkdtemp(prefix="post-d62-etalons-")
    shutil.copy(BENCH, os.path.join(tmp, "bench-post.py"))
    shutil.copy(LINT, os.path.join(tmp, "lint-post.py"))
    with open(os.path.join(tmp, "etalons.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    post_path = os.path.join(tmp, "post.txt")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(_D62_TEST_POST)
    args = [sys.executable, os.path.join(tmp, "bench-post.py"), post_path,
            "--form-goal", form_goal, "--form-class", form_class, "--against-etalons"]
    return subprocess.run(args, capture_output=True, text=True)


def test_d62_dropped_record_missing_author():
    row = _etalon_row()
    del row["author"]
    p = _bench_with_etalons([row])
    ok = (p.returncode == 0 and "[INFO] эталоны: отброшено 1" in p.stdout
          and "ВЕРДИКТ:" in p.stdout)
    record("Д62: запись без author отброшена - [INFO] печатается, ВЕРДИКТ жив, exit 0",
           ok, "" if ok else f"rc={p.returncode}\n{p.stdout[-1000:]}\n{p.stderr[-500:]}")


def test_d62_dropped_record_missing_text():
    row = _etalon_row()
    del row["text"]
    p = _bench_with_etalons([row])
    ok = (p.returncode == 0 and "[INFO] эталоны: отброшено 1" in p.stdout
          and "ВЕРДИКТ:" in p.stdout)
    record("Д62: запись без text отброшена - [INFO] печатается, ВЕРДИКТ жив, exit 0",
           ok, "" if ok else f"rc={p.returncode}\n{p.stdout[-1000:]}\n{p.stderr[-500:]}")


def test_d62_all_records_broken_degrades():
    p = _bench_with_etalons([{"id": 1}, {"text": ""}, {"author": "без остального"}])
    ok = (p.returncode == 0 and "эталоны недоступны" in p.stdout
          and "[INFO] эталоны: отброшено 3" in p.stdout and "ВЕРДИКТ:" in p.stdout)
    record("Д62: все записи битые -> ветка «эталоны недоступны», ВЕРДИКТ жив, exit 0",
           ok, "" if ok else f"rc={p.returncode}\n{p.stdout[-1000:]}\n{p.stderr[-500:]}")


def test_d62_mixed_valid_and_broken():
    good = _etalon_row(id=2, uid="Тест:2")
    bad = _etalon_row(id=3, uid="Тест:3")
    del bad["form_class"]
    p = _bench_with_etalons([good, bad])
    ok = (p.returncode == 0 and "[INFO] эталоны: отброшено 1" in p.stdout
          and "Тест:3" in p.stdout  # битая названа в [INFO]
          and "донор Тест:2" in p.stdout  # валидная дошла до сверки
          and "микс эталонов:" in p.stdout and "ВЕРДИКТ:" in p.stdout)
    record("Д62: валидная+битая в одном наборе - битая отброшена, валидная в миксе",
           ok, "" if ok else f"rc={p.returncode}\n{p.stdout[-1000:]}\n{p.stderr[-500:]}")


def test_d62_live_etalons_untouched():
    """Страж-контроль: тесты Д62 работают НАД КОПИЕЙ, живой набор владельца
    (11 эталонов) не тронут ни одним из тестов выше."""
    if not os.path.isfile(ETALONS_JSON):
        skip("Д62: живой etalons.json не тронут тестами", NO_OWNER_CORPUS)
        return
    with open(ETALONS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    ok = isinstance(data, list) and len(data) == 11
    record("Д62: живой etalons.json не тронут тестами (11 записей на месте)",
           ok, f"нашёл {len(data) if isinstance(data, list) else type(data)} записей")


def test_r34_etalon_composition_three_authors():
    """Страж состава Р34 (скептик-раунд 34, по решению автора, дёшево ниже порога
    отдельного дефекта). ДЕФЕКТ КЛАССА: `test_d62_live_etalons_untouched` выше
    проверяет ТОЛЬКО КОЛИЧЕСТВО записей (11) - донор, у которого исчезли ВСЕ
    записи (например, ошибка мержа стёрла Донор-В, а кто-то тихо задвоил
    Донор-А до той же цифры), красит этот тест зелёным: количество совпало,
    состав - нет, и микс `bench-post.py --against-etalons` тихо потерял треть
    доноров. Живой набор несёт ТРЁХ доноров (докстринг файла, строки 19-20:
    Донор-А/Донор-Б/Донор-В) - страж держит их поимённо, а не числом."""
    if not os.path.isfile(ETALONS_JSON):
        skip("Р34 страж состава: etalons.json несёт всех трёх доноров",
             NO_OWNER_CORPUS)
        return
    with open(ETALONS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    authors = {e.get("author") for e in data} if isinstance(data, list) else set()
    need = {"Донор-А", "Донор-Б", "Донор-В"}
    missing = need - authors
    record("Р34 страж состава: etalons.json несёт всех трёх доноров "
           "(Донор-А/Донор-Б/Донор-В)",
           not missing,
           "нет донора(ов): %s (текущий состав: %s)" % (sorted(missing), sorted(authors))
           if missing else "")


D62_TESTS = (
    test_d62_dropped_record_missing_author,
    test_d62_dropped_record_missing_text,
    test_d62_all_records_broken_degrades,
    test_d62_mixed_valid_and_broken,
    test_d62_live_etalons_untouched,
    test_r34_etalon_composition_three_authors,
)


# ===========================================================================
# Д8 (по решению автора): КЛАСС `event` В ИСПОЛНЯЕМОМ СЛОЕ
# ===========================================================================
# Дефект (скептик-раунд 3, находка 8): класс `event` объявлен в workflow с
# закрытым набором 12 гейтов (01-router.md 0.49-К), а в коде слова `event` было
# 0 вхождений - линтер отбивал флаг argparse-ошибкой, post-phase-gate.sh молча
# ронял класс из argv. Тесты ниже держат ОБА конца: линтер принимает класс и
# гоняет его гейты, хук доносит класс до линтера и громко падает на неизвестном.

_EVENT_TAIL = (
    "Первое - как устроен вайбкодинг на Claude Code, чтобы он сам оркестрировал агентов ну\n\n"
    "Второе - как перестроить контент-завод под инструменты 2026 года, раз уж прежние встали\n\n"
    "У меня 2 подписки MAX, лимитов не встречаю, компьютер оставляю включённым на ночь\n\n"
    "\U0001F449 Записаться на эфир https://example.com/k?utm_source=tg&utm_content=d8\n"
)
EVENT_POST_OK = (
    "\U0001F48E **Сегодня в 19:00 пройдет концентрат про вайбкодинг и Claude Code**\n\n"
    "Разберу две вещи детально, потому что без них дальше никуда\n\n" + _EVENT_TAIL)
EVENT_POST_NO_DATETIME = (
    "\U0001F4A1 **Концентрат про вайбкодинг и Claude Code уже собран**\n\n"
    "Разберу две вещи детально, потому что без них дальше никуда\n\n" + _EVENT_TAIL)
# Плотность: одно время события на два десятка пустых предложений. Носителей
# мало, предложений много -> density далеко за порогом 3.0.
EVENT_POST_LOW_DENSITY = (
    "\U0001F48E **Сегодня в 19:00 будет важная встреча**\n\n"
    + "\n\n".join(
        f"Это по-настоящему сильная и полезная мысль номер {'один два три четыре пять шесть семь восемь девять десять'.split()[i]}, "
        f"которая точно поможет тебе выйти на новый уровень и всё изменить"
        for i in range(10))
    + "\n\n\U0001F449 Записаться https://example.com/k?utm_source=tg&utm_content=d8\n")


def _tmp_post(text):
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def test_event_class_accepted_by_lint():
    """Д8-1. `--form-class event` больше не argparse-ошибка, и класс доезжает
    до профильного слоя: линтер печатает СВОЙ профиль события, а не подменяет
    его продажей («ближайший числовой профиль», как велел роутер до Д8)."""
    p = _tmp_post(EVENT_POST_OK)
    try:
        rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "sales",
                                    "--form-class", "event"])
    finally:
        os.unlink(p)
    bad_arg = "invalid choice: 'event'" in out
    profile = "класс=event" in out and "профиль=E-событие" in out
    record("Д8 линт: --form-class event принят и включил профиль E-событие",
           (not bad_arg) and profile,
           f"rc={rc}; argparse-ошибка={bad_arg}; " + " / ".join(
               l for l in out.splitlines() if l.startswith("[ФОРМА]"))[:300])


def test_event_green_ivan(entry):
    """Д8-2. Событийные посты автора обязаны проходить ИМЕННО как event:
    ноль [FAIL] во всём выводе. Если гейт класса валит зелёный пост - чинится
    порог в lint-post.py, а не фикстура (закон калибровки этого файла)."""
    fname, channel, goal, arch = entry
    path = owner_fixture("green-ivan", fname)
    if path is None:
        skip(f"Д8 green-ivan {fname} как event", NO_OWNER_CORPUS)
        return
    rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                   "--form-class", "event"] + arch)
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith("[FAIL]")]
    fails = drop_element_floor_fails(fails, fname)
    dens = [l.strip() for l in out.splitlines() if "4.DENS" in l]
    record(f"Д8 green-ivan {fname} как event (ноль [FAIL]) · {dens[0][:70] if dens else 'нет строки 4.DENS'}",
           not fails, "\n".join(fails)[:600])


def test_event_without_datetime_fails():
    """Д8-3. Класс объявлен event, а даты и времени в теле нет - HARD.
    Это и есть лазейка, ради которой класс могли бы объявлять: у event не
    меряется доля скилла (04-review B1c), значит слово «event» без признака
    класса = способ уйти от порога."""
    p = _tmp_post(EVENT_POST_NO_DATETIME)
    try:
        rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "sales",
                                    "--form-class", "event"])
    finally:
        os.unlink(p)
    caught = any(l.startswith("[FAIL]") and "событие без даты и времени" in l
                 for l in out.splitlines())
    record("Д8 брак: event без даты/времени -> FAIL", caught and rc == 1,
           f"rc={rc}; " + " / ".join(l for l in out.splitlines() if l.startswith("[FAIL]"))[:300])


def test_event_low_density_fails():
    """Д8-4. 4.DENS: у события порог density <= 3.0 (04-review sub-stage 4.DENS).
    Пост с одним временем на десяток пустых абзацев обязан падать - у event
    плотность заменяет выключенный гейт доли скилла, а не дополняет его."""
    p = _tmp_post(EVENT_POST_LOW_DENSITY)
    try:
        rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "sales",
                                    "--form-class", "event"])
    finally:
        os.unlink(p)
    caught = any(l.startswith("[FAIL]") and "4.DENS" in l for l in out.splitlines())
    record("Д8 брак: event с плотностью хуже 3.0 -> FAIL 4.DENS", caught and rc == 1,
           f"rc={rc}; " + " / ".join(l for l in out.splitlines() if "4.DENS" in l)[:300])


def test_event_not_leaking_to_other_classes():
    """Д8-5. Гейты класса включаются ТОЛЬКО при event. Тот же пост без даты и
    времени под классом sales обязан проходить мимо них - иначе Д8 тихо ужесточил
    все остальные классы."""
    p = _tmp_post(EVENT_POST_NO_DATETIME)
    try:
        _, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "sales",
                                   "--form-class", "sales"])
    finally:
        os.unlink(p)
    leaked = [l for l in out.splitlines()
              if "событие без даты" in l or "4.DENS" in l]
    record("Д8 изоляция: гейты события не включаются на классе sales",
           not leaked, "\n".join(leaked)[:300])


# ---------------------------------------------------------------------------
# 🔴 Д71 (скептик-раунд 22, по решению автора): НЕСОВМЕСТИМАЯ ПАРА цель×класс КОЭРЦИЛАСЬ
# МОЛЧА. `resolve_form_profile` при цели != reactions класс ОТБРАСЫВАЕТ (`c = goal`),
# при цели reactions коэрцит всё лишнее в narrative. Строка `[ФОРМА]` печатает класс
# ВЗЯТЫЙ, а не заявленный, - на паре sales×narrative она выглядит как норма
# (`класс=sales`), и отличить «класс доехал» от «класс выброшен» было НЕЧЕМ. Пост
# мерился порогами чужого класса, микс - эталонами чужого класса, вердикт зелёный.
# Фикс: коэрция оставлена (обратная совместимость), но печатает себя строкой
# `[ФОРМА-КОЭРЦИЯ]`. Тест держит обе стороны: строка есть на подмене и её НЕТ на
# легальной паре (иначе завтра её начнут печатать всегда, и она перестанет значить).
# ---------------------------------------------------------------------------

def test_lint_pair_coercion_loud():
    """Д71-линт: подменённый класс печатается строкой [ФОРМА-КОЭРЦИЯ]."""
    p = _tmp_post(EVENT_POST_OK)
    try:
        _, bad_out = run_lint_file(p, ["--channel", "osn", "--form-goal", "sales",
                                       "--form-class", "narrative"])
        _, ok_out = run_lint_file(p, ["--channel", "osn", "--form-goal", "reactions",
                                      "--form-class", "narrative"])
    finally:
        os.unlink(p)
    said = [l.strip() for l in bad_out.splitlines() if l.startswith("[ФОРМА-КОЭРЦИЯ]")]
    leaked = [l.strip() for l in ok_out.splitlines() if l.startswith("[ФОРМА-КОЭРЦИЯ]")]
    good = (len(said) == 1
            and "«narrative»" in said[0] and "«sales»" in said[0]
            and not leaked)
    record("Д71 линт: sales×narrative печатает [ФОРМА-КОЭРЦИЯ], reactions×narrative - нет",
           good,
           ("на подмене: %s; на легальной паре: %s"
            % (said or "СТРОКИ НЕТ", leaked or "чисто")))


D8_LINT_TESTS = [test_event_class_accepted_by_lint, test_event_without_datetime_fails,
                 test_event_low_density_fails, test_event_not_leaking_to_other_classes,
                 test_lint_pair_coercion_loud]


# ---------------------------------------------------------------------------
# HOOK: post-phase-gate.sh v2.0 маркеры (класс R2-11, задача D)
# ---------------------------------------------------------------------------

def _write_transcript(messages):
    """Собирает минимальный JSONL-транскрипт claude code формата для хука."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return path


POST_TEXT = (
    "📍 Тестовый заголовок фикстуры хука для проверки маркеров\n\n"
    "Абзац один с содержательным текстом длиной больше сорока символов для прохода детектора\n\n"
    "Абзац два тоже длинный и содержательный, чтобы пройти детектор структуры поста\n\n"
    "Абзац три - ещё один содержательный абзац для структуры\n\n"
    "Абзац четыре - и ещё один, чтобы точно набрать четыре содержательных абзаца\n\n"
    "форма: цель=reactions класс=narrative → длина 671, жирный 1\n\n"
    "👉 жми и переходи по ссылке https://example.com/test\n"
)


def _hook_src():
    return open(HOOK, encoding="utf-8").read() if os.path.exists(HOOK) else ""


def test_hook_no_forgeable_greps():
    """🔴 Смена архитектуры доверия (скептик-раунд 3, по решению автора).

    Три греп-маркера, которые хук требовал с этой редакции - «ИТОГ: PASS (hard-правила
    чисты)», «bench-post.py прогнан», «факт-база: объём» - ПОДДЕЛЫВАЕМЫ ПО УСТРОЙСТВУ:
    все три литерала лежат в файлах самого скилла (их печатает lint-post.py, их
    цитирует workflow/05-publish.md), и любое чтение этих файлов кладёт литерал в
    транскрипт. Гейт доказывал «файлы прочитаны», а не «проверки пройдены».

    Тест держит удаление: хук не должен ТРЕБОВАТЬ этих литералов как условие прохода.
    Проверяем строки, которыми хук копил $miss по этим маркерам."""
    src = _hook_src()
    if not src:
        record("hook: подделываемые греп-маркеры удалены", False, "файл хука не найден")
        return
    forbidden = [
        'grep -q "ИТОГ: PASS (hard-правила чисты)" <<<"$transcript_tail"',
        'grep -q "факт-база: объём" <<<"$transcript_tail"',
        'grep -q "bench-post.py" <<<"$transcript_tail"',
    ]
    still = [f for f in forbidden if f in src]
    record("hook: подделываемые греп-маркеры удалены (архитектура доверия v3)",
           not still, f"остались: {still}" if still else "")


def test_hook_executes_checks_itself():
    """Хук обязан САМ запускать проверки, а не искать их следы. Улика в исходнике:
    вызовы python3 по путям lint-post.py и bench-post.py + разбор кода возврата
    линтера + собственный BLOCK по вердикту бенча."""
    src = _hook_src()
    if not src:
        record("hook: исполняет проверки сам", False, "файл хука не найден")
        return
    needed = {
        "путь к линтеру": 'LINT_PY="$SKILL_DIR/scripts/lint-post.py"',
        "путь к бенчу": 'BENCH_PY="$SKILL_DIR/scripts/bench-post.py"',
        "запуск линтера": 'python3 "${_lint_args[@]}"',
        "запуск бенча": 'python3 "${_bench_args[@]}"',
        "разбор кода возврата линтера": '_lint_rc=$?',
        "разбор вердикта бенча": 'ВЕРДИКТ: FAIL',
        "факт-база обязательна": "факт-база не собрана" if "факт-база не собрана" in src else "--factbase",
        "порядок факт-база→черновик": "factbase_created_at",
        "верификатор со слагом": "POST-VERIFIER slug=",
        "факт спавна субагента": '"name":"Agent"',
        "журналы хук не пишет": "--log-skeleton",
    }
    missing = [k for k, v in needed.items() if v not in src]
    record("hook: исполняет lint/bench сам (архитектура доверия v3)", not missing,
           f"нет: {missing}" if missing else "")


def test_hook_no_journal_writes():
    """Хук НЕ должен передавать линтеру --log-skeleton/--log-anchor: иначе каждая
    выдача мусорит в журналы, и следующий пост ловит дубли о собственный хук.
    Проверяем, что в массиве аргументов линтера этих флагов нет."""
    src = _hook_src()
    if not src:
        record("hook: журналы не пишет", False, "файл хука не найден")
        return
    bad = [ln.strip() for ln in src.splitlines()
           if "_lint_args+=" in ln and ("--log-skeleton" in ln or "--log-anchor" in ln)]
    record("hook: не передаёт линтеру --log-* (журналы не мусорятся)", not bad,
           f"строки: {bad}" if bad else "")


def test_hook_syntax():
    """bash -n на хуке: синтаксическая целостность после правок."""
    if not os.path.exists(HOOK):
        record("hook: bash -n", False, "файл хука не найден")
        return
    p = subprocess.run(["bash", "-n", HOOK], capture_output=True, text=True)
    record("hook: bash -n (синтаксис)", p.returncode == 0, p.stderr[-300:])


def _run_hook_isolated(klass, post_body):
    """Д8. Живой прогон Stop-хука в ИЗОЛИРОВАННОМ HOME.

    Зачем изоляция: хук ищет свежий `.post-state*.json` в $HOME (maxdepth 1) и
    берёт свежайший. Прогон из тестов в настоящем $HOME (а) увидел бы боевые
    расписки владельца, (б) на секунду сделал бы СВОЙ state свежайшим для любой
    параллельной выдачи. Поэтому HOME подменяется на временный каталог, где
    лежит только симлинк `.claude` на настоящий (хук берёт оттуда SKILL_DIR).

    Возвращает (returncode, stderr) либо None, если прогон невозможен
    (нет хука / нет jq)."""
    if not os.path.exists(HOOK) or shutil.which("jq") is None:
        return None
    tmp = tempfile.mkdtemp(prefix="d8-hook-")
    try:
        home = os.path.join(tmp, "home")
        os.makedirs(home)
        os.symlink(os.path.expanduser("~/.claude"), os.path.join(home, ".claude"))
        now = datetime.datetime.now()
        fb = os.path.join(tmp, "factbase.md")
        with open(fb, "w", encoding="utf-8") as f:
            f.write("19:00 концентрат, 2 подписки MAX, Claude Code\n")
        old = (now - datetime.timedelta(hours=3)).timestamp()
        os.utime(fb, (old, old))
        state = {
            "slug": "d8test", "file_slug": "d8test", "channel": "osn",
            "form_mode": {"goal": "sales", "class": klass},
            "factbase_path": fb,
            "factbase_created_at": (now - datetime.timedelta(hours=2)).isoformat(timespec="seconds"),
            "draft_at": (now - datetime.timedelta(hours=1)).isoformat(timespec="seconds"),
        }
        with open(os.path.join(home, ".post-state-d8test.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        msg = ("## Финальный пост (копируй и вставляй как есть)\n\n```\n"
               + post_body + "```\n\n"
               f"форма: цель=sales класс={klass} слаг=d8test тема=концентрат -> длина 500-2000\n")
        tr = os.path.join(tmp, "transcript.jsonl")
        with open(tr, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "assistant",
                                "message": {"content": [{"type": "text", "text": msg}]}},
                               ensure_ascii=False) + "\n")
        p = subprocess.run(["bash", HOOK], input=json.dumps({"transcript_path": tr}),
                           capture_output=True, text=True, env=dict(os.environ, HOME=home))
        return p.returncode, p.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_hook_event_class_reaches_lint():
    """Д8-6. БЫЛО: `case "${P_CLASS:-}" in narrative|razbor|sales|gate)` без
    ветки `*)` - легальный по workflow класс `event` молча выпадал из argv, и
    событийный пост мерился порогами ЦЕЛИ. СТАЛО: класс доезжает до линтера, и
    доказывает это СОБСТВЕННЫЙ гейт класса в выводе хука (событийный пост без
    даты и времени валится строкой, которой при классе sales не существует)."""
    res = _run_hook_isolated("event", EVENT_POST_NO_DATETIME)
    if res is None:
        skip("Д8 хук: класс event доезжает до линтера", "нет хука или jq в PATH")
        return
    rc, err = res
    record("Д8 хук: класс event доезжает до линтера (виден гейт класса)",
           rc == 2 and "событие без даты и времени" in err,
           f"rc={rc}; stderr={err.strip()[:400]}")


def test_hook_unknown_class_blocks():
    """Д8-7. Неизвестный класс = ГРОМКАЯ ошибка, а не тишина. Раньше любое
    значение вне четвёрки просто исчезало из команды линтера, и человек видел
    зелёный вердикт по чужим порогам."""
    res = _run_hook_isolated("neizvestny", EVENT_POST_OK)
    if res is None:
        skip("Д8 хук: неизвестный класс -> exit 2", "нет хука или jq в PATH")
        return
    rc, err = res
    record("Д8 хук: неизвестный класс поста -> exit 2 с явным сообщением",
           rc == 2 and "неизвестный класс поста" in err,
           f"rc={rc}; stderr={err.strip()[:400]}")


def test_hook_case_knows_event():
    """Д8-8. Улика в исходнике: обе сборки argv (линтер и бенч) знают event, и
    у обоих `case` есть закрывающая ветка неизвестного значения."""
    src = _hook_src()
    if not src:
        record("Д8 хук: case знает event", False, "файл хука не найден")
        return
    need = [
        'case "${P_CLASS:-}" in narrative|razbor|sales|gate|event) _lint_args+=',
        'case "${P_CLASS:-}" in narrative|razbor|sales|gate|event) _bench_args+=',
        '""|narrative|razbor|sales|gate|event) ;;',
        "неизвестный класс поста",
    ]
    missing = [n for n in need if n not in src]
    record("Д8 хук: обе сборки argv знают event + есть ветка неизвестного класса",
           not missing, f"нет: {missing}" if missing else "")


# ---------------------------------------------------------------------------
# 🔴 Д100 (скептик-раунд 34, по решению автора): ПОРОГ ДЛИНЫ 400 НА ЯКОРНОМ МАРКЕРЕ
# ГЛУШИЛ РОВНО ТОТ БРАК, РАДИ КОТОРОГО ПРАВИЛО ПИСАЛОСЬ.
#
# ДЕФЕКТ: ВСЕ ТРИ пути python-классификатора (`is_post`) к вердикту "POST" несли
# один и тот же пол длины >=400 - якорный маркер №0 (заголовок "## Финальный
# пост (копируй...)" + ```-фенс в пределах ANCHOR_MAX_LINES строк), строка формы
# №0b («форма: цель=...» + ```-фенс) и легаси-эвристика `looks_like_post`. Канон
# постов держит нижний пол готового поста 500 знаков (`_format-canon-v2.md`
# 4.1.6, класс брака «огрызок») - но хук ловит этот брак не сам, а лишь ЗАВОДЯ
# сообщение под `lint-post.py` (правило 4.1.6 живёт ТАМ). При выдаче ПО ПОЛНОМУ
# КОНТРАКТУ (якорь + фенс + строка формы), но с телом короче 400 знаков - все
# три пути дают NOTPOST, `is_post` != "POST" → хук уходит `exit 0` МИМО ВСЕХ
# гейтов (`[ "$is_post" = "POST" ] || exit 0`), линтер вообще не запускается,
# огрызок доезжает до автора непроверенным. Экстрактор контракта (блок «ЯКОРНАЯ
# ЭКСТРАКЦИЯ» ниже по хуку) берёт ТОТ ЖЕ якорь и извлекает пост БЕЗ ЕДИНОГО
# условия на длину - порог 400 у классификатора был скопирован с эвристики
# `looks_like_post`, которой такая страховка нужна, на детерминированный маркер,
# которому она не нужна вовсе (заголовок печатает только сам скилл).
#
# ФИКС: у якорного маркера №0 условие ослаблено с `>= 400` до `>= 1` (непустой
# фенс). Строка формы №0b и легаси `looks_like_post` НЕ ТРОНУТЫ - это эвристики
# без детерминированного заголовка, страховка длины у них остаётся.
#
# Тест вырезает ЖИВОЙ python-heredoc классификатора из post-phase-gate.sh и
# гоняет его на произвольном тексте сообщения - копии кода тут нет намеренно
# (тот же закон, что у _hook_pair_block/_hook_donordev_ns: копия рассинхронится
# с хуком в первый же раунд правок и будет зеленеть на коде, которого там уже
# нет).
# ---------------------------------------------------------------------------

def _hook_classifier_src():
    """Вырезает ЖИВОЙ python-heredoc классификатора (переменная `is_post`) из
    post-phase-gate.sh. Возвращает (текст python-скрипта, причина): причина
    непустая = FAIL/skip, текст пуст в этом случае."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать классификатор "
                      "не из чего" % HOOK)
    lines = src.splitlines(True)
    START = "is_post=$(LAST=\"$last_asst\" python3 - <<'PY' 2>/dev/null\n"
    try:
        start = next(i for i, l in enumerate(lines) if l == START)
    except StopIteration:
        return None, ("якорь начала классификатора (`is_post=$(LAST=...`) не "
                      "найден в %s - хук изменился, извлечение невозможно" % HOOK)
    try:
        end = next(i for i in range(start + 1, len(lines)) if lines[i] == "PY\n")
    except StopIteration:
        return None, "закрывающий 'PY' классификатора не найден"
    return "".join(lines[start + 1:end]), ""


def _hook_classify(text):
    """Гоняет ЖИВОЙ python-блок классификатора на произвольном тексте
    сообщения. Возвращает (verdict, err): verdict = 'POST'/'NOTPOST'/None."""
    body, err = _hook_classifier_src()
    if body is None:
        return None, err
    fd, path = tempfile.mkstemp(suffix=".py", prefix="d100-cls-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                           env=dict(os.environ, LAST=text))
        return p.stdout.strip(), (p.stderr.strip() if p.returncode != 0 else "")
    finally:
        os.unlink(path)


def _r34_anchor_msg(fence_len, with_form_line=False):
    """Минимальное сообщение-кандидат: РОВНО якорь + фенс на `fence_len` знаков
    (+ опционально строка формы). Первая строка сообщения - сам заголовок
    якоря (начинается с `##`), поэтому легаси-fallback `looks_like_post` на
    ВСЁМ тексте сообщения не даёт побочного POST (`head_ok` рубится о служебный
    префикс `##`) - положительный вердикт может дать ТОЛЬКО маркер №0 (якорь)
    или №0b (строка формы), больше никакой путь классификатора не участвует."""
    body = "A" * fence_len
    msg = "## Финальный пост (копируй и вставляй как есть)\n\n```\n" + body + "\n```\n"
    if with_form_line:
        msg += ("\nформа: цель=reactions класс=narrative слаг=r34test тема=тест "
                "-> длина %d\n" % fence_len)
    return msg


_R34_D13_PROSE_MSG = (
    "Статус: Финальный пост ещё не готов, сначала деплой.\n\n"
    "```\n" + ("лог " * 150) + "\n```\n"
)


def test_hook_classifier_anchor_399_with_form_line():
    """Д100-1. Полный контракт (якорь + фенс + строка формы), тело фенса 399
    знаков - ниже прежнего порога 400 у ВСЕХ трёх путей. Живой (непропатченный)
    хук на этом входе даёт NOTPOST - ложный PASS: линтер не запускается, огрызок
    короче канонического пола 500 знаков уезжает непроверенным. После фикса Д100
    (порог у якоря снят) - POST."""
    v, err = _hook_classify(_r34_anchor_msg(399, with_form_line=True))
    if v is None:
        skip("Д100-1 классификатор: якорь+фенс 399 зн + строка формы -> POST", err)
        return
    record("Д100-1 классификатор: якорь+фенс 399 зн (+строка формы) -> POST "
           "(огрызок обязан дойти до lint-post.py, правило 4.1.6)",
           v == "POST", "получили %r (живой хук до фикса Д100 даёт NOTPOST - "
                        "это и есть репро дефекта)" % v)


def test_hook_classifier_anchor_50_no_form_line():
    """Д100-2. Якорь + фенс в 50 знаков, БЕЗ строки формы (маркер №0b тоже не
    сработает - его порог 400 не тронут). Единственный путь к POST - якорный
    маркер №0 с его новым условием `>= 1`."""
    v, err = _hook_classify(_r34_anchor_msg(50))
    if v is None:
        skip("Д100-2 классификатор: якорь+фенс 50 зн -> POST", err)
        return
    record("Д100-2 классификатор: якорь+фенс 50 зн, без строки формы -> POST "
           "(детерминированный якорь = выдача, порога длины у него больше нет)",
           v == "POST", "получили %r" % v)


def test_hook_classifier_anchor_401_control():
    """Д100-3 (контроль-регресс). 401 знак уже проходил порог 400 ДО фикса -
    вердикт обязан остаться POST и после снятия условия (диапазон только
    расширился вниз, не сузился)."""
    v, err = _hook_classify(_r34_anchor_msg(401))
    if v is None:
        skip("Д100-3 контроль: якорь+фенс 401 зн -> POST (не задето фиксом)", err)
        return
    record("Д100-3 контроль-регресс: якорь+фенс 401 зн -> POST "
           "(было POST и до фикса Д100, остаётся POST и после)",
           v == "POST", "получили %r" % v)


def test_hook_classifier_d13_prose_still_notpost():
    """Д100-4 (регресс Д13, скептик-раунд 2). Прежний репро Д13 - технический
    отчёт «Финальный пост ещё не готов…» + произвольный лог-фенс на 400+ знаков.
    Снятие порога длины у маркера №0 НЕ должно вернуть этот ложный BLOCK: якорный
    регексп сам по себе не матчит голую прозу (нет ни `#{1,6}`, ни хвоста
    «(копируй»), длина фенса тут вообще ни при чём - маркер №0 не сработает
    независимо от условия на длину."""
    v, err = _hook_classify(_R34_D13_PROSE_MSG)
    if v is None:
        skip("Д100-4 регресс Д13: проза + лог-фенс -> NOTPOST", err)
        return
    record("Д100-4 регресс Д13: проза «Финальный пост ещё не готов» + лог-фенс "
           "-> NOTPOST (якорный регексп не задет снятием порога длины)",
           v == "NOTPOST", "получили %r" % v)


D100_CLASSIFIER_TESTS = (
    test_hook_classifier_anchor_399_with_form_line,
    test_hook_classifier_anchor_50_no_form_line,
    test_hook_classifier_anchor_401_control,
    test_hook_classifier_d13_prose_still_notpost,
)


# ---------------------------------------------------------------------------
# 🔴 Д101 (скептик-раунд 35, по решению автора): ЭКСТРАКТОР БРАЛ ПЕРВЫЙ ЯКОРЬ RE.SEARCH -
# ВТОРОЙ ПОСТ В ТОМ ЖЕ СООБЩЕНИИ УЕЗЖАЛ МИМО ВСЕХ ГЕЙТОВ.
#
# ДЕФЕКТ: сообщение с ДВУМЯ якорями/постами (серийная выдача пачки, `05-publish.md`
# Шаг 1c-bis) - экстрактор берёт ПЕРВЫЙ якорь `re.search(...)` и извлекает только
# его фенс; второй пост, каким бы бракованным он ни был, никогда не доезжает до
# lint-post.py/bench-post.py/донор-гейта. Живое репро скептика: пост A (701 зн.,
# чист) + пост B (80 зн., три HARD-нарушения) - живой хук E2E даёт `exit 0`, ОБА
# поста уходят к автору.
#
# ФИКС: экстрактор считает ВСЕ вхождения `_ANCHOR_RE` (`re.finditer`, не
# `re.search`) ДО извлечения. Больше одного - `MULTI_ANCHOR:<N>`, гейт BLOCK
# «в сообщении N якорей контракта». Ровно один якорь - поведение не меняется.
#
# Тест вырезает ЖИВОЙ python-heredoc экстрактора (переменная `_extract`) из
# post-phase-gate.sh и гоняет его на произвольном тексте сообщения - тот же закон,
# что у `_hook_classifier_src`/`_hook_pair_block`/`_hook_donordev_ns`: копии кода
# тут нет намеренно (копия рассинхронится с хуком в первый же раунд правок).
# ---------------------------------------------------------------------------

def _hook_extractor_src():
    """Вырезает ЖИВОЙ python-heredoc экстрактора (переменная `_extract`) из
    post-phase-gate.sh. Возвращает (текст python-скрипта, причина): причина
    непустая = FAIL/skip, текст пуст в этом случае."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать экстрактор "
                      "не из чего" % HOOK)
    lines = src.splitlines(True)
    START = ('_extract=$(LAST="$last_asst" OUT="$_post_file" python3 - <<\'PY\' '
             '2>"$_gate_tmp/extract.err"\n')
    try:
        start = next(i for i, l in enumerate(lines) if l == START)
    except StopIteration:
        return None, ("якорь начала экстрактора (`_extract=$(LAST=...`) не "
                      "найден в %s - хук изменился, извлечение невозможно" % HOOK)
    try:
        end = next(i for i in range(start + 1, len(lines)) if lines[i] == "PY\n")
    except StopIteration:
        return None, "закрывающий 'PY' экстрактора не найден"
    return "".join(lines[start + 1:end]), ""


def _hook_extract(text):
    """Гоняет ЖИВОЙ python-блок экстрактора на произвольном тексте сообщения.
    Возвращает (stdout, err): stdout = 'OK:ANCHOR'/'NOANCHOR'/'MULTI_ANCHOR:<N>'/
    None (вырез не удался)."""
    body, err = _hook_extractor_src()
    if body is None:
        return None, err
    fd, path = tempfile.mkstemp(suffix=".py", prefix="d101-extract-")
    outfd, outpath = tempfile.mkstemp(suffix=".txt", prefix="d101-out-")
    os.close(outfd)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                           env=dict(os.environ, LAST=text, OUT=outpath))
        return p.stdout.strip(), (p.stderr.strip() if p.returncode != 0 else "")
    finally:
        os.unlink(path)
        if os.path.exists(outpath):
            os.unlink(outpath)


def _r101_two_anchor_msg():
    """Живое репро Д101: ДВА поста под ДВУМЯ якорями в одном сообщении - пост A
    (701 зн., условно чистый) и пост B (80 зн., условные HARD-нарушения)."""
    post_a = "A" * 701
    post_b = "B" * 80
    return ("## Финальный пост (копируй и вставляй как есть)\n\n```\n" + post_a +
            "\n```\n\nформа: цель=reactions класс=narrative слаг=r101test тема=тест "
            "-> длина 500-2000\n\n"
            "## Финальный пост (копируй и вставляй как есть)\n\n```\n" + post_b +
            "\n```\n\nформа: цель=reactions класс=narrative слаг=r101test тема=тест "
            "-> длина 500-2000\n")


def test_hook_extractor_multi_anchor_blocks():
    """Д101-1. Живое репро скептика: сообщение несёт ДВА якоря/поста. Экстрактор
    ДО патча молча извлекает ПЕРВЫЙ (`OK:ANCHOR`, 702 байта поста A) - про пост B
    он не знает вообще, это и есть ложный PASS (полный E2E прогон живого хука на
    этом входе даёт `exit 0`, доказано `run-tests.py` независимо от этого теста).
    После патча Д101 - `MULTI_ANCHOR:2`, извлечение отказано, гейт BLOCK."""
    v, err = _hook_extract(_r101_two_anchor_msg())
    if v is None:
        skip("Д101-1 экстрактор: два якоря -> MULTI_ANCHOR:2 (BLOCK)", err)
        return
    record("Д101-1 экстрактор: два якоря в сообщении -> MULTI_ANCHOR:2 "
           "(до патча живой хук молча извлекает ТОЛЬКО первый пост, OK:ANCHOR)",
           v == "MULTI_ANCHOR:2",
           "получили %r (живой хук до патча Д101 даёт OK:ANCHOR - это и есть "
           "репро дефекта: второй пост уезжает мимо всех гейтов)" % v)


def test_hook_extractor_single_anchor_regression():
    """Д101-2 (регресс). Ровно один якорь - поведение экстрактора НЕ меняется:
    `OK:ANCHOR`, как и до фикса Д101."""
    msg = ("## Финальный пост (копируй и вставляй как есть)\n\n```\n" + "A" * 701 +
           "\n```\n\nформа: цель=reactions класс=narrative слаг=r101test тема=тест "
           "-> длина 500-2000\n")
    v, err = _hook_extract(msg)
    if v is None:
        skip("Д101-2 регресс: один якорь -> OK:ANCHOR (не задет фиксом)", err)
        return
    record("Д101-2 регресс: ровно один якорь в сообщении -> OK:ANCHOR "
           "(одиночная выдача фиксом Д101 не задета)",
           v == "OK:ANCHOR", "получили %r" % v)


def test_hook_extractor_no_anchor_regression():
    """Д101-3 (регресс). Якоря нет вовсе - `NOANCHOR`, как и раньше (контракт
    05-publish, скептик-раунд 16 - fallback снесён полностью)."""
    msg = "Обычный технический отчёт без единого якоря контракта.\n"
    v, err = _hook_extract(msg)
    if v is None:
        skip("Д101-3 регресс: якоря нет -> NOANCHOR (не задет фиксом)", err)
        return
    record("Д101-3 регресс: якоря нет вовсе -> NOANCHOR (не задет фиксом Д101)",
           v == "NOANCHOR", "получили %r" % v)


D101_EXTRACTOR_TESTS = (
    test_hook_extractor_multi_anchor_blocks,
    test_hook_extractor_single_anchor_regression,
    test_hook_extractor_no_anchor_regression,
)


# ---------------------------------------------------------------------------
# 🔴 Д71 (скептик-раунд 22, по решению автора): ПАРА цель×класс НЕ ГЕЙТИЛАСЬ В ХУКЕ.
# Цель проверялась словарём и сверялась со state (блок «ж»), класс - словарём (Д8) и
# сверялся со state (блок «ж2»). Обе величины по отдельности честные, а меряет пост
# ПАРА: линтер при цели != reactions класс отбрасывает, при reactions коэрцит в
# narrative. Значит sales×narrative / reactions×sales / forwards×razbor проходили все
# четыре проверки МОЛЧА и уезжали на чужие пороги. Блок «ж3» закрывает это стопом.
# Тест вырезает ЖИВОЙ блок «ж3» из хука и гоняет его - копии кода тут нет намеренно
# (копия рассинхронится с хуком в первый же раунд правок и будет зеленеть на коде,
# которого там уже нет; тот же закон, что у _hook_donordev_ns и _hook_verifier_block).
# ---------------------------------------------------------------------------

def _hook_pair_block():
    """Вырезает ЖИВОЙ блок «ж3» (гейт пары цель×класс) из post-phase-gate.sh.

    Возвращает `(путь к .sh, причина)`: `NOHOOK` = skip (машина ученика без хука),
    любая другая причина = FAIL с честным текстом. Границы выреза - от строки-якоря
    `# --- (ж3) Д71` до начала следующего блока `# --- (д) факт-база`. Вырезанный
    кусок оборачивается в скрипт, который берёт цель и класс аргументами и печатает
    `PASS_THROUGH`, если блок не остановил прогон."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать блок гейта пары "
                      "не из чего" % HOOK)
    lines = src.splitlines(True)
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("# --- (ж3) Д71"))
    except StopIteration:
        return None, ("блок «ж3» не найден в хуке - патч R22 (Д71) ещё НЕ применён "
                      "к %s, либо якорь `# --- (ж3) Д71` переименован. Пара "
                      "цель×класс сейчас не гейтится ничем" % HOOK)
    try:
        end = next(i for i in range(start + 1, len(lines))
                   if lines[i].startswith("# --- (д) факт-база"))
    except StopIteration:
        return None, ("границу блока «ж3» не найти - якорь следующего блока "
                      "`# --- (д) факт-база` сдвинут или переименован")
    body = "".join(lines[start:end])
    script = ('set -uo pipefail\nP_GOAL="$1"; P_CLASS="$2"\n'
              + body + '\necho PASS_THROUGH\n')
    fd, path = tempfile.mkstemp(suffix=".sh", prefix="d71-pair-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(script)
    return path, ""


# кейс: (имя, цель, класс, ждём код возврата)
D71_PAIR_CASES = [
    ("нелегальная пара sales×narrative -> BLOCK", "sales", "narrative", 2),
    ("легальная пара reactions×narrative -> проход", "reactions", "narrative", 0),
    ("класс event перекрывает цель: sales×event -> проход", "sales", "event", 0),
    ("пустой класс при цели forwards -> проход", "forwards", "", 0),
    # 🔴 Д85 (скептик-раунд 28, по решению автора): БЫЛО - `if [-n "${P_CLASS:-}"]`
    # пропускал пустой класс насквозь при ЛЮБОЙ цели, хотя канон (01-router.md:251)
    # разрешает пустое значение РОВНО у forwards. reactions/sales без объявленного
    # класса проходили блок «ж3» молча - пара «не заявлена», а не «класс не объявлен
    # при цели, где класс обязателен». Два кейса ниже репродуцируют дыру на ЖИВОМ
    # (непропатченном) хуке: до патча R28 оба дают rc=0 вместо rc=2.
    ("Д85 пустой класс при цели reactions -> BLOCK (класс обязателен)", "reactions", "", 2),
    ("Д85 пустой класс при цели sales -> BLOCK (класс обязателен)", "sales", "", 2),
]


def test_hook_pair_gate():
    """Д71/Д85: хук рубит словарно-легальную, но несовместимую пару цель×класс,
    и рубит пустой класс при любой цели кроме forwards.

    Шесть кейсов покрывают все ветки канона 01-router Шаг 0.49: подмена (класс
    выброшен → чужие пороги), обычная легальная пара, перекрытие целью класса
    `event`, штатный пустой класс цели `forwards` (Д71) и брак пустого класса при
    reactions/sales, где канон класс назначает всегда (Д85, раунд 28). Текст
    блокировки проверяется буквально: для несовместимой ПАРЫ - оба слова пары; для
    ПУСТОГО класса - имя цели и отсылка к канону, иначе оператор не поймёт, что
    именно чинить."""
    blk, err = _hook_pair_block()
    if err == "NOHOOK":
        skip("Д71/Д85 хук: гейт пары цель×класс (блок «ж3»)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if blk is None:
        record("Д71/Д85 хук: гейт пары цель×класс (блок «ж3»)", False, err)
        return
    bad = []
    try:
        for name, goal, cls, want_rc in D71_PAIR_CASES:
            p = subprocess.run(["bash", blk, goal, cls], capture_output=True, text=True)
            if p.returncode != want_rc:
                bad.append("%s: ждём rc=%d, получили rc=%d (%s)"
                           % (name, want_rc, p.returncode,
                              (p.stderr.strip() or p.stdout.strip())[:120]))
                continue
            if want_rc == 2 and cls == "":
                # Д85: пустой класс при цели, где класс обязателен
                need = ["класс не объявлен при цели %s" % goal,
                        "легально", "forwards", "brief.form_class"]
                miss = [n for n in need if n not in p.stderr]
                if miss:
                    bad.append("%s: в тексте блокировки нет %s" % (name, miss))
            elif want_rc == 2:
                need = ["пара цель=%s класс=%s нелегальна" % (goal, cls),
                        "подменён на", "эталонами чужого класса", "brief.form_class"]
                miss = [n for n in need if n not in p.stderr]
                if miss:
                    bad.append("%s: в тексте блокировки нет %s" % (name, miss))
            elif "PASS_THROUGH" not in p.stdout:
                bad.append("%s: блок не пропустил дальше (stdout=%r)"
                           % (name, p.stdout.strip()[:120]))
    finally:
        os.unlink(blk)
    record("Д71/Д85 хук: гейт пары цель×класс - живой блок «ж3» (%d кейсов)"
           % len(D71_PAIR_CASES), not bad, "; ".join(bad))


def _hook_donordev_ns():
    """Вырезает ЖИВОЙ кусок гейта `donor-devices` из post-phase-gate.sh и ИСПОЛНЯЕТ его.

    Возвращает пару `(namespace, причина)` по тому же контракту, что и
    `_hook_donordev_state` ниже (см. её докстринг - там записано, почему вырезаем,
    а не копируем, и почему сломанный вырез = FAIL, а не SKIP). Отдельная функция
    нужна, потому что из этого же куска берётся не только `_donordev_state`, но и
    регекс `_DONORDEV_REF_RE` - его гоняет страж диапазона §-подписей (Д51, раунд 12).

    🔴 Почему вырезаем, а не копируем (дефект Д45, скептик-раунд 10). У гейта
    `donor-devices` тестов не было ВООБЩЕ (grep donordev по этому файлу давал ноль),
    и поэтому дефекты одного класса жили раундами подряд: Д28 → Д29 → Д34 → Д35 →
    Д36 → Д43, каждый раз находил человек, а не прогон. Копия функции в тесте эту
    дыру не закрывает - она рассинхронится с хуком в первый же раунд правок и будет
    зеленеть на коде, которого в хуке уже нет. Поэтому исходник читается с диска,
    кусок от `_DONORDEV_RE` до конца функции компилируется и исполняется как есть.

    🔴 Дефект Д47 (скептик-раунд 11, по решению автора): НЕУДАЧНЫЙ ВЫРЕЗ УХОДИЛ В SKIP.
    Функция возвращала голый None на ВСЕ случаи сразу - и «хука нет на диске», и
    «якорь `_DONORDEV_RE` сдвинулся», и «кусок не скомпилировался». Тест по этому None
    вызывал `skip()` с причиной «нет хука или функция не вырезалась», то есть сломанный
    вырез не считался ни плюсом, ни минусом: раннер давал exit 0, а печатал ЛОЖНУЮ
    причину («отсутствует приватный корпус владельца» - формулировка самого `skip`),
    хотя корпус тут ни при чём. Класс дефекта тот же, что у Д45: страж гейта обезоружен,
    и это видно только человеку. Соседний `test_hook_no_forgeable_greps` при отсутствии
    исходника пишет честный `record(False)` - разнобой снят в пользу FAIL.

    Возвращает пару `(namespace, причина)`:
      (ns, "")           вырез удался;
      (None, "NOHOOK")   хука нет на диске - ЕДИНСТВЕННЫЙ случай под skip (машина
                         ученика без установленного хука);
      (None, <текст>)    вырез/exec не удались = FAIL с честной причиной."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать функцию "
                      "_donordev_state не из чего" % HOOK)
    lines = src.splitlines(True)
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("_DONORDEV_RE = re.compile("))
    except StopIteration:
        return None, ("функция не вырезалась из хука - якорь `_DONORDEV_RE = re.compile(` "
                      "сдвинут или переименован? тест-страж гейта обезоружен")
    end, seen_def = None, False
    for i in range(start, len(lines)):
        if lines[i].startswith("def _donordev_state("):
            seen_def = True
            continue
        if seen_def and lines[i][:1] not in ("", " ", "\t", "\n", "#"):
            end = i
            break
    if not seen_def:
        return None, ("функция не вырезалась из хука - якорь `def _donordev_state(` "
                      "не найден после `_DONORDEV_RE`; тест-страж гейта обезоружен")
    ns = {"re": re}
    try:
        exec(compile("".join(lines[start:end or len(lines)]), HOOK, "exec"), ns)
    except Exception as e:
        return None, ("вырезанный кусок хука не исполняется (%s: %s) - границы выреза "
                      "сдвинуты или код функции битый; тест-страж гейта обезоружен"
                      % (type(e).__name__, e))
    return ns, ""


def _hook_donordev_state():
    """ЖИВАЯ функция `_donordev_state` из хука (обёртка над `_hook_donordev_ns`).

    Контракт пары `(функция, причина)` тот же: `NOHOOK` = skip, любая другая
    причина = FAIL, пустая строка = вырез удался."""
    ns, err = _hook_donordev_ns()
    if ns is None:
        return None, err
    fn = ns.get("_donordev_state")
    if fn is None:
        return None, ("кусок исполнился, но имени _donordev_state в нём нет - функцию "
                      "переименовали? тест-страж гейта обезоружен")
    return fn, ""


# (что проверяем, значение строки donor-devices, ожидаемое состояние)
DONORDEV_CASES = [
    # --- штатное использование: гейт обязан ПРОПУСКАТЬ ---
    ("штатный §N.M", "§2.3 смена системы отсчёта «цитата» -> PASS", "OK"),
    ("голый номер приёма N.M (Д35)", "2.3 смена системы отсчёта «цитата» -> PASS", "OK"),
    ("нумерованный список перед строкой (Д30)",
     "§4.3 вопрос-финал «согласны?» -> PASS", "OK"),
    ("перестановка стрелки (Д36)", "-> PASS, §2.1 обещание-в-хуке «цитата»", "OK"),
    ("цитата с «<1%» - не литерал (Д34)",
     "§1.3 тезис «конверсия <1%, а мы подняли» -> PASS", "OK"),
    # --- обратная сторона слово-границы Д43: «нет» ≠ «нетривиальный» ---
    ("слово-граница: «нетривиальный приём §2.3» НЕ отказ",
     "нетривиальный приём §2.3 «цитата из поста» -> PASS", "OK"),
    ("слово-граница внутри значения",
     "§1.1 кадр, нетривиальный случай «цитата» -> PASS", "OK"),
    # --- отказ словарём (Д28/Д29) ---
    ("отказ «нет»", "нет", "NO"),
    ("отказ N/A", "N/A", "NO"),
    ("пустое значение", "", "NO"),
    # --- 🔴 отказ ФРАЗОЙ (Д43, раунд 10): все пять пробивали гейт как OK ---
    ("Д43 отказ фразой + диапазон §",
     "нет подходящего приёма §1-§5 -> PASS", "NO"),
    ("Д43 «ни один … не опознан» + §",
     "ни один приём справочника не опознан, ближайший §2.3 -> PASS", "NO"),
    ("Д43 «не применимо к классу» + §",
     "не применимо к этому классу, ср. §4.2 -> PASS", "NO"),
    ("Д43 «отсутствует, см. §1.1»", "отсутствует, см. §1.1 -> PASS", "NO"),
    ("Д43 «приём не применялся» (фраза не в начале)",
     "приём не применялся, справочник §3.1 прочитан -> PASS", "NO"),
    # --- 🔴 Д49 (раунд 11): §-ссылка ограничена разделами справочника 1-5 ---
    # Подписи приёмов в references/donor-copy-devices.md живут только в §1.1-§5.4:
    # §6 - наблюдения третьего донора, §7 - сигнатуры «не переносить», §8 - анти-приёмы,
    # §9 не существует. Ветка голого номера этот диапазон держала с Д38, §-ветка - нет.
    ("Д49 §8.2 - раздел анти-приёмов, подписи приёма там нет",
     "§8.2 раздел вне подписей «цитата из поста» -> PASS", "NOREF"),
    ("Д49 §9.1 - раздела 9 в справочнике нет вовсе",
     "§9.1 «цитата из поста» -> PASS", "NOREF"),
    ("Д49 §7 - сигнатуры донора, приёмом не являются",
     "§7 сигнатура донора «цитата из поста» -> PASS", "NOREF"),
    # 🔴 ФИКС Д102 (скептик-раунд 35, по решению автора): ПЕРЕВЁРНУТО. Кейс ниже раньше ждал
    # `OK` («§5 без подномера - законная ссылка») - это и был сам дефект: подписи
    # приёмов справочника `references/donor-copy-devices.md` живут ТОЛЬКО в форме
    # `§N.M` (§1.1…§5.4), голый номер раздела `§N` приёмом не является, а канон
    # верификации (`workflow/04-review.md:955`) прямо требует «ссылка на раздел без
    # подписи приёма = FAIL». §-ветка `_DONORDEV_REF_RE` сужена до `§\s*[1-5]\.\d`
    # (требует подномер) - голая `§N` больше не ссылка на приём.
    ("Д102 фикс: §5 без подномера - ссылка на РАЗДЕЛ, не приём (не §N.M) - NOREF",
     "§5 CTA и передача «цитата из поста» -> PASS", "NOREF"),
    ("Д102 фикс: §2 без подномера - тоже раздел, не приём - NOREF",
     "§2 удержание «цитата из поста» -> PASS", "NOREF"),
    # «§2.3 -> OK» (подпись приёма, легальна) уже покрыт кейсом «штатный §N.M» выше -
    # дублировать не требовалось.
    # --- 🔴 Д132а (скептик-раунд 44, по решению автора): PIPE-ТАБЛИЧНАЯ ФОРМА БЕЗ
    # ДВОЕТОЧИЯ ДАВАЛА ЛОЖНЫЙ ДИАГНОЗ «СТРОКИ НЕТ» - `_DONORDEV_RE` требует
    # ЛИТЕРАЛЬНОЕ двоеточие сразу за ключом, табличная форма реестра («|
    # donor-devices | §2.3 … |») двоеточия не несёт, `finditer` не находил
    # НИ ОДНОГО матча, честная живая строка читалась `MISSING`. Фикс -
    # зеркало `_DONORDEV_TABLE_RE` (тот же приём, что `_READFLAG_TABLE_RE`
    # у Д126). `val` здесь несёт ГОТОВУЮ pipe-строку ЦЕЛИКОМ (начинается с
    # `|`) - `test_hook_donordev_gate` распознаёт этот маркер и подставляет
    # её КАК ЕСТЬ, а не через колон-шаблон `donor-devices: %s` (см. правку
    # цикла подстановки в самом тесте ниже).
    ("Д132а табличная форма без двоеточия, честная ссылка на приём",
     "| donor-devices | §2.3 смена системы отсчёта «цитата» -> PASS |", "OK"),
    ("Д132а табличная форма без двоеточия, отказ «нет»",
     "| donor-devices | нет |", "NO"),
    # --- 🔴 Д103 (скептик-раунд 36, по решению автора): РЕГЕКС ФОРМАТА ≠ РЕАЛЬНАЯ ПОДПИСЬ ---
    # Д102 сузил §-ветку до `§N.M` (требует подномер), но диапазон `\.\d` берёт ЛЮБУЮ
    # цифру после точки - формат «§3.9» технически валиден, а такого приёма в
    # справочнике НЕТ (подписи РОВНО §1.1-1.4/2.1-2.7/3.1-3.4/4.1-4.4/5.1-5.4, 23 штуки).
    # Канон `workflow/04-review.md:955` прямо называет «§3.9» примером брака. Фикс
    # добавляет сверку числа с ЖИВЫМ файлом справочника ПОСЛЕ регекса - см.
    # `_donordev_load_signatures` в хуке.
    ("Д103 §3.9 - формат верный, такого приёма в справочнике нет",
     "§3.9 воображаемый приём «цитата из поста» -> PASS", "NOREF"),
    ("Д103 §2.8 - раздел 2 доходит только до §2.7",
     "§2.8 воображаемый приём «цитата из поста» -> PASS", "NOREF"),
    ("Д103 §2.0 - подномер 0 не существует ни в одном разделе",
     "§2.0 воображаемый приём «цитата из поста» -> PASS", "NOREF"),
    ("Д103 голый 3.9 (без §) - тот же выдуманный подномер",
     "3.9 воображаемый приём «цитата из поста» -> PASS", "NOREF"),
    ("Д103 регресс: §2.3 - РЕАЛЬНАЯ подпись, фикс её не задевает",
     "§2.3 смена системы отсчёта «цитата из поста» -> PASS", "OK"),
    ("Д103 регресс: голый 2.3 - РЕАЛЬНАЯ подпись без §, тоже не задета",
     "2.3 смена системы отсчёта «цитата из поста» -> PASS", "OK"),
    # --- 🔴 Д65 (раунд 20): ЧИСЛО ИЗ ЦИТАТЫ - НЕ ССЫЛКА НА ПРИЁМ ---
    # Ветка голого номера `[1-5].\d{1,2}` ловила бытовое число ИЗ ЦИТАТЫ поста, а
    # цитата в строке `donor-devices:` по формату 04-review 4.M.2 ОБЯЗАТЕЛЬНА - то
    # есть канал был штатный, не редкий край. Сужение диапазона до 1-5 (Д38) закрыло
    # только числа РАЗДЕЛОВ; 1.0-5.99 - самый ходовой диапазон бытовых чисел (часы,
    # месяцы, разы), 15 постов корпуса из 608 их несут. Фикс: ref ищется в куске
    # значения ДО первой открывающей «ёлочки» (ссылка по формату стоит ПЕРЕД цитатой).
    ("Д65 бытовое число в цитате, ссылки нет вообще",
     "кадр против витрины «за 1.5 часа собрал первый экран» -> PASS", "NOREF"),
    ("Д65 обратная сторона: то же число, но ссылка §1.1 стоит ДО цитаты",
     "§1.1 кадр против витрины «за 1.5 часа собрал первый экран» -> PASS", "OK"),
    ("Д65 обратная сторона: голая ссылка 2.3 до цитаты с «155.000 за 3.5 месяца»",
     "2.3 смена системы отсчёта «155.000 за 3.5 месяца» -> PASS", "OK"),
    # --- 🔴 Д67 + Д69 (раунд 21): СКОУП = ЗНАЧЕНИЕ БЕЗ ЗАКАВЫЧЕННЫХ СПАНОВ ---
    # Скоуп-эвристика раунда 20 («кусок до первой открывающей ёлочки») держала ОДИН
    # класс кавычек и ОДИН порядок слов, и ломалась с двух сторон: (Д67) число в
    # кавычках другого класса гейт по-прежнему открывало - ёлочек в строке нет, скоуп
    # оставался полным значением; (Д69) закавыченное НАЗВАНИЕ приёма резало скоуп до
    # первого слова и рубило законный отчёт. Механизм заменён: из значения вырезаются
    # ВСЕ сбалансированные закавыченные спаны, ref ищется по остатку. Побочный эффект -
    # снят размен раунда 20 «ссылка ПОСЛЕ цитаты = ложный BLOCK» (кейс ниже).
    ("Д67 число в ПРЯМЫХ кавычках, ссылки нет",
     'кадр против витрины "за 1.5 часа собрал" -> PASS', "NOREF"),
    ("Д67 число в ЛАПКАХ „…“, ссылки нет",
     "кадр против витрины „за 1.5 часа собрал“ -> PASS", "NOREF"),
    ("Д67 число в АНГЛИЙСКИХ парных “…”, ссылки нет",
     "кадр против витрины “за 1.5 часа собрал” -> PASS", "NOREF"),
    ("Д67 число в УГОЛКАХ ‹…›, ссылки нет",
     "кадр против витрины ‹за 1.5 часа собрал› -> PASS", "NOREF"),
    ("Д67 число в БЭКТИКАХ, ссылки нет",
     "кадр против витрины `за 1.5 часа собрал` -> PASS", "NOREF"),
    ("Д67 число в УДВОЕННОМ АПОСТРОФЕ, ссылки нет",
     "кадр против витрины ''за 1.5 часа собрал'' -> PASS", "NOREF"),
    ("Д69 закавыченное НАЗВАНИЕ приёма + §1.1 + цитата - законный отчёт",
     "приём «кадр против витрины» §1.1 «за 1.5 часа собрал» -> PASS", "OK"),
    ("Д69 снятие размена Р20: ссылка §2.3 стоит ПОСЛЕ цитаты",
     "смена системы отсчёта «за 1.5 часа собрал первый экран» §2.3 -> PASS", "OK"),
    ("Д67 fail-closed: непарная « - остаток режется до неё, число после не считается",
     "кадр против витрины «за 1.5 часа собрал первый экран -> PASS", "NOREF"),
    # --- прочие состояния ---
    ("литерал шаблона (Д29б)",
     "<§номер + название приёма> «<строка-улика поста>» -> PASS", "LITERAL"),
    ("без ссылки на приём (Д29в)", "приём применён, всё ок -> PASS", "NOREF"),
    # --- 🔴 Д146 (найден фиксером раунда 50 побочной находкой, по решению автора):
    # §-ССЫЛКА ПЕРЕД СЛОВОМ ОТКАЗА ДАВАЛА `OK` ВМЕСТО `NO`. `_donordev_state_
    # one` режет значение по стрелке-вердикту и сканирует PHRASE-регекс
    # отказа ТОЛЬКО на куске ДО стрелки (фолбэк на кусок ПОСЛЕ - только если
    # кусок ДО пуст, Д36); §-ссылка ДО стрелки делает кусок непустым, и отказ
    # ПОСЛЕ стрелки не сканируется НИКЕМ. Порядок «отказ ДО стрелки» и без
    # §-ссылки уже работал честно (кейсы Д43 выше) - дефект СТРОГО
    # односторонний по порядку. Живой репро - scratchpad r52/dd_mech.py.
    ("Д146 репро 1: §-ссылка ДО «не нашёл приёма» ПОСЛЕ стрелки",
     "§2.3 «цитата из поста» -> не нашёл приёма, PASS", "NO"),
    ("Д146 репро 2: §-ссылка ДО «не применялся» ПОСЛЕ стрелки",
     "§2.3 «цитата из поста» -> не применялся приём, PASS", "NO"),
    ("Д146 ё/е-вариант: §-ссылка ДО «не нашел» (без ё) ПОСЛЕ стрелки",
     "§2.3 «цитата из поста» -> не нашел приёма, PASS", "NO"),
    ("Д146 легальный контроль: §-ссылка + «применён»/«работает» БЕЗ отрицания "
     "ПОСЛЕ стрелки - НЕ отказ (нет «не» перед корнем, PHRASE-регекс якорен "
     "на \\bне\\s+)",
     "§2.3 смена системы отсчёта «цитата» -> приём применён, работает", "OK"),
    # --- 🔴 Д147 (скептик-раунд 51, по решению автора), ЗЕРКАЛО Д146 НА START-
    # РЕГЕКСЕ: START-словарь `_DONORDEV_NO_START_RE` проверял ТОЛЬКО кусок ДО
    # ПЕРВОЙ стрелки (`soft(_parts[0])`), НЕ начало КАЖДОГО arrow-сегмента.
    # PHRASE-словарь (Д146, кейсы выше) не несёт голых `нет`/`нету`/`ни один`/
    # `отсутств…`/`none`/`n/a`/`ок`/`ok` отдельными формами (только фразы «не
    # примен…»/«не опознан…»/…) - эти 8 токенов словаря `_DONORDEV_NO_START_RE`
    # БЕЗ приставки «не», написанные С НАЧАЛА сегмента ПОСЛЕ стрелки, не
    # проверялись НИ ОДНИМ из двух слоёв. Живой репро: «§2.3 удержание «улика
    # поста» -> нет» → `OK` вместо `NO`. ФИКС: START-регекс якорен к началу
    # КАЖДОГО `_parts[i]` (порождённого тем же `re.split`, что уже режет
    # `raw_full`), а не только `_parts[0]`. Якорь `^` НЕ снят (не превращён в
    # свободный скан) - без него «нет» ловило бы себя внутри цитаты поста
    # (контроль-кейс ниже это проверяет напрямую).
    ("Д147 START после стрелки: «нет»",
     "§2.3 удержание «улика поста» -> нет", "NO"),
    ("Д147 START после стрелки: «нет подходящего приёма»",
     "§2.3 удержание «улика поста» -> нет подходящего приёма", "NO"),
    ("Д147 START после стрелки: «нету»",
     "§2.3 удержание «улика поста» -> нету", "NO"),
    ("Д147 START после стрелки: «ни один»",
     "§2.3 удержание «улика поста» -> ни один приём не подошёл", "NO"),
    ("Д147 START после стрелки: «отсутствует»",
     "§2.3 удержание «улика поста» -> отсутствует", "NO"),
    ("Д147 START после стрелки: «none»",
     "§2.3 удержание «улика поста» -> none", "NO"),
    ("Д147 START после стрелки: «N/A»",
     "§2.3 удержание «улика поста» -> N/A", "NO"),
    ("Д147 START после стрелки: «ок»",
     "§2.3 удержание «улика поста» -> ок", "NO"),
    ("Д147 контроль: та же форма «нет подходящего приёма» ДО стрелки "
     "(старый Д36-путь через _parts[0], не задет фиксом - уже блокировал)",
     "нет подходящего приёма, §2.3 удержание -> PASS", "NO"),
    ("Д147 контроль: «N/A» ДО стрелки (та же старая позиция, не задета)",
     "N/A, §2.3 удержание -> PASS", "NO"),
    ("Д147 контроль честный: §-ссылка -> PASS без единого токена отказа",
     "§2.3 удержание «улика поста» -> PASS", "OK"),
    ("Д147 контроль-цитата: «нет» ВНУТРИ цитаты поста, НЕ начало сегмента - "
     "фикс НЕ превращает якорь в свободный скан, ложного BLOCK нет",
     "§2.3 контраст «нет времени на прогрев» -> PASS", "OK"),
    ("Д147 контроль: несколько стрелок, отказ-токен - начало ПОСЛЕДНЕГО "
     "сегмента",
     "§2.3 удержание «улика» -> предварительно PASS -> нет", "NO"),
    # --- 🔴 Д148 (скептик-раунд 51, по решению автора): ручной ё-свип Д143 (раунд
    # 50) прошёл по «наш» (5 мест) и по «назв\\w*\\s+при[её]ма», но пропустил
    # 8-е несущее место - `приём\\w*` в `_DONORDEV_PLACEHOLDERS` («<приём
    # справочника>» плейсхолдер шаблона 04-review 4.M.2). «<прием
    # справочника>» (без ё, частая живая орфография) не распознавался
    # литералом-шаблоном, гейт открывался НЕЗАКРЫТЫМ шаблоном. ФИКС классом:
    # `_yo_insensitive` (зеркало `lint-post.py`) - ё/е-нечувствительность у
    # ВСЕХ плейсхолдеров DD/DL сразу, не точечная расстановка.
    ("Д148 плейсхолдер с ё: «<приём справочника>» - литерал шаблона",
     "<приём справочника>", "LITERAL"),
    ("Д148 плейсхолдер БЕЗ ё (живая орфография): «<прием справочника>» - "
     "тот же литерал, не должен проходить как отчёт",
     "<прием справочника>", "LITERAL"),
    ("Д148 регресс: «<название приёма>» (уже был закрыт Д143) держится",
     "<название приёма>", "LITERAL"),
    ("Д148 регресс: «<название приема>» без ё - тот же литерал",
     "<название приема>", "LITERAL"),
    # --- 🔴 Д150+Д152 (скептик-раунд 52, по решению автора), ОБЩИЙ КОРЕНЬ: START-скан
    # резал raw_full НА СЕГМЕНТЫ ТОЛЬКО ПО СТРЕЛКЕ, ДО вырезки цитат - Д150
    # (регресс патча R54, ложный BLOCK): стрелка ВНУТРИ цитаты поста рождает
    # arrow-сегмент из СЛОВ ЦИТАТЫ, который матчит START-токен с начала - «§2.3
    # контраст «было -> нет результата» -> PASS» стала ложным NO после Р54.
    # Д152 (fail-open, асимметрия с dead-language): отказ ПОСЛЕ любого НЕ-
    # arrow разделителя (`;`/`,`/`·`/соло-дефис/`:`/`=>`/`⟶`) не порождал новый
    # сегмент и был невидим. ФИКС - общий хелпер `_donordev_start_refusal`
    # (quote-strip ПЕРЕД разрезкой + расширенный `_DONORDEV_START_SPLIT_RE`) -
    # полное обоснование класса и выбора механики («сегмент-старты», не «хвост
    # целиком», как у DL) - комментарий перед `_donordev_start_refusal` в
    # `post-phase-gate.sh`.
    ("Д150 регресс патча R54: стрелка ВНУТРИ цитаты поста (контраст "
     "«было -> нет результата») - quote-strip срезает цитату ПЕРЕД "
     "арроу-сплитом START-скана, ложного BLOCK нет",
     "§2.3 контраст «было -> нет результата» -> PASS", "OK"),
    ("Д150 стрелка внутри цитаты, другой токен отказа («нету денег»)",
     "§2.3 контраст «точка А -> нету денег» -> PASS", "OK"),
    ("Д150 стрелка внутри цитаты, токен «ок» внутри цитаты",
     "§2.3 контраст «раньше -> ок, теперь иначе» -> PASS", "OK"),
    ("Д150 стрелка внутри цитаты, unicode-стрелка → и токен «нет» внутри",
     "§2.3 приём «сначала → нет, потом да» -> PASS", "OK"),
    ("Д152 fail-open: отказ после запятой «,» (не arrow-разделитель)",
     "§2.3 удержание «улика поста», нет", "NO"),
    ("Д152 fail-open: отказ после точки с запятой «;»",
     "§2.3 удержание «улика поста»; нет", "NO"),
    ("Д152 fail-open: отказ после средней точки «·»",
     "§2.3 удержание «улика поста» · нет", "NO"),
    ("Д152 fail-open: отказ после соло-дефиса С ПРОБЕЛАМИ с обеих сторон "
     "(не спутать со стрелкой - у той дефис БЕЗ пробела перед «>»)",
     "§2.3 удержание «улика поста» - нет", "NO"),
    ("Д152 fail-open: отказ после ASCII-варианта стрелки «=>»",
     "§2.3 удержание «улика поста» => нет", "NO"),
    ("Д152 fail-open: отказ после двоеточия «:»",
     "§2.3 удержание «улика поста»: нет", "NO"),
    ("Д152 fail-open: отказ после длинной стрелки «⟶» (не путать с «→», "
     "которая уже несла легальный статус arrow-разделителя)",
     "§2.3 удержание «улика поста» ⟶ нет", "NO"),
    # --- контроли расширенного скана: генерик-разделители СНАРУЖИ цитаты не
    # рождают ложный NO на честном отчёте (проверка «ложняков на живом
    # корпусе нет», обязательная часть отчёта Р52) ---
    ("Д152 контроль: децимальная запятая СНАРУЖИ цитаты («1,5 часа») режет "
     "на куски, ни один не начинается со слова отказа - честный OK держится",
     "§2.3 удержание, потратил 1,5 часа на разбор «улика поста» -> PASS", "OK"),
    ("Д152 контроль: двоеточие сразу после §-ссылки (естественная форма прозы) "
     "не рождает ложный NO",
     "§2.3: удержание фокуса «улика поста» -> PASS", "OK"),
    ("Д152 контроль: соло-дефис с пробелами как естественный разделитель прозы "
     "(«приём - результат виден сразу») не рождает ложный NO",
     "§2.3 приём - результат виден сразу «улика поста» -> PASS", "OK"),
    # --- 🔴 Д158 (fail-open, назван фиксером раунда 53 как кандидат ВНЕ его
    # периметра, найден этой сессией, по решению автора): токен «ни один» словаря
    # `_DONORDEV_NO_START_RE` нёс ТОЛЬКО именительный падеж буквальным
    # литералом «один» - косвенные падежи МЕНЯЮТ стем целиком на «одн-»
    # («один» = о-д-и-н, «одного»/«одна»/«одной» = о-д-н-..., буквы «и» там
    # нет вовсе - это не суффиксация), литерал не матчился НИ ЧАСТИЧНО.
    # Живой репро: «-> ни одного приёма не подошло» после стрелки читалось
    # `OK` вместо `NO`. ФИКС - ВТОРАЯ альтернатива добавлена рядом со старым
    # литералом (`ни\s+один|ни\s+одн\w*`), НЕ замена: голая замена на
    # `одн\w*` регрессирует сам номинатив («одн» не подстрока «один» - 3-я
    # буква расходится, и/н) - живой репро при первой попытке, scratchpad
    # r57/mech_check.py. И4 контракта R56 не тронут - хвост НЕ-предмет
    # («ни одного призыва в тексте», матрица R56 #35) по-прежнему `OK`.
    # DL/READFLAG корень «ни один» НЕ несут ни в одной форме (подтверждено
    # грепом всех пяти словарей отказа) - расширять там нечего, это
    # единственное место, где корень уже жил.
    ("Д158 fail-open: «ни одного приёма» (генитив) после стрелки, хвост-ПРЕДМЕТ",
     "§2.3 удержание «улика поста» -> ни одного приёма не подошло", "NO"),
    ("Д158 line-start: «ни одного из приёмов не опознал» (генитив, начало значения, И2)",
     "ни одного из приёмов не опознал, §2.3 удержание -> PASS", "NO"),
    ("Д158 «ни одна» (женский род) после стрелки, хвост-ПРЕДМЕТ",
     "§2.3 удержание «улика поста» -> ни одна ссылка справочника не подошла", "NO"),
    ("Д158 контроль И4: «ни одной» хвост НЕ предмет (посторонний) - пропуск, "
     "зеркало §5.2-контроля #35 (матрица R56)",
     "§2.3 удержание «улика поста» -> PASS · ни одной оси в тексте не названо", "OK"),
    ("Д158 контроль регресс: исходная форма «ни один» (номинатив) держится "
     "(живой репро первой попытки фикса - голая замена на `одн\\w*` эту форму рвала)",
     "§2.3 удержание «улика поста» -> ни один вариант справочника не подошёл", "NO"),
    # --- 🔴 Д166 (fail-open, скептик-раунд 56, по решению автора): словари ОТКАЗА несли
    # причастие/страдательный залог («опознан\\w*»/«вложен\\w*»), но не активный
    # перфектив («опознал»/«вложил») - канон-фраза 04-review.md:1005 «не опознал
    # ни одного» дословно проходила гейт как OK. Систематический проход по ВСЕМ
    # ЧЕТЫРЁМ словарям отказа + READFLAG_EXPLICIT_BAD нашёл ДВЕ леммы с
    # корпус-уликой (грепом по скиллу): «опознал\\w*» (workflow/04-review.md:1005,
    # ДОСЛОВНАЯ инструкция верификатору) и «вложил\\w*» (run-tests.py: «справочник
    # приёмов не вложили», уже живущая тестовая формулировка). «не прочитал»/
    # «не передал» - ТОТ ЖЕ класс лемм, но грепом по скиллу 0 вхождений (bigram) -
    # правило Д160 (без корпус-улики в словарь не включено). Фикс - обе леммы
    # добавлены в `_DONORDEV_NO_START_RE`/`_DONORDEV_NO_PHRASE_RE`,
    # `_DEADLANG_NO_START_RE`/`_DEADLANG_NO_PHRASE_RE` (только «вложил» - «опознал»
    # семантически про идентификацию ТЕХНИКИ донора, вне домена dead-language) и
    # `_READFLAG_EXPLICIT_BAD_RE` (только «вложил» - тот же домен «справочник не
    # передан», «опознал» вне домена *_read).
    ("Д166 канон-фраза дословно «не опознал ни одного» (workflow/04-review.md:1005)",
     "не опознал ни одного", "NO"),
    ("Д166 «не опознал ни одного» ДО стрелки (порядок как в живом репро)",
     "§2.3 -> не опознал ни одного, PASS", "NO"),
    ("Д166 «не опознал ни одного» line-start",
     "не опознал ни одного, §2.3 -> PASS", "NO"),
    ("Д166 mid-line «справочник приёмов не вложили» (PHRASE, без N/A-триггера рядом)",
     "§2.3 «улика поста» -> PASS, но справочник приёмов не вложили", "NO"),
    ("Д166 контроль: «опознать не смог» вне евиденцированного набора лемм - "
     "не ломается (правило Д160/Д164)",
     "§2.3 удержание «улика поста» -> опознать не смог", "OK"),
    # --- 🔴 Д167 (fail-open, порядко-зависимость, скептик-раунд 56, по решению автора):
    # предмет искался ТОЛЬКО в хвосте ПОСЛЕ отказ-токена (И4) - «не подошёл ни
    # один приём» (отказ-глагол ПЕРВЫМ) читался OK, «ни один приём не подошёл»
    # (предмет ПЕРВЫМ) уже читался NO (START ловит «ни один» с начала сегмента
    # независимо от того, что дальше). 14 из 18 глаголов словаря-ПРЕДМЕТА
    # (`_DONORDEV_SUBJECT_RE`) текут в порядке «не V …», line-start И2 течёт так
    # же. ФИКС - механика (а) из двух кандидатов: новый фразовый класс в
    # `_DONORDEV_NO_PHRASE_RE` (PHRASE сканирует ВЕСЬ raw_full независимо от
    # позиции/порядка - проще и предсказуемее (б) симметричного И4). Леммы взяты
    # ИЗ УЖЕ ЕВИДЕНЦИРОВАННОГО словаря-ПРЕДМЕТА Д160/Д164 (не изобретены заново):
    # «подош\\w*»/«подойд\\w*»/«подходит»/«подходят»/«подходил\\w*»/«совпад\\w*»/
    # «совпал\\w*». «сработ\\w*»/«срабатыва\\w*» ИСКЛЮЧЕНЫ из PHRASE (тоже
    # евиденцированы в SUBJECT_RE, но живой репро на существующем контрольном
    # кейсе Д153б - «анти-паттерн (без описи и ссылки) не сработал» - доказал
    # ложный BLOCK: «не сработал» описывает ОТСУТСТВИЕ анти-паттерна, не отказ
    # техники; PHRASE не различает контекст, добавление ломает принятый OK).
    # СПОРНОЕ (задокументировано честно, как просил владелец): «приём не подошёл,
    # взял §2.4 вместо» (честная замена приёма) даёт `NO` ПОСЛЕ фикса - ТА ЖЕ
    # ЦЕНА, что УЖЕ была принята для евиденцированного root «наш» ДО этого фикса
    # (живой репро «приём не нашёл, взял §2.4 вместо» -> NO уже на живом хуке,
    # PHRASE не смотрит на «взял §2.4» отдельно от отказа), фикс не создаёт новый
    # класс размена, а расширяет уже принятый на симметричные глаголы. Гипотетика
    # «не подошёл бы без правок» тоже ловится NO (тот же класс, что и у всех
    # остальных 15 корней PHRASE - ни один не делает mood-детекцию, не новая
    # дыра).
    ("Д167 «не подошёл ни один приём» (отказ ДО предмета, порядок A)",
     "§2.3 -> не подошёл ни один приём, PASS", "NO"),
    ("Д167 line-start «не подошёл ни один приём» (порядок A)",
     "не подошёл ни один приём, §2.3 -> PASS", "NO"),
    ("Д167 контроль: инверсия «ни один приём не подошёл» держится (порядок B, "
     "уже работал через START до этого фикса)",
     "ни один приём не подошёл, §2.3 -> PASS", "NO"),
    ("Д167 честная замена приёма «взял §2.4 вместо» - принятая цена (тот же "
     "класс, что евиденцированный root «наш», не новый размен)",
     "§2.3 «улика поста» -> PASS · взял §2.4 вместо, приём не подошёл", "NO"),
    ("Д167 регресс-контроль: «сработ»/«срабатыва» НЕ добавлены в PHRASE (живой "
     "репро на Д153б - «анти-паттерн не сработал» не отказ, ложный BLOCK)",
     "§5.1 замкнутый контур передачи «улика» -> PASS, анти-паттерн (без описи и "
     "ссылки) не сработал", "OK"),
    ("Д167 «не подойдёт ни один вариант» (буд.вр., порядок A)",
     "§2.3 -> не подойдёт ни один вариант, PASS", "NO"),
    ("Д167 «не совпал ни один результат» (порядок A)",
     "§2.3 -> не совпал ни один результат, PASS", "NO"),
    ("Д167 честный контроль: «подходит по срокам» без отказа рядом не триггерит",
     "§2.3 удержание «улика» -> PASS · подходит по срокам", "OK"),
    # --- 🔴 Д168 (критический, fail-open, позиционный класс, скептик-раунд
    # 57, по решению автора): START-словарь якорен к началу сегмента - ЛЮБОЕ слово
    # слева (вводное или глагол) снимает словарь целиком. Поверхность А -
    # глагол ПЕРЕД квантором «ни один» («не сработал ни один приём», квантор
    # не на позиции 0 сегмента); поверхность Б - вводное слово ПЕРЕД голым
    # токеном («но нет подходящего приёма», «нет» сдвинут вправо). Полное
    # обоснование, измерения на 219 живых контролях и 72-форменная сетка
    # (12 токенов x 6 вводных, 66/72 реально текли) - баннер ФИКСА Д168 в
    # `post-phase-gate.sh` перед `_DONORDEV_NO_START_RE`.
    ("Д168-А «не сработал ни один приём» (глагол ДО квантора, вне PHRASE)",
     "не сработал ни один приём, §2.3 -> PASS", "NO"),
    ("Д168-А mid-line «§2.3 «улика» -> PASS, не сработал ни один приём»",
     "§2.3 «улика» -> PASS, не сработал ни один приём", "NO"),
    ("Д168-А «не зашёл ни один приём» (глагол вне ЛЮБОГО словаря)",
     "не зашёл ни один приём, §2.3 -> PASS", "NO"),
    ("Д168-Б «но нет подходящего приёма» (вводное «но» перед голым токеном)",
     "§2.3 «улика» -> PASS, но нет подходящего приёма", "NO"),
    ("Д168-Б «тут нет подходящего приёма» (вводное «тут»)",
     "§2.3 «улика» -> PASS, тут нет подходящего приёма", "NO"),
    ("Д168-Б «увы отсутствует приём справочника» (вводное «увы»; ДО этого "
     "фикса диагностировалось DEADLANG_NO через lead-окно чужого гейта - "
     "после фикса ловится СВОИМ гейтом, e2e.py 0/12 расхождений)",
     "§2.3 «улика» -> PASS, увы отсутствует приём справочника", "NO"),
    ("Д168 контроль Д153б: «анти-паттерн не сработал» держится OK (сработ/"
     "срабатыва НЕ в PHRASE, Д167 - свободный скан И6 читает ТОТ ЖЕ словарь "
     "START, не расширяет его новыми корнями)",
     "§2.3 удержание «улика поста» -> PASS · анти-паттерн (без описи и "
     "ссылки) не сработал", "OK"),
    # ЦЕНА (1 из 9 названных течей У И6 САМОЙ, НЕ закрыта - предмет ДО
    # квантора «ничего», глагол ПОСЛЕ него вне словаря-предмета;
    # bidirectional-расширение это чинит, но живой репро доказал ложный
    # BLOCK на многосентенционной честной прозе - «Справочник использован
    # полностью. Больше ничего добавлять не пришлось» → ложный NO, баннер
    # ФИКСА Д168 в хуке). Порядко-зависимая (tail-only) механика этой
    # дыры не имеет - названо ценой, ожидание ниже - ДЕЙСТВИТЕЛЬНОЕ
    # поведение (не регресс, а сознательно не закрытый край). 🔴 Д173
    # (скептик-раунд 59, по решению автора): БЫЛО ДВЕ ЦЕНЫ ЭТОГО КЛАССА - вторая
    # («приёмов ничего не дало», глагол «дал\w*») закрыта ОТДЕЛЬНЫМ
    # словарём `_DONORDEV_NO_DALO_RE` (не И6, кейс переехал ниже с
    # ожиданием `NO`, см. группу «Д173» после этого блока):
    ("Д168 ЦЕНА (1/1): «из справочника ничего не взял» (предмет ДО "
     "квантора «ничего», глагол «взял» ПОСЛЕ него вне словаря-предмета) - "
     "НЕ закрыто, порядко-зависимость И6 сохранена; держится ТОЛЬКО чужим "
     "DL-гейтом через lead-окно (Д171, misdiagnosis, документация)",
     "§2.3 «улика» -> PASS, из справочника ничего не взял", "OK"),
    # 🔴 Д173 (скептик-раунд 59, по решению автора, fail-open + ложное утверждение
    # Д171 - банер утверждал «блок держится» про ОБЕ формы, но ЭТА форма
    # раньше проходила OK НАСКВОЗЬ, DL её тоже не ловил - `_DEADLANG_
    # SUBJECT_RE` не несёт корень «приём»). ФИКС: новый словарь
    # `_DONORDEV_NO_DALO_RE` (сканирует кавычко-вырезанное значение, Д43-
    # класс снят) - диагноз теперь ПРАВИЛЬНЫЙ, `DONORDEV_NO` У DD САМОЙ, а
    # не случайный `DEADLANG_NO` соседнего гейта. Живой прогон ДО фикса -
    # `scratchpad/r62s/d175_named_price.py` (`OK`, выпущено БЕЗ БЛОКА).
    ("Д173 ФИКС: «приёмов ничего не дало» (глагол «дал\\w*», форма 2 "
     "именованной цены Д168) - была fail-open (`OK`), с этого фикса своя "
     "DONORDEV_NO, форма 1 «…не взял» НЕ тронута",
     "§2.3 «улика» -> PASS, приёмов ничего не дало", "NO"),
    ("Д173 вариант «приёмы ничего не дали» (мн.ч., тот же словарь "
     "`_DONORDEV_NO_DALO_RE`)",
     "§2.3 «улика» -> PASS, приёмы ничего не дали", "NO"),
    ("Д173 контроль Д43: ЧЕСТНАЯ цитата поста «ничего не дало» ВНУТРИ «…» "
     "НЕ отказ (`_DONORDEV_NO_DALO_RE` сканирует кавычко-вырезанное "
     "значение - Д43-класс снят для этого словаря)",
     "§2.3 «в первый месяц ничего не дало эффекта, потом пошло» -> PASS",
     "OK"),
    # ЦЕНА (названный скептиком ложный BLOCK свободного скана): «приём» в
    # ОБЩЕМ маркетинговом смысле («приём закрытия»), не ссылка §N.M -
    # `_DONORDEV_SUBJECT_RE` смысл не различает. В живом корпусе такой
    # формы нет (грепом подтверждено) - кейс с ОЖИДАНИЕМ `NO` как цена,
    # не тихий пропуск:
    ("Д168 ЦЕНА (3/3): «нет призыва как приёма закрытия» (общее «приём», "
     "не ссылка на §N.M справочника) - ложный BLOCK, названная цена И6, "
     "формы нет в живом корпусе",
     "§5.2 нулевой CTA в продающем «Такие дела» -> PASS - в посте нет "
     "призыва как приёма закрытия", "NO"),
]


def test_hook_donordev_gate():
    """🔴 Дефект Д45 (скептик-раунд 10, по решению автора): У ГЕЙТА donor-devices НЕ БЫЛО
    НИ ОДНОГО ТЕСТА.

    Гейт кода живёт в `post-phase-gate.sh` с раунда 5 (Д28) и с тех пор правился
    пять раз - и КАЖДЫЙ дефект находил скептик глазами, потому что `grep donordev`
    по раннеру давал ноль. Класс дефекта не «в функции ошибка», а «функцию никто не
    гоняет». Тест закрывает именно это: он берёт ЖИВУЮ функцию из хука (см.
    `_hook_donordev_state`) и прогоняет её по всем пяти состояниям.

    Отдельно держится обратная сторона Д43: «нетривиальный приём §2.3» - НЕ отказ.
    Без слово-границы регекс отказа съел бы честный отчёт, а это ровно тот ложный
    BLOCK, который чинили Д35 и Д36.

    🔴 Д47 (раунд 11): SKIP остался РОВНО на один случай - хука нет на диске (машина
    ученика). Любой другой отказ выреза - FAIL с честной причиной: сломанный вырез
    означает, что страж гейта не гоняет НИЧЕГО, и молчать об этом нельзя."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д45 хук: гейт donor-devices (все состояния)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д45 хук: гейт donor-devices - все состояния на ЖИВОЙ функции хука",
               False, err)
        return
    bad = []
    for name, val, want in DONORDEV_CASES:
        # 🔴 Д132а (скептик-раунд 44, по решению автора): `val`, начинающийся с `|`,
        # несёт ГОТОВУЮ pipe-табличную строку целиком («| donor-devices |
        # значение |») - подставляется КАК ЕСТЬ, а не через колон-шаблон
        # `donor-devices: %s` (двойная обёртка дала бы «donor-devices: |
        # donor-devices | … |» - искажённый вход, который не проверяет
        # табличную форму вовсе). Голое значение (без `|` в начале) - как
        # раньше, оборачивается в колон-форму.
        text = ("донор-разбор\n%s\nВЕРДИКТ: PASS\n" % val if val.lstrip().startswith("|")
                else "донор-разбор\ndonor-devices: %s\nВЕРДИКТ: PASS\n" % val)
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    got = st("Верификатор всё проверил, donor-devices смотрел, приём есть.\nВЕРДИКТ: PASS\n")
    if got != "MISSING":
        bad.append(f"проза без строки: ждём MISSING, получили {got}")
    record("Д45 хук: гейт donor-devices - все состояния на ЖИВОЙ функции хука",
           not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 FIX-R38 (класс Д28, зеркало donor-devices, по решению автора): ГЕЙТ dead-language
# НЕ ИМЕЛ НИ ОДНОГО ТЕСТА - ровно тот же дефект-класс, что Д45 закрыл у
# donor-devices. Строка-отчёт `dead-language: чисто | N слов заменено`
# обязательна ТЕКСТОМ (`workflow/04-review.md:994` - таблица обязательных
# строк 4.M.2, `:1001` - сам промпт верификатора), но хук не проверял её
# НИЧЕМ: `grep dead.language` по этому раннеру ДО FIX-R38 давал ноль. Тест
# ниже - зеркало `_hook_donordev_ns`/`_hook_donordev_state`/
# `test_hook_donordev_gate` выше: вырезает ЖИВУЮ функцию `_deadlang_state` из
# хука (не копирует - копия рассинхронится с хуком в первый же раунд правок,
# как объяснено в докстринге `_hook_donordev_ns`), гоняет её по всем
# состояниям и ДОПОЛНИТЕЛЬНО регрессирует 3 опорных donordev-кейса на
# `_hook_donordev_state`, чтобы подтвердить: вставка нового блока рядом с
# `_donordev_state` (тот же файл, соседний код) не сдвинула якорь-экстрактор
# `_hook_donordev_ns` и не задела саму функцию donordev.
# ---------------------------------------------------------------------------

def _hook_deadlang_ns():
    """Вырезает ЖИВОЙ кусок гейта `dead-language` из post-phase-gate.sh и
    ИСПОЛНЯЕТ его - зеркало `_hook_donordev_ns()` выше (тот же контракт
    `(namespace, причина)`, тот же приём резки по якорям, то же обоснование
    «вырезаем, а не копируем» - см. докстринг `_hook_donordev_ns` целиком,
    здесь он не повторяется).

    Возвращает пару `(namespace, причина)`:
      (ns, "")           вырез удался;
      (None, "NOHOOK")   хука нет на диске - ЕДИНСТВЕННЫЙ случай под skip;
      (None, <текст>)    вырез/exec не удались = FAIL с честной причиной
                         (в т.ч. если FIX-R38 ещё не применён - якоря
                         `_DEADLANG_RE`/`_deadlang_state` в хуке попросту нет,
                         это честный FAIL, а не SKIP: страж должен красным
                         сигналить «гейта нет», а не молчать)."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать функцию "
                      "_deadlang_state не из чего" % HOOK)
    lines = src.splitlines(True)
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("_DEADLANG_RE = re.compile("))
    except StopIteration:
        return None, ("функция не вырезалась из хука - якорь `_DEADLANG_RE = "
                      "re.compile(` не найден (FIX-R38 ещё не применён, или "
                      "якорь сдвинут/переименован) - тест-страж гейта dead-"
                      "language обезоружен")
    end, seen_def = None, False
    for i in range(start, len(lines)):
        if lines[i].startswith("def _deadlang_state("):
            seen_def = True
            continue
        if seen_def and lines[i][:1] not in ("", " ", "\t", "\n", "#"):
            end = i
            break
    if not seen_def:
        return None, ("функция не вырезалась из хука - якорь `def "
                      "_deadlang_state(` не найден после `_DEADLANG_RE`; "
                      "тест-страж гейта dead-language обезоружен")
    # 🔴 Д112 (скептик-раунд 39, по решению автора): namespace ЗАСЕВАЕТСЯ куском
    # donor-devices. После Д112 `_deadlang_state` зовёт `_donordev_strip_quoted`
    # (вырезать цитаты поста перед сканом на слова отказа - иначе цитата «я не
    # проверял гипотезу» внутри пары читалась бы как отказ верификатора). Эта
    # функция определена ВЫШЕ по файлу хука, ЗА границей выреза dead-language,
    # и без засева exec упал бы NameError'ом на первом же вызове. Копировать её
    # в тест нельзя по тому же закону, что записан в `_hook_donordev_ns`:
    # копия рассинхронится с хуком в первый же раунд правок. Берём живой
    # namespace соседнего выреза - один источник истины остаётся один.
    ns = {"re": re}
    dns, _derr = _hook_donordev_ns()
    if dns:
        ns.update({k: v for k, v in dns.items() if not k.startswith("__")})
    try:
        exec(compile("".join(lines[start:end or len(lines)]), HOOK, "exec"), ns)
    except Exception as e:
        return None, ("вырезанный кусок хука не исполняется (%s: %s) - границы "
                      "выреза сдвинуты или код функции битый; тест-страж гейта "
                      "dead-language обезоружен" % (type(e).__name__, e))
    return ns, ""


def _hook_deadlang_state():
    """ЖИВАЯ функция `_deadlang_state` из хука (обёртка над
    `_hook_deadlang_ns`, зеркало `_hook_donordev_state` выше). Контракт пары
    `(функция, причина)` тот же: `NOHOOK` = skip, любая другая причина =
    FAIL, пустая строка = вырез удался."""
    ns, err = _hook_deadlang_ns()
    if ns is None:
        return None, err
    fn = ns.get("_deadlang_state")
    if fn is None:
        return None, ("кусок исполнился, но имени _deadlang_state в нём нет - "
                      "функцию переименовали? тест-страж гейта dead-language "
                      "обезоружен")
    return fn, ""


# (что проверяем, значение строки dead-language, ожидаемое состояние) -
# зеркало DONORDEV_CASES. Легальных ФОРМ значения у этой строки ровно две
# («чисто» и «N слов заменено» с парами - 04-review.md 4.M.2 не знает третьей),
# а СОСТОЯНИЙ после раунда 39 пять: MISSING · NO (отказ словарём, префиксом
# или фразой - Д112) · LITERAL (пересказ шаблона - Д113) · NOPAIRS (число без
# пар-улик - Д113) · OK. Ровно как у зеркала: чем больше состояний, тем точнее
# диагноз оператору, и новое состояние не может молча выпасть в OK (урок Д29).
DEADLANG_CASES = [
    # --- штатное использование: гейт обязан ПРОПУСКАТЬ ---
    ("чисто, нижний регистр", "чисто", "OK"),
    ("ЧИСТО, верхний регистр (терпимость к регистру)", "ЧИСТО", "OK"),
    ("Чисто, смешанный регистр", "Чисто", "OK"),
    # --- Д108 (скептик-раунд 38, по решению автора): значение обёрнуто markdown/кавычками -
    # верификатор реально так печатает («**чисто**», ««чисто»»), а прежний
    # `_DEADLANG_OK_RE` был жёстко заякорен `^\s*чист` на СЫРОЕ значение и падал в
    # ложный NO-блок на честном PASS. См. докстринг `_deadlang_state` в хуке.
    ("Д108 значение в **bold**", "**чисто**", "OK"),
    ("Д108 значение в «ёлочках»", "«чисто»", "OK"),
    # --- контроль обратной стороны Д108: отказ, начинающийся со слова «не», не
    # должен ослабляться нормализацией - «не чисто» НЕ форма «чисто» ---
    ("Д108 контроль: «не чисто» - НЕ ослаблено фиксом, остаётся отказом",
     "не чисто, нашёл пару слов", "NO"),
    ("N слов заменено, каноничная форма (04-review.md:994)",
     "3 слов заменено · «мёртвое» -> «живая замена»", "OK"),
    ("N слов заменено, несколько пар-улик",
     "2 слова заменено · «методология» -> «пошаговый план» · «оптимизировать» "
     "-> «сделать быстрее»", "OK"),
    # --- 🔴 Д112 (скептик-раунд 39, по решению автора): отказ, развёрнутый во ФРАЗУ.
    # Все три формы ДО фикса давали ложный OK и выпускали пост: словарь
    # `_DEADLANG_NO` ловил только ЦЕЛОЕ значение, а дальше поднимала в OK
    # либо числовая ветка, либо КОРЕНЬ `чист\w*` (совпадает с «чистоту»).
    # Кейс E тяжелейший: верификатор прямо говорит о поломке пакета.
    ("Д112-C отказ + число: «не проверял, 0 замен»", "не проверял, 0 замен", "NO"),
    ("Д112-D отказ фразой после слова на «чист»: «чистоту не проверял»",
     "чистоту не проверял", "NO"),
    ("Д112-E отказ про непереданный справочник рядом с «чисто»",
     "чисто, но справочник zhivoy-yazyk.md в промпт не вложен", "NO"),
    # обратная сторона Д112: сужение «чисто» до слова целиком не должно рубить
    # честный отчёт, который просто НАЧИНАЕТСЯ с однокоренного слова
    ("Д112 контроль: «чистка словаря» + честные пары - НЕ отказ",
     "чистка словаря завершена, 2 слова заменено · «методология» -> "
     "«пошаговый план»", "OK"),
    # --- 🔴 Д113 (скептик-раунд 39): пересказ шаблона и число без пар ---
    ("Д113 литерал шаблона 04-review 4.M.2 (короткая форма)",
     "3 слов заменено · «<мёртвое>» -> «<живая замена>»", "LITERAL"),
    ("Д113 литерал шаблона 04-review 4.M.2 (полная форма)",
     "2 слова заменено · «<мёртвое из поста цитатой>» -> «<живая замена из "
     "разд.4>»", "LITERAL"),
    # 🔴 ИЗМЕНЕНИЕ ОЖИДАНИЯ ПРОТИВ FIX-R38 (осознанное, Д113 раунда 39): две
    # строки ниже раньше стояли как "OK" («3 слова заменено» / «5 замен» -
    # форма из требования задачи R38). Канон это опроверг: `04-review.md`
    # 4.M.2 требует пару «<мёртвое из поста цитатой>» -> «<живая замена из
    # разд.4>» на КАЖДОЕ слово, а правило засчитывания того же раздела говорит
    # «строка есть, но без цитаты и чисел → вердикт не засчитан». У «3
    # заменено» число есть, цитат нет - проверять нечего, fail-closed.
    ("Д113 число без единой пары-улики (было OK до раунда 39)",
     "3 слова заменено", "NOPAIRS"),
    ("Д113 голое число + «замен» без пар (было OK до раунда 39)",
     "5 замен", "NOPAIRS"),
    ("Д113 ноль замен - пар не требует, это та же «чисто» другими словами",
     "0 слов заменено", "OK"),
    # --- отказ словарём (04-review.md:994 называет явно три слова) ---
    ("отказ «не проверял» (04-review.md:994, явный пример)", "не проверял", "NO"),
    ("отказ N/A (04-review.md:994, явный пример)", "N/A", "NO"),
    ("отказ «ок» (04-review.md:994, явный пример)", "ок", "NO"),
    ("отказ «-» (голый прочерк вместо факта)", "-", "NO"),
    ("отказ «нет»", "нет", "NO"),
    ("пустое значение", "", "NO"),
    # --- fail-closed на всё, что не совпало ни со словарём, ни с легальной формой ---
    ("не число и не «чисто» - произвольная проза", "проверил, всё в порядке", "NO"),
    ("число без слова «замен» рядом - не считается legal-формой",
     "3 слова изменено", "NO"),
    # --- 🔴 Д118 (скептик-раунд 40, по решению автора): фразовый отказ рядом с «чисто» -
    # белый список ПЯТИ корней глагола (Д112: провер/вложен/передан/прочитан/
    # доступ) не закрывал КЛАСС - любой ШЕСТОЙ глагол признания проходил мимо
    # словаря и «чисто, <признание другим глаголом>» выпускало пост при явном
    # отказе. Десять форм ниже - ни одна НЕ входит в старый пятисловный список
    # (каждая репродуцирует ложный OK на непропатченном хуке, см.
    # verify-FIX-R41.sh). ФИКС - структурная проверка `_deadlang_clean_admits_
    # absence()`: токен ПРЕДМЕТА + токен ОТРИЦАНИЯ в одной фразе после «чисто».
    ("Д118-1 «справочник не открывал» (глагол вне старого списка)",
     "чисто, справочник не открывал", "NO"),
    ("Д118-2 «антисловарь не смотрел» (глагол вне старого списка)",
     "чисто, антисловарь не смотрел", "NO"),
    ("Д118-3 «словаря не было под рукой» (оборот «не было», не глагол)",
     "чисто, словаря не было под рукой", "NO"),
    ("Д118-4 «в справочник не заглядывал» (глагол вне старого списка)",
     "чисто, я в справочник не заглядывал", "NO"),
    ("Д118-5 «мне не показали» (subject=zhivoy-yazyk.md - точка в имени файла "
     "не должна резать фразу)",
     "чисто, zhivoy-yazyk.md мне не показали", "NO"),
    ("Д118-6 «так и не нашёл» (глагол вне старого списка)",
     "чисто, антисловарь так и не нашёл", "NO"),
    ("Д118-7 «без справочника проверял» (токен «без», не «не»)",
     "чисто, без справочника проверял", "NO"),
    ("Д118-8 «словаря нет под рукой» («нет» не в начале значения, не префикс)",
     "чисто, словаря нет под рукой", "NO"),
    ("Д118-9 «разд.3 мне не давали» (subject=разд.3, точка перед цифрой не "
     "должна резать фразу)",
     "чисто, разд.3 мне не давали", "NO"),
    ("Д118-10 «референс так и не появился» (глагол вне старого списка)",
     "чисто — референс так и не появился", "NO"),
    # --- контроль обратной стороны Д118: субъект упомянут БЕЗ отрицания в той
    # же фразе - структурная проверка не должна рубить честный отчёт ---
    ("Д118-контроль «проверил по справочнику разд.3» - НЕ отказ",
     "чисто, проверил по справочнику разд.3", "OK"),
    ("Д118-контроль «справочник прочитан» - НЕ отказ",
     "чисто (справочник прочитан)", "OK"),
    # --- 🔴 Д128 (скептик-раунд 43, в даты запуска.2026): МЕНЮ-ЛИТЕРАЛ «ЧИСТО ИЛИ
    # N СЛОВ ЗАМЕНЕНО» - дословный пересказ строки меню 04-review.md:996
    # («dead-language: чисто» **или** «dead-language: N слов заменено …»)
    # засчитывался как честное «чисто»: `_DEADLANG_CLEAN_RE` якорит начало и
    # дальше значение не читает. Различитель - БУКВА `N` (латиницей, как в
    # каноне) вместо ЦИФРЫ у настоящего счётчика; работает на всех трёх
    # формах разделителя канона («или»/«|»/«//» - после нормализации все три
    # сводятся к одному скелету).
    ("Д128 меню-литерал, разделитель «или» (дословно 04-review.md:996)",
     "чисто или N слов заменено", "LITERAL"),
    ("Д128 меню-литерал, разделитель «|»",
     "чисто | N слов заменено", "LITERAL"),
    ("Д128 меню-литерал, разделитель «//»",
     "чисто // N слов заменено", "LITERAL"),
    # --- контроль обратной стороны Д128: честные ответы держатся ---
    ("Д128 контроль: честное «чисто» - НЕ меню (нет буквы N)", "чисто", "OK"),
    ("Д128 контроль: честное «2 слова заменено» с парой - НЕ меню (цифра, не N)",
     "2 слова заменено · «методология» -> «пошаговый план»", "OK"),
    # --- 🔴 Д132б (скептик-раунд 44, по решению автора): зеркало Д132а для dead-
    # language - pipe-табличная форма без двоеточия давала ложный `MISSING`.
    # Фикс - зеркало `_DEADLANG_TABLE_RE`. `val` несёт ГОТОВУЮ pipe-строку
    # целиком (начинается с `|`) - `test_hook_deadlang_gate` подставляет её
    # КАК ЕСТЬ (см. правку цикла подстановки в самом тесте ниже).
    ("Д132б табличная форма без двоеточия, честное «чисто»",
     "| dead-language | чисто |", "OK"),
    ("Д132б табличная форма без двоеточия, отказ «не проверял»",
     "| dead-language | не проверял |", "NO"),
    # --- 🔴 Д146-зеркало (регресс-фиксация, НЕ новый фикс, по решению автора): у
    # donor-devices §-ссылка ПЕРЕД словом отказа маскировала отказ, ПОСЛЕ
    # стрелки-вердикта (см. DONORDEV_CASES выше) - у dead-language ЭТОГО
    # класса дефекта нет, потому что `_deadlang_state_one` НЕ режет значение
    # ни по какой стрелке/разделителю перед PHRASE-проверкой: `raw =
    # m.group(1).strip()` берётся ЦЕЛИКОМ, `_DEADLANG_NO_PHRASE_RE` сканирует
    # весь `raw` (после вырезки закавыченных спанов) независимо от позиции
    # отказа внутри значения. Кейс закрепляет уже-корректное поведение.
    ("Д146-зеркало DL: признание «не сверял» рядом с «чисто» - уже блокирует "
     "независимо от позиции (не новый фикс, страхует от регресса)",
     "чисто, но не сверял со словарём", "NO"),
    # --- 🔴 Д147 (скептик-раунд 51, по решению автора), ЗЕРКАЛО У DEAD-LANGUAGE -
    # СВОЙ МЕХАНИЗМ, НЕ КОПИЯ ФИКСА DD. `_deadlang_state_one` НЕ режет `raw`
    # по стрелке вовсе (стрелка тут легально живёт ВНУТРИ числовой формы как
    # разделитель пары «мёртвое» -> «живая замена», резать по ней было бы
    # неправильно) - дефект жил В ДРУГОМ месте: `_DEADLANG_CLEAN_RE`
    # (`^\s*чист(?:о|ы|а|ое|ые|ая)?\b`) якорена к НАЧАЛУ значения, но НЕ
    # требует, чтобы «чисто» было значением ЦЕЛИКОМ - хвост ПОСЛЕ «чисто» не
    # проверялся структурной формой вовсе, только узкий `_deadlang_clean_
    # admits_absence` (требует токен ПРЕДМЕТА + токен ОТРИЦАНИЯ РЯДОМ) - голый
    # отказ БЕЗ упоминания предмета («чисто -> нет») предмета не несёт,
    # проходил CLEAN-веткой честным `OK`. Живой репро: «чисто -> нет»/
    # «чисто -> ок»/«чисто -> N/A» → `OK` вместо `NO`. ФИКС: хвост значения
    # ПОСЛЕ распознанного префикса «чисто» (из quote-stripped `soft_nq`, не
    # сырого `soft` - см. контроль-кейс с цитатой ниже) проверяется теми же
    # словарями отказа `_DEADLANG_NO_START_RE`/`_DEADLANG_NO_PHRASE_RE`.
    ("Д147 DL START после «чисто»: «нет»",
     "чисто -> нет", "NO"),
    ("Д147 DL START после «чисто»: «ок»",
     "чисто -> ок", "NO"),
    ("Д147 DL START после «чисто»: «N/A»",
     "чисто -> N/A", "NO"),
    ("Д147 DL START после «чисто»: «нету»",
     "чисто -> нету", "NO"),
    ("Д147 DL START после «чисто»: «отсутствует»",
     "чисто -> отсутствует", "NO"),
    ("Д147 DL контроль-цитата: «нет» ВНУТРИ цитаты поста сразу за «чисто» - "
     "хвост берётся из quote-stripped soft_nq, ложного BLOCK нет",
     "чисто, «нет ничего мёртвого» - именно так я и написал", "OK"),
    ("Д147 DL контроль честный: голое «чисто» без довеска - НЕ задето",
     "чисто", "OK"),
    ("Д147 DL контроль: числовая ветка с ЛЕГАЛЬНЫМ хвостом-парой - НЕ "
     "задета (фикс не режет arrow-разделитель числовой формы)",
     "3 слов заменено · «мёртвое» -> «живая замена»", "OK"),
    # --- 🔴 Д151 (скептик-раунд 52, по решению автора): ЧИСЛОВАЯ ВЕТКА НЕ ЗВАЛА
    # _deadlang_clean_admits_absence ВООБЩЕ - признание рядом с честным числом+
    # парами проходило как `OK` (CLEAN-ветка «чисто» это уже умела с Д118/
    # Д121, числовая - никогда). ФИКС - тот же вызов `_deadlang_clean_admits_
    # absence(raw, "", tail)` ПЕРВЫМ шагом внутри `if cnt:`, ДО разбора нулевой/
    # парной формы; БЕЗ `lead` (спорное решение, задокументировано в коде -
    # `lead` статистически чаще несёт несвязанный заголовок, живой регресс на
    # существующем «Д113 контроль: пар нет…» ниже это подтвердил).
    ("Д151 fail-open: числовая ветка с легальными парами + признание рядом "
     "ТОЙ ЖЕ строкой («справочник не открывал») - было OK, должно быть NO",
     "3 слова заменено · «шаг» -> «нажми кнопку» · справочник не открывал",
     "NO"),
    ("Д151 fail-open: числовая ветка, признание «антисловарь … не показали»",
     "3 слова заменено · «шаг» -> «нажми кнопку» · "
     "антисловарь разд.3 мне не показали", "NO"),
    ("Д151 контроль: числовая ветка, легальные пары БЕЗ признания - "
     "детектор ищет предмет+отрицание, не стрелку/кавычки, OK держится",
     "3 слова заменено · «шаг» -> «нажми кнопку» · «путь» -> «дорога»", "OK"),
    # --- 🔴 Д166 зеркало DL (скептик-раунд 56, по решению автора, полное обоснование -
    # баннер Д166 в DONORDEV_CASES выше): «вложил\\w*» добавлена в
    # `_DEADLANG_NO_START_RE`/`_DEADLANG_NO_PHRASE_RE` зеркалом DD. Значение как
    # ЕДИНСТВЕННОЕ вхождение уже давало `NO` ДО фикса через fail-closed
    # catch-all `_deadlang_state_one` (любое нераспознанное значение - не
    # «чисто», не «N слов заменено» - и так `NO`) - кейс регрессия-лок держит
    # словарное распознавание явным, а не только catch-all'ом. РЕАЛЬНЫЙ класс
    # Д166 у DL живёт в mid-line worst-wins (`_deadlang_looks_explicit`,
    # Д136) - «не вложили» рядом (но НЕ на своей line-start строке) с честной
    # «dead-language: чисто» давало ложный `OK`, т.к. фильтр НЕ признавал
    # «вложил» «явной формой» без словаря; эмпирически доказано и закрыто
    # живым прогоном (scratchpad r60/probe_d166_midline_dl.py +
    # probe_d166_debug.py - две-occurrence репро с >300-знаковым разрывом
    # против lead-bleed соседней line-start строки), постоянным тестом здесь
    # НЕ оформлено (single-occurrence обвязка DEADLANG_CASES эту позицию не
    # различает).
    ("Д166 DL зеркало: значение «справочник приёмов не вложили» (fail-closed "
     "catch-all уже давал NO ДО фикса; регрессия-лок держит явный словарь тоже)",
     "справочник приёмов не вложили", "NO"),
]


def test_hook_deadlang_gate():
    """🔴 FIX-R38 (класс Д28, зеркало donor-devices, по решению автора): у гейта
    dead-language не было ни одного теста, хотя контракт строки («обязательная
    именованная строка, отказ нелегален, штатной деградации нет») текстом
    отдан `04-review.md:994`/`:1001` ещё в v2.4 (по решению автора, фаза 9.2). Хук
    эту строку не проверял НИЧЕМ до FIX-R38 - см. докстринг `_deadlang_state`
    в самом хуке. Тест берёт ЖИВУЮ функцию (см. `_hook_deadlang_state`) и
    прогоняет её по DEADLANG_CASES, ЗАТЕМ регрессирует 3 опорных donordev-
    кейса на `_hook_donordev_state()` - подтверждает, что вставка нового
    блока по соседству (тот же файл, между `_donordev_state` и шапкой Д48)
    не сдвинула экстрактор `_hook_donordev_ns` и не задела саму функцию."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("FIX-R38 хук: гейт dead-language (все состояния)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("FIX-R38 хук: гейт dead-language - все состояния на ЖИВОЙ функции хука",
               False, err)
        return
    bad = []
    for name, val, want in DEADLANG_CASES:
        # 🔴 Д132б (скептик-раунд 44, по решению автора): зеркало Д132а у donor-
        # devices выше - `val`, начинающийся с `|`, несёт ГОТОВУЮ pipe-
        # табличную строку целиком, подставляется КАК ЕСТЬ.
        text = ("живой-разбор\n%s\nВЕРДИКТ: PASS\n" % val if val.lstrip().startswith("|")
                else "живой-разбор\ndead-language: %s\nВЕРДИКТ: PASS\n" % val)
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    got = st("Верификатор всё проверил, антисловарь смотрел, слов не нашёл.\nВЕРДИКТ: PASS\n")
    if got != "MISSING":
        bad.append(f"проза без строки: ждём MISSING, получили {got}")
    record("FIX-R38 хук: гейт dead-language - все состояния на ЖИВОЙ функции хука",
           not bad, "; ".join(bad))

    # --- регресс: 3 опорных donordev-кейса не задеты вставкой блока рядом ---
    dst, derr = _hook_donordev_state()
    if derr == "NOHOOK":
        skip("FIX-R38 регресс: 3 опорных donordev-кейса не задеты соседством",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if dst is None:
        record("FIX-R38 регресс: 3 опорных donordev-кейса не задеты соседством",
               False, derr)
        return
    _anchor_cases = [
        ("штатный §N.M", "§2.3 смена системы отсчёта «цитата» -> PASS", "OK"),
        ("отказ «нет»", "нет", "NO"),
        ("литерал шаблона (Д29б)",
         "<§номер + название приёма> «<строка-улика поста>» -> PASS", "LITERAL"),
    ]
    dbad = []
    for name, val, want in _anchor_cases:
        got = dst("донор-разбор\ndonor-devices: %s\nВЕРДИКТ: PASS\n" % val)
        if got != want:
            dbad.append(f"{name}: ждём {want}, получили {got}")
    record("FIX-R38 регресс: 3 опорных donordev-кейса не задеты соседством "
           "нового блока dead-language", not dbad, "; ".join(dbad))


# (имя, ПОЛНАЯ строка транскрипта - не только значение, ЛЕЙБЛ тоже обёрнут
# markdown/списком, поэтому не влезает в шаблон "dead-language: %s" -> ждём
# от `_deadlang_state` на ВСЁМ ответе целиком, ожидаемое состояние)
_DEADLANG_MARKDOWN_LABEL_CASES = [
    ("Д108 булет + bold-лейбл, значение плоское",
     "разбор антисловаря\n- **dead-language:** чисто\nВЕРДИКТ: PASS\n", "OK"),
    ("Д108 плоский лейбл, bold-значение",
     "разбор антисловаря\ndead-language: **чисто**\nВЕРДИКТ: PASS\n", "OK"),
    # 🔴 Д113 (раунд 39): пары НА СЛЕДУЮЩИХ строках засчитываются наравне с
    # парами в самой строке. `_DEADLANG_RE` берёт значение только до конца
    # строки, поэтому без этого смягчения честный многострочный отчёт
    # верификатора давал бы ложный `NOPAIRS` - ровно тот размен, который Д69
    # снял у donor-devices («позиция ссылки внутри значения больше не важна»).
    ("Д113 пары следующими строками - НЕ ложный NOPAIRS",
     "разбор антисловаря\ndead-language: 2 слова заменено\n"
     "  «методология» -> «пошаговый план»\n"
     "  «прозрачность» -> «показываю цифры и результаты»\nВЕРДИКТ: PASS\n", "OK"),
    # контроль обратной стороны: пар нет НИГДЕ - ни в строке, ни в хвосте
    ("Д113 контроль: пар нет ни в строке, ни в хвосте - NOPAIRS",
     "разбор антисловаря\ndead-language: 2 слова заменено\n"
     "всё поправил, вопросов нет\nВЕРДИКТ: PASS\n", "NOPAIRS"),
]


def test_hook_deadlang_markdown_labels():
    """🔴 Д108 (скептик-раунд 38, по решению автора). `_DEADLANG_OK_RE` был заякорен
    `^\\s*чист` на СЫРОЕ значение строки - «**чисто**», ««чисто»», «- **dead-
    language:** чисто» давали ложный `DEADLANG_NO` (блок на честном PASS),
    потому что markdown-обвязка/кавычки стояли ПЕРЕД словом «чисто», а якорь
    требовал его буквально первым символом (после пробелов). ФИКС - мягкая
    нормализация значения (зеркало `_donordev_soft`) ПЕРЕД проверкой якоря,
    не снятие якоря целиком (сняли бы якорь - «не чисто» стало бы ложным OK,
    см. контрольный кейс в DEADLANG_CASES).

    Этот тест - зеркало `test_hook_deadlang_gate` выше, но гоняет ДВЕ ПОЛНЫЕ
    строки транскрипта (не только значение через фиксированный шаблон
    "dead-language: %s"): в обоих случаях бывает обёрнут САМ ЛЕЙБЛ
    («- **dead-language:**»), а это касается работы `_DEADLANG_RE`
    (извлечение значения из полной строки), а не только `_DEADLANG_OK_RE`
    (проверка значения) - раздельное покрытие обеих частей пайплайна."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д108 хук: markdown-обёртка лейбла/значения dead-language не блокирует честный PASS",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д108 хук: markdown-обёртка лейбла/значения dead-language не блокирует честный PASS",
               False, err)
        return
    bad = []
    for name, full_line, want in _DEADLANG_MARKDOWN_LABEL_CASES:
        got = st(full_line)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д108 хук: markdown-обёртка лейбла/значения dead-language не блокирует честный PASS",
           not bad, "; ".join(bad))


def test_deadlang_missing_reference_is_hard_fail():
    """Д119 (скептик-раунд 40, по решению автора): `_deadlang_state` не проверял
    СУЩЕСТВОВАНИЕ `references/zhivoy-yazyk.md` на диске - зеркало Д105
    (раунд 37), закрытого у donor-devices: `_donordev_state` падает в
    `NOSIG` (hard-block), если `references/donor-copy-devices.md`
    недоступен, а `_deadlang_state` до FIX-R41 пропускал ЛЮБУЮ легальную
    форму («чисто»/«N слов заменено» с парами) без единой проверки, что
    справочник живого языка вообще существует - строка-отчёт судилась
    ТОЛЬКО текстом, без сверки с диском. Канон называет отсутствие файла
    поломкой пакета, не штатной деградацией - `04-review.md` 4.M.2 («…
    файл раздаётся вместе со скиллом, поэтому его отсутствие - не штатная
    деградация, а поломка пакета») и `05-publish.md` поле 7
    `zhivoy_yazyk_read` («N/A тут не легален, зеркало donordev_read»).

    Тот же приём, что `test_donordev_missing_reference_is_hard_fail`:
    `_hook_deadlang_ns()`/`_hook_deadlang_state()` исполняют вырезанный
    кусок хука ЗАНОВО при каждом вызове, путь справочника внутри куска
    читает `os.environ.get("SKILL_DIR")` на момент exec - смена
    `SKILL_DIR` МЕЖДУ вызовами реально меняет поведение свежего среза.
    Проверка в два шага: (1) `SKILL_DIR` указывает на временный каталог
    БЕЗ файла справочника - ОБЕ легальные формы обязаны дать `NOSIG`, а не
    `OK`; (2) контроль - тот же каталог, но с КОПИЕЙ живого справочника
    внутри, те же формы снова дают штатный `OK` (Д118 не задет этим
    тестом - ни одна форма в тесте не несёт признания рядом с «чисто»)."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д119: справочник живого языка недоступен -> NOSIG (hard-block)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д119: справочник живого языка недоступен -> NOSIG (hard-block)",
               False, err)
        return
    old_skill_dir = os.environ.get("SKILL_DIR")
    zhivoy_ref_md = os.path.join(os.path.dirname(SCRIPTS), "references",
                                  "zhivoy-yazyk.md")
    bad = []
    try:
        td = tempfile.mkdtemp(prefix="d119-nosig-")
        os.makedirs(os.path.join(td, "references"), exist_ok=True)
        # references/zhivoy-yazyk.md НАМЕРЕННО отсутствует - поломка пакета.
        os.environ["SKILL_DIR"] = td
        st_missing, err_missing = _hook_deadlang_state()
        if st_missing is None:
            bad.append("срез с SKILL_DIR=temp(без файла) не удался: %s" % err_missing)
        else:
            for name, val in (
                ("форма «чисто»", "чисто"),
                ("форма «N слов заменено» с парой",
                 "2 слова заменено · «методология» -> «пошаговый план»"),
                ("форма «0 слов заменено»", "0 слов заменено"),
            ):
                got = st_missing("живой-разбор\ndead-language: %s\nВЕРДИКТ: PASS\n" % val)
                if got != "NOSIG":
                    bad.append("без файла справочника, %s -> ждали NOSIG, получили %s "
                               "(Д119 не применён/сломан)" % (name, got))

        if os.path.isfile(zhivoy_ref_md):
            shutil.copy(zhivoy_ref_md,
                        os.path.join(td, "references", "zhivoy-yazyk.md"))
            st_present, err_present = _hook_deadlang_state()
            if st_present is None:
                bad.append("срез с SKILL_DIR=temp(файл скопирован) не удался: %s" % err_present)
            else:
                got_ok = st_present("живой-разбор\ndead-language: чисто\nВЕРДИКТ: PASS\n")
                if got_ok != "OK":
                    bad.append("контроль: файл присутствует, «чисто» -> ждали OK, "
                               "получили %s" % got_ok)
        else:
            bad.append("файл %s не найден - справочник раздаётся со скиллом, "
                       "контрольная половина теста (файл присутствует) не прогнана"
                       % zhivoy_ref_md)
        shutil.rmtree(td, ignore_errors=True)
    finally:
        if old_skill_dir is None:
            os.environ.pop("SKILL_DIR", None)
        else:
            os.environ["SKILL_DIR"] = old_skill_dir

    record("Д119: справочник живого языка недоступен -> NOSIG (hard-block), "
           "зеркало Д105 (донор-приёмы)", not bad, "; ".join(bad))


# (имя, ПОЛНЫЙ текст ответа верификатора, ожидаемое состояние `_deadlang_state`)
# - Д133/Д134 (скептик-раунд 45, по решению автора) требуют многострочный/составной
# текст (mid-line отказ на ДРУГОЙ строке, компактная пара через `·`, цитата
# в бэктиках) - не влезает в шаблон-подстановку одного значения
# `"dead-language: %s"`, поэтому отдельный список полных текстов, зеркало
# `_DEADLANG_MARKDOWN_LABEL_CASES` выше.
_DEADLANG_D133_D134_CASES = [
    # --- Д133а: fail-open - честная строка + отказ СЕРЕДИНОЙ строки прозой ---
    ("Д133а fail-open: dead-language честная строка + отказ прозой mid-line",
     "dead-language: чисто\n"
     "Примечание: dead-language: не проверял, соврал строкой выше\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д133б: ложный MISSING - обе строки ОДНОЙ строкой через · ---
    ("Д133б компактная однострочная пара donor-devices · dead-language "
     "(легальная форма 04-review.md 4.M.2) - dead-language честно найден",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS · "
     "dead-language: чисто\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д134: цитата канона в бэктиках не закрывает мандат присутствия ---
    ("Д134 цитата dead-language в бэктиках (пример из инструкции) с OK - "
     "мандат MISSING, других вхождений нет",
     "Пример из инструкции: `dead-language: чисто`\nВЕРДИКТ: PASS\n",
     "MISSING"),
    ("Д134 цитата dead-language в бэктиках с ОТКАЗОМ - продолжает "
     "блокировать (Д126 fail-closed держится и здесь)",
     "Пример отказа из инструкции: `dead-language: не проверял`\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д134: компактный отчёт БЕЗ бэктиков - легален (существо соблюдено) ---
    ("Д134 компактный отчёт без бэктиков - легальный OK",
     "Чек-лист вывода: dead-language: чисто.\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д134: смесь - цитата в бэктиках + честный отчёт НИЖЕ ---
    ("Д134 смесь: цитата в бэктиках + честный отчёт НИЖЕ - мандат закрыт "
     "честной строкой, не цитатой",
     "Как говорит канон: `dead-language: чисто`\n"
     "dead-language: чисто\nВЕРДИКТ: PASS\n", "OK"),
]


def test_hook_deadlang_d133_d134():
    """🔴 Д133+Д134 (скептик-раунд 45, по решению автора).

    Д133 - `_DEADLANG_RE` держала `^`-якорь (Д129/R44 снял его ТОЛЬКО у
    `_READFLAG_RE`) - две зеркальные аварии: (а) честная строка где-то в
    ответе + отказ, напечатанный СЕРЕДИНОЙ строки прозой («Примечание:
    dead-language: не проверял…») - «худшее побеждает» в `_deadlang_state`
    не видел отказ ВООБЩЕ (`finditer` его не находил), честная строка
    побеждала единолично; (б) компактная однострочная форма «donor-devices:
    … -> PASS · dead-language: чисто» (легальная по 04-review.md 4.M.2,
    тот же стиль, что канонная форма READFLAG «donordev_read: PASS ·
    zhivoy_yazyk_read: PASS») - «dead-language:» стоит ПОСЛЕ разделителя
    `·`, не с начала строки, `^`-якорь его не находил -> ложный
    `DEADLANG_MISSING` на честном отчёте. Фикс снял якорь и ограничил
    значение lookahead'ом до следующего известного ключа/EOL - зеркало
    Д129 (R44).

    Д134 - ответ, ЦИТИРУЮЩИЙ канон дословно в бэктиках («Пример из
    инструкции: `dead-language: чисто`»), матчился ТЕМ ЖЕ regex'ом, что и
    настоящий отчёт - мандат присутствия закрывался ЦИТАТОЙ, а не
    решением верификатора. Фикс - `_in_backticks`: бэктик-вхождение с
    ХОРОШИМ состоянием (OK/«чисто») не удовлетворяет мандат присутствия
    (остаётся MISSING, если других вхождений нет), но с ПЛОХИМ состоянием
    (NO/LITERAL/NOPAIRS/NOSIG) ПРОДОЛЖАЕТ блокировать - fail-closed в
    сторону признания-отказа не ослаблен (Д126 не откатывается)."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д133+Д134 хук: dead-language mid-line/компактная пара/бэктик-цитата",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д133+Д134 хук: dead-language mid-line/компактная пара/бэктик-цитата",
               False, err)
        return
    bad = []
    for name, text, want in _DEADLANG_D133_D134_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д133+Д134 хук: dead-language mid-line/компактная пара/бэктик-цитата "
           "(%d кейсов)" % len(_DEADLANG_D133_D134_CASES), not bad, "; ".join(bad))


# (имя, ПОЛНЫЙ текст ответа верификатора, ожидаемое состояние `_deadlang_state`)
# - Д135/Д136 (скептик-раунд 46, по решению автора). Д135: `_in_backticks` щупал
# позицию КЛЮЧА матча, не ЗНАЧЕНИЯ - зеркала у dead-language нет (регекс не
# несёт `` `? `` тolerance вокруг СВОЕГО ключа, как READFLAG после Д126), но
# фикс применён и сюда для консистентности (позиция значения = семантически
# верный признак цитаты, а не позиции ключа). Д136: mid-line УПОМИНАНИЕ имени
# поля прозой («Итог по строке dead-language: смотри выше.», дословные куски
# `04-review.md:1005`) больше не топит соседний честный отчёт - см. полное
# обоснование в комментарии перед `_at_line_start` в хуке.
_DEADLANG_D135_D136_CASES = [
    # --- Д136: mid-line упоминание ПОСЛЕ честного отчёта (H3-класс) ---
    ("Д136 H3 mid-line упоминание «Итог по строке dead-language: смотри "
     "выше.» ПОСЛЕ честного отчёта - упоминание, не отчёт",
     "dead-language: чисто\nВЕРДИКТ: PASS\n"
     "Итог по строке dead-language: смотри выше.\n", "OK"),
    # --- Д136: mid-line упоминание В КОНЦЕ ответа (H7-класс) ---
    ("Д136 H7 mid-line упоминание в конце ответа «строку я напечатал "
     "первой попыткой.» - упоминание, не отчёт",
     "dead-language: чисто\nВЕРДИКТ: PASS\n"
     "Отдельно отмечу: dead-language: строку я напечатал первой попыткой.\n",
     "OK"),
    # --- Д136: дословная фраза промпта 04-review.md:1005 (J2-класс) ---
    ("Д136 J2 дословная фраза промпта про dead-language + честный отчёт - "
     "пересказ канона не блокирует",
     "Строка `dead-language:` обязана быть: прогони текст поста против "
     "антисловаря разд.3 и напечатай либо `dead-language: чисто`, либо "
     "`dead-language: N слов заменено`.\n"
     "dead-language: чисто\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д136 контроль (Д133 держится): mid-line ЯВНЫЙ отказ ПРОДОЛЖАЕТ NO ---
    ("Д136 контроль Д133: mid-line ЯВНЫЙ отказ прозой продолжает NO "
     "(явная форма - не упоминание)",
     "dead-language: чисто\n"
     "Примечание: dead-language: не проверял, соврал строкой выше\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д136 контроль: line-start ГАРБАЖ держит полную строгость (NO) ---
    ("Д136 контроль line-start: garbage С НАЧАЛА строки остаётся NO "
     "(позиционный фильтр строгость с начала строки не снимает)",
     "dead-language: какая-то отговорка без чисто и без числа\n"
     "ВЕРДИКТ: PASS\n", "NO"),
]


def test_hook_deadlang_d135_d136():
    """🔴 Д135+Д136 (скептик-раунд 46, по решению автора) - зеркало
    `test_hook_deadlang_d133_d134` выше, тот же приём (вырез живой функции,
    прогон по полным текстам ответа).

    Д135 - `_in_backticks(answer, m.start())` щупал позицию НАЧАЛА МАТЧА
    (ключ), а не позицию ЗНАЧЕНИЯ - фикс: `m.start(1)` (единственная группа
    значения что у колон-, что у pipe-табличной формы). У dead-language
    своего ключа регекс не несёт `` `? `` tolerance (в отличие от READFLAG
    после Д126), поэтому наблюдаемого поведенческого отличия здесь нет -
    фикс применён для консистентности позиции, не для наблюдаемого дефекта
    (см. `_DONORDEV_D135_D136_CASES`/докстринг `test_hook_donordev_d135_
    d136` про READFLAG, где эффект наблюдаем).

    Д136 - mid-line УПОМИНАНИЕ имени поля прозой («Ниже строка dead-
    language: смотри выше.», дословные куски `04-review.md:1005`) давало
    `_deadlang_state_one` НЕРАСПОЗНАННОЕ значение, которое падает в
    структурный fallback `return "NO"` последней строкой функции - «худшее
    побеждает» клало этим гарбажем ЧЕСТНУЮ строку, напечатанную где-то ещё
    в ответе. Фикс - `_deadlang_looks_explicit` + `_at_line_start`: mid-line
    вхождение засчитывается, ТОЛЬКО если значение распознано явной формой
    (явный отказ ИЛИ структурное «чисто…»/«N замен…»); line-start сохраняет
    полную строгость без изменений (последний кейс списка - контроль)."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д135+Д136 хук: dead-language mid-line упоминание vs отчёт",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д135+Д136 хук: dead-language mid-line упоминание vs отчёт",
               False, err)
        return
    bad = []
    for name, text, want in _DEADLANG_D135_D136_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д135+Д136 хук: dead-language mid-line упоминание vs отчёт "
           "(%d кейсов)" % len(_DEADLANG_D135_D136_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д137+Д138 (скептик-раунд 47, по решению автора), ВЕТКА dead-language.
# Д137: `_DEADLANG_RE` не несла `` `? `` вокруг СВОЕГО ключа (Д135, раунд 46,
# сама констатировала эту асимметрию текстом и чинила только позицию
# `_in_backticks`, не саму нехватку `` `? ``) - форма «`dead-language`:
# чисто» (типографика канона у READFLAG-ключей) не матчилась вовсе,
# `_deadlang_state` читал честную строку как `MISSING`. Д138: mid-line-
# фильтр (`_deadlang_looks_explicit`, Д136) зовёт ТЕ ЖЕ словари, что line-
# start, но словари не несли корень «свер…» - «не сверял» не матчил НИ ОДИН
# слой отказа, mid-line-вхождение читалось нераспознанным гарбажем и
# пропускалось целиком, честный отчёт рядом единолично давал `OK`. Полное
# обоснование обоих классов - шапки `_DEADLANG_RE`/`_DEADLANG_NO_START_RE` в
# самом хуке.
# ---------------------------------------------------------------------------
_DEADLANG_D137_D138_CASES = [
    # --- Д137: ключ в бэктиках, значение снаружи ---
    ("Д137 ключ в бэктиках, значение снаружи - `dead-language`: чисто",
     "`dead-language`: чисто\nВЕРДИКТ: PASS\n", "OK"),
    ("Д137 буллет + бэктик-ключ, значение снаружи",
     "- `dead-language`: чисто\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д137 регресс Д134: ключ+значение ОДНОЙ парой бэктиков - цитата ---
    ("Д137 регресс Д134: ключ+значение ОДНОЙ парой бэктиков - цитата, "
     "MISSING (не закрывается бэктик-ключом)",
     "`dead-language: чисто`\nВЕРДИКТ: PASS\n", "MISSING"),
    # --- Д137 регресс: бэктик-ключ + явный отказ продолжает блокировать ---
    ("Д137 регресс: бэктик-ключ + явный отказ «не проверял» продолжает NO",
     "`dead-language`: не проверял\nВЕРДИКТ: PASS\n", "NO"),
    # --- Д138: mid-line признание «не сверял» рядом с честным отчётом ---
    ("Д138 mid-line признание «не сверял» рядом с честным отчётом - "
     "блокирует (явная форма, не упоминание)",
     "dead-language: чисто\n"
     "Примечание: dead-language: не сверял антисловарь\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д138 line-start регресс: «не сверял» продолжает NO ---
    ("Д138 line-start регресс: «не сверял» остаётся NO (теперь и явным "
     "словарём, не только catch-all'ом)",
     "dead-language: не сверял\nВЕРДИКТ: PASS\n", "NO"),
]


def test_hook_deadlang_d137_d138():
    """🔴 Д137+Д138 (скептик-раунд 47, по решению автора) - зеркало
    `test_hook_deadlang_d135_d136` выше, тот же приём (вырез живой функции,
    прогон по полным текстам ответа).

    Д137 - `_DEADLANG_RE` не несла опциональный бэктик `` `? `` вокруг
    СВОЕГО ключа (в отличие от `_READFLAG_RE`/`_DEADLANG_TABLE_RE`) - форма
    «`dead-language`: чисто» не матчилась вовсе, честная строка читалась
    `MISSING`. Фикс - `` `? `` СРАЗУ за литералом ключа, та же позиция, что
    несёт `_READFLAG_RE`.

    Д138 - словари отказа `_DEADLANG_NO_START_RE`/`_DEADLANG_NO_PHRASE_RE`
    не несли корень «свер…» - «не сверял» не матчил mid-line-фильтр Д136
    (тот же словарь, что и line-start, копии нет), гарбаж пропускался,
    честный отчёт рядом единолично давал `OK`. Фикс - корень добавлен в ОБА
    словаря."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д137+Д138 хук: dead-language бэктик-ключ + mid-line словарь",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д137+Д138 хук: dead-language бэктик-ключ + mid-line словарь",
               False, err)
        return
    bad = []
    for name, text, want in _DEADLANG_D137_D138_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д137+Д138 хук: dead-language бэктик-ключ + mid-line словарь "
           "(%d кейсов)" % len(_DEADLANG_D137_D138_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д139+Д140 (скептик-раунд 48, по решению автора), ВЕТКА dead-language - зеркало
# `_DONORDEV_D139_D140_CASES` у соседнего гейта (полное обоснование обоих
# классов - шапка перед ним, шапки `_at_line_start`/`_DEADLANG_RE` в самом
# хуке).
# ---------------------------------------------------------------------------
_DEADLANG_D139_D140_CASES = [
    # --- Д139: LITERAL/отказ ВНЕ словаря бэктик-ключом НА СВОЕЙ СТРОКЕ
    # рядом с честным отчётом - блок как у голого (было OK, fail-open) ---
    ("Д139 LITERAL бэктик-ключом на своей строке рядом с честной строкой - "
     "блок держится (было OK, fail-open)",
     "`dead-language`: 3 слов заменено · «<мёртвое>» -> «<живая замена>»\n"
     "dead-language: чисто\nВЕРДИКТ: PASS\n", "LITERAL"),
    ("Д139 отказ ВНЕ словаря «пропустил» бэктик-ключом на своей строке - "
     "блок держится (было OK, fail-open)",
     "`dead-language`: пропустил этот шаг\ndead-language: чисто\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д139 регресс: бэктик-ключ + явный отказ словарём продолжает NO ---
    ("Д139 регресс: бэктик-ключ + явный отказ «не сверял» продолжает NO",
     "`dead-language`: не сверял\ndead-language: чисто\nВЕРДИКТ: PASS\n",
     "NO"),
    # --- Д140: markdown-подчёркивание вокруг ключа - честный отчёт матчится ---
    ("Д140 __подчёркивание__ (жирный markdown, CommonMark) - честный отчёт "
     "матчится (было MISSING, fail-closed)",
     "__dead-language__: чисто\nВЕРДИКТ: PASS\n", "OK"),
]


def test_hook_deadlang_d139_d140():
    """🔴 Д139+Д140 (скептик-раунд 48, по решению автора) - зеркало
    `test_hook_donordev_d139_d140` выше, тот же приём (вырез живой функции,
    прогон по полным текстам ответа). Оба класса и обоснование - её
    докстринг целиком, здесь не повторяется."""
    st, err = _hook_deadlang_state()
    if err == "NOHOOK":
        skip("Д139+Д140 хук: dead-language бэктик-line-start + подчёркивание",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д139+Д140 хук: dead-language бэктик-line-start + подчёркивание",
               False, err)
        return
    bad = []
    for name, text, want in _DEADLANG_D139_D140_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д139+Д140 хук: dead-language бэктик-line-start + подчёркивание "
           "(%d кейсов)" % len(_DEADLANG_D139_D140_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д51 (скептик-раунд 12, по решению автора): ШАПКА СПРАВОЧНИКА СЛАЛА НА НЕВЕРНЫЕ §.
# Шапка `references/donor-copy-devices.md` перечисляла приёмы-механики как
# «§5 панорама чужих кейсов и опись, §6 снятие возражения», хотя по факту §5 это
# CTA И ПЕРЕДАЧА, панорама чужих кейсов - §3.4, снятие возражения - §1.4 и §2.6,
# а §6 это наблюдения третьего донора. Верификатор, взявший номер раздела ИЗ ШАПКИ,
# печатал в строку `donor-devices:` ссылку на §6 и ловил `DONORDEV_NOREF` - блок по
# подсказке самого раздаваемого справочника. Шапка приведена к факту, а тест ниже
# привязывает ДИАПАЗОН РЕГЕКСА ХУКА к содержимому файла: подписи приёмов обязаны
# жить в §1-§5, и живой `_DONORDEV_REF_RE` обязан покрывать каждую из них.
# ---------------------------------------------------------------------------

SKILL_ROOT = os.path.dirname(SCRIPTS)
DONORDEV_REF_MD = os.path.join(SKILL_ROOT, "references", "donor-copy-devices.md")
_SIGNATURE_RE = re.compile(r"^\*\*§(\d+)(?:\.(\d+))?")
_SIGNATURE_NAME_RE = re.compile(r"^\*\*§(\d+\.\d+)\s+(.+?)\*\*")


def test_donordev_reference_sections():
    """Д51: подписи приёмов справочника живут в §1-§5 И покрыты регексом хука.
    Д56 (скептик-раунд 14): шапка (строки до первого `## `) называет приёмы
    парой «§N.M + название» СВОИМИ словами вместо подписи из тела - после Д53
    название нагружено (сверяется верификатором), несовпадение шапки с подписью
    - мина ложного блока. Каждая пара «§N.M» в шапке обязана нести ДОСЛОВНУЮ
    подпись этого § (проверка - подпись целиком встречается в тексте перед
    самим §N.M в шапке).

    Отсутствие файла = FAIL, не skip: `references/donor-copy-devices.md` раздаётся
    ВМЕСТЕ со скиллом и читается HARD-ридом в `02d`/`01-router` E1/`01d-rewrite`
    Шаг 2.5/`04-review` 4.M.2 - если его нет, сломан пакет, а не «нет входных данных
    владельца». Skip остаётся ровно на отсутствие ХУКА (машина ученика без хука):
    тогда половина про регекс не проверяется, а диапазон подписей и шапка - проверяются."""
    if not os.path.isfile(DONORDEV_REF_MD):
        record("Д51/Д56 справочник: подписи приёмов живут в §1-§5, покрыты регексом хука, "
               "шапка дословна подписям",
               False, "файла %s нет - справочник раздаётся со скиллом, "
                      "его отсутствие = поломка пакета" % DONORDEV_REF_MD)
        return
    sigs = []
    names_by_tag = {}
    with open(DONORDEV_REF_MD, encoding="utf-8") as f:
        lines = f.readlines()
    for n, line in enumerate(lines, 1):
        m = _SIGNATURE_RE.match(line)
        if m:
            sigs.append((n, "§" + m.group(1) + ("." + m.group(2) if m.group(2) else ""),
                         int(m.group(1))))
        mn = _SIGNATURE_NAME_RE.match(line)
        if mn:
            names_by_tag[mn.group(1)] = mn.group(2)
    header_lines = []
    for line in lines:
        if line.startswith("## "):
            break
        header_lines.append(line)
    header = "".join(header_lines)
    problems = []
    if not sigs:
        problems.append("в справочнике НЕТ НИ ОДНОЙ подписи вида `**§N.M` - "
                        "формат подписей сменили? (Д35 требует § в подписи)")
    out_of_range = [f"{tag} (стр. {n})" for n, tag, major in sigs if not 1 <= major <= 5]
    if out_of_range:
        problems.append("подписи вне разделов 1-5: " + ", ".join(out_of_range)
                        + " - либо приём переехал в §6-§8 (наблюдения/сигнатуры/"
                          "анти-приёмы), либо надо расширять диапазон в ХУКЕ")
    ns, err = _hook_donordev_ns()
    if err == "NOHOOK":
        print("       (регекс-половина не проверена: хука нет на этой машине)")
    elif ns is None:
        problems.append("живой регекс не вырезан из хука: " + err)
    else:
        ref_re = ns.get("_DONORDEV_REF_RE")
        if ref_re is None:
            problems.append("в вырезанном куске хука нет имени _DONORDEV_REF_RE - "
                            "переименовали? страж диапазона обезоружен")
        else:
            uncovered = [f"{tag} (стр. {n})" for n, tag, _ in sigs if not ref_re.search(tag)]
            if uncovered:
                problems.append("регекс хука НЕ покрывает подписи справочника: "
                                + ", ".join(uncovered)
                                + " - верификатор, скопировавший подпись дословно, "
                                  "получит ложный DONORDEV_NOREF")
    name_mismatches = []
    for m in re.finditer(r"§(\d+\.\d+)", header):
        tag = m.group(1)
        name = names_by_tag.get(tag)
        if not name:
            continue
        window = header[max(0, m.start() - 80):m.start()].lower()
        if name.lower() not in window:
            name_mismatches.append(f"§{tag} '{name}'")
    if name_mismatches:
        problems.append("Д56: шапка называет приём НЕ дословной подписью §: "
                        + ", ".join(name_mismatches))
    record("Д51/Д56 справочник: подписи приёмов живут в §1-§5, покрыты регексом хука, "
           f"шапка дословна подписям ({len(sigs)} подписей)",
           not problems, " · ".join(problems))


# ---------------------------------------------------------------------------
# 🔴 Д103 (скептик-раунд 36, по решению автора): СТРАЖ-НАПРАВЛЕНИЕ, ОБРАТНОЕ Д51.
# Д51 выше проверяет «каждая РЕАЛЬНАЯ подпись справочника ПРОХОДИТ регекс хука»
# (иначе честный отчёт со скопированной дословно подписью ловил бы ложный NOREF).
# Это ЗЕРКАЛЬНАЯ, ранее непроверенная сторона того же контракта: «каждое число,
# которое РЕГЕКС+ФАЙЛ хука ЗАСЧИТЫВАЮТ как OK, РЕАЛЬНО существует подписью в
# справочнике» - без неё регекс мог принимать (и принимал, Д103) номера ШИРЕ
# множества подписей: `.\d` берёт любую цифру 0-9, а подписей всего 23.
# Гоняет ЖИВУЮ `_donordev_state` (тот же вырез хука, что у Д45/Д51) на ВСЕХ
# 23 реальных подписях справочника (ждём OK на каждой - страж НЕ должен резать
# легальные ссылки) и на 3 выдуманных подномерах (ждём NOREF - страж НЕ должен
# засчитывать подделку). Число 23 в тексте FAIL - для читателя, не источник
# истины: источник истины - живой файл, прочитанный этим же тестом.
# ---------------------------------------------------------------------------

def test_donordev_signature_guard():
    """Д103: страж-направление, обратное Д51 - принимаемое регексом ОБЯЗАНО
    существовать в справочнике.

    Контракт `(функция, причина)` от `_hook_donordev_state()` тот же, что у
    Д45/Д51: `NOHOOK` = skip (машина ученика без хука), любая другая причина
    выреза = FAIL. Отсутствие `references/donor-copy-devices.md` - тоже FAIL,
    не skip: файл раздаётся ВМЕСТЕ со скиллом (тот же принцип, что у Д51/Д56
    выше), и без него сверить регекс с подписями нечем."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д103 страж-направление: подписи справочника <-> регекс+файл хука",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д103 страж-направление: подписи справочника <-> регекс+файл хука",
               False, err)
        return
    if not os.path.isfile(DONORDEV_REF_MD):
        record("Д103 страж-направление: подписи справочника <-> регекс+файл хука",
               False, "файла %s нет - справочник раздаётся со скиллом, "
                      "его отсутствие = поломка пакета" % DONORDEV_REF_MD)
        return
    # 🔴 `_SIGNATURE_RE` (не `_SIGNATURE_NAME_RE`) - тот же экстрактор, что даёт
    # список `sigs` у Д51 выше. `_SIGNATURE_NAME_RE` требует ИМЯ приёма перед
    # закрывающим `**` и не матчит СОСТАВНОЙ заголовок «§2.7-2.9 Три приёма
    # Донор-Б» (там имя не сразу после номера) - даёт 22 вместо 23, ложно
    # исключая §2.7. Хук читает файл ТЕМ ЖЕ простым паттерном `^\*\*§(\d+\.\d+)`
    # (см. `_DONORDEV_SIG_RE` в хуке) - он берёт «2.7» из составного заголовка,
    # ровно как этот тест; расхождение экстракторов дало бы ложный FAIL здесь
    # на честном хуке.
    with open(DONORDEV_REF_MD, encoding="utf-8") as f:
        real_sigs = sorted(set(m.group(1) + ("." + m.group(2) if m.group(2) else "")
                    for m in (_SIGNATURE_RE.match(ln) for ln in f) if m))
    bad = []
    if len(real_sigs) != 23:
        bad.append("в справочнике %d подписей, ждали 23 (§1.1-1.4, §2.1-2.7, "
                   "§3.1-3.4, §4.1-4.4, §5.1-5.4) - число сверки устарело "
                   "или справочник менялся" % len(real_sigs))
    for tag in real_sigs:
        ans = ("донор-разбор\ndonor-devices: §%s название приёма «цитата из "
               "поста» -> PASS\nВЕРДИКТ: PASS\n" % tag)
        got = st(ans)
        if got != "OK":
            bad.append("§%s (реальная подпись справочника) -> ждали OK, "
                       "получили %s" % (tag, got))
    for fake in ("3.9", "2.8", "2.0"):
        ans = ("донор-разбор\ndonor-devices: §%s воображаемый приём «цитата "
               "из поста» -> PASS\nВЕРДИКТ: PASS\n" % fake)
        got = st(ans)
        if got != "NOREF":
            bad.append("§%s (выдуманный подномер, формат верный) -> ждали "
                       "NOREF, получили %s" % (fake, got))
        ans2 = ("донор-разбор\ndonor-devices: %s воображаемый приём «цитата "
                "из поста» -> PASS\nВЕРДИКТ: PASS\n" % fake)
        got2 = st(ans2)
        if got2 != "NOREF":
            bad.append("голый %s (выдуманный, без §) -> ждали NOREF, "
                       "получили %s" % (fake, got2))
    record("Д103 страж-направление: %d подписей справочника дают OK, "
           "3 выдуманных подномера (§ и голых) дают NOREF" % len(real_sigs),
           not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д105 (скептик-раунд 37, по решению автора): НАПРАВЛЕНИЕ МЯГКОЙ ДЕГРАДАЦИИ ДОНОР-
# СПРАВОЧНИКА БЫЛО ПЕРЕВЁРНУТО ПРОТИВ КАНОНА.
# Д103 (раунд 36) ввёл контракт «файл справочника недоступен -> сверка по
# подписям тихо пропускается, решает только регекс формата, гейт не падает» -
# по аналогии с `load_etalons()` в `bench-post.py`. Аналогия ложная:
# `references/donor-copy-devices.md` не персональный корпус донора (как
# `etalons.json`, который ученик правомерно подставляет своим набором - там
# отсутствие штатно), а справочник приёмов, обязательная часть самого
# механизма гейта, раздаётся ВМЕСТЕ со скиллом. Канон прямо называет его
# отсутствие поломкой пакета, а не штатной деградацией -
# `workflow/04-review.md:912` («файл раздаётся вместе со скиллом, поэтому его
# отсутствие - не штатная деградация, а поломка пакета») и
# `workflow/05-publish.md:26` (поле `donordev_read` держит `PASS`, `N/A` по
# этому полю нелегален). Плюс диагностика деградации шла ТОЛЬКО в stderr
# python-блока, который хук сам же удаляет непрочитанным (`trap 'rm -rf
# "$_gate_tmp"' EXIT`) до того, как кто-либо мог его увидеть - поломка пакета
# проходила ПОЛНОСТЬЮ БЕЗ СЛЕДА.
# ФИКС: направление перевёрнуто. Файл недоступен -> новое терминальное
# состояние `NOSIG` -> отдельная bash-ветка `case` -> `exit 2` с BLOCK-текстом.
# Тест держит ОБЕ стороны контракта РАЗДЕЛЬНО, чтобы следующая правка не
# перепутала «файла нет» (Д105, `NOSIG`, hard-block) с «файл есть, но ссылка
# выдумана» (Д103, `NOREF`, страж выше `test_donordev_signature_guard` этот
# тест не трогает).
# ---------------------------------------------------------------------------

def test_donordev_missing_reference_is_hard_fail():
    """Д105: файл справочника недоступен -> `NOSIG` (hard-block), НЕ мягкий
    регекс-only `OK`.

    `_hook_donordev_ns()`/`_hook_donordev_state()` исполняют вырезанный кусок
    хука ЗАНОВО при каждом вызове (см. их докстринги) - путь справочника
    внутри куска читает `os.environ.get("SKILL_DIR")` на момент exec, поэтому
    смена `SKILL_DIR` МЕЖДУ вызовами реально меняет поведение свежего среза.
    Проверка в два шага: (1) `SKILL_DIR` указывает на временный каталог БЕЗ
    файла справочника - ЛЮБАЯ формально верная §N.M-ссылка (реальная подпись
    ИЛИ выдуманный подномер - без файла отличить их нечем) обязана дать
    `NOSIG`, а не `OK`; (2) контроль - тот же каталог, но с КОПИЕЙ живого
    справочника внутри, тот же вопрос снова даёт штатные `OK`/`NOREF` (Д103
    не задет этим тестом)."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д105: файл справочника недоступен -> NOSIG (hard-block)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д105: файл справочника недоступен -> NOSIG (hard-block)",
               False, err)
        return
    old_skill_dir = os.environ.get("SKILL_DIR")
    bad = []
    try:
        td = tempfile.mkdtemp(prefix="d105-nosig-")
        os.makedirs(os.path.join(td, "references"), exist_ok=True)
        # references/donor-copy-devices.md НАМЕРЕННО отсутствует - поломка пакета.
        os.environ["SKILL_DIR"] = td
        st_missing, err_missing = _hook_donordev_state()
        if st_missing is None:
            bad.append("срез с SKILL_DIR=temp(без файла) не удался: %s" % err_missing)
        else:
            for name, val in (
                ("реальная по формату §2.3",
                 "§2.3 смена системы отсчёта «цитата из поста» -> PASS"),
                ("выдуманная §3.9",
                 "§3.9 воображаемый приём «цитата из поста» -> PASS"),
            ):
                got = st_missing("донор-разбор\ndonor-devices: %s\nВЕРДИКТ: PASS\n" % val)
                if got != "NOSIG":
                    bad.append("без файла справочника, %s -> ждали NOSIG, получили %s "
                               "(мягкая деградация ещё жива - Д105 не применён/сломан)"
                               % (name, got))

        if os.path.isfile(DONORDEV_REF_MD):
            shutil.copy(DONORDEV_REF_MD,
                        os.path.join(td, "references", "donor-copy-devices.md"))
            st_present, err_present = _hook_donordev_state()
            if st_present is None:
                bad.append("срез с SKILL_DIR=temp(файл скопирован) не удался: %s" % err_present)
            else:
                got_ok = st_present("донор-разбор\ndonor-devices: §2.3 смена системы "
                                     "отсчёта «цитата из поста» -> PASS\nВЕРДИКТ: PASS\n")
                if got_ok != "OK":
                    bad.append("контроль: файл присутствует, §2.3 -> ждали OK, получили %s"
                               % got_ok)
                got_noref = st_present("донор-разбор\ndonor-devices: §3.9 воображаемый "
                                        "приём «цитата из поста» -> PASS\nВЕРДИКТ: PASS\n")
                if got_noref != "NOREF":
                    bad.append("контроль (Д103 регресс): файл присутствует, §3.9 -> "
                               "ждали NOREF, получили %s" % got_noref)
        else:
            bad.append("файл %s не найден - справочник раздаётся со скиллом, "
                       "контрольная половина теста (файл присутствует) не прогнана"
                       % DONORDEV_REF_MD)
        shutil.rmtree(td, ignore_errors=True)
    finally:
        if old_skill_dir is None:
            os.environ.pop("SKILL_DIR", None)
        else:
            os.environ["SKILL_DIR"] = old_skill_dir

    record("Д105: файл справочника недоступен -> NOSIG (hard-block), "
           "не молчаливый регекс-only OK (направление Д103 перевёрнуто)",
           not bad, "; ".join(bad))


# (имя, ПОЛНЫЙ текст ответа верификатора, ожидаемое состояние `_donordev_state`)
# - Д133/Д134 (скептик-раунд 45, по решению автора), зеркало
# `_DEADLANG_D133_D134_CASES` выше - многострочный/составной текст не влезает
# в шаблон-подстановку одного значения `"donor-devices: %s"`.
_DONORDEV_D133_D134_CASES = [
    # --- Д133а: fail-open - честная строка + отказ СЕРЕДИНОЙ строки прозой ---
    ("Д133а fail-open: donor-devices честная строка + отказ прозой mid-line",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "Примечание: donor-devices: нет, приём на самом деле не нашёл\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д133б: компактная однострочная пара - donor-devices половина ---
    ("Д133б компактная однострочная пара donor-devices · dead-language - "
     "donor-devices половина честна как и до фикса (позитивный регресс-"
     "контроль, donor-devices сам стоит с начала строки)",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS · "
     "dead-language: чисто\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д133 регресс: прозА БЕЗ двоеточия по-прежнему не над-триггерит ---
    ("Д133 регресс: упоминание «donor-devices» БЕЗ двоеточия - MISSING как раньше",
     "Верификатор всё проверил, donor-devices смотрел, приём есть.\n"
     "ВЕРДИКТ: PASS\n", "MISSING"),
    # --- Д134: цитата канона в бэктиках не закрывает мандат присутствия ---
    ("Д134 цитата donor-devices в бэктиках (пример из инструкции) с OK - "
     "мандат MISSING, других вхождений нет",
     "Инструкция цитирует пример: `donor-devices: §2.3 приём «цитата» "
     "-> PASS`\nВЕРДИКТ: PASS\n", "MISSING"),
    ("Д134 цитата donor-devices в бэктиках с ОТКАЗОМ - продолжает "
     "блокировать (Д126 fail-closed держится и здесь)",
     "Инструкция цитирует пример отказа: `donor-devices: нет`\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д134: компактный отчёт БЕЗ бэктиков - легален (существо соблюдено) ---
    ("Д134 компактный отчёт без бэктиков - легальный OK",
     "Чек-лист вывода: donor-devices: §2.3 смена системы отсчёта «цитата» "
     "-> PASS.\nВЕРДИКТ: PASS\n", "OK"),
    # --- Д134: смесь - цитата в бэктиках + честный отчёт НИЖЕ ---
    ("Д134 смесь: цитата в бэктиках + честный отчёт НИЖЕ - мандат закрыт "
     "честной строкой, не цитатой",
     "Цитата: `donor-devices: §2.3 приём «пример» -> PASS`\n"
     "donor-devices: §2.3 смена системы отсчёта «реальная цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
]


def test_hook_donordev_d133_d134():
    """🔴 Д133+Д134 (скептик-раунд 45, по решению автора) - зеркало
    `test_hook_deadlang_d133_d134` у соседнего гейта dead-language,
    полное обоснование класса дефекта - её докстринг.

    Д133 - `_DONORDEV_RE` держала `^`-якорь: (а) отказ, напечатанный
    СЕРЕДИНОЙ строки прозой, был невидим finditer'у (fail-open, честная
    строка выше побеждала единолично); (б) компактная однострочная форма
    «donor-devices: … -> PASS · dead-language: чисто» - donor-devices
    половина стоит С НАЧАЛА строки и матчилась и ДО фикса (позитивный
    регресс-контроль в списке ниже), а вот СОСЕДНЯЯ dead-language половина
    ловила ложный MISSING (см. `_DEADLANG_D133_D134_CASES`). Фикс снял
    якорь и ограничил значение lookahead'ом до следующего известного
    ключа/EOL.

    Д134 - цитата канона в бэктиках («Инструкция цитирует пример:
    `donor-devices: §2.3 … -> PASS`») матчилась ТЕМ ЖЕ regex'ом, что и
    настоящий отчёт - мандат присутствия закрывался цитатой. Фикс -
    `_in_backticks`: бэктик-вхождение с OK не удовлетворяет присутствие
    (MISSING, если других вхождений нет), с ПЛОХИМ состоянием (NO/LITERAL/
    NOREF/NOSIG) ПРОДОЛЖАЕТ блокировать (Д126 fail-closed не откатывается)."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д133+Д134 хук: donor-devices mid-line/компактная пара/бэктик-цитата",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д133+Д134 хук: donor-devices mid-line/компактная пара/бэктик-цитата",
               False, err)
        return
    bad = []
    for name, text, want in _DONORDEV_D133_D134_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д133+Д134 хук: donor-devices mid-line/компактная пара/бэктик-цитата "
           "(%d кейсов)" % len(_DONORDEV_D133_D134_CASES), not bad, "; ".join(bad))


# (имя, ПОЛНЫЙ текст ответа верификатора, ожидаемое состояние `_donordev_state`)
# - Д135/Д136 (скептик-раунд 46, по решению автора), зеркало `_DEADLANG_D135_D136_
# CASES` выше. Д135 у donor-devices/dead-language - см. её докстринг в
# `test_hook_deadlang_d135_d136`: фикс применён для консистентности позиции,
# наблюдаемый эффект живёт у READFLAG (`READFLAG_CASES`, кейсы «Д135» ниже) -
# донор-девайсов регекс не несёт `` `? `` tolerance вокруг СВОЕГО ключа.
_DONORDEV_D135_D136_CASES = [
    # --- Д136: mid-line упоминание СЕРЕДИНОЙ ответа (H1-класс) ---
    ("Д136 H1 mid-line упоминание «Ниже строка donor-devices: с приёмом и "
     "уликой.» ПЕРЕД честным отчётом - упоминание, не отчёт",
     "Ниже строка donor-devices: с приёмом и уликой.\n"
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    # --- Д136: mid-line упоминание заголовком раздела (H5-класс) ---
    ("Д136 H5 mid-line упоминание «## Блок donor-devices: разбор» - "
     "заголовок, не отчёт",
     "## Блок donor-devices: разбор\n"
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    # --- Д136: дословная фраза промпта 04-review.md:1005 (J1-класс) ---
    ("Д136 J1 дословная фраза промпта про donor-devices + честный отчёт - "
     "пересказ канона не блокирует",
     "Строка `donor-devices:` обязана назвать конкретный приём справочника "
     "`references/donor-copy-devices.md` (`§номер` + название) и дать "
     "строку-улику поста.\n"
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    # --- Д136 контроль (Д133 держится): mid-line ЯВНЫЙ отказ ПРОДОЛЖАЕТ NO ---
    ("Д136 контроль Д133: mid-line ЯВНЫЙ отказ прозой продолжает NO "
     "(явная форма - не упоминание)",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "Примечание: donor-devices: нет, приём на самом деле не нашёл\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д136 контроль: line-start ГАРБАЖ держит полную строгость (NOREF) ---
    ("Д136 контроль line-start: garbage С НАЧАЛА строки остаётся NOREF "
     "(позиционный фильтр строгость с начала строки не снимает)",
     "donor-devices: какая-то ерунда без ссылки на приём\nВЕРДИКТ: PASS\n",
     "NOREF"),
]


def test_hook_donordev_d135_d136():
    """🔴 Д135+Д136 (скептик-раунд 46, по решению автора) - зеркало
    `test_hook_deadlang_d135_d136` у соседнего гейта dead-language, полное
    обоснование класса дефекта - её докстринг + комментарий перед
    `_at_line_start` в самом хуке.

    Д135 - `_in_backticks` щупал позицию ключа, фикс - `m.start(1)`
    (значение). У donor-devices эффект не наблюдаем на текущей форме
    регекса (нет `` `? `` вокруг ключа) - фикс здесь ради консистентности,
    регресс держит существующие Д134-кейсы (`_DONORDEV_D133_D134_CASES`)
    зелёными.

    Д136 - mid-line УПОМИНАНИЕ имени поля прозой («Ниже строка donor-
    devices: с приёмом и уликой.») давало `_donordev_state_one`
    НЕРАСПОЗНАННОЕ значение (обычно `NOREF`), которое «худшее побеждает»
    подхватывало наравне с настоящим отказом - ложный BLOCK на честном
    отчёте, напечатанном рядом. Фикс - `_donordev_looks_explicit` +
    `_at_line_start`: mid-line вхождение засчитывается, ТОЛЬКО если
    значение распознано явной формой (`OK` или непустой явный отказ);
    line-start сохраняет полную строгость (последний кейс списка -
    контроль)."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д135+Д136 хук: donor-devices mid-line упоминание vs отчёт",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д135+Д136 хук: donor-devices mid-line упоминание vs отчёт",
               False, err)
        return
    bad = []
    for name, text, want in _DONORDEV_D135_D136_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д135+Д136 хук: donor-devices mid-line упоминание vs отчёт "
           "(%d кейсов)" % len(_DONORDEV_D135_D136_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д137+Д138 (скептик-раунд 47, по решению автора), ВЕТКА donor-devices - зеркало
# `_DEADLANG_D137_D138_CASES` у соседнего гейта. Д137: `_DONORDEV_RE` не
# несла `` `? `` вокруг СВОЕГО ключа (Д135, раунд 46, сама констатировала
# асимметрию, чинила только позицию `_in_backticks`) - форма «`donor-
# devices`: §2.3 … -> PASS» не матчилась вовсе, читалась `MISSING`. Д138:
# словари `_DONORDEV_NO_START_RE`/`_DONORDEV_NO_PHRASE_RE` не несли корни
# «провер…»/«чита…» (только «примен…»/«опознан…») - «не проверял»/«не читал
# справочник» не матчили ни один слой отказа, mid-line-фильтр
# (`_donordev_looks_explicit`, Д136) читал их нераспознанным гарбажем и
# пропускал целиком. Полное обоснование - шапки `_DONORDEV_RE`/`_DONORDEV_
# NO_START_RE` в самом хуке.
# ---------------------------------------------------------------------------
_DONORDEV_D137_D138_CASES = [
    # --- Д137: ключ в бэктиках, значение снаружи ---
    ("Д137 ключ в бэктиках, значение снаружи - `donor-devices`: §2.3 ... "
     "-> PASS",
     "`donor-devices`: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    ("Д137 буллет + бэктик-ключ, значение снаружи",
     "- `donor-devices`: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    # --- Д137 регресс Д134: ключ+значение ОДНОЙ парой бэктиков - цитата ---
    ("Д137 регресс Д134: ключ+значение ОДНОЙ парой бэктиков - цитата, "
     "MISSING (не закрывается бэктик-ключом)",
     "`donor-devices: §2.3 смена системы отсчёта улика -> PASS`\n"
     "ВЕРДИКТ: PASS\n", "MISSING"),
    # --- Д137 регресс: бэктик-ключ + явный отказ продолжает блокировать ---
    ("Д137 регресс: бэктик-ключ + явный отказ «нет» продолжает NO",
     "`donor-devices`: нет\nВЕРДИКТ: PASS\n", "NO"),
    # --- Д138: mid-line признание «не проверял»/«не читал справочник» ---
    ("Д138 mid-line признание «не проверял» рядом с честным отчётом - "
     "блокирует (явная форма, не упоминание)",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "Примечание: donor-devices: не проверял, приём взял по памяти\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    ("Д138 mid-line признание «не читал справочник» рядом с честным "
     "отчётом - блокирует",
     "donor-devices: §2.3 смена системы отсчёта «цитата» -> PASS\n"
     "Примечание: donor-devices: не читал справочник приёмов\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д138 line-start регресс: «не проверял» продолжает блокировать ---
    ("Д138 line-start регресс: «не проверял» теперь классифицируется NO "
     "(было NOREF тем же catch-all'ом - точнее диагноз, тот же класс "
     "блокировки)",
     "donor-devices: не проверял\nВЕРДИКТ: PASS\n", "NO"),
]


def test_hook_donordev_d137_d138():
    """🔴 Д137+Д138 (скептик-раунд 47, по решению автора) - зеркало
    `test_hook_donordev_d135_d136` выше, тот же приём (вырез живой функции,
    прогон по полным текстам ответа).

    Д137 - `_DONORDEV_RE` не несла опциональный бэктик `` `? `` вокруг
    СВОЕГО ключа (в отличие от `_READFLAG_RE`/`_DONORDEV_TABLE_RE`) - форма
    «`donor-devices`: §2.3 … -> PASS» не матчилась вовсе, честная строка
    читалась `MISSING`. Фикс - `` `? `` СРАЗУ за литералом ключа.

    Д138 - словари отказа `_DONORDEV_NO_START_RE`/`_DONORDEV_NO_PHRASE_RE`
    не несли корни «провер…»/«чита…» - «не проверял»/«не читал справочник»
    не матчили mid-line-фильтр Д136 (тот же словарь, что и line-start,
    копии нет), гарбаж пропускался, честный отчёт рядом единолично давал
    `OK`. Фикс - корни добавлены в ОБА словаря."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д137+Д138 хук: donor-devices бэктик-ключ + mid-line словарь",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д137+Д138 хук: donor-devices бэктик-ключ + mid-line словарь",
               False, err)
        return
    bad = []
    for name, text, want in _DONORDEV_D137_D138_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д137+Д138 хук: donor-devices бэктик-ключ + mid-line словарь "
           "(%d кейсов)" % len(_DONORDEV_D137_D138_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д139+Д140 (скептик-раунд 48, по решению автора), ВЕТКА donor-devices.
# Д139 (тяжёлый, FAIL-OPEN): `_at_line_start` дефолтом щупает
# `_LINESTART_PREFIX_RE` (БЕЗ бэктика в классе символов) - у `_READFLAG_RE`
# та же функция с Д136 вызывается ТРЕТЬИМ аргументом
# `_LINESTART_PREFIX_BT_RE` (класс С бэктиком), а `_donordev_state`
# оставалась на дефолте. После Д137 (раунд 47) форма «`donor-devices`: …»
# МАТЧИТСЯ, но `m.start()` указывает на первую букву ключа, ПОСЛЕ
# открывающего бэктика - префикс от начала строки до этой позиции несёт
# ОДИН символ `` ` ``, которого класс без бэктика не терпит,
# `_at_line_start` возвращает `False`, вхождение считается MID-LINE.
# Дальше решает Д136: LITERAL/NOREF/отказ ВНЕ словаря - нераспознанная
# явная форма, вхождение ВЫБРАСЫВАЕТСЯ из «худшее побеждает» - честная
# строка рядом побеждает единолично, FAIL-OPEN. Фикс - `_at_line_start`
# зовётся ТЕМ ЖЕ третьим аргументом `_LINESTART_PREFIX_BT_RE`, что уже
# несёт READFLAG.
# Д140 (средний, FAIL-CLOSED, регресс класса от Д129/Д133): ведущее
# markdown-подчёркивание вокруг ключа («__donor-devices__:»/
# «_donor-devices_:») не матчилось вовсе - `\b` перед литералом ключа не
# видит переход между двумя словесными символами (`_` + буква), хотя
# ХВОСТОВОЙ класс `[ \t*_]*` эту же обвязку ПОСЛЕ ключа уже терпел с самого
# начала (несимметрично). Фикс - `\b` заменён альтернативой двух
# lookbehind-веток фиксированной ширины, «слово_donor-devices:» (слитно
# приклеенное подчёркивание) по-прежнему НЕ матчится. Полные обоснования
# обоих классов - шапки `_at_line_start`/`_DONORDEV_RE` в самом хуке.
# ---------------------------------------------------------------------------
_DONORDEV_D139_D140_CASES = [
    # --- Д139: LITERAL/NOREF/отказ ВНЕ словаря бэктик-ключом НА СВОЕЙ
    # СТРОКЕ рядом с честным отчётом - блок как у голого (было OK, fail-open) ---
    ("Д139 LITERAL бэктик-ключом на своей строке рядом с честной строкой - "
     "блок держится (было OK, fail-open)",
     "`donor-devices`: <§номер + название приёма> «<улика>» -> PASS\n"
     "donor-devices: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "LITERAL"),
    ("Д139 NOREF бэктик-ключом на своей строке рядом с честной строкой - "
     "блок держится (было OK, fail-open)",
     "`donor-devices`: смена системы отсчёта, улика есть -> PASS\n"
     "donor-devices: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "NOREF"),
    ("Д139 отказ ВНЕ словаря «пропустил» бэктик-ключом на своей строке - "
     "блок держится (было OK, fail-open)",
     "`donor-devices`: пропустил этот шаг\n"
     "donor-devices: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "NOREF"),
    # --- Д139 регресс: бэктик-ключ + явный отказ словарём продолжает NO ---
    ("Д139 регресс: бэктик-ключ + явный отказ «нет» продолжает NO",
     "`donor-devices`: нет\n"
     "donor-devices: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "NO"),
    # --- Д140: markdown-подчёркивание вокруг ключа - честный отчёт матчится ---
    ("Д140 __подчёркивание__ (жирный markdown, CommonMark) - честный отчёт "
     "матчится (было MISSING, fail-closed)",
     "__donor-devices__: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    ("Д140 _курсив_ подчёркиванием - честный отчёт матчится (было MISSING, "
     "fail-closed)",
     "_donor-devices_: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "OK"),
    # --- Д140 негативный контроль: подчёркивание, ПРИКЛЕЕННОЕ к слову, - НЕ
    # ключ (защита от ложного матча за счёт lookbehind-альтернативы) ---
    ("Д140 негативный контроль: «слово_donor-devices:» слитно - НЕ ключ, "
     "MISSING держится",
     "слово_donor-devices: §2.3 смена системы отсчёта «улика» -> PASS\n"
     "ВЕРДИКТ: PASS\n", "MISSING"),
]


def test_hook_donordev_d139_d140():
    """🔴 Д139+Д140 (скептик-раунд 48, по решению автора) - зеркало
    `test_hook_donordev_d137_d138` выше, тот же приём (вырез живой функции,
    прогон по полным текстам ответа).

    Д139 - `_at_line_start` внутри `_donordev_state` звалась БЕЗ третьего
    аргумента (дефолт `_LINESTART_PREFIX_RE`, без бэктика) - бэктик-ключ
    «`donor-devices`: …» (легален с Д137) на СВОЕЙ строке ложно читался
    MID-LINE, mid-line-фильтр Д136 выбрасывал нераспознанные значения
    (LITERAL/NOREF/отказ вне словаря) из «худшее побеждает» - честная
    строка рядом побеждала единолично, FAIL-OPEN. Фикс - третий аргумент
    `_LINESTART_PREFIX_BT_RE`.

    Д140 - `_DONORDEV_RE` открывалась `\\b` перед ключом - ведущее markdown-
    подчёркивание («__donor-devices__:»/«_donor-devices_:») не матчилось
    вовсе (два словесных символа подряд, перехода нет), честный отчёт
    читался `MISSING`. Фикс - `\\b` заменён lookbehind-альтернативой,
    приклеенное подчёркивание («слово_donor-devices:») по-прежнему НЕ
    матчится (негативный контроль в списке кейсов)."""
    st, err = _hook_donordev_state()
    if err == "NOHOOK":
        skip("Д139+Д140 хук: donor-devices бэктик-line-start + подчёркивание",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д139+Д140 хук: donor-devices бэктик-line-start + подчёркивание",
               False, err)
        return
    bad = []
    for name, text, want in _DONORDEV_D139_D140_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д139+Д140 хук: donor-devices бэктик-line-start + подчёркивание "
           "(%d кейсов)" % len(_DONORDEV_D139_D140_CASES), not bad, "; ".join(bad))


# ---------------------------------------------------------------------------
# 🔴 Д52 (скептик-раунд 12, по решению автора): У СЕМАНТИКИ Д48 НЕ БЫЛО НИ ОДНОГО ТЕСТА.
# Раунд 11 переписал выбор действующего ответа верификатора («действует ПОСЛЕДНИЙ
# ответ со слагом, а не первый»), но проверялось это только временным скриптом
# временным проверочным скриптом раунда 11, который в пакет не входит - то есть в
# раздаваемом раннере семантика жила
# БЕЗ стража, и следующая правка блока разбора транскрипта откатила бы её молча.
# Класс дефекта тот же, что у Д45: «функцию никто не гоняет». Тест ниже вырезает
# ЖИВОЙ python-блок из хука (как `_hook_donordev_ns` вырезает функцию гейта) и
# гоняет его на синтетических транскриптах.
# ---------------------------------------------------------------------------

def _hook_verifier_block():
    """Вырезает ЖИВОЙ python-блок разбора транскрипта из post-phase-gate.sh.

    Блок начинается строкой `_ver=$(... python3 - <<'PY'` и кончается одиночным
    `PY`. Возвращает пару `(путь к .py, причина)` по контракту `_hook_donordev_ns`:
    `NOHOOK` = skip (машина ученика без хука), любая другая причина = FAIL с
    честным текстом. Копии кода в тесте нет намеренно: копия рассинхронится с
    хуком в первый же раунд правок и будет зеленеть на коде, которого там уже нет."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать блок разбора "
                      "транскрипта не из чего" % HOOK)
    lines = src.splitlines(True)
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("_ver=$(") and "python3" in l)
    except StopIteration:
        return None, ("блок не вырезался из хука - якорь `_ver=$(… python3` сдвинут "
                      "или переименован? тест-страж семантики Д48 обезоружен")
    try:
        end = next(i for i in range(start + 1, len(lines))
                   if lines[i].rstrip("\n") == "PY")
    except StopIteration:
        return None, ("блок не вырезался из хука - закрывающий heredoc `PY` после "
                      "якоря не найден; тест-страж семантики Д48 обезоружен")
    body = "".join(lines[start + 1:end])
    try:
        compile(body, HOOK, "exec")
    except SyntaxError as e:
        return None, ("вырезанный блок хука не компилируется (%s) - границы выреза "
                      "сдвинуты или код битый; тест-страж семантики Д48 обезоружен" % e)
    fd, path = tempfile.mkstemp(suffix=".py", prefix="d52-verblock-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    return path, ""


_D52_SLUG = "d52ver"


def _d52_answer(verdict, donordev="§2.3 смена системы отсчёта «цитата из поста» -> PASS"):
    # dead-language: чисто - обязательная именованная строка формата 4.M.2 с v2.4
    # (слой живого языка, FIX-R38): фикстура несёт ВСЕ обязательные строки, иначе
    # гейт DEADLANG_MISSING честно рубит синтетический PASS-ответ.
    # 🔴 Д130 (скептик-раунд 43, в даты запуска.2026): ТА ЖЕ ЛОГИКА - donordev_read: PASS/
    # zhivoy_yazyk_read: PASS теперь МАНДАТОРНЫ на happy-path (см. `_readflag_state`
    # в хуке - READFLAG_MISSING_<ключ> при их отсутствии), а READFLAG проверяется
    # ПЕРВЫМ шагом elif-цепочки (Д124а) - раньше, чем donor-devices/dead-language.
    # Без этих двух строк синтетический PASS-ответ рубится READFLAG_MISSING_
    # donordev_read раньше, чем очередь доходит до кейсов, которые эта фикстура
    # реально проверяет (семантика Д48/Д52 - «действует последний ответ»).
    return ("POST-VERIFIER slug=%s\nW15-цепь: PASS\ndonor-devices: %s\n"
            "dead-language: чисто\ndonordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
            "ВЕРДИКТ: %s\n"
            % (_D52_SLUG, donordev, verdict))


def _d52_agent_pair(text, tid):
    """Пара записей транскрипта: tool_use(name=Agent) + его tool_result."""
    return [
        json.dumps({"message": {"content": [
            {"type": "tool_use", "id": tid, "name": "Agent"}]}}, ensure_ascii=False),
        json.dumps({"message": {"content": [
            {"type": "tool_result", "tool_use_id": tid,
             "content": [{"type": "text", "text": text}]}]}}, ensure_ascii=False),
    ]


D52_CASES = [
    ("FAIL → PASS (тот же слаг): действует СВЕЖИЙ PASS",
     _d52_agent_pair(_d52_answer("FAIL"), "t1") + _d52_agent_pair(_d52_answer("PASS"), "t2"),
     "OK"),
    ("PASS → FAIL: действует СВЕЖИЙ FAIL, старый PASS не спасает",
     _d52_agent_pair(_d52_answer("PASS"), "t1") + _d52_agent_pair(_d52_answer("FAIL"), "t2"),
     "VERDICT_FAIL"),
    ("старый PASS + свежий «donor-devices: нет» -> отказ микса действует",
     _d52_agent_pair(_d52_answer("PASS"), "t1")
     + _d52_agent_pair(_d52_answer("PASS", "нет"), "t2"),
     "DONORDEV_NO"),
    ("одиночный PASS без перепрогонов - без изменений",
     _d52_agent_pair(_d52_answer("PASS"), "t1"), "OK"),
]


def test_hook_verifier_last_answer():
    """🔴 Д52 (раунд 12): семантика Д48 «действует ПОСЛЕДНИЙ ответ верификатора».

    Слаг живёт весь прогон поста и при правках не меняется, поэтому пока блок
    обрывался `break` на ПЕРВОМ ответе со слагом, перепрогоны верификатора в решение
    не попадали вовсе: старый PASS маскировал свежий отказ (пост выходил с уже
    найденным дефектом), старый FAIL делал блок вечным (новый ответ ложится ПОЗЖЕ и
    до решения не доходит, обойти можно было только сменой слага). Раунд 11 это
    починил, но проверял временным скриптом раунда 11, в пакет не входящим - здесь
    семантика получает
    страж в раздаваемом раннере.

    Fail-closed ВНУТРИ выбранного ответа проверяется третьим кейсом: свежий ответ
    несёт `ВЕРДИКТ: PASS`, но отказ в строке `donor-devices` его не пропускает."""
    blk, err = _hook_verifier_block()
    if err == "NOHOOK":
        skip("Д52 хук: действует ПОСЛЕДНИЙ ответ верификатора (семантика Д48)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if blk is None:
        record("Д52 хук: действует ПОСЛЕДНИЙ ответ верификатора (семантика Д48)",
               False, err)
        return
    bad = []
    tmpdir = tempfile.mkdtemp(prefix="d52-tr-")
    try:
        for i, (name, records_, want) in enumerate(D52_CASES):
            tr = os.path.join(tmpdir, f"case{i}.jsonl")
            with open(tr, "w", encoding="utf-8") as f:
                f.write("\n".join(records_) + "\n")
            p = subprocess.run([sys.executable, blk], capture_output=True, text=True,
                               env=dict(os.environ, TRANSCRIPT=tr, SLUG=_D52_SLUG))
            got = p.stdout.strip() or ("<stderr> " + p.stderr.strip()[:200])
            if got != want:
                bad.append(f"{name}: ждём {want}, получили {got}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.unlink(blk)
    record("Д52 хук: действует ПОСЛЕДНИЙ ответ верификатора - живой блок разбора "
           f"транскрипта ({len(D52_CASES)} кейса)", not bad, "; ".join(bad))


def _invocable_self_check():
    """Д75-self-check (скептик-раунд 24, по решению автора). Докстринг раунда 23 обещал
    «репро на ВРЕМЕННОЙ копии (chmod -x)», которого в коде не было - страж
    рассказывал о своей детекции, но живьём её не проверял.

    Строит РЕАЛЬНЫЙ мини-скрипт БЕЗ бита x во временном каталоге (не копию
    боевого хука по содержимому - экзек зависит только от прав файла, копия
    содержимого ничего не доказывает дополнительно) и подтверждает обе
    половины логики, которую использует test_hook_invocable: os.access(...,
    X_OK) обязан вернуть False, а прямой вызов - дать PermissionError (в
    основном тесте это ловится как rc=126). Копия удаляется в finally,
    живой хук этот self-check не трогает."""
    tmpdir = tempfile.mkdtemp(prefix="d75-invocable-selfcheck-")
    try:
        fake = os.path.join(tmpdir, "fake-hook.sh")
        with open(fake, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\necho ok\n")
        os.chmod(fake, 0o644)  # осознанно без бита x - воспроизводим корень Д72
        detects_missing_x = not os.access(fake, os.X_OK)
        try:
            subprocess.run([fake], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=5)
            live_rc = None
        except PermissionError:
            live_rc = 126
        ok = detects_missing_x and live_rc == 126
        record("Д75 self-check: страж реально ловит потерю бита x (os.access "
               "+ живой вызов на временной копии)", ok,
               "" if ok else
               f"os.access(X_OK)={not detects_missing_x}, live_rc={live_rc} - "
               "self-check не воспроизвёл Д72 на этой машине")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")

# Живой вызов чужого хука со стороны раннера скилла post - side-effect-риск
# (сеть/файлы/боты чужих контуров). Безопасно гонять живьём ТОЛЬКО хуки
# СВОЕГО контура (post-*), явно проверенные на быстрый выход и отсутствие
# побочек на пустом/закрытом stdin. Остальным голым путям из settings.json -
# только проверка бита x (см. _check_bare_sh_hook ниже).
SAFE_LIVE_INVOKE_HOOKS = {
    os.path.expanduser("~/.claude/hooks/post-phase-gate.sh"),
    os.path.expanduser("~/.claude/hooks/post-layer-checkpoint-gate.sh"),
    os.path.expanduser("~/.claude/hooks/post-receipt-write-guard.sh"),
    os.path.expanduser("~/.claude/hooks/post-skill-must-be-invoked.sh"),
}

# Голый абсолютный путь на *.sh: начинается с "/", без пробелов/кавычек
# (значит без обёртки `bash "..."`/`sh ...`), заканчивается на .sh.
_BARE_SH_RE = re.compile(r'^/\S+\.sh$')

# 🔴 Д81 (скептик-раунд 26, по решению автора, рецидив класса Д74/Д77 - хардкод/недосчёт
# СПИСКА форм, не поимённых хуков). Комментарий-предок здесь заявлял: «формы
# `$HOME/...` и `~/...` осознанно не матчатся: settings.json их не зовёт голым
# путём, для них permission-денайл не воспроизводится тем же способом» - ОБА
# утверждения ложны. Репро скептика раунда 26: снять бит x с любой из этих форм
# без bash-обёртки и вызвать её так, как это делает settings.json (путь напрямую,
# без интерпретатора) - `subprocess.run([path], ...)` даёт PermissionError / rc=126,
# ИДЕНТИЧНО голому абсолютному пути (см. `_invocable_self_check`, та же механика).
# Отличается РОВНО ОДНА вещь - присутствие bash/sh-обёртки (`bash "$HOME/..."`):
# тогда файл читает интерпретатор, бит x ему не нужен, и это ДЕЙСТВИТЕЛЬНО другой
# класс - такие формы по-прежнему не матчатся ни одним из трёх регэкспов ниже.
# А голые (БЕЗ обёртки) `$HOME/...` и `~/...` - в живом settings.json их 5
# (grep-улика раунда 26: 3× $HOME, 2× ~) - тот же класс, что голый абсолютный
# путь, и с этого раунда покрыты им же (см. `_resolve_bare_sh_command`).
_BARE_SH_HOME_RE = re.compile(r'^\$HOME/\S+\.sh$')
_BARE_SH_TILDE_RE = re.compile(r'^~/\S+\.sh$')


def _resolve_bare_sh_command(cmd):
    """Три легальные ГОЛЫЕ (без bash/sh-обёртки) формы регистрации *.sh в
    settings.json: абсолютный путь `/abs/...`, `$HOME/...`, `~/...`. Возвращает
    РЕЗОЛВНУТЫЙ абсолютный путь на диске для любой из трёх, либо None, если cmd
    не голая форма ни одной (в т.ч. если это форма с bash/sh-обёрткой - другой
    класс, см. докстринг `_BARE_SH_HOME_RE` выше).

    `$HOME` резолвится через `os.environ["HOME"]` (та же переменная, которую при
    исполнении команды подставляет сама settings.json/shell-среда claude code -
    не `os.path.expanduser`, у него своя логика на системах без HOME в env);
    `~` - через `os.path.expanduser` (стандартная и эквивалентная HOME семантика
    для tilde-форм)."""
    if _BARE_SH_RE.match(cmd):
        return cmd
    if _BARE_SH_HOME_RE.match(cmd):
        home = os.environ.get("HOME", os.path.expanduser("~"))
        return os.path.join(home, cmd[len("$HOME/"):])
    if _BARE_SH_TILDE_RE.match(cmd):
        return os.path.expanduser(cmd)
    return None


def _bare_path_sh_hooks(settings_path):
    """Источник истины Д77 (взамен хардкод-списка из двух хуков р23/р24),
    расширен Д81 (раунд 26) на голые `$HOME/...` и `~/...` формы - см.
    `_resolve_bare_sh_command`. Разбирает settings.json и возвращает ВСЕ
    регистрации, где command - голый путь на *.sh (любой из трёх видов).
    Формат settings.json: `.hooks.<Событие>` = список групп, группа =
    `{matcher?, hooks: [{command, type, ...}]}` - matcher на группе
    необязателен (тогда действует на все инструменты, репортим как "*").
    Возвращает список (event, matcher, resolved_path); resolved_path уже
    абсолютный путь на диске (см. `_resolve_bare_sh_command`), не сырую
    строку command. None - если settings.json не прочитать (битый JSON/файла
    нет) - это не 0 регистраций, вызывающий код обязан различать эти два
    случая (SKIP vs «страж без данных»)."""
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    out = []
    for event, groups in (data.get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher") or "*"
            for h in group.get("hooks") or []:
                if not isinstance(h, dict):
                    continue
                cmd = h.get("command", "")
                if not isinstance(cmd, str):
                    continue
                resolved = _resolve_bare_sh_command(cmd)
                if resolved:
                    out.append((event, matcher, resolved))
    return out


def _check_bare_sh_hook(path):
    """Общая логика проверки ОДНОГО голого пути - переиспользуется и боевым
    test_hook_invocable (живой settings.json), и Д77-self-check (подменный
    settings.json), чтобы страж и его самопроверка не могли разойтись.
    Возвращает (ok, detail). Порядок: (а) файла нет на диске - FAIL «битая
    регистрация» (это НЕ «машина ученика» - хук в settings.json прописан,
    значит кто-то его удалил/переименовал, не поставил); (б) бит x снят -
    FAIL немедленно; (в) хук из SAFE_LIVE_INVOKE_HOOKS (контур post) - живой
    вызов МЕХАНИКОЙ settings.json (голым путём, без bash, пустой/закрытый
    stdin), rc/исключение 126 (Permission denied) или 127 (не найден) = FAIL,
    остальное = OK; хуки НЕ из safe-list живьём не дёргаем - только бит x."""
    if not os.path.exists(path):
        return False, f"зарегистрирован в settings.json, но файла нет на диске ({path}) - битая регистрация"
    if not os.access(path, os.X_OK):
        return False, f"{path}: без бита x (settings.json зовёт голым путём, без bash-обёртки) - гейт мёртв; chmod +x"
    if path in SAFE_LIVE_INVOKE_HOOKS:
        try:
            p = subprocess.run([path], stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=15)
            rc = p.returncode
        except PermissionError:
            rc = 126
        except FileNotFoundError:
            rc = 127
        if rc in (126, 127):
            return False, f"rc={rc} - хук не запускается способом settings.json (путь напрямую, без bash-обёртки)"
    return True, ""


def _settings_source_of_truth_self_check():
    """Д77-self-check (скептик-раунд 25, по решению автора, рецидив класса Д74),
    расширен Д81 (раунд 26, по решению автора - тот же рецидив ЕЩЁ РАЗ, на этот раз на
    ВИДЕ форм, не на числе поимённых хуков).
    Докстринг р24 заявлял «страж знает голые пути settings.json», а по факту
    список был захардкожен на РОВНО ДВА хука (HOOK, PKT_HOOK) - в живом
    settings.json их 64 (grep-улика раунда 25). Хардкод не масштабируется:
    каждый новый голый Stop/PreToolUse/UserPromptSubmit-хук оставался
    бит-слепым, пока кто-то вручную не дописывал его в список руками - тот же
    класс дефекта, что и Д74, просто на другом числе хуков. Фикс р25 убил
    класс по ЧИСЛУ: `_bare_path_sh_hooks` выводит перечень из settings.json на
    каждый прогон, хардкод-список удалён целиком - но регэксп покрывал только
    ОДНУ из трёх легальных голых форм (`/abs/...`), а голые `$HOME/...` и
    `~/...` (5 регистраций в живом settings.json - Д81) объявлялись исключённой
    категорией ложным обоснованием «permission-денайл не воспроизводится тем же
    способом». Фикс р26 закрывает и вид формы: `_resolve_bare_sh_command`
    резолвит все три в абсолютный путь на диске.

    Этот self-check доказывает на ПОДМЕННОМ settings.json (живой
    ~/.claude/settings.json не трогаем и не читаем здесь) четыре формы разом:
    голый абсолютный путь, голый `$HOME/...`, голый `~/...`, и bash-обёрнутый
    путь (`bash "..."`) - и требует: (1) в списке РОВНО ТРИ записи - все три
    голые формы попали, bash-обёртка (другой класс, интерпретатор читает файл
    сам) исключена; (2) проверка КАЖДОЙ из трёх - FAIL с текстом про
    отсутствующий файл (несуществующие decoy-имена, резолвятся под реальный
    HOME, но там точно не существуют)."""
    tmpdir = tempfile.mkdtemp(prefix="d77-settings-sot-selfcheck-")
    try:
        fake_settings = os.path.join(tmpdir, "settings.json")
        ghost = os.path.join(tmpdir, "ghost-hook-does-not-exist.sh")
        home_form = "$HOME/.claude/hooks/decoy.sh"
        tilde_form = "~/.claude/hooks/decoy2.sh"
        fake_data = {
            "hooks": {
                "Stop": [
                    {"hooks": [{"type": "command", "command": ghost}]}
                ],
                "PreToolUse": [
                    {"matcher": "Bash",
                     "hooks": [
                         {"type": "command", "command": f'bash "{ghost}"'},
                         {"type": "command", "command": home_form},
                         {"type": "command", "command": tilde_form},
                     ]}
                ],
            }
        }
        with open(fake_settings, "w", encoding="utf-8") as f:
            json.dump(fake_data, f)

        expect_home = os.path.join(os.environ.get("HOME", os.path.expanduser("~")),
                                    ".claude/hooks/decoy.sh")
        expect_tilde = os.path.expanduser(tilde_form)
        want = {("Stop", "*", ghost), ("PreToolUse", "Bash", expect_home),
                ("PreToolUse", "Bash", expect_tilde)}
        found = _bare_path_sh_hooks(fake_settings)
        three_bare_forms_found = set(found) == want and len(found) == 3

        ok_fail_detect = False
        detail = ""
        if three_bare_forms_found:
            bad = []
            for p in (ghost, expect_home, expect_tilde):
                ok_hook, why = _check_bare_sh_hook(p)
                if ok_hook or "файла нет" not in why:
                    bad.append(f"{p}: ok={ok_hook}, why={why!r}")
            ok_fail_detect = not bad
            if not ok_fail_detect:
                detail = "проверка не поймала отсутствующий файл: " + "; ".join(bad)
        else:
            detail = (f"found={found!r}, ожидали={sorted(want)!r} - парсер либо не выделил "
                      "все три голые формы, либо ошибочно зацепил bash-обёртку как голый путь")

        ok = three_bare_forms_found and ok_fail_detect
        record("Д81 self-check: страж на ПОДМЕННОМ settings.json резолвит и ловит FAIL'ом ВСЕ ТРИ "
               "голые формы (/abs, $HOME/, ~/), bash-обёртку не путает с голым путём",
               ok, detail)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_hook_invocable():
    """Д72/Д74/Д77-страж (скептик-раунды 23-25, по решению автора, класс «гейт
    физически не вызывается»). Корень Д72: боевой Stop-хук post-phase-gate.sh
    потерял бит x - затёрт cp-применениями патчей из scratchpad (копия несёт
    содержимое источника, НЕ его права; исходник в scratchpad лежал без +x).
    settings.json зовёт хук ПО ПУТИ напрямую (`"command":
    ".../post-phase-gate.sh"`, БЕЗ обёртки `bash "..."`, в отличие от части
    соседних Stop-хуков в том же settings.json) - без бита x это "Permission
    denied", rc=126, и ВСЕ гейты выдачи (lint/bench/donor-devices/класс
    события) молчали, а раннер тестов этого не поймал ни разу: test_hook_syntax
    гоняет `["bash", "-n", HOOK]`, _run_hook_isolated и Д52-блок гоняют
    `["bash", HOOK]` - bash интерпретирует скрипт по содержимому, бит x ему
    не нужен. Слепое пятно было в способе ВЫЗОВА раннера, не в логике хука.

    Д74 (раунд 24): страж р23 параметризовал ровно ОДИН хук, а голым путём
    settings.json зовёт минимум два. Фикс р24 расширил список до ДВУХ
    (HOOK, PKT_HOOK) - но захардкодил их поимённо, тот же класс дефекта на
    другом числе: в живом settings.json голых путей на *.sh 64 (grep-улика
    раунда 25, Д77), список знал про 2. Каждый следующий голый хук снова был
    бы бит-слепым до ручной правки этого файла.

    Д77 (раунд 25): класс закрыт ИСТОЧНИКОМ ИСТИНЫ, не расширением списка.
    `_bare_path_sh_hooks` вычитывает settings.json на каждый прогон и
    возвращает ВСЕ регистрации голых путей - хардкод-список удалён. На
    каждую запись `_check_bare_sh_hook`: (а) файла нет на диске - FAIL
    «зарегистрирован, но отсутствует» (битая регистрация, не «машина
    ученика» - в settings.json путь прописан); (б) бит x снят - FAIL
    немедленно; (в) живой вызов МЕХАНИКОЙ settings.json (голым путём, без
    bash, пустой/закрытый stdin, rc/исключение 126/127 = FAIL) - но ТОЛЬКО
    для хуков из SAFE_LIVE_INVOKE_HOOKS (контур post: post-phase-gate.sh,
    post-layer-checkpoint-gate.sh, post-receipt-write-guard.sh,
    post-skill-must-be-invoked.sh - все явно проверены на быстрый выход без
    побочек); все прочие голые пути (чужие контуры - website-*, no-*-guard,
    reel-*, deck-* и т.п.) получают ТОЛЬКО проверку бита x - живой вызов
    чужого хука со стороны раннера скилла post это side-effect-риск (сеть,
    файлы, боты чужого контура). settings.json не прочитать (битый JSON/нет
    файла) - страж сам FAIL, не тихо 0 регистраций.

    Д81 (раунд 26, по решению автора): «источник истины» из Д77 сам оказался неполным
    источником - `_bare_path_sh_hooks` ловил ТОЛЬКО форму `/abs/...`, а голые
    (БЕЗ bash-обёртки) `$HOME/...` и `~/...` объявлялись исключением с ложным
    обоснованием («permission-денайл не воспроизводится тем же способом» -
    воспроизводится идентично, отличается только присутствие bash-обёртки,
    которая делает класс ДРУГИМ, а не сама тильда/макрос). Фикс резолвит все
    три голые формы в абсолютный путь на диске (`_resolve_bare_sh_command`) и
    считает их одним классом; bash-обёрнутые формы по-прежнему не матчатся -
    это законно другой класс (интерпретатор читает файл сам). Честное число
    проверенных регистраций печатается строкой `Д81-страж: ... под проверкой`
    ниже - счёт живой (из settings.json на каждый прогон), не захардкожен.
    Репро логики детекции бита x - в `_invocable_self_check` (Д75); репро
    логики «источник истины ловит битую регистрацию на всех трёх формах» - в
    `_settings_source_of_truth_self_check` (Д77/Д81) - обе гоняются вызовом
    ниже."""
    registrations = _bare_path_sh_hooks(SETTINGS_PATH)
    if registrations is None:
        record("Д77-страж: settings.json читается и разбирается", False,
               f"не смог прочитать/распарсить {SETTINGS_PATH} - страж без источника истины")
    else:
        if not registrations:
            record("Д77-страж: в settings.json есть хотя бы одна регистрация голым путём на *.sh",
                   False, f"{SETTINGS_PATH}: 0 регистраций - формат сменился или парсер сломан")
        by_path = {}
        for event, matcher, cmd in registrations:
            by_path.setdefault(cmd, []).append(f"{event}/{matcher}")
        # Д81 (раунд 26): улика роста числа проверенных - до фикса регэксп ловил
        # только форму /abs (было ~64, grep-улика раунда 25), голые $HOME/~ формы
        # (5 регистраций живого settings.json на момент раунда 26) не матчились и
        # молча выпадали из проверки. Печатаем счёт как отдельную строку - число
        # растёт с каждым новым голым хуком любой из трёх форм, не захардкожено.
        # 🔴 Д84 скептик-раунда 27 (по решению автора): строка печатала ОДНО число -
        # len(by_path) (уникальные разрешённые пути, 69) - подставляя его туда,
        # где по смыслу текста ожидалось число РЕГИСТРАЦИЙ (у одного хука бывает
        # несколько регистраций - разные события/matcher'ы на один файл). Живой
        # свод: registrations = 76 (71 голых /abs + 3 $HOME + 2 ~), by_path
        # схлопывает дубли по разрешённому пути до 69 уникальных файлов - это
        # ДВА разных, оба честных числа, а печаталось одно под именем другого.
        # Теперь печатаются оба явно.
        record(f"Д81-страж: голых регистраций *.sh под проверкой (3 формы: /abs, "
               f"$HOME/, ~/) - {len(registrations)} (уникальных файлов {len(by_path)})", True, "")
        for path, sites in sorted(by_path.items()):
            where = ", ".join(sites)
            live = " + живой вызов (contour post)" if path in SAFE_LIVE_INVOKE_HOOKS else " (только бит x - чужой контур)"
            name = f"Д77-страж: {os.path.basename(path)} [{where}]{live}"
            ok, detail = _check_bare_sh_hook(path)
            record(name, ok, detail)
    _invocable_self_check()
    _settings_source_of_truth_self_check()


# ---------------------------------------------------------------------------
# 🔴 Дефект-класс Д45/Д52/Д107 (третий+ рецидив, «дефекты без постоянного
# стража»): у гейта READFLAG (`_readflag_state`, честность строк-отчётов
# `zhivoy_yazyk_read:`/`donordev_read:`, фиксы R42-R44 - дефекты Д120/Д125-
# Д130) НЕ БЫЛО НИ ОДНОГО ПОСТОЯННОГО ТЕСТА В ЭТОМ РАННЕРЕ - `grep READFLAG`
# по файлу до этой правки давал 0 совпадений. Слой жил только временными
# `verify-FIX-R42.sh`/`verify-FIX-R43.sh` в scratchpad сессии, которые
# удаляются вместе с сессией - ровно тот класс, что Д45 закрыл у
# donor-devices (раунд 10, см. `test_hook_donordev_gate` выше) и Д52 у
# семантики «последний ответ верификатора» (раунд 12, см.
# `test_hook_verifier_last_answer`): страж В ХУКЕ есть и правится раундами,
# но ЕГО НИКТО НЕ ГОНЯЕТ на каждом прогоне, и следующая правка функции
# рядом рассинхронится молча. Функции ниже - зеркало `_hook_donordev_ns`/
# `_hook_deadlang_ns` выше (тот же контракт `(namespace, причина)`, тот же
# приём резки по якорям, то же обоснование «вырезаем, а не копируем» - см.
# докстринг `_hook_donordev_ns` целиком, здесь не повторяется).
# ---------------------------------------------------------------------------

def _hook_readflag_ns():
    """Вырезает ЖИВОЙ кусок гейта READFLAG (константы `_READFLAG_*` + функция
    `_readflag_state`) из post-phase-gate.sh и ИСПОЛНЯЕТ его - зеркало
    `_hook_donordev_ns()`/`_hook_deadlang_ns()` выше.

    Возвращает пару `(namespace, причина)`:
      (ns, "")           вырез удался;
      (None, "NOHOOK")   хука нет на диске - ЕДИНСТВЕННЫЙ случай под skip
                         (машина ученика без установленного хука);
      (None, <текст>)    вырез/exec не удались = FAIL с честной причиной."""
    if not os.path.exists(HOOK):
        return None, "NOHOOK"
    src = _hook_src()
    if not src:
        return None, ("файл хука %s пуст или нечитаем - вырезать функцию "
                      "_readflag_state не из чего" % HOOK)
    lines = src.splitlines(True)
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("_READFLAG_RE = re.compile("))
    except StopIteration:
        return None, ("функция не вырезалась из хука - якорь `_READFLAG_RE = "
                      "re.compile(` сдвинут или переименован? тест-страж гейта "
                      "READFLAG обезоружен")
    end, seen_def = None, False
    for i in range(start, len(lines)):
        if lines[i].startswith("def _readflag_state("):
            seen_def = True
            continue
        if seen_def and lines[i][:1] not in ("", " ", "\t", "\n", "#"):
            end = i
            break
    if not seen_def:
        return None, ("функция не вырезалась из хука - якорь `def "
                      "_readflag_state(` не найден после `_READFLAG_RE`; "
                      "тест-страж гейта READFLAG обезоружен")
    # `_readflag_state` зовёт `_deadlang_soft` (мягкая нормализация значения) -
    # эта функция определена ВЫШЕ по файлу хука, ЗА границей выреза READFLAG,
    # тем же способом, каким `_hook_deadlang_ns` берёт `_donordev_strip_quoted`
    # у соседнего выреза donor-devices. Копировать нельзя по тому же закону,
    # что записан в `_hook_donordev_ns`: копия рассинхронится с хуком в первый
    # же раунд правок. Берём живой namespace соседнего выреза - один источник
    # истины остаётся один.
    ns = {"re": re}
    dlns, _dlerr = _hook_deadlang_ns()
    if dlns:
        ns.update({k: v for k, v in dlns.items() if not k.startswith("__")})
    try:
        exec(compile("".join(lines[start:end or len(lines)]), HOOK, "exec"), ns)
    except Exception as e:
        return None, ("вырезанный кусок хука не исполняется (%s: %s) - границы "
                      "выреза сдвинуты или код функции битый; тест-страж гейта "
                      "READFLAG обезоружен" % (type(e).__name__, e))
    return ns, ""


def _hook_readflag_state():
    """ЖИВАЯ функция `_readflag_state` из хука (обёртка над
    `_hook_readflag_ns`, зеркало `_hook_donordev_state`/`_hook_deadlang_state`
    выше). Контракт пары `(функция, причина)` тот же: `NOHOOK` = skip, любая
    другая причина = FAIL, пустая строка = вырез удался."""
    ns, err = _hook_readflag_ns()
    if ns is None:
        return None, err
    fn = ns.get("_readflag_state")
    if fn is None:
        return None, ("кусок исполнился, но имени _readflag_state в нём нет - "
                      "функцию переименовали? тест-страж гейта READFLAG "
                      "обезоружен")
    return fn, ""


# (имя, ПОЛНЫЙ текст ответа верификатора, ожидаемый диагноз `_readflag_state`)
# - `_readflag_state` судит ВЕСЬ ответ целиком (finditer по обоим regex'ам),
# не одну строку по шаблону, поэтому, в отличие от DONORDEV_CASES/
# DEADLANG_CASES, каждый кейс несёт готовый многострочный текст, а не
# значение под подстановку. Кейсы по фиксам R42-R44 (дефекты Д120/Д125-Д130).
READFLAG_CASES = [
    # --- штатное использование: обе строки честны -> None (Д120 база) ---
    ("оба ключа честны (happy-path Д130)",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    # --- отказ по каждому ключу отдельно (Д120 база) ---
    ("zhivoy_yazyk_read: FAIL - явный отказ",
     "donordev_read: PASS\nzhivoy_yazyk_read: FAIL\nВЕРДИКТ: PASS\n",
     "zhivoy_yazyk_read"),
    ("donordev_read: FAIL - справочник не передан (канонная формула 04-review.md 4.M.2)",
     "donordev_read: FAIL - справочник не передан\nzhivoy_yazyk_read: PASS\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д129: признание НЕ с начала строки, мид-предложением ---
    ("mid-line «Примечание: zhivoy_yazyk_read: FAIL» - без ^-якоря (Д129)",
     "donordev_read: PASS\nПримечание: zhivoy_yazyk_read: FAIL - справочник "
     "не открывал\nВЕРДИКТ: PASS\n", "zhivoy_yazyk_read"),
    # --- 🔴 Д126: ключ в бэктиках / в pipe-таблице реестра ---
    ("бэктики `donordev_read`: FAIL (Д126)",
     "`donordev_read`: FAIL\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "donordev_read"),
    ("pipe-таблица | zhivoy_yazyk_read | FAIL | (Д126)",
     "donordev_read: PASS\n| zhivoy_yazyk_read | FAIL |\nВЕРДИКТ: PASS\n",
     "zhivoy_yazyk_read"),
    # --- 🔴 Д125: литерал реестра «PASS | FAIL» - пересказ шаблона, не решение ---
    ("литерал реестра «PASS | FAIL» (Д125)",
     "donordev_read: PASS | FAIL\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "LITERAL"),
    # --- 🔴 Д127: белый список - легально РОВНО слово pass, всё иное FAIL ---
    ("N/A - не входит в белый список (Д127)",
     "donordev_read: N/A\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "donordev_read"),
    ("опечатка FAILED - не входит в белый список (Д127)",
     "donordev_read: PASS\nzhivoy_yazyk_read: FAILED\nВЕРДИКТ: PASS\n",
     "zhivoy_yazyk_read"),
    # --- 🔴 Д130: happy-path мандатирует ПРИСУТСТВИЕ обоих ключей ---
    ("обе строки отсутствуют при ВЕРДИКТ: PASS - побеждает donordev_read (Д130)",
     "Верификатор всё проверил, справочники не упомянуты.\nВЕРДИКТ: PASS\n",
     "MISSING_donordev_read"),
    ("donordev_read есть, zhivoy_yazyk_read отсутствует (Д130)",
     "donordev_read: PASS\nВЕРДИКТ: PASS\n", "MISSING_zhivoy_yazyk_read"),
    ("zhivoy_yazyk_read есть, donordev_read отсутствует (Д130)",
     "zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", "MISSING_donordev_read"),
    # --- 🔴 Д131 (скептик-раунд 44, по решению автора): белый список Д127 требовал
    # значение РОВНО «pass», но канонная формула 04-review.md 4.M.2 САМА
    # предписывает хвост-пояснение («PASS - справочник приёмов прочитан из
    # промпта») - честный отчёт по этому образцу ловился как FAIL. Плюс оба
    # ключа одной строкой топили второй ключ в значении первого (жадный
    # `(.*)$`). Фикс - `_READFLAG_RE` ограничивает значение следующим ключом/
    # концом строки, `_readflag_state` признаёт «pass + честный хвост», но
    # НЕ «pass + хвост с признанием-отказом» (см. следующий кейс).
    ("честный PASS с пояснением, канонная формула 04-review.md 4.M.2 (Д131а)",
     "donordev_read: PASS - справочник приёмов прочитан из промпта\n"
     "zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    ("оба ключа одной строкой, разделитель · - второй ключ не тонет в первом (Д131а)",
     "donordev_read: PASS · zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    ("PASS с признанием-отказом в хвосте - НЕ амнистируется (Д131б)",
     "donordev_read: PASS, но не открывал справочник\nzhivoy_yazyk_read: PASS\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д134 (скептик-раунд 45, по решению автора): ЦИТАТА КАНОНА В БЭКТИКАХ НЕ
    # УДОВЛЕТВОРЯЕТ МАНДАТ ПРИСУТСТВИЯ Д130 (fail-open, если бы не фикс).
    # Ответ, цитирующий инструкцию промпта дословно («ОБЯЗАТЕЛЬНЫ именованные
    # строки … `donordev_read: PASS` …»), несёт ключ+значение в бэктиках -
    # это ПРИМЕР из ТЗ, не отчёт самого верификатора. `_in_backticks`:
    # бэктик-вхождение с честным pass НЕ отмечает ключ присутствующим,
    # мандат Д130 остаётся MISSING; та же цитата с FAIL/LITERAL ПРОДОЛЖАЕТ
    # засчитываться (Д126, R42, fail-closed не откатывается - следующий кейс).
    ("Д134 цитата канона целиком в бэктиках, ОБА ключа - мандат Д130 не "
     "закрыт цитатой",
     "Верификатор напоминает себе: ОБЯЗАТЕЛЬНЫ именованные строки "
     "`donordev_read: PASS` и `zhivoy_yazyk_read: PASS` перед выдачей.\n"
     "ВЕРДИКТ: PASS\n", "MISSING_donordev_read"),
    ("Д134 компактная форма БЕЗ бэктиков - легальный отчёт (существо "
     "соблюдено, регресс формы (б) из канона)",
     "Чек-лист вывода: donordev_read: PASS, zhivoy_yazyk_read: PASS.\n"
     "ВЕРДИКТ: PASS\n", None),
    ("Д134 бэктиковый FAIL продолжает блокировать (Д126 держится - "
     "fail-closed в сторону признания-отказа не ослаблен)",
     "`donordev_read: FAIL - справочник не передан`\n"
     "zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", "donordev_read"),
    ("Д134 смесь: цитата в бэктиках + честный отчёт НИЖЕ - мандат закрыт "
     "честной строкой, не цитатой",
     "Как говорит канон: `donordev_read: PASS`\n"
     "donordev_read: PASS - справочник реально прочитан\n"
     "zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    # --- 🔴 Д135 (скептик-раунд 46, по решению автора): `_in_backticks` щупал
    # позицию КЛЮЧА, не ЗНАЧЕНИЯ - форма «`ключ`: значение» (бэктики ТОЛЬКО
    # вокруг имени поля, значение СНАРУЖИ - markdown-привычка, не цитата
    # канона) ложно читалась как бэктик-цитата и амнистировала мандат Д130
    # ОБРАТНО в MISSING. Фикс - `m.start(2)` (позиция значения). Регресс:
    # истинная цитата (ключ+значение ОДНОЙ парой бэктиков) и бэктиковый FAIL
    # выше в этом же списке продолжают держаться (Д134/Д126 не откатываются).
    ("Д135 ключ в бэктиках, значение СНАРУЖИ - markdown-привычка, не "
     "цитата - оба ключа честны",
     "`donordev_read`: PASS\n`zhivoy_yazyk_read`: PASS\nВЕРДИКТ: PASS\n",
     None),
    ("Д135 буллет + бэктик-ключ, значение снаружи - honest",
     "- `donordev_read`: PASS\n- `zhivoy_yazyk_read`: PASS\n"
     "ВЕРДИКТ: PASS\n", None),
    ("Д135 регресс: бэктик-ключ + FAIL снаружи продолжает блокировать "
     "(Д126 держится и на этой форме)",
     "`donordev_read`: FAIL\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "donordev_read"),
    # --- 🔴 ЗЕРКАЛО Д136 НА READFLAG (скептик-раунд 46, по решению автора, решение
    # оркестратора - см. changelog v2.4-r46). Whitelist Д127 читает ЛЮБОЙ
    # не-`pass` токен как `FAIL` - mid-line ПЕРЕСКАЗ промпта прозой («Я
    # напечатал строку donordev_read: как требует канон.») тоже давал
    # `FAIL`, ложный блок честного отчёта. Фикс - `_READFLAG_EXPLICIT_BAD_RE`
    # (буквальное fail/na/none ИЛИ фраза отказа «не передан…»/«недоступ…»/
    # «отсутств…» и т.п.) отличает НАМЕРЕННЫЙ FAIL-отчёт от упоминания;
    # line-start сохраняет полную строгость (mid-line «Примечание:
    # zhivoy_yazyk_read: FAIL» выше в этом же списке, Д129, продолжает
    # блокировать - явный `FAIL` распознаётся). «Хорошая форма mid-line
    # закрывает мандат» (Д129а) не тронута - НЕ этот кейс.
    ("Д136 зеркало: mid-line ПЕРЕСКАЗ промпта прозой «Я напечатал строку "
     "donordev_read: как требует канон» - упоминание, не отчёт",
     "Я напечатал строку donordev_read: как требует канон.\n"
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    ("Д136 зеркало: mid-line перечисление обоих ключей прозой «Поля "
     "donordev_read: и zhivoy_yazyk_read: заполнены» - упоминание",
     "Поля donordev_read: и zhivoy_yazyk_read: заполнены.\n"
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    ("Д136 зеркало контроль line-start: бэктик-ключ С НАЧАЛА строки + "
     "нераспознанное значение остаётся FAIL (позиционный фильтр строгость "
     "с начала строки не снимает)",
     "`donordev_read`: назвал что-то невнятное без pass\n"
     "zhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д138 (скептик-раунд 47, по решению автора): `_READFLAG_EXPLICIT_BAD_RE`
    # не знала нормализованного «N/A» (слэш -> пробел даёт «n a», словарь
    # нёс только слитное «na») и канонных слов отказа «нет»/«нету»/«ок»/«ok»
    # (04-review.md:1005/1126/1127 называют их поимённо) - mid-line-
    # пересказ этими словами читался нераспознанным гарбажем, mid-line-
    # фильтр Д136 пропускал вхождение, честный `pass` рядом единолично
    # закрывал мандат. Полное обоснование - шапка `_READFLAG_EXPLICIT_
    # BAD_RE` в самом хуке.
    ("Д138 mid-line отказ «N/A» (нормализуется в «n a», слэш -> пробел) - "
     "блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: donordev_read: N/A - справочник приёмов не вложили\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    ("Д138 mid-line отказ «нет» - канонное слово отказа 04-review.md:1005 - "
     "блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: donordev_read: нет, справочник приёмов не открывал\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    ("Д138 mid-line отказ «нету» - блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: donordev_read: нету, забыл открыть\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    ("Д138 mid-line отказ «ок» - нелегальное значение 04-review.md:1126/1127 - "
     "блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: zhivoy_yazyk_read: ок, вроде всё нормально\n"
     "ВЕРДИКТ: PASS\n", "zhivoy_yazyk_read"),
    ("Д138 mid-line отказ «ok» (латиница) - блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: zhivoy_yazyk_read: ok, вроде всё нормально\n"
     "ВЕРДИКТ: PASS\n", "zhivoy_yazyk_read"),
    ("Д138 регресс line-start: голое «N/A» продолжает блокировать (Д127, "
     "не переоткрывается)",
     "donordev_read: N/A\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "donordev_read"),
    # --- 🔴 Д140 (скептик-раунд 48, по решению автора): ЗЕРКАЛО ПАТЧА У
    # `_DONORDEV_RE`/`_DEADLANG_RE` - `_READFLAG_RE` открывалась `\b` перед
    # ключом, ведущее markdown-подчёркивание («__donordev_read__:») не
    # матчилось вовсе (полное обоснование класса - шапка `_DONORDEV_D139_
    # D140_CASES` в run-tests.py / шапка `_DONORDEV_RE` в самом хуке).
    # Негативный контроль (приклеенное подчёркивание) держит защиту.
    ("Д140 __подчёркивание__ (CommonMark) - оба ключа честны, матчится "
     "(было MISSING_donordev_read, fail-closed)",
     "__donordev_read__: PASS\n__zhivoy_yazyk_read__: PASS\nВЕРДИКТ: PASS\n",
     None),
    ("Д140 негативный контроль: «слово_donordev_read:» слитно - НЕ ключ, "
     "MISSING_donordev_read держится",
     "слово_donordev_read: PASS\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n",
     "MISSING_donordev_read"),
    # --- 🔴 Д141 (скептик-раунд 48, по решению автора): `_READFLAG_RE` несёт
    # `re.I`, но `key = m.group(1)` хранился СЫРЫМ регистром - сверка с
    # `_READFLAG_KEYS` (строго нижним) давала ложный `MISSING_<ключ>` НА
    # ЧЕСТНОМ ответе верхним/смешанным регистром (петля исполнителя: BLOCK-
    # текст предписывает напечатать ровно то, что уже напечатано). Фикс -
    # `key = m.group(1).lower()`.
    ("Д141 регистр DONORDEV_READ (полностью верхний) честный - матчится "
     "(было MISSING_donordev_read, fail-open петля)",
     "DONORDEV_READ: PASS\nzhivoy_yazyk_read: PASS\nВЕРДИКТ: PASS\n", None),
    ("Д141 регистр Donordev_Read/Zhivoy_Yazyk_Read (смешанный) честный - "
     "матчится",
     "Donordev_Read: PASS\nZhivoy_Yazyk_Read: PASS\nВЕРДИКТ: PASS\n", None),
    ("Д141 регресс: DONORDEV_READ (верхний) с явным FAIL продолжает "
     "блокировать, состояние канонично нижним регистром ключа",
     "DONORDEV_READ: FAIL - справочник не передан\nzhivoy_yazyk_read: PASS\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д146-зеркало (регресс-фиксация, НЕ новый фикс, по решению автора): у
    # donor-devices §-ссылка ПЕРЕД словом отказа маскировала отказ ПОСЛЕ
    # стрелки-вердикта (см. DONORDEV_CASES выше) - у READFLAG хвост-отказ
    # ПОСЛЕ честного первого токена `pass` уже закрыт Д131б (раунд 44, кейс
    # выше «PASS с признанием-отказом в хвосте»): `_tail and
    # _DEADLANG_ADMIT_RE.search(_tail)` сканирует хвост НЕЗАВИСИМО от того,
    # каким словом отказ оформлен - позиция «после PASS» тут не открывает
    # обходной путь, в отличие от donor-devices. Кейс закрепляет уже-
    # корректное поведение другим глаголом отказа («не проверял» вместо «не
    # открывал»), не дублируя существующий кейс дословно.
    ("Д146-зеркало RF: «PASS, но не проверял» - хвост-отказ уже блокирует "
     "(Д131б, не новый фикс, страхует от регресса)",
     "donordev_read: PASS, но не проверял\nzhivoy_yazyk_read: PASS\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д147-зеркало RF (регресс-фиксация, НЕ новый фикс, скептик-раунд
    # 51, по решению автора): у DD/DL Д147 - START-словарь пропускал отказ-токен без
    # приставки «не» (голое «нет»/«ок»/«N/A»…) на начале сегмента ПОСЛЕ
    # стрелки. У READFLAG (`_readflag_state`) этот класс структурно НЕ живёт -
    # белый список Д127 (раунд 42) требует, чтобы нормализованное значение
    # было РОВНО словом `pass`, ЛЮБОЕ иное непустое значение (в т.ч. «PASS ->
    # нет» - после нормализации `passнет`, не равно `pass`) флагуется `FAIL`
    # по этому ключу fail-closed самим устройством белого списка, отдельного
    # арроу-сегментного разбора не требуется. Кейс закрепляет уже-корректное
    # поведение (не новый фикс).
    ("Д147-зеркало RF: «PASS -> нет» - белый список Д127 уже блокирует "
     "(значение не РОВНО «pass», не новый фикс, страхует от регресса)",
     "donordev_read: PASS -> нет\nzhivoy_yazyk_read: PASS\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
    # --- 🔴 Д166 зеркало RF (скептик-раунд 56, по решению автора, полное обоснование -
    # баннер Д166 в DONORDEV_CASES выше): «вложил\\w*» добавлена в
    # `_READFLAG_EXPLICIT_BAD_RE` зеркалом DD/DL - mid-line отказ «не вложили»
    # БЕЗ соседнего «N/A»-триггера (Д138 тестировал «N/A» рядом с «не вложили»,
    # где триггером был «N/A», а не сама лемма) читался нераспознанным гарбажем
    # и пропускался mid-line-фильтром Д136.
    ("Д166 RF mid-line отказ «не вложили» (без N/A рядом, зеркало Д138) - "
     "блокирует",
     "donordev_read: PASS\nzhivoy_yazyk_read: PASS\n"
     "Примечание: donordev_read: справочник приёмов не вложили\n"
     "ВЕРДИКТ: PASS\n", "donordev_read"),
]


def test_hook_readflag_gate():
    """🔴 Дефект-класс Д45/Д52/Д107 (третий+ рецидив, «дефекты без постоянного
    стража», см. шапку перед `_hook_readflag_ns` выше): у гейта READFLAG
    (`_readflag_state`, фиксы R42-R44) не было НИ ОДНОГО постоянного теста -
    слой жил только во временных `verify-FIX-R*.sh` scratchpad-сессии. Тест
    берёт ЖИВУЮ функцию (см. `_hook_readflag_state`) и прогоняет её по ВСЕМ
    состояниям `READFLAG_CASES`, ЗАТЕМ регрессирует по 3 опорных кейса
    donordev + 3 опорных кейса deadlang - подтверждает, что вставка нового
    блока по соседству не сдвинула экстракторы `_hook_donordev_ns`/
    `_hook_deadlang_ns` и не задела сами функции donordev/deadlang.

    🔴 Д47 (дисциплина этого файла, раунд 11): SKIP остаётся РОВНО на один
    случай - хука нет на диске (машина ученика). Любой другой отказ выреза -
    FAIL с честной причиной: сломанный вырез означает, что страж гейта не
    гоняет НИЧЕГО, и молчать об этом нельзя."""
    st, err = _hook_readflag_state()
    if err == "NOHOOK":
        skip("Д45/Д52/Д107 хук: гейт READFLAG (все состояния)",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if st is None:
        record("Д45/Д52/Д107 хук: гейт READFLAG - все состояния на ЖИВОЙ функции хука",
               False, err)
        return
    bad = []
    for name, text, want in READFLAG_CASES:
        got = st(text)
        if got != want:
            bad.append(f"{name}: ждём {want}, получили {got}")
    record("Д45/Д52/Д107 хук: гейт READFLAG - все состояния на ЖИВОЙ функции "
           "хука (%d кейсов)" % len(READFLAG_CASES), not bad, "; ".join(bad))

    # --- регресс: опорные donordev/deadlang-кейсы не задеты соседством ---
    dst, derr = _hook_donordev_state()
    if derr == "NOHOOK":
        skip("READFLAG регресс: опорные donordev-кейсы не задеты соседством",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
    elif dst is None:
        record("READFLAG регресс: опорные donordev-кейсы не задеты соседством",
               False, derr)
    else:
        _anchor_donordev = [
            ("штатный §N.M", "§2.3 смена системы отсчёта «цитата» -> PASS", "OK"),
            ("отказ «нет»", "нет", "NO"),
            ("литерал шаблона (Д29б)",
             "<§номер + название приёма> «<строка-улика поста>» -> PASS", "LITERAL"),
        ]
        dbad = []
        for name, val, want in _anchor_donordev:
            got = dst("донор-разбор\ndonor-devices: %s\nВЕРДИКТ: PASS\n" % val)
            if got != want:
                dbad.append(f"{name}: ждём {want}, получили {got}")
        record("READFLAG регресс: опорные donordev-кейсы не задеты соседством",
               not dbad, "; ".join(dbad))

    lst, lerr = _hook_deadlang_state()
    if lerr == "NOHOOK":
        skip("READFLAG регресс: опорные deadlang-кейсы не задеты соседством",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
    elif lst is None:
        record("READFLAG регресс: опорные deadlang-кейсы не задеты соседством",
               False, lerr)
    else:
        _anchor_deadlang = [
            ("чисто", "чисто", "OK"),
            ("N слов заменено, каноничная форма",
             "3 слов заменено · «мёртвое» -> «живая замена»", "OK"),
            ("отказ «не проверял»", "не проверял", "NO"),
        ]
        lbad = []
        for name, val, want in _anchor_deadlang:
            got = lst("живой-разбор\ndead-language: %s\nВЕРДИКТ: PASS\n" % val)
            if got != want:
                lbad.append(f"{name}: ждём {want}, получили {got}")
        record("READFLAG регресс: опорные deadlang-кейсы не задеты соседством",
               not lbad, "; ".join(lbad))


# ===========================================================================
# МАТРИЧНЫЙ СТРАЖ ТИПОГРАФИКИ (v2.4-r49/r50, скептик-раунды 45-48,
# по решению автора): постоянный класс-фикс поверх дефектов Д133-Д141.
#
# ИСТОРИЯ КЛАССА: раунды 45-48 нашли 10 дефектов ОДНОГО класса на трёх
# regex-парсерах строк-отчётов верификатора (`_donordev_state`/
# `_deadlang_state`/`_readflag_state`) - каждый фикс-раунд зеркалил ОДНУ ось
# обвязки ключа (бэктики Д137, ведущее подчёркивание Д140, словарь отказа
# Д138, line-start-детекция бэктик-ключа Д139...) и пропускал соседнюю,
# потому что рядом НЕ было теста, гоняющего ВСЮ матрицу (архетип значения x
# позиция x обвязка) СРАЗУ по трём слоям. Точечные `DONORDEV_CASES`/
# `DEADLANG_CASES`/`READFLAG_CASES` выше проверяют каждый гейт ПО ОТДЕЛЬНОСТИ
# и хорошо ловят РЕГРЕСС конкретного кейса - но НЕ ловят класс «слой A
# обновили под форму X, слой B забыли» ЗАРАНЕЕ, до того как скептик найдёт
# его глазами. Этот блок - постоянный страж именно КЛАССА, не инстанса:
# сгенерированная матрица десятков обвязок x архетипов x позиций x слоёв,
# один разлад в ЛЮБОЙ комбинации красит один из пяти тестов ниже.
#
# ДВА ИНВАРИАНТА (задача владельца, по решению автора):
#   Инвариант 1 (внутрислойный) - для каждого слоя состояние НЕ зависит от
#     типографики: для (архетип значения x позиция) ВСЕ обвязки ключа ИЗ
#     ПРОВЕРЯЕМОГО СПИСКА (`_MTX_ALL_WRAPPERS` ниже, сейчас 26 форм) дают
#     ТО ЖЕ состояние, что голая форма. 🔴 ЧЕСТНАЯ ГРАНИЦА (Д145, скептик-
# раунд 50, по решению автора): список - НЕ исчерпывающий реестр легальной
#     типографики, а РАСТУЩИЙ класс-фикс - формулировка «ВСЕ легальные
#     обвязки БЕЗ ИСКЛЮЧЕНИЙ», которую несла эта строка раньше, была
#     оверклеймом. Живой репро (`hunt_wrappers.py`, scratchpad r52): 33
#     кандидата типографики ВНЕ списка дали 103 расхождения с голой формой
#     (MISSING вместо NOREF/NO/LITERAL) - Д145 закрыл ИЗ них «+ буллет»,
#     «1) нумерация скобкой» (CommonMark-братья уже включённых `*`/`1.`) и
#     5 частотных символов-префиксов (✅🔴✓→●); heading (`###`/`####`)
#     НЕ включён НАРОЧНО - структурно не line-start по определению самого
#     хука (см. комментарий у `_MTX_WRAPPERS` ниже); двойной бэктик,
#     `~~зачёркнутый~~`, `<b>html</b>`, тире-буллеты (–/—/‣/·) остаются ВНЕ
#     списка - не части этого раунда, не проверены и не гарантированы.
#   Инвариант 2 (межслойный, паритет матчинга) - множество обвязок, при
#     которых ключ РАСПОЗНАЁТСЯ (матч есть, MISSING vs не-MISSING), одинаково
#     у всех трёх слоёв.
#
# АРХЕТИПЫ ЗНАЧЕНИЙ: HONEST (§-сигнатура у DD / «чисто» у DL / PASS у
# READFLAG) · REFUSAL (явный отказ словарём - «не сверял»/«не смотрел»,
# намеренно НОВЫЕ корни R50, не старые «не проверял», чтобы страж СРАЗУ
# проверял и класс, и конкретный фикс) · GARBAGE (мусор-проза, ключ
# упомянут, значение не опознаётся НИЧЕМ) · LITERAL (шаблон-плейсхолдер,
# где применимо - у DD/DL есть отдельное состояние LITERAL, у READFLAG
# «LITERAL» структурно другое - оба токена pass+fail разом, не сопоставимо
# построчно, поэтому не участвует в этом архетипе здесь).
#
# ПОЗИЦИИ: line-start (своя строка) · mid-line (после ЧЕСТНОЙ строки того
# же ключа - размен Р46: мусор мимоходом рядом с честным отчётом ДОЛЖЕН
# промолчать, иначе живой пересказ промпта прозой ложно блокирует ЛЮБОЙ
# честный ответ - см. докстринг `_donordev_looks_explicit` в хуке).
#
# ИМЕНОВАННЫЕ ИСКЛЮЧЕНИЯ (манифест, НЕ баг - причина у каждого):
#  (а) целиком-в-бэктиках «`ключ: значение`» ОДНОЙ парой = цитата канона,
#      не отчёт исполнителя (Д134) -> MISSING/MISSING_<ключ> у всех трёх,
#      мандат присутствия НЕ закрывается цитатой - размен назван в самом
#      хуке текстом BLOCK-сообщения.
#  (б) mid-line мусор-упоминание (ключ есть, значение НЕ опознаётся) ->
#      пропуск, честная строка рядом побеждает единолично (размен Р46,
#      названный в докстринге `_donordev_looks_explicit`/`_deadlang_looks_
#      explicit`/зеркала READFLAG) - иначе живой пересказ промпта прозой
#      ложно блокирует ЛЮБОЙ честный ответ.
#  (в) DD «значение ЦЕЛИКОМ в бэктиках» (ключ голый, всё значение одной
#      backtick-парой) -> NOREF, НЕ OK: `_donordev_strip_quoted` считает
#      backtick-пару закавыченным спаном и вырезает её вместе с §-ссылкой
#      ПЕРЕД поиском ref - DD-специфично (единственный слой, ищущий §-ref
#      ВНУТРИ значения); у DL/RF тот же приём честно проходит (нет ref-
#      поиска по остатку).
#  (г) pipe-таблица НЕ имеет mid-line формы - Markdown-таблица всегда своя
#      строка (`^[ \t]*\|`-якорь живёт в САМОЙ структуре regex'а, не в
#      позиционном фильтре); тест не пытается обернуть её прозой.
#
# 🔴 ФИКС Д142 (позиционный квирк, задача R51, по решению автора): БЫВШЕЕ
# исключение (д) БОЛЬШЕ НЕ исключение - починено, снято из манифеста.
# ДЕФЕКТ (найден стражем в раунде 49/R50, задокументирован «кандидат R51»):
# line-start GARBAGE/LITERAL через __подчёркивание__/_подчёркивание_/
# чекбокс-[x]/pipe-таблицу(+бэктик) на ИЗОЛИРОВАННОЙ строке давал MISSING
# вместо NOREF/NO/LITERAL - `_at_line_start()` в хуке звалась с `m.start()`
# ЦЕЛОГО матча, а ДВЕ разные причины давали один симптом: (1) у __ключ__/
# pipe-таблицы `m.start()` УЖЕ РАВЕН `line_start` (обвязка - часть тела
# матча целиком, лукэхед-гибрид Д141 у `_{1,2}`/`^`-якорь `_*_TABLE_RE`), а
# старый скан всё равно ЕХАЛ ВПЕРЁД и переезжал `pos`, давая ложный `False`
# на позиции, которая по построению и есть line-start; (2) у чекбокса
# `- [x]` префиксный класс не нёс `[`/`]`/`x`/`X`, скан останавливался
# РАНЬШЕ настоящего `pos`. ФИКС хука (`post-phase-gate.FIX-R51.sh`,
# применяет владелец) - `_at_line_start` возвращает `True` СРАЗУ, когда
# `pos == line_start` (диапазон пуст по построению, полное обоснование в
# докстринге функции в самом хуке), плюс `[`, `]`, `x`, `X` добавлены в
# ОБА префиксных класса (`_LINESTART_PREFIX_RE`/`_BT_RE`). Тест ниже
# (`test_matrix_typography_invariant`) больше НЕ несёт карве-аут для этих
# 5 обвязок - они проверяются ТЕМ ЖЕ инвариантом, что все остальные
# (`exp_ls = base_ls` без исключения), кейсы точного диагноза (NOREF/NO/
# key-FAIL вместо MISSING) участвуют в общей матрице напрямую. Регресс:
# mid-line упоминание тех же обвязок («Примечание: __donor-devices__:
# мусор») остаётся mid-line - реальная проза перед обвязкой блокирует скан
# кириллическими буквами, которых НЕТ в префиксном классе (размен Р46 не
# тронут, см. `test_matrix_typography_invariant` ниже - mid-line часть
# инварианта чиста).
#
# Тесты ЧИТАЮТ ЖИВУЮ функцию хука через уже существующие
# `_hook_donordev_state`/`_hook_deadlang_state`/`_hook_readflag_state`
# (см. их докстринги выше - тот же контракт NOHOOK=skip/иначе=FAIL с
# причиной), новых экстракторов не заводит.
# ===========================================================================

_MTX_V_DD = "§2.3 смена системы отсчёта «улика» -> PASS"
_MTX_HONEST = {"DD": _MTX_V_DD, "DL": "чисто", "RF": "PASS"}
# 🔴 DL-якорь для проверки словаря - ЧИСЛОВАЯ форма («N слов заменено»),
# НЕ «чисто»: у ветки «чисто» есть ОТДЕЛЬНЫЙ, НЕ словарный механизм
# `_deadlang_clean_admits_absence` (сканирует lead 300зн/tail 600зн вокруг
# «чисто» на предмет+отрицание СТРУКТУРНО, а не по словарю Д138) - он
# МАСКИРУЕТ дыры словаря отказа (был бы ложный «зелёный» даже БЕЗ R50-фикса
# на кейсах вроде «не смотрел»/«не нашёл», см. живой репро в финальном
# ответе исполнителя). Числовая форма этой страховки не несёт - проверка
# именно словаря, самая строгая из двух честных якорей DL.
_MTX_HONEST_DL_NUMERIC = '2 слов заменено "старое" -> "новое", "иное" -> "свежее"'
_MTX_KEY = {"DD": "donor-devices", "DL": "dead-language", "RF": "donordev_read"}
_MTX_RF_OTHER_KEY = "zhivoy_yazyk_read"
_MTX_GARBAGE = "какой-то текст мимоходом без всякого смысла"
_MTX_LITERAL = {
    "DD": "<§номер + название приёма> «<строка-улика поста>» -> PASS",
    "DL": "<мёртвое> -> <живая замена>",
}

# 18-19 обвязок ключа - переработка t3_forms.py (scratchpad r48s, 18 форм) +
# явные пункты ТЗ владельца (буллет •, ВЕРХНИЙ РЕГИСТР, буллет-| префикс).
# + 7 обвязок Д145 (раунд 50, по решению автора) - «+»/«1)» + 5 эмодзи-префиксов,
# итог 26 форм (`_MTX_ALL_WRAPPERS`) - список РАСТУЩИЙ, не исчерпывающий
# (честная граница - баннер-комментарий «ДВА ИНВАРИАНТА» выше).
# heading (### ключ) НЕ включена намеренно: `#` не входит в префиксный класс
# `_LINESTART_PREFIX_RE`/`_BT_RE` вовсе - форма структурно НЕ line-start по
# определению самого хука, тестировать её как "должна быть line-start" было
# бы проверкой выдуманного требования, не реального контракта.
_MTX_WRAPPERS = [
    ("голый ключ", lambda k, v: "%s: %s" % (k, v)),
    ("бэктик-ключ", lambda k, v: "`%s`: %s" % (k, v)),
    ("**жирный**", lambda k, v: "**%s**: %s" % (k, v)),
    ("**жирный:**", lambda k, v: "**%s:** %s" % (k, v)),
    ("*курсив*", lambda k, v: "*%s*: %s" % (k, v)),
    ("__двойное_подчёркивание__", lambda k, v: "__%s__: %s" % (k, v)),
    ("_одиночное_подчёркивание_", lambda k, v: "_%s_: %s" % (k, v)),
    ("ВЕРХНИЙ РЕГИСТР", lambda k, v: "%s: %s" % (k.upper(), v)),
    ("буллет -", lambda k, v: "- %s: %s" % (k, v)),
    ("буллет *", lambda k, v: "* %s: %s" % (k, v)),
    ("буллет >", lambda k, v: "> %s: %s" % (k, v)),
    ("буллет •", lambda k, v: "• %s: %s" % (k, v)),
    ("буллет 1.", lambda k, v: "1. %s: %s" % (k, v)),
    ("буллет | (префикс)", lambda k, v: "| %s: %s" % (k, v)),
    ("чекбокс - [x]", lambda k, v: "- [x] %s: %s" % (k, v)),
    ("буллет+бэктик", lambda k, v: "- `%s`: %s" % (k, v)),
    ("буллет+жирный+бэктик", lambda k, v: "- **`%s`**: %s" % (k, v)),
    # 🔴 ФИКС Д145 (скептик-раунд 50, по решению автора): 7 обвязок, найденных
    # `hunt_wrappers.py` (scratchpad r52) вне списка 19 - CommonMark-братья
    # уже включённых `*`/`1.` («+ ключ:», «1) ключ:») плюс 5 частотных
    # эмодзи/символов-префиксов (✅🔴✓→●), которые автор реально пишет в
    # отчётах. Хук чинится ЗЕРКАЛЬНО (патч `post-phase-gate.FIX-R52.sh`,
    # применяет владелец) - `_LINESTART_PREFIX_RE`/`_LINESTART_PREFIX_BT_RE`
    # несут те же 7 символов классом `+`/`)`/эмодзи-перечисление, БЕЗ
    # букв/кириллицы (иначе mid-line-фильтр Р46 сломался бы - «Примечание:
    # ключ...» обязан остаться mid-line).
    ("буллет +", lambda k, v: "+ %s: %s" % (k, v)),
    ("нумерация 1)", lambda k, v: "1) %s: %s" % (k, v)),
    ("эмодзи ✅", lambda k, v: "✅ %s: %s" % (k, v)),
    ("эмодзи 🔴", lambda k, v: "🔴 %s: %s" % (k, v)),
    ("галка ✓", lambda k, v: "✓ %s: %s" % (k, v)),
    ("стрелка →", lambda k, v: "→ %s: %s" % (k, v)),
    ("буллет ●", lambda k, v: "● %s: %s" % (k, v)),
]
_MTX_TABLE_WRAPPERS = [
    ("pipe-таблица", lambda k, v: "| %s | %s |" % (k, v)),
    ("pipe-таблица+бэктик", lambda k, v: "| `%s` | %s |" % (k, v)),
]
_MTX_ALL_WRAPPERS = _MTX_WRAPPERS + _MTX_TABLE_WRAPPERS

# 🔴 Д142: карве-аут "именованного исключения (д)" убран отсюда - __ключ__/
# _ключ_/чекбокс-[x]/pipe-таблицу(+бэктик) больше не проверяются отдельным
# ожиданием MISSING, они идут через ТОТ ЖЕ `base_ls`, что все остальные
# обвязки (см. `test_matrix_typography_invariant` ниже). Прежние константы
# `_MTX_QUIRK_WRAPPERS`/`_MTX_QUIRK_MISSING` удалены как мёртвый код.


def _mtx_dd_body(text_line, midline=False):
    if midline:
        return ("donor-devices: %s\n" % _MTX_V_DD +
                "dead-language: чисто\ndonordev_read: PASS\nzhivoy_yazyk_read: PASS\n" +
                "Примечание: " + text_line + "\nВЕРДИКТ: PASS\n")
    return text_line + "\nВЕРДИКТ: PASS\n"


def _mtx_dl_body(text_line, midline=False, anchor="чисто"):
    if midline:
        return ("dead-language: %s\n" % anchor +
                "donor-devices: %s\ndonordev_read: PASS\nzhivoy_yazyk_read: PASS\n" % _MTX_V_DD +
                "Примечание: " + text_line + "\nВЕРДИКТ: PASS\n")
    return text_line + "\nВЕРДИКТ: PASS\n"


def _mtx_rf_body(text_line, midline=False):
    other = "%s: PASS\n" % _MTX_RF_OTHER_KEY
    if midline:
        return ("%s: PASS\n" % _MTX_KEY["RF"] + other +
                "Примечание: " + text_line + "\nВЕРДИКТ: PASS\n")
    return text_line + "\n" + other + "ВЕРДИКТ: PASS\n"


_MTX_BODY = {"DD": _mtx_dd_body, "DL": _mtx_dl_body, "RF": _mtx_rf_body}

_MTX_DD_LS = {"HONEST": "OK", "REFUSAL": "NO", "GARBAGE": "NOREF", "LITERAL": "LITERAL"}
_MTX_DD_ML = {"HONEST": "OK", "REFUSAL": "NO", "GARBAGE": "OK", "LITERAL": "OK"}
_MTX_DL_LS = {"HONEST": "OK", "REFUSAL": "NO", "GARBAGE": "NO", "LITERAL": "LITERAL"}
_MTX_DL_ML = {"HONEST": "OK", "REFUSAL": "NO", "GARBAGE": "OK", "LITERAL": "OK"}
_MTX_RF_LS = {"HONEST": None, "REFUSAL": _MTX_KEY["RF"], "GARBAGE": _MTX_KEY["RF"]}
_MTX_RF_ML = {"HONEST": None, "REFUSAL": _MTX_KEY["RF"], "GARBAGE": None}
_MTX_EXPECT_LS = {"DD": _MTX_DD_LS, "DL": _MTX_DL_LS, "RF": _MTX_RF_LS}
_MTX_EXPECT_ML = {"DD": _MTX_DD_ML, "DL": _MTX_DL_ML, "RF": _MTX_RF_ML}

_MTX_REFUSAL_WORDS_TYPO = ["не сверял", "не смотрел"]


def _mtx_fns():
    """Три живые функции хука (fn, ошибка) x 3 - единая точка сбора для
    всех тестов матрицы ниже, тот же NOHOOK/FAIL-контракт что у соседей."""
    dd, dderr = _hook_donordev_state()
    dl, dlerr = _hook_deadlang_state()
    rf, rferr = _hook_readflag_state()
    return {"DD": (dd, dderr), "DL": (dl, dlerr), "RF": (rf, rferr)}


def test_matrix_typography_invariant():
    """🔴 МАТРИЧНЫЙ СТРАЖ, Инвариант 1 (задача владельца, класс-
    фикс поверх Д133-Д141; Д142 - позиционный квирк R51 закрыл последнее
    именованное исключение этого теста, по решению автора; Д145 - скептик-раунд
    50, по решению автора, добавил 7 обвязок и починил формулировку ниже - полное
    обоснование границы списка в баннер-комментарии «ДВА ИНВАРИАНТА» выше
    этого блока): для (слой x архетип x позиция) ВСЕ обвязки ключа ИЗ
    ПРОВЕРЯЕМОГО СПИСКА (`_MTX_ALL_WRAPPERS`, сейчас 26 форм) дают ТО ЖЕ
    состояние, что голая форма. 🔴 ЧЕСТНО: список - растущий класс-фикс, не
    реестр всей легальной типографики (раньше здесь стояло «ВСЕ легальные
    обвязки… БЕЗ ИСКЛЮЧЕНИЙ» - оверклейм, Д145 его снял; `hunt_wrappers.py`
    в scratchpad r52 держит живой список кандидатов ВНЕ текущего списка,
    ещё не проверенных и не гарантированных этим тестом). 4 архетипа
    (HONEST/2xREFUSAL-новых-корня-R50/GARBAGE/LITERAL-где-применимо) x 26
    обвязок x 2 позиции x 3 слоя. До Д142 __двойное_подчёркивание__/
    _одиночное_подчёркивание_/чекбокс-[x]/pipe-таблица(+бэктик) несли
    карве-аут «GARBAGE/LITERAL на line-start ожидаемо MISSING» (баг
    `_at_line_start`, не контракт) - фикс хука закрыл ПРИЧИНУ, карве-аут
    снят, эти 5 обвязок теперь проверяются ТЕМ ЖЕ `base_ls`, что и все
    остальные (NOREF/NO/key-FAIL, ТОЧНЫЙ диагноз). Мутационно проверено
    (scratchpad r50/r51): убрать бэктик из префиксного класса, ИЛИ
    откатить корень «свер» у DD, ИЛИ откатить Д142 (вернуть `m.end() ==
    pos` без ранней проверки `pos == line_start` и без `[`/`]`/`x`/`X` в
    классе) - тест краснеет ТОЧНО на затронутых комбинациях, не молчит."""
    fns = _mtx_fns()
    for layer in ("DD", "DL", "RF"):
        fn, err = fns[layer]
        if err == "NOHOOK":
            skip("матричный страж (Инвариант 1): %s" % layer,
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
        if fn is None:
            record("матричный страж (Инвариант 1): %s - функция не вырезалась" % layer,
                   False, err)
            return
    bad = []
    n = 0
    for layer in ("DD", "DL", "RF"):
        fn = fns[layer][0]
        archetypes = ([("HONEST", _MTX_HONEST[layer])] +
                      [("REFUSAL", w) for w in _MTX_REFUSAL_WORDS_TYPO] +
                      [("GARBAGE", _MTX_GARBAGE)] +
                      ([("LITERAL", _MTX_LITERAL[layer])] if layer in _MTX_LITERAL else []))
        for aname, value in archetypes:
            base_ls = _MTX_EXPECT_LS[layer].get(aname)
            base_ml = _MTX_EXPECT_ML[layer].get(aname)
            for wname, wfn in _MTX_ALL_WRAPPERS:
                is_table = wname in ("pipe-таблица", "pipe-таблица+бэктик")
                line = wfn(_MTX_KEY[layer], value)
                exp_ls = base_ls    # Д142: без карве-аута, все обвязки равны
                got_ls = fn(_MTX_BODY[layer](line, midline=False))
                n += 1
                if got_ls != exp_ls:
                    bad.append("%s/%s/%s/line-start: ждём %r, получили %r"
                               % (layer, aname, wname, exp_ls, got_ls))
                if is_table:
                    continue
                got_ml = fn(_MTX_BODY[layer](line, midline=True))
                n += 1
                if got_ml != base_ml:
                    bad.append("%s/%s/%s/mid-line: ждём %r, получили %r"
                               % (layer, aname, wname, base_ml, got_ml))
    record("матричный страж: Инвариант 1 - типографика не меняет состояние "
           "(%d проверок)" % n, not bad, "; ".join(bad[:12]))


def _mtx_recognized(layer, state):
    if layer == "RF":
        return not (isinstance(state, str) and state.startswith("MISSING"))
    return state != "MISSING"


def test_matrix_recognition_parity():
    """🔴 МАТРИЧНЫЙ СТРАЖ, Инвариант 2 (задача владельца):
    множество обвязок, при которых ключ РАСПОЗНАЁТСЯ (матч есть - не
    MISSING/MISSING_<ключ>), одинаково у всех трёх слоёв. pipe-форма
    проверена живьём у ВСЕХ ТРЁХ слоёв (не только DD/DL, как предполагала
    исходная гипотеза задачи - `_READFLAG_TABLE_RE` существует и реально
    гоняется `_readflag_state`, живой репро в финальном ответе исполнителя) -
    если распознавание разъедется в будущем правкой ОДНОГО слоя, тест
    покраснеет здесь, а не через N раундов скептика."""
    fns = _mtx_fns()
    for layer in ("DD", "DL", "RF"):
        fn, err = fns[layer]
        if err == "NOHOOK":
            skip("матричный страж (Инвариант 2): %s" % layer,
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
        if fn is None:
            record("матричный страж (Инвариант 2): %s - функция не вырезалась" % layer,
                   False, err)
            return
    bad = []
    n = 0
    for wname, wfn in _MTX_ALL_WRAPPERS:
        rec = {}
        for layer in ("DD", "DL", "RF"):
            line = wfn(_MTX_KEY[layer], _MTX_HONEST[layer])
            got = fns[layer][0](_MTX_BODY[layer](line, midline=False))
            rec[layer] = _mtx_recognized(layer, got)
        n += 1
        if len(set(rec.values())) != 1:
            bad.append("%s: распознавание расходится %r" % (wname, rec))
    record("матричный страж: Инвариант 2 - паритет распознавания обвязки "
           "между DD/DL/RF (%d обвязок)" % n, not bad, "; ".join(bad))


def _mtx_split_top_level(pat):
    """🔴 Д144 (скептик-раунд 50, по решению автора), кирпич 1/5 экстрактора: делит
    regex-паттерн на альтернативы `A|B|C` СТРОГО на верхнем уровне
    скобочной вложенности - `|` внутри `(?:...)` разделителем не считается.
    Полное обоснование, зачем экстрактор вообще нужен (а не ручная копия
    словаря) - докстринг `_mtx_extract_refusal_probes` ниже."""
    parts, depth, buf = [], 0, ""
    for c in pat:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == "|" and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += c
    parts.append(buf)
    return parts


def _mtx_strip_regex_anchors(s):
    """Кирпич 2/5: снимает `^`/`\\b` с краёв альтернативы - позиционные и
    словограничные якоря не часть слова-корня."""
    for a in (r"\b", "^"):
        if s.startswith(a):
            s = s[len(a):]
    for a in (r"\b", "$"):
        if s.endswith(a):
            s = s[:-len(a)]
    return s


def _mtx_unwrap_pure_group(alt):
    """Кирпич 3/5: если альтернатива ЦЕЛИКОМ - один `(?:...)` (после снятия
    якорей, форма `^(?:тут|весь|словарь)\\b`, какую несут `_*_NO_START_RE`),
    возвращает содержимое для повторного верхнеуровневого разбора, иначе
    `None`."""
    s = _mtx_strip_regex_anchors(alt.strip())
    if s.startswith("(?:") and s.endswith(")"):
        return s[3:-1]
    return None


def _mtx_expand_nested_group(alt):
    """Кирпич 4/5: раскрывает ОДНУ вложенную группу `(?:a|b|c)` ИЛИ один
    простой буквенный класс `[её]` внутри альтернативы в список конкретных
    вариантов - нужно для `наш(?:[её]л|ла|ли|ло)\\w*` (форма ПОСЛЕ фикса
    Д143, скептик-раунд 50, по решению автора): без раскрытия ГРУППЫ экстрактор
    увидел бы только голое «наш», а хук НАРОЧНО его не ловит (искл.
    притяжательное «наш»/«наша»/«нашего», см. комментарий у
    `_DONORDEV_NO_START_RE` в хуке) - раскрытие группы обязано дать
    «[её]л»/«ла»/«ли»/«ло». Без раскрытия ВЛОЖЕННОГО КЛАССА `[её]` (второй
    `re.search` ниже) экстрактор дальше произвёл бы мусорную пробу
    «наш[её]л» буквально с квадратными скобками вместо ДВУХ раздельных проб
    «нашёл»/«нашел» - живой репро дыры и её фикса: scratchpad r52,
    `extractor_verify.py` (0 несовпадений ПОСЛЕ, 8 несовпадений с диагнозом
    «наш[её]л» ДО этого второго `re.search`)."""
    m = re.search(r"\(\?:([^()]*)\)", alt)
    if m:
        out = []
        for inner_alt in m.group(1).split("|"):
            out.extend(_mtx_expand_nested_group(alt[:m.start()] + inner_alt + alt[m.end():]))
        return out
    m = re.search(r"\[([а-яА-ЯёЁa-zA-Z]{2,6})\]", alt)
    if m:
        out = []
        for ch in m.group(1):
            out.extend(_mtx_expand_nested_group(alt[:m.start()] + ch + alt[m.end():]))
        return out
    return [alt]


def _mtx_alt_to_probe(s):
    """Кирпич 5/5: regex-альтернатива -> конкретная строка, которую эта
    альтернатива гарантированно матчит (`\\w*`/`\\s*` -> пусто, `\\s+` ->
    пробел, `/?` -> `/`, `\\w+` -> заполнитель «x»)."""
    s = s.replace(r"\s+", " ").replace(r"\s*", "")
    s = s.replace(r"\w*", "").replace(r"\w+", "x")
    s = s.replace("/?", "/")
    s = _mtx_strip_regex_anchors(s).replace(r"\b", "")
    return s.strip()


def _mtx_extract_refusal_probes(*pattern_texts):
    """🔴 ФИКС Д144 (скептик-раунд 50, СТРАЖ-СЛЕПОТА, по решению автора): ЖИВОЙ
    экстрактор словаря отказа - ходит по ТЕКСТУ переданных живых
    regex-паттернов хука (`.pattern`, тот же вырез из диска, что несут
    `_hook_donordev_ns`/`_hook_deadlang_ns`/`_hook_readflag_ns` выше - не по
    ручной константе), раскрывает верхнеуровневую альтернацию и вложенные
    `(?:a|b|c)`-группы (кирпичи 1-5 выше), конвертирует каждый лист в
    конкретную пробную строку и добавляет ё/е-двойника КАЖДОЙ пробе, где
    попалась ё (универсально - закрывает КЛАСС Д143, не только корень
    «наш»: если завтра в словарь добавят ЛЮБОЙ новый корень с ё, проба на
    него сгенерируется сама, без правки этой функции).

    ДЕФЕКТ Д144 (найден при закрытии Д143): ЗАКОН докстринга
    `_hook_donordev_ns` выше - «копия рассинхронится в первый же раунд
    правок, тестов не было ВООБЩЕ» - для словаря ОТКАЗА был нарушен тем же
    способом: `_MTX_REFUSAL_DICTIONARY` была РУЧНОЙ константой из 11 слов,
    а живых корней в пяти regex'ах отказа (`_DONORDEV_NO_START_RE`/
    `_PHRASE_RE`, `_DEADLANG_NO_START_RE`/`_PHRASE_RE`,
    `_READFLAG_EXPLICIT_BAD_RE`) - 16 (примен/опознан/провер/чита/
    прочитан/свер/смотр/наш/найден/вложен/передан/доступ/недоступ/
    отсутств/нет/справочник); 8 из них тест не гонял НИКОГДА. Когда Р50
    добавил в хук корень «наш» ТОЛЬКО ё-формой (`наш(?:ёл|ла|ли|ло)`, без
    «нашел»), страж этого не заметил ни в одном раунде - Д143 (fail-open
    обход через «не нашел» без ё) пережил раунды 50-51 незамеченным именно
    тестом, человек нашёл его руками. ФИКС: тест больше не хранит копию,
    он ЧИТАЕТ словарь из хука на каждый прогон - рассинхрон физически
    невозможен, а не «замечен позже». Мутационно проверено (scratchpad
    r52/rt-mut-d144.log): убрать корень из ЖИВОГО regex'а хука -> эта
    функция перестаёт генерировать его пробу -> счётчик проверок в имени
    теста падает и/или связанные пробы пропадают - красный тест НАЗЫВАЕТ
    пропавший корень, не молчит."""
    probes = set()
    for pat in pattern_texts:
        leaves = []
        for alt in _mtx_split_top_level(pat):
            inner = _mtx_unwrap_pure_group(alt)
            leaves.extend(_mtx_split_top_level(inner) if inner is not None else [alt])
        for leaf in leaves:
            leaf = _mtx_strip_regex_anchors(leaf.strip())
            if not leaf:
                continue
            has_ne = leaf.startswith(r"не\s+")
            body = leaf[len(r"не\s+"):] if has_ne else leaf
            for variant in _mtx_expand_nested_group(body):
                probe = _mtx_alt_to_probe(variant)
                if not probe or not re.search(r"[а-яa-z]", probe, re.I):
                    continue
                full = ("не " + probe) if has_ne else probe
                probes.add(full)
                if "ё" in full:
                    probes.add(full.replace("ё", "е"))
    return sorted(probes)


# 🔴 Д144 (мутационная страховка, скептик-раунд 50, по решению автора): МИНИМУМ
# корней на слой - НЕ словарь (слова живьём извлекаются
# `_mtx_extract_refusal_probes`, эта константа их не хранит и не
# копирует), а голое ЧИСЛО - последний рубеж против мутации «корень тихо
# убрали из ВСЕХ regex'ов». Полное обоснование - докстринг
# `test_matrix_refusal_dictionary_coverage` ниже. Зафиксировано на числах
# закрытия Д144 (по решению автора, ПОСЛЕ фикса Д143 - «наш» несёт е/ё-двойника,
# поэтому DD/DL/RF на 1 корень больше, чем считал `dict_drift.py` ДО
# фикса).
# 🔴 Д158 (по решению автора): DD 27 -> 28 - вторая альтернатива `ни\s+одн\w*`
# (косвенные падежи «ни один», раунд `ФИКСЫ Р53`) даёт РОВНО одну новую
# пробу («ни одн», проверено живым экстрактором, scratchpad r57/
# probe_count.py: ДО 27/23/22, ПОСЛЕ 28/23/22 - DL/RF не задеты, корень
# «ни один» они не несли ни в одной форме). Число - `len()` живого
# извлечения на патченной копии, не рука.
# 🔴 Д159 (скептик-раунд 54, по решению автора, патч R58): DD 28 -> 31 - три новые
# альтернативы `ничего|ничто|никак\w*` (родственники «ни один»/«ни одн\w*»,
# отсутствовали ни в одной форме) дают РОВНО три новые пробы («ничего»/
# «ничто»/«никак»), проверено живым экстрактором на патченной копии
# (scratchpad r58/verify-FIX-R58.output.log). DL/RF не задеты (23/22 как
# были - грепом подтверждено, ни один из трёх корней им не свойственен).
# Число - `len()` живого извлечения, не рука.
# 🔴 Д166+Д167 (скептик-раунд 56, по решению автора, патч R60): DD 31 -> 40 (9 новых
# проб), DL 23 -> 24 (1 новая проба), RF 22 -> 23 (1 новая проба). Д166 -
# «опознал»/«вложил» добавлены в `_DONORDEV_NO_START_RE`+`_PHRASE_RE` (2 леммы,
# но экстрактор даёт РОВНО 2 новые пробы «не опознал»/«не вложил» - START и
# PHRASE несут ОДИНАКОВЫЙ текст леммы, дедуп множеством), «вложил» зеркалом в
# `_DEADLANG_NO_START_RE`+`_PHRASE_RE` (1 проба) и `_READFLAG_EXPLICIT_BAD_RE`
# (1 проба) - «опознал» НЕ несут DL/RF (домен идентификации техники донора, не
# dead-language/*_read). Д167 - 7 новых проб ТОЛЬКО в `_DONORDEV_NO_PHRASE_RE`
# (`подош`/`подойд`/`подходит`/`подходят`/`подходил`/`совпад`/`совпал`), leммы
# взяты из уже евиденцированного `_DONORDEV_SUBJECT_RE` (Д160/Д164) - `сработ`/
# `срабатыва` НАРОЧНО не перенесены (живой репро на Д153б доказал ложный BLOCK
# «анти-паттерн не сработал», полное обоснование - баннер Д167 в
# DONORDEV_CASES). DD 31+9=40, DL 23+1=24, RF 22+1=23. Проверено живым
# экстрактором на патченной копии (scratchpad r60/probe_fix_design.py вывод +
# прямой прогон `_mtx_extract_refusal_probes` на WORKCOPY, 0 расхождений с
# ручным подсчётом). Число - `len()` живого извлечения, не рука.
_MTX_REFUSAL_FLOOR = {"DD": 40, "DL": 24, "RF": 23}


def test_matrix_refusal_dictionary_coverage():
    """🔴 МАТРИЧНЫЙ СТРАЖ: покрытие словаря отказа (Часть 2 задачи владельца
     - «кейсы R50 в матричный страж»; ПЕРЕСОБРАН Д144, скептик-
    раунд 50, по решению автора - живое извлечение вместо ручной константы, полное
    обоснование - докстринг `_mtx_extract_refusal_probes` выше). Каждый
    корень, который ЖИВЫЕ regex'ы отказа хука РЕАЛЬНО несут сейчас (не
    список, который кто-то может забыть переписать), даёт ОДИНАКОВОЕ
    распознавание словарём у своего слоя - на ОБЕИХ позициях (line-start И
    mid-line, а не только mid-line, как было ДО Д144): у DD line-start
    различает словарный `NO` от catch-all `NOREF` (см.
    `test_matrix_recognition_parity` рядом), дыра словаря видна и там -
    старая версия проверяла только менее строгий mid-line-канал. У DL/RF
    line-start НЕ различает «распознано словарём» от «неопознанный гарбаж»
    по конструкции (оба ветвятся в тот же catch-all) - проверка там не
    молчит, просто менее чувствительна, тот же контракт `_MTX_EXPECT_LS`,
    что несёт `test_matrix_typography_invariant`. У DL честный якорь -
    ЧИСЛОВАЯ форма (`_MTX_HONEST_DL_NUMERIC`): ветка «чисто» несёт
    ОТДЕЛЬНЫЙ структурный механизм `_deadlang_clean_admits_absence`,
    который маскирует дыры словаря - числовая форма его не несёт, самая
    строгая проверка.

    🔴 ДОБАВЛЕНО ПРИ ЗАКРЫТИИ Д144 (мутационная проверка живьём, scratchpad
    r52/mut_d144.py + rt-mut-d144.log): ЧИСТОЕ живое извлечение слепо к
    УДАЛЕНИЮ корня - убери корень «свер» из ВСЕХ ПЯТИ regex'ов отказа, и
    экстрактор просто перестаёт его извлекать, тест как ни в чём не бывало
    зеленеет на МЕНЬШЕМ множестве проб (живой репро: тест ПРОШЁЛ на
    мутанте без «свер» - DD 26/DL 22/RF 21 корней вместо 27/23/22, ни
    единого предупреждения). Живое извлечение чинит СТАРУЮ болезнь
    (список не растёт вместе с regex'ом), но само по себе не чинит НОВУЮ
    (список может тихо УСОХНУТЬ вместе с regex'ом). Фикс - `_MTX_REFUSAL_
    FLOOR` ниже: минимальное число корней на слой, зафиксированное на
    момент закрытия Д144 (27/23/22). Рост (добавили корень) проходит БЕЗ
    правки floor - `>=`, не `==`. Падение ниже floor - тест красный С ИМЕНЕМ
    слоя и числами (было/стало), даже если экстрактор не считает потерю
    расхождением. Понижать floor МОЖНО, только осознанным изменением ЭТОЙ
    же строки в ТОМ ЖЕ коммите, что убирает корень из хука намеренно - не
    авто-подстройкой под упавший тест."""
    fns = _mtx_fns()
    for layer in ("DD", "DL", "RF"):
        fn, err = fns[layer]
        if err == "NOHOOK":
            skip("матричный страж (словарь отказа): %s" % layer,
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
        if fn is None:
            record("матричный страж (словарь отказа): %s - функция не вырезалась" % layer,
                   False, err)
            return
    dd, dl, rf = fns["DD"][0], fns["DL"][0], fns["RF"][0]
    # Живые namespace'ы - тот же вырез, что _mtx_fns() уже дёрнул через
    # _hook_*_state() выше (err уже проверены), берём их ЕЩЁ раз только за
    # .pattern regex'ов - функцию извлечения переиспользовать нельзя, она
    # возвращает готовую функцию state, не сырой namespace.
    ns_dd, _ = _hook_donordev_ns()
    ns_dl, _ = _hook_deadlang_ns()
    ns_rf, _ = _hook_readflag_ns()

    dd_probes = _mtx_extract_refusal_probes(ns_dd["_DONORDEV_NO_START_RE"].pattern,
                                             ns_dd["_DONORDEV_NO_PHRASE_RE"].pattern)
    dl_probes = _mtx_extract_refusal_probes(ns_dl["_DEADLANG_NO_START_RE"].pattern,
                                             ns_dl["_DEADLANG_NO_PHRASE_RE"].pattern)
    rf_probes = _mtx_extract_refusal_probes(ns_rf["_READFLAG_EXPLICIT_BAD_RE"].pattern)

    bad = []
    n = 0
    # 🔴 Д144 мутационная страховка - ПЕРВЫМ делом, ДО прогона проб: живое
    # извлечение само по себе слепо к УДАЛЕНИЮ корня (см. докстринг выше и
    # `_MTX_REFUSAL_FLOOR`) - если корней меньше зафиксированного минимума,
    # тест обязан назвать ЭТО отдельной строкой, даже если каждая
    # оставшаяся проба сама по себе честно проходит.
    for layer, probes in (("DD", dd_probes), ("DL", dl_probes), ("RF", rf_probes)):
        floor = _MTX_REFUSAL_FLOOR[layer]
        if len(probes) < floor:
            bad.append("%s: корней в живом словаре %d < минимума %d - корень(и) исчезли "
                       "из regex'а отказа (мутация/регресс, не расширение)"
                       % (layer, len(probes), floor))
    for word in dd_probes:
        for midline in (False, True):
            n += 1
            got = dd(_mtx_dd_body("donor-devices: %s" % word, midline=midline))
            exp = (_MTX_EXPECT_ML if midline else _MTX_EXPECT_LS)["DD"]["REFUSAL"]
            if got != exp:
                bad.append("DD %s %r: ждём %r, получили %r"
                           % ("mid-line" if midline else "line-start", word, exp, got))
    for word in dl_probes:
        for midline in (False, True):
            n += 1
            got = dl(_mtx_dl_body("dead-language: %s" % word, midline=midline,
                                  anchor=_MTX_HONEST_DL_NUMERIC))
            exp = (_MTX_EXPECT_ML if midline else _MTX_EXPECT_LS)["DL"]["REFUSAL"]
            if got != exp:
                bad.append("DL %s %r: ждём %r, получили %r"
                           % ("mid-line" if midline else "line-start", word, exp, got))
    for word in rf_probes:
        for midline in (False, True):
            n += 1
            got = rf(_mtx_rf_body("donordev_read: %s" % word, midline=midline))
            exp = (_MTX_EXPECT_ML if midline else _MTX_EXPECT_LS)["RF"]["REFUSAL"]
            if got != exp:
                bad.append("RF %s %r: ждём %r, получили %r"
                           % ("mid-line" if midline else "line-start", word, exp, got))
    record("матричный страж: покрытие словаря отказа (живое извлечение, "
           "DD %d/DL %d/RF %d корней x 2 позиции, %d проверок)"
           % (len(dd_probes), len(dl_probes), len(rf_probes), n),
           not bad, "; ".join(bad[:12]))


def test_matrix_named_exceptions():
    """🔴 МАТРИЧНЫЙ СТРАЖ: манифест именованных исключений КАК КОД (не
    только текст в шапке блока) - официально задокументированная
    типографская цена красит тест, если её поведение вдруг изменится (тоже
    регресс, просто в другую сторону - молчаливое ИСЧЕЗНОВЕНИЕ размена так
    же стоит заметить, как его появление).

    (Д134) целиком-в-бэктиках «`ключ: значение`» ОДНОЙ парой = цитата
    канона -> MISSING/MISSING_<ключ> у ВСЕХ трёх, мандат не закрыт цитатой.

    (strip_quoted-цена) DD «значение ЦЕЛИКОМ в бэктиках» (ключ голый) ->
    NOREF: `_donordev_strip_quoted` вырезает backtick-пару вместе с §-
    ссылкой внутри ПЕРЕД ref-поиском - DD-специфично (единственный слой с
    ref-поиском по остатку значения); DL/RF та же обвязка -> честный
    OK/None (контроль, НЕ исключение)."""
    fns = _mtx_fns()
    for layer in ("DD", "DL", "RF"):
        fn, err = fns[layer]
        if err == "NOHOOK":
            skip("матричный страж (именованные исключения): %s" % layer,
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
        if fn is None:
            record("матричный страж (именованные исключения): %s - функция не вырезалась"
                   % layer, False, err)
            return
    bad = []
    for layer, keyname, val in (("DD", "donor-devices", _MTX_V_DD),
                                ("DL", "dead-language", "чисто"),
                                ("RF", "donordev_read", "PASS")):
        line = "`%s: %s`" % (keyname, val)
        got = fns[layer][0](_MTX_BODY[layer](line, midline=False))
        want = "MISSING" if layer != "RF" else "MISSING_donordev_read"
        if got != want:
            bad.append("Д134-цитата %s: ждём %r, получили %r" % (layer, want, got))
    got = fns["DD"][0](_mtx_dd_body("donor-devices: `%s`" % _MTX_V_DD, midline=False))
    if got != "NOREF":
        bad.append("DD значение-в-бэктиках: ждём NOREF, получили %r" % got)
    got = fns["DL"][0](_mtx_dl_body("dead-language: `чисто`", midline=False))
    if got != "OK":
        bad.append("DL значение-в-бэктиках (контроль): ждём OK, получили %r" % got)
    got = fns["RF"][0](_mtx_rf_body("donordev_read: `PASS`", midline=False))
    if got is not None:
        bad.append("RF значение-в-бэктиках (контроль): ждём None, получили %r" % got)
    record("матричный страж: манифест именованных исключений (Д134-цитата "
           "x3 + DD strip_quoted-цена + 2 контроля)", not bad, "; ".join(bad))


def test_matrix_compact_line_regression():
    """🔴 МАТРИЧНЫЙ СТРАЖ: компактная однострочная форма (переработка
    t7_compact.py, scratchpad r48s, в постоянный тест - задача владельца
). Все четыре именованные строки одной строкой (04-review.md
    4.M.2 «компактный список»), 6 разделителей x 24 перестановки порядка -
    каждая комбинация обязана дать полностью честный результат."""
    fns = _mtx_fns()
    for layer in ("DD", "DL", "RF"):
        fn, err = fns[layer]
        if err == "NOHOOK":
            skip("матричный страж (компактная строка): %s" % layer,
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
        if fn is None:
            record("матричный страж (компактная строка): %s - функция не вырезалась"
                   % layer, False, err)
            return
    dd, dl, rf = fns["DD"][0], fns["DL"][0], fns["RF"][0]
    p = {
        "DD": "donor-devices: %s" % _MTX_V_DD,
        "DL": "dead-language: чисто",
        "R1": "donordev_read: PASS",
        "R2": "zhivoy_yazyk_read: PASS",
    }
    seps = [" · ", "; ", ", ", " | ", " - ", "  "]
    bad = []
    n = 0
    for sep in seps:
        for order in itertools.permutations(["DD", "DL", "R1", "R2"]):
            line = sep.join(p[k] for k in order)
            body = line + "\nВЕРДИКТ: PASS\n"
            n += 1
            r_dd, r_dl, r_rf = dd(body), dl(body), rf(body)
            if not (r_dd == "OK" and r_dl == "OK" and r_rf is None):
                bad.append("sep=%r order=%s -> DD=%s DL=%s RF=%s"
                           % (sep, "/".join(order), r_dd, r_dl, r_rf))
    record("матричный страж: компактная однострочная форма, разделитель x "
           "порядок (%d комбинаций, переработка t7_compact.py)" % n,
           not bad, "; ".join(bad[:10]))


# 🔴 ПОСТОЯННЫЙ КОНТРАКТ СЕМАНТИКИ START-СКАНА donor-devices/dead-language
# (Д153+Д154, скептик-раунд 53, по решению автора). Заведён ПОСЛЕ ТРЁХ РАУНДОВ
# КАЧЕЛЕЙ вокруг ОДНОГО места: Д147 (раунд 51) закрыл fail-open -> Д150
# (раунд 52) вернулся ложным BLOCK -> Д152 (раунд 52) снова fail-open ->
# Д153 (раунд 53) снова ложный BLOCK. Каждый раунд чинил ИНСТАНС и проверял
# СВОЮ горсть форм; ни один прогон не держал ВСЕ формы РАЗОМ, поэтому
# следующая правка честно чинила своё и молча ломала соседнее.
# ЗДЕСЬ ЛЕЖИТ ВСЯ МАТРИЦА СРАЗУ - все формы Д147/Д150/Д152/Д153/Д154 плюс
# контроли (цитата с «нет времени», децимальная запятая «1,5», время
# «14:30», «§2.3:», соло-дефис прозы, компактная пара ключей, N/A ЧУЖОГО
# ключа, улика-отсутствие §4.2/§5.2, «-> «нет»», «было -> нет результата»
# внутри цитаты) 🔴 ПЛЮС Д158 (косвенные падежи «ни один»), Д159 (местоимения
# «ничего»/«ничто»/«никак…»), Д160 (глагольные формы + синонимы словаря-
# ПРЕДМЕТА «механика»/«паттерн»/«сработал») и Д161 (голый токен по сырому
# хвосту цитаты, `_donordev_mark_quoted`) - скептик-раунды 53-54, 🔴 ПЛЮС
# Д164 (несовершенный вид/прошедшее время лемм словаря-ПРЕДМЕТА -
# «подходил\w*»/«срабатыва\w*»/«опознал\w*») и Д165 (порядко-независимость
# токен/цитата в `_donordev_segment_quote_tail` - Д161 закрыл только
# токен-первый порядок) - скептик-раунд 55, 🔴 ПЛЮС Д168 (позиционный класс:
# вводное слово или глагол ПЕРЕД токеном/квантором снимает якорный скан
# целиком - И6, свободный fallback ТОЙ ЖЕ дисциплины И4) - скептик-раунд 57,
# дописаны той же дисциплиной «весь контракт разом», не отдельным скриптом на
# раунд. Пересечение с DONORDEV_CASES/DEADLANG_CASES/READFLAG_CASES выше
# НАМЕРЕННОЕ: те списки - ИСТОРИЯ по дефектам, этот - КОНТРАКТ целиком, и
# красным он обязан становиться от ЛЮБОГО сдвига семантики, а не только от
# отката последнего фикса.
#
# ИНВАРИАНТЫ (полные формулировки и названная цена - баннер-комментарий перед
# `_donordev_segment_refusal` в `post-phase-gate.sh`):
#   И1  цитата = данные (сбалансированные кавычки не режут и не сканируются);
#   И2  первый сегмент значения - полная строгость словаря отказа;
#   И3  не-первый сегмент, ГОЛЫЙ токен = отказ;
#   И4  не-первый сегмент, токен + хвост: хвост называет ПРЕДМЕТ гейта =
#       отказ, посторонний хвост = пропуск (улика-отсутствие §4.2/§5.2);
#   И4-b `n/a`/`none` - машинные статус-литералы, отказ с любым хвостом;
#       И3 сильнее И4 (разделитель, оставивший токен один, делает его голым);
#   И5  сегмент, равный ЦЕЛИКОМ закавыченному спану, разворачивается и идёт
#       по И3/И4 как НЕ-первый;
#   И6  якорный скан (позиция 0 сегмента) провалился - СВОБОДНЫЙ скан ТОГО
#       ЖЕ словаря где угодно внутри ЭТОГО сегмента, ТА ЖЕ дисциплина «токен
#       слева -> хвост-предмет справа» (порядко-зависима нарочно, не
#       bidirectional - Д168, скептик-раунд 57).
# (группа, что проверяем, слой DD|DL|RF, значение строки, ожидаемое состояние)
START_SCAN_INVARIANTS = [
    ('Д147', '-> нет (голый токен)',
     'DD', '§2.3 удержание «улика поста» -> нет', 'NO'),
    ('Д147', '-> нету',
     'DD', '§2.3 удержание «улика поста» -> нету', 'NO'),
    ('Д147', '-> ни один',
     'DD', '§2.3 удержание «улика поста» -> ни один', 'NO'),
    ('Д147', '-> отсутствует',
     'DD', '§2.3 удержание «улика поста» -> отсутствует', 'NO'),
    ('Д147', '-> none',
     'DD', '§2.3 удержание «улика поста» -> none', 'NO'),
    ('Д147', '-> N/A',
     'DD', '§2.3 удержание «улика поста» -> N/A', 'NO'),
    ('Д147', '-> ок',
     'DD', '§2.3 удержание «улика поста» -> ок', 'NO'),
    ('Д147', '-> нет подходящего приёма (хвост-ПРЕДМЕТ)',
     'DD', '§2.3 удержание «улика поста» -> нет подходящего приёма', 'NO'),
    ('Д147', '-> **нет** (markdown-обвязка)',
     'DD', '§2.3 удержание «улика поста» -> **нет**', 'NO'),
    ('Д147', '-> _нет_ (markdown-обвязка)',
     'DD', '§2.3 удержание «улика поста» -> _нет_', 'NO'),
    ('Д147', 'контроль: отказ ДО стрелки (старая позиция)',
     'DD', 'нет подходящего приёма §1-§5 -> FAIL', 'NO'),
    ('Д147', 'контроль-цитата: «нет времени на прогрев» внутри кавычек',
     'DD', '§2.3 контраст «нет времени на прогрев» -> PASS', 'OK'),
    ('Д147', 'контроль честный: §-ссылка -> PASS',
     'DD', '§2.3 смена системы отсчёта «это 8 обедов» -> PASS', 'OK'),
    ('Д150', '«было -> нет результата»',
     'DD', '§2.3 контраст «было -> нет результата» -> PASS', 'OK'),
    ('Д150', '«точка А -> нету денег»',
     'DD', '§2.3 контраст «точка А -> нету денег» -> PASS', 'OK'),
    ('Д150', '«раньше -> ок, теперь иначе»',
     'DD', '§2.3 контраст «раньше -> ок, теперь иначе» -> PASS', 'OK'),
    ('Д150', '«сначала → нет, потом да» (unicode-стрелка)',
     'DD', '§2.3 приём «сначала → нет, потом да» -> PASS', 'OK'),
    ('Д150', '"было -> нет времени" (прямые кавычки)',
     'DD', '§2.3 контраст "было -> нет времени" -> PASS', 'OK'),
    ('Д150', '`код -> none` (бэктики)',
     'DD', '§2.3 контраст `код -> none` -> PASS', 'OK'),
    ('Д152', 'отказ после «,»',
     'DD', '§2.3 удержание «улика поста», нет', 'NO'),
    ('Д152', 'отказ после «;»',
     'DD', '§2.3 удержание «улика поста»; нет', 'NO'),
    ('Д152', 'отказ после «·»',
     'DD', '§2.3 удержание «улика поста» · нет', 'NO'),
    ('Д152', 'отказ после соло-дефиса',
     'DD', '§2.3 удержание «улика поста» - нет', 'NO'),
    ('Д152', 'отказ после «=>»',
     'DD', '§2.3 удержание «улика поста» => нет', 'NO'),
    ('Д152', 'отказ после «:»',
     'DD', '§2.3 удержание «улика поста»: нет', 'NO'),
    ('Д152', 'отказ после «⟶»',
     'DD', '§2.3 удержание «улика поста» ⟶ нет', 'NO'),
    ('Д152', 'контроль: децимальная запятая «1,5 часа»',
     'DD', '§2.3 удержание, потратил 1,5 часа на разбор «улика поста» -> PASS', 'OK'),
    ('Д152', 'контроль: двоеточие сразу за §-ссылкой «§2.3:»',
     'DD', '§2.3: удержание фокуса «улика поста» -> PASS', 'OK'),
    ('Д152', 'контроль: соло-дефис прозы',
     'DD', '§2.3 приём - результат виден сразу «улика поста» -> PASS', 'OK'),
    ('Д152', 'контроль: время «14:30» снаружи цитаты',
     'DD', '§2.3 кадр против витрины, в 14:30 открыл ноут «улика поста» -> PASS', 'OK'),
    ('Д153б', '§5.2 «нет адреса и нет глагола-призыва» после «·»',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS · нет адреса и нет глагола-призыва', 'OK'),
    ('Д153б', '§4.2 «нет ссылки в финале» после «,»',
     'DD', '§4.2 финал-вывод вместо финала-ссылки «Значит, раньше надо» -> PASS, нет ссылки в финале', 'OK'),
    ('Д153б', '§4.2 «нет ссылки последней строкой» после соло-дефиса',
     'DD', '§4.2 финал-вывод вместо финала-ссылки «Значит, делать надо раньше» -> PASS - нет ссылки последней строкой', 'OK'),
    ('Д153б', '§5.2 «отсутствует адрес и глагол-призыва» после «;»',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS; отсутствует адрес и глагол-призыва', 'OK'),
    ('Д153б', '§5.2 «ни одного призыва в тексте»',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS, ни одного призыва в тексте', 'OK'),
    ('Д153б', '§4.2 «ссылки нет» (токен НЕ в начале сегмента)',
     'DD', '§4.2 финал-вывод «улика» -> PASS: ссылки нет', 'OK'),
    ('Д153б', '§5.1 «(без описи и ссылки) не сработал»',
     'DD', '§5.1 замкнутый контур передачи «улика» -> PASS, анти-паттерн (без описи и ссылки) не сработал', 'OK'),
    ('Д153б', '§4.2 «ссылки в финале нет» (обратный порядок)',
     'DD', '§4.2 финал-вывод «Значит, делать надо раньше» -> PASS, ссылки в финале нет', 'OK'),
    ('Д153б', 'И4 ОБРАТНАЯ СТОРОНА: хвост-ПРЕДМЕТ после «·» = отказ',
     'DD', '§2.3 удержание «улика» -> PASS · ни один приём не подошёл', 'NO'),
    ('Д153б', 'И4 обратная: «отсутствует приём справочника»',
     'DD', '§2.3 удержание «улика» -> PASS; отсутствует приём справочника', 'NO'),
    ('Д153б', 'И4: «ок по всем осям» - посторонний хвост В ТОМ ЖЕ сегменте',
     'DD', '§2.3 удержание «улика» -> PASS · ок по всем осям', 'OK'),
    ('Д153б', 'И3 СИЛЬНЕЕ И4: «ок, идём дальше» - запятая делает «ок» ГОЛЫМ сегментом (названная цена)',
     'DD', '§2.3 удержание «улика» -> PASS · ок, идём дальше', 'NO'),
    ('Д153б', 'И4: «нет адреса, нет глагола» - оба сегмента с хвостом',
     'DD', '§5.2 нулевой CTA «Такие дела» -> PASS · нет адреса, нет глагола-призыва', 'OK'),
    ('Д153а', 'компакт + checklist_ivana_read: N/A (канон-легально)',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · checklist_ivana_read: N/A (ключ не задан)', 'OK'),
    ('Д153а', 'компакт + factbase_read: N/A',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · factbase_read: N/A', 'OK'),
    ('Д153а', 'компакт + 4.ET: N/A',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · 4.ET: N/A - эталон не подключён', 'OK'),
    ('Д153а', 'компакт + 4.ЯЗ: N/A',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · 4.ЯЗ: N/A - слепок конструкций не подключён', 'OK'),
    ('Д153а', 'компакт + factbase_read: N/A через запятую',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS, factbase_read: N/A', 'OK'),
    ('Д153а', 'компакт + checklist: 47/47',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · checklist: 47/47', 'OK'),
    ('Д153а', 'компакт + 4.R (числовой отчёт соседа)',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · 4.R: референтов 3, висящих 0 -> PASS', 'OK'),
    ('Д153а', 'компакт + W15-цепь-итог соседа',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · W15-цепь-итог: звеньев 5 / порог 5 -> PASS', 'OK'),
    ('Д153а', 'контроль: сосед donordev_read (знали и раньше)',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · donordev_read: PASS', 'OK'),
    ('Д153а', 'контроль: сосед dead-language (знали и раньше)',
     'DD', '§2.3 смена системы отсчёта «улика» -> PASS · dead-language: чисто', 'OK'),
    ('Д153а', 'контроль fail-closed: СОБСТВЕННЫЙ отказ после чужого ключа виден (значение режется, но вторая строка судится своим слоем)',
     'DD', '§2.3 «улика» -> PASS · 4.ET: N/A\ndonor-devices: нет', 'NO'),
    ('Д153в', 'RF: PASS + checklist_ivana_read: N/A (был ложный FAIL)',
     'RF', 'PASS · checklist_ivana_read: N/A (ключ не задан)', None),
    ('Д153в', 'RF: PASS + factbase_read: N/A',
     'RF', 'PASS · factbase_read: N/A', None),
    ('Д153в', 'RF контроль: собственное признание в хвосте всё ещё FAIL',
     'RF', 'PASS, но справочник не открывал', 'donordev_read'),
    ('Д153а', 'DL: чисто + checklist_ivana_read: N/A',
     'DL', 'чисто · checklist_ivana_read: N/A (ключ не задан)', 'OK'),
    ('Д153а', 'DL: чисто + 4.ET: N/A',
     'DL', 'чисто · 4.ET: N/A', 'OK'),
    ('Д154', '-> «нет» (ёлочки)',
     'DD', '§2.3 удержание «улика поста» -> «нет»', 'NO'),
    ('Д154', '-> "нет" (прямые)',
     'DD', '§2.3 удержание «улика поста» -> "нет"', 'NO'),
    ('Д154', '-> `нет` (бэктики)',
     'DD', '§2.3 удержание «улика поста» -> `нет`', 'NO'),
    ('Д154', '-> “нет” (английские парные)',
     'DD', '§2.3 удержание «улика поста» -> “нет”', 'NO'),
    ('Д154', '-> «N/A»',
     'DD', '§2.3 удержание «улика поста» -> «N/A»', 'NO'),
    ('Д154', '-> «отсутствует»',
     'DD', '§2.3 удержание «улика поста» -> «отсутствует»', 'NO'),
    ('Д154', '-> «ни один приём не подошёл» (хвост-ПРЕДМЕТ в цитате)',
     'DD', '§2.3 удержание «улика поста» -> «ни один приём не подошёл»', 'NO'),
    ('Д154', '-> «нет» после «·»',
     'DD', '§2.3 удержание «улика поста» · «нет»', 'NO'),
    ('Д154', 'контроль И5+И4: улика-цитата ПОСЛЕ стрелки, отказ СРЕДИ слов',
     'DD', '§2.3 приём удержания -> «нет времени на прогрев»', 'OK'),
    ('Д154', 'контроль И5: цитата отдельным сегментом, проза внутри',
     'DD', '§2.3 приём удержания, «нет времени на прогрев», -> PASS', 'OK'),
    ('Д154', 'контроль Д150 НЕ откачен: «было -> нет результата» в цитате',
     'DD', '§2.3 контраст «было -> нет результата» -> PASS', 'OK'),
    ('Д154-DL', 'чисто -> нет (уже работало, Д147-DL)',
     'DL', 'чисто -> нет', 'NO'),
    ('Д154-DL', 'чисто -> «нет»',
     'DL', 'чисто -> «нет»', 'NO'),
    ('Д154-DL', 'чисто -> `нет`',
     'DL', 'чисто -> `нет`', 'NO'),
    ('Д154-DL', 'чисто · «N/A»',
     'DL', 'чисто · «N/A»', 'NO'),
    ('Д154-DL', 'контроль: цитата поста с «нет» СРЕДИ слов',
     'DL', 'чисто, «нет ничего мёртвого» - именно так я и написал', 'OK'),
    ('Д154-DL', 'контроль Д150-DL: «было -> нет результата» в цитате',
     'DL', 'чисто, цитата поста «было -> нет результата» оставлена как есть', 'OK'),
    ('Д154-DL', 'контроль: голое «чисто»',
     'DL', 'чисто', 'OK'),
    ('Д154-DL', 'контроль: числовая форма с парами',
     'DL', '3 слов заменено · «мёртвое» -> «живая замена»', 'OK'),
    ('Д154-DL', 'контроль: числовая форма, пара с «нет» внутри цитаты',
     'DL', '2 слова заменено · «нет времени» -> «времени мало» · «шаг» -> «нажми»', 'OK'),
    # --- 🔴 Д158 (fail-open, назван фиксером раунда 53 как кандидат ВНЕ его
    # периметра, найден этой сессией, по решению автора): токен «ни один» START-
    # словаря нёс ТОЛЬКО именительный падеж (буквальный литерал «один») -
    # косвенные падежи («ни одного»/«ни одна»/«ни одной») меняют стем
    # целиком на «одн-» (это НЕ суффиксация - «один» = о-д-и-н, «одного» =
    # о-д-н-ого, буквы «и» там нет вовсе), литерал не матчился НИ ЧАСТИЧНО.
    # ФИКС - вторая альтернатива `ни\s+одн\w*` ДОБАВЛЕНА рядом со старым
    # литералом `ни\s+один` (голая замена регрессировала бы сам номинатив -
    # живой репро при первой попытке, scratchpad r57/mech_check.py). И4 не
    # тронут - «-> PASS, ни одного призыва в тексте» (эта же матрица, #35
    # выше) держится `OK`, форма токена И4 не примешана.
    ('Д158', '-> ни одного (генитив, хвост-ПРЕДМЕТ)',
     'DD', '§2.3 удержание «улика поста» -> ни одного приёма не подошло', 'NO'),
    ('Д158', 'line-start: «ни одного из приёмов не опознал»',
     'DD', 'ни одного из приёмов не опознал, §2.3 удержание -> PASS', 'NO'),
    ('Д158', '-> ни одна (женский род, хвост-ПРЕДМЕТ)',
     'DD', '§2.3 удержание «улика поста» -> ни одна ссылка справочника не подошла', 'NO'),
    ('Д158', 'И4 контроль: «ни одной» хвост НЕ предмет - пропуск (зеркало §5.2 #35)',
     'DD', '§2.3 удержание «улика поста» -> PASS · ни одной оси в тексте не названо', 'OK'),
    ('Д158', 'контроль регресс: «ни один» (номинатив) держится',
     'DD', '§2.3 удержание «улика поста» -> ни один вариант справочника не подошёл', 'NO'),
    ('Д158', 'контроль §5.2 #35 (Д153б) НЕ откачен: «ни одного призыва в тексте» после PASS',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS, ни одного призыва в тексте', 'OK'),
    # --- 🔴 Д159 (fail-open, класс Д158, скептик-раунд 54, по решению автора):
    # отрицательные местоимения «ничего»/«ничто»/«никак…» не были START-
    # токенами словаря отказа - патч R58 добавил `ничего|ничто|никак\w*`
    # рядом с `ни\s+одн\w*`. Полное обоснование - баннер над Д159 в
    # `post-phase-gate.sh` (генератор `scratchpad/r58/generate_fix_r58.py`).
    ('Д159', '-> ничего не подошло (хвост-ПРЕДМЕТ)',
     'DD', '§2.3 удержание «улика поста» -> ничего не подошло', 'NO'),
    ('Д159', 'line-start: «ничего не подошло, §2.3 -> PASS»',
     'DD', 'ничего не подошло, §2.3 удержание -> PASS', 'NO'),
    ('Д159', '-> ничто не совпало (хвост-ПРЕДМЕТ, форма «ничто»)',
     'DD', '§2.3 удержание «улика поста» -> ничто не совпало', 'NO'),
    ('Д159', '-> никаких подходящих приёмов (форма «никак\\w*»)',
     'DD', '§2.3 удержание «улика поста» -> никаких подходящих приёмов', 'NO'),
    ('Д159', 'контроль И1: «ничего не изменилось» ВНУТРИ цитаты - данные, не скан',
     'DD', '§2.3 удержание «ничего не изменилось» -> PASS', 'OK'),
    ('Д159', 'контроль: «-> ничего не нашёл» держится NO через PHRASE (не через новую альтернативу)',
     'DD', '§2.3 удержание «улика поста» -> ничего не нашёл', 'NO'),
    ('Д159', 'И4 контроль: «ничего» хвост НЕ предмет - пропуск (зеркало §5.2 #35/Д158)',
     'DD', '§2.3 удержание «улика поста» -> PASS · ничего особенного в тексте', 'OK'),
    # --- 🔴 Д160 (fail-open, словарь-ПРЕДМЕТ И4 неполон, скептик-раунд 54,
    # по решению автора): глагольные формы «подходит»/«подойдёт»/«совпал» (причастия/
    # несовершенный вид уже в словаре, финитных форм не несли) + синонимы
    # предмета из канона (механика/паттерн/сработал, донор-copy-devices.md +
    # 04-review.md). Полное обоснование + таблица «токен -> источник» -
    # баннер над Д160 в `post-phase-gate.sh`.
    ('Д160', '-> ни один из вариантов не подходит (финитный глагол «подходит»)',
     'DD', '§2.3 удержание «улика поста» -> ни один из вариантов не подходит', 'NO'),
    ('Д160', '-> ни один из результатов не совпал (перфектив «совпал», был не покрыт «совпад\\w*»)',
     'DD', '§2.3 удержание «улика поста» -> ни один из результатов не совпал', 'NO'),
    ('Д160', '-> ни один вариант не подойдёт (буд. вр. «подойдёт»)',
     'DD', '§2.3 удержание «улика поста» -> ни один вариант не подойдёт', 'NO'),
    ('Д160', '-> нет паттерна под эту ситуацию (синоним «паттерн» из канона)',
     'DD', '§2.3 удержание «улика поста» -> нет паттерна под эту ситуацию', 'NO'),
    ('Д160', '-> нет механики под эту ситуацию (синоним «механика» из канона)',
     'DD', '§2.3 удержание «улика поста» -> нет механики под эту ситуацию', 'NO'),
    ('Д160', '-> нет сработавшей техники (синоним «сработал» из канона)',
     'DD', '§2.3 удержание «улика поста» -> нет сработавшей техники', 'NO'),
    ('Д160', 'И4 контроль: «подходит» БЕЗ отказ-токена в своём сегменте - не триггерит (граница «подход»-омонима)',
     'DD', '§2.3 удержание «улика» -> PASS · подходит по срокам', 'OK'),
    ('Д160', 'И4 контроль: «паттерн»/«механика» упомянуты как факт без отказа',
     'DD', '§2.3 удержание «улика» -> PASS · паттерн сохранён, механика описана', 'OK'),
    # --- 🔴 Д161 (ложный BLOCK, стык И1×И3, скептик-раунд 54, по решению автора):
    # «голый токен» (И3) решался ПОСЛЕ вырезки цитаты - хвост из ОДНОЙ
    # цитаты схлопывался до пустоты и читался отказом, хотя цитата - улика-
    # отсутствие (И4). Полное обоснование - баннер над Д161 в
    # `post-phase-gate.sh` (`_donordev_mark_quoted`/`_donordev_segment_
    # quote_tail`).
    ('Д161', '§5.2 «нет «подписывайся»» с ОДНОЙ цитатой-уликой после «·» -> OK (была ложным BLOCK)',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS · нет «подписывайся»', 'OK'),
    ('Д161', '§4.2 «нет «переходи по ссылке»» с ОДНОЙ цитатой-уликой после «,» -> OK',
     'DD', '§4.2 финал-вывод вместо финала-ссылки «Значит, раньше надо» -> PASS, нет «переходи по ссылке»', 'OK'),
    ('Д161', 'два «нет + цитата» через союз «и» (не разделитель) - OK, согласовано с формой выше',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS · нет «пиши в личку» и нет «переходи»', 'OK'),
    ('Д161', 'И5 контроль: «-> «нет»» держится NO (сегмент ЦЕЛИКОМ цитата, не откачен)',
     'DD', '§2.3 удержание «улика поста» -> «нет»', 'NO'),
    ('Д161', 'И3 контроль: «· нет» ГОЛЫЙ (цитаты не было) держится NO',
     'DD', '§2.3 удержание «улика поста» · нет', 'NO'),
    ('Д161', 'рекурсия И5-сильнее-пропуска: «-> PASS · нет «нет»» (содержимое цитаты САМО отказ) -> NO',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «нет»', 'NO'),
    ('Д161', 'рекурсия контроль: цитата-хвост НЕ отказ, хоть и содержит слово-предмет «приём» -> OK',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «конкретно этот приём не пробовали»', 'OK'),
    # --- 🔴 Д164 (fail-open, класс Д158/Д160, скептик-раунд 55, по решению автора):
    # несовершенный вид и прошедшее время лемм словаря-ПРЕДМЕТА не были
    # покрыты - «подходил\w*»/«срабатыва\w*» отсутствовали в
    # `_DONORDEV_SUBJECT_RE`. Систематический проход по ВСЕМ леммам словаря
    # (таблица «лемма -> покрытые формы -> добавленные» - отчёт исполнителя,
    # scratchpad r59) нашёл ТРЕТЬЮ форму той же дыры - «опознан\w*»
    # (причастие) не покрывал «опознал» (перфектив, активный залог,
    # буква «л» вместо «н» на 7-й позиции - другой стем, не суффиксация),
    # хотя «не опознал» - ДОСЛОВНАЯ канон-фраза верификатора
    # (`workflow/04-review.md:1005` «не опознал ни одного - печатай
    # donor-devices: нет -> FAIL»). Полное обоснование - баннер ФИКСА Д164
    # в `post-phase-gate.sh`.
    ('Д164', '-> ничего не подходило (имперфектив прош.вр., ср.р./муж.р. основа, «подходил\\w*»)',
     'DD', '§2.3 удержание «улика поста» -> ничего не подходило', 'NO'),
    ('Д164', '-> ничего не подходил (имперфектив прош.вр., муж.р.)',
     'DD', '§2.3 удержание «улика поста» -> ничего не подходил', 'NO'),
    ('Д164', '-> ничего не подходила (имперфектив прош.вр., жен.р.)',
     'DD', '§2.3 удержание «улика поста» -> ничего не подходила', 'NO'),
    ('Д164', '-> ничего не срабатывает (имперфектив наст.вр., «срабатыва\\w*»)',
     'DD', '§2.3 удержание «улика поста» -> ничего не срабатывает', 'NO'),
    ('Д164', '-> ни один не срабатывал (имперфектив прош.вр.)',
     'DD', '§2.3 удержание «улика поста» -> ни один не срабатывал', 'NO'),
    ('Д164', 'контроль регресс: «подходит» (литерал Д160) держится',
     'DD', '§2.3 удержание «улика поста» -> ничего не подходит', 'NO'),
    ('Д164', 'контроль регресс: «сработало» («сработ\\w*» Д160) держится',
     'DD', '§2.3 удержание «улика поста» -> ничего не сработало', 'NO'),
    ('Д164', 'систематическая находка: -> ничего не опознал (канон 04-review.md:1005 «не опознал ни одного», «опознал\\w*»)',
     'DD', '§2.3 удержание «улика поста» -> ничего не опознал', 'NO'),
    ('Д164', 'контроль границы: «подход» БЕЗ отказ-токена в сегменте - омоним «творческий подход» НЕ триггерит',
     'DD', '§2.3 удержание «улика» -> PASS · творческий подход к тонам', 'OK'),
    ('Д164', 'контроль отклонённой формы: «опознаёт» (имперфектив наст.вр.) НЕ в словаре - нет корпус-улики (ОТКЛОНЕНО, см. баннер), без отказ-токена в своём сегменте не триггерит',
     'DD', '§2.3 удержание «улика» -> PASS · верификатор уверенно опознаёт формат', 'OK'),
    # --- 🔴 Д165 (ложный BLOCK, асимметрия порядка токен/цитата, скептик-
    # раунд 55, по решению автора): `_donordev_segment_quote_tail` (Д161) искала
    # токен `^`-анкером на РАЗМЕЧЕННОМ сегменте - работало ТОЛЬКО когда
    # токен стоял ДО цитаты. Цитата ДО токена («подписывайся» отсутствует»)
    # читалась голым токеном (И3, ложный `NO`), хотя смысл ТОТ ЖЕ, что у
    # честного «нет «подписывайся»» (`OK`, до R59 обе формы читались `NO` -
    # Д161 закрыл только половину симметрии). Полное обоснование - баннер
    # ФИКСА Д165 в `post-phase-gate.sh`.
    ('Д165', '§5.2 «подписывайся» отсутствует» (цитата ПЕРЕД токеном, обратный порядок Д161) -> OK, симметрично',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS · «подписывайся» отсутствует', 'OK'),
    ('Д165', '§4.2 «жду в комментариях» отсутствует» (второй CTA, цитата ПЕРЕД токеном)',
     'DD', '§4.2 финал-вывод вместо финала-ссылки «Значит, раньше надо» -> PASS, «жду в комментариях» отсутствует', 'OK'),
    ('Д165', 'контроль регресс: токен-первый «нет «подписывайся»» держится OK (Д161 не откачен)',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS · нет «подписывайся»', 'OK'),
    ('Д165', 'контроль И5: сегмент ЦЕЛИКОМ цитата «-> «нет»» держится NO (другая функция, не эта)',
     'DD', '§2.3 удержание «улика поста» -> «нет»', 'NO'),
    ('Д165', 'контроль И3: голый токен БЕЗ цитаты «· нет» держится NO',
     'DD', '§2.3 удержание «улика поста» · нет', 'NO'),
    ('Д165', 'контроль: quote_tail из ДВУХ цитат, ни одна САМА не отказ -> OK (порядко-независимый сбор маркеров не путает счёт)',
     'DD', '§2.3 удержание «улика поста» -> нет «раз» «два»', 'OK'),
    ('Д165', 'контроль: quote_tail из ДВУХ цитат, ОДНА сама отказ -> NO (И5-сильнее-пропуска не сломан)',
     'DD', '§2.3 удержание «улика поста» -> нет «раз» «нет»', 'NO'),
    ('Д165', 'контроль регресс: цитата ПЕРЕД токеном, но ОСТАТОК СЕГМЕНТА (вырезанный хвост) НЕ пуст - функция quote_tail не вызывается вовсе, судит обычный И4',
     'DD', '§2.3 удержание «улика поста» -> нет «Такие дела» не подошёл', 'NO'),
    # --- 🔴 Д166/Д167 (скептик-раунд 56, по решению автора, полное обоснование - баннеры
    # Д166/Д167 в DONORDEV_CASES выше). ОБА порядка слов на ВСЕХ парах, что нашёл
    # скептик + канон-фраза дословно.
    ('Д166', 'канон-фраза дословно «не опознал ни одного» (04-review.md:1005)',
     'DD', 'не опознал ни одного', 'NO'),
    ('Д166', 'порядок A (отказ ДО предмета): «-> не опознал ни одного, PASS»',
     'DD', '§2.3 -> не опознал ни одного, PASS', 'NO'),
    ('Д166', 'порядок A line-start: «не опознал ни одного, §2.3 -> PASS»',
     'DD', 'не опознал ни одного, §2.3 -> PASS', 'NO'),
    ('Д166', 'вложил mid-line: «справочник приёмов не вложили»',
     'DD', '§2.3 «улика поста» -> PASS, но справочник приёмов не вложили', 'NO'),
    ('Д167', 'порядок A (отказ ДО предмета): «-> не подошёл ни один приём, PASS»',
     'DD', '§2.3 -> не подошёл ни один приём, PASS', 'NO'),
    ('Д167', 'порядок A line-start: «не подошёл ни один приём, §2.3 -> PASS»',
     'DD', 'не подошёл ни один приём, §2.3 -> PASS', 'NO'),
    ('Д167', 'порядок B (контроль, уже работал ДО фикса через START): «ни один приём не подошёл, §2.3 -> PASS»',
     'DD', 'ни один приём не подошёл, §2.3 -> PASS', 'NO'),
    ('Д167', 'порядок A: «-> не подойдёт ни один вариант, PASS»',
     'DD', '§2.3 -> не подойдёт ни один вариант, PASS', 'NO'),
    ('Д167', 'порядок B (контроль): «ни один вариант не подойдёт, §2.3 -> PASS»',
     'DD', 'ни один вариант не подойдёт, §2.3 -> PASS', 'NO'),
    ('Д167', 'порядок A: «-> не совпал ни один результат, PASS»',
     'DD', '§2.3 -> не совпал ни один результат, PASS', 'NO'),
    ('Д167', 'порядок B (контроль): «ни один результат не совпал, §2.3 -> PASS»',
     'DD', 'ни один результат не совпал, §2.3 -> PASS', 'NO'),
    ('Д167', 'контроль: честная замена приёма «взял §2.4 вместо» - принятая цена (класс root «наш», не новый размен)',
     'DD', '§2.3 «улика поста» -> PASS · взял §2.4 вместо, приём не подошёл', 'NO'),
    ('Д167', 'контроль: «сработ»/«срабатыва» НЕ в PHRASE - «анти-паттерн не сработал» (Д153б) держит OK',
     'DD', '§5.1 замкнутый контур передачи «улика» -> PASS, анти-паттерн (без описи и ссылки) не сработал', 'OK'),
    # --- 🔴 Д168 (скептик-раунд 57, по решению автора): 12 токенов x 3 вводных = 36
    # форм (выборка полной 72-сетки 12x6 - все 12 токенов словаря представлены
    # минимум 2-3 вводными, обе поверхности А/Б). Полное обоснование, живые
    # репро на всех 72 формах - баннер ФИКСА Д168 в post-phase-gate.sh.
    ('Д168', 'вводное «но» + токен «нет» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но нет подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «нет» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы нет подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «нет» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути нет подходящего приёма', 'NO'),
    ('Д168', 'вводное «но» + токен «нету» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но нету подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «нету» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы нету подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «нету» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути нету подходящего приёма', 'NO'),
    ('Д168', 'вводное «но» + токен «ни один» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но ни один подходящий приём', 'NO'),
    ('Д168', 'вводное «увы» + токен «ни один» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы ни один подходящий приём', 'NO'),
    ('Д168', 'вводное «по сути» + токен «ни один» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути ни один подходящий приём', 'NO'),
    ('Д168', 'вводное «но» + токен «ничего» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но ничего подходящего в справочнике', 'NO'),
    ('Д168', 'вводное «увы» + токен «ничего» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы ничего подходящего в справочнике', 'NO'),
    ('Д168', 'вводное «по сути» + токен «ничего» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути ничего подходящего в справочнике', 'NO'),
    ('Д168', 'вводное «но» + токен «ничто» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но ничто подходящее в справочнике', 'NO'),
    ('Д168', 'вводное «увы» + токен «ничто» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы ничто подходящее в справочнике', 'NO'),
    ('Д168', 'вводное «по сути» + токен «ничто» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути ничто подходящее в справочнике', 'NO'),
    ('Д168', 'вводное «но» + токен «никак» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но никакой подходящий приём', 'NO'),
    ('Д168', 'вводное «увы» + токен «никак» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы никакой подходящий приём', 'NO'),
    ('Д168', 'вводное «по сути» + токен «никак» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути никакой подходящий приём', 'NO'),
    ('Д168', 'вводное «но» + токен «отсутствует» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но отсутствует подходящий приём', 'NO'),
    ('Д168', 'вводное «увы» + токен «отсутствует» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы отсутствует подходящий приём', 'NO'),
    ('Д168', 'вводное «по сути» + токен «отсутствует» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути отсутствует подходящий приём', 'NO'),
    ('Д168', 'вводное «но» + токен «недоступен» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но недоступен подходящий приём', 'NO'),
    ('Д168', 'вводное «увы» + токен «недоступен» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы недоступен подходящий приём', 'NO'),
    ('Д168', 'вводное «по сути» + токен «недоступен» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути недоступен подходящий приём', 'NO'),
    ('Д168', 'вводное «но» + токен «none» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но none подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «none» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы none подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «none» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути none подходящего приёма', 'NO'),
    ('Д168', 'вводное «но» + токен «n/a» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но n/a подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «n/a» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы n/a подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «n/a» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути n/a подходящего приёма', 'NO'),
    ('Д168', 'вводное «но» + токен «ок» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но ок без подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «ок» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы ок без подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «ок» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути ок без подходящего приёма', 'NO'),
    ('Д168', 'вводное «но» + токен «ok» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, но ok без подходящего приёма', 'NO'),
    ('Д168', 'вводное «увы» + токен «ok» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, увы ok без подходящего приёма', 'NO'),
    ('Д168', 'вводное «по сути» + токен «ok» (mid-line, tail-предмет)',
     'DD', '§2.3 «улика поста» -> PASS, по сути ok без подходящего приёма', 'NO'),
    ('Д168', 'line-start Surface А: «не срабатывает ни один приём, §2.3 -> PASS» (И6 применяется и к ПЕРВОМУ сегменту)',
     'DD', 'не срабатывает ни один приём, §2.3 -> PASS', 'NO'),
    ('Д168', 'line-start Surface А: «не годится ни один приём донора, §2.3 -> PASS»',
     'DD', 'не годится ни один приём донора, §2.3 -> PASS', 'NO'),
    ('Д168', 'mid-line Surface А: «§2.3 «улика» -> PASS, не выстрелил ни один приём справочника»',
     'DD', '§2.3 «улика» -> PASS, не выстрелил ни один приём справочника', 'NO'),
    ('Д168', 'ЦЕНА (1/1): «из справочника ничего не взял» - предмет ДО квантора, НЕ закрыто у DD (И6 порядко-зависима нарочно), держится ТОЛЬКО чужим DL-гейтом (Д171)',
     'DD', '§2.3 «улика» -> PASS, из справочника ничего не взял', 'OK'),
    ('Д168', 'ЦЕНА: названный ложный BLOCK - «приём» в общем маркетинговом смысле, не §N.M; формы нет в живом корпусе',
     'DD', '§5.2 нулевой CTA в продающем «Такие дела» -> PASS - в посте нет призыва как приёма закрытия', 'NO'),
    # --- 🔴 Д173 (fail-open + ложное утверждение Д171, скептик-раунд 59,
    # по решению автора): форма 2 именованной цены Д168 («приёмов ничего не дало»)
    # раньше проходила `OK` НАСКВОЗЬ - ни DD (И6, ценой), ни DL (`_DEADLANG_
    # SUBJECT_RE` не несёт корень «приём») её не ловили. ФИКС: новый словарь
    # `_DONORDEV_NO_DALO_RE` (кавычко-безопасный, Д43-класс снят) - диагноз
    # `DONORDEV_NO`. Живой прогон ДО фикса - `scratchpad/r62s/
    # d175_named_price.py` (`OK`). Форма 1 («…не взял», запись выше) НЕ
    # тронута:
    ('Д173', 'ФИКС: «приёмов ничего не дало» (форма 2, глагол «дал\\w*») - была OK насквозь, теперь своя DONORDEV_NO',
     'DD', '§2.3 «улика» -> PASS, приёмов ничего не дало', 'NO'),
    ('Д173', 'вариант «приёмы ничего не дали» (мн.ч.)',
     'DD', '§2.3 «улика» -> PASS, приёмы ничего не дали', 'NO'),
    ('Д173', 'контроль Д43: честная цитата поста «ничего не дало» внутри «…» - НЕ отказ (кавычко-вырезанный скан)',
     'DD', '§2.3 «в первый месяц ничего не дало эффекта, потом пошло» -> PASS', 'OK'),
    # --- 🔴 Д172 (критический, fail-open, класс-повтор Д170, скептик-раунд 59,
    # по решению автора): рекурсия `_donordev_segment_refusal` по `quote_tail` (И3,
    # пустой хвост после вырезки цитаты) звала САМА СЕБЯ БЕЗ `free_re` -
    # hedge-отказ ВНУТРИ цитаты-хвоста после голого токена невидим И6-fallback'у.
    # Полная 12x6-матрица - `scratchpad/r62s/d172_grid.py`+`d172_e2e.py` (ДО фикса
    # 42/72 grid + 30/72 e2e текли); здесь выборка 12x2 (2 вводных из измеренных 6,
    # тот же принцип семплирования, что Д169/Д170 выше):
    ('Д172', 'Д172 quote_tail рекурсия: «но нет подходящего приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но нет подходящего приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути нет подходящего приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути нет подходящего приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но нету подходящего приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но нету подходящего приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути нету подходящего приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути нету подходящего приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но ни один приём не подошёл» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но ни один приём не подошёл»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути ни один приём не подошёл» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути ни один приём не подошёл»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но ничего из справочника» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но ничего из справочника»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути ничего из справочника» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути ничего из справочника»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но никаких приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но никаких приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути никаких приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути никаких приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но не применял приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но не применял приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути не применял приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути не применял приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но отсутствует приём справочника» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но отсутствует приём справочника»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути отсутствует приём справочника» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути отсутствует приём справочника»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но недоступен справочник приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но недоступен справочник приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути недоступен справочник приёмов» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути недоступен справочник приёмов»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но не нашёл ни одного приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но не нашёл ни одного приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути не нашёл ни одного приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути не нашёл ни одного приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но не сработал ни один приём» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но не сработал ни один приём»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути не сработал ни один приём» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути не сработал ни один приём»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но не зашёл ни один приём» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но не зашёл ни один приём»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути не зашёл ни один приём» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути не зашёл ни один приём»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «но не опознал ни одного приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «но не опознал ни одного приёма»', 'NO'),
    ('Д172', 'Д172 quote_tail рекурсия: «по сути не опознал ни одного приёма» в позиции цитаты-хвоста',
     'DD', '§2.3 удержание «улика поста» -> PASS · нет «по сути не опознал ни одного приёма»', 'NO'),
    # --- 🔴 Д169 (критический, ложный BLOCK, скептик-раунд 58, по решению автора):
    # `_DONORDEV_NO_FREE_RE` (Д168, срез `.pattern[1:]`) снимала ТОЛЬКО
    # ведущий `^` - словограницы СЛЕВА не было вовсе, свободный скан ловил
    # корень словаря ВНУТРИ ЛЮБОГО слова, оканчивающегося на альтернативу
    # («крючОК»/«блОК»/«урОК»/hOOK ловили «ок»; «интерНЕТ» ловило «нет»).
    # ИЗМЕРЕНО (scratchpad/r61s/d169_matrix.py): 16 слов x 6 хвостов = 96/96
    # ложных BLOCK. ФИКС: negative lookbehind `(?<![0-9a-zа-яё])` СНАРУЖИ
    # среза (словарь остаётся срезом, не литералом - урок Д144). Ниже -
    # ВЫБОРКА 16 слов x 2 хвоста (из измеренных 6) - полная 16x6-матрица
    # живёт repro-скриптом, здесь - постоянный контракт-замок.
    ('Д169', 'крючок + применён (хвост-ПРЕДМЕТ следом)',
     'DD', '§2.3 крючок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'крючок + паттерн донора',
     'DD', '§2.3 крючок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'блок + применён',
     'DD', '§2.3 блок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'блок + паттерн донора',
     'DD', '§2.3 блок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'поток + применён',
     'DD', '§2.3 поток применён «цитата» -> PASS', 'OK'),
    ('Д169', 'поток + паттерн донора',
     'DD', '§2.3 поток паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'урок + применён',
     'DD', '§2.3 урок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'урок + паттерн донора',
     'DD', '§2.3 урок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'срок + применён',
     'DD', '§2.3 срок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'срок + паттерн донора',
     'DD', '§2.3 срок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'рынок + применён',
     'DD', '§2.3 рынок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'рынок + паттерн донора',
     'DD', '§2.3 рынок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'список + применён',
     'DD', '§2.3 список применён «цитата» -> PASS', 'OK'),
    ('Д169', 'список + паттерн донора',
     'DD', '§2.3 список паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'скачок + применён',
     'DD', '§2.3 скачок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'скачок + паттерн донора',
     'DD', '§2.3 скачок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'слепок + применён',
     'DD', '§2.3 слепок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'слепок + паттерн донора',
     'DD', '§2.3 слепок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'недостаток + применён',
     'DD', '§2.3 недостаток применён «цитата» -> PASS', 'OK'),
    ('Д169', 'недостаток + паттерн донора',
     'DD', '§2.3 недостаток паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'порядок + применён',
     'DD', '§2.3 порядок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'порядок + паттерн донора',
     'DD', '§2.3 порядок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'заголовок + применён',
     'DD', '§2.3 заголовок применён «цитата» -> PASS', 'OK'),
    ('Д169', 'заголовок + паттерн донора',
     'DD', '§2.3 заголовок паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'интернет + применён (корень «нет» внутри слова)',
     'DD', '§2.3 интернет применён «цитата» -> PASS', 'OK'),
    ('Д169', 'интернет + паттерн донора',
     'DD', '§2.3 интернет паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'кабинет + применён',
     'DD', '§2.3 кабинет применён «цитата» -> PASS', 'OK'),
    ('Д169', 'кабинет + паттерн донора',
     'DD', '§2.3 кабинет паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'hook (EN) + применён',
     'DD', '§2.3 hook применён «цитата» -> PASS', 'OK'),
    ('Д169', 'hook (EN) + паттерн донора',
     'DD', '§2.3 hook паттерн донора «цитата» -> PASS', 'OK'),
    ('Д169', 'book (EN) + применён',
     'DD', '§2.3 book применён «цитата» -> PASS', 'OK'),
    ('Д169', 'book (EN) + паттерн донора',
     'DD', '§2.3 book паттерн донора «цитата» -> PASS', 'OK'),
    # --- 🔴 Д170 (fail-open, скептик-раунд 58, по решению автора):
    # `_donordev_solo_quote_refusal` (И5, сегмент-цитата целиком) звала
    # `_donordev_segment_refusal` БЕЗ `free_re` - И6-fallback внутри
    # развёрнутой цитаты никогда не пробовался, hedge-отказ ЦЕЛИКОМ-
    # цитатой («§2.3 -> PASS, «но нет подходящего приёма»») проходил `OK`.
    # ИЗМЕРЕНО (scratchpad/r61s/d170_grid.py, живой python-блок хука): 72
    # формы (12 токенов x 6 вводных) -> 36/72 текли. ФИКС: `free_re`
    # пробрасывается ИЗ `_donordev_start_refusal` в `_donordev_solo_quote_
    # refusal` дальше В `_donordev_segment_refusal` (DL-вызов НЕ ТРОНУТ,
    # дефолт `None`). Ниже - ВЫБОРКА 12 токенов x 2 вводных (из 6) - полная
    # 12x6-сетка живёт repro-скриптом, здесь - постоянный контракт-замок.
    ('Д170', '«но нет подходящего приёма» в цитате-сегменте целиком',
     'DD', '§2.3 -> PASS, «но нет подходящего приёма»', 'NO'),
    ('Д170', '«по сути нет подходящего приёма» в цитате-сегменте целиком',
     'DD', '§2.3 -> PASS, «по сути нет подходящего приёма»', 'NO'),
    ('Д170', '«но нету подходящего приёма» в цитате',
     'DD', '§2.3 -> PASS, «но нету подходящего приёма»', 'NO'),
    ('Д170', '«по сути нету подходящего приёма» в цитате',
     'DD', '§2.3 -> PASS, «по сути нету подходящего приёма»', 'NO'),
    ('Д170', '«но ни один приём не подошёл» в цитате',
     'DD', '§2.3 -> PASS, «но ни один приём не подошёл»', 'NO'),
    ('Д170', '«по сути ни один приём не подошёл» в цитате',
     'DD', '§2.3 -> PASS, «по сути ни один приём не подошёл»', 'NO'),
    ('Д170', '«но ничего из справочника» в цитате',
     'DD', '§2.3 -> PASS, «но ничего из справочника»', 'NO'),
    ('Д170', '«по сути ничего из справочника» в цитате',
     'DD', '§2.3 -> PASS, «по сути ничего из справочника»', 'NO'),
    ('Д170', '«но никаких приёмов» в цитате',
     'DD', '§2.3 -> PASS, «но никаких приёмов»', 'NO'),
    ('Д170', '«по сути никаких приёмов» в цитате',
     'DD', '§2.3 -> PASS, «по сути никаких приёмов»', 'NO'),
    ('Д170', '«но не применял приёмов» в цитате',
     'DD', '§2.3 -> PASS, «но не применял приёмов»', 'NO'),
    ('Д170', '«по сути не применял приёмов» в цитате',
     'DD', '§2.3 -> PASS, «по сути не применял приёмов»', 'NO'),
    ('Д170', '«но отсутствует приём справочника» в цитате',
     'DD', '§2.3 -> PASS, «но отсутствует приём справочника»', 'NO'),
    ('Д170', '«по сути отсутствует приём справочника» в цитате',
     'DD', '§2.3 -> PASS, «по сути отсутствует приём справочника»', 'NO'),
    ('Д170', '«но недоступен справочник приёмов» в цитате',
     'DD', '§2.3 -> PASS, «но недоступен справочник приёмов»', 'NO'),
    ('Д170', '«по сути недоступен справочник приёмов» в цитате',
     'DD', '§2.3 -> PASS, «по сути недоступен справочник приёмов»', 'NO'),
    ('Д170', '«но не нашёл ни одного приёма» в цитате',
     'DD', '§2.3 -> PASS, «но не нашёл ни одного приёма»', 'NO'),
    ('Д170', '«по сути не нашёл ни одного приёма» в цитате',
     'DD', '§2.3 -> PASS, «по сути не нашёл ни одного приёма»', 'NO'),
    ('Д170', '«но не сработал ни один приём» в цитате',
     'DD', '§2.3 -> PASS, «но не сработал ни один приём»', 'NO'),
    ('Д170', '«по сути не сработал ни один приём» в цитате',
     'DD', '§2.3 -> PASS, «по сути не сработал ни один приём»', 'NO'),
    ('Д170', '«но не зашёл ни один приём» в цитате',
     'DD', '§2.3 -> PASS, «но не зашёл ни один приём»', 'NO'),
    ('Д170', '«по сути не зашёл ни один приём» в цитате',
     'DD', '§2.3 -> PASS, «по сути не зашёл ни один приём»', 'NO'),
    ('Д170', '«но не опознал ни одного приёма» в цитате',
     'DD', '§2.3 -> PASS, «но не опознал ни одного приёма»', 'NO'),
    ('Д170', '«по сути не опознал ни одного приёма» в цитате',
     'DD', '§2.3 -> PASS, «по сути не опознал ни одного приёма»', 'NO'),
]


def test_donordev_start_scan_invariants():
    """🔴 КОНТРАКТ START-СКАНА (Д153+Д154, скептик-раунд 53, по решению автора;
    расширен Д158-Д161, скептик-раунды 53-54; расширен Д164-Д165, скептик-
    раунд 55; расширен И6/Д168, скептик-раунд 57): ВСЯ инвариант-матрица
    Д147/Д150/Д152/Д153/Д154/Д158/Д159/Д160/Д161/Д164/Д165/Д168 разом, на
    ЖИВЫХ функциях всех ТРЁХ слоёв (`_donordev_state`/`_deadlang_state`/
    `_readflag_state`).

    Зачем отдельным тестом, а не добавкой в существующие списки кейсов:
    списки `DONORDEV_CASES`/`DEADLANG_CASES`/`READFLAG_CASES` растут ПО
    ДЕФЕКТАМ и читаются как история; этот - ЕДИНЫЙ КОНТРАКТ семантики, и
    его задача краснеть от ЛЮБОГО сдвига, включая «починили одно, сломали
    соседнее» (ровно тот класс, что дал три раунда качелей Д147 -> Д150 ->
    Д152 -> Д153). Полное обоснование и формулировки И1-И6 - баннер над
    константой `START_SCAN_INVARIANTS` выше.

    🔴 Д47 (дисциплина файла): SKIP ровно на один случай - хука нет на диске.
    Любой другой отказ выреза - FAIL с честной причиной."""
    dd, dderr = _hook_donordev_state()
    dl, dlerr = _hook_deadlang_state()
    rf, rferr = _hook_readflag_state()
    for err in (dderr, dlerr, rferr):
        if err == "NOHOOK":
            skip("контракт START-скана: инвариант-матрица И1-И6",
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
    for fn, err, nm in ((dd, dderr, "donor-devices"), (dl, dlerr, "dead-language"),
                        (rf, rferr, "readflag")):
        if fn is None:
            record("контракт START-скана: инвариант-матрица И1-И6 (%s не "
                   "вырезалась)" % nm, False, err)
            return
    body = {
        "DD": lambda v: dd("donor-devices: %s\nВЕРДИКТ: PASS\n" % v),
        "DL": lambda v: dl("dead-language: %s\nВЕРДИКТ: PASS\n" % v),
        "RF": lambda v: rf("donordev_read: %s\nzhivoy_yazyk_read: PASS\n"
                           "ВЕРДИКТ: PASS\n" % v),
    }
    bad = []
    for grp, what, layer, val, want in START_SCAN_INVARIANTS:
        got = body[layer](val)
        if got != want:
            bad.append("%s/%s «%s»: ждём %r, получили %r"
                       % (grp, layer, what, want, got))
    record("контракт START-скана donor-devices/dead-language: инвариант-"
           "матрица И1-И6, %d форм Д147/Д150/Д152/Д153/Д154/Д159/Д160/Д161/"
           "Д164/Д165/Д168 + контроли" % len(START_SCAN_INVARIANTS), not bad,
           "; ".join(bad[:12]))


# 🔴 Д171 (misdiagnosis, скептик-раунд 58, по решению автора): контрактный ЗАМОК
# на страховочный блок ЧУЖИМ гейтом - НЕ дефект, РЕШЕНИЕ ОРКЕСТРАТОРА не
# чинить маской (полное обоснование - баннер в докстринге
# `_deadlang_clean_admits_absence` в самом хуке, перед вызовом `lead =
# _deadlang_mask_read_lines(lead)`).
#
# Именованная цена Д168 («из справочника ничего не взял» / «приёмов
# ничего не дало» - предмет ДО квантора «ничего», DD осознанно даёт `OK`,
# см. `START_SCAN_INVARIANTS` группа Д168-ЦЕНА выше) в ЖИВОМ E2E ВСЁ
# РАВНО блокируется - через `_deadlang_clean_admits_absence`: lead/tail-
# окно вокруг `dead-language: чисто` содержит СОСЕДНЮЮ строку `donor-
# devices: …из справочника ничего не взял`, клауза несёт И «справочник»
# (`_DEADLANG_SUBJECT_RE`), И «не» (`_DEADLANG_ADMIT_RE` - голый `не\\b`) -
# функция честно возвращает `True`, гейт даёт `DEADLANG_NO`. Диагноз
# оператору НЕВЕРНЫЙ (BLOCK-текст говорит про «мёртвый язык», причина
# реально - неопознанный приём донора), НО САМ БЛОК ДЕРЖИТСЯ - пост с
# непроверенным приёмом не выпускается.
#
# ПОЧЕМУ НЕЛЬЗЯ ЧИНИТЬ МАСКОЙ: добавить `donor-devices:`-строки в
# `_deadlang_mask_read_lines()` (рядом с уже маскируемыми `*_read`-
# строками, Д124б) ВЫГЛЯДИТ как починка диагноза, но СНИМЕТ ЭТУ ФУНКЦИЮ
# КАК ПОСЛЕДНЮЮ СТРАХОВКУ именно для 2 из 9 форм, где DD намеренно даёт
# `OK` - результат: ЧИСТЫЙ FAIL-OPEN (ни DD, ни DL не поймает). Хук НЕ
# ТРОНУТ в этой части ни на строку - фикс Д171 только (1) банер-
# документация в хуке, (2) одна строка-подсказка в BLOCK-тексте
# `DEADLANG_NO` (текст сообщения, `case`-ветка та же), (3) ЭТОТ тест-замок
# ниже, чтобы будущая правка, которая ТИХО добавит маску и уберёт
# страховку, покраснела здесь же.
def test_d171_deadlang_foreign_gate_safety_net():
    """🔴 Д171-замок: DD осознанно пропускает именованную цену Д168 (`OK`),
    DL страхует её ЧЕРЕЗ lead/tail-окно (`DEADLANG_NO`) - живьём, на ОБОИХ
    слоях сразу, той же комбинированной строкой отчёта, что реально
    печатает верификатор (donor-devices ПЕРЕД dead-language, канонный
    порядок полей 04-review.md 4.M.2)."""
    dd, dderr = _hook_donordev_state()
    dl, dlerr = _hook_deadlang_state()
    for err in (dderr, dlerr):
        if err == "NOHOOK":
            skip("Д171: DD осознанно пропускает цену Д168, DL страхует "
                 "чужим гейтом (безопасно, не маскировать)",
                 "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
            return
    if dd is None or dl is None:
        record("Д171: DD осознанно пропускает цену Д168, DL страхует "
               "чужим гейтом (безопасно, не маскировать)", False,
               dderr or dlerr)
        return
    report = ("donor-devices: §2.3 «улика» -> PASS, из справочника ничего "
              "не взял\n"
              "donordev_read: PASS\n"
              "dead-language: чисто\n"
              "zhivoy_yazyk_read: PASS\n"
              "ВЕРДИКТ: PASS\n")
    dd_got = dd(report)
    dl_got = dl(report)
    bad = []
    if dd_got != "OK":
        bad.append("DD: ждём OK (именованная цена Д168 держится - предмет "
                    "ДО квантора «ничего» вне И6-дисциплины), получили %r" % dd_got)
    if dl_got != "NO":
        bad.append("DL: ждём NO (страховочный блок ЧЕРЕЗ lead-окно "
                    "`_deadlang_clean_admits_absence` - «справочник»+«не» в "
                    "СОСЕДНЕЙ donor-devices-строке) - получили %r; если "
                    "здесь стало OK, кто-то замаскировал donor-devices: в "
                    "_deadlang_mask_read_lines - ЭТО ЧИСТЫЙ FAIL-OPEN, "
                    "откатить немедленно" % dl_got)
    record("Д171: DD осознанно пропускает цену Д168 (OK) - DL страхует её "
           "ЧЕРЕЗ чужой гейт (DEADLANG_NO, lead-окно) - НЕ чинить маской, "
           "см. докстринг _deadlang_clean_admits_absence в хуке",
           not bad, "; ".join(bad))


# ===========================================================================
# 🔴 КЛАСС-СТРАЖ Д175 (скептик-раунд 60, по решению автора): ПОЗИЦИОННАЯ МАТРИЦА
# «СЛОВАРЬ ОТКАЗА x ПОЗИЦИЯ СКАНА» - КАЖДАЯ ЯЧЕЙКА ДОЛЖНА БЛОКИРОВАТЬ.
#
# ЗАЧЕМ ОТДЕЛЬНЫМ СТРАЖОМ, А НЕ ЕЩЁ ОДНОЙ ПАЧКОЙ КЕЙСОВ В
# `START_SCAN_INVARIANTS`. Класс «новый словарь отказа не проброшен во ВСЕ
# пути скана» повторился ТРИЖДЫ подряд, каждый раз новым путём и каждый раз
# его находил ЧЕЛОВЕК, а не прогон:
#   Д170 (раунд 58) - `_donordev_solo_quote_refusal` (И5) звала
#                     `_donordev_segment_refusal` БЕЗ `free_re`;
#   Д172 (раунд 59) - рекурсия по `quote_tail` звала САМА СЕБЯ БЕЗ `free_re`;
#   Д175 (раунд 60) - `_DONORDEV_NO_DALO_RE` (Д173) жила ТОЛЬКО в двух
#                     плоских дизъюнкциях верхнего уровня и не доезжала ни до
#                     И5, ни до `quote_tail` (24/32 формы выпускались БЕЗ
#                     блока, `scratchpad/r63/d175_quotegrid.py`).
# Точечные кейсы ловят ИНСТАНС (конкретная форма, конкретный путь) - и
# зеленеют ровно до следующего нового словаря. Этот страж ловит КЛАСС: он
# перебирает ВСЕ словари отказа DD против ВСЕХ позиций скана и требует блок
# в КАЖДОЙ ячейке. Новый словарь добавляется одной строкой в
# `D175_REFUSAL_DICTS` - и обязан немедленно проехать по всем позициям, иначе
# страж красный (`feedback_skeptic_loop_class_defect_not_instance`,
# `feedback_point_patch_in_one_branch_is_not_a_fix`).
#
# СЛОВАРИ (все ЧЕТЫРЕ поверхности отказа donor-devices):
#   START  - `_DONORDEV_NO_START_RE`, якорный скан начала сегмента (И2/И3/И4);
#   FREE   - `_DONORDEV_NO_FREE_RE`, безъякорный двойник того же словаря (И6,
#            Д168) - срез `.pattern`, отдельного литерала нет;
#   PHRASE - `_DONORDEV_NO_PHRASE_RE`, standalone-словарь, режим `"with"`
#            (кавычки = обычный контент, размен Д43 принят раундом 10);
#   DALO   - `_DONORDEV_NO_DALO_RE`, standalone-словарь, режим `"stripped"`
#            (Д173, Д43-класс снят ДЛЯ ЭТОГО словаря собственным строгим
#            совпадением).
# PHRASE и DALO с Д175 достаются ЕДИНОЙ точкой `_donordev_standalone_refusal`
# из кортежа `_DONORDEV_NO_STANDALONE` в хуке - страж проверяет, что эта
# точка реально доезжает ДО КАЖДОГО пути, а не только до верхнего уровня.
#
# ПОЗИЦИИ (все места, где скан вообще может встретить отказ - см. баннер
# инвариантов И1-И6 перед `_donordev_segment_refusal` в самом хуке):
#   И2 line-start · И3 голый токен в не-первом сегменте · И4 токен + хвост-
#   ПРЕДМЕТ · И6 вводное слово перед токеном (свободный скан) · И5 сегмент
#   ЦЕЛИКОМ закавыченный спан (ёлочки И бэктики - РАЗНЫЕ классы пар в
#   `_DONORDEV_QUOTE_PAIRS`, оба обязаны разворачиваться) · quote_tail -
#   ПРЕДМЕТ снаружи, отказ ЦЕЛИКОМ внутри соседней цитаты (позиция, которой
#   Д175 и течела).
#
# ИЗМЕРЕНО ЖИВЬЁМ (`scratchpad/r64/d175_posmatrix_probe.py`, тот же
# экстрактор, что у стража): на живом хуке ДО патча R64 - 5 из 28 ячеек
# выпускали пост БЕЗ БЛОКА (START/FREE в `quote_tail`, DALO в И5-ёлочках,
# И5-бэктиках и `quote_tail`); на патченной копии - 0 из 28.
#
# МУТАЦИОННО ПРОВЕРЕНО (постоянным тестом не оформить - мутация ломает сам
# хук; улика - `scratchpad/r64/mutcheck_r64.py` + `mutcheck_r64.log`):
#   M2 (убран `standalone=` из главного цикла сегментов) -> КРАСНЫЙ, назвал
#      DALO x quote_tail;
#   M3 (словарь DALO вынут из `_DONORDEV_NO_STANDALONE`) -> КРАСНЫЙ, назвал
#      ВСЕ 7 позиций DALO разом;
#   M4 (убрана атомарная ветка `quote_tail` Д175) -> КРАСНЫЙ, назвал ровно
#      течь Д175: START/FREE/DALO x quote_tail.
#   M1 (убран `standalone=` из вызова `_donordev_solo_quote_refusal`/И5) ->
#      ЗЕЛЁНЫЙ, И ЭТО ВЕРНО: проводка через И5 ИЗБЫТОЧНА - атомарная ветка
#      `quote_tail` того же фикса доминирует И5 для standalone-словарей.
#      Доказано дифференциальным прогоном (`scratchpad/r64/
#      m1_differential.py`): 1728 форм (6 классов кавычек x 12 фраз x 12
#      обвязок x закавычено/нет) - 0 расхождений между воркопией и мутантом.
#      Страж судит НАБЛЮДАЕМЫЙ результат (заблокировано или нет), а не
#      маршрут; оба проброса оставлены в хуке НАРОЧНО, чтобы контракт
#      «новый словарь едет ВЕЗДЕ» не зависел от того, какой путь сегодня
#      кого доминирует.
# ===========================================================================

# (имя словаря, ГОЛАЯ форма отказа, форма «отказ + хвост-ПРЕДМЕТ»)
D175_REFUSAL_DICTS = [
    ("START", "нет", "нет подходящего приёма"),
    ("FREE", "ни один", "ни один приём не подошёл"),
    ("PHRASE", "не подошёл", "приём не подошёл"),
    ("DALO", "ничего не дало", "приёмов ничего не дало"),
]

# (имя позиции, сборщик значения строки `donor-devices:` из (голая, с хвостом))
D175_POSITIONS = [
    ("И2 line-start", lambda bare, tail: tail),
    ("И3 голый токен", lambda bare, tail: "§2.3 «улика» -> %s" % bare),
    ("И4 хвост-предмет", lambda bare, tail: "§2.3 «улика» -> %s" % tail),
    ("И6 вводное слово", lambda bare, tail: "§2.3 «улика» -> но %s" % tail),
    ("И5 соло-цитата ёлочки", lambda bare, tail: "§2.3 улика -> «%s»" % tail),
    ("И5 соло-цитата бэктики", lambda bare, tail: "§2.3 улика -> `%s`" % tail),
    ("quote_tail (предмет снаружи, отказ в цитате)",
     lambda bare, tail: "§2.3 улика -> PASS, приёмов «%s»" % bare),
]

# 🔴 МАНИФЕСТ NAMED-ИСКЛЮЧЕНИЙ. Ячейки матрицы выше обязаны блокировать ВСЕ
# без изъятия - поэтому всё, что НЕ блокирует (или блокирует ЛОЖНО), названо
# здесь ПОИМЁННО, с ожиданием и ПРИЧИНОЙ-решением, а не молчит пропуском.
# Формат: (имя, значение строки donor-devices, ожидание, причина-решение).
D175_NAMED_EXCEPTIONS = [
    ("PHRASE x цитата: честная цитата поста с «не подошёл» внутри «…»",
     "§2.3 «этот заход мне не подошёл по тону, взял другой» -> PASS", "NO",
     "РАЗМЕН Д43 (раунд 10, принят и НЕ пересматривается Д175): PHRASE "
     "сканирует `_donordev_soft(raw_full)` - кавычки участвуют как обычный "
     "контент, поэтому честная цитата поста с PHRASE-глаголом даёт ЛОЖНЫЙ "
     "BLOCK. Цена названа, видна оператору текстом BLOCK, снимается "
     "перестройкой цитаты. Ждём NO не потому, что это правильно, а потому "
     "что это ИЗВЕСТНАЯ цена - если здесь станет OK, кто-то ТИХО поменял "
     "режим PHRASE со `\"with\"` на `\"stripped\"` в `_DONORDEV_NO_STANDALONE`"),
    ("DALO x цитата: честная многоклаузная цитата «ничего не дало»",
     "§2.3 «в первый месяц ничего не дало эффекта, потом пошло» -> PASS", "OK",
     "РЕШЕНИЕ Р59 (Д173): кандидат (б) «добавить `ничего не дал\\w*` прямо в "
     "PHRASE» ОТВЕРГНУТ живым прогоном (`scratchpad/r63/d173_falsepos_"
     "probe.py`, 2/2 честные цитаты ловились ложно) - вместо него отдельный "
     "словарь `_DONORDEV_NO_DALO_RE` в режиме `\"stripped\"`: Д43-класс снят "
     "ДЛЯ НЕГО ОДНОГО. Ждём OK - если здесь станет NO, Д43-размен молча "
     "расползся на DALO и честная цитата поста больше не проходит"),
    ("Д175 guard атомарности: та же цитата в ХВОСТЕ после предмета",
     "§2.3 улика -> PASS, приёмов «в первый месяц ничего не дало эффекта, "
     "потом пошло»", "OK",
     "GUARD АТОМАРНОСТИ Д175: `quote_tail`-запись участвует в новой ветке "
     "ТОЛЬКО если её содержимое НЕ несёт разделителя `_DONORDEV_START_SPLIT_"
     "RE` - у И5 та же защита стоит СТРУКТУРНО (разрезка сырого текста ДО "
     "поиска цитаты рвёт многоклаузную цитату на несбалансированные "
     "обрывки), у `quote_tail` её пришлось сделать ЯВНОЙ. Без guard'а этот "
     "кейс - НОВЫЙ ложный BLOCK (живой репро `scratchpad/r64/`). Ждём OK"),
    ("И4 честная улика-отсутствие (§5.2 нулевой CTA)",
     "§5.2 «Такие дела» -> PASS · нет адреса и нет глагола-призыва", "OK",
     "И4-контракт (Д153-б): токен отказа + хвост, НЕ называющий ПРЕДМЕТ "
     "гейта, есть УЛИКА-ОТСУТСТВИЕ, а не признание - отсутствие адреса и "
     "глагола-призыва И ЕСТЬ суть приёма §5.2. Ждём OK: если новая проводка "
     "словарей начнёт блокировать эту форму, Д153-б откатился"),
    ("🔴 НОВАЯ ЦЕНА Д175 (1/2): ОДНОклаузная честная цитата поста без "
     "разделителя, содержимое читается отказом",
     "§2.3 смена системы отсчёта «ничего не дало» -> PASS", "NO",
     "ЦЕНА АТОМАРНОЙ ВЕТКИ Д175, НАЗВАНА ЧЕСТНО (не молчаливый пропуск, но и "
     "НЕ решение). Guard атомарности спасает только МНОГОклаузную цитату (в "
     "ней есть разделитель `_DONORDEV_START_SPLIT_RE`); ОДНОклаузная цитата, "
     "чьё содержимое само читается отказом, теперь блокируется, даже когда "
     "она честная улика поста. На живом хуке ДО патча здесь было `OK`. Это "
     "РАСШИРЕНИЕ по сравнению с Д161: та ветка рекурсировала в цитату ТОЛЬКО "
     "когда бар-текст сегмента УЖЕ начинался словарём отказа, новая ветка "
     "такого условия не ставит. Кандидат на сужение (потребовать, чтобы "
     "бар-текст называл ПРЕДМЕТ) - решение владельца/оркестратора; если ветку "
     "сузят, этот кейс переедет в `OK`, и страж об этом честно скажет"),
    ("🔴 НОВАЯ ЦЕНА Д175 (2/2): цитата-улика из ОДНОГО слова «нет» рядом с "
     "валидной §-ссылкой",
     "§2.3 улика «нет» -> PASS", "NO",
     "Тот же класс, что запись выше, острый край: по И1 «цитата = данные» и "
     "по И4 «цитата = улика-отсутствие» эта форма ДОЛЖНА была бы проходить "
     "(на живом хуке ДО патча - `OK`), но атомарная ветка Д175 читает "
     "содержимое цитаты как отказ независимо от бар-текста. В контрактном "
     "корпусе (`START_SCAN_INVARIANTS` 262 формы) этой формы нет - грепом "
     "подтверждено, поэтому патч не даёт регресса по корпусу; цена "
     "теоретическая по корпусу, но РЕАЛЬНАЯ по семантике - названа здесь, "
     "чтобы не жить молча"),
    ("зелёный контроль: обычный честный отчёт",
     "§2.3 смена системы отсчёта «за 3 месяца» -> PASS", "OK",
     "База: ни один словарь отказа не срабатывает на честном отчёте. Если "
     "красное здесь - новая проводка блокирует ВСЁ подряд"),
]


def test_d175_refusal_dictionary_position_matrix():
    """🔴 КЛАСС-СТРАЖ Д175: КАЖДЫЙ словарь отказа DD x КАЖДАЯ позиция скана.

    Полное обоснование (почему класс, а не инстанс; три повтора Д170 → Д172
    → Д175; измерения 5/28 на живом ДО и 0/28 на патче) - баннер над
    `D175_REFUSAL_DICTS` выше.

    Матрица требует `NO` (блок) в КАЖДОЙ из 4x7 ячеек. Всё, что законно НЕ
    блокирует (или блокирует известной ЦЕНОЙ), вынесено в манифест
    `D175_NAMED_EXCEPTIONS` с ожиданием и причиной-решением - молчаливых
    пропусков в этом страже нет по построению.

    🔴 Д47 (дисциплина файла): SKIP ровно на один случай - хука нет на
    диске. Любой другой отказ выреза - FAIL с честной причиной."""
    dd, dderr = _hook_donordev_state()
    if dderr == "NOHOOK":
        skip("класс-страж Д175: позиционная матрица словарей отказа DD",
             "хука post-phase-gate.sh нет на этой машине (%s)" % HOOK)
        return
    if dd is None:
        record("класс-страж Д175: позиционная матрица словарей отказа DD",
               False, dderr)
        return

    def _state(val):
        return dd("donor-devices: %s\nВЕРДИКТ: PASS\n" % val)

    bad = []
    cells = 0
    for dname, bare, tail in D175_REFUSAL_DICTS:
        for pname, mk in D175_POSITIONS:
            val = mk(bare, tail)
            cells += 1
            got = _state(val)
            if got != "NO":
                bad.append("%s x %s: ждём NO (блок), получили %r - «%s»"
                           % (dname, pname, got, val))
    for name, val, want, why in D175_NAMED_EXCEPTIONS:
        got = _state(val)
        if got != want:
            bad.append("named-исключение «%s»: ждём %r, получили %r; ПРИЧИНА "
                       "ожидания: %s" % (name, want, got, why))
    record("класс-страж Д175: позиционная матрица словарей отказа DD - "
           "%d ячеек (%d словарей x %d позиций) + %d named-исключений "
           "манифестом" % (cells, len(D175_REFUSAL_DICTS),
                           len(D175_POSITIONS), len(D175_NAMED_EXCEPTIONS)),
           not bad, "; ".join(bad[:12]))


# ===========================================================================
# 🔴 КЛАСС-СТРАЖ Д177 (скептик-раунд 60, по решению автора): КАЖДЫЙ ЗАЯВЛЕННЫЙ В
# SKILL.md РЕЛИЗ `v2.4-rNN` ОБЯЗАН ИМЕТЬ ЗАПИСЬ В `knowledge/changelog.md`.
#
# ПРЕЦЕДЕНТ Д177: SKILL.md нёс блёрбы `v2.4-r61` и `v2.4-r62` (раунды 58 и
# 59, дефекты Д169-Д174), а `knowledge/changelog.md` обрывался на
# `v2.4-r60` - ДВЕ версии существовали только в шапке скилла. Формат
# changelog'а сам себя объявляет полной историей («Полная история версий
# скилла… В SKILL.md остались текущая версия + однострочное резюме + ссылка
# сюда»), то есть разрыв - не косметика: разбор «когда и почему это правило
# появилось» по changelog'у ВРЁТ, а именно за этим его и заводили.
#
# КЛАСС, А НЕ ИНСТАНС: Д174 (раунд 59) уже чинил ПОРЯДОК записей changelog'а
# руками, Д177 - их НАЛИЧИЕ. Ручная дисциплина «не забыть дописать» этот
# класс не держит (ровно тот же вывод, что у Д162 про стухший чекбокс
# плана) - нужен страж, читающий ОБА файла на каждом прогоне.
#
# ГРАНИЦА rNN >= 43 и NAMED-ИСКЛЮЧЕНИЯ r41/r42: история до r43 сложилась ДО
# того, как changelog стал обязательным местом записи (r41/r42 названы
# поимённо ниже с причиной - они физически отсутствуют в changelog'е с
# момента его выделения из SKILL.md и переписывать историю задним числом
# протокол Д31 запрещает). Новая версия НИЖЕ границы не появляется по
# построению - номера растут.
#
# ПОРТАТИВНОСТЬ: оба файла - часть РАЗДАВАЕМОГО скилла, автор-специфики в
# страже нет; на машине без одного из файлов - честный SKIP.
# ===========================================================================
D177_MIN_ROUND = 43
D177_NAMED_EXCEPTIONS = {
    "41": "r41/r42 сложились ДО выделения changelog'а из SKILL.md - записей "
          "в knowledge/changelog.md у них нет с самого начала его истории; "
          "дописывать задним числом = переписывать историю (протокол Д31)",
    "42": "то же, что r41 - см. причину выше",
}


def test_d177_skill_versions_have_changelog_entries():
    """🔴 КЛАСС-СТРАЖ Д177: SKILL.md заявил релиз - changelog обязан его
    нести.

    Полное обоснование (прецедент r61/r62, почему класс, почему граница
    r43 и почему r41/r42 - named-исключения) - баннер выше.

    SKIP ровно на один случай - нет одного из двух файлов на диске (машина
    ученика с урезанной раздачей). Любой другой отказ - FAIL."""
    skill_md = os.path.join(SKILL_ROOT, "SKILL.md")
    chlog = os.path.join(SKILL_ROOT, "knowledge", "changelog.md")
    for p in (skill_md, chlog):
        if not os.path.exists(p):
            skip("класс-страж Д177: релизы SKILL.md ↔ записи changelog.md",
                 "нет файла %s на этой машине" % p)
            return
    try:
        sk = open(skill_md, encoding="utf-8").read()
        cl = open(chlog, encoding="utf-8").read()
    except OSError as e:
        record("класс-страж Д177: релизы SKILL.md ↔ записи changelog.md",
               False, "файл не читается: %s" % e)
        return
    rx = re.compile(r"v2\.4-r(\d+)")
    declared = sorted({m.group(1) for m in rx.finditer(sk)}, key=int)
    present = {m.group(1) for m in rx.finditer(cl)}
    missing = []
    excepted = []
    checked = 0
    for n in declared:
        # named-исключение проверяется ПЕРВЫМ, ДО порога: иначе r41/r42
        # (оба НИЖЕ порога 43) вылетали бы по порогу молча, манифест ни разу
        # не срабатывал бы, и обратная проверка «исключение протухло» была
        # бы мёртвой - ровно тот класс холостого барьера, что чинил Д163.
        if n in D177_NAMED_EXCEPTIONS:
            excepted.append(n)
            continue
        if int(n) < D177_MIN_ROUND:
            continue
        checked += 1
        if n not in present:
            missing.append(
                "v2.4-r%s заявлена в SKILL.md, но записи «v2.4-r%s» НЕТ в "
                "knowledge/changelog.md - допиши запись (формат: заголовок → "
                "прецедент → root cause → фикс → затронутые файлы), история "
                "версий обязана быть полной" % (n, n))
    for n in sorted(D177_NAMED_EXCEPTIONS, key=int):
        if n in present:
            missing.append(
                "v2.4-r%s числится named-исключением (%s), но запись в "
                "changelog.md ПОЯВИЛАСЬ - сними исключение из "
                "D177_NAMED_EXCEPTIONS, иначе манифест врёт"
                % (n, D177_NAMED_EXCEPTIONS[n][:60]))
    record("класс-страж Д177: каждый релиз v2.4-rNN (NN>=%d) из SKILL.md "
           "имеет запись в knowledge/changelog.md - %d проверено, %d "
           "named-исключений (r%s)"
           % (D177_MIN_ROUND, checked, len(excepted),
              ", r".join(excepted) if excepted else "-"),
           not missing, "; ".join(missing[:8]))


# 🔴 Д162 (класс-повтор Д156/Д90 - стухший чекбокс плана, скептик-раунд 54,
# по решению автора): МАШИННЫЙ барьер вместо ручной галочки. Ручные чекбоксы
# «патч R(N) ПОДГОТОВЛЕН, не применён» в плане возвращаются стухшими -
# владелец применяет патч, а строка плана всё ещё несёт `[ ]` и текст «не
# применён», врёт о состоянии живого хука (прецедент Д156, раунд 53:
# `run-tests.py` живой держал 383/383, чекбокс держал `[ ]`; тот же класс
# ещё раньше - Д90). Ручная память НЕ держит этот класс дисциплины - нужен
# страж, читающий диск на каждый прогон, не «не забыть поднять».
#
# ПОРТАТИВНОСТЬ (изоляция автор-специфики, `~/.claude/skills/post/`
# раздаётся ученикам целиком - `feedback_isolate_ivan_specific_from_
# student_shipped_artifacts`): путь плана НЕ хардкодит имя запуска/донора -
# конкретное имя файла плана автор-специфично и уедет в раздачу, если
# вписать буквально. Разрешение пути - см.
# `_phase_gate_plan_paths` ниже: явный env-override -> контентный glob по
# `plans/*.md` (маркер `post-phase-gate.FIX-R`, строка САМОГО хука,
# не имя запуска) -> ничего не найдено на машине ученика (нет `~/IvanOS/
# plans` вовсе) -> `[]`, тест тихо SKIP, не FAIL.
#
# 🔴 ФИКС Д163 (критический, скептик-раунд 55, по решению автора): БАРЬЕР Д162
# БЫЛ ХОЛОСТ - ТРИ ДЫРЫ ОДНОВРЕМЕННО, `checked` НА ЖИВОМ ПЛАНЕ ВСЕГДА
# ДЕРЖАЛ 0, БАРЬЕР ПРОВЕРЯЛ ПУСТОЕ МНОЖЕСТВО И ВСЕГДА ЗЕЛЕНЕЛ.
# (1) ФРАЗА: старый регекс ждал ДОСЛОВНО и РЕГИСТРОЗАВИСИМО (флага re.I не
#     было) «патч R(N) ПОДГОТОВЛЕН, не применён» - а домашний стиль плана
#     (КАЖДАЯ строка «Фиксы Р…» этой сессии) пишет «Патч R(N) подготовлен
#     и полностью верифицирован … применяет владелец» (заглавная «П»,
#     другие слова, БЕЗ «не применён» вовсе). Живая улика: грепом по
#     плану фраза «Патч R» встречается 47+ раз, совпадений старого
#     регекса - НОЛЬ.
# (2) ОКНО: `.{0,400}?` между чекбоксом и фразой обрезало текст ДО
#     реального смещения - в живых строках плана «Патч R(N)» стоит на
#     офсете 750-2375 символов от начала строки (грепом по plans/2026-08-
#     07-post-tretiy-donor-amirkhanyan.md), даже верная фраза была бы вне
#     окна.
# (3) ОДИН ФАЙЛ: `_phase_gate_plan_path` (единственное число) брала
#     САМЫЙ СВЕЖИЙ по mtime файл с маркером - стухшая строка в ДРУГОМ
#     (не самом свежем) файле с тем же маркером осталась бы в тени.
# ФИКС: (1) инвариант упрощён - ЛЮБАЯ незакрытая строка `- [ ]` (буквально
# пробел в скобках - закрытые `[x]`-строки НЕ триггер вовсе, история не
# переписывается, протокол Д31), содержащая (РЕГИСТРОНЕЗАВИСИМО) «патч
# R(\d+)» И один из ТРЁХ маркеров («не применён» | «применяет владелец» |
# «подготовлен») ГДЕ УГОДНО в строке - кандидат на проверку бэкапа; (2)
# окно убрано - сканируется строка ЦЕЛИКОМ; (3) `_phase_gate_plan_path`
# заменена на `_phase_gate_plan_paths` (МНОЖЕСТВЕННОЕ число) - возвращает
# ВСЕ файлы с маркером, тест проходит по КАЖДОМУ, не по одному самому
# свежему.
# МУТАЦИОННО ПРОВЕРЕНО (постоянным тестом не оформить - мутации плана,
# улики - scratchpad r59/mutcheck_d163.py + verify-FIX-R59.output.log):
# кейс A (стухшая строка в домашнем стиле, зеркало реальной «Фиксы Р…») -
# красный; кейс B (дословная старая фраза «ПОДГОТОВЛЕН, не применён» в
# начале строки) - красный; кейс C (фраза на офсете 2000+) - красный;
# кейс D (стухшая строка во ВТОРОМ файле по mtime, не в самом свежем) -
# красный; чистый план (маркеры есть, бэкапа нет - патч ещё не применён)
# - зелёный; закрытая `[x]`-строка с теми же словами - зелёный (не
# триггер, ложняков на исторических строках плана - которых МНОГО - быть
# не должно).
def _phase_gate_plan_paths():
    """Путь(-и) до планов, отслеживающих раунды `post-phase-gate.sh`
    (Д162 + расширение Д163, скептик-раунд 55, по решению автора - сканирует ВСЕ
    файлы с маркером, не один самый свежий, см. дыра (3) в баннере ФИКСА
    Д163 выше). Приоритет: (1) env `POST_PHASE_GATE_PLAN_PATH` - явный
    ОДИН путь для нестандартного расположения (список из одного файла,
    если он существует); (2) ВСЕ файлы `plans/*.md`,
    отфильтрованные по СОДЕРЖИМОМУ (маркер `post-phase-gate.FIX-R`),
    отсортированные по mtime (свежие первыми - порядок не влияет на
    корректность после Д163, оставлен для стабильного вывода); (3)
    пустой список - `~/IvanOS/plans` нет или ни один файл маркер не несёт
    (машина ученика)."""
    override = os.environ.get("POST_PHASE_GATE_PLAN_PATH")
    if override:
        return [override] if os.path.isfile(override) else []
    plans_dir = os.path.expanduser("~/IvanOS/plans")
    if not os.path.isdir(plans_dir):
        return []
    candidates = []
    for path in glob.glob(os.path.join(plans_dir, "*.md")):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if "post-phase-gate.FIX-R" in text:
            candidates.append((os.path.getmtime(path), path))
    candidates.sort(reverse=True)
    return [path for _, path in candidates]


_PHASE_GATE_PATCH_NUM_RE = re.compile(r"патч\s+R(\d+)", re.I)
_PHASE_GATE_STALE_FLAG_RE = re.compile(
    r"не\s+примен[её]н|применяет\s+владелец|подготовлен", re.I)


def test_plan_hook_backup_consistency():
    """🔴 Д162 + ФИКС Д163 (барьер Д162 был холост - три дыры разом,
    скептик-раунд 55, по решению автора, полное обоснование - баннер ПЕРЕД
    `_phase_gate_plan_paths` выше): находит в КАЖДОМ плане
    (`_phase_gate_plan_paths`) незакрытые строки `- [ ] …`, которые
    (регистронезависимо) несут И «патч R(\\d+)», И один из трёх маркеров
    «не применён»/«применяет владелец»/«подготовлен» ГДЕ УГОДНО в строке
    (окно убрано - была дыра (2) Д163). Для КАЖДОГО найденного N
    проверяет: существует ли на диске `~/.claude/hooks/post-phase-
    gate.sh.bak-R(N)-*` - самоприменитель (`post-phase-gate.FIX-R(N).sh`,
    протокол R51-R59) создаёт ИМЕННО такой бэкап НЕПОСРЕДСТВЕННО ПЕРЕД
    `mv` на цель, то есть бэкап на диске = патч физически применён к
    живому хуку. Если бэкап ЕСТЬ, а чекбокс строки всё ещё `[ ]` - FAIL с
    именем файла и номером патча: план врёт оператору, подними галочку.

    Чекбокс `[x]` (закрытая строка) НЕ триггер вовсе - матчится ТОЛЬКО
    буквальное `- [ ]` (пробел внутри скобок); закрытые строки не
    сканируются, даже если несут слово «применён»/«подготовлен» как
    ИСТОРИЮ (протокол Д31) - живой план несёт МНОГО таких строк («Фиксы
    Р…» прошлых раундов), ни одна не должна давать ложный FAIL.

    SKIP (не FAIL), если НИ ОДИН план не найден - машина ученика,
    портативность, см. `_phase_gate_plan_paths`. Сбой ЧТЕНИЯ найденного
    файла - FAIL с причиной, не тихий SKIP (Д47: дисциплина файла - SKIP
    только на ОДИН случай, «файла на диске нет вовсе»)."""
    plan_paths = _phase_gate_plan_paths()
    if not plan_paths:
        skip("план↔хук: консистентность чекбокса «патч R(N) подготовлен»",
             "план post-phase-gate.sh не найден на этой машине (нет "
             "~/IvanOS/plans или ни один файл не несёт маркер "
             "post-phase-gate.FIX-R - машина ученика, изоляция автор-специфики)")
        return
    stale = []
    checked = 0
    seen = set()  # (plan_path, n) - строка «Фиксы Р…» часто поминает свой
                   # раунд ДВАЖДЫ («патч R58 ПРИМЕНЁН … Патч R58 подготовлен
                   # … применяет владелец») - дедуп по (файл, N), чтобы
                   # verdict не дублировал одно и то же сообщение
    read_errors = []
    for plan_path in plan_paths:
        try:
            with open(plan_path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            read_errors.append("%s: %s" % (plan_path, e))
            continue
        for line in text.splitlines():
            if not line.startswith("- [ ]"):
                continue
            if not _PHASE_GATE_STALE_FLAG_RE.search(line):
                continue
            for m in _PHASE_GATE_PATCH_NUM_RE.finditer(line):
                checked += 1
                n = m.group(1)
                key = (plan_path, n)
                if key in seen:
                    continue
                seen.add(key)
                hits = glob.glob(os.path.expanduser(
                    "~/.claude/hooks/post-phase-gate.sh.bak-R%s-*" % n))
                if hits:
                    stale.append(
                        "%s: патч R%s: строка плана держит «- [ ] …», но "
                        "%d бэкап(ов) .bak-R%s-* уже на диске - патч "
                        "ПРИМЕНЁН, строка плана врёт - подними галочку"
                        % (os.path.basename(plan_path), n, len(hits), n))
    if read_errors:
        record("план↔хук: консистентность чекбокса «патч R(N) подготовлен» "
               "(%d файл(ов) не читается)" % len(read_errors),
               False, "; ".join(read_errors))
        return
    record("план↔хук: консистентность чекбокса «патч R(N) подготовлен» "
           "(%d строк(и) проверено, %d файл(ов): %s)"
           % (checked, len(plan_paths),
              ", ".join(os.path.basename(p) for p in plan_paths)),
           not stale, "; ".join(stale))


HOOK_TESTS = [test_hook_no_forgeable_greps, test_hook_executes_checks_itself,
              test_hook_no_journal_writes, test_hook_syntax,
              test_hook_event_class_reaches_lint, test_hook_unknown_class_blocks,
              test_hook_case_knows_event, test_hook_pair_gate, test_hook_donordev_gate,
              test_donordev_reference_sections, test_donordev_signature_guard,
              test_donordev_missing_reference_is_hard_fail,
              test_hook_donordev_d133_d134,
              test_hook_donordev_d135_d136,
              test_hook_donordev_d137_d138,
              test_hook_donordev_d139_d140,
              test_hook_verifier_last_answer,
              test_hook_deadlang_gate,
              test_hook_deadlang_markdown_labels,
              test_deadlang_missing_reference_is_hard_fail,
              test_hook_deadlang_d133_d134,
              test_hook_deadlang_d135_d136,
              test_hook_deadlang_d137_d138,
              test_hook_deadlang_d139_d140,
              test_hook_readflag_gate,
              test_matrix_typography_invariant,
              test_matrix_recognition_parity,
              test_matrix_refusal_dictionary_coverage,
              test_matrix_named_exceptions,
              test_matrix_compact_line_regression,
              test_donordev_start_scan_invariants,
              test_d171_deadlang_foreign_gate_safety_net,
              test_d175_refusal_dictionary_position_matrix,
              test_d177_skill_versions_have_changelog_entries,
              test_plan_hook_backup_consistency,
              test_hook_invocable,
              *D100_CLASSIFIER_TESTS, *D101_EXTRACTOR_TESTS]


# ---------------------------------------------------------------------------
# HOOK: post-layer-checkpoint-gate.sh, скоуп B (принудительный путь «пост файлом
# в пакет»). 🔴 РАУНД 3 (скептик по решению автора, дефект 1): хук строил команду линта
# из белого списка флагов шапки, `--factbase` в списке не было - AC5-гейт
# выдуманных фактов в этом пути не запускался НИКОГДА, честное объявление
# факт-базы отбивалось, а пост с выдуманной выручкой получал машинную расписку
# «verdict: PASS». Тесты живые: гоняют сам хук на временном пакете.
# ---------------------------------------------------------------------------

PKT_HOOK = os.path.expanduser("~/.claude/hooks/post-layer-checkpoint-gate.sh")

# Тело-донор берём из ЖИВОГО зелёного корпуса владельца (osn18-0608 - канал osn,
# reactions/razbor, проходит линт начисто), а не пишем синтетику: синтетический
# текст спотыкается о живой слой и плотность идей, и тест мерил бы не факт-базу.
# Нет приватного корпуса - тесты честно пропускаются, как соседние.
def _pkt_body_clean():
    p = owner_fixture("green-ivan", "osn18-0608.txt")
    return open(p, encoding="utf-8").read().strip() if p else None


_PKT_LINT_CMD = ("`python3 ~/.claude/skills/post/scripts/lint-post.py unit.md "
                 "--channel osn --form-goal reactions --form-class razbor%s`\n\n")


def _pkt_run(tmp, name, body, factbase_decl=""):
    """Пишет единицу в временный `_pakety-*` и гоняет по ней хук как PreToolUse
    Write. Возвращает (exit-код, stderr, расписка-словарь или None)."""
    pkt = os.path.join(tmp, "_pakety-test")
    os.makedirs(pkt, exist_ok=True)
    fp = os.path.join(pkt, name)
    hdr = _PKT_LINT_CMD % ((" " + factbase_decl) if factbase_decl else "")
    open(fp, "w", encoding="utf-8").write(hdr + "```\n" + body.strip() + "\n```\n")
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": fp,
                                         "content": open(fp, encoding="utf-8").read()},
                          "transcript_path": ""}, ensure_ascii=False)
    p = subprocess.run(["bash", PKT_HOOK], input=payload,
                       capture_output=True, text=True, timeout=90)
    rp = os.path.join(pkt, ".post-state-%s.json" % name.rsplit(".", 1)[0])
    receipt = None
    if os.path.exists(rp):
        try:
            receipt = json.load(open(rp, encoding="utf-8"))
        except Exception:
            receipt = None
    return p.returncode, (p.stderr or ""), receipt


def _pkt_factbase(tmp, name, text):
    """Факт-база как ВЫПИСКА из источника, а не копия поста.

    🔴 Раунд 4, К3: до фикса тут лежало ровно тело поста плюс добивка, и это
    ровно та атака, которую хук теперь блокирует («факт-база дублирует пост»).
    Правильная факт-база - первичный источник: числа, имена, ссылки, контекст
    расшифровки. Пост из неё пишется, а не наоборот. Строим механически из
    того же тела, чтобы покрытие AC5б/AC5в осталось полным, но НИ ОДНОГО
    предложения поста в базу не переносим."""
    pkt = os.path.join(tmp, "_pakety-test")
    os.makedirs(pkt, exist_ok=True)
    p = os.path.join(pkt, name)
    nums = sorted(set(re.findall(r"\d[\d\s.,]*\d|\d", text)))
    names = sorted(set(re.findall(r"[А-ЯЁ][а-яё]{2,}", text)
                       + re.findall(r"[A-Z][a-z]{2,}", text)))
    urls = sorted(set(re.findall(r"(?:https?://|t\.me/)\S+", text)))
    lines = ["# Выписка из источника (расшифровка эфира, кабинет, переписка)",
             "", "## Числа, снятые с источника"]
    lines += ["- значение: %s" % n.strip() for n in nums]
    lines += ["", "## Имена собственные и названия, встреченные в источнике"]
    lines += ["- упомянут: %s" % n for n in names]
    lines += ["", "## Адреса входа"]
    lines += ["- %s" % u for u in urls]
    lines += ["", "## Контекст сбора"]
    # добивка нужна для AC5а (объём базы >= объёма поста); текст добивки
    # намеренно НЕ из поста - иначе вернулся бы дубликат
    lines += ["- запись рабочей встречи, тайм-код зафиксирован, расшифровка "
              "сверена вручную с аудио"] * 60
    open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return p


def _pkt_guard(label):
    """Общая заглушка: нет хука - провал, нет приватного корпуса - пропуск."""
    if not os.path.exists(PKT_HOOK):
        record(label, False, "файл хука не найден")
        return None
    body = _pkt_body_clean()
    if body is None:
        skip(label, NO_OWNER_CORPUS)
        return None
    return body


_PKT_INVENTED = ("Выручка выросла на 257000 рублей за 317 дней", " ")


def _with_invented(body):
    """Врезает выдуманные числа В СЕРЕДИНУ длинного абзаца (репро скептика:
    зелёный пост владельца + выдуманная выручка). Точку в конце не ставим - её
    ловит другое правило, и тест мерил бы не тот класс."""
    lines = body.split("\n")
    for i, l in enumerate(lines):
        if len(l) > 120:
            lines[i] = l + " " + _PKT_INVENTED[0]
            break
    return "\n".join(lines)


def test_pkt_hook_factbase_accepted():
    """Раунд 3, дефект 1 (первая половина): честное объявление --factbase в шапке
    ПРИНИМАЕТСЯ и доезжает до линта - иначе AC5 не запускается вообще."""
    label = "pkt-hook: --factbase из шапки принят и доехал до линта"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-fb-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc, err, receipt = _pkt_run(tmp, "osn70.md", body, "--factbase _fb.txt")
    passed = (rc == 0 and receipt is not None
              and receipt["lint"]["verdict"] == "PASS"
              and "--factbase" in receipt["lint"]["argv"]
              and "флаг из шапки не принят" not in err)
    record(label, passed,
           (err[-300:] + " | argv=" + str(receipt and receipt["lint"]["argv"]))[:500])


def test_pkt_hook_invented_numbers_blocked():
    """Раунд 3, дефект 1 (репро скептика): пост с числами, которых нет в
    факт-базе, обязан БЛОКИРОВАТЬСЯ, а расписка получать FAIL. До правки хук
    выдавал PASS - AC5 не запускался."""
    label = "pkt-hook: выдуманные числа валят пост в принудительном пути"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-inv-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc, err, receipt = _pkt_run(tmp, "osn71.md", _with_invented(body), "--factbase _fb.txt")
    ok = (rc == 2 and "выдуманные числа" in err
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_no_factbase_is_fail():
    """Раунд 3, дефект 1 (вторая половина): числа в теле + факт-база не
    объявлена = FAIL расписки и блок, а не мягкое [INFO] с вердиктом PASS."""
    label = "pkt-hook: числа без факт-базы = FAIL расписки"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-nofb-")
    rc, err, receipt = _pkt_run(tmp, "osn72.md", _with_invented(body))
    ok = (rc == 2 and "post-packet-factbase" in err
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_no_numbers_needs_no_factbase():
    """Честная граница: пост БЕЗ единого числа в теле факт-базу не требует и
    проходит как раньше. Иначе гейт валил бы законный класс единиц."""
    label = "pkt-hook: пост без чисел факт-базу не требует"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-nonum-")
    nonum = "".join(ch for ch in body if not ch.isdigit())
    rc, err, receipt = _pkt_run(tmp, "osn73.md", nonum)
    ok = (rc == 0 and receipt is not None and receipt["lint"]["verdict"] == "PASS")
    record(label, ok, err[-400:])


def test_pkt_hook_factbase_self_certification_blocked():
    """Подмена источника: факт-базой объявлен САМ ПОСТ (тогда все его числа
    «есть в базе») или соседняя единица пакета. Оба пути обязаны блокироваться,
    как и объявление несуществующего файла."""
    label = "pkt-hook: факт-базой не может быть сам пост / соседняя единица / пустота"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-self-")
    rc1, err1, _ = _pkt_run(tmp, "osn74.md", body, "--factbase osn74.md")
    rc2, err2, _ = _pkt_run(tmp, "osn75.md", body, "--factbase osn74.md")
    rc3, err3, _ = _pkt_run(tmp, "osn76.md", body, "--factbase _netu.txt")
    ok = (rc1 == 2 and "САМ ПОСТ" in err1
          and rc2 == 2 and "другая единица пакета" in err2
          and rc3 == 2 and "нет на диске" in err3)
    record(label, ok, (err1[-200:] + " || " + err2[-200:] + " || " + err3[-200:]))


def test_pkt_hook_allow_flag_still_rejected():
    """Регресс раунда 1: расширение белого списка НЕ должно вернуть послабления.
    --allow-* из шапки по-прежнему отбивается."""
    label = "pkt-hook: --allow-* из шапки по-прежнему отвергается"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-allow-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc, err, receipt = _pkt_run(tmp, "osn77.md", body,
                                "--factbase _fb.txt --allow-metaphor причина")
    ok = ("allow-флаг из шапки не принят" in err
          and receipt is not None
          and "--allow-metaphor" not in receipt["lint"]["argv"])
    record(label, ok, err[-300:])


# ---------------------------------------------------------------------------
# РАУНД 4 (скептик по решению автора), критичные К1/К2/К3 и серьёзные С13/С14.
# Каждый тест держит ДОКАЗАННЫЙ обход: до фикса все они давали exit 0 и
# машинную расписку «verdict: PASS».
#   К1 - шапка снимала правила, которыми пост судят: `--min 1 --max 99999`
#        убирал пол длины (огрызок 364 знака = PASS), `--channel botreg` -
#        закон 32, `--form-goal reactions --form-class narrative` менял
#        требование двери на требование НУЛЯ ссылок;
#   К2 - `_has_numeric_claim` искал `\\d` и не видел чисел ПРОПИСЬЮ;
#   К3 - анти-самозаверение сверяло ПУТИ, а копия тела поста под служебным
#        именем путём не является - `cp` восстанавливал круг;
#   С14 - тело 360 КБ роняло python через ARG_MAX, гейт выходил нулём и
#        расписку не писал ВООБЩЕ (fail-open по размеру).
# ---------------------------------------------------------------------------

def test_pkt_hook_header_cannot_widen_length():
    """К1-а: `--min 1 --max 99999` из шапки обязан зажиматься движковыми
    границами (пол 500 = UNIT_LENGTH_HARD_FLOOR, потолок 3200 = максимум
    боевого корпуса). Репро скептика: огрызок 367 знаков с этой шапкой
    получал EXIT 0 и расписку PASS."""
    label = "pkt-hook К1: --min/--max из шапки зажаты движком (огрызок не проходит)"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-clamp-")
    # огрызок = первые абзацы зелёного поста автора: он чист по всем правилам,
    # кроме длины, поэтому тест меряет РОВНО пол длины
    stub = "\n\n".join(body.split("\n\n")[:3])
    rc, err, receipt = _pkt_run(tmp, "osn97.md", stub, "--min 1 --max 99999")
    argv = (receipt or {}).get("lint", {}).get("argv", [])
    ok = (rc == 2
          and "< min 500" in err
          and "зажат движковой границей" in err
          and "1" not in argv[argv.index("--min") + 1:argv.index("--min") + 2]
          and "99999" not in argv
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, (err[-400:] + " | argv=" + str(argv))[:600])


def _pkt_body_no_door(body):
    """То же тело автора, но БЕЗ двери: снята и ссылка, и датированное обещание.

    Нужно тестам закона 32: зелёный `osn18-0608` законно идёт без ссылки именно
    потому, что несёт обещание «Ссылка на вечерний эфир появится здесь в 18:00»
    (решение владельца 6.08). Пока обещание на месте, закон 32 молчит по делу, и
    тест мерил бы не ту ось."""
    keep = [l for l in body.splitlines()
            if "ссылк" not in l.lower() and "http" not in l.lower()]
    return "\n".join(keep).strip()


def test_pkt_hook_channel_must_match_prefix():
    """К1-б: `--channel` из шапки не может увести единицу из-под закона 32.

    🔴 Д18 (по решению автора), К3/К5: контракт изменён с ОТКАЗА на ЗАЖИМ. Канал вне
    семейства префикса движок просто не берёт и судит единицу каналом ИМЕНИ
    файла. Защищаемое свойство то же самое и проверяется прямо: объявленный
    `botreg` до линта не доезжает, и пост без двери на канале `osn` падает
    законом 32. Причина смены: отказ убивал 5 живых файлов владельца из принятого
    пакета Д18, которые объявляли botreg именно ради этой поблажки."""
    label = "pkt-hook К1: --channel из шапки не снимает закон 32 (зажим именем файла)"
    body = _pkt_guard(label)
    if body is None:
        return
    nodoor = _pkt_body_no_door(body)
    tmp = tempfile.mkdtemp(prefix="pkt-chan-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc1, err1, rec1 = _pkt_run(tmp, "osn98.md", nodoor,
                               "--factbase _fb.txt --channel botreg --form-goal sales "
                               "--form-class sales")
    rc2, err2, rec2 = _pkt_run(tmp, "b17-1.md", nodoor,
                               "--factbase _fb.txt --channel osn --form-goal sales "
                               "--form-class sales")
    # контроль: бот-семейству botreg законен и дверь ему не нужна - блока нет
    rc3, err3, _ = _pkt_run(tmp, "b17-2.md", nodoor,
                            "--factbase _fb.txt --channel botreg --form-goal sales "
                            "--form-class sales")
    argv1 = (rec1 or {}).get("lint", {}).get("argv", [])
    argv2 = (rec2 or {}).get("lint", {}).get("argv", [])
    ok = (rc1 == 2 and "закон 32" in err1 and "зажат движковой границей" in err1
          and "botreg" not in argv1
          and argv1[argv1.index("--channel") + 1:argv1.index("--channel") + 2] == ["osn"]
          and rc2 == 2 and "зажат движковой границей" in err2
          and argv2[argv2.index("--channel") + 1:argv2.index("--channel") + 2] == ["bot"]
          and "закон 32" not in err3)
    record(label, ok, (err1[-250:] + " || argv1=" + str(argv1) + " || " + err3[-150:])[:700])


def test_pkt_hook_form_goal_cannot_lift_law32():
    """К1-в / К3: ни ЦЕЛЬ, ни КЛАСС из шапки не снимают закон 32 канала.

    Две ноги.
      (а) ЛЕГАЛЬНАЯ пара `reactions/narrative` больше не отбивается шапкой, но
          право «ноль двери» ей на канале с дверью не положено - решает матрица
          КАНАЛ×КЛАСС в lint-post.py, и пост без двери падает законом 32;
      (б) ОФФ-КАНОННАЯ пара `gate/razbor` (раунд 5, К3: давала PASS единице без
          двери, потому что resolve_form_profile молча сводил её к профилю
          gate) отбивается на входе как несуществующая."""
    label = "pkt-hook К1/К3: цель и класс из шапки не снимают закон 32"
    body = _pkt_guard(label)
    if body is None:
        return
    nodoor = _pkt_body_no_door(body)
    tmp = tempfile.mkdtemp(prefix="pkt-goal-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc1, err1, rec1 = _pkt_run(tmp, "osn99.md", nodoor,
                               "--factbase _fb.txt --form-goal reactions --form-class narrative")
    rc2, err2, rec2 = _pkt_run(tmp, "osn99b.md", nodoor,
                               "--factbase _fb.txt --form-goal gate --form-class razbor")
    ok = (rc1 == 2 and "закон 32" in err1
          and rec1 is not None and rec1["lint"]["verdict"] == "FAIL"
          and rc2 == 2 and "post-packet-header" in err2 and "канону формы" in err2
          and rec2 is not None and rec2["lint"]["verdict"] == "FAIL")
    record(label, ok, (err1[-300:] + " || " + err2[-300:])[:700])


def test_pkt_hook_word_numerals_need_factbase():
    """К2: числа ПРОПИСЬЮ - такое же числовое утверждение, как цифры. Репро
    скептика: «выручка выросла на двести пятьдесят семь тысяч рублей за триста
    семнадцать дней» давало numeric_claims=false, факт-база не требовалась,
    AC5 не запускался, расписка PASS."""
    label = "pkt-hook К2: числа прописью требуют факт-базу (numeric_claims=true)"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-wordnum-")
    nodigits = "".join(ch for ch in body if not ch.isdigit())
    lines = nodigits.split("\n")
    for i, l in enumerate(lines):
        if len(l) > 120:
            lines[i] = l + (" выручка выросла на двести пятьдесят семь тысяч рублей "
                            "за триста семнадцать дней")
            break
    rc, err, receipt = _pkt_run(tmp, "osn72b.md", "\n".join(lines))
    ok = (rc == 2 and "post-packet-factbase" in err
          and receipt is not None
          and receipt["lint"]["factbase"]["numeric_claims"] is True
          and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_word_numerals_escalated_in_forced_path():
    """К2, вторая половина: факт-база ЕСТЬ и честная, но число прописью в ней
    не покрыто. В самом линте это осознанный WARN (решение владельца держит
    test_red_word_numerals), в принудительном пути уровень поднимает ХУК -
    файл на диске это выдача, WARN там никто не читает. Порог значения 11:
    единицы («три шага», «один экран») омонимичны речи и стоят в зелёном
    корпусе автора."""
    label = "pkt-hook К2: число прописью вне факт-базы блокирует принудительный путь"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-wnesc-")
    _pkt_factbase(tmp, "_fb.txt", body)     # выписка по ОРИГИНАЛЬНОМУ телу
    lines = body.split("\n")
    for i, l in enumerate(lines):
        if len(l) > 120:
            lines[i] = l + (" выручка выросла на двести пятьдесят семь тысяч рублей "
                            "за триста семнадцать дней")
            break
    rc, err, receipt = _pkt_run(tmp, "osn80.md", "\n".join(lines), "--factbase _fb.txt")
    ok = (rc == 2 and "числа ПРОПИСЬЮ" in err and "257000" in err
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_factbase_copy_of_post_blocked():
    """К3: факт-база = копия тела поста под служебным именем. Сверка ПУТЕЙ её
    пропускала (служебное имя не единица пакета и не сам пост), и все числа
    поста «находились» в базе - потому что база И ЕСТЬ пост. Репро скептика:
    одна команда cp давала EXIT 0 и расписку PASS."""
    label = "pkt-hook К3: факт-база, дублирующая пост по содержимому, блокируется"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="pkt-dup-")
    pkt = os.path.join(tmp, "_pakety-test")
    os.makedirs(pkt, exist_ok=True)
    # ровно то, что делал скептик: cp тела поста + добивка объёма
    open(os.path.join(pkt, "_faktbaza-osn60.md"), "w", encoding="utf-8").write(
        body + "\nисточник, расшифровка, контекст\n" * 40)
    rc, err, receipt = _pkt_run(tmp, "osn60.md", body, "--factbase _faktbaza-osn60.md")
    ok = (rc == 2 and "дублирует сам пост" in err
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_body_size_ceiling():
    """С14, первая половина: тело больше движкового потолка = явный блок.
    Репро скептика: тело 360 КБ уходило в python через окружение, упиралось в
    ARG_MAX («Argument list too long»), python не стартовал, гейт выходил
    НУЛЁМ и расписку не писал вообще."""
    label = "pkt-hook С14: тело сверх потолка = блок с распиской, а не тихий пропуск"
    if not os.path.exists(PKT_HOOK):
        record(label, False, "файл хука не найден")
        return
    tmp = tempfile.mkdtemp(prefix="pkt-big-")
    big = "Сегодня разобрал одну штуку про воронку и вход в канал. " * 12000
    rc, err, receipt = _pkt_run(tmp, "osn59.md", big)
    ok = (rc == 2 and "post-packet-size" in err
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, err[-400:])


def test_pkt_hook_fail_closed_on_internal_error():
    """С14, вторая половина: ЛЮБОЙ сбой прогона (исключение, таймаут, битый
    payload) = FAIL-CLOSED с распиской, а не exit 0. Триггер живой: content
    приходит не строкой, python падает на .strip() - до фикса это был bail()
    с exit 0 и без расписки."""
    label = "pkt-hook С14: сбой прогона = блок + расписка FAIL (fail-closed)"
    if not os.path.exists(PKT_HOOK):
        record(label, False, "файл хука не найден")
        return
    tmp = tempfile.mkdtemp(prefix="pkt-fc-")
    pkt = os.path.join(tmp, "_pakety-test")
    os.makedirs(pkt, exist_ok=True)
    fp = os.path.join(pkt, "osn88.md")
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": fp, "content": 12345},
                          "transcript_path": ""})
    p = subprocess.run(["bash", PKT_HOOK], input=payload,
                       capture_output=True, text=True, timeout=90)
    rp = os.path.join(pkt, ".post-state-osn88.json")
    receipt = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else None
    ok = (p.returncode == 2 and "post-packet-failclosed" in (p.stderr or "")
          and receipt is not None and receipt["lint"]["verdict"] == "FAIL")
    record(label, ok, (p.stderr or "")[-400:])


def test_pkt_hook_payload_not_via_environment():
    """С14, улика в исходнике: payload обязан уходить в python ФАЙЛОМ, а не
    через окружение - иначе класс ARG_MAX жив при любом потолке размера."""
    label = "pkt-hook С14: payload передаётся файлом, не через окружение"
    if not os.path.exists(PKT_HOOK):
        record(label, False, "файл хука не найден")
        return
    src = open(PKT_HOOK, encoding="utf-8").read()
    ok = ('RAW_FILE="$pkt_tmp"' in src
          and 'RAW="$input" LINT_PY' not in src
          and '[ "$pkt_rc" != "0" ]' in src)
    record(label, ok, "RAW через окружение или нет fail-closed ветки")


def test_pkt_hook_syntax():
    """bash -n на хуке скоупа B."""
    if not os.path.exists(PKT_HOOK):
        record("pkt-hook: bash -n", False, "файл хука не найден")
        return
    p = subprocess.run(["bash", "-n", PKT_HOOK], capture_output=True, text=True)
    record("pkt-hook: bash -n (синтаксис)", p.returncode == 0, p.stderr[-300:])


PKT_HOOK_TESTS = [test_pkt_hook_factbase_accepted,
                  test_pkt_hook_invented_numbers_blocked,
                  test_pkt_hook_no_factbase_is_fail,
                  test_pkt_hook_no_numbers_needs_no_factbase,
                  test_pkt_hook_factbase_self_certification_blocked,
                  test_pkt_hook_allow_flag_still_rejected,
                  # раунд 4: К1 / К2 / К3 / С14
                  test_pkt_hook_header_cannot_widen_length,
                  test_pkt_hook_channel_must_match_prefix,
                  test_pkt_hook_form_goal_cannot_lift_law32,
                  test_pkt_hook_word_numerals_need_factbase,
                  test_pkt_hook_word_numerals_escalated_in_forced_path,
                  test_pkt_hook_factbase_copy_of_post_blocked,
                  test_pkt_hook_body_size_ceiling,
                  test_pkt_hook_fail_closed_on_internal_error,
                  test_pkt_hook_payload_not_via_environment,
                  test_pkt_hook_syntax]


# ===========================================================================
# ГЕЙТ СЦЕНЫ (workflow/02b1-scene-mining.md) - код-гейт добычи сцены.
#
# ЗАЧЕМ. Фаза 02b1 требует под КАЖДУЮ единицу конкретный эпизод с уликой
# происхождения (`файл:строка` + дословная цитата). До гейта фаза держалась
# дисциплиной агента: карточку можно было сочинить, и проверить это было нечем.
# Логика живёт в lint-post.py (`--scene-state`), энфорс - в скоупе B хука
# post-layer-checkpoint-gate.sh (файл в пакете это выдача).
#
# ТЕСТЫ ЖИВЫЕ. Улика берётся из РЕАЛЬНОГО файла на диске автора; нет его -
# группа честно пропускается (как соседние группы без приватного корпуса).
# ===========================================================================

# Файл-улика. Приоритет: env -> реальный разбор из архива владельца (если есть на
# этой машине) -> СИНТЕТИЧЕСКИЙ файл, который тест кладёт сам. Синтетика нужна
# ради переносимости: на машине ученика приватного архива нет, а гейт проверять
# всё равно надо - группа обязана гоняться, а не уходить в SKIP. Никакой
# владелец-специфики в поведении гейта нет, путь ниже - только предпочтительный
# кандидат входных данных, ровно как OWNER_FIXTURES_CANDIDATES выше.
SCENE_EVIDENCE_CANDIDATES = (
    os.environ.get("POST_SCENE_EVIDENCE") or "",
    ".business/легаси/obsidian-vault-archived-2026-05-31/"
    "Аналитика/Разборы/mama_mozg/2026-05-29_конкурент_разбор.md",
)
SCENE_EVIDENCE_QUOTE = "выборка: 56 постов"
SCENE_SYNTH_LINE2 = ("- **выборка:** 56 постов (3 итерации ленты + пагинация), "
                     "медиана просмотров 5650")
NO_SCENE_EVIDENCE = "файл-улику не удалось ни найти, ни создать (нет прав на запись?)"

_SCENE_EV_CACHE = {}


def _scene_evidence():
    """(путь, номер строки) файла-улики, где строка ДЕЙСТВИТЕЛЬНО несёт цитату.
    Проверяем именно это, а не «файл существует»: иначе тест мерил бы не гейт,
    а отсутствие данных."""
    if _SCENE_EV_CACHE:
        return _SCENE_EV_CACHE.get("path"), _SCENE_EV_CACHE.get("line")
    for cand in SCENE_EVIDENCE_CANDIDATES:
        if not cand:
            continue
        p = os.path.expanduser(cand)
        try:
            lines = open(p, encoding="utf-8").read().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            if SCENE_EVIDENCE_QUOTE in ln:
                _SCENE_EV_CACHE.update({"path": p, "line": i})
                return p, i
    try:
        d = tempfile.mkdtemp(prefix="scene-src-")
        p = os.path.join(d, "razbor-arhiva.md")
        open(p, "w", encoding="utf-8").write(
            "# разбор архива\n%s\nхвост\nER: ~23%% сводно по выборке\n" % SCENE_SYNTH_LINE2)
        _SCENE_EV_CACHE.update({"path": p, "line": 2})
        return p, 2
    except Exception:
        _SCENE_EV_CACHE.update({"path": None, "line": None})
        return None, None


def _scene_evidence_ok():
    return _scene_evidence()[0] is not None


def _scene_card(**over):
    card = {
        "id": "s-analytics-mamamozg-56",
        "who": "я",
        "when": "по решению автора",
        "did": "прогнал разбор архива конкурента и снял метрики выборки",
        "number": "56 постов · 24500 подписчиков",
        "broke": "пагинация отдавала не всё, добирал тремя итерациями",
        "result": "файл разбора с гипотезами и антигипотезами на диске",
        # три поля от этой редакции (П5-П7). Карточка фикстуры - НОВОГО формата:
        # иначе группа мерила бы архивную калитку, а не сами проверки.
        "pain": {"quote": SCENE_EVIDENCE_QUOTE, "file": _scene_evidence()[0],
                 "line": _scene_evidence()[1]},
        "novice_retell": "Человек без единой строчки кода за вечер собрал себе "
                         "страницу и увидел первые заявки",
        "audience_level": "novice",
        "evidence": {"file": _scene_evidence()[0], "line": _scene_evidence()[1],
                     "quote": SCENE_EVIDENCE_QUOTE},
        "status": "свежая",
    }
    ev = over.pop("evidence", None)
    pn = over.pop("pain_patch", None)
    card.update(over)
    if ev:
        card["evidence"] = dict(card["evidence"], **ev)
    if pn:
        card["pain"] = dict(card["pain"], **pn)
    return card


def _scene_card_old(**over):
    """Карточка ДО по решению автора: те же семь полей, ни одного из трёх новых.
    Ровно так выглядят все 80 боевых карточек корпуса (замер)."""
    card = _scene_card(**over)
    for f in ("pain", "novice_retell", "audience_level"):
        card.pop(f, None)
    return card


def _scene_second_evidence():
    """Вторая, ДРУГАЯ улика из того же файла - нужна там, где две единицы пакета
    обязаны нести разные сцены. Берём первую подходящую строку (>= 2 слов,
    >= 10 знаков), кроме строки первой улики."""
    path, line = _scene_evidence()
    lines = open(path, encoding="utf-8").read().splitlines()
    for i, ln in enumerate(lines, 1):
        if i == line:
            continue
        t = ln.strip().lstrip("#-*> ").strip()
        q = t if len(t) <= 60 else t[:60].rsplit(" ", 1)[0]
        if len(q) >= 14 and len(re.findall(r"\w+", q)) >= 3 and q in ln:
            return {"file": path, "line": i, "quote": q}
    raise RuntimeError("во входном файле нет второй пригодной строки-улики")


def _scene_state(scene=None, **over):
    """State «нового формата»: несёт отметки конвейера, поэтому сцена с него
    ТРЕБУЕТСЯ (архивная калитка не открывается)."""
    st = {"post_file": "unit.md",
          "factbase_path": "/tmp/fb.md",
          "factbase_created_at": "2026-08-09T09:00:00",
          "scene_mined_at": "2026-08-09T10:00:00",
          "draft_at": "2026-08-09T12:00:00"}
    if scene is not None:
        st["scene"] = scene
    st.update(over)
    return st


def _scene_run(state, name="osn90", extra_states=None):
    """Пишет state (и соседей по пакету) во временный каталог и гоняет
    lint-post.py --scene-state. Возвращает (rc, вывод)."""
    tmp = tempfile.mkdtemp(prefix="scene-")
    for nm, st in (extra_states or {}).items():
        with open(os.path.join(tmp, ".post-state-%s.json" % nm), "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
    sp = os.path.join(tmp, ".post-state-%s.json" % name)
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    p = subprocess.run([sys.executable, LINT, "--scene-state", sp, "--scene-package", tmp],
                       capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _scene_guard(label):
    if not _scene_evidence_ok():
        skip(label, NO_SCENE_EVIDENCE)
        return False
    return True


def test_scene_valid_passes():
    """Контроль: реальная сцена с резолвящейся уликой проходит. Без этого теста
    остальные пять доказывали бы только то, что гейт умеет говорить FAIL."""
    label = "сцена/контроль: валидная карточка с реальной уликой = PASS"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card()))
    ok = rc == 0 and "[PASS] сцена" in out and "[FAIL]" not in out
    record(label, ok, out[-400:])


def test_scene_missing_file_fails():
    """П1: заявленный файл улики не существует = FAIL. Заявленная и не
    существующая улика - тот же класс, что выдуманный факт."""
    label = "сцена/П1: файла улики нет на диске = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(
        evidence={"file": "/net/takogo/fajla/net.md"})))
    ok = rc == 1 and "сцена/П1" in out and "нет на диске" in out
    record(label, ok, out[-400:])


def test_scene_forged_quote_fails():
    """🔴 СЕРДЦЕ АНТИ-ВЫДУМКИ (П2). Файл и строка настоящие, а цитата подделана
    («56 постов» -> «560 постов»). Сцену без реального происхождения так не
    подделать: строка источника цитату не содержит."""
    label = "сцена/П2: подделанная цитата не совпадает со строкой источника = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(
        evidence={"quote": "выборка: 560 постов"})))
    ok = rc == 1 and "сцена/П2" in out and "НЕ содержит цитату" in out
    record(label, ok, out[-500:])


def test_scene_wrong_line_fails():
    """П2, вторая половина: файл и цитата настоящие, а номер строки сдвинут.
    Аналог `sed -n '<line>p'` - на другой строке лежит другой текст."""
    label = "сцена/П2: сдвинутый номер строки = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(
        evidence={"line": _scene_evidence()[1] + 1})))
    ok = rc == 1 and "сцена/П2" in out
    record(label, ok, out[-500:])
    # и за пределом файла - тоже FAIL, а не молчание
    rc2, out2 = _scene_run(_scene_state(_scene_card(evidence={"line": 999999})))
    record("сцена/П2: строка за пределом файла = FAIL",
           rc2 == 1 and "сцена/П2" in out2, out2[-300:])


def test_scene_order_stamp_fails():
    """П3: scene_mined_at не раньше draft_at = сцена подобрана под уже
    написанный текст (тот же принцип порядка, что у factbase_created_at)."""
    label = "сцена/П3: scene_mined_at позже draft_at = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(),
                                      scene_mined_at="2026-08-09T13:00:00"))
    ok = rc == 1 and "сцена/П3" in out
    record(label, ok, out[-400:])
    # отметок нет вовсе - порядок недоказуем, тоже FAIL
    st = _scene_state(_scene_card())
    st.pop("scene_mined_at")
    rc2, out2 = _scene_run(st)
    record("сцена/П3: нет отметки scene_mined_at = FAIL",
           rc2 == 1 and "сцена/П3" in out2, out2[-300:])


def test_scene_package_uniqueness():
    """П4: одна сцена = одна единица пакета. Совпадение scene.id с соседней
    единицей блокирует; переименование id при ТОЙ ЖЕ улике - тоже (иначе
    проверка снимается одной правкой строки)."""
    label = "сцена/П4: тот же scene.id в соседней единице пакета = FAIL"
    if not _scene_guard(label):
        return
    nb = {"osn91": _scene_state(_scene_card())}
    rc, out = _scene_run(_scene_state(_scene_card()), extra_states=nb)
    record(label, rc == 1 and "сцена/П4" in out and "уже стоит в единице" in out, out[-400:])

    rc2, out2 = _scene_run(_scene_state(_scene_card(id="s-drugoe-imya")), extra_states=nb)
    record("сцена/П4: переименованный id при той же улике = FAIL",
           rc2 == 1 and "ТА ЖЕ улика" in out2, out2[-400:])


def test_scene_hero_once_but_author_many():
    """П4, решение по данным боевого корпуса. Пакет дня несёт 9-22 единицы, и
    по определению 02b1 поле who у автора почти всегда «я». Дословная
    уникальность who означала бы «одна единица на пакет» - пакет несобираем.
    Поэтому: НАЗВАННЫЙ герой уникален (закон «один герой = один раз за
    пакет»), автор в роли who - нет."""
    label = "сцена/П4: названный герой дважды = FAIL, автор («я») дважды = PASS"
    if not _scene_guard(label):
        return
    hero_a = _scene_card(id="s-hero-a", who="Наталья, куратор")
    hero_b = _scene_card(id="s-hero-b", who="Наталья, куратор",
                         evidence=_scene_second_evidence())
    rc, out = _scene_run(_scene_state(hero_b),
                         extra_states={"osn92": _scene_state(hero_a)})
    hero_blocked = rc == 1 and "один герой = один раз за пакет" in out

    ya_a = _scene_card(id="s-ya-a")
    ya_b = _scene_card(id="s-ya-b", evidence=_scene_second_evidence())
    rc2, out2 = _scene_run(_scene_state(ya_b),
                           extra_states={"osn93": _scene_state(ya_a)})
    author_ok = rc2 == 0 and "[PASS] сцена" in out2
    record(label, hero_blocked and author_ok,
           "герой rc=%s | автор rc=%s %s" % (rc, rc2, out2[-250:]))


def test_scene_archive_state_passes():
    """АРХИВ не ломается. Два вида state без ключа scene проходят с N/A:
    (а) чистая машинная расписка хука - именно так выглядят ВСЕ боевые
        .post-state-*.json пакетов (замер: 193 файла, ключа scene нет ни у
        одного);
    (б) полный state конвейера с draft_at РАНЬШЕ внедрения гейта;
    (в) 🔴 полный state конвейера БЕЗ draft_at вовсе - замер боевого корпуса
        (193 файла) нашёл 49 таких: слои L1/L5_review/final есть, draft_at
        начали писать позже. По одной отметке draft_at весь этот архив уехал
        бы в FAIL, поэтому «когда собран» берётся по цепочке до mtime state.
    А вот новый state (draft_at после эпохи) без сцены обязан валиться."""
    label = "сцена/архив: расписка старого формата и старый draft_at = N/A, не блок"
    receipt_only = {"post_file": "osn18.md",
                    "lint": {"exit_code": 0, "verdict": "PASS"},
                    "produced_by": "post-layer-checkpoint-gate.sh"}
    rc1, out1 = _scene_run(receipt_only)
    old_pipeline = _scene_state(None, draft_at="2026-08-05T10:00:00")
    rc2, out2 = _scene_run(old_pipeline)
    rc3, out3 = _scene_run(_scene_state(None))          # новый state без сцены

    # (в) слои есть, ни одной ISO-отметки нет, файл старый - как 49 боевых
    tmp = tempfile.mkdtemp(prefix="scene-arch-")
    sp = os.path.join(tmp, ".post-state-old.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump({"post_id": "2026-07-24", "L1": {"смысл": "..."},
                   "L5_review": {"linter": "PASS"}, "final": True},
                  f, ensure_ascii=False)
    old_ts = 1753000000        # 2025-07-20, заведомо раньше эпохи гейта
    os.utime(sp, (old_ts, old_ts))
    p4 = subprocess.run([sys.executable, LINT, "--scene-state", sp],
                        capture_output=True, text=True, timeout=60)
    rc4, out4 = p4.returncode, p4.stdout + p4.stderr

    ok = (rc1 == 0 and "[N/A]" in out1
          and rc2 == 0 and "[N/A]" in out2
          and rc3 == 1 and "сцена/П1" in out3
          and rc4 == 0 and "[N/A]" in out4 and "mtime" in out4)
    record(label, ok, "расписка rc=%s | старый draft_at rc=%s | новый без сцены rc=%s | "
                      "архив без отметок rc=%s %s" % (rc1, rc2, rc3, rc4, out4[-200:]))


def test_scene_empty_fields_and_short_quote():
    """П1/П2, края формата 02b1: пустое обязательное поле = карточки нет
    (обязательны все семь кроме broke); улика на файл БЕЗ номера строки не
    принимается; цитата в одно слово уликой не является - она совпадает с чем
    угодно, и через неё выдумка проходила бы насквозь."""
    label = "сцена/П1-П2: пустое поле, улика без строки, цитата-обрубок = FAIL"
    if not _scene_guard(label):
        return
    rc1, out1 = _scene_run(_scene_state(_scene_card(number="")))
    rc2, out2 = _scene_run(_scene_state(_scene_card(evidence={"line": "не число"})))
    rc3, out3 = _scene_run(_scene_state(_scene_card(evidence={"quote": "56"})))
    # broke - единственное необязательное поле, пустое пройти обязано
    rc4, out4 = _scene_run(_scene_state(_scene_card(broke="")))
    ok = (rc1 == 1 and "пустые обязательные поля" in out1
          and rc2 == 1 and "БЕЗ номера строки" in out2
          and rc3 == 1 and "короче порога" in out3
          and rc4 == 0 and "[PASS] сцена" in out4)
    record(label, ok, "поле rc=%s | строка rc=%s | цитата rc=%s | broke rc=%s"
           % (rc1, rc2, rc3, rc4))


def test_scene_quote_normalisation_not_too_loose():
    """П2, граница нормализации. Разметка, типографика, регистр и «ё/е» между
    файлом и карточкой различать не должны - иначе гейт валит честную улику.
    Но нормализация НЕ имеет права быть настолько широкой, чтобы подделка
    проходила: цитата с ДРУГИМ числом обязана падать (проверено выше в П2),
    а цитата с той же цифрой и иной разметкой - проходить."""
    label = "сцена/П2: разметка и регистр не мешают, число - решает"
    tmp = tempfile.mkdtemp(prefix="scene-norm-")
    src = os.path.join(tmp, "istochnik.md")
    open(src, "w", encoding="utf-8").write(
        "# шапка\n- **выборка:** 56 постов, «Мама Мозг» - разбор\nхвост\n")
    loose = _scene_card(evidence={"file": src, "line": 2,
                                  "quote": "Выборка: 56 постов, \"мама мозг\""})
    tight = _scene_card(id="s-2", evidence={"file": src, "line": 2,
                                            "quote": "выборка: 57 постов"})
    def go(card):
        sp = os.path.join(tmp, ".post-state-%s.json" % card["id"])
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(_scene_state(card), f, ensure_ascii=False)
        p = subprocess.run([sys.executable, LINT, "--scene-state", sp],
                           capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr
    rc1, out1 = go(loose)
    rc2, out2 = go(tight)
    record(label, rc1 == 0 and rc2 == 1,
           "разметка/регистр rc=%s | другое число rc=%s | %s" % (rc1, rc2, out1[-250:]))


def test_scene_pkt_hook_blocks_delivery():
    """ЭНФОРС. Гейт обязан стоять не только в линте, но и на ВЫДАЧЕ: единица,
    записываемая файлом в пакет с непрошедшей сценой, блокируется хуком
    (exit 2), а расписка получает scene.verdict = FAIL. Валидная сцена -
    exit 0 и scene.verdict = PASS."""
    label = "сцена/энфорс: хук пакета блокирует выдачу единицы без сцены"
    body = _pkt_guard(label)
    if body is None:
        return
    if not _scene_evidence_ok():
        skip(label, NO_SCENE_EVIDENCE)
        return

    def run_with_state(nm, st):
        tmp = tempfile.mkdtemp(prefix="scene-pkt-")
        pkt = os.path.join(tmp, "_pakety-test")
        os.makedirs(pkt, exist_ok=True)
        _pkt_factbase(tmp, "_fb.txt", body)
        if st is not None:
            with open(os.path.join(pkt, ".post-state-%s.json" % nm), "w",
                      encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False)
        return _pkt_run(tmp, nm + ".md", body, "--factbase _fb.txt")

    rc_ok, err_ok, rcpt_ok = run_with_state("osn88", _scene_state(_scene_card()))
    rc_no, err_no, rcpt_no = run_with_state("osn89", _scene_state(None))
    scene_ok = ((rcpt_ok or {}).get("lint", {}).get("scene") or {}).get("verdict")
    scene_no = ((rcpt_no or {}).get("lint", {}).get("scene") or {}).get("verdict")
    ok = (rc_ok == 0 and scene_ok == "PASS"
          and rc_no == 2 and "post-packet-scene" in err_no and scene_no == "FAIL")
    record(label, ok, "валидная rc=%s scene=%s | без сцены rc=%s scene=%s | %s"
           % (rc_ok, scene_ok, rc_no, scene_no, err_no[-250:]))


def test_scene_pkt_hook_archive_not_broken():
    """РЕГРЕСС АРХИВА на живом хуке: единица БЕЗ state рядом (ровно так выглядят
    все боевые пакеты - 193 расписки, ключа scene нет ни у одной) обязана
    проходить как раньше, с пометкой N/A в расписке. Гейт, ломающий архив,
    не внедряют."""
    label = "сцена/архив на хуке: единица без state проходит с N/A"
    body = _pkt_guard(label)
    if body is None:
        return
    tmp = tempfile.mkdtemp(prefix="scene-pkt-arch-")
    _pkt_factbase(tmp, "_fb.txt", body)
    rc, err, rcpt = _pkt_run(tmp, "osn79.md", body, "--factbase _fb.txt")
    sc = ((rcpt or {}).get("lint", {}).get("scene") or {}).get("verdict")
    record(label, rc == 0 and sc == "N/A" and (rcpt or {}).get("lint", {}).get("verdict") == "PASS",
           "rc=%s scene=%s %s" % (rc, sc, err[-250:]))


# ===========================================================================
# П5-П7 (три поля карточки от этой редакции): pain / novice_retell / audience_level
#
# ЗАЧЕМ ОТДЕЛЬНАЯ ГРУППА. П1-П4 выше доказывают, что сцена РЕАЛЬНА. Они молчат
# о том, понятна ли она читателю - а именно этот класс («эпизод настоящий, но
# читается только изнутри проекта») 02b1 называет вторым корнем и закрывает
# тремя новыми полями. Сутки поля стояли БЕЗ кода и держались глазами судьи.
#
# СЛОВАРЬ НЕ КОПИРУЕТСЯ В ТЕСТ. Термины берутся из того же живого
# 02b1-scene-mining.md, из которого их читает линтер: копия в тесте
# рассинхронится с каноном в первый же раунд правок и будет зеленеть на
# словаре, которого там уже нет (тот же закон, что у `_hook_donordev_ns`).
# ===========================================================================

SCENE_MINING_DOC_T = os.path.join(SKILL_ROOT, "workflow", "02b1-scene-mining.md")


def test_scene_pain_resolves():
    """П5-контроль: боль с резолвящейся уликой не мешает PASS, и гейт печатает
    именно то, что проверил. Без этого теста остальные доказывали бы только
    умение говорить FAIL."""
    label = "сцена/П5: боль с резолвящейся уликой = PASS, улика названа в выводе"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card()))
    ok = rc == 0 and "[PASS] сцена" in out and "боль резолвится" in out
    record(label, ok, out[-400:])


def test_scene_pain_forged_fails():
    """П5: боль, которой на заявленной строке НЕТ, = FAIL. Ровно тот же способ
    проверки, что у evidence (02b1 Г4: «проверка та же, что у Г2») - формулировка
    своими словами или абстракцией «страх технологий» гейту непроверяема."""
    label = "сцена/П5: подделанная цитата боли не совпадает со строкой = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(
        pain_patch={"quote": "страх технологий и нехватка времени у взрослых"})))
    ok = rc == 1 and "сцена/П5" in out and "НЕ содержит цитату боли" in out
    record(label, ok, out[-500:])
    rc2, out2 = _scene_run(_scene_state(_scene_card(
        pain_patch={"file": "/net/takoj/karty/bolej.md"})))
    record("сцена/П5: файла карты болей нет на диске = FAIL",
           rc2 == 1 and "сцена/П5" in out2 and "нет на диске" in out2, out2[-400:])
    rc3, out3 = _scene_run(_scene_state(_scene_card(pain_patch={"line": "нет"})))
    record("сцена/П5: боль без номера строки непроверяема = FAIL",
           rc3 == 1 and "сцена/П5" in out3 and "line не число" in out3, out3[-400:])


def test_scene_retell_empty_fails():
    """П6: пустой пересказ = FAIL. Пустое поле по 02b1 значит «карточки нет»."""
    label = "сцена/П6: пустой novice_retell = FAIL"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(novice_retell="")))
    ok = rc == 1 and "сцена/П5-П7" in out and "novice_retell" in out
    record(label, ok, out[-500:])


def test_scene_retell_kitchen_term_fails():
    """П6: термин внутренней кухни в пересказе = FAIL, и словарь берётся ЖИВЬЁМ
    из 02b1 (не копией в коде). Термины для проверки вытаскиваем из того же
    файла: перечень в каноне поменяется - тест поедет за ним, а не отстанет."""
    label = "сцена/П6: термин внутренней кухни в пересказе = FAIL (словарь из 02b1)"
    if not _scene_guard(label):
        return
    try:
        src = open(SCENE_MINING_DOC_T, encoding="utf-8").read()
    except OSError as e:
        record(label, False, "02b1-scene-mining.md не читается (%s) - словарь "
                             "раздаётся вместе со скиллом, его отсутствие = поломка "
                             "пакета, а не повод пропустить тест" % e)
        return
    anchor = "Термины-маркеры, при появлении которых перевод считается несостоявшимся:"
    if anchor not in src:
        record(label, False, "в 02b1 нет якоря перечня «%s» - словарь переписан, "
                             "тест обезоружен" % anchor)
        return
    seg = src.split(anchor, 1)[1].split("\n", 1)[0].strip().rstrip(".")
    live = [t.strip().strip("«»") for t in seg.split(",") if t.strip()]
    probes = [t for t in live if t and "тех-имя" not in t and "NN" not in t][:6]
    if len(probes) < 3:
        record(label, False, "из живого перечня 02b1 разобрано %d пригодных "
                             "терминов - мало для проверки" % len(probes))
        return
    bad = []
    for term in probes:
        rc, out = _scene_run(_scene_state(_scene_card(
            novice_retell="Человек увидел, что %s не сошлась, и всё переделал" % term)))
        if not (rc == 1 and "сцена/П6" in out and "внутренней кухни" in out):
            bad.append("«%s» -> rc=%s (термин из живого перечня 02b1 гейт НЕ ловит)"
                       % (term, rc))
    # контроль: чистый человеческий пересказ мимо словаря НЕ падает
    rc_ok, out_ok = _scene_run(_scene_state(_scene_card(
        novice_retell="Женщина 56 лет за вечер собрала себе страницу и получила "
                      "первую заявку на следующий день")))
    if rc_ok != 0:
        bad.append("контроль: чистый пересказ без терминов дал rc=%s - гейт режет "
                   "живой язык (регресс по ложным срабатываниям): %s"
                   % (rc_ok, out_ok[-300:]))
    record(label, not bad, "; ".join(bad)[:700])


def test_scene_retell_kitchen_no_false_positive():
    """П6-регресс: обычные русские слова, начинающиеся так же, как термины
    («декабрь», «декорации», «деканат», «копия», «голову»), терминами НЕ
    считаются. Гейт, режущий живой язык, - регресс, а не строгость."""
    label = "сцена/П6: бытовые слова похожие на термины не ловятся (нет ложняка)"
    if not _scene_guard(label):
        return
    honest = [
        "В декабре человек, который в программировании ноль, собрал сайт за вечер",
        "Он поднял голову и понял, что декорации тут не нужны",
        "Женщина из деканата купила курс и через месяц запустила свой канал",
        "Копия договора пришла на почту через полчаса после оплаты",
    ]
    bad = []
    for s in honest:
        rc, out = _scene_run(_scene_state(_scene_card(novice_retell=s)))
        if rc != 0:
            bad.append("«%s» -> rc=%s: %s" % (s[:40], rc, out[-200:]))
    record(label, not bad, "; ".join(bad)[:600])


def test_scene_retell_two_sentences_fails():
    """П6: пересказ длиннее одного предложения = FAIL. 02b1 просит РОВНО одно -
    то, что не влезает в предложение, обычно и есть непереведённая кухня.
    Контроль тут же: число с точкой («5.5») и сокращение вторым предложением
    не считаются."""
    label = "сцена/П6: два предложения в пересказе = FAIL, число с точкой = PASS"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(
        novice_retell="Женщина собрала сайт за вечер. Потом взяла двух клиентов")))
    ok1 = rc == 1 and "сцена/П6" in out and "одного предложения" in out
    rc2, out2 = _scene_run(_scene_state(_scene_card(
        novice_retell="Женщина за 1.5 часа собрала себе страницу и получила заявку")))
    ok2 = rc2 == 0
    record(label, ok1 and ok2, "два предложения rc=%s | число с точкой rc=%s %s"
           % (rc, rc2, (out[-200:] + " || " + out2[-200:])))


def test_scene_practitioner_on_mass_channel_fails():
    """П7: `practitioner` на массовом канале = FAIL. Карта болей 02b1 разрешает
    продвинутую боль РОВНО в одной строке - ММ; osn/bot/inf/star/email/zakr
    читают преимущественно новички без ниши. Канал берётся из имени единицы
    (в brief.channel его нет - замер 233 боевых state дал 0 совпадений)."""
    label = "сцена/П7: practitioner на массовом канале = FAIL (все массовые)"
    if not _scene_guard(label):
        return
    bad = []
    for name, chan in (("osn90", "osn"), ("b90", "bot"), ("inf90", "info"),
                       ("star90", "star"), ("e90", "email"), ("zakr90", "zakr")):
        rc, out = _scene_run(_scene_state(_scene_card(audience_level="practitioner")),
                             name=name)
        if not (rc == 1 and "сцена/П7" in out and chan in out):
            bad.append("%s (ждали FAIL с каналом %s) -> rc=%s: %s"
                       % (name, chan, rc, out[-200:]))
    # канал не опознан вовсе - practitioner тоже не проходит (fail-closed:
    # незнание канала это не разрешение)
    rc_u, out_u = _scene_run(_scene_state(_scene_card(audience_level="practitioner"),
                                          post_file="bezymyannyj.md"),
                             name="bezymyannyj")
    if not (rc_u == 1 and "сцена/П7" in out_u):
        bad.append("канал не опознан -> ждали FAIL, rc=%s: %s" % (rc_u, out_u[-200:]))
    record(label, not bad, "; ".join(bad)[:800])


def test_scene_practitioner_on_mm_passes():
    """П7: `practitioner` в ММ проходит. Без этой половины гейт был бы не
    «сверкой с картой болей», а запретом слова practitioner - и фаза потеряла бы
    единственный законный адрес продвинутой сцены."""
    label = "сцена/П7: practitioner на ММ = PASS, novice на массовом = PASS"
    if not _scene_guard(label):
        return
    rc, out = _scene_run(_scene_state(_scene_card(audience_level="practitioner")),
                         name="mm90")
    ok1 = rc == 0 and "[PASS] сцена" in out and "уровень practitioner" in out
    rc2, out2 = _scene_run(_scene_state(_scene_card()), name="osn90")
    ok2 = rc2 == 0 and "уровень novice" in out2
    rc3, out3 = _scene_run(_scene_state(_scene_card(audience_level="expert")))
    ok3 = rc3 == 1 and "сцена/П7" in out3 and "не из перечисления" in out3
    record(label, ok1 and ok2 and ok3,
           "mm rc=%s | osn rc=%s | мусорный уровень rc=%s %s"
           % (rc, rc2, rc3, (out[-200:] + " || " + out3[-200:])))


def test_scene_old_card_fields_na():
    """АРХИВ: карточка ДО по решению автора без трёх полей не блокируется, а карточка
    ПОСЛЕ - обязана их нести. Замер корпуса по решению автора: 233 файла
    `.post-state-*.json`, из них 80 с ключом `scene`, все датированы по решению автора и ни
    в одном нет ни одного из трёх полей. Гейт, ломающий архив, не внедряют - но
    и калитка «просто не пиши поля» закрыта датой."""
    label = "сцена/П5-П7 архив: карточка до этой редакции без трёх полей = N/A, не блок"
    if not _scene_guard(label):
        return
    old = _scene_state(_scene_card_old())
    old["scene_mined_at"] = "2026-08-08T10:00:00"
    old["draft_at"] = "2026-08-08T12:00:00"
    old["factbase_created_at"] = "2026-08-08T09:00:00"
    rc, out = _scene_run(old)
    ok1 = rc == 0 and "[PASS] сцена" in out and "П5-П7 N/A" in out
    # та же карточка, но собранная ПОСЛЕ эпохи - поля обязательны
    fresh = _scene_state(_scene_card_old())
    rc2, out2 = _scene_run(fresh)
    ok2 = rc2 == 1 and "сцена/П5-П7" in out2
    # частичное заполнение архивом не считается
    part = _scene_card_old()
    part["audience_level"] = "novice"
    partial = _scene_state(part)
    partial["scene_mined_at"] = "2026-08-08T10:00:00"
    partial["draft_at"] = "2026-08-08T12:00:00"
    partial["factbase_created_at"] = "2026-08-08T09:00:00"
    rc3, out3 = _scene_run(partial)
    ok3 = rc3 == 1 and "сцена/П5-П7" in out3
    record(label, ok1 and ok2 and ok3,
           "архив rc=%s | свежая без полей rc=%s | частичная rc=%s %s"
           % (rc, rc2, rc3, (out[-250:] + " || " + out2[-200:] + " || " + out3[-200:])))


def test_scene_kitchen_dictionary_is_single_source():
    """Словарь читается ИЗ 02b1 и НЕ продублирован в коде линтера: перечень
    правится в каноне - едет и гейт. Плюс контракт Д105 на этом же словаре:
    файл недоступен = HARD FAIL, а не тихая мягкая деградация (02b1 раздаётся
    вместе со скиллом и является частью самого механизма гейта)."""
    label = "сцена/П6: словарь кухни живёт в 02b1, копии в коде нет, файла нет = HARD FAIL"
    if not _scene_guard(label):
        return
    bad = []
    try:
        src = open(LINT, encoding="utf-8").read()
    except OSError as e:
        record(label, False, "линтер не читается: %s" % e)
        return
    # 1. в коде линтера нет ПЕРЕЧНЯ терминов (копии словаря).
    # Ищем ПЕРЕЧИСЛЕНИЕ, а не упоминание: копия словаря - это список, где
    # термины стоят кучей в одной строке кода, а пояснение оператору или пример
    # в докстринге несёт один-два. Замер на живом файле: максимум 3 термина на
    # строку (докстринг про словоизменение), поэтому порог 5 отделяет копию от
    # документации и не превращает тест в запрет писать по-русски в комментариях.
    # Сравнение по границам слова: без них «гейт» и «контур» ловились бы внутри
    # сотен служебных комментариев этого же файла и тест зеленел бы всегда.
    live_terms, live_meta, live_why = [], [], ""
    try:
        doc = open(SCENE_MINING_DOC_T, encoding="utf-8").read()
        seg_bl = doc.split("Маркеры провала прямо из слов владельца:", 1)
        seg_tr = doc.split("Термины-маркеры, при появлении которых перевод "
                           "считается несостоявшимся:", 1)
        if len(seg_bl) > 1:
            live_terms += re.findall(r"«([^«»]+)»", seg_bl[1].split("\n", 1)[0])
        if len(seg_tr) > 1:
            live_terms += [t.strip().strip("«»") for t
                           in seg_tr[1].split("\n", 1)[0].strip().rstrip(".").split(",")]
    except OSError as e:
        live_why = str(e)
    live_terms = sorted({t.strip().casefold() for t in live_terms if t.strip()})
    if len(live_terms) < 6:
        bad.append("живой перечень 02b1 не разобрался (%d терминов, %s) - тест на "
                   "дублирование словаря обезоружен" % (len(live_terms), live_why))
    else:
        rx_terms = {t: re.compile(r"(?<![0-9a-zа-я])" + re.escape(t) + r"(?![0-9a-zа-я])")
                    for t in live_terms}
        worst, worst_no, worst_hits = 0, 0, []
        for i, ln in enumerate(src.casefold().splitlines(), 1):
            hits = [t for t, r in rx_terms.items() if r.search(ln)]
            if len(hits) > worst:
                worst, worst_no, worst_hits = len(hits), i, hits
        if worst >= 5:
            bad.append("в lint-post.py строка %d несёт %d терминов живого перечня "
                       "разом (%s) - это копия словаря, а он обязан читаться из "
                       "02b1 одним источником (контракт 02b1)"
                       % (worst_no, worst, ", ".join(worst_hits[:8])))
    # 2. линтер реально разбирает живой файл: подсовываем ПУСТОЙ каталог скилла
    tmp = tempfile.mkdtemp(prefix="scene-dict-")
    os.makedirs(os.path.join(tmp, "workflow"), exist_ok=True)
    shim = os.path.join(tmp, "probe_dict.py")
    with open(shim, "w", encoding="utf-8") as f:
        f.write(
            "import importlib.util, sys, json\n"
            "spec = importlib.util.spec_from_file_location('lp', %r)\n"
            "m = importlib.util.module_from_spec(spec); sys.modules['lp'] = m\n"
            "spec.loader.exec_module(m)\n"
            "m.SCENE_MINING_DOC = %r\n"
            "m._scene_kitchen_cache.clear()\n"
            "t, meta, why = m._scene_kitchen_terms()\n"
            "print(json.dumps({'terms': t, 'why': why}, ensure_ascii=False))\n"
            % (LINT, os.path.join(tmp, "workflow", "02b1-scene-mining.md")))
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True, timeout=60)
    try:
        got = json.loads((p.stdout or "{}").strip().splitlines()[-1])
    except Exception:
        got = {}
    if got.get("terms") is not None:
        bad.append("без файла 02b1 словарь всё равно собрался (%s) - значит перечень "
                   "берётся не из канона" % str(got.get("terms"))[:120])
    # 3. и этот случай обязан ронять карточку, а не пропускать её молча
    probe2 = os.path.join(tmp, "probe_gate.py")
    with open(probe2, "w", encoding="utf-8") as f:
        f.write(
            "import importlib.util, sys, json\n"
            "spec = importlib.util.spec_from_file_location('lp', %r)\n"
            "m = importlib.util.module_from_spec(spec); sys.modules['lp'] = m\n"
            "spec.loader.exec_module(m)\n"
            "m.SCENE_MINING_DOC = %r\n"
            "m._scene_kitchen_cache.clear()\n"
            "r = m.check_scene_state(sys.argv[1], sys.argv[2])\n"
            "print(json.dumps({'status': r['status'], 'lines': r['lines']}, ensure_ascii=False))\n"
            % (LINT, os.path.join(tmp, "workflow", "02b1-scene-mining.md")))
    pkg = tempfile.mkdtemp(prefix="scene-dict-pkg-")
    sp = os.path.join(pkg, ".post-state-osn90.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(_scene_state(_scene_card()), f, ensure_ascii=False)
    p2 = subprocess.run([sys.executable, probe2, sp, pkg],
                        capture_output=True, text=True, timeout=60)
    try:
        got2 = json.loads((p2.stdout or "{}").strip().splitlines()[-1])
    except Exception:
        got2 = {}
    if got2.get("status") != "FAIL" or "недоступен" not in " ".join(got2.get("lines") or []):
        bad.append("словарь недоступен, а карточка получила «%s» - мягкая деградация: "
                   "чистота пересказа объявлена проверенной, хотя проверять было нечем "
                   "(вывод: %s)" % (got2.get("status"), str(got2.get("lines"))[:200]))
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(pkg, ignore_errors=True)
    record(label, not bad, "; ".join(bad)[:800])


def test_scene_pkt_hook_blocks_kitchen_term():
    """ЭНФОРС: П5-П7 стоят не только в ручном прогоне - хук пакета блокирует
    ВЫДАЧУ единицы, чей пересказ несёт термин кухни. Без этой проверки гейт
    жил бы только там, где его сознательно позвали."""
    label = "сцена/энфорс: хук пакета блокирует единицу с термином кухни в пересказе"
    body = _pkt_guard(label)
    if body is None:
        return
    if not _scene_evidence_ok():
        skip(label, NO_SCENE_EVIDENCE)
        return
    tmp = tempfile.mkdtemp(prefix="scene-pkt-kitchen-")
    _pkt_factbase(tmp, "_fb.txt", body)
    st = _scene_state(_scene_card(
        novice_retell="Расписка не сошлась с гейтом, перегнал линт и переделал"))
    pkt = os.path.join(tmp, "_pakety-test")     # тот же каталог, куда пишет _pkt_run
    os.makedirs(pkt, exist_ok=True)
    with open(os.path.join(pkt, ".post-state-osn78.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    rc, err, rcpt = _pkt_run(tmp, "osn78.md", body, "--factbase _fb.txt")
    scene_v = ((rcpt or {}).get("lint", {}).get("scene") or {}).get("verdict")
    ok = rc == 2 and "post-packet-scene" in err and scene_v == "FAIL"
    record(label, ok, "rc=%s scene=%s %s" % (rc, scene_v, err[-400:]))


SCENE_TESTS = [test_scene_valid_passes,
               test_scene_missing_file_fails,
               test_scene_forged_quote_fails,
               test_scene_wrong_line_fails,
               test_scene_order_stamp_fails,
               test_scene_package_uniqueness,
               test_scene_hero_once_but_author_many,
               test_scene_archive_state_passes,
               test_scene_empty_fields_and_short_quote,
               test_scene_quote_normalisation_not_too_loose,
               test_scene_pkt_hook_blocks_delivery,
               test_scene_pkt_hook_archive_not_broken,
               # --- П5-П7, три поля от этой редакции ---
               test_scene_pain_resolves,
               test_scene_pain_forged_fails,
               test_scene_retell_empty_fails,
               test_scene_retell_kitchen_term_fails,
               test_scene_retell_kitchen_no_false_positive,
               test_scene_retell_two_sentences_fails,
               test_scene_practitioner_on_mass_channel_fails,
               test_scene_practitioner_on_mm_passes,
               test_scene_old_card_fields_na,
               test_scene_kitchen_dictionary_is_single_source,
               test_scene_pkt_hook_blocks_kitchen_term]


# ===========================================================================
# РАУНД 3, дефекты Д4/Д5/Д6 (по решению автора) - обходы стража исключений и
# юникод-нормализация. Каждый тест держит ДОКАЗАННЫЙ обход, а не «проверку
# вообще»: до фикса все они давали PASS/exit 0.
#   Д4 - страж lint-owner-exceptions-guard.sh обходился через Bash и через
#        симлинк с чужим basename (alias.json -> файл исключений);
#   Д5 - _owner_scan матчил СЫРОЙ текст мимо нормализации («мaрафон» с
#        латинской a = [PASS] 0, снимались все три запрета владельца);
#   Д6 - вне маппинга были греческие двойники («двεрь»), soft hyphen U+00AD
#        и ё вместо е.
# Словарь владельца тут НЕ нужен: тесты подкладывают свой временный лексикон
# через POST_OWNER_LEXICON, поэтому группа гоняется и на машине ученика.
# ===========================================================================
OWNER_GUARD = os.path.expanduser("~/.claude/hooks/lint-owner-exceptions-guard.sh")
OWNER_EXC_NAME = "lint-owner-exceptions.json"


def _owner_guard_run(payload):
    p = subprocess.run(["bash", OWNER_GUARD], input=json.dumps(payload, ensure_ascii=False),
                       capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stderr or "")


def _owner_guard_missing(label):
    if os.path.exists(OWNER_GUARD):
        return False
    record(label, False, "файл стража не найден: " + OWNER_GUARD)
    return True


def test_owner_guard_bash_write_blocked():
    """Д4а: матчер стоял только на Write|Edit|MultiEdit - `echo ... >>` в файл
    исключений проходил с exit 0 и выписывал агенту --allow-* сам себе."""
    label = "owner-guard: Bash-запись в файл исключений = блок (Д4а)"
    if _owner_guard_missing(label):
        return
    tmp = tempfile.mkdtemp(prefix="owner-guard-")
    target = os.path.join(tmp, OWNER_EXC_NAME)
    open(target, "w", encoding="utf-8").write("{}\n")
    blocked = []
    for cmd in ('echo \'{"*.md":[{"flag":"--allow-metaphor"}]}\' >> %s' % target,
                'cat x | tee %s' % target,
                "sed -i '' 's/a/b/' %s" % target,
                'python3 -c "open(\\"%s\\",\\"w\\").write(1)"' % target):
        rc, err = _owner_guard_run({"tool_name": "Bash", "tool_input": {"command": cmd}})
        blocked.append((cmd[:40], rc, err.strip()[:60]))
    ok = all(rc == 2 for _, rc, _ in blocked)
    record(label, ok, "не заблокировано: " + str([b for b in blocked if b[1] != 2]))


def test_owner_guard_symlink_alias_blocked():
    """Д4б: классификация шла по basename САМОГО пути, поэтому симлинк с чужим
    именем (alias.json -> файл исключений) менял содержимое цели без блока."""
    label = "owner-guard: симлинк с чужим basename = блок (Д4б)"
    if _owner_guard_missing(label):
        return
    tmp = tempfile.mkdtemp(prefix="owner-guard-")
    target = os.path.join(tmp, OWNER_EXC_NAME)
    open(target, "w", encoding="utf-8").write("{}\n")
    alias = os.path.join(tmp, "alias.json")
    os.symlink(target, alias)
    rc_w, err_w = _owner_guard_run({"tool_name": "Write",
                                    "tool_input": {"file_path": alias,
                                                   "content": '{"HACKED":true}'}})
    rc_b, err_b = _owner_guard_run({"tool_name": "Bash",
                                    "tool_input": {"command": 'echo x > %s' % alias}})
    ok = rc_w == 2 and rc_b == 2
    record(label, ok, f"Write rc={rc_w} ({err_w.strip()[:60]}) · Bash rc={rc_b} ({err_b.strip()[:60]})")


def test_owner_guard_no_false_block():
    """Контроль Д4: страж не превращается в глушилку - чтение файла исключений
    и любая запись в посторонний файл обязаны проходить."""
    label = "owner-guard: чтение и посторонняя запись проходят (контроль)"
    if _owner_guard_missing(label):
        return
    tmp = tempfile.mkdtemp(prefix="owner-guard-")
    target = os.path.join(tmp, OWNER_EXC_NAME)
    open(target, "w", encoding="utf-8").write("{}\n")
    cases = [
        ({"tool_name": "Bash", "tool_input": {"command": "cat %s | head -5" % target}}, "чтение cat"),
        ({"tool_name": "Bash", "tool_input": {"command": "grep flag %s" % target}}, "чтение grep"),
        ({"tool_name": "Bash", "tool_input": {"command": "echo hi > %s/other.txt" % tmp}}, "запись в чужой файл"),
        ({"tool_name": "Write", "tool_input": {"file_path": os.path.join(tmp, "other.json"),
                                               "content": "{}"}}, "Write в чужой json"),
    ]
    bad = []
    for payload, name in cases:
        rc, err = _owner_guard_run(payload)
        if rc != 0:
            bad.append((name, rc, err.strip()[:60]))
    record(label, not bad, "ложный блок: " + str(bad))


def test_owner_guard_syntax():
    label = "owner-guard: bash -n (синтаксис)"
    if _owner_guard_missing(label):
        return
    p = subprocess.run(["bash", "-n", OWNER_GUARD], capture_output=True, text=True)
    record(label, p.returncode == 0, p.stderr[-300:])


# --- Д5/Д6: линт с ВРЕМЕННЫМ словарём владельца (не зависит от .business) ---
_TMP_LEXICON = {"banned_words": [
    {"id": "marathon", "label": "тестовое запрещённое слово",
     "patterns": ["марафон\\w*"], "fail_note": "тестовая запись раннера"},
]}
_UNICODE_BODY = ("**Заголовок дня 🔥**\n\n"
                 "Я собрал 42 человека и показал %s внутри 3 дней\n\n"
                 "дальше был разбор на живых примерах и разбор цифр\n")


def _run_lint_with_lexicon(text, extra_args=None):
    tmp = tempfile.mkdtemp(prefix="unicode-lint-")
    lex = os.path.join(tmp, "lex.json")
    with open(lex, "w", encoding="utf-8") as f:
        json.dump(_TMP_LEXICON, f, ensure_ascii=False)
    post = os.path.join(tmp, "post.txt")
    open(post, "w", encoding="utf-8").write(text)
    env = dict(os.environ)
    env["POST_OWNER_LEXICON"] = lex
    cmd = [sys.executable, LINT, post, "--channel", "osn",
           "--form-goal", "reactions", "--form-class", "razbor"] + (extra_args or [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    return p.stdout + p.stderr


# (имя варианта, слово-мишень с обфускацией). Все до фикса давали [PASS] 0.
_OWNER_OBFUSCATIONS = [
    ("латинская a (U+0061)", "мaрафон"),
    ("греческая ο (U+03BF)", "марафοн"),
    ("soft hyphen (U+00AD)", "мара­фон"),
    ("zero-width space (U+200B)", "мар​афон"),
    ("markdown-разрыв слова", "мар**афон**"),
    # --- С13, раунд 4 (по решению автора): таблица невидимок была ПЕРЕЧИСЛЕНИЕМ
    # символов, а не категорией Unicode; внутрисловные разделители не
    # снимались вовсе. Все четыре давали [PASS] 0.
    ("combining acute U+0301", "марафо́н"),
    ("variation selector U+FE0F", "мара️фон"),
    ("курсив-подчёркивания внутри слова", "мара_ф_он"),
    ("дефис внутри слова", "мара-фон"),
    ("без обфускации (базовая ловля)", "марафон"),
]


def test_owner_scan_unicode(variant):
    """Д5+Д6: запрет владельца обязан ловиться сквозь обфускацию слова."""
    name, word = variant
    out = _run_lint_with_lexicon(_UNICODE_BODY % word)
    caught = [l.strip() for l in out.splitlines()
              if l.strip().startswith("[FAIL]") and "тестовое запрещённое слово" in l]
    record(f"unicode owner-scan: «{name}» ловится запретом владельца",
           bool(caught), "нет [FAIL] по запрету:\n" + "\n".join(
               l for l in out.splitlines() if "запрещённое слово" in l)[:300])


_METAPHOR_OBFUSCATIONS = [
    ("греческая ε (U+03B5)", "двεрь"),
    ("ё вместо е в основе", "двёрь"),
    ("soft hyphen в корне", "дв­ерь"),
    # --- С13, раунд 4 (по решению автора): три новых невидимых обхода того же корня
    ("combining acute U+0301", "две́рь"),
    ("variation selector U+FE0F", "д️верь"),
    ("курсив-подчёркивания в корне", "д_в_ерь"),
]


def test_metaphor_unicode(variant):
    """Д6: корень-метафора обязан ловиться сквозь греческий двойник, ё и
    невидимый перенос. Греческая буква раньше ещё и РАЗРЫВАЛА слово надвое -
    регекс слова не считал её буквой."""
    name, word = variant
    out = _run_lint_with_lexicon(_UNICODE_BODY % ("%s в профессию" % word))
    caught = [l.strip() for l in out.splitlines()
              if l.strip().startswith("[FAIL]") and "метафоры (канон п.49)" in l]
    record(f"unicode метафора: «{name}» ловится корнем-метафорой",
           bool(caught), "нет [FAIL] метафоры в выводе")


def test_unicode_no_false_positive():
    """Контроль Д5/Д6 + С13: нормализация не должна выдумывать нарушений на
    честном тексте - ни на легальном слове события, ни на чистом английском
    термине (латиница без кириллицы в слове гомоглифами не трогается), ни на
    ЛЕГИТИМНЫХ дефисных словах (второй проход снимает разделители, и глухая
    склейка «мастер-класс» -> «мастеркласс» не имеет права родить нарушение)."""
    out = _run_lint_with_lexicon(
        _UNICODE_BODY % "по-настоящему рабочий мастер-класс по Claude Code и capcut")
    bad = [l.strip() for l in out.splitlines()
           if l.strip().startswith("[FAIL]") and ("запрещённое слово" in l
                                                  or "метафоры (канон п.49)" in l)]
    record("unicode: ложных срабатываний на честном тексте нет (контроль)",
           not bad, "\n".join(bad)[:300])


UNICODE_TESTS = ([test_owner_guard_bash_write_blocked,
                  test_owner_guard_symlink_alias_blocked,
                  test_owner_guard_no_false_block,
                  test_owner_guard_syntax]
                 + [(lambda v=v: test_owner_scan_unicode(v)) for v in _OWNER_OBFUSCATIONS]
                 + [(lambda v=v: test_metaphor_unicode(v)) for v in _METAPHOR_OBFUSCATIONS]
                 + [test_unicode_no_false_positive])


# ===========================================================================
# ГРАНИЦА ДВУХ ЗАПРЕТОВ ВЛАДЕЛЬЦА: категория-слово вместо имени + подводка-
# мостик перед оффером. Тесты держат ОБЕ стороны класса: брак обязан падать,
# а живые формы (множественное число как класс вещей, реакция-гейт в финале)
# обязаны проходить - иначе гейт съедает законную речь.
#
# 🔒 ИЗОЛЯЦИЯ: ни одного слова запрета здесь не хардкодится. Записи берутся из
# личного словаря владельца по тем же путям, что читает линтер, копируются во
# ВРЕМЕННЫЙ словарь (чтобы соседние запреты не мешали замеру), а ярлык для
# сверки читается из самой записи. Нет словаря или нет записи (машина ученика)
# -> тест самоустраняется через skip, а не краснеет.
# ===========================================================================
LEXICON_NAME = "lint-owner-lexicon.json"
_LEXICON_CANDIDATES = (
    os.environ.get("POST_OWNER_LEXICON") or "",
    ".business/processes/" + LEXICON_NAME,
    "~/.business/processes/" + LEXICON_NAME,
)
NO_OWNER_LEXICON = ("личный словарь запретов владельца не подключён "
                    "(POST_OWNER_LEXICON / ~/.business/processes/" + LEXICON_NAME + "); "
                    "проверка изолирована by design и на машине ученика спит")


def _load_owner_lexicon_entries():
    for p in _LEXICON_CANDIDATES:
        if not p:
            continue
        fp = os.path.expanduser(p)
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}
        return {e.get("id"): e for e in (data.get("banned_words") or [])
                if isinstance(e, dict)}
    return {}


OWNER_LEXICON_ENTRIES = _load_owner_lexicon_entries()

# Пара «id записи -> человекочитаемое имя гейта в отчёте теста». Сами слова
# запрета в этом файле не появляются - только id и ярлык из словаря.
_BOUNDARY_GATES = ("instrument_naming", "cta_bridge")

# (имя кейса, текст, ожидание по каждому гейту). Ожидание True = гейт обязан
# сработать, False = обязан промолчать. Тексты нейтральные: ни продукта, ни
# ссылок, ни имён - только сама языковая конструкция класса.
_BOUNDARY_CASES = [
    ("брак: подводка-мостик + категория-слово вместо имени",
     "Кому нужен сам инструмент, у меня лежит готовый разбор. Четыре дня в записи",
     {"instrument_naming": True, "cta_bridge": True}),
    ("живое: тот же смысл без подводки и без категории-слова",
     "У меня лежит готовый разбор, четыре дня в записи",
     {"instrument_naming": False, "cta_bridge": False}),
    ("живое: реакция-гейт в финале (клауза не открывает предложение)",
     "Накидайте 🔥 кому интересно, посмотрим сколько тут таких)",
     {"instrument_naming": False, "cta_bridge": False}),
    ("живое: множественное число как класс вещей",
     "активно наращиваем боеспособность через актуальные модели и инструменты",
     {"instrument_naming": False, "cta_bridge": False}),
    # Калибровка по зелёному корпусу владельца: родовое слово рядом с названной
    # вещью законно, запрещена только ПОДМЕНА имени. Широкий регекс на голое
    # слово валил четыре одобренных поста автора - этот кейс держит границу.
    ("живое: родовое слово при названной вещи, а не вместо имени",
     "а пока разберу инструмент, который закрывает у меня карусели целиком",
     {"instrument_naming": False, "cta_bridge": False}),
    # Правка по решению автора (скептик-приёмщик, живой прогон _owner_scan): узкий
    # префикс между границей предложения и «кому» пропускал эмодзи-маркеры
    # перед клаузой - три кейса ниже держат закрытую дыру и живую границу.
    ("брак: подводка-мостик с эмодзи-маркером перед клаузой",
     "🔥 Кому нужен разбор, забирайте",
     {"instrument_naming": False, "cta_bridge": True}),
    ("брак: подводка-мостик с маркером 👉 перед клаузой",
     "👉 Кому нужно, держите",
     {"instrument_naming": False, "cta_bridge": True}),
    ("живое: донорская форма с тире вместо запятой (названная цена)",
     "Кому интересно поучаствовать— накидайте 🔥 тут)",
     {"instrument_naming": False, "cta_bridge": False}),
]

_BOUNDARY_BODY = ("**Заголовок дня 🔥**\n\n"
                  "%s\n\n"
                  "дальше был разбор на живых примерах и разбор цифр\n")


def _run_lint_with_entries(text, entry_ids):
    """Прогон линта с временным словарём из указанных записей владельца."""
    tmp = tempfile.mkdtemp(prefix="owner-boundary-")
    lex = os.path.join(tmp, "lex.json")
    with open(lex, "w", encoding="utf-8") as f:
        json.dump({"banned_words": [OWNER_LEXICON_ENTRIES[i] for i in entry_ids]},
                  f, ensure_ascii=False)
    post = os.path.join(tmp, "post.txt")
    open(post, "w", encoding="utf-8").write(text)
    env = dict(os.environ)
    env["POST_OWNER_LEXICON"] = lex
    cmd = [sys.executable, LINT, post, "--channel", "osn",
           "--form-goal", "reactions", "--form-class", "razbor"]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    return p.stdout + p.stderr


def test_owner_boundary_case(case):
    name, body, expect = case
    label = f"граница запретов владельца: {name}"
    missing = [i for i in _BOUNDARY_GATES if i not in OWNER_LEXICON_ENTRIES]
    if missing:
        skip(label, NO_OWNER_LEXICON)
        return
    out = _run_lint_with_entries(_BOUNDARY_BODY % body, _BOUNDARY_GATES)
    bad = []
    for gate_id in _BOUNDARY_GATES:
        gate_label = OWNER_LEXICON_ENTRIES[gate_id].get("label") or gate_id
        fired = any(l.strip().startswith("[FAIL]") and gate_label in l
                    for l in out.splitlines())
        if fired != expect[gate_id]:
            bad.append(f"{gate_id}: ждали {'FAIL' if expect[gate_id] else 'PASS'}, "
                       f"получили {'FAIL' if fired else 'PASS'}")
    record(label, not bad, " · ".join(bad))


def test_owner_boundary_flags_release():
    """Обе записи обязаны сниматься своим флагом: жёсткий гейт без ручки =
    ловушка на честном тексте, где слово стоит законно."""
    label = "граница запретов владельца: флаги-обходы снимают оба гейта"
    missing = [i for i in _BOUNDARY_GATES if i not in OWNER_LEXICON_ENTRIES]
    if missing:
        skip(label, NO_OWNER_LEXICON)
        return
    tmp = tempfile.mkdtemp(prefix="owner-boundary-flag-")
    lex = os.path.join(tmp, "lex.json")
    with open(lex, "w", encoding="utf-8") as f:
        json.dump({"banned_words": [OWNER_LEXICON_ENTRIES[i] for i in _BOUNDARY_GATES]},
                  f, ensure_ascii=False)
    post = os.path.join(tmp, "post.txt")
    open(post, "w", encoding="utf-8").write(_BOUNDARY_BODY % _BOUNDARY_CASES[0][1])
    env = dict(os.environ)
    env["POST_OWNER_LEXICON"] = lex
    flags = [OWNER_LEXICON_ENTRIES[i].get("flag") for i in _BOUNDARY_GATES]
    bad = [i for i, f_ in zip(_BOUNDARY_GATES, flags) if not f_]
    if bad:
        record(label, False, "у записи нет поля flag: " + str(bad))
        return
    p = subprocess.run([sys.executable, LINT, post, "--channel", "osn",
                        "--form-goal", "reactions", "--form-class", "razbor"] + flags,
                       capture_output=True, text=True, env=env, timeout=120)
    out = p.stdout + p.stderr
    still = []
    for gate_id in _BOUNDARY_GATES:
        gate_label = OWNER_LEXICON_ENTRIES[gate_id].get("label") or gate_id
        if any(l.strip().startswith("[FAIL]") and gate_label in l for l in out.splitlines()):
            still.append(gate_id)
    record(label, not still, "флаг не снял гейт: " + str(still))


OWNER_BOUNDARY_TESTS = ([(lambda c=c: test_owner_boundary_case(c)) for c in _BOUNDARY_CASES]
                        + [test_owner_boundary_flags_release])


# ===========================================================================
# 4c: КОРПУС green-ivan (12) и red-classes (47)
# План: plans/2026-08-06-content-engine-v3.md, подэтап 4c.
# Замер «до» - BASELINE-0608.md в приватном корпусе владельца (зелёных PASS 6/12,
# красных 16/47). Сам корпус вне скилла, см. OWNER_FIXTURES выше.
# ===========================================================================

# --- МАТРИЦА КЛАСС → ФЛАГИ. Флаг здесь = не поблажка, а объявление КЛАССА
# ЕДИНИЦЫ (канал, цель формы) плюс, где нужно, ДАТИРОВАННАЯ архивная оговорка.
# Правило то же, что в шапке модуля: фикстура под порог не подгоняется, порог
# чинится по корпусу; флаг остаётся только там, где текст ФИЗИЧЕСКИ старше
# правила, и тогда рядом стоит улика с датами.
_ARCH_PSA = ["--allow-no-psa",
             "архивные финалы по решению автора (INF K1/K2/K3, источник финалов по решению автора в приватном корпусе) "
             "выданы без приписки-fallback; правило приписки введено позже"]
_ARCH_ORAL = ["--allow-no-oral",
              "архивный финал по решению автора старше закона живого слоя (по решению автора); живых "
              "знаков вне URL в источнике ноль - это факт архива, а не дефект письма"]
_ARCH_META = ["--allow-metaphor",
              "пост по решению автора старше правила метафор (канон п.49, сформулировано "
              "по решению автора): несёт «одной картиной» - оборот попал в запрет на день позже"]
# Раунд 1, находка 5: класс «ярлыки-рубрикаторы» поднят WARN -> HARD. Ярлык
# физически стоит в 4 из 12 постов автора (inf17 «На вход», star17 и
# ivan-final-0/2 «Честная граница»), и все 4 написаны ДО разбора эталона 6.08,
# где формульные блоки запрещены построчно. Порог не понижаем - ставим
# датированную оговорку, как _ARCH_PSA/_ARCH_META выше.
_ARCH_RUBR = ["--allow-rubricator",
              "пост старше разбора эталона по решению автора, где автор построчно запретил "
              "формульные блоки «на вход/на выходе» и «честная граница»"]

GREEN_IVAN_MANIFEST = [
    # файл, канал, цель формы, класс формы, архивные оговорки
    ("etalon-0608.txt",     "osn",   "reactions", "razbor", []),
    ("osn17-0508.txt",      "osn",   "reactions", "razbor", []),
    ("osn18-0608.txt",      "osn",   "reactions", "razbor", []),
    ("star17-0508.txt",     "star",  "reactions", "razbor", _ARCH_RUBR),
    ("inf17-0508.txt",      "info",  "reactions", "razbor", _ARCH_RUBR),
    ("inf18-0608.txt",      "info",  "reactions", "razbor", []),
    ("zakr18-den-0608.txt", "zakr",  "reactions", "razbor", []),
    ("b17-3-0508.txt",      "bot",   "reactions", "razbor", _ARCH_META),
    ("e17-0508.txt",        "email", "reactions", "razbor", []),
    ("ivan-final-0.txt",    "info",  "sales",     "sales",  _ARCH_PSA + _ARCH_RUBR),
    ("ivan-final-1.txt",    "info",  "sales",     "sales",  _ARCH_PSA + _ARCH_ORAL),
    ("ivan-final-2.txt",    "info",  "sales",     "sales",  _ARCH_PSA + _ARCH_RUBR),
]

# Д8: те же посты автора, но прогнанные КАК СОБЫТИЙНЫЕ. Отобраны по признакам
# класса из 01-router.md 0.49-E: время события в теле (оба несут «19:00»),
# каскад доходимости, единственное действие читателя - регистрация, 👉-дверь.
# Строки в GREEN_IVAN_MANIFEST выше НЕ трогаем: их прогон под razbor - это
# отдельный, уже зафиксированный замер, и подменять его нельзя.
# etalon-0608.txt (эталон 6.08) сюда НЕ входит намеренно: фикстура обрезана на
# скрине («[обрез скрина - хвост поста добрать у владельца]»), CTA-хвоста в ней
# физически нет, поэтому она падает на политике ссылок цели, а не на гейтах
# класса. Её 4.DENS считается и равна 0.87 - см. ADMISSION в lint-post.py.
EVENT_GREEN = [
    # файл, канал, цель формы, архивные оговорки (те же, что в манифесте выше)
    ("b17-3-0508.txt", "bot",  "sales", _ARCH_META),
    ("inf18-0608.txt", "info", "sales", []),
]


def test_green_ivan_corpus(entry):
    """Корпус «обязаны проходить»: посты, которые владелец считает эталонными.
    Критерий строгий - НОЛЬ [FAIL] во всём выводе, а не только в разделе v2.0."""
    fname, channel, goal, cls, arch = entry
    path = owner_fixture("green-ivan", fname)
    if path is None:
        skip(f"корпус автора {fname} (канал {channel})", NO_OWNER_CORPUS)
        return
    rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                   "--form-class", cls] + arch)
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith("[FAIL]")]
    fails = drop_element_floor_fails(fails, fname)
    record(f"green-ivan {fname} (канал {channel}, ноль [FAIL] во всём выводе)",
           not fails, "\n".join(fails)[:600])


# --- Ожидаемая ловля красного корпуса: класс -> подстрока СВОЕЙ строки [FAIL].
# Не «упало хоть как-нибудь», а «упало своим правилом».
RED_CLASS_EXPECT = {
    "B11-vydumannye-problemy-avtora.txt": "выдуманные числа",
    "B14-cifra-ne-iz-faktbazy.txt":       "выдуманные числа",
    "B15-plejsholder-v-finale.txt":       "плейсхолдеры в тексте",
    # раунд 1, находка 4 (ложный ПРОПУСК): заглушка переставала ловиться,
    # стоило вписать в неё дату - исключение «в скобке есть цифра» глотало
    # дословную жалобу автора «[живой факт]». Фикстура держит починенный край
    "B15b-plejsholder-s-datoy.txt":       "плейсхолдеры в тексте",
    # раунд 1, находка 5: класс поднят WARN -> HARD
    "KANON16-yarlyki-rubrikatory.txt":    "ярлыки-рубрикаторы",
    "B17-yakor-istoriya-dvazhdy.txt":     "дубль якоря/героя",
    "B18-skill-geroj-dvazhdy.txt":        "дубль якоря/героя",
    "B19-nizkaya-plotnost-idej.txt":      "плотность идей",
    "B20-fillery.txt":                    "филлеры",
    "B3-zaglushka-cennosti.txt":          "отложенное обещание",
    "B4-perechislenie-programmy.txt":     "перечисление программы",
    "B8-ruchnaya-domashka.txt":           "действие-читателю мимо регистрации",
    "C10-rich-razmetka.txt":              "rich-разметка запрещена",
    "C12-format-troyka.txt":              "точка в конце абзаца",
    "C3-odna-forma-zagolovka-paket.txt":  "дубли внутри волны",
    "C4-caps-shablon.txt":                "дубли внутри волны",
    "C5-odin-skelet-serii.txt":           "дубли внутри волны",
    "C8-nabor-lozungov.txt":              "причинных связок 0",
    "C9-ogryzok.txt":                     "4.1.6 огрызок",
    "D1-metafora.txt":                    "метафоры (канон п.49)",
    # скептик Р2 (по решению автора, находка 3): ZWSP внутри «дверь» + латинский
    # гомоглиф «у»→«y» внутри «путь» - оба слова визуально неотличимы от
    # чистых, но байты другие. Держит normalize_unicode_obfuscation в
    # lint-post.py (_strip_md_plain).
    "D1b-unicode-obfuscation.txt":        "метафоры (канон п.49)",
    "D2-metafora-podmena.txt":            "метафоры (канон п.49)",
    "D3-vydumannaya-svyazka.txt":         "несуществующие словосочетания",
    "D4-ocenochnye-yarlyki-voda.txt":     "вода суммарно",
    "D5-ritm-generatora.txt":             "медиана слов в предложении",
    "D6-privetstvie-samopredstavlenie.txt": "обрубки-нейрослоп",
    "E3-edinica-bez-dveri-i-utm.txt":     "UTM",
    "E6-vtoroe-dejstvie-chitatelyu.txt":  "действие-читателю мимо регистрации",
    "E8-cena-cifroy.txt":                 "цена цифрой",
    "F7-starye-kanaly-ogryzkom.txt":      "4.1.6 огрызок",
    "F8-email-dva-subject.txt":           "email: Subject-блоков",
}

# --- ЧЕСТНАЯ ГРАНИЦА 4c: классы, которые машина по-прежнему НЕ ловит.
# Список зафиксирован намеренно и проверяется тестом: если завтра кто-то
# закроет класс - тест покраснеет и заставит убрать его отсюда; если, наоборот,
# сломает работающий детектор - класс сюда не впишется молча.
# Причины, почему не закрыто в 4c (границы подэтапа - словарные детекторы):
#   B5/B9/B10/B13 - требуют чтения реального SKILL.md и сверки механики (П-класс);
#   B12/D8 - висящий референт без факт-базы неотличим от штатного имени;
#   C1 - «заголовок не выделен» неотделим машинно: green-ivan/inf18-0608.txt
#        (одобренный пост) несёт РОВНО такой же голый заголовок строкой;
#   C6/C7/C11/C13, E1/E2/E4/E5/E7/E9/E10/E11 - вне словарного слоя 4c
#        (реестры CTA, слоты каскада, вложения, списки фамилий).
RED_CLASS_KNOWN_GAPS = {
    "B10-mehanika-obshimi-slovami.txt", "B12-nepredstavlennye-imena.txt",
    "B13-otsylka-k-nevidimomu.txt", "B5-skill-ne-sushestvuet.txt",
    "B9-mehanika-vydumana.txt", "C1-zagolovok-ne-vydelen.txt",
    "C11-teh-imya-skilla.txt", "C13-kartinka-ne-vlozhena.txt",
    "C6-prokladka-posle-zagolovka.txt", "C7-sploshnye-bloki.txt",
    "D8-visyashij-referent.txt", "E1-goly-url.txt", "E10-uchenik-po-familii.txt",
    "E11-obeshanie-rezultata.txt", "E2-bez-strelki-pered-regoj.txt",
    "E4-ssylka-efira-ranshe-chasa.txt", "E5-vhod-zaregistrirovannym-nakanune.txt",
    "E7-dva-prizyva-v-sutki.txt", "E9-otsylka-na-post-bez-giperssylki.txt",
}

# Классы, которым нужен КОНТЕКСТ СЕРИИ (--package) или журнал якорей:
# одиночный файл физически не может показать «повтор внутри волны».
_RED_PACKAGE_SIBLING = {
    "C3-odna-forma-zagolovka-paket.txt": "C5-odin-skelet-serii.txt",
    "C5-odin-skelet-serii.txt": "D1-metafora.txt",
    "C4-caps-shablon.txt": None,     # сосед строится синтетически, см. ниже
}


def _red_extra_args(fname, rd):
    """Флаги, объявляющие КОНТЕКСТ красной фикстуры (серия дня / журнал якорей)."""
    extra = []
    if fname in _RED_PACKAGE_SIBLING:
        pkg = tempfile.mkdtemp(prefix="red-pkg-")
        sib = _RED_PACKAGE_SIBLING[fname]
        if sib:
            shutil.copy(os.path.join(rd, sib), pkg)
        else:
            # C4: второй пост той же серии с ТЕМ ЖЕ шаблоном «КАПС - расшифровка»,
            # но другим КАПС-словом (канон п.39 бьёт по шаблону, не по тексту)
            txt = open(os.path.join(rd, fname), encoding="utf-8").read()
            txt = txt.replace("ВОРОНКА ПОД СЛОВО", "ОТЧЁТ ПО КЛИКАМ", 1)
            open(os.path.join(pkg, "sibling.txt"), "w", encoding="utf-8").write(txt)
        extra += ["--package", pkg]
    if fname.startswith(("B17", "B18")):
        fd, log = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"date": datetime.date.today().isoformat(),
                                "channel": "osn", "slug": "vchera",
                                "anchor": "ночь 11 июня",
                                "hero": "Воронка под слово"}, ensure_ascii=False) + "\n")
        extra += ["--used-anchors-log", log, "--anchor", "ночь 11 июня",
                  "--hero", "Воронка под слово"]
    return extra


def test_red_class_corpus(fname):
    """Каждая red-фикстура обязана падать СВОИМ классом (или числиться в
    задокументированном списке дыр)."""
    rd = os.path.join(FIXTURES, "red-classes")
    path = os.path.join(rd, fname)
    args = ["--channel", "osn", "--form-goal", "reactions", "--form-class", "razbor"]
    args += _red_extra_args(fname, rd)
    fb = path.replace(".txt", ".factbase.txt")
    if os.path.exists(fb):
        args += ["--factbase", fb]
    rc, out = run_lint_file(path, args)
    expect = RED_CLASS_EXPECT.get(fname)
    if expect is None:
        ok = fname in RED_CLASS_KNOWN_GAPS
        record(f"red-classes {fname}: числится задокументированной дырой", ok,
               "класс не в RED_CLASS_EXPECT и не в RED_CLASS_KNOWN_GAPS")
        return
    own = [l.strip() for l in out.splitlines()
           if l.strip().startswith("[FAIL]") and expect in l]
    ok = rc == 1 and bool(own)
    record(f"red-classes {fname}: ловится своим классом «{expect}»", ok,
           f"rc={rc}; ожидали «{expect}»\n" + out[-500:] if not ok else "")


def test_red_gaps_are_still_gaps():
    """Карта покрытия полна: каждая фикстура либо ожидание, либо дыра.

    🔴 РАУНД 1 (скептик по решению автора, находка 8): раньше эта функция НАЗЫВАЛАСЬ
    проверкой дыр («ни одна из них не ловится тихо»), а телом считала только
    пересечение множеств - линт по gap-фикстурам не запускался ни разу.
    Проверка множеств осталась здесь, а заявленная проверка дыр вынесена в
    отдельный тест test_red_gaps_really_not_caught (ниже), где линт реально
    гоняется. Имя теста больше не обещает того, чего не делает."""
    overlap = RED_CLASS_KNOWN_GAPS & set(RED_CLASS_EXPECT)
    rd = os.path.join(FIXTURES, "red-classes")
    all_reds = {x for x in os.listdir(rd) if x.endswith(".txt") and ".factbase" not in x}
    uncovered = all_reds - set(RED_CLASS_EXPECT) - RED_CLASS_KNOWN_GAPS
    missing = (set(RED_CLASS_EXPECT) | RED_CLASS_KNOWN_GAPS) - all_reds
    ok = not overlap and not uncovered and not missing
    record("red-classes: карта покрытия полна (каждая фикстура либо ожидание, либо дыра)",
           ok, f"пересечение={overlap} без карты={uncovered} нет файла={missing}")


# Класс -> подстрока [FAIL], которой ЭТА дыра закрылась бы, если бы её кто-то
# закрыл. Проверяется живым прогоном линта: дыра обязана оставаться дырой, а
# если класс внезапно заловился - тест краснеет и заставляет перенести его в
# RED_CLASS_EXPECT (иначе система отчитывалась бы дырой по закрытому классу).
_GAP_WOULD_BE_CAUGHT_BY = {
    "C1-zagolovok-ne-vydelen.txt":            "заголовок",
    "C6-prokladka-posle-zagolovka.txt":       "прокладка",
    "C7-sploshnye-bloki.txt":                 "плита",
    "C11-teh-imya-skilla.txt":                "тех-имя",
    "C13-kartinka-ne-vlozhena.txt":           "картинка",
    "E1-goly-url.txt":                        "голый URL",
    "E2-bez-strelki-pered-regoj.txt":         "стрелк",
    "E4-ssylka-efira-ranshe-chasa.txt":       "раньше часа",
    "E5-vhod-zaregistrirovannym-nakanune.txt": "накануне",
    "E7-dva-prizyva-v-sutki.txt":             "два призыва",
    "E9-otsylka-na-post-bez-giperssylki.txt": "без гиперссылки",
    "E10-uchenik-po-familii.txt":             "фамили",
    "E11-obeshanie-rezultata.txt":            "обещание результата",
    "B5-skill-ne-sushestvuet.txt":            "скилл не существует",
    "B9-mehanika-vydumana.txt":               "механика выдумана",
    "B10-mehanika-obshimi-slovami.txt":       "механика общими словами",
    "B12-nepredstavlennye-imena.txt":         "непредставленное имя",
    "B13-otsylka-k-nevidimomu.txt":           "отсылка к невидимому",
    "D8-visyashij-referent.txt":              "висящий референт",
}


def test_red_gaps_really_not_caught(fname):
    """Дыра честная: линт РЕАЛЬНО прогоняется по gap-фикстуре и её класс в
    выводе не появляется. Раньше это заявлялось докстрингом, но не делалось."""
    rd = os.path.join(FIXTURES, "red-classes")
    path = os.path.join(rd, fname)
    args = ["--channel", "osn", "--form-goal", "reactions", "--form-class", "razbor"]
    args += _red_extra_args(fname, rd)
    fb = path.replace(".txt", ".factbase.txt")
    if os.path.exists(fb):
        args += ["--factbase", fb]
    rc, out = run_lint_file(path, args)
    needle = _GAP_WOULD_BE_CAUGHT_BY.get(fname)
    if needle is None:
        record(f"red-gaps {fname}: у дыры объявлена подстрока своего класса", False,
               "класс не описан в _GAP_WOULD_BE_CAUGHT_BY - дыру нельзя проверить прогоном")
        return
    # 🔴 по решению автора: строки обоих полов элементов из поиска исключены. Они несут
    # СПИСОК НЕДОСТАЮЩИХ элементов («стрелка», «прямая речь», ...), то есть
    # называют слова чужих классов по построению - и «стрелк» в подсказке
    # линтера не значит, что класс E2 поймали. Это другой гейт, у него своя
    # строка и свой тест.
    own = [l.strip() for l in out.splitlines()
           if l.strip().startswith("[FAIL]") and needle.lower() in l.lower()
           and not any(l.strip().startswith(m) for m in ELEMENT_FLOOR_FAIL_MARKS)]
    record(f"red-gaps {fname}: класс «{needle}» по-прежнему НЕ ловится (прогон линта)",
           not own, "класс внезапно ловится - перенеси фикстуру в RED_CLASS_EXPECT:\n"
                    + "\n".join(own)[:400])


# ===========================================================================
# РАУНД 5 (по решению автора), К1 + К2 - два класса, которые никто не охранял.
#   К1 - расписка гейта `.post-state-<слаг>.json` писалась обычным Write, и
#        код-гейт доставки снимался двумя ходами (пост вне пакета + расписка с
#        verdict=PASS и своим sha256). Плюс TOCTOU: sha ловил подмену тела и
#        снимался правкой соседней расписки. Закрыто стражем
#        post-receipt-write-guard.sh + подписью расписки + правилом свежести.
#   К2 - страж банка знал на 10 конструкций меньше соседнего hooks-selfguard,
#        и второго слоя (канарейки) у банка не было вовсе. Закрыто общим
#        лексиконом <hooks>/lib/write_detect.py и манифестом канарейки.
# Каждый тест держит ДОКАЗАННЫЙ обход: до фикса все они давали exit 0.
# ===========================================================================
RCPT_GUARD = os.path.expanduser("~/.claude/hooks/post-receipt-write-guard.sh")
BANK_GUARD = os.path.expanduser("~/.claude/hooks/senses-bank-write-guard.sh")
CANARY = os.path.expanduser("~/.claude/hooks/selfguard-canary.sh")
WRITE_DETECT = os.path.expanduser("~/.claude/hooks/lib/write_detect.py")


def _hook_rc(hook, tool, tool_input, cwd="/tmp", env=None):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input,
                          "cwd": cwd, "transcript_path": ""}, ensure_ascii=False)
    e = dict(os.environ)
    e.pop("IVAN_ALLOW_RECEIPT_EDIT", None)
    if env:
        e.update(env)
    p = subprocess.run(["bash", hook], input=payload, capture_output=True,
                       text=True, timeout=120, env=e)
    return p.returncode, (p.stderr or "")


def _r5_tmp_receipt(with_lint=True):
    tmp = tempfile.mkdtemp(prefix="r5-rcpt-")
    p = os.path.join(tmp, ".post-state-osn99.json")
    d = {"post_file": "osn99.md", "L1": "черновик"}
    if with_lint:
        d["lint"] = {"exit_code": 0, "verdict": "PASS", "text_sha256": "a" * 64,
                     "ran_at": "2026-08-07T10:00:00", "sig": "deadbeef"}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    return p, d


def test_r5_receipt_write_blocked():
    """К1: Write расписки с блоком lint там, где расписки не было."""
    label = "Р5-К1: Write фейковой расписки = блок"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    tmp = tempfile.mkdtemp(prefix="r5-rcpt-")
    p = os.path.join(tmp, ".post-state-osn99.json")
    content = json.dumps({"post_file": "osn99.md",
                          "lint": {"exit_code": 0, "verdict": "PASS",
                                   "text_sha256": "b" * 64}}, ensure_ascii=False)
    rc, err = _hook_rc(RCPT_GUARD, "Write", {"file_path": p, "content": content})
    record(label, rc == 2, err[-300:])


def test_r5_receipt_layers_allowed():
    """Контроль: слои конвейера в тот же файл писать МОЖНО - иначе страж
    остановил бы сам post-скилл."""
    label = "Р5-К1: слои конвейера в .post-state пишутся свободно (контроль)"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    p, d = _r5_tmp_receipt()
    d["L2_voice"] = "проверено"
    rc, err = _hook_rc(RCPT_GUARD, "Write",
                       {"file_path": p, "content": json.dumps(d, ensure_ascii=False)})
    record(label, rc == 0, err[-300:])


def test_r5_receipt_verdict_edit_blocked():
    """К1, TOCTOU: правка sha в расписке под новое тело."""
    label = "Р5-К1: Edit sha в расписке = блок (TOCTOU)"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    p, _ = _r5_tmp_receipt()
    rc, err = _hook_rc(RCPT_GUARD, "Edit",
                       {"file_path": p, "old_string": "a" * 64,
                        "new_string": "c" * 64})
    record(label, rc == 2, err[-300:])


def test_r5_receipt_bash_blocked():
    """К1: Bash-конструкции по расписке (редирект и pathlib)."""
    label = "Р5-К1: Bash-запись в расписку = блок"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    p, _ = _r5_tmp_receipt()
    rc1, e1 = _hook_rc(RCPT_GUARD, "Bash", {"command": "echo '{}' > " + p})
    rc2, e2 = _hook_rc(RCPT_GUARD, "Bash", {
        "command": """python3 -c "from pathlib import Path; Path('%s').write_text('{}')" """ % p})
    record(label, rc1 == 2 and rc2 == 2, (e1 + e2)[-300:])


def test_r5_receipt_bypass_declared():
    """К1: объявленный ремонт проходит - у стража есть легальный путь."""
    label = "Р5-К1: IVAN_ALLOW_RECEIPT_EDIT=1 пропускает (объявленный ремонт)"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    p, _ = _r5_tmp_receipt()
    rc, err = _hook_rc(RCPT_GUARD, "Bash",
                       {"command": "IVAN_ALLOW_RECEIPT_EDIT=1 rm -f " + p})
    record(label, rc == 0, err[-300:])


def test_r5_receipt_guard_syntax():
    label = "Р5-К1: bash -n стража расписки"
    if not os.path.exists(RCPT_GUARD):
        record(label, False, "страж не найден")
        return
    p = subprocess.run(["bash", "-n", RCPT_GUARD], capture_output=True, text=True)
    record(label, p.returncode == 0, p.stderr[-300:])


def test_r5_gate_signs_receipt():
    """К1: расписку подписывает САМ ГЕЙТ - без подписи доставка её не примет."""
    label = "Р5-К1: гейт кладёт в расписку подпись машины"
    src = open(PKT_HOOK, encoding="utf-8").read() if os.path.exists(PKT_HOOK) else ""
    ok = "_receipt_sig" in src and 'lint["sig"]' in src
    record(label, ok, "в скоупе B нет подписи расписки")


def test_r5_deliver_checks_signature_and_freshness():
    """К1: доставка сверяет подпись и требует, чтобы расписка не была новее тела.

    Скрипт доставки - личный канал владельца, санитайзер раздачи вычищает
    файлы с 'ivan' в имени (класс, не точечное правило). На машине ученика
    его нет и не будет - это не дефект, а SKIP, а не FAIL (см. skip() выше)."""
    label = "Р5-К1: доставка сверяет подпись расписки и её свежесть"
    dp = os.path.expanduser("~/.claude/skills/post/scripts/deliver-post.py")
    if not os.path.exists(dp):
        skip(label, "скрипт доставки не настроен на этой машине (канал доставки опционален)")
        return
    src = open(dp, encoding="utf-8").read()
    ok = ("receipt_sig" in src and "compare_digest" in src
          and "НОВЕЕ тела поста" in src)
    record(label, ok, "в доставке нет сверки подписи или правила свежести")


# ─── К2: общий лексикон + канарейка ────────────────────────────────────────
def _r5_radar_clone():
    tmp = tempfile.mkdtemp(prefix="r5-radar-")
    root = os.path.join(tmp, "radar")
    os.makedirs(os.path.join(root, "senses"))
    os.makedirs(os.path.join(root, "dumps", "2026-W33"))
    open(os.path.join(root, "senses_index.md"), "w").write("| id | смысл |\n")
    open(os.path.join(root, "senses", "senses.jsonl"), "w").write('{"id":"S1"}\n')
    open(os.path.join(root, "senses_usage.jsonl"), "w").write('{"used":"S1"}\n')
    open(os.path.join(root, "watchlist.json"), "w").write('{"channels":[]}\n')
    open(os.path.join(root, "dumps", "2026-W33", "real.jsonl"), "w").write(
        '{"url":"https://t.me/kanal/1"}\n')
    return root


def test_r5_bank_guard_ten_constructs():
    """К2: десять конструкций отчёта Р5 - до фикса ВСЕ проходили exit 0."""
    label = "Р5-К2: 10 конструкций записи в банк/дампы = блок"
    if not os.path.exists(BANK_GUARD):
        record(label, False, "страж банка не найден")
        return
    R = _r5_radar_clone()
    idx = os.path.join(R, "senses_index.md")
    usg = os.path.join(R, "senses_usage.jsonl")
    dmp = os.path.join(R, "dumps", "2026-W33")
    vectors = [
        """python3 -c "from pathlib import Path; Path('%s').write_text('x')" """ % idx,
        """python3 -c "from pathlib import Path; Path('%s/f.jsonl').write_text('x')" """ % dmp,
        """python3 -c "import shutil; shutil.copy('/etc/hosts','%s/f2.jsonl')" """ % dmp,
        """python3 -c "import os; os.rename('/tmp/x','%s/f3.jsonl')" """ % dmp,
        """echo '{}' 1> %s/f4.jsonl""" % dmp,
        """echo 'x' >| %s""" % idx,
        """dd if=/dev/zero of=%s/f6.jsonl bs=1 count=10""" % dmp,
        """patch %s < /tmp/p.diff""" % idx,
        """ed -s %s < /tmp/e.txt""" % idx,
        """python3 -c "R='%s'; open(R+'/senses_index.md','w').write('x')" """ % R,
        """python3 -c "u='%s'; from pathlib import Path; Path(u).write_text('')" """ % usg,
    ]
    passed = [c for c in vectors if _hook_rc(BANK_GUARD, "Bash", {"command": c})[0] != 2]
    record(label, not passed, "пролезло: " + " || ".join(p[:60] for p in passed))


def test_r5_bank_guard_controls():
    """Контроль: чтение и легальный контур радара не задеты."""
    label = "Р5-К2: чтение банка и прогон радара проходят (контроль)"
    if not os.path.exists(BANK_GUARD):
        record(label, False, "страж банка не найден")
        return
    R = _r5_radar_clone()
    idx = os.path.join(R, "senses_index.md")
    usg = os.path.join(R, "senses_usage.jsonl")
    dmp = os.path.join(R, "dumps", "2026-W33")
    controls = [
        "grep -c '|' %s" % idx,
        "echo '{\"used\":\"S2\"}' >> %s" % usg,
        "RADAR_WRITE=1 python3 radar_pull.py --week 2026-W33 > %s/new.jsonl" % dmp,
        "RADAR_WRITE=1 echo '| S1 | смысл | https://t.me/kanal/1 |' >> %s" % idx,
    ]
    blocked = [c for c in controls if _hook_rc(BANK_GUARD, "Bash", {"command": c})[0] != 0]
    record(label, not blocked, "ложный блок: " + " || ".join(b[:60] for b in blocked))


def test_r5_shared_lexicon_is_single_source():
    """К2: лексикон один на всех стражей класса - иначе списки разойдутся снова."""
    label = "Р5-К2: общий лексикон lib/write_detect.py подключён обоими стражами"
    if not os.path.exists(WRITE_DETECT):
        record(label, False, "модуля lib/write_detect.py нет")
        return
    users = [BANK_GUARD, os.path.expanduser("~/.claude/hooks/hooks-selfguard.sh"),
             RCPT_GUARD]
    missing = [os.path.basename(u) for u in users
               if not os.path.exists(u)
               or "from write_detect import" not in open(u, encoding="utf-8").read()]
    record(label, not missing, "не зовут модуль: " + ", ".join(missing))


def test_r5_canary_watches_bank_and_dumps():
    """К2(б): молчаливая подмена дампа СВОИМ СКРИПТОМ ловится канарейкой -
    единственный слой, который видит то, что лексический разбор не видит."""
    label = "Р5-К2: канарейка ловит молчаливую подмену дампа"
    if not os.path.exists(CANARY):
        record(label, False, "канарейки нет")
        return
    R = _r5_radar_clone()
    tmp = tempfile.mkdtemp(prefix="r5-canary-")
    hooks = os.path.join(tmp, "hooks")
    os.makedirs(os.path.join(hooks, "lib"))
    shutil.copy(CANARY, os.path.join(hooks, "selfguard-canary.sh"))
    open(os.path.join(hooks, "dummy.sh"), "w").write("#!/bin/bash\nexit 0\n")
    can = os.path.join(hooks, "selfguard-canary.sh")
    env = {"SENSES_RADAR_DIR": R}
    rc0, _ = _hook_rc(can, "Bash", {"command": "ls"}, env=env)          # база
    with open(os.path.join(R, "dumps", "2026-W33", "real.jsonl"), "a") as f:
        f.write('{"url":"https://t.me/kanal/9999"}\n')                  # тихо
    rc1, err1 = _hook_rc(can, "Bash", {"command": "python3 my_script.py"}, env=env)
    with open(os.path.join(R, "dumps", "2026-W33", "real.jsonl"), "a") as f:
        f.write('{"url":"https://t.me/kanal/8888"}\n')
    rc2, _ = _hook_rc(can, "Bash",
                      {"command": "RADAR_WRITE=1 python3 radar_pull.py"}, env=env)
    ok = rc0 == 0 and rc1 == 2 and rc2 == 0
    record(label, ok, "база=%d тихая подмена=%d объявленный радар=%d | %s"
           % (rc0, rc1, rc2, err1[:200]))


def test_r5_canary_is_fast():
    """К2(б): дампов много, поэтому в манифест идёт агрегат каталога, а не хеш
    содержимого. Проверяем цену: канарейка обязана оставаться дешёвой."""
    import time
    label = "Р5-К2: канарейка укладывается в 200 мс"
    if not os.path.exists(CANARY):
        record(label, False, "канарейки нет")
        return
    R = _r5_radar_clone()
    tmp = tempfile.mkdtemp(prefix="r5-fast-")
    hooks = os.path.join(tmp, "hooks")
    os.makedirs(hooks)
    shutil.copy(CANARY, os.path.join(hooks, "selfguard-canary.sh"))
    can = os.path.join(hooks, "selfguard-canary.sh")
    env = {"SENSES_RADAR_DIR": R}
    _hook_rc(can, "Bash", {"command": "ls"}, env=env)
    worst = 0.0
    for _ in range(3):
        t0 = time.time()
        _hook_rc(can, "Bash", {"command": "ls"}, env=env)
        worst = max(worst, (time.time() - t0) * 1000)
    record(label, worst < 200, "худший прогон %.0f мс" % worst)


def test_r5_canary_syntax():
    label = "Р5-К2: bash -n канарейки и стража банка"
    ok = True
    detail = ""
    for h in (CANARY, BANK_GUARD):
        if not os.path.exists(h):
            ok = False
            detail += os.path.basename(h) + " отсутствует; "
            continue
        p = subprocess.run(["bash", "-n", h], capture_output=True, text=True)
        if p.returncode != 0:
            ok = False
            detail += p.stderr[-150:]
    record(label, ok, detail)


# ===========================================================================
# АНТИ-КОРПУС МЁРТВЫХ КОНСТРУКЦИЙ (по решению автора). Классы К1-К11 lint-post.py.
# ===========================================================================
# Владелец по решению автора: «Ты полностью неживой, мёртвый язык даёшь... Тебе нужно прямо
# языковую модель создать полноценную, которая будет в нашем движке стоять».
# Три части закона:
#   1) каждый класс ловится СВОЕЙ строкой (11 красных фикстур ниже);
#   2) шесть примеров мёртвого языка, названных владельцем ДОСЛОВНО, ловятся
#      (DEAD_OWNER_EXAMPLES) - это приёмка, а не выдуманный кейс;
#   3) зелёный корпус автора остаётся чистым - держит GREEN_IVAN_MANIFEST выше,
#      никаких послаблений под новый блок туда не добавлено.
# Живая половина закона (заготовки, откуда конструкции берутся) лежит в
# .business/voice-corpus/_konstrukcii-zhivogo-yazyka.md и машиной не проверяется.

DEAD_CLASS_FIXTURES = {
    "DEAD-K1-simmetriya-ne-potomu.txt":        "К1",
    "DEAD-K2-obobshennyj-subekt.txt":          "К2",
    "DEAD-K3-psevdo-uteshenie.txt":            "К3",
    "DEAD-K4-vyglyadit-odinakovo.txt":         "К4",
    "DEAD-K5-simmetrichnyj-povtor-golovy.txt": "К5",
    "DEAD-K6-aforizm-kaskad.txt":              "К6",
    "DEAD-K7-eto-ne-x-eto-y.txt":              "К7",
    "DEAD-K8-zachin-datoj.txt":                "К8",
    "DEAD-K9-zagolovok-dejktik.txt":           "К9",
    "DEAD-K10-abstraktnoe-podlezhashee.txt":   "К10",
    "DEAD-K11-psevdotochnost-rovno.txt":       "К11",
}

# Дословные примеры владельца (по решению автора) + класс, которым каждый обязан пасть.
DEAD_OWNER_EXAMPLES = [
    ("владелец-1 «Тишина ... выглядит одинаково»",
     "Человек не знает, кончились места или про него забыли\n\n"
     "Тишина с той стороны выглядит одинаково в обоих случаях. "
     "Человек не знает, кончились места или про него забыли",
     ("К4", "К10")),
    ("владелец-2 «не потому X, а потому Y»",
     "Дальше про то, как часто я буду сюда писать\n\n"
     "Пять дней подряд чаще обычного, по несколько сообщений в день. "
     "Не потому, что мне нечем заняться, а потому, что за пять дней человеку "
     "надо успеть решить, а решают люди редко с первого касания",
     ("К1",)),
    ("владелец-3 «никуда он не денется»",
     "Про ритм честно\n\n"
     "Кому такой ритм не подходит - после пятницы канал вернётся в обычный "
     "режим, никуда он не денется",
     ("К3",)),
    ("владелец-4 «Машина посчитала честно...»",
     "Про счётчик\n\n"
     "Машина посчитала честно. Она посчитала ровно то, что я ей назвал. Назвал я не то",
     ("К6",)),
    ("владелец-5 серийный зачин датой",
     "Откуда взялось обещание\n\n"
     "Шестого августа я разбирал, кому из написавших нам людей никто не ответил. Нашёл троих",
     ("К8",)),
    ("владелец-6 заголовок «Вчера в полдень было три блока подряд»",
     "Вчера в полдень было три блока подряд и ни одного слайда\n\n"
     "Сегодня в 12 тот же эфир идёт повтором целиком",
     ("К9",)),
]


def test_dead_class_fixture(fname):
    """Красная фикстура обязана падать СВОИМ классом мёртвых конструкций."""
    rd = os.path.join(FIXTURES, "red-dead")
    path = os.path.join(rd, fname)
    cls = DEAD_CLASS_FIXTURES[fname]
    rc, out = run_lint_file(path, ["--channel", "osn", "--form-goal", "reactions",
                                   "--form-class", "razbor"])
    head = [l for l in out.splitlines()
            if l.strip().startswith("[FAIL] мёртвые конструкции")]
    own = [l for l in out.splitlines() if l.strip().startswith(cls + " ")]
    ok = rc == 1 and bool(head) and bool(own)
    record(f"мёртвые конструкции {cls}: фикстура {fname} ловится своим классом", ok,
           f"rc={rc}; шапка={bool(head)}; строка класса={bool(own)}\n" + out[-500:] if not ok else "")


def test_dead_owner_example(entry):
    """Пример владельца обязан пасть - и именно ожидаемым классом."""
    name, text, classes = entry
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as tf:
        tf.write(text)
        p = tf.name
    try:
        rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "reactions",
                                    "--form-class", "razbor"])
        got = {l.strip().split()[0] for l in out.splitlines()
               if l.startswith("        К")}
        missing = [c for c in classes if c not in got]
        head = [l for l in out.splitlines()
                if l.strip().startswith("[FAIL] мёртвые конструкции")]
        ok = rc == 1 and bool(head) and not missing
        record(f"пример владельца ловится: {name} (классы {'/'.join(classes)})", ok,
               f"rc={rc}; не поймано {missing}; поймано {sorted(got)}")
    finally:
        os.unlink(p)


def test_dead_green_ivan_untouched():
    """🔴 КАЛИБРОВКА. 12 постов зелёного корпуса автора обязаны идти БЕЗ единой
    строки [FAIL] мёртвых конструкций - без флагов и без исключений по имени.
    Правило, валящее зелёный, сужается; фикстура под порог не подгоняется."""
    bad = []
    checked = 0
    for entry in GREEN_IVAN_MANIFEST:
        fname, channel, goal, cls, arch = entry
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", cls] + arch)
        for l in out.splitlines():
            if l.strip().startswith("[FAIL] мёртвые конструкции") or \
               l.strip().startswith("[FAIL] К8 пакет"):
                bad.append(f"{fname}: {l.strip()[:160]}")
    if checked == 0:
        skip("мёртвые конструкции: зелёный корпус автора 12/12 чист", NO_OWNER_CORPUS)
        return
    record(f"мёртвые конструкции: зелёный корпус автора {checked}/{checked} чист "
           f"(ноль [FAIL] по К1-К11)", not bad, "\n".join(bad)[:600])


def test_dead_donor_green_untouched():
    """Донор-фикстуры green/ - ЧУЖИЕ тексты. Закон о конструкциях это закон
    автора про СВОИ посты, поэтому донор проверяется мягко: допускается до 1
    донор-поста с HARD (замер по всему корпусу 608: 24 поста, 3.9%)."""
    rd = os.path.join(FIXTURES, "green")
    if not os.path.isdir(rd):
        skip("мёртвые конструкции: донор-корпус green/ в пределах замера", "нет каталога green/")
        return
    hits = []
    files = sorted(x for x in os.listdir(rd) if x.endswith(".txt"))
    for fname in files:
        rc, out = run_lint_file(os.path.join(rd, fname),
                                ["--channel", "osn", "--form-goal", "reactions",
                                 "--form-class", "razbor"])
        if any(l.strip().startswith("[FAIL] мёртвые конструкции") for l in out.splitlines()):
            hits.append(fname)
    ok = len(hits) <= 1
    record(f"мёртвые конструкции: донор-корпус green/ {len(hits)}/{len(files)} с HARD "
           f"(порог замера <=1)", ok, "сработало на: " + ", ".join(hits))


def test_dead_package_date_opener_gate():
    """К8 на уровне пакета: доля постов с зачином датой выше 15% валит пакет.
    Порог откалиброван: доноры 0.5% (2/608), зелёный корпус автора 8.3% (1/12)."""
    td = tempfile.mkdtemp(prefix="dead-k8-pkg-")
    body = ("🧩 **Заголовок про счётчик лидов**\n\n"
            "{opener}\n\n"
            "Одно кодовое слово даёт мне 110 рублей, за ту ночь слов пришло 60, "
            "так что вышло 6.600 рублей за время, пока я спал. Считал в кровати\n\n"
            "Скилл, который это держит, называется «Воронка под слово». Ему идёт "
            "слово и ссылка на гайд, дальше он сам собирает выдачу и отчёт по кликам\n\n"
            "Трафик он не приведёт, слово всё равно надо произнести голосом в рилзе))\n")
    dated = "Шестого августа я открыл заметки в два часа ночи, лид падал каждую минуту"
    plain = "Ночью я открыл заметки в два часа, потому что лид падал каждую минуту"
    try:
        for i in range(10):
            with open(os.path.join(td, f"p{i}.md"), "w", encoding="utf-8") as f:
                f.write("```\n" + body.format(opener=dated if i < 4 else plain) + "```\n")
        probe = os.path.join(td, "p9.md")
        rc, out = run_lint_file(probe, ["--channel", "osn", "--form-goal", "reactions",
                                        "--form-class", "razbor", "--package", td])
        fail_line = [l for l in out.splitlines() if l.strip().startswith("[FAIL] К8 пакет")]
        # контроль: тот же пакет, но датой открыт только один пост из десяти
        for i in range(1, 4):
            with open(os.path.join(td, f"p{i}.md"), "w", encoding="utf-8") as f:
                f.write("```\n" + body.format(opener=plain) + "```\n")
        rc2, out2 = run_lint_file(probe, ["--channel", "osn", "--form-goal", "reactions",
                                          "--form-class", "razbor", "--package", td])
        pass_line = [l for l in out2.splitlines() if l.strip().startswith("[PASS] К8 пакет")]
        ok = bool(fail_line) and bool(pass_line)
        record("К8 пакет: 40% зачинов датой = FAIL, 10% = PASS (порог 15%)", ok,
               f"fail_line={fail_line[:1]}; pass_line={pass_line[:1]}")
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_dead_allow_flag_downgrades():
    """--allow-dead-lang понижает HARD до WARN с печатью причины (архив/чужой текст)."""
    path = os.path.join(FIXTURES, "red-dead", "DEAD-K1-simmetriya-ne-potomu.txt")
    rc, out = run_lint_file(path, ["--channel", "osn", "--form-goal", "reactions",
                                   "--form-class", "razbor",
                                   "--allow-dead-lang", "архивный текст старше правила по решению автора"])
    warn = [l for l in out.splitlines()
            if l.strip().startswith("[WARN] мёртвые конструкции")
            and "архивный текст старше правила" in l]
    no_hard = not any(l.strip().startswith("[FAIL] мёртвые конструкции") for l in out.splitlines())
    record("--allow-dead-lang понижает класс до WARN с печатью причины",
           bool(warn) and no_hard, f"warn={warn[:1]}; no_hard={no_hard}")


def test_dead_slepok_exists_and_wired():
    """Слепок живых конструкций физически существует и прописан в config.md
    скилла. Без слепка машинная половина закона осталась бы без живой."""
    problems = []
    md = None
    for cand in (".business/voice-corpus/_konstrukcii-zhivogo-yazyka.md",
                 "~/.business/voice-corpus/_konstrukcii-zhivogo-yazyka.md"):
        p = os.path.expanduser(cand)
        if os.path.isfile(p):
            md = p
            break
    if md is None:
        skip("слепок живых конструкций существует и прописан в config.md",
             "слепок живёт в .business (не раздаётся со скиллом)")
        return
    js = md[:-3] + ".json"
    if not os.path.isfile(js):
        problems.append("нет машинного зеркала .json рядом со слепком")
    else:
        try:
            data = json.load(open(js, encoding="utf-8"))
            if len(data.get("classes", [])) < 8:
                problems.append("классов в слепке < 8")
            if len(data.get("headlines", {}).get("formulas", [])) < 30:
                problems.append("формул заголовка в слепке < 30")
            for c in data.get("classes", []):
                if len(c.get("examples", [])) < 5:
                    problems.append(f"класс {c.get('id')} несёт < 5 примеров")
        except Exception as e:
            problems.append(f"json не читается: {e}")
    cfg = os.path.join(SCRIPTS, "..", "config.md")
    if os.path.isfile(cfg):
        txt = open(cfg, encoding="utf-8").read()
        if "konstrukcii-zhivogo-yazyka" not in txt:
            problems.append("config.md не ссылается на слепок (ключ voice_canon.konstrukcii)")
    else:
        problems.append("config.md скилла не найден")
    record("слепок живых конструкций: файлы на месте, >=8 классов x >=5 примеров, "
           "прописан в config.md", not problems, "; ".join(problems))


DEAD_LANG_TESTS = [test_dead_green_ivan_untouched,
                   test_dead_donor_green_untouched,
                   test_dead_package_date_opener_gate,
                   test_dead_allow_flag_downgrades,
                   test_dead_slepok_exists_and_wired]


# ===========================================================================
# МЁРТВЫЙ ЯЗЫК: ЛЕКСИКА (антисловарь абстракций, владелец)
# ===========================================================================
# Пара к блоку выше: там СИНТАКСИС (К1-К11), здесь СЛОВА. Класс до этой редакции не
# ловился НИЧЕМ - корпус red (68 фикстур) по этой лексике пуст полностью,
# поэтому фикстуры ниже первые красные этого класса. Замер и пороги - в
# lint-post.py (блок DEAD_LEX_*) и references/zhivoy-yazyk.md.
# Три части закона:
#   1) каждый порог ловится СВОЕЙ строкой (3 красных фикстуры red-lex/);
#   2) зелёный корпус НЕ красится - ни владелец (12), ни доноры (7): правило,
#      валящее принятое, сужается (feedback_gate_blocking_whole_corpus_is_regression);
#   3) слова, которые замер показал ЖИВЫМИ, не запрещаются - отдельный тест.

DEAD_LEX_FIXTURES = {
    "LEX1-tier-a-mertvye-slova.txt":   ("[FAIL] мёртвый язык (лексика)", "порог 1, лексический"),
    "LEX2-plotnost-abstrakciy.txt":    ("[FAIL] плотность абстракций", "порог 2, плотностный"),
    "LEX3-perekrestnye-pary-cliche.txt": ("[FAIL] нейросетевые связки (AI_CLICHE)", "перекрёстные пары"),
}

# Слова из references/zhivoy-yazyk.md разд.5 «живое, НЕ запрещать»: замер нашёл
# их у доноров, у владельца и в опросах аудитории. Любое срабатывание на них =
# регресс на принятом корпусе, а не находка.
DEAD_LEX_LIVE_WORDS = [
    ("точка А / точка Б", "его точка А: напроходил курсов, вроде что-то понял, "
                          "а точка Б у него это 300к в месяц"),
    ("ценность", "отвечает в минуту интереса и сразу отдает ценность, "
                 "и чем больше ты создаешь ценности, тем устойчивее растешь"),
    ("системный подход", "Простая съемка, но системный подход. Результат: "
                         "стабильный поток заявок"),
    ("новый уровень", "Вышел на новый уровень в новом году. Закрыл долги"),
    ("понимание", "мне не хватает понимания, что конкретно продавать"),
    ("видение", "Мое видение на 2026 - расслойка между новичками и топами"),
    ("экосистема", "у меня экосистема из клуба и разборов, все в одном месте"),
]


def test_dead_lex_fixture(fname):
    """Красная фикстура обязана падать СВОЕЙ строкой лексического слоя."""
    expect, why = DEAD_LEX_FIXTURES[fname]
    path = os.path.join(FIXTURES, "red-lex", fname)
    if not os.path.isfile(path):
        record(f"мёртвый язык-лексика: фикстура {fname} существует", False, f"нет файла {path}")
        return
    rc, out = run_lint_file(path, ["--channel", "osn", "--form-goal", "reactions",
                                   "--form-class", "razbor"])
    line = [l for l in out.splitlines() if l.strip().startswith(expect)]
    ok = rc == 1 and bool(line)
    record(f"мёртвый язык-лексика: {fname} ловится строкой «{expect}» ({why})", ok,
           f"rc={rc}; строка={bool(line)}\n" + out[-400:] if not ok else "")


def test_dead_lex_fail_carries_live_replacement():
    """🔴 Закон сообщения (ресёрч разд.6.3): FAIL не называет термин, а ДАЁТ
    живую замену конкретной строкой - переписывать будет модель, и ей нужен
    целевой язык, а не запрет. Строка без «живой человек говорит» бесполезна."""
    path = os.path.join(FIXTURES, "red-lex", "LEX1-tier-a-mertvye-slova.txt")
    if not os.path.isfile(path):
        record("мёртвый язык-лексика: FAIL несёт живую замену", False, "нет фикстуры LEX1")
        return
    rc, out = run_lint_file(path, ["--channel", "osn", "--form-goal", "reactions",
                                   "--form-class", "razbor"])
    repl = [l for l in out.splitlines() if "живой человек говорит:" in l]
    has_evidence = any("donor-" in l or "ivan-final" in l or "survey" in l for l in repl)
    has_ref = any("zhivoy-yazyk.md" in l for l in out.splitlines())
    ok = len(repl) >= 3 and has_evidence and has_ref
    record("мёртвый язык-лексика: FAIL печатает живую замену + улику + путь справочника",
           ok, f"строк с заменой={len(repl)}; улика={has_evidence}; справочник={has_ref}")


def test_dead_lex_green_ivan_untouched():
    """🔴 КАЛИБРОВКА. 12 постов зелёного корпуса автора обязаны идти БЕЗ единой
    строки [FAIL] лексического слоя - без флагов и без исключений по имени.
    Замер: 0 вхождений TIER-A на 15 документах владельца."""
    bad, checked = [], 0
    for fname, channel, goal, cls, arch in GREEN_IVAN_MANIFEST:
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", cls] + arch)
        for l in out.splitlines():
            s = l.strip()
            if s.startswith("[FAIL] мёртвый язык (лексика)") or \
               s.startswith("[FAIL] плотность абстракций"):
                bad.append(f"{fname}: {s[:160]}")
    if checked == 0:
        skip("мёртвый язык-лексика: зелёный корпус автора чист", NO_OWNER_CORPUS)
        return
    record(f"мёртвый язык-лексика: зелёный корпус автора {checked}/{checked} чист "
           f"(ноль [FAIL] по антисловарю)", not bad, "\n".join(bad)[:600])


def test_dead_lex_donor_green_untouched():
    """🔴 КАЛИБРОВКА. 7 донор-эталонов green/ обязаны идти чисто. Здесь порог
    строже, чем у конструкций (там допускается 1 донор с HARD): лексический
    замер дал НОЛЬ вхождений TIER-A на всех 608 постах доноров и ноль постов
    выше плотностного порога, поэтому любое срабатывание = дефект словаря."""
    rd = os.path.join(FIXTURES, "green")
    if not os.path.isdir(rd):
        skip("мёртвый язык-лексика: донор-корпус green/ чист", "нет каталога green/")
        return
    bad = []
    files = sorted(x for x in os.listdir(rd) if x.endswith(".txt"))
    for fname in files:
        rc, out = run_lint_file(os.path.join(rd, fname),
                                ["--channel", "osn", "--form-goal", "reactions",
                                 "--form-class", "razbor"])
        for l in out.splitlines():
            s = l.strip()
            if s.startswith("[FAIL] мёртвый язык (лексика)") or \
               s.startswith("[FAIL] плотность абстракций"):
                bad.append(f"{fname}: {s[:140]}")
    record(f"мёртвый язык-лексика: донор-корпус green/ {len(files)}/{len(files)} чист",
           not bad, "\n".join(bad)[:600])


def test_dead_lex_live_words_not_banned():
    """🔴 АНТИ-РЕГРЕСС. Слова, которые замер показал ЖИВЫМИ (разд.5 справочника),
    запрещать нельзя: это язык доноров, владельца и аудитории. Владелец назвал
    «точку А/Б» примером абстракции - замер показал обратное (8 вхождений)."""
    body = ("🧩 **Заголовок про замер живых слов**\n\n{line}\n\n"
            "За ту неделю вышло 18 постов вместо 9, я считал по журналу каждый день\n\n"
            "👉 Слово ЗАМЕР в комментарии, пришлю таблицу\n")
    bad = []
    for word, line in DEAD_LEX_LIVE_WORDS:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as tf:
            tf.write(body.format(line=line))
            p = tf.name
        try:
            rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "reactions",
                                        "--form-class", "razbor"])
            for l in out.splitlines():
                s = l.strip()
                if s.startswith("[FAIL] мёртвый язык (лексика)") or \
                   s.startswith("[FAIL] плотность абстракций") or \
                   s.startswith("[WARN] мёртвый язык"):
                    bad.append(f"«{word}»: {s[:140]}")
        finally:
            os.unlink(p)
    record(f"мёртвый язык-лексика: {len(DEAD_LEX_LIVE_WORDS)} живых слов НЕ запрещены "
           f"(точка А/Б, ценность, системный подход, новый уровень, понимание, видение, экосистема)",
           not bad, "\n".join(bad)[:600])


def test_dead_lex_no_overlap_with_existing_dicts():
    """🔴 ОДИН ИСТОЧНИК ИСТИНЫ. Ни один регекс антисловаря не должен дублировать
    уже стоящий словарь линтера: дубль печатал бы одно нарушение двумя строками
    и дважды считался бы в плотностном пороге. Сверяются строки паттернов и
    отдельно слова словарей воды."""
    src = open(LINT, encoding="utf-8").read()

    def _pats(name):
        m = re.search(r"^" + name + r"\s*=\s*\[(.*?)^\]", src, re.S | re.M)
        return set(re.findall(r"r'([^']*)'|r\"([^\"]*)\"", m.group(1))) if m else set()

    def _flat(s):
        return {a or b for a, b in s}
    new = set()
    for name in ("DEAD_LEX_A", "DEAD_LEX_B", "DEAD_LEX_WARN"):
        new |= _flat(_pats(name))
    old = set()
    for name in ("WATER_KANC", "AI_CLICHE", "FILLER_PATTERNS",
                 "RUBRICATOR_OPENERS_HARD", "RUBRICATOR_OPENERS_SOFT"):
        old |= _flat(_pats(name))
    dupes = sorted(new & old)
    # слова словарей воды: антисловарь не имеет права ловить то же слово
    water_words = set()
    for name in ("WATER_EVAL", "WATER_INTENS"):
        m = re.search(r"^" + name + r'\s*=\s*set\("""(.*?)"""', src, re.S | re.M)
        if m:
            water_words |= set(m.group(1).split())
    collide = sorted(w for w in water_words
                     if any(re.fullmatch(p.replace("\\b", ""), w) for p in new
                            if not any(c in p for c in "\\|()[]{}+*?^$"))) if water_words else []
    ok = not dupes and not collide
    record("мёртвый язык-лексика: ноль пересечений с WATER_KANC/AI_CLICHE/FILLER/"
           "RUBRICATOR и словарями воды", ok,
           f"дубли паттернов: {dupes}; коллизии со словами воды: {collide}")


def test_ai_cliche_crosspairs_closed():
    """🔴 ДЫРА ПЕРЕКРЁСТНОЙ ПАРЫ (находка замера по решению автора). AI_CLICHE ловил
    «стоит отметить» и «важно понимать», но их зеркала «важно отметить» и
    «стоит понимать» проходили насквозь. Проверяем ОБА направления И то, что
    антисловарь их НЕ дублирует (одно нарушение = одна строка)."""
    body = ("🧩 **Заголовок про замер пары**\n\n{line}\n\n"
            "За ту неделю вышло 18 постов вместо 9, я считал по журналу каждый день\n\n"
            "👉 Слово ПАРА в комментарии, пришлю таблицу\n")
    cases = [("важно отметить", "Важно отметить, что руками я писал заметно ровнее"),
             ("стоит понимать", "Стоит понимать и обратную сторону: машина не придумывает сцену"),
             ("стоит отметить", "Стоит отметить, что руками я писал заметно ровнее"),
             ("важно понимать", "Важно понимать и обратную сторону: сцену приношу я сам")]
    bad = []
    for word, line in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as tf:
            tf.write(body.format(line=line))
            p = tf.name
        try:
            rc, out = run_lint_file(p, ["--channel", "osn", "--form-goal", "reactions",
                                        "--form-class", "razbor"])
            caught = any(l.strip().startswith("[FAIL] нейросетевые связки (AI_CLICHE)")
                         for l in out.splitlines())
            doubled = any(l.strip().startswith("[FAIL] мёртвый язык (лексика)")
                          for l in out.splitlines())
            if not caught:
                bad.append(f"«{word}» НЕ поймано AI_CLICHE")
            if doubled:
                bad.append(f"«{word}» посчитано ДВАЖДЫ (ещё и антисловарём)")
        finally:
            os.unlink(p)
    record("AI_CLICHE: обе перекрёстные пары закрыты (важно отметить / стоит понимать) "
           "и не дублируются антисловарём", not bad, "; ".join(bad)[:400])


def test_dead_lex_allow_flag_downgrades():
    """--allow-dead-lexicon понижает лексический HARD до WARN с печатью причины.
    Флаг ОТДЕЛЬНЫЙ от --allow-dead-lang: тот про синтаксис, этот про слова."""
    path = os.path.join(FIXTURES, "red-lex", "LEX1-tier-a-mertvye-slova.txt")
    if not os.path.isfile(path):
        record("--allow-dead-lexicon понижает лексический слой до WARN", False, "нет фикстуры LEX1")
        return
    rc, out = run_lint_file(path, ["--channel", "osn", "--form-goal", "reactions",
                                   "--form-class", "razbor",
                                   "--allow-dead-lexicon", "чужой текст донор-корпуса"])
    warn = [l for l in out.splitlines()
            if l.strip().startswith("[WARN] мёртвый язык (лексика)")
            and "чужой текст донор-корпуса" in l]
    no_hard = not any(l.strip().startswith("[FAIL] мёртвый язык (лексика)")
                      or l.strip().startswith("[FAIL] плотность абстракций")
                      for l in out.splitlines())
    record("--allow-dead-lexicon понижает лексический слой до WARN с печатью причины",
           bool(warn) and no_hard, f"warn={warn[:1]}; no_hard={no_hard}")


def test_dead_lex_reference_exists_and_wired():
    """Справочник живого языка физически существует, раздаётся вместе со
    скиллом и прописан в маршруте: Read в 03-dry Шаг 0, строка верификатора
    dead-language в 04-review, каталог references в SKILL.md. авторской специфики
    внутри нет (файл уезжает ученикам как есть).

    🔴 Д116 (скептик-раунд 39, по решению автора): страж смотрел ТРИ дома и потому не
    видел РОВНО ту дыру, ради которой заведён. `references/zhivoy-yazyk.md`
    читался в ДВУХ точках маршрута из четырёх: короткий событийный маршрут
    (фаза E1, `01-router.md` разд.0.49-К - `03-dry` там в отдельный проход не
    разворачивается) и маршрут `rewrite` (`01d-rewrite.md` - идёт мимо
    `03-dry`) о справочнике не знали ВООБЩЕ, хотя код-гейт
    `check_dead_language` маршрут-нейтрален и блокирует их одинаково. Итог -
    не «гейт молчит», а «писателя блокируют, а словарь замен ему не дали».
    Зеркало `donor-copy-devices.md` этот же класс закрыло по решению автора (Д1 раунда 1)
    и держит ЧЕТЫРЕ точки. Проверяемые дома приведены к четырём + SKILL.md."""
    problems = []
    ref = os.path.expanduser("~/.claude/skills/post/references/zhivoy-yazyk.md")
    if not os.path.isfile(ref):
        record("живой язык: справочник существует и проведён в маршрут", False,
               f"нет файла {ref}")
        return
    body = open(ref, encoding="utf-8").read()
    for must in ("СЛОВАРЬ ЖИВЫХ ЗАМЕН", "ЖИВОЕ, НЕ ЗАПРЕЩАТЬ", "точка А"):
        if must not in body:
            problems.append(f"в справочнике нет раздела/строки «{must}»")
    # ивано-специфика в раздаваемом артефакте (feedback_isolate_ivan_specific_...)
    for leak in ("<твой-домен>", "start=", "@ivans", "t.me/"):
        if leak in body:
            problems.append(f"утечка ивано-специфики в раздаваемый файл: «{leak}»")
    # 🔴 Д116: ЧЕТЫРЕ точки маршрута + SKILL.md. Порядок = порядок прохождения
    # поста: полный маршрут (03-dry) · rewrite (01d) · короткий event (E1,
    # 01-router) · верификатор (04-review).
    wiring = {
        "workflow/03-dry.md": "references/zhivoy-yazyk.md",
        "workflow/01d-rewrite.md": "references/zhivoy-yazyk.md",
        "workflow/01-router.md": "references/zhivoy-yazyk.md",
        "workflow/04-review.md": "dead-language:",
        "SKILL.md": "references/zhivoy-yazyk.md",
    }
    skill_root = os.path.expanduser("~/.claude/skills/post")
    for rel, needle in wiring.items():
        p = os.path.join(skill_root, rel)
        if not os.path.isfile(p) or needle not in open(p, encoding="utf-8").read():
            problems.append(f"{rel}: нет проводки «{needle}»")
    # SKILL.md обязан ЗАЯВЛЯТЬ четыре точки, а не две (иначе доки снова разъедутся
    # с маршрутом молча - ровно так Д116 и прожил незамеченным).
    sk = os.path.join(skill_root, "SKILL.md")
    if os.path.isfile(sk):
        sk_body = open(sk, encoding="utf-8").read()
        i = sk_body.find("`references/zhivoy-yazyk.md` - **HARD read")
        if i < 0:
            problems.append("SKILL.md: строка каталога про zhivoy-yazyk.md не найдена")
        elif "ЧЕТЫРЁХ точках" not in sk_body[i:i + 300]:
            problems.append("SKILL.md: у zhivoy-yazyk.md заявлено НЕ «ЧЕТЫРЁХ точках» "
                            f"(«{sk_body[i:i + 120]}»)")
    record("живой язык: справочник существует, чист от ивано-специфики и проведён "
           "в ЧЕТЫРЁХ точках маршрута (03-dry / 01d-rewrite / 01-router E1 / "
           "04-review) + SKILL.md", not problems, "; ".join(problems)[:500])


def _dead_lex_module():
    """Живой `lint-post.py` как модуль (тот же приём importlib, что
    `test_ps_action_landing`/`test_bench_pair_coercion_loud` выше)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("lint_post_dead_lex", LINT)
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    return lp


# 🔴 7 ИМИТАЦИЙ ФИНАЛЬНОГО ЖЮРИ (по решению автора). Каждая = стерильная база плюс
# РОВНО ОДИН формальный токен. До Д1 все семь давали `sig=1` и снимали пол:
# гейт мерил не решение автора, а служебную типографику.
_SIG_STERILE = ("🧳 **Заголовок поста тут**\n\nВопрос читателю?))\n\n"
                "Обычный абзац прозой без единого приёма, просто текст 😖\n\n"
                "Ещё один такой же абзац, тоже прозой и тоже без приёмов\n")

_SIG_IMITATIONS = {
    # курсив, стоящий ТОЛЬКО в служебной 👉-CTA-строке: это типографика воронки,
    # а не акцент автора (курсив в теле поста по-прежнему законный элемент)
    "одинокий курсив в служебной 👉-строке":
        _SIG_STERILE + "\n👉 *забирай тут*\n",
    "служебное двоеточие перед длинным абзацем":
        _SIG_STERILE + "\nВот что я думаю по этому поводу:\n\nЭто длинный абзац "
                       "раскрытия, который тянется дальше шестидесяти знаков и "
                       "никаким раскрытием короткой строкой не является совершенно\n",
    "нумерация из ОДНОГО пункта":
        _SIG_STERILE + "\n1. Единственный пункт, за которым ничего не идёт\n\nДальше проза\n",
    "кавычки вокруг оборота":
        _SIG_STERILE + "\nВсё это работает через «систему контент-завода» и дальше проза\n",
    "знак → внутри 👉-строки":
        _SIG_STERILE + "\n👉 регистрация -> по ссылке в закрепе\n",
    "КАПС = МСК (таймзона в служебной строке эфира)":
        _SIG_STERILE + "\nЭфир сегодня в 19:00 МСК, приходи\n",
    "тире-опись из ОДНОГО пункта":
        _SIG_STERILE + "\n- единственный пункт описи\n\nДальше проза\n",
}

# Честный текст: КАПС-выделение, опись из трёх пунктов, реплика с местоимением,
# двоеточие с раскрытием. Обязан проходить - иначе пол ловит не имитацию, а всё.
_SIG_HONEST = """🧳 **Как я перебрал воронку за один вечер**

Сначала я думал, что дело в трафике. ВООБЩЕ не в трафике.

Разобрал по шагам:
- вынес оффер в первый экран
- убрал два лишних клика до оплаты
- переписал письмо-напоминание

Партнёр написал мне вечером: «я не понял, где тут кнопка, ты серьёзно?»

Вот и весь секрет
"""


def test_element_signature_floor():
    """🔴 по решению автора, находка владельца «докажи, что движок правда применяет
    копирайтинг», плюс Д1 финального жюри того же дня.

    ИСТОРИЯ ДЕФЕКТА В ДВА СЛОЯ. (1) Счёт «типов из 15» оказался БЕСПЛАТНЫМ:
    шесть категорий (жирный/эмодзи/вопрос/скобка/панч/эмодзи-хвост) ставит сам
    канон формы, и стерильный пост, который владелец разнёс, набирал ими 6 типов
    и получал `[PASS] 6 типов из 15`. Ответ - второй пол на подмножестве
    ELEMENTS_SIGNATURE. (2) Жюри доказало, что и ЭТОТ пол снимается ОДНИМ
    ФОРМАЛЬНЫМ ТОКЕНОМ: 7 из 7 имитаций проходили, а в зелёном корпусе 8 постов
    из 12 держали пол строкой `МСК` (таймзона в служебной строке эфира) и 9 из 12
    кавычками вокруг обычного оборота. Ответ - строгие детекторы (Д1).

    Страж держит пять вещей разом: (1) все 7 имитаций жюри валятся, (2)
    стерильный текст валится, (3) честный текст с настоящими элементами
    проходит, (4) legacy-фикстуры манифеста краснеть не обязаны и их счёт
    совпадает с записанным, (5) константы не разъехались с замером."""
    lp = _dead_lex_module()
    problems = []
    if lp.ELEMENT_SIG_FLOOR != 1:
        problems.append(f"ELEMENT_SIG_FLOOR={lp.ELEMENT_SIG_FLOOR}, решение по калибровке "
                        f"по решению автора даёт 1")
    free = {"bold", "question", "emoji_count", "smile_bracket", "short_punch", "emoji_tail"}
    if set(lp.ELEMENTS_SIGNATURE) & free:
        problems.append(f"в сигнатурный набор просочились бесплатные: "
                        f"{sorted(set(lp.ELEMENTS_SIGNATURE) & free)}")
    # Д3: цитата-блок выведен из набора - его запрещает канон формы §4 и
    # анти-паттерн R3 №5, советовать запрещённое нельзя
    if "quote_block" in lp.ELEMENTS_SIGNATURE:
        problems.append("quote_block вернулся в сигнатурный набор - конфликт Д3 "
                        "(совет линтера против HARD-запрета цитата-блока)")

    # (а) 7 имитаций жюри
    for name, txt in _SIG_IMITATIONS.items():
        got = lp.check_element_types(txt)
        if got["sig_types"] >= lp.ELEMENT_SIG_FLOOR:
            problems.append(f"ИМИТАЦИЯ ПРОХОДИТ «{name}»: sig={got['sig_types']} "
                            f"({got['sig_present']})")
    # (б) стерильный текст
    if lp.check_element_types(_SIG_STERILE)["sig_types"] >= lp.ELEMENT_SIG_FLOOR:
        problems.append("стерильный текст (жирный+вопрос+скобка+эмодзи) проходит "
                        "сигнатурный пол - дыра по решению автора вернулась")
    # (в) честный текст с настоящими элементами
    honest = lp.check_element_types(_SIG_HONEST)
    if honest["sig_types"] < 2:
        problems.append(f"честный текст с 2+ настоящими элементами не проходит: "
                        f"sig={honest['sig_types']} ({honest['sig_present']}) - "
                        f"детекторы пережали, ловят не имитацию")

    # (г) зелёный корпус: регресс считается ТОЛЬКО вне манифеста
    # расакцептованных, а счёт манифеста обязан совпадать с записанным
    # путь берётся резолвером приватного корпуса (env POST_OWNER_FIXTURES ->
    # ~/.business -> ~/.business), а не хардкодом: файл раздаётся ученикам,
    # у них этого каталога нет и группа обязана просто пропуститься
    green_dir = os.path.join(OWNER_FIXTURES, "green-ivan") if OWNER_FIXTURES else ""
    if green_dir and os.path.isdir(green_dir):
        for fn in sorted(os.listdir(green_dir)):
            if not fn.endswith(".txt"):
                continue
            r = lp.check_element_types(open(os.path.join(green_dir, fn), encoding="utf-8").read())
            legacy = ELEMENT_FLOOR_LEGACY_FIXTURES.get(fn)
            if legacy is not None:
                if r["sig_types"] != legacy["sig"] or r["types"] != legacy["types"]:
                    problems.append(f"манифест разъехался с замером: {fn} "
                                    f"sig={r['sig_types']}/типов={r['types']}, "
                                    f"записано sig={legacy['sig']}/типов={legacy['types']}")
                continue
            if r["sig_types"] < lp.ELEMENT_SIG_FLOOR:
                problems.append(f"РЕГРЕСС green вне манифеста: {fn} сигнатурных "
                                f"{r['sig_types']} - либо чинится детектор, либо файл "
                                f"вносится в ELEMENT_FLOOR_LEGACY_FIXTURES с обоснованием")
    record("сигнатурный пол элементов: 7 имитаций жюри и стерильный текст валятся, "
           "честный текст проходит, манифест расакцептованных сходится с замером "
           f"(пол {lp.ELEMENT_SIG_FLOOR} из {len(lp.ELEMENTS_SIGNATURE)})",
           not problems, "; ".join(problems)[:900])


def test_element_strict_detectors_units():
    """🔴 Д1 ЮНИТ (по решению автора). Каждая из пяти строгих правок проверяется на
    ПАРЕ «имитация против настоящего», иначе тест доказывает только полдела -
    что детектор стал строже, но не что он остался рабочим."""
    lp = _dead_lex_module()
    problems = []
    cases = [
        # (метка, текст-имитация, текст-настоящий, ключ counts)
        ("КАПС: аббревиатура против выделения",
         "Эфир в 19:00 МСК и в США тоже", "Это ВООБЩЕ не про трафик", "caps_word"),
        ("тире-опись: один пункт против блока",
         "- единственный пункт", "- первый пункт\n- второй пункт", "dash_list"),
        ("нумерация: один пункт против блока",
         "1. единственный", "1. первый\n2. второй", "numbered_list"),
        ("двоеточие: длинный абзац против короткого раскрытия",
         "Вот что вышло:\n\n" + "длинный абзац раскрытия, который тянется дальше "
         "шестидесяти знаков и коротким не является",
         "Вот что вышло:\n\nдве заявки за вечер", "colon_reveal"),
        ("знак →: служебная 👉-строка против тела",
         "👉 регистрация -> в закрепе", "лид -> заявка -> оплата", "arrow"),
        ("речь: кавычки вокруг оборота против реплики",
         "работает через «систему контент-завода» дальше",
         "он написал: «я не понял, где тут кнопка»", "direct_speech"),
    ]
    for label, fake, real, key in cases:
        if lp.check_element_types(fake)["counts"][key] != 0:
            problems.append(f"{label}: имитация всё ещё считается "
                            f"({lp.check_element_types(fake)['counts'][key]})")
        if lp.check_element_types(real)["counts"][key] == 0:
            problems.append(f"{label}: НАСТОЯЩИЙ элемент перестал считаться - "
                            f"детектор пережат")
    # расшифровка аббревиатуры соседними словами (аббревиатура НЕ из стоп-листа -
    # иначе тест доказал бы работу списка, а не правила первых букв)
    if lp.check_element_types("Общая Теория Относительности (ОТО) объясняет")["counts"]["caps_word"]:
        problems.append("КАПС из первых букв соседних слов всё ещё считается выделением")
    record("строгие детекторы Д1: 6 пар «имитация против настоящего» разведены",
           not problems, "; ".join(problems)[:700])


def test_metaphor_bank_card_literal():
    """🔴 по решению автора, ложный BLOCK на живом посте: корень «карта» ловил
    БАНКОВСКУЮ карту («установка ... даже без иностранной карты» - дословный
    канон-факт продукта). Фикс - per-hit исключение METAPHOR_BANK_CARD_CTX
    (банковский контекст в ±30 знаках). Страж держит обе стороны: буквальная
    банковская карта не ловится, метафора «покажу карту целиком» ловится."""
    lp = _dead_lex_module()
    cases = [
        ("ставим Claude Code по шагам, даже без иностранной карты", 0),
        ("привяжете карту оплаты за минуту", 0),
        ("инструмент выдаёт карту смыслов целиком", 0),
        ("Показываю карту целиком, потому что сегодня последний день", 1),
        ("эта карта приведёт тебя к деньгам", 1),
    ]
    problems = []
    for txt, exp in cases:
        got = len(lp.check_metaphor_roots(txt))
        if got != exp:
            problems.append(f"«{txt[:40]}»: hits={got}, ожидалось {exp}")
    record("метафора-корень «карта»: банковская карта буквальна (per-hit CTX), "
           "метафора-карта по-прежнему ловится", not problems, "; ".join(problems))


def test_gate_evidence_template_has_formatting_skeleton():
    """🔴 Д2 скептик-раунда 3 (по решению автора). Гейт 4.0.2 (04-review.md:135-139)
    сделал `mandatory_reads.formatting_skeleton` HARD-обязательным, но
    фенс-шаблон GATE EVIDENCE REPORT того же раздела ключа не нёс - ровно
    тот класс, из-за которого `donor_devices` был декоративным до этой редакции
    (ключ пишется, шаблон отчёта о нём молчит, ревьюер пропуск не видит).
    Страж: шаблонная зона 4.0.2 обязана нести ОБЕ строки mandatory_reads -
    donor_devices И formatting_skeleton; заодно держит запись ключа обеими
    фазами-писателями (02f Шаг 4 - маршрут full, 01d Шаг 3.4 - rewrite)."""
    problems = []
    skill_root = os.path.dirname(SCRIPTS)
    review = os.path.join(skill_root, "workflow", "04-review.md")
    src = open(review, encoding="utf-8").read()
    # зона шаблона: от заголовка 4.0.2 до следующего под-гейта
    m = re.search(r"4\.0\.2[\s\S]{0,6000}?mandatory_reads\.donor_devices", src)
    if not m:
        problems.append("04-review.md: зона 4.0.2 с donor_devices не найдена (якорь сдвинут?)")
    zone = re.search(r"GATE EVIDENCE REPORT[\s\S]{0,4000}", src)
    zone_txt = zone.group(0) if zone else src
    if "mandatory_reads.formatting_skeleton" not in zone_txt:
        problems.append("04-review.md: в шаблоне GATE EVIDENCE REPORT нет строки "
                        "mandatory_reads.formatting_skeleton (Д2 раунда 3 вернулся)")
    for path, phase in ((os.path.join(skill_root, "workflow", "02f-polish.md"), "02f Шаг 4"),
                        (os.path.join(skill_root, "workflow", "01d-rewrite.md"), "01d Шаг 3.4")):
        if "mandatory_reads.formatting_skeleton" not in open(path, encoding="utf-8").read():
            problems.append(f"{os.path.basename(path)}: фаза {phase} не пишет ключ "
                            "mandatory_reads.formatting_skeleton (Д1 раунда 3 вернулся)")
    record("гейт 4.0.2: ключ formatting_skeleton в фенс-шаблоне отчёта + обе "
           "фазы-писателя (02f full / 01d rewrite) несут запись ключа",
           not problems, "; ".join(problems))


def test_dead_lex_counts_match_docs():
    """🔴 Д109 (скептик-раунд 38, по решению автора). Заявленные счётчики словарей
    разошлись с фактом кода: `DEAD_LEX_A` заявлен 66 записей (`lint-post.py`
    комментарий над списком, `zhivoy-yazyk.md` заголовок 3.1), живой
    `len(DEAD_LEX_A)` даёт 67 - «важно отметить» из объяснительной приписки
    («67-я живёт в AI_CLICHE») в списке физически ОТСУТСТВУЕТ, приписка была
    устаревшей, не офсетом. `DEAD_LEX_WARN` заявлен 18 (`lint-post.py`,
    `zhivoy-yazyk.md` заголовок 3.3), живой `len()` даёт 19 - справочник
    сжимает пары записей в общие табличные строки через «·», а в коде это
    раздельные регекс-записи. Числа приведены к факту в обоих домах; этот
    страж - функция кода, а не разовая правка: заявленный счётчик ОБЯЗАН
    равняться `len()` живого словаря, иначе следующая правка словаря снова
    разъедет числа с доком тихо.

    🔴 МИНОР Д114-раунда (скептик-раунд 39, по решению автора): страж держал НЕ ТО,
    что заявлял. Сравнивались только `DEAD_LEX_A` и `DEAD_LEX_WARN`;
    `len(DEAD_LEX_B)` в теле теста не встречался НИ РАЗУ, а число TIER-B жило
    в трёх домах (`lint-post.py`, `zhivoy-yazyk.md` 3.2, `SKILL.md`) и не
    охранялось нигде. Регекс по `SKILL.md` физически переступал через него -
    средняя группа `DEAD_LEX_B` не захватывалась. Для TIER-B страж был
    декоративен ровно в том смысле, который сам докстринг называет дефектом.
    Теперь проверяются ВСЕ ТРИ тира во ВСЕХ домах, таблицей, а не тремя
    копиями кода: следующая правка словаря упирается в страж по любому тиру.
    """
    lp = _dead_lex_module()
    live = {"A": len(lp.DEAD_LEX_A), "B": len(lp.DEAD_LEX_B),
            "WARN": len(lp.DEAD_LEX_WARN)}
    lint_src = open(LINT, encoding="utf-8").read()
    zh_path = os.path.join(SKILL_ROOT, "references", "zhivoy-yazyk.md")
    skill_md = os.path.join(SKILL_ROOT, "SKILL.md")
    problems = []

    # (дом, тир, регекс, номер группы). Каждый тир в каждом доме - своя строка,
    # чтобы «дом молча забыл про тир» было видно как отдельный провал.
    HOMES = [
        (LINT, "lint-post.py", [
            ("A", r"TIER-A: HARD-ядро\.\s*(\d+)\s*запис", 1),
            ("B", r"TIER-B:\s*(\d+)\s*запис", 1),
            ("WARN", r"WARN-слой:\s*(\d+)\s*запис", 1),
        ]),
        (zh_path, "zhivoy-yazyk.md", [
            ("A", r"3\.1 TIER-A.*?\((\d+)\s*запис", 1),
            ("B", r"3\.2 TIER-B.*?(\d+)\s*запис", 1),
            ("WARN", r"3\.3 WARN-слой,\s*(\d+)\s*запис", 1),
        ]),
        (skill_md, "SKILL.md", [
            ("A", r"DEAD_LEX_A`\s*(\d+)\s*·\s*`DEAD_LEX_B`\s*(\d+)\s*·\s*`DEAD_LEX_WARN`\s*(\d+)", 1),
            ("B", r"DEAD_LEX_A`\s*(\d+)\s*·\s*`DEAD_LEX_B`\s*(\d+)\s*·\s*`DEAD_LEX_WARN`\s*(\d+)", 2),
            ("WARN", r"DEAD_LEX_A`\s*(\d+)\s*·\s*`DEAD_LEX_B`\s*(\d+)\s*·\s*`DEAD_LEX_WARN`\s*(\d+)", 3),
            # вторая, прозаическая копия тех же трёх чисел в каталоге references
            ("A", r"TIER-A (\d+) запис", 1),
            ("B", r"TIER-B (\d+) · WARN-омонимия (\d+)", 1),
            ("WARN", r"TIER-B (\d+) · WARN-омонимия (\d+)", 2),
        ]),
    ]
    for path, name, checks in HOMES:
        if not os.path.isfile(path):
            problems.append(f"{name} не найден по пути {path}")
            continue
        src = lint_src if path == LINT else open(path, encoding="utf-8").read()
        for tier, pat, grp in checks:
            m = re.search(pat, src, re.S)
            if not m:
                problems.append(f"{name}: счётчик TIER-{tier} не найден (якорь сдвинут?)")
            elif int(m.group(grp)) != live[tier]:
                problems.append(f"{name} TIER-{tier}={m.group(grp)}, "
                                f"live len={live[tier]}")

    record(f"мёртвый язык-лексика: заявленные счётчики ВСЕХ ТРЁХ тиров "
           f"(A={live['A']} B={live['B']} WARN={live['WARN']}) равны len() живого "
           f"словаря во ВСЕХ домах (lint-post.py x3, zhivoy-yazyk.md x3, SKILL.md x3)",
           not problems, "; ".join(problems))


# 🔒 Приватный корпус (Д110, скептик-раунд 38, по решению автора): те же правила
# изоляции, что OWNER_FIXTURES выше - corpus-12m.json (608 донор-постов) это
# ЛИЧНЫЙ архив автора, в раздаваемом пакете ученика его нет и быть не должно.
# env POST_DONOR_CORPUS_12M -> кандидатные пути в .business -> нет файла =
# SKIP этой ОДНОЙ группы, остальные тесты зелёные.
CORPUS_12M_CANDIDATES = (
    os.environ.get("POST_DONOR_CORPUS_12M") or "",
    ".business/growth/content-archive/Доноры стиля/_research/corpus-12m.json",
    "~/.business/growth/content-archive/Доноры стиля/_research/corpus-12m.json",
)


def _resolve_corpus_12m():
    for p in CORPUS_12M_CANDIDATES:
        if not p:
            continue
        fp = os.path.expanduser(p)
        if os.path.isfile(fp):
            return fp
    return None


CORPUS_12M = _resolve_corpus_12m()
NO_CORPUS_12M = ("донор-корпус corpus-12m.json (608 постов) не подключён "
                 "(POST_DONOR_CORPUS_12M / .../Доноры стиля/_research/corpus-12m.json); "
                 "заявленные проценты TIER-B/WARN не проверяются на этой машине, "
                 "но и не заявляются без подтверждения")


def test_dead_lex_b_warn_percentages_match_corpus():
    """🔴 Д110 (скептик-раунд 38, по решению автора). Заявлено «TIER-B срабатывает
    на 4.6% донор-корпуса, WARN на 7.1%» (`zhivoy-yazyk.md` порог 3,
    `lint-post.py` шапка модуля) - число НЕ ВОСПРОИЗВОДИЛОСЬ. Живой пересчёт
    по corpus-12m.json (608 постов, `check_dead_language` живого
    `lint-post.py`, доля постов с ХОТЯ БЫ ОДНИМ вхождением TIER-B/WARN
    соответственно, дедуп спанов + снятие кавычек - тот же метод, что даёт
    замер порогов 1-2 того же раздела) дал 4.3% / 2.6% - оба дома приведены
    к этому факту. Страж проверяет ОБА направления: (а) заявленные в доках
    числа совпадают с живым замером, (б) старые враньё-числа 4.6%/7.1%
    нигде не остались забытой копией."""
    if not CORPUS_12M:
        skip("мёртвый язык-лексика: TIER-B/WARN% воспроизводится по corpus-12m.json (608 постов)",
             NO_CORPUS_12M)
        return
    lp = _dead_lex_module()
    posts = json.load(open(CORPUS_12M, encoding="utf-8"))
    if not posts:
        record("мёртвый язык-лексика: TIER-B/WARN% воспроизводится по corpus-12m.json",
               False, f"corpus-12m.json пуст: {CORPUS_12M}")
        return
    b_hit = sum(1 for p in posts if lp.check_dead_language(p.get("text", ""))["b"])
    warn_hit = sum(1 for p in posts if lp.check_dead_language(p.get("text", ""))["warn"])
    b_pct = round(b_hit / len(posts) * 100, 1)
    warn_pct = round(warn_hit / len(posts) * 100, 1)
    problems = []
    # 🔴 МИНОР Д110-стража (скептик-раунд 39, по решению автора): тест ХАРДКОДИЛ
    # 4.3/2.6 и грепал доки только на СТАРУЮ фразу «4.6%». То есть он
    # сравнивал живой замер с КОНСТАНТОЙ ТЕСТА (третьей копией числа!), а
    # утверждение «доки СЕЙЧАС говорят 4.3/2.6» не проверял ВООБЩЕ - правка
    # процента в справочнике на любое другое число прошла бы мимо стража,
    # ровно тот же класс, что чинил сам Д110. СТАЛО: число ВЫПАРСИВАЕТСЯ ИЗ
    # ДОКОВ и сравнивается с живым замером; своей константы у теста больше
    # нет. Греп старой декларации оставлен вторым, независимым контролем.
    _PCT_RE = re.compile(
        r"TIER-B срабатывает на (\d+\.\d+)% донор-корпуса, WARN на (\d+\.\d+)%")
    zh_path = os.path.join(SKILL_ROOT, "references", "zhivoy-yazyk.md")
    homes = 0
    for path in (LINT, zh_path):
        if not os.path.isfile(path):
            problems.append(f"дом процентов не найден: {path}")
            continue
        body = open(path, encoding="utf-8").read()
        m = _PCT_RE.search(body)
        if not m:
            problems.append(f"{os.path.basename(path)}: заявленные проценты "
                            f"TIER-B/WARN не найдены (якорь сдвинут?)")
            continue
        homes += 1
        doc_b, doc_w = float(m.group(1)), float(m.group(2))
        if doc_b != b_pct:
            problems.append(f"{os.path.basename(path)} заявляет TIER-B {doc_b}%, "
                            f"живой замер {b_pct}%")
        if doc_w != warn_pct:
            problems.append(f"{os.path.basename(path)} заявляет WARN {doc_w}%, "
                            f"живой замер {warn_pct}%")
    if homes < 2:
        problems.append(f"проценты заявлены не во всех домах: нашли {homes} из 2")
    # Ищем СТАРУЮ ДЕКЛАРАЦИЮ конкретной фразой ("срабатывает на 4.6%" / "4.6%
    # срабатываний"), а не голую подстроку "4.6%" - файлы ЛЕГАЛЬНО несут
    # число 4.6% в ИСТОРИЧЕСКОЙ фразе «было заявлено 4.6%/7.1% - не
    # воспроизводилось» (этот же Д110-фикс объясняет находку), голая
    # подстрока считала бы эту честную историческую справку дефектом.
    _STALE_PCT_RE = re.compile(r"срабатывает на 4\.6%|4\.6% срабатыван")
    for path in (LINT, zh_path):
        if os.path.isfile(path):
            body = open(path, encoding="utf-8").read()
            if _STALE_PCT_RE.search(body):
                problems.append(f"устаревшая ДЕКЛАРАЦИЯ 4.6% всё ещё встречается в {path}")
    record(f"мёртвый язык-лексика: TIER-B/WARN% в доках = живому замеру corpus-12m.json "
           f"({len(posts)} постов, TIER-B {b_pct}%, WARN {warn_pct}%)",
           not problems, "; ".join(problems))


_DEAD_LEX_SEP_CASES = [
    ("дефис внутри TIER-A слова", "у нас за счёт мето-дологии всё расписано по шагам"),
    ("подчёркивание внутри TIER-A слова", "у нас за счёт мето_дологии всё расписано по шагам"),
]


def test_dead_lex_inword_separators():
    """🔴 Д111 (скептик-раунд 38, по решению автора, зеркало `check_metaphor_roots` -
    Р4 скептика, С13, «мини-карта»/«д_в_ерь»). У `check_dead_language` НЕ
    БЫЛО второго прохода по тексту без внутрисловных разделителей:
    «мето-дология»/«мето_дология» рвали корень TIER-A `методологи` надвое
    (регекс матчит слитное слово) и проходили гейт живого языка НЕЗАМЕЧЕННЫМИ.
    ФИКС - `_dead_lex_scan()` вынесена в отдельную функцию, второй скан по
    `_strip_inword_separators(plain)`, дедуп через `_dedup_second_pass` по
    ключу (tier, label, нормализованный фрагмент). Прямой вызов живой
    функции (импорт `lint-post.py` как модуля), не через хук - второй проход
    живёт в `lint-post.py`."""
    lp = _dead_lex_module()
    bad = []
    for name, text in _DEAD_LEX_SEP_CASES:
        res = lp.check_dead_language(text)
        if not res["a"]:
            bad.append(f"{name}: «методология» с внутрисловным разделителем НЕ поймана (tier a пуст)")
    record("мёртвый язык-лексика: второй проход без внутрисловных разделителей "
           "ловит «мето-дология»/«мето_дология» (Д111)", not bad, "; ".join(bad))


DEAD_LEX_TESTS = [test_dead_lex_fail_carries_live_replacement,
                  test_dead_lex_green_ivan_untouched,
                  test_dead_lex_donor_green_untouched,
                  test_dead_lex_live_words_not_banned,
                  test_dead_lex_no_overlap_with_existing_dicts,
                  test_ai_cliche_crosspairs_closed,
                  test_dead_lex_allow_flag_downgrades,
                  test_dead_lex_reference_exists_and_wired,
                  test_dead_lex_counts_match_docs,
                  test_dead_lex_b_warn_percentages_match_corpus,
                  test_dead_lex_inword_separators,
                  test_element_signature_floor,
                  test_element_strict_detectors_units,
                  test_metaphor_bank_card_literal,
                  test_gate_evidence_template_has_formatting_skeleton]


# ===========================================================================
# 🔴 Д110 «ФОРМАТ-ПОЛ» + Д111 «БЕЗЫМЯННЫЙ НОСИТЕЛЬ» (правки владельца
# по решению автора). Оба класса были ВШИТЫ в lint-post.py и откалиброваны по 12
# зелёным, но НЕ ЗАКРЫТЫ НИ ОДНИМ ТЕСТОМ - то есть держались только на том,
# что их никто не тронет. Здесь оба получают постоянный замок.
#
# Д110, дословно владелец: «Форматирование по канону не внедрил - просто
# заголовок жирный и всё. Форматирование это ключевая база движка». Дыра:
# `bold_target/bold_ceiling` были ОРИЕНТИРОМ без ПОЛА, и пост-простыня
# (жирный только в заголовке, голое тело) уходил зелёным в любом профиле.
# Пол лежит на ТЕЛЕ (`bold_body_min`) и на СУММЕ (`bold_min_total`).
#
# Д111, дословно владелец про свой пост osn23 («Взял свои записи за десять
# месяцев»): «Какие нахер записи? Про что речь? Про Reels? Про посты в
# Telegram?». Дыра: слово-КОРПУС без названной площадки, читатель не может
# опознать источник, и весь довод поста повисает.
#
# 🔴 ДИСЦИПЛИНА КАЛИБРОВКИ у обоих классов одна: правило, валящее зелёный
# корпус владельца, СУЖАЕТСЯ, а фикстура под порог НЕ подгоняется. Поэтому
# ниже к каждому красному тесту стоит парный контроль-зелёный, а замыкают
# оба класса прогоны по всем 12 постам владельца.
#
# Фикстуры красных - `fixtures/red/23-format-*.txt` и `24-carrier-*.txt`,
# НЕЙТРАЛЬНЫЕ по содержанию намеренно: каталог скилла раздаётся ученикам,
# ссылок/боты/имена запусков владельца в нём быть не должно.
# ===========================================================================

# Профиль -> (аргументы линта, метка профиля в выводе, пол суммы, пол тела).
# Таблица держит ровно то, что записано в FORM_PROFILES живого линта; тест
# `test_d110_floors_match_profile_table` сверяет её с кодом, чтобы молчаливый
# снос пола в одном месте краснел здесь, а не всплывал у владельца в посте.
D110_FLOOR_PROFILES = [
    (["--form-goal", "sales", "--form-class", "sales"], "S", 3, 2),
    (["--form-goal", "forwards"], "F", 2, 1),
    (["--form-goal", "sales", "--form-class", "event"], "E-событие", 2, 1),
]
# Профили БЕЗ пола - и это решение, а не пропуск: канон §3.1/§9 R-4 ставит
# нарративу цель РОВНО 1 жирный (хук), разбору 1-2, а зелёные владельца
# osn18-0608 и zakr18-den-0608 несут 1 жирный ВСЕГО и 0 в теле. Любой пол в
# теле зарубил бы 2 из 12 зелёных.
D110_NO_FLOOR_PROFILES = [
    (["--form-goal", "reactions", "--form-class", "narrative"], "R-нарратив"),
    (["--form-goal", "reactions", "--form-class", "razbor"], "R-разбор"),
]

_D110_FAIL = "[FAIL] форматирование-простыня"


def test_d110_prostynya_blocks_in_sales_forwards_event():
    """🔴 Д110 КРАСНЫЙ. Пост с ОДНИМ жирным (заголовок) и голым телом обязан
    падать HARD в S, F и E - в каждом профиле, где канон даёт форматированию
    работу навигации. Проверяется не только факт [FAIL], но и что в строке
    названы оба числа пола: диагноз обязан говорить, СКОЛЬКО добрать."""
    bad = []
    for args, label, total_min, body_min in D110_FLOOR_PROFILES:
        rc, out = run_lint("23-format-prostynya.txt", args)
        line = next((l.strip() for l in out.splitlines()
                     if l.strip().startswith(_D110_FAIL)), "")
        if rc != 1 or not line:
            bad.append(f"{label}: rc={rc}, строки [FAIL] простыни нет")
            continue
        if f"поле {body_min}" not in line or f"поле {total_min}" not in line:
            bad.append(f"{label}: в диагнозе нет полов {total_min}/{body_min} - «{line[:120]}»")
        if "заголовок 1 + тело 0" not in line:
            bad.append(f"{label}: в диагнозе нет разбивки заголовок/тело - «{line[:120]}»")
    record("Д110 формат-пол: простыня (1 жирный в заголовке, 0 в теле) падает "
           "HARD в S/F/E с числами пола в диагнозе", not bad, "; ".join(bad))


def test_d110_narrative_razbor_have_no_floor():
    """🔴 Д110 КОНТРОЛЬ-ЗЕЛЁНЫЙ (цена решения названа поимённо). Та же простыня
    в нарративе и разборе НЕ падает: там цель канона - РОВНО 1 жирный, и пола
    нет НАМЕРЕННО. Улика калибровки: зелёные владельца osn18-0608.txt и
    zakr18-den-0608.txt несут 1 жирный всего и 0 в теле - пол в теле зарубил бы
    2 из 12 зелёных. Тест держит именно это решение, а не забывчивость."""
    bad = []
    for args, label in D110_NO_FLOOR_PROFILES:
        rc, out = run_lint("23-format-prostynya.txt", args)
        if any(l.strip().startswith(_D110_FAIL) for l in out.splitlines()):
            bad.append(f"{label}: пол сработал там, где его нет по канону §3.1/§9 R-4")
    record("Д110 формат-пол: в R-нарративе и R-разборе пола нет намеренно "
           "(зелёные osn18-0608/zakr18-den-0608 несут 0 жирных в теле)",
           not bad, "; ".join(bad))


def test_d110_two_bolds_in_body_pass():
    """🔴 Д110 ЗЕЛЁНЫЙ-ПОЧИНКА. Тот же пост, где в ТЕЛЕ размечены две точки
    остановки глаза, проходит пол во всех трёх профилях. Пара красный/зелёный
    отличается РОВНО двумя парами `**` - значит гейт меряет то, что заявляет,
    а не что-то соседнее."""
    bad = []
    for args, label, _tm, _bm in D110_FLOOR_PROFILES:
        rc, out = run_lint("23-format-prostynya-fixed.txt", args)
        if any(l.strip().startswith(_D110_FAIL) for l in out.splitlines()):
            bad.append(f"{label}: 2 жирных в теле не сняли пол")
        if f"[PASS] форма-профиль {label}: жирных 3 (заголовок 1 + тело 2" not in out:
            bad.append(f"{label}: PASS-строка не печатает разбивку 1+2")
    record("Д110 формат-пол: две разметки в теле снимают пол в S/F/E "
           "(парная фикстура отличается ровно двумя `**`)", not bad, "; ".join(bad))


def test_d110_bold_split_unit():
    """🔴 Д110 ЮНИТ. `check_bold_split` = (всего, заголовок, тело), и «всего»
    обязано совпадать с `check_bold_count` НА ТОМ ЖЕ тексте: это одно множество
    совпадений, разъезд двух счётчиков уже давал дефект Д106 (bold_n=0 при
    доле жирного 10.9%). Заголовок = первый абзац, ровно как у
    `check_headline_bold`."""
    lp = _dead_lex_module()
    cases = [
        ("**Заголовок**\n\nголое тело без разметки", (1, 1, 0)),
        ("**Заголовок**\n\nтело с **акцентом** и ещё **одним**", (3, 1, 2)),
        ("Заголовок без жирного\n\nтело с **акцентом**", (1, 0, 1)),
        ("<b>Заголовок HTML</b>\n\nтело с <b>акцентом</b>", (2, 1, 1)),
        ("голый текст без единого выделения", (0, 0, 0)),
    ]
    bad = []
    for text, want in cases:
        got = lp.check_bold_split(text)
        if got != want:
            bad.append(f"{text[:32]!r}: ждём {want}, получили {got}")
        if got[0] != lp.check_bold_count(text):
            bad.append(f"{text[:32]!r}: «всего» разошлось с check_bold_count")
        if got[0] != got[1] + got[2]:
            bad.append(f"{text[:32]!r}: всего != заголовок + тело")
    record("Д110 юнит: check_bold_split даёт (всего, заголовок, тело) и «всего» "
           "совпадает с check_bold_count на том же тексте", not bad, "; ".join(bad))


def test_d110_floors_match_profile_table():
    """🔴 Д110 ЗАМОК НА ТАБЛИЦУ. Полы живут в `FORM_PROFILES` живого линта;
    здесь сверяем их с числами, которые проверяют тесты выше. Зачем отдельно:
    молчаливый снос пола (`None` вместо числа) не покраснел бы нигде - красные
    фикстуры просто перестали бы падать, и это читалось бы как «стало лучше».
    Числа обоснованы в шапке FORM_PROFILES: S - канон §3.3 (медиана 4.5, ≥4 у
    59% верха, зелёные ivan-final несут 6/5), F - §9 F-10, E - замер событийных
    зелёных, R - пола нет."""
    lp = _dead_lex_module()
    bad = []
    # Ключ событийного профиля - ("event", "event"), а не ("sales", "event"):
    # `resolve_form_profile` приводит цель к классу (см. LAST_FORM_COERCION),
    # поэтому CLI-аргументы `--form-goal sales --form-class event` в таблицу
    # профилей приходят уже как event/event. Тесты выше гоняют лint через CLI,
    # этот - через таблицу, и разница ключей здесь названа намеренно.
    want = {("sales", "sales"): (3, 2), ("forwards", "forwards"): (2, 1),
            ("event", "event"): (2, 1),
            ("reactions", "narrative"): (None, None),
            ("reactions", "razbor"): (None, None),
            ("gate", "gate"): (None, None)}
    for key, (tot, body) in want.items():
        prof = lp.FORM_PROFILES.get(key)
        if prof is None:
            bad.append(f"{key}: профиля нет в FORM_PROFILES")
            continue
        got = (prof.get("bold_min_total"), prof.get("bold_body_min"))
        if got != (tot, body):
            bad.append(f"{key}: полы {got}, ждём {(tot, body)}")
    record("Д110 замок: полы жирного в FORM_PROFILES = S 3/2, F 2/1, E 2/1, "
           "R без пола (молчаливый снос краснеет здесь)", not bad, "; ".join(bad))


def test_d110_green_ivan_no_prostynya():
    """🔴 Д110 КАЛИБРОВКА ПО КОРПУСУ. Ни один из 12 зелёных постов владельца не
    ловится классом «форматирование-простыня» в своём профиле. Правило, валящее
    зелёный, сужается - фикстура под порог не подгоняется."""
    bad, checked = [], 0
    for fname, channel, goal, cls, arch in GREEN_IVAN_MANIFEST:
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", cls] + arch)
        for l in out.splitlines():
            if l.strip().startswith(_D110_FAIL):
                bad.append(f"{fname}: {l.strip()[:150]}")
    if checked == 0:
        skip("Д110 формат-пол: зелёный корпус автора чист", NO_OWNER_CORPUS)
        return
    record(f"Д110 формат-пол: зелёный корпус автора {checked}/{checked} чист "
           f"(ноль [FAIL] простыни)", not bad, "\n".join(bad)[:600])


def test_d110_event_green_no_prostynya():
    """🔴 Д110 КАЛИБРОВКА, СОБЫТИЙНАЯ ВЕТКА. Пол E введён по замеру событийных
    зелёных (b17-3-0508 - 3 жирных в теле, inf18-0608 - 2), значит обе эти
    фикстуры обязаны идти чисто ИМЕННО под `--form-class event`, а не только
    под разбором."""
    bad, checked = [], 0
    for fname, channel, goal, arch in EVENT_GREEN:
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", "event"] + arch)
        for l in out.splitlines():
            if l.strip().startswith(_D110_FAIL):
                bad.append(f"{fname}: {l.strip()[:150]}")
    if checked == 0:
        skip("Д110 формат-пол: событийные зелёные чисты", NO_OWNER_CORPUS)
        return
    record(f"Д110 формат-пол: событийные зелёные {checked}/{checked} чисты "
           f"под --form-class event", not bad, "\n".join(bad)[:600])


_D111_FAIL = "[FAIL] носитель без площадки"
_D111_ARGS = ["--form-goal", "reactions", "--form-class", "razbor"]


def test_d111_unnamed_carrier_blocks():
    """🔴 Д111 КРАСНЫЙ. «Взял свои записи за десять месяцев» без названной
    площадки падает HARD, и диагноз цитирует САМО слово-носитель - иначе автор
    не поймёт, какое из слов поста чинить."""
    rc, out = run_lint("24-carrier-unnamed.txt", _D111_ARGS)
    lines = [l.strip() for l in out.splitlines() if l.strip().startswith(_D111_FAIL)]
    ok = rc == 1 and lines and "«записи»" in lines[0]
    record("Д111 носитель: «свои записи за десять месяцев» без площадки падает "
           "HARD с цитатой слова", ok,
           f"rc={rc}; строк={len(lines)}; первая={lines[0][:160] if lines else '-'}")


def test_d111_named_platform_passes():
    """🔴 Д111 КОНТРОЛЬ-ЗЕЛЁНЫЙ. Та же фраза с названной площадкой («записи в
    Телеграме») проходит. Пара красный/зелёный отличается РОВНО двумя словами -
    значит гейт меряет площадку, а не длину или соседний класс."""
    rc, out = run_lint("24-carrier-named.txt", _D111_ARGS)
    fails = [l for l in out.splitlines() if l.strip().startswith(_D111_FAIL)]
    ok = not fails and "[PASS] носитель назван площадкой" in out
    record("Д111 носитель: «записи в Телеграме» проходит (пара отличается "
           "двумя словами)", ok, "\n".join(fails)[:300])


def test_d111_allow_flag_downgrades():
    """🔴 Д111 ФЛАГ. `--allow-unnamed-carrier ПРИЧИНА` понижает класс до WARN и
    ПЕЧАТАЕТ причину. Законная область флага узкая: площадка названа не текстом
    (картинкой, шапкой канала); в живой выдаче она обязана быть словом."""
    rc, out = run_lint("24-carrier-unnamed.txt",
                       _D111_ARGS + ["--allow-unnamed-carrier", "тест-причина"])
    warn = [l.strip() for l in out.splitlines()
            if l.strip().startswith("[WARN] носитель без площадки")]
    ok = (not any(l.strip().startswith(_D111_FAIL) for l in out.splitlines())
          and warn and "тест-причина" in warn[0])
    record("Д111 носитель: --allow-unnamed-carrier понижает до WARN и печатает "
           "причину", ok, f"warn={warn[:1]}")


def test_d111_calibration_narrowings():
    """🔴 Д111 ЮНИТ-КАЛИБРОВКА, ПОИМЁННО. Широкое правило «любое слово-носитель
    обязано нести площадку» валило 11 зелёных из 12, поэтому класс сужен ДВАЖДЫ,
    и оба сужения держит этот тест:

      1) слова, КОТОРЫЕ САМИ НАЗЫВАЮТ ФОРМУ (пост, ролик, карусель, сторис,
         блог, канал), читатель опознаёт без площадки - класс их не трогает;
      2) слово-корпус ловится, ТОЛЬКО когда присвоено («свои записи») или
         отмерено сроком («записи за десять месяцев»), то есть подано как
         ИСТОЧНИК ДАННЫХ поста; голое «вход и записи открыты» (зелёные
         ivan-final-0/1/2, там это записи занятий) легально;
      3) хвост `(?![\\w-])` выводит составное слово: «контент-завод» это ИМЯ
         СИСТЕМЫ, а не корпус публикаций (зелёный etalon-0608).

    Плюс окно в ДВЕ фразы: площадка, названная в ПРЕДЫДУЩЕМ предложении,
    закрывает носитель (зелёный inf17-0508)."""
    lp = _dead_lex_module()
    cases = [
        # (текст, ловится ли, за что отвечает случай)
        ("Взял свои записи за десять месяцев и посмотрел на заявки", True,
         "прецедент владельца osn23"),
        ("Взял свои записи в Телеграме за десять месяцев", False, "площадка названа"),
        ("Вход и записи открыты", False, "голое слово без присвоения - ivan-final"),
        ("Написал посты, собрал воронку", False, "слово называет форму - ivan-final"),
        ("У меня ролики собираются с нуля, без камеры", False, "форма - inf17-0508"),
        ("Я не рисую карусели и не открываю редактор", False, "форма - zakr18-den-0608"),
        ("Наталия собрала сайт и блог сама", False, "форма - inf18-0608"),
        ("Перестроить свой контент-завод и ИИ-блог", False,
         "составное имя системы - etalon-0608"),
        ("Свой архив я тут разбирал по полкам", False, "указательная привязка «тут»"),
        ("Мой архив за год лежал мёртвым грузом", True, "присвоен и отмерен, площадки нет"),
        ("Раз уж многие выдохлись от рилсов. Свои материалы я пересобрал заново",
         False, "площадка в ПРЕДЫДУЩЕМ предложении - окно в две фразы"),
    ]
    bad = []
    for text, want_hit, why in cases:
        hits = lp.check_unnamed_carrier(text)
        if bool(hits) != want_hit:
            bad.append(f"«{text[:46]}» ({why}): ждём {'ловится' if want_hit else 'чисто'}, "
                       f"получили {hits[:1]}")
    record("Д111 носитель: оба сужения калибровки держатся (форма-слова, голое "
           "слово, составное имя, окно в две фразы) - 11 случаев", not bad,
           "; ".join(bad))


def test_d111_green_ivan_untouched():
    """🔴 Д111 КАЛИБРОВКА ПО КОРПУСУ. 12 зелёных постов владельца обязаны идти
    БЕЗ единой строки [FAIL] носителя - без флагов и без исключений по имени.
    Это тот самый замер, которым класс сужался: широкая версия валила 11 из 12."""
    bad, checked = [], 0
    for fname, channel, goal, cls, arch in GREEN_IVAN_MANIFEST:
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", cls] + arch)
        for l in out.splitlines():
            if l.strip().startswith(_D111_FAIL):
                bad.append(f"{fname}: {l.strip()[:150]}")
    if checked == 0:
        skip("Д111 носитель: зелёный корпус автора чист", NO_OWNER_CORPUS)
        return
    record(f"Д111 носитель: зелёный корпус автора {checked}/{checked} чист "
           f"(широкое правило валило 11 из 12)", not bad, "\n".join(bad)[:600])


def test_d111_donor_green_untouched():
    """🔴 Д111 КАЛИБРОВКА ПО ДОНОРАМ. 7 донор-эталонов `fixtures/green/` тоже
    обязаны идти чисто: класс говорит про ЯСНОСТЬ для читателя, а не про личное
    правило владельца, значит на чужом сильном тексте он срабатывать не должен."""
    rd = os.path.join(FIXTURES, "green")
    if not os.path.isdir(rd):
        skip("Д111 носитель: донор-корпус green/ чист", "нет каталога green/")
        return
    bad, checked = [], 0
    for fname in sorted(os.listdir(rd)):
        if not fname.endswith(".txt") or is_owner_green(fname):
            continue
        checked += 1
        rc, out = run_lint_file(os.path.join(rd, fname),
                                _D111_ARGS + COMMON_GREEN_FLAGS)
        for l in out.splitlines():
            if l.strip().startswith(_D111_FAIL):
                bad.append(f"{fname}: {l.strip()[:150]}")
    record(f"Д111 носитель: донор-корпус green/ {checked} эталонов чист",
           not bad and checked > 0, "\n".join(bad)[:600] or "эталонов не найдено")


FORM_FLOOR_TESTS = [test_d110_prostynya_blocks_in_sales_forwards_event,
                    test_d110_narrative_razbor_have_no_floor,
                    test_d110_two_bolds_in_body_pass,
                    test_d110_bold_split_unit,
                    test_d110_floors_match_profile_table,
                    test_d110_green_ivan_no_prostynya,
                    test_d110_event_green_no_prostynya]

CARRIER_TESTS = [test_d111_unnamed_carrier_blocks,
                 test_d111_named_platform_passes,
                 test_d111_allow_flag_downgrades,
                 test_d111_calibration_narrowings,
                 test_d111_green_ivan_untouched,
                 test_d111_donor_green_untouched]


# ===========================================================================
# ЭЛЕМЕНТЫ ФОРМЫ (по решению автора, разнос владельца: «нет элементов и выделений как
# у доноров... вообще нет никаких прикольных элементов... измени движок чтобы
# элементы копи были забраны и движок скилла их каждый раз давал мне»).
#
# ЗАМЕР (element-census.py, по решению автора): 608 донорских постов - медиана 6
# разных типов элементов на пост, q1 = 4; 12 принятых владельцем постов -
# медиана 5, МИНИМУМ 3; 3 эталона A-telegram - минимум 4.
# Отсюда пол HARD = 3 (его держит весь зелёный корпус) и цель WARN = 6.
# Эта группа стережёт ОБА уровня и границу флага.
# ===========================================================================

_EL_FAIL = "[FAIL] элементы формы"
_EL_WARN = "[WARN] элементы формы"
_EL_PASS = "[PASS] элементы формы"
_EL_ARGS = ["--form-goal", "reactions", "--form-class", "razbor"]

# 2 типа ровно: жирный (заголовок) + вопрос. Ни капса, ни эмодзи, ни описи, ни
# панч-строк (все строки длиннее 25 знаков), ни строк на двоеточии, ни прямой
# речи, ни скобок-улыбок - это и есть та «голая простыня», за которую владелец
# разнёс выдачу по решению автора.
_EL_STERILE = (
    "**Заголовок про сборку системы за неделю плотной работы**\n\n"
    "Первый абзац рассказывает, как я собирал систему руками и что из этого "
    "вышло за неделю работы над задачей\n\n"
    "Второй абзац про то, зачем это нужно и почему я взялся за него именно "
    "сейчас, а не месяцем позже?\n"
)

# 6 типов: жирный + КАПС + вопрос + тире-опись + эмодзи + панч-строка.
_EL_RICH = (
    "🔥 **Заголовок про сборку системы за неделю плотной работы**\n\n"
    "Первый абзац рассказывает, как я собирал систему руками и что из этого "
    "вышло за неделю работы над задачей\n\n"
    "Собрал ВСЁ вот так\n\n"
    "- первый пункт описи, что именно лежит внутри системы\n"
    "- второй пункт описи, чем она отличается от прошлой сборки\n\n"
    "Работает\n\n"
    "Второй абзац про то, зачем это нужно и почему я взялся именно сейчас?\n"
)


def _el_lines(out, prefix):
    return [l.strip() for l in out.splitlines() if l.strip().startswith(prefix)]


def test_elements_sterile_text_fails():
    """🔴 КРАСНЫЙ. Пост на двух типах элементов (жирный + вопрос) обязан валить
    HARD-пол 3. Это ровно та выдача, которую владелец забраковал по решению автора: гейта
    на неё не было вообще - `check_formatting_devices` свою квоту потерял
    каноном §8.2, а замены ему не поставили."""
    path = _tmp_post(_EL_STERILE)
    try:
        rc, out = run_lint_file(path, _EL_ARGS)
    finally:
        os.unlink(path)
    fail = _el_lines(out, _EL_FAIL)
    ok = bool(fail) and "2 типов" in fail[0] and "HARD-пол 3" in fail[0]
    record("элементы формы: стерильный текст (2 типа) валит HARD-пол 3",
           ok, f"строки={fail[:1]}")


def test_elements_flag_downgrades_to_warn():
    """🔴 ФЛАГ. `--allow-element-floor ПРИЧИНА` понижает пол до WARN и ПЕЧАТАЕТ
    причину. Законная область узкая: чужой или архивный текст - пол снят с
    зелёного корпуса ВЛАДЕЛЬЦА, чужой текст ему не обязан."""
    path = _tmp_post(_EL_STERILE)
    try:
        rc, out = run_lint_file(path, _EL_ARGS
                                + ["--allow-element-floor", "тест-причина"])
    finally:
        os.unlink(path)
    warn = _el_lines(out, _EL_WARN)
    ok = (not _el_lines(out, _EL_FAIL)
          and bool(warn) and "тест-причина" in warn[0])
    record("элементы формы: --allow-element-floor понижает до WARN и печатает "
           "причину", ok, f"warn={warn[:1]}")


def test_elements_rich_text_passes():
    """🔴 ЗЕЛЁНЫЙ. Синтетика на 6 типах (жирный · КАПС · вопрос · тире-опись ·
    эмодзи · панч-строка) обязана дать PASS: 6 это цель, медиана доноров."""
    path = _tmp_post(_EL_RICH)
    try:
        rc, out = run_lint_file(path, _EL_ARGS)
    finally:
        os.unlink(path)
    ok = bool(_el_lines(out, _EL_PASS)) and not _el_lines(out, _EL_FAIL)
    record("элементы формы: синтетика 6+ типов даёт PASS",
           ok, f"строки={_el_lines(out, _EL_PASS)[:1] or _el_lines(out, _EL_WARN)[:1]}")


def test_elements_green_ivan_never_fails():
    """🔴 КАЛИБРОВКА ПО КОРПУСУ. 12 принятых владельцем постов идут без строки
    `[FAIL] элементы формы` - КРОМЕ явно названных в манифесте
    ELEMENT_FLOOR_LEGACY_FIXTURES.

    🔴 ПОЧЕМУ ПОЯВИЛОСЬ ИСКЛЮЧЕНИЕ (по решению автора). До Д1 тест держал закон «пол
    равен минимуму зелёного корпуса». После строгих детекторов минимум просел
    (`ivan-final-1/2` дают 2 типа), и понижать по ним пол ЗАПРЕЩЕНО решением по
    калибровке: владелец сам забраковал уровень текстуры своих выданных
    постов, значит на этой оси green расакцептован. Файлы вынесены в манифест
    поимённо, со счётом, и по ним прощаются ТОЛЬКО две строки element-floor -
    все прочие гейты по этим же файлам работают как раньше."""
    bad, checked, legacy_hits = [], 0, []
    for fname, channel, goal, cls, arch in GREEN_IVAN_MANIFEST:
        path = owner_fixture("green-ivan", fname)
        if path is None:
            continue
        checked += 1
        rc, out = run_lint_file(path, ["--channel", channel, "--form-goal", goal,
                                       "--form-class", cls] + arch)
        lines = _el_lines(out, _EL_FAIL)
        if fname in ELEMENT_FLOOR_LEGACY_FIXTURES:
            if lines:
                legacy_hits.append(fname)
            continue
        for l in lines:
            bad.append(f"{fname}: {l[:150]}")
    if checked == 0:
        skip("элементы формы: зелёный корпус владельца держит пол 3", NO_OWNER_CORPUS)
        return
    record(f"элементы формы: зелёный корпус {checked}/{checked} держит пол 3, "
           f"кроме {len(legacy_hits)} расакцептованных из манифеста "
           f"({', '.join(legacy_hits) or 'нет'})", not bad, "\n".join(bad)[:600])


def test_elements_floor_matches_measured_minimum():
    """🔴 ЮНИТ. Пороги в коде обязаны совпадать с замером. Тест держит числа от
    тихого дрейфа - «улучшить» порог без нового замера запрещено.

    Пол 3 / цель 6 - замер по 15 категориям (строгий перемер по решению автора дал ту
    же медиану доноров 6). Сигнатурный пол 1 / цель 2 - строгий замер:
    медиана 608 доноров равна 2, поэтому цель именно 2, а не «на глаз»."""
    lp = _dead_lex_module()
    problems = []
    if not (lp.ELEMENT_TYPES_FLOOR == 3 and lp.ELEMENT_TYPES_TARGET == 6):
        problems.append(f"15-типовой уровень: пол={lp.ELEMENT_TYPES_FLOOR} "
                        f"цель={lp.ELEMENT_TYPES_TARGET}, замер даёт 3/6")
    # 1.5.2: ожидание 15 осталось от замера 19.08, а 20.08 владелец вывел скобку
    # `))` из набора элементов формы («это шаблонность»), и живой состав стал 14.
    # Сторож держит СОГЛАСОВАННОСТЬ трёх множеств и фактическое число от дрейфа,
    # но больше не требует числа, отменённого правкой владельца
    ELEMENTS_SOSTAV = 14
    if len(lp.ELEMENTS_15) != ELEMENTS_SOSTAV or set(lp.ELEMENTS_15) != set(lp.ELEMENT_TOP_SHARE) \
            or set(lp.ELEMENTS_15) != set(lp.ELEMENT_LABELS):
        problems.append(f"состав категорий разъехался: {len(lp.ELEMENTS_15)} "
                        f"при ожидании {ELEMENTS_SOSTAV}, либо множества не совпали")
    if not (lp.ELEMENT_SIG_FLOOR == 1 and lp.ELEMENT_SIG_TARGET == 2):
        problems.append(f"сигнатурный уровень: пол={lp.ELEMENT_SIG_FLOOR} "
                        f"цель={lp.ELEMENT_SIG_TARGET}, строгий замер даёт 1/2 "
                        f"(цель = медиана 608 доноров)")
    if len(lp.ELEMENTS_SIGNATURE) != 8:
        problems.append(f"сигнатурных {len(lp.ELEMENTS_SIGNATURE)}, после выноса "
                        f"quote_block (Д3) их 8")
    if set(lp.ELEMENTS_SIGNATURE) != set(lp.ELEMENT_SIG_STRICT_SHARE):
        problems.append("ELEMENT_SIG_STRICT_SHARE разъехался с ELEMENTS_SIGNATURE")
    if not set(lp.ELEMENTS_SIGNATURE) <= set(lp.ELEMENTS_15):
        problems.append("сигнатурный набор вышел за 15 категорий")
    record("элементы формы: пол 3 / цель 6 / 15 категорий и сигнатурные 1 / 2 / 8 "
           "совпадают с замером", not problems, "; ".join(problems)[:500])


def test_elements_never_advise_forbidden():
    """🔴 Д3 (по решению автора). КОНФЛИКТ СОВЕТА И ЗАПРЕТА. Линтер советовал поставить
    цитата-блок (20% верха), а канон формы §4 держит на него потолок 0 с
    пометкой HARD-запрет и анти-паттерн R3 №5 (`ap5_quote_block_razbor`) валит
    его в классе `razbor`. Совет вёл прямо в FAIL соседнего гейта.

    Фикс: `quote_block` выведен и из сигнатурного набора, и из строки-совета.
    Страж держит обе стороны - совета нет, а в переписи 15 категорий он остался
    (доноры его несут, мерить корпус надо честно)."""
    lp = _dead_lex_module()
    problems = []
    if "quote_block" not in lp.ELEMENTS_NEVER_ADVISE:
        problems.append("quote_block не помечен как «не советовать»")
    if "quote_block" not in lp.ELEMENTS_15:
        problems.append("quote_block выпал из переписи 15 категорий - состав менять нельзя")
    if "quote_block" in lp.ELEMENTS_SIGNATURE:
        problems.append("quote_block остался в сигнатурном наборе")
    sterile = ("🧳 **Заголовок**\n\nВопрос?))\n\nАбзац прозой 😖\n\nЕщё абзац прозой\n")
    r = lp.check_element_types(sterile)
    advice = lp.element_missing_line(r["missing"], limit=15)
    if "цитата-блок" in advice:
        problems.append(f"строка-совет по 15 категориям всё ещё зовёт цитата-блок: {advice[:120]}")
    sig_advice = lp.element_sig_missing_line(r["sig_missing"], limit=15)
    if "цитата-блок" in sig_advice:
        problems.append(f"сигнатурный совет всё ещё зовёт цитата-блок: {sig_advice[:120]}")
    record("Д3: цитата-блок не советуется ни одной строкой линтера (канон §4 "
           "держит на него потолок 0), но в переписи 15 категорий остался",
           not problems, "; ".join(problems)[:500])


def test_elements_signature_flag_is_separate():
    """🔴 Д6 (по решению автора). ОДНА ПРИЧИНА НА ДВА ЗАКОНА. `--allow-element-floor`
    снимал ОБА пола разом, а его help описывал только «3 типа»: причина,
    написанная под один закон, молча извиняла второй.

    Решение - РАЗВЕСТИ НА ДВА ФЛАГА (не «переписать help честно»): пол переписи
    формы и пол авторской текстуры это разные законы с разными областями
    законного снятия, и общий флаг делает вторую причину неназванной по
    построению. Страж держит: (1) element-floor НЕ снимает сигнатурный,
    (2) signature-floor снимает именно его и печатает причину, (3) help каждого
    флага называет СВОЙ пол."""
    problems = []
    path = _tmp_post(_EL_STERILE)
    try:
        rc, out = run_lint_file(path, _EL_ARGS + ["--allow-element-floor", "тест-типы"])
        if not any(l.strip().startswith("[FAIL] сигнатурные элементы")
                   for l in out.splitlines()):
            problems.append("--allow-element-floor снял и сигнатурный пол - Д6 вернулся")
        rc2, out2 = run_lint_file(path, _EL_ARGS
                                  + ["--allow-signature-floor", "тест-сигнатура"])
        sig_warn = [l.strip() for l in out2.splitlines()
                    if l.strip().startswith("[WARN] сигнатурные элементы")]
        if not sig_warn or "тест-сигнатура" not in sig_warn[0]:
            problems.append(f"--allow-signature-floor не понизил до WARN с причиной: {sig_warn[:1]}")
        if any(l.strip().startswith("[FAIL] сигнатурные элементы") for l in out2.splitlines()):
            problems.append("--allow-signature-floor не снял свой пол")
    finally:
        os.unlink(path)
    rc3, help_out = run_lint_file(os.devnull, ["--help"])
    if "--allow-signature-floor" not in help_out:
        problems.append("флаг --allow-signature-floor не объявлен в help")
    record("Д6: два пола - два флага, каждый help называет свой пол",
           not problems, "; ".join(problems)[:500])


# 🔴 «ДЕШЁВЫЙ» ПОСТ ФИНАЛЬНОГО ЖЮРИ (по решению автора). Нормальный по всем прочим
# гейтам текст (длина, плотность, ритм, точки, факты), у которого ЕДИНСТВЕННЫЙ
# сигнатурный токен - `МСК` в служебной строке эфира плюс стрелка в 👉-строке.
# До Д1 такой пост брал пол и уходил зелёным; проверено живьём - без флага он
# даёт ровно одну строку [FAIL] (сигнатурные элементы) и rc=1, с флагом rc=0.
_EL_CHEAP_JURY = (
    "🧳 **Собрал воронку за вечер и показываю результат**\n\n"
    "Вчера я сел и перебрал цепочку от заявки до оплаты 😖\n\n"
    "Было 4 шага до кнопки. Стало 2 шага\n\n"
    "Заявок за сутки пришло 17, а позавчера было 6\n\n"
    "Артём из второго потока написал вечером, что дошёл до оплаты с первого раза))\n\n"
    "Я думал, дело в трафике. Дело было в третьем шаге, где форма просила телефон\n\n"
    "Убрал поле с телефоном и перенёс кнопку выше. Времени ушло 40 минут\n\n"
    "Проверил на двух браузерах, потом на телефоне. Всё живое\n\n"
    "Что дальше?\n\n"
    "Разбираю сборку на эфире сегодня в 19:00 МСК, приходи\n\n"
    "👉 регистрация -> по ссылке в закрепе\n"
)


def test_elements_flag_application_goes_to_stderr():
    """🔴 Д5 (по решению автора). НЕВИДИМОЕ ОСЛАБЛЕНИЕ. Применение флага печаталось
    только в stdout, а хук на exit 0 stdout не показывает - снятый HARD-пол не
    видел никто. По закону state факт применения флага обязан идти в stderr
    ДАЖЕ при exit 0.

    Условие теста жёсткое именно поэтому: берём текст, который валит ТОЛЬКО
    сигнатурный пол, снимаем его флагом и требуем rc=0 при НЕПУСТОМ stderr.
    Пустой stderr при rc=0 - это и есть тот самый невидимый обход."""
    problems = []
    path = _tmp_post(_EL_CHEAP_JURY)
    try:
        cmd = [sys.executable, LINT, path, "--skeleton-log", TMP_SKELETON_LOG,
               "--used-anchors-log", TMP_ANCHOR_LOG] + _EL_ARGS + [
            "--allow-signature-floor", "архивный чужой текст"]
        p = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        os.unlink(path)
    if p.returncode != 0:
        problems.append(f"rc={p.returncode}, единственный пол снят флагом - ожидался 0")
    if not p.stderr.strip():
        problems.append("stderr ПУСТ при rc=0 - ослабление снова невидимо для хука")
    for needle in ("--allow-signature-floor", "архивный чужой текст"):
        if needle not in p.stderr:
            problems.append(f"в stderr нет «{needle}»")
    record("Д5: применение флага-понижателя печатается в stderr даже при rc=0",
           not problems, f"rc={p.returncode}; stderr={p.stderr.strip()[:300]}")


def test_elements_cheap_post_of_jury_fails_live():
    """🔴 ЖИВОЙ КОНТР-ПРОГОН (по решению автора). Тот же «дешёвый» пост БЕЗ флага
    обязан давать FAIL сигнатурного пола и rc=1. Это финальная приёмка Д1:
    текст, который по всем остальным гейтам зелёный, больше не проходит на
    служебном токене."""
    path = _tmp_post(_EL_CHEAP_JURY)
    try:
        rc, out = run_lint_file(path, _EL_ARGS)
    finally:
        os.unlink(path)
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith("[FAIL]")]
    sig_fail = [l for l in fails if l.startswith("[FAIL] сигнатурные элементы")]
    ok = bool(sig_fail) and rc == 1 and len(fails) == 1
    record("живой контр-прогон: «дешёвый» пост с единственным токеном МСК валит "
           "сигнатурный пол и только его", ok,
           f"rc={rc}; всего FAIL={len(fails)}; {fails[:2]}")


ELEMENT_TESTS = [test_elements_sterile_text_fails,
                 test_elements_flag_downgrades_to_warn,
                 test_elements_rich_text_passes,
                 test_elements_green_ivan_never_fails,
                 test_elements_floor_matches_measured_minimum,
                 test_elements_never_advise_forbidden,
                 test_elements_signature_flag_is_separate,
                 test_elements_flag_application_goes_to_stderr,
                 test_elements_cheap_post_of_jury_fails_live]


R5_GUARD_TESTS = [test_r5_receipt_write_blocked,
                  test_r5_receipt_layers_allowed,
                  test_r5_receipt_verdict_edit_blocked,
                  test_r5_receipt_bash_blocked,
                  test_r5_receipt_bypass_declared,
                  test_r5_receipt_guard_syntax,
                  test_r5_gate_signs_receipt,
                  test_r5_deliver_checks_signature_and_freshness,
                  test_r5_bank_guard_ten_constructs,
                  test_r5_bank_guard_controls,
                  test_r5_shared_lexicon_is_single_source,
                  test_r5_canary_watches_bank_and_dumps,
                  test_r5_canary_is_fast,
                  test_r5_canary_syntax]


def main():
    global TMP_SKELETON_LOG, TMP_ANCHOR_LOG
    tmpdir = tempfile.mkdtemp(prefix="post-lint-tests-")
    TMP_SKELETON_LOG = os.path.join(tmpdir, ".skeleton-log.jsonl")
    TMP_ANCHOR_LOG = os.path.join(tmpdir, ".used-anchors.jsonl")

    print("=" * 60)
    print("RED-фикстуры (13 классов R2-feedback-taxonomy.md)")
    print("=" * 60)
    for t in RED_TESTS:
        t()

    print()
    print("=" * 60)
    print("ДЕФЕКТ 2 (раунд 9): абзацы-абстракции без словарных маркеров (R2-1-b)")
    print("=" * 60)
    test_red_substance_abstraction()
    test_green_substance_narrative_excluded()

    print()
    print("=" * 60)
    print("ВОЛНА 15: ритм в словах · живой слой · механика класса")
    print("=" * 60)
    for t in W15_TESTS:
        t()

    print()
    print("=" * 60)
    print("GREEN-фикстуры (7 донор-постов Донор-А/Донор-Б + 3 финала владельца)")
    print("=" * 60)
    for entry in GREEN_MANIFEST:
        test_green(entry)

    print()
    print("=" * 60)
    print("GREEN·финалы владельца БЕЗ маски класса «код-слово» (п.11)")
    print("=" * 60)
    for entry in GREEN_MANIFEST:
        if entry["file"].startswith("ivan-final-"):
            test_green_ivan_full(entry)

    print()
    print("=" * 60)
    print("4c · GREEN-IVAN (12 постов-эталонов автора, матрица класс→флаги)")
    print("=" * 60)
    for entry in GREEN_IVAN_MANIFEST:
        test_green_ivan_corpus(entry)

    print()
    print("=" * 60)
    print("4c · RED-CLASSES (47 фикстур брака, каждая своим классом)")
    print("=" * 60)
    _rd = os.path.join(FIXTURES, "red-classes")
    for fname in sorted(x for x in os.listdir(_rd)
                        if x.endswith(".txt") and ".factbase" not in x):
        test_red_class_corpus(fname)
    test_red_gaps_are_still_gaps()

    print()
    print("=" * 60)
    print("4c · ДЫРЫ ВСЁ ЕЩЁ ДЫРЫ (прогон линта по каждой gap-фикстуре)")
    print("=" * 60)
    for fname in sorted(RED_CLASS_KNOWN_GAPS):
        test_red_gaps_really_not_caught(fname)

    print()
    print("=" * 60)
    print("P.S.-Action на посте-лендинге (ВАЖНО 7, скептик-раунд 4)")
    print("=" * 60)
    test_ps_action_landing()

    print()
    print("=" * 60)
    print("bench-post.py smoke-тест на всех green")
    print("=" * 60)
    for entry in GREEN_MANIFEST:
        test_bench_smoke(entry)
    test_etalon_floor_discipline()
    test_bench_pair_coercion_loud()

    print()
    print("=" * 60)
    print("Д106 (скептик-раунд 37): одинокие строки ** не портят air/bold")
    print("=" * 60)
    test_d106_stray_bold_line_normalization()

    print()
    print("=" * 60)
    print("Д62 (скептик-раунд 17): пер-запись валидация load_etalons()")
    print("=" * 60)
    for t in D62_TESTS:
        t()

    print()
    print("=" * 60)
    print("Д8 (раунд 3, находка 8): класс event в исполняемом слое")
    print("=" * 60)
    for t in D8_LINT_TESTS:
        t()
    for entry in EVENT_GREEN:
        test_event_green_ivan(entry)

    print()
    print("=" * 60)
    print("HOOK: post-phase-gate.sh v2.0")
    print("=" * 60)
    for t in HOOK_TESTS:
        t()

    print()
    print("=" * 60)
    print("HOOK: post-layer-checkpoint-gate.sh скоуп B (факт-база, раунд 3)")
    print("=" * 60)
    for t in PKT_HOOK_TESTS:
        t()

    print()
    print("=" * 60)
    print("ГЕЙТ СЦЕНЫ (02b1): улика происхождения, порядок фаз, пакет")
    print("=" * 60)
    for t in SCENE_TESTS:
        t()

    print()
    print("=" * 60)
    print("МЁРТВЫЕ КОНСТРУКЦИИ (анти-корпус К1-К11, владелец)")
    print("=" * 60)
    for fname in sorted(DEAD_CLASS_FIXTURES, key=lambda x: DEAD_CLASS_FIXTURES[x]):
        test_dead_class_fixture(fname)
    for entry in DEAD_OWNER_EXAMPLES:
        test_dead_owner_example(entry)
    for t in DEAD_LANG_TESTS:
        t()

    print()
    print("=" * 60)
    print("МЁРТВЫЙ ЯЗЫК: ЛЕКСИКА (антисловарь абстракций, владелец)")
    print("=" * 60)
    for fname in sorted(DEAD_LEX_FIXTURES):
        test_dead_lex_fixture(fname)
    for t in DEAD_LEX_TESTS:
        t()

    print()
    print("=" * 60)
    print("Д110 ФОРМАТ-ПОЛ + Д111 БЕЗЫМЯННЫЙ НОСИТЕЛЬ (владелец)")
    print("=" * 60)
    for t in FORM_FLOOR_TESTS:
        t()
    for t in CARRIER_TESTS:
        t()

    print()
    print("=" * 60)
    print("ЭЛЕМЕНТЫ ФОРМЫ: пол 3 / цель 6 (замер корпуса по решению автора)")
    print("=" * 60)
    for t in ELEMENT_TESTS:
        t()

    print()
    print("=" * 60)
    print("РАУНД 5: К1 расписка гейта как защищённый класс + К2 банк/дампы")
    print("=" * 60)
    for t in R5_GUARD_TESTS:
        t()

    print()
    print("=" * 60)
    print("Д4/Д5/Д6 (раунд 3): обходы стража исключений + юникод-нормализация")
    print("=" * 60)
    for t in UNICODE_TESTS:
        t()

    print()
    print("=" * 60)
    print("ГРАНИЦА ЗАПРЕТОВ ВЛАДЕЛЬЦА: категория-слово · подводка-мостик")
    print("=" * 60)
    for t in OWNER_BOUNDARY_TESTS:
        t()

    print()
    print("=" * 60)
    n_ok = sum(1 for _, ok, _ in results if ok)
    n_total = len(results)
    print(f"ИТОГ: {n_ok}/{n_total} тестов зелёных"
          + (f" · {len(skipped)} пропущено (нет входных данных)" if skipped else ""))
    if skipped:
        print("ПРОПУЩЕНЫ (не провал - отсутствует приватный корпус владельца):")
        for name, reason in skipped:
            print(f"  - {name}")
        print(f"  причина: {skipped[0][1]}")
    if n_ok != n_total:
        print("ПРОВАЛЕНЫ:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}")
                if detail:
                    print(f"    {detail}")
    print("=" * 60)

    sys.exit(0 if n_ok == n_total else 1)


if __name__ == "__main__":
    main()
