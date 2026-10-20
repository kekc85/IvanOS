#!/usr/bin/env bash
# selftest для chunk-review-gate.py — ПЕРЕПРОВЕРКА улик (анти-фабрикация), не trust-the-flag.
# Создаёт РЕАЛЬНЫЕ рендеры (ffmpeg 1080x1920) + привязку по md5; негативы бьют по фабрикации.
# Exit 0 = все тесты прошли. Требует ffmpeg (есть, как в golden-run).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/chunk-review-gate.py"
PASS=0; FAIL=0
expect() { if [ "$2" = "$3" ]; then echo "  v $1 (exit $3)"; PASS=$((PASS+1)); else echo "  x $1: ждали $2, получили $3"; FAIL=$((FAIL+1)); fi; }
md5q() { if command -v md5 >/dev/null 2>&1; then md5 -q "$1"; else md5sum "$1" | cut -d' ' -f1; fi; }

# стаб layout-contract-check (формат-канон) — в selftest не гоняем реальный CV, проверяем проводку слоя
STUBDIR="$(mktemp -d)"; printf '#!/usr/bin/env bash\nexit 0\n' > "$STUBDIR/layout-ok.sh"
printf '#!/usr/bin/env bash\nexit 2\n' > "$STUBDIR/layout-fail.sh"; chmod +x "$STUBDIR"/*.sh
export CHUNK_GATE_LAYOUT_CMD="bash $STUBDIR/layout-ok.sh"

write_decon() {
cat > "$1/deconstruction.md" <<'EOF'
| t_start | t_end | frame | layout | shows | motion | text | sfx | block | bench |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | f.jpg | split | a | video | none | - | - | ★h |
| 1.0 | 2.0 | f.jpg | split | a | video | none | - | - | - |
| 2.0 | 3.0 | f.jpg | split | a | video | none | - | - | - |
| 3.0 | 4.0 | f.jpg | full-ui | b | video | none | - | - | ★s |
| 4.0 | 5.0 | f.jpg | full-ui | b | video | none | - | - | - |
| 5.0 | 6.0 | f.jpg | full-ui | b | video | none | - | - | - |
EOF
}

full_chunk() {  # <dir> — полный нефабрикуемый чанк: реальный рендер + привязка md5 + содержательная панель
  local d="$1"; mkdir -p "$d"
  ffmpeg -v error -f lavfi -i color=c=black:s=1080x1920:d=1 -pix_fmt yuv420p -y "$d/render.mp4" 2>/dev/null
  for i in 0 1 2 3 4 5 6 7 8 9; do echo x > "$d/f$i.jpg"; done
  echo x > "$d/pair_hook.png"
  local R; R="$(md5q "$d/render.mp4")"
  echo "{\"verdict\":\"PASS\",\"render_md5\":\"$R\"}" > "$d/audit-verdict.json"
  echo '{"verdict":"PASS","matched_blocks":["K3-overlap-card-avatar","A18-title-strap-caps"]}' > "$d/plan-conformance.json"
  echo '{"verdict":"PASS","anchors":["A","B","C"],"pairs":[{"label":"hook","contact_sheet":"pair_hook.png"}]}' > "$d/benchmark-verdict.json"
  python3 - "$d/.critic-verdict.json" "$R" <<'PY'
import json,sys
out=sys.argv[1]; rmd5=sys.argv[2]
cats=["subtitles","avatar","ui","transitions","typography","color","layout","broll","sfx","dynamics"]
axes=[{"axis":c,"verdict":"PASS","frame":"f%d.jpg"%i,
       "note":"Сверка %s vs конкурент и эталон покадрово: соответствует планке, дефектов H1-H8 нет."%c}
      for i,c in enumerate(cats)]
json.dump({"verdict":"PASS","benchmark_reel":"DYPgTzuSilc","render_md5":rmd5,"axes":axes},open(out,"w"))
PY
  printf 'Отчёт по куску целиком: side-by-side our|конкурент|эталон, контакт-лист pair_hook.png, все слои L0-L6 проверены покадрово, дефектов нет. %s\n' "$(printf 'x%.0s' $(seq 1 240))" > "$d/report.md"
}

mk_project() { local R="$1"; mkdir -p "$R"; write_decon "$R";
  echo '{"avatar_mode":"half","seam_y":960,"content_dynamic":"video"}' > "$R/contract.json";
  full_chunk "$R/_chunks/chunk_0"; full_chunk "$R/_chunks/chunk_1"; }

# --- HAPPY ---
T1="$(mktemp -d)"; mk_project "$T1"
python3 "$GATE" "$T1" >/dev/null 2>&1; expect "happy: 2 реально отревьюенных куска -> PASS" 0 $?

# --- NEG 1 → PENDING: непостроенный кусок (нет render.mp4) НЕ FAIL (инкрементальный воркфлоу) ---
T2="$(mktemp -d)"; mk_project "$T2"; rm -f "$T2/_chunks/chunk_1/render.mp4"
python3 "$GATE" "$T2" >/dev/null 2>&1; expect "pending: непостроенный кусок -> exit 0 (не FAIL)" 0 $?

# --- NEG 2: stale-md5 (вердикт критика не на этом рендере = фабрикация/старый) ---
T3="$(mktemp -d)"; mk_project "$T3"
python3 - "$T3/_chunks/chunk_0/.critic-verdict.json" <<'PY'
import json,sys;p=sys.argv[1];d=json.load(open(p));d["render_md5"]="deadbeefdeadbeef";json.dump(d,open(p,"w"))
PY
python3 "$GATE" "$T3" >/dev/null 2>&1; expect "neg: stale md5 критика -> FAIL" 1 $?

# --- NEG 3: пустые оси панели (trust-the-flag фабрикация) ---
T4="$(mktemp -d)"; mk_project "$T4"
R="$(md5q "$T4/_chunks/chunk_0/render.mp4")"
echo "{\"verdict\":\"PASS\",\"benchmark_reel\":\"x\",\"render_md5\":\"$R\",\"axes\":[{\"axis\":\"a\"},{\"axis\":\"b\"}]}" > "$T4/_chunks/chunk_0/.critic-verdict.json"
python3 "$GATE" "$T4" >/dev/null 2>&1; expect "neg: пустые/несодержательные оси -> FAIL" 1 $?

# --- NEG 4: нет контакт-PNG бенчмарка (прогон не делался) ---
T5="$(mktemp -d)"; mk_project "$T5"; rm -f "$T5/_chunks/chunk_1/pair_hook.png"
python3 "$GATE" "$T5" >/dev/null 2>&1; expect "neg: нет pair_*.png -> FAIL" 1 $?

# --- NEG 5: plan-conformance без matched_blocks (соответствие плану не считалось) ---
T6="$(mktemp -d)"; mk_project "$T6"
echo '{"verdict":"PASS"}' > "$T6/_chunks/chunk_0/plan-conformance.json"
python3 "$GATE" "$T6" >/dev/null 2>&1; expect "neg: plan без matched_blocks -> FAIL" 1 $?

# --- NEG 6: нет contract.json (формат-канон не объявлен) -> FAIL ---
T7="$(mktemp -d)"; mk_project "$T7"; rm -f "$T7/contract.json"
python3 "$GATE" "$T7" >/dev/null 2>&1; expect "neg: нет contract.json (формат-канон) -> FAIL" 1 $?

# --- NEG 7: layout-contract FAIL (пропорция/рамка/окклюзия не по канону) -> FAIL ---
T8="$(mktemp -d)"; mk_project "$T8"
CHUNK_GATE_LAYOUT_CMD="bash $STUBDIR/layout-fail.sh" python3 "$GATE" "$T8" >/dev/null 2>&1; expect "neg: layout-contract FAIL (формат мимо канона) -> FAIL" 1 $?

rm -rf "$T1" "$T2" "$T3" "$T4" "$T5" "$T6" "$T7" "$T8" "$STUBDIR"
echo "  ---"
echo "  chunk-review-gate selftest: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
