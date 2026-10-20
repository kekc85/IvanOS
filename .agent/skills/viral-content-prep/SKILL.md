---
name: viral-content-prep
description: Preprocessor для виральных конкурентских материалов перед Custom GPT уникализатором. Primary режим (carousel→carousel) — по URL IG-карусели скачивает N слайдов как плоский набор PNG. Secondary режим (reel→carousel) — split-screen tutorial Reel → UI-кропы + cover + transcript + structure.json. Output на Desktop плоской папкой готов к загрузке в Custom GPT. Триггерится на «подготовь карусель», «уникализируй карусель <URL>», «нарежь Reel в карусель», «/prep <URL>».
allowed-tools: Bash, Read, Write, Edit
version: "2.0"
created: 2026-05-29
last_reviewed: 2026-05-29
review_deps_every: 3 months
---

# Viral-Content-Prep — preprocessor для Custom GPT уникализатора

Скачивает виральный конкурентский контент (карусели IG / Reels split-screen tutorial) и готовит плоский PNG-пакет для Custom GPT уникализатора. Не генерирует визуал — берёт ОРИГИНАЛЬНЫЕ слайды/кадры.

## 🔒 BYOA-гейт Instagram (ПЕРЕД любым обращением к куки — HARD)

`apifetch.py` ходит в IG media API на cookies. Cookies должны быть ТВОИ (твоя IG-сессия), не автора курса. ПЕРЕД тем как читать `~/.business/processes/.ig-cookies.json`:

```
1. python3 ~/.claude/skills/_shared/bin/account.py status instagram
2. если "missing" (файла куки нет / он пуст):
     - показать онбординг:  python3 ~/.claude/skills/_shared/bin/account.py onboard instagram
     - запустить интерактивный headed-login (он уже встроен в ig-carousel-radar):
         cd ~/.claude/skills/ig-carousel-radar && python3 scripts/setup.py
       откроется окно Chromium → ученик логинится в СВОЙ IG (вкл. 2FA) →
       скрипт сам сохранит ЕГО cookies в ~/.business/processes/.ig-cookies.json (chmod 600)
     - СТОП до завершения логина. НЕ запускать apifetch без куки, НЕ падать.
3. только "connected" → дальше apifetch использует ТВОИ cookies из ~/.business/processes/.ig-cookies.json
```

Канон гейта — `_shared/bring-your-own-account.md`. Cookies автора в дистрибутив не кладутся; ученик подключает свою сессию сам. (yt-dlp/`download-carousel.sh` для публичных постов куки не требуют — гейт нужен только для apifetch/private API.)

## 🛑 ГРАБИНГ КАРУСЕЛИ — ПЕРВЫЙ выбор Apify, cookies-путь ЗАПРЕЩЁН по умолчанию (правило по решению автора)

ПЕРВЫЙ выбор: `download-carousel.sh <URL>` - внутри yt-dlp для видео-постов (бесплатно) и автоматический фолбэк на Apify для фото-каруселей (`.business/scripts/ig-fetch/apify_ig.py carousel <URL> <out_dir>`, актор apify/instagram-scraper, слайды 1080x1350 + caption + meta, ~$0.003/пост, токен `APIFY_TOKEN` в `~/.claude/.env`). Аккаунт и IP владельца полностью вне цепочки - банов не бывает by design.

Старый путь `apifetch.py` на cookies (`~/.business/processes/.ig-cookies.json`) = ДЕПРЕКЕЙТ: баны в даты запуска.2026, профиль заморожен по решению автора. Использовать только как аварийный резерв при явном «да» владельца аккаунта.

НИКОГДА не изобретать DOM-граберы (Playwright клик-Next, screenshot региона) - по решению автора они дали грязь (комменты в кадре, обрезка, перебор в соседние посты, 0/14/1 слайдов), потеряны часы. yt-dlp берёт только видео.

## Два режима

### Primary: CAROUSEL → CAROUSEL
Source = viral карусель конкурента в IG (URL вида `instagram.com/p/<ID>`).
Output = N PNG слайдов (yt-dlp для видео, Apify-фолбэк для фото-каруселей) + плоская папка.
Use case: ежедневный pipeline уникализации виральных каруселей.

### Secondary: REEL → CAROUSEL
Source = split-screen tutorial Reel (Reel URL).
Output = N UI-кропов реальных скринов + cover-frame + transcript + structure.json.
Use case: периодическое переупаковывание viral Reels в карусели.

## Когда триггерить

**Primary режим:**
- `/prep <carousel-URL>`
- «подготовь карусель к уникализации»
- «уникализируй карусель <URL>»
- «скачай карусель конкурента»

**Secondary режим:**
- `/prep <reel-URL>`
- «нарежь Reel в карусель»
- «подготовь Reel-пакет»
- «собери из Reel пакет для карусели»

URL auto-detect в `scripts/prep.sh`: `/p/<id>` где это набор изображений = carousel; `/reel/<id>` или video-only `/p/<id>` = Reel.

## Когда НЕ триггерить

- Reel не split-screen (talking-head без UI) — нет downstream pipeline
- Reel >90 сек — слишком много сцен
- Пользователь хочет генерить новый дизайн с нуля
- URL не IG (TikTok/YouTube/X) — нужны другие skills

## Зависимости

**Primary режим:** `yt-dlp` (homebrew). IG cookie опционален для приватных аккаунтов.
**Secondary режим:** `ingest-reel` skill, `ui-inventory` skill.

## Workflow

### Entry script: `scripts/prep.sh <URL>`

Auto-detects URL type, dispatches to mode-specific handler.

```bash
~/.claude/skills/viral-content-prep/scripts/prep.sh "https://www.instagram.com/p/<ID>/"
```

### Primary (carousel) workflow

`scripts/download-carousel.sh <URL>`:
1. Извлекает ID карусели из URL
2. yt-dlp скачивает все N слайдов
3. Конвертирует JPG → PNG если нужно
4. Нумерует `slide-01.png ... slide-NN.png`
5. Output: `~/Desktop/viral-content/<handle>-<id>/` плоской папкой

### Secondary (reel) workflow

`scripts/prep.py <ingest-dir>` (существующая логика):
1. Читает `scene-types.json` + `transcript.json` + `frames/`
2. Для каждой `ui_only` секции → кропает UI зону → resize до 1080-ширины
3. Дедупликация подряд идущих кадров через md5 hash
4. Cover-frame: первый `face_only` кадр
5. Группирует transcript по смысловым кускам
6. Output: `~/Desktop/viral-content/<reel-id>/` с `cover-frame.png`, `step-01.png` ... `step-N.png`, `transcript.txt`, `structure.json`

## Output контракт

Обе режимы → плоская папка `~/Desktop/viral-content/<id>/` (без подпапок, готов к drag-and-drop в Custom GPT).

**Primary:**
```
viral-content/<handle>-<id>/
  ├── slide-01.png
  ├── slide-02.png
  ├── ...
  └── meta.json (URL, handle, дата, count)
```

**Secondary:**
```
viral-content/<reel-id>/
  ├── cover-frame.png
  ├── step-01.png ... step-N.png
  ├── transcript.txt
  ├── structure.json
  └── README.md
```

## Output контракт `structure.json` (secondary режим)

```json
{
  "reel_id": "...",
  "reel_url": "...",
  "creator": "...",
  "duration_sec": 31.5,
  "language": "EN",
  "cover": {"frame": "cover-frame.png", "transcript_hook": "..."},
  "steps": [{"id": 1, "ui_crop": "step-01.png", "transcript": "...", "sec_start": 3, "sec_end": 7}],
  "cta_hint": {"transcript": "...", "code_word_suggestion": "..."}
}
```

## Что НЕ делает

- Не генерирует финальные slide-images (это Custom GPT)
- Не накладывает watermark (это Custom GPT)
- Не переводит транскрипт
- Не подбирает DNA для дизайна

## Связано

- [[ingest-reel]] — upstream для secondary режима
- [[ui-inventory]] — генерирует scene-types.json для secondary
- [[ig-carousel-radar]] — upstream daily scan каруселей (находит URLы для primary)
- [[broll-swap]] — соседний preprocessor (B-roll замена в Reels)
- Custom GPT уникализатор IG (`carousels <твой-хэндл>`) — downstream consumer
- `reel-mode.md` в Knowledge Custom GPT'а — инструкции для secondary режима

## История версий

**v2.0 (2026-05-29):** rename `reel-to-carousel-prep` → `viral-content-prep`. Добавлен Primary режим carousel→carousel (yt-dlp download). Существующая reel→carousel логика стала Secondary. Output путь сменён с `~/Desktop/reel-to-carousel/` на `~/Desktop/viral-content/`.

**v1.0 (2026-05-29):** initial release как `reel-to-carousel-prep`, только Secondary режим.