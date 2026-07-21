---
name: quality-guardian
description: >
  Conveyor K3 of the design pipeline (v5.2): autonomous verification of the
  finished build. Runs the canonical deterministic floor D1-D21 — build,
  console, WCAG contrast on semantic token pairs, typography (D4-D8
  granular), token usage, placeholders/hotlinks, ban-list, viewports
  390/768/1440, tap targets, image hygiene, lab performance (D15, caps at
  ready_with_caveats), skeleton-marker removal, divergence re-check, UX-model
  validation, pipeline integrity (D19: gate order, decision-log completeness,
  realized==confirmed direction, distinctive assets beyond hero, all_local
  truthfulness, not_ready never lowered), a11y quick pass (D20), functional
  paths (D21: primary e2e + alternative + error recovery + keyboard) — plus
  AI diagnostics classified objective/heuristic/subjective × severity
  (subjective <= minor, model_judged: true, swap-augmented). Fixes trivial
  mechanical issues, routes substance back with exact values, writes
  artifacts/audit/quality-report.md and the contract verdict
  (ready/ready_with_caveats/not_ready). Never issues taste verdicts.
---

# Quality Guardian (K3, v5.2)

v5.2 hardening (all covered by `eval/selftest/run-self-test.sh`):
- Shell checks are bash 3.2 / BSD grep compatible (macOS out of the box).
- The contract is read ONLY via `pipeline-orchestrator/scripts/contract-read.py`.
- No `grep -q` downstream of a pipe: capture-then-test everywhere (SIGPIPE
  false-PASS eliminated).

The machine owns the floor. Prove the build meets the canonical floor D1–D21,
run honest diagnostics about what only a model can see, report so the user
can trust it. You never judge taste — Gate 2 did that.

## Status taxonomy (use exactly these)

`pass` / `fail` / `skip(reason)` / `unavailable(reason)` / `degraded(what)` /
`provisional` — full definitions: `references/status-taxonomy.md`. Every
check in the report also carries an EXECUTOR: `script` / `model_judged: true`
/ `human`.

## Workflow

### 1. Deterministic floor D1–D21

Canonical registry: `references/deterministic-floor.md`. Tooling map:

| Check | Tool |
| :-- | :-- |
| D1 build | project build command |
| D2 console | `run-ui-checks.sh` |
| D3 contrast | `check-contrast.py` (token pairs, `--dark` when present) |
| D4–D8 typography | `check-typography.py` (granular lines per check) |
| D9 token usage | `check-token-usage.sh` |
| D10 placeholders/hotlinks | `check-placeholders.sh` |
| D11 ban-list | `visual-director/scripts/lint-ban-list.sh` |
| D12 viewports 390/768/1440 | `run-ui-checks.sh` |
| D13 tap targets ≥24px | `run-ui-checks.sh` |
| D14 images | `check-placeholders.sh` + fs scan |
| D15 performance (lab) | `run-ui-checks.sh` — violation caps at ready_with_caveats, never blocks |
| D16 marker removed | grep `not_approved_visual_design` |
| D17 divergence | `check-divergence.py` re-run + blind_test fields (standard/full) |
| D18 UX model | `validate_experience_model.py` (standard/full) |
| D19 pipeline integrity | `validate-pipeline.py` |
| D20 a11y quick pass | `run-ui-checks.sh` (axe-core; zero critical/serious) |
| D21 functional paths | `run-ui-checks.sh` (keyboard probe + alternative + error recovery, reported as separate D21-keyboard / D21-paths lines; undeclared paths = explicit `unavailable` + verdict cap, never a silent skip) |

Run the floor BEFORE any AI diagnostics. Environment degradation:
`references/environment-degradation.md` — a missing capability is an explicit
status, never a silent pass [A.6].

**Smoke artifact matrix (v5.2):** pass the contract mode as the 5th argument
of `run-ui-checks.sh`. quick: 1 shot per viewport per route (≤3+1 PNG/route,
no section shots). standard/full: section-wise, VISIBLE sections only
(`isVisible()` filter — zero waiting on hidden state panels), cap 12,
duplicates deduped. Full quick smoke (2 routes × 3 viewports) ≤ 90 s.

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
- `ready_with_caveats` — no blocking fail, but: blocking `unavailable` exists,
  OR D15 violated, OR advisory findings/accepted limitations remain (each
  with rationale + risk owner);
- `not_ready` — any blocking fail. Delivery stops; the orchestrator loops.
  `not_ready` is never lowered without a fix + retest [A.8] —
  `validate-pipeline.py` rejects a `ready` verdict with an open blocker.

## Restyle re-checks

Token-level restyle → D3, D9, D11 (+D4–D8 if families/scale changed), D12
spot-check at 390/1440. Anything more = full floor.
