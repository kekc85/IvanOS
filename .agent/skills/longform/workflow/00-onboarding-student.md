# 00 - Onboarding ученика

> Срабатывает при первом запуске скилла `longform` если `config.md` отсутствует или неполный. Создаёт config.md через 11 вопросов и кладёт стартовые intake-файлы.

## Когда срабатывает

- `config.md` отсутствует
- В `config.md` есть `<active-launch>` / `null` / placeholder значения в обязательных полях
- Любое из обязательных полей `subject.name` / `platforms.canonical.url` / `paths.avatar` пустое

## 11 вопросов

Задаются последовательно. После каждого ответа - мгновенно записывается в config черновик. После 11-го вопроса показывается preview и подтверждение.

| # | Вопрос | Поле в config | Default / hint |
|---|---|---|---|
| 1 | Как тебя зовут (имя автора)? | `subject.name` | - |
| 2 | Основной язык контента - RU / EN / both? | `subject.language` + `subject.market` + `subject.bilingual_mode` | RU = `ru_canonical` |
| 3 | О чём в основном пишешь (продукт / экспертиза / ниша)? | `subject.product_focus` | - |
| 4 | Где **канонически** публикуется длинный контент: свой блог / Substack / Beehiiv / Kit / LinkedIn-only? | `platforms.canonical.type` + `platforms.canonical.url` | personal_blog |
| 5 | Newsletter platform (если есть): Kit / Beehiiv / Substack / MailerLite / нет | `platforms.newsletter.provider` + `.url` | none |
| 6 | LinkedIn URL для article distribution (если ведёшь) | `platforms.linkedin.profile_url` | null |
| 7 | Cross-post targets (Substack / Medium / другое) | `platforms.cross_post_targets[]` | пустой массив |
| 8 | Где у тебя лежит аватар целевого читателя? | `paths.avatar` | `.business/audience/avatar.md` |
| 9 | Где Brand DNA / распаковка бренда (голос автора)? | `paths.brand_dna` | `.business/Распаковка бренда.md` |
| 10 | Сколько в неделю планируешь выпускать longform (1 / 2 / 3+)? | `subject.longform_cadence` | 1-2 |
| 11 | Запретные термины / обязательные замены под нишу (можно пропустить) | `lexicon_required` + `lexicon_banned_longform` | inherit from post |

## Что делает онбординг

После 11 ответов:

1. **Записывает `config.md`** с заполненными полями. Поля которые не заданы - оставляет дефолтами.
2. **Создаёт `examples/gold-standard-<name>-longform.md`** с шаблоном для заполнения 3-5 эталонными длинными текстами автора. Без эталона voice fidelity будет слабым - это явно говорим пользователю в финальном сообщении.
3. **Проверяет существование `paths.avatar` / `paths.brand_dna`**. Если файлов нет - выводит warning со списком файлов которые надо создать ДО первого `/longform`.
4. **Возвращает quick-start подсказку**:

```
Готово. Чтобы запустить первый longform:
- /longform про <тема>             - Spark B1 (расширение темы)
- /longform                         - Plan (из Карты смыслов / контент-плана)
- /longform <надиктовка>            - Transcript (>500 знаков)

Перед первым запуском заполни:
- examples/gold-standard-<name>-longform.md (3-5 эталонных текстов)
- .business/audience/avatar.md
- .business/Распаковка бренда.md (или укажи другой путь)
```

## Финальный preview

Перед записью показывается:

```
Готовлю config для:
  Автор: <name>
  Язык: <language>
  Canonical: <type> @ <url>
  Newsletter: <provider> @ <url>
  LinkedIn: <profile_url>
  Cadence: <longform_cadence>

Подтверждаешь? (y/n/edit)
```

`edit` → возвращает к редактированию любого поля по номеру.

## Memory cross-refs

- `[[post]]` - параллельный onboarding pattern (9 вопросов для TG)
- - не задавать лишних выборов когда есть defaults