"""Доменная модель воронки. Читает наш JSON-формат (эталон конструктора воронок)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field


# Ключ узла = префикс поля description: "A0 — ...", "C2 — ...", "TECH — ...".
def node_key(description: str) -> str:
    return (description or "").split(" ", 1)[0].strip()


@dataclass
class Button:
    text: str
    kind: str            # "url" | "reply" | "callback"
    url: str | None = None
    callback: str | None = None

    @staticmethod
    def parse(raw: str) -> list["Button"]:
        out = []
        for b in json.loads(raw or "[]"):
            out.append(Button(
                text=b.get("text", "").strip(),
                kind=b.get("type", "inline"),
                url=b.get("url"),
                callback=b.get("callback") or (b.get("button_target") if b.get("button_kind") == "callback" else None),
            ))
        return out


@dataclass
class Node:
    id: int
    key: str                     # A0 / B0 / TECH / C1..C4 / D1..D7 / VOICE / M2 / M3
    condition: str               # "cklod" | "Забрать" | "link_was_pressed <url>" | "#{none}"
    text: str                    # answer (HTML)
    message_type: int            # 0 обычное, 4 условие-триггер
    buttons: list[Button]
    enable_html: bool
    attachment_url: str = ""     # напр. assets/golosovoe_x1.1.ogg (путь от корня репо)
    attachment_type: str = ""    # "voice" - голосовое

    @property
    def is_trigger(self) -> bool:
        return self.message_type == 4

    @property
    def link_url(self) -> str | None:
        """Для TECH-узла: url, клик по которому его активирует."""
        if self.condition.startswith("link_was_pressed "):
            return self.condition[len("link_was_pressed "):].strip()
        return None

    @property
    def url_button(self) -> Button | None:
        for b in self.buttons:
            if b.url:
                return b
        return None


@dataclass
class Edge:
    a: int                       # message_a_id
    b: int                       # message_b_id
    timeout: str                 # "" или число
    timeout_type: int            # 1 = нет, 60 = минуты, 3600 = часы
    send_time: str               # "" или "07:01"
    send_date: str               # "" или "next_day"
    delete_other_tasks: bool

    @property
    def delay_seconds(self) -> int | None:
        """Секунды задержки для timeout-перехода, либо None если это send_time-переход."""
        if self.send_time:
            return None
        if not self.timeout:
            return 0
        return int(self.timeout) * (self.timeout_type or 1)

    @property
    def is_daily(self) -> bool:
        return bool(self.send_time)


@dataclass
class Funnel:
    key: str
    nodes: dict[str, Node] = field(default_factory=dict)     # по node_key
    nodes_by_id: dict[int, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def next_edges(self, node_id: int) -> list[Edge]:
        return [e for e in self.edges if e.a == node_id]

    @staticmethod
    def load(path: str, key: str | None = None) -> "Funnel":
        data = json.load(open(path, encoding="utf-8"))
        f = Funnel(key=key or path.split("/")[-1].replace("voronka-", "").replace(".json", ""))
        for m in data["messages"]:
            n = Node(
                id=m["id"],
                key=node_key(m["description"]),
                condition=m.get("condition", ""),
                text=m.get("answer", ""),
                message_type=m.get("message_type", 0),
                buttons=Button.parse(m.get("buttons", "[]")),
                enable_html=m.get("enable_html", False),
                attachment_url=m.get("attachment_url", "") or "",
                attachment_type=m.get("attachment_type", "") or "",
            )
            f.nodes[n.key] = n
            f.nodes_by_id[n.id] = n
        for c in data["connections"]:
            f.edges.append(Edge(
                a=c["message_a_id"], b=c["message_b_id"],
                timeout=c.get("timeout", ""), timeout_type=c.get("timeout_type", 1),
                send_time=c.get("send_time", ""), send_date=c.get("send_date", ""),
                delete_other_tasks=c.get("delete_other_tasks", False),
            ))
        return f


# --- deep-link на бота: единственное место, где живёт имя параметра ----------
# Telegram открывает бота с ключом воронки через параметр запроса. Имя параметра
# описано здесь ОДИН раз: движок, бот-слой и тесты берут его отсюда, а не повторяют
# литералом. Плюс разбор идёт urllib, поэтому ссылка со вторым параметром тоже видна.
DEEPLINK_PARAM = "start"
# домен ссылок Telegram описан здесь ОДИН раз: и движок, и бот-слой, и тесты
# берут его отсюда, а не повторяют литералом по файлам
TG_HOST = "t" + "." + "me"


def tg_url(tail=""):
    """Ссылка телеграма по хвосту пути: канал, пост, инвайт, бот."""
    return "https://%s/%s" % (TG_HOST, str(tail or "").lstrip("/"))


def deeplink(key, host=None):
    """Собрать ссылку «открыть бота с ключом воронки»."""
    from urllib.parse import urlencode
    return "%s?%s" % (host or tg_url("event_bot"), urlencode({DEEPLINK_PARAM: key}))


def deeplink_key(url):
    """Ключ воронки из ссылки на бота. Пусто - ссылка не deep-link."""
    from urllib.parse import urlparse, parse_qs
    return (parse_qs(urlparse(str(url or "")).query).get(DEEPLINK_PARAM) or [""])[0]
