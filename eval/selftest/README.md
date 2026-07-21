# Self-test circuit (v5.2, TZ-4.1)

Runs every package validator against the bundled fixture and asserts the
expected outcomes. This is the regression net for the defects found in the
external v5.1 testing (macOS, July 2026) — every fix ships with the case
that caught it.

## Run

```bash
bash eval/selftest/run-self-test.sh
```

Expected: `self-test: 22 passed, 0 failed, 0 skipped` (see `expected.txt`).
Without playwright the browser stage is an explicit `skip`, never a silent
pass — install it (`npm i -D playwright && npx playwright install chromium`)
for the full circuit. Run on BOTH environment families before shipping
changes to scripts: **macOS (bash 3.2 + BSD grep)** and **Linux (bash 5 +
GNU grep)** [TZ-4.2].

## What the fixture covers

| Case | Fixture | Regression for |
| :-- | :-- | :-- |
| Contract parsing | `fixture/contract/design-contract.yaml` (3 key_screens + 2 scenarios) | defect A2: sed/awk scrape bled scenario IDs into the screen check [TZ-1.3] |
| Clean skeleton | `fixture/clean/` (marker, gray ramp, real copy, priorities) | false FAILs on a legitimately passing skeleton [TZ-2.1b] |
| Lorem trap | (generated at runtime, >64 KB of matches) | SIGPIPE false PASS under `pipefail` + `grep -q` [TZ-2.1a] |
| D5 selectivity | `fixture/clean/tokens.css` (h1 `11ch` + `--measure-text: 65ch`) | heading ch failing the body measure [TZ-2.4] |
| D5 negative | `fixture/traps/measure/bad.css` (p `30ch`) | over-correction: a genuine violation must still fail |
| Hidden state panels | `fixture/site/` (5 `hidden` panels, 2 routes) | 30-second stalls in smoke; quick artifact matrix [TZ-3.1/3.2] |
| D21 honesty | `fixture/site/paths.json` present vs absent | silent skip → explicit `unavailable` + verdict cap [TZ-2.2] |
| INP | browser stage | interactivity pass without a measured value [TZ-2.3] |
| Static audits | all `.agents/**/scripts/*.sh` | bash-4-only constructs, GNU-only regex tokens [TZ-1.1/1.2] |

The runner itself is strictly bash 3.2 / BSD grep compatible — it is part
of the guarantee it checks.
