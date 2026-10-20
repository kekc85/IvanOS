---
name: longform-config-v1.1-extension
description: v1.1 extension config patches (anglicism blocker, tutorial pattern расширение, fake percent regex, techjarg disclosure flag). Loaded в дополнение к config.md. Создан 2026-05-28 после test incident.
metadata:
  version: "1.1"
  parent_config: "config.md"
---

# config-v1.1-extension

> Loaded в дополнение к `config.md`. Применяется в `04-review.md` Pass 1 hard gates.

## v1.1 anglicism extension (lexicon_banned_hard EXTEND)

Добавляется к `lexicon_banned_hard` из config.md + post inherit. Hard fail на каждое.

```yaml
lexicon_banned_hard_v1_1_extension:
  # Контент / маркетинг nouns
  - "tools"
  - "tool"
  - "stack"
  - "stack-up"
  - "stack-rank"
  - "transition"
  - "transitions"
  - "crossfade"
  - "viral"
  - "layered"
  - "catalog"
  - "mockup"
  - "mockups"
  - "validators"
  - "gauntlet"
  - "guesswork"
  - "reveal"
  - "breakdown"
  - "takeaway"
  - "hack"
  - "hacks"
  - "hustle"
  - "edge case"
  - "use case"
  - "insight"
  - "insights"
  - "flow"
  - "roadmap"
  - "value prop"
  - "talking head"
  - "screen-record"
  - "face-cam"
  - "split-screen"
  - "stop-scroll"
  - "churn"
  - "open rate"
  - "click-through"
  - "draft"
  - "brief"
  - "trigger"
  - "config"
  - "feedback loop"
  - "context"
  - "Excel"
```

Полный catalog с RU заменами - `references/anglicism-blocker-ru.md`.

## v1.1 tutorial genre pattern extension

Добавляется к `tutorial_genre_pattern` из config.md.

```yaml
tutorial_genre_pattern_v1_1_extension:
  - "Уровень 1[:.].+Уровень 2[:.].+Уровень 3[:.].+Уровень 4"
  - "Component 1[:.].+Component 2[:.].+Component 3[:.].+Component 4"
  - "Часть 1[.:].+Часть 2[.:].+Часть 3[.:]"
  - "Стадия 1[.:].+Стадия 2[.:].+Стадия 3[.:]"
  - "Layer 1[:.].+Layer 2[:.].+Layer 3[:.]"
  - "Этап 1[:.].+Этап 2[:.].+Этап 3[:.]"
```

## v1.1 fake percent regex (extends fake_precision_pattern)

```yaml
fake_percent_without_source:
  patterns:
    - "\\b\\d{2}\\s*процент(а|ов|)\\b"   # «80 процентов»
    - "\\b\\d{2}%\\b"                     # «80%»
    - "\\b\\d{1,2},\\d\\s*%\\b"          # «80,5%»
  exception_window: 200  # chars from match
  exception_patterns:    # если хотя бы одно в окне - OK
    - "по данным"
    - "согласно"
    - "исследование"
    - "опрос"
    - "из (\\d+|N) человек"
    - "n=\\d+"
    - "источник:"
  action_on_fail: "replace с verifiable claim или delete"
```

## v1.1 anglicism density check

```yaml
anglicism_density_check:
  catalog_ref: "references/anglicism-blocker-ru.md"
  threshold_per_1000_words: 5
  language_scope: "ru"
  action_on_fail: |
    Revision request с конкретным diff list:
    - line N: «<original>» → suggested «<RU replacement>»
    - count violations / words = density
    - продолжить только когда density ≤5
```

## v1.1 techjarg disclosure check

```yaml
techjarg_disclosure_check:
  catalog_ref: "references/techjarg-explain-list.md"
  scope: "first occurrence in text"
  disclosure_window: 200  # chars after first mention
  disclosure_patterns:
    - "{term}\\s*\\("                    # TERM (
    - "{term},\\s*это\\s"                # TERM, это
    - "{term},\\s*то\\sесть\\s"          # TERM, то есть
    - "{term}\\s*[--]\\s"                # TERM - (dash)
  action_on_fail: |
    «Term '{term}' упомянут без раскрытия. Добавь:
    {term} ({minimal_disclosure_from_catalog})»
```

## v1.1 section colon hard gate

```yaml
section_colon_hard:
  pattern: "^#{1,6}\\s+[^\\n]+:[^\\n]*$"  # markdown header with colon
  threshold: 1                              # ≥2 = FAIL (было WARN)
  action_on_fail: "Restructure headers без двоеточия. Pattern «Topic: subtitle» banned."
```

## v1.1 hyperbolic claims gate

```yaml
hyperbolic_claims:
  patterns:
    - "больше\\s*(чем|вс[её])\\s*любо\\w+"      # «больше чем любой»
    - "всегда\\s+работает"
    - "никогда\\s+не\\s+(подведёт|подводит)"
    - "100\\s*процент(а|ов|)"
    - "абсолютно\\s+(все|каждый)"
    - "идеально\\s+подходит"
  exception_window: 200
  exception_patterns:                            # нужен specific proof
    - "за\\s+\\d+\\s+(дней|месяцев|лет)"
    - "из\\s+\\d+\\s+(случаев|применений|тестов)"
    - "по\\s+данным"
  action_on_fail: "Replace на specific (n out of N) или delete claim"
```

## v1.1 subject lines diversity (newsletter only)

```yaml
subject_diversity:
  required_axes:    # минимум 2 разных из 3
    - "curiosity_gap"   # «… одна штука …»
    - "personal_anchor" # «Я … 4 месяца …»
    - "specific_outcome" # «$N/мес от …»
  detection:
    curiosity_gap_signal: ["одна штука", "что", "почему"]
    personal_anchor_signal: ["я ", "моя", "мой"]
    specific_outcome_signal: ["\\$", "₽", "\\d+\\s*(подписчик|клиент|рилз)"]
  action_on_fail: "Re-generate 3 subjects тестирующие 3 РАЗНЫХ axes"
```

## v1.1 Voice Fidelity Gate hardened

```yaml
voice_fidelity_gate:
  mandatory_corpus_file: "examples/gold-standard-{subject_name}-longform.md"
  min_corpus_word_count: 3000
  min_examples_count: 3
  action_on_fail: "STOP PIPELINE с message о corpus requirement (см. 03-write.md Pass 0)"
  no_silent_warning_override: true   # v1.1: запрет «WARN продолжаем»
```

## v1.1 hook quality gate

```yaml
hook_quality_gate:
  checks:
    - "no anglicisms from catalog в hook"
    - "≤12 words"
    - "contains 1 of: counter-intuitive | personal_anchor | specific_outcome"
    - "passes Scroller Pass 2.3 3-second test"
  action_on_fail: "regenerate hook через references/hook-patterns-longform.md"
```

## v1.1 abstract claim detector (для Skeptic Pass 2.1)

```yaml
abstract_claim_signals:
  patterns:
    - "работа(ю|е)т\\s+(в\\s)?слепую"
    - "не\\s+запомина(ет|ют)"
    - "превраща(ет|ются)\\s+в"
    - "стандарт\\s+качества"        # без specifying what standard
    - "по\\s+своей\\s+сути"
    - "по\\s+определению"
    - "буквально"                    # vague intensifier
  action_on_flag: "Skeptic Pass 2.1 mandatory revision - replace с specific evidence или delete"
```

## v1.1 anti-self-eval enforcement

```yaml
anti_self_eval:
  forbidden_pass_outputs:
    - "PASS"               # без structured findings
    - "9/9 PASS"           # без per-question evidence
    - "all checks passed"  # без list
  required_pass_output_format: "YAML с структурированными findings + severity"
  action_on_violation: "FAIL Pass с message «simulated not executed. Re-run with criterion checks.»"
```

## Activation

`04-review.md` Pass 1 после loading config.md также loads этот extension. Каждый gate из этого файла применяется как hard fail (если type=hard) или WARN (если type=warning), указано в каждом gate.

## Memory cross-refs

- - driver для anti_self_eval section
- - driver для anglicism + techjarg sections
- - driver для hyperbolic + abstract sections