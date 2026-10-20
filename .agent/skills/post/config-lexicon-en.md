---
name: post-config-lexicon-en
version: "1.0"
created: 2026-05-28
last_reviewed: 2026-05-28
description: EN lexicon (banned terms + required substitutions) для skill `post` platform=linkedin language=en. Источник - synthesis 29 LinkedIn EN авторов 2026-05-28, Section 7 (AI-tells) + Section 8 (anti-patterns для автора).
---

# post lexicon EN (LinkedIn EN gates)

> Используется в `workflow/04-review.md` для platform=linkedin language=en. RU lexicon - `config-lexicon-ru.md` (отдельный файл).

---

## Hard auto-fail (regex) - 22 AI-tells phrases

Cross-cut absence в 29-author corpus = strong signal AI-generation. Из synthesis Section 7.

```yaml
lexicon_banned_hard_en:
  # Verb / adjective tells (16) - single words, exact match case-insensitive
  - "delve"
  - "delve into"
  - "leverage"          # as verb in flat contexts (allow "leverage point" noun)
  - "navigate"          # as metaphor (allow "navigate to a URL" literal)
  - "unlock"            # only suspect in non-CTA contexts
  - "unleash"
  - "landscape"         # as metaphor ("AI landscape" - fail)
  - "foster"            # collaboration / community context
  - "streamline"
  - "robust"
  - "holistic"
  - "seamless"
  - "empower"           # default verb
  - "facilitate"
  - "meticulous"
  - "meticulously"

  # Phrase / opener tells (6) - multi-word, exact match
  - "in a world where"
  - "in today's fast-paced"           # killed by Dunford viral post 3,780 reactions
  - "in today's fast paced"
  - "in today's digital"
  - "in today's business"
  - "thrilled to share"               # Welsh actively warns against
  - "excited to announce"
  - "let's dive in"
  - "at the end of the day"
  - "it is important to note that"
  - "game-changer"
  - "paradigm shift"

  # Carrigan-style cliches (6) - corporate-speak fail
  - "unlock your potential"
  - "embrace the journey"
  - "the future is bright"
  - "synergize"
  - "circle back"
  - "move the needle"
```

---

## Hard auto-fail - Anti-patterns для автора (synthesis Section 8)

12 things top авторы делают что автору противопоказано:

```yaml
lexicon_banned_patterns_en:
  # US-business-jargon без объяснения
  - acronyms_unexplained:
      - "GTM"           # use "go-to-market motion"
      - "ICP"           # use "your ideal buyer"
      - "RevOps"        # use "revenue operations"
      - "MQL"           # use "marketing-qualified lead"
      - "MoM"           # use "month-over-month"
      - "CMO"
      - "CRO"
      - "CSO"
      - "B2B SaaS"      # use "business software" if non-tech audience

  # Comment-WORD gating (Donnelly/Bolis/Bourgoin pattern)
  - comment_word_gating:
      - "Comment '[A-Z]+' to"
      - "Comment .* to receive"
      - "Comment .* to get"
      - "DM me '[A-Z]+'"
      - "DM me .* for"
      - "Type '[A-Z]+' below"

  # Repost-bait
  - repost_bait:
      - "♻️ Repost"
      - "♻️ REPOST"
      - "Repost this if"
      - "Repost to help"
      - "Repost to unlock"

  # Dollar-anchor reciprocity (Bolis $X-Y value / Vicino $80M / Jay Clouse $2.8M)
  - dollar_anchor_inflated:
      - "\\$[0-9]+[MK]\\+? (revenue|earned|attributed|portfolio)"  # без verifiable proof
      - "value: \\$[0-9]+"
      - "worth \\$[0-9]+, free"

  # Family vulnerability content (Taha / Goetz / Donnelly / Vicino mentions)
  - family_vulnerability:
      - "my wife"
      - "my husband"
      - "my kids"
      - "my children"
      - "my divorce"
      - "IVF"
      - "miscarriage"
      # для автора vulnerability axis = business mistakes / product failures ONLY

  # Girlboss-coach register (Taha pattern)
  - girlboss_register:
      - "Young improfiters"
      - "Podcast Princess"
      - "babe"
      - "queen"
      - "🔥 ✨ 👀"        # emoji clusters
      - "⬇️⬇️⬇️"
      - "1️⃣2️⃣3️⃣"        # number emojis (generic-AI smell)

  # Celebrity name-drop (Taha tags MrBeast/Hormozi/GaryVee, Jay Clouse tags Welsh/Shleyner)
  - celebrity_name_drop:
      - "MrBeast"
      - "Hormozi"
      - "GaryVee"
      - "Gary Vee"
      - "Tobi Lutke"
      - "Dharmesh"
      # для автора: запрет в первые 6 месяцев EN - нет peer-stack для honest tag

  # ALL CAPS hooks
  - all_caps_hooks:
      - "^[A-Z]{4,}.*"  # hook line ≥4 заглавных подряд
      # ALL CAPS allowed только для 1-2 emphasis words MID-body, никогда в line 1

  # Bolis acronym-mining (PVC / SSR / CAR / VIP / PIE / TAP)
  - acronym_mining:
      - "PVC framework"
      - "SSR framework"
      - "CAR framework"
      - "VIP framework"
      - "PIE framework"
      - "TAP framework"
      # для автора: coin 1-2 named concepts MAX (вайбмаркетинг / контент-завод)
```

---

## Hard formatting gates (LinkedIn-specific)

```yaml
lexicon_formatting_en:
  # Hook spacing rule (Donnelly, validated synthesis Section 5)
  - hook_line_1_max_chars: 62
  - hook_line_2_max_chars: 62
  - hook_line_3_max_chars: 50
  - hook_see_more_cutoff: 210     # before LinkedIn truncates

  # Markdown stripping
  - no_unicode_bold: true          # LinkedIn doesn't render markdown bold
  - no_unicode_italic: true
  - no_markdown_headers: true      # no #/##/###

  # Hashtag count (validated 19/29 use 0-1)
  - hashtag_max: 1                 # premium positioning
  - hashtag_warn_above: 1
  - hashtag_fail_above: 3

  # Emoji count
  - emoji_max_per_post: 2          # functional only
  - emoji_warn_above: 2
  - emoji_fail_above: 5
  - banned_emoji:
      - "😀"  # face emojis cringe
      - "😂"
      - "💖"
      - "🎉"
      - "🚀"  # overused launch emoji
```

---

## Required substitutions (auto-correct)

```yaml
lexicon_required_en:
  # US-jargon → human language
  - replace: "your ICP"
    with: "your ideal buyer"
  - replace: "the ICP"
    with: "the ideal buyer"
  - replace: "GTM strategy"
    with: "go-to-market strategy"
  - replace: "GTM motion"
    with: "go-to-market motion"
  - replace: "MQL"
    with: "marketing-qualified lead"

  # Common AI-tell → human
  - replace: "let's dive in"
    with: "here's the breakdown"
  - replace: "at the end of the day"
    with: "the bottom line"
  - replace: "delve into"
    with: "look at"
  - replace: "leverage"
    with: "use"
```

---

## Validation refresh tracking

```yaml
validation:
  banned_list_last_review_date: "2026-05-28"
  banned_list_source: "synthesis 29 LinkedIn EN authors 2026-05-28"
  banned_list_refresh_interval_days: 30
  banned_list_refresh_workflow: "workflow/06-banned-refresh.md"
  # Когда пересматривать:
  # - catch_rate < 80% (track-record)
  # - 3+ post-publish "AI-slop" замечания от автора
  # - quarterly review синтеза competitors
```

---

## References

- `references/_voice-TEMPLATE.md` Section 7 - full 22 AI-tells list
- `references/_voice-TEMPLATE.md` Section 8 - full 12 anti-patterns
- `references/_voice-TEMPLATE.md` - verbatim примеры что НЕ нарушает эти rules
---

## Hard auto-fail - Parallel emphasis / triadic AI tics (gap fix 2026-05-28)

Перенесено из RU lexicon `double_emphasis_patterns` (config.md) которое было пропущено при initial сборке config-lexicon-en. Прецедент: proof generation 2026-05-28 выдал «Zero ads. Zero funnels. Zero sales calls.» - моя AI-конструкция приписанная Welsh (у Welsh «No funnels. No webinars. No upsells.» - другая лексика, не triple-Zero). Triple-X parallel emphasis pattern = generic AI tic detection.

```yaml
lexicon_banned_patterns_en_emphasis:
  # Triple-X parallel emphasis (cardinal AI tic)
  - triple_negation_pattern: "(Zero|No|Nothing)\\s+[\\w\\s]+?\\.\\s+(Zero|No|Nothing)\\s+[\\w\\s]+?\\.\\s+(Zero|No|Nothing)\\s+[\\w\\s]+?\\."
    # Examples blocked: "Zero ads. Zero funnels. Zero sales calls." / "No fluff. No filler. No BS." / "Nothing fancy. Nothing complex. Nothing hard."
    # Exception ALLOWED only if verbatim cited quote from another author with attribution

  - triple_emphatic_adjective: "(Only|Always|Never)\\s+[\\w\\s]+?\\.\\s+(Only|Always|Never)\\s+[\\w\\s]+?\\.\\s+(Only|Always|Never)\\s+[\\w\\s]+?\\."
    # Examples blocked: "Only X. Only Y. Only Z." / "Always X. Always Y. Always Z."

  - parallel_adjective_triplet: "\\b(simple|easy|fast|clean|smart|sharp|raw|honest)\\b\\.\\s+\\b(simple|easy|fast|clean|smart|sharp|raw|honest)\\b\\.\\s+\\b(simple|easy|fast|clean|smart|sharp|raw|honest)\\b\\."
    # Examples blocked: "Simple. Easy. Fast." / "Clean. Sharp. Smart." / "Raw. Honest. Simple."

  # Welsh closing signature combo - if both elements appear in sequence = Welsh form-copy fail
  - thats_it_newsletter_combo: "That's it\\.[\\s\\S]{0,200}Want the (full|complete|whole) (breakdown|playbook|guide)"
    # Welsh signature - voice theft if copied without explicit attribution

  # Generic confidence stack
  - confidence_stack: "(That's it|Done|Period|Simple as that)\\.\\s+(That's it|Done|Period|Simple as that)\\."

  # Rapid-fire short sentences (>=4 consecutive ≤30 chars)
  - rapid_fire_short_sentences: "^.{1,30}\\.\\s+.{1,30}\\.\\s+.{1,30}\\.\\s+.{1,30}\\.$"
    # WARN level - 4+ consecutive short sentences = AI rhythm tic
```

---

## Hard auto-fail - Voice-signature theft detection (gap fix 2026-05-28)

Из synthesis Section 6 Voice signature playbook: «Ivan should coin 2-3 of his own, NEVER borrow these verbatim». Skill должен поймать verbatim use чужой voice-signature.

```yaml
lexicon_banned_voice_signatures:
  - welsh_signatures:
      - "one-person business"
      - "Saturday Solopreneur"
      - "Build → Monetise → Scale"
      - "less ambition"
      - "(feel free to steal it)"

  - matt_gray_signatures:
      - "Founder Flywheel"
      - "ACER framework"
      - "Systems are your clone"
      - "♻️ Repost this to help"

  - acosta_signatures:
      - "SLAY framework"
      - "Master hook in every. single. line."
      - "Literally Academy"
      - "Power-ending"
      - "CTE (Call-To-Engagement)"

  - bloom_signatures:
      - "Engineered Serendipity"
      - "Luck surface area"
      - "The Curiosity Chronicle"
      - "Pygmalion Razor"

  - sanchez_signatures:
      - "boring businesses"
      - "Main Street vs Wall Street"
      - "Build anyway."
      - "Do your thing."
      - "sweaty, profitable"

  - hassid_signatures:
      - "Master AI before it masters you"
      - "How to AI with English, not code"

  - donnelly_signatures:
      - "The hook is 90%"
      - "Cut the fluff"
      - "Uncomfortable truths"

# Rule: any verbatim match = FAIL с message «<author> signature phrase. Find your own per synthesis Section 6.»
```
