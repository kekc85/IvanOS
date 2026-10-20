#!/usr/bin/env bash
# Discovery layer для TikTok + YouTube Shorts
# Wraps yt-dlp --flat-playlist on profile URLs
#
# Usage: discover.sh <@handle> <platform>
#   platform = tiktok | youtube
#
# Stdout: JSONL, one reel per line:
#   {"url":"...","platform":"...","handle":"...","upload_date":"YYYYMMDD","view_count":N}
#
# Stderr: progress + warnings
# Exit: 0 on success (even with 0 results), 1 on bad args, 2 on tool missing

set -e
set -o pipefail

HANDLE_RAW="${1:?handle argument required (e.g. @rileybrown.ai)}"
PLATFORM="${2:?platform argument required: tiktok | youtube}"

HANDLE="${HANDLE_RAW#@}"

if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "ERROR: yt-dlp not installed. brew install yt-dlp" >&2
    exit 2
fi

case "$PLATFORM" in
    tiktok)
        PROFILE_URL="https://www.tiktok.com/@${HANDLE}"
        ;;
    youtube)
        PROFILE_URL="https://www.youtube.com/@${HANDLE}/shorts"
        ;;
    instagram)
        echo "ERROR: instagram discovery requires playwright (yt-dlp broken on IG profiles)" >&2
        echo "INSTRUCTION: use mcp__playwright__browser_navigate + browser_snapshot in calling Claude" >&2
        exit 1
        ;;
    *)
        echo "ERROR: unsupported platform '$PLATFORM' (allowed: tiktok, youtube)" >&2
        exit 1
        ;;
esac

LIMIT=15

echo "INFO: fetching last $LIMIT from $PROFILE_URL" >&2

RAW=$(yt-dlp --flat-playlist --playlist-end "$LIMIT" --no-warnings \
    --print "%(id)s|%(upload_date)s|%(view_count)s|%(webpage_url)s" \
    "$PROFILE_URL" 2>&1 || true)

if echo "$RAW" | grep -q "Unable to extract\|extractor.*broken"; then
    echo "ERROR: yt-dlp broken on $PLATFORM/$HANDLE - update yt-dlp or use playwright fallback" >&2
    echo "  brew upgrade yt-dlp" >&2
    exit 2
fi

LINE_COUNT=0
while IFS='|' read -r ID UPDATE VIEWS URL; do
    [ -z "$URL" ] && continue
    [ "$URL" = "NA" ] && continue
    [ "${URL:0:4}" != "http" ] && continue

    UPDATE="${UPDATE:-NA}"
    VIEWS="${VIEWS:-0}"
    [ "$VIEWS" = "NA" ] && VIEWS=0

    if [ "$PLATFORM" = "youtube" ] && [ "$UPDATE" = "NA" ]; then
        UPDATE=$(yt-dlp --print "%(upload_date)s" --skip-download --no-warnings "$URL" 2>/dev/null || echo "NA")
    fi

    URL=$(echo "$URL" | tr -d '"\\')
    UPDATE=$(echo "$UPDATE" | tr -d '"\\')
    HANDLE_SAFE=$(echo "$HANDLE" | tr -d '"\\')

    printf '{"url":"%s","platform":"%s","handle":"%s","upload_date":"%s","view_count":%s}\n' \
        "$URL" "$PLATFORM" "$HANDLE_SAFE" "$UPDATE" "$VIEWS"
    LINE_COUNT=$((LINE_COUNT + 1))
done <<< "$RAW"

echo "INFO: discovered $LINE_COUNT reels from $HANDLE ($PLATFORM)" >&2
exit 0