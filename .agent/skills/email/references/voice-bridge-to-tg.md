---
name: voice-bridge-to-tg
description: Voice bridge на post skill - single source of truth для голоса автора. Email skill наследует ivan-voice / _voice-TEMPLATE / archetypes / hooks-15 / Maxwell Ross 9 / atomic essay structure из post references. Что специфично для email (НЕ из post). Voice adaptations TG vs email. Fail-safe если post не клонирован. Loading bridge в `workflow/03-write.md` Pass 0. Single source = no synchronization tax, no voice drift.
version: 1.0.0
last_updated: 2026-05-28
---

# Voice bridge на post skill

автор (и ученик курса) пишет письма и TG-посты одним голосом. Дублировать voice references в обоих skill = drift: правка в одном файле, забыли в другом, через 3 месяца два голоса разъезжаются. Bridge = single source of truth, email skill наследует voice rules из post skill без копи-пасты.

Документ объясняет что наследуется, что email-specific (НЕ из post), как loading работает в `workflow/03-write.md`, и как bridge fail-safe если post не клонирован у ученика.

## Зачем bridge

3 причины:

- **No drift** - обновили `~/.claude/skills/post/references/_voice-TEMPLATE.md` (новая banned A-Z фраза, новый живой глагол), email skill автоматически подхватывает на следующий run. Без bridge - пришлось бы вручную синкать оба skill.
- **No duplication tax** - `~/.claude/skills/post/references/_voice-TEMPLATE.md` это ~600 строк. Дублировать = 1200 строк maintained. Bridge = 600 строк maintained.
- **Single source of truth** - голос автора это product. Один авторитетный файл = одно решение. Два файла = вечный спор какой prevails.

## Что наследуется из post

Email skill в Pass 0 (`workflow/03-write.md`) читает 6 reference файлов из `~/.claude/skills/post/references/`. Это voice DNA автора.

- `~/.claude/skills/post/references/_voice-TEMPLATE.md` - 16 уникальных терминов автора (вайбкодинг / вайбмаркетинг / контент-завод / ферма / перегнать / пдп / Нельзяграм / Дубайск / …) + 11 анти-паттернов (банальные метафоры, AI-конструкции, em-dash, abstract value language) + 5 главных приёмов из gold-standard постов
- `~/.claude/skills/post/references/_voice-TEMPLATE.md` - живые глаголы вместо AI-абстракций («доставить» вместо «делиться ценностью», «перегнать» вместо «адаптировать»), 26 banned A-Z классов AI-конструкций (от A.1 «инсайты и решения» до Z.5 «архитектура смыслов»), Self-Discovery Method для генерации новых banned фраз
- `~/.claude/skills/post/references/archetypes-12.md` - Marc & Pearson 12 архетипов, mapping автора: primary Magician (трансформация через AI) + Sage (методология) + Outlaw (анти-курсомания, анти-продюсерская модель). Banned для автора: Caregiver (не «забочусь»), Lover (не интим-сообщество), Innocent (не наивный энтузиазм)
- `~/.claude/skills/post/references/hooks-15-templates.md` - 15 LinkedIn hook templates (Welsh / Hormozi / Vasilkov) + RU adaptation. Email skill использует для Subject lines и для body hook (первая строка)
- `~/.claude/skills/post/references/maxwell-ross-9-checklist.md` - 9 pre-publish items (1-line hook test / scroll-stop test / single-CTA test / читается на 13-летнего / no-jargon test / etc.)
- `~/.claude/skills/post/references/atomic-essay-structure.md` - Bush+Cole 7-step (hook / context / promise / proof / payoff / cta / sign-off) + headline formula + 1/3/1 rhythm (1 sentence - 3-sentence block - 1 sentence)

Все 6 файлов наследуются всегда, no per-mode toggle.

## Что email-specific (НЕ из post)

Email skill имеет свои references, которые в post не существуют:

- `references/subject-formulas-50.md` - 50 subject line formulas (curiosity gap, specificity, urgency, personalization, contradiction, social proof, question, numbered)
- Preheader patterns - отдельная hook отличная от Subject, дополняет не дублирует
- CTA strategy для email - above-fold + bottom + P.S. placement rules; single-CTA goal per email
- Spam triggers - каких слов и форматов избегать в Subject + body (ALL CAPS, $$$, money-back, click here, FREE!!!)
- Mobile inbox preview rules - первые 40 chars Subject + 80 chars preheader решают open rate
- ESP-specific formats - Kit (`references/kit-format.md`) / Beehiiv (`references/beehiiv-format.md`)
- Launch sequence frameworks - 7-14 email arc для запуска (anticipation / cart open / urgency / close)

Email-specific references лежат рядом с bridge в `~/.claude/skills/email/references/`.

## Voice adaptations для email vs TG

Голос один (автора), но формат разный. Что одинаково, что меняется.

**Одинаково (наследуется):**

- Местоимение «ты» (low formality, peer-to-peer)
- Уникальные термины автора (вайбкодинг / вайбмаркетинг / контент-завод / Нельзяграм / etc.)
- Живые глаголы вместо AI-абстракций
- Архетипы Magician / Sage / Outlaw
- 1/3/1 rhythm в параграфах
- Single-CTA goal (не размывать)
- Запрет em-dash внутри строк, банальных метафор, generic AI-конструкций

**Разное (adaptation):**

- **Длина:** TG-пост обычно 1500-2500 chars (~250-400 слов). Email типично 500-1500 слов (4-10x длиннее). Email позволяет multi-paragraph flow, TG требует радикальной компрессии.
- **Структура параграфов:** TG = короткие chunks по 1-3 предложения (mobile reading). Email = mixed (short hooks + longer body paragraphs OK для desktop reading на email client).
- **Hook timing:** TG hook = первая строка (scroll-stop в feed). Email hook = Subject + Preheader (inbox decision) + первая строка body (open decision).
- **CTA placement:** TG = один CTA в конце (или вообще no CTA для nurture). Email = 1 CTA для nurture, 3-5 strategic placements для sales-letter (above-fold + value stack + social proof + guarantee + P.S.).
- **Mobile preview matters:** TG = первая строка превью в notification. Email = Subject (40 chars iPhone) + Preheader (80 chars) в inbox preview. Both critical для open / read decision.
- **Sign-off:** TG = no sign-off (channel post, no greeting). Email = greeting в начале (Привет / нет) + sign-off (С уважением, автор) + P.S.

## Когда bridge fail-safe

Если у ученика курса post skill НЕ клонирован (например, ученик пришёл сразу на email skill без полного content factory setup), bridge должен gracefully fail.

- `config.md` ученика имеет поле `paths.tg_content_voice = null` (или путь к локальному clone).
- Если null, email skill loads только свои references (subject-formulas-50.md + kit-format.md / beehiiv-format.md).
- Voice будет generic (не авторский), но email будет structurally valid (Subject + Preheader + Body + CTA).
- Onboarding (`workflow/00-onboarding-student.md` Q9) явно спрашивает: «Клонирован ли у тебя post skill? Если да, путь?». Default = «нет» для учеников, «yes $HOME/.claude/skills/post» для автора.

## Loading bridge в `workflow/03-write.md` Pass 0

В начале каждого `workflow/03-write.md` run, skill делает Pass 0 - loading voice DNA. Обязательные Read'ы:

1. `config.paths.tg_content_voice` → `~/.claude/skills/post/references/_voice-TEMPLATE.md`
2. `config.paths.tg_content_living_language` → `~/.claude/skills/post/references/_voice-TEMPLATE.md`
3. `config.paths.tg_content_archetypes` → `~/.claude/skills/post/references/archetypes-12.md` (опционально, для archetype-aware writing)
4. `config.paths.tg_content_hooks` → `~/.claude/skills/post/references/hooks-15-templates.md` (для Subject и body hook)
5. `config.paths.tg_content_maxwell` → `~/.claude/skills/post/references/maxwell-ross-9-checklist.md` (для review pass)
6. `config.paths.tg_content_atomic` → `~/.claude/skills/post/references/atomic-essay-structure.md` (для structure pass)

Если любой путь null или файл не существует - Pass 0 logs warning, продолжает без этого файла (graceful degradation).

## Как bridge prevents voice drift

Сценарий 1 - обновили banned phrase в post:

- автор добавил в `~/.claude/skills/post/references/_voice-TEMPLATE.md` новую banned A-Z phrase (например, X.7 «открывает новые горизонты»).
- Email skill следующий run автоматически Read'ит обновлённый файл.
- Review pass в `workflow/04-review.md` ловит banned phrase в email draft, кикает на revision.
- No manual sync, no drift.

Сценарий 2 - обновили email-specific Subject formula:

- Skill добавил в `subject-formulas-50.md` новую formula (например, #51 reverse-curiosity).
- post НЕ trogается, потому что Subject это email-specific concept.
- No cross-pollution, clear ownership.

Сценарий 3 - voice DNA меняется (новый архетип или новый сигнатурный термин):

- Меняется только в post references.
- Email auto-inherits.
- Single source = no synchronization tax.

## Anti-patterns

Что НЕ делать с bridge:

- **Дублировать _voice-TEMPLATE.md в email/references/** - drift через 3 месяца, два голоса разъезжаются. Always reference, never copy.
- **Игнорировать bridge если у ученика клонирован post** - waste. Email skill теряет 600 строк voice DNA, генерит generic email.
- **Hard-code voice rules в email workflow** - копи-паст banned phrases в `workflow/03-write.md` = drift при обновлении _voice-TEMPLATE.md. Always load from bridge.
- **Кешировать voice DNA между sessions** - voice DNA может обновляться между sessions. Always Read at Pass 0, не предполагать что в memory.
- **Override voice DNA email-specific exceptions** (например, «для email можно em-dash») - нет, voice DNA = absolute. Email-specific это только то что в post НЕ существует (Subject lines, CTA placement, ESP format).

## Cross-references

- Bridge target skill `~/.claude/skills/post/SKILL.md` + `~/.claude/skills/post/references/`
- Email-specific references `references/subject-formulas-50.md`, `references/kit-format.md`, `references/beehiiv-format.md`
- Loading в workflow `workflow/03-write.md` Pass 0
- Onboarding bridge availability `workflow/00-onboarding-student.md` Q9
- Config paths `config.md` секция paths
