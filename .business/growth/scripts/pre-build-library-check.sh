#!/bin/bash
# pre-build-library-check.sh — mandatory library inventory check before authoring new composition
# Usage: bash pre-build-library-check.sh [search-keyword]
#
# Prevents the recurring failure: building примитивы from scratch когда library has ready blocks.
# Created: 2026-05-27 after showcase v2 failure (built simple terminal mock когда O3/B15/G23 already existed)

KEYWORD="${1:-}"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  PRE-BUILD LIBRARY INVENTORY CHECK"
echo "═══════════════════════════════════════════════════════════════"
echo ""

LIB="$HOME/.business/growth/assets/motion-blocks"

echo "→ Total blocks in library: $(find $LIB -type d -name '[A-Z][0-9]*' | wc -l | tr -d ' ')"
echo ""

echo "→ Rourke-prompted blocks (Tier 1 for high visual depth):"
echo "  Path: $LIB/<family>/<block>/"
echo ""
echo "  | Block | Family | Description |"
echo "  |---|---|---|"
echo "  | O3 | character | Claude Character Upload — Claude UI + character drag + 5 cards 3D scatter (20s) |"
echo "  | B15 | 3d | 3D Cinematic Carousel — 5 panels rotating cylinder, gold borders, Velvet Standard (5.5s) |"
echo "  | O4 | character | Instagram Follow Explosion — IG profile + 8 Reels burst 3D spin (5.5s) |"
echo "  | C9 | particles | Fan Videos Circular Orbit — 5 portrait cards arc sweep into pentagon (6s) |"
echo "  | A17 | typography | Kinetic Word Reveal — multi-scene, 3 accent colors, dot indicators (variable) |"
echo "  | G23 | ui-mocks | Finder Template Library — REC badge + 47 thumbnails grid + scroll (38s) |"
echo "  | J4 | captions | Twitter Post Cards — 2 cards drift + like elastic spring + count increment (custom) |"
echo "  | O5 | character | Plane Flight Route Map — airplane arc + avatar + landmarks + frosted card (custom) |"
echo ""

echo "→ 9 academic families (v4.0 taxonomy):"
echo "  F-AP Animation Principles → $LIB/A-typography/ + B-3d-objects/"
echo "  F-DZ Design fundamentals → A-typography (15) + J-captions (4)"
echo "  F-CH Character animation → O-character-storytelling (5)"
echo "  F-3D 3D animation → B-3d-objects (13) + E-lighting-material (5)"
echo "  F-CP Compositing → C-particles-dataviz (9 partial) + D-camera-transitions (11) + F-mixed-media (5)"
echo "  F-UI UI/UX motion → G-ui-mocks (9)"
echo "  F-VX VFX/effects → C-particles-dataviz (9) + E-lighting-material (5)"
echo "  F-IL Illustration → L-hand-drawn (3)"
echo "  F-PR Procedural → N-replicator (1) + P-niche-signature (2)"
echo ""

if [ -n "$KEYWORD" ]; then
  echo "→ Search results for '$KEYWORD':"
  grep -rli "$KEYWORD" $LIB --include="README.md" 2>/dev/null | head -10 | while read f; do
    BLOCK=$(basename $(dirname "$f"))
    echo "  → $BLOCK ($(dirname $f | sed "s|$LIB/||"))"
  done
  echo ""
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  DECISION POINT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Before building NEW composition from scratch:"
echo "  1. Check if existing Rourke-prompted block fits (8 above)"
echo "  2. Check if composing 2-3 existing blocks fits the brief"
echo "  3. ONLY если ничего не подходит → build new + add to library"
echo ""
echo "  Memory: feedback_library_first_before_build"
echo "  Catalog: ~/.business/growth/motion-vocabulary-v4.md"
echo ""
echo "═══════════════════════════════════════════════════════════════"
