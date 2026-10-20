# Funnel awareness — empirical

КАЖДЫЙ content-skill output должен знать **куда ведёт зрителя** в авторской воронке.

Из corpus видно: топ creators (Greg / Riley / Sabrina) ВСЕГДА имеют explicit funnel destination. Без destination шорт = content для content's sake = no business impact.

Это был критический gap в video skill v1.0 (мой провальный test: «Коммент СКИЛЛ. Покажу свои» — не вёл никуда).

---

## авторская funnel architecture (2026 май)

### Top of funnel (TOFU) — discovery

**Channels:**
- Нельзяграм Reel (<твой-хэндл>)
- YouTube Shorts (<твой-хэндл> — пока не активен)
- TikTok (через uniqalizer)
- TG канал <твой-хэндл> (тёплая аудитория)

**KPI:** views / reach / unique watches

### Middle of funnel (MOFU) — capture

**Channels:**
- TG канал подписка (через bio link)
- Newsletter (Kit — planned)
- Lead magnets (free PDF / video / промпт-файл)

**KPI:** subscribers / open rate / save rate

### Bottom of funnel (BOFU) — conversion

**Products (авторский):**
- Cash event <частота запусков> (<твой ценовой диапазон> EN / 43-199К₽ RU)
- Skool club (<твоя подписка> EN / ?₽ RU)
- High-ticket personal launches

**KPI:** registrations / conversions / revenue

---

## ⛔ Два независимых механизма — НЕ путать 

Любой writer-скилл обязан держать эти две сущности раздельно. Их смешивание = фактическая ошибка (был случай: пост заявил, что контент-завод «работает по карте смыслов»).

| Механизм | Что это | Где | Движок |
|---|---|---|---|
| **Контент-завод 2.0** | acquisition / growth машина органических подписчиков | Нельзяграм / TikTok / Shorts (рилсы, карусели) | AI-pipeline уникализации и производства роликов |
| **Карта смыслов** | source of truth для контента ЗАПУСКА | запуск в Telegram (посты, прогрев) | Claude по карте смыслов пишет посты/прогрев на запуск |

**Запрещённые связки (любая = фактический брак):**
- «контент-завод / ролики / карусели работают по карте смыслов»
- «карта смыслов производит / управляет рилсами для Нельзяграма»
- «устойчивость к бану держится на карте смыслов»

**Правильная модель:** бан Нельзяграма бьёт по контент-заводу (acquisition), карта смыслов кормит ТОЛЬКО посты запуска в TG. Это два независимых фронта. Реакция автора на путаницу: «Карта смыслов - это для запуска в Telegram. Каким образом это связано с постами для Нельзяграма и каруселями?»

---

## Mapping CTA → funnel stage

| CTA Type (из cta-patterns-empirical) | Funnel target | Best content type |
|---|---|---|
| Type 1 — «Comment TRIGGER» | TOFU → MOFU (DM auto-message с lead magnet) | Tutorial / how-to teasers |
| Type 2 — «Go to URL» | TOFU → MOFU (landing → email opt-in) | Free product launches |
| Type 3 — «Save mid-roll» | TOFU algorithmic boost | Long prompts / workflows |
| Type 4 — «Series cliffhanger» | TOFU (follow → next video) | Brand-building content |
| Type 5 — Drop-mic | TOFU brand association | Conviction / philosophy content |

---

## Funnel-aware checklist для content-skill

Перед output каждого скрипта проверить:

### 1. Funnel destination explicit
- ❓ Куда зритель идёт после просмотра?
- ❓ Что он делает в течение 7 дней?
- ❓ Какая метрика авторских KPI улучшается?

Если ответ ≥1 vague — script не готов.

### 2. CTA matches funnel target
- ❓ Если target = TG канал → CTA = «подпишись на <твой-хэндл>, ссылка в био»
- ❓ Если target = lead magnet → CTA = «коммент TRIGGER» с auto-DM настройка готова
- ❓ Если target = brand association → CTA = drop-mic с emotional payoff

### 3. Lead magnet ready (если applicable)
- ❓ Если CTA promises «пришлю гайд» — гайд существует в файле?
- ❓ Auto-DM настроена в ManyChat (или аналог)?
- ❓ Landing page готова если CTA = URL?

Если ответ NO — script задерживается до infrastructure ready. Иначе viewer заходит → ничего не получает → trust loss.

### 4. One CTA per video
- ❓ Только ОДИН primary action в финале?
- ❓ Mid-roll save (Type 3) допустим как дополнение, не как primary?

Multiple CTAs = viewer не делает ничего.

### 5. Funnel pillar alignment
- ❓ Topic шорта соответствует content pillar автора?
- ❓ См. `.business/marketing/content.md` — текущие pillars

Если topic вне pillars — это random content без strategic value.

---

## авторские lead magnets (existing + planned)

### Existing (verified, можно использовать в CTA)
- TG канал <твой-хэндл> (просто подписка)
- (Дополнить когда есть: lead magnet PDF / промпт-файл / видео)

### Planned (НЕ использовать в CTA пока не готовы)
- Vibemarketing 2026 курс (запуск июнь 2026)
- Mastermind клуб (RU)
- Newsletter Kit (EN, planned)
- Free промпт-файл для контент-завода (planned)
- Skool club EN (<твоя подписка>)

**Critical:** content-skill должен сверяться с этим списком перед CTA generation. Если lead magnet not ready → fallback CTA = подписка на TG.

---

## Failed CTA patterns (из моего video skill test)

### «Коммент СКИЛЛ. Покажу свои» (моё output)

**Проблемы:**
1. «Свои» — что? У зрителя нет skills. Confusion.
2. Trigger word «СКИЛЛ» — не настроен в ManyChat
3. Lead magnet «скилл» — не существует как packaged deliverable
4. Funnel target undefined — куда ведёт после DM?

**Fix:**
- Trigger word связан с конкретным lead magnet
- Lead magnet = существующий artifact
- Funnel target = MOFU (email signup or TG subscribe)
- Phrase ясная: «Коммент `ЗАВОД` — пришлю промпт-файл который запускает контент-завод за вечер»

---

## Pillar-CTA matrix (recommended)

| Content pillar (Ivan) | Funnel target | CTA template |
|---|---|---|
| Vibemarketing methodology | Email signup → cash event | «Коммент `ВОРОНКА` — пришлю шаблон» |
| Vibecoding builds | TG subscribe | «Подпишись на <твой-хэндл>» |
| AI tooling reviews | Lead magnet URL | «vibemarketing.ru/free» |
| Personal launch updates | Cash event registration | «Регистрация в био — следующий запуск через X дней» |
| Behind-the-scenes | Brand association (drop-mic) | (drop-mic close) |

---

## Cutoff правила в content-skill

1. Каждый script ОБЯЗАН иметь explicit funnel destination в meta block
2. CTA должна match destination (см. matrix выше)
3. Если lead magnet not ready — fallback на TG subscribe
4. Если pillar match отсутствует — content-skill ESCAPE с warning «topic outside Ivan pillars»
5. Не более 1 primary CTA + 1 mid-roll save

---

## Cross-refs

- `cta-patterns-empirical.md` — 5 типов CTA с mechanics
- `~/.business/marketing/content.md` — content pillars автора
- `~/.business/marketing/funnel.md` — funnel architecture
- `~/.business/products/overview.md` — list of products для CTA mapping
