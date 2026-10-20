# Reference - POSSE Distribution

> POSSE = Publish (on your) Own Site, Syndicate Elsewhere. Канонический URL на своём блоге, cross-post везде с rel="canonical". Loaded в `05-publish.md` Step 4-6.

## Что такое POSSE

Принцип IndieWeb 2015. Канонический контент живёт на сайте автора (под его контролем). Cross-posted версии на platform'ах с явной ссылкой на canonical (rel="canonical" header или meta tag).

**Преимущества:**
- Google индексирует canonical, не cross-post → SEO authority на свой сайт
- Если platform закроется (Substack / Medium) - контент не пропадает
- Платформы дают reach + discovery, но не контролируют контент
- Email list и paid subscribers - на своих rails (Kit/Beehiiv), а не у Substack

## Канонический поток

```
1. Опубликовать на BLOG (canonical URL)
   ↓
2. Send NEWSLETTER (Kit/Beehiiv) с link на canonical
   ↓
3. Cross-post LINKEDIN article (24-72 ч после canonical)
   rel="canonical" → blog
   ↓
4. Cross-post SUBSTACK (если есть)
   rel="canonical" → blog
   ↓
5. Cross-post MEDIUM (если есть)
   rel="canonical" → blog
   ↓
6. Derivatives:
   - X-thread summary (paips-post)
   - LinkedIn carousel (visual-concept-square)
   - 2-4 TG-posts (post)
   - 5-7 spiky-one-liners
   - YouTube long-form (если применимо)
   - Shorts cuts (если есть видео)
```

## Timing

| Step | Когда | Зачем |
|---|---|---|
| 1. Publish blog | T = 0 | Canonical first для Google crawl |
| 2. Send newsletter | T = 0 to T+2h | Newsletter == sync with blog publish |
| 3. LinkedIn article | T+24-72h | Даёт Google indexing time на canonical |
| 4-5. Substack/Medium | T+24-72h | То же, что LinkedIn |
| 6. Derivatives | T+1 day to T+7 days | Размазать по неделе для каждого канала |

## rel="canonical" - как ставить

### LinkedIn

LinkedIn editor поддерживает «Settings → Canonical URL» в article setup. Заполнить полным URL canonical.

Если поле не доступно - manual mention в первой строке: «Originally published at: <url>».

### Substack

Substack editor → Settings (gear icon) → Canonical URL. Заполнить URL.

### Medium

Medium editor → ... (3 dots) → Edit story → Advanced → Canonical URL. Заполнить URL.

### Beehiiv (если cross-post)

Beehiiv не имеет нативной canonical setting. Manual `<link rel="canonical">` в head через custom HTML block.

### Kit (если cross-post)

Kit не нужен canonical (это email-only delivery, не web). Если есть Kit landing page для post - manual canonical в Kit editor HTML.

## Cross-post versions - что менять

Минимально менять, потому что canonical = source of truth.

**Меняем:**
- LinkedIn - headline (LinkedIn-friendly 90-110 chars вместо blog SEO H1)
- LinkedIn - line breaks частые (mobile reader)
- Newsletter - добавить subject + preheader
- Substack/Medium - format conversion (markdown → их native editor)

**НЕ меняем:**
- Main_aha
- Structure (3-section)
- Examples / numbers
- CTA (можно адаптировать link target, но same intent)

## Derivatives plan - расшифровка

Каждый pillar longform → 6-12 derivatives. Не запускать автоматически, а планировать в `05-publish.md` Step 6.

| Derivative | Skill | Source из longform |
|---|---|---|
| X-thread summary (PAIPS) | `paips-post` | main_aha + 1 example + CTA |
| LinkedIn carousel (5-8 slides) | `visual-concept-square` | 3-section outline = slides outline |
| TG-posts (2-4) | `post` | personal_anchor + один example + один process step |
| Spiky-one-liners (5-7) | `spiky-one-liner` | counter-intuitive claims из INSIGHT |
| YouTube long-form script | manual | весь outline (если type=teaching/framework) |
| Shorts cuts (5-7) | `cut-from-long-form` | если есть видео-версия |
| Single-image post (1-3) | `single-image` | framework component diagram (для framework type) |
| Email follow-up (1-2) | `email` | повтор newsletter с deeper CTA через 5-7 дней |

## Hreflang для bilingual

Если `bilingual_mode = mirror`:

```html
<link rel="alternate" hreflang="ru" href="<blog>/blog/ru/<slug>" />
<link rel="alternate" hreflang="en" href="<blog>/blog/en/<slug>" />
<link rel="alternate" hreflang="x-default" href="<blog>/blog/en/<slug>" />
```

Google ранжирует по language preference читателя.

Если `bilingual_mode = ru_canonical`:
- RU = canonical, имеет canonical URL
- EN translation = cross-post с rel="canonical" → RU
- Альтернатива: published на отдельном /en/ subpath с hreflang ↔ canonical

## Memory cross-refs

- - POSSE как часть 12-promp acquisition
- - переработка / cross-distribution
- - derivatives как same-format reproduction
- - один сайт для всего, не Telegraph / Notion