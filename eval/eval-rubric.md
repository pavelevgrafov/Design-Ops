# Eval rubric — scoring runs of v5.1

Score every prompt from `example-prompts.md` on 11 criteria.
Points: 0 (no), 0.5 (partial), 1 (yes). Pass = ≥9/11 AND no zeros in the
blocking criteria (C1–C4, C11).

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
domains each; boldness points SPREAD; 1–2 bold moves each; standard/full:
external blind test recorded (overlap ≤50%, model_judged).
0 = "3 variants = 3 recolors"; overlapping domains; coinciding boldness
points ignored; missing blind test in standard/full.

**C3. Merge worked with the confirming render.**
Merge follow-up asked after a plain pick; on merge: axes resolved into
final_direction, coherence gate ran (render + AI check + D9/D11/D3), the
CONFIRMING RENDER was shown (interactive) or deferred+offered (autonomous).
0 = merge path skipped, or merged direction scaled without the confirming
render.

**C4. The deterministic floor was run honestly.**
D1–D21 executed; statuses from the taxonomy with executors; D15 caveats not
blocks; unavailable/degraded named with reasons; report verdict == contract
verdict; validate-pipeline.py green. 0 = silent unavailable→pass conversion;
checks claimed without artifacts.

**C11. Decision log is complete.**
artifacts/decision-log.md exists with ALL mandatory sections (Classification,
Clarification, Gate 1, Taste calibration, Direction seeds, Gate 2, Verdict)
+ conditional ones when applicable (Regenerations with hypotheses; Accepted
limitations with risk owners). Script-verified (AC-25). 0 = missing log or
missing mandatory sections.

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

## Scoring protocol

1. Run the prompt on a clean project.
2. Mechanical part: validate-pipeline.py + all K3 scripts (auto-points for
   C2, C4, C6, C7, C11 — green script = 1, else 0).
3. Manual part: C1, C3, C5, C8, C9, C10 from artifacts (contract, contact
   sheet, decision log, final message) — screenshots as evidence.
4. Result in `eval/results/YYYY-MM-DD-<prompt-id>.md`: score table +
   evidence links + the main defect (if any).
5. Regression = total dropping ≥1.5 points vs the previous run OR any new 0
   in C1–C4/C11 → stop the change from shipping.
