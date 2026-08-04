#!/usr/bin/env python3
"""check-reduced-motion.py — D.29 (Tier 1): the quiet version exists.

Rule (source: knowledge/motion-budgets, invariant A.17): any stylesheet
that introduces movement (@keyframes, transition:, animation:) MUST also
carry a `@media (prefers-reduced-motion: reduce)` block providing the
quiet version.

Usage: python3 check-reduced-motion.py <file-or-dir> [...]
Exit: 0 pass, 1 fail, 2 usage.
"""
import os, re, sys

MOTION = re.compile(r"@keyframes|transition\s*:|animation\s*:", re.I)
REDUCED = re.compile(r"@media\s*[^{]*prefers-reduced-motion\s*:\s*reduce", re.I)

def scan_file(path, problems):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        problems.append(f"{path}: unreadable ({e})")
        return
    if MOTION.search(text) and not REDUCED.search(text):
        problems.append(
            f"{path}: motion present (@keyframes/transition/animation) but no "
            "prefers-reduced-motion quiet version [A.17]")

def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    problems = []
    for p in paths:
        if os.path.isdir(p):
            for dirpath, _d, files in os.walk(p):
                for fn in files:
                    if fn.endswith((".css", ".html")):
                        scan_file(os.path.join(dirpath, fn), problems)
        else:
            scan_file(p, problems)
    for pr in problems:
        print(f"FAIL: {pr}")
    if problems:
        print(f"\n{len(problems)} reduced-motion problem(s) [D.29]")
        return 1
    print("OK: reduced-motion quiet version present [D.29]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
