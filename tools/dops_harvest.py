#!/usr/bin/env python3
"""dops_harvest.py — the flywheel gate (Wave 2).

The starter library has stayed at three entries while every project runs
`from_scratch` — and a `from_scratch` run costs roughly twice a
`starter_first` one (the package's own cost-table). The flywheel was
described but never enforced, so it never turned.

This makes the DECISION mandatory at delivery, not the harvest itself:
harvesting needs the owner's explicit permission flag, but recording what
was decided does not [A.10]. A run that produced a new pattern and left no
trace of why it was not harvested is the defect this catches.

Contract field (starters block):
  harvest_decision: "candidate:<id>" | "declined: <reason>" | "reused:<id>"

Usage:
  python3 tools/dops_harvest.py --check [--root DIR]
  python3 tools/dops_harvest.py --decide "declined: one-off client microsite" [--root DIR]
  python3 tools/dops_harvest.py --self-test

Exit: 0 decision recorded (or not required), 1 missing decision, 2 io.
"""
import argparse
import os
import re
import sys

VALID = re.compile(r"^(candidate:[a-z0-9-]+|reused:[a-z0-9-]+|declined:\s*\S.*)$")


def block(text, name):
    m = re.search(r"^%s:.*$" % re.escape(name), text, re.M)
    if not m:
        return None, None, None
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    end = m.end() + (stop.start() if stop else len(tail))
    return m.group(0), text[m.end():end], end


def read_field(text, section, key):
    head, body, _ = block(text, section)
    if head is None:
        return None
    inline = re.search(r"\{(.*)\}", head)
    if inline:
        m = re.search(r"%s:\s*([^,}]+)" % re.escape(key), inline.group(1))
        if m:
            return m.group(1).strip().strip('"').strip("'")
    if body:
        m = re.search(r"^\s{2}%s:\s*(.*?)\s*$" % re.escape(key), body, re.M)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def check(contract_path):
    if not os.path.isfile(contract_path):
        print("harvest: no contract at %s — nothing to check" % contract_path)
        return 0
    with open(contract_path, encoding="utf-8") as f:
        text = f.read()
    route = read_field(text, "starters", "route") or ""
    decision = read_field(text, "starters", "harvest_decision") or ""

    if decision:
        if not VALID.match(decision):
            print("harvest FAIL: harvest_decision is not a recognised value: "
                  "%r (expect candidate:<id> | reused:<id> | declined: <reason>)"
                  % decision)
            return 1
        print("harvest: decision recorded — %s" % decision)
        return 0

    if route == "starter_first":
        print("harvest FAIL: starter_first run with no harvest_decision — "
              "record `reused:<id>` (or a candidate, if the run changed the pattern)")
        return 1
    print("harvest FAIL: a from_scratch run left no harvest_decision. This is "
          "why the library still has three starters and every project pays "
          "the from_scratch price. Record one of:\n"
          "  starters.harvest_decision: \"candidate:<new-starter-id>\"\n"
          "  starters.harvest_decision: \"declined: <why this pattern is not reusable>\"")
    return 1


def decide(contract_path, value):
    if not VALID.match(value):
        print("harvest: %r is not a recognised decision" % value)
        return 2
    if not os.path.isfile(contract_path):
        print("harvest: no contract at %s" % contract_path)
        return 2
    with open(contract_path, encoding="utf-8") as f:
        text = f.read()
    head, body, end = block(text, "starters")
    if head is None:
        print("harvest: no `starters:` block in the contract")
        return 2
    quoted = '"%s"' % value.replace('"', "'")
    if body is not None and re.search(r"^\s{2}harvest_decision:", body, re.M):
        new_body = re.sub(r"^(\s{2}harvest_decision:).*$", r"\1 " + quoted,
                          body, count=1, flags=re.M)
    elif "{" in head:                       # inline block: expand one line below
        new_body = "\n  harvest_decision: %s\n%s" % (quoted, body or "")
    else:
        new_body = (body or "").rstrip("\n") + "\n  harvest_decision: %s\n" % quoted
    start = text.index(head) + len(head)
    with open(contract_path, "w", encoding="utf-8") as f:
        f.write(text[:start] + new_body + text[end:])
    print("harvest: decision recorded — %s" % value)
    return 0


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "c.yaml")

        with open(path, "w", encoding="utf-8") as f:
            f.write('meta:\n  mode: quick\nstarters:\n  route: from_scratch\n'
                    '  chosen: ""\n\nstatus:\n  verdict: ready\n')
        if check(path) != 1:
            problems.append("a from_scratch run without a decision was let through")
        if decide(path, "candidate:landing-event") != 0:
            problems.append("--decide failed on a well-formed contract")
        if check(path) != 0:
            problems.append("a recorded decision was not accepted")
        with open(path, encoding="utf-8") as f:
            out = f.read()
        if "verdict: ready" not in out or "route: from_scratch" not in out:
            problems.append("--decide damaged the rest of the contract")

        with open(path, "w", encoding="utf-8") as f:
            f.write('starters: {route: starter_first, chosen: landing-local}\n')
        if check(path) != 1:
            problems.append("a starter_first run without a decision was let through")

        with open(path, "w", encoding="utf-8") as f:
            f.write('starters:\n  route: from_scratch\n  harvest_decision: "maybe later"\n')
        if check(path) != 1:
            problems.append("a free-text decision was accepted")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-harvest: %s" % p)
        return 1
    print("OK: dops-harvest self-test (decision required, taxonomy enforced, "
          "contract preserved)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--decide", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    contract = os.path.join(os.path.abspath(args.root), "artifacts",
                            "design-contract.yaml")
    if args.decide:
        return decide(contract, args.decide)
    return check(contract)


if __name__ == "__main__":
    sys.exit(main())
