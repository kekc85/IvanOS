#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""atomic_io.py - ОДИН атомарный писатель для разделяемых файлов контура SEO
(state.json, measures.json и всё, что читают несколько процессов сразу).

🔴 ЗАЧЕМ (В6, скептик-3 волны r5, по решению автора). Все четыре писателя state.json в
контуре писали файл ПРЯМО:

    json.dump(data, open(path, "w", encoding="utf-8"), ...)      # rost.py, spros.py, apply_patch.py
    path.write_text(json.dumps(data, ...), encoding="utf-8")     # demand_gate.save_state

`open(path, "w")` УСЕКАЕТ боевой файл ДО ТОГО, как в него что-то записано. Любой
обрыв между усечением и последним байтом (kill ночного агента, паника питона на
сериализации, полный диск, перезагрузка) оставляет на диске ПОЛОВИНУ state.json -
битый JSON, который дальше не читается НИКЕМ: ни добычей, ни модерацией, ни
rost.py. База очереди на 432 темы восстанавливается тогда только из бэкапа, а
бэкап у demand_gate снимается ОДИН РАЗ В ДЕНЬ (`if not bak.exists()`), то есть
может быть на десяток записей старше.

Закон теперь один: пишем во ВРЕМЕННЫЙ файл РЯДОМ (тот же каталог = та же
файловая система) и переносим на место `os.replace()` - атомарной операцией
POSIX. Читатель в любой момент видит либо старый файл целиком, либо новый
целиком; половины не существует. Обрыв на любом шаге до replace() оставляет
боевой файл НЕТРОНУТЫМ, а временный убирается сам.

Почему модуль лежит здесь, а не в scripts/seo/common.py: писатели живут в ДВУХ
деревьях (growth/seo и scripts/seo), а сам файл-данные (state.json) - в этом.
Модуль-помощник селится рядом с данными, которые защищает, и оба дерева тянут
его одним и тем же путём.
"""

import datetime
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
# ── УБОРКА БЕЗ СТИРАНИЯ (закон владельца 27.08.2026 «пусть лежит») ──────────
# Временный путь уезжает ПЕРЕИМЕНОВАНИЕМ в датированную папку рядом, а не
# стирается: страж no-entity-deletion-gate.sh читает тело запускаемого скрипта и
# валит прогон на любом вызове семейства стирания. Из-за этого канонический вход
# §4.4 («заводишь тему через moderate_queue.py, а не руками в state.json») был
# headless недоступен - дефект найден боевым прогоном исполнителя по решению автора.
_КОРЕНЬ_УБОРКИ = "~/.business/scripts/seo"
_КОРЕНЬ_УБОРКИ = os.path.expanduser(_КОРЕНЬ_УБОРКИ)
if _КОРЕНЬ_УБОРКИ not in sys.path:
    sys.path.insert(0, _КОРЕНЬ_УБОРКИ)
try:
    from uborka_bez_udaleniya import убрать as убрать_без_стирания  # noqa: E402
except ImportError:
    # R212: у ученика uborka_bez_udaleniya.py в пакете нет (он не шипится, живёт
    # только у автора). Честный фолбэк ТОГО ЖЕ закона «пусть лежит», не копия
    # регэкспов стража: временный файл уводится переименованием в датированную
    # папку рядом, а не удаляется. Сигнатура и поведение идентичны оригиналу.
    def убрать_без_стирания(путь, метка=None, корень_архива=None):  # noqa: E302
        import datetime as _dt
        if not путь or not os.path.exists(путь):
            return None
        метка = метка or _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        основа = корень_архива or os.path.dirname(путь) or "."
        круг = os.path.join(основа, "arhiv-temp", "krug-" + метка)
        os.makedirs(круг, exist_ok=True)
        имя = os.path.basename(путь)
        цель = os.path.join(круг, имя)
        i = 1
        while os.path.exists(цель):
            корень, расш = os.path.splitext(имя)
            цель = os.path.join(круг, "%s-%d%s" % (корень, i, расш))
            i += 1
        os.rename(путь, цель)
        return цель

__all__ = ["atomic_write_text", "atomic_write_json", "stamp_updated",
           "operation_name", "DEFAULT_MODE", "UPDATED_KEY"]

DEFAULT_MODE = 0o644     # права нового файла, если целевого ещё нет

# ─────────────────────────── АВТО-МЕТКА «обновлено» (М-2, скептик-4, по решению автора)
#
# Что было сломано. У state.json есть поле «обновлено» - человеческая отметка
# «когда база последний раз двигалась». Двигали её ВРУЧНУЮ и только некоторые
# писатели: collect_queries и moderate_queue ставили дату сами, а rost.py
# («взять/этап/готово/отложить») и spros.py писали файл молча. В итоге метка
# показывала 2026-08-10, когда база менялась 12-го по десять раз за день, и
# читать её было нельзя ни человеку, ни коду: «свежая» она или нет - неизвестно.
#
# Класс лечится там же, где лечится атомарность: в ЕДИНСТВЕННОМ писателе. Любой
# путь записи проходит через atomic_write_json, значит метку двигает он - и
# забыть её нельзя, потому что забывать нечего.
#
# Правило намеренно узкое, чтобы не портить чужие данные:
#   * поля «обновлено» в словаре нет  -> не добавляем (measures.json его не носит);
#   * значение уже начинается с СЕГОДНЯШНЕЙ даты -> не трогаем (писатель поставил
#     свою, более содержательную формулировку - она информативнее нашей);
# * иначе -> «по решению автора (<операция>)», формат совпадает с тем, что писали руками.
# Имя операции: SEO_OP из окружения, иначе выводится из командной строки
# процесса (rost.py готово / spros.py --recalc) - по метке видно, КТО двигал.
UPDATED_KEY = "обновлено"


def _target_mode(path: Path) -> int:
    """Права боевого файла, чтобы замена их не сбрасывала.

    tempfile.mkstemp() создаёт файл с 0600 - если просто перенести его на место
    state.json, файл станет доступен только владельцу. Здесь это не дыра, но
    молчаливая смена прав на разделяемом файле - именно тот класс сюрприза,
    который потом ищут часами. Забираем режим у существующего файла."""
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return DEFAULT_MODE


def atomic_write_text(path, text: str, encoding: str = "utf-8") -> Path:
    """Атомарно записать текст: временный файл рядом -> fsync -> os.replace.

    Возвращает Path записанного файла. Бросает наружу ЛЮБУЮ ошибку записи,
    предварительно убрав временный файл: молча проглоченный сбой записи хуже
    самого сбоя - вызывающий будет считать, что данные на диске."""
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    mode = _target_mode(path)
    fd, tmp = tempfile.mkstemp(dir=str(parent), prefix=path.name + ".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())          # данные на диске ДО подмены имени
        os.chmod(tmp, mode)
        os.replace(tmp, path)             # атомарная подмена в пределах ФС
        tmp = None
        return path
    finally:
        if tmp is not None and os.path.exists(tmp):
            try:
                убрать_без_стирания(tmp)
            except OSError:
                pass


def operation_name() -> str:
    """Короткое имя операции для метки: «rost.py готово», «spros.py --recalc».

    Из окружения SEO_OP (если волна назвала себя явно), иначе из командной строки
    процесса. Ставим имя ИНСТРУМЕНТА С ПОДКОМАНДОЙ, а не PID и не путь: метку
    читает человек, и ему нужно «кто двигал», а не «каким процессом»."""
    явно = (os.environ.get("SEO_OP") or "").strip()
    if явно:
        return явно[:80]
    argv = list(sys.argv or [])
    tool = os.path.basename(argv[0]) if argv else ""
    # «-», «-c», пустая строка = питон, запущенный из stdin/инлайном: имя файла в
    # argv[0] отсутствует, и подпись «-» в метке не сказала бы ничего никому.
    if tool in ("", "-", "-c", "python3", "python"):
        tool = "python-инлайн"
    хвост = [a for a in argv[1:] if not a.startswith("/")][:2]
    return (" ".join([tool] + хвост))[:80]


def stamp_updated(data, op=None, today=None):
    """Проставить метку «обновлено» В КОПИИ данных. -> (данные, что_поставили|None).

    Копия, а не мутация на месте: писатель мог передать словарь, который дальше
    сам же читает - тихая правка его памяти была бы сюрпризом. Возвращаем и
    ЧТО поставили, чтобы вызывающий мог это напечатать/залогировать."""
    if not isinstance(data, dict) or UPDATED_KEY not in data:
        return data, None
    today = today or datetime.date.today().isoformat()
    было = data.get(UPDATED_KEY)
    if isinstance(было, str) and было.startswith(today):
        return data, None          # писатель уже поставил свою, более подробную
    метка = f"{today} ({op or operation_name()})"
    новые = dict(data)
    новые[UPDATED_KEY] = метка
    return новые, метка


def atomic_write_json(path, data, *, indent: int = 2, ensure_ascii: bool = False,
                      trailing_newline: bool = True, encoding: str = "utf-8",
                      stamp: bool = True, op=None) -> Path:
    """Атомарно записать JSON. СНАЧАЛА сериализуем в память, потом пишем:
    падение сериализации (несериализуемый объект в данных) не должно оставлять
    на диске ни временного огрызка, ни тем более тронутого боевого файла.

    stamp=True (по умолчанию) двигает метку «обновлено», если она в данных есть -
    см. блок про М-2 в шапке. stamp=False - для случаев, когда пишется чужой
    снимок как есть (бэкап, миграция) и метку двигать НЕЛЬЗЯ: это была бы подделка
    даты чужой записи."""
    if stamp:
        data, _метка = stamp_updated(data, op=op)
    text = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
    if trailing_newline:
        text += "\n"
    return atomic_write_text(path, text, encoding=encoding)


# ───────────────────────────────────────────────────────────────── селфтест
def _selftest():
    import tempfile as _tf
    ok = [0]
    fails = []

    def check(name, cond, detail=""):
        if cond:
            ok[0] += 1
            print(f"  ok   {name}")
        else:
            fails.append(name)
            print(f"  FAIL {name}" + (f" ({detail})" if detail else ""))

    сегодня = datetime.date.today().isoformat()
    with _tf.TemporaryDirectory(prefix="atomic-io-selftest-") as tmp:
        p = os.path.join(tmp, "state.json")

        # ПОЗИТИВ: метка есть в данных и протухла -> двигается
        d, м = stamp_updated({"обновлено": "2026-08-10 (brand-safety скан)", "темы": [1]},
                             op="rost.py готово")
        check("ПОЗИТИВ: протухшая метка «обновлено» двигается на сегодня с именем операции",
              d["обновлено"] == f"{сегодня} (rost.py готово)" and м == d["обновлено"], d)
        check("ПОЗИТИВ: остальные поля не тронуты", d["темы"] == [1], d)

        # НЕГАТИВ: поля нет - НЕ добавляем (measures.json его не носит)
        d2, м2 = stamp_updated({"ряды": {}}, op="zamery")
        check("НЕГАТИВ: поля «обновлено» в данных нет - оно НЕ дописывается",
              "обновлено" not in d2 and м2 is None, d2)

        # НЕГАТИВ: писатель уже поставил СВОЮ метку сегодня - не перебиваем
        своя = f"{сегодня} (модерация: +7 кандидатов в очередь)"
        d3, м3 = stamp_updated({"обновлено": своя}, op="rost.py")
        check("НЕГАТИВ: своя сегодняшняя метка писателя НЕ перебивается нашей "
              "(она содержательнее)", d3["обновлено"] == своя and м3 is None, d3)

        # НЕГАТИВ: не мутируем исходные данные
        исход = {"обновлено": "2026-01-01", "x": 1}
        stamp_updated(исход, op="t")
        check("НЕГАТИВ: исходный словарь вызывающего НЕ мутируется",
              исход["обновлено"] == "2026-01-01", исход)

        # имя операции: явное SEO_OP сильнее выведенного, инлайн-питон не подписывается «-»
        было_op = os.environ.pop("SEO_OP", None)
        argv_было = list(sys.argv)
        try:
            sys.argv = ["-"]
            check("НЕГАТИВ: инлайн-питон (argv «-») не подписывается прочерком",
                  operation_name() == "python-инлайн", operation_name())
            sys.argv = ["/path/to/rost.py", "готово", "/abs/path"]
            check("ПОЗИТИВ: имя операции = инструмент + подкоманда, без путей",
                  operation_name() == "rost.py готово", operation_name())
            os.environ["SEO_OP"] = "волна r6 ретайтл"
            check("ПОЗИТИВ: SEO_OP из окружения сильнее выведенного из argv",
                  operation_name() == "волна r6 ретайтл", operation_name())
        finally:
            sys.argv = argv_было
            os.environ.pop("SEO_OP", None)
            if было_op is not None:
                os.environ["SEO_OP"] = было_op

        # СВЯЗКА: боевой путь записи двигает метку сам
        atomic_write_json(p, {"обновлено": "2026-08-10 (старое)", "темы": []},
                          indent=1, op="rost.py готово")
        на_диске = json.load(open(p, encoding="utf-8"))
        check("СВЯЗКА: atomic_write_json двигает метку САМ - забыть её нельзя",
              на_диске["обновлено"] == f"{сегодня} (rost.py готово)", на_диске)

        # СВЯЗКА: stamp=False - чужой снимок пишется как есть (бэкап не подделывается)
        atomic_write_json(p, {"обновлено": "2026-08-10 (старое)", "темы": []},
                          indent=1, stamp=False)
        снимок = json.load(open(p, encoding="utf-8"))
        check("СВЯЗКА: stamp=False пишет чужой снимок как есть (дата бэкапа не подделана)",
              снимок["обновлено"] == "2026-08-10 (старое)", снимок)

        # атомарность и права - прежний контракт не сломан
        os.chmod(p, 0o600)
        atomic_write_json(p, {"обновлено": "2026-08-10", "темы": [1, 2]}, indent=1)
        check("режим боевого файла переживает замену (0600 остался 0600)",
              stat.S_IMODE(os.stat(p).st_mode) == 0o600,
              oct(stat.S_IMODE(os.stat(p).st_mode)))
        check("временных огрызков .tmp-*.part рядом не осталось",
              not [f for f in os.listdir(tmp) if ".tmp-" in f], os.listdir(tmp))
        try:
            atomic_write_json(p, {"обновлено": "2026-08-10", "плохое": object()})
            check("НЕГАТИВ: несериализуемые данные отбиты ДО записи", False, "не упало")
        except TypeError:
            цел = json.load(open(p, encoding="utf-8"))
            check("НЕГАТИВ: падение сериализации не тронуло боевой файл и не "
                  "оставило огрызка",
                  цел["темы"] == [1, 2]
                  and not [f for f in os.listdir(tmp) if ".tmp-" in f], цел)

    print(f"\natomic_io селфтест: {ok[0]} ok, провалов {len(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        sys.exit(_selftest())
    ap.print_help()
