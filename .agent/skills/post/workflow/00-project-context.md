# Workflow 00 — Project Context Resolution (репликуемость)

**Назначение:** развязать скилл-движок от конкретного проекта. Движок общий; данные проекта (голос, JTBD, контент-источник, лексикон, модель контента) живут СНАРУЖИ в проектном пакете. Этот файл резолвит активный проект и связывает переменные `{active.*}`, которыми пользуются все остальные стадии.
**Когда:** первым делом в `01-router.md` Шаг 0 (до всего остального).
**Выход:** объект `active` (project context), проброшенный во все стадии.

---

## Принцип репликуемости

> Скилл выдаётся ученикам. Ученик НЕ трогает код (`workflow/*`, generic `references/*`, `templates/*`). Он подключает свой **проектный пакет** флагом `--project <name>`. Хардкод на автора запрещён — везде `{active.*}`.

Что входит в скилл-ядро (общее, не трогать): `workflow/*`, methodology-references (maxwell-ross / archetypes / ai-tells / hooks / atomic-essay / value-types / hook-story-offer), `templates/*`.

Что входит в проектный пакет (СНАРУЖИ скилла, у каждого проекта свой): voice-canon · gold-standard · jtbd-value-map · content-source · lexicon/stop-list · post-config.

---

## Шаг 1 — Определить активный проект

**Priority 1 — флаг:** `--project <name>` в input → активный проект = `<name>`.
**Priority 2 — дефолт:** нет флага → `active_project = "ivan"` (backward compat — автор-инстанс вайбкодинга работает как раньше).

## Шаг 2 — Загрузить проектный конфиг

Найти запись проекта в реестре `config.md` → `projects:`. Взять `pack` (путь к post-config проекта) и прочитать его.

- `active_project = "ivan"` → источник = корневой `config.md` (текущие поля автора; ничего не переезжает).
- `active_project = "<other>"` → прочитать `<pack>/post-config.md`.

Если проект не найден в реестре → fail с подсказкой: «Проект <name> не зарегистрирован в config.md → projects. Доступные: <list>».

## Шаг 3 — Связать переменные `active`

Из конфига активного проекта связать (с дефолтами автора, если поле отсутствует):

```yaml
active:
  project: "ivan" | "<name>"
  subject: <subject блок>
  # ГОЛОС (заменяет хардкод ivan-voice / _TEMPLATE / _voice-TEMPLATE)
  voice.canon:          # дефолт ivan: references/_voice-TEMPLATE.md
  voice.gold_standard:  # дефолт ivan: examples/_TEMPLATE.md
  voice.living_language:# дефолт ivan: references/_voice-TEMPLATE.md
  voice.lexicon:        # дефолт ivan: config-lexicon-ru.md
  voice.stop_list:      # дефолт ivan: лексикон/banned в config-lexicon-ru.md
  # КАРТА РАБОТ (заменяет хардкод вайбкодинг genre-value-jtbd-mapping)
  jtbd_value_map:       # дефолт ivan: references/genre-value-jtbd-mapping.md
  # КОНТЕНТ-ИСТОЧНИК (заменяет хардкод Карты смыслов 5.2)
  content_source:       # дефолт ivan: config.paths.content_map
  content_source_format:# calendar | thematic | hybrid
  # МОДЕЛЬ
  content_model: "launch" | "evergreen"   # дефолт ivan: launch
  cta_policy:           # дефолт ivan: soft в финале; для health: none-skill-writes
  launch_module: true|false                 # дефолт ivan: true; health: false
  combo: <platform combo блок>
```

## Шаг 4 — Контракт для downstream-стадий (HARD)

Все стадии ниже ОБЯЗАНЫ использовать `{active.*}` вместо литеральных авторских-путей:

| Стадия | Было (хардкод) | Стало |
|---|---|---|
| `knowledge/workflow-overview.md` mandatory reads (чтение канона голоса - `02f-polish.md` Шаг 2) | _voice-TEMPLATE.md / _TEMPLATE.md / _voice-TEMPLATE.md | `{active.voice.canon}` / `{active.voice.gold_standard}` / `{active.voice.living_language}` |
| `04-review.md` Voice Fidelity Gate 4.6 | сверка с ivan-voice | сверка с `{active.voice.canon}` + `{active.voice.gold_standard}` |
| `02b-research-summary.md` | Карта смыслов 5.2 / gold-standard автора | `{active.content_source}` (формат `{active.content_source_format}`) / `{active.voice.gold_standard}` |
| `02c-tuple-choice.md` | вайбкодинг JTBD из genre-value-jtbd-mapping | `{active.jtbd_value_map}` |
| `02e-value-injection.md` | вайбкодинг кейсы | proof из `{active.jtbd_value_map}` / `{active.content_source}` |
| `05-publish.md` CTA | soft CTA автора | по `{active.cta_policy}` (если `none-skill-writes` — скилл НЕ пишет ссылку/CTA) |

`content_model=evergreen` → отключить запусковую логику: без прогрева/дедлайнов/клиффхэнгеров, каждый пост самостоятелен (тема закрыта), genre `sales-launch` недоступен.

## Шаг 5 — Метафоры проекта

Общий движок банит небуквальные метафоры (`04-review` 4.1.7). Если `{active.voice.canon}` явно РАЗРЕШАЕТ список метафор (как у health: «охранник, забывший выключиться» и т.п.) — этот список перекрывает общий бан для данного проекта.

---

## Шаг 6 — Структурная ротация (анти-шаблон, когда нет истории канала)

Если у проекта нет `recent_posts` (напр. `channel_url: null`) — archetype-rotation скилла не ловит повтор. Тогда ОБЯЗАТЕЛЬНО прочитать `<project-pack>/structure-rotation.md` (если есть): банк скелетов + лог использованных. Новый пост — скелетом, НЕ совпадающим с последними 2-3 в логе. Варьировать финал и приписку. После выдачи — дописать строку в лог. Прецедент по решению автора: два поста подряд вышли на одном скелете (протокол-список) и читались как шаблон.

**Передать `active` в:** `01-router.md` (продолжение Шага 0) → все downstream-стадии.