# Design Production Pipeline v5.1

Turns a plain-text request into a finished, verified website or web application.
Architecture: **three conveyors, two human gates, one contract.**

```
K1 "Structure"   →   GATE 1 (human)   →   K2 "Visual"   →   GATE 2 (human)   →   K2 continued   →   K3 "Verification"
(scaffold +        (structure            (directions →      (blind choice        (merge → tokens →      (checks D1–D21
 neutral            approved)             contact sheet)      of a direction)     assets → scale)       + AI diagnostics)
 skeleton)
```

## What it is for

A skill pack for Codex CLI-style agents that takes a request like "make a
landing page" or "I have a prototype, make it look good" and runs it through
a production line: structure first (a neutral skeleton approved by a human),
then visuals (a blind choice between real, divergent directions), then
machine-verified quality. The human makes the taste decisions at two gates;
the machine proves the floor; AI assists only where it is reliable.

## Problems it solves

- **AI slop and mode collapse.** "3 variants" from one model are usually one
  layout recolored. Here divergence is constructed (persona + domain seeds,
  7 axes, boldness spread) and machine-verified (`check-divergence.py` plus
  an external blind-description test); a linted ban-list blocks the
  statistical defaults (first-position Inter, indigo→purple gradients, glass,
  bento, blobs, icon-per-label, marketing-slop copy).
- **Taste gathered by interrogation.** Instead of "why do you like it?",
  taste is calibrated by showing: references decomposed into principles, an
  8–10 style-card test, and an anonymized contact sheet with recorded
  randomization. No anchoring, no authorship hints.
- **Frankenstein merges.** "Typography from 2, color from 3" is a default
  path, but every merge passes a coherence gate and a confirming render
  before it scales to the whole product (with a hard post-scale failure
  budget and a documented `not_ready` stop).
- **Unverifiable quality claims.** A canonical deterministic floor D1–D21
  (build, console, WCAG contrast, typography, token usage, placeholders,
  ban-list, viewports, tap targets, images, performance, a11y, functional
  paths, pipeline integrity) runs by script; a missing capability reports an
  honest `unavailable` and caps the verdict — never a silent pass.
- **Restyle as code surgery.** The design lives in DTCG tokens; a restyle is
  a token edit + recompile with zero manual component edits (the skin
  property, enforced by `check-token-usage.sh`).
- **Silent drift and lost decisions.** One contract (schema 5.1) is the
  single source of truth; a decision log records every gate, hypothesis, and
  accepted risk; `validate-pipeline.py` rejects retro-fitted compliance.
- **"I already have a prototype."** A dedicated neutralize route strips an
  existing build back to an approved neutral skeleton (scenarios and logic
  preserved) instead of rebuilding it from scratch.

## Core principles

1. **Taste is gathered by showing, not by asking.** User references are
   decomposed into principles; choice happens on a blind, anonymized contact
   sheet. No "why do you like it?" before the choice is recorded.
2. **The machine owns the floor, the human owns the ceiling, AI does
   diagnostics in between.** Scripts verify objective checks (D1–D21); the
   human decides taste at Gate 2; AI may only diagnose and pre-filter —
   never issue a final taste verdict (`provisional` + `model_judged` always).
3. **The contract is the single source of truth.** `artifacts/design-contract.yaml`
   beats any markdown; the changelog beats field values; where the contract is
   silent, the earlier stage wins. Decisions are recorded before they are executed.
4. **Degradation never upgrades the verdict.** A missing capability is an
   explicit status (`unavailable`/`degraded`/`skip`), never a silent pass.

## Modes

| | quick | standard | full |
| :-- | :-- | :-- | :-- |
| When | landing, ≤5 screens, 1 role, low risk | 6–15 routes, 2–3 roles | >15 routes, high-risk, payments, PII |
| Directions at Gate 2 | 2 | 3 | 3 (+wildcard) |
| Taste calibration | references OR style cards | both, user's choice | both, mandatory |
| QA cycles | 1 | 2 | 3 |
| Viewports | 390/768/1440 (all modes) | same | same + project extras |

Interaction modes (orthogonal): **interactive** (default) and **autonomous**
(gates run as objective AI self-check / `provisional_ai` pre-filter, with a
mandatory 3-minute confirmation offer when the user returns).

## Install

1. Copy `.agents/`, `eval/`, `AGENTS.md`, `README.md` into your repo.
2. Python ≥3.10 + `pip install pyyaml`. For browser checks:
   `npm i -D playwright && npx playwright install chromium`.
3. `chmod +x .agents/skills/*/scripts/*`.
4. First run: prompt P01 from `eval/example-prompts.md`, score with
   `eval/eval-rubric.md` (pass ≥ 8.5/10, no zeros in blocking criteria).

See `INSTALL.md` for the full installation and v5.0 → v5.1 migration guide.

## Skills

| Skill | Conveyor | Owns |
| :-- | :-- | :-- |
| `pipeline-orchestrator` | — | routing, contract, gates, decision log, economy, restyle, delivery |
| `structure-builder` | K1 | brief, experience model, neutral skeleton (incl. neutralizing existing code) |
| `visual-director` | K2 | calibration, divergence, contact sheet, merge, tokens, assets, scaling |
| `quality-guardian` | K3 | deterministic floor D1–D21, AI diagnostics, report, verdict |

## License

MIT — see `LICENSE`.
