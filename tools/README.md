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
tools/dops pins check            # [П-3] feasible? legal? new? — refuse with alternatives
tools/dops panel emit            # [П-4] the owner's own knobs: bake the safe domain
tools/dops panel apply delta.json # [П-4] the only door back into tokens.json
tools/dops pins sweep            # [П-5] one intake pass: classify + check the new pins
tools/dops pins apply --machine-only  # [П-5] execute what is machine-executable
tools/dops pins feed --json      # [П-6] the whole revision picture in one call
tools/dops status --json         # [П-6] pulse + plan + checkpoints + queue + pins
tools/dops skin darkramp         # [Т-1] regenerate the dark tones from $meta.darkModel
tools/dops skin darkramp --check # [Т-1] D.40: a hand-edited dark tone fails the build
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

## The checker at the door

`dops pins check` runs between sorting and execution, on each pin, asking four
questions in a fixed order — cheap before expensive:

1. **feasible** — does the selector still resolve in the current build?
2. **norms** — is the value inside the declared ranges (type scale, 8pt
   ladder, `$meta.contrastPairs` at 4.5:1)? does it ask for a tier-1 banned
   pattern?
3. **conflict** — does it contradict `scope.exclusions` or the decision log?
4. **duplicate** — has the owner already said this?

The ranges are read from the skin's `tokens.json` and the WCAG maths is
imported from `check-contrast.py`; a second copy of either in the checker
would be exactly the drift [A.10] forbids.

Two rules make a refusal usable. **A refusal always carries alternatives** —
"contrast falls to 1.54:1; use #6e6a64 (5.14:1), or darken the background, or
carry the emphasis with weight" — and `annotations-log.py` fails a `rejected`
verdict that arrives without a reason and at least one way out. And **a
duplicate is questioned, never silently merged**: the owner wrote it twice for
a reason.

Cost: on the same 15-pin set, **15 of 15 pins were decided by script alone,
zero model calls**; 4 became instant negotiations instead of work that would
have been built and then thrown away. A small model may be consulted for two
things only — an unresolvable target, and a semantic conflict with the
decision log — through `$DOPS_SMALL_MODEL` (a command reading one JSON object
on stdin, printing one JSON verdict on stdout). With no such command the
script lane still runs and those pins go to the owner marked
`checker_unavailable`: honest degradation [A.6], not a fabricated pass.

`dops pins answer --pin ID --text "..."` puts the owner's reply back into the
pin, keeps the old wording in `supersedes`, and sends it round for
re-classification. `dops pins metrics` counts revision latency, refusal share
and the script-only share.

## The self-service panel

`dops panel emit --skin <S> --artifact <page.html>` writes `panel-config.js`
next to the artefact; with `assets/token-panel.js` embedded after it, the
owner turns the parameters themselves — palette, type scale, line length,
dark theme — and the page changes in the same second. No assistant, no model,
no dev server. "Doing it" becomes "saw it and kept it".

The load-bearing decision is that **the safe domain is baked at emit time,
never computed in the browser**:

- the WCAG formula lives in `check-contrast.py` and is imported, not retyped;
  the thresholds come from D3's own table, including the tertiary tier at 3:1;
- artefacts open from `file://`, where fetching the skin is blocked, so the
  domain arrives as a `<script>`;
- an unsafe value is not warned about, it is **unrepresentable** — it never
  appears among the options, even if the JS has a bug.

A knob exists only for a variable the artefact actually uses, and only where
the skin declares alternatives. Both absences are printed with their reason.
When П-4 shipped, that left the dark layer with a theme toggle and one colour
knob: its values were authored as literals, so there was no declared ramp for
the emitter to draw from — and inventing one would be the emitter making
design decisions. Т-1 declared the ramp instead of relaxing the rule, and the
same emitter now builds twelve dark colour knobs per flagship skin without a
line of new code in this file. That is the shape of the rule working.

`dops panel apply token-delta.json` is the only door into `tokens.json`, and
it is five gates deep: the delta's sha256 must match the current skin, every
path must be a knob and every value one of that knob's options, the patch is
pointed text (the file's `comment` entries carry reasoning that a dump would
erase), the compiler and D3 re-run afterwards, and **any failure restores the
file in full**. Success records the new input hash [E.3] and one line in the
decision log.

Not in v1, deliberately: font families (no `$meta.fontAlternates` in the skins
yet), global spacing density (no semantic spacing aliases to move), and free
input of any kind — ever.

## The declared dark ramp

`dops skin darkramp` (Т-1) is the answer to a comment that could not be
checked. The dark layer used to be sixteen hand-written hexes under the
sentence *"text 87/60/38% over #121212, action lightened 40% + desaturated"* —
a model stated in prose, so nothing stopped the values and the sentence from
drifting apart, and П-4 could offer no dark knob at all.

The sentence is now `$meta.darkModel`:

```json
"darkModel": {
  "base": "#121212",
  "inkEmphasis": [100, 87, 60, 38, 24, 16, 12, 8],
  "accent": { "lighten": 0.40, "desaturate": 0.35 },
  "elevation": { "raised": 5, "overlay": 8, "modal": 11 }
}
```

From those four numbers the generator writes `primitive.color.darkInk`,
`darkSurface` and `accentDark`, and `semantic.dark.color.*` references them
instead of carrying literals. Two rules keep it honest:

- **the model is the only place taste lives.** `--check` recomputes every tone
  and fails on any difference, so a hand-edited hex is no longer invisible;
  that check is D.40 in the floor and therefore in CI. A skin that declares no
  model passes without a claim rather than pretending to have verified one.
- **the mapping stays a design decision.** That `inkMuted` is the 60% tier and
  not the 38% one is authored in the skin — the generator only refuses to let
  it be a literal.

Colour maths lives in one module (`dops_color.py`), which imports WCAG and hex
parsing from `check-contrast.py` rather than restating them. A second copy of a
formula is drift the moment one of them is corrected [A.10].

## Streaming intake

The conveyor worked but it walked: Export dropped a file in `~/Downloads`,
somebody moved it into the project, and the pins waited for the assistant to
have a session. `dops pins sweep` is the whole intake pass in one command —
take only the pins that are new, classify and check them in birth order, write
the store, record the latencies, print one line:

```
sweep: 17 new → 13 checked, 0 clarify, 3 rejected, 1 duplicate (2 machine-executable)
```

One command rather than "classify, then check" from outside: two external
calls mean two reads and two writes of the store and a split atomicity. The
kruto lesson — a floor made of many invocations can be passed halfway —
applies to intake too. Nothing new is a quiet `sweep: 0 new`; a watcher must
not shout when it has nothing to say.

Sweeping is idempotent, and a pin the owner answered comes round by itself:
`dops pins answer` puts it back to `new`, so the next sweep re-classifies it
with the new wording and keeps the old one in `supersedes`.

`dops pins apply` executes the pins whose plan is **machine-executable**, one
transaction per pin, through the same safety chain as the panel: a pointed
patch, the compiler and D3 (or the copy-linter for text), a full rollback of
that pin on any failure — its neighbours still land — and `apply_error` written
into the pin. Two pins aimed at the same token are not both applied: the later
one wins, the earlier becomes `superseded` with `superseded_by` and a sentence
explaining why. Silently overwriting the owner's first instruction with their
second is the failure this rule exists to prevent.

**A plan is machine-executable only when every parameter was extracted in
full** — a quoted `"old" → "new"` pair, or a named token and ramp step. Marking
prose `machine: true` would fabricate executability, which is worse than an
honest wait [A.6]. Measured share on the realistic 15-pin revision set:
**0%** — owners do not write instructions that way. On a set seeded with two
deliberately complete ones it is 12%. The number is a measurement, not a
target, and it is the argument for keeping the assistant in the loop for lane
A rather than the argument for a bigger extractor.

## The status feeds

The statuses existed; the aggregation did not. To understand ten pins the
owner had to open ten pins, and to understand the run they had to ask in chat
— and a status re-request is an interruption, which is the thing this wave
removes.

`dops pins feed --json` is the whole revision picture in one call: a summary
(waiting on owner, applied, rejected, superseded, in flight, apply errors,
median latency born→classified→checked→applied) and one row per pin carrying
its marker, its age, its last event and, when it is waiting, the question it
is waiting on. `dops status --json` is the run: pulse, run plan, checkpoints,
control queue, pin summary, and `pulse_freshness` — the share of the run
during which the pulse was alive (81.1% on the reference run).

Two promises hold the feeds together:

- **A section with no data is empty, never missing.** A widget that has to
  guess whether a key exists starts inventing meanings for its absence.
- **A stale pulse says so.** `fresh: false` is reported, never hidden: data
  from yesterday without a marker is worse than no widget at all.

Medians skip pins that lack a timestamp instead of counting them as zero — an
invented 0-second latency would make the run look better than it was. Nothing
is folded twice: the checkpoint log is folded by `dops_checkpoint`, which owns
that closed taxonomy, and the pin statuses are declared once in
`tools/pin-status.json`. `gate-annotate.js` keeps its own copy of that
taxonomy because it must run from `file://` with zero dependencies — the
duplication is deliberate and a self-test fails the moment the two diverge.

Inside the artefact the pin counter became a door: click it (or press `l`) and
every pin is one list, the ones waiting on the owner first, each row clickable
straight to its pin. A status line that cannot be acted on is an illusion of
control.

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
