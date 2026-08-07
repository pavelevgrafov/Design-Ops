#!/usr/bin/env python3
"""dops_trace.py — run instrumentation (P0).

Before this, `cost.actual` was prose ("1 сессия сквозного теста"). What is
not measured cannot be managed: every speed claim about the pipeline was
unfalsifiable. This writes NUMBERS, and the SCRIPT writes them, not the
model.

Usage:
  python3 tools/dops_trace.py start <stage> [--root DIR] [--note TEXT]
  python3 tools/dops_trace.py end   <stage> [--root DIR] [--status ok|fail]
  python3 tools/dops_trace.py mark  <event> [--root DIR] [--note TEXT]
  python3 tools/dops_trace.py report [--root DIR] [--json]
  python3 tools/dops_trace.py cost   [--root DIR] [--write]
  python3 tools/dops_trace.py --self-test

Stages are free-form; the pipeline uses K0 K1 gate1 K2A K3 K2B deliver.
Trace lands in artifacts/trace.jsonl; token estimates are read from
artifacts/context-log.jsonl (written by context-budget.py).

Exit: 0 ok, 1 nothing to report, 2 usage.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

TRACE = os.path.join("artifacts", "trace.jsonl")
CONTEXT_LOG = os.path.join("artifacts", "context-log.jsonl")
HERE = os.path.dirname(os.path.abspath(__file__))
PROGRESS_PY = os.path.join(os.path.dirname(HERE), ".agents", "skills",
                           "pipeline-orchestrator", "scripts", "progress.py")


def beat(root, stage, kind, note=""):
    """One event, two views: `trace.jsonl` is the history the cost and the
    gate-wait metrics are computed from; `progress.json` is the current state
    the owner (or a dashboard) reads. They are written by the SAME call —
    two separate calls per event would drift apart within a day."""
    if not os.path.isfile(PROGRESS_PY):
        return "progress.py not present — history recorded, pulse skipped"
    substep = note or {"start": "stage started", "end": "stage finished",
                       "mark": "checkpoint"}.get(kind, kind)
    cmd = [sys.executable or "python3", PROGRESS_PY, "beat",
           "--stage", stage, "--substep", substep]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "pulse not written: %s" % exc
    if proc.returncode != 0:
        return "pulse not written: %s" % (proc.stderr or "").strip()[:120]
    return None


def append(root, record):
    path = os.path.join(root, TRACE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    record["at"] = time.time()
    record["at_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def load(root):
    path = os.path.join(root, TRACE)
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


def tokens_read(root):
    path = os.path.join(root, CONTEXT_LOG)
    if not os.path.isfile(path):
        return None, 0
    total, files = 0, 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += int(rec.get("est_tokens") or 0)
            files += 1
    return total, files


def summarize(root):
    events = load(root)
    if not events:
        return None
    stages, open_stages = [], {}
    for e in events:
        if e.get("kind") == "start":
            open_stages[e["stage"]] = e
        elif e.get("kind") == "end":
            started = open_stages.pop(e["stage"], None)
            if started:
                stages.append({
                    "stage": e["stage"],
                    "seconds": round(e["at"] - started["at"], 1),
                    "status": e.get("status", "ok"),
                })
    marks = [e for e in events if e.get("kind") == "mark"]
    wall = round(events[-1]["at"] - events[0]["at"], 1)
    tokens, files = tokens_read(root)
    return {
        "started_at": events[0]["at_iso"],
        "ended_at": events[-1]["at_iso"],
        "wall_clock_s": wall,
        "stages": stages,
        "unclosed_stages": sorted(open_stages),
        "marks": [{"event": m["stage"], "note": m.get("note", "")} for m in marks],
        "instruction_tokens_est": tokens,
        "instruction_files": files,
    }


def process_metrics(root, summary):
    """The §7 metrics of the visibility design: they exist so "the owner lost
    control" stops being an impression and becomes a number. Anything not
    computable here is reported as None, never guessed."""
    import json as _json

    def jsonl(name):
        path = os.path.join(root, "artifacts", name)
        rows = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(_json.loads(line))
                        except ValueError:
                            continue
        return rows

    checkpoints = jsonl("checkpoints.jsonl")
    control = jsonl("control-queue.jsonl")
    events_ = load(root)

    # blind zone: how long the owner saw nothing at all
    blind = None
    first_cp = next((e for e in checkpoints if e.get("event") == "publish"), None)
    if first_cp and events_:
        try:
            t0 = events_[0]["at"]
            t1 = time.mktime(time.strptime(first_cp["at"], "%Y-%m-%dT%H:%M:%S"))
            blind = round(max(0.0, (t1 - t0) / 60.0), 1)
        except (ValueError, KeyError, OverflowError):
            blind = None

    # visible decisions: machine decisions announced at the moment
    machine, announced = 0, 0
    for e in checkpoints:
        if e.get("event") != "decide":
            continue
        d = e.get("decision") or {}
        if d.get("decided_by") == "machine":
            machine += 1
            announced += 1 if d.get("announced_at") else 0
    visible = round(100.0 * announced / machine, 1) if machine else None

    issued = [c for c in control if c.get("event") == "issue"]

    # [У-5] depth against the agreed depth. Absent rather than zero when the
    # run never declared one: a fabricated 0 would read as "nothing was built".
    lod = None
    try:
        import dops_lod
        lod = dops_lod.metrics(root)
    except Exception:                                     # noqa: BLE001
        lod = None

    return {
        "lod": lod,
        "blind_zone_min": blind,
        "checkpoints_published": sum(1 for e in checkpoints
                                     if e.get("event") == "publish"),
        "machine_decisions": machine,
        "visible_decisions_pct": visible,
        "control_usage": len(issued),
        "targets": {"blind_zone_min": "<=10 (standard)",
                    "visible_decisions_pct": "100",
                    "control_usage": ">0 means the owner actually steered"},
    }


def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    return "%dm%02ds" % (m, s) if m else "%ds" % s


def cost_line(root, summary):
    facts = []
    facts.append("wall-clock %s" % fmt_duration(summary["wall_clock_s"]))
    if summary["instruction_tokens_est"] is not None:
        facts.append("~%dk tokens of instructions read over %d file(s)"
                     % (round(summary["instruction_tokens_est"] / 1000.0),
                        summary["instruction_files"]))
    else:
        facts.append("instruction tokens not logged (context-log.jsonl absent)")
    if summary["stages"]:
        slowest = max(summary["stages"], key=lambda s: s["seconds"])
        facts.append("slowest stage %s %s"
                     % (slowest["stage"], fmt_duration(slowest["seconds"])))
    return "; ".join(facts) + " [measured by dops_trace]"


def write_cost(root, line):
    """Surgical single-line edit of `cost.actual` — no YAML dependency, and
    nothing else in the contract is touched."""
    path = os.path.join(root, "artifacts", "design-contract.yaml")
    if not os.path.isfile(path):
        return False, "contract not found: %s" % path
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^cost:\s*$", text, re.M)
    if not m:
        return False, "no `cost:` block in the contract"
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    block_end = m.end() + (stop.start() if stop else len(tail))
    block = text[m.end():block_end]
    quoted = '"%s"' % line.replace('"', "'")
    if re.search(r"^\s{2}actual:.*$", block, re.M):
        new_block = re.sub(r"^(\s{2}actual:).*$", r"\1 " + quoted.replace("\\", "\\\\"),
                           block, count=1, flags=re.M)
    else:
        new_block = block.rstrip("\n") + "\n  actual: %s\n" % quoted
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:m.end()] + new_block + text[block_end:])
    return True, path


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        append(tmp, dict(kind="start", stage="K1"))
        time.sleep(0.01)
        append(tmp, dict(kind="end", stage="K1", status="ok"))
        s = summarize(tmp)
        if not s or len(s["stages"]) != 1 or s["stages"][0]["stage"] != "K1":
            problems.append("start/end pair did not produce one closed stage")
        append(tmp, dict(kind="start", stage="K3"))
        s = summarize(tmp)
        if s["unclosed_stages"] != ["K3"]:
            problems.append("an unclosed stage was not reported")
        # one event must produce BOTH views, or they drift apart
        problem = beat(tmp, "K1", "start", "self-test")
        pulse = os.path.join(tmp, "artifacts", "progress.json")
        if problem is None and not os.path.isfile(pulse):
            problems.append("a traced event did not write the pulse")
        elif problem is None:
            with open(pulse, encoding="utf-8") as f:
                if json.load(f).get("stage") != "K1":
                    problems.append("the pulse recorded a different stage")

        os.makedirs(os.path.join(tmp, "artifacts"), exist_ok=True)
        with open(os.path.join(tmp, "artifacts", "design-contract.yaml"),
                  "w", encoding="utf-8") as f:
            f.write("meta:\n  mode: quick\ncost:\n  estimate: \"quick, ~15 мин\"\n"
                    "  actual: \"1 сессия\"\n\nstatus:\n  verdict: ready\n")
        ok, _ = write_cost(tmp, cost_line(tmp, s))
        if not ok:
            problems.append("write_cost failed on a well-formed contract")
        else:
            with open(os.path.join(tmp, "artifacts", "design-contract.yaml"),
                      encoding="utf-8") as f:
                out = f.read()
            if "1 сессия" in out:
                problems.append("cost.actual prose stub survived the write")
            if "wall-clock" not in out:
                problems.append("cost.actual has no measured number")
            if "verdict: ready" not in out or "mode: quick" not in out:
                problems.append("write_cost damaged the rest of the contract")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-trace: %s" % p)
        return 1
    print("OK: dops-trace self-test (stage pairing, unclosed stages, "
          "cost.actual is a measured number)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?",
                    choices=["start", "end", "mark", "report", "cost"])
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--root", default=".")
    ap.add_argument("--note", default="")
    ap.add_argument("--status", default="ok")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.command:
        ap.print_help()
        return 2
    root = os.path.abspath(args.root)

    if args.command in ("start", "end", "mark"):
        if not args.stage:
            print("usage: dops_trace.py %s <stage>" % args.command)
            return 2
        rec = dict(kind=args.command, stage=args.stage)
        if args.command == "end":
            rec["status"] = args.status
        if args.note:
            rec["note"] = args.note
        append(root, rec)
        problem = beat(root, args.stage, args.command, args.note)
        print("trace %s %s%s" % (args.command, args.stage,
                                 "" if not problem else "  (%s)" % problem))
        # [У-5] a closed stage is the only moment the depth actually changes,
        # so it is the only writer of `status.lod` — and the moment to offer
        # the owner the rest of the ladder, with its price, if the run is
        # about to end below what was agreed. It runs AFTER the trace line so
        # a published checkpoint reads as a consequence of the stage ending,
        # which is what it is.
        if args.command == "end" and args.status == "ok":
            try:
                import dops_lod
                note = dops_lod.on_stage_end(root, args.stage)
            except Exception as exc:                      # noqa: BLE001
                note = "depth not recorded: %s" % exc
            if note:
                print("  (%s)" % note)
        return 0

    summary = summarize(root)
    if not summary:
        print("no trace recorded (%s absent) — start stages with "
              "`dops stage start <name>`" % TRACE)
        return 1

    if args.command == "report":
        summary["process_metrics"] = process_metrics(root, summary)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        print("run trace — %s → %s (%s total)"
              % (summary["started_at"], summary["ended_at"],
                 fmt_duration(summary["wall_clock_s"])))
        for s in summary["stages"]:
            print("  %-8s %-8s %s" % (s["stage"], fmt_duration(s["seconds"]),
                                      s["status"]))
        if summary["unclosed_stages"]:
            print("  unclosed: %s" % ", ".join(summary["unclosed_stages"]))
        if summary["instruction_tokens_est"] is not None:
            print("  instructions read: ~%d tokens over %d file(s)"
                  % (summary["instruction_tokens_est"],
                     summary["instruction_files"]))
        m = summary["process_metrics"]
        print("  visibility: %s checkpoint(s) published, blind zone %s min, "
              "%s machine decision(s) (%s%% announced), %d control command(s)"
              % (m["checkpoints_published"],
                 m["blind_zone_min"] if m["blind_zone_min"] is not None else "n/a",
                 m["machine_decisions"],
                 m["visible_decisions_pct"] if m["visible_decisions_pct"] is not None else "n/a",
                 m["control_usage"]))
        lod = m.get("lod")
        if lod and lod.get("lod"):
            print("  depth: LOD-%s%s; %s"
                  % (lod["lod"],
                     "" if not lod["lod_mismatch"] else "  [lod_mismatch: %s]"
                     % lod["lod_mismatch"],
                     lod["lod_mismatch_note"]))
        return 0

    line = cost_line(root, summary)
    if not args.write:
        print(line)
        print("(add --write to record it into contract cost.actual)")
        return 0
    ok, where = write_cost(root, line)
    print(("cost.actual written → %s" if ok else "cost.actual NOT written: %s")
          % where)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
