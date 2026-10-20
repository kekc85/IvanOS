# 02-structure.md - Type detection + skeleton + hook draft

Принимает `brief_final` от 01-finalize. Строит skeleton + hook draft.

## Step 1 - Load template

Load `templates/<type-slug>.md` соответствующий `brief_final.type`:

| Type | Template |
|---|---|
| single punchline | `templates/single-punchline.md` |
| PAIPS story | `templates/paips-story.md` |
| spiky one-liner | `templates/spiky-oneliner.md` |
| numbered list mini-thread | `templates/numbered-list.md` |
| story / news mega-thread | `templates/mega-thread.md` |
| contrarian take | `templates/contrarian.md` |
| how-i-did demo | `templates/how-i-did.md` |

## Step 2 - Draft hook (Hook Char Zone Gate, канон формы v2)

Generate hook based on `brief_final.hook_pattern` + `brief_final.char_zone_target`.

**Профильный состав хука (HARD-часть, канон §3 и §4.1) - применяется, когда `brief.form_goal` установлен (синхронизировано с `04-review.md` G7, `tweet/SKILL.md:117-124`):**

- `form_goal = forwards` (F): цифра или валюта в хуке **обязательна** (63% верха против 20% низа), хук **не короче 50 знаков**, цель 64 знака (канон §3.2)
- `form_goal = reactions` (R): в первой строке **нет** числа ≥1000 и нет круглой метрики канала (подписчики / просмотры / выручка), `+` первым знаком → FAIL - чистое поле держат 93% верха (канон §9 R-6). Хук - сцена или парадокс, ориентир 60 знаков (WARN, канон §3.1/§9 R-5)
- `form_goal = sales` (S): в самом хуке **нет** связки «ты/твой/вы + сумма дохода или число подписчиков» - **HARD** (0/34 верха против 3/34 низа, канон §9 S-3), цель 36 знаков, ориентир 50 - WARN (держат 62% верха, канон §3.3)
- `form_goal = gate` (A): недоступен на X / Threads - `01-router.md` 5.5.5 этот скилл `form_goal = gate` не выставляет никогда (реакция-гейт §7 - TG-механика), ветка помечена `N/A` и не проверяется

**Zone A/B (дефолт уровня 7 иерархии, канон §8.2).** Zone A (40-100 chars) - short punch, aphorism, spiky. Zone B (200-280 chars) - compressed narrative. При объявленной цели это справочный ориентир, а не условие PASS - решает профильный состав выше

**Dead zone 100-200 chars → WARNING плюс одна строка обоснования** (было HARD reject - понижено каноном формы v2 §8.2: зоны заимствованы из чужого исследования Welsh/Bloom/Cole и с нашими данными не сверены, у нас измерена не длина хука, а его состав)

**`brief.form_goal` пуст - НЕ рабочее состояние.** Это HARD FAIL Гейта 0 (канон §9), а не повод строить хук по старым зонам: `01-finalize.md` обязан был остановить пайплайн до этого шага. Если он всё же не остановлен - это разрыв проводки, чинить в `01-router.md` Step 5.5 FORM-GOAL ROUTER, а не продолжать генерацию хука по Zone A/B

Generate 3 hook variants → pick best by:
- Specificity (concrete number / identity)
- Voice match (config.voice.primary_register)
- Counter-intuitive factor
- При объявленной цели - соответствие профильному составу хука выше (приоритетнее трёх пунктов above, канон уровень 5 > дефолт уровня 7)

## Step 3 - Build skeleton

### For single types (single-punchline / spiky-oneliner / contrarian-single)

```
[Hook line - Zone A or B]
```

### For PAIPS story (mini-thread 5-8 OR X long 150-300 слов)

```
1/ [Pain hook]
2/ [Agitate - consequences]
3/ [Intrigue - counter-intuitive turn]
4/ [Positive - solution / insight]
5/ [Soft CTA] (optional)
```

### For numbered list mini-thread (5-15 tweets)

```
1/ [Hook: "N things that [outcome]" - Zone B 200-280]
2/ [Item 1: concrete + verbatim example]
3/ [Item 2: ...]
...
N+1/ [Closer: bookmark this / newsletter CTA / open question]
```

### For story / news mega-thread (18-34 tweets)

Cole's 7-template choice или Bloom Named-Principle:

**Bloom Named-Principle Visual Thread:**
```
1/ [Hook: "Everyone needs to read this. The [Name] Principle. (a visual thread)"]
2/ [Setup of named principle]
3-15/ [Beats with concrete examples + verbatim]
16-30/ [Variations / counter-examples]
31-34/ [Synthesis + newsletter CTA + bookmark directive]
```

**Cole Framework Thread:**
```
1/ [Hook]
2/ [Framework name + 1-line definition]
3-N/ [Each step: name + verbatim example]
N+1/ [Closer: CTA]
```

### For how-i-did demo (8-12 tweets)

```
1/ [Hook: outcome reveal - "$X in N days. Workflow:"]
2/ [Setup: starting point]
3-7/ [Steps with concrete numbers / time]
8/ [Result + lesson]
9-12/ [Newsletter CTA / community link]
```

## Step 4 - Thread Length Gate (HARD)

If recommended format = mini-thread:
- **8-15 tweets compact OK**
- **3-7 tweets awkward middle → fail**, regenerate as either single or 8-15

If recommended format = mega-thread:
- **18-34 tweets mega OK**
- **16-17 tweets awkward → fail**, expand to 18+

## Step 5 - Output skeleton

```yaml
skeleton:
  hook_draft: <verbatim, Zone A or B>
  hook_pattern: <1 of 15>
  beats: [<draft tweet 1>, <draft tweet 2>, ...]
  closer: <draft>
  char_count_per_tweet: [<N1>, <N2>, ...]
  thread_total_count: <N>
  form_goal: <reactions|forwards|sales|gate|null>   # эхо brief.form_goal, единый словарь (слово, не буква); null = HARD FAIL выше, сюда пайплайн доходить не должен
  form_goal_letter: <R|F|S|A|null>   # только печать улики человеку, ни в одном сравнении не участвует
  gates_passed:
    hook_char_zone: PASS | WARN <обоснование>   # WARN на dead zone 100-200 при любой цели (канон v2 §8.2); PASS|FAIL на профильные HARD-пункты (F цифра+50 знаков / R запрет крупного числа / S запрет «ты+сумма»); form_goal пуст → form_mode: FAIL в 04-review.md, сюда доходить не должно
    thread_length: PASS | N/A
```

→ Hand off to `03-write.md`.

## Anti-patterns

- НЕ skip Hook Char Zone Gate: при объявленной `brief.form_goal` dead zone 100-200 - WARNING + строка обоснования, а не FAIL (канон формы v2 §8.2, синхронизировано с `04-review.md` G7); профильные HARD-пункты (F цифра/длина, R запрет крупного числа, S запрет «ты+сумма») остаются блокирующими. `brief.form_goal` пуст → до этого шага доходить не должно: `form_mode` в `04-review.md` даёт HARD FAIL раньше, вернуться в `01-router.md` Step 5.5
- НЕ skip Thread Length Gate (3-7 awkward = FAIL)
- НЕ skeleton без template load - каждый тип имеет fixed skeleton
- НЕ generate 1 hook variant - minimum 3 для choice
- НЕ pick hook без specificity check