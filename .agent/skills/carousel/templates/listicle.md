# Template: Listicle

**Когда применять:** N инструментов / N способов / N ошибок / tool roundup.
**Reference creator:** Riley Brown («6 vibe coding tools used simultaneously»), Greg Isenberg.
**Slide count:** 8-10.

---

## Условие вызова (HARD, канон формы v2 §8.2 и §9)

Шаблон **условный**, не самостоятельный тип на выбор по умолчанию (согласовано с `carousel/workflow/04-review.md` блок «нумерация в тексте», строки 51-61):

- **Вызывать** при `form_goal = forwards` (F) - нумерация/опись как алгоритм или маршрут из шагов, желательна в этом профиле (SOFT, канон §9 F-8, §3.2)
- **Вызывать** при `form_goal = reactions` (R), класс **разбор** - нумерация разрешена (25% верха против 17% низа, знак обратный, гейт снят, канон §3.1/§9 R-9)
- **НЕ вызывать** при `form_goal = sales` (S) - нумерация запрещена **HARD** (88% верха её не используют, канон §9 S-13)
- **НЕ вызывать** при `form_goal = reactions` (R), класс **нарратив** - нумерация даёт WARN (канон §3.1/§9 R-9), листикл не предлагать как самостоятельный тип
- `form_goal` пуст → до выбора шаблона доходить не должно: это `form_mode: FAIL` (Гейт 0 канона §9), вернуться в `01-router.md` Шаг 4.5 FORM-GOAL ROUTER за целью, а не подключать шаблон по старому дефолту

Внутри разрешённых веток (F и R-разбор) действует дополнительное условие из §8.2: цифра N должна работать обещанием хука слайда 1 («N инструментов / N способов») - не заменяет проверку цели, а действует поверх неё

---

## Structure

```
[Slide 1 - Hook]
"<N> <items> + <1 outcome>. <Stack/condition>:"
Example: "6 инструментов. 1 воронка. Без кода:"

[Slides 2 to N-1 - Items (odd/even alternation)]
ODD slide (text-heavy): name + 1-line description
EVEN slide (screenshot-heavy): UI screenshot этого item + minimal annotation

[Slide N - CTA]
"Save для stack. Comment '<keyword>' → DM полный список"
```

## Hook formulas (3 варианта для A/B)

1. **Stack equation:** «Cursor + Lovable + Stripe = $X/мес. Stack:»
2. **Tool count + outcome:** «5 инструментов которыми я заменил $50K маркетингового консультанта:»
3. **Saves promise:** «6 инструментов которые экономят 15h/неделю. Bookmark:»

## Real elements requirements

КРИТИЧНО для listicle - ≥60% slides должны содержать:
- Real product UI screenshots (КАЖДЫЙ item slide - screenshot реального инструмента)
- Tool names by exact brand (`@cursor_ai` / Claude Code / Lovable / n8n / Stripe / Kit / Skool)
- Real outcomes per tool (time saved / $ generated / users acquired)
- НЕ generic icons вместо product logos

## Pacing

- Slide 1: hook + N tease (matryoshka opening)
- Slides 2-3: первые 2 items быстро (build trust)
- Slides 4-N-1: middle items с varying density
- Slide N: hard CTA

**Odd/Even alternation (Riley Brown trick):**
- ODD: name + short description text-heavy
- EVEN: UI screenshot этого инструмента (proof)

Это удваивает density per item - text + visual за два slides вместо одного перенасыщенного.

## Visual style

- **Typography:** medium-weight, ≤20 words per slide
- **Item numbering:** "1/6 - Cursor" или просто item name + counter (2/6)
- **Screenshot crop:** key UI region only, не весь interface
- **Annotations:** стрелка / circle на крупный element с overlay text
- **No-go:** generic icon вместо real logo / AI-illustrated tool comparison

## Reference examples

- Riley Brown «6 vibe coding tools simultaneously» (Bucket A)
- Greg Isenberg AI tool roundups
- Sabrina Ramonov «N AI tools for X»

## Что переносимо для автора

- Format «N tools / 1 outcome» - для русского рынка («6 инструментов которыми я строю воронку без кода»)
- Odd/even alternation - удваивает value density
- Tool roundup per Jobs-to-be-Done (не generic list)