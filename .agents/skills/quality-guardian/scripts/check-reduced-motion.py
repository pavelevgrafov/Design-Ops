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

# --- scan scope: never audit the vendored pipeline itself ---------------------
# A project installs the toolkit INTO itself (install.sh), so walking the
# project root would scan .agents/, packs/ and eval/selftest/fixture/ (which
# holds deliberate traps) and report them as product defects. Override with
# DOPS_SCAN_EXCLUDE="dir1,dir2" when a project genuinely ships such a folder.
_DEFAULT_SKIP_SCAN = ("node_modules .git .agents eval packs packs-pro starters "
                      "starters-pro skins skins-pro knowledge docs radar "
                      "showcase tools dist build __pycache__ .pack-cache")
SKIP_SCAN_DIRS = set((os.environ.get("DOPS_SCAN_EXCLUDE") or "")
                     .replace(",", " ").split() or _DEFAULT_SKIP_SCAN.split())

def _scan_skips(root):
    """Exclusions protect a project-root walk. Scanning an excluded directory
    deliberately (a fixture, a vendored subtree) disables them."""
    parts = set(os.path.abspath(root).split(os.sep))
    return set() if parts & SKIP_SCAN_DIRS else SKIP_SCAN_DIRS

MOTION = re.compile(r"@keyframes|transition\s*:|animation\s*:", re.I)
REDUCED = re.compile(r"@media\s*[^{]*prefers-reduced-motion\s*:\s*reduce", re.I)
NO_PREF = re.compile(r"@media\s*[^{]*prefers-reduced-motion\s*:\s*no-preference[^{]*\{", re.I)


def guarded_ranges(text):
    """Character ranges of `@media (prefers-reduced-motion: no-preference)`
    blocks. Motion declared only inside one of these is the STRONGER pattern:
    movement is opt-in, so a browser that cannot answer the query stays
    quiet. Accepting only the `reduce` form would push authors toward the
    weaker one."""
    spans = []
    for m in NO_PREF.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        spans.append((m.start(), i))
    return spans


def motion_is_guarded(text):
    spans = guarded_ranges(text)
    if not spans:
        return False
    for m in MOTION.finditer(text):
        if not any(a <= m.start() < b for a, b in spans):
            return False
    return True

def scan_file(path, problems):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        problems.append(f"{path}: unreadable ({e})")
        return
    if not MOTION.search(text):
        return
    if REDUCED.search(text) or motion_is_guarded(text):
        return
    problems.append(
        f"{path}: motion present (@keyframes/transition/animation) but no "
        "prefers-reduced-motion quiet version [A.17] — add a "
        "`reduce` block, or declare all motion inside "
        "`@media (prefers-reduced-motion: no-preference)`")

def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    problems = []
    for p in paths:
        if os.path.isdir(p):
            _skips = _scan_skips(p)
            for dirpath, _d, files in os.walk(p):
                _d[:] = [d for d in _d if d not in _skips]
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
