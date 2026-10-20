# Workflow 00: Onboarding student

Триггер: первый запуск skill при отсутствии или неполном `config.md`.

## Когда срабатывает

Router (`01-router.md`) проверяет:
- Существует ли `~/.claude/skills/single-image/config.md`?
- Есть ли в нём заполненный `subject.name` ≠ «автор» (если ученик)?
- Есть ли `paths.avatar` и `paths.brand_guidelines` указатели в существующие файлы?

Если ХОТЬ ОДИН ответ NO → запустить onboarding.

## 9 вопросов

Задаются последовательно (НЕ batch). Каждый ответ сохраняется в config.md инкрементально.

### Вопрос 1: Имя автора
«Как тебя зовут? (полное имя или handle - то что будешь использовать в attribution)»

→ `subject.name`

### Вопрос 2: Главные платформы
«На каких платформах ты публикуешь картинки-посты?
- X / Twitter
- LinkedIn
- Нельзяграм / Instagram
- TG / Telegram
- Threads

Можешь выбрать несколько.»

→ `subject.platforms_primary`

### Вопрос 3: Primary язык
«На каком языке primary content?
- RU
- EN
- Both (bilingual)»

→ `subject.primary_language` + `subject.bilingual_always`

Если both - bilingual_always=true.

### Вопрос 4: Ниша / тема экспертизы
«Опиши коротко: какой ты эксперт, для какой аудитории, чему обучаешь?»

→ `subject.niche`

### Вопрос 5: Brand visual identity
«Опиши твой визуальный стиль если есть:
- Палитра (основные цвета) - hex или описание
- Шрифт-семьи (sans / serif / mono / display)
- Эстетика (minimalist / editorial / playful / corporate / brutalist)

Если ничего нет - скажу «нет» и стартую с базового minimalist setup.»

→ `visual_identity.palette_primary` + `visual_identity.typography` + `visual_identity.aesthetic_principles`

### Вопрос 6: Reference creators
«Кого ты considers reference в visual style для image posts?
Назови 3-5 имён которых стиль тебе нравится (X handle / IG handle / website).

Если не знаешь - пропусти, я подскажу типовые reference creators для твоей ниши.»

→ `reference_creators` per type (skill manage matching после этого вопроса)

### Вопрос 7: Aspect default
«Какие aspect ratios тебе нужны в основном?
- 1:1 (square) - X / TG / general
- 4:5 (vertical) - Нельзяграм feed
- 1.91:1 (landscape) - LinkedIn feed
- 9:16 (story) - Stories / Reels

Можешь выбрать несколько.»

→ `aspect_defaults` per platform

### Вопрос 8: Tool stack
«Что используешь для создания картинок?
- AI generation: Higgsfield / Midjourney / DALL-E / другое
- Manual composition: Figma / Canva / Photopea / Photoshop
- Screenshots: CleanShot / ShareX / native
- Memes: Canva / Photopea / Procreate

Если не определился - дефолтю на самый общедоступный (Photopea + Canva).»

→ `tool_stack`

### Вопрос 9: Путь к Карте смыслов
«Если у тебя идёт запуск, укажи путь к Карте смыслов:
- `.business/запуски/<active-launch>/5.2-Карта-смыслов.md` (если ты используешь launch-methodology автора)
- Свой путь
- Нет / не идёт запуск (Mode A отключим, останутся Mode B и C)»

→ `paths.content_map` + `active_launch`

## После 9 вопросов

1. **Запиши** config.md из ответов (overwrite если был incomplete)
2. **Сообщи** автору: «Onboarding завершён. Config сохранён в `~/.claude/skills/single-image/config.md`. Можешь редактировать вручную для тонкой настройки.»
3. **Покажи** первые 3 пути которые точно надо заполнить:
   - `paths.avatar` (если не указал)
   - `paths.brand_guidelines` (если не указал)
   - `examples/gold-standard-<name>.md` (если есть готовые примеры)
4. **Спроси** хочет ли пользователь сразу запустить первый brief или подготовить контекст сначала.

## Defaults для skip-ов

Если автор пропустил вопрос - дефолты:
- Q2 platforms: ["X", "TG"]
- Q3 language: ru, bilingual_always: false
- Q5 visual: Ivan's default palette (ink/paper/blue accent) + Inter typography + minimalist
- Q6 references: автоматически назначаются typovые per type из knowledge/reference-creators.md
- Q7 aspect: 1:1 default
- Q8 tools: Photopea + Canva (free baseline)
- Q9 content_map: null (Mode A disabled)

## Validation после onboarding

Запустить L1 sanity check:
- config.md frontmatter valid
- subject.name заполнен
- subject.primary_language ∈ [ru, en, both]
- paths.avatar или указатель на null
- visual_identity.palette_primary имеет >=2 цвета
- tool_stack заполнен

Если что-то fail - сказать пользователю что не валидно и предложить fix.
