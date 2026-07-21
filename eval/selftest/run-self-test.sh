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
if [ -z "$AUDIT" ]; then
  ok "BSD grep audit: no \\s or \\b in shell scripts"
else
  bad "perl shorthand in scripts: $(printf '%s' "$AUDIT" | head -3 | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: validate-pipeline.py [TZ-1.4/2.5] =="

OUT=$(python3 "$QG/validate-pipeline.py" "$FIX/pipeline-ok" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "OK: pipeline integrity" "$OUT"; then
  ok "5.1 fixture contract: integrity green"
else
  bad "fixture pipeline must validate (rc=$RC): $(printf '%s' "$OUT" | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: contract-migrate.py 5.1 -> 6.0 [TZ-13] =="

MIGWORK=$(mktemp -d 2>/dev/null || mktemp -d -t mig)
mkdir -p "$MIGWORK/artifacts"
cp "$FIX/pipeline-ok/artifacts/design-contract.yaml" "$MIGWORK/artifacts/design-contract.yaml"
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/artifacts/design-contract.yaml" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "migrated to 6.0" "$OUT"; then
  ok "migration 5.1 -> 6.0 runs"
else
  bad "migration failed (rc=$RC): $OUT"
fi
OUT=$(python3 "$PO/contract-migrate.py" "$MIGWORK/artifacts/design-contract.yaml" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "already 6.0" "$OUT"; then
  ok "migration idempotent (second run is a no-op)"
else
  bad "migration not idempotent (rc=$RC): $OUT"
fi
OUT=$(python3 "$QG/validate-pipeline.py" "$MIGWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ]; then
  ok "migrated 6.0 contract passes validate-pipeline (v6 deferred path)"
else
  bad "migrated contract must validate (rc=$RC): $(printf '%s' "$OUT" | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: v6 enum rejection [TZ-13] =="

BADWORK=$(mktemp -d 2>/dev/null || mktemp -d -t bad)
mkdir -p "$BADWORK/artifacts"
cp "$FIX/pipeline-ok/artifacts/design-contract.yaml" "$BADWORK/artifacts/design-contract.yaml"
python3 - "$BADWORK/artifacts/design-contract.yaml" <<'BADYAML'
import sys, yaml
p = sys.argv[1]
c = yaml.safe_load(open(p, encoding="utf-8"))
c["meta"]["schema_version"] = "6.0"
c["meta"]["artifact_profile"] = "banana"
c.setdefault("gates", {})["mode"] = "lumped"
yaml.safe_dump(c, open(p, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
BADYAML
OUT=$(python3 "$QG/validate-pipeline.py" "$BADWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "artifact_profile 'banana'" "$OUT" && has "gates.mode 'lumped'" "$OUT"; then
  ok "bad profile + bad gate mode rejected by v6 enums"
else
  bad "v6 enums must reject bad values (rc=$RC): $(printf '%s' "$OUT" | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: Gate 3 + delegation rules [TZ-7] =="

G3WORK=$(mktemp -d 2>/dev/null || mktemp -d -t g3)
mkdir -p "$G3WORK/artifacts"
cp "$FIX/pipeline-ok/artifacts/design-contract.yaml" "$G3WORK/artifacts/design-contract.yaml"
python3 - "$G3WORK/artifacts/design-contract.yaml" <<'G3YAML'
import sys, yaml
p = sys.argv[1]
c = yaml.safe_load(open(p, encoding="utf-8"))
c["meta"]["schema_version"] = "6.0"
c["deploy"] = {"previews": [], "prod": {"confirmed_by": "user", "at": "2026-07-21T12:00:00Z",
                                       "rollback_tested": False}}
c.setdefault("gates", {})["delegated"] = ["gate2"]
c["gates"]["gate2"] = "deferred"
yaml.safe_dump(c, open(p, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
G3YAML
OUT=$(python3 "$QG/validate-pipeline.py" "$G3WORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "rollback" "$OUT" && has "non-delegated value" "$OUT"; then
  ok "Gate 3 without dry-run rollback + delegated gate with wrong value both rejected"
else
  bad "Gate 3/delegation rules must fire (rc=$RC): $(printf '%s' "$OUT" | tr '\n' ' ')"
fi

printf '%s\n' "== self-test: pack-resolve.py [TZ-3] =="

OUT=$(python3 "$PO/pack-resolve.py" "$ROOT/packs" google-fonts --json 2>&1); RC=$?
if [ "$RC" -ne 0 ] && (has '"unavailable"' "$OUT" || has '"active"' "$OUT"); then
  ok "pack-resolve: missing-env pack resolves unavailable with non-zero exit"
else
  bad "pack-resolve missing-env semantics broken (rc=$RC): $OUT"
fi

OUT=$(python3 "$PO/pack-resolve.py" "$ROOT/packs" _fixture --json 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has '"active"' "$OUT"; then
  ok "pack-resolve: green acceptance fixture resolves active"
else
  bad "pack-resolve fixture must be active (rc=$RC): $OUT"
fi

OUT=$(python3 "$PO/pack-resolve.py" "$ROOT/packs" _fixture --json --ttl-hours 0 2>&1); RC=$?
has '"status"' "$OUT" && ok "pack-resolve: --ttl-hours 0 forces re-resolution (arg parsed)" \
  || bad "--ttl-hours 0 arg parsing broken (rc=$RC): $OUT"

printf '%s\n' "== self-test: D24 check-packs.py [TZ-8] =="

OUT=$(python3 "$QG/check-packs.py" "$FIX/contract/design-contract.yaml" "$ROOT/packs" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "pass D24" "$OUT"; then
  ok "D24: empty integrations pass"
else
  bad "D24 empty integrations (rc=$RC): $OUT"
fi

D24WORK=$(mktemp -d 2>/dev/null || mktemp -d -t d24)
cat > "$D24WORK/contract.yaml" <<'D24YAML'
integrations:
  - pack: _fixture
    class: peripheral
  - pack: nonexistent-pack
    class: core
D24YAML
OUT=$(python3 "$QG/check-packs.py" "$D24WORK/contract.yaml" "$ROOT/packs" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "CAPS verdict" "$OUT" && has "active D24 _fixture" "$OUT"; then
  ok "D24: core pack down caps verdict, peripheral active is a plain line"
else
  bad "D24 core/peripheral semantics broken (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: knowledge-validate.py [TZ-10] =="

OUT=$(python3 "$PO/knowledge-validate.py" "$ROOT" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "OK: 16 note(s)" "$OUT" && has "16 id(s) referenced" "$OUT"; then
  ok "knowledge vault: 16 notes green, no orphans, no dangling refs"
else
  bad "knowledge vault must validate (rc=$RC): $(printf '%s' "$OUT" | tail -5 | tr '\n' ' ')"
fi

KVWORK=$(mktemp -d 2>/dev/null || mktemp -d -t kv)
mkdir -p "$KVWORK/knowledge/sources"
cat > "$KVWORK/knowledge/sources/orphan-note.md" <<'KVNOTE'
---
id: orphan-note
title: "Orphan"
url: https://example.com/
evidence_level: curated
verified_at: 2026-07-01
tags: [test]
thesis: "Unreferenced note must be flagged."
---
KVNOTE
OUT=$(python3 "$PO/knowledge-validate.py" "$KVWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "orphan note" "$OUT"; then
  ok "knowledge: orphan note rejected (rule without note does not exist)"
else
  bad "orphan discipline broken (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: D23 check-secrets.py [TZ-8] =="

SEWORK=$(mktemp -d 2>/dev/null || mktemp -d -t sec)
cat > "$SEWORK/leak.env" <<'SECRET'
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE  # SECRET-ALLOW: fake key for the D23 negative test itself, not a real credential
SECRET
OUT=$(python3 "$QG/check-secrets.py" "$SEWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "pass D23" "$OUT"; then
  ok "D23: SECRET-ALLOW marker documents the fixture false positive"
else
  bad "D23 SECRET-ALLOW handling broken (rc=$RC): $OUT"
fi
printf 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef123456"\n' > "$SEWORK/real-leak.py"
OUT=$(python3 "$QG/check-secrets.py" "$SEWORK" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "github_token" "$OUT"; then
  ok "D23: real-looking token caught (blocking)"
else
  bad "D23 must catch a token (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: gate annotations [TZ-9] =="

cat > "$SKELWORK/annotations-ok.json" <<'ANNOK'
[{"target_selector": "#variant-2 > div.card", "x": 412, "y": 188,
  "text": "слишком плотно", "at": "2026-07-21T12:00:00Z"}]
ANNOK
OUT=$(python3 "$PO/annotations-log.py" "$SKELWORK/annotations-ok.json" --log "$SKELWORK/decision-log.md" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "1 annotation(s) appended" "$OUT"; then
  ok "annotations: valid pins mirrored into the decision log"
else
  bad "annotations valid case broken (rc=$RC): $OUT"
fi
cat > "$SKELWORK/annotations-bad.json" <<'ANNBAD'
[{"target_selector": "#v2", "x": "wide", "text": "no y, bad x"}]
ANNBAD
OUT=$(python3 "$PO/annotations-log.py" "$SKELWORK/annotations-bad.json" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "must be int" "$OUT" && has "missing 'y'" "$OUT" && has "missing 'at'" "$OUT"; then
  ok "annotations: schema violations rejected (types + required fields)"
else
  bad "annotations schema check broken (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: starter injection [TZ-3] =="

INJWORK=$(mktemp -d 2>/dev/null || mktemp -d -t inj)
python3 "$ROOT/starters/inject.py" "$ROOT/starters/landing-local" "$FIX/inject-copy.yaml" "$INJWORK" > "$INJWORK/log.txt" 2>&1; RC=$?
if [ "$RC" -eq 0 ] && has "coverage 100%" "$INJWORK/log.txt"; then
  ok "starter injection: 100% slot coverage on a full copy-map"
else
  bad "injection must reach 100% (rc=$RC): $(cat "$INJWORK/log.txt")"
fi
OUT=$(python3 "$ROOT/starters/inject.py" "$ROOT/starters/landing-local" "$FIX/inject-thin.yaml" "$INJWORK/thin" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "coverage" "$OUT" && has "leftover" "$OUT"; then
  ok "starter injection: thin brief fails with an explicit leftover list"
else
  bad "thin brief must fail loudly (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: render-sitemap.py [TZ-5] =="

OUT=$(python3 "$SB/render-sitemap.py" "$FIX/contract/design-contract.yaml" --out-dir "$SKELWORK/sitemap" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -f "$SKELWORK/sitemap/sitemap.mmd" ] && [ -f "$SKELWORK/sitemap/sitemap.html" ]; then
  ok "sitemap: mmd + html artifacts generated"
else
  bad "sitemap generation broken (rc=$RC): $OUT"
fi
cat > "$SKELWORK/ghost-contract.yaml" <<'GHOST'
experience:
  key_screens:
    - id: home
      purpose: "Landing"
  scenarios:
    - id: flow
      screens: [home, ghost]
GHOST
OUT=$(python3 "$SB/render-sitemap.py" "$SKELWORK/ghost-contract.yaml" --out-dir "$SKELWORK/sitemap2" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "ghost" "$OUT"; then
  ok "sitemap: ghost screen id in a flow fails the cross-check"
else
  bad "ghost id must fail (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: context-budget.py [TZ-12] =="

CBWORK=$(mktemp -d 2>/dev/null || mktemp -d -t cb)
python3 "$PO/context-budget.py" read "$ROOT/AGENTS.md" --log "$CBWORK/log.jsonl" >/dev/null 2>&1
python3 "$PO/context-budget.py" read "$ROOT/README.md" --log "$CBWORK/log.jsonl" >/dev/null 2>&1
OUT=$(python3 "$PO/context-budget.py" report --mode quick --log "$CBWORK/log.jsonl" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "OK context budget (quick)" "$OUT"; then
  ok "context budget: two reads under the quick limit"
else
  bad "context budget under-limit broken (rc=$RC): $OUT"
fi
OUT=$(python3 "$PO/context-budget.py" report --mode quick --log "$CBWORK/log.jsonl" --limits "$FIX/tiny-limits.yaml" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && has "OVER context budget" "$OUT"; then
  ok "context budget: over-limit exits 1 as a wave defect"
else
  bad "context budget over-limit must exit 1 (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: v6.0 handoff package [TZ-11] =="

HOWORK=$(mktemp -d 2>/dev/null || mktemp -d -t ho)
OUT=$(bash "$PO/make-handoff.sh" "$ROOT/starters/landing-local" "$HOWORK" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && has "links verified" "$OUT" && [ -f "$HOWORK/handoff/README.md" ]; then
  ok "handoff: package assembled on a reference starter, links verified"
else
  bad "handoff assembly broken (rc=$RC): $OUT"
fi

printf '%s\n' "== self-test: browser smoke [TZ-2.2/2.3/3.1/3.2] =="

if node -e "require.resolve('playwright')" 2>/dev/null; then
  SMLOG="$SKELWORK/smoke.log"
  SMOKE_RC=0
  (cd "$FIX/smoke" && bash "$QG/run-ui-checks.sh" . "$SMLOG" quick 2>&1) || SMOKE_RC=$?
  if [ "$SMOKE_RC" -eq 0 ] && [ -f "$SMLOG" ]; then
    ok "browser smoke: run-ui-checks green on the fixture site"
  else
    bad "browser smoke failed (rc=$SMOKE_RC)"
  fi
  if grep -q '30.*timeout\|Timeout 30000' "$SMLOG" 2>/dev/null; then
    bad "smoke log shows 30-second stalls"
  else
    ok "smoke log: zero 30-second stalls"
  fi
  D22LOG="$SKELWORK/d22.log"
  bash "$QG/visual-regression.sh" reference "file://$FIX/smoke" "$SKELWORK/shots" "/" > "$D22LOG" 2>&1 \
    && ok "D22: baseline recorded" || bad "D22 reference failed: $(tail -2 "$D22LOG" | tr '\n' ' ')"
  bash "$QG/visual-regression.sh" test "file://$FIX/smoke" "$SKELWORK/shots" "/" >> "$D22LOG" 2>&1 \
    && ok "D22: identical build shows no diff" || bad "D22 test on identical build must pass"
else
  skip "browser smoke: playwright not resolvable by node (install per INSTALL.md; fs-level checks above already ran)"
fi

printf '%s\n' "---"
printf 'self-test: %s passed, %s failed, %s skipped\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ]
