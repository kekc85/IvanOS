#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demand_gate.py - гейт спроса E для контура очереди state.json (И5.1, по решению автора)

Зачем. Старый гейт "спрос >= 300" был экономически сломан: тема на 300 запросов/мес
даёт ~0,1 клика/день - конвейер тратил полный цикл статьи на тему, которая никогда
не окупится. Новый гейт считает ОЖИДАЕМЫЕ КЛИКИ, а не сырой спрос.

🔴 ДВЕ РАЗНЫЕ ВЕЛИЧИНЫ (С.3б движка 5.0, по решению автора). До этой правки одно число
E выдавалось И за ранговый балл, И за "ожидаемые клики/мес" - и во втором
качестве врало в 16 раз (проверено живьём, расчёт ниже). Теперь величины
разведены и НИКОГДА не подменяют друг друга:

  E_ранг    = спрос / RANK_DIVISOR (105) с коэффициентом информационности.
              ЭТО БАЛЛ СРАВНЕНИЯ ТЕМ, НЕ КЛИКИ. На нём живут гейт (HARD_E),
              приоритет (PRIORITY_E) и вся сортировка очереди. Шкала и пороги
              откалиброваны друг под друга с этой редакции - трогать делитель здесь
              значит обнулить смысл порогов на всей накопленной базе.
  E_прогноз = спрос / FACT_DIVISOR (1700) с тем же коэффициентом, а для тем,
              добытых из показов Вебмастера, напрямую показы_31д × CTR_ФАКТ.
              ЭТО ОЖИДАЕМЫЕ КЛИКИ В МЕСЯЦ. Только на нём разрешены любые
              экономические формулировки ("ожидаемые клики", "окупится").

Гейт и сортировка - E_ранг. Деньги и окупаемость - E_прогноз. Смешивать нельзя.

Правила:
  HARD   - тема с E < 10 не берётся в работу без --force (спрос примерно от 1000
           и выше даёт HARD-пропуск, но порог формально считается по E, не по
           спросу - при спросе ровно 1000 E = 9.52 и гейт ещё не пропускает,
           реальная граница E>=10 начинается со спроса 1050).
  ПРИОРИТЕТ - E >= 50 после применения коэффициента - в начало очереди.
  КОЭФФИЦИЕНТ 0.5 - применяется к E, если тема ЧИСТО информационная (лид
           "что такое / как работает / почему / зачем ..." БЕЗ инструментального
           хвоста рядом). Причина - Алиса и нейро-ответы Яндекса съедают 30-60%
           кликов у чисто информационных запросов (разведка Р.5/ГР.5, по решению автора),
           инструментальные и сравнительные запросы этим не облагаются.

Использование:
    python3 demand_gate.py --selftest
    python3 demand_gate.py --check "что такое нейросеть" --spros 6000
    python3 demand_gate.py --audit                    # весь statuse=='очередь' state.json
    python3 demand_gate.py --audit --status резерв
    python3 demand_gate.py --take-next                 # верхняя тема, прошедшая HARD-гейт
    python3 demand_gate.py --take-next --commit         # + пишет статус "в работе" в state.json
    python3 demand_gate.py --recalc                    # пересчёт полей E_ранг/E_прогноз по всей базе
    python3 demand_gate.py --recalc --commit            # + запись в state.json (нужен claim волны)
"""

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "state.json"

# общий атомарный писатель разделяемых файлов контура (В6). Импорт по пути
# модуля, а не по текущему каталогу: demand_gate зовут и как модуль, и из
# соседнего дерева scripts/seo
sys.path.insert(0, str(HERE))
import atomic_io  # noqa: E402

RANK_DIVISOR = 105.0      # спрос -> РАНГОВЫЙ БАЛЛ E_ранг (шкала И5.0, не клики)
DIVISOR = RANK_DIVISOR     # исторический псевдоним: старое имя = ранговый делитель
HARD_E = 10.0             # HARD-порог по E_ранг: ниже - тема не идёт в работу без --force
PRIORITY_E = 50.0         # порог приоритета по E_ранг (в начало очереди)
INFO_COEF = 0.5           # понижающий коэффициент чисто информационным запросам

# ---- МЕТОДИКА FACT_DIVISOR и CTR_ФАКТ (калибровка по решению автора, движок 5.0) ----
# Проблема, которую эта константа закрывает. Поле "ожидаемые клики" считалось
# тем же делителем 105, что и ранговый балл. Живая проверка по 158 темам,
# добытым из показов Вебмастера (у каждой в state.json лежат СВОИ показы_31д и
# клики_31д, то есть факт, а не модель):
#     сумма показы_31д  = 5573      сумма клики_31д = 184     CTR = 3.30%
#     старая формула предсказывала по этим же темам 2972 клика/мес
#     завышение = 2972 / 184 = 16.2x
# Откуда 1700. Три независимых счёта сходятся в одну точку:
#   (1) через показы: FACT_DIVISOR = K / CTR_ФАКТ = 56 / 0.0330 = 1697
#   (2) через замеренные темы: 52 темы с ЗАМЕРЕННЫМ Wordstat-спросом сведены с
#       собственными показами (лемма-containment по webmaster-queries-2026-08-09
#       .csv); у 13 из них есть ненулевые клики -> спрос/клики: медиана 1217,
#       p25 280, p75 1937, агрегат 2363. 1700 лежит внутри полосы
#   (3) от обратного: 105 × 16.2 (замеренное завышение) = 1701
# Контрольная точка на единственной ЗРЕЛОЙ странице корпуса: "claude code",
# спрос 65851 -> прогноз 65851/1700 = 38.7 клика/мес; факт Вебмастера за 31
# день = 34 клика. Расхождение 14%, это лучшая доступная проверка формулы.
# Пересчитывается командой (не руками): collect_queries.py --kalibrovka
FACT_DIVISOR = 1700.0     # спрос (Wordstat) -> ОЖИДАЕМЫЕ КЛИКИ/МЕС, зрелая страница
CTR_ФАКТ = 0.033          # клики/показ по 158 живым темам (184/5573), 31 день

# лид чисто информационного запроса
INFO_LEAD_RE = re.compile(
    r"\b(что такое|что это такое|что это|как работает|как устроен[ыоа]?|"
    r"почему|зачем|кто такой|кто такая|когда появил|история)\b",
    re.IGNORECASE,
)

# инструментальный/сравнительный хвост - если он есть рядом, коэффициент НЕ применяется
# (человек хочет действие или сравнение, а не справку - нейро-ответ такой клик не съедает)
INSTRUMENTAL_RE = re.compile(
    r"\b(как сделать|как настроить|как установить|как пользоваться|как использовать|"
    r"как создать|как подключить|как запустить|как написать|как выбрать|как получить|"
    r"как купить|как заработать|инструкция|пошагов|сравнени|\bvs\b|цена|стоимост|"
    r"купить|тариф|рейтинг|лучш|топ[- ]|обзор|отзыв|скачать|установка|настройка|"
    r"таблиц)\b",
    re.IGNORECASE,
)


def demand_e(спрос):
    """Сырой РАНГОВЫЙ балл без коэффициента. None/отсутствующий спрос = 0
    (не проходит). Это НЕ клики - см. шапку файла."""
    if спрос is None:
        return 0.0
    return спрос / RANK_DIVISOR


def forecast_clicks(тема_обj: dict, coef: float = 1.0) -> tuple:
    """ОЖИДАЕМЫЕ КЛИКИ В МЕСЯЦ (E_прогноз) и на чём они посчитаны.

    Две ветки по источнику спроса, потому что источники разной природы:
      * "показы-вебмастера" - у темы есть СВОИ показы_31д, факт нашей выдачи.
        Считаем напрямую показы × CTR_ФАКТ, без промежуточного перевода в
        спрос-эквивалент: меньше звеньев - меньше накопленной ошибки.
      * всё остальное (замер Wordstat) - спрос / FACT_DIVISOR.
    Обе ветки численно согласованы: спрос_экв = показы × K(56), а 56/1700 =
    0.0329 ≈ CTR_ФАКТ 0.033, то есть ветки дают одно и то же число, просто
    первая берёт факт там, где он есть.

    Возвращает (клики_в_месяц, основание_строкой)."""
    if (тема_обj.get("спрос_источник") == "показы-вебмастера"
            and тема_обj.get("показы_31д")):
        pok = float(тема_обj["показы_31д"])
        return round(pok * CTR_ФАКТ * coef, 2), f"показы_31д {pok:g} × CTR {CTR_ФАКТ:g}"
    спрос = тема_обj.get("спрос")
    if спрос is None:
        return 0.0, "нет спроса"
    return round(спрос / FACT_DIVISOR * coef, 2), f"спрос {спрос} / {FACT_DIVISOR:g}"


def is_informational(тема_текст: str) -> bool:
    """Чисто информационный запрос: есть информационный лид И нет инструментального
    хвоста рядом. «Как настроить нейросеть» - НЕ информационный (хвост есть).
    «Что такое нейросеть» - информационный."""
    t = (тема_текст or "").lower()
    if not INFO_LEAD_RE.search(t):
        return False
    if INSTRUMENTAL_RE.search(t):
        return False
    return True


def evaluate(тема_обj: dict) -> dict:
    """Полный вердикт гейта для одной темы (словарь из state.json или ad hoc).

    Ключи результата:
      e_rank / e_eff  - РАНГОВЫЙ балл (e_eff оставлен как исторический
                        псевдоним: на него смотрят collect_queries.py и все
                        отчёты, написанные до разведения величин по решению автора)
      hard_pass / priority - гейт и приоритет, СЧИТАЮТСЯ ТОЛЬКО ПО e_rank
      e_forecast      - ожидаемые клики/мес, единственное поле, на котором
                        разрешены экономические формулировки
      forecast_basis  - на чём посчитан прогноз (показы или спрос)
    """
    спрос = тема_обj.get("спрос")
    тема_текст = тема_обj.get("тема", "")
    informational = is_informational(тема_текст)
    coef = INFO_COEF if informational else 1.0
    e_raw = demand_e(спрос)
    e_rank = round(e_raw * coef, 3)
    e_forecast, basis = forecast_clicks(тема_обj, coef)
    источник = тема_обj.get("спрос_источник") or "замер-wordstat"
    hard = e_rank >= HARD_E
    # 🔴 HARD-ПРОХОД НА ОЦЕНКЕ ВИДЕН ОТДЕЛЬНЫМ ПОЛЕМ (класс-фикс по решению автора,
    # дефект F2 круга 1 конвейера). Спрос из показов Вебмастера - это ОЦЕНКА:
    # показы × K=56. Ранговый балл считает её наравне с живым замером Wordstat,
    # и ровно здесь заход поймал живой прецедент. Тема «ltx studio текст в видео»
    # несла спрос-эквивалент 16 184 (289 показов × 56), дала E_ранг 154.1 и ушла
    # в производство пятой статьёй транша. Живой замер Wordstat по решению автора
    # (регион 225, окно 29.в даты запуска) дал по ней 752 запроса в месяц, то есть
    # E_ранг 7.16: тема HARD-гейт НЕ проходит и в работу идти не должна была.
    # Ошибка оценки 21.5 раза. Примечание записи просило «перезамерить живым
    # Wordstat», но просьба была ТЕКСТОМ, а не барьером, и её никто не исполнил.
    # Теперь это поле результата и отдельный код возврата под --require-zamer
    hard_на_оценке = bool(hard and источник == "показы-вебмастера")
    return {
        "тема": тема_текст,
        "кластер": тема_обj.get("кластер", ""),
        "спрос": спрос,
        "спрос_источник": источник,
        "e_raw": round(e_raw, 3),
        "informational": informational,
        "coef": coef,
        "e_rank": e_rank,
        "e_eff": e_rank,          # исторический псевдоним, см. docstring
        "e_forecast": e_forecast,
        "forecast_basis": basis,
        "hard_pass": hard,
        "hard_pass_на_оценке": hard_на_оценке,
        "priority": e_rank >= PRIORITY_E,
    }


def load_state(path=STATE_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_state(data, path=STATE_FILE):
    """Пишет state.json АТОМАРНО с бэкапом рядом (*.bak-demand-gate-по решению автора), не тихо.

    В6 (скептик-3, по решению автора): было `path.write_text(...)` - усечение боевого
    файла до записи, обрыв посередине = битый JSON на диске у ВСЕГО контура.
    Теперь запись идёт через общий helper atomic_io (временный файл рядом +
    os.replace), тот же самый, что у rost.py, spros.py и apply_patch.py -
    один класс, один код, а не заплатка в одной ветке."""
    path = Path(path)
    bak = path.with_name(path.name + f".bak-demand-gate-{date.today().isoformat()}")
    if not bak.exists() and path.exists():
        shutil.copy2(path, bak)
    atomic_io.atomic_write_json(path, data, indent=2, ensure_ascii=False)
    return bak


# ---- CLI-режимы ----

def cmd_check(args):
    v = evaluate({"тема": args.check, "спрос": args.spros, "кластер": "",
                  "спрос_источник": args.istochnik})
    print(json.dumps(v, ensure_ascii=False, indent=2))
    print(f"\nвердикт: {'ПРОХОДИТ HARD' if v['hard_pass'] else 'НЕ ПРОХОДИТ HARD (E_ранг<10)'}"
          f"{' · ПРИОРИТЕТ' if v['priority'] else ''}")
    print(f"  E_ранг = {v['e_rank']} (балл сравнения тем, НЕ клики) - на нём гейт и сортировка")
    print(f"  E_прогноз = {v['e_forecast']} клика/мес ожидаемых ({v['forecast_basis']})")
    if v["e_forecast"] < 1:
        print("  ⚠ экономика: меньше одного клика в месяц - статья под эту тему "
              "не отобьёт цикл производства")
    if v["hard_pass_на_оценке"]:
        print("  🔴 HARD пройден на ОЦЕНКЕ спроса (показы Вебмастера × K=56), а не на "
              "живом замере Wordstat. Перед производством тему обязан перезамерить "
              "живой Wordstat: прецедент по решению автора - оценка 16 184 против замера 752, "
              "ошибка 21.5 раза, тема на замере гейт НЕ проходит")
        if args.require_zamer:
            sys.exit(2)
    sys.exit(0 if v["hard_pass"] or args.force else 1)


def cmd_audit(args):
    data = load_state(args.state)
    темы = [t for t in data["темы"] if t.get("статус") == args.status]
    results = [evaluate(t) for t in темы]
    results.sort(key=lambda r: r["e_eff"], reverse=True)
    passed = [r for r in results if r["hard_pass"]]
    failed = [r for r in results if not r["hard_pass"]]
    priority = [r for r in results if r["priority"]]
    informational = [r for r in results if r["informational"]]
    print(f"Аудит гейта спроса · state={args.state} · статус='{args.status}'")
    print(f"  тем в срезе: {len(results)}")
    print(f"  проходят HARD (E_ранг>=10): {len(passed)}")
    print(f"  НЕ проходят HARD: {len(failed)}")
    print(f"  из них приоритет (E_ранг>=50): {len(priority)}")
    print(f"  чисто информационных (коэффициент 0.5 применён): {len(informational)}")
    forecast_sum = round(sum(r["e_forecast"] for r in passed), 1)
    under_one = [r for r in passed if r["e_forecast"] < 1]
    print(f"  ЭКОНОМИКА среза (только E_прогноз): {forecast_sum} ожидаемых кликов/мес "
          f"суммарно по прошедшим гейт")
    print(f"    из них тем с прогнозом меньше 1 клика/мес: {len(under_one)}")
    if args.verbose:
        print("\n  топ прошедших:")
        for r in passed[: args.top]:
            flag = " ★приоритет" if r["priority"] else ""
            info = " [инфо x0.5]" if r["informational"] else ""
            print(f"    E_ранг={r['e_rank']:>7.2f}  E_прогноз={r['e_forecast']:>6.2f} кл/мес  "
                  f"спрос={r['спрос']:<7}  {r['тема']}{info}{flag}")
        if failed:
            print("\n  не прошли (топ по спросу):")
            for r in sorted(failed, key=lambda r: r["спрос"] or 0, reverse=True)[: args.top]:
                print(f"    E_ранг={r['e_rank']:>7.2f}  E_прогноз={r['e_forecast']:>6.2f} кл/мес  "
                      f"спрос={r['спрос']:<7}  {r['тема']}")
    return results


def cmd_take_next(args):
    """ЕДИНСТВЕННАЯ точка входа темы в производство.

    DEFAULT-HOLD (по решению автора). Берётся ТОЛЬКО статус 'очередь'. Свежедобытая
    тема лежит в статусе 'кандидат' и сюда не попадает ни при каких условиях,
    пока её не переведёт moderate_queue.py (регулярный brand-safety + LLM-судья).
    Это второй эшелон защиты: первый - регулярки brand_unsafe(), они закрывают
    ИЗВЕСТНЫЕ классы; кандидатский холд закрывает НЕИЗВЕСТНЫЕ - те, для которых
    правила ещё не написано (скептик-A принёс восемь таких за один заход).
    """
    data = load_state(args.state)
    темы = data["темы"]
    candidates = [t for t in темы if t.get("статус") == "очередь"]
    на_модерации = [t for t in темы if t.get("статус") == "кандидат"]
    scored = sorted(
        ((evaluate(t), t) for t in candidates),
        key=lambda pair: pair[0]["e_eff"],
        reverse=True,
    )
    passing = [(v, t) for v, t in scored if v["hard_pass"]]
    if not passing:
        print("Очередь пуста ИЛИ ни одна тема не проходит HARD-гейт E>=10.")
        if на_модерации:
            print(f"🔒 При этом в статусе 'кандидат' лежит {len(на_модерации)} тем - "
                  f"они НЕ считаются очередью и в работу не берутся.")
            print("   Сначала модерация: python3 moderate_queue.py --scan -> --commit")
        print("Это триггер контура добычи (--dobycha в collect_queries.py) - запас исчерпан.")
        sys.exit(1)
    v, t = passing[0]
    flag = " ★приоритет" if v["priority"] else ""
    info = " [инфо x0.5]" if v["informational"] else ""
    print(f"Следующая тема в работу: «{v['тема']}» (кластер: {v['кластер']})")
    print(f"  спрос={v['спрос']}  E_ранг={v['e_rank']}{info}{flag}")
    print(f"  E_прогноз={v['e_forecast']} ожидаемых кликов/мес ({v['forecast_basis']})")
    if v["e_forecast"] < 1:
        print("  ⚠ экономика: прогноз меньше клика в месяц - тема проходит ранговый "
              "гейт, но цикл производства не окупает")
    if args.commit:
        t["статус"] = "в работе"
        bak = save_state(data, args.state)
        print(f"  статус -> 'в работе' записан, бэкап: {bak.name}")
    else:
        print("  (не записано - для записи добавь --commit)")
    sys.exit(0)


def cmd_recalc(args):
    """Проставляет каждой теме state.json оба поля - E_ранг и E_прогноз.

    Зачем поля в базе, а не только в отчётах: очередь читают четыре разных
    контура (moderate_queue, collect_queries, rost, пульт), и каждый считал
    экономику по-своему из одного размытого 'E'. С полями в базе спорить не о
    чем - в файле лежит и балл, и клики, и подпись, чем именно они посчитаны.
    По умолчанию сухой прогон: пишет только с --commit (и только под claim
    волны, state.json - разделяемый файл)."""
    data = load_state(args.state)
    changed = 0
    итог = {"замер-wordstat": [0, 0.0], "показы-вебмастера": [0, 0.0]}
    for t in data.get("темы", []):
        v = evaluate(t)
        src = "показы-вебмастера" if t.get("спрос_источник") == "показы-вебмастера" else "замер-wordstat"
        if t.get("E_ранг") != v["e_rank"] or t.get("E_прогноз") != v["e_forecast"]:
            changed += 1
        t["E_ранг"] = v["e_rank"]
        t["E_прогноз"] = v["e_forecast"]
        t["E_прогноз_основание"] = v["forecast_basis"]
        итог[src][0] += 1
        итог[src][1] += v["e_forecast"]
    print(f"Пересчёт E_ранг / E_прогноз · state={args.state}")
    print(f"  тем в базе: {len(data.get('темы', []))}, изменилось значений: {changed}")
    for src, (n, s) in итог.items():
        print(f"  источник '{src}': {n} тем, суммарный E_прогноз {round(s, 1)} кликов/мес")
    print(f"  константы: RANK_DIVISOR={RANK_DIVISOR:g} (балл) · "
          f"FACT_DIVISOR={FACT_DIVISOR:g} (клики) · CTR_ФАКТ={CTR_ФАКТ:g}")
    if not args.commit:
        print("  (сухой прогон - в state.json ничего не записано, для записи добавь --commit)")
        sys.exit(0)
    bak = save_state(data, args.state)
    print(f"  ЗАПИСАНО. Бэкап: {bak.name}")
    sys.exit(0)


def cmd_selftest():
    """Негативный + позитивные тесты формулы. exit 1 при любом провале."""
    cases = [
        # (описание, тема_обj, ожидание hard_pass, ожидание priority)
        ("НЕГАТИВНЫЙ: спрос=300, не-информационная -> НЕ проходит",
         {"тема": "ии для юриста", "спрос": 300}, False, False),
        ("граница: спрос=1000 (E=9.52) -> ещё НЕ проходит (E<10 строго)",
         {"тема": "cursor ai для новичка", "спрос": 1000}, False, False),
        ("граница: спрос=1050 (E=10.0) -> проходит HARD, не приоритет",
         {"тема": "как настроить cursor ai", "спрос": 1050}, True, False),
        ("информационная: спрос=6000, коэффициент 0.5 применён (E_raw 57.1 -> 28.6)",
         {"тема": "что такое нейросеть", "спрос": 6000}, True, False),
        ("информационная с высоким спросом уходит в приоритет через коэффициент "
         "(спрос=12000, E_raw 114.3 -> eff 57.1 >= 50)",
         {"тема": "как работает vibe coding", "спрос": 12000}, True, True),
        ("инструментальный хвост СНИМАЕТ коэффициент (спрос=6000, полный E=57.1 -> приоритет)",
         {"тема": "как настроить нейросеть для работы", "спрос": 6000}, True, True),
        ("нет данных спроса -> не проходит (E=0)",
         {"тема": "тема без замера", "спрос": None}, False, False),
    ]
    ok = True
    print("SELFTEST demand_gate.py\n")
    print("A. ранговый гейт (E_ранг) - шкала и пороги")
    for desc, obj, exp_hard, exp_priority in cases:
        v = evaluate(obj)
        got_hard, got_priority = v["hard_pass"], v["priority"]
        status = "OK" if (got_hard == exp_hard and got_priority == exp_priority) else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"[{status}] {desc}")
        print(f"       E_raw={v['e_raw']}  coef={v['coef']}  E_ранг={v['e_rank']}  "
              f"hard_pass={got_hard} (ожидали {exp_hard})  priority={got_priority} (ожидали {exp_priority})")

    # ---- B. разведение E_ранг и E_прогноз (С.3б, по решению автора) ----
    print("\nB. разведение E_ранг и E_прогноз")
    fcases = [
        ("ПОЗИТИВНЫЙ: контрольная точка калибровки - «claude code» спрос 65851, "
         "факт Вебмастера 34 клика/31д -> прогноз должен лечь в 30..45",
         {"тема": "claude code", "спрос": 65851},
         lambda v: 30 <= v["e_forecast"] <= 45),
        ("ПОЗИТИВНЫЙ: тема из показов считается по СВОИМ показам, не по спрос-экв",
         {"тема": "metricool mcp", "спрос": 9072, "спрос_источник": "показы-вебмастера",
          "показы_31д": 162.0},
         lambda v: abs(v["e_forecast"] - 162.0 * CTR_ФАКТ) < 0.01 and "показы_31д" in v["forecast_basis"]),
        ("НЕГАТИВНЫЙ: E_прогноз НЕ равен E_ранг (иначе величины снова слиплись)",
         {"тема": "как настроить cursor ai", "спрос": 1050},
         lambda v: v["e_forecast"] != v["e_rank"] and v["e_forecast"] < v["e_rank"]),
        ("НЕГАТИВНЫЙ: тема на границе рангового гейта даёт МЕНЬШЕ клика/мес - "
         "гейт пропускает, экономика говорит нет (ровно тот разрыв, ради которого разводили)",
         {"тема": "как настроить cursor ai", "спрос": 1050},
         lambda v: v["hard_pass"] and v["e_forecast"] < 1.0),
        ("НЕГАТИВНЫЙ: нет спроса -> прогноз 0 и основание 'нет спроса'",
         {"тема": "тема без замера", "спрос": None},
         lambda v: v["e_forecast"] == 0.0 and v["forecast_basis"] == "нет спроса"),
        ("ПОЗИТИВНЫЙ: коэффициент информационности бьёт по ОБЕИМ величинам",
         {"тема": "что такое нейросеть", "спрос": 6000},
         lambda v: v["coef"] == INFO_COEF
                   and abs(v["e_forecast"] - round(6000 / FACT_DIVISOR * INFO_COEF, 2)) < 0.01),
        ("ПОЗИТИВНЫЙ: старый ключ e_eff жив и равен e_rank (обратная совместимость "
         "collect_queries.py и отчётов до этой редакции)",
         {"тема": "ии для юриста", "спрос": 5000},
         lambda v: v["e_eff"] == v["e_rank"]),
        ("НЕГАТИВНЫЙ: обе ветки прогноза согласованы - показы×CTR и спрос_экв/делитель "
         "расходятся меньше чем на 5%",
         {"тема": "проверка согласованности", "спрос": int(100 * 56),
          "спрос_источник": "показы-вебмастера", "показы_31д": 100.0},
         lambda v: abs(100 * CTR_ФАКТ - (100 * 56) / FACT_DIVISOR) / (100 * CTR_ФАКТ) < 0.05),
    ]
    for desc, obj, check in fcases:
        v = evaluate(obj)
        good = bool(check(v))
        if not good:
            ok = False
        print(f"[{'OK' if good else 'FAIL'}] {desc}")
        print(f"       E_ранг={v['e_rank']}  E_прогноз={v['e_forecast']}  "
              f"основание={v['forecast_basis']}")

    # ---- В. барьер «HARD пройден на ОЦЕНКЕ спроса» (по решению автора, дефект F2) ----
    # Живой прецедент воспроизведён числами обеих сторон: та же тема, та же
    # формула, разные источники спроса дают разный вердикт гейта
    print("\nВ. барьер «HARD на оценке» (живой прецедент ltx studio, по решению автора)")
    bcases = [
        ("🔴 КОНТРПРИМЕР: оценка 16 184 (289 показов × K=56) проходит HARD - "
         "барьер обязан ПОДНЯТЬСЯ",
         {"тема": "ltx studio текст в видео", "спрос": 16184,
          "спрос_источник": "показы-вебмастера", "показы_31д": 289.0},
         lambda v: v["hard_pass"] is True and v["hard_pass_на_оценке"] is True),
        ("ЖИВОЙ ЗАМЕР той же темы 752 запроса/мес - гейт НЕ проходит вовсе, "
         "то есть статья вышла на теме, которую движок обязан был отклонить",
         {"тема": "ltx studio текст в видео", "спрос": 752,
          "спрос_источник": "замер-wordstat"},
         lambda v: v["hard_pass"] is False and v["hard_pass_на_оценке"] is False),
        ("ПОЗИТИВНЫЙ: живой замер Wordstat проходит HARD и барьер МОЛЧИТ - "
         "иначе он мерил бы факт прохода, а не источник числа",
         {"тема": "claude code", "спрос": 66035, "спрос_источник": "замер-wordstat"},
         lambda v: v["hard_pass"] is True and v["hard_pass_на_оценке"] is False),
        ("НЕГАТИВНЫЙ: оценка, которая гейт НЕ проходит, барьер тоже не поднимает - "
         "поднимать нечего, тема и так отклонена",
         {"тема": "мелкая тема", "спрос": 500, "спрос_источник": "показы-вебмастера",
          "показы_31д": 9.0},
         lambda v: v["hard_pass"] is False and v["hard_pass_на_оценке"] is False),
    ]
    for desc, obj, check in bcases:
        v = evaluate(obj)
        good = bool(check(v))
        if not good:
            ok = False
        print(f"[{'OK' if good else 'FAIL'}] {desc}")
        print(f"       E_ранг={v['e_rank']}  hard_pass={v['hard_pass']}  "
              f"hard_pass_на_оценке={v['hard_pass_на_оценке']}  "
              f"источник={v['спрос_источник']}")

    print(f"\n{'ВСЕ ТЕСТЫ ПРОШЛИ' if ok else 'ЕСТЬ ПРОВАЛЫ'}")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=str(STATE_FILE), help="путь к state.json")
    ap.add_argument("--check", help="ad hoc проверка формулировки темы (нужен --spros)")
    ap.add_argument("--spros", type=int, help="спрос/мес для --check")
    ap.add_argument("--istochnik", default="замер-wordstat",
                    choices=("замер-wordstat", "показы-вебмастера"),
                    help="откуда взят спрос: живой замер Wordstat либо ОЦЕНКА "
                         "из показов Вебмастера (показы × K=56)")
    ap.add_argument("--require-zamer", dest="require_zamer", action="store_true",
                    help="с --check: код 2, если HARD пройден на ОЦЕНКЕ спроса, "
                         "а не на живом замере Wordstat (барьер дефекта F2)")
    ap.add_argument("--force", action="store_true", help="с --check: exit 0 даже если гейт не пройден")
    ap.add_argument("--audit", action="store_true", help="прогнать гейт по срезу state.json")
    ap.add_argument("--status", default="очередь", help="статус тем для --audit (по умолч. очередь)")
    ap.add_argument("--top", type=int, default=15, help="сколько строк печатать в --audit -v")
    ap.add_argument("-v", "--verbose", action="store_true", help="печатать построчный разбор в --audit")
    ap.add_argument("--take-next", action="store_true",
                     help="показать верхнюю тему очереди, прошедшую HARD-гейт")
    ap.add_argument("--commit", action="store_true",
                     help="с --take-next: записать статус 'в работе' в state.json (с бэкапом); "
                          "с --recalc: записать поля E_ранг/E_прогноз")
    ap.add_argument("--recalc", action="store_true",
                     help="пересчитать поля E_ранг и E_прогноз по всем темам state.json "
                          "(сухой прогон без --commit)")
    ap.add_argument("--selftest", action="store_true", help="встроенные тесты формулы, вкл. негативный")
    args = ap.parse_args()

    if args.selftest:
        cmd_selftest()
    elif args.recalc:
        cmd_recalc(args)
    elif args.check is not None:
        if args.spros is None:
            sys.exit("--check требует --spros N")
        cmd_check(args)
    elif args.take_next:
        cmd_take_next(args)
    elif args.audit:
        cmd_audit(args)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
