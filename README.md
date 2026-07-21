<p align="center">
  <img src="docs/brand-header.svg" alt="DesignOps — brand image" width="100%">
</p>

# Design Production Pipeline v6.0

<img src="docs/banner.svg" alt="Design Production Pipeline — conveyors, human gates, one contract" width="100%">

Turns a plain-text request into a **working interface foundation** for
websites AND web apps — assembled fast, machine-verified, testable locally,
and ready to be taken into further UI refinement whenever you want. Not a
pretty-page generator: a basic but real product that works from the first
hour. Architecture: **conveyors + one mandatory gate + one contract.**

```
K0 discovery → K1 structure → GATE 1 (human) → K2A base skin (automatic)
→ K3 verification → [K2B full visual work — optional, anytime] → [K4 deploy — optional, GATE 3]
```

## What it is for

A skill pack for Codex CLI-style agents that takes a request like "make a
landing page", "prototype a dashboard with two roles", or "I have a
prototype, make it look good" and runs it through a production line:
structure first (a neutral skeleton approved by a human), an automatic
calibrated base skin, machine-verified quality — and full visual craft
(directions, blind choice, merge) as an option you can trigger today, next
month, or never. The human makes the taste decisions; the machine proves
the floor; AI assists only where it is reliable.

## Problems it solves

- **The first launch must sell.** A Verified Starter (`starters/`) lands the
  first testable artifact in minutes, not after a questionnaire — structure
  arrives pre-verified at "factory time", copy injects through a slot map,
  and the floor re-runs on the result. Finished projects feed new starters
  back through the harvest flywheel.
- **Real products are apps, not landings.** The `app` profile models the
  domain, RBAC, user flows, state matrix (screen × state × role × data
  volume) and an OpenAPI contract with typed mock fixtures BEFORE screens —
  accounts, dashboards and nested flows included.
- **Taste work shouldn't block a working product.** K2A (base skin) applies
  automatically after Gate 1; Gate 2 is deferrable — full visual work (K2B)
  is a restyle route over the finished foundation, never a rebuild.
- **AI slop and mode collapse.** Divergence is constructed (persona + domain
  seeds, 7 axes, boldness spread) and machine-verified; a linted ban-list
  blocks the statistical defaults (first-position Inter, indigo→purple
  gradients, glass, bento, blobs, icon-per-label, marketing-slop copy, dark
  patterns) — every ban cites its evidence note in `knowledge/`.
- **Unverifiable quality claims.** A canonical deterministic floor D1–D24
  adds visual regression (D22, unapproved diff blocks), secrets scan (D23),
  and the service-pack acceptance block (D24) to the v5.2 floor; a missing
  capability reports an honest `unavailable` and caps the verdict.
- **Fragile integrations.** Every external capability is a pack with a
  manifest, a live acceptance test and a frozen registry version. Core pack
  down → the verdict caps; peripheral pack down → a plain report line. Kill
  criteria remove what rots.
- **Silent drift and lost decisions.** One contract (schema 6.0) is the
  single source of truth; statuses are set by scripts from closed taxonomies
  [A.11], never by prose.
- **"I already have a prototype."** The neutralize route ingests a URL or
  files (screenshot + DOM dump) and strips the build back to an approved
  neutral skeleton instead of rebuilding.

## The skills — who builds UX, who builds UI

| Skill | Conveyor | Layer | Owns |
| :-- | :-- | :-- | :-- |
| `pipeline-orchestrator` | — | process | routing (profile site/app, starter-first/from-scratch, neutralize, restyle), the contract as SSOT, gates, packs, decision log, context/cost budgets, delivery report |
| `structure-builder` | K1 | **UX** | product frame, experience model, domain model + RBAC + state matrix (app), information pattern, neutral skeleton, sitemap artifact, neutralization |
| `visual-director` | K2A/K2B | **UI** | base skin (automatic); calibration, divergent directions, contact sheet, merge, DTCG tokens, assets, scaling (K2B) |
| `quality-guardian` | K3 | proof | deterministic floor D1–D24, INP field beacon, AI diagnostics, quality report, verdict |

Sidecars: `packs/` (integration bus), `starters/` (Verified Starters +
harvest), `skins/` (base-site, base-app), `knowledge/` (evidence vault — a
rule without a note does not exist; Obsidian is an optional viewer, never a
dependency).

## Gates

- **Gate 1 (structure)** — the only mandatory human gate of the core. The
  user approves a picture (sitemap / flow-map + RBAC), not YAML.
- **Gate 2 (visuals)** — deferrable; runs when K2B is requested. Blind
  contact sheet, anonymized variants, recorded randomization, merge by
  default.
- **Gate 3 (prod)** — exists only with an active deploy pack; requires a
  ready-family verdict, explicit confirmation, and a passed dry-run
  rollback.
- **Batch gate** — only on an explicit "fast": skeleton+skin (+contact
  sheet) in one message, answered as two explicit points.
- **"I trust the machine"** — explicit delegation of any gate
  (`provisional_ai`, recorded, with a confirmation offer on return). A
  normal mode for the non-designer persona, not a degradation.

## Core principles

1. **Taste is gathered by showing, not by asking.**
2. **The machine owns the floor, the human owns the ceiling, AI does
   diagnostics in between** (`provisional` + `model_judged` always).
3. **The contract is the single source of truth**; decisions are recorded
   before they are executed.
4. **Degradation never upgrades the verdict** — and a core-pack failure caps
   it; peripheral failure is just a report line.
5. **Statuses are set by scripts, not prose** [A.11]; a rule without an
   evidence note does not exist.

## Modes

| | quick | standard | full |
| :-- | :-- | :-- | :-- |
| When | landing, ≤5 screens, 1 role, low risk | 6–15 routes, 2–3 roles | >15 routes, high-risk, payments, PII |
| Directions at Gate 2 (K2B) | 2 | 3 | 3 (+wildcard) |
| Taste calibration | references OR style cards | both, user's choice | both, mandatory |
| QA cycles | 1 | 2 | 3 |
| Viewports | 390/768/1440 (all modes) | same | same + project extras |

Interaction modes (orthogonal): **interactive** (default) and **autonomous**
(gates run as objective AI self-check / `provisional_ai` pre-filter, with a
mandatory confirmation offer when the user returns).

## Install

One command:

```bash
bash install.sh <target-repo>
```

It copies the package, restores permissions, checks dependencies (Python
≥3.10 + pyyaml, Bash ≥3.2-compatible; playwright optional — browser checks
degrade honestly without it), runs the self-test, and prints the ready
line. See `INSTALL.md` for manual steps and the v5.x → v6.0 migration
(`contract-migrate.py`, idempotent).

First run: prompt P01 from `eval/example-prompts.md`, score with
`eval/eval-rubric.md` (pass ≥ 10/12, no zeros in blocking criteria).

## Changelog

### v6.0 — working interface foundation (contract schema 6.0)

- **Positioning:** not a pretty page but a working basic interface for
  sites AND apps — fast to assemble, locally testable, ready for further
  UI refinement.
- **K2 split:** K2A base skin (automatic, per-profile calibrated default,
  flagship maintained asset) + K2B full visual work (optional, deferrable,
  a restyle route). Gate 2 deferrable; Gate 1 is the only mandatory human
  gate; batch gate on explicit "fast"; "I trust the machine" delegation on
  any gate; Gate 3 (prod) with dry-run rollback acceptance.
- **App profile:** domain model, RBAC, user flows, state matrix, OpenAPI
  contract + typed mocks (100-row fixtures) before screens; starter
  `app-dashboard` demonstrates the full set.
- **Verified Starters:** factory-verified first artifact (landing-local,
  landing-saas, app-dashboard), slot-map injection, harvest flywheel from
  finished projects (`starters/harvest.py`).
- **Pack bus:** manifest + acceptance test + frozen registry per
  integration; core/peripheral classes with verdict semantics; scheduled
  re-checks; kill criteria. Packs: lazyweb-research, iconify, unsplash,
  google-fonts, og-image, favicon, deploy-github-pages,
  deploy-cloudflare-pages.
- **Floor D1–D24:** D22 visual regression (unapproved diff blocks, approve
  is human), D23 secrets scan (blocking, precedes deploy), D24 pack
  acceptance block (core caps the verdict), INP field beacon (caps, never
  blocks).
- **Knowledge vault:** `knowledge/` — evidence notes with levels
  (research / industry-standard / curated), every ban-list and checklist
  rule cites a `source:`, orphan notes are deleted by the validator, index
  ≤4 KB regenerated from notes, `verified_at` freshness tracked. Obsidian =
  optional viewer.
- **NFR mechanics:** context budget counter with calibrated limits,
  pre-start cost estimate vs `cost.actual`, one-command `install.sh`,
  invariant [A.11] (statuses by scripts), gate annotations
  (pin → `annotations.json` → decision log).
- **Migration:** `contract-migrate.py` 5.1 → 6.0, idempotent;
  `validate-pipeline.py` accepts 6.0 and warns on 5.1.

### v5.2 — bugfix/hardening (contract schema unchanged, still 5.1)

Released after external testing of v5.1 on macOS; every fix ships with a
regression case in `eval/selftest/`.

- **Runs on macOS out of the box.** All shell checks are bash 3.2 / BSD grep
  compatible (no bash-4-only expansions, POSIX regex classes, `grep -z`
  capability probe with honest skip, GNU/BSD `stat` fallback).
- **The contract is read only via PyYAML.** New helper
  `pipeline-orchestrator/scripts/contract-read.py` replaces sed/awk scraping
  that swallowed the `scenarios:` block and checked scenario IDs as screens
  (guaranteed false FAIL).
- **No more flaky placeholder checks.** The `producer | grep -q` pattern
  under `pipefail` died by SIGPIPE on outputs >64 KB and reported false
  PASS — all checks now use capture-then-test.
- **D5 typography fixed.** A heading with `max-width: 11ch` no longer fails
  the body-text measure; evidence comes from `--measure-*` tokens and text
  selectors only.
- **D15 measures interactivity.** Lab INP-proxy (PerformanceObserver event
  timing + real input, ≤200 ms) reported as "lab, not field-INP"; no
  interactivity pass without a measured value.
- **D21 without silent skips.** Undeclared functional paths now report an
  explicit `unavailable` and cap the verdict; keyboard probe and declared
  paths are reported as separate lines, and a pass requires both declared
  paths actually walked.
- **Smoke without 30-second stalls.** Screenshots cover only visible
  sections (`isVisible()` filter, 3 s timeout, no double DOM query); quick
  mode produces ≤3+1 PNG per route, standard/full are section-wise with cap
  12 and dedup; a 2-route quick run finishes in ≤90 s.
- **Self-test circuit.** `eval/selftest/run-self-test.sh` runs every
  validator against a bundled fixture (clean site, lorem trap, D5 heading
  case, contract with screens + scenarios, hidden state panels) on both
  macOS and Linux; "works out of the box" is now a blocking eval criterion
  (C12).

### v5.1

Canonical D1–D21 registry, ready-family verdicts, two-screen slice, merge
coherence + confirming render, asset mini-gate, degradation matrix,
execution economy, decision log (CR-01…CR-16 over v5.0).

## License

MIT — see `LICENSE`.
