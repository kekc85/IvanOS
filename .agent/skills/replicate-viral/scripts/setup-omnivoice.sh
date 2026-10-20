#!/usr/bin/env bash
# setup-omnivoice.sh — автоустановка локального клона голоса (OmniVoice) с нуля.
# Для новичка: Claude запускает сам, когда выбран Вариант A (OmniVoice) и окружения нет.
# Идемпотентно. Референс голоса - СВОЙ у каждого (BYOA): 3-10 сек чистой записи,
# скилл попросит записать и положит рядом (ref_voice.wav + ref_text.txt с дословной расшифровкой).
# Веса модели качаются с HuggingFace сами при первом прогоне omnivoice-tts.py.
set -uo pipefail

VENVS="$HOME/IvanOS/.venvs"
VENV="$VENVS/omnivoice"
say() { printf '%s\n' "$*"; }
ok()  { say "[OK]   $*"; }
fail(){ say "[FAIL] $*"; }

say "== OmniVoice: установка окружения клона голоса (один раз, несколько минут) =="
command -v python3 >/dev/null 2>&1 || { fail "нет python3 - поставь Python 3 с python.org и запусти меня снова"; exit 1; }

mkdir -p "$VENVS"
if [ -x "$VENV/bin/python" ]; then
  ok "venv уже создан"
else
  python3 -m venv "$VENV" || { fail "venv не создался"; exit 1; }
fi
say "Ставлю зависимости (torch - может занять несколько минут)…"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q torch soundfile omnivoice \
  && ok "зависимости стоят" || { fail "pip install не прошёл (см. вывод выше)"; exit 1; }

"$VENV/bin/python" - <<'PY' 2>/dev/null && echo "[OK]    okружение импортируется" || { echo "[FAIL] импорт не прошёл"; exit 1; }
import torch, soundfile
PY

say ""
ok "ГОТОВО. Запуск озвучки: $VENV/bin/python scripts/omnivoice-tts.py \"<текст>\" <ref_voice.wav> <ref_text.txt> <out.wav>"
say "Референс голоса: запиши СВОИ 3-10 секунд чистой речи (тихая комната, один дубль) - скилл попросит и сохранит"
say "Веса модели скачаются сами при первом прогоне (HuggingFace)"