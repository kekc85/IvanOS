# panorama-mechanics

> Техническая база для panorama-каруселей (canvas math, slice rules, tooling, viral patterns). Загружается когда `family=panorama` или автор запрашивает «панорамная карусель» / «wide composition». Источник - `.business/growth/carousel-research/2026-05-28/bucket-d-panorama-and-dense.md` (444 строки research).

## Что такое panorama-карусель

Wide composition (canvas N × 1080 px width × 1350 px height) разрезается на N вертикальных сегментов 1080×1350. Каждый сегмент загружается как отдельный slide карусели. Зритель свайпает - видит continuous flow вместо изолированных карточек.

**Базовая canvas math:**

- 3 slides = 3240 px width × 1350 px height
- 5 slides = 5400 px width × 1350 px height
- 8 slides = 8640 px width × 1350 px height
- 10 slides = 10800 px width × 1350 px height
- Каждый разрез строго по 1080 px boundary (вертикальные guides)

**Aspect ratio решение:**

- 1080×1350 portrait = оптимально для mobile feed (4:5). Default для автора.
- 1080×1080 square = legacy IG, меньше визуального real estate. Использовать только если square required brand-системой.
- Mix aspect-ratio между slides ломает seamless эффект. Все slides ОДНОГО формата.

## Optimal slide count

| Slides | Применение | Swipe-through rate |
|---|---|---|
| 3 | Sweet spot panorama. Минимум для эффекта continuous. | ~80% |
| 4 | Multi-area scenes (например 4-этапная цепочка). | ~75% |
| 5-8 | Detailed storytelling panorama (revenue timeline / stack reveal). | ~70-72% |
| 9-10 | Top influencers max - completion rate падает. | ~65% |
| 10+ | Резкий drop-off, не использовать. | <60% |

**Default для автора:** 5 slides × 1080×1350 portrait = 5400×1350 canvas. Sweet spot между swipe completion и storytelling depth.

**Image source requirements (если входит реальная панорамная фотография):**

- 2160 px wide минимум для 2-slide split
- 3240 px wide для 3 slides
- 5400 px wide для 5 slides
- 10800 px wide для 10 slides
- iPhone панорамные снимки (до 63 MP) натурально подходят

## LinkedIn специфика

LinkedIn native multi-image carousel deprecated с late 2023. Единственный способ - **multi-page PDF document upload**.

- Каждая slide = одна страница PDF
- Размер каждой страницы 1080×1350
- Padding 80 px со всех сторон (LinkedIn UI элементы могут перекрыть края)
- Sans-serif min 24 pt текст
- Max pages 300 / Max file 300 MB
- Panorama-эффект работает идентично IG - PDF рендерится swipeable images клиент-сайд

## Правила разделения (slide isolated + работает в панораме)

1. **Leading standalone slide 1.** Первый slide должен работать как самостоятельный poster. Если зритель не свайпает - это всё равно интересный кадр с promise. Bold headline + visual element ≥50% площади.

2. **Areas of interest distributed.** Интересные элементы (numbers / icons / face / UI accent) распределены равномерно по всей wide composition. Не только в slide 1 и slide N. Иначе зритель прыгает к payoff и теряет середину.

3. **Per-slide micro-headline.** Даже если основное продолжение в slide N+1 - каждый slide содержит свой micro-text или icon чтобы держать interest standalone.

4. **Cut lines clean.** Важные детали (лица / key text / логотипы / numbers) НЕ должны попадать на cut lines. Тест - провести вертикальный ruler через каждую 1080 px границу, всё что попадает на линию - сдвинуть в центр своего 1080-zone.

5. **Same aspect ratio everywhere.** Один slide в другом формате = visible jump, ломает continuous эффект.

6. **Overlap continuity.** Shapes / lines / colors / arrows переходят через границы между slides. Стрелка начинается в slide 1, заканчивается в slide 2 - психологически тянет swipe.

7. **Swipe-left visual cue.** Стрелка / «→» / «1/N» pagination в углу. 95% каруселей не имеют этого. Добавление повышает вовлечённость с 1.83% до 2% (PostNitro benchmark).

## 7 вариаций panorama

1. **Horizontal panorama** - классика. Wide image слева направо, разрезается на 3-8 vertical slides. Для landscapes, продуктовых линеек, процессов.

2. **Vertical-scroll panorama внутри одного slide** - 4:5 portrait extended вверх-вниз. TikTok-style scroll но в carousel context работает как extended single slide. Реже используется.

3. **Depth / parallax illusion** - слои переднего плана сдвигаются медленнее заднего между slides. Manual эффект через offset shapes. Сложный, но wow.

4. **Character continuity** - персонаж переходит через slides, меняет позы. Используется storytelling каруселями (Riley Brown / Cheung style). Подходит когда face-cam источник.

5. **Numerical progression panorama** - цифры от 0 до 100 (или $0 до $100K MRR) растянуты через все slides. Каждый slide = milestone. Идеально для revenue / growth timelines.

6. **Typography reveal panorama** - одно длинное слово / фраза разорвано через slides. Payoff = full word reveal на последнем slide. Casper ZZZ pattern.

7. **Stacked panorama (Subway-style)** - несколько горизонтальных полос одна над другой внутри 1350 px height. Каждая полоса = свой message. Daily deals / weekly schedule структура.

## Tools - production цепочка

### Adobe Photoshop (контроль)

```
File > New > N×1080 px wide × 1350 px tall (например 5400×1350 для 5 slides)
View > Guides > New Guide Layout > N columns
Slice tool (C) > Slices From Guides
File > Export > Save for Web (Legacy) > All Slices > 1080 px height
```

Reference template - Photoshop Training Channel free PSD.

### Canva (speed)

- Custom Size = N×1080 px wide × 1350 px tall (например 5400×1350)
- Add ruler guidelines на каждой 1080 px mark
- Дизайнить seamless с overlap элементами через границы
- Use Grid Maker / Split Image button
- Download individual slides as JPG/PNG

### Figma (designers)

- Plugin **Instagram Carousel Creator** - design + preview + auto-export
- Plugin **IG Multi Image Splitter** - split design в multiple IG posts
- Plugin **Split to Frames** - generic frame splitter
- Plugin **CarouselAI** - AI-driven carousel generation в Figma
- Manual способ - создать N frames 1080×1350 + Slice tool

### Online splitters (mobile / quick)

- splitimage.im/panorama-splitter
- omnicalculator.space/instagram-panorama-splitter
- post-bridge.com/tools/instagram-carousel-splitter
- ezibreezy.com/tools/instagram-carousel-splitter
- pixample.com/instagram-carousel-splitter

### AI генерация panorama

- Midjourney `--ar 6:1` или `--ar 8:1` для wide composition
- MJ Splitter (mjsplitter.com) для grid output
- Open Carrusel (github.com/Hainrixz/open-carrusel) - Claude CLI генерирует HTML/CSS slides, скриншотит в PNG exact IG dimensions
- Mirra MCP carousel - 7-slide carousel за ~43 секунды через Claude/Cursor

### Mobile apps

- SwipeMix (iOS) - all-in-one swipegram maker
- Caro app - простейший panorama splitter
- Panoslice (Android)
- Panorama Split (mwm.ai)

## 8 viral panorama-примеров (с переносом на автора)

### Example 1 - Subway daily deals horizontal

- Brand: Subway US Instagram
- Wide image: длинная горизонтальная фотография sub-сэндвича разрезана на slides где каждый = day-of-week deal
- Hook slide 1: начало сэндвича + «$5 footlong»
- Payoff slide N: конец сэндвича + общая неделя
- Перенос на автора: продуктовая линейка (вайбкодинг → вайбмаркетинг → клуб) как continuous flow слева направо, каждый slide = свой элемент стека.

### Example 2 - Starbucks Holiday Astrology pairing

- Brand: Starbucks IG
- Wide composition: continuous illustrated holiday скатерть с food pairings по знакам зодиака
- Каждый slide = pair созвездие + напиток + еда
- Hook slide 1: bold astrology icon + «your sign's perfect pairing»
- Перенос на автора: «твой AI-стек по типу проекта» - каждый slide = pair тип проекта + tools.

### Example 3 - Casper continuous «ZZZ»

- Brand: Casper mattress IG
- Wide composition: одна gigantic «Z» буква растянута через все slides
- Hook slide 1: загадочный фрагмент Z (curiosity gap)
- Payoff slide N: full Z reveals + caption про сон
- Перенос на автора: typography reveal panorama - слово «ВАЙБКОДИНГ» растянуто через 8 slides, payoff = «больше не profession».

### Example 4 - Travel landscape panorama (samirzarrouk.com pattern)

- Pattern: drone shot Хельсинки разрезан на 6-8 slides
- Hook slide 1: most dramatic часть landscape (cloud burst)
- Payoff slide N: завершение panorama (sunset edge)
- Перенос на автора: десктоп-панорама day-in-the-life - macOS с открытыми Claude + browser Lovable + Stripe + Notion панелями как continuous «один день моей работы».

### Example 5 - Brand campaign panorama (Nude Project / Gentle Monster)

- Pattern: editorial wide product shot + per-slide product detail callout
- Hook slide 1: model / product hero + headline
- Middle: detail close-ups переходят
- Payoff: lookbook total flow
- Перенос на автора: контент-завод visual - wide composition AI tools flowchart, per-slide micro-explanation.

### Example 6 - Architecture / photography swipegram (itchban)

- Pattern: 8:5 panoramic crop в Lightroom → Photoshop slice template
- Hook slide 1: dramatic visual элемент (например лицо в углу)
- Payoff: full architectural сцена
- Перенос на автора: dashboard panorama - Stripe revenue график растянут через 5 slides, каждый slide = milestone month.

### Example 7 - Hold-and-Scroll (May 2026 viral)

- Pattern: «Hold and Scroll» - пользователь зажимает первый slide, картинка анимируется
- IG trend May 2026 (newengen.com)
- Перенос на автора: anti-pattern reveal - «вот так делают курсы» → swipe → «вот как делает вайбмаркетинг».

### Example 8 - Before-After transformation (browsbyzulema audio)

- Pattern: slide 1 = «World, stop!» frozen before-state, далее slides = transformation reveal
- Hook slide 1: frozen «до» state с обещанием reveal
- Payoff slide N: «после» полный reveal
- Перенос на автора: «контент до AI / после AI» - старый ручной процесс слева, новый AI-процесс справа в continuous panorama.

## Stack-as-Panorama (signature visual для автора)

Tech stack показан как continuous цепочка horizontal:

- Slide 1: Claude Code logo + role («ядро методологии»)
- Slide 2: стрелка → Lovable screenshot («лендинг за час»)
- Slide 3: стрелка → higgsfield generation example («креативы»)
- Slide 4: стрелка → Stripe dashboard («первые продажи»)
- Slide 5: total summary («$X за Y дней»)

Wide composition tools left-to-right = visual инструментальной цепочки + per-tool proof screenshot. Это переносимо в любой пост про вайбмаркетинг / vibemarketing stack.

## 14 anti-patterns (что НЕ работает в panorama)

1. **Different aspect ratios между slides** - ломает seamless эффект.
2. **Important details на cut lines** - лицо / логотип / key text режутся.
3. **Generic first slide без hook** - «10 tips для X» без visual element и promise = провал на slide 1.
4. **Wall of text slide** - параграф текста = swipe-away. Max 15 слов per slide для panorama (text-light формат).
5. **Boring middle slides** - panorama без интересных элементов в slides 2-4 теряет swipe momentum.
6. **Wrong slide order на upload** - IG сохраняет порядок загрузки. Один slide в неправильном месте = ломает continuity.
7. **Heavy filter поверх dashboard screenshot** - фильтр на Stripe = «fake screenshot» suspicion. Raw скриншот = trust.
8. **CTA только на last slide** - меньше людей видят финальный slide. Распределить value + CTAs по нескольким slides.
9. **No swipe cue** - отсутствие стрелки / «→». 95% каруселей не имеют, добавление = 0.17 percentage points вовлечённости.
10. **Inconsistent branding между каруселями** - разные fonts / colors каждый пост = diluted recognition. Stick to 2 fonts + 3 colors.
11. **Panorama без isolated value на slide 1** - если первый slide не работает standalone, non-swipers не получают value = брак для discovery feed.
12. **Carousel длиннее 10 slides на IG** - drop-off резкий после slide 10. Для длинных историй разбить на 2 carousels.
13. **Fake / cropped dashboard** (Pieter Levels callout) - browser dev tools edit, test mode Stripe, one-time payments как recurring - детектится комьюнити, репутационный ущерб.
14. **Panorama для контента который не требует continuous reveal** - listicle «10 tips» не нужен panorama. Format должен matchать message.

## Pre-publish panorama checklist (LLM gate CR-G9)

Перед output карусели c `family=panorama` проверить:

- [ ] Все slides одного aspect ratio (1080×1350)
- [ ] Slide count в диапазоне 3-8
- [ ] Slide 1 работает isolated (есть hook + visual + promise)
- [ ] Areas of interest распределены по всем slides (не только slide 1 и N)
- [ ] Важные детали (лица / numbers / логотипы / key text) НЕ на cut lines (80 px clearance от boundary)
- [ ] Overlap элементы (стрелки / shapes / lines / colors) переходят границы
- [ ] Swipe cue присутствует (стрелка / «→» / pagination «1/N»)
- [ ] Slide order verified до загрузки в IG
- [ ] Если dashboard - raw screenshot, без filter
- [ ] CTA distributed (не только slide N)

Если хоть один пункт fail - вернуться к Pass 2 visual brief в `workflow/03-write.md`.

## Default panorama spec для автора

- Slides: 5
- Canvas: 5400 × 1350 px
- Format: 1080×1350 portrait per-slide
- Aspect: 4:5
- Cut clearance: 80 px от boundary
- Tool default: Photoshop slice tool ИЛИ Open Carrusel (если Claude-driven HTML цепочка)
- Visual style: dark mode preferred, sans-serif Inter / Helvetica 24-32 px min, один accent color (зелёный для $/profit), swipe cue «→» bottom-right slides 1-4