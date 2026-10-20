#!/usr/bin/env bash
# leak_scan.sh - проверка, что в папке движка не осталось ничего личного.
#
# Зачем он тебе. Движок ты будешь показывать, класть в репозиторий и, может быть,
# отдавать помощнику. Ключ от бота или адрес твоего сервера, случайно оставшийся
# в коде, уезжает вместе с папкой и обратно уже не возвращается. Этот скан ловит
# такое до того, как папка ушла.
#
# Запуск:  bash leak_scan.sh [папка]     (по умолчанию папка рядом со скриптом)
# Выход:   0 = чисто, 1 = найдены утечки
#
# Свои строки-стоп-слова (имя, домен, название компании) допиши в файл
# leak_extra.txt рядом: по строке на регулярное выражение. Файла нет - скан
# работает на базовом наборе

set -uo pipefail
DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
EXTRA="$(cd "$(dirname "$0")" && pwd)/leak_extra.txt"

PATTERNS=(
  '[0-9]{6,12}:AA[A-Za-z0-9_-]{30,}'            # токен телеграм-бота
  'IGA[A-Za-z0-9_-]{40,}'                       # токен доступа инстаграм
  'EAA[A-Za-z0-9]{40,}'                         # токен доступа мета
  'vk1\.a\.[A-Za-z0-9_-]{30,}'                  # токен доступа вк
  'sk-[A-Za-z0-9_-]{20,}'                       # ключ модели
  'AKIA[0-9A-Z]{16}'                            # ключ облака
  'BEGIN [A-Z ]*PRIVATE KEY'                    # приватный ключ
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'             # адрес сервера
  '/Users/[A-Za-z0-9._-]+/'                     # путь с именем пользователя (мак)
  '/home/[A-Za-z0-9._-]+/'                      # путь с именем пользователя (линукс)
  'C:\\\\Users\\\\[A-Za-z0-9._-]+'              # путь с именем пользователя (windows)
  '@[A-Za-z][A-Za-z0-9_]{4,31}'                 # чей-то адрес в телеграм
  '-100[0-9]{10}'                               # номер закрытого канала
  'https?://[a-z0-9-]+\.[a-z0-9.-]*(ru|com|net|org|io|dev|me)\b'  # чей-то домен
)

# Заведомо безопасные совпадения: адреса самих площадок, документация,
# плейсхолдеры образца и декораторы питона
ALLOW='api\.telegram\.org|core\.telegram\.org|graph\.instagram\.com|graph\.facebook\.com'
ALLOW="$ALLOW"'|api\.vk\.com|dev\.vk\.com|developers\.facebook\.com|python\.org|pypi\.org'
# публичные адреса самих площадок, из которых собирается ссылка на твою же запись
ALLOW="$ALLOW"'|https://t\.me/|https://vk\.com/|https://www\.instagram\.com/'
ALLOW="$ALLOW"'|example\.com|example\.org|\.example/|\.example"|\.invalid'
ALLOW="$ALLOW"'|@BotFather|@example|@username|@adres_kanala|@testkanal|@moy_bot|@moy_akkaunt'
ALLOW="$ALLOW"'|@(staticmethod|property|dataclass|classmethod|abstractmethod|pytest|param|return)'
ALLOW="$ALLOW"'|127\.0\.0\.1|0\.0\.0\.0|203\.0\.113\.|\{\{|<твой|<ваш|ТВОЙ_|ВАШ_'
# служебная ссылка в шаблоне расписания macOS, не чей-то домен
ALLOW="$ALLOW"'|www\.apple\.com/DTDs'

if [ -f "$EXTRA" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    PATTERNS+=("$line")
  done < "$EXTRA"
fi

# .env исключён из поиска намеренно: он и ДОЛЖЕН содержать твои ключи, и если бы
# скан ругался на него каждый раз, ты перестал бы читать его вывод через неделю.
# Вместо крика - отдельное напоминание ниже, что этот файл не уезжает никуда
if [ -f "$DIR/.env" ] && grep -qE '^[A-Z_]+=.+' "$DIR/.env" 2>/dev/null; then
  filled=$(grep -cE '^[A-Z_]+=.{4,}' "$DIR/.env" 2>/dev/null)
  echo "НАПОМИНАНИЕ: .env заполнен (непустых полей: $filled). Это твои ключи."
  echo "  Он закрыт .gitignore и в поиске утечек не участвует. Никому его не пересылай"
  echo
fi

# СЛУЖЕБНЫЕ КАТАЛОГИ ИНСТРУМЕНТОВ - не твои данные и не утечка.
# Их содержимое пишет не человек, а инструмент: кэш прогона проверок, кэш линтера,
# кэш типов, сборочный мусор. Там лежат чужие ссылки из документации, и скан ловил их
# как «чей-то домен». Судить надо КЛАСС таких каталогов, а не три знакомых имени: завтра
# ты поставишь ещё один инструмент со своим кэшем, и перечень имён снова отстанет.
# Поэтому исключение задано образцами `*_cache` и `.*_cache` плюс известные имена.
# Прецедент по решению автора: после штатной установки движка скан объявил утечкой ссылку из
# README внутри .pytest_cache, то есть проверка чистоты ломалась о собственную установку.
# Второй замок стоит с другой стороны: pytest.ini рядом вообще не даёт создать этот кэш
SERVICE_DIRS=(
  '*_cache' '.*_cache'
  '__pycache__' '.venv' 'venv' '.git' 'node_modules'
  '.tox' '.nox' 'htmlcov' '.ipynb_checkpoints' '.gradle' 'target' 'dist' 'build'
)
EXCLUDE_ARGS=()
for d in "${SERVICE_DIRS[@]}"; do EXCLUDE_ARGS+=(--exclude-dir="$d"); done

# Ученику честно говорим, что такие каталоги есть и почему они не в счёт
sluzhebnye=$(find "$DIR" \( -name '*_cache' -o -name '.*_cache' -o -name '__pycache__' \
               -o -name '.tox' -o -name 'htmlcov' -o -name '.ipynb_checkpoints' \) \
               -type d 2>/dev/null | head -5)
if [ -n "$sluzhebnye" ]; then
  echo "СПРАВКА: в папке есть служебные каталоги инструментов, они в поиске не участвуют."
  echo "$sluzhebnye" | sed 's/^/  /'
  echo "  Это кэш программ, а не твои данные. В репозиторий они не уезжают (.gitignore)"
  echo
fi

found=0
for pattern in "${PATTERNS[@]}"; do
  hits=$(grep -rInE "$pattern" "$DIR" \
           --exclude=leak_scan.sh --exclude=leak_extra.txt --exclude=.env --exclude=.env.local \
           "${EXCLUDE_ARGS[@]}" 2>/dev/null \
         | grep -vE "$ALLOW" || true)
  if [ -n "$hits" ]; then
    echo "УТЕЧКА по образцу: $pattern"
    echo "$hits" | sed -E 's#[0-9]{6,12}:AA[A-Za-z0-9_-]{30,}#ТОКЕН_СКРЫТ#g' | head -10
    echo
    found=1
  fi
done

if [ "$found" -eq 0 ]; then
  echo "LEAK-СКАН ЧИСТО: $DIR"
  exit 0
fi
echo "LEAK-СКАН НАШЁЛ УТЕЧКИ в $DIR"
exit 1
