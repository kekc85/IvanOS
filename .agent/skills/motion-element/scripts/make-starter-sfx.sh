#!/usr/bin/env bash
# make-starter-sfx.sh — синтезирует стартовый $0 SFX-пак через FFmpeg (без скачиваний/ключей).
# Это заглушки-плейсхолдеры, чтобы аудио-путь работал e2e сразу. Для финала заменить на
# реальные CC0-сэмплы (Pixabay/Freesound — knowledge/free-audio-sources.md).
# Usage: make-starter-sfx.sh <out_dir>   (default ./sfx)
set -euo pipefail
OUT="${1:-sfx}"; mkdir -p "$OUT"
SR=48000
g() { ffmpeg -y -f lavfi -i "$1" -ar $SR -ac 1 "$OUT/$2" >/dev/null 2>&1; echo "  $2"; }

echo "synth SFX → $OUT/"
# pop: короткий высокий блип с быстрым затуханием
g "sine=frequency=620:duration=0.09,afade=t=out:st=0.02:d=0.07" pop.wav
# tick: очень короткий клик
g "sine=frequency=1200:duration=0.04,afade=t=out:st=0.005:d=0.035" tick.wav
# click: щелчок
g "sine=frequency=900:duration=0.05,afade=t=out:st=0.01:d=0.04" click.wav
# ding: колокольчик
g "sine=frequency=880:duration=0.4,afade=t=out:st=0.05:d=0.35" ding.wav
# clink: монетный звон
g "sine=frequency=1500:duration=0.18,afade=t=out:st=0.02:d=0.16" clink.wav
# impact: низкий удар
g "sine=frequency=90:duration=0.28,afade=t=out:st=0.03:d=0.25" impact.wav
# whoosh: шумовой свип
g "anoisesrc=d=0.35:c=pink:a=0.4,afade=t=in:st=0:d=0.12,afade=t=out:st=0.18:d=0.17" whoosh.wav
# riser: нарастание
g "sine=frequency=300:duration=0.6,afade=t=in:st=0:d=0.55" riser.wav
# swipe: короткий шумовой свайп
g "anoisesrc=d=0.18:c=white:a=0.3,afade=t=out:st=0.04:d=0.14" swipe.wav
# typewriter: щелчок клавиши
g "anoisesrc=d=0.03:c=white:a=0.5" typewriter.wav
echo "done: 10 sfx ($OUT)"
