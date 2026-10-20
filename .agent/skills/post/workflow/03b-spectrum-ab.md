# Workflow 03b - Spectrum-then-Choice A/B варианты

**Назначение:** генерация двух архитектурно разных версий поста (A и B) через spectrum-then-choice по 4 структурным частям. Не перестановка одного параметра.

**Когда запускается:** после сборки в `02f-polish.md`, до `03-dry.md`, если `config.output.ab_variants ≥ 2`.

**Выход:** 2 готовых варианта (A и B) + Design Memo каждого (почему выбрали именно этот pick из спектра).

**Принципиальное отличие от прошлой версии A/B:**
- Раньше: A = numbered hook, B = contrarian hook (перестановка одного параметра).
- Сейчас: A и B - это два разных weighted pick по 4 частям (hook, setup, mass, close). Архитектурно разные посты на один и тот же angle.

Источник правила: memory `feedback_design_choices_not_just_stylization` .

---

## Шаг 1 - Развернуть спектр по 4 частям

Для одного зафиксированного `brief.angle` построить spectrum.

### Hook (4-6 опций)
- Numbered (цифра в начале / период / порядок)
- Contrarian («не делай X», «X больше не работает»)
- Personal stake («вчера я / на прошлой неделе»)
- Pattern interrupt («запомнил один факт / увидел странное»)
- Question (открытый вопрос читателю)
- Authority drop (имя / цифра / источник)

### Setup (4-5 опций)
- Context («происходит сейчас на рынке X»)
- Personal story (короткий эпизод)
- Reframe («все думают X - это не так»)
- Tension («одно работает - другое нет»)
- Counter-myth («распространённый совет неверен»)

### Mass / Body (4-5 опций)
- Numbered breakdown (1, 2, 3 пункта по сути)
- Single deep example (один кейс развёрнуто)
- Compare/contrast (A vs B по 2-3 осям)
- Step-by-step (последовательность)
- Inversion («что не делать»)

### Close (4-5 опций)
- Direct CTA (одна строка)
- Open question (читателю)
- Resource drop (ссылка / файл / комментарий)
- Cliffhanger («дальше расскажу как»)
- Statement (без вызова к действию, просто закрытие)

---

## Шаг 2 - Weighted choice для каждой опции

Для каждой 4-х частей: weight каждой опции по 3 критериям (1-5 шкала):
- **Brand fit** - соответствует архетипу из brand_dna (Magician / Sage / Outlaw для автора)
- **JTBD fit** - закрывает ли работа читателя из jtbd.md
- **Freshness** - не использовано в последних 5 постах канала (anti-repeat)

Total weight = sum 3 критериев. Максимум 15.

---

## Шаг 3 - Pick A = highest weight per part

Версия A = (highest hook, highest setup, highest mass, highest close).

---

## Шаг 4 - Pick B = highest weight НО разный pattern

Версия B = (highest для каждой части, **но другой опцион чем A**). Если для какой-то части #2 имеет вес отстающий от #1 более чем на 30% - отметить «B compromise: <part> weak», но всё равно взять #2 для разнообразия.

Edge case: если для какой-то части доступна только одна сильная опция (например, для tool-drop hook действительно работает только Authority drop) - зафиксировать одинаковый pick в A и B по этой части и компенсировать diff по другим 3 частям. В Design Memo указать «<part> locked, diff обеспечен по остальным 3».

---

## Шаг 5 - Render 2 версии полностью

Каждая версия = полный пост (не diff), прошедший через все валидаторы из 04-review.md.

---

## Шаг 6 - Design Memo на каждый вариант

```
## Версия A

Пост: <full text>

Design Memo:
- Hook: <chosen option> (weight X/15) - почему: <reason>
- Setup: <chosen option> (weight X/15) - почему: <reason>
- Mass: <chosen option> (weight X/15) - почему: <reason>
- Close: <chosen option> (weight X/15) - почему: <reason>

Архитектурный профиль: <одна фраза, например "холодный контраст с numbered breakdown">

## Версия B

Пост: <full text>

Design Memo:
... (всё то же)

Архитектурный профиль: <одна фраза, например "тёплая личная история с inversion">

## A vs B

| Часть | A | B | Diff |
|---|---|---|---|
| Hook | Numbered | Contrarian | разная позиция |
| Setup | Context | Personal story | разный entry |
| Mass | Numbered breakdown | Single deep example | разная глубина |
| Close | Direct CTA | Cliffhanger | разная плотность |

Рекомендация: <A или B> - почему: <одна фраза>
```

---

## Anti-patterns
- НЕ повторять одинаковый pick в A и B для всех 4 частей (тогда нет diff)
- НЕ менять только hook (это слабый A/B)
- НЕ выходить за brand_dna ни в одной из версий (Caregiver / Lover / Innocent banned - см. config.voice.archetypes_banned)
- НЕ нарушать banned AI-tells: код-банк `scripts/lint-post.py` + `config.md` `lexicon_banned_hard` + внешний `config.voice_canon.voice_profile` (раздел Voice Drift Detection). Пустой шаблон `references/_voice-TEMPLATE.md` списком классов НЕ является
- НЕ выдумывать факты в одной версии для разнообразия (memory `feedback_no_inventing_facts`)
