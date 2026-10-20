#!/usr/bin/env bash
# selftest для phase-gate.py — фокус на Higgsfield content-гейтах Ф4.5/Ф4.6 (AC3 по решению автора).
# Проверяем ИЗОЛИРОВАННО функции check_f45 / check_f46 (без полного конвейера): happy +
# negative по каждой оси (пусто / протухло / реюз / число!=сегментам). Exit 0 = все зелёные.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PG="$HERE/phase-gate.py"
T="$(mktemp -d)"
JOURNAL="$HOME/.claude/skills/replicate-viral/speaker-locations-journal.md"
proj_name="ffgate-self-$$"
cleanup() {
  rm -rf "$T"
  # снять ВСЕ тестовые строки ffgate-self-*, дописанные в общий журнал (не засорять)
  [ -f "$JOURNAL" ] && grep -q "ffgate-self-" "$JOURNAL" 2>/dev/null && \
    grep -v "ffgate-self-" "$JOURNAL" > "$JOURNAL.tmp$$" && mv "$JOURNAL.tmp$$" "$JOURNAL"
}
trap cleanup EXIT

PASS=0; FAIL=0
expect() { if [ "$2" = "$3" ]; then echo "  v $1"; PASS=$((PASS+1)); else echo "  x $1: ждали $2, получили $3"; FAIL=$((FAIL+1)); fi; }

# гоняем конкретную проверку через python-обёртку, печатаем PASS/MISS
runchk() {  # <proj> <func>  -> печатает PASS|MISS
  python3 - "$PG" "$1" "$2" <<'PY'
import importlib.util, json, os, sys
pg_path, proj, func = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("pg", pg_path)
pg = importlib.util.module_from_spec(spec); spec.loader.exec_module(pg)
m = json.load(open(os.path.join(proj, "project-meta.json")))
ok, ev = getattr(pg, func)(proj, m)
print("PASS" if ok else "MISS")
PY
}

# свежий журнал-строка с проектом, чтобы journal-проверка f46 не валила happy
mkproj() {  # <dir>
  mkdir -p "$1/higgsfield/wow" "$1/heygen"
}
big() { head -c 9000 /dev/urandom > "$1"; }   # >5КБ непустой "кадр"

ensure_journal() {
  if [ -f "$JOURNAL" ]; then
    grep -q "$proj_name" "$JOURNAL" 2>/dev/null || printf '| %s | %s | test | selftest | - | 0 | - |\n' "$(date +%F)" "$proj_name" >> "$JOURNAL"
  fi
}
ensure_journal

# ===== Ф4.5 wow-inserts =====
# HAPPY: непустые свежие вставки, нет соседей-реюза
P="$T/p45ok"; mkproj "$P"; big "$P/higgsfield/wow/insert1.png"; big "$P/higgsfield/wow/insert2.png"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name", "wow_inserts":"higgsfield/wow" }
EOF
expect "Ф4.5 happy: непустые свежие вставки -> PASS" PASS "$(runchk "$P" check_f45)"

# NEGATIVE: нет wow_inserts вообще
P="$T/p45miss"; mkproj "$P"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name" }
EOF
expect "Ф4.5 negative: нет вставок -> MISS" MISS "$(runchk "$P" check_f45)"

# NEGATIVE: вставка протухла (mtime год назад)
P="$T/p45stale"; mkproj "$P"; big "$P/higgsfield/wow/old.png"; touch -t 202501010101 "$P/higgsfield/wow/old.png"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name", "wow_inserts":"higgsfield/wow" }
EOF
expect "Ф4.5 negative: протухшая вставка -> MISS" MISS "$(runchk "$P" check_f45)"

# ===== Ф4.6 locations (Higgsfield i2i) =====
# HAPPY: 2 сегмента, 2 свежих непустых кадра, журнал есть
P="$T/p46ok"; mkproj "$P"; big "$P/heygen/look-1.jpg"; big "$P/heygen/look-2.jpg"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name",
  "segments":[{"beat":"hook","look_frame":"heygen/look-1.jpg"},{"beat":"cta","look_frame":"heygen/look-2.jpg"}] }
EOF
if [ -f "$JOURNAL" ]; then
  expect "Ф4.6 happy: 2 кадра=2 сегмента, свежие -> PASS" PASS "$(runchk "$P" check_f46)"
else
  echo "  ! Ф4.6 happy SKIP: нет журнала $JOURNAL"
fi

# NEGATIVE: кадров меньше чем сегментов
P="$T/p46count"; mkproj "$P"; big "$P/heygen/look-1.jpg"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name",
  "segments":[{"beat":"hook","look_frame":"heygen/look-1.jpg"},{"beat":"cta","look_frame":"heygen/look-2.jpg"}] }
EOF
expect "Ф4.6 negative: кадров < сегментов -> MISS" MISS "$(runchk "$P" check_f46)"

# NEGATIVE: пустышка-кадр (<5КБ)
P="$T/p46tiny"; mkproj "$P"; echo x > "$P/heygen/look-1.jpg"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name", "look_frame":"heygen/look-1.jpg" }
EOF
expect "Ф4.6 negative: пустышка-кадр <5КБ -> MISS" MISS "$(runchk "$P" check_f46)"

# NEGATIVE: протухший кадр (реюз прошлого ролика по mtime)
P="$T/p46stale"; mkproj "$P"; big "$P/heygen/look-1.jpg"; touch -t 202501010101 "$P/heygen/look-1.jpg"
cat > "$P/project-meta.json" <<EOF
{ "project":"$proj_name", "look_frame":"heygen/look-1.jpg" }
EOF
expect "Ф4.6 negative: протухший кадр -> MISS" MISS "$(runchk "$P" check_f46)"

# NEGATIVE: реюз кадра из СОСЕДНЕГО проекта (одинаковый md5)
PARENT="$T/reusebox"; mkdir -p "$PARENT/other/heygen" "$PARENT/cur/heygen"
big "$PARENT/other/heygen/look-1.jpg"; cp "$PARENT/other/heygen/look-1.jpg" "$PARENT/cur/heygen/look-1.jpg"
# свежий mtime обоим, чтобы сработал именно md5-реюз, а не stale
touch "$PARENT/other/heygen/look-1.jpg" "$PARENT/cur/heygen/look-1.jpg"
cat > "$PARENT/cur/project-meta.json" <<EOF
{ "project":"$proj_name", "look_frame":"heygen/look-1.jpg" }
EOF
expect "Ф4.6 negative: реюз кадра соседнего ролика (md5) -> MISS" MISS "$(runchk "$PARENT/cur" check_f46)"

echo "  ---"
echo "  phase-gate selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
