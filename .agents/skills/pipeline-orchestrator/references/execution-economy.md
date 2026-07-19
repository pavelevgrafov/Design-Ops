# Execution economy [E.1]–[E.5]

Internal behavior rules for the orchestrator. Not an artifact, not a report —
how the executor spends effort. Budgets are set BEFORE a stage starts and
recorded in the decision log when exceeded.

## [E.1] Countable budgets per stage

Set before the stage, in countable units:

| Budget | Default |
| :-- | :-- |
| Tool calls per stage | K1 ≤40, K2-phase1 ≤60, K2-phase2 ≤50, K3 ≤40 (scale with mode) |
| Directions generated | exactly per mode (2 quick / 3 standard / 3+1 full) — never "one more for luck" |
| Candidates per raster asset slot | 3–4, never more |
| Gate 2 regenerations | 1 (all modes) |
| Post-scale failure returns | 1 (all modes, separate from regeneration) |
| Session minutes per gate wait | interactive: unlimited (human time); autonomous: 0 (proceed provisional) |

Exceeding a stage budget = STOP and report to the user with what was achieved
and what remains — never continue silently on momentum.

## [E.2] Early stop

Passing a gate or a check ENDS the stage's work. No "polish for polish's
sake": a skeleton that passes `check-skeleton.sh` is done; a direction set
that passes divergence + ban-list is done; a QA cycle with zero fails
completes the remaining cycles as pure re-runs (no new scope).

## [E.3] Reuse by input hash

Artifacts are not regenerated if their inputs did not change:

- contract sections → skeleton (hash of product+experience+content_model);
- calibration + seeds → directions;
- final_direction → tokens;
- tokens → compiled CSS.

Store input hashes next to artifacts (a comment line or manifest field). On a
change request, recompute only downstream of the changed input. A restyle
never rebuilds the structure; a structure delta never rebuilds directions.

## [E.4] Budgets never downgrade blocking checks

D1–D14 and D16–D21 always run where the environment permits; Gate 2 in
interactive mode is never replaced by an AI filter "to save time". Savings
come from reuse and early stop, never from skipping verification.

## [E.5] Quick-mode hard ceilings

2 directions, 1 comparison pair, 1 QA cycle, ≤1 distinctive asset. The ceiling
is enforced by `validate-pipeline.py` (AC-23) — the answer to "just one more
variant in quick" is no; offer a mode upgrade instead.
