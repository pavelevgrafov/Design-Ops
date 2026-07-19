# Canonical deterministic floor D1–D21 (v5.1)

This registry REPLACES both v5.0 variants' D1–D19 (they conflicted). The
mapping table at the bottom is normative for reading older reports.

Blocking: D1–D14 and D16–D21 block `ready` (D16–D19 block their stage's
handoff, hence the final verdict). D15 (lab performance) caps at
`ready_with_caveats`, never blocks fully — CLS prevention stays blocking
indirectly via D14 (declared image dimensions).

## D1 — Build / typecheck. Blocking. Script.
Project build exits 0. Fail: any build error, TS error, unresolvable import.

## D2 — Console errors. Blocking. Script.
Zero `console.error`, zero uncaught exceptions, zero failed requests on every
key screen × 3 viewports. Warnings logged, not blocking.

## D3 — Contrast (WCAG). Blocking. Script.
`check-contrast.py` on compiled tokens: ink/canvas, inkMuted/canvas,
actionPrimaryText/actionPrimary, inkOnDark/surfaceDark (+ dark mirrors).
4.5:1 normal text, 3:1 large (≥24px / ≥18.66px bold) and non-text UI.

## D4 — Base text size. Blocking. Script.
Body/base text ≥16px at all viewports (`check-typography.py` line D4).

## D5 — Measure. Blocking. Script.
45–75ch for body columns (`check-typography.py` line D5). On
`localization_risk` — verified on BOTH language variants (e.g. Latin and
CJK/long-content) [D5.1].

## D6 — Line-height. Blocking. Script.
1.4–1.7 for body text (`check-typography.py` line D6).

## D7 — Type scale. Blocking. Script.
Modular ratio 1.2–1.333 across the emitted scale; sizes come from the scale
(`check-typography.py` line D7).

## D8 — Font usage. Blocking. Script.
≤2 proportional families (+1 mono); every stack ends in a generic fallback;
`font-display: swap` on every @font-face; webfonts actually load
(`check-typography.py` line D8 + network probe).

## D9 — Token usage. Blocking. Script.
`check-token-usage.sh`: no raw colors/fonts/out-of-scale spacing in
components (token files excepted). Fail = a raw value in a component.

## D10 — Placeholders & hotlinks. Blocking. Script.
`check-placeholders.sh`: no lorem/TODO-copy; no external image hosts or
placeholder services; no external CDN assets unless whitelisted.

## D11 — Ban-list. Blocking. Script.
`lint-ban-list.sh` on the FINAL build (post-merge!): first-position fonts,
indigo→purple gradients, glassmorphism, bento hero+3, blobs, icon-per-label,
marketing slop. Justified exceptions require `ALLOW:` lines in the final
direction doc.

## D12 — Viewports. Blocking. Script.
No horizontal overflow, no broken layout at 390/768/1440 (`run-ui-checks.sh`
probe + screenshots).

## D13 — Tap targets. Blocking. Script.
Interactive elements ≥24×24 CSS px at 390px (WCAG 2.2 AA); target 44px on
mobile-primary products. Exception: inline links within body text.

## D14 — Images. Blocking. Script + fs scan.
All sources local, real alt (decorative: alt=""), ≤300 KB, declared crop,
srcset for heroes, width/height or aspect-ratio declared. Favicon and OG
exist (CR-08).

## D15 — Performance (lab). Caps at ready_with_caveats. Script.
LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 on the main screen (`run-ui-checks.sh`).
Violation → cap, with the values in the report. `unavailable` when the
measurement environment is missing — stated, with a manual alternative.

## D16 — Skeleton marker. Blocking (stage: scaling). Script.
Zero `not_approved_visual_design` occurrences in the shipped build. Presence
= scaling happened before Gate 2 or cleanup was skipped (also a D19 issue).

## D17 — Divergence. Blocking (stage: K2 before Gate 2). Script (+model_judged).
`check-divergence.py` clean; in standard/full the external blind test is
recorded (`directions[].blind_test`, overlap ≤50%).

## D18 — UX model. Blocking (stage: K1, standard/full). Script.
`validate_experience_model.py` clean: pattern, screens, p1 per screen, states,
scenario coverage, localization variants when triggered.

## D19 — Pipeline integrity. Blocking (stage: K3). Script.
`validate-pipeline.py`: gate order via changelog (A.1/A.2 — retro-fitted
compliance is detectable); mode ceiling (AC-23); verdict ↔ report; every
`model_judged` claim paired with `provisional`; autonomous Gate 2 honesty;
**decision-log mandatory sections present (AC-25)**; **realized direction ==
confirmed direction** (final_direction non-empty, gate2_result ids exist);
**distinctive assets present beyond the hero**; **all_local truthful** (every
slot has an existing local file); **not_ready never lowered without fix+retest**.

## D20 — Accessibility quick pass. Blocking (critical/serious). Script.
axe-core (or equivalent) on key screens: zero critical/serious violations.
Moderate/minor → residual risks. Tool missing = `unavailable` (caps verdict),
never `skip`.

## D21 — Functional paths. Blocking. Script.
Per `acceptance.functional_paths`: primary scenario end-to-end + ONE
alternative path + ONE error recovery + keyboard navigation of the key path
(Tab order sane, focus visible, key controls reachable). Paths are declared
before the K3 run; keyboard check may be `model_judged` only when a DOM probe
is impossible — with the mark.

## Environment honesty

If a check cannot run: `unavailable` + reason + nearest manual alternative;
blocking-check `unavailable` ⇒ verdict caps at `ready_with_caveats` [A.6].
Never silently convert unavailable to pass.

## Mapping from v5.0 variants (normative)

| 5.1 | v5.0 (executable package) | v5.0 (SOP "Visual Gate") |
| :-- | :-- | :-- |
| D1–D3 | D1–D3 | Д1–Д3 |
| D4–D8 | D4 (merged), D18 | Д4–Д8 |
| D9–D14 | D5, D6, D7, D8, D9, D10 | Д9–Д14 |
| D15 | D11, D12, D13 | Д15 |
| D16 | D17 | Д16 |
| D17 | (lived in visual-director, unnumbered) | Д17 |
| D18 | (K1 validation, unnumbered) | Д18 |
| D19 | D19 | Д19 |
| D20 | D16 | — (new for the SOP variant) |
| D21 | D14 + D15 (merged with SOP functional stage) | — (formalized from К3.4) |
