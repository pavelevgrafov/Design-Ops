# Eval rubric — scoring runs of v5.2

Score every prompt from `example-prompts.md` on 12 criteria.
Points: 0 (no), 0.5 (partial), 1 (yes). Pass = ≥10/12 AND no zeros in the
blocking criteria (C1–C4, C11, C12).

## Blocking criteria (the 5.1 core)

**C1. Gates passed in order.** Gate 1 (structure) BEFORE any visual work
[A.1]; Gate 2 (blind visual choice) BEFORE scaling [A.2]. Evidence:
contract `gates.*` + `changelog` timestamps; `validate-pipeline.py` green.
0 = any visual work before Gate 1, any scaling before Gate 2.

**C2. Skeleton is truly neutral.** `check-skeleton.sh` green: marker on all
screens, zero non-gray colors, no visual properties, real copy,
data-priority on all key blocks. 0 = skeleton shipped with styling or
placeholder copy.

**C3. Contact sheet is blind and complete.** Randomized order recorded in
`visual.gate2_randomization`; ALL variants shown simultaneously; TWO-screen
slice per variant (main + contrast screen, +CJK variant when the
localization trigger fired). 0 = authorship hints, sequential showing, or a
missing screen.

**C4. Deterministic floor passed.** D1–D21 run via scripts; every
`skip`/`unavailable` carries a reason; verdict matches the report;
`not_ready` never lowered without fix+retest (D19 green). 0 = any blocking
check silently skipped or a verdict contradicting the evidence.

## Quality criteria

**C5. Directions are constructed-divergent.** Persona + ≥3 non-overlapping
domains per direction; boldness spread across the band; ≥3 differing axes
per pair incl. composition or type_voice; `check-divergence.py` clean;
external blind test ≤50% overlap (standard/full). 0 = recolors of one
layout.

**C6. Merge has a coherence gate.** On `merged(...)`: axes_resolution filled,
contradiction check ran, CONFIRMING RENDER shown (interactive) or deferred
(autonomous) BEFORE scaling. 0 = merge applied silently.

**C7. Token discipline (skin property).** DTCG tokens compiled via
compile-tokens.py; restyle = token edit + recompile, ZERO manual component
edits (D9 green). 0 = raw hex/px/fonts in components.

**C8. Assets pass the mini-gate.** 3–4 candidates per raster slot with
versioned prompts; human pick or provisional AI pick; favicon + OG
auto-generated; AI images carry disclosure; all local, alt, ≤300 KB (D10/
D14 green). 0 = hotlinks or placeholder services.

**C9. Ban-list enforced.** `lint-ban-list.sh` green on specs AND the final
build (D11); exceptions have written `ALLOW:` justifications. 0 = banned
defaults shipped.

**C10. Economics respected.** Question budget (≤5/≤3, none about taste in
K1); one regeneration round max with a failure hypothesis; post-scale
budget ≤1; QA cycles per mode. 0 = interrogation-style K1 or autonomous
looping.

**C11. Decision log is complete.**
artifacts/decision-log.md exists with ALL mandatory sections (Classification,
Clarification, Gate 1, Taste calibration, Direction seeds, Gate 2, Verdict)
+ conditional ones when applicable (Regenerations with hypotheses; Accepted
limitations with risk owners). Script-verified (AC-25). 0 = missing log or
missing mandatory sections.

**C12. Works out of the box (v5.2, blocking).**
Fresh copy → install per INSTALL.md → quick-run completes WITHOUT a single
edit to the package (no patched scripts, no swapped rem-units workarounds,
no custom copies of validators). `bash eval/selftest/run-self-test.sh` is
green on the target platform; smoke logs show zero 30-second stalls and a
quick run ≤ 90 s; every PASS in the report is backed by a measured/checked
evidence (spot-check D5, D15, D21, placeholders, screens). 0 = any package
edit needed, any unmeasured pass, or self-test red/skipped silently.

## How to score

1. Run a prompt end-to-end; collect `artifacts/`.
2. Run the scripted gates: `validate-pipeline.py`, `check-skeleton.sh`,
   `check-typography.py`, `check-token-usage.sh`, `check-placeholders.sh`,
   `lint-ban-list.sh`, `run-ui-checks.sh`.
3. Score C1–C12 from evidence (scripts first, artifacts second, prose last).
4. Record: prompt, mode, scores, total, blocking zeros, verdict, notes.
5. Regression = total dropping ≥1.5 points vs the previous run OR any new 0
   in C1–C4/C11/C12 → stop the change from shipping.
