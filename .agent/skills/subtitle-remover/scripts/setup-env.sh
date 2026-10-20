#!/usr/bin/env bash
# setup-env.sh — автоустановка окружения subtitle-remover (ProPainter + EAST) с нуля.
# Для новичка: запускается ОДИН раз (Claude запускает сам при первом использовании скилла,
# если окружение не найдено). Идемпотентно: готовые шаги пропускаются.
# Ставит: ~/propainter-lab/ (venv + ProPainter repo) + models/frozen_east_text_detection.pb.
# Веса ProPainter докачает сам inference_propainter.py при первом прогоне (официальный механизм).
set -uo pipefail

LAB="$HOME/propainter-lab"
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS="$SKILL/models"
EAST="$MODELS/frozen_east_text_detection.pb"

say() { printf '%s\n' "$*"; }
ok()  { say "[OK]   $*"; }
fail(){ say "[FAIL] $*"; }

say "== subtitle-remover: установка окружения (один раз, ~5-10 минут) =="

# 0. python3 + git
command -v python3 >/dev/null 2>&1 || { fail "нет python3 - поставь Python 3 с python.org и запусти меня снова"; exit 1; }
command -v git >/dev/null 2>&1 || { fail "нет git - поставь git (Mac: xcode-select --install) и запусти меня снова"; exit 1; }

# 1. ProPainter repo (официальный, публичный)
mkdir -p "$LAB"
if [ -d "$LAB/ProPainter/.git" ]; then
  ok "ProPainter уже склонирован"
else
  say "Клонирую ProPainter (официальный репозиторий)…"
  git clone --depth 1 https://github.com/sczhou/ProPainter "$LAB/ProPainter" \
    && ok "ProPainter склонирован" || { fail "clone не прошёл (проверь интернет)"; exit 1; }
fi

# 2. venv + зависимости (torch CPU/MPS сам подберётся под платформу)
if [ -x "$LAB/venv/bin/python" ]; then
  ok "venv уже создан"
else
  say "Создаю python-окружение…"
  python3 -m venv "$LAB/venv" || { fail "venv не создался"; exit 1; }
fi
say "Ставлю зависимости (torch/opencv - может занять несколько минут)…"
"$LAB/venv/bin/pip" install -q --upgrade pip
"$LAB/venv/bin/pip" install -q torch torchvision opencv-python numpy einops scipy tqdm av \
  && ok "зависимости стоят" || { fail "pip install не прошёл (см. вывод выше)"; exit 1; }

# 3. EAST text-detection модель (~95МБ, публичные зеркала)
mkdir -p "$MODELS"
if [ -s "$EAST" ]; then
  ok "EAST-модель уже на месте"
else
  say "Скачиваю EAST-модель (~95МБ)…"
  curl -fSL -o "$EAST" "https://github.com/oyyd/frozen_east_text_detection.pb/raw/master/frozen_east_text_detection.pb" \
    || curl -fSL -o "$EAST" "https://raw.githubusercontent.com/oyyd/frozen_east_text_detection.pb/master/frozen_east_text_detection.pb" \
    || { fail "EAST-модель не скачалась - проверь интернет и запусти меня снова"; exit 1; }
  ok "EAST-модель скачана"
fi

# 4. смоук: интерпретатор видит cv2+torch, inference на месте
"$LAB/venv/bin/python" -c "import cv2, torch" 2>/dev/null && ok "python-окружение живое (cv2+torch)" \
  || { fail "окружение не импортирует cv2/torch"; exit 1; }
[ -f "$LAB/ProPainter/inference_propainter.py" ] && ok "inference_propainter.py на месте" \
  || { fail "нет inference_propainter.py в клоне"; exit 1; }

say ""
ok "ГОТОВО. Окружение subtitle-remover установлено. Веса ProPainter докачаются сами при первом прогоне"