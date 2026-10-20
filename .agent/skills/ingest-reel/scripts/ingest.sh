#!/bin/bash
# ingest-reel pipeline
# Usage: ingest.sh <URL>
# Output: prints OUTDIR + key file paths to stdout for the calling Claude

set -e

URL="$1"

if [ -z "$URL" ]; then
  echo "ERROR: URL argument required" >&2
  echo "Usage: $0 <URL>" >&2
  exit 1
fi

# --- 1. Extract video ID from URL ---
# Supports: instagram.com/p/{id}, instagram.com/reel/{id}, tiktok.com/.../video/{id}, youtube.com/shorts/{id}
VIDEO_ID=$(echo "$URL" | grep -oE '(p/|reel/|shorts/|video/)[A-Za-z0-9_-]+' | sed 's|.*/||' | head -1)

if [ -z "$VIDEO_ID" ]; then
  # Fallback: try generic last path segment
  VIDEO_ID=$(echo "$URL" | sed 's|/$||' | grep -oE '[A-Za-z0-9_-]+$')
fi

if [ -z "$VIDEO_ID" ]; then
  echo "ERROR: could not extract video ID from URL: $URL" >&2
  exit 1
fi

DATE=$(date +%Y-%m-%d)
OUTDIR="$HOME/.business/growth/ingest/${DATE}-${VIDEO_ID}"

# Idempotency: if already exists, skip download steps but still print paths
if [ -d "$OUTDIR" ] && [ -f "$OUTDIR/grid.jpg" ] && [ -f "$OUTDIR/transcript.txt" ]; then
  echo "ALREADY_INGESTED=true"
  echo "OUTDIR=$OUTDIR"
  VIDEO_FILE=$(ls "$OUTDIR"/*.mp4 2>/dev/null | head -1)
  echo "VIDEO=$VIDEO_FILE"
  echo "GRID=$OUTDIR/grid.jpg"
  echo "TRANSCRIPT=$OUTDIR/transcript.txt"
  INFO_FILE=$(ls "$OUTDIR"/*.info.json 2>/dev/null | head -1)
  echo "INFO=$INFO_FILE"
  exit 0
fi

mkdir -p "$OUTDIR"
cd "$OUTDIR"

cleanup_on_err() {
  cd "$HOME"
  rm -rf "$OUTDIR"
  echo "ERROR: ingest failed, removed orphan $OUTDIR" >&2
}
trap cleanup_on_err ERR

# --- 2. Dependency check ---
for tool in yt-dlp ffmpeg whisper-cli ffprobe python3; do
  if ! command -v "$tool" &> /dev/null; then
    echo "ERROR: $tool not installed. Install via: brew install ${tool/whisper-cli/whisper-cpp}" >&2
    exit 1
  fi
done

WHISPER_MODEL="$HOME/whisper-models/ggml-large-v3-turbo.bin"
if [ ! -f "$WHISPER_MODEL" ]; then
  echo "ERROR: whisper model not found at $WHISPER_MODEL" >&2
  echo "Download from: https://huggingface.co/ggerganov/whisper.cpp/blob/main/ggml-large-v3-turbo.bin" >&2
  exit 1
fi

# --- 3. Download video + metadata ---
echo "STEP=download" >&2
COOKIES_FILE="$HOME/.config/yt-dlp/instagram-cookies.txt"
COOKIES_ARG=""
if [ -f "$COOKIES_FILE" ]; then
  COOKIES_ARG="--cookies $COOKIES_FILE"
fi

yt-dlp $COOKIES_ARG \
  -o "%(id)s.%(ext)s" \
  --write-info-json \
  --write-description \
  --no-warnings \
  "$URL" >&2

VIDEO_FILE=$(ls *.mp4 2>/dev/null | head -1)
if [ -z "$VIDEO_FILE" ]; then
  SOURCE_FILE=$(ls *.webm *.mkv 2>/dev/null | head -1)
  if [ -n "$SOURCE_FILE" ]; then
    echo "STEP=convert ($SOURCE_FILE -> mp4)" >&2
    BASE="${SOURCE_FILE%.*}"
    ffmpeg -hide_banner -loglevel error \
      -i "$SOURCE_FILE" \
      -c:v libx264 -crf 20 -preset fast \
      -c:a aac -b:a 192k \
      "${BASE}.mp4" -y
    VIDEO_FILE="${BASE}.mp4"
  fi
fi

if [ -z "$VIDEO_FILE" ]; then
  echo "ERROR: yt-dlp did not produce mp4 or webm/mkv. URL may be private or invalid." >&2
  exit 1
fi

INFO_FILE=$(ls *.info.json 2>/dev/null | head -1)

# --- 4. Extract audio ---
echo "STEP=audio" >&2
ffmpeg -hide_banner -loglevel error \
  -i "$VIDEO_FILE" \
  -ar 16000 -ac 1 -c:a pcm_s16le \
  audio.wav -y

# --- 5. Transcribe with whisper-cli ---
echo "STEP=transcribe" >&2
whisper-cli \
  -m "$WHISPER_MODEL" \
  -f audio.wav \
  -l auto \
  -otxt -ojf \
  -of transcript 2>&1 | tail -10 >&2

if [ ! -f transcript.txt ]; then
  echo "ERROR: whisper-cli did not produce transcript.txt" >&2
  exit 1
fi

# --- 6. Determine FPS based on duration, extract frames ---
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO_FILE" | cut -d. -f1)
if [ "$DURATION" -lt 20 ]; then
  FPS=4
elif [ "$DURATION" -lt 60 ]; then
  FPS=2
else
  FPS=1
fi

echo "STEP=frames (fps=$FPS, dur=${DURATION}s)" >&2
mkdir -p frames
ffmpeg -hide_banner -loglevel error \
  -i "$VIDEO_FILE" \
  -vf "fps=${FPS},scale=540:-1" \
  "frames/f_%03d.jpg" -y

FRAME_COUNT=$(ls frames | wc -l | tr -d ' ')

# --- 7. Build overview grid ---
echo "STEP=grid (frames=$FRAME_COUNT)" >&2
COLS=8
ROWS=$(( (FRAME_COUNT + COLS - 1) / COLS ))
if [ $ROWS -lt 1 ]; then ROWS=1; fi

ffmpeg -hide_banner -loglevel error \
  -pattern_type glob -i 'frames/*.jpg' \
  -vf "scale=270:-1,tile=${COLS}x${ROWS}" \
  grid.jpg -y

# --- 8. Parse metadata for downstream Claude ---
META=$(python3 -c "
import json, sys
with open('$INFO_FILE') as f:
    d = json.load(f)
print('TITLE=' + str(d.get('title','')))
print('UPLOADER=' + str(d.get('uploader','')))
print('UPLOADER_ID=' + str(d.get('uploader_id','')))
print('UPLOAD_DATE=' + str(d.get('upload_date','')))
print('LIKES=' + str(d.get('like_count','')))
print('COMMENTS=' + str(d.get('comment_count','')))
print('VIEWS=' + str(d.get('view_count','')))
" 2>/dev/null || echo "META_PARSE_ERROR=true")

# --- 9. Print structured output for calling Claude ---
trap - ERR
echo "ALREADY_INGESTED=false"
echo "OUTDIR=$OUTDIR"
echo "VIDEO=$OUTDIR/$VIDEO_FILE"
echo "VIDEO_ID=$VIDEO_ID"
echo "DURATION=$DURATION"
echo "FPS=$FPS"
echo "FRAME_COUNT=$FRAME_COUNT"
echo "GRID=$OUTDIR/grid.jpg"
echo "TRANSCRIPT=$OUTDIR/transcript.txt"
echo "TRANSCRIPT_JSON=$OUTDIR/transcript.json"
echo "INFO=$OUTDIR/$INFO_FILE"
echo "URL=$URL"
echo "$META"
echo "STATUS=ready_for_analysis"