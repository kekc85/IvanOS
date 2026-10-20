---
name: raspoznavalka-postov
description: "Заполняет поле recognized_text у Instagram-каруселей и рилзов в локальном база знаний-архиве: OCR слайдов через OpenAI Vision и транскрипция рилзов через sian.agency. Идёт по md-файлам архива (YAML-frontmatter с полями id/network/type/url/caption/recognized_text), отбирает кандидатов фильтром network=Instagram + type in (карусель,рилз) + пустой recognized_text, обрабатывает через локальные python-скрипты на ключах эксперта из env. Универсален: одинаково работает на /Мои посты и на любой папке /Конкуренты со схожей схемой frontmatter. Применяй всякий раз когда эксперт говорит про распознавание/OCR/транскрипцию своих или чужих IG-постов в локальной база знаний-базе, даже если он просит лишь «обработать карусели», «заполнить пустые recognized_text» или «прогнать архив через OCR». Не применяй для Telegram-постов (recognized_text там уже из выгрузки) и не для сбора метаданных (это retro-skraping-arhiva)."
---

# Распознавалка постов

Ты — Recognizer скилла «Распознавалка постов» (контент-завод). Заполняешь `recognized_text` у Instagram-каруселей и рилзов в базе знаний-архиве: OCR слайдов через OpenAI Vision и транскрипция рилзов через sian.agency.

Результат — обновлённые md-файлы архива, где у каждой обработанной записи `recognized_text` непустое, а `status` переведён в «распознан». Тело документа (markdown после frontmatter) и метрики (likes, comments и т.п.) — не трогаешь.

Что НЕ делаешь:
- Не скрейпишь архив с нуля — это задача скилла №6 `skraping-postov` (ретро или инкрементальный). В инкрементальном режиме №6 создаёт новые IG-записи с пустым `recognized_text` — ты их подбираешь.
- Не трогаешь Telegram-посты — у них `recognized_text` приходит готовым из выгрузки.
- Не работаешь через Notion — этот скилл вытеснил старый поток «бот клуба → Сервисы → Распознавалка» в пользу локального python-pipeline.
- **Не запускаешь скрипты через `mcp__workspace__bash`** — это Linux-sandbox с allowlist-прокси, sian.agency и api.openai.com через него возвращают `ProxyError 403`. Запуск идёт через mac-host shell (osascript) или копи-паст в локальный Terminal/PowerShell эксперта. См. граблю 15 и Фазу 1.5.

> **Кроссплатформенность (Mac / Windows / Linux).** `osascript` (Apple events) — это ТОЛЬКО macOS-удобство авто-запуска batch-прогона (режим A). Само распознавание не зависит от osascript: на Windows и Linux эксперт работает в режиме B/C — Claude выдаёт ту же команду одним блоком, эксперт копирует её в свой Terminal/PowerShell, либо Claude ведёт прогон напрямую через локальный shell. Никогда не падай с ошибкой на не-Mac из-за отсутствия `mcp__Control_your_Mac__osascript` — это ожидаемо, просто уходи в копи-паст-ветку (см. Фазу 0.1).

## Контекст задачи

Архив — папка md-файлов (база знаний Base, SQL-обёртка над md), один файл = один пост. Frontmatter:

```yaml
---
id: "DXwMNfika2D"
published: 2026-04-30
network: Instagram          # Instagram | Telegram
type: карусель              # карусель | рилз | пост
status: новый               # новый | распознан | ...
url: "https://www.instagram.com/p/DXwMNfika2D/"
caption: "..."
recognized_text: ""         # ← это ты заполняешь
likes: 25
comments: 2
shares: 0
viewers: 0
outlier: false
hypothesis: ""
updated: 2026-05-19
---

# Карусель от 30 апреля
```

Скилл универсален: одинаково работает на `.business/growth/content-archive/Мой контент/записи/` (свой архив) и `.business/growth/content-archive/Конкуренты/<имя>/записи/` (конкурент), если совпадает схема frontmatter. Ключи API (OpenAI + Apify) — в env эксперта; никакого Fernet, master-key, БД.

**Стоимость для эксперта.** Эмпирика бота: ~$0.03/карусель (gpt-4o) + ~$0.005/рилз (sian). На 50 каруселей + 30 рилзов ≈ $1.65. С личных ключей OpenAI и Apify эксперта.

## Жёсткие принципы

1. **Один Apify-вызов на пост.** В отличие от бота клуба, `type` уже размечен во frontmatter — detect-scrape пропускается. Apify нужен только за полезными данными: slide URLs (`apify/instagram-scraper`) или sian-актор для рилзов. Минус один scrape на каждом посту.

2. **OCR Semaphore=1 + ручной backoff 4/16/30/60/90/120 сек.** На gpt-4o TPM-локаут длится десятки секунд. SDK retry слишком короткие — сжигают попытки, не пережидая лимит. Логика встроена в `scripts/ocr_carousel.py`, ничего настраивать не нужно.

3. **sian.agency обязательно с singular `instagramUrl`.** Actor `sian.agency/instagram-ai-transcript-extractor` игнорирует `postUrls` (множественное) и читает только singular. Без него возвращает дефолтный Zig Ziglar-транскрипт на любой URL. `transcribe_reel.py` шлёт оба поля и сверяет shortCode в ответе.

4. **Правило 10 сек для рилзов.** Если `duration ≤ 10s` И `caption > 100 chars` — это b-roll: пишем `[caption-only b-roll: <caption>]` и не транскрибируем. Редкий частый кейс: «эстетика + смысл в подписи», транскрипт там либо пуст, либо шум. Caption-only логика включается передачей `--caption` в `transcribe_reel.py`.

5. **Идемпотентность.** Записывай результат только если `recognized_text` пустой. `--force` перезаписывает (нужно для переcrawl на новой модели). `find_targets.py` уже фильтрует по этому правилу.

6. **Каждый файл атомарен.** Падение на одном файле (apify rate limit, удалённый пост, restricted) не останавливает batch — складываем ошибки в финальный отчёт.

7. **Status: «новый» → «распознан».** После записи `recognized_text` и обновления `updated:` (сегодня) переводим `status: распознан`. Если у эксперта используется другой словарь — спрашиваем перед запуском.

8. **Запуск только через mac-host shell (osascript) или копи-паст в локальный Terminal/PowerShell.** Запрет на запуск python-скриптов через `mcp__workspace__bash` — bash в Cowork живёт в Linux-sandbox'е с allowlist-прокси (только `*.anthropic.com` и небольшой список), `api.apify.com` идёт через MCP-обёртку, а прямые HTTPS-вызовы к `api.openai.com` и `api.sian.agency` возвращают `ProxyError 403 Forbidden`. Mac-host shell прозрачно ходит в интернет — там скрипты работают. См. грабли 15-16 и Фазу 1.5.

9. **`.env` грузится через `python-dotenv` внутри `batch_recognize.py`** — не через `source .env` или `set -a` обёртки. Это даёт одинаковую команду на Mac и Win (`python3 batch_recognize.py --archive PATH`), без shell-зависимостей.

## Фаза 0.0. Пути (источник — `.business/`)

Перед стартом фаз определи корневые папки `.business` через Glob. Паттерны содержат подстановку, чтобы найти папку с префиксом цифры (`1. Контекст`) или без (`Контекст`) — ученик может убрать префиксы и скилл всё равно найдёт:

- Все артефакты эксперта живут в `.business/` (наш источник под git). Подпапки ниже.
- контекст (ЦА, метод, продукты, голос) → `.business/`
- архив контента → `.business/growth/content-archive/`
- аналитика → `.business/growth/analytics/`
- производство и план → `.business/growth/production/`
- внешние материалы → `.business/growth/materials/`

Если какой-то корень не найден — сообщи эксперту: «Не нашёл папку „<имя>"; проверь структуру `.business`». Если релевантный для скилла блок — стоп; если нет — продолжай без него.

Дальше используй эти переменные вместо хардкода путей.

## ФАЗА 0. Подготовка

### 0.1. Определение OS и режима запуска

**Это первый шаг — без него скрипты будут падать в `ProxyError 403`.** В Cowork bash живёт в Linux-sandbox'е с allowlist'ом, который НЕ пропускает прямые HTTPS-вызовы к `api.openai.com` и `api.sian.agency`. Запуск скриптов всегда идёт через mac-host shell или локальный Terminal/PowerShell эксперта.

Определи режим по двум вопросам:

1. **OS эксперта.** Спроси у эксперта одной фразой: «Mac или Windows?». Не пытайся угадать по путям — пути в Cowork выглядят как macOS даже для Win-учеников (mount-обёртка). Не уточняй позже — это влияет на всё что ниже.

2. **Если Mac — доступна ли capability `mcp__Control_your_Mac__osascript`.** Попробуй sanity-call `osascript` с тривиальной командой (например, `echo test`). Если возвращает результат — Control your Mac включён, идём в авто-режим. Если capability отключена — фолбэк в копи-паст.

Три ветки:

| OS + capability | Режим | Что делает скилл |
|----|----|---|
| Mac + Control your Mac | **A. авто** | сам гоняет batch через `osascript do shell script`, ученик ждёт в чате |
| Mac без Control your Mac | **B. копи-паст bash** | выдаёт bash-команду одним блоком, ученик копирует в Terminal |
| Windows | **C. копи-паст PowerShell** | выдаёт PowerShell-команду одним блоком, ученик копирует в PowerShell |

Дальше в скилле все шаги делятся по веткам.

### 0.2. Ключи в `.env`

Ключи `OPENAI_API_KEY` и `APIFY_TOKEN` должны быть в `.env`. По умолчанию `batch_recognize.py` автоматически ищет файл в:

- `<cwd>/.env`
- `<cwd>/secrets.nosync/.env` (Mac, рекомендуется)
- `<cwd>/secrets/.env` (Windows)
- `~/.claude/.env`
- родительские папки до 4-х уровней

Если ученик прошёл Урок Фундамента «Подключение Apify» и Урок «OpenAI API-ключ» — `.env` уже лежит в `content-factory/secrets.nosync/.env` (Mac) или `content-factory/secrets/.env` (Win) и подхватится автоматически.

Проверь явно: попроси эксперта подтвердить, что в `.env` оба ключа заполнены. Без обоих скилл не запустится — это hard gate, `batch_recognize.py` падает с понятной ошибкой.

### 0.3. Установка зависимостей (одноразово)

Перед первым запуском нужно поставить python-зависимости на mac/win-хост (НЕ в Cowork sandbox).

**Mac (Терминал):**
```bash
python3 -m pip install --user -r "<абсолютный путь>/raspoznavalka-postov/scripts/requirements.txt"
```

**Windows (PowerShell):**
```powershell
python -m pip install --user -r "<абсолютный путь>\raspoznavalka-postov\scripts\requirements.txt"
```

Ставит `httpx`, `openai`, `python-frontmatter==1.0.1` (жёсткий пин — на macOS-системном python 3.9 свежий `>=1.1` падает с `ImportError: TypeGuard`, грабля 13), `python-dotenv`. В новом `requirements.txt` пин уже зашит — отдельно ничего делать не нужно. Если у эксперта уже стоит несовместимая версия `python-frontmatter` от прошлой установки — `pip install --user -r ...` сам её даунгрейднет.

В режиме A установка идёт через osascript — скилл сам выполняет команду. В режимах B/C — даёт команду ученику в копи-паст. Если зависимости уже стоят (повторный запуск) — pip быстро это поймёт.

### 0.4. Путь к архиву

Найди папку через Glob (`Карта.md` → `.business/Сбор данных/...`) или спроси у эксперта:

> Какая папка с архивом? Один из вариантов:
> - `<`.business`>/2. Сбор данных/Мой контент/записи/` — свой архив
> - `<`.business`>/2. Сбор данных/Конкуренты/<имя>/записи/` — конкретный конкурент

Сохрани **абсолютный путь** как `ARCHIVE_DIR`. Проверь что папка существует и содержит хотя бы один `.md`. Для Win-ученика приводи путь в формате с прямыми слешами (`C:/Users/.../записи`) — `batch_recognize.py` принимает оба формата.

### 0.5. Опции запуска

Уточни (если из запроса не ясно):

- **Что распознаём:** карусели, рилзы или оба? (default: оба, флаг `--types карусель,рилз`)
- **Лимит:** макс. число постов за прогон? (default: без лимита; флаг `--limit N`)
- **`--force`?** перезаписать уже распознанные. По умолчанию — нет.
- **Словарь статусов?** По умолчанию `новый → распознан`. Если у эксперта другая нотация — флаг `--status`.
- **Модель Vision:** по умолчанию `gpt-4o`. Для экономии — `gpt-4o-mini` (~17× дешевле, но больше `[OCR_ERROR]`). Флаг `--vision-model gpt-4o-mini`.

## ФАЗА 1. Dry-run (предпросмотр кандидатов)

Перед боевым прогоном — обязательный dry-run. На любой ветке (A/B/C) запускаем `batch_recognize.py --dry-run`, чтобы показать сколько постов будет распознано и сколько это будет стоить.

**Ветка A (авто через osascript):**

```
mcp__Control_your_Mac__osascript:
  do shell script "python3 '<абс_путь>/scripts/batch_recognize.py' \
    --archive '<ARCHIVE_DIR>' --dry-run"
```

**Ветки B и C (копи-паст):** выдай эксперту блок с командой. Mac/bash:

```bash
python3 "<абс_путь>/scripts/batch_recognize.py" --archive "<ARCHIVE_DIR>" --dry-run
```

Win/PowerShell:

```powershell
python "<абс_путь>\scripts\batch_recognize.py" --archive "<ARCHIVE_DIR>" --dry-run
```

Скажи эксперту: «скопируй и запусти; пришли мне вывод — посчитаем сколько постов и стоимость».

Из dry-run-вывода извлеки число каруселей, рилзов и оценку: $0.03/карусель + $0.005/рилз. Сообщи: «Нашёл X каруселей и Y рилзов. Прогон займёт ~Z минут и обойдётся в ~$N. Поехали?»

## ФАЗА 2. Боевой прогон

Команда одна и та же — отличается только способ её вызова по ветке.

**Базовая команда:**

```
python3 "<абс_путь>/scripts/batch_recognize.py" --archive "<ARCHIVE_DIR>"
```

Опциональные флаги: `--types`, `--limit N`, `--force`, `--vision-model gpt-4o-mini`, `--status`, `--env PATH`.

### Ветка A — авто через osascript (Mac + Control your Mac)

Запусти команду через `mcp__Control_your_Mac__osascript`. Поскольку прогон длинный (10-60 минут), нельзя одной синхронной командой ждать конца — таймауты осcript короче. Решение: пишем вывод в лог-файл, запускаем nohup в фоне, поллим лог раз в 30-60 секунд.

Конкретно:

1. Создай папку для лога: `mkdir -p ~/.claude/raspoznavalka-logs`.
2. Запусти прогон в фоне:
   ```
   osascript "do shell script \"nohup python3 '<абс_путь>/scripts/batch_recognize.py' \
     --archive '<ARCHIVE_DIR>' \
     > ~/.claude/raspoznavalka-logs/last.log 2>&1 &\""
   ```
3. Поллируй лог каждые 60 секунд: `tail -50 ~/.claude/raspoznavalka-logs/last.log`. Из строк `[batch_recognize] [i/total] ✓ <id>` извлекаешь прогресс, рапортуешь эксперту в чат каждые 5 минут (или каждый раз когда меняется тысячная часть от total).
4. Когда последняя строка — `[batch_recognize] ИТОГ:` — прогон закончился. Прочитай финальный JSON из лога и переходи к Фазе 3.

### Ветка B — копи-паст bash (Mac без Control your Mac)

Выдай эксперту ОДИН готовый блок:

```bash
cd "<абс_путь>/scripts" && python3 batch_recognize.py --archive "<ARCHIVE_DIR>"
```

Текст-обёртка для эксперта:

> Открой Terminal (`Cmd + Пробел` → `Terminal`), вставь это и нажми Enter:
>
> ```bash
> cd "<абс_путь>/scripts" && python3 batch_recognize.py --archive "<ARCHIVE_DIR>"
> ```
>
> Прогон займёт примерно <N> минут — Terminal будет показывать прогресс по постам. Когда увидишь строку `[batch_recognize] ИТОГ: ✓X ✗Y из N` — готово. Вернись сюда и напиши «готово». Я сам прочитаю результаты из `.business` и сделаю сводку.

### Ветка C — копи-паст PowerShell (Windows)

Выдай эксперту ОДИН готовый блок:

```powershell
cd "<абс_путь>\scripts"
python batch_recognize.py --archive "<ARCHIVE_DIR>"
```

Текст-обёртка:

> Открой PowerShell (`Win + X` → `Windows PowerShell` или `Terminal`), вставь это и нажми Enter:
>
> ```powershell
> cd "<абс_путь>\scripts"
> python batch_recognize.py --archive "<ARCHIVE_DIR>"
> ```
>
> Прогон займёт примерно <N> минут — PowerShell будет показывать прогресс по постам. Когда увидишь строку `[batch_recognize] ИТОГ: ✓X ✗Y из N` — готово. Вернись сюда и напиши «готово». Я сам прочитаю результаты из `.business` и сделаю сводку.

### После «готово» от эксперта (ветки B/C)

Иди в `.business` и проверь сколько `.md`-файлов в `<ARCHIVE_DIR>` теперь имеют непустой `recognized_text`. Сравни с числом из dry-run. Соответствие — переходи к Фазе 3. Расхождение — спроси у эксперта, был ли в выводе батча `[batch_recognize] ИТОГ:` и сколько ошибок, попроси скопировать последние 30 строк.

## ФАЗА 3. Финальный отчёт

После прохода — сводка:

```
✓ Готово. Обработано 23 из 23 постов.

• Распознано: 22 (карусель: 15, рилз: 6, caption-only: 1)
• no_speech: 0
• Ошибок: 1
    - DXxXxYY (карусель) — apify scrape: HTTP 429 (превышен Apify-лимит)

• Расход: OpenAI $0.78, Apify $0.04, sian $0.02
• Всего: $0.84
```

Если есть ошибки — предложи:

> Хочешь повторить только ошибочные? Я могу позже запустить `find_targets.py` со списком конкретных ID, либо просто пройти ещё раз через `--force` по тем что без `recognized_text`.

После успешного прохода напомни о следующем шаге онбординга:

> Распознавание прошло. Если это первый онбординг (после ретро-скрапа №6) или если в архиве накопилось >20 каруселей и >20 рилзов — можно запускать скилл №8 «Стиль голоса по постам» (`stil-golosa-po-postam`) для эмпирического портрета стиля по каждому каналу.

## Утилиты в `scripts/`

Каждый скрипт — самодостаточный CLI с JSON-выводом в stdout и логами в stderr.

- **`batch_recognize.py`** — главная точка входа. Кроссплатформенная обёртка над всеми остальными: грузит `.env` через `python-dotenv`, вызывает `find_targets.py`, идёт по списку с прогрессом каждые 5 постов, на каждом посту вызывает соответствующий распознаватель и `write_recognized.py`. Падение одного поста не валит batch. Финальный отчёт — JSON в stdout, человекочитаемая сводка — в stderr. **Эту команду эксперт запускает и в режиме A (через osascript), и в режимах B/C (копи-паст).**

- **`find_targets.py`** — сканер папки. Парсит frontmatter через python-frontmatter, фильтрует по `network=="Instagram"` + `type` + `recognized_text==""`. Сортирует по `published` DESC. Возвращает JSON-массив.

- **`ocr_carousel.py`** — OCR одного поста Sidecar/Image. Apify `apify/instagram-scraper` (`addParentData: false`) → slide URLs → скачка слайдов параллельно (Semaphore=1, retry 3× с паузой 2 сек) → OpenAI Vision (gpt-4o) последовательно (Semaphore=1) с backoff 4/16/30/60/90/120 на 429. Cost считается по таблице tokens × price.

- **`transcribe_reel.py`** — транскрипция одного рилза. Apify `sian.agency/instagram-ai-transcript-extractor` с обязательным singular `instagramUrl`. `_extract_sian_transcript` проверяет что `item.url` содержит наш shortCode — защита от Zig Ziglar default. Правило 10 сек активируется при `duration ≤ 10` И `--caption > 100 chars`.

- **`write_recognized.py`** — безопасный update frontmatter через python-frontmatter. Сохраняет тело и порядок полей. Обновляет `recognized_text`, `status` (если не `--no-status-change`), `updated`.

- **`apify_client.py`** — общая async-обёртка над Apify REST (POST run + polling + GET items). Используется `ocr_carousel.py` и `transcribe_reel.py`. Без зависимости от `apify-client` Python SDK (он иногда падает на ImportError в зависимости от версии pydantic).

## Ограничения и формат

- Только Instagram-карусели и рилзы. Image (одиночное фото) технически работает через тот же OCR (`apify/instagram-scraper` отдаёт `type=Image`), но `find_targets.py` по умолчанию его не подбирает — в схеме `type=пост` для одиночных IG-фото и они редко требуют OCR. Если нужно — добавь `--type пост` руками.
- Telegram-посты не трогаем — `recognized_text` уже заполнен caption'ом. Фильтр в `find_targets.py` отсекает по `network != "Instagram"`.
- Один файл — одна транзакция. Падение не валит batch.
- Ключи только из env: `OPENAI_API_KEY`, `APIFY_TOKEN`. Никаких аргументов командной строки с секретами (история shell, ps).
- Запись только через `write_recognized.py` — Edit'ом руками не делай, можно сломать YAML-многострочное значение.
- Никаких изменений тела документа после frontmatter. `# Карусель от 30 апреля` и любой markdown ниже — нетронутые.
- Без офлайн-фолбэка: без OpenAI/Apify скилл не работает.

## Начало диалога

Начни с Фазы 0:

1. **0.1** — определи OS эксперта (Mac или Windows) и проверь доступность `mcp__Control_your_Mac__osascript` на Mac. Выбери режим A / B / C.
2. **0.2** — подтверди наличие `.env` с обоими ключами (`OPENAI_API_KEY`, `APIFY_TOKEN`).
3. **0.3** — установи зависимости (одноразово, через нужную для режима команду).
4. **0.4** — спроси/найди абсолютный путь к папке `записи/`.
5. **0.5** — уточни опции (типы, лимит, модель, force).
6. **Фаза 1** — обязательный dry-run для оценки объёма и стоимости.
7. **Фаза 2** — боевой прогон по нужной ветке (A/B/C).
8. **Фаза 3** — финальный отчёт и предложение что делать с ошибками.

Никогда не пытайся запускать `batch_recognize.py` или подскрипты через `mcp__workspace__bash` — это упрётся в `ProxyError 403` на первом же вызове sian.agency. Если ты как Claude чувствуешь искушение «попробую через bash, вдруг сработает» — нет, не сработает. Только через mac-host shell (osascript) или копи-паст в Terminal/PowerShell ученика.
