# Device-frame-tilt block

3D-perspective device mockup для product launch стиля Reels. Replicate Buck / Linear / Apple launch motion без After Effects + 3D pipeline. Чистый CSS 3D transform + GSAP.

Закрывает gap 12.8 «floating tilted device mockup» в [GAP-ANALYSIS-main.md](../../../../.business/research/motion-ui-insert-gap/GAP-ANALYSIS-main.md).

## HTML

```html
<div class="device-frame device-frame-iphone" data-tilt-x="12" data-tilt-y="-18">
  <div class="device-frame-screen">
    <video autoplay muted loop playsinline data-hf-track="device-frame">
      <source src="ui-recordings/feature-demo.mp4" type="video/mp4">
    </video>
  </div>
  <div class="device-frame-notch"></div>
  <div class="device-frame-reflection"></div>
</div>
```

## CSS

```css
.device-frame {
  --tilt-x: 12deg;
  --tilt-y: -18deg;
  --device-w: 320px;
  --device-h: 660px;
  --device-radius: 42px;
  --device-bezel: 8px;
  position: relative;
  width: var(--device-w);
  height: var(--device-h);
  margin: 0 auto;
  border-radius: var(--device-radius);
  background: linear-gradient(155deg, #1a1a1d, #0d0d10 60%, #1c1c1f);
  box-shadow:
    0 24px 60px -20px rgba(0,0,0,0.55),
    0 8px 20px -8px rgba(0,0,0,0.45),
    inset 0 0 0 1px rgba(255,255,255,0.06);
  transform-style: preserve-3d;
  transform: perspective(1400px) rotateY(var(--tilt-y)) rotateX(var(--tilt-x));
  will-change: transform;
}

.device-frame-screen {
  position: absolute;
  inset: var(--device-bezel);
  border-radius: calc(var(--device-radius) - var(--device-bezel) + 2px);
  overflow: hidden;
  background: #000;
}

.device-frame-screen video,
.device-frame-screen img,
.device-frame-screen iframe {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
  border: 0;
}

.device-frame-notch {
  position: absolute;
  top: 12px; left: 50%;
  transform: translateX(-50%);
  width: 96px; height: 26px;
  background: #000;
  border-radius: 14px;
  z-index: 2;
}

.device-frame-reflection {
  position: absolute;
  inset: 0;
  border-radius: var(--device-radius);
  background: linear-gradient(
    105deg,
    rgba(255,255,255,0.18) 0%,
    rgba(255,255,255,0) 35%,
    rgba(255,255,255,0) 65%,
    rgba(255,255,255,0.08) 100%
  );
  pointer-events: none;
  mix-blend-mode: screen;
  z-index: 3;
}

.device-frame-iphone   { --device-w: 320px; --device-h: 660px; --device-radius: 42px; }
.device-frame-macbook  { --device-w: 720px; --device-h: 470px; --device-radius: 18px; --device-bezel: 14px; }
.device-frame-ipad     { --device-w: 540px; --device-h: 720px; --device-radius: 24px; --device-bezel: 12px; }
```

## GSAP variants (HyperFrames-deterministic)

### A — entrance с tilt (product launch reveal)

```js
gsap.from('.device-frame', {
  opacity: 0, scale: 0.82,
  rotationY: -40, rotationX: 24,
  duration: 0.9, ease: 'expo.out'
});
```

### B — floating idle (loop-safe для long beats)

```js
gsap.to('.device-frame', {
  '--tilt-y': '-22deg',
  '--tilt-x': '14deg',
  duration: 2.4, ease: 'sine.inOut',
  yoyo: true, repeat: -1
});
```

### C — reveal-then-resolve-to-front (product moment)

```js
const tl = gsap.timeline();
tl.from('.device-frame', {
  opacity: 0, scale: 0.7, rotationY: -50, rotationX: 30,
  duration: 0.7, ease: 'expo.out'
})
.to('.device-frame', {
  rotationY: 0, rotationX: 0,
  duration: 0.6, ease: 'power3.inOut'
}, '+=0.3');
```

## Integration с replicate-reel

`overlay_timeline` как kind=html_block:

```json
{
  "src": "registry://hyperframes/blocks/device-frame-tilt",
  "params": {
    "device": "iphone",
    "tilt_x": 12, "tilt_y": -18,
    "screen_src": "/tmp/recordings/feature-demo.mp4",
    "variant": "reveal_then_resolve"
  },
  "start_sec": 8.2, "end_sec": 12.5,
  "kind": "html_block"
}
```

## Когда применять / не применять

**Применять.** Product launch / SaaS hero reveal / before-after frame / multi-device demo.

**Не применять.** Vibemarketing голос автора (corporate feel) / vertical 9:16 если плашка iPhone-вертикальная / когда UI важнее devices (используй ui-record напрямую).

## Anti-patterns

- ❌ Не комбинировать с auto-zoom-on-click из ui-record на том же beat — два zoom одновременно
- ❌ Не использовать оба Variant A и Variant B подряд - устаёт глаз
- ❌ `rotation*` >50deg выглядит unnatural
- ❌ Забывать `transform-style: preserve-3d` на parent ломает 3D у child
- ❌ `<iframe>` для live UI в render mode HyperFrames - используй pre-recorded `ui-record` MP4