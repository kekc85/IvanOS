# Template - Teaching Essay

> Обучающий long-form. Раскрывает механизм. Главная цель - читатель уносит конкретную mental model или actionable workflow которые применит на следующей неделе.

## Когда применять

- Тема = «как X работает» / «почему Y делает Z» / «механизм A»
- Аудитория готова потратить 8-15 минут на чтение чтобы получить системное понимание
- Есть proof через personal experience или конкретные кейсы

## Длина

- Target: 1200-1800 слов
- Floor: 1000
- Ceiling: 2000

## Структура (3-section + INSIGHT expanded)

```
INTRODUCTION (15-18%)  - ~200-300 слов
├─ Hook (counter-intuitive / specific outcome / re-frame)
├─ Problem setup (audience pain в 2-3 строки)
├─ Personal anchor (момент когда автор сам столкнулся)
└─ Bridge to insight (1 строка перехода к механизму)

INSIGHT (50-55%)       - ~700-1000 слов [GLAVNAYA chast']
├─ Main "aha" (1 центральный тезис, явно выделен)
├─ Why it works (3 reason'а с first principles)
│   ├─ Reason 1 + 1 proof
│   ├─ Reason 2 + 1 proof
│   └─ Reason 3 + 1 proof
├─ Concrete examples (3-5 с specific numbers)
│   ├─ Example 1: <context + numbers + outcome>
│   ├─ Example 2: <>
│   └─ Example 3: <>
└─ Common misunderstanding (что люди обычно думают неверно)

PROCESS (28-32%)        - ~400-600 слов
├─ Step-by-step application (3-5 шагов, каждый actionable)
│   ├─ Step 1: <how + tool>
│   ├─ Step 2: <how>
│   └─ Step N: <how>
├─ Common pitfalls (2-3 типичные ошибки)
└─ CTA (subscribe / next article / community)
```

## Hook patterns для teaching

| Pattern | Пример |
|---|---|
| Mechanism reveal | «Я думал X работает потому что Y. Оказалось - наоборот.» |
| Counter-intuitive | «Большинство <ниша> советует X. Это ловушка.» |
| Personal aha | «Год назад я понял одну вещь про <topic>. С тех пор всё изменилось.» |
| Outcome + mystery | «Из <metric A> в <metric B> за <time>. Ключ - <тема>.» |

## Voice quirks (автор-specific)

- Personal anchor в первых 2 абзацах обязательно
- «Я разобрался» / «я понял» / «я заметил» - predominant voice
- Конкретные числа в каждом example
- Перед «Why it works» - короткий transition «Вот почему» (НЕ formulaic «А теперь сейчас расскажу»)
- В Process - конкретные tool/platform/file имена

## INSIGHT - детальный pacing

INSIGHT = 50-55% длины потому что в teaching это главная часть. Распределение:

1. **Main "aha"** - ~100-150 слов. Выделить параграфом или жирным.
2. **Why it works** - ~300-400 слов. 3 reason'а по ~100-130 слов каждый.
3. **Concrete examples** - ~300-400 слов. 3 example'а по ~100-130 слов.
4. **Common misunderstanding** - ~100-150 слов. Краткий блок «вот что обычно понимают неправильно».

## Anti-patterns specific to teaching

- **«Сейчас разберу что я называю X»** - formulaic tutorial intro, banned (см. config.lexicon_banned_longform)
- **«Топ-3 ошибки» / «5 шагов чтобы»** - generic listicle frame, banned для teaching essay
- **«В этой статье я разберу»** - formulaic transition, banned
- **Multiple "aha" insights** - split на серию из 2-3 teaching essays вместо одного раздутого
- **Без specific numbers** - каждый example должен иметь конкретное число / имя / дату
- **Process без CTA** - teaching без actionable next step = lost engagement

## Output format markers

В draft помечать секции HTML-комментариями (для `04-review.md`):

```html
<!-- SECTION: INTRODUCTION -->
<!-- HOOK_VARIANT_CHOSEN: <which one> -->
<!-- PERSONAL_ANCHOR_SOURCE: <story bank file or transcript verbatim> -->

<!-- SECTION: INSIGHT -->
<!-- MAIN_AHA: <one sentence> -->
<!-- WHY_REASONS: 3 -->
<!-- EXAMPLES_COUNT: 3 with numbers -->

<!-- SECTION: PROCESS -->
<!-- STEPS_COUNT: <N> -->
<!-- CTA_TYPE: <subscribe | next | community> -->
```

## Reference creators

- **Dan Koe** - 3-section teaching essays (`thedankoe.com/letters/`)
- **Justin Welsh** - 5-step formulae for solopreneur teaching (`justinwelsh.me/articles`)
- **Tim Ferriss** - long-form mechanism essays с personal experiments

## Memory cross-refs
