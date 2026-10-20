#!/usr/bin/env bash
# report-gate-selftest.sh — happy/negative/edge для report-gate.py (гигиена хуков CLAUDE.md).
# Прогонять после любой правки report-gate.py. Exit 0 = все кейсы прошли.
set -uo pipefail
GATE="$(dirname "$0")/report-gate.py"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ck() { # ck <expect-rc> <label>
  local exp="$1" lbl="$2"; shift 2
  python3 "$GATE" "$@" >/dev/null 2>&1; local rc=$?
  if [ "$rc" -eq "$exp" ]; then echo "  ✓ $lbl (rc=$rc)"; pass=$((pass+1));
  else echo "  ✗ $lbl: ждал rc=$exp, получил rc=$rc"; fail=$((fail+1)); fi
}

# --- кейс 1 (legacy, edge): нет .phase-ledger, нет рендера → PASS (нечего принуждать) ---
P1="$TMP/legacy"; mkdir -p "$P1"
ck 0 "legacy без леджера и рендера = PASS" "$P1"

# --- кейс 2 (negative): фазы PASS в леджере, но отчётов фаз нет → FAIL ---
P2="$TMP/no-phase-reports"; mkdir -p "$P2/reports"
cat > "$P2/.phase-ledger.json" <<'J'
{"phases":{"Ф1":{"status":"PASS"},"Ф4":{"status":"PASS"},"Ф6":{"status":"MISS"}}}
J
ck 1 "PASS-фазы без отчётов = FAIL" "$P2"

# --- кейс 3 (happy): отчёты фаз есть, содержательны, ссылаются на реальный артефакт ---
P3="$TMP/ok-phase-reports"; mkdir -p "$P3/reports"
cat > "$P3/.phase-ledger.json" <<'J'
{"phases":{"Ф1":{"status":"PASS"},"Ф4":{"status":"PASS"}}}
J
echo "transcript stub" > "$P3/reports/art1.txt"
for s in f1 f4; do
  printf '📋 ФАЗА %s\nЧТО СДЕЛАЛ: stub содержательный отчёт фазы для проверки гейта длиной более двухсот символов, чтобы пройти порог MIN_PHASE и не считаться заглушкой при машинной перепроверке улик.\nУЛИКА: reports/art1.txt\nДАЛЬШЕ: next\n' "$s" > "$P3/reports/$s-report.md"
done
ck 0 "отчёты фаз содержательны + ссылка на артефакт = PASS" "$P3"

# --- кейс 4 (negative): есть рендер, но нет DELIVERY-REVIEW.md → FAIL ---
P4="$TMP/render-no-review"; mkdir -p "$P4/final"
printf 'fakemp4data%.0s' {1..200} > "$P4/final/reel.mp4"
ck 1 "рендер без DELIVERY-REVIEW = FAIL" "$P4" --render "$P4/final/reel.mp4"

# --- кейс 5 (negative): DELIVERY-REVIEW есть, но не хватает слоёв L0-L7 → FAIL ---
P5="$TMP/review-incomplete"; mkdir -p "$P5/reports" "$P5/final"
printf 'fakemp4data%.0s' {1..200} > "$P5/final/reel.mp4"
printf 'РЕВЬЮ ВЫДАЧИ только L0 L1 без остальных слоёв %s\nrender reel.mp4\n%.0s' "$(head -c 700 /dev/zero | tr '\0' 'x')" > "$P5/reports/DELIVERY-REVIEW.md"
ck 1 "DELIVERY-REVIEW без всех L0-L7 = FAIL" "$P5" --render "$P5/final/reel.mp4"

# --- кейс 6 (happy): полный DELIVERY-REVIEW (все слои + render + ≥9 строк панели + артефакт) → PASS ---
P6="$TMP/review-ok"; mkdir -p "$P6/reports" "$P6/final"
printf 'fakemp4data%.0s' {1..200} > "$P6/final/reel.mp4"
{
  echo "🎬 РЕВЬЮ НА ВЫДАЧЕ — review-ok — PASS"
  echo "render: final/reel.mp4"
  echo "Слои: L0 L1 L2 L3 L4 L5 L6 L7 — все пройдены."
  echo "панель L5 (категория | вердикт | якорь | заметка):"
  for c in субтитры аватар ui переходы типографика цвет раскладка broll sfx динамика; do
    echo "| $c | PASS | rpn | планка по montage-lexicon темп 0.5 смен/с соответствует эталону |"
  done
  echo "артефакт: final/reel.mp4"
} > "$P6/reports/DELIVERY-REVIEW.md"
ck 0 "полный DELIVERY-REVIEW = PASS" "$P6" --render "$P6/final/reel.mp4"

# --- кейс 7 (edge): usage без аргументов → rc=2 ---
ck 2 "без аргументов = rc2 (usage)"

echo ""
echo "report-gate-selftest: $pass прошло, $fail упало"
[ "$fail" -eq 0 ] && exit 0 || exit 1