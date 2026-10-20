#!/bin/bash
# deliver.sh - доставка готового ролика: копия на рабочий стол (всегда) + опциональная
# локальная раздача по ссылке (если у тебя поднят сервер раздачи - иначе просто пропускается).
# Usage: deliver.sh <file.mp4> <name.mp4>
#
# Базовый режим (работает у всех, ничего настраивать не надо):
#   готовый ролик копируется на ~/Desktop - заберёшь прямо со стола.
# Опциональный режим (для тех, кто смотрит ролики по ссылке, напр. с телефона):
#   задай переменные REEL_DELIVERY_DIR и REEL_BASE_URL и подними свой http-сервер на этой папке.
#   Тогда скрипт дополнительно положит файл туда и вернёт рабочую ссылку (curl 200).
# Ни бота, ни домена, ни чужих кредов скрипт не трогает.

set -u

SRC_FILE="${1:-}"
DEST_NAME="${2:-}"

# Стол - доставка по умолчанию, работает всегда
DESKTOP_DIR="$HOME/Desktop"
# Опциональный локальный сервер раздачи (пусто = выключено)
DELIVERY_DIR="${REEL_DELIVERY_DIR:-}"
BASE_URL="${REEL_BASE_URL:-}"

if [ -z "$SRC_FILE" ] || [ -z "$DEST_NAME" ]; then
    echo "ОШИБКА: usage: deliver.sh <file.mp4> <name.mp4>" >&2
    exit 1
fi

if [ ! -f "$SRC_FILE" ]; then
    echo "ОШИБКА: исходный файл не найден: $SRC_FILE" >&2
    exit 1
fi

# валидация имени: только [a-zA-Z0-9._-], без пробелов/кириллицы/звёздочек
if ! echo "$DEST_NAME" | grep -Eq '^[a-zA-Z0-9._-]+$'; then
    echo "ОШИБКА: недопустимое имя файла '$DEST_NAME'. Разрешены только [a-zA-Z0-9._-], без пробелов, кириллицы и звёздочек" >&2
    exit 1
fi

# 1. Базовая доставка: копия на рабочий стол (всегда)
mkdir -p "$DESKTOP_DIR"
if ! cp "$SRC_FILE" "$DESKTOP_DIR/$DEST_NAME"; then
    echo "ОШИБКА: не удалось скопировать файл на рабочий стол ($DESKTOP_DIR)" >&2
    exit 1
fi
echo "стол: $DESKTOP_DIR/$DEST_NAME"

# 2. Опциональная локальная раздача по ссылке (только если настроены обе переменные)
if [ -n "$DELIVERY_DIR" ] && [ -n "$BASE_URL" ]; then
    mkdir -p "$DELIVERY_DIR"
    if cp "$SRC_FILE" "$DELIVERY_DIR/$DEST_NAME"; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/$DEST_NAME" 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            echo "$BASE_URL/$DEST_NAME"
        else
            echo "(сервер раздачи не ответил 200 для $BASE_URL/$DEST_NAME - пропускаю ссылку, файл на столе)" >&2
        fi
    fi
fi
