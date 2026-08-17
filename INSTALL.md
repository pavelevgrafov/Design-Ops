### Directory layout after unpacking

```
<project repo or skills repo>/
├── AGENTS.md
├── README.md
├── .agents/skills/
│   ├── pipeline-orchestrator/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   │   ├── design-contract-template.yaml
│   │   │   └── decision-log-template.md
│   │   ├── references/
│   │   │   ├── modes.md
│   │   │   ├── execution-economy.md
│   │   │   ├── gate-templates.md
│   │   │   └── launch-checklist.md
│   │   └── scripts/
│   │       └── contract-read.py
│   ├── structure-builder/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   │   ├── brief-template.md
│   │   │   ├── experience-model-template.yaml
│   │   │   └── skeleton-manifest-template.yaml
│   │   ├── references/
│   │   │   ├── stack-profiles.md
│   │   │   ├── information-model-guide.md
│   │   │   └── component-substrate.md
│   │   └── scripts/
│   │       ├── validate_experience_model.py
│   │       └── check-skeleton.sh
│   ├── visual-director/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   │   ├── direction-template.md
│   │   │   ├── style-cards-template.md
│   │   │   ├── contact-sheet-template.html
│   │   │   ├── tokens-template.json
│   │   │   └── asset-manifest-template.yaml
│   │   ├── references/
│   │   │   ├── divergence-rules.md
│   │   │   ├── ban-list.md
│   │   │   ├── gate2-protocol.md
│   │   │   ├── merge-rules.md
│   │   │   ├── token-pipeline.md
│   │   │   └── asset-production.md
│   │   └── scripts/
│   │       ├── check-divergence.py
│   │       ├── lint-ban-list.sh
│   │       └── compile-tokens.py
│   └── quality-guardian/
│       ├── SKILL.md
│       ├── assets/
│       │   └── quality-report-template.md
│       ├── references/
│       │   ├── deterministic-floor.md
│       │   ├── ai-diagnostics.md
│       │   ├── status-taxonomy.md
│       │   └── environment-degradation.md
│       └── scripts/
│           ├── check-placeholders.sh
│           ├── check-token-usage.sh
│           ├── check-contrast.py
│           ├── check-typography.py
│           ├── run-ui-checks.sh
│           └── validate-pipeline.py
├── eval/
│   ├── example-prompts.md
│   ├── eval-rubric.md
│   └── selftest/
│       ├── run-self-test.sh
│       ├── expected.txt
│       └── fixture/                                 # mini-sites + traps + contract
├── packs/            # integration bus: pack manifests + registry.yaml + recheck.sh
├── starters/         # Verified Starters + index.yaml + harvest.py + recheck.sh
├── skins/            # base-site / base-app (tokens.json + compiled tokens.css)
├── knowledge/        # evidence vault: sources/ + index.yaml (Obsidian = optional viewer)
├── .github/          # workflows the self-test asserts against (amendment 07 §2)
├── package.json      # node manifest the browser lane resolves playwright from
├── install.sh        # one-command installer (v6.0)
└── artifacts/                                   # created on first run
    ├── design-contract.yaml
    ├── decision-log.md
    ├── skeleton/  visual/  ux/  prototype/  audit/
```

### Install steps

1. **Copy** every path listed in `ITEMS` at the top of `install.sh` into the
   target repo (or `~/.codex/` for globally available skills). That list is
   the single definition of what the package ships — a second copy of it
   here would drift, which is how `.github/` and `package.json` came to be
   missing from installs in the first place; the self-test now fails if
   `ITEMS` omits anything the repository tracks.
2. **Script dependencies:** Python ≥3.10 + `pip install pyyaml` (required —
   the contract is read only via `contract-read.py`); **Bash ≥3.2-compatible**
   (verified on macOS bash 3.2.57 + BSD grep and Linux bash 5 + GNU grep).
   For browser checks (D2/D12/D13/D15/D20/D21/D22): `npm install && npx
   playwright install chromium`, run in the target repo — `package.json`
   ships with the package and pins both dependencies, so nothing is typed
   from memory. Without them those checks honestly report `unavailable`
   (curl HTTP fallback) — everything else still works.
3. **Permissions:** `chmod +x .agents/skills/*/scripts/*.sh
   .agents/skills/*/scripts/*.py`.
4. **Self-test (v5.2):**
   ```bash
   bash eval/selftest/run-self-test.sh
   ```
   Runs every validator against the bundled fixture (contract parsing, lorem
   trap, D5 heading case, clean skeleton, static bash/BSD audits) plus the
   browser smoke when playwright is installed. Measured on 17.08.2026, v7.2,
   without playwright: `122 passed, 0 failed, 1 skipped` in the package
   checkout, `121 passed, 0 failed, 2 skipped` in a fresh install (the second
   skip is the install-completeness probe, which needs a git checkout to
   compare against). The browser stage skips explicitly rather than passing
   quietly. Run it on BOTH
   environment families before shipping changes: macOS (bash 3.2 + BSD grep)
   and Linux (bash 5 + GNU grep).
5. **Self-check:**
   ```bash
   python3 .agents/skills/visual-director/scripts/compile-tokens.py \
     .agents/skills/visual-director/assets/tokens-template.json --check-only
   python3 .agents/skills/visual-director/scripts/check-divergence.py --help || true
   python3 .agents/skills/quality-guardian/scripts/check-typography.py \
     .agents/skills/visual-director/assets || true
   ```
   The first must exit 0; the typography check on the assets dir reports
   granular pass[D4]–pass[D8] lines (placeholder tokens legitimately flag
   notes, not errors).
6. **First run:** prompt P01 from `eval/example-prompts.md`, score with
   `eval/eval-rubric.md`. Pass ≥10/12 with no zeros in C1–C4/C11/C12 =
   install OK.

### Fast path (v6.0): one command

```bash
bash install.sh <target-repo>
```

Copies the package, restores permissions, checks dependencies, runs the
self-test, prints the ready line. Steps 1–6 below are what it does manually.

### Migration v5.1 → v6.0

1. **Package:** replace the v5.x tree with this one (new: `packs/`,
   `starters/`, `skins/`, `knowledge/`, `install.sh`; scripts added per
   skill).
2. **Contracts:** run once per project —
   `python3 .agents/skills/pipeline-orchestrator/scripts/contract-migrate.py artifacts/design-contract.yaml`
   (idempotent; appends the migration changelog entry itself).
   `validate-pipeline.py` accepts 6.0 and warns on 5.1.
3. **Nothing else changes:** 5.1 gates/floor semantics carry over; Gate 2
   stays where it was (`deferred` only for contracts that never ran K2B).

### Migration v5.0 → v5.1

1. **Package:** replace the v5.0 `.agents/skills/` tree with this one
   (4 new files, ~27 updated; see the 5.1 changelog table).
2. **Contracts:** a `schema_version: "5.0"` contract is upgraded by the
   orchestrator on first touch: moved from the project root to
   `artifacts/design-contract.yaml`, `schema_version: "5.1"`, verdicts mapped
   (`pass→ready`, `conditional_pass→ready_with_caveats`, `fail→not_ready`),
   new fields defaulted. The migration is logged in changelog + decision log.
   `validate-pipeline.py` REJECTS un-migrated 5.0 contracts with migration
   guidance.
3. **Check numbers:** reports written against either v5.0 D-registry are
   read via the normative mapping table in
   `quality-guardian/references/deterministic-floor.md`. New reports use only
   the canonical D1–D21.
4. **Backward compatibility of work:** v5.0 projects without tokens keep
   working; the restyle router offers tokenization first. Skeletons without
   the marker and directions without axes are NOT accepted by 5.1 stages.

---

*Design Pipeline Codex v6.0 — working interface foundation for sites and
apps (contract schema 6.0): K2A base skin + deferrable K2B, app profile
(domain model/RBAC/state matrix/mock API), Verified Starters, pack bus with
core/peripheral verdict semantics, floor D1–D24 (visual regression, secrets,
pack block, INP beacon), knowledge vault, context/cost budgets, one-command
install, gate annotations, [A.11] statuses-by-scripts. Base: v5.2
(bash 3.2 + BSD grep, PyYAML-only contract reads, SIGPIPE-proof checks,
honest D21, measured INP-proxy, zero-wait smoke, self-test circuit) over
v5.1 (canonical D1–D21 registry, ready-family verdicts, two-screen slice,
merge coherence + confirming render, asset mini-gate, degradation matrix,
execution economy, decision log).*
