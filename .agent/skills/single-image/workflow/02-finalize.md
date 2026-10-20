# Workflow 02: Finalize

Финализация перед design-brief: выбор type + reference creator + platform + aspect.

## Input

От mode file:
- `topic` (concrete topic)
- `hints.type_suggestion`
- `hints.platform_suggestion`
- `verbatim_quote` (если mode=transcript)

## Шаги

### Step 1: Finalize type

Если `hints.type_suggestion` есть И user не override - использовать suggestion.

Иначе показать decision tree из `knowledge/visual-types.md`:
```
Topic: «<topic>»

Какой type лучше? (suggestion: <X>)
1. concept-diagram - mental model / framework
2. dashboard-screenshot - real metric proof
3. meme - cultural recognition + twist
4. quote-card - pocket-wisdom phrase
5. before-after - transformation visual
```

User выбирает 1-5 или «другой» (тогда либо edge case либо нужен другой skill).

### Step 2: Type validation

Каждый type имеет requirements:

| Type | Required |
|---|---|
| concept-diagram | geometry (1 из 10), labels (verbatim) |
| dashboard-screenshot | real verified metric, source, permission если customer data |
| meme | template (recognized), recognition test passed |
| quote-card | quote (≤140 chars), attribution verified |
| before-after | before state + after state, honest delta |

Если type chosen но requirements не выполняются → flag и ask user fill missing.

### Step 3: Finalize reference creator

Из `knowledge/reference-creators.md` per type:
- Если в config есть user-specific reference_creators для type → use those
- Иначе - top default per type:
  - concept-diagram: Jack Butcher
  - dashboard-screenshot: Pieter Levels
  - meme: top-trending template (last 6 мес из knowyourmeme.com)
  - quote-card: Naval
  - before-after: Pat Walls

User может override.

### Step 4: Finalize platform

Иерархия:
1. `--platform` flag если был
2. `hints.platform_suggestion` если был (из Mode A active_launch)
3. `config.subject.platforms_primary[0]` (primary platform)
4. Default `X`

Если автор multi-platform, primary platform = тот для которого designим main brief. В output (`06-output.md`) добавим cross-distribution variants.

### Step 5: Finalize aspect

Из `config.aspect_defaults[platform]`:
- X: 1:1
- LinkedIn: 1.91:1
- Instagram: 4:5
- TG: 1:1
- Threads: 1:1

Override через `--aspect` flag.

### Step 6: Brand identity injection

Из config.visual_identity:
- palette_primary (что использовать в этом brief)
- typography (sans/serif/mono)
- aesthetic_principles (minimalist / editorial / etc)

Эти параметры передаются в 03-design-brief как defaults.

### Step 7: Output structured intent

```yaml
finalize:
  topic: "<concrete topic>"
  type: "<one of 5>"
  reference_creator:
    name: "<creator>"
    style_notes: "<extracted from knowledge/reference-creators.md>"
  platform: "<primary platform>"
  aspect: "<ratio>"
  brand_identity:
    palette: [...]
    typography: {...}
    aesthetic: [...]
  type_requirements_check: "PASS / FAIL: <what missing>"
  verbatim_quote: "<if from transcript>"
```

→ `03-design-brief.md`

## Принципы

1. **Type определяется один раз.** После finalize - design brief строится строго под type.
2. **Reference - style anchor.** Не близкий clone, а структурный референс.
3. **Platform primary determines aspect default.** Если multi-platform - выбираем main, остальные в output как cross-distribution.
4. **Brand identity всегда injected.** Каждая картинка - часть бренд recognition flywheel.

## Edge cases

- **Type не подходит для topic** → suggest alternative skill (post для текста / carousel для 2+ кадров / video для motion)
- **Type chosen но requirements fail** → ask user fill missing (verify number / find quote source / etc)
- **Multiple platforms competing** → ask user который primary, остальные = cross
- **Reference creator пустой** → use default per type from knowledge/reference-creators.md