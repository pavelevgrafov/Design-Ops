#!/usr/bin/env bash
# install.sh — one-command install of the Design-Ops pipeline (v6.0, TZ-12).
#
#   bash install.sh [target-dir]
#
# Copies the package into the target repo (default: current directory),
# restores script permissions, checks dependencies, runs the self-test and
# prints the ready line. C12 applies: a fresh copy must work with zero edits.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

echo "== install: $SRC -> $TARGET"

# --- copy -----------------------------------------------------------------
for item in AGENTS.md README.md INSTALL.md LICENSE .agents eval starters \
            skins packs knowledge docs showcase radar; do
  [ -e "$SRC/$item" ] || continue
  if [ "$TARGET" != "$SRC" ]; then
    rm -rf "$TARGET/$item"
    cp -R "$SRC/$item" "$TARGET/$item"
  fi
done

# --- permissions ------------------------------------------------------------
chmod +x "$TARGET"/.agents/skills/*/scripts/*.sh \
         "$TARGET"/.agents/skills/*/scripts/*.py \
         "$TARGET"/starters/recheck.sh "$TARGET"/starters/harvest.py \
         "$TARGET"/packs/recheck.sh 2>/dev/null || true

# --- dependencies -------------------------------------------------------------
MISSING=""
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || MISSING="$MISSING python>=3.10"
python3 -c 'import yaml' 2>/dev/null || MISSING="$MISSING pyyaml(pip install pyyaml)"
bash --version 2>/dev/null | head -1 | grep -qE 'version [3-9]' \
  || MISSING="$MISSING bash>=3.2"
if [ -n "$MISSING" ]; then
  echo "fail: missing dependencies:$MISSING" >&2
  exit 1
fi
if node -e "require.resolve('playwright')" 2>/dev/null; then
  echo "== playwright: present (browser checks D2/D12/D13/D15/D20/D21/D22 active)"
else
  echo "== playwright: absent — browser checks will honestly report 'unavailable'"
  echo "   (enable: npm i -D playwright axe-core && npx playwright install chromium)"
fi

# --- subscription tier (v7.0) -------------------------------------------------
# Core pipeline is fully open source — always. The tier only gates future
# ecosystem assets (packs-pro/, skins-pro/, starters-pro/). Default: free.
CFG="$TARGET/.agents/config.yaml"
if [ ! -f "$CFG" ]; then
  mkdir -p "$TARGET/.agents"
  cat > "$CFG" <<'YAML'
# Design-Ops install configuration.
# subscription.tier: free | pro | team | enterprise — gates ecosystem assets
# (packs-pro/, skins-pro/, starters-pro/); the core pipeline is always full.
subscription:
  tier: free
YAML
  echo "== config: created .agents/config.yaml (subscription.tier: free)"
fi
TIER=$(sed -n 's/^[[:space:]]*tier:[[:space:]]*\([a-z]*\).*/\1/p' "$CFG" | head -1)
TIER="${TIER:-free}"
echo "== subscription tier: $TIER"
if [ "$TIER" = "free" ]; then
  for prodir in packs-pro skins-pro starters-pro; do
    if [ -d "$SRC/$prodir" ] && [ "$TARGET" != "$SRC" ]; then
      rm -rf "$TARGET/$prodir"
      echo "== $prodir: skipped (Upgrade to Pro for ecosystem assets)"
    fi
  done
else
  for prodir in packs-pro skins-pro starters-pro; do
    [ -e "$SRC/$prodir" ] && [ "$TARGET" != "$SRC" ] \
      && { rm -rf "$TARGET/$prodir"; cp -R "$SRC/$prodir" "$TARGET/$prodir"; }
  done
fi

# --- self-test ---------------------------------------------------------------
echo "== self-test"
if bash "$TARGET/eval/selftest/run-self-test.sh"; then
  echo "== готов к работе: pipeline v7.0 installed in $TARGET"
  echo "   first run: prompt P01 from eval/example-prompts.md (rubric: eval/eval-rubric.md)"
else
  echo "fail: self-test red — do not use the pipeline until fixed" >&2
  exit 1
fi
