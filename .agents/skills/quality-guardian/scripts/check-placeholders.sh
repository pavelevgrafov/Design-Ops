#!/usr/bin/env bash
# check-placeholders.sh — D10 + D14 (partial): placeholder copy, hotlinks, image hygiene.
# Usage: bash check-placeholders.sh [project_root] [assets_dir]
# Exit 0 = pass, 1 = fail.
set -uo pipefail

ROOT="${1:-.}"
ASSETS="${2:-$ROOT/assets}"
FAILS=0
fail() { printf 'FAIL: %s\n' "$*"; FAILS=$((FAILS+1)); }
pass() { printf 'pass: %s\n' "$*"; }

SRC_INCLUDES=(--include='*.html' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.md' --include='*.css')

# --- 1. Placeholder copy -----------------------------------------------------
if grep -rniE 'lorem ipsum|dolor sit amet|consectetur adipiscing|text goes here|TODO:?\s*(copy|text)|placeholder text|coming soon™|xxx+' \
  "$ROOT" "${SRC_INCLUDES[@]}" 2>/dev/null | grep -v node_modules | grep -q .; then
  grep -rniE 'lorem ipsum|dolor sit amet|consectetur adipiscing|text goes here|TODO:?\s*(copy|text)|placeholder text' \
    "$ROOT" "${SRC_INCLUDES[@]}" 2>/dev/null | grep -v node_modules | head -5
  fail "placeholder copy found"
else
  pass "no placeholder copy"
fi

# --- 2. Hotlinked images / placeholder services -------------------------------
HOTLINK=$(grep -rnoE 'https?://[^"'\'' )]*(unsplash\.com|picsum\.photos|placehold\.(co|it)|via\.placeholder\.com|dummyimage\.com|loremflickr\.com|placekitten\.com|source\.unsplash|images\.unsplash)[^"'\'' )]*' \
  "$ROOT" "${SRC_INCLUDES[@]}" 2>/dev/null | grep -v node_modules || true)
if [ -n "$HOTLINK" ]; then
  printf '%s\n' "$HOTLINK" | head -5
  fail "hotlinked/placeholder image URLs found"
else
  pass "no hotlinked or placeholder-service images"
fi

# --- 3. External http(s) image src in markup (any host) ------------------------
EXT_IMG=$(grep -rnoE '<img[^>]*src="https?://[^"]*"' "$ROOT" \
  --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' 2>/dev/null \
  | grep -v node_modules || true)
if [ -n "$EXT_IMG" ]; then
  printf '%s\n' "$EXT_IMG" | head -5
  fail "external <img> sources (images must be local)"
else
  pass "all <img> sources local"
fi

# --- 4. Image alt + size (D14, fs-level) ----------------------------------------
MISSING_ALT=$(grep -rnoE '<img[^>]*>' "$ROOT" \
  --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
  | grep -v node_modules | grep -v 'alt=' || true)
if [ -n "$MISSING_ALT" ]; then
  printf '%s\n' "$MISSING_ALT" | head -5
  fail "images without alt attribute"
else
  pass "all images have alt"
fi

if [ -d "$ASSETS" ]; then
  OVERSIZE=$(find "$ASSETS" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.avif' -o -iname '*.gif' \) -size +300k 2>/dev/null || true)
  if [ -n "$OVERSIZE" ]; then
    printf '%s\n' "$OVERSIZE" | while IFS= read -r f; do
      printf '  %s — %s KB\n' "$f" "$(( $(stat -c%s "$f") / 1024 ))"
    done
    fail "images over 300 KB"
  else
    pass "all images ≤ 300 KB"
  fi
else
  printf 'note: assets dir %s not found; size check degraded (verify manually)\n' "$ASSETS"
fi

printf '%s\n' "---"
if [ "$FAILS" -gt 0 ]; then
  printf 'check-placeholders: FAIL (%s)\n' "$FAILS"; exit 1
fi
printf 'check-placeholders: PASS\n'; exit 0
