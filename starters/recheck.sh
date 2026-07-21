#!/bin/sh
# starters/recheck.sh — scheduled floor re-run for every starter; a starter
# with a red floor flips to status: unavailable in starters/index.yaml
# until repaired (kill criteria as for packs).
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
QG="$ROOT/.agents/skills/quality-guardian/scripts"
VD="$ROOT/.agents/skills/visual-director/scripts"
fail=0
for dir in "$ROOT"/starters/*/; do
  id=$(basename "$dir")
  [ "$id" = "_candidates" ] && continue
  skel="$dir/skeleton"
  [ -d "$skel" ] || continue
  bash "$QG/check-placeholders.sh" "$skel" >/dev/null 2>&1 || { echo "FAIL $id: placeholders"; fail=1; }
  bash "$QG/check-token-usage.sh" "$skel" >/dev/null 2>&1 || { echo "FAIL $id: token usage"; fail=1; }
  bash "$VD/lint-ban-list.sh" "$skel" >/dev/null 2>&1 || { echo "FAIL $id: ban-list"; fail=1; }
  echo "checked $id"
done
[ "$fail" -eq 0 ] && echo "OK: all starters pass static floor" || echo "FAIL: see above"
exit "$fail"
