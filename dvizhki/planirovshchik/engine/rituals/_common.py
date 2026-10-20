#!/usr/bin/env python3
"""Общие утилиты машинных ритуалов планировщика (daily_open/daily_close/wam/watchdog/decide).

Только stdlib. Ничего не падает при отсутствии файлов данных - функции
возвращают явную ошибку вторым элементом кортежа, вызывающий код сам решает,
как об этом сообщить.

Три вещи, которые живут здесь и держат всю конструкцию:

1. СЛЕД ЧЕЛОВЕКА (pulse). Прошлая система умерла потому, что предохранитель
   питался от датчика, который отключается первым: сторож мерил свежесть файла,
   а файл трогала сама машина. Здесь машина ПОСЛЕ каждой своей записи снимает
   отпечаток данных (note_machine_write). Любое расхождение отпечатка с реальным
   файлом = работа не машины, то есть человека. Только оно двигает lastHumanAt.

2. ДОСТАВКА ТРЕВОГИ (notify). Крик в файл, который никто не открывает, тревогой
   не является. Канал по умолчанию - системное уведомление macOS через osascript,
   при затяжной тревоге - модальное окно. В песочнице (PLANNER_TEST_ROOT) реальных
   окон не показываем, пишем в state/notifications.log, чтобы доставка была
   проверяема тестом.

3. ЗАЩИТА ДАННЫХ. Атомарная запись + бэкап + ротация бэкапов.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

# PLANNER_TEST_ROOT переключает все пути в песочницу для ручных тестов ритуалов
# (например daily_close.py, который мутирует sprint.json) - чтобы не портить
# боевые данные владельца посреди дня. По умолчанию не задан - работаем с боевыми путями.
_test_root = os.environ.get("PLANNER_TEST_ROOT")
IS_SANDBOX = bool(_test_root)
ROOT = Path(_test_root) if _test_root else Path.home() / "work"
TASKS_DIR = ROOT / "tasks"
PLANNER_JSON = TASKS_DIR / "sprint.json"
PROFILE_JSON = TASKS_DIR / "profile.json"
TRACKER_JSON = TASKS_DIR / "tracker.json"
GOALS_CYCLE_JSON = TASKS_DIR / "goals-cycle.json"
DAYS_JSON = TASKS_DIR / "days.json"
DAILY_DIR = TASKS_DIR / "daily"
REVIEWS_DIR = TASKS_DIR / "reviews"
ALERT_FILE = TASKS_DIR / "ALERT.md"
PLANNER_DIR = ROOT / "sprint"
BACKUPS_DIR = PLANNER_DIR / "backups"
STATE_DIR = PLANNER_DIR / "state"
PULSE_JSON = STATE_DIR / "pulse.json"
NOTIFY_LOG = STATE_DIR / "notifications.log"

# Сколько дней журнала закрытых дней держится ГОРЯЧИМИ в pulse.json. Вытесненные
# записи не пропадают: `record_day_closed` уносит их в датированный файл
# `state/pulse-arhiv-<дата>.json` рядом и только потом убирает из горячего
# документа. Ноль отключает вытеснение целиком - тот же выключатель константой,
# что стоит у BACKUP_KEEP_DAYS в server.py
PULSE_KEEP_DAYS = 120

# ---------------------------------------------------------------------------
# ЕДИНЫЙ ГАРД ПЕСОЧНИЦЫ ДЛЯ ВСЕХ, КТО ПИШЕТ ДАННЫЕ
#
# Прецедент, ради которого гард стоит здесь, а не заплаткой в одной ветке.
# Инструменты писали отметки через HTTP-API движка и брали адрес из PLANNER_PORT
# со значением по умолчанию 8777. Про PLANNER_TEST_ROOT они не знали вовсе:
# переменная песочницы принималась и МОЛЧА игнорировалась. Дословная команда
# критерия, запущенная контролёром «в песочнице», записала день в БОЕВОЙ трекер
# владельца. Это ровно «мягкая деградация как молча выключенный барьер»: барьер,
# который при отсутствии своей зависимости едет дальше с кодом 0, выключен.
#
# Правило теперь такое. Задан PLANNER_TEST_ROOT - инструмент ОБЯЗАН писать в
# песочный движок, и он это ДОКАЗЫВАЕТ, а не предполагает: спрашивает у сервера
# по адресу назначения, с какой папкой данных тот работает (GET /api/where), и
# сверяет её со своим TASKS_DIR. Не сошлось или сервер молчит - инструмент
# ОТКАЗЫВАЕТСЯ писать с явной ошибкой. Проверка идёт по СОДЕРЖАНИЮ ответа, а не
# по совпадению номера порта: порт можно задать любой, а данные за ним чужие.
PROD_PORT = "8777"

# ресурс движка -> файл данных. Один источник истины для всех инструментов
RESOURCE_FILES = {
    "track": TRACKER_JSON,
    "data": PLANNER_JSON,
    "goals": GOALS_CYCLE_JSON,
    "profile": PROFILE_JSON,
    "days": DAYS_JSON,
}


class SandboxMismatch(RuntimeError):
    """Песочный корень задан, а запись идёт мимо песочницы."""


def api_port():
    """Порт движка, к которому обращается инструмент."""
    return os.environ.get("PLANNER_PORT") or PROD_PORT


def api_url(resource):
    """Полный URL ресурса движка: http://127.0.0.1:<порт>/api/<ресурс>."""
    return "http://127.0.0.1:%s/api/%s" % (api_port(), resource)


def _server_tasks_dir(timeout=4):
    """Куда пишет сервер по адресу назначения. None - сервер не отвечает."""
    import json as _json
    import urllib.request as _rq
    import urllib.error as _err
    try:
        with _rq.urlopen("http://127.0.0.1:%s/api/where" % api_port(), timeout=timeout) as r:
            return _json.loads(r.read().decode()).get("tasks")
    except (_err.URLError, OSError, ValueError):
        return None


def assert_write_target(resource, quiet=False):
    """Гард перед ЛЮБОЙ записью данных инструментом.

    Возвращает ("api", url) либо ("file", путь) и печатает первой строкой, куда
    именно пойдёт запись: полный URL и полный путь файла. Оператору больше не
    нужно держать согласованность порта и корня в голове - несогласованность
    видно ДО записи, а не по её следам в боевом файле.

    Три исхода в песочнице:
      порт не задан        -> пишем ПРЯМО в песочный файл, сервер не нужен;
      порт задан и песочный -> пишем через его API (оптимистичная блокировка цела);
      порт задан и чужой    -> SandboxMismatch, запись остановлена.
    """
    path = RESOURCE_FILES.get(resource)
    if path is None:
        raise SandboxMismatch("неизвестный ресурс движка: %r" % (resource,))
    url = api_url(resource)
    port_given = bool(os.environ.get("PLANNER_PORT"))
    mine = os.path.realpath(str(TASKS_DIR))
    if IS_SANDBOX:
        if not port_given:
            if not quiet:
                print("пишу в: файл песочницы %s (сервер не задан, PLANNER_PORT пуст)" % path)
            return ("file", str(path))
        served = _server_tasks_dir()
        if served is None:
            raise SandboxMismatch(
                "песочный корень задан (%s), а движок на %s не отвечает на /api/where: доказать, что "
                "запись идёт в песочницу, нечем. Подними песочный сервер или сними PLANNER_PORT."
                % (ROOT, url))
        if os.path.realpath(served) != mine:
            raise SandboxMismatch(
                "песочный корень задан, а порт боевой: движок на %s пишет в %s, а песочные данные "
                "лежат в %s. Запись остановлена." % (url, served, mine))
        if not quiet:
            print("пишу в: %s -> %s" % (url, served))
        return ("api", url)
    if not quiet:
        print("пишу в: %s -> %s" % (url, _server_tasks_dir() or mine))
    return ("api", url)


def read_resource(resource):
    """(документ, etag). etag=None означает файловый режим записи.

    Читает ровно из того носителя, куда потом и запишет: иначе инструмент читает
    один документ, а пишет в другой, и расхождение вылезает молча.
    """
    import json as _json
    import urllib.request as _rq
    import urllib.error as _err
    mode, dest = assert_write_target(resource, quiet=True)
    if mode == "api":
        try:
            with _rq.urlopen(dest, timeout=6) as r:
                return _json.loads(r.read().decode()), r.headers.get("ETag")
        except (_err.URLError, OSError):
            pass                       # сервер молчит - падаем в файл того же корня
    return _json.loads(RESOURCE_FILES[resource].read_text(encoding="utf-8")), None


def write_resource(resource, doc, etag, quiet=False):
    """Запись документа тем же путём, который назвал гард. Возвращает строку-улику."""
    import json as _json
    import urllib.request as _rq
    import urllib.error as _err
    mode, dest = assert_write_target(resource, quiet=quiet)
    doc = dict(doc)
    doc.pop("rev", None)
    body = _json.dumps(doc, ensure_ascii=False).encode()
    if mode == "api" and etag is not None:
        req = _rq.Request(dest, data=body, method="POST",
                          headers={"Content-Type": "application/json", "If-Match": etag})
        try:
            with _rq.urlopen(req, timeout=10) as r:
                return "api rev:%s" % _json.loads(r.read().decode()).get("rev")
        except _err.HTTPError as exc:
            raise SandboxMismatch("движок отклонил запись: %s %s"
                                  % (exc.code, exc.read().decode()[:200]))
    if mode == "api" and etag is None:
        raise SandboxMismatch("движок на %s не отвечает, а прямая запись в боевой файл запрещена: "
                              "оптимистичную блокировку сервера в обход не идём" % dest)
    # файловый режим песочницы: бэкап рядом с датой в имени, потом атомарная замена
    path = Path(dest)
    ensure_dir(path.parent)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(str(path), "%s.bak-%s" % (path, stamp))
    atomic_write_text(path, _json.dumps(doc, ensure_ascii=False, indent=1))
    return "файл песочницы %s (бэкап снят)" % path


BACKUP_KEEP = 40  # столько бэкапов sprint.json держим, остальные подрезаем

PROFILE_DEFAULTS = {
    "wake": "08:00",
    "sleep": "00:00",
    "workStart": "10:00",
    "workEnd": "22:00",
    "peakFrom": "10:00",
    "peakTo": "14:00",
    "training": {"days": [], "start": "09:00", "dur": 60},
    "windDown": "22:30",
    "protectedDays": ["sun"],
    "capacityPercent": 60,
    "deepBlockMin": 90,
    "breakMin": 15,
}

WEEKDAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Файлы данных, по которым меряется след человека.
# days.json - ручное закрытие дня из интерфейса (tab-plan.js): единственная запись
# в этот файл делает человек, машина его не пишет никогда - значит любое расхождение
# отпечатка здесь ЖЕЛЕЗНО след человека, датчик sync_pulse() ловит это как обычно.
DATA_FILES = {
    "sprint.json": PLANNER_JSON,
    "profile.json": PROFILE_JSON,
    "tracker.json": TRACKER_JSON,
    "goals-cycle.json": GOALS_CYCLE_JSON,
    "days.json": DAYS_JSON,
}


# --------------------------------------------------------------------------
# Время
# --------------------------------------------------------------------------

def now() -> datetime:
    """Текущий момент. Оверрайды для тестов: PLANNER_NOW=YYYY-MM-DDTHH:MM:SS,
    PLANNER_TODAY=YYYY-MM-DD (фиксирует только дату)."""
    override_now = os.environ.get("PLANNER_NOW")
    override_day = os.environ.get("PLANNER_TODAY")
    if override_now:
        dt = datetime.fromisoformat(override_now)
        if override_day:
            dt = datetime.combine(date.fromisoformat(override_day), dt.time())
        return dt
    if override_day:
        return datetime.combine(date.fromisoformat(override_day), datetime.now().time())
    return datetime.now()


def today() -> date:
    """Текущая дата. Ручной override для тестов: PLANNER_TODAY=YYYY-MM-DD."""
    override = os.environ.get("PLANNER_TODAY")
    if override:
        return date.fromisoformat(override)
    return now().date()


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------
# Чтение и запись
# --------------------------------------------------------------------------

def load_json(path: Path):
    """Возвращает (data, error). error is None при успехе, иначе текст диагноза."""
    if not path.exists():
        return None, f"файл не найден: {path}"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except (json.JSONDecodeError, OSError) as e:
        return None, f"не удалось прочитать {path}: {e}"


def load_profile() -> dict:
    """profile.json с дефолтами поверх отсутствующих/недостающих полей."""
    data, _err = load_json(PROFILE_JSON)
    profile = dict(PROFILE_DEFAULTS)
    if isinstance(data, dict):
        profile.update(data)
    return profile


def load_days() -> dict:
    """days.json: карта dateStr -> {planned, plannedAt, big3, obstacles, closedAt,
    reflection} - журнал ручного закрытия дня, который пишет фронт (tab-plan.js,
    POST /api/days). Отсутствие файла или битый JSON - ресурс ещё не использовали
    или сбой записи, работаем как будто дней ещё нет, НЕ падаем."""
    data, _err = load_json(DAYS_JSON)
    return data if isinstance(data, dict) else {}


def human_closed_at(days: dict, d_str: str):
    """closedAt конкретного дня, если день закрыт человеком руками из интерфейса.
    None - файла/записи нет, день ещё открыт, или значение битое (не непустая строка).
    closedAt в days.json - это 'HH:MM' (см. server.py V_DAY, v_maybe(v_time)),
    не ISO-момент."""
    rec = days.get(d_str) if isinstance(days, dict) else None
    if not isinstance(rec, dict):
        return None
    ca = rec.get("closedAt")
    return ca if isinstance(ca, str) and ca else None


def parse_hhmm(s) -> int:
    """'HH:MM' -> минуты с полуночи. На мусоре возвращает None, а не падает."""
    if not isinstance(s, str):
        return None
    parts = s.split(":")
    if len(parts) < 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= h <= 47 and 0 <= m <= 59):
        return None
    return h * 60 + m


def is_scalar(v) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def dumps_sprint_style(obj, level: int = 0) -> str:
    """Сериализатор JSON, воспроизводящий стиль sprint.json: отступ 1 пробел
    на уровень вложенности, объекты из одних скаляров печатаются в одну строку
    (как события/auto/backlog в исходном файле). Формат файла не ломаем."""
    ind = " " * level
    ind_in = " " * (level + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        if all(is_scalar(v) for v in obj.values()):
            parts = [
                f"{json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                for k, v in obj.items()
            ]
            return "{ " + ", ".join(parts) + " }"
        items = list(obj.items())
        lines = []
        for i, (k, v) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            lines.append(
                f'{ind_in}{json.dumps(k, ensure_ascii=False)}: {dumps_sprint_style(v, level + 1)}{comma}'
            )
        return "{\n" + "\n".join(lines) + "\n" + ind + "}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for i, v in enumerate(obj):
            comma = "," if i < len(obj) - 1 else ""
            lines.append(f"{ind_in}{dumps_sprint_style(v, level + 1)}{comma}")
        return "[\n" + "\n".join(lines) + "\n" + ind + "]"
    return json.dumps(obj, ensure_ascii=False)


def atomic_write_text(path: Path, text: str):
    """Запись через временный файл в той же директории + os.replace."""
    ensure_dir(path.parent)
    fd, tmp_path = tempfile.mkstemp(prefix="." + path.name + "-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        # Запись сорвалась - временный файл не стираем (правило владельца номер ноль),
        # помечаем меткой времени и оставляем рядом
        if os.path.exists(tmp_path):
            try:
                os.replace(tmp_path, tmp_path + ".orphan-" + now().strftime("%Y%m%d-%H%M%S"))
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Собранность дня и мета-порог 85 процентов
# ---------------------------------------------------------------------------

MACHINE_SOURCES = ("auto", "device", "device", "engine")
ADHERENCE_HABIT = "adherence_85"
ADHERENCE_THRESHOLD = 85       # процентов дней, порог из канона
SYNC_FRESH_HOURS = 26          # столько живёт последний успешный забор прибора

# ИМЕНОВАННАЯ ТАБЛИЦА привычек, которые ставит САМ ДВИЖОК. Зачем она есть.
# Строка с source: engine обещает владельцу «ставит трекер, руками не отмечается».
# Обещание держится не словом, а кодом, и код обязан быть НАЗВАН: id -> где именно
# он живёт. Пустая таблица под живой строкой это ровно та «обещанная и не
# работающая автоматика», которая хуже её отсутствия. Зеркало таблицы стоит в
# static/tab-track.js (ENGINE_MARKS), и чекер требует, чтобы каждая активная
# строка с source: engine стояла здесь ключом.
# 🔴 ФОРМАТ ЗНАЧЕНИЯ СТРОГИЙ: «путь#якорь · человеческий адрес».
# Раньше значение было свободным текстом, и проверка 07 чекера мерила только то,
# что id лежит ключом в этом словаре. Фиктивная привычка с source: engine, нулём
# кода и выдуманным якорем проходила зелёной. Теперь чекер РЕЗОЛВИТ значение:
# открывает файл по пути от ~/planner и ищет якорь буквально. Нет якоря -
# нарушение. Человеческая часть после « · » идёт владельцу в вечерний отчёт,
# поэтому она написана адресом на экране, а не адресом в коде.
ENGINE_MARKS = {
    "lichnaya_privychka_4":
        "static/tab-track.js#function syncBenchmarkHabit · блок «Вечерний чек» во вкладке «Трекеры»",
    ADHERENCE_HABIT:
        "rituals/_common.py#def write_adherence_mark · вечерний ритуал, считается сам по доступным единицам",
}


def device_state(track: dict) -> str:
    """ТРИ состояния данных прибора, а не два.

    'нет данных' забора не было НИ РАЗУ (владелец ещё не входил в Прибор)
    'протухли'   забор был, но последний успешный старше SYNC_FRESH_HOURS
    'ok'         данные свежие

    Зачем третье. Пустая галочка у привычки прибора до первого входа читается как
    «не сделал», зелёная - как «сделал», и оба чтения враньё: данных нет вообще.
    Поэтому такая строка в ЗНАМЕНАТЕЛЬ дня не входит."""
    s = (track or {}).get("deviceSync") or {}
    stamp = s.get("lastOkAt")
    if not stamp:
        return "нет данных"
    try:
        age = (now() - datetime.fromisoformat(stamp)).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return "нет данных"
    return "ok" if age <= SYNC_FRESH_HOURS else "протухли"


def available_habits(track: dict, day=None):
    """Привычки, ДОСТУПНЫЕ владельцу в этот день. Ровно они и образуют знаменатель.

    Арифметика, ради которой это заведено: в активном списке 23 строки, из них
    пять снимает Прибор и одна - мета-порог сам по себе. Пока владелец не вошёл в
    Прибор, предельная собранность дня по всему списку выходит около 78 процентов,
    и мета-порог 85 красный по конструкции с первого дня. Считаем по доступному.

    🔴 `daily: false` больше не значит «мертва во все семь дней». Строка, чья
    частота идёт за днями недели (тренировка и всё, что к ней привязано), несёт
    поле `days` с кодами mon..sun и попадает в знаменатель ровно в свои дни.
    Прежняя форма выкидывала такую строку отовсюду и навсегда: подсказка обещала
    владельцу «идёт за днями тренировок», а вечерний ритуал не спрашивал её ни
    разу за неделю. `daily: false` БЕЗ поля `days` работает как прежде - строка
    вне знаменателя всегда (так стоят парковки и мета-порог)."""
    state = device_state(track)
    d = day or today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    wd = WEEKDAY_CODES[d.weekday()]
    out = []
    for h in (track or {}).get("habits", []):
        if h.get("archived") or h.get("id") == ADHERENCE_HABIT:
            continue
        if h.get("daily") is False and wd not in (h.get("days") or []):
            continue
        if h.get("source") in ("device", "device") and state != "ok":
            continue                      # данных прибора нет - строка вне знаменателя
        out.append(h)
    return out


def day_adherence(track: dict, day: str):
    """(отмечено, доступно, процент) за день по ДОСТУПНЫМ единицам.

    День передаётся ДАЛЬШЕ: у строк с частотой по дням недели знаменатель
    у понедельника и у воскресенья разный, и считать их «по сегодня» при
    запросе за другую дату значит печатать процент от чужого множества."""
    rows = available_habits(track, day)
    log = (track.get("log") or {}).get(day, {})
    done = sum(1 for h in rows if log.get(h["id"]))
    pct = round(done / len(rows) * 100) if rows else 0
    return done, len(rows), pct


def visual_duplicates(events):
    """Группы событий, ВЫГЛЯДЯЩИХ одинаково: одна дата, одно время, одно название.

    Зачем. В данных владельца лежит задвоенная запись (она была там ещё до этих
    работ, и удалять её нельзя - правило номер ноль). Утренний отчёт печатал её
    двумя одинаковыми строками подряд, и первое, что владелец читает утром,
    выглядело как сбой движка. Ритуал теперь печатает такую пару ОДНОЙ строкой и
    отдельно называет id, чтобы решение о дубле принимал владелец, а не машина.
    Возвращает {(дата, время, название): [события]} только для групп больше одной.
    """
    groups = {}
    for e in events or []:
        if not isinstance(e, dict):
            continue
        key = (e.get("date"), e.get("start"), e.get("title"))
        groups.setdefault(key, []).append(e)
    return {k: v for k, v in groups.items() if len(v) > 1}


def collapse_visual_duplicates(events):
    """Тот же список, но каждая визуально одинаковая группа оставлена ОДНОЙ записью.

    Данные не трогаются: схлопывание живёт только в отчёте.
    """
    seen, out = set(), []
    for e in events or []:
        if not isinstance(e, dict):
            out.append(e)
            continue
        key = (e.get("date"), e.get("start"), e.get("title"))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def write_adherence_mark(day: str, quiet: bool = True):
    """Движок САМ ставит отметку мета-порога. Это и есть код за `source: engine`.

    Что было до этого. Строка `adherence_85` стояла с source: engine, интерфейс
    обещал владельцу «ставит трекер, руками не отмечается», а кода, который пишет
    log[день]["adherence_85"], не было НИГДЕ: греп по движку давал только
    вычисление процента и его печать. Ячейка осталась бы пустой навсегда при
    обещании, что её заполняет движок.

    Возвращает (поставлено, отмечено, доступно, процент) либо None, если строки
    в активном списке нет или считать не по чему. Пишет через общий гард, поэтому
    в песочнице уезжает в песочный корень, а не в боевые данные владельца.
    """
    doc, etag = read_resource("track")
    live = [h for h in doc.get("habits", [])
            if h.get("id") == ADHERENCE_HABIT and not h.get("archived")]
    if not live:
        return None
    done, avail, pct = day_adherence(doc, day)
    if not avail:
        return None
    ok = pct >= ADHERENCE_THRESHOLD
    d = doc.setdefault("log", {}).setdefault(day, {})
    if bool(d.get(ADHERENCE_HABIT)) == ok and ADHERENCE_HABIT in d:
        return (ok, done, avail, pct)      # значение уже стоит, лишней записи не делаем
    d[ADHERENCE_HABIT] = ok
    write_resource("track", doc, etag, quiet=quiet)
    return (ok, done, avail, pct)


def rotate_backups(prefix: str, keep: int = BACKUP_KEEP):
    """Ротация бэкапов ПЕРЕНОСОМ, а не стиранием: в горячей папке остаются
    последние `keep` файлов префикса, остальные уезжают в backups/arhiv/.

    Раньше здесь стояло стирание файла, то есть ритуал сам сносил бэкапы владельца.
    Правило владельца номер ноль запрещает удаление без его явного «да», а бэкап
    ценен ровно тем, что переживает ошибку. keep <= 0 отключает перенос вовсе."""
    if not BACKUPS_DIR.exists() or keep <= 0:
        return []
    own = sorted(p for p in BACKUPS_DIR.iterdir() if p.name.startswith(prefix + "-") and p.is_file())
    archive = BACKUPS_DIR / "arhiv"
    moved = []
    for p in own[:-keep]:
        try:
            ensure_dir(archive)
            target = archive / p.name
            if target.exists():
                target = archive / (p.name + ".2")
            os.replace(str(p), str(target))
            moved.append(p.name)
        except OSError:
            pass
    return moved


def backup_and_write_sprint(data: dict) -> Path:
    """Бэкап текущего sprint.json в sprint/backups/ (с ротацией), затем атомарная
    запись (temp-файл + os.replace) в исходном стиле форматирования. Возвращает путь
    бэкапа (или None, если исходного файла ещё не было).

    ВАЖНО: это машинная запись. Вызывающий обязан после неё позвать
    note_machine_write(PLANNER_JSON), иначе сторож примет её за работу человека.
    """
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if PLANNER_JSON.exists():
        # микросекунды в штампе - иначе быстрые повторные прогоны (ручной тест,
        # или сбой и рестарт в ту же секунду) затирают предыдущий бэкап тем же именем
        stamp = now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = BACKUPS_DIR / f"sprint-{stamp}.json"
        shutil.copy2(PLANNER_JSON, backup_path)
        rotate_backups("sprint")

    atomic_write_text(PLANNER_JSON, dumps_sprint_style(data) + "\n")
    return backup_path


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def write_report(path: Path, text: str):
    atomic_write_text(path, text)


# --------------------------------------------------------------------------
# След человека (pulse)
# --------------------------------------------------------------------------

def _canonical_bytes(path: Path):
    """Содержимое файла, нормализованное так, чтобы переформатирование того же
    JSON не считалось изменением (сервер пишет indent=1, ритуалы - своим стилем)."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_fingerprint(path: Path):
    if not path.exists():
        return None
    c = _canonical_bytes(path)
    if c is None:
        return None
    return hashlib.sha256(c).hexdigest()


def file_signals(name: str, path: Path) -> dict:
    """Мелкие человекочитаемые счётчики - чтобы в отчёте писать не «файл изменился»,
    а «отметок сделано 2 → 3»."""
    data, err = load_json(path)
    if err or not isinstance(data, dict):
        return {}
    if name == "sprint.json":
        ev = [e for e in (data.get("events") or []) if isinstance(e, dict)]
        return {
            "events": len(ev),
            "done": sum(1 for e in ev if e.get("done") is True),
            "needsDecision": sum(1 for e in ev if e.get("needsDecision") is True),
            "backlog": len(data.get("backlog") or []),
        }
    if name == "tracker.json":
        log = data.get("log") if isinstance(data.get("log"), dict) else {}
        marks = 0
        for v in log.values():
            if isinstance(v, dict):
                marks += sum(1 for x in v.values() if x)
            elif isinstance(v, list):
                marks += len(v)
            elif v:
                marks += 1
        return {"logDays": len(log), "marks": marks, "habits": len(data.get("habits") or [])}
    if name == "goals-cycle.json":
        goals = [g for g in (data.get("goals") or []) if isinstance(g, dict)]
        leads = 0
        for g in goals:
            for l in (g.get("leads") or []):
                if isinstance(l, dict):
                    leads += sum(1 for w in (l.get("weeks") or []) if w)
        return {"goals": len(goals), "leadMarks": leads}
    if name == "profile.json":
        return {"fields": len(data)}
    if name == "days.json":
        # документ здесь - сама карта дат без обёртки (см. server.py _default_days)
        recs = [v for v in data.values() if isinstance(v, dict)]
        return {
            "daysLogged": len(recs),
            "daysClosedByHuman": sum(1 for v in recs if isinstance(v.get("closedAt"), str) and v.get("closedAt")),
        }
    return {}


_SIGNAL_LABELS = {
    "done": "отметок «сделано»",
    "needsDecision": "флагов «требует решения»",
    "events": "событий",
    "backlog": "в бэклоге",
    "marks": "отметок в трекере",
    "logDays": "дней в трекере",
    "habits": "привычек",
    "goals": "целей",
    "leadMarks": "отметок по lead-метрикам",
    "fields": "полей профиля",
    "daysLogged": "дней в days.json",
    "daysClosedByHuman": "дней закрыто вручную",
}


def _describe_drift(old_sig: dict, new_sig: dict, changed: list) -> str:
    parts = []
    for name in changed:
        o = old_sig.get(name) or {}
        n = new_sig.get(name) or {}
        deltas = []
        for k, label in _SIGNAL_LABELS.items():
            a, b = o.get(k), n.get(k)
            if isinstance(a, int) and isinstance(b, int) and a != b:
                deltas.append(f"{label} {a} → {b}")
        parts.append(f"{name}: " + ("; ".join(deltas) if deltas else "правка содержимого"))
    return " · ".join(parts)


def read_pulse() -> dict:
    data, err = load_json(PULSE_JSON)
    if err or not isinstance(data, dict):
        return {}
    return data


def write_pulse(p: dict):
    ensure_dir(STATE_DIR)
    atomic_write_text(PULSE_JSON, json.dumps(p, ensure_ascii=False, indent=1) + "\n")


def _current_state():
    fps, sigs = {}, {}
    for name, path in DATA_FILES.items():
        fps[name] = file_fingerprint(path)
        sigs[name] = file_signals(name, path)
    return fps, sigs


def sync_pulse() -> dict:
    """Сверяет реальные файлы данных с отпечатком, который машина сняла после
    СВОЕЙ последней записи. Расхождение = запись, которую сделала не машина,
    то есть человек (интерфейс, отметка выполнения, апрув). Только оно двигает
    lastHumanAt. Возвращает актуальный pulse."""
    p = read_pulse()
    fps, sigs = _current_state()
    snap = p.get("snapshot")

    if not isinstance(snap, dict) or not snap:
        newest = None
        for path in DATA_FILES.values():
            if path.exists():
                mt = datetime.fromtimestamp(path.stat().st_mtime)
                newest = mt if newest is None or mt > newest else newest
        p["snapshot"] = fps
        p["signals"] = sigs
        if not p.get("lastHumanAt"):
            p["lastHumanAt"] = (newest or now()).isoformat(timespec="seconds")
            p["lastHumanWhat"] = "инициализация следа: взято время последнего изменения данных"
        p.setdefault("initializedAt", now().isoformat(timespec="seconds"))
        write_pulse(p)
        return p

    changed = [name for name in DATA_FILES if fps.get(name) != snap.get(name)]
    if changed:
        stamps = []
        for name in changed:
            path = DATA_FILES[name]
            if path.exists():
                stamps.append(datetime.fromtimestamp(path.stat().st_mtime))
        at = max(stamps) if stamps else now()
        what = _describe_drift(p.get("signals") or {}, sigs, changed)
        p["lastHumanAt"] = at.isoformat(timespec="seconds")
        p["lastHumanWhat"] = what
        recent = p.get("recent") or []
        recent.insert(0, {"at": p["lastHumanAt"], "what": what})
        p["recent"] = recent[:20]
        p["snapshot"] = fps
        p["signals"] = sigs
        write_pulse(p)
    return p


def note_machine_write(*paths: Path):
    """Машина записала файл(ы) - обновляем отпечаток, НЕ трогая lastHumanAt.
    Без этого вызова собственная запись ритуала выглядит как активность человека."""
    p = read_pulse()
    snap = dict(p.get("snapshot") or {})
    sigs = dict(p.get("signals") or {})
    touched = {str(x) for x in paths}
    for name, path in DATA_FILES.items():
        if str(path) in touched:
            snap[name] = file_fingerprint(path)
            sigs[name] = file_signals(name, path)
    p["snapshot"] = snap
    p["signals"] = sigs
    p["lastMachineWriteAt"] = now().isoformat(timespec="seconds")
    write_pulse(p)
    return p


def record_human_action(what: str):
    """Явное действие человека (например решение по застрявшей задаче через decide.py)."""
    p = read_pulse()
    fps, sigs = _current_state()
    p["snapshot"] = fps
    p["signals"] = sigs
    p["lastHumanAt"] = now().isoformat(timespec="seconds")
    p["lastHumanWhat"] = what
    recent = p.get("recent") or []
    recent.insert(0, {"at": p["lastHumanAt"], "what": what})
    p["recent"] = recent[:20]
    write_pulse(p)
    return p


def hours_since_human(p: dict):
    at = parse_dt(p.get("lastHumanAt"))
    if at is None:
        return None
    return (now() - at).total_seconds() / 3600.0


def record_day_closed(d: date, stats: dict):
    """Журнал закрытых дней: сколько было запланировано и сколько человек отметил.
    Сторож читает его, чтобы видеть дни без единой отметки."""
    p = read_pulse()
    days = p.get("days") or {}
    entry = dict(stats)
    entry["closedAt"] = now().isoformat(timespec="seconds")
    days[d.isoformat()] = entry
    # 🔴 Подрезка журнала переведена в ОБРАТИМУЮ форму. Прежняя версия молча
    # изымала всё старше 120 записей, то есть через четыре месяца истории
    # закрытых дней у владельца просто не стало бы, и увидеть это было бы негде.
    # Теперь вытесненные записи не исчезают: они уезжают в датированный файл
    # рядом (`pulse-arhiv-<дата>.json`), и только после успешной записи архива
    # убираются из горячего документа. Выключатель константой на месте: подними
    # PULSE_KEEP_DAYS - и подрезки не будет вовсе.
    if PULSE_KEEP_DAYS and len(days) > PULSE_KEEP_DAYS:
        cold = sorted(days)[:-PULSE_KEEP_DAYS]
        arch_path = STATE_DIR / ("pulse-arhiv-%s.json" % now().strftime("%Y%m%d"))
        ensure_dir(STATE_DIR)
        prev = {}
        if arch_path.exists():
            try:
                prev = json.loads(arch_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                prev = {}
        prev.update({k: days[k] for k in cold})
        arch_path.write_text(json.dumps(prev, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        for k in cold:
            days.pop(k, None)
    p["days"] = days
    p["lastClosedDate"] = max(days) if days else d.isoformat()
    write_pulse(p)
    return p


# --------------------------------------------------------------------------
# Доставка тревоги
# --------------------------------------------------------------------------

def _log_notification(level: str, title: str, message: str, channel: str):
    ensure_dir(STATE_DIR)
    line = f"{now().isoformat(timespec='seconds')}\t{level}\t{channel}\t{title}\t{message}\n"
    with NOTIFY_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def notify(title: str, message: str, level: str = "warn", modal: bool = False) -> str:
    """Тревога, которая реально доходит.

    Канал: системное уведомление macOS (osascript). Оно попадает в Центр
    уведомлений и переживает пропуск - в отличие от файла ALERT.md, который
    никто не открывает, и от лога launchd, который не читает никто вообще.
    При modal=True поверх уведомления показываем модальное окно: его нельзя
    не заметить, применяем только для затяжной тревоги.

    В песочнице (PLANNER_TEST_ROOT) и при PLANNER_NO_NOTIFY=1 окон не показываем,
    пишем строку в state/notifications.log - чтобы доставка была проверяема.
    """
    channel = "osascript"
    if IS_SANDBOX or os.environ.get("PLANNER_NO_NOTIFY") == "1":
        channel = "log+modal" if modal else "log"
        _log_notification(level, title, message, channel)
        return channel

    text = message if len(message) <= 220 else message[:217] + "..."
    try:
        subprocess.run(
            [
                "osascript",
                "-e", "on run argv",
                "-e", 'display notification (item 1 of argv) with title (item 2 of argv) sound name "Sosumi"',
                "-e", "end run",
                text, title,
            ],
            check=False, timeout=20,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        channel = "failed"

    if modal:
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e", "on run argv",
                    "-e", 'display dialog (item 1 of argv) with title (item 2 of argv) '
                          'buttons {"Понял"} default button 1 with icon caution giving up after 300',
                    "-e", "end run",
                    text, title,
                ],
                check=False, timeout=330,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            channel += "+modal"
        except (OSError, subprocess.SubprocessError):
            pass

    _log_notification(level, title, message, channel)
    return channel


def run_ritual(name: str, fn):
    """Обёртка запуска. Падение ритуала больше не уезжает в лог, который никто
    не читает: пишем трейс в state/ и бьём системным уведомлением."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001 - смысл обёртки именно в этом
        tb = traceback.format_exc()
        ensure_dir(STATE_DIR)
        stamp = now().strftime("%Y%m%d-%H%M%S")
        crash_path = STATE_DIR / f"crash-{name}-{stamp}.log"
        try:
            crash_path.write_text(tb, encoding="utf-8")
        except OSError:
            crash_path = None
        notify(
            f"🔴 Ритуал {name} упал",
            f"{type(e).__name__}: {e}. Трейс: {crash_path}",
            level="critical",
        )
        print(tb, file=sys.stderr)
        print(f"РИТУАЛ {name} УПАЛ: {type(e).__name__}: {e}")
        if crash_path:
            print(f"Трейс: {crash_path}")
        sys.exit(1)


# --------------------------------------------------------------------------
# События: классификация и ёмкость дня
# --------------------------------------------------------------------------

PLANNED_KINDS = ("active", "launch")
_RITUAL_TITLE_MARKERS = ("разбор недели", "wam", "daily close", "вечерний ритуал", "утренняя сводка")


def is_planned(e) -> bool:
    return isinstance(e, dict) and e.get("kind") in PLANNED_KINDS


def ritual_code(e):
    """Событие, которое исполняет САМА машина (разбор недели и подобное).
    Такое событие нельзя переносить и нельзя считать в человеческом score:
    человек его никогда не отмечает, оно переносилось вечно и топило счёт."""
    if not isinstance(e, dict):
        return None
    code = e.get("ritual")
    if isinstance(code, str) and code:
        return code
    if e.get("doneBy") == "machine":
        return "machine"
    title = (e.get("title") or "")
    low = title.lower()
    for marker in _RITUAL_TITLE_MARKERS:
        if marker in low:
            return "wam" if ("разбор недели" in low or "wam" in low) else "machine"
    return None


def is_fixed(e) -> bool:
    """Жёсткий слот: эфир, встреча, суд. Машина такое НИКОГДА не двигает."""
    return isinstance(e, dict) and e.get("fixed") is True


def safe_start(e) -> str:
    s = e.get("start") if isinstance(e, dict) else None
    return s if isinstance(s, str) else "99:99"


def safe_priority(e):
    """Приоритет, пригодный для сортировки. priority: null раньше валил сводку
    TypeError'ом на сравнении None с int."""
    p = e.get("priority") if isinstance(e, dict) else None
    if isinstance(p, bool):
        return None
    if isinstance(p, (int, float)):
        return p
    if isinstance(p, str):
        try:
            return float(p)
        except ValueError:
            return None
    return None


def dur_min(e) -> int:
    d = e.get("dur") if isinstance(e, dict) else 0
    if isinstance(d, bool) or not isinstance(d, (int, float)):
        return 0
    return int(max(d, 0))


def capacity_norm_min(profile: dict):
    """Норма загрузки дня в минутах. None, если профиль противоречив
    (workEnd раньше workStart) - тогда правило загрузки просто не применяем,
    но говорим об этом вслух, а не молчим."""
    ws = parse_hhmm(profile.get("workStart"))
    we = parse_hhmm(profile.get("workEnd"))
    if ws is None or we is None or we <= ws:
        return None
    pct = profile.get("capacityPercent", 60)
    if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not (0 < pct <= 100):
        pct = 60
    return (we - ws) * pct / 100.0


def day_load_min(events, d_str: str) -> int:
    return sum(dur_min(e) for e in events if is_planned(e) and e.get("date") == d_str)


def next_free_day(d: date, protected_days, events, profile, add_min: int = 0, horizon: int = 14):
    """Следующий день под перенос: пропускаем защищённые дни И дни, которые уже
    несут больше нормы. Пятница раньше сваливала всё на субботу, где уже стоят
    эфир и разбор недели.

    Возвращает (день, загрузка_после_переноса_мин, норма_мин|None, перегружен_bool).
    """
    norm = capacity_norm_min(profile)
    candidates = []
    for i in range(1, horizon + 1):
        nd = d + timedelta(days=i)
        if WEEKDAY_CODES[nd.weekday()] in (protected_days or []):
            continue
        load = day_load_min(events, nd.isoformat())
        candidates.append((nd, load))
        if norm is None or load + add_min <= norm:
            return nd, load + add_min, norm, False
    if not candidates:
        # все дни горизонта защищены - кладём на ближайший следующий день,
        # молча терять задачу нельзя
        nd = d + timedelta(days=1)
        return nd, day_load_min(events, nd.isoformat()) + add_min, norm, True
    nd, load = min(candidates, key=lambda kv: (kv[1], kv[0]))
    return nd, load + add_min, norm, True
