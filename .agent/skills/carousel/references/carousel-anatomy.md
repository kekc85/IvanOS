# Carousel Anatomy - structure, pacing, hooks

Reference для `workflow/02-structure.md` и `workflow/03-write.md`. Source: bucket-a (EN AI/vibemarketing), bucket-b (EN LinkedIn masters), bucket-e (reel-to-carousel).

Используй этот файл когда нужно:
- Выбрать структуру carousel (3-act vs 5-beat)
- Назначить роль каждому slide
- Выбрать hook formula под family
- Проверить кривую внимания slides (front-load / valley / payoff)

---

## 1. Two structural skeletons

Carousel держится на одной из двух базовых структур. Выбор зависит от family.

### Skeleton A: 3-act Hook → Value → CTA

Применение: framework-breakdown, listicle, panorama.

```
[Slide 1] HOOK          - promise + curiosity gap
[Slide 2-N] VALUE       - доставка обещанного (steps / items / panels)
[Slide N+1] CTA         - single artifact + action
```

Verbatim пример из Justin Welsh "I cracked LinkedIn's code in 8 moves" (3811 likes, 1219 comments, source: bucket-b):
- Slide 1: hook + cover `I cracked LinkedIn's code in 8 moves. 783,895 followers later, here's the playbook`
- Slides 2-9: 8 numbered moves, 30-50 слов на slide
- Slide 10: CTA на newsletter

Verbatim пример из Riley Brown "6 vibe coding tools" (source: bucket-a):
- Slide 1: `Using the 6 best Vibe Coding Tools AT THE SAME TIME. Without writing a single line of code.`
- Slides 2-7: 1 tool на slide (Lovable / Bolt / Replit / Cursor / Windsurf / v0) + UI screenshot каждого
- Slide 8: CTA на Vibecode.dev

### Skeleton B: 5-beat arc Hook → Context → Discovery → Reward → CTA

Применение: story-case, reel-to-carousel.

```
[Slide 1] HOOK          - стоп-скролл, что обещаешь
[Slide 2-3] CONTEXT     - кто я / откуда / что было до
[Slide 4-7] DISCOVERY   - что открыл, как сделал (mass контента)
[Slide 8-10] REWARD     - результат + конкретное число / скриншот proof
[Slide N+1] CTA         - один артефакт
```

Source: bucket-e синтез 11 авторов repurposing video в carousel. Welsh canonical (newsletter → thread → screenshots → LinkedIn carousel) использует этот arc.

Verbatim адаптация для автора (story-case family):
- S1 `Собрал работающий бот за 47 минут. На Lovable + Claude Code.`
- S2 контекст `Раньше тот же бот - 2 недели и 80 000 ₽ подрядчику.`
- S3 контекст `Подрядчик отвалился в среду. Эфир в пятницу. Дедлайн жесткий.`
- S4-S7 discovery (4 шага сборки + screenshot Lovable + Claude prompt)
- S8 reward screenshot Stripe / Skool dashboard
- S9 цифра `47 минут. 0 ₽ на подрядчика. 12 первых платных подписчиков за 48 часов.`
- S10 CTA `В TG полный разбор процесса - закреп в шапке <твой-хэндл>`

---

## 2. Per-slide role taxonomy

Каждому slide назначь одну из 8 ролей. Роль определяет copy length, visual brief, pacing.

| Role | Длина (слов) | Что делает | Visual default |
|---|---|---|---|
| `hook` | 3-12 | Стоп-скролл, promise + curiosity | bold typography ИЛИ hero screenshot + 4-6 слов overlay |
| `context` | 5-25 | Backstory, что было до | photo автора ИЛИ before-state |
| `numbered_step` | 5-25 | Шаг N из методологии | UI screenshot этого шага |
| `item` | 5-25 | Один пункт listicle (1 tool / 1 prompt) | product name + UI screenshot |
| `reveal` | 5-25 | Result / outcome раскрытие | dashboard screenshot raw |
| `synthesis` | 5-25 | Итог, что унесёшь, lesson | typography + 1 цифра |
| `proof` | 3-15 | Чистая цифра / screenshot без annotation | full-bleed screenshot |
| `cta` | 5-15 | Один artifact + action | button-style design |

Роль `proof` опциональна, но желательна минимум 1 раз в carousel (см. real_elements floor в `visual-brief-real-first.md`).

---

## 3. Pacing patterns (3 mechanics)

Между slides должна быть тяга. Три проверенные техники.

### 3.1 Open loop

Slide N задаёт вопрос или открывает loop, slide N+1 закрывает.

Welsh signature pattern: `Relatable Enemy → Hero → Teaser`. Verbatim пример (bucket-b):
- S1 `The 9-to-5 job is getting pummeled.`
- S2 `The great resignation is growing faster than ever.`
- S3 `And I love it. Why?`
- S4 [answer reveals]

### 3.2 Cliffhanger

Slide N ends на половине мысли, slide N+1 завершает.

Verbatim adapted (Acosta-style):
- S5 `Я думал секрет в количестве постов. Но потом увидел метрики.`
- S6 [screenshot analytics + insight]

### 3.3 Curiosity gap

Slide 1 обещает конкретное число (8 / 27 / 35), audience считает до конца.

Verbatim примеры:
- Welsh `I cracked LinkedIn's code in 8 moves` - audience считает 1-8
- Alić `27 Proven LinkedIn Writing Tips by Jasmin Alic` - 27 точно отдан
- Дамир Халилов `35 МОИХ АВТОРСКИХ УСИЛИТЕЛЕЙ` (RU corpus, bucket-c) - 35 на счётчике

Правило: если обещал N - отдай ровно N. Округление вверх или вниз = брак доверия.

---

## 4. Кривая внимания slides - где front-loadить, где payoff

Из bucket-e (Instagram / LinkedIn carousel data 2026):

```
Slide 1-3   ↑↑↑ peak attention - front-load value, max hook punch
Slide 4-7   ↓↓  valley - mass контента, depth, разворот темы
Slide 8-10  ↑↑  payoff rise - saves/shares restoring, "reference material"
Slide 11-12 →   tail - CTA + bonus insight
```

Что это значит для написания:

- **Slides 1-3:** самые сильные insights / самые яркие screenshots / самое крупное обещание. Не оставлять на потом.
- **Slides 4-7:** depth content. Здесь можно дать подробности, прочерки, nuance. Audience уже коммитнулась.
- **Slides 8-10:** второй пик - сюда reveal / cardio-screenshot / payoff. Save-rate здесь самый высокий (саккадирующий читатель видит финал и сохраняет).
- **Slide CTA:** не последний единственный шанс. Soft CTA можно дублировать на slide 5-6 как in-content фраза («сохрани этот пост чтобы вернуться»).

---

## 5. Hook slide formulas top-10 (verbatim из bucket-a + bucket-b)

Используй как пресет для генерации hook slide. Каждая formula - проверенный pattern с указанным автором.

### F1. Number + outcome + timeframe (Welsh, Sabrina, Riley, Greg, Pieter)

Базовый pattern 60% всех топ-carousels. Шаблон:
```
[N] [tools/prompts/principles/moves] that [outcome] [in timeframe]
```
Verbatim:
- `I cracked LinkedIn's code in 8 moves. 783,895 followers later` (Welsh)
- `Using the 6 best Vibe Coding Tools AT THE SAME TIME. Without writing a single line of code.` (Riley)
- `New ChatGPT prompts this week` + 9 prompts (Sabrina)

### F2. Relatable Enemy → Hero → Teaser (Welsh signature)

3 строки на 1 slide или 3 первых slide подряд.
```
[X] is getting pummeled.
[Y] is growing faster than ever.
And I love it. Why?
```

### F3. SLAY framework hook (Lara Acosta)

S = Story, L = Lesson, A = Actionable, Y = You. Hook = Story compressed в 1 предложение ≤10 слов.
```
[2 года назад / в марте / в среду] я [conflict-state]. Сегодня [transformation-state].
```

### F4. Own-name authority hook (Jasmin Alić)

Автор кладёт своё имя прямо в hook. Работает на тех, у кого имя = brand asset.
```
[N] Proven [topic] Tips by [Your Name]
```
Verbatim: `27 Proven LinkedIn Writing Tips by Jasmin Alic`. Адаптация: `12 микро-SaaS за выходные. автор`.

### F5. ALL CAPS bold claim (Chase Dimond - context-dependent)

Контр-intuitive: ALL CAPS работает в email marketing вертикали где Dimond его установил. Тестируй осторожно.
```
HOW TO [outcome] WITH [tool/method]
```
Для русского - не использовать в авторском голосе. CAPS длиннее 3 слов = AI-default flag (см. bucket-c banned).

### F6. Bold contrarian statement (Allie K. Miller)

```
[Accepted belief] doesn't mean [feared consequence].
```
Verbatim: `Using AI in your job doesn't mean expertise is dead.`

### F7. Empathy-problem opener (Ryan Musselman)

```
[Painful state - 1 line]? [N] ways to change this forever:
```
Verbatim: `Sad your post didn't do well? 2 ways to change this forever:`

### F8. Quantified loss (template из bucket-b)

```
[N]% of [persona] are losing [outcome] for one reason
```
Использовать осторожно для автора - правило «не использовать негативные статистики в публичном offer» (memory). Только если статистика об индустрии, не о клиентах.

### F9. Age contrast (Sahil Bloom)

```
Harsh Truths I Know At [current age] I Wish I Knew At [past age]
```
Адаптация: `Что я узнал в 35, запуская курсы, чего не знал в 25`.

### F10. RU verified hooks (bucket-c, RU corpus)

Шесть HIGH-confidence formulas:
1. `[X] больше не нужен` (Палий / Ширяев) - с обязательным live-product proof
2. `За [N] минут - [Y]` (Арина / Афонина) - `Собрал работающий бот за 47 минут`
3. `[Профессия], пришло наше время` (Замесин) - `Эксперты, пора`
4. `Дай мне [N] недель и я [Y]` (Петкова) - квалификатор
5. `Кому НЕ нужен [X]` (Петкова) - анти-кейс
6. `Самый быстрый [X] в моей жизни - [N]` (Афонина) - `Самый быстрый билд - 47 минут`

---

## 6. Real elements floor (≥40% slides)

Правило source: bucket-a top 3 cross-author pattern.

**Минимум 40% slides в carousel должны содержать минимум один real element** из категорий:

- UI screenshot реального tool (Claude Code / Cursor / Lovable / n8n / Stripe / Skool / Kit / Beehiiv)
- Реальное product name verbatim (`@cursor_ai`, `@lovable`, `Claude Code`)
- Реальная цифра (`<твоя выручка>`, `47 минут`, `<число учеников>`, `9.6/10 NPS`)
- Реальный dashboard (Stripe MRR, Skool MRR, TG analytics)
- Реальная фотография автора (face shot, не AI-avatar)
- Реальный DM/screenshot переписки ученика

Если carousel из 10 slides - минимум 4 slides с real elements.

Per-family floor (см. `visual-brief-real-first.md` для details):
- framework: 40%
- listicle: 60% (каждый item = tool с UI screenshot)
- story-case: 50%
- panorama: 40%
- reel-to-carousel: 50%

**Detection в review:** считай slides где `visual_brief.real_elements` содержит ≥1 verbatim название tool / цифру / screenshot reference. Если ниже floor - CR-G4 FAIL.

---

## 7. Slide count per family

Из bucket synthesis (verified):

| Family | Optimal | Range | Источник |
|---|---|---|---|
| framework-breakdown | 9-10 | 8-12 | Welsh canonical, bucket-b |
| listicle | 8-10 | 7-10 | Riley / Sabrina, bucket-a |
| story-case | 10-11 | 9-12 | Acosta SLAY + Pieter, bucket-b |
| panorama | 5 | 3-8 | Subway / Casper / Heather, bucket-d |
| reel-to-carousel | 9 (median) | 6-12 | bucket-e: 15сек→6-8, 30сек→8-10, 60сек→10-12 |

Внимание резко падает после slide 10 на IG. LinkedIn выдерживает до 12-15. Cap 12 для cross-distribution.

---

## 8. CTA slide - 5 канонических patterns

CTA должна быть **artifact + action**, не «follow me».

| # | Pattern | Verbatim | Source |
|---|---|---|---|
| 1 | Comment-trigger DM | `Комментарий "разбор" - пришлю в DM ссылку на полный разбор` | Sabrina, bucket-a |
| 2 | Link in bio + artifact | `Полная методология - закреп в шапке <твой-хэндл>` | Riley / Heather, bucket-a |
| 3 | Save this carousel | `Сохрани - вернёшься когда будешь собирать первый` | Jasmin / Justin, bucket-b |
| 4 | Newsletter subscribe | `Каждую субботу новый билд - подписка в bio` | Heather / Matt, bucket-a |
| 5 | Follow experiment | `На следующей неделе тестирую X - подписка чтобы не пропустить` | Allie, bucket-a |

RU corpus (bucket-c verified): canonical CTA - «закреп в шапке профиля» / «полная серия в TG @handle» / «бесплатный МК в bio».

Запрещены:
- `Follow me` без причины
- `Like if you agree`
- `Tag a friend who needs this` (generic 2018-era)
- Multiple CTAs на одном slide (выбирай одну)

---

## 9. Soft vs Hard CTA distribution

Из bucket-e: carousels с CTA на нескольких slides делают +20-30% ER vs single-CTA в конце.

- **Soft CTA** в середине (slide 5-6): встроенная фраза внутри content. Пример: `Сохрани этот slide - формула пригодится` внутри value slide.
- **Hard CTA** на последнем slide (slide N): button-style design + artifact + reason.

Hard CTA action-specific под family:
- framework / methodology → SAVE
- контроверсия / opinion → COMMENT
- diagnostic / problem → CLICK / DM
- launch / sale → CLICK + deadline

---

## 10. Disambiguator - какую structure выбрать

Если family не задан явно, используй decision tree:

```
Есть числовая методология с шагами? → framework-breakdown (3-act)
Есть N items одного типа (tools / prompts / правила)? → listicle (3-act)
Есть personal experience + результат? → story-case (5-beat)
Есть wide visual который continuous? → panorama (3-act + panorama mechanics)
Есть card.md от ingest-reel? → reel-to-carousel (5-beat)
```

Если в одном замысле есть несколько - выбирай family по primary intent. Cross-family мутации блокируются в `02-structure.md`.