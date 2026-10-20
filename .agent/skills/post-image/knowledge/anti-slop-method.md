# Анти-AI-слоп метод (движок post-image, общий профиль)

> Общая методология фотореализма. Проект-специфику (палитра/типаж/тема→момент) перекрывает `image-dna.md` проекта через `--project`.

## Жанр
Редакционная документальная фотография (editorial / photojournalism). НЕ иллюстрация, НЕ 3D-рендер, НЕ сток.

## Стиль-ДНК (дефолт)
- Герой: реальный человек, живая кожа с порами/текстурой, естественная мимика, без глянца и макияж-маски.
- Свет: мягкий естественный (окно, раннее утро, пасмурно), направленный, мягкие тени. Без студийной вспышки.
- Камера: «shot on Kodak Portra 400, 35mm film», 50mm f/1.8, малая глубина резкости, лёгкое зерно, правдивый цвет.
- Палитра: приглушённая, тёплые нейтрали (дефолт; проект перекрывает).
- Композиция: документальная, чуть несимметричная, есть воздух (negative space), реальный интерьер, не студия.

## Анти-слоп негатив (вставлять в КАЖДЫЙ промпт)
no plastic or waxy skin, no over-smoothing, no hyper-saturation, no symmetrical flawless model face, no fake stock smile, no CGI or 3D render look, no extra fingers or distorted hands, no text or letters or watermark, no surreal elements, no clutter, no HDR glow, no beauty-retouch.

## Реализм-бустеры (вставлять)
natural skin texture and pores, slight asymmetry, a few stray hairs, candid unposed expression, believable everyday interior, soft film grain, realistic imperfect lighting, documentary photo, true-to-life color.

## Формат
Дефолт 4:5 (вертикаль, сильна в TG-ленте). Без текста на картинке.

## ULTRA промпт-шаблон (self-contained, 120-200 слов)
```
Editorial documentary photograph. [ГЕРОЙ: realistic person, natural skin texture] in [МОМЕНТ по теме] inside [РЕАЛЬНЫЙ ИНТЕРЬЕР]. [СВЕТ: soft natural window light, gentle directional shadows]. Mood: [настроение], quiet, honest, not staged. Shot on Kodak Portra 400, 35mm film, 50mm f/1.8, shallow depth of field, fine grain, true-to-life muted palette [палитра проекта]. Composition candid, slightly off-center, negative space [где]. [РЕАЛИЗМ-БУСТЕРЫ]. Aspect ratio [формат].
Negative: [АНТИ-СЛОП НЕГАТИВ].
```

## Принципы момента
- Момент — честная атмосфера по теме, НЕ буквальная иллюстрация заголовка.
- Эмоция героя — узнавание/пауза, не отчаяние и не пафос.
- Один герой ИЛИ одна предметная сцена. Без коллажей и текста.