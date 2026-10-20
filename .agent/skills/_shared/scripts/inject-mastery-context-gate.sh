#!/bin/bash
# inject-mastery-context-gate.sh <skill-name>
# Добавляет в writer-skill ссылки на два общих гейта:
#   - _shared/context-gap-gate.md  (нет реального контекста → спроси, не выдумывай)
#   - _shared/mastery-gate.md      (линза мастеров: Inventory→Select→Apply→Evidence→Verifier)
# Идемпотентно: если маркер уже есть - skip.
#
# Usage:
#   bash inject-mastery-context-gate.sh tweet
#   for s in post tweet longform email bot-message single-image carousel; do bash inject-mastery-context-gate.sh $s; done

SKILL="$1"
SKILLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$SKILLS_DIR/$SKILL"
MARKER="MASTERY+CONTEXT GATES (shared, injected)"

if [ -z "$SKILL" ]; then echo "Usage: $0 <skill-name>"; exit 1; fi
if [ ! -d "$SKILL_DIR" ]; then echo "❌ skill $SKILL не найден"; exit 1; fi

# Idempotent: skip if marker present anywhere in skill
if grep -rql "$MARKER" "$SKILL_DIR" 2>/dev/null; then
  echo "⏭️  $SKILL: gates уже вшиты - skip"
  exit 0
fi

# Найти файл для injection (write/structure/prompt/SKILL)
TARGET=""
for c in "$SKILL_DIR/workflow/03-write.md" "$SKILL_DIR/workflow/02-structure.md" "$SKILL_DIR/prompt.md" "$SKILL_DIR/SKILL.md"; do
  if [ -f "$c" ]; then TARGET="$c"; break; fi
done
if [ -z "$TARGET" ]; then echo "❌ $SKILL: нет файла для injection"; exit 1; fi

cat >> "$TARGET" <<'GATES'

---

## MASTERY+CONTEXT GATES (shared, injected)

> Два обязательных гейта перед написанием публикуемого текста. Общие для всех writer-скиллов, источник истины в `_shared/`.

### Гейт 1 — Context-gap (нет реального контекста → СПРОСИ, не выдумывай) — HARD
`Read(~/.claude/skills/_shared/context-gap-gate.md)` и примени ДО draft. Если для текста нужны цифры / инфоповоды / новости / цены / даты / кейс / цитата, которых НЕТ в источниках (config / карта смыслов / story-bank / транскрипт / то, что дал автор) → **СТОП, не писать**, вывести в чат нумерованный список «нужно от тебя:» и ждать. Выдумывать, округлять, ставить плейсхолдер в финал — запрещено. Вывести секцию `Context-gap: нет / список вопросов`.

### Гейт 2 — Mastery (линза мастеров) — HARD
`Read(~/.claude/skills/_shared/mastery-gate.md)` (полный регламент — `mastery/PROTOCOL.md`). До draft: Inventory ВСЕХ авторов `mastery/copywriting/` + Select с обоснованием + bind. После draft, до humaniser: Evidence Report (метод→цитата) + независимый верификатор (субагент-скептик; нет цитаты→FAIL; верификатор запускается ВСЕГДА, без исключений — v4.2, `--fast`/облегчённый режим устранён).

**Порядок:** Context-gap → (если полно) Mastery Inventory+Select → write → Evidence+Verifier → Humaniser → output.
GATES

echo "✅ $SKILL: gates вшиты в $(basename "$TARGET")"
exit 0
GATES_EOF_GUARD() { :; }
