# Mode B — event photo research

## Input

- `<event_name>` (например "TechCrunch Disrupt 2025")
- `<year>` опционально (если не в имени)
- `<event_type>` опционально (conference / launch / news event)

## Output

`~/Desktop/visual-research/<event-slug>-<YYYY-MM-DD>/` с:
- `<slug>-official.png` — официальный сайт события
- `<slug>-google-grid.png` — общая выдача
- `<slug>-coverage-techcrunch.png` — news coverage screenshot
- `<slug>-coverage-verge.png` — alternative coverage
- 3-5 individual photos из conference (если есть Wikimedia или press kit gallery)
- `README.md` per [[readme-template]]

## Workflow

### Step 1: Disambiguation

Если event ambiguous (есть конференция, есть launch event, есть news event с тем же именем):
- Ask user: «Уточни тип события (conference / launch / news event)»

Если year не указан и есть recurring event — ask year.

### Step 2: Setup output folder

```bash
slug=$(echo "<event_name>" | tr ' ' '-' | tr 'A-ZА-Я' 'a-zа-я')
date=$(date +%Y-%m-%d)
mkdir -p ~/Desktop/visual-research/${slug}-${date}
```

### Step 3: Identify official source

Сценарии:
- **Conference** (Disrupt, Web Summit, TED) → `<conference>.com/<year>` или `<conference>.com/events/<year>`
- **Launch event** (Anthropic Claude launch) → `<company>.com/news/<launch>` или blog post
- **News event** → нет official source, идти на news coverage (Step 4)

Navigate + screenshot:
```
mcp__playwright__browser_navigate → <official_url>
mcp__playwright__browser_take_screenshot
  filename: ~/Desktop/visual-research/<slug>-<date>/<slug>-official.png
  fullPage: true
```

### Step 4: News coverage screenshots

Topic search через WebSearch чтобы найти top coverage:
- Query: `"<event_name>" <year> site:techcrunch.com`
- Query: `"<event_name>" <year> site:theverge.com`
- Query: `"<event_name>" <year> site:bloomberg.com`

Top-3 articles → navigate каждую → screenshot viewport:
```
<slug>-coverage-<outlet>.png
```

### Step 5: Wikimedia Commons category check

```
mcp__playwright__browser_navigate → 
  https://commons.wikimedia.org/wiki/Category:<Event_Name>_<Year>
```

Если категория существует:
- Через evaluate извлечь URLs всех файлов в category
- Download top-5 через `curl`

Если не существует — skip.

### Step 6: Google Images variety grid

```
mcp__playwright__browser_navigate → 
  https://www.google.com/search?q=<URL_encoded_query>&tbm=isch
```

Screenshot viewport:
```
<slug>-google-grid.png
```

### Step 7: License extraction per file

Для каждого Wikimedia файла — license + author per [[mode-a-person]] Step 6.

Для news coverage screenshots:
- License: `Editorial use only (screenshot of public news article)`
- Use: ✅ для commentary / criticism / news context, ❌ как standalone visual в paid ads

### Step 8: Write README.md

Per [[readme-template]]. Включить:
- Event name + year + type
- Files block
- Suggested use per file
- Note про "event coverage license complexity" если applicable

### Step 9: Open + report + close browser

Same as [[mode-a-person]] Step 10-11.

## Anti-patterns

- Не путать events с одинаковыми именами (TechCrunch Disrupt 2023 vs 2024)
- Не использовать news coverage screenshots как primary visual (only for context)
- Не game license — editorial use это editorial use, не вытягивать в commercial
- Не пропускать year disambiguation если event recurring