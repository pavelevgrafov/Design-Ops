#!/usr/bin/env python3
"""validate-layers.py — token-validator: project token architecture (D.37, Tier 1).

Verifies any DTCG tokens.json against the v7.0 layer contract
(source: knowledge/token-architecture-3layer, invariant A.21):

1. DTCG shape: every leaf carries $value (and $type).
2. References resolve inside the document.
3. Layer discipline: component → semantic only; semantic → primitive or
   semantic; primitive → primitive. Never back down the chain.
4. Dark layer (if present) mirrors the light semantic color keys.
5. Report: counts per layer, unresolved refs, violations.

Usage: python3 validate-layers.py <tokens.json> [--self-test]
Exit: 0 pass, 1 violations, 2 usage/io.
"""
import json, os, re, sys

REF_RE = re.compile(r"^\{(.+)\}$")

def flatten(node, path, out, problems):
    if isinstance(node, dict):
        if "$value" in node:
            if "$type" not in node:
                problems.append(f"token {'.'.join(path)} missing $type")
            out[".".join(path)] = node["$value"]
            return
        for k, v in node.items():
            if k.startswith("$") or k == "comment":
                continue
            flatten(v, path + [k], out, problems)
    else:
        problems.append(f"non-token leaf at {'.'.join(path)}")

def validate(path, quiet=False):
    problems, notes = [], []
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: cannot read {path}: {e}")
        return 1
    flat = {}
    flatten(doc, [], flat, problems)
    layers = {"primitive": 0, "semantic": 0, "component": 0, "other": 0}
    for key in flat:
        top = key.split(".")[0]
        layers[top if top in layers else "other"] += 1

    for key, val in flat.items():
        if not isinstance(val, str):
            continue
        m = REF_RE.match(val.strip())
        if not m:
            continue
        ref = m.group(1)
        if ref not in flat:
            problems.append(f"{key}: unresolved reference {{{ref}}}")
            continue
        if key.startswith("component.") and not ref.startswith("semantic."):
            problems.append(f"{key}: component must reference semantic.* (got {{{ref}}}) [A.21]")
        elif key.startswith("semantic.") and not (
                ref.startswith("primitive.") or ref.startswith("semantic.")):
            problems.append(f"{key}: semantic must reference primitive.*/semantic.* (got {{{ref}}}) [A.21]")
        elif key.startswith("primitive.") and not ref.startswith("primitive."):
            problems.append(f"{key}: primitive must reference primitive.* (got {{{ref}}}) [A.21]")

    light = {k[len("semantic."):] for k in flat
             if k.startswith("semantic.") and not k.startswith("semantic.dark.")
             and k.startswith("semantic.color.")}
    dark = {k[len("semantic.dark."):] for k in flat if k.startswith("semantic.dark.color.")}
    if dark:
        missing = sorted(light - dark)
        if missing:
            problems.append(f"dark layer misses semantic color keys: {missing}")
    else:
        notes.append("no dark layer (allowed; add when the direction ships a dark theme)")

    if layers["primitive"] == 0 or layers["semantic"] == 0:
        problems.append("missing required layers: primitive.* and semantic.* are mandatory")

    if not quiet:
        print(f"layers: {layers['primitive']} primitive / {layers['semantic']} semantic "
              f"/ {layers['component']} component; dark={'yes' if dark else 'no'}")
    for n in notes:
        print(f"note: {n}")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} token-architecture problem(s) [D.37]")
        return 1
    print(f"OK: token architecture valid [D.37]")
    return 0

BAD = {
    "primitive": {"color": {"red": {"500": {"$value": "#ff0000", "$type": "color"}}}},
    "semantic": {"color": {"ink": {"$value": "{primitive.color.red.500}", "$type": "color"}}},
    "component": {"button": {"bg": {"$value": "{primitive.color.red.500}", "$type": "color"}}},
}

def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump(BAD, f)
        if validate(bad, quiet=True) == 0:
            print("self-test FAIL: component→primitive violation not caught")
            return 1
        skins = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "..", "skins")
        for skin in ("base-site", "base-app"):
            if validate(os.path.join(skins, skin, "tokens.json"), quiet=True) != 0:
                print(f"self-test FAIL: {skin} tokens.json invalid")
                return 1
    print("OK: token-validator self-test (violation caught, both skins valid)")
    return 0

def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    return validate(args[0])

if __name__ == "__main__":
    sys.exit(main())
