---
name: skill-craft
version: "1.0"
created: 2026-05-22
description: Создание, аудит, эмпирическая итерация и оптимизация триггеринга Claude Code skills. Build - методология нового skill (структура, frontmatter, prompts, knowledge, triggers). Audit - 7-уровневая проверка по индустриальным стандартам (Anthropic Skills best practices + OpenAI Evals + LangSmith). Eval-iteration - доказать ценность скилла поверх baseline (with-skill vs without-skill, assertions, benchmark, human review, improve). Description-optimization - поднять точность триггеринга (trigger-эвалы should/should-not + train/test). Триггер по фразам "создай skill", "новый skill", "проверь skill", "audit skill", "протестируй skill", "сделай evals для skill", "почему skill не триггерится", "оптимизируй description", "/skill-craft <name>".
---

# Skill-craft: создание и аудит Claude Code skills

Один skill закрывает две задачи: **создать** новый skill правильно + **проверить** его качество. Применять при создании нового skill (или правке существующего).

## Когда применять

Триггеры:
- "создай skill <name>" / "новый skill"
- "проверь skill <name>" / "audit skill"
- "правильно ли я сделал skill"
- `/skill-craft create <name>` - режим build
- `/skill-craft audit <name>` - режим audit
- `/skill-craft <name>` - auto-detect (если skill уже существует - audit, если нет - build)

## Два режима

### Режим A: BUILD (создание нового skill)

См. `prompts/01-build-new-skill.md` - пошаговая методология:

1. **Определить scope** - какую задачу skill решает, какие триггеры
2. **Frontmatter** - name, description 80-500, version, created, last_reviewed
3. **Структура** - когда inline в SKILL.md, когда выносить в knowledge/ / prompts/
4. **Body** - Core principles → workflow → anti-patterns → reference
5. **Cross-refs** - `[[other-skill]]` ссылки, memory правила
6. **Sanity check** - прогнать через L1 audit сразу (deterministic)
7. **Track record init** - создать пустой `examples/track-record-<name>.md` для будущих применений

После build - обязательно прогон Режима B (audit) на свежесозданный skill.

### Режим B: AUDIT (проверка существующего skill)

См. `prompts/02-run-full-audit.md` - 7-уровневая проверка:

1. **L1 Structural** - frontmatter, файлы, refs (детерминированно через grep/regex)
2. **L2 Content** - полнота, достоверность, актуальность + **LLM-as-judge** через `prompts/03-llm-judge-template.md`
3. **L3 Trigger** - покрытие фраз, дискриминативность с другими skills
4. **L4 Workflow** - все режимы покрыты + **bug-categories matrix** из `knowledge/bug-categories.md`
5. **L5 E2E** - active dispatch simulation + bug-hunt с троянским input
6. **L6 Safety** - этика, privacy, prompt injection, дисклеймеры
7. **L7 Maintenance** - SemVer, точки устаревания, modular structure

Каждый уровень → PASS / WARN / FAIL. Отчёт по `prompts/07-report-format.md` в `examples/audit-<name>-<date>.md`.

После audit - обязательно `prompts/04-update-track-record.md` для накопления catch_rate metric.

### Режим C: EVAL-ITERATION (доказать ценность поверх baseline)

См. `prompts/05-eval-iteration.md` + теория `knowledge/eval-iteration-loop.md`. Поглощено из официального Anthropic `skill-creator` (2026-05-31). Закрывает дыру: audit проверяет *устройство*, но не доказывает, что скилл **реально лучше голой модели**.

Петля: 2-3 реалистичных тест-промпта → параллельно `with_skill` + baseline (`without_skill` для нового / `old_skill`-снапшот для правки) → assertions → grade → benchmark (pass_rate ± stddev, токены, время, дельта) → human review через `eval-viewer/generate_review.py` → improve → повторять. Готовые скрипты в `scripts/`, agent-промпты в `agents/`, схемы в `references/schemas.md`.

**Решающее правило:** скилл оправдан только если with_skill ощутимо > baseline при приемлемой добавке токенов/времени. Дельта ≈ 0 → урезать или убить.

### Режим D: DESCRIPTION-OPTIMIZATION (против undertriggering)

См. `prompts/06-description-optimization.md`. Description — главный механизм триггеринга; болячка моделей — undertriggering. 20 trigger-эвалов (should-trigger разными формулировками + should-NOT-trigger near-miss) → ревью через `references/eval_review.html` → `python -m scripts.run_loop` (60/40 train/test, 3× прогон, выбор `best_description` по held-out test) → применить во frontmatter. Запускать после доводки качества скилла.

## Knowledge base

- `knowledge/skill-anatomy.md` - как устроен skill, что куда класть, best practices Anthropic
- `knowledge/methodology.md` - детали 7-уровневой методологии audit
- `knowledge/bug-categories.md` - matrix категорий багов per skill type (для L4)
- `knowledge/execution-planning.md` - **NEW v1.1** для content-driven / research-heavy skills: сколько агентов запускать, параллель vs последовательно, QA gate 3 слоя
- `knowledge/eval-iteration-loop.md` - **NEW v1.4** теория Режимов C+D: baseline-сравнение, эмпирическая петля, benchmark, improve-философия (4 принципа), механика триггеринга. Поглощено из Anthropic skill-creator

## Prompts

- `prompts/01-build-new-skill.md` - пошаговая методология BUILD режима
- `prompts/02-run-full-audit.md` - полный алгоритм AUDIT режима (7 уровней)
- `prompts/03-llm-judge-template.md` - executable LLM-judge prompt для L2 семантической оценки
- `prompts/04-update-track-record.md` - формат track-record-<skill>.md, catch_rate metric
- `prompts/05-eval-iteration.md` - **NEW v1.4** исполняемый Режим C (эмпирическая итерация с baseline)
- `prompts/06-description-optimization.md` - **NEW v1.4** исполняемый Режим D (оптимизация триггеринга)
- `prompts/07-report-format.md` - формат итогового markdown-отчёта audit

## Bundled tooling (NEW v1.4 — из Anthropic skill-creator)

- `scripts/` - исполняемые python-скрипты (`python -m scripts.<name>` из корня skill-craft): `aggregate_benchmark`, `run_loop` (description optimization), `run_eval`, `improve_description`, `quick_validate`, `package_skill`, `generate_report`
- `eval-viewer/generate_review.py` - HTML-вьюер результатов прогонов (qual outputs + quant benchmark) для human review
- `agents/` - промпты спец-сабагентов: `grader.md` (оценка assertions), `analyzer.md` (анализ benchmark), `comparator.md` (слепое A/B версий)
- `references/schemas.md` - JSON-схемы evals/grading/benchmark; `references/eval_review.html` - форма ревью trigger-эвалов

## Self-test (false positives)

При прогоне skill-craft через себя - детекторы покажут "находки" которые false positive:
- **TODO/placeholder** в methodology.md - термины для проверки **других** skills
- **Имена пользователя** (автор) в шаблонах - не реальная привязка
- **Em-dash** в цитатах находок из проверяемых skills

При интерпретации self-test - учитывать контекст: упоминание термина в методологии ≠ наличие проблемы.

## Принципы

1. **Build перед audit** - сначала методология создания (раздел anatomy), потом проверка.
2. **Use industry standards** - Anthropic Skills best practices, prompt engineering literature, standard QA. Не выдумывай.
3. **Deterministic where possible** - L1/L3 через grep/regex без LLM (быстрее, дешевле, надёжнее).
4. **LLM-as-judge для semantic** - L2/L5 неизбежно требуют LLM-оценки. Используем явный template.
5. **Reproducible reports** - каждый audit в `examples/audit-<skill>-<date>.md`. История важна.
6. **Track record как метрика качества** - catch_rate (поймано / пропущено) ведём для каждого skill применения. Цель ≥80%.
7. **Не пропускать L6** - safety важнее перфоманса.
8. **Доказывать ценность поверх baseline (v1.4)** - скилл не «выглядит ок», а эмпирически > goloй модели (Режим C). Дельта ≈ 0 → урезать/убить.
9. **Объяснять ЗАЧЕМ, а не давить MUST/ALLCAPS (v1.4)** - модели умные; жёсткие `ALWAYS`/`NEVER` капсом = жёлтый флаг, переформулируй с причиной. Этот принцип сознательно мягче исторического MUST-heavy стиля skill-craft; при конфликте побеждает «explain why». Генерализуй, не оверфить под тест-кейсы; держи промпт lean; повторный код между прогонами → в `scripts/`.

## Версия методологии

**Текущая:** 1.4 (2026-05-31) - поглощён официальный Anthropic `skill-creator`. Добавлены Режим C (EVAL-ITERATION: with_skill vs baseline → assertions → benchmark pass_rate±stddev/токены/время → human review через eval-viewer → improve) и Режим D (DESCRIPTION-OPTIMIZATION: 20 trigger-эвалов should/should-not near-miss + run_loop 60/40 train/test → best_description по held-out). Bundled: `scripts/` (aggregate_benchmark / run_loop / run_eval / quick_validate / package_skill / improve_description), `eval-viewer/`, `agents/` (grader / analyzer / comparator), `references/schemas.md` + `eval_review.html`. Knowledge `eval-iteration-loop.md`, prompts `05-eval-iteration.md` + `06-description-optimization.md`. Принципы 8 (доказывать поверх baseline) + 9 (explain-why вместо MUST-heavy — сознательное смягчение прежнего стиля). Закрывает gap: audit проверяет устройство, но не доказывает реальную ценность и надёжность триггеринга.

**Предыдущая 1.3:** (2026-05-28 evening) - добавлены protections для visual-first skills после прецедента `carousel` disaster: Step -4 Visual Reference Capture (сохранять user-provided screenshots как files), Step 0.7 Pattern Inheritance Check (axis match: artifact_type / platform / language), Step 8.5 + L8 Visual Quality Gate (side-by-side LLM judge output vs anchors), bug-categories VG-A...VG-G (7 visual-first categories) + PIB-1 (cross-type pattern copy anti-pattern). Закрывает gap: deterministic L1-L7 PASS не равно visual quality PASS для visual-first skills.

**Предыдущая 1.2:** (2026-05-28) - добавлен content-skill раздел в `knowledge/bug-categories.md` (13 новых категорий: Voice fidelity regression / Lexicon drift / Source data staleness / Hook strength subjectivity / Cross-skill config conflicts / Track-record bloat / Mandatory Reads missing / Description length out of Anthropic range / Source-of-truth DEPRECATED / Banned terms FALSE POSITIVE / Platform×format compatibility / Generic AI listing artefact / Em-dash metadata vs output). Контекст: прецедент 9 content-skills семейства по решению автора.

**Предыдущая 1.1:** (2026-05-27) - добавлены pre-build стадии для content-driven / research-heavy skills (Step -3 Context map / Step -2 Research scope / Step -1 Execution planning / Step 0.5 QA gate) + `knowledge/execution-planning.md`. Контекст: прецедент `post` по решению автора.

**Предыдущая 1.0:** (2026-05-22) - merge `qa-skill` v1.2 + новая build-методология.

**SemVer правила:**
- MAJOR: breaking change в формате отчёта или критериях PASS/FAIL
- MINOR: новый режим, новый уровень (L8+), новый шаблон prompts
- PATCH: уточнение критериев, новые категории в bug-categories.md, fix broken refs

**Когда пересматривать:**
- Новые best practices от Anthropic / OpenAI
- catch_rate в track-record падает < 80%
- Систематические gap'ы при audit реальных skills
- Раз в 6 месяцев минимум

## Memory cross-refs

- `[[feedback-deep-review-discipline]]` - не «всё ОК» без e2e на реальном кейсе
- `[[feedback-use-industry-standards-not-invent]]` - готовые stacks, не ad-hoc
- `[[вайбкодинг]]` - параллельный skill для приложений/ботов (не для skills)

## История слияния

- Предки: `qa-skill v1.2` (полностью включён)
- Build-часть добавлена 2026-05-22 как новый компонент
- `qa-skill` удалён как отдельный skill после merge