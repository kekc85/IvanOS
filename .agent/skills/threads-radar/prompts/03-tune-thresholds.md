# 03 - Tune thresholds (после первого прогона)

Правится в `config.md` -> синхронизируй с константами `FILTER` в `scripts/radar.py`.

## ENGAGEMENT_THRESHOLD (default 300 = likes + replies)
- Первый прогон: поставь `100` -> сколько finalists?
  - `>30` -> подними (500-1000).
  - `<5` -> опусти или расширь watchlist/keywords.
- Threads-engagement ниже IG-комментов в абсолюте; калибруй по реальной volume ниши.

## recency_days (default 7)
- Хочешь только свежак -> `3`. Шире охват -> `14`.

## Anti-bot (404-decoy / GraphQL empty)
Threads отдаёт фейк-404 ("Not all who wander are lost") и пустой GraphQL при быстрых headless-хитах. Если в логе много decoy/empty:
- `scroll_delay_ms: 4000`, `between_*_delay_ms: 6000`, `post_settle_ms: 10000`.
- Прогоняй реже (1 раз/день), не подряд.
- Не гоняй параллельно — только sequential.

## Metrics-unknown leads
Если GraphQL пуст, DOM-fallback даёт URL/дату/текст, но БЕЗ счётчиков. Такие посты идут в digest как "metrics-unknown (DOM-only lead)" — НЕ отсекаются порогом, но сортируются после метрицированных. Открой URL для точных метрик. Чтобы метрики стабильно подтягивались — снижай anti-bot нагрузку (см. выше), GraphQL отдаётся когда сессия не throttled.

## Watchlist drift
Часть X-хэндлов не имеет Threads-профиля -> 404 (норма, не баг). Quarterly чисти `threads-watchlist.yml`.