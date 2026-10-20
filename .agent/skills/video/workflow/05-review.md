# 05-review - 6-Pass + Maxwell Ross 9 + 3 слоя + Hook Strength Gate + Length

Стадия 5. Финальный QA gate. Без 9/9 PASS Maxwell Ross + 7/7 контуров + Hook Strength PASS - script не выходит.

## Loaded by

- 04-write.md по завершении

## Input

Draft script из 04-write.md.

## Output

Reviewed script для 06-output.md (или escape назад в 04 с reasons).

## Шаги

### 5.1: Regex gates (auto-fail)

Прогнать draft (script_full + captions_full + headline_chosen) через regex:

| Gate | Regex / Check | On fail |
|---|---|---|
| G1: Em-dash inside lines | `-` not at bullet start | FAIL |
| G2: Instagram | `(?i)instagram\|инстаграм` | FAIL (auto-correct в Pass 4) |
| G3: Wrong content-factory term | `контент-фабрика\|контент-машина\|content factory` | FAIL (auto-correct) |
| G4: Vibe coding wrong | `вайб-кодинг\|vibe coding` | FAIL (auto-correct) |
| G5: Banned terms | config.lexicon_banned | FAIL |
| G6: «эксперт» as audience | контекст «для экспертов» | FAIL |
| G7: «без опыта в коде» | `без опыта в коде\|не программист\|программирование` | FAIL |
| G8: Competitor name as enemy | `GetCourse\|<конкурент>\|Skillbox` в позиции «враг» | FAIL |
| G9: Negative public stats | `20% доходят\|только N%\|никто не` | FAIL |
| G10: «только Claude» | `только Claude\|чисто Claude` | FAIL (auto-correct в «Claude в ядре, 90%») |
| G11: Length floor | total_duration_sec < tier.floor_sec | FAIL |
| G12: Length ceiling | total_duration_sec > tier.ceiling_sec | FAIL |
| G13: Multiple exclamations | `!.*!` (>1 в шорте) | WARNING |
| G14: Метафоры если есть термин | См. `_voice-TEMPLATE.md` список banned метафор | WARNING |
| G15: Headline length | YouTube >70 chars / caption overlay >50 chars | FAIL |

Если любой FAIL - записать в `failures[]` и попробовать auto-fix в этом же passe (Pass 2 logic), в конце 5.7 решить эскалацию по unresolved.

### 5.2: Hook Strength Gate

Прочитать первые 1.5-3 sec script:

3 теста (config.hook_strength.tests):
1. В первые 3 sec присутствует conflict / contradiction / visual contrast / numeric outlier?
2. Value proposition понятна зрителю без предыдущего контекста?
3. Первые 3 sec заканчиваются на cliff / question / promise (не на резюме)?

Если хоть один FAIL:
- Output reason в чат
- Re-write hook (max 3 ретрая)
- После 3 неудач - эскалация в чат, спросить у пользователя ручную корректировку

### 5.3: 6-Pass Refinement

Прогнать draft через 6 перспектив (config.six_pass):

1. **Skeptic** - «зачем мне это смотреть»: есть ли явная value proposition для зрителя
2. **Scroller** - «остановит ли scroll в 1.5 sec»: hook strong enough
3. **Producer** - «реально ли это снять»: производственная реализуемость (есть ли B-roll возможность, demo доступен, etc)
4. **Editor** - «темп / pacing / повторы»: нет ли повторов, beat'ы flow, нет лишнего
5. **Algorithm** - «watch time / completion rate / saves / shares»: drag retention check (особенно середина шорта)
6. **Voice** - «звучит ли как автор»: voice fidelity (lexicon, темп, концеретика)

Каждый pass - текстовая оценка + список фиксов. Применить фиксы внутри 05 (не возвращать в 04).

### 5.4: Maxwell Ross 9-checklist

9 yes/no (config.maxwell_ross_9):

1. **Idea** - есть ли центральная идея в одно предложение?
2. **Clarity** - понятно ли с первого просмотра?
3. **Payoff** - есть ли выплата зрителю в конце?
4. **Specificity** - есть ли конкретика (числа / имена / артефакты)?
5. **Freshness** - не повторяет ли предыдущие видео? (check vs track-record)
6. **Hook strength** - первые 1.5-3 sec проходят stop-scroll?
7. **Length fit** - попадает в target tier (floor + ceiling)?
8. **Tone** - voice автора не выдуман? (Pass 0 reads must hit)
9. **CTA** - CTA в финале или explicit отсутствие?

**Cutoff: 9/9 PASS обязательно.** Если 8/9 - переписать так чтобы прошёл 9-й. Если ≤7/9 - эскалация.

### 5.4.5: Benchmark Gate (NEW v1.1 - закрытие root cause v1.0)

**Это критический gate.** Без него skill проходит формально, но output не соответствует реальным viral patterns.

#### Шаг 1: Identify nearest 3 шорта из corpus

```
Read: ~/.business/growth/extracted-patterns/benchmark-corpus-index.md
```

Filter по:
- Length tier (short-15-30s / 30-60s / 60-180s - corpus contains shorts only; для mid/long tier escape с warning «no benchmark, expand corpus»)
- Hook archetype (Pattern 1-9 из hook-patterns-empirical.md)
- CTA type alignment

Получить 3-5 nearest matches с их metadata (views / likes / format).

#### Шаг 2: Structural fidelity comparison

Сравнить generated script с каждым из 3 nearest matches по checklist:

1. **Hook structure match.** Verbatim structure близка к одному из 9 patterns?
   - Pattern 3 (inevitability) → ОБЯЗАТЕЛЬНО authority proof в first 10 sec (per `authority-namedrop-pattern.md`)
   - Pattern 5 (numeric outlier) → number verified, не выдуманный
   - Pattern 6 (timeframe + outcome) → outcome specific

2. **Body structure match.** Walkthrough? N-step system? Multi-step demo?
   - Greg-style 4-step (First / Then / After that / Finally)
   - Riley-style multi-step с mini-hooks каждые 20-30 sec
   - Sabrina-style mid-roll save + URL repeat

3. **Concrete tool names.** Per body beat - есть конкретный tool / file / command? Не abstract.

4. **CTA type match.** CTA соответствует один из 5 types из cta-patterns-empirical.md? Маппинг с funnel destination?

5. **Visual brief present.** Каждый beat имеет visual layer (не только text)?

6. **Audience glossary check.** Output не содержит avoid-list terms (skills / config / command без перевода)?

7. **Funnel destination explicit.** Куда ведёт шорт зрителя? Lead magnet ready?

#### Шаг 3: Score

Каждый item PASS = 1 point. Total /7.

- **5+/7:** Benchmark PASS
- **3-4/7:** WARN (escape с обоснованием в чат)
- **0-2/7:** FAIL - rewrite required

#### Шаг 4: Output benchmark report

В чат:
```
Benchmark Gate:
- Nearest matches: <#X (views) / #Y (views) / #Z (views)>
- Hook archetype: <Pattern N> ✓/✗
- Body structure: <Greg/Riley/Sabrina style> ✓/✗
- Concrete tools per beat: ✓/✗
- CTA type match: <Type N> ✓/✗
- Visual brief present: ✓/✗
- Audience glossary clean: ✓/✗
- Funnel destination explicit: ✓/✗
- Score: X/7
- Verdict: PASS | WARN | FAIL
```

Если FAIL - escape в 04-write с reasons. Если WARN - продолжать в 5.5 с явным acknowledgment.

#### Hard rules

- Pattern 3 (inevitability) без authority proof = auto FAIL (memory `feedback_no_inventing_facts`)
- Avoid-list term из audience-glossary.md = auto FAIL
- Missing funnel destination = auto FAIL (не публиковать без mapping в воронку)

### 5.5: 3 слоя финальный gate

**Слой 1 - Валидаторы:**
- 5.1 regex gates + Hook Strength + Maxwell Ross 9 - все проверены
- Listing detection: «10 советов про X» / «5 ошибок» = generic AI artifact → FAIL

**Слой 2 - 4 концепции:**
1. **Pre-mortem 5 причин провала:** что может пойти не так если этот script запустить? (hook слабый / payoff нет / production невозможен / audience сужена / generic)
2. **Калибровка уверенности 90%+:** уверен ли я что это попадёт в авторский voice? Если <90% - escape назад в 04 для усиления Pass 2 / 2.5
3. **Multi-perspective:** Зритель (стопит scroll?) / Алгоритм (retention?) / автор (хочет ли он это выпустить?)
4. **Адаптивность:** новая ошибка → новый валидатор в config.lexicon_banned или в references

**Слой 3 - 7 контуров:**
1. **Контекст** - соответствие brief из 02 и source из 01
2. **Соответствие предпосылкам** - Карта смыслов / card.md / надиктовка - body соответствует
3. **Целесообразность** - этот формат и этот tier - лучшее решение?
4. **Релевантность** - для конкретного segment target audience?
5. **Фактология** - никаких выдуманных цифр / имён / дат
6. **Реализуемость** - производственная цепочка реальна (downstream handoff workable)
7. **Достоверность** - звучит как автор, не как AI

### 5.6: Approval phrase

После прохождения всех passes - explicit text в чат:

```
3 слоя пройдено, флагов нет.
```

или

```
3 слоя пройдено, флаги: <list>. Митигации применены: <list>.
```

Без этой фразы - 06-output.md не загружается. Это hardcoded правило (как у post).

### 5.6.5: 4 теста заголовка (SOLO `pisatel-*` canib)

Применяется к **script hook** (первая фраза сценария) + **video headline** (для thumbnail / название поста). Gate перед утверждением, BLOCKING:

1. **Самодостаточность.** Hook понятен холодному зрителю без контекста / без описания / без знания канала. Если зритель должен «дослушать чтобы понять о чём» → FAIL.
2. **Конкретное действие.** В hook есть глагол / результат / цифра, не абстракция. «Собери первый продукт за 6 недель» → PASS. «Раскрой свой потенциал через ИИ» → FAIL.
3. **Простой русский.** Без жаргона методологии, без англицизмов, без слов которые зритель не использует в своей речи. Тест: «Сказал бы ICP это вслух другу?» Нет → FAIL.
4. **Не сужает ширину.** Не отсекает зрителей по профессии / нише если контент горизонтальный.

Если хоть один FAIL → переписать hook или headline. После 3 ретраев → эскалация.

### 5.6.7: Identity + Citations Gate (SOLO canib)

Read `~/.claude/skills/_shared/identity-citations-gate.md`, применяй Gate 1 (Identity-preservation) + Gate 2 (Verbatim citations) если в скрипте есть цитаты ICP. Если FAIL → revision, не proceed на humaniser.

### 5.7: Escalation policy

Если после всех passes остались unresolved FAILs:

- Hook Strength fail после 3 ретраев → эскалация в чат «не могу сделать hook сильным - нужны твои идеи»
- Maxwell Ross ≤7/9 → эскалация
- Несовместимые требования (Mode C: original duration 90s но writer считает что 30s лучше) → эскалация с обоснованием

Escalation = output в чат + STOP. Никакого автоматического перехода в 06.

## Strategy paragraph в чат

```
Review:
- Regex gates: <N pass, N fail (исправлено)>
- Hook Strength: <PASS|FAIL (N ретраев)>
- 6-Pass: <summary fixes>
- Maxwell Ross 9: <X/9>
- 3 слоя: <PASS|FAIL details>

3 слоя пройдено, флагов нет.
```

## Hard rules

- 9/9 Maxwell Ross - нет компромисса
- 3 слоя explicit phrase в чат - нет компромисса
- Hook Strength 3 ретрая max, потом эскалация
- Regex gates auto-fix где возможно, fail иначе

## Anti-patterns

- Pass через «выглядит OK» без явного 6-Pass перспектив
- Маркировка 9/9 без реальной проверки каждого пункта
- Auto-loop переписывания (>3 ретрая = эскалация, не endless)
- Skip Hook Strength «потому что hook subjective»
- Skip Layer 2 Pre-mortem «потому что и так понятно»