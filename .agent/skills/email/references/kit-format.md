---
name: kit-format
description: Kit (бывший ConvertKit) - primary ESP для email skill контент-завода. Plain-text bias, Broadcasts vs Sequences vs Visual Automations, Subject A/B, Preheader, формат вывода для broadcast, anti-patterns. Используется в `workflow/03-write.md` Pass 1 и в `templates/*.md` при сборке финального артефакта.
version: 1.0.0
last_updated: 2026-05-28
---

# Kit format - primary ESP

Kit (бывший ConvertKit) - primary ESP контент-завода автора. автор выбрал Kit за tag-based automations и plain-text bias (memory `[[feedback-newsletter-platform-beehiiv-vs-kit]]`). Email skill по умолчанию выдаёт артефакт под Kit. Beehiiv - opt-in alternative (см. `references/beehiiv-format.md`).

Документ объясняет как устроен Kit, что доступно на каких тарифах, какие форматы вывода Kit ожидает, и какие anti-patterns ломают доставляемость или конверсию.

## Kit account types

Kit имеет 3 ценовых уровня. Email skill работает на всех трёх, но некоторые фичи доступны только на платных.

- **Newsletter** (free до 10К подписчиков) - Broadcasts, Sequences, basic Forms, 1 audience. Нет A/B test, нет Visual Automations.
- **Creator** (от \$15/мес) - всё из Newsletter + Visual Automations + Subscriber Scoring + integrations. Нет A/B test subject lines.
- **Creator Pro** (от \$29/мес) - всё из Creator + Subject Line A/B testing + advanced reporting + newsletter referral system + custom HTML.

автор по умолчанию на Creator Pro. Ученик в onboarding (`workflow/00-onboarding-student.md` Q3) указывает свой tier. Если ученик на Newsletter free, skill пропускает Subject A/B блок в output.

## Broadcasts vs Sequences vs Visual Automations

Три способа отправить письмо в Kit. Email skill v1 покрывает Broadcasts и Sequences.

- **Broadcast** - one-shot send в segment или всю базу. Использовать для: nurture letter (одиночное), weekly digest, announcement, sales-letter close cart blast. Default тип для skill.
- **Sequence** - drip series, серия писем с задержками между. Использовать для: welcome email series (Day 0, Day 1, Day 3, Day 7), launch sequence (7-14 писем под запуск), re-engagement (Day 30, Day 60, Day 90). Skill режим `launch-sequence` и `nurture` Day N.
- **Visual Automation** - conditional logic с branching (если открыл письмо 3, отправить ветку A, если кликнул, ветку B). Beyond v1 scope, не покрывается skill.

## Plain-text bias

Kit изначально построен под personal-style emails от creator к audience. Plain-text формат - дефолт.

- **Higher deliverability** - plain воспринимается inbox-фильтрами как personal mail (не promo), попадает в Primary tab Gmail чаще
- **Better mobile render** - нет broken HTML на iOS Mail, Outlook Mobile, Gmail App
- **No HTML breaks** на iOS Mail и Outlook desktop (HTML emails часто ломаются именно там)
- **Faster load** - text грузится мгновенно даже на 3G
- **Kit auto-strips** многослойное форматирование в Plain Text mode (если копи-паст из Notion / Google Docs)

Вывод: skill по умолчанию выдаёт plain-text с markdown-style hints. HTML опционален и только если ученик явно попросил visual newsletter (тогда лучше Beehiiv).

## Plain-text formatting tricks

Kit Plain Text editor поддерживает markdown-style разметку и сам конвертит в inline styles. Что skill использует:

- **Italic** - `*текст*` рендерится как italic в final email
- **Bold** - `**текст**` рендерится как bold
- **Headers** - НЕ использовать `# H1` или `## H2`. Вместо: ЗАГЛАВНЫЕ СЛОВА на отдельной строке или strategic blank lines между параграфами. Plain-text personal mail не имеет h1.
- **Bulleted list** - символ `- ` (дефис + пробел) или `• ` в начале строки. Kit конвертит в list element.
- **Linebreaks** - двойной перенос разделяет параграфы. Single перенос это soft break внутри параграфа (рекомендуется избегать, ломает mobile render).
- **Links** - два варианта: чистый URL (Kit auto-linkifies) или markdown-style anchor (Kit конвертит в HTML тег a).

Email skill в output всегда использует markdown-style разметку. Ученик копирует в Kit Broadcast composer (Plain Text mode), Kit конвертит автоматически.

## Subject lines в Kit

Технические лимиты и best practices Subject поля в Kit.

- Максимум 100 chars технически (Kit обрезает после 100)
- Best practice ≤50 chars (mobile inbox preview показывает первые ~40 chars на iPhone, ~33 chars на Android)
- Emoji разрешены (но не злоупотреблять, попадание в spam фильтры повышается с 2+ emoji)
- A/B test allowed только на Creator Pro tier
- Subject A/B field появляется в Broadcast composer (кнопка Add A/B Test)

## Subject A/B workflow в Kit

Если ученик на Creator Pro tier, skill выдаёт два Subject варианта (A и B). Конфиг по умолчанию:

- 30% audience split (15% получают A, 15% получают B)
- 4 часа wait time, Kit замеряет open rate за окно
- Winner-by-opens-rate, победитель отправляется оставшимся 70%
- Можно сменить metric на click-rate (но opens default для большинства email skill кейсов)

Email skill всегда выдаёт ровно 2 варианта Subject (A primary, B challenger). Если у ученика Newsletter / Creator tier, пишет в output: A/B недоступен на твоём tier, используй вариант A.

## Preheader (Preview text) в Kit

Preheader это hidden field в Broadcast composer, который показывается в inbox preview сразу после Subject.

- Если оставить пустым, Kit auto-pulls первые ~100 chars body. Обычно это Hi first_name или duplicate первой строки Subject. Bad UX.
- Always fill explicitly, отдельный сильный hook, дополняющий Subject (не дублирующий)
- Best practice 50-100 chars (mobile inbox preview обрезает ~80 chars)
- Email skill всегда выдаёт Preheader как обязательное поле output

## Tags и Segments

В Kit база подписчиков сегментируется через Tags и Segments. Skill использует это для таргетинга broadcast или sequence.

- **Tags** - отдельные метки на подписчиков (e.g. marathon-attendee-may-2026, cash-event-2026-q3, interested-vibemarketing, club-skool-active). Подписчик может иметь много tags.
- **Segments** - saved filters (например, segment marathon attendees who haven't bought course yet). Базируются на комбинации tags + behavior.
- **Forms** - точки входа (landing page form, popup, slide-in). Каждая form может авто-добавлять tag.

Skill в output указывает только Tag rule (например, Send to: tag = marathon-attendee-may-2026). Сегмент создаётся вручную в Kit UI. Skill не глубится в advanced Visual Automations.

## CTA в Kit Broadcasts

Plain-text bias диктует CTA-формат. Что работает в Kit:

- **Plain link anchor** - markdown-style anchor или pure URL. Default для skill.
- **Image button** через image upload + linking. Используется редко, только если ученик хочет визуальный CTA. Skill не выдаёт по умолчанию.
- **P.S. с линком** - отдельная строка после подписи. Часто single-CTA emails имеют 2 placement: один в теле + один в P.S.

Для sales-letter режима (close-cart, launch broadcast), 3-5 link placements: above-fold (после первого хука), после value stack, после social proof, перед guarantee, в P.S.

Для nurture / single-value email, 1 link placement в теле или только в P.S.

## Deliverability в Kit

Kit имеет хорошую baseline deliverability, но требует setup от ученика.

- **Authentication** (SPF / DKIM / DMARC) auto-handled при custom domain setup в Kit settings. Ученик подтверждает domain через DNS records. Без этого письма попадают в Promotions / Spam Gmail.
- **Engagement filtering** - Kit auto-suppress подписчиков, которые не открыли ни одного письма за 60 дней (опционально, включается в Settings). Помогает sender reputation.
- **Plain-text default** - обходит большинство spam filters, которые триггерятся на heavy HTML / inline CSS / 5+ image attachments.

Skill в output не лезет в deliverability setup. Это вопрос onboarding Kit ученика (вне scope email skill v1).

## Kit limitations для email skill

Что Kit НЕ умеет хорошо, и где Beehiiv лучше:

- **No native HTML block editor** - нет drag-drop block builder. Если ученик хочет visual newsletter с image hero / image grid / button blocks, Beehiiv лучше.
- **Sequence trigger conditions limited** - простые conditions (tag added / form submitted / link clicked). Нет complex multi-step branching без Visual Automations.
- **Reporting basic** - open rate, click rate, unsubscribe. Нет heatmap, нет cohort analysis. Достаточно для most cases.

Если ученик упирается в эти ограничения, skill предлагает switch на Beehiiv (см. `references/beehiiv-format.md`).

## Output format для Kit broadcast

Что email skill выдаёт в финальном артефакте под Kit. Структура output:

```
SUBJECT A: вариант A, ≤50 chars best
SUBJECT B: вариант B, ≤50 chars best
(если Newsletter / Creator tier, только Variant A)

PREHEADER: 50-100 chars, дополняет Subject, не дублирует

TAG RULE: send to: tag = ... / segment = ... / all subscribers

SCHEDULE: дата / время UTC или сразу после approve

BODY:
plain text с markdown-style разметкой
paragraph 1 hook

paragraph 2 proof / story

paragraph 3 value / promise

paragraph 4 CTA + link

С уважением,
автор

P.S. блок с дополнительным CTA или urgency
```

Skill output полностью готов к копи-паст в Kit Broadcast composer (Plain Text mode).

## Output format для Kit Sequence

Sequence это серия из N писем. Каждое письмо имеет ту же структуру, но + delay перед отправкой.

```
SEQUENCE NAME: название серии, e.g. Welcome series - vibemarketing club

EMAIL 1 - Delay: immediate (0 min after trigger)
SUBJECT / PREHEADER / BODY как выше

EMAIL 2 - Delay: 1 day
...

EMAIL 3 - Delay: 3 days
...
```

Для launch-sequence режим, обычно 7-14 писем с delay 1-2 дня между.

## Anti-patterns в Kit

Что НЕ делать в Kit broadcast / sequence:

- **HTML-heavy templates** ломают plain-text flow, режут deliverability, ломают mobile render. Если визуал нужен, лучше Beehiiv.
- **Empty preheader** Kit auto-pulls первые 100 chars body, обычно дублирует Subject, killing open rate
- **4+ links в short broadcast** overload, dilution внимания, выглядит как promo / spam. Cap: 1 link в nurture, 3-5 в sales-letter.
- **Image-only above-fold** если Gmail / Outlook блокирует images по умолчанию, подписчик видит пустоту. Always text-first.
- **Generic merge tags без fallback** Hi first_name без fallback показывает Hi запятая если first_name пустой. Always use default fallback друг.
- **Subject в ALL CAPS** триггерит spam filters, выглядит как promo. Lowercase / Title Case OK.
- **Multiple unsubscribe links в body** Kit auto-добавляет footer unsubscribe. Дополнительные в body излишни.

## Cross-references

- Альтернативный ESP `references/beehiiv-format.md`
- Subject формулы `references/subject-formulas-50.md`
- Voice bridge `references/voice-bridge-to-tg.md`
- Workflow output `workflow/04-review.md` + `workflow/05-publish.md`
- Templates под Kit `templates/nurture-letter.md`, `templates/launch-sequence-email.md`, `templates/sales-letter.md`
