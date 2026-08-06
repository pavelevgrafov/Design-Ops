#!/usr/bin/env python3
"""dops_color.py — the one place colour maths lives.

Design: Kimi, `Most/tasks/2026-08-06-kimi-t1-dark-ramp-spec.md` §3.1.

Three consumers already need the same arithmetic — the dark-ramp generator
(Т-1), the panel emitter (П-4) and whatever reads colour next (С-1) — and a
second copy of a formula is drift the moment one of them is corrected [A.10].
So: WCAG luminance and hex parsing are *imported* from `check-contrast.py`,
which owns them and is the script the floor runs; HSL and the alpha-composite
live here, because nothing owned them before.

Rounding is pinned rather than left to the platform: a generator whose output
depends on float noise cannot claim idempotency, and `--check` would then fail
on a machine that rounds the other way. Channels are rounded half-up after
being quantised to 6 decimals, which is far below the 1/255 a channel can
express and far above float error.

Stdlib only. Not a CLI — `python3 dops_color.py --self-test` is the exception.
"""
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)


def _contrast_module():
    """check-contrast.py is a hyphenated script, not an importable name."""
    path = os.path.join(PKG_ROOT, ".agents", "skills", "quality-guardian",
                        "scripts", "check-contrast.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("dops_check_contrast", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


_CC = _contrast_module()


# --------------------------------------------------------------------------
# hex <-> channels
# --------------------------------------------------------------------------
def round_channel(value):
    """Half-up, as pinned above. `round()` in Python 3 is half-to-even, which
    would send 36.5 to 36 and 37.5 to 38 — two neighbouring tones rounded by
    two different rules."""
    return int(math.floor(round(value, 6) + 0.5))


def parse_hex(value):
    """`#e0e0e0` -> `(224, 224, 224)`. Delegates the parsing itself to D3 so
    that whatever D3 accepts, the generator accepts — no second syntax."""
    if _CC is None:
        return None
    rgb = _CC.to_rgb(value)
    if rgb is None:
        return None
    return tuple(round_channel(c * 255) for c in rgb)


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def contrast(a, b):
    """WCAG 2.x ratio between two colours written as CSS strings."""
    if _CC is None:
        return None
    ra, rb = _CC.to_rgb(a), _CC.to_rgb(b)
    if ra is None or rb is None:
        return None
    return _CC.ratio(ra, rb)


def relative_luminance(value):
    if _CC is None:
        return None
    rgb = _CC.to_rgb(value)
    return None if rgb is None else _CC.luminance(rgb)


# --------------------------------------------------------------------------
# HSL — new here, because nothing owned it
# --------------------------------------------------------------------------
def rgb_to_hsl(rgb):
    """Channels 0-255 in, (h in degrees, s, l) in 0..1 out."""
    r, g, b = (c / 255.0 for c in rgb)
    hi, lo = max(r, g, b), min(r, g, b)
    l = (hi + lo) / 2.0
    d = hi - lo
    if d == 0:
        return 0.0, 0.0, l
    s = d / (2.0 - hi - lo) if l > 0.5 else d / (hi + lo)
    if hi == r:
        h = ((g - b) / d) % 6.0
    elif hi == g:
        h = (b - r) / d + 2.0
    else:
        h = (r - g) / d + 4.0
    return h * 60.0, s, l


def hsl_to_rgb(h, s, l):
    """Inverse of the above; channels come back rounded half-up."""
    h = h % 360.0
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = l - c / 2.0
    seg = int(h // 60) % 6
    r, g, b = [(c, x, 0.0), (x, c, 0.0), (0.0, c, x),
               (0.0, x, c), (x, 0.0, c), (c, 0.0, x)][seg]
    return tuple(round_channel((v + m) * 255.0) for v in (r, g, b))


# --------------------------------------------------------------------------
# the dark-theme model
# --------------------------------------------------------------------------
def overlay(base_rgb, alpha, over=(255, 255, 255)):
    """Composite `over` at `alpha` on top of `base_rgb`, per channel.

    This is the dark-theme overlay model in one line: emphasis and elevation
    in a dark UI are white at some opacity over one base surface, never a
    separate hand-picked colour (knowledge/dark-theme-rules)."""
    return tuple(round_channel(b * (1.0 - alpha) + o * alpha)
                 for b, o in zip(base_rgb, over))


def lighten_desaturate(rgb, lighten, desaturate):
    """The light-to-dark accent transform: raise lightness by a share of the
    remaining headroom, cut saturation by a share of what is there.

    `L' = L + (1-L)·lighten` rather than `L·(1+lighten)` because the second
    form has no ceiling and clips on already-light tones."""
    h, s, l = rgb_to_hsl(rgb)
    return hsl_to_rgb(h, s * (1.0 - desaturate), l + (1.0 - l) * lighten)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def self_test():
    fails = []

    if _CC is None:
        fails.append("check-contrast.py did not import — colour maths has no owner")

    # round-half-up, the pinned rule
    for value, want in ((36.5, 37), (37.5, 38), (36.4999, 36), (0.5, 1)):
        got = round_channel(value)
        if got != want:
            fails.append("round_channel(%s) = %s, want %s" % (value, got, want))

    if _CC is not None:
        if parse_hex("#e0e0e0") != (224, 224, 224):
            fails.append("parse_hex lost precision on #e0e0e0")
        if to_hex((18, 18, 18)) != "#121212":
            fails.append("to_hex is not the inverse of parse_hex")

        # the anchor of visual continuity: 87% white over #121212 is today's ink
        if to_hex(overlay((18, 18, 18), 0.87)) != "#e0e0e0":
            fails.append("overlay 87%% over #121212 is not #e0e0e0")
        if to_hex(overlay((18, 18, 18), 0.12)) != "#2e2e2e":
            fails.append("overlay 12%% over #121212 is not #2e2e2e")

        # HSL round-trip: every channel comes back where it started
        for hexv in ("#1e9468", "#4cba8b", "#121212", "#ffffff", "#8f8b85"):
            rgb = parse_hex(hexv)
            back = hsl_to_rgb(*rgb_to_hsl(rgb))
            if max(abs(a - b) for a, b in zip(rgb, back)) > 1:
                fails.append("HSL round-trip moved %s to %s" % (hexv, to_hex(back)))

        # the transform only ever lightens and only ever desaturates
        for hexv in ("#1e9468", "#0a4e2f", "#1697b0"):
            src = parse_hex(hexv)
            out = lighten_desaturate(src, 0.40, 0.35)
            _h0, s0, l0 = rgb_to_hsl(src)
            _h1, s1, l1 = rgb_to_hsl(out)
            if l1 <= l0:
                fails.append("lighten_desaturate did not lighten %s" % hexv)
            if s1 > s0 + 1e-6:
                fails.append("lighten_desaturate did not desaturate %s" % hexv)

        if abs(contrast("#ffffff", "#000000") - 21.0) > 0.01:
            fails.append("contrast(white, black) is not 21:1")

    for f in fails:
        print("FAIL: %s" % f)
    if fails:
        print("\n%d colour problem(s)" % len(fails))
        return 1
    print("OK: dops-color self-test (rounding, hex, overlay model, HSL, transform)")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    print(__doc__.strip().splitlines()[0])
    sys.exit(2)
