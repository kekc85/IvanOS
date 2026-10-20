#!/usr/bin/env bash
# ElevenLabs TTS -> MP3 with the student's OWN cloned voice (BYOA: _shared/bring-your-own-account.md)
# Args: $1 = text (required), $2 = voice_id (optional, overrides env)
# Stdout: absolute path to MP3
# Stderr: logs and warnings

set -e
set -o pipefail

TEXT="${1:?text argument required}"
VOICE_ID_OVERRIDE="${2:-}"

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
    echo "INFO: Created empty .env at $ENV_FILE — fill in keys to enable real TTS" >&2
fi

# Load env (whitelisted vars only, no leaking other secrets)
ELEVENLABS_API_KEY=$(grep '^ELEVENLABS_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
ELEVENLABS_VOICE_ID=$(grep '^ELEVENLABS_VOICE_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")

VOICE_ID="${VOICE_ID_OVERRIDE:-${ELEVENLABS_VOICE_ID:-}}"

# BYOA: ключ/голос берём из аккаунта УЧЕНИКА (accounts.json), .env выше - запасной источник
ACCOUNT_PY="$HOME/.claude/skills/_shared/bin/account.py"
if [ -z "${ELEVENLABS_API_KEY:-}" ] && [ -f "$ACCOUNT_PY" ]; then
    ELEVENLABS_API_KEY=$(python3 "$ACCOUNT_PY" get elevenlabs.api_key 2>/dev/null)
fi
if [ -z "$VOICE_ID" ] && [ -f "$ACCOUNT_PY" ]; then
    VOICE_ID=$(python3 "$ACCOUNT_PY" get elevenlabs.voice_id 2>/dev/null)
fi

# Input length validation - ElevenLabs silently truncates at 5000 chars
CHAR_COUNT=$(printf '%s' "$TEXT" | wc -c | tr -d ' ')
if [ "$CHAR_COUNT" -gt 4500 ]; then
    echo "ERROR: Text too long ($CHAR_COUNT chars, max 4500). Split into chunks." >&2
    exit 2
fi

# Hash text → cache key
if command -v md5sum >/dev/null 2>&1; then
    HASH=$(printf '%s' "$TEXT" | md5sum | cut -c1-12)
else
    HASH=$(printf '%s' "$TEXT" | md5 -q | cut -c1-12)
fi

OUT="/tmp/voice-${HASH}.mp3"

# Portable lock to prevent race conditions (two parallel calls = two API jobs = double cost)
LOCK_DIR="/tmp/voice-${HASH}.lock"
RETRY_COUNT=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -gt 60 ]; then
        echo "WARNING: Lock $LOCK_DIR stuck >60s, forcing" >&2
        rm -rf "$LOCK_DIR"
        mkdir "$LOCK_DIR" || true
        break
    fi
    sleep 1
done
trap 'rm -rf "$LOCK_DIR" 2>/dev/null; [ -f "${OUT}.tmp" ] && rm -f "${OUT}.tmp"' EXIT INT TERM

# Idempotent cache check (after lock - second caller sees first call's result)
if [ -f "$OUT" ] && [ "$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")" -gt 1024 ]; then
    echo "INFO: cache hit: $OUT" >&2
    echo "$OUT"
    exit 0
fi

generate_fallback() {
    local reason="$1"
    echo "" >&2
    echo "============================================================" >&2
    echo "ERROR: voice-generate fallback - финальный MP4 будет БЕЗ ГОЛОСА" >&2
    echo "Причина: $reason" >&2
    echo "Установи ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID в ~/.business/processes/.env" >&2
    echo "или передай --no-voice явно в produce-reel чтобы не вводить в заблуждение." >&2
    echo "============================================================" >&2
    echo "" >&2
    local word_count char_count duration_word duration_char duration
    word_count=$(echo "$TEXT" | wc -w | tr -d ' ')
    char_count=$(printf '%s' "$TEXT" | wc -c | tr -d ' ')
    [ "$word_count" -lt 1 ] && word_count=1
    [ "$char_count" -lt 1 ] && char_count=12
    # Калибровка под RU по решению автора: ~2.3 wps + ~12 chars/sec.
    # До этой редакции было 2.0/14 - плейсхолдер кончался раньше реального голоса от ElevenLabs.
    duration_word=$(echo "scale=1; $word_count / 2.3" | bc)
    duration_char=$(echo "scale=1; $char_count / 12.0" | bc)
    duration=$(echo "$duration_word $duration_char" | awk '{print ($1 > $2) ? $1 : $2}')
    # min 1.0 sec
    if [ "$(echo "$duration < 1.0" | bc)" = "1" ]; then
        duration="1.0"
    fi
    ffmpeg -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=44100" \
        -t "$duration" -q:a 9 -acodec libmp3lame "$OUT" -y >/dev/null 2>&1
}

if [ -z "${ELEVENLABS_API_KEY:-}" ] || [ -z "$VOICE_ID" ]; then
    if [ "${IVANOS_ALLOW_PLACEHOLDER:-0}" = "1" ]; then
        generate_fallback "no API key or voice ID (placeholder explicitly allowed)"
        echo "$OUT"
        exit 0
    fi
    echo "" >&2
    echo "============================================================" >&2
    echo "СТОП: подключи СВОЙ ElevenLabs - озвучка пойдёт ТВОИМ голосом" >&2
    echo "============================================================" >&2
    [ -f "$ACCOUNT_PY" ] && python3 "$ACCOUNT_PY" onboard elevenlabs >&2
    echo "" >&2
    echo "Сохрани:  python3 $ACCOUNT_PY set elevenlabs.api_key <твой ключ>" >&2
    echo "          python3 $ACCOUNT_PY set elevenlabs.voice_id <твой voice id>" >&2
    echo "(для тех-отладки пайплайна без голоса: IVANOS_ALLOW_PLACEHOLDER=1)" >&2
    exit 3
fi

# Build JSON payload safely (escape quotes, backslashes, newlines)
PAYLOAD=$(TEXT="$TEXT" python3 -c '
import json, os
print(json.dumps({
    "text": os.environ["TEXT"],
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
}))
')

TMP_OUT="${OUT}.tmp"
HTTP_CODE=$(curl -sS -w "%{http_code}" \
    --max-time 30 --connect-timeout 10 \
    -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
    -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --output "$TMP_OUT" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] && [ -f "$TMP_OUT" ] && [ "$(stat -f%z "$TMP_OUT" 2>/dev/null || stat -c%s "$TMP_OUT")" -gt 1024 ]; then
    mv "$TMP_OUT" "$OUT"
    echo "INFO: TTS generated: $OUT" >&2
    echo "$OUT"
    exit 0
else
    [ -f "$TMP_OUT" ] && rm -f "$TMP_OUT"
    generate_fallback "API error HTTP $HTTP_CODE"
    echo "$OUT"
    exit 0
fi