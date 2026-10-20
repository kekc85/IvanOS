# Visual Brief - REAL elements first

Reference для `workflow/03-write.md` Pass 2 (visual brief generation). Source: bucket-a (top 3 cross-author pattern: real screenshot ≥1 mandatory), bucket-b (Welsh / Acosta / Pieter Levels), bucket-d (dense-info proof carousels).

Используй когда:
- Пишешь visual brief для каждого slide
- Проверяешь brief на abstraction / generic
- Выбираешь real_elements под family
- Решаешь нужен ли AI image gen или хватает screenshot

---

## 1. Schema - 6+1 полей visual brief

Каждому slide назначается visual brief в YAML структуре:

```yaml
slide_N:
  text: "5-25 слов на slide"
  visual_brief:
    real_elements:           # MAIN FIELD - реальные screenshots / продукты / числа
      - "<element 1>"
      - "<element 2>"
    composition:             # что в кадре, layout, focal point
      "<description>"
    typography:              # шрифт / размер / weight
      "<spec>"
    color_palette:           # brand colors + accent
      "<palette>"
    text_overlay:            # exact text который ляжет поверх (annotations)
      "<verbatim text>"
    abstraction_check:       # PASS / FAIL против banned 12
      "<PASS|FAIL>: <reason>"
  pacing_role:               # promise / curiosity gap / reveal / loop-close / cta
    "<role>"
```

**Главное поле:** `real_elements`. Если пусто или только generic ("какой-то dashboard") - brief брак, return на переписать.

**`abstraction_check`** ссылается на 12-item list в `banned-ai-imagery.md`. Если попадает в любой из 12 patterns - FAIL.

**`pacing_role`** связывает slide с соседями (см. `carousel-anatomy.md` раздел 3).

---

## 2. Taxonomy real_elements - 5 категорий

### 2.1 UI screenshots (priority 1)

Реальный интерфейс tool с конкретной активностью.

Что считается:
- Cursor IDE Composer panel с verbatim промптом ученика
- Lovable dashboard с running app preview
- Claude Code сессия в терминале с конкретной командой
- n8n canvas с workflow nodes
- Stripe MRR dashboard ($X verbatim)
- Skool community page с member count
- Beehiiv subscribers dashboard
- Kit ESP automation builder

Что НЕ считается (fail):
- Mockup в Figma stylized как UI
- Generic «dashboard illustration»
- Screenshot закрытый чёрным placeholder
- Подделанный screenshot (репутационный риск per Pieter Levels)

### 2.2 Product names verbatim (priority 2)

Точное название tool с правильным написанием.

Что считается:
- `Claude Code` (не «AI ассистент»)
- `Lovable` (не «AI app builder»)
- `Cursor` / `@cursor_ai`
- `n8n` (не «automation tool»)
- `Stripe` (не «payment processor»)
- `Skool` (не «community platform»)

Правило: tools должны быть verbatim с правильным capitalization. Если упоминаешь tool - проверь его официальное написание.

### 2.3 Numbers (priority 3)

Конкретные специфические числа из реального experience.

Что считается:
- `<твоя выручка> за 12 месяцев` (автор track record)
- `<число учеников>` (verified)
- `47 минут` (specific timeframe)
- `9.6/10 NPS`
- `30 топ-кейсов`
- `125 недель подряд` (discipline cue)

Что НЕ считается:
- Round numbers `10X`, `100`, `1000` (AI-default flag, bucket-c)
- Vague `тысячи`, `много`, `быстро`
- Round currencies `1М ₽` (вместо точного `940 000 ₽`)

Правило: чем специфичнее, тем выше trust. `47 минут` > `быстро`. `940 000 ₽` > `почти миллион`.

### 2.4 Real dashboards (priority 1, overlap с UI)

Raw screenshot proof без annotation поверх.

Что считается (bucket-d список):
- Stripe MRR graph + revenue breakdown
- GitHub contribution graph (green squares)
- Twitter/X Analytics impressions
- IG Insights reach
- YouTube Studio subscribers
- Beehiiv / Kit subscriber chart
- Plausible / Fathom site traffic
- Gumroad / Lemon Squeezy sales

Правило: dashboard slide должна быть **raw screenshot** (max 1 sticker arrow или circle highlight). Heavy filter = «fake screenshot» suspicion = trust loss.

### 2.5 Face photo (priority 2)

Реальная фотография автора, не AI avatar.

Что считается:
- Face-cam frame из Reel (motion-triple trick Welsh)
- Studio shot автора
- Behind-the-scenes shot (квартира / стол / мониторы)
- Conference / stage photo

Что НЕ считается:
- HeyGen avatar still (для skill carousel = брак, для talking video = ок)
- AI-generated portrait
- Stock photo «expert at laptop»

Правило (Acosta pattern): face photo bottom-right на 1-2 slides в carousel = humanization signal. Не на каждом - надоест.

---

## 3. Per-family real_elements floor

Минимум процент slides с real_elements per carousel family:

| Family | Floor | Что обязательно |
|---|---|---|
| `framework-breakdown` | 40% | Минимум 4 из 10 slides: hook screenshot + 2 step UIs + proof |
| `listicle` | 60% | Каждый item slide = product name + UI screenshot этого tool |
| `story-case` | 50% | Hook + context photo + 2 process screenshots + proof dashboard |
| `panorama` | 40% | Continuous visual + минимум 1 dashboard на завершающем slide |
| `reel-to-carousel` | 50% | Frames из card.md + UI inventory items + proof slide |

**Detection в `04-review.md`** (CR-G4 Real elements floor):

```
count_real = sum(1 for slide in slides if len(slide.visual_brief.real_elements) >= 1)
floor_threshold = floor_per_family[family]
if count_real / total_slides < floor_threshold:
    FAIL CR-G4
```

---

## 4. GOOD vs BAD visual brief (3 пары)

### Пара 1: hook slide framework-breakdown

BAD:
```yaml
real_elements: []
composition: "Bold modern hook slide with dynamic gradient background"
typography: "Sans-serif large"
color_palette: "Brand colors with accent"
text_overlay: "8 ходов вайбмаркетинга"
abstraction_check: "PASS"
```

Проблема:
- `real_elements` пуст
- `composition` использует AI-cliché слова `modern / dynamic / gradient`
- `typography` без конкретики (какой шрифт / размер)
- `text_overlay` = title без promise/timeframe

GOOD:
```yaml
real_elements:
  - "Hero screenshot Skool community с member count 247 + MRR $X в углу"
  - "Цифра '8' крупно слева"
typography: "Inter 96pt headline + 36pt subline, чёрный текст на off-white #FAFAFA"
color_palette: "off-white background + чёрный текст + Ivan red accent (HEX #D72E2E) для цифры 8"
composition: "Цифра 8 занимает левую треть slide. Справа Skool screenshot занимает правые две трети, sligtly tilted -3deg. Hook текст overlay снизу: '8 ходов вайбмаркетинга. <твоя выручка> за 12 месяцев. Playbook.'"
text_overlay: "8 ходов вайбмаркетинга / <твоя выручка> за 12 месяцев / Playbook"
abstraction_check: "PASS - real screenshot Skool + verbatim number <твоя выручка>"
pacing_role: "promise + curiosity gap (что за 8 ходов?)"
```

### Пара 2: item slide listicle

BAD:
```yaml
real_elements:
  - "Иконка инструмента"
composition: "Tool name large + abstract icon"
typography: "Modern bold"
color_palette: "Vibrant accent"
text_overlay: "1. Lovable - для лендингов"
abstraction_check: "PASS"
```

Проблема:
- `real_elements` = «иконка» абстрактно (не logo, не screenshot)
- `composition` дублирует AI-cliché
- Нет реального UI, нет цифры результата

GOOD:
```yaml
real_elements:
  - "Lovable dashboard screenshot с running preview лендинга подписки Skool"
  - "URL bar видна: lovable.dev/projects/ivan-skool"
  - "Цифра '47 минут' в правом верхнем углу как сборочное время"
typography: "Inter 72pt step number '01' слева, 48pt product name 'Lovable', 28pt описание под скриншотом"
color_palette: "Lovable purple #6366F1 акцент + off-white BG + чёрный текст"
composition: "Левая треть: крупно '01 / Lovable'. Правые две трети: screenshot dashboard tilted -2deg. Подпись внизу: 'Лендинг подписки за 47 минут. Голосом в Composer.'"
text_overlay: "01 / Lovable / Лендинг подписки за 47 минут"
abstraction_check: "PASS - real Lovable UI + verbatim product name + specific timeframe"
pacing_role: "item reveal + sets pattern для slides 2-N"
```

### Пара 3: proof slide story-case

BAD:
```yaml
real_elements:
  - "График роста"
composition: "Стилизованный chart с восходящей линией"
typography: "Sans-serif"
color_palette: "Green growth accent"
text_overlay: "Результат: рост в 10X"
abstraction_check: "PASS"
```

Проблема:
- `real_elements` = «график» без указания source
- `composition` стилизованный chart = fake suspicion
- `10X` = round number (AI flag)
- Нет verbatim dashboard

GOOD:
```yaml
real_elements:
  - "Stripe MRR dashboard raw screenshot, мобильный shot iPhone Stripe app"
  - "MRR line $0 в марте -> $12 450 в сентябре"
  - "Конкретные subscriber numbers: 247 active members в Skool"
composition: "Full-bleed screenshot Stripe dashboard. Минимальный overlay - один зелёный circle highlight на MRR числе. Подпись внизу 24pt: 'Skool MRR март -> сентябрь. Один человек, ноль команды.'"
typography: "Inter 24pt только для подписи. Сам screenshot не закрывать typography overlay"
color_palette: "Native Stripe dark mode UI + один зелёный accent circle"
text_overlay: "Skool MRR март -> сентябрь / Один человек, ноль команды"
abstraction_check: "PASS - raw dashboard screenshot + verbatim numbers + zero filter"
pacing_role: "reveal payoff (рост саккадирующего читателя -> save)"
```

---

## 5. abstraction_check - 12-item gate

Перед тем как brief уйдёт в render / output - прогон против 12 banned patterns из `banned-ai-imagery.md`.

Detection method (для каждого item):
1. Прочитай `composition` + `real_elements` + `text_overlay`
2. Match против 12 banned patterns (см. `banned-ai-imagery.md`)
3. Если попадает - FAIL с указанием которого pattern

Auto-fail patterns (любое попадание = brief переписать):
- Generic AI illustration людей
- Gradient blob / 3D abstract shapes
- Robot hands / brain circuits
- Stock photo «smiling team»
- AI avatar вместо real photo
- Generic vector icons вместо logos
- Fake/cropped dashboards
- AI-generated charts без real data

Warning patterns (можно оставить если оправдано, но flag):
- Soft pastel background (ок только для quote-card type)
- Symbolic «expert» illustration (ок только если brand mascot документирован в config.md)
- AI illustration generally (ок только как demonstration не decoration - Heather Cooper exception, bucket-a)

---

## 6. Tool prompts для AI image gen (когда screenshot недостаточен)

В v1.0 carousel skill производит brief + manifest, render отдельно. Но если slide требует AI-render (например stylized hook background) - используй tool-specific patterns:

### 6.1 Midjourney

Используй для: hero slide background (subtle), brand mascot stylized, abstract texture.

Шаблон prompt:
```
[subject], minimal flat design, [Ivan brand palette - off-white #FAFAFA background, чёрный text, red accent #D72E2E],
no people, no AI tells, --ar 4:5 --style raw --v 6
```

Запрещено:
- `cinematic lighting` без specific reason
- `3D render` / `octane` (AI tells)
- `vibrant gradient`
- Любые люди (потому что AI-illustrated люди = banned)

### 6.2 higgsfield (для product visuals)

Используй для: brand product shots если carousel о продукте автора. Через `higgsfield-generate` skill chain.

Шаблон передачи в higgsfield:
```
product_shot mode, [product description], minimalist studio, soft natural lighting,
brand palette: off-white + чёрный + red accent
```

Не использовать для people generation - Soul ID required (chain в `higgsfield-soul-id`).

### 6.3 Nano Banana / Pro (для character / reference image work)

Используй для: persona consistency если в carousel multiple slides с одним персонажем (rarely в авторском контенте, чаще для ученика курса).

Через `higgsfield-generate` skill с reference image.

### 6.4 Open Carrusel (Claude-driven HTML→PNG)

Для typography-heavy slides (Welsh / Alić стиль) - не нужен image gen, генерится HTML/CSS и screenshot'ится в PNG. Reference: github.com/Hainrixz/open-carrusel.

Шаблон task для Claude Code:
```
Сгенерируй HTML+CSS slide 1080×1350px:
- background: off-white #FAFAFA
- typography: Inter
- headline: [text] 96pt чёрный
- accent number: [N] 144pt #D72E2E
- export: PNG via puppeteer screenshot
```

---

## 7. Composition principles (8 правил)

Source: bucket-d панорамные carousels, bucket-b LinkedIn carousel specs, single-image composition-principles.

### 7.1 Rule of thirds

Делишь slide на 3×3 сетку. Focal point - на пересечении линий, не в центре.

Применение: hero screenshot в правых 2/3, headline number в левой 1/3 (см. GOOD пример 1).

### 7.2 Single focal point per slide

Один main element. 2-3 supporting max. >7 distinct elements = cluttered = swipe-away.

### 7.3 Type hierarchy (3 levels)

Каждый slide содержит максимум 3 уровня шрифта:
- L1 Headline 60-96pt
- L2 Body 28-40pt
- L3 Caption / annotation 18-24pt

Не использовать 4+ уровня - читатель теряется.

### 7.4 80px padding all sides

LinkedIn PDF carousel требует 80px safe padding от краёв (UI Linkedin может crop). Source: bucket-b verbatim spec.

### 7.5 Central 880×880 safe area

Внутри 1080×1350 canvas - safe zone 880×880 центрированная. Важные элементы (text / faces / logos) только внутри.

### 7.6 Sans-serif default

Inter / Roboto / Helvetica Neue. Serif только для editorial accent (rare).

### 7.7 Min 24pt absolute floor

Любой текст <24pt не читается на mobile (LinkedIn render ~360-450px width на мобильном).

### 7.8 Single accent color

Один brand accent (автор red #D72E2E). Не использовать 3+ ярких colors в одном slide - визуальный шум.

---

## 8. Per-platform brief adjustments

| Param | Instagram 1080×1350 | LinkedIn PDF 1080×1350 |
|---|---|---|
| Padding | 60-80px все стороны | 80px все стороны (mandatory) |
| Headline pt | 60-96pt | 60pt+ обязательно |
| Body pt | 36-40pt | 36-40pt |
| Min pt | 24pt | 24pt absolute |
| Color mode | RGB | RGB 72 DPI |
| File | JPEG / PNG per slide | PDF multi-page |
| Max slides | 10 best (20 hard cap) | 12 best (300 hard cap) |
| Caption fold | 125 chars | 210 chars до «see more» |

---

## 9. Decision tree - какой brief выбрать

```
Slide hook первый? → typography-heavy + 1 hero element (screenshot OR number)
Slide item / step? → product name + UI screenshot этого product
Slide proof / reveal? → full-bleed dashboard screenshot raw
Slide context / story? → photo автора + minimal text
Slide synthesis / lesson? → typography + 1 крупное число
Slide CTA? → button-style design + 1 artifact name
```

Если slide роль непонятна - см. `carousel-anatomy.md` раздел 2 (role taxonomy).