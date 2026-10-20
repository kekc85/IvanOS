---
name: competitors-daily-scan
description: Daily scan конкурентов content factory. Принимает watchlist handles (Нельзяграм / TikTok / YouTube Shorts), достаёт ролики опубликованные сегодня, ранжирует по virality (views/likes), отбирает топ-N и прогоняет через ingest-reel (yt-dlp + Whisper транскрипт + кадры + OCR хедлайна). Output - сводная карточка дня в `~/.business/growth/competitors-scan/YYYY-MM-DD.md`. Триггерится на `/scan`, `/competitors-scan`, или фразы «пройдись по конкурентам», «что сегодня вышло у конкурентов», «дайджест конкурентов за сегодня». НЕ требует авторизации - публичные профили + анонимная сессия. Ноль платных API. НЕ для Telegram-каналов, недельных смыслов рынка и чужих продающих событий - это `konkurent-radar`.
allowed-tools: Bash, Read, Write, Edit, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_close
version: "1.0"
created: 2026-05-23
last_reviewed: 2026-05-23
review_deps_every: 2 months
---

# competitors-daily-scan - watchlist → топ роликов дня

Discovery-надстройка над `ingest-reel`. Ежедневный пайплайн «зашёл на 20-30 конкурентов, отобрал самое виральное за сегодня, получил готовые карточки с транскриптами и хедлайнами».

## Когда триггерить

### Daily mode (по умолчанию)
- `/scan` или `/competitors-scan` от пользователя
- Фразы: «пройдись по конкурентам», «что сегодня вышло», «дайджест за сегодня», «топ конкурентов сегодня»
- При утреннем cron-сценарии (через `/schedule competitors-daily-scan daily 09:00`)

### Weekly-digest mode (NEW 2026-05-28, инспирирован SOLO svyortka-analitik-konkurentov)
- `/scan --weekly` или `/competitors-scan --weekly`
- Фразы: «недельный дайджест конкурентов», «свёртка конкурентов за неделю», «кросс-паттерны конкурентов», «что у нас по конкурентам в сводном виде»

Weekly-digest агрегирует 7 предыдущих daily-cards (`~/.business/growth/competitors-scan/YYYY-MM-DD.md` за 7 дней) в один файл `~/.business/growth/competitors-scan/weekly-YYYY-WNN.md` с разделами:
- **Кросс-паттерны** (что работает у ≥2 конкурентов за неделю — формат / hook-pattern / темы)
- **Антипаттерны** (что точно не работает — низкие views у нескольких)
- **Точки дифференциации** (уникальные ходы одного конкурента которые выглядят системными)
- **Топ-3 ролика недели** (с метриками + хедлайнами)
- **По каждому конкуренту 2-3 наблюдения** (wikilinks-каскад на daily-cards)

Принцип ≥2 конкурента = pattern, 1 конкурент = точка дифференциации (от Алекса svyortka).

## Что НЕ делать

- Не запрашивать у пользователя его Нельзяграм/TikTok/YouTube креды. Discovery работает анонимно.
- Не использовать Apify или другие платные парсеры. Ноль платных API в этом skill.
- Не парсить более 5 платформ параллельно (rate limit risk на твоём IP)
- Не качать полные MP4 на discovery шаге. Только metadata.
- Не игнорировать ошибки yt-dlp на Instagram (он там сломан, fallback на playwright обязателен).

## Архитектура - 3 канала discovery

```
┌──────────────────────────────────────────────────────────────┐
│  [W] Watchlist scan - известные authors из watchlist.md      │
│  [F] Feed scan      - залогиненный Instagram feed <твой-хэндл> │
│  [D] Manual drop    - автор кидает URL в чат (always works)  │
└──────────────────────────────────────────────────────────────┘
   ↓ JSONL merge (все три источника склеиваются)
[1] Discovery   - TikTok/YouTube из watchlist: scripts/discover.sh (yt-dlp --flat-playlist)
                - Instagram из watchlist: playwright (анонимно или с cookies)
                - Feed scan: playwright с cookies <твой-хэндл> → scroll → parse reels
                - Manual drop: URLs из чата
   ↓ JSONL { url, source, platform, handle, upload_date, view_count }
[2] Filter      - filter-and-rank.sh: date window (today / 7d) + views threshold + dedupe
   ↓
[3] Niche relevance - Claude в сессии (0 cost): caption+transcript+keywords-hint → relevant/no/outlier
   ↓
[4] Top-N       - sort by views, take top N
[5] Ingest+OCR  - ingest-reel для каждого + multimodal Read frames/f_001.jpg для хедлайна
[6] Card        - сборка ~/.business/growth/competitors-scan/YYYY-MM-DD.md
[7] Add prompt  - новые uploaders из feed/drop не в watchlist → ask автор добавить (см. Канал 2 inline add)
```

## Входы

- `watchlist` - путь к MD-файлу со списком handles. Дефолт: `~/.business/growth/competitors-watchlist.md`. Формат - по строке: `@handle PLATFORM` где PLATFORM ∈ {instagram, tiktok, youtube}. Комментарии `#` игнорируются.
- `top_n` - сколько роликов в финальной карточке. Дефолт 10.
- `date` - дата фильтра (YYYY-MM-DD). Дефолт today (МСК).

## Шаги выполнения для Claude

### Шаг 1 - Прочитать watchlist

```
Read $WATCHLIST → парсинг строк `@handle PLATFORM`
Группировка: { instagram: [...], tiktok: [...], youtube: [...] }
```

Если watchlist не передан и `~/.business/growth/competitors-watchlist.md` не существует - предложить пользователю создать его или передать handles inline. НЕ пытаться угадывать список.

### Шаг 2 - Discovery TikTok + YouTube (script path)

Для каждого `@handle` платформ tiktok / youtube:

```bash
~/.claude/skills/competitors-daily-scan/scripts/discover.sh "@handle" "<platform>" > /tmp/scan-{handle}.jsonl
```

Скрипт возвращает JSONL: `{"url":"...","platform":"...","handle":"...","upload_date":"YYYYMMDD","view_count":N}` по строке на ролик.

При warning от yt-dlp (impersonation, broken) - не игнорировать, добавить в errors[].

### Шаг 3 - Discovery Instagram (playwright path)

yt-dlp на Instagram-профилях сломан. Для каждого `@handle` платформы instagram:

```
1. mcp__playwright__browser_navigate to https://www.instagram.com/{handle}/
2. mcp__playwright__browser_snapshot → DOM accessibility tree
3. Из snapshot выдёргиваешь все ссылки вида /reel/{shortcode}/ и /p/{shortcode}/ (первые 12)
4. Формируешь полные URL: https://www.instagram.com/reel/{shortcode}/
5. Дату публикации С СНАПШОТА снять нельзя надёжно (Instagram скрывает или показывает relative).
   Поэтому для КАЖДОГО найденного reel URL вызываешь:
   yt-dlp --print "%(upload_date)s|%(view_count)s|%(like_count)s" --skip-download "$URL"
   (yt-dlp на ОТДЕЛЬНОМ ролике работает, ломается ТОЛЬКО на профилях)
```

После каждого Instagram handle закрывай browser-tab (`browser_close`) - не накапливай.

Если Instagram показывает login wall (snapshot пустой / содержит «Log in to see»):
- Сохрани в errors[] что нужен login для этого handle
- Продолжи следующих handles, не блокируйся

### Шаг 3.5 - Feed scan (Instagram logged-in)

Запускается **параллельно** watchlist scan (или вместо него если `--feed-only`). Цель - найти viral у micro-creators которых нет в watchlist.

**Setup (one-time, BYOA — ТВОЙ аккаунт):**

```
python3 ~/.claude/skills/_shared/bin/account.py onboard instagram
```

Открывает headed-браузер, ты логинишься в СВОЙ Instagram (включая 2FA), cookies сохраняются в `~/.business/processes/.ig-cookies.json` (chmod 600). Cookies живут месяцами пока не сделаешь logout. При expire (login wall в feed) - повтори онбординг. Feed scan идёт под ТВОИМ аккаунтом = риск бана на тебе, поэтому безопаснее основной watchlist scan (публичный ingest-reel/yt-dlp, аккаунт вне цепочки). Cookies автора в дистрибутив не кладутся.

**Daily flow:**

```
1. playwright_navigate https://instagram.com/ [с loaded cookies]
2. login_check: если показывает «Log in» - cookies истекли, abort с инструкцией
3. Scroll feed 20-30 раз с human delays (1.5-3 sec через browser_press_key PageDown + browser_wait_for)
4. browser_snapshot - DOM tree
5. Parse все /reel/{shortcode}/ из feed grid (обычно 15-25 reels на 30 scroll'ов)
6. Для каждого:
   - yt-dlp --print "%(upload_date)s|%(view_count)s|%(uploader_id)s|%(description)s" --skip-download "$URL"
   - Filter 1: upload_date в --window (default 7d)
   - Filter 2: view_count >= --views-threshold (default 10K, было 50K по решению автора - отсекало RU micro-creators)
   - LIMIT 15 reels/handle захардкожен в `scripts/discover.sh:45` - совпадает с doc
7. Relevant reels → bucket "feed_discover" в JSONL
8. После merge + ingest → prompt автору:
   «Найдено N новых uploaders в feed которых нет в watchlist:
   @newbie_creator (3 viral reels за неделю, avg 80K views)
   @another_micro (1 reel 200K views) ← outlier
   Добавить в watchlist? [y/n per author]»
```

**Account safety - main account <твой-хэндл>:**

| Rule | Value |
|---|---|
| Scroll cap | ≤30 reels/scan |
| Human delays | 1.5-3 sec random между actions |
| Frequency | 1 scan/day max |
| Actions during scan | view ONLY (никаких likes/comments/follows через playwright) |
| Concurrent | не запускать когда автор активно сидит в Instagram app |

**Risks:**
- Shadowban (твои посты перестают показывать) - low при правилах выше, не нулевой
- Temp block 24-48ч на feed scrolling - редко при ≤30/day
- Permanent ban - очень редко, только при aggressive scraping (1000+/day, likes/follows автоматом)

**Mitigation если детектится:**
- Перестать scrape немедленно
- Logout-login вручную, восстановить cookies через setup
- Уменьшить scroll cap до 15
- Перейти на отдельный @<твой-бренд>_scan аккаунт

### Шаг 4 - Filter + Rank

```bash
cat /tmp/scan-*.jsonl > /tmp/scan-all.jsonl
~/.claude/skills/competitors-daily-scan/scripts/filter-and-rank.sh /tmp/scan-all.jsonl <TOP_N> <DATE> > /tmp/scan-top.json
```

Скрипт фильтрует по `upload_date == DATE`, сортирует по `view_count desc`, берёт top N, выдаёт JSON массив.

### Шаг 4.5 - Niche relevance (Claude в сессии, 0 cost)

После filter+rank я получаю список кандидатов 50-100 reels с captions/transcripts. **Я Claude в этой сессии** одним проходом классифицирую каждый:

```
relevant=yes  - тематика vibemarketing/vibecoding/AI building/content creation
relevant=no   - нерелевантно (фитнес, мода, кулинария, политика, и т.д.)
outlier=yes   - не пойман как relevant, но views > 500K - отдельный bucket для ручного check
```

**Hint-файл для меня:** `~/.business/growth/niche-keywords.md` - стартовый список терминов которые помогают мне понять что для автора «релевантно». Это не отдельный automated filter, это контекст для моей классификации. автор правит руками когда меняется фокус.

Output - два bucket'а:
- `relevant` - идёт дальше в ingest топа
- `outlier` - в карточке отдельной секцией для авторская ручного screening

### Шаг 5 - Ingest топа

Для каждого URL из top-N:

```bash
~/.claude/skills/ingest-reel/scripts/ingest.sh "$URL"
```

Это даёт `~/.business/growth/ingest/YYYY-MM-DD-{id}/` с card.md, transcript.txt, frames/, grid.jpg.

**OCR хедлайна:** для каждого ингеста используешь tool Read на `frames/f_001.jpg` (первый кадр = обычно с хедлайном overlay). Multimodal Claude прочитает текст с кадра. Сохрани в собранную карточку как `headline_ocr`.

Если frame text неразборчив (логотип, фото без оверлея) - просто пропусти, не выдумывай.

### Шаг 6 - Сборка финальной карточки

Используй template `~/.claude/skills/competitors-daily-scan/templates/scan-card.md`. Пиши в:

```
~/.business/growth/competitors-scan/YYYY-MM-DD.md
```

Структура карточки (template подскажет):
- Метаданные: date, total_handles_scanned, total_today_reels, top_n
- Errors[] (handles которые упали)
- Топ-N таблицей: handle / platform / views / likes / URL / headline_ocr / transcript_first_sentence
- Сырой JSONL `/tmp/scan-all.jsonl` копируем в `~/.business/growth/competitors-scan/raw/YYYY-MM-DD.jsonl` для последующего анализа

### Шаг 7 - Cleanup

```bash
rm -f /tmp/scan-*.jsonl /tmp/scan-top.json
```

Ingest папки в `~/.business/growth/ingest/` оставляешь - они полезный архив.

## Watchlist - формат и dynamic add (4 канала)

### Формат файла `~/.business/growth/competitors-watchlist.md`

```markdown
# competitors-watchlist
# format: @handle PLATFORM [#category] [#lang] [#priority] added:YYYY-MM-DD source:CHANNEL

## active

@rileybrown.ai instagram #ai-tutorial #en #high added:2026-05-23 source:manual
@nate.dev youtube #vibecoding #en #high added:2026-05-23 source:inline
@palij_arina instagram #ugc-ai #ru #med added:2026-05-15 source:bulk

## archive
# handles которые не публиковали >30d, scan их пропускает
# @oldhandle tiktok #stale archived:2026-05
```

**Поля:**
- `@handle` - без @ это просто строка, считаем обязательным
- `PLATFORM` ∈ {instagram, tiktok, youtube} - обязательно
- `#category` (свободно, рекомендуемые: ai-tutorial, vibecoding, vibemarketing, ugc-ai, content-creator, business-coach, lifestyle)
- `#lang` ∈ {#ru, #en} - для selective scan
- `#priority` ∈ {#high, #med, #low}
- `added:YYYY-MM-DD` - дата попадания в watchlist
- `source:CHANNEL` ∈ {manual, inline, bulk, recommend} - откуда пришёл

**Dedupe rule:** уникальность по `@handle + PLATFORM`. При попытке добавить дубль - не дублировать, обновить теги если новые передали.

### Канал 1: Manual

```
/scan-add @rileybrown.ai instagram #ai-tutorial #en #high
```

Парсит аргументы, дописывает строку в `## active` watchlist.md, проставляет `added:DATE source:manual`. Idempotent по handle+platform.

### Канал 2: Inline при ingest (UX = ask y/n + category)

После каждого успешного `~/.claude/skills/ingest-reel/scripts/ingest.sh <URL>` skill `ingest-reel` (или его orchestrator `produce-reel`) проверяет: handle автора уже в watchlist?

**Если нет** - спрашивает у автора:

```
INFO: ingest успешен (video_id=DXZsCExij3g, uploader=rileybrown.ai)
Handle @rileybrown.ai не в watchlist. Добавить?
  [1] да - категория ai-tutorial (типичная для этого ingest)
  [2] да - другая категория (введи)
  [3] нет, пропустить
  [4] никогда не спрашивать про этот handle (blacklist)

Выбор:
```

При выборе [1]/[2] - вызывается `/scan-add @uploader_id PLATFORM #category #lang_detected source:inline`. Lang определяется по transcript (Whisper уже знает язык).

При [4] - handle добавляется в `~/.business/growth/competitors-watchlist.md` под секцией `## blacklist`, и при будущих ingest skill не спрашивает.

**Где интегрируется:** в `ingest-reel/SKILL.md` Шаг 9 (после успешного output). Не в bash-скрипте ingest.sh - там нет интерактивности, это шаг Claude.

### Канал 3: Bulk paste

```
/scan-add-bulk
```

автор вставляет любой текст в чат - DM-список, скриншот caption, ссылки строкой, копию из Virale digest. Skill:

1. Парсит текст regex'ом на handles (`@xxx`, instagram.com/xxx, tiktok.com/@xxx, youtube.com/@xxx) и URLs
2. Дедупит против существующего watchlist
3. Выводит **список новых кандидатов** (10-50)
4. Спрашивает категорию **на весь батч** одним выбором: «все ai-tutorial / все ugc-ai / разные (тогда показывает по одному)»
5. Записывает с `source:bulk`

Полезно когда автор подписался на 15 авторов разом или принёс список из Virale.

### Канал 4: Recommend chain (weekly auto)

Раз в неделю `/scan-recommend` (или auto через `/schedule`):

1. Берёт топ-5 `#priority high` handles из watchlist
2. Для каждого playwright `browser_navigate https://instagram.com/{handle}/`
3. Парсит блок «Suggested for you» / «Similar accounts» с DOM snapshot (обычно 6-8 предложений)
4. Дедупит против watchlist
5. Выдаёт автору suggested list для ручного screening:

```
Recommend chain 2026-05-30 (на основе твоего топ-5):

NEW кандидаты (15):
  [1] @ai_creator_xyz instagram - похож на @rileybrown.ai
  [2] @vibemarket_pro instagram - похож на @nate.dev
  ...

Команды:
  y 1 3 7 #ai-tutorial   - добавить 1,3,7 с тегом
  n 5 9                  - blacklist 5, 9
  всё y #ai-tutorial     - добавить всё с одним тегом
```

При выборе - вызывается `/scan-add` для каждого с `source:recommend`.

### Archive автоматика

Раз в неделю при `/scan` если handle не публиковал >30 дней (data из последнего успешного discovery) - перенос строки из `## active` в `## archive` с проставленным `archived:YYYY-MM`. Архив можно вернуть руками или через `/scan-unarchive @handle`.

### Selective scan флаги

```
/scan                          # все active (default)
/scan --tag ai-tutorial        # только #ai-tutorial
/scan --lang en                # только #en handles
/scan --priority high          # только #high
/scan --platform tiktok        # только TT (skip IG playwright)
/scan --top 30 --tag vibecoding --lang en   # композиция
```

## Anti-examples - что НЕ делать

- ❌ Не вызывать `ingest-reel` на ВСЕХ найденных URL подряд. Discovery возвращает 12-15 reels per handle, при 30 handles это 450 ингестов = час времени и забитый диск. Фильтр today + top-N обязателен.
- ❌ Не парсить даты со страницы Instagram «2 hours ago». Это относительное время, ломается в полночь. Используй yt-dlp на конкретном reel URL (он возвращает абсолютный `upload_date`).
- ❌ Не делать OCR на grid.jpg (8x4 миниатюры). Делай на конкретном `frames/f_001.jpg`.
- ❌ Не сохранять PII (cookies, sessions) в output карточки.
- ❌ Не использовать em-dash «—» внутри строк карточки. Только дефис «-» или запятая.

## Output - пример карточки

См. `examples/sample-scan.md` после первого реального run.

## Maintenance

### yt-dlp staleness

При warning «extractor broken» или error «Unable to extract» - первое действие `brew upgrade yt-dlp`. Релизы каждые 1-2 недели. Особенно часто ломается TikTok и Instagram (Instagram уже сломан на профилях, но работает на отдельных reel URLs).

### Playwright session

MCP playwright использует свой headless chrome. Если Instagram начнёт детектить fingerprint и показывать login wall на анонимной сессии:
1. Уменьши частоту запусков (раз в день вместо каждого часа)
2. Добавь cookies файл в `~/.config/playwright-cookies/instagram.json` от залогиненной сессии автора (это уже не «анонимно», но повышает success rate)
3. Если систематически - переключайся на Apify (платный, но обходит fingerprint detection)

### Watchlist refresh

`~/.business/growth/competitors-watchlist.md` обновлять раз в месяц - выкидывать аккаунты которые не публикуют >30 дней, добавлять новых из `G.1-Creators-List.md` (178 creators baseline).

## Memory cross-refs

- `feedback_feed_based_discovery` - твой personal feed = primary discovery, этот scan = secondary
- `feedback_strategy_copy_faster_more_better` - scan нужен для same-format reproduction
- `project_acquisition_decisions_2026_05_21` - 7 решений content system, scan = их инфраструктурный кирпич
- `feedback_no_em_dash` - в output карточке только дефис, не em-dash внутри строк
- `feedback_post_deploy_active_probe` - после изменений в этом skill - e2e run на 2-3 handles перед merge