#!/usr/bin/env python3
"""dops_checkpoint.py — checkpoints (У-2): a published artifact the owner can
act on, without stopping the conveyor.

Design: Kimi, `Most/tasks/2026-08-04-kimi-checkpoints-control-queue-mechanics.md`.

The run used to have one window — the final report. Checkpoints turn every
intermediate artifact into a window with a handle: publish it the moment it
exists, list what the owner may do with it, and keep working (gate-overtaking,
A.25). A checkpoint carrying no actions is a status line — the illusion of
control — and this tool refuses to publish one.

Storage: `artifacts/checkpoints.jsonl`, append-only. Checkpoints are EVENTS
with a chronology (published → acted → superseded), which is what a log is
for; the contract holds state, the log holds history, exactly as the
changelog and the decision log already do. `contract-read.py checkpoints`
reads this log, so the contract stays the single entry point [A.10] without
being rewritten (and losing its comments) on every publish.

Usage:
  dops checkpoint publish  --id sitemap --artifact artifacts/sitemap.html
                           [--provisional] [--note "5 экранов, 1 роль"]
  dops checkpoint decide   --id sitemap --action accept [--args '{"n":2}']
                           [--pin-ref annotations.json#3]
                           [--by owner|machine] [--announced]
  dops checkpoint supersede --id sitemap --reason "rolled back"
  dops checkpoint list [--json]
  dops checkpoint --check            # D19 rules
  dops checkpoint --self-test

Exit: 0 ok, 1 rejected / defect found, 2 usage.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REGISTRY = os.path.join(HERE, "checkpoint-registry.json")
PROGRESS_PY = os.path.join(PKG, ".agents", "skills", "pipeline-orchestrator",
                           "scripts", "progress.py")
LOG = os.path.join("artifacts", "checkpoints.jsonl")

PUBLISHED, ACTED, SUPERSEDED = "published", "acted", "superseded"


def registry():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def append(root, record):
    path = os.path.join(root, LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def events(root):
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


def state(root):
    """Fold the event log into the current state of each checkpoint."""
    cur = {}
    for e in events(root):
        cid = e.get("id")
        if e.get("event") == "publish":
            cur[cid] = {"id": cid, "stage": e.get("stage"),
                        "artifact": e.get("artifact"),
                        "provisional": e.get("provisional", False),
                        "published_at": e.get("at"), "status": PUBLISHED,
                        "decision": None}
        elif e.get("event") == "decide" and cid in cur:
            cur[cid]["status"] = ACTED
            cur[cid]["decision"] = e.get("decision")
        elif e.get("event") == "supersede" and cid in cur:
            cur[cid]["status"] = SUPERSEDED
            cur[cid]["superseded_reason"] = e.get("reason")
    return cur


def pulse(root, name):
    if not os.path.isfile(PROGRESS_PY):
        return
    try:
        subprocess.run([sys.executable or "python3", PROGRESS_PY,
                        "checkpoint", "--name", name],
                       cwd=root, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pass


def publish(root, cid, artifact, provisional, note):
    reg = registry()
    spec = reg["types"].get(cid)
    if not spec:
        print("checkpoint: unknown type %r — the registry is a CLOSED list "
              "(%s). Add the type to tools/checkpoint-registry.json and to the "
              "D19 rules, or use an existing one."
              % (cid, ", ".join(sorted(reg["types"]))))
        return 2
    if not spec["actions"]:
        print("checkpoint: %s has no actions — a checkpoint without actions is "
              "a status line, not a checkpoint" % cid)
        return 2

    record = {"event": "publish", "at": now(), "id": cid,
              "stage": spec["stage"], "artifact": artifact or spec["artifact"],
              "provisional": bool(provisional), "actions": spec["actions"]}
    if note:
        record["note"] = note
    append(root, record)

    marker = " (предварительно — гейт ещё не подтверждён)" if provisional else ""
    label = "%s%s" % (cid, marker)
    pulse(root, label)
    print("Причал: %s — %s%s" % (cid, note or record["artifact"], marker))
    print("  [%s]" % "] [".join(spec["actions"]))
    if provisional:
        print("  Я иду дальше (обгон). Вернуться к этому решению можно в "
              "любой момент — работа помечена как непринятая.")
    return 0


def decide(root, cid, action, args, pin_ref, by, announced):
    reg = registry()
    spec = reg["types"].get(cid)
    if not spec:
        print("checkpoint: unknown type %r" % cid)
        return 2
    if action not in spec["actions"]:
        print("checkpoint: %r is not an action of %s (allowed: %s)"
              % (action, cid, ", ".join(spec["actions"])))
        return 2

    cur = state(root).get(cid)
    if not cur:
        print("checkpoint: %s was never published — nothing to decide" % cid)
        return 1
    if cur["status"] == SUPERSEDED:
        print("checkpoint: %s is superseded (%s) — the artifact it referred to "
              "no longer exists in that form. Act on the republished one."
              % (cid, cur.get("superseded_reason", "")))
        return 1

    if by == "machine" and not announced:
        print("checkpoint: a machine decision must be announced at the moment "
              "it is made, with a rollback command [A.26]. Run "
              "`dops announce --gate <g> --decision <d> --rollback \"...\"` "
              "first, then repeat with --announced.")
        return 1

    decision = {"action": action, "args": json.loads(args) if args else {},
                "pin_ref": pin_ref or None, "decided_by": by,
                "decided_at": now(),
                "announced_at": now() if (by == "machine" and announced) else None}
    append(root, {"event": "decide", "at": now(), "id": cid,
                  "decision": decision})
    extra = ""
    if spec.get("is_gate") and action in ("accept", "choose", "merge"):
        extra = ("  — это же и есть пакетное подтверждение %s и всей работы, "
                 "сделанной в обгоне" % spec["is_gate"])
    print("checkpoint %s: %s by %s%s" % (cid, action, by, extra))
    return 0


def supersede(root, cid, reason):
    cur = state(root).get(cid)
    if not cur:
        print("checkpoint: %s was never published" % cid)
        return 1
    append(root, {"event": "supersede", "at": now(), "id": cid,
                  "reason": reason or "artifact rebuilt"})
    print("checkpoint %s superseded: %s" % (cid, reason or "artifact rebuilt"))
    return 0


def check(root):
    """D19 rules for checkpoints."""
    reg = registry()
    problems = []
    seen_status = {}
    for e in events(root):
        cid = e.get("id")
        if e.get("event") == "publish":
            if cid not in reg["types"]:
                problems.append("%s: not in the closed registry" % cid)
            seen_status[cid] = PUBLISHED
        elif e.get("event") == "supersede":
            seen_status[cid] = SUPERSEDED
        elif e.get("event") == "decide":
            d = e.get("decision") or {}
            if seen_status.get(cid) == SUPERSEDED:
                problems.append(
                    "%s: a decision was recorded on a SUPERSEDED checkpoint — "
                    "the owner acted on an artifact that no longer exists in "
                    "that form" % cid)
            if d.get("decided_by") == "machine" and not d.get("announced_at"):
                problems.append(
                    "%s: machine decision without announced_at — the owner "
                    "would have learned about it from the closing report "
                    "[A.26]" % cid)
            spec = reg["types"].get(cid) or {}
            if spec and d.get("action") not in (spec.get("actions") or []):
                problems.append("%s: action %r is outside the closed list"
                                % (cid, d.get("action")))
            seen_status[cid] = ACTED
    if problems:
        for p in problems:
            print("checkpoints FAIL: %s" % p)
        return 1
    n = len(state(root))
    print("checkpoints pass: %d published, no undeclared machine decisions, "
          "no action on a superseded artifact" % n)
    return 0


def show(root, as_json):
    cur = state(root)
    if as_json:
        print(json.dumps(list(cur.values()), ensure_ascii=False, indent=2))
        return 0
    if not cur:
        print("no checkpoints published yet")
        return 0
    for c in cur.values():
        d = c.get("decision") or {}
        print("  %-16s %-11s %-9s %s"
              % (c["id"], c["status"],
                 d.get("action") or "—",
                 ("provisional" if c.get("provisional") else "")))
    return 0


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        # 1. publishing a checkpoint
        if publish(tmp, "sitemap", "artifacts/sitemap.html", True, "5 экранов") != 0:
            problems.append("a valid checkpoint was not published")
        if state(tmp)["sitemap"]["status"] != PUBLISHED:
            problems.append("published checkpoint has the wrong status")
        # 2. the registry is closed
        if publish(tmp, "invented-type", "x", False, "") != 2:
            problems.append("an unregistered checkpoint type was accepted")
        # 3. accept on a gate checkpoint = batched gate confirmation
        if decide(tmp, "sitemap", "accept", None, None, "owner", False) != 0:
            problems.append("an owner accept was rejected")
        if state(tmp)["sitemap"]["status"] != ACTED:
            problems.append("a decided checkpoint did not become `acted`")
        # 4. an action outside the closed list
        if decide(tmp, "sitemap", "choose", None, None, "owner", False) != 2:
            problems.append("an action outside the checkpoint's list was accepted")
        # 5. amend carries a pin reference
        publish(tmp, "base-skin", "artifacts/audit/screenshots", False, "")
        if decide(tmp, "base-skin", "amend", None, "annotations.json#3",
                  "owner", False) != 0:
            problems.append("amend with a pin reference was rejected")
        # 6. machine decision without an announcement
        publish(tmp, "k3-report", "artifacts/audit/quality-report.md", False, "")
        if decide(tmp, "k3-report", "accept-verdict", None, None,
                  "machine", False) != 1:
            problems.append("an unannounced machine decision was accepted [A.26]")
        if decide(tmp, "k3-report", "accept-verdict", None, None,
                  "machine", True) != 0:
            problems.append("an announced machine decision was rejected")
        if check(tmp) != 0:
            problems.append("a clean log failed the D19 check")
        # 7. acting on a superseded checkpoint
        publish(tmp, "skeleton", "skeleton.html", False, "")
        supersede(tmp, "skeleton", "rolled back to brief")
        if decide(tmp, "skeleton", "accept", None, None, "owner", False) != 1:
            problems.append("a decision on a superseded checkpoint was accepted")
        # 8. the D19 rule catches a forged log
        append(tmp, {"event": "decide", "at": now(), "id": "skeleton",
                     "decision": {"action": "accept", "decided_by": "machine",
                                  "announced_at": None}})
        if check(tmp) != 1:
            problems.append("the D19 check missed a forged machine decision")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-checkpoint: %s" % p)
        return 1
    print("OK: dops-checkpoint self-test (closed registry, gate accept, pins, "
          "A.26 announcement, superseded refusal, D19 rules)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?",
                    choices=["publish", "decide", "supersede", "list"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--id", dest="cid", default=None)
    ap.add_argument("--artifact", default=None)
    ap.add_argument("--action", default=None)
    ap.add_argument("--args", default=None)
    ap.add_argument("--pin-ref", dest="pin_ref", default=None)
    ap.add_argument("--by", default="owner", choices=["owner", "machine"])
    ap.add_argument("--announced", action="store_true")
    ap.add_argument("--provisional", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.check:
        return check(root)
    if args.command == "list" or not args.command:
        return show(root, args.json)
    if not args.cid:
        print("usage: dops checkpoint %s --id <type>" % args.command)
        return 2
    if args.command == "publish":
        return publish(root, args.cid, args.artifact, args.provisional, args.note)
    if args.command == "decide":
        if not args.action:
            print("usage: dops checkpoint decide --id <type> --action <action>")
            return 2
        return decide(root, args.cid, args.action, args.args, args.pin_ref,
                      args.by, args.announced)
    return supersede(root, args.cid, args.reason)


if __name__ == "__main__":
    sys.exit(main())
