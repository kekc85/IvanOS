#!/usr/bin/env bash
# setup-permissions.sh — ставится ОДИН раз учеником.
# После прогона скилл website больше не дёргает «разрешаю …»:
#   1) идемпотентно мёржит КОНКРЕТНЫЙ website-allow-list в ~/.claude/settings.json
#      (не blanket Bash — точечные паттерны команд скилла; без дублей; чужое не ломаем)
#   2) ставит зависимость рендер-гейта: playwright chromium (+ проверка node)
#
# ВАЖНО: exit 0 = успех, exit 2 = ошибка окружения (node/python нет). Никогда не 1.
# Скрипт правит settings.json В КОПИИ или боевой — зависит от TARGET (по умолчанию боевой).
# Оркестратор может переопределить путь: SETTINGS_PATH=/tmp/x.json bash setup-permissions.sh

set -uo pipefail

SETTINGS_PATH="${SETTINGS_PATH:-$HOME/.claude/settings.json}"
SKIP_PLAYWRIGHT="${SKIP_PLAYWRIGHT:-0}"

# ── 0. проверка python3 ─────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  echo "setup-permissions: python3 не найден — нужен для мёржа settings.json" >&2
  exit 2
fi

# ── 1. идемпотентный мёрж allow-list через python3 ──────────────────
# Allow-list = реальные команды воркфлоу website (изучены в scripts/*.* и workflow/*.md):
#   локальный превью-сервер, рендер/аудит-гейты, копи-линт, refs-валидатор,
#   journey-map / deploy / scarcity / phase-tracker / orphan аудиты, grep/node,
#   плюс MCP (Stitch визуал-направления, playwright рендер) и Read/Write/Edit.
python3 - "$SETTINGS_PATH" <<'PYEOF'
import json, os, sys

settings_path = sys.argv[1]

# Конкретные паттерны (НЕ blanket "Bash"). Двойной хвост ":*" покрывает и
# `python3 scripts/x.py …` и `python3 ~/.claude/skills/website/scripts/x.py …`.
WEBSITE_ALLOW = [
    # — локальный превью-сервер (показ экранов автору ссылкой http://localhost) —
    "Bash(python3 -m http.server:*)",
    # — скрипты-гейты скилла website (по basename, путь любой) —
    "Bash(python3 *show-screen.py:*)",
    "Bash(python3 *copy-lint.py:*)",
    "Bash(python3 *validate-refs.py:*)",
    "Bash(python3 *journey-map-audit.py:*)",
    "Bash(python3 *check-deploy.py:*)",
    "Bash(python3 *scarcity-counter-audit.py:*)",
    "Bash(python3 *phase-tracker.py:*)",
    "Bash(python3 *orphan-scan.py:*)",
    # — node-гейты рендера/лейаута/регрессии —
    "Bash(node *layout-audit.mjs:*)",
    "Bash(node *regression-check.mjs:*)",
    # — установка движка рендер-гейта —
    "Bash(npx playwright install:*)",
    # — служебное: grep живого билда, node версия —
    "Bash(grep:*)",
    "Bash(node --version:*)",
    # — файловые инструменты (правка билда без подтверждений) —
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    # — MCP: Stitch (визуал-направления) —
    "mcp__stitch__create_project",
    "mcp__stitch__generate_screen_from_text",
    "mcp__stitch__generate_variants",
    "mcp__stitch__edit_screens",
    "mcp__stitch__get_screen",
    "mcp__stitch__list_screens",
    "mcp__stitch__create_design_system",
    "mcp__stitch__apply_design_system",
    "mcp__stitch__create_design_system_from_design_md",
    "mcp__stitch__upload_design_md",
    # — MCP: playwright (рендер/скриншот-проверка) —
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_resize",
]

# Загрузка существующего settings.json (или пустой каркас) — чужое сохраняем.
if os.path.exists(settings_path):
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print("setup-permissions: settings.json повреждён (невалидный JSON): %s" % e,
              file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print("setup-permissions: корень settings.json не объект — не трогаю", file=sys.stderr)
        sys.exit(2)
else:
    data = {}

perms = data.get("permissions")
if not isinstance(perms, dict):
    perms = {}
allow = perms.get("allow")
if not isinstance(allow, list):
    allow = []

existing = set(allow)
added = []
for pat in WEBSITE_ALLOW:
    if pat not in existing:        # идемпотентность: без дублей
        allow.append(pat)
        existing.add(pat)
        added.append(pat)

perms["allow"] = allow
data["permissions"] = perms

# Атомарная запись.
os.makedirs(os.path.dirname(settings_path) or ".", exist_ok=True)
tmp = settings_path + ".tmp.setup-perms"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
os.replace(tmp, settings_path)

if added:
    print("setup-permissions: добавлено %d паттернов:" % len(added))
    for p in added:
        print("  + " + p)
else:
    print("setup-permissions: все website-паттерны уже на месте (идемпотентно, без правок).")
PYEOF
merge_rc=$?
if [ "$merge_rc" -ne 0 ]; then
  # python вышел с 2 (или иным) — пробрасываем как ошибку окружения, не 1.
  exit 2
fi

# ── 2. зависимости рендер-гейта: node + playwright chromium ─────────
if ! command -v node >/dev/null 2>&1; then
  echo "setup-permissions: node не найден — рендер-гейт (layout-audit.mjs/playwright) не заработает." >&2
  echo "  Поставь Node.js LTS (https://nodejs.org) и перезапусти этот скрипт." >&2
  exit 2
fi
echo "setup-permissions: node $(node --version) ок."

if [ "$SKIP_PLAYWRIGHT" = "1" ]; then
  echo "setup-permissions: SKIP_PLAYWRIGHT=1 — пропускаю установку chromium."
else
  echo "setup-permissions: ставлю playwright chromium (один раз, может занять минуту)…"
  if npx --yes playwright install chromium; then
    echo "setup-permissions: playwright chromium установлен."
  else
    echo "setup-permissions: не удалось поставить chromium через npx playwright install." >&2
    echo "  Проверь сеть/доступ и запусти вручную: npx playwright install chromium" >&2
    exit 2
  fi
fi

echo "setup-permissions: готово. Скилл website больше не будет спрашивать «разрешаю …» по своим командам."
exit 0
