#!/usr/bin/env python3
"""check-contrast.py — D3: WCAG contrast on semantic token pairs.

Reads compiled tokens.css (from compile-tokens.py), resolves the declared
contrast-pairs, computes WCAG 2.x relative luminance ratios:
  4.5:1 normal text, 3:1 large text & UI chrome (reported separately).

Usage: python3 check-contrast.py [tokens.css] [--dark]
Exit 0 = all pairs pass, 1 = failures printed.
Stdlib only.
"""
import argparse, re, sys

def parse_vars(css_text, scope_pat):
    m = re.search(scope_pat, css_text, re.S)
    scope = m.group(1) if m else ""
    out = {}
    for name, val in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", scope, re.I):
        out[name] = val.strip()
    return out

def to_rgb(color):
    color = color.strip()
    m = re.match(r"#([0-9a-fA-F]{3,8})$", color)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    m = re.match(r"rgba?\(([^)]+)\)", color)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")[:3]]
        vals = []
        for p in parts:
            vals.append(float(p[:-1]) / 100 if p.endswith("%") else float(p) / 255)
        return tuple(vals[:3])
    m = re.match(r"hsla?\(([^)]+)\)", color)
    if m:
        p = [x.strip().rstrip("%deg") for x in re.split(r"[,\s]+", m.group(1)) if x and x != "/"]
        h, s, l = float(p[0]) % 360, float(p[1]) / 100, float(p[2]) / 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m0 = l - c / 2
        for lo, hi in ((0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 360)):
            if lo <= h < hi:
                seg = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][(lo // 60)]
                return tuple(v + m0 for v in seg)
    return None

def luminance(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(c1, c2):
    l1, l2 = sorted((luminance(c1), luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

PAIRS = [
    ("--ink", "--canvas", "body text", 4.5),
    ("--ink-muted", "--canvas", "muted text", 4.5),
    ("--action-primary-text", "--action-primary", "button text", 4.5),
    ("--ink-on-dark", "--surface-dark", "text on dark", 4.5),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("css", nargs="?", default="tokens.css")
    ap.add_argument("--dark", action="store_true", help="also check [data-theme=dark] scope")
    args = ap.parse_args()

    try:
        with open(args.css, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"FAIL: {args.css} not found — run compile-tokens.py first")
        return 1

    scopes = [("light", parse_vars(text, r":root\s*\{(.*?)\}"))]
    if args.dark or 'data-theme="dark"' in text:
        scopes.append(("dark", parse_vars(text, r'\[data-theme="dark"\]\s*\{(.*?)\}')))

    problems, checked = [], 0
    for scope_name, vars_ in scopes:
        if not vars_:
            continue
        for fg_name, bg_name, label, minimum in PAIRS:
            fg, bg = vars_.get(fg_name), vars_.get(bg_name)
            if fg is None or bg is None:
                if scope_name == "light":
                    problems.append(f"[{scope_name}] missing token(s) for {fg_name}/{bg_name}")
                continue
            frgb, brgb = to_rgb(fg), to_rgb(bg)
            if frgb is None or brgb is None:
                problems.append(f"[{scope_name}] unparseable color in {fg_name}={fg} or {bg_name}={bg}")
                continue
            r = ratio(frgb, brgb)
            checked += 1
            status = "pass" if r >= minimum else ("FAIL" if r < 3.0 else "FAIL(normal)/pass(large)")
            print(f"[{scope_name}] {label}: {fg_name} on {bg_name} = {r:.2f}:1 (need {minimum}:1) — {status}")
            if r < minimum:
                problems.append(f"[{scope_name}] {label} {r:.2f}:1 < {minimum}:1 ({fg_name} on {bg_name})")

    if checked == 0:
        print("FAIL: no contrast pairs could be checked (tokens missing?)")
        return 1
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} contrast problem(s) — fix semantic tokens and recompile")
        return 1
    print(f"OK: {checked} pair(s) meet WCAG contrast")
    return 0

if __name__ == "__main__":
    sys.exit(main())
