# Workflow 05-publish - Output + A/B + assets manifest

**Назначение:** финальный output для пользователя. Готовый markdown + A/B варианты + assets manifest + 3 слоя report.
**Вход:** `carousel` после `04-review.md` PASS
**Выход:** markdown report + open file через `open` (memory правило)

---

## Шаг 0 - Auto-invoke render (v1.1)

После 04-review PASS - **автоматически** вызвать `workflow/06-render.md` для actual PNG/PDF generation.

```
if carousel.review_status == PASS:
  → workflow/06-render.md (генерирует папку с PNGs + PDF + caption files)
  → output = ~/Desktop/carousels/{date}-{slug}/
```

Если render failed для специфичных slides - placeholder + manual queue (см. 06-render.md). Workflow не блокируется.

После 06-render → продолжить с output markdown ниже как companion brief.

---

## Шаг 1 - Build output markdown (companion to rendered folder)

Структура output:

```markdown
# Carousel: <topic>

**Family:** <one of 5>
**Platform:** <ig | li | both>
**Slides:** <count>
**Mode:** <how it was made>
**Language:** <ru | en | both>

---

## Slides

### Slide 1 - Hook
**Text:** <verbatim>
**Visual brief:**
- Real elements: <list>
- Composition: <description>
- Typography: <font + sizes>
- Color: <palette>
- Text overlay: <exact text on image if any>
- Abstraction check: PASS
- Pacing role: promise + curiosity gap

### Slide 2 - Context
...

### Slide N - CTA
...

---

## Caption (RU)

[full caption text 125 chars hook | body | CTA | hashtags]

## Caption (EN - если bilingual)

[full caption text 210 chars hook | body | CTA | hashtags]

---

## A/B Variants

**Hook alternative:** <alt text>
**Caption first-line alternative:** <alt opening>

---

## Assets Manifest (что нужно собрать)

| # | Asset | Source | Status |
|---|---|---|---|
| 1 | Cursor IDE Composer screenshot | manual screenshot | TODO |
| 2 | Stripe MRR dashboard $X | manual screenshot | TODO |
| 3 | Author face photo | existing brand library | READY |
| 4 | Lovable UI screenshot | manual screenshot | TODO |
| ... | ... | ... | ... |

---

## How it was made (внутрянка)

- Mode: <plan | spark | transcript | reel-to-carousel>
- Source quotes: <если есть из надиктовки или Карты смыслов>
- Family choice rationale: <почему framework а не listicle>
- Archetype: <chosen>
- Hook formula: <number + outcome + timeframe или другой>
- Real elements ratio: <N/M slides - X%>
- Banned patterns avoided: <12-item checklist all PASS>
- 3 слоя пройдено: ✓

---

## Production notes

- Slide aspect: 1080×1350 (4:5 portrait)
- Slide count: N (within IG sweet spot 8-10 / LI 7-12 / panorama 3-8)
- Typography: <font + sizes per slide role>
- Color accent: <brand color>
- Estimated production time: <X hours для manual assets / Y минут для AI-rendered>

---

## Cross-distribution map (POSSE)

- **Primary publish:** <platform>
- **IG carousel ready:** <Y/N> (если platform=ig|both)
- **LinkedIn PDF needed:** <Y/N> (если platform=li|both - chain в frontend-design для PDF)
- **Threads cross-post:** опционально (caption + 1-2 slides preview)
- **TG bridge:** опционально (carousel hero + caption full text)

---

## Next steps

1. Собрать assets из manifest (manual screenshots / AI-gen)
2. Дизайн slides (Figma / Canva / frontend-design chain)
3. Publish per platform
4. Log в `examples/track-record-carousel.md` после публикации
```

---

## Шаг 2 - Save + Open

Save output в `~/Desktop/carousels/<YYYY-MM-DD>-<topic-slug>.md` (или `<config.output.path>` если указан).

Open через Bash:
```bash
open ~/Desktop/carousels/<file>.md
```

Memory правило: `[[feedback-always-open-artifacts]]`.

---

## Шаг 3 - Log в track-record

Append в `examples/track-record-carousel.md`:

```markdown
## Применение N - YYYY-MM-DD: <topic>

- Mode: <mode>
- Family: <family>
- Platform: <platform>
- Slide count: <N>
- Real elements ratio: <X%>
- 6-Pass findings: <count>
- Maxwell Ross: <9/9 или fix-list>
- 3 слоя: PASS
- A/B variants generated: 2
- Time to brief: <X minutes>
- Time to assets (manual estimate): <Y hours>
- Notes: <any non-obvious learnings>
```

Catch_rate metric обновляется когда автор сообщает реальный engagement (post-publication).

---

## Шаг 4 - Final report в чат

Compact summary пользователю:

```
✓ Carousel готов: <topic>

Family: <family>
Slides: <N>
Real elements: <X/N slides>
Caption: RU (<chars>) / EN (<chars>) если bilingual
A/B: 2 hook + 2 caption alternatives
Assets manifest: <M items to collect>

Файл: <path>
3 слоя: PASS ✓

Что дальше: собрать assets → дизайн slides → publish.
```

---

## Принципы

1. **Open artifact mandatory.** `open` готового brief - memory правило.
2. **Assets manifest tracked.** Что нужно собрать - явный список.
3. **POSSE distribution map.** Один source - N каналов.
4. **Track record logging.** Каждое применение - entry для catch_rate.
5. **Compact final report.** Не дублировать output в чат, ссылка + summary.
---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
