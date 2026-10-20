---
name: mobile-preview-rules
version: 1.0
description: Mobile-first preview rules для email-машины контент-завода автора (Subject truncation, preheader display, above-fold preview pane). Применяется в workflow/03-write.md при написании Subject + Preheader + first paragraph и в workflow/04-review.md как mobile-first checklist gate.
---

# Mobile Preview Rules

## Введение

По данным Litmus Email Client Market Share 2024, 70%+ email opens происходят на mobile devices. Из них iOS Mail + Gmail iOS App покрывают 60%+ всех mobile opens. Это значит что email-машина автора пишет в первую очередь под mobile preview pane (Subject + Preheader + первые 200 chars body), а не под desktop reading experience.

Mobile-first rules не делают письмо хуже на desktop. Они делают inbox-decision (открыть или удалить) предсказуемым на 70% базы.

## Subject Truncation per Client

Subject в inbox view обрезается клиентом. Точная длина зависит от модели устройства, ориентации (portrait vs landscape) и font scaling. Baseline rules:

- iOS Mail (portrait): 30-40 chars truncation
- iOS Mail (landscape): 60-80 chars
- Gmail iOS App: 35-50 chars
- Outlook iOS App: 30-45 chars
- Apple Watch notification: 25-35 chars
- Android Gmail: 35-50 chars
- Android Outlook: 30-45 chars

### Rule of thumb

Первые 40 chars Subject должны быть самостоятельным смыслом. Если Subject осмыслен только при полном чтении 60+ chars, на 70% базы он покажется как обрезанная фраза без контекста.

Тест: написать Subject, отсчитать 40 chars, прочитать только эти 40 chars вслух. Если первая половина читается как полноценный hook, OK. Если как «Почему я больше не пишу dai…», fail, переписать.

### Subject length recommendations

- Optimal: 30-40 chars (полностью видно на iOS Mail portrait)
- Acceptable: 41-50 chars (видно в Gmail iOS, обрезано в iOS Mail но смысл сохраняется)
- Avoid: 51-60 chars (обрезано везде, нужен очень сильный first-40-chars hook)
- Hard fail: 60+ chars

## Preheader Display

Preheader (preview text) показывается рядом с Subject в большинстве inbox views. Это вторая строка inbox decision.

- iOS Mail: 50-80 chars (one line)
- Gmail iOS: 60-90 chars
- Outlook iOS: 50-70 chars
- Android Gmail: 60-90 chars

### Rule

50-90 chars sweet spot. Preheader должен дополнять Subject новым углом, не дублировать.

Bad: Subject «Открыл курс вайбкодинг» + Preheader «Курс открыт сегодня». Дубль, waste of inbox space, Gmail классифицирует как low-quality.

Good: Subject «Открыл курс вайбкодинг» + Preheader «Гарантия возврата 14 дней, рассрочка 0%». Subject = action, preheader = risk reversal + payment.

### Если Preheader не задан

ESP (Kit, Beehiiv) подставит первую строку body как preheader. Это часто ломает first paragraph (он начинается с hook'а, не с самостоятельной фразы). Всегда задавать preheader явно.

## Above-fold Preview (Preview Pane)

Multiple клиентов показывают первые 150-200 chars body в preview pane до того как читатель открывает письмо целиком.

- Gmail desktop preview pane: first ~200 chars body
- Outlook desktop preview pane: first ~200 chars body
- Mobile preview pane (Gmail iOS, Outlook iOS): first 150-200 chars

### Rule

Первый параграф body ≤ 200 chars, самодостаточный mini-pitch. Не открывает новую мысль которая требует scroll для понимания. Заканчивается интригой или soft CTA, а не оборванной фразой.

Bad first paragraph: «Когда я впервые попробовал собрать курс по вайбкодингу, я столкнулся с тем что подавляющее большинство существующих курсов сосредоточены вокруг базовых техник промптинга и не учитывают того что реально нужно тем кто запускает свой первый продукт». 280 chars, обрезано на «не учитывают того», читатель не знает чем закончится мысль.

Good first paragraph: «Запускаю курс вайбкодинг 15 июня. Внутри метод который я обкатывал на 800+ учениках. Подробности ниже». 110 chars, законченная мысль, есть хук («подробности ниже») к продолжению.

## Above-fold для Sales-Letter

Sales-letter (cart открыт / open-cart / close-cart) имеет дополнительное требование: CTA #1 above-fold. Тёплая база которая уже знает offer не должна скроллить чтобы найти ссылку на checkout.

### Recommended structure

- Subject (≤40 chars hook)
- Preheader (50-90 chars value + risk reversal)
- First paragraph (200 chars, hook + main offer-claim)
- Second paragraph (100-200 chars, soft proof element)
- CTA-link inline в третьем параграфе или явная кнопка (если HTML) на уровне ~400-500 chars от начала body

Это означает что CTA #1 видна в preview pane на большинстве клиентов (Gmail desktop ~500 chars above-fold). Cold-reader получает context, warm-reader сразу кликает.

### Counter-example

CTA только в конце письма 800 слов. Warm-reader (готов купить с Day 0) скроллит вниз пытаясь найти checkout link, теряет момент, закрывает письмо. Конверсия sales-letter падает на 30-50%.

## Common Mobile Failures

### Subject обрезается на словах

«Почему я больше не пишу daily content» → «Почему я больше не пишу dai…». Перепиши: «Почему перестал писать daily» (28 chars, полностью видно).

### Preheader дублирует Subject

«Открыли курс! / Курс открыт сегодня!». Решение: preheader как complementary angle (risk reversal, время, цена).

### First paragraph 400 chars без break

Большой блок текста на mobile screen = wall of text, читатель закрывает. Решение: первый параграф ≤200 chars, второй ≤200 chars, между ними visual break (пустая строка).

### Image-only above-fold

Если письмо начинается с hero image, и Gmail / Outlook блокируют images by default (~30% случаев), читатель видит пустоту above-fold. Решение: HTML письма всегда имеют text-first above-fold, image как enhancement, не как main content.

### CTA-link в виде text-without-link

«перейти на author dot com» вместо clickable link. Mobile tap target не работает. Решение: всегда явная `<a href>` или markdown link `[текст](url)`.

## Mobile-first Checklist (для каждого письма)

Применяется в workflow/04-review.md перед output.

- ✓ Subject ≤40 chars truncation safe (первые 40 chars читаются как самостоятельный hook)
- ✓ Preheader 50-90 chars, дополняет Subject новым углом (не дубль)
- ✓ First paragraph ≤200 chars, законченная мысль
- ✓ First sentence короткая (≤60 chars)
- ✓ CTA-link рабочий на mobile (явный link или button с touch target ≥44px height в HTML)
- ✓ Без image-зависимого смысла above-fold (тест: блокирую images, теряется ли смысл первого экрана)
- ✓ Один primary CTA на screen-height на mobile (~600px) sales-letter, не два конкурирующих
- ✓ Sales-letter: CTA #1 в первых 400-500 chars body

Если хотя бы один пункт fail, переписать соответствующий элемент перед output.

## Plain-text vs HTML Mobile

### Kit (default plain-text)

Kit отправляет email в формате который выглядит как plain-text но с link-rendering. На mobile это даёт максимальную совместимость: нет broken layouts, font scaling работает естественно, images по умолчанию отсутствуют (нет image-block риска). Open rate Kit на mobile стабильно 5-8% выше чем HTML-heavy ESP при равной базе.

Trade-off: нет visual brand. Для info-products автора это OK, brand живёт через voice, не через visual identity email.

### Beehiiv (default HTML)

Beehiiv шлёт HTML с rich layouts. На mobile нужен testing на минимум 3 клиентах (Gmail iOS, iOS Mail, Outlook iOS) перед первым broadcast. Common issues: multi-column layouts ломаются на iOS portrait, font-size <14px нечитаем на retina, hero image без alt-text = пустота при block.

Если используется Beehiiv, обязательное тестирование Litmus или Email on Acid перед первым live запуском. Если ресурсов на тестирование нет, выбрать single-column layout + 16px base font + alt-text на все images.

## Anti-patterns

### Long Subject (>60 chars)

Обрезается везде, теряет hook. Переписать в <40 chars.

### Preheader missing

ESP подставит первую строку body, что обычно ломает hook. Всегда задавать preheader явно.

### Image-dependent above-fold

Hero image как единственный element above-fold. При image-block (30% случаев) читатель видит пустоту. Решение: text-first above-fold.

### Multi-column layout HTML

Breaks on iOS portrait, mobile reader видит broken layout. Решение: single-column.

### Tiny font (<14px)

Невозможно прочитать на retina screen без zoom. Решение: base font 16px, headings 20px+.

### CTA-button text-only

«Купить курс» без visible button styling в HTML. Mobile reader не воспринимает как clickable. Решение: явная кнопка с background-color, padding ≥12px, font-weight bold, явный underline или контрастный цвет.

### Em-dash в Subject

«Курс вайбкодинг - открыт». Memory rule: только дефис. Переписать: «Курс вайбкодинг открыт» или «Курс вайбкодинг: открыт».

### Нельзяграм в письме

Memory rule: всегда «Нельзяграм». 