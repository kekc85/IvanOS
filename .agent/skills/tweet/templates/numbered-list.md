# Template: Numbered list mini-thread

**Reference cluster:** Idea-drop (Isenberg / Bloom / Cole / Welsh).
**Char zone:** Hook = B (200-280). Beats = N/A (each item own length).
**Format:** Mini-thread 5-15 tweets.

## Условие вызова (HARD, канон формы v2 §8.2 и §9)

Шаблон **условный**, не самостоятельный тип на выбор по умолчанию:

- **Вызывать** при `form_goal = forwards` (F) - нумерация как алгоритм из 3-5 шагов, единственное место, где она желательна (SOFT, канон §9 F-8, §3.2)
- **Вызывать** при `form_goal = reactions` (R), класс **разбор** - нумерация разрешена (25% верха против 17% низа, знак обратный, гейт снят, канон §3.1/§9 R-9)
- **НЕ вызывать** при `form_goal = sales` (S) - нумерация запрещена **HARD** (88% верха её не используют, канон §9 S-13)
- **НЕ вызывать** при `form_goal = reactions` (R), класс **нарратив** - нумерация даёт WARN (канон §3.1/§9 R-9), шаблон не предлагать как самостоятельный тип
- `form_goal` пуст → до выбора шаблона доходить не должно: это `form_mode: FAIL` (Гейт 0 канона §9), вернуться в `01-router.md` Step 5.5 FORM-GOAL ROUTER за целью, а не подключать шаблон по старому дефолту

Внутри разрешённых веток (F и R-разбор) остаётся дополнительное условие из §8.2: цифра N должна работать обещанием хука («N вещей которые...») - это не заменяет проверку цели, а действует поверх неё

## Skeleton

```
1/ [Hook - "N things that [outcome]" - Zone B 200-280 chars]
2/ [Item 1: name + verbatim 1-line example]
3/ [Item 2: name + example]
...
N+1/ [Closer: "bookmark this" / newsletter CTA / open question]
```

## Hook patterns applicable

4. Numbered promise (Welsh / Cole / Bloom)
15. "$X/mo idea for you" (Isenberg signature)

## Voice rules

- Concrete N (3 / 5 / 7 / 10 - odd numbers slightly better viral)
- Each item = name + 1-line verbatim example (NOT abstract)
- 1 sentence per beat (Cole rule)
- No "1." numbering в final tweet (distorts promise)
- Closer = bookmark directive OR newsletter CTA

## Verbatim Cole/Welsh examples

- **Welsh:** "5 X tweets you should write every week."
- **Cole:** "Here are 5 ways to write tweets that build your audience..."
- **Bloom:** "10 mental models that will save you years of bad decisions."

## автор RU adaptation examples

- "5 ошибок которые я сделал в первом запуске на ₽2М."
- "7 промптов которые экономят мне 4 часа в день."
- "3 шага от первого продукта до ₽50К/мес через вайбмаркетинг."

## Item format rule (HARD)

Каждый item:
```
N/ <Name of item>

<1-line verbatim example or concrete>
```

NOT:
```
N/ 1. Try harder.   ❌ (too abstract)
```

YES:
```
N/ Stop "trying harder" - start "iterating faster".

Welsh shipped 5 newsletters in week 1. Iteration > optimization.   ✓
```

## Anti-patterns

- Abstract items без concrete examples
- Inconsistent item format
- "1." numbering в final beat
- >15 items (audience drops off)
- <5 items (looks under-cooked)
- Hashtags