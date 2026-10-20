#!/usr/bin/env python3
"""Пост-обработка картинки для статьи: WebP + JPEG fallback, слаг-имя,
проверка alt, готовый <figure>-сниппет.

python3 convert.py --in raw.png --slug claude-code-ustanovka-mac \\
    --alt "Терминал macOS: установка Claude Code командой npm install" \\
    [--caption "Подпись под картинкой"] [--outdir <каталог статьи>/assets] \\
    [--url-prefix assets/] [--quality 82] [--eager]

Делает:
  1. <slug>.webp (quality 82) + <slug>.jpg (fallback) в --outdir
  2. Проверяет alt: 50-125 знаков (SEO-норма), иначе предупреждение
  3. Печатает готовый <figure> с <picture>, width/height, loading, figcaption
     (--eager для hero: loading="eager" fetchpriority="high", иначе lazy)

🔴 Канон путей (components.md, раздел «Единый канон путей картинок»): картинки статьи
живут в подкаталоге `assets/` каталога статьи и адресуются ОТНОСИТЕЛЬНЫМ путём
`assets/<имя>.webp` - так работает живая страница и так же кладёт файлы ftp_publish.py
(/guide-<slug>/assets/…). Каталога `/images/` на проде нет. `--url-prefix` менять только
под общий ассет сайта (фото автора, favicon): там канон корневой `/assets/`.
"""
import argparse
import re
import sys
from pathlib import Path
import _brand as B


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--slug", required=True, help="имя-через-дефис с ключом")
    ap.add_argument("--alt", required=True)
    ap.add_argument("--caption", default="")
    ap.add_argument("--outdir", default="assets",
                    help="куда класть файлы (канон: <каталог статьи>/assets)")
    ap.add_argument("--url-prefix", default="assets/",
                    help="префикс пути в разметке (канон: относительный assets/; "
                         "корневой /assets/ - только для общих ассетов сайта)")
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--eager", action="store_true", help="hero: eager + fetchpriority")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.slug):
        sys.exit(f"FAIL: слаг «{a.slug}» не в формате слов-через-дефис (a-z, 0-9)")

    n = len(a.alt)
    if n < 50 or n > 125:
        print(f"WARN: alt {n} знаков (норма 50-125) - поправь", file=sys.stderr)
    else:
        print(f"alt ok: {n} знаков")

    from PIL import Image
    src = Path(a.src)
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    w, h = img.size
    webp = outdir / f"{a.slug}.webp"
    jpg = outdir / f"{a.slug}.jpg"
    B.to_webp(src, webp, quality=a.quality)
    B.to_jpeg(src, jpg)
    B.report(webp, jpg)

    loading = ('loading="eager" fetchpriority="high"' if a.eager else 'loading="lazy"')
    cap = f"\n  <figcaption>{B.esc(a.caption)}</figcaption>" if a.caption else ""
    pref = a.url_prefix if a.url_prefix.endswith("/") or not a.url_prefix else a.url_prefix + "/"
    print(f"""
<figure class="fig">
  <picture>
    <source srcset="{pref}{webp.name}" type="image/webp">
    <img src="{pref}{jpg.name}" alt="{B.esc(a.alt)}"
         width="{w}" height="{h}" {loading} decoding="async">
  </picture>{cap}
</figure>""")


if __name__ == "__main__":
    main()
