# 01c-transcript.md - Mode C: разбор надиктовки

Триггер: длинный input >500 знаков ИЛИ «надиктовал для твита» / `--transcript`.

## Step 1 - Receive transcript

Input - длинный raw текст от пользователя (надиктовка).

## Step 2 - Extract atomic meanings (3-10)

Из транскрипта выделить **атомарные смыслы**:
- Каждый смысл = self-contained тезис
- Verbatim quote где возможно (лексика автора, не парафраз)
- 3-10 смыслов max

Format:
```yaml
atomic_meanings:
  - id: 1
    quote: "<verbatim из транскрипта>"
    hook_potential: A 40-100 | B 200-280 | thread
    type_hint: single | paips | spiky | numbered | mega | contrarian | how-i-did
    voice_cluster: <derived>
  - id: 2
    ...
```

## Step 3 - Rank by viral potential

Score each meaning:
- **Specificity** (concrete numbers / people / events) - 0-3
- **Novelty** (counter-intuitive / contrarian) - 0-3
- **Voice match** (соответствует primary register) - 0-2
- **Hook readiness** (первая фраза готова) - 0-2

Total /10.

## Step 4 - Present top 3 to user

Output:

```
Топ-3 смысла из транскрипта (для X):

1. [score 8/10] <quote> → type: <X>, format: <X>
2. [score 7/10] <quote> → type: <X>, format: <X>
3. [score 6/10] <quote> → type: <X>, format: <X>

Выбираешь какой?
```

## Step 5 - User selects → handoff

```yaml
mode: transcript
selected_meaning: <id>
verbatim_quote: <verbatim>
recommended_type: <from atomic_meaning>
recommended_format: <derived>
archetype: <derived>
char_zone_target: A | B
```

## Anti-patterns

- **Verbatim hard rule** - лексика автора важнее «причёсанной» формулировки
- НЕ парафраз - quote верно
- НЕ извлекать >10 смыслов (caps overflow user choice)
- НЕ ranking без specificity / novelty / voice / hook scoring

## Memory cross-refs

- `[[feedback-verbatim-quote-transfer]]` - дословный перенос, не пересказ
- `[[feedback-language-bank-before-meanings]]` - лексика автора первична