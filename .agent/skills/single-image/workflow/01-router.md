# Workflow 01: Router

Точка входа для skill. Определяет mode + subject + загружает config.

## Шаги

### Step 1: Load config

```bash
CONFIG_PATH="$HOME/.claude/skills/single-image/config.md"
```

Если config отсутствует или incomplete → запустить `00-onboarding-student.md`. После onboarding продолжить с Step 2.

Прочитать:
- `subject.*` (name / platforms / language / niche)
- `paths.*` (avatar / Карта смыслов / brand_dna)
- `visual_identity.*` (palette / typography / aesthetic)
- `aspect_defaults.*`
- `tool_stack.*`
- `lexicon_banned_hard` + `lexicon_required`
- `output.*`

### Step 2: Auto-detect mode

| Signal в user input | Mode |
|---|---|
| `/single-image` без аргументов | Plan |
| «по плану», «смысл дня», явная дата | Plan |
| `/single-image про X`, «сделай картинку про X», «визуализируй X», «framework X» | Spark-B1 |
| «дай идеи картинок», «что визуализировать сегодня», «5 идей картинок» | Spark-B2 |
| Текст >500 знаков с пометкой «для картинки» / «надиктовал» | Transcript |

**Override flags** (если присутствуют):
- `--plan` → force Plan
- `--spark` → force Spark
- `--transcript` → force Transcript
- `--type=<concept-diagram|dashboard-screenshot|meme|quote-card|before-after>` → force type, skip 02-finalize type selection
- `--platform=<X|LinkedIn|Instagram|TG|Threads>` → force platform
- `--aspect=<1:1|4:5|1.91:1|9:16>` → force aspect
- `--language=<ru|en|both>` → force caption language (default: both per config)

### Step 3: Detect subject

Subject = `config.subject.name`. Если автор - всё стандартно. Если ученик - убедиться что онboarding пройден и examples/gold-standard-<name>.md существует (если нет - WARNING but continue).

### Step 4: Route to mode file

| Mode | Next file |
|---|---|
| Plan | `01a-plan.md` |
| Spark-B1 (расширение идеи) | `01b-spark.md` (Mode B1 section) |
| Spark-B2 (генерация идей) | `01b-spark.md` (Mode B2 section) |
| Transcript | `01c-transcript.md` |

### Step 5: Output структура для downstream

После route, mode-файл возвращает:
```
{
  mode: "plan|spark-b1|spark-b2|transcript",
  topic: "<concrete topic / intent>",
  hints: {
    type_suggestion: "<один из 5 типов или null>",
    platform_suggestion: "<X|LI|IG|TG или null>",
    reference_creator: "<имя или null>",
  },
  source_context: "<откуда взяли topic - Карта смыслов файл / user input / transcript цитата>"
}
```

Дальше идёт в `02-finalize.md`.

## Edge cases

- **Несколько topics в одном запросе** → ask user clarify какой topic primary
- **Тоник на 2+ языках** → принять, в 04-caption генерим оба
- **User спрашивает «что лучше для X»** → не router, это help-mode, отвечать в чате без запуска workflow
- **Mode не определяется** → ask user явный mode через one of 3
- **Несколько overrides конфликтуют** (--plan + --transcript) → error, ask пользователь выбрать один

## Logging

Записать в memory сессии (не файл):
- Detected mode
- Override flags
- Subject (автор / ученик-X)
- Topic

Это для review stage чтобы видеть откуда что пришло.