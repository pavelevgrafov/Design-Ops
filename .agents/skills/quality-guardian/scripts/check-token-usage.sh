#!/usr/bin/env bash
# check-token-usage.sh — D9: components consume semantic tokens, not raw values.
# Usage: bash check-token-usage.sh [src_root]
# Exit 0 = pass, 1 = fail.
# v5.2: BSD grep compatible — POSIX classes, no perl shorthands [TZ-1.2]
set -uo pipefail

ROOT="${1:-src}"
FAILS=0
fail() { printf 'FAIL: %s\n' "$*"; FAILS=$((FAILS+1)); }

# --- scan scope: never audit the vendored pipeline itself ---------------------
# A project installs the toolkit INTO itself (install.sh), so a plain walk of
# the project root scans .agents/, packs/, eval/selftest/fixture/ (which holds
# deliberate traps) and reports them as product defects. Override with
# DOPS_SCAN_EXCLUDE="dir1|dir2" when a project genuinely ships such a folder.
DOPS_EXCLUDE_RE="${DOPS_SCAN_EXCLUDE:-node_modules|/\.git/|/\.agents/|/eval/|/packs/|/packs-pro/|/starters/|/starters-pro/|/skins/|/skins-pro/|/knowledge/|/docs/|/radar/|/showcase/|/tools/|/dist/|/build/|__pycache__|/\.pack-cache/|/artifacts/audit/}"
# Scanning such a directory ON PURPOSE (e.g. eval/selftest/fixture) must not be
# filtered away — the exclusion protects a project-root walk, nothing else.
if printf '%s' "$(cd "$ROOT" 2>/dev/null && pwd || printf '%s' "$ROOT")" \
   | grep -qE "$DOPS_EXCLUDE_RE"; then DOPS_EXCLUDE_RE='$^'; fi

# Files where raw values are LEGAL (token declarations / generated outputs)
LEGAL_PATTERN='(tokens\.css|tokens\.theme\.css|tokens\.json|globals\.css|tailwind\.config|theme\.ts$|\.d\.ts$)'

is_legal_file() { printf '%s' "$1" | grep -qE "$LEGAL_PATTERN"; }

# --- 1. Raw colors in components ----------------------------------------------
RAW_COLOR=$(grep -rnoE '#[0-9a-fA-F]{3,8}([^0-9a-fA-F]|$)|rgba?\([^)]*\)|hsla?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\)' \
  "$ROOT" --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.css' 2>/dev/null \
  | grep -vE "$DOPS_EXCLUDE_RE" || true)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  file=$(printf '%s' "$line" | cut -d: -f1)
  is_legal_file "$file" && continue
  if printf '%s' "$line" | grep -qE 'var\(--[a-z-]+,[[:space:]]*(#[0-9a-fA-F]{3,8}|rgba?\()'; then
    continue  # CSS var with fallback is fine
  fi
  printf '  raw color: %s\n' "$line"
  FAILS=$((FAILS+1))
done <<< "$RAW_COLOR"
[ "$FAILS" -eq 0 ] && printf 'pass: no raw colors outside token files\n'

# --- 2. Raw font-family in components -------------------------------------------
FONT_START=$FAILS
RAW_FONT=$(grep -rnoE 'font-family:[[:space:]]*[^;}]+' "$ROOT" \
  --include='*.tsx' --include='*.jsx' --include='*.css' 2>/dev/null \
  | grep -vE "$DOPS_EXCLUDE_RE" | grep -v 'var(--' || true)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  file=$(printf '%s' "$line" | cut -d: -f1)
  is_legal_file "$file" && continue
  printf '  raw font-family: %s\n' "$line"
  FAILS=$((FAILS+1))
done <<< "$RAW_FONT"
[ "$FAILS" -eq "$FONT_START" ] && printf 'pass: font-family only via tokens\n'

# --- 3. Arbitrary Tailwind values (spot check) -----------------------------------
ARB=$(grep -rnoE '(^|[^a-zA-Z-])(text|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|w|h)-\[[0-9][^]]*\]' "$ROOT" \
  --include='*.tsx' --include='*.jsx' 2>/dev/null | grep -vE "$DOPS_EXCLUDE_RE" || true)
ARB_COUNT=$(printf '%s' "$ARB" | grep -c . || true)
if [ "${ARB_COUNT:-0}" -gt 0 ]; then
  if [ "$ARB_COUNT" -gt 10 ]; then
    printf '  arbitrary Tailwind values: %s (budget 10). Extend tokens instead:\n' "$ARB_COUNT"
    printf '%s\n' "$ARB" | head -5
    FAILS=$((FAILS+1))
  else
    printf 'note: %s arbitrary Tailwind value(s) within budget (≤10)\n' "$ARB_COUNT"
  fi
fi

printf '%s\n' "---"
if [ "$FAILS" -gt 0 ]; then
  printf 'check-token-usage: FAIL (%s). Skin property violated — route back to K2.\n' "$FAILS"; exit 1
fi
printf 'check-token-usage: PASS — components live on tokens.\n'; exit 0
