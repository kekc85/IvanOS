---
name: nurture-letter-template
version: "1.0"
type: nurture
length_min_words: 600
length_max_words: 900
description: Regular newsletter, edutainment. Education + личная история + soft CTA. Базовая единица funnel'а между cash events.
---

# Template: Nurture letter

> Базовый тип письма автора. 1-2 раза в неделю. Цель - выстраивать relationship + поддерживать topic awareness + лёгкая воронка через soft CTA в клуб / клиентский лендинг.

## Body skeleton

| # | Section | Words alloc | Описание |
|---|---|---|---|
| 1 | Opening line | 10-30 (≤60 chars) | Above-fold hook. Стопит сканирование inbox. Воспринимается до click'a в письмо |
| 2 | Personal story / observation / data | 200-300 | Hook → setup. Личная история / наблюдение / цифра / событие из жизни автора за неделю |
| 3 | Тезис / lesson learned | 100-200 | «Что я из этого понял». Одна big idea - НЕ список тезисов. Тут категория-метод вайбкодинг/вайбмаркетинг может проявиться |
| 4 | Application / how-I tactic | 100-200 | Конкретный шаг 1-2-3 как ТЫ применяешь. «Personal-experience-driven framing» (по Lara Acosta). Без «How to» |
| 5 | Soft CTA | 40-80 | Один CTA с link. Soft, не push-sale. «Если хочешь - посмотри» / «детали в клубе» / «зарегистрируйся на эфир» |
| 6 | P.S. (опционально) | 20-40 | Вторая попытка hook'а. P.S. часто читается даже если основной body skip |

**Итого:** 470-880 слов (sweet spot 600-800).

## Hook framework recommendations

| Framework | Когда использовать | Пример Subject |
|---|---|---|
| Personal confession | После факап-эпизода | «Я облажался вчера» |
| Contrarian | Когда есть spicy take | «Почему я больше не пишу daily» |
| Curiosity | Когда есть deep insight | «То чего я не говорил год» |
| Direct benefit | Edutainment с практикой | «3 шага к первому $1K из подписки» |
| Numbered | Listicle-стиль content | «5 ошибок которые убивают конверсию» |

**Default rotation:** Personal confession / Contrarian / Curiosity - этот трио лучше всего работает для nurture (open rate 35-45% при тёплой базе).

## Voice rules для nurture

- **Pronoun:** «ты» (RU) / «you» (EN)
- **Formality:** low. Как письмо другу.
- **First line short** (above-fold). 30-60 chars.
- **1/3/1 rhythm:** короткая - средние - короткая.
- **Archetype:** Sage (по умолчанию) / Magician / Outlaw - ротация.
- **No corporate** («Уважаемый», «From all of us», «I hope you're doing well»).
- **No buzzword** («прокачать», «зайдёт», «бомба»).
- **No selling в nurture.** Soft CTA = invitation, не close.

## CTA rules для nurture

- **1 CTA**, в section 5
- **Soft CTA tone:** «Если интересно - посмотри», «Детали тут», «Откликнись если резонирует»
- **Link goal:** обычно клуб Skool / лендинг продукта / запись на эфир / прочитать longread
- **P.S. CTA (опционально):** может повторять main CTA с другого угла, или быть отдельным maybe-link («Кстати, я веду TG канал - @...»)

## Length distribution check

```
Opening: 1-3% (≤30 слов)
Story: 30-40%
Тезис: 15-25%
Application: 15-25%
Soft CTA: 5-10%
P.S.: 3-5%
```

Если distribution выходит за рамки - re-balance.

## EMAIL-gates специфика для nurture

- EMAIL-G1: 3 Subject варианта min (можно 4-5)
- EMAIL-G2: Preheader synergy 0.3-0.7
- EMAIL-G3: 1 CTA-link min (P.S. CTA опционально)
- EMAIL-G4: Mobile preview obligatory
- EMAIL-G7: 600-900 words

## Examples (для few-shot)

См. `examples/_TEMPLATE.md` секция «Nurture» (после fill ученика / автора).

## Anti-patterns в nurture

- НЕ продавать прямо в nurture (push sale = unsubscribe)
- НЕ давать >1 CTA (multi-CTA убивает конверсию)
- НЕ писать generic «I hope you're doing well» intro
- НЕ выходить за 900 слов (если выходит → split на 2 nurture или это longform `[[longform]]`)
- НЕ забывать P.S. (часто читается даже если main body skip)
- НЕ ставить sales-letter timing'ы (urgency / scarcity) - это работа sales-letter template