#!/usr/bin/env bash
# Установщик планировщика для macOS.
#
# Что делает по шагам:
#   1. проверяет Python 3
#   2. разворачивает движок в ~/planner
#   3. создаёт ~/planner-data из шаблонов, НЕ трогая то, что там уже лежит
#   4. ставит автозапуск сервера
#   5. ставит расписание четырёх ритуалов
#   6. открывает браузер
#   7. рассказывает человеческим языком, что дальше
#
# Запускать без sudo. Повторный запуск безопасен: всё, что уже стоит,
# переставляется поверх, а данные не трогаются вообще. Перед перезаписью
# движка и служб делается бэкап.
#
# Настроить можно переменными окружения (по умолчанию не нужно):
#   PLANNER_HOME=~/planner        куда положить движок
#   PLANNER_DATA=~/planner-data   где держать данные
#   PLANNER_PORT=8791             на каком порту поднять интерфейс

set -u

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANNER_HOME="${PLANNER_HOME:-$HOME/planner}"
PLANNER_DATA="${PLANNER_DATA:-$HOME/planner-data}"
PLANNER_PORT="${PLANNER_PORT:-8791}"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LABEL_PREFIX="local.planner"
STAMP="$(date +%Y%m%d-%H%M%S)"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
info() { printf '    %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
die()  { printf '\n  \033[31m✗ %s\033[0m\n\n' "$1" >&2; exit 1; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

printf '\n\033[1mУстановка планировщика\033[0m\n'
info "движок:  $PLANNER_HOME"
info "данные:  $PLANNER_DATA"
info "порт:    $PLANNER_PORT"

# ---------------------------------------------------------------- 1. Python 3
step "1/7 Проверяю Python 3"

PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "Python 3 не найден. Поставь его с python.org (кнопка «Download Python»), потом запусти этот установщик снова"

PY_VER="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
[ -n "$PY_VER" ] || die "Python 3 нашёлся ($PY), но не запускается. Переустанови его с python.org"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
  || die "Нужен Python 3.8 или новее, а стоит $PY_VER. Обнови его с python.org"
ok "Python $PY_VER: $PY"

# ---------------------------------------------------------------- 2. движок
step "2/7 Разворачиваю движок"

[ -d "$KIT_DIR/engine" ] || die "В ките нет папки engine. Распакуй архив целиком и запускай установщик из него"

if [ -d "$PLANNER_HOME" ]; then
  BACKUP="$PLANNER_HOME.backup-$STAMP"
  cp -R "$PLANNER_HOME" "$BACKUP" 2>/dev/null && ok "старый движок сохранён: $BACKUP" \
    || warn "не получилось сделать бэкап старого движка, продолжаю"
fi

mkdir -p "$PLANNER_HOME" || die "не могу создать $PLANNER_HOME"
cp -R "$KIT_DIR/engine/." "$PLANNER_HOME/" || die "не скопировался движок в $PLANNER_HOME"
# 🔴 Установщик НИЧЕГО не удаляет на твоей машине. Кэш байткода, приехавший
# вместе с китом, питон подхватывать не должен - но вместо удаления папка
# ПЕРЕИМЕНОВЫВАЕТСЯ рядом: питон её больше не видит, а ты видишь и можешь
# посмотреть, что там лежало
find "$PLANNER_HOME" -name '__pycache__' -type d -print 2>/dev/null | while IFS= read -r d; do
  [ -d "$d" ] && mv "$d" "$d.staroe-$STAMP" 2>/dev/null
done
ok "движок на месте: $PLANNER_HOME"

"$PY" -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$PLANNER_HOME/server.py" \
  || die "server.py не разбирается этим Python. Скорее всего кит распаковался наполовину"
ok "server.py читается без ошибок"

# ---------------------------------------------------------------- 3. данные
step "3/7 Готовлю папку данных"

"$PY" "$PLANNER_HOME/tools/seed_data.py" \
  --templates "$KIT_DIR/data-template" --target "$PLANNER_DATA" | sed 's/^/    /' \
  || die "не получилось разложить шаблоны в $PLANNER_DATA"
ok "данные в $PLANNER_DATA (существующие файлы не тронуты)"

# ---------------------------------------------------------------- 4-5. службы
# Абсолютный путь к python пишем в plist потому, что launchd не читает твой
# .zshrc и PATH у него свой. Путь берём ИЗ PATH (command -v), не хардкодим -
# иначе установка ломается на любой машине с другим питоном.
PY_DIR="$(dirname "$PY")"
AGENT_PATH="$PY_DIR:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "$AGENTS_DIR" "$PLANNER_DATA/logs"

write_plist() {
  # write_plist <короткое имя> <скрипт> <блок расписания>
  local name="$1" script="$2" schedule="$3"
  local label="$LABEL_PREFIX.$name"
  local plist="$AGENTS_DIR/$label.plist"

  if [ -f "$plist" ]; then
    cp "$plist" "$PLANNER_DATA/backups/$label.plist.backup-$STAMP" 2>/dev/null || true
  fi

  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$label</string>
	<key>ProgramArguments</key>
	<array>
		<string>$PY</string>
		<string>$PLANNER_HOME/$script</string>
	</array>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>$AGENT_PATH</string>
		<key>PLANNER_DATA</key>
		<string>$PLANNER_DATA</string>
		<key>PLANNER_PORT</key>
		<string>$PLANNER_PORT</string>
	</dict>
$schedule
	<key>StandardOutPath</key>
	<string>$PLANNER_DATA/logs/$name.log</string>
	<key>StandardErrorPath</key>
	<string>$PLANNER_DATA/logs/$name.err</string>
</dict>
</plist>
PLIST

  # bootout+bootstrap - современный путь; на старых системах падаем на load/unload
  launchctl bootout "gui/$UID/$label" >/dev/null 2>&1
  if launchctl bootstrap "gui/$UID" "$plist" >/dev/null 2>&1; then
    ok "$label"
  elif { launchctl unload "$plist" >/dev/null 2>&1; launchctl load "$plist" >/dev/null 2>&1; }; then
    ok "$label (через load)"
  else
    warn "$label записан в $plist, но launchctl его не принял. Перезайди в систему - он подхватится при входе"
  fi
}

# RunAtLoad ритуалам НЕ ставим намеренно: launchd и так догоняет пропущенный
# StartCalendarInterval после пробуждения ноута, а RunAtLoad заставлял бы сторожа
# кричать сразу после установки - когда вчерашнего отчёта ещё физически нет.
daily_at() {
  printf '\t<key>StartCalendarInterval</key>\n\t<dict>\n\t\t<key>Hour</key>\n\t\t<integer>%s</integer>\n\t\t<key>Minute</key>\n\t\t<integer>%s</integer>\n\t</dict>\n' "$1" "$2"
}

weekly_at() {
  printf '\t<key>StartCalendarInterval</key>\n\t<dict>\n\t\t<key>Weekday</key>\n\t\t<integer>%s</integer>\n\t\t<key>Hour</key>\n\t\t<integer>%s</integer>\n\t\t<key>Minute</key>\n\t\t<integer>%s</integer>\n\t</dict>\n' "$1" "$2" "$3"
}

step "4/7 Ставлю автозапуск сервера"
write_plist "server" "server.py" \
  "$(printf '\t<key>RunAtLoad</key>\n\t<true/>\n\t<key>KeepAlive</key>\n\t<true/>\n')"

step "5/7 Ставлю расписание ритуалов"
write_plist "daily-open"  "rituals/daily_open.py"  "$(daily_at 9 0)"
write_plist "daily-close" "rituals/daily_close.py" "$(daily_at 21 30)"
write_plist "wam"         "rituals/wam.py"         "$(weekly_at 6 20 0)"
write_plist "watchdog"    "rituals/watchdog.py"    "$(daily_at 13 0)"
info "утро 09:00 сводка · вечер 21:30 закрытие дня · суббота 20:00 разбор недели · день 13:00 сторож"

# ---------------------------------------------------------------- 6. браузер
step "6/7 Поднимаю интерфейс"

URL="http://localhost:$PLANNER_PORT"
ALIVE=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 2 "$URL/api/where" >/dev/null 2>&1; then ALIVE="yes"; break; fi  # /api/config у движка нет, он отвечал 404
  sleep 1
done

if [ -n "$ALIVE" ]; then
  ok "сервер отвечает на $URL"
  open "$URL" >/dev/null 2>&1 && info "браузер открыт" || info "открой в браузере: $URL"
else
  warn "сервер пока не ответил. Загляни в $PLANNER_DATA/logs/server.err и запусти mac/check.sh"
fi

# ---------------------------------------------------------------- 7. что дальше
step "7/7 Готово. Что делать дальше"

cat <<TXT

  Планировщик живёт по адресу $URL - открывай его как обычный сайт,
  можно положить в закладки. Интернет ему не нужен, всё работает офлайн.

  Первым делом:
    1. Зайди во вкладку «Настройки» и выставь свой режим дня. Вся сетка
       считается от него, пока цифры не твои - день на экране чужой
    2. Открой «Как пользоваться» в шапке, это пять минут чтения
    3. Замени примеры своими задачами и целями, примеры для того и лежат

  Дальше движок работает сам: утром собирает сводку дня, вечером закрывает
  день и переносит несделанное, в субботу вечером считает разбор недели,
  днём сторож проверяет, что система жива, а не крутится вхолостую.

  Твои данные:   $PLANNER_DATA
  Проверка:      bash "$KIT_DIR/mac/check.sh"
  Снять службы:  launchctl bootout gui/$UID/$LABEL_PREFIX.server (и так же остальные)

TXT
