# Режим D: Description optimization (против undertriggering)

Description во frontmatter — главный механизм, решающий, вызовет ли Claude скилл. Болячка моделей — **undertriggering**. Запускать ПОСЛЕ того, как скилл доведён и юзер согласен с его качеством. Теория — `knowledge/eval-iteration-loop.md` §4.

## Шаг 1. 20 trigger-эвалов
- **8-10 should-trigger:** разные формулировки одного интента (casual/formal), без явного имени скилла/типа файла, плюс редкие юзкейсы и кейсы конкуренции с другим скиллом, где этот должен победить.
- **8-10 should-NOT-trigger:** **near-miss** — делят ключевые слова со скиллом, но реально нужен другой инструмент (самые ценные). НЕ делать очевидно-нерелевантные («напиши fibonacci» для PDF-скилла — ничего не проверяет).

Запросы конкретные и реалистичные: пути файлов, имена компаний, URL, бэкстори, иногда lowercase/опечатки/аббревиатуры, разная длина. Фокус на edge-кейсах.

Формат:
```json
[{"query": "…", "should_trigger": true}, {"query": "…", "should_trigger": false}]
```

## Шаг 2. Ревью с юзером
`references/eval_review.html` — заменить плейсхолдеры:
- `__EVAL_DATA_PLACEHOLDER__` → JSON-массив эвалов (без кавычек — это присваивание JS-переменной)
- `__SKILL_NAME_PLACEHOLDER__` → имя скилла
- `__SKILL_DESCRIPTION_PLACEHOLDER__` → текущий description

Записать в `/tmp/eval_review_<skill>.html`, `open` его. Юзер правит/тоглит/добавляет → «Export Eval Set» → `~/Downloads/eval_set.json` (взять самый свежий). Плохие эвалы → плохой description, поэтому шаг важен.

## Шаг 3. Петля оптимизации (фон)
```bash
python -m scripts.run_loop \
  --eval-set <path>/eval_set.json \
  --skill-path <skill> \
  --model <model-id-текущей-сессии> \
  --max-iterations 5 --verbose
```
Делит 60/40 train/test, гоняет каждый запрос 3× (надёжный trigger-rate), итеративно предлагает улучшения description, выбирает `best_description` по **held-out test** (анти-оверфит). Периодически тейлить лог, давать юзеру апдейты по итерациям/скорам.

## Шаг 4. Применить
Взять `best_description` из JSON-вывода → обновить frontmatter SKILL.md (правка SKILL.md в `~/.claude/skills/` идёт под hard-gate hook — этот Режим уже внутри skill-craft, гейт пройден). Показать юзеру before/after + скоры.

## Замечание про механику
Claude зовёт скилл только для НЕтривиальных задач. Простой одношаговый запрос может не триггернуть даже при идеальном description. Поэтому тест-запросы должны быть содержательными.

## Claude.ai
Требует `claude -p` (только Claude Code) — на Claude.ai пропустить, оптимизировать description вручную по принципам «pushy + near-miss-aware».