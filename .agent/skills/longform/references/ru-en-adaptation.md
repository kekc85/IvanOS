# Reference - RU ↔ EN Adaptation Rules

> Bilingual longform правила. RU и EN - разные структуры, разные lexicon, разные reference creators. Loaded в `01-finalize.md` Step 6 + `03-write.md` Pass 2.

## Главный принцип

**RU и EN - НЕ дословный перевод.** Это разные ниши с разным брендингом, разным позиционированием, разным market context.

| Аспект | RU | EN |
|---|---|---|
| Структура | Story-first | Argument-first |
| Tone | Тёплый-разговорный, теплее | Direct, tighter |
| Lexicon | Нельзяграм / Дубайск / контент-завод / вайбкодинг | Instagram / Dubai / content factory / vibe coding |
| Reference creators | Палий, Замесин, Афонина, Ширяев | Dan Koe, Justin Welsh, Sahil Bloom, Tim Ferriss |
| Examples | RU rates, RU products, RU кейсы | USD rates, EN products, EN кейсы |
| CTA | Подписаться / Telegram / VK | Subscribe / X / LinkedIn |
| Length | Средне (немного длиннее) | Средне-короче (tighter) |

## Структура - story-first vs argument-first

### RU canonical - story-first

```
INTRODUCTION (25-35%)  - расширена под story arc
├─ Hook (момент / observation)
├─ Personal anchor (длинная история / нарратив)
└─ Bridge to insight

INSIGHT (35-45%)        - теплее, разговорнее
├─ Main "aha"
├─ Why this works (через personal experience > first principles)
└─ Examples

PROCESS (25-35%)        - конкретный, но без strict step-by-step
└─ Lessons / principles + CTA
```

### EN canonical - argument-first

```
INTRODUCTION (12-18%)   - tighter, sharper
├─ Hook (counter-intuitive / specific outcome)
├─ Short personal anchor
└─ Bridge to insight

INSIGHT (50-60%)         - доминирует, first principles
├─ Main "aha" (явно declared)
├─ Why this works (3 reasons + first principles)
├─ Examples (specific numbers > stories)
└─ Counter-argument addressed

PROCESS (25-30%)         - actionable step-by-step
└─ Steps + pitfalls + CTA
```

## Lexicon swap

### RU обязательные замены

| EN/IT | RU |
|---|---|
| Instagram | Нельзяграм |
| Dubai (как город автора) | Дубайск |
| content factory | контент-завод |
| vibe coding | вайбкодинг |
| vibe marketing | вайбмаркетинг |
| solopreneur | соло-эксперт / соло-предприниматель |
| newsletter | рассылка / Newsletter (capitalized, как marker) |
| subscriber | подписчик |
| funnel | воронка |
| copy / copywriting | текст / тексты |
| onboarding | первичная настройка / запуск |

### EN обязательные замены (из RU)

| RU | EN |
|---|---|
| Нельзяграм | Instagram |
| Дубайск | Dubai |
| контент-завод | content factory |
| вайбкодинг | vibe coding |
| вайбмаркетинг | vibe marketing |
| соло-эксперт | solopreneur |
| личный бренд | personal brand |
| подписчик | subscriber |

## Тон / regiстр

### RU - тёплый-инженерный
- Разговорный: «понял», «дошло», «попробовал», «получилось»
- Без формализма: «именно поэтому», «таким образом», «следовательно» - banned
- Числа конкретные: «100К» (не «много»), «500К₽/мес» (не «значительный доход»)
- Личность автора в каждой секции
- Эмоциональные маркеры: «зацепило», «не поверил», «обалдеть»

### EN - direct & specific
- Active voice
- Short sentences for impact
- Specific dollar amounts, not «significant revenue»
- First name basis с reader (you / I, не people / one)
- Avoid formality: «I figured out» > «I came to understand»

## Examples - local relevance

### RU
- Numbers в рублях для большинства, USD только если контекст international
- Платформы: Kit / Beehiiv mention с пометкой «зарубежные сервисы»
- Платежи: «через посредников» / «карта Грузии / Казахстана / Турции»
- Tools: «n8n», «Make», «Claude» - same naming
- Local references: Telegram-каналы, ВКонтакте, GetCourse (если уместно)

### EN
- Numbers в USD
- Платформы: native naming (Kit, Beehiiv, ConvertKit, Substack)
- Tools: same naming
- Local references: Reddit, X, Indie Hackers, Hacker News

## Reference creators (для voice fidelity baseline)

### RU
- **Михаил Палий** - story essays, длинные, разговорные
- **автор Замесин** - framework essays, инженерные
- **Дарья Афонина** - образ жизни / soulful longform
- **Алексей Ширяев** - case studies / experiments

### EN
- **Dan Koe** - teaching / framework essays
- **Justin Welsh** - Saturday Solopreneur 5-step
- **Sahil Bloom** - story+framework hybrid
- **Tim Ferriss** - long-form mechanism / case study
- **Naval Ravikant** - first-principles compact essays

## CTA adaptation

| Cтратегия | RU | EN |
|---|---|---|
| Subscribe newsletter | «Подпишись на newsletter - еженедельная статья + воркфлоу» | «Subscribe to the newsletter - weekly essay + workflow» |
| Join club | «Заходи в клуб - closed comminity + воркфлоу + созвоны» | «Join the club - closed community + workflows + calls» |
| DM / reply | «Напиши в личку - если хочешь обсудить» | «DM me - if you want to chat» |
| Read more | «Читай ещё статьи в блоге» | «More essays on the blog» |

## Когда переводим vs переписываем

**Переводим близко к оригиналу (адаптация):**
- Headline / Subject lines (с lexicon swap)
- Specific numbers / examples / quotes (только конвертация валют)
- Process steps (actionable items одинаковы по сути)

**Переписываем (новый текст под аудиторию):**
- Personal anchor (RU = разговорный, EN = tighter scene)
- Cultural references (RU ниши / EN ниши разные)
- CTA destination (RU links vs EN links)
- Structural pacing (story-first vs argument-first)

## Bilingual workflow

В `config.bilingual_mode`:

### `ru_canonical`
1. Generate RU version по RU rules
2. Adapted EN version = отдельный output, генерится по запросу `--also-en`
3. EN = cross-post с rel="canonical" → RU URL

### `en_canonical`
1. Generate EN version по EN rules
2. Adapted RU version = отдельный output, генерится по запросу `--also-ru`
3. RU = cross-post с rel="canonical" → EN URL

### `mirror`
1. Generate both в одной сессии (последовательно)
2. Каждая имеет свой canonical URL с hreflang tags
3. Не одно vs другое - два равноправных canonical

В v1.0 - поддерживаем `ru_canonical` и `en_canonical`. `mirror` - v1.1+.

## Memory cross-refs

- - RU и EN разные направления
- - дословно vs переписать
- `[[multi-language-localization]]` - параллельный skill для C.3 EN ↔ RU adaptation
- - без жаргона
