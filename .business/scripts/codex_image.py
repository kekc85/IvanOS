#!/usr/bin/env python3
"""ТИХИЙ КАНАЛ ГЕНЕРАЦИИ КАРТИНОК - Codex CLI, без единого окна браузера.

Зачем этот файл (правка владельца). До него ВСЕ картинки системы рисовались
через живой Chrome владельца: `seo/images/gpt_render.py` открывал своё окно на
chatgpt.com, `auto-uniqualize/driver.py` водил Playwright по карусельной кастомке.
Оба канала физически занимают экран, буфер обмена и фронтмост-окно - работать за
компьютером во время прогона нельзя, а параллелить нельзя вообще (один браузер = один
межпроцессный лок, очередь). Владелец дословно: «было бы прикольно, чтобы у меня окна
браузера не открывались и не мешали мне, чтобы работало бесшумно».

Канал: `codex exec` (OpenAI Codex CLI) → его системный скилл `imagegen` → встроенный
инструмент `image_gen`. Полностью headless: процесс в фоне, GUI не трогается.
Логин - тот же ChatGPT-аккаунт владельца (`~/.codex/auth.json`), ключ API не нужен.

Замер живого прогона по решению автора (не догадка):
  - фото-обложка 3:2 → ровно 1536x1024, 78 сек, окон Chrome до/после: 0/0
  - слайд карусели image-in→image-out 4:5 → ровно 1024x1280, 108 сек, кириллица
    отрисована без ошибок (заголовок, подпись, 4 тега, авторская плашка)

🔴 ИЗОЛИРОВАННЫЙ ДОМ CODEX (`~/.codex-image`) - не украшение, а несущая деталь.
Первый же живой тест по решению автора показал: обычный `codex exec` из домашней папки
подтягивает `~/.codex/AGENTS.md` (16 КБ навигации IvanOS) и вместо картинки уходит
проводить ОНБОРДИНГ - дословный ответ на промпт про латунный тумблер: «Система готова,
сейчас вместе соберём твой проект. Расскажи коротко, чем ты занимался дольше всего».
Поэтому генерация всегда идёт со своим `CODEX_HOME`, где нет AGENTS.md и нет наших
скиллов, а есть только логин и системный `imagegen`. Дом создаётся сам при первом
вызове, логин переносится копией из `~/.codex` и освежается, когда там он новее.

Параллельность. У этого канала НЕТ общего ресурса (браузера, буфера, ~/Downloads),
поэтому межпроцессный лок не нужен: слайды можно рисовать пачкой одновременно.
Каждый вызов работает в своём временном каталоге и переносит готовый файл к себе.

Использование из питона:

    import sys; sys.path.insert(0, str(Path(".business/scripts").expanduser()))
    from codex_image import render

    render("Photorealistic ... Save to out.png", out_path=Path("cover.png"))
    render(prompt, out_path=Path("slide-01.png"), refs=[Path("donor.jpg")])

Использование из командной строки:

    python3 codex_image.py --prompt "$(cat p.txt)" --out cover.png --size og
    python3 codex_image.py --prompt-file p.txt --out slide.png --ref donor.jpg --size slide
    python3 codex_image.py --selftest        # проверка канала без расхода генерации
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Константы канала ────────────────────────────────────────────────────────────

CODEX_HOME = Path("~/.codex-image").expanduser()
#: Метка последнего пойманного лимита. Живёт файлом, потому что проверить лимит
#: инструмента картинок можно ТОЛЬКО реальной генерацией: текстовый пробник его
#: не видит (у картинок свой пул), и гейт без этой метки врёт «канал готов».
QUOTA_FLAG = CODEX_HOME / "quota-block.json"
SOURCE_CODEX_HOME = Path("~/.codex").expanduser()
CODEX_BIN = "codex"

#: Провенанс - чем помечаются картинки, отрисованные этим каналом.
PROVENANCE_SOURCE = "codex-imagegen-headless"

#: Целевые размеры под наши поверхности (ширина, высота).
SIZES = {
    "og": (1536, 1024),        # обложка статьи / OG-картинка, 3:2
    "square": (1024, 1024),    # квадрат
    "slide": (1024, 1280),     # слайд карусели, 4:5
    "story": (1024, 1536),     # вертикаль 2:3 под сторис
}

DEFAULT_TIMEOUT = 600         # сек на одну генерацию
DEFAULT_ATTEMPTS = 2          # столько раз пробуем, прежде чем признать отказ

#: Модель ставим отдельно от рабочей: генерация картинки не требует xhigh-размышления.
CONFIG_TOML = 'model = "gpt-5.6-terra"\nproject_doc_max_bytes = 0\n\n[projects."/"]\ntrust_level = "trusted"\n'

#: Маркеры отказа модели рисовать - чтобы не отдавать наверх пустоту молча.
REFUSAL_MARKERS = (
    "can't create", "cannot create", "can't generate", "cannot generate",
    "unable to generate", "not able to generate", "i'm sorry", "не могу",
    "policy", "content policy",
)

#: Маркеры ВНЕШНЕГО лимита аккаунта. Это не брак промпта и не отказ модели, поэтому
#: повторять попытки бессмысленно - только жжём время. Урок по решению автора: канал упёрся
#: в лимит и дважды соврал наверх «картинка не появилась на диске», хотя в ответе
#: дословно стояло «You've hit your usage limit ... try again at Sep 2nd». Причину
#: обязаны называть человеческим языком и с датой, когда лимит откроется.
QUOTA_MARKERS = (
    "usage limit", "you've hit your usage limit", "rate limit",
    "quota", "too many requests", "upgrade to plus",
)


class CodexImageError(RuntimeError):
    """Канал не отдал картинку - с человеческой причиной внутри."""


class CodexQuotaError(CodexImageError):
    """Выжжен лимит аккаунта. Ловится отдельно, чтобы вызывающий мог уйти
    на запасной канал или честно сказать владельцу, когда лимит откроется."""


# ── Дом codex: создать, освежить логин ──────────────────────────────────────────

def ensure_home(logger=None) -> Path:
    """Готовит изолированный CODEX_HOME и держит в нём свежий логин.

    Возвращает путь дома. Идемпотентно: вызывать можно перед каждой генерацией.
    """
    CODEX_HOME.mkdir(parents=True, exist_ok=True)

    cfg = CODEX_HOME / "config.toml"
    if not cfg.exists() or cfg.read_text() != CONFIG_TOML:
        cfg.write_text(CONFIG_TOML)

    src_auth = SOURCE_CODEX_HOME / "auth.json"
    dst_auth = CODEX_HOME / "auth.json"
    if not src_auth.exists():
        if not dst_auth.exists():
            raise CodexImageError(
                f"нет логина codex ни в {src_auth}, ни в {dst_auth}. "
                "Почини одной командой: codex login"
            )
    else:
        # Токен в рабочем доме обновляется при рефреше - подтягиваем, когда он новее.
        if (not dst_auth.exists()
                or src_auth.stat().st_mtime > dst_auth.stat().st_mtime + 1):
            shutil.copy2(src_auth, dst_auth)
            if logger:
                logger.info(f"логин codex обновлён из {src_auth}")
    return CODEX_HOME


def _env() -> dict:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(CODEX_HOME)
    return env


# ── Сборка инструкции ───────────────────────────────────────────────────────────

_SAVE_CONTRACT = """
Use your built-in image generation tool (the `imagegen` skill) to produce the image.
Save the final image to the file named `{name}` in the current working directory.
Do not ask any clarifying question, do not propose alternatives, do not write code to
draw the picture yourself - generate it with the image tool.
When the file is on disk, print exactly one final line and nothing else:
SAVED: <absolute path>
"""

_REF_CONTRACT = """
Reference images attached to this turn (absolute paths):
{lines}

These are generation references, not files to modify. If your image tool accepts local
image paths (referenced_image_paths), pass the absolute paths above so the reference
pixels condition the output directly. Never overwrite the referenced files.
"""


def build_instruction(prompt: str, out_name: str, refs: list[Path]) -> str:
    parts = [prompt.strip()]
    if refs:
        parts.append(_REF_CONTRACT.format(
            lines="\n".join(f"- {p}" for p in refs)))
    parts.append(_SAVE_CONTRACT.format(name=out_name))
    return "\n\n".join(parts)


# ── Основная функция ────────────────────────────────────────────────────────────

def fit_exact(png: Path, want: tuple[int, int] | None, say=None,
              mode: str = "cover") -> None:
    """Приводит готовую картинку РОВНО к заказанному размеру.

    Зачем. Размер мы у инструмента только ПРОСИМ словами в промпте, гарантии нет:
    приёмка по решению автора поймала выдачи 1122x1402 и 1731x909 там, где заказывали
    донорские 1080x1350. Для ленты карусели это провал - Instagram режет всю ленту
    по первому слайду, разноформатные слайды поедут.

    Два режима, и разница между ними стоила испорченного слайда по решению автора:
      cover   - масштаб + центр-кроп. Для ФОТО: обрезка краёв незаметна.
      contain - вписать целиком и добить полями цвета фона. Для СЛАЙДОВ с вёрсткой:
                у них по краям живут номер страницы, «листай», плашка автора, и
                центр-кроп их срезает. Живой прогон: у слайда 04 кроп 1092x1440 →
                1080x1350 отъел нижнюю строку «04 / 06 · ЛИСТАЙ».
    """
    if not want:
        return
    try:
        from PIL import Image
    except Exception:
        return
    tw, th = want
    try:
        with Image.open(png) as im:
            if im.size == (tw, th):
                return
            sw, sh = im.size
            src = im.convert("RGB")
            if mode == "contain":
                k = min(tw / sw, th / sh)
                nw, nh = max(1, int(sw * k)), max(1, int(sh * k))
                small = src.resize((nw, nh), Image.LANCZOS)
                # Фон полей берём с угла картинки - у наших слайдов он и есть
                # фон макета, поля становятся невидимыми.
                canvas = Image.new("RGB", (tw, th), small.getpixel((1, 1)))
                canvas.paste(small, ((tw - nw) // 2, (th - nh) // 2))
                canvas.save(png)
            else:
                k = max(tw / sw, th / sh)
                big = src.resize((max(tw, int(sw * k)), max(th, int(sh * k))),
                                 Image.LANCZOS)
                left, top = (big.width - tw) // 2, (big.height - th) // 2
                big.crop((left, top, left + tw, top + th)).save(png)
        if say:
            how = "вписан с полями" if mode == "contain" else "центр-кроп"
            say(f"codex-image: кадр приведён {sw}x{sh} → {tw}x{th} ({how})")
    except Exception as e:
        if say:
            say(f"codex-image: точный кадр не применён ({e}), оставляю как есть")


def render(
    prompt: str,
    out_path: Path,
    refs: list[Path] | None = None,
    size: str | tuple[int, int] | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
    timeout: int = DEFAULT_TIMEOUT,
    logger=None,
) -> Path:
    """Рисует картинку headless-каналом и кладёт её в out_path.

    prompt  - текст задания художнику (наш обычный промпт, как для chatgpt).
    refs    - до 5 картинок-референсов (для каруселей это донорский слайд).
    size    - ключ из SIZES либо (w, h); дописывает к промпту явные пиксели.
    Возвращает out_path. Кидает CodexImageError, если картинки нет.
    """
    refs = [Path(r).expanduser().resolve() for r in (refs or [])]
    for r in refs:
        if not r.exists():
            raise CodexImageError(f"референс не найден: {r}")
    if len(refs) > 5:
        raise CodexImageError(f"референсов {len(refs)}, встроенный лимит инструмента - 5")

    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    want = None
    if size:
        want = SIZES[size] if isinstance(size, str) else tuple(size)
        prompt = (f"{prompt.strip()}\n\nOutput image size: "
                  f"exactly {want[0]}x{want[1]} pixels.")

    ensure_home(logger)

    def say(msg: str) -> None:
        if logger:
            logger.info(msg)

    last_err = ""
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory(prefix="codex-image-") as tmp:
            work = Path(tmp)
            name = "output.png"
            args = [
                CODEX_BIN, "exec",
                "--sandbox", "workspace-write",
                "--skip-git-repo-check",
                "--ephemeral",
                "-C", str(work),
            ]
            for r in refs:
                args += ["--image", str(r)]
            args += ["--", build_instruction(prompt, name, refs)]

            t0 = time.time()
            say(f"codex-image: генерация {out_path.name} (попытка {attempt}/{attempts})")
            try:
                proc = subprocess.run(
                    args, env=_env(), cwd=str(work), stdin=subprocess.DEVNULL,
                    capture_output=True, text=True, timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                last_err = f"канал не ответил за {timeout} сек"
                say(f"codex-image: таймаут, {last_err}")
                continue

            tail = (proc.stdout or "")[-4000:] + (proc.stderr or "")[-2000:]

            # 1) явный контракт SAVED:
            found = None
            for m in re.finditer(r"^SAVED:\s*(.+)$", proc.stdout or "", re.M):
                cand = Path(m.group(1).strip())
                if cand.exists():
                    found = cand
            # 2) страховка: файл на месте, но строку модель не напечатала
            if found is None:
                for cand in sorted(work.glob("*.png")) + sorted(work.glob("*.jpg")):
                    found = cand
            if found and found.exists() and found.stat().st_size > 10_000:
                shutil.move(str(found), str(out_path))
                # Картинка вышла - значит лимит открылся, метку снимаем сами,
                # чтобы гейт не пугал устаревшим блоком.
                QUOTA_FLAG.unlink(missing_ok=True)
                fit_exact(out_path, want, say)
                say(f"codex-image: готово за {time.time() - t0:.0f} сек → {out_path}")
                return out_path

            low = tail.lower()

            # Лимит аккаунта - внешний блокер. Повторять нечего, выходим сразу
            # и отдаём наверх дату, когда лимит откроется (она есть в ответе).
            if any(m in low for m in QUOTA_MARKERS):
                when = re.search(r"try again at ([^\n\.]+)", tail)
                quota_line = re.search(r"[^\n]*usage limit[^\n]*", tail, re.I)
                msg = ("ЛИМИТ АККАУНТА CODEX выжжен, это не брак промпта. "
                       + (f"Откроется: {when.group(1).strip()}. " if when else "")
                       + "Пока лимит закрыт - рисуем запасным каналом "
                       "(--engine browser) либо ждём окна лимита. "
                       + (f"Дословно: {quota_line.group(0).strip()}" if quota_line else ""))
                say(f"codex-image: {msg}")
                # Запоминаем блок на диск: только так --selftest сможет сказать
                # правду. Текстовый пробник лимит НЕ ловит - у инструмента
                # картинок свой пул (по решению автора гейт на этом соврал «канал готов»).
                try:
                    QUOTA_FLAG.write_text(json.dumps({
                        "blocked_until": when.group(1).strip() if when else "",
                        "seen_at": time.strftime("%Y-%m-%d %H:%M"),
                        "raw": quota_line.group(0).strip() if quota_line else "",
                    }, ensure_ascii=False))
                except Exception:
                    pass
                raise CodexQuotaError(f"{out_path.name}: {msg}")

            refusal = next((m for m in REFUSAL_MARKERS if m in low), None)
            last_err = (f"модель отказалась рисовать (маркер {refusal!r})" if refusal
                        else "картинка не появилась на диске")
            say(f"codex-image: {last_err}")

    raise CodexImageError(
        f"{out_path.name}: картинку получить не удалось за {attempts} попыт(ки). "
        f"Последняя причина - {last_err}"
    )


# ── Самопроверка канала ─────────────────────────────────────────────────────────

def selftest() -> int:
    """Проверяет всё, кроме самой генерации: бинарь, версия, логин, дом, imagegen."""
    ok = True

    def line(good: bool, text: str) -> None:
        nonlocal ok
        ok = ok and good
        print(("OK   " if good else "СБОЙ ") + text)

    exe = shutil.which(CODEX_BIN)
    line(bool(exe), f"бинарь codex: {exe or 'не найден в PATH'}")
    if exe:
        ver = subprocess.run([CODEX_BIN, "--version"], capture_output=True, text=True)
        line(ver.returncode == 0, f"версия: {ver.stdout.strip() or ver.stderr.strip()}")
    try:
        home = ensure_home()
        line(True, f"изолированный дом: {home}")
        line((home / "auth.json").exists(), "логин ChatGPT на месте (auth.json)")
        line(not (home / "AGENTS.md").exists(),
             "AGENTS.md в доме отсутствует (иначе канал уйдёт в онбординг)")
        ig = home / "skills" / ".system" / "imagegen"
        line(ig.exists() or True, f"системный скилл imagegen: "
             f"{'на месте' if ig.exists() else 'появится при первом вызове'}")
    except CodexImageError as e:
        line(False, str(e))

    # 🔴 Лимит инструмента картинок текстовым пробником НЕ проверяется: у картинок
    # свой пул. по решению автора гейт на этом соврал - сказал «канал готов», а прогон
    # карусели тут же встал на лимите. Поэтому источник правды - метка от реальной
    # генерации, а текстовый ход остался проверкой «жив ли вообще вход».
    if QUOTA_FLAG.exists():
        try:
            q = json.loads(QUOTA_FLAG.read_text())
        except Exception:
            q = {}
        line(False, "лимит инструмента картинок: ВЫЖЖЕН"
             + (f", откроется {q.get('blocked_until')}" if q.get("blocked_until") else "")
             + f" (поймано {q.get('seen_at', '?')}). Пока лимит закрыт - только "
               "--engine browser. Метка снимется сама при первой удачной картинке")
    else:
        print("     лимит инструмента картинок: метки блока нет. Честная граница: "
              "лимит картинок виден ТОЛЬКО по реальной генерации, текстовый пробник "
              "его не ловит")

    probe = subprocess.run(
        [CODEX_BIN, "exec", "--sandbox", "read-only", "--skip-git-repo-check",
         "--ephemeral", "--", "Reply with exactly one word: PONG"],
        env=_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180)
    blob = (probe.stdout or "") + (probe.stderr or "")
    hit = any(m in blob.lower() for m in QUOTA_MARKERS)
    line(not hit, "текстовый вход в codex: " + ("отвечает" if not hit else "тоже под лимитом"))

    windows = subprocess.run(
        ["osascript", "-e", 'tell application "Google Chrome" to get (count of windows)'],
        capture_output=True, text=True).stdout.strip()
    print(f"     окон Chrome сейчас: {windows or 'n/a'} (канал их не открывает)")
    print("\nИтог: " + ("канал готов" if ok else "канал НЕ готов, см. строки СБОЙ"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Тихая генерация картинок через Codex CLI")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--out")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--size", default=None, choices=list(SIZES))
    ap.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    if not prompt or not a.out:
        ap.error("нужны --prompt/--prompt-file и --out (или --selftest)")

    class _L:
        def info(self, m): print(m, flush=True)

    try:
        p = render(prompt, Path(a.out), refs=[Path(r) for r in a.ref],
                   size=a.size, attempts=a.attempts, timeout=a.timeout, logger=_L())
    except CodexImageError as e:
        print(f"ОШИБКА: {e}", file=sys.stderr)
        return 1
    print(f"SAVED: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
