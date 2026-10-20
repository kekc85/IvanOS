#!/usr/bin/env bash
# selftest для foreign-face-gate.py — 2 кейса (AC2):
#   (1) клип с РЕАЛЬНЫМ лицом в НЕ-avatar окне  -> FAIL (exit 2)  [чужой автор]
#   (2) чистый UI-клип без лиц, без avatar-окон -> PASS (exit 0)
#   (3) клип с лицом В avatar-окне              -> PASS (exit 0)  [двойник на месте]
#   (4) avatar-окно объявлено, но лица в нём НЕТ -> FAIL (exit 2)  [двойника нет]
# Лицо берём из реального портрета автора (Haar его детектит, проверено), кадр
# вставляется только в нужное временное окно. Нет портрета -> тест печатает SKIP
# для лице-несущих кейсов, но чистый PASS-кейс гоняется всегда.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/foreign-face-gate.py"
PORTRAIT="$HOME/<твой-сайт-проект>/assets/ivan-portrait.jpg"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
export FACE_MINSIZE=120 FACE_FPS=3

PASS=0; FAIL=0
expect() { if [ "$2" = "$3" ]; then echo "  v $1 (exit $3)"; PASS=$((PASS+1)); else echo "  x $1: ждали exit $2, получили $3"; FAIL=$((FAIL+1)); fi; }

# --- чистый UI-клип (без лиц): тёмный фон + панель + полосы (ffmpeg lavfi) ---
ffmpeg -y -v error -f lavfi -i "color=c=0x121620:s=1080x1920:d=6" \
  -vf "drawbox=x=80:y=300:w=920:h=900:color=0x222838:t=fill,drawbox=x=130:y=400:w=820:h=40:color=0x465a8c:t=fill" \
  -r 24 "$T/ui_clean.mp4" 2>/dev/null

# --- helper: собрать клип, где portrait-лицо показано в окне [a,b], остальное = UI ---
make_face_clip() {  # <out> <a> <b>
  local out="$1" a="$2" b="$3"
  # сегмент до окна (UI), сегмент с лицом, сегмент после (UI) — конкатим
  ffmpeg -y -v error -f lavfi -i "color=c=0x121620:s=1080x1920:d=$a" -r 24 "$T/p0.mp4" 2>/dev/null
  local fdur; fdur=$(python3 -c "print(max(0.5,$b-$a))")
  ffmpeg -y -v error -loop 1 -i "$PORTRAIT" -t "$fdur" \
     -vf "scale=720:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x121620" -r 24 "$T/pf.mp4" 2>/dev/null
  local tail; tail=$(python3 -c "print(max(0.5,6-$b))")
  ffmpeg -y -v error -f lavfi -i "color=c=0x121620:s=1080x1920:d=$tail" -r 24 "$T/p2.mp4" 2>/dev/null
  printf "file '%s'\nfile '%s'\nfile '%s'\n" "$T/p0.mp4" "$T/pf.mp4" "$T/p2.mp4" > "$T/list.txt"
  ffmpeg -y -v error -f concat -safe 0 -i "$T/list.txt" -r 24 "$out" 2>/dev/null
}

# spec helper
write_spec() {  # <path> <json-beats>
  cat > "$1" <<EOF
{ "scene_id":"t", "duration":6, "beats": $2 }
EOF
}

# === CASE 2 (PASS): чистый UI, нет avatar-окон, нет лиц ===
write_spec "$T/spec_ui.json" '[{"layout":"full-ui","t0":0,"t1":6}]'
python3 "$GATE" "$T/ui_clean.mp4" "$T/spec_ui.json" "$T" >/dev/null 2>&1
expect "PASS: чистый UI без лиц, нет avatar-окон" 0 $?

if [ ! -f "$PORTRAIT" ]; then
  echo "  ! SKIP лице-несущих кейсов: нет $PORTRAIT"
else
  # лицо в окне [1.5,3.0]
  make_face_clip "$T/face_15_30.mp4" 1.5 3.0

  # === CASE 1 (FAIL): лицо в окне [1.5,3.0], но avatar-окно объявлено [4.0,6.0] ===
  #     => лицо ВНЕ avatar-окна = чужой автор
  write_spec "$T/spec_far.json" '[{"layout":"full-ui","t0":0,"t1":4},{"layout":"full-head","t0":4,"t1":6}]'
  python3 "$GATE" "$T/face_15_30.mp4" "$T/spec_far.json" "$T" >/dev/null 2>&1
  expect "FAIL: лицо вне avatar-окна (чужой автор)" 2 $?

  # === CASE 3 (PASS): лицо в окне [1.5,3.0] И avatar-окно = [1.5,3.0] ===
  write_spec "$T/spec_match.json" '[{"layout":"full-ui","t0":0,"t1":1.5},{"layout":"full-head","t0":1.5,"t1":3.0},{"layout":"full-ui","t0":3.0,"t1":6}]'
  python3 "$GATE" "$T/face_15_30.mp4" "$T/spec_match.json" "$T" >/dev/null 2>&1
  expect "PASS: лицо ровно в avatar-окне (двойник на месте)" 0 $?

  # === CASE 4 (FAIL): avatar-окно [4.0,6.0] объявлено, но лиц там нет (лицо в 1.5-3.0) ===
  #     => двойника в окне нет. (тут лицо в 1.5-3.0 тоже вне окна -> сработает и A; для
  #      чистого теста B используем клип БЕЗ лица вовсе в avatar-окне)
  write_spec "$T/spec_empty.json" '[{"layout":"full-head","t0":4,"t1":6}]'
  python3 "$GATE" "$T/ui_clean.mp4" "$T/spec_empty.json" "$T" >/dev/null 2>&1
  expect "FAIL: avatar-окно без лица (двойника нет)" 2 $?
fi

echo "  ---"
echo "  foreign-face-gate selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
