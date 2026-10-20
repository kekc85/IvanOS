#!/usr/bin/env bash
# Машинная проверка СВЕЖЕСТИ улик в живых артефактах папки задачи.
#
# Зачем: класс «протухшая улика» (число снято до последней правки артефакта, ссылка путь:строка уехала
# от вставки выше по файлу) три круга подряд переживал дисциплину в прозе. Критичный маршрут держат кодом,
# а не правилом в промпте, поэтому третье условие гейта 3 получает машинный измеритель.
#
# Что проверяет: РЕЗОЛВИМОСТЬ адреса, СОВПАДЕНИЕ счётного заявления с фактом, СВЕЖЕСТЬ по mtime и
# СОСТАВ реестра (уникальность сквозных ID плюс перенос временных меток исполнителя). Смысл текста не
# судит, разметку не судит, качество не оценивает - это не линтер и не ревью.
#
# Границы намеренные:
#   - только ЖИВЫЕ файлы в корне папки задачи. Архивы, снимки, фикстуры и поправки не трогает: правка
#     замороженного запрещена, значит у найденного там расхождения нет исполнителя и гейт стал бы вечно
#     красным. По той же причине из скана выведен вердикт под живым именем: пока он не унесён в архив,
#     он несёт улики ЗАКРЫТОГО круга, чинить которые уже некому;
#   - честная граница отсюда: свежесть вердикта ТЕКУЩЕГО круга машиной не проверяется. Это осознанно.
#     Вердикт пишется последним действием круга, все его числа контролёр снимает своими прогонами прямо
#     при написании, а сразу после круга файл замерзает архивацией. Проверять машиной артефакт, который
#     в момент прогона ещё не дописан, нечем и незачем;
#   - вырезается содержимое НЕ всякого тройного фенса, а только ПОМЕЧЕННОГО: маркер `дословный вывод`
#     обязан стоять в самой СТРОКЕ ОТКРЫТИЯ фенса (```дословный вывод). Такой фенс - цитата чужого
#     вывода, и своих заявлений в нём нет. Фенс без маркера сканируется наравне с прозой: иначе любая
#     собственная сводка, завёрнутая в тройной штрих, получала бы иммунитет наравне с выводом программы.
#     Маркер строкой ВЫШЕ открытия не считается: код смотрит только строку открытия;
#   - заявление, помеченное на своей же строке как цитата чужого протухшего числа («при факте N»,
#     «отменено», «архивная»), не перепроверяется, а печатается отдельным списком: цитата чужой ошибки
#     не является собственным заявлением.
#
# Вызов:  evidence-freshness.sh <папка задачи> [--report-into <имя файла>] [--strict-registry]
#   --report-into называет файл, который прямо сейчас переписывает вызывающий (в него вклеивается сам
#   отчёт). Этот файл исключается из скана целиком: его пересъём и есть то действие, в котором отчёт
#   появляется. Отсюда правило двух прогонов с разными флагами - оркестратор ставит флаг на реестр,
#   контролёр на свой вердикт, вместе они накрывают все живые файлы.
#   --strict-registry превращает пробелы полноты реестра (хвост ПРОШЛОГО круга, которого в реестре нет
#   ни под каким видом) из справки в расхождение. Метки ТЕКУЩЕГО круга флаг не судит вообще: их судит
#   признак поглощения (реестр новее файла работы), поэтому у исполнителя оба режима дают ноль, когда
#   состав в порядке, а у оркестратора и контролёра прогон идёт с флагом. Архивы при этом читаются
#   не на свежесть, а как источник состава: править их нельзя, но реестр правится всегда, значит у
#   такого расхождения есть законный исполнитель и вечно красным гейт не станет.
#
# Коды возврата: 0 - расхождений ноль · 1 - расхождения найдены и перечислены · 2 - ошибка вызова
# или на машине нет python3.
#
# Зависимости: python3 (весь разбор) и grep (перезапуск счётных заявлений тем же инструментом, каким
# их снимал автор). Генерик: ни одного имени, домена, кода, названия проекта или задачи.
set -uo pipefail

usage() {
  printf '%s\n' "вызов: evidence-freshness.sh <папка задачи> [--report-into <имя файла>] [--strict-registry]" >&2
}

TASK=""
REPORT_INTO=""
STRICT=""
RECHECK=""
while [ $# -gt 0 ]; do
  case "$1" in
    --strict-registry)
      STRICT="1"
      ;;
    --recheck-stands)
      RECHECK="1"
      ;;
    --report-into)
      shift
      [ $# -gt 0 ] || { printf '%s\n' "флаг --report-into без значения" >&2; usage; exit 2; }
      REPORT_INTO="$1"
      ;;
    -h|--help)
      usage
      exit 2
      ;;
    -*)
      printf '%s\n' "неизвестный флаг: $1" >&2
      usage
      exit 2
      ;;
    *)
      [ -z "$TASK" ] || { printf '%s\n' "лишний аргумент: $1" >&2; usage; exit 2; }
      TASK="$1"
      ;;
  esac
  shift
done

[ -n "$TASK" ] || { printf '%s\n' "не задана папка задачи" >&2; usage; exit 2; }
[ -d "$TASK" ] || { printf '%s\n' "папка задачи не найдена: $TASK" >&2; exit 2; }

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 &&
     "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done
if [ -z "$PY" ]; then
  printf '%s\n' "на машине не найден python3 (пробовал python3 и python), разбор делает он" >&2
  exit 2
fi

SELF_DIR=$(cd "$(dirname "$0")" && pwd)

EF_TASK="$TASK" EF_REPORT_INTO="$REPORT_INTO" EF_SELF_DIR="$SELF_DIR" EF_STRICT="$STRICT" EF_RECHECK="$RECHECK" "$PY" - <<'PY'
import glob
import os
import re
import subprocess
import sys
import time
from fnmatch import fnmatch

task = os.path.abspath(os.environ["EF_TASK"])
report_into = os.path.basename(os.environ.get("EF_REPORT_INTO") or "")
self_dir = os.environ["EF_SELF_DIR"]
SELF_PATH = os.path.join(self_dir, "evidence-freshness.sh")
strict = bool(os.environ.get("EF_STRICT"))
recheck = bool(os.environ.get("EF_RECHECK"))
home = os.path.expanduser("~")

started = time.time()

# Закрытый перечень замороженного, один на три места движка: before/**, snapshots/**, fixtures/**,
# 2-rabota-krug*.md, 3-proverka*-krug*.md, hook-progon*.md, *.note.md, 1<буква>-resheniya-krug<N>.md,
# 1k-kritika-tz*.md.
FROZEN_MASKS = ("*-krug*.md", "*.note.md", "hook-progon*.md", "1?-resheniya-*.md", "1k-kritika-tz*.md")
# Имя -> причина, почему файл не улика ДЛЯ СКАНА. Список детерминированный, без догадок по датам и
# номерам круга: поведение проверки не должно зависеть от порядка вызовов звеньев.
NOT_EVIDENCE = {
    "0-zadacha.md": "не улика, дословная постановка",
    "3-proverka.md": "вердикт круга: до архивации несёт улики закрытого круга, после архивации попадает под маску *-krug*",
    # Панельный вердикт 3-proverka-<ось>.md той же природы, что и общий вердикт, но имя оси
    # заранее не известно - поэтому запись glob-формой. Ключи со звездой разбирает ветка fnmatch
    # в отборе живых файлов ниже, точные имена там же сравниваются напрямую, как и раньше.
    "3-proverka-*.md": "панельный вердикт круга: та же природа, что у 3-proverka.md, после архивации попадает под маску *-krug*",
}

SEARCH_DIRS = [
    task,
    self_dir,
    os.path.join(home, ".claude", "agents"),
    os.path.join(home, ".claude", "hooks"),
    os.path.join(home, ".business", "processes"),
]

# Заявление, рядом с которым тут же стоит опровержение («= 8 при факте 9», «= 2, а не 3», «до правки
# = 0», «ОТМЕНЕНО ВОЛНОЙ 2»), это цитата чужого протухшего числа, а не собственное утверждение автора.
# Признак ищется В ОКНЕ вокруг самого числа, а не по всей строке: слово «протухшая» в названии класса
# дефекта не должно выключать проверку соседнего честного заявления.
CITATION_CUES = (
    "при факте", "при моём факте", "при моем факте", "а не ", "вместо ",
    "отменено", "до правки", "на момент снятия", "архивн", "устарел",
)
CITATION_WINDOW = 60

CONNECTOR = r"(?:=|даёт|дает|дал|дало|равно|равен|равна)"

TOKEN_RE = re.compile(r"`([^`\n]+)`")
ADDR_RE = re.compile(r"([~./A-Za-z0-9_\-]+\.[A-Za-z0-9]{1,6}):(\d+)(?:-(\d+))?")
ANCHOR_RE = re.compile(r"^(?P<path>[^\s#]+)#(?P<anchor>.+)$")
TZ_NAME = "1-tz.md"
STATE_RE = re.compile(r"^(mtime|version|size|sha256)\s+([^\s=]+)\s*=\s*(.+)$")
SUSP_TOKEN_RE = re.compile(r"подозрительных\s+(\d+),\s*разобрано\s+(\d+)")
PATHONLY_RE = re.compile(r"^([~./A-Za-z0-9_\-]+\.[A-Za-z0-9]{1,6})(?::\d+(?:-\d+)?)?$")
GREP_RE = re.compile(r"^grep\s+-c([EF]?)\s+'([^']*)'\s*(.*)$")
WC_RE = re.compile(r"^wc\s+-([lc])\s*(.*)$")


def stamp(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def resolve(p):
    if p.startswith("~"):
        cands = [os.path.expanduser(p)]
    elif p.startswith("/"):
        cands = [p]
    else:
        cands = [os.path.join(d, p) for d in SEARCH_DIRS]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def count_lines(path):
    return len(read_bytes(path).splitlines())


FENCE_QUOTE_MARK = "дословный вывод"


MARK_SINK = {}
SIGN_LINE = "evidence-freshness: "
def cmd_resolvable(line):
    """Строка команды годится в маркер, только если её исполняемое звено реально существует.

    Голый знак доллара признаком не считается: первый значащий токен обязан быть бинарём в PATH или
    путём к существующему файлу, а для bash, sh и python3 проверяется второй токен.
    """
    parts = line.lstrip("$ ").split()
    if not parts:
        return False
    cand = parts[0]
    if cand in ("bash", "sh", "python3", "python") and len(parts) > 1:
        cand = parts[1]
    if cand.startswith("~"):
        cand = os.path.expanduser(cand)
    if os.path.exists(cand):
        return True
    if "/" in cand:
        return False
    from shutil import which
    return which(cand) is not None


CMD_STARTS = ("$", "bash ", "cp ", "printf ", "python3 ", "env ", "stat ", "grep ", "diff ", "sed ", "ls ")


def marked_fences(path):
    """Помеченные фенсы файла: (номер строки открытия, строка открытия, список строк тела)."""
    res, body, opened, quoted = [], [], None, False
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if line.strip().startswith("```"):
                if opened is None:
                    opened, quoted, body = i, (FENCE_QUOTE_MARK in line), []
                else:
                    if quoted:
                        res.append((opened, body))
                    opened, quoted, body = None, False, []
                continue
            if opened is not None and quoted:
                body.append(line)
    return res


def defenced(path):
    """Строки файла, кроме содержимого фенсов, ПОМЕЧЕННЫХ как дословный вывод.

    Разводка по явному маркеру, а не по разметке: фенс, открытый строкой с маркером, это цитата
    прогона и не проверяется. Фенс без маркера проверяется наравне с прозой, потому что рукописная
    сводка в фенсе иначе получает иммунитет наравне с выводом программы.
    """
    out, fenced, quoted, pending_check = [], False, False, False
    bad_marks = MARK_SINK.setdefault(path, [])
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if line.strip().startswith("```"):
                if not fenced:
                    fenced, quoted = True, (FENCE_QUOTE_MARK in line)
                    pending_check = quoted
                else:
                    fenced, quoted = False, False
                continue
            if fenced and quoted and pending_check:
                pending_check = False
                first = line.strip()
                if first and not (first.startswith(SIGN_LINE) or cmd_resolvable(first)):
                    quoted = False  # маркер недействителен: ни вывод чекера, ни блок с командой
                    bad_marks.append((i, first[:60]))
            if not fenced or not quoted:
                out.append((i, line))
    return out


def run_grep(flag, pattern, path):
    args = ["grep", "-c" + flag if flag else "-c", pattern, path]
    try:
        res = subprocess.run(args, capture_output=True, text=True)
    except OSError as exc:
        return None, "не смог запустить grep: %s" % exc
    if res.returncode not in (0, 1):
        return None, "grep вернул код %d" % res.returncode
    try:
        return int(res.stdout.strip().splitlines()[0]), None
    except (ValueError, IndexError):
        return None, "не разобрал вывод grep"


# ── отбор живых файлов ─────────────────────────────────────────────────────
live, frozen = [], []
for name in sorted(os.listdir(task)):
    full = os.path.join(task, name)
    if not os.path.isfile(full) or not name.endswith(".md"):
        continue
    if name in NOT_EVIDENCE:
        frozen.append((name, NOT_EVIDENCE[name]))
        continue
    if any(fnmatch(name, m) for m in FROZEN_MASKS):
        frozen.append((name, "заморожен маской"))
        continue
    # Glob-ключи NOT_EVIDENCE разбираются ПОСЛЕ масок архива: панельный архив
    # 3-proverka-<ось>-krug<N>.md подходит под обе записи, и правильная причина у него
    # «заморожен маской», а не «вердикт круга».
    glob_reason = next((NOT_EVIDENCE[k] for k in sorted(NOT_EVIDENCE)
                        if "*" in k and fnmatch(name, k)), None)
    if glob_reason:
        frozen.append((name, glob_reason))
        continue
    if report_into and name == report_into:
        frozen.append((name, "файл отчёта, пересъём делает вызывающий"))
        continue
    live.append(name)

addr_bad, addr_susp, cnt_bad, fresh_bad, cited, skipped, susp_bad, stale_bad = [], [], [], [], [], [], [], []
stale_susp = []
susp_info = []
susp_expect = {}
per_file = {}

for name in live:
    path = os.path.join(task, name)
    art_mtime = os.path.getmtime(path)
    n_addr = n_cnt = n_cit = n_anchor = tz_note = n_state = 0
    susp_by_target = {}
    named_targets = set()

    for lineno, line in defenced(path):
        for m in TOKEN_RE.finditer(line):
            token = m.group(1).strip()

            # ── якорный класс: `путь#якорь`, буквальный поиск подстроки ───
            am = ANCHOR_RE.match(token)
            if am and not ADDR_RE.search(token):
                n_anchor += 1
                raw = am.group("path")
                anchor_text = am.group("anchor").strip()
                target = resolve(raw)
                if target is None:
                    (skipped if name == TZ_NAME else addr_bad).append(
                        "%s:%d  `%s`  путь якоря не резолвится" % (name, lineno, token))
                    continue
                named_targets.add(target)
                if anchor_text and anchor_text not in open(target, "r", encoding="utf-8", errors="replace").read():
                    addr_bad.append("%s:%d  `%s`  якорь НЕ НАЙДЕН в цели %s: ссылка указывает не на тот текст"
                                    % (name, lineno, token, target))
                continue

            # ── адресный класс ────────────────────────────────────────────
            for a in ADDR_RE.finditer(token):
                raw, start_line = a.group(1), int(a.group(2))
                n_addr += 1
                target = resolve(raw)
                if target is None:
                    # ТЗ - якорный снимок, исполнитель его не переписывает, и на нём
                    # ветка адресов даёт красный по причинам самой регулярки: класс
                    # символов латинский, поэтому кириллический путь обрезается, а
                    # «адрес:порт» разбирается как «путь:строка». Соседние ветки
                    # (якорь, состояние файла) уже уводят такой случай в «пропущено»,
                    # эта осталась строгой. Для ЛЮБОГО другого живого файла суд прежний
                    (skipped if name == TZ_NAME else addr_bad).append(
                        "%s:%d  `%s`  путь не резолвится" % (name, lineno, a.group(0)))
                    continue
                named_targets.add(target)
                total = count_lines(target)
                end_line = int(a.group(3)) if a.group(3) else start_line
                if end_line > total:
                    addr_bad.append(
                        "%s:%d  `%s`  цель найдена (%s), но в ней %d строк"
                        % (name, lineno, a.group(0), target, total)
                    )
                    continue
                in_task = os.path.abspath(target).startswith(task + os.sep)
                rel = os.path.relpath(os.path.abspath(target), task) if in_task else ""
                frozen_target = in_task and (
                    rel.split(os.sep)[0] in ("before", "snapshots", "fixtures")
                    or any(fnmatch(os.path.basename(rel), m) for m in FROZEN_MASKS)
                )
                if not frozen_target:
                    # Цель правится в ЭТОЙ ЖЕ задаче (движок), значит номер строки запрещён: нужен якорь.
                    # Единственное исключение - ТЗ: оно якорный снимок, пересъёму не подлежит, и жёсткий
                    # режим сделал бы гейт вечно красным без законного исполнителя.
                    if name == TZ_NAME:
                        tz_note += 1
                    else:
                        addr_bad.append("%s:%d  `%s`  цель вне перечня замороженного (папка задачи плюс маска "
                                        "архива, снимка, фикстуры, поправки, лога, файла решений): нужен якорь "
                                        "вида путь#якорь" % (name, lineno, a.group(0)))
                        continue
                if os.path.getmtime(target) > art_mtime:
                    key = target
                    susp_by_target[key] = susp_by_target.get(key, 0) + 1

            # ── канонические формы состояния файла: mtime, version, size, sha256 ──
            fm = STATE_RE.match(token)
            if fm:
                kind_s, raw_path, claimed_s = fm.group(1), fm.group(2), fm.group(3).strip()
                n_state += 1
                target = resolve(raw_path)
                if target is None:
                    (skipped if name == TZ_NAME else cnt_bad).append(
                        "%s:%d  `%s`  путь не резолвится, состояние не перепроверить" % (name, lineno, token))
                    continue
                if kind_s == "mtime":
                    fact_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(target)))
                elif kind_s == "size":
                    fact_s = str(os.path.getsize(target))
                elif kind_s == "sha256":
                    import hashlib
                    fact_s = hashlib.sha256(read_bytes(target)).hexdigest()
                else:
                    head = read_bytes(target).decode("utf-8", "replace").split("---")
                    m_ver = re.search(r"^version:\s*(\S+)", head[1] if len(head) > 2 else "", re.M)
                    fact_s = m_ver.group(1) if m_ver else "(frontmatter без version)"
                ok = fact_s.startswith(claimed_s) if kind_s == "sha256" else (fact_s == claimed_s)
                if not ok:
                    cnt_bad.append("%s:%d  %s %s  заявлено %s, факт %s"
                                   % (name, lineno, kind_s, raw_path, claimed_s, fact_s))
                continue

            # ── счётный класс ─────────────────────────────────────────────
            flag = pattern = None
            kind = None
            g = GREP_RE.match(token)
            w = WC_RE.match(token)
            if g:
                kind, flag, pattern, rest = "grep", g.group(1), g.group(2), g.group(3).strip()
            elif w:
                kind, flag, pattern, rest = "wc", w.group(1), None, w.group(2).strip()
            else:
                continue

            tail = line[m.end():].split("`")[0]
            num = re.search(CONNECTOR + r"\s*(\d+)", tail)
            if not num or num.start() > 30:
                continue
            claimed = int(num.group(1))

            window = (tail[:num.start()] + tail[num.end():num.end() + CITATION_WINDOW]).lower()
            if any(cue in window for cue in CITATION_CUES):
                n_cit += 1
                cited.append("%s:%d  `%s` %s %d  (строка объявляет число чужим и протухшим)"
                             % (name, lineno, token, "=", claimed))
                continue

            parts = rest.split()
            if len(parts) > 1:
                (skipped if name == TZ_NAME else cnt_bad).append(
                    "%s:%d  `%s`  несколько путей в одном заявлении, не канон: заявление нечем перепроверить"
                    % (name, lineno, token))
                continue
            if len(parts) == 1:
                raw_path = parts[0]
            else:
                raw_path = None
                for prev in TOKEN_RE.finditer(line[:m.start()]):
                    pm = PATHONLY_RE.match(prev.group(1).strip())
                    if pm:
                        raw_path = pm.group(1)
                if raw_path is None:
                    (skipped if name == TZ_NAME else cnt_bad).append(
                        "%s:%d  `%s`  путь не назван ни в заявлении, ни левее в строке: заявление нечем перепроверить"
                        % (name, lineno, token))
                    continue

            n_cnt += 1
            target = resolve(raw_path)
            if target is None:
                cnt_bad.append("%s:%d  `%s` -> %s  путь не резолвится, заявление не перепроверить"
                               % (name, lineno, token, raw_path))
                continue

            if kind == "grep":
                fact, err = run_grep(flag, pattern, target)
                if fact is None:
                    cnt_bad.append("%s:%d  `%s` -> %s  %s" % (name, lineno, token, raw_path, err))
                    continue
            else:
                data = read_bytes(target)
                fact = len(data.splitlines()) if flag == "l" else len(data)

            if fact != claimed:
                cnt_bad.append(
                    "%s:%d  %s %s  заявлено %d, факт %d  (цель %s)"
                    % (name, lineno,
                       ("grep -c%s '%s'" % (flag, pattern)) if kind == "grep" else ("wc -%s" % flag),
                       raw_path, claimed, fact, target)
                )

    # Машинный приговор ставится только там, где у строки есть ЗАКОННЫЙ ИСПОЛНИТЕЛЬ на момент
    # прогона (круг 4, запись R57). Цель ВНУТРИ папки задачи звено круга правит само, значит
    # несвежесть - его недоработка и это [РАСХОЖДЕНИЕ]. Цель ВНЕ папки задачи (страж, скилл,
    # файл памяти) живёт своей жизнью и правится в том числе соседними сессиями: требовать от
    # артефакта быть новее такой цели - значит красить круг за чужое действие. Такая строка
    # уходит в [ПОДОЗРИТЕЛЬНО], то есть в место для глаз контролёра, а не в приговор.
    # Печататься она обязана ВСЕГДА: из приговора уходит severity, а не сама строка.
    for tgt in sorted(named_targets):
        if name == TZ_NAME:
            continue
        try:
            tgt_mtime = os.path.getmtime(tgt)
        except OSError:
            continue
        if tgt_mtime <= art_mtime:
            continue
        tgt_in_task = os.path.abspath(tgt).startswith(task + os.sep)
        if tgt_in_task:
            stale_bad.append("%s: артефакт записан %s, а цель %s правилась %s, то есть ПОЗЖЕ: пересъём не был "
                             "последним действием" % (name, stamp(art_mtime), tgt, stamp(tgt_mtime)))
        else:
            stale_susp.append("%s: артефакт записан %s, а цель %s правилась %s, то есть ПОЗЖЕ. Цель лежит ВНЕ "
                              "папки задачи, её правит в том числе соседняя сессия: смотрит контролёр, машина "
                              "приговор не ставит" % (name, stamp(art_mtime), tgt, stamp(tgt_mtime)))

    for target, cnt in sorted(susp_by_target.items()):
        addr_susp.append(
            "%s: %d адрес(ов) в %s, цель правилась %s, позже самого артефакта (%s)"
            % (name, cnt, target, stamp(os.path.getmtime(target)), stamp(art_mtime))
        )

    if art_mtime > started:
        fresh_bad.append("%s  изменён %s, это ПОЗЖЕ старта пересъёма" % (name, stamp(art_mtime)))

    n_susp_lines = len(susp_by_target)
    susp_expect[name] = n_susp_lines
    per_file[name] = (n_addr, n_cnt, n_cit, art_mtime, n_anchor, n_susp_lines, tz_note)

# ── отчёт ──────────────────────────────────────────────────────────────────
out = []
out.append("evidence-freshness: %s" % task)
out.append("старт пересъёма: %s" % stamp(started))
out.append("живых файлов: %d" % len(live))
for name in live:
    a, c, ct, mt, an, ns, tz = per_file[name]
    out.append("  %-26s адресных %-4d якорных %-4d счётных %-4d цитат %-3d подозрительных строк %-3d mtime %s"
               % (name, a, an, c, ct, ns, stamp(mt)))
    if tz:
        out.append("      из них номеров строки на файлы движка: %d, для ТЗ это справка, а не расхождение" % tz)
out.append("вне скана: %d" % len(frozen))
for name, why in frozen:
    out.append("  %-26s %s" % (name, why))

out.append("")
out.append("--- АДРЕСНЫЕ УЛИКИ (путь:строка) ---")
out.append("расхождений: %d, подозрительных: %d" % (len(addr_bad), len(addr_susp)))
for row in addr_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in addr_susp:
    out.append("  [ПОДОЗРИТЕЛЬНО] %s" % row)
out.append("  подозрительное не считается расхождением: адрес резолвится, но цель могла уехать,")
out.append("  это место для глаз контролёра, а не машинный приговор")

out.append("")
out.append("--- СЧЁТНЫЕ УЛИКИ (grep -c, wc) ---")
out.append("расхождений: %d, цитат пропущено: %d, вне канона пропущено: %d"
           % (len(cnt_bad), len(cited), len(skipped)))
for row in cnt_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in cited:
    out.append("  [ЦИТАТА] %s" % row)
for row in skipped:
    out.append("  [ВНЕ КАНОНА] %s" % row)

# Токены разбора живут в матрице свежести, а она лежит у ПОСЛЕДНЕГО ПИСАТЕЛЯ круга (круг 4,
# запись R57). Раньше токен искался только в файле работы, и когда подозрительных строк
# становилось больше уже ПОСЛЕ того, как исполнитель закрыл свой файл, законного писателя у
# растущей популяции не оставалось: контролёр разбирал строки поимённо, а прогон всё равно
# краснел. То же правило класса, что и в ветке пересъёма выше: машинный приговор ставится
# только там, где у строки есть законный исполнитель на момент прогона.
# Теперь токен берётся из носителя круга с самым поздним mtime среди тех, что его несут:
# файл работы, вердикт контролёра, реестр оркестратора. Файлы, выведенные из скана флагом
# --report-into и правилом NOT_EVIDENCE, тоже читаются - они и так читаются ради сквозных ID.
# Панельный вердикт 3-proverka-<ось>.md несёт токен разбора наравне с общим вердиктом, а имя оси
# заранее не известно - поэтому носители перечислены и точным именем, и glob-формой. Точное имя
# резолвится прямым isfile, glob - перебором содержимого папки (ветка fnmatch, как в отборе живых
# файлов выше). Архивы под масками заморозки в носители не берутся: писателя текущего круга в них нет.
TOKEN_CARRIERS = ("2-rabota.md", "3-proverka.md", "3-proverka-*.md", "5-reestr.md")
task_names = sorted(os.listdir(task)) if os.path.isdir(task) else []
carriers = []
for n in TOKEN_CARRIERS:
    if "*" in n:
        carriers += [os.path.join(task, f) for f in task_names
                     if fnmatch(f, n)
                     and not any(fnmatch(f, m) for m in FROZEN_MASKS)
                     and os.path.isfile(os.path.join(task, f))]
    elif os.path.isfile(os.path.join(task, n)):
        carriers.append(os.path.join(task, n))
carriers = sorted(set(carriers))
carriers_with_token = [p for p in carriers
                       if any(SUSP_TOKEN_RE.search(l) for _, l in defenced(p))]
work_path_t = max(carriers_with_token, key=os.path.getmtime) if carriers_with_token else (
    os.path.join(task, "2-rabota.md"))
if carriers_with_token:
    susp_info.append("токен разбора взят у последнего писателя круга: %s (mtime %s). Носителей с "
                     "токеном: %s" % (os.path.basename(work_path_t), stamp(os.path.getmtime(work_path_t)),
                                      ", ".join(sorted(os.path.basename(p) for p in carriers_with_token))))
if os.path.isfile(work_path_t):
    wtext = [l for _, l in defenced(work_path_t)]
    for aname, n_exp in sorted(susp_expect.items()):
        rows_with = [l for l in wtext if aname in l and SUSP_TOKEN_RE.search(l)]
        if not rows_with:
            susp_bad.append("%s: подозрительных строк %d, а строки матрицы с токеном «подозрительных <N>, "
                            "разобрано <M>» в файле работы нет" % (aname, n_exp))
            continue
        m = SUSP_TOKEN_RE.search(rows_with[0])
        cn, cm = int(m.group(1)), int(m.group(2))
        if cn != n_exp:
            susp_bad.append("%s: в матрице заявлено подозрительных %d, факт %d" % (aname, cn, n_exp))
        elif cm < cn:
            susp_bad.append("%s: подозрительных %d, разобрано только %d" % (aname, cn, cm))
        elif cn > 0 and "машинно" in rows_with[0]:
            susp_bad.append("%s: метка «машинно» стоит при %d подозрительных строках, она разрешена только при нуле"
                            % (aname, cn))
elif os.path.isfile(os.path.join(task, "5-reestr.md")):
    # Реестр на месте, значит это папка задачи в работе, и отсутствие файла работы там дефект.
    susp_bad.append("файла работы нет, разбор подозрительных проверить не по чему")
else:
    # Ни файла работы, ни реестра: это половина стенда, а не папка круга. Справка, а не расхождение.
    susp_info.append("ни файла работы, ни реестра: папка не является папкой круга, разбор подозрительных пропущен")

# ── вклейка: самодатирование, сверка с прозой, перечень увиденного ─────────
paste_bad, paste_info, seen_tokens = [], [], []
MT_LINE = re.compile(r"^\s{2,}(\S+\.md)\s+.*mtime\s+(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*$")
ITOG_RE = re.compile(r"ИТОГ: расхождений (\d+)")
EXIT_RE = re.compile(r"^exit=(\d+)")
REPORT_RE = re.compile(r"--report-into\s+(\S+)")

for name in live:
    path = os.path.join(task, name)
    art_mtime = os.path.getmtime(path)
    for bad_line, first in MARK_SINK.get(path, []):
        paste_bad.append("%s:%d  маркер дословности недействителен: первая строка «%s» не сигнатура отчёта "
                         "и не исполненная команда" % (name, bad_line, first))
    prose_zero = any("расхождений 0" in l or "расхождений: 0" in l for _, l in defenced(path))
    for open_line, body in marked_fences(path):
        head = body[0].strip() if body else ""
        if not head.startswith(SIGN_LINE):
            continue
        # Освобождение строго одно и равно значению --report-into: правку носителя после прогона
        # ловит прогон соседней роли, у которой флаг стоит на её собственном файле.
        exempt = {report_into} if report_into else set()
        for l in body:
            m_rep = REPORT_RE.search(l)
            if m_rep:
                exempt.add(os.path.basename(m_rep.group(1)))
        for l in body:
            m = MT_LINE.match(l)
            if not m:
                continue
            fname, printed = m.group(1), m.group(2)
            if fname in exempt:
                continue
            target = os.path.join(task, fname)
            if not os.path.isfile(target):
                continue
            tgt_mt = os.path.getmtime(target)
            fact = stamp(tgt_mt)
            if fact == printed:
                continue
            # Разводим два случая. Цель изменилась ПОЗЖЕ последней правки носителя - вклейка просто
            # состарилась, её обновит владелец носителя своим прогоном, и это справка. Цель была новее
            # уже в момент вклейки - значит прогон снят не последним действием, и это расхождение.
            if tgt_mt > art_mtime:
                paste_info.append("%s:%d  вклейка состарилась: %s изменился %s, уже после последней правки "
                                  "носителя (%s). Обновит владелец носителя своим прогоном"
                                  % (name, open_line, fname, fact, stamp(art_mtime)))
            else:
                paste_bad.append("%s:%d  вклейка печатает mtime %s = %s, а факт %s: прогон снят не последним "
                                 "действием" % (name, open_line, fname, printed, fact))
        for l in body:
            mi = ITOG_RE.search(l)
            me = EXIT_RE.match(l.strip())
            if (mi and int(mi.group(1)) > 0) or (me and int(me.group(1)) > 0):
                if prose_zero:
                    paste_bad.append("%s:%d  вклейка кончается ненулевым итогом («%s»), а проза того же файла "
                                     "заявляет ноль расхождений" % (name, open_line, l.strip()))
                break
    for _, l in defenced(path):
        for tok in re.findall(r"(подозрительных \d+, разобрано \d+|предметов \d+, закрыто \d+)", l):
            seen_tokens.append("%s: %s" % (name, tok))

# ── обязательные разделы живых файлов по таблице ТЗ ────────────────────────
# ПЕРЕЧЕНЬ КРИТЕРИЕВ читается из таблицы «Реестр критериев, судящих живой артефакт по имени» в 1-tz.md,
# поэтому новый критерий с новой строкой начинает проверяться сам собой. Заучен в коде не перечень, а
# ПОДСКАЗКИ к нему: словарь PROBES ниже переводит формулировку строки в машинный признак присутствия
# для тех строк, где автор ТЗ не дал ни одного токена в обратных кавычках. Порядок разбора строки:
# сначала дословные токены в обратных кавычках, затем подсказка из PROBES по ключевому слову, и только
# потом самые длинные слова формулировки. Нет таблицы в ТЗ - раздел печатает «строк таблицы прочитано: 0»
# и расхождений не даёт: судить нечего, а не «всё в порядке».
sect_bad, sect_info, sect_rows = [], [], 0
PROBES = [
    ("фикстур", ["fixtures/"]),
    ("ripple", ["ripple"]),
    ("Хвосты круга", ["## Хвосты круга"]),
    ("обязательного прогона", ["evidence-freshness: "]),
    ("противопоставления на срезе", ["snapshots/", "срез"]),
    ("матрица свежести", ["атрица свежести"]),
    ("без `sort`", ["sort"]),
    ("ОТКЛОНЕНО", ["ОТКЛОНЕНО"]),
    ("якорная адресация", ["#"]),
    ("подозрительных", ["подозрительных"]),
    ("матрица класса", ["атрица класса"]),
    ("стенды", ["стенд"]),
    ("предметов", ["предметов"]),
]
tz_path = os.path.join(task, TZ_NAME)
if os.path.isfile(tz_path):
    inside = False
    for _, line in defenced(tz_path):
        s = line.strip()
        if s.startswith("## "):
            inside = s.startswith("## Реестр критериев, судящих живой артефакт по имени")
            continue
        if not inside or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or cells[0].startswith("Критерий") or set(cells[0]) <= set("-: "):
            continue
        sect_rows += 1
        files = re.findall(r"`([^`]+\.md)`", cells[1])
        need = cells[2]
        # Признак берётся из САМОЙ таблицы: сначала дословные токены в обратных кавычках, затем
        # значимые слова формулировки. Хардкод остаётся лишь подсказкой для строк без токенов.
        probes = re.findall(r"`([^`]+)`", need)
        for key, vals in PROBES:
            if key.lower() in need.lower():
                probes.extend(vals)
        if not probes:
            # Берём САМЫЕ ДЛИННЫЕ слова формулировки: короткие общие («раздел», «строка») есть почти
            # в любом файле и дают ложное совпадение, то есть тихий пропуск под видом присутствия.
            words = sorted(re.findall(r"[A-Za-zА-Яа-яЁё]{6,}", need), key=len, reverse=True)
            probes = words[:2]
        if not probes:
            sect_info.append("строка таблицы «%s» не даёт машинного признака присутствия" % need[:50])
            continue
        for fname in files:
            fpath = os.path.join(task, fname)
            if not os.path.isfile(fpath):
                sect_bad.append("%s: файла нет, а критерий %s судит его по имени" % (fname, cells[0]))
                continue
            body = open(fpath, "r", encoding="utf-8", errors="replace").read()
            low_body = body.lower()
            if not any(pr.lower() in low_body for pr in probes):
                # Тот же признак поглощения, что и в проверке меток: реестр наполняет оркестратор ПОСЛЕ
                # звена. Реестр старше файла работы - его вклейка этого круга ещё впереди, это справка.
                # Реестр новее - момент его хода уже прошёл, и пропуск раздела становится расхождением.
                work_p = os.path.join(task, "2-rabota.md")
                pending = (fname == "5-reestr.md" and os.path.isfile(work_p)
                           and os.path.getmtime(fpath) < os.path.getmtime(work_p))
                (sect_info if pending else sect_bad).append(
                    "%s: критерий %s требует «%s», в файле этого нет%s"
                    % (fname, cells[0], need[:60], " (ход владельца ещё впереди)" if pending else ""))

out.append("")
out.append("--- ОБЯЗАТЕЛЬНЫЕ РАЗДЕЛЫ ЖИВЫХ ФАЙЛОВ (таблица ТЗ) ---")
out.append("строк таблицы прочитано: %d, расхождений: %d" % (sect_rows, len(sect_bad)))
for row in sect_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in sect_info:
    out.append("  [СПРАВКА] %s" % row)

# ── режим перепроверки стендов: перезапуск команды из первой строки фенса ───
stand_bad, stand_info = [], []
if recheck:
    for name in live:
        path = os.path.join(task, name)
        for open_line, body in marked_fences(path):
            if not body:
                continue
            head = body[0].strip()
            cmd = head.lstrip("$ ").strip()
            if head.startswith(SIGN_LINE):
                # Вклейка собственного отчёта: команда в фенсе не напечатана, но восстанавливается из
                # него самого - путь папки стоит в сигнатурной строке, флаг в строке «вне скана».
                task_arg = head[len(SIGN_LINE):].strip()
                rep = ""
                for l in body:
                    if "файл отчёта" in l:
                        rep = l.strip().split()[0]
                        break
                cmd = "bash %s %s%s" % (SELF_PATH, task_arg, (" --report-into " + rep) if rep else "")
            if "evidence-freshness.sh" not in cmd or "<" in cmd:
                stand_info.append("%s:%d  фенс не перезапускается: первая строка не команда чекера и не его отчёт"
                                  % (name, open_line))
                continue
            claimed, claimed_exit = None, None
            for l in body:
                m = ITOG_RE.search(l)
                if m:
                    claimed = int(m.group(1))
                me = EXIT_RE.match(l.strip())
                if me:
                    claimed_exit = int(me.group(1))
            if claimed is None and claimed_exit is None:
                stand_info.append("%s:%d  в фенсе нет ни строки ИТОГ, ни строки exit: сверять перезапуску нечего"
                                  % (name, open_line))
                continue
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            except OSError as exc:
                stand_bad.append("%s:%d  команду стенда не удалось перезапустить: %s" % (name, open_line, exc))
                continue
            if claimed is None:
                if res.returncode != claimed_exit:
                    stand_bad.append("%s:%d  стенд заявляет exit=%d, перезапуск даёт %d"
                                     % (name, open_line, claimed_exit, res.returncode))
                continue
            got = ITOG_RE.findall(res.stdout)
            if not got:
                stand_bad.append("%s:%d  перезапуск команды стенда не дал строки ИТОГ" % (name, open_line))
            elif int(got[-1]) != claimed:
                stand_bad.append("%s:%d  стенд заявляет ИТОГ %d, перезапуск даёт %d"
                                 % (name, open_line, claimed, int(got[-1])))

out.append("")
out.append("--- ПЕРЕПРОВЕРКА СТЕНДОВ (перезапуск команды из фенса) ---")
out.append("режим: %s, расхождений: %d" % ("включён" if recheck else "выключен, нужен флаг --recheck-stands", len(stand_bad)))
for row in stand_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in stand_info:
    out.append("  [СПРАВКА] %s" % row)

out.append("")
out.append("--- ВКЛЕЙКА И ПЕРЕЧЕНЬ УВИДЕННОГО ---")
out.append("расхождений: %d" % len(paste_bad))
for row in paste_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in paste_info:
    out.append("  [СПРАВКА] %s" % row)
out.append("  токенов увидено: %d" % len(seen_tokens))
for row in seen_tokens:
    out.append("    %s" % row)

out.append("")
out.append("--- ПЕРЕСЪЁМ: АРТЕФАКТ ПРОТИВ ЦЕЛЕЙ, КОТОРЫЕ ОН НАЗЫВАЕТ ---")
out.append("расхождений: %d, подозрительных: %d" % (len(stale_bad), len(stale_susp)))
for row in stale_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in stale_susp:
    out.append("  [ПОДОЗРИТЕЛЬНО] %s" % row)
out.append("  правило: живой артефакт с обязанностью пересъёма обязан быть НОВЕЕ каждой цели,")
out.append("  которую он называет и которую САМ МОЖЕТ ПРАВИТЬ, то есть цели внутри папки задачи.")
out.append("  Цель вне папки задачи правится и соседними сессиями, поэтому она подозрительна, а не")
out.append("  приговорна: её смотрит контролёр. ТЗ из правила исключено как якорный снимок")

out.append("")
out.append("--- РАЗБОР ПОДОЗРИТЕЛЬНЫХ (токен «подозрительных N, разобрано M») ---")
out.append("расхождений: %d" % len(susp_bad))
for row in susp_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
for row in susp_info:
    out.append("  [СПРАВКА] %s" % row)
out.append("  правило: на каждый живой артефакт с подозрительными строками в нём самом стоит токен,")
out.append("  N сверяется с числом выше, M меньше N не принимается")

out.append("")
out.append("--- СВЕЖЕСТЬ (mtime против старта) ---")
out.append("расхождений: %d" % len(fresh_bad))
for row in fresh_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)

# ── реестр и сквозные ID ───────────────────────────────────────────────────
# Свежесть отвечает на вопрос «числа не врут», этот блок на вопрос «состав полон и ID не двоятся».
# Пропущенная строка улики не имеет и потому невидима для двух секций выше.
REGISTRY_NAME = "5-reestr.md"
WORK_NAME = "2-rabota.md"
ID_RE = re.compile(r"^R\d+$")
LABEL_RE = re.compile(r"^T\d+$")
id_bad, id_info = [], []


def row_heads(path):
    """Первая ячейка каждой строки таблицы вне фенсов: (номер строки, текст ячейки)."""
    res = []
    for lineno, line in defenced(path):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cell = s.strip("|").split("|")[0].strip().strip("*").strip("`").strip()
        res.append((lineno, cell))
    return res


reg_path = os.path.join(task, REGISTRY_NAME)
work_path = os.path.join(task, WORK_NAME)

if os.path.isfile(reg_path):
    seen = {}
    for lineno, cell in row_heads(reg_path):
        if ID_RE.match(cell):
            seen.setdefault(cell, []).append(lineno)
    dups = sorted((k, v) for k, v in seen.items() if len(v) > 1)
    for k, lines in dups:
        id_bad.append("%s: ID %s стоит первой ячейкой %d раз (строки %s), сквозной ID обязан быть один"
                      % (REGISTRY_NAME, k, len(lines), ", ".join(str(x) for x in lines)))
    id_info.append("%s: сквозных ID строками таблицы %d, повторов %d (файл читается даже когда исключён из скана)"
                   % (REGISTRY_NAME, len(seen), len(dups)))
else:
    id_info.append("%s: файла нет, проверка состава пропущена" % REGISTRY_NAME)

if os.path.isfile(work_path):
    labels, r_heads = [], []
    for lineno, cell in row_heads(work_path):
        if LABEL_RE.match(cell):
            labels.append((lineno, cell))
        elif ID_RE.match(cell):
            r_heads.append((lineno, cell))
    for lineno, cell in r_heads:
        id_bad.append("%s:%d  строка таблицы открыта сквозным ID %s: финальные ID выдаёт только оркестратор, "
                      "звено ставит временную метку вида T<N>" % (WORK_NAME, lineno, cell))
    id_info.append("%s: временных меток %d, сквозных ID первой ячейкой %d" % (WORK_NAME, len(labels), len(r_heads)))
    if labels and os.path.isfile(reg_path):
        reg_text = open(reg_path, "r", encoding="utf-8", errors="replace").read()
        missing = [c for _, c in labels if c not in reg_text]
        absorbed = os.path.getmtime(reg_path) > os.path.getmtime(work_path)
        if missing and absorbed:
            id_bad.append("%s: поглощение состоялось (реестр новее работы), но меток %s в реестре нет: хвост потерян"
                          % (REGISTRY_NAME, ", ".join(missing)))
        elif missing:
            id_info.append("%s: меток без записи в реестре %d, поглощение текущего круга ещё не состоялось "
                           "(реестр старше файла работы). Это не расхождение ни в одном режиме: судит признак "
                           "поглощения, а не флаг" % (REGISTRY_NAME, len(missing)))

        else:
            id_info.append("%s: токены всех временных меток работы в тексте реестра встречаются. Точность ограничена: метки повторяются из круга в круг, поимённую сверку делает оркестратор по колонке «Источник», где стоит пара метка-ID" % REGISTRY_NAME)
else:
    id_info.append("%s: файла нет, проверка меток пропущена" % WORK_NAME)

# Полнота по хвостам ПРОШЛЫХ кругов: архивы не проверяются на свежесть (править их нельзя), но реестр
# обязан их содержать, а вот он правится всегда. Поэтому пробел полноты имеет законного исполнителя и
# вечно красным гейт не делает. Считается он только под флагом --strict-registry: у исполнителя прогон
# идёт до поглощения, и красный цвет в его момент ничего не значит.
gaps = []
if os.path.isfile(reg_path):
    reg_text_full = open(reg_path, "r", encoding="utf-8", errors="replace").read()
    tail_re = re.compile(r"^(R\d+(?:-[a-zA-Z])?|T\d+)$")
    for arch in sorted(glob.glob(os.path.join(task, "2-rabota-krug*.md"))):
        if arch.endswith(".note.md"):
            continue
        inside = False
        for lineno, line in defenced(arch):
            s = line.strip()
            if s.startswith("## "):
                inside = s.startswith("## Хвосты круга")
                continue
            if not inside or not s.startswith("|"):
                continue
            head = s.strip("|").split("|")[0].strip().strip("*").strip("`").strip()
            if not tail_re.match(head):
                continue
            if head not in reg_text_full:
                gaps.append("%s:%d  хвост %s в реестре не найден ни под каким видом"
                            % (os.path.basename(arch), lineno, head))
if gaps and strict:
    id_bad.extend(gaps)

# Второй обязательный источник реестра, который считается СТРОКАМИ, а не таблицей: отклонения аналитика.
# Точное сопоставление формулировок машине не по силам (реестр переписывает их своими словами, а дубли
# между файлами сводятся в одну запись), поэтому здесь только СИГНАЛ числами и всегда справкой: красить
# им гейт нельзя, законная разница существует.
decl_src = 0
for cand in sorted(glob.glob(os.path.join(task, "1*.md"))):
    inside = False
    for _, line in defenced(cand):
        s = line.strip()
        if s.startswith("## "):
            inside = s.startswith("## Отклонено по целесообразности")
            continue
        if inside and s.startswith("- "):
            decl_src += 1
if os.path.isfile(reg_path):
    reg_rows = 0
    for _, line in defenced(reg_path):
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) > 4 and cells[4] == "ОТКЛОНЕНО":
                reg_rows += 1
    id_info.append("отклонения аналитика: строк в его файлах %d, записей ОТКЛОНЕНО в реестре %d, разница %d "
                   "(часть разницы может быть сведёнными дублями, проверять поимённо)"
                   % (decl_src, reg_rows, decl_src - reg_rows))

out.append("")
out.append("--- РЕЕСТР И СКВОЗНЫЕ ID ---")
out.append("расхождений: %d, пробелов полноты: %d, строгий режим: %s"
           % (len(id_bad), len(gaps), "да" if strict else "нет"))
for row in id_bad:
    out.append("  [РАСХОЖДЕНИЕ] %s" % row)
if not strict:
    for row in gaps:
        out.append("  [ПРОБЕЛ ПОЛНОТЫ] %s" % row)
for row in id_info:
    out.append("  [ИНФО] %s" % row)
if gaps and not strict:
    out.append("  пробел полноты не входит в счёт без флага --strict-registry: до поглощения он ничего")
    out.append("  не означает. С флагом эти же строки становятся расхождениями")

total = (len(addr_bad) + len(cnt_bad) + len(fresh_bad) + len(id_bad) + len(susp_bad) + len(stale_bad)
         + len(paste_bad) + len(sect_bad) + len(stand_bad))
out.append("")
out.append("ИТОГ: расхождений %d" % total)

sys.stdout.write("\n".join(out) + "\n")
sys.exit(1 if total else 0)
PY
