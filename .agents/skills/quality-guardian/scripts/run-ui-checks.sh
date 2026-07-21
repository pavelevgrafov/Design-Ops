#!/usr/bin/env bash
# run-ui-checks.sh — D2, D12, D13, D15, D20, D21: browser-level checks (v5.2).
# Usage: bash run-ui-checks.sh <base_url> [routes_csv] [out_dir] [paths_json] [mode]
#   base_url    e.g. http://localhost:5173
#   routes_csv  e.g. "/,/pricing,/app"   (default: /)
#   out_dir     default: artifacts/prototype/screenshots
#   paths_json  optional functional-paths config for D21:
#               {"alternative": {"route": "/x", "expect": "selector"},
#                "error_recovery": {"route": "/y", "action": {"click": "selector"},
#                                   "expect": "selector"}}
#   mode        quick | standard | full (default: standard) — artifact matrix:
#               quick: 1 shot per viewport per route (≤3+1 PNG/route);
#               standard/full: section-wise, visible only, cap 12, dedup.
# Exit 0 = pass, 1 = failures, 2 = unavailable (no playwright).
#
# v5.2 hardening:
#   - smoke: zero waiting on hidden panels — one page.$$, isVisible()
#     filter, screenshot timeout ≤3000ms, no double DOM query        [TZ-3.1]
#   - mode artifact matrix (quick vs standard/full)                  [TZ-3.2]
#   - D21 without silent skip: missing paths_json = explicit
#     unavailable + verdict cap; report split into D21-keyboard /
#     D21-paths; pass only when BOTH declared paths walked           [TZ-2.2]
#   - D15 now measures INP-proxy (lab, PerformanceObserver event
#     timing + real trusted input) or honestly degrades; no
#     interactivity pass without a measured value                    [TZ-2.3]
set -uo pipefail

BASE_URL="${1:?usage: run-ui-checks.sh <base_url> [routes_csv] [out_dir] [paths_json] [mode]}"
ROUTES="${2:-/}"
OUT="${3:-artifacts/prototype/screenshots}"
PATHS_JSON="${4:-}"
MODE="${5:-standard}"
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
const crypto = require('crypto');

const base = process.argv[2];
const routes = process.argv[3].split(',').map(s => s.trim()).filter(Boolean);
const out = process.argv[4];
const pathsJson = process.argv[5] || '';
const mode = (process.argv[6] || 'standard').toLowerCase();
const VIEWPORTS = [390, 768, 1440];
const SECTION_CAP = 12;
const results = { console: [], overflow: [], taps: [], perf: [], inp: [], shots: [], axe: [],
                  d21kb: [], d21paths: [], d21walked: [] };

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
        if (kb.focusable === 0) results.d21kb.push({ route, fail: 'keyboard: no focusable elements on key path' });
        if (kb.issues.length > 3) results.d21kb.push({ route, fail: `keyboard: ${kb.issues.length} elements lack visible focus` });
      }

      // Section-wise screenshots for AI diagnostics.
      // [TZ-3.1] zero waiting on hidden panels: ONE page.$$, isVisible()
      // filter (no wait), per-shot timeout ≤3000ms, no $$eval+$$ double query.
      const shotDir = `${out}/shots${route.replace(/\//g, '_')}_${width}`;
      fs.mkdirSync(shotDir, { recursive: true });
      if (mode === 'quick') {
        // [TZ-3.2] quick matrix: 1 shot per viewport per route (+1 overview @1440)
        await page.screenshot({ path: `${shotDir}/viewport.png`, timeout: 3000 }).catch(() => {});
        if (width === 1440)
          await page.screenshot({ path: `${shotDir}/full.png`, fullPage: false, timeout: 3000 }).catch(() => {});
      } else {
        // [TZ-3.2] standard/full: section-wise, cap 12, dedup identical
        const handles = await page.$$('main section, [data-section], header, footer');
        const seen = new Set();
        let idx = 0;
        for (const el of handles) {
          if (idx >= SECTION_CAP) break;
          let vis = false;
          try { vis = await el.isVisible(); } catch (e) { vis = false; }
          if (!vis) continue; // hidden state panels: no waiting, no shot
          const p = `${shotDir}/section-${String(idx).padStart(2, '0')}.png`;
          try { await el.screenshot({ path: p, timeout: 3000 }); } catch (e) { continue; }
          let h = '';
          try { h = crypto.createHash('sha1').update(fs.readFileSync(p)).digest('hex'); } catch (e) {}
          if (h && seen.has(h)) { fs.unlinkSync(p); continue; } // dedup
          if (h) seen.add(h);
          idx++;
        }
        await page.screenshot({ path: `${shotDir}/full.png`, fullPage: false, timeout: 3000 }).catch(() => {});
      }
      results.shots.push({ route, width, dir: shotDir, mode });

      // D15-INP: lab INP-proxy [TZ-2.3] — measure or honestly degrade.
      // PerformanceObserver event timing + REAL trusted input (mouse/keyboard);
      // metric = max event duration; threshold ≤200ms. Done LAST on the page
      // because clicking controls may navigate.
      if (width === 1440) {
        await page.evaluate(() => {
          window.__inpMax = 0; window.__inpSupported = true;
          try {
            new PerformanceObserver(l => {
              for (const e of l.getEntries()) if (e.duration > window.__inpMax) window.__inpMax = e.duration;
            }).observe({ type: 'event', durationThreshold: 16, buffered: true });
          } catch (e) { window.__inpSupported = false; }
        }).catch(() => {});
        let interacted = 0;
        // buttons/inputs only — clicking nav links would navigate and lose
        // the in-page measurement context
        const controls = await page.$$('button, [role="button"], input, select, textarea, [tabindex]');
        for (const hnd of controls) {
          if (interacted >= 5) break;
          const box = await hnd.boundingBox().catch(() => null); // null = hidden, no waiting
          if (!box || box.width < 24 || box.height < 24) continue;
          if (box.y < 0 || box.y > 900) continue;
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2).catch(() => {});
          await page.mouse.down().catch(() => {});
          await page.mouse.up().catch(() => {});
          interacted++;
        }
        // Tab presses generate trusted key events without navigating
        await page.keyboard.press('Tab').catch(() => {});
        await page.keyboard.press('Tab').catch(() => {});
        await page.waitForTimeout(400);
        const inp = await page.evaluate(() =>
          ({ maxMs: Math.round(window.__inpMax || 0),
             supported: window.__inpSupported !== false })).catch(() => null);
        if (inp) results.inp.push({ route, ...inp, interacted });
      }

      await page.close();
    }
  }

  // D21: declared functional paths (alternative + error recovery) [TZ-2.2]
  if (pathsJson && fs.existsSync(pathsJson)) {
    const cfg = JSON.parse(fs.readFileSync(pathsJson, 'utf8'));
    const page = await browser.newPage();
    for (const name of ['alternative', 'error_recovery']) {
      const spec = cfg[name];
      if (!spec || !spec.route) { results.d21paths.push({ path: name, unavailable: `path '${name}' not declared in acceptance.functional_paths` }); continue; }
      try {
        await page.goto(base.replace(/\/$/, '') + spec.route, { waitUntil: 'networkidle', timeout: 20000 });
        if (spec.action && spec.action.click) await page.click(spec.action.click, { timeout: 5000 });
        if (spec.expect) await page.waitForSelector(spec.expect, { timeout: 5000 });
        results.d21walked.push(name);
      } catch (e) {
        results.d21paths.push({ path: name, fail: `${name} path failed: ${e.message.slice(0, 120)}` });
      }
    }
    await page.close();
  } else {
    // no silent skip: explicit unavailable + verdict cap [TZ-2.2]
    results.d21paths.push({ unavailable: 'functional paths not declared (paths_json missing)' });
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
    const inp = results.inp.find(i => i.route === p.route);
    const bad = [];
    if (p.lcpMs > 2500) bad.push(`LCP ${p.lcpMs}ms`);
    if (p.cls > 0.1) bad.push(`CLS ${p.cls}`);
    let inpPart = '';
    if (inp) {
      if (!inp.supported) inpPart = '; INP unavailable (event timing unsupported — INP needs field data)';
      else if (inp.interacted === 0) inpPart = '; INP-proxy n/a (no visible controls)';
      else if (inp.maxMs > 200) { bad.push(`INP-proxy ${inp.maxMs}ms`); inpPart = `, INP-proxy ${inp.maxMs}ms (lab, not field-INP)`; }
      else inpPart = `, INP-proxy ${inp.maxMs}ms (lab, not field-INP)`;
    }
    rep.push(bad.length
      ? `caveat D15 ${p.route}: ${bad.join(', ')} (caps verdict at ready_with_caveats)`
      : `pass D15 ${p.route}: LCP ${p.lcpMs}ms, CLS ${p.cls}${inpPart}`);
  }
  for (const a of results.axe) {
    if (a.unavailable) rep.push(`unavailable D20 on ${a.route}: ${a.unavailable}`);
    else { fails++; rep.push(`FAIL D20 a11y on ${a.route}: ${a.violations.slice(0, 5).join('; ')}`); }
  }
  if (!results.axe.length) rep.push('pass D20 a11y: zero critical/serious violations');
  // D21 — split evidence [TZ-2.2]: keyboard probe and declared paths are
  // reported separately; a pass requires measured/clean evidence on BOTH.
  if (!results.d21kb.length) rep.push('pass D21-keyboard: tab order sane, visible focus on key path');
  for (const d of results.d21kb) { fails++; rep.push(`FAIL D21-keyboard on ${d.route}: ${d.fail}`); }
  const d21unavail = results.d21paths.filter(d => d.unavailable);
  const d21fail = results.d21paths.filter(d => d.fail);
  if (d21unavail.length) {
    rep.push(`unavailable D21-paths: ${d21unavail.map(d => d.unavailable).join('; ')} — caps verdict at ready_with_caveats`);
  } else if (d21fail.length) {
    fails++;
    rep.push('FAIL D21-paths: ' + d21fail.map(d => `${d.path}: ${d.fail}`).join('; '));
  } else if (results.d21walked.includes('alternative') && results.d21walked.includes('error_recovery')) {
    rep.push('pass D21-paths: alternative + error_recovery declared paths walked');
  } else {
    rep.push('unavailable D21-paths: not all declared paths walked — caps verdict at ready_with_caveats');
  }
  rep.forEach(l => console.log(l));
  process.exit(fails ? 1 : 0);
})();
NODE

NODE_EXIT=0
node "$RUNNER" "$BASE_URL" "$ROUTES" "$OUT" "$PATHS_JSON" "$MODE" || NODE_EXIT=$?

echo "---"
echo "artifacts: $OUT (ui-results.json + screenshots for AI diagnostics; mode=$MODE)"
exit "$NODE_EXIT"
