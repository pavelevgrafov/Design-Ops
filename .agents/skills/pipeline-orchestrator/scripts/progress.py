#!/usr/bin/env python3
"""progress.py — run heartbeat (У-1, v0.1.0).

The pipeline's pulse. Stage scripts (not model prose) write
`artifacts/progress.json` on every stage event; anything outside the run
(the owner, a dashboard widget, a watcher automation) can tell
"working / thinking / stalled" without asking the chat.

Commands:
  beat --stage K2B [--substep "..."] [--tokens N] [--next "..."]
       [--human-needed "..."] [--run-id ID]
       → update artifacts/progress.json (sets updated_at, health: alive,
         computes stage_elapsed_min from stage_started_at).
  status [--max-age-min 3]
       → prints one-line status; exit 1 if the pulse is stale
         (silent-incident signal) or absent.
  checkpoint --name "..." [--status published|pending]
       → record a published intermediate artifact (причал) with its
         decision actions; the owner-facing list of checkpoints lives
         inside progress.json for the panel to render.

Heartbeat discipline (per doc 11): beat on EVERY stage event; any beat
older than --max-age-min (default 3) means "silent incident" — visible
from outside without a single chat question.
"""
import argparse, datetime, json, os, sys

PROGRESS = os.path.join("artifacts", "progress.json")


def set_root(root):
    """Every other tool in the contour takes `--root`; this one silently used
    the working directory, so `dops status --root DIR` reported on whatever
    directory the shell happened to be in. Found while wiring У-6's schedule
    line into that same output."""
    global PROGRESS
    PROGRESS = os.path.join(root, "artifacts", "progress.json")


def now():
    return datetime.datetime.now()


def load():
    if os.path.isfile(PROGRESS):
        with open(PROGRESS, encoding="utf-8") as f:
            return json.load(f)
    return {"checkpoints": []}


def save(data):
    os.makedirs(os.path.dirname(PROGRESS), exist_ok=True)
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_beat(a):
    d = load()
    ts = now()
    if a.stage and d.get("stage") != a.stage:
        d["stage_started_at"] = ts.isoformat(timespec="seconds")
    d.setdefault("stage_started_at", ts.isoformat(timespec="seconds"))
    d["run_id"] = a.run_id or d.get("run_id") or f"run-{ts:%Y%m%d-%H%M}"
    d["updated_at"] = ts.isoformat(timespec="seconds")
    d["health"] = "alive"
    if a.stage:
        d["stage"] = a.stage
    if a.substep:
        d["substep"] = a.substep
    if a.tokens is not None:
        d["tokens_used"] = a.tokens
    if a.next:
        d["next_checkpoint"] = a.next
    if a.human_needed:
        d["human_needed_at"] = a.human_needed
    try:
        started = datetime.datetime.fromisoformat(d["stage_started_at"])
        d["stage_elapsed_min"] = round((ts - started).total_seconds() / 60, 1)
    except Exception:
        pass
    save(d)
    print(f"beat: {d.get('stage','?')} / {d.get('substep','—')} "
          f"({d.get('stage_elapsed_min', 0)} min, health=alive)")
    return 0


def cmd_status(a):
    if not os.path.isfile(PROGRESS):
        print("status: NO PULSE (progress.json absent) — run not started or heartbeat broken")
        return 1
    d = load()
    try:
        age = (now() - datetime.datetime.fromisoformat(d["updated_at"])).total_seconds() / 60
    except Exception:
        print("status: CORRUPT progress.json"); return 1
    fresh = age <= a.max_age_min
    health = "alive" if fresh else "SILENT INCIDENT"
    print(f"status: {health} | stage {d.get('stage','?')} "
          f"({d.get('substep','—')}) | pulse age {age:.1f} min "
          f"| tokens {d.get('tokens_used','?')} | next: {d.get('next_checkpoint','?')} "
          f"| human needed: {d.get('human_needed_at','—')}")
    return 0 if fresh else 1


def cmd_checkpoint(a):
    d = load()
    d.setdefault("checkpoints", []).append({
        "name": a.name, "status": a.status,
        "at": now().isoformat(timespec="seconds"),
        "actions": ["принять", "поправить (пин)", "отменить этап",
                    "ускорить дальше", "достаточно глубины"]})
    save(d)
    print(f"checkpoint: '{a.name}' {a.status} — owner may act without "
          f"stopping the conveyor")
    return 0


def self_test():
    import tempfile, time
    os.chdir(tempfile.mkdtemp())
    class A: pass
    a = A()
    a.stage, a.substep, a.tokens, a.next = "K1", "skeleton", 12000, "Gate 1 (~5 мин)"
    a.human_needed, a.run_id = "~21:58 (выбор структуры)", "selftest"
    if cmd_beat(a) != 0: return 1
    a.max_age_min = 3
    if cmd_status(a) != 0:
        print("fail: fresh pulse reported stale"); return 1
    a.name, a.status = "sitemap", "published"
    if cmd_checkpoint(a) != 0: return 1
    d = load()
    ok = (d["health"] == "alive" and d["stage"] == "K1"
          and d["checkpoints"][0]["name"] == "sitemap"
          and d["stage_elapsed_min"] >= 0)
    # stale detection: forge an old pulse
    d["updated_at"] = (now() - datetime.timedelta(minutes=10)).isoformat(timespec="seconds")
    save(d)
    if cmd_status(a) == 0:
        print("fail: stale pulse reported alive"); return 1
    print("pass: heartbeat beat/status/checkpoint, stale pulse detected")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["beat", "status", "checkpoint"])
    ap.add_argument("--stage"); ap.add_argument("--substep")
    ap.add_argument("--tokens", type=int); ap.add_argument("--next")
    ap.add_argument("--human-needed"); ap.add_argument("--run-id")
    ap.add_argument("--max-age-min", type=float, default=3)
    ap.add_argument("--name"); ap.add_argument("--status", default="published")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    set_root(a.root)
    if a.self_test:
        sys.exit(self_test())
    sys.exit({"beat": cmd_beat, "status": cmd_status,
              "checkpoint": cmd_checkpoint}[a.command](a))


if __name__ == "__main__":
    main()
