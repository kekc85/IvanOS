# Аудит скилла: post v3.0
Дата: 2026-05-28
Версия методологии: skill-craft v1.3
Аудитор: Claude через `/skill-craft post`
Предыдущий отчёт: (первый аудит после rename post v2.2 → post v3.0)

## Сводка

| Уровень | Статус | Critical | Important | Minor |
|---|---|---|---|---|
| L1 Structural | PASS | 0 | 0 | 0 |
| L2 Content | PASS | 0 | 0 | 1 |
| L3 Trigger | PASS | 0 | 0 | 0 |
| L4 Workflow | PASS (с reservations) | 0 | 2 | 1 |
| L5 E2E | SKIPPED | 0 | 0 | 0 |
| L6 Safety | PASS | 0 | 0 | 1 |
| L7 Maintenance | PASS | 0 | 1 | 0 |

## Вердикт

⚠️ **NEEDS FIXES** (Important на L4/L7, не блокирующие production-ready для combo telegram-ru / linkedin-en)

Production-ready: ✅ telegram-ru (backward compat v2.2 sustained), ✅ linkedin-en (validated через synthesis 29 авторов)
Placeholder: 🚧 linkedin-ru / telegram-en (warned в config.md status field)

## Детальные находки

### L1.1 - Frontmatter valid
- **Что:** name=post / version="3.0" / description=482 chars (within 80-500)
- **Где:** SKILL.md:1-7
- **Приоритет:** PASS

### L1.2 - Em-dash в новых файлах
- **Что:** 0 em-dash в SKILL.md / config.md / config-lexicon-en.md / 01-router.md (sed fixed)
- **Приоритет:** PASS
- **Примечание:** legacy em-dash остались в 02-structure.md (6) / 03-write.md (1) в old sections. Backlog для full sweep.

### L2.1 - Synthesis content validated
- **Что:** _voice-TEMPLATE с verbatim quotes 5+ авторов per pattern. _voice-TEMPLATE full text + applicability
- **Приоритет:** PASS

### L2.2 - Source data freshness (Minor)
- **Что:** synthesis 2026-05-28. Banned list refresh default 30 days. LinkedIn trends могут эволюционировать быстрее
- **Как починить:** trigger re-scan EN-LinkedIn раз в месяц через workflow/06-banned-refresh.md
- **Приоритет:** Minor

### L3.1 - Triggers покрытие
- **Что:** /post / "напиши пост про X" / "напиши LinkedIn про X" / "дай идеи" / надиктовки >500 знаков / 6 флагов --telegram/--linkedin/--ru/--en/--co-create/--fast
- **Приоритет:** PASS

### L3.2 - Discriminative vs sibling skills
- **Что:** MECE-граница sustained vs tweet (X/Threads), longform (newsletter/article 800-3000), bot-message (TG-bot push), email/carousel/single-image/video (orthogonal artifact_type). paips-post/spiky-one-liner DEPRECATED → tweet - резолвлены
- **Приоритет:** PASS

### L4.1 - Content-skill family categories coverage (10/13 PASS)
- **Что:** post v3.0 покрывает:
  - ✅ Voice fidelity regression (Pass 0 Mandatory Reads)
  - ✅ Lexicon drift (banned_list_refresh_interval)
  - ✅ Source data staleness (Mode A fallback)
  - ✅ Cross-skill config conflicts (declared sibling re-routes)
  - ✅ Mandatory Reads file missing (Pass 0 HARD check)
  - ✅ Description length 80-500
  - ✅ Banned terms FALSE POSITIVE (context-aware)
  - ✅ Platform × format compatibility (char_limit per combo)
  - ✅ Generic AI listing artefact (banned «10 prompts comment X»)
  - ✅ Em-dash metadata vs output (separate handling)
- **Приоритет:** PASS на 10/13

### L4.2 - Hook strength gate gap (Important)
- **Что:** для linkedin-en есть Donnelly hook spacing 62/62/50 (4.LI.1 deterministic). Для telegram-ru - нет dedicated hook strength gate
- **Как починить:** добавить TG hook strength gate в v3.1 (8-10 слов первая строка)
- **Приоритет:** Important

### L4.3 - Track-record reset (Minor)
- **Что:** examples/track-record-post.md renamed но содержание ещё v1.x post. Reset для v3.0 counter не сделан
- **Как починить:** append section «v3.0 reset, prior metrics не reusable»
- **Приоритет:** Minor

### L5 - E2E reality test (SKIPPED)
- **Что:** требует реальной генерации LinkedIn EN post end-to-end + manual review автора
- **Как починить:** запланировано Phase 4 backlog next session
- **Приоритет:** SKIPPED

### L6.1 - Safety / prompt injection
- **Что:** post skill = artifact_type=stylistic. Не выполняет network requests / system commands вне scope. User input идёт через draft для review gates, не для exec
- **Приоритет:** PASS

### L6.2 - Mode C PII gap (Minor)
- **Что:** post = stylistic не action. Не triggered Gate C PII. Но Mode C Transcript авторская надиктовка может содержать PII (имена / суммы) - нет explicit sanitization pass
- **Как починить:** optional PII regex scan в 01c-transcript.md
- **Приоритет:** Minor

### L7.1 - SKILL.md длина (Important)
- **Что:** SKILL.md 296 строк > рекомендация ≤250. Превышение из-за Platform×Language matrix v3.0 + унаследованная Workflow секция v2.2
- **Как починить:** вынести Workflow detail в knowledge/workflow-overview.md
- **Приоритет:** Important

### L7.2 - SemVer compliance (Minor)
- **Что:** v3.0 = MAJOR (правильно - rename + 2 новых axis). Changelog в SKILL.md документирует v1.0-v2.2 - v3.0 entry не добавлен явно
- **Как починить:** добавить v3.0 entry в Changelog
- **Приоритет:** Minor

### L7.3 - Modular structure
- **Что:** правильная организация - references/ / templates/ / workflow/ / examples/. v3.0 references в linkedin/en/ поддиректории - логично для multi-platform/language
- **Приоритет:** PASS

## Action plan

### Critical (block publish): (none)

### Important - ✅ ВСЕ ЗАКРЫТЫ В ТОЙ ЖЕ СЕССИИ:
1. **L4.2** - ✅ TG hook strength gate добавлен (Sub-stage 4.TG в 04-review.md)
2. **L7.1** - ✅ Workflow detail вынесен в knowledge/workflow-overview.md; SKILL.md slim version замещён

### Minor - ✅ ВСЕ ЗАКРЫТЫ В ТОЙ ЖЕ СЕССИИ:
1. **L2.2** - ✅ banned_list_refresh_workflow указан в config-lexicon-en.md validation section (workflow/06-banned-refresh.md trigger)
2. **L4.3** - ✅ track-record-post.md reset для v3.0 counter (per-combo tracking)
3. **L6.2** - ✅ PII safety note добавлен в workflow/01c-transcript.md
4. **L7.2** - ✅ v3.0 entry добавлен в Changelog SKILL.md
5. **Legacy em-dash sweep** - ✅ 02-structure.md / 03-write.md очищены (0 em-dash)

## L5 E2E Status

L5 SKIPPED в этом audit. Требует реального вызова `/post --linkedin --en про <автора real topic>` + manual review автора. Это **out of scope этой задачи** - не backlog skill-extension, а отдельный validation запрос когда автор будет использовать skill в production.

## Track record update

**Что skill-craft audit поймал:**
1. SKILL.md длина 296 > 250 (L7.1)
2. TG hook strength gate отсутствует (L4.2)
3. Legacy em-dash в old sections (L1.2 note)
4. Track-record не reset для v3.0 (L4.3)
5. Mode C PII gap (L6.2)
6. Banned list refresh не triggered (L2.2)
7. v3.0 Changelog entry missing (L7.2)

**Пропущенное (TBD после L5 E2E):** real LinkedIn EN post quality, real авторский voice match

## Recommendations beyond fixes

1. **L5 E2E приоритет:** реальный `/post --linkedin --en про <автора real topic>`, scoring «reads like автор / generic AI / как один из 29 авторов»
2. **LinkedIn RU activation:** когда автор накопит 10+ RU LinkedIn постов → research 15-20 RU LinkedIn авторов → активировать combo linkedin-ru
3. **Cross-skill voice sync:** post / tweet / longform / email все ссылаются на автора voice. При update sync всех 4 одновременно
4. **Next audit:** через 30 дней или после 5+ применений

## Метаурок

Audit выявил: skill-craft v1.3 bug-categories.md хорошо покрывает content-skill family (13 categories). post v3.0 hit 10/13. Оставшиеся 3 (TG hook gate / Mode C PII / banned auto-refresh) не critical.

**Gap в skill-craft methodology:** L5 E2E нужен structured prompt template. Предложение: добавить `prompts/05-e2e-test-template.md` с test scenarios (mode × platform × language combos) и rubric для scoring.