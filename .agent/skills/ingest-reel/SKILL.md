---
name: ingest-reel
description: Ingest vertical video (Нельзяграм Reel, TikTok, YouTube Short) by URL into the content factory knowledge base. Downloads video via yt-dlp, transcribes audio with whisper-cli, extracts frames, builds analysis card (format identification, structure, replication spec). Triggers on /ingest <URL>, on bare URL with intent to analyze ("разбери", "проанализируй", "возьми в работу", "что внутри"), or on any Instagram/TikTok/YouTube Shorts link sent for content factory work.
allowed-tools: Bash, Read, Write, Edit
version: "1.1"
created: 2026-05-23
last_reviewed: 2026-05-27
review_deps_every: 3 months
---

# Ingest Reel - URL → анализ-карточка

Полный pipeline превращения публичной вертикальной короткометражки в structured artefact для контент-завода автора.

## Когда триггерить

- Явный вызов `/ingest <URL>`
- Пользователь скинул ссылку на Reel / Short / TikTok в любом виде и просит «разобрать», «понять что внутри», «возьми в работу», «проанализируй», «спарсим»
- Пользователь говорит «для контент машины спарсим» / «занеси в знание» + URL
- Любая голая ссылка вида `instagram.com/p/`, `instagram.com/reel/`, `tiktok.com/.../video/`, `youtube.com/shorts/` в контексте content work

## Когда НЕ триггерить

- Ссылка на длинное видео (YouTube long-form) - для них используется skill `youtube-transcript`
- Ссылка прислана не для анализа (например, в legal context или просто для просмотра)
- Видео уже было ингестировано (проверить через `ls ~/.business/growth/ingest/` - папка с этим ID уже существует)

## Workflow

### Шаг 1: запустить pipeline-скрипт

```bash
~/.claude/skills/ingest-reel/scripts/ingest.sh "URL_HERE"
```

Скрипт делает атомарную последовательность:
1. Извлекает video_id из URL
2. Создаёт папку `~/.business/growth/ingest/{YYYY-MM-DD}-{video_id}/`
3. Скачивает видео + metadata + description через yt-dlp
4. Извлекает audio (16kHz mono PCM) через ffmpeg
5. Транскрибирует через whisper-cli с моделью large-v3-turbo, auto-detect language
6. Адаптивно извлекает кадры (4fps для ≤20с, 2fps для ≤60с, 1fps для длиннее)
7. Строит обзорный grid.jpg для one-shot визуального просмотра
8. Печатает в stdout пути ко всем артефактам + метрики

Скрипт идемпотентен - если папка существует, пропускает уже сделанные шаги.

### Шаг 2: прочитать grid + транскрипт

```
Read: {OUTDIR}/grid.jpg
Read: {OUTDIR}/transcript.txt
Read: {OUTDIR}/{video_id}.info.json
```

Визуально проанализировать:
- Что показано в кадре (формат, layout, persona автора)
- Структура (хук / development / CTA с timestamps)
- Subtitle overlay, тексты внутри inset clips
- Видимые UI-элементы платформы (likes/comments/saves если они в кадре)
- Конкретный creator-референс если виден

Текстуально проанализировать:
- Длина транскрипта vs длина видео = темп речи
- Лексика, специфичные термины
- Хук в первых 1.5-3 секундах
- CTA в конце

### Шаг 3: классификация формата (mandatory 5-step gate)

Обязательная процедура до написания card.md. Цель — поле `format_classification.primary` в YAML-шапке заполняется одним из 20 канонических slug'ов из `.business/growth/format-library-vertical-2026.md` или строкой `new` с обоснованием.

**3.1. Read обзорный grid ингеста**
```
Read: {OUTDIR}/grid.jpg
```
Покрытие всех ключевых кадров за один взгляд.

**3.2. Read визуальный reference 20 форматов**
```
Read: ~/.business/growth/ingest/2026-05-23-DYZbFlToI8T/format-examples/grid.jpg
```
Сетка 5×4: каждый tile подписан slug'ом NN-name. Это эталонный визуальный словарь — никогда не классифицировать без этого Read.

**3.3. GATE A inventory — посчитать сырые наблюдения**

По grid.jpg ингеста определить (в YAML-шапке card.md `format_classification.gate_a`):
- `face_pct` — какая часть кадра занята лицом/телом автора (0-100)
- `ui_pct` — какая часть — UI / screen recording / external media (0-100)
- `pip` — есть picture-in-picture inset (true/false)
- `split` — none | horizontal-50-50 | horizontal-30-70 | vertical | triple | other
- `captions_dominant` — большие burnt-in captions перекрывают визуал (true/false)

Цифры — глазомерные, не точные. Цель — закрепить наблюдения, чтобы reasoning был воспроизводим.

**3.4. Mapping на 20 slug'ов через decision shortcuts**

Базовые правила-сокращения (full catalog — в `format-library-vertical-2026.md`):

| Признак | Кандидаты |
|---|---|
| `face_pct >70` + статичный кадр + плотная речь | `01-yap` / `03-talking-head` |
| `face_pct >50` + крупный медиа-объект за спиной | `02-green-screen` |
| Микрофон в кадре + другой собеседник | `04-interview` / `05-man-on-the-street` |
| `face_pct <30` + крупный текст-overlay + B-roll | `06-text-over-b-roll` |
| `split = horizontal-50-50` или `vertical` | `07-split-screen` |
| Один и тот же автор в 2-3 экземплярах в кадре | `08-clone` / `09-triple-clone` |
| `pip = true` + чужой viral сверху + реакция снизу | `10-video-reaction` |
| Список с цифровыми пунктами + ранжирование | `11-ranking` / `12-listicle` |
| Демонстрация физического объекта крупным планом | `13-object-lesson` / `15-top-down` |
| Play/pause паттерн в визуале + комментарий | `14-play-pause-reaction` |
| Свайп-карусель Нельзяграм | `16-carousel` |
| Маркер + доска / iPad + рисование | `17-white-board` |
| Текстовый вопрос-overlay + ответ автора | `18-ask-me-anything` |
| Кинематографичный шот, slow-mo, грейдинг | `19-hyper-cinematic` |
| Aspect ratio меняется внутри ролика | `20-change-of-aspect-ratio` |

Если ни одно правило не сработало однозначно — `confidence: medium` + reasoning раскрыть.
Если ролик гибрид (2 признака сильные) — основной в `primary`, второй в `secondary[]`.

**3.5. Если ни один из 20 не подходит — `new`**

`primary: "new"`, в `reasoning` обосновать через GATE A что новое, предложить slug `NN-name` (NN = следующий номер: 21, 22…). После сохранения card.md — добавить раздел в `format-library-vertical-2026.md` (living document).

### Шаг 4: написать card.md

Использовать `~/.claude/skills/ingest-reel/templates/card.md` как структурный шаблон. YAML-шапка с `format_classification` — уже заполнена по результатам Шага 3.

**Критично:**
- Spec для replication - формировать как реальный JSON-bin, который потом съест Remotion-template (фаза 2). Не как маркетинговое описание.
- Применимость для автора - конкретные сценарии в его нише (вайбкодинг RU курс / Skool EN / контент-завод), не абстрактно.
- Метрики - только то что реально видно из info.json или из кадров, не выдумывать.
- НЕ дублировать описание формата из `format-library-vertical-2026.md`. В card.md ссылка на каталог + что отклоняется от эталона.

### Шаг 5: краткий summary в чат

В чат автору - компактное сообщение, **первой строкой обязательно**:

```
Format: NN-slug (confidence: high|medium|low)
```

Дальше:
- Что за ролик (автор, длина, метрики)
- 2-3 главных insight'а
- Ссылка на card.md и папку ingest

НЕ дублировать весь card.md в чат. Card.md - для машины (фазы 2-3), чат - для человека.

### Шаг 6: накоп в конце (правило проекта)

В конце ответа выдавать актуальный полный накоп операционных задач из `tasks/today.md`.

## Зависимости

Все локальные, никаких API:
- `yt-dlp` (homebrew, версия ≥ 2026.03)
- `ffmpeg` (homebrew)
- `whisper-cli` из пакета `whisper-cpp` (homebrew)
- Модель `~/whisper-models/ggml-large-v3-turbo.bin`
- `python3` (для парсинга info.json)

Проверка установки:
```bash
which yt-dlp && which ffmpeg && which whisper-cli && ls ~/whisper-models/ggml-large-v3-turbo.bin
```

Если что-то отсутствует - установить через brew перед запуском.

## Авторизация для приватных Reels

Публичные Reels yt-dlp скачивает без cookies. Если ролик приватный, скрипт упадёт с ошибкой `Login required`. Тогда:

1. Сообщить автору что нужны cookies Нельзяграм
2. Предложить экспортировать через расширение типа Get cookies.txt LOCALLY
3. Положить в `~/.config/yt-dlp/instagram-cookies.txt`
4. Перезапустить скрипт с флагом `--cookies`

В большинстве случаев публичные feed-based Reels не требуют этого.

## Output structure

```
~/.business/growth/ingest/{YYYY-MM-DD}-{video_id}/
├── {video_id}.mp4              # исходное видео
├── {video_id}.info.json        # метадата yt-dlp
├── {video_id}.description       # description from platform
├── audio.wav                    # 16kHz mono для Whisper
├── transcript.txt               # plain text
├── transcript.json              # с timestamps
├── frames/                      # извлечённые кадры
│   ├── f_001.jpg
│   ├── f_002.jpg
│   └── ...
├── grid.jpg                     # обзорная сетка для visual scan
└── card.md                      # ⭐ финальная карточка анализа
```

## Связи

- Для конвейера replicate-viral после ingest ОБЯЗАТЕЛЕН `~/.claude/skills/replicate-viral/scripts/ui-detect.py <video>` — классификация верхнего экрана (real-screencast/mock/hero/author) + действия репликации; howto `replicate-viral/knowledge/ui-detect.md`
 с другими частями системы

- Catalog: `.business/growth/format-library-vertical-2026.md` - база форматов
- Pipeline doc: `.business/growth/G.2-Production-Pipeline.md`
- Adjacent skills:
  - `adaptation` - берёт card.md и адаптирует в voice автора
  - `hook-generator` - берёт hook section из card.md и генерит варианты
  - `pattern-extraction` - батчевый разбор множества ингестов на паттерны

## Anti-patterns

- ❌ Не запускать скрипт через Bash напрямую если можно через этот skill (skill даёт structured output)
- ❌ Не писать card.md «по аудио без grid» - визуал даёт >50% смысла
- ❌ Не выдумывать метрики (saves count, share rate) если они не видны в info.json или кадрах
- ❌ Не дублировать материал из format-library в card.md - давать ссылку
- ❌ Не складывать ингесты вне `.business/growth/ingest/` - теряется findability
- ❌ Не классифицировать формат без Read `format-examples/grid.jpg` (Шаг 3.2). Без визуального словаря классификация = угадывание.
- ❌ Не оставлять `format_classification.confidence: high` если хоть один признак GATE A был на глаз. high = только когда формат очевиден (split / clone / carousel / man-on-street).
- ❌ Не помечать как `new` без сверки со всеми 20 канонами. Часто это `hybrid` (primary + secondary), а не `new`.

## Maintenance

### yt-dlp staleness

yt-dlp ломается на Instagram / TikTok когда платформа меняет API. Симптомы: `HTTP 403`, `HTTP 404`, `Unable to extract`, `extractor.*broken`.

Первое действие при любом из этих симптомов:

```bash
brew upgrade yt-dlp
```

Релизы yt-dlp выходят каждые 1-2 недели. Если после upgrade всё ещё падает - проверь https://github.com/yt-dlp/yt-dlp/issues на issue про целевую платформу. Обычно фикс выкатывают в течение 24-48 часов после поломки.

Instagram **на профилях** сломан хронически (yt-dlp не извлекает grid). На **отдельных reel URLs** работает. Discovery конкурентов по handle - через playwright (см. skill `competitors-daily-scan`), ingest по URL - через этот skill.

### Whisper model

Модель `~/whisper-models/ggml-large-v3-turbo.bin` (~1.6GB). Если обновляется до v4 - сменить путь в скрипте.