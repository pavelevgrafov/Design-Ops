#!/usr/bin/env python3
"""dops_control.py — the control queue (У-3): commands to the PROCESS, not
only to the product.

Design: Kimi, `Most/tasks/2026-08-04-kimi-checkpoints-control-queue-mechanics.md` §2.

The owner could always ask for changes to the artifact. What was missing was
a way to steer the run itself — speed it up, pause it, roll it back, cut
scope, go deeper — without waiting for it to finish. Commands are queued from
chat, panel or a pin, and executed ONLY at control points (a stage script
finishing, a checkpoint publishing, a stage starting). Never mid-script:
a command applied halfway through leaves a half-written artifact.

Storage: `artifacts/control-queue.jsonl`, append-only — commands are events
with a resolution, same reasoning as the checkpoint log.

Usage:
  dops control issue --command speed_up [--args '{"...":"..."}']
                     [--source chat|panel|pin]
  dops control apply [--at <control-point name>]   # at a control point only
  dops control list [--json]
  dops control --self-test

Exit: 0 ok, 1 something rejected, 2 usage.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dops_hash                                   # noqa: E402
import dops_checkpoint                             # noqa: E402

LOG = os.path.join("artifacts", "control-queue.jsonl")

# Which commands contend for the same setting: a later one supersedes an
# earlier one in the same topic. "The owner's latest explicit instruction
# beats all" — the doctrine already in the conflict order.
TOPIC = {
    "speed_up": "mode",
    "pause": "mode",
    "resume": "mode",
    "stop_after_checkpoint": "mode",
    "skip_scope": "scope",
    "deepen_lod": "lod",
    "rollback_to": None,          # not a setting: a one-shot action
    "report_now": None,
}
COMMANDS = sorted(TOPIC)

# [E.4] budgets never downgrade blocking checks — scope cuts cannot reach the
# core floor, no matter who asks.
CORE_PROTECTED = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
                  "D11", "D12", "D13", "D14", "D16", "D17", "D18", "D19",
                  "D20", "D21", "core", "floor", "contrast", "a11y"}


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
    cur = {}
    for e in events(root):
        cid = e.get("id")
        if e.get("event") == "issue":
            cur[cid] = dict(e, status="queued")
        elif cid in cur:
            cur[cid]["status"] = e.get("event")        # applied|rejected|superseded
            cur[cid]["resolved_at"] = e.get("at")
            cur[cid]["reason"] = e.get("reason")
    return cur


def issue(root, command, args, source):
    if command not in TOPIC:
        print("control: unknown command %r (known: %s)"
              % (command, ", ".join(COMMANDS)))
        return 2
    parsed = json.loads(args) if args else {}
    cur = state(root)
    seq = len(cur) + 1
    cid = "cq-%03d" % seq

    # a later command in the same topic supersedes the earlier queued ones
    topic = TOPIC[command]
    if topic:
        for other_id, other in cur.items():
            if other["status"] != "queued":
                continue
            if TOPIC.get(other["command"]) == topic:
                append(root, {"event": "superseded", "at": now(),
                              "id": other_id,
                              "reason": "superseded by %s (%s): the owner's "
                                        "latest instruction wins" % (cid, command)})

    append(root, {"event": "issue", "at": now(), "id": cid, "command": command,
                  "args": parsed, "source": source})
    print("%s queued: %s%s — will be applied at the next control point, never "
          "mid-script" % (cid, command, (" %s" % parsed) if parsed else ""))
    return 0


def apply_one(root, cmd):
    """Return (ok: bool, message). Only mechanical effects happen here; the
    orchestrator reads the applied commands and honours them."""
    command, args = cmd["command"], cmd.get("args") or {}

    if command == "rollback_to":
        target = args.get("checkpoint")
        if not target:
            return False, "rollback_to needs {checkpoint: <id>}"
        cps = dops_checkpoint.state(root)
        cp = cps.get(target)
        if not cp:
            return False, "checkpoint %r was never published" % target
        if cp["status"] == dops_checkpoint.SUPERSEDED:
            return False, ("checkpoint %r is already superseded — it no longer "
                           "names a state to return to" % target)
        manifest = dops_hash.load_manifest(root)
        if not manifest.get("artifacts"):
            # honest degradation [A.6]: without hashes a rollback is a full
            # rebuild, and pretending otherwise would hide the cost
            return False, ("hash-graph unavailable (no artifacts/hashes.json) — "
                           "run `dops hash record` during the run, otherwise a "
                           "rollback costs a full recompute")
        artifact = cp.get("artifact") or ""
        graph = dops_hash.load_graph()
        order = dops_hash.downstream(graph, artifact)
        # everything published after the target is no longer current
        superseded = []
        seen_target = False
        for cid_, c in cps.items():
            if cid_ == target:
                seen_target = True
                continue
            if seen_target and c["status"] != dops_checkpoint.SUPERSEDED:
                dops_checkpoint.supersede(root, cid_, "rollback to %s" % target)
                superseded.append(cid_)
        return True, ("rolled back to %s — recompute: %s; reuse everything "
                      "else; checkpoints superseded: %s"
                      % (target, ", ".join(order) or "nothing downstream",
                         ", ".join(superseded) or "none"))

    if command == "skip_scope":
        what = str(args.get("what") or "")
        if not what:
            return False, "skip_scope needs {what: <screen|flow|check>}"
        words = {w.strip(".,:;()").lower() for w in what.split()}
        protected = {t.lower() for t in CORE_PROTECTED} | {"ядро", "пол"}
        hit = words & protected
        if hit:
            return False, ("the core floor cannot be cut [E.4] — budgets never "
                           "downgrade blocking checks (matched: %s). Name a "
                           "screen or a flow instead; if the scope genuinely is "
                           "a screen whose name collides, rephrase it."
                           % ", ".join(sorted(hit)))
        return True, "scope exclusion recorded: %s (with reason, in the contract)" % what

    if command == "speed_up":
        return True, ("from here: quick profile (core floor intact), gates "
                      "delegated VISIBLY — every delegation is announced at the "
                      "moment [A.26], K2B deferred")

    if command == "stop_after_checkpoint":
        cp = args.get("checkpoint") or "next"
        return True, "the conveyor stops after checkpoint %s — not mid-stage" % cp

    if command == "deepen_lod":
        lod = args.get("lod")
        if lod not in (100, 200, 300, 400):
            return False, "deepen_lod needs {lod: 100|200|300|400}"
        scope = args.get("scope")
        return True, ("target LOD %s%s — the next checkpoint carries its price"
                      % (lod, (" for %s" % scope) if scope else " globally"))

    if command == "pause":
        return True, "paused at the nearest control point"
    if command == "resume":
        return True, "resumed — the plateau is cleared"
    if command == "report_now":
        return True, "an out-of-band report will be produced at the next control point"
    return False, "no handler for %r" % command


def apply_queued(root, at):
    cur = state(root)
    queued = [c for c in cur.values() if c["status"] == "queued"]
    if not queued:
        print("control: nothing queued%s" % (" at %s" % at if at else ""))
        return 0
    rejected = 0
    for cmd in sorted(queued, key=lambda c: c["id"]):
        ok, message = apply_one(root, cmd)
        append(root, {"event": "applied" if ok else "rejected", "at": now(),
                      "id": cmd["id"], "reason": message,
                      "control_point": at or ""})
        print("%s %s: %s" % (cmd["id"], "применён" if ok else "отклонён", message))
        rejected += 0 if ok else 1
    return 1 if rejected else 0


def show(root, as_json):
    cur = state(root)
    if as_json:
        print(json.dumps(list(cur.values()), ensure_ascii=False, indent=2))
        return 0
    if not cur:
        print("control queue empty")
        return 0
    for c in sorted(cur.values(), key=lambda x: x["id"]):
        print("  %-8s %-22s %-11s %s" % (c["id"], c["command"], c["status"],
                                         (c.get("reason") or "")[:70]))
    return 0


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))

        if issue(tmp, "not_a_command", None, "chat") != 2:
            problems.append("an unknown command was queued")

        issue(tmp, "speed_up", None, "chat")
        issue(tmp, "pause", None, "chat")          # same topic → supersedes
        st = state(tmp)
        if st["cq-001"]["status"] != "superseded":
            problems.append("a later command in the same topic did not "
                            "supersede the earlier one")

        # core floor cannot be cut
        issue(tmp, "skip_scope", '{"what": "D3 contrast"}', "chat")
        apply_queued(tmp, "test")
        st = state(tmp)
        cut = [c for c in st.values() if c["command"] == "skip_scope"][0]
        if cut["status"] != "rejected":
            problems.append("a scope cut reaching the core floor was applied [E.4]")

        # rollback without a hash graph degrades honestly
        dops_checkpoint.publish(tmp, "sitemap", "skeleton.html", False, "")
        issue(tmp, "rollback_to", '{"checkpoint": "sitemap"}', "chat")
        apply_queued(tmp, "test")
        st = state(tmp)
        rb = [c for c in st.values() if c["command"] == "rollback_to"][0]
        if rb["status"] != "rejected" or "hash-graph unavailable" not in (rb.get("reason") or ""):
            problems.append("rollback without hashes did not degrade honestly [A.6]")

        # with hashes it works, and supersedes later checkpoints
        with open(os.path.join(tmp, "skeleton.html"), "w", encoding="utf-8") as f:
            f.write("<h1>x</h1>")
        os.makedirs(os.path.join(tmp, "artifacts", "visual"), exist_ok=True)
        with open(os.path.join(tmp, "artifacts", "visual", "tokens.json"),
                  "w", encoding="utf-8") as f:
            f.write("{}")
        manifest = dops_hash.load_manifest(tmp)
        dops_hash.record(tmp, dops_hash.load_graph(), manifest)
        dops_hash.save_manifest(tmp, manifest)
        dops_checkpoint.publish(tmp, "base-skin", "artifacts/visual/tokens.json",
                                False, "")
        issue(tmp, "rollback_to", '{"checkpoint": "sitemap"}', "chat")
        apply_queued(tmp, "test")
        if dops_checkpoint.state(tmp)["base-skin"]["status"] != dops_checkpoint.SUPERSEDED:
            problems.append("rollback did not supersede the later checkpoint")

        # a bad LOD value is refused
        issue(tmp, "deepen_lod", '{"lod": 250}', "chat")
        apply_queued(tmp, "test")
        bad = [c for c in state(tmp).values() if c["command"] == "deepen_lod"][0]
        if bad["status"] != "rejected":
            problems.append("an out-of-scale LOD was accepted")

    if problems:
        for p in problems:
            print("self-test FAIL: dops-control: %s" % p)
        return 1
    print("OK: dops-control self-test (closed command set, topic supersession, "
          "core floor protected [E.4], rollback via hash-graph with honest "
          "degradation [A.6])")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", choices=["issue", "apply", "list"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--command", dest="cmd", default=None)
    ap.add_argument("--args", default=None)
    ap.add_argument("--source", default="chat", choices=["chat", "panel", "pin"])
    ap.add_argument("--at", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.command == "issue":
        if not args.cmd:
            print("usage: dops control issue --command <%s>" % "|".join(COMMANDS))
            return 2
        return issue(root, args.cmd, args.args, args.source)
    if args.command == "apply":
        return apply_queued(root, args.at)
    return show(root, args.json)


if __name__ == "__main__":
    sys.exit(main())
