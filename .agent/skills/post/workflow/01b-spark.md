# Workflow 01b - Mode B: Spark (ситуативный)

**Назначение:** получить готовый brief на основе либо идеи пользователя (B1), либо генерации скилла под JTBD/аватар (B2).
**Входы:** `brief.mode = "spark-b1"` или `"spark-b2"`
**Выходы:** `brief.topic`, `brief.angle`, `brief.source = "user-idea"` или `"ai-generated"`
**Следующая стадия:** `workflow/01-finalize.md`

---

## Sub-flow B1 - расширение идеи пользователя

Запускается когда пользователь дал конкретную тему: «напиши про X», «/post про вайбкодинг», «пост о Cursor».

### Шаг B1.1 - Извлечь тему

Из user input выделить ядро темы.

Примеры:
- «напиши пост про вайбкодинг» → core_topic = «вайбкодинг»
- «/post про то как Cursor 4 делает Claude слабее» → core_topic = «Cursor 4 ослабил Claude»
- «сделай пост про мою сессию с автором Б.» → core_topic = «сессия с автором Б.»

Записать `brief.core_topic = <извлечённое>`.

<!--
B1.2 GATE введён по решению автора после прецедента post v1.2 first-run (см. `.business/история/2026-05-27-post-skill-v1-2-living-language.md`).
Memory `feedback_each_correction_becomes_system_rule` - точечный fix + системная правка скилла. Без enforced reads идея формируется без привязки к JTBD/боли аватара, выходят generic углы.
-->

### Шаг B1.2 - Mandatory Context Reads (GATE)

**HARD requirement.** Без этого gate не идти в B1.3. Skill ОБЯЗАН выполнить 4 Read'а по путям из `config.paths` (read-only):

1. `paths.avatar` - кому пишем (портрет читателя, боли, желания)
2. `paths.jtbd` - какие работы читатель нанимает контент закрыть
3. `paths.brand_dna` - голос, архетип, угол автора
4. `paths.products_dir` - overview активных продуктов (что сейчас продаётся)

**Порядок выполнения:**

1. Для каждого из 4 путей вызвать Read tool.
2. Если файл отсутствует / Read failit - пометить как `✗ (отсутствует)`, продолжить со следующим. НЕ skip silently.
3. После 4 попыток подсчитать `read_count` (сколько успешно прочитано).

**Gate условие:**

- `read_count >= 2` → PASS, продолжать в B1.3
- `read_count < 2` → **ABORT** с сообщением в чат:
  ```
  B1.2 GATE FAILED: прочитано N/4, нужно ≥2.
  Не могу продолжить без минимального контекста автора.
  Проверь config.paths и наличие файлов avatar / jtbd / brand_dna / products_dir.
  ```

**Output отчёт в чат (всегда показывать перед B1.3):**

```
B1.2 GATE: прочитано X/4 файлов: [avatar V / jtbd V / brand_dna V / products X (отсутствует)]
```

(Использовать `V` для прочитано, `X` для отсутствует. Никаких emoji.)

Это даёт скиллу «голос» и контекст JTBD, под который будут адаптированы идеи в B1.3.

### Шаг B1.3 - Сгенерировать 5-7 углов (подидей)

Для core_topic построить 5-7 разных **углов раскрытия**.

Каждый угол = пара (hook_angle, payoff):
- `hook_angle` - с какого ракурса заходим (contrarian / vulnerable / numbered / time-based / etc.)
- `payoff` - какой инсайт/вывод

**Обязательное разнообразие:**
- Не более 2 углов с одним hook_angle.
- Минимум 1 угол должен быть «опровергающий общепринятое» (Contrarian / Myth-Busting).
- Минимум 1 угол должен быть personal/vulnerable.

**Связка с JTBD:**
Для каждого угла указать: какой JTBD читателя он закрывает (одна фраза). Если не закрывает ничего - выкинуть угол.

### Шаг B1.4 - Показать пользователю

Формат вывода:

```
Идея: <core_topic>

Углы:
1. <hook_angle> - <payoff>
   JTBD: <одна фраза>
2. <hook_angle> - <payoff>
   JTBD: <одна фраза>
...
7. <hook_angle> - <payoff>
   JTBD: <одна фраза>

Какой берём? (номер) Или дай свой угол.
```

### Шаг B1.5 - Зафиксировать выбор

Пользователь называет номер ИЛИ диктует свой угол.

Записать:
- `brief.topic = core_topic`
- `brief.angle = <выбранный или продиктованный угол>`
- `brief.hook_type_hint = <hook_angle выбранного>`
- `brief.source = "user-idea"`

→ Перейти в `workflow/01-finalize.md`.

---

## Sub-flow B2 - генерация идей под JTBD

Запускается когда пользователь сказал «дай идеи», «что писать», «варианты».

<!--
B2.1 GATE введён по решению автора после прецедента post v1.2 first-run (см. `.business/история/2026-05-27-post-skill-v1-2-living-language.md`).
Memory `feedback_each_correction_becomes_system_rule`. В B2 (без темы от пользователя) контекст ещё критичнее чем в B1 - идеи генерятся from scratch, без enforced reads вся пачка получится generic.
-->

### Шаг B2.1 - Mandatory Context Reads (GATE)

**HARD requirement.** Без этого gate не идти в B2.2. Skill ОБЯЗАН выполнить 7 Read'ов по путям из `config.paths`:

1. `paths.avatar` - портрет читателя
2. `paths.jtbd` - список JTBD (приоритизированный, если есть)
3. `paths.objections` - возражения (для контр-постов)
4. `paths.brand_dna` - голос и угол
5. `paths.products_dir` - что сейчас активно продаётся
6. `paths.content_map` - что уже было запланировано (no overlap)
7. `recent_posts` через `paths.recent_posts_source` - что уже опубликовано (no repeat). Для `recent_posts_source: webfetch` использовать WebFetch на `paths.recent_posts_url`. Для `file` - Read файла. Для `none` - пометить `✗ (отключено в config)`.

**Порядок выполнения:**

1. Для каждого из 7 источников вызвать Read / WebFetch tool.
2. Если файл отсутствует / Read failit / WebFetch недоступен - пометить как `✗ (отсутствует)`, продолжить со следующим. НЕ skip silently.
3. После 7 попыток подсчитать `read_count`.

**Gate условие:**

- `read_count >= 4` → PASS, продолжать в B2.2
- `read_count < 4` → **ABORT** с сообщением в чат:
  ```
  B2.1 GATE FAILED: прочитано N/7, нужно ≥4.
  Не могу генерить идеи без минимального контекста.
  Проверь config.paths: критичны avatar / jtbd / brand_dna / products_dir.
  ```

**Output отчёт в чат (всегда показывать перед B2.2):**

```
B2.1 GATE: прочитано X/7 источников: [avatar V / jtbd V / objections X / brand_dna V / products V / content_map X / recent_posts V]
```

(Использовать `V` для прочитано, `X` для отсутствует. Никаких emoji.)

### Шаг B2.2 - Сгенерировать 5-7 идей с обоснованием

Каждая идея = структура:

```
Идея N: <одна фраза-тезис>
JTBD: <какой нанимаемый job закрывает>
Боль: <конкретная боль из avatar.md>
Угол: <Contrarian / Vulnerable / Results / Myth / ...>
Свежесть: <чем отличается от последних 30 постов>
```

**Hard filters:**
- Не повторяет ни один из последних 30 постов (по теме + углу).
- Закрывает реальный JTBD из `jtbd.md`, не выдуманный.
- Соответствует Brand DNA автора (Magician/Sage/Outlaw).
- Не нарушает запреты config.lexicon_banned_hard.

**Soft preferences:**
- Привязка к актуальному запуску (если есть `paths.content_map` с активной дугой).
- Тематическое разнообразие - не все 7 идей про одно.
- Минимум 1 personal / 1 educational / 1 contrarian.

### Шаг B2.3 - Показать пользователю

Формат - как в B1.4, но без core_topic (его нет):

```
Идеи на сегодня:

1. <тезис>
   JTBD: <фраза>
   Боль: <фраза>
   Угол: <тип>

2. ...
...
7. ...

Какую берём? (номер) Или дай свою.
```

### Шаг B2.4 - Зафиксировать выбор

Пользователь выбирает или диктует свою.

Записать:
- `brief.topic = <выбранный тезис>`
- `brief.angle = <тот же тезис, угол из идеи>`
- `brief.hook_type_hint = <угол>`
- `brief.source = "ai-generated"`

→ Перейти в `workflow/01-finalize.md`.

---

## Anti-patterns обоих sub-flow

- **Generic идеи без JTBD** - каждая идея обязательно привязана к конкретной боли из avatar.md.
- **Повторы тематики** последних 30 постов - фильтруется в B2.2 hard filter.
- **AI-slop тематика** («ИИ изменит всё» / «контент важен» / «вот 5 советов») - auto-fail.
- **Идеи в стиле другого автора** - обязательная проверка через `brand_dna.md` и `voice_reference`.
- **Выдуманные кейсы / цифры** - если идея ссылается на конкретный кейс/число, оно должно быть из артефактов проекта (memory `feedback-no-inventing-facts`).

---

## Принципы Mode B

1. **Идея ≠ пост.** Spark выдаёт brief, пост идёт дальше по маршруту `01-finalize.md` → `02b…02f` → `03-dry.md` → `04-review.md`.
2. **5-7, не 1.** Один вариант = диктат. 5-7 = выбор. Больше 7 = когнитивная перегрузка.
3. **JTBD-bound.** Без привязки к нанимаемой работе идея не проходит.
4. **No-repeat hard.** Прочитал последние 30 постов - не повторяешь.
