#!/usr/bin/env bash
# reel-design-corpus :: deconstruct.sh
# Design-deconstruction pass over ONE ingested reel.
# Produces the raw artifacts an agent reads to author a per-reel design card:
#   - design-frames/  : frames at fps=1.5 (the cadence the corpus reads on)
#   - tiles/          : legible 6-up montages (read fonts / subtitle position / layout)
#   - cuts.txt        : scene-change timestamps + cut frequency (sec/cut)
#   - meta.txt        : author / views / duration / source dims / fps
# Usage: deconstruct.sh <ingest-dir>   (e.g. ~/.business/growth/ingest/2026-06-10-DZF4V4aMxKz)
set -euo pipefail

DIR="${1:?usage: deconstruct.sh <ingest-dir>}"
DIR="${DIR%/}"
[ -d "$DIR" ] || { echo "no such dir: $DIR" >&2; exit 1; }

MP4="$(ls "$DIR"/*.mp4 2>/dev/null | grep -v -i 'avatar\|produced' | head -1)"
[ -n "$MP4" ] || { echo "no source mp4 in $DIR" >&2; exit 1; }

OUT="$DIR/design"
mkdir -p "$OUT/design-frames" "$OUT/tiles"

# --- meta ---
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MP4" | cut -d. -f1)
read -r W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$MP4" | tr ',' ' ')
IJ="$(ls "$DIR"/*.info.json 2>/dev/null | head -1)"
AUTHOR="?" ; VIEWS="?" ; TITLE="?"
if [ -n "$IJ" ]; then
  AUTHOR=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('uploader') or d.get('channel') or '?')" "$IJ" 2>/dev/null || echo '?')
  VIEWS=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('view_count') or d.get('like_count') or '?')" "$IJ" 2>/dev/null || echo '?')
  TITLE=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print((d.get('title') or '')[:120])" "$IJ" 2>/dev/null || echo '?')
fi
{
  echo "source_mp4: $MP4"
  echo "author: $AUTHOR"
  echo "views: $VIEWS"
  echo "title: $TITLE"
  echo "duration_s: ${DUR:-?}"
  echo "src_dims: ${W}x${H}"
  echo "aspect: $(python3 -c "print(round($W/$H,3))" 2>/dev/null || echo '?')"
} > "$OUT/meta.txt"

# --- design frames @ fps=1.5, scaled to 540 wide for legibility ---
ffmpeg -y -loglevel error -i "$MP4" -vf "fps=1.5,scale=540:-1" "$OUT/design-frames/d_%03d.jpg"
NF=$(ls "$OUT/design-frames"/*.jpg | wc -l | tr -d ' ')

# --- legible 6-up tiles (one row of 6 per tile so text stays readable) ---
i=0; tile=0; FILES=("$OUT"/design-frames/*.jpg)
while [ $i -lt ${#FILES[@]} ]; do
  tile=$((tile+1))
  chunk=("${FILES[@]:$i:6}")
  inputs=(); fc=""
  for j in "${!chunk[@]}"; do inputs+=(-i "${chunk[$j]}"); fc="$fc[$j]"; done
  printf -v tnum "%02d" "$tile"
  ffmpeg -y -loglevel error "${inputs[@]}" \
    -filter_complex "${fc}hstack=${#chunk[@]}" "$OUT/tiles/tile_${tnum}.jpg" 2>/dev/null || true
  i=$((i+6))
done

# --- scene-change / edit-pace detection ---
# NB: showinfo logs at info level (swallowed by -loglevel error) -> use metadata=print.
# thr 0.25 captures hard camera cuts AND strong graphic/caption swaps over a continuous take
# (which is how most talking-head reels actually create "edit pace").
ffmpeg -y -i "$MP4" -filter:v "select='gt(scene,0.25)',metadata=print:file=$OUT/_si.txt" -an -f null - 2>/dev/null || true
python3 - "$OUT/_si.txt" "${DUR:-1}" > "$OUT/cuts.txt" <<'PY'
import re,sys,os
p=sys.argv[1]; dur=float(sys.argv[2] or 1)
si=open(p).read() if os.path.exists(p) else ""
ts=[float(m) for m in re.findall(r'pts_time:([0-9.]+)', si)]
ts=sorted(set(round(t,2) for t in ts))
cuts=len(ts)
print(f"scene/graphic_changes (thr0.25): {cuts}")
print(f"duration_s: {dur}")
print(f"changes_per_sec: {round((cuts+1)/dur,2)}")
print(f"avg_sec_between_changes: {round(dur/(cuts+1),2)}")
print("change_timestamps_s: " + ", ".join(str(t) for t in ts))
PY
rm -f "$OUT/_si.txt"

echo "OK  $DIR"
echo "  frames: $NF @ fps1.5   tiles: $tile   dims:${W}x${H}  dur:${DUR}s  author:$AUTHOR  views:$VIEWS"
echo "  -> $OUT/{meta.txt,cuts.txt,design-frames/,tiles/}"