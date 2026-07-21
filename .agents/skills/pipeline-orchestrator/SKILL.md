---
name: pipeline-orchestrator
description: >
  Entry point and controller of the design-production pipeline (v5.2). Use
  whenever the user asks to create, prototype, redesign, or restyle a website
  or web application — "make a landing page", "build a site for...", "prototype
  an app", "change the style/fonts/colors", or "I already have a
  prototype/skeleton, make it look good". Routes the request (including
  neutralization of existing code), owns artifacts/design-contract.yaml as the
  single source of truth, runs the two human gates (structure approval, blind
  visual choice), keeps the decision log, enforces execution budgets, handles
  change requests and restyles, and delivers the final report. Do NOT use for
  non-web artifacts (docs, slides, spreadsheets) or pure code tasks with no
  design surface.
---

# Pipeline Orchestrator (v5.2)

You are the controller. You never design pixels yourself — you route work to
the conveyor skills (`structure-builder`, `visual-director`, `quality-guardian`),
keep the contract consistent, and enforce the invariants [A.1]–[A.10] (see
AGENTS.md). If an invariant is violated (by you or a sub-skill), stop, roll
back to the last valid gate state, and redo the work properly.

## 0. First actions on any request

1. Run the **launch checklist** (`references/launch-checklist.md`): classify
   the request, check environment capabilities, fix the degradation path,
   set budgets. Record the classification as the FIRST entry of
   `artifacts/decision-log.md` (template: `assets/decision-log-template.md`).
2. Get the current date/time (`date` via bash) and record it.
3. Read or create `artifacts/design-contract.yaml` from
   `assets/design-contract-template.yaml` (`schema_version: "5.1"`).
   **Migration:** if a `design-contract.yaml` is found at the project ROOT
   (v5.0 layout), move it to `artifacts/`, upgrade the schema to 5.1 (map
   verdicts pass→ready, conditional_pass→ready_with_caveats, fail→not_ready;
   add new fields with defaults), and log the migration in both the changelog
   and the decision log.
   **Machine access (v5.2):** scripts never parse the contract with sed/awk —
   they call `scripts/contract-read.py` (PyYAML) with atomic queries
   (`key_screens`, `scenarios`, `functional_paths`, `mode`, `verdict`, …).
   Any new shell consumer of contract data goes through this helper.
4. Decide **interaction mode**: `interactive` (default) or `autonomous`
   (explicit delegation, or the user is unresponsive after one clarifying
   round). Record `meta.interaction_mode`. Never mix modes silently — a switch
   needs `meta.mode_override_reason` and a decision-log entry.

## 1. Request routing (S0)

Classify BEFORE doing anything else:

| Request | Route |
| :-- | :-- |
| New build (no existing code/design) | Full conveyor: K1 → G1 → K2 → G2 → K2' → K3 |
| **"I have a skeleton/prototype, need design"** | Skip K1-build: neutralize the existing code (structure-builder neutralize mode, [K1.6]) → K2 → G2 → K2' → K3 |
| Restyle ("recolor / stricter / warmer / more contrast") | §6 restyle router (tokens only) |
| Composition change ("rearrange this section") | Targeted screen rebuild inside the existing visual system → D1–D14 on that screen |
| Structural addition ("add a page/flow/role") | K1 targeted (new scope only) → G1 targeted → apply existing visual system → K3 targeted |
| Full style change ("want a different style entirely") | New K2 run on the existing skeleton: calibration → directions → G2 → scale. Structure untouched |
| Fix after QA (`not_ready` findings) | Targeted fix at the owning conveyor → retest failed checks |
| Non-design task (no UI surface) | Exit: answer directly, no pipeline |

The classification is the first decision-log entry, with a one-line rationale.

## 2. Mode selection (quick / standard / full)

Auto-select by formula: `screens ≤5 AND 1 role AND low risk → quick`;
`6–15 routes OR 2–3 roles → standard`; `high-risk / payments / PII → full`.
An explicit user word ("quickly", "full process") always beats auto-selection
and is recorded in `meta.mode_override_reason`. Question budget in K1: ≤5
functional questions in one block (quick ≤3), never about style/taste.
Full matrix and ceilings: `references/modes.md`. Execution budgets:
`references/execution-economy.md` — set them BEFORE K1 starts [E.1].

## 3. Conveyor orchestration

### 3.1 K1 — Structure (skill: structure-builder)

Hand off: mode, contract path, interaction mode. Expect back: contract sections
`product`, `experience`, `content_model` filled (incl. `localization_risk`
detection [K1.7]); neutral skeleton (gray graphite, real copy, `data-priority`
annotations, `not_approved_visual_design` marker on every screen);
`skeleton-manifest.yaml` validating clean. Hold [A.1] until Gate 1 passes.

### 3.2 Gate 1 — Structure approval

Use the message template from `references/gate-templates.md`. Interactive:
present the skeleton + 3–5 bullets (product, audience, primary scenario,
screens, deliberately deferred). ONE question: "Is the structure right? Yes /
what to change". Visual feedback is not accepted here — the skeleton is
neutral by definition. Autonomous: objective AI self-check (scenarios walkable,
skeleton matches brief) → `autonomous_passed` (no provisional — the decision
is objective), queue a confirmation offer. Record the result in the contract,
changelog, and decision log.

### 3.3 K2 — Visual, phase 1 (skill: visual-director)

Hand off: contract (product, audience, `visual_boldness`, category anchors,
`localization_risk`), skeleton path, mode, budgets. Expect back:
- calibration (`visual.calibration.status`): references decomposed to
  principles, or the style-card test, or `skipped_autonomous`;
- 2–3 constructed-divergence directions (seeds: persona + ≥3 non-overlapping
  domains + boldness point spread across the band; 7 axes each; ≥3 differing
  axes per pair incl. composition or type voice; `check-divergence.py` clean;
  in standard/full also the external blind-description test, overlap ≤50%);
- renders of the TWO-screen slice (main + contrast screen; +CJK/long variant
  if the localization trigger fired) and a blind contact sheet with randomized
  order recorded in `visual.gate2_randomization`.

### 3.4 Gate 2 — Blind visual choice

Use the gate template. Present all variants simultaneously, no authorship
hints. Result options:
- one variant → `gate2_result: chosen(X)`; then ask the default merge
  follow-up ("anything you'd take from the other variants?");
- parts of several → merge: `gate2_result: merged(base+donor.axes...)` →
  visual-director runs the **coherence gate** (render + AI contradiction check
  + D9/D11/D3) and you show the **confirming render** (quick confirmation, not
  a full gate). Record `visual.merge.confirm_render: shown|adjusted|rejected`.
- "nothing works" → ONE regeneration with a recorded failure hypothesis
  (what repels: color/density/mood) in the decision log; repeat the gate once;
  a second miss → stop and present the two nearest variants with the concrete
  trade-off, do not loop.
- autonomous: AI pre-filter per `visual-director/references/gate2-protocol.md`
  (section screenshots, pairwise with swap-augmentation, only agreed verdicts)
  → `provisional_ai(X)` + mandatory 3-minute confirmation offer on return.

### 3.5 K2 — Visual, phase 2

Merge (if any) → final direction → DTCG tokens (`compile-tokens.py`) →
**asset mini-gate**: 3–4 candidates per raster slot, human one-click pick
(interactive) or `provisional` AI pick (autonomous); favicon/OG auto-generated
from tokens; AI-image disclosure per the visual system → scale to ALL
`experience.key_screens` × `required_states`. If the system breaks at full
scale: ONE merge return with a new hypothesis in `visual.post_scale.hypothesis_log`;
a second break → `not_ready` with documentation, do not continue autonomously
[CR-07]. Remove the neutral marker only after scaling.

### 3.6 K3 — Verification (skill: quality-guardian)

Deterministic floor D1–D21 (D15 caps at `ready_with_caveats`, the rest block)
+ AI diagnostics (classes objective/heuristic/subjective × severity; subjective
≤ minor; `model_judged: true`) + functional paths D21 + a11y D20 + contract
consistency D19 (realized direction == confirmed; distinctive assets beyond
the hero; `all_local` truthful; decision-log complete). Cycles: quick 1,
standard 2, full 3. Verdicts: `ready | ready_with_caveats | not_ready`
(rules [A.8], [CR-03]). A `not_ready` routes back to the owning conveyor with
the failing values; retest keeps history (found → fixed → retested).

## 4. Change requests

Any user edit lands in the contract + decision log first, then routes per the
S0 table. Forbidden: silent drift — editing components/tokens without a
contract entry. Every change appends to `changelog` with timestamp and author.

## 5. Conflict resolution order

1. `artifacts/design-contract.yaml` beats any markdown, comment, or memory.
2. Within the contract, later `changelog` entries beat earlier field values.
3. Where the contract is silent, the earlier stage wins: brief > direction >
   tokens > components.
4. The user's latest explicit instruction beats all of the above — but record
   it (contract + decision log) before acting on it.

## 6. Restyle router

Restyle = structure stays, skin changes [A.7].

- **Token-level** (colors, radius, spacing, dark mode, font swap within the
  same voice): edit semantic tokens → `compile-tokens.py` → re-run D3/D9/D11
  (+D4–D8 if families/scale changed) → deliver. No gates.
- **Direction-level** (new mood, "make it premium/brutalist"): K2 phase-1
  re-run: calibration delta → 2 new directions → blind contact sheet → Gate 2
  → tokens → scale.
- Legacy project without tokens: say so and offer tokenization first. Never
  restyle by hand-editing components.

## 7. Delivery report (final message to the user)

Plain language, no jargon:

1. **What was built** — artifact, screens/pages, mode.
2. **Gate decisions** — what was approved at Gate 1; which variant/merge won
   at Gate 2 (or provisional status + the pending confirmation offer).
3. **What was verified** — D-checks summary (n/n), viewports, budgets;
   everything `skip`/`unavailable`/`provisional` named with reasons.
4. **What remains** — accepted limitations (with risk owners), suggested next
   steps, how to ask for changes.
