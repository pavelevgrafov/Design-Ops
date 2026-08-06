#!/usr/bin/env python3
"""dops_hash.py — reuse and invalidation by input hash ([E.3], for real).

[E.3] has been in the rules since v5: "artifacts are not regenerated if
their inputs did not change; on a change request, recompute only downstream
of the changed input." Nothing implemented it — no artifact stored the hash
of its inputs — so every change request meant rebuilding everything, and a
gate veto could never be cheap.

Three questions this answers mechanically:

  fresh?    `dops hash check`  — which artifacts still match their inputs
  drifted?  same command       — which were hand-edited after generation
                                 (silent drift = defect [A.10])
  scope?    `dops hash plan X` — given X changed, what must be recomputed,
                                 in order, and what is safe to reuse

Usage:
  python3 tools/dops_hash.py record [--root DIR] [--artifact P] [--stage S]
  python3 tools/dops_hash.py check  [--root DIR] [--json]
  python3 tools/dops_hash.py plan <changed-input> [--root DIR]
  python3 tools/dops_hash.py --self-test

Exit: 0 all fresh / plan printed, 1 stale or drifted artifacts, 2 usage.
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
GRAPH = os.path.join(HERE, "hash-graph.json")
MANIFEST = os.path.join("artifacts", "hashes.json")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")

FRESH, STALE, DRIFTED, ABSENT, UNRECORDED = (
    "fresh", "stale", "drifted", "absent", "unrecorded")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()[:16]


def sha_file(path):
    try:
        with open(path, "rb") as f:
            return sha_bytes(f.read())
    except OSError:
        return None


def sha_dir(path):
    h = hashlib.sha256()
    if not os.path.isdir(path):
        return None
    for dirpath, dirnames, files in os.walk(path):
        dirnames.sort()
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            h.update(os.path.relpath(fp, path).encode())
            try:
                with open(fp, "rb") as f:
                    h.update(f.read())
            except OSError:
                continue
    return h.hexdigest()[:16]


def contract_section(root, name):
    path = os.path.join(root, CONTRACT)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^%s:.*$" % re.escape(name), text, re.M)
    if not m:
        return None
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    block = tail[:stop.start()] if stop else tail
    # normalise trailing whitespace so reformatting is not a "change"
    body = "\n".join(l.rstrip() for l in (m.group(0) + block).splitlines()
                     if l.strip())
    return sha_bytes(body.encode("utf-8"))


def hash_input(root, spec):
    """None means 'this input does not exist here' — recorded as such, so an
    input that later appears counts as a change rather than passing unnoticed."""
    if spec.startswith("contract:"):
        return contract_section(root, spec.split(":", 1)[1])
    path = spec if os.path.isabs(spec) else os.path.join(root, spec)
    if spec.endswith("/"):
        return sha_dir(path)
    if os.path.isdir(path):
        return sha_dir(path)
    return sha_file(path)


def load_graph():
    with open(GRAPH, encoding="utf-8") as f:
        return json.load(f)


def load_manifest(root):
    path = os.path.join(root, MANIFEST)
    if not os.path.isfile(path):
        return {"schema": "dops-hashes/1", "artifacts": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"schema": "dops-hashes/1", "artifacts": {}}


def save_manifest(root, manifest):
    path = os.path.join(root, MANIFEST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def record(root, graph, manifest, only_artifact=None, only_stage=None):
    written = []
    for name, spec in graph["artifacts"].items():
        if only_artifact and name != only_artifact:
            continue
        if only_stage and only_stage not in spec.get("stage", ""):
            continue
        own = hash_input(root, name)
        if own is None:
            continue                     # nothing produced — nothing to pin
        manifest["artifacts"][name] = {
            "stage": spec.get("stage", ""),
            "self": own,
            "inputs": {i: hash_input(root, i) for i in spec["inputs"]},
        }
        written.append(name)
    return written


def status_of(root, graph, manifest, name):
    spec = graph["artifacts"][name]
    own = hash_input(root, name)
    if own is None:
        return ABSENT, ""
    rec = manifest["artifacts"].get(name)
    if not rec:
        return UNRECORDED, "never pinned — run `dops hash record`"
    changed = [i for i in spec["inputs"]
               if rec["inputs"].get(i) != hash_input(root, i)]
    if changed:
        return STALE, "inputs changed: %s" % ", ".join(changed)
    if rec.get("self") != own:
        return DRIFTED, "edited by hand after generation — silent drift [A.10]"
    return FRESH, ""


def downstream(graph, changed):
    """Everything that must be recomputed, in derivation order. An artifact is
    affected when the change is one of its inputs, directly or through another
    affected artifact."""
    affected, order = set(), []
    frontier = {changed}
    progress = True
    while progress:
        progress = False
        for name, spec in graph["artifacts"].items():
            if name in affected:
                continue
            if any(i in frontier for i in spec["inputs"]):
                affected.add(name)
                order.append(name)
                frontier.add(name)
                progress = True
    return order


def self_test():
    import tempfile
    problems = []
    graph = load_graph()
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts", "visual"))
        with open(os.path.join(tmp, CONTRACT), "w", encoding="utf-8") as f:
            f.write("product:\n  name: demo\nexperience:\n  primary_job: x\n"
                    "content_model:\n  pattern: task-first\nvisual:\n  base_skin: base-site\n"
                    "acceptance:\n  target_viewports: [390]\n")
        with open(os.path.join(tmp, "skeleton.html"), "w", encoding="utf-8") as f:
            f.write("<h1>demo</h1>")
        with open(os.path.join(tmp, "artifacts", "visual", "tokens.json"),
                  "w", encoding="utf-8") as f:
            f.write('{"color": {"$value": "#123456"}}')
        with open(os.path.join(tmp, "artifacts", "visual", "tokens.css"),
                  "w", encoding="utf-8") as f:
            f.write(":root{--x:1}")

        manifest = load_manifest(tmp)
        record(tmp, graph, manifest)
        save_manifest(tmp, manifest)

        st, _ = status_of(tmp, graph, manifest, "skeleton.html")
        if st != FRESH:
            problems.append("a just-recorded artifact is not fresh (%s)" % st)

        # a hand edit of a generated artifact is drift, not a change
        with open(os.path.join(tmp, "artifacts", "visual", "tokens.css"),
                  "a", encoding="utf-8") as f:
            f.write("\n.x{color:red}")
        st, _ = status_of(tmp, graph, manifest, "artifacts/visual/tokens.css")
        if st != DRIFTED:
            problems.append("a hand-edited generated artifact was not "
                            "reported as drift (%s)" % st)

        # a contract section change invalidates only what derives from it
        with open(os.path.join(tmp, CONTRACT), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(tmp, CONTRACT), "w", encoding="utf-8") as f:
            f.write(text.replace("primary_job: x", "primary_job: something else"))
        st, _ = status_of(tmp, graph, manifest, "skeleton.html")
        if st != STALE:
            problems.append("an experience change did not invalidate the "
                            "skeleton (%s)" % st)
        st, _ = status_of(tmp, graph, manifest, "artifacts/visual/tokens.json")
        if st != FRESH:
            problems.append("an experience change wrongly invalidated tokens "
                            "(%s) — structure and taste must stay independent" % st)

        # whitespace-only reformatting of the contract is not a change
        with open(os.path.join(tmp, CONTRACT), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(tmp, CONTRACT), "w", encoding="utf-8") as f:
            f.write(text.replace("visual:\n", "visual:   \n\n"))
        st, _ = status_of(tmp, graph, manifest, "artifacts/visual/tokens.json")
        if st != FRESH:
            problems.append("reformatting the contract counted as a change (%s)" % st)

    order = downstream(graph, "artifacts/visual/tokens.json")
    if "artifacts/visual/tokens.css" not in order:
        problems.append("plan misses the direct consumer of tokens.json")
    if "artifacts/audit/floor.json" not in order:
        problems.append("plan misses the transitive consumer (floor via CSS)")
    if "skeleton.html" in order:
        problems.append("plan rebuilds the structure after a token change — "
                        "a restyle never rebuilds structure [A.7]")

    if problems:
        for p in problems:
            print("self-test FAIL: dops-hash: %s" % p)
        return 1
    print("OK: dops-hash self-test (freshness, drift, targeted invalidation, "
          "reformatting is not a change)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", choices=["record", "check", "plan"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--root", default=".")
    ap.add_argument("--artifact", default=None)
    ap.add_argument("--stage", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.command:
        ap.print_help()
        return 2

    root = os.path.abspath(args.root)
    graph = load_graph()
    manifest = load_manifest(root)

    if args.command == "record":
        written = record(root, graph, manifest, args.artifact, args.stage)
        path = save_manifest(root, manifest)
        print("pinned %d artifact(s) → %s" % (len(written), path))
        for name in written:
            print("  %s" % name)
        return 0

    if args.command == "plan":
        if not args.target:
            print("usage: dops hash plan <changed-input>")
            return 2
        order = downstream(graph, args.target)
        if not order:
            print("nothing derives from %s — no recomputation needed"
                  % args.target)
            return 0
        print("%s changed → recompute in this order:" % args.target)
        for i, name in enumerate(order, 1):
            print("  %d. %-38s (%s)" % (i, name,
                                        graph["artifacts"][name].get("stage", "")))
        reusable = [n for n in graph["artifacts"] if n not in order]
        print("reuse unchanged: %s" % (", ".join(reusable) or "—"))
        return 0

    results = {}
    for name in graph["artifacts"]:
        st, why = status_of(root, graph, manifest, name)
        results[name] = {"status": st, "reason": why}

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for name, r in results.items():
            if r["status"] == ABSENT:
                continue
            print("  %-10s %-38s %s" % (r["status"], name, r["reason"]))
    bad = [n for n, r in results.items()
           if r["status"] in (STALE, DRIFTED, UNRECORDED)]
    if not args.json:
        print("%d artifact(s) need attention" % len(bad) if bad
              else "all recorded artifacts are fresh")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
