---
name: compliance
version: "1.0"
last_reviewed: 2026-05-28
description: Email-marketing compliance requirements - GDPR / CAN-SPAM / 152-ФЗ unsubscribe / sender info / consent. Mandatory checklist для production. EMAIL-G9 gate в workflow/04-review.md.
---

# Compliance - GDPR / CAN-SPAM / 152-ФЗ

> Skill production-grade. Без compliance письмо может попасть в spam, привести к жалобе Роспотребнадзора, или нарушить EU/US закон. Это mandatory section для любой email рассылки.

## Что регулируется

| Закон | Юрисдикция | Применимо к |
|---|---|---|
| **CAN-SPAM Act 2003** | США | Любые commercial emails читателям в US |
| **GDPR Article 7** | EU | Любые emails читателям в EU |
| **CASL 2014** | Канада | Любые emails читателям в Canada (одно из самых строгих) |
| **152-ФЗ "О персональных данных"** | РФ | Любые emails читателям в РФ |
| **ЗоЗПП ст. 10** | РФ | Любые маркетинговые сообщения в РФ |

## Mandatory elements для любого commercial email

### 1. Unsubscribe link

- **CAN-SPAM:** "clear and conspicuous notice of opportunity to opt-out" - link на каждом письме
- **GDPR:** "easy withdrawal of consent" - one-click unsubscribe
- **CASL:** unsubscribe должен работать <10 business days
- **152-ФЗ:** отписка - право субъекта, реализуется без затруднений

**Implementation в skill:**

Если ESP = Kit / Beehiiv -> auto-handled by platform footer.
Если ESP = custom -> ОБЯЗАТЕЛЬНО добавить в template footer:

```
RU: «Если больше не хочешь получать письма - отписаться: <link>»
EN: «Don't want these emails? Unsubscribe: <link>»
```

### 2. Sender identification

- **CAN-SPAM:** "physical postal address of sender" в каждом письме
- **GDPR:** controller identification + legal entity
- **152-ФЗ:** оператор персональных данных идентифицирован

**Implementation:**

```
RU: «ИП [ФИО] [name], ИНН [инн], [physical address или PO box]»
EN: «<your name>, [legal entity], [physical address]»
```

Ставится в footer одной строкой.

### 3. No deceptive subject lines

- **CAN-SPAM:** subject must accurately reflect body
- **GDPR:** transparent processing

**Уже покрыто** в `references/spam-triggers-list.md` + workflow/04-review.md EMAIL-G5.

### 4. Consent на старте

- **GDPR:** opt-in mandatory (double opt-in рекомендуется)
- **CAN-SPAM:** opt-in для transactional не нужен, для marketing - желателен
- **152-ФЗ:** согласие на обработку персональных данных (часть стандартной формы регистрации)

**Implementation:**

Не задача email skill. Задача form/landing skill. Skill assumes база уже opted-in.

### 5. Identification как marketing

- **CAN-SPAM:** "clear and conspicuous identification that message is advertisement"
- **CASL:** обязательно

Для nurture letter и launch sequence (от автора лично) - не строго advertising. Для sales-letter -> идентифицировать как commercial offer.

**Implementation:** в footer строка типа «Это маркетинговое письмо от автора» (RU) или «This is a promotional email from <your name>» (EN).

## EMAIL-G9 gate (новый)

Добавляется в `workflow/04-review.md` Layer 2:

### EMAIL-G9 - Compliance check

Для каждого письма перед publish:

- ✓ Unsubscribe link присутствует в body OR template ESP auto-handles footer (Kit/Beehiiv)
- ✓ Sender identification присутствует (ИП ФИО + ИНН или физ. адрес для US)
- ✓ Subject не вводит в заблуждение (accuracy check vs body promise)
- ✓ Если sales-letter - identification как commercial OK
- ✓ Если sales-letter - указан гарантия возврата (152-ФЗ ЗоЗПП ст. 10)

→ FAIL при нарушении.

## ESP-specific compliance behavior

### Kit (default)

Auto-handles:
- Unsubscribe link в footer (mandatory, нельзя убрать)
- Sender info из account settings
- Suppression list для unsubscribed
- Reply-to address

**Skill output не требует custom compliance text** - Kit добавляет footer автоматически. Skill только проверяет что в Kit account настройки правильные (one-time setup).

### Beehiiv

Auto-handles:
- Unsubscribe link в footer
- Sender info
- Suppression list
- Reply-to

Аналогично Kit - skill output не нужен custom text.

### Custom ESP (e.g. self-hosted Mailgun / Postmark)

**Skill ДОЛЖЕН** добавить footer в каждом письме:

```
RU footer template:
-----
Если больше не хочешь получать письма - отписаться: {unsubscribe_link}
{sender_legal_entity} | ИНН: {inn} | {physical_address или PO box}
Это маркетинговое письмо. Reply on {reply_email}
-----

EN footer template:
-----
Don't want these emails? Unsubscribe: {unsubscribe_link}
{sender_legal_entity} | {physical_address}
This is a promotional email. Reply to {reply_email}
-----
```

Skill читает `config.esp.default`. Если `custom` или `null` - auto-injects footer.

## Workflow integration

В `workflow/04-review.md`:

```
EMAIL-G9 check:
  IF config.esp.default in ['kit', 'beehiiv']:
    auto_compliance = True  # ESP handles
    -> PASS
  ELSE IF config.esp.default == 'custom':
    check body contains unsubscribe link + sender ID
    -> PASS or FAIL
  ELSE:
    WARN: 'ESP unknown, manual check required'
```

В `workflow/05-publish.md`:

```
IF config.esp.default == 'custom':
    inject_compliance_footer(body, config)
ELSE:
    note: 'ESP auto-handles compliance footer'
```

## 152-ФЗ specifics для RU рассылок

Дополнительно к unsubscribe / sender ID:

1. **Согласие на обработку** - получено на стадии opt-in (форма регистрации). Не задача email skill.
2. **Право на удаление** - subject может потребовать удаления данных. Не задача email skill, но ESP должен поддерживать (Kit + Beehiiv ОК).
3. **Гарантия возврата 14 дней** для sales-letter - per ЗоЗПП ст. 25, ст. 26.1. Уже в `templates/sales-letter.md` принципы.

## Anti-patterns

- НЕ убирать unsubscribe link "потому что мне не хочется чтобы отписывались" - hard fail compliance + Mailtrap blacklisting
- НЕ использовать «No-reply@» как from address - читатель не может ответить = CAN-SPAM violation
- НЕ скрывать sender info - identity fraud
- НЕ маскировать commercial intent в subject ("Quick question" для sales-letter) - CAN-SPAM deceptive
- НЕ обходить suppression list (если человек отписался - не присылать заново через 6 мес "новой welcome series")
- НЕ собирать emails без opt-in для GDPR audience

## Sources

- CAN-SPAM Act 2003 (FTC.gov)
- GDPR Article 7 + Recital 32 (gdpr-info.eu)
- CASL 2014 (fightspam.gc.ca)
- 152-ФЗ "О персональных данных" (consultant.ru)
- ЗоЗПП РФ (consultant.ru)

## Когда пересматривать

- Изменения в законодательстве (раз в полгода чек)
- Новый ESP добавлен в config.esp options
- автор получил жалобу от подписчика (любой источник - чат поддержки / email / TG)
- Mailtrap / SendGrid deliverability scores снижаются
