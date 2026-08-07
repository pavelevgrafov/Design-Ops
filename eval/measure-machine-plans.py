#!/usr/bin/env python3
"""measure-machine-plans.py — what share of owner edits a machine can execute.

П-5 measured 0 of 15 and the number carried the move: it said the missing
piece was never a cleverer extractor, because a person looking at a mockup
writes "typo in the ticket caption", not "replace A with B". Ф-1 answers that
by changing where the edit is BORN, so the honest test of Ф-1 is the same set
measured again.

The set lives in `eval/pins-realistic-set.json`, in the repository, because a
number nobody can re-derive is an assertion rather than a measurement — and
this project has already been bitten by claims that were true when written and
unverifiable afterwards.

What is compared:

  before   the fifteen edits as the owner typed them
  after    the same fifteen, with the five COPY edits made through the form

The ten taste and structure pins are identical in both runs on purpose. The
form takes copy out of the prose lane and touches nothing else; a measurement
that quietly improved the other ten would be measuring optimism.

Usage:
  python3 eval/measure-machine-plans.py [--json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import dops_pins as pins                              # noqa: E402

SET = os.path.join(HERE, "pins-realistic-set.json")


def as_pins(rows):
    out = []
    for i, row in enumerate(rows, start=1):
        at = "2026-08-07T09:%02d:00" % i
        out.append(dict(row, id="a-%04d" % i, target_selector=row.get("selector", ""),
                        created_at=at, at=at, status="new"))
    return out


def measure(rows):
    classified = [pins.row_for(p) for p in as_pins(rows)]
    machine = [r for r in classified if (r.get("plan") or {}).get("machine")]
    return len(machine), len(classified), classified


def main():
    data = json.load(open(SET, encoding="utf-8"))
    organic = data["organic"]
    for row in organic:
        row.setdefault("selector", "#s")

    before_n, before_total, _ = measure(organic)

    # the five copy edits, made through the form instead of typed
    after = []
    form = list(data["form_edits"])
    for row in organic:
        if row["kind"] == "copy" and form:
            e = form.pop(0)
            after.append({
                "kind": "copy", "selector": e["selector"], "lane": "A",
                "text": "правка на месте: «%s» → «%s»" % (e["find"], e["replace"]),
                "plan": {"machine": True, "action": "set_text",
                         "params": {"selector": e["selector"], "find": e["find"],
                                    "replace": e["replace"]}},
            })
        else:
            after.append(row)
    after_n, after_total, after_rows = measure(after)

    born = sum(1 for r in after_rows
               if "born with the pin" in str(r.get("why") or ""))
    out = {
        "before": {"machine": before_n, "total": before_total,
                   "share_pct": round(100.0 * before_n / before_total, 1)},
        "after": {"machine": after_n, "total": after_total,
                  "share_pct": round(100.0 * after_n / after_total, 1),
                  "born_in_form": born},
        "note": ("the ten taste and structure pins are identical in both runs: "
                 "the form takes copy out of the prose lane and claims nothing "
                 "about the rest"),
    }
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print("machine_plan_share on %d realistic owner edits" % before_total)
    print("  before Ф-1 (as typed):        %d/%d  (%.1f%%)"
          % (before_n, before_total, out["before"]["share_pct"]))
    print("  after  Ф-1 (copy via form):   %d/%d  (%.1f%%), %d born in the form"
          % (after_n, after_total, out["after"]["share_pct"], born))
    print("  %s" % out["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
