# Merge rules — combining directions after Gate 2 (v5.1, CR-06/CR-07)

Merge = chosen base direction + adopted elements from losers, resolved into
one coherent `visual.final_direction`. Merge is the DEFAULT outcome — but an
uncontrolled merge is a Frankenstein, so every merge passes a coherence gate
and a confirming render before scaling.

## Resolution order

1. **Base = the variant the user picked first** (or praised most). Its axes
   are the default value of every axis.
2. **Adopted elements override axis-by-axis**, never pixel-by-pixel:
   - "typography from 2" → adopt the donor's type_voice axis wholesale.
   - "color from 3" → adopt the donor's color axis; re-derive semantic tokens;
     re-run contrast checks on the merged result.
   - "that card" → decompose into axes (surface? shape? composition?) → adopt
     those decisions for that component family only; record as a scoped override.
3. **Conflicts resolve toward the base** unless the user explicitly preferred
   the donor's conflicting trait. Record every conflict + resolution.
4. Write the resolved axes into `visual.merge.axes_resolution` AND
   `visual.final_direction` — ALL 7 axes, concrete.

## Coherence gate [K2.16] — mandatory before scaling

1. Render the merged direction on the slice (both screens).
2. AI contradiction check (`model_judged`): incompatible type scales,
   clashing surface models, motion that the base's shapes can't carry.
3. Deterministic checks on the merged result: D9 (token usage), D11
   (ban-list — a merge can introduce banned combinations even when both
   sources were clean), D3 (contrast).
4. Any failure → reject with a per-axis diagnosis and return to axis
   selection. Do not "patch around" a failed merge.

## Confirming render [K2.17]

The orchestrator shows the merged slice for a quick confirmation (NOT a full
gate): "confirm or adjust". Record `visual.merge.confirm_render:
shown | adjusted | rejected`. In autonomous mode: `deferred` — included in
the 3-minute return confirmation.

## Compatibility constraints (hard)

- Motion axis adopts cleanly only if the base's surface/shape axes can carry it.
- Adopting a donor's imagery axis re-checks the asset plan: consistency groups
  must re-anchor.
- Composition axis adoption is all-or-nothing per screen type — never merge
  two grids on one screen.
- If adopted elements contradict ≥4 of the base's 7 axes, the "base" is wrong:
  the real choice was a different direction. Say so, swap base, remerge.

## Post-scale failure budget (CR-07) [K2.28]

If the visual system breaks at full scale (unforeseen densities, state
conflicts, broken rhythms):
1. Record a failure hypothesis in `visual.post_scale.hypothesis_log`.
2. ONE return to merge/axis adjustment with the new hypothesis. This budget
   is SEPARATE from the Gate 2 regeneration budget.
3. A second break → `not_ready` with documentation: what breaks, what was
   tried, the options for a human decision. Never loop autonomously.

## Chosen(X) still merges lightly

Even a clean pick gets the default merge follow-up question. If the user names
nothing, proceed — record `chosen(X)` and move on. Do not force adoption.

## Provisional merges (autonomous)

AI may NOT invent merges. `provisional_ai` selects ONE direction whole; merges
require human reaction. If the confirmation gate later produces merge
feedback, apply these same rules then.
