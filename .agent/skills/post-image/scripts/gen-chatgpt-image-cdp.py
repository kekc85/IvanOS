#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-chatgpt-image-cdp.py - генерация картинки к посту.

🔇 ДЕФОЛТ (с этой редакции) - ТИХИЙ КАНАЛ, окно браузера НЕ открывается и рендер-Chrome
поднимать не нужно. Рисует движок `codex_image` (Codex CLI -> системный скилл imagegen)
тем же логином ChatGPT, только в фоне. Все прежние аргументы приняты как были, старые
вызовы менять не надо - они просто стали тихими.

Запасной путь - прежний тракт через живой залогиненный ChatGPT в рендер-Chrome по
CDP :9222 (профиль ~/.chrome-cdp-profile). Включается флагом `--engine browser`.
Он работает в своей новой вкладке, чужие не трогает и закрывает её за собой.

Если тихий движок не найден (скилл раздаётся ученикам, а движок лежит в личной папке
владельца) - скрипт честно печатает причину и сам откатывается на браузерный путь;
с флагом --no-fallback вместо отката вернёт код 8.

Рендер-Chrome для запасного пути поднимается так (это ОТДЕЛЬНЫЙ машинный Chrome,
НЕ рабочий браузер владельца). Сначала снять стейл-лок профиля ПЕРЕИМЕНОВАНИЕМ
(закон «ничего не удалять», mv вместо удаления; полная команда - в тексте
хука gpt-image-wrong-browser-guard.sh):
  mv "$HOME/.chrome-cdp-profile/SingletonLock" "$HOME/.chrome-cdp-profile/SingletonLock.stale" 2>/dev/null || true
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --remote-debugging-port=9222 '--remote-allow-origins=*' \
    --user-data-dir="$HOME/.chrome-cdp-profile" --no-first-run \
    --no-default-browser-check --disable-session-crashed-bubble \
    "https://chatgpt.com/" >/dev/null 2>&1 & disown; sleep 9

Использование:
  # тихо, без окон
  python3 gen-chatgpt-image-cdp.py --prompt "$(cat /tmp/imgprompt.txt)" --out ~/path/img.png
  # запасной путь через рендер-Chrome
  python3 gen-chatgpt-image-cdp.py --engine browser --prompt "..." --out ~/path/img.png

Коды возврата: 0 SAVED · 2 NO_EDITOR (не залогинен/страница не та) ·
3 NO_IMAGE_TIMEOUT · 4 NO_SRC · 5 DOWNLOAD_FAIL · 6 ERROR · 7 CDP_DEAD ·
8 тихий канал не сработал, а откат запрещён флагом --no-fallback (или дело в
аргументах) · 9 лимит аккаунта ChatGPT выжжен: ждать дату открытия либо явно
--engine browser · 10 рисовать нечем: нет ни тихого движка, ни playwright.
Ни один отказ не выходит трейсбеком: у ученика нет ни движка, ни playwright, и раньше
штатный путь кончался `ImportError: playwright not installed` вместо объяснения.
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import quiet_channel as QC

#: Тихому каналу на генерацию нужно больше времени, чем браузерному опросу страницы.
CODEX_MIN_TIMEOUT = 600


def run_browser(args, quiet_why: str = ""):
    """Запасной путь: живой ChatGPT в рендер-Chrome по CDP. Окно уже открыто/откроется.

    🔴 playwright тянем через QC.playwright_or_reason(), а не прямым импортом: скилл
    раздаётся ученикам, у них ни тихого движка, ни playwright - прямой импорт обрывал
    штатный путь трейсбеком `ImportError: playwright not installed` вместо того, чтобы
    сказать человеку, что рисовать нечем и что поставить.
    """
    out = pathlib.Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    sync_playwright, why = QC.playwright_or_reason()
    if sync_playwright is None:
        QC.no_channel_banner(
            pathlib.Path(__file__).name, quiet_why, f"playwright не поднялся: {why}",
            venv_hint="$HOME/.business/scripts/auto-uniqualize/venv/bin/python3")
        return QC.EXIT_NO_CHANNEL

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            print(f"CDP_DEAD: {e}\nПодними рендер-Chrome (команда в докстринге)")
            return 7
        ctx = browser.contexts[0]
        page = ctx.new_page()  # СВОЯ вкладка, чужие не трогаем
        try:
            page.goto("https://chatgpt.com/", wait_until="domcontentloaded",
                      timeout=60000)
            page.wait_for_timeout(3500)

            editor = page.query_selector("#prompt-textarea") \
                or page.query_selector('div[contenteditable="true"]')
            if not editor:
                print("NO_EDITOR: редактор не найден (страница не та или логин слетел)")
                return 2

            known = {img.get_attribute("src")
                     for img in page.query_selector_all(
                         'img[src*="backend-api/estuary"], img[src*="oaiusercontent"]')}

            editor.click()
            # длинный промпт через clipboard-paste (набор по буквам ломает разметку)
            page.evaluate(
                "async t => { await navigator.clipboard.writeText(t); }",
                args.prompt)
            page.keyboard.press("Meta+V")
            page.wait_for_timeout(1200)
            send = page.query_selector('button[data-testid="send-button"]') \
                or page.query_selector('#composer-submit-button')
            if send:
                send.click()
            else:
                page.keyboard.press("Enter")

            deadline = time.time() + args.timeout
            src = None
            while time.time() < deadline:
                page.wait_for_timeout(3000)
                for img in page.query_selector_all(
                        'img[src*="backend-api/estuary"], img[src*="oaiusercontent"]'):
                    s = img.get_attribute("src")
                    if s and s not in known:
                        src = s
                if src:
                    # дождаться финального рендера (src может смениться)
                    page.wait_for_timeout(4000)
                    break
            if not src:
                print("NO_IMAGE_TIMEOUT: картинка не появилась за отведённое время")
                return 3

            resp = ctx.request.get(src)
            if not resp.ok:
                print(f"DOWNLOAD_FAIL: HTTP {resp.status}")
                return 5
            out.write_bytes(resp.body())
            print(f"SAVED: {out} ({out.stat().st_size} bytes)")
            return 0
        except Exception as e:
            print(f"ERROR: {e}")
            return 6
        finally:
            try:
                page.close()  # закрыть СВОЮ вкладку за собой
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    ap.add_argument("--timeout", type=int, default=240)
    QC.add_engine_args(ap)
    args = ap.parse_args()

    quiet_why = ""
    if args.engine == "codex":
        out = pathlib.Path(args.out).expanduser()
        # старые вызовы шлют --timeout 240 под опрос страницы, тихому каналу этого мало
        ok, why, kind = QC.render_quiet(
            args.prompt, out, size=args.size, refs=args.ref,
            timeout=max(args.timeout, CODEX_MIN_TIMEOUT), attempts=args.attempts)
        if ok:
            print(f"SAVED: {out} ({out.stat().st_size} bytes)")
            return 0
        quiet_why = why
        # Лимит аккаунта отделён от прочих отказов: повторы на нём бессмысленны, а
        # рендер-Chrome ходит тем же аккаунтом ChatGPT - решает человек, не скрипт.
        if kind == QC.KIND_QUOTA:
            QC.quota_banner(why, pathlib.Path(__file__).name)
            return QC.EXIT_QUOTA
        print(f"QUIET_CHANNEL_FAIL [{kind}]: {why}")
        if kind == QC.KIND_BAD_ARG:
            # кривой аргумент браузером не лечится - чинится одним словом в вызове
            return QC.EXIT_QUIET_UNAVAILABLE
        if args.no_fallback:
            return QC.EXIT_QUIET_UNAVAILABLE
        print("откатываюсь на браузерный путь через рендер-Chrome по CDP")

    return run_browser(args, quiet_why)


if __name__ == "__main__":
    sys.exit(main())
