---
name: post-workflow-overview
version: "2.0"
created: 2026-05-28
last_reviewed: 2026-08-07
description: Workflow карта skill post - единый конвейер (Lane убран с v4.2), phase route v2.0 (03-dry НОВАЯ), Mandatory Reads per combo (внешний канон голоса по config.voice_canon), file dependencies. Вынесено из SKILL.md для соблюдения skill-anatomy ≤250 строк рекомендации.
---

# post - Workflow Overview

> Вынесено из SKILL.md (skill-anatomy.md рекомендация: SKILL.md ≤250 строк, выносить detail в knowledge/).
> **v2.0 (по решению автора):** ветвления ПО LANE больше нет (fast/co-creation убран с v4.2, здесь диаграмма приведена в соответствие - до v2.0 файл продолжал описывать несуществующую параллельную fast-lane через `02-structure.md`/`03-write.md`, которые физически не маршрутизируются с v4.2, R1 дефект 3). Новая фаза `03-dry.md` (осушение по Ильяхову + lint) вшита между `02f-polish` и `04-review`.
> **Уточнение по решению автора (дефект Д42 скептик-раунда 9):** формулировка «путь ОДИН для любого поста» была неверной с момента появления развилки маршрутов. Отмена lane и единственность маршрута - разные утверждения: lane действительно один, а маршрутов ТРИ (`full` / `packet` / `short-event`, развилка `01-router.md` Шаг 0.7-Р). Раздел «Три маршрута» ниже.

## Workflow (progressive disclosure, v2.0 единый конвейер)

При вызове skill router определяет platform/language/combo, дальше ветвления ПО LANE нет. Маршрут прогона при этом выбирается: `01-router.md` Шаг 0.7-Р разводит на `full` / `packet` / `short-event` (раздел «Три маршрута» ниже). Диаграмма ниже - маршрут `full`.

```
[первый запуск ученика?] → 00-onboarding-student.md → создаёт config.md

/post → 01-router.md
          │
          ├─ Шаг 0: Read config + platforms[] array + config.voice_canon (AC8)
          ├─ Шаг 0.4: Platform Selection (flags / phrases / plan-metadata / default)
          ├─ Шаг 0.45: Language Selection (flags / platform-derive / input-detect / default)
          ├─ Шаг 0.47: Combo Resolution + Status Check (load brief.combo)
          ├─ Шаг 0.49: form_goal / form_class / form_profile + ЦЕЛЬ длины (канон формы §2.1) - НЕ HARD-FAIL, WARN
          ├─ Шаг 0.55: banned list refresh check
          └─ Шаги 1-3: Mode detection
                │
                ├─ 01a-plan.md      ← Mode A: из Карты смыслов
                ├─ 01b-spark.md     ← Mode B1/B2: ситуативный
                ├─ 01c-transcript.md ← Mode C: из надиктовки (+ PII safety note)
                └─ 01d-rewrite.md   ← Mode D: улучшить готовый пост
                       ↓
                01-finalize.md       ← archetype + hook + length (общая часть)
                       ↓
                02b-research-summary.md  ← ФАКТ-БАЗА в отдельный файл (AC5, входной гейт ДО письма:
                                            объём факт-базы ≥ объём поста, каждое число/имя - с источником)
                       ↓
                02c-tuple-choice.md      ← 3 tuple (genre × value × JTBD) → автор выбирает
                       ↓
                02d-components-options.md ← по каждому HSO-компоненту 2-3 options
                       ↓
                02e-value-injection.md   ← value-types framework + JTBD-pinning
                       ↓
                02f-polish.md            ← финальная сборка draft.final
                       ↓
                03-dry.md (НОВАЯ, v2.0)  ← Ильяхов-осушение: было→стало + lint (вода/обороты/
                                            анти-паттерны/факт-чек), давление на длину ВНИЗ, не HARD-блок
                       ↓
                04-review.md         ← полный реестр вердикта (верификатор + mastery + humaniser
                                        включены), 6-Pass + Maxwell Ross 9 + 3 слоя + platform gates
                                        + AC4 гейт checklist_ivana (B1/B3, прикладная ценность)
                       ↓
                05-publish.md
```

`02-structure.md` и `03-write.md` (Ильяхов/мастера/Power Idea жили здесь, физически не маршрутизировались с v4.2) → `workflow/_archive/`. Их живое содержимое переехало в `03-dry.md` и `04-review.md` (зона Z2).

## Три маршрута (развилка `01-router.md` Шаг 0.7-Р)

Маршрут выбирается ОДИН раз, порядок проверки строгий, первый сработавший побеждает: `short-event` → `packet` → `full`. Дефолт при неоднозначности - `full`. Выбор печатается строкой `маршрут: <full|packet|short-event> причина=<признак> единиц=<N> пакет=<packet_id или ->` и пишется в `brief.route`.

| маршрут | когда | что меняется против `full` |
|---|---|---|
| `full` | одиночный пост, новая форма, первый пост класса/платформы | ничего, это и есть полный конвейер диаграммы выше |
| `packet` | пакет дня: **≥3 единицы за один прогон** на одну дату (ячейки одного дня карты смыслов, серия информеров, дуга запуска) | короче ЧТЕНИЕ, не гейты: канон формы, канон голоса, справочники приёмов и файлы фаз читаются ОДИН РАЗ на пакет в `packet_state.reads`, единица ссылается значением `packet:<packet_id>`. Набор гейтов, факт-база и осушение остаются per-unit и совпадают с `full` (`01-router.md` Шаг 0.7-П) |
| `short-event` | `form_class = event`: анонс события, звено каскада доходимости, финальный пуш | 3 фазы E1-E3 вместо полной цепочки сборки (`01-router.md` раздел 0.49-К). Часть полных гейтов не прогоняется и пишется в вердикт как `N/A (короткий маршрут event)` - поимённый список закреплён в 0.49-К (`4.0.5`, `4.B`, `4.2`, `4.3`, `4.9`, `4.11`, `4.13`, `4.TG-E`) |

> Смысловые гейты маршрутом не ослабляются: быстрый путь (тот, где часть гейтов просто не прогонялась) устранён дефектом Д11. Молчаливый PASS по непрогнанному гейту = подделка вердикта.

## Workflow файлы

| Файл | Назначение | v2.0 статус |
|---|---|---|
| `workflow/00-project-context.md` | Резолвер активного проекта (`--project <name>`, дефолт `ivan`) → переменные `{active.*}`. Читается ПЕРВЫМ, `01-router.md` Шаг 0 | активен |
| `workflow/00-onboarding-student.md` | First run для ученика. Создаёт config.md через 9 вопросов | активен |
| `workflow/01-router.md` | Auto-detect platform / language / combo / mode / form_goal | активен |
| `workflow/01a-plan.md` | Mode A: читает Карту смыслов по дате | активен |
| `workflow/01b-spark.md` | Mode B1: расширение идеи / Mode B2: генерация под JTBD | активен |
| `workflow/01c-transcript.md` | Mode C: разбор надиктовки в атомарные смыслы | активен |
| `workflow/01d-rewrite.md` | Mode D: улучшить готовый пост | активен |
| `workflow/01-finalize.md` | Общая доводка brief: archetype/hook/length | активен |
| `workflow/02b-research-summary.md` | Факт-база (источники файл:строка) - входной гейт AC5 | активен |
| `workflow/02c-tuple-choice.md` | 3 tuple (genre × value × JTBD) → автор выбирает | активен |
| `workflow/02d-components-options.md` | По каждому HSO компоненту 2-3 options | активен |
| `workflow/02e-value-injection.md` | Value-types framework + JTBD-pinning | активен |
| `workflow/02f-polish.md` | Финальная сборка draft.final перед осушением | активен |
| `workflow/03-dry.md` | **НОВЫЙ v2.0.** Ильяхов-пасс (было→стало) + lint v2 (вода/обороты/анти-паттерны/факт-чек) | активен |
| `workflow/03b-spectrum-ab.md` | **Опционально.** A/B-варианты: два архитектурно разных поста на один angle (spectrum-then-choice по 4 частям). Запускается между `02f` и `03-dry` и только при `config.output.ab_variants ≥ 2`, иначе стадия пропускается молча (`01-router.md`, таблица фаз) | активен (опциональный) |
| `workflow/04-review.md` | Полный реестр вердикта + 6-Pass + Maxwell Ross 9 + 3 слоя + platform gates + AC4 | активен |
| `workflow/05-publish.md` | Output + A/B + STEPPS + self-check | активен |
| `workflow/06-banned-refresh.md` | Refresh banned list (triggered by --refresh-banned) | утилита |
| `workflow/02-structure.md`, `workflow/03-write.md` | Detect-type + HSO + headline / draft + voice injection | → `_archive/` (не маршрутизируются с v4.2, живое содержимое перенесено в 03-dry/04-review) |

## Override flags

- **Mode:** `--plan` / `--spark` / `--transcript` / (Mode D auto-detect по входу «вот мой пост, докрути»)
- **Platform:** `--telegram` / `--tg` / `--linkedin` / `--li`
- **Language:** `--ru` / `--en`
- **Utility:** `--refresh-banned`

## Combo Resolution table (Шаг 0.47)

| combo_key | Status | Голос (source of truth v2.0) | Platform gates |
|---|---|---|---|
| telegram-ru | ✅ production | внешний канон по `config.voice_canon` (AC8); не подключён - гейты голоса печатают `UNVERIFIED`, не `PASS` (Д9) | 4.TG-H/4.TG-E hook strength + standard stack |
| linkedin-en | ✅ v3.0 validated | EN-канон по `config.voice_canon` (ключи EN-комбинации); `references/_voice-TEMPLATE.md` - пустой шаблон, не подключён - `UNVERIFIED`, не `PASS` (Д9) | 4.LI.1-4.LI.8 (hook spacing / no markdown / hashtag / emoji / no comment-WORD / no US-jargon / AI-tells EN-22) |
| linkedin-ru | 🚧 placeholder | TBD (10+ RU LinkedIn постов автора required) | 4.LI structural + RU lexicon |
| telegram-en | 🚧 placeholder | TBD (EN TG audience required) | 4.TG hook + EN lexicon |

## Mandatory Reads (per combo) - v2.0

> **AC8/AC10:** ядро голоса читается ИЗВНЕ по ключам `config.voice_canon` (config.md), а не из внутрискилловых заглушек. Внутрискилловые `references/ivan-*.md`/`_TEMPLATE.md` (устаревшие дубли мая) - в `_archive/`, НЕ читаются. Голос грузится частично (секционно/по form_class), не целиком, чтобы не раздувать контекст: ≤35КБ голосового материала за прогон (AC8 бюджет).

**Для combo=telegram-ru (HARD, без них Voice Fidelity Gate + Blueprint Gate fail):**
1. `{config.voice_canon.voice_gold_standard}` - секционно (не целиком, 58КБ файл)
2. `{config.voice_canon.voice_profile}` - целиком (~25КБ)
3. `{config.voice_canon.voice_corpus_dir}` - 3-5 эталонов, отбор по `form_class` брифа
4. `{config.voice_canon.checklist_ivana}` - HARD read + гейт AC4 (B1/B3 прикладная ценность, `04-review.md`)
5. `references/_voice-TEMPLATE.md` - ПУСТОЙ ШАБЛОН под заполнение учеником, предметом mandatory read не является и `PASS` по нему запрещён: ключи `config.voice_canon` пусты или файл не проходит `[-f <путь>]` → гейты голоса печатают `UNVERIFIED` со строкой «канон … не подключён (config.voice_canon.<ключ>)» (портативность AC12; формулировка-канон - `config.md` Д9, по решению автора)
6. `config.md` (весь файл активной комбинации)
7. `references/donor-copy-devices.md` - **HARD Read целиком**, четыре точки маршрута: `02d-components-options.md` Шаг 0.6 (full/packet) · `01d-rewrite.md` Шаг 2.5 (rewrite) · фаза E1 (short-event) · `04-review.md` 4.M.2 (Read целиком + вложение в промпт верификатора, на ВСЕХ маршрутах, добавлено Р13 по решению автора). Ключ `mandatory_reads.donor_devices` со значением вне пары `true` | `packet:<packet_id>` = HARD FAIL в `04-review.md` 4.0.2, а строка верификатора `donor-devices: нет` = FAIL и возврат на доработку (по решению автора)

**Для combo=linkedin-en:**
1. EN-канон голоса по ключам `config.voice_canon` (`references/_voice-TEMPLATE.md` в них стоит плейсхолдером и остаётся пустым шаблоном: заполнил ученик - читается как канон, пуст - гейты голоса печатают `UNVERIFIED`, не `PASS`, см. `config.md` Д9; в списке стоял дважды - дубль снят, волна 7 по решению автора)
2. `config-lexicon-en.md`
3. `config.md`
4. `references/donor-copy-devices.md` - **HARD Read целиком**, те же четыре точки и тот же гейт `mandatory_reads.donor_devices`, что у telegram-ru: справочник приёмов от комбинации не зависит

**Для факт-базы (AC5, все combo, читается 02b ДО письма):**
- Файл факт-базы поста (создаётся в `02b-research-summary.md`), проверяется `lint-post.py --factbase <file>` перед 03-dry: объём факт-базы ≥ объём поста в знаках; каждое число из поста присутствует в факт-базе; каждое имя собственное из поста присутствует в факт-базе. Провал = HARD FAIL «выдуманный факт».

Pass 0.5 mandatory tuple selection (genre × value × JTBD) - для всех combo:
- `references/genre-value-jtbd-mapping.md`
- `references/value-types-framework.md`

## Журналы (пишутся конвейером, читаются на входе следующего поста)

- `.skeleton-log.jsonl` - форма скелета блоков за 7 дней канала (анти-шаблонность, checklist C11)
- `.used-anchors.jsonl` (NEW v2.0) - якорь-история + скилл-герой + форма заголовка + канал + дата; lint проверяет дубль якоря/героя кросс-канально за 7 дней
