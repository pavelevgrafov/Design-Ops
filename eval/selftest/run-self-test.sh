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

printf '%s\n' "== self-test: v6.0/v7.0 contract-migrate [TZ-1] =="

MIGWORK=$(mktemp -d 2>/dev/null || mktemp -d -t mig)
cp "$FIX/contract/design-contract.yaml" "$MIGWORK/design-contract.yaml"
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/design-contract.yaml" 2>&1); RC=$?
GOT=$(python3 "$PO/contract-read.py" "$MIGWORK/design-contract.yaml" schema_version 2>&1)
if [ "$RC" -eq 0 ] && [ "$GOT" = "7.0" ] && has "5.1->6.0" "$OUT" && has "6.0->7.0" "$OUT"; then
  ok "migrator: 5.1 fixture -> schema 7.0 in one chained run"
else
  bad "migrator run (rc=$RC, schema=$GOT): $(printf '%s' "$OUT" | tail -1)"
fi
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/design-contract.yaml" 2>&1)
has "already 7.0" "$OUT" && ok "migrator: idempotent second run" \
  || bad "migrator not idempotent: $OUT"
V7BAD=$(mktemp -d 2>/dev/null || mktemp -d -t v7bad)
mkdir -p "$V7BAD/artifacts"
cp "$MIGWORK/design-contract.yaml" "$V7BAD/artifacts/design-contract.yaml"
python3 - "$V7BAD/artifacts/design-contract.yaml" <<'PYEOF'
import sys, yaml
p = sys.argv[1]
c = yaml.safe_load(open(p))
c["product"]["job_hypothesis"] = {"statement": "x", "confidence": "sure", "source": "vibes"}
c["experience"]["assumptions"] = [{"claim": "a", "kill_criteria": "k"}] * 4
c["visual"]["design_review"] = "looks-good"
yaml.safe_dump(c, open(p, "w"), allow_unicode=True, sort_keys=False)
PYEOF
OUT=$(python3 "$QG/validate-pipeline.py" "$V7BAD" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "confidence" "$OUT" && has "RAT-lite caps" "$OUT" && has "design_review" "$OUT"; then
  ok "validate-pipeline: v7 field violations caught (confidence, RAT cap, design_review)"
else
  bad "validate-pipeline v7 negatives missed (rc=$RC): $(printf '%s' "$OUT" | grep -c FAIL) fail lines"
fi

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
[ "$IDXSIZE" -le 8192 ] && ok "knowledge index <= 8 KB v7.0 ($IDXSIZE B)" \
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

printf '%s\n' "== self-test: v7.0 floor D.25–D.38 + verification packs =="

# --- compile-tokens A.21 layer enforcement (negative) -------------------
A21WORK=$(mktemp -d 2>/dev/null || mktemp -d -t a21)
printf '%s' '{"primitive":{"color":{"red":{"500":{"$value":"#ff0000","$type":"color"}}}},"semantic":{"color":{"ink":{"$value":"{primitive.color.red.500}","$type":"color"}}},"component":{"button":{"bg":{"$value":"{primitive.color.red.500}","$type":"color"}}}}' > "$A21WORK/bad.json"
OUT=$(python3 "$VD/compile-tokens.py" "$A21WORK/bad.json" --check-only 2>&1); RC=$?
[ "$RC" -eq 1 ] && has "component token must reference semantic" "$OUT" \
  && ok "compile-tokens: component->primitive violation blocked [A.21]" \
  || bad "compile-tokens A.21 negative (rc=$RC): $(printf '%s' "$OUT" | tail -1)"

# --- D.25 extended contrast (contrast-checker) ---------------------------
OUT=$(python3 "$ROOT/packs/contrast-checker/scripts/check-all-pairs.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.25 contrast-checker: both skins, both themes green" \
  || bad "D.25 contrast-checker self-test: $(printf '%s' "$OUT" | tail -1)"

# --- D.27 focus visible ---------------------------------------------------
python3 "$QG/check-focus-visible.py" "$FIX/v7/focus-ok.css" >/dev/null 2>&1 \
  && ok "D.27 focus-visible: styled focus passes" \
  || bad "D.27 false-positive on focus-ok.css"
OUT=$(python3 "$QG/check-focus-visible.py" "$FIX/v7/focus-bad.css" 2>&1); RC=$?
[ "$RC" -eq 1 ] && ok "D.27 focus-visible: naked outline:none fails" \
  || bad "D.27 missed outline removal (rc=$RC)"

# --- D.28 semantic HTML ---------------------------------------------------
python3 "$QG/check-semantic-html.py" "$FIX/v7/semantic-ok.html" >/dev/null 2>&1 \
  && ok "D.28 semantic: landmarks + continuous headings pass" \
  || bad "D.28 false-positive on semantic-ok.html"
OUT=$(python3 "$QG/check-semantic-html.py" "$FIX/v7/semantic-bad.html" 2>&1); RC=$?
[ "$RC" -eq 1 ] && has "heading level skips" "$OUT" \
  && ok "D.28 semantic: double h1 + skipped level + div-button caught" \
  || bad "D.28 missed violations (rc=$RC)"

# --- D.29 reduced motion --------------------------------------------------
python3 "$QG/check-reduced-motion.py" "$FIX/v7/motion-ok.css" >/dev/null 2>&1 \
  && ok "D.29 reduced-motion: quiet version present passes" \
  || bad "D.29 false-positive on motion-ok.css"
OUT=$(python3 "$QG/check-reduced-motion.py" "$FIX/v7/motion-bad.css" 2>&1); RC=$?
[ "$RC" -eq 1 ] && ok "D.29 reduced-motion: motion without quiet version fails" \
  || bad "D.29 missed missing reduced-motion (rc=$RC)"

# --- D.30 ai-look-detector ------------------------------------------------
OUT=$(python3 "$ROOT/packs/ai-look-detector/scripts/scan.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.30 ai-look-detector: clean passes, tier-1 markers caught" \
  || bad "D.30 ai-look-detector self-test: $(printf '%s' "$OUT" | tail -1)"

# --- D.35 motion properties (tier 2) --------------------------------------
OUT=$(python3 "$QG/check-motion-properties.py" "$FIX/v7/motion-ok.css" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.35 motion-props: transform/opacity motion passes" \
  || bad "D.35 false-positive on motion-ok.css"
OUT=$(python3 "$QG/check-motion-properties.py" "$FIX/v7/motion-bad.css" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "WARN" "$OUT"; then
  python3 "$QG/check-motion-properties.py" "$FIX/v7/motion-bad.css" --strict >/dev/null 2>&1
  [ "$?" -eq 1 ] && ok "D.35 motion-props: layout-property transition warns (tier 2), strict fails" \
    || bad "D.35 --strict did not fail on motion-bad.css"
else
  bad "D.35 expected tier-2 warning on motion-bad.css (rc=$RC)"
fi

# --- D.36 copy-linter ------------------------------------------------------
OUT=$(python3 "$ROOT/packs/copy-linter/scripts/lint-copy.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.36 copy-linter: clean copy passes, slop caught" \
  || bad "D.36 copy-linter self-test: $(printf '%s' "$OUT" | tail -1)"

# --- D.37 token-validator --------------------------------------------------
OUT=$(python3 "$ROOT/packs/token-validator/scripts/validate-layers.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.37 token-validator: violation caught, both skins valid" \
  || bad "D.37 token-validator self-test: $(printf '%s' "$OUT" | tail -1)"

# --- D.38 state-generator + seven-states -----------------------------------
OUT=$(python3 "$ROOT/packs/state-generator/scripts/generate-states.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.38 state-generator: generate->check cycle works" \
  || bad "D.38 state-generator self-test: $(printf '%s' "$OUT" | tail -1)"
OUT=$(python3 "$QG/check-seven-states.py" "$FIX/contract/design-contract.yaml" 2>&1); RC=$?
has "skip D.38" "$OUT" || has "OK:" "$OUT" || [ "$RC" -eq 0 ] \
  && ok "D.38 seven-states: honest skip/ pass on fixture contract" \
  || bad "D.38 unexpected failure on fixture (rc=$RC): $OUT"

# --- pack bus: new packs resolve through pack-resolve ----------------------
for v7pack in ai-look-detector contrast-checker token-validator state-generator copy-linter awwwards-reference; do
  OUT=$(python3 "$PO/pack-resolve.py" "$ROOT/packs" "$v7pack" --json 2>&1)
  has '"status": "active"' "$OUT" \
    && ok "pack-resolve: $v7pack active (acceptance green)" \
    || bad "pack-resolve: $v7pack not active: $(printf '%s' "$OUT" | tr '\n' ' ' | head -c 160)"
done

# --- v7.0 K2B: tier-2 ban-list + awwwards-reference flows -------------------
T2WORK=$(mktemp -d 2>/dev/null || mktemp -d -t t2)
printf 'h1{background-clip:text;-webkit-text-fill-color:transparent}\n.x{border-radius:2rem}\n' > "$T2WORK/t.css"
OUT=$(bash "$VD/lint-ban-list.sh" "$T2WORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "tier-2 warning" "$OUT"; then
  bash "$VD/lint-ban-list.sh" "$T2WORK" --strict >/dev/null 2>&1
  [ "$?" -eq 1 ] && ok "lint-ban-list: tier-2 warns without blocking, --strict fails" \
    || bad "lint-ban-list --strict did not fail on tier-2 hits"
else
  bad "lint-ban-list tier-2 behavior broken (rc=$RC): $(printf '%s' "$OUT" | tail -1)"
fi
bash "$VD/lint-ban-list.sh" "$FIX/clean" >/dev/null 2>&1 \
  && ok "lint-ban-list: clean fixture stays green with tier-2 active" \
  || bad "lint-ban-list false-positive on clean fixture"

OUT=$(python3 "$ROOT/packs/awwwards-reference/scripts/search-references.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "awwwards-reference: search honors hard stops (<=3, scored)" \
  || bad "awwwards-reference search self-test: $(printf '%s' "$OUT" | tail -1)"
OUT=$(python3 "$ROOT/packs/awwwards-reference/scripts/extract-tokens.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "awwwards-reference: CSS-only token extraction drafts DTCG" \
  || bad "awwwards-reference extract self-test: $(printf '%s' "$OUT" | tail -1)"

# --- v7.0 ecosystem: showcase + radar --------------------------------------
SCWORK=$(mktemp -d 2>/dev/null || mktemp -d -t sc)
OUT=$(python3 "$ROOT/showcase/build-showcase.py" --out "$SCWORK/index.html" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -f "$SCWORK/index.html" ]; then
  has "landing-saas" "$(cat "$SCWORK/index.html")" \
    && ok "showcase: auto-populated from starters index" \
    || bad "showcase: generated page misses starters"
else
  bad "showcase build failed (rc=$RC): $(printf '%s' "$OUT" | tail -1)"
fi
OUT=$(env -u GITHUB_TOKEN -u GITHUB_REPOSITORY python3 "$ROOT/radar/radar.py" 2>&1); RC=$?
[ "$RC" -eq 2 ] && has "required" "$OUT" \
  && ok "radar: missing env is an explicit usage error, never a silent run" \
  || bad "radar env-honesty broken (rc=$RC)"

# --- v7.1: wiki-sync + gate enforcement + install --update -------------------
OUT=$(python3 "$ROOT/packs/wiki-sync/scripts/wiki-sync.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "wiki-sync: pin -> check -> tamper-detect cycle works" \
  || bad "wiki-sync self-test: $(printf '%s' "$OUT" | tail -1)"
OUT=$(python3 "$PO/pack-resolve.py" "$ROOT/packs" wiki-sync --json 2>&1)
has '"status": "active"' "$OUT" \
  && ok "pack-resolve: wiki-sync active (acceptance green)" \
  || bad "pack-resolve: wiki-sync not active: $(printf '%s' "$OUT" | tr '\n' ' ' | head -c 160)"

GRWORK=$(mktemp -d 2>/dev/null || mktemp -d -t gr)
printf 'meta: {schema_version: "7.0"}\ngates: {gate1: pending}\nstatus: {verdict: not_ready}\ndeploy: {prod: {rollback_tested: false}}\n' > "$GRWORK/c.yaml"
python3 "$PO/gate-require.py" "$GRWORK/c.yaml" gate1 >/dev/null 2>&1
[ "$?" -eq 1 ] && ok "gate-require: unpassed gate1 is mechanically refused" \
  || bad "gate-require let a pending gate1 through"
printf 'meta: {schema_version: "7.0"}\ngates: {gate1: passed}\nstatus: {verdict: ready}\ndeploy: {prod: {rollback_tested: true}}\n' > "$GRWORK/c.yaml"
python3 "$PO/gate-require.py" "$GRWORK/c.yaml" gate1 >/dev/null 2>&1 \
  && ok "gate-require: passed gate1 admits the stage" \
  || bad "gate-require refused a legal gate1"

UPDWORK=$(mktemp -d 2>/dev/null || mktemp -d -t upd)
DESIGN_OPS_SKIP_SELFTEST=1 bash "$ROOT/install.sh" "$UPDWORK" >/dev/null 2>&1 \
  || { bad "install.sh fresh install red in update test"; }
if [ -d "$UPDWORK/.agents" ]; then
  printf 'broken\n' > "$UPDWORK/knowledge/index.yaml"
  printf 'local\n' > "$UPDWORK/LOCAL-NOTES.md"
  OUT=$(DESIGN_OPS_SKIP_SELFTEST=1 bash "$ROOT/install.sh" --update --dry-run "$UPDWORK" 2>&1)
  if has "change:  knowledge/index.yaml" "$OUT" && has "nothing written" "$OUT"; then
    grep -q broken "$UPDWORK/knowledge/index.yaml" \
      && ok "install --update --dry-run: reports the diff, writes nothing" \
      || bad "install --dry-run wrote anyway"
  else
    bad "install --dry-run report wrong: $(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"
  fi
  DESIGN_OPS_SKIP_SELFTEST=1 bash "$ROOT/install.sh" --update "$UPDWORK" >/dev/null 2>&1 \
    && ! grep -q broken "$UPDWORK/knowledge/index.yaml" && [ -f "$UPDWORK/LOCAL-NOTES.md" ] \
    && ok "install --update: overlays the package, preserves local files" \
    || bad "install --update broke overlay semantics"
else
  bad "install.sh fresh install red in update test"
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

printf '%s\n' "== self-test: dops machine contour (single-entry floor, run trace) =="
DOPS="$ROOT/tools/dops"
if [ -x "$DOPS" ]; then
  OUT=$("$DOPS" selftest 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops: registry shape, profile floors, verdict rules, trace, cost.actual"
  else
    bad "dops selftest (rc=$RC): $OUT"
  fi
  # [П-1/П-2] pins on the artifact, sorted into lanes before the model sees them.
  OUT=$(cd "$ROOT" && python3 tools/dops_pins.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops pins: 4 lanes, structure beats token words, ambiguity asks"
  else
    bad "dops pins self-test (rc=$RC): $OUT"
  fi
  # [П-3] the checker at the door: refusals must carry alternatives, dead
  # selectors must ask, and lanes A/B must cost zero model calls.
  OUT=$(cd "$ROOT" && python3 tools/dops_pins_check.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops pins check: 10 probes (alternatives, questions, duplicates, script-only)"
  else
    bad "dops pins check self-test (rc=$RC): $OUT"
  fi
  # A refusal without an alternative is a wall. The validator must say so.
  PINWORK=$(mktemp -d 2>/dev/null || mktemp -d -t pin)
  printf '%s' '[{"target_selector":"#a","x":1,"y":2,"text":"t","at":"2026-08-06T09:00:00","check":{"verdict":"rejected","checked_at":"2026-08-06T09:01:00","checker":"script","reason":"r","alternatives":[]}}]' > "$PINWORK/wall.json"
  OUT=$(python3 "$PO/annotations-log.py" "$PINWORK/wall.json" 2>&1); RC=$?
  [ "$RC" -eq 1 ] && ok "П-3: a refusal without alternatives is rejected by the validator" \
    || bad "П-3 accepted a refusal with no way out (rc=$RC): $OUT"
  printf '%s' '[{"target_selector":"#a","x":1,"y":2,"text":"t","at":"2026-08-06T09:00:00","check":{"verdict":"rejected","checked_at":"2026-08-06T09:01:00","checker":"script","reason":"contrast 1.5:1","alternatives":["use #6e6a64"]}}]' > "$PINWORK/ok.json"
  OUT=$(python3 "$PO/annotations-log.py" "$PINWORK/ok.json" 2>&1); RC=$?
  [ "$RC" -eq 0 ] && ok "П-3: a negotiated refusal validates and reaches the decision log" \
    || bad "П-3 rejected a well-formed refusal (rc=$RC): $OUT"

  # [AC-23] the quick ceiling limits production, not inheritance.
  ACWORK=$(mktemp -d 2>/dev/null || mktemp -d -t ac23)
  mkdir -p "$ACWORK/artifacts/ux"
  printf 'meta: {mode: quick, schema_version: "7.0"}\n' > "$ACWORK/artifacts/design-contract.yaml"
  printf 'artifacts:\n  ux: {origin: inherited, source_starter: "landing-event"}\n' >> "$ACWORK/artifacts/design-contract.yaml"
  OUT=$(python3 "$QG/validate-pipeline.py" "$ACWORK" 2>&1)
  if has "ceiling violated" "$OUT"; then
    bad "AC-23: an inherited starter model was counted as production"
  else
    ok "AC-23: an inherited experience model does not break the quick ceiling"
  fi
  printf 'meta: {mode: quick, schema_version: "7.0"}\n' > "$ACWORK/artifacts/design-contract.yaml"
  printf 'artifacts:\n  ux: {origin: produced, source_starter: ""}\n' >> "$ACWORK/artifacts/design-contract.yaml"
  OUT=$(python3 "$QG/validate-pipeline.py" "$ACWORK" 2>&1)
  if has "ceiling violated" "$OUT"; then
    ok "AC-23: a model produced inside a quick run still violates the ceiling"
  else
    bad "AC-23: silence bought an exemption — produced/absent origin let through"
  fi

  # the always-on pin script must keep the v6 field names, or the existing
  # annotations validator stops reading its own artifacts
  GA="$ROOT/.agents/skills/pipeline-orchestrator/assets/gate-annotate.js"
  if has "target_selector" "$(cat "$GA")" && has "created_at" "$(cat "$GA")"; then
    ok "gate-annotate: always-on schema stays backward compatible"
  else
    bad "gate-annotate lost a field annotations-log.py requires"
  fi
  # [У-2/У-3] checkpoints and the control queue: windows with handles.
  for probe in dops_checkpoint dops_control dops_guard; do
    OUT=$(cd "$ROOT" && python3 "tools/$probe.py" --self-test 2>&1); RC=$?
    if [ "$RC" -eq 0 ]; then
      ok "$probe: self-test"
    else
      bad "$probe self-test (rc=$RC): $OUT"
    fi
  done
  # [A.25] gate-overtaking: work ahead is allowed, calling it a product is not.
  OVWORK=$(mktemp -d 2>/dev/null || mktemp -d -t ov)
  printf 'gates: {gate1: provisional}\nstatus: {deliverable_blocked: true, verdict: ""}\n' > "$OVWORK/c.yaml"
  OUT=$(python3 "$PO/gate-require.py" "$OVWORK/c.yaml" stage:K2A 2>&1); RC=$?
  [ "$RC" -eq 0 ] && ok "A.25: K2A may run under a provisional gate" \
    || bad "A.25 K2A refused under provisional (rc=$RC): $OUT"
  OUT=$(python3 "$PO/gate-require.py" "$OVWORK/c.yaml" stage:K2B-scale 2>&1); RC=$?
  [ "$RC" -eq 1 ] && ok "A.25: scaling beyond the slice refused under provisional" \
    || bad "A.25 let K2B-scale through (rc=$RC): $OUT"
  printf 'gates: {gate1: provisional}\nstatus: {deliverable_blocked: true, verdict: ready}\n' > "$OVWORK/c.yaml"
  OUT=$(python3 "$PO/gate-require.py" "$OVWORK/c.yaml" verdict 2>&1); RC=$?
  [ "$RC" -eq 1 ] && ok "A.25: a ready verdict under a provisional gate is refused" \
    || bad "A.25 allowed a ready verdict under provisional (rc=$RC): $OUT"
  printf 'gates: {gate1: provisional}\nstatus: {deliverable_blocked: false}\n' > "$OVWORK/c.yaml"
  OUT=$(python3 "$PO/gate-require.py" "$OVWORK/c.yaml" deliver 2>&1); RC=$?
  [ "$RC" -eq 1 ] && ok "A.25: a stale deliverable_blocked flag is caught" \
    || bad "A.25 missed the flag/gate mismatch (rc=$RC): $OUT"

  # [A.26] the kruto incident must now fail mechanically, not be regretted later.
  OUT=$(cd "$ROOT" && python3 tools/dops_announce.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops announce: A.26 enforced (grant required, decisions announced)"
  else
    bad "dops announce self-test (rc=$RC): $OUT"
  fi
  # [E.3] for real: reuse by input hash, and drift detection on generated files.
  OUT=$(cd "$ROOT" && python3 tools/dops_hash.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops hash: freshness, drift, targeted invalidation [E.3]"
  else
    bad "dops hash self-test (rc=$RC): $OUT"
  fi
  # The flywheel gate: a run that leaves no starter and no reason is a defect.
  OUT=$(cd "$ROOT" && python3 tools/dops_harvest.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops harvest: decision required at delivery, taxonomy enforced"
  else
    bad "dops harvest self-test (rc=$RC): $OUT"
  fi
  # Stage isolation: a packet must be buildable for every conveyor stage.
  OUT=$(cd "$ROOT" && python3 tools/dops_handoff.py K1 --stdout 2>&1); RC=$?
  if [ "$RC" -eq 0 ] && has "Do NOT read" "$OUT"; then
    ok "dops handoff: stage packet builds with its exclusion list"
  else
    bad "dops handoff K1 (rc=$RC): $OUT"
  fi
  # The card must stay in sync with its sources and inside its context budget.
  OUT=$(cd "$ROOT" && python3 tools/dops_card.py --audit 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops card: sources aligned, resident set inside budget"
  else
    bad "dops card audit (rc=$RC): $OUT"
  fi
  # The floor must be reachable as ONE command: agent turns are the cost driver.
  DOPS_OUT="$(mktemp -d)/floor.json"
  OUT=$(cd "$ROOT" && python3 tools/dops_verify.py --root eval/selftest \
        --profile quick --out "$DOPS_OUT" 2>&1); RC=$?
  if [ "$RC" -eq 0 ] || [ "$RC" -eq 1 ]; then
    if has "checks in" "$OUT"; then
      ok "dops verify: whole floor runs as one command, one report"
    else
      bad "dops verify: no summary line: $OUT"
    fi
  else
    bad "dops verify (rc=$RC): $OUT"
  fi
else
  bad "tools/dops missing or not executable"
fi

printf '%s\n' "---"
printf 'self-test: %s passed, %s failed, %s skipped\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
