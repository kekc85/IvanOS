# Update track record

После каждого реального применения skill — обновить `examples/track-record-<skill>.md`. Это empirical мера эффективности skill и обратная связь для улучшения qa-skill методологии.

## Формат файла `examples/track-record-<skill_name>.md`

```markdown
# Track record: <skill_name>

История реальных применений skill, что поймано / пропущено.

## Применение N — YYYY-MM-DD: <короткое описание контекста>

**Контекст:** какая задача, какой проект, какая цель применения skill

**Что поймал skill:**
- bug N1 категории `permissions`: краткое описание
- bug N2 категории `encoding`: краткое описание
- ...

**Что пропустил skill (выявилось позже):**
- bug N3 категории `<category>`: краткое описание + когда выявилось + почему пропустил
- ...

**Уроки для улучшения skill:**
- ...

**Уроки для улучшения qa-skill методологии:**
- Например: «L4 не покрывал категорию X, добавить в bug-categories.md»
```

## Когда обновлять

1. **Сразу после применения** (часть выходных артефактов audit'а)
2. **Когда выявился пропущенный bug позже** — добавить в существующее application с timestamp

## Пример

Файл `examples/track-record-qa-process.md`:

```markdown
# Track record: qa-process

## Применение 1 — 2026-05-22: TG-бот uniqalizer-bot после рефактора

**Контекст:** Применил qa-process v1.0 к боту после фикса bind mount. Сказал «всё ОК».

**Что поймал skill:**
- 22 em-dash в SKILL.md самого qa-process (через qa-skill audit)
- Пустая папка stacks/ — удалена
- Версия не указана в frontmatter

**Что пропустил skill (выявилось позже):**
- 2026-05-22 19:47 UTC, через 9 часов после «готово»: PermissionError на новых файлах от контейнера. Категория: `permissions / bind mount`. Не покрыта в universal checklist v1.0.

**Уроки:**
- v1.1: добавить Post-deploy active probe (live tail logs + docker exec touch → host cat)
- v1.1: добавить Regression test для каждого fix
- qa-skill v1.1: добавить `bug-categories.md` matrix с категорией `Permissions / bind mount` обязательной для TG-bot skill type
```

## Метрика эффективности skill

```
catch_rate = bugs_caught / (bugs_caught + bugs_missed)
```

Над временем track record должен показать рост catch_rate. Если падает или плато — пора пересматривать методологию.