#!/usr/bin/env python3
"""annotations-log.py — validate gate annotations and mirror them into the
decision log (v6.0, TZ-9; v7.2 adds the П-3 check block).

annotations.json schema (produced by assets/gate-annotate.js):
  [{target_selector: str, x: int, y: int, text: str, at: ISO-8601 str}]

A pin that has been through the checker (`dops pins check`) also carries:
  check: {verdict, checked_at, checker, reason, alternatives, question,
          conflict_ref}

The one rule worth enforcing mechanically: a `rejected` verdict must carry
both a reason and at least one alternative. A refusal without an alternative
is a wall, not a negotiation — and a wall is exactly the failure mode the
checker exists to prevent, so it is caught here rather than regretted by the
owner. `clarify` and `duplicate` must carry the question they are waiting on,
for the same reason: a pin that stops the conveyor without saying what it
needs is a silent block.

Usage:
  python3 annotations-log.py <annotations.json> [--log artifacts/decision-log.md]
Without --log, prints the formatted entries to stdout (dry run).
Exit: 0 ok, 1 schema violation, 2 usage/io.
"""
import datetime
import json
import sys

REQUIRED = {"target_selector": str, "x": int, "y": int, "text": str, "at": str}
VERDICTS = {"pass", "clarify", "rejected", "duplicate"}
CHECKERS = {"script", "model"}


def validate_check(i, check, problems):
    if not isinstance(check, dict):
        problems.append(f"[{i}] 'check' must be an object")
        return
    verdict = check.get("verdict")
    if verdict not in VERDICTS:
        problems.append(f"[{i}] check.verdict {verdict!r} not in "
                        f"{sorted(VERDICTS)}")
        return
    checker = check.get("checker")
    if checker is not None and checker not in CHECKERS:
        problems.append(f"[{i}] check.checker {checker!r} not in {sorted(CHECKERS)}")
    at = check.get("checked_at")
    if at:
        try:
            datetime.datetime.fromisoformat(str(at).replace("Z", "+00:00"))
        except ValueError:
            problems.append(f"[{i}] check.checked_at is not ISO-8601: {at!r}")
    if verdict == "rejected":
        if not str(check.get("reason") or "").strip():
            problems.append(f"[{i}] rejected without a reason — a refusal the "
                            f"owner cannot argue with")
        alts = check.get("alternatives")
        if not isinstance(alts, list) or not [a for a in alts if str(a).strip()]:
            problems.append(f"[{i}] rejected without alternatives — that is a "
                            f"wall, not a negotiation")
    if verdict in ("clarify", "duplicate") and not str(check.get("question") or "").strip():
        problems.append(f"[{i}] {verdict} without a question — the conveyor "
                        f"stops and nobody knows what it is waiting for")


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
        if "check" in a:
            validate_check(i, a["check"], problems)
    if problems:
        for p in problems:
            print(f"fail {p}")
        return 1

    lines = ["", f"## Gate annotations ({datetime.date.today().isoformat()})"]
    for i, a in enumerate(data, 1):
        lines.append(f"- pin {i} on `{a['target_selector']}` ({a['x']},{a['y']}) "
                     f"at {a['at']}: {a['text']}")
        # A refusal belongs in the decision log, not only in the pin: the next
        # run must be able to see that this was asked for and answered.
        check = a.get("check") if isinstance(a.get("check"), dict) else None
        if check and check.get("verdict") in ("rejected", "clarify", "duplicate"):
            lines.append(f"  - checker ({check.get('checker', 'script')}): "
                         f"{check['verdict']} — "
                         f"{check.get('reason') or check.get('question') or ''}")
            for alt in check.get("alternatives") or []:
                lines.append(f"    - alternative offered: {alt}")
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
