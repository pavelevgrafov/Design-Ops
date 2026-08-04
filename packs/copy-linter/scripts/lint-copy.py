#!/usr/bin/env python3
"""lint-copy.py — copy-linter: corporate-slop scan (D.36, Tier 2, A.22).

Ban list source: knowledge/microcopy-principles + knowledge/ai-look-catalog.
Hits are WARNINGS (tier 2): exit 0; --strict turns them into failures.

Usage: python3 lint-copy.py <file-or-dir> [...] [--strict] [--self-test]
Exit: 0 pass/warnings, 1 strict hits, 2 usage.
"""
import os, re, sys

BAN = [
    r"\bempower(?:ing|s|ed)?\b", r"\bunlock(?:ing|s|ed)?\b", r"\bseamless(?:ly)?\b",
    r"\bsupercharg", r"\bleverage\b", r"\bgame[- ]chang", r"\bnext level\b",
    r"\bcutting[- ]edge\b", r"\bbest[- ]in[- ]class\b", r"\bworld[- ]class\b",
    r"\brevolutioni", r"\bbuilt for modern teams\b", r"\bdelightful\b",
    r"\btransform your\b", r"\belevate your\b", r"\bunleash\b",
    # RU equivalents (same slop, localized)
    r"расширьт\w* возможност", r"бесшовн", r"новый уровень", r"революцион",
    r"передов\w+ решени", r"мирового класса",
]
BAN_RE = re.compile("|".join(BAN), re.I)
TAG_RE = re.compile(r"<[^>]+>")
NUM_RE = re.compile(r"\d")

def text_of(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except OSError:
        return ""
    if path.endswith(".html"):
        raw = TAG_RE.sub(" ", raw)
    return raw

def walk(paths, hits, files_scanned):
    for p in paths:
        if os.path.isdir(p):
            for dirpath, _d, files in os.walk(p):
                for fn in files:
                    if fn.endswith((".html", ".md", ".txt")):
                        fp = os.path.join(dirpath, fn)
                        t = text_of(fp)
                        files_scanned.append(fp)
                        for m in BAN_RE.finditer(t):
                            hits.append(f"{fp}: slop '{m.group(0)}' [A.22]")
        elif os.path.isfile(p):
            t = text_of(p)
            files_scanned.append(p)
            for m in BAN_RE.finditer(t):
                hits.append(f"{p}: slop '{m.group(0)}' [A.22]")

CLEAN = "Pricing starts at 12 dollars per seat. Setup takes 10 minutes."
DIRTY = "Empower your team with our seamless, world-class platform. Unlock productivity!"

def self_test():
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        c = os.path.join(td, "clean.md"); d = os.path.join(td, "dirty.md")
        open(c, "w").write(CLEAN); open(d, "w").write(DIRTY)
        hits, fs = [], []
        walk([c], hits, fs)
        if hits:
            print("self-test FAIL: clean copy flagged")
            return 1
        hits, fs = [], []
        walk([d], hits, fs)
        if len(hits) < 3:
            print(f"self-test FAIL: dirty copy caught only {len(hits)} hit(s)")
            return 1
    print("OK: copy-linter self-test (clean passes, dirty caught)")
    return 0

def main():
    if "--self-test" in sys.argv:
        return self_test()
    strict = "--strict" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    hits, files_scanned = [], []
    walk(paths, hits, files_scanned)
    for h in hits:
        print(f"WARN: {h}")
    if hits:
        print(f"{len(hits)} corporate-slop hit(s) in {len(files_scanned)} file(s) [D.36, tier 2]")
        return 1 if strict else 0
    print(f"OK: copy clean ({len(files_scanned)} file(s)) [D.36]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
