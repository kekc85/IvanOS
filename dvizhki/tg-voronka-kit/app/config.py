"""Конфиг из .env (без сторонних зависимостей)."""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(HERE, ".env")


def _load_env():
    if not os.path.exists(ENV_PATH):
        return
    for line in open(ENV_PATH, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0") or 0)
# Игнор-лист: tg user_id, чьи апдейты бот молча дропает (спамеры). Их сообщения
# НЕ форвардятся админу и не стартуют воронку - не бан, а «не показывать никогда».
# Пополняется в .env через запятую: BLOCKED_USER_IDS=111222333,444555666
BLOCKED_USER_IDS = {int(x) for x in os.environ.get("BLOCKED_USER_IDS", "").replace(" ", "").split(",") if x.strip().isdigit()}
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "voronka.sqlite"))
FUNNELS_DIR = os.environ.get("FUNNELS_DIR", os.path.join(HERE, "funnels"))
# Клик по событие-кнопке = регистрация (прокси, пока не подключён вебхук платформы курса).
# ДЕФОЛТ 0 (безопасный): клик по кнопке != регистрация. При
# дефолте 1 клик метил всех кликнувших registered → ложное "доступ открыт, 4 урока"
# (событие-бот) + CancelAll дожима и глушение продаж (основной бот). Включать 1
# ЯВНО и ТОЛЬКО на период без честного вебхука платформы курса, снимать сразу как заработал.
REGISTERED_BY_CLICK = os.environ.get("REGISTERED_BY_CLICK", "0") == "1"
# Секрет вебхука регистрации платформы курса (пусто = endpoint выключен)
GC_WEBHOOK_TOKEN = os.environ.get("GC_WEBHOOK_TOKEN", "")
# Воронки с ПРЯМЫМ входом по deep-link: первый экран (A0) человек уже
# видел на странице, откуда пришёл, и повторять его в боте не нужно.
# Перечисли ключи через запятую в .env: DIRECT_ENTRY_FUNNELS=СЛОВО1,СЛОВО2
DIRECT_ENTRY_FUNNELS = {x.strip() for x in
                        os.environ.get("DIRECT_ENTRY_FUNNELS", "").split(",")
                        if x.strip()}
# Ключ фронт-воронки прямой продажи (вход в неё глушит параллельные дожимы)
FRONT_FUNNEL_KEY = os.environ.get("FRONT_FUNNEL_KEY", "СОБЫТИЕ")
# Дефолтная воронка на голый /start (без ключа/с неизвестным). Пусто = старая
# заглушка. На фронт-боте событие ставить СОБЫТИЕ - тупиков для людей не будет.
DEFAULT_FUNNEL_KEY = os.environ.get("DEFAULT_FUNNEL_KEY", "")
# Ссылки welcome-цепочки (после регистрации/оплаты). Пусто = welcome-воронки
# не грузятся: кнопка в никуда хуже отсутствия цепочки.
WELCOME_CABINET_URL = os.environ.get("WELCOME_CABINET_URL", "")
WELCOME_VIP_URL = os.environ.get("WELCOME_VIP_URL", "")
WELCOME_ANKETA_URL = os.environ.get("WELCOME_ANKETA_URL", "")
WELCOME_CHANNEL_URL = os.environ.get("WELCOME_CHANNEL_URL", "")
WELCOME_LINKS = {"{КАБИНЕТ}": WELCOME_CABINET_URL,
                 "{ОПЛАТА}": WELCOME_VIP_URL,
                 "{АНКЕТА}": WELCOME_ANKETA_URL,
                 "{КАНАЛ}": WELCOME_CHANNEL_URL}
# Путь к БД соседнего бота-инстанса: вход во фронт-цепочку гасит его pending-дожимы
# этого же юзера (tg user_id общий). Пусто = выключено.
MUTE_DB_PATH = os.environ.get("MUTE_DB_PATH", "")
# Общий реестр исключений (suppression list) - ОДИН файл на все 7 инстансов бота.
# Попавший туда (флагман/зарегистрировался/ручное исключение) не получает
# рассылку НИ ИЗ ОДНОГО бота. Дефолт - путь на проде (см. app/suppression.py).
SUPPRESSION_DB_PATH = os.environ.get("SUPPRESSION_DB_PATH", "/opt/shared/suppression.sqlite")
# Пути ко ВСЕМ 7 SQLite инстансов (contacts.username) - для поиска tg user_id по
# username с сайта платформы курса (форма регистрации отдаёт @ник, не tg_id). redirect-сервис
# всегда работает в контексте ОДНОГО инстанса (свой DB_PATH), но человек мог писать
# ЛЮБОМУ из 7 ботов под этим username - искать нужно везде. Дефолт = прод-раскладка
# (7 инстансов на одном сервере, см. app/suppression.py шапку про 7 ботов).
SUPPRESSION_LOOKUP_DBS = [
    p.strip() for p in os.environ.get(
        "SUPPRESSION_LOOKUP_DBS",
        "/opt/voronka/voronka.sqlite,"
        "/opt/voronka-2/voronka-2.sqlite,"
        "/opt/base-author/voronka.sqlite,"
        "/opt/base-autoapprove/voronka.sqlite,"
        "/opt/base-pr/voronka.sqlite,"
        "/opt/base-team/voronka.sqlite,"
        "/opt/base-secret/voronka.sqlite",
    ).split(",") if p.strip()
]
# Ускорение времени для теста дожима (1 = боевой режим). На проде принудительно 1.
TIME_SCALE = float(os.environ.get("TIME_SCALE", "1"))
# База редиректа клик-трекинга (свой домен с TLS)
REDIRECT_BASE = os.environ.get("REDIRECT_BASE", "https://author.ru")
# Allowlist доменов, куда редирект вообще имеет право вести (анти-open-redirect)
REDIRECT_ALLOW = ["author.ru", "t.me"]
# Второй фактор на рассылку/экспорт (TOTP). Пусто = 2ФА выключен.
TOTP_SECRET = os.environ.get("TOTP_SECRET", "")
# Потолок скорости рассылки (сообщений/сек, ниже лимита Telegram ~30)
BROADCAST_RATE = max(0.5, float(os.environ.get("BROADCAST_RATE", "20")))  # floor: rate<=0 дал бы деление на ноль/битый batch
# Дожим (C1-D7): в 07:01 все D-джобы дозревают разом. Без троттлинга это залп
# до 500 sendMessage за тик = flood-бан всего бота. Размазываем: не более
# DOZHIM_BATCH за тик (interval=15с) с паузой 1/DOZHIM_RATE между отправками.
# 200 при 20 msg/s = ~10с работы, укладывается в тик; остаток дозреет на следующем.
DOZHIM_RATE = max(0.5, float(os.environ.get("DOZHIM_RATE", "20")))
DOZHIM_BATCH = int(os.environ.get("DOZHIM_BATCH", "200"))

# --- ИИ-ответчик (fallback необработанного текста в on_text) ---
# Пустой ключ = ИИ жёстко выключен независимо от AI_ENABLED/ai_kv (см. ai_responder.py)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Дефолт kill-switch'а: реальный рантайм-флаг живёт в БД (ai_kv "ai_enabled"), этот
# только сид при первом чтении - переживает рестарт через БД, не через .env.
# Нормализуем в строгие "1"/"0": «true/yes/on/да» тоже включают (иначе AI_ENABLED=true
# молча выключал бы ИИ, а лог старта печатал бы «kill-switch=true» = выглядит включённым)
AI_ENABLED = "1" if os.environ.get("AI_ENABLED", "1").strip().lower() in (
    "1", "true", "yes", "on", "да") else "0"
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5")
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "1200"))
AI_TIMEOUT = float(os.environ.get("AI_TIMEOUT", "30"))
AI_DAILY_PER_USER = int(os.environ.get("AI_DAILY_PER_USER", "20"))
AI_HOURLY_PER_USER = int(os.environ.get("AI_HOURLY_PER_USER", "6"))
AI_DAILY_GLOBAL = int(os.environ.get("AI_DAILY_GLOBAL", "300"))
AI_EVENT_URL = os.environ.get("AI_EVENT_URL", "https://author.ru/event/")
# Ссылки роли "live" (консьерж живого события): закрытый канал и оплата VIP.
# Пустые = плейсхолдеры ссылок в ответе ИИ бракуются постгардом
AI_STAFF_URL = os.environ.get("AI_STAFF_URL", "")
AI_VIP_URL = os.environ.get("AI_VIP_URL", "")
# "front" = фронт-бот подарков (дефолт), "event" = бот события, "live" =
# консьерж живого события - переключает акцент промпта
# (см. ai_responder.SYSTEM_PROMPT)
AI_BOT_ROLE = os.environ.get("AI_BOT_ROLE", "front")

# --- Сквозные метки аналитики (label): <бот>__<кампания>__<пост>__<действие>) ---
# Короткое имя бота для меток (tgmain, tgofficial, tgevent...).
# Пусто = метки собираются без бота (легаси-совместимость со старыми записями events).
BOT_LABEL = os.environ.get("BOT_LABEL", "")
# Текущая кампания (событие/поток/...) - второй сегмент метки.
CAMPAIGN = os.environ.get("CAMPAIGN", "live")

# Авто-одобрение ЛЮБОЙ органической заявки на вступление (join request) без
# запуска воронки - только approve + запись в contacts. Нужен клону-инстансу
# "autoapprove"-бота, который сидит в канале/чате исключительно чтобы снимать
# заявки с модерации. ДЕФОЛТ 0 (безопасный): на обычном воронка-боте органика
# должна оставаться как есть (игнорироваться), включать явно только на этом клоне.
AUTO_APPROVE_ALL = os.environ.get("AUTO_APPROVE_ALL", "0") == "1"
