# AUDIO ADDENDUM — `motion-element` skill (slots after Phase 2, before lint)

Appendable as-is. Extends Phases 0-7 with frame-accurate sound design synced to the GSAP timeline. Core leverage: the timeline already holds the exact second of every motion event, so a build script emits a deterministic SFX cue list — sound lands frame-accurate, never nudged by hand.

---

## PHASE 2.5 — SOUND DESIGN

Runs **between Phase 2 (author HyperFrames composition)** and **Phase 3 (lint/inspect)**. Skipped entirely when `--mute`. Gated behind `--with-audio` (default ON for Reels; see triggers §5).

**Inputs:** authored `index.html` with a GSAP timeline + labels, `sfx-map.json`, a chosen music-bed mood, optional VO track.
**Output:** the same `index.html` with `<audio>` tags injected on dedicated track-indices + (when ducking/mastering needed) an FFmpeg post-step recipe written to `audio-post.sh`.

### Steps

**2.5.1 — Tag motion events.** Author annotates each element that triggers a sound. No native `data-sfx` exists in HyperFrames — this is a thin build-script convention this skill adds.
```html
<div class="card"   data-sfx="impact" data-sfx-at="s2-card-in" data-sfx-gain="0.9"></div>
<h1  class="kicker" data-sfx="whoosh"></h1>
```
Author drops a timeline **label at the exact accent tween** (authoritative timestamp source):
```js
tl.add("s2-card-in", 2.4);
tl.from(".card", { y: 60, opacity: 0, ease: "back.out" }, "s2-card-in");
```

**2.5.2 — Build the SFX cue list.** `build-sfx-cues.mjs` seeks the page in headless Chrome (same engine `inspect` uses), reads `tl.labels`, resolves each tag to a timestamp:
- **Option A (preferred):** `data-sfx-at` → `tl.labels[label]` — the label *is* the motion event's time. Use whenever the punch is mid-tween.
- **Option B (fallback):** parse the element's own `data-start` (resolve `"clipId + N"` by walking the id graph). Less precise — mount time, not accent frame.

Emits `sfx-cues.json` = `[{file, atSeconds, gain}]`, sorted by time. Snapshot it so renders are reproducible.

**2.5.3 — Attach the music bed.** Pre-bake once with FFmpeg (trim to comp length + fade), then drop the result in as a normal `<audio>` so HyperFrames mixes VO + SFX over it natively:
```bash
ffmpeg -i music.mp3 -t 30 -af "afade=t=in:st=0:d=1.5, afade=t=out:st=28:d=2" bed_30s.wav
```

**2.5.4 — Inject SFX as native `<audio>` (default path, zero FFmpeg).** One tag per cue, each on its own `data-track-index` so overlaps are free:
```js
let idx = 30;
const tags = cues.map(c =>
  `<audio src="${c.file}" data-start="${c.atSeconds.toFixed(3)}" `
+ `data-track-index="${idx++}" data-volume="${c.gain}"></audio>`).join('\n');
// splice into index.html before </body>
```

**2.5.5 — Duck + master (FFmpeg post-step, only when needed).** Native mixing is sum-of-static-volumes — no fades, no sidechain, no normalization. When the brief needs ducking under VO or a loudness master, render the composition to `base.mp4` first, then:
```bash
ffmpeg -i bed_30s.wav -i vo.wav \
 -filter_complex "[1:a]asplit=2[vo][key];\
   [0:a][key]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[duck];\
   [duck][vo]amix=inputs=2:normalize=0[mix];\
   [mix]loudnorm=I=-12:TP=-1:LRA=11[out]" \
 -map "[out]" master.wav
# then mux master.wav back over the silent/visual render
```
`normalize=0` is mandatory (else FFmpeg divides by input count and the bed goes quiet). `dropout_transition=0` stops level pumping. Cheaper deterministic alternative to sidechain: scripted `volume=enable='between(t,2.1,2.6)':volume=0.3` envelopes generated straight from `sfx-cues.json` (you already know every event time).

### Native HyperFrames vs FFmpeg post-step

| Capability | Native HF | FFmpeg post |
|---|---|---|
| Multiple audio tracks mixed in one render | ✅ one `<audio>` per `data-track-index` | — |
| Static per-clip volume, trim (`data-media-start`), delayed start | ✅ | — |
| Inject SFX at timeline-derived timestamps | ✅ write `<audio>` from cue list | optional `adelay`+`amix` |
| Per-frame freq-band reactivity | ✅ `extract-audio-data.py` | — |
| Discrete beat/onset timestamps | ❌ | librosa / aubio (pre-bake) |
| Fade in/out, trim-with-fade on bed | ❌ | `afade` |
| Sidechain ducking under VO/SFX | ❌ | `sidechaincompress` |
| Loudness normalize / final master | ❌ | `loudnorm` / `amix normalize=0` |

> Never call `audio.play()` from GSAP — the framework owns playback; GSAP only animates visuals.

### Optional 2.5.b — Beat-sync (when music-led)
HyperFrames' `extract-audio-data.py` gives per-frame RMS + 16 bands (continuous reactivity), **not** discrete onsets. For "caption slam lands on the kick," pre-bake real beats with librosa ($0):
```python
import librosa, json, sys
y, sr = librosa.load(sys.argv[1])
tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
json.dump({"tempo": float(tempo),
  "beats": librosa.frames_to_time(frames, sr=sr).round(3).tolist(),
  "onsets": librosa.onset.onset_detect(y=y, sr=sr, units='time').round(3).tolist()},
  open("beats.json","w"))
```
Feed `beats.json` back into motion (snap accents / place tweens at beat times) **and** into 2.5.2's cue list (emit `tick`/`impact` per beat). One analysis, motion accents and SFX land on the identical grid.

---

## sfx-map CONFIG

`sfx-map.json` — event tag → file + gain + offset. Lives in the skill root; per-project overrides allowed.

```json
{
  "version": "1.0",
  "fps": 30,
  "vocabulary": {
    "click":      { "file": "sfx/click.wav",      "gain": 0.85, "offset": 0.00 },
    "whoosh":     { "file": "sfx/whoosh.wav",      "gain": 0.80, "offset": -0.10 },
    "pop":        { "file": "sfx/pop.wav",         "gain": 0.80, "offset": 0.00 },
    "impact":     { "file": "sfx/impact.wav",      "gain": 0.95, "offset": 0.00 },
    "riser":      { "file": "sfx/riser.wav",       "gain": 0.85, "offset": -1.50 },
    "tick":       { "file": "sfx/tick.wav",        "gain": 0.75, "offset": 0.00 },
    "ding":       { "file": "sfx/ding.wav",        "gain": 0.85, "offset": 0.00 },
    "swipe":      { "file": "sfx/swipe.wav",       "gain": 0.80, "offset": -0.07 },
    "coin":       { "file": "sfx/coin.wav",        "gain": 0.90, "offset": 0.00 },
    "typewriter": { "file": "sfx/typewriter.wav",  "gain": 0.70, "offset": 0.00 },
    "error":      { "file": "sfx/error.wav",       "gain": 0.80, "offset": 0.00 }
  }
}
```
- `gain` = `data-volume` written into the injected `<audio>` (0–1, relative to bed).
- `offset` = seconds added to the resolved timestamp. **Anticipatory sounds lead** (`whoosh`/`riser`/`swipe` have negative offset — start before the hit, peak on it). Impacts/clicks = `0` (land exactly on hit frame).

### Default sound profile per v1.0 template

`{bed, key SFX events, payoff, duck note}` — starting defaults; the SFX→motion table governs extra events. One impact per beat, ≤1 whoosh per ~3s, one drop per video on the payoff.

| Template | Bed (mood, level) | Key SFX events | Payoff | Duck |
|---|---|---|---|---|
| **comment-pop** | light/curious, −15 dB | `pop` per comment appear; soft `tick` on reply snap | punchline → single `impact` + bed lift | −7 dB under VO |
| **count-up-ticker** | rising tension, drop on final number | `tick` per increment (pitch ramps); `riser` last ~1.5s; `impact`+sub-boom on final | landed number; pre-drop gap 2–3f before final | −5 dB during tick run |
| **code-terminal** | techy/glitch ambient, −16 dB | `typewriter` per char (cap ~10/s, thin if faster); `click` on run; `ding`/`error` on output | green check → `ding` + small `impact` | −6 dB under VO; keystrokes high-band |
| **before-after-wipe** | builds across "before", `riser` into wipe | `whoosh` ON wipe (start 3f early); `impact` on "after"; optional `ding` sparkle | the "after" reveal | −6 dB under VO; one whoosh only |
| **kinetic-caption** | rhythmic, clear beat, drop on key line | `tick`/`click` per emphasized word (not every word if dense); `impact` on punch line | hook/CTA synced to drop | words quantized to beat; SFX +1–2 dB |
| **ui-comparison-bar** | steady, builds to winning bar | `pop` per bar appear; `tick` as bar fills (length-proportional); `impact`+`ding` on winner; soft `error` thud on loser | winner highlight → `impact` + lift | −6 dB under VO; fills proportional |
| **chat-bubbles** | light messaging, −15 dB | `pop` per incoming bubble; `tick` on typing-indicator dots; `ding` on the key/reply bubble | the punch reply bubble → `impact` | −7 dB under VO; alternate pop pitch L/R sides |
| **scribble-callout** | playful/sketch, −15 dB | `swipe`/`whoosh` as the scribble draws on; soft `pop` on the circled word | the highlighted target → `ding` or small `impact` | −6 dB under VO; one whoosh per draw-on |
| **screen-zoom-punch** | tension build into the zoom | `riser` into the zoom (ends on punch frame); `impact`+sub on the zoom-snap; `whoosh` if it's also a cut | the zoomed detail → `impact` (loudest) | bed near-silent 2–4f pre-zoom (pre-drop gap) |
| **price-odometer** | rising, drop on final price | `coin`/`clink` per digit roll (pitch ramps); `riser` last ~1s; `impact`+`coin` flourish on final price | landed price → loudest non-VO event +6 dB | −5 dB during roll; coin high/mid-band so it cuts |

---

## ASSET PIPELINE

**Integrate first — 2 free, scriptable, zero-attribution sources** (both safe for monetized creator content):

1. **Pixabay Audio — primary.** Pixabay Content License = de-facto CC0, commercial OK, no attribution, no royalty. **Public REST API** (free key). Covers *both* SFX and music beds → one key closes almost the whole starter pack + all bed moods. Limits: 100 req/60 s, results must be cached 24h, no systematic mass downloads.
2. **Freesound (CC0 filter) — secondary, for SFX depth.** Mixed-license DB — **must** filter `filter=license:"Creative Commons 0"` to get attribution-free only. APIv2 preview mp3 (128–256k, enough for short SFX) via token key, no OAuth; original quality needs OAuth (500 dl/day). Use for richer impact / tick / typewriter / coin / glitch variation.

**Architecture:** Pixabay default for everything → Freesound CC0 as fallback/enrichment for SFX categories needing variety. Optionally seed a Mixkit pack once (no API, no attribution, scrape).
**Exclude:** BBC SFX (non-commercial), Uppbeat/Zapsplat/Incompetech/Chosic (attribution on free), YT Audio Library/FMA (no API).

**Starter SFX pack taxonomy** (all covered by Pixabay CC0 + Freesound CC0):

| Category | Fires on | Query |
|---|---|---|
| click | UI press, element appear | `ui click` / `button click` |
| whoosh / transition | scene change, text fly-in | `whoosh transition swoosh` |
| pop | comment/bubble surface | `pop bubble` |
| impact / boom | climax, accent hit | `cinematic impact boom hit` |
| riser / swell | build before payoff | `riser swell build up` |
| tick | counter, list step | `tick clock counter` |
| ding / notification | confirm, success | `notification ding bell` |
| swipe | slide change | `swipe slide` |
| coin / clink | $-ticker, income | `coin cash money clink` |
| typewriter | code/terminal typing | `typewriter keyboard typing` |
| error / glitch | error, glitch accent | `error glitch digital` |

**Folder layout under the skill:**
```
motion-element/
├── sfx-map.json
├── assets/
│   ├── sfx/        click.wav whoosh.wav pop.wav impact.wav riser.wav
│   │               tick.wav ding.wav swipe.wav coin.wav typewriter.wav error.wav
│   ├── beds/       energetic-tech.mp3 cinematic.mp3 lofi.mp3 corporate-uplift.mp3 tension.mp3
│   └── LICENSES.md  # source + license per file (CC0 only); regenerated by the fetch script
└── scripts/
    ├── fetch-audio.mjs     # Pixabay→Freesound, writes assets/ + LICENSES.md
    ├── build-sfx-cues.mjs  # timeline labels → sfx-cues.json
    ├── beats.py            # librosa beats/onsets → beats.json
    └── audio-post.sh       # generated FFmpeg duck/master recipe
```

**Music-bed by mood** (all Pixabay CC0, full-length, no attribution):

| Mood | Where it plays | Query |
|---|---|---|
| energetic / tech | hook, dynamic tutorial | `upbeat tech electronic energetic` |
| cinematic | storytelling, before/after | `cinematic epic inspiring` |
| lo-fi | calm teaching, background | `lofi chill beats` |
| corporate-uplift | product, case, offer | `corporate uplifting motivational` |
| tension | problem, build-up | `tension suspense dark` |

---

## AUDIO QUALITY GATES (add to the skill's gate list)

Each emits a one-line Evidence entry (value + source frame/file), same as existing gates.

- **AG-1 Loudness.** Integrated −14 LUFS default (music-led); push to −11/−12 LUFS for VO-led intelligibility. **True peak −1 dBTP hard ceiling.** Prioritize 200 Hz–5 kHz clarity (phone speakers roll off <200 Hz). Evidence: `loudnorm`/ffmpeg measured I + TP.
- **AG-2 Ducking present.** When VO exists, bed ducks −6 to −9 dB under it (attack ~10 ms, release 250–400 ms); −3 to −6 dB under prominent SFX. VO stays the most intelligible sustained element.
- **AG-3 Sound-off readable.** Burned-in captions for ALL spoken words; meaning carried by color/motion/checkmarks. No load-bearing info in audio only ("listen for the answer" = FAIL). ~70 %+ watched muted.
- **AG-4 No over-whooshing.** ≤1 whoosh per ~3 s; never two consecutive cuts both whooshed; one impact per beat (no two impacts within ~150 ms = flam); one drop per video on the payoff.
- **AG-5 Determinism.** `sfx-cues.json` + `beats.json` + `audio-data.json` all pre-baked and committed before render. No Web Audio API, no runtime analysis, no `Math.random()`/`Date.now()` in audio timing. Re-run `build-sfx-cues.mjs` → byte-identical cue list. Reactivity rides the GSAP timeline via `tl.call(draw, [], frame/fps)`, seek-driven.
- **AG-6 License-clean.** Каждый ассет (лицензии фиксируй в `assets/LICENSES.md`, создаётся при первом ассете) - CC0 / no-attribution (Pixabay or Freesound CC0-filter). Any attribution-required or non-commercial source = FAIL.

---

## NEW TRIGGERS + FLAGS

**Flags:** `--with-audio` (run Phase 2.5; default ON for Reels), `--mute` (skip Phase 2.5; ship silent), `--bed <mood>` (energetic-tech | cinematic | lofi | corporate-uplift | tension), `--no-duck` (skip FFmpeg post-step, native mix only), `--beat-sync` (run librosa beats + snap accents).

**RU triggers:** «добавь звук к анимации», «озвучь моушн», «звуковой дизайн под этот элемент», «синкни звук под анимацию», «подложи музыку и эффекты», «саунд-дизайн рилза», «звук в бит», «озвучка моушн-графики».

**EN triggers:** "add sound to this motion", "sound design for the overlay", "sync SFX to the animation", "score this reel", "add a music bed + sfx", "beat-synced audio", "make it land on the beat".

---

## UPDATED OUTPUT (Phase 7)

The rendered element now ships with **baked audio**:
```
~/Desktop/motion-elements/{date}-{slug}/
├── {slug}.mp4            # final, baked audio (bed + VO + SFX, ducked + mastered)
├── {slug}-muted.mp4      # silent variant for editors who add their own sound
├── {slug}.mov            # transparent overlay variant (unchanged from Phase 5; carries audio if requested)
├── sfx-cues.json         # the deterministic cue list (reproducibility)
├── beats.json            # present only if --beat-sync
└── LICENSES.md           # CC0 provenance of every audio asset used
```
Flat folder, no subdirs (drag-drop one move). `--mute` ships only the `-muted.mp4`. The muted variant is always produced alongside the baked one so editors can drop the element onto an existing soundtrack without fighting baked SFX.