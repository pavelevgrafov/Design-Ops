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
└── artifacts/                                   # created on first run
    ├── design-contract.yaml
    ├── decision-log.md
    ├── skeleton/  visual/  ux/  prototype/  audit/
```

### Install steps

1. **Copy** `.agents/`, `eval/`, `AGENTS.md`, `README.md` into the target
   repo (or `~/.codex/` for globally available skills).
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

*Design Pipeline Codex v5.2 — bugfix/hardening over v5.1 (contract schema
unchanged, still 5.1): bash 3.2 + BSD grep compatibility, contract read only
via PyYAML (`contract-read.py`), SIGPIPE-proof checks (no `grep -q` after
pipes), D5 heading-selectivity fix, honest D21 (no silent skip), measured
INP-proxy (lab), zero-wait smoke + quick artifact matrix, self-test circuit
(`eval/selftest/`). Base: v5.1, CR-01…CR-16 over v5.0 (canonical D1–D21
registry, ready-family verdicts, two-screen slice, merge coherence +
confirming render, asset mini-gate, degradation matrix, execution economy,
decision log).*
