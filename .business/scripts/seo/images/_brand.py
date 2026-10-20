#!/usr/bin/env python3
"""Общий слой картинко-конвейера SEO: бренд-токены, рендер HTML->PNG, конвертация.

Используется og_hero.py / meme.py / shot.py / cards.py / convert.py.
Шрифты локальные (fonts/*.woff2), сеть при рендере не нужна.
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- бренд-палитра <твой-домен> ----
PAPER = "#FAF6EF"
INK = "#1C1815"
ACCENT = "#BE4A24"
MUTED = "#6E655B"          # приглушённый текст на бумаге
LINE = "rgba(28,24,21,.14)"  # тонкие линии/рамки
PAPER_DIM = "#F2ECE1"       # чуть темнее бумаги (панели)
SITE = "<твой-домен>"

# Кириллица: у Fraunces/Newsreader нет кириллицы (как и на проде - там фолбэк serif).
# Латиница (Claude Code, AI...) идёт Fraunces, кириллица - Georgia (тёплый editorial serif).
SERIF = "'Fraunces', Georgia, serif"
TEXT_SERIF = "'Newsreader', Georgia, serif"
MONO = "'JetBrains Mono', Menlo, monospace"

_FONT_CSS_CACHE = None


def font_css() -> str:
    """@font-face с абсолютными file:// путями к локальным woff2."""
    global _FONT_CSS_CACHE
    if _FONT_CSS_CACHE is None:
        css = (HERE / "fonts.css").read_text()
        _FONT_CSS_CACHE = css.replace("fonts/", f"file://{HERE}/fonts/")
    return _FONT_CSS_CACHE


BASE_CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:100%;height:100%}}
body{{background:{PAPER};color:{INK};font-family:{TEXT_SERIF};
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}}
"""


def page_html(body: str, extra_css: str = "", width: int = 1200, height: int = 630) -> str:
    size = (f"height:{height}px;overflow:hidden" if height
            else "height:auto;min-height:0;overflow:visible")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{font_css()}{BASE_CSS}
html,body{{height:auto}}
body{{width:{width}px;{size}}}
{extra_css}</style></head><body>{body}</body></html>"""


def render_html(html: str, out_png, width: int, height: int = 0, scale: int = 2):
    """HTML -> PNG через headless Chromium. height=0 -> авто по контенту.

    Рендер в scale x, даунскейл LANCZOS до целевого размера (чёткая типографика).
    Возвращает (w, h) итогового PNG.
    """
    from playwright.sync_api import sync_playwright
    from PIL import Image
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": width, "height": height or 800},
                          device_scale_factor=scale)
        page.set_content(html, wait_until="load")
        page.evaluate("document.fonts.ready.then(()=>1)")
        page.wait_for_timeout(150)
        if not height:  # авто-высота по фактическому контенту
            height = int(page.evaluate(
                "Math.ceil(document.body.getBoundingClientRect().bottom)"))
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(80)
        page.screenshot(path=str(out_png),
                        clip={"x": 0, "y": 0, "width": width, "height": height})
        b.close()
    img = Image.open(out_png)
    if scale > 1:
        img = img.resize((img.width // scale, img.height // scale), Image.LANCZOS)
        img.save(out_png)
    return img.size


def to_webp(png_path, out=None, quality: int = 82):
    from PIL import Image
    png_path = Path(png_path)
    out = Path(out) if out else png_path.with_suffix(".webp")
    Image.open(png_path).convert("RGB").save(out, "WEBP", quality=quality, method=6)
    return out


def to_jpeg(png_path, out=None, quality: int = 88):
    from PIL import Image
    png_path = Path(png_path)
    out = Path(out) if out else png_path.with_suffix(".jpg")
    Image.open(png_path).convert("RGB").save(out, "JPEG", quality=quality,
                                             optimize=True, progressive=True)
    return out


# Длинное и среднее тире - маркер ИИ, в бренд-текстах их нет (правило автора).
# Вшитое в картинку тире обходит ВСЕ текстовые гейты страницы: grep по HTML чист,
# а на карточке глиф длиннее дефиса. Поэтому режем на общем входе типографики -
# esc() зовут все генераторы (cards / cover / og_hero / meme / chatgpt_cover).
LONG_DASHES = {"—": "-", "–": "-", "―": "-", "−": "-"}


def no_long_dash(s) -> str:
    """Длинное/среднее тире и минус -> обычный дефис."""
    s = str(s)
    for bad, good in LONG_DASHES.items():
        s = s.replace(bad, good)
    return s


def esc(s: str) -> str:
    s = no_long_dash(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def report(*paths):
    for p in paths:
        p = Path(p)
        print(f"  {p}  {p.stat().st_size/1024:.0f} KB")
