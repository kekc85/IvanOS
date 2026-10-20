#!/usr/bin/env python3
"""
Параллельный driver карусельного рендера. Два канала, промпты общие.

  --engine codex   (ДЕФОЛТ) тихий headless-канал codex exec → imagegen: ни одного
                   окна браузера, экран/буфер обмена/фронтмост-окно не трогаются.
                   Общего ресурса у канала нет, поэтому слайды рисуются пачкой.
  --engine browser прежний путь: CDP к живому Chrome, кастомка ChatGPT, вкладки.
                   Оставлен запасным - он единственный, кто ходит в кастомку.

Логику промптов/лиц/CTA берёт из driver.py + design_system.py (не дублирует).

Usage:
    python3 driver_parallel.py <package-id> [номера] [--parallel N] [--delay S]
    python3 driver_parallel.py <package-id> --engine browser --parallel 2 --delay 14
"""

import asyncio
import logging
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    # Тихому каналу (дефолт) playwright не нужен вообще - падаем внятным текстом
    # только тогда, когда реально попросили браузерный рендер.
    async_playwright = None

# Тихий канал живёт уровнем выше (общий с рендером обложек), путь добавляем сами,
# а не надеемся на побочный эффект импорта driver.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_image as CX

import driver as D  # переиспользуем config/logging/helpers/prompts
from design_system import (
    load_design_profile, load_face_decision, preflight_face_checklist,
    build_slide_prompt, is_last_slide,
)

SCRIPT_DIR = Path(__file__).parent.resolve()
CHANNEL_REF = Path("~/.business/assets/tg-channel/channel-2.jpg").expanduser()
AVATAR_REF = Path("~/<твой-сайт-проект>/assets/ivan-square.jpg").expanduser()

#: Потолок одновременных генераций тихого канала. Браузеру потолок 3 нужен против
#: бана ChatGPT-веба, у codex бана нет - ограничение чисто про CPU/сеть машины.
CODEX_LANES_CAP = 6

#: Один источник истины: тихий рендер слайда написан в driver.py, здесь только имя,
#: чтобы правка промпта/размера/попыток не расходилась между двумя драйверами.
render_slide_codex = D.render_slide_codex


async def render_slide_async(context, sem, input_lock, logger, cfg, custom_gpt_url,
                             slide_id, prompt, input_files, output_path, debug_dir):
    """Один слайд в своей вкладке. sem ограничивает одновременность,
    input_lock сериализует ввод (clipboard в браузере общий на все вкладки)."""
    async with sem:
        page = await context.new_page()

        async def snap(label):
            try:
                await page.screenshot(path=str(debug_dir / f"{slide_id}-{label}.png"), full_page=True)
            except Exception:
                pass

        try:
            await page.goto(custom_gpt_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector(
                '#prompt-textarea, div.ProseMirror[contenteditable="true"]',
                state="visible", timeout=40000)
            await asyncio.sleep(2)

            # CIRCUIT-BREAKER: если ChatGPT показал rate-limit — НЕ долбим, выходим.
            try:
                body = (await page.inner_text("body")).lower()
                if "too many requests" in body or "making requests too quickly" in body:
                    logger.error(f"{slide_id}: RATE-LIMIT ChatGPT — стоп, не долблю (дай остыть)")
                    return False
            except Exception:
                pass

            # СЕКЦИЯ ВВОДА под общим lock: clipboard один на браузер, параллельный
            # writeText/paste затёр бы промпты друг друга. Ввод по очереди, быстрый.
            async with input_lock:
                if input_files:
                    file_input = await page.query_selector('input[type="file"]')
                    if not file_input:
                        await snap("no-file-input")
                        logger.error(f"{slide_id}: input[type=file] не найден")
                        return False
                    await file_input.set_input_files([str(f) for f in input_files])
                    await asyncio.sleep(4 + 3 * len(input_files))

                editor = await page.query_selector('#prompt-textarea') \
                    or await page.query_selector('div.ProseMirror[contenteditable="true"]')
                if not editor:
                    await snap("no-editor")
                    logger.error(f"{slide_id}: editor не найден")
                    return False
                await editor.click()
                await asyncio.sleep(0.5)
                await page.evaluate("""async (t) => { await navigator.clipboard.writeText(t); }""", prompt)
                await asyncio.sleep(0.3)
                await page.keyboard.press("Meta+V")
                await asyncio.sleep(1.5)

                send_btn = await page.query_selector('button[data-testid="send-button"]:not([disabled])') \
                    or await page.query_selector('button[aria-label*="end" i]:not([disabled])') \
                    or await page.query_selector('form button[type="submit"]:not([disabled])')
                if send_btn:
                    await send_btn.click()
                else:
                    await editor.focus()
                    await page.keyboard.press("Enter")
                logger.info(f"{slide_id}: отправлен, ждём генерацию...")
            # дальше — ожидание генерации ПАРАЛЛЕЛЬНО (вне lock)
            await asyncio.sleep(3)

            timeout = cfg.get("generation_timeout_sec", 150)
            poll = cfg.get("poll_interval_sec", 4)
            img_sel = ('img[src*="backend-api/estuary"], '
                       'img[src*="oaiusercontent"], img[src*="files.oaiusercontent"], '
                       'img[alt*="lide"], img[alt*="enerate"]')
            baseline = len(await page.query_selector_all(img_sel))
            start = time.time()
            got_new = False
            while time.time() - start < timeout:
                await asyncio.sleep(poll)
                n = len(await page.query_selector_all(img_sel))
                if n > baseline:
                    got_new = True
                    await asyncio.sleep(6)
                    break
            else:
                logger.warning(f"{slide_id}: timeout {timeout}s")

            await snap("done")
            # GUARD ПАССХРУ (урок по решению автора): нет НОВОЙ картинки = GPT не сгенерил,
            # последняя img = загруженный оригинал-донор. НЕ сохранять брак и не доставлять.
            if not got_new:
                logger.warning(f"{slide_id}: новой картинки нет (таймаут) — НЕ сохраняю пассхру-оригинал, это брак")
                return False
            imgs = await page.query_selector_all(img_sel)
            if not imgs:
                logger.warning(f"{slide_id}: PNG в ответе не найдено")
                return False
            src = await imgs[-1].get_attribute("src")
            if not src:
                return False
            resp = await context.request.get(src)
            if resp.ok:
                output_path.write_bytes(await resp.body())
                logger.info(f"{slide_id}: PNG сохранён → {output_path.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"{slide_id}: ошибка: {e}")
            await snap("error")
            return False
        finally:
            try:
                await page.close()
            except Exception:
                pass


def build_slide_jobs(cfg, logger, package_dir, only_slides):
    """Общая подготовка пакета для ОБОИХ каналов: входные слайды, папки, дизайн,
    решение по лицам, CTA и готовые промпты.

    Вынесено сюда, чтобы тихий и браузерный каналы получали ПОБУКВЕННО один и тот
    же промпт и один и тот же набор вложений - иначе картинки разъедутся по стилю
    в зависимости от того, каким каналом её нарисовали.

    Возвращает (cfg, output_dir, debug_dir, jobs) либо None, если пакет невалиден.
    jobs: список (slide_id, prompt, files, out_png).
    """
    package_id = package_dir.name
    images = D.collect_input_images(package_dir)
    if not images:
        logger.error(f"{package_id}: нет входных слайдов")
        return None

    output_dir = Path(cfg["output_dir"]) / package_id
    if not only_slides:
        if output_dir.exists():
            shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = Path(cfg["log_file"]).parent / "debug" / package_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    design = load_design_profile(package_dir)
    face_decision = load_face_decision(package_dir)
    # УРОК по решению автора/по решению автора: своп лица не влезает в 300с (драйвер ловил таймаут и терял слайд).
    # Пакет с _faces != none автоматически получает таймаут >= 600с.
    _face_policy = str(getattr(face_decision, "policy", face_decision or "none")).lower()
    if _face_policy != "none" and cfg.get("generation_timeout_sec", 150) < 600:
        cfg = {**cfg, "generation_timeout_sec": 600}
        logger.info(f"{package_id}: _faces={_face_policy} → generation_timeout_sec=600 (свопы медленные)")
    pf = preflight_face_checklist(images, D.has_face)
    cta_mode_path = package_dir / "_cta_mode.txt"
    cta_mode = cta_mode_path.read_text().strip().lower() if cta_mode_path.exists() else "codeword"
    face_cfg = cfg.get("face_image")
    face_file = Path(face_cfg).expanduser() if face_cfg and Path(face_cfg).expanduser().exists() else None
    total = len(images)

    jobs = []
    for idx, img in enumerate(images, start=1):
        if only_slides and idx not in only_slides:
            continue
        slide_id = f"slide-{idx:02d}-{img.stem}"
        face_here = face_file is not None and face_decision.swap_anywhere() and D.has_face(img)
        with_face = face_here
        trans = D.slide_translation(package_dir, idx)
        cta = is_last_slide(idx, total)
        prompt = build_slide_prompt(
            translation=trans, design=design, face_policy=face_decision.policy,
            face_in_frame=face_here, with_face_attachment=with_face,
            is_cta=cta, cta_mode=cta_mode, cta_topic=design.notes if cta else "")
        files = [img, face_file] if with_face else [img]
        if cta and cta_mode == "tg" and CHANNEL_REF.exists():
            files.append(CHANNEL_REF)
            if AVATAR_REF.exists():
                files.append(AVATAR_REF)  # реальное лицо автора для аватара мокапа
        jobs.append((slide_id, prompt, files, output_dir / f"slide-{idx:02d}.png"))

    return cfg, output_dir, debug_dir, jobs


def process_codex(cfg, logger, package_dir, only_slides, lanes):
    """Тихий прогон пакета: ни одного окна, слайды пачкой в несколько полос.

    Асинхронщина здесь не нужна вообще - у canal'а нет общей вкладки и общего
    буфера обмена, каждый вызов codex живёт в своей временной папке. Поэтому
    полосы держим обычным ThreadPoolExecutor, как в driver.py.

    Возвращает (сколько отрисовано, сколько планировалось). Пара чисел вместо
    прежнего bool «хоть что-то вышло»: из неё main() собирает честный код
    возврата, иначе прогон 1 из 8 уезжал наверх как удачный.
    Лимит аккаунта (CodexQuotaError) пробрасывается наверх - прогон обрывается.
    """
    package_id = package_dir.name
    logger.info(f"=== Тихий прогон {package_id} (codex-imagegen, до {lanes} полос) ===")

    # Гейт «аккаунт Plus» (verify_account.py) относится к вебу ChatGPT и здесь
    # неприменим: мы вообще не заходим в браузер. Проверяем ровно то, от чего
    # зависит этот канал - логин codex и изолированный дом без AGENTS.md.
    try:
        CX.ensure_home(logger)
    except CX.CodexImageError as e:
        logger.error(f"{package_id}: тихий канал не готов - {e}. "
                     "Почини одной командой: codex login")
        return (0, 0)

    prepared = build_slide_jobs(cfg, logger, package_dir, only_slides)
    if not prepared:
        return (0, 0)
    cfg, output_dir, _debug_dir, jobs = prepared
    if not jobs:
        logger.error(f"{package_id}: под фильтр слайдов ничего не попало")
        return (0, 0)

    lanes = max(1, min(lanes, len(jobs)))
    logger.info(f"{package_id}: рисую {len(jobs)} слайдов тихим каналом в {lanes} полос(ы)")

    rendered = []
    quota_stop = None      # сюда ляжет CodexQuotaError, если лимит аккаунта выжжен
    with ThreadPoolExecutor(max_workers=lanes) as pool:
        futures = {
            pool.submit(render_slide_codex, logger, sid, prompt, files, out_png, cfg): out_png
            for sid, prompt, files, out_png in jobs
        }
        for fut, out_png in futures.items():
            try:
                if fut.result():
                    rendered.append(out_png)
            except CX.CodexQuotaError as e:
                # Лимит аккаунта - внешний блокер, а не брак слайда. Гасим всё,
                # что ещё не стартовало, причину печатает main ОДИН раз с датой.
                if quota_stop is None:
                    quota_stop = e
                    for other in futures:
                        other.cancel()
            except Exception as e:
                logger.error(f"{out_png.name}: неожиданная ошибка тихого канала: {e}")
    rendered.sort()

    ok = len(rendered)
    logger.info(f"{package_id}: успех {ok}/{len(jobs)} (тихий канал)")
    # Отдельного ретрая тут нет намеренно: CX.render сам делает codex_attempts
    # попыток на слайд, а лимита «не долби, дай остыть» у канала нет.
    if rendered:
        try:
            D.stamp_provenance(output_dir, "codex-cli://imagegen", rendered, logger,
                               source=D.PROVENANCE_SOURCE_CODEX)
        except Exception as e:
            logger.warning(f"провенанс не записан: {e}")
    # Штамп ставим ДО проброса лимита: то, что успело выйти, остаётся валидным.
    if quota_stop is not None:
        raise quota_stop
    return (ok, len(jobs))


async def process_parallel(cfg, logger, package_dir, only_slides, max_parallel, start_delay):
    """Браузерный прогон. Возвращает (сколько отрисовано, сколько планировалось) -
    тот же контракт, что у тихого process_codex, чтобы main() считал код возврата
    одинаково для обоих каналов."""
    package_id = package_dir.name
    logger.info(f"=== Параллельный прогон {package_id} (до {max_parallel} вкладок) ===")
    prepared = build_slide_jobs(cfg, logger, package_dir, only_slides)
    if not prepared:
        return (0, 0)
    cfg, output_dir, debug_dir, jobs = prepared

    async with async_playwright() as p:
        # Подключаемся к УЖЕ ОТКРЫТОМУ залогиненному Chrome по CDP (порт 9222) — НЕ поднимаем
        # свой профиль ~/.playwright-chrome-data (там НЕ залогинено) и НЕ открываем новых окон.
        # Вкладки автора НЕ трогаем: каждый рендер открывает и сам закрывает свою новую вкладку.
        cdp_url = cfg.get("cdp_url", "http://localhost:9222")
        # GATE аккаунта: рендерим ТОЛЬКО на Plus. Если это Go/Free/не залогинен —
        # hard abort, ноль рендера (тот предохранитель, которого не было и который
        # раньше молча жёг Go до дневного лимита). Чинится: bash browser.sh ensure.
        import subprocess
        _gate = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("verify_account.py")), "--cdp", cdp_url])
        if _gate.returncode != 0:
            logger.error(f"{package_id}: ACCOUNT GATE FAIL — аккаунт не Plus, рендер ОТМЕНЁН. "
                         "Почини: bash browser.sh ensure")
            return (0, len(jobs))
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context(accept_downloads=True)

        sem = asyncio.Semaphore(max_parallel)
        input_lock = asyncio.Lock()
        tasks = []
        task_pngs = []
        specs = []  # (slide_id, prompt, files, out_png) для ретрая упавших
        for slide_id, prompt, files, out_png in jobs:
            # старт со сдвигом — чтобы не открывать все вкладки в одну миллисекунду (анти-бан)
            await asyncio.sleep(start_delay)
            task_pngs.append(out_png)
            specs.append((slide_id, prompt, files, out_png))
            tasks.append(asyncio.create_task(render_slide_async(
                context, sem, input_lock, logger, cfg, cfg["custom_gpt_url"], slide_id, prompt,
                files, out_png, debug_dir)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if r is True)
        logger.info(f"{package_id}: успех {ok}/{len(tasks)} (параллельно)")
        # РЕТРАЙ упавших (таймаут / rate-limit ChatGPT): 1 доп-попытка ПО ОДНОМУ после паузы.
        # ChatGPT-веб структурно лимитит ~2-3 подряд, пауза даёт квоте выдохнуть (урок по решению автора).
        failed = [i for i, r in enumerate(results) if r is not True]
        if failed:
            cooldown = int(cfg.get("retry_delay_sec", 60))
            logger.info(f"{package_id}: упало {len(failed)} — пауза {cooldown}с и 1 ретрай по одному (лимит ChatGPT)")
            await asyncio.sleep(cooldown)
            retry_sem = asyncio.Semaphore(1)  # ретрай строго по одному — мягче к лимиту
            rtasks = []
            for i in failed:
                sid, prm, fls, opng = specs[i]
                await asyncio.sleep(start_delay)
                rtasks.append(asyncio.create_task(render_slide_async(
                    context, retry_sem, input_lock, logger, cfg, cfg["custom_gpt_url"],
                    sid + "-retry", prm, fls, opng, debug_dir)))
            rres = await asyncio.gather(*rtasks, return_exceptions=True)
            for j, i in enumerate(failed):
                if rres[j] is True:
                    results[i] = True
            ok = sum(1 for r in results if r is True)
            logger.info(f"{package_id}: после ретрая успех {ok}/{len(tasks)}")
        # НЕ закрываем context/browser — это живой Chrome автора (CDP). Свои вкладки рендер закрыл сам.
        # Провенанс: пометить только реально отрисованные GPT-браузером слайды этого прогона
        rendered = [png for png, r in zip(task_pngs, results) if r is True]
        # Кадр в геометрию донора ДО штампа провенанса: иначе нормализация после
        # штампа развалит md5 и гейт доставки зарубит свои же слайды. Лента из
        # разноформатных картинок не собирается, Instagram режет по первому.
        for png, (_sid, _prm, files, _out) in zip(task_pngs, jobs):
            if png in rendered and files:
                CX.fit_exact(png, D.slide_size(files[0]), logger.info, mode="contain")
        if rendered:
            try:
                D.stamp_provenance(output_dir, cfg["custom_gpt_url"], rendered, logger,
                                   source=D.PROVENANCE_SOURCE)
            except Exception as e:
                logger.warning(f"провенанс не записан: {e}")
        return (ok, len(tasks))


PID_FILE = Path("/tmp/auto-uniqualize.pid")


def main():
    import os
    cfg = D.load_config()
    logger = D.setup_logging(cfg["log_file"])
    args = [a for a in sys.argv[1:]]
    # БЕЗОПАСНЫЕ ДЕФОЛТЫ (после инцидента по решению автора): ChatGPT-веб банит за агрессию.
    # 2 вкладки + 14с между стартами = безопасная зона (5 вкладок = rate-limit).
    # Для тихого канала эти цифры значат другое (см. ниже), поэтому сырое значение
    # --parallel держим отдельно и режем потолком уже после выбора канала.
    max_parallel = 2
    start_delay = 14.0
    parallel_given = None
    # Канал рендера. Дефолт тихий: окна браузера у владельца открываться не должны.
    engine = str(cfg.get("engine", "codex"))
    lanes_override = None
    if "--engine" in args:
        i = args.index("--engine"); engine = str(args[i + 1]).lower(); del args[i:i + 2]
    if "--lanes" in args:
        i = args.index("--lanes"); lanes_override = int(args[i + 1]); del args[i:i + 2]
    if "--parallel" in args:
        i = args.index("--parallel"); parallel_given = int(args[i + 1]); del args[i:i + 2]
    if "--delay" in args:
        i = args.index("--delay"); start_delay = max(float(args[i + 1]), 8.0); del args[i:i + 2]
    if engine not in ("codex", "browser"):
        logger.error(f"неизвестный канал {engine!r}, допустимы codex и browser")
        return 2
    if engine == "browser":
        # Жёсткий потолок 3 - про бан ChatGPT-веба, снимать его нельзя.
        max_parallel = min(parallel_given, 3) if parallel_given else max_parallel
    else:
        # Тихому каналу --parallel задаёт число одновременных генераций. Банить
        # тут некому, потолок только чтобы не поднять десяток codex-процессов разом.
        lanes = lanes_override if lanes_override else (parallel_given or int(cfg.get("codex_lanes", 3)))
        lanes = max(1, min(lanes, CODEX_LANES_CAP))
    pkg_id = args[0] if args else None
    only_slides = None
    if len(args) > 1:
        only_slides = {int(x) for x in args[1].split(",") if x.strip().isdigit()}
    if not pkg_id:
        logger.error("укажи package-id")
        return 1
    package_dir = Path(str(Path(cfg["queue_dir"]) / pkg_id))
    if not package_dir.is_dir():
        logger.error(f"пакет не найден: {package_dir}")
        return 1
    if engine == "browser" and async_playwright is None:
        logger.error("браузерный канал просит playwright, а его нет. "
                     "Либо поставь его (setup.sh), либо иди тихим каналом (--engine codex)")
        return 2
    # KILL-SWITCH: пишем PID. Полный стоп: kill -9 $(cat /tmp/auto-uniqualize.pid)
    # Подсказка «чем добить хвосты» РАЗНАЯ у каналов: в тихом режиме никакого
    # playwright-chrome-data не существует, добивать надо процессы codex.
    PID_FILE.write_text(str(os.getpid()))
    tail_hint = ("pkill -9 -f playwright-chrome-data" if engine == "browser"
                 else "pkill -9 -f 'codex exec'   # окон браузера тихий канал не открывает")
    logger.info(f"PID {os.getpid()} → {PID_FILE}. СТОП: kill -9 $(cat {PID_FILE}); {tail_hint}")
    try:
        if engine == "browser":
            logger.info(f"канал: браузерный, {max_parallel} вкладки, старт каждые {start_delay}с (безопасная зона)")
            rendered, planned = asyncio.run(
                process_parallel(cfg, logger, package_dir, only_slides, max_parallel, start_delay))
        else:
            # --delay здесь намеренно игнорируем: пауза между стартами существует
            # только против бана ChatGPT-веба, тихому каналу она чистое ожидание.
            logger.info(f"канал: тихий codex-imagegen, {lanes} полос(ы), окон браузера не открывает "
                        f"(--delay {start_delay:g}с не нужен, пропускаю)")
            rendered, planned = process_codex(cfg, logger, package_dir, only_slides, lanes)
    except CX.CodexQuotaError as e:
        # Лимит аккаунта. Причина печатается ОДИН раз, человеческим языком и с
        # датой открытия - раньше человек видел только «успех 0/8».
        logger.error(f"ПРОГОН ОБОРВАН: {e}")
        logger.error("Пока лимит закрыт, каждый следующий вызов пустой. Варианты: "
                     "дождаться даты выше либо --engine browser")
        return 3
    finally:
        PID_FILE.unlink(missing_ok=True)
    # Код возврата = реальность прогона. 0 только когда вышли ВСЕ слайды: раньше
    # тут стояло безусловное «return 0», и раннеры считали удачей 0 из 8.
    return 0 if planned and rendered == planned else 1


if __name__ == "__main__":
    sys.exit(main())
