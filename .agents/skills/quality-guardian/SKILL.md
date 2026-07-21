---
name: quality-guardian
description: >
  Conveyor K3 of the design pipeline (v6.0): autonomous verification of the
  finished build. Runs the canonical deterministic floor D1-D24 — build,
  console, WCAG contrast on semantic token pairs, typography (D4-D8
  granular), token usage, placeholders/hotlinks, ban-list, viewports
  390/768/1440, tap targets, image hygiene, lab performance (D15, caps at
  ready_with_caveats), skeleton-marker removal, divergence re-check, UX-model
  validation, pipeline integrity (D19: gate order, v6 enums, deferred Gate 2,
  Gate 3 rollback, decision-log completeness, realized==confirmed direction,
  not_ready never lowered), a11y quick pass (D20), functional paths (D21),
  visual regression (D22: unapproved diff blocks, approve is human), secrets
  scan (D23: blocking, precedes any deploy), service-pack acceptance block
  (D24: core pack unavailable caps the verdict) — plus the INP field beacon
  (p75 over 200ms caps, never blocks) and AI diagnostics classified
  objective/heuristic/subjective x severity (subjective <= minor,
  model_judged: true, swap-augmented). Fixes trivial mechanical issues,
  routes substance back with exact values, writes
  artifacts/audit/quality-report.md and the contract verdict
  (ready/ready_with_caveats/not_ready). Never issues taste verdicts.
---

# Quality Guardian (K3, v6.0)

Hardening (all covered by `eval/selftest/run-self-test.sh`):
- Shell checks are bash 3.2 / BSD grep compatible (macOS out of the box).
- The contract is read ONLY via `pipeline-orchestrator/scripts/contract-read.py`.
- No `grep -q` downstream of a pipe: capture-then-test everywhere.
- Statuses are set by scripts, from a closed taxonomy [A.11] — never by prose.

The machine owns the floor. Prove the build meets the canonical floor
D1–D24, run honest diagnostics about what only a model can see, report so
the user can trust it. You never judge taste — Gate 2 did that (or it is
deferred, and the base skin carries no taste claims to check).

## Status taxonomy (use exactly these)

`pass` / `fail` / `skip(reason)` / `unavailable(reason)` / `degraded(what)` /
`provisional` — full definitions: `references/status-taxonomy.md`. Every
check in the report also carries an EXECUTOR: `script` / `model_judged: true`
/ `human`.

## Workflow

### 1. Deterministic floor D1–D24

Canonical registry: `references/deterministic-floor.md`. Tooling map:

| Check | Tool |
| :-- | :-- |
| D1 build | project build command |
| D2 console | `run-ui-checks.sh` |
| D3 contrast | `check-contrast.py` (token pairs, `--dark` when present; formula per WCAG 2.2 — source: knowledge/wcag) |
| D4–D8 typography | `check-typography.py` (granular lines per check) |
| D9 token usage | `check-token-usage.sh` |
| D10 placeholders/hotlinks | `check-placeholders.sh` |
| D11 ban-list | `visual-director/scripts/lint-ban-list.sh` |
| D12 viewports 390/768/1440 | `run-ui-checks.sh` |
| D13 tap targets ≥24px | `run-ui-checks.sh` |
| D14 images | `check-placeholders.sh` + fs scan |
| D15 performance (lab) | `run-ui-checks.sh` — violation caps at ready_with_caveats, never blocks |
| D16 marker removed | grep `not_approved_visual_design` (present while Gate 2 is deferred — that is the honest state) |
| D17 divergence | `check-divergence.py` re-run + blind_test fields (only when K2B ran) |
| D18 UX model | `validate_experience_model.py` (standard/full) |
| D19 pipeline integrity | `validate-pipeline.py` (incl. v6 enums, deferred-G2 legality, Gate 3 rollback) |
| D20 a11y quick pass | `run-ui-checks.sh` (axe-core; zero critical/serious) |
| D21 functional paths | `run-ui-checks.sh` (keyboard probe + alternative + error recovery, separate D21-keyboard / D21-paths lines; undeclared paths = explicit `unavailable` + verdict cap) |
| D22 visual regression | `visual-regression.sh reference|test|approve` — an unapproved diff BLOCKS; `approve` is a human action recorded in the decision log; no playwright → `unavailable` + cap |
| D23 secrets scan | `check-secrets.py` — BLOCKING, runs before any deploy and at every floor; `SECRET-ALLOW:` documents false positives |
| D24 service packs | `check-packs.py` — resolves every contract `integrations[]` entry; core pack not active → verdict caps at ready_with_caveats; peripheral → report line only [A.6] |

Field add-on (not a floor check): `assets/inp-beacon.js` (≤2 KB, Event
Timing API) measures real INP when the artifact is deployed; p75 >200ms caps
at ready_with_caveats, never blocks, and is reported separately from the lab
proxy (D15).

Run the floor BEFORE any AI diagnostics. Environment degradation:
`references/environment-degradation.md` — a missing capability is an explicit
status, never a silent pass [A.6].

**Smoke artifact matrix:** pass the contract mode as the 5th argument of
`run-ui-checks.sh`. quick: 1 shot per viewport per route (≤3+1 PNG/route, no
section shots). standard/full: section-wise, VISIBLE sections only
(`isVisible()` filter), cap 12, duplicates deduped. Full quick smoke
(2 routes × 3 viewports) ≤ 90 s.

**Deferred Gate 2 runs:** D17 is `skip(K2B deferred)`; D16 keeps the marker
by design; the base skin is held to the same D3/D9/D11 floor as any
direction — "default" is not an excuse for failing contrast or token
discipline.

### 2. AI diagnostics (visible factors, classified)

Methodology: `references/ai-diagnostics.md`. Section-wise screenshots, fixed
checklist per section, swap-augmentation for comparisons. Every finding is
classified: **objective / heuristic / subjective** × **blocker / major /
minor / polish** [AI.7]. Subjective findings are capped at minor and always
`provisional` [AI.8]. Any visible defect caps its dimension score at ≤3/5
[AI.9]. Objective findings become blockers only with deterministic
corroboration.

### 3. Fix, route, or report

- Trivial mechanical fails (missing alt, oversized image, marker left): fix
  directly, log in the report.
- Design-substance fails (contrast pair, type scale, layout break): route to
  visual-director with the exact failing values.
- Structure fails (unwalkable scenario, missing state): route via orchestrator.
- After fixes, re-run ONLY the failed checks + dependents. Retest history is
  kept: found → fixed → retested [A.8].

### 4. Cycles and verdict

A cycle counts when ≥1 fail was fixed and re-checked. Required cycles:
quick 1, standard 2, full 3 (later cycles are full-floor re-runs catching
regressions; a fully green cycle 1 auto-completes the rest).

Write `artifacts/audit/quality-report.md` from the template; fill
`acceptance.automated_checks` and `status` in the contract. Verdict rules
[CR-03]:
- `ready` — no blocking fail, no blocking `unavailable`, no open provisional
  on blocking topics;
- `ready_with_caveats` — no blocking fail, but: blocking `unavailable`
  exists, OR D15 violated, OR D22 unbaselined/unavailable, OR a core pack
  inactive (D24), OR advisory findings/accepted limitations remain (each
  with rationale + risk owner);
- `not_ready` — any blocking fail (incl. D22 unapproved diff, D23 any
  finding). Delivery stops; the orchestrator loops. `not_ready` is never
  lowered without a fix + retest [A.8] — `validate-pipeline.py` rejects a
  `ready` verdict with an open blocker.

## Restyle re-checks

Token-level restyle → D3, D9, D11 (+D4–D8 if families/scale changed), D12
spot-check at 390/1440, D22 test (diff expected → human approve). Anything
more = full floor.
