#!/usr/bin/env bash
# Селфтест гейта произношения tts-textlint.py (Ф4 шаг 1).
# Регрессия на PRONUNCIATION_MAP (FAIL на сыром англицизме), --apply (respell),
# чёрный список транслитов, и НЕ-ложные срабатывания (ChatGPT латиницей = PASS).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LINT="python3 $HERE/tts-textlint.py"
fails=0
n=0

# check NAME EXPECT_EXIT "text" -- проверяет exit-код линта
chk() {
  local name="$1" want="$2" text="$3"
  n=$((n+1))
  $LINT "$text" >/dev/null 2>&1
  local got=$?
  if [ "$got" != "$want" ]; then
    echo "FAIL[$n] $name: ждал exit=$want, получил $got"; fails=$((fails+1))
  else
    echo "ok  [$n] $name (exit=$got)"
  fi
}

# check_apply NAME "text" MUST_CONTAIN MUST_NOT_CONTAIN
chk_apply() {
  local name="$1" text="$2" must="$3" mustnot="$4"
  n=$((n+1))
  local out; out=$($LINT --apply "$text" 2>/dev/null)
  if ! grep -q "$must" <<<"$out"; then
    echo "FAIL[$n] $name: нет «$must» в --apply выходе"; fails=$((fails+1)); return
  fi
  if grep -q "$mustnot" <<<"$out"; then
    echo "FAIL[$n] $name: «$mustnot» осталось в --apply выходе"; fails=$((fails+1)); return
  fi
  echo "ok  [$n] $name (--apply respell)"
}

echo "== FAIL: сырой англицизм из реестра =="
chk "raw Lovable"  2 "Этот ИИ убил Lovable сегодня"
chk "raw Bolt"     2 "Он лучше чем Bolt"
chk "raw 3D"       2 "готовый 3D сайт"
chk "raw iOS"      2 "выложи в iOS"
chk "raw XR"       2 "и даже в XR"
chk "raw Claude"   2 "ставишь Claude Code"

echo "== FAIL: чёрный список кириллических транслитов =="
chk "translit gpt" 2 "открой чат джи пи ти"
chk "translit hg"  2 "генерим в хиггсфилд"

echo "== PASS: respelled / нейтральный текст =="
chk "respelled"    0 "Этот ИИ убил Ловэбл и Болт. Готовый три-дэ сайт"
chk "neutral"      0 "Простой русский текст без брендов"
chk "ChatGPT latin" 0 "спроси у ChatGPT ответ"

echo "== --apply: авто-respell + идемпотентность =="
chk_apply "apply Lovable" "убил Lovable и Bolt" "Ловэбл" "Lovable"
chk_apply "apply 3D"      "готовый 3D сайт"     "три-дэ" "3D"
# идемпотентность: applied текст линтуется в PASS
n=$((n+1))
applied=$($LINT --apply "убил Lovable, Bolt, 3D, iOS, XR" 2>/dev/null)
$LINT "$applied" >/dev/null 2>&1
if [ $? = 0 ]; then echo "ok  [$n] idempotent (applied → lint PASS)"; else echo "FAIL[$n] applied текст не проходит линт"; fails=$((fails+1)); fi

echo "== EDGE: граница слова (не матчить внутри слова) =="
chk "boundary inside" 0 "слово Болтливый и Курсорный"   # не Bolt/Cursor как подстрока

echo ""
if [ "$fails" = 0 ]; then echo "SELFTEST PASS ($n кейсов)"; exit 0
else echo "SELFTEST FAIL: $fails из $n"; exit 1; fi