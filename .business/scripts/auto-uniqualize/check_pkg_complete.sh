#!/bin/bash
# Гейт полноты выдачи (урок по решению автора): после прогона сверить НОМЕРА слайдов, не счётчик.
# «успех 3/9» НЕ значит слайды 1,2,3 - в ночном батче по решению автора первые прогоны сохранили 01/05/09,
# а пропуск 02-03 заметили только при ручном пересчёте.
# Usage: check_pkg_complete.sh <package-id>   (queue/<id>/slide-NN.{jpg,txt} vs output/<id>/slide-NN.png)
set -u
BASE=~/.business/scripts/auto-uniqualize
ID="$1"
missing=0
for t in "$BASE/queue/$ID"/slide-*.txt; do
  [ -e "$t" ] || continue
  n=$(basename "$t" .txt | sed 's/slide-//')
  if [ ! -f "$BASE/output/$ID/slide-$n.png" ]; then
    echo "MISSING slide-$n.png"
    missing=1
  fi
done
# CTA-промпты тоже должны иметь выдачу
for c in "$BASE/queue/$ID"/cta/prompt-*.txt; do
  [ -e "$c" ] || continue
  n=$(basename "$c" .txt | sed 's/prompt-//')
  if [ ! -f "$BASE/output/$ID/slide-$n.png" ]; then
    echo "MISSING CTA slide-$n.png"
    missing=1
  fi
done
# дубли по md5
d=$(md5 -r "$BASE/output/$ID"/*.png 2>/dev/null | awk '{print $1}' | sort | uniq -d | wc -l | tr -d ' ')
[ "$d" != "0" ] && { echo "DUPLICATE md5: $d"; missing=1; }
[ "$missing" = "0" ] && echo "COMPLETE: все номера на месте, дублей нет"
exit $missing
