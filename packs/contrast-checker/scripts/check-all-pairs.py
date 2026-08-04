#!/usr/bin/env python3
"""check-all-pairs.py — contrast-checker: extended WCAG pairs (D.25, Tier 1).

Extends K3 D3 (the four core pairs) to the full v7.0 semantic contract:
text tiers, status hues, focus ring, component button — in BOTH themes
when [data-theme="dark"] exists. Source: knowledge/wcag-22-aa-rules,
knowledge/text-hierarchy-tiers, knowledge/dark-theme-rules.

Pairs (fg/bg, minimum):
  textPrimary/canvas 4.5 · textSecondary/canvas 4.5 · textTertiary/canvas 3.0
  semanticError|Success|Warning|Info/canvas 4.5 (text usage)
  focusRing/canvas 3.0 (non-text, SC 1.4.11)
  button-primary-text/button-primary-bg 4.5 (component layer, when present)

Usage: python3 check-all-pairs.py [tokens.css] [--self-test]
Exit: 0 pass, 1 fail, 2 usage.
"""
import os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", ".agents", "skills",
                                "quality-guardian", "scripts"))
try:
    from importlib import import_module
    cc = import_module("check-contrast")
    parse_vars, to_rgb, ratio = cc.parse_vars, cc.to_rgb, cc.ratio
except Exception:  # pragma: no cover — fallback duplication
    def parse_vars(text, pattern):
        m = re.search(pattern, text, re.S)
        vars_ = {}
        if m:
            for vm in re.finditer(r"--([a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
                vars_[f"--{vm.group(1)}"] = vm.group(2).strip()
        return vars_
    def to_rgb(s):
        s = s.strip()
        m = re.match(r"#([0-9a-f]{6})$", s, re.I)
        if m:
            h = m.group(1)
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", s)
        if m:
            return tuple(int(m.group(i)) for i in (1, 2, 3))
        return None
    def _lum(rgb):
        def ch(c):
            c /= 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (ch(c) for c in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    def ratio(c1, c2):
        l1, l2 = sorted((_lum(c1), _lum(c2)), reverse=True)
        return (l1 + 0.05) / (l2 + 0.05)

PAIRS = [
    ("--text-primary", "--canvas", "primary text", 4.5),
    ("--text-secondary", "--canvas", "secondary text", 4.5),
    ("--text-tertiary", "--canvas", "tertiary text (hints)", 3.0),
    ("--semantic-error", "--canvas", "error on canvas", 4.5),
    ("--semantic-success", "--canvas", "success on canvas", 4.5),
    ("--semantic-warning", "--canvas", "warning on canvas", 4.5),
    ("--semantic-info", "--canvas", "info on canvas", 4.5),
    ("--focus-ring", "--canvas", "focus ring (non-text)", 3.0),
    ("--button-primary-text", "--button-primary-bg", "button text (component)", 4.5),
]

def run(css_path):
    try:
        with open(css_path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"FAIL: {css_path} not found — run compile-tokens.py first")
        return 1
    scopes = [("light", parse_vars(text, r":root\s*\{(.*?)\}"))]
    if 'data-theme="dark"' in text:
        scopes.append(("dark", parse_vars(text, r'\[data-theme="dark"\]\s*\{(.*?)\}')))
    problems, checked, skipped = [], 0, 0
    for scope_name, vars_ in scopes:
        if not vars_:
            continue
        for fg_name, bg_name, label, minimum in PAIRS:
            fg, bg = vars_.get(fg_name), vars_.get(bg_name)
            if fg is None or bg is None:
                skipped += 1
                continue
            frgb, brgb = to_rgb(fg), to_rgb(bg)
            if frgb is None or brgb is None:
                problems.append(f"[{scope_name}] unparseable: {fg_name}={fg} / {bg_name}={bg}")
                continue
            r = ratio(frgb, brgb)
            checked += 1
            status = "pass" if r >= minimum else "FAIL"
            print(f"[{scope_name}] {label}: {r:.2f}:1 (need {minimum}:1) — {status}")
            if r < minimum:
                problems.append(f"[{scope_name}] {label} {r:.2f}:1 < {minimum}:1")
    if checked == 0:
        print("FAIL: no extended pairs could be checked (tokens missing?)")
        return 1
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} extended-contrast problem(s) [D.25]")
        return 1
    print(f"OK: {checked} extended pair(s) meet WCAG ({skipped} absent, reported) [D.25]")
    return 0

def self_test():
    here = os.path.dirname(os.path.abspath(__file__))
    skins = os.path.join(here, "..", "..", "..", "skins")
    ok = True
    for skin in ("base-site", "base-app"):
        css = os.path.join(skins, skin, "tokens.css")
        if not os.path.exists(css):
            print(f"self-test FAIL: {css} missing — compile skins first")
            ok = False
            continue
        rc = run(css)
        if rc != 0:
            print(f"self-test FAIL: {skin} extended pairs red")
            ok = False
    if ok:
        print("OK: contrast-checker self-test (both skins, both themes)")
        return 0
    return 1

def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    return run(args[0] if args else "tokens.css")

if __name__ == "__main__":
    sys.exit(main())
