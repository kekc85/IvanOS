---
name: lottie
description: Lottie and dotLottie adapter patterns for HyperFrames. Use when embedding lottie-web JSON animations, .lottie files, @lottiefiles/dotlottie-web players, registering instances on window.__hfLottie, or making After Effects exports deterministic in HyperFrames.
---

# Lottie for HyperFrames

HyperFrames can seek both `lottie-web` and dotLottie players through its `lottie` runtime adapter. Lottie is a strong fit because the animation timeline is already encoded in the asset; HyperFrames only needs a player object it can seek.

## Contract

- Load assets from local project files, usually under `assets/`.
- Set `autoplay: false`.
- Prefer `loop: false` unless the user explicitly wants a loop.
- Register every returned animation or player on `window.__hfLottie`.
- Keep the Lottie container dimensions stable with CSS.

The adapter seeks `lottie-web` with `goToAndStop(timeMs, false)` and dotLottie with frame or percentage APIs depending on player shape.

## dotLottie 2025-2026 capabilities (новое)

Используй когда нужна сложная stateful UI animation внутри Reel.

### Multi-animation containers

Один `.lottie` файл может содержать **несколько вариантов одной анимации** (например, button states: idle / hover / pressed / loading / success). Asset deduplication между ними.

```html
<dotlottie-player id="button-states" autoplay="false" src="assets/button-states.lottie"></dotlottie-player>

<script type="module">
  import '@lottiefiles/dotlottie-web';
  const player = document.getElementById('button-states');
  player.addEventListener('ready', () => {
    const ids = player.getAnimationIds();
    player.loadAnimation(ids[2]); // например "pressed"
  });

  window.__hfLottie = window.__hfLottie || [];
  window.__hfLottie.push(player);
</script>
```

### State machines (interactive logic)

С late-2025 dotLottie state machines позволяют декларативно описать переходы между анимациями по триггерам. Для HyperFrames render — state machine seek-driven, не event-driven.

В HyperFrames composition state переключается по data-attribute с seek-bound logic:

```html
<dotlottie-player id="btn" src="..." data-hf-states='[
  {"at": 0.0, "state": "idle"},
  {"at": 1.0, "state": "hover"},
  {"at": 1.4, "state": "pressed"},
  {"at": 1.8, "state": "success"}
]'></dotlottie-player>
```

Adapter в `lottie` runtime читает `data-hf-states` и при `hf-seek` event переключает state на нужный.

### AI logic generation (Lottie Creator)

В Lottie Creator можно описать словами какой нужен state machine — система сгенерит JSON. Workflow: спроектировать states + transitions словами → AI сгенерит config → импортировать в `.lottie` файл → подключить через адаптер выше.

### ThorVG renderer перформанс

На iOS — 80% быстрее рендер + 70% меньше memory. На web — `dotlottie-web` использует Canvas renderer по умолчанию (vs SVG в legacy lottie-web). В render-режиме HyperFrames это означает что сложные анимации не тормозят browser-side capture.

### Когда использовать что

- **lottie-web**: legacy AE экспорты, одиночная анимация, нет state логики
- **dotLottie + multi-animation**: серия вариантов одного объекта (button states / icon variants / character emotions)
- **dotLottie + state machine**: interactive UI mockup где разные states важны для нарратива

## lottie-web Pattern

```html
<div id="logo-lottie" class="lottie-layer"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js"></script>
<script>
  const anim = lottie.loadAnimation({
    container: document.getElementById("logo-lottie"),
    renderer: "svg",
    loop: false,
    autoplay: false,
    path: "assets/logo-reveal.json",
  });

  window.__hfLottie = window.__hfLottie || [];
  window.__hfLottie.push(anim);
</script>
```

```css
.lottie-layer {
  width: 100%;
  height: 100%;
}
```

## dotLottie Pattern

```html
<canvas id="product-lottie" class="lottie-canvas"></canvas>
<script src="https://unpkg.com/@lottiefiles/dotlottie-web"></script>
<script>
  const player = new DotLottie({
    canvas: document.getElementById("product-lottie"),
    src: "assets/product-flow.lottie",
    autoplay: false,
    loop: false,
  });

  window.__hfLottie = window.__hfLottie || [];
  window.__hfLottie.push(player);
</script>
```

```css
.lottie-canvas {
  width: 100%;
  height: 100%;
  display: block;
}
```

## Multiple Animations

Push each player into the same registry:

```js
window.__hfLottie = window.__hfLottie || [];
window.__hfLottie.push(backgroundAnim);
window.__hfLottie.push(iconAnim);
window.__hfLottie.push(confettiAnim);
```

HyperFrames seeks them all to the same composition time.

## Good Uses

- After Effects exports that are already known to render correctly in lottie-web.
- Logo reveals, icon loops, decorative accents, and product UI motion.
- Translating Remotion Lottie usage into plain HyperFrames HTML.

## Avoid

- Relying on remote `path` URLs at render time.
- Starting playback with `play()`.
- Assuming unsupported After Effects effects will survive export. Test the JSON or `.lottie` file in a browser first.
- Loading a player asynchronously and registering it after HyperFrames validation has already inspected the page.

## Validation

After editing a Lottie composition:

```bash
npx hyperframes lint
npx hyperframes validate
```

## Credits And References

- HyperFrames adapter source: `packages/core/src/runtime/adapters/lottie.ts`.
- lottie-web by Airbnb: https://github.com/airbnb/lottie-web
- lottie-web `loadAnimation` options: https://github.com/airbnb/lottie-web/wiki/loadAnimation-options
- dotLottie web player methods by LottieFiles: https://developers.lottiefiles.com/docs/dotlottie-player/dotlottie-web/methods
