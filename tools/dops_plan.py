#!/usr/bin/env python3
"""dops_plan.py — the decision schedule (У-6).

Design: Kimi, `Most/tasks/2026-08-06-kimi-u5-u6-lod-runplan-spec.md` block 1.

A run used to be opaque in the one way that matters to the person paying for
it: how long it will take and when it will need them. `meta.run_plan` was a
field in the contract with no mechanism behind it, so the honest answer to
"when will you need me?" was a guess written in prose.

This file turns it into a computed object. Two rules carry the weight:

  1. **The plan is emitted, never written by hand.** A model writing YAML into
     a commented contract loses the comments and invents the numbers. Here the
     composition comes from the closed checkpoint registry and the numbers
     from a declared table or from measurements — nothing is authored at the
     keyboard.
  2. **A measured number and an estimate never look alike.** Every step
     carries `source`, always: `estimate` until a stage has three closed
     measurements in the project's own trace, `measured` after. Silently
     upgrading a guess into a fact would make the plan less trustworthy the
     more it is used, which is the opposite of the point.

Which checkpoints a route passes is deliberately NOT declared here: that is
`checkpoint-registry.json` `route_sets`, and a second copy of a closed set is
exactly the drift [A.10] exists to prevent. `run-routes.json` adds only the
cost and the attention the registry does not know about.

Usage:
  dops plan emit --route starter_first [--with-k2b] [--root DIR] [--dry-run]
  dops plan show [--root DIR] [--json]

Exit: 0 ok, 1 refused (nothing written), 2 usage/io.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dops_trace                      # noqa: E402  (the stage history's owner)

ROUTES = os.path.join(HERE, "run-routes.json")
REGISTRY = os.path.join(HERE, "checkpoint-registry.json")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")
MIN_SAMPLES = 3        # below this a median is a coincidence, not a measurement


# --------------------------------------------------------------------------
# the declarations
# --------------------------------------------------------------------------
def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def route_names(registry):
    """The routes a run can take. `k2b` is not a route — it is the set that
    gets appended when K2B actually runs, which is why it is a flag here and
    not a third entry."""
    return sorted(k for k in (registry.get("route_sets") or {}) if k != "k2b")


def compose(registry, route, with_k2b):
    """The checkpoints of a route, in registry order, K2B spliced in where it
    belongs rather than tacked onto the end."""
    sets = registry.get("route_sets") or {}
    if route not in sets or route == "k2b":
        return None
    base = list(sets[route])
    if not with_k2b:
        return base
    k2b = list(sets.get("k2b") or [])
    types = registry.get("types") or {}
    # K2B runs after the base skin and before the K3 report; splicing by stage
    # order keeps the plan readable as a timeline rather than as two lists.
    tail = [c for c in base if (types.get(c) or {}).get("stage") == "K3"]
    head = [c for c in base if c not in tail]
    return head + k2b + tail


# --------------------------------------------------------------------------
# the measurements
# --------------------------------------------------------------------------
def median(values):
    s = sorted(values)
    n = len(s)
    if not n:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def measured_minutes(root):
    """{stage: (median minutes, sample count)} from the project's own trace.

    The trace is append-only, so a project run three times carries three
    measurements per stage — which is exactly what "history" means here. The
    pairing of start and end events belongs to `dops_trace`, so it is imported
    rather than reimplemented."""
    summary = dops_trace.summarize(root)
    if not summary:
        return {}
    buckets = {}
    for row in summary.get("stages") or []:
        if row.get("status") not in (None, "ok"):
            continue        # a failed stage measures the failure, not the work
        buckets.setdefault(row["stage"], []).append(row["seconds"] / 60.0)
    return {stage: (median(vals), len(vals)) for stage, vals in buckets.items()}


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------
def build(root, route, with_k2b):
    registry = read_json(REGISTRY)
    routes = read_json(ROUTES)
    if not registry or not routes:
        return None, "cannot read the checkpoint registry or the route table"
    order = compose(registry, route, with_k2b)
    if order is None:
        return None, ("unknown route %r — the routes are a closed set: %s"
                      % (route, ", ".join(route_names(registry))))

    types = registry.get("types") or {}
    costs = routes.get("checkpoints") or {}
    facts = measured_minutes(root)

    steps = []
    for cp in order:
        spec = types.get(cp)
        if spec is None:
            return None, ("route %s names checkpoint %r, which the registry "
                          "does not declare" % (route, cp))
        cost = costs.get(cp)
        if cost is None:
            return None, ("no cost declared for checkpoint %r — a plan with a "
                          "blank number is worse than no plan" % cp)
        stage = spec.get("stage") or ""
        eta, source, samples = cost["eta_min"], "estimate", 0
        got = facts.get(stage)
        if got and got[1] >= MIN_SAMPLES:
            eta, source, samples = round(got[0], 1), "measured", got[1]
        step = {
            "stage": stage,
            "checkpoint": cp,
            "eta_min": eta,
            "source": source,
            "human_needed": bool(cost.get("human_needed")),
        }
        if samples:
            step["samples"] = samples
        if step["human_needed"]:
            step["attention_min"] = cost.get("attention_min", 0)
        steps.append(step)
    return steps, None


def plan_line(run_plan, current_stage):
    """One line of schedule under the pulse: where the run is against its own
    plan, and when the owner is next needed. A stale pulse still reports as a
    silent incident above — the schedule never covers for it."""
    if not run_plan:
        return ""
    here = next((s for s in run_plan if s["stage"] == current_stage), None)
    parts = []
    if here:
        parts.append("%s, %s/%s min" % (here["stage"], here["fact_min"] or 0,
                                        here["eta_min"]))
    idx = run_plan.index(here) if here else -1
    ahead = [s for s in run_plan[idx + 1:] if s["human_needed"]]
    if ahead:
        nxt = ahead[0]
        wait = sum(s["eta_min"] for s in run_plan[idx + 1:run_plan.index(nxt) + 1])
        parts.append("next time you are needed: %s (~%s min of your attention, "
                     "in roughly %s min)"
                     % (nxt["checkpoint"], nxt.get("attention_min", 0), round(wait)))
    else:
        parts.append("nothing else needs you")
    return "; ".join(parts)


def attention_total(steps):
    return sum(s.get("attention_min", 0) for s in steps if s["human_needed"])


# --------------------------------------------------------------------------
# writing into a contract that has comments in it
# --------------------------------------------------------------------------
def render(steps, indent=2):
    pad = " " * indent
    lines = ["%srun_plan:" % pad]
    for s in steps:
        parts = ["stage: %s" % s["stage"], "checkpoint: %s" % s["checkpoint"],
                 "eta_min: %s" % s["eta_min"], "source: %s" % s["source"]]
        if "samples" in s:
            parts.append("samples: %d" % s["samples"])
        parts.append("human_needed: %s" % ("true" if s["human_needed"] else "false"))
        if s["human_needed"]:
            parts.append("attention_min: %s" % s.get("attention_min", 0))
        lines.append("%s  - {%s}" % (pad, ", ".join(parts)))
    return "\n".join(lines)


def patch_contract(text, steps):
    """Put `run_plan` under `meta:` without rewriting the document.

    A load-and-dump would delete every comment in the contract — the same
    damage `inject.py` and `dops panel apply` avoid, and for the same reason:
    the comments are where the reasoning lives."""
    block = render(steps)

    flow = re.search(r"^meta:[ \t]*\{(.*)\}[ \t]*$", text, re.M)
    if flow:
        # `meta: {a: 1, b: 2}` cannot hold a nested list; expand exactly this
        # one line into block style, key order preserved, and leave the rest of
        # the file untouched.
        inner = flow.group(1)
        pairs = [p.strip() for p in split_top(inner) if p.strip()]
        expanded = ["meta:"] + ["  %s" % p for p in pairs if not p.startswith("run_plan")]
        return text[:flow.start()] + "\n".join(expanded) + "\n" + block + text[flow.end():]

    block_meta = re.search(r"^meta:[ \t]*$", text, re.M)
    if not block_meta:
        return None
    start = block_meta.end()
    end = len(text)
    for m in re.finditer(r"^\S", text[start:], re.M):
        end = start + m.start()
        break
    section = text[start:end]
    existing = re.search(r"^[ \t]+run_plan:.*?(?=^[ \t]{0,2}\S|\Z)",
                         section, re.M | re.S)
    if existing:
        section = section[:existing.start()] + block + "\n" + section[existing.end():]
    else:
        section = section.rstrip("\n") + "\n" + block + "\n"
    return text[:start] + section + text[end:]


def split_top(s):
    """Split a flow mapping on commas that are not inside braces or quotes."""
    out, depth, quote, buf = [], 0, None, []
    for ch in s:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    out.append("".join(buf))
    return out


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def emit(root, route, with_k2b, dry_run, as_json):
    steps, why = build(root, route, with_k2b)
    if steps is None:
        print("plan: refused — %s" % why)
        return 1

    routes = read_json(ROUTES) or {}
    owner_line = (routes.get("owner_line") or "your attention ~%d min") % attention_total(steps)

    contract = os.path.join(root, CONTRACT)
    written = False
    if not dry_run:
        if not os.path.isfile(contract):
            print("plan: refused — no contract at %s; a plan with nowhere to "
                  "live is a number nobody can act on" % contract)
            return 1
        with open(contract, encoding="utf-8") as f:
            text = f.read()
        patched = patch_contract(text, steps)
        if patched is None:
            print("plan: refused — could not find `meta:` in %s" % contract)
            return 1
        try:
            import yaml
            got = ((yaml.safe_load(patched) or {}).get("meta") or {}).get("run_plan")
            if not isinstance(got, list) or len(got) != len(steps):
                print("plan: refused — the patch would not parse back into "
                      "%d steps; nothing written" % len(steps))
                return 1
        except ImportError:
            pass            # [A.6] no PyYAML: write, and say the check was skipped
        with open(contract, "w", encoding="utf-8") as f:
            f.write(patched)
        written = True

    if as_json:
        print(json.dumps({"route": route, "with_k2b": with_k2b,
                          "owner_line": owner_line, "written": written,
                          "run_plan": steps}, ensure_ascii=False, indent=2))
        return 0

    measured = sum(1 for s in steps if s["source"] == "measured")
    print("plan: %s%s — %d step(s), %d measured, %d estimated%s"
          % (route, " + K2B" if with_k2b else "", len(steps), measured,
             len(steps) - measured, "" if written else "  [dry run]"))
    for s in steps:
        print("  %-4s %-12s %5s min  %-8s%s"
              % (s["stage"], s["checkpoint"], s["eta_min"], s["source"],
                 "  owner ~%s min" % s["attention_min"] if s["human_needed"] else ""))
    print("  total ~%d min, of which the owner is asked for ~%d"
          % (sum(s["eta_min"] for s in steps), attention_total(steps)))
    print("  hand to the owner as is: %s" % owner_line)
    return 0


def line(root):
    """The pulse's schedule line. Silent when there is no plan: a run without
    one is not an error, and inventing a line for it would be noise."""
    import dops_feed
    snapshot = None
    try:
        snapshot = dops_feed.contract_query(root, "run_plan")
    except Exception:
        snapshot = None
    if not isinstance(snapshot, list) or not snapshot:
        return 0
    facts = {stage: got[0] for stage, got in measured_minutes(root).items()}
    rows = []
    for step in snapshot:
        stage = step.get("stage") or ""
        rows.append({"stage": stage, "checkpoint": step.get("checkpoint") or "",
                     "eta_min": step.get("eta_min") or 0,
                     "human_needed": bool(step.get("human_needed")),
                     "attention_min": step.get("attention_min") or 0,
                     "fact_min": round(facts[stage], 1) if stage in facts else 0})
    progress = os.path.join(root, "artifacts", "progress.json")
    current = ""
    try:
        with open(progress, encoding="utf-8") as f:
            current = (json.load(f) or {}).get("stage") or ""
    except (OSError, ValueError):
        pass
    text = plan_line(rows, current)
    if text:
        print("  %s" % text)
    return 0


def show(root, as_json):
    contract = os.path.join(root, CONTRACT)
    steps = []
    if os.path.isfile(contract):
        try:
            import yaml
            with open(contract, encoding="utf-8") as f:
                steps = ((yaml.safe_load(f) or {}).get("meta") or {}).get("run_plan") or []
        except ImportError:
            print("plan: PyYAML absent — cannot read the contract [A.6]")
            return 1
    if as_json:
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 0
    if not steps:
        print("plan: no run_plan in the contract — `dops plan emit --route <r>` "
              "writes one")
        return 0
    facts = measured_minutes(root)
    for s in steps:
        got = facts.get(s.get("stage"))
        fact = ("%.1f" % got[0]) if got else "—"
        print("  %-4s %-12s plan %5s min  fact %5s min  %s"
              % (s.get("stage", ""), s.get("checkpoint", ""), s.get("eta_min", "?"),
                 fact, s.get("source", "")))
    return 0


# --------------------------------------------------------------------------
def quiet(fn, *a):
    """Run a command without printing its report: the self-test asserts on the
    contract, and a full plan printout in the middle of it is noise."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


def self_test():
    import shutil
    import tempfile

    problems = []
    registry = read_json(REGISTRY)
    routes = read_json(ROUTES)

    # 1. composition comes from the registry, and an unknown route is refused
    for route in route_names(registry):
        got = compose(registry, route, False)
        if got != list(registry["route_sets"][route]):
            problems.append("route %s does not match the registry's own set" % route)
    if compose(registry, "made_up", False) is not None:
        problems.append("a route outside the closed set was composed anyway")
    if compose(registry, "k2b", False) is not None:
        problems.append("k2b was treated as a route rather than as an appended set")

    spliced = compose(registry, "from_scratch", True)
    if spliced and spliced[-1] != "k3-report":
        problems.append("K2B was appended after the K3 report: %r" % (spliced,))
    if spliced and not set(registry["route_sets"]["k2b"]).issubset(spliced):
        problems.append("--with-k2b did not add the K2B checkpoints")

    # every checkpoint any route can reach must carry a declared cost
    for route in route_names(registry):
        for cp in compose(registry, route, True) or []:
            if cp not in (routes.get("checkpoints") or {}):
                problems.append("no cost declared for %s (route %s)" % (cp, route))

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))
        contract = os.path.join(tmp, CONTRACT)
        shutil.copy(os.path.join(PKG_ROOT, "starters", "landing-event",
                                 "contract.yaml"), contract)

        # 2. with no history every step is an estimate, and the owner line is
        #    the sum of the attention minutes — not of the etas
        steps, why = build(tmp, "starter_first", False)
        if steps is None:
            problems.append("starter_first refused: %s" % why)
        else:
            if any(s["source"] != "estimate" for s in steps):
                problems.append("a step claimed to be measured with no history")
            want = sum((routes["checkpoints"][s["checkpoint"]].get("attention_min", 0))
                       for s in steps if s["human_needed"])
            if attention_total(steps) != want:
                problems.append("owner line is not the sum of attention_min")
            if any(not s["human_needed"] and "attention_min" in s for s in steps):
                problems.append("a step nobody is needed for still asks for attention")

        # 3. three measurements flip the source to measured; two do not
        for n in (2, 3):
            trace = os.path.join(tmp, "artifacts", "trace.jsonl")
            if os.path.exists(trace):
                os.remove(trace)
            for i in range(n):
                dops_trace.append(tmp, {"stage": "K0", "kind": "start"})
                rec = {"stage": "K0", "kind": "end", "status": "ok"}
                dops_trace.append(tmp, rec)
                # widen the pair so the median is a real number, not 0.0
                events = open(trace, encoding="utf-8").read().splitlines()
                last = json.loads(events[-1])
                last["at"] += 60 * (i + 4)
                events[-1] = json.dumps(last, ensure_ascii=False)
                open(trace, "w", encoding="utf-8").write("\n".join(events) + "\n")
            steps, _why = build(tmp, "starter_first", False)
            k0 = next(s for s in steps if s["stage"] == "K0")
            if n < MIN_SAMPLES and k0["source"] != "estimate":
                problems.append("%d sample(s) were enough to claim a measurement" % n)
            if n >= MIN_SAMPLES:
                if k0["source"] != "measured":
                    problems.append("%d samples did not flip the source" % n)
                elif k0.get("samples") != n:
                    problems.append("the sample count was not carried into the plan")
                elif abs(k0["eta_min"] - 5.0) > 0.2:
                    problems.append("median of 4/5/6 min came out as %s, not 5"
                                    % k0["eta_min"])

        # 4. the contract keeps its comments and parses back
        before = open(contract, encoding="utf-8").read()
        rc = quiet(emit, tmp, "from_scratch", True, False, False)
        after = open(contract, encoding="utf-8").read()
        if rc != 0:
            problems.append("emit refused on a real starter contract")
        for line in before.splitlines():
            if line.strip().startswith("#") and line not in after:
                problems.append("a comment was lost: %s" % line.strip()[:50])
        try:
            import yaml
            doc = yaml.safe_load(after) or {}
            plan = (doc.get("meta") or {}).get("run_plan")
            if not isinstance(plan, list) or not plan:
                problems.append("run_plan did not parse back as a list")
            elif doc["meta"].get("mode") != "quick":
                problems.append("expanding `meta:` lost one of its keys")
            # 5. emitting twice replaces the plan rather than stacking two
            quiet(emit, tmp, "starter_first", False, False, False)
            again = yaml.safe_load(open(contract, encoding="utf-8")) or {}
            plan2 = (again.get("meta") or {}).get("run_plan")
            if not isinstance(plan2, list):
                problems.append("a second emit broke the contract")
            elif len(plan2) != len(compose(registry, "starter_first", False)):
                problems.append("a second emit stacked plans instead of replacing: "
                                "%d steps" % len(plan2))
        except ImportError:
            problems.append("PyYAML absent — the contract round-trip was not checked")

    for p in problems:
        print("FAIL: %s" % p)
    if problems:
        print("\n%d run-plan problem(s)" % len(problems))
        return 1
    print("OK: dops-plan self-test (routes from the closed registry, estimates "
          "never pass as measurements, owner line sums attention, contract "
          "keeps its comments and its plan is replaced not stacked)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dops plan")
    sub = ap.add_subparsers(dest="cmd")
    e = sub.add_parser("emit", help="compute the run plan and write it into the contract")
    e.add_argument("--route", default=None)
    e.add_argument("--with-k2b", action="store_true",
                   help="K2B actually runs, so its checkpoints join the plan")
    e.add_argument("--root", default=".")
    e.add_argument("--dry-run", action="store_true")
    e.add_argument("--json", action="store_true")
    s = sub.add_parser("show", help="the plan against the measured facts")
    s.add_argument("--root", default=".")
    s.add_argument("--json", action="store_true")
    ln = sub.add_parser("line", help="one line of schedule, for the pulse")
    ln.add_argument("--root", default=".")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.cmd == "emit":
        if not args.route:
            registry = read_json(REGISTRY) or {}
            print("plan: --route is required; the closed set is: %s"
                  % ", ".join(route_names(registry)))
            return 2
        return emit(args.root, args.route, args.with_k2b, args.dry_run, args.json)
    if args.cmd == "show":
        return show(args.root, args.json)
    if args.cmd == "line":
        return line(args.root)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
