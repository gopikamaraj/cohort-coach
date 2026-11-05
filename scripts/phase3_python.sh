#!/bin/sh
# Phase 3: every Python test directory, one pytest run each, one summary line per directory in $OUT.
# No paid API calls (recorded fixtures only). Run from the repo root.
PY=.venv/Scripts/python.exe
OUT="${TEMP}/phase3_python.txt"
: > "$OUT"
for d in ai api assistant channels chat cohort_chat cohort_run cohorts content data demo engine evals flows media modules papers papers_hub pilot_demo practice roles sheets_keep spoken sprites store usage speech; do
  [ -d "tests/$d" ] || { echo "SKIP $d (no directory)" >> "$OUT"; continue; }
  echo "START $d" >> "$OUT"
  $PY -m pytest "tests/$d" -q --no-header -p no:cacheprovider --maxfail=200 > "${TEMP}/phase3_$d.log" 2>&1
  echo "END $d: $(tail -1 "${TEMP}/phase3_$d.log")" >> "$OUT"
done
echo "START top-level" >> "$OUT"
$PY -m pytest tests/test_*.py -q --no-header -p no:cacheprovider > "${TEMP}/phase3_top.log" 2>&1
echo "END top-level: $(tail -1 "${TEMP}/phase3_top.log")" >> "$OUT"
echo done >> "$OUT"
