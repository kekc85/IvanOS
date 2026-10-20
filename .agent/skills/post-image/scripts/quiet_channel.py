#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тихий канал генерации картинок для скилла post-image (общий кусок двух скриптов).

Зачем. Раньше картинка к посту рисовалась только через живой браузер: скрипт открывал
окно Chrome на chatgpt.com, занимал экран, буфер обмена и фронтмост-окно. Работать за
компьютером во время генерации было нельзя. Владелец потребовал, чтобы окна больше не
открывались и генерация шла бесшумно.

Теперь дефолт - движок `codex_image` (Codex CLI -> системный скилл imagegen), который
ходит тем же логином ChatGPT, но без единого окна браузера. Браузерные тракты никуда не
делись, они лежат запасными и включаются флагом `--engine browser`.

Движок живёт в личной папке владельца (`.business/scripts/codex_image.py`), а скилл
раздаётся ученикам - у них этой папки нет. Поэтому импорт условный: не нашли движок -
честно печатаем причину и откатываемся на браузерный путь, молча не падаем.

🔴 ПОЧЕМУ ЗДЕСЬ ЖИВУТ КОДЫ ВОЗВРАТА И БАННЕРЫ ОТКАЗА. У ученика нет ни движка, ни
playwright: штатный путь у него кончался ImportError-трейсбеком в момент отката на
браузер, то есть скилл падал ровно там, где обязан был объяснить, что делать. Отказ
любого канала обязан выйти человеческой причиной и внятным кодом, а не стеком. Коды
одинаковые у обоих скриптов скилла, поэтому лежат в одном месте.

Отдельно разведён ЛИМИТ АККАУНТА. Движок кидает `CodexQuotaError` (наследник
`CodexImageError`) с датой открытия лимита: это не брак промпта и не поломка канала,
повторять попытки бессмысленно, а тихо открывать окно браузера - тем более (браузер
ходит тем же аккаунтом ChatGPT, скорее всего упрётся в ту же стену, зато экран займёт).
Поэтому лимит отдаётся своим кодом, и решение «ждать окна лимита или всё-таки идти в
браузер» принимает человек.
"""
from __future__ import annotations

import sys
from pathlib import Path

#: Где искать тихий движок. Первый путь - канон владельца, второй - симлинк-совместимость.
ENGINE_DIRS = (
    Path(".business/scripts").expanduser(),
    Path("~/.business/scripts").expanduser(),
)

#: Причина, по которой движок не подхватился (для честного сообщения в лог).
LOAD_ERROR = ""

# ── Коды возврата (общие для gen-chatgpt-image.py и gen-chatgpt-image-cdp.py) ──────
#: Тихий канал не сработал, а откат запрещён флагом --no-fallback.
EXIT_QUIET_UNAVAILABLE = 8
#: Лимит аккаунта ChatGPT выжжен. Ждать дату открытия либо осознанно идти --engine browser.
EXIT_QUOTA = 9
#: Оба канала отвалились (например, нет ни движка, ни playwright) - рисовать нечем.
EXIT_NO_CHANNEL = 10

# ── Классы отказа тихого канала (третье значение render_quiet) ────────────────────
KIND_OK = ""
KIND_NO_ENGINE = "no-engine"     # движка нет на машине (типовой случай ученика)
KIND_QUOTA = "quota"             # лимит аккаунта выжжен, повторять нечего
KIND_REFUSED = "refused"         # движок отработал, но картинки нет (отказ/таймаут)
KIND_BAD_ARG = "bad-arg"         # мусор в аргументах (например, --size 1024)
KIND_BROKEN = "broken"           # движок сломался неожиданным образом

#: Ключи размеров движка. Держим копией, чтобы валидировать --size ДО загрузки движка
#: (у ученика движка нет вовсе, а сказать про кривой размер надо всё равно).
SIZE_KEYS = ("og", "square", "slide", "story")


def load_engine():
    """Пробует подтянуть codex_image. Возвращает модуль или None (причина - в LOAD_ERROR)."""
    global LOAD_ERROR
    for d in ENGINE_DIRS:
        if (d / "codex_image.py").exists():
            if str(d) not in sys.path:
                sys.path.insert(0, str(d))
            try:
                import codex_image  # type: ignore
                return codex_image
            except Exception as e:  # движок есть, но не грузится - причину наверх
                LOAD_ERROR = f"{d / 'codex_image.py'} не импортируется: {type(e).__name__}: {e}"
                return None
    LOAD_ERROR = ("тихий движок codex_image.py не найден (искал в "
                  + ", ".join(str(d) for d in ENGINE_DIRS) + ")")
    return None


def parse_size(raw, known=SIZE_KEYS):
    """Размер: ключ движка (og/square/slide/story) либо явные пиксели вида 1024x1280.

    🔴 Ключ проверяем ЗДЕСЬ, а не в движке. Раньше любой мусор («--size 1024», «--size
    большой») уезжал в движок строкой, там ловился `SIZES[key]` и вылетал KeyError -
    вызывающий печатал «тихий канал сломался», хотя сломался не канал, а аргумент, и
    чинится он одним словом. Кидаем ValueError с человеческим текстом.
    """
    if not raw:
        return None
    s = str(raw).strip().lower()
    if "x" in s:
        w, h = s.split("x", 1)
        if not (w.strip().isdigit() and h.strip().isdigit()):
            raise ValueError(
                f"--size {raw!r} не разобрать: пиксели пишутся как 1024x1280 "
                f"(целые числа), либо возьми ключ: {', '.join(known)}")
        return (int(w), int(h))
    if s not in known:
        raise ValueError(
            f"--size {raw!r} не ключ размера. Допустимые ключи: {', '.join(known)}. "
            "Нужен свой размер - пиши пиксели явно, например 1024x1280")
    return s


class _Log:
    """Простой логгер: движок пишет прогресс прямо в stdout скрипта."""

    def info(self, msg):
        print(msg, flush=True)


def render_quiet(prompt, out, size=None, refs=None, timeout=600, attempts=2):
    """Рисует картинку тихим каналом.

    Возвращает тройку (ok, причина, класс отказа). Класс - одна из констант KIND_*:
    по ней вызывающий решает, что делать дальше, не разбирая текст ошибки руками.
    Главное различие - KIND_QUOTA (лимит аккаунта, ждать дату) против всего
    остального (канала нет / картинка не вышла - тогда есть смысл в браузере).
    """
    try:
        parsed_size = parse_size(size)
    except ValueError as e:
        return False, str(e), KIND_BAD_ARG

    engine = load_engine()
    if engine is None:
        return False, LOAD_ERROR, KIND_NO_ENGINE

    out = Path(out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    # Лимит ловим ОТДЕЛЬНО и первым: CodexQuotaError - наследник CodexImageError,
    # поэтому порядок проверок здесь несущий. getattr - на случай старого движка
    # без этого класса (тогда лимит просто уедет обычным отказом, а не трейсбеком).
    quota_exc = getattr(engine, "CodexQuotaError", None)
    try:
        engine.render(
            prompt,
            out_path=out,
            refs=[Path(r).expanduser() for r in (refs or [])],
            size=parsed_size,
            attempts=attempts,
            timeout=timeout,
            logger=_Log(),
        )
    except Exception as e:
        if quota_exc is not None and isinstance(e, quota_exc):
            return False, str(e), KIND_QUOTA
        if isinstance(e, engine.CodexImageError):
            return False, str(e), KIND_REFUSED
        return False, f"тихий канал сломался: {type(e).__name__}: {e}", KIND_BROKEN
    return True, "", KIND_OK


def quota_banner(reason: str, script: str) -> None:
    """Лимит аккаунта выжжен. Честно: дата открытия и один выбор человека.

    Ни советов «повторить с --attempts», ни ссылок на папку скринов: движок на лимите
    намеренно НЕ повторяет, а скринов у тихого канала не бывает вовсе.
    """
    print("\n" + "!" * 78)
    print("ЛИМИТ АККАУНТА ChatGPT ВЫЖЖЕН - это не брак промпта и не поломка канала")
    print(f"  {reason}")
    print("  Что делать (одно из двух):")
    print("    1) дождаться даты открытия лимита выше и повторить тот же вызов")
    print(f"    2) осознанно пойти браузером: python3 {script} --engine browser ...")
    print("       (откроется окно Chrome и займёт экран; аккаунт ChatGPT тот же, "
          "лимит там может быть тем же)")
    print("  Повторы сейчас бессмысленны: на лимите движок попытки не тратит")
    print("!" * 78 + "\n")


def playwright_or_reason():
    """Импорт playwright с человеческой причиной вместо трейсбека.

    🔴 Ради этого функция и существует. Скилл раздаётся ученикам, playwright у них
    обычно не стоит, а движка нет вовсе - штатный путь упирался в
    `ImportError: playwright not installed` прямо в момент отката на браузер, то есть
    ученик видел стек вместо объяснения. Возвращаем (sync_playwright, "") либо
    (None, причина).
    """
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def no_channel_banner(script: str, quiet_why: str, browser_why: str,
                      venv_hint: str = "") -> None:
    """Оба канала отвалились. Говорим словами: почему и что чинить первым."""
    print("\n" + "!" * 78)
    print("КАРТИНКУ РИСОВАТЬ НЕЧЕМ: не сработал ни тихий канал, ни браузерный")
    print(f"  тихий канал:     {quiet_why or 'не запускался'}")
    print(f"  браузерный путь: {browser_why or 'не запускался'}")
    print("  Что делать:")
    print("    1) поставить playwright для запасного пути:")
    print("       python3 -m pip install playwright && python3 -m playwright install chromium")
    if venv_hint:
        print(f"       либо запускать готовым окружением: {venv_hint}")
    print("    2) либо взять картинку руками: открыть chatgpt.com, вставить промпт, "
          "скачать файл")
    print(f"  Скрипт: {script}")
    print("!" * 78 + "\n")


def add_engine_args(ap):
    """Добавляет скрипту общие флаги канала. Дефолт - тихий codex, окон не открывает."""
    ap.add_argument(
        "--engine", choices=["codex", "browser"], default="codex",
        help="codex (по умолчанию) - тихо, без окон; browser - старый путь через "
             "живой Chrome, окно откроется")
    ap.add_argument(
        "--size", default=None,
        help="og / square / slide / story либо явно 1024x1280 (только для codex)")
    ap.add_argument(
        "--ref", action="append", default=[],
        help="картинка-референс, можно повторять до 5 раз (только для codex)")
    ap.add_argument(
        "--attempts", type=int, default=2,
        help="сколько раз пробовать, прежде чем признать отказ (только для codex)")
    ap.add_argument(
        "--no-fallback", action="store_true",
        help="не откатываться на браузер, если тихий канал не сработал")
    return ap
