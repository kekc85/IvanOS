# Bug categories — coverage matrix per skill type

L4 Workflow Coverage обязан проверять что skill упоминает категории багов типичные для его типа. Если категория не упомянута и применима — это **gap в workflow**.

## Универсальные категории (для любого исполняемого skill)

| Категория | Описание | Триггерные слова в workflow |
|---|---|---|
| Empty/null input | Что если вход пустой / None | "empty input", "None", "пустой", "отсутствует" |
| Wrong type | Неправильный тип данных | "wrong type", "TypeError", "isinstance" |
| Out-of-bound | Превышение лимитов | "max", "overflow", "лимит", "превышен" |
| Encoding | Юникод, не-ASCII | "encoding", "utf-8", "unicode", "юникод" |
| Race conditions | Параллельные запросы | "race", "concurrent", "параллельн", "lock" |
| Idempotency | Повторный запуск даёт тот же результат | "idempotent", "repeat", "повторн" |

## Категории для TG-ботов / messaging-skills

| Категория | Описание | Обязательно для |
|---|---|---|
| **Permissions / bind mount** | docker volume → host user не может прочитать | aiogram + Local Bot API |
| **MIME-type discrimination** | video MIME / document video/* / image / audio — разные handler paths | любой bot принимающий media |
| **Rotation метаданные** | iPhone MOV: displaymatrix vs tags.rotate | video processing bot |
| **Subscription gate** | пользователь подписался/отписался mid-session | gated content bot |
| **Rate limits** | TG API 30 msg/sec, Local Bot API нет лимита | broadcast / massive messaging |
| **Long-running operation timeout** | Heroku 30s / TG callback 15s | render / processing bot |
| **State management (FSM)** | пользователь жмёт Cancel mid-flow / уходит / возвращается | wizard / multi-step flow |

## Категории для web-frontend skills

| Категория | Обязательно для |
|---|---|
| Loading state | любой fetch |
| Error state | API call |
| Empty state | список/каталог |
| Success state | submit form |
| Offline mode | PWA |
| Hydration mismatch | SSR + client |
| XSS protection | user input rendering |

## Категории для API-backend skills

| Категория | Обязательно для |
|---|---|
| Auth failure (401/403) | любой protected endpoint |
| Validation (400) | input from user |
| DB transaction rollback | multi-write |
| External API failure | integration |
| Rate limiting (429) | public API |
| CORS | public API |
| SQL injection | raw queries |

## Категории для CLI / ETL skills

| Категория | Обязательно для |
|---|---|
| Partial failure | 1 row of 1000 битый |
| Dry-run mode | destructive ops |
| Exit codes | scripting |
| Progress reporting | long-running |
| Resume after crash | long-running |

## Категории для content-skill / writing skills (NEW v1.2 — 2026-05-28)

Семейство content-skills у автора: `post` / `longform` / `email` / `bot-message` / `video` / `carousel` / `single-image` / `paips-post` / `spiky-one-liner`. Все производят текст/визуал в голосе автора через portable config + Mode × Subject архитектуру.

| Категория | Описание | Обязательно для |
|---|---|---|
| **Voice fidelity regression** | Новая версия модели меняет style, старый voice выходит generic | любой content-skill с voice reference |
| **Lexicon drift** | Lexicon автора эволюционирует (новые термины / устаревшие) — config.md устаревает | любой voice-bound skill |
| **Source data staleness** | Карта смыслов / brand DNA устарели / DEPRECATED — skill читает stale source | Mode A (Plan из Карты смыслов) |
| **Hook strength subjectivity** | Hook quality assessment — субъективная категория, нужны конкретные tests (conflict / clarity / cliff) | любой viral-format skill (Reels / Shorts / shorts content) |
| **Cross-skill config conflicts** | Изменение config в одном skill (например lexicon) не синхронизировано с sister skills | family of skills sharing voice rules |
| **Track-record bloat** | После 1000+ применений track-record становится огромным, freshness check замедляется | любой skill с catch_rate metric |
| **Mandatory Reads file missing** | Workflow ссылается на `examples/gold-standard-<name>.md` который не существует — Pass 0 fails silently | любой skill с Mandatory Reads pattern |
| **Description length out of Anthropic 80-500** | Frontmatter description >500 chars снижает trigger accuracy | любой skill (L1 deterministic check) |
| **Source-of-truth pointer to deprecated file** | config.paths.* указывает на DEPRECATED файл в .business/ | любой skill читающий business sources |
| **Banned terms в banlist context FALSE POSITIVE** | Regex matcher на banned terms (например «артефакт») hits в metadata списках запретов — нужен context-aware check | любой skill с lexicon_banned list |
| **Platform × format compatibility gate** | Tier/length conflict с платформой (например 30 min для Reels) — silent warning, не FAIL | tiered output skill (video tiers / longform 800-3000 wc) |
| **Generic AI listing artefact** | «10 хуков», «100 промптов» — generic AI промис, sophistication 4-5 sees through | любой viral / lead-magnet content skill |
| **Em-dash в metadata vs output** | Em-dash «—» в documentation skill (заголовки / разделители) vs em-dash в output контенте — разный treatment | любой skill с no-em-dash правилом |
| **Humaniser final pass missing** | text-skill не вызывает `~/.claude/skills/humaniser/prompt.md` в финальной фазе - output будет содержать 12 категорий AI-tics (triple-negation / voice-signature theft / ложная глубина / фальшивая близость / canon / etc) | любой text-content skill (post / tweet / longform / email / bot-message / single-image / carousel / pisatel-*) |

### Прецеденты (где найдена категория)

- **2026-05-28 audit video v1.0:** Mandatory Reads file missing (L4.1 critical) / Description 951 chars (L1.2 critical) / Source-of-truth DEPRECATED (L5.1 critical) / Platform×tier conflict not FAIL (L4.3 important) / Banned terms FALSE POSITIVE (L2.1)
- **2026-05-27 audit post v1.2:** Voice fidelity regression (Pass 0 Mandatory Reads pattern введён) / Hook strength subjectivity
- **2026-05-28 audit longform / email / bot-message / carousel / single-image / video:** Cross-skill config conflicts (9 skills семейство — каждый имеет _voice-TEMPLATE.md копию)

## Как использовать в L4 audit

```python
# Псевдо-код для L4 check
skill_type = detect_type(skill)  # tg-bot / frontend / backend / cli
required_categories = bug_categories[skill_type] + universal_categories
for cat in required_categories:
    if not category_mentioned(skill, cat):
        report_finding(
            level="L4",
            category=cat,
            severity="important",
            message=f"Skill is type={skill_type} but doesn't mention {cat}"
        )
```

## Категории для action skills (content-factory) — NEW v1.2

**Action skill** = output служит обещанием к non-reversible action подписчика / зрителя. Каждый факт = публичное обещание. Fact invention = потеря доверия / реальный вред.

Action skills в контент-фабрике автора: `bot-message` (push с callback), `email` (sales-letter / launch-sequence), `carousel` (анонс product/event), `longform` (newsletter promo / launch-essay).

Stylistic skills (НЕ требуют truth verification): `paips-post`, `spiky-one-liner`, `post` (long narrative), `post` (когда не launch-related), `single-image` (когда не launch-related).

| Категория | Описание | Pattern в workflow |
|---|---|---|
| **Gate A: Fact Verification** | Каждое число / дата / именованный факт в draft - match in business context ИЛИ flag UNVERIFIED | Pass перед draft: extract facts regex → verify against config.paths.business_index / products / avatar |
| **Gate B: Event Existence** | Mentions workshop / live / эфир / запуск - match в `.business/запуски/<active>/` или config.upcoming_events ИЛИ require user confirm | Pass перед draft: detect event regex → verify against active launch dir + transcript if Mode C |
| **Gate C: PII Pre-Read Sanitize** | Apply config.privacy.pii_patterns к каждому файлу контекста ПЕРЕД использованием для draft | Pass перед mandatory reads: regex sub на content of each file |
| **Gate D: CTA Verb+Object Pair** | Кнопка / Subject / Headline = `<verb> <object>` pair (regex `^\S+\s+\S+`) ИЛИ whitelist одиночных | Pass review: regex check + whitelist match |
| **Gate E: Self-Review Cross-Check** | Перед output «3 слоя пройдено» - fact-list с verification source для каждого utterance | Pass review final: produce fact-list before approval |

### Detection of artifact_type=action в L4 audit

```python
skill_metadata = parse_frontmatter(skill_path/SKILL.md)
artifact_type = skill_metadata.get("artifact_type", "unknown")

if artifact_type == "action":
    for gate in ["A", "B", "C", "D", "E"]:
        if not gate_implemented(skill, gate):
            report_finding(
                level="L4",
                category=f"Action-skill Gate {gate}",
                severity="critical",
                message=f"action skill missing Gate {gate}"
            )
elif artifact_type == "unknown":
    report_finding(
        level="L7",
        category="metadata.artifact_type missing",
        severity="important",
        message="declare artifact_type for build-time gate detection"
    )
```

### Прецедент

- **2026-05-28: bot-message v1.0.1 → v1.0.2.** E2E test показал catch_rate halftura 100% при real 33%. 3 из 3 push содержали fact invention (workshop / 12 месяцев / 14 эпизодов / 5000 base) + PII leak ($280K). Audit v1.0.1 не покрыл этот class - artifact_type axis отсутствовал в skill-craft v1.1. Root cause: skill-craft не различал action vs stylistic ментальные модели.

## Категории для visual-first skills (NEW v1.3 — 2026-05-28)

**Visual-first skill** = output = визуальный артефакт (PNG / PDF / video frame / image composition). Качество судится глазами, не deterministic checks. Pattern наследование от text-content skill = категориальная ошибка.

Visual-first skills в фабрике автора: `carousel` (multi-slide deck), `single-image` (1 кадр), `video` (production handoff с visual brief), `produce-reel` (video), `motion-storyboard` (motion sequences), `hyperframes` compositions.

Stylistic / text-only skills (НЕ visual-first): `post`, `tweet`, `email`, `bot-message`, `longform`, `paips-post`.

| Категория | Описание | Pattern в workflow |
|---|---|---|
| **VG-A: Visual Reference Capture** | Если user даёт reference images (screenshots конкурентов / brand examples) - сохранить как файлы в `skill/visual-anchors/` или `references/visual-anchors/`. Не текстовое описание - реальные image files. | Pre-build Step -4: download / save all reference images user provided + любые URLs WebFetched в anchors folder |
| **VG-B: Visual Reference Read перед Render** | Перед designing template / rendering - ОБЯЗАТЕЛЬНО Read anchors folder. Не «я помню как выглядит», а actual visual ground truth. | Workflow design / render stage Pass 0: list anchors folder + open key references |
| **VG-C: Visual Decomposition в Research** | Research для visual skills включает per-reference visual decomposition: измерь image-to-text ratio, identify hero element % площади, layout zones, typography role. Не только описания. | Pre-build Step 0 research per reference: visual decomposition matrix (hero %, typo %, real elements list, palette, mood) |
| **VG-D: Pattern Inheritance Check** | Нельзя слепо копировать pattern от другого skill. Категориальная проверка: text-content pattern для visual-first = brak. | Pre-build Step 0.7: explicit check «inheriting pattern from skill X — is X same artifact_type? Same platform native format?» — FAIL если text→visual или LinkedIn→IG |
| **VG-E: Visual Quality Gate (L8)** | После render - side-by-side comparison output vs visual-anchors. LLM judge «same category Y/N» strict. Если N - FAIL, rebuild. Не declare done без visual confirmation. | L8 audit (см. methodology.md L8) — required для artifact_type=visual |
| **VG-F: Hero Element Required** | Visual-first slides / images требуют hero element (real photo / screenshot / scene) занимающий ≥40-50% area. Pure typography = только если family=document-format (LinkedIn PDF). | Template gate: regex check HTML template для image/screenshot placeholder с min-height 40-50% canvas |
| **VG-G: Asset Pipeline для Hero Images** | Без assets templates пустые. Source pipeline должен быть defined: brand library / AI generation / ui-record / manual. | config.md: assets_pipeline section с paths + strategies per asset_type |

### Прецедент

- **2026-05-28: carousel v1.0 + v1.1 disaster.** Создал skill через research-based agents (только текстовые описания). Template = pure typography (Welsh LinkedIn pattern скопирован для IG mobile). Render slide-01.png = generic agency template 2018, в категории «хуже GPT default». автор diagnoz: «лютое говно». Root cause: 5 одновременных ошибок — research = text only (VG-C), references user-provided не сохранены (VG-A), pattern скопирован от text-content post/single-image (VG-D), templates без hero element (VG-F), no visual quality gate (VG-E). 9 «PASS» gates в audit были все deterministic (em-dash / banned terms / count) — visual quality не проверено вообще.

### Detection of artifact_type=visual в L4 audit

```python
skill_metadata = parse_frontmatter(skill_path/SKILL.md)
artifact_type = skill_metadata.get("artifact_type", "unknown")

if artifact_type == "visual" or artifact_type == "mixed":
    for gate in ["VG-A", "VG-B", "VG-C", "VG-D", "VG-E", "VG-F", "VG-G"]:
        if not gate_implemented(skill, gate):
            report_finding(
                level="L4",
                category=f"Visual-first Gate {gate}",
                severity="critical",
                message=f"visual skill missing {gate}"
            )
```

## Pattern inheritance bug (universal anti-pattern) — NEW v1.3

| Категория | Описание |
|---|---|
| **PIB-1: Cross-type pattern copy** | Pattern от skill A скопирован для skill B без проверки что A и B одного artifact_type. Frequent: text-content → visual-first, stylistic → action, single-language → bilingual. |

**Mitigation:** при build skill explicit declare «inheriting pattern from <X>» + проверить axis match (artifact_type / platform / language). Если mismatch — pattern частично применим, нужны targeted overrides.

**Прецедент:** carousel v1.0 inherited от post (text-content) — категориальная ошибка, привела к pure typography templates для IG mobile.

## Когда добавлять новую категорию

- При появлении нового prod-инцидента который не покрывался ни одной существующей категорией
- Каждая категория должна быть зафиксирована **прецедентом** (real bug, дата, ссылка на разбор)
- Не плодить «теоретические» категории — только опытно подтверждённые

## История категорий

- 2026-05-22: создан файл. Стартовый набор после прецедента «Полин-bug v2 жил 9 часов» из-за непокрытой категории `Permissions / bind mount`.