#!/usr/bin/env bash
# Живая самопроверка планировщика на macOS.
#
# Проверяет ровно четыре вещи и по каждой отвечает честно:
#   1. сервер отвечает или нет
#   2. данные на месте и читаются
#   3. расписание стоит
#   4. ритуалы реально запускаются (прогон в песочнице, рабочие данные не трогаем)
#
# При проблеме печатает, что именно чинить. Выход 0 - всё дышит, 1 - есть что чинить.

set -u

PLANNER_HOME="${PLANNER_HOME:-$HOME/planner}"
PLANNER_DATA="${PLANNER_DATA:-$HOME/planner-data}"
PLANNER_PORT="${PLANNER_PORT:-8791}"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LABEL_PREFIX="local.planner"
URL="http://localhost:$PLANNER_PORT"
PROBLEMS=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; PROBLEMS=$((PROBLEMS+1)); }
fix()  { printf '      \033[33m→ чинить так:\033[0m %s\n' "$1"; }
info() { printf '    %s\n' "$1"; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

printf '\n\033[1mПроверка планировщика\033[0m\n'
info "движок: $PLANNER_HOME"
info "данные: $PLANNER_DATA"
info "адрес:  $URL"

PY="$(command -v python3 || true)"

# ---------------------------------------------------------------- 1. сервер
step "1/4 Сервер"

if [ -z "$PY" ]; then
  bad "Python 3 не найден"
  fix "поставь Python с python.org и запусти mac/install.sh заново"
else
  ok "Python $("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])'): $PY"
fi

if [ ! -f "$PLANNER_HOME/server.py" ]; then
  bad "движка нет: $PLANNER_HOME/server.py не найден"
  fix "bash mac/install.sh"
else
  ok "движок на месте"
fi

# Пульс сервера снимается с /api/where. Прежде тут стоял /api/config, эндпоинта с таким
# именем у движка нет вовсе: живой сервер отвечал на него 404, curl -f возвращал ошибку,
# и самопроверка на ПОЛНОСТЬЮ рабочем ките печатала «сервер не отвечает» и звала
# переустановку. Настройки модулей лежат файлом в папке данных, по HTTP их не отдают.
if curl -fsS --max-time 3 "$URL/api/where" >/dev/null 2>&1; then
  ok "сервер отвечает на $URL"
  CFG="$(cat "$PLANNER_DATA/config.json" 2>/dev/null || true)"
  if printf '%s' "$CFG" | grep -q 'eveningCheckin'; then
    if printf '%s' "$CFG" | grep -q '"enabled": *false'; then
      info "вечерний чек-ин выключен в config.json - так и задумано, если ты его выключал"
    else
      ok "вечерний чек-ин включён"
    fi
  fi
  if curl -fsS --max-time 3 "$URL/" 2>/dev/null | grep -q 'tab-week.js'; then
    ok "страница интерфейса отдаётся"
  else
    bad "сервер жив, но страница интерфейса не отдалась"
    fix "проверь, что папка $PLANNER_HOME/static не пустая, потом bash mac/install.sh"
  fi
else
  bad "сервер не отвечает на $URL"
  if lsof -nP -iTCP:"$PLANNER_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    fix "порт $PLANNER_PORT занят кем-то другим. Переустанови на другом порту: PLANNER_PORT=8792 bash mac/install.sh"
  else
    fix "launchctl kickstart -k gui/$UID/$LABEL_PREFIX.server ; смотри ошибку в $PLANNER_DATA/logs/server.err"
  fi
fi

# ---------------------------------------------------------------- 2. данные
step "2/4 Данные"

if [ ! -d "$PLANNER_DATA" ]; then
  bad "папки данных нет: $PLANNER_DATA"
  fix "bash mac/install.sh"
else
  ok "папка данных на месте"
  for f in sprint.json profile.json goals-cycle.json tracker.json; do
    p="$PLANNER_DATA/$f"
    if [ ! -f "$p" ]; then
      bad "нет файла $f"
      fix "bash mac/install.sh (существующие файлы он не тронет, добавит только недостающие)"
    elif [ -n "$PY" ] && ! "$PY" -c "import json,sys;json.load(open(sys.argv[1],encoding='utf-8'))" "$p" >/dev/null 2>&1; then
      bad "$f не читается как JSON"
      LAST="$(ls -t "$PLANNER_DATA/backups/" 2>/dev/null | head -1)"
      if [ -n "$LAST" ]; then
        fix "верни последний снимок: cp \"$PLANNER_DATA/backups/$LAST\" \"$p\""
      else
        fix "снимков нет. Удали битый файл и запусти bash mac/install.sh - он положит чистый шаблон"
      fi
    else
      ok "$f читается"
    fi
  done
  SNAPS="$(ls "$PLANNER_DATA/backups/" 2>/dev/null | wc -l | tr -d ' ')"
  info "снимков в backups: $SNAPS"
fi

# ---------------------------------------------------------------- 3. расписание
step "3/4 Расписание"

for name in server daily-open daily-close wam watchdog; do
  label="$LABEL_PREFIX.$name"
  if [ ! -f "$AGENTS_DIR/$label.plist" ]; then
    bad "$name: службы нет"
    fix "bash mac/install.sh"
    continue
  fi
  if launchctl print "gui/$UID/$label" >/dev/null 2>&1; then
    ok "$name: стоит и загружена"
  else
    bad "$name: файл службы есть, но launchd её не держит"
    fix "launchctl bootstrap gui/$UID \"$AGENTS_DIR/$label.plist\""
  fi
done

# ---------------------------------------------------------------- 4. ритуалы
step "4/4 Ритуалы"

if [ -z "$PY" ] || [ ! -d "$PLANNER_HOME/rituals" ]; then
  bad "ритуалов нет: $PLANNER_HOME/rituals"
  fix "bash mac/install.sh"
else
  SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/planner-check.XXXXXX")"
  # Гоняем ритуалы в песочнице: PLANNER_TEST_ROOT уводит ВСЕ пути внутрь неё,
  # поэтому проверка не может испортить твой реальный план и не покажет окон.
  mkdir -p "$SANDBOX/planner-data"
  for f in sprint.json profile.json goals-cycle.json tracker.json; do
    [ -f "$PLANNER_DATA/$f" ] && cp "$PLANNER_DATA/$f" "$SANDBOX/planner-data/$f" 2>/dev/null
  done
  for r in daily_open daily_close wam watchdog; do
    OUT="$(PLANNER_TEST_ROOT="$SANDBOX" PLANNER_NO_NOTIFY=1 "$PY" "$PLANNER_HOME/rituals/$r.py" 2>&1)"
    CODE=$?
    # watchdog осознанно выходит 1, когда видит проблему - это не поломка ритуала
    if printf '%s' "$OUT" | grep -q "УПАЛ\|Traceback"; then
      bad "$r: падает"
      printf '%s\n' "$OUT" | tail -5 | sed 's/^/        /'
      fix "покажи эти строки тому, кто выдал кит: ритуал не должен падать"
    elif [ "$CODE" -ne 0 ] && [ "$r" != "watchdog" ]; then
      bad "$r: вышел с кодом $CODE"
      fix "запусти руками и посмотри вывод: $PY $PLANNER_HOME/rituals/$r.py"
    else
      ok "$r: запускается"
    fi
  done
  # 🔴 Песочница НЕ стирается. Проверка ничего не удаляет на твоей машине -
  # ни своего, ни тем более твоего. Папка лежит во временном каталоге системы,
  # система убирает его сама, а пока она есть - в неё можно заглянуть и увидеть,
  # что именно проверка делала
  printf '        песочница проверки осталась лежать: %s\n' "$SANDBOX"
fi

# ---------------------------------------------------------------- итог
printf '\n'
if [ "$PROBLEMS" -eq 0 ]; then
  printf '\033[32m\033[1mВсё дышит.\033[0m Планировщик открывается на %s\n\n' "$URL"
  exit 0
fi
printf '\033[31m\033[1mНашлось проблем: %s.\033[0m Что чинить - написано выше стрелкой →\n\n' "$PROBLEMS"
exit 1
