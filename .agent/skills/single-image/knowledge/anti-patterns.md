# Anti-patterns для single-image

Что НЕ делать. Detection rules для 05-review.md и общий guard против generic / stock / brand-damaging output.

---

## Generic AI aesthetics (top priority)

Самая опасная категория. AI image generators по-умолчанию выдают визуальные tells, которые audience уже adapted ignore.

**Visible markers:**
- Soft pastel gradients (purple → pink, blue → cyan)
- Glossy 3D objects (rendered isometric shapes на neutral bg)
- Bokeh / depth-of-field как decorative effect
- Symmetric centered face composition
- Бессмысленные абстрактные shapes (geometry без semantic load)
- «Tech aesthetic» (neon grids / cyberpunk / hologram)
- Hyper-clean studio lighting на ALL products
- Default Midjourney style (oversaturated dramatic)
- «Hero shot» с low angle camera (cliché)

**Detection в review:**
- Brief описывает «modern», «sleek», «dynamic», «vibrant» как primary attribute → flag
- Tool prompt включает «cinematic lighting», «depth of field», «3D render» без specific reason → flag
- Brief не упоминает identity якорь (специфика автора / niche / unique element) → flag

**Counter (что делать):**
- Specific human imperfections (hand-drawn marks / asymmetric placement / unexpected color)
- Real photography / screenshots вместо AI gen где можно
- Identity element обязательно (Ivan's palette / type family / signature element)

---

## Stock photo маскировка

Stock photos сигнал что у автора нет своей идеи / ресурсов.

**Markers:**
- People с обобщёнными офисными позами
- «Diversity stock photo» composition (4 people разных etnos смеются у laptop)
- Pristine empty workspace
- Tech objects на белом фоне без context
- Handshakes / high-fives
- Generic city skylines
- Lifestyle стоковые «work from beach» / «coffee + laptop»

**Detection:**
- Brief описывает «professional team», «modern workspace», «business meeting» → flag
- Нет specific identity context

**Counter:** Real photos, real screenshots, real products. Если нет ресурсов - переключись на type где они не нужны (concept-diagram, quote-card).

---

## Cluttered (8+ elements)

**Markers:**
- >7 distinct visual elements в одной композиции
- Множественные text blocks без clear hierarchy
- Decorative icons вокруг main content
- Borders / frames вокруг каждого element
- Multiple arrows pointing разные directions

**Detection:**
- Brief перечисляет 8+ named elements
- Composition section >150 слов описания

**Counter:** Один primary + 2-3 supporting max. Убрать всё что не critical.

---

## Color chaos (5+ colors)

**Markers:**
- 5+ distinct hue families в композиции
- Rainbow palette
- Multiple bright accents
- High saturation everywhere

**Detection:**
- Palette в brief lists 5+ colors

**Counter:** 60-30-10 правило строго. Один accent.

---

## Шрифт-каша (3+ typeface families)

**Markers:**
- Display + body + accent serif + script + mono в одной композиции

**Detection:**
- Typography section в brief lists 3+ families

**Counter:** Max 2 typeface families. Hierarchy через size + weight + color.

---

## Низкий контраст

**Markers:**
- Light grey text on white bg (contrast <3:1)
- Pastel pairs (mint on lavender)
- White text on light photo bg без shadow / overlay

**Detection:**
- Hex pairs в brief дают contrast <4.5:1

**Counter:** webaim.org check. Минимум 7:1 для body, 4.5:1 для headline.

---

## Text-heavy image

**Markers:**
- >50 слов на картинке (тогда лучше longform post)
- >5 lines of text
- Long paragraphs визуализированные как картинка

**Detection:**
- Verbatim text on image >50 слов

**Counter:** Картинка - не essay. >50 слов = переключись на type quote-card (max 25 слов) или вынеси текст в caption.

---

## Decorative emojis / icons без смысла

**Markers:**
- Emojis в text overlay просто для «decorative» (🚀✨💡)
- Generic icons (lightbulb / rocket / target) без specific function
- Icon decoration на каждом element

**Detection:**
- Brief mentions emojis в image text
- Icons без semantic role

**Counter:** Каждый visual element должен нести смысл. Если убираешь и ничего не меняется - убери.

---

## Выдуманные numbers (dashboard-screenshot)

Самая опасная категория для credibility.

**Markers:**
- «$50K MRR» без verification
- «10K subscribers» если факт не подтверждён
- Round numbers slightly inflated
- Projections как fact

**Detection:**
- type=dashboard-screenshot AND number не в `.business/` AND not explicit user-provided
- «on track to», «expecting», «soon will hit» framing

**Counter:** ТОЛЬКО verified numbers. Если нет - переключись на другой type или отложи пост.

---

## Negative статистики в публичном

**Markers (RU):**
- «20% доходят»
- «только 20%»
- «большинство не справится»
- «90% делают X неправильно»

**Markers (EN):**
- «only 20% reach goal»
- «most people fail at X»
- «90% don't make it»

**Detection:** Regex по этим patterns в caption.

**Counter:** Public = positive framing. Negative статистики OK только в private analyses.

---

## Hyperbolic captions / image text

**Markers:**
- «life-changing»
- «mind-blown»
- «10x results»
- «game-changer»
- «incredible»
- «amazing»
- «жизнь изменилась»
- «взрыв мозга»

**Detection:** Regex по этим словам.

**Counter:** Specific concrete claim. «$132K MRR» beats «amazing growth». «3 hour build» beats «life-changing speed».

---

## Имена конкурентов в visual или caption

**Markers:**
- Specific competitor product names с negative framing
- «X is dead, here's why Y wins» где X = real competitor
- Logos конкурентов

**Detection:** Regex по known competitor names из `.business/marketing/competitors.md`.

**Counter:** Враг = явление (см. `[[feedback-no-attacking-competitors-by-name]]`). «Курсомания» вместо имени.

---

## Hyped buzzwords (text on image)

**Markers:**
- «AI» в одиночку без контекста
- «hustle» / «grind» / «10x» / «next level» 
- «синергия» / «парадигма» / «прорыв» / «революция»
- «game-changing» / «disruptive»

**Detection:** Regex.

**Counter:** Specific concrete language. «3-line Python script» beats «AI revolution».

---

## Inside jokes без universality (meme type)

**Markers:**
- Niche-specific reference которое только tech Twitter знает
- В RU - reference на местные мемы которые EN audience не считает (для bilingual)
- Jokes про specific people которых audience не знает

**Detection:**
- Brief описывает meme template, который не входит в top-100 mainstream meme database
- Reference требует knowledge ниже общедоступного

**Counter:** Test «mom test» - моя мама понимает основу шутки? Если совсем niche - не подходит для broad post. Использовать только если target audience точно знает.

---

## Misleading visual comparisons (before-after)

**Markers:**
- Different angles / lighting / scales между before vs after
- Fake polish в after
- Exaggerated improvement

**Detection:**
- Brief описывает «dramatic transformation» без specific concrete delta

**Counter:** Honest comparison. Same angle / lighting / scale. Если разница не dramatic - не приводи в before-after type.

---

## Misattributed quotes (quote-card type)

**Markers:**
- Famous quote без verified attribution
- Quote attributed Einstein / Mark Twain / Churchill (most misattributed)
- Quote без source citation

**Detection:**
- Brief attributes quote without verifiable source

**Counter:** Verify через quotation database (quoteinvestigator.com / wikiquote.org) перед использованием. Если не verified - либо найди real source, либо отметь «anonymous» / use твой собственный quote.

---

## Drop shadows / outdated effects

**Markers:**
- Drop shadows on text
- Bevel / emboss
- Stroke / outline на text без functional reason
- Glow effects
- Old-school 3D button styles

**Detection:**
- Brief mentions «shadow», «glow», «3D» как style attribute

**Counter:** Flat design (current >=10 years standard). Hierarchy через other means.

---

## Stale meme formats (>12 мес)

**Markers:**
- Templates которые были peak >12 мес назад без revival
- «Doge» (peak 2013-2014)
- «Forever Alone» (peak 2010-2011)
- Specific outdated reaction images

**Detection:**
- Brief uses meme template that doesn't appear в last 3 мес trending databases

**Counter:** Check knowyourmeme.com trending / current. Use templates which are <12 мес since peak relevance.

---

## Caption дублирует image text

**Markers:**
- Image text: «Stop using AI for content»
- Caption: «Don't use AI for your content - here's why»

**Detection:** Word overlap caption vs image text >60%.

**Counter:** Image carries 80% смысла. Caption даёт context / setup / CTA, не повторяет.

---

## Меры в review

В `05-review.md` каждый из выше категорий имеет explicit check. Detection methods:
- Regex (для текстовых markers)
- Semantic check (LLM-judge для visual aesthetics)
- Verification queries (для facts / numbers / attributions)

PASS = none flagged. WARNING = 1-2 minor. FAIL = 1+ major (выдуманные numbers / generic AI / negative stats public).