# Install / Migration Guide — Design Pipeline Codex v5.2

## Fresh install (a host project without the pipeline)

1. **Copy into the project root:**
   - `.agents/` — the skill package;
   - `eval/` — prompts and rubric;
   - `AGENTS.md` — entry point;
   - `README.md`, `INSTALL.md`, `LICENSE` — documentation.

2. **Script dependencies:** Python ≥3.10 + `pip install pyyaml` (required —
   the contract is read only via `contract-read.py`); **Bash ≥3.2-compatible**
   (verified on macOS bash 3.2.57 + BSD grep and Linux bash 5 + GNU grep).
   For browser checks (D2/D12/D13/D15/D20/D21):
   `npm i -D playwright axe-core && npx playwright install chromium`.
   Without them those checks honestly report `unavailable` (curl HTTP
   fallback) — everything else still works.
3. **Permissions:** `chmod +x .agents/skills/*/scripts/*.sh
   .agents/skills/*/scripts/*.py`.
4. **Self-test (v5.2):**
   ```bash
   bash eval/selftest/run-self-test.sh
   ```
   Runs every validator against the bundled fixture (contract parsing, lorem
   trap, D5 heading case, clean skeleton, static bash/BSD audits) plus the
   browser smoke when playwright is installed. Expected: `22 passed, 0 failed`
   (browser stage skips explicitly without playwright). Run it on BOTH
   environment families before shipping changes: macOS (bash 3.2 + BSD grep)
   and Linux (bash 5 + GNU grep).
5. **Self-check:**
   ```bash
   bash .agents/skills/structure-builder/scripts/check-skeleton.sh
   python3 .agents/skills/quality-guardian/scripts/check-typography.py .agents/skills/visual-director/assets
   ```
   The first must exit 0; the typography check on the assets dir reports
   granular pass[D4]–pass[D8] lines (placeholder tokens legitimately flag
   notes, not errors).
6. **First run:** prompt P01 from `eval/example-prompts.md`, score with
   `eval/eval-rubric.md`. Pass ≥10/12 with no zeros in C1–C4/C11/C12 =
   install OK.

## Repository layout

```
project-root/
├── AGENTS.md
├── README.md
├── INSTALL.md
├── LICENSE
├── .agents/
│   └── skills/
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
│   │   │   ├── information-model-guide.md
│   │   │   ├── component-substrate.md
│   │   │   └── stack-profiles.md
│   │   └── scripts/
│   │       ├── check-skeleton.sh
│   │       └── validate_experience_model.py
│   ├── visual-director/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   │   ├── tokens-template.json
│   │   │   ├── style-cards-template.md
│   │   │   ├── direction-template.md
│   │   │   ├── contact-sheet-template.html
│   │   │   └── asset-manifest-template.yaml
│   │   ├── references/
│   │   │   ├── divergence-rules.md
│   │   │   ├── gate2-protocol.md
│   │   │   ├── merge-rules.md
│   │   │   ├── token-pipeline.md
│   │   │   ├── asset-production.md
│   │   │   └── ban-list.md
│   │   └── scripts/
│   │       ├── compile-tokens.py
│   │       ├── check-divergence.py
│   │       └── lint-ban-list.sh
│   └── quality-guardian/
│       ├── SKILL.md
│       ├── assets/
│       │   └── quality-report-template.md
│       ├── references/
│       │   ├── deterministic-floor.md
│       │   ├── ai-diagnostics.md
│       │   ├── environment-degradation.md
│       │   └── status-taxonomy.md
│       └── scripts/
│           ├── run-ui-checks.sh
│           ├── check-contrast.py
│           ├── check-typography.py
│           ├── check-token-usage.sh
│           ├── check-placeholders.sh
│           └── validate-pipeline.py
├── eval/
│   ├── example-prompts.md
│   ├── eval-rubric.md
│   └── selftest/
│       ├── run-self-test.sh
│       ├── expected.txt
│       └── fixture/                                 # mini-sites + traps + contract
└── artifacts/                                       # created on the first run
```

## Migration v5.0 → v5.1

1. **Contract:** move `design-contract.yaml` from the root to `artifacts/`, set
   `meta.schema_version: "5.1"`, add new fields with defaults from
   `.agents/skills/pipeline-orchestrator/assets/design-contract-template.yaml`.
2. **Verdicts:** `pass` → `ready`, `conditional_pass` → `ready_with_caveats`,
   `fail` → `not_ready`. Old verdicts in the report are a validation error
   (`validate-pipeline.py` flags them with the mapping).
3. **Quick-mode ceiling (AC-23):** `brief.md`, `ux/`, `style-calibration.md`,
   `asset-manifest.yaml` exist only in standard/full; in quick their content
   lives in contract sections.
4. **Merge (CR-06):** on `gate2_result: merged(...)` fill
   `visual.merge.axes_resolution` and record `confirm_render` (in autonomous
   mode — `deferred` + include in the confirmation offer).
5. **Assets (CR-08):** every AI image carries a disclosure mechanism
   (`assets.slots[].disclosure: true` + a badge/credits per the visual
   system).
6. **Scripts:** replace the whole `scripts/` directories — signatures and
   exit codes changed (validate-pipeline.py is the single entry for D19).

## Updating inside a project (v5.1 → v5.2)

1. Replace `.agents/skills/*/scripts/` and `.agents/skills/*/SKILL.md` with
   the new versions (no contract changes — schema stays 5.1).
2. Ensure PyYAML is installed — `check-skeleton.sh` now reads the contract
   only via `pipeline-orchestrator/scripts/contract-read.py`.
3. Copy `eval/selftest/` and run `bash eval/selftest/run-self-test.sh` once
   on the target machine; keep the log.
4. Skim the v5.2 changelog in `README.md` — D15/D21 semantics changed
   (measured INP-proxy; undeclared paths = explicit `unavailable`).

## Environment matrix (v5.2)

| Environment | Status |
| :-- | :-- |
| macOS (bash 3.2.57 + BSD grep/sed/stat) | supported, self-test required before shipping script changes |
| Linux (bash 5 + GNU coreutils) | supported, reference CI environment |
| No Playwright | browser checks degrade to `unavailable` + curl HTTP fallback; verdict caps at `ready_with_caveats` |
| No PyYAML | contract-dependent checks report `unavailable` — install `pyyaml` (hard requirement) |

---

*Design Pipeline Codex v5.2 — bugfix/hardening over v5.1 (contract schema
unchanged, still 5.1): bash 3.2 + BSD grep compatibility, contract read only
via PyYAML (`contract-read.py`), SIGPIPE-proof checks (no `grep -q` after
pipes), D5 heading-selectivity fix, honest D21 (no silent skip), measured
INP-proxy (lab), zero-wait smoke + quick artifact matrix, self-test circuit
(`eval/selftest/`). Base: v5.1, CR-01…CR-16 over v5.0 (canonical D1–D21
registry, ready-family verdicts, two-screen slice, merge coherence +
confirming render, asset mini-gate, degradation matrix, execution economy,
decision log).*
