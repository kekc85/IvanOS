#!/usr/bin/env python3
"""Отметка привычек за день - инструмент ассистента, не владельца.

Зачем существует. Владелец привычки руками не ведёт: в трекере за первые дни
стояло ноль отмеченных дней при живом списке. Диктовка голосом («спал семь,
тренька была, писания вечером не было») должна превращаться в записанный день
за одну команду, иначе трекер снова умрёт.

Как пользуюсь я (каждая строка запускается копипастом как есть):
    habits.py show                                  - что за сегодня отмечено, по блокам
    habits.py show --date 2026-08-26                - то же за прошлый день (бэкафилл)
    habits.py ask                                   - что на сегодня ещё открыто
    habits.py set lichnaya_privychka_2,utrennyaya_voda_1l  - отметить сделанным
    habits.py set --off nol_alkogolya               - снять отметку
    habits.py set вода,писание_утро                 - то же по русским словам (см. ALIASES)
    habits.py set сон,треня,писание                 - двусмысленное слово и машинная строка:
                                                      команда НИЧЕГО не пишет и объясняет, почему
    habits.py adherence                             - мета-порог 85% по ДОСТУПНЫМ сегодня единицам

Пишет через HTTP-API движка с If-Match, чтобы не обойти оптимистичную блокировку
сервера и не затереть правку, сделанную во вкладке параллельно. Если сервер не
поднят - пишет файл напрямую, но только после бэкапа рядом с датой в имени.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
from _common import (IS_SANDBOX, TASKS_DIR, api_port, api_url,  # noqa: E402
                     read_resource, write_resource, SandboxMismatch)

# Раньше здесь стояли СВОИ переменные (PLANNER_PORT и PLANNER_DATA), и про
# PLANNER_TEST_ROOT инструмент не знал вовсе: запуск «в песочнице» уезжал и
# запросом в боевой движок, и фолбэком в боевой файл. Теперь и адрес, и путь
# данных берутся из общего гарда, который знает обе песочницы разом.
PORT = api_port()
API = api_url("track")
TASKS = str(TASKS_DIR) if IS_SANDBOX else os.path.expanduser(
    os.environ.get("PLANNER_DATA", "~/planner-data"))
TRACKER = os.path.join(TASKS, "tracker.json")

# Восемь блоков жизни. Тот же набор и в том же порядке продублирован ещё на ДВУХ
# поверхностях, и они обязаны меняться вместе, иначе привычка падает в «Прочее»
# именно здесь - в инструменте, которым день отмечается диктовкой:
#   static/tab-track.js -> HABIT_GROUPS
#   кит ученикам        -> собирается скриптом build.sh из того же движка
GROUP_TITLES = {
    "sleep": "Сон", "light": "Свет", "body": "Тело", "food": "Питание",
    "focus": "Фокус", "health_metrics": "Показатели", "supplements": "Добавки",
    "spirit": "Дух", "": "Прочее",
}
GROUP_ORDER = ["sleep", "light", "body", "food", "focus", "health_metrics",
               "supplements", "spirit", ""]

# Источники, где галочку ставит МАШИНА. Руками они не отмечаются никогда: иначе
# трекер зеленеет со слов там, где обещал показания прибора
MACHINE_SOURCES = ("auto", "device", "device", "engine")

# Русские слова из живой диктовки -> id привычки. Одно слово может вести к одной
# привычке; двусмысленное («писание») требует уточнения утро/вечер и здесь не
# сокращается специально - лучше переспросить, чем поставить не ту галочку.
ALIASES = {
    # сон и подъём
    "отбой": "otboy_v_odno_vremya", "лёг": "otboy_v_odno_vremya", "лег": "otboy_v_odno_vremya",
    "подъём": "podyem_v_odno_vremya", "подъем": "podyem_v_odno_vremya", "встал": "podyem_v_odno_vremya",
    "пульс": "puls_pokoya_pered_snom",
    "экраны": "ekrany_off_60_min", "экран": "ekrany_off_60_min", "виндаун": "ekrany_off_60_min",
    # свет
    "свет": "utrenniy_svet", "улица": "utrenniy_svet", "солнце": "utrenniy_svet",
    "ночьсвет": "zapret_yarkogo_sveta_22_04", "верхнийсвет": "zapret_yarkogo_sveta_22_04",
    # тело
    "тренировка": "trenirovka_6_dney", "тренька": "trenirovka_6_dney", "спорт": "trenirovka_6_dney",
    "активность": "minimum_20_min_aktivnosti", "двадцать": "minimum_20_min_aktivnosti",
    "хрв": "hrv_ezhednevno", "hrv": "hrv_ezhednevno",
    # питание
    "еда": "poslednyaya_eda_4h", "ужин": "poslednyaya_eda_4h", "последняя": "poslednyaya_eda_4h",
    "кофе": "kofe_otsechka_do_11", "отсечка": "kofe_otsechka_do_11",
    "чашка": "pervaya_chashka_90_120", "перваячашка": "pervaya_chashka_90_120",
    "вода": "utrennyaya_voda_1l", "литр": "utrennyaya_voda_1l",
    "алкоголь": "nol_alkogolya", "трезвость": "nol_alkogolya",
    # фокус
    "телефон": "bez_telefona_na_trenirovke",
    "ссоры": "bez_ssor_posle_17", "мир": "bez_ssor_posle_17",
    "запрещённое": "spisok_zapreshchennogo", "запрещенное": "spisok_zapreshchennogo",
    "список": "spisok_zapreshchennogo",
    # показатели и дух
    "рот": "gigiena_rta", "зубы": "gigiena_rta", "нить": "gigiena_rta",
}

# Слова, которые ведут БОЛЬШЕ ЧЕМ К ОДНОЙ строке. Молча выбрать одну из них значит
# поставить галочку не той привычке, поэтому инструмент переспрашивает и не пишет
# ничего. Решение автора инструмента, оно остаётся и на новом списке.
AMBIGUOUS = {
    "сон": ("otboy_v_odno_vremya", "podyem_v_odno_vremya"),
    "спал": ("otboy_v_odno_vremya", "podyem_v_odno_vremya"),
    "утро": ("utrenniy_svet", "utrennyaya_voda_1l"),
    "вечер": ("ekrany_off_60_min", "bez_ssor_posle_17"),
    "треня": ("trenirovka_6_dney", "minimum_20_min_aktivnosti"),
}



def fetch():
    """(данные, etag). etag=None означает файловый режим записи.

    Носитель выбирает общий гард песочницы: раньше здесь стоял свой urlopen с
    боевым портом по умолчанию, и прогон «в песочнице» читал боевые данные.
    """
    return read_resource("track")


def store(data, etag):
    """Запись трекера. Адрес печатает и сторожит общий гард песочницы."""
    try:
        return write_resource("track", data, etag)
    except SandboxMismatch as exc:
        msg = str(exc)
        if msg.startswith("движок отклонил запись: 409"):
            sys.exit("КОНФЛИКТ: трекер изменили параллельно. Перечитай и повтори.")
        raise


def active_habits(data):
    return [h for h in data.get("habits", []) if not h.get("archived")]


def by_groups(habits):
    out = []
    for g in GROUP_ORDER:
        rows = [h for h in habits if (h.get("group") or "") == g]
        if rows:
            out.append((GROUP_TITLES[g], rows))
    return out


def resolve(tokens, habits):
    """Токены (id или русское слово) -> (список id, список вопросов на уточнение).

    Неопознанное валит команду: молча проглоченное слово = не поставленная галочка,
    которую я потом сочту поставленной. Двусмысленное слово команду НЕ валит, но и
    галочку не ставит: оно возвращается вопросом, а запись целиком отменяется.
    Так `set сон,треня,писание` из докстринга не падает и не метит чужую строку."""
    ids = {h["id"] for h in habits}
    out, bad, ask = [], [], []
    for raw in tokens:
        t = raw.strip().lower()
        if not t:
            continue
        if t in ids:
            out.append(t)
        elif t in AMBIGUOUS:
            live = [i for i in AMBIGUOUS[t] if i in ids]
            if len(live) > 1:
                ask.append("«%s» - это что из: %s?" % (t, ", ".join(live)))
            elif live:
                out.append(live[0])
            else:
                bad.append(raw)
        elif t in ALIASES and ALIASES[t] in ids:
            out.append(ALIASES[t])
        else:
            bad.append(raw)
    if bad:
        sys.exit("не понял: %s\nдоступны id: %s" % (", ".join(bad), ", ".join(sorted(ids))))
    return out, ask


def cmd_adherence(args):
    """Мета-порог 85 процентов считается по ДОСТУПНЫМ сегодня единицам, а не по
    всему списку. Пять привычек прибора и одна движковая до первого входа владельца
    в Прибор недоступны: считать их в знаменатель значит красить порог красным по
    конструкции с первого дня, а не по поведению владельца."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
    from _common import available_habits, day_adherence, device_state
    data, _ = fetch()
    rows = available_habits(data, args.date)
    done, total, pct = day_adherence(data, args.date)
    print("состояние данных прибора: %s" % device_state(data))
    print("доступных единиц дня: %d из %d активных"
          % (total, len(active_habits(data))))
    print("adherence_85 за %s: %d из %d = %d%% (порог 85%%, %s)"
          % (args.date, done, total, pct, "взят" if pct >= 85 else "не взят"))
    for h in rows:
        mark = "[x]" if (data.get("log") or {}).get(args.date, {}).get(h["id"]) else "[ ]"
        print("  %s %s" % (mark, h["id"]))


def cmd_show(args):
    """Показ дня. Знаменатель тот же, что у ритуалов: ДОСТУПНЫЕ сегодня единицы.

    Раньше здесь печаталось «отмечено 0 из 23» рядом с «0 из 17 доступных» в
    вечернем ритуале, и машинные строки рисовались пустыми галочками `[ ]`, хотя
    данных прибора нет вовсе. Пустая галочка читается как «не сделал», а это
    враньё: строку владелец физически не может закрыть до входа в Прибор.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
    from _common import available_habits, device_state
    data, _ = fetch()
    habits = active_habits(data)
    avail = {h["id"] for h in available_habits(data, args.date)}
    day = args.date
    log = (data.get("log") or {}).get(day, {})
    done_n = sum(1 for h in habits if h["id"] in avail and log.get(h["id"]))
    print("== %s · отмечено %d из %d доступных сегодня (активных в списке %d) =="
          % (day, done_n, len(avail), len(habits)))
    print("   состояние данных прибора: %s" % device_state(data))
    for title, rows in by_groups(habits):
        print("\n%s" % title)
        for h in rows:
            if log.get(h["id"]):
                mark = "[x]"
            elif h["id"] in avail:
                mark = "[ ]"
            else:
                mark = "[-]"          # вне знаменателя дня: данных нет либо строка не ежедневная
            src = {"auto": "сама", "ask": "спрошу", "device": "трекер",
                   "device": "Прибор", "engine": "движок"}.get(h.get("source"), "")
            print("  %s %-32s %-8s %s" % (mark, h["name"], src, h["id"]))
    print("\n[x] отмечено · [ ] доступно и открыто · [-] вне знаменателя дня "
          "(нет данных прибора, мета-порог или не ежедневная)")


def cmd_ask(args):
    """Что осталось спросить: только source=ask/device и только неотмеченное."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
    from _common import available_habits
    data, _ = fetch()
    log = (data.get("log") or {}).get(args.date, {})
    # 🔴 Множество ТО ЖЕ, что у ритуалов и у шапки вкладки: доступные в этот день.
    # Раньше здесь стоял третий по счёту знаменатель (все активные плюс фильтр по
    # source), и на воскресенье он предлагал строку, привязанную к дням
    # тренировок, которую вечерний ритуал в тот же день не спрашивал.
    # Спрашиваем ТОЛЬКО то, что владелец правда отмечает сам. Машинные строки
    # (Прибор, движок) сюда не попадают: спросить про них значит попросить владельца
    # сделать руками ровно то, ради чего куплен прибор
    rows = available_habits(data, args.date)
    open_rows = [h for h in rows
                 if h.get("source") == "ask" and not log.get(h["id"])]
    if not open_rows:
        print("за %s всё собрано, спрашивать нечего" % args.date)
        return
    print("Открыто за %s - %d из %d доступных в этот день:"
          % (args.date, len(open_rows), len(rows)))
    for title, rows in by_groups(open_rows):
        print("\n%s" % title)
        for h in rows:
            print("  · %s   [%s]" % (h["name"], h["id"]))


def cmd_set(args):
    data, etag = fetch()
    habits = active_habits(data)
    src = {h["id"]: h.get("source") for h in habits}
    on, ask_on = resolve((args.ids or "").split(","), habits)
    off, ask_off = resolve((args.off or "").split(","), habits)
    ask = ask_on + ask_off
    machine = sorted({i for i in on + off if src.get(i) in MACHINE_SOURCES})
    if ask or machine:
        for q in ask:
            print("уточни: %s" % q)
        for m in machine:
            print("«%s» ставит %s, руками не отмечается - строка пропущена"
                  % (m, {"device": "прибор Прибор", "engine": "сам движок"}.get(src.get(m), src.get(m))))
        print("ничего не записано: сначала уточни, потом повтори команду")
        return
    both = set(on) & set(off)
    if both:
        sys.exit("одна привычка и в set, и в --off: %s" % ", ".join(sorted(both)))
    if not on and not off:
        sys.exit("нечего ставить: передай id/слова или --off")

    log = data.setdefault("log", {})
    day = log.setdefault(args.date, {})
    for hid in on:
        day[hid] = True
    # 🔴 Снятие отметки пишет явный False и НЕ изымает ключ, а пустой день НЕ
    # изымается из журнала. Прежняя форма (`day.pop` плюс `log.pop`) стирала
    # историю владельца его же командой: снял единственную отметку дня - и день
    # переставал существовать в журнале, отличить «не было ответа» от «день не
    # вёлся» становилось нечем. Все читатели журнала смотрят truthiness, поэтому
    # поведение снаружи прежнее, а история цела. Правило владельца номер ноль.
    for hid in off:
        day[hid] = False

    where = store(data, etag)
    names = {h["id"]: h["name"] for h in habits}
    if on:
        print("+ %s" % " · ".join(names[i] for i in on))
    if off:
        print("- %s" % " · ".join(names[i] for i in off))
    # тот же знаменатель, что у ритуалов и у шапки вкладки: доступные сегодня
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rituals"))
    from _common import available_habits
    avail = {h["id"] for h in available_habits(data, args.date)}
    day_log = (data.get("log", {}).get(args.date) or {})
    now_done = sum(1 for i in avail if day_log.get(i))
    print("%s: %d из %d доступных сегодня · %s" % (args.date, now_done, len(avail), where))


def valid_date(v):
    """Дата валидируется ЗДЕСЬ, а не на записи. Раньше кривое значение доезжало до
    файла ключом журнала, и документ переставал проходить схему сервера: одна
    опечатка запирала сохранение всего трекера."""
    try:
        date.fromisoformat(v)
    except ValueError:
        raise argparse.ArgumentTypeError("нужна дата ГГГГ-ММ-ДД, пришло %r" % v)
    return v


def main():
    p = argparse.ArgumentParser(description="Отметка привычек за день")
    # --date стоит И на верхнем парсере, И на каждой подкоманде. Причина
    # практическая: собственная документация писала `show --date 2026-08-26`, а
    # argparse валил такую форму на неизвестном аргументе. Теперь запускаются обе.
    p.add_argument("--date", default=date.today().isoformat(), type=valid_date,
                   help="день, по умолчанию сегодня")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="что отмечено за день")
    s.add_argument("--date", dest="date_sub", default=None, type=valid_date,
                  help="день, по умолчанию сегодня")
    s.set_defaults(func=cmd_show)

    a = sub.add_parser("ask", help="что осталось спросить за день")
    a.add_argument("--date", dest="date_sub", default=None, type=valid_date,
                  help="день, по умолчанию сегодня")
    a.set_defaults(func=cmd_ask)

    ad = sub.add_parser("adherence", help="мета-порог по доступным сегодня единицам")
    ad.add_argument("--date", dest="date_sub", default=None, type=valid_date,
                  help="день, по умолчанию сегодня")
    ad.set_defaults(func=cmd_adherence)

    st = sub.add_parser("set", help="отметить сделанным")
    st.add_argument("ids", nargs="?", default="", help="id или русские слова через запятую")
    st.add_argument("--off", default="", help="снять отметку")
    st.add_argument("--date", dest="date_sub", default=None, type=valid_date,
                  help="день, по умолчанию сегодня")
    st.set_defaults(func=cmd_set)

    args = p.parse_args()
    # подкоманда своим --date перебивает верхний, иначе оба вида записи разошлись бы
    if getattr(args, "date_sub", None):
        args.date = args.date_sub
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except SandboxMismatch as exc:
        print("запись остановлена гардом песочницы: %s" % exc, file=sys.stderr)
        sys.exit(2)
