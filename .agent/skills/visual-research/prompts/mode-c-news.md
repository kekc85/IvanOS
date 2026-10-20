# Mode C — news + visuals research для контент-плана

## Input

- `<topic>` (например "AI", "OpenAI launches", "Anthropic Claude")
- `<window>` опционально (today / 7d / 30d, default = 7d)
- `<count>` опционально (default = 5 top news items)

## Output

`~/Desktop/visual-research/<topic-slug>-news-week-<NN>-<YYYY-MM-DD>/` с:
- `summary.md` — топ-N новостей + headline + source + suggested content angle
- `news-<N>-<outlet>.png` — screenshot каждой news article
- `news-<N>-visual.{png,jpg}` — visual associated with each (если есть в article)
- `README.md` per [[readme-template]] adapted для news mode

## Workflow

### Step 1: Topic + window normalization

- Topic как user typed it
- Window → date range:
  - `today` → today
  - `7d` / "неделя" → last 7 days
  - `30d` / "месяц" → last 30 days

### Step 2: Setup output folder

```bash
slug=$(echo "<topic>" | tr ' ' '-' | tr 'A-ZА-Я' 'a-zа-я')
week=$(date +%V)
date=$(date +%Y-%m-%d)
mkdir -p ~/Desktop/visual-research/${slug}-news-week-${week}-${date}
```

### Step 3: News search

Использовать WebSearch с date constraint:
```
Query: <topic> after:<YYYY-MM-DD>
```

или Google News:
```
mcp__playwright__browser_navigate → 
  https://news.google.com/search?q=<URL_encoded_topic>&hl=en
```

Screenshot news grid:
```
<slug>-news-grid.png
```

### Step 4: Pick top-N headlines

Critère отбора:
- Recency: внутри window
- Source quality: TechCrunch / Verge / Bloomberg / Reuters / Wired > random blog
- Topical relevance: высокий sigma от centroid topic
- Visual potential: статья с фото > чистый текст

### Step 5: Per-headline fetch

Для каждой из top-N:

1. **Navigate** к article URL
2. **Screenshot viewport** как `news-<N>-<outlet>.png`
3. **WebFetch** content → text summary
4. **Extract visual** из article если present:
   - `browser_evaluate` найти hero image URL
   - `curl` download как `news-<N>-visual.jpg`

### Step 6: Write summary.md

Структура:
```markdown
# News digest: <topic> — week <NN> (<YYYY-MM-DD>)

## Item 1: <headline>
- **Source:** <outlet> + URL
- **Date:** YYYY-MM-DD
- **Summary:** <2-3 sentence WebFetch summary>
- **Visual:** news-1-visual.jpg (if available) — <license note>
- **Why it matters for content:** <one-liner>
- **Suggested angle (single-image / carousel / video):** 
  - Single-image: <hook + caption direction>
  - Carousel: <3-slide structure idea>
  - Video: <30-sec script outline>

## Item 2: ...

## Cross-cutting themes
- Theme A: <pattern across items>
- Theme B: ...

## Weekly recommendation
<which item is the strongest content opportunity + why>
```

### Step 7: Write README.md

Adapted для news mode — per [[readme-template]] но с дополнительными секциями:
- News digest metadata
- Per-item license breakdown
- Suggested content production order

### Step 8: Open + report

```bash
# macOS: open · Windows: start "" · Linux: xdg-open · универсально: ~/.claude/skills/_shared/bin/open-file
open ~/Desktop/visual-research/<slug>-news-week-<NN>-<date>/
```

Report:
- Папка открыта
- Топ-3 рекомендации для контент-плана (тема + angle + visual)
- Quick path: «следующий шаг — `/single-image` с темой из item N»

### Step 9: Close browser

## Anti-patterns

- Не миксовать topics — один topic per run
- Не вытягивать paywalled articles — если paywall hit, skip и note в summary
- Не давать "viral guaranteed" claims в suggested angles
- Не отдавать AI-generated hero images как "news photo" если article их использует — пометить «AI-generated» в README

## Integration с другими skills

После Mode C run — natural next steps:
1. `single-image` с item N → создать пост из angle suggestion
2. `carousel` с item N → 8-slide breakdown
3. `video` с item N → script + production handoff
4. `tweet` с темой digest → spiky-one-liner или thread

Подсказывать эти next steps в финальном report.