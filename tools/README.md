# tools/ — the machine contour

Everything deterministic lives here, behind one entry point: `tools/dops`.

## Why

Cost and wall-clock of an agent pipeline are linear in the **number of
turns**, and a resident instruction is paid on every turn that follows it:

```
money      ≈ Σ over turns (context size at that turn) + output
wall-clock ≈ turns × (latency + thinking + tool time)
```

The floor used to be ~25 separate script invocations — ~25 turns per
verification — while the scripts themselves take about a second in total.
The scripts were never the bottleneck; invoking them one at a time was.

So the contour is split:

| Contour | Runs | Costs |
| :-- | :-- | :-- |
| **A — deterministic (`tools/`)** | build, floor, tokens, reports, trace | seconds, 0 tokens |
| **B — generative** | K1 structure, K2A/K2B visuals, fixes | model turns |
| **C — human** | Gate 1 / 2 / 3 | human time |

Contour A never enters the model's context. The agent reads the failures,
not the registry.

## Commands

```bash
tools/dops doctor [--fix]        # capabilities: pyyaml, node, playwright, chromium, axe
tools/dops verify --profile standard [--url http://localhost:5173] [--build-cmd "npm run build"]
tools/dops card [--audit]        # regenerate .agents/RULES.card.md (the resident rule set)
tools/dops handoff K1            # context packet for a stage subagent (flat, ~2k tokens)
tools/dops shots --budget 6      # which screenshots diagnostics may open
tools/dops harvest --check       # the flywheel gate: what does this run leave behind?
tools/dops hash plan contract:experience   # [E.3] what a change forces, what may be reused
tools/dops announce --gate gate2 --decision provisional_ai --rollback "..."   # [A.26]
tools/dops status                # current pulse; stale pulse = silent incident
tools/dops checkpoint publish --id sitemap --artifact ... [--provisional]   # [У-2]
tools/dops control issue --command speed_up      # [У-3] steer the run, not the product
tools/dops pins classify         # [П-2] sort owner edits into 4 lanes before the model
tools/dops stage start K1        # run instrumentation
tools/dops stage end   K1
tools/dops report                # per-stage wall-clock + instruction tokens
tools/dops cost --write          # measured cost.actual into the contract
tools/dops selftest              # acceptance probes of the tooling itself
```

`verify` exits 0 for the ready family and 1 for `not_ready`, writes
`artifacts/audit/floor.json`, and prints only what is not green.

## floor-registry.json

The executable registry: id, group, lane, blocking, command, required
capabilities, fix hint. `quality-guardian/references/deterministic-floor.md`
remains the canonical prose registry for humans — the two are guarded
against drift by `dops verify --audit-registry`.

Lanes: `fs` checks run in parallel, `browser` checks run serially (one
browser at a time). Profiles select groups; the blocking core is present in
every profile, so `[E.4]` holds — budgets never downgrade blocking checks.

## RULES.card.md and the rule taxonomy

A rule belongs in the prompt only if it changes what the model **writes**.
If a checker catches it afterwards, stating it costs context on every turn
and buys nothing. `tools/rules-taxonomy.json` makes that judgement explicit
per invariant — `generative`, `generative_and_verified`, `verified`,
`process` — and `dops card` emits only the first two, plus the numbers a
writer needs up front and the ban-list.

Result: ~1.1k resident tokens instead of the full references. The card is
generated, never hand-edited; `dops card --audit` (wired into the self-test)
fails when a constraint key is renamed, an invariant is added to AGENTS.md
without a class, or the card outgrows its budget.

Numbers come from `.agents/knowledge-sync/constraints/` — a frozen snapshot
of the ux-wiki constraints, pinned in `PIN.json` and refreshed only at
version boundaries through the `wiki-sync` pack. The runtime never reads a
live wiki: a run must be reproducible months later, and an external repo is
data, not instructions.

## hash-graph.json — [E.3] for real

`[E.3]` ("recompute only downstream of the changed input") had been written
down since v5 and never implemented: no artifact stored the hash of its
inputs, so every change request rebuilt everything and a gate veto could
never be cheap. `hash-graph.json` states what derives from what;
`dops hash` records, verifies and plans against it.

Statuses: `fresh`, `stale` (an input changed), `drifted` (the artifact was
hand-edited after generation while its inputs stayed put — silent drift, a
defect [A.10]), `absent`, `unrecorded`. Contract sections are hashed
normalised, so reformatting the contract is not a change.

## One event, two views

`dops stage start|end` writes BOTH the history (`artifacts/trace.jsonl`, what
cost and gate-wait metrics are computed from) and the current state
(`artifacts/progress.json`, what the owner or a dashboard reads) in a single
call. Two separate calls per event would drift apart within a day — and the
gate-overtaking metrics have to be computable from the same stream they are
measured on.

## Checkpoints and the control queue

A checkpoint is a published artifact plus the actions the owner may take on
it; publishing never stops the conveyor. The type registry
(`checkpoint-registry.json`) is closed on purpose — `publish` refuses an
unregistered type, and refuses a type with no actions, because a checkpoint
without actions is a status line.

Control commands are queued from chat, panel or a pin and applied only at
control points. `rollback_to` walks the input-hash graph and supersedes the
checkpoints after its target; without recorded hashes it is refused with the
reason rather than silently costing a full rebuild [A.6]. `skip_scope` can
never reach the core floor [E.4].

Both live in append-only logs (`artifacts/checkpoints.jsonl`,
`artifacts/control-queue.jsonl`): they are events with a chronology, and
rewriting the contract on every publish would destroy its comments.
`contract-read.py checkpoints|checkpoint <id>|control_queue [status]` reads
them, so the contract stays the single entry point [A.10].

## Pins and the sorting station

A comment is born in the artifact and used to be expressed in chat, so half
of every revision went into working out which element was meant.
`gate-annotate.js` is now always-on — a pin carries selector, viewport and
kind — and `dops pins classify` routes each pin into a lane **before** the
model is involved: A token/copy (script, seconds), B block swap, C structure
(narrow K1 + gate), D taste or ambiguous (waits for one word from the owner).

The classifier is a word list, not a model: it has to be cheaper than the work
it routes. Structure rules are checked before token rules, so "add a page
about prices" is not mistaken for a colour edit. On a realistic 15-pin set,
67% of edits never reach the big model.

## Scan scope

A project installs this toolkit *into itself*, so a naive walk of the
project root audits `.agents/`, `packs/` and `eval/selftest/fixture/` (which
holds deliberate traps) and reports them as product defects. Every walker
now skips the vendored pipeline; override with

```bash
DOPS_SCAN_EXCLUDE="dir1,dir2" tools/dops verify
```

Scanning an excluded directory on purpose (a fixture, a vendored subtree)
disables the exclusion — pointing a check at a directory means you meant it.
