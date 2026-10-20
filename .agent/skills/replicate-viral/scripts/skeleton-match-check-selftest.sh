#!/usr/bin/env bash
# selftest для skeleton-match-check.py — happy + 3 negative + skip (AC5 спеки, Ф3).
# Запускать после любой правки гейта. Exit 0 = все тесты прошли.
# Гейт hard: exit 2 при FAIL, exit 0 при PASS/SKIP.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
CHK="$HERE/skeleton-match-check.py"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

PASS=0; FAIL=0
expect() { # <name> <expected_exit> <actual_exit>
  if [ "$2" = "$3" ]; then echo "  v $1 (exit $3)"; PASS=$((PASS+1));
  else echo "  x $1: ждали exit $2, получили $3"; FAIL=$((FAIL+1)); fi
}

# --- синтетический scene-skeleton.json: 5 битов, bookend/absent чередование ---
# bookend-full-head / absent-full-ui / absent-split / absent-full-demo / bookend-full-head
# (4 разных layout у скелета -> diversity >=3, монотон композиции = FAIL)
SKEL="$T/scene-skeleton.json"
cat > "$SKEL" <<'EOF'
{
 "source": "synthetic.md",
 "n_beats": 5,
 "duration": 6.0,
 "beats": [
  {"i":0,"t0":0.0,"t1":1.0,"layout":"full-head","avatar_role":"bookend"},
  {"i":1,"t0":1.0,"t1":2.5,"layout":"full-ui","avatar_role":"absent"},
  {"i":2,"t0":2.5,"t1":4.0,"layout":"split","avatar_role":"absent"},
  {"i":3,"t0":4.0,"t1":5.0,"layout":"full-demo","avatar_role":"absent"},
  {"i":4,"t0":5.0,"t1":6.0,"layout":"full-head","avatar_role":"bookend"}
 ]
}
EOF

# собранный HTML (пустышка — биты берём из --spec, html нужен только как путь)
HTML="$T/index.html"
echo "<html><body>built</body></html>" > "$HTML"

# --- HAPPY: спека с beats[] ТОЧНО по скелету -> PASS(0) ---
cat > "$T/ok.spec.json" <<'EOF'
{"scene_id":"ok","duration":6,"layers":[{"block":"K3-overlap-card-avatar"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-ui","t0":1.0,"t1":2.5},
  {"layout":"split","t0":2.5,"t1":4.0},
  {"layout":"full-demo","t0":4.0,"t1":5.0},
  {"layout":"full-head","t0":5.0,"t1":6.0}
 ]}
EOF
python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/ok.spec.json" --project "$T" >/dev/null 2>&1
expect "happy: композиция точно по скелету -> PASS" 0 $?

# --- MONOTONE FAIL: все 5 битов full-head -> exit 2 (анти-монотон + avatar-вне-bookend) ---
cat > "$T/mono.spec.json" <<'EOF'
{"scene_id":"mono","duration":6,"layers":[{"block":"O6-avatar-feathered-fill"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-head","t0":1.0,"t1":2.5},
  {"layout":"full-head","t0":2.5,"t1":4.0},
  {"layout":"full-head","t0":4.0,"t1":5.0},
  {"layout":"full-head","t0":5.0,"t1":6.0}
 ]}
EOF
python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/mono.spec.json" --project "$T" >/dev/null 2>&1
expect "monotone: 1 layout на всё -> FAIL" 2 $?

# --- AVATAR-EVERYWHERE FAIL: full-head на absent-бите (бит 2) -> exit 2 ---
cat > "$T/avatar.spec.json" <<'EOF'
{"scene_id":"avatar","duration":6,"layers":[{"block":"K3-overlap-card-avatar"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-ui","t0":1.0,"t1":2.5},
  {"layout":"full-head","t0":2.5,"t1":4.0},
  {"layout":"full-demo","t0":4.0,"t1":5.0},
  {"layout":"full-head","t0":5.0,"t1":6.0}
 ]}
EOF
python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/avatar.spec.json" --project "$T" >/dev/null 2>&1
expect "avatar-everywhere: full-head на absent-бите -> FAIL" 2 $?

# --- COUNT-MISMATCH FAIL: число битов != скелету (4 вместо 5) -> exit 2 ---
cat > "$T/count.spec.json" <<'EOF'
{"scene_id":"count","duration":6,"layers":[{"block":"K3-overlap-card-avatar"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-ui","t0":1.0,"t1":2.5},
  {"layout":"split","t0":2.5,"t1":4.0},
  {"layout":"full-head","t0":4.0,"t1":6.0}
 ]}
EOF
python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/count.spec.json" --project "$T" >/dev/null 2>&1
expect "count-mismatch: битов != скелету -> FAIL" 2 $?

# --- C2 REGRESSION: K3-блок (НЕ full-head layout) на absent-бите -> exit 2 ---
# Дефект C2: детектор смотрел только full-head/O6, K3-overlap-card-avatar (блок говорящей
# головы) протаскивал аватар на absent-битах. layout совпадает со скелетом (full-ui), но
# block=K3 на absent-бите 1 -> аватар-несущий -> FAIL.
cat > "$T/c2.spec.json" <<'EOF'
{"scene_id":"c2","duration":6,"layers":[{"block":"K3-overlap-card-avatar"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-ui","t0":1.0,"t1":2.5,"block":"K3-overlap-card-avatar"},
  {"layout":"split","t0":2.5,"t1":4.0},
  {"layout":"full-demo","t0":4.0,"t1":5.0},
  {"layout":"full-head","t0":5.0,"t1":6.0}
 ]}
EOF
out=$(python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/c2.spec.json" --project "$T" 2>&1); rc=$?
expect "C2: K3-блок на absent-бите -> FAIL" 2 "$rc"
case "$out" in
  *"бит 1"*аватар*|*"бит 1"*"K3"*) echo "  v C2: сообщение указывает на K3/аватар на бите 1"; PASS=$((PASS+1));;
  *) echo "  x C2: сообщение не указывает на K3-аватар: $out"; FAIL=$((FAIL+1));;
esac

# --- M2 REGRESSION: comp-бит без t0/t1 при скелете с длительностью -> exit 2 ---
# Дефект M2: бит без t0/t1 молча отключал проверку длительности (тихий PASS). Фикс: если
# у скелет-бита dur есть, а у comp-бита нет t0/t1 -> FAIL.
cat > "$T/m2.spec.json" <<'EOF'
{"scene_id":"m2","duration":6,"layers":[{"block":"K3-overlap-card-avatar"}],
 "beats":[
  {"layout":"full-head","t0":0.0,"t1":1.0},
  {"layout":"full-ui"},
  {"layout":"split","t0":2.5,"t1":4.0},
  {"layout":"full-demo","t0":4.0,"t1":5.0},
  {"layout":"full-head","t0":5.0,"t1":6.0}
 ]}
EOF
out=$(python3 "$CHK" --skeleton "$SKEL" --html "$HTML" --spec "$T/m2.spec.json" --project "$T" 2>&1); rc=$?
expect "M2: бит без t0/t1 при скелете с dur -> FAIL" 2 "$rc"
case "$out" in
  *"бит 1"*t0/t1*) echo "  v M2: сообщение указывает на отсутствие t0/t1 на бите 1"; PASS=$((PASS+1));;
  *) echo "  x M2: сообщение не про t0/t1: $out"; FAIL=$((FAIL+1));;
esac

# --- SKIP: нет скелета -> exit 0 (печать skip) ---
out=$(python3 "$CHK" --skeleton "$T/NOPE-skeleton.json" --html "$HTML" --spec "$T/ok.spec.json" --project "$T" 2>&1)
rc=$?
expect "skip: нет скелета -> exit 0" 0 "$rc"
case "$out" in
  *SKIP*) echo "  v skip: печать содержит SKIP"; PASS=$((PASS+1));;
  *) echo "  x skip: в выводе нет 'SKIP'"; FAIL=$((FAIL+1));;
esac

# --- C1 REGRESSION: selftest.sh CHECK 13 — деконструкция без скелета -> FAIL (не SKIP) ---
# Дефект C1: нет scene-skeleton.json -> CHECK 13 давал чистый SKIP, монтаж-биндинг опционален,
# монотон проходил мимо гейта. Фикс: если в проекте ЕСТЬ deconstruction.md, но НЕТ скелета,
# CHECK 13 даёт FAIL. Прогоняем РЕАЛЬНЫЙ selftest.sh на мини-проекте и проверяем сообщение.
SELFTEST="$HERE/selftest.sh"
if [ -f "$SELFTEST" ]; then
  C1P="$T/c1proj"; mkdir -p "$C1P"
  printf '# deconstruction\n| t_start | t_end |\n|---|---|\n| 0 | 1 |\n' > "$C1P/deconstruction.md"
  # запускаем selftest (он FAIL по многим причинам — проект пустой; нам важна строка C1)
  c1out=$(bash "$SELFTEST" "$C1P" 2>&1)
  case "$c1out" in
    *"скелет не выведен"*|*"монтаж-биндинг обязателен"*)
      echo "  v C1: деконструкция без скелета -> CHECK 13 FAIL (монтаж-биндинг обязателен)"; PASS=$((PASS+1));;
    *)
      echo "  x C1: CHECK 13 НЕ дал FAIL про скелет при наличии деконструкции (дефект вернулся)"; FAIL=$((FAIL+1));;
  esac
  # и НЕ должно быть чистого SKIP «нет ни скелета, ни деконструкции» при наличии деконструкции
  case "$c1out" in
    *"ни скелета, ни деконструкции"*) echo "  x C1: дал ложный чистый SKIP при наличии деконструкции"; FAIL=$((FAIL+1));;
    *) echo "  v C1: ложного чистого SKIP при наличии деконструкции нет"; PASS=$((PASS+1));;
  esac
  # контроль backward-compat: пустой проект БЕЗ деконструкции -> чистый SKIP (не C1-FAIL)
  C0P="$T/c0proj"; mkdir -p "$C0P"
  c0out=$(bash "$SELFTEST" "$C0P" 2>&1)
  case "$c0out" in
    *"скелет не выведен"*) echo "  x C1: проект БЕЗ деконструкции дал ложный C1-FAIL (сломан backward-compat)"; FAIL=$((FAIL+1));;
    *) echo "  v C1: проект без скелета и без деконструкции -> не C1-FAIL (backward-compat)"; PASS=$((PASS+1));;
  esac
else
  echo "  - C1: selftest.sh не найден рядом, C1-регрессия пропущена"
fi

echo "  ---"
echo "  skeleton-match-check selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
