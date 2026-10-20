#!/usr/bin/env python3
"""ПРИЁМНИК записи об ужине. Только вход, наружу не ходит ни одной строкой.

Зачем. Владелец описал канал так: данные об ужинах может собирать ассистент, либо
под них можно сделать бота, куда их будут скидывать. Дословная формулировка и имя
адресата лежат в постановке задачи, а НЕ в коде: код раздаётся ученикам, и чужой
ник в нём это утечка личного. Здесь построена ровно приёмная сторона -
структурированная запись об ужине превращается в отметки по привычкам питания.

🔴 ЧЕГО ЗДЕСЬ НЕТ И НЕ ПОЯВИТСЯ БЕЗ ЯВНОГО «ДА» ВЛАДЕЛЬЦА:
транспорта наружу, адреса получателя, готовой формулировки сообщения живому
человеку, юнита launchd. Правило владельца: рассылка и любое сообщение живому
человеку уходят только после его явного «да» на текст, сегмент и канал, а
заранее написанный текст это уже полшага к отправке. Поэтому в файле нет ни
одного текста, адресованного человеку, и нет ключа с адресом.

Пока канал не подключён, у привычек питания source остаётся `ask`: обещанная и
не работающая автоматика хуже её отсутствия.

Запуск:
    python3 ~/planner/tools/dinner_intake.py --json '{"date":"2026-08-29","last_meal":"19:00","forbidden":false}'
    python3 ~/planner/tools/dinner_intake.py --file <путь к json>
Песочница: PLANNER_TEST_ROOT (данные) + PLANNER_PORT (сервер).

Поля записи:
    date        ГГГГ-ММ-ДД, день ужина
    last_meal   ЧЧ:ММ, время последнего приёма пищи
    forbidden   true, если в этот день было что-то из списка запрещённого
    note        свободный комментарий, в отметки не идёт
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
from _common import (TRACKER_JSON, PROFILE_JSON, parse_hhmm,  # noqa: E402
                     api_url, assert_write_target, read_resource, write_resource,
                     SandboxMismatch)

# Адрес НЕ вычисляется на импорте: раньше здесь стояло значение по умолчанию
# 8777, и запуск с PLANNER_TEST_ROOT молча уезжал в боевой движок. Теперь адрес
# берётся у гарда, который перед записью доказывает, что за портом песочные
# данные, и отказывается работать, если песочница задана наполовину.
API = api_url("track")

# Привычка -> как считается из записи. Список закрытый: приёмник ставит ТОЛЬКО
# то, что запись физически содержит, и ничего не додумывает
HABIT_LAST_MEAL = "poslednyaya_eda_4h"
HABIT_FORBIDDEN = "spisok_zapreshchennogo"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class IntakeError(Exception):
    pass


def _bedtime():
    try:
        p = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        p = {}


def evaluate(rec):
    """Запись -> {id привычки: True/False}. Ключа нет в записи - строки нет в ответе."""
    marks = {}
    lm = rec.get("last_meal")
    if lm is not None:
        m = parse_hhmm(lm)
        if m is None:
            raise IntakeError("last_meal должен быть ЧЧ:ММ, пришло %r" % (lm,))
        bed = _bedtime()
        gap = bed - m if bed >= m else bed + 24 * 60 - m
        marks[HABIT_LAST_MEAL] = gap >= 4 * 60
    if "forbidden" in rec:
        if not isinstance(rec["forbidden"], bool):
            raise IntakeError("forbidden должен быть true или false")
        marks[HABIT_FORBIDDEN] = not rec["forbidden"]
    return marks


def _read():
    """Читает ровно из того носителя, куда потом и пишет: решает общий гард."""
    return read_resource("track")


def apply_marks(marks, day):
    doc, etag = _read()
    known = {h["id"] for h in doc.get("habits", [])}
    unknown = sorted(set(marks) - known)
    if unknown:
        raise IntakeError("в трекере нет привычек: %s" % ", ".join(unknown))
    log = doc.setdefault("log", {})
    d = log.setdefault(day, {})
    for hid, ok in marks.items():
        # «Не выполнено» пишется явным False, ключ и день из журнала не изымаются:
        # тот же класс, что закрыт в device_sync.apply_marks. Читатели журнала
        # смотрят truthiness, поэтому поведение не меняется, а история цела
        d[hid] = bool(ok)
    doc.pop("rev", None)
    # адрес записи печатает и сторожит общий гард: он же валит прогон, если
    # песочный корень задан, а порт указывает на боевой движок
    write_resource("track", doc, etag)


def main():
    p = argparse.ArgumentParser(description="Приёмник записи об ужине. Наружу не ходит")
    p.add_argument("--json", default=None, help="запись строкой JSON")
    p.add_argument("--file", default=None, help="запись файлом JSON")
    args = p.parse_args()
    raw = None
    if args.json:
        raw = args.json
    elif args.file:
        raw = open(args.file, encoding="utf-8").read()
    else:
        raw = sys.stdin.read()
    try:
        rec = json.loads(raw)
        if not isinstance(rec, dict):
            raise IntakeError("в записи должен быть объект JSON")
        day = rec.get("date")
        if not isinstance(day, str) or not DATE_RE.match(day):
            raise IntakeError("нужна дата ГГГГ-ММ-ДД в поле date")
        marks = evaluate(rec)
        if not marks:
            raise IntakeError("в записи нет ни одного поля, из которого ставится отметка")
        apply_marks(marks, day)
    except SandboxMismatch as exc:
        print("запись остановлена гардом песочницы: %s" % exc, file=sys.stderr)
        sys.exit(2)
    except (IntakeError, ValueError) as exc:
        print("запись не принята: %s" % exc, file=sys.stderr)
        sys.exit(1)
    print("отмечено: %s" % ", ".join(sorted(k for k, v in marks.items() if v)))


if __name__ == "__main__":
    main()
