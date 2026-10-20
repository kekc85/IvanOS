# Research Index - Tweet Skill

> Pointer к research base.

## Location


## Structure

```
2026-05-28-tweet-skill-research/
├── per-author/                      # 21 EN авторов с 12-парам schema
│   ├── B1 vibe coding/
│   │   ├── en-alex-finn.md          (#1 direct конкурент, $97 Skool)
│   │   ├── en-riley-brown.md        (vibe coding mobile)
│   │   └── en-nate-herk-x.md        (n8n agents)
│   ├── B2 X core/
│   │   ├── en-hormozi.md            (spiky / PAIPS punchline)
│   │   ├── en-levels.md             (build-in-public / Stripe screenshot)
│   │   ├── en-marc-lou.md           (MRR ritual / "Just ship it")
│   │   └── en-butcher.md            (aphorism compression / median 9 words)
│   ├── B3 Aphorism + community/
│   │   ├── en-naval.md              (eternal aphorism)
│   │   ├── en-isenberg.md           ("$X/mo idea")
│   │   └── en-sanchez.md            (contrarian community)
│   ├── B4 REUSE + X-layer/
│   │   ├── en-welsh-x.md            (GOLD #1, 5-12-3 rule)
│   │   ├── en-koe-x.md              (APAG rule)
│   │   ├── en-acosta-x.md           (6-part anatomy)
│   │   ├── en-bloom-x.md            (Named-Principle, Parent Time 18 tweets verbatim)
│   │   └── en-cole-x.md             (7 thread templates verbatim)
│   ├── B5 Niche/
│   │   ├── en-iman-gadzhi.md        (naked aphorism)
│   │   └── en-rowan-cheung.md       (AI-NEWS + avatar pipeline match)
│   └── B6 Rising young viral/
│       ├── en-jack-friks.md         (day-counter)
│       ├── en-yacine.md             (parallel anaphora)
│       ├── en-brett-malinowski.md   (meta-authority frame)
│       └── en-ras-mic.md            (frustration-as-flex)
├── qa-gate.md                       # Step 0.5 - L1+L2+L3 verdict PASS
├── synthesis-light.md               # Step 0.6 - cross-author + hook bank + автора positioning
└── (no full INDEX.md created - synthesis-light combines INDEX role)
```

## Total stats

- **21 EN авторов** in 6 buckets
- **~314 verbatim posts** with 12-параметровой schema each
- **15 hook patterns** (8 base + 7 new MECE-collapsed)
- **4 dominant skeletons** (Welsh PAIPS / Bloom Named-Principle / Cole 7 templates / Cheung AI-NEWS)
- **5 voice clusters** (aphorism / paips-story / spiky / build-in-public / idea-drop)

## How `tweet` skill uses this base

| Workflow stage | Uses |
|---|---|
| `02-structure.md` Step 1 | `templates/*.md` (которые reference per-author files) |
| `02-structure.md` Step 2 | `references/viral-hooks-2026-x.md` (extracted из research) |
| `03-write.md` Pass 0 | NOT directly - uses `references/_voice-TEMPLATE.md` (которая reference research) |
| `04-review.md` Stage 4 Layer 3 | NOT directly - uses `synthesis-light.md` patterns |

## Caveats

- X paywall 402 throughout research - fallback на ThreadReader / TweetHunter / archive sites / WebSearch snippets
- Engagement metrics partial (bookmarks/RT/likes недоступны без auth)
- Naval 80% archive 2018-2022 (timeless aphorism OK, не для current trends)
- Acosta primarily LinkedIn (90%+) - её X output edge-case study

## QA verdict (qa-gate.md)

L1 Deterministic: **PASS** (all 21 files, anti-vagueness 0, sources 21/21)
L2 4 концепции: **PASS** (multi-perspective + pre-mortem + 90% calibration + adaptive)
L3 7 контуров: **PASS** (with реализуемость PARTIAL acknowledged)
Overall: **PASS** → proceed to Step 1 Strategy synthesis (already done) → Step 2 Build SKILL (this skill)