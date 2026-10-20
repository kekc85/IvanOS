# Integration guide для content-skills

Как каждый sister content-skill должен интегрировать shared empirical layer.

10 skills в семействе на 2026-05-28:
- `video` — script для videos (15 sec - 60 min)
- `post` — long narrative posts (TG / LinkedIn)
- `longform` — 800-3000 слов (newsletter / blog / LinkedIn article)
- `email` — Subject + Body для ESP
- `bot-message` — TG push 100-300 знаков
- `carousel` — multi-slide (Instagram / LinkedIn)
- `single-image` — статичная картинка-пост
- `paips-post` — PAIPS story
- `spiky-one-liner` — contrarian тwitter-style
- `tweet` — X / Threads

---

## Required Mandatory Reads per skill

В Pass 0 каждый skill должен Read следующие файлы из shared layer:

| Skill | hook-patterns | body-structure | cta-patterns | voice-markers | authority | funnel | audience-glossary | visual-formats | form-canon-v2 |
|---|---|---|---|---|---|---|---|---|---|
| video | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| post | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| longform | ✓ partial | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| email | ✓ for Subject | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| bot-message | ✓ partial | — | ✓ | ✓ | — | ✓ | ✓ | — | - |
| carousel | ✓ for slide 1 | partial | ✓ | ✓ | partial | ✓ | ✓ | ✓ | ✓ для caption |
| single-image | partial | — | partial | ✓ | partial | ✓ | ✓ | partial | - |
| paips-post | ✓ | — | ✓ | ✓ | partial | ✓ | ✓ | — | - |
| spiky-one-liner | ✓ short patterns | — | — | ✓ | partial | partial | ✓ | — | - |
| tweet | ✓ | partial | partial | ✓ | partial | ✓ | ✓ | — | ✓ |

`form-canon-v2` = `.business/voice-corpus/_format-canon-v2.md`, канон формы под цель (v2.3). Отмечен ✓ - значит скилл обязан прочитать его в Pass 0 и объявить цель формы (R реакции / F репосты / S продажа / A реакция-гейт) до первой строки текста. В `carousel` профиль применяется к caption, анатомия слайдов остаётся своей. Прочерк = скилл канон формы не читает, работает на прежних дефолтах

---

## Ранг канона формы в иерархии источников (NEW 2026-08-03)

Порядок источников для ВСЕХ пяти текстовых скиллов (`post`, `longform`, `email`, `tweet`, `carousel`). Уровень выше переписывает уровень ниже, а не дополняет его. Конфликт разрешается вслух, строкой-уликой `конфликт: <правило A> vs <правило B> -> взял <A> по уровню N`:

1. Реальность и факты, запрет выдумки
2. Прямое указание автора в этой сессии
3. Голос автора (`.business/voice-corpus/_voice-profile.md`, корпус `A-telegram/`) - лексика, интонация, табу
4. Слой 0 «Деньги» и Sales Gate 4.S - только при `launch_window = true`
5. **Канон формы v2.3** (`.business/voice-corpus/_format-canon-v2.md`) - форма под цель
6. `.business/voice-corpus/_donor-format-canon.md` v1 - **опущен до уровня 6, отменён как источник норм**; остаются только неизмеренные в v2 наблюдения слоя «приёмы подачи», и то как гипотезы
7. Плоские дефолты скиллов - fallback там, где молчат уровни 5 и 6 (таблицы длин по типам, пороги приёмов, потолки списков, Blueprint Gate, Hook Char Zone Gate)
8. Generic-каркасы (Брансон, atomic essay, 15 LinkedIn-хуков)

Что это меняет по сравнению с прежним стихийным попарным приоритетом «голос > донор-канон»: числовые нормы формы теперь берутся из ПРОФИЛЯ ЦЕЛИ, а не из плоской таблицы v1. Старые числовые правила скиллов не удалены - они становятся fallback-веткой «если `brief.form_goal` пуст», то есть при необъявленной цели система ведёт себя ровно как раньше. Принуждение живёт в самих скиллах (вход-гейт в `03-write` и Гейт 0 в `04-review`), здесь только декларация ранга

---

## Pattern applicability matrix

Не каждый hook pattern переносим в каждый format. Mapping:

| Pattern | video | post | longform | email | bot | carousel | single-img | paips | spiky | tweet |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 — Why would you X | ✓ | ✓ | ✓ | ✓ Subject | ✓ | ✓ slide 1 | ✓ caption | ✓ | ✓ | ✓ |
| 2 — Conditional benefit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | partial | ✓ |
| 3 — Inevitability | ✓ + auth | ✓ + auth | ✓ + auth | partial | partial | ✓ + auth | partial | partial | ✓ | ✓ |
| 4 — Anti-pattern → solution | ✓ | ✓ | ✓ | ✓ | partial | ✓ | partial | ✓ | partial | partial |
| 5 — Numeric outlier | ✓ verify | ✓ verify | ✓ verify | ✓ | partial | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6 — Timeframe + outcome | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7 — N-step system | ✓ | ✓ | ✓ | ✓ | partial | ✓ | partial | partial | — | partial |
| 8 — Brand reactor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | partial | ✓ | ✓ |
| 9 — Self-deprecating | ✓ | ✓ | ✓ | ✓ | partial | partial | partial | ✓ | partial | partial |

«✓ + auth» = требует authority proof per `authority-namedrop-pattern.md`
«✓ verify» = число должно быть verified
«partial» = адаптация требуется

---

## Benchmark Gate integration

Каждый sister skill должен иметь Benchmark Gate в review stage:

### For video-format skills (`video`, `carousel`, `single-image`)
- Compare output structure vs nearest 3 шорта из corpus
- Visual format match required
- Score /7 (см. video/workflow/05-review.md 5.4.5)

### For text-format skills (`post`, `longform`, `email`, `bot-message`, `paips-post`, `spiky-one-liner`, `tweet`)
- Compare hook structure vs 9 patterns
- Compare CTA mechanic vs 5 types
- Voice markers cross-check
- Audience glossary clean check (avoid-list terms)
- Score /6 (без visual)

Cutoff:
- 4+/6 PASS for text
- 5+/7 PASS for video
- WARN/FAIL → escape с reasons

---

## Funnel-awareness universal requirement

ВСЕ content-skills должны иметь funnel destination в output. Без исключения.

CTA mapped to:
- TOFU (discovery) — drop-mic, brand reactor
- MOFU (capture) — comment trigger, URL, save
- BOFU (conversion) — registration link, cash event signup

См. `funnel-awareness.md` для checklist.

---

## Audience glossary universal requirement

ВСЕ content-skills должны прогнать output через audience-glossary.md avoid-list:
- skill → мини-приложение
- config → настройка
- command → один промпт
- infrastructure → система
- etc.

Auto-fail если avoid-list terms detected без перевода.

---

## Business mechanism integrity universal requirement (NEW 2026-05-31)

ВСЕ content-skills обязаны держать раздельно два механизма бизнеса и не связывать их причинно:
- **Контент-завод 2.0** = acquisition в Нельзяграме/TikTok/Shorts (рилсы, карусели)
- **Карта смыслов** = source of truth для контента ЗАПУСКА в Telegram

Запрещено писать, что ролики/карусели «работают по карте смыслов» или что устойчивость к бану держится на карте смыслов. Бан Нельзяграма бьёт по контент-заводу, а НЕ по карте смыслов. Полная карта + запрещённые связки — в `funnel-awareness.md` раздел «Два независимых механизма». Прецедент 2026-05-31.

---

## Анти-вода universal requirement (Ильяхов «Пиши, сокращай», NEW 2026-05-31)

ВСЕ content-skills прогоняют output через humaniser, где это закреплено как категория 16 «Вода и плеоназмы». Главный лов — синонимичная пара «X и Y», где Y дублирует X («упущенная прибыль и недозаработанные деньги»). SMELL TEST: «Y несёт факт, которого нет в X?» Нет → удалить второй член. Плюс резать стоп-слова, оценки вместо фактов, лишние «который». Прецедент 2026-05-31.

---

## Implementation roadmap per sister skill

### `video` v1.1 (COMPLETED 2026-05-28)
- Pass 0 Mandatory Reads → shared layer
- 5.4.5 Benchmark Gate в review

### `post` (next)
- Patch config.md mandatory_reads → add 6 shared files
- Add Benchmark Gate в review pipeline
- Test on real post task

### `longform` (after post)
- Same pattern as post
- + длинная форма requires authority proof per Pattern 3 / 7

### `email` (after longform)
- Subject line gets hook pattern treatment
- Body gets walkthrough structure (если sequence/launch)
- A/B subject 3-5 still required

### `bot-message`
- Hook applies to message text first sentence
- CTA = button (Type 1 comment trigger applies к auto-response logic)

### `carousel`
- Slide 1 = hook (Pattern 1-9)
- Slide N (last) = CTA (Type 1-5)
- Visual format inherits from video Format A/B/C/D

### `single-image`
- Caption gets hook treatment
- Image follows visual format archetype

### `paips-post`, `spiky-one-liner`, `tweet`
- Hook structures apply
- Voice markers cross-check
- Funnel destination required

---

## Maintenance protocol shared layer

- **Weekly:** add 5-10 fresh viral examples ingestов с watchlist
- **Monthly:** re-rank corpus, update top 30
- **Quarterly:** full pattern re-extraction
- **При platform algorithm change** (Reels / Shorts / TikTok / LinkedIn / X) — emergency re-extract

При обновлении shared layer:
1. Update relevant empirical file
2. Bump version в README.md
3. Notify через memory `[[project-extracted-patterns-shared-layer]]`
4. Sister skills don't need re-deploy (они читают current state)

---

## Cross-refs

- `README.md` — overview shared layer
- Все 10 shared layer files в `.business/growth/extracted-patterns/` (боевой путь; `~/.business` - симлинк на шаблон IvanOS, читать оттуда нельзя)
- Канон формы под цель в `.business/voice-corpus/_format-canon-v2.md`, журнал формы в `.business/voice-corpus/_form-log.md`
- 10 sister content-skills в `~/.claude/skills/<name>/`
