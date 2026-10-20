# Voice Signal Discovery (shared, v1.0)

> Shared dependency для всех content-factory skills. Replaces «требуй у user corpus» pattern на automated WebFetch discovery 4 sources. Created 2026-05-28 after incident («simulated review + corpus dependency») в longform.

## Кто использует

- `longform` (newsletter / blog / LinkedIn article)
- `post` (TG / LinkedIn post)
- `email` (Kit / Beehiiv)
- `tweet` (X / Threads)
- `carousel` (IG / LinkedIn carousel)
- `single-image` (X / LinkedIn / TG image post)
- `video` (Reels / Shorts / TikTok / YouTube script)
- `bot-message` (TG-бот push)

## Главный принцип

Voice signal = **public information** которое skill discovers сам. User ничего не предоставляет. Никаких STOP PIPELINE на missing corpus.

## 4 sources voice signal

### Source 1: Author's public channels (50% weight)

Для автора (default):
- TG `<твой-tg-канал>` — verbatim posts
- LinkedIn `https://www.<твой-linkedin>/recent-activity/posts/`
- Blog `<твой-домен>/blog` (если public)
- YouTube transcripts через `youtube-transcript` skill

### Source 2: Reference creators newsletters (30% weight)

EN reference (для longform / email / post EN):
- Dan Koe `https://thedankoe.com/letters/`
- Justin Welsh `https://www.justinwelsh.me/articles`
- Sahil Bloom `https://www.sahilbloom.com/newsletter`
- Rowan Cheung `https://www.therundown.ai/p`

Format-specific:
- Tweet patterns — Alex Hormozi / Naval / Iman Gadzhi tweets
- Carousel patterns — Jack Butcher / Justin Welsh carousels
- Video patterns — Riley Brown / Nate Herk / Chris Cordero
- Email patterns — Welsh nurture / Hormozi launch / Cheung daily

### Source 3: RU competitors (20% weight, language=ru)

- автор Замесин `https://zamesin.ru`
- Михаил Палий, Алексей Ширяев TG (если public)

### Source 4: Memory lexicon (fixed 20% fallback)

Always loaded:
- `~/.claude/projects/<твой-проект>/memory/user_lexicon.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE-2026-05-27.md`

## Discovery flow

```
START Voice Signal Discovery
│
├─ Check ~/.claude/skills/_shared/cache/voice-signal-*.md (TTL 7 days)
│   └─ если найдено ≥3 fresh files → use cached + skip WebFetch
│
├─ Parallel WebFetch Source 1 (author public channels)
├─ Parallel WebFetch Source 2 (reference creators per format)
├─ Parallel WebFetch Source 3 (RU competitors if language=ru)
│
├─ Always load Source 4 (memory lexicon)
│
└─ Aggregate Voice Fidelity Score (0-100):
    score = Σ (source_weight × source_quality / 100)
    
    ≥70 = PASS → proceed
    40-69 = WARN → proceed + warning в output
    <40 = LOW SIGNAL → proceed + suggestion --refresh-voice-signal
    
    NEVER STOP PIPELINE.
```

## Shared cache

```
~/.claude/skills/_shared/cache/
├── voice-signal-<date>.md
├── voice-signal-author-linkedin-<date>.md
├── voice-signal-reference-dan-koe-<date>.md
├── voice-signal-reference-welsh-<date>.md
├── voice-signal-reference-bloom-<date>.md
├── voice-signal-ru-zamesin-<date>.md
└── ...
```

TTL: 7 days. Все content-factory skills используют ту же кэш-папку.

## Failure modes

| Failure | Action |
|---|---|
| WebFetch 429 | Wait 5s + retry once. Skip if fails. |
| WebFetch 403 | Skip + log |
| 0 posts returned | Skip + use next |
| All Source 1-3 fail | Source 4 only. Score capped at 50. Continue. |

## Output schema (для всех skills)

```yaml
voice_signal:
  sources_used: [<list>]
  total_corpus_words: <N>
  voice_fidelity_score: <0-100>
  recommendation: PASS | WARN | LOW
  cached_files: [<list>]
  warnings: [<list>]
```

Pass forward в каждом skill's write step (Pass 2 voice injection).

## Per-skill format mapping

Каждый content-factory skill использует тот же discovery но fetches DIFFERENT reference creators based on format:

| Skill | Format-specific reference focus |
|---|---|
| longform | Dan Koe / Welsh / Bloom newsletters |
| post | Welsh LinkedIn / Lara Acosta / Matt Gray posts |
| email | Welsh nurture / Hormozi launch / Cheung daily |
| tweet | Naval / Hormozi / Iman X bank |
| carousel | Butcher / Welsh carousels |
| single-image | Butcher concept diagrams |
| video | Riley Brown / Nate Herk / Cordero scripts |
| bot-message | (Source 1 only - personal bot pushes — нет публичных reference) |

## Memory cross-refs

- — never delegate to user
- — skill responsible
- — WebFetch public = standard
- — driver rule
- — Source 1 primary
---

## v1.0.1 hardened voice rules (added 2026-05-28 после авторской критики)

### Rule 1: No period at end of paragraphs

Hard regex gate в Pass 1 review всех content skills:

```
для каждого \n\n-разделённого абзаца:
  last_char = paragraph.strip()[-1]
  if last_char == "." (bare period, не «...» / ! / ? / emoji / :):
    FAIL → remove trailing period
```

Источник:. Validated на 10 cached TG posts (10/10 НЕ заканчиваются точкой).

### Rule 2: TG markers not universal

Markers «Лол» / «Прёт» / «Бесит» / экстремальные emoji в опенерах:
- ✅ OK в TG-post / personal aside
- ❌ FAIL в newsletter opener / email subject / blog headline / sales content

Source — full catalog там.

Context-aware application в Pass 2 voice injection:
- format=newsletter / blog / email / sales → filter OUT tg_aside markers в openers
- format=tg / personal_story → apply все markers OK
