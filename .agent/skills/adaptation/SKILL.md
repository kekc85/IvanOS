---
name: "adaptation"
description: "C.1 Same-Format Adaptation. Transform competitor's viral piece (Reel transcript / X-thread / video script) into Ivan's voice + category vibemarketing. Same format preserved."
---

# Same-Format Adaptation (C.1)

## Когда использовать

Когда есть **source piece** (чужой залетевший виральный контент) и нужно сделать **свою версию** в same format в voice автора.

Триггеры:
- "Adapt this Reel transcript: ..."
- "Сделай свою версию этого X-thread: ..."
- "Скопируй структуру этого LinkedIn post: ..."
- "Build-with-me видео adaptation: ..."

## Принципы adaptation

1. **Copy structure** - hook pattern + middle elements + climax + CTA pattern. Не контент, а скелет.
2. **Faster** - 24-72 часа от source publish для short formats, 1 неделя для long-form.
3. **More** - готовим под multi-account multiplication + cross-platform distribution.
4. **Better** - voice автора + категория вайбмаркетинг + slight angle twist (не radical innovation, 5-10% improvement).

## Гвардрейлы (применяются ВСЕГДА)

- **Источник голоса (graceful fallback, без hard-crash):** канон голоса = `.business/voice-corpus/_voice-profile.md`. ЕСЛИ файл есть → опираться на него. ЕСЛИ его нет / он пуст → fallback на `references/_voice-TEMPLATE.md` (если присутствует), ИНАЧЕ продолжить на нейтральном профиле голоса по гвардрейлам ниже + строка в чат «_voice-profile.md не найден, опираюсь на нейтральный профиль». НИКОГДА не падать на file-not-found из-за отсутствующего профиля.
- Voice автора: тёплый-инженерный, на "ты", горизонтально
- БЕЗ em-dash «—» внутри строк (только дефис «-» или запятая)
- БЕЗ техжаргона методологии в публичной части ("артефакт" / "контур" / "фасилитация" / "Grand Slam Offer")
- Категория = **вайбмаркетинг** (вайбкодинг = инструмент внутри)
- Lexicon: **Нельзяграм** не Instagram, **Дубайск**, **контент-завод**, **ферма**, **перегнать**, **пдп**
- БЕЗ атак конкурентов по именам
- БЕЗ выдуманных фактов / цифр (только из real track record автора: <твоя выручка> 2025, <число учеников>, ИП <твои реквизиты> с образовательной лицензией)
- БЕЗ negative статистик ("20% доходят" убивает продажи)
- Common Enemy = рыночное явление, не имя

## Шаги работы

### Шаг 1: Разобрать source structure
Извлечь из source piece:
- Hook (первые 3 секунды / 1-2 строки)
- Pacing / middle elements (количество beats, длительность)
- Climax / peak moment
- CTA pattern (subscribe / save / DM / link)
- Visual format (если video: vertical / split-screen / talking head / screen-record / etc)

### Шаг 2: Проверить virality × deficiency
- Залетело ли у source в первые 3-4 дня? (если данных нет - предположить да если попало в feed)
- Свежая ли идея (max 1 неделя для short, 2-3 недели для long)?
- Если оба нет - **DROP**, не adapting

### Шаг 3: Adapt контент в структуру
- Свой content в same structure
- Угол на категорию вайбмаркетинг
- Voice автора (применить все гвардрейлы выше)
- Если visual format - указать что нужно записать / сгенерировать

### Шаг 4: Output adaptation

Format output:
```
**Source структура**:
- Hook: [original]
- Structure: [N beats / pattern]
- CTA: [original CTA pattern]

**Adapted draft в voice автора**:
- Hook: [твой]
- Body: [твоя версия]
- CTA: [твой CTA]

**Production notes**:
- Format: [Reel / X-thread / LinkedIn post / etc]
- Tooling: [Tella + CapCut / HeyGen + ElevenLabs / etc]
- Estimated production time: [X hours]
```

## Что НЕ делаем

- Дословное копирование (это плагиат)
- Менять формат (Reel → YouTube long-form = НЕТ, это cross-format)
- Original content из нуля
- Documenter контент о своих запусках
- Educational теория без proven engagement
- Атаки конкурентов по именам

## Связано

- `.business/processes/acquisition-methodology.md` - полная методология
- Voice Corpus в `.business/voice-corpus/` (канон `_voice-profile.md`; если отсутствует - fallback `references/_voice-TEMPLATE.md` → нейтральный профиль, см. гвардрейлы)
- Memory: project-content-factory-principles + feedback-strategy-copy-faster-more-better
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


---

## Variation Rotation Gate (HARD, анти-шаблон — ДО write)

ОБЯЗАТЕЛЬНО прочитать и применить `_shared/variation-rotation-gate.md` ПЕРЕД написанием. Прогнать ротацию по 4 осям (Hook type / Opening type / Narrative structure / Archetype) против источника «последних постов» (история канала ИЛИ `<project-pack>/variation-log.md` если истории нет) и **вывести в чат декларацию вариативности** (4 оси × «другой ✓»). Любая ось совпала с последними 2-3 → переписать, не выдавать. После выдачи — дописать строку в `variation-log.md`.

Это улика, что rotation-gate реально прогнан (а не пропущен по поверхностному чтению). Прецедент по решению автора: два поста подряд на одном скелете. Память `feedback_rotate_post_axes_every_time`.

---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
