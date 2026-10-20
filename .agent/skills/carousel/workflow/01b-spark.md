# Workflow 01b - Mode B: Spark (ситуативный)

**Назначение:** превратить идею (B1) или запрос на идеи (B2) в carousel brief.
**Вход:** `brief.mode = "spark-b1" | "spark-b2"` + `brief.raw_input`
**Выход:** обогащённый `brief` + передача в `01-finalize.md`

---

## Sub-flow B1 - User дал тему

### B1.1 - Распарсить тему

Извлечь из raw_input:
- **topic_core** - основная тема (1-5 слов)
- **angle_hint** - если есть подсказка угла
- **platform_hint** - если указана платформа

### B1.2 - GATE: Mandatory Reads (≥2/4)

Прочитать минимум 2 из 4:

1. `paths.avatar` - кому
2. `paths.jtbd` - какой JTBD
3. `paths.brand_dna` - голос
4. `paths.products_dir/` - продукт-якорь

**GATE FAIL:** <2 → re-attempt + force brand_dna + avatar.

### B1.3 - Расширить тему в 5-7 углов

```yaml
angles:
  - angle_id: 1
    family_hint: "framework-breakdown"
    one_liner: "N ходов вайбмаркетинга которые я применяю каждый день"
    hook_seed: "8 ходов вайбмаркетинга. <твоя выручка> позже - вот они:"
    
  - angle_id: 2
    family_hint: "listicle"
    one_liner: "6 инструментов которыми я строю воронку без кода"
    hook_seed: "Stack который заменил $50K/year маркетингового консультанта:"
    
  - angle_id: 3
    family_hint: "story-case"
    one_liner: "Как Лиза сделала 940К ₽ на запуске за 6 недель"
    hook_seed: "Лиза. 940 000 ₽ за 6 недель. С нуля. История:"
    
  - angle_id: 4
    family_hint: "panorama"
    one_liner: "Вайбмаркетинг больше не profession (panorama reveal)"
    hook_seed: "ВАЙБМАРКЕТИНГ растянутый через 8 slides"
    
  - angle_id: 5
    family_hint: "framework-breakdown"
    one_liner: "Мой контент-завод: что внутри (методология)"
    hook_seed: "Контент-завод = 7 систем работающих вместе. Разбор:"
```

**MECE rule:** углы не пересекаются, на одной оси, покрывают разные family.

### B1.4 - User выбирает

Показать 5-7 углов кратко (1-liner + family + hook_seed). User выбирает angle / override family / override platform.

После выбора → brief.topic / brief.family / brief.hook_seed.

---

## Sub-flow B2 - User просит идеи

### B2.1 - GATE: Mandatory Reads (≥4/7)

Прочитать минимум 4 из 7:

1. `paths.avatar`
2. `paths.jtbd`
3. `paths.objections`
4. `paths.brand_dna`
5. `paths.products_dir/`
6. `paths.content_map` (если есть)
7. recent_carousels (no-repeat)

**GATE FAIL:** <4 → re-attempt.

### B2.2 - Генерация 5-7 идей под JTBD

```yaml
ideas:
  - idea_id: 1
    jtbd_addressed: "Понять что такое вайбмаркетинг и зачем"
    topic: "Карта инструментов AI-маркетинга 2026"
    family_hint: "framework-breakdown"
    hook_seed: "30 инструментов AI-маркетинга 2026. На каждый этап воронки:"
    why_now: "Свежий запрос аудитории в комментариях за неделю"
    
  - idea_id: 2
    jtbd_addressed: "Преодолеть страх «я не программист»"
    topic: "5 проектов которые я сделал голосом без кода"
    family_hint: "listicle"
    hook_seed: "5 проектов. 0 строк кода. Только голос. Stripe внутри:"
```

**Идеи должны:**
- Закрывать конкретные JTBD из `paths.jtbd`
- НЕ повторять recent_carousels (7 дней)
- Иметь разные family (MECE по углу)
- Опираться на verifiable assets автора

### B2.3 - User выбирает

Показать 5-7 идей. User выбирает 1-3. Top-1 → продолжить в finalize.

---

## Шаг C - Передача в finalize (общая)

```yaml
brief:
  mode: "spark-b1" | "spark-b2"
  topic: "<chosen one_liner>"
  family: "<chosen или null>"
  hook_seed: "<initial hook>"
  source_quotes: []
  angle_pool: [...]  # сохранить для A/B
```

Перейти в `workflow/01-finalize.md`.

---

## Принципы

1. **GATE mandatory reads - hard.** Не генерить без контекста автора.
2. **MECE углы.** На разных осях, не вариации одной мысли.
3. **No-repeat strict.** 7-day window для тем.
4. **JTBD-driven в B2.** Каждая идея отвечает на JTBD.
5. **Hook seed verifiable.** Числа/имена/продукты - только из `.business/`.