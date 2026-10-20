# L2 LLM-as-judge template (v1.2)

Используется в Шаге 2.2 из `01-run-full-audit.md`. Это actually-executable prompt, не декларация.

## Когда применять

После того как deterministic L2 checks (grep TODO/em-dash/конкуренты) прошли — обязательно прогнать LLM-judge для semantic gaps.

## Как применять

1. Прочитать SKILL.md + все prompts/*.md + все knowledge/*.md аудируемого skill.
2. Прочитать `~/.claude/projects/<твой-проект>/memory/MEMORY.md` index — выяснить применимые feedback правила.
3. Прочитать `~/.claude/skills/qa-skill/knowledge/bug-categories.md` — выяснить bug categories обязательные для типа skill.
4. Применить prompt ниже как mental check (или в отдельной Claude-сессии для независимости).

## Prompt

```
ROLE: Ты независимый аудитор Claude Code skill. Оценил структуру через deterministic
checks (см. L1) — теперь нужна семантическая оценка качества.

ARTIFACT: <name skill> — содержимое всех файлов прилагается ниже.

USER CONTEXT: пользователь = автор, его персональные правила в memory:
- feedback-no-em-dash: «—» только в начале bullet, не в строке
- feedback-no-tech-jargon: запрет на «артефакт/контур/grand slam» в публичных текстах
- feedback-no-attacking-competitors-by-name: имена конкурентов в публичной части запрещены
- feedback-deep-review-discipline: не говорить «всё ОК» без e2e на реальном кейсе
- feedback-apply-qa-process-after-vibecoding: qa-process обязательно после прод-кода
- feedback-verify-via-api-not-user-clicks: проверять через psql/curl, не дёргать UI
- feedback-post-deploy-active-probe: после deploy live tail logs + docker exec test
(полный список ~/.claude/projects/<твой-проект>/memory/MEMORY.md)

CRITERIA — отвечай YES/NO с reasoning по каждому:

1. **Полнота режимов**: каждый workflow из SKILL.md имеет соответствующий prompt-файл с
   inputs / шагами / outputs? Какие missing?

2. **Active vs snapshot probes**: skill использует «watch logs N минут» / «verify by reading
   logs of real request» — или ограничивается snapshot («последние 30 строк ОК = готово»)?
   Snapshot-only без active probe = important finding.

3. **Coverage по bug-categories**: для типа skill (TG-бот / Frontend / Backend / CLI / ETL)
   упомянуты ли категории из `~/.claude/skills/qa-skill/knowledge/bug-categories.md`?
   List какие отсутствуют.

4. **Достоверность фактов**: версии пакетов реалистичные? Имена сервисов корректные?
   Числа разумные? Нет ли явных галлюцинаций?

5. **Memory alignment**: skill соответствует каждому feedback-* правилу пользователя?
   List каких нарушает (включая «промпт даёт примеры вместо полного текста» / «em-dash в
   строке» / «упоминает конкурента по имени» / итд).

6. **Universal vs personal**: skill явно объявляет тип (personal под автора / universal)?
   Если universal — нет ли привязки к одному пользователю? Если personal — заявлено ли
   в description?

7. **Decision branching полнота**: каждая if/then ветка имеет ответ для каждого исхода?
   Есть ли «если ни X ни Y — что делать?» без ответа?

8. **Hand-off clarity**: где skill требует решение человека — это явно обозначено?
   (Например «спросить пользователя» / «эскалировать юристу» / «согласовать с владельцем»).

9. **Tone match**: tone соответствует ожиданиям пользователя? Не слишком ли formal /
   informal / маркетинговый / технический для контекста?

10. **Track record check** (для skills с реальными применениями): прочитать
    `examples/track-record-<skill>.md`, если есть. Что пропустил skill в прошлых
    применениях? Учтены ли уроки в текущей версии?

OUTPUT: для каждого критерия — PASS / WARN / FAIL + 1-2 предложения reasoning.
В конце — общий вердикт по semantic quality.
```

## Как использовать output

Каждый WARN/FAIL из LLM-judge → finding в L2 отчёта с severity:
- FAIL → critical / important
- WARN → important / minor

Если LLM-judge противоречит deterministic checks (например grep нашёл «артефакт», но LLM-judge говорит «это технический термин в QA-контексте, false positive») — LLM-judge выигрывает с пометкой «false positive детектора, suggest update regex».

## История применений

При каждом запуске LLM-judge — записать в `examples/llm-judge-runs.md` дату, аудируемый skill, ключевые findings. Это позволит улучшать сам template со временем.