# Design Review Audit — post-contact-sheet protocol (v7.0)

Runs AFTER the Gate 2 choice and BEFORE merge/scale (Step 4). Not a taste
verdict — a pass/fail evidence audit of the chosen direction (and later of
the merged result), scored against the rubric below, never 0–10
(source: knowledge/crap-framework, knowledge/nielsen-heuristics-checklist,
knowledge/text-hierarchy-tiers, knowledge/ai-look-catalog,
knowledge/parallel-design). Every model judgment is `model_judged: true`
and provisional [A.5].

## The cycle (per chosen/merged direction)

critique (structure) → audit (technical defects) → polish (micro) →
normalize (token discipline). A failing stage returns the direction to the
previous step — polishing a broken structure is banned.

## Rubric (pass/fail per line, artifact required)

**Critique — structure:**
1. Hierarchy: the squint story holds — one primary accent per view [A.14],
   three text tiers visibly separated (100 / 70–80 / 40–50%).
2. Flow: the primary job is reachable in the fewest unambiguous clicks;
   CTA sits on the scanning trajectory (F/Z).
3. Affordance: interactive looks interactive, non-interactive does not
   [A.13]; every action has visible feedback < 400 ms.

**Audit — technical:**
4. Machine floor on the slice: D3 (contrast, both themes when dark ships),
   D9 (token usage), D11 + D.30 (ban-list + AI-look, tier 1), D.25
   (extended pairs), D.27/D.28/D.29 on the slice CSS/markup.
5. States: async blocks on the slice show ≥ loading + error + empty
   (7-state spec follows at scale) [A.12, D.38].
6. Copy: no corporate slop [A.22, D.36]; ≥1 concrete claim with a number.

**Polish — micro:**
7. Spacing: 8pt ladder holds (64–96 / 32–48 / 16–24 / 8–16 / 4–8),
   padding ≤ margin; alignment to one dominant axis per block.
8. Type: modular scale only, measure ≤ 75ch, line-height in band,
   ≤2 families.

**Normalize — system:**
9. Nothing outside tokens: no raw hex/px/font outside the token files;
   component layer references semantic only [A.21, D.37].
10. Restyle proof: a one-token edit + recompile changes the slice without
    manual component edits.

## Verdict

- All 10 pass → `design_review: pass`, proceed to merge/scale.
- Any fail → `design_review: fail(<lines>)` + per-line diagnosis with exact
  values; return to the named stage. A fail is never overridden by prose —
  fix + re-audit [A.8].
- The audit report appends to `artifacts/audit/quality-report.md` (K2B
  section) and the decision log (Gate 2 retrospective).
