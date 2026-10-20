#!/usr/bin/env bash
# selftest для skeleton-derive.py — happy + negative + edge + smoke по реальным деконструкциям.
# Фаза 1 «montage skeleton binding». Запускать после любой правки. Exit 0 = все тесты прошли.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DERIVE="$HERE/skeleton-derive.py"
CORPUS="$HOME/.business/growth/materials/reel-design-corpus"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

PASS=0; FAIL=0
ok()   { echo "  v $1"; PASS=$((PASS+1)); }
bad()  { echo "  x $1"; FAIL=$((FAIL+1)); }
expect_exit() { # <name> <expected> <actual>
  if [ "$2" = "$3" ]; then ok "$1 (exit $3)"; else bad "$1: ждали exit $2, получили $3"; fi
}

valid_table() {
cat > "$1" <<'EOF'
# deconstruction
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.5 | frames/f1.jpg | full-head | спикер, хук влетает | push-in | title:ОН СЛИЛ ВСЁ | whoosh | A18-title-strap-caps | ★hook |
| 0.5 | 1.0 | frames/f2.jpg | full-head | спикер, титр держится | static | title:ОН СЛИЛ ВСЁ | - | A18-title-strap-caps | - |
| 1.0 | 3.0 | frames/f3.jpg | split | верх = демо тула, низ спикер | video | caption:вот что он сделал | click | K3-overlap-card-avatar | ★showcase |
| 3.0 | 9.0 | frames/f4.jpg | full-ui | экран тула, ряд моделей, глоу | push-in | caption:выбираешь модель | - | F5-ai-model-icon-row | ★ui-demo |
| 9.0 | 16.0 | frames/f5.jpg | full-broll | репозиторий, файлы появляются | video | none | ding | G24-repo-file-list | - |
| 16.0 | 24.0 | frames/f6.jpg | split | результат-сайт + спикер реагирует | cursor-trace | caption:за 8 секунд | - | K3-overlap-card-avatar | ★payoff |
| 24.0 | 28.0 | frames/f7.jpg | full-head | спикер, призыв | static | title:напиши СЛОВО | riser | A18-title-strap-caps | ★cta |
EOF
}

PY="python3"

# --- HAPPY ---
valid_table "$T/ok.md"
$PY "$DERIVE" "$T/ok.md" --out "$T/ok.json" >/dev/null 2>&1
rc=$?
expect_exit "happy: валидная деконструкция -> derive" 0 $rc

if [ -f "$T/ok.json" ]; then ok "happy: scene-skeleton.json создан"; else bad "happy: JSON не создан"; fi

# n_beats == 7
NB=$($PY -c "import json;print(json.load(open('$T/ok.json'))['n_beats'])" 2>/dev/null)
[ "$NB" = "7" ] && ok "happy: n_beats=7" || bad "happy: n_beats=$NB (ждали 7)"

# duration == 28.0 (последний t_end)
DUR=$($PY -c "import json;print(json.load(open('$T/ok.json'))['duration'])" 2>/dev/null)
[ "$DUR" = "28.0" ] && ok "happy: duration=28.0" || bad "happy: duration=$DUR (ждали 28.0)"

# все layout в enum
ENUMOK=$($PY - "$T/ok.json" <<'PYEOF'
import json,sys
ENUM={"full-demo","split","full-ui","full-head","anchor-rotate"}
d=json.load(open(sys.argv[1]))
bad=[b for b in d["beats"] if b["layout"] not in ENUM]
print("BAD" if bad else "OK")
PYEOF
)
[ "$ENUMOK" = "OK" ] && ok "happy: все layout в enum" || bad "happy: layout вне enum"

# первый + последний avatar_role = bookend
BOOK=$($PY - "$T/ok.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]));b=d["beats"]
print("OK" if b[0]["avatar_role"]=="bookend" and b[-1]["avatar_role"]=="bookend" else "BAD")
PYEOF
)
[ "$BOOK" = "OK" ] && ok "happy: первый+последний avatar_role=bookend" || bad "happy: bookend не выставлен"

# средний бит (layout!=anchor-rotate, не bench-hook/cta) -> absent. Бит i=4 (full-broll, bench=-) должен быть absent.
MID=$($PY - "$T/ok.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]));b=d["beats"]
mid=[x for x in b if x["i"] not in (0,len(b)-1) and x["layout"]!="anchor-rotate" and not (x.get("bench") or "")]
print("OK" if mid and all(x["avatar_role"]=="absent" for x in mid) else "BAD")
PYEOF
)
[ "$MID" = "OK" ] && ok "happy: средний non-anchor бит -> avatar_role=absent" || bad "happy: средний бит не absent"

# default out = <dir>/scene-skeleton.json
rm -f "$T/scene-skeleton.json"
$PY "$DERIVE" "$T/ok.md" >/dev/null 2>&1
[ -f "$T/scene-skeleton.json" ] && ok "happy: дефолтный out=<dir>/scene-skeleton.json" || bad "happy: дефолтный out не создан"

# --- NEGATIVE 1: нет файла ---
$PY "$DERIVE" "$T/NETU.md" >/dev/null 2>&1
expect_exit "negative: нет файла -> ошибка" 1 $?

# --- NEGATIVE 2: файл без таблицы (свободный текст) ---
printf '# просто текст\nникакой таблицы тут нет\n' > "$T/notable.md"
$PY "$DERIVE" "$T/notable.md" --out "$T/notable.json" >/dev/null 2>&1
expect_exit "negative: файл без таблицы -> ошибка" 1 $?

# --- EDGE: неизвестный layout нормализуется (warning, не падает) ---
cat > "$T/edge.md" <<'EOF'
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.5 | f.jpg | full-head | хук | push-in | title:X | - | - | ★hook |
| 0.5 | 2.0 | f.jpg | полноэкранный экран браузера | демо | какое-то-движение | none | - | - | - |
| 2.0 | 4.0 | f.jpg | full-head | cta | static | title:Y | - | - | ★cta |
EOF
$PY "$DERIVE" "$T/edge.md" --out "$T/edge.json" >/dev/null 2>&1
rc=$?
expect_exit "edge: неизвестный layout -> не падает" 0 $rc
if [ -f "$T/edge.json" ]; then
  W=$($PY -c "import json;d=json.load(open('$T/edge.json'));print(len(d.get('warnings',[])))" 2>/dev/null)
  [ "${W:-0}" -ge 1 ] && ok "edge: warning про неизвестный layout есть ($W)" || bad "edge: warning не добавлен"
  EL=$($PY -c "import json;d=json.load(open('$T/edge.json'));print(d['beats'][1]['layout'])" 2>/dev/null)
  [ "$EL" = "full-head" ] && ok "edge: неизвестный layout -> default full-head" || bad "edge: layout=$EL (ждали full-head)"
else
  bad "edge: JSON не создан"
fi

# --- M1 REGRESSION: middle-бит с СОСТАВНОЙ bench '★showcase-hook' -> НЕ bookend ---
# Дефект M1: bookend давался по in-подстроке (hook/cta) даже в середине -> говорящая
# голова протаскивалась в середину. Фикс: bench-bookend только при ТОЧНОМ равенстве токену.
cat > "$T/m1.md" <<'EOF'
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | f.jpg | full-head | хук | push-in | title:X | - | A18-title-strap-caps | ★hook |
| 1.0 | 3.0 | f.jpg | split | демо тула | video | none | - | K3-overlap-card-avatar | ★showcase-hook |
| 3.0 | 6.0 | f.jpg | full-ui | экран | push-in | none | - | F5-ai-model-icon-row | ★ui-demo |
| 6.0 | 9.0 | f.jpg | full-head | cta | static | title:Y | - | A18-title-strap-caps | ★cta |
EOF
$PY "$DERIVE" "$T/m1.md" --out "$T/m1.json" >/dev/null 2>&1
expect_exit "M1: составной bench -> derive не падает" 0 $?
M1ROLE=$($PY - "$T/m1.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]));b=d["beats"]
# бит i=1 (middle, bench '★showcase-hook') НЕ должен быть bookend
print(b[1]["avatar_role"])
PYEOF
)
[ "$M1ROLE" != "bookend" ] && ok "M1: middle '★showcase-hook' -> avatar_role='$M1ROLE' (НЕ bookend)" || bad "M1: middle '★showcase-hook' стал bookend (дефект вернулся)"
# bench строго '★hook' на краевом бите -> bookend (и так bookend как edge, но проверим exact-match не сломал)
M1ROLE0=$($PY -c "import json;print(json.load(open('$T/m1.json'))['beats'][0]['avatar_role'])" 2>/dev/null)
[ "$M1ROLE0" = "bookend" ] && ok "M1: краевой '★hook' -> bookend (exact-match живой)" || bad "M1: краевой bench-bookend сломан"

# --- SMOKE: реальные деконструкции конкурентов (могут быть НЕ табличными) ---
for f in 2026-06-14-DX_6bSDTWqM.md 2026-06-14-DYPgTzuSilc.md; do
  P="$CORPUS/$f"
  if [ ! -f "$P" ]; then echo "  - smoke $f: файла нет, пропуск"; continue; fi
  OUT="$($PY "$DERIVE" "$P" --out "$T/smoke_$f.json" 2>&1)"
  rc=$?
  if [ "$rc" = "0" ]; then
    NB=$($PY -c "import json;print(json.load(open('$T/smoke_$f.json'))['n_beats'])" 2>/dev/null)
    ok "smoke $f: табличная, n_beats=$NB"
  else
    # exit 1 = не табличная, должна быть ПОНЯТНАЯ причина (не стектрейс)
    if echo "$OUT" | grep -qi "Traceback"; then
      bad "smoke $f: упал стектрейсом (не понятная ошибка)"
    else
      ok "smoke $f: не табличная, понятная причина (exit 1)"
    fi
  fi
done

echo "  ---"
echo "  skeleton-derive selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
