# Environment degradation matrix (v5.1, CR-09)

Checked in the launch checklist BEFORE K1 starts; the degradation path is
fixed in advance and logged in the decision log. Invariant [A.6]: degradation
never upgrades a verdict; a missing capability is an explicit status, never a
silent pass.

## Capability: browser / render engine missing

| Stage | Behavior |
| :-- | :-- |
| K1 | **Blocked after skeleton code**: D2/D12 → `unavailable`; skeleton review happens on code + static HTML only |
| Gate 1 | Allowed on working static HTML; if even that is impossible — the run STOPS (a structure gate without any render is theater) |
| K2 | Visual gate declared `unavailable`: directions are delivered IN CODE with the note "aesthetics not verified" and `model_judged` marks. **Text verdicts about aesthetics without a render are forbidden** |
| Gate 2 | Cannot run blind → postponed until a render exists; autonomous `provisional_ai` is NOT allowed without screenshots |
| K3 | D2/D12/D13/D15/D20/D21 → `unavailable`; verdict caps at `ready_with_caveats` |

## Capability: image generation missing

| Stage | Behavior |
| :-- | :-- |
| K2 assets | Raster slots → typography-compositional solutions (display type, CSS/SVG composition, duotone of licensed sources); manifest records `typography_only` |
| K3 | D14 applies to what exists; slots must not silently vanish — each has a declared replacement |

## Capability: Node.js missing

| Stage | Behavior |
| :-- | :-- |
| K1 | Single-file neutral HTML profile only (no build step) |
| K3 | D1 → `unavailable` (no build to run); HTTP-only checks (curl status codes per route); everything browser-based → `unavailable`; verdict caps at `ready_with_caveats` |

## Capability: Playwright missing (Node present)

| Stage | Behavior |
| :-- | :-- |
| K2 | Slice renders via the project's dev server + system browser screenshots if possible; else degrade per "browser missing" |
| K3 | `run-ui-checks.sh` exits 2 (`unavailable`) after running curl-based HTTP checks; AI diagnostics FROM CODE ONLY — no aesthetic verdicts without section screenshots; D20 → `unavailable` |

## Capability: axe-core missing (Playwright present)

| Stage | Behavior |
| :-- | :-- |
| K3 | D20 → `unavailable` with the install command in the report; NEVER `skip`; a11y-relevant DOM probes (alt, labels, contrast — covered by D3/D10/D14) still run |

## Capability: network / fonts CDN missing

| Stage | Behavior |
| :-- | :-- |
| K2 | Font choices restricted to locally installable/bundled families; no hotlinked webfonts |
| K3 | D8 font-load check against local files only |

## Escalation rule

If the degradation path blocks a HUMAN gate (Gate 1 without any render, Gate
2 without screenshots), the run PAUSES and tells the user exactly which
capability to restore — it never substitutes an AI verdict for a human gate
that cannot honestly run.
