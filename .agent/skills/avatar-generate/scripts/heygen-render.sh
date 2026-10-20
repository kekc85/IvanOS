#!/usr/bin/env bash
# HeyGen Avatar V text -> MP4 with the student's OWN trained avatar (BYOA: _shared/bring-your-own-account.md)
# Args: $1 = text (required), $2 = avatar_id (optional), $3 = voice_audio_url (optional)
# Stdout: absolute path to MP4
# Stderr: logs, warnings

set -e
set -o pipefail

TEXT="${1:?text argument required}"
AVATAR_ID_OVERRIDE="${2:-}"
AUDIO_URL="${3:-}"

ENV_FILE="$HOME/.business/processes/.env"
ENV_TEMPLATE="$HOME/.business/processes/.env.template"

# Ensure .env exists (create from template if missing)
if [ ! -f "$ENV_FILE" ]; then
    mkdir -p "$(dirname "$ENV_FILE")"
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
    else
        cat > "$ENV_FILE" <<'EOF'
# ElevenLabs PVC (voice clone) credentials
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# HeyGen Avatar V credentials
HEYGEN_API_KEY=
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=
EOF
    fi
    chmod 600 "$ENV_FILE"
    echo "INFO: Created empty .env at $ENV_FILE — fill in keys to enable real rendering" >&2
fi

# Whitelisted env loading - don't export unrelated secrets
HEYGEN_API_KEY=$(grep '^HEYGEN_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
HEYGEN_AVATAR_ID=$(grep '^HEYGEN_AVATAR_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
HEYGEN_VOICE_ID=$(grep '^HEYGEN_VOICE_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")

AVATAR_ID="${AVATAR_ID_OVERRIDE:-${HEYGEN_AVATAR_ID:-}}"

# BYOA: ключ/аватар/голос берём из аккаунта УЧЕНИКА (accounts.json), .env выше - запасной источник
ACCOUNT_PY="$HOME/.claude/skills/_shared/bin/account.py"
if [ -z "${HEYGEN_API_KEY:-}" ] && [ -f "$ACCOUNT_PY" ]; then
    HEYGEN_API_KEY=$(python3 "$ACCOUNT_PY" get heygen.api_key 2>/dev/null)
fi
if [ -z "$AVATAR_ID" ] && [ -f "$ACCOUNT_PY" ]; then
    AVATAR_ID=$(python3 "$ACCOUNT_PY" get heygen.avatar_id 2>/dev/null)
fi
if [ -z "${HEYGEN_VOICE_ID:-}" ] && [ -f "$ACCOUNT_PY" ]; then
    HEYGEN_VOICE_ID=$(python3 "$ACCOUNT_PY" get heygen.voice_id 2>/dev/null)
fi

# PII-safe stderr redaction helper
redact() {
    sed 's/"avatar_id":"[^"]*"/"avatar_id":"<redacted>"/g; s/"voice_id":"[^"]*"/"voice_id":"<redacted>"/g'
}

# Hash text → cache key
if command -v md5sum >/dev/null 2>&1; then
    HASH=$(printf '%s|%s' "$TEXT" "${AUDIO_URL}" | md5sum | cut -c1-12)
else
    HASH=$(printf '%s|%s' "$TEXT" "${AUDIO_URL}" | md5 -q | cut -c1-12)
fi

OUT="/tmp/avatar-${HASH}.mp4"

# Portable lock to prevent race conditions (double HeyGen billing)
LOCK_DIR="/tmp/avatar-${HASH}.lock"
RETRY_COUNT=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -gt 360 ]; then
        echo "WARNING: Lock $LOCK_DIR stuck >360s, forcing" >&2
        rm -rf "$LOCK_DIR"
        mkdir "$LOCK_DIR" || true
        break
    fi
    sleep 1
done
trap 'rm -rf "$LOCK_DIR" 2>/dev/null; [ -f "${OUT}.tmp" ] && rm -f "${OUT}.tmp"' EXIT INT TERM

if [ -f "$OUT" ] && [ "$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")" -gt 1024 ]; then
    echo "INFO: cache hit: $OUT" >&2
    echo "$OUT"
    exit 0
fi

generate_fallback() {
    local reason="$1"
    echo "WARNING: Using avatar placeholder ($reason)" >&2
    local word_count char_count duration_word duration_char duration
    word_count=$(echo "$TEXT" | wc -w | tr -d ' ')
    char_count=$(printf '%s' "$TEXT" | wc -c | tr -d ' ')
    [ "$word_count" -lt 1 ] && word_count=1
    [ "$char_count" -lt 1 ] && char_count=14
    # Russian-friendly duration: max of word-based and char-based estimates
    duration_word=$(echo "scale=1; $word_count / 2.0" | bc)
    duration_char=$(echo "scale=1; $char_count / 14.0" | bc)
    duration=$(echo "$duration_word $duration_char" | awk '{print ($1 > $2) ? $1 : $2}')
    if [ "$(echo "$duration < 1.0" | bc)" = "1" ]; then
        duration="1.0"
    fi
    # Try drawtext (needs libfreetype); fall back to plain color block if filter missing
    if ! ffmpeg -f lavfi -i "color=c=0x1a1a1a:s=1080x1920:d=${duration}" \
        -vf "drawtext=text='AVATAR PLACEHOLDER':fontcolor=white:fontsize=72:x=(w-tw)/2:y=(h-th)/2" \
        -c:v libx264 -pix_fmt yuv420p -t "$duration" "$OUT" -y >/dev/null 2>&1; then
        ffmpeg -f lavfi -i "color=c=0x1a1a1a:s=1080x1920:d=${duration}" \
            -c:v libx264 -pix_fmt yuv420p -t "$duration" "$OUT" -y >/dev/null 2>&1
    fi
}

if [ -z "${HEYGEN_API_KEY:-}" ] || [ -z "$AVATAR_ID" ]; then
    if [ "${IVANOS_ALLOW_PLACEHOLDER:-0}" = "1" ]; then
        generate_fallback "no API key or avatar ID (placeholder explicitly allowed)"
        echo "$OUT"
        exit 0
    fi
    echo "" >&2
    echo "============================================================" >&2
    echo "СТОП: подключи СВОЙ HeyGen - двойник будет ТВОИМ аватаром" >&2
    echo "============================================================" >&2
    [ -f "$ACCOUNT_PY" ] && python3 "$ACCOUNT_PY" onboard heygen >&2
    echo "" >&2
    echo "Сохрани:  python3 $ACCOUNT_PY set heygen.api_key <твой ключ>" >&2
    echo "          python3 $ACCOUNT_PY set heygen.avatar_id <твой avatar id>" >&2
    echo "          python3 $ACCOUNT_PY set heygen.voice_id <твой voice id>" >&2
    echo "(для тех-отладки пайплайна без аватара: IVANOS_ALLOW_PLACEHOLDER=1)" >&2
    exit 3
fi

# Build voice section based on whether audio_url provided
if [ -n "$AUDIO_URL" ]; then
    VOICE_SECTION=$(AUDIO_URL="$AUDIO_URL" python3 -c '
import json, os
print(json.dumps({"type": "audio", "audio_url": os.environ["AUDIO_URL"]}))
')
else
    if [ -z "${HEYGEN_VOICE_ID:-}" ]; then
        if [ "${IVANOS_ALLOW_PLACEHOLDER:-0}" = "1" ]; then
            generate_fallback "no audio_url and no HEYGEN_VOICE_ID (placeholder explicitly allowed)"
            echo "$OUT"
            exit 0
        fi
        echo "" >&2
        echo "============================================================" >&2
        echo "СТОП: подключи СВОЙ HeyGen - двойник будет ТВОИМ аватаром" >&2
        echo "============================================================" >&2
        [ -f "$ACCOUNT_PY" ] && python3 "$ACCOUNT_PY" onboard heygen >&2
        echo "" >&2
        echo "Сохрани:  python3 $ACCOUNT_PY set heygen.api_key <твой ключ>" >&2
        echo "          python3 $ACCOUNT_PY set heygen.avatar_id <твой avatar id>" >&2
        echo "          python3 $ACCOUNT_PY set heygen.voice_id <твой voice id>" >&2
        echo "(для тех-отладки пайплайна без аватара: IVANOS_ALLOW_PLACEHOLDER=1)" >&2
        exit 3
    fi
    VOICE_SECTION=$(TEXT="$TEXT" VID="$HEYGEN_VOICE_ID" python3 -c '
import json, os
print(json.dumps({"type": "text", "input_text": os.environ["TEXT"], "voice_id": os.environ["VID"]}))
')
fi

PAYLOAD=$(AID="$AVATAR_ID" VOICE="$VOICE_SECTION" python3 -c '
import json, os
print(json.dumps({
    "video_inputs": [{
        "character": {"type": "avatar", "avatar_id": os.environ["AID"], "avatar_style": "normal"},
        "voice": json.loads(os.environ["VOICE"])
    }],
    "dimension": {"width": 1080, "height": 1920}
}))
')

echo "INFO: submitting HeyGen render job..." >&2
CREATE_RESPONSE=$(curl -sS \
    --max-time 30 --connect-timeout 10 \
    -X POST "https://api.heygen.com/v2/video/generate" \
    -H "X-Api-Key: ${HEYGEN_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null || echo "")

VIDEO_ID=$(echo "$CREATE_RESPONSE" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("data", {}).get("video_id", ""))
except Exception:
    print("")
' 2>/dev/null)

if [ -z "$VIDEO_ID" ]; then
    echo "ERR: HeyGen create job failed: $(echo "$CREATE_RESPONSE" | redact)" >&2
    generate_fallback "HeyGen API create failed"
    echo "$OUT"
    exit 0
fi

echo "INFO: video_id=$VIDEO_ID, polling..." >&2

VIDEO_URL=""
MAX_ATTEMPTS=36   # 36 * 10s = 360s = 6 min
for ATTEMPT in $(seq 1 $MAX_ATTEMPTS); do
    # Poll FIRST, then sleep (saves 10s on fast renders)
    STATUS_RESPONSE=$(curl -sS \
        --max-time 15 --connect-timeout 10 \
        "https://api.heygen.com/v1/video_status.get?video_id=${VIDEO_ID}" \
        -H "X-Api-Key: ${HEYGEN_API_KEY}" 2>/dev/null || echo "")
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("data", {}).get("status", ""))
except Exception:
    print("")
' 2>/dev/null)
    echo "INFO: attempt $ATTEMPT/$MAX_ATTEMPTS status=$STATUS" >&2
    case "$STATUS" in
        completed)
            VIDEO_URL=$(echo "$STATUS_RESPONSE" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get("data", {}).get("video_url", ""))
except Exception:
    print("")
' 2>/dev/null)
            break
            ;;
        failed)
            echo "ERR: HeyGen job failed: $(echo "$STATUS_RESPONSE" | redact)" >&2
            break
            ;;
    esac
    # Sleep AFTER check (skip on last iteration anyway since loop exits)
    if [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
        sleep 10
    fi
done

if [ -z "$VIDEO_URL" ]; then
    generate_fallback "HeyGen poll timeout or failure"
    echo "$OUT"
    exit 0
fi

TMP_OUT="${OUT}.tmp"
curl -sS -L --max-time 120 --connect-timeout 10 \
    -o "$TMP_OUT" "$VIDEO_URL" 2>/dev/null || true

# Verify size + MIME (must be valid h264 MP4)
if [ -f "$TMP_OUT" ] && [ "$(stat -f%z "$TMP_OUT" 2>/dev/null || stat -c%s "$TMP_OUT")" -gt 102400 ]; then
    if ffprobe -v error -select_streams v:0 -show_entries stream=codec_name "$TMP_OUT" 2>/dev/null | grep -q h264; then
        mv "$TMP_OUT" "$OUT"
        echo "INFO: avatar rendered: $OUT" >&2
        echo "$OUT"
        exit 0
    else
        echo "ERR: downloaded file is not valid h264 MP4" >&2
        rm -f "$TMP_OUT"
        generate_fallback "invalid MP4"
        echo "$OUT"
        exit 0
    fi
else
    [ -f "$TMP_OUT" ] && rm -f "$TMP_OUT"
    generate_fallback "download failed"
    echo "$OUT"
    exit 0
fi