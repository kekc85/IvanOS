# workflow/02-structure.md

> Каркас Subject + Preheader + Body skeleton + CTA по типу письма.

## Inputs

- `brief` (из finalize)
- `config`

## Steps

### Step 1 - Load template by type

```
template_path = "templates/" + brief.type + ".md"
template = Read(template_path)
```

Template содержит:
- Структуру body (sections + поток)
- Hook framework recommendations
- CTA placement rules
- Length distribution (% по секциям)

### Step 2 - Generate Subject A/B variants

Прочитать `references/subject-formulas-50.md` + `references/voice-bridge-to-tg.md` → hooks-15-templates.

Сгенерировать **3-5 Subject вариантов** на разных hook frameworks (из config.email.subject_frameworks_per_ab):

| Variant | Framework | Пример (RU) |
|---|---|---|
| A | curiosity | «То чего я не говорил год» |
| B | direct_benefit | «3 шага к $5K/мес из 100 подписчиков» |
| C | contrarian | «Почему я больше не пишу daily» |
| D | personal_confession | «Я облажался вчера» |
| E | numbered | «5 ошибок которые убивают конверсию» |

**Constraints:**

- Каждый Subject ≤50 chars (hard fail >60)
- ≤1 «!» в Subject
- Без CAPS-слов (>3 заглавных подряд)
- Без spam-trigger слов из `config-lexicon.md` + `references/spam-triggers-list.md`
- Разные frameworks (НЕ 3 варианта curiosity подряд)
- Mobile preview check: первые 40 chars должны быть самостоятельным смыслом

Lock `brief.subject_variants` = список 3-5 пар (framework, text).

### Step 3 - Generate Preheader

Прочитать `references/preheader-patterns.md`.

Preheader = усиление Subject (не дубликат):

- 50-90 chars
- Similarity с Subject <70%
- Содержит: дополнительный hook / context / preview ценности

Если language=both → preheader для RU + EN отдельно.

Lock `brief.preheader_ru` + `brief.preheader_en` (если both).

### Step 4 - Body skeleton

Прочитать `templates/<type>.md` → раздел `body_skeleton`. Каркас по типу:

**Nurture letter skeleton:**

```
1. Opening line (≤60 chars, above-fold hook)
2. Personal story / observation / data (200-300 слов)
3. Тезис / lesson learned (100-200 слов)
4. Application / how-I tactic (100-200 слов)
5. Soft CTA (40-80 слов)
6. P.S. (опционально, 20-40 слов)
```

**Launch sequence skeleton (по sequence_position):**

```
Pre-launch (-7d / -3d):
- Hook (curiosity / aspiration)
- Story setup
- Tease для launch day
- Soft CTA: «calendar / save the date»

Launch day (Day 0):
- Hook (event marker)
- Big announcement
- Value stack preview
- Hard CTA: «check it out / join»

Open cart (Day 1-4):
- Hook (objection-addressing или social proof)
- Storytelling proof
- Detailed value
- CTA: «buy now»

Close cart (Day 5 / last call):
- Hook (urgency-based but not spam)
- Recap
- Last value reminder
- CTA: «buy now / last chance»
```

**Sales letter skeleton (Halbert/Welsh fusion):**

```
1. Opening hook (≤60 chars)
2. Problem amplification (150-250 слов)
3. Story / personal context (200-400 слов)
4. Solution introduction (150-250 слов)
5. Value stack (100-200 слов + bullet up to 2)
6. Proof / social proof (100-200 слов)
7. Offer terms + guarantee (100-150 слов)
8. CTA #1 above-fold position (already passed) - placed after Value stack
9. Objection handling (100-200 слов)
10. CTA #2 bottom (40-80 слов)
11. P.S. (40-80 слов, recap offer + CTA #3)
```

Lock `brief.body_skeleton` = ordered list of sections + word allocations.

### Step 5 - CTA placement

Прочитать `references/cta-patterns.md`.

**Nurture:** 1 CTA, link form «прочитать дальше / клик» или soft «ответ на письмо».

**Launch:** 1-2 CTA (1 = primary в конце, 2-я опционально mid-body как inline reference).

**Sales:** 2-3 CTA (above-fold OR after value stack + bottom + P.S.). Все ведут на ОДНУ страницу.

Lock `brief.cta_text` + `brief.cta_link` + `brief.cta_positions`.

### Step 6 - Hand-off

```yaml
brief:
  ... (all previous)
  subject_variants: [{framework, text}, ...]
  preheader_ru: "..."
  preheader_en: "..."  (если both)
  body_skeleton: [{section, words_alloc}, ...]
  cta_text: "..."
  cta_link: "<url или placeholder>"
  cta_positions: ["above-fold" | "after-value-stack" | "bottom" | "p.s."]
```

→ `workflow/03-write.md`.

## Anti-patterns

- НЕ выдавать <3 Subject вариантов - нарушает EMAIL-G1
- НЕ дублировать Preheader = Subject парафраз - нарушает EMAIL-G2
- НЕ ставить multi-CTA-goal в одном письме - нарушает принцип №1
- НЕ менять skeleton от типа на лету - template = договор для типа
- НЕ забывать sequence_context для launch-sequence skeleton - иначе письмо disconnected от sequence flow