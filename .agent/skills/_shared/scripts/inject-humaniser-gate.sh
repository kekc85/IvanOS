#!/bin/bash
# inject-humaniser-gate.sh <skill-name>
# Добавляет mandatory humaniser final pass в указанный text-skill.
# Идемпотентно: если skill уже вызывает humaniser - skip.
#
# Usage:
#   bash inject-humaniser-gate.sh post
#   bash inject-humaniser-gate.sh tweet
#   for s in post tweet longform email bot-message single-image carousel; do bash inject-humaniser-gate.sh $s; done

SKILL="$1"
SKILLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HUMANISER_PROMPT="$SKILLS_DIR/humaniser/prompt.md"
SKILL_DIR="$SKILLS_DIR/$SKILL"

if [ -z "$SKILL" ]; then
  echo "Usage: $0 <skill-name>"
  exit 1
fi

if [ ! -d "$SKILL_DIR" ]; then
  echo "❌ skill $SKILL не найден в $SKILLS_DIR"
  exit 1
fi

# Check existing humaniser reference
if grep -rql "humaniser" "$SKILL_DIR" 2>/dev/null; then
  echo "⏭️  $SKILL: humaniser already referenced - skip (idempotent)"
  exit 0
fi

# Find review/finalize file (where humaniser должен быть встроен — финальная фаза)
REVIEW_FILE=""
for candidate in "$SKILL_DIR/workflow/04-review.md" "$SKILL_DIR/workflow/03-write.md" "$SKILL_DIR/workflow/05-publish.md" "$SKILL_DIR/prompt.md" "$SKILL_DIR/SKILL.md"; do
  if [ -f "$candidate" ]; then
    REVIEW_FILE="$candidate"
    break
  fi
done

if [ -z "$REVIEW_FILE" ]; then
  echo "❌ $SKILL: не найден файл для injection (нет workflow/04-review.md / 03-write.md / 05-publish.md / prompt.md / SKILL.md)"
  exit 1
fi

# Append humaniser phase
cat >> "$REVIEW_FILE" <<HUMPHASE

---

## Финальная фаза — Humaniser (HARD GATE для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Вызови Skill tool: \`Skill('humaniser', args=<финальный текст>)\` ПЕРЕД любым output. НЕ читай humaniser/prompt.md inline и НЕ применяй mentally — это shallow execution которое пропускает AI-tics. Только полный pass через Skill tool invocation документированный в чате.

Humaniser v2 ловит 11 категорий AI-паттернов:
1. Ложная глубина
2. Фальшивая близость
3. Пустые связки
4. Канцелярит
5. Fake-энергия
6. Шаблонные призывы
7. Рубленые фразы (3+ из 1-2 слов подряд)
8. Кинематограф
9. Структурные клише
10. Интонационные клише
11. **Slap-эмфаза (длинное + 1-3-словное короткое для эмфазы) — главный AI-tic социалок 2025-2026**

**HARD GATE:** Output финального текста ТОЛЬКО после green CHECKER (все 5/5 в «Клише удалены»). Если CHECKER не green — REWRITER ещё раз. Без этого = брак.

**Прецеденты:**
- 2026-05-28: post v3.0 выдал «Zero ads. Zero funnels. Zero sales calls.» (triple-negation AI tic)
- 2026-05-29: caption выдал «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, новая категория 11)

Оба = провал shallow inline pass. HARD GATE через Skill tool решает.
HUMPHASE

echo "✅ $SKILL: humaniser final phase injected в $(basename $REVIEW_FILE)"
