#!/usr/bin/env python3
"""dops_shots.py — image budget for AI diagnostics (P3).

Section-wise capture is right for judging, but the standard/full matrix can
emit up to 12 sections x 3 viewports x routes. Every image the model opens
is ~1-1.5k tokens AND stays resident for the rest of the run, so an
unbudgeted diagnostics pass can cost more than the entire instruction
corpus. This picks the informative subset once, deterministically:

  1. drop byte-identical duplicates (the same section at two viewports that
     did not actually reflow);
  2. keep one overview per route x viewport (hierarchy is judged there);
  3. fill the remaining budget with the largest distinct sections (more
     pixels = more content = more to judge);
  4. write a manifest the diagnostics step must follow, plus a
     contact-sheet.html for the human, which costs the model nothing.

Usage:
  python3 tools/dops_shots.py [--root DIR] [--shots DIR] [--budget N]
                              [--json] [--self-test]

Exit: 0 ok, 1 no shots found, 2 usage.
"""
import argparse
import hashlib
import json
import os
import re
import sys

OVERVIEW = ("viewport.png", "full.png")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(shots_dir):
    found = []
    for dirpath, _d, files in os.walk(shots_dir):
        for fn in sorted(files):
            if not fn.lower().endswith(".png"):
                continue
            path = os.path.join(dirpath, fn)
            # dir name shape: shots_<route>_<width>
            m = re.search(r"shots(.*)_(\d+)$", os.path.basename(dirpath))
            route = (m.group(1).replace("_", "/") or "/") if m else "?"
            width = int(m.group(2)) if m else 0
            found.append({
                "path": path, "file": fn, "route": route, "viewport": width,
                "bytes": os.path.getsize(path),
                "overview": fn in OVERVIEW,
            })
    return found


def select(shots, budget):
    seen, unique, dropped = {}, [], []
    for s in shots:
        digest = sha(s["path"])
        if digest in seen:
            dropped.append({"path": s["path"], "reason": "identical to %s"
                            % os.path.relpath(seen[digest])})
            continue
        seen[digest] = s["path"]
        s["sha256"] = digest[:16]
        unique.append(s)

    chosen, keys = [], set()
    for s in sorted(unique, key=lambda x: (x["route"], x["viewport"])):
        if not s["overview"]:
            continue
        key = (s["route"], s["viewport"])
        if key in keys:
            continue
        keys.add(key)
        s["reason"] = "overview %s @%dpx" % (s["route"], s["viewport"])
        chosen.append(s)

    rest = [s for s in unique if s not in chosen]
    for s in sorted(rest, key=lambda x: -x["bytes"]):
        if len(chosen) >= budget:
            break
        s["reason"] = "largest distinct section"
        chosen.append(s)

    over = []
    if len(chosen) > budget:
        over = chosen[budget:]
        for s in over:
            s["reason"] = "over budget — overview kept for coverage"
        chosen = chosen[:budget] + over      # never drop coverage silently
    return chosen, dropped, unique


CONTACT_SHEET = """<!doctype html><meta charset="utf-8">
<title>Contact sheet — AI diagnostics budget</title>
<style>
 body{font:14px/1.5 system-ui,sans-serif;margin:2rem;background:#12100e;color:#f2efe9}
 h1{font-size:1.25rem;margin:0 0 .25rem}
 p{color:#a9a29a;margin:0 0 1.5rem}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr));gap:1.5rem}
 figure{margin:0}
 img{width:100%%;height:auto;border:1px solid #3a352f;border-radius:.25rem;background:#fff}
 figcaption{margin-top:.5rem;color:#a9a29a;font-size:.8125rem}
</style>
<h1>Contact sheet — %d of %d distinct shots</h1>
<p>Budget %d. The model reads this selection; the full set stays on disk for you.</p>
<div class="grid">
%s
</div>
"""


def write_sheet(path, chosen, unique_count, budget):
    figures = "\n".join(
        '<figure><img src="%s" alt="%s"><figcaption>%s — %s</figcaption></figure>'
        % (os.path.relpath(s["path"], os.path.dirname(path)),
           s["reason"], s["file"], s["reason"])
        for s in chosen)
    with open(path, "w", encoding="utf-8") as f:
        f.write(CONTACT_SHEET % (len(chosen), unique_count, budget, figures))


def self_test():
    import tempfile
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "screenshots")
        for route, width in (("_", 390), ("_", 1440)):
            d = os.path.join(base, "shots%s_%d" % (route, width))
            os.makedirs(d)
            with open(os.path.join(d, "viewport.png"), "wb") as f:
                f.write(b"\x89PNG" + bytes(200) + str(width).encode())
            for i in range(6):
                with open(os.path.join(d, "section-%02d.png" % i), "wb") as f:
                    f.write(b"\x89PNG" + bytes(100 + i * 10))
        shots = collect(base)
        if len(shots) != 14:
            problems.append("collect found %d shots, expected 14" % len(shots))
        chosen, dropped, unique = select(shots, 6)
        if not dropped:
            problems.append("identical sections across viewports were not deduped")
        if len(chosen) > 6:
            problems.append("budget exceeded: %d shots chosen" % len(chosen))
        overviews = [s for s in chosen if s["overview"]]
        if len(overviews) != 2:
            problems.append("coverage lost: %d overviews kept, expected 2"
                            % len(overviews))
        sheet = os.path.join(tmp, "contact-sheet.html")
        write_sheet(sheet, chosen, len(unique), 6)
        if not os.path.getsize(sheet):
            problems.append("contact sheet not written")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-shots: %s" % p)
        return 1
    print("OK: dops-shots self-test (dedup, coverage kept, budget honoured)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--shots", default=None)
    ap.add_argument("--budget", type=int, default=6)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = os.path.abspath(args.root)
    shots_dir = args.shots or os.path.join(root, "artifacts", "audit",
                                           "screenshots")
    if not os.path.isdir(shots_dir):
        print("no screenshots at %s — run the browser floor first" % shots_dir)
        return 1

    shots = collect(shots_dir)
    if not shots:
        print("no PNGs under %s" % shots_dir)
        return 1
    chosen, dropped, unique = select(shots, args.budget)

    out_dir = os.path.join(root, "artifacts", "audit")
    os.makedirs(out_dir, exist_ok=True)
    manifest = {
        "schema": "dops-shots/1",
        "budget": args.budget,
        "found": len(shots),
        "distinct": len(unique),
        "deduped": len(dropped),
        "read_these": [
            {"path": os.path.relpath(s["path"], root), "route": s["route"],
             "viewport": s["viewport"], "reason": s["reason"],
             "sha256": s["sha256"]} for s in chosen],
    }
    manifest_path = os.path.join(out_dir, "shots-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    sheet_path = os.path.join(out_dir, "contact-sheet.html")
    write_sheet(sheet_path, chosen, len(unique), args.budget)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print("shots: %d found, %d distinct, %d selected (budget %d)"
              % (len(shots), len(unique), len(chosen), args.budget))
        for s in chosen:
            print("  %-46s %s" % (os.path.relpath(s["path"], root), s["reason"]))
        print("  manifest: %s" % manifest_path)
        print("  contact sheet (for you, not the model): %s" % sheet_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
