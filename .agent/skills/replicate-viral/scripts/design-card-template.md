---
id: <ingest-dir-id>
author: <handle>
platform: <IG | TikTok | YouTube Shorts | X>
views: <int>
duration_s: <float>
src_dims: <WxH>
subformat: <talking-head | split-screen | POV-faceless | avatar-news | screen-demo>
niche_fit: <core | adjacent | offniche>   # core = AI-tools/vibecoding/vibemarketing creator reel
analyzed: <YYYY-MM-DD>
---

# <author> — <short title>

> meta: views <N> · dur <s> · <subformat> · changes/sec <x> (avg <y>s/change)

## HOOK (first 2s, beat order)
- Pattern: <intrigue "кто-то слил" / number / question / bold claim / POV / demo-first>
- Beat order: <t0 …> → <t1 …>
- Verbal hook (transcript first line): "<…>"
- Visual hook: <what's on screen at 0.0–2.0s>

## A. FONTS (titles + subtitles)
- Title font: <family + weight>  | nearest free: <Anton / Montserrat 900 / Inter / Druk-alt / …>  | confidence: <high/med/flag>
- Subtitle font: <family + weight>  | nearest free: <…>  | confidence: <…>
- Stroke/treatment: <multi-shadow / box-plate / outline / none>; artifacts? <y/n>

## B. SUBTITLES (placement + treatment)
- Words on screen at once: <1 / 2-3 / 3-6 / phrase>
- Position band (of 1920h): <y≈… ; in safe-zone 300-1430? y/n>
- Color scheme: <mono white / white+accent / neon>; accent color: <…>; accent on <keyword/verb>
- Timing: <word-pop / karaoke / by-phrase / static>
- CAPS? <ALL / Title / sentence>
- Always-on or selective? <24/7 burned / selective by beat / none>

## C. OVERLAP / CLUTTER
- Element collisions observed: <none / …>
- Tiny/illegible elements: <none / e.g. small handle, watermark — note size>
- On-face text? <never / occasionally — where>

## D. EFFECTS / TRANSITIONS / DYNAMICS
- Cut/change pace: <changes/sec from cuts.txt> → <fast ~1/s | medium ~1/3s | calm ~1/5s+>
- Transition vocabulary: <whip-pan / smash-cut / zoom-punch / push / wipe / crossfade / glitch / parallax / none>
- Motion primitives: <push-in / ken-burns / text word-pop / cursor-trace / highlight-sweep / data-anim>
- Static stretches >1.5s? <none / where>

## E. CONTENT / HONESTY
- Claim type: <demo / news / tutorial / opinion>; specific tool names? <list>
- UI shown clean (logged-in, real output)? <y/n — note any error/empty states>
- Clickbait/unverifiable? <none / flag>

## F. STRUCTURE / LAYOUT (time-map)
- Layout rhythm (alternation): <e.g. 0-3 split · 3-8 full-screen UI · 8-12 talking-head · …>
- Dominant layout: <split / full-talking-head / full-Broll>
- Layout switches count: <n>  → <static-one-layout | alternating>

## B-ROLL
- What: <real screen UI / app icons / screencast / generated graphic / stock>
- Technique: <screen-record / mockup-render / zoom-on-content / icon-montage>

## SPEAKER
- Digital-twin or live? <live talking-head / AI avatar (HeyGen-style) / faceless POV / no speaker>
- Framing: <full-frame / split-bottom / corner-cam / none>

## SIGNATURE MOVE (what makes THIS reel land — 1-2 lines)
<the one design decision worth stealing or noting>

## REPLICATE / AVOID (for our pipeline)
- ✅ replicate: <…>
- ❌ avoid / differentiate: <…>