# Template: short-30-60s (стандартный шорт)

Грузится в `workflow/03-structure.md` когда `length_tier = short-30-60s`.

**Когда применять:** самый частый формат для автора. Reels / Shorts / TikTok стандарт. 3-step framework / 3 examples / personal story с insight.
**Reference creators:** Riley Brown (build-with-me), Nate Herk (anti-n8n / methodology), Chris Cordero (EN avatar).
**Sweet spot duration:** 45 sec.

## Structure (7 beats)

| Beat | Duration | Words RU | Words EN | Назначение |
|---|---|---|---|---|
| hook | 3 sec | 8 | 10 | Stop scroll |
| setup | 7 sec | 18 | 19 | Контекст / зачем смотреть |
| body_1 | 10 sec | 25 | 27 | Грань 1 |
| body_2 | 10 sec | 25 | 27 | Грань 2 |
| body_3 | 10 sec | 25 | 27 | Грань 3 |
| payoff | 3 sec | 8 | 9 | Synthesis |
| cta | 2 sec | 5 | 6 | Single action |

Sum: 45 sec / ~114 words RU.

## Fallback каркас (5-блочный, SOLO canib по решению автора from pisatel-rilz-razgovor)

Применяется когда нет готового арсенала структур / Spark mode без plan'а / Replication из card.md без точной structure-map.

5 блоков для скрипта 30-60 сек:

1. **Хук** (3-5 сек) — first sentence, стоп-скролл. Цитата ICP / spiky claim / contrarian opening
2. **Проблема** (7-10 сек) — что болит у ICP, на каком этапе застрял, цитата боли
3. **Решение** (10-15 сек) — как метод / приём / инсайт закрывает проблему, конкретика
4. **Разбор** (10-20 сек) — мини-кейс / пример / иллюстрация решения в действии (мини-история ученика или своего опыта)
5. **CTA** (3-5 сек) — single action: «напиши в личку X», «приходи на эфир», «забери лидмагнит». Без множественных «и подписывайся и комментируй и сохраняй»

Каркас применять когда длина = 30-60 сек, формат разговорный (talking head или voice-over).

## Hook archetype fit

Все 8 patterns. Naиболее частые для автора:
- Pattern 1 (Timeframe + outcome): «Собрал X за Y минут»
- Pattern 6 (Contrarian): «N умирает. Вот что вместо»
- Pattern 2 (Demo-first): tool уже в кадре

## Pacing

- Быстрый, но air для body примеров
- body_1/2/3 = 3-step framework / 3 sequential examples / 1 story с 3 beats
- Mini-hook в начале body_2 не обязателен, но retention helper

## Caption overlay

- 12-20 lines total, ALL CAPS Hormozi
- 2-6 слов на line
- Hook line bigger, hold 1.5 sec

## Production handoff

screen-record-face-cam (alpha) / split-screen-trend-jack / ai-avatar-news / before-after / replicate-reel.
Aspect: 9:16 vertical.

## Headline / caption first 3 sec

≤50 chars Hook line.

Examples:
- «КОНСТРУКТОРЫ УМИРАЮТ. ВОТ ЧТО ВМЕСТО»
- «СМОТРИ - ЭТО CLAUDE. ОДИН ПРОМПТ. ГОТОВЫЙ БОТ»
- «Я ПЕРЕПИСАЛ $50K САЙТ ЗА 11 МИНУТ»

## Beat placeholders (для 04-write.md)

```yaml
hook:
  archetype: <from finalize>
  seed: "<3-sec hook, 8 слов>"
  caption_lines: [<2 lines>]
setup:
  seed: "<контекст: что было раньше / зачем зрителю слушать>"
  caption_lines: [<3-4 lines>]
body_1:
  seed: "<грань 1, конкретная>"
  caption_lines: [<4-5 lines>]
body_2:
  seed: "<грань 2, концретная>"
  caption_lines: [<4-5 lines>]
body_3:
  seed: "<грань 3>"
  caption_lines: [<4-5 lines>]
payoff:
  seed: "<synthesis 8 слов>"
  caption_lines: [<2 lines>]
cta:
  seed: "<single action 5 слов>"
  caption_lines: [<1-2 lines>]
```

## Beat shape (универсальный для body)

Каждый body beat = 1-sentence setup + 1-sentence detail/example + 1-sentence implication.

Без shape beat «расплывается», retention падает.

## Anti-patterns

- Setup beat >10 sec (затягивает)
- Только 1-2 body beats (нужно 3 для shape)
- Payoff >5 sec (не Hormozi-cut)
- CTA generic «коммент» без action word
- Listing tells «вот 3 правила X» (используй methodology формулировку, не lecture)

## Example reference

`examples/_TEMPLATE-shorts.md`:
- Эталон 1 (Mode B1 contrarian Outlaw) - 45 sec
- Эталон 2 (Mode A demo-first Magician) - 50 sec

## Length check

Floor 30 sec / Ceiling 60 sec / Sweet spot 40-50 sec.