# Bot anti-patterns

> Каталог анти-паттернов bot push. Каждый - auto-fail или warning в `04-review.md`. Список растёт через self-learning (каждая правка автора → новая запись).

## Anti-patterns текста

### Структурные

| Anti-pattern | Severity | Почему |
|---|---|---|
| Длина >300 знаков | hard fail | Notification обрезается, кнопки уходят с экрана |
| Длина <80 знаков | warning | Слишком тонко, возможна потеря смысла |
| Hook = generic «Привет» / «Здравствуй» / «Доброе утро» | hard fail | Notification preview не несёт смысла |
| Hook начинается с эмоджи | warning | Старые клиенты могут резать |
| Списки / буллеты (`- `, `* `, `1. `) | hard fail | Push не формат списка, читается как стена |
| >2 предложений в body | warning | Push требует brevity |
| Стена без переноса в 200+ знаков | warning | Глаз соскальзывает |

### Лексические

| Anti-pattern | Severity | Почему |
|---|---|---|
| Em-dash «-» внутри строк | hard fail | Memory rule `feedback_no_em_dash` |
| «Instagram» | auto-correct | → «Нельзяграм» (memory `user_lexicon`) |
| «программист» / «без опыта в коде» | hard fail | Не возражение целевой аудитории (memory `feedback_no_code_objection_ever`, `feedback_product_positioning_no_programmer`) |
| Жаргон: «артефакт», «digital-twin», «КЭВ», «связки», «Grand Slam Offer» | hard fail | Memory `feedback_no_tech_jargon_no_anglicisms` |
| Filler: «просто», «довольно», «достаточно», «по сути», «буквально», «сразу же», «вот», «короче» | hard fail | Слабит push |
| «Click here», «Тык», «Сюда» | hard fail | Generic CTA |
| Любые англицизмы в RU push | warning | Адаптировать («post» → «пост», «click» → «клик» только если term не имеет RU-аналога) |
| Многоточие «...» или «…» | hard fail | Выглядит слабо, лучше точка |

### Эмоциональные

| Anti-pattern | Severity | Почему |
|---|---|---|
| Восклицательных «!» >0 | hard fail | Notification noise, выглядит как spam |
| Вопросительных «?» >1 | hard fail | Рассеивает фокус |
| ВСЕ КАПС | hard fail | Read как кричащая реклама |
| «Срочно!!!», «Внимание!!!», «Только сегодня!!!» | hard fail | Spam-сигнатура |
| Эмоджи в каждом предложении | warning | Clutter |
| >2 эмоджи всего | warning | Decoration > content |

### Содержательные

| Anti-pattern | Severity | Почему |
|---|---|---|
| Метафоры в первых 50 знаках | hard fail | В коротком формате читаются как невнятица |
| «Жми кнопку» / «нажми сюда» / «тапни» | hard fail | Дублирование affordance |
| Две разные цели в одном push | hard fail | Single action rule |
| Цена в личке («напиши в личку») | hard fail | Memory `feedback_no_em_dash` + DM-only ценообразование |
| Негативные статистики («20% доходят», «80% бросают») | hard fail | Memory `feedback_no_negative_stats_in_public_offer` |
| Травел-флекс («Бали», «40 стран», «Дубай») | hard fail | Memory `feedback_no_travel_flex` (через ivan-voice) |
| Статус-флекс («архитектор ИИ-систем», «эксперт уровня senior») | hard fail | Memory ivan-voice |
| Атака конкурентов по имени | hard fail | Memory `feedback_no_attacking_competitors_by_name` |
| Фактические выдумки (числа, даты, имена) | hard fail | Memory `feedback_no_inventing_facts` |
| «20% доходят», «80% бросают» (любая негативная статистика про учеников) | hard fail | Memory `feedback_no_student_failure_quotes` |

### Forma адресации

| Anti-pattern | Severity | Почему |
|---|---|---|
| Микс «ты» и «вы» в одном push | hard fail | Один config.voice.address для всех |
| «вы все» / «дорогие подписчики» | hard fail | Группе адресация в персональном канале - диссонанс |
| Безличные обороты («стоит обратить внимание», «следует учесть») | warning | Канцеляризм |

## Anti-patterns кнопок

### Microcopy

| Anti-pattern | Severity | Почему |
|---|---|---|
| Текст кнопки >24 знака | warning | Truncation на mobile |
| Текст кнопки <8 знаков | warning | Недостаточно контекста |
| Generic: «Узнать», «Подробнее», «Подробности» | hard fail | Не показывает что произойдёт |
| «OK», «Да», «Нет» без объекта | hard fail | Без контекста action |
| «Ссылка», «Перейти» без объекта | hard fail | Куда? |
| Одиночные эмоджи без слова | hard fail | Не CTA |
| ВСЕ КАПС в тексте кнопки | hard fail | Кричащая реклама |

### Structural

| Anti-pattern | Severity | Почему |
|---|---|---|
| >3 кнопок в одном push | hard fail | Выбор парализован |
| 0 кнопок | hard fail | Без CTA - это пост, не push |
| Кнопка не соответствует ожиданию из текста | hard fail | Frustration → отписка |
| 2 одинаковые кнопки рядом | hard fail | Дублирование |
| Очень разные кнопки в одном push (например, «Купить» + «Удалиться») | warning | Two-action - нарушение single action rule |

## Anti-patterns timing & frequency

| Anti-pattern | Severity | Почему |
|---|---|---|
| >2 push в день на одного подписчика | warning | Push fatigue |
| Push в 0:00-7:00 (без явной необходимости) | warning | Notification ночью раздражает |
| 3+ reminder подряд о том же событии | hard fail | Spam |
| Один и тот же hook framework 3 раза подряд | hard fail | Memory предсказуемость, отписки |
| Один и тот же тип push 5+ раз подряд | warning | Monotony |

## Anti-patterns workflow

| Anti-pattern | Severity | Почему |
|---|---|---|
| Push без чтения карты воронки (Mode A был доступен) | hard fail | Воронка = source of truth |
| Push без проверки `recent_push_log` (Mode B был выбран) | warning | No-repeat фильтр пропущен |
| Push без mandatory reads в `03-write.md` Pass 0 | hard fail | Voice будет generic |
| Output без A/B варианта (с config.validation.ab_variant_required: true) | hard fail | Не покрыто validation |
| Output без внутрянки (с config.validation.three_layers_required: true) | hard fail | Не накапливается обоснование выбора |

## Format errors

| Anti-pattern | Severity | Почему |
|---|---|---|
| JSON inline_keyboard невалидный | hard fail | Не парсится bot API |
| `callback_data` >64 байта (Telegram limit) | hard fail | Telegram API rejection |
| `url` не https | hard fail | Telegram требует https |
| `web_app` для бота без `bot.supported_button_types: web_app` | hard fail | Не работает в этом боте |

## Self-learning entries (новые, заполняется по фидбеку автора)

> Этот раздел растёт. Каждая правка автора → новая запись здесь и/или в `config.banned_terms`.

(пусто - заполнится по ходу применений)

## Cross-refs
