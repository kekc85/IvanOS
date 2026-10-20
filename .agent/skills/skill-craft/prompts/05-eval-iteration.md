# Режим C: Eval-iteration loop (эмпирическая итерация с baseline)

Запускать после BUILD (Режим A) или при правке существующего скилла, когда нужно ДОКАЗАТЬ, что скилл добавляет ценность, а не просто «выглядит ок». Полная теория и философия — `knowledge/eval-iteration-loop.md`. Это исполняемый чек-лист.

> Не использовать `/skill-test` или иные тест-скиллы. Это одна непрерывная последовательность — не останавливаться посередине.

## Шаг 0. Тест-кейсы
2-3 РЕАЛИСТИЧНЫХ промпта (как реальный юзер напишет, с деталями: пути, имена, контекст). Показать юзеру: «вот кейсы, ок или добавить?». Сохранить в `evals/evals.json` (только промпты, assertions позже). Схема — `references/schemas.md`.

## Шаг 1. Параллельный запуск with_skill + baseline (в одном ходу)
Воркспейс: `<skill>-workspace/iteration-N/eval-<имя>/`. Имя evalʼа — описательное.

- **with_skill:** сабагент с `Skill path`, сохранить в `…/with_skill/outputs/`.
- **baseline:**
  - новый скилл → `without_skill` (тот же промпт, без скилла).
  - правка → снапшот ДО правок (`cp -r <skill> <ws>/skill-snapshot/`), baseline целит в снапшот, сохранить в `…/old_skill/outputs/`.

Запускать ОБЕ ветки сразу. На каждый eval — `eval_metadata.json` (`eval_id`, `eval_name`, `prompt`, `assertions:[]`).

## Шаг 2. Пока бегут — набросать assertions
Объективно проверяемые, с понятными именами (читаются в viewer). Субъективные скиллы (стиль/дизайн) — не насиловать assertions, оценивать качественно. Обновить `eval_metadata.json` + `evals/evals.json`.

## Шаг 3. Поймать тайминг
Из notification каждого сабагента сразу в `timing.json`: `{total_tokens, duration_ms, total_duration_seconds}`. Другого источника нет.

## Шаг 4. Grade → aggregate → viewer
1. **Grade:** сабагент читает `agents/grader.md`, оценивает assertions → `grading.json` (поля строго `text`/`passed`/`evidence`). Где можно — скриптом, не на глаз.
2. **Aggregate:** `python -m scripts.aggregate_benchmark <ws>/iteration-N --skill-name <name>` → `benchmark.json`+`benchmark.md` (pass_rate, токены, время, mean±stddev, дельта). with_skill перед своим baseline.
3. **Analyst pass:** по `agents/analyzer.md` — недискриминирующие assertions, flaky evalʼы, trade-off время/токены.
4. **Viewer:** `nohup python eval-viewer/generate_review.py <ws>/iteration-N --skill-name "<name>" --benchmark <ws>/iteration-N/benchmark.json > /dev/null 2>&1 &` (итерация 2+ → `--previous-workspace <ws>/iteration-N-1`; headless/cowork → `--static <out.html>`). Сказать юзеру: две вкладки — Outputs (кликать кейсы + фидбэк) и Benchmark.

## Шаг 5. Прочитать feedback
Когда юзер сказал «готово» — читать `feedback.json`. Пустой фидбэк = ок. Чинить там, где конкретные претензии. Убить вьюер (`kill $VIEWER_PID`).

## Шаг 6. Improve (по 4 принципам из knowledge)
Генерализуй не оверфить · держи lean (читай транскрипты, не только output) · объясняй ЗАЧЕМ вместо MUST/ALLCAPS · повторный код между прогонами → вынести в `scripts/`. Применить правки → новая `iteration-N+1` → повторять, пока юзер доволен / фидбэк пуст / прогресса нет → расширить тест-сет на масштабе.

## Решающее правило
Скилл оправдан, только если with_skill ощутимо > baseline по качеству/pass_rate при приемлемой добавке токенов/времени. Дельта ≈ 0 → урезать или убить скилл.

## Claude.ai / без сабагентов
Петля та же, но прогон один-за-другим самим, без параллельного baseline и quant-benchmark; упор на human review.

После Режима C — предложить Режим D (`prompts/06-description-optimization.md`).