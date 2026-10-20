---
name: post-config
version: "2.0"
last_reviewed: 2026-08-04
description: Конфиг скилла post. Указывает пути к контексту проекта (аватар / JTBD / Brand DNA / Карта смыслов / последние посты) + platforms[] array (telegram-ru / linkedin-en / linkedin-ru / telegram-en) с per-combo voice references, lexicon files, char limits, CTA styles. v2.0 (рефактор архитектуры, AC8/AC12): секция voice_canon (внешний канон голоса по ключам), починены битые ссылки RU-лексикона (был указатель на несуществующий файл, RU-лексикон объявлен встроенным в этот файл).
---

# post config

> Это **точка адаптации скилла под конкретного автора**. Скилл (`post`) одинаков у автора и у учеников. Различие - только в этом файле и в данных, на которые он указывает.

---

## Subject (кто автор)

```yaml
subject:
  name: "<Твоё имя>"
  default_platform: telegram    # NEW v3.0 - default если не задан флаг --linkedin
  default_language: ru          # NEW v3.0 - default если не задан флаг --en
  channel_platform: telegram    # legacy (backward compat)
  channel_handle: null
  channel_url: null
  language: ru                  # legacy
  market: ru
  # Семантика ключевых терминов автора (для правильной интерпретации топиков)
  content_factory_definition: "<что у тебя за контент-формат>"
  product_focus: "<твоя ниша / продукт>"
  # ⛔ HARD: карта механизмов бизнеса. НЕ ПУТАТЬ И НЕ СВЯЗЫВАТЬ ПРИЧИННО 
  business_mechanisms:
    - name: "Контент-завод 2.0"
      что: "acquisition / growth машина органических подписчиков"
      где: "Нельзяграм / TikTok / Shorts (рилсы, карусели)"
      движок: "AI-pipeline уникализации и производства роликов"
      НЕ_связан_с: "картой смыслов. Ролики/карусели НЕ производятся по карте смыслов"
    - name: "Карта смыслов"
      что: "source of truth для контента ЗАПУСКА"
      где: "запуск в Telegram (посты, прогрев)"
      движок: "Claude по карте смыслов пишет посты/прогрев на запуск (Mode A/Plan этого скилла)"
      НЕ_связан_с: "контент-заводом. Карта смыслов НЕ управляет производством рилсов/каруселей для Нельзяграма"
  mechanism_confusion_rule: "Бан Нельзяграма бьёт по контент-заводу (acquisition), а НЕ по карте смыслов (запуск в TG). Это два независимых фронта. Запрещено писать что контент-завод/ролики/карусели работают по карте смыслов, или что устойчивость к бану держится на карте смыслов"
```

**Для ученика:** заменить `name`, `channel_handle`, `channel_url` на свои. Если канал ещё не запущен - `channel_url: null

---

## Projects registry (репликуемость, NEW)

> Реестр проектов для `/post --project <name>`. Резолвится в `workflow/00-project-context.md`. Без флага = `ivan` (поля subject/paths/voice/platforms ниже в этом файле). Сторонний проект = свой пакет СНАРУЖИ скилла; скилл читает его post-config, код не трогается.

```yaml
projects:
  ivan:
    pack: "self"            # источник = этот config.md (backward compat, не ломается)
    content_model: "launch"
  health:
    pack: ".business/проекты/здоровье/post-pack/post-config.md"
    content_model: "evergreen"
```

## Platforms (NEW v3.0) - 4 platform×language combinations

Каждая комбинация задаёт platform-specific параметры: char limit, tone, CTA style, voice references, lexicon file. Router в `workflow/01-router.md` Шаг 0.4 resolve активную комбинацию по input + флагам.

```yaml
platforms:
  # ============= TELEGRAM RU (default, v1-2 production) =============
  - key: telegram-ru
    platform: telegram
    language: ru
    char_limit: 2500              # Telegram максимум для длинного поста
    char_optimal: [1000, 2200]    # sweet spot для engagement
    tone: "разговорный, ты-форма, эмоциональный, конкретные числа"
    cta_style: "soft, в финале опционально"
    hashtags_policy: "none"        # TG не использует hashtags для distribution
    emoji_policy: "sparse, functional"
    no_markdown: false              # TG поддерживает разметку (но ограничено)
    voice_reference: "examples/_TEMPLATE.md"        # legacy fallback field, source of truth v2.0 = voice_canon секция выше (AC8)
    voice_living_language: "references/_voice-TEMPLATE.md"  # legacy fallback field, см. voice_canon.voice_profile
    voice_canonical: "references/_voice-TEMPLATE.md"        # legacy fallback field, см. voice_canon.voice_gold_standard
    lexicon_file: "config.md#lexicon-обязательная-и-запретная"  # RU-лексикон встроен в этот файл (см. раздел ниже), отдельного config-lexicon-ru.md НЕТ (в отличие от EN)
    competitors_dir: ".business/marketing/competitors/telegram-ru/"  # опц., СПРАВОЧНО: ни одна фаза workflow его не читает (проверено, grep = 0). Fallback на references/ru-author-patterns.md снят - файл в references/_archive/  # TBD
    review_extra_gates: []          # стандартный набор v2.2

  # ============= LINKEDIN EN (NEW v3.0, validated synthesis 29 авторов) =============
  - key: linkedin-en
    platform: linkedin
    language: en
    char_limit: 3000                # LinkedIn максимум 3000 для длинного поста
    char_optimal: [1300, 2200]      # sweet spot (по synthesis Section 1)
    tone: "professional but personal, peer-to-peer, NOT corporate jargon"
    cta_style: "soft default (newsletter PS / question / link-in-comments), hard reserved ONLY для launch weeks"
    hashtags_policy: "0-1 max"      # validated 19/29 в synthesis Section 5
    emoji_policy: "0-2 functional only (banned: 😀 face / 💖 heart / 🎉 sparkle / 7+ stacking)"
    no_markdown: true               # LinkedIn strips bold/italic Unicode
    hook_spacing_rule:              # Donnelly rule (validated synthesis Section 5)
      line_1_max_chars: 62
      line_2_max_chars: 62
      line_3_max_chars: 50
      see_more_cutoff: 210
    voice_reference: "references/_voice-TEMPLATE.md"  # ПУСТОЙ ШАБЛОН, не корпус постов. Источник истины = секция voice_canon выше; не подключён - гейты голоса печатают UNVERIFIED
    voice_synthesis: "references/_voice-TEMPLATE.md"   # то же: шаблон, не свод. Никаких «10 разделов» в нём нет
    voice_living_language: "references/_voice-TEMPLATE.md"  # TBD после накопления 10+ EN постов
    voice_canonical: "references/_voice-TEMPLATE.md"
    lexicon_file: "config-lexicon-en.md"
    competitors_dir: ".business/marketing/competitors/linkedin-en/"
    review_extra_gates:
      - "hook-preview-cutoff"       # line 1-3 spacing rule
      - "no-markdown-formatting"    # strip bold/italic
      - "hashtag-count-0-1"
      - "no-comment-word-gating"    # anti-Bolis/Donnelly DM-trigger
      - "no-us-business-jargon"     # ICP/GTM/RevOps explain or substitute
      - "ai-tells-en-22-phrases"    # delve/leverage/landscape/etc

  # ============= LINKEDIN RU (placeholder - нет истории) =============
  - key: linkedin-ru
    platform: linkedin
    language: ru
    char_limit: 3000
    char_optimal: [1300, 2200]
    tone: "TBD - RU LinkedIn audience сильно отличается от EN"
    cta_style: "TBD"
    hashtags_policy: "0-2 (RU LinkedIn более активно)"
    emoji_policy: "0-2 functional"
    no_markdown: true
    voice_reference: "TBD - после накопления 10+ RU LinkedIn постов автора"
    lexicon_file: "config.md#lexicon-обязательная-и-запретная"  # reuse RU lexicon встроенного в этот файл (не отдельный файл)
    competitors_dir: ".business/marketing/competitors/linkedin-ru/"  # опц., СПРАВОЧНО: читателя в workflow нет (см. telegram-ru выше). Fallback на references/ru-author-patterns.md снят - файл в references/_archive/  # TBD
    status: "placeholder - НЕ использовать пока не накоплены данные"

  # ============= TELEGRAM EN (placeholder - нет EN TG audience) =============
  - key: telegram-en
    platform: telegram
    language: en
    char_limit: 2500
    char_optimal: [1000, 2200]
    tone: "TBD"
    cta_style: "soft"
    hashtags_policy: "none"
    emoji_policy: "sparse"
    no_markdown: false
    voice_reference: "TBD"
    lexicon_file: "config-lexicon-en.md"
    status: "placeholder - НЕ использовать пока не запущен EN TG канал"
```

**Для ученика:** оставить telegram-ru (default), удалить остальные если не нужны. Добавить свои platforms если выходит на новые каналы.

---

## Voice canon (NEW v2.0, AC8) - внешний канон голоса

> Корень дефекта до v2.0 (R1 дефект 1): ядро-канон голоса ссылалось на внутрискилловые заглушки `references/_voice-TEMPLATE.md` (458 байт, «Пока пусто») - 62 ссылки исполнялись вхолостую, гейты PASS на пустоте. Реальный канон голоса живёт СНАРУЖИ скилла. С v2.0 конвейер читает эти пути ИЗ CONFIG, а не хардкод внутри workflow/.

```yaml
voice_canon:
  form_canon: ".business/voice-corpus/_format-canon-v2.md"  # КАНОН ФОРМЫ v2.6: §2.1 дерево решений цели, §3 профили длины, §9 гейты - всё на чистом корпусе 296 постов ДВУХ доноров (Донор-Б/Донор-А, окно 12 мес). §10 = слой ТРЕТЬЕГО донора (Донор-В, n=31 чистых (56 в окне)): наблюдения и приёмы, порогов и гейтов не даёт - его вклад в скилл это справочник `references/donor-copy-devices.md` и 3 эталона в `scripts/etalons.json`. ПЛЕЙСХОЛДЕР для учеников - своего файла нет, читатели ключа деградируют на встроенные числовые профили роутера (см. ниже)
  voice_profile: ".business/voice-corpus/_voice-profile.md"  # целиком, ~25КБ - лексика/интонация/табу
  voice_corpus_dir: ".business/voice-corpus/A-telegram/"  # 3-5 эталонов класса (form_class-aware выборка)
  checklist_ivana: ".business/processes/checklist-postov-ivana.md"  # HARD mandatory read + гейт AC4 (B1/B3, прикладная ценность)
  ps_action_canon: ".business/запуски/<active-launch>/PS-ACTION-канон.md"  # эталон приписки PS-ACTION (класс 10 R2, гейт CTA/деньги). lint-post.py находит его сам глобом по ~/…/запуски/*/, нет файла - гейт печатает «не применяется»
  etalon_post: ".business/запуски/<active-launch>/_etalon-post-ivana-0608.md"  # NEW по решению автора: ЭТАЛОННЫЙ ПОСТ АВТОРА - мерило «стоит ли мой пост рядом с этим». Читается УСЛОВНО (нет файла - гейт 4.ET пропускается с пометкой)
  owner_lexicon: ".business/processes/lint-owner-lexicon.json"  # 🔒 4i: ЛИЧНЫЙ СЛОВАРЬ ЗАПРЕТОВ для scripts/lint-post.py (запретное слово события, снятый концепт, класс возражений, личные имена факт-базы). Живёт ВНЕ скилла, читается условно; нет файла - эти HARD-гейты словаря печатают [PASS] 0 и не блокируют. Переопределяется env POST_OWNER_LEXICON
  konstrukcii: ".business/voice-corpus/_konstrukcii-zhivogo-yazyka.md"  # NEW по решению автора: СЛЕПОК ЖИВЫХ КОНСТРУКЦИЙ - справочник заготовок (зачины/связки/вопросы/финалы/обращения/частицы/ритм/50 формул заголовка) с дословными примерами и частотами по трём корпусам. Машинное зеркало рядом: `_konstrukcii-zhivogo-yazyka.json`. Читают 02f-polish, 03-dry и гейт 4.ЯЗ в 04-review. Читается УСЛОВНО
```

**🔴 `konstrukcii` - живая половина закона о языке (NEW по решению автора).** Владелец по решению автора: «Ты полностью неживой, мёртвый язык даёшь... Тебе нужно прямо языковую модель создать полноценную, которая будет в нашем движке стоять и посты делать». Закон разложен на две половины, и обе обязательны:

- **машинная** - блок «мёртвые конструкции» (классы К1-К11) в `scripts/lint-post.py`: ловит синтаксис, который проходил словарные гейты и всё равно читался мёртвым (симметрия «не потому X, а потому Y», обобщённый субъект, псевдо-утешение, «выглядит одинаково», афоризм-пуант каскадом, серийный зачин датой, дейктик-заголовок и т.д.);
- **живая** - этот слепок: из чего конструкция БЕРЁТСЯ, когда мёртвая снята.

> ключ отсутствует / пуст / `[ -f ]` не проходит → фазы печатают `слепок конструкций не подключён (config.voice_canon.konstrukcii)` и работают как раньше; линтер это не трогает, его классы К1-К11 вшиты в код и блокируют всегда. Ключ заполнен И файл читается → правило сборки обязательно: **зачин, связка и финал каждого предложения обязаны иметь прецедент в слепке; сомневаешься - открой слепок и возьми оттуда**.

Ученик кладёт сюда СВОЙ слепок (собирается тем же способом: 10-15 своих лучших постов + корпус доноров своей ниши → классы с дословными примерами и частотами) либо оставляет ключ пустым.

**🔴 `etalon_post` - условное чтение, никогда не блок по отсутствию (NEW по решению автора).** Ключ указывает на один пост автора, признанный эталоном качества содержания: его читают `02d-components-options.md` Шаг 0 (при `form_class = event`) и гейт `4.ET` в `04-review.md` (при любом классе). Правило доступа - ровно как у остальных ключей секции, без исключений:

> ключ отсутствует / пуст / `Read` по пути вернул ошибку → гейт `4.ET` печатает `4.ET: N/A - эталон не подключён (config.voice_canon.etalon_post)` и НЕ блокирует выдачу. Ключ заполнен И файл читается → сравнение обязательно, пропуск = FAIL.

Проверка перед чтением - `[ -f <путь> ]` (или `Read` с обработкой ошибки), не слепой `Read`. Ученик кладёт сюда СВОЙ лучший пост либо оставляет ключ пустым: своего файла по пути автора у него нет и не будет.

**⚠️ Для раздачи ученикам эти 8 ключей ОСТАЮТСЯ ПЛЕЙСХОЛДЕРАМИ автора.** У ученика этих файлов нет и не будет по этим путям - при отсутствии файла скилл НЕ падает. Ученик подключает СВОЙ канон голоса, заполняя эти ключи своими путями тем же способом, каким заполняет `paths.voice_reference` ниже: собственный gold-standard из своих лучших постов, свой `_voice-profile.md`, **свой корпус эталонов**, свой чек-лист правок (если есть).

**🔴 Схема записи `scripts/etalons.json` (уточнено, дефект Д62 скептик-раунда 17).** Ученик, подставляя свой набор эталонов вместо `3 эталона в scripts/etalons.json` выше, пишет список объектов; `bench-post.py` (`load_etalons`) валидирует КАЖДУЮ запись отдельно, а не файл целиком. Обязательные ключи записи: `text` (непустая строка - текст поста-эталона), `id` (любой не-`None`), `author` (непустая строка), `form_class` (непустая строка - `narrative`/`razbor`/`sales`/…). Опциональные: `uid` (человекочитаемый `Автор:id`, иначе строится из `author`+`id`), `er_idx` (engagement rate), `cls` (метка класса для людей, кодом не читается). Запись без обязательного ключа в набор не идёт - причина копится и печатается одной строкой `[INFO] эталоны: отброшено N записей без обязательных ключей (…)`; если битыми оказались ВСЕ записи - список пуст, действует та же мягкая деградация, что и на отсутствующий/битый файл (`ВЕРДИКТ:` и exit-код бенча не меняются ни в одном случае). Полная схема с обоснованием - докстринг `load_etalons()` в `scripts/bench-post.py`.

**🔴 Что именно происходит при недоступном каноне (исправлено по решению автора, дефект Д9).** Формулировка «молча откатывается на заглушку `references/_voice-TEMPLATE.md`» была неверной и порождала ложный `PASS`: заглушка - ПУСТОЙ ШАБЛОН, сверять по ней нечего. Правило одно на все гейты голоса:

> ключ пуст / файл по пути не проходит `[ -f <путь> ]` → гейт печатает `UNVERIFIED` со строкой «канон … не подключён (config.voice_canon.<ключ>)» и НЕ печатает `PASS`. Пункты, проверяемые по самому посту (счётчики, анти-паттерны, последние 5 постов канала, код-банк `lint-post.py`), работают и блокируют как обычно.

Гейты, где это прописано дословно: `04-review.md` 4.B (шапка), 4.B.6, 4.B.9, 4.6.1, 4.7.1 · `05-publish.md` Слой 2. `references/_voice-TEMPLATE.md` остаётся ШАБЛОНОМ для заполнения учеником (структура разделов + указатель на этот config), не источником закона.

**🔴 Деградация `form_canon` (NEW, скептик-раунд 3, по решению автора).** Путь к канону формы до этого был ВПИСАН РУКАМИ в три файла скилла (`workflow/01-router.md` Шаг 0.49, `workflow/04-review.md` гейт 4.0.3b, `SKILL.md` Принцип 0) - то есть у ученика три обязательных `Read` вели в никуда, и это ломало не голос, а сам маршрут выбора цели. Теперь путь читается ОТСЮДА, а при недоступности файла ветка одна и та же во всех трёх местах:

> файл по `config.voice_canon.form_canon` не читается → работать на **встроенных числовых профилях роутера** (они уже вшиты в `01-router.md` Шаг 0.49 таблицей коридоров и в `scripts/lint-post.py` функцией `resolve_form_profile` - это и есть цифры канона, вынутые в код) + напечатать строку **«канон формы недоступен, работаю на встроенных профилях»**. Цель формы объявляется как обычно, дерево решений §2.1 прогоняется по его копии в роутере. Это НЕ разрешение выдать пост без объявленной цели: пустой `form_goal` остаётся FAIL с возвратом в Шаг 0.49.

---

## Paths (где лежит контекст проекта)

Все пути относительно корня проекта (у тебя это `~/IvanOS`).

```yaml
paths:
  # Аудитория
  avatar: ".business/audience/avatar.md"
  segments: ".business/audience/avatar.md"  # сегменты внутри avatar (раздел «по сегменту»)
  objections: ".business/audience/objections.md"
  journey: ".business/audience/journey.md"

  # Продукт
  products_dir: ".business/products/"
  pricing: ".business/products/pricing.md"

  # Brand DNA / голос
  brand_dna: ".business/Распаковка бренда.md"
  voice_reference: "examples/_TEMPLATE.md"

  # JTBD
  jtbd: ".business/audience/avatar.md"  # JTBD-раздел внутри avatar (отдельного файла нет; не падать)

  # Карта смыслов (Mode A - Plan). active-launch РАСКРЫТ (был плейсхолдер - прецедент 2026-05-31)
  # active_launch НЕ дублируется здесь - канонический слот один, блок «Активный запуск» внизу файла
  # 🔒 Подэтап 4i. Пути к папке запуска: через `~` (НЕ абсолютом с именем пользователя)
  # и через токен `<active-launch>`, который подставляется из блока `active_launch`
  # внизу файла - это ЕДИНСТВЕННЫЙ слот с именем запуска, дубля здесь больше нет.
  # Читаются УСЛОВНО: нет файла (машина ученика) - читатель ключа деградирует молча,
  # ровно как описано в блоке про `etalon_post` выше.
  content_map: ".business/запуски/<active-launch>/5.2-Карта-смыслов.md"        # ТЕЛО смыслов: дословные цитаты ЦА (q7/q9), симптомы, сцены, COI
  content_plan: ".business/запуски/<active-launch>/Контент-план-матрица.md"   # день × каналы: ячейка дня = коды смыслов + механика + CTA
  formulations_bank: ".business/запуски/<active-launch>/5.0-Подтверждённые-формулировки.md"  # каноничные формулировки (статусы АПРУВ 1×/2×+)
  story_bank: ".business/story-bank/"  # личные сцены для якоря «личный момент - метод»

  # 🔴 Источники ЖИВЫХ СЦЕН (NEW по решению автора, потребитель - workflow/02b1-scene-mining.md).
  # Все читаются УСЛОВНО через `[ -f ]` / `[ -d ]`: ключ пуст или пути нет (машина ученика) -
  # источник молча пропускается, добыча идёт дальше по порядку S1→S8, скилл НЕ падает.
  personal_setup: ".business/ЛИЧНЫЙ-СЕТАП-владельца.md"   # S2: закрытый канон личных фактов автора, у каждого факта улика файл:строка и статус свежий/жжёный
  analytics_dir: ".business/growth/analytics/"        # S3: разборы своих и чужих архивов - сцены «прогнал и увидел число»
  retrospectives_dir: "~/IvanOS/retrospectives/"               # S7: рефлексии сессий - лучший источник поля broke («что пробовал и не сработало»)
  session_logs_dir: "~/.claude/projects/<project-slug>/"     # S8: логи сессий (.jsonl), дорого - только когда S1-S7 пусты
  tools_catalog: ".business/growth/КАТАЛОГ-внутрянки-инструментов.md"  # СПРАВОЧНО, НЕ источник сцены: даёт механику и ограничения, лица и времени в нём нет
  content_map_format: "thematic"  # calendar | thematic | hybrid
  # ⛔ RESOLVE-протокол : ячейка плана = КОД-указатель.
  # Перед draft код ОБЯЗАТЕЛЬНО развернуть в тело 5.2 + формулировку 5.0 (дословный перенос, правило 6.1). См. 02b-research-summary.md Шаг 1.
  # Дополнительные источники инфоповодов (читать вместе с content_map)
  content_topics_extra:
    - ".business/Распаковка бренда.md#15-карта-инфоповодов"  # раздел 15 - актуальные смыслы запуска

  # История постов (для no-repeat / archetype rotation)
  recent_posts_source: "webfetch"  # webfetch | file | none
  recent_posts_url: "<твой-tg-канал>"
  recent_posts_count: 5

  # Запретные термины и обязательная лексика (RU встроен в этот файл, см. раздел "## Lexicon" ниже; отдельного config-lexicon.md/config-lexicon-ru.md НЕТ)
  lexicon: "config.md#lexicon-обязательная-и-запретная"
```

**Для ученика:**
1. Скопировать дерево `.business/` из шаблона курса под свой проект.
2. Заполнить файлы: `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`.
3. Указать **активный запуск** в `<active-launch>` (если идёт запуск) или удалить ссылки на `content_map` (Mode A работать не будет, останутся Mode B и Mode C).
4. Указать URL канала или поставить `null` если канал свежий.

---

## Voice parameters

```yaml
voice:
  archetypes_allowed: ["Magician", "Sage", "Outlaw"]
  archetypes_banned: ["Caregiver", "Lover", "Innocent"]
  rhythm: "1/3/1"
  pronoun: "ты"
  formality: low
  rotation_window: 3  # не повторять archetype последние N постов
```

**Для ученика:** настроить под свою позиционировку. Если непонятно какие архетипы - пройти Фазу 0 запуска (опрос аудитории + Brand DNA), архетипы выйдут оттуда.

---

## Lexicon (обязательная и запретная)

> **Это и есть RU-лексикон.** Битые ссылки на `config-lexicon-ru.md`/`config-lexicon.md` (несуществующие файлы) починены v2.0: везде выше в этом файле (`lexicon_file`/`lexicon` у telegram-ru и linkedin-ru) стоит self-ссылка `config.md#lexicon-обязательная-и-запретная` на этот раздел. RU-лексикон живёт встроенным здесь, в отличие от EN, у которого свой отдельный `config-lexicon-en.md`.

```yaml
lexicon_required:
  # Замены которые скилл делает auto
  - replace: "Instagram"
    with: "Нельзяграм"
  - replace: "инстаграм"
    with: "Нельзяграм"

lexicon_banned_hard:
  # Auto-fail если попадается в выходе (expanded по решению автора v2.0)
  # Existing
  - "-"  # em-dash внутри строк (только в начале буллета можно)
  - "artifact"
  - "digital-twin"
  - "fast-action"
  - "Grand Slam Offer"
  - "КЭВ"
  - "связки"

  # Англицизмы-формализмы (verified 0/65 в corpus автора)
  - "валидируется"
  - "валидация"
  - "валидировать"
  - "onboarding"
  - "онбординг"
  - "engagement"
  - "энгейджмент"
  - "retention"
  - "ретеншн"
  - "релевантность"
  - "scope"
  - "скоуп"
  - "pipeline"
  - "пайплайн"
  - "framework"
  - "фреймворк"
  - "assessment"
  - "case study"
  - "workflow"
  - "webhook"
  - "endpoint"
  - "rate-limit"
  - "upsell"
  - "hockey stick"
  - "pre-launch"
  - "watchlist"
  - "burnt-in"
  - "voice cloning"
  - "production-ready"
  - "оркестратор"
  - "функционал"
  - "тюнинговать"
  - "протюнинговал"
  - "промт-инжиниринг"
  - "таргетинг"
  - "бенчмарк"
  - "фидбэк"
  - "нетворк"

  # V1 hallucinations (verified 0/65 в corpus, выкинуты в v2.0)
  - "бахнул"
  - "забахал"
  - "выкатил"
  - "выкатываю"
  - "выкачу"
  - "вкатил"
  - "вкатился"
  - "уделал"
  - "затащил"
  - "втащил"
  - "у ребят"
  - "один пацан"
  - "обратно в найм поползли"
  - "вот как устроено"
  - "расписываю"

  # Mortuary formals (0/65, AI-biographical)
  - "потеряли клиентов"
  - "вернулись на найм"
  - "ушли на найм"
  - "лишились аудитории"
  - "лишились клиентов"
  - "растеряли"
  - "затухли"
  - "угасли"
  - "дотянуть до результата"
  - "достичь результата"
  - "реализовать себя"
  - "обрести опыт"
  - "осуществить переход"
  - "совершить покупку"

  # Formal explanatory linkers (audit-gap)
  - "именно поэтому"
  - "так как"
  - "в результате чего"
  - "по причине"
  - "вследствие"
  - "таким образом"
  - "следовательно"
  - "не из-за"

  # Subject naming formal nouns (когда обозначают третье лицо)
  # NB: эти проверяются в context - auto-fail только в pattern «один + N» / «у N с +число»
  # См. 04-review.md 4.8.9

  # Generic AI clichés
  - "без воды"
  - "без теории"
  - "безопасная подушка"
  - "финансовая страховка"
  - "образ жизни ради которого"
  - "адская"
  - "звезду прошлого"

lexicon_banned_patterns:
  # Не auto-string-match, а семантическая проверка в 04-review (4.1.7 / 4.8)
  - metaphors: "любой глагол в небуквальном значении - fail (см. workflow/04-review.md шаг 4.1.7)"
  - invented_collocations: "выдуманные словосочетания которые не встречаются в живой речи - fail"
  - examples_banned:
      - "ломает контент-завод"
      - "закрывает контент-завод"
      - "вынесли мозг"
      - "на грани неприличия"
      - "собирать рилсы руками"
      - "склеивать рилсы руками"
      - "прёт / залетел / взорвался" (если буквально не происходило)
      # NEW по решению автора — класс «не-русский язык» (автор разнёс пост):
      - "список заходов"        # несуществующее словосочетание → «подборка роликов»
      - "проверенные заходы"    # жаргон-слоган → «то, что набрало просмотры»
      - "заходы сработали"      # неправильная сочетаемость (работают люди, не заходы)
      - "зашло / зашедшее"      # как факт-объект → «набрало просмотры»
      - "бить в аудиторию"      # жаргон-слоган → «снимать для такой же аудитории»
      - "радар на чужие победы" # абстрактный слоган → конкретика
      - "лежит не пустота"      # метафора → «не пустой экран»
      - "контент собирается"    # ГРУБО: контент не собирается → «контент делают/генерят»
      - "собирать контент"      # собирают камни/мусор/лего, не контент → «делать/генерить»
      - "робот"                 # абстракция/бабушкин язык → «скилл / воркфлоу / парсер / имя»
      - "роботы"                # то же → реальные сущности (скиллы/воркфлоу)
      - "сам инструмент"        # категория-слово вместо имени программы/модели → называть по имени (мн.ч. «инструменты» живое)

  # Structural thresholds (см. 04-review.md 4.8)
  - colons_per_post_threshold: 1  # >1 двоеточия на пост = FAIL (автор ; машинно - lint-post.py check_colons; время 19:00 и URL не считаются)
  - passive_voice_ratio_threshold: 0.15  # > 15% = WARNING, > 25% = FAIL
  - participle_phrase_count_threshold: 2  # > 2 = WARNING, > 4 = FAIL
  - tricolon_per_post_threshold: 1  # ≥2 в одном посте = FAIL
  - section_headers_colon_threshold: 1  # ≥2 = FAIL
  - numbered_steps_threshold: 3  # fallback при пустом brief.form_goal: ≥4 numbered steps в TG-post = FAIL (поведение как сегодня)
    # K3 (канон формы v2 §9, соответствует I7): при объявленной цели порог берётся из профиля, не из этой константы:
    #   R-нарратив и S (продажа): порог 0 - любая нумерация `^\d+\.` или «Шаг N» = FAIL (R держат 93%/88% верха соответственно)
    #   R-разбор: нумерация разрешена (25% против 17%, обратный знак - гейт снят, не FAIL)
    #   F (репосты): разрешён алгоритм 3-5 нумерованных шагов (единственное место, где нумерация желательна)
  - numeric_density_threshold: 10  # >10 цифр = WARNING
  - reveal_headings_threshold: 1  # ≥4 = FAIL

  # Double emphasis patterns (regex, см. 4.8.7)
  - double_emphasis_patterns:
      - "(прямо сейчас|сейчас|сегодня),\\s+(каждый день|постоянно|регулярно|всегда)"
      - "(всегда|везде|всюду),\\s+(всегда|везде|всюду)"
      - "(каждый день|каждый раз|каждое утро),\\s+(весь день|круглые сутки)"

  # Fake-precision regex (R-15)
  - fake_precision_pattern: "\\b\\d+\\.\\d\\b"  # 3.4%, 2.3x, 15.8

  # Formal subject nouns (in context "один + X" / "у X с +число")
  - formal_subject_nouns:
      - "эксперт"
      - "специалист"
      - "предприниматель"
      - "автор контента"
      - "пользователь"
      - "человек"

  # Genre HARD ABORT pattern (см. 4.8.6 в workflow/04-review.md)
  - tutorial_genre_pattern:
      - "Сейчас разберу что я называю"
      - "Топ-3 ошибки"
      - "Топ-5 ошибок"
      - "5 шагов чтобы"
      - "Шаг 1.+Шаг 2.+Шаг 3.+Шаг 4"

lexicon_warnings:
  # Предупреждение, не блокер
  - pattern: "![!]+"  # больше одного восклицательного
    message: "more than one exclamation mark"
  - pattern: "^[-*•]"
    count_threshold: 2
    message: "more than one bullet list per post"
    # K2 (канон формы v2 §3): при пустом brief.form_goal порог остаётся 2 (fallback, поведение как сегодня).
    # При объявленной цели читать профиль вместо фиксированной двойки:
    #   R-нарратив: списочных блоков 0 (HARD, canon §9 R-9) - warning здесь избыточен, гейт уже блокирует
    #   R-разбор: ≤1 блок до 3 предикативных пунктов (WARN)
    #   F: 1-2 блока тире со ссылкой - желателен, порог warning поднимается до 3
    #   S: ≤1 блок (как fallback)
```

**Для ученика:** базовый список одинаков (em-dash, числа восклицаний). Добавить свои запретные термины и обязательные замены под свою нишу.

---

## Validation refresh tracking

```yaml
validation:
  banned_list_last_review_date: "2026-05-27"
  banned_list_refresh_interval_days: 7
  banned_list_refresh_workflow: "workflow/06-banned-refresh.md"
```

---

## Output settings

```yaml
output:
  ab_variants: 2  # сколько A/B вариантов генерим помимо основного
  show_self_check_report: true
  show_stepps_score: true
  # emoji_policy убран отсюда (канон формы v2, K1): единственный источник числа эмодзи -
  # `references/formatting-skeleton.md` §4 (потолок 0-3), который при объявленной цели
  # (brief.form_goal) читает профиль канона §3. Третье конкурирующее правило по эмодзи
  # (это поле + platforms[].emoji_policy) создавало случайность - убрано, platforms[].emoji_policy
  # остаётся как platform-specific ограничение (например LinkedIn 0-2), не как общий дефолт
```

---

## Quick start для нового пользователя

Если ты ученик и только что склонировал скилл:

1. **Прочитай SKILL.md** - поймёшь архитектуру.
2. **Запусти `/post`** без аргументов в первый раз.
3. Скилл проверит этот config и спросит чего не хватает.
4. **Заполни недостающее** - путь к avatar, JTBD, brand-dna.
5. Если каналу ещё не из чего тянуть посты - установи `recent_posts_source: none`.
6. **Запусти `/post про X`** - получишь первый пост.

---

## Активный запуск автора

```yaml
active_launch:
  ru: "<твоя-папка-запуска>"
  en: null  # ещё не стартовал
```

Используется для подстановки в `<active-launch>` выше. Когда стартует новый запуск - обновить здесь.
