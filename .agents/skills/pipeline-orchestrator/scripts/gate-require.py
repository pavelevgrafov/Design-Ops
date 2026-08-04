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

Usage: python3 gate-require.py <contract> <gate1|gate2|gate3>
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


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in REQUIRED:
        print(__doc__, file=sys.stderr)
        return 2
    path, gate = sys.argv[1], sys.argv[2]
    try:
        with open(path, encoding="utf-8") as f:
            c = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"gate-require: cannot read contract: {e}", file=sys.stderr)
        return 2

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
