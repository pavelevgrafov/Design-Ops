# K0/K1 discovery-lite — AJTBD-lite + RAT-lite (v7.0)

Enhancement of Step 1 (product frame) and the K0→K1 transition. Sources:
knowledge/discovery-methods, knowledge/ux-laws-21, knowledge/scanning-patterns,
knowledge/gestalt-principles.

Purpose: the pipeline gets smarter at the intake without turning discovery
into research theatre. Both tools are capped, recorded in the contract, and
never block the conveyor on their own.

## AJTBD-lite — job hypothesis (≤ 4 questions)

Ask at most 3–4 questions, folded into the Step-1 block (not an extra round):

1. What is the user trying to do? (situation → action)
2. What gets in the way today?
3. What do they use now (current alternative)?
4. (app profile only) Who pays for the result / who is the second role?

Output — a **job hypothesis**, not a job statement, recorded in the contract:

```yaml
product:
  job_hypothesis:
    statement: "When [situation], I want to [action], so I can [outcome]"
    confidence: low | medium | high     # high = owner confirmed it
    source: user_answer | inferred_from_request | category_default
```

Rules: `confidence: low|medium` hypotheses are flagged in the decision log
and offered for confirmation at Gate 1; the agent never upgrades confidence
by prose. For complex app screens, the 5W question set (what/when/where/
whom/how) from knowledge/discovery-methods maps every screen element to a
question a user actually asks — an element answering nothing is a removal
candidate (Nielsen №8).

## RAT-lite — riskiest assumptions (max 3)

At the K0→K1 transition, record at most 3 assumptions the structure depends
on, ranked by lethality:

```yaml
experience:
  assumptions:
    - claim: "Operators need cross-order aggregation, not per-order detail"
      lethality: high
      evidence: knowledge-vault cross-reference (similar projects/patterns)
      kill_criteria: "Gate 1 reviewer asks for per-order view first"
```

Rules:

- **Max 3.** More assumptions = the brief is not understood; go back to
  Step 1, don't accumulate.
- **Evidence = cross-reference** with the knowledge vault and Verified
  Starters, never a newly generated artifact.
- **Every assumption carries explicit kill criteria** — an observable
  condition that marks it refuted (at Gate 1 or during K3 functional
  paths). A refuted high-lethality assumption = structure defect: stop,
  record, redo the affected part of K1.
- The agent does not "fail fast" by itself: refutation is judged at a gate
  or by a check, never declared by the model.

## What this is NOT (scope guard)

- Not full AJTBD (no interviews, no Job Graph) — the agent has no access to
  real users; hypotheses stay hypotheses.
- Not full RAT (no evidence purchase) — "buying evidence" inside an agent
  pipeline means generating yet another artifact, which is banned.
- Not strategy: no segmentation, no market sizing — that is the owner's
  call, recorded at most as a contract label.
