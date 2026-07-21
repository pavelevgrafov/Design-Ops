# Quality report — {product.name} — {date}
<!-- artifacts/audit/quality-report.md. Cross-checked by validate-pipeline.py (D19). -->

## Verdict: {ready | ready_with_caveats | not_ready}

Mode: {mode} · QA cycles: {n} · Viewports: {390/768/1440}
Environment degradation (if any): {path per environment-degradation.md}

## Deterministic floor (D1–D24)

| # | Check | Status | Executor | Details |
|---|-------|--------|----------|---------|
| D1 | Build / typecheck | | script | |
| D2 | Console errors | | script | |
| D3 | Contrast (token pairs, WCAG) | | script | ink/canvas {x.x}:1 … |
| D4 | Base text ≥16px | | script | |
| D5 | Measure 45–75ch {+ both language variants} | | script | |
| D6 | Line-height 1.4–1.7 | | script | |
| D7 | Modular scale 1.2–1.333 | | script | |
| D8 | Fonts ≤2 (+mono), swap, fallback | | script | |
| D9 | Token usage | | script | |
| D10 | Placeholders & hotlinks | | script | |
| D11 | Ban-list | | script | |
| D12 | Viewports 390/768/1440 | | script | |
| D13 | Tap targets ≥24px | | script | |
| D14 | Images local, alt, ≤300KB, dims | | script | |
| D15 | Performance (lab): LCP/INP/CLS | | script | violation → caps at ready_with_caveats |
| D16 | Neutral marker removed | | script | |
| D17 | Divergence (axes + blind test) | | script + model_judged | |
| D18 | UX model valid | | script | standard/full |
| D19 | Pipeline integrity | | script | gates order, decision log, realized==confirmed |
| D20 | A11y quick pass (axe) | | script | 0 critical/serious |
| D21 | Functional paths (e2e/alt/error/keyboard) | | script | |
| D22 | Visual regression (unapproved diff blocks) | | script + human | approve is human, logged |
| D23 | Secrets scan | | script | blocking; Gate 3 precondition |
| D24 | Service packs (core caps verdict) | | script | one line per pack |

Field add-on (not a floor check): INP beacon p75 {value} ms — caps, never blocks.

Statuses: pass / fail / skip(reason) / unavailable(reason) / degraded(what).

## AI diagnostics (advisory)

| Screen §section @viewport | Factor | Class | Severity | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| {home §hero @1440} | hierarchy | heuristic | minor | {p1 dominant?} | {shot path} | provisional · model_judged |

Rules: subjective findings never exceed minor [AI.8]; any visible defect caps
its dimension at ≤3/5 [AI.9]; swap-augmentation used for all comparisons:
{yes/no}; flipped verdicts discarded: {n}.

## Fixed during QA (retest history)

- {finding} — fix: {what} — retest: pass · {date}

## Accepted limitations (ready_with_caveats only)

- {limitation} — impact: … — rationale: … — **risk accepted by: {name/role}**

## Skips & unavailabilities

- {check}: {reason + nearest manual alternative}

---
Report ↔ contract consistency: {verified by validate-pipeline.py}
