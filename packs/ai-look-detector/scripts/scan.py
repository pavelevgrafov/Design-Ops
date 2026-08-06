#!/usr/bin/env python3
"""scan.py — ai-look-detector: statistical-default marker scan (D.30, Tier 1).

Catalog source: knowledge/ai-look-catalog. Tier 1 markers FAIL the scan;
Tier 2 markers are warnings (report lines, exit stays 0 without --strict).

Usage: python3 scan.py <file-or-dir> [...] [--strict] [--self-test]
Exit: 0 pass (warnings allowed), 1 tier-1 hit / strict warnings, 2 usage.
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

TIER1 = [
    (re.compile(r"#6366f1|#4f46e5|#4338ca", re.I), "indigo-600 family hex (default Tailwind accent)"),
    (re.compile(r"#0f172a|#1e293b", re.I), "slate-900/800 family hex (default Tailwind ink)"),
    (re.compile(r"from-(indigo|purple|violet)-\d|to-(purple|violet|fuchsia)-\d", re.I),
     "indigo→purple gradient classes"),
    (re.compile(r"linear-gradient\([^)]*(#6366f1|#4f46e5|#a855f7|#8b5cf6)", re.I),
     "indigo→purple gradient in CSS"),
]
TIER2 = [
    (re.compile(r"rounded-2xl", re.I), 3, "rounded-2xl on many elements (>{n} occurrences)"),
    (re.compile(r"shadow-lg", re.I), 3, "shadow-lg on many elements (>{n} occurrences)"),
    (re.compile(r"font-family[^;{]*\bInter\b", re.I), 0, "Inter in a font stack (first-position laziness marker)"),
    (re.compile(r"backdrop-filter", re.I), 0, "glassmorphism (backdrop-filter) — needs content-under-glass justification"),
]

def scan_text(path, text, fails, warns):
    for rx, label in TIER1:
        if rx.search(text):
            fails.append(f"{path}: {label} [D.30]")
    for rx, threshold, label in TIER2:
        hits = len(rx.findall(text))
        if hits > threshold:
            warns.append(f"{path}: {label.format(n=threshold)} ({hits}x)")

def walk(paths, fails, warns):
    for p in paths:
        if os.path.isdir(p):
            _skips = _scan_skips(p)
            for dirpath, _d, files in os.walk(p):
                _d[:] = [d for d in _d if d not in _skips]
                for fn in files:
                    if fn.endswith((".css", ".html", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")):
                        try:
                            with open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace") as f:
                                scan_text(os.path.join(dirpath, fn), f.read(), fails, warns)
                        except OSError:
                            pass
        elif os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                scan_text(p, f.read(), fails, warns)

CLEAN = ":root{--ink:#141312} .card{border-radius:8px;box-shadow:0 1px 2px rgb(0 0 0/.05)}"
DIRTY = ".hero{background:linear-gradient(90deg,#6366f1,#a855f7)} .x{color:#0f172a}"

def self_test():
    fails, warns = [], []
    scan_text("<clean>", CLEAN, fails, warns)
    if fails:
        print("self-test FAIL: clean fixture flagged as tier-1")
        return 1
    fails, warns = [], []
    scan_text("<dirty>", DIRTY, fails, warns)
    if len(fails) < 2:
        print(f"self-test FAIL: dirty fixture caught only {len(fails)} tier-1 marker(s)")
        return 1
    print("OK: ai-look-detector self-test (clean passes, dirty caught)")
    return 0

def main():
    if "--self-test" in sys.argv:
        return self_test()
    strict = "--strict" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    fails, warns = [], []
    walk(paths, fails, warns)
    for w in warns:
        print(f"WARN: {w}")
    for f_ in fails:
        print(f"FAIL: {f_}")
    if fails:
        print(f"\n{len(fails)} AI-look tier-1 marker(s) [D.30]")
        return 1
    if warns and strict:
        return 1
    print(f"OK: no tier-1 AI-look markers ({len(warns)} warning(s)) [D.30]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
