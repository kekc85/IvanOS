---
date: {{DATE}}
total_handles: {{TOTAL_HANDLES}}
handles_ok: {{HANDLES_OK}}
handles_failed: {{HANDLES_FAILED}}
total_reels_today: {{TOTAL_TODAY}}
top_n: {{TOP_N}}
generated_at: {{GENERATED_AT}}
---

# Competitors scan {{DATE}}

Топ-{{TOP_N}} роликов конкурентов опубликованных {{DATE}}, ранжированных по views.

## Errors

{{ERRORS_BLOCK}}

## Top-{{TOP_N}}

| # | Handle | Platform | Views | Likes | Headline (OCR) | URL |
|---|---|---|---|---|---|---|
{{TOP_TABLE}}

## Подробно

{{REELS_DETAILED}}

## Сырые данные

`~/.business/growth/competitors-scan/raw/{{DATE}}.jsonl` - все найденные ролики дня (не только top-N).

## Следующие шаги

- Прогнать топ через replicate-reel для отбора форматов под перегон
- Положить headline OCR в `~/.business/growth/hook-library/{{DATE}}.md` для viral hook update
- Удалить failed handles из watchlist если падают >7 дней подряд