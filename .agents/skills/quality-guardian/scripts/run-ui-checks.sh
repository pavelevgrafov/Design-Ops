#!/usr/bin/env bash
# run-ui-checks.sh — D2, D12, D13, D15, D20, D21: browser-level checks (v5.1).
# Usage: bash run-ui-checks.sh <base_url> [routes_csv] [out_dir] [paths_json]
#   base_url    e.g. http://localhost:5173
#   routes_csv  e.g. "/,/pricing,/app"   (default: /)
#   out_dir     default: artifacts/prototype/screenshots
#   paths_json  optional functional-paths config for D21:
#               {"alternative": {"route": "/x", "expect": "selector"},
#                "error_recovery": {"route": "/y", "action": {"click": "selector"},
#                                   "expect": "selector"}}
# Exit 0 = pass, 1 = failures, 2 = unavailable (no playwright).
set -uo pipefail

BASE_URL="${1:?usage: run-ui-checks.sh <base_url> [routes_csv] [out_dir] [paths_json]}"
ROUTES="${2:-/}"
OUT="${3:-artifacts/prototype/screenshots}"
PATHS_JSON="${4:-}"
mkdir -p "$OUT"

# --- availability gate: honest degradation [A.6] -------------------------------
if ! node -e "require.resolve('playwright')" 2>/dev/null && ! npx --no-install playwright --version >/dev/null 2>&1; then
  echo "unavailable: playwright not installed (npm i -D playwright && npx playwright install chromium)"
  # HTTP-only fallback (degradation matrix): curl status per route
  if command -v curl >/dev/null 2>&1; then
    IFS=',' read -ra R <<< "$ROUTES"
    for r in "${R[@]}"; do
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${BASE_URL%/}${r}" || echo 000)
      if [ "$code" -lt 400 ] 2>/dev/null; then
        echo "pass[HTTP-fallback]: $r → $code"
      else
        echo "FAIL[HTTP-fallback]: $r → $code"
      fi
    done
  fi
  echo "unavailable: D2/D12/D13/D15/D20/D21 require playwright — verdict caps at ready_with_caveats"
  exit 2
fi

RUNNER="$OUT/_runner.cjs"
cat > "$RUNNER" <<'NODE'
const { chromium } = require('playwright');
const fs = require('fs');

const base = process.argv[2];
const routes = process.argv[3].split(',').map(s => s.trim()).filter(Boolean);
const out = process.argv[4];
const pathsJson = process.argv[5] || '';
const VIEWPORTS = [390, 768, 1440];
const results = { console: [], overflow: [], taps: [], perf: [], shots: [], axe: [], d21: [] };

(async () => {
  let axeSource = null;
  try { axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8'); } catch (e) {}

  const browser = await chromium.launch();
  for (const route of routes) {
    const url = base.replace(/\/$/, '') + route;
    for (const width of VIEWPORTS) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('pageerror', e => errors.push('pageerror: ' + e.message));
      page.on('requestfailed', r => errors.push('reqfail: ' + r.url()));
      const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => null);
      if (!resp) { results.console.push({ route, width, errors: ['navigation failed/timeout'] }); await page.close(); continue; }
      if (resp.status() >= 400) errors.push('HTTP ' + resp.status());
      if (errors.length) results.console.push({ route, width, errors });

      // D12: horizontal overflow
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (overflow > 1) results.overflow.push({ route, width, overflowPx: overflow });

      // D13: tap targets at mobile width
      if (width === 390) {
        const small = await page.evaluate(() => {
          const bad = [];
          document.querySelectorAll('a,button,[role="button"],input,select,textarea,[tabindex]').forEach(el => {
            const r = el.getBoundingClientRect();
            const inText = el.closest('p');
            if (r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24) && !inText)
              bad.push(`${el.tagName}#${el.id || ''} ${Math.round(r.width)}x${Math.round(r.height)} "${(el.textContent||'').trim().slice(0,30)}"`);
          });
          return bad.slice(0, 20);
        });
        if (small.length) results.taps.push({ route, targets: small });
      }

      // D15: LCP + CLS (lab)
      if (width === 1440) {
        const perf = await page.evaluate(() => new Promise(res => {
          let lcp = 0, cls = 0;
          try {
            new PerformanceObserver(l => { const e = l.getEntries(); if (e.length) lcp = e[e.length-1].startTime; })
              .observe({ type: 'largest-contentful-paint', buffered: true });
            new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) cls += e.value; })
              .observe({ type: 'layout-shift', buffered: true });
          } catch (e) { res({ unavailable: true }); }
          setTimeout(() => res({ lcpMs: Math.round(lcp), cls: Math.round(cls * 1000) / 1000 }), 2500);
        }));
        results.perf.push({ route, ...perf });
      }

      // D20: axe-core (critical/serious only), once per route at 1440
      if (width === 1440) {
        if (axeSource) {
          try {
            await page.addScriptTag({ content: axeSource });
            const axeRes = await page.evaluate(async () => {
              const r = await window.axe.run(document, { resultTypes: ['violations'] });
              return r.violations
                .filter(v => ['critical', 'serious'].includes(v.impact))
                .map(v => `${v.id} (${v.impact}): ${v.nodes.length} node(s)`);
            });
            if (axeRes.length) results.axe.push({ route, violations: axeRes });
          } catch (e) {
            results.axe.push({ route, unavailable: 'axe run failed: ' + e.message });
          }
        } else {
          results.axe.push({ route, unavailable: 'axe-core not installed (npm i -D axe-core)' });
        }
      }

      // D21 keyboard probe (once per route, 1440): real Tab presses + visible focus.
      // NOTE: synthetic dispatchEvent does NOT move focus (untrusted events skip
      // default actions) — must use page.keyboard.press('Tab').
      if (width === 1440) {
        const kb = { focusable: 0, issues: [] };
        await page.locator('body').click({ position: { x: 1, y: 1 } }).catch(() => {});
        for (let i = 0; i < 15; i++) {
          await page.keyboard.press('Tab');
          const info = await page.evaluate(() => {
            const el = document.activeElement;
            if (!el || el === document.body) return null;
            const cs = getComputedStyle(el);
            const visible = cs.outlineWidth !== '0px' || cs.boxShadow !== 'none'
              || el.matches(':focus-visible');
            return { tag: el.tagName + (el.id ? '#' + el.id : ''), visible };
          });
          if (!info) break;
          kb.focusable++;
          if (!info.visible) kb.issues.push('no visible focus on ' + info.tag);
        }
        if (kb.focusable === 0) results.d21.push({ route, fail: 'keyboard: no focusable elements on key path' });
        if (kb.issues.length > 3) results.d21.push({ route, fail: `keyboard: ${kb.issues.length} elements lack visible focus` });
      }

      // section-wise screenshots for AI diagnostics
      const shotDir = `${out}/shots${route.replace(/\//g, '_')}_${width}`;
      fs.mkdirSync(shotDir, { recursive: true });
      const sections = await page.$$eval('main section, [data-section], header, footer',
        els => els.slice(0, 12).map((_, i) => i)).catch(() => []);
      for (const i of sections) {
        const el = (await page.$$('main section, [data-section], header, footer'))[i];
        if (el) await el.screenshot({ path: `${shotDir}/section-${String(i).padStart(2, '0')}.png` }).catch(() => {});
      }
      await page.screenshot({ path: `${shotDir}/full.png`, fullPage: false });
      results.shots.push({ route, width, dir: shotDir });
      await page.close();
    }
  }

  // D21: declared functional paths (alternative + error recovery)
  if (pathsJson && fs.existsSync(pathsJson)) {
    const cfg = JSON.parse(fs.readFileSync(pathsJson, 'utf8'));
    const page = await browser.newPage();
    for (const name of ['alternative', 'error_recovery']) {
      const spec = cfg[name];
      if (!spec || !spec.route) { results.d21.push({ path: name, unavailable: 'not declared in acceptance.functional_paths' }); continue; }
      try {
        await page.goto(base.replace(/\/$/, '') + spec.route, { waitUntil: 'networkidle', timeout: 20000 });
        if (spec.action && spec.action.click) await page.click(spec.action.click, { timeout: 5000 });
        if (spec.expect) await page.waitForSelector(spec.expect, { timeout: 5000 });
      } catch (e) {
        results.d21.push({ path: name, fail: `${name} path failed: ${e.message.slice(0, 120)}` });
      }
    }
    await page.close();
  }

  await browser.close();
  fs.writeFileSync(`${out}/ui-results.json`, JSON.stringify(results, null, 2));

  let fails = 0;
  const rep = [];
  if (results.console.length) { fails++; rep.push('FAIL D2 console: ' + JSON.stringify(results.console.slice(0, 3))); }
  else rep.push('pass D2 console: no errors on ' + routes.length + ' route(s) × ' + VIEWPORTS.length + ' viewports');
  if (results.overflow.length) { fails++; rep.push('FAIL D12 overflow: ' + JSON.stringify(results.overflow)); }
  else rep.push('pass D12 viewports: no horizontal overflow at 390/768/1440');
  if (results.taps.length) { fails++; rep.push('FAIL D13 tap targets: ' + JSON.stringify(results.taps)); }
  else rep.push('pass D13 tap targets ≥24px @390');
  for (const p of results.perf) {
    if (p.unavailable) { rep.push(`unavailable D15 on ${p.route}: PerformanceObserver missing`); continue; }
    const bad = [];
    if (p.lcpMs > 2500) bad.push(`LCP ${p.lcpMs}ms`);
    if (p.cls > 0.1) bad.push(`CLS ${p.cls}`);
    rep.push(bad.length
      ? `caveat D15 ${p.route}: ${bad.join(', ')} (caps verdict at ready_with_caveats)`
      : `pass D15 ${p.route}: LCP ${p.lcpMs}ms, CLS ${p.cls}`);
  }
  for (const a of results.axe) {
    if (a.unavailable) rep.push(`unavailable D20 on ${a.route}: ${a.unavailable}`);
    else { fails++; rep.push(`FAIL D20 a11y on ${a.route}: ${a.violations.slice(0, 5).join('; ')}`); }
  }
  if (!results.axe.length) rep.push('pass D20 a11y: zero critical/serious violations');
  for (const d of results.d21) {
    if (d.unavailable) rep.push(`unavailable D21: ${d.unavailable}`);
    else { fails++; rep.push(`FAIL D21: ${d.fail}`); }
  }
  if (!results.d21.length) rep.push('pass D21 functional paths: keyboard path sane, declared paths walkable');
  rep.forEach(l => console.log(l));
  process.exit(fails ? 1 : 0);
})();
NODE

NODE_EXIT=0
node "$RUNNER" "$BASE_URL" "$ROUTES" "$OUT" "$PATHS_JSON" || NODE_EXIT=$?

echo "---"
echo "artifacts: $OUT (ui-results.json + section screenshots for AI diagnostics)"
exit "$NODE_EXIT"
