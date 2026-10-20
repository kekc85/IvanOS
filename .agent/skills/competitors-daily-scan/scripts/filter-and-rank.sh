#!/usr/bin/env bash
# Filter discovered reels by date, sort by views desc, take top N
#
# Usage: filter-and-rank.sh <jsonl-file> <top-n> [date-YYYYMMDD]
#   date defaults to today (МСК)
#
# Stdout: JSON array of selected reels
# Stderr: counts

set -e

INPUT="${1:?jsonl file required}"
TOP_N="${2:?top N required}"
TARGET_DATE="${3:-}"

if [ ! -f "$INPUT" ]; then
    echo "ERROR: input file not found: $INPUT" >&2
    exit 1
fi

if [ -z "$TARGET_DATE" ]; then
    TARGET_DATE=$(TZ="Europe/Moscow" date +%Y%m%d)
fi

echo "INFO: filtering for date=$TARGET_DATE, top_n=$TOP_N" >&2

TOTAL=$(wc -l < "$INPUT" | tr -d ' ')

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 required for JSON manipulation" >&2
    exit 2
fi

OUTPUT=$(INPUT="$INPUT" TARGET_DATE="$TARGET_DATE" TOP_N="$TOP_N" python3 <<'PY'
import json, os, sys

input_path = os.environ["INPUT"]
target_date = os.environ["TARGET_DATE"]
top_n = int(os.environ["TOP_N"])

reels = []
malformed = 0
with open(input_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            reels.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
            continue

today_reels = [r for r in reels if str(r.get("upload_date", "")) == target_date]

def views_key(r):
    v = r.get("view_count", 0)
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0

today_reels.sort(key=views_key, reverse=True)
top = today_reels[:top_n]

sys.stderr.write(f"INFO: parsed={len(reels)} (malformed={malformed}) today={len(today_reels)} top={len(top)}\n")

print(json.dumps(top, ensure_ascii=False, indent=2))
PY
)

echo "$OUTPUT"