# AGENTS.md — Design Production (v6.0)

## What this repository does

Production pipeline that turns a text request into a **working interface
foundation** for websites AND web apps: assembled fast, machine-verified,
testable locally, ready to be taken into further UI refinement — today, next
month, or never. Not a pretty page generator: a basic but real product that
works from the first hour.

```
K0 discovery → K1 structure → GATE 1 (human) → K2A base skin (automatic)
→ K3 verification → [K2B full visual work — optional, anytime] → [K4 deploy — optional, GATE 3]
```

Two artifact profiles: `site` (content-driven) and `app` (accounts,
dashboards, nested flows — domain model + RBAC + state matrix + mock API
before screens). Two build routes: `starter_first` (a Verified Starter as
the first testable artifact in minutes) or `from_scratch`.

## Hard invariants (never violate)

- **[A.1]** No visual work beyond the neutral skeleton until
  `gates.gate1 ∈ {passed, autonomous_passed}`.
- **[A.2]** K2B scaling beyond the slice requires `gates.gate2 ∈ {passed,
  provisional_ai}` (+ confirmed merge, if any). The automatic base skin
  (K2A) is NOT visual work in this sense: it applies and scales without
  Gate 2 (`gates.gate2: deferred`).
- **[A.3]** Skeleton and visuals never mix in one stage; no taste questions
  in K1; taste calibration happens only in K2B, only by showing.
- **[A.4]** Never ask "why" before the Gate 2 choice is recorded.
- **[A.5]** AI never issues a `ready` verdict on aesthetics — at most
  `provisional` or a diagnostic finding. Every model check: `model_judged: true`.
- **[A.6]** Degradation never upgrades a verdict; a missing capability is an
  explicit status, not a silent skip. A `core` pack unavailable caps the
  verdict at `ready_with_caveats`; a `peripheral` one is a report line.
- **[A.7]** A restyle never changes markup (skin property); if markup must
  change, it is not a restyle. K2B is a restyle route over the finished
  foundation, never a rebuild.
- **[A.8]** `not_ready` is never lowered without a fix + retest; an accepted
  limitation needs a rationale and a recorded risk owner.
- **[A.9]** Budgets never downgrade blocking checks (D1–D14, D16–D24) and
  never cancel Gate 1 in interactive mode.
- **[A.10]** Single source of truth: `artifacts/design-contract.yaml`.
  Decisions are recorded (contract changelog / decision log) before they are
  executed. Silent drift = defect.
- **[A.11]** Statuses are set by scripts, not by prose. Every status value
  comes from a closed taxonomy and is backed by an artifact a check can
  re-verify; the agent never "declares" a pass.

## Entry point

Trigger words: "make a website", "landing page", "prototype an app",
"dashboard", "account portal", "redesign", "restyle", "change fonts/colors".
Entry skill: `pipeline-orchestrator` (`.agents/skills/pipeline-orchestrator/`).
Scope guard: websites and web apps only — for docs/slides/spreadsheets, stop
and say so.

## Skills

| Skill | Conveyor | Role |
| :-- | :-- | :-- |
| `pipeline-orchestrator` | — | routing (profile/route/mode), contract, gates, decision log, economy, packs, restyle, delivery |
| `structure-builder` | K1 | brief, experience model, domain model/RBAC (app), neutral skeleton, sitemap, neutralization of existing code |
| `visual-director` | K2A/K2B | base skin application (automatic); taste calibration, divergence, contact sheet, merge, tokens, assets, scale (K2B) |
| `quality-guardian` | K3 | checks D1–D24, AI diagnostics, quality report, verdict |

Sidecars: `packs/` (integration bus: manifest + acceptance test + registry,
core/peripheral classes), `starters/` (Verified Starters + harvest
flywheel), `skins/` (base-site, base-app), `knowledge/` (evidence vault —
a rule without a note does not exist).

## Gates in one paragraph each

- **Gate 1 (structure) — the only mandatory human gate of the core.** The
  user approves a picture, not YAML: sitemap (site) or flow-map + RBAC +
  module thumbnails (app). Pass = explicit "ok" / change list / silence in
  autonomous (`autonomous_passed` + confirmation offer on return).
- **Gate 2 (visuals) — deferrable.** Runs only when K2B is requested (now or
  months later). Blind contact sheet — anonymized "Variant 1/2/3", randomized
  order recorded, all variants simultaneously, main + contrast screen each.
  Merge is the default. Until then the product wears the base skin.
- **Gate 3 (prod) — exists only with an active deploy pack.** Prod requires
  `ready|ready_with_caveats` + explicit human confirmation + a passed dry-run
  rollback (`deploy.prod.rollback_tested: true`) + D23 green.
- **Batch gate:** only on the user's explicit "fast": skeleton+skin (+
  contact sheet if K2B requested at once) in ONE message, answered as two
  explicit points. `gates.mode: batched`; the rework-rate metric watches the
  dogma.
- **"I trust the machine":** explicit delegation of any gate →
  `provisional_ai`, recorded in `gates.delegated[]`, mandatory confirmation
  offer on return. A normal mode, not a degradation.

## Verdicts

`ready` | `ready_with_caveats` | `not_ready`. Rules: an open blocker →
`not_ready`; `not_ready` never lowered without a fix + retest; accepted
limitations require a rationale and a named risk owner; core-pack failure or
uncovered D21/D22 caps at `ready_with_caveats` (never upgrades).

## Definition of Done (every delivery)

1. `status.verdict` = `ready` or `ready_with_caveats` (explicit accepted
   limitations + risk owners).
2. All D1–D24 checks pass, or carry `skip`/`unavailable` with reasons; no
   blocking check `unavailable` under a `ready` verdict.
3. All images local, alt text, ≤300 KB, declared dimensions; favicon + OG
   slots filled.
4. Restyle of any page = token edit + `compile-tokens.py`, zero manual
   component edits.
5. `artifacts/audit/quality-report.md` generated and consistent with the
   contract; `artifacts/decision-log.md` contains all mandatory entries
   (Gate-2 sections only when K2B ran).
6. D22 visual regression baselined; D23 secrets scan green; D24 pack block
   evaluated.
7. The user gets a plain-language summary: what was built, what was decided
   at the gates, what was verified, what remains — plus the actual cost
   (`cost.actual`) against the pre-start estimate.
