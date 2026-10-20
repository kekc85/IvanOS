# Workflow 04: Caption (bilingual RU + EN)

> 🔴 Если CTA caption = КОД-СЛОВО (lead-magnet) — строить СТРОГО по канону `~/.claude/skills/_shared/lead-magnet-description-structure.md` (6 блоков: хук-парадокс / суть / примеры-с-якорями / личный опыт / что внутри / CTA код-слово). НЕ плоский caption.

Bilingual caption draft - 3 варианта на каждый язык. Caption поддерживает картинку, не дублирует.

## Input

Из 03-design-brief:
- type
- topic
- text_on_image_verbatim (важно для no-duplicate check)
- platform (определяет длину caption)
- verbatim_quote (если из transcript)

Из config:
- subject.primary_language
- subject.bilingual_always (true для автора)
- voice.* (archetypes / pronoun / formality)
- lexicon_banned_hard
- lexicon_required

## Шаги

### Step 1: Caption length target

| Platform | Caption target (chars) |
|---|---|
| X | <240 (leave room для image alt) |
| LinkedIn | 150-400 (story tone, 1-3 abzaca) |
| Нельзяграм | 150-500 (включая hashtags) |
| TG | 100-400 |
| Threads | <200 |

### Step 2: Caption role per type

| Type | Caption role |
|---|---|
| concept-diagram | Setup для diagram (1 line) или mental model context (2-3 lines) |
| dashboard-screenshot | Context / setup (1-3 lines max). Cifры в image, не дублировать |
| meme | Минимальный или нет (image carries hook). Если есть - 1 line meta |
| quote-card | Минимальный или 1 line attribution context |
| before-after | Setup before / context after. 2-3 lines |

### Step 3: 3 hook patterns per language

**RU hook patterns:**
1. **Hook-Story-Offer (Brunson):** короткий setup + story bit + soft CTA
2. **Verb-first (action):** Глагол в начале «Покажу как X». Прямой adressing
3. **Question hook:** Вопрос провоцирующий continue-read

**EN hook patterns:**
1. **"I" hook (personal):** «I [did X]. Here's [Y].»
2. **Imperative:** «Stop doing X. Try Y instead.»
3. **List preview:** «3 things I learned from [X]:»

Применить voice config:
- Archetypes Magician/Sage/Outlaw (не Caregiver/Lover/Innocent)
- Local pronoun (ты / you)
- Low formality

### Step 4: Generate 3 RU + 3 EN

**Шаблон output:**
```
RU caption (3 варианта):
A: <hook + body + cta, ≤target chars>
B: <hook + body + cta, ≤target chars>
C: <hook + body + cta, ≤target chars>

EN caption (3 варианта):
A: <hook + body + cta, ≤target chars>
B: <hook + body + cta, ≤target chars>
C: <hook + body + cta, ≤target chars>
```

### Step 5: Validations (preview - full в 05-review)

Каждый caption проверить:
- Длина <= target
- Em-dash «-» внутри строк? → FAIL
- Banned англицизмы / hyped buzzwords? → FAIL
- Negative статистики? → FAIL
- Word overlap с text on image > 60%? → FAIL (caption дублирует)
- Voice fit (читается как автор / автор?) → semantic check

Если FAIL - regenerate с corrections.

### Step 6: Output

```yaml
captions:
  ru:
    A: "<text>"
    B: "<text>"
    C: "<text>"
  en:
    A: "<text>"
    B: "<text>"
    C: "<text>"
  notes:
    primary_language: "<from config>"
    word_overlap_with_image: "<%>"
    voice_fit_self_check: "<PASS/notes>"
```

→ `05-review.md`

## Принципы

1. **Caption < image.** Image carries 80% смысла. Caption поддерживает.
2. **No-duplicate с image text.** Caption даёт setup / context / CTA, не пересказ.
3. **Bilingual всегда.** RU + EN параллельно по config.subject.bilingual_always.
4. **Не дословный перевод.** EN не калька RU. Culturally adapt (см. `[[multi-language-localization]]`).
5. **Voice locked.** Archetype config sets tone.
6. **3 варианта = choice room.** Финальный single pick - в 06-output.

## Edge cases

- **Quote-card type:** caption может быть 0-1 строка (quote самодостаточен)
- **Meme type:** caption часто 0-1 line meta. Допустимо blank caption
- **Dashboard type:** caption строго не повторяет цифру из image
- **Verbatim quote из transcript:** должен присутствовать минимум в одном из 3 вариантов RU
- **Multi-platform:** captions могут быть platform-specific