# 00-onboarding-student.md - First-run onboarding для ученика курса

Срабатывает при отсутствии или неполном `config.md`. Создаёт config через 9 вопросов.

## Когда триггерится

- `config.md` отсутствует (свежий clone skill'а)
- `config.subject.name` пуст или = "автор" (значит default, не student)
- User явно вызвал `/tweet --onboard` или «настрой tweet под меня»

## 9 questions (sequential через AskUserQuestion если VS Code, иначе plain text list)

### Q1 - Имя автора
```
Как тебя зовут? (отображается в config, нужно для context чтения)
```

### Q2 - X handle (опционально)
```
Твой X (Twitter) handle? Если ещё нет - пиши "нет".
Examples: <твой-хэндл>_x / @username
```

### Q3 - Threads handle (опционально)
```
Твой Threads (Meta) handle? Если ещё нет - пиши "нет".
```

### Q4 - Language default
```
Основной язык контента?
- ru (русский)
- en (english)
- both (если планируешь оба, default ru, флаг --en для переключения)
```

### Q5 - Market
```
Какой рынок?
- ru
- en
- both
```

### Q6 - Категория (1-2 термина)
```
Какой твой method / category? 1-2 термина которыми ты называешь свой подход.
Examples: "вайбмаркетинг", "вайбкодинг + вайбмаркетинг", "AI-маркетинг для коучей", "no-code SaaS"
```

### Q7 - Product focus (одна строка)
```
Какой основной outcome для аудитории? Одна строка.
Example: "первый цифровой продукт + первая монетизация через клуб для новичков с экспертизой"
```

### Q8 - Primary voice register
```
Какой основной голос на X? Выбери один:
- build-in-public  (Levels / Marc Lou / Friks - daily MRR / metric / "shipped X today")
- paips-story      (Welsh - Pain-Agitate-Insight-Positive personal stories)
- spiky            (Hormozi / Sanchez - punchy contrarian one-liners)
- aphorism         (Naval / Iman - compressed identity bombs)
- idea-drop        (Isenberg / Bloom - daily framework / startup idea posts)
```

### Q9 - Где лежат файлы проекта
```
Где у тебя живёт контекст? (avatar / brand-dna / products)
- .business/         (как у автора)
- intake/            (legacy folder)
- custom path        (укажи свой)
- ничего нет        (создадим placeholder structure)
```

## Step 2 - Generate config.md

После 9 ответов - generate `~/.claude/skills/tweet/config.md` с заполненными полями (см. `config.md` template).

## Step 3 - Generate placeholder intake structure (если Q9 = "ничего нет")

Create:
```
~/intake/
├── avatar.md          (placeholder для ICP)
├── jtbd.md            (placeholder для JTBD)
├── brand-dna.md       (placeholder для voice)
└── products/          (empty dir)
```

С template structure и instructions.

## Step 4 - Onboarding complete

```
✓ Config saved: ~/.claude/skills/tweet/config.md
✓ Intake structure ready (if needed)
✓ Skill ready

Запуск:
  /tweet                - Plan mode (из Карты смыслов)
  /tweet про X          - Spark-B1 (idea expansion)
  /tweet --spark        - Spark-B2 (idea generation)
  /tweet <надиктовка>   - Transcript mode

Дальше: добавь 5-10 своих лучших постов в examples/gold-standard-<your-name>.md для voice match.
```

## Anti-patterns onboarding

- НЕ ask 20+ questions - 9 enough
- НЕ default'ить voice register без явного выбора (определяет всё)
- НЕ копировать автора `paths` в ученика config (custom paths)
- НЕ создавать `.business/` у ученика (`intake/` legacy folder cleaner)