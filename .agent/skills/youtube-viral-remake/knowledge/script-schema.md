# script-schema - card.md (16:9 long-form) под контракт скилла `video`

Фаза 02 деконструирует источник в `card.md`, который читает и парсит скилл `video`
(`workflow/01c-replication.md`, Mode C). Схема ниже **изоморфна тому, что video реально парсит** -
сверено живьём с рабочей ingest-карточкой и с шагами 3-9 01c-replication. Отступишь от дословных
заголовков или структуры Spec-JSON - `video` не найдёт поля и Validate readiness упадёт

## 1. Куда кладётся (иначе video не резолвит)

`video` резолвит источник через `ls ~/.business/growth/ingest/<папка>` и читает `card.md` ОТТУДА,
а не по произвольному пути. Поэтому фаза 02 кладёт card в **ingest-совместимую папку**:
`~/.business/growth/ingest/<YYYY-MM-DD-VIDEO_ID>/card.md`. Вызов далее - `video --replicate <VIDEO_ID>`

## 2. Что именно парсит video (сверено с 01c шаги 3-9)

- **Шаг 3 - YAML frontmatter**: `url`, `author`, `duration_sec` (→ length_tier), `language`,
  `format_classification.primary`
- **Шаг 4 - секции с ДОСЛОВНЫМИ русскими заголовками**: `## Транскрипт`, `## Структура`,
  `## Spec для replication` (JSON-блок: `voice_script_brief` / `narrative_arc` / `format_type` /
  `visual_layers` / `captions`), `## Главный insight`, `## Применимость для контент-завода автора`
- **Шаг 5 - маппинг duration_sec → tier**: `601+` → `long-10-60min` (наш случай)
- **Шаг 9 - Validate readiness требует ТОЛЬКО**: `voice_script_brief` непустой + `narrative_arc` ≥2
  beats + `main_insight` (из «Главный insight») существует + `duration_sec` > 0. Всё - других
  обязательных полей на этом гейте нет

**format_classification НЕ обязателен для прохода.** Для long-form ставим `primary: "youtube-longform"`
строкой. Vertical format-library (`ingest-reel` living doc) НЕ трогаем - это её каталог форматов
вертикали, наш long-form туда не пишем

## 3. Полный шаблон card.md (16:9 long-form) - готов к заполнению фазой 02

```markdown
---
url: <YouTube-URL источника>
platform: YouTube
author: <канал / автор>
duration_sec: <целое, 601+>
language: <en | ru>
views: <число или n/a>
ingested: <YYYY-MM-DD>
format_classification:
  primary: "youtube-longform"      # строка, для long-form не трогаем vertical library
  aspect_ratio: "16:9"
  confidence: n/a
  reasoning: "Long-form YouTube (10-60 мин, 16:9). format_classification не обязателен для video Validate readiness (01c Шаг 9) - ставим строку youtube-longform."
---

# <короткое имя ролика / формата>

## Транскрипт
<Дословный текст с таймкодами глав. youtube-transcript (VTT) + whisper --word_timestamps где нужен
word-level. Дословно, не парафраз - терминология автора важнее переформулирования.>

## Структура
<Узлы удержания по таймкодам (см. longform-structure.md §1). Пример строк:>
- **0:00-0:30 - Hook:** <дословный хук + какой визуальный пруф на 1-й секунде>
- **0:30-1:30 - Promise/Preview:** <что обещано к концу, какая главная петля открыта>
- **1:30-6:00 - Глава 1 «<имя>»:** <мини-хук главы> · <тезис> · open loop: <что обещано впереди>
- **6:00-12:00 - Глава 2 «<имя>»:** <мини-хук> · <тезис> · ставка выше Главы 1
- ... (5-9 глав, у каждой мини-хук + мини-развязка)
- **<t> - Payoff:** <выплата главного обещания хука>
- **<t> - Synthesis:** <одна мысль, что зритель уносит>
- **<t> - CTA/Outro:** <единственное действие по role, последним кадром>

## Spec для replication
```json
{
  "format_type": "youtube_longform_<slug>",
  "aspect_ratio": "16:9",
  "duration_target_sec": <целевая длина, 601+>,
  "hook_strategy": "<напр. proof_first_second_promise>",
  "voice_script_brief": "автор: <бриф скрипта в голосе автора на всю длину - хук + промис + главы + payoff + synthesis + CTA, с таймингом по узлам. НЕПУСТОЙ (иначе Validate readiness падает). outcome для ЦА - не 'программирование/MVP/SaaS/приложение/разработчик', а 'мини-продукт / цифровой продукт эксперта'.>",
  "narrative_arc": [
    {"sec": "0:00-0:30",  "beat": "hook",      "content": "<хук + пруф>"},
    {"sec": "0:30-1:30",  "beat": "promise",   "content": "<обещание + главная петля>"},
    {"sec": "1:30-6:00",  "beat": "chapter_1", "content": "<мини-хук + тезис + open loop>"},
    {"sec": "6:00-12:00", "beat": "chapter_2", "content": "<мини-хук + тезис + эскалация>"},
    {"sec": "...",        "beat": "chapter_N", "content": "<...>"},
    {"sec": "...",        "beat": "payoff",    "content": "<выплата обещания>"},
    {"sec": "...",        "beat": "synthesis", "content": "<одна мысль>"},
    {"sec": "...",        "beat": "cta",       "content": "<единственное действие по role>"}
  ],
  "visual_layers": [
    {"track": "speaker",    "source": "camera_or_avatar", "position": "bookend_hook_cta_chapter_anchors", "crop": "16:9"},
    {"track": "screencast", "source": "screen_record_or_cdp_or_official_footage", "position": "fullscreen", "note": "реальный UI - только живой захват + провенанс URL, НИКОГДА мок (engine-boundary.md)"},
    {"track": "motion",     "source": "hyperframes_or_higgsfield", "position": "chapter_titles_diagrams_metaphors", "note": "ТОЛЬКО абстракции/диаграммы/титры/данные-в-движении, НЕ реальный UI"}
  ],
  "captions": {"style": "clean_bold", "position": "lower_third_outside_screencast", "note": "keep-out: ноль оверлеев поверх скринкаста реального UI"},
  "assembly": {"engine": "scripts/assemble.sh", "method": "по главам: hyperframes ≤N сек/композиция + ffmpeg concat глав, аутро последним"}
}
```

## Главный insight
<Одна управляющая мысль, что ролик доказывает (Макки controlling idea / Андерсон through-line).
ОБЯЗАТЕЛЕН для Validate readiness. Формула: ЦЕННОСТЬ + ПРИЧИНА, утверждение а не тема.>

## Применимость для контент-завода автора
<Как ложится на тему автора (вайбкодинг + нейросети, Claude Code). Сценарии воспроизведения под RU
и EN. Учесть role (acquisition / launch-lead-magnet) и outcome-language-гейт. Риски: не атаковать
конкурентов по имени; higgsfield под гардом.>
```

## 4. Минимальный набор для прохода Validate readiness (self-check фазы 02 до вызова video)

Card проходит `video` Mode C только если есть, все непустые:
- frontmatter: `url` + `author` + `duration_sec` (>0) + `language`
- `## Транскрипт` (дословный)
- `## Структура` (узлы по таймкодам)
- `## Spec для replication` с непустым `voice_script_brief` + `narrative_arc` ≥2 beats
- `## Главный insight` (непустой)
- `## Применимость для контент-завода автора`

Чего-то нет → фаза 02 не вызывает video, а достраивает card (не подделывает пустышкой)
. Дословные заголовки - буква в букву, video
ищет их точным совпадением

## 5. Что отдавать в чат vs в файл

В файл - полный card по схеме. В чат автору - компактно: ссылка на источник + путь к card +
логлайн + главный insight одной строкой + число глав + tier. Не дублировать весь card в чат
