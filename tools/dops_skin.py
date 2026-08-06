#!/usr/bin/env python3
"""dops_skin.py — the declared dark ramp (Т-1).

Design: Kimi, `Most/tasks/2026-08-06-kimi-t1-dark-ramp-spec.md`.

Before this move the dark layer of a skin was sixteen hand-written literals
under a comment that described the model in prose: "text 87/60/38% over
#121212, action lightened 40% + desaturated". Prose cannot be checked, so the
values and the sentence were free to drift apart, and П-4 could offer no dark
colour knob at all — a literal declares no alternatives, and the emitter is
not allowed to invent them.

Т-1 moves that sentence into `$meta.darkModel` and makes this script the only
hand that writes the tones it implies. Two consequences follow without any
further code: the panel finds declared ramps behind the dark tokens and builds
dark knobs on its own, and a hand-edited dark tone stops being invisible —
`--check` recomputes the model and fails the build on any difference.

What is generated (per skin, into `primitive.color`):

  darkInk      one tone per `inkEmphasis` step — white at N% over `base`
  darkSurface  `0` plus one tone per `elevation` step — the same composite
  accentDark   the light `accent` ramp under `lighten` + `desaturate`

What is NOT generated: which tone each semantic role takes. That
`inkMuted` is the 60% tier and not the 38% one is a design decision, so it
stays authored in the skin — this script only refuses to let it be a literal.

Usage:
  dops skin darkramp --skin base-site [--root DIR]
  dops skin darkramp --skin base-site --check
  dops skin darkramp --all [--check]
  dops skin darkramp --tokens path/to/tokens.json [--check]

Exit: 0 ok, 1 drift / refused (nothing written), 2 usage/io.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dops_color as colour          # noqa: E402  (the one colour module)
import dops_panel as panel           # noqa: E402  (the pointed JSON patch)

FLAGSHIP_SKINS = ("base-site", "base-app")

INK_RAMP = "darkInk"
SURFACE_RAMP = "darkSurface"
ACCENT_RAMP = "accentDark"
GENERATED = (INK_RAMP, SURFACE_RAMP, ACCENT_RAMP)

RAMP_COMMENT = ("generated from $meta.darkModel by `dops skin darkramp`; "
                "do not hand-edit — drift fails the build")
DARK_COMMENT = ("Dark theme = separate design, not an inversion "
                "(knowledge/dark-theme-rules). Every value below is a reference "
                "into a ramp generated from $meta.darkModel by "
                "`dops skin darkramp`; do not hand-edit — drift fails the build. "
                "Which tone a role takes is the design decision and lives here; "
                "what that tone *is* lives in the model.")


# --------------------------------------------------------------------------
# reading the declaration
# --------------------------------------------------------------------------
def read_model(doc):
    model = ((doc.get("$meta") or {}).get("darkModel")
             if isinstance(doc, dict) else None)
    return model if isinstance(model, dict) else None


def model_problems(model, doc):
    """A malformed model must fail loudly here rather than quietly produce a
    plausible-looking ramp: these numbers become the whole dark theme."""
    out = []
    base = model.get("base")
    if not isinstance(base, str) or colour.parse_hex(base) is None:
        out.append("$meta.darkModel.base is not a colour: %r" % (base,))
    steps = model.get("inkEmphasis")
    if not isinstance(steps, list) or not steps:
        out.append("$meta.darkModel.inkEmphasis must be a non-empty list of percentages")
    else:
        for s in steps:
            if not isinstance(s, (int, float)) or not 0 <= s <= 100:
                out.append("inkEmphasis step %r is not a percentage in 0..100" % (s,))
        if sorted(steps, reverse=True) != list(steps):
            out.append("inkEmphasis must be declared from most to least emphatic — "
                       "the order is the ramp's order")
    elev = model.get("elevation")
    if not isinstance(elev, dict) or not elev:
        out.append("$meta.darkModel.elevation must be a non-empty object")
    else:
        seen = []
        for name, pct in elev.items():
            if not isinstance(pct, (int, float)) or not 0 <= pct <= 100:
                out.append("elevation.%s = %r is not a percentage in 0..100" % (name, pct))
            else:
                seen.append(pct)
        if sorted(seen) != seen:
            out.append("elevation steps must be declared from lowest to highest — "
                       "a surface that rises must get lighter, not darker")
    acc = model.get("accent")
    if not isinstance(acc, dict):
        out.append("$meta.darkModel.accent must declare lighten and desaturate")
    else:
        for key in ("lighten", "desaturate"):
            v = acc.get(key)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                out.append("accent.%s = %r is not a share in 0..1" % (key, v))
    if not light_accent(doc):
        out.append("primitive.color.accent has no tones — nothing to transform "
                   "into %s" % ACCENT_RAMP)
    return out


def light_accent(doc):
    """The light accent ramp, in its declared order — `accentDark` mirrors it
    tone for tone so the two ramps stay addressable by the same keys."""
    node = ((doc.get("primitive") or {}).get("color") or {}).get("accent") or {}
    return [(k, v["$value"]) for k, v in node.items()
            if isinstance(v, dict) and isinstance(v.get("$value"), str)]


# --------------------------------------------------------------------------
# the generator
# --------------------------------------------------------------------------
def generate(doc, model):
    """{ramp name: {tone key: hex}} — the whole output of the model."""
    base = colour.parse_hex(model["base"])
    ink = {}
    for pct in model["inkEmphasis"]:
        ink[tone_key(pct)] = colour.to_hex(colour.overlay(base, pct / 100.0))

    surface = {"0": colour.to_hex(tuple(base))}
    for name, pct in model["elevation"].items():
        surface[name] = colour.to_hex(colour.overlay(base, pct / 100.0))

    acc = model["accent"]
    accent = {}
    for key, hexv in light_accent(doc):
        rgb = colour.parse_hex(hexv)
        if rgb is None:
            continue
        accent[key] = colour.to_hex(
            colour.lighten_desaturate(rgb, acc["lighten"], acc["desaturate"]))

    return {INK_RAMP: ink, SURFACE_RAMP: surface, ACCENT_RAMP: accent}


def tone_key(pct):
    """`87` and not `87.0`: the key is written into the skin and referenced by
    hand, so it must be the shortest honest spelling of the number."""
    return str(int(pct)) if float(pct) == int(pct) else str(pct)


def current_ramps(doc):
    node = ((doc.get("primitive") or {}).get("color") or {})
    out = {}
    for name in GENERATED:
        ramp = node.get(name)
        if not isinstance(ramp, dict):
            continue
        out[name] = {k: v["$value"] for k, v in ramp.items()
                     if isinstance(v, dict) and isinstance(v.get("$value"), str)}
    return out


# --------------------------------------------------------------------------
# writing: the same pointed patch the panel and the injector use
# --------------------------------------------------------------------------
def render_ramp(tones, key_indent=6):
    pad = " " * (key_indent + 2)
    lines = ["{", '%s"comment": %s,'
                  % (pad, json.dumps(RAMP_COMMENT, ensure_ascii=False))]
    for key, hexv in tones.items():
        lines.append('%s%s: { "$value": "%s", "$type": "color" },'
                     % (pad, json.dumps(key), hexv))
    lines[-1] = lines[-1].rstrip(",")
    lines.append(" " * key_indent + "}")
    return "\n".join(lines)


def insert_after(text, parent_dotted, anchor_key, new_key, block, key_indent=6):
    """Add a key right after `anchor_key` inside `parent_dotted`. Used the
    first time a skin declares a model: the ramps do not exist yet, and a
    load-and-dump would flatten every comment in the file."""
    parent = panel.locate(text, parent_dotted)
    if parent is None:
        return None
    span = panel.span_of_key(text, anchor_key, parent[0], parent[1])
    if span is None:
        return None
    at = span[1]
    return (text[:at] + ',\n%s%s: %s' % (" " * key_indent, json.dumps(new_key), block)
            + text[at:])


def write_ramps(text, wanted, doc):
    anchor = "accent"          # the ramps land after the light accent, in order
    for name in GENERATED:
        block = render_ramp(wanted[name])
        path = "primitive.color." + name
        if panel.locate(text, path) is not None:
            new = panel.patch_value(text, path, block)
        else:
            new = insert_after(text, "primitive.color", anchor, name, block)
        anchor = name
        if new is None:
            return None, "could not place %s in primitive.color" % name
        text = new
    if panel.locate(text, "semantic.dark.comment") is not None:
        new = panel.patch_value(text, "semantic.dark.comment",
                                json.dumps(DARK_COMMENT, ensure_ascii=False))
        if new is not None:
            text = new
    return text, None


# --------------------------------------------------------------------------
# drift
# --------------------------------------------------------------------------
def literal_dark_tokens(doc):
    """After Т-1 every dark colour is a reference. A literal there is the same
    defect the move exists to remove — the value stops being derivable from the
    declaration, silently."""
    node = (((doc.get("semantic") or {}).get("dark") or {}).get("color") or {})
    out = []
    for name, spec in node.items():
        val = spec.get("$value") if isinstance(spec, dict) else None
        if isinstance(val, str) and not val.strip().startswith("{"):
            out.append((name, val))
    return out


def diff(doc, wanted):
    """Every way the file can disagree with its own declaration."""
    have = current_ramps(doc)
    problems = []
    for name in GENERATED:
        mine, theirs = wanted[name], have.get(name)
        if theirs is None:
            problems.append("%s: ramp missing — the model declares it, the skin "
                            "does not have it" % name)
            continue
        for key in mine:
            if key not in theirs:
                problems.append("%s.%s: tone missing (model says %s)"
                                % (name, key, mine[key]))
            elif theirs[key].lower() != mine[key].lower():
                problems.append("%s.%s: %s in the skin, %s from the model"
                                % (name, key, theirs[key], mine[key]))
        for key in theirs:
            if key not in mine:
                problems.append("%s.%s = %s: tone the model does not declare"
                                % (name, key, theirs[key]))
    for name, val in literal_dark_tokens(doc):
        problems.append("semantic.dark.color.%s = %s: a literal, not a reference "
                        "into a generated ramp" % (name, val))
    return problems


# --------------------------------------------------------------------------
# one file
# --------------------------------------------------------------------------
def run_one(tokens_path, check_only, quiet=False):
    try:
        with open(tokens_path, encoding="utf-8") as f:
            text = f.read()
        doc = json.loads(text)
    except (OSError, ValueError) as exc:
        print("skin: cannot read %s: %s" % (tokens_path, exc))
        return 2, 0

    model = read_model(doc)
    if model is None:
        # Honest absence [A.6]: a skin that declares no model has nothing to
        # drift from. Saying so is not the same as passing silently.
        if not quiet:
            print("skin: %s declares no $meta.darkModel — nothing to generate "
                  "or verify" % rel(tokens_path))
        return 0, 0

    bad = model_problems(model, doc)
    if bad:
        for b in bad:
            print("FAIL: %s: %s" % (rel(tokens_path), b))
        return 1, 0

    wanted = generate(doc, model)
    problems = diff(doc, wanted)

    if check_only:
        if problems:
            print("FAIL: %s: dark ramp drifted from $meta.darkModel"
                  % rel(tokens_path))
            for p in problems:
                print("      %s" % p)
            print("      fix: `dops skin darkramp --tokens %s` regenerates the "
                  "tones; change the model, not the tones" % rel(tokens_path))
            return 1, len(problems)
        if not quiet:
            print("OK: %s: %d dark tone(s) match $meta.darkModel"
                  % (rel(tokens_path), sum(len(v) for v in wanted.values())))
        return 0, 0

    new_text, why = write_ramps(text, wanted, doc)
    if new_text is None:
        print("FAIL: %s: %s" % (rel(tokens_path), why))
        return 1, 0
    try:
        json.loads(new_text)
    except ValueError as exc:
        print("FAIL: %s: the patch would break the file (%s) — nothing written"
              % (rel(tokens_path), exc))
        return 1, 0

    changed = new_text != text
    if changed:
        with open(tokens_path, "w", encoding="utf-8") as f:
            f.write(new_text)
    if not quiet:
        print("%s: %s (%d tones: %s)"
              % (rel(tokens_path), "rewritten" if changed else "already current",
                 sum(len(v) for v in wanted.values()),
                 ", ".join("%s×%d" % (n, len(wanted[n])) for n in GENERATED)))
        for name, val in literal_dark_tokens(doc):
            print("  note: semantic.dark.color.%s is still the literal %s — "
                  "rebind it to a ramp tone by hand, the mapping is a design "
                  "decision" % (name, val))
    return 0, 1 if changed else 0


def rel(path):
    try:
        short = os.path.relpath(path, PKG_ROOT)
    except ValueError:
        return path
    # a path that climbs out of the package is not shorter, only harder to read
    return path if short.startswith("..") else short


def skin_tokens(root, name):
    for cand in (os.path.join(root, "skins", name, "tokens.json"),
                 os.path.join(PKG_ROOT, "skins", name, "tokens.json")):
        if os.path.isfile(cand):
            return cand
    return None


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def probe(path, check_only):
    """Run the tool on a deliberately broken copy without printing its verdict.
    These probes are supposed to fail; letting them shout would put four
    convincing FAIL blocks in the middle of a green self-test."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return run_one(path, check_only, quiet=True)


def self_test():
    import copy
    import tempfile

    fails = []
    rc = colour.self_test()
    if rc != 0:
        fails.append("dops_color self-test is red — the maths under this one")

    src = skin_tokens(PKG_ROOT, "base-site")
    if not src:
        print("FAIL: base-site skin not found")
        return 1
    with open(src, encoding="utf-8") as f:
        text = f.read()
    doc = json.loads(text)
    model = read_model(doc)

    if model is None:
        fails.append("base-site declares no $meta.darkModel — Т-1 not applied")
    else:
        wanted = generate(doc, model)

        # 3. the anchor of visual continuity
        if wanted[INK_RAMP].get("87") != "#e0e0e0":
            fails.append("darkInk.87 = %s, not the #e0e0e0 the skin renders today"
                         % wanted[INK_RAMP].get("87"))

        # 6. monotonicity — a swapped parameter must not pass unnoticed
        lums = [colour.relative_luminance(v) for v in wanted[INK_RAMP].values()]
        if lums != sorted(lums, reverse=True):
            fails.append("darkInk is not monotone: emphasis falls but lightness "
                         "does not")
        order = ["0"] + list(model["elevation"].keys())
        slums = [colour.relative_luminance(wanted[SURFACE_RAMP][k])
                 for k in order if k in wanted[SURFACE_RAMP]]
        if slums != sorted(slums):
            fails.append("darkSurface is not monotone: a higher surface is darker")

        # 1. idempotency, on a copy
        tmp = tempfile.mkdtemp(prefix="dops-skin-")
        work = os.path.join(tmp, "tokens.json")
        with open(work, "w", encoding="utf-8") as f:
            f.write(text)
        probe(work, False)
        first = open(work, encoding="utf-8").read()
        probe(work, False)
        second = open(work, encoding="utf-8").read()
        if first != second:
            fails.append("generator is not idempotent — a second run moved bytes")
        if json.loads(first) != json.loads(text):
            fails.append("generator changed a skin that was already current")

        # 2. --check catches a hand-edited tone
        drifted = copy.deepcopy(doc)
        drifted["primitive"]["color"][INK_RAMP]["87"]["$value"] = "#e0e0e1"
        with open(work, "w", encoding="utf-8") as f:
            json.dump(drifted, f)
        code, n = probe(work, True)
        if code == 0 or n == 0:
            fails.append("--check passed a hand-edited dark tone (#e0e0e1)")

        # and a re-literalised semantic token
        relit = copy.deepcopy(doc)
        relit["semantic"]["dark"]["color"]["ink"]["$value"] = "#e0e0e0"
        with open(work, "w", encoding="utf-8") as f:
            json.dump(relit, f)
        code, _n = probe(work, True)
        if code == 0:
            fails.append("--check passed a dark token turned back into a literal")

        # a malformed model is refused, not silently normalised
        broken = copy.deepcopy(doc)
        broken["$meta"]["darkModel"]["elevation"] = {"raised": 16, "modal": 5}
        with open(work, "w", encoding="utf-8") as f:
            json.dump(broken, f)
        code, _n = probe(work, False)
        if code == 0:
            fails.append("an elevation ladder declared upside down was accepted")

        # 4. every dark role resolves into a generated ramp
        for skin in FLAGSHIP_SKINS:
            path = skin_tokens(PKG_ROOT, skin)
            if not path:
                fails.append("%s not found" % skin)
                continue
            sdoc = json.loads(open(path, encoding="utf-8").read())
            lits = literal_dark_tokens(sdoc)
            if lits:
                fails.append("%s: %d dark token(s) still literal: %s"
                             % (skin, len(lits), ", ".join(n for n, _v in lits)))
            code, _n = run_one(path, True, quiet=True)
            if code != 0:
                fails.append("%s: dark ramp drifted from its model" % skin)

    for f in fails:
        print("FAIL: %s" % f)
    if fails:
        print("\n%d dark-ramp problem(s)" % len(fails))
        return 1
    print("OK: dops-skin self-test (model shape, composite anchor, monotonicity, "
          "idempotency, drift, no literals left)")
    return 0


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(prog="dops skin")
    sub = ap.add_subparsers(dest="cmd")
    dr = sub.add_parser("darkramp", help="regenerate the dark ramps from $meta.darkModel")
    dr.add_argument("--skin", default=None)
    dr.add_argument("--tokens", default=None, help="a tokens.json to work on directly")
    dr.add_argument("--all", action="store_true", help="every flagship skin")
    dr.add_argument("--root", default=".")
    dr.add_argument("--check", action="store_true",
                    help="recompute without writing; drift is exit 1")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.cmd != "darkramp":
        ap.print_help()
        return 2

    targets = []
    if args.tokens:
        targets.append(args.tokens)
    elif args.all or not args.skin:
        for name in FLAGSHIP_SKINS:
            path = skin_tokens(args.root, name)
            if path:
                targets.append(path)
    else:
        path = skin_tokens(args.root, args.skin)
        if not path:
            print("skin: no tokens.json for skin %r" % args.skin)
            return 2
        targets.append(path)

    if not targets:
        print("skin: nothing to do — no tokens.json found")
        return 2

    rc = 0
    for path in targets:
        code, _n = run_one(path, args.check)
        rc = max(rc, code)
    return rc


if __name__ == "__main__":
    sys.exit(main())
