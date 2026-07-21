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

printf '%s\n' "== self-test: v6.0 contract-migrate [TZ-1] =="

MIGWORK=$(mktemp -d 2>/dev/null || mktemp -d -t mig)
cp "$FIX/contract/design-contract.yaml" "$MIGWORK/design-contract.yaml"
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/design-contract.yaml" 2>&1); RC=$?
GOT=$(python3 "$PO/contract-read.py" "$MIGWORK/design-contract.yaml" schema_version 2>&1)
if [ "$RC" -eq 0 ] && [ "$GOT" = "6.0" ]; then
  ok "migrator: 5.1 fixture -> schema 6.0"
else
  bad "migrator run (rc=$RC, schema=$GOT): $(printf '%s' "$OUT" | tail -1)"
fi
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/design-contract.yaml" 2>&1)
has "already 6.0" "$OUT" && ok "migrator: idempotent second run" \
  || bad "migrator not idempotent: $OUT"

printf '%s\n' "== self-test: v6.0 pack-resolve + D24 [TZ-2/TZ-8] =="

PACKWORK=$(mktemp -d 2>/dev/null || mktemp -d -t packs)
mkdir -p "$PACKWORK/_fixture"
cp "$ROOT/packs/_fixture/pack.yaml" "$PACKWORK/_fixture/pack.yaml"
OUT=$(env -u FIXTURE_PACK_TOKEN python3 "$PO/pack-resolve.py" "$PACKWORK" _fixture --ttl-hours 0 --json 2>&1); RC=$?
if [ "$RC" -ne 0 ] && has "unavailable" "$OUT" && has "FIXTURE_PACK_TOKEN" "$OUT"; then
  ok "pack-resolve: missing env -> unavailable with the var named"
else
  bad "pack-resolve missing-env path (rc=$RC): $OUT"
fi
OUT=$(FIXTURE_PACK_TOKEN=t FIXTURE_PACK_ACCEPT=pass python3 "$PO/pack-resolve.py" "$PACKWORK" _fixture --ttl-hours 0 --json 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has '"active"' "$OUT"; then
  ok "pack-resolve: env + green acceptance -> active"
else
  bad "pack-resolve green path (rc=$RC): $OUT"
fi
OUT=$(FIXTURE_PACK_TOKEN=t FIXTURE_PACK_ACCEPT=fail python3 "$PO/pack-resolve.py" "$PACKWORK" _fixture --ttl-hours 0 --json 2>&1); RC=$?
if [ "$RC" -ne 0 ] && has "unavailable" "$OUT"; then
  ok "pack-resolve: red acceptance -> unavailable"
else
  bad "pack-resolve red-acceptance path (rc=$RC): $OUT"
fi

printf 'integrations: [{pack: _fixture, class: peripheral}]\n' > "$PACKWORK/c-periph.yaml"
OUT=$(env -u FIXTURE_PACK_TOKEN python3 "$QG/check-packs.py" "$PACKWORK/c-periph.yaml" "$PACKWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "unavailable D24 _fixture" "$OUT" && ! has "CAPS" "$OUT"; then
  ok "D24: peripheral pack down = report line, exit 0, no cap"
else
  bad "D24 peripheral path (rc=$RC): $OUT"
fi
mkdir -p "$PACKWORK/_corefix"
printf 'id: _corefix\ntype: api\nconveyor: [K3]\nclass: core\nprovides: [probe]\nrequires_env: [DEFINITELY_MISSING_ENV_VAR]\ncontract_fields: [integrations]\nacceptance_test: "true"\ndegradation: caps verdict\ncost_profile: free\nlicense_notes: n/a\nversion: "0.1.0"\n' > "$PACKWORK/_corefix/pack.yaml"
printf 'integrations: [{pack: _corefix, class: core}]\n' > "$PACKWORK/c-core.yaml"
OUT=$(python3 "$QG/check-packs.py" "$PACKWORK/c-core.yaml" "$PACKWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "CAPS verdict at ready_with_caveats" "$OUT"; then
  ok "D24: core pack down = exit 1 + explicit verdict cap"
else
  bad "D24 core-cap path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 knowledge vault [TZ-10] =="

OUT=$(python3 "$PO/knowledge-validate.py" "$ROOT" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "OK:" "$OUT"; then
  ok "knowledge-validate: repo vault green, index in sync"
else
  bad "knowledge-validate on repo (rc=$RC): $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
fi
IDXSIZE=$(wc -c < "$ROOT/knowledge/index.yaml" | tr -d ' ')
[ "$IDXSIZE" -le 4096 ] && ok "knowledge index <= 4 KB ($IDXSIZE B)" \
  || bad "knowledge index too big: $IDXSIZE B"
KVWORK=$(mktemp -d 2>/dev/null || mktemp -d -t kv)
mkdir -p "$KVWORK/knowledge/sources" "$KVWORK/.agents/skills/x"
for nid in cited orphan; do
  printf -- '---\nid: %s\ntitle: "T"\nurl: https://example.com/\nevidence_level: curated\nverified_at: 2026-07-21\ntags: [t]\nthesis: "x"\n---\nbody\n' "$nid" > "$KVWORK/knowledge/sources/$nid.md"
done
printf 'rule cites knowledge/cited\n' > "$KVWORK/.agents/skills/x/SKILL.md"
OUT=$(python3 "$PO/knowledge-validate.py" "$KVWORK" --write-index >/dev/null 2>&1; python3 "$PO/knowledge-validate.py" "$KVWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "orphan note knowledge/orphan" "$OUT" && ! has "orphan note knowledge/cited" "$OUT"; then
  ok "knowledge-validate: orphan flagged, cited note not flagged"
else
  bad "knowledge-validate orphan path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 D23 secrets scan [TZ-8] =="

SECWORK=$(mktemp -d 2>/dev/null || mktemp -d -t sec)
printf 'aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"\n' > "$SECWORK/app.js"  # SECRET-ALLOW: D23 self-test fixture (AWS docs example key)
OUT=$(python3 "$QG/check-secrets.py" "$SECWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "BLOCKING" "$OUT"; then
  ok "D23: fake AWS key caught, blocking"
else
  bad "D23 catch path (rc=$RC): $OUT"
fi
printf 'const greeting = "hello";\n' > "$SECWORK/app.js"
OUT=$(python3 "$QG/check-secrets.py" "$SECWORK" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D23: clean tree passes" || bad "D23 clean path (rc=$RC): $OUT"

printf '%s\n' "== self-test: v6.0 gate annotations [TZ-9] =="

ANNWORK=$(mktemp -d 2>/dev/null || mktemp -d -t ann)
printf '[{"target_selector": "#v2 > div.card", "x": 412, "y": 188, "text": "too dense", "at": "2026-07-21T12:00:00Z"}]\n' > "$ANNWORK/ok.json"
OUT=$(python3 "$PO/annotations-log.py" "$ANNWORK/ok.json" --log "$ANNWORK/log.md" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "pin 1" "$(cat "$ANNWORK/log.md")"; then
  ok "annotations: valid fixture serializes into the log"
else
  bad "annotations valid path (rc=$RC): $OUT"
fi
printf '[{"target_selector": "#v2", "x": "412"}]\n' > "$ANNWORK/bad.json"
OUT=$(python3 "$PO/annotations-log.py" "$ANNWORK/bad.json" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "fail" "$OUT"; then
  ok "annotations: schema violation rejected"
else
  bad "annotations invalid path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 starter injection [TZ-3] =="

INJWORK=$(mktemp -d 2>/dev/null || mktemp -d -t inj)
cat > "$INJWORK/values.yaml" <<'VALUES'
business_name: "Selftest Bakery"
tagline: "Fresh every morning"
phone: "+1 555 0100"
address: "12 Main St"
hours: "Mon-Sat 7-20"
service_1_name: "Rye"
service_1_price: "$4"
service_2_name: "Croissant"
service_2_price: "$3"
service_3_name: "Sourdough"
service_3_price: "$6"
cta_label: "Order"
VALUES
OUT=$(python3 "$ROOT/starters/inject.py" "$ROOT/starters/landing-local" "$INJWORK/values.yaml" --out "$INJWORK/out" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "100%" "$OUT" && has "Selftest Bakery" "$(cat "$INJWORK/out/index.html")"; then
  ok "starter injection: 12/12 slots filled (>=95% floor)"
else
  bad "starter injection full path (rc=$RC): $OUT"
fi
printf 'business_name: "Only Name"\n' > "$INJWORK/thin.yaml"
OUT=$(python3 "$ROOT/starters/inject.py" "$ROOT/starters/landing-local" "$INJWORK/thin.yaml" --out "$INJWORK/thin-out" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "leftover" "$OUT"; then
  ok "starter injection: thin brief fails with explicit leftover list"
else
  bad "starter injection thin path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 render-sitemap [TZ-5] =="

SMWORK=$(mktemp -d 2>/dev/null || mktemp -d -t sm)
OUT=$(python3 "$SB/render-sitemap.py" "$ROOT/starters/app-dashboard/contract.yaml" --out-dir "$SMWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -f "$SMWORK/sitemap.html" ] && [ -f "$SMWORK/sitemap.mmd" ]; then
  ok "render-sitemap: app contract -> mmd + html artifacts"
else
  bad "render-sitemap green path (rc=$RC): $OUT"
fi
printf 'experience:\n  key_screens: [{id: home, purpose: "entry"}]\n  scenarios: [{id: main, screens: [home, ghost]}]\n' > "$SMWORK/bad.yaml"
OUT=$(python3 "$SB/render-sitemap.py" "$SMWORK/bad.yaml" --out-dir "$SMWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "not a key_screen id" "$OUT"; then
  ok "render-sitemap: ghost screen id fails the deterministic cross-check"
else
  bad "render-sitemap red path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 context budget [TZ-12] =="

CBWORK=$(mktemp -d 2>/dev/null || mktemp -d -t cb)
python3 "$PO/context-budget.py" read "$ROOT/AGENTS.md" --log "$CBWORK/log.jsonl" >/dev/null 2>&1
OUT=$(python3 "$PO/context-budget.py" report --mode quick --log "$CBWORK/log.jsonl" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "OK" "$OUT"; then
  ok "context-budget: under-limit report green"
else
  bad "context-budget green path (rc=$RC): $OUT"
fi
printf 'limits: {quick: 10}\nest_bytes_per_token: 4\n' > "$CBWORK/limits.yaml"
OUT=$(python3 "$PO/context-budget.py" report --mode quick --log "$CBWORK/log.jsonl" --limits "$CBWORK/limits.yaml" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "OVER" "$OUT"; then
  ok "context-budget: over-limit = explicit wave defect"
else
  bad "context-budget over-limit path (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 handoff package [TZ-11] =="

HOWORK=$(mktemp -d 2>/dev/null || mktemp -d -t ho)
OUT=$(bash "$PO/make-handoff.sh" "$ROOT/starters/landing-local" "$HOWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -f "$HOWORK/handoff/README.md" ] && [ -f "$HOWORK/handoff/design-contract.yaml" ]; then
  ok "handoff: package assembled on a reference starter, links verified"
else
  bad "handoff path (rc=$RC): $OUT"
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

  # --- D22 visual regression on an injected diff [TZ-8] -------------------
  VRWORK="$WORK/vr"
  mkdir -p "$VRWORK/site"
  printf '<!doctype html><meta charset="utf-8"><title>vr</title><h1>v1</h1>' > "$VRWORK/site/index.html"
  VR="$QG/visual-regression.sh"
  VRBASE="file://$VRWORK/site"
  bash "$VR" reference "$VRBASE" "$VRWORK/shots" "/index.html" > /dev/null 2>&1
  OUT=$(bash "$VR" test "$VRBASE" "$VRWORK/shots" "/index.html" 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "D22: no diff -> green"
  else
    bad "D22 identical path (rc=$RC): $OUT"
  fi
  printf '<!doctype html><meta charset="utf-8"><title>vr</title><h1>v2 CHANGED</h1>' > "$VRWORK/site/index.html"
  OUT=$(bash "$VR" test "$VRBASE" "$VRWORK/shots" "/index.html" 2>&1); RC=$?
  if [ "$RC" -eq 1 ] && has "unapproved diff" "$OUT"; then
    ok "D22: injected diff blocks until approved"
  else
    bad "D22 diff path (rc=$RC): $OUT"
  fi
  bash "$VR" approve "$VRBASE" "$VRWORK/shots" "/index.html" > /dev/null 2>&1
  OUT=$(bash "$VR" test "$VRBASE" "$VRWORK/shots" "/index.html" 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "D22: approve promotes the baseline, test green again"
  else
    bad "D22 approve path (rc=$RC): $OUT"
  fi

  kill "$SRV" 2>/dev/null
else
  skip "browser smoke: playwright not resolvable by node (install per INSTALL.md; fs-level checks above already ran)"
fi

printf '%s\n' "---"
printf 'self-test: %s passed, %s failed, %s skipped\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
