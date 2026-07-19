# Status taxonomy + verdicts (v5.1, CR-03)

One vocabulary across scripts, reports, and the contract. Consistency here is
what makes the report trustworthy.

## Check statuses

| Status | Meaning | Requirements | Effect on verdict |
| :-- | :-- | :-- | :-- |
| `pass` | ran, criteria met | evidence path/value | none |
| `fail` | ran, criteria violated | failing values + location | blocking (unless the check is advisory/capped) |
| `skip` | not applicable | reason, why N/A | none |
| `unavailable` | should run, couldn't | reason + nearest manual alternative | blocking checks: caps verdict at ready_with_caveats |
| `degraded` | partially ran | what passed + what didn't run | treated as unavailable for the unrun part |
| `provisional` | AI-judged, awaiting human | `model_judged: true` + evidence | advisory only; never alone-blocking |

Every check line also names its **executor**: `script` / `model_judged: true`
/ `human`.

## Verdicts (renamed in 5.1)

| Verdict | Meaning | Rules |
| :-- | :-- | :-- |
| `ready` | ship it | no blocking fail; no blocking unavailable; provisionals confirmed or demoted |
| `ready_with_caveats` | ship with named caveats | no blocking fail, BUT: blocking unavailable exists, OR D15 violated, OR advisory findings/accepted limitations remain (each: rationale + **risk owner**) |
| `not_ready` | do not ship | any blocking fail. Delivery stops; orchestrator loops |

## Verdict rules [A.8]

1. An open blocker ⇒ `not_ready`. No exceptions.
2. `not_ready` is **never lowered without a fix + retest**; the report keeps
   history (found → fixed → retested). `validate-pipeline.py` rejects a
   `ready` verdict recorded over an unretested blocker.
3. An accepted limitation ⇒ at best `ready_with_caveats`, with the
   justification and WHO accepted the risk recorded (decision log + report).
4. D15 violations never block `ready` entirely — they cap at
   `ready_with_caveats` (lab metrics are environment-dependent; CLS
   prevention is blocking via D14).

## Rules for statuses

1. **No silent conversions.** unavailable→pass, provisional→pass, fail→skip
   without a recorded reason are integrity violations (D19 catches them via
   report↔contract cross-check).
2. **Reasons are mandatory** for skip/unavailable/degraded — a cause, not a
   restatement.
3. **Provisional travels in pairs**: `status: provisional` +
   `model_judged: true`, with evidence. A provisional finding on a blocking
   topic is routed to a deterministic check; if none exists, it becomes a
   residual risk, not a fail.
4. **Degraded is honest partial credit**: "390 ✓, 768 ✓, 1440 didn't render —
   environment timeout" is `degraded`, not pass, not fail.
5. **Advisory checks** (AI diagnostics) never block alone; they shape
   ready_with_caveats residuals.

## User-facing wording (delivery report)

Translate to plain language:
- ready → "ready"
- ready_with_caveats → "ready with caveats" (+ the list)
- not_ready → "not ready" (+ what blocks it)
- pass → "verified"
- fail → "failed (fixed / sent back)"
- skip → "not applicable, because …"
- unavailable → "couldn't verify here, because …; how to check manually: …"
- degraded → "partially verified: …"
- provisional → "preliminary model assessment, awaits your confirmation"
