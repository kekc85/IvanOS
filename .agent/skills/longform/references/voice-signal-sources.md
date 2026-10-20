# Voice Signal Sources (automated discovery)

> Replaces «user must provide corpus» pattern. Skill сам discovers voice signal через 4 sources в order приоритета. Cache в `cache/voice-signal-<source>-<YYYY-MM-DD>.md` на 7 дней. Created 2026-05-28 after incident «требовал у user corpus».

## Принцип

Voice signal = **public information** которое skill discovers сам через WebFetch. User ничего не предоставляет. Если хотя бы один source returns достаточный signal - pipeline continues с указанной voice fidelity score.

## 4 sources voice signal

### Source 1: Author's public channels (highest fidelity, 50% weight)

Для автора (default config):

| Channel | URL | Content | Weight |
|---|---|---|---|
| Personal blog | `<твой-домен>/blog` (если public posts) | longform | 40% |
| TG канал | `<твой-tg-канал>` | posts (короткие, true voice) | 30% |
| LinkedIn | `https://www.<твой-linkedin>/recent-activity/posts/` | posts | 20% |
| YouTube | transcripts через `youtube-transcript` skill | speaking voice | 10% |

WebFetch URL → extract последние 10-20 публикаций → save в cache → use as primary signal.

### Source 2: Reference creators newsletter archives (30% weight)

Top EN reference creators в нише soloprenuership / content factory / AI marketing:

| Creator | URL |
|---|---|
| Dan Koe | `https://thedankoe.com/letters/` |
| Justin Welsh | `https://www.justinwelsh.me/articles` |
| Sahil Bloom | `https://www.sahilbloom.com/newsletter` |
| Rowan Cheung | `https://www.therundown.ai/p` |
| Tim Ferriss | `https://tim.blog` |
| Alex Finn | LinkedIn `linkedin.com/in/alex-finn-ai/recent-activity/posts/` |

Discovery: WebFetch URL → extract 5 latest essays each → save в cache → use для structure / headline / hook patterns (не для voice replication).

### Source 3: RU competitors blogs (20% weight, language=ru only)

| Creator | URL |
|---|---|
| автор Замесин | `https://zamesin.me` |
| Михаил Палий | TG public archive если есть |
| Дарья Афонина | TG public archive |
| Алексей Ширяев | TG public archive |

Discovery: WebFetch → save в cache → use для RU structure / RU lexicon patterns.

### Source 4: Memory lexicon (fallback, fixed 20% weight)

Always loaded:
- `~/.claude/projects/<твой-проект>/memory/user_lexicon.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE-2026-05-27.md`
- `~/.claude/skills/post/references/_voice-TEMPLATE.md`

Voice Fidelity Score capped at 50/100 при использовании только Source 4.

## Discovery flow

```
START Voice Fidelity Discovery
│
├─ Check cache/voice-signal-*.md (modified < 7 days ago)
│   └─ if found → use cached + skip WebFetch
│
├─ Source 1 (parallel WebFetch all author channels)
│   ├─ fetch each
│   ├─ extract content
│   ├─ save cache/voice-signal-author-<channel>-<date>.md
│   └─ compute quality score
│
├─ Source 2 (parallel WebFetch top 3-5 reference creators)
│
├─ Source 3 (only if language=ru, parallel WebFetch top 3)
│
├─ Source 4 (always loaded from local memory)
│
└─ Aggregate Voice Fidelity Score:
    Score = Σ (source_weight × source_quality / 100)
    
    Threshold: ≥70 = PASS, 40-69 = WARN, <40 = LOW SIGNAL
    
    NEVER STOP PIPELINE. Always produce output.
```

## Caching

```
~/.claude/skills/longform/cache/
├── voice-signal-2026-05-28.md
├── voice-signal-author-blog-2026-05-28.md
├── voice-signal-reference-dan-koe-2026-05-28.md
├── voice-signal-reference-welsh-2026-05-28.md
├── voice-signal-ru-zamesin-2026-05-28.md
└── ...
```

TTL 7 days. Refresh: `/longform --refresh-voice-signal` или auto via cron.

## Failure handling

| Failure | Action |
|---|---|
| WebFetch 429 (rate limit) | Wait 5s + retry once. If fails - skip source. |
| WebFetch 403 (blocked) | Skip + log |
| Channel returns 0 posts | Skip + use next |
| All Source 1-3 fail | Fall back на Source 4 only. Score capped at 50. Continue. |

## Output schema

```yaml
voice_signal:
  sources_used:
    - {name: "author_tg", word_count: 8000, quality: 75, weight: 30, contribution: 22.5}
    - {name: "reference_dan_koe", word_count: 12000, quality: 90, weight: 15, contribution: 13.5}
    - {name: "reference_welsh", word_count: 9000, quality: 90, weight: 15, contribution: 13.5}
    - {name: "memory_lexicon", word_count: "loaded", quality: 100, weight: 20, contribution: 20}
  total_corpus_words: 29000
  voice_fidelity_score: 69.5
  recommendation: WARN (40-69 range)
  cached_files: [<list>]
  warnings: ["LinkedIn fetch failed (403)", "blog returned 0 posts (not yet published)"]
```

Pass forward в `03-write.md` Pass 2 voice injection.

## Memory cross-refs

- - public sources = standard practice
- - never delegate discovery to user
- - skill responsible for voice signal
- - Source 1 primary