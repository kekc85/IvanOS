---
name: launch-sequence-email-template
version: "1.0"
type: launch-sequence
length_min_words: 500
length_max_words: 1200
description: Часть launch sequence (5-8 letter cash-event campaign). Sequence-aware - каждое письмо знает свою позицию (pre-launch / launch-day / open-cart / close-cart). Reference Jeff Walker PLF + Halbert + Welsh nurture→pitch.
---

# Template: Launch sequence email

> Письмо в составе launch sequence для cash event (<твой ценовой диапазон>). Sequence-aware: тон и структура меняются в зависимости от позиции письма в кампании. **Только в окне продаж** (или подготовка к нему).

## Sequence positions

| Position | Timing | Mode | Length sweet spot |
|---|---|---|---|
| Pre-launch -7d | За неделю до launch | Tease / curiosity | 500-700 слов |
| Pre-launch -3d | За 3 дня до launch | Setup / story | 600-800 слов |
| Pre-launch -1d | За 1 день до launch | Anticipation / save the date | 400-600 слов |
| Launch day Day 0 | Open cart / event start | Big announcement | 800-1200 слов |
| Open cart Day 1-3 | First 3 days | Storytelling proof / value | 700-1000 слов |
| Open cart в день запуска | 24h before close | Last-chance value | 600-900 слов |
| Close cart Day 5 | Last day, 8-12h before close | Urgency-based | 400-700 слов |
| Close cart last call | 1-3h before close | Final reminder | 200-400 слов |

## Body skeleton (общий, адаптируется к position)

| # | Section | Words alloc | Адаптация под position |
|---|---|---|---|
| 1 | Opening hook | 20-40 | Pre-launch: curiosity. Launch day: event marker. Open cart: objection address или proof. Close: urgency (без spam) |
| 2 | Context callback | 80-150 | Callback на previous email в sequence (для коннект) |
| 3 | Main content | 200-500 | Pre-launch: tease. Launch day: full announcement. Open cart: storytelling proof. Close: recap |
| 4 | Value reminder | 80-200 | Pre-launch: hint. Launch day: full stack. Open cart: deep dive 1-2 elements. Close: «remember what you get» |
| 5 | Social proof | 100-200 | Open cart only - testimonials / numbers / case (без выдумывания) |
| 6 | Offer summary | 60-120 | Цена + что внутри + гарантия. Sales-letter elements в концентрированном виде |
| 7 | CTA (primary) | 30-60 | Hard CTA в окне продаж. Soft в pre-launch |
| 8 | Sequence teaser | 30-60 | «Завтра расскажу про X» (pre-launch и open cart) или «это последнее письмо» (close cart) |
| 9 | P.S. | 30-60 | Recap + secondary CTA (часто) |

## Sequence-aware hook frameworks по position

| Position | Hook framework | Пример Subject |
|---|---|---|
| Pre-launch -7d | Curiosity | «На следующей неделе расскажу то о чём молчал 6 месяцев» |
| Pre-launch -3d | Personal confession | «Почему я делаю это сейчас (а не год назад)» |
| Pre-launch -1d | Anticipation | «Завтра в 10:00. Не пропусти» |
| Launch day Day 0 | Direct announcement | «Открыл регистрацию: вайбмаркетинг 2026» |
| Open cart Day 1-3 | Storytelling / proof | «История ученика который сделал $5K за 30 дней» |
| Open cart в день запуска | Last-chance value | «24 часа осталось: что ты пропускаешь» |
| Close cart Day 5 | Urgency (non-spam) | «Сегодня закрываю набор» |
| Close cart last call | Final reminder | «3 часа осталось» (или «Last call» - допустимо в close, не в nurture) |

## CTA rules для launch sequence

- **Pre-launch:** 1 CTA, soft. «Save the date» / «calendar reminder» / «get on the list»
- **Launch day:** 1 CTA, hard. «Go to checkout» / «Join now» link to cart page
- **Open cart:** 1-2 CTA, hard. CTA1 above-fold (после opening hook), CTA2 bottom. Может быть P.S. CTA3
- **Close cart:** 2-3 CTA. CTA1 above-fold, CTA2 bottom, CTA3 в P.S. Все на одну страницу

## Sequence consistency rules (EMAIL-G8)

Каждое письмо в sequence ДОЛЖНО:

- ✓ Callback на pre_email_context (если position > 1)
- ✓ Teaser для post_email_context (если position < total)
- ✓ Один CTA-goal (один link для всей sequence)
- ✓ Voice/archetype consistent (нельзя day 0 как Sage, day 1 как Outlaw - выберите 1-2 архетипа на sequence)
- ✓ Big idea sequence - общая. Каждое письмо = угол big idea, не новая big idea

## Voice rules launch

- **Pronoun:** «ты» (RU) / «you» (EN). Pre-launch чуть более personal, close cart - direct.
- **Formality:** low → mid в close cart (нужна clarity)
- **Tone arc:** pre-launch (curious/teasing) → launch day (excited/clear) → open cart (proof-focused/calm) → close cart (urgent/direct)
- **Archetype:** Magician (pre-launch tease) → Sage (open cart proof) → Outlaw (close cart urgency, but без spam)

## Sales-letter elements могут перекрывать launch (особенно close cart)

Close cart письмо часто = mini sales-letter. См. `templates/sales-letter.md` для proof / objection / guarantee structure.

## Length distribution check

```
Pre-launch / Open cart:
Opening: 3-6%
Context callback: 12-20%
Main content: 30-50%
Value reminder: 10-20%
Social proof: 10-20% (open cart only)
Offer summary: 8-15%
CTA: 5-8%
Sequence teaser: 4-8%
P.S.: 4-8%

Close cart (short):
Opening: 6-10%
Recap: 30-50%
Offer summary: 15-25%
CTA: 10-15%
P.S.: 8-15%
```

## EMAIL-gates специфика для launch sequence

- EMAIL-G1: 3-5 Subject варианта, urgency допустим в close cart (но не spam)
- EMAIL-G2: Preheader synergy
- EMAIL-G3: 1-2 CTA-link (1 для pre-launch / soft; 2 для launch+, hard)
- EMAIL-G4: Mobile preview (close cart особенно - много читают на mobile)
- EMAIL-G6: No-image-dependency (image-blocking common)
- EMAIL-G7: word range по position
- EMAIL-G8 hard required: sequence_position + sequence_context required

## Examples

См. `examples/_TEMPLATE.md` секция «Launch sequence» (после fill после первого запуска).

Reference frameworks: `references/launch-sequence-frameworks.md` (Jeff Walker PLF / Halbert 5-letter / Welsh nurture→pitch).

## Anti-patterns в launch sequence

- НЕ запускать БЕЗ launch-sequence-map в `.business/запуски/<active>/launch-sequence.md` - Mode A FAIL
- НЕ менять big idea / CTA goal от письма к письму - одна sequence = один CTA goal
- НЕ забывать sequence callback в письмах > position 1 (disconnect ломает flow)
- НЕ использовать spam-trigger phrases в Subject даже в close cart («ACT NOW», «100%», «FREE») - deliverability убьётся
- НЕ выдумывать social proof в open cart (см. `[[feedback-first-launch-no-alumni]]` - если запуск первый, выпускников нет → no fake quotes)
- НЕ писать close cart raньше launch day - sequence timing священ