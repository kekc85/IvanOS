#!/usr/bin/env bash
# golden-run.sh — ЗОЛОТОЙ E2E-ПРОГОН скилла replicate-viral как РЕГРЕССИЯ-ЯКОРЬ (Ф5).
#
# ЮЗ-КЕЙС: гонять ПОСЛЕ ЛЮБОЙ правки скилла replicate-viral / сниппетов motion-blocks /
# scene-assemble.py / scene-audit.py / профилей семей — ЛОВИТ ДЕГРАДАЦИЮ ДО АВТОРА.
# Якорь = эталонная overlap-card сцена (examples/etalon-overlap.spec.json, планка автора DUqeScpDAHW).
#
# ЧТО ПРОВЕРЯЕТ (по порядку, любой шаг red => exit 2):
#   1) ДЕТЕРМИНИЗМ СБОРКИ: scene-assemble -> HTML, md5(HTML) против записанного baseline-md5.
#      (одинаковая спека обязана давать байт-в-байт одинаковый index.html — сорт ключей, без дат/рандома)
#   2) АУДИТ: scene-audit --family overlap-card по рендеру ОБЯЗАН PASS (профильные оси семьи).
#   3) ПОКАДРОВАЯ РЕГРЕССИЯ РЕНДЕРА: 5 равномерных кадров против baseline-PNG —
#      mean-abs-diff < порога И SSIM > порога. Порог откалиброван = шум кодека × 3
#      (рендер недетерминирован побайтово => сверка ПО КАДРАМ с порогом, НЕ md5 видео).
#
# --update-baseline: пересоздать baseline (md5 HTML + 5 PNG + metadata) из ТЕКУЩЕГО состояния.
#   Запускать ТОЛЬКО когда текущее состояние заведомо корректно (после осознанной правки эталона).
#
# Exit 0 = PASS, 2 = FAIL (как у хуков). FAIL печатает ЧТО разошлось (кадр, SSIM, diff).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ASSEMBLE="$HERE/scene-assemble.py"
SPEC="$HERE/examples/etalon-overlap.spec.json"
GOLDEN="$HERE/golden"
META="$GOLDEN/metadata.json"
BASELINE_MD5="$GOLDEN/baseline.html.md5"
NFRAMES=5

UPDATE=0
[ "${1:-}" = "--update-baseline" ] && UPDATE=1

[ -f "$ASSEMBLE" ] || { echo "FAIL: scene-assemble.py не найден ($ASSEMBLE)"; exit 2; }
[ -f "$SPEC" ]     || { echo "FAIL: эталонная спека не найдена ($SPEC)"; exit 2; }
mkdir -p "$GOLDEN"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
OUT="$WORK/scene"

echo "=========================================================="
echo " golden-run — регрессия-якорь replicate-viral (overlap-card эталон)"
echo " режим: $([ $UPDATE = 1 ] && echo 'UPDATE BASELINE' || echo 'CHECK')"
echo "=========================================================="

# ---------- 1) сборка + рендер ----------
echo "--- сборка + рендер эталона ---"
python3 "$ASSEMBLE" "$SPEC" -o "$OUT" --render >"$WORK/asm.log" 2>&1
ASM_RC=$?
IDX="$OUT/index.html"
if [ ! -f "$IDX" ]; then
  echo "FAIL: сборка не дала index.html"; tail -20 "$WORK/asm.log"; exit 2
fi
MP4="$(ls -t "$OUT"/renders/*.mp4 2>/dev/null | head -1)"
if [ -z "$MP4" ] || [ ! -f "$MP4" ]; then
  echo "FAIL: рендер не дал mp4"; tail -30 "$WORK/asm.log"; exit 2
fi
# аудит уже прогнан внутри assemble (--render): проверим что он PASS (family из спеки = overlap-card)
if grep -q "SCENE-AUDIT: PASS" "$WORK/asm.log"; then
  echo "  · авто-аудит overlap-card: PASS"
else
  echo "FAIL: авто-аудит эталона НЕ PASS (профиль overlap-card должен проходить)"
  grep -E "SCENE-AUDIT:|✗ " "$WORK/asm.log" | head -20
  [ $UPDATE = 1 ] || exit 2
fi

# текущий md5 HTML
CUR_MD5="$(md5 -q "$IDX" 2>/dev/null || md5sum "$IDX" | awk '{print $1}')"

# ---------- UPDATE BASELINE ----------
if [ $UPDATE = 1 ]; then
  echo "--- UPDATE BASELINE ---"
  echo "$CUR_MD5" > "$BASELINE_MD5"
  cp "$IDX" "$GOLDEN/baseline.index.html"
  # 5 равномерных эталонных PNG
  DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MP4")"
  python3 - "$MP4" "$DUR" "$GOLDEN" "$NFRAMES" <<'PY'
import sys,subprocess,os
mp4,dur,gold,n=sys.argv[1],float(sys.argv[2]),sys.argv[3],int(sys.argv[4])
for i in range(n):
    t=dur*(i+0.5)/n
    subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',mp4,'-frames:v','1',
                    os.path.join(gold,f'baseline_{i}.png')],capture_output=True)
print("baseline PNG:",n)
PY
  # metadata: когда/чем + откалиброванные пороги (шум кодека × 3, замер)
  python3 - "$META" "$CUR_MD5" "$(basename "$SPEC")" <<'PY'
import sys,json,subprocess,datetime
meta,md5,spec=sys.argv[1],sys.argv[2],sys.argv[3]
try: hf=subprocess.run(['npx','--yes','hyperframes@0.6.91','--version'],capture_output=True,text=True).stdout.strip()
except Exception: hf='?'
json.dump({
  'created': datetime.datetime.now().isoformat(timespec='seconds'),
  'spec': spec,
  'baseline_html_md5': md5,
  'n_frames': 5,
  'renderer': 'hyperframes@0.6.91',
  'hyperframes_version_probe': hf,
  # ПОРОГИ откалиброваны: двойной идентичный рендер по решению автора дал
  # max mean-abs-diff≈0.56 (0-255), min SSIM≈0.993. Порог = шум×3.
  'codec_noise_measured': {'max_mean_abs_diff': 0.56, 'min_ssim': 0.993, 'measured': '2026-06-11'},
  'thresholds': {'max_mean_abs_diff': 1.7, 'min_ssim': 0.978},
  'note': 'рендер недетерминирован побайтово (кодек) => сверка ПО КАДРАМ с порогом, не md5 видео. md5 проверяется только для HTML (детерминированная сборка).'
}, open(meta,'w'), ensure_ascii=False, indent=2)
print("metadata written:",meta)
PY
  echo "BASELINE обновлён в $GOLDEN (md5 HTML + ${NFRAMES} PNG + metadata)."
  echo "PASS (baseline создан)"
  exit 0
fi

# ---------- CHECK ----------
[ -f "$BASELINE_MD5" ] || { echo "FAIL: нет baseline ($BASELINE_MD5). Запусти: $0 --update-baseline"; exit 2; }
[ -f "$GOLDEN/baseline_0.png" ] || { echo "FAIL: нет baseline-PNG. Запусти: $0 --update-baseline"; exit 2; }

FAILN=0

# 1) md5 HTML — детерминизм сборки
BASE_MD5="$(cat "$BASELINE_MD5")"
echo "--- 1) детерминизм сборки (md5 HTML) ---"
if [ "$CUR_MD5" = "$BASE_MD5" ]; then
  echo "  ✅ md5 HTML совпал ($CUR_MD5)"
else
  echo "  ❌ md5 HTML РАЗОШЁЛСЯ: baseline=$BASE_MD5 current=$CUR_MD5 — сборка перестала быть детерминированной ИЛИ эталон осознанно изменён (тогда --update-baseline)"
  if command -v diff >/dev/null 2>&1 && [ -f "$GOLDEN/baseline.index.html" ]; then
    echo "  --- первые отличия HTML ---"; diff "$GOLDEN/baseline.index.html" "$IDX" | head -20
  fi
  FAILN=$((FAILN+1))
fi

# 2) аудит PASS уже проверен выше (assemble --render). Печать-напоминание.
echo "--- 2) аудит overlap-card: PASS (см. выше) ---"

# 3) покадровая регрессия рендера против baseline-PNG
echo "--- 3) покадровая регрессия (SSIM + mean-abs-diff vs baseline) ---"
DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MP4")"
python3 - "$MP4" "$DUR" "$GOLDEN" "$NFRAMES" "$META" "$WORK/frame_bad" <<'PY'
import sys,subprocess,tempfile,os,json
import numpy as np
from PIL import Image
import cv2
mp4,dur,gold,n,meta,badfile=sys.argv[1],float(sys.argv[2]),sys.argv[3],int(sys.argv[4]),sys.argv[5],sys.argv[6]
th=json.load(open(meta))['thresholds']
TH_DIFF=th['max_mean_abs_diff']; TH_SSIM=th['min_ssim']
def grab(t):
    o=tempfile.mktemp(suffix='.png')
    subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',mp4,'-frames:v','1',o],capture_output=True)
    a=np.asarray(Image.open(o).convert('RGB'),dtype=np.float32); os.remove(o); return a
def ssim(x,y):
    x=cv2.cvtColor(x.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float64)
    y=cv2.cvtColor(y.astype(np.uint8),cv2.COLOR_RGB2GRAY).astype(np.float64)
    if x.shape!=y.shape: y=cv2.resize(y,(x.shape[1],x.shape[0]))
    C1=(0.01*255)**2; C2=(0.03*255)**2; k=(11,11); s=1.5
    mx=cv2.GaussianBlur(x,k,s); my=cv2.GaussianBlur(y,k,s)
    mx2,my2,mxy=mx*mx,my*my,mx*my
    sx=cv2.GaussianBlur(x*x,k,s)-mx2; sy=cv2.GaussianBlur(y*y,k,s)-my2; sxy=cv2.GaussianBlur(x*y,k,s)-mxy
    ss=((2*mxy+C1)*(2*sxy+C2))/((mx2+my2+C1)*(sx+sy+C2))
    return float(ss.mean())
bad=0
for i in range(n):
    t=dur*(i+0.5)/n
    cur=grab(t)
    base=np.asarray(Image.open(os.path.join(gold,f'baseline_{i}.png')).convert('RGB'),dtype=np.float32)
    if base.shape!=cur.shape:
        cur=np.asarray(Image.fromarray(cur.astype(np.uint8)).resize((base.shape[1],base.shape[0])),dtype=np.float32)
    d=float(np.mean(np.abs(cur-base))); sv=ssim(cur,base)
    okd=d<=TH_DIFF; oks=sv>=TH_SSIM
    mark='OK ' if (okd and oks) else 'BAD'
    print(f"  [{mark}] кадр{i} t={t:.2f}s mean-abs-diff={d:.4f}(порог<={TH_DIFF}) SSIM={sv:.5f}(порог>={TH_SSIM})")
    if not (okd and oks): bad+=1
open(badfile,'w').write(str(bad))
print("кадров вне порога: %d/%d"%(bad,n))
PY
FRAME_BAD="$(cat "$WORK/frame_bad" 2>/dev/null || echo 1)"
[ "${FRAME_BAD:-1}" = "0" ] || FAILN=$((FAILN+1))

echo "=========================================================="
if [ "$FAILN" -eq 0 ]; then
  echo " golden-run: PASS — эталон детерминирован, аудит зелёный, кадры в пороге"
  echo "=========================================================="
  exit 0
else
  echo " golden-run: FAIL — $FAILN расхождений (см. выше). Если правка эталона ОСОЗНАННА → $0 --update-baseline"
  echo "=========================================================="
  exit 2
fi
