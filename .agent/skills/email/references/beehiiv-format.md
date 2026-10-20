---
name: beehiiv-format
description: Beehiiv - opt-in alternative ESP для email skill. HTML blocks editor, web archive, ad network monetization, premium tier paywall. Когда использовать Beehiiv вместо Kit, формат вывода для Beehiiv post, anti-patterns. Используется в `workflow/03-write.md` Pass 1 и в `templates/*.md` если config.esp = beehiiv.
version: 1.0.0
last_updated: 2026-05-28
---

# Beehiiv format - opt-in alternative ESP

Beehiiv - opt-in alternative ESP для email skill. Подходит когда нужен visual newsletter (HTML blocks), web archive (SEO + cross-distribution), ad network monetization или premium tier с подпиской. автор по умолчанию на Kit (см. `references/kit-format.md`), но email skill поддерживает Beehiiv для учеников и для длинных newsletter (см. также `[[longform]]` skill).

Документ описывает Beehiiv positioning, post types, HTML blocks editor, output format и anti-patterns.

## Beehiiv vs Kit positioning

Когда выбирать Beehiiv, когда Kit.

- **Beehiiv лучше для:** visual newsletters с image hero + image grid + button blocks, sponsorship monetization через встроенный ad network, web archive каждого поста (SEO + POSSE cross-distribution), премиум-тиры с подпиской (paywall на специальные посты), длинные newsletter (800-3000 слов).
- **Kit лучше для:** plain-text personal emails, course / membership launches с tag-based automations, простые sequences, broadcast в существующую базу с поведенческими сегментами.

Email skill v1 default = Kit. Beehiiv включается через `config.esp = beehiiv` в `config.md` ученика.

## Beehiiv post types

Beehiiv имеет 3 типа контента:

- **Post** - single broadcast, аналог Kit Broadcast. Использовать для: nurture newsletter (weekly digest, weekly story), announcement, sales-letter, sponsorship-funded posts.
- **Series** - drip series, аналог Kit Sequence. Использовать для: welcome series, onboarding sequence, paid course delivery (если monetize через premium tier).
- **Premium-only posts** - gated by paid subscription. Beehiiv имеет встроенный paywall: подписка $X/мес откроет доступ. Использовать для: paid newsletter tier, paid case studies, paid templates / playbooks.

Email skill v1 покрывает Post (default) и Series. Premium-only - flag в output (`premium_gated: true`).

## HTML blocks editor

Beehiiv главное отличие от Kit - drag-drop HTML block editor. Доступные блоки:

- **Heading** (h1, h2, h3)
- **Paragraph** (rich text с inline formatting)
- **Button** (CTA с link, цвет, размер кастомизируется)
- **Image** (single image, optional caption + alt text)
- **Divider** (horizontal rule)
- **Embed** (Tweet, YouTube, Vimeo, custom iframe)
- **Code block** (для технических newsletter)
- **Table** (для comparison / pricing tables)
- **Quote** (blockquote с auto-styling)

Mobile responsive по умолчанию - lazy-loaded images, adaptive typography. Email skill использует block markers в output (HERO / H1 / PARAGRAPH / BUTTON / IMAGE / DIVIDER / etc.) - ученик копи-пастит, собирает blocks вручную в Beehiiv editor.

## Subject + preheader в Beehiiv

Beehiiv использует поля Title и Subtitle.

- **Title field** = Subject line, отправляется в inbox. Best practice ≤50 chars. Max 100 chars технически.
- **Subtitle field** = Preheader / Preview text. Beehiiv НЕ auto-pulls из body (в отличие от Kit). Если subtitle пустой, в inbox preview показывается пустота. Always fill.
- **A/B test** - через separate composer view (Beehiiv добавил A/B Subject testing в 2024-2025). Конфиг: split %, wait time, winner metric (opens / clicks).

Email skill выдаёт Title (Subject A + B) и Subtitle (Preheader) как обязательные поля.

## Body структура в Beehiiv

Типичная структура Beehiiv newsletter post.

- **Hero image** (optional) - full-width image сверху, задаёт визуальный тон. Часто бренд-картинка или иллюстрация темы поста.
- **Header (h1)** - главный headline поста (отличается от Title - Title в inbox, h1 в web archive и при открытии email).
- **Sections** (h2, paragraphs, image blocks) - основное тело, разбито на логические секции с h2-заголовками.
- **Button blocks** - primary visual CTA. Размещаются strategically (см. ниже).
- **Footer** - auto-generated Beehiiv (unsubscribe, branding, ad placement если включён ad network).

## CTA в Beehiiv

Два варианта CTA в Beehiiv:

- **Button block** - primary visual CTA. Bright color, prominent, тяжело пропустить. Default для broadcast / sales-letter.
- **Hyperlink text inside paragraph** - inline link, subtle. Для secondary CTA или для multi-link nurture.

Для sales-letter режим - 2-3 button blocks placed strategically: above-fold (после хука), после value stack, после social proof или перед guarantee, в P.S.

Для nurture - 1 button block в конце основного блока + опционально 1 inline link.

## Segments в Beehiiv

Beehiiv имеет более простой сегментинг чем Kit (нет tag-based system).

- **Free** segment - все free подписчики
- **Premium** segment - paying subscribers (если включён premium tier)
- **Custom segments** - saved filters по signup date, engagement level, custom fields

Email skill в output указывает segment targeting (например, `Send to: Free + Premium` или `Send to: Premium only`).

## Web archive view

Beehiiv ключевая фича: каждое письмо это публичная web page по умолчанию.

- Каждое письмо имеет permalink URL - можно отключить per-post (toggle Public / Private).
- Хорошо для SEO - поисковая индексация newsletter постов, органический traffic в lead magnet.
- POSSE-friendly - single source of truth, cross-distribute web URL в TG / X / LinkedIn / Threads / RSS.
- Подходит для longform content - `[[longform]]` skill часто публикует в Beehiiv именно из-за web archive.

Email skill в output указывает `web_archive: public / private` (default public).

## Beehiiv ad network

Beehiiv премиум tier даёт доступ к встроенному ad network - Beehiiv продаёт sponsorships, авто-вставляет ad placements в твои posts, ты получаешь revenue share.

- Подходит для newsletter с 5К+ подписчиков и regular publishing schedule.
- НЕ рекомендуется для автора v1 - focus на funnel conversion (club / high-ticket), не на ad revenue. Дистракция.
- Skill не выдаёт ad placement hints в v1.

## Output format для Beehiiv post

Что email skill выдаёт под Beehiiv. Структура output:

```
TITLE A: вариант A, ≤50 chars best
TITLE B: вариант B, ≤50 chars best

SUBTITLE: 50-100 chars, дополняет Title, не дублирует

SEGMENT: Free + Premium / Premium only / Custom segment name

PREMIUM GATED: true / false

WEB ARCHIVE: public / private

SCHEDULE: дата / время UTC или сразу после approve

BODY (block-by-block):

[HERO IMAGE]: optional, описание / alt text / source URL

[H1]: главный headline поста

[PARAGRAPH]: первый параграф, hook

[BUTTON]: текст кнопки / link / placement note above-fold

[H2]: section heading 1

[PARAGRAPH]: section 1 body

[IMAGE]: optional, alt text + source

[H2]: section heading 2

[PARAGRAPH]: section 2 body

[QUOTE]: optional blockquote для social proof

[BUTTON]: текст кнопки / link / placement note bottom

[PARAGRAPH]: P.S. блок (inline link или дополнительный context)
```

Skill output это блок-по-блок инструкция. Ученик собирает blocks вручную в Beehiiv editor (copy text + image URL + button settings).

## Beehiiv vs Kit comparison table

Краткая таблица для решения какой ESP использовать:

| Критерий | Kit | Beehiiv |
| --- | --- | --- |
| Plain-text bias | yes | no (HTML blocks default) |
| HTML block editor | no | yes |
| Tag-based automations | yes | no (только segments) |
| Web archive каждого письма | no | yes (default public) |
| Premium tier paywall | no | yes |
| Ad network monetization | no | yes |
| A/B Subject testing | Creator Pro only | yes (newer feature) |
| Лучше для | course launches, sequences | newsletter, longform, monetize |

## Anti-patterns в Beehiiv

Что НЕ делать в Beehiiv post:

- **Pure plain-text в Beehiiv** упущенный potential HTML blocks. Если plain text нужен, использовать Kit.
- **Forgetting Subtitle** Beehiiv не auto-pulls subtitle из body. Пустой = пустой preview в inbox.
- **Too many button blocks** 4+ button blocks в один post = overload, dilution. Cap: 1 в nurture, 2-3 в sales-letter.
- **Hero image без alt text** broken accessibility + если image не грузится подписчик видит пустоту с broken icon.
- **Public archive для private content** premium-gated content должен иметь `web_archive: private`, иначе bypassing paywall через permalink URL.
- **Embed-heavy posts** 5+ embeds (Tweets / YouTube / iframes) ломают mobile render и грузятся медленно.
- **Generic Title без emotional hook** Beehiiv subject visible в inbox = first-impression. Generic = ignored.

## Cross-references

- Primary ESP `references/kit-format.md`
- Subject формулы `references/subject-formulas-50.md`
- Voice bridge `references/voice-bridge-to-tg.md`
- Longform skill (часто публикует в Beehiiv) `~/.claude/skills/longform/SKILL.md`
- Workflow output `workflow/04-review.md` + `workflow/05-publish.md`
- Templates под Beehiiv `templates/nurture-letter.md`, `templates/launch-sequence-email.md`, `templates/sales-letter.md`
