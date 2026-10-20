# Reference - AI-tells специфика длинных форм

> Catalog AI-tells специфичных для длинных форм (>800 слов). Inherits базовые AI-tells из `post/references/_voice-TEMPLATE.md` (26 семантических классов A-Z). Здесь - longform-specific additions.

## Главные классы AI-tells в longform

### 1. Formulaic transitions

AI любит использовать одни и те же фразы для перехода между секциями.

**Banned EN:**
- «Now let me tell you»
- «So here's the thing»
- «But wait, there's more»
- «Here's what I learned»
- «Let me share with you»
- «Let me break it down»
- «Here's the kicker»
- «What's even more interesting»

**Banned RU:**
- «А теперь самое интересное»
- «Но это ещё не всё»
- «И вот что я понял»
- «Сейчас расскажу как»
- «В этой статье я разберу»
- «Давайте по порядку»
- «А теперь о главном»
- «Итак, поехали»

**Replacement strategy:** restructure параграф так чтобы переход был естественным. Или удалить transition полностью - следующая мысль должна сама связаться через content connection.

---

### 2. Generic listicle patterns

AI генерит generic «N способов» / «N причин» без глубины.

**Banned headlines:**
- «10 ways to grow your newsletter» ❌
- «5 reasons content marketing fails» ❌
- «Top 7 tools every solopreneur needs» ❌
- «10 способов» / «5 причин» / «Топ-7» - всё это banned для не-listicle типов

**Acceptable только для listicle template (v1.1):**
- «3 micro-decisions that 10x'd my open rate.»
- «4 emails I never thought to write - and they printed money.»

**Difference:** Number должен указывать на specific, отлично от generic.

---

### 3. Empty intensifiers

AI рассыпает intensifiers без causation.

**Banned:**
- «revolutionary», «mind-blowing», «game-changing»
- «революционный», «потрясающий», «обалденный»
- «значительно», «существенно», «зачастую»
- «massive impact», «huge results», «incredible»

**Replacement:** specific number + reference. «10x revenue» > «massive growth».

---

### 4. False precision

Fake-precision numbers (3.4%, 2.3x, 15.8) которые AI генерит для видимости data-driven.

**Regex auto-fail:** `\b\d+\.\d\b`

**Allowed:** Round numbers (10%, 100%, 2x) с указанием источника.

---

### 5. Tutorial genre intrusion

AI любит превращать любой essay в tutorial. Banned patterns даже если type != listicle:

- «Сейчас разберу что я называю»
- «Топ-3 ошибки которые я совершил»
- «5 шагов чтобы добиться X»
- «Шаг 1. ... Шаг 2. ... Шаг 3. ... Шаг 4. ...»

В teaching essay шаги OK в PROCESS секции, но НЕ в качестве всей статьи.

---

### 6. Hyperbolic life-changing claims

AI пытается убедить через emotional inflation:

**Banned:**
- «this changed my life»
- «это изменило всё»
- «после этого ничего не будет как прежде»
- «I'll never go back»

**Replacement:** конкретное изменение с числом / временем.

---

### 7. Reveal headings overuse

AI любит подзаголовки-обещания которые не выполняются.

**Banned патterns:**
- «What I learned» (без конкретики что именно)
- «The Truth About X» (без revelation в body)
- «Here's the secret» (без secret revealed)
- «The real reason» (без real reason)

**Replacement:** подзаголовок = mini-claim + payoff в body.

---

### 8. Closing-rhetorical questions

AI любит закрывать rhetorical question без CTA.

**Banned:**
- «What do you think?»
- «А что думаешь ты?»
- «Sound familiar?»
- «Have you experienced this?»

**Replacement:** specific CTA (subscribe / DM with specific topic / reply with specific answer).

---

### 9. List of 3 ratio overuse (rule of 3)

AI любит rule of 3 в каждом предложении («faster, cheaper, easier» / «быстрее, проще, дешевле»).

**Warning threshold:** ≥3 rule-of-3 constructs в 1000 слов → flag.

**Replacement:** vary structure - иногда 2, иногда 4-5, иногда no list.

---

### 10. Section header colon overuse

AI ставит двоеточие в каждом подзаголовке: «Topic: subtitle that explains it».

**Banned threshold:** ≥2 section headers с двоеточием → flag.

**Replacement:** alternate с question-based headers, или statement headers без colon.

---

### 11. Mortuary formals (из post config)

Inherited из `post/config.md#lexicon_banned_hard`:
- «потеряли клиентов»
- «вернулись на найм»
- «лишились аудитории»
- «дотянуть до результата»
- «осуществить переход»
- «совершить покупку»

В longform особенно опасны в PROCESS секции - звучат formal-corporate.

---

### 12. Numeric density overload

AI рассыпает числа везде чтобы выглядеть data-driven.

**Warning threshold:** >10 цифр в одном параграфе → warning.

**Replacement:** объединять близкие числа в short summary, оставлять только impactful numbers.

---

### 13. Anthropic-flavored closings

AI Claude любит закрывать «Let me know if you'd like me to expand on any of these points» / «Happy to dive deeper into any section».

**Banned:** любое closing к читателю в meta-tone «дайте знать если что».

**Replacement:** content-level CTA («Если ты пробовал X - поделись в комментариях что получилось»).

---

## Self-Discovery Method

В Pass 3 редактор сам должен:

1. Прочитать draft eyes-of-AI-tells (как будто это AI-generated)
2. Отметить любую sentence которая чувствуется generic
3. Применить «3-source test»: смогу ли я найти эту фразу в материалах автора (`paths.voice_corpus_dir`)? Если нет - restructure
4. Применить «voice quirks check»: соответствует ли фраза `config.voice.voice_quirks`?

## Output

```yaml
ai_tells_pass:
  formulaic_transitions_caught: [<list>]
  generic_listicle_patterns: [<list>]
  empty_intensifiers: [<list>]
  false_precision: [<list>]
  tutorial_intrusion: [<list>]
  hyperbolic_claims: [<list>]
  reveal_overuse: [<list>]
  closing_rhetorical: [<list>]
  rule_of_3_overuse: <count>
  colon_overuse: <count>
  mortuary_formals: [<list>]
  anthropic_closings: [<list>]
  total_violations: <count>
  severity: low | medium | high
```

**Fail threshold:** severity ≥medium → revision request с fix list.

## Inherits from

Base AI-tells: `post/references/_voice-TEMPLATE.md` + `post/references/ai-tells-catalog.md` (26 семантических классов A-Z, 100+ items).

Этот файл - longform-specific additions поверх базы.

## Memory cross-refs

- - generic AI banned
- - каждая правка системная
- - em-dash banned
- - без жаргона