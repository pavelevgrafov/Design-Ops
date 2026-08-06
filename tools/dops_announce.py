#!/usr/bin/env python3
"""dops_announce.py — mechanical enforcement of [A.26] "nothing silently".

The kruto-landing incident was not a broken pipeline. It was a pipeline
behaving exactly as its prose allowed: `autonomous` switched on because the
owner was quiet, Gate 1 passed itself, Gate 2 chose direction A under
`provisional_ai`, and the owner learned all of it hours later from the final
report. A.26 was written to forbid that — as prose, which is the same form
the rule was already in when it was broken.

This makes it checkable:

  1. `autonomous` requires the owner's explicit grant recorded in the
     contract (`meta.autonomous_granted_by`). Silence is not a grant.
  2. Every machine-made gate decision (`autonomous_passed`, `provisional_ai`,
     a delegated gate) requires an announcement made AT THE MOMENT, carrying
     a rollback command — not a line in the closing report.

Usage:
  python3 tools/dops_announce.py --gate gate2 --decision provisional_ai \\
          --rollback "скажи «верни выбор» — направление откатится" [--root DIR]
  python3 tools/dops_announce.py --check [--root DIR]
  python3 tools/dops_announce.py --self-test

Exit: 0 clean, 1 an undeclared machine decision, 2 usage.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
PROGRESS_PY = os.path.join(PKG, ".agents", "skills", "pipeline-orchestrator",
                           "scripts", "progress.py")
LOG = os.path.join("artifacts", "announcements.jsonl")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")

MACHINE_DECISIONS = {"autonomous_passed", "provisional_ai"}


def read_block(text, name):
    m = re.search(r"^%s:.*$" % re.escape(name), text, re.M)
    if not m:
        return None
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    return m.group(0) + (tail[:stop.start()] if stop else tail)


def field(text, section, key):
    block = read_block(text, section)
    if block is None:
        return None
    inline = re.search(r"\{(.*)\}", block.splitlines()[0])
    if inline:
        m = re.search(r"%s:\s*([^,}]+)" % re.escape(key), inline.group(1))
        if m:
            return m.group(1).strip().strip('"').strip("'")
    m = re.search(r"^\s{2}%s:\s*(.*?)\s*$" % re.escape(key), block, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None


def load_log(root):
    path = os.path.join(root, LOG)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def announce(root, gate, decision, rollback, note=""):
    if not rollback.strip():
        print("announce: a machine decision without a rollback command is not "
              "an announcement — it is a notification [A.26]")
        return 2
    path = os.path.join(root, LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "gate": gate,
              "decision": decision, "rollback": rollback.strip(), "note": note}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # the announcement must be VISIBLE now, not only on disk
    if os.path.isfile(PROGRESS_PY):
        name = "%s → %s (откат: %s)" % (gate, decision, rollback.strip())
        try:
            subprocess.run([sys.executable or "python3", PROGRESS_PY,
                            "checkpoint", "--name", name],
                           cwd=root, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass
    print("announced: %s → %s | rollback: %s" % (gate, decision, rollback.strip()))
    return 0


def check(root):
    path = os.path.join(root, CONTRACT)
    if not os.path.isfile(path):
        print("A.26: no contract — nothing to check")
        return 0
    with open(path, encoding="utf-8") as f:
        text = f.read()

    problems = []
    mode = field(text, "meta", "interaction_mode") or ""
    if mode == "autonomous":
        grant = field(text, "meta", "autonomous_granted_by") or ""
        if not grant or grant in ('""', "''"):
            problems.append(
                "interaction_mode is `autonomous` with no "
                "`meta.autonomous_granted_by` — autonomous needs the owner's "
                "explicit word for THIS run; being unresponsive is not a grant "
                "[A.26]")

    announced = {(a.get("gate"), a.get("decision")) for a in load_log(root)}
    gates_block = read_block(text, "gates") or ""
    for m in re.finditer(r"^\s{2}(gate\d):\s*(\S+)\s*$", gates_block, re.M):
        gate, decision = m.group(1), m.group(2).strip('"').strip("'")
        if decision in MACHINE_DECISIONS and (gate, decision) not in announced:
            problems.append(
                "%s is `%s` — a machine decision with no announcement. It must "
                "be announced at the moment it is made, with a rollback "
                "command, not deferred to the final report [A.26]"
                % (gate, decision))

    if problems:
        for p in problems:
            print("A.26 FAIL: %s" % p)
        print("\nfix: `dops announce --gate <g> --decision <d> --rollback "
              "\"<how the owner undoes it>\"` at the moment of deciding")
        return 1
    print("A.26 pass: no undeclared machine decisions")
    return 0


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))
        cpath = os.path.join(tmp, CONTRACT)

        # the kruto incident, reproduced exactly
        with open(cpath, "w", encoding="utf-8") as f:
            f.write('meta:\n  mode: standard\n  interaction_mode: autonomous\n'
                    'gates:\n  gate1: autonomous_passed\n  gate2: provisional_ai\n')
        if check(tmp) != 1:
            problems.append("the kruto incident passed the check")

        # a grant alone is not enough — the decisions still need announcing
        with open(cpath, "w", encoding="utf-8") as f:
            f.write('meta:\n  mode: standard\n  interaction_mode: autonomous\n'
                    '  autonomous_granted_by: "pavel 2026-08-04: гони сам"\n'
                    'gates:\n  gate1: autonomous_passed\n  gate2: provisional_ai\n')
        if check(tmp) != 1:
            problems.append("machine gate decisions passed without announcements")

        if announce(tmp, "gate1", "autonomous_passed", "скажи «покажи структуру»") != 0:
            problems.append("a valid announcement was rejected")
        if announce(tmp, "gate2", "provisional_ai", "  ") != 2:
            problems.append("an announcement without a rollback was accepted")
        if check(tmp) != 1:
            problems.append("gate2 still undeclared but the check passed")
        announce(tmp, "gate2", "provisional_ai", "скажи «верни выбор»")
        if check(tmp) != 0:
            problems.append("a fully announced run did not pass")

        # interactive runs need no grant
        with open(cpath, "w", encoding="utf-8") as f:
            f.write('meta:\n  interaction_mode: interactive\n'
                    'gates:\n  gate1: passed\n  gate2: deferred\n')
        if check(tmp) != 0:
            problems.append("an ordinary interactive run was flagged")

    if problems:
        for p in problems:
            print("self-test FAIL: dops-announce: %s" % p)
        return 1
    print("OK: dops-announce self-test (A.26: grant required, machine "
          "decisions announced with a rollback, kruto incident now fails)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--gate", default=None)
    ap.add_argument("--decision", default=None)
    ap.add_argument("--rollback", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.gate and args.decision:
        return announce(root, args.gate, args.decision, args.rollback, args.note)
    return check(root)


if __name__ == "__main__":
    sys.exit(main())
