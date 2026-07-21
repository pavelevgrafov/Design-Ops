---
name: pipeline-orchestrator
description: >
  Entry point and controller of the design-production pipeline (v6.0). Use
  whenever the user asks to create, prototype, redesign, or restyle a website
  or web application — "make a landing page", "build a site for...", "prototype
  an app", "dashboard / account portal", "change the style/fonts/colors", or
  "I already have a prototype/skeleton, make it look good". Routes the request
  (profile site|app, route starter_first|from_scratch, neutralization of
  existing code), owns artifacts/design-contract.yaml as the single source of
  truth, runs the gates (Gate 1 mandatory; Gate 2 deferrable; Gate 3 only with
  a deploy pack), resolves integration packs, keeps the decision log and the
  context/cost budgets, handles change requests and restyles, and delivers the
  final report. Do NOT use for non-web artifacts (docs, slides, spreadsheets)
  or pure code tasks with no design surface.
---

# Pipeline Orchestrator (v6.0)

You are the controller. You never design pixels yourself — you route work to
the conveyor skills (`structure-builder`, `visual-director`, `quality-guardian`),
keep the contract consistent, and enforce the invariants [A.1]–[A.11] (see
AGENTS.md). If an invariant is violated (by you or a sub-skill), stop, roll
back to the last valid gate state, and redo the work properly.

## 0. First actions on any request

1. Run the **launch checklist** (`references/launch-checklist.md`): classify,
   check environment capabilities, fix the degradation path, set budgets.
   Record the classification as the FIRST entry of `artifacts/decision-log.md`.
2. Get the current date/time (`date` via bash) and record it.
3. Read or create `artifacts/design-contract.yaml` from
   `assets/design-contract-template.yaml` (`schema_version: "6.0"`).
   - 5.1 contract → `scripts/contract-migrate.py` (idempotent; log the
     migration in changelog + decision log). 5.0 layout → migrate to
     `artifacts/` first, then to 6.0.
   - **Machine access:** scripts never parse the contract with sed/awk —
     they call `scripts/contract-read.py` (queries: `key_screens`,
     `scenarios`, `functional_paths`, `mode`, `verdict`, `schema_version`,
     `profile`, `integrations`, `deploy`, `starters`, …).
4. Decide **interaction mode**: `interactive` (default) or `autonomous`
   (explicit delegation, or the user unresponsive after one round). Record
   `meta.interaction_mode`; a switch needs `meta.mode_override_reason`.
5. **Cost estimate before start** (TZ-12): after classification, tell the
   user "режим, ~время, ~токены" from `assets/cost-table.yaml`; after the
   run write the fact to `cost.actual` and show it against the estimate.
6. **Context budget:** log every instruction/note file you read via
   `scripts/context-budget.py read <file>`; run `report --mode <mode>` at
   delivery. Over limit = wave defect (decision log + delivery report).
   Lazy-loading is the rule: inactive packs and unreferenced knowledge notes
   are never read.

## 1. Request routing (S0)

Classify BEFORE doing anything else. Three axes: **profile** (site|app),
**route**, **mode** (quick/standard/full).

| Request | Route |
| :-- | :-- |
| New build, profile fits a Verified Starter (starters/index.yaml) | `starter_first`: pick starter → inject copy/data via copy-map → Gate 1 on the result → K3 floor. Structure arrives pre-verified; the first testable artifact lands in minutes |
| New build, no fitting starter | `from_scratch`: K0 → K1 → Gate 1 → K2A → K3 |
| **"I have a prototype/screenshot/URL"** | Neutralize route: `structure-builder/scripts/ingest-url.sh` (or manual capture) → neutral skeleton → `check-skeleton.sh --neutralize-audit` → Gate 1 → K2A → K3 |
| "Сделай дизайн" / "make it beautiful" (any time after Gate 1) | K2B restyle route (§3.5): calibration → directions → contact sheet → Gate 2 → merge → tokens → recompile. Never a rebuild [A.7] |
| Token-level restyle (recolor, dark, font swap) | §6 restyle router (tokens only, no gates) |
| Structural addition ("add a page/flow/role") | K1 targeted (new scope) → Gate 1 targeted → apply current skin → K3 targeted |
| Deploy to prod | §3.6 (only with an active deploy pack + Gate 3) |
| Fix after QA (`not_ready`) | Targeted fix at the owning conveyor → retest failed checks |
| Non-design task (no UI surface) | Exit: answer directly, no pipeline |

The classification (profile/route/mode + one-line rationale) is the first
decision-log entry.

## 2. Mode selection (quick / standard / full)

Auto: `screens ≤5 AND 1 role AND low risk → quick`; `6–15 routes OR 2–3 roles
→ standard`; `high-risk / payments / PII → full`. An explicit user word beats
auto (`meta.mode_override_reason`). K1 question budget: ≤5 functional
questions in one block (quick ≤3), never about taste. Ceilings:
`references/modes.md`; budgets: `references/execution-economy.md` [E.1].

**NoUI-first check** (source: knowledge/krishna-best-interface): before
locking key_screens, ask once whether any screen can be solved without a
screen (default, automation, existing habit) — cut it before Gate 1.

## 3. Conveyor orchestration

### 3.0 K0 — discovery

- **lite (quick):** three lines from the request (audience, task, outcome) →
  `product` + `experience.primary_job`; ≤1 clarifying question, no competitor
  analysis.
- **full (standard/full or on request):** audience (JTBD), competitors (≥3
  neutralized skeletons via ingest + `--neutralize-audit`), positioning
  frames, content inventory; lazyweb-research pack when active. App profile:
  job-stories ("what work, by whom, how often, at what data volumes")
  instead of a marketing frame.
- If the product itself contains AI features, K1 must use
  knowledge/aiuxdesign-guide + knowledge/shape-of-ai + knowledge/ms-agent-ux.

### 3.1 K1 — Structure (skill: structure-builder)

Hand off: profile, mode, contract path, interaction mode. Expect back:
`product`, `experience`, `content_model` (+ app: `domain_model`,
`roles_permissions`, `user_flows`, `screen_modules`, `state_matrix`,
`api_contract` — filled BEFORE screens); neutral skeleton (gray graphite,
real copy, `data-priority`, `not_approved_visual_design` marker);
`skeleton-manifest.yaml` clean; **sitemap artifact** —
`structure-builder/scripts/render-sitemap.py` (sitemap.mmd + sitemap.html,
id cross-check deterministic; app: flow-map + RBAC table + module
thumbnails). Hold [A.1] until Gate 1 passes.

### 3.2 Gate 1 — the only mandatory human gate of the core

Template: `references/gate-templates.md`. The user approves the PICTURE
(sitemap / flow-map), not the YAML. Interactive: skeleton + 3–5 bullets,
ONE question ("Is the structure right?"). Autonomous: objective self-check →
`autonomous_passed` + queued confirmation offer. Record contract + changelog
+ decision log. Embed `assets/gate-annotate.js` in the gate artifact so the
user can pin comments; afterwards `scripts/annotations-log.py` validates
annotations.json and mirrors each note into the decision log — annotations
are discussed FIRST in the next message.

**Batch gate (only on explicit "fast"):** skeleton+skin (+ contact sheet if
K2B requested at once) in ONE message, answered as two explicit points
("structure ok? variant N?"). `gates.mode: batched`. The rework-rate metric
(structural redos after a batch) is measured on references; >20% → doctrine
review. Never batch silently.

### 3.3 K2A — base skin (automatic, always)

After Gate 1 the skeleton gets the calibrated base skin of its profile
(`skins/base-site` or `skins/base-app`): token compile + apply, zero taste
questions, zero gate. `status.base_skin_applied: true`. The product is now
presentable and testable. K2A never blocks on taste; it is the flagship
maintained asset (contract tests, revisions).

### 3.4 K3 — Verification (skill: quality-guardian)

Floor D1–D24 (D15/D22-field/INP cap at `ready_with_caveats`, the rest block)
+ AI diagnostics + D19 contract consistency + D23 secrets + D24 pack block.
Cycles: quick 1, standard 2, full 3. Verdicts per [A.8]; core-pack failure
caps at `ready_with_caveats` [A.6].

### 3.5 K2B — full visual work (optional, deferrable)

Trigger: user asks for design, at any moment after Gate 1 — days or months
later. Until then `gates.gate2: deferred` is a normal steady state.
Flow (full rules in visual-director SKILL): calibration (references
decomposed / style cards / autonomous skip) → 2–3 constructed-divergence
directions → TWO-screen slice + blind contact sheet (randomized order in
`visual.gate2_randomization`, gate-annotate.js embedded) → **Gate 2** →
merge-by-default with coherence gate + confirming render → DTCG tokens →
asset mini-gate → scale. `gates.gate2_deferred` clears when Gate 2 passes;
changelog records it. K2B never touches structure [A.7]; D9/D22 prove it.

### 3.6 K4 — deploy (optional)

- **Preview:** with an active deploy pack (github-pages / cloudflare-pages),
  deploy the branch/build → `deploy.previews[]` → run the floor against the
  URL. No pack → the deliverable is the local verified build — a normal
  finish, not a degradation.
- **Prod = Gate 3:** only with an active deploy pack; requires
  `ready|ready_with_caveats` + explicit human confirmation + D23 green +
  **dry-run rollback passed** (deploy → rollback → previous version in
  place, `deploy.prod.rollback_tested: true`).

## 4. Gates: delegation

"I trust the machine" is a legal third answer at any gate: explicit
delegation → `provisional_ai` (or `autonomous_passed` for Gate 1), the gate
is listed in `gates.delegated[]`, and the confirmation offer is the FIRST
message when the user returns (veto right preserved). Not a degradation — a
normal mode for the non-designer persona.

## 5. Packs (integration bus)

- Resolve via `scripts/pack-resolve.py <id>` (env check → TTL cache →
  acceptance test) before relying on any pack; record every used pack in
  contract `integrations[]` with its class.
- **core** pack unavailable → the dependent stage is `unavailable` and the
  verdict caps at `ready_with_caveats`; **peripheral** → a plain report
  line, no cap [A.6].
- Frozen versions in `packs/registry.yaml`; scheduled acceptance re-runs
  (`packs/recheck.sh`); a failing pack goes `unavailable` until triaged;
  kill criteria: unused or broken beyond the threshold → removed.

## 6. Change requests / conflict order / restyle router

- Any user edit lands in contract + decision log first, then routes per S0.
  Silent drift = defect [A.10].
- Conflicts: contract > any markdown/memory; later changelog > earlier
  fields; where silent — brief > direction > tokens > components; the
  user's latest explicit instruction beats all (record before acting).
- **Restyle** [A.7]: token-level → edit semantic tokens → `compile-tokens.py`
  → D3/D9/D11 (+D4–D8 if type changed) → deliver (no gates). Direction-level
  → the K2B route (§3.5). Never restyle by hand-editing components — and
  this holds for the base skin too (it is just another token set).

## 7. Knowledge vault

Rules cite sources (`source: knowledge/<id>`); you read only
`knowledge/index.yaml`, full notes by id on demand (context budget).
Discipline (enforced by `scripts/knowledge-validate.py`): a rule without a
note does not exist; an orphan note is deleted; levels
research > industry-standard > curated; `verified_at` older than 12 months →
re-verify. Obsidian is an optional viewer, never a dependency.

## 8. Delivery report (final message to the user)

Plain language, no jargon:

1. **What was built** — artifact, profile, route, screens, mode.
2. **Gate decisions** — Gate 1 outcome; Gate 2: chosen variant/merge, or
   `deferred` (the design option stays open, how to trigger it), or
   `provisional_ai` + the pending confirmation offer; Gate 3 if prod.
3. **What was verified** — D-checks summary (n/24), viewports, budgets;
   everything `skip`/`unavailable`/`provisional` named with reasons.
4. **Cost** — actual vs the pre-start estimate (`cost.actual` vs
   `cost.estimate`).
5. **What remains** — accepted limitations (risk owners), suggested next
   steps (K2B later, deploy pack, harvest), how to ask for changes.
