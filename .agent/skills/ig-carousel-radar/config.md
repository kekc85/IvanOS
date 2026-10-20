# IG Carousel Radar - config

Portable configuration. Изменить значения здесь → script подхватит.

## paths

```yaml
watchlist: ~/.business/growth/watchlist-en.yml
hashtags: ~/.business/growth/hashtags-en.yml
clusters: ~/.business/growth/clusters-en.yml   # формат-фильтр на выходе (want/avoid/neutral)
ig_cookies: ~/.business/processes/.ig-cookies.json
output_dir: ~/.business/growth/ig-digest/
thumbs_dir: ~/.business/growth/ig-digest/.thumbs/
```

## discovery

```yaml
feed_scroll_screens: 50           # сколько экранов прокрутить в feed mode
watchlist_posts_per_profile: 10   # последние N постов / profile в watchlist mode
hashtag_posts_per_tag: 30         # сколько постов / hashtag (top + recent merged)
scroll_delay_ms: 1500             # delay между scroll (anti-bot)
between_profiles_delay_ms: 3000   # delay между profile visits
between_hashtags_delay_ms: 3000   # delay между hashtag visits
timeout_per_mode_sec: 600         # hard timeout per mode (10 min)
```

## filter

```yaml
recency_days: 7                   # age < N days
comments_threshold: 200 # tuned по решению автора (500 давал <5 finalists)
require_carousel: true            # type == carousel only
```

## clusters (формат-фильтр на выходе)

Второй слой релевантности: seed-листы фильтруют ТЕМУ на входе, кластеры — ФОРМАТ на выходе.
Полная таксономия живёт в `~/.business/growth/clusters-en.yml` (правится без кода).

```yaml
# в clusters-en.yml:
mode: drop_avoid    # drop_avoid = выкидывать avoid-формат | soft = только опускать вниз
# clusters: [{name, policy: want|avoid|neutral, keywords:[...]}]
# want   -> в топ выдачи (сейчас: tool-onboarding, build-walkthrough)
# avoid  -> выкинуть (сейчас: prompt-handout - "забери промпт", не цепляет)
# neutral-> оставить ниже want (всё не совпавшее = "other")
```

Тюнить: смотри блок «## Кластеры» в дайджесте после прогона → правь keywords в seed.
keyword = substring (lowercase); префикс `re:` = regex.

## notification

```yaml
tg_push: false                    # включить позже (v1.1)
tg_chat_id: ""                    # авторский personal chat id
tg_bot_token_env: TG_RADAR_TOKEN  # env var name для bot token (если включишь)
```

## output

```yaml
digest_filename_pattern: "{date}.md"   # date = YYYY-MM-DD
thumb_filename_pattern: "{shortcode}.jpg"
slide_preview_max_width: 600           # px, для readable preview
caption_preview_chars: 200             # первые N chars caption в digest
```

## reliability

```yaml
max_retries_per_profile: 2        # retry если IG throws temp error
fail_silently: true               # один профиль fail не валит весь run
log_path: ~/.business/growth/ig-radar.log
```

## Tuning hints

- **Первый прогон**: `comments_threshold: 100` → посмотри сколько finalists. Если >30 → подними threshold. Если <5 → опусти или добавь handles/hashtags
- **Anti-bot**: если IG flags account → `scroll_delay_ms: 3000`, `feed_scroll_screens: 20`
- **Cron timing**: 08:00 утра локального = свежий контент за US night (USA EN рынок)
