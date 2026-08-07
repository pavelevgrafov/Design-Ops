#!/usr/bin/env python3
"""dops_feed.py — the status feeds (П-6): one for the edits, one for the run.

Design: Kimi, `Most/tasks/2026-08-06-kimi-p6-status-feed-spec.md`.

The pin statuses and the run pulse both existed already. What was missing was
**aggregation**: to understand ten pins the owner had to open ten pins, and to
understand the run they had to ask in chat. A status re-request is an
interruption, and interruptions are the thing this whole wave is removing.

Two machine feeds, no second copy of any data:

  dops pins feed --json     the edits: summary + one row per pin
  dops status --json        the run: pulse, plan, checkpoints, queue, pins

Schema stability is a promise, not a side effect: a section with no data comes
back as an empty list or a zero, never missing. A widget that has to guess
whether a key exists starts inventing meanings for its absence.

The one rule that shapes the rows: **a status line without an action is an
illusion of control.** Every row carries the pin it belongs to and, when it is
waiting, what it is waiting for.

Exit: 0 ok, 1 nothing to read, 2 usage.
"""
import argparse
import datetime
import json
import os
import subprocess
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

STATUS_FILE = os.path.join(HERE, "pin-status.json")
PINS = os.path.join("artifacts", "pins.json")
ANNOTATIONS = os.path.join("artifacts", "annotations.json")
PROGRESS = os.path.join("artifacts", "progress.json")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")
CONTRACT_READ = os.path.join(PKG_ROOT, ".agents", "skills",
                             "pipeline-orchestrator", "scripts", "contract-read.py")
DEFAULT_MAX_AGE_MIN = 3.0


def load_statuses():
    with open(STATUS_FILE, encoding="utf-8") as f:
        return json.load(f)["statuses"]


STATUSES = load_statuses()
WAITING = {name for name, spec in STATUSES.items() if spec.get("waiting")}


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value)[:19])
    except ValueError:
        return None


def minutes_since(value, ref=None):
    ts = parse_ts(value)
    if ts is None:
        return None
    ref = ref or datetime.datetime.now()
    return round(max(0.0, (ref - ts).total_seconds() / 60.0), 1)


def median(values):
    """A pin without both timestamps stays out of the median rather than
    contributing a fabricated zero — an invented 0s latency would make the
    whole number look better than the run was."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    if len(vals) % 2:
        return round(vals[mid], 1)
    return round((vals[mid - 1] + vals[mid]) / 2.0, 1)


def seconds_between(a, b):
    ta, tb = parse_ts(a), parse_ts(b)
    if ta is None or tb is None:
        return None
    return max(0.0, (tb - ta).total_seconds())


# --------------------------------------------------------------------------
# the edits feed
# --------------------------------------------------------------------------
def last_event(pin):
    """One line of history: what happened to this pin most recently. A row
    that only shows a state leaves the owner asking how it got there."""
    if pin.get("status") == "superseded":
        return "checked → superseded by %s" % (pin.get("superseded_by") or "?")
    if pin.get("apply_error"):
        return "apply failed → checked"
    if pin.get("status") == "applied":
        return "checked → applied"
    check = pin.get("check") or {}
    if check.get("verdict"):
        return "classified → %s" % check["verdict"]
    if pin.get("lane"):
        return "new → triaged (lane %s)" % pin["lane"]
    return "new"


def pin_row(pin, ref=None):
    check = pin.get("check") or {}
    status = pin.get("status") or "new"
    return {
        "id": pin.get("id") or "",
        "status": status,
        "mark": (STATUSES.get(status) or {}).get("mark", "•"),
        "lane": pin.get("lane") or "",
        "kind": pin.get("kind") or "",
        "text": pin.get("text") or "",
        "selector": pin.get("selector") or pin.get("target_selector") or "",
        "created_at": pin.get("created_at") or "",
        "age_min": minutes_since(pin.get("created_at"), ref),
        "waiting": status in WAITING,
        "last_event": last_event(pin),
        "question": check.get("question"),
        "reason": check.get("reason"),
        "alternatives": check.get("alternatives") or [],
        "superseded_by": pin.get("superseded_by"),
        "apply_error": pin.get("apply_error"),
    }


def pins_feed(root, as_json, ref=None):
    store = read_json(os.path.join(root, PINS))
    raw = read_json(os.path.join(root, ANNOTATIONS)) or []
    known = {}
    for pin in (store or {}).get("pins", []):
        if pin.get("id"):
            known[pin["id"]] = pin
    # A pin exported but not yet swept is still part of the picture: leaving it
    # out would show the owner a shorter list than the one they are looking at.
    for pin in raw if isinstance(raw, list) else []:
        if isinstance(pin, dict) and pin.get("id") and pin["id"] not in known:
            known[pin["id"]] = pin

    rows = [pin_row(p, ref) for p in known.values()]
    rows.sort(key=lambda r: (not r["waiting"], r["created_at"]), reverse=False)
    rows.sort(key=lambda r: (not r["waiting"], ), reverse=False)

    to_classified, to_checked, to_applied = [], [], []
    for pin in known.values():
        check = pin.get("check") or {}
        born = pin.get("created_at")
        to_classified.append(seconds_between(born, pin.get("classified_at")))
        to_checked.append(seconds_between(born, check.get("checked_at")))
        to_applied.append(seconds_between(born, pin.get("applied_at")))

    summary = {
        "total": len(rows),
        "waiting_on_owner": sum(1 for r in rows if r["waiting"]),
        "applied": sum(1 for r in rows if r["status"] == "applied"),
        "rejected": sum(1 for r in rows if r["status"] == "rejected"),
        "superseded": sum(1 for r in rows if r["status"] == "superseded"),
        "in_flight": sum(1 for r in rows if r["status"] in
                         ("new", "triaged", "checked", "executing")),
        # A refusal offering alternatives is not "waiting" in the ribbon sense
        # (the conveyor is not blocked), but somebody does have to choose. The
        # widget gets its own counter rather than a status quietly reclassified.
        "needs_choice": sum(1 for r in rows
                            if r["status"] == "rejected" and r["alternatives"]),
        "apply_errors": sum(1 for r in rows if r["apply_error"]),
        # If a pin has been waiting for half an hour, the feed is not being
        # seen. That is a signal to rethink the surface, not to nudge the
        # owner — so it is counted rather than turned into a notification.
        "waiting_over_30min": sum(1 for r in rows if r["waiting"]
                                  and (r["age_min"] or 0) > 30),
        "median_latency_s": {
            "to_classified": median(to_classified),
            "to_checked": median(to_checked),
            "to_applied": median(to_applied),
        },
    }
    feed = {"generated_at": (ref or datetime.datetime.now()).isoformat(timespec="seconds"),
            "schema": "dops-pins-feed/1", "summary": summary, "pins": rows}

    if as_json:
        print(json.dumps(feed, ensure_ascii=False, indent=2))
        return 0
    print("pins: %d total · %d waiting on you · %d applied · %d rejected"
          % (summary["total"], summary["waiting_on_owner"], summary["applied"],
             summary["rejected"]))
    for r in rows:
        print("  %s %-10s %-7s %s" % (r["mark"], r["status"], r["id"],
                                      (r["text"] or "")[:56]))
        if r["waiting"] and r["question"]:
            print("       needs you: %s" % r["question"][:100])
    return 0


# --------------------------------------------------------------------------
# the run feed
# --------------------------------------------------------------------------
def fold_log(path):
    """Append-only event logs, folded to the latest state per id — the same
    reading contract-read.py applies, so the two never disagree."""
    out = {}
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            key = row.get("id") or row.get("name")
            if key:
                out[key] = {**out.get(key, {}), **row}
    return list(out.values())


def contract_query(root, query):
    """The contract is read through its single door [A.10]. No pyyaml means no
    answer — reported as empty, never guessed at with a regex."""
    contract = os.path.join(root, CONTRACT)
    if not os.path.isfile(contract) or not os.path.isfile(CONTRACT_READ):
        return None
    try:
        r = subprocess.run([sys.executable, CONTRACT_READ, contract, query],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return [l for l in r.stdout.splitlines() if l.strip()]


def pulse_freshness(root, max_age_min):
    """Share of the run during which the pulse was alive. Computed from the
    gaps between recorded beats: a gap longer than the threshold is time the
    owner could not tell whether anything was happening. Fewer than two beats
    means there is nothing to measure — reported as None, never as 100%."""
    path = os.path.join(root, "artifacts", "trace.jsonl")
    beats = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                # dops_trace writes `at` as an epoch float and `at_iso`
                # beside it; progress.py writes ISO. Read both rather
                # than assume the shape of a log this file does not own.
                ts = parse_ts(row.get("at_iso") or row.get("at")
                              or row.get("ts"))
                if ts:
                    beats.append(ts)
    beats.sort()
    if len(beats) < 2:
        return None
    total = alive = 0.0
    for a, b in zip(beats, beats[1:]):
        gap = (b - a).total_seconds() / 60.0
        total += gap
        alive += min(gap, max_age_min)
    return round(100.0 * alive / total, 1) if total else None


def status_feed(root, as_json, max_age_min, ref=None):
    ref = ref or datetime.datetime.now()
    pulse_raw = read_json(os.path.join(root, PROGRESS)) or {}
    age = minutes_since(pulse_raw.get("updated_at"), ref)
    pulse = {
        "stage": pulse_raw.get("stage") or "",
        "substep": pulse_raw.get("substep") or "",
        "next": pulse_raw.get("next_checkpoint") or "",
        "human_needed_at": pulse_raw.get("human_needed_at") or "",
        "tokens": pulse_raw.get("tokens_used") or 0,
        "beat_at": pulse_raw.get("updated_at") or "",
        "age_min": age,
        # A stale pulse is a silent incident. It is reported, never hidden:
        # "data from yesterday" without a marker is worse than no widget.
        "fresh": bool(age is not None and age <= max_age_min),
    }

    # The checkpoint log is folded by the module that writes it, not by a
    # second reader here: `published/acted/superseded` is a closed taxonomy
    # [A.11], and a private copy of the fold would drift from it silently.
    checkpoints = []
    try:
        import dops_checkpoint
        folded = dops_checkpoint.state(root)
    except Exception:                                   # noqa: BLE001
        folded = {}
    for cid, row in folded.items():
        checkpoints.append({
            "id": cid or "",
            "status": row.get("status") or "",
            "provisional": bool(row.get("provisional")),
            "at": row.get("published_at") or "",
            "acted": row.get("status") == dops_checkpoint.ACTED,
        })
    if not checkpoints:
        for row in pulse_raw.get("checkpoints") or []:
            checkpoints.append({"id": row.get("name") or row.get("id") or "",
                                "status": row.get("status") or "",
                                "provisional": False, "at": row.get("at") or "",
                                "acted": False})

    queue = fold_log(os.path.join(root, "artifacts", "control-queue.jsonl"))
    control = {
        "queued": sum(1 for r in queue if r.get("status") == "queued"),
        "applied": sum(1 for r in queue if r.get("status") == "applied"),
        "refused": sum(1 for r in queue if r.get("status") == "refused"),
    }

    plan_raw = contract_query(root, "run_plan")
    # У-6: the plan is what was promised, the trace is what happened. Joining
    # them here rather than storing `fact_min` in the contract keeps one writer
    # per fact [A.10] — `dops stage end` already records the measurement, and a
    # copy in the contract would be the number that goes stale.
    facts = {}
    try:
        import dops_plan
        facts = {stage: got[0] for stage, got in dops_plan.measured_minutes(root).items()}
    except Exception:
        facts = {}
    run_plan = []
    if isinstance(plan_raw, list):
        for step in plan_raw:
            if isinstance(step, dict):
                stage = step.get("stage") or ""
                row = {
                    "stage": stage,
                    "checkpoint": step.get("checkpoint") or "",
                    "eta_min": step.get("eta_min") or 0,
                    "source": step.get("source") or "estimate",
                    "human_needed": bool(step.get("human_needed")),
                    "fact_min": round(facts[stage], 1) if stage in facts else 0,
                }
                if row["human_needed"]:
                    row["attention_min"] = step.get("attention_min") or 0
                run_plan.append(row)

    store = read_json(os.path.join(root, PINS)) or {"pins": []}
    rows = [pin_row(p, ref) for p in store.get("pins", [])]
    pins_summary = {
        "total": len(rows),
        "waiting_on_owner": sum(1 for r in rows if r["waiting"]),
        "in_flight": sum(1 for r in rows if r["status"] in
                         ("new", "triaged", "checked", "executing")),
    }

    snapshot = {
        "pulse_freshness": pulse_freshness(root, max_age_min),
        "generated_at": ref.isoformat(timespec="seconds"),
        "schema": "dops-status-feed/1",
        "pulse": pulse,
        "run_plan": run_plan,
        "checkpoints": checkpoints,
        "control_queue": control,
        "pins_summary": pins_summary,
    }
    if as_json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0 if pulse["fresh"] else 1

    print("status: %s | stage %s (%s) | pulse age %s min | %d checkpoint(s) | "
          "%d pin(s) waiting"
          % ("alive" if pulse["fresh"] else "SILENT INCIDENT",
             pulse["stage"] or "?", pulse["substep"] or "—",
             "?" if age is None else age, len(checkpoints),
             pins_summary["waiting_on_owner"]))
    line = schedule_line(run_plan, pulse.get("stage"))
    if line:
        print("  %s" % line)
    return 0 if pulse["fresh"] else 1




# --------------------------------------------------------------------------
# acceptance probes
# --------------------------------------------------------------------------
GA = os.path.join(PKG_ROOT, ".agents", "skills", "pipeline-orchestrator",
                  "assets", "gate-annotate.js")

def schedule_line(run_plan, current_stage):
    """Delegated to dops_plan, which owns the schedule [A.10]."""
    try:
        import dops_plan
    except ImportError:
        return ""
    return dops_plan.plan_line(run_plan, current_stage)


SUMMARY_KEYS = {"total", "waiting_on_owner", "applied", "rejected", "superseded",
                "in_flight", "needs_choice", "apply_errors", "median_latency_s",
                "waiting_over_30min"}
SNAPSHOT_KEYS = {"generated_at", "schema", "pulse", "run_plan", "checkpoints",
                 "control_queue", "pins_summary", "pulse_freshness"}


def _capture(fn, *a, **kw):
    import io as _io
    buf, real = _io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        fn(*a, **kw)
    finally:
        sys.stdout = real
    return json.loads(buf.getvalue())


def _js_statuses():
    """Parse the marks and the waiting set out of gate-annotate.js. The JS
    cannot import this file — it runs from file:// with zero dependencies — so
    the duplication is deliberate and this is the test that holds it."""
    import re
    src = open(GA, encoding="utf-8").read()
    marks, waiting = {}, set()
    m = re.search(r"var STATUS_MARK = \{(.*?)\};", src, re.S)
    if m:
        for name, mark in re.findall(r"'?([A-Za-z_]+)'?\s*:\s*'([^']+)'", m.group(1)):
            marks[name] = mark
    m = re.search(r"var NEEDS_OWNER = \{(.*?)\};", src, re.S)
    if m:
        for name in re.findall(r"([A-Za-z_]+)\s*:\s*1", m.group(1)):
            waiting.add(name)
    return marks, waiting


def self_test():
    import tempfile
    problems = []
    ref = datetime.datetime(2026, 8, 6, 12, 0, 0)

    def project(tmp, pins=None, progress=None, checkpoints=None, queue=None):
        os.makedirs(os.path.join(tmp, "artifacts"), exist_ok=True)
        if pins is not None:
            with open(os.path.join(tmp, PINS), "w", encoding="utf-8") as f:
                json.dump({"schema": "dops-pins/1", "pins": pins}, f, ensure_ascii=False)
        if progress is not None:
            with open(os.path.join(tmp, PROGRESS), "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False)
        if checkpoints:
            with open(os.path.join(tmp, "artifacts", "checkpoints.jsonl"),
                      "w", encoding="utf-8") as f:
                for row in checkpoints:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if queue:
            with open(os.path.join(tmp, "artifacts", "control-queue.jsonl"),
                      "w", encoding="utf-8") as f:
                for row in queue:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return tmp

    # 1. the schema is stable on an empty project and on a full one
    with tempfile.TemporaryDirectory() as tmp:
        project(tmp, pins=[])
        empty = _capture(pins_feed, tmp, True, ref)
        if set(empty["summary"]) != SUMMARY_KEYS:
            problems.append("the empty feed's summary keys differ from the full one's")
        if empty["pins"] != []:
            problems.append("an empty project produced pin rows")
    with tempfile.TemporaryDirectory() as tmp:
        project(tmp, pins=[
            {"id": "a-0001", "status": "applied", "lane": "A", "text": "опечатка",
             "created_at": "2026-08-06T11:00:00", "classified_at": "2026-08-06T11:00:04",
             "applied_at": "2026-08-06T11:01:01",
             "check": {"verdict": "pass", "checked_at": "2026-08-06T11:00:09"}},
            {"id": "a-0002", "status": "clarify", "lane": "A", "text": "поправь это",
             "created_at": "2026-08-06T11:48:00",
             "check": {"verdict": "clarify", "checked_at": "2026-08-06T11:48:05",
                       "question": "какой элемент?"}},
            {"id": "a-0003", "status": "superseded", "lane": "A", "text": "ink -> gray.600",
             "created_at": "2026-08-06T11:10:00", "superseded_by": "a-0004"},
            {"id": "a-0004", "status": "rejected", "lane": "A", "text": "#cccccc",
             "created_at": "2026-08-06T11:20:00",
             "check": {"verdict": "rejected", "checked_at": "2026-08-06T11:20:03",
                       "reason": "1.54:1", "alternatives": ["use #6e6a64"]}},
        ])
        feed = _capture(pins_feed, tmp, True, ref)
        s = feed["summary"]
        if set(s) != SUMMARY_KEYS:
            problems.append("the full feed's summary keys drifted")
        if s["waiting_on_owner"] != 1 or s["applied"] != 1 or s["rejected"] != 1 \
                or s["superseded"] != 1:
            problems.append("the summary miscounted: %r" % s)
        if s["needs_choice"] != 1:
            problems.append("a refusal offering alternatives was not counted as a choice")
        if not feed["pins"][0]["waiting"]:
            problems.append("a waiting pin is not first in the feed")

        # 2. medians use only pins that carry both marks
        if s["median_latency_s"]["to_applied"] != 61.0:
            problems.append("to_applied median wrong: %r" % s["median_latency_s"])
        if s["median_latency_s"]["to_classified"] != 4.0:
            problems.append("a pin without classified_at contributed a fabricated 0")

        # 6. superseded carries its marker and its cause
        row = [r for r in feed["pins"] if r["id"] == "a-0003"][0]
        if row["mark"] != STATUSES["superseded"]["mark"] or row["superseded_by"] != "a-0004":
            problems.append("superseded lost its marker or its cause: %r" % row)
        if "superseded by a-0004" not in row["last_event"]:
            problems.append("superseded shows a state but not how it got there")

    # 3. the run snapshot always has all five sections; a stale pulse says so
    with tempfile.TemporaryDirectory() as tmp:
        project(tmp)
        bare = _capture(status_feed, tmp, True, DEFAULT_MAX_AGE_MIN, ref)
        if set(bare) != SNAPSHOT_KEYS:
            problems.append("a project with no run data lost a snapshot section")
        if bare["pulse"]["fresh"]:
            problems.append("a missing pulse was reported as fresh")
        if bare["run_plan"] != [] or bare["checkpoints"] != []:
            problems.append("absent data came back as something other than empty")
    with tempfile.TemporaryDirectory() as tmp:
        project(tmp, pins=[],
                progress={"stage": "K2A", "substep": "skin", "updated_at":
                          "2026-08-06T11:00:00", "tokens_used": 12300},
                # real event rows: the fold belongs to dops_checkpoint, so the
                # fixture speaks its language rather than a convenient shorthand
                checkpoints=[{"event": "publish", "id": "sitemap", "stage": "K1",
                              "at": "2026-08-06T11:00:00", "provisional": False},
                             {"event": "decide", "id": "sitemap",
                              "at": "2026-08-06T11:05:00",
                              "decision": {"action": "accept"}}],
                queue=[{"id": "c1", "status": "queued"}, {"id": "c2", "status": "applied"}])
        snap = _capture(status_feed, tmp, True, DEFAULT_MAX_AGE_MIN, ref)
        if snap["pulse"]["fresh"]:
            problems.append("a 60-minute-old pulse was called fresh")

    # 3b. the same snapshot on a FILLED plan (У-6): an empty section proves the
    # key exists, not that the join works. Here the contract carries a real
    # run_plan and the trace a real measurement, and the two must meet.
    with tempfile.TemporaryDirectory() as tmp:
        project(tmp, pins=[], progress={"stage": "K2A", "substep": "skin",
                                        "updated_at": ref.isoformat(timespec="seconds"),
                                        "tokens_used": 100})
        sys.path.insert(0, HERE)
        import dops_plan
        import dops_trace
        shutil.copy(os.path.join(PKG_ROOT, "starters", "landing-event", "contract.yaml"),
                    os.path.join(tmp, "artifacts", "design-contract.yaml"))
        dops_plan.quiet(dops_plan.emit, tmp, "starter_first", False, False, False)
        trace = os.path.join(tmp, "artifacts", "trace.jsonl")
        for i in range(2):
            dops_trace.append(tmp, {"stage": "K2A", "kind": "start"})
            dops_trace.append(tmp, {"stage": "K2A", "kind": "end", "status": "ok"})
            rows = open(trace, encoding="utf-8").read().splitlines()
            last = json.loads(rows[-1])
            last["at"] += 60 * (i + 3)          # 3 and 4 minutes: median 3.5
            rows[-1] = json.dumps(last, ensure_ascii=False)
            open(trace, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        filled = _capture(status_feed, tmp, True, DEFAULT_MAX_AGE_MIN, ref)
        if set(filled) != SNAPSHOT_KEYS:
            problems.append("a filled plan changed the snapshot's sections")
        plan = filled["run_plan"]
        if len(plan) != 3:
            problems.append("the emitted plan did not reach the feed: %d step(s)" % len(plan))
        else:
            if set(plan[0]) < {"stage", "checkpoint", "eta_min", "source",
                               "human_needed", "fact_min"}:
                problems.append("a plan row lost a contract field: %r" % (plan[0],))
            if not any(s["human_needed"] and "attention_min" in s for s in plan):
                problems.append("no step carried the owner's attention into the feed")
            k2a = next(s for s in plan if s["stage"] == "K2A")
            if k2a["fact_min"] == 0:
                problems.append("the measured stage came back with no fact_min — "
                                "the plan and the trace were not joined")
        line = schedule_line(plan, "K2A")
        if "K2A" not in line or "next time you are needed" not in line:
            problems.append("the pulse line does not say where the run is and "
                            "when the owner is next needed: %r" % line)
        if snap["pulse"]["age_min"] != 60.0:
            problems.append("pulse age miscomputed: %r" % snap["pulse"]["age_min"])
        if len(snap["checkpoints"]) != 1 or snap["checkpoints"][0]["status"] != "acted":
            problems.append("the checkpoint log was not folded to its latest state")
        if snap["control_queue"] != {"queued": 1, "applied": 1, "refused": 0}:
            problems.append("the control queue tally is wrong: %r" % snap["control_queue"])
        fresh = _capture(status_feed, tmp, True, 120.0, ref)
        if not fresh["pulse"]["fresh"]:
            problems.append("a pulse inside the threshold was still called stale")

    # 4. the taxonomy is declared once: the JS literal must match the data file
    marks, waiting = _js_statuses()
    if not marks:
        problems.append("could not read STATUS_MARK out of gate-annotate.js")
    for name, spec in STATUSES.items():
        if name not in marks:
            problems.append("gate-annotate.js has no marker for status %r" % name)
        elif marks[name] != spec["mark"]:
            problems.append("marker for %r differs: js %r vs data %r"
                            % (name, marks[name], spec["mark"]))
    if waiting != WAITING:
        problems.append("the waiting set differs: js %r vs data %r" % (waiting, WAITING))
    for name in marks:
        if name not in STATUSES:
            problems.append("gate-annotate.js knows a status the taxonomy does not: %r"
                            % name)

    if problems:
        for p in problems:
            print("self-test FAIL: dops-feed: %s" % p)
        return 1
    print("OK: dops-feed self-test (stable schema on empty and full projects, "
          "medians skip pins without marks, a stale pulse says so, and the JS "
          "status taxonomy is held to the declared one)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", default="pins", choices=["pins", "status"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-age-min", type=float, default=DEFAULT_MAX_AGE_MIN)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.command == "status":
        return status_feed(root, args.json, args.max_age_min)
    return pins_feed(root, args.json)


if __name__ == "__main__":
    sys.exit(main())
