#!/usr/bin/env python3
"""lint-copy.py — copy-linter: corporate-slop scan (D.36, Tier 2, A.22).

Ban list source: knowledge/microcopy-principles + knowledge/ai-look-catalog.
Hits are WARNINGS (tier 2): exit 0; --strict turns them into failures.

An element carrying `data-dops-exhibit` displays banned words as data (a
stop-words tab, a quoted bad example) — its subtree is not linted, and the
report says how many subtrees that removed.

Usage: python3 lint-copy.py <file-or-dir> [...] [--strict] [--self-test]
Exit: 0 pass/warnings, 1 strict hits, 2 usage.
"""
import os, re, sys
from html.parser import HTMLParser

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
# Root-level toolkit docs shipped by install.sh — not product copy.
SKIP_SCAN_FILES = {"AGENTS.md", "INSTALL.md", "README.md", "LICENSE"}

def _scan_skips(root):
    """Exclusions protect a project-root walk. Scanning an excluded directory
    deliberately (a fixture, a vendored subtree) disables them."""
    parts = set(os.path.abspath(root).split(os.sep))
    return set() if parts & SKIP_SCAN_DIRS else SKIP_SCAN_DIRS

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

# --- exhibits: banned words displayed AS DATA ---------------------------------
# D-BZ-4, case №1: a brand kit renders a stop-words tab, so the interface shows
# «революционный» in a list of words the product must never say. The linter read
# it as the product saying it. Both readings are literally correct; only the
# author knows which one applies, so the author declares it — one attribute on
# the element whose subtree is data rather than voice:
#
#     <ul data-dops-exhibit="stop-list"> <li>революционный</li> ... </ul>
#
# Declared, not inferred, and never silent: main() prints how many subtrees the
# marker removed, so a page that mutes half its copy says so in the report.
# The exemption is scoped to D.36 — no other check reads this attribute.
EXHIBIT_ATTR = "data-dops-exhibit"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class _ExhibitStripper(HTMLParser):
    """Text of the document minus every subtree marked as an exhibit.

    Tag-level parsing rather than a regex: an exhibit is a subtree, and the
    closing tag that ends it cannot be found by matching angle brackets."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts = []
        self.depth = 0          # open elements inside the current exhibit
        self.exhibits = 0

    def _marked(self, attrs):
        return any(k.lower() == EXHIBIT_ATTR for k, _v in attrs)

    def handle_starttag(self, tag, attrs):
        if self.depth:
            if tag not in VOID_TAGS:
                self.depth += 1
            return
        if self._marked(attrs):
            self.exhibits += 1
            if tag not in VOID_TAGS:
                self.depth = 1

    def handle_startendtag(self, tag, attrs):
        # `<x ... />` — overridden so the default start+end pair cannot
        # unbalance the depth counter.
        if not self.depth and self._marked(attrs):
            self.exhibits += 1

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data)

    def text(self):
        return " ".join(self.parts)


def strip_html(raw):
    """(text, exhibits removed). Falls back to the flat tag strip if the
    document cannot be parsed at all — a broken page is still linted, just
    without exhibit support, which is the honest degradation."""
    p = _ExhibitStripper()
    try:
        p.feed(raw)
        p.close()
    except Exception:
        return TAG_RE.sub(" ", raw), 0
    return p.text(), p.exhibits


def text_of(path):
    """-> (text, exhibits removed)"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except OSError:
        return "", 0
    if path.endswith(".html"):
        return strip_html(raw)
    return raw, 0

def _scan_one(fp, hits, files_scanned, exhibits):
    t, n = text_of(fp)
    files_scanned.append(fp)
    if n:
        exhibits.append((fp, n))
    for m in BAN_RE.finditer(t):
        hits.append(f"{fp}: slop '{m.group(0)}' [A.22]")


def walk(paths, hits, files_scanned, exhibits=None):
    if exhibits is None:
        exhibits = []
    for p in paths:
        if os.path.isdir(p):
            _skips = _scan_skips(p)
            for dirpath, _d, files in os.walk(p):
                _d[:] = [d for d in _d if d not in _skips]
                for fn in files:
                    if fn in SKIP_SCAN_FILES:
                        continue
                    if fn.endswith((".html", ".md", ".txt")):
                        _scan_one(os.path.join(dirpath, fn), hits,
                                  files_scanned, exhibits)
        elif os.path.isfile(p):
            _scan_one(p, hits, files_scanned, exhibits)
    return exhibits

CLEAN = "Pricing starts at 12 dollars per seat. Setup takes 10 minutes."
DIRTY = "Empower your team with our seamless, world-class platform. Unlock productivity!"
# The brand-kit page from case №1, reduced: the stop list is shown as data, the
# heading next to it is the product's own voice and stays under the rule.
EXHIBIT_PAGE = """<html><body>
<h2>Stop words — never write these</h2>
<ul data-dops-exhibit="stop-list">
  <li>революционный</li><li>seamless</li>
  <li><span>world-class</span></li>
</ul>
<p>Setup takes 10 minutes.</p>
</body></html>"""
VOICE_PAGE = EXHIBIT_PAGE.replace(' data-dops-exhibit="stop-list"', "")

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

        # [D-BZ-4] the exhibit is exempt; the same words unmarked are not, and
        # nesting inside the marked subtree does not leak out.
        e = os.path.join(td, "kit.html"); v = os.path.join(td, "voice.html")
        open(e, "w").write(EXHIBIT_PAGE); open(v, "w").write(VOICE_PAGE)
        hits, fs = [], []
        ex = walk([e], hits, fs)
        if hits:
            print(f"self-test FAIL: a declared exhibit was read as the "
                  f"product's voice ({hits[0]})")
            return 1
        if ex != [(e, 1)]:
            print(f"self-test FAIL: exhibit removal not reported: {ex}")
            return 1
        hits, fs = [], []
        ex = walk([v], hits, fs)
        if len(hits) < 3 or ex:
            print(f"self-test FAIL: without the marker the same list must be "
                  f"3 hits and 0 exhibits — got {len(hits)}/{ex}")
            return 1
    print("OK: copy-linter self-test (clean passes, dirty caught, declared "
          "exhibit exempt while the unmarked copy still fails)")
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
    exhibits = walk(paths, hits, files_scanned)
    for h in hits:
        print(f"WARN: {h}")
    # An exemption nobody can see is an exemption nobody can audit.
    for fp, n in exhibits:
        print(f"note: {fp}: {n} exhibit subtree(s) not linted "
              f"({EXHIBIT_ATTR}) — declared as data, not the product's voice")
    if hits:
        print(f"{len(hits)} corporate-slop hit(s) in {len(files_scanned)} file(s) [D.36, tier 2]")
        print(f"a hit that is a stop-list entry or a quoted example is data: "
              f"mark that element {EXHIBIT_ATTR}=\"...\" instead of rewording it")
        return 1 if strict else 0
    print(f"OK: copy clean ({len(files_scanned)} file(s)) [D.36]")
    return 0

if __name__ == "__main__":
    sys.exit(main())
