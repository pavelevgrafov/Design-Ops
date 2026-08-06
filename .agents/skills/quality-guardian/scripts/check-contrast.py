#!/usr/bin/env python3
"""check-contrast.py — D3: WCAG contrast on semantic token pairs.

Reads compiled tokens.css (from compile-tokens.py), resolves the declared
contrast-pairs, computes WCAG 2.x relative luminance ratios:
  4.5:1 normal text, 3:1 large text & UI chrome (reported separately).

Usage: python3 check-contrast.py [tokens.css] [--dark]
Exit 0 = all pairs pass, 1 = failures printed.
Stdlib only.
"""
import argparse, json, re, sys

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
    # Declared in $meta.contrastPairs since v7.0 but never gated until v7.2 —
    # the two lists had drifted. Thresholds decided 2026-08-06 (owner: Pavel):
    # the text tiers are normal text; the tertiary tier is UI chrome, so it
    # answers to the 3:1 floor, not 4.5:1.
    ("--text-primary", "--canvas", "text tier 1", 4.5),
    ("--text-secondary", "--canvas", "text tier 2", 4.5),
    ("--text-tertiary", "--canvas-raised", "text tier 3 (UI chrome)", 3.0),
    # Eighth pair, declared in С-1 (Kimi's suggestion on the Т-1 review): focus
    # visibility is non-text UI (SC 1.4.11), so 3:1 — the same class of gap as
    # the tertiary tier, caught before it could hide anything rather than after.
    ("--focus-ring", "--canvas", "focus ring (non-text)", 3.0),
]


def kebab(name):
    return "--" + re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name).lower()


def declared_pairs(tokens_json):
    """`$meta.contrastPairs` is where the skin DECLARES its geometry (move 8).
    This list and PAIRS above are two copies of the same idea, and two copies
    drift — silently, which [A.10] calls a defect. Reporting the difference is
    not the same as gating on it: which floor a newly-surfaced pair must meet
    (4.5 normal text vs 3.0 large text and UI chrome) is a design decision,
    and this script is not the place to make it. Report, then decide."""
    try:
        with open(tokens_json, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    return [(p.get("foreground"), p.get("background"))
            for p in doc.get("$meta", {}).get("contrastPairs", [])
            if p.get("foreground") and p.get("background")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("css", nargs="?", default="tokens.css")
    ap.add_argument("--dark", action="store_true", help="also check [data-theme=dark] scope")
    ap.add_argument("--tokens", default=None,
                    help="tokens.json — report pairs the skin declares in "
                         "$meta.contrastPairs but this check never measures")
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

    if args.tokens:
        declared = declared_pairs(args.tokens)
        if declared is None:
            print(f"note: could not read {args.tokens} — declared-pair report skipped")
        else:
            gated = {(fg, bg) for fg, bg, _l, _m in PAIRS}
            light = scopes[0][1]
            extra = 0
            for fg, bg in declared:
                if (kebab(fg), kebab(bg)) in gated:
                    continue
                fv, bv = light.get(kebab(fg)), light.get(kebab(bg))
                if not fv or not bv:
                    continue
                frgb, brgb = to_rgb(fv), to_rgb(bv)
                if frgb is None or brgb is None:
                    continue
                r = ratio(frgb, brgb)
                extra += 1
                verdict = "meets 4.5:1" if r >= 4.5 else (
                    "large text / UI chrome only" if r >= 3.0 else "below 3:1")
                print(f"declared-not-gated: {fg} on {bg} = {r:.2f}:1 — {verdict}")
            if extra:
                print(f"note: {extra} pair(s) declared in $meta.contrastPairs are "
                      f"not part of this check's gate. Decide per pair whether it "
                      f"is normal text (4.5:1) or UI chrome (3:1), then add it to "
                      f"PAIRS — an undecided declaration is drift [A.10].")

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
