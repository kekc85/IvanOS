#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-chatgpt-image.py - генерация картинки к посту.

🔇 ДЕФОЛТ (с этой редакции) - ТИХИЙ КАНАЛ, окно браузера НЕ открывается.
Картинку рисует движок `codex_image` (Codex CLI -> системный скилл imagegen) тем же
логином ChatGPT, но целиком в фоне: экран, буфер обмена и фронтмост-окно свободны,
за компьютером можно спокойно работать. Все прежние аргументы приняты и работают,
вызовы менять не нужно - они просто стали тихими.

Запасной путь - старый Playwright-тракт через живой Chrome (профиль
~/.playwright-chrome-data): включается флагом `--engine browser`, вот он окно открывает.
Тихий движок лежит в личной папке владельца, у ученика её нет - тогда скрипт честно
печатает причину и сам откатывается на браузер (или падает, если дан --no-fallback).

Usage:
  # тихо, без окон
  python3 gen-chatgpt-image.py --prompt "..." --out ~/Desktop/post-<slug>.png
  # запасной путь через живой Chrome
  python3 gen-chatgpt-image.py --engine browser --prompt "..." --out ~/Desktop/img.png
Браузерному пути нужен venv с playwright:
  ~/.business/scripts/auto-uniqualize/python3 gen-chatgpt-image.py --engine browser ...

Коды возврата: 0 SAVED · 2 NO_EDITOR · 3 NO_IMAGE_TIMEOUT · 4 NO_SRC ·
5 DOWNLOAD_FAIL · 6 ERROR · 8 тихий канал не сработал, а откат запрещён (--no-fallback)
или дело в аргументах · 9 лимит аккаунта ChatGPT выжжен (ждать дату либо явно
--engine browser) · 10 рисовать нечем: нет ни тихого движка, ни playwright.
Ни один отказ не выходит трейсбеком: у ученика нет ни движка, ни playwright, и раньше
штатный путь кончался `ImportError: playwright not installed` вместо объяснения.
"""
import sys, time, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quiet_channel as QC

IMG_SEL = ('img[src*="backend-api/estuary"], img[src*="oaiusercontent"], img[src*="files.oaiusercontent"], '
           'img[alt*="enerate"], img[alt*="mage"]')

#: Тихому каналу на генерацию нужно больше времени, чем браузерному опросу страницы.
CODEX_MIN_TIMEOUT = 600


def run_browser(args, quiet_why: str = "") -> int:
    """Старый путь: живой Chrome по Playwright. Окно откроется, это ожидаемо.

    🔴 playwright импортируем через QC.playwright_or_reason(), а не напрямую: скилл
    раздаётся ученикам, у них ни движка, ни playwright - прямой импорт заканчивал
    штатный путь трейсбеком `ImportError: playwright not installed` ровно в момент,
    когда скрипт обязан был объяснить человеку, чем рисовать.
    """
    sync_playwright, why = QC.playwright_or_reason()
    if sync_playwright is None:
        QC.no_channel_banner(
            Path(__file__).name, quiet_why, f"playwright не поднялся: {why}",
            venv_hint="$HOME/.business/scripts/auto-uniqualize/venv/bin/python3")
        return QC.EXIT_NO_CHANNEL

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=args.profile,
                channel="chrome",
                headless=False,
                accept_downloads=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as e:
            # Браузер не поднялся (нет Chrome, занят профиль, нет графической сессии) -
            # это тоже отказ канала, а не повод показывать стек.
            QC.no_channel_banner(
                Path(__file__).name, quiet_why,
                f"живой Chrome не запустился: {type(e).__name__}: {e}",
                venv_hint="$HOME/.business/scripts/auto-uniqualize/venv/bin/python3")
            return QC.EXIT_NO_CHANNEL
        page = ctx.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector(
                '#prompt-textarea, div.ProseMirror[contenteditable="true"]',
                state="visible", timeout=30000)
            time.sleep(2)

            editor = (page.query_selector('#prompt-textarea')
                      or page.query_selector('div.ProseMirror[contenteditable="true"]'))
            if not editor:
                print("NO_EDITOR"); return 2
            editor.click(); time.sleep(0.5)
            page.evaluate("""async (t) => { await navigator.clipboard.writeText(t); }""", args.prompt)
            time.sleep(0.3)
            page.keyboard.press("Meta+V")
            time.sleep(1.5)

            btn = (page.query_selector('button[data-testid="send-button"]:not([disabled])')
                   or page.query_selector('button[aria-label*="end" i]:not([disabled])')
                   or page.query_selector('form button[type="submit"]:not([disabled])'))
            if btn:
                btn.click()
            else:
                editor.focus(); page.keyboard.press("Enter")
            print("SENT, waiting for image...")

            baseline = len(page.query_selector_all(IMG_SEL))
            start = time.time()
            while time.time() - start < args.timeout:
                time.sleep(4)
                n = len(page.query_selector_all(IMG_SEL))
                if n > baseline:
                    time.sleep(6)  # дать дорисоваться
                    break
            imgs = page.query_selector_all(IMG_SEL)
            if not imgs:
                print("NO_IMAGE_TIMEOUT"); return 3
            src = imgs[-1].get_attribute("src")
            if not src:
                print("NO_SRC"); return 4
            resp = ctx.request.get(src)
            if resp.ok:
                out.write_bytes(resp.body())
                print(f"SAVED {out}")
                return 0
            print(f"DOWNLOAD_FAIL {resp.status}"); return 5
        except Exception as e:
            print(f"ERROR {e}"); return 6
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default=str(Path("~/.playwright-chrome-data").expanduser()))
    ap.add_argument("--url", default="https://chatgpt.com/")
    ap.add_argument("--timeout", type=int, default=240)
    QC.add_engine_args(ap)
    args = ap.parse_args()

    quiet_why = ""
    if args.engine == "codex":
        out = Path(args.out).expanduser()
        # старые вызовы шлют --timeout 240 под опрос страницы, тихому каналу этого мало
        ok, why, kind = QC.render_quiet(
            args.prompt, out, size=args.size, refs=args.ref,
            timeout=max(args.timeout, CODEX_MIN_TIMEOUT), attempts=args.attempts)
        if ok:
            print(f"SAVED {out}")
            return 0
        quiet_why = why
        # Лимит аккаунта - не поломка канала: решение «ждать дату или всё-таки открыть
        # окно» принимает человек, молча жечь его экран ради той же стены нельзя.
        if kind == QC.KIND_QUOTA:
            QC.quota_banner(why, Path(__file__).name)
            return QC.EXIT_QUOTA
        print(f"QUIET_CHANNEL_FAIL [{kind}]: {why}")
        if kind == QC.KIND_BAD_ARG:
            # кривой аргумент браузером не лечится - чинится одним словом в вызове
            return QC.EXIT_QUIET_UNAVAILABLE
        if args.no_fallback:
            return QC.EXIT_QUIET_UNAVAILABLE
        print("откатываюсь на браузерный путь - сейчас откроется окно Chrome")

    return run_browser(args, quiet_why)


if __name__ == "__main__":
    sys.exit(main())
