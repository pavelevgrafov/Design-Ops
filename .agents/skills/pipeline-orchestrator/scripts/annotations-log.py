#!/usr/bin/env python3
"""annotations-log.py — validate gate annotations and mirror them into the
decision log (v6.0, TZ-9).

annotations.json schema (produced by assets/gate-annotate.js):
  [{target_selector: str, x: int, y: int, text: str, at: ISO-8601 str}]

Usage:
  python3 annotations-log.py <annotations.json> [--log artifacts/decision-log.md]
Without --log, prints the formatted entries to stdout (dry run).
Exit: 0 ok, 1 schema violation, 2 usage/io.
"""
import datetime
import json
import sys

REQUIRED = {"target_selector": str, "x": int, "y": int, "text": str, "at": str}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    log = None
    if "--log" in sys.argv:
        log = sys.argv[sys.argv.index("--log") + 1]
    if not args:
        print("usage: annotations-log.py <annotations.json> [--log FILE]",
              file=sys.stderr)
        return 2
    try:
        with open(args[0], encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"fail: cannot read {args[0]}: {e}", file=sys.stderr)
        return 2
    if not isinstance(data, list):
        print("fail: annotations.json must be a JSON array", file=sys.stderr)
        return 1

    problems = []
    for i, a in enumerate(data):
        if not isinstance(a, dict):
            problems.append(f"[{i}] not an object")
            continue
        for field, typ in REQUIRED.items():
            if field not in a:
                problems.append(f"[{i}] missing '{field}'")
            elif not isinstance(a[field], typ):
                problems.append(f"[{i}] '{field}' must be {typ.__name__}")
        if "at" in a and isinstance(a.get("at"), str):
            try:
                datetime.datetime.fromisoformat(a["at"].replace("Z", "+00:00"))
            except ValueError:
                problems.append(f"[{i}] 'at' is not ISO-8601: {a['at']!r}")
    if problems:
        for p in problems:
            print(f"fail {p}")
        return 1

    lines = ["", f"## Gate annotations ({datetime.date.today().isoformat()})"]
    for i, a in enumerate(data, 1):
        lines.append(f"- pin {i} on `{a['target_selector']}` ({a['x']},{a['y']}) "
                     f"at {a['at']}: {a['text']}")
    block = "\n".join(lines) + "\n"
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(block)
        print(f"OK: {len(data)} annotation(s) appended to {log}")
    else:
        print(block, end="")
        print(f"OK: {len(data)} annotation(s) valid (dry run, no --log)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
