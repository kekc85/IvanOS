# Reference - 6-Pass Refinement (longform adaptation)

> 6 LLM-judge passes в `04-review.md` Pass 2. Каждый pass = independent prompt с конкретным persona / focus. Adapted для длинных форм (более глубокий Skeptic для argumentation, Scroller через 3-секундный hook test для newsletter open rate).

## Происхождение

Pattern из `create-viral-content` skill (audited 2026-05-27, NOT forked для post). Концепт 6-Pass Refinement сохранён, internals адаптированы под TG-короткие в `post`. Здесь - longform adaptation.

## 6 passes

### Pass 2.1 - Skeptic

**Persona:** Skeptical reader who clicked from social link, default trust = low.

**Focus:**
- Любое утверждение без proof / numbers / examples → flag
- Hyperbolic claims («revolutionary», «10x», «обалденный») → flag
- Логические дыры в main_aha (не выдерживает counter-argument) → flag
- Implied promises не выполненные в conclusion → flag

**Output:**
```yaml
skeptic_pass:
  claims_without_proof: [<list>]
  hyperbolic_claims: [<list>]
  logical_gaps: [<list>]
  unfulfilled_promises: [<list>]
  severity: low | medium | high
```

**Fail:** ≥3 critical претензий (severity ≥medium) → revision request.

**Prompt template:**
```
You are a skeptical reader who clicked from a social media link. Default trust is low. You have 2 minutes before you decide to bookmark or close.

Read the draft. List:
1. Claims made without proof / numbers / examples
2. Hyperbolic language that triggers your BS detector
3. Logical gaps in the main argument
4. Promises set up in introduction but not delivered in conclusion

Be specific (quote the line). Don't generic.
```

---

### Pass 2.2 - Expert (domain)

**Persona:** Expert в нише (вайбкодинг / маркетинг для соло-экспертов / то же что у автора).

**Focus:**
- Технические неточности
- Outdated references (платформы / инструменты / цены)
- Поверхностное раскрытие там где нужна глубина
- Mistakes that would embarrass an expert

**Output:**
```yaml
expert_pass:
  technical_inaccuracies: [<list>]
  outdated_references: [<list>]
  superficial_sections: [<list>]
  embarrassing_mistakes: [<list>]
  severity: low | medium | high
```

**Fail:** ≥2 critical inaccuracies (severity ≥medium) → revision request.

**Prompt template:**
```
You are an expert in <niche from config>. You've spent 10+ years in this space. You teach this professionally.

Read the draft. List:
1. Technical inaccuracies (be specific - quote the line, explain why it's wrong)
2. Outdated references (tools / prices / platforms that have moved on)
3. Sections that need depth but are surface-level
4. Mistakes that would make a professional in this niche cringe

Be honest. Don't hedge.
```

---

### Pass 2.3 - Scroller (3-секундный hook test)

**Persona:** Mobile reader scrolling through feed / opening newsletter on phone.

**Focus:**
- Headline + first 2 paragraphs test
- 3-second decision: scroll past or continue?
- Platform-specific test:
  - Newsletter → open rate test (subject + preheader + first line)
  - LinkedIn → стоп-скролл test
  - Blog → bounce rate test (первый экран)

**Output:**
```yaml
scroller_pass:
  hook_strength: 1-10
  decision: continue | scroll-past
  reason: <one line why>
  alternative_hook_suggestions: [<list 2-3>]
```

**Fail:** decision = scroll-past → переработать hook через `references/hook-patterns-longform.md`.

**Prompt template:**
```
You're scrolling through your social feed / inbox on your phone. You see this headline and the first 2 paragraphs.

Decide in 3 seconds: continue reading or scroll past?

If scroll past - explain in 1 line why.
If continue - explain what hooked you.

Suggest 2-3 alternative hooks that would make it stronger.
```

---

### Pass 2.4 - Competitor (reference creator)

**Persona:** Reference creator в той же нише (Dan Koe для teaching, Justin Welsh для story, Sahil Bloom для listicle, Tim Ferriss для deep-dive).

**Focus:**
- Сравнение с pattern reference creator'а
- Чего у тебя нет что у них есть (specific number patterns, personal anchor depth, unique frame)
- В чём ты можешь превзойти (твоя ниша / твой опыт / свежий angle)

**Output:**
```yaml
competitor_pass:
  reference_creator: <name>
  patterns_missing: [<list>]
  patterns_present: [<list>]
  unique_advantage: <one line>
  fail_areas: [<list>]
```

**Fail:** ≥3 essential pattern'ов reference'а не использованы → revision request.

**Prompt template:**
```
You are <reference creator name from longform-structures.md>. You read this essay and compare it to your own style.

List:
1. Patterns / techniques YOU use that this draft is missing
2. Patterns this draft uses well
3. The unique advantage this draft has (something YOU couldn't write)
4. Areas where this draft fails vs your own work

Be honest. Don't be polite. Reference creators are competitive.
```

---

### Pass 2.5 - Editor (line-by-line)

**Persona:** Copy editor с опытом newsletter / blog editing.

**Focus:**
- Удалить filler words
- Сократить длинные предложения (>30 слов)
- Заменить пассив на актив
- Удалить дублирующие мысли
- Сверка с lexicon_banned_* (regex повторно)

**Output:**
```yaml
editor_pass:
  filler_words_removed: <count>
  long_sentences_shortened: <count>
  passive_to_active_conversions: <count>
  duplicate_thoughts_merged: <count>
  lexicon_violations_caught: [<list>]
```

**Fail:** Не fail-gate, просто cleanup. Output = cleaned draft.

**Prompt template:**
```
You are a copy editor. Your job is to make this draft tighter without losing voice or meaning.

Apply:
1. Remove filler words (just / actually / basically / really / very / quite)
2. Shorten sentences over 30 words
3. Convert passive voice to active where possible
4. Merge duplicate thoughts
5. Flag any banned lexicon (see config.lexicon_banned_*)

Return the cleaned draft. Track changes count for each category.
```

---

### Pass 2.6 - Thumbnail / Subject (newsletter only)

**Persona:** Newsletter subscriber scanning subject lines в inbox.

**Focus:**
- Только для platform = newsletter (Kit / Beehiiv)
- 3 subject lines (40-60 chars каждая)
- 1 preheader (90-100 chars)
- A/B-able гипотезы (что тестируется)

**Output:**
```yaml
thumbnail_pass:
  subjects: ["<1>", "<2>", "<3>"]
  preheader: "<>"
  hypotheses:
    subject_a: <what's tested>
    subject_b: <>
    subject_c: <>
  predicted_winner: <subject letter + reasoning>
```

**Fail:** Все 3 subject варианта одинаково слабые (no contrast / no curiosity / no specific) → re-generate.

**Prompt template:**
```
You are scanning your inbox on Tuesday morning. You have 15 newsletters waiting. You'll open 3.

For this longform article, generate:
1. Three subject lines (40-60 chars each) testing different angles:
   - A: Curiosity gap
   - B: Personal anchor
   - C: Specific outcome
2. One preheader (90-100 chars) that complements subject without repeating
3. For each subject: what's the testable hypothesis?
4. Which subject would YOU click and why?

Don't be clever. Be specific.
```

---

## Sequence

Passes run в order 2.1 → 2.6. Каждый pass получает draft с применёнными fixes из предыдущего pass.

После Pass 2.5 (Editor) - cleaned draft.
После Pass 2.6 (Thumbnail) - финальный package для `04-review.md` Pass 3.

## Iteration limit

Если Pass 2.1-2.4 fail → revision request → `03-write.md` Pass 2/3 повторяется с fix prompt → возврат в `04-review.md` → пересдача 2.1-2.4.

Максимум 3 итерации pass 2-cycle. Если после 3 не проходит - escalate пользователю.

## Memory cross-refs

- `[[post]]` - параллельный 6-Pass для TG-постов (Skeptic / Expert / Scroller / Competitor / Editor / Thumbnail)
- - не self-eval, а distinct personas
- - деpe review через distinct passes