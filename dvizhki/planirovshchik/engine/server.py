#!/usr/bin/env python3
"""Планировщик: недельная сетка + режим дня + цели цикла + трекеры.

Источник истины - файлы в ~/planner-data/:
  sprint.json       события недели
  profile.json      режим дня (подъём/отбой/работа/тренировка/ёмкость)
  goals-cycle.json  цели цикла 12WY
  tracker.json      привычки и сферы

Дашборд читает и пишет ТОЛЬКО эти файлы, к остальному контуру не прикасается.

КОНТРАКТ API (нужен фронту):
  GET  /api/<ресурс>  -> документ + поле "rev" (та же строка в заголовке ETag)
  POST /api/<ресурс>  -> тело: документ ЦЕЛИКОМ + "rev" из последнего GET
                         (либо заголовок If-Match: "<rev>")
      200 {"ok": true, "rev": "<новая версия>"}
      400 схема не сошлась или в теле пропали ключи документа
      403 чужой Origin/Host (CSRF)
      409 {"error": "conflict", "rev": ..., "current": {...}} - документ изменился,
          НИЧЕГО не записано, показать владельцу конфликт
      411 нет Content-Length и тело не chunked
      413 тело больше лимита
      415 Content-Type не application/json
      428 версия не прислана вовсе

  rev - хэш байтов файла на диске. Поэтому запись ритуалом (daily_close, wam и
  прочие пишут файлы напрямую, мимо HTTP) тоже сдвигает версию, и открытая
  вкладка получит честный 409 вместо тихой затирки.

Запуск: python3 ~/planner/server.py   ->   http://localhost:8791
Песочница для тестов: PLANNER_PORT, PLANNER_DATA, PLANNER_BACKUPS, PLANNER_LOG.
"""
import hashlib
import html
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from urllib.parse import unquote, urlparse

PORT = int(os.environ.get("PLANNER_PORT", "8791"))
ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.realpath(os.path.join(ROOT, "static"))
TASKS = os.path.expanduser(os.environ.get("PLANNER_DATA", "~/planner-data"))
BACKUP_DIR = os.path.expanduser(os.environ.get("PLANNER_BACKUPS", os.path.join(ROOT, "backups")))
LOG_PATH = os.path.expanduser(os.environ.get("PLANNER_LOG", "/tmp/planner-server.log"))

BACKUP_KEEP_DAYS = 40      # дней истории на каждый ресурс (первая и последняя версия дня)
MAX_BODY = 1_000_000       # 1 МБ на документ: самый жирный файл проекта - 8 КБ
READ_TIMEOUT = 20          # секунд на чтение запроса, иначе тред висел бы вечно
REV_EMPTY = "empty"        # версия «файла ещё нет» - не путать с битым файлом
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


# --------------------------------------------------------------------------
# Логи. Раньше log_message был заглушён, а трейсбеки уходили в никуда.
# --------------------------------------------------------------------------

LOG = logging.getLogger("sprint")


def _setup_logging():
    LOG.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(message)s")
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    LOG.addHandler(stream)
    try:
        os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
        rotating = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        rotating.setFormatter(fmt)
        LOG.addHandler(rotating)
    except OSError as exc:  # /tmp недоступен - остаёмся хотя бы на stderr
        LOG.warning("не удалось открыть лог-файл %s: %s", LOG_PATH, exc)


# --------------------------------------------------------------------------
# Ресурсы и дефолты
# --------------------------------------------------------------------------

def _default_data():
    return {"events": [], "backlog": [], "sprintGoal": ""}


def _default_profile():
    return {
        "wake": "08:00", "sleep": "00:00",
        "workStart": "10:00", "workEnd": "22:00",
        "peakFrom": "10:00", "peakTo": "14:00",
        "training": {"days": ["mon", "wed", "fri"], "start": "09:00", "dur": 60},
        "windDown": "22:30",
        "protectedDays": ["sun"],
        "capacityPercent": 60,
        "deepBlockMin": 90,
        "breakMin": 15,
        # ритм дня: разметка рабочего окна на блоки с перерывами в недельной
        # сетке. Перерыв живёт ВНУТРИ блока: 90 минут = 80 фокуса + 10 паузы
        "lunchStart": "12:00",
        "lunchDur": 60,
        "dinnerStart": "19:00",
        "dinnerDur": 30,
        "rhythmOn": True,
    }


def _default_goals():
    return {"cycle": {}, "goals": []}


def _default_track():
    return {"habits": [], "spheres": [], "log": {}}


def _default_days():
    """Ритуалы дня живут ОТДЕЛЬНО от sprint.json (решение критика волны 2):
    новый ключ верхнего уровня в sprint.json ломал бы сохранение из старой
    открытой вкладки 400-кой «нет ключей документа». Документ здесь - сама
    карта дат, без обёртки."""
    return {}


# ключ ресурса -> (путь к файлу, фабрика дефолта, префикс бэкапа)
RESOURCES = {
    "data": (os.path.join(TASKS, "sprint.json"), _default_data, "sprint"),
    "profile": (os.path.join(TASKS, "profile.json"), _default_profile, "profile"),
    "goals": (os.path.join(TASKS, "goals-cycle.json"), _default_goals, "goals"),
    "track": (os.path.join(TASKS, "tracker.json"), _default_track, "track"),
    "days": (os.path.join(TASKS, "days.json"), _default_days, "days"),
}

# путь API -> ключ ресурса
ROUTES = {
    "/api/data": "data",
    "/api/profile": "profile",
    "/api/goals": "goals",
    "/api/track": "track",
    "/api/days": "days",
}


def _device_page(title, body):
    """Ответ приёмнику кода Прибор. Текст простой: его читает владелец в браузере."""
    return (
        "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>%s</title><body style='font:17px/1.5 -apple-system,system-ui,sans-serif;max-width:640px;"
        "margin:48px auto;padding:0 20px;color:#1c1c1e'><h1 style='font-size:26px'>%s</h1>"
        "<pre style='white-space:pre-wrap;background:#f4f1ec;padding:14px;border-radius:10px'>%s</pre>"
        "<p><a href='/'>Открыть Task Manager</a></p></body>"
    ) % (html.escape(title), html.escape(title), html.escape(body))

# одна блокировка на ресурс: read-modify-write не должен перемешиваться между вкладками
_LOCKS = {key: threading.Lock() for key in RESOURCES}


# --------------------------------------------------------------------------
# Схема входа. Раньше сохранялось всё подряд: start "99:99", dur -500,
# title объектом. Ниже - маленький набор проверок, из них собраны 4 схемы.
# Незнакомые ключи не режем (фронт добавляет свои), знакомые проверяем строго.
# --------------------------------------------------------------------------

class Invalid(Exception):
    """Тело не прошло схему: путь до поля + объяснение по-человечески."""

    def __init__(self, path, msg):
        super().__init__("%s: %s" % (path, msg) if path else msg)
        self.path = path
        self.msg = msg


TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _tname(value):
    return {str: "строка", bool: "булево", int: "целое", float: "дробное",
            list: "список", dict: "объект", type(None): "null"}.get(type(value), type(value).__name__)


def _key(parent, name):
    return "%s.%s" % (parent, name) if parent else str(name)


def v_any(_value, _path):
    return None


def v_str(max_len=500, empty_ok=True):
    def check(value, path):
        if not isinstance(value, str):
            raise Invalid(path, "ожидалась строка, пришло %s" % _tname(value))
        if not empty_ok and not value.strip():
            raise Invalid(path, "пустая строка недопустима")
        if len(value) > max_len:
            raise Invalid(path, "длиннее %d символов" % max_len)
    return check


def v_int(low, high, none_ok=False):
    def check(value, path):
        if value is None and none_ok:
            return
        if isinstance(value, bool) or not isinstance(value, int):
            raise Invalid(path, "ожидалось целое число, пришло %s" % _tname(value))
        if not (low <= value <= high):
            raise Invalid(path, "вне диапазона %d..%d (пришло %s)" % (low, high, value))
    return check


def v_num(low=None, high=None, none_ok=False):
    def check(value, path):
        if value is None and none_ok:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise Invalid(path, "ожидалось число, пришло %s" % _tname(value))
        if low is not None and value < low:
            raise Invalid(path, "меньше %s (пришло %s)" % (low, value))
        if high is not None and value > high:
            raise Invalid(path, "больше %s (пришло %s)" % (high, value))
    return check


def v_bool(value, path):
    if not isinstance(value, bool):
        raise Invalid(path, "ожидалось true/false, пришло %s" % _tname(value))


def v_time(value, path):
    if not isinstance(value, str) or not TIME_RE.match(value):
        raise Invalid(path, "время должно быть ЧЧ:ММ в сутках 00:00-23:59 (пришло %r)" % (value,))


def v_date(value, path):
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise Invalid(path, "дата должна быть ГГГГ-ММ-ДД (пришло %r)" % (value,))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise Invalid(path, "такой даты не существует: %s" % value)


def v_month(value, path):
    if not isinstance(value, str) or not MONTH_RE.match(value):
        raise Invalid(path, "ожидался месяц ГГГГ-ММ (пришло %r)" % (value,))


def v_enum(values):
    def check(value, path):
        if value not in values:
            raise Invalid(path, "допустимы только %s (пришло %r)" % (", ".join(map(str, values)), value))
    return check


def v_maybe(checker):
    """null проходит всегда, иначе делегирует внутреннему валидатору.
    Нужен для полей вида null|"HH:MM" (closedAt - день ещё не закрыт)."""
    def check(value, path):
        if value is None:
            return
        checker(value, path)
    return check


def v_scalar(max_len=500):
    """Строка/число/булево/пусто - для свободных полей вроде оценок сфер."""
    text = v_str(max_len)

    def check(value, path):
        if value is None or isinstance(value, (bool, int, float)):
            return
        text(value, path)
    return check


def v_obj(fields, required=(), max_keys=200):
    def check(value, path):
        if not isinstance(value, dict):
            raise Invalid(path, "ожидался объект, пришло %s" % _tname(value))
        if len(value) > max_keys:
            raise Invalid(path, "слишком много ключей (%d)" % len(value))
        for name in required:
            if name not in value:
                raise Invalid(path, "не хватает обязательного ключа %r" % name)
        for name, item in value.items():
            if not isinstance(name, str):
                raise Invalid(path, "ключ объекта должен быть строкой")
            checker = fields.get(name)
            if checker is not None:
                checker(item, _key(path, name))
    return check


def v_arr(item, max_items=2000):
    def check(value, path):
        if not isinstance(value, list):
            raise Invalid(path, "ожидался список, пришло %s" % _tname(value))
        if len(value) > max_items:
            raise Invalid(path, "больше %d элементов" % max_items)
        for i, element in enumerate(value):
            item(element, "%s[%d]" % (path, i))
    return check


def v_map(key_check, value_check, max_keys=5000):
    def check(value, path):
        if not isinstance(value, dict):
            raise Invalid(path, "ожидался объект, пришло %s" % _tname(value))
        if len(value) > max_keys:
            raise Invalid(path, "больше %d ключей" % max_keys)
        for name, item in value.items():
            key_check(name, "%s{%s}" % (path, name))
            value_check(item, _key(path, name))
    return check


V_EVENT = v_obj(
    {
        "id": v_str(64, empty_ok=False),
        "title": v_str(500, empty_ok=False),
        "date": v_date,
        "start": v_time,
        "dur": v_int(1, 1440),          # 0 давал событие-невидимку, -5 сохранялся
        "kind": v_str(32),
        "track": v_str(64),
        "note": v_str(4000),
        "priority": v_int(0, 9, none_ok=True),
        "est": v_int(0, 10080, none_ok=True),
        "actual": v_int(0, 10080, none_ok=True),
        "dependsOn": v_str(64),
        "starts": v_str(64),
        "fixed": v_bool,
        "done": v_bool,
        "moved": v_int(0, 100),
        "focusMin": v_int(0, 1440, none_ok=True),   # накопленные минуты фокус-таймера
        # taskId - к какой ЗАДАЧЕ ЦЕЛИ цикла относится действие (goals-cycle.json,
        # goals[].tasks[].id). Появляется ТОЛЬКО когда владелец сам тянет строку
        # проекции задач в календарь. Обратной записи нет: полоса задач читает
        # goals-cycle.json и не пишет туда ничего, поэтому копии названия задачи в
        # sprint.json не возникает и расходиться нечему
        "taskId": v_str(64),
    },
    required=("id", "title", "date", "start", "dur"),
)

V_AUTO = v_obj(
    {
        "id": v_str(64, empty_ok=False),
        "title": v_str(500, empty_ok=False),
        "from": v_date,
        "to": v_date,
        "track": v_str(64),
        "note": v_str(4000),
        "launchedBy": v_str(64),
    },
    required=("id", "title", "from", "to"),
)

V_BACKLOG = v_obj(
    {
        "id": v_str(64, empty_ok=False),
        "title": v_str(500, empty_ok=False),
        "est": v_int(0, 10080, none_ok=True),
        "track": v_str(64),
        "when": v_str(200),
        "note": v_str(4000),
        "status": v_enum(("anytime", "someday")),   # someday прячется за ссылкой в бэклоге
        "ttl": v_date,                               # просроченный TTL всплывает бейджем
        "due": v_date,
        "priority": v_int(0, 9, none_ok=True),
        "energy": v_enum(("deep", "mid", "low")),   # для слотов автораскладки: пик/провал
    },
    required=("id", "title"),
)

V_LEAD = v_obj(
    {
        "id": v_str(64, empty_ok=False),
        "title": v_str(300, empty_ok=False),
        "weeklyTarget": v_int(0, 1000),
        "weeks": v_arr(v_any, 53),
    },
    required=("id", "title"),
)

V_LAG = v_obj({
    "metric": v_str(200),
    "target": v_num(low=0, none_ok=True),     # отрицательная цель - брак
    "current": v_num(low=0, none_ok=True),
    "unit": v_str(32),
    "due": v_date,
})

V_GOAL = v_obj(
    {
        "id": v_str(64, empty_ok=False),
        "title": v_str(300, empty_ok=False),
        "note": v_str(4000),
        "lag": V_LAG,
        # второй слой той же цели (100 учеников И $200к) - форма один в один с lag.
        # НЕобязательный: у цели с одним слоем ключа нет вообще, и документы,
        # написанные до появления lag2, проходят валидацию без единой правки
        "lag2": V_LAG,
        # ЗАДАЧИ цели - средний этаж цепочки цель -> задача -> действие.
        # Цель «100 000 подписчиков» разбивается на задачи «разогнать три аккаунта»,
        # «наладить автовыкладку», а те уже дают действия в плане недели.
        # weeks - номера недель цикла (1..53), в которых задача живёт: по ним неделя
        # понимает, что в неё класть. done - задача закрыта целиком.
        # ЭТО НЕ lead measures: задача имеет конец, процесс с галочками по неделям - нет.
        "tasks": v_arr(v_obj({
            "id": v_str(64, empty_ok=False),
            "title": v_str(300, empty_ok=False),
            "note": v_str(2000),
            "done": v_bool,
            "weeks": v_arr(v_int(1, 53), 53),
            "project": v_str(200),      # файл в tasks/projects/, если задача уже там ведётся
        }, required=("id", "title")), 30),
        "leads": v_arr(V_LEAD, 20),
    },
    required=("id", "title"),
)

V_DAY = v_obj(
    {
        "planned": v_bool,
        "plannedAt": v_time,
        "big3": v_arr(v_str(64, empty_ok=False), 10),   # id-шники до 10 штук
        "obstacles": v_str(2000),
        "closedAt": v_maybe(v_time),                    # null - день ещё не закрыт
        "reflection": v_str(4000),
    },
    # всё необязательное - визард пишет поля по шагам, не документом целиком
)

SCHEMAS = {
    "data": v_obj(
        {
            "sprintGoal": v_str(2000),                # числом или объектом - брак
            # ОВЕРРАЙД цели недели по ключу понедельника этой недели. Основная цель
            # недели ВЫЧИСЛЯЕТСЯ из goals-cycle.json (северная задача по фокусирующему
            # вопросу Келлера), а здесь лежит только то, что владелец написал руками.
            # Так цель не протухает при переименовании или закрытии задачи цели
            "sprintGoals": v_map(v_date, v_str(2000), 400),
            "weekStart": v_date,
            "tracks": v_map(v_str(64), v_obj({"label": v_str(120), "color": v_str(32)}), 100),
            "events": v_arr(V_EVENT),
            "auto": v_arr(V_AUTO),
            "backlog": v_arr(V_BACKLOG),
        },
        required=("events",),
    ),
    "profile": v_obj(
        {
            "wake": v_time, "sleep": v_time,
            "workStart": v_time, "workEnd": v_time,
            "peakFrom": v_time, "peakTo": v_time,
            "windDown": v_time,
            "training": v_obj({
                "days": v_arr(v_enum(DAYS), 7),
                "start": v_time,
                "dur": v_int(0, 600),
            }),
            "protectedDays": v_arr(v_enum(DAYS), 7),
            "capacityPercent": v_int(5, 100),
            "deepBlockMin": v_int(15, 480),
            "breakMin": v_int(0, 180),
            # ритм дня. Длительность 0 - еды в разметке нет, но время всё равно
            # обязано быть валидным ЧЧ:ММ: пустая строка сюда не пройдёт
            "lunchStart": v_time,
            "lunchDur": v_int(0, 240),
            "dinnerStart": v_time,
            "dinnerDur": v_int(0, 240),
            "rhythmOn": v_bool,
        },
        required=("wake", "sleep", "workStart", "workEnd"),
    ),
    "goals": v_obj(
        {
            "cycle": v_obj({
                "name": v_str(200),
                "start": v_date,
                "end": v_date,
                "weeks": v_int(1, 53),
            }),
            "goals": v_arr(V_GOAL, 50),
            "execution": v_obj({"weeks": v_arr(v_any, 53)}),
            "stopList": v_arr(v_obj({
                "id": v_str(64, empty_ok=False),
                "title": v_str(300, empty_ok=False),
                "reason": v_str(2000),
            }, required=("id", "title")), 100),
        },
        required=("goals",),
    ),
    "track": v_obj(
        {
            "habits": v_arr(v_obj({
                "id": v_str(64, empty_ok=False),
                "name": v_str(200, empty_ok=False),
                "archived": v_bool,
                "createdAt": v_date,
                # group - блок жизни, по которому привычки рисуются пачками (см. tab-track.js HABIT_GROUPS).
                # source - откуда берётся галочка:
                #   ask    спрашиваю вечером, владелец диктует
                #   device  снимает прибор через tools/device_sync.py
                #   engine движок считает сам (мета-порог, вечерний чек сердца)
                #   auto, device - ПРЕЖНИЕ значения. Из перечисления не выкидываем:
                #          с ними в файле лежат архивные записи, и запрет уронил бы
                #          сохранение всего документа на первой же правке
                # hint - почему привычка в списке: механизм и автор, видно в карточке.
                "group": v_str(64),
                "source": v_enum(("auto", "ask", "device", "engine")),
                "hint": v_str(600),
                # --- слой обоснования: откуда взялся порог и кто за него отвечает ---
                # class разводит ТРИ разных авторства, которые нельзя смешивать:
                #   protocol          порог автора: обязаны дословная цитата и ссылка
                #   owner_requirement требование владельца: цитатой не подкрепляется,
                #                     обязана метка, иначе читается выводом ресёрча
                #   owner_canon       личный канон владельца: то же самое
                "class": v_enum(("protocol", "owner_requirement", "owner_canon")),
                "threshold": v_str(1200),
                "whose_protocol": v_str(300),
                "porogi_row_id": v_str(200),
                "quote": v_str(1600),
                "quote_note": v_str(600),       # служебная метка 📎/🎙️ ВНЕ текста цитаты
                "source_url": v_str(500),
                "frequency": v_str(300),        # свободный текст: «2 раза в сутки», «на каждой тренировке»
                # daily - булево «действие каждый день», НЕЗАВИСИМО от того, как записан
                # свободный текст frequency. По префиксу текста ежедневность не считается:
                # «2 раза в сутки» и «на каждой тренировке» тоже ежедневные
                "daily": v_bool,
                "echelon": v_int(1, 3),
                "conflict_note": v_str(1200),
                "available_today": v_bool,
                "replaces": v_str(300),         # какой прежний id эта строка заменила
                "id_was": v_str(64),            # прежнее написание id, если оно правилось
                "mapped_to": v_str(200),        # куда уехала история архивной записи
                # причина СНЯТИЯ живёт своим полем. Раньше её клали в hint, а hint по
                # своему же определению это «почему привычка в списке», не «почему убрана»
                "archivedReason": v_str(400),
            }, required=("id", "name")), 200),
            "spheres": v_arr(v_obj({
                "id": v_str(64, empty_ok=False),
                "name": v_str(200, empty_ok=False),
                "archived": v_bool,
            }, required=("id", "name")), 200),
            "log": v_map(v_date, v_map(v_str(64), v_scalar(64), 500), 4000),
            "benchmark": v_map(v_date, v_map(v_str(64), v_scalar(64), 500), 4000),
            "monthly": v_map(v_month, v_map(v_str(64), v_map(v_str(64), v_scalar(200), 50), 200), 400),
        },
        required=("habits", "spheres", "log"),
    ),
    # документ - САМА карта дат (без обёртки-ключа). v_obj с дефолтным
    # max_keys=200 умер бы через ~200 дней записи; v_map без такого потолка -
    # правильная идиома для растущей карты (max_keys здесь - явный высокий свой).
    "days": v_map(v_date, V_DAY, max_keys=20000),
}

# где id обязаны быть уникальными: дубль ломает выбор карточки и перенос
UNIQUE_IDS = {
    "data": ("events", "auto", "backlog"),
    "goals": ("goals", "stopList"),
    "track": ("habits", "spheres"),
    "profile": (),
    "days": (),
}


def _check_unique_ids(resource, payload):
    for field in UNIQUE_IDS.get(resource, ()):
        seen = set()
        for i, item in enumerate(payload.get(field) or []):
            if not isinstance(item, dict):
                continue
            ident = item.get("id")
            if ident in seen:
                raise Invalid("%s[%d].id" % (field, i), "такой id уже есть в списке: %r" % (ident,))
            seen.add(ident)


def _check_order(payload, container, first, second, label):
    """Пара «начало не позже конца». Только для ДАТ: время в профиле может
    честно переходить через полночь (работа до 01:00), даты - нет."""
    node = payload.get(container) if container else payload
    if not isinstance(node, dict):
        return
    a, b = node.get(first), node.get(second)
    if isinstance(a, str) and isinstance(b, str) and a > b:
        raise Invalid(_key(container or "", first), "%s: начало %s позже конца %s" % (label, a, b))


def validate(resource, payload):
    """Бросает Invalid с путём до поля. Ничего не пишет и не чинит молча."""
    SCHEMAS[resource](payload, "")
    _check_unique_ids(resource, payload)
    if resource == "goals":
        _check_order(payload, "cycle", "start", "end", "цикл")
    if resource == "data":
        for i, item in enumerate(payload.get("auto") or []):
            if isinstance(item, dict):
                _check_order(item, None, "from", "to", "лента auto[%d]" % i)


def check_no_dropped_keys(current, payload):
    """POST заменяет документ целиком. Значит клиент, приславший только события,
    унёс бы бэклог и цель спринта. Пропажу ключа считаем браком, а не правкой."""
    dropped = [k for k in current if k not in payload]
    if dropped:
        raise Invalid("", "в теле нет ключей документа: %s. POST заменяет документ целиком, "
                          "эти данные были бы стёрты" % ", ".join(sorted(dropped)))


# --------------------------------------------------------------------------
# Файлы: версия документа, чтение, бэкапы по дням, атомарная запись с fsync
# --------------------------------------------------------------------------

class BrokenData(Exception):
    """Файл есть, но прочитать нельзя. Дефолт подсовывать ЗАПРЕЩЕНО:
    первое же сохранение затёрло бы восстановленный файл пустотой."""


def _rev(raw):
    return hashlib.sha256(raw).hexdigest()[:16]


def _read_doc(resource):
    """(документ, версия). Файла нет - дефолты и версия REV_EMPTY.
    Файл битый или недоступен - BrokenData, никаких дефолтов."""
    path, default, _prefix = RESOURCES[resource]
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return default(), REV_EMPTY
    except OSError as exc:
        raise BrokenData("файл недоступен: %s" % exc)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BrokenData("файл повреждён: %s" % exc)
    if not isinstance(data, dict):
        raise BrokenData("в файле не объект JSON, а %s" % _tname(data))
    return data, _rev(raw)


def _backup(prefix, path):
    """Срез по дням: первая версия дня и последняя. Секундный штамп давал окно
    в минуты - при дебаунсе 400 мс вчерашняя версия вымывалась за полчаса."""
    if not os.path.exists(path):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    first = os.path.join(BACKUP_DIR, "%s-%s-first.json" % (prefix, day))
    last = os.path.join(BACKUP_DIR, "%s-%s-last.json" % (prefix, day))
    shutil.copy2(path, first if not os.path.exists(first) else last)
    _prune_backups(prefix, day)


def _prune_backups(prefix, today):
    """Уводим из горячей папки всё старше BACKUP_KEEP_DAYS дней - ПЕРЕНОСОМ в
    backups/arhiv/, без единого стирания.

    Раньше здесь стоял вызов стирания файла, то есть движок сам сносил бэкапы
    владельца при каждой записи ресурса. Это против правила владельца номер ноль
    («вообще ничего не удаляй, пусть лежит»): бэкап тем и ценен, что переживает
    ошибку, а сторож, который сам стирает историю, страховкой не является.
    Обратимая форма: файл уезжает в подпапку, руками возвращается одной командой mv.
    Выключить перенос целиком: BACKUP_KEEP_DAYS = 0."""
    if BACKUP_KEEP_DAYS <= 0:
        return
    pattern = re.compile(r"^%s-(\d{8})[-.]" % re.escape(prefix))
    found = []
    for name in os.listdir(BACKUP_DIR):
        match = pattern.match(name)
        if match:
            found.append((match.group(1), name))
    days = sorted({day for day, _ in found} | {today})
    keep = set(days[-BACKUP_KEEP_DAYS:])
    archive = os.path.join(BACKUP_DIR, "arhiv")
    for day, name in found:
        if day in keep:
            continue
        try:
            os.makedirs(archive, exist_ok=True)
            target = os.path.join(archive, name)
            if os.path.exists(target):        # уже уезжал - второй экземпляр не затираем
                target = os.path.join(archive, "%s.%s" % (name, _rev(name.encode())))
            os.replace(os.path.join(BACKUP_DIR, name), target)
        except OSError as exc:
            LOG.warning("не удалось увести бэкап %s в архив: %s", name, exc)


def _fsync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _save(resource, data):
    """Атомарно, с бэкапом и fsync. Временный файл УНИКАЛЬНЫЙ на каждую запись:
    общий path + '.tmp' при параллельных POST падал с FileNotFoundError."""
    path, _default, prefix = RESOURCES[resource]
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    _backup(prefix, path)
    raw = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())       # без этого при потере питания остаётся нулевой файл
        os.replace(tmp, path)
        tmp = None
        _fsync_dir(folder)
    finally:
        # Запись сорвалась - временный файл НЕ стираем (правило владельца номер ноль),
        # а помечаем меткой времени и оставляем рядом: в нём лежит ровно то, что не
        # доехало до диска, и это единственный след неудачной записи
        if tmp and os.path.exists(tmp):
            try:
                os.replace(tmp, tmp + ".orphan-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            except OSError as exc:
                LOG.warning("временный файл %s остался как есть: %s", tmp, exc)
    return _rev(raw)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

STATIC_CTYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}


class BadRequest(Exception):
    """Тело не прочитать. code - что ответить клиенту."""

    def __init__(self, code, error, message):
        super().__init__(message)
        self.code = code
        self.error = error
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = "sprint"
    timeout = READ_TIMEOUT      # socketserver ставит его на соединение

    # ---------- логи ----------

    def log_message(self, fmt, *args):
        LOG.info("%s %s", self.address_string(), fmt % args)

    def log_error(self, fmt, *args):
        LOG.warning("%s %s", self.address_string(), fmt % args)

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except socket.timeout:
            LOG.warning("таймаут чтения запроса от %s", self.address_string())
            self.close_connection = True
        except (ConnectionResetError, BrokenPipeError) as exc:
            LOG.info("клиент отвалился: %s", exc)
            self.close_connection = True

    # ---------- ответы ----------

    def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError) as exc:
            LOG.info("ответ не доставлен, клиент закрыл соединение: %s", exc)

    def _fail(self, code, error, message, **extra):
        LOG.warning("%s %s -> %s %s (%s)", self.command, self.path, code, error, message)
        payload = {"error": error, "message": message}
        payload.update(extra)
        self._send(code, payload)

    # ---------- защита от чужого сайта ----------

    def _host_ok(self):
        host = self.headers.get("Host")
        if not host:
            return True                       # HTTP/1.0 без Host - браузер так не ходит
        if host.startswith("[") and host.endswith("]"):
            name, port = host, ""             # IPv6 без порта
        else:
            name, _, port = host.rpartition(":")
            if not name or "]" not in name and ":" in name:
                name, port = host, ""
        if name.lower() not in LOCAL_HOSTS:
            return False
        return not port or port == str(PORT)

    def _origin_ok(self):
        if (self.headers.get("Sec-Fetch-Site") or "").lower() == "cross-site":
            return False
        origin = self.headers.get("Origin")
        if not origin:
            return True                       # curl, ритуалы, локальные скрипты
        if origin == "null":
            return False
        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https"):
            return False
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError:
            return False
        if (parsed.hostname or "").lower() not in LOCAL_HOSTS:
            return False
        return port == PORT

    # ---------- чтение тела ----------

    def _read_exact(self, size):
        buf = bytearray()
        while len(buf) < size:
            chunk = self.rfile.read(min(65536, size - len(buf)))
            if not chunk:
                raise BadRequest(400, "short body", "тело оборвалось: ждали %d байт, получили %d"
                                 % (size, len(buf)))
            buf += chunk
        return bytes(buf)

    def _read_chunked(self):
        parts, total = [], 0
        while True:
            line = self.rfile.readline(1024)
            if not line:
                raise BadRequest(400, "bad chunked", "chunked-тело оборвалось")
            head = line.strip().split(b";")[0]
            try:
                size = int(head, 16)
            except ValueError:
                raise BadRequest(400, "bad chunked", "битый размер чанка: %r" % head)
            if size < 0:
                raise BadRequest(400, "bad chunked", "отрицательный размер чанка")
            if size == 0:
                while True:                     # трейлеры до пустой строки
                    tail = self.rfile.readline(1024)
                    if not tail or tail in (b"\r\n", b"\n"):
                        break
                break
            total += size
            if total > MAX_BODY:
                raise BadRequest(413, "too large", "тело больше %d байт" % MAX_BODY)
            parts.append(self._read_exact(size))
            if self.rfile.read(2) not in (b"\r\n",):
                raise BadRequest(400, "bad chunked", "после чанка нет CRLF")
        return b"".join(parts)

    def _read_body(self):
        encoding = (self.headers.get("Transfer-Encoding") or "").strip().lower()
        raw_length = self.headers.get("Content-Length")
        if encoding:
            if encoding != "chunked":
                raise BadRequest(501, "unsupported encoding", "Transfer-Encoding %r не поддержан" % encoding)
            body = self._read_chunked()
        elif raw_length is None:
            raise BadRequest(411, "length required",
                             "нужен Content-Length или Transfer-Encoding: chunked")
        else:
            try:
                length = int(raw_length)
            except ValueError:
                raise BadRequest(400, "bad content-length", "битый Content-Length: %r" % raw_length)
            if length < 0:
                raise BadRequest(400, "bad content-length", "отрицательный Content-Length")
            if length > MAX_BODY:
                raise BadRequest(413, "too large", "тело больше %d байт" % MAX_BODY)
            body = self._read_exact(length)
        if not body.strip():
            raise BadRequest(400, "empty body", "пустое тело: записывать нечего")
        return body

    # ---------- статика ----------

    def _static_path(self, rel):
        rel = rel.lstrip("/")
        if not rel or "\x00" in rel:
            return None
        full = os.path.realpath(os.path.join(STATIC, rel))
        if full != STATIC and not full.startswith(STATIC + os.sep):
            return None                        # симлинк наружу тоже сюда попадает
        return full if os.path.isfile(full) else None

    def _send_static_file(self, rel):
        full = self._static_path(rel)
        if not full:
            return False
        ctype = STATIC_CTYPES.get(os.path.splitext(full)[1], "application/octet-stream")
        try:
            with open(full, "rb") as f:
                payload = f.read()
        except OSError as exc:
            LOG.error("статика %s не читается: %s", full, exc)
            self._fail(500, "static unreadable", "файл интерфейса не читается")
            return True
        self._send(200, payload, ctype)
        return True

    # ---------- маршруты ----------

    # ---------- Прибор: приёмник кода авторизации ----------
    # Redirect URI у PRIBOR обязан быть https, поэтому браузер сначала попадает на
    # страницу сайта владельца (/device/callback/), а та пересылает ?code= сюда, на
    # localhost. Здесь код меняется на токен (tools/device_sync.py) и сразу идёт первый
    # забор. Секретов в ответе нет: код одноразовый, токен ложится в sprint/state/.
    def _device_callback(self):
        from urllib.parse import parse_qs
        qs = parse_qs(urlparse(self.path).query)
        code = (qs.get("code") or [""])[0].strip()
        err = (qs.get("error") or [""])[0]
        desc = (qs.get("error_description") or [""])[0]
        ctype = "text/html; charset=utf-8"
        if not code:
            return self._send(200, _device_page(
                "Прибор не вернул код входа",
                "Ответ Прибор: %s %s" % (err or "в адресе нет параметра code", desc)), ctype)
        tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        try:
            import device_sync
            device_sync.exchange_code(code)
        except Exception as exc:                      # noqa: BLE001 - причина обязана дойти до экрана
            LOG.error("device callback: обмен кода не прошёл: %s", exc)
            return self._send(200, _device_page("Прибор: обмен кода не прошёл", str(exc)), ctype)
        LOG.info("device callback: токен получен, запускаю первый забор")
        script = os.path.join(tools, "device_sync.py")
        try:
            r = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=120)
            out, ok = (r.stdout + r.stderr).strip(), r.returncode == 0
        except subprocess.TimeoutExpired:
            out, ok = "забор не уложился в 120 секунд, сторож повторит его сам в 12:00 и 21:00", False
        title = "Прибор подключён" if ok else "Прибор подключён, но первый забор не прошёл"
        return self._send(200, _device_page(title, out or "готово"), ctype)

    def do_GET(self):
        try:
            path = unquote(urlparse(self.path).path)
            if not self._host_ok():
                return self._fail(403, "bad host", "чужой Host: %r" % self.headers.get("Host"))
            if path in ("/", "/index.html"):
                if not self._send_static_file("index.html"):
                    self._fail(404, "not found", "index.html не найден")
                return
            if path == "/api/where":
                # Read-only справка «куда я пишу». Нужна инструментам, чтобы
                # ДОКАЗАТЬ адресата записи по содержанию, а не по номеру порта:
                # порт можно задать любой, а данные за ним могут быть боевые.
                # Ни одного секрета здесь нет: только порт и папка данных.
                return self._send(200, {"port": PORT, "tasks": os.path.realpath(TASKS),
                                        "backups": os.path.realpath(BACKUP_DIR)})
            if path == "/device/callback":
                return self._device_callback()
            if path in ROUTES:
                return self._get_resource(ROUTES[path])
            if not path.startswith("/api/") and self._send_static_file(path):
                return
            return self._fail(404, "not found", "нет такого пути")
        except Exception:
            LOG.error("GET %s упал:\n%s", self.path, traceback.format_exc())
            self._fail(500, "internal", "внутренняя ошибка, подробности в логе")

    def _get_resource(self, resource):
        with _LOCKS[resource]:
            try:
                data, rev = _read_doc(resource)
            except BrokenData as exc:
                path = RESOURCES[resource][0]
                LOG.error("%s: %s", path, exc)
                return self._fail(500, "broken data",
                                  "%s: %s. Дефолт не подставляю, чтобы не затереть файл" % (path, exc))
        body = dict(data)
        body["rev"] = rev
        self._send(200, body, headers={"ETag": '"%s"' % rev})

    def do_POST(self):
        try:
            path = unquote(urlparse(self.path).path)
            if not self._host_ok():
                return self._fail(403, "bad host", "чужой Host: %r" % self.headers.get("Host"))
            if path not in ROUTES:
                return self._fail(404, "not found", "нет такого пути")
            if not self._origin_ok():
                return self._fail(403, "forbidden origin",
                                  "запись разрешена только с localhost:%d (Origin: %r)"
                                  % (PORT, self.headers.get("Origin")))
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                return self._fail(415, "bad content-type",
                                  "нужен Content-Type: application/json (пришло %r)" % ctype)
            try:
                body = self._read_body()
            except BadRequest as exc:
                return self._fail(exc.code, exc.error, exc.message)
            except socket.timeout:
                return self._fail(408, "timeout", "тело не пришло за %d секунд" % READ_TIMEOUT)
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                return self._fail(400, "bad json", "не разобрать JSON: %s" % exc)
            if not isinstance(payload, dict):
                return self._fail(400, "bad json", "в теле должен быть объект")
            return self._post_resource(ROUTES[path], payload)
        except Exception:
            LOG.error("POST %s упал:\n%s", self.path, traceback.format_exc())
            self._fail(500, "internal", "внутренняя ошибка, подробности в логе")

    def _claimed_rev(self, payload):
        header = self.headers.get("If-Match")
        if header:
            value = header.strip()
            if value.startswith("W/"):
                value = value[2:]
            return value.strip('"')
        rev = payload.get("rev")
        if rev is None:
            return None
        if not isinstance(rev, str):
            raise Invalid("rev", "версия документа должна быть строкой")
        return rev

    def _post_resource(self, resource, payload):
        try:
            claimed = self._claimed_rev(payload)
        except Invalid as exc:
            return self._fail(400, "bad request", str(exc))
        payload.pop("rev", None)                    # служебное поле в файл не пишем

        with _LOCKS[resource]:
            try:
                current, rev = _read_doc(resource)
            except BrokenData as exc:
                path = RESOURCES[resource][0]
                LOG.error("%s: %s", path, exc)
                return self._fail(500, "broken data",
                                  "%s: %s. Запись остановлена" % (path, exc))
            if claimed is None:
                return self._fail(428, "rev required",
                                  "пришли rev из последнего GET (или заголовок If-Match)",
                                  rev=rev)
            if claimed != rev:
                LOG.warning("конфликт версий %s: клиент %s, на диске %s", resource, claimed, rev)
                return self._fail(409, "conflict",
                                  "документ изменился с вашего последнего чтения, ничего не записано",
                                  rev=rev, current=current)
            try:
                validate(resource, payload)
                check_no_dropped_keys(current, payload)
            except Invalid as exc:
                return self._fail(400, "bad request", str(exc), field=exc.path)
            new_rev = _save(resource, payload)

        LOG.info("сохранено %s: %s -> %s", resource, rev, new_rev)
        self._send(200, {"ok": True, "rev": new_rev}, headers={"ETag": '"%s"' % new_rev})


def main():
    _setup_logging()
    LOG.info("старт: http://localhost:%d, данные %s, бэкапы %s", PORT, TASKS, BACKUP_DIR)
    print("Планировщик: http://localhost:%d" % PORT, flush=True)
    print("Данные: %s" % TASKS, flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOG.info("остановлен вручную")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
