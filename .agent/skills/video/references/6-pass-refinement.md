# 6-Pass Refinement (video-adapted)

6 перспектив через которые прогоняется draft в `workflow/05-review.md` стадия 5.3.

Адаптация create-viral-content design pattern (был для длинных форм / Twitter) - переделана под video.

## Pass 1: Skeptic

**Вопрос:** «Зачем мне это смотреть?»

Skeptical viewer ничего не знает про автора. Каждый beat должен оправдать своё существование с его точки зрения.

**Tests:**
- В первые 3 sec sceptic понимает value proposition?
- Каждый body beat даёт что-то новое (не повтор предыдущего)?
- Payoff = реальная выплата, не «обсудим в комментах»?

**Fix patterns:**
- Hook слабый → переписать с больше contrast / numeric outlier
- Body beat = повтор → удалить или переделать
- Payoff = vague → конкретизировать

## Pass 2: Scroller

**Вопрос:** «Остановит ли scroll в 1.5 sec?»

Scroller - это algorithm-shaped user. Решение «продолжить смотреть» принимается в первые 1.5-3 sec. Дальше - задача удержания.

**Tests:**
- Hook visual + caption + audio = ALL hit в первые 1.5 sec?
- Первое слово / первая caption - provocative / specific?
- Первый 3-sec ending = cliff / question / promise?

**Fix patterns:**
- Hook слабый → применить Pattern 1-8 из hook-patterns-8.md
- Open с «привет» / «сегодня я расскажу» → strip
- Open с general statement → make specific

## Pass 3: Producer

**Вопрос:** «Реально ли это снять?»

Producer думает о production reality. Если в скрипте говорится «и тут я показываю как Claude генерит full SaaS за 5 минут» - это снимаемо? Есть ли B-roll? Demo доступен?

**Tests:**
- Каждое action (показ / demo / B-roll) - производственно реализуемо?
- Длительность каждого beat соответствует производственной реальности (нельзя «показать сложный workflow за 3 sec»)?
- Production handoff downstream skill (face-cam / split / ai-avatar / replicate / before-after) - реалистично подходит?

**Fix patterns:**
- Несинхрон script vs visual (script говорит «вот N8N node» но снимать нужно «генерация Claude») → fix script или visual
- Beat предполагает невозможный assets (например, «студийная съёмка с 4 актёрами») → переписать в реалистичное (face-cam + AI b-roll)
- Production handoff vague → конкретизировать tools / steps

## Pass 4: Editor

**Вопрос:** «Темп / pacing / повторы?»

Editor - это редактор который чистит. Любая фраза без работы - на cutting room floor.

**Tests:**
- Есть ли повторы мысли (одна идея в разных beats)?
- Filler words («просто», «как бы», «такое») - убрать?
- Каждое предложение делает работу (новый smыcл / эмоция / переход)?
- Темп для tier правильный (shorts: 2.5 слов/sec; mid: чуть медленнее; long: variable)?

**Fix patterns:**
- Повторы → удалить или объединить
- Filler → strip
- Слишком быстрый темп в long-form → добавить пауз
- Слишком медленный в short → Hormozi-cut

## Pass 5: Algorithm

**Вопрос:** «Watch time / completion rate / saves / shares?»

Algorithm - это reach engine платформы. Сигналы которые он смотрит:
- Hook → watch time (первые 3 sec retention)
- Body → completion rate (досматривают до конца)
- Payoff → saves (стоит сохранить?)
- CTA или surprise → shares (delivers ли видео для рассказа другому?)

**Tests:**
- Hook strong enough для completion start?
- Mini-hook(s) середине для retention dip?
- Payoff даёт reason для saves?
- Финал даёт reason для shares (insight, useful info, surprise)?

**Fix patterns:**
- Mid-section sag (середина boring) → mini-hook
- Финал не save-able → переделать payoff в более concrete
- Финал не share-able → добавить surprise или counterintuitive insight
- CTA generic «like + subscribe» → specific «коммент СБОРКА» (single action)

## Pass 6: Voice

**Вопрос:** «Звучит ли как автор?»

Voice fidelity - это финальная проверка что не получился generic AI tone.

**Tests:**
- 5+ native lexicon terms используется?
- 0 banned terms (из config.lexicon_banned + ai-tells-catalog)?
- Em-dash отсутствует внутри строк?
- Action verbs > nouns?
- Архетип (Magician / Sage / Outlaw) консистентно держится?
- Mandatory Reads Pass 0 был выполнен (audit log в draft.passes_log.pass_0)?

**Fix patterns:**
- Voice generic → strict Pass 2/2.5 в 04-write (rewrite через _voice-TEMPLATE.md)
- Banned term detected → replacement из _voice-TEMPLATE.md
- Архетип wobble → выбрать один и держать
- Mandatory Reads пропущены → strict re-run

## Output формат (для 05-review.md)

```yaml
six_pass:
  skeptic:
    score: 8/10
    fixes_applied: ["...", "..."]
  scroller:
    score: 9/10
    fixes_applied: ["..."]
  producer:
    score: 10/10
    fixes_applied: []
  editor:
    score: 7/10
    fixes_applied: ["убраны 3 filler", "слиты 2 повтора"]
  algorithm:
    score: 8/10
    fixes_applied: ["добавлен mini-hook в sec 22"]
  voice:
    score: 9/10
    fixes_applied: ["заменено 'эксперт' на 'ты'"]
  
  total_avg: 8.5/10
  cutoff: 8.0+   # ниже = escape назад в 04
```

## Anti-patterns

- «Score 10/10» без real check (memory `feedback_self_eval_not_qa`)
- Skip Pass 6 «потому что voice subjective» - нет, voice проверяется через мandatory reads compliance
- Apply fixes без записи (audit log важен)
- Total < cutoff и всё равно переходить в 5.4 - нет, escape в 04