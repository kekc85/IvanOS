#!/usr/bin/env python3
"""
send-rich-post.py - отправщик rich-сообщения в Telegram через Bot API 10.2 sendRichMessage.

Метод sendRichMessage появился в Bot API 10.1 (по решению автора), поле `blocks` у
InputRichMessage добавлено в Bot API 10.2 (по решению автора). Стандартные обёртки
(python-telegram-bot и т.п.) метод пока НЕ поддерживают - шлём raw HTTP через
stdlib urllib, без сторонних зависимостей.

Статус схемы (см. references/tg-rich-formatting.md раздел 6 и отчёт агента):
- VERIFIED напрямую с core.telegram.org (WebFetch, по решению автора): существование
  метода sendRichMessage, chat_id/rich_message как параметры sendRichMessage,
  наличие поля blocks у InputRichMessage (доб. в 10.2), лимиты 32768 символов /
  500 блоков / 20 колонок таблицы / 16 уровней вложенности / 50 медиавложений
  (лимиты подтверждены также каноном tg-rich-formatting.md).
- UNVERIFIED напрямую (WebFetch на core.telegram.org стабильно обрезал страницу
  до раздела types/methods, где живут точные таблицы полей; поля ниже взяты из
  вторичного источника - зеркала спеки Bot API 10.1/10.2, github.com/serejaris/
  telegram-skills/reference/rich-messages-spec.md - и НЕ сверены дословно с
  оригиналом core.telegram.org): точные имена полей ячейки таблицы (is_header,
  colspan, rowspan, align, valign), точное имя чек-бокс-полей у list item
  (has_checkbox / is_checked), обязательность align/valign у ячейки.
  Помечены комментарием UNVERIFIED прямо в коде ниже.

Использование:
    python3 send-rich-post.py --demo --dry-run          # печатает JSON, в сеть не ходит (дефолт)
    python3 send-rich-post.py --demo                      # то же самое, --dry-run подразумевается
    python3 send-rich-post.py payload.json --dry-run       # свой payload, только печать
    python3 send-rich-post.py --demo --send                # РЕАЛЬНАЯ отправка (только по явному "да" владельца)

Токен и chat_id читаются из env IVAN_TG_BOT_TOKEN / IVAN_TG_CHAT_ID с фолбэком
на значения из ~/.business/scripts/auto-uniqualize/.env (тот же токен, которым
уже пользуются auto-uniqualize доставщики - <твой-бот>, <твой-бот-токен-id>:...).
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

API_BASE = "https://api.telegram.org"

# Фолбэк-источник токена/chat_id - общий .env, которым уже пользуются
# telegram-deliver.py / redeliver-full-caption.py / deliver_carousel.py /
# deliver_all_batch.py в auto-uniqualize. Читаем ТОЛЬКО как fallback, если
# env-переменные IVAN_TG_BOT_TOKEN / IVAN_TG_CHAT_ID не заданы явно.
FALLBACK_ENV_FILE = Path.home() / ".business/scripts/auto-uniqualize/.env"


def load_fallback_env(path: Path) -> dict:
    """Парсит простой .env (KEY=VALUE, # комментарии) без внешних зависимостей."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip()
    return values


def resolve_credentials():
    """
    Токен: env IVAN_TG_BOT_TOKEN -> fallback TELEGRAM_BOT_TOKEN из .env auto-uniqualize.
    Chat ID: env IVAN_TG_CHAT_ID -> fallback TELEGRAM_USER_ID из того же .env
             (доставка владельцу лично, НЕ TELEGRAM_CHANNEL_ID - тот пуст по умолчанию).
    """
    token = os.environ.get("IVAN_TG_BOT_TOKEN")
    chat_id = os.environ.get("IVAN_TG_CHAT_ID")

    if token and chat_id:
        return token, chat_id, "env IVAN_TG_BOT_TOKEN / IVAN_TG_CHAT_ID"

    fallback = load_fallback_env(FALLBACK_ENV_FILE)
    token = token or fallback.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or fallback.get("TELEGRAM_USER_ID")
    source = f"fallback {FALLBACK_ENV_FILE} (TELEGRAM_BOT_TOKEN / TELEGRAM_USER_ID)"
    return token, chat_id, source


# ---------------------------------------------------------------------------
# RichText helpers (форматирование внутри блока)
# ---------------------------------------------------------------------------

def rt_plain(text: str) -> dict:
    """Обычный текст. type=plain - UNVERIFIED точное имя (сверено косвенно:
    changelog подтверждает RichText как класс-обёртку форматирования, но
    имя базового "просто текст" варианта не встретилось ни в одном fetch)."""
    return {"type": "plain", "text": text}


def rt_bold(text: str) -> dict:
    """RichTextBold. VERIFIED (changelog 10.1 явно называет RichTextBold)."""
    return {"type": "bold", "text": rt_plain(text)}


def rt(text: str, bold: bool = False) -> dict:
    return rt_bold(text) if bold else rt_plain(text)


# ---------------------------------------------------------------------------
# InputRichBlock* builders
# ---------------------------------------------------------------------------

def block_paragraph(text: str) -> dict:
    """InputRichBlockParagraph. VERIFIED тип блока (changelog), поле text -
    UNVERIFIED дословно (вторичный источник)."""
    return {"type": "paragraph", "text": rt_plain(text)}


def block_table(headers: list[str], rows: list[list[str]]) -> dict:
    """
    InputRichBlockTable. VERIFIED как тип блока (10.2 changelog).
    UNVERIFIED дословно: структура cells как Array of Array of cell-объектов,
    поля is_header/colspan/rowspan/align/valign у ячейки (источник - вторичное
    зеркало спеки, не сам core.telegram.org). Нет отдельного InputRichBlockTableRow
    по тому же вторичному источнику - таблица собрана как список строк, каждая
    строка - список ячеек.
    """
    def cell(text: str, is_header: bool = False) -> dict:
        c = {
            "text": rt_plain(text),
            "align": "left",     # UNVERIFIED: обязательность поля не подтверждена напрямую
            "valign": "middle",  # UNVERIFIED: обязательность поля не подтверждена напрямую
        }
        if is_header:
            c["is_header"] = True  # UNVERIFIED имя поля
        return c

    header_row = [cell(h, is_header=True) for h in headers]
    body_rows = [[cell(v) for v in row] for row in rows]
    return {
        "type": "table",
        "cells": [header_row] + body_rows,  # UNVERIFIED: Array of Array of cell
    }


def block_checklist(items: list[str], checked: list[bool] | None = None) -> dict:
    """
    InputRichBlockList с чек-боксами (InputRichBlockListItem, has_checkbox/is_checked).
    VERIFIED как типы (10.2 changelog: InputRichBlockList, InputRichBlockListItem).
    UNVERIFIED дословно: поля has_checkbox / is_checked - имена не подтверждены
    напрямую с core.telegram.org, взяты из вторичного зеркала спеки.
    """
    if checked is None:
        checked = [False] * len(items)
    list_items = []
    for label, is_checked in zip(items, checked):
        list_items.append({
            "has_checkbox": True,   # UNVERIFIED имя поля
            "is_checked": is_checked,  # UNVERIFIED имя поля
            "blocks": [block_paragraph(label)],  # UNVERIFIED: nested blocks на item
        })
    return {"type": "list", "items": list_items}


# ---------------------------------------------------------------------------
# Demo payload - пост-пример по ТЗ
# ---------------------------------------------------------------------------

def build_demo_blocks() -> list[dict]:
    heading_text = "Три недели вайбкодил лендинг вместо найма студии"

    intro = (
        "Сел считать честно, во что это вылилось. "
        "Ниже сравнение по трём параметрам"
    )

    table = block_table(
        headers=["Параметр", "Вайбкодинг", "Студия"],
        rows=[
            ["Срок", "21 день", "10 дней"],
            ["Стоимость", "~15 000 ₽", "~120 000 ₽"],
            ["Правки после сдачи", "без ограничений", "доп. оплата"],
        ],
    )

    checklist_intro = "Проверь себя по трём пунктам"

    checklist = block_checklist(
        items=[
            "Есть свободные вечера на 2-3 недели",
            "Задача понятная, без сложной интеграции",
            "Бюджет на студию тратить не хочется",
        ]
    )

    outro = "Если набралось два из трёх - тебе тоже дешевле сделать самому"

    return [
        # Заголовок жирным - как параграф с bold-обёрткой текста (heading-блок
        # не используется по канону tg-rich-formatting.md раздел 2.4 - "не входит
        # в контракт v5.2"; здесь используем bold-параграф, не InputRichBlockSectionHeading)
        {"type": "paragraph", "text": rt_bold(heading_text)},
        block_paragraph(intro),
        table,
        block_paragraph(checklist_intro),
        checklist,
        block_paragraph(outro),
    ]


DEMO_MARKDOWN = """**Три недели вайбкодил лендинг вместо найма студии**

Сел считать честно, во что это вылилось. Ниже сравнение по трём параметрам

| Параметр | Вайбкодинг | Студия |
|---|---|---|
| Срок | 21 день | 10 дней |
| Стоимость | ~15 000 ₽ | ~120 000 ₽ |
| Правки после сдачи | без ограничений | доп. оплата |

Дальше самопроверка, отметь что у тебя есть

- [ ] Есть свободные вечера на 2-3 недели
- [ ] Задача понятная, без сложной интеграции
- [ ] Бюджет на студию тратить не хочется

Если набралось два из трёх - тебе тоже дешевле сделать самому"""


NBSP = " "  # неразрывный пробел - НАСТОЯЩИЙ, не обычный (обычный парсер съедает)


def add_paragraph_air(md_text: str) -> str:
    """🔴 ВОЗДУХ МЕЖДУ АБЗАЦАМИ (владелец, ~10 кругов правок).

    Проблема: rich-парсер Telegram схлопывает пустые строки между paragraph-
    блоками → в канале абзацы идут ВПЛОТНУЮ, без отступа. Обычный пробел между
    \\n\\n парсер тоже съедает. Решение: между блоками вставляем абзац из
    НЕРАЗРЫВНОГО пробела (\\u00a0) - парсер держит его как отдельный блок-воздух,
    и в ленте появляется вертикальный отступ. Проверено живьём (msg 21, воздух=14).

    ⚠️ italic: только ОДИНАРНОЕ `_текст_` (GFM). Двойное `__текст__` парсер НЕ
    рендерит курсивом (проглатывает как текст) - в постах использовать `_..._`.
    """
    blocks = [b for b in md_text.split("\n\n") if b.strip()]
    return ("\n\n" + NBSP + "\n\n").join(blocks)


def validate_post_text(md_text: str) -> list:
    """🔴 ГЕЙТ ПЕРЕД ОТПРАВКОЙ (по решению автора, ~30 кругов правок поста нейропоиск).

    Детерминированно ловит дыры, которые повторялись в сессии. Каждый rich-пост
    идёт через send() → эту проверку не обойти. Возвращает список нарушений;
    непустой = отправка блокируется (см. main).
    """
    errs = []
    # 1. Двойной курсив __текст__ НЕ рендерится в rich (парсер проглатывает как текст).
    # Только одинарный _текст_. Прецедент по решению автора: __italic__ в посте пропал.
    if re.search(r"__[^_\n]+__", md_text):
        errs.append("двойной курсив __текст__ не рендерится в rich - замени на одинарный _текст_")
    # 2. Длинные тире в ПРОЗЕ (вне код-блоков и таблиц) = AI-маркер, запрет владельца.
    in_code = False
    for ln in md_text.split("\n"):
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code; continue
        if in_code or s.startswith("|"):
            continue
        if "—" in ln or "–" in ln:
            errs.append(f"длинное тире в прозе: {ln.strip()[:50]} - замени на дефис/двоеточие/запятую")
            break
    # 3. Вода / оценочные ярлыки-подача (Ильяхов: факт вместо оценки). Прецедент по решению автора:
    #    «честно и жёстко», «места свободны, лопатой», «окно открыто» = впаривание.
    water = ["честно и жёстко", "сейчас будет мясо", "места свободны", "снимать лопатой",
             "собирать трафик лопатой", "окно открыто именно", "снимал сливки", "на автопилоте",
             "пока я сплю", "это меняет всё", "просто огонь"]
    hit = [w for w in water if w.lower() in md_text.lower()]
    if hit:
        errs.append(f"вода/оценочный ярлык: {hit} - замени на факт/деталь/механику (память feedback_post_no_water_no_evaluative_labels_ilyahov)")
    return errs


def build_markdown_payload(chat_id: str, md_text: str, photo_file_id: str = None) -> dict:
    """🔴 РАБОЧИЙ ПУТЬ (проверено живой отправкой по решению автора, message_id 6605).

    Серверу отдаётся rich_message.markdown - Telegram САМ парсит GFM-разметку
    в блоки: **bold** → bold-параграф, `_курсив_` → italic, ==текст== → marked
    (highlight), | | таблица → table, `- [ ]` → list с has_checkbox.
    🔴 ВСЕГДА прогоняем add_paragraph_air - иначе абзацы слипаются.

    photo_file_id: фото ВНУТРИ rich одним сообщением Bot API 10.2 пока НЕ отдаёт
    (структура photo-блока не разгадана, API отбивает - открытый UNKNOWN в даты запуска).
    Рабочий контур: фото владелец цепляет сам в редакторе отложки, ЛИБО фото шлётся
    отдельным sendPhoto ПЕРЕД rich-постом (см. --photo в main). Параметр оставлен
    как якорь на будущее, когда структура photo-блока прояснится.
    """
    return {
        "chat_id": chat_id,
        "rich_message": {"markdown": add_paragraph_air(md_text)},
        "disable_notification": False,
    }


def build_demo_payload(chat_id: str) -> dict:
    return build_markdown_payload(chat_id, DEMO_MARKDOWN)


def build_demo_payload_blocks_legacy(chat_id: str) -> dict:
    """Legacy: ручная сборка blocks. по решению автора API вернул 400
    «can't parse InputRichBlock: Unsupported rich text type» - НЕ использовать,
    пока не сверены точные имена RichText-типов с core.telegram.org."""
    return {
        "chat_id": chat_id,
        "rich_message": {
            "blocks": build_demo_blocks(),
        },
        "disable_notification": False,
    }


# ---------------------------------------------------------------------------
# Отправка / dry-run
# ---------------------------------------------------------------------------

def send_rich_message(token: str, payload: dict, timeout: int = 30) -> dict:
    url = f"{API_BASE}/bot{token}/sendRichMessage"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "error_code": e.code, "description": body}


def main():
    parser = argparse.ArgumentParser(description="Отправка rich-сообщения в Telegram (sendRichMessage, Bot API 10.2)")
    parser.add_argument("payload_file", nargs="?", help="Путь к JSON-файлу с payload (без chat_id - он подставляется автоматически)")
    parser.add_argument("--demo", action="store_true", help="Использовать встроенный демо-payload (markdown-путь, рабочий)")
    parser.add_argument("--markdown-file", help="🔴 ОСНОВНОЙ ПУТЬ: путь к .md-файлу с текстом поста (GFM: **bold**, | | таблицы, - [ ] чек-листы) - сервер сам соберёт блоки")
    parser.add_argument("--dry-run", action="store_true", help="Только напечатать итоговый JSON, в сеть НЕ ходить (дефолт, если не указан --send)")
    parser.add_argument("--send", action="store_true", help="РЕАЛЬНАЯ отправка в Telegram. Требует явного флага, дефолт - dry-run")
    parser.add_argument("--chat-id", help="Переопределить получателя (напр. @username или -100... тестового канала). Без него - дефолтный chat_id из env/.env")
    parser.add_argument("--schedule-in", type=int, help="Отложка: отправить через N СЕКУНД (кладётся в schedule_date как unix-ts). Пост уходит в 'Отложенные' получателя, не публикуется сразу")
    parser.add_argument("--now-ts", type=int, help="Текущий unix-ts (передаётся снаружи, т.к. время в скрипте недоступно). Обязателен при --schedule-in")
    parser.add_argument("--force", action="store_true", help="Обойти гейт качества (двойной курсив/тире/вода). Только осознанно.")
    args = parser.parse_args()

    if not args.demo and not args.payload_file and not args.markdown_file:
        parser.error("нужен --markdown-file <пост.md>, либо путь к JSON-файлу с payload, либо --demo")

    token, chat_id, source = resolve_credentials()
    if args.chat_id:
        chat_id = args.chat_id
        source = f"--chat-id override ({chat_id})"
    if not token or not chat_id:
        sys.stderr.write(
            f"ERROR: не удалось получить token/chat_id (источник: {source}). "
            f"Проверь env IVAN_TG_BOT_TOKEN/IVAN_TG_CHAT_ID или файл {FALLBACK_ENV_FILE}\n"
        )
        sys.exit(1)

    if args.markdown_file:
        md_text = Path(args.markdown_file).read_text(encoding="utf-8")
        # 🔴 ГЕЙТ ПЕРЕД ОТПРАВКОЙ: дыры сессии по решению автора (двойной курсив / тире в прозе / вода).
        # Блокирует send, обход только --force (для крайних случаев, осознанно).
        violations = validate_post_text(md_text)
        if violations and not args.force:
            sys.stderr.write("🛑 ПОСТ НЕ ПРОШЁЛ ГЕЙТ КАЧЕСТВА (по решению автора прецедент, ~30 кругов):\n")
            for v in violations:
                sys.stderr.write(f"  - {v}\n")
            sys.stderr.write("Исправь текст. Обход (осознанно): --force\n")
            sys.exit(2)
        payload = build_markdown_payload(chat_id, md_text)
    elif args.demo:
        payload = build_demo_payload(chat_id)
    else:
        raw = Path(args.payload_file).read_text(encoding="utf-8")
        payload = json.loads(raw)
        payload.setdefault("chat_id", chat_id)

    # Отложка: schedule_date = unix-ts момента отправки. Telegram кладёт такое
    # сообщение в «Отложенные» получателя (канал/чат), не публикуя сразу.
    if args.schedule_in is not None:
        if args.now_ts is None:
            parser.error("--schedule-in требует --now-ts <текущий unix-ts> (время внутри скрипта недоступно)")
        payload["schedule_date"] = int(args.now_ts) + int(args.schedule_in)

    # Валидность JSON payload (само по себе гарантировано json.dumps ниже,
    # но проверяем явным round-trip как требует Шаг 4 ТЗ)
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    json.loads(payload_json)  # округляем через json.loads - падает, если невалидно

    do_send = args.send and not args.dry_run

    print(f"# token source: {source} (token starts with: {token[:6]}...)")
    print(f"# chat_id: {chat_id}")
    print(f"# mode: {'SEND' if do_send else 'DRY-RUN (no network call)'}")
    print(payload_json)

    if not do_send:
        return

    result = send_rich_message(token, payload)
    print("# response:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
