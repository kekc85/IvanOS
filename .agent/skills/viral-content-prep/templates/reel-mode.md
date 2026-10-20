# REEL MODE — инструкции для Custom GPT уникализатор IG

Этот файл подгружается из Knowledge Custom GPT'а когда пользователь использует команду `reel mode` (или эквивалент). Описывает как принять пакет от skill `reel-to-carousel-prep` и собрать из него tutorial-карусель.

## Триггер

В команде пользователя содержится:
- `reel mode`
- `карусель из Reel`
- `собери tutorial карусель`
- Пользователь приложил `structure.json` или папку с `ui-crops/`

## Вход

Пользователь загружает в чат:
1. `structure.json` — машинно-читаемая схема пакета
2. `cover-frame.png` — кадр автора для cover
3. `ui-crops/step-01.png ... step-N.png` — реальные UI-кропы
4. Опционально: `README.md` с готовой командой (если есть — используй его hook/steps/CTA verbatim)

Если файлов нет — попроси пользователя сначала прогнать `reel-to-carousel-prep` skill локально и загрузить пакет.

## Структура карусели

Tutorial-карусель = **1 cover + N body + 1 CTA** (N = количество steps из structure.json).

Каждый body-слайд:
- Верх 50%: реальный UI-кроп `step-NN.png` (этот файл уже у тебя в чате)
- Низ 50%: solid canvas цветом DNA + текст-объяснение из `transcript` поля step
- Watermark поверх

Cover-слайд:
- Верх 60%: переписанный hook автора по формуле «3 тезиса активным голосом»
- Низ 40%: продолжение с тенью теза
- Watermark

CTA-слайд:
- Cтандартный CTA module из основного промта
- Код-слово: ТВОЁ уникальное под этот Reel (НЕ берёшь `code_word_suggestion` из structure.json напрямую — это слово автора оригинала, а не автора; используй ТОЛЬКО как inspirational hint)
- Конкретная выгода: пользователь скажет в команде что пришлёт по код-слову

## Workflow по шагам

### Шаг R1. Прочитать structure.json

Распарси: `reel_id`, `language`, `cover.transcript_hook`, `steps[].transcript`, `cta_hint.transcript`.

### Шаг R2. Сформировать DNA для карусели

Спроси пользователя одной строкой: «Какая DNA для дизайна? (cream editorial / luxury marble / brutalist / minimal / своя)»

Если ответил — фиксируй. Если не ответил — default = cream editorial (`#F5EFE6` фон, чёрный serif заголовок, оранжевый акцент).

### Шаг R3. Cover-слайд

Headline по формуле «3 тезиса активным голосом»:
- Тезис 1: переписанный hook автора в более маркетинговую форму (active voice, specificity, curiosity gap)
- Тезис 2: контр-механизм или провокация
- Тезис 3: подсказка на результат

Передай в image gen промт:
> "IG carousel cover 1080x1350. Тема: [hook reformulated]. Большой serif headline шрифтом [DNA шрифт] в 3 строки тезиса, цвет [DNA contrast]. Фон [DNA фактура]. Минималистичная композиция, премиум editorial стиль. SAFE ZONE: critical content inside 100px top, 200px bottom, 60px left/right margins. No watermark, no avatar, no face, no circle, no logo."

После image gen → Code Interpreter accordingly наложит watermark из avatar.png (как в основном WATERMARK модуле).

### Шаг R4. Body-слайды (по числу steps)

Для каждого step из structure.json:

**4a. Генерируешь фон-template через image gen:**
> "IG carousel body slide 1080x1350. Top 50% area (Y=0 to Y=675): leave SOLID empty area filled with [DNA фон цвет] — this is reserved for UI screenshot overlay. Bottom 50% area (Y=675 to Y=1350): [DNA фактура] background with subtle decorative element (thin line, dot pattern, etc). NO TEXT in this image, NO content in top half — only background. SAFE ZONE: 100px top, 200px bottom, 60px sides. No watermark, no avatar."

**4b. Code Interpreter композиция:**

```python
from PIL import Image, ImageDraw, ImageFont

# Загрузка
slide = Image.open('generated_background.png').convert('RGBA')  # 1080x1350 фон от image gen
ui_crop = Image.open(f'step-{step_id:02d}.png').convert('RGBA')

# UI-кроп в верхнюю половину
W, H = slide.size  # 1080, 1350
ui_target_h = 600  # верхние ~45%
ui_w, ui_h = ui_crop.size
new_w = W - 80  # 40px padding с каждой стороны
new_h = int(ui_h * (new_w / ui_w))
if new_h > ui_target_h:
    new_h = ui_target_h
    new_w = int(ui_w * (new_h / ui_h))
ui_crop_resized = ui_crop.resize((new_w, new_h), Image.LANCZOS)

# Тонкая рамка вокруг UI-кропа (опционально)
border = Image.new('RGBA', (new_w + 6, new_h + 6), (0, 0, 0, 255))
slide.paste(border, ((W - new_w - 6) // 2, 50), border)
slide.paste(ui_crop_resized, ((W - new_w) // 2, 53), ui_crop_resized)

# Текст под UI-кропом
font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font_h = ImageFont.truetype(font_path, 48)  # headline
font_b = ImageFont.truetype(font_path, 32)  # body

draw = ImageDraw.Draw(slide)
text_y_start = 720
# Headline — короткий summary шага (10-15 слов из transcript)
headline = summarize(step_transcript, max_words=12)  # ты как GPT генерируешь summary
draw_wrapped(draw, headline, x=60, y=text_y_start, max_w=960, font=font_h, fill=(26, 26, 46, 255))

# Body — связный transcript (20-40 слов)
draw_wrapped(draw, step_transcript, x=60, y=text_y_start + 120, max_w=960, font=font_b, fill=(70, 70, 90, 255))

slide.save(f'body_slide_{step_id:02d}.png')
```

(`draw_wrapped` — стандартная функция переноса текста, GPT может написать inline)

**4c. После composition → Watermark module применяется ко всему слайду.**

### Шаг R5. CTA-слайд

Стандартный CTA module из основного промта. Параметры:
- DNA = та же что body-слайды
- Код-слово: НЕ берёшь `code_word_suggestion` напрямую. Спроси пользователя одной строкой: «Какое код-слово на этот Reel? (запрет универсальных. Hint: автор использовал [code_word_suggestion])»
- Конкретная выгода: спроси: «Что пришлёшь по код-слову? (PDF / шаблон / список / калькулятор / другое)»

### Шаг R6. Финал

После всех слайдов:

**Caption поста** (текстом в чате):
- Hook 2-3 строки (переписан из cover headline)
- Body 5-7 предложений (краткий пересказ steps)
- CTA 1 строка: «Пиши [КОД-СЛОВО] [конкретная выгода]»

**Метаданные:**
- ФОРМУЛА оригинала: tutorial step-by-step
- DNA: [какую выбрал]
- N слайдов: 1 cover + 7 body + 1 CTA = 9 (или сколько по steps)
- КОД-СЛОВО: [verbatim]
- Язык: [как было в structure.json]

## ВАЖНО

1. UI-кропы — РЕАЛЬНЫЕ файлы от пользователя. НЕ генерируй UI через DALL-E. ВСЕГДА вставляешь готовый PNG в композицию через Code Interpreter.
2. Watermark — стандартный модуль, применяется ко ВСЕМ слайдам (cover + body + CTA).
3. Язык карусели = язык структуры (из structure.json). Перевод только по явной команде override.
4. Если в transcript step попадает «and nodes» / каптион автора оригинала — НЕ цитируй дословно, а перепиши своими словами (мы делаем CONTENT уникализацию, а не копию).
5. Hook на cover должен быть в формуле 3 тезиса активным голосом — это правило для всех hooks Custom GPT.
6. Не пиши на cover «как у автора X» / любое упоминание оригинала. Карусель = автономный продукт.