# Gate 2 protocol — blind visual choice (v5.1)

The gate where the human does what humans do best (recognize) and is protected
from what humans do badly (rationalize, anchor, defer to authorship).

## Setup (visual-director, before showing anything)

1. Render the TWO-screen slice per direction: main + contrast screen (CR-04);
   +CJK/long variant when the localization trigger fired.
2. Randomize order. Record the mapping:
   `visual.gate2_randomization: {"Variant 1": "C", "Variant 2": "A", ...}`.
3. Build the contact sheet from `assets/contact-sheet-template.html`: all
   variants simultaneously, equal size, both screens accessible per variant,
   labels "Variant N" only.
4. Strip authorship: no direction names, no concepts, no "this one is the
   safe choice" commentary. Even tone = anchoring.

## Presentation (orchestrator)

Use the gate template (`pipeline-orchestrator/references/gate-templates.md`).
Question format:
- quick (2 variants): "Which is better — 1 or 2?"
- standard/full (3): "Which is best of the three?" (pairwise on request, or
  one triple comparison).
Always offer merge and "none of these" paths. Never ask "why" before the
choice [A.4]. Never present variants sequentially with discussion.

## Recording the result

| User says | Contract `gate2_result` | Next |
| :-- | :-- | :-- |
| "Variant 2" | `chosen(A)` (map via randomization) | merge follow-up (default) → Phase 2 |
| "typography from 2, color from 3" | `merged(A.type+B.color)` | coherence gate → confirming render → Phase 2 |
| "none of these, too bland" | `regenerated` + failure hypothesis | ONE new round, then gate again |
| "your call" / silence (autonomous) | `provisional_ai(X)` | AI pre-filter (below), offer confirm on return |

## Merge-by-default

After a plain `chosen(X)`, still ask ONE follow-up: "Anything you'd like to
take from the other variants?" Users reliably compose better results than any
single variant. Merge mechanics + coherence gate: `references/merge-rules.md`.

## Regeneration limits

Maximum ONE full regeneration round, always with a recorded failure hypothesis
(what repels: color/density/mood — the only allowed clarifying question at
this gate). If round two also misses: stop guessing, show the two nearest
variants, name the concrete trade-off, let the user pick a base + constraints.

## Autonomous pre-filter (provisional only)

Allowed only when the user delegated. Method:
- section-wise screenshots (not full-page) + structured description;
- pairwise comparisons with **swap-augmentation** (A-vs-B AND B-vs-A); only
  agreed verdicts count — a flipping verdict = position bias, discard it;
- compare on VISIBLE, objective factors: hierarchy (is p1 dominant?), trust
  (alignment, consistency, restraint), clarity (sizes, spacing, states);
- record `provisional_ai(X)` + deciding factors + `model_judged: true` + the
  flag "not confirmed by a human" in the report;
- on the user's first return: the 3-minute confirmation offer (gate template 4).
  If the user overrides, re-enter Phase 1 with their feedback as constraints.

## What invalidates the gate (redo)

- Variants shown with names/concepts → anchoring, redo blind.
- Sequential presentation → redo simultaneously.
- A "recommended" marker on any variant → redo.
- Order not recorded → redo randomization and record.
- Only one screen per variant shown → the slice is incomplete, re-render.
