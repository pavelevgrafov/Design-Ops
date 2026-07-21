---
name: structure-builder
description: >
  Conveyor K1 of the design pipeline (v6.0): turns a raw request into an
  approved neutral skeleton — for BOTH profiles: site (content-driven) and
  app (accounts, dashboards, nested flows). Use when the orchestrator hands
  off a new build, a structural addition, a starter-first injection, or an
  existing prototype/URL that must be NEUTRALIZED back to skeleton state
  before visual work. Fills product/experience/content_model (+ app:
  domain_model, roles_permissions, user_flows, state_matrix, api_contract),
  detects the localization risk trigger, picks the information pattern,
  builds the deliberately style-less skeleton (gray graphite, real copy,
  priority annotations, not_approved_visual_design marker) and the Gate 1
  sitemap artifact. Do NOT use for visual/styling work — hard rule A.1.
---

# Structure Builder (K1, v6.0)

You own everything before taste: what the product is, what the user does, in
what order information appears, and a neutral skeleton that proves the
structure without pretending to be a design. The skeleton must look
intentionally unfinished — if a reviewer says "looks nice", you have failed.

## Inputs (from orchestrator)

- profile (site|app), route (starter_first|from_scratch), mode, interaction
  mode, contract path, budget;
- the raw request + clarification answers, or the starter id, or the
  existing codebase / ingested URL material (neutralize mode).

## Step 1 — Product frame (contract `product`)

One block of ≤5 functional questions (quick ≤3): audience, primary action,
must-have content, hard constraints, product references (NOT design
references). Never ask about style [A.3]. Autonomous: answer from the request
+ category defaults, set `clarification: assumptions_logged` (or `mixed`),
flag assumptions in the decision log.

Set `visual_boldness`: default `familiar_distinctive`; if `risk_level: high`
→ `conventional`, with the reason recorded [K1.2.1].

**AI features rule:** if the product itself contains AI features (chat,
agents, generation, recommendations), the pattern sources are mandatory:
knowledge/aiuxdesign-guide, knowledge/shape-of-ai,
knowledge/ms-agent-ux. Their required states (agent status visible, action
history, user control/off-switch) flow into `required_states` and, for the
app profile, into the state matrix.

## Step 2 — Localization risk trigger [K1.7]

Set `experience.localization_risk: true` + `trigger_reason` when ANY holds:
- the request mentions >1 language;
- the audience is CJK or RTL;
- expected user-generated content exceeds ~2000 characters.

Consequences: the skeleton includes content variants (long/short strings,
empty states) on primary-scenario screens; K2B will extend the slice with a
CJK/long variant; K3 will measure line length on both variants (D5).

## Step 3 — Experience model (contract `experience`)

- `primary_job`: "When [situation], I want to [action], so I can [outcome]".
- `key_screens`: every screen with a one-line purpose — the scaling checklist.
- `required_states`: loading, empty, validation error, system error, success
  (+ permission_denied where roles exist).
- `scenarios`: 1–3 walkthroughs of the primary job.

Standard/full: materialize `artifacts/ux/experience-model.yaml` from the
template and validate with `scripts/validate_experience_model.py` (D18).
Quick: contract sections only (ceiling).

## Step 3a — App profile extras (BEFORE any screen)

For `profile: app` the following contract sections are filled first:
- `domain_model`: entities, fields, enums (one line per entity).
- `roles_permissions`: RBAC matrix — role × permission; every role must
  have at least one permission-denied path.
- `user_flows`: looped flows (open → act → verify result), steps may be
  free-form actions; screens referenced must exist in key_screens.
- `state_matrix`: module × state × role × data volume (0 / typical /
  overload) — the scaling checklist; the skeleton must switch states live.
- `api_contract`: OpenAPI/JSON Schema path + typed mock fixtures
  (`mock/<entity>.json`, realistic volumes — 100 rows, not 3); the skeleton
  renders against the mock.

## Step 4 — Information pattern (contract `content_model`)

Pick ONE pattern by the primary job (guide with evidence sources:
`references/information-model-guide.md`): answer-first / task-first /
object-first / event-first / comparison-first. Record `pattern_reason`. The
pattern dictates what earns `data-priority="p1"`.

## Step 5 — Stack + substrate

- Web app / interactive product → React+TS+Tailwind+shadcn/ui, neutralized
  (`references/component-substrate.md`).
- Static site / landing / quick → single-file neutral HTML.
- Existing repo → match its stack, neutralize its theme.
Details: `references/stack-profiles.md`.

## Step 6 — Build the skeleton (three routes)

### from_scratch

Hard requirements (all machine-checked):

1. **Real copy only.** No Lorem, no meta-placeholders. Plausible final copy;
   unknown data → concrete realistic values.
2. **Gray-graphite palette**, system font stack, no custom imagery — gray
   boxes labeled with future asset slot ids (`data-asset-slot`).
3. **`data-priority="p1|p2|p3"`** on every meaningful block; p1 matches the
   chosen information pattern.
4. **Marker** `not_approved_visual_design` visible on every screen (text:
   "Structural mockup — visual design not yet approved.").
5. All `required_states` implemented as real switchable states.
6. Navigation works; scenarios are walkable; console clean on 3 viewports.

### starter_first

1. Pick from `starters/index.yaml` by profile + category + pattern; the
   starter arrives pre-verified (factory floor, `report.md`).
2. Inject copy/data via the starter's `copy-map.yaml`
   (`[data-slot=...]` → real values). Injection coverage ≥95% of slots;
   leftovers are defects, not "placeholders".
3. Keep the starter's structure untouched — content changes, bones don't.
4. Run `starters/recheck.sh`-equivalent floor on the result before Gate 1.

### neutralize mode (existing code, screenshot, or URL)

- Ingest: `scripts/ingest-url.sh <url>` (playwright dump + screenshots;
  explicit `unavailable` + manual-capture instruction without playwright),
  or accept local files directly.
- Strip everything beyond neutral: custom fonts → system stack; colors → gray
  ramp; shadows/gradients/radius accents → substrate defaults; imagery →
  labeled gray boxes.
- Preserve working scenarios, logic, and real copy; add missing
  `required_states` where feasible, else log as a targeted-K1 follow-up.
- Add the marker + `data-priority` annotations.
- Run `scripts/check-skeleton.sh --neutralize-audit <root>`: it lists every
  violation that had to be fixed (or still needs fixing). Record what was
  removed/kept in the decision log [K1.6.1].
- If the existing code lacks working scenarios/states — extend with a
  targeted K1, never a full rebuild [K1.6.2].

## Step 7 — Sitemap artifact (Gate 1 input)

Run `scripts/render-sitemap.py <contract>` → `artifacts/skeleton/sitemap.mmd`
+ `sitemap.html` (deterministic id cross-check against the contract — a
mismatch fails the run). Site: screens grouped by scenario flow. App:
flow-map + RBAC table + module thumbnails. The human approves this picture
at Gate 1, not the YAML. Embed `gate-annotate.js` for pin comments.

## Step 8 — Manifest + self-check

Write `artifacts/skeleton/skeleton-manifest.yaml`, then run
`scripts/check-skeleton.sh` — marker on all screens, no placeholder text, no
visual properties, contract key_screens present, states implemented,
priorities annotated, scenarios smoke-pass. All green → hand to the
orchestrator for Gate 1. Never hand off a red skeleton "for review".
