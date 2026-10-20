# Reference - Maxwell Ross 9-Item Checklist (longform adaptation)

> Pre-publish gate в `04-review.md` Pass 3. 9 yes/no вопросов. Все 9 = PASS обязательно. Adapted для longform (более длинные параметры specificity / hook / length).

## Происхождение

Maxwell Ross - copywriter / content strategist. Опубликовал 9-item checklist в Saturday Solopreneur newsletter (Justin Welsh), позже скопирован в post skill v1.0. Здесь - longform adaptation.

## 9 вопросов

### 1. Idea - есть ли один центральный insight?

**Тест:** Может ли читатель сформулировать main_aha в одно предложение через час после прочтения?

**PASS критерии:**
- В INSIGHT секции явно declared main_aha (один)
- Все examples / reasons поддерживают этот один main_aha (не уводят на другие insights)
- В headline присутствует hint на main_aha

**FAIL примеры:**
- 2-3 «aha» insights одновременно (split на серию)
- main_aha = вариант существующего consensus (не свежий)
- main_aha = generic claim («content is important»)

### 2. Clarity - может ли читатель пересказать main_aha?

**Тест:** Прочитай первые 200 слов + последние 200 слов. Можешь сформулировать main_aha?

**PASS критерии:**
- main_aha явно проговорен (не подразумевается)
- Bridge между секциями ясный (читатель не теряется)
- Vocabulary доступен (jargon раскрыт)

**FAIL примеры:**
- Main_aha подразумевается, но не declared
- Терминология не объяснена («3M / AARRR / Core Four» без раскрытия)
- Bridge секциями = formulaic transition («А теперь самое интересное»)

### 3. Payoff - получает ли читатель ясный outcome shift?

**Тест:** После прочтения у читателя изменилось понимание / план действий / mental model?

**PASS критерии:**
- В INSIGHT - reframe («раньше я думал X, теперь Y»)
- В PROCESS - actionable next step (что делать сегодня / эта неделя)
- В closing - emotional или intellectual completion

**FAIL примеры:**
- Только теория без applicable next step
- Описательная статья без shift («вот как работает X» без «и значит это»)
- Closing зависает («продолжение в следующей статье...» без payoff в этой)

### 4. Specificity - есть ли конкретные числа / имена / кейсы?

**Тест:** В INSIGHT и PROCESS секциях ≥3 specific numbers / names / dates на 1000 слов.

**PASS критерии:**
- Каждый example с конкретным числом / именем / датой
- Vague claims («significantly», «много», «зачастую») = ≤2 per 1000 слов
- Personal anchor с конкретным моментом (дата / место / сцена)

**FAIL примеры:**
- «Однажды я заработал значительную сумму...»
- «Большинство экспертов используют X»
- «Многие из моих учеников добились результата»

### 5. Freshness - это новое или старое в новой обёртке?

**Тест:** Reference creator в твоей нише уже писал об этом? Если да - ты добавляешь что-то новое?

**PASS критерии:**
- Main_aha - counter-intuitive vs current consensus
- Frame / metaphor / angle - оригинальный
- Examples / personal anchor - твои, не заимствованные

**FAIL примеры:**
- Перепев Dan Koe / Justin Welsh без своего angle
- Common knowledge wrapped в personal moments
- Generic AI-flavored framework

### 6. Hook - открывающая строка цепляет за 3 секунды?

**Тест:** Прочитай только headline + первые 2 абзаца. За 3 секунды - скроллю или дальше?

**PASS критерии:**
- Headline соответствует hook patterns (см. `hook-patterns-longform.md`)
- Первая строка ≤12 слов
- Counter-intuitive claim, personal anchor, или specific outcome
- НЕ начинается с formulaic «В этой статье...» / «Сегодня расскажу...»

**FAIL примеры:**
- Generic intro «Привет! Сегодня поговорим о X»
- Длинная преамбула без hook
- Em-dash в headline

### 7. Length - соответствует target_length по platform?

**Тест:** Word count в пределах `platforms.<platform>.length_floor` - `length_ceiling`.

**PASS критерии:**
- Length в пределах platform spec
- Тип modifier применён (story essay < teaching < framework по target)
- Pacing соблюдён (INTRODUCTION / INSIGHT / PROCESS proportions)

**FAIL примеры:**
- Blog at 500 слов (под floor)
- LinkedIn article 2500 слов (>>> ceiling)
- INTRODUCTION = 60% length (over-extended)

### 8. Tone - voice автора, не generic AI?

**Тест:** Может ли читатель определить что это написано автором X, а не AI / другим creator?

**PASS критерии:**
- Voice quirks из `config.voice.voice_quirks` применены
- Lexicon автора (Нельзяграм / Дубайск / контент-завод / вайбкодинг)
- Personal anchor в первых 2-3 абзацах
- Archetype voice consistent (Magician / Sage / Outlaw, не Caregiver)

**FAIL примеры:**
- Generic AI prose («In today's fast-paced world...»)
- Formulaic transitions
- Voice mixing (Sage в INTRODUCTION, Outlaw в PROCESS - без causation)

### 9. CTA - есть ли явный next step?

**Тест:** В closing - что читатель делает дальше? Это actionable?

**PASS критерии:**
- CTA в последних 50-100 словах
- CTA specific (одно действие, не «delight me with options»)
- CTA соответствует platform (newsletter → reply / forward, blog → subscribe, LinkedIn → comment / DM)
- CTA связан с main_aha (next step применяет insight)

**FAIL примеры:**
- Closing без CTA («thanks for reading»)
- Multiple CTAs (subscribe / share / DM / forward - выбери ОДИН)
- CTA не связан с content («подпишись на YouTube» в teaching essay про newsletter)

---

## Output для `04-review.md`

После прохождения checklist:

```yaml
maxwell_ross_9:
  idea: PASS
  clarity: PASS
  payoff: PASS
  specificity: PASS
  freshness: PASS
  hook: PASS
  length: PASS
  tone: PASS
  cta: PASS
  total: 9/9
```

Если хотя бы один FAIL → revision request с конкретным fix prompt.

## Memory cross-refs

- `[[post]]` - параллельная адаптация checklist для TG-постов
- - Freshness gate
- - Specificity gate
- - Hook gate (em-dash banned)
