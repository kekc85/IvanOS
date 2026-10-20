# Banned AI Imagery - 12-item checklist

Consolidated list anti-patterns из bucket-a (EN AI/vibemarketing 11 авторов), bucket-b (LinkedIn 12 masters consensus), bucket-c (RU 10 авторов verified), bucket-d (panorama anti-patterns).

Используй для `workflow/04-review.md` CR-G5 (Banned AI imagery scan). Любое попадание = auto-fail или warning.

---

## Как использовать

1. Прочитай каждый `visual_brief.composition` + `real_elements` + `text_overlay` всех slides carousel.
2. Match против 12 patterns ниже.
3. Для каждого попадания:
   - Если severity = **auto-fail** → return на переписать brief
   - Если severity = **warning** → flag в review report, но не блокирует output
4. Edge cases (раздел 13) - случаи когда AI illustration ОК.

---

## 1. Generic AI-illustrated люди в офисах

**Severity:** auto-fail

**Что это:** Midjourney / DALL-E / Stable Diffusion стилизованные люди в офисной обстановке. Идеальные «diverse team» с симметричными лицами, в pristine workspace.

**Markers:**
- `composition` упоминает «professional team», «business meeting», «office collaboration»
- `composition` описывает «diverse group at laptop»
- AI-generated люди без явного контекста (не реальный сотрудник, не реальная конференция)
- Стилизованные corporate avatars

**Bad example:** «Midjourney generated image of 4 diverse professionals around a glossy laptop, modern office bokeh background»

**Good replacement:** Реальная фотография автора (автор face shot) ИЛИ screenshot Skool community page с реальными аватарами учеников ИЛИ photo с live эфира.

**Detection:** Brief упоминает любое из `team / meeting / collaboration / office / professionals` + «AI-generated» или «illustrated» → flag.

**Источник:** bucket-a Top 3 banned (никто из 11 топ AI creators это не делает), bucket-b consensus (all 12 LinkedIn masters avoid).

---

## 2. Gradient blob backgrounds + 3D abstract shapes

**Severity:** auto-fail

**Что это:** Templated carousel design в стиле PostNitro / aiCarousels - soft purple-to-pink gradient backgrounds с floating 3D geometric shapes (sphere / cube / torus).

**Markers:**
- `composition` или `color_palette` упоминает `gradient blob`, `gradient background`, `3D shapes`, `floating geometry`
- `composition` описывает «dynamic abstract background»
- Multiple soft pastel gradients (purple → pink, blue → cyan)

**Bad example:** «Bold modern hook slide with dynamic gradient background and floating 3D crystals in pink-purple palette»

**Good replacement:**
- Plain solid color (off-white #FAFAFA или Ivan brand)
- Real screenshot full-bleed
- Bold typography on flat background (Welsh / Alić стиль)

**Detection:** Brief содержит `gradient` + `(blob | background | abstract | shape)` → flag. Также `3D render`, `octane`, `cinema4d` без specific reason.

**Источник:** bucket-a top 3 banned (top-tier creators используют либо flat color + typography, либо real screenshot, либо meme screenshots), bucket-b 12-item consensus.

---

## 3. Robot hands typing / brain with circuits

**Severity:** auto-fail

**Что это:** Главный AI cliché. Иллюстрация роботизированной руки печатающей на keyboard, человеческого мозга с электронными платами, AI «brain» с нейронными connections.

**Markers:**
- `composition` упоминает `robot hand`, `robotic arm`, `brain circuits`, `neural network visualization`
- `composition` описывает `AI hand on keyboard`, `cyborg fingers`, `mechanical limb`

**Bad example:** «Robotic hand типing on a laptop with neural network glow effects, representing AI assistance»

**Good replacement:**
- Screenshot real Cursor IDE с verbatim промптом
- Screenshot Claude conversation
- Face photo автора за компьютером (реальная)

**Detection:** Brief содержит `robot | robotic | cyborg | neural network` визуализация → flag. Engagement drop 40-60% per creator data (bucket-a).

**Источник:** bucket-a (zero usage у всех 11 топ авторов), bucket-b consensus.

---

## 4. Stock photos «diverse team smiling at laptop»

**Severity:** auto-fail

**Что это:** Generic stock photography - люди в идеализированных позах вокруг laptop, handshakes, high-fives, «work from beach», «coffee + laptop» lifestyle.

**Markers:**
- `real_elements` ссылается на `stock photo`, `unsplash photo of team`
- `composition` описывает обобщённую офисную сцену без specific identity
- Pristine empty workspace без personal items

**Bad example:** «Stock photo team of 4 professionals smiling at MacBook with coffee cups, diversity composition»

**Good replacement:**
- Реальная фотография автора / ученика
- Screenshot Skool member roster (реальные люди)
- Screenshot переписки с учеником (с blur имён если приватность)

**Detection:** Brief содержит `stock photo`, `unsplash`, `getty images`, `lifestyle shot` + people → flag.

**Источник:** bucket-a 12-item banned consensus.

---

## 5. AI avatars вместо real photo автора

**Severity:** auto-fail (для carousel skill)

**Что это:** HeyGen / D-ID / synthesis generated portrait автора используется вместо настоящей фотографии. Может быть photoreal, но не аутентичная.

**Markers:**
- `real_elements` содержит `HeyGen avatar`, `AI avatar`, `synthesized portrait`
- `composition` описывает «AI rendition of [author]»

**Bad example:** «HeyGen avatar still of Ivan in studio setting, looking confident»

**Good replacement:** Реальная фотография автора (face-cam frame из Reel, studio shot, behind-the-scenes).

**Edge case (НЕ banned):** В talking-head video AI avatar ОК (skill `avatar-generate`). Но в static carousel = брак.

**Detection:** Brief содержит `AI avatar`, `HeyGen still`, `synthesized portrait` → flag. Для автора: photo bottom-right (Acosta pattern) - только реальная фотография.

**Источник:** bucket-a (все 11 топ-авторов используют реальные photos), bucket-c (RU авторы тоже все реальные).

---

## 6. Generic vector icons вместо real product logos

**Severity:** auto-fail

**Что это:** Flaticon / Noun Project / generic icon library symbols вместо verbatim product logos. Лампочка вместо идеи, шестерёнка вместо настроек, мишень вместо цели.

**Markers:**
- `real_elements` упоминает `lightbulb icon`, `gear icon`, `target icon`, `rocket icon` без specific brand
- `composition` использует Material icons / FontAwesome generics
- Tool referenced abstractly: «AI tool icon» вместо `Claude logo`

**Bad example:** «Row of 5 generic tool icons (lightbulb, gear, lightning, brain, chart) representing AI workflow»

**Good replacement:**
- Verbatim product logos (Claude / Lovable / Cursor / n8n / Stripe official marks)
- Screenshot самого tool вместо icon

**Detection:** Brief упоминает `icon` + generic concept (`idea / settings / goal / speed`) → flag. Если упоминается tool - должно быть verbatim brand logo или screenshot.

**Источник:** bucket-a (vector icons заменяются конкретными tool логотипами у всех топ-авторов), bucket-c (RU - real product names).

---

## 7. Soft pastel backgrounds без content

**Severity:** warning (ок для quote-card)

**Что это:** Pretty pastel background (mint / lavender / peach gradient) с минимальным content. «Aesthetic» подача без substance.

**Markers:**
- `color_palette` содержит multiple pastels
- `composition` минимальная: 1 цитата + decorative pastel BG
- `real_elements` пустой

**Bad example:** «Soft mint-to-lavender gradient background with single inspirational quote in script font»

**Good replacement (если quote-card):** flat brand color + bold typography (Welsh стиль).

**Good replacement (general):** добавить real_elements (screenshot, number, product name).

**Edge case:** Quote-card type в `single-image` skill допускает soft pastel если quote = real verbatim от автора. В carousel - чаще brak.

**Detection:** Brief содержит pastel palette + `real_elements` пустой → warning. Если 2+ slides подряд - escalate to fail.

**Источник:** bucket-a / bucket-d (top creators используют flat solid color + typography).

---

## 8. Fake / cropped dashboards

**Severity:** auto-fail (репутационный риск)

**Что это:** Подделанный screenshot dashboard - Stripe test mode помечен как production, browser dev tools edit числа, one-time payment labelled as recurring MRR.

**Markers:**
- `real_elements` упоминает `mockup dashboard`, `Figma dashboard mockup`, `designed dashboard`
- Dashboard screenshot с heavy filter / blur маскирующий details
- Numbers выглядят round / suspicious (`$100,000.00` exact)

**Bad example:** «Figma-designed Stripe-like dashboard mockup showing $100k MRR»

**Good replacement:**
- Реальный Stripe screenshot raw (mobile iPhone shot предпочтительнее - bucket-d)
- Если real numbers конфиденциальны - blur только конкретные fields, оставить раму UI authentic

**Critical:** Per Pieter Levels (bucket-d) - комьюнити детектит fake screenshots, репутационный damage очень высокий. Trust = всё.

**Detection:** Brief упоминает `mockup`, `designed`, `Figma`, `Sketch` + `dashboard` → flag. Round numbers `$100,000`, `$1M` без verification → flag.

**Источник:** bucket-d (Pieter Levels callout, Marc Lou TrustMRR launched specifically против этого).

---

## 9. Symbolic «expert» illustration generic

**Severity:** auto-fail

**Что это:** Стилизованная иллюстрация «эксперта» - figure в очках с указкой, человек на mountain peak, silhouette с лампочкой над головой.

**Markers:**
- `composition` упоминает `expert silhouette`, `figure with lightbulb`, `person on mountain`
- `real_elements` ссылается на иллюстрацию без specific identity

**Bad example:** «Silhouette of expert standing on mountain peak with sunrise, representing achievement»

**Good replacement:**
- Реальная фотография автора / ученика
- Screenshot Skool ученика с реальным результатом
- Цифра + dashboard вместо метафоры

**Detection:** Brief описывает abstract person без identity context → flag.

**Источник:** bucket-a top 12 banned.

---

## 10. AI charts без real numbers

**Severity:** auto-fail

**Что это:** Сгенерированный chart с поддельными данными - growth line без real data source, pie chart с round percentages не из real analytics.

**Markers:**
- `real_elements` упоминает `chart`, `graph`, `data visualization` без source
- Numbers на chart округлены до десятков / сотен подозрительно
- Нет ссылки на конкретный dashboard / period

**Bad example:** «Growth chart showing 10X increase over 6 months, modern data viz style»

**Good replacement:**
- Screenshot real Stripe / Plausible / IG Insights с native chart UI
- Screenshot specific период с verbatim datapoints
- Если cant share real - не делать chart вообще, использовать text + 1 цифра

**Detection:** Brief содержит `chart / graph / data viz` + нет ссылки на конкретный source (Stripe / Plausible / etc.) → flag.

**Источник:** bucket-a / bucket-d (real dashboards = trust signal, fake = brand damage).

---

## 11. Corporate buzzwords overlay

**Severity:** auto-fail

**Что это:** Text overlay с корпоративными buzzwords - «synergy», «leverage», «paradigm shift», «disruption», «innovation».

**Markers:**
- `text_overlay` содержит: `synergy`, `leverage` (в значении «использовать»), `paradigm`, `disruption`, `innovation` (без specific context), `seamless`, `cutting-edge`, `next-gen`, `transformative`
- RU equivalents: «синергия», «инновационный», «революционный», «прорыв года», «следующий уровень», «трансформация», «экосистема»

**Bad example:** «Headline overlay: 'Leverage AI synergy for innovative disruption'»

**Good replacement:** конкретный outcome + специфические числа. «Собрал 12 микро-SaaS за выходные» > «Innovative AI productivity boost».

**Detection:** Regex против banned word list:
- EN: `\b(synergy|leverage|paradigm|disruption|cutting-edge|next-gen|transformative|seamless)\b`
- RU: `\b(синерги|инновацион|революционн|прорыв год|следующий уровень|трансформац|экосистем)\b`

**Источник:** bucket-b 12 master consensus, автор memory `feedback_no_tech_jargon_no_anglicisms`.

---

## 12. Vector illustrations с американцами для RU аудитории

**Severity:** auto-fail (для RU subject)

**Что это:** Stock vector illustrations с типичными «американскими» персонажами (диверсная команда в business casual, white-collar setting) в материале для русской аудитории.

**Markers:**
- `composition` описывает диверсную команду персонажей в western office
- Vector illustration стиля Storyset / unDraw с US-coded персонажами
- Westernized lifestyle context (kitchen islands, Tesla, открытое open-space)

**Bad example:** «unDraw vector illustration of diverse team brainstorming around whiteboard in modern open office»

**Good replacement (RU subject):**
- Реальные фотографии русских учеников (с разрешения)
- Screenshot Telegram переписки на русском
- Screenshot Skool channel на русском
- Photo рабочего стола автора (хрущёвка-detail level - Афонина pattern, bucket-c)

**Detection:** Brief содержит `vector illustration` + diverse / team / office + subject = RU → flag.

**Источник:** bucket-c RU edition banned patterns (raw flag - не используется ни одним из 10 RU топ-авторов).

---

## 13. Edge cases - когда AI illustration ОК

Не всё AI-generated visual = брак. Три legitimate use cases.

### 13.1 AI gen как demonstration (Heather Cooper exception, bucket-a)

Если carousel = `tool roundup` про AI image gen (Midjourney / Runway / Kling) - сам AI-generated output ОК потому что это **demonstration**, а не decoration.

Verbatim allow:
- Slide показывает prompt + actual Midjourney output (input-output pair)
- Slide показывает Kling-generated video frame с captioning «созданно через Kling AI»
- Slide показывает Runway 4-frame storyboard как demo

Запрет: AI gen без указания tool + промпта (тогда это decoration, fail).

### 13.2 Stylized brand mascot документированный в config

Если в `config.md` brand mascot документирован (например условный логотип автора или брендовый персонаж) - использование ОК.

Условие: mascot прописан в `config.md` раздел `brand_visual_identity` + используется consistently across carousels (recognition signal).

### 13.3 Abstract texture / brand background subtle

Очень subtle abstract texture как brand background (например paper texture, subtle noise) - ОК если:
- Не доминирует композиционно (<5% visual weight)
- Не имитирует banned patterns (не gradient blob)
- Не несёт semantic load («что-то про AI»)

---

## 14. RU-specific banned extensions (bucket-c)

Дополнительные patterns которые особенно «AI-фальшиво» в RU контенте.

### 14.1 Англицизмы-формализмы в slide overlay

Запрещены в text_overlay:
- `функционал` (заменять «возможности» или конкретикой)
- `pipeline` (заменять «процесс» или конкретикой)
- `scope` (заменять «границы» / «зона»)
- `retention` (заменять «удержание» / «возврат»)
- `engagement` (заменять «отклик» / «реакции»)
- `workflow` (заменять «последовательность» / «как работаю»)
- `framework` (заменять «методология» / «подход» / «структура»)
- `onboarding` (заменять «введение» / «первые шаги»)
- `artifact` (заменять «материал» / «документ» / «файл»)

**Detection:** regex check всех `text_overlay` против banned list.

### 14.2 Патерналистские обращения

Запрещены: `Друзья!`, `Дорогие подписчики!`, `Уважаемые читатели!`, `Дамы и господа!`.

Source: bucket-c Халилов signature (clone-risk).

Замена: прямое обращение «ты» / «вы» / именно конкретная роль («те, кто...»).

### 14.3 CAPSLOCK длиннее 3 слов

CAPS короткие (1-3 слова) ОК для emphasis. CAPS целые фразы = AI default или Халилов clone.

**Detection:** regex `\b[А-ЯA-Z]{4,}(?: [А-ЯA-Z]{4,}){2,}` (3+ слов подряд в CAPS).

### 14.4 Generic emoji-flood headers

Запрещено: `🚀✨💡⚡🔥` spray в hook.

Разрешено: targeted single-emoji branding (Sabrina mushroom 🍄, у автора может быть один signature emoji).

### 14.5 Round numbers в hook

Запрещены: `10X`, `100`, `1000` (округлённые до круглых, AI-default).

Замена: специфические `12 / 47 / 125 / 940 000` (автор-track numbers).

---

## 15. Detection workflow summary

В `04-review.md` CR-G5 для каждого slide:

```
for slide in carousel.slides:
    composition = slide.visual_brief.composition
    overlay = slide.visual_brief.text_overlay
    elements = slide.visual_brief.real_elements
    palette = slide.visual_brief.color_palette

    for pattern in 12_banned + RU_extensions:
        if pattern.detect(composition, overlay, elements, palette):
            if pattern.severity == "auto-fail":
                FAIL slide
            else:
                WARN slide

    if slide.failed:
        return on rewrite brief
```

Если carousel содержит ≥1 auto-fail slide - весь carousel return на переписать.
Если только warnings - output продолжается, но flag в review report для автора.

---

## 16. Cross-references

- `visual-brief-real-first.md` - 6-field schema и real_elements taxonomy
- `carousel-anatomy.md` - hook formulas и slide roles
- `caption-formulas.md` - caption rules (текстовые banned patterns)
- `~/.claude/skills/single-image/knowledge/anti-patterns.md` - parent-level anti-patterns

Memory cross-refs:
- `[[feedback-no-generic-ai-artifacts]]` - generic AI = брак (Sophistication 4-5 видела всё)
- `[[feedback-images-from-icp-world]]` - образы из мира аватара, не из AI/кода
- `[[feedback-no-tech-jargon-no-anglicisms]]` - запрет англицизмов
- `[[feedback-real-ui-not-abstract-blocks]]` - настоящие UI screenshots, не abstract