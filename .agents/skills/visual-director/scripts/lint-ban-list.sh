#!/usr/bin/env bash
# lint-ban-list.sh — D11: machine-linted AI-slop ban-list (v5.2).
# Scans direction docs, CSS, and components for banned patterns.
# Usage: bash lint-ban-list.sh [scan_root] [--allow direction-id]
#   --allow: a direction id whose doc contains written justifications
#            (lines starting with "ALLOW:") for specific banned keys.
# Exit 0 = clean, 1 = banned patterns found.
# v5.2: bash 3.2 (no bash-4 case conversion); BSD grep/sed (POSIX
#       classes, no perl shorthands); grep -z is GNU-only → capability
#       probe with honest skip                                       [TZ-1.1/1.2]
set -uo pipefail

ROOT="${1:-.}"
ALLOW_DIR=""
if [ "${2:-}" = "--allow" ] && [ -n "${3:-}" ]; then ALLOW_DIR="$3"; fi

HITS=0
hit() { printf 'BAN[%s]: %s\n' "$1" "$2"; HITS=$((HITS+1)); }

# --- 1. Fonts: banned in FIRST position of font-family stacks -------------
FONT_STACKS=$(grep -rnoE 'font-family:[^;}]*' "$ROOT" \
  --include='*.css' --include='*.html' --include='*.tsx' --include='*.jsx' \
  --include='*.json' --include='*.md' 2>/dev/null \
  | grep -v node_modules | grep -v 'lint-ban-list' || true)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  first=$(printf '%s' "$line" | sed -E 's/.*font-family:[[:space:]]*//; s/^[[:space:]]*["'\'']?([^,"'\'']*)["'\'']?.*/\1/' | tr -d ' ' )
  first_lc=$(printf '%s' "$first" | tr 'A-Z' 'a-z')
  case "$first_lc" in
    inter|roboto|arial|spacegrotesk|space-grotesk)
      hit "font-first-position" "$line" ;;
  esac
done <<< "$FONT_STACKS"

# --- 2. Indigo→purple gradients --------------------------------------------
GRAD=$(grep -rniE 'linear-gradient\([^)]*(indigo|#6366f1|#4f46e5|#5b21b6)[^)]*(purple|#a855f7|#9333ea|#7c3aed)|(indigo|#6366f1)[^)]*(purple|#a855f7)|from-indigo-[0-9]+[^"'\'' ]*to-purple-[0-9]+|from-purple-[0-9]+[^"'\'' ]*to-indigo-[0-9]+' \
  "$ROOT" --include='*.css' --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
  | grep -v node_modules | grep -v 'lint-ban-list' || true)
[ -n "$GRAD" ] && { printf '%s\n' "$GRAD" | head -5; hit "indigo-purple-gradient" "$(printf '%s\n' "$GRAD" | wc -l | tr -d ' ') occurrence(s)"; }

# --- 3. Glassmorphism --------------------------------------------------------
GLASS=$(grep -rniE 'backdrop-(filter|blur)|bg-white/(5|10|20)[^0-9]|border-white/(10|20)' "$ROOT" \
  --include='*.css' --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
  | grep -v node_modules | grep -v 'lint-ban-list' || true)
[ -n "$GLASS" ] && hit "glassmorphism" "$(printf '%s\n' "$GLASS" | wc -l | tr -d ' ') occurrence(s): $(printf '%s\n' "$GLASS" | head -2)"

# --- 4. Bento "hero + 3 identical cards" -------------------------------------
# grep -z (multiline) is GNU-only: probe once, skip honestly on BSD/macOS.
if printf 'a\0b\n' | grep -qzE 'a.b' 2>/dev/null; then
  BENTO=$(grep -rnzE 'grid[^>]*grid-cols-3[^>]*>([[:space:]]*<div[^>]*class="[^"]*"[^>]*>[[:space:]]*(<svg|<[^>]*icon)[^]*?(<h[23])[^]*?<p[^]*?</div>[[:space:]]*){3}' \
    "$ROOT" --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
    | grep -v node_modules | head -3 || true)
  [ -n "$BENTO" ] && hit "bento-hero-3-cards" "3 identical icon+title+text cards detected"
else
  printf 'skip: bento-hero-3-cards check requires GNU grep -z (unavailable on this platform)\n'
fi

# --- 5. Blobs -----------------------------------------------------------------
BLOB=$(grep -rniE 'blob|border-radius:[[:space:]]*[0-9]+%[[:space:]]+[0-9]+%[[:space:]]+[0-9]+%[[:space:]]+[0-9]+%[[:space:]]*/[[:space:]]*[0-9]+%|organic-shape' "$ROOT" \
  --include='*.css' --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.svg' 2>/dev/null \
  | grep -v node_modules | grep -v 'lint-ban-list' | grep -viE 'blob\(|binary|README|CHANGELOG' || true)
[ -n "$BLOB" ] && hit "blobs" "$(printf '%s\n' "$BLOB" | wc -l | tr -d ' ') occurrence(s): $(printf '%s\n' "$BLOB" | head -2)"

# --- 6. Icon-per-label decoration ----------------------------------------------
ICONLABEL=$(grep -rnoE '<li[^>]*>[[:space:]]*(<svg|<img[^>]*icon|<[^>]*class="[^"]*icon)[^>]*>[^<]{0,40}' "$ROOT" \
  --include='*.html' --include='*.tsx' --include='*.jsx' 2>/dev/null \
  | grep -v node_modules | wc -l | tr -d ' ')
case "$ICONLABEL" in ''|*[!0-9]*) ICONLABEL=0 ;; esac
if [ "$ICONLABEL" -ge 3 ]; then
  hit "icon-per-label" "$ICONLABEL decorated list items"
fi

# --- 7. Marketing slop copy -----------------------------------------------------
SLOP=$(grep -rniE 'elevate your|seamless(ly)? |supercharge|unlock the power|revolutionize your|🚀' "$ROOT" \
  --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.md' 2>/dev/null \
  | grep -v node_modules | grep -v 'lint-ban-list' | grep -v 'ban-list' || true)
[ -n "$SLOP" ] && hit "marketing-slop" "$(printf '%s\n' "$SLOP" | wc -l | tr -d ' ') occurrence(s): $(printf '%s\n' "$SLOP" | head -2)"

# --- Allowlist note --------------------------------------------------------------
if [ -n "$ALLOW_DIR" ] && [ "$HITS" -gt 0 ]; then
  printf 'note: --allow %s given; verify each BAN line has an "ALLOW:" justification in that direction doc.\n' "$ALLOW_DIR"
fi

printf '%s\n' "---"
if [ "$HITS" -gt 0 ]; then
  printf 'lint-ban-list: FAIL (%s hit group(s)). Remove or justify in the direction doc.\n' "$HITS"
  exit 1
fi
printf 'lint-ban-list: PASS — no banned defaults detected.\n'
exit 0
