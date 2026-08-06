#!/usr/bin/env python3
"""dops_check_marker.py — D16, state-aware.

The `not_approved_visual_design` marker is not simply "must be absent":
while Gate 2 is deferred the base skin is presentable, not approved design,
so the marker is KEPT BY DESIGN and its ABSENCE is the defect. After K2B
scales, the marker must be gone.

Usage: python3 dops_check_marker.py <project_root> <contract.yaml>
Exit: 0 pass, 1 fail, 2 usage.
"""
import os
import re
import sys

MARKER = "not_approved_visual_design"
SKIP_DIRS = {".git", "node_modules", "artifacts", ".agents", "dist", "build",
             "eval", "packs", "packs-pro", "starters", "starters-pro", "skins",
             "skins-pro", "knowledge", "docs", "radar", "showcase", "tools"}
# skeleton.html is the K1 artifact (the neutral skeleton), not the shipped
# build — it legitimately keeps the marker forever. Named explicitly rather
# than filtered silently.
SKIP_FILES = {"skeleton.html"}
SCAN_EXT = {".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".vue"}


def gate2_state(contract):
    if not os.path.isfile(contract):
        return "deferred"
    with open(contract, encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"^gates:\s*$", text, re.M)
    if not m:
        return "deferred"
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    block = tail[:stop.start()] if stop else tail
    km = re.search(r"^\s{2}gate2:\s*(.+?)\s*$", block, re.M)
    return km.group(1).strip().strip('"').strip("'") if km else "deferred"


def find_marker(root):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            if os.path.splitext(name)[1].lower() not in SCAN_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    if MARKER in f.read():
                        hits.append(os.path.relpath(path, root))
            except OSError:
                continue
    return hits


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip())
        return 2
    root, contract = sys.argv[1], sys.argv[2]
    state = gate2_state(contract)
    hits = find_marker(root)
    deferred = state in ("deferred", "", "pending")

    if deferred:
        if hits:
            print("D16 pass: Gate 2 %s — marker present by design (%d file(s))"
                  % (state, len(hits)))
            return 0
        print("D16 FAIL: Gate 2 is %s but the %s marker is absent — the build "
              "claims approved design it never got" % (state, MARKER))
        return 1

    if hits:
        print("D16 FAIL: Gate 2 is %s but the marker survives in: %s"
              % (state, ", ".join(hits[:10])))
        return 1
    print("D16 pass: Gate 2 %s — marker removed after scaling" % state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
