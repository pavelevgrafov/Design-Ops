# Token pipeline — DTCG, compile, skin property (v5.2)

Design tokens are the ONLY sanctioned channel between a direction and
components. They make restyle a data edit, not a code surgery [A.7].

## Layers

1. **Primitive** (`tokens.json` → `primitive.*`): raw decisions — color ramps,
   font families, modular scale, space scale, radius. Named by value, not
   meaning (`gray.500`, `accent.600`, `font.scale.step3`).
2. **Semantic** (`semantic.*`): roles — `ink`, `canvas`, `actionPrimary`,
   `focusRing`, `borderSubtle`, `measure.body`... Components consume ONLY
   semantic names. Semantic values reference primitives (`{primitive...}`).
3. **Compiled outputs** (generated, never hand-edited):
   - `tokens.css` — CSS custom properties, `:root` (light) and
     `[data-theme="dark"]` when a dark theme is planned;
   - Tailwind `@theme` block mapping semantic tokens into utilities.

## Compiler

`scripts/compile-tokens.py <tokens.json> [--out-css tokens.css] [--out-tailwind theme.css]`
- resolves `{references}` one level deep (semantic → primitive);
- emits `--ink`, `--canvas`, `--action-primary`, ... (kebab-case; the color
  group maps to bare names, other groups keep their prefix);
- emits primitives too (`--color-gray-500`, `--font-scale-step3`, `--space-4`);
- emits a `contrast-pairs` comment header consumed by `check-contrast.py`;
- dark theme: if `semantic.dark.*` exists, emit under `[data-theme="dark"]`;
- exits non-zero on unresolved references, non-DTCG shapes, missing contrast
  pairs, or ban-listed fonts in first position.

## The skin property (acceptance test)

**Restyle any page = edit tokens + recompile. Zero manual component edits.**
When you find yourself writing a raw hex/px/font in a component:
- stop; decide which semantic role it actually is;
- add/extend the semantic token; recompile; use the token.
`check-token-usage.sh` (D9) enforces it.

## Dark mode

- A dark theme is a semantic override set (`semantic.dark.*`), not a second
  design. Either a full semantic dark layer or none — never a filter invert.
- Dark contrast pairs are checked by the same `check-contrast.py --dark`.

## Typography tokens

- Families: exactly the direction's type_voice (display/text[/mono]) — ≤2
  proportional families + optional mono (D8); every stack ends in a generic
  fallback (D8); `font-display: swap` on every @font-face (D8).
- Scale: modular ratio 1.2–1.333 (D7); body = step0 ≥ 16px (D4); line-height
  1.4–1.7 body (D6); measure 45–75ch via `measure.body` (D5).

## Contrast pairs (contract with K3)

The semantic layer defines the checked pairs: `ink/canvas`,
`inkMuted/canvas`, `actionPrimaryText/actionPrimary`, `inkOnDark/surfaceDark`,
plus `semantic.dark.*` equivalents. `check-contrast.py` computes WCAG relative
luminance: 4.5:1 text / 3:1 large text (≥24px or ≥18.66px bold) and UI chrome.

## Versioning

Tokens live in the repo; any token edit after Gate 2 = `changelog` entry
(field `tokens`, reason) + decision-log line. A restyle is a tokens diff +
recompile + K3 re-check (D3/D9/D11, +D4–D8 if type changed) — nothing else.

## v7.0 — extended categories + component layer

New primitive categories (both base skins): `color.semantic.*` (error/
success/warning/info with `dark` variants), `font.size` (named xs…3xl
aliases over the modular scale), `font.weight`, `font.tracking`,
`font.fluid` (clamp), `lineHeight.caption`, `radius.full`, `shadow`
(two-layer, 3 elevations), `motion` (duration/easing/spring),
`elevation` (dark state overlays). New semantic groups: `textPrimary/
Secondary/Tertiary` (three text tiers), `semanticError/Success/Warning/
Info`, `shadow.*`, `radius.*`, `motion.*`, plus a full `semantic.dark`
layer (sources: knowledge/dark-theme-rules, knowledge/text-hierarchy-tiers,
knowledge/motion-budgets, knowledge/modular-type-scale, knowledge/spacing-8pt-grid).

Since v7.2 (Т-1) the dark layer is **declared, not authored**: the overlay
model lives in `$meta.darkModel` (base surface, emphasis ladder, elevation
ladder, accent transform), `dops skin darkramp` generates
`primitive.color.darkInk / darkSurface / accentDark` from it, and
`semantic.dark.color.*` references those tones. A tone edited by hand fails
D.40 — the model and the values can no longer drift apart, which is what the
prose version of this paragraph ("text 87/60/38% over #121212") could not
prevent. Change taste in the model, never in a tone.

4. **Component** (`component.*`, v7.0): per-element bindings
   (`button.primaryBg`, `card.radius`, `input.focusRing`). Component
   tokens reference semantic ONLY [A.21]; the compiler fails the build on
   `component → primitive` or `semantic → component` references and emits
   component vars (`--button-primary-bg`, `--card-radius`).

Layer discipline is machine-enforced at compile time (A.21); see also the
`token-validator` pack (D.37) for project-side verification.
