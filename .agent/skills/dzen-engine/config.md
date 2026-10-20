# config - портируемые значения dzen-engine

> Адаптация под автора - только этот файл. Workflow и правила площадки общие для всех

## автор (по умолчанию)

```yaml
domain: <твой-домен>

# Канал Дзена, куда публикуется статья (руками через веб-редактор, API у площадки нет)
dzen_channel: <ссылка на свой канал Дзена>

# Воронка, в которую ведёт дзен-статья - нативно, не рекламной подписью:
# код-слово → t.me бот → трипваер
# Куда ведёт код-слово из статьи - решаешь ты. Значения ниже это ПРИМЕР формы,
# а не готовая воронка: подставь свой бот, свой продукт и свою ссылку.
# Держи ОДИН ответ на вопрос «куда ведёт статья»: разные CTA в разных статьях
# размывают замер, и потом непонятно, что сработало
funnel:
  mechanic: codeword
  bot: t.me
  tripwire: <твой-продукт>                                  # только имя продукта, без внутреннего жаргона (правка 16.08.2026)
  tripwire_url: https://<твой-домен>/<твой-продукт>/

# Главный вход движка - рабочие папки SEO-конвейера lead-magnit:
# один slug = одна опубликованная статья сайта, вход = <articles_source>/<slug>/draft.md
# 🔴 ЭТО ЗНАЧЕНИЕ = work.path из ~/.claude/skills/lead-magnit/config.md (переехало из скилла
# наружу по решению автора - installer раздаёт содержимое каталога скилла ученикам дословно). Меняешь
# work.path там - поменяй и здесь, второго источника истины нет.
articles_source: .business/growth/seo/lead-magnit-work/

# URL полной версии статьи на своём сайте (для ссылки внутри дзен-статьи).
# Живой URL собирается по паттерну и ДО вставки в текст проверяется curl -sI = 200.
# Нормализация slug: slug уже начинается с "guide-" → префикс не дублировать
# (проверено: /guide-guide-skilly/ = 404, /guide-skilly/ = 200)
article_url_pattern: "https://<твой-домен>/guide-<slug>/"

# 🔴 Бизнес-контекст читать ТОЛЬКО из .business/
# ЗАЧЕМ: ~/.business - симлинк на ШАБЛОН IvanOS с пустышками (voice-profile 129 байт
# вместо канона). Текст по шаблону выйдет безликим и не пройдёт humaniser
voice_profile: .business/voice-corpus/_voice-profile.md
business_context: .business/

# Рабочая папка прогона - внутри скилла, одна на статью
workdir_pattern: work/<slug>/
adapted_file: work/<slug>/adapted.md          # выход адаптации, его гонят все чекеры
source_file: work/<slug>/source.md            # скачанный исходник, если вход = URL
images_dir_pattern: work/<slug>/images/       # картинки ТОЛЬКО сюда

# Темп публикаций (гард site reputation abuse)
tempo: 1-2 статьи в месяц
```

## Ученик курса (пример переопределения)

```yaml
domain: <свой-домен>
dzen_channel: <ссылка на свой канал Дзена>
funnel:
  mechanic: codeword
  bot: <ссылка на своего бота или канал>
  tripwire: <свой трипваер>
  tripwire_url: https://<свой-домен>/<страница-трипваера>/
articles_source: <твой work.path из lead-magnit/config.md>
article_url_pattern: "https://<свой-домен>/<путь-статьи-со-slug>/"
voice_profile: <свой voice-profile>
business_context: <своя папка бизнес-контекста>
workdir_pattern: work/<slug>/
images_dir_pattern: work/<slug>/images/
tempo: 1-2 статьи в месяц
```
