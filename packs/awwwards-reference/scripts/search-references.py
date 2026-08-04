#!/usr/bin/env python3
"""search-references.py — awwwards-reference: curated candidates for K2B.

Reads the LOCAL cache (assets/cache/top-references.yaml), filters by the
project profile (reference-taxonomy.yaml), and returns at most 3 contact
-sheet candidates (hard stop: choice-paradox guard). Offline by design;
when the cache is missing/empty the pack reports unavailable and K2B
calibration falls back to category anchors + base skin.

Usage:
  python3 search-references.py --profile site/landing-saas [--tags a,b]
  python3 search-references.py --self-test
Output: JSON list of candidates (id, name, dials, tokens_hint, source_note).
Exit: 0 candidates found, 1 unavailable/fail, 2 usage.
"""
import json, os, sys

try:
    import yaml
except ImportError:
    print("search-references: PyYAML required", file=sys.stderr)
    sys.exit(2)

PACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_CANDIDATES = 3  # hard stop: never more than 3 in the contact sheet


def load_yaml(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}


def search(profile, extra_tags):
    taxonomy = load_yaml(os.path.join(PACK_DIR, "assets", "reference-taxonomy.yaml"))
    cache = load_yaml(os.path.join(PACK_DIR, "assets", "cache", "top-references.yaml"))
    entries = cache.get("entries") or []
    if not entries:
        print("unavailable: local reference cache missing or empty — "
              "fall back to category anchors + base skin", file=sys.stderr)
        return None
    prof = (taxonomy.get("profiles") or {}).get(profile) or {}
    want_cats = set(prof.get("categories") or [])
    want_tags = set(prof.get("tags") or []) | set(extra_tags or [])

    def score(e):
        s = 0
        cats = set(e.get("categories") or [])
        tags = set(e.get("tags") or [])
        s += 2 * len(cats & want_cats)
        s += 1 * len(tags & want_tags)
        return s

    ranked = sorted(entries, key=score, reverse=True)
    top = [e for e in ranked if score(e) > 0][:MAX_CANDIDATES]
    if not top:  # profile uncovered → broadest fallback, still ≤3
        top = entries[:MAX_CANDIDATES]
    return [
        {"id": e.get("id"), "name": e.get("name"), "kind": e.get("kind"),
         "dials": e.get("dials"), "tokens_hint": e.get("tokens_hint"),
         "source_note": e.get("source_note"),
         "score": score(e)}
        for e in top
    ]


def self_test():
    out = search("site/landing-saas", [])
    if out is None:
        print("self-test FAIL: cache unavailable")
        return 1
    if not (1 <= len(out) <= MAX_CANDIDATES):
        print(f"self-test FAIL: {len(out)} candidates (must be 1..{MAX_CANDIDATES})")
        return 1
    for c in out:
        for field in ("id", "name", "dials", "tokens_hint", "source_note"):
            if not c.get(field):
                print(f"self-test FAIL: candidate missing '{field}'")
                return 1
    # scoring sanity: saas profile should rank minimal-editorial first
    if out[0]["id"] != "arch-minimal-editorial":
        print(f"self-test FAIL: unexpected top candidate {out[0]['id']}")
        return 1
    # unknown profile degrades to ≤3 broad entries, never explodes
    out2 = search("unknown/profile", [])
    if out2 is None or len(out2) > MAX_CANDIDATES:
        print("self-test FAIL: unknown profile fallback broken")
        return 1
    print(f"OK: search-references self-test ({len(out)} candidates, hard stop ≤{MAX_CANDIDATES})")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    profile, tags = None, []
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--profile" and i + 1 < len(args):
            profile = args[i + 1]
        elif a == "--tags" and i + 1 < len(args):
            tags = [t.strip() for t in args[i + 1].split(",") if t.strip()]
    if not profile:
        print(__doc__, file=sys.stderr)
        return 2
    out = search(profile, tags)
    if out is None:
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
