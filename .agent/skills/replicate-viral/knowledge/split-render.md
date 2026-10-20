# Сборка сплита — HyperFrames (финал) + ffmpeg (быстрый POC)

> Стек ЕДИНЫЙ: HyperFrames (HTML + GSAP + CSS → `npx hyperframes render` → MP4). Remotion deprecated по решению автора (рассинхрон стека = корень бага «1/10 тулкита», см. ERROR-REGISTER #1). Ничего из Remotion в финал НЕ тянем.

Формат подтверждён эмпирикой по решению автора (7 топ-конкурентов: nick_saraev, alassafi, sanji.chien, thechriscordero, rpn, askgpts, neyro_max). ВСЕ Reels = 1080x1920 (9:16). Доминирует СПЛИТ ~50/50: верх — скриншот экрана/интерфейса/B-roll, низ — говорящая голова крупно. 16:9 в Reels нет (то, что «горизонтально» — верхняя панель сплита со скриншотом).

## Геометрия кропа

Контейнер 1080x1920. Сплит 50/50: верх 1080x960, низ 1080x960.
Portrait-аватар 1080x1920 → нижняя панель 1080x960: ширина 1080 СОВПАДАЕТ (бока не режем), берём верхние 960px по высоте (лицо+плечи), низ (тело) отрезаем. В HyperFrames кроп = контейнер `height:960px; overflow:hidden` поверх `<video>` (CSS, не ffmpeg-фильтр). Вертикальный сдвиг лица — `object-position` / `translateY` на видео. (ffmpeg-эквивалент для POC: `crop=1080:960:0:0`.)

## ffmpeg — быстрый POC (отлажено по решению автора)

ТОЛЬКО для быстрой проверки кропа/раскладки, НЕ финал.

```bash
ffmpeg -y -i input.mp4 -f lavfi -i "testsrc2=s=1080x960:r=25:d=5.1" \
 -filter_complex "[0:v]crop=1080:960:0:0[bot];[1:v]format=yuv420p[top];[top][bot]vstack=inputs=2[v]" \
 -map "[v]" -map "0:a?" -c:v libx264 -pix_fmt yuv420p -c:a aac -t 5 out.mp4
```
Верх (`testsrc2`) заменить на реальный скриншот: `-loop 1 -i screenshot.png` + scale=1080:960. Кавычки вокруг `0:a?` обязательны (zsh глобит `?`). drawtext недоступен (нет freetype) — субтитры делаются в HyperFrames (captions-модуль), не в ffmpeg.

## HyperFrames-native — ФИНАЛ ПО BUILD_ORDER (обязательно, не опция)

Качество нашего уровня = HyperFrames-native по `build_order[]` из motion-storyboard (Фаза 3 скилла): motion-блоки из библиотеки (`~/.business/growth/assets/motion-blocks/_INDEX.md`) + Material-токены + transitions + style variant. ffmpeg-сплит выше — ТОЛЬКО быстрый POC/fallback для проверки кропа, НЕ финальный рендер. Финал всегда через `npx hyperframes render` по собранному `index.html` (`scripts/scene-assemble.py` из блоков библиотеки, хендролл запрещён валидатором).

## HyperFrames — проект (анимации + субтитры)

Проект-эталон: `~/<твоя рабочая папка ролика>/fullreel/index.html` (блок `K5-continuous-anchor-reel`, ОДНА плоская композиция на весь ролик). Композиция `data-width="1080" data-height="1920"`, низ = `<video>` аватара в контейнере `height:960px; overflow:hidden` (кроп), верх = панель-слот под скриншот/футаж. Длительность таймлайна — по аудио/футажу (ffprobe источника), таймсинк через `data-*`-атрибуты + GSAP-таймлайн.

Шрифты В РЕНДЕР — через `@font-face` + локальный `.ttf/.woff2` (КАНОН эталонов: `anton.ttf` рядом с index.html в G0DM0D3, base64-инлайн @font-face в karkas). Anton/Oswald/Impact компилятор HyperFrames НЕ авто-встраивает — голый `font-family` без @font-face = системный фолбэк (lint `font_family_without_font_face`, проверено рендером по решению автора; Inter авто-резолвится). НЕ `@remotion/google-fonts`.

Запуск: `npx hyperframes render --fps 30 --quality high --output renders/final.mp4`. Перед рендером — `npx hyperframes lint` + `inspect` (ловит overflow/слёт таймлайна). Байт-идентичный рендер — `--docker`.

## Hormozi-субтитры (из ресёрча по решению автора)

Anton (free Google font) или Montserrat Bold, ВСЕ КАПС, 3-6 слов на экран, keyword выделен жёлтым #f7c204, word-by-word pop (всплывают по слову, +15% вовлечения educational/business), позиция центр-верх (не нижние 25% UI, не верхние 15%), белый текст + толстая чёрная обводка, покрытие 12-20% высоты, мин 48-60px. Тайминг ~3-4 слова/сек по транскрипту whisper. В HyperFrames — через captions-модуль (whisper-json с word-level таймкодами → стилизованные клипы).

## Экспорт под Instagram

1080x1920, H.264, битрейт 8-10 Mbps, fps под источник (25/30). НЕ 4K — IG режет плейбек до 1080p, 4K только тяжелее и пережимается агрессивнее. Рычаг качества — битрейт, не разрешение.