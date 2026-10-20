"""Доктор: честный диагноз по каждой площадке и по сети.

Правило доктора: он не говорит «что-то пошло не так». По каждой площадке он
называет три вещи - что с настройкой, что с ответом площадки, что делать
следующим шагом. Если сеть режет адрес, он это показывает отдельной строкой,
потому что лечение тут другое: не токен менять, а канал
"""

from __future__ import annotations

import platform as os_platform
import socket
import sys
from dataclasses import dataclass

from . import config, media
from .net import NetworkDown
from .platforms import NAMES, build_all

def endpoints() -> dict:
    """Считается на вызове, а не на импорте: .env подтягивается позже старта
    процесса, и замороженный на импорте адрес показал бы вчерашнюю настройку"""
    ig = config.instagram()
    return {
        "instagram": "%s/%s/me" % (ig.api_base, ig.api_version),
        "telegram": config.telegram().api_base + "/",
        "vk": config.vk().api_base + "/method/utils.getServerTime",
    }


@dataclass
class Probe:
    name: str
    reachable: bool
    detail: str


def probe_network(http) -> list[Probe]:
    probes: list[Probe] = []
    table = endpoints()
    for name in NAMES:
        url = table[name]
        try:
            reply = http.get(url)
            probes.append(Probe(name, True, "ответ %s" % reply.status))
        except NetworkDown as exc:
            probes.append(Probe(name, False, "канал закрыт: %s" % str(exc)[:120]))
    return probes


def report(http=None) -> str:
    from . import net as net_module

    http = http or net_module.build()
    net_cfg = config.net()
    lines: list[str] = []
    lines.append("ДОКТОР АВТОПОСТИНГА")
    lines.append("узел          : %s / %s" % (socket.gethostname(), os_platform.system()))
    lines.append("python        : %s" % sys.version.split()[0])
    lines.append("рабочий дом   : %s" % config.home())
    lines.append("канал в сеть  : %s" % (("через прокси %s" % net_cfg.proxy) if net_cfg.proxy else "прямой"))
    lines.append("медиа-адрес   : %s" % media.describe())
    lines.append("")

    lines.append("ДОСТУПНОСТЬ АДРЕСОВ (сеть этого узла)")
    blocked = []
    for probe in probe_network(http):
        mark = "доступен" if probe.reachable else "НЕ ДОСТУПЕН"
        lines.append("  %-9s | %-11s | %s" % (probe.name, mark, probe.detail))
        if not probe.reachable:
            blocked.append(probe.name)
    if getattr(http, "forced_v4", False):
        lines.append("  примечание: маршрута до IPv6 у этого узла нет, замер сделан по IPv4")
    lines.append("")

    lines.append("ПЛОЩАДКИ")
    verdicts = {}
    for adapter in build_all(http):
        diagnosis = adapter.check()
        verdicts[adapter.name] = diagnosis.verdict
        lines.append("  " + diagnosis.line())
        if diagnosis.next_step:
            lines.append("      следующий шаг: %s" % diagnosis.next_step)
    lines.append("")

    lines.append("ЧТО ДЕЛАТЬ")
    if blocked:
        lines.append(
            "  сеть этого узла не пускает: %s. Лечится не токеном, а каналом:" % ", ".join(blocked)
        )
        lines.append("    1) прописать AUTOPOST_PROXY и повторить")
        if "telegram" in blocked:
            lines.append("    2) для telegram поднять свой local Bot API server и указать TELEGRAM_API_BASE")
        lines.append("    3) запускать движок на сервере, где адрес открыт (переменная AUTOPOST_REMOTE)")
    ready = [name for name, verdict in verdicts.items() if verdict == "ok"]
    if ready:
        lines.append("  готовы к публикации: %s" % ", ".join(ready))
    not_ready = [name for name, verdict in verdicts.items() if verdict != "ok"]
    if not_ready:
        lines.append("  ждут настройки: %s (смотри «следующий шаг» выше)" % ", ".join(not_ready))
    if not blocked and not not_ready:
        lines.append("  всё зелено: ставь публикацию командой cli.py add и запускай cli.py run")
    return "\n".join(lines)
