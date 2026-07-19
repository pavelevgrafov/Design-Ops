# Design Production Pipeline v5.1

<img src="docs/banner.svg" alt="Design Production Pipeline — three conveyors, two human gates, one contract" width="100%">

Turns a plain-text request into a finished, verified website or web application.
Architecture: **three conveyors, two human gates, one contract.**

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

## The skills — who builds UX, who builds UI

| Skill | Conveyor | Layer | Owns |
| :-- | :-- | :-- | :-- |
| `pipeline-orchestrator` | — | process | request routing (new build / neutralize / restyle / targeted), the contract as SSOT, both gates, decision log, budgets, delivery report |
| `structure-builder` | K1 | **UX** | product frame, experience model, information pattern, the neutral skeleton |
| `visual-director` | K2 | **UI** | taste calibration, divergent directions, blind contact sheet, merge, DTCG tokens, assets, scaling |
| `quality-guardian` | K3 | proof | deterministic floor D1–D21, AI diagnostics, quality report, verdict |

**UX is built by `structure-builder` (K1).** Everything the user *does*,
before anything about how it *looks*: the primary job-to-be-done, key screens
with required states (loading / empty / error / success), walkable scenarios,
and the information pattern that decides what earns the first viewport
(answer-first, task-first, object-first, event-first, comparison-first).
Output: a deliberately style-less neutral skeleton — gray graphite, real
copy, priority annotations, `not_approved_visual_design` marker — approved by
the human at Gate 1. On the "I already have a prototype" route it
*neutralizes* existing code back to this state instead of rebuilding.

**UI is built by `visual-director` (K2).** Everything the user *sees*, in two
gated phases. Phase 1: taste calibration by showing (reference decomposition
or the style-card test), 2–3 constructed-divergence directions on 7 axes
(composition, type voice, color, surface, shape, imagery, motion) with
machine-verified difference, and an anonymized contact sheet for the blind
Gate 2 choice. Phase 2: merge-by-default with a coherence gate and confirming
render, DTCG design tokens compiled to CSS/Tailwind (the skin property:
restyle = token edit + recompile), an asset mini-gate (3–4 candidates per
raster slot, auto favicon/OG, AI disclosure), and scaling to all screens ×
states under a hard failure budget.

**`quality-guardian` (K3) proves both** — the canonical deterministic floor
D1–D21 (build, console, WCAG contrast, typography, token usage, placeholders,
ban-list, viewports, tap targets, images, performance, a11y, functional
paths, pipeline integrity) plus classified AI diagnostics, ending in a
verdict the delivery report can stand behind: `ready`,
`ready_with_caveats`, or `not_ready`.

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

## License

MIT — see `LICENSE`.
