# AI diagnostics — honest model judgment (v5.1, CR-14)

Models judge objective visible factors decently and taste at near coin-flip.
This file defines what AI judgment MAY claim, how it must be produced, and
how findings are classified.

## What AI may judge (advisory)

1. **Hierarchy** — does the first viewport make the p1 content (per contract
   annotations) obviously dominant? Is the eye path plausible?
2. **Trust** — alignment consistency, spacing rhythm, restraint (count of
   competing accents), absence of broken/placeholder-looking areas.
3. **Clarity** — readable sizes at each viewport, distinguishable states,
   obvious form affordances.
4. **Coherence** — imagery sets in one visual family; components speaking one
   shape/surface language; distinctive assets present beyond the hero.

## What AI may NOT judge

- Beauty, taste, "premium feel", brand fit — those belonged to Gate 2.
- Comparative ranking of directions after the gate (gate is done).
- Any verdict phrased as fact without `provisional` + `model_judged: true`.

## Finding classes × severity (CR-14) [AI.7]–[AI.9]

Every finding is classified TWO ways:

| Class | Meaning | May be blocker? |
| :-- | :-- | :-- |
| `objective` | verifiable by measurement (overlap, clipping, misaligned values) | only with deterministic corroboration |
| `heuristic` | experience rule (weak hierarchy, "gray soup", rhythm break) | no — max major |
| `subjective` | taste ("looks off", "not premium") | no — **max minor, always provisional** [AI.8] |

Severity: `blocker / major / minor / polish`.

**Score ceiling [AI.9]:** any visible defect on a dimension caps that
dimension's score at **≤3/5** — no inflated totals over visible problems.

## Method (mandatory)

1. **Section-wise capture**: screenshots by sections at each target viewport —
   never one long full-page image (section-wise judging is substantially more
   reliable: published F1 0.78 vs 0.46).
2. **Structured probe per section**: the judge answers a fixed checklist
   (hierarchy: dominant element named; trust: misaligned elements listed;
   clarity: sub-16px text found? overlapping elements? states
   distinguishable?) — not free-form impressions.
3. **Swap-augmentation for any comparison**: A-vs-B AND B-vs-A. Agreement =
   usable signal; disagreement = position bias → `unavailable`, say so.
4. **Corroboration rule**: an AI finding becomes blocking only if a
   deterministic check confirms it. Otherwise: advisory + `provisional`.

## Blind-description test protocol (CR-13, used by visual-director)

The same discipline powers the external divergence test: an AI agent WITHOUT
access to direction specs receives slice renders and returns 5–8 adjectives
per render. Pairwise adjective overlap >50% = insufficient divergence. Always
`model_judged: true`; the judge never sees direction names or concepts.

## Screenshot hygiene

- Disable animations/caret blink; consistent device scale factor.
- Capture empty/loading/error states too — slop hides in states.
- Filenames encode screen+section+viewport+state (report traceability).

## Typical AI-detectable issues (worth the tokens)

- Orphaned spacing: a section visibly tighter/looser than siblings.
- Contrast failures over imagery (D3 covers flat pairs; imagery needs eyes).
- "Gray soup": everything same visual weight despite p1/p2/p3 annotations.
- State screens that look broken rather than intentional (empty states).
- Imagery incoherence: one slot visibly off-style vs its consistency group.

## Reporting format

Each finding: `{screen §section @viewport, factor, class, severity,
observation (what is seen), evidence (screenshot path), status: provisional,
model_judged: true, suggested deterministic check}`. No finding without a
screenshot path.
