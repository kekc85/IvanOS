#!/usr/bin/env bash
# render-element.sh — собрать и отрендерить motion-элемент по шаблону.
# Usage: render-element.sh <template_id> <slug> [--mute] [--no-watermark]
# Требует: Node >=22, FFmpeg, Chrome (npx hyperframes doctor). Docker НЕ нужен.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${1:?template_id required}"; SLUG="${2:?slug required}"; shift 2 || true
DATE="$(date +%Y-%m-%d)"
OUT_ROOT="$HOME/.business/growth/motion-elements"
PROJ="$OUT_ROOT/$DATE-$SLUG"

TPL_DIR="$SKILL_DIR/templates/$TEMPLATE"
[ -f "$TPL_DIR/index.html" ] || { echo "FAIL: template $TEMPLATE not built yet (см. prompts/02-templates.md Build status)"; exit 1; }

mkdir -p "$OUT_ROOT"
( cd "$OUT_ROOT" && npx --yes hyperframes init "$DATE-$SLUG" >/dev/null 2>&1 || true )
cp "$TPL_DIR/index.html" "$PROJ/index.html"
[ -f "$TPL_DIR/params.json" ] && cp "$TPL_DIR/params.json" "$PROJ/params.json"

echo "== determinism gate =="
if grep -nE "Math\.random|setInterval|Date\.now" "$PROJ/index.html"; then
  echo "FAIL: non-deterministic code in composition"; exit 1
fi
echo "OK deterministic"

echo "== lint =="
( cd "$PROJ" && npx --yes hyperframes lint 2>&1 | tail -3 )

echo "== render =="
( cd "$PROJ" && npx --yes hyperframes render 2>&1 | tail -3 )

echo "== output =="
find "$PROJ/renders" -name "*.mp4" 2>/dev/null | tail -1
echo "Проект: $PROJ"
echo "Дальше: аудио (prompts/03-audio.md), output-mode (transparent/composite/recolor), визуальный+аудио ревью ДО выдачи."