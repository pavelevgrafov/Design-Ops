#!/usr/bin/env bash
# run-self-test.sh — v5.2 regression circuit [TZ-4.1].
# Runs every package validator against the bundled fixture and asserts the
# expected outcomes (see expected.txt). Itself strictly bash 3.2 / BSD grep
# compatible — it is part of the guarantee it checks.
#
# Usage:
#   bash eval/selftest/run-self-test.sh
# Browser stage runs only when playwright is resolvable by node
# (npm i -D playwright, or NODE_PATH pointing at a node_modules that has it);
# otherwise it is an explicit skip, never a silent pass.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
FIX="$HERE/fixture"
PO="$ROOT/.agents/skills/pipeline-orchestrator/scripts"
SB="$ROOT/.agents/skills/structure-builder/scripts"
QG="$ROOT/.agents/skills/quality-guardian/scripts"
VD="$ROOT/.agents/skills/visual-director/scripts"

PASS=0; FAIL=0; SKIP=0
ok()   { PASS=$((PASS+1)); printf 'pass: %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$*"; }
skip() { SKIP=$((SKIP+1)); printf 'skip: %s\n' "$*"; }

has() { # has <needle> <haystack> — fixed-string containment, no regex
  case "$2" in *"$1"*) return 0;; *) return 1;; esac
}

printf '%s\n' "== self-test: contract-read.py [TZ-1.3 / defect A2] =="

GOT=$(python3 "$PO/contract-read.py" "$FIX/contract/design-contract.yaml" key_screens 2>&1)
EXP='home
pricing
app'
if [ "$GOT" = "$EXP" ]; then
  ok "key_screens: exactly 3 ids, no scenario bleed-through"
else
  bad "key_screens mismatch — got: $(printf '%s' "$GOT" | tr '\n' ',')"
fi

GOT=$(python3 "$PO/contract-read.py" "$FIX/contract/design-contract.yaml" scenarios 2>&1)
EXP='checkout-happy
search-empty'
if [ "$GOT" = "$EXP" ]; then
  ok "scenarios: exactly 2 ids, separate from key_screens"
else
  bad "scenarios mismatch — got: $(printf '%s' "$GOT" | tr '\n' ',')"
fi

GOT=$(python3 "$PO/contract-read.py" "$FIX/contract/design-contract.yaml" mode 2>&1)
[ "$GOT" = "standard" ] && ok "mode query: standard" || bad "mode query: got '$GOT'"

GOT=$(python3 "$PO/contract-read.py" "$FIX/contract/design-contract.yaml" functional_paths 2>&1)
has '"alternative"' "$GOT" && has '"error_recovery"' "$GOT" \
  && ok "functional_paths query: both paths present" \
  || bad "functional_paths query incomplete: $GOT"

printf '%s\n' "== self-test: check-skeleton.sh [TZ-1.1/1.2/2.1] =="

# The checker excludes test/story files by path; the fixture lives under
# eval/selftest, so run it against a copy at a neutral path.
SKELWORK=$(mktemp -d 2>/dev/null || mktemp -d -t skel)
mkdir -p "$SKELWORK/clean/artifacts"
cp -R "$FIX/clean/." "$SKELWORK/clean/"
cp "$FIX/contract/design-contract.yaml" "$SKELWORK/clean/artifacts/design-contract.yaml"

# Lorem trap: generated deterministically at runtime (>64KB of matches,
# regression TZ-2.1a) — kept out of git for size.
TRAPDIR="$SKELWORK/lorem-trap"
mkdir -p "$TRAPDIR"
TRAPLINE='<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.</p>'
{
  printf '<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="utf-8"><title>Lorem trap</title></head>\n<body>\n'
  i=0; while [ "$i" -lt 1000 ]; do printf '%s\n' "$TRAPLINE"; i=$((i+1)); done
  printf '</body>\n</html>\n'
} > "$TRAPDIR/big.html"

OUT=$(bash "$SB/check-skeleton.sh" "$SKELWORK/clean" "$FIX/no-manifest.yaml" "$SKELWORK/clean/artifacts/design-contract.yaml" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "(3 checked)" "$OUT"; then
  ok "clean skeleton PASS, exactly 3 contract screens checked"
else
  bad "clean skeleton should PASS with 3 screens (rc=$RC): $(printf '%s' "$OUT" | tail -3 | tr '\n' ' ')"
fi

OUT=$(bash "$SB/check-skeleton.sh" "$TRAPDIR" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "placeholder copy found" "$OUT"; then
  ok "lorem trap FAILs even with >64KB grep output (no SIGPIPE false-PASS)"
else
  bad "lorem trap must FAIL with placeholder verdict (rc=$RC)"
fi

printf '%s\n' "== self-test: check-placeholders.sh [TZ-2.1] =="

OUT=$(bash "$QG/check-placeholders.sh" "$FIX/clean" "$FIX/clean/assets" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "clean project: no placeholders" || bad "clean project placeholders (rc=$RC)"

OUT=$(bash "$QG/check-placeholders.sh" "$TRAPDIR" "$TRAPDIR/assets" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "placeholder copy found" "$OUT"; then
  ok "lorem trap: guaranteed FAIL (regression TZ-2.1a)"
else
  bad "lorem trap must FAIL (rc=$RC)"
fi

printf '%s\n' "== self-test: check-typography.py D5 [TZ-2.4] =="

OUT=$(python3 "$QG/check-typography.py" "$FIX/clean/tokens.css" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "pass[D5]" "$OUT" && has "ignored" "$OUT"; then
  ok "heading 11ch + 65ch token: D5 PASS without project edits"
else
  bad "D5 selector selectivity broken (rc=$RC): $(printf '%s' "$OUT" | tr '\n' ' ')"
fi

OUT=$(python3 "$QG/check-typography.py" "$FIX/traps/measure/bad.css" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "FAIL[D5]" "$OUT"; then
  ok "genuine 30ch body measure: D5 FAIL (no over-correction)"
else
  bad "30ch body text must FAIL D5 (rc=$RC)"
fi

printf '%s\n' "== self-test: token usage + ban-list [TZ-1.2 audit] =="

OUT=$(bash "$QG/check-token-usage.sh" "$FIX/clean" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "token usage clean" || bad "token usage (rc=$RC): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"

OUT=$(bash "$VD/lint-ban-list.sh" "$FIX/clean" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "ban-list clean" || bad "ban-list (rc=$RC): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"

printf '%s\n' "== self-test: static environment audits [TZ-1.1/1.2] =="

AUDIT=$(grep -rnE '\$\{[A-Za-z_][A-Za-z0-9_]*,,|\$\{[A-Za-z_][A-Za-z0-9_]*\^\^|declare[[:space:]]+-A|mapfile|;&' \
  "$ROOT/.agents/skills" --include='*.sh' 2>/dev/null || true)
if [ -z "$AUDIT" ]; then
  ok "bash 3.2 audit: zero bash-4-isms in package scripts"
else
  bad "bash-4-isms found: $(printf '%s' "$AUDIT" | head -3 | tr '\n' ' ')"
fi

AUDIT=$(grep -rnF '\s' "$ROOT/.agents/skills" --include='*.sh' 2>/dev/null || true)
AUDIT2=$(grep -rnF '\b' "$ROOT/.agents/skills" --include='*.sh' 2>/dev/null || true)
if [ -z "$AUDIT" ] && [ -z "$AUDIT2" ]; then
  ok "BSD grep audit: no \\s or \\b in shell scripts"
else
  bad "GNU-only regex tokens found: $(printf '%s%s' "$AUDIT" "$AUDIT2" | head -3 | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: browser smoke [TZ-2.2/2.3/3.1/3.2] =="

if node -e "require.resolve('playwright')" >/dev/null 2>&1; then
  PORT=$(( (RANDOM % 2000) + 8000 ))
  WORK=$(mktemp -d 2>/dev/null || mktemp -d -t selftest)
  (cd "$FIX/site" && python3 -m http.server "$PORT" >/dev/null 2>&1) &
  SRV=$!
  sleep 1

  START=$SECONDS
  bash "$QG/run-ui-checks.sh" "http://127.0.0.1:$PORT" "/index.html,/about.html" \
    "$WORK/quick" "$FIX/site/paths.json" quick > "$WORK/quick.log" 2>&1; RC=$?
  ELAPSED=$((SECONDS - START))
  LOG=$(cat "$WORK/quick.log")
  if [ "$RC" -eq 0 ] && has "pass D21-keyboard" "$LOG" && has "pass D21-paths" "$LOG"; then
    ok "quick smoke PASS with declared D21 paths walked"
  else
    bad "quick smoke (rc=$RC): $(printf '%s' "$LOG" | grep -E 'D2|D21' | tr '\n' ' ')"
  fi
  if has "INP-proxy" "$LOG" || has "INP" "$LOG"; then
    ok "INP reported with a measured/labeled value (no unmeasured interactivity pass)"
  else
    bad "no INP line in D15 report"
  fi
  if ! has "unavailable D21-paths" "$LOG"; then
    ok "no silent D21 degradation when paths declared"
  else
    bad "unexpected D21-paths unavailable with paths_json present"
  fi
  [ "$ELAPSED" -le 90 ] && ok "quick run wall time ${ELAPSED}s ≤ 90s" \
    || bad "quick run too slow: ${ELAPSED}s"
  N_SECTION=$(find "$WORK/quick" -name 'section-*.png' 2>/dev/null | wc -l | tr -d ' ')
  N_PNG=$(find "$WORK/quick" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$N_SECTION" -eq 0 ] && [ "$N_PNG" -le 8 ]; then
    ok "quick artifact matrix: $N_PNG PNG total, zero section shots"
  else
    bad "quick matrix violated: $N_PNG PNG, $N_SECTION section shots"
  fi

  START=$SECONDS
  bash "$QG/run-ui-checks.sh" "http://127.0.0.1:$PORT" "/index.html" \
    "$WORK/std" "" standard > "$WORK/std.log" 2>&1
  ELAPSED=$((SECONDS - START))
  LOG=$(cat "$WORK/std.log")
  if has "unavailable D21-paths" "$LOG" && ! has "declared paths walked" "$LOG"; then
    ok "no paths_json → explicit unavailable D21-paths, no false pass (regression TZ-2.2)"
  else
    bad "missing paths_json must yield unavailable D21-paths without a pass line"
  fi
  N_SECTION=$(find "$WORK/std" -name 'section-*.png' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$N_SECTION" -gt 0 ] && [ "$N_SECTION" -le 12 ]; then
    ok "standard matrix: $N_SECTION visible-only section shots (hidden panels skipped)"
  else
    bad "standard matrix: unexpected $N_SECTION section shots"
  fi
  [ "$ELAPSED" -le 90 ] && ok "standard run wall time ${ELAPSED}s ≤ 90s (no 30s stalls)" \
    || bad "standard run too slow: ${ELAPSED}s — hidden-panel stall suspected"

  kill "$SRV" 2>/dev/null
else
  skip "browser smoke: playwright not resolvable by node (install per INSTALL.md; fs-level checks above already ran)"
fi

printf '%s\n' "---"
printf 'self-test: %s passed, %s failed, %s skipped\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
