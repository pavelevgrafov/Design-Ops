# Starter floor report — site-portfolio

Verdict: ready_with_caveats (script-run checks green; hosted browser checks
run on first materialization into a project).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-site/tokens.css — 4/4 pairs |
| D4–D8 typography | pass | check-typography.py on skeleton/tokens.css |
| D9 token usage | pass | check-token-usage.sh — zero raw values in markup |
| D10 placeholders | pass | check-placeholders.sh — real copy slots only |
| D11 ban-list | pass | lint-ban-list.sh |
| D.27 focus visible | pass | check-focus-visible.py |
| D.28 semantic HTML | pass | check-semantic-html.py |
| D.29 reduced motion | pass | motion only inside `prefers-reduced-motion: no-preference` |
| D.30 AI-look | pass | ai-look-detector — zero tier-1 markers |
| D.36 copy | pass | copy-linter — no corporate slop |
| D12/D13/D20 | unavailable(hosted run pending) | run on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run |

## Design notes

- **Cases are outcomes, not process diaries.** Every `case_N_result` slot is
  documented as requiring a number or a concrete change. "Redesigned the
  dashboard" tells a hiring reader nothing, and a portfolio full of such
  lines is the most common reason this page fails its one job.
- **The empty state is shipped, not improvised** [A.12]: a portfolio whose
  work is under NDA still reads as deliberate instead of unfinished.
- **No thumbnail grid.** A grid of images promises visual case studies the
  owner may not have; the list carries the argument in text and survives a
  portfolio with no screenshots at all. Add imagery in K2B, on evidence.
