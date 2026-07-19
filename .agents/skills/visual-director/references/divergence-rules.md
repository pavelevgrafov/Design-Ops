# Constructed Divergence — rules (v5.1)

Problem: asked for "3 variants", any single model produces mode collapse —
three recolors of one layout. Divergence must be constructed, then verified.

## The 7 axes

1. **composition** — grid, density, symmetry, vertical rhythm, what's oversized
2. **type_voice** — families and roles, scale behavior, tracking, attitude
3. **color** — palette logic: temperature, saturation policy, accent behavior,
   dark/light stance (not just hues)
4. **surface** — flat vs texture vs depth, border policy, shadow policy
5. **shape** — radius scale, geometry (sharp/organic/geometric), terminals
6. **imagery** — subject matter, treatment (grain/duotone/line), framing
7. **motion** — what moves, duration character, easing character

"Differ" means a different *decision* on the axis, not a different parameter of
the same decision (indigo vs blue = same decision; "flat duotone" vs "layered
soft depth" = different decisions).

## Seeding (per direction)

1. **Persona** — a specific art-director identity with a sensibility
   ("ex-editorial director from a print magazine who hates startup SaaS
   aesthetics"). Personas measurably diversify output; use them deliberately.
2. **≥3 reference domains, non-overlapping across directions.** A domain is an
   industry/era/movement. Two directions sharing a domain = reseed. Before
   designing, write down what each domain contributes (verbalized sampling) —
   this is what breaks fixation.
3. **Boldness point, SPREAD across the band [K2.4.1]:**
   - quick (2 directions): safer + bolder;
   - standard (3): safer / middle / bolder;
   - full (3+1): add a wildcard outside the band.
   No two directions at the same point. `check-divergence.py` warns when all
   points coincide [K2.4.2].
4. **≤1 user reference per direction**, as decomposed principles only.

## The difference rule (machine-checked)

Every PAIR must differ on **≥3 axes, including composition or type_voice**
(`differs_by` + `scripts/check-divergence.py`). On failure: redesign the
weaker direction's axes — never fix by recoloring.

## Blind-description tests (two layers)

1. **Concept self-test:** the concept paragraph must let a stranger match it
   to the render. If the paragraph fits all directions ("clean, modern,
   trustworthy"), divergence failed — rewrite axes first.
2. **External blind test (CR-13, standard/full; mandatory in autonomous):**
   an outside AI agent with NO access to the specs describes each slice render
   in adjectives. Compute pairwise adjective overlap; **>50% overlap =
   insufficient divergence** → rework the weaker direction. Mark
   `model_judged: true`; record in `directions[].blind_test`.

## Bold moves (MAYA)

1–2 per direction: the most advanced move that remains acceptable to the
category. Each names the category anchor it still respects. Zero bold moves =
a recolor of convention; 3+ = concept art.

## Category anchors are never violated [K2.6.3]

Boldness lives only in the permitted layers (composition, typography, palette,
forms, surfaces, motion). Trust anchors of the category (legibility,
predictable nav, state affordances) are off-limits for differentiation.

## Anti-patterns (observed failure modes)

- "Minimal / Colorful / Dark" — one axis recolored three times.
- Same composition, three font pairs — 1 axis.
- Three personas, same domains — seed theater.
- All three at the same boldness point — hidden recolor.
- Differences listed but not visible in renders — spec/render drift; the
  contact sheet is the ground truth, re-render.
