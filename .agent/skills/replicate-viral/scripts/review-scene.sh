#!/usr/bin/env bash
# review-scene.sh — ОБЯЗАТЕЛЬНОЕ ревью сцены ПО ВИДЕО (не по одному кадру).
# Производит для критика: посекундную раскадровку НАШЕЙ сцены + ОРИГИНАЛА бок-о-бок + кадр под IG-маской.
# Корень провалов G0DM0D3: ревью на одном cherry-picked кадре прятало чёрные полосы / срез лба /
# рассинхрон / разъезд субтитров. Теперь критик смотрит ВИДЕО посекундно + safe-zone.
#
# Usage: review-scene.sh <our-scene.mp4> <ref.mp4> <ref_start_s> [out_dir]
set -uo pipefail
OUR="${1:?our scene mp4}"; REF="${2:?reference mp4}"; RS="${3:-0}"; OUT="${4:-/tmp/review}"
HTML="${5:-}"   # опц.: HTML сцены с data-s/data-start — берём worst-таймкоды появления слов субтитра
MASK=~/.claude/skills/replicate-viral/scripts/ig-safezone-mask.png
mkdir -p "$OUT"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUR" | cut -d. -f1); DUR=${DUR:-4}

# our per-second frames
ours=(); n=0
for ((s=0; s<=DUR; s++)); do t=$(python3 -c "print(min($s+0.5,$DUR-0.05))"); f="$OUT/our_$s.png"; ffmpeg -y -ss "$t" -i "$OUR" -frames:v 1 -vf scale=320:-1 "$f" -loglevel error && ours+=("$f") && n=$((n+1)); done
# reference per-second frames (same count, offset by ref_start)
refs=(); for ((s=0; s<n; s++)); do rt=$(python3 -c "print($RS+$s+0.5)"); f="$OUT/ref_$s.png"; ffmpeg -y -ss "$rt" -i "$REF" -frames:v 1 -vf scale=320:-1 "$f" -loglevel error && refs+=("$f"); done

hstack(){ local out="$1"; shift; local ins=(); local fc=""; local i=0; for f in "$@"; do ins+=(-i "$f"); fc="$fc[$i]"; i=$((i+1)); done; ffmpeg -y "${ins[@]}" -filter_complex "${fc}hstack=$i" "$out" -loglevel error; }
hstack "$OUT/ours_strip.png" "${ours[@]}"
hstack "$OUT/ref_strip.png" "${refs[@]}"

# masked full frame (safe-zone) at mid-scene
mt=$(python3 -c "print($DUR/2)")
ffmpeg -y -ss "$mt" -i "$OUR" -frames:v 1 "$OUT/mid.png" -loglevel error
[ -f "$MASK" ] && ffmpeg -y -i "$OUT/mid.png" -i "$MASK" -filter_complex "[0][1]overlay" "$OUT/mid_masked.png" -loglevel error

# FULL-RES region crops (root R1: превью прячут срез лба / дешёвый шрифт)
# head across motion — срез лба виден только на части кадров (аватар движется)
hc=()
for x in 0.2 0.45 0.7 0.92; do t=$(python3 -c "print(round($DUR*$x,2))"); f="$OUT/head_$x.png"; ffmpeg -y -ss "$t" -i "$OUR" -frames:v 1 -vf "crop=1080:600:0:840,scale=430:-1" "$f" -loglevel error && hc+=("$f"); done
hstack "$OUT/head_motion.png" "${hc[@]}"
# caption region full-res (шрифт/обводка/три-этажа/коллизия)
ct=$(python3 -c "print(round($DUR*0.85,2))"); ffmpeg -y -ss "$ct" -i "$OUR" -frames:v 1 -vf "crop=1080:560:0:470,scale=760:-1" "$OUT/cap_region.png" -loglevel error
# UI/github ВЕРХ full-res на 3 таймкодах — ЧИТАЕМОСТЬ (ghosting/смаз/хаос числом не ловится → только глаза)
gi=()
for x in 0.15 0.5 0.85; do gt=$(python3 -c "print(round($DUR*$x,2))"); f="$OUT/ui_$x.png"; ffmpeg -y -ss "$gt" -i "$OUR" -frames:v 1 -vf "crop=1080:760:0:120,scale=700:-1" "$f" -loglevel error && gi+=("$f"); done
hstack "$OUT/ui_legibility.png" "${gi[@]}"

# КОМПОЗИТ «лицо + субтитр НА ОДНОМ кадре» на worst-таймкодах (root-cause 2026-06-11:
# лицо и субтитр раньше попадали в РАЗНЫЕ кропы → критик не видел наложение «текст на лице»).
# Берём ПОЛНЫЕ кадры (лицо внизу + субтитр на стыке видны вместе) в МОМЕНТЫ появления слов
# (data-s/data-start из HTML), а не один 0.85·DUR. Так наложение «текст поперёк глаз» видно глазами.
wt=()
if [ -n "$HTML" ] && [ -f "$HTML" ]; then
  # вытащить data-s/data-start значения (моменты появления слов субтитра).
  # portable (bash 3.2 macOS — без mapfile): while-read в массив.
  while IFS= read -r v; do [ -n "$v" ] && wt+=("$v"); done < <(grep -oE 'data-s(tart)?=["'"'"'][0-9.]+' "$HTML" | grep -oE '[0-9.]+$' | sort -un)
fi
# фоллбек: если в HTML нет data-s — равномерные таймкоды по длине сцены
if [ "${#wt[@]}" -eq 0 ]; then
  for x in 0.2 0.45 0.7 0.9; do wt+=("$(python3 -c "print(round($DUR*$x,2))")"); done
fi
comp=(); ci=0
for wtime in "${wt[@]}"; do
  # clamp в [0, DUR-0.05]; чуть после появления слова (+0.05)
  ts=$(python3 -c "print(round(min(max(float($wtime)+0.05,0),$DUR-0.05),2))")
  f="$OUT/faceword_$ci.png"
  # ПОЛНЫЙ кадр, уменьшен по ширине для склейки; лицо+субтитр в одном изображении
  ffmpeg -y -ss "$ts" -i "$OUR" -frames:v 1 -vf "scale=300:-1" "$f" -loglevel error && comp+=("$f") && ci=$((ci+1))
  [ "$ci" -ge 8 ] && break   # не больше 8 моментов
done
[ "${#comp[@]}" -gt 0 ] && hstack "$OUT/face_caption_composite.png" "${comp[@]}"

echo "REVIEW ARTIFACTS (отдать критику ВСЕ):"
echo "  наша раскадровка:   $OUT/ours_strip.png"
echo "  оригинал раскадр.:  $OUT/ref_strip.png"
echo "  кадр под IG-маской: $OUT/mid_masked.png"
echo "  голова×движение:    $OUT/head_motion.png   (срез лба ловится тут)"
echo "  субтитры full-res:  $OUT/cap_region.png     (шрифт/обводка/3-этажа/коллизия)"
echo "  лицо+субтитр ВМЕСТЕ:$OUT/face_caption_composite.png (текст НА ЛИЦЕ / поверх UI ловится тут — полные кадры на моментах появления слов)"
echo "Критик ОБЯЗАН: (1) поэлементно хуже/равно/лучше конкурента — ХУЖЕ=FAIL; (2) лоб/макушка на ВСЕХ head-кадрах целы; (3) субтитры 1-2 слова горизонталь на стыке, премиум, НЕ 3 этажа; (4) под красной маской нет важного; (5) на face_caption_composite субтитр/титр НЕ лежит поперёк лица (особ. глаза/лоб) и НЕ закрывает важный UI — ЛЮБОЕ наложение=FAIL."
