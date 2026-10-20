---
name: preheader-patterns
version: 1.0
description: 12 паттернов preheader (inbox snippet) с RU + EN примерами, anti-dup правило, synergy strategy с Subject. Подгружается workflow/02-structure.md и workflow/03-write.md.
---

# 12 паттернов Preheader для email-машины автора

Preheader это текст-сниппет который inbox показывает после Subject. На mobile он часто видим перед открытием письма, на desktop в превью. Это второе предложение твоего email-хука, которое работает в паре с Subject.

Длина preheader: 50-90 chars оптимально. Apple Mail iOS показывает 50-80 chars, Gmail mobile 60-90, Outlook 55-75. Если короче 40 chars, inbox добирает текст из body (часто это "View in browser" или код unsubscribe link, что убивает open rate). Если длиннее 100 chars, обрезается ".." на середине мысли.

Preheader работает как партнёр Subject. Subject обещает / задаёт hook, Preheader усиливает / даёт context / противопоставляется. Они НЕ должны дублировать друг друга.

## 12 паттернов

### 1. Continuation

Продолжает Subject как часть одного предложения.

- RU Subject: "Я облажался вчера на эфире"
  Preheader: "...и вот что я понял через 24 часа"
- EN Subject: "I messed up yesterday"
  Preheader: "...and here is what I figured out 24 hours later"

### 2. Question add-on

Subject утверждает, Preheader задаёт ребром вопрос.

- RU Subject: "Контент-план на месяц это ерунда"
  Preheader: "Или ты до сих пор пишешь его каждое воскресенье?"
- EN Subject: "30-day content plans are bullshit"
  Preheader: "Or are you still making one every Sunday?"

### 3. Specifics

Добавляет конкретную цифру / факт.

- RU Subject: "3 промпта которые я использую каждый день"
  Preheader: "Конкретно: 47 минут экономии в день, посчитал"
- EN Subject: "3 prompts I use every day"
  Preheader: "Exact saving: 47 minutes per day, measured"

### 4. Personal hook

Личный момент, контекст или признание.

- RU Subject: "Как я собрал контент-завод за выходные"
  Preheader: "Расскажу как я облажался в первую попытку"
- EN Subject: "How I built a content factory in a weekend"
  Preheader: "Including how I failed on attempt one"

### 5. Curiosity gap

Обещает inside / spoiler / secret внутри письма.

- RU Subject: "Я больше не пишу посты по расписанию"
  Preheader: "Внутри: одна простая замена которая работает лучше"
- EN Subject: "I no longer post on a schedule"
  Preheader: "Inside: one simple replacement that works better"

### 6. Time-anchored

Указывает на timing / read time / momentum.

- RU Subject: "Готовый шаблон оффера для запуска"
  Preheader: "5 минут чтения, применить можно за час"
- EN Subject: "Ready-to-use offer template"
  Preheader: "5 min read, applicable in an hour"

### 7. Contrarian

Идёт против Subject или общепринятого, создаёт противоречие.

- RU Subject: "5 шагов к первому клиенту"
  Preheader: "И почему это противоположно тому что советуют все"
- EN Subject: "5 steps to your first client"
  Preheader: "And why it is the opposite of what everyone teaches"

### 8. Number reveal

Раскрывает спойлер-цифру из тела письма.

- RU Subject: "Что я заработал в первый месяц курса"
  Preheader: "Спойлер: 327 000 руб, и большая часть из одного канала"
- EN Subject: "What I made in month 1 of my course"
  Preheader: "Spoiler: 5247 dollars and most of it from one channel"

### 9. Story tease

Приглашает в историю / рассказ.

- RU Subject: "То чего я не делал последние 6 месяцев"
  Preheader: "История начинается с провала в марте"
- EN Subject: "What I have not done for 6 months"
  Preheader: "The story starts with a failure in March"

### 10. Direct benefit

Называет конкретный outcome который читатель получит из письма.

- RU Subject: "5 промптов которые экономят 10 часов"
  Preheader: "Результат: контент на неделю за один вечер"
- EN Subject: "5 prompts that save 10 hours"
  Preheader: "Outcome: a week of content in one evening"

### 11. Question to reader

Вопрос напрямую к читателю, провоцирующий ответ.

- RU Subject: "Контент-завод за выходные"
  Preheader: "А ты пробовал хоть раз? Честно"
- EN Subject: "Content factory in a weekend"
  Preheader: "Have you actually tried it? Be honest"

### 12. P.S. preview

Намекает на бонус / подарок / surprise в P.S.

- RU Subject: "Признание: я не пишу свои письма сам"
  Preheader: "P.S. в конце мой Claude промпт, бери"
- EN Subject: "Confession: I do not write my emails myself"
  Preheader: "P.S. at the end grab my Claude prompt"

## Anti-dup правило

Subject и Preheader НЕ должны быть парафразом друг друга. Тест на similarity: убрать стоп-слова, оставить content words, посчитать долю общих слов. Если общих > 70%, дубль, переписывать.

Плохо (similarity ~0.9):
- Subject: "5 шагов к первому клиенту"
- Preheader: "Пять шагов до первого клиента в этом письме"

Хорошо (similarity ~0.2):
- Subject: "5 шагов к первому клиенту"
- Preheader: "И почему это противоположно тому что советуют все"

Простой ручной тест: «можно ли поменять Subject и Preheader местами и смысл не изменится?» Если да, переписывать Preheader, он добавляет второй угол атаки.

## Synergy strategy

Subject и Preheader это дуэт. У дуэта три рабочие стратегии:

**1. Усиление.** Preheader усиливает обещание Subject через specificity / time / proof.
- Subject: "Как я собрал контент-завод за выходные"
- Preheader: "Конкретно: 11 reels за 18 часов работы"

**2. Контекст.** Preheader даёт фон / условия / oговорку.
- Subject: "Я больше не пишу посты по расписанию"
- Preheader: "Контекст: после года писательства по графику"

**3. Противопоставление.** Preheader создаёт контраст, провоцирующий читателя открыть.
- Subject: "5 шагов к первому клиенту"
- Preheader: "И почему ни один из них не про сторис"

Правильный preheader проходит тест: «если Subject зацепил на 60%, добавил ли preheader недостающие 40% чтобы открыли?»

## Mobile preview

ESP-specific длины (на 2026):

| Клиент | Preheader visible chars |
|---|---|
| Apple Mail iOS portrait | 50-80 |
| Apple Mail iOS landscape | 90-110 |
| Gmail mobile | 60-90 |
| Gmail desktop (preview pane) | 100-120 |
| Outlook mobile | 55-75 |
| Outlook desktop | 90-110 |

Правило: ключевая мысль preheader в первые 50 chars. Дальше дополнения которые могут обрезаться без потери смысла.

Плохо: "Внутри: то о чём я молчал весь год узнаешь только если откроешь" (62 chars, hook на 39м символе "то о чём я молчал")

Хорошо: "Молчал об этом весь год. Внутри почему" (38 chars, hook сразу)

## Anti-patterns

Запрещённые preheaders:

- Generic ("Click here", "Read more", "Open this", "Перейди по ссылке")
- Парафраз Subject (similarity > 0.7)
- "View in browser" / "If you cannot see this email" как preheader (это сигнал что preheader НЕ задан и inbox грабит первую строку)
- Unsubscribe link / footer текст
- Пустой preheader (≤ 20 chars), inbox грабит body
- HTML / merge tags не закрытые: "{first_name}, привет!"
- ВСЕ ЗАГЛАВНЫЕ
- Дубль hook из Subject другими словами

## Cross-references

- references/subject-formulas-50.md 50 формул Subject которые работают в паре с preheader
- references/mobile-preview-rules.md детальные правила mobile preview по ESP
- references/spam-triggers-list.md слова которые НЕ должны попадать в preheader (spam folder risk)
