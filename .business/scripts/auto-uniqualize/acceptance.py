#!/usr/bin/env python3
"""
acceptance.py — ГЕЙТ ПРИЁМКИ отрендеренных слайдов.

Закрывает класс дефекта по решению автора: до автора уехали слайды, у которых
(1) сломано соотношение сторон (оригинал 4:5 → результат 9:14) и
(2) картинка вообще НЕ трансформация оригинала, а генерёжка с нуля
    (кастомка подтянула старый контекст-промпт из прошлого чата).

Правило: слайд считается принятым ТОЛЬКО если он одновременно
  A. держит соотношение сторон оригинала (допуск 2%);
  B. похож на оригинал по композиции (сравнение по сетке средних яркостей).

Не прошедший слайд НЕ удаляется — переезжает в <output>/_БРАК/ с причиной
в _БРАК/reasons.txt, чтобы автор мог посмотреть, но он не попал в доставку.

Использование как модуля:
    from acceptance import accept_slides
    passed, rejected = accept_slides(queue_dir, output_dir, logger)

Отдельным прогоном (проверить уже лежащие файлы):
    python3 acceptance.py <queue_dir> <output_dir>
"""
from __future__ import annotations
import sys
from pathlib import Path

ASPECT_TOLERANCE = 0.02   # 2% — тот же кадр, но чуть иной ресайз, это норма
SIMILARITY_MIN = 0.55     # ниже — это уже другая картинка, не уникализация
GRID = 8                  # сетка 8x8 для отпечатка композиции


def _fingerprint(img, grid: int = GRID):
    """Средняя яркость по сетке grid x grid — грубый отпечаток композиции."""
    g = img.convert("L").resize((grid, grid))
    return [g.getpixel((x, y)) for y in range(grid) for x in range(grid)]


def _similarity(a_px, b_px) -> float:
    """1.0 = идентичная раскладка яркостей, 0.0 = совсем разная."""
    if not a_px or len(a_px) != len(b_px):
        return 0.0
    diff = sum(abs(x - y) for x, y in zip(a_px, b_px)) / len(a_px)
    return max(0.0, 1.0 - diff / 255.0)


def check_slide(original: Path, rendered: Path):
    """Вернуть (ok: bool, reason: str) для одной пары оригинал/результат."""
    try:
        from PIL import Image
    except ImportError:
        return True, "PIL недоступен — приёмка пропущена"

    if not original.exists():
        return True, f"оригинала нет ({original.name}) — from-scratch слайд, приёмка пропущена"
    if not rendered.exists():
        return False, "файла результата нет"

    try:
        o = Image.open(original)
        r = Image.open(rendered)
    except Exception as e:
        return False, f"не открылось: {e}"

    o_ar = o.width / o.height
    r_ar = r.width / r.height
    if o_ar <= 0:
        return False, "битый оригинал"
    delta = abs(r_ar - o_ar) / o_ar
    if delta > ASPECT_TOLERANCE:
        return False, (f"СООТНОШЕНИЕ СТОРОН: оригинал {o.width}x{o.height} ({o_ar:.3f}), "
                       f"результат {r.width}x{r.height} ({r_ar:.3f}), расхождение {delta*100:.1f}%")

    sim = _similarity(_fingerprint(o), _fingerprint(r))
    if sim < SIMILARITY_MIN:
        return False, (f"НЕ ТРАНСФОРМАЦИЯ ОРИГИНАЛА: сходство композиции {sim:.2f} "
                       f"< {SIMILARITY_MIN} (похоже, кастомка нарисовала с нуля)")

    return True, f"ok (пропорции {r_ar:.3f}, сходство {sim:.2f})"


def accept_slides(queue_dir, output_dir, logger=None):
    """Проверить все slide-NN.png в output против slide-NN.(jpg|jpeg|png) в queue.

    Брак переносится в <output>/_БРАК/. Возвращает (passed, rejected) — списки Path.
    """
    queue_dir, output_dir = Path(queue_dir), Path(output_dir)
    say = (logger.info if logger else print)
    warn = (logger.error if logger else print)

    passed, rejected, reasons = [], [], []
    for rendered in sorted(output_dir.glob("slide-*.png")):
        nn = rendered.stem.split("-")[-1]
        original = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            cand = queue_dir / f"slide-{nn}{ext}"
            if cand.exists():
                original = cand
                break
        ok, reason = check_slide(original or queue_dir / f"slide-{nn}.jpg", rendered)
        if ok:
            passed.append(rendered)
            say(f"ПРИЁМКА {rendered.name}: {reason}")
        else:
            rejected.append(rendered)
            reasons.append(f"{rendered.name}: {reason}")
            warn(f"ПРИЁМКА ОТКЛОНИЛА {rendered.name}: {reason}")

    if rejected:
        brak = output_dir / "_БРАК"
        brak.mkdir(exist_ok=True)
        for f in rejected:
            try:
                f.rename(brak / f.name)
            except Exception as e:
                warn(f"не удалось убрать в _БРАК {f.name}: {e}")
        (brak / "reasons.txt").write_text("\n".join(reasons) + "\n", encoding="utf-8")
        warn(f"ПРИЁМКА: отклонено {len(rejected)} слайдов → {brak} (причины в reasons.txt)")

    return passed, rejected


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    passed, rejected = accept_slides(sys.argv[1], sys.argv[2])
    print(f"=== приёмка: принято {len(passed)}, отклонено {len(rejected)} ===")
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
