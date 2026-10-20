#!/usr/bin/env python3
"""Замок против ложной расписки о скрин-приёмке.

Прецедент по решению автора, круг 5 у guide-neyroset-kandinskiy: страницу пересобрали,
обложки пересняли, а кадры приёмки остались от прошлой сборки - и в отчёте при
этом стояла строка «кадры сняты ПОСЛЕ последней сборки, смотрел глазами».
Повтор по решению автора, круг 7 у guide-neyroset-pozdravlenie: галочка «Скрин-приёмка
глазами» стояла на кадрах, снятых за четыре часа и две пересборки до страницы;
именно эта дыра пропустила кадр без кнопок и пункт на две экранные высоты.
Третий повтор по решению автора, круг 12 у guide-neyroset-kandinskiy: черновик правили
ПОСЛЕ съёмки пачки, страницу пересобирали, а расписка осталась от прошлой
сборки - и отгружаемый абзац FAQ не видел глазами никто. Причина повторов одна:
до круга 13 этот файл не звал ни один гейт, правило держалось на дисциплине.

Две проверки, обе обязательные.

  A. СВЕЖЕСТЬ. Самый свежий кадр приёмки обязан быть не старше index.html, и ни
     одного кадра старше страницы в текущей пачке быть не должно.

  B. РАСПИСКА. Каждое имя кадра, названное в отчётах каталога (*.md), обязано
     существовать на диске. Расписка, ссылающаяся на кадр, которого нет, - тот
     же класс дефекта: улика названа, улики нет. Найдено круга 13 в двух статьях
     корпуса из 136, в обеих настоящие пропажи (напр. в отчёте guide-neyroset-
     kandinskiy стояли qa-d-shagi.png, qa-d-tablica.png, qa-d-kadr.png,
     qa-d-faq.png, которых на диске не было никогда).

Кадры ищем в трёх раскладках, все три живут в корпусе:
  <статья>/qa-*.png|jpg           - плоская раскладка
  <статья>/priyomka/*.png|jpg     - отдельная папка приёмки
  <статья>/qa-screenshots/*       - раскладка ранних волн

Папки, в имени которых есть «arhiv»/«archiv», из ТЕКУЩЕЙ пачки исключены: там
живёт приёмка прошлых кругов, история, а не расписка за отгружаемую сборку. Для
проверки B они, наоборот, считаются: кадр, названный в отчёте прошлого круга и
убранный в архив, - не пропажа. ГРАНИЦА ИНСТРУМЕНТА, названная честно: увести
свежую пачку в архив и не переснять он не ловит, это ловит скептик по составу
отчёта. Архив заводить только вместе с полной пересъёмкой.

Запуск: python3 qa_freshness.py <каталог-статьи>
Коды: 0 - приёмка свежая, 1 - приёмка протухла, 2 - приёмку не снимали,
      3 - расписка называет кадр, которого нет на диске
"""
import re
import sys
import time
from pathlib import Path

DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
PAGE = DIR / "index.html"
EXT = (".png", ".jpg", ".jpeg")
ARCHIVE_MARK = ("arhiv", "archiv")
# имя кадра в тексте отчёта. Диапазонная запись «qa-look-desktop-1..8.jpg» - это
# сокращение для восьми файлов, а не имя файла: две точки подряд отсекаем, иначе
# гейт краснеет на честной расписке (ложное срабатывание, найдено круга 13)
NAMED_RE = re.compile(r"qa-[A-Za-z0-9_.\-]*\.(?:png|jpe?g)", re.I)


def stamp(t):
    return time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(t))


def is_archive(p, root):
    return any(m in part.lower() for part in p.relative_to(root).parts[:-1]
               for m in ARCHIVE_MARK)


def collect(d, with_archive=False):
    """Кадры приёмки. with_archive=False - только текущая пачка."""
    shots = []
    for pat in ("qa-*.png", "qa-*.jpg", "qa-*.jpeg"):
        shots += list(d.glob(pat))
    for sub in ("priyomka", "qa-screenshots"):
        p = d / sub
        if p.is_dir():
            shots += [f for f in p.rglob("*") if f.suffix.lower() in EXT]
    if with_archive:
        for f in d.rglob("*"):
            if f.suffix.lower() in EXT and is_archive(f, d):
                shots.append(f)
    else:
        shots = [f for f in shots if not is_archive(f, d)]
    return sorted(set(shots))


def named_in_reports(d):
    """{имя кадра: [отчёты, где названо]} по всем *.md каталога, кроме бэкапов."""
    named = {}
    for rep in sorted(d.glob("*.md")):
        if ".bak-" in rep.name or rep.name.endswith(".bak"):
            continue
        try:
            text = rep.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in NAMED_RE.finditer(text):
            name = m.group(0)
            if ".." in name:          # диапазон «-1..8.jpg», не имя файла
                continue
            named.setdefault(name, []).append(rep.name)
    return named


def anywhere_on_disk(d):
    """Все кадры каталога статьи, В ЛЮБОЙ вложенности.

    по решению автора: проверка B резолвила имена только по трём раскладкам приёмки
    (collect), а исходники кадров лежат ещё и в visual-src/ - у guide-ii-navyki
    гейт краснел на qa-r12-desktop-figure0.png, qa-r12-desktop-ctainline0.png и
    qa-r12-mobile-ctainline0.png, которые ФИЗИЧЕСКИ ЕСТЬ в visual-src/. Это
    ложное срабатывание: отчёт называл настоящую улику, а гейт смотрел не туда.
    Проверка A (свежесть текущей пачки) намеренно осталась на узком collect -
    там раскладка и должна быть строгой, иначе старый исходник из visual-src/
    сойдёт за свежий кадр приёмки.
    """
    return {f.name for f in d.rglob("*") if f.suffix.lower() in EXT}


def check_claims(d):
    """B: расписка называет кадр, которого нет на диске. rc 3 либо 0."""
    named = named_in_reports(d)
    if not named:
        return 0
    on_disk = {p.name for p in collect(d, with_archive=True)} | anywhere_on_disk(d)
    missing = sorted(n for n in named if n not in on_disk)
    print(f"кадров названо в отчётах: {len(named)}, нет на диске: {len(missing)}")
    if missing:
        print("РАСПИСКА БЕЗ УЛИКИ, названы кадры, которых на диске нет:")
        for n in missing[:20]:
            print(f"  {n}  <- {', '.join(sorted(set(named[n])))}")
        return 3
    return 0


def main():
    if not PAGE.exists():
        print("нет index.html, проверять нечего")
        return 2
    page_t = PAGE.stat().st_mtime
    shots = collect(DIR)
    arch = [p for p in collect(DIR, with_archive=True) if is_archive(p, DIR)]

    if not shots:
        print("нет ни одного кадра приёмки (qa-*.png|jpg, priyomka/*, "
              "qa-screenshots/*), приёмка не снималась - расписку писать нельзя")
        if arch:
            print(f"в архивных папках при этом лежит кадров: {len(arch)}")
        rc_claims = check_claims(DIR)
        return rc_claims or 2

    stale = [p for p in shots if p.stat().st_mtime < page_t]
    newest = max(shots, key=lambda p: p.stat().st_mtime)
    print(f"index.html       : {stamp(page_t)}")
    print(f"самый свежий кадр: {stamp(newest.stat().st_mtime)}  {newest.name}")
    print(f"кадров в пачке   : {len(shots)}, старше страницы: {len(stale)}"
          + (f", в архиве ещё {len(arch)}" if arch else ""))

    if newest.stat().st_mtime < page_t:
        print("ПРОТУХЛА: вся приёмка старше страницы, расписку писать нельзя")
        return 1
    if stale:
        print("ЧАСТИЧНО ПРОТУХЛА, кадры старше страницы:")
        for p in stale[:20]:
            print(f"  {stamp(p.stat().st_mtime)}  {p.relative_to(DIR)}")
        return 1

    rc_claims = check_claims(DIR)
    if rc_claims:
        return rc_claims
    print("СВЕЖАЯ: каждый кадр приёмки снят после последней сборки, "
          "и каждый названный в отчёте кадр лежит на диске")
    return 0


if __name__ == "__main__":
    sys.exit(main())
