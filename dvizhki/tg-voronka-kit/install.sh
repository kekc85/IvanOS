#!/usr/bin/env bash
# Установка кита TG-воронок на сервер Ubuntu.
#
# Что делает по шагам:
#   1. проверяет Python 3 и ставит недостающее
#   2. кладёт кит в /opt/voronka (или туда, куда скажешь переменной VORONKA_HOME)
#   3. поднимает окружение и ставит зависимости
#   4. создаёт .env из образца, если его ещё нет
#   5. создаёт базу со схемой движка, если её ещё нет
#   6. прогоняет смоук-тесты: сеть при этом не трогается
#   7. ставит две службы - бот и сервис коротких ссылок
#   8. печатает, что делать дальше
#
# Повторный запуск безопасен: существующий .env и база не трогаются, файлы движка
# переписываются поверх. Ничего не удаляется.
#
# Настроить можно переменными окружения (по умолчанию не нужно):
#   VORONKA_HOME=/opt/voronka     куда положить движок
#   VORONKA_PORT=8799             порт сервиса коротких ссылок
#   VORONKA_USER=$(whoami)        от чьего имени работают службы
set -u

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${VORONKA_HOME:-/opt/voronka}"
PORT="${VORONKA_PORT:-8799}"
RUN_USER="${VORONKA_USER:-$(whoami)}"
STAMP="$(date +%Y%m%d-%H%M%S)"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
info() { printf '    %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
die()  { printf '\n  \033[31m✗ %s\033[0m\n\n' "$1" >&2; exit 1; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

printf '\n\033[1mУстановка движка воронок\033[0m\n'
info "движок: $HOME_DIR"
info "порт коротких ссылок: $PORT"
info "пользователь служб: $RUN_USER"

step "1/8 Python"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "Python 3 не найден. Поставь его: sudo apt update && sudo apt install -y python3 python3-venv"
ok "Python $("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
# ПРОВЕРЯЕМ ДЕЛОМ, А НЕ ИМПОРТОМ. На чистой Ubuntu 22.04 модуль venv импортируется,
# а окружение всё равно не создаётся: отсутствует ensurepip из пакета python3.10-venv.
# Замерено живым прогоном на свежей виртуалке: `import venv` прошёл, следом шаг 3 упал
# «ensurepip is not available». Поэтому пробуем создать окружение по-настоящему.
PYV="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
VENV_PROBE="$(mktemp -d)/probe"
if ! "$PY" -m venv "$VENV_PROBE" >/dev/null 2>&1; then
  warn "модуль venv не работает, ставлю пакет"
  sudo apt-get update -qq >/dev/null 2>&1
  sudo apt-get install -y "python${PYV}-venv" python3-venv >/dev/null 2>&1 \
    || sudo apt-get install -y python3-venv >/dev/null 2>&1 \
    || die "не смог поставить python3-venv. Сделай вручную: sudo apt install -y python${PYV}-venv"
  "$PY" -m venv "$VENV_PROBE" >/dev/null 2>&1 || die "окружение не создаётся даже после установки python${PYV}-venv"
fi
ok "venv работает"

step "2/8 Копирую движок"
sudo mkdir -p "$HOME_DIR" || die "нет прав на $HOME_DIR"
if [ -d "$HOME_DIR/engine" ]; then
  sudo cp -a "$HOME_DIR" "$HOME_DIR.backup-$STAMP" 2>/dev/null && ok "прежняя версия сохранена: $HOME_DIR.backup-$STAMP"
fi
for d in engine app tests funnels; do
  sudo mkdir -p "$HOME_DIR/$d"
  sudo cp -a "$KIT_DIR/$d/." "$HOME_DIR/$d/" || die "не скопировалось: $d"
done
sudo cp "$KIT_DIR/requirements.txt" "$KIT_DIR/pytest.ini" "$HOME_DIR/" 2>/dev/null
sudo chown -R "$RUN_USER":"$RUN_USER" "$HOME_DIR"
ok "движок на месте"

step "3/8 Окружение и зависимости"
# Проверяем НАЛИЧИЕ pip, а не папки. Прерванная установка оставляет пустую .venv,
# и проверка по папке пропускала создание: следом падало «pip: No such file».
# Замерено живым прогоном на свежей виртуалке в этом же заходе.
# Повторное создание поверх существующей папки безопасно и ничего не удаляет.
[ -x "$HOME_DIR/.venv/bin/pip" ] || "$PY" -m venv "$HOME_DIR/.venv" || die "не создалось окружение"
[ -x "$HOME_DIR/.venv/bin/pip" ] || die "окружение создано, но pip в нём нет: поставь пакет python${PYV}-venv"
"$HOME_DIR/.venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1
"$HOME_DIR/.venv/bin/pip" install -q -r "$HOME_DIR/requirements.txt" || die "зависимости не поставились"
ok "зависимости на месте"

step "4/8 Настройки"
if [ -f "$HOME_DIR/.env" ]; then
  ok ".env уже есть, не трогаю"
else
  sudo -u "$RUN_USER" cp "$KIT_DIR/.env.example" "$HOME_DIR/.env"
  ok ".env создан из образца"
  info "открой $HOME_DIR/.env и впиши токен бота от BotFather"
fi

step "5/8 База данных"
# ЗАЧЕМ ОТДЕЛЬНЫМ ШАГОМ. Раньше в ките лежал готовый файл voronka.sqlite с пустой
# схемой, и раздача везла двоичный файл. Пустая схема сегодня - это база с
# контактами завтра: один прогон движка у автора, и следующая пересборка увезла
# бы её ученикам. Схему умеет создавать сам движок (app/db.py, CREATE TABLE IF
# NOT EXISTS), поэтому она создаётся ЗДЕСЬ, на машине ученика, из его же кода.
# Повторный запуск безопасен: существующая база не трогается.
DB_FILE="${DB_PATH:-$HOME_DIR/voronka.sqlite}"
if [ -f "$DB_FILE" ]; then
  ok "база уже есть, не трогаю: $DB_FILE"
else
  if (cd "$HOME_DIR" && sudo -u "$RUN_USER" env DB_PATH="$DB_FILE" \
        "$HOME_DIR/.venv/bin/python" -c "import app.db, app.config; app.db.DB(app.config.DB_PATH)" >/dev/null 2>&1); then
    ok "база создана со схемой движка: $DB_FILE"
  else
    warn "база не создалась автоматически - движок создаст её при первом запуске"
  fi
fi

step "6/8 Смоук-тесты"
# СУДИМ ПО КОДУ ВОЗВРАТА САМИХ ТЕСТОВ, а не по коду конвейера с tail: прежняя форма
# печатала «тесты прошли» даже когда pytest вообще не запускался («No module named pytest»).
# Тихо зелёная проверка хуже отсутствующей: она врёт ровно там, где важна правда.
TEST_OUT="$(cd "$HOME_DIR" && PYTHONDONTWRITEBYTECODE=1 "$HOME_DIR/.venv/bin/python" -m pytest 2>&1)"
TEST_RC=$?
printf '%s\n' "$TEST_OUT" | tail -3
if [ "$TEST_RC" = "0" ]; then
  ok "тесты прошли, сеть не использовалась"
else
  warn "тесты НЕ прошли (код возврата $TEST_RC). Движок поставлен, но сначала разберись с выводом выше"
fi

step "7/8 Службы"
UNIT_BOT=/etc/systemd/system/voronka-bot.service
UNIT_WEB=/etc/systemd/system/voronka-redirect.service
sudo tee "$UNIT_BOT" >/dev/null <<UNIT
[Unit]
Description=Voronka bot
After=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$HOME_DIR
EnvironmentFile=$HOME_DIR/.env
ExecStart=$HOME_DIR/.venv/bin/python -m app.bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo tee "$UNIT_WEB" >/dev/null <<UNIT
[Unit]
Description=Voronka redirect service
After=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$HOME_DIR
EnvironmentFile=$HOME_DIR/.env
ExecStart=$HOME_DIR/.venv/bin/uvicorn app.redirect:app --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable voronka-redirect >/dev/null 2>&1 && ok "служба коротких ссылок включена"
info "бот НЕ запускается автоматически: сначала впиши токен в .env"
info "когда впишешь: sudo systemctl enable --now voronka-bot"

step "8/8 Что дальше"
cat <<TXT

  1. Впиши токен бота:            nano $HOME_DIR/.env
  2. Запусти бота:                sudo systemctl enable --now voronka-bot
  3. Посмотри, что он живой:      sudo systemctl status voronka-bot
  4. Положи свою воронку сюда:    $HOME_DIR/funnels/voronka-СЛОВО.json
  5. Перезапусти бота:            sudo systemctl restart voronka-bot

  Короткие ссылки слушают только localhost на порту $PORT: наружу их выводит nginx,
  как описано в КАК-УСТАНОВИТЬ.txt. Без домена бот работает, ссылки просто идут прямыми

TXT
ok "готово"
