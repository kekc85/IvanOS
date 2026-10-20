---
name: spam-triggers-list
version: 1.0
description: Spam trigger words и patterns (RU + EN) для email-машины контент-завода автора. Применяется в workflow/03-write.md при написании Subject / Preheader и в workflow/04-review.md как regex-based detection gate перед output.
---

# Spam Triggers List

## Введение

Spam triggers, слова и patterns которые увеличивают spam-score у Gmail / Outlook / Mail.ru / Apple Mail. Использование одного trigger-слова обычно не fail one-shot, не отправляет письмо сразу в Spam. Но многократное использование внутри одного письма или системное использование в одной из ключевых зон (Subject, From-line, первый параграф) = inbox tab вместо primary tab у Gmail, или Junk Folder у Outlook.

В контексте email-машины автора главная проблема не «попадание в Spam», а deliverability downgrade: письмо доставлено в Promotions tab вместо Primary, open rate падает с 30% до 8%, конверсия sequence обнуляется. Поэтому правило: ноль hard-fail слов в Subject, минимум trigger-слов в body (≤2 на письмо), context-aware exceptions для legal terms.

## Sources

Спам-триггеры собраны из публичных deliverability docs:

- Mailtrap blog «Spam Trigger Words 2024»
- SendGrid «Spam Words to Avoid»
- ActiveCampaign «Email Deliverability Best Practices»
- Mail.ru deliverability docs (postmaster.mail.ru)
- Apple Mail и iCloud Mail public filter guidelines

Списки ниже, базовый industry consensus, не выдуманные. Все слова можно перепроверить в open lists Mailtrap / SendGrid.

## RU Hard Fail Words

Запрещены в Subject. В body контекстно допустимы при условиях.

### Финансовые crash-triggers

- бесплатно (в Subject hard fail; в body OK если контекст value)
- недорого
- скидка XX% (любая %-скидка в Subject)
- акция
- распродажа
- выгодное предложение
- эксклюзивно
- заработай / заработок
- доход в месяц
- быстрые деньги
- финансовая независимость
- пассивный доход
- без вложений
- инвестиции / инвестируй
- кредит / займ

### Urgency crash-triggers

- срочно / срочное
- только сегодня
- последний шанс
- не пропустите
- не упусти
- сейчас или никогда
- осталось мало мест
- спеши

### Authority / hype crash-triggers

- ОФИЦИАЛЬНО (любые CAPS)
- 100% (число + %)
- гарантия (контекстно «гарантия возврата 14 дней», legal term, OK в body)
- прорыв
- сенсация
- секрет успеха
- революционный
- уникальный шанс
- проверенный метод заработка

### Spam-классические

- казино
- ставки
- кредитная история
- очистка карма
- похудение быстро
- знакомства
- эротический массаж

Эти слова не появятся в скриптах автора, но regex должен их детектить если случайно протекло из ингеста чужого контента.

## EN Hard Fail Words

Запрещены в Subject. В body, контекстно.

### Финансовые

- free
- earn extra cash
- make money
- extra income
- pure profit
- serious cash
- cash bonus
- save big
- $$$
- billion / billions
- investment
- credit
- mortgage
- eliminate debt
- hidden assets
- increase sales
- double your

### Urgency

- urgent / urgency
- urgent reply
- ACT NOW
- order now
- apply now
- limited time
- this won't last
- while supplies last
- last chance
- expires today

### Authority / hype

- guaranteed
- 100%
- risk-free
- no risk
- no obligation
- no cost
- no fees
- amazing
- exclusive
- lifetime
- promise
- satisfaction
- super
- special promotion
- dear friend

### Spam-классические

- prize
- winner / you're a winner
- congratulations (без context)
- claim
- click here
- giveaway
- opportunity (в стиле scam, контекст важен)
- lose weight
- pharmacy / viagra / cialis

## Regex Patterns для Auto-detection

В workflow/04-review.md эти patterns используются как regex gate, fail-detection перед output.

### Casing / punctuation

- `[A-ZА-Я]{4,}` - 4+ CAPS подряд (CAPS-shout). Hard fail в Subject. Body warning.
- `!{2,}` - multi-exclamation (`!!` или `!!!`). Hard fail везде.
- `\?{2,}` - multi-question (`??` или `???`). Warning в Subject.
- `\.{3,}` - multi-dot ellipsis (4+ точек). Warning, не hard fail.

### Numeric / currency

- `\$\d` - $50, $1997 в Subject. Hard fail Subject; body OK с context.
- `\d+%` - proc numbers («100%», «50%»). Hard fail Subject; body warning.
- `₽\s?\d` - RU currency в Subject. Hard fail Subject; body OK.
- `\d+\s?(₽|руб|RUB)` - RU price patterns. Subject hard fail.

### Visual scam markers

- `>>+` - multi-arrows (`>>` или `>>>`). Hard fail.
- `★|✓|✔|☆|⭐` - emoji-like stars в Subject. Warning (Gmail Promotions trigger).
- `🔥|💰|💸|🚀|⚡` - emojis в Subject. Warning, не hard fail (контекстно допустимы для casual brands, не для info-products автора).

### Wordlist hits

Каждое слово из RU/EN hard fail list - regex `\b(word1|word2|...)\b` с case-insensitive flag.

## Context-allowed Exceptions

Некоторые spam-trigger слова обязательны в legal или industry-стандартных формулировках. Их использование под условиями.

### Гарантия 14 дней

«гарантия возврата 14 дней», legal term ЗоЗПП РФ, обязательный элемент Welsh / Halbert / Hormozi sales letters. OK в body sales-letter. Запрещён в Subject. Формулировка только полная: «гарантия возврата 14 дней» или «полный возврат в 14 дней». Без «100% гарантия» (двойной trigger).

### Бесплатный гайд внутри

«бесплатный гайд внутри», nurture email body OK (lead magnet announcement). Запрещён в Subject. Альтернатива в Subject: «гайд по [теме] прикрепил» или «забрал ссылку?».

### Free guide inside

Аналогично EN. Body OK, Subject - нет. Альтернатива: «guide attached» / «link inside».

### Last call

OK в Subject close-cart sales-letter, single use в рамках всей sequence. Не использовать в открытии или середине окна. Не комбинировать с другими triggers («LAST CALL!!! 100%»).

### Срочный апдейт по запуску

Body OK если есть real urgency event (сдвинули даты, открыли early access, изменили цену). Запрещён без реальной причины. Запрещён в Subject.

## Subject-only Hard Fails vs Body Context-allowed

| Слово / pattern | Subject | Body | Условие body |
|---|---|---|---|
| бесплатно / free | hard fail | OK | контекст value (не повторяться) |
| гарантия | hard fail | OK | полная фраза «гарантия возврата 14 дней» |
| 100% / 100 percent | hard fail | hard fail | не использовать |
| CAPS 4+ chars | hard fail | warning | только если это аббревиатура (URL, API) |
| $XXX / ₽XXX | hard fail | OK | в офере прозрачно |
| `!!` | hard fail | hard fail | не использовать |
| срочно / urgent | hard fail | OK | real urgency event |
| last chance | hard fail | OK | single use в close-cart |
| скидка XX% | hard fail | warning | если структурный элемент офера |
| прорыв / breakthrough | hard fail | warning | не использовать в этом слове (метафора) |

## Deliverability Beyond Words

Spam-trigger words это один из 30+ факторов deliverability. Beyond words:

### Authentication

SPF / DKIM / DMARC должны быть настроены через ESP (Kit, Beehiiv). Без них любое письмо с любым контентом улетает в Junk. Это настройка инфраструктуры, не контент. Скилл предполагает что authentication настроено.

### Engagement signals

Open rate, click rate, reply rate. Здоровая база (open rate 25%+) сама по себе защищает от spam-классификации. Sick база (open rate <10%) делает любое слово в письме trigger-чувствительным.

### Suppress unengaged

Kit auto-feature: unsubscribe / suppress подписчиков которые не открывали последние 60-90 дней. Это держит engagement metrics в зелёной зоне. Включить в Kit settings перед запуском первой sequence.

### Plain-text version mandatory

HTML-only письма у Gmail падают на 15-25% deliverability. Beehiiv делает auto-plain-text fallback. Kit требует ручного включения. Всегда включать plain-text version.

### Image-to-text ratio

Письмо с 60%+ visual content (картинки, GIF) классифицируется как promotional. Sales letter автора почти всегда text-driven, image только в hero / CTA-button (если HTML). Plain-text Kit не имеет этой проблемы.

## Anti-patterns

### Multi-spam-trigger в одной letter

«Срочно! Бесплатный гайд внутри. 100% гарантия. Last chance!!!». Каждое слово context-allowed по отдельности. В одной строке = hard fail Gmail Promotions tab.

### CAPS Subject в любом контексте

«ОТКРЫЛИ КУРС!» / «LAST CHANCE!». Hard fail Subject у всех ESP. Альтернатива: «Открыли курс вайбкодинг» (sentence case) или «вайбкодинг открыт» (lowercase).

### Мнимая urgency

«Срочно!» в Subject когда реальной urgency нет (cart открыт ещё 5 дней). Двойной damage: spam-trigger + ломает читательский trust («снова кричит, а ничего не происходит»).

### Subject = preheader дубль

«Открыл курс» / «Открыл курс вайбкодинг сегодня». Дублирование Subject и preheader, waste of inbox space + signal Gmail классификации «низкое качество письма». Preheader должен дополнять Subject новым углом.

### Emoji-storm в Subject

«🚀🔥 Вайбкодинг открыт! ⚡💰». Warning у Gmail, hard fail у Mail.ru. Допустим максимум 1 emoji в Subject для casual brands. В info-products автора emoji в Subject запрещён.