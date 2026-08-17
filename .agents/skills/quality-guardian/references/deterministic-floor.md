# Canonical deterministic floor D1–D24 (v6.0)

This registry REPLACES both v5.0 variants' D1–D19 (they conflicted). The
mapping table at the bottom is normative for reading older reports. v6.0
adds D22 (visual regression), D23 (secrets), D24 (service packs) to the
v5.2 floor D1–D21.

Blocking: D1–D14 and D16–D21 block `ready` (D16–D19 block their stage's
handoff, hence the final verdict); D22 blocks on any UNAPPROVED diff; D23
blocks on any finding. D15 (lab performance) caps at `ready_with_caveats`,
never blocks fully — CLS prevention stays blocking indirectly via D14
(declared image dimensions). D24 caps at `ready_with_caveats` when a CORE
pack is unavailable; a peripheral pack is a report line. The INP field
beacon (companion to D15) caps, never blocks.

## D1 — Build / typecheck. Blocking. Script.
Project build exits 0. Fail: any build error, TS error, unresolvable import.

## D2 — Console errors. Blocking. Script.
Zero `console.error`, zero uncaught exceptions, zero failed requests on every
key screen × 3 viewports. Warnings logged, not blocking.

## D3 — Contrast (WCAG). Blocking. Script.
`check-contrast.py` on compiled tokens: ink/canvas, inkMuted/canvas,
actionPrimaryText/actionPrimary, inkOnDark/surfaceDark (+ dark mirrors).
4.5:1 normal text, 3:1 large (≥24px / ≥18.66px bold) and non-text UI.

v7.2 adds the three text tiers the skins had declared in
`$meta.contrastPairs` since v7.0 but this gate never measured: `textPrimary`
and `textSecondary` on canvas at 4.5:1, and **`textTertiary` on canvasRaised
at 3:1** — the tertiary tier was ruled UI chrome, not normal text (owner:
Pavel, 2026-08-06). It measures 3.39:1 light / 3.17:1 dark, so it clears the
chrome floor and would have failed the text floor; the gap between what the
skin declared and what the checker measured had been hiding that for two
versions.

`--tokens <tokens.json>` reports any pair a skin declares that this gate does
not measure, and the self-test fails when that report is non-empty: two copies
of the same geometry drift, and an undeclared drift is a defect [A.10]. A new
pair must be given a floor deliberately — inventing a threshold that makes a
failure disappear would be worse than the drift.

## D4 — Base text size. Blocking. Script.
Body/base text ≥16px at all viewports (`check-typography.py` line D4).

## D5 — Measure. Blocking. Script.
45–75ch for body columns (`check-typography.py` line D5). Evidence (v5.2):
the `--measure-*` token is primary; a raw `max-width: Nch` counts ONLY on
text selectors (`body|p|prose|article|li`, same set as D4/D6); heading ch is
display type — ignored with a note, never flagged. On
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
LCP ≤2.5s, CLS ≤0.1, INP-proxy ≤200ms on the main screen
(`run-ui-checks.sh`). The INP-proxy (v5.2) is a LAB measurement:
PerformanceObserver event timing (durationThreshold 16) + real trusted
input on up to 5 visible key controls, metric = max event duration; it is
labeled "lab, not field-INP" in the report. If event timing is unsupported
or no controls are visible, the report says so — an interactivity PASS
without a measured value is forbidden. Violation → cap, with the values in
the report. `unavailable` when the measurement environment is missing —
stated, with a manual alternative.

## D16 — Skeleton marker. Blocking (stage: scaling). Script.
Zero `not_approved_visual_design` occurrences in the shipped build. Presence
= scaling happened before Gate 2 or cleanup was skipped (also a D19 issue).
v6.0: while Gate 2 is deferred the marker is KEPT BY DESIGN (the base skin
is "presentable", not approved design) — the check then verifies the marker
is present and visible, and flips to "removed" only after K2B scales.

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
v6.0 adds: closed-taxonomy enums [A.11] (artifact_profile, gates.mode,
gates.gate2 incl. `deferred`, pack class, starter route); delegated-gate
values restricted to `provisional_ai`/`autonomous_passed`; Gate 3 legality
(prod confirmation requires `deploy.prod.rollback_tested: true`); deferred-G2
A.2 exemption (scaling over the base skin is legal when
`status.base_skin_applied: true`); decision-log Gate-2 sections required
only when K2B ran.

### D19 companion — [A.26] "nothing silently". Blocking. Script.
`tools/dops_announce.py --check`, run as part of the floor. Two conditions:
`interaction_mode: autonomous` requires `meta.autonomous_granted_by` (the
owner's explicit word for THIS run — being unresponsive is not a grant), and
every machine-made gate decision (`autonomous_passed`, `provisional_ai`)
requires an announcement recorded at the moment it was made, carrying a
rollback command. A decision the owner learns about from the closing report
is a violation even when the decision itself was legal. Origin: the
kruto-landing run, where the pipeline broke no rule and the owner still lost
control of it.

## D20 — Accessibility quick pass. Blocking (critical/serious). Script.
axe-core (or equivalent) on key screens: zero critical/serious violations.
Moderate/minor → residual risks. Tool missing = `unavailable` (caps verdict),
never `skip`.

## D21 — Functional paths. Blocking. Script.
Per `acceptance.functional_paths`: primary scenario end-to-end + ONE
alternative path + ONE error recovery + keyboard navigation of the key path
(Tab order sane, focus visible, key controls reachable). Paths are declared
before the K3 run; keyboard check may be `model_judged` only when a DOM probe
is impossible — with the mark. Honesty rules (v5.2): the report splits
**D21-keyboard** and **D21-paths**; `paths_json` missing or paths undeclared
= explicit `unavailable D21-paths` + verdict cap at `ready_with_caveats`
(never a silent skip, never a pass line); a D21-paths pass requires BOTH
declared paths (`alternative`, `error_recovery`) actually walked.

## D22 — Visual regression. Blocking (unapproved diff). Script + human approve.
`visual-regression.sh reference|test|approve`: baseline shots are recorded
on starter production (factory) and re-taken after scaling; `test` compares
the current build byte-wise against the baseline. Any unapproved diff
BLOCKS the verdict. `approve` accepts the current shots as the new baseline
— a HUMAN decision, recorded in the decision log by the orchestrator. No
playwright → explicit `unavailable` + verdict cap, never a silent skip.
Restyle runs expect a diff → the human approve IS the restyle acceptance.

## D23 — Secrets scan. Blocking. Script.
`check-secrets.py` over the project tree: known credential patterns (AWS,
GitHub, Google, Slack, Stripe, private-key blocks) + high-entropy
assignments. Any finding is a blocking FAIL — secrets live in env only.
Runs at every floor and is a Gate 3 precondition (before any deploy).
Documented false positives carry `SECRET-ALLOW:` on the same line.

## D24 — Service packs. Core caps, peripheral reports. Script.
`check-packs.py` resolves every contract `integrations[]` entry through
`pack-resolve.py` (env check → TTL cache → acceptance test). A CORE pack
not `active` → the dependent stage is `unavailable` and the verdict caps at
`ready_with_caveats` [A.6]; a peripheral pack → a plain report line, no cap.
The pack block is printed as one report line per pack (status, class,
reason).

## INP field beacon (companion, not a floor check)
`assets/inp-beacon.js` (≤2 KB, Event Timing API) reports real field INP
(p75 of event durations) from preview/prod deploys. p75 >200ms caps at
`ready_with_caveats`, never blocks; reported as a SEPARATE line from the
D15 lab proxy.

## Environment honesty

If a check cannot run: `unavailable` + reason + nearest manual alternative;
blocking-check `unavailable` ⇒ verdict caps at `ready_with_caveats` [A.6].
Never silently convert unavailable to pass.

## Mapping from v5.0 variants (normative)

| 5.1–6.0 | v5.0 (executable package) | v5.0 (SOP "Visual Gate") |
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
| D22 | — (new in v6.0) | — (new in v6.0) |
| D23 | — (new in v6.0) | — (new in v6.0) |
| D24 | — (new in v6.0) | — (new in v6.0) |

## v7.0 extension (D.25–D.41, tiered)

Tier 1 failures block the verdict; Tier 2 are warnings in the quality
report and never block. Browser-dependent tests report explicit
`unavailable` without playwright [A.6].

| Check | Rule | Tier | Tool |
| :-- | :-- | :-- | :-- |
| D.25 extended contrast | text tiers 4.5/4.5/3.0, status hues 4.5, focus ring 3.0, component button — both themes | 1 | `packs/contrast-checker` (D3 core pairs stay in `check-contrast.py`) |
| D.26 target size | ≥24×24 CSS px (SC 2.5.8); 44–48px practice | 1 | covered by D13 (`run-ui-checks.sh`) — same rule, kept as one line |
| D.27 focus visible | no naked `outline: none`; `:focus-visible` styled | 1 | `scripts/check-focus-visible.py` |
| D.28 semantic HTML | one h1, continuous hierarchy, `<main>`, no interactive divs | 1 | `scripts/check-semantic-html.py` |
| D.29 reduced-motion | motion ⇒ `prefers-reduced-motion` quiet version | 1 | `scripts/check-reduced-motion.py` |
| D.30 AI-look markers | tier-1 catalog (indigo-600, slate-900, indigo→purple) | 1 | `packs/ai-look-detector` (+ D11 ban-list) |
| D.31 squint test | hierarchy readable under blur | 2 | model_judged on the D22 render; `unavailable` without it |
| D.32 5-second test | new viewer gets what-it-is + what-to-do | 2 | model_judged / human |
| D.33 grayscale test | hierarchy works without color | 2 | model_judged on the D22 render |
| D.34 keyboard test | whole scenario without a mouse | 2 | D21-keyboard line + manual probe |
| D.35 jank-safe motion | transform/opacity only, no linear easing | 2 | `scripts/check-motion-properties.py` |
| D.36 copy audit | no corporate slop (EN+RU list); a banned word *displayed as data* is exempt when the element declares `data-dops-exhibit` (stop-list tab, quoted example) — the removal is printed, never silent | 2 | `packs/copy-linter` |
| D.37 token architecture | primitive → semantic → component refs only | 1 | `packs/token-validator` (+ compile-time A.21) |
| D.38 seven states | idle/loading/skeleton/populated/empty/error/success per async module | 1 | `scripts/check-seven-states.py` + `packs/state-generator` |
| D.39 semantic layer | an artefact must not use a token an alias is declared over; no alias, no finding | 1 | `scripts/check-semantic-layer.py` (С-1) — map built from the skin, never a ban-list |
| D.41 stale compiled theme | `tokens.css` / `tokens.theme.css` must match what `tokens.json` compiles to | 1 | `compile-tokens.py --verify` (С-1) |
| D.40 dark ramp drift | every dark tone recomputes from `$meta.darkModel`; no dark role left as a literal | 1 | `tools/dops_skin.py darkramp --check` (Т-1) — a skin with no model passes without a claim |

Verification packs (v7.0, registered in `packs/registry.yaml`):
ai-look-detector, contrast-checker, token-validator, state-generator
(class: core), copy-linter (class: peripheral). Each carries a
`--self-test` acceptance probe wired into `eval/selftest/run-self-test.sh`
and the D24 pack block.
