#!/usr/bin/env python3
"""
Playwright driver v3 — pure per-slide, без Code Interpreter.

Каждая входная картинка пакета (cover-frame / step-NN / slide-NN) шлётся в
Custom GPT как ОДИН файл + короткая команда. Весь интеллект (зоны, стили,
watermark, размер, выбор стиля) живёт в системном промпте кастомки —
драйвер ничего не диктует. Резка/Code Interpreter убраны: GPT их не исполняет.

Usage:
    python3 driver.py                  # all packages from queue
    python3 driver.py <package-id>     # one specific package
"""

import hashlib
import json
import logging
import shutil
import sys
import threading
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import BrowserContext
except ImportError:
    # Тихому каналу (--engine codex) playwright не нужен вообще - падаем только
    # тогда, когда реально попросили браузерный рендер.
    sync_playwright = None
    BrowserContext = object

# Тихий канал: codex exec → imagegen, ни одного окна браузера. Движок общий с
# рендером обложек (seo/images/gpt_render.py), лежит на уровне scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_image as CX

# === Провенанс GPT-рендера (guard от само-рендера) ===
# Слайды ОБЯЗАНЫ быть отрисованы Custom GPT в браузере, НЕ вручную (Higgsfield/gpt_image/код/HTML→PNG).
# Driver штампует сюда каждый реально отрисованный PNG; telegram-deliver откажется слать без штампа.
PROVENANCE_FILE = "_render_provenance.json"
PROVENANCE_SOURCE = "chatgpt-custom-gpt-browser"
#: Тихий канал ставит свой штамп - доставка знает оба и по-прежнему режет
#: всё остальное (рисование кодом, Higgsfield, HTML→PNG).
PROVENANCE_SOURCE_CODEX = CX.PROVENANCE_SOURCE          # "codex-imagegen-headless"
PROVENANCE_SOURCES = (PROVENANCE_SOURCE, PROVENANCE_SOURCE_CODEX)


def stamp_provenance(output_dir: Path, custom_gpt_url: str, slide_pngs, logger=None,
                     source: str = PROVENANCE_SOURCE):
    prov_path = output_dir / PROVENANCE_FILE
    data = {"generated_by": source, "custom_gpt_url": custom_gpt_url, "slides": {}}
    if prov_path.exists():
        try:
            data = json.loads(prov_path.read_text())
            data.setdefault("slides", {})
            data["generated_by"] = source
        except Exception:
            pass
    for png in slide_pngs:
        png = Path(png)
        if png.exists():
            data["slides"][png.name] = hashlib.md5(png.read_bytes()).hexdigest()
    prov_path.write_text(json.dumps(data, indent=2))
    if logger:
        logger.info(f"провенанс GPT-рендера записан → {prov_path.name} ({len(data['slides'])} слайдов)")

# Дизайн-система карусели (ЗОНЫ 1-4): единый визуальный профиль, бинарное
# решение по лицам, CTA-мок ТГ автора, полный промпт-builder на каждый слайд.
from design_system import (
    load_design_profile,
    load_face_decision,
    preflight_face_checklist,
    build_slide_prompt,
    is_last_slide,
)


SCRIPT_DIR = Path(__file__).parent.resolve()


def load_config() -> dict:
    cfg_path = SCRIPT_DIR / "config.json"
    if not cfg_path.exists():
        sys.stderr.write(f"ERROR: {cfg_path} не найден.\n")
        sys.exit(1)
    with open(cfg_path) as f:
        cfg = json.load(f)
    for k in ("chrome_profile_dir", "queue_dir", "output_dir", "archive_dir", "log_file"):
        cfg[k] = str(Path(cfg[k]).expanduser().resolve())
    return cfg


def setup_logging(log_file: str) -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("auto-uniqualize")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh)
    return logger


def render_with_my_text(translation: str, face: bool) -> str:
    """LEGACY-обёртка (оставлена для обратной совместимости/тестов).

    Боевой путь теперь — build_slide_prompt() из design_system.py с полной
    схемой (design-tokens + face-policy + правила). Эта функция — простой
    промпт без дизайн-профиля, на случай прямого вызова без пакета."""
    return build_slide_prompt(
        translation=translation,
        design=load_design_profile(SCRIPT_DIR / "__none__"),  # пустой профиль
        face_policy="author-only" if face else "none",
        face_in_frame=face,
        with_face_attachment=face,
    )


def slide_translation(package_dir: Path, idx: int) -> str | None:
    """Мой готовый перевод текста слайда, если положен рядом: slide-NN.txt."""
    p = package_dir / f"slide-{idx:02d}.txt"
    if p.exists():
        t = p.read_text(encoding="utf-8").strip()
        return t or None
    return None


# Команда на слайд. Всё остальное знает системный промпт кастомки.
SLIDE_PROMPT = (
    "Уникализируй этот слайд карусели по своему системному промпту. "
    "Сохрани структуру и расположение элементов оригинала (тот же тип слайда, "
    "та же раскладка, та же роль в карусели), визуал пересоздай уникально. "
    "ВЕСЬ текст на слайде переведи на русский язык, без английских вставок. "
    "Переводи по СМЫСЛУ и в контексте слайда, не дословной калькой с английского. "
    "Подбирай слова так, как реально говорят по-русски: если прямой перевод звучит "
    "чужеродно — найди естественный русский эквивалент по смыслу. "
    "Если на слайде есть сравнение или контраст (платный сервис против бесплатного "
    "инструмента, экономия) — передай его законченной мыслью со сказуемым и выводом, "
    "не обрывай фразы на полуслове. "
    "Верни одну готовую картинку."
)

# Команда когда вторым файлом приложено лицо автора (face-swap).
# Кастомка сама решает: автор → меняем, известная личность/герой → оставляем.
SLIDE_PROMPT_WITH_FACE = (
    "Первое вложение — слайд карусели для уникализации. Второе вложение — это я, моё лицо. "
    "Уникализируй слайд по своему системному промпту. "
    "Сохрани структуру и расположение элементов оригинала (тот же тип слайда, "
    "та же раскладка, та же роль в карусели), визуал пересоздай уникально. "
    "ВЕСЬ текст переведи на русский язык, без английских вставок. "
    "Переводи по СМЫСЛУ, не дословно: если есть сравнение или контраст (платный "
    "сервис против бесплатного инструмента, экономия) — передай законченной мыслью "
    "со сказуемым и выводом, не обрывай фразы на полуслове. "
    "Про лицо: ТОЛЬКО если на слайде портрет АВТОРА контента (крупное лицо блогера, "
    "селфи, говорящая голова создателя) — замени его лицо на моё со второго фото, "
    "фотореалистично и узнаваемо. Если это известная личность, герой новости или "
    "человек по теме контента — НЕ трогай, оставь оригинальное лицо. "
    "Новых людей не добавляй. Верни одну готовую картинку."
)


# ============================================================
# Детекция лица — лицо автора прикладываем ТОЛЬКО к слайдам,
# где в оригинале есть человек. Решение «автор или герой
# контента» отдаём кастомке (семантика через промпт).
# ============================================================

_FACE_CASCADE = None


def has_face(image_path: Path) -> bool:
    """True если на слайде оригинала есть фронтальное лицо (грубый фильтр)."""
    global _FACE_CASCADE
    try:
        import cv2
        if _FACE_CASCADE is None:
            _FACE_CASCADE = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        img = cv2.imread(str(image_path))
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = _FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        return len(faces) > 0
    except Exception:
        # opencv недоступен или ошибка — НЕ прикладываем лицо (безопасный дефолт)
        return False


# ============================================================
# Per-slide rendering (один таб = один слайд)
# ============================================================


def render_slide(
    context: BrowserContext,
    logger: logging.Logger,
    custom_gpt_url: str,
    slide_id: str,
    prompt: str,
    input_files: list[Path],
    output_path: Path,
    debug_dir: Path,
    cfg: dict,
) -> bool:
    """Открывает новый таб, рендерит один слайд, скачивает PNG.

    input_files: список вложений к запросу. [слайд] или [слайд, лицо].
    """
    page = context.new_page()

    def snap(label: str) -> None:
        try:
            page.screenshot(path=str(debug_dir / f"{slide_id}-{label}.png"), full_page=True)
        except Exception:
            pass

    try:
        page.goto(custom_gpt_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_selector(
            '#prompt-textarea, div.ProseMirror[contenteditable="true"]',
            state="visible",
            timeout=30000,
        )
        time.sleep(2)

        # Загрузка вложений (слайд + опционально лицо) одним вызовом
        if input_files:
            file_input = page.query_selector('input[type="file"]')
            if not file_input:
                snap("no-file-input")
                logger.error(f"{slide_id}: input[type=file] не найден")
                return False
            file_input.set_input_files([str(f) for f in input_files])
            time.sleep(4 + 3 * len(input_files))  # ждём превью всех вложений

        # Промт через clipboard paste
        editor = page.query_selector('#prompt-textarea') \
            or page.query_selector('div.ProseMirror[contenteditable="true"]')
        if not editor:
            snap("no-editor")
            logger.error(f"{slide_id}: editor не найден")
            return False
        editor.click()
        time.sleep(0.5)
        page.evaluate(
            """async (text) => { await navigator.clipboard.writeText(text); }""",
            prompt,
        )
        time.sleep(0.3)
        page.keyboard.press("Meta+V")
        time.sleep(1.5)

        # Submit
        send_btn = page.query_selector('button[data-testid="send-button"]:not([disabled])') \
            or page.query_selector('button[aria-label*="end" i]:not([disabled])') \
            or page.query_selector('form button[type="submit"]:not([disabled])')
        if send_btn:
            send_btn.click()
        else:
            editor.focus()
            page.keyboard.press("Enter")
        logger.info(f"{slide_id}: команда отправлена, ждём генерацию...")
        time.sleep(3)

        # Wait: ждём НОВУЮ картинку (сверх загруженного превью входных файлов).
        timeout = cfg.get("generation_timeout_sec", 600)
        poll = cfg.get("poll_interval_sec", 4)
        # тот же широкий селектор что и для скачивания (картинка ChatGPT ловится по alt)
        img_sel = ('img[src*="backend-api/estuary"], '
                   'img[src*="oaiusercontent"], img[src*="files.oaiusercontent"], '
                   'img[alt*="lide"], img[alt*="enerate"]')
        baseline = len(page.query_selector_all(img_sel))
        logger.info(f"{slide_id}: baseline картинок = {baseline}")
        start = time.time()
        ticks = 0
        while time.time() - start < timeout:
            time.sleep(poll)
            n = len(page.query_selector_all(img_sel))
            ticks += 1
            if ticks % 5 == 0:
                logger.info(f"{slide_id}: ждём... картинок={n} (baseline={baseline}), {int(time.time()-start)}с")
            if n > baseline:
                logger.info(f"{slide_id}: новая картинка (n={n}>{baseline}), даю дорисоваться")
                time.sleep(6)
                break
        else:
            logger.warning(f"{slide_id}: timeout {timeout}s (картинок={len(page.query_selector_all(img_sel))}, baseline={baseline})")

        snap("done")

        # Скачать последнюю картинку (сгенерированную). Широкий рабочий селектор.
        imgs = page.query_selector_all(
            'img[src*="backend-api/estuary"], img[src*="oaiusercontent"], img[src*="files.oaiusercontent"], img[alt*="lide"], img[alt*="enerate"]'
        )
        if not imgs:
            logger.warning(f"{slide_id}: PNG в ответе не найдено")
            return False

        # Берём последнюю (самую свежую) картинку
        src = imgs[-1].get_attribute("src")
        if not src:
            return False
        try:
            resp = context.request.get(src)
            if resp.ok:
                output_path.write_bytes(resp.body())
                logger.info(f"{slide_id}: PNG сохранён → {output_path.name}")
                return True
        except Exception as e:
            logger.error(f"{slide_id}: ошибка скачивания: {e}")
        return False

    except Exception as e:
        logger.error(f"{slide_id}: ошибка: {e}", exc_info=True)
        snap("error")
        return False
    finally:
        try:
            page.close()
        except Exception:
            pass


# ============================================================
# Package processing
# ============================================================


def slide_size(img: Path) -> tuple[int, int]:
    """Геометрия выходного слайда = геометрия донорского слайда, округлённая
    до чётного. Ленту нельзя собирать из разноформатных картинок - Instagram
    режет по первому слайду."""
    try:
        from PIL import Image
        with Image.open(img) as im:
            w, h = im.size
        return (w - w % 2, h - h % 2)
    except Exception:
        return CX.SIZES["slide"]


#: Лимит аккаунта - состояние ПРОЦЕССА, а не одного слайда. Флаг взводится первым
#: же слайдом, который упёрся в лимит, и остальные полосы даже не начинают
#: генерацию: иначе пул успевает раздать очередь и сжечь ещё N пустых вызовов.
_QUOTA_LOCK = threading.Lock()
_QUOTA_ERR: list[CX.CodexQuotaError] = []


def quota_tripped() -> CX.CodexQuotaError | None:
    """Первая пойманная ошибка лимита или None. Читается из любой полосы."""
    with _QUOTA_LOCK:
        return _QUOTA_ERR[0] if _QUOTA_ERR else None


def render_slide_codex(
    logger: logging.Logger,
    slide_id: str,
    prompt: str,
    input_files: list[Path],
    output_path: Path,
    cfg: dict,
) -> bool:
    """Тихий двойник render_slide: тот же промпт, те же вложения, ноль окон.

    Донорский слайд и (опционально) фото лица уходят в codex как референсы -
    это тот же image-in → image-out, что делала кастомка в браузере, только
    процессом в фоне. Экран, буфер обмена и фронтмост-окно не трогаются.
    """
    already = quota_tripped()
    if already is not None:
        # Лимит уже пойман другой полосой - новую генерацию не начинаем вообще.
        raise already
    try:
        CX.render(
            prompt,
            output_path,
            refs=input_files,
            size=slide_size(input_files[0]) if input_files else CX.SIZES["slide"],
            attempts=int(cfg.get("codex_attempts", 2)),
            timeout=int(cfg.get("codex_timeout", 600)),
            logger=logger,
        )
        return True
    except CX.CodexQuotaError as e:
        # ЛИМИТ АККАУНТА - внешний блокер, а не брак этого слайда. Глотать его тут
        # нельзя: иначе машина молча перемелет всю очередь сотнями бесполезных
        # вызовов, а человек увидит «успех 0/8» вместо «лимит до 2 сентября».
        # Взводим флаг для соседних полос и пробрасываем наверх - там прогон
        # обрывается, а причина печатается ОДИН раз, с датой открытия лимита.
        with _QUOTA_LOCK:
            if not _QUOTA_ERR:
                _QUOTA_ERR.append(e)
        raise
    except CX.CodexImageError as e:
        logger.error(f"{slide_id}: {e}")
        return False


def collect_input_images(package_dir: Path) -> list[Path]:
    """Все входные картинки пакета в порядке слайдов.

    Carousel-пакет: slide-NN.png.
    Reel-пакет: cover-frame.png + step-NN.png.
    Каждая картинка = один слайд к уникализации.
    """
    slides = sorted(package_dir.glob("slide-*.png")) + sorted(package_dir.glob("slide-*.jpg"))
    slides = sorted(slides, key=lambda p: p.stem)
    if slides:
        return slides
    images = []
    cover = package_dir / "cover-frame.png"
    if cover.exists():
        images.append(cover)
    images += sorted(package_dir.glob("step-*.png"))
    return images


def process_package(playwright, cfg: dict, logger: logging.Logger, package_dir: Path,
                    only_slides: set | None = None, engine: str = "codex",
                    lanes: int = 3) -> tuple[int, int]:
    """Рендерит пакет и возвращает (сколько отрисовано, сколько планировалось).

    Раньше отдавалось bool «хоть что-то вышло» - и раннеры считали удачей прогон,
    где из 8 слайдов вышел один. Пара чисел даёт вызывающему настоящую картину,
    из неё main() собирает честный код возврата.
    Лимит аккаунта (CodexQuotaError) наверх ПРОБРАСЫВАЕТСЯ: это не результат
    пакета, а причина немедленно оборвать весь прогон.
    """
    package_id = package_dir.name
    logger.info(f"=== Processing package {package_id} ===")

    images = collect_input_images(package_dir)
    if not images:
        logger.error(f"{package_id}: ни slide-*.png, ни cover/step-*.png — пакет невалиден")
        return (0, 0)

    if only_slides:
        logger.info(f"{package_id}: точечная регенерация слайдов {sorted(only_slides)} (готовые не трогаю)")
    else:
        logger.info(f"{package_id}: {len(images)} слайдов к рендеру")

    # Сколько слайдов ДОЛЖНО выйти в этом прогоне. При точечной регенерации это
    # не len(images), а только попавшие под фильтр - иначе «успех 1/1» выглядел бы
    # как «1/8» и честный код возврата был бы враньём в другую сторону.
    planned = len([i for i in range(1, len(images) + 1)
                   if not only_slides or i in only_slides])

    output_dir = Path(cfg["output_dir"]) / package_id
    # rmtree только при полном прогоне; при точечной регенерации готовые слайды сохраняем
    if output_dir.exists() and not only_slides:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    debug_dir = Path(cfg["log_file"]).parent / "debug" / package_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Лицо автора для face-swap (если задано в config и файл существует)
    face_file = None
    face_cfg = cfg.get("face_image")
    if face_cfg:
        fp = Path(face_cfg).expanduser()
        if fp.exists():
            face_file = fp
            logger.info(f"{package_id}: лицо для swap → {fp.name}")
        else:
            logger.warning(f"{package_id}: face_image указан но файла нет: {fp}")

    # ЗОНА 1 — единый дизайн-профиль карусели (_design.json / _design.txt).
    # Пустой профиль = старое поведение (обратная совместимость).
    design = load_design_profile(package_dir)
    if not design.is_empty():
        logger.info(f"{package_id}: дизайн-профиль найден "
                    f"(фишка: {design.signature[:60] or '—'})")
    else:
        logger.info(f"{package_id}: дизайн-профиля нет — рендер без единого стиля")

    # ЗОНА 2 — режим финального слайда: "tg" (мок ТГ-канала, если на оригинале
    # был телефон/экран с чужим назначением) или "codeword" (чистый призыв,
    # дефолт). Решение задаётся файлом _cta_mode.txt в пакете.
    cta_mode_path = package_dir / "_cta_mode.txt"
    cta_mode = cta_mode_path.read_text().strip().lower() if cta_mode_path.exists() else "codeword"
    logger.info(f"{package_id}: режим CTA = {cta_mode}"
                + (" (мок ТГ)" if cta_mode == "tg" else " (чистый призыв, без ТГ)"))

    # ЗОНА 3 — pre-flight чеклист лиц + бинарное решение на всю карусель.
    pf = preflight_face_checklist(images, has_face)
    face_decision = load_face_decision(package_dir)
    policy_src = ("явно из _faces.txt" if face_decision.explicit
                  else "дефолт, подсказка=" + pf["suggestion"])
    slides_with_face = pf["slides_with_face"] or "[]"
    logger.info(
        f"{package_id}: pre-flight лица — {pf['face_count']}/{pf['total']} слайдов "
        f"с лицом {slides_with_face}; policy={face_decision.policy} ({policy_src})"
    )
    # Если решено «менять у всех/у автора», но фото лица нет — менять нечем.
    if face_decision.swap_anywhere() and face_file is None:
        logger.warning(f"{package_id}: policy={face_decision.policy}, но face_image "
                       "недоступен — лицо меняться не будет")

    total_slides = len(images)

    context = None
    if engine == "browser":
        # ЕДИНАЯ политика браузера: НЕ поднимаем свой профиль (это давало «новый Chrome
        # без логина / инкогнито»), а коннектимся к живому CDP-Chrome (:9222) — тому же,
        # что и driver_parallel.py. Перед этим — GATE «это Plus?», иначе стоп (ноль рендера).
        import subprocess
        cdp_url = cfg.get("cdp_url", "http://127.0.0.1:9222")
        _gate = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("verify_account.py")), "--cdp", cdp_url])
        if _gate.returncode != 0:
            logger.error(f"{package_id}: ACCOUNT GATE FAIL — аккаунт не Plus, рендер ОТМЕНЁН. "
                         "Почини: bash browser.sh ensure")
            return (0, planned)
        cdp_browser = playwright.chromium.connect_over_cdp(cdp_url)
        context = cdp_browser.contexts[0] if cdp_browser.contexts else cdp_browser.new_context(accept_downloads=True)

        # Закрыть дефолтную about:blank страницу что Chrome открывает
        if context.pages:
            try:
                context.pages[0].close()
            except Exception:
                pass
    else:
        # Тихий канал: аккаунт-гейт про Plus здесь неприменим (мы не в вебе ChatGPT),
        # проверяем ровно то, что нужно этому каналу - логин codex и изолированный дом.
        try:
            CX.ensure_home(logger)
        except CX.CodexImageError as e:
            logger.error(f"{package_id}: тихий канал не готов — {e}")
            return (0, planned)
        logger.info(f"{package_id}: канал = тихий codex-imagegen "
                    f"(окон браузера не открывает, полос параллели: {lanes})")

    # Браузерный канал рисует строго по одному (sync Playwright не thread-safe для
    # общего контекста, да и окно на машине одно). У тихого канала общего ресурса нет,
    # поэтому слайды копятся в jobs и рисуются пачкой в несколько полос.
    success_count = 0
    rendered_pngs = []
    jobs: list[tuple] = []
    quota_stop = None      # сюда ляжет CodexQuotaError, если лимит аккаунта выжжен
    try:
        for idx, img in enumerate(images, start=1):
            if only_slides and idx not in only_slides:
                continue  # точечная регенерация — этот слайд уже готов, не трогаем
            slide_id = f"slide-{idx:02d}-{img.stem}"

            # Есть ли лицо в кадре этого слайда (грубый opencv-фильтр).
            face_in_frame = face_file is not None and has_face(img)
            # Прикладываем фото автора только если: policy разрешает замену,
            # фото доступно и на слайде есть лицо. Бинарность — на уровне policy.
            with_face_attachment = (
                face_decision.swap_anywhere() and face_file is not None and face_in_frame
            )

            trans = slide_translation(package_dir, idx)
            cta = is_last_slide(idx, total_slides)

            # ЗОНА 4 — полный промпт слайда из всех слоёв (текст + design +
            # лицо + правила + CTA-мок ТГ для последнего слайда).
            prompt = build_slide_prompt(
                translation=trans,
                design=design,
                face_policy=face_decision.policy,
                face_in_frame=face_in_frame,
                with_face_attachment=with_face_attachment,
                is_cta=cta,
                cta_mode=cta_mode,
                cta_topic=design.notes if cta else "",
            )
            files = [img, face_file] if with_face_attachment else [img]
            # ЗОНА 2 — скриншот ТГ-канала прикладываем ТОЛЬКО в режиме мока ТГ
            # (cta_mode=="tg"). Для чистого призыва с код-словом он не нужен.
            if cta and cta_mode == "tg":
                channel_ref = Path("~/.business/assets/tg-channel/channel-1.jpg").expanduser()
                if channel_ref.exists():
                    files.append(channel_ref)

            mode = "мой текст" if trans else "перевод кастомкой (fallback)"
            tag = []
            if cta:
                tag.append("CTA/мок-ТГ+скрин" if cta_mode == "tg" else "CTA/чистый призыв")
            if with_face_attachment:
                tag.append("лицо приложено")
            elif face_in_frame:
                tag.append(f"лицо в кадре, policy={face_decision.policy}")
            logger.info(f"{slide_id}: {mode}" + (f" [{', '.join(tag)}]" if tag else ""))

            out_png = output_dir / f"slide-{idx:02d}.png"
            if engine == "codex":
                jobs.append((slide_id, prompt, files, out_png))
                continue
            ok = render_slide(
                context,
                logger,
                cfg["custom_gpt_url"],
                slide_id,
                prompt,
                files,
                out_png,
                debug_dir,
                cfg,
            )
            if ok:
                # Кадр в геометрию донора - ЛЕНТА не собирается из разноформатных
                # слайдов, Instagram режет её по первому. Прогон по решению автора через
                # браузер дал 1092x1440 и 1122x1402 при доноре 1080x1350. Тихий
                # канал приводит кадр внутри движка, браузерный был без защиты.
                CX.fit_exact(out_png, slide_size(img), logger.info, mode="contain")
                success_count += 1
                rendered_pngs.append(out_png)

        if engine == "codex" and jobs:
            from concurrent.futures import ThreadPoolExecutor
            logger.info(f"{package_id}: рисую {len(jobs)} слайдов тихим каналом "
                        f"в {min(lanes, len(jobs))} полос(ы)")
            with ThreadPoolExecutor(max_workers=max(1, lanes)) as pool:
                futures = {
                    pool.submit(render_slide_codex, logger, sid, pr, fl, out, cfg): out
                    for sid, pr, fl, out in jobs
                }
                for fut, out in futures.items():
                    try:
                        if fut.result():
                            success_count += 1
                            rendered_pngs.append(out)
                    except CX.CodexQuotaError as e:
                        # Лимит аккаунта. Дальше рисовать нечем: гасим то, что ещё
                        # не стартовало, и запоминаем причину - её напечатает main
                        # ОДИН раз человеческим языком, вместе с датой открытия.
                        if quota_stop is None:
                            quota_stop = e
                            for other in futures:
                                other.cancel()
                    except Exception as e:
                        logger.error(f"{out.name}: неожиданная ошибка тихого канала: {e}")
            rendered_pngs.sort()
    finally:
        # CDP-контекст живой (общий Chrome) — НЕ закрываем, только свои вкладки.
        pass

    logger.info(f"{package_id}: успех {success_count}/{planned}")
    # Провенанс: пометить реально отрисованные GPT-браузером слайды (guard от само-рендера)
    if rendered_pngs:
        try:
            stamp_provenance(
                output_dir,
                cfg["custom_gpt_url"] if engine == "browser" else "codex-cli://imagegen",
                rendered_pngs, logger,
                source=PROVENANCE_SOURCE if engine == "browser" else PROVENANCE_SOURCE_CODEX,
            )
        except Exception as e:
            logger.warning(f"провенанс не записан: {e}")

    # Caption: описание пишет КОПИРАЙТИНГ-ДВИЖОК (SKILL.md шаг 4 - канон
    # _shared/lead-magnet-description-structure.md через post template #9 + humaniser),
    # а НЕ транскрипт донора. Правка по решению автора: раньше сюда падал чужой транскрипт,
    # и доставка пропускала его как готовое описание (гейт ловил только пустой файл) -
    # копирайтинг держался на дисциплине агента, машинной гарантии не было.
    # Транскрипт донора сохраняем рядом как сырьё, описание оставляем пустым:
    # пустое описание рубит гейт доставки и заставляет написать своё.
    tpath = package_dir / "transcript.txt"
    if tpath.exists():
        (output_dir / "donor_transcript.txt").write_text(
            tpath.read_text(errors="ignore").strip())
    (output_dir / "extracted_caption.txt").write_text("")

    # Лимит аккаунта пробрасываем ПОСЛЕ штампа и caption: то, что успело
    # отрисоваться до лимита, остаётся валидным и помеченным.
    if quota_stop is not None:
        raise quota_stop
    return (success_count, planned)


def find_packages(queue_dir: Path, specific_id: str | None = None) -> list[Path]:
    if not queue_dir.exists():
        return []
    if specific_id:
        p = queue_dir / specific_id
        return [p] if p.is_dir() else []
    return sorted([p for p in queue_dir.iterdir() if p.is_dir()])


def main() -> int:
    cfg = load_config()
    logger = setup_logging(cfg["log_file"])

    # Канал рендера. По умолчанию тихий (окон не открывает); старый браузерный
    # оставлен запасным и включается флагом --engine browser.
    argv = [x for x in sys.argv[1:]]
    engine = str(cfg.get("engine", "codex"))
    lanes = int(cfg.get("codex_lanes", 3))
    if "--engine" in argv:
        i = argv.index("--engine")
        engine = argv[i + 1]
        del argv[i:i + 2]
    if "--lanes" in argv:
        i = argv.index("--lanes")
        lanes = int(argv[i + 1])
        del argv[i:i + 2]
    if engine not in ("codex", "browser"):
        logger.error(f"неизвестный канал {engine!r}, допустимы codex и browser")
        return 2
    if engine == "browser" and sync_playwright is None:
        logger.error("браузерный канал просит playwright, а его нет. "
                     "Либо поставь его (setup.sh), либо иди тихим каналом (--engine codex)")
        return 2

    specific_id = argv[0] if argv else None
    # Опциональный 2-й позиционный аргумент — номера слайдов для точечной
    # регенерации, напр. "1,2"
    only_slides = None
    if len(argv) > 1:
        only_slides = {int(x) for x in argv[1].split(",") if x.strip().isdigit()}
    queue_dir = Path(cfg["queue_dir"])
    packages = find_packages(queue_dir, specific_id)

    if not packages:
        logger.info(f"Очередь пуста: {queue_dir}")
        return 0

    logger.info(f"Найдено {len(packages)} пакетов · канал {engine}")

    # Тихому каналу playwright не нужен - не поднимаем его вообще.
    import contextlib
    browser_ctx = sync_playwright() if engine == "browser" else contextlib.nullcontext()
    with browser_ctx as p:
        failed = []      # пакеты, где не вышло НИ ОДНОГО слайда
        partial = []     # пакеты, где вышла только часть - это тоже НЕ успех
        quota = None
        for pkg in packages:
            try:
                rendered, planned = process_package(
                    p, cfg, logger, pkg, only_slides=only_slides,
                    engine=engine, lanes=lanes)
            except CX.CodexQuotaError as e:
                # Внешний блокер: остальные пакеты очереди рисовать нечем,
                # каждый следующий вызов только жжёт время впустую.
                quota = e
                break
            if rendered:
                # при точечной регенерации пакет не архивируем (работа не завершена)
                if not only_slides:
                    archive_root = Path(cfg["archive_dir"]) / time.strftime("%Y-%m-%d")
                    archive_root.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(pkg), str(archive_root / pkg.name))
                if rendered < planned:
                    partial.append(f"{pkg.name} ({rendered}/{planned})")
            else:
                failed.append(pkg.name)
        if quota is not None:
            # Причина печатается ОДИН раз и человеческим языком, вместе с датой,
            # когда лимит откроется. Код 3 = «прогон оборван внешним лимитом».
            logger.error(f"=== ПРОГОН ОБОРВАН: {quota} ===")
            logger.error("Очередь дальше НЕ трогаю: пока лимит закрыт, каждый вызов "
                         "будет пустым. Варианты: дождаться даты выше либо "
                         "--engine browser")
            return 3
        logger.info(f"=== Итог: ошибки {failed}; частично {partial} ===")
        # Код возврата обязан отражать реальность: 0 только когда ВСЕ слайды всех
        # пакетов вышли. Раньше «1 из 8» уезжало наверх как удача, и раннеры
        # (cleanup_render.sh, night_run*.sh, render_gpt10.sh) шли дальше по пустому.
        return 0 if not failed and not partial else 1


if __name__ == "__main__":
    sys.exit(main())
