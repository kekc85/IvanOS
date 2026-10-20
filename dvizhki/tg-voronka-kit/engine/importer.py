"""Импортёр + валидатор воронки против эталона.

Повторяет логику benchmark.py: файл принимается движком, только если совпадает
с эталоном по структуре (14 узлов, 11 связей, топология и тайминги) и отличается
лишь разрешённой дельтой (код-слово, тексты A0/B0, ссылка статьи, слово в D7).
Брак не загружается в прод.

Второй разрешённый шаблон - «прямая продажа» (воронка СОБЫТИЕ): 4 узла
A0/C1/C2/D7, дожим стартует от входа, без магнита B0/TECH. A0 сразу несёт
inline-кнопку на событие; клик по ней движок и так превращает в registered
и гасит дожим (interpreter, ветка click).
"""
from __future__ import annotations
import json, os, re
from .model import Funnel, deeplink_key
from engine.model import tg_url

HERE = os.path.dirname(os.path.abspath(__file__))
ETALON_PATH = os.path.join(HERE, "..", "funnels", "etalon.json")

# Telegram HTML: движок шлёт всё с parse_mode=HTML. Непарный/незакрытый тег →
# Telegram отклоняет sendMessage (BadRequest) → сообщение НЕ уходит, джоба уходит
# в retry→failed молча. Ловим брак на импорте, чтобы битая воронка не загрузилась.
_TG_HTML_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
                 "a", "code", "pre", "span", "tg-spoiler", "blockquote"}
_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)(?:\s[^>]*)?>")


def _html_errors(text: str, node_key: str) -> list[str]:
    """Проверка баланса Telegram-HTML тегов в тексте узла (стек открытых/закрытых)."""
    errs, stack = [], []
    for m in _TAG_RE.finditer(text or ""):
        closing, tag = m.group(1), m.group(2).lower()
        if tag not in _TG_HTML_TAGS:
            errs.append(f"{node_key}: тег <{tag}> не поддержан Telegram HTML")
            continue
        if not closing:
            stack.append(tag)
        elif not stack or stack[-1] != tag:
            errs.append(f"{node_key}: </{tag}> без парного открытия или нарушена вложенность")
        else:
            stack.pop()
    if stack:
        errs.append(f"{node_key}: незакрытые теги {stack}")
    return errs

EXPECT_NODES = 14
EXPECT_EDGES = 11
REQUIRED_KEYS = {"A0", "B0", "TECH", "C1", "C2", "C3", "C4",
                 "D1", "D2", "D3", "D4", "D5", "D6", "D7"}

# Расширение «эталон + R-пуши»: R1/R2 напоминают нажать
# «Забрать» тем, кто вошёл по слову и не забрал гайд. Топология и тайминги
# зашиты жёстко: A0 +1ч → R1, R1 +23ч → R2. Глушение после выдачи B0 - в
# interpreter (тег magnet_taken_<воронка>), ночной перенос - WINDOWED_NODES.
MAGNET_PUSH_KEYS = REQUIRED_KEYS | {"R1", "R2"}
MAGNET_R_EDGES = [("A0", "R1", "1", 3600, "", ""),
                  ("R1", "R2", "23", 3600, "", "")]

# Шаблон «фронт-цепочка событие»: топология и тайминги зашиты жёстко.
# A0 выдача сразу → K1 +3ч → K2 +24ч → K3 +24ч; окно 10-21 МСК кладёт движок.
DIRECT_KEYS = {"A0", "K1", "K2", "K3"}
DIRECT_EDGE_SIG = sorted([
    ("A0", "K1", "3", 3600, "", ""),      # +3 часа после выдачи
    ("K1", "K2", "24", 3600, "", ""),     # +сутки
    ("K2", "K3", "24", 3600, "", ""),     # +сутки, финал
])
# 🔴 Кнопки ВНУТРИ фронт-бота ведут на САЙТ регистрации. Диплинк на этого же
# бота тут был бы рекурсией: человек в боте жмёт кнопку и попадает в того же
# бота, до регистрации не доходит, а клик ставит registered и глушит дожим.
# Правило «весь трафик события на бота» - для ВНЕШНИХ поверхностей (C/D-дожимы
# соседнего бота, конструктор воронок, посты).
EVENT_URL = "https://author.ru/event/"
# Фронт-цепочка живого события: вход для тех, у кого сайт не грузится -
# «регистрация» = вступление в закрытый канал, кнопки ведут туда
LIVE_STAFF_URL = tg_url("+INVITE")
FRONT_BUTTON_URLS = {EVENT_URL, LIVE_STAFF_URL}

# Welcome-шаблоны (после регистрации / после оплаты VIP). Кнопки несут плейсхолдеры
# {КАБИНЕТ}/{ОПЛАТА}/{АНКЕТА} - реальные ссылки подставляет Runtime из .env;
# пока ссылок нет, воронка не грузится (см. runtime._load_all).
WELCOME_KEYS = {"A1", "A11", "A12", "A2", "A4", "A5", "A6"}
WELCOME_EDGE_SIG = sorted([
    ("A1", "A11", "15", 60, "", ""),      # +15 мин: подготовка
    ("A11", "A12", "150", 60, "", ""),    # +2.5 ч: урок 1
    ("A12", "A2", "1", 3600, "", ""),     # +1 ч: апселл VIP (~4 ч от реги)
    ("A2", "A4", "14", 3600, "", ""),     # +14 ч: финал подарка (~18 ч от реги)
    ("A4", "A5", "10", 3600, "", ""),     # +10 ч: анкета (~день 2)
    ("A5", "A6", "72", 3600, "", ""),     # +72 ч: последний зов (~день 5)
])
# Welcome живого события: 5 узлов, ровно 2 VIP-касания (A2 полный питч +
# A6 короткий финал), остальное - польза (как взять максимум от участия).
# Отдельный набор ключей, чтобы не путать с
# evergreen-шаблоном WELCOME (7 узлов, дуга 4.2 суток) - у них разные классы.
LIVEWELCOME_KEYS = {"A1", "A11", "A2"}
LIVE_WELCOME_EDGE_SIG = sorted([
    ("A1", "A11", "15", 60, "", ""),      # +15 мин: как взять максимум
    ("A11", "A2", "45", 60, "", ""),      # +45 мин (≈1 ч от реги): VIP пока горячий, дальше тишина
])
# VIP-welcome живого события: B2 через +3 ч (всё решается в первые часы),
# VIPWELCOME первого запуска остаётся на +24 ч - валидатор принимает обе.
LIVEVIP_EDGE_SIG = sorted([
    ("B1", "B2", "3", 3600, "", ""),
])
VIPWELCOME_KEYS = {"B1", "B2"}
VIPWELCOME_EDGE_SIG = sorted([
    ("B1", "B2", "24", 3600, "", ""),     # +24 ч: бронь стратсессии
])

# Расширенный welcome: кружок, подарки (A12/B3) и VIP-питч. Сигнатуры сняты
# с эталонной воронки этого шаблона.
KONCWELCOME_KEYS = {"A1", "A11", "A12", "A2"}
KONC_WELCOME_EDGE_SIG = sorted([
    ("A1", "A11", "15", 60, "", ""),     # +15 мин: как прийти за результатом
    ("A11", "A12", "30", 60, "", ""),    # +30 мин: два подарка о Клоде + антибан
    ("A12", "A2", "15", 60, "", ""),     # +15 мин (≈1 ч от реги): единственный VIP-питч
])
KONCVIP_KEYS = {"B1", "B2", "B3"}
KONCVIP_EDGE_SIG = sorted([
    ("B1", "B2", "3", 3600, "", ""),     # +3 ч: как взять максимум от VIP
    ("B2", "B3", "30", 60, "", ""),      # +30 мин: два подарка
])
# Welcome события, evergreen-дожим v2 (7 узлов): дуга ~8.3 суток.
LIVEWELCOME7_KEYS = {"A1", "A2", "A3", "A4", "A5", "A6", "A7"}
LIVE_WELCOME7_EDGE_SIG = sorted([
    ("A1", "A2", "15", 60, "", ""),
    ("A2", "A3", "45", 60, "", ""),
    ("A3", "A4", "1", 86400, "", ""),
    ("A4", "A5", "2", 86400, "", ""),
    ("A5", "A6", "3", 86400, "", ""),
    ("A6", "A7", "2", 86400, "", ""),
])
LIVEVIP7_KEYS = {"B1", "B2", "B3", "B4", "B5", "B6", "B7"}
LIVEVIP7_EDGE_SIG = sorted([
    ("B1", "B2", "3", 3600, "", ""),
    ("B2", "B3", "21", 3600, "", ""),
    ("B3", "B4", "3", 86400, "", ""),
    ("B4", "B5", "6", 86400, "", ""),
    ("B5", "B6", "3", 86400, "", ""),
    ("B6", "B7", "2", 86400, "", ""),
])

# Дуга ПРОГРАММА - open sale: вход по UTM-ссылке, бот сразу даёт сайт
# программы, дожим до анкеты, дедлайн в последний день окна продаж.
# Вход по код-слову, кнопки ведут ТОЛЬКО на сайт программы или анкету заявки.
# Три допустимые формы одной воронки:
#   боевая     A0 → P1 +30 мин → P2 +2.5 ч (клетка окна, будни open sale)
#   финальная  A0 → P1 +20 мин → P2 +40 мин (свап в пятницу вечером, короткая)
#   закрытая   один узел A0 без связей (свап после дедлайна: «приём закрыт»)
# Окно отправки P-узлов 10-23 МСК кладёт interpreter (PROG_WINDOWED).
PROGRAMMA_KEYS = {"A0", "P1", "P2"}
PROGRAMMA_CLOSED_KEYS = {"A0"}
PROGRAMMA_EDGE_SIGS = [
    sorted([("A0", "P1", "30", 60, "", ""),
            ("P1", "P2", "150", 60, "", "")]),
    sorted([("A0", "P1", "20", 60, "", ""),
            ("P1", "P2", "40", 60, "", "")]),
]
PROGRAMMA_URL_PREFIXES = ("https://author.com/programma/",
                          "https://author.com/anketa/")


def _validate_welcome(data, keys_set, edge_sigs) -> list[str]:
    """Валидация welcome-шаблонов: топология/тайминги + текст, HTML и кнопка у узлов."""
    errs = []
    if len(data.get("messages", [])) != len(keys_set):
        errs.append(f"узлов {len(data.get('messages', []))}, ждём {len(keys_set)}")
    try:
        if _edge_signature(data) not in edge_sigs:
            errs.append("топология/тайминги связей не совпадают ни с одним welcome-шаблоном")
    except KeyError:
        errs.append("связь ссылается на несуществующий узел")
    for m in data.get("messages", []):
        key = m["description"].split(" ", 1)[0].strip()
        if not (m.get("answer") or "").strip():
            errs.append(f"{key}: пустой текст")
        errs += _html_errors(m.get("answer") or "", key)
        try:
            btns = json.loads(m.get("buttons") or "[]")
        except Exception:
            errs.append(f"{key}: не разобрать кнопки")
            continue
        if not any((b.get("url") or "").strip() for b in btns):
            errs.append(f"{key}: нет url-кнопки")
    return errs


def _edge_signature(data) -> list:
    """Топология+тайминги связей по desc-ключам (без id)."""
    by_id = {m["id"]: m["description"].split(" ", 1)[0].strip() for m in data["messages"]}
    sigs = []
    for c in data["connections"]:
        sigs.append((
            by_id[c["message_a_id"]], by_id[c["message_b_id"]],
            str(c.get("timeout", "")), c.get("timeout_type", 1),
            c.get("send_time", ""), c.get("send_date", ""),
        ))
    return sorted(sigs)


def _validate_direct(data) -> list[str]:
    """Валидация шаблона «фронт-цепочка событие» (A0 → K1 → K2 → K3)."""
    errs = []
    if len(data.get("messages", [])) != len(DIRECT_KEYS):
        errs.append(f"узлов {len(data.get('messages', []))}, ждём {len(DIRECT_KEYS)}")
    if len(data.get("connections", [])) != len(DIRECT_EDGE_SIG):
        errs.append(f"связей {len(data.get('connections', []))}, ждём {len(DIRECT_EDGE_SIG)}")

    try:
        if _edge_signature(data) != DIRECT_EDGE_SIG:
            errs.append("топология/тайминги связей не совпадают с шаблоном фронт-цепочки")
    except KeyError:
        errs.append("связь ссылается на несуществующий узел")

    idx = {m["description"].split(" ", 1)[0].strip(): m for m in data.get("messages", [])}
    a0 = idx.get("A0", {})
    cond = (a0.get("condition") or "").strip()
    if not cond or cond.startswith("#{") or cond.startswith("link_was_pressed"):
        errs.append("у A0 нет боевого код-слова")
    if a0.get("message_type") != 4:
        errs.append("A0 не триггер (message_type != 4)")

    # каждый узел обязан нести текст и кнопку на сайт события
    # (opt-out кнопка в K3 опциональна: финал можно сделать личным письмом без неё)
    for key in ("A0", "K1", "K2", "K3"):
        m = idx.get(key)
        if not m:
            continue
        if not (m.get("answer") or "").strip():
            errs.append(f"{key}: пустой текст")
        errs += _html_errors(m.get("answer") or "", key)
        try:
            btns = json.loads(m.get("buttons") or "[]")
        except Exception:
            errs.append(f"{key}: не разобрать кнопки")
            continue
        urls = [b.get("url", "") for b in btns if b.get("url")]
        if not any(u in FRONT_BUTTON_URLS for u in urls):
            errs.append(f"{key}: нет кнопки на сайт/канал ({sorted(FRONT_BUTTON_URLS)})")

    return errs


def _validate_programma(data, closed: bool = False) -> list[str]:
    """Валидация дуги ПРОГРАММА (open sale): код-слово A0, тексты, кнопки на сайт/анкету."""
    errs = []
    keys_set = PROGRAMMA_CLOSED_KEYS if closed else PROGRAMMA_KEYS
    if len(data.get("messages", [])) != len(keys_set):
        errs.append(f"узлов {len(data.get('messages', []))}, ждём {len(keys_set)}")
    if closed:
        if data.get("connections"):
            errs.append("закрытая форма ПРОГРАММА не несёт связей")
    else:
        try:
            if _edge_signature(data) not in PROGRAMMA_EDGE_SIGS:
                errs.append("топология/тайминги связей не совпадают с шаблоном ПРОГРАММА")
        except KeyError:
            errs.append("связь ссылается на несуществующий узел")

    idx = {m["description"].split(" ", 1)[0].strip(): m for m in data.get("messages", [])}
    a0 = idx.get("A0", {})
    cond = (a0.get("condition") or "").strip()
    if not cond or cond.startswith("#{") or cond.startswith("link_was_pressed"):
        errs.append("у A0 нет боевого код-слова")
    if a0.get("message_type") != 4:
        errs.append("A0 не триггер (message_type != 4)")

    # каждый узел несёт текст и кнопку на сайт программы или анкету заявки -
    # диплинк t.me тут был бы рекурсией (тот же канон, что у фронт-цепочки)
    for key in sorted(keys_set):
        m = idx.get(key)
        if not m:
            continue
        if not (m.get("answer") or "").strip():
            errs.append(f"{key}: пустой текст")
        errs += _html_errors(m.get("answer") or "", key)
        try:
            btns = json.loads(m.get("buttons") or "[]")
        except Exception:
            errs.append(f"{key}: не разобрать кнопки")
            continue
        urls = [b.get("url", "") for b in btns if b.get("url")]
        if not any(u.startswith(PROGRAMMA_URL_PREFIXES) for u in urls):
            errs.append(f"{key}: нет кнопки на сайт программы или анкету ({PROGRAMMA_URL_PREFIXES})")
    return errs


def _validate_magnet_push(data, etalon) -> list[str]:
    """Валидация шаблона «эталон + R-пуши»: 16 узлов, 13 связей.

    R1/R2 проверяются как пассивные узлы с reply-кнопкой «Забрать» и жёсткой
    топологией MAGNET_R_EDGES; остальное обязано совпадать с эталоном так же,
    как в базовой ветке (счётчики, топология, B0↔TECH, HTML-баланс).
    """
    errs = []
    if len(data.get("messages", [])) != EXPECT_NODES + 2:
        errs.append(f"узлов {len(data.get('messages', []))}, ждём {EXPECT_NODES + 2}")
    if len(data.get("connections", [])) != EXPECT_EDGES + 2:
        errs.append(f"связей {len(data.get('connections', []))}, ждём {EXPECT_EDGES + 2}")

    expected_sig = sorted(_edge_signature(etalon) + MAGNET_R_EDGES)
    try:
        if _edge_signature(data) != expected_sig:
            errs.append("топология/тайминги связей не совпадают с шаблоном «эталон + R-пуши»")
    except KeyError:
        errs.append("связь ссылается на несуществующий узел")

    idx = {m["description"].split(" ", 1)[0].strip(): m for m in data.get("messages", [])}
    for key in ("R1", "R2"):
        m = idx.get(key, {})
        if not (m.get("answer") or "").strip():
            errs.append(f"{key}: пустой текст")
        if (m.get("condition") or "") != "#{none}" or m.get("message_type") != 0:
            errs.append(f"{key}: не пассивный узел (condition/message_type)")
        try:
            btns = json.loads(m.get("buttons") or "[]")
        except Exception:
            btns = None
        if not (btns and len(btns) == 1 and btns[0].get("text") == "Забрать"
                and btns[0].get("type") == "reply"):
            errs.append(f"{key}: нет reply-кнопки «Забрать»")

    a0 = idx.get("A0", {})
    cond = (a0.get("condition") or "").strip()
    if not cond or cond.startswith("#{") or cond.startswith("link_was_pressed"):
        errs.append("у A0 нет боевого код-слова")

    if "B0" in idx and "TECH" in idx:
        try:
            b0_url = json.loads(idx["B0"]["buttons"])[0]["url"]
            if idx["TECH"]["condition"] != f"link_was_pressed {b0_url}":
                errs.append("ссылка TECH не совпадает с кнопкой B0")
        except Exception:
            errs.append("не разобрать кнопку B0 / условие TECH")

    for k, m in idx.items():
        errs += _html_errors(m.get("answer") or "", k)

    return errs


def validate(path: str) -> list[str]:
    errs = []
    etalon = json.load(open(ETALON_PATH, encoding="utf-8"))
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"не читается JSON: {e}"]

    keys = {m["description"].split(" ", 1)[0].strip() for m in data.get("messages", [])}
    if keys == DIRECT_KEYS:
        return _validate_direct(data)
    if keys == WELCOME_KEYS:
        return _validate_welcome(data, WELCOME_KEYS, [WELCOME_EDGE_SIG])
    if keys == LIVEWELCOME_KEYS:
        return _validate_welcome(data, LIVEWELCOME_KEYS, [LIVE_WELCOME_EDGE_SIG])
    if keys == VIPWELCOME_KEYS:
        return _validate_welcome(data, VIPWELCOME_KEYS,
                                 [VIPWELCOME_EDGE_SIG, LIVEVIP_EDGE_SIG])
    if keys == KONCWELCOME_KEYS:
        return _validate_welcome(data, KONCWELCOME_KEYS, [KONC_WELCOME_EDGE_SIG])
    if keys == KONCVIP_KEYS:
        return _validate_welcome(data, KONCVIP_KEYS, [KONCVIP_EDGE_SIG])
    if keys == LIVEWELCOME7_KEYS:
        return _validate_welcome(data, LIVEWELCOME7_KEYS, [LIVE_WELCOME7_EDGE_SIG])
    if keys == LIVEVIP7_KEYS:
        return _validate_welcome(data, LIVEVIP7_KEYS, [LIVEVIP7_EDGE_SIG])
    if keys == PROGRAMMA_KEYS:
        return _validate_programma(data)
    if keys == PROGRAMMA_CLOSED_KEYS:
        return _validate_programma(data, closed=True)
    if keys == MAGNET_PUSH_KEYS:
        return _validate_magnet_push(data, etalon)

    if len(data.get("messages", [])) != EXPECT_NODES:
        errs.append(f"узлов {len(data.get('messages', []))}, ждём {EXPECT_NODES}")
    if len(data.get("connections", [])) != EXPECT_EDGES:
        errs.append(f"связей {len(data.get('connections', []))}, ждём {EXPECT_EDGES}")

    keys = {m["description"].split(" ", 1)[0].strip() for m in data.get("messages", [])}
    missing = REQUIRED_KEYS - keys
    if missing:
        errs.append(f"нет узлов: {sorted(missing)}")

    # Альтернативная топология магнит-воронки: дожим стартует от ВЫДАЧИ (B0->C1),
    # а не от клика по кнопке (TECH->C1). Нужна там, где кнопка B0 - само целевое
    # действие (вступить в закрытый канал): при эталонной схеме C1-D7 получали только
    # те, кто уже вступил, т.е. дожим молчал для тех, кого надо дожимать.
    # Вступившим узлы C1-D7 гасит тег in_staff (interpreter.SALES_NODES).
    _et_sig = _edge_signature(etalon)
    ALT_B0_START_SIG = sorted(
        [("B0", b, t, tt, c, s) if a == "TECH" and b == "C1" else (a, b, t, tt, c, s)
         for (a, b, t, tt, c, s) in _et_sig])
    if _edge_signature(data) not in (_et_sig, ALT_B0_START_SIG):
        errs.append("топология/тайминги связей не совпадают с эталоном")

    # ссылка B0 и условие TECH должны указывать на один url
    idx = {m["description"].split(" ", 1)[0].strip(): m for m in data.get("messages", [])}
    b0_url = None
    if "B0" in idx and "TECH" in idx:
        try:
            b0_url = json.loads(idx["B0"]["buttons"])[0]["url"]
            if idx["TECH"]["condition"] != f"link_was_pressed {b0_url}":
                errs.append("ссылка TECH не совпадает с кнопкой B0")
        except Exception:
            errs.append("не разобрать кнопку B0 / условие TECH")

    # 🔴 A0 url-кнопка (если есть) должна вести на ТУ ЖЕ статью, что B0 — иначе
    # застрявшая чужая ссылка из каркаса-донора уводит на не ту статью (прецедент
    # собрал воронку НЕЙРОПОИСК из GPT56-каркаса, A0-кнопка осталась на
    # guide-gpt-5-6, человек по первой кнопке попадал на статью про GPT). Гайд-URL
    # у всех кнопок воронки один = URL статьи этой воронки, не донора.
    if b0_url and "A0" in idx:
        try:
            for btn in json.loads(idx["A0"].get("buttons") or "[]"):
                u = btn.get("url")
                if u and u != b0_url and "event" not in u and not deeplink_key(u):
                    errs.append(f"A0-кнопка ведёт на чужой url {u} (ждём {b0_url}) — застрявшая ссылка донора")
        except Exception:
            pass

    # Telegram-HTML баланс тегов во всех текстовых узлах (парсится с parse_mode=HTML)
    for k, m in idx.items():
        errs += _html_errors(m.get("answer") or "", k)

    return errs


def load_valid(path: str) -> Funnel:
    errs = validate(path)
    if errs:
        raise ValueError("воронка не прошла валидацию:\n  - " + "\n  - ".join(errs))
    return Funnel.load(path)
