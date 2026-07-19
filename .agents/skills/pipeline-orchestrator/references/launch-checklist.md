# Launch checklist — before ANY new run

Every item is recorded (contract field or decision-log line). If any item
can't be completed, stop and say why.

- [ ] **Request classified** per the S0 routing table (orchestrator SKILL §1);
      the route + one-line rationale is the FIRST decision-log entry.
- [ ] **Depth mode determined** (auto-select formula or explicit user word)
      and written to `meta.mode`; overrides have `meta.mode_override_reason`.
- [ ] **Interaction mode determined** (`interactive`/`autonomous`) and written
      to `meta.interaction_mode`.
- [ ] **Contract found/created** at `artifacts/design-contract.yaml`
      (schema 5.1). If a v5.0 contract was found at the project root: migrate
      (move + upgrade + verdict mapping), log the migration.
- [ ] **Not a restyle / targeted change masquerading as a new build** — if it
      is, the full conveyor does NOT start (S0 table).
- [ ] **Invariants acknowledged:** no visual work before Gate 1 [A.1], no
      scaling before Gate 2 [A.2].
- [ ] **Stage budgets set** [E.1]: tool calls per stage, direction count by
      mode, asset candidates 3–4, regeneration budget 1, post-scale budget 1.
- [ ] **Environment capabilities checked:** browser? playwright? node? image
      generation? The degradation path (quality-guardian
      `references/environment-degradation.md`) is FIXED IN ADVANCE and logged.
- [ ] **Decision log opened** at `artifacts/decision-log.md` from the template.
