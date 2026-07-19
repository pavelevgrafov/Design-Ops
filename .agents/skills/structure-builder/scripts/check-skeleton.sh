#!/usr/bin/env bash
# check-skeleton.sh — K1 exit check (+ neutralize-audit mode, CR-01).
# Usage:
#   bash check-skeleton.sh [skeleton_root] [manifest] [contract]
#   bash check-skeleton.sh --neutralize-audit <existing_code_root>
# Exit 0 = pass, 1 = fail. In --neutralize-audit mode violations are listed
# as a work log ("what had to be / still needs to be neutralized").
set -uo pipefail

AUDIT=0
if [ "${1:-}" = "--neutralize-audit" ]; then
  AUDIT=1; shift
fi
ROOT="${1:-.}"
MANIFEST="${2:-artifacts/skeleton/skeleton-manifest.yaml}"
CONTRACT="${3:-artifacts/design-contract.yaml}"
FAILS=0

note() { printf '%s\n' "$*"; }
fail() {
  if [ "$AUDIT" -eq 1 ]; then note "TO-FIX: $*"; else note "FAIL: $*"; fi
  FAILS=$((FAILS+1))
}
pass() { note "pass: $*"; }

# --- 1. Marker present on every screen ---------------------------------------
ALL_SCREENS=$(grep -rlE '<(html|main|section)|export default' "$ROOT" \
  --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
  | grep -v node_modules | grep -viE '(test|stories|\.d\.ts)' || true)
if [ -z "$ALL_SCREENS" ]; then
  fail "no screen files found under $ROOT"
else
  MISSING=0
  while IFS= read -r f; do
    if ! grep -q 'not_approved_visual_design' "$f"; then
      fail "marker missing in: $f"; MISSING=1
    fi
  done <<< "$ALL_SCREENS"
  [ "$MISSING" -eq 0 ] && pass "marker present on all screens"
fi

# --- 2. No placeholder copy ----------------------------------------------------
if grep -rniE 'lorem ipsum|dolor sit amet|consectetur|text goes here|TODO:?\s*copy|placeholder text' \
  "$ROOT" --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.md' 2>/dev/null \
  | grep -v node_modules | grep -v 'check-skeleton' | grep -q .; then
  fail "placeholder copy found (lorem/meta-placeholder)"
else
  pass "no placeholder copy"
fi

# --- 3. Neutrality: no visual properties ---------------------------------------
VISUAL_HITS=$(grep -rnoE 'linear-gradient|radial-gradient|backdrop-blur|box-shadow:\s*[^0 ][^;]*|font-family:\s*[^;]*(Inter|Roboto|Montserrat|Poppins|Playfair)|#[0-9a-fA-F]{6}' \
  "$ROOT" --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.css' 2>/dev/null \
  | grep -v node_modules || true)
NON_GRAY=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  hex=$(printf '%s' "$line" | grep -oE '#[0-9a-fA-F]{6}' | head -1)
  if [ -n "$hex" ]; then
    r=${hex:1:2}; g=${hex:3:2}; b=${hex:5:2}
    if [ "${r,,}" != "${g,,}" ] || [ "${g,,}" != "${b,,}" ]; then
      NON_GRAY="$NON_GRAY$line\n"
    fi
  else
    NON_GRAY="$NON_GRAY$line\n"
  fi
done <<< "$VISUAL_HITS"
if printf '%b' "$NON_GRAY" | grep -v '215 12%' | grep -q .; then
  fail "visual properties / non-gray colors found:"
  printf '%b' "$NON_GRAY" | grep -v '215 12%' | head -10
else
  pass "skeleton visually neutral (gray ramp only)"
fi

# --- 4. Contract screens implemented --------------------------------------------
if [ -f "$CONTRACT" ]; then
  KEY_SCREENS=$(sed -n '/^  key_screens:/,/^[a-z]/p' "$CONTRACT" | grep -oE 'id:\s*[a-z0-9_-]+' | awk '{print $2}' || true)
  for sid in $KEY_SCREENS; do
    if ! grep -rqiE "$sid" "$ROOT" --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null | grep -v node_modules | grep -q .; then
      fail "contract key_screen '$sid' not found in skeleton"
    fi
  done
  [ -n "$KEY_SCREENS" ] && pass "contract key screens present ($(printf '%s' "$KEY_SCREENS" | wc -l | tr -d ' ') checked)"
else
  note "skip: contract not found at $CONTRACT"
fi

# --- 5. Priority annotations ------------------------------------------------------
if grep -rqE 'data-priority="p[123]"' "$ROOT" --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null; then
  pass "priority annotations present"
else
  fail "no data-priority annotations found"
fi

note "---"
if [ "$AUDIT" -eq 1 ]; then
  if [ "$FAILS" -gt 0 ]; then
    note "neutralize-audit: $FAILS item(s) require neutralization (see TO-FIX list)."
    exit 1
  fi
  note "neutralize-audit: existing code is neutral — ready for K2."
  exit 0
fi
if [ "$FAILS" -gt 0 ]; then
  note "check-skeleton: FAIL ($FAILS problem(s)). Do NOT hand off to Gate 1."
  exit 1
fi
note "check-skeleton: PASS — skeleton is neutral, complete, reviewable."
exit 0
