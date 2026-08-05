#!/usr/bin/env python3
"""gate-require.py — mechanical gate enforcement (v7.1, meta-analysis S1.3).

Gates are no longer honesty-on-honor: a conveyor stage that requires a gate
MUST run this check first. Exit 1 = the stage refuses to proceed; the
reason names the exact missing state and the legal path forward.

Requirements (fixed by stage):
  gate1 — K2A base skin and K3 floor require gates.gate1 ∈
          {passed, autonomous_passed} [A.1]
  gate2 — K2B scaling requires gates.gate2 ∈ {passed, provisional_ai} [A.2]
  gate3 — deploy prod requires gates.gate3 ∈ {passed} AND
          deploy.prod.rollback_tested: true AND verdict ∈ ready-family

Gate-overtaking (v7.2, [A.25], mechanics: references/gate-overtaking.md):
  stage:<name> — may this stage run while a gate is `provisional`?
  verdict      — may a ready-family verdict be issued right now?
  deliver      — may the result be handed over / deployed right now?

Usage: python3 gate-require.py <contract> <gate1|gate2|gate3|stage:NAME|verdict|deliver>
Exit: 0 requirement met, 1 refused (reason printed), 2 usage/io.
"""
import sys

try:
    import yaml
except ImportError:
    print("gate-require: PyYAML required", file=sys.stderr)
    sys.exit(2)

REQUIRED = {
    "gate1": {"passed", "autonomous_passed"},
    "gate2": {"passed", "provisional_ai"},
    "gate3": {"passed"},
}
READY_FAMILY = {"ready", "ready_with_caveats"}

# [A.25] What the machine may do while the owner has not yet answered a gate.
# Reversible and cheap: yes. Anything that turns work into a PRODUCT, or that
# is visible outside, or that cannot be undone: no.
PROVISIONAL_ALLOWED = {
    "K2A": "base skin — reversible, no taste claim",
    "K3": "floor run — measurement, not delivery",
    "K2B-slice": "direction preparation on the two-screen slice only",
}
PROVISIONAL_FORBIDDEN = {
    "K2B-scale": "scaling beyond the slice needs Gate 2 [A.2]",
    "verdict": "a verdict is a product claim",
    "deliver": "delivery is a product claim",
    "deploy": "externally visible",
    "gate3": "prod requires every gate answered",
    "harvest": "writes into the shared starter library",
    "marker-removal": "the not_approved_visual_design marker stays while unanswered",
}
PROVISIONAL = "provisional"


def provisional_gates(gates):
    return sorted(g for g, v in gates.items()
                  if isinstance(v, str) and v.strip() == PROVISIONAL)


def overtaking_check(c, query):
    """[A.25] Provisional work is never delivered as product."""
    gates = c.get("gates") or {}
    status = c.get("status") or {}
    pending = provisional_gates(gates)
    blocked = bool(status.get("deliverable_blocked"))

    # the flag and the gates must agree — a stale flag is silent drift [A.10]
    if pending and not blocked:
        print(f"REFUSED: {', '.join(pending)} is provisional but "
              f"status.deliverable_blocked is not true — the contract claims "
              f"the result is deliverable while a gate is unanswered [A.25/A.10]")
        return 1
    if blocked and not pending:
        print("REFUSED: status.deliverable_blocked is true but no gate is "
              "provisional — clear the flag when the last gate is answered")
        return 1

    if query.startswith("stage:"):
        stage = query.split(":", 1)[1]
        if not pending:
            print(f"OK: no provisional gate — stage '{stage}' unrestricted")
            return 0
        if stage in PROVISIONAL_ALLOWED:
            print(f"OK: '{stage}' may run under provisional "
                  f"({PROVISIONAL_ALLOWED[stage]}); pending: {', '.join(pending)}")
            return 0
        why = PROVISIONAL_FORBIDDEN.get(
            stage, "unknown stage — closed taxonomy, so it is refused [A.11]")
        print(f"REFUSED: '{stage}' while {', '.join(pending)} is provisional: {why}")
        return 1

    if not pending:
        print(f"OK: no provisional gate — {query} permitted")
        return 0

    verdict = str(status.get("verdict") or "")
    if query == "verdict":
        if verdict in READY_FAMILY:
            print(f"REFUSED: verdict '{verdict}' with {', '.join(pending)} "
                  f"still provisional — the machine may work ahead, it may not "
                  f"call the result ready [A.25]")
            return 1
        print(f"OK: no ready-family verdict claimed while {', '.join(pending)} "
              f"is provisional")
        return 0

    print(f"REFUSED: {query} while {', '.join(pending)} is provisional. "
          f"Legal path: batch-confirm the gate, or veto it "
          f"(`dops hash plan <changed-input>` scopes the rework).")
    return 1


def main():
    valid = (sys.argv[2] in REQUIRED or sys.argv[2] in ("verdict", "deliver")
             or sys.argv[2].startswith("stage:")) if len(sys.argv) == 3 else False
    if not valid:
        print(__doc__, file=sys.stderr)
        return 2
    path, gate = sys.argv[1], sys.argv[2]
    try:
        with open(path, encoding="utf-8") as f:
            c = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"gate-require: cannot read contract: {e}", file=sys.stderr)
        return 2

    if gate not in REQUIRED:
        return overtaking_check(c, gate)

    gates = c.get("gates") or {}
    value = str(gates.get(gate) or "pending")
    ok_states = REQUIRED[gate]
    if value in ok_states:
        if gate == "gate3":
            prod = ((c.get("deploy") or {}).get("prod") or {})
            verdict = str((c.get("status") or {}).get("verdict") or "")
            if not prod.get("rollback_tested"):
                print(f"REFUSED: gate3 passed but deploy.prod.rollback_tested is not true "
                      f"— run the dry-run rollback first (Gate 3 acceptance)")
                return 1
            if verdict not in READY_FAMILY:
                print(f"REFUSED: verdict '{verdict}' is not ready-family — "
                      f"deploy is legal only from ready|ready_with_caveats")
                return 1
        print(f"OK: {gate} requirement met ({value})")
        return 0

    legal = " | ".join(sorted(ok_states))
    hint = {
        "gate1": "show the structure artifact (sitemap/flow-map) and record the human decision [A.1]",
        "gate2": "run the blind contact sheet or record explicit delegation (provisional_ai) [A.2]",
        "gate3": "prod needs an active deploy pack + explicit human confirmation",
    }[gate]
    print(f"REFUSED: {gate} is '{value}', required: {legal}. Legal path: {hint}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
