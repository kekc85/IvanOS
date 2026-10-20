#!/usr/bin/env bash
# selftest для deconstruction-check.py — happy + 3 negative (AC3 спеки).
# Запускать после любой правки чека. Exit 0 = все 4 теста прошли.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHK="$HERE/deconstruction-check.py"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/frames"
for f in f1 f2 f3 f4 f5 f6 f7 f8 f9 f10; do echo x > "$T/frames/$f.jpg"; done

PASS=0; FAIL=0
expect() { # <name> <expected_exit> <actual_exit>
  if [ "$2" = "$3" ]; then echo "  v $1 (exit $3)"; PASS=$((PASS+1));
  else echo "  x $1: ждали exit $2, получили $3"; FAIL=$((FAIL+1)); fi
}

valid_table() {
cat > "$1" <<'EOF'
# deconstruction
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.5 | frames/f1.jpg | full-head | hook | push-in | title:X | whoosh | A18-title-strap-caps | ★hook |
| 0.5 | 1.0 | frames/f2.jpg | full-head | hold | static | title:X | - | A18-title-strap-caps | - |
| 1.0 | 1.5 | frames/f3.jpg | split | demo | video | none | - | K3-overlap-card-avatar | ★showcase |
| 1.5 | 2.0 | frames/f4.jpg | split | demo | video | none | - | K3-overlap-card-avatar | - |
| 2.0 | 2.5 | frames/f5.jpg | full-ui | ui | push-in | caption:Y | - | F5-ai-model-icon-row | ★ui |
| 2.5 | 3.0 | frames/f6.jpg | full-ui | ui | video | none | - | F5-ai-model-icon-row | - |
| 3.0 | 4.0 | frames/f7.jpg | split | payoff | video | caption:Z | ding | K3-overlap-card-avatar | ★payoff |
| 4.0 | 5.0 | frames/f8.jpg | split | payoff hold | video | none | - | K3-overlap-card-avatar | - |
| 5.0 | 6.0 | frames/f9.jpg | split | payoff end | video | none | - | K3-overlap-card-avatar | - |
EOF
}

# --- HAPPY ---
valid_table "$T/ok.md"
python3 "$CHK" "$T/ok.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "happy: валидная деконструкция -> PASS" 0 $?

# --- NEGATIVE 1: дыра в покрытии (выкинут бит 1.0-1.5) ---
valid_table "$T/gap.md"
grep -v 'frames/f3.jpg' "$T/ok.md" > "$T/gap.md"
python3 "$CHK" "$T/gap.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "negative: дыра в покрытии -> FAIL" 1 $?

# --- NEGATIVE 2: блок заявлен без кадра (выдуманный эффект) ---
valid_table "$T/noframe.md"
sed -i.bak 's#frames/f7.jpg#frames/MISSING.jpg#' "$T/noframe.md"
python3 "$CHK" "$T/noframe.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "negative: блок без кадра-улики -> FAIL" 1 $?

# --- NEGATIVE 3: несуществующий блок (выдуман) ---
valid_table "$T/badblock.md"
sed -i.bak 's#F5-ai-model-icon-row#Z99-fake-block#' "$T/badblock.md"
python3 "$CHK" "$T/badblock.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "negative: несуществующий блок -> FAIL" 1 $?

# --- NEGATIVE 4: неизвестный layout (не из enum) -> FAIL ---
valid_table "$T/badlayout.md"
sed -i.bak 's#| split | payoff |#| diagonal-wipe | payoff |#' "$T/badlayout.md"
python3 "$CHK" "$T/badlayout.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "negative: layout не из enum -> FAIL" 1 $?

# --- NEGATIVE 5: алиас full-demo принимается как валидный (full-demo→full-broll) ---
# Длинный full-demo бит, ВНЕ хук-окна и с ОДИНАКОВЫМ layout у соседей (нет смены
# раскладки) → зона НЕ динамична (full-broll ∉ DYNAMIC_LAYOUTS) → посекундный гейт молчит,
# а сам алиас full-demo валиден. Хук-окно первых 3с закрыто мелкими full-demo битами.
cat > "$T/alias.md" <<'EOF'
# deconstruction
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.5 | frames/f1.jpg | full-demo | hook broll | push-in | title:X | whoosh | - | ★hook |
| 0.5 | 1.0 | frames/f2.jpg | full-demo | broll | video | none | - | - | - |
| 1.0 | 1.5 | frames/f3.jpg | full-demo | broll | video | none | - | - | - |
| 1.5 | 2.0 | frames/f4.jpg | full-demo | broll | video | none | - | - | ★mid |
| 2.0 | 2.5 | frames/f5.jpg | full-demo | broll | video | none | - | - | - |
| 2.5 | 3.0 | frames/f6.jpg | full-demo | broll | video | none | - | - | - |
| 3.0 | 6.0 | frames/f7.jpg | full-demo | broll long | video | none | - | - | ★end |
EOF
python3 "$CHK" "$T/alias.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "alias: full-demo (статичная broll-зона) -> PASS" 0 $?

# --- NEGATIVE 6: длинный бит на ДИНАМИКЕ (split >1с) -> FAIL (посекундное правило) ---
cat > "$T/slowdyn.md" <<'EOF'
# deconstruction
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.5 | frames/f1.jpg | full-head | hook | push-in | title:X | whoosh | A18-title-strap-caps | ★hook |
| 0.5 | 1.0 | frames/f2.jpg | full-head | hold | static | title:X | - | A18-title-strap-caps | - |
| 1.0 | 1.5 | frames/f3.jpg | split | demo | video | none | - | K3-overlap-card-avatar | ★showcase |
| 1.5 | 5.0 | frames/f4.jpg | split | demo long | video | none | - | K3-overlap-card-avatar | ★payoff |
| 5.0 | 6.0 | frames/f5.jpg | split | demo end | video | none | - | K3-overlap-card-avatar | - |
EOF
python3 "$CHK" "$T/slowdyn.md" --project "$T" --duration 6 >/dev/null 2>&1
expect "negative: split-бит 3.5с на динамике -> FAIL" 1 $?

echo "  ---"
echo "  deconstruction-check selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]