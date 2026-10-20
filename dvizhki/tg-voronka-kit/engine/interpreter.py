"""Ядро движка воронки: чистая машина состояний.

Не зависит от Telegram и БД - на вход события, на выход действия (что отправить,
что запланировать, что отменить). Это делает логику юнит-тестируемой без сети.

Внешний слой (бот/воркер) превращает Action в реальные sendMessage и записи
в scheduled_jobs. Гварды (opted_out/registered/banned_bot) проверяются здесь
перед выдачей действий, повторяя семантику эталона конструктора воронок.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from .model import Funnel, Node, Edge
from .timing import next_daily, parse_hhmm, clamp_send_window


# ---- События (вход) ------------------------------------------------------
@dataclass
class Event:
    kind: str          # "enter" | "button" | "click" | "timeout" | "stop"
    at: datetime
    node_key: str | None = None      # для timeout: какой узел «дозрел»
    payload: str | None = None       # текст кнопки / url клика


# ---- Действия (выход) ----------------------------------------------------
@dataclass
class SendAction:
    node_key: str
    at: datetime
    text: str
    buttons: list                    # список Button из модели
    attachment_type: str = ""        # "video_note"/"voice" - шлётся ПЕРЕД текстом
    attachment_url: str = ""         # telegram file_id (бот-скоуп) или путь к файлу


@dataclass
class ScheduleAction:
    node_key: str                    # какой узел отправить...
    due_at: datetime                 # ...в этот момент
    delete_others: bool = False      # погасить прочие pending этого юзера (delete_other_tasks)


@dataclass
class CancelAllAction:
    reason: str


@dataclass
class Decision:
    sends: list[SendAction] = field(default_factory=list)
    schedules: list[ScheduleAction] = field(default_factory=list)
    cancels: list[CancelAllAction] = field(default_factory=list)
    set_tags: list[str] = field(default_factory=list)


# ---- Состояние контакта в воронке ---------------------------------------
@dataclass
class State:
    funnel_key: str
    node: str | None = None
    tags: set = field(default_factory=set)     # f_<funnel>, magnet_taken, registered...
    opted_out: bool = False
    banned_bot: bool = False


# Узлы дожима, которые гасятся тегами registered / event_optout (продающая ветка).
SALES_NODES = {"C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "D5", "D6", "D7",
               "K1", "K2", "K3"}   # K* - фронт-цепочка событие

# Узлы welcome-цепочки, которые гасятся тегом vip (апселл и анкета бесплатных:
# купившему VIP апселл не шлём, анкету ему заменяет бронь стратсессии B2).
VIP_SUPPRESSED = {"A2", "A3", "A4", "A5", "A6", "A7"}

# Пуши «вошёл по слову, но не нажал Забрать». Гасятся тегом
# magnet_taken_<воронка> - он ставится в момент выдачи B0, так что человеку,
# забравшему гайд, напоминания не приходят (pending-джобы дозревают, но глушатся
# гвардом). Тег пер-воронковый: забор гайда КЛОД не глушит напоминания ДОСТУП.
MAGNET_REMINDER_NODES = {"R1", "R2"}

# Узлы с отправкой только в окне 10:00-21:00 МСК (дожим и welcome-хвост;
# A1/A11 событийные - идут сразу за регистрацией в любое время).
# R1/R2 тоже в окне: вход в 23:30 не должен будить человека пушем в 00:30.
WINDOWED_NODES = {"K1", "K2", "K3", "A12", "A2", "A3", "A4", "A5", "A6", "A7",
                  "B2", "B3", "B4", "B5", "B6", "B7", "R1", "R2"}

# Дуга ПРОГРАММА (open sale): окно шире - 10:00-23:00 МСК. Открытие заявок
# гонит трафик вечером, дожим обязан догонять в тот же вечер; но узел,
# дозревший после 23:00, переезжает на утро, а не будит ночью.
PROG_WINDOWED = {"P1", "P2"}


class Interpreter:
    """Прогоняет одно событие через воронку и возвращает Decision."""

    def __init__(self, funnel: Funnel, registered_by_click: bool = True):
        self.f = funnel
        # True: клик по событие-кнопке = регистрация (прокси, пока нет вебхука
        # платформы курса). False: registered ставит только вебхук, клик лишь трекается.
        self.registered_by_click = registered_by_click

    # --- вспомогательное ---
    def _guarded(self, state: State, node_key: str) -> bool:
        if state.opted_out or state.banned_bot:
            return False
        if node_key in SALES_NODES and ({"registered", "event_optout"} & state.tags):
            return False
        # вступил в закрытый канал (бот-админ видит вступление, тег in_staff) -
        # дожимы «вступи в канал» (K*) больше не нужны
        if node_key in SALES_NODES and "in_staff" in state.tags:
            return False
        if node_key in VIP_SUPPRESSED and "vip" in state.tags:
            return False
        if node_key in MAGNET_REMINDER_NODES and f"magnet_taken_{self.f.key}" in state.tags:
            return False
        return True

    def _schedule_from(self, node: Node, at: datetime) -> list[ScheduleAction]:
        """Из узла node строит планы на все исходящие рёбра."""
        plans = []
        for e in self.f.next_edges(node.id):
            target = self.f.nodes_by_id[e.b].key
            if e.is_daily:
                hh, mm = parse_hhmm(e.send_time)
                due = next_daily(at, hh, mm)
            else:
                secs = e.delay_seconds or 0
                due = at.fromtimestamp(at.timestamp() + secs, tz=at.tzinfo)
            if target in WINDOWED_NODES:
                due = clamp_send_window(due)
            elif target in PROG_WINDOWED:
                due = clamp_send_window(due, end_h=23)
            plans.append(ScheduleAction(node_key=target, due_at=due, delete_others=e.delete_other_tasks))
        return plans

    def _emit(self, state: State, node: Node, at: datetime, d: Decision):
        """Провести узел: отправить сообщение (если оно есть) + запланировать переходы.

        Служебные узлы вроде TECH несут answer "#{none}" - они ничего не шлют
        юзеру, только двигают воронку дальше по таймерам.
        """
        state.node = node.key
        if node.key == "B0":
            # выдача магнита: пер-воронковый тег глушит будущие R-напоминания
            tag = f"magnet_taken_{self.f.key}"
            state.tags.add(tag)
            d.set_tags.append(tag)
        if node.text and node.text.strip() not in ("#{none}", ""):
            d.sends.append(SendAction(node_key=node.key, at=at, text=node.text, buttons=node.buttons,
                                      attachment_type=node.attachment_type or "",
                                      attachment_url=node.attachment_url or ""))
        d.schedules.extend(self._schedule_from(node, at))

    # --- главный вход ---
    def handle(self, state: State, ev: Event) -> Decision:
        d = Decision()

        if ev.kind == "stop":
            state.opted_out = True
            d.cancels.append(CancelAllAction(reason="opted_out"))
            return d

        if ev.kind == "enter":
            # старт воронки: тег источника + отправка входного узла
            # (A0 - словесные/фронт, A1 - welcome после реги, B1 - vip-welcome)
            state.tags.add(f"f_{self.f.key}")
            d.set_tags.append(f"f_{self.f.key}")
            entry = self.f.nodes.get("A0") or self.f.nodes.get("A1") or self.f.nodes.get("B1")
            if entry and self._guarded(state, entry.key):
                self._emit(state, entry, ev.at, d)
            return d

        if ev.kind == "reenter":
            # повторный ввод слова при уже активной дуге: A0 и дожим уже идут.
            # Перезапуск заново повторно шлёт пройденные C/D (дедуп ловит только
            # pending, не done). Поэтому только напоминаем A0, БЕЗ нового scheduling.
            # НО не пере-питчим лид-магнит тому, кто его уже забрал или зарегистрировался -
            # A0 нет ни в одном suppression-сете, потому гвардим здесь явно.
            already = (f"magnet_taken_{self.f.key}" in state.tags) or ("registered" in state.tags)
            a0 = self.f.nodes.get("A0")
            if a0 and not already and self._guarded(state, "A0") and a0.text and a0.text.strip() not in ("#{none}", ""):
                d.sends.append(SendAction(node_key="A0", at=ev.at, text=a0.text, buttons=a0.buttons))
            return d

        if ev.kind == "button":
            # нажата reply/inline-кнопка (напр. «Забрать») → узел, чей condition совпал
            target = self._match_condition(ev.payload)
            if target and self._guarded(state, target.key):
                self._emit(state, target, ev.at, d)
            return d

        if ev.kind == "click":
            # клик по редиректу: если url == event → registered + стоп дожима
            # (только в режиме клик-прокси); если url совпал с TECH.link_url →
            # активировать TECH-цепочку
            if ev.payload and "event" in ev.payload:
                if self.registered_by_click:
                    state.tags.add("registered")
                    d.set_tags.append("registered")
                    d.cancels.append(CancelAllAction(reason="registered"))
                return d
            tech = self._match_link(ev.payload)
            if tech and self._guarded(state, tech.key):
                self._emit(state, tech, ev.at, d)
            return d

        if ev.kind == "timeout":
            # запланированный узел дозрел → отправить его (с проверкой гвардов)
            node = self.f.nodes.get(ev.node_key)
            if node and not self._guarded(state, node.key):
                # заглушенный узел гасим сразу, не пересаживая его в окно 10-21
                # (иначе мёртвая pending-джоба переезжает лишний круг - ревью)
                return d
            if node and node.key in WINDOWED_NODES:
                due = clamp_send_window(ev.at)
                if due > ev.at:
                    # дозрело вне окна 10-21 МСК (например бот лежал) -
                    # перенести на окно, а не слать ночью
                    d.schedules.append(ScheduleAction(node_key=node.key, due_at=due))
                    return d
            if node and node.key in PROG_WINDOWED:
                due = clamp_send_window(ev.at, end_h=23)
                if due > ev.at:
                    d.schedules.append(ScheduleAction(node_key=node.key, due_at=due))
                    return d
            if node and self._guarded(state, node.key):
                self._emit(state, node, ev.at, d)
            return d

        return d

    def _match_condition(self, text: str | None) -> Node | None:
        if not text:
            return None
        t = text.strip().lower()
        for n in self.f.nodes.values():
            c = (n.condition or "").strip().lower()
            if c and not c.startswith(("link_was_pressed", "#{")) and c == t:
                return n
        return None

    def _match_link(self, url: str | None) -> Node | None:
        if not url:
            return None
        for n in self.f.nodes.values():
            if n.link_url and n.link_url == url:
                return n
        return None
