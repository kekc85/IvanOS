---
name: "multi-language-localization"
description: "C.3 EN ↔ RU content adaptation. Не дословный перевод, культурная адаптация. Правила что переводится, что переписывается полностью"
---

# Multi-Language Localization EN ↔ RU (C.3)

## Когда использовать

После создания EN content - generate RU version (или обратно RU → EN).

Триггеры:
- "Localize this Reel transcript для RU"
- "Translate X-thread на RU"
- "Adapt этот LinkedIn post в EN"

## Background

EN → RU = культурная адаптация, не translation. Дословный перевод фейлит (другой narrative структура, другой юмор, другие соц-доказательства).

Reference: memory `feedback_ru_en_content_adaptation_rules`.

## Что переводится дословно (sameness)

- Механика хука (pattern interrupt → claim → proof structure)
- Монтажный ритм видео
- B-roll choices
- Subtitle-first approach
- Visual format (split-screen / разворот камеры / talking head)
- Thumbnail style

## Что переписывается полностью (rebuild)

### 1. Структура нарратива
- **EN**: тезис → аргументы → conclusion
- **RU**: история → вывод

EN script: "Most people are wrong about X. Here's why: [3 arguments]"
RU script: "Я думал X. Но потом случилось Y. И понял Z" (story-driven)

### 2. Юмор / идиомы
- Полностью пересобирается с нуля
- EN sarcasm = другой регистр в RU
- RU юмор build на context punchlines

### 3. CTA
- **EN**: "Drop a comment", "Subscribe", "Link in bio"
- **RU**: "Напиши «хочу» и пришлю" (личный триггер с именем автора + конкретное действие + emotional hook)

### 4. Соц-доказательство
- **EN**: цифры дохода ("$10K MRR")
- **RU**: количество людей + личная история ("<число учеников> автора / <твоя выручка>")

### 5. Hook эмоция
- **EN**: confidence, authority, results-driven
- **RU**: vulnerability, journey, "я думал X, оказалось Y"

## RU-specific patterns (только в RU)

- **Цифра + личная драма в first second**: "Я слил 100К на рекламу"
- **Дневник / исповедь** формат (Маргоша pattern)
- **Конфликт с системой**: "Эксперты говорят X, я сделал по-другому"
- **Субтитры с провокацией** в первые 1-2 sec (RU алгоритм давит low-retention сильнее EN)

## Шаги localization

### Шаг 1: Identify content type
- Reel / Short / TikTok script
- X-thread / LinkedIn post / carousel
- Newsletter / long-form article
- YouTube long-form

### Шаг 2: Extract reusable elements
- Hook mechanic (structure pattern)
- Visual format
- B-roll concept
- Pacing / cuts

### Шаг 3: Rebuild narrative структуру
- EN тезис-первый → RU история-первая
- Personal story → universal lesson (RU pattern)

### Шаг 4: Replace cultural elements
- USD → ₽ (с примерным conversion)
- EN names (Hormozi/Welsh) → RU equivalents если применимо (Бали, Артемий Миллер) OR remove
- US-specific brand references → RU equivalents
- US idioms → RU equivalents

### Шаг 5: Apply RU lexicon автора
- Нельзяграм (НЕ Instagram, ЖЁСТКО)
- Дубайск (Dubai)
- контент-завод, ферма, перегнать, пдп

### Шаг 6: RU CTA personalization
- Personal trigger word ("хочу" / "+" / "1")
- Author name reference
- Emotional hook

### Шаг 7: QC checklist
- Звучит ли как родной RU или как перевод?
- Структура story-first (не argument-first)?
- Lexicon applied (Нельзяграм / etc)?
- БЕЗ em-dash в строках?
- БЕЗ negative статистик?

## Output format

```
**Source language**: EN
**Target language**: RU
**Content type**: [Reel script / X-thread / etc]

**Source content (EN)**:
[paste original]

**Localized version (RU)**:
[full RU adapted version]

**Key adaptations made**:
1. Narrative: тезис-first → story-first
2. CTA: "Drop a comment" → "Напиши «хочу» и пришлю"
3. Соц-доказательство: "$10K MRR" → "<число учеников> / <твоя выручка>"
4. Lexicon: Instagram → Нельзяграм
5. Hook: [specific change]
6. Examples localized: [list]

**Production notes RU**:
- Voice clone tool: ElevenLabs PVC (Russian PVC trained)
- HeyGen Avatar (если video) - face <30% screen, ≤60 sec clip
- Subtitle font: bold yellow / white outlined (RU аудитория screen-reading more)

**QC**:
- [ ] Native RU sound, не перевод
- [ ] Story-first narrative
- [ ] Lexicon applied
- [ ] No em-dash
- [ ] No negative stats
- [ ] CTA personalized
```

## Tools

- **Claude C.3 prompt** (this skill)
- **Reap MCP** auto-dubbing 80 языков - для quick translation, не для voice cloning quality
- **HeyGen voice clone Russian** PVC - для voice
- **ElevenLabs PVC** trained на 30-60 min clean Russian audio

## Anti-patterns

- Дословный перевод EN → RU = провал
- Instant ElevenLabs clone для Russian (дрифтит)
- HeyGen avatar >60 sec без accent QC
- EN CTA "Drop comment" дословно
- EN USD без conversion в ₽

## Связано

- Memory: `feedback_ru_en_content_adaptation_rules` (полные правила)
- Memory: `user_lexicon` (Нельзяграм / Дубайск / etc)
- Memory: `project_ai_avatar_cheung_pipeline` (Russian PVC setup)
---

## Финальная фаза — Humaniser (HARD GATE для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Вызови Skill tool: `Skill('humaniser', args=<финальный текст>)` ПЕРЕД любым output. НЕ читай humaniser/prompt.md inline и НЕ применяй mentally — это shallow execution которое пропускает AI-tics. Только полный pass через Skill tool invocation документированный в чате.

Humaniser v2 ловит 11 категорий AI-паттернов:
1. Ложная глубина
2. Фальшивая близость
3. Пустые связки
4. Канцелярит
5. Fake-энергия
6. Шаблонные призывы
7. Рубленые фразы (3+ из 1-2 слов подряд)
8. Кинематограф
9. Структурные клише
10. Интонационные клише
11. **Slap-эмфаза (длинное + 1-3-словное короткое для эмфазы) — главный AI-tic социалок 2025-2026**

**HARD GATE:** Output финального текста ТОЛЬКО после green CHECKER (все 5/5 в «Клише удалены»). Если CHECKER не green — REWRITER ещё раз. Без этого = брак.

**Прецеденты:**
- 2026-05-28: post v3.0 выдал «Zero ads. Zero funnels. Zero sales calls.» (triple-negation AI tic)
- 2026-05-29: caption выдал «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, новая категория 11)

Оба = провал shallow inline pass. HARD GATE через Skill tool решает.

### Humaniser Inline Reminder (fallback если Skill tool недоступен)

Перед output финального текста — проверь по 11 категориям AI-tics:

1. Ложная глубина («Это не X, это Y», «Секрет в том»)
2. Фальшивая близость («Знакомо?», «Представьте»)
3. Пустые связки («Давайте разберёмся», «Важно понимать»)
4. Канцелярит («В современном мире», «Является неотъемлемой»)
5. Fake-энергия («Спойлер», «Бонус», «Лайфхак»)
6. Шаблонные призывы («Хватит X», «Перестаньте X начните Y»)
7. Рубленые фразы (3+ предложения подряд из 1-2 слов: «Просто. Быстро. Эффективно.»)
8. Кинематограф («Воскресенье, 10 вечера», «Понедельник, 9 утра»)
9. Структурные клише (параллелизм X/Y/Z, всегда 3 пункта)
10. Интонационные клише («невероятно простой!», «истина в том»)
11. **Slap-эмфаза**: короткое standalone (1-3 слова) после длинного для эмфазы. SMELL TEST: «можно ли слить через запятую?». YES → SLAP, слить. Исключения: structural separator перед list / hook / punchline finale.

Прецеденты провала которые этот block ловит:
- post v3.0 2026-05-28: «Zero ads. Zero funnels. Zero sales calls.» (triple-negation, cat 7+9)
- caption 2026-05-29: «Бесплатно. 30 минут работы и ожидание ответа.» (slap-эмфаза, cat 11)

При нахождении любого pattern → REWRITER (переписать) → re-CHECKER → если clean → output.

