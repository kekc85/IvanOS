"""Связующий слой: интерпретатор + БД. Превращает Decision в записи БД и
готовит SendAction'ы к отправке. Отделён от Telegram, чтобы тестировать без сети.
"""
import os, glob, uuid as _uuid, time as _time
from datetime import datetime

from engine.importer import load_valid
from engine.interpreter import Interpreter, State, Event
from engine.timing import MSK
from .config import (FUNNELS_DIR, TIME_SCALE, REDIRECT_BASE, REGISTERED_BY_CLICK,
                     REDIRECT_ALLOW, DB_PATH)
from . import crossdb
from . import suppression

# source для общего реестра исключений: у каждого из 7 инстансов свой DB_PATH
# (voronka.sqlite / voronka-2.sqlite / ...) - имя каталога отличает инстанс
# по-человечески в /suppressed и разборе логов (в отличие от одинакового имени
# файла voronka.sqlite на 5 из 7 инстансов).
_INSTANCE_SOURCE = os.path.basename(os.path.dirname(os.path.abspath(DB_PATH))) or "unknown"


def parse_start_payload(payload):
    """deep-link /start payload -> (funnel_token, source_tag).

    'event-cpzapas' -> ('event', 'cpzapas'); 'event' -> ('event', '').
    Разделитель '-' безопасен: код-слова кириллица, translit-alias латиница без
    дефиса, служебные registered/vip дефиса не содержат. Значит любой '-' в payload
    = наш маркер источника, а не часть ключа воронки. Тег в нижний регистр для
    стабильных сегментов. Резолв funnel_token остаётся точным (resolve не трогаем):
    без тега поведение байт-в-байт прежнее.
    """
    p = (payload or "").strip()
    base, _sep, tag = p.partition("-")
    return base, tag.strip().lower()


class Runtime:
    def __init__(self, db):
        self.db = db
        self.funnels = {}       # key -> Funnel
        self.interp = {}        # key -> Interpreter
        self.by_keyword = {}    # слово(lower) -> funnel_key
        self.by_alias = {}      # латинский slug для deep-link /start -> funnel_key
        self.collisions = []    # (слово, старый_ключ, новый_ключ) - дубль A0.condition
        self._load_all()

    @staticmethod
    def _translit(s):
        m = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
             'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
             'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',
             'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}
        return ''.join(m.get(ch, ch) for ch in s.lower())

    def resolve(self, token):
        """token из /start или слова → funnel_key (кириллица-слово, латинский alias или сам ключ)."""
        if not token:
            return None
        t = token.strip()
        if t in self.funnels:
            return t
        low = t.lower()
        return self.by_keyword.get(low) or self.by_alias.get(low)

    def _load_all(self):
        for p in sorted(glob.glob(os.path.join(FUNNELS_DIR, "voronka-*.json"))):
            try:
                f = load_valid(p)
            except Exception as e:
                print(f"[skip] {os.path.basename(p)}: {e}")
                continue
            missing = self._subst_welcome_links(f)
            if missing:
                print(f"[skip] {os.path.basename(p)}: welcome-ссылки не заданы в .env: {missing}")
                continue
            key = f.key
            self.funnels[key] = f
            self.interp[key] = Interpreter(f, registered_by_click=REGISTERED_BY_CLICK)
            a0 = f.nodes.get("A0")
            if a0 and a0.condition:
                low = a0.condition.strip().lower()
                if low in self.by_keyword and self.by_keyword[low] != key:
                    # два файла на одно код-слово: dict молча затрёт первый = кража
                    # трафика. Фиксируем, bot.py логирует список на старте.
                    prev = self.by_keyword[low]
                    self.collisions.append((low, prev, key))
                    print(f"[collision] код-слово '{low}': {key} затирает {prev}")
                self.by_keyword[low] = key
                # deep-link alias (translit ключа, напр. demo->КОМАНДЫ) регистрируем
                # ТОЛЬКО для воронок с код-словом. Служебные (WELCOME/VIPWELCOME) входят
                # через /start registered|vip явными ветками on_start, а не по слову -
                # иначе юзер, набравший 'welcome'/'vipwelcome' в ЛС, запускал welcome-
                # цепочку («ты в деле, доступ открыт») без регистрации. Коллизии alias
                # ловим так же, как код-слова (translit ё/ъ/ь схлопывает омографы).
                alias = self._translit(key)
                if alias in self.by_alias and self.by_alias[alias] != key:
                    prev = self.by_alias[alias]
                    self.collisions.append((alias, prev, key))
                    print(f"[collision] alias '{alias}': {key} затирает {prev}")
                self.by_alias[alias] = key

    @staticmethod
    def _subst_welcome_links(f):
        """Welcome-воронки: плейсхолдеры {КАБИНЕТ}/{ОПЛАТА}/{АНКЕТА} → ссылки из .env.
        Возвращает список незаполненных плейсхолдеров (воронку тогда не грузим)."""
        from .config import WELCOME_LINKS
        used = set()
        for n in f.nodes.values():
            for ph in WELCOME_LINKS:
                if ph in (n.text or "") or any(ph in (b.url or "") for b in n.buttons if b.url):
                    used.add(ph)
        missing = sorted(ph for ph in used if not WELCOME_LINKS[ph])
        if missing:
            return missing
        for n in f.nodes.values():
            for ph, url in WELCOME_LINKS.items():
                if not url:
                    continue
                if n.text:
                    n.text = n.text.replace(ph, url)
                for b in n.buttons:
                    if b.url:
                        b.url = b.url.replace(ph, url)
        return []

    def state_of(self, user_id, funnel_key) -> State:
        st = State(funnel_key=funnel_key)
        st.node = self.db.get_state(user_id, funnel_key)
        st.tags = self.db.tags(user_id)
        st.opted_out, st.banned_bot = self.db.flags(user_id)
        return st

    def render_text(self, user_id, funnel_key, send):
        """Плейсхолдер {ССЫЛКА} в тексте узла → персональная трекинг-ссылка
        (тот же редирект, что у кнопки: клик ловится и двигает воронку).
        Без плейсхолдера текст уходит как есть."""
        text = send.text
        if "{ИМЯ}" in text:
            # first_name из Telegram часто «Имя Фамилия» - обращаемся только по
            # имени (первое слово с буквами; эмодзи-обвес и пустоту меняем на «друг»)
            raw = (self.db.get_first_name(user_id) or "").strip()
            first = next((w for w in raw.split() if any(ch.isalpha() for ch in w)), "друг")
            text = text.replace("{ИМЯ}", first)
        if "{ССЫЛКА}" in text:
            target = next((b.url for b in send.buttons if b.url), None)
            if target:
                text = text.replace("{ССЫЛКА}",
                                    self.wrap_button_url(user_id, funnel_key, send.node_key, target))
        return text

    def wrap_button_url(self, user_id, funnel_key, node_key, url):
        """URL-кнопку → per-user редирект-ссылку клик-трекинга.

        Событие-CTA (в т.ч. бот-диплинк с ключом воронки) ОБОРАЧИВАЕМ - клик по нему
        = регистрация = стоп дожима (редирект 302 доводит до бота событие, клик
        ловится). Канал (t.me-вступление <адрес-бота>...) отдаём ПРЯМО, без обёртки -
        редирект ломает нативный invite-диплинк. article оборачиваем всегда.
        """
        is_event = ("event" in url) or bool(deeplink_key(url))
        if ("t.me" in url) and not is_event:
            return url
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        if not any(host == d or host.endswith("." + d) for d in REDIRECT_ALLOW):
            # кабинет платформы курса / анкета: домен вне allowlist редиректа - отдать прямо
            return url
        kind = "event" if is_event else "article"
        if kind == "event" and "t.me" not in url:
            # лендинг получает tg_id юзера: форма платформы курса подхватит его скрытым
            # полем и вернёт вебхуком /hooks/gc-registered (честный registered)
            url = url + ("&" if "?" in url else "?") + f"tg_id={user_id}"
        uid = _uuid.uuid4().hex
        self.db.add_redirect(uid, user_id, funnel_key, node_key, url, kind)
        return f"{REDIRECT_BASE}/r/{uid}"

    def apply(self, user_id, funnel_key, ev: Event):
        """Прогоняет событие через интерпретатор, пишет в БД, возвращает список SendAction."""
        st = self.state_of(user_id, funnel_key)
        dec = self.interp[funnel_key].handle(st, ev)
        for tag in dec.set_tags:
            self.db.add_tag(user_id, tag)
        for c in dec.cancels:
            if c.reason == "opted_out":
                self.db.set_flag(user_id, "opted_out", True)
            if c.reason == "registered":
                self.db.add_tag(user_id, "registered")
                crossdb.tag_neighbor(user_id, "registered")   # симметрия с соседним инстансом
                suppression.add_safe(user_id, "registered", _INSTANCE_SOURCE)  # гасит рассылки во ВСЕХ 7 ботах
            self.db.cancel_all(user_id, funnel_key)
        for s in dec.schedules:
            self.db.schedule(user_id, funnel_key, s.node_key, s.due_at.timestamp(), s.delete_others)
        if dec.sends:
            # состояние = последний отправленный/проведённый узел
            self.db.set_state(user_id, funnel_key, dec.sends[-1].node_key)
        return dec.sends

    def now(self):
        return datetime.now(MSK)

    def valid_button(self, user_id, funnel_key, label):
        """Разрешён ли button-event: label должен быть reply/callback-кнопкой ТЕКУЩЕГО
        узла юзера. Иначе юзер произвольным текстом самопродвигал бы воронку."""
        if funnel_key not in self.funnels:
            return False
        node_key = self.db.get_state(user_id, funnel_key)
        node = self.funnels[funnel_key].nodes.get(node_key)
        if not node:
            return False
        return any((not b.url) and b.text.strip().lower() == str(label).strip().lower()
                   for b in node.buttons)

# протокол deep-link описан в нижнем слое, здесь только реэкспорт
from engine.model import DEEPLINK_PARAM, deeplink, deeplink_key  # noqa: E402,F401
