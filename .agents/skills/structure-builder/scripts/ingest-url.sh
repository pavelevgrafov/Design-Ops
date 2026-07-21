#!/usr/bin/env bash
# ingest-url.sh — neutralize-input ingestion (v6.0, TZ-5).
# Fetches a URL with a local Playwright browser and saves the raw material
# for neutralization into artifacts/neutralize-input/<slug>/:
#   page.html       — DOM dump (as rendered)
#   page-1440.png   — full-page screenshot @1440
#   page-390.png    — full-page screenshot @390
# The agent then rebuilds a NEUTRAL skeleton from this material and proves it
# with check-skeleton.sh --neutralize-audit (unchanged v5.2 flow).
#
# Usage: bash ingest-url.sh <url> [out-dir]
# Exit: 0 ok, 2 playwright/browser unavailable (explicit status, not a skip).
set -euo pipefail

URL="${1:?usage: ingest-url.sh <url> [out-dir]}"
SLUG=$(printf '%s' "$URL" | sed -E 's#^[a-z]+://##; s#[^a-zA-Z0-9]+#-#g; s#^-+|-+$##g' | cut -c1-60)
OUT="${2:-artifacts/neutralize-input/$SLUG}"
mkdir -p "$OUT"

if ! node -e "require.resolve('playwright')" 2>/dev/null; then
  echo "unavailable: playwright not installed — capture the page manually"
  echo "(save HTML + screenshots @1440/@390 into $OUT) and continue the"
  echo "standard --neutralize-audit flow."
  exit 2
fi

URL="$URL" OUT="$OUT" node <<'NODE'
const { chromium } = require('playwright');
(async () => {
  const url = process.env.URL, out = process.env.OUT;
  const browser = await chromium.launch();
  try {
    for (const [w, h, tag] of [[1440, 900, '1440'], [390, 844, '390']]) {
      const page = await browser.newPage({ viewport: { width: w, height: h } });
      await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
      if (tag === '1440') {
        const fs = require('fs');
        fs.writeFileSync(`${out}/page.html`, await page.content());
      }
      await page.screenshot({ path: `${out}/page-${tag}.png`, fullPage: true });
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(e => { console.error('fail:', e.message); process.exit(1); });
NODE

echo "OK: ingested $URL -> $OUT (page.html, page-1440.png, page-390.png)"
echo "next: rebuild the neutral skeleton from this material, then run"
echo "check-skeleton.sh --neutralize-audit <skeleton-root>."
