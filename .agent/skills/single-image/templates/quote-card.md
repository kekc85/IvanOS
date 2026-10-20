# Template: quote-card

Quote + attribution + minimal design. Bookmark-bait pocket wisdom.

Reference: Naval (plain text), Hormozi (bold sans on black), James Clear, Maria Popova.

## Brief structure

```yaml
type: quote-card
sub_type: <plain-text | bold-sans-black | serif-cream | handwritten | photo-overlay>

quote:
  text: "<verbatim quote, ≤140 chars / ≤25 слов>"
  author: "<имя или 'Аноним' или твоё имя>"
  source: "<book/post/speech URL для verification>"
  source_verified: true|false
  ownership: "<own | external_attributed | adapted>"

composition:
  primary: "<text central, занимает 60-70% canvas>"
  secondary: "<attribution малым шрифтом снизу>"
  background: "solid color"
  alignment: "center | left-third"

text_on_image_verbatim:
  quote: "<полный verbatim>"
  attribution: "- <имя>"

palette:
  background: "<hex или name из config>"
  text: "<hex или name>"
  contrast_check: "WCAG AAA 7:1+"

typography:
  quote: "<family + weight + size>"
  attribution: "<family + weight + size 50% smaller than quote>"
```

## Sub-type details

### Plain text card (Naval)
- Background: cream / off-white #FAFAFA или soft grey
- Text: near-black #0A0A0A
- Font: Helvetica / Inter Medium 40-60pt
- Attribution: same family 20-24pt, italic optional
- Generous whitespace (50%+)
- Center alignment

### Bold sans on black (Hormozi)
- Background: pure black #000000
- Text: white #FFFFFF
- Font: Bold display sans (Inter Bold / Geist Bold / SF Pro Display Bold) 60-90pt
- Attribution: smaller, можно in caps
- Higher contrast, more aggressive
- Center alignment

### Serif on cream (Popova / The Marginalian)
- Background: cream #FAF8F4
- Text: warm black #1A1815
- Font: Serif display (GT Sectra / Tiempos / Georgia) 36-50pt
- Attribution: serif italic 18-22pt
- Editorial feel
- Left-aligned often

### Handwritten / hand-lettered
- Background: paper texture или solid neutral
- Text: hand-lettered (Procreate / Calligraphy)
- Personal feel, less «produced»
- Higher craft, more time investment

### Photo backdrop + overlay
- Background: muted photo (low contrast, blurred)
- Text overlay: white или high-contrast
- Use carefully - может выглядеть generic stock
- Better для emotional context quote

## Tool prompt

**Figma (recommended):**
```
1. Canvas 1080x1080
2. Background fill: <hex>
3. Text frame центр / left-third:
   - Font: <family>
   - Weight: <Bold | Medium | Regular>
   - Size: 40-90pt depending on quote length
   - Color: <hex>
   - Line height: 1.15-1.35
4. Attribution text frame ниже (50% size, optional italic)
5. Export PNG 2x retina
```

**Canva (quick):**
- Use minimalist quote template
- Customize fonts to your brand
- Export PNG

**DALL-E 3 (alt для text accuracy):**
```
A minimalist quote card on {background color}.
Text: "{quote}"
Attribution: - {author}
Font: {family}, large, centered.
Generous whitespace, no decorative elements.
Square 1:1 composition.
```

## Verification before use

Если quote not yours:
- Check quoteinvestigator.com / wikiquote.org
- Common misattributions: Einstein, Mark Twain, Churchill (avoid если не verified)
- Если найден misattribution - используй real author или label «anonymous»

Если quote yours:
- Original phrasing OK
- Attribute себе («- автор» или handle)

## Caption guidance

- Часто blank (quote самодостаточен) или ≤80 chars context
- Hook patterns:
  - RU: «<рефлексия 1 line>» / «<context source>»
  - EN: «From <book/post>:» / «<reflection 1 line>»
- Не повторять quote в caption

## Anti-patterns specific (FAIL)

- Misattributed quotes (verify always)
- Своя quote attributed чужому
- Quote >25 слов (не вписывается в frame)
- Decorative fonts которые убивают readability
- Stock background photos
- 3+ font families
- Multiple accents

## Quote-worthiness test

Перед carded:
- Тezis quote-worthy? (memorable / share-able / bookmark-able)
- Универсален? (vs niche-specific)
- Не cliché? («Just do it» = no)
- Не negative? («Most people fail» = no)
- Pocket wisdom: можно ли применить?

## Cross-distribution

- X: 1:1 square
- IG: 4:5 для feed reach max
- LinkedIn: 1:1
- TG: 1:1
- Threads: 1:1

## Type-specific review hooks

- Quote ≤ 25 слов / ≤ 140 chars
- Attribution verified
- Contrast WCAG AAA
- Max 2 typeface families
- Identity якорь: brand palette / type / signature element

## Memory cross-refs

- `[[feedback-no-em-dash]]` - em-dash в тексте OK на attribution
- `[[feedback-no-inventing-facts]]` - не выдумывать quotes / attributions