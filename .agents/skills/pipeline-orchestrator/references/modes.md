# Modes — quick / standard / full (v5.1)

## Auto-selection formula

`screens ≤5 AND 1 role AND low risk → quick`;
`6–15 routes OR 2–3 roles → standard`;
`high-risk / payments / personal data → full`.

An explicit user word ("quickly", "keep it simple" → quick; "full process",
"this is critical" → full) always beats auto-selection and is recorded in
`meta.mode_override_reason` + decision log.

## Capability matrix

| Capability | quick | standard | full |
| :-- | :-- | :-- | :-- |
| K1 question budget (one block, functional only) | ≤3 | ≤5 | ≤5 + risk follow-up |
| Directions at Gate 2 | 2 | 3 | 3 (+ wildcard) |
| Boldness spread across directions | safer + bolder | safer / middle / bolder | + wildcard outside the band |
| Taste calibration | references OR style cards | both, user's choice | both, mandatory |
| Blind-description test (external AI) | optional | yes | yes |
| Separate `brief.md` | ✗ (contract only) | ✓ | ✓ |
| `ux/` experience models | ✗ (contract section) | ✓ | ✓ extended |
| `style-calibration.md` | ✗ (contract section) | ✓ | ✓ |
| `asset-manifest.yaml` | ✗ (contract `assets`) | ✓ | ✓ |
| Distinctive assets | ≤1 | ≤3 | as planned |
| Viewports | 390/768/1440 | 390/768/1440 | + project extras |
| QA cycles (fix+recheck) | 1 | 2 | 3 |
| Regeneration budget (Gate 2) | 1 | 1 | 1 |
| Post-scale failure budget | 1 | 1 | 1 |

Viewports are the same in every mode — quick narrows the NUMBER OF SCREENS,
not the viewport coverage.

## Question rules (K1)

- One block of ≤5 (quick ≤3) FUNCTIONAL questions: audience, primary action,
  must-have content, hard constraints, product references (NOT design
  references — design taste is gathered in K2, only by showing).
- Never ask about style, colors, or fonts in K1 [A.3].
- Autonomous: no questions; assumptions are logged (`clarification:
  assumptions_logged`); if some questions were answered and the rest assumed —
  `mixed`.

## Quick-mode ceiling (hard constraint, AC-23)

Allowed artifacts ONLY: `artifacts/design-contract.yaml`,
`artifacts/decision-log.md`, `artifacts/skeleton/skeleton-manifest.yaml`,
`artifacts/visual/direction-set.md`, `artifacts/visual/contact-sheet/`,
`artifacts/visual/visual-system.md`, `artifacts/visual/design-tokens.json`,
`artifacts/prototype/test-scenarios.md`, `artifacts/audit/quality-report.md`.
The content of `brief.md`, `ux/*`, `style-calibration.md`,
`asset-manifest.yaml` lives inside contract sections — creating those files in
quick mode is a fail (`validate-pipeline.py`).

## Upgrade triggers (quick → standard, mid-flight)

Upgrade if K1 reveals ≥2 of: auth/payment/personal-data flow; >5 screens;
multi-role audience; legal/compliance content. Record in
`meta.mode_override_reason` + changelog + decision log. Downgrades only before
K1 starts.

## Autonomous interaction mode (orthogonal)

- Gate 1 autonomous → objective AI self-check (scenarios walkable, skeleton
  matches brief) → `autonomous_passed` (no provisional — objective decision).
- Gate 2 autonomous → AI pre-filter (visible objective factors only,
  swap-augmented pairwise) → `provisional_ai(X)`; the confirming render of any
  merge is `deferred` and included in the return confirmation.
- On the user's first return after any autonomous gate, the FIRST message
  offers a 3-minute confirmation by the ready contact sheet (template:
  `gate-templates.md`).

## Risk level ↔ boldness default

`visual_boldness` default: `familiar_distinctive`. If `risk_level: high` —
default `conventional` with the reason recorded [K1.2.1]. The user can
override explicitly.
