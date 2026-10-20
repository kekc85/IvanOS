# Workflow 01c - Mode C: Transcript (из надиктовки)

**Назначение:** разобрать надиктовку / длинный текст в атомарные carousel-смыслы.
**Вход:** `brief.mode = "transcript"` + длинный текст (>500 знаков) в `brief.raw_input`
**Выход:** выбранный смысл + verbatim quotes + передача в `01-finalize.md`

---

## Шаг 1 - Read контекст автора (voice anchor)

Параллельно:

1. `paths.voice_reference` - gold-standard примеры голоса
2. `paths.brand_dna` - archetype + signature phrases
3. `paths.avatar` - кому адресовано

Помечать `mandatory_reads`.

---

## Шаг 2 - Extraction в атомарные смыслы

```yaml
extracted_meanings:
  - meaning_id: 1
    verbatim_quote: "<точная цитата из надиктовки>"
    meaning_summary: "<1 строка что автор сказал>"
    family_hint: "<framework | listicle | story | panorama>"
    proof_elements: ["<если автор упомянул числа / продукты / имена>"]
    energy: "high | medium | low"
```

**Правила extraction:**
- 1 смысл = 1 атомарная мысль = 1 carousel
- Verbatim - дословно, не парафраз
- 3-10 смыслов (зависит от длины надиктовки)
- HIGH energy в приоритете

---

## Шаг 3 - User выбирает top-1-3

Показать 3-10 смыслов:

```
1. [HIGH energy] [framework hint] «Контент-завод = 7 систем»
   Цитата: «...контент-завод - это не один инструмент, а 7 систем...»
   Доказательства: 7 систем (из Распаковки бренда)

2. [MEDIUM] [story hint] «Лиза 940К ₽ через вайбмаркетинг»
   Цитата: «...вот Лиза, моя ученица - 940 тысяч за 6 недель...»
   Доказательства: имя, цифра, тайминг
```

User выбирает 1-3 (top - обычно 1).

---

## Шаг 4 - Brief на выбранный смысл

```yaml
brief:
  mode: "transcript"
  topic: "<meaning_summary>"
  family: "<family_hint>"
  source_quotes: ["<verbatim из автора>"]
  hook_seed: "<генерируется на основе verbatim_quote>"
  proof_elements: [...]
  voice_anchor: "verbatim quote"
```

**Voice preservation rule:** слова из `source_quotes` priority над «причёсанной» формулировкой. Авторская интонация важнее grammar.

---

## Шаг 5 - Передача в finalize

Перейти в `workflow/01-finalize.md`.

---

## Принципы

1. **Verbatim, не парафраз.** Цитата переносится дословно.
2. **Атомарные смыслы.** 1 атом = 1 carousel.
3. **HIGH energy priority.** Эмоциональные фразы → лучше hook.
4. **Proof elements mandatory.** Числа / имена / продукты - включить.
5. **3-10 range.** Меньше - недостаточно выбора, больше - расфокус.