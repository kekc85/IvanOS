#!/usr/bin/env python3
"""
Telegram delivery — Layer 3 of auto-uniqualize pipeline.

Читает auto-output dir, отправляет каждый пакет альбомом в Telegram
с inline buttons «Опубликовать в IG / Доработать / Удалить».

Usage:
    python3 telegram-deliver.py                  # все из output_dir
    python3 telegram-deliver.py <package-id>     # один пакет
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write("ERROR: requests not installed. Run setup.sh first.\n")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    sys.stderr.write("ERROR: python-dotenv not installed. Run setup.sh first.\n")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).parent.resolve()


def load_config() -> dict:
    cfg_path = SCRIPT_DIR / "config.json"
    if not cfg_path.exists():
        sys.stderr.write(f"ERROR: {cfg_path} не найден.\n")
        sys.exit(1)
    with open(cfg_path) as f:
        cfg = json.load(f)
    for k in ("output_dir", "log_file"):
        cfg[k] = str(Path(cfg[k]).expanduser().resolve())
    return cfg


def setup_logging(log_file: str) -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("telegram-deliver")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh)
    return logger


def find_output_packages(output_dir: Path, specific_id: str | None = None) -> list[Path]:
    if not output_dir.exists():
        return []
    if specific_id:
        p = output_dir / specific_id
        return [p] if p.is_dir() else []
    return sorted([p for p in output_dir.iterdir() if p.is_dir()])


def chunk_pngs(pngs: list[Path], max_per_album: int = 10) -> list[list[Path]]:
    """Telegram media group лимит = 10 файлов."""
    return [pngs[i : i + max_per_album] for i in range(0, len(pngs), max_per_album)]


def send_media_group(bot_token: str, chat_id: str, pngs: list[Path], caption: str) -> bool:
    """Отправляет до 10 PNG как альбом."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
    media = []
    files = {}
    for idx, png in enumerate(pngs):
        file_key = f"photo_{idx}"
        files[file_key] = open(png, "rb")
        item = {"type": "photo", "media": f"attach://{file_key}"}
        if idx == 0:
            item["caption"] = caption[:1024]  # Telegram caption limit
            item["parse_mode"] = "Markdown"
        media.append(item)

    try:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "media": json.dumps(media)},
            files=files,
            timeout=120,
        )
        return resp.status_code == 200
    finally:
        for f in files.values():
            f.close()


def send_original_button(bot_token: str, chat_id: str, package_dir: Path) -> None:
    """Отправляет inline-кнопку со ссылкой на оригинал карусели.
    Кнопка (а не текст) — чтобы ссылка не копировалась вместе с описанием."""
    src_path = package_dir / "_source_url.txt"
    if not src_path.exists():
        return
    url = src_path.read_text(encoding="utf-8").strip()
    if not url:
        return
    keyboard = {"inline_keyboard": [[{"text": "🔗 Оригинал карусели", "url": url}]]}
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "Оригинал, с которого сделано:",
            "reply_markup": keyboard,
        },
        timeout=30,
    )


def caption_is_donor_text(package_dir: Path) -> bool:
    """GUARD (по решению автора): описание совпало с сырьём донора - копирайтинг-движок не отработал.

    Зеркало verify_render_provenance: там слайды обязаны нести штамп законного рендера,
    здесь описание обязано отличаться от транскрипта донора. Канон описания -
    ~/.claude/skills/_shared/lead-magnet-description-structure.md через post #9 + humaniser
    (SKILL.md carousel-uniqualizer шаг 4). Сравнение по нормализованному тексту, чтобы
    правка пробелов не считалась переписыванием."""
    cap = package_dir / "extracted_caption.txt"
    for donor_name in ("donor_transcript.txt", "transcript.txt"):
        donor = package_dir / donor_name
        if not (cap.exists() and donor.exists()):
            continue
        norm = lambda p: " ".join(p.read_text(encoding="utf-8", errors="ignore").split())
        if norm(cap) and norm(cap) == norm(donor):
            return True
    return False


def build_caption(package_dir: Path) -> str:
    """ЧИСТЫЙ caption — только текст описания поста, без тех-префиксов.
    автор копирует его как есть в IG, поэтому ничего лишнего (имя пакета,
    ссылка) в текст не добавляем. Ссылка на оригинал идёт отдельной кнопкой."""
    caption_path = package_dir / "extracted_caption.txt"
    if caption_path.exists():
        text = caption_path.read_text(encoding="utf-8").strip()
        if len(text) > 1000:  # Telegram caption limit 1024
            text = text[:1000] + "..."
        return text
    return "Готово, посмотри слайды."


PROVENANCE_FILE = "_render_provenance.json"
PROVENANCE_SOURCE = "chatgpt-custom-gpt-browser"
#: Тихий канал (codex exec → imagegen, без окон) - второй законный источник рендера,
#: врезан по решению автора. Гейт по-прежнему режет ВСЁ остальное: Higgsfield, рисование
#: кодом, HTML→PNG, руками. Меняется только список разрешённых штампов, не строгость.
PROVENANCE_SOURCE_CODEX = "codex-imagegen-headless"
PROVENANCE_SOURCES = (PROVENANCE_SOURCE, PROVENANCE_SOURCE_CODEX)


def verify_render_provenance(package_dir: Path, pngs: list, logger: logging.Logger) -> bool:
    """GUARD: слайды ОБЯЗАНЫ быть отрисованы законным каналом рендера - Custom GPT в
    браузере ЛИБО тихим codex-imagegen (driver штампует провенанс).
    Само-нарисованные слайды (Higgsfield/gpt_image/код/HTML→PNG/руками) штампа не имеют → блок.
    Проверяемо: каждый отправляемый PNG есть в _render_provenance.json с совпадающим md5."""
    import hashlib
    prov_path = package_dir / PROVENANCE_FILE
    if not prov_path.exists():
        logger.error(f"BLOCKED: нет {PROVENANCE_FILE} — слайды НЕ отрисованы GPT-браузером "
                     f"(само-рендер запрещён). Прогони driver_parallel.py/driver.py. Доставка отменена.")
        return False
    try:
        data = json.loads(prov_path.read_text())
    except Exception as e:
        logger.error(f"BLOCKED: провенанс нечитаем ({e}). Доставка отменена.")
        return False
    if data.get("generated_by") not in PROVENANCE_SOURCES:
        logger.error(f"BLOCKED: провенанс не от законного канала рендера "
                     f"(generated_by={data.get('generated_by')!r}, допустимы {PROVENANCE_SOURCES}). "
                     "Доставка отменена.")
        return False
    slides = data.get("slides", {})
    for png in pngs:
        rec = slides.get(png.name)
        if not rec:
            logger.error(f"BLOCKED: {png.name} НЕТ в провенансе GPT-рендера (само-нарисованный?). Доставка отменена.")
            return False
        actual = hashlib.md5(png.read_bytes()).hexdigest()
        if actual != rec:
            logger.error(f"BLOCKED: {png.name} md5 не совпал с провенансом (подменён после рендера?). Доставка отменена.")
            return False
    logger.info(f"провенанс OK: все {len(pngs)} слайдов отрисованы каналом "
                f"{data.get('generated_by')}")
    return True


def deliver_package(bot_token: str, chat_id: str, logger: logging.Logger, package_dir: Path) -> bool:
    package_id = package_dir.name
    pngs = sorted(package_dir.glob("*.png"))
    if not pngs:
        logger.warning(f"{package_id}: нет PNG, пропуск")
        return False

    # GUARD от само-рендера: ничего не уходит автору без провенанса GPT-браузера
    if not verify_render_provenance(package_dir, pngs, logger):
        return False

    # GUARD описания (правило по решению автора): слайды НИКОГДА не уходят без готового описания,
    # которое автор вставит. Нет реального extracted_caption.txt → блок доставки.
    cap_path = package_dir / "extracted_caption.txt"
    cap_text = cap_path.read_text(encoding="utf-8").strip() if cap_path.exists() else ""
    if len(cap_text) < 120 or "посмотри слайды" in cap_text:
        logger.error("BLOCKED: нет готового описания (extracted_caption.txt пуст/заглушка). "
                     "Слайды не отправляю без описания, которое автор вставит. Сначала напиши описание.")
        return False

    # GUARD копирайтинг-движка (по решению автора): описание, равное сырью донора, = движок не отработал.
    # Канон описания - _shared/lead-magnet-description-structure.md через post #9 + humaniser
    # (carousel-uniqualizer SKILL.md шаг 4). До этой правки чужой транскрипт проходил гейт выше,
    # потому что он длиннее 120 знаков и не содержит слов заглушки.
    if caption_is_donor_text(package_dir):
        logger.error("BLOCKED: описание совпадает с транскриптом донора - копирайтинг-движок "
                     "не отработал. Напиши своё описание по канону "
                     "_shared/lead-magnet-description-structure.md (post template #9 + humaniser), "
                     "донорское сырьё лежит рядом в donor_transcript.txt.")
        return False

    logger.info(f"{package_id}: отправляю {len(pngs)} PNG в Telegram chat {chat_id}")

    # 1) Альбом слайдов БЕЗ подписи (полное описание идёт отдельным чистым сообщением ниже,
    #    т.к. album-caption режется на 1024 и его неудобно копировать).
    chunks = chunk_pngs(pngs, max_per_album=10)
    for idx, chunk in enumerate(chunks):
        if not send_media_group(bot_token, chat_id, chunk, ""):
            logger.error(f"{package_id}: не удалось отправить chunk {idx+1}")
            return False
        time.sleep(2)  # rate limit safety

    # 2) ОПИСАНИЕ — ЧИСТЫМ отдельным сообщением, БЕЗ приписок/лейблов/эмодзи-заголовков
    # (автор копирует дословно; любая приписка попадёт в публикацию — правило по решению автора).
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": cap_text, "disable_web_page_preview": "true"},
        timeout=30,
    )
    time.sleep(1)

    # 3) Ссылка на оригинал — кнопкой (минимальный текст).
    send_original_button(bot_token, chat_id, package_dir)
    logger.info(f"{package_id}: доставлено ✓ (альбом + чистое описание + ссылка)")
    return True


def main() -> int:
    load_dotenv(SCRIPT_DIR / ".env")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_USER_ID") or os.getenv("TELEGRAM_CHANNEL_ID")
    if not bot_token or not chat_id:
        sys.stderr.write("ERROR: TELEGRAM_BOT_TOKEN и TELEGRAM_USER_ID должны быть в .env\n")
        return 1

    cfg = load_config()
    logger = setup_logging(cfg["log_file"])

    specific_id = sys.argv[1] if len(sys.argv) > 1 else None
    output_dir = Path(cfg["output_dir"])
    packages = find_output_packages(output_dir, specific_id)

    if not packages:
        logger.info(f"Output пуст: {output_dir}")
        return 0

    delivered = 0
    for pkg in packages:
        if deliver_package(bot_token, chat_id, logger, pkg):
            delivered += 1
            # Помечаем как доставленный
            (pkg / ".delivered").touch()
        time.sleep(3)

    logger.info(f"Доставлено {delivered}/{len(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
