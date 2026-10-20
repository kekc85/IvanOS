# Tech-jargon Explanation List (mandatory disclosure)

> Hard gate в `04-review.md` Pass 1.6. Каждый technical term из этого списка ОБЯЗАТЕЛЬНО раскрывается в первом упоминании в тексте. Иначе FAIL с конкретным suggestion раскрытия. Memory rule: `feedback_explain_marketing_jargon`.

## Принцип

Newsletter / blog reader НЕ обязательно senior vibemarketing / vibe coding ICP. Каждый technical term который выходит за пределы общего lexicon должен быть раскрыт **в первом упоминании в тексте** в формате:

```
TERM (это <короткое определение в 5-10 слов>)
```

или 

```
TERM, это <короткое определение>
```

Если term упоминается без раскрытия - FAIL.

## Mandatory disclosure list

### AI / pipeline terms

| Term | Минимальное раскрытие |
|---|---|
| OCR | OCR (распознавание текста на изображении) |
| TTS | TTS (синтез голоса из текста) |
| LLM | LLM (большая языковая модель типа Claude/GPT) |
| voice clone | клонирование голоса (модель учится говорить твоим голосом) |
| AI avatar | цифровой двойник (модель учится отображать твоё лицо) |
| ingest | загрузка чужого видео и разбор на части |
| motion blocks | блоки анимации с готовыми параметрами движения |
| easing curves | кривые ускорения для плавного движения |
| Material motion tokens | токены анимации из дизайн-системы Material Design |
| storyboard | раскадровка |
| catalog (motion) | библиотека готовых блоков анимации |

### Marketing terms (memory feedback_explain_marketing_jargon)

| Term | Раскрытие |
|---|---|
| JTBD | JTBD (Job-to-be-Done, какую задачу пользователь выполняет) |
| ICP | ICP (Ideal Customer Profile, портрет идеального клиента) |
| LTV | LTV (Lifetime Value, доход с клиента за всё время) |
| CAC | CAC (Customer Acquisition Cost, стоимость привлечения клиента) |
| 3M | 3M (Market / Message / Media - модель Sprint Beyond) |
| AARRR | AARRR (метрики Acquisition / Activation / Retention / Referral / Revenue) |
| Core Four | Core Four (модель 4 каналов привлечения от Hormozi) |
| open rate | процент открытий писем |
| CTR | CTR (click-through rate, процент переходов по ссылке) |
| funnel | воронка (последовательность этапов от первого касания до покупки) |
| lead magnet | лид-магнит (бесплатный материал в обмен на email) |
| POSSE | POSSE (Publish on Own Site, Syndicate Elsewhere - публикация на своём сайте с rel="canonical" cross-post) |

### Skill-specific (vibemarketing terms)

| Term | Раскрытие |
|---|---|
| Карта смыслов | Карта смыслов (план какие тезисы раскрываются на каждой неделе запуска) |
| контент-завод | контент-завод (производство 5-10 рилзов в день одним человеком через AI-стек) |
| вайбкодинг | вайбкодинг (разработка приложений в диалоге с Claude Code) |
| вайбмаркетинг | вайбмаркетинг (маркетинговые кампании через AI-стек одним человеком) |
| ингест | ингест (скачивание чужого видео и разбор на части) |

## Whitelist (когда раскрытие НЕ нужно)

Term **не** требует раскрытия если:

1. **Brand noun** (n8n, Claude, HeyGen, ElevenLabs, Kling, Remotion - это всем понятные продукты в нише, не общие концепты)
2. **Уже раскрыто в этом же тексте раньше** - повторное упоминание OK
3. **Часть RU lexicon автора** (Нельзяграм, Дубайск - это уже устаканенные термины автора, аудитория знает)
4. **Цитата / прямая речь** в кавычках

## Hard regex check (04-review.md Pass 1.6)

```
for term in mandatory_disclosure_list:
    if term in text:
        first_occurrence_index = text.find(term)
        # check 100 char window after first occurrence
        context_after = text[first_occurrence_index : first_occurrence_index + 200]
        if not has_disclosure_pattern(context_after, term):
            FAIL with suggestion: "Term '{term}' upомянут без раскрытия. Добавь в первом упоминании: '{term} ({minimal_disclosure})'"
```

Disclosure pattern detection:
- `TERM ` + parenthesis open `(` within 30 chars
- TERM + `,` + `это` / `i.e.` / `типа` / `буквально` within 50 chars  
- TERM + dash + definition within 50 chars

## Memory cross-refs

- - главное правило
- - generic = brak