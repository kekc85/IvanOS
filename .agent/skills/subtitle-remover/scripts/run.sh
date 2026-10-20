#!/bin/zsh
# Subtitle-remover pipeline: detect -> (preview) -> memory-safe wide-context
# inpaint -> stitch -> OCR self-test gate. Quality is enforced by the gate.
#
# Usage: run.sh <input.mp4> <output.mp4> [workdir]
set -e
IN="$1"; OUT="$2"
WORK="${3:-$HOME/subtitle-lab/work_$(basename ${IN%.*})}"
SKILL=$HOME/.claude/skills/subtitle-remover
PY=~/propainter-lab/venv/bin/python
FFMPEG=ffmpeg
PP=~/propainter-lab/ProPainter/inference_propainter.py
export EAST_MODEL=$SKILL/models/frozen_east_text_detection.pb
mkdir -p "$WORK"/frames "$WORK"/masks "$WORK"/final "$WORK"/report
log(){ echo "[$(date +%H:%M:%S)] $*"; }

# ---- 1. frames ----
if [ $(ls "$WORK"/frames/*.png 2>/dev/null | wc -l) -eq 0 ]; then
  log "extracting frames"; $FFMPEG -i "$IN" -vf fps=30 "$WORK"/frames/%05d.png -hide_banner -loglevel error
fi
TOTAL=$(ls "$WORK"/frames/*.png | wc -l | tr -d ' '); log "frames: $TOTAL"

# ---- 2. detect masks (+overlay preview) ----
if [ $(ls "$WORK"/masks/*.png 2>/dev/null | wc -l) -eq 0 ]; then
  log "detecting captions (EAST + plate + shot-aware temporal)"
  $PY $SKILL/scripts/detect.py "$WORK"/frames "$WORK"/masks "$WORK"/overlay 2>&1 | grep -viE objc | tail -1
  $FFMPEG -y -framerate 30 -i "$WORK"/overlay/%05d.png -vf scale=360:-1 -pix_fmt yuv420p \
     "$WORK"/report/MASK_PREVIEW.mp4 -hide_banner -loglevel error
  log "mask preview -> $WORK/report/MASK_PREVIEW.mp4  (verify before trusting output)"
fi

# ---- 3. memory-safe resolution + chunk ----
read RES_W RES_H CHUNK NB <<EOF
$($PY - <<'PY'
import subprocess
o=subprocess.check_output(["vm_stat"]).decode()
free=0
for l in o.splitlines():
    if "Pages free" in l or "Pages inactive" in l:
        free+=int(l.split(":")[1].strip().rstrip("."))*16384
freeGB=free/1e9
# per-frame RAM cost (GB) by resolution, from measured peaks
if   freeGB>=26: w,h,pf=1080,1920,1.15
elif freeGB>=18: w,h,pf=720,1280,0.55
elif freeGB>=12: w,h,pf=540,960,0.30
elif freeGB>=8:  w,h,pf=480,854,0.22
else:            w,h,pf=0,0,0
if w==0:
    print("0 0 0 0")
else:
    import math
    chunk=int((freeGB*0.65-3)/pf); chunk=max(14,min(60,chunk))
    nb=min(chunk,18)
    print(w,h,chunk,nb)
PY
)
EOF
if [ "$RES_W" = "0" ]; then log "ABORT: free RAM too low (<8GB). Close apps and retry."; exit 1; fi
log "memory-safe: ${RES_W}x${RES_H}, chunk=$CHUNK, neighbor=$NB (wide window fixes ghosting)"

# ---- 4. inpaint in RAM-bounded chunks, resume per frame ----
i=1; cidx=0
while [ $i -le $TOTAL ]; do
  end=$((i+CHUNK-1)); [ $end -gt $TOTAL ] && end=$TOTAL
  miss=0; for n in $(seq $i $end); do [ -f "$WORK"/final/$(printf "%05d" $n).png ] || miss=1; done
  if [ $miss -eq 0 ]; then i=$((end+1)); cidx=$((cidx+1)); continue; fi
  cf="$WORK"/c_f; cm="$WORK"/c_m; co="$WORK"/c_o; rm -rf $cf $cm $co; mkdir -p $cf $cm
  for n in $(seq $i $end); do fn=$(printf "%05d" $n); cp "$WORK"/frames/$fn.png $cf/; cp "$WORK"/masks/$fn.png $cm/; done
  log "inpaint chunk $cidx frames $i-$end"
  PYTORCH_ENABLE_MPS_FALLBACK=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=${OMP_NUM_THREADS:-8} \
    $PY -u $PP -i $cf -m $cm -o $co --width $RES_W --height $RES_H \
    --mask_dilation 8 --raft_iter 12 --subvideo_length $CHUNK --neighbor_length $NB --ref_stride 6 \
    --save_frames --save_fps 30 2>&1 | grep -viE "objc|Warning|warn" | tail -1
  j=$i; for of in $(ls $co/c_f/frames/*.png | sort); do cp $of "$WORK"/final/$(printf "%05d" $j).png; j=$((j+1)); done
  rm -rf $cf $cm $co; i=$((end+1)); cidx=$((cidx+1))
done

# ---- 5. stitch + original audio ----
log "stitching"
$FFMPEG -y -framerate 30 -i "$WORK"/final/%05d.png -i "$IN" \
   -map 0:v -map '1:a?' -c:v libx264 -pix_fmt yuv420p -crf 16 -c:a copy -shortest \
   "$OUT" -hide_banner -loglevel error

# ---- 6. machine quality gate ----
log "self-test (OCR on output caption band)"
set +e
$PY $SKILL/scripts/selftest.py "$WORK"/final "$WORK"/report; GATE=$?
set -e
if [ $GATE -eq 0 ]; then
  log "PASS -> clean: $OUT"
else
  log "FAIL -> subtitles/ghosts remain. NOT clean. See $WORK/report/ (residual_*.png). Do NOT ship."
fi
exit $GATE
