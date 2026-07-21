# Starter floor report — app-dashboard

Verdict: ready_with_caveats (script-run checks green; hosted browser checks
run on first materialization into a project).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-app/tokens.css — 4/4 pairs (17.77, 8.86, 4.79, 17.77) |
| D4–D8 typography | pass | check-typography.py on skeleton/tokens.css |
| D9 token usage | pass | check-token-usage.sh — zero raw values in markup |
| D10 placeholders | pass | check-placeholders.sh — real copy slots only |
| D11 ban-list | pass | lint-ban-list.sh |
| D12/D13/D20 | unavailable(hosted run pending) | runs on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run (no playwright at factory time) |
