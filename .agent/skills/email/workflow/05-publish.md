# workflow/05-publish.md

> Output + ОДИН Subject + ESP-ready format + self-check. 🔴 Subject всегда ровно один (правка автора: «зачем ты мне дал 3 subject? так никогда не делать») - выбор сильнейшего делает скилл внутри, автору варианты не выносить.

## Inputs

- `draft` (после `04-review.md` PASS)
- `brief` (с meta)
- `config`

## Step 1 - Format output

### Структура output (copy-paste ready для Kit / Beehiiv / любой ESP)

```markdown
# Email: <type> | <YYYY-MM-DD> | <language>

## Subject (ровно ОДИН - варианты списком = брак, правка автора)

<один subject: framework под тип письма, mobile-truncation safe, voice fit. Кандидатов сравниваешь ВНУТРИ (не показывая), сильнейший - в output, отброшенные - строкой во Внутрянке>

## Preheader

<preheader text, 50-90 chars>

## Body

<full body — форматирование ОБЯЗАТЕЛЬНО ВСЕГДА (правка автора):
жирный `**...**` на опорные тезисы / главную выгоду / дедлайн / цифру-доказательство (2-5 акцентов, НЕ каждую строку = slap);
курсив `__...__` на ремарки / P.S. (канон голоса §3).
🔴 ВЫДАЧА В ЧАТ — финальный copy-ready текст ВСЕГДА внутри ```-fenced code block с СЫРЫМИ маркерами `**`/`__`, НЕ отрендеренным жирным: иначе при копировании в Telegram маркеры теряются и выделение не уезжает (ярость автора «если скопирую в Telegram — выделение не скопируется»).
НЕ голый plain-text. Telegram-markdown: жирный `**`, курсив `__`>

## CTA

- Текст кнопки / link anchor: <CTA text>
- Link: <url>
- Position(s): above-fold | after-value-stack | bottom | p.s.

## Внутрянка (как писал)

- Mode: <plan | spark | transcript>
- Type: <nurture | launch-sequence | sales-letter>
- Sequence position: <day N или null>
- Hook framework (winner Subject): <framework>
- Archetype: <Magician | Sage | Outlaw>
- Angle: <pain | aspiration | contrarian | personal | tactical>
- CTA goal: <conversion goal>
- Subject-логика: <почему этот subject выиграл; какие кандидаты отброшены и почему>
- Что отброшено: <варианты hook'ов которые рассматривал и почему не выбрал>
- Layer проверок: 1/8 hard / 2/8 EMAIL-G / 3/9 Maxwell Ross / 3 слоя - все PASS
```

### Если language=both - два output блока (RU.md + EN.md)

Отдельные файлы:
- `<date>-<type>-<slug>-ru.md`
- `<date>-<type>-<slug>-en.md`

С перекрёстными ссылками друг на друга в Внутрянке.

## Step 2 - Save to output_dir

```
output_path = config.paths.output_dir + filename
Write(output_path, output)
```

Если language=both → 2 файла. Если RU only → 1 файл.


## Step 2.5 - Compliance footer injection (для custom ESP)

См. `references/compliance.md` для full footer templates.

```
IF config.esp.default in [kit, beehiiv]:
    skip - ESP auto-handles footer
ELSE IF config.esp.default == custom:
    inject_compliance_footer(body, language, config)
    
    RU footer template:
    ---
    Если больше не хочешь получать письма - отписаться: {unsubscribe_link}
    {sender_legal_entity} | ИНН: {inn} | {physical_address}
    Это маркетинговое письмо. Reply: {reply_email}
    ---
    
    EN footer template:
    ---
    Don't want these emails? Unsubscribe: {unsubscribe_link}
    {sender_legal_entity} | {physical_address}
    This is a promotional email. Reply to {reply_email}
    ---
```

Injection происходит после Step 2 (output formatting) и до Step 3 (self-check). Self-check проверяет что footer присутствует если ESP == custom.

## Step 3 - Self-check

После Write обязательно прочитать output (Bash `ls` + Read первые 50 строк) и проверить:

- ✓ Файл создан
- ✓ Subject ровно ОДИН (несколько вариантов = брак, правка автора)
- ✓ Preheader присутствует
- ✓ Body length в диапазоне
- ✓ CTA с link
- ✓ Внутрянка заполнена
- ✓ Внутрянка содержит подтверждение «3 слоя пройдено»

Если что-то отсутствует → log warning + re-write.

## Step 4 - ESP-specific formatting hints

### Kit (default)

```
В Kit:
1. Создай новый Broadcast (или Sequence step)
2. Subject: вставь Subject
3. Preheader: вставь preheader
4. Body: вставь форматированным (Kit поддерживает rich/markdown) — жирный на опорные тезисы сохраняем, НЕ голый plain (правка автора)
5. Tag rules: <tag_rules из brief>
6. Schedule send time: <твой timezone>
```

### Beehiiv (если config.esp.default=beehiiv)

```
В Beehiiv:
1. Create new Post (broadcast)
2. Title: Subject
3. Subtitle / preheader: preheader
4. Body: paste как Rich Text (Beehiiv использует HTML blocks)
5. Add CTA block at position(s) указанных в Внутрянке
6. Segment: <segments из brief>
7. Schedule
```

## Step 5 - POSSE cross-distribution hint (optional)

Если ученик попросил derivatives - список cross-distribution:

- TG-пост из body excerpt → `post` `/post --transcript`
- LinkedIn post из CTA part → `paips-post`
- X thread из big idea → `long-form-essay` или `pattern-extraction`
- YouTube short из angle → `video`

Это **hint**, не auto-execute. Ученик решает что cross-publish.

## Step 6 - Update no-repeat history

Если в config указан `recent_emails_dir`:

- Append output file в директорию
- Skill при следующем запуске будет читать его для no-repeat check

## Step 7 - Bash `open` output file

Per memory `[[feedback-always-open-artifacts]]`:

```bash
open <output_path>
```

Чтобы автор сразу увидел финальный email в VS Code / Markdown viewer.

## Anti-patterns

- НЕ выдавать output БЕЗ Внутрянки - Внутрянка = аудит для автора, без неё нет visibility
- НЕ skip self-check Step 3 - silent failures = брак
- НЕ забывать сохранять output в `recent_emails_dir` - no-repeat сломается через несколько итераций
- 🔴 НЕ выдавать несколько Subject-вариантов - ровно ОДИН всегда (правка автора: «так никогда не делать»); выбор сильнейшего = работа скилла внутри, не автора
- НЕ выдавать ESP-specific format если ESP не указан в config - выдать generic plain-text
---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
