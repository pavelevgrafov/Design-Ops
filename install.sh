#!/usr/bin/env bash
# install.sh — one-command install of the Design-Ops pipeline (v7.1).
#
#   bash install.sh [target-dir]            fresh install (C12: zero edits)
#   bash install.sh --update [target-dir]   safe update of an existing install:
#                                           overlay sync, no deletions, local
#                                           files preserved, diff report shown
#   bash install.sh --update --dry-run [t]  report only, no writes
#
# Copies the package into the target repo (default: current directory),
# restores script permissions, checks dependencies, runs the self-test and
# prints the ready line. C12 applies: a fresh copy must work with zero edits.
set -euo pipefail

MODE="install"
DRYRUN=0
ARGS=""
for a in "$@"; do
  case "$a" in
    --update) MODE="update" ;;
    --dry-run) DRYRUN=1 ;;
    *) ARGS="$a" ;;
  esac
done

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${ARGS:-.}"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

# Every top-level path the package ships is listed here. Two were missing and
# case №1 found both:
#   * `.github` — eval/selftest asserts that the end-to-end job calls
#     eval/e2e/rehearse.sh (amendment 07 §2), so an install without the
#     workflow is red on arrival, which contradicts C12 (a fresh copy works
#     with zero edits);
#   * `package*.json` — the browser half of the floor resolves `playwright`
#     from the project, and an install with no manifest has nothing to
#     `npm install`, so those probes skipped honestly and silently.
# The list is no longer maintained by memory: run-self-test.sh compares it
# against what the repository actually tracks and fails on the next omission.
ITEMS="AGENTS.md README.md INSTALL.md LICENSE install.sh mkdocs.yml package.json package-lock.json .agents tools eval starters skins packs knowledge docs showcase radar .github"
# Paths that belong to the LOCAL project, never to the package overlay:
LOCAL_KEEP=".agents/config.yaml .agents/knowledge-sync .pack-cache"

echo "== $MODE: $SRC -> $TARGET"

is_local_keep() {
  case "$1" in
    *.agents/config.yaml*|*.agents/knowledge-sync*|*.pack-cache*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ "$MODE" = "update" ] && [ "$TARGET" != "$SRC" ]; then
  # --- safe overlay sync: add/change package files, never delete local ones --
  ADDED=0; CHANGED=0
  REPORT=$(mktemp 2>/dev/null || mktemp -t upd)
  for item in $ITEMS; do
    [ -e "$SRC/$item" ] || continue
    find "$SRC/$item" -type f ! -path '*/.pack-cache/*' ! -name '.DS_Store'
  done | while read -r f; do
    rel="${f#$SRC/}"
    if is_local_keep "$rel"; then continue; fi
    dst="$TARGET/$rel"
    if [ ! -f "$dst" ]; then
      printf 'add:     %s\n' "$rel"
    elif ! cmp -s "$f" "$dst"; then
      printf 'change:  %s\n' "$rel"
    fi
  done > "$REPORT"
  ADDED=$(grep -c '^add:' "$REPORT" 2>/dev/null || true)
  CHANGED=$(grep -c '^change:' "$REPORT" 2>/dev/null || true)
  ADDED=${ADDED:-0}; CHANGED=${CHANGED:-0}
  cat "$REPORT"
  echo "== update report: $ADDED to add, $CHANGED to change (local-only files untouched)"
  if [ "$DRYRUN" -eq 1 ]; then
    echo "== dry-run: nothing written"
    rm -f "$REPORT"
    exit 0
  fi
  for item in $ITEMS; do
    [ -e "$SRC/$item" ] || continue
    find "$SRC/$item" -type f ! -path '*/.pack-cache/*' ! -name '.DS_Store'
  done | while read -r f; do
    rel="${f#$SRC/}"
    if is_local_keep "$rel"; then continue; fi
    dst="$TARGET/$rel"
    if [ ! -f "$dst" ] || ! cmp -s "$f" "$dst"; then
      mkdir -p "$(dirname "$dst")"
      cp "$f" "$dst"
    fi
  done
  rm -f "$REPORT"
  # contract schema follows the package version (idempotent)
  if [ -f "$TARGET/artifacts/design-contract.yaml" ]; then
    python3 "$TARGET/.agents/skills/pipeline-orchestrator/scripts/contract-migrate.py" \
      "$TARGET/artifacts/design-contract.yaml" || true
  fi
else
  # --- fresh install: full replace of package items ---------------------------
  for item in $ITEMS; do
    [ -e "$SRC/$item" ] || continue
    if [ "$TARGET" != "$SRC" ]; then
      rm -rf "$TARGET/$item"
      cp -R "$SRC/$item" "$TARGET/$item"
    fi
  done
fi

# --- permissions ------------------------------------------------------------
chmod +x "$TARGET"/.agents/skills/*/scripts/*.sh \
         "$TARGET"/.agents/skills/*/scripts/*.py \
         "$TARGET"/starters/recheck.sh "$TARGET"/starters/harvest.py \
         "$TARGET"/packs/recheck.sh \
         "$TARGET"/tools/dops "$TARGET"/tools/*.py 2>/dev/null || true

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
# Resolution happens FROM THE TARGET: node walks up from its cwd, so asking
# here would answer for whatever directory the installer was launched in.
# The target now carries package.json, so the enable line is `npm install` —
# one command against a pinned manifest, not a remembered dependency list.
#
# This installer checks dependencies and never installs them (pyyaml above
# behaves the same way; `dops doctor --fix` is the one entry point that
# installs, and it says so). What changed is that the remedy is now a single
# command the package itself defines.
if (cd "$TARGET" && node -e "require.resolve('playwright')") 2>/dev/null; then
  echo "== playwright: present (browser checks D2/D12/D13/D15/D20/D21/D22 active)"
elif command -v node >/dev/null 2>&1; then
  echo "== playwright: absent — D2/D12/D13/D15/D20/D21 report 'unavailable' and"
  echo "   D22 visual regression does not run; the verdict caps at ready_with_caveats"
  echo "   (enable: cd $TARGET && npm install && npx playwright install chromium)"
else
  echo "== node: absent — the whole browser half of the floor stays unavailable"
  echo "   (enable: install node ≥20, then npm install && npx playwright install chromium)"
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

# --- knowledge provenance (v7.1 wiki-sync) ----------------------------------
# If UX_WIKI_PATH points at a local ux-wiki clone, vendor its constraints and
# pin the provenance in the contract; otherwise record an honest skip.
if [ -n "${UX_WIKI_PATH:-}" ] && [ -d "${UX_WIKI_PATH:-}/constraints" ]; then
  if [ -f "$TARGET/artifacts/design-contract.yaml" ]; then
    python3 "$TARGET/packs/wiki-sync/scripts/wiki-sync.py" \
      --contract "$TARGET/artifacts/design-contract.yaml" \
      --update --wiki-path "$UX_WIKI_PATH" \
      && echo "== wiki-sync: constraints vendored + pinned from $UX_WIKI_PATH"
  else
    echo "== wiki-sync: skipped (no contract yet; run after K0 creates artifacts/)"
  fi
else
  echo "== wiki-sync: UX_WIKI_PATH not set — provenance pin skipped (offline install)"
fi

# --- git hook (v7.1 gate enforcement) ----------------------------------------
HOOKS_PATH=$(git -C "$TARGET" config core.hooksPath 2>/dev/null || true)
if [ -d "$TARGET/.git" ]; then
  if [ -n "$HOOKS_PATH" ]; then
    echo "== git hook: skipped (global core.hooksPath=$HOOKS_PATH shadows repo hooks)"
    echo "   D19 integrity still enforced in K3 (validate-pipeline) and CI"
  else
    mkdir -p "$TARGET/.git/hooks"
    cp "$SRC/.agents/hooks/pre-commit" "$TARGET/.git/hooks/pre-commit"
    chmod +x "$TARGET/.git/hooks/pre-commit"
    echo "== git hook: pre-commit pipeline integrity (D19) installed"
  fi
else
  echo "== git hook: skipped (no .git in target)"
fi

# --- self-test ---------------------------------------------------------------
if [ "${DESIGN_OPS_SKIP_SELFTEST:-0}" = "1" ]; then
  echo "== self-test: skipped (DESIGN_OPS_SKIP_SELFTEST=1 — nested invocation)"
elif bash "$TARGET/eval/selftest/run-self-test.sh"; then
  echo "== готов к работе: pipeline v7.2 installed in $TARGET"
  echo "   first run: prompt P01 from eval/example-prompts.md (rubric: eval/eval-rubric.md)"
else
  echo "fail: self-test red — do not use the pipeline until fixed" >&2
  exit 1
fi
