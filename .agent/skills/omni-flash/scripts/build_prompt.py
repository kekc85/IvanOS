#!/usr/bin/env python3
"""Build a Gemini Omni Flash (Google Flow) restyle prompt for a talking-head clip.

5-part structure (Omni Flash best practice): Goal / Input role / Scene / Motion / Constraints.
Two modes:
  clean  - keep me photoreal, only add graphics + kinetic accent words + synced captions around me
  energy - restyle the whole frame (paper-cutout / mixed-media collage / stop-motion feel)

Hard constraints baked into BOTH modes (from project rules):
  - preserve source audio and voice exactly
  - 9:16 vertical, never change aspect ratio / never stretch
  - captions and kinetic words never overlap the face zone
  - keep lip movement and timing in sync with the source

Usage:
  build_prompt.py --mode clean  --spoken "текст речи дословно" [--style "..."] [--captions on|off]
  build_prompt.py --mode energy --spoken "текст речи дословно" [--style "bold paper-cutout collage"]
Outputs the prompt to stdout.
"""
import argparse
import sys

COMMON_CONSTRAINTS = (
    "Constraints: keep my voice and the original audio exactly as in the source. "
    "Keep my lip movement, gestures and timing perfectly in sync with the source. "
    "Output 9:16 vertical at the SAME resolution and aspect ratio as the input - "
    "do NOT crop, stretch, zoom or change the aspect ratio. "
    "All on-screen text, captions and kinetic words must stay OUT of the face zone "
    "(place them in the upper third or lower third, never over my face)."
)

CLEAN = (
    "Goal: edit my talking-head clip into an energetic social video while keeping me looking exactly like myself.\n"
    "Input role: use the uploaded video as the editing reference - keep my real footage as the base layer.\n"
    "Scene: keep me photorealistic and untouched - do NOT restyle, repaint or stylize my face or body. "
    "Around me add tasteful motion-design graphic inserts, collage stickers, hand-drawn doodles and arrows{style}.\n"
    "Motion: add aggressive kinetic typography - massive bold accent words popping up one by one exactly in sync with my speech, "
    "highlighted on colored tape, with subtle camera shake on emphasis.{captions}\n"
    + COMMON_CONSTRAINTS
)

ENERGY = (
    "Goal: restyle my talking-head clip into a bold animated edit.\n"
    "Input role: use the uploaded video as the motion + structure reference - keep my movements and timing the same.\n"
    "Scene: restyle the WHOLE video as {style} with a stop-motion animation feel. "
    "Cut me out as a high-contrast silhouette with a rough paper-cutout edge, over a background of bold flat colors "
    "(red, acid yellow, black) with crumpled paper textures, newspaper scraps and halftone dots.\n"
    "Motion: aggressive kinetic typography - massive bold words popping up one by one exactly in sync with my speech, "
    "accent words highlighted on colored tape; collage stickers, flat emoji with drop shadows; "
    "subtle glitch, chromatic aberration and choppy 12fps stop-motion movement.{captions}\n"
    + COMMON_CONSTRAINTS
)


def build(mode: str, spoken: str, style: str, captions: bool) -> str:
    cap = ""
    if captions and spoken.strip():
        cap = f' The spoken words are, in order: "{spoken.strip()}".'
    if mode == "clean":
        style_frag = f", styled as: {style}" if style else ""
        return CLEAN.format(style=style_frag, captions=cap)
    if mode == "energy":
        style_frag = style if style else "a bold mixed-media newspaper-cutout collage"
        return ENERGY.format(style=style_frag, captions=cap)
    raise SystemExit(f"unknown mode: {mode} (use clean|energy)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["clean", "energy"])
    ap.add_argument("--spoken", default="", help="дословный текст речи для синхро-субтитров")
    ap.add_argument("--style", default="", help="стиль-бриф (energy: тема рестайла; clean: тема графики)")
    ap.add_argument("--captions", default="on", choices=["on", "off"])
    a = ap.parse_args()
    sys.stdout.write(build(a.mode, a.spoken, a.style, a.captions == "on"))


if __name__ == "__main__":
    main()