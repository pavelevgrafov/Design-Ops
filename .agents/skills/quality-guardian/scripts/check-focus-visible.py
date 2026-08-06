#!/usr/bin/env python3
"""check-focus-visible.py — D.27 (Tier 1): keyboard focus stays visible.

Rules (source: knowledge/wcag-22-aa-rules, invariant A.13):
- `outline: none` / `outline: 0` is forbidden UNLESS the same stylesheet
  provides a :focus-visible (or :focus) replacement style.
- A stylesheet that styles interactive elements but has no :focus-visible
  rule at all is flagged (focus must be styled, not just not-removed).

Usage: python3 check-focus-visible.py <file-or-dir> [...]
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

REMOVAL = re.compile(r"outline\s*:\s*(none|0\b)", re.I)
FOCUS_STYLE = re.compile(r":focus-visible|:focus\b", re.I)
INTERACTIVE = re.compile(r"\b(a|button|input|select|textarea)\b\s*[,{:]|\[tabindex", re.I)

def scan_file(path, problems):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        problems.append(f"{path}: unreadable ({e})")
        return
    has_focus = bool(FOCUS_STYLE.search(text))
    for i, line in enumerate(text.splitlines(), 1):
        if REMOVAL.search(line) and not has_focus:
            problems.append(
                f"{path}:{i}: outline removed with no :focus-visible replacement in this stylesheet")
            return
    if INTERACTIVE.search(text) and ("{" in text) and not has_focus:
        problems.append(
            f"{path}: interactive selectors styled but no :focus-visible rule anywhere "
            "(focus must be visibly styled, not just not-removed)")

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
        print(f"\n{len(problems)} focus-visibility problem(s) [D.27]")
        return 1
    print("OK: focus visibility preserved [D.27]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
