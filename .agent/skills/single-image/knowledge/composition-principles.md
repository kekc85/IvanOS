# Composition principles

Универсальные правила композиции для одиночной картинки-поста. Применяются во всех 5 типах с type-specific corrections.

---

## 1. Hierarchy (что primary, что secondary, что tertiary)

Каждая композиция имеет 1 primary element. Глаз должен находить его в первые 0.5 сек.

**Hierarchy через:**
- **Size** - primary 2-4x больше secondary
- **Contrast** - primary high contrast vs background, secondary medium
- **Color saturation** - primary saturated, secondary muted
- **Position** - primary центр / left third / golden ratio point
- **Negative space** - primary окружён whitespace

**Test:** Squint на готовый brief. Видишь ли всё ещё primary element distinctly?

**Common mistakes:**
- Multiple competing primaries (audience не знает куда смотреть)
- Primary не выделен ни одним из методов выше
- Decorative elements конкурируют за внимание

---

## 2. Contrast (читаемость)

**Минимум 7:1 contrast ratio** для text на background (WCAG AAA для small text). Для headline-size: 4.5:1 OK (WCAG AA).

**Контраст через:**
- Light text on dark bg (ink black on cream paper - 14:1)
- Dark text on light bg (near-black on off-white - 18:1)
- Color contrast (blue на yellow - high)
- Не использовать: light grey on white, любые pastel pairs

**Test:** Squint - текст читается? Преобразуй в greyscale - читается?

**Tool:** webaim.org/resources/contrastchecker для проверки hex pairs.

---

## 3. Stop-scroll (first 0.5 sec)

Феед прокручивается скоростью 1.5-3 поста/сек. Картинка должна остановить scroll в первые 500ms.

**Stop-scroll triggers:**
- High contrast (выделяется в потоке мутных photos)
- Specific recognizable shape / pattern (NL diagram / Stripe screenshot / meme template)
- Bold typography (хедлайн 60+ pt)
- Unexpected element (broken expectation - tilted text / unusual color)
- Real face / eyes (only если applicable type)

**Anti-stop-scroll:**
- Generic gradient backgrounds
- Stock photos (audience adapted ignore)
- Small thin text
- Muted color palette в bright feed
- Slow visual hierarchy (>1 sec чтобы понять что primary)

---

## 4. Color (правило 60-30-10)

3-цветная палитра balance:
- **60%** = dominant (фон) - обычно neutral (white / cream / black)
- **30%** = secondary - text, supporting elements
- **10%** = accent - CTA, highlight, ключевой visual focus

**4+ цветов = warning.** Multiple accents разваливают focus.

**Palette per type:**
- concept-diagram: 1-2 цвета max (ink + accent или ink + paper)
- dashboard-screenshot: real palette (то что в скрине) + 1 yellow highlight
- meme: template native palette + 1 overlay color
- quote-card: 2 цвета max (text + bg)
- before-after: muted before + vibrant after (контраст)

---

## 5. Typography hierarchy

**Max 2 typeface families** в одной композиции:
- Display / heading sans (Inter / Geist / SF Pro Display)
- Body sans (Inter / Geist)
- OR Display serif + body sans

**Size hierarchy:**
- Headline: 60-120pt
- Subhead: 30-48pt
- Body: 18-24pt
- Caption / meta: 12-16pt

**Anti-patterns:**
- 3+ typeface families (visual chaos)
- All-caps если >5 слов (читаемость drops)
- Italic для emphasis (use weight / color instead)
- Underline (web artifact, не печатный)
- Drop shadows на text (flat design current)

---

## 6. Negative space (whitespace)

**30-50% canvas = empty.** Это premium signal vs cluttered amateur look.

**Rules:**
- Margins минимум 5% от canvas edge до nearest element
- Между element groups - >2x element height as spacing
- Не fill until corners

**Test:** Можешь убрать 30% содержимого и стать ещё лучше? Если да - убирай.

---

## 7. Aspect ratios per platform (verified 2026)

| Platform | Primary | Secondary |
|---|---|---|
| **X / Twitter** | 1:1 (1080x1080) | 16:9 (1200x675) |
| **LinkedIn feed** | 1.91:1 (1200x627) | 1:1 (1080x1080) |
| **LinkedIn carousel** | 1:1 (1080x1080) | - |
| **Нельзяграм feed** | 4:5 (1080x1350) - highest reach | 1:1 (1080x1080) |
| **Нельзяграм story** | 9:16 (1080x1920) | - |
| **TG channel** | 1:1 (1080x1080) | preview 1.91:1 |
| **Threads** | 1:1 (1080x1080) | - |

**Multi-platform single brief:** дизайнить под 4:5, потом обрезать в 1:1 (центральный квадрат). Если 1.91:1 нужен - render отдельно.

---

## 8. Resolution

- Минимум 1080px на short side
- 2x export (2160px short side) для retina displays
- Format: PNG для text-heavy / sharp lines, JPEG quality 90 для photos
- WebP - support inconsistent в social platforms, использовать PNG/JPEG

---

## 9. Mobile-first (90% feed consumed on mobile)

- Text size: visible на 5.5" screen без zoom (тест на phone)
- Primary element: занимает >40% canvas (visible в thumbnail view)
- Не decorative micro-text (нечитаем на mobile)

**Test:** Открой brief на phone. Понимаешь смысл за 1.5 sec без zoom?

---

## 10. Brand consistency

Каждая картинка строит recognition. Через repetition элементов:
- Same primary palette across posts
- Same typography family
- Same composition rhythm (e.g., always centered, always left-aligned)

**Anti:** Each post в radically different aesthetic - аудитория не запоминает якорь.

**Goal:** За 3 sec scroll, audience знает «это от автора» без читания @handle.

---

## 11. Anti-AI aesthetics (importance)

Generic AI generator output имеет visible markers:
- Soft pastel gradients (purple → pink)
- Glossy 3D objects на neutral bg
- Symmetric face composition
- Бессмысленные shapes (абстракция без identity)
- Bokeh / depth-of-field decorative
- «Tech aesthetic» (neon grids / cyberpunk)

**Counter:** Use human-feeling imperfections - hand-drawn elements / specific photography / real screenshots / asymmetric composition / unexpected color choices.

См. `knowledge/anti-patterns.md` подробнее.

---

## 12. Final composition checklist

Перед output:
- [ ] 1 primary element identified (squint test passed)
- [ ] Contrast 7:1+ для small text, 4.5:1+ для headline
- [ ] Mobile-readable (phone test passed)
- [ ] Aspect matches platform target
- [ ] 60-30-10 color balance
- [ ] Max 2 typeface families
- [ ] Negative space 30-50%
- [ ] Resolution >=1080px short side
- [ ] No generic AI aesthetic markers
- [ ] Brand consistency якорь visible