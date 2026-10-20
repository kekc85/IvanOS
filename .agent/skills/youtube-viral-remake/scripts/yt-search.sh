#!/usr/bin/env bash
# yt-search.sh - поиск массовых виральных YouTube long-form роликов по теме
# Usage: yt-search.sh "<тема>" [N]
#   N = сколько кандидатов запросить (дефолт 25)
# Фильтр: duration >= 600с (long-form 10+ мин), сортировка по просмотрам убыв
# Публичный поиск, аккаунт вне цепочки (cookies не нужны)
set -euo pipefail

MIN_DURATION=600   # 10 минут - порог long-form

if [[ $# -lt 1 || -z "${1:-}" ]]; then
  echo "Usage: yt-search.sh \"<тема>\" [N]" >&2
  echo "  Ищет массовые YouTube long-form виралки (>=10 мин) по теме, ранж по просмотрам" >&2
  exit 2
fi

THEME="$1"
N="${2:-25}"

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "ОШИБКА: yt-dlp не установлен. brew install yt-dlp" >&2
  exit 1
fi

echo "Поиск: \"$THEME\" (top $N кандидатов, фильтр long-form >=${MIN_DURATION}s)..." >&2

# view_count<TAB>duration<TAB>id<TAB>url<TAB>title - TAB-разделитель (title может содержать |)
# id/url перед title, чтобы литеральный | в заголовке не сдвигал колонки
raw=$(yt-dlp "ytsearch${N}:${THEME}" \
        --flat-playlist \
        --print $'%(view_count)s\t%(duration)s\t%(id)s\t%(webpage_url)s\t%(title)s' \
        --socket-timeout 20 2>/dev/null || true)

if [[ -z "$raw" ]]; then
  echo "Ничего не найдено (гео/сеть/пустая выдача). Проверь тему или сеть" >&2
  exit 1
fi

# Фильтр duration>=MIN и view_count числовой, сортировка по просмотрам убыв
printf '%s\n' "$raw" | awk -F'\t' -v min="$MIN_DURATION" '
  {
    vc=$1; dur=$2;
    if (vc ~ /^[0-9]+$/ && dur ~ /^[0-9.]+$/ && dur+0 >= min) print $0
  }' | sort -t$'\t' -k1 -rn | head -12 | awk -F'\t' '
  BEGIN { printf "%-12s %-7s %s\n", "ПРОСМОТРЫ", "МИН", "НАЗВАНИЕ / URL" }
  {
    mins = int($2/60);
    printf "%-12s %-7s %s\n              %s  [id:%s]\n", $1, mins"м", $5, $4, $3
  }'

echo "" >&2
echo "ЗАКОН: бери только массовую виралку (сотни тыс / млн просмотров). Слабый донор не берём" >&2