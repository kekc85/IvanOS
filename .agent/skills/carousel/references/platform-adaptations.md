# platform-adaptations

> Per-platform specs (IG / LinkedIn / Threads / TG), cross-distribution rules, decision-таблица «что меняется при переносе carousel между платформами». Загружается в `workflow/01-finalize.md` и `workflow/05-publish.md`. Источник - `.business/growth/carousel-research/2026-05-28/bucket-a-en-ai-vibemarketing.md` + `bucket-b-en-linkedin-masters.md`.

## Instagram carousel specs

```yaml
instagram:
  aspect_ratio: "1080x1350"           # 4:5 portrait, mobile-optimized
  slide_count_optimal: [8, 10]
  slide_count_max: 10
  file_format: ["jpg", "png"]
  caption_max: 2200                   # знаков
  caption_fold_chars: 125             # до "...more" cutoff
  hashtags_optimal: [3, 5]
  hashtags_max: 30
  cta_style: "comment_keyword → DM"
  algorithm_primary_signal_2026: ["saves", "shares"]
```

**Mobile-first рендер.** Аудитория почти 100% mobile - typography 24 pt floor, headlines 60 pt+, контраст ≥7:1. Visual-первичный формат - illustration / screenshot > text density.

**Caption механика:**

- Первые 125 знаков = «...more» fold. Это hook-battlefield.
- 2200 знаков total max
- Hashtags 3-5 оптимально (>10 = spam signal). Можно складывать в первый комментарий вместо caption.
- CTA = comment-trigger DM (Sabrina Ramonov mechanic) или save / share.

**Slide-count свыше 10** - IG режет, не отображает. Stick to 10 max. Для большего контента - split на 2 carousels.

## LinkedIn document specs

```yaml
linkedin:
  aspect_ratio: "1080x1350"
  slide_count_optimal: [8, 12]        # 7 даёт +18% per usevisuals 2026
  slide_count_max: 20                 # технический max 300, но drop-off после 13
  file_format: ["pdf"]                # native multi-image deprecated late 2023
  pdf_max_pages: 300
  pdf_max_size_mb: 300
  caption_max: 3000
  caption_fold_chars: 210             # до "see more" cutoff
  hashtags_optimal: [0, 2]            # 2026 deprioritizes hashtags
  cta_style: "newsletter_subscribe | comment_keyword | save"
  algorithm_primary_signal_2026: ["comments", "saves"]
  padding_px: 80                      # safe area от LinkedIn UI overlap
  safe_zone_px: "880x880 центр"
  font_min_pt: 24
  font_headline_pt: 60                # 60+ обязательно
  font_body_pt: 36                    # 36-40 body
```

**Desktop + mobile dual-аудитория.** ~60% LinkedIn консьюмеров на desktop в B2B сегменте - typography может быть более text-dense чем IG. Sans-serif обязательно (Inter / Roboto / Helvetica Neue).

**PDF механика:**

- LinkedIn рендерит PDF как swipeable images клиент-сайд
- Resolution на mobile ~360-450 px width, на desktop ~552 px
- RGB / 72 DPI
- Padding 80 px все стороны - иначе LinkedIn UI режет края
- Central safe zone 880×880 - туда важные элементы

**Caption механика:**

- Первые 210 знаков = «see more» fold. Hook battlefield.
- 3000 знаков total
- Hashtags 0-2 в 2026 (LI deprioritized их). 0 = OK у Welsh, 1-2 у Acosta.
- CTA primary = newsletter subscribe (Welsh / Acosta / Dimond) или comment-bait (Sabrina mechanic перенос).

**Slide-count свыше 12** - вовлечённость падает. Sweet spot 7-12. Justin Welsh использует 10. Sahil Bloom использует 8.

## Threads cross-distribution

```yaml
threads:
  format: "text + 1-3 image preview"
  caption_max: 500
  carousel_native: false              # нет multi-image swipe
  use_case: "teaser carousel"
```

**Механика:** Threads не поддерживает swipeable carousel. Для cross-distribution из IG carousel - публикуем caption + 1-2 slide-превью (hook slide + один payoff slide) как teaser с ссылкой на полную IG версию.

## Telegram bridge mode

```yaml
telegram:
  format_options:
    - "native_album"                  # 2-10 media в одном posting
    - "hero_plus_narrative"           # 1 hero image + full text narrative
  album_max: 10
  caption_max_per_message: 4096
```

**2 варианта моста carousel → TG:**

1. **Native album** - все slides загружены как media group в одном сообщении. Подходит когда slides самодостаточны и работают как deck.

2. **Hero + narrative** - 1 hero image (объединённая wide composition или slide 1) + полный narrative text (можно длинный, до 4096 знаков). Подходит когда carousel-структура не работает в TG UX и нужна editorial адаптация.

Решение какой вариант - по типу carousel в `workflow/05-publish.md`.

## Cross-platform decision table

| Параметр | IG | LinkedIn | Что меняется при переносе |
|---|---|---|---|
| Slide count | 8-10 optimal | 7-12 optimal | LI чаще больше слайдов (text-dense), IG короче |
| Aspect ratio | 1080×1350 | 1080×1350 PDF | Одинаковый - source file универсален |
| File format | JPG/PNG | PDF multi-page | Экспортнуть из source в оба формата |
| Typography size | 36-60 pt | 60 pt headline / 36-40 pt body | LI обязательно крупнее body text (desktop-readable) |
| Padding | 40-60 px | 80 px | LI требует больше padding |
| Caption length | 2200 max / 125 fold | 3000 max / 210 fold | Caption переписать под cutoff каждой платформы |
| Hashtags | 3-5 | 0-2 | Drop hashtags для LI |
| CTA primary | Comment-trigger DM / save | Newsletter subscribe / comment / save | LI = newsletter / comment, IG = DM / save |
| Selfie placement | Иногда (1 slide) | Часто (1-2 slides, bottom-right) | Lara Acosta pattern - LI любит селфи как trust signal |
| Numbered structure | Опционально | Обязательно (01, 02, 03) | LI ожидает structured listicle |
| Author name в hook | Реже | Чаще («N tips by автор») | Jasmin Alić own-name signature |
| Brand color | Один accent | Один accent consistent | Одинаково |

**Универсальный source-file принцип:** дизайнить в 1080×1350, source content делать platform-agnostic. Адаптации - только в caption + минимально в font sizes (LI крупнее).

## POSSE distribution model

Publish on Own Site, Syndicate Everywhere. Применение для carousel:

1. **Primary platform first.** Выбрать одну primary platform по типу carousel:
   - Методологический разбор (`family=framework-breakdown`) / numbered guide → LinkedIn primary (text-driven читатель)
   - Tool roundup / listicle → IG primary (visual-first)
   - Story-case с personal numbers → дублировать (LI text-strong, IG visual-strong)
   - Panorama → IG primary (LinkedIn PDF теряет seamless эффект между страницами)
   - Reel-to-carousel → IG primary (контекст из reel-источника)

2. **Derivatives map:**

   | Primary | Secondary | Tertiary |
   |---|---|---|
   | LinkedIn PDF | IG carousel | Threads teaser + TG hero+narrative |
   | IG carousel | LinkedIn PDF | Threads teaser + TG album |
   | IG panorama | TG album | (LI - не подходит, panorama теряется в PDF) |

3. **Delay schedule:** primary post → wait 24-48 часов → syndicate на secondary. Алгоритмы не наказывают за cross-posting если caption переписан.

## Typography per platform

### Instagram (visual-led)

- Headlines 60-80 pt максимум - place в первой трети slide
- Body 36-40 pt
- Sans-serif обязательно (Inter / Helvetica / Roboto)
- Один accent color, остальное мономонохром
- Max 25 слов per slide value, 15 per hook, 15 per CTA
- Visual element ≥50% slide area

### LinkedIn (text-driven primary)

- Headlines 60 pt+ обязательно (desktop-readable)
- Body 36-40 pt, никогда <24 pt
- Sans-serif (Inter / Roboto / Helvetica Neue)
- Numbered structure обязательно (01, 02, 03 в углу)
- 30-50 слов per slide (text-dense OK)
- Графика secondary, текст primary
- Brand color accent + selfie corner

## Color / contrast per platform

### Instagram

- High contrast обязательно (mobile-first, sun-glare conditions)
- Dark mode dominant (82% mobile users prefer 2025)
- Один accent color (зелёный для $/profit, красный для loss/warning, синий для neutral)
- Avoid soft pastels на больших площадях - читается как «templated AI carousel»

### LinkedIn

- Readable на desktop + mobile - contrast ratio ≥7:1
- White / off-white background dominant (Welsh signature)
- Brand accent (Acosta red / Welsh orange) consistent across all carousels
- Dark mode possible (Matt Gray pattern), но reduces text readability в B2B сегменте

## Algorithm signals 2026

### Instagram

- **Saves > likes** в 2026 (саге weighted 3× выше likes)
- Shares примерно равны saves
- Comments весомы но меньше чем saves
- Carousel получает 1.9× больше reach + до 3× вовлечённости vs single image
- Hybrid Carousel Reels (новый формат 2026) - 12% ER vs 6% обычных Reels

### LinkedIn

- **Comments > follows** primary signal 2026
- Saves второстепенны но растут
- Carousel = 3.7× вовлечённость vs text, 1.8× vs single image (Buffer + Socialinsider benchmark)
- Hashtags deprioritized
- Comment-bait CTA («Comment "guide" - DM тебе шаблон») работает лучше всего

## Cross-distribution adaptation rules

При переносе carousel IG → LinkedIn:

1. **Caption rewrite.** IG caption (125 fold) переписать в LinkedIn caption (210 fold). Разные hook battlefield, разная аудитория тон. Использовать chain `multi-language-localization` если нужна культурная адаптация.

2. **Slide count adjust.** Если IG carousel 8 slides - LinkedIn оставить 8 (универсально работает). Если IG 10 - LinkedIn может расширить до 12 (текстовая плотность LI допускает).

3. **Numbering added.** Если IG slides без явной нумерации (01, 02, 03) - на LinkedIn добавить.

4. **Selfie slide added.** Если на IG нет личного фото - добавить 1-2 slides с автором на LinkedIn (Acosta / Bloom pattern - повышает trust в B2B).

5. **CTA conversion.** IG «Comment "X" - DM ссылку» → LinkedIn «Newsletter Saturday Solopreneur - link in comments / bio» ИЛИ comment-bait перенесён 1:1.

6. **Hashtags strip.** IG hashtags (3-5) → LinkedIn 0-2 max. Лучше 0.

7. **Typography sizing.** Если на IG headlines 60 pt - на LinkedIn оставить 60 pt+. Если IG body 36 pt - проверить читаемость на mobile + desktop LI.

При переносе carousel LinkedIn → IG:

1. **Slide count tighten** если LI 12 - на IG урезать до 10.
2. **Visual element увеличить** - LinkedIn text-dense, IG требует ≥50% area visual.
3. **Caption shorten** - 3000 → 2200 max, fold 210 → 125.
4. **Hashtags add** - LI 0-2 → IG 3-5.
5. **CTA conversion** - newsletter signup → comment-trigger DM.

## Per-platform default settings (для `workflow/05-publish.md`)

```yaml
defaults:
  if_platform_only_instagram:
    slide_count: 8
    caption_length_target: 200            # well under 2200
    hashtags: 4
    cta_pattern: "comment_keyword_dm"
    
  if_platform_only_linkedin:
    slide_count: 10
    caption_length_target: 400            # under 3000, hook within 210
    hashtags: 1                            # или 0
    cta_pattern: "newsletter_subscribe"
    numbered_slides: true
    selfie_slides: [1, 8]                  # slide 1 + предпоследний
    
  if_platform_both:
    primary: "linkedin"                   # для family=framework-breakdown
    secondary: "instagram"
    source_design: "1080x1350 universal"
    caption_rewritten_per_platform: true
    delay_hours: 24                       # primary first, then secondary
```

## Pre-publish platform checklist

Перед output карусели проверить per platform:

### IG

- [ ] Slide count ≤10
- [ ] Каждый slide 1080×1350 JPG / PNG
- [ ] Hook slide stops scroll - bold headline + visual ≥50%
- [ ] Caption ≤2200 знаков, hook первые 125
- [ ] Hashtags 3-5
- [ ] CTA = comment-trigger или save / share

### LinkedIn

- [ ] PDF multi-page export, ≤20 страниц
- [ ] Каждая страница 1080×1350, RGB, 72 DPI
- [ ] Padding 80 px со всех сторон
- [ ] Font ≥24 pt absolute, headlines 60 pt+
- [ ] Sans-serif (Inter / Roboto / Helvetica Neue)
- [ ] Caption ≤3000 знаков, hook первые 210
- [ ] Hashtags 0-2
- [ ] CTA = newsletter / comment-bait / save
- [ ] Numbered structure (01, 02, 03) присутствует
- [ ] 1-2 selfie slides (если личный бренд carousel)

### Threads

- [ ] Caption ≤500 знаков
- [ ] 1-2 slide-превью (hook + один payoff)
- [ ] Ссылка на полную IG версию

### Telegram

- [ ] Native album если ≤10 slides и slides самодостаточны
- [ ] Hero + narrative если carousel-структура не работает в TG UX
- [ ] Caption ≤4096 знаков
- [ ] Кнопки CTA если применимо

Если хоть один пункт fail для целевой платформы - вернуться к `workflow/03-write.md` или `workflow/04-review.md`.