#!/bin/bash
# ui-record wrapper.
# Запускает Playwright recorder из content-factory.
#
# Usage:
#   record.sh <scenario-name-or-path> [out-path]
#
# Если out-path не указан — пишет в tools/ui-record/library/<scenario>.mp4

set -e

SCENARIO="$1"
OUT="$2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "$CONTENT_FACTORY_DIR" ] && [ -d "$CONTENT_FACTORY_DIR" ]; then
  CF="$CONTENT_FACTORY_DIR"
elif [ -f "$SCRIPT_DIR/tools/ui-record/record.mjs" ]; then
  CF="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../tools/ui-record/record.mjs" ]; then
  CF="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  echo "record.mjs не найден. Этот скилл требует внешний пакет content-factory (см. SKILL.md)." >&2
  echo "Либо поставь его и укажи путь: CONTENT_FACTORY_DIR=/путь/к/content-factory $0 $*" >&2
  echo "Либо собери record.mjs на своём проекте по инструкции SKILL.md ('Synthetic UI mock pipeline')." >&2
  exit 1
fi

if [ -z "$SCENARIO" ]; then
  echo "Usage: $0 <scenario-name-or-path> [out-path]" >&2
  echo "Available scenarios:" >&2
  ls "$CF/tools/ui-record/scenarios/"*.json 2>/dev/null | xargs -n1 basename | sed 's/\.json$//' | sed 's/^/  /' >&2
  exit 1
fi

if [ -z "$OUT" ]; then
  NAME=$(basename "$SCENARIO" .json)
  OUT="$CF/tools/ui-record/library/${NAME}.mp4"
fi

mkdir -p "$(dirname "$OUT")"

cd "$CF"
node tools/ui-record/record.mjs --scenario "$SCENARIO" --out "$OUT"

# Print metadata
if command -v ffprobe >/dev/null 2>&1; then
  echo "---" >&2
  ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration,codec_name -of default=noprint_wrappers=1 "$OUT" >&2
fi