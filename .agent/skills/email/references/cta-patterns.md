---
name: cta-patterns
version: 1.0
description: CTA patterns для email-машины. Типы CTA, placement по типам писем, single-goal rule, actionable RU + EN формулировки. Подгружается workflow/02-structure.md и workflow/03-write.md.
---

# CTA patterns для email-машины автора

CTA это кульминация письма. Всё что было до (hook, story, value, pain) ведёт к одному моменту: читатель должен кликнуть. Если CTA размытый, multi-goal или generic, письмо провалилось вне зависимости от того насколько хорошо написано body.

Главное правило: одна цель = одно письмо. Multi-CTA на разные goals = split на серию из 2-3 писем. Можно повторять link 2-3 раза с разными anchor texts, но destination ОДИН.

## CTA types

### Hard CTA

Прямой вызов к финальному действию: checkout / signup / booking / purchase.

- RU: "Перейти к оформлению", "Забронировать место", "Записаться в клуб", "Купить курс"
- EN: "Go to checkout", "Reserve your spot", "Join the club", "Buy the course"

Когда использовать: launch day, sales letter, close cart, тёплая база которая уже знает offer.

### Soft CTA

Приглашение / reply / read more. Низкий commitment.

- RU: "Ответь на это письмо если интересно", "Если хочешь посмотри подробности", "Прочитай дальше", "Расскажи как у тебя"
- EN: "Reply if interested", "Take a look if you are curious", "Read more", "Tell me how it is going"

Когда использовать: nurture, pre-launch warmup, re-engagement, cold аудитория, survey emails.

### Micro CTA

Очень малое действие: forward, reply with question, hit emoji.

- RU: "Перешли это другу которому пригодится", "Ответь одним словом: согласен или нет", "Расскажи в ответе"
- EN: "Forward this to a friend who needs it", "Hit reply with one word: yes or no", "Share your take in a reply"

Когда использовать: building engagement, deliverability boost (reply сигнализирует inbox-у что email важен), survey, community feels.

## CTA placement by template

### Nurture (educational / story)

1 CTA в section 5 (после main content / value).
P.S. CTA опциональный, может вести на тот же link с другим anchor.

Pattern:
- Body delivers value (3-4 секции)
- Section 5: bridge → CTA (Soft предпочтительно для nurture)
- P.S.: optional reminder CTA на тот же link

Запрещено: 2+ CTA above-fold в nurture (звучит как продающее письмо, breaks trust).

### Launch sequence

Зависит от позиции письма в sequence:

**Pre-launch (письма 1-3, ещё нет offer).** Soft CTA. 1 в письме.
- "Ответь на это письмо одним словом если хочешь узнать первым"

**Launch day (письмо 4, offer открыт).** Hard CTA. 1-2 в письме (выше fold + bottom).
- Above-fold: hook + first CTA ("Записаться")
- After value stack: повтор того же CTA
- P.S.: optional reminder

**Mid-launch (письма 5-7).** Hard CTA 2 раза (after pain agitation + after value).

**Close cart (письмо 8-9).** Hard CTA 2-3 раза + urgency framing. Above-fold обязательно.

### Sales letter

2-3 CTA в одном письме (above-fold или после value stack + bottom + P.S.). ВСЕ link на одну страницу.

Pattern:
- Hook → first CTA (для уже-готовых, above-fold)
- Story / proof / value stack
- Mid-CTA после value
- Objection handling
- Final CTA + urgency / guarantee
- P.S. CTA последний reminder

## Above-fold strategy

Above-fold = первые 200-300 слов которые видны без скролла.

CTA выше fold уместен когда:
- Тёплая база уже знает offer (письмо 3+ в launch)
- Close cart / last call
- Sales letter для warm leads
- Re-engagement с известным offer

CTA выше fold НЕ уместен когда:
- Cold / lukewarm, нужно сначала build pain или dramatic story
- Pre-launch (offer ещё не назван)
- Nurture educational
- Story-driven письма где CTA это payoff в конце

Правило: above-fold CTA работает если читатель в первые 5 секунд уже понимает зачем кликать. Если ещё нет, гонится сначала value, CTA после.

## CTA-text actionable patterns

Actionable CTA-text начинается с глагола, конкретен, короткий (3-5 слов).

### RU CTA text

- "Перейти к [thing]" "Перейти к курсу", "Перейти к программе"
- "Забронировать [thing]" "Забронировать место", "Забронировать звонок"
- "Прочитать дальше" / "Читать полностью"
- "Получить [thing]" "Получить шаблон", "Получить доступ"
- "Записаться" / "Записаться в клуб" / "Записаться на марафон"
- "Купить [thing]" "Купить курс", "Купить доступ"
- "Скачать [thing]" "Скачать pdf", "Скачать промпт"
- "Last call: [action]" "Last call: записаться сегодня" (ТОЛЬКО close cart)
- "Посмотреть [thing]" "Посмотреть программу", "Посмотреть кейсы"
- "Узнать подробности" / "Узнать как"

### EN CTA text

- "Go to [thing]" "Go to the course", "Go to checkout"
- "Reserve [thing]" "Reserve your spot", "Reserve a seat"
- "Read more" / "Read the full thing"
- "Get [thing]" "Get the template", "Get access"
- "Sign up" / "Join the club" / "Join now"
- "Buy [thing]" "Buy the course", "Buy access"
- "Download [thing]" "Download the pdf", "Download the prompt"
- "Last call: [action]" (close cart only)
- "See the details" / "See pricing"
- "Learn more" / "Learn how"

### Запрещённые CTA-text

- "Click here" / "Кликни сюда" / "Жми сюда" (generic, не actionable)
- "Read it" / "Прочитай это"
- "Tap" / "Tap here" (без context)
- "Open" / "Открой" (без context)
- "Submit" / "Отправить" (generic для button)
- ВСЕ ЗАГЛАВНЫЕ ("ЗАПИСАТЬСЯ!")
- 1-word CTA без глагола ("Курс", "Marathon", "Программа")
- 6+ слов ("Записаться на марафон по вайбмаркетингу для экспертов"), обрезается на mobile

## Single-goal rule

Одно письмо = один goal = один destination URL. Не путать с количеством CTA-кнопок: можно иметь 3 CTA-кнопки в письме, но они ведут на ОДНУ страницу.

Single-goal допускает:
- Несколько CTA с разными anchor texts ("Узнать подробности" / "Записаться" / "Last call: оформить") на одну страницу
- UTM parameter варьируется по позиции CTA (above-fold / bottom / ps) для analytics
- Глобальный goal один: например все CTA ведут на /vaibmarketing-marathon?utm_position=X

Single-goal запрещает:
- CTA #1 на курс + CTA #2 на TG-канал + CTA #3 на YouTube = fail (3 цели)
- CTA на трипваер + CTA на основной курс = split на 2 письма
- CTA "Записаться" + CTA "Ответь если есть вопросы" допустимо если reply это micro-action ДЛЯ той же цели (квалификация), но НЕ если reply ведёт в другой funnel

Если в брифе письма есть 2+ goals, это сигнал split на 2 письма последовательно в sequence.

## CTA anchor text vs button text

Для **plain-text Kit emails** CTA = link anchor + hint в скобках.

Pattern:

```
Записаться на марафон → https://example.com/marathon
(жми по ссылке, откроется страница с программой)
```

Или встроенный:

```
Если хочешь записывайся на марафон, забирай место.
```

Для **HTML Beehiiv / template-based ESP** CTA = button text.

Pattern: standalone button с короткой надписью (3-5 слов).

```
[ Записаться на марафон ]
```

Plain-text Kit предпочтителен для nurture / story emails (выше deliverability, ощущение personal). HTML Beehiiv предпочтителен для launch / sales letter с structured offer / pricing table.

## Anti-patterns

Запрещённые CTA-паттерны:

- **Multi-goal CTA в одном письме.** "Запишись на марафон ИЛИ скачай pdf ИЛИ ответь на этот email" = fail. Split на 2-3 письма.
- **Generic "Click here" / "Read it" / "Tap" без context.** Не actionable, warning сигнал что писатель ленился.
- **4+ CTA-link в одном письме.** Overload, читатель путается, CTR падает.
- **CTA без context.** Кнопка "Tap" без предшествующего bridge ("если хочешь узнать как, жми") = миссклик и unsubscribe.
- **CTA на 4+ разных URLs в одном письме.** Сигнал что письмо распыляется. Split.
- **CTA выше fold в cold nurture.** Без pain agitation читатель воспринимает как cold sales pitch и unsubscribe.
- **CTA в самом конце без P.S.** Если письмо длинное, последний CTA должен быть в P.S. блоке потому что 40-60% читателей сначала скроллят к P.S.
- **Идентичный anchor text 3+ раза.** "Записаться → Записаться → Записаться" лениво. Варьировать: "Узнать подробности" / "Посмотреть программу" / "Записаться сейчас".
- **CTA с false urgency.** "Последний шанс" в письме 2 из 8 sequence = выжигание базы, читатели перестают верить.

## Cross-references

- references/subject-formulas-50.md Subject lines которые должны вести к CTA целью
- templates/nurture-template.md 5-section structure с CTA в section 5
- templates/launch-sequence-template.md placement CTA по дням sequence
- templates/sales-letter-template.md 2-3 CTA pattern с above-fold strategy
