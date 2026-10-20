# Dr. Alvaro Cintas (@drcintas) — AI-агенты в 3D-офисе (один GitHub-проект)

> URL: https://www.instagram.com/reel/DYPgTzuSilc/ · 32.97s · 1080x1920 · 6478 likes / 3383 comments · upload 2026-05-12
> Ingest: `~/.business/growth/ingest/2026-06-14-DYPgTzuSilc/` · покадровый разбор @8fps (264 кадра, 4 сегмент-грида) + 7 full-res кадров.
> 🏆 СТАТУС: **ЭТАЛОН-ПЛАНКА МОНТАЖА №2** для нашего основного формата (split AI-product-demo · talking-head + UI-демо инструмента). Назначен автором («монтаж охренеть какой жёсткий, эталон уровня, вдохновляемся»).

## HOOK (first 2s, beat order)
- Pattern: demo-first + intrigue («Someone on GitHub just built this»)
- Beat order: t0.0 full-screen 3D-сцена, агенты СПАВНЯТСЯ сверху градом цветных партиклов-фигурок (вау-анимация, без головы) → t1.47 первый кат на говорящую голову
- Verbal hook: "Imagine giving your AI agents an actual office to work in."
- Visual hook: полноэкранная анимация спавна (партиклы падают, собираются в 3D-офис) — движение в кадре с 0.0с, НЕ статичная голова

## A. FONTS (titles + subtitles)
- Subtitle font: белый **bold humanist sans** (≈ SF Pro / Helvetica Neue Bold / Montserrat SemiBold) | nearest free: **Inter Bold / Montserrat 700** | confidence: med
- UI-тексты продукта (НЕ субтитры автора, но в кадре крупно): "Chat" заголовок — чёрный heavy sans; чат-сообщения — regular sans; отчёты — bold-заголовки + regular тело; role-капсулы — uppercase bold mono-ish. РАЗНООБРАЗИЕ шрифтов = в UI продукта, не в субтитрах.
- Stroke/treatment: серая полупрозрачная **rounded box-plate подложка** (≈rgba(90,90,90,0.6), радиус ~14px) + чёрная мягкая тень по буквам. НЕ outline-обводка.

## B. SUBTITLES (placement + treatment)
- Words on screen at once: **2-3 слова** (фраза-чанк: "choose setups", "Each agent", "built", "by Gemini")
- Position band: центр, **на стыке сплита** (≈y 700-1000 из 1920, в safe-zone) — плашка-подложка маскирует горизонтальный шов между верхом и низом. y: да, в safe-zone.
- Color scheme: **mono white** на серой плашке (без цветного акцент-слова — отличие от нашего золотого keyword)
- Timing: **by-phrase** (фраза появляется целиком, синхрон с речью; не word-by-word karaoke)
- CAPS? **sentence-case** (НЕ all-caps — мягче нашего Hormozi all-caps; это сознательный отличительный стиль автора)
- Always-on or selective? **selective by beat** — субтитры не 24/7, появляются на ключевых фразах

## C. OVERLAP / CLUTTER
- Element collisions: none. Чисто.
- Tiny/illegible: none — UI-вставки всегда крупные, читаемые.
- On-face text? never — субтитр-плашка на стыке сплита, выше лица.

## D. EFFECTS / TRANSITIONS / DYNAMICS
- Cut/change pace: машинный scene-detect = **7 макро-сцен** (0.25/с, каждые ~4с: смена палитры/локации). НО фактический монтажный темп ВЫШЕ — смена вставки/ракурса/раскладки **≈каждую 1с** внутри макро-сцен (покадрово @8fps): camera-pan по 3D-сцене, смена UI-панели, новый ракурс агентов, появление маскота. Это «жёсткий монтаж» = плотность микро-смен, не только крупных катов.
- Transition vocabulary: hard-cut (доминанта) + camera pan/orbit по 3D-сцене + push на UI-карточки. Нет whip-pan/glitch.
- Motion primitives: партикл-спавн (хук), 3D-camera work (pan/follow/orbit), агент-walk-анимация, UI-message-appear, маскот-эмоции (моргание/жесты), cursor-trace, число-агентов-растёт.
- Static stretches >1.5s? none — даже на голове фон/ракурс или верхняя вставка меняются.

## E. CONTENT / HONESTY
- Claim type: demo (реальный GitHub-проект, 3Js + Gemini). Tool names: GitHub, 3Js, Gemini, gemini-3-flash, veo-3.1.
- UI shown clean? **y** — реальный работающий продукт, залогинен, чистые состояния, реальные данные ("FakeClaw Inc.", "Chief People Officer", отчёты). НЕ моки.
- Clickbait? none. Демо соответствует обещанию.

## F. STRUCTURE / LAYOUT (time-map)
- Layout rhythm (alternation): **0-1.5 full-screen 3D-хук · 1.5-8 чередование full-head (multi-location) ↔ full-demo 3D · 8-12.8 full-demo 3D (агенты-роли, camera work) · 12.8-22 split-горизонт (верх UI-чаты / низ голова) ↔ full-UI · 22-26.7 вау-маскоты крупно ↔ split · 26.7-30 full-UI отчёт-результат · 30-33 full-head + CTA-мокап**
- Dominant layout: **чередование 4 раскладок** (full-demo / full-head / split-horizontal / full-UI) — НЕ доминирует одна. Это ключ «жёсткого монтажа».
- Layout switches count: ~25-30 (микро) / 7 (макро). → alternating, высокая плотность.
- 🔑 СПЛИТ-ГЕОМЕТРИЯ: чистый **горизонтальный сплит с ДИНАМИЧНОЙ границей 48-58%** (t13.6≈58% UI-тяжёлый бит, t24.5≈48%, t26.6≈52%). Верх = UI/демо, низ = голова крупно. **БЕЗ u2net-overlap** — голова всегда строго НИЖЕ шва, лоб НЕ заходит за плашку (отличие от нашего K3-overlap DUqeScpDAHW — здесь проще и чище). Шов маскируется субтитр-плашкой.

## B-ROLL
- What: (1) real 3D-демо продукта (3Js-сцена, агенты), (2) UI-панели функционала (Chat / Project Info / generation settings), (3) UI-результата (структурированные отчёты с bold-заголовками Project Leadership / Financial Impact / Team Collaboration), (4) вау-маскоты (анимированные 3D-персонажи крупно — синий/красный/зелёный/жёлтый, эмоции).
- Technique: real screen-record продукта + camera work внутри 3D-сцены. Всё нативно из продукта, ноль рисованных моков.

## SPEAKER
- Digital-twin or live? **live talking-head** (реальный человек Dr. Cintas)
- Framing: чередует **full-frame** (голова крупно на весь низ/экран) и **split-bottom** (голова в нижней половине сплита)
- 🔑 MULTI-LOCATION: фоны головы РЕАЛЬНО разные по битам (охра-комната с картиной, office-жалюзи деревянные, тёмная стена) — несколько записей/локаций. Прямой аналог нашего avatar-multi-location, но у живого спикера.

## CTA
- Финал t30-33: мокап интерфейса «office» — круглый аватар-фото автора (как наш приём реального фото в кружке) + поле ввода + кнопка-стрелка ↑. Кодовое слово: "come in office and I'll send you the link".

## ЧТО РЕПЛИЦИРУЕМ → к себе (планка для replicate-viral)
1. **Плотность микро-монтажа** ≈1 смена/с (вставка/ракурс/раскладка), не только крупные каты — наш Г9 поднять до этого уровня.
2. **Чередование 4 раскладок** без доминанты одной (full-demo / full-head / split / full-UI) — наш Г2.
3. **Сплит с динамичной границей 48-58%** — пропорция по биту (у нас уже делегировано оркестратору; добавить как опцию «чистый сплит без overlap», проще K3).
4. **Captions: серая rounded box-plate + sentence-case by-phrase** — добавить как АЛЬТЕРНАТИВНЫЙ caption-стиль к нашему золотому all-caps Hormozi (разнообразие — автор отметил «шрифты разные охеренные»).
5. **Multi-location головы** — у нас есть (avatar-сегменты), держать плотность смен фона.
6. **Real-product B-roll с camera work** внутри демо — наш Г5 (реальный футаж), усилить camera-work внутри 3D/UI.
7. **Вау-маскоты/hero-вставки крупно** между UI-битами — наш Ф4.5 Higgsfield вау-вставки.
8. **Хук = full-screen движение 0-1.5с без головы** (партикл-спавн / демо-вспышка) — наш хук-канон.
