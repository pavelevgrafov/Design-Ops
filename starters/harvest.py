#!/usr/bin/env python3
"""harvest.py — starter flywheel (v6.0, TZ-3): extract a candidate starter
from a FINISHED project. The owner of the finished project must have agreed
(explicit consent, recorded in its contract as starters.harvest_allowed:
true — a client project never leaks into the catalog silently).

Usage: python3 harvest.py <project-root> <new-starter-id>

The candidate lands in starters/_candidates/<id>/ with a harvest report;
promotion into starters/ is a human decision after a full floor pass.
Exit: 0 ok, 1 floor red, 2 usage/io, 3 consent missing.
"""
import datetime
import os
import re
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    if len(sys.argv) < 3:
        print("usage: harvest.py <project-root> <new-starter-id>", file=sys.stderr)
        return 2
    project, nid = sys.argv[1], sys.argv[2]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", nid):
        print("fail: starter id must be kebab-case", file=sys.stderr)
        return 2
    contract = None
    for rel in ("artifacts/design-contract.yaml", "design-contract.yaml",
                "contract.yaml"):
        p = os.path.join(project, rel)
        if os.path.exists(p):
            contract = p
            break
    if not contract:
        print("fail: no design contract in the project", file=sys.stderr)
        return 2
    with open(contract, encoding="utf-8") as f:
        c = yaml.safe_load(f) or {}
    starters = c.get("starters") or {}
    if starters.get("harvest_allowed") is not True:
        print("fail: consent missing — set starters.harvest_allowed: true in "
              "the project contract (explicit owner agreement)", file=sys.stderr)
        return 3

    out = os.path.join(HERE, "_candidates", nid)
    os.makedirs(out, exist_ok=True)
    copied, slots = 0, set()
    for dirpath, _dirs, files in os.walk(project):
        if any(x in dirpath for x in ("node_modules", ".git", "artifacts",
                                      "_candidates")):
            continue
        for fn in files:
            if not fn.endswith((".html", ".css")):
                continue
            src = os.path.join(dirpath, fn)
            with open(src, encoding="utf-8", errors="replace") as f:
                text = f.read()
            slots.update(re.findall(r'data-slot="([^"]+)"', text))
            # strip injected content back to empty slots
            text = re.sub(r'(data-slot="[^"]+"[^>]*>)[^<]+', r"\1", text)
            rel = os.path.relpath(src, project)
            dst = os.path.join(out, "skeleton", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(text)
            copied += 1

    if not copied:
        print("fail: no .html/.css files harvested", file=sys.stderr)
        return 2

    # static floor on the candidate (same checks as starters/recheck.sh)
    QG = os.path.join(ROOT, ".agents/skills/quality-guardian/scripts")
    VD = os.path.join(ROOT, ".agents/skills/visual-director/scripts")
    red = []
    for name, cmd in (("placeholders", ["bash", os.path.join(QG, "check-placeholders.sh"), os.path.join(out, "skeleton")]),
                      ("token-usage", ["bash", os.path.join(QG, "check-token-usage.sh"), os.path.join(out, "skeleton")]),
                      ("ban-list", ["bash", os.path.join(VD, "lint-ban-list.sh"), os.path.join(out, "skeleton")])):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            red.append(name)

    report = os.path.join(out, "harvest-report.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"# Harvest report — {nid}\n\n"
                f"- source project: {os.path.abspath(project)}\n"
                f"- harvested_at: {datetime.date.today().isoformat()}\n"
                f"- files: {copied}; slots re-emptied: {len(slots)}\n"
                f"- static floor: {'RED: ' + ', '.join(red) if red else 'green'}\n\n"
                "Promotion to starters/ requires: floor green, copy-map.yaml "
                "written, starter.yaml filled, human approval.\n")
    if red:
        print(f"fail: static floor red ({', '.join(red)}) — see {report}",
              file=sys.stderr)
        return 1
    print(f"OK: candidate at {out} ({copied} files, {len(slots)} slots); "
          "promotion is a human decision")
    return 0


if __name__ == "__main__":
    sys.exit(main())
