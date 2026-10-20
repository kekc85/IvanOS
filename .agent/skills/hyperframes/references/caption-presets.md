# Caption presets (named styles, copy-paste ready)

5 готовых caption presets для HyperFrames. Замещают Submagic dependency своими блоками — стилистическая полировка через GSAP + CSS, не через внешний API.

Использовать как стартовую точку, потом твикать под brand и beat tempo. Все presets seek-safe (HyperFrames-deterministic).

---

## 1. Hormozi block (emphasis-stack)

**Когда:** sales / pitch / hype tone. Volume creator default. Bold каждое 2-3 слово, key слова pop scale.

**Visual:** uppercase white text, black stroke 4px, yellow emphasis on 1-2 words per group. Drop-shadow glow.

```css
.cap-hormozi {
  font-family: 'Inter Variable', system-ui, sans-serif;
  font-weight: 900;
  font-size: clamp(56px, 7vw, 96px);
  text-transform: uppercase;
  letter-spacing: -0.02em;
  line-height: 1.0;
  color: #ffffff;
  -webkit-text-stroke: 4px #000;
  text-shadow:
    0 0 24px rgba(0,0,0,0.6),
    0 4px 12px rgba(0,0,0,0.4);
  text-align: center;
  position: absolute;
  bottom: 22%;
  left: 5%;
  right: 5%;
}
.cap-hormozi .accent {
  color: #FFEB3B;
  -webkit-text-stroke: 4px #000;
}
```

```js
// GSAP per-group pop-in
gsap.from('.cap-hormozi .word', {
  scale: 0.6, opacity: 0, duration: 0.18,
  ease: 'back.out(1.8)', stagger: 0.04
});
gsap.from('.cap-hormozi .accent', {
  scale: 1.4, color: '#fff',
  duration: 0.22, ease: 'expo.out', delay: 0.08
});
```

---

## 2. MrBeast pop (kinetic burst)

**Когда:** entertainment / explainer / wide-audience hype.

**Visual:** uppercase, multi-color rotation per group, oversized scale-pop, white glow drop-shadow. Animated emoji decorations OK.

```css
.cap-mrbeast {
  font-family: 'Komika Title', 'Impact', sans-serif;
  font-weight: 900;
  font-size: clamp(64px, 8vw, 112px);
  text-transform: uppercase;
  letter-spacing: 0.01em;
  line-height: 0.95;
  color: #ffffff;
  text-shadow:
    0 0 14px rgba(255,255,255,0.6),
    0 6px 0 rgba(0,0,0,0.85),
    0 8px 24px rgba(0,0,0,0.55);
  text-align: center;
  position: absolute;
  bottom: 22%;
  left: 0; right: 0;
}
.cap-mrbeast .word:nth-child(3n+1) { color: #FF3D71; }
.cap-mrbeast .word:nth-child(3n+2) { color: #FFEB3B; }
.cap-mrbeast .word:nth-child(3n)   { color: #2EE6A8; }
```

```js
gsap.from('.cap-mrbeast .word', {
  scale: 0.3, rotation: -8, opacity: 0,
  duration: 0.28, ease: 'elastic.out(1, 0.55)',
  stagger: 0.06
});
```

---

## 3. Soft serif (storytelling)

**Когда:** narrative / personal / longer beats / cinematic register.

**Visual:** lowercase or sentence case, light serif, white with subtle warm tint, no stroke, gentle fade-in. Restrained scale.

```css
.cap-serif {
  font-family: 'Cormorant Garamond', 'Georgia', serif;
  font-weight: 400;
  font-style: italic;
  font-size: clamp(40px, 5vw, 64px);
  letter-spacing: 0;
  line-height: 1.2;
  color: #fef9ed;
  text-shadow: 0 2px 18px rgba(0,0,0,0.6);
  text-align: center;
  position: absolute;
  bottom: 18%;
  left: 8%; right: 8%;
}
```

```js
gsap.from('.cap-serif', {
  opacity: 0, y: 14,
  duration: 0.55, ease: 'power2.out'
});
```

---

## 4. Minimal subtitle (clean / corporate)

**Когда:** tutorial / SaaS demo / corporate explainer. Maximum readability, zero personality.

**Visual:** clean sans, single color, single line, no stroke, subtle drop-shadow. No emoji, no color accents.

```css
.cap-minimal {
  font-family: 'Inter Variable', -apple-system, sans-serif;
  font-weight: 600;
  font-size: clamp(36px, 4.5vw, 56px);
  letter-spacing: -0.005em;
  line-height: 1.15;
  color: #ffffff;
  text-shadow: 0 2px 10px rgba(0,0,0,0.7);
  text-align: center;
  position: absolute;
  bottom: 14%;
  left: 10%; right: 10%;
  max-width: 80%;
  margin: 0 auto;
}
```

```js
gsap.from('.cap-minimal', {
  opacity: 0,
  duration: 0.3, ease: 'power1.out'
});
```

---

## 5. Kinetic emphasis (per-word reveal w/ marker)

**Когда:** technical / how-to / step-by-step. Key terms get marker sweep underline.

**Visual:** sentence case, medium sans, white, dynamic per-word reveal, marker-style underline on highlighted terms (yellow brush stroke effect via SVG mask).

```css
.cap-kinetic {
  font-family: 'JetBrains Sans', 'Inter', sans-serif;
  font-weight: 700;
  font-size: clamp(46px, 5.5vw, 76px);
  letter-spacing: -0.01em;
  line-height: 1.05;
  color: #ffffff;
  text-shadow: 0 3px 14px rgba(0,0,0,0.55);
  text-align: center;
  position: absolute;
  bottom: 24%;
  left: 6%; right: 6%;
}
.cap-kinetic .marker {
  position: relative;
  display: inline-block;
}
.cap-kinetic .marker::after {
  content: '';
  position: absolute;
  left: -4px; right: -4px;
  bottom: 4%;
  height: 24%;
  background: linear-gradient(90deg, rgba(255,235,59,0.85), rgba(255,193,7,0.85));
  z-index: -1;
  transform: scaleX(0);
  transform-origin: left center;
  border-radius: 3px;
}
```

```js
gsap.from('.cap-kinetic .word', {
  y: 18, opacity: 0,
  duration: 0.22, ease: 'power3.out',
  stagger: 0.05
});
gsap.to('.cap-kinetic .marker::after', {
  scaleX: 1,
  duration: 0.45, ease: 'power2.inOut',
  delay: 0.2
});
// CSS pseudo-elements can't be animated by GSAP directly — use a real <span class="marker-sweep">
// or animate a CSS variable via --marker-sweep: 0; и target ::after with var(). Real impl uses a real span.
```

---

## How to pick

| Tone of beat | Preset |
|---|---|
| sales pitch, hook, urgency | Hormozi block |
| entertainment, wide audience | MrBeast pop |
| personal story, cinematic | Soft serif |
| corporate demo, SaaS, tutorial | Minimal subtitle |
| step-by-step, technical, "вот это важно" | Kinetic emphasis |

## Cross-preset rules

- **Position:** caption block НЕ перекрывает лицо speaker. Vertical 9:16 = bottom 14-24% center
- **Stroke:** только Hormozi и MrBeast используют thick stroke. Остальные = drop-shadow only
- **Per-word грану:** Hormozi и Kinetic делают per-word reveal. MrBeast - per-word pop. Serif и Minimal - per-group fade
- **Тайминги:** все 0.18-0.55s per element. Никогда не дольше — caption должен appear, не animate

## Integration с replicate-reel

В `spec.brand.caption_style` указывать один из:
```json
{
  "brand": {
    "watermark_text": "<твой-хэндл>",
    "caption_style": "hormozi" | "mrbeast" | "serif" | "minimal" | "kinetic",
    "caption_color": "#FFFFFF",
    "caption_stroke_color": "#000000"
  }
}
```

Затем в Remotion / HyperFrames render слой подхватывает соответствующий CSS+JS из этого preset library.

---

## Anti-patterns

- ❌ Не смешивать 2 preset в одной композиции (визуальный диссонанс)
- ❌ Не использовать MrBeast pop для corporate SaaS demo (clash with brand voice)
- ❌ Не использовать Soft serif для hype beats (visual mismatch)
- ❌ Не делать font-size >120px в vertical 9:16 (нечитаемо при scaling в feed)
- ❌ Не использовать em-dash «—» внутри captions text (рендерится плохо на mobile, лучше «-» или запятая)