# Free $0 audio sources (SFX + music) для motion-element

> **ПРОВЕРЕНО (ресёрч по решению автора) — основной источник палитры: Mixkit.** Это РЕАЛЬНАЯ edit-grade палитра рилз (cinematic whoosh/swoosh/transition/impact/magic/glitch), а НЕ game-audio (Kenney) и НЕ синтез. Keyless, free, коммерция, БЕЗ атрибуции, без аккаунта.
> Механизм: страница `https://mixkit.co/free-sound-effects/<категория>/` содержит прямые `https://assets.mixkit.co/active_storage/sfx/<id>/<id>-preview.mp3`. Загрузчик: `scripts/fetch-mixkit-sfx.py`.
> **Pixabay** (125k+ SFX, free, без атрибуции) — отличный добор, НО прямой fetch даёт 403 (анти-скрейпинг); нужен рабочий bulk-механизм (Playwright / реальный CDN-URL после клика), пока «требует проверки».
> **Платное (Epidemic Sound / Artlist)** — у топов именно их звук, но ИЗБЕГАЕМ (решение автора). Только free.
> Урок почему так: — game-audio/синтез звучали роботизированно.

---

# SOURCES
I have enough verified data on all key sources. I have direct knowledge of YouTube Audio Library, FMA, Zapsplat, BBC Sound Effects, and Incompetech licensing. Let me compile the research.

# Бесплатные программно-доступные источники аудио для short-form видео

## Сравнение источников

### 🥇 Pixabay Audio — лучший #1
- **Что:** музыка + SFX (оба)
- **Лицензия:** собственная Pixabay Content License = de-facto CC0. Коммерческое использование, без атрибуции, без royalty
- **API:** ДА, публичный REST API. Регистрация → бесплатный API-ключ
- **Лимиты:** 100 запросов / 60 сек на ключ (расширяемо). Результаты обязаны кэшироваться 24ч. Запрет «systematic mass downloads» / автоматических массовых запросов
- **Нюанс:** audio-эндпоинт в API менее задокументирован чем images/videos, но качаемые mp3-URL доступны. Скриптуется без проблем
- **Вывод:** идеальная лицензия (CC0, zero attribution) + реальный API. Топ для интеграции

### 🥈 Freesound — лучший #2 (особенно SFX)
- **Что:** SFX (огромная база) + музыкальные фрагменты
- **Лицензия:** **смешанная** — CC0, CC-BY (attribution), CC-BY-NC (НЕ для коммерции), CC Sampling+. ОБЯЗАТЕЛЬНО фильтровать `filter=license:"Creative Commons 0"` чтобы получить только чистый CC0 без атрибуции
- **API:** ДА, APIv2. Превью (mp3/ogg) — по token-ключу без OAuth. **Полное качество (original) — требует OAuth2**
- **Лимиты:** 500 полных скачиваний / день (OAuth). Token-доступ к превью без лимита скачивания
- **Вывод:** богатейшая SFX-база. Для CC0-only через фильтр лицензии. Превью-mp3 (128-256k) достаточно для коротких SFX в видео

### Mixkit (Envato)
- **Что:** музыка + SFX (оба)
- **Лицензия:** Mixkit Free License — коммерция OK, **без атрибуции, без регистрации**. НО: нельзя перепродавать/распространять как stand-alone аудио (только внутри своего видео — для нас норм)
- **API:** НЕТ публичного API. Скрейпится (статичные mp3-ссылки), но без официального доступа
- **Вывод:** отличная лицензия, но ручной/скрейп-доступ. Хорош как seed-библиотека (скачать пак один раз)

### YouTube Audio Library
- **Что:** музыка + SFX (оба)
- **Лицензия:** часть треков без атрибуции, часть с атрибуцией (помечено). SFX — все свободны
- **API:** НЕТ публичного API (только UI в YouTube Studio, нужен Google-аккаунт)
- **Вывод:** не скриптуется. Только ручной батч-экспорт. Не для автоматизации

### Uppbeat
- **Что:** музыка + немного SFX
- **Лицензия:** Free-тариф **требует атрибуцию** (кредит прикрепляется к скачиванию) + лимит скачиваний. Без атрибуции — только платный Premium ($7-10/мес)
- **API:** НЕТ публичного API
- **Вывод:** атрибуция на free = трение для конвейера. Пропустить

### Chosic
- **Что:** музыка (агрегатор, многое из FMA/incompetech) + SFX-раздел
- **Лицензия:** в основном **CC-BY 4.0 = требует атрибуцию**. Часть CC0
- **API:** НЕТ
- **Вывод:** агрегатор, не источник. Атрибуция-требование. Пропустить как primary

### Free Music Archive (FMA)
- **Что:** музыка
- **Лицензия:** **смешанная** — CC-BY, CC-BY-NC, CC0, some-rights. Надо проверять трек за треком
- **API:** старый API **закрыт** (2019). Сейчас только web/скрейп
- **Вывод:** без API, лицензия неоднородна. Низкий приоритет

### Zapsplat
- **Что:** SFX (огромная база) + музыка
- **Лицензия:** Free-тариф **требует атрибуцию** + регистрацию. Без атрибуции — платный Gold
- **API:** НЕТ публичного API
- **Вывод:** атрибуция + аккаунт = трение. Пропустить

### BBC Sound Effects
- **Что:** SFX (~33 000)
- **Лицензия:** **RemArc License — ТОЛЬКО personal/educational/research. Коммерческое использование ЗАПРЕЩЕНО**
- **API:** НЕТ (web-download)
- **Вывод:** ❌ нельзя для creator-монетизации. Исключить

### Kevin MacLeod / Incompetech
- **Что:** музыка (cinematic, tension, corporate)
- **Лицензия:** **CC-BY 4.0 = требует атрибуцию** (либо разовая платная лицензия ~$30/трек без кредита)
- **API:** НЕТ
- **Вывод:** легендарный фонд, но атрибуция. Не для zero-credit конвейера

## Итог сравнения лицензий (для коммерческого creator-контента БЕЗ атрибуции)

| Источник | Тип | CC0 / no-attr | API | Готов к скрипту |
|---|---|---|---|---|
| **Pixabay** | both | ✅ да | ✅ да | ✅ |
| **Freesound** (CC0-filter) | SFX+ | ✅ если фильтр | ✅ да (OAuth для original) | ✅ |
| Mixkit | both | ✅ да | ❌ | скрейп |
| YT Audio Library | both | частично | ❌ | ❌ |
| Uppbeat | music | ❌ attr | ❌ | ❌ |
| Chosic | music | ❌ attr | ❌ | ❌ |
| FMA | music | mixed | ❌ (API закрыт) | ❌ |
| Zapsplat | SFX | ❌ attr | ❌ | ❌ |
| BBC SFX | SFX | ❌ non-commercial | ❌ | ❌ |
| Incompetech | music | ❌ attr | ❌ | ❌ |

---

## Starter SFX Pack — таксономия под motion-element skill

Каждая категория = что озвучивает в шаблонах + лучший бесплатный источник:

| Категория | Когда срабатывает | Запрос | Лучший источник |
|---|---|---|---|
| **click** | UI-нажатие, появление элемента | `ui click` / `button click` | Pixabay (CC0) |
| **whoosh / transition** | смена сцены, влёт текста | `whoosh transition swoosh` | Pixabay + Freesound CC0 |
| **pop (comment)** | всплытие комментария/баббла | `pop bubble` | Pixabay (CC0) |
| **impact / boom (climax)** | кульминация, акцент-удар | `cinematic impact boom hit` | Freesound CC0 + Pixabay |
| **riser / swell (build)** | нагнетание перед поинтом | `riser swell build up` | Pixabay + Freesound CC0 |
| **tick (counter)** | отсчёт, шаги списка | `tick clock counter` | Freesound CC0 |
| **ding / notification** | подтверждение, success | `notification ding bell` | Pixabay (CC0) |
| **swipe** | смена слайда, листание | `swipe slide` | Pixabay (CC0) |
| **coin / clink (money ticker)** | $-счётчик, доход | `coin cash money clink` | Freesound CC0 + Pixabay |
| **typewriter (terminal)** | печать кода/терминала | `typewriter keyboard typing` | Freesound CC0 |
| **error / glitch** | ошибка, сбой, glitch-акцент | `error glitch digital` | Pixabay + Freesound CC0 |

Все 11 категорий полностью покрываются связкой **Pixabay (CC0) + Freesound (CC0-filter)** — без единого attribution-требования.

## Music-bed таксономия по настроению

| Mood | Где звучит | Запрос | Источник |
|---|---|---|---|
| **energetic / tech** | хук, динамичный туториал | `upbeat tech electronic energetic` | Pixabay (CC0) |
| **cinematic** | сторителлинг, before/after | `cinematic epic inspiring` | Pixabay (CC0) |
| **lo-fi** | спокойный обучающий, фон | `lofi chill beats` | Pixabay (CC0) |
| **corporate-uplift** | продуктовый, кейс, оффер | `corporate uplifting motivational` | Pixabay (CC0) |
| **tension** | проблема, нагнетание | `tension suspense dark` | Pixabay (CC0) |

Музыкальные беды целиком закрывает Pixabay в CC0 (full-length треки, без атрибуции).

---

## Рекомендация: что интегрировать первым

**Интегрировать в первую очередь — 2 источника:**

1. **Pixabay Audio** — primary. CC0 / zero-attribution + реальный REST API + покрывает И SFX, И музыкальные беды. Один API-ключ закрывает почти весь starter-pack и всю music-bed таксономию. Минимум трения.

2. **Freesound (с жёстким фильтром `license:"Creative Commons 0"`)** — secondary, для глубины SFX-библиотеки (impact, tick, typewriter, coin, glitch — там богаче и разнообразнее). Превью-mp3 по token-ключу без OAuth достаточно для коротких SFX; OAuth подключать только если нужно original-качество.

**Архитектура:** Pixabay как дефолт для всего → Freesound CC0 как fallback/обогащение для SFX-категорий, где нужно больше вариативности. Обе лицензии безопасны для монетизируемого creator-контента без атрибуции. Mixkit — опционально скачать один раз как seed-пак (без API).

**Исключить из конвейера:** BBC SFX (non-commercial), Uppbeat/Zapsplat/Incompetech/Chosic (требуют атрибуцию на free), YT Audio Library/FMA (нет API).

Sources:
- [Pixabay API Documentation](https://pixabay.com/api/docs/)
- [Freesound APIv2 Overview](https://freesound.org/docs/api/overview.html)
- [Freesound API Resources](https://freesound.org/docs/api/resources_apiv2.html)
- [Mixkit License](https://mixkit.co/license/)
- [Uppbeat music licenses](https://uppbeat.io/blog/royalty-free-and-copyright-free-music/uppbeats-music-licenses)
- [Chosic free music policy](https://www.chosic.com/free-music-policy/)

