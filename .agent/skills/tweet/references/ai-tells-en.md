# AI Tells EN catalog

> Phrases that signal AI-generated text. Auto-fail в `04-review.md` Stage 1 G6.
> Derived from research: 21 gold-standard EN авторов **never** use these.

## Tier 1 - Auto-fail (универсальные)

- delve / delves / delving
- tapestry
- in conclusion
- in summary
- to elaborate
- moreover
- furthermore
- additionally
- ensure / ensuring
- embark on a journey
- navigate the landscape
- in the realm of
- harness the power of
- unlock the potential
- pave the way
- shed light on
- delve into
- foster
- multifaceted
- nuanced

## Tier 2 - Warning (suspicious без context)

- it is worth noting
- it is important to
- it is essential to
- one must consider
- a deeper understanding
- comprehensive overview
- intricate
- robust
- streamline
- leverage (как verb, для inanimate things)
- ecosystem (когда не tech-specific)
- pivotal
- transformative
- revolutionary (когда не technology-specific)
- game-changer / game-changing

## Tier 3 - Voice red flags (часто AI)

- "Let's dive in"
- "Let's explore"
- "When it comes to..."
- "At the end of the day..."
- "Picture this:"
- "Imagine if..."
- "Here's the thing:"
- "The reality is..."
- "The truth is..."
- "It's no secret that..."
- "In today's fast-paced world..."

## Tier 4 - Structure tells (часто AI)

- Triple-list parallelism в каждом beat ("A, B, and C" repeatedly)
- Excessive em-dashes (memory `[[feedback-no-em-dash]]`)
- "However, X. Moreover, Y." conjunction pairs
- Closing summary tweet repeating main points
- "In essence" recap pattern

## How review uses this catalog

`04-review.md` Stage 1 G6:
- Tier 1 → fail (regex grep)
- Tier 2 → warning (manual review)
- Tier 3 → warning + suggestion
- Tier 4 → manual review

## What gold-standard EN authors DO instead

| AI-pattern | Gold-standard alternative |
|---|---|
| "delve into" | "look at" / "break down" |
| "comprehensive overview" | "everything you need to know" |
| "harness the power of" | "use" |
| "in conclusion" | (just stop - no closer needed) |
| "moreover" | "also" / "and" |
| "ensure you..." | "make sure" / "you need to" |
| "navigate the landscape" | "find your way" |

## Sources

- 21-author research (none use Tier 1 terms)
- авторский voice corpus (RU)
- Public discussions o AI-tells (Tweet Hunter / Welsh writing process)