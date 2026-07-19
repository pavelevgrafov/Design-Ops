# Eval prompts — regression corpus for pipeline v5.1

Run on every change to skills/scripts. Score each run with `eval-rubric.md`.
Prompts deliberately vary mode, category, and taste signals; expected modes
and risk points are noted.

## Core conveyor coverage

1. **P01 — landing, quick, no references.**
   "Make a landing page for a habit-tracker app. Quickly, no questions."
   Expect: quick (explicit word), autonomous gates with provisional_ai,
   return confirmation offer, 2 directions, quick ceiling holds.

2. **P02 — event site, standard.**
   "A site for a typography conference: program, speakers, tickets. I like
   Swiss modernism and old Bauhaus posters."
   Expect: event-first pattern, calibration from 2 references (decomposed
   principles, ≤1 per direction), 3 directions with boldness spread, clean
   ban-list.

3. **P03 — SaaS dashboard, full, multi-role.**
   "Prototype a logistics analytics dashboard: manager + executive roles,
   loading/empty/error states. This is a critical screen — do it thoroughly."
   Expect: full (multi-role + criticality), task-first, extended scenarios,
   3 QA cycles, all required_states implemented, D21 declared + walked.

4. **P04 — e-commerce product page, standard, "your call".**
   "A product page for a handmade ceramics shop. Style — you decide, I'll
   look later."
   Expect: object-first, calibration skipped_autonomous, gate2
   provisional_ai + mandatory 3-minute confirmation offer.

5. **P05 — pricing page, quick→standard upgrade.**
   "Build a pricing page, keep it simple. Oh, and it needs login and
   payment."
   Expect: comparison-first, quick→standard upgrade with a recorded reason
   (auth + payment).

## Stress tests (mechanics)

6. **P06 — gate blindness provocation.**
   Any request + at Gate 2: "Why is Variant 2 first? Is it the best one?"
   Expect: order randomized and recorded; no authorship hints; variants were
   shown simultaneously; the answer reveals nothing about positions.

7. **P07 — merge by default + confirming render (CR-06).**
   At Gate 2: "I'll take Variant 2, but the colors of Variant 3 are nicer."
   Expect: gate2_result=merged(base+B.color); coherence gate ran; CONFIRMING
   RENDER SHOWN before scaling; axes resolution + confirm_render recorded;
   contrast re-checked on the merged result.

8. **P08 — slop provocation.**
   "Make a modern SaaS landing like every startup: gradients, glass cards,
   an icon for every feature."
   Expect: the pipeline does NOT obey blindly — ban-list records the request
   as anti-reference; directions avoid slop; the user gets a plain-language
   explanation (plus a justified deliberate variant if they insist).

9. **P09 — restyle (skin property).**
   After P02 completes: "Make a dark version and change the accent to
   terracotta."
   Expect: semantic token edit + compile-tokens only, ZERO manual component
   edits; D3/D9/D11 re-run; no gates; no structure rebuild [E.3].

10. **P10 — Gate 2 regeneration.**
    At Gate 2: "None of these, all boring, I want bolder."
    Expect: exactly ONE regeneration round with a recorded failure hypothesis;
    new seeds (boldness up within the band); second blind showing; escalation
    (two nearest variants + trade-off) on a second miss, no infinite loop.

11. **P11 — environment degradation.**
    Run without playwright / without perf APIs.
    Expect: honest `unavailable` statuses with manual alternatives; verdict
    capped at ready_with_caveats; no silent conversions; degradation path
    logged BEFORE the stages ran.

12. **P12 — source conflict.**
    Brief says "minimalism is key". At Gate 2 the user picks the densest
    variant.
    Expect: the user's latest explicit instruction wins; the choice is
    recorded in changelog + decision log, superseding the earlier field.

## New mechanics (5.1)

13. **P13 — neutralization route (CR-01).**
    "Here's my prototype (link/files) — make it look good."
    Expect: neutralize route, NOT a rebuild; styling stripped to neutral,
    marker + data-priority added; check-skeleton --neutralize-audit clean;
    working scenarios preserved; neutralization logged in the decision log.

14. **P14 — localization trigger (CR-05).**
    "A landing for a tea shop, in English and Chinese."
    Expect: localization_risk=true + reason; content variants in the
    skeleton; CJK slice variant in the contact sheet; D5 measured on both
    language variants.

15. **P15 — post-scale failure (CR-07).**
    Simulated: the chosen direction breaks at full scale (unforeseen density).
    Expect: ONE merge return with a new hypothesis in post_scale.hypothesis_log;
    a second break → documented not_ready, no autonomous looping.

16. **P16 — asset mini-gate + disclosure (CR-08).**
    After Gate 2 on any prompt with a hero slot.
    Expect: 3–4 candidates per raster slot, one-click pick (or provisional);
    favicon + OG auto-generated; AI images carry disclosure: true + a visible
    mechanism; distinctive assets appear beyond the hero (D19).
