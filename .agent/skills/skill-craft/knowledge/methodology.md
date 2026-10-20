# QA-Skill: 7-уровневая методология тестирования скиллов

Полная методология построена на индустриальных стандартах:

- **Anthropic Skill best practices** (структура, frontmatter, hierarchical loading)
- **OpenAI Evals framework** (eval definitions, accuracy / regression tests)
- **LangSmith Evaluation** (LLM-as-judge, dataset-based testing)
- **Microsoft Promptflow** (prompt evaluation pipelines)
- **Standard software QA** (unit, integration, e2e, regression, security)
- **ISTQB QA principles** (test independence, defect clustering, exhaustive testing impossible)

## Уровень L1: Structural Integrity (детерминированные проверки)

**Цель:** убедиться что скилл вообще может загрузиться и не сломан технически.

**Что проверяется:**

1. **Папка существует** в `~/.claude/skills/<name>/` или `<project>/.claude/skills/<name>/`
2. **SKILL.md существует** на верхнем уровне папки
3. **YAML frontmatter валиден:**
   - Открывается и закрывается `---`
   - Парсится как YAML
   - Содержит обязательное поле `name`
   - Содержит обязательное поле `description`
   - `name` совпадает с именем папки (case-sensitive)
4. **Description адекватная:**
   - Не пустая
   - Не одно слово
   - Содержит триггеры (фразы которые ожидаемо запустят скилл)
   - Длина 80-500 символов (короче - LLM не поймёт когда применять, длиннее - шумно)
5. **Все referenced файлы существуют:**
   - Каждая ссылка на `knowledge/X.md` в SKILL.md → проверить что `knowledge/X.md` есть
   - Каждая ссылка вида `prompts/<имя>.md` → проверить наличие файла
   - Каждая ссылка на `examples/X.md` → проверить наличие
6. **Markdown структура:**
   - Заголовки (H1, H2) расставлены
   - Нет битых markdown-ссылок
   - Нет незакрытых code-fence блоков
7. **Размер файлов разумный:**
   - Не пустые (< 100 байт = подозрительно)
   - Не слишком огромные (> 50 КБ для одного файла = пересмотреть структуру)

**Инструменты:** Bash (find, grep, wc), Python (yaml parsing, regex)

**Время выполнения:** ~30 секунд

**Возможные результаты:**
- ✅ PASS - всё на месте
- ⚠️ WARN - есть мелкие огрехи (длина description выходит за рекомендуемые рамки, файл подозрительно маленький)
- ❌ FAIL - есть критические нарушения (нет SKILL.md, невалидный YAML, битые ссылки)

## Уровень L2: Content Quality (LLM-as-judge или ручная)

**Цель:** убедиться что содержание скилла качественное, актуальное, полное и тонально соответствует пользователю.

**Что проверяется:**

1. **Полнота покрытия:**
   - Все режимы / sub-tasks описаны
   - Нет "TODO" / "todo" / "[заполнить]" / "..." вместо контента
   - Каждый prompt-файл имеет понятные инструкции
   - Knowledge базы содержат фактические данные, не placeholder
2. **Достоверность фактов:**
   - Цифры (ставки, лимиты, штрафы) актуальны на момент создания
   - Ссылки на законы, статьи, нормы корректны
   - Нет очевидных галлюцинаций
3. **Актуальность:**
   - Если упоминаются даты - они реалистичные
   - Если есть нормы которые могут устареть - есть пометка "проверять на актуальность"
4. **Стиль и тон:**
   - Соответствует user preferences (см. user memories)
   - Например для пользователей с правилом "no em-dash" - проверить отсутствие em-dash внутри строк
5. **Universal vs personal:**
   - Если скилл универсальный - нет жёсткой привязки к одному пользователю (имени, проекту, бизнесу)
   - Имена ролей, не персон ("Руководитель проекта", не "автор")
6. **Memory alignment:**
   - Если есть relevant feedback memories пользователя - они учтены
   - Например feedback "не использовать em-dash" → проверить
7. **Cross-skill consistency:**
   - Не дублирует функциональность других скиллов
   - Если ссылается на другие knowledge bases (например `materials/legal-pack/`) - они существуют

**Инструменты:** grep, Read, Claude как judge (для семантической оценки), сверка с memories пользователя

**Время выполнения:** ~3-5 минут (с LLM-judge)

## Уровень L3: Trigger Engineering

**Цель:** убедиться что description правильно срабатывает на типичные пользовательские формулировки.

**Что проверяется:**

1. **Описание содержит триггеры:**
   - "Use when..." / "Когда срабатывать..." / "Trigger when..."
   - Минимум 3-5 типичных фраз
2. **Покрытие формулировок:**
   - Тестовые входы (10-15 типичных формулировок задачи)
   - Для каждой - предположение: должен ли скилл сработать?
   - Match expected vs actual (через симуляцию: подать input в Claude и спросить какой скилл подходит)
3. **Дискриминативность:**
   - Скилл не путается с другими скиллами в namespace
   - Если есть похожие скиллы (например `frontend-design` и `visual-concept-square`) - description чётко разделяет
4. **Анти-фразы (negative tests):**
   - Несколько фраз которые НЕ должны запустить скилл
   - Проверка что description не overfits и не запускается на не своей теме
5. **Локализация:**
   - Если скилл для пользователей которые говорят по-русски - description содержит русские триггеры
   - Если для EN - английские
   - Если bilingual - оба

**Тест-датасет (минимум):**

```yaml
positive_tests:
  - "помоги с возвратом ученика"          # → должен сработать
  - "обработай возврат"                    # → должен сработать
  - "пришёл клиент с возвратом"            # → должен сработать
  - "сделай юр.документы"                  # → должен сработать
  - "/yurist"                              # → должен сработать
  - "audit my landing page"                # → должен сработать?

negative_tests:
  - "напиши пост в Twitter"                # → НЕ должен сработать
  - "сделай Reels"                         # → НЕ должен сработать
  - "помоги с маркетингом"                 # → НЕ должен сработать
```

**Инструменты:** Симуляция через Claude API или ручной прогон

**Время выполнения:** ~5 минут

## Уровень L4: Workflow Coverage

**Цель:** убедиться что workflow покрывает все реалистичные ситуации и не оставляет пользователя без инструкций.

**Что проверяется:**

1. **Все режимы прописаны от старта до финиша:**
   - Каждый workflow имеет вход (initial trigger / inputs)
   - Каждый имеет выход (final output / artifact / hand-off)
   - Нет логических разрывов
2. **Edge cases покрыты:**
   - Что если input неполный?
   - Что если пользователь меняет mind в середине?
   - Что если несколько режимов конфликтуют?
3. **Error handling:**
   - Что делать если внешний tool не отвечает (Playwright не подключился)?
   - Что если URL невалидный?
   - Что если запрашиваемый файл не существует?
4. **Hand-off points:**
   - Когда нужен человек (Руководитель / юрист / специалист)?
   - Чётко обозначены ли точки эскалации?
5. **Decision branching:**
   - Если есть условные ветки (если X то Y) - все ветки имеют продолжение
   - Нет "если ни X ни Y - что делать?" без ответа

**Инструменты:** Чтение prompts, проверка логических связок

**Время выполнения:** ~3 минуты

## Уровень L5: End-to-End Simulation

**Цель:** убедиться что скилл работает на реальном (или близком к реальному) input.

**Что проверяется:**

1. **Симуляция каждого режима:**
   - Сгенерировать realistic test input
   - "Запустить" скилл в воображении (или реально - подать в Claude отдельную сессию)
   - Оценить output
2. **Критерии оценки output:**
   - Релевантность (отвечает ли скилл на input?)
   - Полнота (все ли требуемые поля заполнены?)
   - Корректность (нет ли явных ошибок?)
   - Tone (соответствует ожидаемому?)
3. **Time to complete:**
   - Сколько шагов?
   - Сколько вопросов задаёт пользователю?
   - Не слишком ли длинно?
4. **No hallucinations:**
   - Output не выдумывает факты которых нет в knowledge base
   - Если нет данных - честно говорит "у меня нет этой информации"
5. **Real-world example check:**
   - Если в examples/ есть кейсы - воспроизвести их через скилл
   - Output должен сходиться с записанным результатом

**Инструменты:** Manual review кейсов из examples/, опционально - отдельная Claude-сессия для симуляции

**Время выполнения:** ~5-10 минут на режим

## Уровень L6: Safety & Compliance

**Цель:** убедиться что скилл не нанесёт вреда пользователю или третьим лицам.

**Что проверяется:**

1. **Этические границы:**
   - Скилл отказывается от заведомо вредоносных запросов?
   - Если есть dual-use функции (например "аудит сайта" может быть для атаки на конкурента) - есть ли защита?
2. **Privacy:**
   - Если работает с чувствительными данными (ПДн, финансы, медицина) - есть ли требование на согласие?
   - Не сохраняет ли данные сверх необходимого?
3. **Compliance с законами:**
   - Для юр.скиллов: соответствуют ли советы актуальному законодательству?
   - Есть ли дисклеймер "не юридическая консультация"?
4. **Дисклеймеры:**
   - Где скилл выдаёт material advice (юр./медицинский/финансовый) - есть ли disclaimer?
   - Где есть риск ошибки (например генерация юр.документов) - есть ли рекомендация review у профессионала?
5. **Prompt injection resistance:**
   - Если скилл принимает user input (URL, текст, файлы) - не уязвим ли к injection-атакам?
   - Например audit-скилл принимающий URL - проверяет ли что URL не является `javascript:alert()` или подобным?

**Инструменты:** Review SKILL.md и prompts на наличие safety paragraphs, тест adversarial inputs

**Время выполнения:** ~5 минут

## Уровень L7: Maintenance & Sustainability

**Цель:** убедиться что скилл можно поддерживать и обновлять долго.

**Что проверяется:**

1. **Версионность:**
   - Есть ли дата последнего обновления?
   - Помечены ли данные которые могут устареть (например "актуально на 2026 год")?
2. **Documentation для будущих обновлений:**
   - Описано ли где искать факты которые могут измениться?
   - Например для юр.скилла: где смотреть актуальные ставки УСН, нормы 152-ФЗ?
3. **Точки устаревания:**
   - Идентифицированы ли разделы которые особенно подвержены устареванию?
   - Например cheatsheet с конкретными статьями законов - чётко помечен?
4. **Modular structure:**
   - Если что-то изменится - сколько файлов придётся править?
   - Если изменение одного факта требует правки в 10 местах - bad maintainability
5. **Backwards compatibility:**
   - Если скилл обновляется - не сломает ли это существующих сценариев использования?
6. **Examples freshness:**
   - Когда были обновлены examples?
   - Не устарели ли в them конкретные цифры?
7. **🔴 Холистический ripple-review при ЛЮБОЙ правке существующего скилла/воркфлоу (ОБЯЗАТЕЛЬНО).**
   - Правка одной фазы/секции НЕ оценивается в вакууме. Скилл — единая система: фазы взаимозависимы (выход одной = вход другой, общие артефакты типа Design.md, общие инструменты, сквозные гейты).
   - После правки фазы N прогнать **ripple-чек по ВСЕМ остальным фазам**: (а) не дублирует ли правка то, что уже делает другая фаза? (б) не противоречит ли порядку/гейтам? (в) не обещает ли то, что фаза-исполнитель ниже не вывозит (стек/движки)? (г) не осиротел ли вход/выход смежной фазы? (д) согласованы ли названия/артефакты сквозь фазы?
   - Кросс-скилл: задеты ли другие скиллы, которые этот вызывает/которые вызывают его.
   - Прецедент по решению автора: точечные правки Фазы 4 website создали 5 рассогласований с Фазами 2/5/6/7 (дубли, рассинхрон эффектов, дыра mastery), видимые только при взгляде на весь процесс.
   - Отчитываться автору по правке скилла = всегда в связке «как это влияет на весь процесс», не по одной фазе.

**Инструменты:** Read review (ВСЕ фазы, не одна), git log (если репо)

**Время выполнения:** ~3 минуты (+ ripple-review всех фаз)

## Уровень L8: Visual Quality Gate (NEW v1.3 — ОБЯЗАТЕЛЬНО для artifact_type=visual)

**Цель:** убедиться что визуальный output skill сопоставим по качеству с reference visuals (конкуренты / brand examples). Не deterministic checks - реальная визуальная категория.

**Срабатывает только если** `artifact_type=visual` или `mixed` (содержит visual output).

**Pre-requisite:** visual anchors сохранены в `skill/visual-anchors/` или `skill/references/visual-anchors/` (см. bug-categories.md VG-A / Pre-build Step -4).

**Что проверяется:**

1. **Reference parity gate:**
   - Скилл render'нул минимум 1 актуальный output (PNG / PDF / frame)
   - Перед declaring «test passed» - запущен side-by-side compare с anchors
   - LLM judge получает: output_image + 3-5 anchor images + criteria list
   - Output: PASS (same category) / WARN (mostly category, mild deviation) / FAIL (different category)

2. **Hero element check:**
   - Output содержит hero visual element (photo / screenshot / scene / illustration) занимающий ≥40% area
   - Pure typography = FAIL (если только family declared как document-format)

3. **Real elements visibility:**
   - Real product names / numbers / UI screenshots визуально присутствуют (≥40% slides если applicable)
   - Не только в schema / brief, а physically в rendered output

4. **Generic AI tells check:**
   - Output не падает в banned imagery patterns (gradient blobs / generic icons / AI-illustrated office people)
   - Проверка против `references/banned-ai-imagery.md` если есть, иначе baseline checklist

5. **Brand consistency:**
   - Output использует brand colors / typography / signature elements из config
   - Не generic Canva template aesthetic

**LLM judge prompt template:**

```
You are visual quality judge for content carousel/image skill.

ANCHORS (these are reference visuals user has marked as target quality):
[Embed 3-5 anchor images]

SKILL OUTPUT:
[Embed rendered output]

CRITERIA:
1. Same visual category as anchors? (typography role / image role / layout zones)
2. Hero element present and dominant (>=40% area)?
3. Real elements physically visible (not just claimed in brief)?
4. No generic AI tells (gradient blobs / stock illustrations / AI-people-in-office)?
5. Brand consistency with config.brand?

For each: PASS/WARN/FAIL with 1-line reasoning.

Final verdict:
- PASS: All 5 PASS or 4 PASS + 1 WARN
- WARN: 3 PASS + 2 WARN, or 4 PASS + 1 FAIL on non-critical
- FAIL: Any FAIL on criteria 1 (category mismatch) OR criteria 2 (no hero) OR >=2 FAILs
```

**Failure handling:**

Если L8 = FAIL → НЕ declare skill ready. Required actions:
- Identify which criteria failed
- Map to bug-categories VG-A...VG-G
- Apply fix at root cause level (templates / asset pipeline / pattern inheritance)
- Re-render → re-run L8

**Manual confirmation override:**

LLM judge может ошибаться (visual subjectivity). User может override: explicit «PASS confirmed» в chat → record decision в track-record. Но default = trust judge, override = exception.

**Инструменты:** Read (images), LLM-as-judge (vision-capable model), bash compose для side-by-side preview

**Время выполнения:** ~3-5 минут (зависит от количества anchors + LLM call)

**Возможные результаты:**
- ✅ PASS — visual quality в категории anchors
- ⚠️ WARN — близко но есть deviation, можно ship с пометкой
- ❌ FAIL — не та категория, rebuild template / asset pipeline

**Прецедент:**

- **2026-05-28: carousel v1.0/v1.1.** L1-L7 все PASS. L8 не существовал. Output = generic agency 2018. User diagnoz «хуже чем GPT default». После introduction L8: side-by-side с user anchors (socialeaver / divyannshisharma / aykhanium) - FAIL на criteria 1 (category mismatch) + 2 (no hero) + 3 (no real elements visible).

## Итоговый отчёт

После прохождения всех 7 уровней - сводный отчёт:

| Уровень | Статус | Находок | Критичных |
|---|---|---|---|
| L1 Structural | PASS/WARN/FAIL | N | M |
| L2 Content | ... | ... | ... |
| L3 Trigger | ... | ... | ... |
| L4 Workflow | ... | ... | ... |
| L5 E2E | ... | ... | ... |
| L6 Safety | ... | ... | ... |
| L7 Maintenance | ... | ... | ... |

**Общий вердикт:**
- ✅ READY TO PUBLISH - все PASS, может быть WARN на L7
- ⚠️ NEEDS FIXES - есть WARN на L2-L6 или FAIL на L7
- ❌ NOT READY - есть FAIL на L1-L5
- 🚨 DANGEROUS - есть FAIL на L6 (нельзя использовать как есть)

Полный пример отчёта - см. `examples/audit-yurist-2026-05-21.md`.

## Принципы методологии

1. **Exhaustive testing impossible.** Невозможно протестировать каждый возможный input - выбираем representative subset.
2. **Defect clustering.** Если на одном уровне нашли проблему - смотрим внимательнее (часто рядом ещё).
3. **Early detection cheaper.** L1 находит проблемы за секунды; L5 - за минуты. Делаем L1 первым.
4. **Independence of testing.** QA-скилл не должен сам входить в скилл который тестирует.
5. **No skill is perfect.** Финальный отчёт всегда содержит рекомендации улучшения. PASS не значит "идеально", означает "готово к публикации".