#!/usr/bin/env python3
"""check-semantic-html.py — D.28 (Tier 1): semantic HTML before ARIA.

Rules (source: knowledge/wcag-22-aa-rules, invariant A.18):
- exactly one <h1> per document;
- heading levels never skip (h1 -> h3 without h2 is a defect);
- a content page exposes landmarks: <main> (and <header>/<nav> where present);
- no interactive divs/spans: <div role="button">, onclick on div/span.

Usage: python3 check-semantic-html.py <file-or-dir> [...]
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

H_RE = re.compile(r"<h([1-6])\b", re.I)
MAIN_RE = re.compile(r"<main\b", re.I)
DIV_BUTTON = re.compile(r"<(div|span)\b[^>]*\b(role\s*=\s*[\"']button[\"']|onclick\s*=)", re.I)

def scan_file(path, problems):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        problems.append(f"{path}: unreadable ({e})")
        return
    if "<html" not in text.lower():
        return  # not a full document (fragment) — skip
    levels = [int(m.group(1)) for m in H_RE.finditer(text)]
    if levels.count(1) > 1:
        problems.append(f"{path}: {levels.count(1)} <h1> elements — exactly one allowed")
    if levels and 1 not in levels:
        problems.append(f"{path}: headings present but no <h1>")
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            problems.append(f"{path}: heading level skips h{prev} -> h{lv} (hierarchy must be continuous)")
            break
        prev = lv
    if not MAIN_RE.search(text):
        problems.append(f"{path}: no <main> landmark")
    for m in DIV_BUTTON.finditer(text):
        problems.append(f"{path}: interactive <{m.group(1)}> (role=button/onclick) — use <button>/<a> [A.18]")

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
                    if fn.endswith(".html"):
                        scan_file(os.path.join(dirpath, fn), problems)
        else:
            scan_file(p, problems)
    for pr in problems:
        print(f"FAIL: {pr}")
    if problems:
        print(f"\n{len(problems)} semantic-HTML problem(s) [D.28]")
        return 1
    print("OK: semantic HTML [D.28]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
