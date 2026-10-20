#!/usr/bin/env bash
# motion-floor-check.sh - бенчмарк динамики: визуальных изменений в секунду
# Usage:
#   motion-floor-check.sh <video> [scene_threshold] [min_events_per_sec]
#   motion-floor-check.sh <video> --donor <donor-video> [scene_threshold] [ratio]
#
#   scene_threshold    = порог сцен-детекции ffmpeg (дефолт 0.06, чувствительный)
#   min_events_per_sec = фиксированный пол PASS (дефолт 0.8) - слабый режим без донора
#   --donor            = ЭТАЛОН: замерить события/сек ДОНОРА и выставить порог = донор*ratio.
#                        Это канон закона (динамика НЕ ниже эталона-источника), не фикс-константа
#   ratio              = доля от донора (дефолт 0.8 = наш не ниже 80% динамики эталона)
#
# ЗАКОН (feedback_montage_dynamics_match_reference_highest_level): если у донора событие ~каждую
# секунду, у нас так же. Режим --donor делает это БЛОКИРУЮЩИМ (exit 1 если ниже), не декларацией
set -euo pipefail

usage(){ echo "Usage: motion-floor-check.sh <video> [--donor <donor-video>] [scene_thr] [min_eps|ratio]" >&2; exit 2; }
[[ $# -lt 1 || -z "${1:-}" ]] && usage

VIDEO="$1"; shift
DONOR=""
if [[ "${1:-}" == "--donor" ]]; then
  [[ -n "${2:-}" ]] || { echo "ОШИБКА: --donor без пути к файлу донора" >&2; exit 2; }
  DONOR="$2"; shift 2
fi
SCENE_THR="${1:-0.06}"
PARAM2="${2:-}"   # без донора = min_eps (0.8); с донором = ratio (0.8)

command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 || { echo "ОШИБКА: нужен ffmpeg/ffprobe" >&2; exit 1; }
[[ -f "$VIDEO" ]] || { echo "ОШИБКА: файл не найден: $VIDEO" >&2; exit 1; }

# events/sec для любого видео. Считаем РЕАЛЬНЫЕ детектированные сцен-кадры по токену ' pts_time:'
# (grep 'showinfo' ловил бы ещё 2 config-строки лога ffmpeg = завышение счёта). Длительность float,
# чтобы клипы <1с не обнулялись
measure_eps(){
  local v="$1"
  local d; d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v" 2>/dev/null)
  d="${d:-0}"
  # числовой guard ДО awk: N/A-длительность (raw-стримы/битые контейнеры) иначе даёт division-by-zero в stderr
  [[ "$d" =~ ^[0-9]+\.?[0-9]*$ ]] || { echo "0"; return; }
  awk "BEGIN{exit !($d>0)}" || { echo "0"; return; }
  local sc; sc=$(ffmpeg -i "$v" -vf "select='gt(scene,${SCENE_THR})',showinfo" -f null - 2>&1 | grep -c " pts_time:" || true)
  sc="${sc:-0}"
  awk -v s="$sc" -v d="$d" 'BEGIN{ if(d>0) printf "%.3f", s/d; else print "0" }'
}

our_eps=$(measure_eps "$VIDEO")
echo "Наш ролик:  событий/с = $our_eps"

if [[ -n "$DONOR" ]]; then
  [[ -f "$DONOR" ]] || { echo "ОШИБКА: донор не найден: $DONOR" >&2; exit 1; }
  ratio="${PARAM2:-0.8}"
  donor_eps=$(measure_eps "$DONOR")
  # донор со счётом 0 = битый/статичный/нечитаемый → порог 0 дал бы ложный PASS. Это НЕ валидный эталон
  if awk -v de="$donor_eps" 'BEGIN{exit !(de+0<=0)}'; then
    echo "Донор:      событий/с = $donor_eps" >&2
    echo "РЕЗУЛЬТАТ:  WARN - донор нечитаем/статичен (0 событий), порог невалиден. Проверь файл донора" >&2
    echo "  Массовая виралка не бывает статичной - вероятно битый забор. Сверь динамику глазами" >&2
    exit 0
  fi
  floor=$(awk -v de="$donor_eps" -v r="$ratio" 'BEGIN{ printf "%.3f", de*r }')
  echo "Донор:      событий/с = $donor_eps (эталон)"
  echo "Порог:      $floor (= донор × $ratio)"
  pass=$(awk -v e="$our_eps" -v m="$floor" 'BEGIN{ print (e+0 >= m+0) ? "1" : "0" }')
  if [[ "$pass" == "1" ]]; then
    echo "РЕЗУЛЬТАТ:  PASS - динамика не ниже эталона-донора (порог $floor)"
    exit 0
  else
    echo "РЕЗУЛЬТАТ:  FAIL - динамика НИЖЕ эталона-донора. Добрать движения в фазе 05 (закон motion-floor)" >&2
    echo "  Наш $our_eps < порог $floor. Ролик статичнее эталона = мы слабее, брак" >&2
    exit 1   # БЛОКИРУЮЩИЙ в режиме донора
  fi
else
  # слабый режим без донора: фикс-порог, WARN не блокирует
  MIN_EPS="${PARAM2:-0.8}"
  echo "Пол (фикс): $MIN_EPS (без донора - слабый режим, для точного бенчмарка дай --donor)"
  pass=$(awk -v e="$our_eps" -v m="$MIN_EPS" 'BEGIN{ print (e+0 >= m+0) ? "1" : "0" }')
  if [[ "$pass" == "1" ]]; then
    echo "РЕЗУЛЬТАТ:  PASS - динамика не ниже фикс-пола"
    exit 0
  else
    echo "РЕЗУЛЬТАТ:  WARN - динамика ниже фикс-пола. Точнее сверить с --donor" >&2
    exit 0
  fi
fi