#!/usr/bin/env python3
"""dops_handoff.py — build the context packet for a stage subagent (P3).

One continuous context for a whole run grows monotonically: by K3 the agent
still carries K0's brief, the skeleton, every token file and every
screenshot — and pays for all of it on every remaining turn. This makes the
context FLAT instead: each stage runs fresh with exactly the packet built
here (rule card + its slice of the contract + its inputs, outputs and
acceptance command) and hands back its artifact plus a short summary.

Usage:
  python3 tools/dops_handoff.py <K0|K1|K2A|K2B|K3|deliver> [--root DIR]
                                [--out PATH] [--stdout]
  python3 tools/dops_handoff.py --list
  python3 tools/dops_handoff.py --check <stage> [--root DIR]
  python3 tools/dops_handoff.py --self-test

Exit: 0 ok, 1 over budget / missing output, 2 usage.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
STAGES = os.path.join(HERE, "stages.json")
CARD = os.path.join(PKG, ".agents", "RULES.card.md")


def load_stages():
    with open(STAGES, encoding="utf-8") as f:
        return json.load(f)


def contract_slice(path, sections):
    """Copy whole top-level YAML blocks verbatim. No parser, no PyYAML, no
    risk of a lossy round-trip: the packet quotes the contract, it does not
    re-render it."""
    if not os.path.isfile(path):
        return None, ["contract not found: %s" % path]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    out, missing = [], []
    for name in sections:
        m = re.search(r"^%s:.*$" % re.escape(name), text, re.M)
        if not m:
            missing.append(name)
            continue
        tail = text[m.end():]
        stop = re.search(r"^\S", tail, re.M)
        block = tail[:stop.start()] if stop else tail
        out.append(m.group(0) + block.rstrip() + "\n")
    return "\n".join(out), missing


def build(stage, root):
    spec = load_stages()["stages"][stage]
    notes = []

    card = ""
    if os.path.isfile(CARD):
        with open(CARD, encoding="utf-8") as f:
            card = f.read()
    else:
        notes.append("RULES.card.md absent — run `dops card`")

    contract_path = os.path.join(root, "artifacts", "design-contract.yaml")
    sliced, missing = contract_slice(contract_path, spec["contract_sections"])
    if sliced is None:
        notes.append(missing[0])
        sliced = "# (no contract yet — this stage creates it)"
    elif missing:
        notes.append("contract sections not present yet: %s" % ", ".join(missing))

    packet = """# Handoff packet — stage %s (%s)

You run this stage and nothing else. This packet is your whole context: do
not go looking for the rest of the run. Hand back the artifacts listed under
"Produce" plus a summary of at most ten lines.

## Job

%s

## Produce

%s

## Read (inputs)

%s

## Do NOT read

%s

Reading these costs context on every turn that follows and changes nothing
about this stage's output. If you genuinely cannot proceed without one, say
so in the summary instead of reading it silently.

## Acceptance — run this before handing back

```
%s
```

## Contract slice

```yaml
%s```

---

%s""" % (
        stage, spec["role"],
        spec["job"],
        "\n".join("- %s" % o for o in spec["outputs"]),
        "\n".join("- %s" % i for i in spec["inputs"]),
        "\n".join("- %s" % d for d in spec["do_not_read"]),
        spec["acceptance"],
        sliced,
        card or "_(rule card missing)_",
    )
    return packet, notes


def check(stage, root):
    """Did the stage actually produce what it promised?"""
    spec = load_stages()["stages"][stage]
    missing = []
    for out in spec["outputs"]:
        if out.startswith("contract") or out.startswith("status.") \
                or out.startswith("the "):
            continue                    # contract fields: D19 owns those
        candidate = out.split(" ")[0]
        if not os.path.exists(os.path.join(root, candidate)):
            missing.append(candidate)
    if missing:
        print("%s: not produced yet: %s" % (stage, ", ".join(missing)))
        return 1
    print("%s: all declared outputs present" % stage)
    return 0


def self_test():
    data = load_stages()
    problems = []
    budget = data["budget_tokens"]
    for stage, spec in data["stages"].items():
        for key in ("role", "job", "contract_sections", "inputs", "outputs",
                    "acceptance", "do_not_read"):
            if not spec.get(key):
                problems.append("%s: missing %s" % (stage, key))
        packet, _ = build(stage, os.path.join(PKG, "eval", "selftest"))
        approx = len(packet) // 4
        if approx > budget:
            problems.append("%s packet ~%d tokens, budget %d"
                            % (stage, approx, budget))
        if "Do NOT read" not in packet:
            problems.append("%s packet lost its exclusion list" % stage)
    # the whole point: a stage packet must be far smaller than the old
    # resident set (AGENTS.md + four SKILL.md)
    resident = sum(os.path.getsize(p) for p in
                   [os.path.join(PKG, "AGENTS.md")] +
                   [os.path.join(PKG, ".agents", "skills", s, "SKILL.md")
                    for s in ("pipeline-orchestrator", "structure-builder",
                              "visual-director", "quality-guardian")]) // 4
    biggest = max(len(build(s, PKG)[0]) // 4 for s in data["stages"])
    if biggest >= resident:
        problems.append("a stage packet (~%d) is no smaller than the old "
                        "resident set (~%d)" % (biggest, resident))
    if problems:
        for p in problems:
            print("self-test FAIL: dops-handoff: %s" % p)
        return 1
    print("OK: dops-handoff self-test (%d stages, largest packet ~%d tokens "
          "vs ~%d resident before)" % (len(data["stages"]), biggest, resident))
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    data = load_stages()
    if args.list:
        for stage, spec in data["stages"].items():
            print("%-8s %s" % (stage, spec["role"]))
        return 0

    root = os.path.abspath(args.root)
    if args.check:
        if args.check not in data["stages"]:
            print("unknown stage: %s" % args.check)
            return 2
        return check(args.check, root)

    if not args.stage or args.stage not in data["stages"]:
        print("usage: dops handoff <%s>" % "|".join(data["stages"]))
        return 2

    packet, notes = build(args.stage, root)
    approx = len(packet) // 4
    if args.stdout:
        print(packet)
    else:
        out = args.out or os.path.join(root, "artifacts", "handoff",
                                       "%s.md" % args.stage)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(packet)
        print("handoff packet → %s (~%d tokens, budget %d)"
              % (out, approx, data["budget_tokens"]))
    for n in notes:
        print("  note: %s" % n)
    return 1 if approx > data["budget_tokens"] else 0


if __name__ == "__main__":
    sys.exit(main())
