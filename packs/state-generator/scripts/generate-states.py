#!/usr/bin/env python3
"""generate-states.py — state-generator: 7-state specs for async blocks (A.12, D.38).

Two modes:
  generate (default): read an experience model (state_matrix) and write a
    state spec YAML with all 7 states per async module, ready for K1/K2A
    to fill with concrete CSS/copy (the agent is the executor, the spec is
    the contract — source: knowledge/async-seven-states).
  --check: verify an existing state spec covers all 7 states per module
    (feeds D.38).

Usage:
  python3 generate-states.py <experience-model.yaml> [--out state-spec.yaml]
  python3 generate-states.py --check <state-spec.yaml>
  python3 generate-states.py --self-test
Exit: 0 pass/skip, 1 fail, 2 usage/io.
"""
import sys

try:
    import yaml
except ImportError:
    print("generate-states: PyYAML required", file=sys.stderr)
    sys.exit(2)

STATES = ["idle", "loading", "skeleton", "populated", "empty", "error", "success"]
STATE_RULES = {
    "idle": "что здесь будет + CTA (подсказка до первой загрузки)",
    "loading": "< 4s — спиннер; > 4s — прогресс с процентами/шагами",
    "skeleton": "предсказуемая структура → скелетон вместо спиннера (aria-hidden)",
    "populated": "идеальное состояние с данными",
    "empty": "не пустота, а онбординг: причина + следующий шаг + CTA",
    "error": "конкретика без кодов + действие восстановления + сохранение ввода (inline, role=alert для критичных)",
    "success": "подтверждение завершения (правило «пик–конец»)",
}

def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"generate-states: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)

def generate(model_path, out_path):
    doc = load(model_path)
    matrix = (doc.get("state_matrix") or doc.get("experience", {}).get("state_matrix")) or []
    if not matrix:
        print("skip: no state_matrix (site profile) — no spec generated")
        return 0
    spec = {"generated_by": "state-generator (A.12)", "states_taxonomy": STATES, "modules": []}
    for m in matrix:
        if not isinstance(m, dict) or not m.get("async", True):
            continue
        name = m.get("module") or m.get("name") or "<unnamed>"
        spec["modules"].append({
            "module": name,
            "states": {s: {"rule": STATE_RULES[s], "spec": None} for s in STATES},
            "a11y": {"busy": "aria-busy on loading region",
                     "live": "aria-live=polite for state changes",
                     "alert": "role=alert for critical errors"},
        })
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
        print(f"OK: state spec for {len(spec['modules'])} module(s) -> {out_path}")
    else:
        print(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False))
    return 0

def check(spec_path):
    doc = load(spec_path)
    modules = doc.get("modules") or []
    if not modules:
        print("FAIL: state spec has no modules [D.38]")
        return 1
    problems = []
    for m in modules:
        name = m.get("module", "<unnamed>")
        states = set((m.get("states") or {}).keys())
        missing = [s for s in STATES if s not in states]
        if missing:
            problems.append(f"module '{name}': missing states {missing}")
        else:
            empty = [s for s, v in (m.get("states") or {}).items()
                     if isinstance(v, dict) and v.get("spec") in (None, "")]
            if empty:
                problems.append(f"module '{name}': states declared but unfilled: {sorted(empty)}")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} state-spec problem(s) [D.38]")
        return 1
    print(f"OK: {len(modules)} module(s) with complete 7-state specs [D.38]")
    return 0

def self_test():
    import os, tempfile
    model = {"state_matrix": [{"module": "orders", "states": ["loading", "empty", "error", "success"]}]}
    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, "model.yaml")
        sp = os.path.join(td, "spec.yaml")
        with open(mp, "w", encoding="utf-8") as f:
            yaml.safe_dump(model, f)
        if generate(mp, sp) != 0 or not os.path.exists(sp):
            print("self-test FAIL: spec not generated")
            return 1
        doc = load(sp)
        states = set(doc["modules"][0]["states"].keys())
        if states != set(STATES):
            print(f"self-test FAIL: generated states {sorted(states)} != 7 canonical")
            return 1
        if check(sp) == 0:
            print("self-test FAIL: unfilled spec passed --check")
            return 1
        for st in doc["modules"][0]["states"].values():
            st["spec"] = "filled"
        with open(sp, "w", encoding="utf-8") as f:
            yaml.safe_dump(doc, f)
        if check(sp) != 0:
            print("self-test FAIL: filled spec rejected by --check")
            return 1
    print("OK: state-generator self-test (generate -> check cycle)")
    return 0

def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--check" in sys.argv:
        if not args:
            print(__doc__, file=sys.stderr)
            return 2
        return check(args[0])
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    out = None
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        out = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    return generate(args[0], out)

if __name__ == "__main__":
    sys.exit(main())
