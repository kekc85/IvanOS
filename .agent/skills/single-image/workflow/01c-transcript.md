# Workflow 01c: Mode C - Transcript (из надиктовки)

Разбор длинной (>500 знаков) надиктовки автора в атомарные визуальные смыслы.

## Когда срабатывает

- User input >500 знаков с пометкой «надиктовал» / «для картинки» / «вот мысли»
- Override flag `--transcript`
- Текст содержит непрерывный narrative без явного structured request

## Шаги

### Step 1: Атомарные смыслы

Разобрать transcript на 3-10 атомарных смыслов. Каждый смысл = 1 visual-friendly идея.

**Шаблон output:**
```
Из надиктовки извлёк 7 визуальных смыслов:

1. <verbatim цитата 5-15 слов или close paraphrase> [type: <type>]
2. <цитата> [type: <type>]
3. ...
```

### Step 2: Diversity check

7 смыслов должны cover минимум 3 разных типа из 5 (concept-diagram / dashboard-screenshot / meme / quote-card / before-after).

Если все попадают в один тип - flag warning «narrow transcript - все смыслы это <type>».

### Step 3: User selects top 1-3

«Выбери top 1-3 которые делаем картинками сейчас. Остальные сохраним как backlog?»

User отвечает номерами.

Если backlog - записать оставшиеся смыслы в `examples/track-record-single-image.md` секцию «Backlog from transcripts» для future use.

### Step 4: Per chosen смысл - expand to angle

Для каждого выбранного смысла:
- Подтвердить type (или предложить альтернативу)
- Уточнить угол (если transcript неясен)
- Подтвердить cue для каждого type:
  - concept-diagram: какая geometry?
  - dashboard-screenshot: какое real metric?
  - meme: какой template?
  - quote-card: какой verbatim quote?
  - before-after: что before, что after?

### Step 5: Verbatim quote preservation

Важный принцип: лексика автора в transcript должна сохраняться в visual brief / caption.

Если автор сказал «контент-завод», caption использует «контент-завод», не «content engine» / «content production system».

См. memory `[[feedback-verbatim-quote-transfer]]`.

### Step 6: Output

Для каждого chosen смысла:
```yaml
mode: "transcript"
topic: "<смысл expanded>"
verbatim_quote: "<цитата из transcript>"
hints:
  type_suggestion: "<chosen type>"
  platform_suggestion: null
  reference_creator: null
source_context: "Transcript user input ({date})"
```

→ для каждого - отдельный pass через `02-finalize.md` и далее.

Если user выбрал 3 - последовательно: 02-finalize → ... → 06-output (3 раза). Финальный response содержит 3 готовых brief'а.

## Принципы

1. **Verbatim quote.** Лексика автора > «причёсанная» формулировка. Сохранять цитаты дословно где возможно.
2. **Atomic smysli.** 1 visual = 1 смысл. Multi-смысловые transcripts split на серию.
3. **3 от 5 типов.** Diversity в разборе - не все смыслы в один type.
4. **Backlog не теряй.** Невыбранные смыслы сохраняем для future runs.

## Edge cases

- **Transcript на 2 языках mix** → принять, генерация brief / caption будет в primary_language config
- **Transcript содержит технический jargon** → flag для review (caption должна раскрывать)
- **Transcript содержит negative статистики** → flag «эта часть не подходит для public», но atomic смыслы можно extract из других частей
- **Transcript содержит выдуманные numbers** → если type=dashboard, нельзя использовать как brief, ask verify