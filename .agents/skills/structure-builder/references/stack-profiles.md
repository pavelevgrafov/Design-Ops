# Stack Profiles (K1, v5.1)

Substrate choice is structural, not visual. Styling arrives later via tokens.

## Profile A — Web app / interactive product (standard, full)

- React + TypeScript + Tailwind CSS + shadcn/ui (via the webapp-building
  toolchain). Neutralized shadcn theme: gray ramp, `--primary` = neutral
  blue-gray (affordance only), system font stack, default radius/shadows.
- States via local state or MSW mocks — every `required_state` reachable
  without a backend.

## Profile B — Static site / landing (standard, quick)

- Single-file neutral HTML (embedded `<style>`, system font stack). No build
  step required to review the skeleton.
- Semantic landmarks; one `<section>` per contract block with `data-priority`;
  gray boxes for asset slots (`data-asset-slot="hero-visual"`).
- Required states as toggleable variants (`?state=empty`).

## Profile C — App prototype inside an existing repo

- Match the repo's existing stack and component library; neutralize its theme
  to the gray-graphite contract. Do not introduce shadcn into a repo that
  already has a component library — use theirs, neutralized.

## Profile D — Neutralization of an existing prototype (CR-01)

Entry: the user brings working code that must become a skeleton for K2.

1. **Inventory first:** list what exists — screens, working flows, states,
   real copy, styling layers, fonts, imagery. Log it.
2. **Strip the visual layer:** custom fonts → system stack; brand colors →
   gray ramp (keep ONE neutral accent for affordance); shadows/gradients/
   decorative radius → substrate defaults; imagery → gray boxes with
   `data-asset-slot` labels; icon decorations removed unless they carry meaning.
3. **Preserve:** working scenarios, navigation, logic, real copy. Neutralize
   skin, never amputate behavior.
4. **Repair structural gaps:** missing required states or screens → targeted
   additions (a K1 delta), never a full rebuild.
5. **Annotate:** `data-priority` per block; `not_approved_visual_design`
   marker on every screen.
6. **Audit:** `check-skeleton.sh --neutralize-audit <root>` must end clean;
   its violation list is the neutralization work log.

## Decision table

| Request | Mode | Profile |
| :-- | :-- | :-- |
| "prototype an app", dashboard, SaaS | standard/full | A |
| landing, promo site | any | B |
| work inside an existing repo | any | C |
| "I have a prototype, make it look good" | any | D → then K2 |

## Non-negotiables (all profiles)

1. Real copy from step one; Lorem = automatic fail.
2. No custom fonts, brand colors, gradients, shadows-beyond-default, imagery.
3. `not_approved_visual_design` marker visible on every screen.
4. Every key screen reachable; every required state demonstrable; console clean.
