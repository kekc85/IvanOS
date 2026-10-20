"""Telegram-бот: вход по заявке (окно 5 мин), deep-link /start, слово, кнопки, дожим.

Запуск: .venv/bin/python -m app.bot
"""
import asyncio, html, time, logging, re
from datetime import datetime

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      LinkPreviewOptions)
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ChatJoinRequestHandler, ChatMemberHandler, ContextTypes, filters)

from .config import (BOT_TOKEN, ADMIN_CHAT_ID, DB_PATH, FUNNELS_DIR, BROADCAST_RATE,
                     FRONT_FUNNEL_KEY, DEFAULT_FUNNEL_KEY, DOZHIM_RATE, DOZHIM_BATCH,
                     BLOCKED_USER_IDS, ANTHROPIC_API_KEY, AI_ENABLED, AI_MODEL,
                     AI_HOURLY_PER_USER, AI_DAILY_PER_USER, AI_DAILY_GLOBAL,
                     AI_BOT_ROLE, WELCOME_CABINET_URL, AUTO_APPROVE_ALL,
                     DIRECT_ENTRY_FUNNELS)
from . import crossdb
from . import suppression
from .db import DB
from .runtime import Runtime, parse_start_payload
from . import broadcast as bc
from . import ai_responder
from .observability import init_sentry, capture_exception, capture_message
from engine.interpreter import Event, SendAction
from engine.timing import MSK
from engine.model import tg_url
from engine.model import deeplink as _dl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# безопасность: python-telegram-bot ходит в Bot API через httpx, а
# httpx на уровне INFO печатает ПОЛНЫЙ URL запроса - вместе с боевым токеном,
# который лежит прямо в пути (.../bot<TOKEN>/getUpdates). В bot.log это тысячи
# строк с секретом открытым текстом плюс те же строки в ротированных .gz.
# Поднимаем httpx и httpcore до WARNING: сетевые сбои и ретраи по-прежнему
# видны, рутинный поллинг больше не течёт токеном. Наш логгер voronka и
# логгер telegram.* остаются на INFO - штатная работа логируется как раньше.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("voronka")

db = DB(DB_PATH)
rt = Runtime(db)

# Превью ссылок ОТКЛЮЧЕНО везде (автор: карточки-превью не показывать никогда).
NOPREVIEW = LinkPreviewOptions(is_disabled=True)


def _kbd(node_buttons, user_id, funnel_key, node_key):
    """Клавиатура узла.

    url-кнопки → inline, URL обёрнут в per-user редирект (клик-трекинг); t.me-кнопки
    остаются прямыми. Кнопки БЕЗ url (в эталоне «Забрать» type=reply) → REPLY-клавиатура:
    нажатие ШЛЁТ текст кнопки боту, открывает диалог навсегда (иначе после approve
    заявки окно инициации закрыто и бот ловит 403 на дожим). Один тип на сообщение -
    в эталоне A0 только reply-кнопка, B0/C/D только url, конфликта нет.
    """
    url_rows = []
    for b in node_buttons:
        if b.url:
            wrapped = rt.wrap_button_url(user_id, funnel_key, node_key, b.url)
            url_rows.append([InlineKeyboardButton(b.text, url=wrapped)])
        elif b.kind == "callback" and b.callback:
            # inline callback-кнопка (напр. «Не в этот раз» = wsopt в K3)
            url_rows.append([InlineKeyboardButton(b.text, callback_data=b.callback)])
    if url_rows:
        return InlineKeyboardMarkup(url_rows)
    # reply-кнопка «Забрать» внизу экрана лишняя - висит у человека
    # навсегда и ничего не даёт. Новую не ставим, а сообщением узла снимаем ту,
    # что осталась от прошлых воронок (ReplyKeyboardRemove безвреден, если её нет)
    return ReplyKeyboardRemove()


# Подтверждение отказа от событие-напоминаний (кнопка «Не в этот раз» в K3)
OPTOUT_CONFIRM = "Принял, про событие больше не пишу 🤝\n\nОстаёмся на связи в канале"


def _mute_parallel_dozhim(user_id):
    """Вход во фронт-цепочку событие глушит параллельные дожимы юзера:
    свои pending-джобы + pending-джобы соседнего бота-инстанса (MUTE_DB_PATH),
    иначе человек получит несколько дожимов о событие за одни сутки.
    Звать через asyncio.to_thread - записи в SQLite блокирующие."""
    db.cancel_all(user_id)
    crossdb.cancel_neighbor(user_id)


def _optout_event(user_id):
    """Кнопка «Не в этот раз»: глобальный стоп событие-дожимов для юзера -
    тег event_optout (гасит SALES_NODES у всех воронок) + отмена pending
    здесь и в соседнем инстансе (там тег ставим тоже).
    Звать через asyncio.to_thread."""
    db.add_tag(user_id, "event_optout")
    db.cancel_all(user_id)
    db.event(user_id, "event_optout")
    crossdb.tag_neighbor(user_id, "event_optout")


async def _send_node(bot, chat_id, funnel_key, send):
    if getattr(send, "attachment_type", "") == "video_note" and send.attachment_url:
        # приветственный кружок: сначала кружок, текст узла через 10 секунд.
        # Кружок best-effort: протухший file_id не должен глушить
        # текст welcome-цепочки - логируем и шлём текст сразу.
        try:
            await bot.send_video_note(chat_id=chat_id, video_note=send.attachment_url)
            await asyncio.sleep(10)
        except Exception as e:
            log.warning("video_note failed user %s node %s: %s", chat_id, send.node_key, e)
    await bot.send_message(chat_id=chat_id, text=rt.render_text(chat_id, funnel_key, send),
                           parse_mode=ParseMode.HTML,
                           reply_markup=_kbd(send.buttons, chat_id, funnel_key, send.node_key),
                           link_preview_options=NOPREVIEW)


async def _run(bot, user_id, funnel_key, ev, skip_nodes=None):
    """Прогнать событие и отправить сообщения. Возвращает True если ок (или нечего
    слать), False если была СЕТЕВАЯ ошибка отправки (джобу надо ретраить).

    skip_nodes: узлы, которые движок ПРОВОДИТ полностью (funnel_state, теги, все
    исходящие рёбра в scheduled_jobs), но сообщение юзеру НЕ уходит. Нужен только
    деплинк-входу воронок DIRECT_ENTRY_FUNNELS: там A0 (питч + reply-кнопка
    «Забрать») - лишнее нулевое касание, человек пришёл по осознанной ссылке и
    должен получить ровно одно сообщение, узел B0. Ребро A0→R1 при
    этом сохраняется - иначе пропадут R-пуши.
    """
    # свежая проверка флагов ПЕРЕД отправкой (гонка: юзер отписался, а джоба уже в тике)
    opted, banned = db.flags(user_id)
    if opted or banned:
        return True
    try:
        sends = rt.apply(user_id, funnel_key, ev)
    except Exception as e:
        log.exception("apply failed: %s", e)
        return True  # логическая ошибка - не крутить бесконечно
    if skip_nodes:
        # Фильтруем СТРОГО ПОСЛЕ rt.apply: там уже записаны funnel_state, теги и
        # джобы (runtime.py apply), гасим ровно один исходящий sendMessage.
        # Аудит db.event(send) для подавленного узла тоже не пишется - верно,
        # отправки не было.
        sends = [s for s in sends if s.node_key not in skip_nodes]
    for s in sends:
        o2, b2 = db.flags(user_id)          # мог отписаться между сообщениями
        if o2 or b2:
            break
        try:
            await _send_node(bot, user_id, funnel_key, s)
        except Forbidden as e:
            msg = str(e).lower()
            if "blocked" in msg or "deactivated" in msg:
                db.set_flag(user_id, "banned_bot", True)
                db.cancel_all(user_id)
                log.info("user %s заблокировал бота - дожим остановлен", user_id)
            else:
                log.info("user %s: диалог не открыт (%s) - жду сообщения от юзера", user_id, e)
            return True   # не сетевой сбой - ретрай не нужен
        except Exception as e:
            log.warning("send failed (retry) user %s: %s", user_id, e)
            return False  # сетевой сбой - джобу вернём в pending
        # аудит-запись ПОСЛЕ подтверждённой отправки и ВНЕ send-try: если db.event
        # бросит (лок БД), это не должно уронить нас в except→return False→ретрай =
        # повторная отправка уже доставленного узла (дубль). Аудит best-effort.
        try:
            db.event(user_id, "send", f"{funnel_key}/{s.node_key}")
        except Exception as e:
            log.warning("audit event failed (send уже прошёл) user %s: %s", user_id, e)
    return True


# --- анти-абьюз заявок: дедуп по юзеру + глобальный лимит/мин ---
_join_seen = {}          # user_id -> ts последней обработки
_join_window = []        # ts заявок за последнюю минуту
JOIN_PER_USER_SEC = 3600  # не пере-обрабатывать одного юзера чаще раза в час
JOIN_GLOBAL_PER_MIN = 120 # не больше стольки заявок в минуту суммарно


def _join_allowed(user_id):
    now = time.time()
    if now - _join_seen.get(user_id, 0) < JOIN_PER_USER_SEC:
        return False
    while _join_window and now - _join_window[0] > 60:
        _join_window.pop(0)
    if len(_join_window) >= JOIN_GLOBAL_PER_MIN:
        return False
    _join_seen[user_id] = now
    _join_window.append(now)
    return True


# Хэш инвайт-ссылки закрытого канала: по нему узнаём свои заявки
LIVE_STAFF_HASH = "INVITE"


async def on_staff_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Бот-админ закрытого канала видит вступления: тег in_staff гасит недосланные
    K-дожимы фронт-цепочки (гвард в интерпретаторе). Работает для любого канала,
    где бот админ."""
    cm = update.chat_member
    if not cm or cm.chat.type != "channel":
        return
    was = cm.old_chat_member.status if cm.old_chat_member else ""
    now = cm.new_chat_member.status if cm.new_chat_member else ""
    if now in ("member", "administrator", "creator") and was not in ("member", "administrator", "creator"):
        uid = cm.new_chat_member.user.id
        if cm.new_chat_member.user.is_bot:
            return
        await asyncio.to_thread(db.add_tag, uid, "in_staff")
        await asyncio.to_thread(db.event, uid, "in_staff", f"joined:{cm.chat.id}")
        log.info("STAFF_JOIN user %s chat %s (%r)", uid, cm.chat.id, cm.chat.title)
        # Вступление в канал НЕ запускает welcome-цепочку: «вступил мимо
        # сайта» это не «зарегистрировался». Цепочки стартуют ТОЛЬКО от
        # регистрации (deep-link с ключом воронки)


# --- Вход №1: заявка на вступление → ЛС в окне 5 мин → approve ---
async def on_join_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    user = req.from_user
    funnel_key = None
    join_src_tag = ""
    if req.invite_link and req.invite_link.name:
        name = req.invite_link.name.strip()
        funnel_key = rt.resolve(name) or (name if name in rt.funnels else None)
        # Меченая ссылка вида «события-<слаг-статьи>»: дефис = маркер источника,
        # как в /start (parse_start_payload). База резолвится в воронку, хвост
        # уходит тегом src:<слаг> - у каждой SEO-статьи своя закрытая ссылка,
        # аналитика по статьям без размножения воронок
        if not funnel_key and "-" in name:
            base, join_src_tag = parse_start_payload(name)
            funnel_key = rt.resolve(base)
            if not funnel_key:
                join_src_tag = ""
    # Закрытый канал события: заявка по НАШЕЙ ссылке = мгновенный approve
    # + тег in_staff (гасит K-дожимы фронт-цепочки). Заявки по меченым
    # ссылкам основного бота и прочую органику НЕ трогаем - см. защиту ниже.
    link = (req.invite_link.invite_link if req.invite_link else "") or ""
    if LIVE_STAFF_HASH and LIVE_STAFF_HASH in link:
        db.upsert_contact(user.id, user.username, user.first_name, "staff_join")
        db.add_tag(user.id, "in_staff")
        db.event(user.id, "in_staff", "join_request")
        try:
            await ctx.bot.approve_chat_join_request(req.chat.id, user.id)
            log.info("STAFF_APPROVE user %s chat %s", user.id, req.chat.id)
        except Exception as e:
            log.warning("staff approve failed user %s: %s", user.id, e)
        # welcome тут НЕ стартуем: автоапрув мгновенный и немой,
        # цепочки идут только от регистрации
        return
    # 🔴 Защита реального канала: трогаем ТОЛЬКО заявки по нашим меченым ссылкам.
    # Органические заявки (без нашей воронки) не одобряем и не пишем - пусть их
    # обрабатывает штатный механизм канала (конструктор воронок/ручное), мы не вмешиваемся.
    if not funnel_key:
        if AUTO_APPROVE_ALL:
            # клон-инстанс autoapprove-бота: органика тут - норма (канал без своей
            # воронки), задача бота - только снять заявку с модерации и завести
            # контакт в базу. Воронку НЕ стартуем (funnel_key нет и не будет).
            if not _join_allowed(user.id):
                # per-user дедуп (не пере-approve одного и того же чаще раза в час)
                # оставляем как есть - защищает от повторных дублей апдейтов TG.
                # А вот ГЛОБАЛЬНЫЙ лимит здесь не должен молча дропать саму заявку:
                # человек не попадёт в канал, если промолчать - approve всё равно,
                # только фиксируем перегруз варнингом для последующего разбора.
                log.warning("autoapprove: заявка %s мимо rate-limit (глобальный лимит), approve всё равно", user.id)
            db.upsert_contact(user.id, user.username, user.first_name, "autoapprove")
            try:
                await ctx.bot.approve_chat_join_request(req.chat.id, user.id)
            except Exception as e:
                log.warning("autoapprove: approve failed: %s", e)
            return
        log.info("организическая заявка %s - игнор (не наша меченая ссылка)", user.id)
        return
    # анти-абьюз: массовые заявки по публичной ссылке = спам-усилитель + flood-бан
    if not _join_allowed(user.id):
        log.warning("заявка %s отброшена rate-limit (дедуп/глобальный лимит)", user.id)
        return
    db.upsert_contact(user.id, user.username, user.first_name, funnel_key)
    if join_src_tag:
        db.add_tag(user.id, f"src:{join_src_tag}")
    db.event(user.id, "join", f"{funnel_key}#{join_src_tag}" if join_src_tag else funnel_key)
    # заявка по НАШЕЙ меченой ссылке = возврат (симметрично on_start/on_text): снимаем
    # opted_out, иначе ранее написавший «стоп» впускается в канал, но A0 (лид-магнит)
    # не уходит - _run видит opted_out и молча возвращает True без отправки.
    db.set_flag(user.id, "opted_out", False)
    if funnel_key == FRONT_FUNNEL_KEY:
        await asyncio.to_thread(_mute_parallel_dozhim, user.id)
    # СНАЧАЛА пишем A0 в ЛС (user_chat_id, окно 5 мин), ПОТОМ approve. A0 идёт живым
    # send (не scheduled_job), после approve DM-окно закрывается и переотправить нечем -
    # потому при сетевом сбое (_run=False) делаем один повтор перед approve, чтобы не
    # терять магнит безвозвратно. approve всё равно проходит (не подвешиваем заявку).
    ok = await _run(ctx.bot, user.id, funnel_key, Event("enter", rt.now()))
    if not ok:
        ok = await _run(ctx.bot, user.id, funnel_key, Event("enter", rt.now()))
        if not ok:
            log.warning("A0 юзеру %s не доставлен после ретрая (сетевой сбой) - approve всё равно", user.id)
    try:
        await ctx.bot.approve_chat_join_request(req.chat.id, user.id)
    except Exception as e:
        log.warning("approve failed: %s", e)


# --- Бот стал/перестал быть админом канала: запоминаем chat_id ---
async def on_my_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if not cm:
        return
    chat = cm.chat
    status = cm.new_chat_member.status
    if chat.type in ("channel", "supergroup", "group"):
        log.info("MY_CHAT_MEMBER chat_id=%s type=%s title=%r status=%s",
                 chat.id, chat.type, chat.title, status)
        with open("channels.log", "a") as f:
            f.write(f"{chat.id}\t{chat.type}\t{chat.title}\t{status}\n")


async def on_channel_post(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if post:
        log.info("CHANNEL_POST chat_id=%s title=%r", post.chat.id, post.chat.title)
        with open("channels.log", "a") as f:
            f.write(f"{post.chat.id}\t{post.chat.type}\t{post.chat.title}\tpost\n")


# Ответ на переброс из платформы курса после регистрации (start=KEY)
REGISTERED_WELCOME = ("Регистрацию вижу, ты в деле 🤝\n\n"
                      "Больше напоминать про событие не буду. "
                      "Если что-то не открывается - напиши @ud25187")


VIP_WELCOME_FALLBACK = ("Оплату вижу, VIP твой 🤝\n\n"
                        "Если что-то не открывается - напиши @ud25187")


# МОСТ В СОСЕДНИЙ БОТ. Welcome-цепочки второго запуска могут жить не здесь, а в
# другом боте. Тогда тут остаётся короткое сообщение с кнопкой в правильный бот и
# с тем же payload, что пришёл сюда (адрес бота - в LIVE_BRIDGE_BOT_USERNAME)
LIVE_BRIDGE_BOT_USERNAME = "event_bot"

LIVE_BRIDGE_TEXT = ("Регистрацию вижу, ты в деле 🤝\n\n"
                     "Все материалы ждут тебя в другом боте - жми кнопку "
                     "ниже и забирай")

LIVEVIP_BRIDGE_TEXT = ("Оплату вижу, VIP-доступ твой 🤝\n\n"
                        "Все материалы ждут тебя в другом боте - жми кнопку ниже и "
                        "открывай доступ")


def _live_bridge_markup(start_payload):
    """Кнопка-мост в welcome-бот события с тем же payload, что пришёл сюда."""
    url = _dl(start_payload, host=tg_url(LIVE_BRIDGE_BOT_USERNAME))
    label = "Открыть доступ" if start_payload == "livevip" else "Забрать материалы"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, url=url)]])


def _welcome_for(user_id):
    """Актуальная welcome-цепочка ДЛЯ ЭТОГО человека.

    Зачем развилка. Когда запусков было два, ветка «registered -> WELCOME» знала
    только про первый. Лид второго запуска, у которого тег registered остался с
    первого, при клике выдёргивался в цепочку закрытого потока, а её кнопка вела
    в кабинет, который для него уже недоступен.

    Правило: отдаём цепочку того запуска, в котором человек РЕАЛЬНО сидит.
    Приоритет у текущего запуска. Ничего не подошло = None, и
    вызывающий не подменяет воронку вообще (кнопка в никуда хуже её отсутствия).
    """
    tags = db.tags(user_id)
    for cand in ("LIVEVIPWELCOME", "LIVEWELCOME", "VIPWELCOME", "WELCOME"):
        if "f_" + cand in tags and cand in rt.funnels:
            return cand
    # следов входа нет: ориентируемся на тег vip и текущий запуск (события)
    fallback = ("LIVEVIPWELCOME", "LIVEWELCOME") if "vip" in tags else ("LIVEWELCOME",)
    for cand in fallback:
        if cand in rt.funnels:
            return cand
    return None


# Служебные payload'ы /start, которые обрабатываются ДО резолва воронок.
# Каждый из них перекрывает одноимённый translit-алиас воронки, если такой есть:
# у запуска алиас совпадает с ключом воронки, то есть голая ссылка с этим
# ключом уходит в служебную ветку (registered + cancel_all + welcome),
# а не в воронку.
#
# ПРИНЯТЫЙ РИСК, ветки НЕ сужаем. Разобрано по боевой базе:
# служебный путь дал считанные события за всё время (возврат с платформы
# курса, один притянул в базу нового человека), вреда ноль; параллельный
# вебхук /hooks/gc-registered за всё время поставил ровно 1 тег, то есть НЕ
# покрывает задачу. Потерянный или ложный registered дороже этого дефекта,
# поэтому поведение оставлено байт-в-байт. Взамен - детектор ниже: он ничего
# не меняет, только помечает в лог случай, похожий на обрезанную ссылку
# (у человека есть ЖИВОЙ дожим той воронки, чей алиас перекрыт).
SERVICE_START_PAYLOADS = ("registered", "vip", "live", "livevip",
                          "livetest", "liveviptest")


def _warn_if_payload_shadows_funnel(user_id, payload):
    """Служебный payload перекрыл алиас живой воронки - записать в лог.

    Поведение НЕ меняет ни на байт (только log.warning): решение по цене ошибки -
    терять registered нельзя, а отличить возврат с платформы курса от обрезанной ссылки
    на входе физически невозможно, payload у них дословно одинаковый. Детектор
    нужен, чтобы принятый риск перестал быть немым: если такие строки пойдут
    пачкой, значит ссылку где-то опубликовали обрезанной.
    """
    try:
        key = rt.resolve(payload)
        if not key:
            return
        if db.has_pending(user_id, key):
            log.warning("start=%s: служебная ветка перекрыла алиас воронки %s, "
                        "а у %s ЖИВОЙ дожим этой воронки - похоже на обрезанную "
                        "ссылку, а не возврат с платформы курса", payload, key, user_id)
    except Exception as e:      # детектор не имеет права уронить контур регистрации
        log.warning("детектор перекрытого алиаса упал (контур не тронут): %s", e)


# --- Вход №2: deep-link /start <funnel_key> ---
async def on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if _is_blocked(user):
        return
    args = ctx.args or []
    low0 = args[0].strip().lower() if args else ""
    if low0 in SERVICE_START_PAYLOADS:
        _warn_if_payload_shadows_funnel(user.id, low0)
    if args and args[0].strip().lower() == "registered":
        # человек пришёл со страницы «после регистрации» платформы курса:
        # честный registered без вебхука + затягиваем в базу даже тех,
        # кто попал на лендинг мимо бота
        db.upsert_contact(user.id, user.username, user.first_name, "gc_redirect")
        db.set_flag(user.id, "opted_out", False)
        db.add_tag(user.id, "registered")
        db.cancel_all(user.id)
        db.event(user.id, "registered", "gc_redirect")
        await asyncio.to_thread(crossdb.tag_neighbor, user.id, "registered")
        await asyncio.to_thread(suppression.add_safe, user.id, "registered", "gc_redirect")
        if "WELCOME" in rt.funnels:
            # welcome-цепочка живёт в боте: A1 сразу + хвост по таймингам
            await _run(ctx.bot, user.id, "WELCOME", Event("enter", rt.now()))
        else:
            await update.message.reply_text(REGISTERED_WELCOME)
        return
    if args and args[0].strip().lower() == "vip":
        # переброс после ОПЛАТЫ VIP: тег vip гасит апселл/анкету welcome-ветки
        # (подготовка A11/A12 доживает), registered гасит фронт-дожим
        db.upsert_contact(user.id, user.username, user.first_name, "gc_vip")
        db.set_flag(user.id, "opted_out", False)
        db.add_tag(user.id, "registered")
        db.add_tag(user.id, "vip")
        db.event(user.id, "vip", "gc_redirect")
        # алерт о новом VIP убран: входы видны в кабинете платформы,
        # админу шлём только когда что-то падает
        await asyncio.to_thread(crossdb.tag_neighbor, user.id, "registered")
        await asyncio.to_thread(suppression.add_safe, user.id, "registered", "gc_redirect_vip")
        if "VIPWELCOME" in rt.funnels:
            await _run(ctx.bot, user.id, "VIPWELCOME", Event("enter", rt.now()))
        else:
            await update.message.reply_text(VIP_WELCOME_FALLBACK)
        return
    if args and args[0].strip().lower() == "live":
        # переброс с платформы курса после БЕСПЛАТНОЙ регистрации (зеркало
        # ветки registered). МОСТ: welcome-цепочка живёт только в соседнем
        # боте, тут - кнопка туда с тем же payload.
        # Теги/событие ниже НЕ трогаем - они гасят продающий дожим запуска.
        db.upsert_contact(user.id, user.username, user.first_name, "gc_live")
        db.set_flag(user.id, "opted_out", False)
        db.add_tag(user.id, "registered")
        db.cancel_all(user.id)
        db.event(user.id, "registered", "gc_live")
        await asyncio.to_thread(crossdb.tag_neighbor, user.id, "registered")
        await asyncio.to_thread(suppression.add_safe, user.id, "registered", "gc_live")
        await update.message.reply_text(LIVE_BRIDGE_TEXT,
                                        reply_markup=_live_bridge_markup("live"))
        return
    if args and args[0].strip().lower() == "livevip":
        # переброс после оплаты VIP-тарифа. МОСТ: welcome-цепочка живёт
        # только в соседнем боте, тут - кнопка туда с тем же payload.
        # Теги/событие ниже НЕ трогаем.
        db.upsert_contact(user.id, user.username, user.first_name, "gc_livevip")
        db.set_flag(user.id, "opted_out", False)
        db.add_tag(user.id, "registered")
        db.add_tag(user.id, "vip")
        db.event(user.id, "vip", "gc_livevip")
        # алерт о новом VIP убран: входы видны в кабинете платформы,
        # админу шлём только когда что-то падает
        await asyncio.to_thread(crossdb.tag_neighbor, user.id, "registered")
        await asyncio.to_thread(suppression.add_safe, user.id, "registered", "gc_livevip")
        await update.message.reply_text(LIVEVIP_BRIDGE_TEXT,
                                        reply_markup=_live_bridge_markup("livevip"))
        return
    if args and args[0].strip().lower() in ("livetest", "liveviptest"):
        # Тест-прогон welcome события для АДМИНА: все узлы подряд с паузой ~1с,
        # без тегов/дожимов/боевых таймеров/окна отправки. Чужим - молчок.
        if not _is_admin(update):
            return
        key = "LIVEWELCOME" if args[0].strip().lower() == "livetest" else "LIVEVIPWELCOME"
        f = rt.funnels.get(key)
        if not f:
            await update.message.reply_text(f"тест: воронка {key} не загружена")
            return
        order = ["A1", "A11", "A2"] if key == "LIVEWELCOME" else ["B1", "B2"]
        timings = {"A1": "сразу", "A11": "+15 мин", "A2": "+45 мин (≈1 ч, финал)",
                   "B1": "сразу", "B2": "+3 ч (финал)"}
        await update.message.reply_text(
            f"ТЕСТ {key}: сейчас все узлы придут подряд. Боевой тайминг каждого - строкой перед ним")
        for nk in order:
            n = f.nodes.get(nk)
            if not n:
                continue
            await ctx.bot.send_message(user.id, f"[{nk} · боевой тайминг: {timings.get(nk, '?')}]")
            send = SendAction(node_key=nk, at=rt.now(), text=n.text, buttons=n.buttons,
                              attachment_type=n.attachment_type or "",
                              attachment_url=n.attachment_url or "")
            await _send_node(ctx.bot, user.id, key, send)
            await asyncio.sleep(1)
        await ctx.bot.send_message(user.id, "ТЕСТ завершён: это был предпросмотр, теги не ставились")
        return
    # deep-link source-тег: event-<тег> = воронка event + метка src:<тег>.
    # Резолвим ТОЛЬКО funnel-часть (до дефиса), поэтому ссылка с ключом воронки
    # входит в ту же воронку СОБЫТИЕ, а не падает в заглушку. Голый event
    # (без дефиса) даёт tag='' и ведёт себя ровно как раньше.
    base, src_tag = parse_start_payload(args[0]) if args else ("", "")
    key = rt.resolve(base) if base else None
    resolved_by_word = key is not None       # тег пишем только на реальный резолв, не на default
    if key == FRONT_FUNNEL_KEY and "registered" in db.tags(user.id) and _welcome_for(user.id):
        # ОБХОД кривого редиректа платформы у зарегистрированных: человек уже
        # помечен registered -> ему welcome, а не продажа по кругу. Цепочку
        # выбираем ПО ЗАПУСКУ, в котором человек сидит, а не жёстко WELCOME -
        # иначе лид текущего запуска уезжал в цепочку закрытого потока, а её
        # кнопка вела в кабинет, который ему уже недоступен.
        key = _welcome_for(user.id)
    if not key and DEFAULT_FUNNEL_KEY and DEFAULT_FUNNEL_KEY in rt.funnels:
        # фронт-бот: голый /start (без хвостика или с неизвестным) = вход в
        # дефолтную воронку, а не тупиковая заглушка. Прецедент: ученик
        # открыл бота вручную после поста и упёрся в «зайди по ссылке»
        key = DEFAULT_FUNNEL_KEY
    if key:
        db.set_flag(user.id, "opted_out", False)   # вход по deep-link = возврат
        db.upsert_contact(user.id, user.username, user.first_name, key)
        if src_tag and resolved_by_word:
            db.add_tag(user.id, f"src:{src_tag}")   # источник касания (конструктор воронок/канал/слово)
        db.event(user.id, "start", f"{key}#{src_tag}" if (src_tag and resolved_by_word) else key)
        if key == FRONT_FUNNEL_KEY:
            await asyncio.to_thread(_mute_parallel_dozhim, user.id)
        else:
            await asyncio.to_thread(db.cancel_other_funnels, user.id, key)   # один дожим за раз
        # Deep-link вход: человек сам стартовал бота, шлюз «Забрать» (разлочка
        # для канального входа, где юзер обязан сам ответить боту) здесь - лишнее
        # нулевое касание. Сразу проводим B0, дожим идёт без ручного клика (18.08).
        # у воронок DIRECT_ENTRY_FUNNELS на этом пути НЕ шлём и сам A0 -
        # человек пришёл по осознанной ссылке и получает РОВНО одно сообщение,
        # узел B0 (его текст переписан под первый экран). A0 при этом проводится
        # движком (состояние + ребро A0→R1), гасится только отправка. Автогейт
        # считаем ДО enter: решение о подавлении нужно принять раньше отправки.
        # Прочим воронкам не меняем НИЧЕГО - их B0 написаны репликами-ответами
        # («как договорились», «финишная прямая») и первым экраном = обрывок.
        b0 = rt.funnels[key].nodes.get("B0")
        autogate = bool(b0 and b0.condition and b0.condition != "#{none}"
                        and not b0.condition.startswith("link_was_pressed"))
        skip = {"A0"} if (autogate and key in DIRECT_ENTRY_FUNNELS) else None
        await _run(ctx.bot, user.id, key, Event("enter", rt.now()), skip_nodes=skip)
        if autogate:
            await _run(ctx.bot, user.id, key, Event("button", rt.now(), payload=b0.condition))
    else:
        await update.message.reply_text(
            "Привет! Это бот-воронка. Зайди по ссылке-приглашению или напиши кодовое слово")


# --- Вход №3: слово в ЛС + reply-кнопка «Забрать» как текст ---
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if _is_blocked(user):
        return
    text = (update.message.text or "").strip()
    low = text.lower()
    # админ вводит текст рассылки после /broadcast
    if _is_admin(update) and _draft.get(user.id, {}).get("await_text"):
        await _broadcast_capture(update, ctx)
        return
    if low in ("стоп", "stop"):
        # гасим все активные воронки юзера
        db.set_flag(user.id, "opted_out", True)
        db.cancel_all(user.id)
        await update.message.reply_text("Ок, больше не пишу. Захочешь вернуться - просто напиши слово")
        return
    # если это кодовое слово (кириллица или латинский alias) - старт воронки
    key = rt.resolve(text)
    if key == FRONT_FUNNEL_KEY and "registered" in db.tags(user.id) and _welcome_for(user.id):
        # ОБХОД кривого редиректа платформы у зарегистрированных: человек уже
        # помечен registered -> ему welcome, а не продажа по кругу. Цепочку
        # выбираем ПО ЗАПУСКУ, в котором человек сидит, а не жёстко WELCOME -
        # иначе лид текущего запуска уезжал в цепочку закрытого потока, а её
        # кнопка вела в кабинет, который ему уже недоступен.
        key = _welcome_for(user.id)   # зарегистрированному - ЕГО welcome, не продажа по кругу
    if key:
        was_opted = db.flags(user.id)[0]
        # повторный ввод активной воронки (не после «стоп») = напоминание A0 без
        # перезапуска дожима: иначе повторно уедут уже пройденные C/D-узлы
        if not was_opted and db.has_pending(user.id, key):
            db.event(user.id, "reenter", key)
            await _run(ctx.bot, user.id, key, Event("reenter", rt.now()))
            return
        db.set_flag(user.id, "opted_out", False)   # вход словом = возврат, снимаем отписку
        db.upsert_contact(user.id, user.username, user.first_name, key)
        db.event(user.id, "word", key)
        if key == FRONT_FUNNEL_KEY:
            await asyncio.to_thread(_mute_parallel_dozhim, user.id)
        else:
            # один активный дожим за раз: гасим дожимы прочих воронок юзера
            await asyncio.to_thread(db.cancel_other_funnels, user.id, key)
        await _run(ctx.bot, user.id, key, Event("enter", rt.now()))
        return
    # иначе - возможно нажата reply-кнопка активной воронки (напр. «Забрать»).
    # Валидируем: текст должен быть кнопкой ТЕКУЩЕГО узла (не самопродвижение произвольным текстом)
    key = db_active_funnel(user.id)
    if key and rt.valid_button(user.id, key, text):
        await _run(ctx.bot, user.id, key, Event("button", rt.now(), payload=text))
        return
    # Мёртвая кнопка «Забрать» у воронок DIRECT_ENTRY_FUNNELS: человек уже в B0,
    # а reply-клавиатура с A0/R1/R2 висит у него в чате. valid_button её не
    # пропускает (у B0 единственная кнопка - url-овая, а он требует кнопку БЕЗ
    # url у ТЕКУЩЕГО узла), и нажатие падало в ИИ-ответчик - живая жалоба
    # «Нет кнопки забрать» (user 1176097012, 20.08). Отдаём B0 повторно: человек
    # снова получает ссылку. Узко: только эти воронки, только состояние B0,
    # только дословный текст condition B0 - самопродвижение произвольным текстом
    # по-прежнему невозможно, B0 исходящих рёбер не имеет, дожим не сдвинется.
    if key and rt.reissue_b0_button(user.id, key, text):
        await _run(ctx.bot, user.id, key, Event("button", rt.now(), payload=text))
        return
    # не слово, не кнопка, не команда = живой вопрос/реплика человека.
    # Гард админа: свободный текст автора мимо команд НЕ должен уходить в ИИ (иначе
    # бот продаёт событие самому автору и жжёт лимит) - просто форвард как до ИИ.
    if _is_admin(update):
        await _forward_to_admin(ctx.bot, update)
        return
    # Лог входящего - ВСЕГДА, даже при выключенном ИИ (иначе ai_history потом
    # не увидит это сообщение, если ИИ включат позже).
    await asyncio.to_thread(db.ai_log, user.id, "user", text)
    if await asyncio.to_thread(_ai_enabled):
        task = asyncio.create_task(_ai_task(ctx.bot, user.id, user.first_name, text))
        _AI_TASKS.add(task)
        task.add_done_callback(_AI_TASKS.discard)
    else:
        await _forward_to_admin(ctx.bot, update)


def db_active_funnel(user_id):
    r = db._c.execute("SELECT funnel_key FROM funnel_state WHERE user_id=? ORDER BY entered_at DESC LIMIT 1",
                     (user_id,)).fetchone()
    return r["funnel_key"] if r else None


async def _forward_to_admin(bot, update):
    """Неопознанный текст (не слово, не кнопка) пересылаем админу с контекстом."""
    if not ADMIN_CHAT_ID:
        return
    user = update.effective_user
    if _is_blocked(user):   # спамер из игнор-листа - админу не показываем
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    text = text[:2000]   # обрезаем, не дропаем (штатный режим при выключенном ИИ)
    # Форвард с инфо: кто писал, какой ID, сам текст. parse_mode=HTML -> теги <b>, не *
    msg = f"<b>От:</b> {html.escape(user.first_name or 'Аноним')} (@{user.username or 'нет'})\n<b>ID:</b> {user.id}\n\n{html.escape(text)}"
    try:
        await bot.send_message(ADMIN_CHAT_ID, msg, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"forward_to_admin failed: {e}")


async def _forward_raw_to_admin(bot, user_id, first_name, text, reply_count=None):
    """Тот же формат форварда что _forward_to_admin, но без Update - для путей ИИ
    (лимит исчерпан / сбой API / postguard брак): лид не должен теряться молча.
    Длинный текст ОБРЕЗАЕМ по границе строки, не дропаем (пачка склеенных unanswered
    легко >2000), и помечаем сколько реплик обрезано - курсор двигается на всё, а
    полный текст всегда в ai_dialog (админ достанет /who). reply_count = сколько
    реплик лида в исходной пачке (для честной пометки, если задано)."""
    if not ADMIN_CHAT_ID:
        return
    text = (text or "").strip()
    if not text:
        return
    if len(text) > 2000:
        cut = text[:2000]
        nl = cut.rfind("\n")
        cut = cut[:nl] if nl > 0 else cut   # режем по последней строке, не посреди реплики
        # оценка сверху: считаем физические строки, не реплики (многострочная реплика
        # завысит shown -> «ещё N» занижено). Направление ошибки безопасное, полный
        # текст в ai_dialog - точность здесь не критична
        shown = cut.count("\n") + 1
        tail = (f" ещё {reply_count - shown} реплик" if reply_count and reply_count > shown
                else " продолжение")
        text = cut + f"\n\n[...обрезано,{tail}, полностью в ai_dialog]"
    msg = f"<b>От:</b> {html.escape(first_name or 'Аноним')} (@нет)\n<b>ID:</b> {user_id}\n\n{html.escape(text)}"
    try:
        await bot.send_message(ADMIN_CHAT_ID, msg, parse_mode="HTML")
    except Exception as e:
        logging.warning(f"forward_raw_to_admin failed: {e}")


# --- ИИ-ответчик: фоновый таск на живое сообщение лида (см. ai_responder.py) ---
_AI_TASKS = set()              # анти-GC для fire-and-forget тасков
_AI_LOCKS = {}                 # user_id -> asyncio.Lock (ботов мало, чистку не делаем)
_AI_DEBOUNCE_SEC = 2            # коалесценция быстрых сообщений подряд в один вызов Claude


def _ai_enabled():
    """ИИ включён = ключ задан И kill-switch в БД не выключил (ai_kv "ai_enabled",
    дефолт из config.AI_ENABLED - только сид при первом чтении)."""
    if not ANTHROPIC_API_KEY:
        return False
    return db.ai_kv_get("ai_enabled", AI_ENABLED) == "1"


def _ai_lock(user_id):
    lock = _AI_LOCKS.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _AI_LOCKS[user_id] = lock
    return lock


def _user_registered(user_id):
    return "registered" in db.tags(user_id)


def _user_guide_url(funnel_key):
    """B0-узел воронки юзера -> прямой url первой url-кнопки (НЕ wrap_button_url -
    ИИ-ответ не должен ходить через redirect_links/клик-трекинг воронки, топ-2
    находки критики плана). Нет воронки/нет B0 -> ''."""
    if not funnel_key:
        return ""
    f = rt.funnels.get(funnel_key)
    if not f:
        return ""
    node = f.nodes.get("B0")
    if not node:
        return ""
    b = node.url_button
    return b.url if b else ""


def _load_ai_catalog():
    """Каталог гайдов -> ai_responder: (ключ, код-слово, A0-текст, url гайда).

    Зачем каталог. Лид без записи в contacts/funnel_state называет тему, гайд под
    неё в воронках есть, но модель о существовании гайдов не знает и отвечает «это
    не моя тема». Каталог собирается из ТЕХ ЖЕ загруженных
    воронок (rt.funnels), url берём из B0-кнопки - как _user_guide_url, без
    redirect-трекинга. Берём только воронки с код-словом (A0.condition) и живой
    ссылкой: служебные WELCOME/VIPWELCOME сами отсеются.
    """
    entries = []
    for key, f in rt.funnels.items():
        a0 = f.nodes.get("A0")
        b0 = f.nodes.get("B0")
        if not (a0 and a0.condition and b0):
            continue
        btn = b0.url_button
        if not (btn and btn.url):
            continue
        entries.append((key, a0.condition.strip(), a0.text or "", btn.url))
    n = ai_responder.set_catalog(entries)
    log.info("ai catalog: %s гайдов доступно для выдачи по теме", n)
    return n


async def _ai_task(bot, user_id, first_name, raw_text_for_fallback):
    """Обрабатывает живое сообщение лида через Claude. Дебаунс + лимиты под
    per-user локом (TOCTOU закрыт), любой сбой -> сырой форвард админу, лид не
    теряется молча. Вся функция в try/except - таск фоновый, исключение не должно
    всплыть незамеченным."""
    try:
        async with _ai_lock(user_id):
            await asyncio.sleep(_AI_DEBOUNCE_SEC)
            # ЕДИНЫЙ снимок (id,text) на весь таск: и промпт, и overflow, и граница
            # курсора берутся из НЕГО. Никаких повторных чтений ai_unanswered - иначе
            # параллельная запись в зазор между снимками теряет старейшее (R6).
            snapshot = await asyncio.to_thread(db.ai_unanswered_with_ids, user_id)
            if not snapshot:
                return   # уже ответил параллельный таск (коалесценция) - курсор НЕ двигаем

            unanswered = [t for _id, t in snapshot]
            # max_id = id ПОСЛЕДНЕГО из снятого списка (не MAX по всей БД): всё что
            # записалось после снимка (id>max_id) останется unanswered и подхватится
            # следующим таском, не потеряется и не будет ложно «покрыто» курсором
            max_id = snapshot[-1][0]

            async def _mark():
                await asyncio.to_thread(db.ai_answered_upto_set, user_id, max_id)

            h, d, g = await asyncio.to_thread(db.ai_counts, user_id)
            if h >= AI_HOURLY_PER_USER or d >= AI_DAILY_PER_USER or g >= AI_DAILY_GLOBAL:
                # форвардим ВСЕ неотвеченные (не кэпленные) = обработали, повторно не слать
                await _forward_raw_to_admin(bot, user_id, first_name, "\n".join(unanswered),
                                            reply_count=len(unanswered))
                await _mark()
                return

            opted, banned = await asyncio.to_thread(db.flags, user_id)
            if banned:
                return   # заблокировал бота - НЕ двигаем курсор (ни ответа, ни форварда)
            if opted:
                # отписавшийся написал живой текст: ИИ молчит (человек просил не писать),
                # но админ видит - так было и до ИИ (_forward_to_admin), не терять
                await _forward_raw_to_admin(bot, user_id, first_name, "\n".join(unanswered),
                                            reply_count=len(unanswered))
                await _mark()
                return

            # 🔴 ТЕХНИЧЕСКИЙ ПРЕДОХРАНИТЕЛЬ: командное сообщение-действие
            # НЕ доходит до модели вообще. Не «бот вежливо откажет», а системный блок на
            # входе: Claude не вызывается, токены не тратятся, шанса отреагировать на
            # команду нет. Курсор двигаем (обработано), лиду молчим, админу тихий флаг.
            # (Фундамент и так железный: у бота нет tools - действие физически невозможно.)
            if any(ai_responder.is_command_attempt(t) for t in unanswered):
                log.info("ai command-attempt заблокирована ДО модели, user %s", user_id)
                await _mark()
                return

            funnel_key = await asyncio.to_thread(db_active_funnel, user_id)
            node = await asyncio.to_thread(db.get_state, user_id, funnel_key) if funnel_key else None
            registered = await asyncio.to_thread(_user_registered, user_id)
            guide_url = _user_guide_url(funnel_key)

            # кэп промпта считаем ЗДЕСЬ из снятого списка: последние 10 -> в ответ ИИ,
            # старейшие сверх -> overflow. Обе части из ОДНОГО snapshot, курсор честен
            sent_to_ai = unanswered[-10:]
            overflow = unanswered[:-10]

            # участник живого события? правда лежит в БД соседа (LIVE*-воронки).
            # Read-only, сбой = None = старое поведение
            live_state = await asyncio.to_thread(crossdb.neighbor_live_state, user_id)

            reply, reason = await ai_responder.generate_reply(
                db, user_id, first_name, funnel_key, node, registered, guide_url,
                sent_to_ai, cabinet_url=WELCOME_CABINET_URL, live_state=live_state)
            if reply is None:
                # 'error' (сбой API/сети) - лид не обслужен, форвардим админу (не терять).
                # 'guard' (постгард забраковал = провокация/инъекция/выдумка) - лиду не
                # отвечаем И админу НЕ форвардим (это шум-атака, не потерянный лид);
                # курсор двигаем - обработано, повторно не гонять.
                if reason == "error":
                    await _forward_raw_to_admin(bot, user_id, first_name, "\n".join(unanswered),
                                                reply_count=len(unanswered))
                else:
                    log.info("ai guard-blocked (провокация/инъекция) user %s - не форвардим", user_id)
                await _mark()
                return

            await bot.send_message(user_id, reply, link_preview_options=NOPREVIEW)
            await asyncio.to_thread(db.ai_log, user_id, "assistant", reply)
            # sent_to_ai (последние 10) -> в ответ ИИ; overflow (старейшие сверх 10) ->
            # форвард админу ПЕРЕД сдвигом курсора, иначе они молча пропадут.
            # Свой try/except: сбой доставки АДМИНУ (сеть/429) не должен откатить курсор
            # после успешной доставки ОТВЕТА юзеру - иначе следующий таск ответит повторно
            # (дубль юзеру + лишний вызов). Полный текст всё равно в ai_dialog.
            if overflow:
                try:
                    await _forward_raw_to_admin(
                        bot, user_id, first_name,
                        f"[+{len(overflow)} ранних сообщений лида, не вошли в ответ ИИ]:\n"
                        + "\n".join(overflow),
                        reply_count=len(overflow) + 1)
                except Exception as e:
                    log.warning("ai overflow forward failed user %s: %s", user_id, e)
            await _mark()   # реальный ответ ИИ - двигаем курсор ПОСЛЕ успешной отправки

            if ADMIN_CHAT_ID:
                # лимит Telegram 4096 на сообщение - режем обе части заранее
                q = html.escape("\n".join(unanswered)[:3500])
                a = html.escape(reply[:3500])
                name = html.escape(first_name or "Аноним")
                try:
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🤖 {name} ({user_id})\n❓ {q}\n💬 {a}",
                        parse_mode="HTML")
                except Exception as e:
                    log.warning("ai admin copy failed user %s: %s", user_id, e)
    except Exception as e:
        log.exception("_ai_task failed user %s: %s", user_id, e)
        try:
            await _forward_raw_to_admin(bot, user_id, first_name, raw_text_for_fallback)
        except Exception:
            pass


async def cmd_ai(update, ctx):
    """/ai on|off|status - kill-switch и статус ИИ-ответчика с телефона."""
    if not _is_admin(update):
        return
    args = ctx.args or []
    sub = (args[0].lower() if args else "status")
    if sub == "off":
        await asyncio.to_thread(db.ai_kv_set, "ai_enabled", "0")
        await update.message.reply_text("🤖 ИИ-ответчик выключен")
        return
    if sub == "on":
        await asyncio.to_thread(db.ai_kv_set, "ai_enabled", "1")
        await update.message.reply_text("🤖 ИИ-ответчик включён")
        return
    enabled = await asyncio.to_thread(_ai_enabled)
    glob_count, users_answered = await asyncio.to_thread(_ai_daily_stats)
    await update.message.reply_text(
        f"🤖 ИИ-ответчик: {'включён' if enabled else 'выключен'}\n"
        f"Модель: {AI_MODEL}\n"
        f"За сутки: {users_answered} юзеров, {glob_count} ответов "
        f"(лимит {AI_DAILY_GLOBAL})")


def _ai_daily_stats():
    since = time.time() - 86400
    glob_count = db._c.execute(
        "SELECT COUNT(*) FROM ai_dialog WHERE role='assistant' AND ts>?", (since,)).fetchone()[0]
    users_answered = db._c.execute(
        "SELECT COUNT(DISTINCT user_id) FROM ai_dialog WHERE role='assistant' AND ts>?",
        (since,)).fetchone()[0]
    return glob_count, users_answered


async def on_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Медиа в ЛС (фото/голосовое/кружок/файл) раньше молча исчезало - частый сценарий
    вопроса «фото с подписью что делать?». Caption есть -> ровно тот же путь что
    текстовый fallback on_text (ИИ отвечает на подпись). Caption нет -> лог-заглушка
    в ai_dialog + форвард админу (контент медиа мы не разбираем)."""
    user = update.effective_user
    if _is_blocked(user):
        return
    if _is_admin(update):
        # кружок/голосовое от автора - зафиксировать file_id (для welcome-цепочек:
        # админ шлёт кружок прямо боту, мы вшиваем file_id в узел A1)
        m = update.message
        if m is not None and (getattr(m, "video_note", None) or getattr(m, "voice", None)):
            att = m.video_note or m.voice
            kind = "video_note" if m.video_note else "voice"
            log.info("ADMIN_MEDIA %s file_id=%s", kind, att.file_id)
            with open("admin_media.log", "a") as f:
                f.write(f"{kind}\t{att.file_id}\n")
        return   # не мешать админ-потокам (broadcast ловит текст, но на всякий случай)
    msg = update.message
    if msg is None:
        return
    caption = (msg.caption or "").strip()
    if caption:
        await asyncio.to_thread(db.ai_log, user.id, "user", caption)
        if await asyncio.to_thread(_ai_enabled):
            task = asyncio.create_task(_ai_task(ctx.bot, user.id, user.first_name, caption))
            _AI_TASKS.add(task)
            task.add_done_callback(_AI_TASKS.discard)
        else:
            await _forward_raw_to_admin(ctx.bot, user.id, user.first_name, caption)
        return
    kind = ("фото" if msg.photo else "голосовое" if getattr(msg, "voice", None)
            else "кружок" if getattr(msg, "video_note", None)
            else "видео" if getattr(msg, "video", None)
            else "аудио" if getattr(msg, "audio", None) else "файл")
    await asyncio.to_thread(db.ai_log, user.id, "user", f"[прислал {kind}]")
    if ADMIN_CHAT_ID:
        try:
            await ctx.bot.send_message(
                ADMIN_CHAT_ID,
                f"[медиа без текста] от {html.escape(user.first_name or 'Аноним')} ({user.id})")
        except Exception as e:
            log.warning("media forward failed user %s: %s", user.id, e)


# --- inline-кнопки (callback) ---
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    if _is_blocked(user):
        return
    data = q.data or ""
    if data == "wsopt":
        # «Не в этот раз» (K3): глобальный стоп событие-дожимов
        await asyncio.to_thread(_optout_event, user.id)
        await ctx.bot.send_message(user.id, OPTOUT_CONFIRM)
        return
    if data.startswith("btn:"):
        label = data[4:]
        key = db_active_funnel(user.id)
        if key and rt.valid_button(user.id, key, label):
            await _run(ctx.bot, user.id, key, Event("button", rt.now(), payload=label))


# --- Админ-команды (только chat автора) ---
def _is_admin(update):
    # админ = владелец И только в личке: команда в группе/канале засветила бы
    # PII и управление рассылками всем участникам
    return (update.effective_user and update.effective_user.id == ADMIN_CHAT_ID
            and update.effective_chat and update.effective_chat.type == "private")


def _is_blocked(user):
    """Игнор-лист (config.BLOCKED_USER_IDS): апдейты спамера молча дропаем."""
    return bool(user) and user.id in BLOCKED_USER_IDS


async def cmd_stats(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    keys = [args[0]] if args and rt.resolve(args[0]) else list(rt.funnels.keys())
    lines = []
    for raw in keys:
        k = rt.resolve(raw) or raw
        s = db.funnel_stats(k)
        if not s["entered"]:
            continue
        conv = round(100 * s["registered"] / s["entered"]) if s["entered"] else 0
        gc = round(100 * s["clicked_guide"] / s["entered"]) if s["entered"] else 0
        lines.append(
            f"<b>{html.escape(k)}</b>: вошло {s['entered']} → гайд забрали {s['got_b0']} → "
            f"кликнули {s['clicked_guide']} ({gc}%) → рег {s['registered']} ({conv}%), "
            f"отписки {s['opted_out']}")
    if not lines:
        lines = ["пока нет входов ни в одну воронку"]
    await update.message.reply_text("📊 Статистика воронок\n\n" + "\n".join(lines),
                                    parse_mode=ParseMode.HTML)


async def cmd_who(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text("Формат: /who <user_id>")
        return
    card = db.contact_card(int(args[0]))
    if not card["contact"]:
        await update.message.reply_text("контакт не найден")
        return
    c = card["contact"]
    esc = html.escape
    st = "; ".join(f"{esc(s['funnel_key'])}={esc(s['node'] or '-')}" for s in card["states"]) or "-"
    tags = ", ".join(esc(t) for t in card["tags"]) or "-"
    await update.message.reply_text(
        f"👤 {c['user_id']} @{esc(c.get('username') or '-')}\n"
        f"источник: {esc(c.get('source_funnel') or '-')}\n"
        f"состояние: {st}\nтеги: {tags}\n"
        f"pending-джобов: {card['pending_jobs']}\n"
        f"opted_out={bool(c['opted_out'])} banned={bool(c['banned_bot'])}",
        parse_mode=ParseMode.HTML)


async def cmd_reset(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    if len(args) < 2 or not args[0].isdigit():
        await update.message.reply_text("Формат: /reset <user_id> <воронка>")
        return
    uid = int(args[0]); k = rt.resolve(args[1]) or args[1]
    db.reset_contact(uid, k)
    await update.message.reply_text(f"сброшен {uid} в воронке {k} - пройдёт заново")


async def cmd_tag(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    if len(args) < 2 or not args[0].isdigit():
        await update.message.reply_text("Формат: /tag <user_id> <тег> | /untag <user_id> <тег>")
        return
    uid = int(args[0]); tag = args[1]
    if update.message.text.startswith("/untag"):
        db.remove_tag(uid, tag); await update.message.reply_text(f"снят тег {tag} у {uid}")
    else:
        db.add_tag(uid, tag); await update.message.reply_text(f"добавлен тег {tag} у {uid}")


async def cmd_suppress(update, ctx):
    """Ручное добавление в общий реестр исключений (все 7 ботов перестанут слать)."""
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Формат: /suppress <user_id> [причина]")
        return
    uid = int(args[0])
    reason = args[1] if len(args) > 1 else "manual"
    await asyncio.to_thread(suppression.add, uid, reason, "admin")
    await update.message.reply_text(f"{uid} добавлен в реестр исключений (reason={reason})")


async def cmd_unsuppress(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Формат: /unsuppress <user_id>")
        return
    uid = int(args[0])
    await asyncio.to_thread(suppression.remove, uid)
    await update.message.reply_text(f"{uid} убран из реестра исключений")


async def cmd_suppressed(update, ctx):
    """Статистика ОБЩЕГО реестра (не только этого инстанса)."""
    if not _is_admin(update):
        return
    total = await asyncio.to_thread(suppression.count)
    by_reason = await asyncio.to_thread(suppression.count_by_reason)
    lines = [f"{html.escape(r)}: {n}" for r, n in sorted(by_reason.items())]
    await update.message.reply_text(
        f"🚫 Общий реестр исключений: {total} всего\n" + ("\n".join(lines) or "-"))


async def cmd_funnels(update, ctx):
    if not _is_admin(update):
        return
    lst = ", ".join(sorted(rt.funnels.keys()))
    await update.message.reply_text(f"воронок загружено: {len(rt.funnels)}\n{lst}")


async def cmd_stop(update, ctx):
    # отписка любого юзера от всех воронок
    user = update.effective_user
    db.set_flag(user.id, "opted_out", True)
    db.cancel_all(user.id)
    await update.message.reply_text("Ок, больше не пишу. Захочешь вернуться - просто напиши слово")


# --- Direct Message админу → пользователю ---
async def cmd_dm(update, ctx):
    """Ответить пользователю в ЛС. Формат: /dm <user_id> <текст>"""
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args or len(args) < 2:
        await update.message.reply_text("Формат: /dm <user_id> <текст сообщения>")
        return
    try:
        user_id = int(args[0])
        # берём текст ПОСЛЕ user_id из сырого message.text, а не " ".join(args) -
        # join схлопывает переносы строк в пробелы, искажая и отправку, и запись 'owner'
        raw = update.message.text or ""
        first_tok = raw.split(maxsplit=1)[0]              # "/dm"
        after_cmd = raw[len(first_tok):].lstrip()         # "<user_id> <многострочный текст>"
        text = after_cmd[len(args[0]):].lstrip()
        await ctx.bot.send_message(user_id, text)
        await asyncio.to_thread(db.ai_log, user_id, "owner", text)   # ИИ видит ответы владельца в контексте
        # автор ответил лично = вопросы лида обработаны: двигаем курсор, иначе ИИ-таск
        # потом ответит на то, что автор уже закрыл (дубль-ответ)
        await asyncio.to_thread(db.ai_answered_upto_set, user_id, await asyncio.to_thread(db.ai_max_user_id, user_id))
        await update.message.reply_text(f"✓ Отправлено пользователю {user_id}")
    except ValueError:
        await update.message.reply_text(f"user_id должен быть число")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


# --- Рассылки (только chat автора) ---
# черновик рассылки в памяти: chat_id -> {"segment","await_text","body","buttons","count"}
_draft = {}

SEGMENTS = {
    "all": "все живые контакты",
    "registered": "зарегистрированные на событие",
    "not_registered": "НЕ зарегистрированные",
}


async def cmd_broadcast(update, ctx):
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args:
        segs = "\n".join(f"  • {k} - {v}" for k, v in SEGMENTS.items())
        await update.message.reply_text(
            "Рассылка. Формат: /broadcast <сегмент>\n\nСегменты:\n" + segs +
            "\n  • funnel:КЛЮЧ - вошедшие в воронку (напр. funnel:КОМАНДЫ)"
            "\n  • tag:ИМЯ - у кого стоит тег (напр. tag:vip)")
        return
    seg = args[0]
    users = db.segment_users(seg)
    if not users and seg not in SEGMENTS and not seg.startswith("funnel:") and not seg.startswith("tag:"):
        await update.message.reply_text(f"неизвестный сегмент: {seg}")
        return
    # фиксируем получателей ЗДЕСЬ (снапшот), чтобы к /go состав не «уехал»
    _draft[update.effective_user.id] = {"segment": seg, "await_text": True,
                                        "count": len(users), "recipients": users}
    await update.message.reply_text(
        f"Сегмент «{seg}»: {len(users)} получателей\n\n"
        "Пришли текст рассылки следующим сообщением. Кнопку добавь последней строкой:\n"
        "<code>Подпись кнопки | https://ссылка</code>", parse_mode=ParseMode.HTML)


async def _broadcast_capture(update, ctx):
    """Ловит текст рассылки после /broadcast (вызывается из on_text для админа)."""
    d = _draft.get(update.effective_user.id)
    body, buttons = bc.parse_draft(update.message.text)
    if not body.strip():
        # единственная строка «Подпись | ссылка» даёт пустое тело: sendMessage упал бы
        # на пустом тексте, а /go разослал бы пустое всей базе (вся база в failed).
        await update.message.reply_text(
            "⚠️ Текст рассылки пуст (одна строка-кнопка без тела). Пришли сначала текст "
            "сообщения, а кнопку добавь последней строкой «Подпись | https://ссылка»")
        d["await_text"] = True
        return
    d["body"], d["buttons"], d["await_text"] = body, buttons, False
    if not bc.has_link(buttons):
        await update.message.reply_text(
            "⚠️ В рассылке НЕТ кнопки-ссылки. По правилу у каждого сообщения должна быть ссылка. "
            "Пришли текст заново с последней строкой «Подпись | https://ссылка»")
        d["await_text"] = True
        return
    # превью «как увидит подписчик»
    await ctx.bot.send_message(update.effective_user.id, "👇 Так увидит подписчик:")
    await ctx.bot.send_message(update.effective_user.id, body, parse_mode=ParseMode.HTML,
                               reply_markup=bc.build_keyboard(buttons), link_preview_options=NOPREVIEW)
    gate = ("код из аутентификатора: /go <код>" if bc.totp_enabled() else "/go")
    await update.message.reply_text(
        f"Сегмент «{d['segment']}»: {d['count']} получателей\n"
        f"Запуск: {gate}\nОтмена: /abort")


async def cmd_post(update, ctx):
    """/post <ссылка на пост канала> - рассылка КОПИЕЙ поста (copyMessage), а не
    пересборкой текста. Идёт ПОСЛЕ /broadcast <сегмент> (черновик уже открыт и
    ждёт тело) - вместо текста админ даёт ссылку, форматирование/кнопки/медиа
    сохраняются машинно один в один."""
    if not _is_admin(update):
        return
    d = _draft.get(update.effective_user.id)
    if not d or not d.get("await_text"):
        await update.message.reply_text("сначала /broadcast <сегмент>")
        return
    args = ctx.args or []
    if not args:
        await update.message.reply_text(
            "Формат: /post <ссылка на пост>\n"
            "Приватный канал: <адрес-бота>\n"
            "Публичный: <адрес-бота>имя_канала/1234")
        return
    src_chat_id, src_message_id = bc.parse_post_url(args[0])
    if src_chat_id is None:
        await update.message.reply_text(
            "не разобрал ссылку. Форматы: <адрес-бота> или <адрес-бота>имя_канала/1234")
        return
    # превью: copyMessage админу в ЛС - видит ТОЧНУЮ копию (не пересказ). Если бот не
    # админ канала-источника или сообщение недоступно - copy_message падает; черновик
    # НЕ портим (await_text остаётся True), просто внятная ошибка админу
    try:
        await ctx.bot.copy_message(chat_id=update.effective_user.id,
                                   from_chat_id=src_chat_id, message_id=src_message_id)
    except Exception as e:
        await update.message.reply_text(f"⚠️ не смог скопировать пост: {e}")
        return
    d["mode"] = "copy"
    d["src_chat_id"], d["src_message_id"] = src_chat_id, src_message_id
    d["body"], d["buttons"], d["await_text"] = "", "[]", False
    # правило «у рассылки должна быть ссылка» тут не применяем - кнопки уже свои,
    # из оригинального поста, has_link на них не проверяем
    gate = ("код из аутентификатора: /go <код>" if bc.totp_enabled() else "/go")
    await update.message.reply_text(
        f"Сегмент «{d['segment']}»: {d['count']} получателей\n"
        f"Запуск: {gate}\nОтмена: /abort")


async def cmd_go(update, ctx):
    if not _is_admin(update):
        return
    d = _draft.get(update.effective_user.id)
    if not d or d.get("await_text"):
        await update.message.reply_text("нет готового черновика. Сначала /broadcast <сегмент> + текст")
        return
    if db.running_broadcast():
        await update.message.reply_text("уже идёт рассылка. Дождись конца или /abort")
        return
    if not bc.totp_enabled():
        await update.message.reply_text(
            "❌ второй фактор не настроен - рассылка по базе без 2ФА запрещена. Настрой TOTP_SECRET")
        return
    code = (ctx.args or [""])[0]
    if not bc.verify_totp(code):
        await update.message.reply_text("❌ неверный код второго фактора")
        return
    users = d.get("recipients") or db.segment_users(d["segment"])   # зафиксированный на /broadcast список
    if d.get("mode") == "copy":
        bid = db.create_broadcast(d["segment"], "", "[]", mode="copy",
                                  src_chat_id=d["src_chat_id"], src_message_id=d["src_message_id"])
    else:
        bid = db.create_broadcast(d["segment"], d["body"], d["buttons"])
    db.snapshot_recipients(bid, users)
    _draft.pop(update.effective_user.id, None)
    await update.message.reply_text(f"🚀 рассылка #{bid} запущена: {len(users)} получателей. Прогресс: /bstatus, стоп: /abort")


async def cmd_abort(update, ctx):
    if not _is_admin(update):
        return
    bid = db.running_broadcast()
    _draft.pop(update.effective_user.id, None)
    if bid:
        db.set_broadcast_status(bid, "aborted")
        await update.message.reply_text(f"⛔ рассылка #{bid} остановлена")
    else:
        await update.message.reply_text("черновик отменён (активной рассылки нет)")


async def cmd_bstatus(update, ctx):
    if not _is_admin(update):
        return
    bid = db.running_broadcast()
    if not bid:
        await update.message.reply_text("активной рассылки нет")
        return
    r = db.broadcast_report(bid)
    await update.message.reply_text(
        f"рассылка #{bid} [{r['status']}] сегмент «{r['segment']}»\n"
        f"всего {r['total']}: отправлено {r['sent']}, ошибок {r['failed']}, заблокировали {r['blocked']}")


async def cmd_preview(update, ctx):
    """/preview <СЛОВО> - прогон ВСЕЙ цепочки воронки в ЛС админа без боевых
    задержек. Тот же код отправки (_send_node/_kbd), что и в бою: реальные тексты,
    кнопки и per-user редирект-трекинг. Для быстрой проверки без ожидания суток."""
    import types
    if not _is_admin(update):
        return
    args = ctx.args or []
    if not args:
        await update.message.reply_text("Формат: /preview <СЛОВО>")
        return
    key = rt.resolve(args[0]) or args[0].upper()
    f = rt.funnels.get(key)
    if not f:
        await update.message.reply_text(f"воронка {key} не найдена")
        return
    chat_id = update.effective_chat.id
    order = ["A0", "B0", "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "D5", "D6", "D7"]
    if "B0" not in f.nodes:                    # фронт-цепочка событие
        order = ["A0", "K1", "K2", "K3"]

    def when(nk):
        node = f.nodes[nk]
        if nk == "A0":
            return "вход по ссылке"
        inc = [e for e in f.edges if e.b == node.id]
        if not inc:
            return ""
        e = inc[0]
        if e.is_daily:
            return f"в бою утром {e.send_time} МСК"
        sec = e.delay_seconds or 0
        if sec == 0:
            return "в бою сразу"
        return f"в бою через {sec // 3600} ч" if sec >= 3600 else f"в бою через {sec // 60} мин"

    await update.message.reply_text(
        f"🔎 ТЕСТ воронки {key}: {len(order)} сообщений подряд, боевые задержки сняты")
    for nk in order:
        node = f.nodes.get(nk)
        if not node:
            continue
        await ctx.bot.send_message(chat_id, f"— {nk} · {when(nk)} —")
        send = types.SimpleNamespace(text=node.text, buttons=node.buttons, node_key=node.key)
        await _send_node(ctx.bot, chat_id, key, send)
        await asyncio.sleep(0.5)
    await update.message.reply_text("✅ конец теста")


# Пауза рассылки по flood control: Telegram в RetryAfter говорит сколько ждать.
# dict вместо голого float, чтобы не возиться с global внутри async def.
_flood_pause = {"until": 0.0}


async def broadcast_tick(ctx: ContextTypes.DEFAULT_TYPE):
    """Отправка активной рассылки батчами с rate-limit + чекпоинт."""
    if time.time() < _flood_pause["until"]:
        return
    bid = db.running_broadcast()
    if not bid:
        return
    # осколки 'sending' от краша посреди прошлого батча → 'failed' (at-most-once:
    # получатель мог уже получить сообщение, повторно НЕ шлём, чтобы не дублировать)
    db.reap_orphan_sending(bid)
    r = db.broadcast_report(bid)
    batch = db.broadcast_batch(bid, limit=max(1, int(BROADCAST_RATE * 3)))  # ~3 сек работы за тик
    if not batch:
        db.set_broadcast_status(bid, "done")
        await ctx.bot.send_message(ADMIN_CHAT_ID,
            f"✅ рассылка #{bid} завершена: отправлено {r['sent']}, ошибок {r['failed']}, заблокировали {r['blocked']} из {r['total']}")
        return
    kbd = bc.build_keyboard(r["buttons"])   # copy-режим и рассылки без label шлют как есть
    label = r.get("label") or ""
    for uid in batch:
        if db.running_broadcast() != bid:   # /abort посреди батча
            break
        opted, banned = db.flags(uid)       # мог отписаться после снапшота (длинная рассылка)
        if opted or banned:
            db.mark_recipient(bid, uid, "blocked")
            continue
        # общий реестр исключений (все 7 ботов): флагман/регистрация/ручное
        # исключение в ЛЮБОМ боте гасит рассылку из ЭТОГО тоже
        if suppression.is_suppressed(uid):
            db.mark_recipient(bid, uid, "blocked")
            continue
        # сегмент not_registered: человек мог зарегистрироваться уже во время рассылки
        # (deep-link/вебхук GC ставят тег registered параллельно) - не слать ему
        # «ты ещё не зарегистрировался», перечитываем тег живьём как opted_out выше
        if r["segment"] == "not_registered" and "registered" in db.tags(uid):
            db.mark_recipient(bid, uid, "blocked")
            continue
        try:
            # помечаем 'sending' ДО отправки: краш после send, но до 'sent', оставит
            # 'sending' (не 'pending') → reap не дошлёт повторно. broadcast_batch берёт
            # только 'pending', так что 'sending' из батча выпадает.
            db.mark_recipient(bid, uid, "sending")
            if r["mode"] == "copy":
                # копия поста канала как есть (Bot API copyMessage) - форматирование,
                # медиа и кнопки оригинала сохраняются машинно, без пересборки текста.
                # Клик по кнопкам оригинального поста НЕ трекается (кнопки чужие, менять
                # их значило бы перестать быть точной копией) - метка на клик не пишется.
                await ctx.bot.copy_message(chat_id=uid, from_chat_id=r["src_chat_id"],
                                          message_id=r["src_message_id"])
            else:
                # per-user редирект-обёртка кнопок ТОЛЬКО когда есть label (BOT_LABEL
                # задан): клик по кнопке рассылки идёт через /r/<uuid>, redirect.py
                # распознаёт маркер __broadcast__ и пишет label__click в events.
                msg_kbd = bc.wrap_broadcast_buttons(db, r["buttons"], uid, bid, label) if label else kbd
                await ctx.bot.send_message(uid, r["text"], parse_mode=ParseMode.HTML, reply_markup=msg_kbd,
                                           link_preview_options=NOPREVIEW)
            db.mark_recipient(bid, uid, "sent")
        except Forbidden:
            db.set_flag(uid, "banned_bot", True)
            db.mark_recipient(bid, uid, "blocked")
        except RetryAfter as e:
            # Telegram сам сказал сколько ждать (retry_after) - уважаем его:
            # юзер обратно в pending, вся рассылка на паузе до дедлайна,
            # тики в паузе выходят сразу (не долбимся каждые 3с)
            _flood_pause["until"] = time.time() + float(getattr(e, "retry_after", 30) or 30) + 1.0
            db.mark_recipient(bid, uid, "pending")
            log.warning("broadcast #%s: flood control, пауза до +%.0fс", bid, _flood_pause["until"] - time.time())
            break
        except Exception as e:
            msg = str(e).lower()
            if "retry" in msg or "429" in msg or "flood" in msg:
                # 429 без распарсенного retry_after - консервативная пауза 35с
                _flood_pause["until"] = time.time() + 35.0
                db.mark_recipient(bid, uid, "pending")
                break
            db.mark_recipient(bid, uid, "failed", str(e)[:100])
        await asyncio.sleep(1.0 / BROADCAST_RATE)


# --- Планировщик дожима + обработка кликов (тик) ---
async def scheduler_tick(ctx: ContextTypes.DEFAULT_TYPE):
    # дожимы и клики шлют с того же токена - во флуд-паузу (429 от
    # Telegram в рассылке) не суёмся, дозреют после паузы
    if time.time() < _flood_pause["until"]:
        return
    # 1) клики из redirect-сервиса → продвигаем воронку (клик по гайду = TECH,
    #    клик по событие = registered + стоп дожима)
    for cq in db.pending_clicks():
        try:
            await _run(ctx.bot, cq["user_id"], cq["funnel_key"],
                       Event("click", rt.now(), payload=cq["target_url"]))
            db.mark_click_done(cq["id"])
        except Exception as e:
            log.exception("click %s failed: %s", cq["id"], e)
            db.mark_click_done(cq["id"])
    # 2) реанимация зависших в processing (краш между processing и done)
    db.reap_stale_jobs(300)
    # 3) дозревшие таймаут/дожим-джобы. Троттлинг: не больше DOZHIM_BATCH за тик
    #    с паузой между отправками, иначе залп 07:01 (сотни D-джоб разом) = flood-бан.
    #    Остаток дозреет на следующем тике (interval=15с).
    now_ts = time.time()
    jobs = db.due_jobs(now_ts, limit=DOZHIM_BATCH)
    for j in jobs:
        db.mark_job(j["id"], "processing")
        try:
            ok = await _run(ctx.bot, j["user_id"], j["funnel_key"],
                            Event("timeout", rt.now(), node_key=j["node"]))
            if ok:
                db.mark_job(j["id"], "done")
            elif db.requeue_or_fail(j["id"]) == "failed":
                # узел исчерпал ретраи и так и не доставлен, а его потомки уже
                # запланированы оптимистичным apply → гасим прямых потомков, чтобы
                # юзер не получил следующее звено дожима без этого (разрыв цепочки)
                _cancel_children(j["funnel_key"], j["user_id"], j["node"])
        except Exception as e:
            log.exception("job %s failed: %s", j["id"], e)
            db.requeue_or_fail(j["id"])
        await asyncio.sleep(1.0 / DOZHIM_RATE)


def _cancel_children(funnel_key, user_id, node_key):
    """Отменить pending прямых потомков узла (для компенсатора failed-джобы)."""
    f = rt.funnels.get(funnel_key)
    node = f.nodes.get(node_key) if f else None
    if not node:
        return
    for e in f.next_edges(node.id):
        child = f.nodes_by_id.get(e.b)
        if child:
            db.cancel_pending_node(user_id, funnel_key, child.key)


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN пуст - проверь .env")
    if not ADMIN_CHAT_ID:
        raise SystemExit("ADMIN_CHAT_ID не задан - админка была бы открыта/сломана, стоп")
    init_sentry()  # инит Sentry если DSN задан, иначе no-op
    crossdb.check_on_startup()   # кривой MUTE_DB_PATH = падение на старте, не тихий no-op
    _load_ai_catalog()           # каталог гайдов в контекст ИИ (тема лида -> гайд)
    # Python 3.14: get_event_loop() больше не создаёт loop сам - создаём явно
    # (на 3.12, целевом для VPS, это безвредно)
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(on_join_request))
    app.add_handler(ChatMemberHandler(on_my_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(on_staff_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("dm", cmd_dm))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("who", cmd_who))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler(["tag", "untag"], cmd_tag))
    app.add_handler(CommandHandler("suppress", cmd_suppress))
    app.add_handler(CommandHandler("unsuppress", cmd_unsuppress))
    app.add_handler(CommandHandler("suppressed", cmd_suppressed))
    app.add_handler(CommandHandler("funnels", cmd_funnels))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(CommandHandler("go", cmd_go))
    app.add_handler(CommandHandler("abort", cmd_abort))
    app.add_handler(CommandHandler("bstatus", cmd_bstatus))
    app.add_handler(CommandHandler("preview", cmd_preview))
    app.add_handler(CommandHandler("ai", cmd_ai))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VOICE | filters.VIDEO_NOTE | filters.VIDEO | filters.AUDIO
         | filters.Document.ALL) & filters.ChatType.PRIVATE, on_media))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, on_channel_post))
    app.job_queue.run_repeating(scheduler_tick, interval=15, first=5)
    app.job_queue.run_repeating(broadcast_tick, interval=3, first=8)
    log.info("движок воронок запущен. Воронок загружено: %d, слов: %d",
             len(rt.funnels), len(rt.by_keyword))
    # улика в bot.log после рестарта: активен ли ИИ-ответчик и почему
    log.info("ИИ-ответчик: ключ %s, модель %s, kill-switch(ai_kv)=%s, роль=%s",
             "задан" if ANTHROPIC_API_KEY else "НЕ задан", AI_MODEL,
             db.ai_kv_get("ai_enabled", AI_ENABLED), AI_BOT_ROLE)
    app.run_polling(allowed_updates=["message", "callback_query", "chat_join_request",
                                     "my_chat_member", "channel_post", "chat_member"])


if __name__ == "__main__":
    main()
