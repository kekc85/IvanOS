#!/usr/bin/env bash
# viral-content-prep router: auto-detect URL type → carousel или Reel.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: prep.sh <IG-URL>"
    echo "       prep.sh <ingest-dir>   # для уже скачанного Reel"
    exit 2
fi

ARG="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Case 1: путь к ingest-папке (secondary режим, уже было `ingest-reel`)
if [ -d "$ARG" ]; then
    echo "Режим: SECONDARY (Reel ingest dir)"
    exec python3 "$SCRIPT_DIR/prep.py" "$ARG"
fi

# Case 2: URL — определяем тип
URL="$ARG"
if [[ "$URL" =~ /reel/ ]]; then
    URL_TYPE="reel"
elif [[ "$URL" =~ /p/ ]]; then
    # Карусель ИЛИ single-photo ИЛИ video — нужна проверка через yt-dlp
    # Самый надёжный способ: yt-dlp --print "%(_type)s" → playlist для каруселей
    PROBE=$(yt-dlp --no-warnings --skip-download --print "%(_type)s" "$URL" 2>/dev/null || echo "video")
    if [ "$PROBE" = "playlist" ]; then
        URL_TYPE="carousel"
    else
        URL_TYPE="reel"
    fi
else
    echo "❌ Неподдерживаемый URL: $URL"
    echo "   Ожидаем instagram.com/p/<id> или instagram.com/reel/<id>"
    exit 1
fi

case "$URL_TYPE" in
    carousel)
        echo "Режим: PRIMARY (carousel→carousel)"
        exec bash "$SCRIPT_DIR/download-carousel.sh" "$URL"
        ;;
    reel)
        echo "Режим: SECONDARY (reel→carousel)"
        # Нужен ingest сначала
        REEL_ID=$(echo "$URL" | grep -oE '/(reel|p)/[A-Za-z0-9_-]+' | awk -F'/' '{print $NF}')
        INGEST_DIR=$(ls -d "$HOME/.business/growth/ingest"/*"-${REEL_ID}" 2>/dev/null | head -1 || true)
        if [ -z "$INGEST_DIR" ]; then
            echo "Запускаю ingest-reel для $REEL_ID..."
            bash "$HOME/.claude/skills/ingest-reel/scripts/ingest.sh" "$URL"
            INGEST_DIR=$(ls -d "$HOME/.business/growth/ingest"/*"-${REEL_ID}" 2>/dev/null | head -1)
        fi
        if [ -z "$INGEST_DIR" ] || [ ! -f "$INGEST_DIR/scene-types.json" ]; then
            echo "❌ scene-types.json отсутствует. Прогон ui-inventory: claude /ui-inventory $INGEST_DIR"
            exit 1
        fi
        exec python3 "$SCRIPT_DIR/prep.py" "$INGEST_DIR"
        ;;
esac