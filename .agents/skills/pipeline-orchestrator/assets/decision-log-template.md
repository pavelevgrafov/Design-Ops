# Decision log — {product.name}
<!-- Chronological journal: one line per decision — date, stage, decision, basis.
     Mandatory sections are checked by validate-pipeline.py (AC-25).
     First entry is always the request classification. -->

## Classification
- {date} · S0 · Request classified as: {route from the S0 table} · basis: {one line}
- {date} · S0 · Modes: depth={quick|standard|full}, interaction={interactive|autonomous} · basis: {auto-select formula / explicit user word}
- {date} · S0 · Environment: browser={yes|no}, playwright={yes|no}, imagegen={yes|no} · degradation path: {if any}

## Clarification (K1)
- {date} · K1 · {questions asked + answers | assumptions logged (autonomous)} · basis:

## Gate 1
- {date} · G1 · Result: {passed | changes_requested | autonomous_passed} · notes: {what was changed, if anything}

## Taste calibration (K2)
- {date} · K2 · Method: {references | style cards | skipped_autonomous} · principles: {list} · anti-references: {list}

## Direction seeds
- {date} · K2 · Direction {id}: persona={...}, domains={...}, boldness={safer|middle|bolder} · basis:

## Gate 2
- {date} · G2 · Result: {chosen(X) | merged(...) | regenerated | provisional_ai(X)} · randomization: {mapping}
- {date} · G2 · (if merged) Axes: {axis → source}; coherence: {pass/diagnosis}; confirming render: {shown|adjusted|rejected|deferred}

## Regenerations & failure hypotheses
- {date} · K2 · Regeneration #{n}: hypothesis={what repels: color/density/mood} · basis: {user words}
- {date} · K2 · Post-scale failure #{n}: hypothesis={...} · action: {...}

## Accepted limitations
- {date} · K3 · {limitation} · impact: {...} · risk accepted by: {name/role}

## Verdict
- {date} · K3 · Verdict: {ready | ready_with_caveats | not_ready} · checks: {n/n} · retests: {history}
