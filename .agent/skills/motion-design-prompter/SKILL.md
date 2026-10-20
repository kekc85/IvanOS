---
name: motion-design-prompter
description: Generate a complete Higgsfield Supercomputer animation prompt from any static design image. Use this skill whenever someone uploads a design, poster, graphic, or visual and wants it animated — even if they just say "animate this", "write the prompt for this", "motion graphic prompt", "make this move", or drops an image with no explanation. This skill applies a professional motion design system (ease in/out, physics-based entrances, layered stagger, living zoom, sound design) to every element in the design. Always trigger this when a static visual needs to become a motion brief. Never guess or improvise the animation rules — always follow this skill's system exactly.
---

# Motion Design Prompter

Generates a complete, production-ready Higgsfield Supercomputer animation prompt from any static design image. Applies a professional motion design system consistently across all element types.

---

## Контекст: роль в конвейере автора (replicate-viral)

Этот скилл - инструмент **зелёной зоны Higgsfield** в `replicate-viral`. Креатив-директор (Фаза 2c) расставляет вставки в раскадровке и решает движок по природе данных:

- **Higgsfield Infographic Animator + этот скилл** - абстрактный смысл без точных данных: деньги/рост/метрики/концепт-метафоры, стат-ревилы и титры-заставки как графика, мотион-переходы и стингеры между сегментами
- **HyperFrames (детерминированно)** - точная дата-виз с цифрами/логотипами/привязкой к реальному UI (счётчик установок инструмента, бренд-SVG, печать кода) и весь несущий спайн (сплит, субтитры, аватар-композит). Генеративка цифры и логотипы исказит
- **Реальный инструмент/репо/интерфейс** - НИКОГДА не этот скилл, только захват браузером (закон `feedback_reel_inserts_real_captures_never_drawn`). Этот скилл оживляет ДИЗАЙН, а не воспроизводит настоящий продукт

**🔴 ГИБРИД ДЛЯ ТЕКСТА (предохранитель, пока не пройден боевой тест Infographic Animator).** Если на инфографике есть числа/подписи, несущие смысл - текст накладывается ОВЕРЛЕЕМ кодом (HTML → PNG) поверх Higgsfield-фона, генеративке текст-носитель не отдаём (риск поплывших букв). Перед первым продакшен-использованием прогнать тест-клип и проверить, держит ли инструмент подписи.

**Формат текста автора (если в дизайне есть RU-текст):** без длинных тире (только обычный дефис), без точки в конце абзаца, без нейроклише.

---

## Step 1 — Analyze the Design

Before writing a single line of the prompt, identify and classify every visible element in the image into one of four tiers:

### Tier 1 — HERO OBJECT
The dominant 3D or photorealistic physical element. One per design usually.
Examples: coin, hourglass, dart, chain, book, phone, product, statue, weapon, vehicle.
→ Gets full physics entrance (directional travel + rotation + opacity)

### Tier 2 — HERO TEXT
The largest, most prominent text. Usually 1–3 lines. The headline.
Examples: "SCALE", "Don't Change your Business", "OVER $20,000", "HAPPY EASTER"
→ Gets Y-offset slide entrance + opacity

### Tier 3 — BODY / SECONDARY TEXT
Smaller supporting copy, subtitles, Bible verses, body paragraphs, captions, labels.
→ Gets typewriter effect

### Tier 4 — BACKGROUND / DECORATIVE
Ghost text, grid textures, question marks, repeated symbols, subtle overlays, corner elements, small icons, barcodes.
→ Gets subtle drift settle (±20–50px) + opacity fade. Never flies in from off-screen.

### Lines / Strokes (any tier)
Thin decorative lines, arcs, curves, geometric shapes, trim paths, calligraphic strokes.
→ Always gets trim path draw-on effect (0% → 100%)

---

## Step 2 — Apply the Animation System

These rules are non-negotiable and apply to every prompt written with this skill.

### RULE 1 — Zoom Out (Full Video, Always Breathing)
The composition never stops moving. The zoom out is alive for the entire duration.

```
Start: scale(1.2) + Gaussian blur 30
First 10–20 frames at 60fps: fast ease to scale(1.04–1.05) — this covers 60–80% of the total reduction
Gaussian blur: 30 → 0 in the same first 10–20 frames only
Rest of video: slow continuous ease from ~1.04 → 1.0 across the full remaining duration
Result: the composition always has a slow living breath — never fully static
```

### RULE 2 — Every Element Has Motion
No layer is ever static. Every element in the design must have at least one animation property. Background elements are NOT exempt — they get the drift treatment.

### RULE 3 — HERO OBJECT Entrance (Physics-Based)
The hero object enters from its natural directional side with rotation physics.

```
- Starts off or near its edge (not necessarily fully off-screen)
- Carries a rotation keyframe during travel: typically ±12° to ±18°
- As it arrives at its final position, rotation eases to 0° (or its final design resting angle)
- Position and rotation correction settle on the SAME keyframe
- Opacity: 0 → 100 during travel
- Ease in + ease out on position AND rotation
```

Direction logic by object type:
- Coins, discs, flat objects → from left or right
- Darts, arrows, projectiles → from the direction they're pointing, angled trajectory
- Frames, paintings, panels → from below or slight diagonal, subtle rotation
- Chains, ropes, long objects → from the side they extend toward, with rotation matching diagonal angle
- Papers, documents, cards → from the direction they're tilted toward, rotation settles to design tilt

### RULE 4 — HERO TEXT Entrance
Each line slides down from 200px above its final Y position with opacity 0 → 100.

```
- translateY(-200px) → translateY(0)
- Opacity 0 → 100
- Ease in + ease out
- Stagger: each line enters after the previous one lands (do not cascade all at once)
```

### RULE 5 — BACKGROUND Elements (Drift Only)
These are already roughly in position. They do NOT fly in from off-screen.

```
- Drift ±20–50px from a nearby offset into their final position
- Opacity 0 → final design value (often low, e.g. 30–60%)
- Ease in + ease out
- Triggers early, parallel with the scene zoom open
```

### RULE 6 — Lines and Strokes (Trim Path)
Every thin line, arc, curve, or calligraphic stroke draws itself on.

```
- Stroke-dashoffset / trim path: 0% → 100%
- Start from the beginning of the animation
- Ease in + ease out
- Duration: slow and cinematic (1.5–2.5 seconds is typical)
```

### RULE 7 — Body Text (Typewriter)
Small secondary copy appears character by character, triggered after the headline lands.

### RULE 8 — Speed and Curves
Everything ease in + ease out. Slow and cinematic. No linear timing. No snappy motion. The whole animation breathes.

### RULE 9 — Frame Rate
Always 60fps.

### RULE 10 — Sound Design
Always included. Match sound character to the design's visual mood:

| Design Mood | Music Bed | SFX Character |
|---|---|---|
| Dark / edgy (black bg, neon) | Electronic, industrial, bass | Digital whoosh, impact, power hum |
| Clean / minimal (white/light bg) | Minimal, ambient, light | Air swish, clean clink, soft keys |
| Financial / luxury (gold, money) | Cinematic, confident | Metallic clink, paper rustle, cash register |
| Spiritual / emotional | Orchestral, choir swell | Soft bell, ambient pad, gentle whoosh |
| Energetic / motivational | Upbeat, punchy | Sharp impact, fast swish, hit sounds |

Always include:
- One sound per hero object entrance (whoosh + impact/settle)
- One sound per hero text line (soft air swish)
- Typewriter key sounds for body text
- Ambient music bed appropriate to mood
- Any special sounds the element demands (chain clink, dart thud, coin spin, paper shuffle)

---

## Step 3 — Write the Prompt

Use this exact structure:

```
[Opening context: brief design description + output request]

GLOBAL:
- 60fps, ease in + ease out on all animations, slow and cinematic

SCENE OPEN — Zoom Out (alive for full video):
[Full zoom + blur spec following Rule 1]

[BACKGROUND ELEMENTS section]
[DECORATIVE LINES section]
[HERO OBJECT section]
[HERO TEXT lines, each staggered]
[SECONDARY TEXT blocks]
[BODY TEXT / typewriter section]
[ACCENT / small elements section]

SOUND:
[Detailed sound brief following Rule 10]

OUTPUT: 9:16 vertical, 60fps, cinematic quality.
```

---

## Step 4 — Quality Check Before Outputting

Before finalizing the prompt, verify:

- [ ] Zoom rule includes both the fast initial pop AND the slow full-video continuation
- [ ] Every element in the design has been addressed — nothing omitted
- [ ] Hero object has rotation keyframe specified (angle in, angle out)
- [ ] All lines/strokes have trim path
- [ ] Background elements say "drift ±Xpx" not "enter from off-screen"
- [ ] All text tiers are correctly classified (slide vs typewriter)
- [ ] Sound section covers every major entrance + music bed
- [ ] Output spec is at the end

---

## Quick Reference Card

```
ELEMENT TYPE          ANIMATION TREATMENT
─────────────────────────────────────────────────────
Hero 3D object        Direction + rotation (±12–18°) → 0° at landing + opacity
Hero text lines       translateY(-200px) → 0 + opacity, stagger per line
Background/ghost      ±20–50px drift settle + opacity (no off-screen)
Decorative lines      Trim path 0% → 100%
Body/secondary text   Typewriter character by character
Small accents         ±20–30px drift + opacity, subtle only

SCENE OPEN (always)
  Scale 1.2 → 1.04 fast (frames 0–20) + blur 30→0
  Scale 1.04 → 1.0 slowly across full remaining video
  [Composition always breathing, never static]

SPEED: Ease in + ease out. Everything. No exceptions.
FPS: 60fps always.
SOUND: Always. SFX per element + ambient music bed.
```
