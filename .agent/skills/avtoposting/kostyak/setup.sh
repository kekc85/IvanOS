#!/usr/bin/env bash
# Установка движка автопостинга на macOS и Linux.
# Ровно 7 шагов, те же самые и в том же порядке, что в setup.ps1 для Windows.
# Запуск:  bash setup.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

step() { printf '\nШАГ %s/7 %s\n' "$1" "$2"; }
ok()   { printf '  готово: %s\n' "$1"; }
warn() { printf '  внимание: %s\n' "$1"; }

PY=""
step 1 "проверяю питон"
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$candidate"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  warn "питон 3.9 или новее не найден. Поставь его и запусти setup.sh заново"
  exit 1
fi
ok "$($PY --version 2>&1)"

step 2 "ставлю зависимости"
if $PY -c 'import httpx' >/dev/null 2>&1; then
  ok "httpx уже стоит"
else
  $PY -m pip install --quiet -r requirements.txt \
    || $PY -m pip install --quiet --break-system-packages -r requirements.txt \
    || warn "pip не смог поставить httpx. Поставь вручную: $PY -m pip install httpx"
  $PY -c 'import httpx' >/dev/null 2>&1 && ok "httpx поставлен"
fi

step 3 "готовлю файл ключей .env"
if [ -f .env ]; then
  ok ".env уже есть, не трогаю"
else
  cp env.example .env
  chmod 600 .env 2>/dev/null || true
  ok "создан .env из образца. Открой его и впиши свои ключи"
fi

step 4 "готовлю рабочий дом"
HOME_DIR="$($PY - <<'PY'
import os, pathlib
value = os.environ.get("AUTOPOST_HOME", "").strip()
path = pathlib.Path(value).expanduser() if value else pathlib.Path.home() / ".autopost"
path.mkdir(parents=True, exist_ok=True)
print(path)
PY
)"
ok "очередь и лог будут лежать в $HOME_DIR (вне папки движка)"

step 5 "проверяю движок тестами"
# имя отчёта уникальное: на общей машине два прогона рядом не перетирают файл друг друга,
# а ученик читает именно СВОЙ отчёт. Тот же порядок и в setup.ps1
REPORT="$(mktemp "${TMPDIR:-/tmp}/autopost-tests-XXXXXX.txt" 2>/dev/null || echo "${TMPDIR:-/tmp}/autopost-tests-$$.txt")"
# -p no:cacheprovider: проверки не оставляют кэш прогона в папке движка. То же правило
# лежит в pytest.ini рядом - там оно работает и для запуска руками, и из редактора.
# Здесь флаг стоит вторым замком: если движок запустят с чужим pytest.ini из папки выше,
# файл рядом не найдётся, а флаг в команде сработает всё равно
if $PY -m pytest tests -q -p no:cacheprovider >"$REPORT" 2>&1; then
  ok "$(tail -1 "$REPORT")"
  ok "полный отчёт: $REPORT"
else
  if $PY -c 'import pytest' >/dev/null 2>&1; then
    warn "тесты не прошли, смотри $REPORT"
  else
    warn "pytest не установлен, шаг пропущен (на работу движка не влияет)"
  fi
fi

step 6 "спрашиваю доктора"
$PY cli.py doctor || warn "доктор завершился с ошибкой"

step 7 "расписание"
printf '  шаблоны автозапуска лежат в raspisanie/\n'
case "$(uname -s)" in
  Darwin) printf '    твоя система: macOS, бери raspisanie/launchd.plist.example\n' ;;
  Linux)  printf '    твоя система: Linux, бери raspisanie/systemd.service.example и systemd.timer.example\n' ;;
  *)      printf '    система не опознана, смотри raspisanie/README.md\n' ;;
esac
printf '    поставить расписание можно позже, движок работает и по ручному запуску\n'

printf '\nУСТАНОВКА ЗАВЕРШЕНА. Дальше: впиши ключи в .env, потом %s cli.py doctor\n' "$PY"
