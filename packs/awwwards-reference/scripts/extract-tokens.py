#!/usr/bin/env python3
"""extract-tokens.py — awwwards-reference: CSS-only token extraction.

Dembrandt-style, offline: reads a CSS file (e.g. saved from a reference
site) and drafts DTCG tokens — colors (usage-clustered), font families,
font sizes, spacing values, radii, shadows. HARD STOP: CSS only — no
WebGL/JS/motion extraction, no network.

Usage:
  python3 extract-tokens.py <file.css> [--out tokens-draft.json]
  python3 extract-tokens.py --self-test
Exit: 0 draft emitted, 1 nothing extractable, 2 usage.
"""
import json, re, sys
from collections import Counter

HEX_RE = re.compile(r"#(?:[0-9a-f]{6}|[0-9a-f]{3})\b", re.I)
FONT_RE = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)
SIZE_RE = re.compile(r"font-size\s*:\s*([0-9.]+(?:px|rem|em))", re.I)
SPACE_RE = re.compile(r"(?:padding|margin|gap)(?:-[a-z]+)?\s*:\s*([0-9.]+(?:px|rem))", re.I)
RADIUS_RE = re.compile(r"border-radius\s*:\s*([0-9.]+(?:px|rem|%))", re.I)
SHADOW_RE = re.compile(r"box-shadow\s*:\s*([^;}]+)", re.I)


def norm_hex(h):
    h = h.lower()
    if len(h) == 4:
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def cluster(counter, top):
    return [v for v, _n in counter.most_common(top)]


def extract(css_path):
    try:
        with open(css_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"extract-tokens: cannot read {css_path}: {e}", file=sys.stderr)
        sys.exit(2)
    colors = Counter(norm_hex(m.group(0)) for m in HEX_RE.finditer(text))
    fonts = Counter(m.group(1).strip() for m in FONT_RE.finditer(text))
    sizes = Counter(m.group(1) for m in SIZE_RE.finditer(text))
    spaces = Counter(m.group(1) for m in SPACE_RE.finditer(text))
    radii = Counter(m.group(1) for m in RADIUS_RE.finditer(text))
    shadows = Counter(m.group(1).strip() for m in SHADOW_RE.finditer(text))

    draft = {
        "$schema": "https://design-tokens.org/schema/dtcg/2025-10",
        "$meta": {
            "name": "extracted-reference-draft",
            "warning": "DRAFT from CSS extraction — curate into primitive/semantic layers "
                       "before use; component layer references semantic only [A.21].",
        },
        "primitive": {},
    }
    if colors:
        draft["primitive"]["color"] = {
            f"extracted-{i+1}": {"$value": v, "$type": "color"}
            for i, v in enumerate(cluster(colors, 12))
        }
    if fonts:
        draft["primitive"]["font"] = {
            "family": {
                f"extracted-{i+1}": {
                    "$value": [f.strip().strip('"\'') for f in v.split(",")],
                    "$type": "fontFamily",
                } for i, v in enumerate(cluster(fonts, 3))
            }
        }
    if sizes:
        draft["primitive"].setdefault("font", {})["sizes"] = {
            f"extracted-{i+1}": {"$value": v, "$type": "dimension"}
            for i, v in enumerate(cluster(sizes, 8))
        }
    if spaces:
        draft["primitive"]["space"] = {
            f"extracted-{i+1}": {"$value": v, "$type": "dimension"}
            for i, v in enumerate(cluster(spaces, 8))
        }
    if radii:
        draft["primitive"]["radius"] = {
            f"extracted-{i+1}": {"$value": v, "$type": "dimension"}
            for i, v in enumerate(cluster(radii, 4))
        }
    if shadows:
        draft["primitive"]["shadow"] = {
            f"extracted-{i+1}": {"$value": v, "$type": "string"}
            for i, v in enumerate(cluster(shadows, 3))
        }
    return draft


FIXTURE = """
:root { --ink: #1c1917; --paper: #fafaf9; }
h1 { font-family: "Fraunces", Georgia, serif; font-size: 3rem; color: #1c1917; }
body { font-family: "Public Sans", system-ui, sans-serif; font-size: 1rem;
       background: #fafaf9; color: #1c1917; }
.card { padding: 1.5rem; border-radius: 0.5rem;
        box-shadow: 0 1px 2px rgb(0 0 0 / 0.05); margin: 2rem; }
"""

def self_test():
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ref.css")
        with open(p, "w", encoding="utf-8") as f:
            f.write(FIXTURE)
        draft = extract(p)
    prim = draft.get("primitive") or {}
    checks = [
        ("color" in prim and len(prim["color"]) >= 2, "colors clustered"),
        ("font" in prim and "family" in prim["font"], "font families extracted"),
        ("font" in prim and "sizes" in prim["font"], "font sizes extracted"),
        ("space" in prim, "spacing extracted"),
        ("radius" in prim, "radii extracted"),
        ("shadow" in prim, "shadows extracted"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"self-test FAIL: {label}")
            return 1
    print("OK: extract-tokens self-test (CSS-only draft, all categories)")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    draft = extract(args[0])
    if not draft["primitive"]:
        print("extract-tokens: nothing extractable (no CSS tokens found)")
        return 1
    out = None
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        out = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    text = json.dumps(draft, ensure_ascii=False, indent=2)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"OK: draft tokens -> {out} (curate before use)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
