# Execution planning для content-driven / research-heavy skills

Методология как ЭФФЕКТИВНО решать research-задачу: сколько агентов, что параллельно, какие зависимости, какой QA — чтобы быстро прийти к результату без потери качества.

## Когда применяется

Skill зависит от:
- Industry best practices research
- Voice/style modeling от чужого корпуса (gold-standard)
- Multi-author / multi-domain знаний синтеза
- Open-ended discovery паттернов из внешних источников

**Примеры:** `post`, `linkedin-post`, `paips-post`, `ivan-voice`, market-research skills.

**НЕ применяется** для tool wrappers (`ui-record`, `uniqalizer-bot`), pure computation, deterministic CLI tasks.

## Зачем

Линейный single-thread research занимает 4-6 часов. Параллельные агенты — 20-40 минут + QA. Speedup 4-6x БЕЗ потери качества — если briefs precise.

Параллель вводит координационные риски: дубли работы, неконсистентные форматы, скрытые зависимости, quality drift между агентами. Нужен явный план.

## Методология (6 фаз)

### Фаза 1: Decomposition

Разбить research scope на независимые buckets:
- По геогрaphy (RU / EN / другие)
- По tier (primary / secondary / framework lookup)
- По типу источника (channels / books / encoded skills)
- По похожести авторов (группируй похожих в один bucket = один context для агента)

**Target bucket size:** 3-6 объектов per агент. Меньше = overhead. Больше = context overflow + потеря фокуса.

### Фаза 2: Dependency analysis

Для каждого bucket пометь:
- **BLOCKS** — bucket который должен завершиться до этого (например, «сначала найти автора X, потом его исследовать»)
- **CAN PARALLEL** — независимые buckets

Если нет blocks — всё в параллель.

### Фаза 3: Agent brief (обязательные поля)

Каждый agent brief ДОЛЖЕН содержать:

1. **Bucket scope** — какие конкретно объекты
2. **Pipeline per item** — пошаговая процедура (например, Step 1 search готовой систематизации → Step 2 разбор если нет)
3. **Output format** — фиксированный schema с конкретными полями
4. **Anti-patterns** — что считается провалом (например, «anti-vagueness — вербатим цитаты обязательны»)
5. **Anti-scope** — что НЕ делать
7. **Summary at end** — что собрал, чего не хватило

Без любого поля — agent выдаст generic результат.

### Фаза 4: Launch

`run_in_background: true` для всех параллельных агентов в одном tool_use block. Ждать notifications, НЕ поллить.

Максимум **5-6 параллельных** — больше теряет track. Если объектов больше — bucket до 6 items в одном агенте.

### Фаза 5: QA gate (3 слоя) — ОБЯЗАТЕЛЬНО перед synthesis

**Слой 1 — Валидаторы (deterministic, regex/grep):**
- Anti-vagueness check: нет «классный пост» / «хороший framework» без вербатим + конкретных параметров
- Source citations: URL + дата для каждого claim
- Schema compliance: все поля per format заполнены
- Anti-scope соблюдён

**Слой 2 — 4 концепции (LLM-judge):**
- Pre-mortem 5 причин провала research
- Calibrate confidence 90% на каждый вывод
- Multi-perspective (3+ angles на один data point)
- Adaptive (новый finding от одного агента интегрирован в interpretation других)

**Слой 3 — 7 контуров:**
- Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность

Если слой не пройден где-то — **relaunch specific agent(s) с правленым брифом**, не весь research. Документировать причину в `audit-{date}.md`.

### Фаза 6: Synthesis

Только после QA gate — strategy synthesis на валидированных данных.

## Speed expectations

| Подход | Wall-clock | Quality |
|---|---|---|
| Serial single-thread (10 RU + 10 EN + Ivan) | 4-6 hours | Высокий, но медленно |
| Parallel 5-agent (buckets 3-5 items) | 20-40 min + 10-15 min QA + 30-60 min synthesis | Высокий при precise briefs |
| Parallel 10+ agents (too granular) | 30-50 min, но lost track | Quality drift |

Sweet spot: **5 параллельных агентов** с 3-6 объектами в bucket.

## Прецеденты провалов (что не повторять)

1. **Reels precedent (2026-05):** агенты вернули «классный пост» / «nice motion» без semantic richness. Результат: UI выглядел generic. **Fix:** anti-vagueness как HARD rule в brief (вербатим первая строка + 9 параметров + конкретный архетип).

2. **<конкурент> precedent (2026-05-27):** использован устаревший reference потому что не проверил `.business/` сначала. **Fix:** всегда читать существующие `.business/` lists перед добавлением references.

3. **Over-parallelization:** запустил 10 агентов, потерял track. **Fix:** max 5-6 параллельных.

4. **Mid-stream brief changes:** relaunch агента с другим брифом mid-flow ломает comparison. **Fix:** lock brief перед launch; если меняется — kill all и restart.

5. **Промис без действия:** обещал внести правки в skill-craft и не внёс . **Fix:** каждое обещание в чате → Edit/Write СРАЗУ, не потом.

## Cross-refs

- `[[feedback-parallel-agents]]` — для 3+ однотипных независимых задач — параллельные Agent-инстансы
- `[[feedback-systemic-process-fails-motion]]` — pre-render checklist 7 items, обязательно
- `[[feedback-self-eval-not-qa]]` — никогда не отчитываться «fidelity X» без visual verification
