#!/usr/bin/env python3
"""inject.py — deterministic content injection for the starter_first route
(v6.0, TZ-3). No markup generation: values from the brief fill the text of
`data-slot` elements per the starter's copy-map.yaml.

Usage:
  python3 inject.py <starter-dir> <values.yaml> [--out <dir>]

  <starter-dir>  starter root with copy-map.yaml + skeleton/
  <values.yaml>  flat {field: value} map (subset of copy-map fields)
  --out          output dir (default: <starter-dir>/_injected)

Prints the coverage line and the explicit leftover list. Acceptance:
coverage >= 95% of mapped slots (exit 1 below that).
Exit: 0 ok, 1 coverage below 95%, 2 usage/io.
"""
import html
import os
import re
import shutil
import sys

import yaml

COVERAGE_FLOOR = 0.95


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = None
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if len(args) < 2:
        print("usage: inject.py <starter-dir> <values.yaml> [--out dir]",
              file=sys.stderr)
        return 2
    starter, values_path = args[0], args[1]
    out = out or os.path.join(starter, "_injected")

    with open(os.path.join(starter, "copy-map.yaml"), encoding="utf-8") as f:
        cmap = yaml.safe_load(f) or {}
    with open(values_path, encoding="utf-8") as f:
        values = yaml.safe_load(f) or {}
    src = os.path.join(starter, "skeleton")
    if not os.path.isdir(src):
        print(f"fail: {src} not found", file=sys.stderr)
        return 2

    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(src, out)

    filled, leftovers = 0, []
    unknown = [k for k in values if k not in cmap]
    for field, selector in sorted(cmap.items()):
        m = re.fullmatch(r"\[data-slot=([a-z0-9_]+)\]", str(selector).strip())
        if not m:
            leftovers.append(f"{field}: unsupported selector {selector}")
            continue
        slot = m.group(1)
        if field not in values or values[field] in (None, ""):
            leftovers.append(f"{field}: no value in brief")
            continue
        val = html.escape(str(values[field]))
        hits = 0
        for root, _dirs, files in os.walk(out):
            for fn in files:
                if not fn.endswith(".html"):
                    continue
                p = os.path.join(root, fn)
                with open(p, encoding="utf-8") as f:
                    doc = f.read()
                doc, n = re.subn(
                    r'(data-slot="%s"[^>]*>)[^<]*' % re.escape(slot),
                    lambda mo: mo.group(1) + val, doc)
                if n:
                    hits += n
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(doc)
        if hits:
            filled += 1
        else:
            leftovers.append(f"{field}: slot '{slot}' not found in skeleton")

    total = len(cmap)
    cov = filled / total if total else 0
    for k in unknown:
        leftovers.append(f"{k}: value given but not in copy-map (ignored)")
    print(f"injection coverage: {filled}/{total} slots ({cov:.0%}) -> {out}")
    for l in leftovers:
        print(f"leftover: {l}")
    if cov < COVERAGE_FLOOR:
        print(f"fail: coverage below {COVERAGE_FLOOR:.0%} — fill the brief "
              "or fix the copy-map", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
