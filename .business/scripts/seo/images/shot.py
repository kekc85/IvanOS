#!/usr/bin/env python3
"""Скриншот веб-UI с аннотациями + мокап терминала с РЕАЛЬНЫМ выводом команд.

Режим URL (Playwright, свой чистый headless-профиль, viewport 1440x900, retina 2x):
  python3 shot.py --url https://claude.ai --out shot.png \\
      --annotate '[{"type":"box","x":100,"y":200,"w":300,"h":60},
                   {"type":"arrow","from":[500,400],"to":[420,240]},
                   {"type":"num","x":120,"y":180,"n":1},
                   {"type":"label","x":520,"y":410,"text":"Жми сюда"},
                   {"type":"box","selector":"#login","n":2}]'
  Координаты - CSS-пиксели (как в DevTools). selector вместо x/y - рамка/номер
  по живому элементу. --selector CSS - скриншот только элемента. --fullpage - вся страница.

Режим СЦЕНАРИЯ (кейс-превью: вход -> интерфейс -> готовый выход, кадр после реальных
действий, а не «скрин главной»):
  python3 shot.py --scenario steps.json --out <каталог кадров> \\
      --class result --manifest $WORK/<slug>/shots-manifest.json
  steps.json - список шагов (или {"steps": [...], "viewport": {...}, "state": "..."}):
    {"do":"goto","url":"https://сервис","wait_for":"main"}
    {"do":"wait_for","selector":".result"}
    {"do":"click","selector":"button.run"}
    {"do":"fill","selector":"#prompt","value":"текст"}
    {"do":"shot","name":"slug-result-1","class":"result","note":"выход функции",
     "annotate":[...],"selector":"...","fullpage":false,"mobile_crop":[x,y,w,h]}
  Короткая форма шага строкой тоже понимается: "goto <url>", "wait_for <селектор>",
  "click <селектор>", "fill <селектор> <значение>", "shot <имя>".
  Вместо networkidle - ожидание по селектору: на живых SPA networkidle не наступает.
  Cookie/consent-баннеры закрываются best-effort по списку типовых селекторов.
  🔴 Значения fill в манифест и в лог не попадают НИКОГДА: только селектор поля и
  метка «заполнено».

Залогиненная сессия: --state storage_state.json (playwright storage state). Профиль
владельца не трогаем - браузер всегда поднимается своим чистым профилем.

Манифест происхождения кадра (--manifest, по контракту лежит РЯДОМ со страницей,
$WORK/<slug>/shots-manifest.json, НЕ в assets/): дописывается автоматически, дубль по
ключу file перезаписывается. Кадр, снятый вне shot.py (живой Chrome), регистрируется
отдельно:
  python3 shot.py --register-external assets/имя.webp --class step \\
      --manifest $WORK/<slug>/shots-manifest.json --url https://сервис --note "..."
  Это СЛАБЫЙ класс происхождения: подтверждения съёмки у скрипта нет, hero сам по себе
  такой записью не закрывается.
  Кадр снят раньше (inherited - готовый файл со старой страницы при её ревизии, кадр из
  живого Chrome, кроп со старого hero) - добавить --shot-at YYYY-MM-DD: без флага в
  манифест уйдёт сегодняшняя дата, а её читают как дату съёмки.

Мобильная версия кадра: --mobile-crop X,Y,W,H (CSS-пиксели, плотная зона того же
кейс-превью) + --mobile-width (итоговая ширина, по умолчанию 720). Файл кладётся рядом
с основным, суффикс -mobile.

Режим терминала (ось 9 плана: вывод ТОЛЬКО из файла с реально прогнанными командами,
скрипт ничего не выдумывает) - легаси, поведение не менялось:
  python3 shot.py --terminal output.txt --title "~/my-app" --out term.png
  Строки, начинающиеся с "$ ", подсвечиваются как команды.
"""
import argparse
import json
import os
import time
from datetime import date
from pathlib import Path
import _brand as B

VIEWPORT = {"width": 1440, "height": 900}
SCALE = 2
MOBILE_WIDTH = 720          # итоговая ширина мобильного кроп-кадра (360 CSS x2)
FRAME_CLASSES = ("result", "step", "own-run", "inherited")

# Типовые кнопки согласия: баннер лезет поверх кадра и портит кейс-превью.
# Список best-effort: селектора нет или клик не прошёл - молча идём дальше.
CONSENT_SELECTORS = (
    "#onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    "#accept-cookies",
    ".fc-cta-consent",
    "[data-testid='cookie-policy-manage-dialog-accept-button']",
    "button[aria-label*='Accept']",
    "button[aria-label*='Принять']",
    "button:has-text('Accept all')",
    "button:has-text('Accept All Cookies')",
    "button:has-text('Allow all')",
    "button:has-text('I agree')",
    "button:has-text('Got it')",
    "button:has-text('Принять все')",
    "button:has-text('Принять')",
    "button:has-text('Согласен')",
    "button:has-text('Хорошо')",
    # 🔴 НЕ ТОЛЬКО <button> (класс-фикс по решению автора, дефект T3 круга 2 конвейера).
    # Прежний список искал согласие исключительно тегом button, и на живом
    # прогоне ЮKassa плашка «Мы сохраняем «куки» ... Ясно» осталась В КАДРЕ
    # ХИРО: её кнопка свёрстана не тегом button. То же у ряда SPA, где согласие
    # рисуется через <a>, <div role="button"> и <span>. Роль и тег перебираются
    # отдельными строками, потому что `:has-text` по произвольному узлу цепляет
    # весь контейнер и клик уходит мимо
    "[role='button']:has-text('Ясно')",
    "[role='button']:has-text('Принять')",
    "[role='button']:has-text('Accept')",
    "a:has-text('Ясно')",
    "a:has-text('Принять все')",
    "a:has-text('Accept all')",
    "div[class*='cookie'] button",
    "div[class*='consent'] button",
    "div[class*='cookie'] [role='button']",
    "*:text-is('Ясно')",
    "*:text-is('Понятно')",
    "*:text-is('Хорошо, спасибо')",
)


# ---------------------------------------------------------------- аннотации (Pillow)

def _rgba(hexcol, alpha):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def _overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _busyness(img, rect):
    """Насколько «занята» зона кадра: stddev яркости. Пустой фон ~0, текст/UI высоко."""
    from PIL import ImageStat
    x0, y0, x1, y1 = (int(v) for v in rect)
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, img.width), min(y1, img.height)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return float("inf")
    return ImageStat.Stat(img.crop((x0, y0, x1, y1)).convert("L")).stddev[0]


def _place_label(img, anchor, lw, lh, obstacles, gap):
    """Умное позиционирование подписи: кандидаты вокруг аннотируемого элемента
    (под/над со скольжением по горизонтали вплоть до краёв кадра, справа/слева
    со скольжением по вертикали), всё в кадре; отбрасываем перекрытия с
    элементами, из остальных берём самую СВОБОДНУЮ зону (минимальный stddev
    пикселей = пустой фон), при равной свободе - ближайшую к элементу."""
    bx0, by0, bx1, by1 = anchor
    W, H = img.width, img.height
    xs = {bx0, (bx0 + bx1 - lw) // 2, bx1 - lw, gap, W - lw - gap}
    ys = {by0, (by0 + by1 - lh) // 2, by1 - lh}
    cands = [(x, by1 + gap) for x in xs]          # под элементом
    cands += [(x, by0 - lh - gap) for x in xs]    # над элементом
    cands += [(bx1 + gap, y) for y in ys]         # справа
    cands += [(bx0 - lw - gap, y) for y in ys]    # слева
    diag = (W ** 2 + H ** 2) ** 0.5
    ax, ay = (bx0 + bx1) / 2, (by0 + by1) / 2
    scored = []
    for cx, cy in cands:
        cx = min(max(cx, gap), W - lw - gap)
        cy = min(max(cy, gap), H - lh - gap)
        rect = (cx, cy, cx + lw, cy + lh)
        clash = any(_overlap(rect, o) for o in obstacles)
        dist = (((cx + lw / 2 - ax) ** 2 + (cy + lh / 2 - ay) ** 2) ** 0.5) / diag
        scored.append((clash, _busyness(img, rect) + dist * 3, rect))
    scored.sort(key=lambda s: (s[0], s[1]))
    return scored[0][2]


def annotate(png_path, notes, scale=SCALE):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(png_path).convert("RGB")
    d = ImageDraw.Draw(img)
    acc = B.ACCENT
    lw = 3 * scale

    def font(sz):
        # Кроссплатформенно: жирный системный шрифт Mac / Windows / Linux, иначе дефолт PIL.
        for _f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                   "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
            try:
                return ImageFont.truetype(_f, sz * scale)
            except OSError:
                continue
        return ImageFont.load_default()

    # проход 1: рамки/стрелки/номера + сбор препятствий для подписей
    obstacles = []
    for n in notes:
        t = n["type"]
        if t == "box":
            x, y, w, h = (n[k] * scale for k in ("x", "y", "w", "h"))
            d.rounded_rectangle([x, y, x + w, y + h], radius=6 * scale,
                                outline=acc, width=lw)
            obstacles.append((x, y, x + w, y + h))
        elif t == "arrow":
            (x1, y1), (x2, y2) = n["from"], n["to"]
            x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
            d.line([x1, y1, x2, y2], fill=acc, width=lw)
            import math
            ang = math.atan2(y2 - y1, x2 - x1)
            L = 14 * scale
            for da in (math.radians(153), math.radians(-153)):
                d.line([x2, y2, x2 + L * math.cos(ang + da),
                        y2 + L * math.sin(ang + da)], fill=acc, width=lw)
        elif t == "num":
            x, y, r = n["x"] * scale, n["y"] * scale, 16 * scale
            d.ellipse([x - r, y - r, x + r, y + r], fill=acc)
            f = font(18)
            s = str(n.get("n", "?"))
            bb = d.textbbox((0, 0), s, font=f)
            d.text((x - (bb[2] - bb[0]) / 2, y - (bb[3] - bb[1]) / 2 - bb[1]),
                   s, font=f, fill="white")
            obstacles.append((x - r, y - r, x + r, y + r))

    # проход 2: подписи - полупрозрачная подложка, не поверх аннотируемого
    labels = [n for n in notes if n["type"] == "label"]
    if labels:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        f = font(16)
        pad, gap = 10 * scale, 12 * scale
        placed = []
        for n in labels:
            s = n["text"]
            bb = d.textbbox((0, 0), s, font=f)
            box_w = bb[2] - bb[0] + 2 * pad
            box_h = bb[3] - bb[1] + 2 * pad
            if "anchor" in n:  # подпись элемента: ищем свободную зону рядом
                ax, ay, aw, ah = (v * scale for v in n["anchor"])
                rect = _place_label(img, (ax, ay, ax + aw, ay + ah),
                                    box_w, box_h, obstacles + placed, gap)
            else:              # явные координаты автора: только подложка + кадр
                x = min(max(n["x"] * scale, 0), img.width - box_w)
                y = min(max(n["y"] * scale, 0), img.height - box_h)
                rect = (x, y, x + box_w, y + box_h)
            od.rounded_rectangle(rect, radius=8 * scale,
                                 fill=_rgba(B.PAPER, 216), outline=acc,
                                 width=2 * scale)
            placed.append(rect)
            n["_rect"] = rect
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        d = ImageDraw.Draw(img)
        for n in labels:
            bb = d.textbbox((0, 0), n["text"], font=f)
            x0, y0 = n["_rect"][0], n["_rect"][1]
            d.text((x0 + pad, y0 + pad - bb[1]), n["text"], font=f, fill=B.INK)
    img.save(png_path)


# ---------------------------------------------------------------- общий слой съёмки

def derive_notes(page, notes, fullpage):
    """selector-аннотации -> координаты живых элементов (общее для --url и сценария)."""
    vh = (page.viewport_size or VIEWPORT)["height"]
    derived = []
    for n in notes:
        if "selector" in n:
            loc = page.locator(n["selector"]).first
            bb = loc.bounding_box()
            if not bb:
                raise SystemExit(f"selector не найден: {n['selector']}")
            if bb["y"] + bb["height"] > vh and not fullpage:
                print(f"WARN: {n['selector']} ниже первого экрана - "
                      f"добавь --fullpage или элемент не попадёт в кадр")
            if n["type"] == "box":
                n.update(x=bb["x"] - 6, y=bb["y"] - 6,
                         w=bb["width"] + 12, h=bb["height"] + 12)
                # бонус-опции: номер в углу рамки и плашка под ней
                if "n" in n:
                    derived.append({"type": "num", "x": n["x"], "y": n["y"],
                                    "n": n["n"]})
                if "label" in n:
                    derived.append({"type": "label", "text": n["label"],
                                    "anchor": [n["x"], n["y"], n["w"], n["h"]]})
            else:
                n.update(x=bb["x"] + bb["width"] / 2, y=bb["y"] + bb["height"] / 2)
    return notes + derived


def capture(page, out, notes=None, selector=None, fullpage=False):
    """Кадр -> PNG + WEBP, с аннотациями box/arrow/num/label. Возвращает (png, webp)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    notes = derive_notes(page, list(notes or []), fullpage)
    if selector:
        page.locator(selector).first.screenshot(path=str(out))
    else:
        page.screenshot(path=str(out), full_page=fullpage)
    if notes:
        annotate(out, notes)
    return out, B.to_webp(out)


def dismiss_consent(page, quiet=False):
    """Best-effort закрытие cookie/consent-баннеров. Число закрытых плашек."""
    hit = 0
    for sel in CONSENT_SELECTORS:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=500)
            loc.click(timeout=1500)
            page.wait_for_timeout(300)
            hit += 1
            if not quiet:
                print(f"  consent: закрыт баннер по {sel}")
            if hit >= 2:      # больше двух плашек подряд не бывает, дальше не тратим время
                break
        except Exception:
            continue
    return hit


def settle(page, selector=None, timeout=30000, pause=700):
    """Ожидание вместо networkidle: на живых SPA он не наступает (сокеты, поллинг,
    аналитика) и съёмка просто упирается в таймаут. Ждём DOM, нужный селектор,
    шрифты и короткую паузу на анимацию появления."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass
    if selector:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
    try:
        page.evaluate("document.fonts && document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(pause)


def retry(what, fn, tries=3, pause=1.2):
    """Разумный ретрай шага сценария: живой сервис отвечает не с первого раза."""
    last = None
    for i in range(1, max(1, tries) + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            head = str(e).strip().splitlines()[0][:140] if str(e).strip() else type(e).__name__
            print(f"  ретрай {i}/{tries}: {what} - {head}")
            if i < tries:
                time.sleep(pause)
    raise SystemExit(f"шаг не прошёл после {tries} попыток: {what} ({last})")


def new_context(pw_browser, viewport=None, state=None):
    """Контекст съёмки: свой чистый профиль, при --state - готовая storage_state."""
    kw = {"viewport": viewport or VIEWPORT, "device_scale_factor": SCALE,
          "locale": "ru-RU"}
    if state:
        sp = Path(state).expanduser()
        if not sp.is_file():
            raise SystemExit(f"--state: файла нет - {sp}")
        kw["storage_state"] = str(sp)
    return pw_browser.new_context(**kw)


# ---------------------------------------------------------------- манифест происхождения

def _rel_file(manifest_path, file_path):
    """Путь кадра в манифесте - относительно каталога манифеста (даёт assets/<имя>.webp)."""
    return os.path.relpath(Path(file_path).expanduser().resolve(),
                           Path(manifest_path).expanduser().resolve().parent)


def manifest_add(manifest_path, file_path, klass, url, mode, steps, note="",
                 shot_at=None):
    """Дописать запись о кадре в манифест происхождения (append; дубль по file
    перезаписывается). Ключи латиницей по контракту плана.

    shot_at - ДАТА СЪЁМКИ, а не дата записи: у кадра, снятого раньше (готовый файл со
    старой страницы, кадр из живого Chrome, кроп со старого hero), она приходит флагом
    --shot-at; без флага ставится сегодня.

    🔴 Значения полей fill сюда не попадают никогда: в манифест уходит только селектор
    поля и метка «заполнено», собранная вызывающим кодом."""
    if klass not in FRAME_CLASSES:
        raise SystemExit(f"--class: нужен один из {', '.join(FRAME_CLASSES)}")
    mp = Path(manifest_path).expanduser().resolve()
    mp.parent.mkdir(parents=True, exist_ok=True)
    data = {"frames": []}
    if mp.is_file():
        try:
            loaded = json.loads(mp.read_text())
            if isinstance(loaded, dict) and isinstance(loaded.get("frames"), list):
                data = loaded
            else:
                print(f"WARN: {mp} не похож на манифест кадров, начинаю новый")
        except json.JSONDecodeError:
            print(f"WARN: {mp} не читается как JSON, начинаю новый")
    rel = _rel_file(mp, file_path)
    rec = {"file": rel, "class": klass, "url": url or "-", "mode": mode,
           "steps": int(steps),
           "shot_at": shot_at or date.today().isoformat(),
           "note": B.no_long_dash(" ".join((note or "").split()))[:200]}
    data["frames"] = [f for f in data["frames"] if f.get("file") != rel] + [rec]
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"  манифест: {mp} <- {rel} [{klass} / {mode} / шагов {rec['steps']}]")
    return rec


def parse_shot_at(s):
    """--shot-at YYYY-MM-DD -> строка даты съёмки; пустое -> None (значит сегодня)."""
    if not s:
        return None
    s = str(s).strip()
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise SystemExit("--shot-at: нужен формат YYYY-MM-DD (дата съёмки кадра)")


def parse_crop(s):
    """--mobile-crop X,Y,W,H -> четыре числа в CSS-пикселях."""
    parts = [p.strip() for p in str(s).replace(";", ",").split(",") if p.strip()]
    if len(parts) != 4:
        raise SystemExit("--mobile-crop: нужен формат X,Y,W,H в CSS-пикселях")
    try:
        return [float(p) for p in parts]
    except ValueError:
        raise SystemExit("--mobile-crop: координаты должны быть числами")


def make_mobile(png_path, crop, width=MOBILE_WIDTH, scale=SCALE):
    """Мобильная версия кадра: плотный кроп той же зоны кейс-превью, суффикс -mobile.

    Координаты кропа - CSS-пиксели (как в --annotate), внутри домножаем на scale."""
    from PIL import Image
    png_path = Path(png_path)
    x, y, w, h = crop
    img = Image.open(png_path)
    box = (max(int(x * scale), 0), max(int(y * scale), 0),
           min(int((x + w) * scale), img.width), min(int((y + h) * scale), img.height))
    if box[2] - box[0] < 8 or box[3] - box[1] < 8:
        raise SystemExit(f"--mobile-crop: зона вне кадра {img.width}x{img.height} "
                         f"(в CSS-пикселях {img.width // scale}x{img.height // scale})")
    cut = img.crop(box).convert("RGB")
    if width and cut.width != int(width):
        target = int(width)
        cut = cut.resize((target, max(1, round(cut.height * target / cut.width))),
                         Image.LANCZOS)
    out = png_path.with_name(f"{png_path.stem}-mobile{png_path.suffix}")
    cut.save(out)
    # источник уже webp (кадр из живого Chrome) - второй конвертации не нужно
    webp = out if out.suffix.lower() == ".webp" else B.to_webp(out)
    print(f"  мобильный кадр: {out.name} {cut.width}x{cut.height}")
    return out, webp


# ---------------------------------------------------------------- режим URL

def shoot_url(a):
    from playwright.sync_api import sync_playwright
    notes = json.loads(a.annotate) if a.annotate else []
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()  # свой чистый профиль, никаких профилей автора
        ctx = new_context(b, VIEWPORT, a.state)
        page = ctx.new_page()
        try:
            page.goto(a.url, wait_until="networkidle", timeout=a.timeout)
            page.wait_for_timeout(800)
        except Exception as e:
            # networkidle не наступил (живой SPA) - не роняем кадр, добираем по DOM
            print(f"WARN: networkidle не дождался ({type(e).__name__}), "
                  f"добираю по DOM + селектору")
            page.goto(a.url, wait_until="domcontentloaded", timeout=a.timeout)
            settle(page, a.wait_for, a.timeout)
        if a.wait_for:
            page.wait_for_selector(a.wait_for, state="visible", timeout=a.timeout)
        if a.consent:
            dismiss_consent(page)
        png, webp = capture(page, out, notes, a.selector, a.fullpage)
        b.close()
    print("OK shot [url]")
    B.report(png, webp)
    if a.mobile_crop:
        mpng, mwebp = make_mobile(png, parse_crop(a.mobile_crop), a.mobile_width)
        B.report(mpng, mwebp)
    if a.manifest:
        klass = require_class(a)
        manifest_add(a.manifest, webp, klass, a.url, "url", 1, a.note)
        if a.mobile_crop:
            manifest_add(a.manifest, mwebp, klass, a.url, "url", 1,
                         f"мобильный кроп кадра {Path(webp).name}")


# ---------------------------------------------------------------- режим сценария

def load_scenario(path):
    """steps.json: список шагов или объект {"steps": [...]} с необязательными
    ключами viewport / state / class."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise SystemExit(f"--scenario: файла нет - {p}")
    try:
        raw = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"--scenario: битый JSON ({e})")
    if isinstance(raw, list):
        raw = {"steps": raw}
    if not isinstance(raw, dict) or not isinstance(raw.get("steps"), list):
        raise SystemExit("--scenario: нужен список шагов или объект с ключом steps")
    return raw


def norm_step(s):
    """Шаг: объект {"do": ...} или короткая строка «goto <url>» / «fill <сел> <знач>»."""
    if isinstance(s, dict):
        st = dict(s)
        st["do"] = str(st.get("do") or st.get("action") or st.get("type") or "").strip()
    elif isinstance(s, str):
        head, _, rest = s.strip().partition(" ")
        head, rest = head.strip(), rest.strip()
        if head == "goto":
            st = {"do": "goto", "url": rest}
        elif head in ("wait_for", "click"):
            st = {"do": head, "selector": rest}
        elif head == "fill":
            sel, _, val = rest.partition(" ")
            st = {"do": "fill", "selector": sel.strip(), "value": val}
        elif head == "shot":
            st = {"do": "shot", "name": rest}
        else:
            raise SystemExit(f"сценарий: непонятный шаг «{s}»")
    else:
        raise SystemExit(f"сценарий: шаг должен быть строкой или объектом, а не {type(s)}")
    if st["do"] not in ("goto", "wait_for", "click", "fill", "shot"):
        raise SystemExit(f"сценарий: неизвестное действие «{st['do']}» "
                         f"(есть goto / wait_for / click / fill / shot)")
    return st


def shoot_scenario(a):
    from playwright.sync_api import sync_playwright
    sc = load_scenario(a.scenario)
    steps = [norm_step(s) for s in sc["steps"]]
    if not any(s["do"] == "shot" for s in steps):
        raise SystemExit("сценарий без шага shot: снимать нечего")
    outdir = Path(a.out).expanduser()
    if outdir.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"):
        raise SystemExit("в сценарном режиме --out это КАТАЛОГ кадров "
                         "(имена берутся из шагов shot)")
    outdir.mkdir(parents=True, exist_ok=True)
    viewport = sc.get("viewport") or VIEWPORT
    state = a.state or sc.get("state")
    default_class = a.frame_class or sc.get("class")
    done = 0            # выполнено действий сценария до текущего кадра
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()  # свой чистый профиль, профиль владельца не трогаем
        ctx = new_context(b, viewport, state)
        page = ctx.new_page()
        page.set_default_timeout(a.timeout)
        for st in steps:
            op = st["do"]
            if op == "goto":
                url = st.get("url") or ""
                if not url:
                    raise SystemExit("шаг goto без url")
                print(f"  goto {url}")
                retry(f"goto {url}",
                      lambda u=url: page.goto(u, wait_until="domcontentloaded",
                                              timeout=a.timeout), a.retries)
                if a.consent:
                    dismiss_consent(page)
                settle(page, st.get("wait_for"), a.timeout)
                done += 1
            elif op == "wait_for":
                sel = st.get("selector") or ""
                print(f"  wait_for {sel}")
                retry(f"wait_for {sel}",
                      lambda s=sel: page.wait_for_selector(s, state="visible",
                                                           timeout=a.timeout), a.retries)
                done += 1
            elif op == "click":
                sel = st.get("selector") or ""
                print(f"  click {sel}")
                retry(f"click {sel}",
                      lambda s=sel: page.locator(s).first.click(timeout=a.timeout),
                      a.retries)
                settle(page, st.get("wait_for"), a.timeout,
                       pause=int(st.get("pause", 500)))
                done += 1
            elif op == "fill":
                sel = st.get("selector") or ""
                # значение не печатаем и не пишем в манифест - только факт заполнения
                print(f"  fill {sel}: заполнено")
                retry(f"fill {sel}",
                      lambda s=sel, v=str(st.get("value", "")):
                      page.locator(s).first.fill(v, timeout=a.timeout), a.retries)
                done += 1
            elif op == "shot":
                name = str(st.get("name") or f"shot-{len(made) + 1}").strip()
                if not name:
                    name = f"shot-{len(made) + 1}"
                out = outdir / (name if name.lower().endswith(".png") else f"{name}.png")
                if st.get("wait_for"):
                    page.wait_for_selector(st["wait_for"], state="visible",
                                           timeout=a.timeout)
                notes = st.get("annotate") or []
                if isinstance(notes, str):
                    notes = json.loads(notes)
                png, webp = capture(page, out, notes, st.get("selector"),
                                    bool(st.get("fullpage")))
                print(f"OK shot [scenario] {out.name}")
                B.report(png, webp)
                crop = st.get("mobile_crop") or (a.mobile_crop and parse_crop(a.mobile_crop))
                mwebp = None
                if crop:
                    crop = crop if isinstance(crop, (list, tuple)) else parse_crop(crop)
                    mpng, mwebp = make_mobile(png, [float(v) for v in crop],
                                              st.get("mobile_width") or a.mobile_width)
                    B.report(mpng, mwebp)
                if a.manifest:
                    klass = st.get("class") or default_class
                    if klass not in FRAME_CLASSES:
                        raise SystemExit(
                            f"кадру {out.name} нужен класс: --class или поле class "
                            f"в шаге ({', '.join(FRAME_CLASSES)})")
                    manifest_add(a.manifest, webp, klass, page.url, "scenario", done,
                                 st.get("note") or a.note)
                    if mwebp:
                        manifest_add(a.manifest, mwebp, klass, page.url, "scenario",
                                     done, f"мобильный кроп кадра {Path(webp).name}")
                made.append(out)
        b.close()
    print(f"OK сценарий: кадров {len(made)}, действий {done}")


# ---------------------------------------------------------------- регистрация чужого кадра

def register_external(a):
    """Кадр, снятый вне shot.py (живой Chrome), -> запись в манифест.

    Гейт frame-provenance ЧИТАЕТ поле mode и по нему отличает запись инструмента от
    рукописной строки: mode вне списка external|relay|url|scenario = съёмка не
    подтверждена, кадр непокрыт. external и relay остаются СЛАБЫМ происхождением:
    съёмку скрипт не подтверждал, судит приёмка глазами, и hero одной такой записью
    не закрывается."""
    src = Path(a.register_external).expanduser()
    if not src.is_file():
        raise SystemExit(f"--register-external: файла нет - {src}")
    if not a.manifest:
        raise SystemExit("--register-external: нужен --manifest (куда писать запись)")
    klass = require_class(a)
    mode = a.mode or "external"
    shot_at = parse_shot_at(getattr(a, "shot_at", None))
    if klass == "inherited" and not shot_at:
        print("WARN: кадр inherited снят раньше - без --shot-at в манифест уйдёт "
              "сегодняшняя дата, а ось приёмки «свежесть» читает её как дату съёмки")
    rec = manifest_add(a.manifest, src, klass, a.url, mode, 0,
                       a.note or "кадр снят вне shot.py", shot_at=shot_at)
    print(f"OK register-external [{mode}] {rec['file']}")
    if a.mobile_crop:
        mpng, mwebp = make_mobile(src, parse_crop(a.mobile_crop), a.mobile_width)
        # источник уже webp (кадр из живого Chrome) - make_mobile отдаёт один и тот
        # же путь дважды, вес печатаем одной строкой; порядок аргументов фиксирован
        if mwebp == mpng:
            B.report(mpng)
        else:
            B.report(mpng, mwebp)
        manifest_add(a.manifest, mwebp, klass, a.url, mode, 0,
                     f"мобильный кроп кадра {src.name}", shot_at=shot_at)


def require_class(a):
    if a.frame_class not in FRAME_CLASSES:
        raise SystemExit(f"нужен --class из списка: {', '.join(FRAME_CLASSES)}")
    return a.frame_class


# ---------------------------------------------------------------- режим терминала

# Локальный woff2 через file:// не грузится: страница отдаётся page.set_content(),
# её origin не file://, и Chromium режет подгрузку шрифта - мокап молча уезжал в
# системный Menlo, где два дефиса «--» слипаются в длинное тире, а «-type» читается
# как «–type». Поэтому терминалу шрифт отдаём инлайном (data:), своей семьёй.
_TERM_FONT_CACHE = None


def term_font_css():
    """@font-face JetBrains Mono инлайном (base64), семья 'JBMono Term'."""
    global _TERM_FONT_CACHE
    if _TERM_FONT_CACHE is None:
        import base64
        from pathlib import Path as _P
        here = _P(__file__).resolve().parent / "fonts"
        out = []
        for wgt in (400, 500, 700):
            for sub in ("latin", "cyrillic"):
                f = here / f"JetBrainsMono-{wgt}-normal-{sub}.woff2"
                if not f.exists():
                    continue
                b64 = base64.b64encode(f.read_bytes()).decode()
                out.append("@font-face{font-family:'JBMono Term';font-style:normal;"
                           f"font-weight:{wgt};font-display:block;"
                           f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        _TERM_FONT_CACHE = "".join(out)
    return _TERM_FONT_CACHE


def shoot_terminal(a):
    text = Path(a.terminal).read_text()
    lines_html = []
    for ln in text.rstrip("\n").split("\n"):
        e = B.esc(ln)
        if ln.startswith("$ "):
            lines_html.append(f'<div class="ln"><span class="pr">$</span>'
                              f'<span class="cmd">{B.esc(ln[2:])}</span></div>')
        else:
            lines_html.append(f'<div class="ln">{e or "&nbsp;"}</div>')
    body_lines = "".join(lines_html)
    title = B.esc(a.title or "терминал - zsh")
    css = f"""{term_font_css()}
body{{background:{B.PAPER};display:flex;align-items:center;justify-content:center;
  padding:44px;height:auto}}
.term{{width:1112px;border-radius:14px;overflow:hidden;background:#1A1613;
  box-shadow:0 26px 60px rgba(28,24,21,.38);border:1px solid rgba(0,0,0,.4)}}
.bar{{height:44px;background:#2A2521;display:flex;align-items:center;padding:0 18px;gap:9px;
  position:relative}}
.d{{width:14px;height:14px;border-radius:50%}}
.title{{position:absolute;left:0;right:0;text-align:center;color:#8F857A;
  font-family:'JBMono Term', monospace;font-size:17px}}
.feed{{padding:26px 30px 32px;font-family:'JBMono Term', monospace;font-size:19px;line-height:1.75;
  color:#D8D2C8;white-space:pre-wrap;overflow-wrap:anywhere;
  font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0}}
.pr{{color:{B.ACCENT};font-weight:700;margin-right:12px}}
.cmd{{color:#FAF6EF;font-weight:500}}
"""
    body = f"""<div class="term">
  <div class="bar"><span class="d" style="background:#FF5F57"></span>
    <span class="d" style="background:#FEBC2E"></span>
    <span class="d" style="background:#28C840"></span>
    <span class="title">{title}</span></div>
  <div class="feed">{body_lines}</div></div>"""
    html = B.page_html(body, css, 1200, 0)
    out = Path(a.out)
    B.render_html(html, out, 1200, 0, scale=2)
    webp = B.to_webp(out)
    print("OK shot [terminal]")
    B.report(out, webp)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="адрес кадра (режим --url; в сценарии - адрес "
                                  "для записи в манифест при --register-external)")
    ap.add_argument("--selector")
    ap.add_argument("--annotate", help="JSON-список аннотаций")
    ap.add_argument("--fullpage", action="store_true")
    ap.add_argument("--terminal", help="файл с реальным выводом команд (легаси)")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", help="файл кадра (--url/--terminal) или КАТАЛОГ кадров "
                                  "(--scenario)")
    # сценарная съёмка
    ap.add_argument("--scenario", help="steps.json: goto / wait_for / click / fill / shot")
    ap.add_argument("--state", help="playwright storage_state.json для залогиненной "
                                    "сессии (профиль владельца не трогаем)")
    ap.add_argument("--wait-for", dest="wait_for",
                    help="селектор готовности страницы вместо networkidle")
    ap.add_argument("--consent", action="store_true", default=None,
                    help="закрывать cookie/consent-баннеры (в сценарии включено по "
                         "умолчанию, отключить - --no-consent)")
    ap.add_argument("--no-consent", dest="consent", action="store_false",
                    help="не трогать баннеры согласия")
    ap.add_argument("--timeout", type=int, default=45000, help="мс на шаг, по умолчанию 45000")
    ap.add_argument("--retries", type=int, default=3, help="попыток на шаг, по умолчанию 3")
    # манифест происхождения
    ap.add_argument("--manifest", help="shots-manifest.json РЯДОМ со страницей "
                                       "($WORK/<slug>/), НЕ в assets/")
    ap.add_argument("--class", dest="frame_class", choices=list(FRAME_CLASSES),
                    help="класс кадра для манифеста: result | step | own-run "
                         "(inherited - только для --register-external)")
    ap.add_argument("--note", default="", help="одна строка пояснения в манифест")
    ap.add_argument("--shot-at", dest="shot_at",
                    help="YYYY-MM-DD, ДАТА СЪЁМКИ кадра для манифеста (по умолчанию "
                         "сегодня); ставить у кадра, снятого раньше - inherited "
                         "(готовый файл со старой страницы), кадр из живого Chrome, "
                         "кроп со старого hero")
    ap.add_argument("--register-external", dest="register_external",
                    help="зарегистрировать кадр, снятый вне shot.py (живой Chrome). "
                         "СЛАБЫЙ класс происхождения: съёмку скрипт не подтверждал, "
                         "hero одной такой записью не закрывается")
    ap.add_argument("--mode", choices=("external", "relay"),
                    help="способ получения кадра для --register-external (external "
                         "по умолчанию, relay - готовый файл забран с внешнего узла); "
                         "по этому полю гейт отличает запись shot.py от рукописной")
    # мобильная версия кадра
    ap.add_argument("--mobile-crop", dest="mobile_crop",
                    help="X,Y,W,H в CSS-пикселях: плотная зона того же кадра -> файл "
                         "с суффиксом -mobile рядом с основным")
    ap.add_argument("--mobile-width", dest="mobile_width", type=int, default=MOBILE_WIDTH,
                    help=f"итоговая ширина мобильного кадра, по умолчанию {MOBILE_WIDTH}")
    a = ap.parse_args()
    if a.frame_class == "inherited" and not a.register_external:
        ap.error("--class inherited годится только для --register-external")
    if a.shot_at and not a.register_external:
        # живая съёмка датируется днём прогона, задним числом её не подписывают
        ap.error("--shot-at годится только для --register-external")
    if a.register_external:
        register_external(a)
        return
    if not a.out:
        ap.error("нужен --out")
    if a.scenario:
        if a.consent is None:
            a.consent = True          # в сценарии баннер гарантированно портит кадр
        shoot_scenario(a)
    elif a.terminal:
        shoot_terminal(a)
    elif a.url:
        shoot_url(a)
    else:
        ap.error("нужен --url, --scenario, --terminal или --register-external")


if __name__ == "__main__":
    main()
