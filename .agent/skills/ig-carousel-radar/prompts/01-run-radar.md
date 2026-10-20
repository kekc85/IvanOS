# Алгоритм: run radar (one daily prog)

Триггер: `/radar` / `/carousel-radar` / "пройди по конкурентам IG" / cron 08:00.

## Pre-check (deterministic)

```bash
# Cookies exist + not stale (> 90 days old = re-export warning)
test -f ~/.business/processes/.ig-cookies.json && \
  python3 -c "import os, time; m=os.path.getmtime(os.path.expanduser('~/.business/processes/.ig-cookies.json')); age=(time.time()-m)/86400; print(f'cookie age: {age:.0f}d'); exit(0 if age<90 else 1)"

# Seed files exist
test -f ~/.business/growth/watchlist-en.yml && test -f ~/.business/growth/hashtags-en.yml

# Output dir exists
mkdir -p ~/Desktop/ig-digest/.thumbs
```

Если pre-check FAIL → switch to `prompts/02-setup-cookies.md` (авторский one-time setup).

## Run

```bash
cd ~/.claude/skills/ig-carousel-radar
python3 scripts/radar.py
```

(venv pre-installed с Playwright + pyyaml + Chromium. См. `prompts/02-setup-cookies.md` если venv отсутствует.)

Script делает:

1. Load config (`config.md`) + seed lists
2. Launch headless Chromium с loaded cookies
3. Run 3 mode параллельно (asyncio.gather):
   - Mode A: feed scroll
   - Mode B: watchlist sweep
   - Mode C: hashtag sweep
4. Merge candidates → filter pipeline:
   - type == carousel
   - age < recency_days
   - comments >= threshold
   - dedupe by URL
   - sort by comments DESC
5. Download slide-1 thumb per finalist → `~/Desktop/ig-digest/.thumbs/{shortcode}.jpg`
6. Write digest → `~/Desktop/ig-digest/{date}.md`
7. (Optional) TG push если `tg_push: true` в config

## Post-run

```bash
# Open digest — macOS: open · Windows: start "" · Linux: xdg-open · универсально: ~/.claude/skills/_shared/bin/open-file
open ~/Desktop/ig-digest/$(date +%Y-%m-%d).md
```

### MANDATORY: handoff финалистов в чат

После digest ОБЯЗАТЕЛЬНО принести финалистов в чат как actionable нумерованный список. НЕ закрывать на «digest opened», НЕ говорить «готово» / «закрыт» / «done». автор не пойдёт читать digest вручную — Claude приносит решения.

🔴🔴 **ФОРМАТ HANDOFF = ТАБЛИЦА (автор, обязательно).** Шорт-лист финалистов несём в чат ТОЛЬКО таблицей с фиксированными колонками. Перед выдачей пробить каждый shortcode через IG media API (`apifetch`-паттерн: shortcode→media_id→`/api/v1/media/{id}/info/` с куками + `x-ig-app-id`) и достать точные счётчики + `taken_at` (дата) + типы детей `carousel_media[].media_type` (1=фото, 2=видео) для колонки видео/фото. Колонки СТРОГО:

| № | Аккаунт | О чём карусель | Лайки | Комменты | Просмотры | Дата | Видео/Фото | Ссылка |
|---|---|---|---|---|---|---|---|---|

- **Просмотры** у фото-каруселей IG не отдаёт → ставить «n/a» (мерить по лайкам), у видео — реальное число если есть.
- **Видео/Фото** — «фото» если все дети media_type=1; «видео (X/N)» если есть видео-дети (X видео из N слайдов) → это сразу сигнал, что пойдёт по видео-ветке (`video_overlay`).
- **О чём** — суть в 5-10 слов на русском.
- Fable-карусели и уже-сделанное в таблицу НЕ включать (сказать одной строкой сколько отсеяно). Связано:,.

(легаси-формат строкой, НЕ использовать):
```
N. @handle (Xd, Y comments, ratio Z%) — суть карусели в 5-8 слов
   URL: instagram.com/p/<shortcode>/
```

Затем явный actionable prompt:

```
**Какие забираешь в контент-завод?** Дай номера через запятую (например, "1, 4, 7") и для каждого — downstream:
- **A** = `adaptation` (переписать carousel в твоём голосе + категории)
- **B** = `ingest-reel` (глубокий разбор поста под replication spec)
- **C** = `carousel` (build с нуля по той же big idea)
- **D** = save to bank (закинуть в `.business/marketing/content-banks/ig-radar-bank.md` для review позже)

Пример ответа: "1A, 4B, 7D" или "skip all".
```

После ответа автора — для каждого approved item запускать соответствующий downstream skill с URL карусели как input. Если "skip all" — записать в digest строку `# автор skipped all N финалистов 2026-MM-DD` и завершить.

### Track-record

Append run reflection per:
- feed candidates: N
- watchlist candidates: M
- hashtag candidates: K
- finalists: F
- approved by автор: A (из F)
- duration: Ts

## Error handling

| Error | Action |
|---|---|
| Cookie expired (login redirect) | Halt, prompt re-export per `prompts/02-setup-cookies.md` |
| IG rate-limit (429 / soft-block) | Halt, log, retry в next cron (24h cooldown) |
| Single profile 404 (deactivated) | Log warning, skip, continue |
| Selector broken (new IG HTML) | Halt, prompt maintenance update `scripts/radar.py` |
| 0 finalists после filter | Write digest с note "tune COMMENTS_THRESHOLD" + suggest value по `prompts/03-tune-thresholds.md` |

## What this does NOT do

Запреты per:
- НЕ выдумывает метрики если parse failed → skip post (не подставлять `comments: 0`)
- НЕ генерирует AI-rewrite caption → берёт первые N chars verbatim
- НЕ топик-классифицирует через LLM → фильтр уже на источнике
- НЕ скачивает все слайды → только slide-1 thumb