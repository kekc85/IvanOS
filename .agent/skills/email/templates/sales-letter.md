---
name: sales-letter-template
version: "1.0"
type: sales-letter
length_min_words: 800
length_max_words: 1500
description: Окно продаж sales-letter. Halbert / Welsh fusion. Problem → Story → Solution → Value stack → Proof → Offer → Guarantee → CTA. Только в окне продаж (open cart day, last call).
---

# Template: Sales letter

> Продающее письмо в окне продаж. Полная классическая структура Halbert / Welsh. 800-1500 слов. CTA повторяется 2-3 раз (above-fold или после value stack + bottom + P.S.). Все CTA-link на одну checkout page.

## Body skeleton (Halbert / Welsh fusion)

| # | Section | Words alloc | Описание |
|---|---|---|---|
| 1 | Opening hook | 20-50 | Above-fold attention grabber. Stop scroll. Может быть question / confession / contrarian statement |
| 2 | Problem amplification | 150-250 | Pain в ICP. «Ты заметил что Y? Это потому что Z». Specific, не generic |
| 3 | Story / personal context | 200-400 | Личная история автора. Как он dealt с этой problem. «Я тоже был в этом 2 года назад. Вот что я сделал» |
| 4 | Solution introduction | 150-250 | Big idea / method. «Вайбмаркетинг - это X. Это категория-метод который Y». Introduce product name. |
| 5 | Value stack | 100-200 | Что внутри offer. Bullet list (1-2 списка max). «Ты получишь: 1) X 2) Y 3) Z». Каждый - конкретный outcome |
| 6 | Proof / social proof | 100-200 | Testimonials / case studies / numbers. Без выдумывания. Если первый запуск - proof = личный track record |
| 7 | Offer terms + guarantee | 100-150 | Цена + что внутри + bonuses + гарантия 14 дней (legally compliant). Welsh: «$X одноразовый платёж. Плюс bonuses Y. Гарантия 14 дней - если не работает, return» |
| 8 | CTA #1 (above-fold или after value stack) | 30-60 | Hard CTA. «Перейти к оформлению» link |
| 9 | Objection handling | 100-200 | Распространённые возражения. «Если ты думаешь "я не маркетолог" - это и есть причина почему тебе это нужно» |
| 10 | CTA #2 (bottom) | 30-60 | Повтор link, другой anchor text. «Готов начать? Жми сюда» |
| 11 | P.S. | 40-80 | Recap offer + CTA #3 (P.S. читается часто). «P.S.: Гарантия возврата 14 дней. Если не сработает - return. Жми сюда» |

**Итого:** 1020-1850 слов. Sweet spot 800-1500.

## CTA placement strategy

**Above-fold position (Halbert):**

Опционально - CTA #1 может быть above-fold (после opening hook, до problem amplification). Это работает для **тёплой базы**, которая уже знает offer (open cart в день запуска-5, close cart). Для холодной - НЕ above-fold (нужно сначала setup pain).

**After value stack (Welsh):**

CTA #1 default position = после value stack (section 5). К этому моменту читатель уже emotionally invested и ему нужна kicker «вот ссылка».

**Bottom:**

CTA #2 - после objection handling. К этому моменту все возражения сняты.

**P.S.:**

CTA #3 в P.S. - часто читается даже если основной body skip. Recap + link.

**Все CTA → одна страница.** Не разные URL'ы. Не разные UTM. Не разные goals.

## Hook framework recommendations

| Framework | Когда использовать |
|---|---|
| Personal confession | Open cart Day 1-2. «Я долго не делал этого. Вот почему сейчас» |
| Contrarian | Open cart в день запуска-3. «Все говорят X. Я считаю Y» |
| Numbered (results-first) | Open cart Day 3-4. «3 факта почему это работает» |
| Direct benefit | Open cart в день запуска-5, close cart. «Полный playbook за $X. Last call» |
| Urgency | Close cart only. «Last call: 3 часа до закрытия» (один из немногих случаев когда «last call» допустим в Subject) |

## Voice rules sales-letter

- **Pronoun:** «ты» (RU) / «you» (EN), 1:1 conversational
- **Formality:** low в opening / story; mid в offer / guarantee; low снова в CTA
- **1/3/1 rhythm + bullet1 рулят:** короткие - средние - короткие; одна (макс две) bullet list в value stack
- **Archetype:** Magician (transformation promise) + Sage (proof / authority). Outlaw в close cart (urgency без spam)
- **No selling language cliché:** «уникальное предложение», «не пропусти», «прорыв», «эксклюзивно» - все banned
- **Direct sales language OK:** «Я хочу чтобы ты записался», «Жми сюда», «Это работает», «Get the playbook» - direct, не slimy
- **Guarantee mandatory:** «Гарантия возврата 14 дней» (per memory `[[feedback-no-refunds]]`). Юридический термин - НЕ спам.

## Mobile preview rules для sales-letter

- Subject ≤40 chars truncation safe
- Preheader дополняет (price hint или guarantee hint - drives clicks)
- First 200 chars body = mini-pitch. CTA #1 above-fold optional but desirable

## EMAIL-gates специфика для sales-letter

- EMAIL-G1: 3-5 Subject варианта. Hook frameworks допустимы все включая urgency для close cart
- EMAIL-G2: Preheader synergy 0.3-0.7. Preheader часто включает hint про price/guarantee
- EMAIL-G3: 2-3 CTA-link (above-fold OR after-value-stack + bottom + p.s.). Все на одну страницу
- EMAIL-G4: Mobile preview obligatory
- EMAIL-G5: Spam-trigger ОСТОРОЖНО. «Гарантия возврата 14 дней» = legal term, OK. «100% гарантия» = spam.
- EMAIL-G6: No-image-dependency
- EMAIL-G7: 800-1500 words
- (EMAIL-G8 не применяется если single sales-letter, применяется если часть launch sequence)

## Sequence-aware variant

Если sales-letter входит в launch sequence (close cart Day 5 / last call) - также применяются EMAIL-G8 (sequence consistency). См. `templates/launch-sequence-email.md`.

## Length distribution check

```
Opening hook: 2-4%
Problem amplification: 12-18%
Story / personal: 18-28%
Solution intro: 12-18%
Value stack: 8-14%
Proof: 8-14%
Offer terms / guarantee: 8-12%
CTA #1: 3-5%
Objection handling: 8-14%
CTA #2: 3-5%
P.S.: 4-6%
```

## Examples

См. `examples/_TEMPLATE.md` секция «Sales letter» (fill после первого cash event).

Reference frameworks:
- `references/launch-sequence-frameworks.md` - Halbert Boron Letters / Welsh nurture-to-pitch
- `references/cta-patterns.md` - above-fold + bottom + p.s. CTA strategy

## Anti-patterns в sales-letter

- НЕ продавать без guarantee (юр. требование + trust)
- НЕ выдумывать social proof (если первый запуск - proof = личный track record, не invented testimonials)
- НЕ multi-product offer в одном sales-letter (один offer = одна letter, отдельная letter для другого product)
- НЕ агрессивный urgency без real timing («last chance forever» когда продукт будет ещё раз - fail)
- НЕ выдумывать negative statistics («только 5% доходят») - `[[feedback-no-negative-stats-in-public-offer]]`
- НЕ скрывать price («цена в личке») запрет
- НЕ ссылаться на конкурентов по имени («лучше чем у X»)
- НЕ техжаргон в публичной части
- НЕ забыть P.S. - самая читаемая часть после Subject
