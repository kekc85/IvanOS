# Workflow Step 07: Visual Quality Gate (L8)

**Когда:** После 06-render, ДО declare ready для publish.
**Триггер:** automatic для каждого rendered carousel (mandatory если artifact_type=visual).
**Status:** BLOCKING - если FAIL, carousel не публикуется.

---

## Pre-requisites

1. **Anchors saved.** `~/.claude/skills/carousel/visual-anchors/` содержит:
   - 3+ anchor image files (`reference-N-{author}-{category}.png` или `.jpg`)
   - `manifest.md` с decomposition per anchor

2. **Rendered output exists.** `~/Desktop/carousels/{date}-{topic}-RENDERED/slide-NN.png` (минимум slide-01).

3. **Vision judge доступен.** Read tool способен загрузить PNG в LLM context.

Если хотя бы один pre-req fail - НЕ запускать gate, написать в chat «L8 BLOCKED: <причина>» + предложить fix.

---

## Шаг 1: Load anchors

```bash
ls ~/.claude/skills/carousel/visual-anchors/*.{png,jpg,jpeg} 2>/dev/null
```

Read каждый anchor через Read tool (image). Загружаются как visual context.

Read `~/.claude/skills/carousel/visual-anchors/manifest.md` для interpretation.

---

## Шаг 2: Load output

Read `~/Desktop/carousels/{date}-{topic}-RENDERED/slide-01.png` минимум. Если несколько slides - Read первые 3 (hook + 2 mid).

---

## Шаг 3: Run LLM judge

**Prompt:**

```
Ты - visual quality judge для Instagram/LinkedIn carousel skill.

ANCHORS (это reference visuals которые автор пометил как target quality):
[Embedded N anchor images]

SKILL OUTPUT (что нужно оценить):
[Embedded rendered slide(s)]

ANCHOR DECOMPOSITION (text descriptions из manifest):
{paste manifest.md content here}

ОЦЕНИ по 5 criteria:

1. **Same visual category?** Output принадлежит той же визуальной категории что anchors?
   - Тест: если положить рядом 3 anchors + 1 output, output не выделяется как "из другой эпохи / другого мира"
   - Hero element role + typography role + layout zones одинаковые
   - Verdict: PASS / WARN / FAIL + 1 строка reasoning

2. **Hero element ≥40% area?**
   - Output содержит physical hero element (photo / screenshot / scene / composite) занимающий минимум 40% canvas
   - Pure typography = FAIL (если family ≠ document-format / CTA action card)
   - Verdict: PASS / WARN / FAIL + 1 строка

3. **Real elements visible?**
   - Output содержит physical real elements (product UI screenshots / numbers с context / brand logos / persona faces)
   - Не только text mentions ("Stripe MRR" словом), а physically embedded UI / image
   - Verdict: PASS / WARN / FAIL + 1 строка

4. **No generic AI tells?**
   - Не gradient blobs / generic stock illustrations / AI-people-in-office / generic abstract shapes
   - Не cream-and-red corporate template aesthetic
   - Verdict: PASS / WARN / FAIL + 1 строка

5. **Brand consistency?**
   - Использует brand colors / typography / signature elements из config.brand_assets
   - Имеет brand signature (handle / signature element / consistent palette)
   - Verdict: PASS / WARN / FAIL + 1 строка

ФИНАЛЬНЫЙ VERDICT:
- **PASS** - все 5 PASS, или 4 PASS + 1 WARN на non-critical
- **WARN** - 3 PASS + 2 WARN, или 4 PASS + 1 FAIL на criteria 4 или 5
- **FAIL** - любой FAIL на criteria 1 (category) ИЛИ criteria 2 (hero) ИЛИ ≥2 FAILs

Output формат:
```yaml
verdict: PASS | WARN | FAIL
criteria:
  1_category: PASS | WARN | FAIL + "1 строка причины"
  2_hero: PASS | WARN | FAIL + "1 строка"
  3_real_elements: PASS | WARN | FAIL + "1 строка"
  4_no_ai_tells: PASS | WARN | FAIL + "1 строка"
  5_brand: PASS | WARN | FAIL + "1 строка"
fix_recommendations:
  - "Какой template / asset / palette нужно изменить (concrete)"
```
```

---

## Шаг 4: Apply verdict

### Verdict = PASS

- Write `~/Desktop/carousels/{date}-{topic}-RENDERED/L8-PASS.md` с judge output.
- Continue к 05-publish.

### Verdict = WARN

- Write `~/Desktop/carousels/{date}-{topic}-RENDERED/L8-WARN.md` с judge output + flagged areas.
- Output в chat: «L8 WARN - публикую с пометкой [X/Y/Z deviations]».
- Continue к 05-publish (не blocking).

### Verdict = FAIL

- Write `~/Desktop/carousels/{date}-{topic}-RENDERED/L8-FAIL.md` с judge output + root cause analysis.
- НЕ continue к 05-publish.
- Output в chat:
  ```
  ❌ L8 FAIL: <criteria>
  Root cause: <which template / asset / pattern wrong>
  Fix: <concrete action - replace template X / regenerate asset Y / change palette Z>
  Action: re-render slide(s) с fix → re-run L8.
  ```

---

## Manual override

LLM judge может subjectivity-FAIL даже когда output OK. User может explicit override:
- В chat: «L8 PASS confirmed manual» → write `L8-MANUAL-PASS.md` с user decision + reasoning.

Override = exception, не default. Default trust judge.

---

## Tracking

После каждого gate run - append в `~/.claude/skills/carousel/examples/L8-history.md`:

```yaml
- date: 2026-MM-DD
  carousel: {topic}
  output: slide-01.png
  anchors_used: [list]
  verdict: PASS | WARN | FAIL
  criteria_failed: [list]
  fix_applied: "..."
  re_run_verdict: PASS | WARN | FAIL
```

Track-record позволяет catch_rate metric для L8 calibration over time.

---

## Cross-refs

- как собирать anchors - описано в этом же файле выше
- `references/banned-ai-imagery.md` - checklist для criteria 4
- `config.md` `brand_assets` section - для criteria 5
- skill-craft `knowledge/methodology.md` L8 section - methodology reference

---

**Версия:** v1.0 (2026-05-28 evening, carousel v2.0 visual-first rebuild)