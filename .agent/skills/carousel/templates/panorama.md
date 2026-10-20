# Template: Panorama

**Когда применять:** wow эффект / category reveal / wide composition разрезанный на slides.
**Reference creator:** Casper continuous «ZZZ», Subway daily deals, Starbucks holiday astrology pairing.
**Slide count:** 3-8 (sweet spot 5).

---

## Что это технически

- Canvas width = `N slides × 1080 px` (например 5 slides = 5400 px wide)
- Canvas height = `1350` (4:5 portrait - оптимально для mobile)
- После дизайна canvas разрезается на N equal сегментов по вертикальным гайдам
- Каждый сегмент = отдельный JPG/PNG 1080×1350
- Slides загружаются в IG carousel в правильном порядке

LinkedIn: multi-image native deprecated с late 2023. Только multi-page PDF (каждая страница 1080×1350).

---

## Structure

```
[Slide 1 - Leading Standalone]
Hook word / image + must work isolated (если reader не свайпает - это всё равно стопскролл)

[Slides 2 to N-1 - Middle Continuous]
Wide image continuous портион. Text может быть light (0-10 слов).

[Slide N - Payoff]
Final reveal word + CTA combined (или CTA в caption если payoff чисто визуальный)
```

## Hook formulas (3 варианта)

1. **Word-reveal panorama:** «ВАЙБКОДИНГ» растянутое через 8 slides, payoff = «...больше не profession»
2. **Stack-as-panorama:** Claude + Lovable + Stripe в одной wide composition, per-tool detail per slide
3. **Timeline panorama:** Month 0 → Month 6 → Month 12 continuous revenue chart, milestones per slide

## Real elements requirements (для panorama)

≥40% slides должны содержать:
- Real continuous element (real wide screenshot, real wide product composition)
- Если typography panorama - used real numbers as part of letters/composition
- НЕ generic AI-art landscape без content

**FAIL:** Midjourney generic wide art без content / stock photo wide / blurred gradient

## Pacing (особый для panorama)

- Slide 1: **must work isolated** - hook word или strong image (если reader не свайпает - это стопскролл одиночно)
- Slides 2 to N-1: continuous wide composition + light text per slide
- Slide N: **payoff reveal** - closes the wide composition (must payoff обещание Slide 1)

**Areas of interest distributed:** интересные elements распределены по всей wide composition, не только в одном slide. Каждый slide содержит свой micro-focal-point чтобы держать interest.

**Cut lines clean:** important details (faces, key text, logos) НЕ на cut lines. Канва располагает важное в центре каждого 1080-zone.

---

## Visual style

- **Typography:** если text - крупный, растянутый через slides (большие буквы 200-400pt, разрезанные)
- **Overlap continuity:** shapes / lines / colors переходят через границы. Psychologically тянет swipe
- **Same aspect:** обязательно одинаковый формат для всех slides (1080×1350) - continuous эффект ломается иначе
- **Swipe-left cue:** стрелка/«→» на slide 1 бустит engagement с 1.83% до 2% (research data)

## Tools / workflow

- **Photoshop:** canvas 5400×1350 → guides на каждые 1080 px → Slice Tool → Save for Web (Legacy) → All Slices
- **Canva:** Custom Size + Grid Maker
- **Figma:** plugin Instagram Carousel Creator / IG Multi Image Splitter
- **AI workflow:** Midjourney `--ar 6:1` или `--ar 8:1` → MJ Splitter (mjsplitter.com)
- **Mobile splitters:** splitimage.im / panoslice / post-bridge

## Reference examples

- Casper «ZZZ» continuous (one gigantic Z across all slides - sleep product)
- Subway daily deals horizontal (sub-sandwich через slides по дням недели)
- Starbucks Holiday Astrology pairing (continuous illustration + food pairs)
- Bucket D research: `~/.business/growth/carousel-research/2026-05-28/bucket-d-panorama-and-dense.md`

## Что переносимо для автора

- **Stack-as-Panorama signature** - Claude + Lovable + higgsfield + Stripe в одной wide composition (visualizing stack как hero asset)
- **Word-reveal**: «ВАЙБКОДИНГ» растянутый через 8 slides с payoff «больше не profession»
- **Revenue timeline panorama** - Month 0 → Month 12 continuous chart с milestones (есть Stripe MRR data у автора)

## Banned для panorama

- Different aspect ratios между slides - auto-fail (ломает continuous эффект)
- Important details (faces / key text / logos) на cut lines - fail
- Panorama без isolated value на slide 1 (если reader не свайпает - wasted slide) - fail
- Slides > 8 - drop-off rate uneconomic для panorama (research data)
- Fake/cropped визуал dashboards as panorama - репутационный риск