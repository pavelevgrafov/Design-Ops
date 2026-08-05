# Starter floor report — landing-event

Verdict: ready_with_caveats (script-run checks green; hosted browser checks
run on first materialization into a project).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-site/tokens.css — 4/4 pairs |
| D4–D8 typography | pass | check-typography.py on skeleton/tokens.css |
| D9 token usage | pass | check-token-usage.sh — zero raw values in markup |
| D10 placeholders | pass | check-placeholders.sh — real copy slots only |
| D11 ban-list | pass | lint-ban-list.sh (bento probe skipped: GNU grep -z absent) |
| D.27 focus visible | pass | check-focus-visible.py |
| D.28 semantic HTML | pass | check-semantic-html.py — one h1, continuous hierarchy, `<main>` |
| D.29 reduced motion | pass | motion declared only inside `prefers-reduced-motion: no-preference` |
| D.30 AI-look | pass | ai-look-detector — zero tier-1 markers |
| D12/D13/D20 | unavailable(hosted run pending) | run on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run |

## Design notes

- **Sold-out is a state, not a missing card.** The third ticket tier carries
  an explicit sold-out line (icon + text + colour, never colour alone
  [A.19]) rather than disappearing — an absent tier reads as a page defect.
- **Days are separate blocks, not one long list.** The kruto run flagged
  lineup density on mobile as the structural risk; a per-day block with its
  own date keeps the scan cheap at 390px.
- **Two CTAs in the hero, one primary** [A.14]: buy (filled) and see the
  programme (text link) — the second is the honest answer for a visitor who
  is not ready to pay yet, and keeps them on the page.
- No hero image slot. A dated event usually arrives with its own poster;
  the starter does not pretend to supply one, and the layout holds without it.
