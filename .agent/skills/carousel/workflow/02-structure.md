# Workflow 02-structure - Slide-by-slide skeleton

**Назначение:** превратить `brief` в slide-by-slide skeleton с placeholder text и visual brief slot per slide.
**Вход:** финальный `brief` от `01-finalize.md`
**Выход:** `outline.slides[]` с placeholder structure → `03-write.md`

---

## Шаг 1 - Load template for family

Прочитать `templates/<family>.md`:

- framework-breakdown → `templates/framework-breakdown.md`
- listicle → `templates/listicle.md`
- story-case → `templates/story-case.md`
- panorama → `templates/panorama.md`
- reel-to-carousel → `templates/reel-to-carousel.md` (если нужно overrides, иначе из beats)

Извлечь default structure (3-act: Hook / Value / CTA) + slide-by-slide pattern.

---

## Шаг 2 - Build skeleton per family

### Family: framework-breakdown (8-12 slides)

```yaml
outline:
  slides:
    - position: 1
      role: hook
      placeholder: "Number + outcome + timeframe"
      verbatim_seed: "<brief.hook_seed>"
      
    - position: 2
      role: context
      placeholder: "Why this matters / problem statement"
      
    - position: 3..N-1
      role: numbered_step
      step_number: <1..N>
      placeholder: "Step <n>: <action>"
      
    - position: N-1
      role: synthesis
      placeholder: "Recap / pattern / lesson"
      
    - position: N
      role: cta
      placeholder: "Single artifact CTA"
```

### Family: listicle (8-10)

```yaml
outline:
  slides:
    - position: 1
      role: hook
      placeholder: "N items + 1 outcome"
      
    - position: 2..N-1
      role: item
      item_number: <1..N-2>
      placeholder: "Item name + description"
      odd_even_alternation: "odd=text-heavy / even=screenshot-heavy"
      
    - position: N
      role: cta
```

### Family: story-case (10-12)

```yaml
outline:
  slides:
    - position: 1
      role: hook
      placeholder: "Name + outcome + timeframe"
      
    - position: 2
      role: context
      placeholder: "Before state / situation"
      
    - position: 3
      role: problem
      placeholder: "What was broken"
      
    - position: 4-6
      role: action
      placeholder: "What was done - steps"
      
    - position: 7-8
      role: outcome
      placeholder: "Result with NUMBER"
      
    - position: 9-10
      role: lesson
      placeholder: "Generalizable takeaway"
      
    - position: N
      role: cta
```

### Family: panorama (3-8)

```yaml
outline:
  slides:
    - position: 1
      role: leading_standalone
      placeholder: "Hook word + must work isolated"
      visual_role: "left portion wide image"
      
    - position: 2..N-1
      role: middle_continuous
      placeholder: "0-10 words / typography-light"
      visual_role: "middle continuous portion wide image"
      
    - position: N
      role: payoff
      placeholder: "Final reveal word + CTA combined"
      visual_role: "right portion wide image"
```

### Family: reel-to-carousel

Inherit `outline.slides[]` из `brief.beats[]` (1 beat = 1 slide). Не переписывать structure - взять beat order + types.

---

## Шаг 3 - Real elements pre-allocation + render_strategy

Для каждого slide пометить planned real_elements + auto-assign render_strategy:

```yaml
slides[i].real_elements_planned:
  - "Cursor IDE Composer screenshot" (если topic про vibe coding)
  - "Stripe MRR $X figure"
  - "Author face photo"

slides[i].render_strategy: "typography | web-screenshot | desktop-manual | brand-asset | composite"
```

**Auto-assignment rules:**

```
if slide.role in [hook, context, synthesis, cta]:
  → render_strategy = typography (default)
  
elif slide.role in [numbered_step, item]:
  if real_elements_planned требует UI screenshot:
    if tool == web (Skool / TG Web / Stripe public / GitHub):
      → render_strategy = web-screenshot
    elif tool == desktop (Claude Code / Cursor / Figma):
      → render_strategy = desktop-manual
    else:
      → render_strategy = typography (с product names как text)
  else:
    → render_strategy = typography
  
elif slide.role == reveal:
  if reveal_type == author_face:
    → render_strategy = brand-asset
  elif reveal_type == UI:
    → render_strategy = web-screenshot OR desktop-manual
  else:
    → render_strategy = typography
  
elif family == panorama:
  → render_strategy = composite (для всех slides)
```

Override через explicit `slide.render_strategy` в brief.

**Real elements floor:** ≥40% slides должны иметь real_elements_planned. Если меньше → flag в brief, в `03-write.md` усилить.

---

## Шаг 4 - Pacing hints per slide

Для каждого slide задать `pacing_role`:

- slide 1: `promise + curiosity gap`
- slides 2-3: `tease reveal`
- middle slides: `open loop` (каждый tease'ит следующий)
- slide N-1: `loop close`
- slide N (CTA): `action trigger`

---

## Шаг 5 - Передача в write

```yaml
outline:
  family: "<one of 5>"
  slides: [<8-12 объектов с placeholder + visual_role + real_elements_planned + pacing_role>]
  hook_alternatives: []      # пусто, заполнится в write Pass A/B
  cta_alternatives: []
```

Перейти в `workflow/03-write.md`.

---

## Принципы

1. **Template-driven.** Каждый family имеет canonical structure, не reinventing.
2. **Position is meaning.** Hook = 1, CTA = N. Middle = beats.
3. **Real elements floor ≥40%.** Carousels без proof = generic.
4. **Pacing chain mandatory.** Каждый slide имеет role в pacing chain.
5. **Reel-to-carousel inherits.** Не переписываем beat-mapping, используем как есть.