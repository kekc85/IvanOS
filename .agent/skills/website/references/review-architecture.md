# Архитектура визуального review (авторитетный чертёж скилла website)

> Это ЧЕРТЁЖ системы review, против которого сверяется реализация (`workflow/09-self-review.md` + `scripts/layout-audit.mjs` + хук `website-review-gate.sh`). Источник модели — индустрия 2024-2026 (ресёрч + верификация полноты по решению автора). Цель: review ловит ВСЕ классы дефектов сам, автор не «пополняет библиотеку» руками.

## Принцип полноты: НЕ длина списка, а ОСИ ОХВАТА
Полнота гарантируется не перечнем классов (он всегда неполон), а **матрицей охвата по 5 ортогональным осям**. Пропуск = явная дыра в ячейке, а не молчание.

```
ПОЛНОТА = РУБРИКА (что искать)  ×  РЕГИОНЫ (где: hero/заголовок/CTA/соцпруф/…)
        × ШИРИНЫ (320-360 / 768± / 1024± / 1280 / 1440+ — зоны МЕЖДУ брейкпоинтами, не 3 точки)
        × СОСТОЯНИЯ (default / loading / empty / error / disabled / submitted / hover / focus)
        × КАДРЫ-ВО-ВРЕМЕНИ (0ms / после шрифта / после картинок / после анимации — CLS/jank)
```
Старая модель брала только РУБРИКА × РЕГИОНЫ × ШИРИНЫ (1 кадр, 1 состояние) = ~80% (SOTA для статичного снимка). Оси СОСТОЯНИЯ и ВРЕМЯ — главный слепой класс, добиваем до ~95%.

## 3 слоя (что кому)
Ни один слой не ловит «всё». Полнота = сборка. Разделение по принципу «машина — измеримое, vision — вкус, человек — развилка».

### Слой 1 — ДЕТЕРМИНИРОВАННЫЙ ПОЛ (машина, без зрения, exit-гейт)
Меряемое НИКОГДА не проскакивает. `scripts/layout-audit.mjs` + axe + Lighthouse + design-lint. Зрение тут слабее (модели в spatial 50-60%).

| Класс | Чем меряется | Статус |
|---|---|---|
| Наложение текста (стикер закрывает текст) | пересечение `getBoundingClientRect` | ✅ есть |
| Прилипание секций (нет отступа) | gap между band'ами, дедуп обёрток DOM-containment | ✅ есть |
| Вылет за вьюпорт / обрезка на узком | `right>vw`, декор `pointer-events:none` не флагать | ✅ есть |
| «Буквы за плашкой» (контент за свой бокс) | `scrollW/H>clientW/H` на визуально-замкнутом компоненте | ✅ есть (`container_overflow`) |
| Контент шире контейнера (клип) | `scrollWidth>clientWidth` + `overflow≠visible` | ✅ есть |
| Контраст текста ≥4.5:1 (3:1 крупный/UI) | `@axe-core/playwright` WCAG 2.2 AA | ✅ есть |
| a11y (alt, фокус, роли) | axe-core (~57%, 0 false-positive) | ✅ есть |
| **Touch-target ≥24×24px** (WCAG 2.2 SC 2.5.8) | `getBoundingClientRect` интерактивных (display≠inline) | ✅ есть (`touch_targets`) |
| **Картинка без width/height/aspect-ratio** (→ reflow/CLS/blur) | атрибуты + `aspect-ratio` CSS | ✅ есть (`image_dims`) |
| **CLS / layout-shift во времени** (шрифт/картинка догрузились → прыжок) | `PerformanceObserver('layout-shift', buffered)` в Playwright за окно загрузки, порог ≤0.1 | ✅ есть (`cls`) — без тяжёлого Lighthouse |
| **FOUT/FOIT (`font-display`)** | прямая проверка `@font-face`/Google-Fonts на `font-display:swap` на моб | ✅ есть (`font_display`, HARD) |
| **Render-blocking JS** (синхронный `<script src>` в `<head>`) | DOM-проверка на defer/async/module, на моб (≤480) | ✅ есть (`render_blocking`, HARD) |
| **Offscreen-картинка без `loading=lazy`** (качает впустую) | bbox top > 1.5×vh + атрибут loading, на моб | ✅ есть (`img_offscreen_eager`, HARD) |
| **Вес/запросы/LCP/DOM-узлы** (мобильный перф-бюджет) | Resource Timing `decodedBodySize` + LCP-observer | ✅ advisory (`_perf`/`lcp_ms`; HARD при `--weight-budget`) |
| **Развёртка между брейкпоинтами** (360/768/1024/1280, не 3 точки) | дефолт ширин аудита | ✅ есть |
| **Токены (spacing/typography/color из канона)** | design-lint | 🔜 опц. |
| Орфаны (слово на строке) | Range-подсчёт слов | ⚠️ НЕблокирующий КАНДИДАТ (намерение решает Слой 3) |

### Слой 2 — РЕГРЕССИЯ против baseline (полнота по построению) — ✅ РЕАЛИЗОВАН
`scripts/regression-check.mjs` (pixelmatch self-baseline): первый прогон создаёт baseline, дальше — diff vs baseline, exit 1 при `diff_ratio > 0.01` (индустр. 0.01-0.02), пишет diff-PNG; `--update` перезаписывает baseline после АПРУВА экрана. Ловит ЛЮБОЕ непреднамеренное отклонение/дрейф (фикс экрана N не сломал N-1), не завися от перечня классов. Анимационный шум (печать/счётчики) поглощается порогом. Усиливает. *(Апгрейд при желании: Playwright `toHaveScreenshot` + Argos review-UI.)*

### Слой 3 — VISION-LLM по ЗАКРЫТОЙ РУБРИКЕ (вкус, что машина не берёт) — ✅ РЕАЛИЗОВАН (rubric-as-code)
`references/vision-rubric.md` — критик-субагент загружает её на Шаге 9.2. Метод arxiv 2412.16829 + 2510.08783:
- Рубрика **11 линз × регионы × ширины** ОБЯЗАТЕЛЬНА, по каждой ячейке «ок/нарушено + bbox». ✅
- **PAIRWISE против эталона** (90%+). ✅
- Каждый дефект = **bbox + правка**; 🔴 **КРОСС-ВАЛИДАЦИЯ Слоем 1** — геометрический дефект без подтверждения машиной = галлюцинация, отбросить (bbox доказанно не защищает — [arxiv 2406.14492](https://arxiv.org/pdf/2406.14492)). ✅ зашито в протокол рубрики.
- Multi-pass 2-3 прохода; ≥2 судьи (перспектива-диверсити), свод по худшему. ✅
- **Few-shot калибровка** good/bad якорями (UICrit [arxiv 2407.08850](https://arxiv.org/pdf/2407.08850)). ✅

### Человек
Финальный апрув ЭКРАНА + реальная бизнес-развилка. НЕ микроправки, НЕ отлов брака.

## Луп сходимости (минимум человека)
```
на экран: render(ширины × состояния) → Слой1 → fix → render → до 0 красных
        → Слой2(регрессия) → Слой3(рубрика×регионы, pairwise, bbox, кросс-валид Слоем1)
        → агент применяет правки САМ → re-render
        → СТОП по СХОДИМОСТИ: 0 красных Слой1 И 100% рубрики «ок» И L2-дифф<порог И линзы ≥9
```
Сходимость по КРИТЕРИЮ, не по числу итераций. Эмпирика: агент, что ВИДИТ/МЕРЯЕТ результат, сходится за 2-3 итерации (vs 10+).

## СТАТУС: для статичного лендинга — ВСЕ 3 СЛОЯ РЕАЛИЗОВАНЫ (целостная система)
Было ~80% (статичный снимок ≈ SOTA одного слоя). После реализации по решению автора — полная 3-слойная система:
1. ✅ **Слой 1 (машина)** — геометрия + container_overflow + контраст/a11y (axe) + touch-target + image-dims + **CLS (ось ВРЕМЯ)** + развёртка между брейкпоинтами. `scripts/layout-audit.mjs`.
2. ✅ **Слой 2 (регрессия)** — `scripts/regression-check.mjs` (pixelmatch self-baseline).
3. ✅ **Слой 3 (vision)** — `references/vision-rubric.md` (11 линз × регионы × ширины, pairwise, bbox + **кросс-валидация Слоем 1**, few-shot, перспектива-диверсити, сходимость).

**N/A для статичного лендинга (НЕ пробел — вне скоупа по природе объекта):** ось СОСТОЯНИЙ loading/empty/error (лендинг рендерит ОДНО состояние; hover/focus — во входе критика); dark-mode / RTL / печать (для RU/EN-лендинга не нужны); Storybook-состояния (нужны при компонентной сборке, не при цельной странице); APCA-потолок и font-display — опц. сверх WCAG-пола. Система знает свои границы и в них исчерпывающа.

## Пороги (индустриальный стандарт)
| Метрика | Порог | Источник |
|---|---|---|
| Pixel-diff регрессии | `maxDiffPixelRatio` 0.01–0.02 | [Playwright](https://playwright.dev/docs/test-snapshots) |
| CLS | ≤0.1 good · >0.25 poor (p75) | [web.dev/cls](https://web.dev/articles/cls) |
| Контраст текста | 4.5:1 норм · 3:1 крупный/UI (WCAG 2.2 AA) | [W3C 1.4.3](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) |
| Touch-target | ≥24×24px AA · 44-48px рекоменд. платформ | [W3C 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) |

## Источники
arxiv [2412.16829](https://arxiv.org/abs/2412.16829), [2510.08783](https://arxiv.org/html/2510.08783v1), [2407.08850](https://arxiv.org/pdf/2407.08850) (UICrit), [2406.14492](https://arxiv.org/pdf/2406.14492) (bbox≠анти-галлюцинация); [axe-core](https://www.deque.com/axe/axe-core/), [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci), [Playwright snapshots/agents](https://playwright.dev/docs/test-snapshots), [Argos](https://argos-ci.com/), [Storybook visual/a11y](https://storybook.js.org/docs/writing-tests/visual-testing), [Galen](https://galenframework.com/), [design-lint](https://lapidist.net/articles/2025/introducing-lapidist-design-lint/), [web.dev CLS](https://web.dev/articles/cls), WCAG 2.2.

## Связь
Реализация: `workflow/09-self-review.md` (процесс) · `scripts/layout-audit.mjs` (Слой 1) · хук `website-review-gate.sh` (принуждение). Память:,.
