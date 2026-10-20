# Template - Framework Essay

> Конструирует mental model или каркас в голове читателя. Цель - после прочтения у читателя появляется **новый способ думать** о теме (а не новый workflow как в teaching и не новая эмоция как в story).

## Когда применять

- Тема перегружена смыслами / много fragmented advice → нужен каркас
- У автора есть синтез из 3-7 компонентов
- Читатель пройдёт «aha - теперь понятно как думать про это»

## Длина

- Target: 1500-2000 слов
- Floor: 1200
- Ceiling: 2200

## Структура (INSIGHT доминирует)

```
INTRODUCTION (15-18%)  - ~250-350 слов
├─ Hook (re-frame / counter-intuitive)
├─ Problem (почему текущее понимание не работает)
├─ Personal anchor (когда сам перестал понимать)
└─ Promise (вот новый каркас который наводит порядок)

INSIGHT (60-65%)       - ~900-1300 слов [GLAVNAYA chast' framework]
├─ Framework introduction (одна метафора / одно название)
├─ Component breakdown (3-7 компонентов с descriptions)
│   ├─ Component 1: <name> - <description> - <example>
│   ├─ Component 2: <name> - <description> - <example>
│   └─ Component N: <name> - <description> - <example>
├─ How they interact (как компоненты связаны между собой)
├─ Why this framework works (where it comes from / first principles)
└─ When it doesn't apply (boundary conditions)

PROCESS (20-25%)        - ~300-500 слов
├─ Application примеры (2-3 конкретных кейса где применить)
├─ Self-diagnostic вопросы (как читатель применит к своей ситуации)
└─ CTA (subscribe / next в серии / community discussion)
```

## Hook patterns для framework

| Pattern | Пример |
|---|---|
| Re-definition | «X - не <common belief>. X - это <new definition>.» |
| Mental model intro | «Лучший способ думать про <topic> - через <metaphor>.» |
| Counter-intuitive | «Все думают что <topic> - это <X>. На самом деле это <Y>.» |
| Synthesis | «Я долго не мог систематизировать <topic>. Наконец получилось.» |

## Voice quirks (автор-specific)

- В Framework introduction - одна сильная метафора (НЕ длинная серия аналогий)
- Component breakdown - каждый компонент с conkretnym example, не abstract
- При описании компонента - связать с пейном читателя «когда у тебя X, это значит работает компонент Y»
- В «How they interact» - ASCII-схема или 3-5 буллетов
- Не заявлять framework как «universal» - указывать boundary conditions

## INSIGHT - framework-specific pacing

INSIGHT в framework-essay = 60-65% (доминирует) потому что framework - это и есть main_aha + raskrytie.

1. **Framework introduction** - ~100-150 слов. Название + метафора + почему именно так.
2. **Component breakdown** - ~500-700 слов. 3-7 компонентов по 100-150 слов каждый.
3. **How they interact** - ~150-250 слов. Связи / порядок / dependencies. Можно ASCII-схему.
4. **Why this works** - ~100-150 слов. First principles или source.
5. **When it doesn't apply** - ~50-100 слов. Boundary conditions.

## PROCESS - application + self-diagnostic

Format:

```
Где применить:
- <кейс 1: <context>, <как применить компонент X> →  <outcome>>
- <кейс 2: <>>

Самодиагностика:
- <вопрос 1: «есть ли у тебя X? если да - это компонент Y»>
- <вопрос 2>
- <вопрос 3>

<CTA>
```

## Anti-patterns specific to framework

- **Framework без названия** - нечего запомнить, читатель не унесёт
- **>7 компонентов** - невозможно удержать в голове, это уже не framework, а handbook
- **Все компоненты одного уровня** - нужна иерархия или граф
- **Abstract компоненты без examples** - каркас в голове не строится
- **Без boundary conditions** - заявление universal framework вызывает skepticism
- **«Полный гайд»**, «Ultimate framework», «Everything you need» - banned listicle patterns
- **Без ASCII-схемы или 3-5 буллетов взаимодействия** - текстовое описание framework тяжело воспринимается

## Output format markers

```html
<!-- SECTION: INTRODUCTION -->
<!-- HOOK_PATTERN: re-frame | mental-model-intro | synthesis -->
<!-- PROBLEM_SETUP: <one line> -->

<!-- SECTION: INSIGHT -->
<!-- FRAMEWORK_NAME: <> -->
<!-- COMPONENTS_COUNT: <3-7> -->
<!-- HAS_INTERACTION_DIAGRAM: <yes | no> -->
<!-- BOUNDARY_CONDITIONS_STATED: <yes | no> -->

<!-- SECTION: PROCESS -->
<!-- APPLICATION_CASES_COUNT: <2-3> -->
<!-- SELF_DIAGNOSTIC_QUESTIONS_COUNT: <3-5> -->
```

## Reference creators

- **Jack Butcher** - minimal frameworks через Visualize Value
- **Dan Koe** - synthesis frameworks (Eternal Markets / 4 horsemen)
- **Naval Ravikant** - first-principles frameworks в коротких форматах
- **Sahil Bloom** - mental models с iconic naming

## Memory cross-refs

- - framework должен быть изощрённее
- - components должны быть MECE
- - формула / framework, не шаблон
- - метод через логику