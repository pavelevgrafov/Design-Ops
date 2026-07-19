# AGENTS.md — Design Production (v5.1)

## What this repository does

Production pipeline turning a text request into a finished, verified website
or web application. Architecture: **three conveyors, two gates.**

```
K1 "Structure" → GATE 1 (human) → K2 "Visual" → GATE 2 (human) → K2 continued → K3 "Verification"
```

## Hard invariants (never violate)

- **[A.1]** No visual work (directions, tokens, styling beyond neutral) until
  `gates.gate1 ∈ {passed, autonomous_passed}`.
- **[A.2]** No scaling beyond the slice until `gates.gate2 ∈ {passed,
  provisional_ai}` (+ confirmed merge, if any).
- **[A.3]** Skeleton and visuals never mix in one stage; no taste questions in
  K1; taste calibration happens only in K2, only by showing.
- **[A.4]** Never ask "why" before the Gate 2 choice is recorded.
- **[A.5]** AI never issues a `ready` verdict on aesthetics — at most
  `provisional` or a diagnostic finding. Every model check: `model_judged: true`.
- **[A.6]** Degradation never upgrades a verdict; a missing capability is an
  explicit status, not a silent skip.
- **[A.7]** A restyle never changes markup (skin property); if markup must
  change, it is not a restyle.
- **[A.8]** `not_ready` is never lowered without a fix + retest; an accepted
  limitation needs a rationale and a recorded risk owner.
- **[A.9]** Budgets never downgrade blocking checks (D1–D14, D16–D21) and
  never cancel Gate 2 in interactive mode.
- **[A.10]** Single source of truth: `artifacts/design-contract.yaml`.
  Decisions are recorded (contract changelog / decision log) before they are
  executed. Silent drift = defect.

## Entry point

Trigger words: "make a website", "landing page", "prototype an app", "redesign",
"restyle", "change fonts/colors". Entry skill: `pipeline-orchestrator`
(`.agents/skills/pipeline-orchestrator/`). Scope guard: websites and web apps
only — for docs/slides/spreadsheets, stop and say so.

## Skills

| Skill | Conveyor | Role |
| :-- | :-- | :-- |
| `pipeline-orchestrator` | — | routing, contract, gates, decision log, economy, restyle, delivery |
| `structure-builder` | K1 | brief, experience model, neutral skeleton, neutralization of existing code |
| `visual-director` | K2 | taste calibration, divergence, contact sheet, merge, tokens, assets, scale |
| `quality-guardian` | K3 | checks D1–D21, AI diagnostics, quality report, verdict |

## Gates in one paragraph each

- **Gate 1 (structure):** the user reviews the working neutral skeleton. Pass =
  explicit "ok" / change list (`changes_requested`) / silence in autonomous
  (`autonomous_passed`, with a confirmation offer on return).
- **Gate 2 (visuals):** blind contact sheet — anonymized "Variant 1/2/3",
  randomized order recorded in the contract, all variants shown simultaneously,
  each with the main + contrast screen. Merge is the default behavior.
- **Autonomous mode:** Gate 1 = objective AI self-check (`autonomous_passed`);
  Gate 2 = AI pre-filter only → `provisional_ai` + a mandatory 3-minute
  confirmation offer when the user returns.

## Verdicts

`ready` | `ready_with_caveats` | `not_ready`. Rules: an open blocker →
`not_ready`; `not_ready` never lowered without a fix + retest; accepted
limitations require a rationale and a named risk owner.

## Definition of Done (every delivery)

1. `status.verdict` = `ready` or `ready_with_caveats` (with an explicit list of
   accepted limitations and risk owners).
2. All D1–D21 checks pass, or carry `skip`/`unavailable` with reasons; no
   blocking check `unavailable` under a `ready` verdict.
3. All images local, alt text, ≤300 KB, declared dimensions.
4. Restyle of any page = token edit + `compile-tokens.py`, zero manual
   component edits.
5. `artifacts/audit/quality-report.md` generated and consistent with the
   contract; `artifacts/decision-log.md` contains all mandatory entries.
6. The user gets a plain-language summary: what was built, what was decided at
   the gates, what was verified, what remains.
