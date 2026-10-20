# Visual formats — empirical

4 visual format archetypes observed в top 30 corpus. Каждый имеет специфичные production requirements.

Видео ≠ только текст. Это (a) что говорится (b) что показывается (c) что цепляет глаз — синхронно.

В моём failed video skill test я выдал только (a). (b) был vague handoff. (c) — отсутствовал.

---

## Format A — Greg Isenberg style (talking head + interview B-roll)

**Examples в corpus:** #2 (563K), #4 (523K), #9 (373K), #11 (274K), #13 (95K), #14 (79K), #16 (50K), #17 (47K), #20 (36K), #23 (25K), #28 (18K), #29 (18K), #30 (15K)

**Visual structure:**

| Time | Visual |
|---|---|
| 0-3 sec | Greg talking head (often head + shoulders, neutral background) с captions overlay |
| 3-end | Cuts между talking head AND screen recordings AND collab guest |

**Production stack:**
- Recording: Riverside or similar (для collab quality)
- Editing: Descript или premiere
- Captions: burned-in Hormozi-style yellow

**Когда применять для автора:**
- Когда есть collab гость (ученик с кейсом, expert friend)
- Для tutorial / methodology breakdowns
- Когда есть screen recording демо

**Опасность:** требует приличной production. Если автор один — этот формат overkill.

---

## Format B — Riley Brown style (POV + screen recording silent)

**Examples в corpus:** #5 (478K), #6 (468K), #15 (58K), #18 (43K), #26 (19K)

**Visual structure:**

| Time | Visual |
|---|---|
| 0-1 sec | Screen recording УЖЕ показывает action (Cursor / Lovable / Claude) |
| 1-end | Continuous screen recording с overlay text captions |

**Audio:** часто отсутствует! Только caption text + background music через TikTok overlay.

**Production stack:**
- Tella / Screen Studio для screen recording
- TikTok native captions + music
- iPhone optional для face-cam corner

**Когда применять для автора:**
- Для build-with-me / demo контента
- Когда виден экран = вся ценность
- Для TikTok native distribution

**Преимущество:** минимальная production, максимум authenticity. Это альфа-формат автора (memory `screen-record-face-cam`).

---

## Format C — Sabrina Ramonov style (POV with overlay tutorials)

**Examples в corpus:** #7 (402K), #10 (284K), #12 (136K), #19 (36K), #21 (31K), #24 (25K), #27 (18K)

**Visual structure:**

| Time | Visual |
|---|---|
| 0-3 sec | Numeric overlay («23M views» big text) + В-roll viral examples (screenshots) |
| 3-end | Screen recording app UI + tool walkthrough |

**Audio:** voice-over Sabrina + ambient music.

**Production stack:**
- Sabrina records voice-over на iPhone
- Screen recording app demo
- B-roll viral content screenshots
- CapCut для assembly

**Когда применять для автора:**
- Для «прокачка одним инструментом» content
- Когда есть viral metric для proof
- Для lead magnet promotion

---

## Format D — Cleo Abram style (cinematic B-roll narrative)

**Examples в corpus:** #8 (373K)

**Visual structure:**

| Time | Visual |
|---|---|
| 0-3 sec | Cinematic shot (close-up product / face / process) |
| 3-end | Sequence of cinematic B-roll synchronized с narration |

**Production stack:**
- DSLR / mirrorless camera
- Professional editing
- Often с team

**Когда применять для автора:**
- НЕ применять в стандарте — слишком высокая production для solo setup
- Только для major launches (cash event preview, brand-defining content)

---

## Visual mapping для авторского length tier

| Length tier | Recommended format |
|---|---|
| short-15-30s | Format B (Riley POV) — самый дешёвый, самый wow factor |
| short-30-60s | Format A (Greg talking + B-roll) OR Format B |
| short-60-180s | Format B for builds, Format A for methodology |
| mid-3-10min | Format A с deeper interview structure |
| long-10-60min | Format A + Format D mix |

---

## Required visual sequence (for content-skill output)

Каждый script должен включать **visual brief параллельно с тексту**, не отдельный handoff в конце:

```yaml
beat:
  text: "Сейчас покажу как настроить Claude Skills"
  visual:
    primary: "screen recording Finder с ~/.claude/skills/ folder открытой"
    secondary: "face-cam автор в corner"
    caption_overlay: "CLAUDE SKILLS SETUP"
    duration_sec: 10
```

Без visual layer каждого beat — script half-готовый.

---

## Visual hook tests (для 05-review Hook Strength Gate расширения)

Hook должен PASS visual contrast test:

1. **В первые 0.5 sec ВИДНО что-то ИЗМЕНЯЮЩЕЕ кадр** (movement / new screen / number popup)
2. **Visual не == простой talking head** (если talking head — должен быть unusual angle / lighting / motion)
3. **Captions появляются СРАЗУ** (не через 1 sec)

Test:
- Riley #3 hook: screen-recording vibe coding tutorial loops + Riley face overlay = visual contrast PASS
- Greg #2 hook: Greg head + captions «Why would you subscribe...» = caption motion contrast PASS
- Sabrina #7 hook: «23M 13M 13M» цифры big text = numeric outlier visual PASS

В моём failed video skill test:
- Hook visual: «face-cam автора крупным планом + caption ПРОМПТИНГ УМИРАЕТ»
- Visual contrast: ZERO — это просто talking head с caption. Algorithm не получает signal что это что-то новое.
- PASS test? NO.

---

## Cutoff правила в content-skill

1. Каждый script должен иметь visual brief параллельно тексту (per beat)
2. Hook должен PASS visual contrast test (movement / number / unusual frame)
3. Visual format должен match recommended для length tier
4. Visual format должен match Ivan's production capability (solo, no team)
5. Если visual brief требует production capability за пределами автора setup — flag в output

---

## Cross-refs

- `hook-patterns-empirical.md` — visual mechanics per hook pattern
- `body-structure-empirical.md` — visual cadence per body type
- Memory `screen-record-face-cam` — авторской alpha format
- `~/.claude/skills/video/references/structure-by-length.md` — text structure (требует обновления с visual layer)
