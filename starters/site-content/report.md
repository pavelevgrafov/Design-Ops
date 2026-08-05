# Starter floor report — site-content

Verdict: ready_with_caveats (script-run checks green; hosted browser checks
run on first materialization into a project).

| Check | Status | Evidence |
| :-- | :-- | :-- |
| D3 contrast | pass | skins/base-site/tokens.css — 4/4 pairs |
| D4–D8 typography | pass | check-typography.py on skeleton/tokens.css |
| D9 token usage | pass | check-token-usage.sh — zero raw values in markup |
| D10 placeholders | pass | check-placeholders.sh — real copy slots only |
| D11 ban-list | pass | lint-ban-list.sh |
| D.27 focus visible | pass | check-focus-visible.py (input + button + links) |
| D.28 semantic HTML | pass | check-semantic-html.py |
| D.29 reduced motion | pass | motion only inside `prefers-reduced-motion: no-preference` |
| D.30 AI-look | pass | ai-look-detector — zero tier-1 markers |
| D.36 copy | pass | copy-linter — no corporate slop |
| D12/D13/D20 | unavailable(hosted run pending) | run on materialization |
| D22 baseline | pending | taken by visual-regression.sh on the first hosted run |

## Design notes

- **The subscribe form is a real form**, not a decorative row: labelled
  input (visually hidden, still in the accessibility tree), `type=email`,
  `autocomplete`, `required`, and a privacy line next to the button. The
  states beyond idle (success, error) are declared in the contract and get
  their markup when the form is wired to a backend [A.12].
- **Reading time and date sit in the byline**, because the decision the
  visitor is making is "now or later", and both inputs to it must be visible
  without opening the piece.
- **Excerpts state a finding.** The copy-map documents it: "explores the
  question of…" is the failure mode this page exists to avoid.
