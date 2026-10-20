# Workflow 02c - Tuple Choice (Co-creation Lane)

> **Project-aware (NEW):** matrix genre×value×JTBD читать из `{active.jtbd_value_map}`. Для project=default = `references/genre-value-jtbd-mapping.md` (вайбкодинг J1-J7). Для health = `post-pack/jtbd-value-map.md` (J: сон/живот/энергия/эмоции/сладкое/цикл/самообвинение). НЕ подмешивать вайбкодинг-JTBD в сторонние проекты.

**Назначение:** предложить автору 3 варианта tuple `(genre × value × JTBD)` на основе research summary. автор выбирает один → fixed в outline.tuple. Дальнейшие стадии (02d / 02e / 02f) опираются на этот выбор.
**Триггеры:** после `02b-research-summary.md` в co-creation lane.
**Входы:** `outline.research_summary` + `outline.genre`.
**Выходы:** `outline.tuple = (G?, V?, J?)` - fixed выбор автора.
**Следующая стадия:** `workflow/02d-components-options.md`.

---

## Принцип

Genre уже зафиксирован на Pass 0.5 (это форма). Остаётся выбрать:
- **Value-vector** (V1-V6) - что доставить читателю
- **JTBD** (J1-J7) - на какую работу читателя пост работает

Эти две оси НЕ свободны. Они ограничены matrix-table из `references/genre-value-jtbd-mapping.md` (Fix 4 output). Часть ячеек = **hard-abort** (комбинация не работает структурно - например G3 alarm × V5 strategic). Часть = **strong**. Часть = **weak но допустимы**.

Skill сам выбирать tuple НЕ должен - это marketing decision автора. Но skill обязан **сузить выбор до 3 valid вариантов с rationale**, чтобы автор не тратил время на отбраковку hard-abort cells.

---

## Шаг 1 - Read genre-value-jtbd-mapping

Прочитать `references/genre-value-jtbd-mapping.md` (Fix 4 output).

Извлечь:
- **Matrix table genres × values** (какие V допустимы для current genre)
- **Hard-abort cells** (помечены `❌` или `abort`)
- **Strong combinations** (помечены `★★★` или `strong`)
- **JTBD compatibility** (для каждой valid V - какие J1-J7 работают, какие нет)

Запомнить **только строки для `outline.genre`** (G1/G2/G3/G4/G5).

---

## Шаг 2 - Generate 3 valid tuples

Сгенерировать **ровно 3 tuple `(G, V, J)`** под current genre.

**Правила отбора:**

1. **G фиксирован** = `outline.genre` (одинаков во всех 3 tuples)
2. **V varied** - 3 разных value-vectors (не повторять). Приоритет:
   - Сначала strong-cells по matrix
   - Если strong < 3 - дополнить allowed-cells
   - Hard-abort cells = **запрещены**
3. **J varied** - приоритет J которые matches `outline.research_summary.case_studies` / Karta sections. JTBD для которого нет proof в research summary = **не предлагать**.

**Фильтр по research_summary:**
- Если для tuple (G, V, J) **нет proof в research_summary.available_value_vectors** под этот V → skip
- Если для tuple **нет case_studies / karta_sections под этот J** → skip
- Если после фильтра valid tuples < 3 → **ESCALATE** («research summary не покрывает 3 valid combos - нужно расширить summary или сменить genre»)

**Пример output (для G1 narrative-кейс, topic «первые продажи без аудитории»):**

```yaml
tuple_options:
  - id: T1
    G: G1 (narrative-кейс)
    V: V4 (case study)
    J: J2 (первые 100-500К без аудитории 10К)
  - id: T2
    G: G1 (narrative-кейс)
    V: V1 (insight)
    J: J1 (первые автооплаты)
  - id: T3
    G: G1 (narrative-кейс)
    V: V6 (original frame)
    J: J6 (без камеры / контент-завод)
```

---

## Шаг 3 - Rationale для каждого tuple

Для каждого из 3 tuples написать **3-уровневое обоснование**:

1. **Почему этот value-vector работает с этим genre** (matrix-cell strength + 1 sentence)
2. **Почему этот JTBD доступен** (какой case study / Karta section из research_summary его покрывает)
3. **Ожидаемый insight для читателя** (1 sentence - что читатель уносит)

**Шаблон:**

```
T1 - G1 × V4 × J2
- V4×G1 strength: ★★★ (narrative-кейс структурно создан под case study; matrix-cell strong)
- J2 proof в summary: <имя ученика> (gold-standard пост 8) - реальный кейс «с 0 до $100K» под J2
- Ожидаемый insight: «база 800 даёт первые продажи если оффер на JTBD-2, а не количество подписчиков»

T2 - G1 × V1 × J1
- V1×G1 strength: ★★ (insight внутри case = живо, но требует non-obvious наблюдения)
- J1 proof в summary: канон #5 «5 уведомлений за выходные» + case <имени ученика>
- Ожидаемый insight: «20К подписчиков ≠ продажи, конверсия маленькой базы на JTBD выше чем большой холодной»

T3 - G1 × V6 × J6
- V6×G1 strength: ★★ (frame через case = легко скатиться в proof-by-example, нужна осторожность)
- J6 proof в summary: термин «контент-завод» (Распаковка) + Карта 2.1 root cause
- Ожидаемый insight: «контент-завод снимает зависимость от съёмок - это и есть путь без камеры»
```

---

## Шаг 4 - Show автору 3 options + recommendation

Output в чат **компактным форматом** (не Write в файл):

```
## Tuple options (3)

**T1 - G1 × V4 × J2** (RECOMMENDED ★★★)
- Что делаем: рассказываем кейс <имени ученика> с фокусом на «первые 100-500К без аудитории 10К»
- Value: V4 case study с real цифрой ($100K) + механика
- JTBD: J2 - твоя core аудитория (малая база 100-3000)
- Insight: «база 800 даёт первые продажи если оффер на JTBD-2»

**T2 - G1 × V1 × J1**
- Что делаем: кейс с фокусом на insight «подписчики ≠ продажи»
- Value: V1 insight с numerical proof (20K vs копейки)
- JTBD: J1 - первые автооплаты
- Insight: «конверсия маленькой базы > большой холодной»

**T3 - G1 × V6 × J6**
- Что делаем: кейс через рамку контент-завода
- Value: V6 proprietary frame
- JTBD: J6 - без камеры
- Insight: «контент-завод = путь без зависимости от съёмок»
- Caveat: легко скатиться в proof-by-example, нужна осторожность

Recommendation: **T1** - strongest matrix-cell + real case в gold-standard + покрывает core JTBD.

Какой берём - T1 / T2 / T3? Или модифицируем?
```

**Recommendation rule:**
- Strongest matrix-cell (★★★) > ★★ > ★
- Tie-break: tuple с лучшим proof в research_summary (real case > Karta quote > общий контекст)
- Tie-break 2: tuple с JTBD ближе к core avatar (J1/J2/J3 > J4/J5/J6/J7)

---

## Шаг 5 - Зафиксировать выбор

После ответа автора:

- Если выбран один из T1/T2/T3 → `outline.tuple = (G?, V?, J?)`
- Если автор модифицирует («хочу G1 × V1 × J2») → проверить что combo не hard-abort по matrix → если valid, fixed как `outline.tuple`
- Если автор выбирает hard-abort combo → объяснить почему не работает + предложить ближайший valid
- Если автор «не нравится ни один» → вернуться в 02b с уточнением topic / angle

**Записать:**

```yaml
outline.tuple:
  G: "G1"
  G_name: "narrative-кейс"
  V: "V4"
  V_name: "case study"
  J: "J2"
  J_name: "первые 100-500К без аудитории 10К"
  rationale: "<short text почему этот выбор fixed>"
  chosen_by: "ivan"  # или "modified" если автор дописал
```

---

## Output stage 02c

Передаётся в stage 02d:

```yaml
outline:
  # carry-over из 02b
  topic: "..."
  genre: "G1|G2|G3|G4|G5"
  research_summary: {...}
  factbase_path: "<путь факт-базы из 02b, AC5 - прокидывается неизменным до 03-dry/04>"
  lane: "co-creation"

  tuple:
    G: "..."
    V: "..."
    J: "..."
    rationale: "..."
```

**Передать в:** `workflow/02d-components-options.md`.
