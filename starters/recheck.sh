#!/bin/sh
# starters/recheck.sh — static floor for every starter (factory-time
# verification; hosted browser checks D12/D13/D20 run on materialization).
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
QG="$ROOT/.agents/skills/quality-guardian/scripts"
VD="$ROOT/.agents/skills/visual-director/scripts"
RED=0
for d in "$ROOT"/starters/*/; do
  name=$(basename "$d")
  case "$name" in _*) continue;; esac
  [ -d "$d/skeleton" ] || continue
  for check in check-placeholders.sh check-token-usage.sh; do
    if ! bash "$QG/$check" "$d/skeleton" > /dev/null 2>&1; then
      echo "RED $name: $check"; RED=1
    fi
  done
  if ! bash "$VD/lint-ban-list.sh" "$d/skeleton" > /dev/null 2>&1; then
    echo "RED $name: lint-ban-list.sh"; RED=1
  fi
  echo "checked $name"
done
if [ "$RED" -eq 0 ]; then echo "OK: all starters pass static floor"; else
  echo "FAIL: starter floor red" >&2; fi
exit "$RED"
