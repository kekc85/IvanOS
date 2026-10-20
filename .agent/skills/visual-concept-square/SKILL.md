---
name: "visual-concept-square"
description: "[DEPRECATED 2026-05-28] Замещён скиллом `single-image` v1.0 как type=concept-diagram. Используй `/single-image` с type=concept-diagram (Jack Butcher Visualize Value style diagram + bilingual caption). Этот SKILL.md остался как pointer для backwards-compat и для users, которые вызывают по старому имени."
---

# Visual Concept Square - DEPRECATED → single-image

## Status

**DEPRECATED 2026-05-28.** Замещён `single-image` v1.0 как один из 5 типов (concept-diagram).

## Что делать

### Вариант A: использовать новый skill

```
/single-image про <topic>
--type=concept-diagram
```

Получишь:
- Visual brief (композиция / verbatim text on image / палитра / typography / tool prompt ready-to-execute)
- Bilingual caption (RU + EN, 3 варианта на язык)
- Production notes (Figma steps / Higgsfield prompt)
- 6-Pass review + 3 слоя + no-caption test + anti-stock test

### Вариант B: продолжить как раньше

Старый скилл - простой single-shot generation. Если хочешь minimal output без полного workflow - можешь продолжать использовать. Но рекомендуется переходить.

## Что было в этом skill

Generator visual concept / framework diagrams в Jack Butcher Visualize Value style. Black-on-white minimalist diagrams для X + LinkedIn.

7 типов visual concepts:
1. Framework diagram
2. Spectrum / scale
3. 2x2 matrix
4. Equation / formula
5. Iceberg
6. Funnel
7. Pyramid

Output: image specification + 1-line caption (<50 chars).

## Почему deprecated

`single-image` v1.0:
- Покрывает 5 типов картинок (concept-diagram - один из них)
- Portable by config.md (работает для автора и для учеников курса)
- 3 режима (Plan / Spark / Transcript)
- Bilingual caption (RU + EN всегда)
- Full review pipeline (6-Pass + Maxwell Ross + 3 слоя + no-caption test)
- A/B caption варианты
- Auto track-record для catch_rate metric

Старый скилл - thin slice одного частного случая. Новый - полная архитектура.

## Migration

Если у тебя были saved briefs от старого скилла - они совместимы с новым:
- «Framework diagram» → `type=concept-diagram, geometry=boxes-arrows`
- «Spectrum / scale» → `type=concept-diagram, geometry=spectrum`
- «2x2 matrix» → `type=concept-diagram, geometry=2x2`
- «Equation» → `type=concept-diagram, geometry=equation`
- «Iceberg» → `type=concept-diagram, geometry=iceberg`
- «Funnel» → `type=concept-diagram, geometry=funnel`
- «Pyramid» → `type=concept-diagram, geometry=pyramid`

## Связано

- `single-image` v1.0 - новый replacement
- `templates/concept-diagram.md` в single-image - детальный template
- `knowledge/visual-types.md#type-1` в single-image - 10 geometries explained
- `knowledge/reference-creators.md#concept-diagram` - Jack Butcher как reference
---

## Финальная фаза — Humaniser (mandatory для всех text-skills)

**ОБЯЗАТЕЛЬНО перед output:**

Прочитай `~/.claude/skills/humaniser/prompt.md` и применяй к финальному тексту по 4-этапному алгоритму DETECTOR → REWRITER → CHECKER → OUTPUT.

Humaniser ловит 12 категорий AI-паттернов (Ложная глубина / Фальшивая близость / Пустые связки / Канцелярит / Fake-энергия / Шаблонные призывы / Рубленые фразы / Кинематограф / Структурные клише / Интонационные клише / **Triple-X parallel emphasis** / **Voice-signature theft**).

Если CHECKER возвращает «Найдено клише: 2+» — переделать через REWRITER, не пропускать в output.

**Без этой фазы text-skill выдаёт AI-generic** — empirically validated прецедент post v3.0 2026-05-28 (выдал «Zero ads. Zero funnels. Zero sales calls.» = triple-negation AI tic).
