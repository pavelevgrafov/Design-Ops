#!/usr/bin/env python3
"""check-motion-properties.py — D.35 (Tier 2, warning): jank-safe motion.

Rules (source: knowledge/motion-budgets, invariant A.17):
- transition/animation MUST NOT target layout properties
  (width, height, top, left, right, bottom, margin, padding) — transform
  and opacity only;
- `linear` easing is forbidden in UI motion.

Tier 2: violations are WARNINGS in the report, exit stays 0 unless
--strict is passed.

Usage: python3 check-motion-properties.py <file-or-dir> [--strict]
Exit: 0 pass/warnings, 1 fail (--strict), 2 usage.
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

TRANSITION = re.compile(r"transition(?:-property)?\s*:\s*([^;]+);", re.I)
FORBIDDEN = re.compile(r"\b(width|height|top|left|right|bottom|margin|padding)\b", re.I)
LINEAR = re.compile(r"\blinear\b", re.I)

def scan_file(path, warnings_):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return
    for m in TRANSITION.finditer(text):
        props = m.group(1)
        if FORBIDDEN.search(props):
            warnings_.append(f"{path}: transition targets layout property ({props.strip()[:60]}) — "
                             "animate transform/opacity only")
    for m in re.finditer(r"(?:transition|animation)[^;{}]*\blinear\b[^;{}]*[;{]", text, re.I):
        warnings_.append(f"{path}: linear easing in UI motion is forbidden — use ease-out family")

def main():
    args = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    warnings_ = []
    for p in args:
        if os.path.isdir(p):
            _skips = _scan_skips(p)
            for dirpath, _d, files in os.walk(p):
                _d[:] = [d for d in _d if d not in _skips]
                for fn in files:
                    if fn.endswith((".css", ".html")):
                        scan_file(os.path.join(dirpath, fn), warnings_)
        else:
            scan_file(p, warnings_)
    for w in warnings_:
        print(f"WARN: {w}")
    if warnings_:
        print(f"{len(warnings_)} motion warning(s) [D.35, tier 2]")
        return 1 if strict else 0
    print("OK: motion properties jank-safe [D.35]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
