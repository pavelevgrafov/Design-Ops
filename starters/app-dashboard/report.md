# Starter floor report — app-dashboard

Verdict: ready_with_caveats (hosted browser checks run on first materialization).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-app/tokens.css — 4/4 pairs |
| D4–D8 typography | pass | check-typography.py |
| D9 token usage | pass | check-token-usage.sh |
| D10 placeholders | pass | check-placeholders.sh |
| D11 ban-list | pass | lint-ban-list.sh |
| D12/D13/D20 | unavailable(hosted run pending) | runs on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run (no playwright at factory time) |
| mock volume | pass | mock/orders.json — 100 rows, seeded |
| RBAC | pass | manager role has order.delete denied (live switch) |
