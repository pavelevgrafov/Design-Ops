# Design Production Pipeline v5.2

![Design-Ops banner](docs/banner.svg)

Production pipeline that turns a text request into a finished, verified
website or web application — for AI agents (Codex, Claude Code, etc.).
Architecture: **three conveyors, two gates.**

```
K1 "Structure" → GATE 1 (human) → K2 "Visual" → GATE 2 (human) → K2 continued → K3 "Verification"
```

## What it does

- **Structure before style.** K1 builds a deliberately style-less neutral
  skeleton (real copy, gray graphite, priority annotations, all states
  implemented) — the user approves the STRUCTURE at Gate 1 before any visual
  work begins.
- **Taste is calibrated by showing, not interrogation.** K2 never asks "what
  style do you like?" — it decomposes user references into portable principles
  or runs an 8–10 style-card test, then constructs 2–3 divergent directions
  (persona + ≥3 non-overlapping domains + boldness spread, machine-verified)
  and presents them as a blind contact sheet at Gate 2.
- **The machine owns the floor.** K3 runs the canonical deterministic floor
  D1–D21 (build, console, WCAG contrast, typography, tokens, placeholders,
  ban-list, viewports, tap targets, images, lab performance, a11y, functional
  paths, pipeline integrity) and issues the verdict:
  `ready | ready_with_caveats | not_ready`.

## The guarantee

No "the model decided it looks fine". Every claim in the quality report is
backed by a script, a `model_judged: true` mark (always `provisional`), or a
human gate decision. A missing capability is an explicit `unavailable`
status — never a silent pass.

## Verdicts

- `ready` — no blocking fail, no blocking unavailable;
- `ready_with_caveats` — no blocking fail, but accepted limitations exist
  (each with a rationale and a named risk owner);
- `not_ready` — any blocking fail. Never lowered without a fix + retest.

## Modes

`quick` (≤5 screens, 1 role, low risk) · `standard` (6–15 routes or 2–3
roles) · `full` (high-risk / payments / PII). Orthogonal interaction mode:
`interactive` (default, two human gates) or `autonomous` (objective
self-checks + provisional AI pre-filter with a mandatory confirmation offer
on the user's return).

## Repository layout

```
.agents/skills/          — the four pipeline skills (orchestrator, K1–K3)
  pipeline-orchestrator/   routing, contract, gates, decision log, restyle
  structure-builder/       K1: brief, experience model, neutral skeleton
  visual-director/         K2: calibration, directions, tokens, assets, scale
  quality-guardian/        K3: checks D1–D21, diagnostics, verdict
AGENTS.md                — entry point, hard invariants A.1–A.10
INSTALL.md               — installation + migration guide
eval/                    — example prompts + scoring rubric + self-test circuit
docs/                    — brand assets
LICENSE                  — MIT
```

## Install

1. Copy `.agents/`, `eval/`, `AGENTS.md`, `README.md` into your repo.
2. Python ≥3.10 + `pip install pyyaml`; Bash ≥3.2-compatible (macOS and
   Linux both supported out of the box). For browser checks:
   `npm i -D playwright && npx playwright install chromium`.
3. `chmod +x .agents/skills/*/scripts/*`.
4. Verify the install: `bash eval/selftest/run-self-test.sh` (green on both
   macOS and Linux; browser stage runs when playwright is present).
5. First run: prompt P01 from `eval/example-prompts.md`, score with
   `eval/eval-rubric.md` (pass ≥ 10/12, no zeros in blocking criteria).

See `INSTALL.md` for the full installation and v5.0 → v5.1 migration guide.

## Changelog

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
