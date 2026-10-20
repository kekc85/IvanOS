# 00-voice-signal-discovery

> Replaces «требуй corpus у user» pattern из 03-write.md Pass 0. Runs автоматически перед `03-write.md` Pass 1. Discovers voice signal через 4 public sources (см. `references/voice-signal-sources.md`).

## Когда запускается

- В начале `03-write.md` (перед Pass 0 mandatory reads)
- Если cache fresh (<7 days) - skip WebFetch, use cached
- Если cache stale или missing - full discovery
- При `/longform --refresh-voice-signal` - force re-discovery

## Шаги

### Шаг 1: Cache check

```bash
find ~/.claude/skills/longform/cache -name 'voice-signal-*.md' -mtime -7
```

Если ≥3 файлов found с total word count ≥10000 - use cached + skip к Step 5.

### Шаг 2: Source 1 - Author's public channels (parallel WebFetch)

Параллельный WebFetch:
- `<твой-tg-канал>` - public TG archive
- `https://www.<твой-linkedin>/recent-activity/posts/` - LinkedIn (если accessible)
- `<твой-домен>/blog` - personal blog (если есть)

Каждый response:
- Extract content
- Strip HTML / metadata
- Count words
- Save в `cache/voice-signal-author-<channel>-<YYYY-MM-DD>.md` со structure:

```markdown
# Voice Signal - author_<channel>
fetched_at: 2026-05-28T19:56:00Z
source_url: <URL>
word_count: <N>
post_count: <N>
quality_score: <0-100>

## Top patterns extracted
- <pattern 1>
- <pattern 2>

## Raw content
<full text>
```

### Шаг 3: Source 2 - Reference creators (parallel WebFetch)

Параллельный WebFetch:
- `https://thedankoe.com/letters/`
- `https://www.justinwelsh.me/articles`
- `https://www.sahilbloom.com/newsletter`

Из каждого extract 5 latest essay URLs → fetch каждый → save в cache.

### Шаг 4: Source 3 - RU competitors (parallel, language=ru only)

WebFetch:
- `https://zamesin.me`
- Other RU competitors из `.business/marketing/competitors.md`

### Шаг 5: Aggregate signal

```python
score = 0
sources = []

if Source1 quality > 0:
    contribution = Source1.weight * Source1.quality / 100
    score += contribution
    sources.append({"name": "author_*", "contribution": contribution})

if Source2 quality > 0:
    contribution = Source2.weight * Source2.quality / 100
    score += contribution
    sources.append(...)

if Source3 quality > 0 and language == "ru":
    contribution = Source3.weight * Source3.quality / 100
    score += contribution

# Source 4 always
score += 20  # fixed contribution from memory lexicon
sources.append({"name": "memory_lexicon", "contribution": 20})
```

### Шаг 6: Decision

| Score | Decision | Action |
|---|---|---|
| ≥70 | PASS - full voice fidelity | proceed to 03-write Pass 1 |
| 40-69 | WARN - degraded voice | proceed + warning в final output |
| <40 | LOW SIGNAL | proceed + suggestion `/longform --refresh-voice-signal` |

**NEVER STOP PIPELINE.** Always produce output с best available signal.

### Шаг 7: Output → 03-write.md

```yaml
voice_signal_discovery:
  sources_used: [<list>]
  total_corpus_words: <N>
  voice_fidelity_score: <0-100>
  recommendation: PASS | WARN | LOW
  cached_files: [<list>]
  warnings: [<list>]
```

## Failure modes

| Failure | Handling |
|---|---|
| WebFetch 429 | Wait 5s + retry once. Skip if retry fails. |
| WebFetch 403 | Skip + log |
| Channel returns 0 posts | Skip + use next |
| All Source 1-3 fail | Source 4 only. Score capped at 50. Continue. |
| Cache directory not writable | WebFetch без caching. Continue. |

## Memory cross-refs

- - never delegate to user
- - skill owns voice signal
- - WebFetch public = standard
- - Source 1