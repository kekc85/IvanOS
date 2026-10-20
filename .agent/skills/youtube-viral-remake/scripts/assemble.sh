#!/usr/bin/env bash
# assemble.sh - сборка чернового long-form ролика: голова автора + вставки по таймкодам
# Usage: assemble.sh <recording.mp4> <segments-dir> <out.mp4> [manifest.tsv] [outro_start]
#
#   recording.mp4  = запись говорящей головы автора (base video+audio track)
#   segments-dir   = папка с клипами-вставками (screencast/motion mp4 + оверлеи png)
#   out.mp4        = выходной файл (16:9)
#   manifest.tsv   = опц. таблица вставок: type<TAB>start<TAB>end<TAB>file
#                    type = overlay-video | overlay-png | replace  (по таймкодам речи)
#   outro_start    = опц. таймкод (сек) начала аутро - вставка с end>outro_start даёт
#                    предупреждение (закон 7 «аутро последним»), сборку не блокирует
#
# Паттерн проверен в проде автора (память feedback_replicate_own_face_ui_beats_pipeline):
#   - image-оверлеи в ffmpeg ОБЯЗАТЕЛЬНО через `-loop 1 -t <дольше ролика> -i png`
#     + финальный `-t <длина> -shortest`. Без -loop 1 у PNG PTS=0 → enable=between(t,t0,t1)
#     покажет его ТОЛЬКО если t0<=0 → все оверлеи с t0>0 молча НЕ бурнутся.
#   - concat глав через MPEG-TS во избежание рассинхрона.
#   - исходное аудио записи муксится целиком (речь = несущая дорожка).
#
# СТАТУС: рабочий скелет. Полный монтаж под конкретную раскладку storyboard достраивается
# фазой 06 (она формирует manifest.tsv из выравнивания по whisper word-level). Скелет собирает
# базовый случай (голова целиком + PNG-оверлеи по таймкодам) детерминированно.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: assemble.sh <recording.mp4> <segments-dir> <out.mp4> [manifest.tsv] [outro_start]" >&2
  echo "  Собирает черновик: голова автора (base) + вставки по таймкодам (16:9)" >&2
  exit 2
fi

REC="$1"; SEGDIR="$2"; OUT="$3"; MANIFEST="${4:-}"; OUTRO_START="${5:-}"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "ОШИБКА: нужен ffmpeg/ffprobe. brew install ffmpeg" >&2
  exit 1
fi
if [[ ! -f "$REC" ]]; then
  echo "ОШИБКА: запись не найдена: $REC" >&2
  exit 1
fi
[[ -d "$SEGDIR" ]] || { echo "ОШИБКА: папка сегментов не найдена: $SEGDIR" >&2; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$REC" 2>/dev/null | cut -d. -f1)
DUR="${DUR:-0}"
[[ "$DUR" -gt 0 ]] || { echo "ОШИБКА: не читается длительность записи" >&2; exit 1; }
OVER_DUR=$((DUR + 5))   # оверлеи длиннее ролика, обрежем -shortest

echo "База (голова): $REC (${DUR}с, 16:9)"
echo "Сегменты:      $SEGDIR"
echo "Выход:         $OUT"

# Собираем ffmpeg-команду: base = запись, каждый PNG-оверлей через -loop 1
# 16:9 канвас (1920x1080) применяется К БАЗЕ первым фильтром, чтобы выход был 16:9 и в
# manifest-ветке (не только в no-manifest) - иначе оверлеи легли бы на сырой AR базы
CANVAS="scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1"
inputs=(-i "$REC")
filter="[0:v]${CANVAS}[base];"
idx=1
last="[base]"

if [[ -n "$MANIFEST" && -f "$MANIFEST" ]]; then
  while IFS=$'\t' read -r type start end file; do
    [[ -z "${type:-}" || "${type:0:1}" == "#" ]] && continue
    fpath="$SEGDIR/$file"
    [[ -f "$fpath" ]] || { echo "  пропуск (нет файла): $file" >&2; continue; }
    # закон 7: вставка НЕ должна заходить на аутро (аутро = последний кадр). Предупредить если end > outro_start
    if [[ -n "$OUTRO_START" ]] && awk -v e="$end" -v o="$OUTRO_START" 'BEGIN{exit !(e+0>o+0)}'; then
      echo "  ⚠️ ВНИМАНИЕ: вставка $file (end=${end}) заходит на аутро (начало ${OUTRO_START}s) - закон 'аутро последним'. Сдвинь окно" >&2
    fi
    case "$type" in
      overlay-png)
        # КРИТИЧНО: -loop 1 -t OVER_DUR, иначе PTS=0 и enable с t0>0 не сработает
        inputs+=(-loop 1 -t "$OVER_DUR" -i "$fpath")
        filter+="${last}[${idx}:v]overlay=enable='between(t,${start},${end})'[v${idx}];"
        last="[v${idx}]"
        echo "  overlay-png: $file @ ${start}-${end}s"
        ;;
      overlay-video|replace)
        inputs+=(-i "$fpath")
        # setpts сдвигает клип на start, иначе вставка играет по глобальным часам с t=0 и к своему
        # окну (напр. 5-я минута) уже доиграла → показывает ЗАМЁРЗШИЙ кадр (зеркало PNG-бага).
        # PTS-STARTPTS обнуляет старт клипа, +start/TB сдвигает его в окно показа
        filter+="[${idx}:v]${CANVAS},setpts=PTS-STARTPTS+${start}/TB[s${idx}];${last}[s${idx}]overlay=enable='between(t,${start},${end})'[v${idx}];"
        last="[v${idx}]"
        echo "  ${type}: $file @ ${start}-${end}s"
        ;;
      *) echo "  неизвестный type: $type ($file)" >&2 ;;
    esac
    idx=$((idx+1))
  done < "$MANIFEST"
fi

# Финал: filter уже содержит [0:v]->[base] (16:9), плюс оверлеи если были. -t DUR -shortest
# обрезает залупленные PNG-оверлеи по длине речи; аудио 0:a = речь автора (несущая)
filter="${filter%;}"
if [[ "$idx" -eq 1 ]]; then
  echo "Вставок нет - нормализую базу в 16:9"
fi
ffmpeg -y "${inputs[@]}" \
  -filter_complex "${filter}" \
  -map "${last}" -map 0:a? \
  -t "$DUR" -shortest -movflags +faststart "$OUT" -loglevel error

if [[ ! -f "$OUT" ]]; then
  echo "ОШИБКА: выход не создан" >&2
  exit 1
fi

# ФИНАЛ: loudnorm + skew-фикс (память feedback_reel_loudness_normalize_final + _av_skew_after_loudnorm_fix)
# Голос из TTS/записи выходит тихим (~-38 LUFS), соц-стандарт ~-14. Без loudnorm = «звук тихий,
# спикера не слышно». loudnorm-ресемпл даёт A/V skew ~60-70мс → жёсткое выравнивание по видео-длине
VDUR=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$OUT" 2>/dev/null | cut -d. -f1)
VDUR="${VDUR:-$DUR}"
NORM="${OUT%.mp4}-norm.mp4"
echo "Финальная аудио-нормализация (loudnorm=-13 LUFS) + skew-фикс..."
if ffmpeg -y -i "$OUT" -t "$VDUR" \
     -c:v copy \
     -af "loudnorm=I=-13:TP=-1.0:LRA=7,aresample=async=1000:first_pts=0" \
     -c:a aac -b:a 256k -ar 48000 -video_track_timescale 30000 \
     "$NORM" -loglevel error 2>/dev/null; then
  mv -f "$NORM" "$OUT"
  # Проверка skew после нормализации (порог <50мс)
  vd=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$OUT" 2>/dev/null)
  ad=$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 "$OUT" 2>/dev/null)
  skew=$(awk -v v="$vd" -v a="$ad" 'BEGIN{ d=v-a; if(d<0)d=-d; printf "%.0f", d*1000 }' 2>/dev/null || echo "?")
  echo "  loudnorm применён, A/V skew: ${skew}мс (порог <50мс)"
else
  echo "  ВНИМАНИЕ: loudnorm-проход не удался, финал БЕЗ нормализации (звук может быть тихим)" >&2
fi

outdur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null | cut -d. -f1)
echo "ГОТОВО: $OUT (${outdur:-?}с)"
echo "Проверь глазами: аутро/CTA последним кадром, реальный UI = чистый скринкаст без оверлеев"
exit 0