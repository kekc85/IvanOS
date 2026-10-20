# Mode A — person photo research

## Input

- `<person_name>` (например "Dario Amodei")
- `<context>` опционально (компания / роль для disambiguation)

## Output

`~/Desktop/visual-research/<person-slug>-<YYYY-MM-DD>/` с:
- `<slug>-wikipedia.png` — full page screenshot
- `<slug>-hires.jpg` — original из Wikimedia Commons (если есть)
- `<slug>-google-grid.png` — variety grid
- `<slug>-official.png` — company About/Team page
- `README.md` per [[readme-template]]

## Workflow

### Step 1: Disambiguation gate

Если `<person_name>` — общее имя (John Smith, автор авторский), либо нет context:
- Ask user: «Уточни компанию или роль (например, John Smith CEO Acme)»
- НЕ запускать browser до получения context

Если имя уникальное (Dario Amodei, Sam Altman) — skip.

### Step 2: Public figure gate

Прогнать через [[public-figure-policy]] decision algorithm:
- Allow list match → continue
- Soft case → continue с caution flag в README
- Deny list match → STOP, refuse with brief reason

### Step 3: Setup output folder

```bash
slug=$(echo "<person_name>" | tr ' ' '-' | tr 'A-ZА-Я' 'a-zа-я')
date=$(date +%Y-%m-%d)
mkdir -p ~/Desktop/visual-research/${slug}-${date}
```

### Step 4: Wikipedia run

```
mcp__playwright__browser_navigate → https://en.wikipedia.org/wiki/<Person_Name>
```

Проверить через snapshot, что страница та (не disambiguation page).

Screenshot full page:
```
mcp__playwright__browser_take_screenshot
  filename: ~/Desktop/visual-research/<slug>-<date>/<slug>-wikipedia.png
  fullPage: true
```

### Step 5: Wikimedia Commons hi-res extraction

Через `browser_evaluate` извлечь URL infobox photo:
```js
() => {
  const imgs = Array.from(document.querySelectorAll('table.infobox img, .infobox-image img'));
  return imgs.map(i => ({
    src: i.src,
    alt: i.alt,
    w: i.naturalWidth,
    h: i.naturalHeight
  }));
}
```

Преобразовать thumbnail URL в original:
- thumbnail: `/wikipedia/commons/thumb/X/XX/Filename.jpg/250px-Filename.jpg`
- original:  `/wikipedia/commons/X/XX/Filename.jpg`

Удалить `/thumb/` сегмент и `/NNNpx-...` суффикс.

Download через Bash:
```bash
curl -sL "<original_url>" -o ~/Desktop/visual-research/<slug>-<date>/<slug>-hires.jpg
```

Если нет Wikipedia article — skip и записать в README «No Wikipedia article found».

### Step 6: License extraction

Navigate к Wikimedia Commons file page:
```
https://commons.wikimedia.org/wiki/File:<filename>
```

Через evaluate извлечь license tag:
```js
() => {
  const txt = document.querySelector('.licensetpl')?.textContent || 
              document.querySelector('#mw-content-text')?.textContent;
  const match = txt?.match(/(CC[- ]BY[- ]?(SA|NC|ND)?-?\d?\.?\d?|Public domain|GFDL|PD-self|PD-USGov)/i);
  return match?.[0] || 'UNKNOWN';
}
```

Author:
```js
() => document.querySelector('a[title*="User:"]')?.textContent || 
      document.querySelector('.fileinfotpl_aut + td')?.textContent?.trim() || 
      'UNKNOWN'
```

### Step 7: Official company page

Если в Wikipedia infobox указана company — navigate к ней:
- `<company>.com/about` или `/team` или `/company`

Screenshot full page как `<slug>-official.png`.

### Step 8: Google Images variety grid

```
mcp__playwright__browser_navigate → 
  https://www.google.com/search?q=<URL_encoded_query>&tbm=isch
```

Wait 2s для load. Screenshot viewport (НЕ full page — viewport достаточно для grid):
```
mcp__playwright__browser_take_screenshot
  filename: ~/Desktop/visual-research/<slug>-<date>/<slug>-google-grid.png
  fullPage: false
```

### Step 9: Write README.md

Использовать [[readme-template]]. Включить:
- Mode + query + date + disambiguated query
- Files block с source + author + license per file
- Suggested use (post / carousel / video b-roll)
- Caveats (staleness if photo >2 years old, license uncertainties)

### Step 10: Open folder + report

```bash
# macOS: open · Windows: start "" · Linux: xdg-open · универсально: ~/.claude/skills/_shared/bin/open-file
open ~/Desktop/visual-research/<slug>-<date>/
```

Report в чат:
- Папка открыта
- Markdown links к каждому файлу через `[file](path)` formatting
- Top recommendation: какой файл для какой цели

### Step 11: Cleanup browser

```
mcp__playwright__browser_close
```

## Anti-patterns

- Не пропустить disambiguation если имя неоднозначное
- Не пропустить public figure gate
- Не сохранять thumbnail из Google Images как "hi-res original"
- Не выдумывать license info — если не нашли, явно `UNKNOWN — verify`
- Не оставлять browser открытым (close в финале)

## Verbatim values

Каждый файл в README должен иметь:
- ✅ Source URL точно как в browser (не сокращать)
- ✅ License точно как в Wikimedia (не translate)
- ✅ Author точно как в credit (не модифицировать)
- ✅ Date taken если known (год минимум)