---
name: "ui-inventory"
description: "Inventory v2 + v4.0 5-level review для replicate viral Reels. (1) Покадровый анализ ингеста + 4 GATES discipline: GATE A Type classification (verbatim measurements: face % / UI % / PIP Y/N), GATE B brand specifics inventory (actual products, не abstractions), GATE C talk-track word-level pinning (transcript.json), GATE D pre-render manifest (FILLED/PLACEHOLDER/MISSING). (2) v4.0 5-level review (WCAG 2.1 PASS/FAIL gate / Disney 12 + Material tokens / NN/g heuristics 4-question / Reference Fidelity visual diff no-self-eval / PDCA iteration). Empirically validated по решению автора на Nate Herk DXZsCExij3g — catches 5/6 known clone failures. Triggers: 'разбери UI', 'inventory ролика', 'review mock', '/ui-inventory <ingest-folder>'."
---

# UI Inventory — раскладка чужого viral ролика перед репликацией

## Когда использовать

После `ingest-reel`, перед `replicate-reel`. Решает задачу "откуда брать UI-вставки при репликации чужого viral ролика чтобы получить чистые клипы без лица оригинального автора".

Решает системную проблему в даты запуска.2026 — 4 сессии буксования на ffmpeg trim наугад → куски с лицами авторов. Теперь покадровый анализ + классификация по 2 типам.

## Шаги

### Шаг 1: Извлечь кадры 2fps + сделать montage'и

```bash
INGEST=~/.business/growth/ingest/YYYY-MM-DD-VIDEOID
OUT=/tmp/ui-inv-$(basename $INGEST)
mkdir -p $OUT

# Кадры 2fps
ffmpeg -y -i $INGEST/*.mp4 -vf "fps=2,scale=240:426" $OUT/f_%03d.jpg

# Длительность определяет количество montage'ей
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $INGEST/*.mp4)
FRAMES=$(ls $OUT/f_*.jpg | wc -l)

# Montage'и по 20 кадров (5x4 tile) = 10 сек каждый
for batch in 1 2 3 4 5 6; do
  start=$(( (batch-1)*20 + 1 ))
  end=$(( batch*20 ))
  [ $batch -eq $(((FRAMES+19)/20)) ] && end=$FRAMES
  [ $start -gt $FRAMES ] && break
  count=$((end-start+1))
  ffmpeg -y -framerate 1 -start_number $start -i "$OUT/f_%03d.jpg" \
    -frames:v $count -vf "tile=5x4:padding=4:color=white" \
    $OUT/montage_0${batch}.jpg
done
```

Для ролика <40 сек используй tile=4x4 и batches по 16 кадров.

### Шаг 2: Самому прочитать каждый montage

**КРИТИЧНО**: открыть каждый `montage_0N.jpg` через Read и **словами описать каждый кадр**. Не показывать автору непросмотренным — это системная ошибка №1.

Для каждого кадра f_N (timestamp = (N-1)*0.5s) выписать:
- что в верхней половине / нижней половине
- talking head автора в полный кадр / в PIP / нет
- какой UI (mock-up график / реальный editor / AI-gen b-roll / vendor screenshot / lifestyle stock)
- любой текст overlay на кадре

### Шаг 3: GATE A — Type classification (mandatory verbatim measurements)

**КРИТИЧНО:** Type classification NEVER assigned without verbatim measurements. Predicted Type ≠ measured Type. Source: empirical Nate Herk re-inventory по решению автора — implicit Type 1 в clone v5 каскадировал во все downstream решения и убрал face cam как primary handle.

**3 measurements required перед Type assignment:**

```bash
# Measurement 1: Face-cam visible seconds (full or PIP)
# Просмотр всех frames, count where author face is present
# Output format: "X / Y seconds = Z% face visible"

# Measurement 2: Real product UI screenshot seconds
# Count frames с реальный screen recording / app capture
# Output format: "X / Y seconds = Z% real UI"

# Measurement 3: PIP composition detection (Y/N)
# Y = face cam в углу + UI dominant в течение ≥10% длительности
# N = no PIP composition observed
```

**Type assignment rules (criteria-based, не intuition):**

| Measurement | Тип 1 (Mock-driven) | Тип 2 (Real-product-UI + face PIP) |
|---|---|---|
| Face visible | <20% | ≥20% |
| Real UI | <30% | ≥30% (often ≥50%) |
| PIP detected | N | Y (often) |

**Тип 1 — Mock-driven** (face <20%, UI mostly mocked):
- Доминирует full-screen UI на белом/едином фоне (графики, comments mockups, terminal mocks, folders)
- AI-generated b-roll (CGI продукт, vertical UGC девушки, lifestyle)
- Split screen верх-UI / низ-talking head
- Пример эталон: `2026-05-25-DYAopkSSDL6` (Codex CLI / Higgsfield)

**Тип 2 — Real-product-UI + face PIP** (face ≥20%, real UI ≥30%, PIP Y):
- Реальный screen recording продукта (n8n editor, Cursor, Claude Code, web app)
- Face cam автора в углу нижней четверти кадра
- Иногда переходы в full talking head на 1-3 сек
- Пример эталон: `2026-05-23-DXZsCExij3g` (Nate Herk anti-n8n) — 56% face / 50% n8n / PIP Y

**Output GATE A:** verbatim measurements + Type verdict. Without measurements — block proceeding to GATE B.

### Шаг 4: Построить ui-inventory.md с 4 GATES

Структура с обязательными gates A-D (validated empirically Nate Herk по решению автора, catches 5/6 known clone failures):

```markdown
# UI Inventory v2 - <ingest-id>

**Тип ролика:** Тип 1 / Тип 2 (verdict из GATE A)
**Длительность:** XX.X сек
**Resolution:** 1080x1920

---

## GATE A — Type Classification (verbatim measurements)

| Metric | Value |
|---|---|
| Total duration | XX seconds |
| Face-cam visible (full + PIP combined) | X / XX = Z% |
| Face-cam in PIP/split | X / XX = Z% (at seconds: a,b,c,...) |
| Face-cam full-screen | X / XX = Z% (at seconds: a,b,c,...) |
| Real product UI seconds | X / XX = Z% |
| Brand specific UI (e.g. n8n editor / Cursor IDE) | X / XX = Z% |
| AI/staged B-roll (letterboxed / cinematic) | X / XX = Z% |
| PIP composition (UI top + face bottom) Y/N | Y / N |

**Verdict GATE A:** Тип 1 или Тип 2 (с обоснованием через measurements).

---

## GATE B — Brand Specifics Inventory (each UI moment)

Для каждого significant UI moment — exact identity, NOT "generic mockup":

| TS range | Visible content (verbatim observable) | Brand identity / actual product | Source URL / reference path | Animation behavior |
|---|---|---|---|---|
| 6.0-9.5s | n8n editor workflow with purple connection nodes, visible node names: "MCP Server Trigger", "Gmail Trigger", "Email Responder Agent" | n8n.io editor real screen recording | https://n8n.io + screenshots from /Users/.../ingest/.../scene-frames/f_013.jpg | scale 1.0 → 1.4 over 400ms, ease cubic-bezier(0.2,0,0,1) |
| 12.0-13.5s | cream off-white BG #F4F0EA with bold serif "✦ Claude Code" wordmark, typewriter reveal char-by-char | Claude Code by Anthropic | https://claude.com/claude-code + ref-26s.jpg | char stagger 40ms / total 800ms ease.emphasized.decelerate |

**Каждый row MUST:**
- Identify actual product (not "generic workflow mockup" / not "Newcomer essentials")
- Cite source: URL / screenshot path / vendor docs
- Verbatim observable content (text content, node names, exact UI elements)
- Animation specs with Material motion tokens

**Mark MISSING для items where brand specifics cannot be identified** — это блокирует render (GATE D check).

---

## GATE C — Talk-track Timing Locks (word-level pinning)

Open `transcript.json` (word-level, whisper output). Каждый visual element pinned to specific transcript word start_time.

| Word (transcript) | start_time | Visual element triggered | Replicate target |
|---|---|---|---|
| "n8n" | 0.18s | Split-screen: n8n splash top + face cam bottom | mirror composition with our product |
| "dead" | 0.94s | "DEAD" caption overlay в Submagic-style yellow box | match caption style + word pinning |
| "things" | 9.82s | n8n folders changelog post (meta-evidence beat — strongest narrative argument) | hard requirement — DO NOT omit |
| "it doesn't" | 18.0s | Continued indictment of n8n с red Execute (NOT pivot to solution despite audio setup) | preserve INTENTIONAL pain-visual + setup-audio dissonance |
| "switch" | 28.5s | Full face cam Nate "SWITCH" + AIS logo | our author full face + brand |

**Rule:** каждый significant visual element MUST have transcript word anchor. Visual без anchor = generic decoration = candidate for cut.

**Meta-evidence beats detected through GATE C inspection** (например n8n changelog post = "things change" meta-argument) — naturally surface когда forced to inspect what visual lands on specific transcript words.

---

## GATE D — Pre-render Manifest

| Slot | Required content | Status | Blocker if MISSING |
|---|---|---|---|
| A1 — Face cam range | XX seconds of author face talking head | FILLED / PLACEHOLDER / MISSING | render blocked |
| A2 — Face cam PIP | XX seconds of PIP composition | FILLED / PLACEHOLDER / MISSING | render blocked |
| B1 — n8n editor real screenshots | 9 distinct frames (specific node names) | FILLED / PLACEHOLDER / MISSING | render blocked |
| B2 — Claude Code wordmark cream slide | reference frame ref-12s | FILLED / PLACEHOLDER / MISSING | render blocked |
| C1 — Word-level caption track | Submagic-style word-by-word for entire duration | FILLED / PLACEHOLDER / MISSING | render blocked |
| D1 — Cinematic B-roll polarity break | 2s letterboxed at "identity shift" line | FILLED / PLACEHOLDER / MISSING | render warning (optional) |

**STATUS legend:**
- FILLED — data exists, ready to use в replicate-reel
- PLACEHOLDER — needs gathering (real screen recording / face cam shooting / AI-gen)
- MISSING — cannot fill from current data, blocker для high-fidelity replica

**Rule:** все critical slots (A1-A2, B-family for Type 2, C1) MUST be FILLED перед replicate-reel starts. Any PLACEHOLDER или MISSING — replicate-reel запускается с warning или blocked.

---

## Sections plan (post-gates summary table)

| TS | Тип секции | Описание UI | Категория | План повтора |
|---|---|---|---|---|
| 0.0-2.5 | SPLIT | Sam Altman сверху + автор снизу + текст "OPENAI dropped CODEX CLI" | Г+Д | Public OpenAI press portrait + наш talking head |
| 2.5-3.5 | FULL CLEAN UI | график "Optimized token spend / With CLI 10x cheaper" | А | hyperframes mock с нашими цифрами |

## Категории UI

- **А** = Mock автора → hyperframes/HTML под нас (v2.0 prompt template, см. motion-storyboard SKILL.md)
- **Б** = Public продуктовый UI → ui-record / OBS свой экран
- **В** = AI-gen b-roll → Higgsfield с нашим продуктом
- **Г** = Vendor launch material → public source вендора
- **Д** = Talking head → твой
```

### Шаг 5: Если Тип 2 — вырезать clean UI cuts

Определить координаты PIP face cam:
- Открыть кадр с PIP, посмотреть где лицо
- На 1080x1920 обычно face PIP занимает нижние 800-1000 px
- Crop сверху: `crop=1080:1100:0:0` или подобное

Найти transition фреймы где автор переключается между PIP и full talking head:
- Просмотр кадров вокруг ожидаемой границы (на этот случай иногда extract 4fps для точности)
- Границы НЕ круглыми секундами, а на конкретных переходах

Cut + verify:
```bash
ffmpeg -y -ss <start> -i source.mp4 -t <dur> -an \
  -vf "crop=1080:1100:0:0" -c:v libx264 -crf 18 \
  $OUT/clean_<segment>.mp4

# Verify через grid - убедиться что лица нет
ffmpeg -y -i $OUT/clean_<segment>.mp4 \
  -vf "fps=3,scale=240:244,tile=3x3:padding=4:color=white" \
  $OUT/verify_<segment>.jpg

# Read verify_<segment>.jpg как изображение и описать словами что вижу
```

### Шаг 6: Если Тип 1 — план recreate

Для каждой секции категории А (Mock):
- spec hyperframes/HTML composition с нашими данными вместо данных автора
- **Перед началом** — Read реального скриншота продукта (GitHub repo / Cursor IDE / n8n editor) через WebFetch product docs/landing. Выписать ВСЕ visible UI элементы по [[feedback-mock-realism-standard]]
- Сохранить spec в `$INGEST/replicate-plan/<segment>.md`
- **Делать ВСЕ сегменты** — не пропускать "для экономии" ([[feedback-no-skipping-segments]])

Для категории В (AI-gen b-roll):
- prompt для Higgsfield/Sora с нашим продуктом
- референс кадра автора как visual reference

### Шаг 7: Self-grade каждого mock'а (обязательно)

После каждого render — **обязательный** проход 10-point checklist перед переходом к следующему mock'у:

```bash
# Side-by-side comparison
ffmpeg -y -ss <orig_ts> -i $INGEST/*.mp4 -vframes 1 -vf "scale=540:960" /tmp/cmp_orig.jpg
ffmpeg -y -ss <our_ts> -i $MOCK/renders/*.mp4 -vframes 1 -vf "scale=540:960" /tmp/cmp_ours.jpg
ffmpeg -y -i /tmp/cmp_orig.jpg -i /tmp/cmp_ours.jpg -filter_complex hstack /tmp/cmp_side.jpg

# Read /tmp/cmp_side.jpg как изображение, описать различия словами
```

**v4.0 5-level review** — authority-grounded framework, REPLACES invented system with arbitrary weights.

Reference: catalog v4.0 Section 9 + authority sources (WCAG 2.1 / Nielsen Norman Group / Disney 12 / Material motion tokens / PDCA cycle).

### Level 1 — WCAG 2.1 compliance (PASS/FAIL gate, mandatory)

**Hard pass/fail criteria — block render если fails:**

| Criterion | Spec verbatim | Pass condition |
|---|---|---|
| 2.3.1 Three Flashes | *"No more than three flashes within any one-second period"* + area ≤0.006 steradians | No flash sequence violates |
| 2.3.3 prefers-reduced-motion | Motion animation can be disabled — vestibular harm protection | Embed has C39/SCR40 OR static-frame alt exists |
| 2.2.2 Pause/Stop/Hide (embed parallel content) | Mechanism to pause/stop motion >5s | Block ≤5s autoplay OR embed has pause control |

**Output:** PASS / FAIL. Any FAIL = block render. No score.

### Level 2 — Disney 12 + Material token conformance (quality scoring, no weights)

**8 sub-checks:**

- **2A. Anticipation** (Disney Principle 2): hook motions >200ms have wind-up phase
- **2B. Slow In/Out** (Principle 6): linear easing only где meaning (progress bars / loops). Else use Material easing tokens.
- **2C. Follow-Through** (Principle 5): secondary elements lag 50-100ms behind primary
- **2D. Arc** (Principle 7): translate >100px uses arc, not straight line
- **2E. Staging** (Principle 3): 1 dominant action per beat
- **2F. Timing** (Principle 9): durations from Material 16-token ladder (50ms-1000ms), not arbitrary
- **2G. Token conformance**: easing/duration/spring values from `<style_block>` (v2.0 prompt), no inline magic numbers
- **2H. Animation Bootcamp principles declared**: ≥3 для Tier 1 / ≥2 Tier 2 / ≥1 Tier 3 (см. catalog v4.0 Section 4)

**Output:** count sub-checks passed. 6+/8 = high quality, 4-5 = acceptable, ≤3 = re-iterate.

### Level 3 — NN/g motion heuristics (quality scoring, no weights)

**8 sub-checks (motion-relevant subset из 10 Nielsen heuristics + 4-question framework + duration article):**

- **3A. Visibility of System Status** (Heuristic #1): motion communicates state change clearly
- **3B. Consistency and Standards** (Heuristic #4): same easing/duration tokens within ролик, не mixed
- **3C. Aesthetic and Minimalist** (Heuristic #8): no gratuitous motion — *"every extra unit competes with relevant"*
- **3D. NN/g 4-question framework**:
  - User Attention Context (где user's focus when animation occurs)
  - Animation Goal (Attract / Show continuity / Indicate relationship)
  - Frequency (repetitive = roadblock)
  - Trigger Mechanics (direct vs indirect)
- **3E. Linear motion check** verbatim NN/g: *"Completely linear motion looks weird and unnatural to users."* Fail если linear где не meaning.
- **3F. Asymmetric entrance/exit**: ratio 1.2-1.5x entrance:exit duration (verbatim NN/g)
- **3G. Response time threshold**: motion start ≤100ms after trigger (0.1s NN/g hard threshold для direct manipulation)
- **3H. Animation category declared** (3 NN/g): Attention & Explanation / Aesthetic Enhancement / Brand Signaling

**Output:** count sub-checks passed. 6+/8 high, 4-5 acceptable, ≤3 re-iterate.

### Level 4 — Reference Fidelity (empirical measurement, NO self-eval)

REPLACES v3 subjective "Reference Fidelity 0-100" rating. [[feedback-self-eval-not-qa]] memory enforces — agent self-eval banned, visual verification mandatory.

**Protocol:**

```bash
REF=$INGEST/*.mp4
CLONE=$MOCK/renders/*.mp4
OUT=/tmp/L4-$(basename $MOCK)
mkdir -p $OUT

# Extract sync frames at 5-6 timestamps
for t in 1 6 12 18 24 30; do
  ffmpeg -y -ss $t -i $REF -frames:v 1 -vf "scale=540:960" $OUT/ref_t${t}.jpg
  ffmpeg -y -ss $t -i $CLONE -frames:v 1 -vf "scale=540:960" $OUT/clone_t${t}.jpg
  ffmpeg -y -i $OUT/ref_t${t}.jpg -i $OUT/clone_t${t}.jpg -filter_complex "[0][1]hstack" $OUT/pair_t${t}.jpg
done

# Tile vertical grid
ls $OUT/pair_t*.jpg | sort -V | awk '{print "file \047" $0 "\047"}' > $OUT/list.txt
ffmpeg -y -f concat -safe 0 -i $OUT/list.txt -vf "tile=1x6:padding=4:color=white" -update 1 $OUT/grid.jpg

# Open $OUT/grid.jpg через Read tool — describe specific deltas verbatim
```

**Output:** structured delta list (no score):
- DELTA 1: at t=Xs, REF shows [X], CLONE shows [Y] — missing element / different color / different timing
- DELTA 2: ...etc

Repeat для каждого significant timestamp. If all deltas minor/stylistic → ship. If structural deltas → Level 5 iteration.

### Level 5 — PDCA iteration loop (process discipline)

**Plan-Do-Check-Act (industrial QA cycle, replaces invented "Iteration Loop"):**

- **Plan:** define what v(N+1) will fix based on Level 4 deltas
- **Do:** rewrite prompt v(N+1) targeting specific deltas (use v2.0 prompt template — см. motion-storyboard SKILL.md)
- **Check:** re-render + re-Level-4 against reference
- **Act:** if deltas closed → ship. If not → another P-D-C-A cycle.

**Termination conditions:**
- Level 1 all PASS (mandatory)
- Level 2 ≥6/8 sub-checks
- Level 3 ≥6/8 sub-checks
- Level 4 deltas all minor / stylistic (no structural deltas)
- Max 5 P-D-C-A cycles (автор time budget protection)

**No composite score. No weighted formula. Levels checked sequentially:**
1. Level 1 PASS/FAIL hard gate
2. Level 2 + 3 sub-check counts reported transparently
3. Level 4 delta list transparent
4. Level 5 cycle counter (≤5)

Anthropic best practice: *"be concrete about where the bar is rather than using qualitative terms like 'important'"* — no qualitative composite score, only specific criteria with explicit thresholds.

### Parallel execution для >5 mocks

При ингесте с большим количеством сегментов — spawn N parallel agents через `Agent` tool, по одному per-mock. Каждый agent делает sequential 5-level review своего mock. Main agent делает только concat финального timeline.

**Per-agent prompt template:** "Take mock spec X (category Y), do sequential L1→L2→L3→L4 review with iteration loops. Save grade card to /tmp/grades/<mock>.md. Return rendered mp4 path + done/limitation status."

## Output

```
<ingest-folder>/
  ui-inventory.md          # таблица секций + классификация
  clean-cuts/              # только для Тип 2
    clean_<segment>.mp4
    verify_<segment>.jpg
  replicate-plan/          # только для Тип 1
    <segment>.md           # spec recreate каждой секции
```

## Anti-patterns (НЕ делать)

1. **ffmpeg trim наугад** без покадрового анализа — даст куски с лицами
2. **Открыть автору montage без своего описания** — системная ошибка №1
3. **Использовать grid.jpg от ingest-reel** (9 кадров на весь ролик) как основу — слишком грубо, нужно 2fps
4. **Cut круглыми секундами** на Тип 2 — попадёшь на transition в full talking head
5. **Запустить replicate-reel** без классификации Тип 1/Тип 2 — композиция не получится

## Связано

- `ingest-reel` — производит исходник для inventory
- `motion-storyboard` — производит motion plan per-segment (используется как primary input для Level 2F+2G review)
- `replicate-reel` — потребляет ui-inventory.md + motion-storyboard.md для адаптации скрипта и сборки HF composition
- `hyperframes` — recreate Mock-up секций для Тип 1
- `ui-record` — захват Public UI для категории Б
- `higgsfield-generate` — AI-gen b-roll для категории В
- Motion catalog: `~/.business/growth/motion-vocabulary.md` (single source of truth для 2F conformance)
- Motion blocks library: `~/.business/growth/assets/motion-blocks/` (single source of truth для 2G fidelity)
- Memory `project-ui-inventory-method` — фиксация метода