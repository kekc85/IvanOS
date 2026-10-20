# Template: Reel-to-Carousel

**Когда применять:** перепаковка viral Reel в static carousel для cross-platform distribution или same-platform evergreen.
**Reference creator:** Justin Welsh repurposing (newsletter → thread → carousel), Lara Acosta multi-format.
**Slide count:** зависит от длины Reel (см. таблицу ниже).

---

## Inheritance from card.md

Этот template inherits structure из `brief.beats[]` (1 beat = 1 slide), НЕ переписывает.

Workflow:
1. Read `brief.card_md_path` (от `ingest-reel`)
2. Extract beats / frames / UI inventory
3. Map beats → slides (см. ниже)
4. Apply loss compensation (см. ниже)

---

## Slide count по длине Reel

| Reel length | Slide count target | Reasoning |
|---|---|---|
| 15s | 6-8 | 1 beat ≈ 1.5-2 сек видео |
| 30s | 8-10 | sweet spot для repurpose |
| 60s | 10-12 | full storytelling arc |

Если beats > target → cluster соседних beats в один slide.
Если beats < target → split один beat на под-beats.

---

## Structure (5-beat arc)

```
[Slide 1 - Hook frame]
Berbatim opening from Reel + visual: либо reveal frame, либо motion-triple grid (Welsh trick)

[Slide 2 - Context]
Setup / why this matters (transcript beat 2)

[Slides 3 to N-3 - Discovery / Steps]
1 beat = 1 slide. Каждый beat → standalone slide

[Slides N-2 to N-1 - Reward / Insight]
Payoff / result / number (если есть в Reel)

[Slide N - CTA]
Verbal CTA из Reel → static button-style CTA
```

---

## Hook slide pattern (verbal hook → static)

4 patterns:

1. **Question hook:** verbal вопрос → крупный bold typo на чистом фоне («Что если LinkedIn ER зависит от 1 переменной?»)
2. **Stat hook:** цифра-bomber из видео → один крупный number на slide
3. **Before/After hook:** split-screen (left = старое, right = новое)
4. **Motion-triple grid (Welsh):** 3 frames «start/middle/end» автора в grid + «Play» icon overlay + headline. Намекает на видео-источник, создаёт curiosity

---

## Frame extraction priority

Для каждого slide выбрать hero frame по приоритету:

1. **Reveal frames** - final UI / dashboard / before-after (HIGHEST)
2. **Motion-triple** (для hook slide) - 3 frames horizontal
3. **UI screenshots** - pure UI + аннотация (стрелка / обводка / callout)
4. **Face frame** - если автор эмоция / pointing gesture
5. **Typography-only** - если frame слабый, заменить чистой типографикой

**Quality gate:** все extracted frames в полном разрешении. Hero frame занимает 60-70% площади slide, оставшиеся 30-40% - typography overlay.

---

## Loss compensation matrix

Что теряется в Reel → как компенсировать в carousel:

| Loss | Compensation |
|---|---|
| Movement (cuts, zoom) | Bold typography weight contrast, 80-120pt на hook |
| Voice tone / emotion | ALL CAPS для emphasis, italics для интонации, color на key слова |
| Music / beat / rhythm | Visual rhythm через repeating template grid |
| Sound effects | Layered visuals - frame + sticker + arrow + highlight |
| Real-time pacing | Slide numbers ("3/9"), progress dots |
| Face-cam authority | 1-2 slides с фото автора + signature «- автор» |

---

## CTA conversion (verbal → static)

| Verbal in Reel | Static CTA slide |
|---|---|
| «подпишись на канал» | "Follow <твой-хэндл> - больше каруселей про X" |
| «link in bio» | "Полный гайд - link in bio" + visible button |
| «сохрани этот пост» | "Save this carousel + DM 'X' for the prompt" |
| «комментируй ниже» | "Comment '<keyword>' → DM лидмагнит" |

CTA должен быть **action-specific** под жанр:
- Educational / framework → ask SAVE
- Контроверсия → ask COMMENT
- Diagnostic / problem → ask CLICK / DM
- Funnel slide → ask FOLLOW

Carousels с явным CTA slide делают +20-30% ER vs без.

---

## Visual style

- **Inherit Reel визуальный стиль** (если автор имеет brand consistency)
- **Hero frame** на slide 1 - full bleed или с typography overlay
- **Typography** растёт от hook (largest) → middle (medium) → CTA (medium-large)
- **Color accent** - авторский brand color применить на key words

## Reference examples

- Justin Welsh canonical: newsletter → Twitter thread → LinkedIn PDF carousel (один source, три format)
- Lara Acosta multi-format consistency
- Bucket E research: `~/.business/growth/carousel-research/2026-05-28/bucket-e-reel-to-carousel.md`

## Что переносимо для автора

- Riley Brown 60s Reel «6 vibe coding tools simultaneously» → 10-slide carousel listicle (одинаковый content, 2 formata)
- автор's face-cam vibemarketing Reels → typography-led carousels с face frame 1-2 slides
- Длинные надиктовки автора → могут стать сначала Reel (`/video`) → потом carousel через этот mode

## Banned для reel-to-carousel

- Скриншоты прямо из видео без переосмысления (это не reel-to-carousel, это screenshot dump) - fail
- Hook slide = frame 0:00 как есть (часто frame 0:00 = setup, не hook) - fail
- Filler «значит», «вот», «вообще» оставлены в slide text - fail
- CTA дословно verbal без переосмысления («подпишись» как есть) - fail