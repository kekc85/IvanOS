# Caption Formulas - IG vs LinkedIn + bilingual

Reference для `workflow/03-write.md` Pass 3 (caption generation). Source: bucket-a (Sabrina / Riley / Pieter caption patterns), bucket-b (LinkedIn 210-char fold + Welsh / Acosta / Alić caption structures), bucket-e (CTA mechanics).

Используй когда:
- Пишешь caption под carousel
- Выбираешь caption formula под family / mode
- Решаешь hashtag strategy
- Адаптируешь под bilingual RU + EN

---

## 1. Platform character folds - что критично

| Platform | Fold | Что значит |
|---|---|---|
| Instagram | 125 chars | До «more» tap. Первые 125 символов решают раскрытие caption. |
| LinkedIn | 210 chars | До «see more». Hook live battlefield. |
| Threads | 500 chars total | Нет fold но total cap. |
| TG (если cross-post) | 1024 chars в media group | Native album caption limit. |

**Правило:** первые 125 / 210 chars = hook battleground. Должны самостоятельно работать как промо carousel без раскрытия.

Source: bucket-b verbatim spec, bucket-a Sabrina / Riley caption analysis.

---

## 2. Caption ≠ slides duplication rule

**Hard rule (CR-G7 в `04-review.md`):**

Caption НЕ должна пересказывать содержимое slides. Caption даёт **дополнительный layer**:

- Backstory которой нет в slides
- TL;DR + amplified CTA
- Вопрос аудитории
- Behind-scenes как делал
- Soft CTA dispersed (slide 5-6 встроенно + hard CTA caption end)

Bad example (duplication):
```
В этом carousel я показываю 8 шагов:
1. Сделай X
2. Потом Y
3. Дальше Z
...
[пересказ всех slides]
```

Good example (additional layer):
```
Этот процесс родился в среду в 03:47 когда подрядчик отвалился перед эфиром.

Что я вынес - в карусели. Что забыл сказать там - что 80% людей застревают на шаге 5 потому что пропускают одну деталь в Cursor setup.

Скинь "разбор" в комменты - пришлю в DM подробный разбор шага 5.
```

**Detection:** если >50% caption text повторяет slide bodies - CR-G7 FAIL, переписать.

---

## 3. 5 caption formulas

### 3.1 Mini-PAIPS (pain → agitate → intrigue → positive → sale)

Source: Уэлш PAIPS adapter, верифицировано на linkedin-friendly формате.

Структура:
```
[Pain] - 1 строка боль аудитории
[Agitate] - 1-2 строки усиление боли (consequences)
[Intrigue] - 1 строка teaser о solution
[Positive] - 1 строка transformation possible
[Sale] - CTA конкретный
```

Verbatim пример (адаптировано для автора):
```
Подрядчик исчез перед эфиром. Дедлайн в пятницу.

Раньше это значило перенос, потерю аудитории, репутационный hit. Сейчас - значит 47 минут на Lovable + Claude Code.

В карусели разбор полного процесса. Inside: какой prompt в Composer, как обойти 3 классических трудности с auth, что сломалось у меня в третьей попытке.

Это работает не потому что я гений - потому что инструменты дозрели в 2026.

Сохрани этот пост - вернёшься когда будешь собирать первый MVP.
```

Длина: ~600-900 chars (LinkedIn-friendly, не fits в IG 125 fold но fits в LinkedIn 210 fold с разворотом).

Применение: launch-content, ситуативный (Spark), story-case family.

### 3.2 Story-bridge (caption = backstory к carousel)

Caption даёт backstory которой нет в slides. Carousel = playbook, caption = откуда взялся.

Структура:
```
[Trigger event] - что произошло в реальности
[Internal conflict] - как чувствовал
[Decision moment] - что решил делать
[Tease carousel] - не пересказ, а зачем читать
[CTA] - один artifact
```

Verbatim пример:
```
В марте 2025 я считал что мне нужна команда из 3 человек чтобы запустить курс.

К сентябрю обнаружил себя соло, с 247 платных учеников и 12 микро-SaaS которые работают без меня.

Что изменилось между мартом и сентябрём - в карусели 9 slides.

Один из них (slide 6) я бы не понял в марте даже если бы прочитал.

В TG разбор + полный процесс шаг за шагом - закреп <твой-хэндл>.
```

Применение: story-case family, retrospective content.

### 3.3 Summary-with-CTA (TL;DR + amplified CTA)

Короткий caption который суммирует основную мысль + сильное CTA.

Структура:
```
[TL;DR в 1-2 строках] - main insight carousel
[1 строка bridge]
[Hard CTA с конкретным artifact]
```

Verbatim пример (Sabrina-style):
```
9 промптов для вайбмаркетинга 2026. Все тестированы на запуске <твоя подписка>.

Slide 4 - тот который добавил +30% к open rate в Kit.

Сохрани, чтобы вернуться. Комментарий "промпты" - пришлю в DM полный pack.
```

Длина: ~250-400 chars. Fits в LinkedIn 210 fold ровно.

Применение: listicle / framework-breakdown family, value-drop posts.

### 3.4 Question-bait (caption опрашивает, carousel отвечает)

Caption задаёт открытый вопрос аудитории, carousel = автор отвечает / разбирает варианты.

Структура:
```
[Вопрос аудитории] - open question, не yes/no
[Контекст почему спрашиваешь] - 1-2 строки
[Carousel reference] - "мой ответ в карусели"
[Comment invitation] - "напиши свой в комментах"
```

Verbatim пример:
```
Что мешает вам собрать первый рабочий MVP за выходные?

За три месяца я спросил это у 80 учеников. Получил 5 повторяющихся ответов.

Мой разбор каждого - в карусели. Slide 8 - тот который удивил меня больше всего.

Напиши в комменты что мешает именно тебе - разберём в эфире в субботу.
```

Применение: список 5-7 items, посты на обсуждение с аудиторией.

### 3.5 Behind-scenes (caption = «как делал», carousel = «что получилось»)

Caption показывает messy process, carousel = clean output.

Структура:
```
[Messy reality] - что было до полировки
[Specific moment] - 1 деталь которая запомнилась
[Result tease] - финал в карусели
[Soft CTA] - сохрани / комментарий
```

Verbatim пример:
```
Три попытки. Первая сломалась на Supabase RLS, вторая на Lovable preview build, третья заработала за 47 минут.

В среду в три ночи нашёл одну строку в auth setup которая ломала всё. Перепробовал 14 вариантов prompt в Cursor.

Финальный процесс + Claude prompts - в карусели 10 slides.

Сохрани - вернёшься когда будешь делать первый.
```

Применение: story-case family, vulnerability + proof.

---

## 4. Hashtag strategy 2026

### 4.1 Instagram

- 3-5 hashtags максимум
- Mix: 1 broad (`#вайбмаркетинг`), 2-3 niche (`#claudecode #lovable #нельзяграм`), 1 branded (`#сергеевиван`)
- Размещение: в конце caption ИЛИ первый комментарий (нет разницы в охвате 2026)

### 4.2 LinkedIn

- 0-2 hashtags - алгоритм LI deprioritizes hashtags в 2026 (verified bucket-b)
- Если используешь - только специфические (`#vibemarketing`, не `#marketing`)

Verbatim правило Welsh / Acosta / Alić (bucket-b): zero hashtags на post. Они signal что contenty organic, не SEO-bait.

### 4.3 Telegram

Хэштеги в TG работают как navigation tags для канала, не для discovery. Если используешь - один или ноль (`#разбор` для дайджеста по тегу).

### 4.4 Threads

3-5 как IG, но Threads растёт - можно experiment до 7.

---

## 5. CTA placement в caption

### 5.1 Soft CTA mid-caption

В середине caption встроенная фраза:
- `Сохрани - вернёшься когда [trigger]`
- `Скинь "[keyword]" в комменты`
- `Slide [N] - тот который удивил`

Source: bucket-e (CTAs на нескольких slides +20-30% ER).

### 5.2 Hard CTA caption end

Последняя строка caption = explicit ask.

5 canonical patterns:
1. **Comment-trigger DM** (Sabrina): `Комментарий "разбор" - в DM пришлю ссылку на полный разбор процесса`
2. **Link in bio**: `Полная методология - закреп в шапке <твой-хэндл>`
3. **Save**: `Сохрани этот пост - вернёшься когда будешь собирать первый`
4. **Newsletter subscribe**: `Каждую субботу новый билд - подписка в bio`
5. **Follow experiment**: `На следующей неделе тестирую X - подписка чтобы не пропустить`

Запрещены generic:
- `Like if you agree`
- `Tag a friend`
- `Follow me для большего контента`
- Multi-CTA на одной строке (выбирай ОДНУ)

---

## 6. Bilingual handling (RU + EN)

Если `config.subject.language = both` или флаг `--bilingual`:

### 6.1 Параллельная генерация

Сначала пишем RU caption (primary voice автора). Потом chain в `multi-language-localization` skill для EN адаптации.

**Не дословный перевод.** Культурная адаптация:
- Cultural anchors меняются (RU «хрущёвка-detail» → EN «one-bedroom apartment»)
- Currency меняется (₽ → $ с пересчётом или с явным «(~$ amount)» в скобках)
- TG references меняются на EN platforms (`<твой-хэндл> TG` → `subscribe my newsletter`)

### 6.2 Output structure

Caption выдаётся как два независимых блока:

```
=== RU ===
[RU caption full text]

=== EN ===
[EN caption full text - cultural adaptation, not translation]
```

Каждый блок проходит свой review (RU - русские banned patterns из bucket-c, EN - английские из bucket-a/b).

### 6.3 Carousel slides bilingual

Слайды публикуются раздельно для RU vs EN аудитории:
- RU carousel = RU slides + RU caption → <твой-хэндл> TG / RU Нельзяграм
- EN carousel = EN slides + EN caption → Skool / LinkedIn / EN Threads

Если один carousel для bilingual audience (rare) - text overlay на slides EN-only, caption даётся в двух блоках.

---

## 7. Verbatim examples из research

### 7.1 Justin Welsh LinkedIn caption (8 moves carousel)

Pattern: micro-hook ≤210 → context → newsletter CTA.

```
I cracked LinkedIn's code in 8 moves.

783,895 followers, 6.384M impressions, and a $5M+ business later, here's the playbook.

Most creators chase reach. I chased trust. The result was a system that compounds.

The 8 moves in the carousel are the same ones I teach inside Saturday Solopreneur.

Join 300K+ readers: [link]
```

Длина: ~440 chars total. Первые 210 (до «see more» fold):
```
I cracked LinkedIn's code in 8 moves.

783,895 followers, 6.384M impressions, and a $5M+ business later, here's the playbook.
```

### 7.2 Riley Brown IG caption (vibe coding tools)

Pattern: short tease + tool tags + bio CTA.

```
Using the 6 best Vibe Coding Tools AT THE SAME TIME.

Without writing a single line of code.

Stack: @lovable @boltdotnew @replit @cursor_ai @windsurf_ai @v0

Full tutorial - link in bio.
```

Длина: ~220 chars. Tool tags = boost для discovery.

### 7.3 Lara Acosta LinkedIn caption (SLAY framework)

Pattern: short hook + framework name + comment-trigger.

```
SLAY - the only LinkedIn framework I use.

S - Story (≤10 words)
L - Lesson (1 line)
A - Actionable (1 step)
Y - You (direct address)

Carousel breaks down each layer with examples.

Comment "SLAY" - I'll DM the template.
```

Длина: ~280 chars. Mini-CTA встроена в acronym.

---

## 8. Caption length budgets

| Platform | Hook (до fold) | Body | Total max |
|---|---|---|---|
| Instagram | ≤125 chars | 200-600 chars | 1000 hard cap (правило автора — НЕ больше 1000) |
| LinkedIn | ≤210 chars | 300-1500 chars | 3000 practical (no hard cap) |
| Threads | ≤500 chars | 100-400 chars | 500 hard cap |
| TG media group | ≤200 chars hook | 500-800 body | 1024 hard cap |

**Target sweet spots:**
- IG: 600-900 chars total (audience reads если hook раскрыли)
- LinkedIn: 800-1500 chars total (LI audience reads больше)
- Threads: 350-450 chars total
- TG album: 700-900 chars total

---

## 9. Banned in captions (text-level patterns)

Хард-фейл (regex check в `04-review.md`):

- Em-dash «-» внутри строк (используй дефис «-» или запятую)
- «Instagram» (auto-correct в «Нельзяграм»)
- `framework / workflow / pipeline / engagement / retention / scope / onboarding / artifact` (англицизмы из banned list)
- `synergy / leverage / paradigm / disruption / cutting-edge`
- Round numbers без verification (`10X / 1000% / 100% gain`)
- Multi-CTA на одной строке (`Follow + like + comment + share`)
- Generic AI clichés (`без воды / именно поэтому / следовательно / в этом посте`)

Soft-warning:
- >1 восклицательный знак в caption
- >5 hashtags на IG / >2 на LinkedIn
- Caption длиннее platform target
- ALL CAPS длиннее 3 слов (RU-specific bucket-c)

---

## 10. Decision tree - какая formula

```
Personal story с backstory? → Story-bridge (3.2)
List items 5-12 с проверенной value? → Summary-with-CTA (3.3)
Open question, хочу community discussion? → Question-bait (3.4)
Vulnerability post, messy process? → Behind-scenes (3.5)
Launch / sale-adjacent? → Mini-PAIPS (3.1)
```

Если несколько подходят - выбирай по primary intent. Cross-formula = brak (выбери одну, иначе caption разваливается).

---

## 11. Caption review checklist (mini)

Перед output проверь:

- [ ] Hook (первые 125 IG / 210 LI chars) самостоятельно работает как stop-scroll
- [ ] Caption НЕ пересказывает slides (CR-G7)
- [ ] Soft CTA в mid если caption >400 chars
- [ ] Hard CTA в финале - один artifact + action
- [ ] Hashtag count в пределах platform (3-5 IG / 0-2 LI)
- [ ] Нет em-dash «-» внутри строк
- [ ] Нет банлист англицизмов
- [ ] Если bilingual - 2 блока RU + EN через `multi-language-localization`
- [ ] Length в platform budget

Если ≥1 чек fail - переписать перед output.

---

## 12. Cross-references

- `carousel-anatomy.md` - hook formulas, slide structure (caption hook повторяет slide 1 hook логику)
- `visual-brief-real-first.md` - real elements rule (caption тоже содержит specific numbers и tool names)
- `banned-ai-imagery.md` - text-level banned patterns (раздел 11 + RU-specific)

Memory cross-refs:
- `[[feedback-no-em-dash]]` - em-dash запрещён
- `[[feedback-telegram-friendly-output]]` - plain text для TG mirror
- `[[multi-language-localization]]` - RU↔EN адаптация cultural