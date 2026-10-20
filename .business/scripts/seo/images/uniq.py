#!/usr/bin/env python3
"""Общий гейт уникальности обложек: опубликованный корпус + ОЧЕРЕДЬ на публикацию.

Зачем. по решению автора две статьи вышли с одной и той же обложкой. Каждый агент честно
прогнал попарный diff, но сравнивал только с УЖЕ опубликованным кластером - друг про
друга они не знали. При параллельной публикации это дыра размером с весь релиз.

Решение - один индекс на машину. Любая обложка, которую сгенерил ЛЮБОЙ генератор
(cover.py, chatgpt_cover.py, og_hero.py), сразу попадает в индекс со статусом `queued`
и с этого момента видна всем остальным прогонам. Второй агент, который принесёт похожую
картинку, упрётся в гейт ещё до вёрстки страницы.

═══════════════════════════════════════════════════════════════════════════════
ВЕРСИЯ 2 (по решению автора). Почему переделан: гейт стал непроходим штатными генераторами,
и виноват был не набор сцен, а сама метрика.

Что было. Третья метрика `struct_sim` считала МЕДИАНУ корреляции карт границ по 16
тайлам и работала безусловным override: `if struct >= 0.40: клон` - при любой пиксельной
разнице. Замер по индексу (62 обложки, 1868 пар) показал две вещи:
  1. Тайлы пустых полей и общего бренд-каркаса (отбивки, футер, виньетка) у ЛЮБЫХ двух
     наших обложек совпадают буквально, корреляция ровно 1.000. Когда таких тайлов 8 из
     16, медиана скачет в 1.000 - хотя ВСЁ содержимое разное. Так две обложки разных
     статей (`pilot-guide-claude-code` и `guide-neyropoisk`) получали struct 1.000 при
     8 тайлах контента с корреляцией 0.02..0.08.
  2. Порог 0.40 стоял внутри шума: p99 честных пар корпуса = 0.391, а перекодировка
     PNG->WebP сдвигала struct до 0.156. Вердикт зависел от кодека.
Итог старого гейта на размеченном наборе: 8 ложных клонов из 23 честно разных пар.

Что теперь. Метрика идентичности вместо метрики похожести композиции, три канала:
  mean|Δ|  - средняя разница пикселей 0-255 (как было)
  share    - доля различающихся пикселей, |Δ|.max(axis=2) > 16 (как было)
  znd      - L1 между картинками, НОРМИРОВАННЫМИ по своему контрасту. Корпус почти весь
             тёмный: там абсолютная пиксельная разница структурно мала, и порог
             `mean < 15` ловил честно разные обложки. Нормировка по своему среднему и
             своей сигме убирает эту фору тёмного кадра
  scene    - тот же L1, но на ГРУБОЙ карте 64px (гаусс + BOX-даунсемпл). Типографика на
             ней исчезает, остаются большие формы: «та же картинка под другой надписью»

Вердикт клона (порог по замеру, зазор до ближайшей честной пары в комментарии):
  mean|Δ| < 6                          - тот же файл/тот же кадр
  share < 10% И znd < 0.40             - различие только в надписи (ближайшая честная
                                         пара корпуса: share 10.1%)
  scene < 0.20                         - та же картинка при любом тексте (ближайшая
                                         честная пара: 0.253)

🔴 Что гейт БОЛЬШЕ НЕ считает клоном: «та же композиция при другом содержимом». Замер
показал, что фотометрически это неотличимо от нужного клона и даже мягче его: две
обложки шаблона `object` с РАЗНЫМИ предметами (лупа против сферы) расходятся на
scene 0.253, а две обложки шаблона og_hero с РАЗНЫМИ заголовками - на 0.417. Один порог
физически не может пропустить первое и зарубить второе. Поэтому:
  - картинка гейтится на ИДЕНТИЧНОСТЬ (этот файл),
  - композиция гейтится на УНИКАЛЬНОСТЬ ПО ПОСТРОЕНИЮ - реестр сцен `scenes.json`
    (`--scene-claim`): генератор объявляет кортеж осей сцены ДО рендера, и один кортеж
    не может достаться двум статьям. Это точное сравнение строк, метрика не участвует.

Свои картинки одной страницы (один slug) друг с другом не сравниваются: hero и og
одной статьи - это одна фотография в двух раскладках, так и задумано.

CLI:
    python3 uniq.py --seed                     # пересобрать индекс: хинты имени (обложки)
                                               # + кадры из shots-manifest.json рядом со
                                               # страницами, только кандидаты в обложку
                                               # (класс result / own-run; step и inherited
                                               # в индекс уникальности не берутся)
    python3 uniq.py --prune                    # выкинуть мёртвые записи и скрины страниц
    python3 uniq.py --check FILE --slug SLUG   # проверить, не клон ли (не пишет в индекс)
    python3 uniq.py --register FILE --slug SLUG --role og --status queued
    python3 uniq.py --publish SLUG             # пометить обложки слага как published
    python3 uniq.py --matrix A.png B.png ...   # попарная таблица по произвольным файлам
    python3 uniq.py --scene-claim SIG --slug SLUG   # занять кортеж сцены (exit 4 = занят)
    python3 uniq.py --scene-list
    python3 uniq.py --forget SLUG              # снять обложки слага и освободить кортежи
    python3 uniq.py --selftest                 # прогон порогов по размеченным парам
    python3 uniq.py --list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

def отложить(путь, ignore_errors=False):
    """ЗАКОН №0 владельца (по решению автора, дословно «вообще ничего не удаляй, пусть лежит»).

    Обратимая замена сноса: путь ПЕРЕИМЕНОВЫВАЕТСЯ в датированного соседа
    `<имя>.otlozheno-<ГГГГММДД-ЧЧММСС>`. Прежнее имя после вызова свободно,
    и маска `*.png` / `index.json` его уже не ловит, а байты остаются на диске.
    Заведено по решению автора: страж удалений не давал ЗАПУСТИТЬ инструмент,
    в теле которого лежал вызов удаления.
    """
    try:
        if not путь or not os.path.exists(путь):
            return None
        метка = time.strftime("%Y%m%d-%H%M%S")
        цель = "%s.otlozheno-%s" % (путь, метка)
        n = 0
        while os.path.exists(цель):
            n += 1
            цель = "%s.otlozheno-%s-%d" % (путь, метка, n)
        os.rename(путь, цель)
        return цель
    except OSError:
        if ignore_errors:
            return None
        raise


HERE = Path(__file__).resolve().parent
INDEX_DIR = HERE / "cover-index"
THUMBS = INDEX_DIR / "thumbs"
INDEX = INDEX_DIR / "index.json"
SCENES = INDEX_DIR / "scenes.json"
LOCK = INDEX_DIR / ".lock"

THUMB = (600, 315)
COARSE_W = 64           # ширина грубой карты: на ней типографика уже не читается
COARSE_BLUR = 1.4

CLONE_HARD = 6.0        # mean|Δ| ниже - клон при любой доле различий
SHARE_SAME = 0.10       # доля различающихся пикселей ниже (вместе с ZND_SAME) - клон
ZND_SAME = 0.40         # норм-контрастное расстояние по всему кадру
SCENE_SAME = 0.20       # норм-контрастное расстояние на грубой карте - «та же картинка»
# полоса предупреждения: не блокирует, но печатает «семейное сходство»
WARN_SHARE, WARN_SCENE = 0.35, 0.45

# Порог самообороны гейта (И1.8а, прецедент дубль-обложки по решению автора): живой индекс сейчас
# держит 282 записи. Если на гейт-путях (check/register/publish/prune/list) индекс
# внезапно оказался сильно меньше этого - это не «мало обложек», а похоже на потерю
# данных (битый файл переписан пустым/урезанным), и гейт обязан упасть, а не тихо
# сравнить новую обложку с горсткой записей и сказать «уникально».
#
# ПОРОГ СУДИТ ПАДЕНИЕ, А НЕ МОЛОДОСТЬ (р9-по решению автора, находка панели Ф6-2). У порога
# была слепая зона на другом конце: ЧИСТАЯ машина. Там индекса нет вовсе,
# документированный --seed находит ноль обложек (корпуса ещё нет), и следующий же
# обязательный шаг приёмки `--register` падал exit 5 «0 записей < 20 - похоже на
# потерю данных». Ученик упирался в это на ПЕРВОЙ же статье, и дальше тоже: пока
# обложек меньше двадцати, каждая регистрация давала тот же провал.
#
# ОТСУТСТВУЮЩИЙ ИНДЕКС = ТОТ ЖЕ БУТСТРАП (рв даты запуска.2026, находка панели Ф6-3).
# Половину слепой зоны закрыли, вторая осталась и стоила ученику первого же шага:
# ПУСТОЙ индекс (файл есть, в нём []) и ОТСУТСТВУЮЩИЙ (файла нет вовсе) в коде были
# разными вещами, и на чистой машине - там каталога cover-index нет по построению -
# первый же `--register` падал exit 5 «индекс уникальности отсутствует», хотя канон
# чек-листа обещает «--register заводит первую запись и не роняет шаг». Обходной
# `--seed` существовал только чтобы погасить сообщение об ошибке, и в чек-листе
# назван не был. Теперь отсутствие файла разбирается тем же следом наполненности,
# что и урезанный индекс: миниатюр рядом меньше порога - машина молода, индекс
# заводится первой же регистрацией; миниатюр много, а индекса нет - это потеря
# данных, и гейт падает, как падал.
# Разводит случаи не размер индекса, а СЛЕД НАПОЛНЕННОСТИ на диске - миниатюры
# thumbs/ (по одной на запись, их не удаляют ни --prune, ни --forget, см.
# index_seen_covers). Машина, видевшая меньше MIN_INDEX_ROWS обложек, просто молода:
# индекс из нуля-трёх записей у неё законен, сравнивать пока не с чем. Машина,
# видевшая больше, с урезанным индексом - потеря данных, и гейт падает, как падал
# (И1.8а в полной силе: на живом индексе рядом лежат 904 миниатюры).
MIN_INDEX_ROWS = 20

# где искать обложки при --seed (и опубликованные, и лежащие в работе)
SEED_GLOBS = [
    HERE / "covers-photo",
    HERE / "covers-samples",
    Path.home() / ".business/growth/seo",
]
COVER_HINTS = ("-og", "-hero", "-cover", "-illustration", "-photo", "-square")
SKIP_PARTS = ("thumb-", "/qa/", "/shots/", "/raw/", "/.proxy-cache/", "/masters/",
              "/thumbs-raw/", "/carddata/", "/demo/", "/terminal-outputs/",
              # скрины страниц и портреты - не обложки, в гейт не берём
              "/live-after/", "/shots-pre/", "/shots-el-live/", "/img-live/",
              "/preview/", "ivan-square", "_sravnenie", "/images-vc/",
              # по решению автора: скрины ЖИВЫХ страниц пролезали как обложки (совпал хинт
              # «-hero») и потом блокировали настоящие обложки. Это не картинки-обложки,
              # а снимки вёрстки: два снимка одной страницы в тёмной и светлой теме
              # неизбежно «клоны» друг друга и мусорят индекс
              "/shots-el-pre/", "/shots-live/", "/shots-el/", "/audit-img/",
              "/_deploy/", "/live/", "/screens/",
              "-1440-", "-390-", "-1440.", "-390.", "-hero-d.", "-hero-m.")
EXT = (".png", ".webp", ".jpg", ".jpeg")

# 🔴 Второй источник для --seed: манифест съёмки (по решению автора, закон доказательного кадра).
# Хинты выше опознают обложку по ИМЕНИ файла, а доказательные кадры зовутся по КОНТРАКТУ
# `<slug>-result-N` / `<slug>-step-N` - ни одного хинта в имени нет. Пересборка индекса
# собирает found с нуля и заканчивается write_index(), поэтому зарегистрированный
# `--register ... --role hero` кадр после --seed молча исчезал из индекса, и дыра
# параллельной публикации открывалась заново ровно для кадров нового мира.
# Манифест `shots-manifest.json` (пишет shot.py РЯДОМ со страницей, не в assets/) - это
# положительная улика происхождения кадра: берём ровно то, что снято, а не догадку по имени.
MANIFEST_NAME = "shots-manifest.json"

# Классы кадра по КОНТРАКТУ: result | step | own-run | inherited | sourced. В общий индекс
# берём ТОЛЬКО кандидатов в обложку - result, own-run и sourced. Требование уникальности канон
# предъявляет к hero и og (visual-layer.md, раздел про очередь), а шаговый кадр уникальным быть
# не обязан: два гайда законно снимают один и тот же экран регистрации. Пока step/inherited
# падали в индекс, чужой шаг становился законным источником вердикта «клон» и exit 4 для чужой
# обложки.
# по решению автора: sourced (чужой реальный кадр, взятый движком imgsrc.py) - ПОЛНОПРАВНЫЙ кандидат
# в обложку, поэтому в индекс он обязан идти. Без этой строки регистрация кадра класса sourced
# молча не делала бы НИЧЕГО: --register проходил бы с кодом 0, а в индексе записи не было бы,
# и два гайда законно уносили бы на прод один и тот же чужой кадр.
COVER_FRAME_CLASSES = ("result", "own-run", "sourced")


# ------------------------------------------------------------------ утилиты
def _np():
    import numpy as np
    return np


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_thumb(src: Path, dst: Path):
    from PIL import Image
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGB").resize(THUMB, Image.LANCZOS).save(dst, "PNG")


def load_thumb(p: Path):
    from PIL import Image
    np = _np()
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)


def znorm(a):
    """Нормировка по своему контрасту: убирает фору тёмного кадра.

    Корпус почти весь - тёмная тёплая студия. Там |Δ| между ЛЮБЫМИ двумя обложками мал
    просто потому, что оба кадра тёмные, и абсолютный порог `mean < 15` начинает ловить
    честно разные картинки. После вычитания своего среднего и деления на свою сигму
    расстояние мерится в единицах собственного контраста кадра.
    """
    np = _np()
    ax = (0, 1) if a.ndim == 3 else None
    return (a - a.mean(axis=ax)) / (a.std(axis=ax) + 1e-6)


def coarse_map(thumb_path: Path):
    """Грубая карта яркости: гаусс + BOX-даунсемпл до 64px, нормировка по контрасту.

    Типографика - высокая частота, на 64px она усредняется в фон. Остаются большие формы:
    силуэт предмета, раскладка панелей, направление света. Это и есть «сцена».
    """
    from PIL import Image, ImageFilter
    np = _np()
    im = Image.open(thumb_path).convert("L").filter(ImageFilter.GaussianBlur(COARSE_BLUR))
    h = max(2, round(COARSE_W * im.height / im.width))
    a = np.asarray(im.resize((COARSE_W, h), Image.BOX), dtype=np.float32)
    return znorm(a)


def feats(thumb_path: Path):
    """Признаки одной обложки: (rgb, znorm(rgb), грубая карта)."""
    a = load_thumb(thumb_path)
    return a, znorm(a), coarse_map(thumb_path)


def compare(fa, fb) -> tuple[float, float, float, float]:
    """(mean|Δ| 0-255, доля различающихся 0-1, znd, scene).

    Принимает либо тройки из feats(), либо (для совместимости со старым кодом) сырые
    массивы - тогда znd/scene считаются по тому, что есть.
    """
    np = _np()
    if isinstance(fa, tuple):
        ra, za, ca = fa
        rb, zb, cb = fb
    else:
        ra, rb = fa, fb
        za, zb = znorm(ra), znorm(rb)
        ca = cb = None
    d = np.abs(ra - rb)
    mean = float(d.mean())
    share = float((d.max(axis=2) > 16).mean())
    znd = float(np.abs(za - zb).mean())
    scene = float(np.abs(ca - cb).mean()) if ca is not None else znd
    return mean, share, znd, scene


def is_clone(mean: float, share: float, znd: float = 1.0, scene: float = 1.0) -> bool:
    """Клон = ТА ЖЕ КАРТИНКА. «Та же композиция при другом содержимом» клоном не считаем.

    Пороги калиброваны на размеченном наборе индекса (см. --selftest):
      8 настоящих клонов, 23 честно разные пары, ложных срабатываний 0.
    """
    if mean < CLONE_HARD:
        return True
    if share < SHARE_SAME and znd < ZND_SAME:
        return True
    if scene < SCENE_SAME:
        return True
    return False


def clone_reason(mean: float, share: float, znd: float, scene: float) -> str:
    if mean < CLONE_HARD:
        return "тот же кадр (пиксели)"
    if share < SHARE_SAME and znd < ZND_SAME:
        return "тот же кадр, различие только в надписи"
    if scene < SCENE_SAME:
        return "та же картинка (грубая карта сцены)"
    return "-"


def is_warn(mean: float, share: float, znd: float, scene: float) -> bool:
    """Семейное сходство: не блокирует, но стоит взглянуть глазами."""
    return (not is_clone(mean, share, znd, scene)
            and share < WARN_SHARE and scene < WARN_SCENE)


# ------------------------------------------------------------------ индекс
class Lock:
    """Межпроцессный лок на индекс: параллельные агенты пишут по очереди."""

    def __enter__(self):
        import fcntl
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.fh = open(LOCK, "a+")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        import fcntl
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def index_seen_covers() -> int:
    """Сколько обложек машина УЖЕ видела: число миниатюр в thumbs/ (по одной на запись).

    Это самый долгоживущий след наполненности индекса на диске: миниатюру пишет
    entry_for на каждую регистрацию, и её не удаляют ни --prune, ни --forget (они
    чистят записи). Поэтому число миниатюр отвечает на вопрос, которого не знает сам
    индекс: этот индекс МОЛОД (машина ученика, первые статьи) или УРЕЗАН (обложек
    были сотни, а в файле пусто).
    """
    if not THUMBS.is_dir():
        return 0
    return sum(1 for _ in THUMBS.glob("*.png"))


def read_index(allow_missing: bool = False, min_rows: int = 0) -> list[dict]:
    """Прочитать индекс уникальности.

    И1.8а: битый или подозрительно УРЕЗАННЫЙ индекс
    НИКОГДА не превращается в пустой список - гейту сравнивать не с чем, значит гейт
    не прошёл, а падает явным текстом, а не тихо решает «уникально» без единого
    реального сравнения.

    Порог min_rows судит ПАДЕНИЕ числа записей, а не молодость индекса: на машине,
    видевшей меньше min_rows обложек (index_seen_covers), маленький и даже пустой
    индекс законен - это бутстрап первой статьи, сравнивать пока не с чем.

    ОТСУТСТВУЮЩИЙ файл индекса судится тем же следом, что и урезанный: на чистой
    машине (миниатюр рядом меньше порога) это ровно тот же бутстрап - пустой список,
    первая же регистрация заведёт файл. Индекса нет, а миниатюр сотни - потеря
    данных, и гейт падает: сравнивать не с чем, значит гейт не прошёл.
    """
    if not INDEX.exists():
        if allow_missing:
            return []
        видано = index_seen_covers()
        if видано >= MIN_INDEX_ROWS:
            raise RuntimeError(
                f"индекс уникальности отсутствует: {INDEX}, а рядом лежат {видано} "
                f"миниатюр ранее зарегистрированных обложек - похоже на потерю "
                f"данных, гейт уникальности провести нечем; восстанови индекс из "
                f".bak рядом либо пересобери python3 uniq.py --seed"
            )
        return []      # чистая машина: индекса ещё не было, это бутстрап
    try:
        rows = json.loads(INDEX.read_text())
    except json.JSONDecodeError as ex:
        raise RuntimeError(
            f"индекс уникальности повреждён ({INDEX}): {ex} - "
            f"гейт уникальности провести нечем, восстанови из .bak рядом с индексом"
        ) from ex
    if min_rows and len(rows) < min_rows:
        видано = index_seen_covers()
        if видано >= min_rows:
            raise RuntimeError(
                f"индекс уникальности подозрительно мал: {len(rows)} записей < "
                f"{min_rows} ({INDEX}), а рядом лежат {видано} миниатюр ранее "
                f"зарегистрированных обложек - похоже на потерю данных, гейт "
                f"уникальности провести нечем"
            )
        # молодая машина: обложек в мире меньше порога, индекс просто ещё не набрался
    return rows


def write_index(rows: list[dict]):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    tmp.replace(INDEX)


def entry_for(path: Path, slug: str, role: str, status: str) -> dict:
    sid = sha1_file(path)
    thumb = THUMBS / f"{sid}.png"
    if not thumb.exists():
        make_thumb(path, thumb)
    return {"id": sid, "slug": slug, "slugs": [slug], "role": role, "status": status,
            "path": str(path), "ts": time.strftime("%Y-%m-%d %H:%M:%S")}


def slug_of(path: Path) -> str:
    """Слаг = имя папки статьи, если картинка лежит в assets/, иначе имя файла."""
    if path.parent.name == "assets":
        return path.parent.parent.name
    return path.stem


def skip_path(p) -> bool:
    s = str(p)
    return any(k in s for k in SKIP_PARTS)


def seed_roots() -> list[Path]:
    """Корни для --seed: постоянные каталоги + рабочий каталог статей из $WORK.

    Рабочий каталог переопределяем (config.md, `paths.work`), поэтому путь не зашит: если
    $WORK стоит и лежит вне уже перечисленных корней - добавляем его, иначе манифесты
    съёмки на такой машине никто не найдёт.
    """
    roots = [Path(r) for r in SEED_GLOBS]
    w = os.environ.get("WORK", "").strip()
    if not w:
        return roots
    p = Path(w).expanduser()
    if not p.is_dir():
        return roots
    p = p.resolve()
    for r in roots:
        try:
            rr = r.resolve()
        except OSError:
            continue
        if p == rr or rr in p.parents:
            return roots
    roots.append(p)
    return roots


def manifest_frames(root: Path) -> list[tuple[Path, str, str]]:
    """Кадры из манифестов съёмки под корнем: [(файл, слаг, класс)].

    Манифест лежит РЯДОМ со страницей (`$WORK/<slug>/shots-manifest.json`), пути внутри -
    относительно него (`assets/<имя>.webp`). Слаг берём из имени каталога манифеста: по
    КОНТРАКТУ это и есть <slug> статьи, а имя файла кадра его повторять не обязано.

    Класс отдаём как есть (нормализуем регистр и пробелы), фильтрует вызывающий: индексу
    уникальности нужны только кандидаты в обложку (COVER_FRAME_CLASSES), а другим читателям
    манифеста - весь список кадров.
    """
    out: list[tuple[Path, str, str]] = []
    for mp in root.rglob(MANIFEST_NAME):
        try:
            data = json.loads(mp.read_text())
        except (OSError, ValueError) as ex:      # битый манифест не валит весь seed
            print(f"  пропуск манифеста {mp}: {ex}", file=sys.stderr)
            continue
        frames = data.get("frames") if isinstance(data, dict) else None
        if not isinstance(frames, list):
            continue
        base = mp.parent
        for fr in frames:
            if not isinstance(fr, dict):
                continue
            rel = str(fr.get("file", "")).strip()
            if not rel:
                continue
            p = Path(rel)
            p = p if p.is_absolute() else base / p
            try:
                p = p.resolve()
            except OSError:
                continue
            if p.suffix.lower() not in EXT or not p.is_file() or skip_path(p):
                continue
            out.append((p, base.name, str(fr.get("class", "")).strip().lower()))
    return out


# ------------------------------------------------------------------ операции
def check(path: Path, slug: str, rows: list[dict] | None = None) -> list[tuple]:
    """Нарушения [(mean, share, znd, scene, entry)] против ВСЕГО индекса, кроме своего слага.

    Индекс общий на машину: в нём и опубликованный корпус, и всё, что другие агенты
    прямо сейчас держат в очереди на публикацию.
    """
    rows = read_index(min_rows=MIN_INDEX_ROWS) if rows is None else rows
    tmpdir = INDEX_DIR / "_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    mine_thumb = tmpdir / f"{os.getpid()}-{path.stem}.png"
    make_thumb(path, mine_thumb)
    mine = feats(mine_thumb)
    my_id = sha1_file(path)

    bad = []
    for r in rows:
        if slug in r.get("slugs", [r["slug"]]):
            continue
        if r["id"] == my_id:
            bad.append((0.0, 0.0, 0.0, 0.0, r))
            continue
        t = THUMBS / f"{r['id']}.png"
        if not t.exists():
            continue
        m, s, zn, sc = compare(mine, feats(t))
        if is_clone(m, s, zn, sc):
            bad.append((m, s, zn, sc, r))
    отложить(mine_thumb, ignore_errors=True)   # закон №0: не сносим, откладываем
    return bad


def warns(path: Path, slug: str, rows: list[dict] | None = None) -> list[tuple]:
    """Семейное сходство: не блокирует, печатается как совет посмотреть глазами."""
    rows = read_index(min_rows=MIN_INDEX_ROWS) if rows is None else rows
    tmpdir = INDEX_DIR / "_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    mine_thumb = tmpdir / f"w{os.getpid()}-{path.stem}.png"
    make_thumb(path, mine_thumb)
    mine = feats(mine_thumb)
    out = []
    for r in rows:
        if slug in r.get("slugs", [r["slug"]]):
            continue
        t = THUMBS / f"{r['id']}.png"
        if not t.exists():
            continue
        m, s, zn, sc = compare(mine, feats(t))
        if is_warn(m, s, zn, sc):
            out.append((m, s, zn, sc, r))
    отложить(mine_thumb, ignore_errors=True)   # закон №0: не сносим, откладываем
    return sorted(out, key=lambda x: x[3])[:5]


def register(path: Path, slug: str, role: str = "cover", status: str = "queued",
             strict: bool = True) -> list[tuple]:
    """Проверить и записать в общий индекс. strict=True -> при клоне НЕ записываем."""
    path = Path(path).resolve()
    with Lock():
        rows = read_index(min_rows=MIN_INDEX_ROWS)
        bad = check(path, slug, rows)
        if bad and strict:
            return bad
        e = entry_for(path, slug, role, status)
        rows = [r for r in rows if not (r["path"] == e["path"])]
        rows.append(e)
        write_index(rows)
    return bad


def publish(slug: str):
    with Lock():
        rows = read_index(min_rows=MIN_INDEX_ROWS)
        n = 0
        for r in rows:
            if slug in r.get("slugs", [r["slug"]]) and r["status"] != "published":
                r["status"] = "published"
                n += 1
        write_index(rows)
    return n


def prune() -> tuple[int, list[str]]:
    """Выкинуть мёртвые записи: файла нет / это скрин страницы, а не обложка.

    Зачем. Индекс собирался по хинтам в имени файла, и в него пролезли снимки ЖИВЫХ
    страниц (`shots-el-pre/vpn-hero-1440-dark.png`, `shots-live/*-hero-d.png`): в имени
    есть «-hero», а по сути это скриншот вёрстки. Дальше такая запись блокирует честные
    обложки, и её эталон никак не проверить глазами - страницы под этим слагом на проде
    нет вовсе. Мёртвые записи из индекса надо убирать, а не обходить.
    """
    removed = []
    with Lock():
        rows = read_index(min_rows=MIN_INDEX_ROWS)
        keep = []
        for r in rows:
            p = Path(r["path"])
            if not p.exists():
                removed.append(f"{r['slug']}: файла нет ({p})")
                continue
            if skip_path(p):
                removed.append(f"{r['slug']}: не обложка, а скрин/служебка ({p})")
                continue
            keep.append(r)
        write_index(keep)
    return len(keep), removed


def seed():
    found: list[Path] = []
    # слаг доказательного кадра приходит из манифеста, а не из имени файла
    from_manifest: dict[Path, str] = {}
    for root in seed_roots():
        root = Path(root)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() not in EXT or not p.is_file():
                continue
            if skip_path(p):
                continue
            if p.parent == root or any(h in p.stem for h in COVER_HINTS):
                if "-720" in p.stem:
                    continue
                found.append(p)
        # второй источник: кадры, зарегистрированные съёмкой (см. MANIFEST_NAME выше).
        # Имя `<slug>-result-N` хинтов не содержит, и без этого прохода --seed вычищал бы
        # из индекса уже зарегистрированный hero. Берём только кандидатов в обложку
        # (COVER_FRAME_CLASSES): шаговый и унаследованный кадр в индекс уникальности не идут
        for p, slug, klass in manifest_frames(root):
            if klass not in COVER_FRAME_CLASSES:
                continue
            from_manifest.setdefault(p, slug)
            found.append(p)
    found = sorted(set(found))

    with Lock():
        # --seed - единственный легитимный бутстрап: на первой сборке файла ещё нет.
        # Но битый (существующий, нечитаемый) индекс всё равно должен упасть - иначе
        # --seed молча перезапишет повреждённые данные пустотой и утащит их в write_index().
        prev = read_index(allow_missing=True)
        rows, seen = [], set()
        for p in sorted(found):
            try:
                sid = sha1_file(p)
            except OSError:
                continue
            if sid in seen:
                continue
            seen.add(sid)
            try:
                slug = from_manifest.get(p, slug_of(p))
                role = "frame" if p in from_manifest else "cover"
                rows.append(entry_for(p, slug, role, "corpus"))
            except Exception as ex:            # битый файл - не валим весь seed
                print(f"  пропуск {p}: {ex}", file=sys.stderr)

        # схлопываем ПЕРЕКОДИРОВКИ одной картинки (png/webp/jpg, копии по рабочим папкам):
        # это один визуал под разными слагами, гонять их друг против друга бессмысленно
        merged: list[dict] = []
        cache = {}
        for r in rows:
            t = THUMBS / f"{r['id']}.png"
            cache[r["id"]] = feats(t)
            hit = None
            for q in merged:
                m, _, _, _ = compare(cache[r["id"]], cache[q["id"]])
                if m < 2.5:
                    hit = q
                    break
            if hit:
                hit.setdefault("slugs", [hit["slug"]])
                if r["slug"] not in hit["slugs"]:
                    hit["slugs"].append(r["slug"])
            else:
                r["slugs"] = [r["slug"]]
                merged.append(r)

        # пересборка индекса НЕ должна терять слаги, которыми обложку зарегистрировал
        # генератор: рабочая копия в covers-photo/ и та же картинка в assets/ статьи -
        # один визуал одной статьи, иначе гейт ловит сам себя
        for old in prev:
            t = THUMBS / f"{old['id']}.png"
            if not t.exists():
                continue
            a = feats(t)
            for q in merged:
                m, _, _, _ = compare(a, cache[q["id"]])
                if m < 2.5:
                    for sl in old.get("slugs", [old["slug"]]):
                        if sl not in q["slugs"]:
                            q["slugs"].append(sl)
                    break
        write_index(merged)
    return len(merged)


def matrix(paths: list[Path]):
    tmpdir = INDEX_DIR / "_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    f = {}
    for p in paths:
        t = tmpdir / f"m-{sha1_file(p)}.png"
        if not t.exists():
            make_thumb(p, t)
        f[p] = feats(t)
    import itertools
    out = []
    for a, b in itertools.combinations(paths, 2):
        m, s, zn, sc = compare(f[a], f[b])
        out.append((m, s, zn, sc, a, b, is_clone(m, s, zn, sc)))
    return out


# --------------------------------------------------- реестр сцен (по построению)
def read_scenes() -> dict:
    """Реестр сцен. Отсутствие файла легитимно (сцен ещё никто не занимал) - {}.

    Битый JSON - тот же класс дефекта, что и read_index(): молчаливый {} даёт
    scene_claim() пустой реестр, и любой кортеж сцены «свободен» - гейт уникальности
    по построению перестаёт работать без единого предупреждения.
    """
    if not SCENES.exists():
        return {}
    try:
        return json.loads(SCENES.read_text())
    except json.JSONDecodeError as ex:
        raise RuntimeError(
            f"реестр сцен повреждён ({SCENES}): {ex} - "
            f"гейт уникальности по сценам провести нечем, восстанови из .bak"
        ) from ex


def scene_claim(sig: str, slug: str) -> str | None:
    """Занять кортеж осей сцены. Возвращает слаг-владельца, если кортеж уже занят.

    Точное сравнение строк, без картинок и без порогов: одна и та же композиция физически
    не может достаться двум статьям. Именно это, а не метрика похожести, даёт
    уникальность ПО ПОСТРОЕНИЮ.
    """
    with Lock():
        sc = read_scenes()
        owner = sc.get(sig)
        if owner and owner != slug:
            return owner
        sc[sig] = slug
        tmp = SCENES.with_suffix(".json.tmp")
        SCENES.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(sc, ensure_ascii=False, indent=1, sort_keys=True))
        tmp.replace(SCENES)
    return None


def forget(slug: str) -> tuple[int, int]:
    """Забыть слаг: убрать его обложки из индекса и его кортежи из реестра сцен.

    Зачем отдельная операция. Перерисовка обложки статьи - штатное дело (поправили пункты
    разбора, сменили число шагов). Без освобождения кортеж остаётся занят НАВСЕГДА за
    слагом, которому он больше не соответствует: реестр протекает, и на 380 сценах эта
    утечка съедает запас молча. Своя обложка своего же слага при этом клоном не считается,
    поэтому забывать нужно именно перед ПЕРЕсборкой, а не после.
    """
    with Lock():
        rows = read_index(min_rows=MIN_INDEX_ROWS)
        keep = [r for r in rows if slug not in r.get("slugs", [r["slug"]])]
        write_index(keep)
        sc = read_scenes()
        sigs = [k for k, v in sc.items() if v == slug]
        for k in sigs:
            del sc[k]
        if sigs:
            tmp = SCENES.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(sc, ensure_ascii=False, indent=1, sort_keys=True))
            tmp.replace(SCENES)
    return len(rows) - len(keep), len(sigs)


def scene_release(sig: str, slug: str) -> bool:
    """Освободить кортеж, если он занят ЭТИМ слагом.

    Нужно генератору: кортеж занимается ДО рендера, а собраться вёрстка может не с любым
    (замер вместимости делался на коротких подписях, у живой статьи они длиннее). Занял,
    не собралось - обязан вернуть кортеж в общий котёл, иначе каждая неудачная попытка
    навсегда выжигает одну сцену из 380.
    """
    with Lock():
        sc = read_scenes()
        if sc.get(sig) != slug:
            return False
        del sc[sig]
        tmp = SCENES.with_suffix(".json.tmp")
        SCENES.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(sc, ensure_ascii=False, indent=1, sort_keys=True))
        tmp.replace(SCENES)
    return True


def scene_taken(sig: str, slug: str) -> bool:
    owner = read_scenes().get(sig)
    return bool(owner) and owner != slug


# ------------------------------------------------------------------ печать
def fail_banner(path: Path, slug: str, bad: list[tuple]):
    print("\n" + "!" * 78)
    print("ГЕЙТ УНИКАЛЬНОСТИ: ОБЛОЖКА - КЛОН. ПУБЛИКАЦИЯ ЗАПРЕЩЕНА")
    print("!" * 78)
    print(f"  файл: {path}")
    print(f"  слаг: {slug}")
    for m, s, zn, sc, r in bad:
        print(f"  клон с [{r['status']}] {r['slug']}: {clone_reason(m, s, zn, sc)} · "
              f"mean|Δ| {m:.2f} · различается {s*100:.1f}% · znd {zn:.3f} · "
              f"сцена {sc:.3f} · {r['path']}")
    print("  Переделать СЦЕНУ, а не подпись. Фолбэк в другой генератор запрещён")
    print("!" * 78 + "\n")


def warn_banner(w: list[tuple]):
    if not w:
        return
    print("  ⚠️  семейное сходство (НЕ блокирует, глянуть глазами):")
    for m, s, zn, sc, r in w:
        print(f"     {r['slug']}: сцена {sc:.3f} · различается {s*100:.1f}% · {r['path']}")


# ------------------------------------------------------------------ selftest
# Размеченные глазами пары корпуса (контактный лист /tmp/corpus-all.png, по решению автора).
# Пары заданы слагами: если запись из индекса ушла, пара молча пропускается.
SELFTEST_CLONE = [
    ("pamyat", "pamyat-claude-og-photo"),
    ("guide-pamyat-hero-og-photo", "pamyat-claude-og-photo"),
    ("pamyat", "guide-pamyat-hero-og-photo"),
    ("pilot-guide-claude-code", "claude-vpn-bez-banov-hero"),
    ("claude-vpn-bez-banov", "claude-vpn-bez-banov__vpn-banov-hero"),
    ("guide-neyropoisk", "claude-vpn-bez-banov-hero"),
    ("pilot-guide-claude-code", "guide-neyropoisk"),
]
SELFTEST_DIFF = [
    ("audit-lupa-object", "kontekst-mozg-object"),
    ("audit-lupa-object", "klyuchi-api-object"),
    ("kontekst-mozg-object", "klyuchi-api-object"),
    ("vpn-bez-banov-object", "klyuchi-api-object"),
    ("guide-neyroset-pishet-kod", "neyroset-kod-lenta-og-photo"),
    ("seo-protiv-geo-abstract", "vpn-bez-banov-object"),
    ("rabochee-mesto-isometric", "pamyat-claude-stack"),
    ("guide-pamyat", "guide-pamyat-illustration"),
    ("claude-code-ustanovka-terminal", "pamyat-claude-stack"),
    ("claude-code", "guide-claude-code"),
    ("vpn-bez-banov-og-photo", "vpn-bez-banov-object"),
    ("seo-protiv-geo-og-photo", "seo-protiv-geo-abstract"),
    ("pamyat-claude-og-photo", "neyroset-kod-lenta-og-photo"),
    ("guide-neyropoisk", "guide-neyroset-pishet-kod"),
    ("rabochee-mesto-isometric", "claude-code-ustanovka-terminal"),
    ("vpn-banov-chast-1-hero-photo", "vpn-banov-chast-3-hero-photo"),
    ("guide-pamyat-illustration", "guide-neyropoisk-illustration"),
    ("ustanovka-claude", "guide-jarvis"),
    ("claude-code-ustanovka-og-photo", "guide-claude-code-ustanovka"),
    ("guide-besplatnye-zameny", "guide-vidrush"),
    ("guide-claude-code", "guide-claude-code-ustanovka"),
    ("guide-promt-eto", "guide-pamyat"),
    ("guide-promt-eto", "audit-lupa-object"),
]


def selftest_bootstrap() -> int:
    """Бутстрап и самооборона индекса на ВРЕМЕННОМ каталоге (живой не трогаем).

    Пять случаев, которые обязаны разойтись: чистой машины ДВА - индекса нет вовсе
    (файла не существует, миниатюр рядом нет) и индекс пустой ([] в файле); молодая
    машина (записей меньше порога, но столько же миниатюр - законно); и две потери
    данных - записей меньше порога при сотнях миниатюр и индекс ИСЧЕЗ при сотнях
    миниатюр (оба провал, И1.8а как была).
    """
    global INDEX_DIR, INDEX, THUMBS, SCENES, LOCK
    import tempfile
    сохранено = (INDEX_DIR, INDEX, THUMBS, SCENES, LOCK)
    ошибок = 0
    print("\n  БУТСТРАП индекса (временный каталог, живой индекс не трогаем)")

    def _строки(n):
        return json.dumps([{"id": f"id{i}", "slug": f"s{i}", "role": "hero",
                            "status": "queued", "path": f"/{i}.png"}
                           for i in range(n)])

    def _миниатюр(n):
        THUMBS.mkdir(parents=True, exist_ok=True)
        for f in THUMBS.glob("*.png"):
            отложить(f, ignore_errors=True)   # закон №0: не сносим, откладываем
        for i in range(n):
            (THUMBS / f"id{i}.png").write_bytes(b"")

    with tempfile.TemporaryDirectory() as td:
        INDEX_DIR = Path(td) / "cover-index"
        THUMBS, INDEX = INDEX_DIR / "thumbs", INDEX_DIR / "index.json"
        SCENES, LOCK = INDEX_DIR / "scenes.json", INDEX_DIR / ".lock"
        INDEX_DIR.mkdir(parents=True)
        try:
            # чистая машина в её РЕАЛЬНОМ состоянии: каталога индекса нет вовсе
            нет_файла = read_index(min_rows=MIN_INDEX_ROWS) == []

            INDEX.write_text("[]")
            чисто = read_index(min_rows=MIN_INDEX_ROWS) == []

            INDEX.write_text(_строки(3))
            _миниатюр(3)
            молодо = len(read_index(min_rows=MIN_INDEX_ROWS)) == 3

            _миниатюр(MIN_INDEX_ROWS + 5)
            try:
                read_index(min_rows=MIN_INDEX_ROWS)
                потеря = False
            except RuntimeError as ex:
                потеря = "потерю данных" in str(ex) and "миниатюр" in str(ex)

            # обратная сторона бутстрапа: индекс ИСЧЕЗ, а миниатюры остались -
            # это не молодая машина, а пропажа файла, и молчать о ней нельзя
            отложить(INDEX)   # закон №0: не сносим, откладываем
            try:
                read_index(min_rows=MIN_INDEX_ROWS)
                пропажа = False
            except RuntimeError as ex:
                пропажа = "отсутствует" in str(ex) and "потерю данных" in str(ex)
        finally:
            INDEX_DIR, INDEX, THUMBS, SCENES, LOCK = сохранено
    for good, текст in (
            (нет_файла, "чистая машина: файла индекса НЕТ вовсе и миниатюр рядом "
                        "нет - read_index отдаёт пустой список, первый --register "
                        "заводит индекс сам (не exit 5)"),
            (чисто, "чистая машина: индекс [] и ни одной миниатюры рядом - "
                    "read_index отдаёт пустой список, --register проходит"),
            (молодо, f"молодая машина: 3 записи при 3 миниатюрах - законно, порог "
                     f"{MIN_INDEX_ROWS} к ней не применяется"),
            (потеря, f"потеря данных: те же 3 записи, но рядом {MIN_INDEX_ROWS + 5} "
                     f"миниатюр - гейт падает (И1.8а жива)"),
            (пропажа, f"пропажа индекса: файла нет, а рядом {MIN_INDEX_ROWS + 5} "
                      f"миниатюр - это не молодая машина, гейт падает")):
        ошибок += (not good)
        print(f"    {'  ' if good else '✗ '}{текст}")
    return ошибок


def selftest():
    rows = read_index(min_rows=MIN_INDEX_ROWS)
    by = {}
    for r in rows:
        for s in r.get("slugs", [r["slug"]]):
            by.setdefault(s, r)
    cache = {}

    def F(r):
        if r["id"] not in cache:
            cache[r["id"]] = feats(THUMBS / f"{r['id']}.png")
        return cache[r["id"]]

    def run(pairs, want_clone):
        ok = miss = skip = 0
        det = []
        for a, b in pairs:
            ra, rb = by.get(a), by.get(b)
            if not ra or not rb or ra["id"] == rb["id"]:
                skip += 1
                continue
            m, s, zn, sc = compare(F(ra), F(rb))
            cl = is_clone(m, s, zn, sc)
            good = (cl == want_clone)
            ok += good
            miss += (not good)
            det.append((good, m, s, zn, sc, a, b))
        return ok, miss, skip, det

    print("ГЕЙТ УНИКАЛЬНОСТИ · SELFTEST порогов на размеченных парах индекса")
    print(f"пороги: mean<{CLONE_HARD} · share<{SHARE_SAME} и znd<{ZND_SAME} · "
          f"сцена<{SCENE_SAME}")
    tot_miss = 0
    for label, pairs, want in (("КЛОНЫ (обязан ловить)", SELFTEST_CLONE, True),
                               ("РАЗНЫЕ (обязан пропускать)", SELFTEST_DIFF, False)):
        ok, miss, skip, det = run(pairs, want)
        tot_miss += miss
        print(f"\n  {label}: верно {ok}, ошибок {miss}, нет в индексе {skip}")
        for good, m, s, zn, sc, a, b in sorted(det, key=lambda x: x[4]):
            mark = "  " if good else "✗ "
            print(f"    {mark}mean {m:7.2f} · разл {s*100:5.1f}% · znd {zn:.3f} · "
                  f"сцена {sc:.3f}   {a[:30]:30} vs {b[:30]}")
    tot_miss += selftest_bootstrap()
    print(f"\nИТОГ: ошибок {tot_miss}")
    return tot_miss


def main():
    ap = argparse.ArgumentParser(description="Гейт уникальности обложек (корпус + очередь)")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", default="")
    ap.add_argument("--register", default="")
    ap.add_argument("--publish", default="")
    ap.add_argument("--matrix", nargs="*", default=None)
    ap.add_argument("--scene-claim", default="", help="кортеж осей сцены (exit 4 = занят)")
    ap.add_argument("--scene-list", action="store_true")
    ap.add_argument("--forget", default="", help="слаг: снять его обложки и кортежи сцен")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--slug", default="")
    ap.add_argument("--role", default="cover")
    ap.add_argument("--status", default="queued", choices=["queued", "published", "corpus"])
    a = ap.parse_args()

    try:
        _dispatch(ap, a)
    except RuntimeError as ex:
        # И1.8а: битый/отсутствующий/урезанный индекс - явный текстовый провал гейта,
        # отдельный exit-код (5) от «клон найден» (4), чтобы вызывающий код не спутал
        # «гейт не смог проверить» с «гейт проверил и нашёл клон».
        print(f"гейт уникальности: НЕ ПРОВЕДЁН - {ex}", file=sys.stderr)
        sys.exit(5)


def _dispatch(ap: argparse.ArgumentParser, a: argparse.Namespace):
    if a.selftest:
        sys.exit(4 if selftest() else 0)
    if a.prune:
        n, removed = prune()
        for line in removed:
            print(f"  выкинуто · {line}")
        print(f"индекс после чистки: {n} обложек, убрано {len(removed)}")
        return
    if a.seed:
        print(f"индекс собран: {seed()} обложек · {INDEX}")
        return
    if a.forget:
        nimg, nsig = forget(a.forget)
        print(f"забыт слаг {a.forget}: обложек снято {nimg}, кортежей сцен освобождено {nsig}")
        return
    if a.scene_list:
        for sig, slug in sorted(read_scenes().items()):
            print(f"  {sig:52} -> {slug}")
        return
    if a.scene_claim:
        if not a.slug:
            ap.error("нужен --slug")
        owner = scene_claim(a.scene_claim, a.slug)
        if owner:
            print(f"КОРТЕЖ СЦЕНЫ ЗАНЯТ: {a.scene_claim} уже у слага {owner}")
            sys.exit(4)
        print(f"кортеж сцены занят за {a.slug}: {a.scene_claim}")
        return
    if a.list:
        for r in read_index(min_rows=MIN_INDEX_ROWS):
            print(f"  [{r['status']:9}] {r['slug']:38} {r['path']}")
        return
    if a.matrix is not None:
        ps = [Path(p).resolve() for p in a.matrix]
        print(f"{'mean|Δ|':>9} {'различ':>8} {'znd':>7} {'сцена':>7}  вердикт   пара")
        for m, s, zn, sc, x, y, cl in sorted(matrix(ps)):
            print(f"{m:9.2f} {s*100:7.1f}% {zn:7.3f} {sc:7.3f}  "
                  f"{'КЛОН  ' if cl else 'разные'}   {x.name}  vs  {y.name}")
        return

    target = a.check or a.register
    if a.publish:
        print(f"помечено published: {publish(a.publish)}")
        return
    if not target:
        ap.error("нужен --seed / --prune / --check / --register / --publish / --matrix / "
                 "--scene-claim / --scene-list / --forget / --selftest / --list")
    if not a.slug:
        ap.error("нужен --slug")

    p = Path(target).expanduser().resolve()
    if not p.exists():
        ap.error(f"нет файла: {p}")

    # бутстрап: индекс пуст ДО этой операции - значит гейт проходится по построению,
    # и сказать об этом надо прямым текстом, а не молчаливым «OK против 0 обложек».
    # Отдельно называется чистая машина: файла индекса не было вовсе, и он заводится
    # прямо этой командой (ученику важно видеть, что шаг не «прошёл вхолостую»)
    индекса_не_было = not INDEX.exists()
    бутстрап = not read_index(min_rows=MIN_INDEX_ROWS)

    if a.check:
        bad = check(p, a.slug)
    else:
        bad = register(p, a.slug, a.role, a.status)

    if bad:
        fail_banner(p, a.slug, bad)
        sys.exit(4)
    if бутстрап:
        print("бутстрап: "
              + ("индекса уникальности ещё не было (чистая машина, первая статья)"
                 if индекса_не_было else "индекс уникальности пуст")
              + " - сравнивать пока не с чем"
              + ("" if a.check else
                 ", обложка заведена первой записью"
                 + (f" · индекс создан: {INDEX}" if индекса_не_было else "")))
    print(f"гейт уникальности: OK · {p.name} против "
          f"{len(read_index(min_rows=MIN_INDEX_ROWS))} обложек индекса")
    warn_banner(warns(p, a.slug))


if __name__ == "__main__":
    main()
