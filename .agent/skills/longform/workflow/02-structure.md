# 02-structure - outline + headline

> Принимает `finalized_brief`. Грузит template для выбранного type, строит 3-section outline (Koe), генерит headline.

## Step 1 - load template

По `finalized_brief.type` грузить template:

| Type | File |
|---|---|
| teaching | `templates/teaching-essay.md` |
| story | `templates/story-essay.md` |
| framework | `templates/framework-essay.md` |
| contrarian | структура ниже в этом файле |
| case_study | структура ниже в этом файле |
| listicle | `templates/listicle.md` (v1.1) |
| deep_dive | структура ниже в этом файле |

Template содержит:
- 3-section structure adapted под type
- Pacing recommendations (что в каком section)
- Type-specific требования к main_thesis / personal_anchor / examples / CTA

## Step 2 - построить 3-section outline (Dan Koe baseline)

```
INTRODUCTION (15-20% от target_length)
- Hook (выбранный из brief.hook_variants[])
- Relatable problem (audience pain читается за 30 секунд)
- Personal anchor (story moment / observation)

INSIGHT (40-50% от target_length)
- Main "aha" (1 центральный тезис, не больше)
- Why it works (first principles / mechanism)
- Concrete examples (3-5 с specific numbers)

PROCESS (30-40% от target_length)
- Step-by-step / Principle list / Application
- Common pitfalls (что НЕ делать)
- CTA (subscribe / next article / community)
```

Type override этой baseline:
- **Teaching** - INSIGHT расширен (механизм важнее всего), PROCESS детальнее
- **Story** - INTRODUCTION расширена (нарратив занимает больше), INSIGHT встроен в payoff story
- **Framework** - INSIGHT доминирует (mental model + почему он работает), PROCESS = как применить framework

## Step 3 - headline (5 elements)

Headline = (Specific Promise) + (Audience Marker) + (Time/Constraint) + (Mechanism Hint) + (Differentiation).

Сгенерировать 3 варианта headline. Записать в brief.

Для разных платформ - разные стратегии:
- **Personal blog** - SEO-friendly H1 (60-70 chars)
- **Newsletter (Kit/Beehiiv)** - subject line A/B (3 варианта, 40-60 chars каждая) + preheader (90-100 chars)
- **LinkedIn article** - LinkedIn-friendly headline (90-110 chars, prompts curiosity без clickbait)

Образцы - `references/hook-patterns-longform.md`.

### Headline-валидаторы

- НЕ начинается с numerals если type != listicle (auto-fail)
- НЕ содержит «Ultimate Guide» / «Everything You Need» / «Полный гайд» (banned listicle pattern)
- НЕ содержит em-dash «-» (memory)
- НЕ содержит trailing «?» если type != story (story может)
- НЕ содержит больше 1 двоеточия

## Step 4 - section outline (детальный)

Под каждый section прописать буллеты что будет внутри. Не prose - конспект.

```yaml
outline:
  introduction:
    hook: "<выбранный hook>"
    problem_setup: "<1-2 строки про pain>"
    personal_anchor: "<story moment, 2-3 строки>"
    bridge_to_insight: "<1 строка перехода>"

  insight:
    main_aha: "<1 центральный тезис>"
    why_it_works:
      - "<reason 1 + 1 line proof>"
      - "<reason 2 + 1 line proof>"
      - "<reason 3 + 1 line proof>"
    concrete_examples:
      - "<example 1: specific numbers + context>"
      - "<example 2>"
      - "<example 3>"

  process:
    steps:
      - "<step 1 + 1 line how>"
      - "<step 2>"
      - "<step 3>"
    pitfalls:
      - "<pitfall 1>"
      - "<pitfall 2>"
    cta: "<1-2 строки CTA соответствующего platform>"
```

## Step 5 - section length budget

Распределить `target_length` по секциям по pacing (см. Step 2). Записать примерные word count per section.

```yaml
length_budget:
  introduction: <N words>
  insight: <N words>
  process: <N words>
  total: <target_length>
```

`03-write.md` будет уважать этот budget с tolerance ±15%.

## Step 6 - visual structure for platform

Подсказки для `03-write.md` как форматировать:

| Platform | Visual structure |
|---|---|
| Personal blog | H1 + H2 для секций + H3 для подразделов внутри INSIGHT |
| Newsletter (Kit/Beehiiv) | H1 + bold-section headers + блоки `quote` / `divider` между секциями |
| LinkedIn article | H1 + bold для подзаголовков (LinkedIn не уважает H2/H3) + line breaks частые |

## Output для `03-write.md`

```yaml
structure_output:
  finalized_brief: <inherit>
  outline: <Step 4>
  length_budget: <Step 5>
  headline_variants: ["<1>", "<2>", "<3>"]
  visual_structure_hint: <Step 6>
  template_path: "templates/<type>.md"
```

## Что НЕ делать

- НЕ строить outline без template - даже простой story-essay требует template ( относится к курсу, в skill - наоборот, полный template обязателен)
- НЕ генерить более 1 main_aha - split на серию
- НЕ нарушать pacing - INTRODUCTION 50% от длины = brake, не essay

## Memory cross-refs

- - Шаг 1 brief / Шаг 2 outline / Шаг 3 write
- - Big Idea (=main_aha) должна превосходить конкурентов