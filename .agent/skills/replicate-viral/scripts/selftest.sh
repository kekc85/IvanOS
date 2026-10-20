#!/usr/bin/env bash
# selftest.sh — ЕДИНЫЙ РАННЕР ГЕЙТОВ replicate-viral
#
# ПОЧЕМУ ЭТОТ ФАЙЛ ПОЯВИЛСЯ по решению автора:
# SKILL.md ссылался на `scripts/selftest.sh` 19 раз, ERROR-REGISTER — 24 раза,
# через него были «вшиты» CHECK 0/1/2/2.5/2.6/3/4/5/6/8/11/13/14.
# Файла НЕ СУЩЕСТВОВАЛО. Значит НИ ОДНА из этих проверок никогда не запускалась:
# канон описывал воображаемую систему принуждения, а дефекты возвращались после
# каждой «починки» (класс «Повтор уже исправленного» — 148 браковок из 818).
# Диагноз и урок: memory/feedback_skill_rot_measured_prose_not_gates.md
#
# ПРИНЦИП: тут НЕТ новых проверок. Только вызов уже написанных гейтов, которые
# лежали осиротевшими. Работа была сделана — её никто не звал.
#
# Запуск:  bash scripts/selftest.sh            # все CHECK
#          bash scripts/selftest.sh --quick    # только быстрые (без scene-audit)
#          bash scripts/selftest.sh --list     # что вообще прогоняется
#
# Коды: 0 = все зелёные · 2 = хоть один FAIL (блокирует «готово»)

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# ── ЗАЩИТА ОТ РЕКУРСИИ (обязательна) ──────────────────────────────────────────
# skeleton-match-check-selftest.sh (C1/C0-регрессии) сам вызывает selftest.sh на
# мини-проекте. Пока файла не существовало, вызов молча пропускался. С появлением
# раннера получилась петля selftest → skeleton-selftest → selftest → … (поймано
# живьём по решению автора: ветвящийся каскад процессов). Флаг рвёт цикл.
if [ "${RV_SELFTEST_ACTIVE:-0}" = "1" ] && [ "${1:-}" = "" ]; then
  echo "  selftest.sh: вложенный вызов без проекта — SKIP (защита от рекурсии)"
  exit 0
fi
export RV_SELFTEST_ACTIVE=1

QUICK=0
LIST=0
PROJECT=""
for a in "$@"; do
  case "$a" in
    --quick) QUICK=1 ;;
    --list)  LIST=1 ;;
    -*)      ;;
    *)       [ -d "$a" ] && PROJECT="$a" ;;
  esac
done

# ── РЕЖИМ ПРОВЕРКИ ПРОЕКТА ────────────────────────────────────────────────────
# Контракт, который ожидают существующие тесты: `selftest.sh <project-dir>`
# проверяет КОНКРЕТНУЮ сборку, а не гоняет харнесс гейтов.
if [ -n "$PROJECT" ]; then
  echo "=========================================================="
  echo " selftest.sh — проверка проекта: $PROJECT"
  echo "=========================================================="
  P_FAIL=0
  # CHECK 13 — деконструкция есть, а скелета нет = FAIL (не SKIP).
  # Именно эту регрессию проверяет skeleton-match-check-selftest C1.
  DEC="$(ls "$PROJECT"/*deconstruction*.md "$PROJECT"/deconstruction.md 2>/dev/null | head -1)"
  SKEL="$(ls "$PROJECT"/*skeleton*.json 2>/dev/null | head -1)"
  if [ -n "$DEC" ] && [ -z "$SKEL" ]; then
    echo "  ❌ CHECK 13: скелет не выведен — деконструкция есть ($(basename "$DEC")),"
    echo "     а scene-skeleton.json НЕТ. Монтаж-биндинг обязателен: без скелета"
    echo "     раскладка донора не принуждается → монотонная говорящая голова."
    echo "     Гнать: python3 scripts/skeleton-derive.py"
    P_FAIL=1
  elif [ -n "$SKEL" ]; then
    echo "  ✅ CHECK 13: скелет на месте ($(basename "$SKEL"))"
  else
    echo "  CHECK 13: деконструкции нет — skeleton-match не проверяется (SKIP)"
  fi
  echo
  if [ "$P_FAIL" -gt 0 ]; then
    echo " ❌ FAIL — «готово» говорить НЕЛЬЗЯ"
    exit 2
  fi
  echo " ✅ проект прошёл проверки"
  exit 0
fi

PASS=0
FAIL=0
SKIP=0
FAILED_NAMES=""

run() {  # run <CHECK-id> <описание> <команда...>
  local id="$1"; shift
  local desc="$1"; shift
  if [ "$LIST" = "1" ]; then
    printf "  %-10s %s\n" "$id" "$desc"
    return 0
  fi
  # существует ли то, что зовём
  local target="$1"
  case "$target" in
    bash|python3) target="$2" ;;
  esac
  if [ ! -f "$target" ]; then
    printf "  ⚠️  %-10s SKIP (нет файла: %s)\n" "$id" "$target"
    SKIP=$((SKIP+1)); return 0
  fi
  local out
  out="$("$@" 2>&1)"
  local code=$?
  if [ $code -eq 0 ]; then
    printf "  ✅ %-10s %s\n" "$id" "$desc"
    PASS=$((PASS+1))
  else
    printf "  ❌ %-10s %s  (exit=%d)\n" "$id" "$desc" "$code"
    printf '%s\n' "$out" | tail -6 | sed 's/^/        /'
    FAIL=$((FAIL+1))
    FAILED_NAMES="${FAILED_NAMES}${id} "
  fi
}

echo "=========================================================="
echo " selftest.sh — гейты replicate-viral"
[ "$QUICK" = "1" ] && echo " режим: QUICK (без тяжёлых scene-audit/chunk)"
echo "=========================================================="
echo

echo "── Фазы и отчётность ──"
run "CHECK 0"  "phase-gate: полнота фаз из артефактов"      bash phase-gate-selftest.sh
run "CHECK 11" "report-gate: отчёт на каждую PASS-фазу"      bash report-gate-selftest.sh

echo "── Раскладка и скелет (1:1 с донором) ──"
run "CHECK 13" "skeleton-match: композиция == скелет донора" bash skeleton-match-check-selftest.sh
run "CHECK 13b" "skeleton-derive: деконструкция → скелет"    bash skeleton-derive-selftest.sh
run "CHECK 5"  "deconstruction-check: enum раскладки, бит<=1с" bash deconstruction-check-selftest.sh

echo "── Автор не должен протекать в наш выход ──"
run "CHECK 14" "foreign-face-gate: чужое лицо в выходе"      bash foreign-face-gate-selftest.sh
run "CHECK 14b" "source-vision: покадровое зрение (step=1)"  python3 source-vision-selftest.py

echo "── Субтитры ──"
run "CHECK 3"  "subtitle-cover: плашка, residual чужого текста" python3 subtitle-cover-selftest.py
run "CHECK 3c" "плашка КОНСИСТЕНТНА (не дышит) — правка 30.07" python3 subtitle-plate-consistency-test.py
run "CHECK 1"  "tts-textlint: транслиты брендов, омографы"   bash tts-textlint-selftest.sh

echo "── Дефекты рендера ──"
run "CHECK 9"  "render-defect-scan"                          python3 render-defect-scan-selftest.py

if [ "$QUICK" != "1" ]; then
  echo "── Тяжёлые (полный прогон) ──"
  run "CHECK 4"  "scene-audit: оси качества сцены"           bash scene-audit-selftest.sh
  run "CHECK 6"  "chunk-review-gate: слои L-FORMAT"          bash chunk-review-gate-selftest.sh
fi

if [ "$LIST" = "1" ]; then
  echo
  echo "(--list: ничего не запускалось)"
  exit 0
fi

echo
echo "=========================================================="
printf " ИТОГ: %d зелёных · %d красных · %d пропущено\n" "$PASS" "$FAIL" "$SKIP"
if [ "$FAIL" -gt 0 ]; then
  echo " ❌ FAIL: $FAILED_NAMES"
  echo " «готово» говорить НЕЛЬЗЯ — сначала в зелёное."
  echo "=========================================================="
  exit 2
fi
echo " ✅ Все гейты зелёные."
echo "=========================================================="
exit 0
