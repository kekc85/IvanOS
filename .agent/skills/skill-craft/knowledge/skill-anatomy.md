# Skill anatomy: как устроен Claude Code skill

Best practices по Anthropic Skills docs + опыт построения skills для проектов автора.

## Структура папки

```
~/.claude/skills/<name>/
├── SKILL.md                 # ОБЯЗАТЕЛЬНО: главный файл с frontmatter + триггерами
├── knowledge/               # ОПЦ: статические факты, методологии (читается по запросу)
│   ├── <topic-1>.md
│   └── <topic-2>.md
├── prompts/                 # ОПЦ: исполняемые шаблоны / алгоритмы / процедуры
│   ├── 01-<task>.md
│   └── 02-<task>.md
└── examples/                # ОПЦ: реальные кейсы, audit reports, track records
    ├── <example-1>.md
    └── track-record-<name>.md
```

## SKILL.md anatomy

### Frontmatter (обязательно)

```yaml
---
name: <kebab-case-slug>           # совпадает с именем папки (case-sensitive)
version: "X.Y"                    # SemVer, в кавычках
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
review_deps_every: <N months>     # для skills с фиксированными deps версиями
description: |
  80-500 символов. Что skill делает + триггеры. LLM использует description
  для решения "применять или нет". Если короче 80 - LLM не поймёт когда.
  Если длиннее 500 - шумно, плохо ранжируется.
---
```

### Body структура (рекомендуется)

```markdown
# Название skill - короткий tagline

> Опц.: причина создания, история, контекст

## Когда применять

Триггеры:
- "фраза 1" / "phrase 1"
- "фраза 2"
- `/slash-command <args>`

## [Workflow / Режимы / Что делает]

Конкретные шаги. Если 1 режим - inline. Если 2+ - выделить в подразделы.

## Knowledge base / Prompts (если есть подпапки)

- `knowledge/X.md` - что там
- `prompts/<другое-имя>.md` - что там (условное имя)

## Принципы

1-7 явных принципов работы skill.

## Anti-patterns (опц., но рекомендуется)

Что **НЕ** делать. Часто полезнее чем «что делать».

## Memory cross-refs

- `[[feedback-X]]` - связанное правило
- `[[other-skill]]` - параллельный или вызываемый skill

## Версия

История изменений, SemVer правила, когда ревизия.
```

## Когда выносить в knowledge/ vs prompts/ vs inline

| Что | Куда |
|---|---|
| Workflow одного режима (1-2 страницы) | inline в SKILL.md |
| Workflow 2+ режимов / много шагов | `prompts/0X-<mode>.md` |
| Статические факты, таблицы, нормы, законы | `knowledge/<topic>.md` |
| Executable LLM-judge template | шаблон судьи в `prompts/` (нумерация по порядку фаз) |
| Шаблон выходного артефакта | `prompts/0X-<artifact>-format.md` |
| История применений + catch rate | `examples/track-record-<name>.md` |

Принцип: **SKILL.md = карта**, prompts/knowledge = детали. Если SKILL.md > 250 строк - время выносить.

## Триггеры в description

Минимум 3-5 разных фраз для покрытия:
- Разные формулировки задачи: «создай», «сделай», «помоги с»
- Slash-command: `/skill-name`
- Доменные термины из задачи
- Английские + русские если bilingual

Дискриминативность: проверить что description явно отличается от соседних skills в namespace. Например `frontend-design` vs `visual-concept-square` - разные scopes.

## Anti-patterns при создании skill

1. **Ad-hoc вместо industry standards**: если для класса задач есть готовый stack (pytest / Sentry / OpenAI Evals) - не выдумывай свой.
2. **Module-level state** в prompts: «загрузи это, потом сделай X» - prompts должны быть idempotent.
3. **Hardcoded имена пользователя** в universal skill: «помоги автору с X». Используй роли («помоги пользователю»), не персон.
4. **Описание без триггеров**: description без явных фраз - LLM не знает когда применять.
5. **Дублирование с другими skills**: перед созданием - проверить нет ли уже похожего. Если есть - расширить existing, не плодить.
6. **Em-dash «—» внутри строк**: только в начале bullet-списка (см. memory `[[feedback-no-em-dash]]`).
7. **Persona-specific без declaration**: если skill только под автора - явно в description «для проектов автора», иначе он включится у любого.
8. **Большой SKILL.md без выноса**: > 250 строк inline - выносить в knowledge/prompts.
9. **Broken cross-refs**: `prompts/<имя>.md` который не существует (X.md здесь - условное имя, не реальный файл). Перед commit прогон L1.5 placeholder-aware check.

## Anthropic Skills best practices

Источник: https://docs.claude.com (Skills docs)

1. **Progressive disclosure** - не дамп всего контента в context, скилл указывает «детали см. в `prompts/<имя>.md`» (условное имя).
2. **Hierarchical loading** - SKILL.md первым, остальное по нужде.
3. **Idempotent prompts** - повторный вызов даёт тот же результат при тех же входах.
4. **Composable** - skill может вызывать другие skills через `[[name]]` references.
5. **No external state in skill files** - все state в файлах проекта или памяти, не в skill.

## Reference

- `prompts/01-build-new-skill.md` - пошаговый процесс build
- `prompts/02-run-full-audit.md` - audit после build
- Anthropic docs: https://docs.claude.com (Skills)
- Track record как метрика: `prompts/04-update-track-record.md`