# Starter floor report — app-dashboard

Verdict: ready_with_caveats (hosted browser checks + D21-matrix run on first
materialization into a project).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-app/tokens.css — 4/4 pairs (17.77, 8.86, 5.36, 17.77) |
| D4–D8 typography | pass | check-typography.py |
| D9 token usage | pass | check-token-usage.sh |
| D10 placeholders | pass | check-placeholders.sh |
| D11 ban-list | pass | lint-ban-list.sh |
| States implemented | pass | loading/empty/error/success/permission_denied panels in markup |
| D12/D13/D20/D21-matrix | unavailable(hosted run pending) | runs on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run (no playwright at factory time) |
