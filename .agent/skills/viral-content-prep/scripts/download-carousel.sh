#!/usr/bin/env bash
# Primary режим: скачивает виральную IG-карусель как плоский набор PNG.
# Usage: download-carousel.sh <IG-carousel-URL>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: download-carousel.sh <IG-URL>"
    exit 2
fi

URL="$1"
OUTDIR_ROOT="${VIRAL_CONTENT_DIR:-$HOME/Desktop/viral-content}"
mkdir -p "$OUTDIR_ROOT"

if ! command -v yt-dlp &>/dev/null; then
    echo "ERROR: yt-dlp не установлен. brew install yt-dlp"
    exit 1
fi

# Извлекаем ID карусели и handle
CAROUSEL_ID=$(echo "$URL" | grep -oE '/p/[A-Za-z0-9_-]+' | awk -F'/' '{print $NF}')
if [ -z "$CAROUSEL_ID" ]; then
    echo "ERROR: не смог извлечь ID из URL: $URL"
    exit 1
fi

# Probe meta чтобы получить handle (uploader)
META_JSON=$(yt-dlp --no-warnings --skip-download --print-json --no-playlist "$URL" 2>/dev/null | head -1 || true)
HANDLE=$(echo "$META_JSON" | python3 -c "import sys, json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('uploader_id') or d.get('channel') or 'unknown')" 2>/dev/null || echo "unknown")

OUTDIR="$OUTDIR_ROOT/${HANDLE}-${CAROUSEL_ID}"
if [ -d "$OUTDIR" ]; then
    rm -rf "$OUTDIR"
fi
mkdir -p "$OUTDIR"

echo "Скачиваю карусель $URL"
echo "Output: $OUTDIR"

# Скачиваем все слайды через yt-dlp
# Карусель IG = playlist of images. Каждый слайд = отдельный image.
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

yt-dlp \
    --no-warnings \
    --no-progress \
    --output "$TMPDIR/slide-%(playlist_index)02d.%(ext)s" \
    --write-info-json \
    --yes-playlist \
    "$URL" 2>&1 | grep -v "^\[" || true

# Конвертим JPG → PNG если нужно, переименовываем чистенько
COUNT=0
for f in $(ls "$TMPDIR"/slide-*.{jpg,jpeg,png,webp} 2>/dev/null | sort); do
    COUNT=$((COUNT + 1))
    OUT_NAME=$(printf "slide-%02d.png" $COUNT)
    case "${f##*.}" in
        png) cp "$f" "$OUTDIR/$OUT_NAME" ;;
        *) python3 -c "from PIL import Image; Image.open('$f').convert('RGB').save('$OUTDIR/$OUT_NAME')" 2>/dev/null || cp "$f" "$OUTDIR/$OUT_NAME" ;;
    esac
done

# Фолбэк: yt-dlp берёт только видео-посты; фото-карусели в 2026 за логин-стеной.
# Их качаем через Apify (аккаунт и IP вне цепочки, ~$0.003/пост, токен в ~/.claude/.env).
if [ "$COUNT" -eq 0 ]; then
    APIFY_IG=""
    for cand in "$HOME/.business/scripts/ig-fetch/apify_ig.py"; do
        [ -f "$cand" ] && APIFY_IG="$cand" && break
    done
    if [ -n "$APIFY_IG" ]; then
        echo "yt-dlp дал 0 слайдов (фото-карусель) - иду через Apify"
        if python3 "$APIFY_IG" carousel "$URL" "$TMPDIR/apify"; then
            for f in $(ls "$TMPDIR"/apify/slide-*.jpg 2>/dev/null | sort); do
                COUNT=$((COUNT + 1))
                OUT_NAME=$(printf "slide-%02d.png" $COUNT)
                python3 -c "from PIL import Image; Image.open('$f').convert('RGB').save('$OUTDIR/$OUT_NAME')" 2>/dev/null || cp "$f" "$OUTDIR/$OUT_NAME"
            done
            [ -f "$TMPDIR/apify/caption.txt" ] && cp "$TMPDIR/apify/caption.txt" "$OUTDIR/caption.txt"
        fi
    else
        echo "WARN: apify_ig.py не найден - фолбэк Apify недоступен"
    fi
fi

# Meta-файл
cat > "$OUTDIR/meta.json" <<JSONEOF
{
  "carousel_id": "$CAROUSEL_ID",
  "handle": "$HANDLE",
  "url": "$URL",
  "downloaded_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "slide_count": $COUNT
}
JSONEOF

echo ""
echo "OK: $COUNT слайдов в $OUTDIR"
echo "Готов к drag-and-drop в Custom GPT (плоская папка)"