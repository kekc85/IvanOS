---
name: email
description: Email-машина для контент-фабрики. Производит готовые письма (Subject + Preheader + Body + CTA) под Kit / Beehiiv / любой ESP. Portable by config.md. 3 mode (Plan из карты воронки / Spark / Transcript) × 2 subject × 3 language (RU/EN/both). 8 типов (v1 = nurture / launch-sequence / sales-letter). Review = 6-Pass + Maxwell Ross 9 + EMAIL-G1-10 + 3 слоя. Subject всегда ровно ОДИН (варианты не выдавать - правка автора). Triggers /email, "напиши письмо про X", "sequence day N", надиктовки >500 знаков.
metadata:
  version: "1.0.1"
  created: "2026-05-28"
  last_reviewed: "2026-05-28"
  artifact_type: "action"  # DONE v1.0.1: implemented 5 mandatory gates (Pass 0.5 PII / 0.6 Event / 0.7 Fact / EMAIL-G3 verb+object / Layer 5.5 Self-Review). См. skill-craft/knowledge/bug-categories.md «Категории для action skills».
---

# email - Portable email-машина для контент-фабрики

> Skill производит готовые письма в голосе автора. Цель - конверсия в воронке, не виральность. Базируется на референсах email-копирайтинга (Welsh, Halbert, Boron Letters, Sparkloop) + voice-bridge на `post` (общий voice автора).

## Архитектура

Skill portable: один и тот же код работает у автора и у учеников курса вайбмаркетинга. Различие - только `config.md` и данные проекта, на которые он указывает.

**Три ортогональных axis:**

| Axis | Значения |
|---|---|
| **Mode** (откуда смысл) | Plan (карта воронки / launch sequence position) / Spark-B1 (тема пользователя) / Spark-B2 (генерация под JTBD) / Transcript (надиктовка) |
| **Subject** (кто автор) | автор / ученик (свой config + свой `.business/`) |
| **Language** | RU / EN / both (культурная адаптация, не дословный перевод) |

**Router** в `workflow/01-router.md` auto-detect'ит mode по сигналам в input. Override через флаги `--plan` / `--spark` / `--transcript` / `--en` / `--ru` / `--both`.

**Onboarding** для нового пользователя - `workflow/00-onboarding-student.md`. Срабатывает при отсутствии или неполном `config.md`. После onboarding ученик имеет заполненный config + intake-файлы и может запускать `/email`.

## Когда применять

Триггеры (auto-detect mode в router):

| User input | Mode | Что делает |
|---|---|---|
| `/email` без аргументов | Plan | Берёт письмо N из карты launch sequence активного запуска |
| «по карте воронки», «sequence day N», «launch day N» | Plan | То же |
| `/email про X` / «напиши письмо про X» / «email про X» | Spark-B1 | Расширяет тему X в 3-5 углов, ты выбираешь |
| «дай идеи письма» / «что отправить базе» | Spark-B2 | Генерит 5-7 идей под JTBD/avatar/CJM stage |
| Длинный текст (>500 знаков) с пометкой email / «надиктовал → email» | Transcript | Извлекает 3-10 атомарных смыслов, выбираешь top-1-3 |

**Не применять** для:

- TG-поста → `post`
- Поста в Нельзяграм / X / LinkedIn → `paips-post` / `spiky-one-liner`
- Длинной статьи / эссе / newsletter web publication / LinkedIn article (800-3000 слов, web archive matters, без обязательных Subject+Preheader+CTA) → `longform`
- Бот-рассылки TG push (100-300 chars + inline-кнопки) → `bot-message`
- Видео-скрипта → `replicate-reel` / `produce-reel`
- Лендинг-копи → планируется `landing-copy`
- Сборки email-воронки целиком (welcome-серия + автоматизации + сегментация под нишу) → `email-voronka` (он даёт брифы, письма по ним пишет этот скилл)

**Граница email vs longform (важный split):**

- `email` = **ESP broadcast** (Kit/Beehiiv) с обязательными **Subject + Preheader + Body + CTA**. Цель - **конверсия в воронке** (клик → лендинг / клуб / cash event). Длина 300-1500 слов. Mobile inbox-first.
- `longform` = **web publication** (Beehiiv/Kit web view / personal blog / LinkedIn article). Цель - **архив + индексация + reach**. Длина 800-3000 слов. Read-first, не broadcast push.

**Правило выбора:** если письмо идёт по списку с Subject в inbox → `email`. Если артефакт публикуется как статья и потом, возможно, рассылается из web → `longform` (а в email-broadcast превращается opt-in через POSSE pipeline `~/.claude/skills/longform/workflow/05-publish.md`).

## Workflow (progressive disclosure)

При вызове skill последовательно грузит соответствующие `workflow/` файлы:

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

01-router.md                  ← detect mode + language + load config
   ├─ 01a-plan.md             ← Mode A: из карты воронки / sequence position
   ├─ 01b-spark.md            ← Mode B1/B2: ситуативный
   └─ 01c-transcript.md       ← Mode C: из надиктовки
       ↓
01-finalize.md                ← detect type (8 типов) + длина + sequence position
02-structure.md               ← каркас Subject + Preheader + Body + CTA по типу
03-write.md                   ← Pass 0 mandatory reads + draft + voice injection
04-review.md                  ← 6-Pass + Maxwell Ross 9 + EMAIL-G1-10 + 3 слоя
05-publish.md                 ← output + ОДИН Subject + ESP-ready format
```

**Файлы:**

| Файл | Назначение |
|---|---|
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 9 вопросов под email-канал |
| `workflow/01-router.md` | Auto-detect mode + language + subject |
| `workflow/01a-plan.md` | Mode A: читает карту воронки / launch sequence map по дате/позиции |
| `workflow/01b-spark.md` | Mode B1: расширение темы / Mode B2: генерация под JTBD |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в атомарные смыслы |
| `workflow/01-finalize.md` | Общая доводка brief: type/длина/sequence-position/CTA-goal |
| `workflow/02-structure.md` | Каркас Subject + Preheader + Body skeleton + CTA по типу письма |
| `workflow/03-write.md` | Draft + voice injection (1/3/1 rhythm, plain-text bias) |
| `workflow/04-review.md` | 6-Pass + Maxwell Ross 9 + EMAIL-G1-10 + 3 слоя |
| `workflow/05-publish.md` | Output + ОДИН Subject + ESP-ready format + self-check |

## 8 типов писем (templates)

| # | Тип | Длина (слов) | Template | Применение | Версия |
|---|---|---|---|---|---|
| 1 | Nurture letter | 600-900 | `templates/nurture-letter.md` | Regular newsletter, edutainment | v1 |
| 2 | Launch sequence email | 500-1200 | `templates/launch-sequence-email.md` | Часть 5-8 letter cash-event sequence | v1 |
| 3 | Sales letter | 800-1500 | `templates/sales-letter.md` | Окно продаж (open cart day, last call) | v1 |
| 4 | Weekly digest | 300-600 | templates/weekly-digest.md (v2 planned) | Regular round-up топ-3 ссылок/мыслей | v2 |
| 5 | Re-engagement | 400-700 | templates/re-engagement.md (v2 planned) | Winback неактивных (>60 дней) | v2 |
| 6 | Welcome email | 500-1000 | templates/welcome-email.md (v2 planned) | Soap opera #1 после подписки | v2 |
| 7 | Abandoned cart | 300-500 | templates/abandoned-cart.md (v2 planned) | После клика на оплату без покупки | v2 |
| 8 | Announcement / transactional | 200-500 | templates/announcement.md (v2 planned) | Новый эфир / новый продукт / запись на вебинар | v2 |

**v1 (текущий релиз):** templates 1, 2, 3 - закрывают ~80% потребностей funnel'а автора (newsletter + launch sequences + cash events).
**v2+:** templates 4-8 + полная launch sequence campaign (10-email PLF kampania через Jeff Walker / Halbert 5-letter sequence).

## Knowledge base (references/)

Все references грузятся по нужде через progressive disclosure:

- `references/subject-formulas-50.md` - 50 формул заголовков (Welsh / Halbert / Sparkloop / Boron Letters / Mark Manson). RU + EN.
- `references/preheader-patterns.md` - синергия Subject↔Preheader. Anti-dup правило. 12 паттернов.
- `references/cta-patterns.md` - одна цель письма / micro vs hard CTA / above-fold + bottom для sales. Примеры RU + EN.
- `references/launch-sequence-frameworks.md` - Jeff Walker PLF / Halbert 5-letter / Welsh nurture→pitch / Halbert Boron Letters
- `references/spam-triggers-list.md` - CAPS / $ / «бесплатно» / !!! / spam-trigger words RU+EN (Mailtrap / SendGrid public lists)
- `references/mobile-preview-rules.md` - Subject ≤40 chars / Preheader 50-90 chars / above-fold правила / mobile-first render
- `references/kit-format.md` - Kit-specific (plain-text bias, broadcasts vs sequences, tags, deliverability)
- `references/beehiiv-format.md` - Beehiiv-specific (HTML blocks, segments, premium tier)
- `references/voice-bridge-to-tg.md` - bridge на `post` references (ivan-voice, _voice-TEMPLATE, archetypes-12)

## Examples

- `examples/_TEMPLATE.md` - RU эталонные письма автора (drafts → fill после первых 3-5 RU writeups)
- `examples/_TEMPLATE.md` - EN эталонные письма автора (drafts → fill после первых 3-5 EN writeups)
- `examples/track-record-email.md` - история применений + catch_rate metric

## Валидаторы

**Hard rules (regex, auto-fail в `workflow/04-review.md`):**

- Em-dash «-» внутри строк → fail
- «Нельзяграм» → auto-correct в «Нельзяграм» (RU only)
- Запретные термины из `config-lexicon.md` (artifact / digital-twin / fast-action / КЭВ / связки / Grand Slam Offer) → fail
- Восклицательных знаков >1 в Subject → fail
- Spam-trigger слова из `references/spam-triggers-list.md` → fail
- Subject > 50 chars → warning, > 60 chars → fail
- Preheader > 90 chars → fail
- Body длина outside floor+ceiling диапазона → fail

**EMAIL-G1-10 gates:**

- **EMAIL-G1** Subject ровно ОДИН, <50 chars, framework под тип письма (варианты списком = брак, правка автора; кандидаты сравниваются внутри, отброшенные - во Внутрянку)
- **EMAIL-G2** Preheader synergy - не дублирует Subject, расширяет/контрастирует
- **EMAIL-G3** CTA clarity - ровно 1 цель письма, CTA-link ≥1 раз (sales - ≥2: above-fold + bottom)
- **EMAIL-G4** Mobile preview - Subject обрезка ≤40 chars не убивает смысл
- **EMAIL-G5** Spam-trigger scan (regex)
- **EMAIL-G6** No-image-dependency - письмо читабельно с отключёнными картинками
- **EMAIL-G7** Length range - floor+ceiling по типу
- **EMAIL-G8** Sequence-consistency (только для launch sequence) - письмо согласовано с pre/post письмами

**6-Pass Refinement (LLM):**
Skeptic / Expert / Scroller (Inbox-scanner) / Competitor / Editor / Thumbnail (Preview-pane). Адаптировано из `post` под email-канал.

**Maxwell Ross 9-Item Checklist (адаптация под email):**

- Idea (одна большая идея в письме)
- Clarity (понятно с первого прочтения)
- Payoff (Subject обещание выполнено)
- Specificity (конкретика, не abstractions)
- Freshness (не клише inbox'а)
- Hook (Subject-hook + first line)
- Length (по диапазону типа)
- Tone (1:1 personal, не corporate)
- CTA (clear single goal)

**3 слоя финальный gate:**

- Слой 1 валидаторы (regex + EMAIL-G1-10)
- Слой 2 4 концепции (Pre-mortem / 90% calibration / Multi-perspective Marketer/Subscriber/Deliverability / Adaptive)
- Слой 3 7 контуров (Context / Соответствие предпосылкам / Целесообразность / Релевантность / Фактология / Реализуемость / Достоверность)

## Принципы

1. **Один email = одна цель.** Multi-CTA = split на серию. CTA-goal фиксируется в `workflow/01-finalize.md`.
2. **Subject = hook + open promise.** Body обязано выполнить обещание Subject. Иначе churn / unsubscribe.
3. **Preheader усиливает, не дублирует.** Если preheader = Subject парафраз - fail.
4. **Plain-text bias** (Kit) → no HTML-зависимый смысл. Beehiiv - opt-in через `config.esp: beehiiv`.
5. **Conversion > virality.** Email = funnel, не reach. CTR > likes.
6. **Voice over format** (наследовано из `post`) - стиль автора важнее структуры. Если шаблон ломает голос - голос побеждает.
7. **ОДИН Subject mandatory** - внутри рассмотреть кандидатов на разных hook frameworks (curiosity / direct-benefit / contrarian / numbered / personal-confession), в output отдать ровно один сильнейший (правка автора: «варианты никогда не выдавать»).
8. **Mobile-first preview.** Subject читабелен на 40 chars. Above-fold (первые 2-3 строки body) - самостоятельный мини-pitch.
9. **No spam triggers.** Hard fail regex.
10. **Sequence-aware** для launch. Каждое письмо знает свою позицию в карте sequence (`pre`, `position`, `post`).
11. **Карта воронки = source of truth** для Mode A. Не дополнять, не выдумывать. Пустая запись = fallback на Mode B2.
12. **Транскрипт в Mode C - цитата, не парафраз.** Лексика автора важнее «причёсанной» формулировки.
13. **Maxwell Ross 9 + EMAIL-G1-10 + 3 слоя - hard gate.** Никакой email не выходит без 9/9 + 8/8 + 3/3 PASS.
14. **Внутрянка после письма.** Каждый output включает блок «Как писал»: Mode / тип / hook framework / archetype / angle / CTA-goal / sequence-position / A/B логика / что отброшено.
15. **Каждая правка = системная.** Любая обратная связь от автора закрывается на ДВУХ уровнях: (1) точечный fix в текущем письме + (2) системная правка в скилле - config / workflow / review gate / memory / SKILL.md. Наследовано из `post`. См. [[feedback-each-correction-becomes-system-rule]].
16. **Mandatory reads перед draft.** В Pass 0 `workflow/03-write.md` обязательны Read'ы: gold-standard (по языку) / voice-bridge → ivan-voice / _voice-TEMPLATE / config. Без них Voice Fidelity Gate failit. Закрывает класс «skill написал generic email, потому что не загрузил голос».
17. **Bilingual через одну машину.** Если `config.language: both` или флаг `--both` - skill выдаёт обе версии. EN не дословный перевод, а культурно-адаптированный (Welsh / Halbert tone для EN; автора RU voice для RU). См. [[multi-language-localization]] + `references/voice-bridge-to-tg.md`.

## Portability - для ученика курса

Ученик клонирует папку `~/.claude/skills/email/` в свою машину и заменяет ТОЛЬКО:

1. **`config.md`** - пути, voice params, ESP под свой проект (onboarding делает за него при первом запуске).
2. **`examples/gold-standard-<your-name>-email-<lang>.md`** - свои лучшие письма (5-10 штук) по языку.
3. **`.business/`** - `avatar.md`, `jtbd.md`, `brand-dna.md`, `products/`, `запуски/<active>/` с картой воронки и launch sequence map.

Что НЕ трогаем:

- `workflow/*` - общая методология
- `references/*` - references (subject formulas, frameworks, spam triggers) одинаковы для всех
- `templates/*` - шаблоны 8 типов

Это делает skill **product курса**: ученики курса вайбмаркетинга получают тот же инструмент, который автор использует ежедневно.

## Anti-patterns

См. `config-lexicon.md` + `references/spam-triggers-list.md` + `references/voice-bridge-to-tg.md` → ivan-voice anti-patterns. Ключевые:

- Em-dash «-» внутри строк
- «Нельзяграм» вместо «Нельзяграм»
- Subject с CAPS LOCK словами
- Subject со «$» / «бесплатно» / «срочно» / «последний шанс» (хотя «last call» в окне продаж OK по контексту, см. spam-triggers-list)
- Subject длиннее 50 chars
- Preheader = парафраз Subject
- Multi-CTA в одном письме
- Корпоративный тон («Уважаемый подписчик»)
- Любые метафоры (глаголы в небуквальном значении - «ломает», «закрывает», «выстрелил»)
- Технический жаргон в публичной части
- Negативные статистики в публичном (типа «20% доходят»)
- DM-only ценообразование («цена в личке»)
- Травел-флекс / «Архитектор ИИ-систем» / «Дубайск»
- Списки/буллеты >1 в одном письме (кроме nurture-letter где допустимо до 2)
- >1 восклицательного знака в Subject


## Compliance (GDPR / CAN-SPAM / 152-ФЗ)

Email-marketing skill production-grade. Все письма проходят compliance check через EMAIL-G9 gate в `workflow/04-review.md` + auto-injection footer для custom ESP в `workflow/05-publish.md`.

См. `references/compliance.md` для полного reference (юрисдикции, mandatory elements, footer templates RU/EN, ESP-specific behavior).

**Mandatory elements (auto-handled для Kit/Beehiiv, инжектится для custom ESP):**

- Unsubscribe link в каждом письме
- Sender identification (ИП ФИО + ИНН для РФ / physical postal address для US)
- Commercial intent identification (для sales-letter)
- Гарантия возврата 14 дней (для sales-letter, ЗоЗПП ст. 25)
- No deceptive subject lines (уже EMAIL-G5)

**152-ФЗ specifics:**

- Согласие на обработку персональных данных получается на стадии opt-in (form/landing skill, не email skill)
- Suppression list соблюдается (Kit/Beehiiv auto)
- Право на удаление через ESP-side request handling

## Memory cross-refs

- `[[post]]` - voice/lexicon reuse через `references/voice-bridge-to-tg.md` (ivan-voice / _voice-TEMPLATE / archetypes-12)
- `[[multi-language-localization]]` - RU↔EN cultural adaptation rules
- `longform` - границу определяем: long-form-essay = standalone эссе для Newsletter platform / publication; email = ESP broadcast с Subject+Preheader+CTA конверсия-ориентированный
- `[[sales-council]]` - для sales-letter (Cialdini / Hormozi / Rackham / Voss / Klaff / Schwartz)
- `[[launch-marketing]]` - для launch sequence планирования (карта воронки → email-positions)
- `[[feedback-newsletter-platform-beehiiv-vs-kit]]` - автор выбрал Kit
- `[[feedback-ru-en-content-adaptation-rules]]` - дословно/переписывать
- `[[feedback-no-em-dash]]` - em-dash запрещён
- `[[feedback-no-tech-jargon-no-anglicisms]]`
- `[[feedback-no-negative-stats-in-public-offer]]`
- `[[feedback-product-positioning-no-programmer]]`
- `[[feedback-verbatim-quote-transfer]]` - дословный перенос цитат в Mode C

## Версия

**Текущая:** 1.0 (2026-05-28) - Initial release.

**Что включено в v1.0:**

- 3 mode (Plan / Spark B1+B2 / Transcript)
- 2 subject (автор / ученик с onboarding)
- 3 language (RU / EN / both)
- 3 template v1 (nurture / launch-sequence / sales-letter)
- 9 references (subject-formulas / preheader / cta / launch-frameworks / spam-triggers / mobile-preview / kit-format / beehiiv-format / voice-bridge)
- 8 EMAIL-gates + 6-Pass + Maxwell Ross 9 + 3 слоя
- Subject ровно ОДИН (правка автора)
- Plain-text bias (Kit default) / HTML opt-in (Beehiiv)

**Roadmap v2.x:**

- 5 templates 4-8 (weekly-digest / re-engagement / welcome / abandoned-cart / announcement)
- Co-creation lane для sales-letter + launch sequence (по аналогии с `post` v2.2 Architecture C Hybrid)
- Full PLF 10-email sequence campaign mode
- API integration с Kit / Beehiiv (broadcast push, sequence trigger)
- EN gold-standard корпус автора (после 3-5 EN writeups)

**SemVer правила:**

- MAJOR: breaking change в выходном формате или критериях fail
- MINOR: новый template / новый mode / новый reference файл / новая language
- PATCH: уточнение правил валидации, новые spam triggers, fix references

**Когда пересматривать:**

- catch_rate в track-record падает < 80%
- 3+ систематических промаха voice автора в email
- Новые ключевые findings от Welsh / Halbert / Sparkloop / Kit deliverability team (раз в квартал чек)
- Раз в 3 месяца минимум

## Связанные артефакты

- `config.md` - точка адаптации скилла под автора (см. внутри файла)
- `config-lexicon.md` - required / banned lexicon
- `~/.claude/skills/post/` v2.2 - общий voice источник (через voice-bridge reference)
- `~/.claude/skills/skill-craft/` v1.1 - методология build применена
- `.business/marketing/funnel.md` - карта воронки RU+EN (source of truth для Mode A)
- `.business/запуски/<active-launch>/launch-sequence.md` - карта launch sequence для конкретного запуска

## Empirical patterns layer (NEW 2026-05-28)

Этот skill интегрирован с shared empirical layer для всех content-skills.

**Mandatory Reads в Pass 0** (пути боевые, `~/IvanOS/...`; `~/.business` - симлинк на шаблон IvanOS, читать оттуда запрещено):
- `.business/growth/extracted-patterns/INTEGRATION.md` - что читать для этого скилла
- `.business/growth/extracted-patterns/hook-patterns-empirical.md` - 9 patterns из 30 corpus
- `.business/growth/extracted-patterns/voice-markers-empirical.md` - Greg/Riley/Sabrina + авторская calibration
- `.business/growth/extracted-patterns/audience-glossary.md` - agent-jargon → язык RU ЦА
- `.business/growth/extracted-patterns/funnel-awareness.md` - куда ведёт content
- `.business/voice-corpus/_format-canon-v2.md` - **канон формы v2** (иерархия источников §8.1). Читается в `03-write.md` Pass 0, применение проверяется уликой формы в `04-review.md`

**Benchmark Gate** в review stage:
- Compare output vs nearest 3 examples из `benchmark-corpus-index.md`
- Score /6 для text-only OR /7 для visual
- Cutoff: 4+/6 (text) | 5+/7 (visual) = PASS

Root cause fix: до 2026-05-28 references зашивали теорию виральности из памяти. Shared layer = empirical extraction из 30 real viral шортов в авторской нише.
