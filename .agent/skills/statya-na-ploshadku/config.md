# config - портируемые значения statya-na-ploshadku

> Адаптация под автора - только этот файл. Workflow и правила общие (продукт курса вайбмаркетинга)

## автор (по умолчанию)

```yaml
domain: <твой-домен>

# Воронка, в которую ведёт каждая площадочная статья (нативно, не рекламной подписью).
# Решение владельца: CTA = именная закрытая пригласительная ссылка канала,
# НЕ код-слово в общем боте и НЕ прямой лендинг трипваера (старый паттерн снят).
funnel:
  mechanic: named-invite                                # заявка на вступление в закрытый канал, бот пишет первым и одобряет
  # 🔴 Боевые значения (сервер/канал/бот/реестр инвайтов) - автор-специфика, в скилл НЕ хардкодится
  # (скилл раздаётся ученикам целиком). Канон и инструмент создания ссылки - во внешнем файле,
  # читается УСЛОВНО - есть на машине автора, нет на машине ученика:
  canon_file: .business/growth/seo/vc-funnel-canon.md   # [ -f ] gate
  fallback_if_missing: codeword                                 # нет своего закрытого канала → используй паттерн из раздела «Ученик курса» ниже

# Источник статей для адаптации (главный вход скилла) - рабочие папки SEO-конвейера lead-magnit:
# один slug = одна опубликованная статья сайта, вход = <articles_source>/<slug>/draft.md
# 🔴 ЭТО ЗНАЧЕНИЕ = work.path из ~/.claude/skills/lead-magnit/config.md (переехало из скилла
# наружу по решению автора - installer раздаёт содержимое каталога скилла ученикам дословно). Меняешь
# work.path там - поменяй и здесь, второго источника истины нет.
articles_source: .business/growth/seo/lead-magnit-work/

# URL полной версии статьи на своём сайте (для ссылки в адаптации).
# Живой URL собирается по паттерну и ДО вставки в текст проверяется curl -sI = 200
# Нормализация slug: slug уже начинается с "guide-" → префикс не дублировать,
# URL = https://<domain>/<slug>/ (проверено: /guide-guide-skilly/ = 404, /guide-skilly/ = 200)
article_url_pattern: "https://<твой-домен>/guide-<slug>/"

# 🔴 Бизнес-контекст читать ТОЛЬКО из .business/
# ЗАЧЕМ: ~/.business - симлинк на ШАБЛОН IvanOS с пустышками (там voice-profile 129 байт
# вместо канона). Текст, собранный по шаблону, выйдет безликим и не пройдёт humaniser
voice_profile: .business/voice-corpus/_voice-profile.md
business_context: .business/

# Рабочая папка прогона - внутри скилла, по одной на пару статья+площадка
workdir_pattern: work/<slug>-<площадка>/               # например work/guide-skilly-vc/
adapted_file: work/<slug>-<площадка>/adapted.md        # выход адаптации, его гонят все чекеры; для Хабра вместо adapted.md - karkas.md (режим каркас), ручной текст автора - final.md
images_dir_pattern: work/<slug>-<площадка>/images/     # картинки ТОЛЬКО сюда (не в .business/growth/produced)

# Темп публикаций (гард site reputation abuse)
tempo: 1-2 статьи в месяц на площадку
```

## Ученик курса (пример переопределения)

```yaml
domain: <свой-домен>
funnel:
  mechanic: codeword
  bot: <ссылка на своего бота или канал>
  tripwire: <свой трипваер>
  tripwire_url: https://<свой-домен>/<страница-трипваера>/
articles_source: <твой work.path из lead-magnit/config.md>   # тот же конвейер, свои slug
article_url_pattern: "https://<свой-домен>/<путь-статьи-со-slug>/"   # проверяется curl -sI = 200 до вставки
voice_profile: <свой voice-profile>
business_context: <своя папка бизнес-контекста>
workdir_pattern: work/<slug>-<площадка>/
images_dir_pattern: work/<slug>-<площадка>/images/
tempo: 1-2 статьи в месяц на площадку
```
