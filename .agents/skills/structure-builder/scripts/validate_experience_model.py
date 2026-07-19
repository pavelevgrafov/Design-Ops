#!/usr/bin/env python3
"""validate_experience_model.py — D18: validate artifacts/ux/experience-model.yaml.

Usage: python3 validate_experience_model.py [path]
       (default: artifacts/ux/experience-model.yaml)
Exit 0 = valid, 1 = violations (printed one per line).
Requires PyYAML.
"""
import sys, os

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML required (pip install pyyaml)")
    sys.exit(1)

VALID_PATTERNS = {"answer-first", "task-first", "object-first", "event-first", "comparison-first"}
VALID_PRIORITIES = {"p1", "p2", "p3"}
VALID_STATES = {"loading", "empty", "validation_error", "system_error", "success", "permission_denied"}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("artifacts", "ux", "experience-model.yaml")
    problems = []
    if not os.path.exists(path):
        print(f"FAIL: file not found: {path}")
        return 1
    with open(path, encoding="utf-8") as f:
        try:
            m = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"FAIL: YAML parse error: {e}")
            return 1

    m = m or {}
    pj = m.get("primary_job") or {}
    if not pj.get("statement"):
        problems.append("primary_job.statement is empty")
    st = str(pj.get("statement", "")).lower()
    if "when" not in st or "i want" not in st:
        problems.append("primary_job.statement not in 'When..., I want..., so I can...' form")

    aud = m.get("audience") or {}
    roles = aud.get("roles")
    if roles is not None and not isinstance(roles, list):
        problems.append("audience.roles must be a list (v5.1), not a string")

    # Localization risk: content variants required [K1.7]
    loc = m.get("localization") or {}
    if loc.get("risk") and not loc.get("content_variants"):
        problems.append("localization.risk=true but localization.content_variants is empty "
                        "(need long/short/cjk/empty-state variants on primary-scenario screens)")

    screens = m.get("screens") or []
    if not screens:
        problems.append("no screens defined")
    screen_ids = set()
    for s in screens:
        sid = s.get("id") or "<no-id>"
        if sid in screen_ids:
            problems.append(f"duplicate screen id: {sid}")
        screen_ids.add(sid)
        if not s.get("purpose"):
            problems.append(f"screen {sid}: purpose empty")
        if not s.get("p1_content"):
            problems.append(f"screen {sid}: p1_content empty")
        has_p1 = False
        for b in s.get("blocks") or []:
            pr = b.get("priority")
            if pr not in VALID_PRIORITIES:
                problems.append(f"screen {sid} block {b.get('id','?')}: priority '{pr}' not in {sorted(VALID_PRIORITIES)}")
            if pr == "p1":
                has_p1 = True
            if b.get("copy_source") not in {"real", "realistic-draft"}:
                problems.append(f"screen {sid} block {b.get('id','?')}: copy_source must be real|realistic-draft")
        if not has_p1:
            problems.append(f"screen {sid}: no p1 block")
        for stt in s.get("states") or []:
            if stt not in VALID_STATES:
                problems.append(f"screen {sid}: unknown state '{stt}' (valid: {sorted(VALID_STATES)})")
        for t in s.get("transitions") or []:
            if t.get("to_screen") and t["to_screen"] not in {x.get("id") for x in screens}:
                problems.append(f"screen {sid}: transition to unknown screen '{t['to_screen']}'")

    ip = m.get("information_pattern") or {}
    if ip.get("pattern") not in VALID_PATTERNS:
        problems.append(f"information_pattern.pattern '{ip.get('pattern')}' not in {sorted(VALID_PATTERNS)}")
    if not ip.get("reason"):
        problems.append("information_pattern.reason empty")

    covered = set()
    for sc in m.get("scenarios") or []:
        if not sc.get("steps"):
            problems.append(f"scenario {sc.get('id','?')}: no steps")
        covered |= set(sc.get("covers_screens") or [])
    uncovered = screen_ids - covered
    if uncovered:
        problems.append(f"screens not covered by any scenario: {sorted(uncovered)}")

    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} problem(s) in {path}")
        return 1
    print(f"OK: {path} valid ({len(screens)} screens, pattern={ip.get('pattern')})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
