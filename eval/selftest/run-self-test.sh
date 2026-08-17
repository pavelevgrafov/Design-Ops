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

# --- D3 vs $meta.contrastPairs: one geometry, not two ---------------------
# The skin DECLARES its pairs and check-contrast.py GATES them. Two copies of
# the same list drift, and this one had: three declared pairs went unmeasured
# for two versions, hiding a 3.39:1 tertiary tier. Now a declaration without a
# floor fails the build [A.10].
CPWORK=$(mktemp -d 2>/dev/null || mktemp -d -t cp)
CPDRIFT=0
for SKIN in base-site base-app; do
  python3 "$VD/compile-tokens.py" "$ROOT/skins/$SKIN/tokens.json" \
    --out-css "$CPWORK/$SKIN.css" --out-tailwind "$CPWORK/$SKIN.t.css" >/dev/null 2>&1
  OUT=$(python3 "$QG/check-contrast.py" "$CPWORK/$SKIN.css" \
        --tokens "$ROOT/skins/$SKIN/tokens.json" 2>&1); RC=$?
  [ "$RC" -eq 0 ] || { bad "D3: $SKIN fails its own declared pairs: $(printf '%s' "$OUT" | grep FAIL | head -1)"; CPDRIFT=1; }
  has "declared-not-gated" "$OUT" && { bad "D3: $SKIN declares a contrast pair the gate does not measure"; CPDRIFT=1; }
done
[ "$CPDRIFT" -eq 0 ] && ok "D3: every declared contrast pair is gated, both skins, both themes"

# --- the browser lane's availability gate honours the path it was handed ---
# `dops verify` resolves playwright once — from the project or from the
# vendored toolkit — and hands the absolute path to every browser check,
# precisely so they work from a project root with no node_modules. The gate in
# run-ui-checks.sh used to ignore that and re-resolve from the current
# directory, so on every real project six blocking checks (D2, D12, D13, D15,
# D20, D21) reported `unavailable` with playwright sitting right there. Found
# by comparing a CI log against a local run of the shared rehearsal.
GATEWORK=$(mktemp -d 2>/dev/null || mktemp -d -t gate)
mkdir -p "$GATEWORK/bin"
printf '#!/bin/sh\nexit 1\n' > "$GATEWORK/bin/node"
printf '#!/bin/sh\nexit 1\n' > "$GATEWORK/bin/npx"
chmod +x "$GATEWORK/bin/node" "$GATEWORK/bin/npx"
# `bash`, not `sh`: that is how the floor registry invokes this check, and the
# script's shebang says the same. Probing it through dash made the first CI run
# of this probe pass for the wrong reason — the script died on a bash-ism
# before it could print anything. Test it the way it is really run.
OUT=$(cd "$GATEWORK" && PATH="$GATEWORK/bin:$PATH" DOPS_PLAYWRIGHT="/some/resolved/playwright" \
      bash "$QG/run-ui-checks.sh" http://localhost:1 / "$GATEWORK/out" 2>&1)
has "playwright not installed" "$OUT" \
  && bad "the browser lane bailed out although the caller had resolved playwright" \
  || ok "browser lane: the availability gate honours DOPS_PLAYWRIGHT, not the cwd"

# ...and it still degrades honestly when nobody resolved anything
OUT=$(cd "$GATEWORK" && PATH="$GATEWORK/bin:$PATH" \
      bash "$QG/run-ui-checks.sh" http://localhost:1 / "$GATEWORK/out2" 2>&1)
has "playwright not installed" "$OUT" \
  && ok "browser lane: with nothing resolved it still says unavailable [A.6]" \
  || bad "the browser lane stopped reporting a genuinely missing playwright"

# --- [amendment 07 §2] the rehearsal is defined exactly once ---------------
# A rehearsal must be the thing it rehearses. The end-to-end job used to carry
# its steps inline, so checking a change locally meant retyping them — and on
# 2026-08-06 the retyped copy was one `cp` more generous than the job, which
# hid a D.41 defect until it turned main red. The steps now live in
# eval/e2e/rehearse.sh and nowhere else; this probe is what keeps "nowhere
# else" true, because a convention that nothing enforces is not a control.
python3 - "$ROOT" <<'REHPY' && ok "amendment 07 §2: the e2e rehearsal is defined once and CI calls it" \
  || bad "amendment 07 §2: rehearsal check failed — reason printed above"
import sys, os, yaml
root = sys.argv[1]
wf = os.path.join(root, ".github", "workflows", "design-ops.yml")
script = os.path.join(root, "eval", "e2e", "rehearse.sh")

# the commands that ARE the rehearsal: each must live in the script, and none
# of them may appear in the workflow again
MARKS = ["starters/inject.py", "dops_panel.py", "dops_verify.py",
         "visual-regression.sh", "dops_shots.py", "http.server"]

if not os.path.isfile(script):
    raise SystemExit("eval/e2e/rehearse.sh is missing — the rehearsal has no home")
if not os.path.isfile(wf):
    raise SystemExit(".github/workflows/design-ops.yml is missing — the install is "
                     "incomplete, not the rehearsal divergent. Reinstall, or copy "
                     "the workflow in; a probe cannot compare against a file that "
                     "is not there")
body = open(script, encoding="utf-8").read()
missing = [m for m in MARKS if m not in body]
if missing:
    raise SystemExit("the rehearsal script does not run: %s — this probe would "
                     "pass on an empty script" % ", ".join(missing))

doc = yaml.safe_load(open(wf, encoding="utf-8"))
steps = doc["jobs"]["end-to-end"]["steps"]
runs = "\n".join(s.get("run", "") for s in steps)
leaked = [m for m in MARKS if m in runs]
if leaked:
    raise SystemExit("the end-to-end job runs the rehearsal inline again: %s — "
                     "call eval/e2e/rehearse.sh instead [amendment 07 §2]"
                     % ", ".join(leaked))
if "rehearse.sh" not in runs:
    raise SystemExit("the end-to-end job no longer calls the rehearsal script")
REHPY

# ...and the script survives being asked what it is without doing anything
bash "$ROOT/eval/e2e/rehearse.sh" --help >/dev/null 2>&1 \
  && ok "rehearse.sh: --help answers without materialising a project" \
  || bad "rehearse.sh cannot describe itself"

OUT=$(bash "$ROOT/eval/e2e/rehearse.sh" --nonsense 2>&1); RC=$?
[ "$RC" -eq 2 ] && ok "rehearse.sh: an unknown argument is refused, not ignored" \
  || bad "rehearse.sh accepted an unknown argument (rc=$RC)"

# --- [У-6] the decision schedule ------------------------------------------
# `meta.run_plan` was a contract field with no mechanism behind it, so the
# honest answer to "how long, and when do you need me?" was a guess in prose.
# Three claims are worth CI time: the plan lands in a commented contract
# without damaging it, it reaches the feed П-6 renders, and the pulse gains a
# schedule line WITHOUT the stale-pulse incident being softened by it.
U6WORK=$(mktemp -d 2>/dev/null || mktemp -d -t u6)
mkdir -p "$U6WORK/artifacts"
cp "$ROOT/starters/landing-event/contract.yaml" "$U6WORK/artifacts/design-contract.yaml"
OUT=$(python3 "$ROOT/tools/dops_plan.py" emit --route starter_first --root "$U6WORK" 2>&1); RC=$?
[ "$RC" -eq 0 ] && has "ваше участие ~3 мин" "$OUT" \
  && ok "У-6: a plan is emitted and the owner's line is the sum of the attention, not of the etas" \
  || bad "У-6 plan emit (rc=$RC): $(printf '%s' "$OUT" | tail -1)"

OUT=$(python3 "$ROOT/tools/dops_plan.py" emit --route made_up --root "$U6WORK" 2>&1); RC=$?
[ "$RC" -eq 1 ] && has "closed set" "$OUT" \
  && ok "У-6: a route outside the closed registry is refused, not improvised" \
  || bad "У-6 accepted an unknown route (rc=$RC)"

python3 "$ROOT/tools/dops_trace.py" start K2A --root "$U6WORK" >/dev/null 2>&1
python3 "$ROOT/tools/dops_trace.py" end K2A --root "$U6WORK" >/dev/null 2>&1
OUT=$(python3 "$ROOT/tools/dops_feed.py" status --json --root "$U6WORK" 2>/dev/null)
python3 - "$OUT" <<'U6PY' && ok "У-6: the emitted plan reaches the status feed with its source and its facts" \
  || bad "У-6: the plan did not survive the trip through the contract into the feed"
import json, sys
snap = json.loads(sys.argv[1])
plan = snap["run_plan"]
assert len(plan) == 3, "expected three steps, got %d" % len(plan)
assert all("source" in s for s in plan), "a step lost its source"
assert any(s["human_needed"] and s.get("attention_min") for s in plan), "no attention"
assert all(s["source"] == "estimate" for s in plan), "an estimate passed as measured"
U6PY

# The pulse line is an addition to the pulse, never a replacement for it: a
# silent incident must still read as a silent incident with a plan in place.
python3 - "$U6WORK" <<'U6PY'
import json, os, sys
p = os.path.join(sys.argv[1], "artifacts", "progress.json")
d = json.load(open(p, encoding="utf-8"))
d["stage"], d["updated_at"] = "K2A", "2020-01-01T00:00:00"
json.dump(d, open(p, "w", encoding="utf-8"))
U6PY
OUT=$(python3 "$ROOT/tools/dops_feed.py" status --root "$U6WORK" 2>&1)
has "SILENT INCIDENT" "$OUT" && has "k3-report" "$OUT" \
  && ok "У-6: the schedule line joins a stale pulse without softening it" \
  || bad "У-6: the schedule masked or lost the silent incident: $(printf '%s' "$OUT" | head -2)"

# --- [У-5] the depth ladder ------------------------------------------------
# `target_lod` / `status.lod` were fields with nothing behind them, so a run
# either stopped short in silence or polished past what was asked and billed
# for it. Four claims are worth CI time, and the first one is the one that
# would rot quietly: the gap has to be REACHABLE on a default route. If K3
# ever declared a depth, every verified run would claim the top of the ladder
# and `lod-transition` could never fire — the mechanism would be dead while
# every unit test still passed.
U5WORK=$(mktemp -d 2>/dev/null || mktemp -d -t u5)
mkdir -p "$U5WORK/artifacts/visual"
cp "$ROOT/starters/landing-event/contract.yaml" "$U5WORK/artifacts/design-contract.yaml"
python3 "$ROOT/tools/dops_plan.py" emit --route starter_first --root "$U5WORK" >/dev/null 2>&1
python3 - "$U5WORK/artifacts/design-contract.yaml" <<'U5PY'
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(
    re.sub(r"^meta:$", "meta:\n  target_lod: 300", t, count=1, flags=re.M))
U5PY
for st in K1 K2A; do
  python3 "$ROOT/tools/dops_trace.py" start "$st" --root "$U5WORK" >/dev/null 2>&1
  python3 "$ROOT/tools/dops_trace.py" end "$st" --root "$U5WORK" >/dev/null 2>&1
done
OUT=$(python3 "$ROOT/tools/dops_checkpoint.py" list --root "$U5WORK" 2>&1)
LOGLINE=$(grep '"id": "lod-transition"' "$U5WORK/artifacts/checkpoints.jsonl" 2>/dev/null | head -1)
has "lod-transition" "$OUT" && has "мин" "$LOGLINE" && has "токен" "$LOGLINE" \
  && ok "У-5: a run ending below its target publishes the transition WITH its price" \
  || bad "У-5: no priced lod-transition on a starter_first run: $(printf '%s' "$OUT" | head -2)"

OUT=$(python3 "$ROOT/tools/dops_lod.py" check --root "$U5WORK" 2>&1); RC=$?
[ "$RC" -eq 1 ] && has "lod_mismatch" "$OUT" \
  && ok "У-5: stopping short of the target with no owner command is a defect line" \
  || bad "У-5: the gap passed the delivery check (rc=$RC): $(printf '%s' "$OUT" | head -1)"

python3 "$ROOT/tools/dops_control.py" issue --command enough --root "$U5WORK" >/dev/null 2>&1
python3 "$ROOT/tools/dops_control.py" apply --at selftest --root "$U5WORK" >/dev/null 2>&1
OUT=$(python3 "$ROOT/tools/dops_lod.py" check --root "$U5WORK" 2>&1); RC=$?
[ "$RC" -eq 0 ] \
  && ok "У-5: the owner's enough turns the same gap from a defect into a decision" \
  || bad "У-5: the owner's enough did not close the ladder (rc=$RC): $OUT"

# A deepening is a restyle, and a restyle never rebuilds structure [A.7] —
# so the skeleton's hash must survive one. Without the graph the scoped form
# is refused outright rather than quietly costing a full rebuild [A.6].
OUT=$(python3 "$ROOT/tools/dops_control.py" issue --command deepen_lod \
      --args '{"lod": 300, "scope": "section:hero"}' --root "$U5WORK" 2>&1
      python3 "$ROOT/tools/dops_control.py" apply --at selftest --root "$U5WORK" 2>&1)
has "hash-graph unavailable" "$OUT" \
  && ok "У-5: a scoped deepening without hashes is refused, not silently full-price" \
  || bad "У-5: a scoped deepening was accepted with no hash graph: $(printf '%s' "$OUT" | tail -1)"

printf '<h1>x</h1>' > "$U5WORK/skeleton.html"
printf '{}' > "$U5WORK/artifacts/visual/tokens.json"
printf ':root{}' > "$U5WORK/artifacts/visual/tokens.css"
python3 "$ROOT/tools/dops_hash.py" record --root "$U5WORK" >/dev/null 2>&1
python3 "$ROOT/tools/dops_control.py" issue --command deepen_lod \
  --args '{"lod": 300, "scope": "section:hero"}' --root "$U5WORK" >/dev/null 2>&1
OUT=$(python3 "$ROOT/tools/dops_control.py" apply --at selftest --root "$U5WORK" 2>&1)
python3 - "$U5WORK" <<'U5PY' && ok "У-5: a scoped deepening drops the visual chain and leaves the structure alone [A.7]" \
  || bad "У-5: the deepening invalidated the wrong set"
import json, os, sys
m = json.load(open(os.path.join(sys.argv[1], "artifacts", "hashes.json"), encoding="utf-8"))
a = m["artifacts"]
assert "skeleton.html" in a, "the deepening rebuilt the structure"
assert "artifacts/visual/tokens.css" not in a, "the visual chain was not invalidated"
U5PY

# The table's own rule made mechanical: `measured` is a label only a retrain
# may apply, and a hand-written one is an estimate wearing a fact's badge.
OUT=$(python3 "$ROOT/tools/dops_lod.py" retrain --check 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "У-5: every measured cost carries the samples that earned it" \
  || bad "У-5: cost-table has a hand-written measurement: $(printf '%s' "$OUT" | head -1)"

# --- [Ф-1] the selector's subtree, and the measurement behind the move ----
OUT=$(python3 "$ROOT/tools/dops_dom.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "Ф-1: selector subtrees resolve, out-of-grammar selectors are refused" \
  || bad "dops_dom self-test: $(printf '%s' "$OUT" | grep FAIL | head -1)"

# The number this move exists for, re-measured from a set that lives in the
# repository. The baseline assertion is the valuable one: if it ever stops
# being 0, an extractor has started GUESSING find/replace out of prose, which
# is the one thing Ф-1 was built to avoid doing.
OUT=$(python3 "$ROOT/eval/measure-machine-plans.py" --json 2>&1); RC=$?
if [ "$RC" -ne 0 ]; then
  bad "Ф-1 measurement crashed: $(printf '%s' "$OUT" | tail -1)"
else
  python3 - "$OUT" <<'F1MPY' && ok "Ф-1: 0/15 typed edits are machine-executable, 5/5 via the form" \
    || bad "Ф-1 machine_plan_share: $OUT"
import json, sys
d = json.loads(sys.argv[1])
assert d["before"]["machine"] == 0, (
    "%d typed edit(s) were called machine-executable — an extractor is guessing "
    "find/replace out of prose again" % d["before"]["machine"])
assert d["after"]["born_in_form"] == 5, (
    "the form produced %d machine plans, expected 5" % d["after"]["born_in_form"])
assert d["after"]["machine"] == 5, "a plan appeared from somewhere other than the form"
F1MPY
fi

# --- [С-1] D.39: no artefact steps around a declared alias ---------------
# Found by П-4: the panel could offer no radius knob on the reference landing,
# because the markup wrote var(--radius-md) while the knob moves
# semantic.radius.card. The rule is read from the skin, so silence where no
# alias exists (--space-*) is the skin admitting the layer was never designed,
# not an exemption.
OUT=$(python3 "$QG/check-semantic-layer.py" --self-test 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.39: alias map from declarations, semantic offered first, honest absence" \
  || bad "D.39 self-test: $(printf '%s' "$OUT" | grep FAIL | head -1)"

OUT=$(python3 "$QG/check-semantic-layer.py" "$ROOT/starters" \
      --tokens "$ROOT/skins/base-site/tokens.json" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.39: all six shipped starters speak through the declared aliases" \
  || bad "D.39: a starter bypasses the semantic layer: $(printf '%s' "$OUT" | grep FAIL | head -1)"

# [D-BZ-5] Scope, not verdict. D.39 runs with {src} = the project root, and a
# project has the toolkit vendored inside it — so an unexcluded walk audits
# eval/selftest/fixture/, whose traps are deliberate, and fails the floor on
# them. Every other walker had this exclusion; this one did not, and the gap
# survived because D.39 is only reachable once a run registers skin tokens.
# Case №1 was the first real run and its only fail was exactly that.
# Both halves are asserted: silent on the vendored package, still loud when
# the fixture is scanned on purpose.
OUT=$(python3 "$QG/check-semantic-layer.py" "$ROOT" \
      --tokens "$ROOT/skins/base-site/tokens.json" 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "D.39: the vendored package is not audited as product" \
  || bad "D.39 scans the toolkit's own fixture: $(printf '%s' "$OUT" | grep FAIL | head -1)"

OUT=$(python3 "$QG/check-semantic-layer.py" "$FIX" \
      --tokens "$ROOT/skins/base-site/tokens.json" 2>&1); RC=$?
[ "$RC" -eq 1 ] && has "font-scale-step2" "$OUT" \
  && ok "D.39: the exclusion is scope only — the fixture trap still fires when scanned on purpose" \
  || bad "D.39 went quiet on its own fixture trap (rc=$RC) — the exclusion ate the check"

# The acceptance of the move, and the reason it is not bureaucracy: after the
# rebinding the panel must find the radius knob it could not find before.
S1WORK=$(mktemp -d 2>/dev/null || mktemp -d -t s1)
cp "$ROOT/starters/landing-event/skeleton/index.html" "$S1WORK/index.html"
cp "$ROOT/skins/base-site/tokens.css" "$S1WORK/tokens.css"
OUT=$(python3 "$ROOT/tools/dops_panel.py" emit --skin base-site \
      --artifact "$S1WORK/index.html" --out "$S1WORK/panel-config.js" 2>&1)
has "semantic-radius-card" "$OUT" && has "type-scale" "$OUT" \
  && ok "С-1: the panel finds the radius knob and keeps the scale knob on a rebound starter" \
  || bad "С-1: rebinding did not restore the panel's sight: $(printf '%s' "$OUT" | head -3)"

# A scale knob that moves only the raw steps would turn nothing on an artefact
# that speaks aliases — the compiler resolves an alias to a literal, so the
# knob has to write both.
python3 - "$S1WORK/panel-config.js" <<'S1PY' && ok "С-1: the scale knob writes the aliases, not only the raw steps" \
  || bad "С-1: the scale knob would turn nothing on an aliased artefact"
import json, sys
s = open(sys.argv[1], encoding="utf-8").read()
cfg = json.loads(s[s.index("{"):s.rstrip().rstrip(";").rindex("}") + 1])
knob = next(k for k in cfg["knobs"] if k["id"] == "type-scale")
css = knob["options"][0]["css"]
sys.exit(0 if "--font-size-md" in css and "--font-scale-step1" in css else 1)
S1PY

# --- [С-1] D.41: a compiled theme must not outlive its source -------------
# Fourth case of the same family in one week (drifted pairs, the unrun kruto
# check, the stale skin CSS): a build artefact that keeps claiming what the
# declaration no longer says.
D41WORK=$(mktemp -d 2>/dev/null || mktemp -d -t d41)
D41BAD=0
for SKIN in base-site base-app; do
  cp "$ROOT/skins/$SKIN/tokens.json" "$D41WORK/tokens.json"
  cp "$ROOT/skins/$SKIN/tokens.css" "$D41WORK/tokens.css"
  cp "$ROOT/skins/$SKIN/tokens.theme.css" "$D41WORK/tokens.theme.css"
  python3 "$VD/compile-tokens.py" "$D41WORK/tokens.json" --out-css "$D41WORK/tokens.css" \
    --out-tailwind "$D41WORK/tokens.theme.css" --verify >/dev/null 2>&1 \
    || { bad "D.41: $SKIN ships a compiled theme that does not match its tokens.json"; D41BAD=1; }
  printf '  --tampered: 1px;\n' >> "$D41WORK/tokens.css"
  python3 "$VD/compile-tokens.py" "$D41WORK/tokens.json" --out-css "$D41WORK/tokens.css" \
    --out-tailwind "$D41WORK/tokens.theme.css" --verify >/dev/null 2>&1 \
    && { bad "D.41: $SKIN accepted a hand-edited compiled theme"; D41BAD=1; }
done
[ "$D41BAD" -eq 0 ] && ok "D.41: both skins ship a fresh theme, and one edited line fails the build"

# The Tailwind bridge is optional; the CSS is not. A project that never emits
# a bridge must pass, and a project missing the CSS itself must not — the
# post-merge run on main failed on exactly this over-reach, because the CI
# materialisation copied two of the three files a real K2A leaves behind.
D41OPT=$(mktemp -d 2>/dev/null || mktemp -d -t d41o)
cp "$ROOT/skins/base-site/tokens.json" "$ROOT/skins/base-site/tokens.css" "$D41OPT/"
python3 "$VD/compile-tokens.py" "$D41OPT/tokens.json" --out-css "$D41OPT/tokens.css"   --out-tailwind "$D41OPT/tokens.theme.css" --verify >/dev/null 2>&1   && rm -f "$D41OPT/tokens.css"   && ! python3 "$VD/compile-tokens.py" "$D41OPT/tokens.json" --out-css "$D41OPT/tokens.css"        --out-tailwind "$D41OPT/tokens.theme.css" --verify >/dev/null 2>&1   && ok "D.41: a project with no Tailwind bridge passes, a project with no CSS does not"   || bad "D.41 treats the optional bridge and the required CSS alike"

# ...and --verify refuses to guess its own paths, which is how a reviewer got a
# false 'missing' on the day D.41 shipped.
python3 "$VD/compile-tokens.py" "$ROOT/skins/base-site/tokens.json" --verify >/dev/null 2>&1
[ "$?" -eq 2 ] && ok "D.41: --verify against default paths is refused, not answered"   || bad "D.41 --verify still compares against whatever is in the working directory"

# --- [Т-1] the declared dark ramp ----------------------------------------
# The dark theme used to live in a comment ("87/60/38% over #121212") next to
# sixteen literals nobody could check against it. Now the sentence is
# $meta.darkModel, the literals are generated from it, and D.40 fails on any
# tone that stopped matching. Three claims are worth CI time here: both skins
# still render dark exactly as before, the dark layer holds no literal, and a
# hand-edited tone is caught.
OUT=$(python3 "$ROOT/tools/dops_skin.py" darkramp --all --check 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "Т-1: both flagship skins match their declared dark model" \
  || bad "Т-1 dark ramp drift: $(printf '%s' "$OUT" | grep -v '^OK' | head -2)"

T1WORK=$(mktemp -d 2>/dev/null || mktemp -d -t t1)
T1DRIFT=0
for SKIN in base-site base-app; do
  python3 - "$ROOT/skins/$SKIN/tokens.json" "$T1WORK/$SKIN.json" <<'T1PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
doc["primitive"]["color"]["darkInk"]["87"]["$value"] = "#e0e0e1"
json.dump(doc, open(sys.argv[2], "w", encoding="utf-8"))
T1PY
  OUT=$(python3 "$ROOT/tools/dops_skin.py" darkramp --tokens "$T1WORK/$SKIN.json" --check 2>&1); RC=$?
  [ "$RC" -eq 1 ] && has "e0e0e1" "$OUT" || { bad "Т-1: $SKIN accepted a hand-edited dark tone (rc=$RC)"; T1DRIFT=1; }
done
[ "$T1DRIFT" -eq 0 ] && ok "D.40: one channel off in one dark tone fails the build, both skins"

# Visual continuity, measured rather than asserted. Every ink and surface tone
# must land byte-identical on what the skin rendered before Т-1 — the emphasis
# percentages were chosen to make that true. The two accent tokens are the
# declared exception (§4 of the spec: the model wins over a hand-picked
# literal), so they are checked for having moved TO the model, not for having
# stayed — a silent accent is as much a defect as a moved ink.
OUT=$(python3 - "$ROOT" <<'T1PY'
import json, os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "tools"))
import dops_panel as panel
BEFORE = {"ink": "#e0e0e0", "inkMuted": "#a0a0a0", "textTertiary": "#6c6c6c",
          "canvas": "#121212", "canvasRaised": "#1e1e1e",
          "borderSubtle": "#2e2e2e", "textPrimary": "#e0e0e0",
          "textSecondary": "#a0a0a0", "inkOnDark": "#e0e0e0",
          "surfaceDark": "#121212", "actionPrimaryText": "#121212"}
bad, knobs = 0, {}
for skin in ("base-site", "base-app"):
    doc = json.load(open(os.path.join(root, "skins", skin, "tokens.json"), encoding="utf-8"))
    res = panel.resolved_colors(doc, "dark")
    for name, was in BEFORE.items():
        if res.get(name, "").lower() != was:
            print("MOVED %s %s: %s -> %s" % (skin, name, was, res.get(name)))
            bad = 1
    ramps = doc["primitive"]["color"]
    for name, ramp, tone in (("actionPrimary", "accentDark", "500"),
                             ("focusRing", "accentDark", "300")):
        want = ramps[ramp][tone]["$value"].lower()
        if res.get(name, "").lower() != want:
            print("UNDECLARED %s %s: %s is not %s.%s" % (skin, name, res.get(name), ramp, tone))
            bad = 1
    cfg = panel.build_config(doc, skin, None, "x")
    knobs[skin] = sum(1 for k in cfg["knobs"]
                      if k["kind"] == "color" and k["theme"] == "dark")
    if knobs[skin] < 4:
        print("KNOBLESS %s: %d dark colour knob(s)" % (skin, knobs[skin]))
        bad = 1
print("KNOBS %s" % json.dumps(knobs))
sys.exit(bad)
T1PY
); RC=$?
[ "$RC" -eq 0 ] \
  && ok "Т-1: ink and surface render unchanged, accents follow the model, dark knobs appear ($(printf '%s' "$OUT" | grep KNOBS))" \
  || bad "Т-1: $(printf '%s' "$OUT" | grep -E 'MOVED|UNDECLARED|KNOBLESS' | head -2)"

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

  # --- [D-BZ-1/2] the install carries everything the package ships ------------
  # Case №1 installed the toolkit into a fresh repo and got a red self-test:
  # install.sh's ITEMS list had never been given `.github`, and `package.json`
  # was gitignored, so the browser lane had nothing to resolve playwright from.
  # Both are the same class as the CI defect fixed in 3330a3e — the check
  # existed, the thing that ran was not it — and both were invisible because
  # ITEMS was maintained by memory. This probe is what makes ITEMS a list the
  # repository checks: whatever is tracked at the top level either ships or is
  # named as deliberately local, and the fresh install is verified to hold it.
  ITEMSPY=$(mktemp 2>/dev/null || mktemp -t items)
  python3 - "$ROOT" "$UPDWORK" > "$ITEMSPY" 2>&1 <<'ITEMPY'
import os, re, subprocess, sys
root, target = sys.argv[1], sys.argv[2]

m = re.search(r'^ITEMS="([^"]*)"', open(os.path.join(root, "install.sh"),
                                        encoding="utf-8").read(), re.M)
if not m:
    raise SystemExit("install.sh has no ITEMS= line — the copy list is gone")
items = set(m.group(1).split())

# Tracked at the top level but deliberately NOT copied. Each entry is a
# decision, not an oversight: the pro directories are handled separately by the
# subscription tier block below ITEMS; .gitignore belongs to whatever repository
# the package lands in, never to the package; and DECISIONS.md records why THIS
# toolkit is built the way it is — a project built with the pipeline needs the
# instructions (README, AGENTS, INSTALL, which do ship) and not the history.
# Shipping it would also hand the copy-linter a root-level document to read as
# product copy, which it is not.
LOCAL_ONLY = {"packs-pro", "skins-pro", "starters-pro", ".gitignore",
              "DECISIONS.md"}

try:
    # -z: the package carries Cyrillic filenames under docs/, which plain
    # ls-files returns C-quoted ("docs/\320\221...") and would have been read
    # here as a top-level path named `"docs`.
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                         capture_output=True, text=True, timeout=30)
except (OSError, subprocess.SubprocessError) as e:
    raise SystemExit("SKIP: git unavailable (%s)" % e)
if out.returncode != 0 or not out.stdout.strip():
    raise SystemExit("SKIP: not a git checkout — nothing to compare ITEMS against")

tracked = {p.split("/", 1)[0] for p in out.stdout.split("\0") if p.strip()}
unlisted = sorted(tracked - items - LOCAL_ONLY)
if unlisted:
    raise SystemExit("the package tracks %s, which install.sh never copies — a "
                     "fresh install arrives without it (add to ITEMS, or to "
                     "LOCAL_ONLY here with the reason)" % ", ".join(unlisted))

stale = sorted(i for i in items if not os.path.exists(os.path.join(root, i)))
if stale:
    raise SystemExit("ITEMS lists %s, which the package no longer has" %
                     ", ".join(stale))

absent = sorted(i for i in items if os.path.exists(os.path.join(root, i))
                and not os.path.exists(os.path.join(target, i)))
if absent:
    raise SystemExit("the fresh install is missing %s — it is in ITEMS but did "
                     "not arrive" % ", ".join(absent))
print("%d shipped path(s) listed and installed" % len(items))
ITEMPY
  ITEMSOUT=$(cat "$ITEMSPY"); rm -f "$ITEMSPY"
  case "$ITEMSOUT" in
    SKIP:*) skip "install completeness: ${ITEMSOUT#SKIP: }" ;;
    *"listed and installed"*)
      ok "install completeness: every tracked top-level path ships and arrives ($ITEMSOUT)" ;;
    *) bad "install completeness: $ITEMSOUT" ;;
  esac
else
  bad "install.sh fresh install red in update test"
fi

printf '%s\n' "== self-test: browser smoke [TZ-2.2/2.3/3.1/3.2] =="

if node -e "require.resolve('playwright')" >/dev/null 2>&1; then
  # resolved once, passed explicitly: a runner written into a temp directory
  # cannot resolve `playwright` from there — the defect that kept the whole
  # browser lane from ever running
  PW_PATH=$(node -e "console.log(require.resolve('playwright'))")
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

  # [П-4] the panel is a browser asset, so its two claims are checked in a
  # browser: a knob actually moves the variable, and a page without a config
  # is left completely alone. Three assertions, not a laboratory.
  PANWORK=$(mktemp -d 2>/dev/null || mktemp -d -t pan)
  mkdir -p "$PANWORK/site"
  cp "$ROOT/skins/base-site/tokens.css" "$PANWORK/site/tokens.css"
  cat > "$PANWORK/site/index.html" <<'PANHTML'
<!doctype html><html><head><link rel="stylesheet" href="tokens.css">
<style>body{background:var(--canvas);color:var(--ink);max-width:var(--measure-body)}</style>
</head><body><h1>panel smoke</h1>
<script src="./panel-config.js"></script>
<script src="./token-panel.js"></script>
</body></html>
PANHTML
  cp "$ROOT/.agents/skills/pipeline-orchestrator/assets/token-panel.js" "$PANWORK/site/"
  python3 "$ROOT/tools/dops_panel.py" emit --skin base-site \
    --artifact "$PANWORK/site/index.html" > /dev/null 2>&1
  cat > "$PANWORK/smoke.cjs" <<'PANJS'
const { chromium } = require(process.env.DOPS_PLAYWRIGHT);
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + dir + '/site/index.html');
  const before = await p.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--ink').trim());
  const hasButton = await p.locator('#dops-panel-open').count();
  await p.locator('#dops-panel-open').click();
  const knob = await p.locator('[data-knob="color-ink-light"]').count();
  // the FIRST option: the options are the ramp in order, so the last one is
  // usually the current value, and picking the current value is correctly a
  // no-op — that would test nothing
  await p.locator('[data-knob="color-ink-light"]').nth(0).click();
  const after = await p.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--ink').trim());
  await p.locator('[data-knob="theme"]').nth(1).click();
  const theme = await p.evaluate(() =>
    document.documentElement.getAttribute('data-theme'));
  // reset must return to the compiled CSS with no reload
  await p.locator('[data-act="reset"]').click();
  const reset = await p.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--ink').trim());
  // a page with no config must get no button and no errors
  await p.goto('file://' + dir + '/bare/index.html');
  const bare = await p.locator('#dops-panel-open').count();
  console.log(JSON.stringify({ hasButton, before, after, theme, reset, bare,
                               errs: errs.length, knob }));
  await b.close();
})().catch(e => { console.error(String(e)); process.exit(1); });
PANJS
  mkdir -p "$PANWORK/bare"
  cp "$ROOT/skins/base-site/tokens.css" "$PANWORK/bare/tokens.css"
  cp "$ROOT/.agents/skills/pipeline-orchestrator/assets/token-panel.js" "$PANWORK/bare/"
  printf '%s\n' '<!doctype html><html><head><link rel="stylesheet" href="tokens.css"></head><body><h1>bare</h1><script src="./token-panel.js"></script></body></html>' > "$PANWORK/bare/index.html"
  OUT=$(DOPS_PLAYWRIGHT="$PW_PATH" node "$PANWORK/smoke.cjs" "$PANWORK" 2>&1); RC=$?
  if [ "$RC" -ne 0 ]; then
    bad "П-4 panel smoke crashed: $(printf '%s' "$OUT" | tail -1)"
  else
    python3 - "$OUT" <<'PANPY' && ok "П-4 panel: knob moves the variable, theme toggles, reset restores" || bad "П-4 panel smoke: $OUT"
import json, sys
d = json.loads(sys.argv[1])
assert d["hasButton"] == 1, "no panel button on a page that has a config"
assert d["knob"] >= 1, "no colour knob rendered"
assert d["before"] and d["after"] and d["before"] != d["after"], "the knob moved nothing"
assert d["theme"] == "dark", "the theme toggle did not set data-theme"
assert d["reset"] == d["before"], "reset did not return to the compiled CSS"
assert d["bare"] == 0, "a page without a config still grew a panel button"
assert d["errs"] == 0, "the panel logged console errors"
PANPY
  fi

  # [Ф-1] the edit form, and the overlap the П-4 probe could not see.
  # П-5 measured 0% machine-executable owner edits; the fix is not a cleverer
  # classifier but a form that cannot produce a non-machine plan. Both claims
  # are browser claims, so they are checked in a browser: find/replace really
  # do come out of the DOM, and — the defect Kimi found on the live demo —
  # the token panel and the pins bar are usable AT THE SAME TIME. The old
  # panel probe clicked each surface in turn and so never saw the collision.
  F1WORK=$(mktemp -d 2>/dev/null || mktemp -d -t f1)
  mkdir -p "$F1WORK/site"
  cp "$ROOT/.agents/skills/pipeline-orchestrator/assets/gate-annotate.js" "$F1WORK/site/"
  cp "$ROOT/.agents/skills/pipeline-orchestrator/assets/token-panel.js" "$F1WORK/site/"
  cp "$ROOT/skins/base-site/tokens.css" "$F1WORK/site/tokens.css"
  cat > "$F1WORK/site/index.html" <<'F1HTML'
<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>ф-1</title>
<link rel="stylesheet" href="tokens.css"></head><body>
<main id="tickets"><p class="note">Билеты в продаже</p><img id="pic" alt="x" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="></main>
<script src="./panel-config.js"></script>
<script src="./token-panel.js"></script>
<script src="./gate-annotate.js"></script>
</body></html>
F1HTML
  python3 "$ROOT/tools/dops_panel.py" emit --skin base-site \
    --artifact "$F1WORK/site/index.html" > /dev/null 2>&1
  cat > "$F1WORK/f1.cjs" <<'F1JS'
const { chromium } = require(process.env.DOPS_PLAYWRIGHT);
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  // short, because every wait in this probe is a surface covering another
  // one: a timeout here IS the finding, and it should read as one rather
  // than as a crash with a stack trace
  p.setDefaultTimeout(3000);
  const url = 'file://' + dir + '/site/index.html';
  await p.goto(url);

  // an edit is born machine-executable, straight out of the DOM
  await p.keyboard.press('e');
  await p.locator('#tickets .note').click();
  await p.keyboard.type('Билеты уже в продаже');
  await p.keyboard.press('Enter');
  const pins = await p.evaluate(() =>
    JSON.parse(localStorage.getItem('dops-pins:' + location.pathname) || '[]'));

  // it survives a reload, because the artefact on disk has not changed yet
  await p.reload();
  const afterReload = await p.locator('#tickets .note').innerText();

  // markup typed in stays text
  await p.keyboard.press('e');
  await p.locator('#tickets .note').click();
  await p.keyboard.type('<b>жирно</b>');
  await p.keyboard.press('Enter');
  const boldNodes = await p.evaluate(() =>
    document.querySelectorAll('#tickets .note b').length);

  // Esc puts the original back and writes no pin
  const countBefore = await p.evaluate(() =>
    JSON.parse(localStorage.getItem('dops-pins:' + location.pathname) || '[]').length);
  await p.keyboard.press('e');
  await p.locator('#tickets .note').click();
  await p.keyboard.type('мусор');
  await p.keyboard.press('Escape');
  const countAfter = await p.evaluate(() =>
    JSON.parse(localStorage.getItem('dops-pins:' + location.pathname) || '[]').length);

  // a non-text target never arms
  await p.keyboard.press('e');
  await p.locator('#pic').click();
  const editingImg = await p.evaluate(() =>
    document.querySelector('#pic').getAttribute('contenteditable'));

  // the overlap: every control of BOTH surfaces reachable at once
  const boxes = await p.evaluate(() => {
    const r = (s) => { const e = document.querySelector(s);
      return e ? e.getBoundingClientRect().toJSON() : null; };
    return { panel: r('#dops-panel'), bar: r('#ga-bar') };
  });
  let panelOpened = true;
  try { await p.locator('#dops-panel-open').click(); }   // panel open = 320px
  catch (e) { panelOpened = false; }
  const openBox = await p.evaluate(() =>
    document.querySelector('#dops-panel').getBoundingClientRect().toJSON());
  const barBox = await p.evaluate(() =>
    document.querySelector('#ga-bar').getBoundingClientRect().toJSON());
  let clickable = true;
  for (const sel of ['#ga-arm', '#ga-edit', '#ga-export', '#ga-count']) {
    try { await p.locator(sel).click({ trial: true, timeout: 1500 }); }
    catch (e) { clickable = false; }
  }
  console.log(JSON.stringify({ pins, afterReload, boldNodes, countBefore,
    countAfter, editingImg, boxes, openBox, barBox, clickable, panelOpened,
    errs: errs.length }));
  await b.close();
})().catch(e => { console.error(String(e)); process.exit(1); });
F1JS
  OUT=$(DOPS_PLAYWRIGHT="$PW_PATH" node "$F1WORK/f1.cjs" "$F1WORK" 2>&1); RC=$?
  if [ "$RC" -ne 0 ]; then
    bad "Ф-1 form smoke crashed: $(printf '%s' "$OUT" | tail -1)"
  else
    python3 - "$OUT" <<'F1PY' && ok "Ф-1: the form writes find/replace from the DOM, survives reload, refuses non-text" || bad "Ф-1 form smoke: $(printf '%s' "$OUT" | tail -1)"
import json, sys
d = json.loads(sys.argv[1])
pins = d["pins"]
assert len(pins) == 1, "one edit produced %d pin(s)" % len(pins)
a = pins[0]
plan = a.get("plan") or {}
assert plan.get("machine") is True, "the form produced a pin with no machine plan"
assert plan.get("action") == "set_text", "wrong action: %r" % plan.get("action")
pr = plan.get("params") or {}
assert pr.get("find") == "Билеты в продаже", "find is not the DOM text: %r" % pr.get("find")
assert pr.get("replace") == "Билеты уже в продаже", "replace is not what was typed: %r" % pr.get("replace")
assert pr.get("selector"), "the plan carries no selector, so it has no scope"
assert a.get("lane") == "A", "a born machine plan is not lane A: %r" % a.get("lane")
assert a.get("status") == "new", "a fresh edit is not `new`: %r" % a.get("status")
assert d["afterReload"] == "Билеты уже в продаже", \
    "a pending edit did not survive the reload: %r" % d["afterReload"]
assert d["boldNodes"] == 0, "typed markup became real nodes"
assert d["countAfter"] == d["countBefore"], "Esc still wrote a pin"
assert d["editingImg"] is None, "an image was armed for text editing"
assert d["errs"] == 0, "%d console error(s)" % d["errs"]
F1PY
    python3 - "$OUT" <<'F1PY' && ok "Ф-1: the panel and the pins bar are usable at the same time (Kimi's overlap defect)" || bad "Ф-1 overlap: $(printf '%s' "$OUT" | tail -1)"
import json, sys
d = json.loads(sys.argv[1])
assert d["panelOpened"], "the panel button itself was not reachable"
assert d["clickable"], "a control of the pins bar could not be clicked with the panel open"
op, bar = d["openBox"], d["barBox"]
overlap_x = min(op["x"] + op["width"], bar["x"] + bar["width"]) - max(op["x"], bar["x"])
overlap_y = min(op["y"] + op["height"], bar["y"] + bar["height"]) - max(op["y"], bar["y"])
assert not (overlap_x > 0 and overlap_y > 0), (
    "the open panel overlaps the pins bar by %.0fx%.0f px" % (overlap_x, overlap_y))
F1PY
  fi

  # [П-6] the feed inside the artefact: the counter is a door, waiting pins
  # come first, and a row opens the pin it is about.
  FEEDWORK=$(mktemp -d 2>/dev/null || mktemp -d -t feed)
  cp "$ROOT/.agents/skills/pipeline-orchestrator/assets/gate-annotate.js" "$FEEDWORK/"
  # charset declared: without it the browser decodes the markers as latin-1
  # and the status ribbon turns to mojibake — the same defect D.28 catches in
  # a real artefact
  printf '%s\n' '<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>feed</title></head><body><main id="hero"><h1>feed</h1></main><script src="./gate-annotate.js"></script></body></html>' > "$FEEDWORK/index.html"
  cat > "$FEEDWORK/feed.cjs" <<'FEEDJS'
const { chromium } = require(process.env.DOPS_PLAYWRIGHT);
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('dialog', async d => { await d.dismiss(); });
  await p.addInitScript(() => {
    const now = new Date().toISOString();
    localStorage.setItem('dops-pins:' + location.pathname, JSON.stringify([
      { id: 'a-0001', selector: '#hero', x: 10, y: 20, text: 'применённый пин',
        status: 'applied', lane: 'A', created_at: now, at: now },
      { id: 'a-0002', selector: '#hero', x: 10, y: 40, text: 'ждёт ответа',
        status: 'clarify', lane: 'A', created_at: now, at: now,
        check: { verdict: 'clarify', question: 'какой элемент?' } },
      { id: 'a-0003', selector: '#hero', x: 10, y: 60, text: 'снят поздним словом',
        status: 'superseded', lane: 'A', created_at: now, at: now,
        superseded_by: 'a-0002' }
    ]));
  });
  await p.goto('file://' + dir + '/index.html');
  const closed = await p.locator('#ga-feed').isVisible();
  await p.locator('#ga-count').click();
  const rows = await p.locator('[data-feed-row]').count();
  const first = await p.locator('[data-feed-row]').first().innerText();
  const marks = await p.locator('#ga-feed').innerText();
  await p.keyboard.press('Escape');
  const afterEsc = await p.locator('#ga-feed').isVisible();
  console.log(JSON.stringify({ closed, rows, first, afterEsc, errs: errs.length,
                               hasSuperseded: marks.indexOf('\u25cc') >= 0 }));
  await b.close();
})().catch(e => { console.error(String(e)); process.exit(1); });
FEEDJS
  OUT=$(DOPS_PLAYWRIGHT="$PW_PATH" node "$FEEDWORK/feed.cjs" "$FEEDWORK" 2>&1); RC=$?
  if [ "$RC" -ne 0 ]; then
    bad "П-6 feed smoke crashed: $(printf '%s' "$OUT" | tail -1)"
  else
    python3 - "$OUT" <<'FEEDPY' && ok "П-6 feed: counter opens the list, waiting first, superseded marked" || bad "П-6 feed smoke: $OUT"
import json, sys
d = json.loads(sys.argv[1])
assert d["closed"] is False, "the feed was open before anyone asked for it"
assert d["rows"] == 3, "the feed shows %s rows for 3 pins" % d["rows"]
assert "ждёт ответа" in d["first"], "a waiting pin is not first: %r" % d["first"]
assert d["hasSuperseded"], "the superseded marker is missing from the feed"
assert d["afterEsc"] is False, "Esc did not close the feed"
assert d["errs"] == 0, "the feed logged console errors"
FEEDPY
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
  # [П-5] streaming intake: idempotent, machine plans only where extractable,
  # the owner's last instruction wins visibly, failures roll back alone.
  OUT=$(cd "$ROOT" && python3 tools/dops_pins_sweep.py --self-test 2>&1); RC=$?
  if [ "$RC" -eq 0 ]; then
    ok "dops pins sweep/apply: 9 probes (intake, machine plans, conflicts, rollback)"
  else
    bad "dops pins sweep self-test (rc=$RC): $OUT"
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
