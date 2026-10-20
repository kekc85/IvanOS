# Tune COMMENTS_THRESHOLD after first run

Делается после первого реального прогона. Цель - найти sweet spot между signal и noise.

## Heuristic table

| Finalists в digest | Action |
|---|---|
| 0 | Threshold СЛИШКОМ высокий → reduce 50% |
| 1-3 | Threshold высокий → reduce 25% |
| **5-15** | **Sweet spot** - keep |
| 16-30 | Threshold низковат → increase 50% |
| 30+ | Threshold СЛИШКОМ низкий → increase 100% |

Цель: 5-15 финалистов в день - автор успевает ревьюить за 5-10 минут.

## Walkthrough (первый run)

1. Open `~/Desktop/ig-digest/{today}.md`
2. Count finalists
3. Match таблице выше
4. Edit `~/.claude/skills/ig-carousel-radar/config.md` → `comments_threshold: <new>`
5. Re-run tomorrow → reassess

## По нишам (empirical baseline)

| Niche | Reasonable threshold (comments) |
|---|---|
| AI tools / vibecoding EN | 300-800 |
| Indie hacker / solopreneur EN | 200-500 |
| Marketing / growth EN | 500-1500 |
| Lifestyle / fitness (если расширишь) | 1000-3000 |

Стартовое значение `500` подходит для AI / vibecoding нити в EN рынке.

## Long-term

После 2 недель → собрать distribution. Если cosmetics - fine. Если volume drifts (IG алгоритм меняет engagement) - re-tune.

Roadmap v1.3 - auto-tune от 7-day rolling median (не делается в v1).

## Alt-axis tuning

Если comments threshold не помогает (например AI рынок mass posting):

- Подкрутить `likes_threshold` (добавить в filter pipeline)
- Подкрутить `engagement_ratio` (comments/likes ≥ 5%)
- Сократить `recency_days: 3` (агрессивнее - только последние 3 дня)
- Сократить `watchlist_posts_per_profile: 5` (только последние 5 у каждого)

Эти knobs появятся в config v1.1 если в v1 будет недостаточно.