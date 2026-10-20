#!/usr/bin/env python3
"""
render-from-prompt.py — рендер слайда(ов) карусели ПО ПРОМПТУ (CTA-плашки и
слайды «с нуля»).

Каналов два, интерфейс запуска у обоих ОДИН И ТОТ ЖЕ:

  codex (ПО УМОЛЧАНИЮ, правка владельца) - тихий headless-канал
          `codex exec` → системный скилл imagegen. Ни одного окна браузера, экран,
          буфер обмена и фронтмост-окно не трогаются: во время прогона за
          компьютером можно спокойно работать. Владелец дословно: «было бы
          прикольно, чтобы у меня окна браузера не открывались и не мешали мне».
  browser (--engine browser) - старый путь: подключение к ЖИВОМУ браузеру
          владельца (CDP :9222), где есть залогиненная сессия ChatGPT, и работа в
          кастомке carousels-<твой-бренд>. Оставлен запасным на случай, когда
          нужна именно кастомка со своим системным промптом.

Почему дефолт именно тихий: браузерный канал физически занимает единственный
Chrome владельца, поэтому параллелить нельзя и работать во время рендера нельзя.
У codex общего ресурса нет.

Совместимость: десятки .sh-раннеров зовут этот файл позиционными аргументами
(`render-from-prompt.py "queue/$pkg/cta" "output/$pkg" 7`). Разбор аргументов не
менялся - старые команды просто стали тихими. Флаги (если нужны) ставятся в любом
месте строки и вырезаются до позиционного разбора.

Usage: render-from-prompt.py [--engine codex|browser] [--size WxH] [--ref]
                             <prompts_dir> <out_dir> [NN ...]
       prompts_dir/prompt-NN.txt -> out_dir/slide-NN.png

Донор ВЫКЛЮЧЕН по умолчанию (правка 03.08.2026). Этот файл рисует «с нуля»:
CTA-плашки, обложки, свои слайды. В реальной раскладке пакета prompt-NN.txt и
ЧУЖОЙ оригинал конкурента slide-NN.jpg лежат в ОДНОЙ папке (улика:
queue/appinventiv-claude-cowork-ru/), а шесть раннеров зовут нас именно формой
`render-from-prompt.py queue/$p output/$p 7`. С автоподхватом донора наша плашка
молча получала референсом чужой слайд - это лукалайк вместо своей плашки, прямо
запрещено каноном владельца. Поэтому автоподхват включается только явным --ref;
без него идёт чистая текстовая генерация, как было до появления донора.
Флаг --no-ref принимается по-прежнему (теперь это просто дефолт) - старые вызовы
раннеров ломать нельзя.
"""
import asyncio, json, os, sys, time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    # Тихому каналу playwright не нужен вообще: падать из-за его отсутствия
    # имеет смысл только тогда, когда реально попросили браузерный рендер.
    async_playwright = None

# Тихий канал: codex exec → imagegen. Движок общий с обложками статей и с
# driver.py, лежит на уровне scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_image as CX

CFG_PATH = Path("~/.business/scripts/auto-uniqualize/config.json")
try:
    CFG = json.loads(CFG_PATH.read_text())
except Exception:
    # Конфиг нужен только браузерному каналу (URL кастомки, таймауты опроса
    # вкладки). Тихий канал без него живёт, поэтому не роняем процесс.
    CFG = {}

PID_FILE = Path("/tmp/auto-uniqualize.pid")
CDP = "http://127.0.0.1:9222"
IMG_SEL = ('img[src*="backend-api/estuary"], '
           'img[src*="oaiusercontent"], img[src*="files.oaiusercontent"], '
           'img[alt*="lide"], img[alt*="enerate"]')

#: Геометрия слайда карусели 4:5. Своей константы в этом файле раньше не было
#: (кастомка брала размер из системного промпта), а тихому каналу размер надо
#: назвать явно, иначе он рисует квадрат и лента разъезжается.
DEFAULT_SLIDE_SIZE = (1080, 1350)

#: Возможные имена донорского слайда рядом с промптом.
DONOR_STEMS = ("slide", "donor", "ref")
DONOR_EXTS = (".jpg", ".jpeg", ".png", ".webp")


class ChannelNotReady(RuntimeError):
    """Канал вообще не поднялся (нет логина codex и т.п.).

    Отдельный тип нужен, чтобы не путать «канал не стартовал» с числом успешных
    слайдов: раньше run_codex возвращал 1 как код ошибки, а main читал это как
    «один слайд вышел» и завершал пустой прогон нулём, то есть «успешно».
    """


# ── Тихий канал ─────────────────────────────────────────────────────────────────

def find_donor(prompts_dir: Path, nn: str) -> Path | None:
    """Донорская картинка ДЛЯ ЭТОГО ЖЕ номера слайда, лежащая рядом с промптом.

    Вызывается ТОЛЬКО при явном --ref. По умолчанию донор не ищется вовсе:
    prompt-NN.txt и чужой оригинал slide-NN.jpg реально лежат в одной папке
    пакета, и автоподхват подсовывал слайд конкурента туда, где мы рисуем СВОЮ
    плашку с нуля.
    """
    for stem in DONOR_STEMS:
        for ext in DONOR_EXTS:
            cand = prompts_dir / f"{stem}-{nn}{ext}"
            if cand.exists():
                return cand
    return None


def out_size(donor: Path | None, forced: tuple[int, int] | None) -> tuple[int, int]:
    """Размер выхода: явный флаг → геометрия донора → дефолтные 4:5.

    Геометрию донора повторяем по той же причине, что и driver.py: ленту нельзя
    собирать из разноформатных картинок, Instagram режет всё по первому слайду.
    """
    if forced:
        return forced
    if donor is not None:
        try:
            from PIL import Image
            with Image.open(donor) as im:
                w, h = im.size
            return (w - w % 2, h - h % 2)
        except Exception:
            pass
    return DEFAULT_SLIDE_SIZE


def render_one_codex(prompt: str, donor: Path | None, out_path: Path,
                     forced_size: tuple[int, int] | None) -> bool:
    """Тихий двойник render_one: тот же промпт, то же вложение, ноль окон."""
    class _L:
        def info(self, m): print(f"  {m}", flush=True)

    try:
        CX.render(
            prompt,
            out_path,
            refs=[donor] if donor else [],
            size=out_size(donor, forced_size),
            attempts=int(CFG.get("codex_attempts", 2)),
            timeout=int(CFG.get("codex_timeout", 600)),
            logger=_L(),
        )
        return True
    except CX.CodexQuotaError:
        # Лимит аккаунта - внешний блокер, не брак этого слайда. Наверх, там
        # прогон обрывается и причина печатается один раз с датой открытия.
        raise
    except CX.CodexImageError as e:
        print(f"  ОШИБКА: {e}")
        return False


def run_codex(prompts: list[Path], out_dir: Path, use_ref: bool,
              forced_size: tuple[int, int] | None) -> tuple[int, int]:
    """Последовательный прогон тихим каналом.

    Возвращает (сколько вышло, сколько промптов было) - именно пару, а не одно
    число: смысл возвращаемого раньше был двойным (и «код ошибки», и «счётчик»),
    из-за чего пустой прогон уезжал наверх как успешный.
    Канал не поднялся - ChannelNotReady. Лимит аккаунта - CodexQuotaError.

    Пауз между слайдами тут нет: они стояли против rate-limit живой вкладки
    ChatGPT, у codex общего ресурса и очереди во вкладке нет.
    """
    try:
        CX.ensure_home()
    except CX.CodexImageError as e:
        raise ChannelNotReady(f"тихий канал не готов: {e}") from e
    ok = 0
    for pf in prompts:
        nn = pf.stem.split("-")[-1]
        donor = find_donor(pf.parent, nn) if use_ref else None
        print(f"[{nn}] {pf.name}" + (f" + донор {donor.name}" if donor else " (текст, без донора)"))
        if render_one_codex(pf.read_text(encoding="utf-8"), donor,
                            out_dir / f"slide-{nn}.png", forced_size):
            ok += 1
    print(f"=== готово: {ok}/{len(prompts)} (тихий канал codex) ===")
    return (ok, len(prompts))


# ── Браузерный канал (запасной) ─────────────────────────────────────────────────

async def render_one(context, url, prompt, out_path):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector('#prompt-textarea, div.ProseMirror[contenteditable="true"]',
                                     state="visible", timeout=40000)
        await asyncio.sleep(2)
        body = (await page.inner_text("body")).lower()
        if "too many requests" in body or "making requests too quickly" in body:
            print("  RATE-LIMIT — стоп"); return False
        editor = await page.query_selector('#prompt-textarea') \
            or await page.query_selector('div.ProseMirror[contenteditable="true"]')
        await editor.click(); await asyncio.sleep(0.5)
        await page.evaluate("async (t) => { await navigator.clipboard.writeText(t); }", prompt)
        await asyncio.sleep(0.3)
        await page.keyboard.press("Meta+V"); await asyncio.sleep(1.5)
        send = await page.query_selector('button[data-testid="send-button"]:not([disabled])') \
            or await page.query_selector('button[aria-label*="end" i]:not([disabled])') \
            or await page.query_selector('form button[type="submit"]:not([disabled])')
        if send: await send.click()
        else: await editor.focus(); await page.keyboard.press("Enter")
        print("  отправлен, жду генерацию...")
        await asyncio.sleep(8)
        timeout = CFG.get("generation_timeout_sec", 200); poll = CFG.get("poll_interval_sec", 4)
        baseline = len(await page.query_selector_all(IMG_SEL)); start = time.time()
        got_new = False
        while time.time() - start < timeout:
            await asyncio.sleep(poll)
            try: n = len(await page.query_selector_all(IMG_SEL))
            except Exception as e: print(f"  page closed: {e}"); break
            if n > baseline:
                got_new = True
                await asyncio.sleep(6); break
        else:
            print(f"  timeout {timeout}s")
        # GUARD ПАССХРУ (урок по решению автора): нет новой картинки = не сохранять брак
        if not got_new:
            print("  новой картинки нет (таймаут) — не сохраняю пассхру, брак"); return False
        imgs = await page.query_selector_all(IMG_SEL)
        if not imgs: print("  PNG не найдено"); return False
        src = await imgs[-1].get_attribute("src")
        resp = await context.request.get(src)
        if resp.ok:
            out_path.write_bytes(await resp.body()); print(f"  сохранён -> {out_path}"); return True
        return False
    finally:
        try: await page.close()
        except Exception: pass


async def run_browser(prompts: list[Path], out_dir: Path) -> tuple[int, int]:
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        ok = 0
        for i, pf in enumerate(prompts):
            nn = pf.stem.split("-")[-1]; print(f"[{nn}] {pf.name}")
            r = await render_one(context, CFG["custom_gpt_url"], pf.read_text(encoding="utf-8"), out_dir / f"slide-{nn}.png")
            ok += 1 if r else 0
            if i < len(prompts) - 1: await asyncio.sleep(30)
        # НЕ закрываем браузер автора — только отключаемся
        print(f"=== готово: {ok}/{len(prompts)} ===")
        return (ok, len(prompts))


# ── Точка входа ─────────────────────────────────────────────────────────────────

def parse_flags(argv: list[str]) -> tuple[str, tuple[int, int] | None, bool, list[str]]:
    """Вырезает флаги из строки запуска и отдаёт хвост позиционных аргументов.

    Флаги вырезаются ДО позиционного разбора, поэтому старые вызовы раннеров
    (`... queue/$pkg/cta output/$pkg 7`) читаются ровно как раньше.
    """
    engine = str(CFG.get("engine", "codex"))
    forced_size = None
    # Донор ВЫКЛЮЧЕН по умолчанию: этот файл рисует с нуля, а рядом с промптом в
    # пакете лежит чужой оригинал конкурента - автоподхват давал лукалайк.
    use_ref = False
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--engine" and i + 1 < len(argv):
            engine = argv[i + 1]; i += 2; continue
        if a == "--size" and i + 1 < len(argv):
            w, h = argv[i + 1].lower().split("x")
            forced_size = (int(w), int(h)); i += 2; continue
        if a == "--ref":
            # Осознанное включение донора: только когда человек знает, что рядом
            # с промптом лежит НАША, а не чужая картинка.
            use_ref = True; i += 1; continue
        if a == "--no-ref":
            # Совместимость: флаг остался у старых вызовов, теперь это дефолт.
            use_ref = False; i += 1; continue
        rest.append(a); i += 1
    return engine, forced_size, use_ref, rest


def main() -> int:
    engine, forced_size, use_ref, argv = parse_flags(sys.argv[1:])
    if len(argv) < 2:
        print(__doc__); return 1
    if engine not in ("codex", "browser"):
        print(f"неизвестный канал {engine!r}, допустимы codex и browser"); return 2
    if engine == "browser" and async_playwright is None:
        print("браузерный канал просит playwright, а его нет. "
              "Либо поставь его (setup.sh), либо иди тихим каналом (--engine codex)")
        return 2

    prompts_dir = Path(argv[0]); out_dir = Path(argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
    only = [f"{int(x):02d}" for x in argv[2:]] if len(argv) > 2 else None
    prompts = sorted(prompts_dir.glob("prompt-*.txt"))
    if only: prompts = [p for p in prompts if p.stem.split("-")[-1] in only]
    if not prompts: print("нет prompt-NN.txt"); return 1
    PID_FILE.write_text(str(os.getpid()))
    try:
        if engine == "codex":
            ok, total = run_codex(prompts, out_dir, use_ref, forced_size)
        else:
            ok, total = asyncio.run(run_browser(prompts, out_dir))
    except ChannelNotReady as e:
        print(str(e))
        return 2
    except CX.CodexQuotaError as e:
        # Лимит аккаунта. Человеческая причина с датой печатается ОДИН раз,
        # остальные промпты не гоняем: они всё равно вернутся пустыми.
        print(f"ПРОГОН ОБОРВАН: {e}")
        print("Пока лимит закрыт, каждый следующий вызов пустой. Варианты: "
              "дождаться даты выше либо --engine browser")
        return 3
    finally:
        try: PID_FILE.unlink()
        except Exception: pass
    # Код возврата = реальность: 0 только когда вышли ВСЕ запрошенные слайды.
    # Раньше единица от run_codex («канал не готов») читалась как «один слайд
    # вышел», и прогон без картинок завершался нулём, то есть «успешно».
    return 0 if total and ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
