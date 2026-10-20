# Body structure — empirical patterns

Анализ body структур (после hook) из 30 viral шортов в авторской нише.

## Главная находка

**Все top шорты имеют explicit WALKTHROUGH structure, не «3 grани».**

Зрителю показывают КАК сделать, шаг за шагом. Каждый body beat = 1 actionable step.

Это категорически отличается от theory-driven «3 examples / 3 angles» подхода в моих references. Viral шорты — это **how-to** + **demo на экране**, не «эссе с 3 пунктами».

---

## Pattern A — «First X. Then Y. Next Z. Finally W» — 4-step workflow

**Корпус частота:** топ 1 паттерн (15 из 30 шортов)

**Examples (verbatim):**

Greg #2 (563K views):
> «Start by creating the agents.md file...
> Next is the context folder...
> Say you ask it to stop signing emails with cheers, it logs that in the memory.md file...
> And lastly, create the skills folder»

Greg #4 (523K):
> «First, you need to download this free note-taking tool called Obsidian...
> Next, simply connect this to Claude code using the Obsidian CLI...
> After that, ask Claude to build you custom commands...»

Greg #9 (373K):
> «First, use the Ask User Question tool by copy-pasting this prompt...
> Now that Claude knows what you want, don't simply say, build me an app. Instead, break it into feature A, B, and C...
> Finally, watch your context window»

Greg #14 (79K):
> «First, build a React-based ad generator...
> Then generate an infinite number of variations...
> Next, use the Perplexity API...
> Just feed those insights directly into your agent...
> Finally, use the Facebook Ads API»

Greg #16 (50K):
> «But before you even type in your first prompt, you need to run these two commands and install the front-end design skill...
> Another is the brand voice skill...
> Finally, if you want truly high converting landing pages, set up this landing page architecture skill»

Greg #17 (47K):
> «First, build the ugly prototype in Google AI Studio...
> Next, move to this Pinterest alternative to pick five to ten images...
> Now, for the most important part, the logo, use ideagram v3...
> Finally, assemble everything in Figma»

**Структура (extracted):**

| Step | Duration | Words | Что делает |
|---|---|---|---|
| Step 1 | 8-12 sec | 20-30 | Setup / starting point — tool name + first action |
| Step 2 | 8-12 sec | 20-30 | Second action + small context |
| Step 3 | 8-12 sec | 20-30 | Third action (often с detail explanation) |
| Step 4 | 8-12 sec | 20-30 | Final action + ИЛИ payoff |
| (Optional Step 5) | 5-8 sec | 15-20 | Bonus / advanced trick |

**Total body:** 32-50 sec для шорта 45-60 sec total.

**Critical: каждый step имеет CONCRETE TOOL NAME + CONCRETE ACTION.**

- ❌ «настрой voice один раз»
- ✅ «create the agents.md file with your business, voice, and how you like to work»

**Replication для автора:**

«First, в `~/.claude/skills/` создай папку `post`. В ней SKILL.md с твоим voice.
Next, добавь references/voice.md — твои 5 любимых постов копи-паст.
After that, в любом чате пиши `/post идея X` — Claude напишет в твоём тоне.
Finally, добавь references/voronka.md с ссылками — каждый пост ведёт в твою воронку».

Каждый step = 1 файл / 1 команда / 1 концепт. Не абстракция «структура knowledge base».

---

## Pattern B — «Demo through example» (concrete scenarios)

**Корпус частота:** 8 из 30

**Examples:**

Greg #2:
> «Say you ask it to stop signing emails with cheers, it logs that in the memory.md file»

Greg #4:
> «Daily operations, like a today command, that pulls your calendar, tasks, and recent notes into a one-day prioritized plan»

Greg #13:
> «Like, say, organizing your receipts. Claude Cowork not only names and rearranges them, but also creates a spreadsheet»

Riley #25 (Riley building Tinder for guys):
> «I want you to create an app, Tinder, but for guys to find other guys to do projects with. And so these projects will be in these five different categories»

**Паттерн:** «Say you X. Y happens. Result Z.»

- Setup (You X) — relatable scenario
- Mechanism (Y happens) — what tool does
- Result (Z) — payoff

**Replication для автора (RU):**

«Скажешь — напиши пост про вебинар через 3 дня. Claude не пишет шаблон. Идёт в /knowledge, берёт твою last reach 25K, твой CTR на TG 8%, твой voice. Выдаёт пост с цифрами твоего канала».

---

## Pattern C — Multi-step с inline mini-hooks (для шортов 90+ sec)

**Корпус частота:** Riley #3 (562K), Riley #22, Riley #26 (top 5 longer-form viral)

**Mechanic:** длинный body разбит на эпизоды, каждый эпизод имеет мини-hook (often question или authority callback).

Riley #3 example (109 sec):
- Hook: «Is programming going to be replaced by vibe coding?»
- Authority proof: «According to the founder of Anthropic...»
- Mini-hook 1: «And this isn't just hype. The CEO of Gumroad thinks that we are already there»
- Mini-hook 2: «And there's also web-based tools like Lovable, V0, Bolt»
- Mini-hook 3: «And I guarantee you there's going to be defensive nerds in the comments saying...»
- Payoff: «So congratulations. If you speak English, you are now a VibeCoder»

**5 mini-hooks за 109 sec** — каждые 20 sec retention bridge.

**Replication для автора:**

Для long-form шортов (60-180 sec) — каждые 20-30 sec обязательно один из:
- «А вот что заметил»
- «Тут есть нюанс»
- «Сейчас самое интересное»
- «И гарантирую — в комментах будет [archetype оппонент]»
- Authority callback

---

## Pattern D — «Multi-step end-to-end demo» (90+ sec build-with-me)

**Корпус частота:** Riley #25 (20K — but lower view counts типичны для long form)

Riley #25 (118 sec — building Tinder for guys app):
- Hook + intent: «I saw this post on Twitter yesterday... I'm gonna build this»
- Plan announcement
- Prompt copy-paste
- Side action (logo generation while Claude builds)
- Result reveal
- Result demo (showing app working)
- Closing (boom emphasis)

**Структура:** Plan → Prompt → Wait/Side-action → Result → Demo → Close

**Это формат для авторского «build a SaaS in 47 minutes» направления.** Высокий effort, но maximum credibility.

---

## Что НЕ работает в body (anti-patterns из low-virality observed)

1. **Theory без demo.** Если ни один step не показывает конкретный экран / результат — viewer falls off.
2. **«У меня X» без teaching.** Flex без walkthrough = self-promo, не value.
3. **No tool names.** Generic «AI tool» вместо конкретного «Claude Code» / «Cursor» / «Lovable» = forget-able.
4. **More than 5 steps.** Viewer не запомнит. 3-5 — sweet spot.
5. **No transition phrases.** «Просто скажу так-то». Не работает — viewer теряет связь между beats.

---

## Глоссарий transitions (русский)

Use these verbatim для body beats в скриптах:

- «Сначала — [action]. [explanation in 1 sentence].»
- «Дальше — [action]. [why this is important].»
- «После этого — [action]. [what happens].»
- «Финально — [action]. [payoff].»
- (для mini-hooks): «А вот что важно...» / «Сейчас фокус...» / «И гарантирую...»

Avoid:
- «Теперь рассмотрим...» (lecture)
- «Также важно...» (filler)
- «Давайте посмотрим...» (AI tell)
- «В завершение хочется сказать...» (formal)

---

## Cutoff правила для использования

В content-skill review:

1. Body должен быть walkthrough structure (Pattern A / B / C / D) или explicit обоснование отклонения
2. Минимум 1 concrete tool name per body beat
3. Минимум 1 demo-able action per body beat (не abstract concept)
4. Для шортов 60+ sec — обязательно mini-hooks каждые 20-30 sec
5. Не более 5 steps. Иначе split на серию.

---

## Cross-refs

- `hook-patterns-empirical.md` — что предшествует body
- `cta-patterns-empirical.md` — как закрывать body
- `voice-markers-empirical.md` — verbatim transitions per creator
- `audience-glossary.md` — agent-jargon → язык ЦА для tool names
