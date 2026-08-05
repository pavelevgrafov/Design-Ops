# Gate-overtaking mechanics (provisional pipeline) — A.25 reference

The gate is a veto right, not a stopcock. The machine continues past a shown
gate under `provisional` status; the owner confirms or vetoes afterwards.
Hard boundaries while any gate is provisional:

- allowed: K2A base skin, K3 floor run, K2B direction preparation (slice only);
- forbidden: verdict, delivery, deploy, Gate 3, harvest commits, any
  irreversible or externally visible action; K2B scaling beyond the slice
  (A.2 untouched); removing the `not_approved_visual_design` marker.

Contract fields (schema 7.0):
`gates.mode: blocking|overtaking`, `gates.provisional_since`,
`gates.provisional_scope[]`, `gates.provisional_plateau`,
`status.deliverable_blocked: true` while any gate is provisional.

Resolution paths:
1. **Confirm** — one batched action sets the gate to `passed`, records the
   confirmed `provisional_scope` in the decision log, clears
   `deliverable_blocked`.
2. **Veto** — cascade invalidation over the input-hash graph (E.3): only
   artifacts downstream of the changed input are recomputed; rejected
   directions/skeletons are archived, not deleted.
3. **Silence** — the orchestrator stops at `provisional_plateau` (a defined
   checkpoint, never mid-stage) and queues the confirmation offer. Per A.26,
   silence is a pause, never self-assigned progress.

Prerequisites: A.25 ships only as one package with A.26 (no silent machine
decisions) and requires the input-hash graph to exist — without recorded
input hashes a veto costs a full recompute and the rework metric turns
against the feature.

Defaults: `overtaking` for quick/standard low-risk; `blocking` for full /
payments / PII / high-risk; the owner's explicit word always wins and is
recorded with `meta.mode_override_reason`.

Metrics: `gate_wait_minutes` (before/after), `veto_rate`,
`veto_rework_minutes`. Rollback criterion: if cumulative veto rework over 20
runs exceeds the saved gate-wait time, the mode default reverts to
`blocking` with a doctrine review.

Enforcement: stage policy in `gate-require.py` (which stages may run under
`provisional`), verdict/deliver refusal while `deliverable_blocked`,
`validate-pipeline.py` rejects a `ready*` verdict with any provisional gate.

Full design (rationale, TRIZ context): Kimi workspace doc
`08-Гейт-обгон-механика.md` (2026-08-04).
