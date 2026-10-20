---
name: launch-sequence-frameworks
version: 1.0
description: Канонические launch sequence frameworks (Jeff Walker PLF, Halbert 5-Letter, Welsh nurture-to-pitch, Hormozi Velocity) для email-машины контент-завода автора. Применяется в workflow/02-structure.md при выборе модели sequence и в workflow/03-write.md при написании каждого письма последовательности.
---

# Launch Sequence Frameworks

## Зачем launch sequence

Одно письмо с офером в холодную базу даёт конверсию 0.1-0.5%. Sequence из 5-8 писем в ту же базу даёт 2-7%. Разница не в технике copywriting, а в накоплении 4 эффектов внутри окна.

- Cognitive priming: читатель в Day 0 не готов к покупке. К Day 3 он уже знает категорию, метод и автора. Решение «купить vs пропустить» принимается на фоне сложившейся картины, а не с нуля.
- Urgency build: один cutoff без warm-up не убеждает. Sequence строит ощущение приближающегося окна постепенно (Day 1 «открыли», Day 3 «осталось 48 часов», Day 5 «через 6 часов закрытие»).
- Objection handling: реальные возражения покупателя (цена, время, доверие, формат) невозможно закрыть в одном письме. Каждое возражение получает своё письмо с своим углом.
- Social proof accumulation: одно письмо = один кейс / одно testimonial. Sequence = 3-5 разных доказательств которые в сумме формируют critical mass доверия.

Все 4 эффекта работают только при последовательности. Пропуск даже одного письма из 5 ломает arc, читатель теряет контекст и решает «потом разберусь», что эквивалентно «никогда».

## Framework 1: Jeff Walker Product Launch Formula (PLF)

PLF, наиболее формализованный launch framework, разработан Jeff Walker в начале 2000-х для info-products. Базовая модель: трёхэтапная подготовка (pre-pre-launch, pre-launch, launch) с накопленным cognitive priming через free value перед открытием cart.

### Stage 1: Pre-pre-launch (за 7-14 дней до open cart)

1-2 письма teaser-формата. Цель пробудить любопытство без раскрытия деталей.

- Письмо 1 (-14d или -10d): «работаю над чем-то новым, расскажу через неделю». 60-120 слов. Без названия продукта, без цены.
- Письмо 2 (-7d или -5d): «через несколько дней покажу. Что бы ты хотел узнать?», приглашение к отклику для warm-up сегмента.

В этом skill маппится на `email type = launch-sequence`, position = `pre-launch`.

### Stage 2: Pre-launch (3 PLV видео + 3 email-обёртки)

Walker называет три видео PLV1, PLV2, PLV3. Каждое доставляет чистую value (без оффера) и заканчивается teaser к следующему. Email-обёртка, это письмо которое презентует видео.

- PLV1 «Opportunity»: показывает что мир изменился, есть новая возможность. Email-обёртка анонсирует видео + 1 параграф why now.
- PLV2 «Transformation»: показывает путь от состояния А к состоянию Б. Email-обёртка фокусируется на 1 конкретной трансформации.
- PLV3 «Ownership»: показывает что читатель уже способен это сделать (под крылом метода). Email-обёртка заканчивается teaser к открытию cart.

В этом skill маппится на `email type = launch-sequence`, position = `pre-launch`. Каждое PLV-письмо длинной 250-400 слов, видео-ссылка above-fold.

### Stage 3: Open cart (4-7 писем за 4-7 дней)

- Day 1 (Launch / Open Cart): объявление «cart открыт», полное описание оффера, первая CTA. Длинное письмо 600-1000 слов. В skill маппится на `email type = sales-letter`, position = `launch-day`.
- в день запуска (Story / Proof): один развёрнутый кейс или story-сегмент. 400-600 слов. В skill маппится на `email type = sales-letter`, position = `open-cart`.
- Day 3 (FAQ / Objection): 5-8 главных возражений с ответами. 500-700 слов. Position `open-cart`.
- в день запуска (Last 24h): urgency-письмо, фокус на «осталось N часов». 200-350 слов. Position `close-cart`.
- Day 5 (Close): финальное «через X часов закрываем». 150-250 слов. Position `close-cart`.

### Когда использовать PLF

- High-ticket <твой ценовой диапазон> (или RU 199-790К₽)
- Уже сформированная база минимум 2000 подписчиков с open rate 25%+
- Есть 2-4 недели на подготовку + production трёх PLV видео
- Запуск редкий (1-4 раза в год), не daily product

Для автора PLF подходит под cash event квартального запуска курса вайбкодинг.

## Framework 2: Halbert 5-Letter Sales Sequence

Сборка от Гэри Халберта (Boron Letters), адаптирована под digital. Короче PLF, без видео-pre-launch, фокус на text-driven persuasion. Применяется при более коротком окне (5-7 дней) и более warm-аудитории.

### Letter 1: Setup / Story (Day 1)

Привлечь attention через личную story или resonant observation. Цель identification («это про меня»). Без оффера, без цены. 400-600 слов. Position `pre-launch` или `launch-day` если sequence начинается с открытия cart.

### Letter 2: Value / Education (в день запуска)

Доставить one big lesson или framework без продажи. Build trust через demonstrated expertise. 500-700 слов. Position `open-cart` если cart уже открыт, иначе `pre-launch`.

### Letter 3: Offer Introduction (Day 3)

Соединить story из Letter 1 + value из Letter 2 + product. Первое прямое предложение купить. 700-1000 слов. Полное описание оффера, гарантия 14 дней, первая CTA. Position `launch-day` или `open-cart`.

### Letter 4: Objection / Proof (в день запуска-5)

Закрыть 3-5 главных возражений. Включить proof elements (метод, логика, гарантия). Без выдуманных testimonials если первый запуск. См. `[[feedback-first-launch-no-alumni]]`. 500-700 слов. Position `open-cart`.

### Letter 5: Close (Day 6-7)

Urgency + final CTA. «Закрываем через X часов». 200-400 слов. Position `close-cart`.

### Когда использовать Halbert

- Mid-ticket $500-2000 (RU 50-200К₽)
- Shorter cycle 5-7 дней
- Warm база (open rate 30%+)
- Solopreneur без production бюджета
- Онбординг новых подписчиков в Skool club (адаптация под membership offer)

## Framework 3: Welsh Nurture-to-Pitch (90/10)

Модель Justin Welsh для solopreneur newsletter (Beehiiv / Kit). Не отдельный launch framework, а ритм жизни всего канала: 90% нагревающего контента + 10% pitch в редких окнах.

### Структура 10-недельного цикла

- Недели 1-9: один nurture email в неделю (teaching, story, framework). По типологии skill = `nurture` email type.
- Неделя 10: pitch window. 1-2 sales-letter письма в одном окне. По типологии = `launch-sequence` position `launch-day` + `close-cart`.

Pitch window короткий: open 48-72 часа, 2 письма (open + close). Без full Halbert / PLF arc.

### Когда использовать Welsh

- Retention focus, длинный horizon (год+)
- Сильный newsletter game (open rate 35%+, click rate 5%+)
- Mini-event $97-497 (RU 5-50К₽)
- Соло-предприниматель без launch bandwidth раз в квартал
- Канал = main asset, продукты обновляются медленно

Для автора Welsh подходит под mini-events между квартальными cash events.

## Framework 4: Hormozi Velocity

Модель Alex Hormozi для proven info-products с короткой воронкой. Не sequence в традиционном смысле, а 4-точечный пинг по уже warm-аудитории.

### Структура

- Day 0 (Launch): объявление открытия + полный оффер + CTA. 500-700 слов. Position `launch-day`.
- Day 1 (Social Proof Case): один конкретный кейс с метриками. 300-500 слов. Position `open-cart`.
- Day 3 (Objection): главное общее возражение с ответом. 400-600 слов. Position `open-cart`.
- Day 7 (Last Chance Close): closing urgency. 200-350 слов. Position `close-cart`.

### Когда использовать Hormozi Velocity

- Short window 7 дней
- Mid-ticket $497-1497
- Продукт уже proven (минимум 2 предыдущих запуска с данными)
- Warm база с историей покупок

Для автора не основной framework на первый запуск (нет proof data). Применим после второго-третьего запуска курса вайбкодинг.

## Choosing Framework по контексту автора

| Контекст | Framework | Длительность | Кол-во писем |
|---|---|---|---|
| Cash event <твой ценовой диапазон> (квартальный запуск курса) | PLF | 14-21 день | 7-12 |
| Mini-event $97-497 | Welsh nurture-to-pitch | 10 недель цикл, 2-3 дня pitch | 2-3 в окне |
| Skool club membership онбординг | Halbert 5-Letter | 5-7 дней | 5 |
| Proven re-launch (с 3-го запуска) | Hormozi Velocity | 7 дней | 4 |

Выбор framework, первый шаг в workflow/02-structure.md. Без выбора framework нет sequence position для отдельного письма.

## Sequence Position Types

Каждое письмо внутри sequence имеет position. Position определяет tone, length, CTA, urgency level.

### pre-launch

- Когда: до открытия cart (-14d, -7d, -3d, -1d)
- Tone: curious, building anticipation
- Length: 60-400 слов
- CTA: «жди следующее письмо», «ответь что хотел бы узнать»
- Urgency: low, ноль hard deadline
- Email types: launch-sequence, nurture

### launch-day

- Когда: Day 0 / Day 1 открытия cart
- Tone: excited, energetic, direct
- Length: 500-1000 слов
- CTA: «оформить», прямая ссылка на checkout
- Urgency: medium, «cart открыт на N дней»
- Email types: sales-letter

### open-cart

- Когда: Day 1-4 после открытия (середина окна)
- Tone: calm, proof-focused, addressing objections
- Length: 300-700 слов
- CTA: «оформить», часто soft CTA («посмотри полную страницу»)
- Urgency: medium-high, накопление social proof
- Email types: sales-letter

### close-cart

- Когда: последние 24-48 часов перед закрытием
- Tone: direct, urgent, calm-not-panicked
- Length: 150-400 слов
- CTA: прямая ссылка на checkout, single CTA
- Urgency: high, «осталось N часов»
- Email types: sales-letter

## Sequence Consistency Rules

Sequence работает только если внутри окна сохраняется consistency по 5 параметрам. Нарушение любого = trust break и drop конверсии.

### One Big Idea

Одна центральная идея на всю sequence. Если Day 0 говорит «новый метод вайбмаркетинга», Day 3 не может говорить «возможно тебе нужен SaaS». Big Idea зафиксирована в workflow/02-structure.md шаг 1 и переносится во все письма.

### One CTA Goal

Все письма ведут на один checkout URL. Не «купи курс ИЛИ запишись на эфир ИЛИ заполни анкету». Один primary action. Soft CTA (типа «прочитай полное описание») допустимы при условии что они ведут на ту же страницу checkout.

### One Archetype Primary

Magician / Sage / Outlaw / Hero, выбрать 1, максимум 2 (primary + secondary). Не менять между письмами. Если Day 0 = Sage (структурное объяснение), Day 3 не может быть Outlaw (rebel critique конкурентов). Mid-sequence pivot ломает читательский trust.

### Voice Arc

Эмоциональный arc по всей sequence:

- pre-launch: curious, slightly mysterious
- launch-day: excited, confident
- open-cart middle: calm, proof-focused
- close-cart: direct, urgent, но не panicked

Voice arc не «писать в одном настроении». Это запланированная динамика.

### Callback + Teaser (EMAIL-G8)

Каждое письмо в sequence:

- Callback к предыдущему: «вчера я писал про X. Сегодня…»
- Teaser к следующему: «завтра расскажу почему Y…»

Это требование EMAIL-G8 (workflow/04-review.md, review gate). Без callback + teaser sequence распадается на отдельные письма.

## Length Distribution per Position

| Position | Words count | Skim time | CTA position |
|---|---|---|---|
| pre-launch (teaser) | 60-150 | <30 sec | end only |
| pre-launch (PLV-style) | 250-400 | 1-1.5 min | end + middle |
| launch-day (open cart) | 500-1000 | 2-4 min | above-fold + middle + end |
| open-cart (story) | 400-600 | 1.5-2 min | middle + end |
| open-cart (FAQ/objection) | 500-700 | 2-3 min | end only |
| close-cart (last 24h) | 200-350 | <1.5 min | above-fold + end |
| close-cart (last call) | 150-250 | <1 min | above-fold + end |

Words count, RU baseline. EN tends to быть на 15-20% меньше за счёт более коротких слов.

## Anti-patterns

### Multi-product offer в одной sequence

«Купи курс ИЛИ зайди в Skool ИЛИ запишись на 1-1». Размывает решение, конверсия падает на 60-80%. Решение: один offer на sequence, второстепенные продукты, отдельные sequences или nurture-only mentions.

### Менять CTA goal между letters

Day 0 ведёт на checkout курса, Day 3 ведёт на free webinar registration. Читатель теряет ориентир. Если webinar часть pre-launch, он должен быть в pre-launch position, не в open-cart.

### Negативные статистики

«Только 5% доходят до результата», «90% бросают на середине». См. `[[feedback-no-negative-stats-in-public-offer]]`. Внутри методики и эфиров OK, в email-sequence публичной запрещено. Убивает urgency через подсознательное «значит это не для меня».

### Fake testimonials если первый запуск

См. `[[feedback-first-launch-no-alumni]]`. Курс вайбкодинг, первый запуск, выпускников нет. Любая фраза «как сказал ученик X» = выдумка, не использовать. Альтернатива: использовать кейсы из других продуктов автора с явным указанием контекста («не из этого курса, но из соседнего проекта»).

### «Last chance forever» когда продукт будет ещё раз

«Больше никогда не открою» при том что запуск квартальный = trust killer. После 1-2 повторов база перестаёт верить любому close-cart. Альтернатива: честное «следующий запуск через N месяцев» или «следующий запуск по другой цене».

### Spam-trigger phrases в Subject

См. `references/spam-triggers-list.md`. Даже в close cart нельзя использовать «100%», «гарантия», «срочно» в Subject. Body context-allowed под условиями.

### Em-dash внутри строк

Memory rule: только дефис «-» или запятая. Em-dash допустим только в начале bullet list. См. memory `[[feedback-no-em-dash]]`.

### Метафоры

Memory rule: запрещены метафоры если есть точный термин. См. `[[feedback-no-metaphor-if-term-exists]]`. «Контент-завод» = OK (зафиксированный термин автора). «Печь возможностей» = запрет.

### Нельзяграм

Memory rule: всегда «Нельзяграм», не «Нельзяграм».  Жёсткое правило для всех артефактов skill.
