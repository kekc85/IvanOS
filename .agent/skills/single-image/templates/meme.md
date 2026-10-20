# Template: meme

Cultural reference + topic twist. Hook через recognition.

Reference: Distillery (general culture), Saagar Enjeti, finance Twitter.

## Brief structure

```yaml
type: meme
template: "<Drake | Distracted Boyfriend | Galaxy Brain | Two Buttons | Expanding Brain | This is Fine | Stonks | Pointing Spider-Men | Original>"

recognition:
  template_age_months: "<6-12 max для fast-moving, <24 для evergreen>"
  audience_recognition: "<test: mom test passed? top-100 mainstream? niche?>"
  twist: "<какая связь template ↔ topic>"

text_overlay_verbatim:
  # Зависит от template, минимум по 1 line per element
  top: "<text, ≤8 слов>"
  bottom: "<text, ≤8 слов>"
  # Для multi-element templates (Distracted Boyfriend / Galaxy Brain):
  per_element:
    element_1: "<label, ≤5 слов>"
    element_2: "<label, ≤5 слов>"
    element_3: "<label, ≤5 слов>"

composition:
  template_source: "<URL или path to template image>"
  text_position: "<native to template - top/bottom OR per-element>"
```

## Template-specific layouts

### Drake format
- Top panel: Drake rejecting → text «<thing rejected>»
- Bottom panel: Drake approving → text «<thing approved>»
- Twist: classic vs new approach to topic

### Distracted Boyfriend
- Guy = main subject (the «one being seduced»)
- Original GF = current state / status quo
- New woman = new thing / temptation
- Labels: 3 в кадре, ≤5 слов each

### Galaxy Brain
- 4-5 levels of brain (small → galaxy)
- Each level = escalating sophistication
- Twist: ironic that «basic» actually best

### Two Buttons
- Person sweating, deciding между 2 кнопками
- Labels на кнопках: 2 options of dilemma
- Twist: false dilemma comment

### Expanding Brain
- 3-5 panels, expanding glow
- Each = level of understanding
- Topic-specific progression

### This is Fine
- Dog в горящей комнате говорит «this is fine»
- Single bottom caption
- Topic = situation что should NOT be fine

### Stonks / Not Stonks
- Meme guy + chart up или down
- Single caption
- Topic = ironic metric reaction

### Pointing Spider-Men
- 2-3 Spider-Men поинтят друг на друга
- Labels: similar things якобы different
- Twist: same thing under different brands

### Original (no template)
- Skill-driven, hand-crafted meme
- Use only если у автора есть meme skill
- Higher risk но distinguishes

## Tool prompt

```
Tool: imgflip.com / kapwing.com (template generators)
OR: Photopea (custom composition)
OR: Canva (meme templates)

Steps:
1. Find template на knowyourmeme.com (verify currency)
2. Open в imgflip / Photopea
3. Add text overlays:
   - Font: Impact Bold (classic meme font) OR Inter Bold
   - Color: white с black outline
   - Size: 36-48pt
   - Position: native template position
4. Export PNG square 1:1 или 4:5
```

## Caption guidance

- Часто blank или ≤30 chars meta
- Hook patterns:
  - RU: «когда X.» / «правда.» / «<нет caption>»
  - EN: «when X.» / «true.» / «<no caption>»
- Meme сам несёт tone
- Avoid: long explanation (kills joke)

## Anti-patterns specific (FAIL)

- Outdated template (>12 мес для fast-moving, >24 для evergreen)
- Force connection (template не подходит topic)
- Inside joke без universality (mom test fail)
- Mean-spirited / attacking specific people
- Too text-heavy (>8 слов per overlay)
- Wrong font (use Impact OR Inter Bold)
- Hate speech / discriminatory humor
- Politically divisive (если не niche тема)

## Recognition test (mom test)

Перед использованием:
1. Объясни template без visual в 1 предложении
2. Если для объяснения нужны 3+ steps - too niche
3. Если только Twitter tech bros знают - too niche
4. Если общедоступно в meme culture последние 12 мес - PASS

## Cross-distribution

- X: 1:1 square
- Threads: cross-post from X
- IG: 1:1 или 4:5
- LinkedIn: использовать с caution (some templates не fit corporate)
- TG: 1:1

## Type-specific review hooks

- Template recognizable last 12 мес?
- Recognition test passed?
- Inside-joke check
- Не attacking persons
- Twist clean (1-second understand?)

## Memory cross-refs

- `[[feedback-no-attacking-competitors-by-name]]` - враг = явление
- `[[feedback-no-generic-ai-artifacts]]` - generic meme = brak