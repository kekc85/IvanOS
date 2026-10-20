# 05-publish.md - Output + A/B + STEPPS + self-check

Принимает clean draft от 04-review (PASS). Финальный output.

## Step 1 - Format final output для пользователя

### For single tweet

```
**X (1 tweet, <N> chars):**

[hook + body, ready to copy]

**Threads (1 post, <N> chars):** (если platform_target = both)

[expanded version, ready to copy]
```

### For thread

```
**X thread (N tweets):**

1/ [hook]

2/ [beat 1]

3/ [beat 2]

...

N/ [closer]

---

**Threads chain (M posts):** (если platform_target includes threads)

[adapted version, может быть короче chain]
```

## Step 2 - A/B variants (3 alternatives)

Generate 3 A/B variants по разным hook patterns:

- Variant A: original hook (chosen in 02-structure)
- Variant B: same content, alt hook from 15 patterns library
- Variant C: same content, opposite hook (e.g., если A = counter-intuitive, C = confession+pivot)

Format:
```
**A/B variants for testing:**

Variant A (current): "<hook>"
Variant B (alt 1): "<alt hook>"
Variant C (alt 2): "<alt hook>"

Рекомендация: A для X primary, B для Threads cross-post (algorithm difference)
```

## Step 3 - STEPPS check (Berger virality)

| Element | Present? |
|---|---|
| **S**ocial currency (makes reader look smart sharing it?) | Y/N |
| **T**riggers (cues that remind reader?) | Y/N |
| **E**motion (high arousal - awe / anger / amusement?) | Y/N |
| **P**ublic (visible action?) | Y/N |
| **P**ractical value (saves time / makes money?) | Y/N |
| **S**tories (narrative wrapping?) | Y/N |

Score N/6. Менее 3 → warning, не fail (не каждый пост STEPPS-heavy нужно).

## Step 4 - Self-check «Как писал» блок

```
**Как писал** (внутрянка):
- Mode: <Plan / Spark-B1 / Spark-B2 / Transcript>
- Platform: <x / threads / both>
- Language: <ru / en>
- Type: <1 of 7>
- Format: <single / mini-thread N / mega-thread N>
- Hook pattern: <1 of 15>
- Char zone: <A 40-100 / B 200-280>
- Archetype: <Magician / Sage / Outlaw>
- Voice cluster: <build-in-public / paips-story / spiky / aphorism / idea-drop>
- HSO scaffold: <Hook → Story → Offer breakdown>
- Что отброшено: <list альтернатив которые не выбрал>
- A/B логика: <почему A primary, B/C alternatives>
- 3 слоя пройдено: ✓
```

## Step 5 - Track record update

Append к `examples/track-record-tweet.md`:

```markdown
## Application <N> - YYYY-MM-DD

- Mode: <mode>
- Type: <type>
- Hook pattern: <pattern>
- Char zone: <A/B>
- Topic: <topic>
- Output saved: <link or null>
- Catch rate: TBD (update после реальной publication + engagement data)
```

## Step 6 - Output to user

Финальный message в чат с:
1. Ready text (X + Threads если both)
2. A/B variants
3. STEPPS score
4. «Как писал» блок
5. Confirmation 3 слоя пройдено

## Anti-patterns publish

- НЕ output без A/B variants (минимум 2 alternatives)
- НЕ skip «Как писал» блок (глубина процесса видна через обоснования)
- НЕ output без 3 слоя confirmation
- НЕ update track-record до confirmation от user (заполняется после real publication)
---

## Proof Block (HARD — обязательный вывод под постом)

ОБЯЗАТЕЛЬНО вывести в чат `_shared/proof-block-gate.md` КАЖДЫЙ раз под готовым постом: (1) чек-лист стадий скилла (что взято), (2) таблица по ВСЕМ 13 мастерам `mastery/copywriting/` с дословной цитатой из поста (или причиной skip), (3) вердикт независимого верификатора. Итеративно: сначала пост через скилл → наложить мастеров → доказать по чек-листу/таблице. Без Proof-блока вывод недоделан. Прецедент по решению автора (скепсис «не имплементировал»). Память `feedback_prove_skill_and_masters_each_time`.
