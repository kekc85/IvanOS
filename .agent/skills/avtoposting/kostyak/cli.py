#!/usr/bin/env python3
"""Автопостинг: один вход на весь движок.

Команды, которых хватает на всё:

  doctor              что настроено, что отвечает, что делать дальше
  add                 поставить публикацию в очередь (сейчас или на время)
  run                 отправить всё, чему пришло время
  status              что в очереди и чем закончилось
  retry               вернуть упавшее обратно в очередь
  media put <файл>    положить файл в веб и получить публичный адрес
  media check <адрес> проверить, что адрес живой и отдаёт медиа

Примеры:
  python3 cli.py doctor
  python3 cli.py add --platform telegram --text "первый пост движка"
  python3 cli.py add --platform instagram --media https://example.org/kartinka.jpg \\
                     --text "подпись" --at "2026-08-27 09:00"
  python3 cli.py run
  python3 cli.py status
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# ставится ДО первого импорта пакета: костяк раздаётся ученикам и обязан
# оставаться чистым, а кэш байткода растёт молча от каждого запуска
sys.dont_write_bytecode = True

from autopost import config, media, net, runner, store  # noqa: E402
from autopost.platforms import NAMES  # noqa: E402


def log(line: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = "%s %s" % (stamp, line)
    print(text)
    try:
        with config.log_path().open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass


def parse_when(value: str) -> float:
    """Время публикации человеческими словами.

    Понимает: пусто (сейчас), «+30m» / «+2h» / «+1d», «2026-08-27 09:00»
    """
    value = (value or "").strip()
    if not value or value in ("now", "сейчас"):
        return time.time()
    if value.startswith("+"):
        unit = value[-1].lower()
        try:
            amount = float(value[1:-1])
        except ValueError:
            raise SystemExit("не понял отсрочку «%s». Пример: +30m, +2h, +1d" % value)
        factor = {"m": 60, "h": 3600, "d": 86400, "s": 1}.get(unit)
        if not factor:
            raise SystemExit("не понял единицу «%s». Есть s, m, h, d" % unit)
        return time.time() + amount * factor
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).timestamp()
        except ValueError:
            continue
    raise SystemExit("не понял время «%s». Примеры: +30m, 2026-08-27 09:00" % value)


def cmd_doctor(args) -> int:
    from autopost import doctor

    http = net.build()
    try:
        print(doctor.report(http))
    finally:
        http.close()
    return 0


def cmd_add(args) -> int:
    queue = store.Queue(config.db_path())
    when = parse_when(args.at)
    media_list = list(args.media or [])
    if args.upload:
        media_list = [media.put(path) for path in media_list]
    item_id, created = queue.add(
        platform=args.platform,
        kind=args.kind or "",
        text=args.text or "",
        media=media_list,
        publish_at=when,
        idem_key=args.key or None,
    )
    word = "поставлено" if created else "уже стояло в очереди, повтор не создан"
    log("add %s %s %s на %s" % (item_id, args.platform, word, store.human_time(when)))
    queue.close()
    return 0


def cmd_run(args) -> int:
    queue = store.Queue(config.db_path())
    http = net.build()
    try:
        if args.loop:
            runner.run_forever(queue, http, interval=args.interval, log=log)
            return 0
        outcomes = runner.run_once(queue, http, platform=args.platform or "", log=log)
        if not outcomes:
            log("run: сейчас публиковать нечего")
        failed = [o for o in outcomes if o.status == "failed"]
        return 1 if failed else 0
    finally:
        http.close()
        queue.close()


def cmd_status(args) -> int:
    queue = store.Queue(config.db_path())
    counts = queue.counts()
    if not counts:
        print("очередь пуста")
    else:
        print("итого: " + ", ".join("%s %s" % (status, number) for status, number in sorted(counts.items())))
    print("")
    print("%-12s %-9s %-10s %-16s %s" % ("id", "площадка", "статус", "когда", "след"))
    for item in queue.all(limit=args.limit):
        trail = item.remote_url or item.last_error[:70]
        print(
            "%-12s %-9s %-10s %-16s %s"
            % (item.id, item.platform, item.status, store.human_time(item.publish_at), trail)
        )
    queue.close()
    return 0


def cmd_retry(args) -> int:
    queue = store.Queue(config.db_path())
    number = queue.revive(args.id or "")
    log("retry: вернул в очередь строк - %d" % number)
    queue.close()
    return 0


def cmd_media(args) -> int:
    if args.action == "put":
        url = media.put(args.value)
        print(url)
        ok, status, ctype = media.verify(url)
        print("проверка адреса: %s (код %s, тип %s)" % ("живой" if ok else "НЕ ОТВЕЧАЕТ", status, ctype))
        return 0 if ok else 1
    ok, status, ctype = media.verify(args.value)
    print("%s | код %s | тип %s" % ("живой" if ok else "НЕ ОТВЕЧАЕТ", status, ctype))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="движок автопостинга по официальным API площадок"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="диагноз по каждой площадке и по сети")

    add = subparsers.add_parser("add", help="поставить публикацию в очередь")
    add.add_argument("--platform", required=True, choices=list(NAMES))
    add.add_argument("--text", default="")
    add.add_argument("--media", nargs="*", default=[], help="публичные ссылки или локальные файлы")
    add.add_argument("--kind", default="", help="text | photo | album | video | carousel | reels")
    add.add_argument("--at", default="", help="когда: пусто = сейчас, +30m, 2026-08-27 09:00")
    add.add_argument("--upload", action="store_true", help="сначала положить локальные файлы в веб")
    add.add_argument("--key", default="", help="свой ключ идемпотентности")

    run = subparsers.add_parser("run", help="отправить всё, чему пришло время")
    run.add_argument("--platform", default="", help="ограничить одной площадкой")
    run.add_argument("--loop", action="store_true", help="крутиться вечно, для расписания")
    run.add_argument("--interval", type=float, default=60.0)

    status = subparsers.add_parser("status", help="что в очереди и чем закончилось")
    status.add_argument("--limit", type=int, default=20)

    retry = subparsers.add_parser("retry", help="вернуть упавшее в очередь")
    retry.add_argument("--id", default="")

    media_cmd = subparsers.add_parser("media", help="публичный адрес медиа")
    media_cmd.add_argument("action", choices=["put", "check"])
    media_cmd.add_argument("value")

    return parser


def main(argv=None) -> int:
    config.load_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "doctor": cmd_doctor,
        "add": cmd_add,
        "run": cmd_run,
        "status": cmd_status,
        "retry": cmd_retry,
        "media": cmd_media,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
