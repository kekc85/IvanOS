# Maxwell Ross 9-checklist (video-adapted)

Pre-publish gate. 9 yes/no вопросов. **Cutoff: 9/9 PASS обязательно.**

Применяется в `workflow/05-review.md` стадия 5.4. Если 8/9 - переписать так чтобы 9-й прошёл. Если ≤7/9 - эскалация в чат.

## 9 пунктов

### 1. Idea - есть ли центральная идея в одно предложение?

Тест: сформулируй в чат одной фразой что зритель унесёт. Если получается «несколько вещей» - split на серию.

❌ FAIL: «Видео про Claude и про маркетинг и про контент»
✅ PASS: «Claude Code заменяет 3 SaaS подписки» - одна идея

### 2. Clarity - понятно ли с первого просмотра?

Тест: дай скрипт человеку который никогда не слышал про авторское - поймёт за один прогон?

❌ FAIL: жаргон без объяснения, hidden context required
✅ PASS: каждый термин либо известен либо immediately introduced

### 3. Payoff - есть ли выплата зрителю в конце?

Тест: зритель в финале получает emotional or practical resolution?

❌ FAIL: финал = «давайте обсудим в комментариях»
✅ PASS: финал = explicit takeaway + emotional landing

### 4. Specificity - есть ли конкретика?

Тест: минимум 1 конкретное число / имя / артефакт.

❌ FAIL: «многие люди делают эту ошибку»
✅ PASS: «3 из 5 моих учеников делают эту ошибку - вот она»

### 5. Freshness - не повторяет ли предыдущие видео?

Тест: read track-record последние 30 записей. Тема + угол не должны повторяться.

❌ FAIL: «вайбкодинг - это методика» (уже было 3 раза)
✅ PASS: «вайбкодинг под маркетолога: чем отличается от программерского»

### 6. Hook strength - первые 1.5-3 sec проходят stop-scroll?

См. отдельный Hook Strength Gate (5.2). Этот item Maxwell Ross дублирует - gating.

### 7. Length fit - попадает в target tier (floor + ceiling)?

Тест: total_duration_sec в [floor, ceiling] из config.length_tiers[<tier>].

❌ FAIL: target 30-60s, факт 75s
✅ PASS: target 30-60s, факт 45s

### 8. Tone - voice автора не выдуман?

Тест: 5+ native lexicon terms используется. 0 banned terms. Em-dash отсутствует. Native verbs.

❌ FAIL: «эксперт по контент-фабрике использует современные методики»
✅ PASS: «ты гоняешь промпт, и контент-завод собирает шорт за 11 минут»

### 9. CTA - CTA в финале или explicit отсутствие?

Тест: либо явный single CTA, либо явное решение «без CTA, drop mic».

❌ FAIL: random «давайте подпишемся» в середине
✅ PASS: «коммент СБОРКА - пришлю промпт» в финале

## Output формат

В 05-review.md заполняется:

```yaml
maxwell_ross_9:
  idea: PASS
  clarity: PASS
  payoff: PASS
  specificity: PASS
  freshness: PASS
  hook_strength: PASS
  length_fit: PASS
  tone: PASS
  cta: PASS
  total: 9/9
```

Если total < 9/9 - список failed items + причины + decision (fix in 05 vs escalate).

## Anti-patterns при использовании

- Маркировка «PASS» без real check (memory `feedback_self_eval_not_qa`). Каждый item должен иметь конкретное обоснование в 1 строку.
- 8/9 «и так сойдёт» - нет. Переписать до 9/9.
- Пропуск freshness check «потому что мне лень читать track-record» - нет, без этого freshness fails повторно.

## Связано

- post references/maxwell-ross-9-checklist.md (sister) - те же 9 items адаптированы под TG-посты
- email references (sister) - те же 9 items + EMAIL-G1-8 деривации
