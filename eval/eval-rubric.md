# Eval rubric — scoring runs of v5.2

Score every prompt from `example-prompts.md` on 12 criteria.
Points: 0 (no), 0.5 (partial), 1 (yes). Pass = ≥10/12 AND no zeros in the
blocking criteria (C1–C4, C11, C12).

## Blocking criteria (the 5.1 core)

**C1. Gates happened and were honest.**
Gate 1 showed the neutral skeleton (marker, gray, real copy) BEFORE any
visual work; Gate 2 showed a blind contact sheet: anonymized variants,
simultaneous presentation, BOTH slice screens per variant, randomization
recorded. 0 = visual work before Gate 1 / named or sequential variants /
"recommended" marker.

**C2. Divergence was real.**
check-divergence.py green AND (manual sample) directions visibly differ in
composition/type voice, not just color; seeds: personas + ≥3 non-overlapping
domains each; boldness points SPREAD; 1–2 bold moves each; Three Dials
(variance/motion/density, v7.0) recorded per direction with no two
directions sharing all three values; standard/full: external blind test
recorded (overlap ≤50%, model_judged, **a different model family than the
builder**, v7.1).
0 = "3 variants = 3 recolors"; overlapping domains; coinciding boldness
points ignored; missing blind test in standard/full; blind test run by the
same model family that built the directions.

**C3. Merge worked with the confirming render.**
Merge follow-up asked after a plain pick; on merge: axes resolved into
final_direction, coherence gate ran (render + AI check + D9/D11/D3), the
CONFIRMING RENDER was shown (interactive) or deferred+offered (autonomous).
0 = merge path skipped, or merged direction scaled without the confirming
render.

**C4. The deterministic floor was run honestly.**
D1–D24 executed; statuses from the taxonomy with executors; D15 caveats not
blocks; unavailable/degraded named with reasons; report verdict == contract
verdict; validate-pipeline.py green. 0 = silent unavailable→pass conversion;
checks claimed without artifacts.

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

**C13. Design review audit ran honestly (v7.0, blocking when K2B ran).**
Before merge/scale, the chosen direction passed the 10-line pass/fail rubric
(`visual-director/references/design-review-audit.md`): `visual.design_review`
is `pass`, each line is backed by an artifact (machine floor lines by script
output, judgment lines marked `model_judged: true`), and any `fail(<lines>)`
led to rework + re-audit, not prose override. 0 = merge started without the
audit, a fail overridden by prose, or a pass declared without evidence [A.11].
Skip (not 0) when K2B never ran in this project.

## Quality criteria

**C5. Taste calibrated by showing, not asking.**
References decomposed to principles, or the style-card test ran; no
"why do you like it?" before the choice; anti-references recorded and honored.

**C6. Slop stopped.**
lint-ban-list green on the FINAL (post-merge) build; no banned first-position
fonts, indigo→purple gradients, glass, bento, blobs, icon-per-label,
marketing-slop copy.

**C7. Skin property holds.**
check-token-usage green; (P09) restyle done as token diff + recompile, zero
manual component edits; dark theme is a semantic layer, not a filter invert;
input-hash reuse — no rebuilt structure on restyle [E.3].

**C8. Autonomy is honest.**
Autonomous gates marked (autonomous_passed / provisional_ai); AI judgments
only visible factors, swap-augmented; every model_judged carries provisional;
subjective findings ≤ minor; the return confirmation offer is the FIRST
message on the user's return.

**C9. The contract is the single source of truth.**
All decisions (mode, pattern, axes, gates, merges, fixes) recorded with
changelog + decision log; conflicts resolved by the documented order; no
silent drift; budgets respected [E.1] (no "one more variant for luck").

**C10. Delivery report is plain-language.**
Final message: what was built / gate decisions / what was verified (n/n) /
what remains — no jargon; statuses translated; ready-family verdicts used
everywhere.

## Benchmark opponent

Blind comparisons in the demand test use the strongest free alternative as
opponent (source: knowledge/ui-ux-pro-max-skill): it emits recommendations
without verification, we run a machine floor — the comparison measures
whether the floor is visible to a blind reviewer.

## Scoring protocol

1. Run the prompt on a clean project.
2. Mechanical part: validate-pipeline.py + all K3 scripts (auto-points for
   C2, C4, C6, C7, C11 — green script = 1, else 0).
3. Manual part: C1, C3, C5, C8, C9, C10 from artifacts (contract, contact
   sheet, decision log, final message) — screenshots as evidence.
4. Result in `eval/results/YYYY-MM-DD-<prompt-id>.md`: score table +
   evidence links + the main defect (if any).
5. Regression = total dropping ≥1.5 points vs the previous run OR any new 0
   in C1–C4/C11/C12 → stop the change from shipping.

## v7.0 floor extension (D25–D38)

The deterministic floor extends D1–D24 → D1–D38 with tiered enforcement.
Tier 1 failures block the verdict; Tier 2 produce warnings in the quality
report and never block. Until a check is wired (phase 3), its status is
`skip(spec)` — explicit, never a silent pass [A.6].

| Check | Rule | Tier | Source |
| :-- | :-- | :-- | :-- |
| D25 contrast WCAG | text 4.5:1, large 3:1, non-text 3:1; no rounding | 1 | knowledge/wcag-22-aa-rules |
| D26 target size | ≥24×24 CSS px (AA), 44–48px practice | 1 | knowledge/wcag-22-aa-rules |
| D27 focus visible | :focus-visible styled, never removed; indicator ≥3:1 | 1 | knowledge/wcag-22-aa-rules |
| D28 semantic HTML | correct tags, continuous H1→H3 | 1 | knowledge/wcag-22-aa-rules |
| D29 reduced-motion | quiet version without movement | 1 | knowledge/motion-budgets |
| D30 AI-look markers | no ban-list defaults (indigo-600 hero, slate-900, rounded-2xl-everything) | 1 | knowledge/ai-look-catalog |
| D31 squint test | hierarchy readable under blur | 2 | knowledge/text-hierarchy-tiers |
| D32 5-second test | a new viewer understands what it is and what to do | 2 | knowledge/parallel-design |
| D33 grayscale test | hierarchy works without color | 2 | knowledge/text-hierarchy-tiers |
| D34 keyboard test | the whole scenario without a mouse | 2 | knowledge/wcag-22-aa-rules |
| D35 jank | 60fps, transform/opacity only, jank < 1% | 2 | knowledge/motion-budgets |
| D36 copy audit | no corporate slop; ≥1 concrete claim with a number | 2 | knowledge/microcopy-principles |
| D37 token architecture | primitive → semantic → component references only | 1 | knowledge/token-architecture-3layer |
| D38 seven states | idle/loading/skeleton/populated/empty/error/success per async block | 1 | knowledge/async-seven-states |
