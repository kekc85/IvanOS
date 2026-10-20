#!/usr/bin/env bash
# setup-env.sh — автоустановка hyperframes-checkout для embedded-captions с нуля.
# Скрипты скилла (check-occlusion.cjs, render-and-composite.sh) ищут SOURCE-checkout
# hyperframes (packages/cli/dist/cli.js + node_modules с sharp/puppeteer) - npx-пакета
# им мало. Репозиторий публичный (github.com/heygen-com/hyperframes) - клонируем в
# ~/Downloads/hyperframes (один из путей, которые скрипты уже умеют резолвить) и собираем.
# Идемпотентно; Claude запускает сам при первом использовании, если checkout не найден.
set -uo pipefail

DST="$HOME/Downloads/hyperframes"
say() { printf '%s\n' "$*"; }
ok()  { say "[OK]   $*"; }
fail(){ say "[FAIL] $*"; }

say "== embedded-captions: установка hyperframes-checkout (один раз) =="
command -v git  >/dev/null 2>&1 || { fail "нет git - поставь (Mac: xcode-select --install) и запусти снова"; exit 1; }
command -v node >/dev/null 2>&1 || { fail "нет node - установщик IvanOS ставит его; поставь Node LTS и запусти снова"; exit 1; }

if [ -d "$DST/.git" ]; then
  ok "checkout уже есть: $DST"
else
  say "Клонирую hyperframes (публичный репозиторий)…"
  git clone --depth 1 https://github.com/heygen-com/hyperframes "$DST" \
    && ok "склонирован" || { fail "clone не прошёл (проверь интернет)"; exit 1; }
fi

cd "$DST" || exit 1
if [ -f "packages/cli/dist/cli.js" ]; then
  ok "cli уже собран"
else
  say "Ставлю зависимости и собираю (npm - несколько минут)…"
  npm install --no-fund --no-audit >/dev/null 2>&1 || { fail "npm install не прошёл"; exit 1; }
  npm run build >/dev/null 2>&1 || true
  [ -f "packages/cli/dist/cli.js" ] && ok "cli собран" \
    || { fail "packages/cli/dist/cli.js не появился после сборки - покажи вывод npm run build"; exit 1; }
fi

node -e "require('$DST/packages/cli/dist/cli.js')" 2>/dev/null || true
ok "ГОТОВО. Скрипты скилла найдут checkout в $DST"