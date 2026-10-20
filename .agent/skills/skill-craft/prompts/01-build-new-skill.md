# BUILD-режим: пошаговое создание нового skill

Используется когда пользователь говорит «создай skill <name>» или skill ещё не существует.

## Pre-build стадии для text-skills (NEW 2026-05-31 — ОБЯЗАТЕЛЬНО если skill производит текст для аудитории)

**Triggers:** skill производит публикуемый текст (пост / письмо / карусель-копия / твит / пуш / сценарий / caption / лендинг-копия).

### Step T-1: Mastery research + обогащение (ОБЯЗАТЕЛЬНО)

Перед сборкой text-skill — найти тематический mastery и подключить его по `mastery/PROTOCOL.md`:
1. Есть ли `mastery/<область>/` под задачу скилла (текст → `mastery/copywriting/`; продажи → `mastery/sales/`; и т.д.)?
2. **Есть** → скилл обязан вызывать линзу мастеров (Inventory ВСЕХ авторов → Select → Apply → Evidence Report → независимый верификатор).
3. **Нет или неполон** → ДО сборки скилла **дополнить мастера**: web-ресёрч ключевых концепций области, создать/обогатить файлы авторов (1-3 применимых метода каждый, по `mastery/README.md`), затем подключить.
4. Сами методы мастеров использовать при проектировании скилла (структура хука, оффера, удержания).

### Step T-2: Context-gap + humaniser gates (ОБЯЗАТЕЛЬНО)

Любой новый text-skill обязан вшить два общих гейта (idempotent скрипт):
```
bash ~/.claude/skills/_shared/scripts/inject-mastery-context-gate.sh <name>   # context-gap + mastery
bash ~/.claude/skills/_shared/scripts/inject-humaniser-gate.sh <name>          # финальный humaniser
```
- **Context-gap** (`_shared/context-gap-gate.md`): нет реального контекста (цифры/инфоповоды/новости/цены/кейс) → СПРОСИТЬ автора/пользователя списком, НЕ выдумывать. Память `feedback_ask_for_missing_context_never_invent`.
- **Mastery** (`_shared/mastery-gate.md`): линза мастеров + Evidence + верификатор. Память `feedback_mastery_real_application_with_verification`.
- **Humaniser** — финальная антиклише-фаза.

Без T-1 + T-2 text-skill считается недоделанным (L4/L6 audit FAIL).

---

## Pre-build стадии для visual-first skills (NEW v1.3 — ОБЯЗАТЕЛЬНО если artifact_type=visual)

**Triggers:** Skill produces visual output (PNG / PDF / image / video frame / composition).

Примеры: `carousel`, `single-image`, `video` (с visual brief), `produce-reel`, `motion-storyboard`.

### Step -4: Visual Reference Capture (ОБЯЗАТЕЛЬНО)

Перед research / design / template build — собрать **реальные image files** как visual anchors.

**Источники:**
1. **User-provided screenshots** в первом сообщении / context — СОХРАНИТЬ КАК ФАЙЛЫ немедленно. Не текстовое описание. Файлы.
2. **WebFetch viral examples** — если research включает competitor analysis, screenshot saving обязательно (не только URL bookmarking)
3. **Brand library existing assets** — copy в anchors для brand consistency reference

**Сохранять в:**
```
~/.claude/skills/<name>/visual-anchors/
  ├── reference-1-<creator>-<date>.png
  ├── reference-2-<creator>-<date>.png
  └── manifest.md  (что откуда + что копировать / что НЕ копировать per anchor)
```

**Manifest format:**

```markdown
# Visual Anchors Manifest

## reference-1-socialeaver-2026-05-28.png
- Source: пользовательский скриншот в чате 2026-05-28
- Author: @socialeaver (RU IG)
- What to copy: panorama hero image 70% area, typography overlay strong contrast zone
- What NOT to copy: specific хамелеон as subject, blue CTA button styling
- Category: IG mobile carousel hook, panorama family

## reference-2-...
```

**GATE:** Step -3 (Context map) не начинается без минимум 3 visual anchors сохранены.

### Step 0.7: Pattern Inheritance Check (NEW v1.3)

Перед designing template / structure — explicit check откуда наследуется pattern и совпадают ли axis.

```yaml
inheriting_from:
  skill: "<other skill name>"
  artifact_type: "<text-content | visual-first | action | mixed>"
  platform: "<TG / IG / LinkedIn / X / email>"
  language_native: "<RU / EN / mixed>"

axis_match_check:
  artifact_type: <self.artifact_type> == <inheriting.artifact_type>?
  platform: native of inheriting platform applies to self?
  language: same language paradigm?

verdict:
  - PASS = full inheritance OK
  - PARTIAL = inherit structure, override implementation details for diff axis
  - FAIL = mismatch in 2+ axes, do NOT inherit, design from scratch
```

**Прецедент:** carousel v1.0 inherited от post (text-content / TG / RU) для visual-first / IG mobile / RU - 2 axes mismatch. PIB-1 anti-pattern. Catastrophic result.

### Step 8.5: Visual Quality Gate (L8) - pre-publish gate (NEW v1.3)

После build / before declare ready - обязательный L8 audit для visual-first skills.

См. `knowledge/methodology.md` L8 раздел. Требует:
1. Минимум 1 рендеренный output
2. Visual anchors из Step -4 загружены
3. LLM judge side-by-side compare
4. Verdict PASS / WARN / FAIL

**FAIL = skill НЕ готов. Rebuild templates / asset pipeline / pattern inheritance, не косметика.**

---

## Pre-build стадии (для content-driven / research-heavy skills)

**Эти стадии ОБЯЗАТЕЛЬНЫ перед Шагом 0 Scope**, если skill зависит от:
- Industry best practices research
- Voice/style modeling от чужого корпуса (gold-standard)
- Multi-author знаний синтеза
- Open-ended discovery паттернов

Примеры: `post`, `linkedin-post`, `paips-post`, voice-modeled skills.

**НЕ применяется** для tool wrappers (`ui-record`, `uniqalizer-bot`), pure computation, deterministic skills — для них пропускаем pre-build и идём сразу на Шаг 0.

Детальная методология execution: см. `knowledge/execution-planning.md`.

### Step -3: Context map

Очертить контекст задачи: какие каналы / периоды / роли в воронке / частоты / цели. Без гипотез про конкретные решения.


### Step -2: Research scope definition

Определить ДО запуска research:

1. **Критерии отбора объектов** — мотивация/модель автора, не просто «большой блогер». Сигналы фильтра + анти-сигналы.
2. **Список кандидатов** — фильтрован через критерии. Перед добавлением RU-имён обязательно `Read .business/marketing/competitors.md` и `Read .business/запуски/.../2-Конкуренты.md`. Не выдумывать заново.
3. **Параметры разбора per object** — для семантической детализации против Reels-антипаттерна (например, 9 параметров для контент-постов: hook / context / archetype / drama / value / CTA / length / formatting / specific tricks).
4. **Анти-скоуп** — что НЕ берём.
5. **Расширенное «готовое»** — не только закодированные skills. Любая систематизация: newsletter / paid course / book / framework thread / podcast interview / encoded skill / awesome-list / NotebookLM template / GPTs prompt.
6. **Output формат** — per-object dossier по фиксированному schema.


### Step -1: Execution planning

Определить ДО запуска research:

1. **Decomposition в buckets** (3-6 объектов per bucket). Группировка по geography / tier / source type / author similarity.
2. **Dependency analysis** — что BLOCKS, что CAN PARALLEL. Default — параллель для независимых.
3. **Agent brief schema** — каждый bucket → один agent в фоне со своим brief. Brief ОБЯЗАН содержать: bucket scope / pipeline per item / output format / anti-patterns / anti-scope / save path / summary.
4. **Параллелизм** — `run_in_background: true` для всех. Max 5-6 параллельных. Ждать notifications, не поллить.
5. **QA gate plan** (см. Step 0.5 ниже).

Speedup expectation: 4-6x vs serial single-thread. См. `knowledge/execution-planning.md` секция Speed expectations.

### Step 0 (research execution): Industry research

Launch агентов параллельно по плану из Step -1. Wait notifications.

### Step 0.5: QA gate (3 слоя) — ОБЯЗАТЕЛЬНО перед synthesis

**Слой 1 Валидаторы (deterministic):**
- Anti-vagueness: нет «классный пост» / «good framework» без вербатим + конкретных параметров
- Source citations: URL + дата для каждого claim
- Schema compliance: все поля per format
- Anti-scope соблюдён

**Слой 2 4 концепции (LLM-judge):**
- Pre-mortem 5 причин провала
- Calibrate confidence 90%
- Multi-perspective 3+ angles
- Adaptive integration findings

**Слой 3 7 контуров:**
- Context / Соответствие / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность

Если слой не пройден — relaunch specific agent(s) с правленым брифом, не весь research.


### Step 1: Strategy synthesis

На основе валидированного research → architecture decision → состав v1.

Артефакт: `plans/{date}-{skill-slug}-spec.md`. Согласование с пользователем по логике (бьётся ли с видением рынка).

---

## Шаг 0: Scope

Прежде чем писать SKILL.md - ответить на 5 вопросов:

1. **Какую задачу skill решает?** Одной фразой.
2. **Когда срабатывает?** 3-5 типичных триггер-фраз.
3. **Кто пользователь?** Universal (любой) или personal (под автора). Это влияет на description и приёмы.
4. **Какой output?** Markdown отчёт / отредактированный код / отправленное сообщение?
5. **Какой artifact_type?** (**NEW v1.2** - предотвращает класс ошибок fact invention)
   - **action** - output служит обещанием к non-reversible action подписчика / зрителя. Каждый факт = публичное обещание. Нужны 5 mandatory gates (см. `knowledge/bug-categories.md` раздел «Категории для action skills»). Примеры: bot-message, email, carousel-announce, longform-promo.
   - **stylistic** - output = opinion / take / story. Truth не требует verify. Примеры: paips-post, spiky-one-liner, post-narrative.
   - **mixed** - часть output action, часть stylistic. Применить gates только к action-частям, явно отделить в workflow.

Если на любой из 5 вопросов ответ «не знаю» - не писать SKILL.md, сначала уточнить с пользователем.

Записать `artifact_type` в frontmatter `metadata:` (см. Шаг 2).

## Шаг 1: Проверка дубликатов

```bash
ls ~/.claude/skills/
# Прочитать descriptions всех skills, найти близкие по scope
for s in ~/.claude/skills/*/SKILL.md; do
    grep '^description:' "$s" | head -1
done
```

Если близкий skill уже есть - **расширить его**, не создавать дубликат. Дубликаты ломают триггеринг (LLM не знает какой выбрать).

## Шаг 2: Создать папку и SKILL.md

```bash
SKILL_NAME="<kebab-case-name>"
mkdir -p ~/.claude/skills/$SKILL_NAME
```

Минимальный SKILL.md (см. `knowledge/skill-anatomy.md` полный шаблон):

```markdown
---
name: <skill_name>
version: "1.0"
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
description: <80-500 chars: что делает + триггеры>
---

# <Skill name> - короткий tagline

## Когда применять

Триггеры:
- "фраза 1"
- "фраза 2"
- `/<name>` (если slash-command)

## Что делает

[Workflow или режимы]

## Принципы

1. ...

## Anti-patterns

- ...

## Memory cross-refs

- `[[feedback-X]]`
```

## Шаг 3: Решить структуру

| Размер skill | Структура |
|---|---|
| Простой, 1 режим, 50-150 строк | всё inline в SKILL.md |
| Средний, 2-3 режима, 200-400 строк | SKILL.md + 1-3 prompts/ файла |
| Большой, 5+ режимов, knowledge base | SKILL.md + prompts/ + knowledge/ + examples/ |

Принцип: SKILL.md = карта. Если SKILL.md > 250 строк - выносить.

## Шаг 4: Body

Заполнить секции:

- **Core principles** (3-7 явных правил)
- **Workflow / Режимы** (конкретные шаги, inputs, outputs)
- **Anti-patterns** (что НЕ делать, часто полезнее чем «что делать»)
- **Memory cross-refs** ([[feedback-X]] правила которые применяются)

Для каждого workflow - чек: есть ли вход, шаги, выход, error handling, hand-off (когда нужен человек)?

## Шаг 5: Cross-refs и параллели

- Если есть параллельные skills (которые делают похожее в другой области) - явно сказать в SKILL.md.

## Шаг 6: L1 sanity check (deterministic из audit)

Сразу после черновика SKILL.md прогнать:

```bash
# Frontmatter валиден
python3 -c "
import re
with open('~/.claude/skills/$SKILL_NAME/SKILL.md') as f:
    fm = re.match(r'^---\n(.*?)\n---', f.read(), re.DOTALL)
print('OK' if fm else 'FAIL')
"

# Em-dash в строках (memory feedback-no-em-dash)
grep -n '—' ~/.claude/skills/$SKILL_NAME/SKILL.md | grep -v -E '^\s*[0-9]+:\s*[-*+]\s*—' | wc -l
# Должно быть 0

# Жаргон / англицизмы
grep -i 'grand slam\|fast-action\|digital-twin' ~/.claude/skills/$SKILL_NAME/SKILL.md
# Должно быть пусто

# Длина description
python3 -c "
import re
with open('~/.claude/skills/$SKILL_NAME/SKILL.md') as f:
    fm = re.match(r'^---\n(.*?)\n---', f.read(), re.DOTALL).group(1)
d = re.search(r'^description:\s*(.+)$', fm, re.M).group(1)
print(f'description len: {len(d)}')
assert 80 <= len(d) <= 500
"
```

## Шаг 7: Track record init

```bash
mkdir -p ~/.claude/skills/$SKILL_NAME/examples
touch ~/.claude/skills/$SKILL_NAME/examples/track-record-$SKILL_NAME.md
```

Содержимое начального файла:

```markdown
# Track record: <skill_name>

История реальных применений для оценки эффективности.

## Применение 0 - <date>: создание skill

Skill создан. Прогонов в проде пока 0.
Цель catch_rate для первых 5 применений: ≥80%.
```



## Шаг 7.5: Humaniser injection (MANDATORY для text-content skills, NEW 2026-05-28)

Если skill - text-content (производит текстовый output: посты / письма / скрипты / описания / captions) - **ОБЯЗАТЕЛЬНО** inject humaniser final pass:

```bash
bash ~/.claude/skills/_shared/scripts/inject-humaniser-gate.sh <new-skill-name>
```

Script идемпотентный (если уже есть - skip). Patches:
- `workflow/04-review.md` (если есть) ИЛИ
- `workflow/03-write.md` (fallback) ИЛИ
- `workflow/05-publish.md` (fallback) ИЛИ
- `prompt.md` (single-file skills) ИЛИ
- `SKILL.md` (inline skills)

Без этой инъекции skill будет выдавать AI-generic - 12 категорий AI-tics не отфильтрованы (triple-negation parallel emphasis / voice-signature theft / ложная глубина / etc). Прецедент: post v3.0 (2026-05-28) выдал «Zero ads. Zero funnels. Zero sales calls.» = triple-negation AI tic = опознано автором моментально.

**Verification:**
```bash
grep -rl "humaniser" ~/.claude/skills/<new-skill-name>/ | wc -l
# Должно быть ≥1
```

**Когда применять:**
- post / tweet / longform / email / bot-message - HARD requirement
- single-image / carousel - HARD requirement (caption part)
- pisatel-* - уже включают по умолчанию (автор при сборке)
- video / scripts - HARD requirement (генерируют разговорный текст)
- НЕ требуется для tool-wrappers (ui-record / yt-dlp wrappers / etc - они не генерируют текст)

## Шаг 8: Обязательный AUDIT после build

После build - **сразу** перейти к режиму AUDIT через `prompts/02-run-full-audit.md`.
Найденные L1-L7 findings - исправить, не закрывать build пока audit не зелёный.

## Шаг 9: Memory index update

Добавить в `~/.claude/projects/<твой-проект>/memory/MEMORY.md` строку про новый skill если он:
- Личного типа (под автора)
- Содержит важные правила работы

Format:
```
- [<Skill name>](file_to_relevant_memory.md) - одна строка о том что skill даёт
```

## Anti-patterns при создании

См. `knowledge/skill-anatomy.md` секция «Anti-patterns при создании skill» (9 пунктов).

Главное:
1. Не выдумывать stack - использовать industry standards
2. Не плодить дубликаты
3. Не пропускать L1 sanity check перед коммитом
4. Не закрывать build без обязательного audit прогона