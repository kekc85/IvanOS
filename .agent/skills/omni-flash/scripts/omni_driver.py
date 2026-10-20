#!/usr/bin/env python3
"""Drive Google Flow (Gemini Omni Flash) over CDP in the USER's already-running Chrome.

BYOA: runs on the user's own logged-in Google Flow session (canon _shared/bring-your-own-account.md).
Connects to an EXISTING logged-in Chrome via CDP (--remote-debugging-port=9222).
NEVER launches or closes the browser - the user starts it himself. The CDP port is account-agnostic;
the account comes from whichever Google Flow tab the user is logged into.

Two subcommands:
  probe  - open Flow, dump candidate selectors (file inputs / editors / buttons / video)
           + screenshot, so selectors can be filled into config.json before a real run.
  run    - upload clip -> paste prompt -> submit -> poll for new video -> download output.

Reuses the project CDP pattern from ~/.business/scripts/auto-uniqualize/driver_parallel.py:
  connect_over_cdp -> contexts[0] (reuse, do not create) -> clipboard paste input ->
  baseline-count polling (track OUR baseline, not "newest") -> context.request.get download.

Run with the project venv:
  ~/.business/scripts/auto-uniqualize/python3 omni_driver.py probe
  ~/.business/scripts/auto-uniqualize/python3 omni_driver.py run --clip in.mp4 --prompt-file p.txt --out out.mp4
"""
import argparse
import asyncio
import json
import os
import sys
import time

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "..", "config.json")


def load_cfg():
    with open(CFG_PATH) as f:
        return json.load(f)


async def connect(p, cfg):
    """Attach to the running Chrome. Fail loudly with a clear message if CDP is down."""
    cdp = cfg.get("cdp_url", "http://localhost:9222")
    try:
        browser = await p.chromium.connect_over_cdp(cdp)
    except Exception as e:
        raise SystemExit(
            f"CDP не доступен на {cdp}: {e}\n"
            "Подними СВОЙ Chrome с --remote-debugging-port=9222 и залогинься в СВОЙ Google Flow "
            "(account.py onboard google_flow), потом повтори."
        )
    context = browser.contexts[0] if browser.contexts else await browser.new_context(accept_downloads=True)
    return browser, context


async def cmd_probe(cfg):
    async with async_playwright() as p:
        _, context = await connect(p, cfg)
        page = await context.new_page()
        await page.goto(cfg["flow_url"], wait_until="domcontentloaded")
        await asyncio.sleep(cfg.get("page_settle_sec", 6))

        dump = await page.evaluate(
            """() => {
                const t = el => (el.innerText||el.value||el.getAttribute('aria-label')||el.placeholder||'').trim().slice(0,60);
                const grab = sel => [...document.querySelectorAll(sel)].slice(0,25).map(e => ({
                    tag:e.tagName.toLowerCase(),
                    type:e.getAttribute('type'),
                    aria:e.getAttribute('aria-label'),
                    testid:e.getAttribute('data-testid'),
                    placeholder:e.getAttribute('placeholder'),
                    text:t(e),
                    src:e.getAttribute('src')
                }));
                return {
                    file_inputs: grab('input[type=file]'),
                    editors: grab('textarea, [contenteditable=\"true\"], div.ProseMirror'),
                    buttons: grab('button'),
                    videos: grab('video, video source, a[download]')
                };
            }"""
        )
        shot = os.path.join(HERE, "..", "probe-flow.png")
        await page.screenshot(path=shot, full_page=False)
        print(json.dumps(dump, ensure_ascii=False, indent=2))
        print(f"\n[probe] screenshot -> {os.path.abspath(shot)}", file=sys.stderr)
        await page.close()


async def cmd_run(cfg, clip, prompt, out_path):
    sel = cfg["selectors"]
    async with async_playwright() as p:
        _, context = await connect(p, cfg)
        page = await context.new_page()
        await page.goto(cfg["flow_url"], wait_until="domcontentloaded")
        await asyncio.sleep(cfg.get("page_settle_sec", 6))

        # rate-limit / quota circuit-breaker
        body = (await page.inner_text("body")).lower()
        for marker in ("too many requests", "quota", "limit reached", "try again later"):
            if marker in body:
                raise SystemExit(f"Flow вернул лимит ('{marker}') - стоп, не долбим. Жди сброса.")

        # 1) upload clip
        fi = await page.query_selector(sel["file_input"])
        if not fi:
            raise SystemExit(f"не найден file_input по селектору {sel['file_input']} - сними probe заново")
        await fi.set_input_files(clip)
        await asyncio.sleep(cfg.get("upload_settle_sec", 8))

        # 2) paste prompt (clipboard, обход бана на paste)
        editor = await page.query_selector(sel["editor"])
        if not editor:
            raise SystemExit(f"не найден editor по селектору {sel['editor']} - сними probe заново")
        await editor.click()
        await asyncio.sleep(0.4)
        await page.evaluate("async (t) => { await navigator.clipboard.writeText(t); }", prompt)
        await asyncio.sleep(0.3)
        await page.keyboard.press("Meta+V")
        await asyncio.sleep(1.0)

        # 3) baseline before submit, then submit
        baseline = len(await page.query_selector_all(sel["result_video"]))
        submit = await page.query_selector(sel["submit"])
        if submit:
            await submit.click()
        else:
            await editor.focus()
            await page.keyboard.press("Enter")

        # 4) poll for a NEW result video (track our own baseline)
        timeout = cfg.get("generation_timeout_sec", 300)
        poll = cfg.get("poll_interval_sec", 5)
        start = time.time()
        src = None
        while time.time() - start < timeout:
            await asyncio.sleep(poll)
            vids = await page.query_selector_all(sel["result_video"])
            if len(vids) > baseline:
                await asyncio.sleep(6)
                src = await vids[-1].get_attribute("src")
                if src:
                    break
            b2 = (await page.inner_text("body")).lower()
            if "too many requests" in b2 or "limit reached" in b2:
                raise SystemExit("Flow лимит во время генерации - стоп.")
        if not src:
            raise SystemExit(f"таймаут {timeout}s - результат не появился (или селектор result_video мимо)")

        # 5) download via CDP session request (несёт куки/сессию)
        resp = await context.request.get(src)
        if not resp.ok:
            raise SystemExit(f"скачивание не удалось: HTTP {resp.status} {src}")
        with open(out_path, "wb") as f:
            f.write(await resp.body())
        print(json.dumps({"ok": True, "out": os.path.abspath(out_path), "src": src}, ensure_ascii=False))
        await page.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    r = sub.add_parser("run")
    r.add_argument("--clip", required=True)
    r.add_argument("--prompt-file", required=True)
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = load_cfg()

    if a.cmd == "probe":
        asyncio.run(cmd_probe(cfg))
    else:
        with open(a.prompt_file) as f:
            prompt = f.read()
        asyncio.run(cmd_run(cfg, a.clip, prompt, a.out))


if __name__ == "__main__":
    main()