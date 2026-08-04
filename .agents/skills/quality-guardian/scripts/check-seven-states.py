#!/usr/bin/env python3
"""check-seven-states.py — D.38 (Tier 1): async screens cover 7 states.

Rule (source: knowledge/async-seven-states, invariant A.12): every async
module of the app profile is a 7-state automaton: idle, loading, skeleton,
populated, empty, error, success. The check reads the experience model
(artifacts/ux/experience-model.yaml or a given file) and verifies that
every module in state_matrix covers the required state set — 'skeleton'
may substitute 'loading', and 'populated' is implied by the screen itself
unless the module is async (declares data loading).

Site profile (no state_matrix) -> explicit skip, never a silent pass.

Usage: python3 check-seven-states.py <experience-model.yaml>
Exit: 0 pass/skip(site), 1 fail, 2 usage/io.
"""
import sys

try:
    import yaml
except ImportError:
    print("check-seven-states: PyYAML required", file=sys.stderr)
    sys.exit(2)

REQUIRED = {"loading", "empty", "error", "success"}
CANONICAL7 = ["idle", "loading", "skeleton", "populated", "empty", "error", "success"]
ALIASES = {"skeleton": "loading"}  # skeleton substitutes loading


def norm_states(module):
    raw = module.get("states") or []
    states = set()
    for s in raw:
        s = str(s).strip().lower()
        states.add(ALIASES.get(s, s))
    # populated is the designed default state — always present implicitly
    if states:
        states.add("populated")
        states.add("idle")
    return states


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"check-seven-states: cannot read {path}: {e}", file=sys.stderr)
        return 2

    matrix = (doc.get("state_matrix") or doc.get("experience", {}).get("state_matrix")) or []
    if not matrix:
        print("skip D.38: no state_matrix (site profile or quick mode)")
        return 0

    problems = []
    for module in matrix:
        if not isinstance(module, dict):
            continue
        name = module.get("module") or module.get("name") or "<unnamed>"
        is_async = bool(module.get("async", True))
        if not is_async:
            continue
        states = norm_states(module)
        missing = sorted(REQUIRED - states)
        if missing:
            problems.append(f"module '{name}': missing states {missing} "
                            f"(needs loading|skeleton, empty, error, success) [A.12]")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} seven-states problem(s) [D.38]")
        return 1
    print(f"OK: {len(matrix)} module(s) cover required async states [D.38]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
