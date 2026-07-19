# Gate message templates (ready-to-use, plain language)

Use these verbatim, filling {placeholders}. Never add authorship hints,
recommendations, or "why" questions before a choice. Every template states
how long the review takes.

## 1. Gate 1 — presentation (interactive)

```
The product skeleton is ready for a structure check (~2 min).

Product: {product.name} — {product.user_outcome}
Audience: {product.audience}
Primary scenario: {experience.primary_job}
Screens: {experience.key_screens}
Deliberately deferred: {P3/absent list}

Is the structure right? Yes / what to change
(Visual style is not evaluated here — the skeleton is intentionally neutral.)
```

## 2. Gate 1 — autonomous notification

```
Gate 1 passed autonomously (autonomous_passed): I walked the primary scenario
and checked the skeleton against the brief — objective points only, no taste
decisions involved. Moving to the visual conveyor.
Want to review the structure anyway? It takes ~2 minutes.
```

## 3. Gate 2 — contact sheet presentation (interactive)

```
The contact sheet is ready (~3 min). {N} anonymized visual directions on a
slice of your product — same screens, same real text. Each variant shows the
main screen and a dense working screen.

[Variant 1] [Variant 2] [Variant 3]

Which one is best?
— You can pick one as a whole.
— You can ask for a merge: "take the typography from 1, the color from 2".
— You can say "none of these" — then one regeneration round, with a note on
  what repels you (color / density / mood).

(I'll only ask about reasons afterwards — and only if you want to share.)
```

## 4. Gate 2 — provisional_ai return offer (autonomous)

```
The pipeline ran autonomously. The direction was chosen by an AI pre-filter
(provisional_ai) and is NOT confirmed by you.

The contact sheet is ready — confirming takes ~3 minutes:
[Variant 1] [Variant 2] [Variant 3] (AI's pick: Variant {N})

Confirm the AI's choice, pick a different variant, or request a merge?
```

## 5. Merge — confirming render (CR-06)

```
Merged direction assembled: {axis → source, e.g. "typography ← Variant 2,
color ← Variant 3"}.
Coherence check passed — no internal contradictions between the parts.
Here is the slice render with this merged direction — confirm or adjust?
```

## 6. Asset mini-gate (CR-08)

```
Candidates for the {slot id} visual ({n} options, generated to the chosen
direction's recipe). One click picks:
[1] [2] [3] [4]
```
(Autonomous: no message — the AI pick is marked `provisional` and included in
the return confirmation.)

## 7. Post-scale failure (CR-07)

```
The chosen direction broke at full scale: {what breaks, where}.
Working hypothesis: {hypothesis}. I will adjust {axis} and re-apply —
one correction round is available. If it breaks again, I'll stop and lay out
the options instead of guessing.
```

## 8. Final verdict (K3)

```
Verdict: {ready | ready_with_caveats | not_ready}
Checks passed: {N of M} (D1–D21, see artifacts/audit/quality-report.md).

{if not_ready: list of open blockers and required fixes}
{if ready_with_caveats: list of accepted limitations + who accepted each risk}
{if anything unavailable/degraded: what couldn't be checked here and how to
 check it manually}
```
