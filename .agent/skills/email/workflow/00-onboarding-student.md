# workflow/00-onboarding-student.md

> First-run для ученика курса вайбмаркетинга. Создаёт `config.md` через 9 вопросов. После онбординга ученик может запускать `/email`.

## Когда срабатывает

- `config.md` отсутствует
- Любое из обязательных полей не заполнено: `subject.name`, `paths.avatar`, `esp.default`

## 9 вопросов

Задавать по одному. Если VS Code - через AskUserQuestion. Если CLI/mobile - plain text список с цифрами.

### Q1 - Имя автора

```
Как тебя зовут (имя бренда канала)?
Пример: "автор"
```

→ config.subject.name

### Q2 - Язык

```
На каком языке будешь рассылать?
1) RU only
2) EN only
3) Both (skill будет генерить две версии)
```

→ config.subject.language

### Q3 - ESP платформа

```
Через какой ESP отправляешь письма?
1) Kit (бывший ConvertKit) - plain-text bias, broadcasts + sequences
2) Beehiiv - HTML blocks, premium tier, paid ads network
3) Другой ESP (выдадим в plain-text format universal)
```

→ config.esp.default

### Q4 - Фокус продукта

```
Опиши в одной фразе твой продукт / нишу.
Пример: "вайбкодинг + вайбмаркетинг для соло-экспертов любых ниш"
```

→ config.subject.product_focus

### Q5 - Позиция в воронке

```
Что email делает в твоей воронке? Куда ведёт?
Пример: "newsletter → клуб Skool <твоя подписка> → cash events <твой ценовой диапазон> каждые 6-8 нед"
```

→ config.subject.funnel_position

### Q6 - Архетипы голоса (если знаешь)

```
Какие архетипы голоса (Marc & Pearson 12) тебе подходят?
По умолчанию: Magician + Sage + Outlaw.
Banned (тебе НЕ подходят): Caregiver + Lover + Innocent.
Можешь оставить дефолт или назвать свои.
```

→ config.voice.archetypes_allowed / archetypes_banned

Если ученик не знает - оставить дефолт. На следующем шаге курса (Brand DNA через `~/.claude/skills/skill-craft` audit его проекта) - пересмотрит.

### Q7 - Пути к контексту проекта

```
Где у тебя лежит .business/ дерево?
1) Стандартное: .business/ (рекомендую)
2) Кастомное: <твой путь>
```

→ config.paths.* (все пути относительно root)

### Q8 - Активный запуск (опционально)

```
Идёт ли сейчас запуск? Если да - имя папки в .business/запуски/
Пример: "vibemarketing-2026"
Если нет - пропусти, Mode A для launch sequence отключим.
```

→ config.paths.active_launch

### Q9 - Voice-bridge на post

```
У тебя клонирован skill post? (он содержит voice/lexicon/архетипы автора)
1) Да, клонирован → используем общий voice через bridge
2) Нет → email скилл будет использовать только свои references
```

→ config.paths.tg_content_voice / living_language / archetypes (или null)

## Post-onboarding

1. Write `config.md` со всеми ответами
2. Write `config-lexicon.md` (дефолтный шаблон, ученик дописывает свою banned-лексику)
3. Создать пустые `examples/gold-standard-<name>-email-ru.md` и `examples/gold-standard-<name>-email-en.md` (если language=both) с инструкцией «вставь 5-10 своих лучших писем после первого месяца использования»
4. Если `config.paths.active_launch` указан, проверить существование `.business/запуски/<name>/launch-sequence.md` - если нет, создать пустой скелет с инструкцией
5. Сообщить ученику: «Готово. Запускай `/email` чтобы написать первое письмо.»

## Anti-patterns

- НЕ задавать >9 вопросов на онбординге (cognitive overload)
- НЕ требовать у ученика ответы на все 9 за раз - допустимо «не знаю, оставь дефолт» на Q6 / Q8 / Q9
- НЕ генерировать первое письмо в рамках onboarding - onboarding только настраивает config
- НЕ выдумывать пути за ученика - если Q7 ответ неоднозначный, переспросить с точным путём