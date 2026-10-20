# Visual Anchors Manifest

**Created:** 2026-05-28 evening (after carousel v1.1 disaster + skill-craft v1.3 audit)
**Purpose:** Visual ground truth для template design + L8 visual quality gate
**Status:** INCOMPLETE - anchor image files отсутствуют, только text descriptions

---

## Recovery action required

User дал 3 reference screenshots в чате 2026-05-28 (первое сообщение). Они НЕ сохранены как files - root cause VG-A violation который привёл к carousel v1.1 disaster.

**Options:**
1. User re-share screenshots → save в этой папке
2. User указывает paths к brand library (если есть)
3. Approve WebFetch substitute viral examples (Riley Brown / Sabrina Ramonov / Heather Cooper / Lara Acosta recent posts) как fallback

Без anchor files L8 visual quality gate невозможен → carousel BLOCKED.

---

## Anchor 1: @socialeaver (RU IG carousel hook)

Filename target: `reference-1-socialeaver-RU-carousel.png` (TODO save)
Engagement: 1500 likes / 4160 comments / 1511 saves
Category: IG mobile carousel hook, family ≈ framework-breakdown с panorama vibes

**Copy:**
- Hero image 60-70% area (хамелеон AI-photo high quality, real animal not generic)
- Typography overlay strong-contrast zone (BOLD кириллический «КАК СОЗДАТЬ ТАКУЮ ЖЕ КАРУСЕЛЬ?»)
- Slide counter «1/6» top-right minimal
- Numbered marker «01» top-left с horizontal line
- Sub-headline под main
- CTA button bottom outlined style («Тогда листай далее...» + chevrons)
- Palette: off-white bg + black text + brand-colored CTA

**NOT copy:**
- Specific subject (хамелеон) - нужен авторский hero
- Blue CTA color - Ivan brand red

---

## Anchor 2: @divyannshisharma (EN vintage cinematic stack)

Filename target: `reference-2-divyannshisharma-EN-vibe-stack.png` (TODO save)
Engagement: 4662 likes / 5055 comments
Category: IG single-image post, family ≈ story-case + stack-as-panorama hybrid

**Copy:**
- Cinematic photo background (мужчина за печатной машинкой в поле, sunset golden hour)
- Atmospheric mood - НЕ corporate stock
- Stack overlay top («The Vibe Stack» + 4 product logos = $4,200)
- Serif typography equation huge + IN ONE WEEKEND emphasis
- UGC mockup embedded (Reddit DM screenshot с real story)
- Number-bomber treatment

**NOT copy:**
- Sepia/vintage если не авторский brand
- Reddit-specific UGC → адаптировать на TG DM / Skool

---

## Anchor 3: @aykhanium (EN gritty proof + GitHub)

Filename target: `reference-3-aykhanium-EN-github-proof.png` (TODO save)
Engagement: 8282 likes / 869 comments / 310 saves
Category: IG single-image post, family ≈ proof + listicle

**Copy:**
- Real UGC photo background (gym mirror selfie, gritty real not stock)
- Real screenshot overlay (GitHub contribution graph 1,066 contributions visible)
- Typography overlay bold message
- Real list embedded (TOP 3 USEFUL REPOS с descriptions + tags)
- Dark/moody treatment
- Caption «The last one changed my life» - мощный hook

**NOT copy:**
- Gym setting → Claude Code IDE / Stripe вместо
- Specific repo names → наши skills

---

## Cross-anchor formula (это нужно реплицировать)

1. Hero visual 50-70% area (real photo / cinematic AI / real screenshot)
2. Typography overlay в strong-contrast zone
3. Real proof elements visible (number / logo / screenshot embedded)
4. Brand atmosphere - cinematic / gritty / natural (НЕ sterile template)
5. Multi-layer composition (hero + UI overlay + typography + caption + counter)
6. Bold typography hierarchy (1 huge focal + supporting)

**Anti-pattern:** ни один не использует cream/white bg с pure typography. Это категорически несовместимо. (Точно что я сделал в v1.1 - anti-formula.)

---

## авторские адаптации (TODO design v2.0)

| Anchor element | автор equivalent |
|---|---|
| socialeaver хамелеон photo | AI cinematic автор за Claude Code через higgsfield-generate |
| divyannshisharma typewriter | AI cinematic OR real selfie из brand library |
| aykhanium gym selfie | автор face-cam OR Claude Code IDE screenshot |
| aykhanium GitHub graph | Stripe Skool MRR / skills Finder / motion-storyboard.md |
| divyannshisharma Reddit DM | TG DM real student (anonymized) |
| Bold typography | Inter Bold 60-90pt strong-contrast |

---

## Asset pipeline для hero images

1. AI cinematic photos: chain `higgsfield-generate` (gpt_image_2 / text2image_soul_v2 если Soul ID есть)
2. Real web screenshots: chain `ui-record` (Skool / Stripe / Beehiiv / Kit / TG Web)
3. Real desktop screenshots: manual queue (Claude Code IDE / Cursor / Figma) + AppleScript helper TODO
4. Brand library: existing автор assets в `~/.business/assets/brand-library/` (user collects)

---

## Status: BLOCKED until anchor files saved

skill-craft v1.3 made anchors saving MANDATORY before template design. Carousel v2.0 cannot proceed без visual ground truth files в этой папке.
