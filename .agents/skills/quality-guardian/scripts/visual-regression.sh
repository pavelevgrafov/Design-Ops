#!/bin/sh
# visual-regression.sh — D22: screenshot diff as proof "the restyle broke
# nothing". Modes:
#   reference  record baseline shots (on starter production or after Gate 2)
#   test       compare current build against baseline; any unapproved diff
#              is a BLOCKING fail
#   approve    accept current shots as the new baseline — a HUMAN decision,
#              recorded in the decision log by the orchestrator
# Usage: visual-regression.sh <reference|test|approve> <base_url> <shots_dir> [pages]
# Example: visual-regression.sh test http://localhost:3000 artifacts/audit/shots "/ /pricing"
# Degradation: without playwright — explicit `unavailable` + verdict cap.
set -u
MODE=${1:-}; BASE=${2:-}; SHOTS=${3:-}; PAGES=${4:-"/"}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -z "$MODE" ] || [ -z "$BASE" ] || [ -z "$SHOTS" ]; then
  sed -n '1,12p' "$0"
  exit 1
fi

if ! node -e "require.resolve('playwright')" 2>/dev/null; then
  echo "unavailable D22 visual-regression: playwright not installed" \
       "(npm i -D playwright && npx playwright install chromium) — caps verdict"
  exit 2
fi

mkdir -p "$SHOTS/reference" "$SHOTS/current" "$SHOTS/diff"

run_shots() {  # $1 = target dir
  node - "$BASE" "$1" "$PAGES" <<'NODE'
const [base, dir, pagesArg] = process.argv.slice(2);
const pages = pagesArg.split(" ").filter(Boolean);
const { chromium } = require("playwright");
const slug = p => (p === "/" ? "index" : p.replace(/\W+/g, "_"));
(async () => {
  const browser = await chromium.launch();
  for (const size of [[1440, 900], [390, 844]]) {
    const page = await browser.newPage({
      viewport: { width: size[0], height: size[1] } });
    for (const p of pages) {
      await page.goto(base + p, { waitUntil: "networkidle",
                                  timeout: 15000 }).catch(() => {});
      await page.screenshot({
        path: `${dir}/${slug(p)}-${size[0]}.png`, fullPage: false });
    }
    await page.close();
  }
  await browser.close();
})();
NODE
}

case "$MODE" in
  reference)
    run_shots "$SHOTS/reference" && echo "OK D22: baseline recorded in $SHOTS/reference"
    ;;
  test)
    run_shots "$SHOTS/current" || exit 1
    diffs=0
    for ref in "$SHOTS"/reference/*.png; do
      [ -e "$ref" ] || { echo "unavailable D22: empty baseline — run reference first"; exit 2; }
      name=$(basename "$ref")
      cur="$SHOTS/current/$name"
      if [ ! -e "$cur" ]; then
        echo "fail D22: missing current shot for $name"; diffs=$((diffs+1)); continue
      fi
      if ! cmp -s "$ref" "$cur"; then
        # byte-level fast path failed; keep the pair for human review
        cp "$ref" "$SHOTS/diff/ref-$name" 2>/dev/null || true
        cp "$cur" "$SHOTS/diff/new-$name" 2>/dev/null || true
        echo "diff D22: $name differs — needs human approve (pairs in $SHOTS/diff/)"
        diffs=$((diffs+1))
      fi
    done
    if [ "$diffs" -gt 0 ]; then
      echo "fail D22: $diffs unapproved diff(s) — BLOCKING until approved"
      exit 1
    fi
    echo "pass D22: no visual diffs"
    ;;
  approve)
    if [ ! -d "$SHOTS/current" ] || [ -z "$(ls -A "$SHOTS/current" 2>/dev/null)" ]; then
      echo "fail D22 approve: nothing to approve (run test first)"
      exit 1
    fi
    cp "$SHOTS"/current/*.png "$SHOTS/reference/" &&
      echo "OK D22: current shots approved as new baseline (record in decision log)"
    ;;
  *)
    echo "unknown mode: $MODE (reference|test|approve)"
    exit 1
    ;;
esac
