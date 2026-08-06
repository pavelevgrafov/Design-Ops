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
   user "режим, ~время, ~токены" from `assets/cost-table.yaml`.
   **Measure the run, never narrate it:** open every stage with
   `tools/dops stage start <K0|K1|gate1|K2A|K3|K2B|deliver>` and close it
   with `tools/dops stage end <name>`; at delivery run
   `tools/dops cost --write`, which computes `cost.actual` from the trace
   and the context log and writes it into the contract. A prose
   `cost.actual` ("one session") is a defect: what is not measured cannot
   be managed, and every later speed claim becomes unfalsifiable.
6. **Context budget:** the resident set is `.agents/RULES.card.md` plus the
   contract — load it once and hand it to every conveyor skill. Everything
   else is on demand: a reference file when a decision is contested, a
   knowledge note by id, a pack manifest only when the pack is in
   `integrations[]`. Log every instruction/note file you read via
   `scripts/context-budget.py read <file>`; run `report --mode <mode>` at
   delivery. Over limit = wave defect (decision log + delivery report).
   Reading a full reference "to be safe" is the defect the card exists to
   prevent: it is paid on every turn that follows.

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

**Hand off, do not accumulate.** Each conveyor stage runs in a FRESH context
built by `tools/dops handoff <K0|K1|K2A|K2B|K3|deliver>`: the rule card, that
stage's slice of the contract, its inputs, its outputs, its acceptance
command and an explicit do-not-read list (~1.7–2.8k tokens, flat). The stage
returns its artifacts plus a summary of at most ten lines — never its whole
working transcript. One continuous context instead would still be carrying
K0's research at K3 and paying for it on every turn. Verify with
`dops handoff --check <stage>` that a stage produced what it promised before
moving on.

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

The floor is ONE command — `tools/dops verify --profile <mode>` — returning
one JSON; read its `failures[]`, never the check registry.
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

### 3.2b Gate-overtaking and the announcement duty (v7.2)

`gates.mode: overtaking` — the machine keeps working past a SHOWN gate under
`provisional` instead of idling. Full mechanics: `references/gate-overtaking.md`.
Two rules make it safe, and neither is optional:

- **[A.25]** provisional work is never a product. Before any stage,
  `gate-require.py <contract> stage:<K2A|K3|K2B-slice|…>`; before a verdict,
  `… verdict`. Scaling, verdict, delivery, deploy, harvest and marker removal
  are refused while a gate is provisional, and `status.deliverable_blocked`
  must agree with the gates or the contract itself is the defect.
- **[A.26]** nothing silently. `autonomous` requires
  `meta.autonomous_granted_by` — the owner's word for THIS run; silence is
  not a grant. Every machine gate decision is announced AT THE MOMENT with a
  rollback command: `dops announce --gate gate2 --decision provisional_ai
  --rollback "<how the owner undoes it>"`. It lands in the pulse as a
  checkpoint, so the owner sees it while it matters, not in the closing
  report. `dops verify` refuses a run where either rule was skipped.

Overtaking without A.26 recreates the kruto-landing incident at a larger
scale: work runs ahead, decisions are made quietly, the owner finds out at
the end. Ship them together or not at all.

Veto is cheap by construction: `dops hash plan <changed-input>` names exactly
what must be recomputed and what may be reused.

### 3.2c Checkpoints and the control queue (v7.2, У-2/У-3)

A run used to have exactly one window: the final report. Every intermediate
artifact is now published the moment it exists, with the actions the owner
may take on it — and publishing never stops the conveyor.

```
dops checkpoint publish --id sitemap --artifact artifacts/sitemap.html --provisional
dops checkpoint decide  --id sitemap --action accept
dops control issue --command speed_up
dops control apply --at "checkpoint:sitemap"
```

- **Closed registry** (`tools/checkpoint-registry.json`): brief-card, sitemap,
  skeleton, base-skin, directions, merge, tokens, k3-report, lod-transition.
  A checkpoint carrying no actions is a status line — the illusion of control
  — and `publish` refuses it. Adding a type means editing the registry, not
  inventing one at run time.
- `accept` on a gate checkpoint (sitemap, directions) **is** the batched
  confirmation of that gate and of everything done on credit under A.25.
- **Commands run only at control points** — a stage script finishing, a
  checkpoint publishing, a stage starting. Never mid-script: a command applied
  halfway through leaves a half-written artifact.
- `rollback_to` costs only what actually changed — it walks the input-hash
  graph and supersedes the checkpoints after the target. Without recorded
  hashes it is REFUSED with the reason [A.6], because a rollback that silently
  means "rebuild everything" is worse than one that says so.
- `skip_scope` can never reach the core floor [E.4], whoever asks.
- Write `meta.run_plan` at classification — stages, checkpoints, eta, where the
  owner is needed and for how long in total. The owner should know the price
  of their attention before the run starts, not after.
- `meta.target_lod` is the agreed depth. A result "not detailed enough" is
  usually a target nobody set; `status.lod` records what was reached, and a
  gap without an owner command is a defect line in the delivery report.

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
### Revisions: pins and the sorting station (v7.2, П-1/П-2)

Every edit used to cost the same. "Make the button darker" and "add a booking
flow" both ran the full cycle, and the big model met both. Now:

- **Pins live on the artifact, not in chat.** `assets/gate-annotate.js` is
  always-on: embed it in the skeleton, the landing, the app. A click on an
  element records selector + viewport + kind, so "that blue button on the
  third screen, you know the one" stops being a conversation.
- **`tools/dops pins classify` sorts before the model sees anything:**
  lane **A** token/copy (a script, seconds), **B** block swap or reorder,
  **C** structure (narrow K1 + targeted gate), **D** taste or ambiguous
  (options, or one question — and it waits).
- The classifier is a dictionary, not a model: it must be cheaper than the
  work it routes. Where the wording does not determine the action it says so
  and routes to D. **A wrong cheap lane costs more than an honest question.**
- Measured on a realistic 15-pin revision set: **67% never reach the big
  model** (the design estimate was ~80% — report the measured number, not the
  estimate).
- Duplicate pins are marked, never dropped: the owner wrote it twice for a
  reason.
- **`tools/dops pins check` stands between sorting and doing.** Four questions
  in a fixed order: does the selector still resolve, is the value inside the
  declared ranges, does it contradict `scope.exclusions` or the decision log,
  has the owner already said this. A refusal always carries alternatives —
  `annotations-log.py` fails a `rejected` verdict that arrives without a
  reason and a way out, because a wall is not a negotiation. Measured on the
  same 15-pin set: **every pin decided by script, zero model calls.**

- **Intake is a stream, not a batch.** `tools/dops pins sweep` is one pass —
  only the new pins, classified and checked in birth order, latencies
  recorded, one summary line. `dops pins apply [--machine-only]` executes the
  pins whose plan carries fully extracted parameters, one transaction each,
  rolling back alone on failure; two pins on the same target do not both land
  (the later wins, the earlier is `superseded` with the reason). Measured on
  the realistic revision set, **0% of pins as owners actually write them are
  machine-executable** — so this is an accelerator for the explicit cases, not
  a replacement for the assistant on lane A.

- **The owner turns the parameters themselves.** `assets/token-panel.js` plus
  a `panel-config.js` emitted by `tools/dops panel emit --skin <S> --artifact
  <page.html>`: palette, type scale, line length, dark theme — the change is
  visible in the same second, with no assistant in the loop. Embed it only
  where compiled tokens exist; **no compiled tokens, no panel tag** (the JS
  never guesses — without a config it renders nothing).
  The safe domain is computed by the emitter, not in the browser: an unsafe
  value is not warned about, it is absent from the list. `dops panel apply
  token-delta.json` is the only door back into `tokens.json` — it refuses a
  stale delta, refuses anything outside the emitted options, re-runs the
  compiler and D3, and rolls the file back in full on any failure.
  The panel covers **parameters** (lane A). Everything compositional stays
  with the pins, always.

- **Scope the change before doing it:** `tools/dops hash plan <changed-input>`
  prints exactly what must be recomputed, in derivation order, and what may
  be reused. Rebuilding what did not change is the most expensive habit in
  the pipeline. After each stage, `dops hash record --stage <S>` re-pins;
  `dops hash check` at K3 catches a generated artifact that was hand-edited
  instead of regenerated.
- Conflicts: contract > any markdown/memory; later changelog > earlier
  fields; where silent — brief > direction > tokens > components; the
  user's latest explicit instruction beats all (record before acting).
- **Restyle** [A.7]: token-level → edit semantic tokens → `compile-tokens.py`
  → D3/D9/D11 (+D4–D8 if type changed) → deliver (no gates). Direction-level
  → the K2B route (§3.5). Never restyle by hand-editing components — and
  this holds for the base skin too (it is just another token set).

## 7. Knowledge vault

Numbers come from the frozen constraints snapshot
(`.agents/knowledge-sync/constraints/`) via `RULES.card.md` — one door, no
live wiki read at runtime. Prose notes explain *why* a number is what it is:
rules cite sources (`source: knowledge/<id>`); you read only
`knowledge/index.yaml`, full notes by id on demand (context budget). Where
a note and the constraints disagree, the YAML wins — it is what the checkers
read.
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
   steps (K2B later, deploy pack), how to ask for changes.
6. **Harvest decision** — before delivering, run `tools/dops harvest --check`
   and record `candidate:<id>` (the run produced a pattern the library
   lacks), `reused:<id>` (it rode an existing starter), or
   `declined: <reason>`. A Definition-of-Done item, not a nicety:
   `starter_first` costs roughly half of `from_scratch`, and the library
   only grows if every run answers the question.

## 9. Slash commands (v7.0)

Trigger aliases for the pipeline stages — same routing rules, shorter
invocation. A slash command never skips a gate; it only presets the route.

| Command | Maps to | Preset |
| :-- | :-- | :-- |
| `/design <request>` | full pipeline entry (S0 routing) | route by classification, Gate 1 mandatory |
| `/restyle [scope]` | K2B over the finished foundation | requires a `ready`-family verdict; never touches markup [A.7] |
| `/verify` | K3 floor re-run on the current build | D1–D24 (+D25–D38 as wired); verdict from the taxonomy |
| `/deploy <target>` | K4 via the matching deploy pack | Gate 3 rules apply (ready-family + rollback dry-run + D23 green), verified mechanically: `gate-require.py gate3` refuses otherwise |

Unknown or ambiguous commands fall back to normal S0 classification.

## 10. Gate retrospectives (v7.0)

After EVERY gate outcome (passed, autonomous_passed, provisional_ai,
rejected, deferred), append a retrospective entry to the decision log:
what was decided → what the gate surfaced → what to watch next. One to
three lines, no bureaucracy. This is the Focus → Test → Learn → Decide
loop made concrete: the log stays the single memory of *why*, and the next
gate (or the next restyle, months later) inherits the context instead of
re-deriving it.
