#!/bin/bash
# inject-variation-gate.sh <skill-name>
# Вшивает Variation Rotation Gate (анти-шаблон: ротация hook/opening/narrative/archetype + видимая декларация) в writer-skill.
# Идемпотентно: если skill уже ссылается на variation-rotation-gate — skip.
#
# Usage:
#   bash inject-variation-gate.sh post
#   for s in post carousel tweet longform email bot-message single-image video; do bash inject-variation-gate.sh $s; done

SKILL="$1"
SKILLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$SKILLS_DIR/_shared/variation-rotation-gate.md"
SKILL_DIR="$SKILLS_DIR/$SKILL"

if [ -z "$SKILL" ]; then echo "Usage: $0 <skill-name>"; exit 1; fi
if [ ! -d "$SKILL_DIR" ]; then echo "❌ skill $SKILL не найден"; exit 1; fi

if grep -rql "variation-rotation-gate" "$SKILL_DIR" 2>/dev/null; then
  echo "⏭️  $SKILL: variation-rotation-gate уже подключён - skip (идемпотентно)"
  exit 0
fi

# Целевой файл: фаза подготовки ДО write (finalize/structure/write), иначе prompt/SKILL
TARGET=""
for c in "$SKILL_DIR/workflow/01-finalize.md" "$SKILL_DIR/workflow/02-structure.md" "$SKILL_DIR/workflow/03-write.md" "$SKILL_DIR/prompt.md" "$SKILL_DIR/SKILL.md"; do
  if [ -f "$c" ]; then TARGET="$c"; break; fi
done
if [ -z "$TARGET" ]; then echo "❌ $SKILL: нет файла для injection"; exit 1; fi

cat >> "$TARGET" <<VARGATE

---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить \`_shared/variation-rotation-gate.md\` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ \`<project-pack>/variation-log.md\` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в \`variation-log.md\`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память \`feedback_rotate_post_axes_every_time\`.
VARGATE

echo "✅ $SKILL: variation-rotation-gate вшит в $(basename "$TARGET")"