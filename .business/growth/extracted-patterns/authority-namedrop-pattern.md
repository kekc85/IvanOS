# Authority name-drop pattern — empirical

Отдельный класс mechanic потому что это **обязательная составляющая** для Pattern 3 (inevitability hook).

## Mechanic

Authority name-drop = ссылка на industry figure / company / verified number в первые 5-10 sec после hook.

Используется как **proof of concept** для bold claim в hook. Без него bold claim звучит как пустая претензия.

---

## Examples из corpus

### Riley #3 (562K views — TOP 5 viral)

Hook: «Is programming going to be replaced by vibe coding?»

**Authority proof (sec 3-7 после hook):**
> «In the next three to six months, AI will be writing 90% of the code, according to the founder of Anthropic»

**Second authority callback (sec 15-20):**
> «The CEO of Gumroad thinks that we are already there, saying that if you're writing code, you're making the conscious choice not to ask AI to write the code for you, and then comparing this to doing dishes by hand»

**Triple proof structure:**
1. Hook claim
2. Anthropic founder citation (Dario Amodei)
3. Gumroad CEO citation (Sahil Lavingia)

**Эффект:** viewer не может dismiss hook как opinion — это прямые цитаты top industry figures.

---

### Greg #16 (50K)

Hook: «Here's a 3-skill system that turns Claude Opus 4.5 from just a coding agent to an army of senior engineers»

**Authority hint:**
> «...all vetted by Anthropic»

Менее explicit но всё равно authority signal.

---

### Greg #23 (25K)

Hook: «Here's how you can get 10 times better outputs from Claude»

**Authority proof:**
> «...all vetted by Anthropic»
> 
> «Here's some power phrases shared by Anthropic, to help get better outputs»

**Эффект:** rules не выдуманы Грэгом — он передаёт официальную позицию Anthropic.

---

## Authority categories observed

### Tier 1: Founder / CEO of major AI company
- Dario Amodei (Anthropic CEO)
- Sahil Lavingia (Gumroad CEO)
- Логан Кильпатрик (Google DeepMind)
- Sam Altman (OpenAI — implied часто)

### Tier 2: Brand company name
- «Anthropic verified»
- «Anthropic recommends»
- «vetted by [company]»

### Tier 3: Verified numbers
- «23 million views»
- «hundreds of millions of views»
- «81M views in 12 days»

### Tier 4: Citation of specific tool / research
- «according to this study»
- «based on this Anthropic doc»

---

## авторские authorities (для replication)

**Tier 1 — RU/Global figures автор может cite:**
- Карпатый (Andrej Karpathy) — vibe coding originator, founder OpenAI alumni, deep learning
- Бенгио (Yoshua Bengio) — Turing Award, AI safety
- Sam Altman (OpenAI)
- Dario Amodei (Anthropic)
- Pieter Levels (indie hacker authority)

**Tier 2 — Russian-friendly figures:**
- Андрей Себрант (Яндекс)
- Дмитрий Песков (АСИ, AI лидерство)
- Игорь Манн (маркетинг authority)
- Алекс Хормози (Hormozi — universally known)

**Tier 3 — verified numbers (авторские):**
- <число учеников> автора
- <твоя выручка> за квартал 2025
- 500K+ совокупная аудитория
- Конкретные результаты учеников (например тренеры <метрики учеников>/мес после курса)

**Tier 4 — Russian businesses references:**
- Pieter Levels examples
- Riley Brown examples
- Greg Isenberg examples

**Critical:** Если cite авторская statistic, она ДОЛЖНА быть verified. Memory `[[feedback-no-inventing-facts]]` строго применяется.

---

## Replication template для авторского скрипта

**Hook + Authority structure:**

```
[Hook claim — 3 sec]
[Authority proof — 5-7 sec]
[Optional: second authority callback later — 10-15 sec into video]
[Continue body...]
```

**Examples replication:**

«Конструкторы воронок умрут. // Карпатый месяц назад сказал — через 3-6 месяцев 90% кода пишет AI. // А продюсерская модель — это та же программистская задача. Делегирование, координация, выпуск. AI закрывает 90%. //  Сейчас покажу как заменить целую команду маркетинга одним промптом...»

Где:
- 1st sentence = hook (Pattern 3 inevitability)
- 2nd sentence = Tier 1 authority (Karpathy)
- 3rd sentence = bridge connecting authority to claim
- 4th sentence = body start

---

## Cutoff правила в content-skill

1. Если используется Pattern 3 (inevitability hook) — authority proof ОБЯЗАТЕЛЕН в first 10 sec
2. Authority citation должна быть verifiable (cite source, не выдуманная)
3. Tier 1 (industry CEO) > Tier 2 (brand) > Tier 3 (numbers) > Tier 4 (anonymous study)
4. Для авторских scripts — preferred Tier 1 international (Karpathy / Altman / Amodei) ИЛИ Tier 3 авторские verified numbers
5. Никогда не выдумывать quote / statistic — instant credibility loss

---

## Anti-patterns

1. **Vague authority** — «эксперты говорят» / «многие считают» = no authority
2. **Misquoted figure** — если процитировал неправильно, viewers в комментах поймают
3. **Self-as-authority без proof** — «я знаю что» без verified numbers / track record
4. **Too many authorities** — больше 2 имён в одном шорте dilutes каждый

---

## Cross-refs

- `hook-patterns-empirical.md` Pattern 3 — обязательная связка
- `voice-markers-empirical.md` Riley section — best example
- `audience-glossary.md` — authority names в RU контексте
