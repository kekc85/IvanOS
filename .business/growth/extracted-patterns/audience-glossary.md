# Audience glossary — agent jargon → язык авторской ЦА

авторская ЦА (RU primary 2026): начинающие эксперты любых ниш, маркетологи, продюсеры курсов, SMM-щики, нишевые блогеры. **НЕ разработчики.** НЕ программисты. НЕ tech-savvy AI users.

Это значит agent-jargon из corpus (где creators говорят с tech-savvy audience) НЕ переносим напрямую. Нужен translation layer.

Это критическая causal проблема моего failed video skill test — я говорил «skills», «настроил voice», «команда» = это языкa Greg/Riley/Sabrina (их audience tech-savvy). авторская аудитория этого не понимает.

---

## Translation map

| Agent jargon | RU маркетолог | EN маркетолог |
|---|---|---|
| skill (Claude Skill) | мини-приложение / автомат / помощник | mini-app / assistant |
| skills folder | папка с твоими помощниками | folder with your assistants |
| config / config.md | настройка / твои данные | setup / your data |
| command (/post, /video) | одна команда / один промпт | one command / one prompt |
| voice (как в AI context) | стиль / манера речи / голос бренда | brand voice / your style |
| context window | сколько помнит за раз | how much it remembers |
| prompt engineering | как ставить задачи AI | how to instruct AI |
| MCP / model context protocol | подключения к твоим данным | data connections |
| agent / AI agent | помощник который сам делает | autonomous assistant |
| LLM | AI / искусственный интеллект | AI |
| token | (избегать вообще) | (avoid) |
| inference | работа AI / ответ AI | AI processing |
| fine-tune | обучение под себя | custom training |
| RAG | AI с твоими данными | AI with your data |
| vector / embedding | (избегать) | (avoid) |
| API key | ключ доступа | access key |
| webhook | соединение / триггер | trigger |
| markdown | текстовый файл | text file |
| terminal | командная строка / окно с кодом | command line |
| CLI | управление через текст | text-based control |
| infrastructure (как в моём failed test) | система / основа | system / foundation |
| repository / repo | папка с проектом | project folder |
| pipeline | цепочка / последовательность | sequence / chain |
| workflow | процесс / последовательность шагов | step-by-step process |
| n8n / Zapier | конструкторы автоматизаций | automation builders |
| Cursor / Claude Code | AI редакторы для создания | AI builders |
| Lovable / Bolt / V0 | AI которые делают сайты | AI website makers |
| vibe coding | программирование промптами / создание без кода | prompt-based programming / no-code creation |
| vibemarketing | маркетинг через AI / контент-завод | AI marketing / content factory |

---

## Avoid-list (term которые НЕ должны появляться)

В скрипте для RU ЦА:

- ❌ «настроил воркфлоу»
- ❌ «модель» (когда речь об LLM)
- ❌ «токен»
- ❌ «эмбеддинг»
- ❌ «инференс»
- ❌ «латенси»
- ❌ «промпт-инжиниринг» (можно «как давать задачи AI»)
- ❌ «деплой»
- ❌ «фронтенд / бэкенд»
- ❌ «фреймворк»
- ❌ «API»
- ❌ «контекст-окно»
- ❌ «вектор / эмбеддинг»

Если слово из avoid-list появляется в скрипте — auto-fail в content-skill review.

---

## Допустимые в правильном контексте

Эти слова OK для RU аудитории если используются с context:

- ✅ «Claude» (бренд) — все знают
- ✅ «ChatGPT» (бренд) — все знают
- ✅ «промпт» — стало RU mainstream термином
- ✅ «AI» / «искусственный интеллект»
- ✅ «нейросеть» (RU mainstream)
- ✅ «контент-завод» (авторский термин)
- ✅ «вайбкодинг» / «вайбмаркетинг» (авторская категория)
- ✅ «Нельзяграм» / «Instagram» (но preferences «Нельзяграм»)

---

## ICP language markers (что использует авторская ЦА сама)

Из observed survey / DM / комментариев в авторских группах:

- «у меня курс на 200К»
- «мои подписчики»
- «моя аудитория»
- «запускаю / запустить»
- «воронка»
- «трипваер»
- «прогрев»
- «кейсы учеников»
- «50К подписчиков»
- «прайс / прайсинг»
- «оффер»
- «продажи / выручка»
- «оборот / месяц»

**Use these** в content-skill output для cross-recognition с целевой аудиторией. Они сразу опознают что это про них.

---

## Audience descriptor (memory `feedback_audience_not_only_experts`)

В авторской content (от lead magnets до cash events):

- ✅ «ты» / «тех у кого» / «один человек»
- ❌ «эксперт» / «эксперты» / «специалист» (сужает воронку)

Объекция аудитории:

- ✅ «не маркетолог» (primary)
- ❌ «без опыта в коде» / «не программист» (никогда — memory `feedback_no_code_objection_ever`)

---

## Жаргон-замена checklist для content-skill review

1. Прогнать output через avoid-list (regex)
2. Auto-replace common (skill → мини-приложение, command → один промпт, config → настройка)
3. Flag uncertain (term который может быть OK в контексте) → manual review
4. Validate ICP markers — есть ли хотя бы 1 phrase из ICP language list

Если ICP markers = 0 → output звучит как для tech-savvy audience, не для авторской ЦА.

---

## Authority name translation

Для authority name-drop (см. `authority-namedrop-pattern.md`):

- Anthropic CEO / Dario Amodei → «CEO Anthropic» (без имени если RU аудитория не знает) ИЛИ «Карпатый из Anthropic-circle»
- OpenAI CEO / Sam Altman → «Альтман / CEO OpenAI» (известен в RU mainstream)
- Andrej Karpathy → «Карпатый» (один из создателей AI образования)
- Pieter Levels → «Питер Левелс / индихакер»

**Iваные authorities в RU контексте** (work лучше чем foreign names):
- авторские ученики (с verified results)
- авторские собственные результаты (<твоя выручка> / <число учеников>)
- Andrei Sebrant (Яндекс)
- Алекс Хормози — universally known через переводы

---

## Cultural adaptation notes (RU vs EN)

### Что переносится дословно
- Hook structures (Pattern 1-9)
- Body walkthrough steps
- CTA mechanics
- Visual sequences

### Что адаптируется культурно
- Idioms («I'd bet my life on it» → «гарантирую»)
- Examples (Tinder for guys → Сбербанк-приложение для X)
- Numbers (¥ → $ / $ → ₽ при переносе)
- Authority names (foreign → Russian-known)

### Что НЕ переносится
- Mat / swearing (авторская persona — не мат)
- Cultural references США (NBA / NFL / college references)
- US-specific tools без EN equivalents

---

## Cross-refs

- `hook-patterns-empirical.md` — authority embedded в Pattern 3
- `authority-namedrop-pattern.md` — name translation matrix
- `voice-markers-empirical.md` — авторский voice не использует jargon
- `~/.business/audience/avatar.md` — официальный ICP документ
- `~/.business/audience/objections.md` — known objections
