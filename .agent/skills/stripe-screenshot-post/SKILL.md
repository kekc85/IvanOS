---
name: "stripe-screenshot-post"
description: "[DEPRECATED 2026-05-28] Замещён скиллом `single-image` v1.0 как type=dashboard-screenshot. Используй `/single-image` с type=dashboard-screenshot (Pieter Levels / Marc Lou style real metric reveal + bilingual caption). Этот SKILL.md остался как pointer для backwards-compat и для users, которые вызывают по старому имени."
---

# Stripe Screenshot Post - DEPRECATED → single-image

## Status

**DEPRECATED 2026-05-28.** Замещён `single-image` v1.0 как один из 5 типов (dashboard-screenshot).

## Что делать

### Вариант A: использовать новый skill

```
/single-image про <metric reveal>
--type=dashboard-screenshot
```

Получишь:
- Visual brief (composition / verbatim text / privacy blur instructions)
- Tool prompt (screenshot tool + Photopea/Figma polish steps)
- Bilingual caption (RU + EN, 3 варианта на язык)
- Cross-distribution (X primary + LinkedIn Multi-Image Sequential)
- Verification check для real numbers (через `.business/` или explicit user-provided)

### Вариант B: продолжить как раньше

Старый скилл - simple Stripe screenshot generation. Если хочешь minimal output - можешь продолжать. Но рекомендуется переход.

## Что было в этом skill

Generator dashboard screenshot posts в Pieter Levels / Marc Lou style:
- Single tweet/post: Stripe dashboard screenshot + 1-3 lines caption
- Cross-distribution: X single, LinkedIn Multi-Image Sequential (4 images)

Hook patterns: Just achieved / Confession / Specific number first / Pat-Walls style.

## Почему deprecated

`single-image` v1.0 покрывает dashboard-screenshot type с full pipeline:
- Verification gate для real numbers (verified или fail)
- Privacy blur instructions (customer names / emails / IDs)
- AI-generation disallowed (real screenshot only)
- Cross-distribution full (X / LinkedIn Multi-Image / Threads / TG)
- 6-Pass review (catch выдуманные numbers / negative stats / misleading crops)
- Bilingual caption

Старый - thin slice. Новый - full architecture с safety gates.

## ВАЖНО про real numbers

Оба skill - старый и новый - не разрешают выдуманные numbers. `single-image` имеет explicit verification step:
- Number должен быть в `.business/economics/revenue.md` ИЛИ explicitly provided в текущей session
- AI-generated dashboard = brand suicide if detected

Реальные verified автора (из /):
- <твоя выручка> revenue 2025 (cash events)
- 800+ выпускников
- <размер базы> <твой-хэндл>
- 500K+ суммарный reach

## Migration

Старые применения автоматически совместимы:
- Stripe MRR screenshot → `type=dashboard-screenshot, sub_type=single-metric, source=stripe`
- Multi-product breakdown → `type=dashboard-screenshot, sub_type=multi-metric`
- Notification screenshot → `type=dashboard-screenshot, sub_type=notification`

## Связано

- `single-image` v1.0 - новый replacement
- `templates/dashboard-screenshot.md` в single-image - детальный template
- `knowledge/visual-types.md#type-2` в single-image - 5 sub-types
- `knowledge/anti-patterns.md` в single-image - выдуманные numbers как top FAIL
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

