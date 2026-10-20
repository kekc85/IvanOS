#!/bin/bash
# inject-proof-block-gate.sh <skill-name>
# Вшивает обязательный Proof-блок (чек-лист стадий + таблица 13 мастеров с цитатами + линтер + верификатор) в writer-skill.
# Идемпотентно: если уже ссылается на proof-block-gate — skip.
#
# Usage: for s in post carousel tweet longform email bot-message single-image video adaptation; do bash inject-proof-block-gate.sh $s; done

SKILL="$1"
SKILLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$SKILLS_DIR/$SKILL"

if [ -z "$SKILL" ]; then echo "Usage: $0 <skill-name>"; exit 1; fi
if [ ! -d "$SKILL_DIR" ]; then echo "❌ skill $SKILL не найден"; exit 1; fi
if grep -rql "proof-block-gate" "$SKILL_DIR" 2>/dev/null; then
  echo "⏭️  $SKILL: proof-block-gate уже подключён - skip"
  exit 0
fi

# Целевой файл: финальная фаза вывода (publish/review), иначе prompt/SKILL
TARGET=""
for c in "$SKILL_DIR/workflow/05-publish.md" "$SKILL_DIR/workflow/04-review.md" "$SKILL_DIR/prompt.md" "$SKILL_DIR/SKILL.md"; do
  if [ -f "$c" ]; then TARGET="$c"; break; fi
done
if [ -z "$TARGET" ]; then echo "❌ $SKILL: нет файла для injection"; exit 1; fi

cat >> "$TARGET" <<PROOF

---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат \`_shared/proof-block-gate.md\` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам \`mastery/copywriting/\` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память \`feedback_prove_skill_and_masters_each_time\`.
PROOF

echo "✅ $SKILL: proof-block-gate вшит в $(basename "$TARGET")"