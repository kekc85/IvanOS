"""Observability: Sentry для ошибок доставки + локальное логирование."""
import logging
import os

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


def init_sentry():
    """Инициализация Sentry (no-op если DSN не задан или sentry_sdk не установлен)."""
    if not SENTRY_AVAILABLE:
        return False
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            environment=os.environ.get("ENV", "production"),
            # дефолт и так False - фиксируем намерение явно: тексты лидов/ПДн
            # в Sentry не уходят (в событиях только стектрейсы и наши контексты)
            send_default_pii=False,
        )
        logging.info("Sentry initialized with DSN")
        return True
    except Exception as e:
        logging.warning(f"Failed to init Sentry: {e}")
        return False


def capture_exception(exc, **context):
    """Отправить исключение в Sentry (no-op если не инициализирован)."""
    if not SENTRY_AVAILABLE:
        return
    try:
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_context(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception as e:
        logging.warning(f"Failed to capture in Sentry: {e}")


def capture_message(msg, level="info", **context):
    """Отправить сообщение в Sentry (no-op если не инициализирован)."""
    if not SENTRY_AVAILABLE:
        return
    try:
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_context(k, v)
            sentry_sdk.capture_message(msg, level=level)
    except Exception as e:
        logging.warning(f"Failed to capture message in Sentry: {e}")
