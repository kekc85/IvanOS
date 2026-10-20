#!/bin/bash
# inject-value-delivery-gate.sh <skill-name>
# Вшивает в writer-skill ссылку на общий Value-Delivery Gate:
#   - _shared/value-delivery-gate.md (действие генеративное / ≥2 value-types не огрызок / объём+формат для длинных)
# Идемпотентно: если маркер уже есть - skip.
# Прецедент по решению автора: пост-«огрызок» без ценности + диагностическое действие. Правила вынесены в общий слой.
#
# Usage:
#   bash inject-value-delivery-gate.sh tweet
#   for s in post tweet longform email bot-message single-image carousel; do bash inject-value-delivery-gate.sh $s; done

SKILL="$1"
SKILLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$SKILLS_DIR/$SKILL"
MARKER="VALUE-DELIVERY GATE (shared, injected)"

if [ -z "$SKILL" ]; then echo "Usage: $0 <skill-name>"; exit 1; fi
if [ ! -d "$SKILL_DIR" ]; then echo "❌ skill $SKILL не найден"; exit 1; fi

# Idempotent: skip if marker present anywhere in skill
if grep -rql "$MARKER" "$SKILL_DIR" 2>/dev/null; then
  echo "⏭️  $SKILL: value-delivery gate уже вшит - skip"
  exit 0
fi

# Найти файл для injection (review/write/structure/prompt/SKILL — ближе к финалу ценности/ревью)
TARGET=""
for c in "$SKILL_DIR/workflow/04-review.md" "$SKILL_DIR/workflow/05-review.md" "$SKILL_DIR/workflow/03-write.md" "$SKILL_DIR/workflow/02-structure.md" "$SKILL_DIR/prompt.md" "$SKILL_DIR/SKILL.md"; do
  if [ -f "$c" ]; then TARGET="$c"; break; fi
done
if [ -z "$TARGET" ]; then echo "❌ $SKILL: нет файла для injection"; exit 1; fi

cat >> "$TARGET" <<'GATES'

---

## VALUE-DELIVERY GATE (shared, injected)

> Обязательный гейт «что текст ОБЯЗАН доставить» (вещество, не форма). Источник истины — `~/.claude/skills/_shared/value-delivery-gate.md`. Прецедент по решению автора: пост-«огрызок» без пользы + диагностическое действие.

`Read(~/.claude/skills/_shared/value-delivery-gate.md)` и примени на стадии ценности и на ревью:

1. **Действие ГЕНЕРАТИВНОЕ, не диагностическое (HARD).** Actionable-шаг даёт на руки новый результат/артефакт, а не подтверждает известное («посчитай свою цифру» = диагностика = FAIL; «собери первый продукт через нейросеть» = генеративное). Тест: появился ли у читателя НОВЫЙ результат?
2. **Реальная ценность ≥2 value-types (HARD).** Текст несёт ≥2 из: V1 инсайт / V5 модель «почему» / V2 генеративное действие / пруф-кейс с цифрой. Только «было плохо → стало хорошо + призыв» = бот-сообщение = FAIL «ноль пользы».
3. **Объём+формат — ТОЛЬКО длинные форматы** (educational/story/longform): ~2300-2500 символов, богатое форматирование ≥4 типов (<2 = брак). НЕ применять к микроформатам (tweet ≤280 / bot-message / IG-caption) — там только правила 1-2 по сути.

Независимый верификатор обязан проверить: действие генеративное? ≥2 value-types? не огрызок? Память.
GATES

echo "✅ $SKILL: value-delivery gate вшит в $(basename "$TARGET")"
exit 0