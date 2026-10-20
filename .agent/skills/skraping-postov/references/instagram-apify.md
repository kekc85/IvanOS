# Фаза 1. Instagram через Apify

Этот референс читается, когда в собираемом архиве есть Instagram. Два прохода (post-scraper + reel-scraper) обязательны в обоих режимах охвата (ретро и инкрементальный) — отличается только значение `onlyPostsNewerThan`.

## Шаг 1.1. Прогон `apify/instagram-post-scraper` (всё кроме шеров рилзов)

```python
input = {
    "username": ["<handle без @>"],
    "resultsType": "posts",
    "resultsLimit": 500,
    "onlyPostsNewerThan": f"{<число_дней_из_режима>} days",
    "addParentData": False
}
```

Где `<число_дней_из_режима>`:
- В ретро: значение, выбранное в Шаге 0.2 (дефолт 365 свой / 180 конкурент).
- В инкрементальном: дельта из Шага 0.1.

Запуск через `mcp__Apify__call-actor` с `async: true`. Получаешь `runId_post`.

Аналогично — `apify/instagram-reel-scraper` с `"includeSharesCount": true` для рилзов с шерами. Получаешь `runId_reel`.

Почему два прохода: рилзы без `includeSharesCount` дают заниженный ERV на 5–8 п.п. — без этого outlier-разметка по рилзам становится непредсказуемой.

## Шаг 1.2. Ожидание

Подожди 60–90 секунд (большинство аккаунтов отрабатывают за это время). В инкрементальном режиме — обычно быстрее (меньше данных).

Не дёргай `mcp__Apify__get-actor-run` — token-overflow на больших датасетах (см. Жёсткий принцип №6 в SKILL.md).

## Шаг 1.3. Фетч датасетов через прямой API

Через Python в bash:

```python
import urllib.request, json
url = f"https://api.apify.com/v2/actor-runs/{runId}/dataset/items?clean=1&format=json"
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())
```

Endpoint публичный — токен не нужен. Если run ещё не закончился — вернёт пустой массив, подожди ещё 30 секунд и повтори. Хелпер `fetch_dataset` с ретраями см. в `references/utilities.md`.

## Шаг 1.4. Маппинг IG → frontmatter

Объедини items из 1.1 и `instagram-reel-scraper` по `shortCode`. Для рилзов возьми `sharesCount` из reel-scraper-а, остальные поля — из post-scraper-а. Image/Sidecar без шеров → `shares: 0`.

| Поле frontmatter | Источник Apify |
|---|---|
| `id` | `shortCode` |
| `network` | `Instagram` |
| `type` | `Sidecar→карусель`, `Video→рилз`, `Image→пост` |
| `status` | `новый` |
| `url` | `url` |
| `caption` | `caption` (truncate_utf16 до 1990) |
| `recognized_text` | `''` (пусто — заполнит распознавалка) |
| `likes` | `likesCount` |
| `comments` | `commentsCount` |
| `shares` | `sharesCount` (только рилзы) или `0` |
| `viewers` | `videoViewCount` (только рилзы) или `0` |
| `published` | `timestamp[:10]` |
| `author` | handle (свой эксперт или конкурент) |
| `saves`, `reach`, `hypothesis` | пусто/0 |
| `scanned`, `updated` | сегодняшняя дата ISO |

Поле `published_tg` в IG-записях не пишем — оно бессмысленно для IG (база знаний парсит `published` без проблем).
