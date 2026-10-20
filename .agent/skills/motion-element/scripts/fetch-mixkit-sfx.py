#!/usr/bin/env python3
"""fetch-mixkit-sfx.py — скачать edit-grade cinematic SFX с Mixkit (keyless, free, без атрибуции).

Проверенный механизм (ресёрч 2026-06-01): страница категории Mixkit содержит прямые
ссылки assets.mixkit.co/active_storage/sfx/<id>/<id>-preview.mp3 — качаются без ключа/аккаунта.
Лицензия Mixkit Free: коммерция OK, без атрибуции, без регистрации.

Это РЕАЛЬНАЯ палитра, что юзают эдиторы рилз (cinematic whoosh/swoosh/transition/impact/magic),
в отличие от game-audio (Kenney) и синтеза. См. knowledge/sound-design-standards.md + free-audio-sources.md.

Usage: python3 fetch-mixkit-sfx.py [out_dir]   (default ~/.business/assets/sfx-library/mixkit)
Затем пересобрать манифест (scripts/build-library-manifest или вручную) и подменить sorted/.
"""
import urllib.request, re, os, sys

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
# mixkit category slug -> наша таксономия
CATS = [("whoosh","whoosh"),("swoosh","whoosh"),("transition","whoosh"),("impact","impact"),
        ("magic","sparkle"),("pop","pop"),("riser","riser"),("glitch","glitch"),
        ("bass","sub"),("cinematic","stinger")]

def fetch(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf-8","ignore")
    except Exception:
        return ""

def main(out):
    os.makedirs(out, exist_ok=True)
    total = 0
    for slug, tax in CATS:
        html = fetch(f"https://mixkit.co/free-sound-effects/{slug}/")
        ids = sorted(set(re.findall(r'assets\.mixkit\.co/active_storage/sfx/(\d+)/\d+-preview\.mp3', html)))
        d = os.path.join(out, tax); os.makedirs(d, exist_ok=True); n = 0
        for i in ids:
            dst = os.path.join(d, f"mixkit_{i}.wav")
            if os.path.exists(dst): n += 1; continue
            try:
                # FULL quality .wav (НЕ -preview.mp3 — то низкое качество, 18КБ vs 127КБ)
                data = urllib.request.urlopen(urllib.request.Request(
                    f"https://assets.mixkit.co/active_storage/sfx/{i}/{i}.wav", headers=UA), timeout=30).read()
                if len(data) > 2000:
                    open(dst, "wb").write(data); n += 1
            except Exception:
                pass
        print(f"  {slug:12}→ {tax:8} {n}")
        total += n
    print("TOTAL:", total)

if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.business/assets/sfx-library/mixkit"))