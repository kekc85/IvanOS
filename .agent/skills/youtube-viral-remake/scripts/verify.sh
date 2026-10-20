#!/usr/bin/env bash
# verify.sh - проверка готовности проекта youtube-viral-remake перед заявлением «готово»
# Usage: verify.sh <project-dir>
#   project-dir = папка проекта (~/Desktop/yt-remake/<date>-<slug>/ или ingest-папка)
# exit 0 = всё на месте · exit 1 = чего-то не хватает
set -euo pipefail

if [[ $# -lt 1 || -z "${1:-}" ]]; then
  echo "Usage: verify.sh <project-dir>" >&2
  exit 2
fi

DIR="$1"
if [[ ! -d "$DIR" ]]; then
  echo "ОШИБКА: папка проекта не найдена: $DIR" >&2
  exit 1
fi

fail=0
ok(){ echo "  [OK]   $1"; }
bad(){ echo "  [FAIL] $1" >&2; fail=1; }

echo "Проверка проекта: $DIR"

# 1. card.md (деконструкция) - ищем в проекте или в ingest
card=$(find "$DIR" -maxdepth 2 -name "card.md" 2>/dev/null | head -1)
[[ -n "$card" ]] && ok "card.md найден: $card" || bad "card.md отсутствует (фаза 02)"

# 2. card.md несёт обязательные для video поля (Validate readiness 01c)
if [[ -n "$card" ]]; then
  grep -q "voice_script_brief" "$card" 2>/dev/null && ok "voice_script_brief есть" || bad "нет voice_script_brief в card.md"
  grep -q "Главный insight\|main_insight" "$card" 2>/dev/null && ok "Главный insight есть" || bad "нет 'Главный insight' в card.md"
fi

# 3. storyboard.md (фаза 04) - существует И непустой (0-байт файл = замысел, не результат)
sb=$(find "$DIR" -maxdepth 2 -name "storyboard.md" 2>/dev/null | head -1)
if [[ -n "$sb" && -s "$sb" ]]; then
  ok "storyboard.md найден и непустой"
elif [[ -n "$sb" ]]; then
  bad "storyboard.md пустой (0 байт) - замысел без содержания (фаза 04)"
else
  bad "storyboard.md отсутствует (фаза 04)"
fi

# 4. production-package (фаза 05) - папка с НЕПУСТЫМИ файлами (не 0-байт заглушки)
pkg=$(find "$DIR" -maxdepth 2 -type d -name "production-package" 2>/dev/null | head -1)
if [[ -n "$pkg" ]]; then
  nonempty=$(find "$pkg" -type f -size +0c 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$nonempty" -gt 0 ]]; then
    ok "production-package/ содержит $nonempty непустых файлов"
  else
    bad "production-package/ пуст или только 0-байт заглушки (фаза 05)"
  fi
else
  bad "production-package/ отсутствует (фаза 05)"
fi

# 5. Собранный черновик (фаза 06) - опционально, но если есть, должен быть валиден
draft=$(find "$DIR" -maxdepth 2 -name "*.mp4" 2>/dev/null | head -1)
if [[ -n "$draft" ]]; then
  if command -v ffprobe >/dev/null 2>&1; then
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$draft" 2>/dev/null | cut -d. -f1)
    [[ "${d:-0}" -gt 0 ]] && ok "черновик валиден: $(basename "$draft") (${d}с)" || bad "черновик битый: $draft"
  else
    ok "черновик есть: $(basename "$draft") (ffprobe нет, не проверил длину)"
  fi
else
  echo "  [SKIP] черновик .mp4 ещё не собран (фаза 06 - после записи автора)"
fi

echo ""
if [[ "$fail" -eq 0 ]]; then
  echo "VERIFY: PASS"
  exit 0
else
  echo "VERIFY: FAIL - не заявлять «готово», доделать помеченное" >&2
  exit 1
fi