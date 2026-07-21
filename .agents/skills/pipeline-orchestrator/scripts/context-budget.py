#!/usr/bin/env python3
"""context-budget.py — run context-budget counter (v6.0, TZ-12).

The orchestrator records every instruction/note file it reads during a run:
  context-budget.py read <file> [--log artifacts/context-log.jsonl]
At the end of a stage (and always at delivery) it reports:
  context-budget.py report [--mode quick|standard|full] [--log ...]

Estimation: est_tokens = ceil(bytes / est_bytes_per_token) from
assets/context-limits.yaml. Exceeding the mode limit = wave defect:
exit 1, and the report line lands in the delivery report + decision log
(never silently).

Exit: 0 ok, 1 over limit, 2 usage/io.
"""
import datetime
import json
import math
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LIMITS = os.path.join(HERE, "..", "assets", "context-limits.yaml")


def load_limits(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("limits") or {}, int(cfg.get("est_bytes_per_token") or 4)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    log = "artifacts/context-log.jsonl"
    mode = "quick"
    limits_path = DEFAULT_LIMITS
    for flag, attr in (("--log", "log"), ("--mode", "mode"),
                       ("--limits", "limits_path")):
        if flag in sys.argv:
            val = sys.argv[sys.argv.index(flag) + 1]
            if attr == "log":
                log = val
            elif attr == "mode":
                mode = val
            else:
                limits_path = val
    if len(args) < 1 or args[0] not in ("read", "report"):
        print("usage: context-budget.py read <file> | report [--mode M]",
              file=sys.stderr)
        return 2
    limits, bpt = load_limits(limits_path)

    if args[0] == "read":
        if len(args) < 2:
            print("usage: context-budget.py read <file>", file=sys.stderr)
            return 2
        path = args[1]
        try:
            size = os.path.getsize(path)
        except OSError as e:
            print(f"fail: {e}", file=sys.stderr)
            return 2
        os.makedirs(os.path.dirname(log) or ".", exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "file": path, "bytes": size,
                "est_tokens": math.ceil(size / bpt)}) + "\n")
        return 0

    # report
    if not os.path.exists(log):
        print(f"OK: no reads recorded ({log} absent) — 0 tokens")
        return 0
    total, files = 0, 0
    with open(log, encoding="utf-8") as f:
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
    limit = limits.get(mode)
    head = f"context budget ({mode}): ~{total} tokens over {files} file(s)"
    if limit is None:
        print(f"{head}; no limit for mode '{mode}'")
        return 0
    if total > limit:
        print(f"OVER {head}; limit {limit} — wave defect (TZ-12): "
              "record in decision log + delivery report")
        return 1
    print(f"OK {head}; limit {limit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
