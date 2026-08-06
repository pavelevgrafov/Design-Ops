#!/usr/bin/env python3
"""inject.py — deterministic content injection for the starter_first route
(v6.0, TZ-3). No markup generation: values from the brief fill the text of
`data-slot` elements per the starter's copy-map.yaml.

Usage:
  python3 inject.py <starter-dir> <values.yaml> [--out <dir>]

  <starter-dir>  starter root with copy-map.yaml + skeleton/ (+ ux/)
  <values.yaml>  flat {field: value} map (subset of copy-map fields)
  --out          output dir (default: <starter-dir>/_injected)
  --ux-out       where the starter's experience model lands
                 (default: <out>/../artifacts/ux)
  --contract     contract to stamp with the model's origin (AC-23)
                 (default: <out>/../artifacts/design-contract.yaml)

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


def stamp_origin(contract_path, starter_name):
    """Record `artifacts.ux.origin: inherited` in the project's contract.

    Written as a targeted text edit rather than a load-and-dump: the contract
    carries comments that explain the decisions in it, and yaml.dump would
    delete every one of them. Rewriting a document to add one field, and
    losing the reasoning as a side effect, is the kind of silent damage [A.10]
    exists to prevent.
    """
    if not contract_path or not os.path.isfile(contract_path):
        print("note: no contract at %s — the experience model is not marked "
              "`inherited`, and a quick-mode run will read it as produced "
              "(AC-23)" % contract_path)
        return False
    with open(contract_path, encoding="utf-8") as f:
        text = f.read()
    block = ("artifacts:\n"
             "  ux: {origin: inherited, source_starter: \"%s\"}\n" % starter_name)
    if re.search(r"^artifacts:\s*$", text, re.M):
        if re.search(r"^\s+ux:", text, re.M):
            text = re.sub(r"^(\s+ux:).*$",
                          r"\1 {origin: inherited, source_starter: \"%s\"}"
                          % starter_name, text, count=1, flags=re.M)
        else:
            text = re.sub(r"^(artifacts:\s*)$",
                          r"\1\n  ux: {origin: inherited, source_starter: \"%s\"}"
                          % starter_name, text, count=1, flags=re.M)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += block
    with open(contract_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("contract marked: artifacts.ux.origin=inherited (from %s)" % starter_name)
    return True


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
    ux_dir = None
    if "--ux-out" in sys.argv:
        ux_dir = sys.argv[sys.argv.index("--ux-out") + 1]
    src = os.path.join(starter, "skeleton")
    if not os.path.isdir(src):
        print(f"fail: {src} not found", file=sys.stderr)
        return 2

    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(src, out)

    # The starter's verified experience model travels WITH the structure.
    # Without it a starter_first project leaves D18 and D.38 `unavailable`
    # forever: the structure arrives pre-verified, but the model that proves
    # it stays behind in the starter. `--ux-out` puts it where K3 looks.
    model = os.path.join(starter, "ux", "experience-model.yaml")
    if os.path.isfile(model):
        ux_out = ux_dir or os.path.join(os.path.dirname(out.rstrip(os.sep)),
                                        "artifacts", "ux")
        os.makedirs(ux_out, exist_ok=True)
        shutil.copy2(model, os.path.join(ux_out, "experience-model.yaml"))
        print("experience model -> %s" % ux_out)
        # AC-23: mark HOW the model got here. Inherited is exempt from the
        # quick-mode ceiling, produced is not, and the ceiling check has no
        # other way to tell them apart.
        contract = None
        if "--contract" in sys.argv:
            contract = sys.argv[sys.argv.index("--contract") + 1]
        else:
            contract = os.path.join(os.path.dirname(out.rstrip(os.sep)),
                                    "artifacts", "design-contract.yaml")
        stamp_origin(contract, os.path.basename(starter.rstrip(os.sep)))
    else:
        print("note: %s ships no experience model — D18/D.38 will report "
              "`unavailable` for this project" % starter)

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
