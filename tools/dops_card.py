#!/usr/bin/env python3
"""dops_card.py — generate RULES.card.md, the resident rule set (P2).

A rule belongs in the prompt only if it changes what the model WRITES. A
rule a checker enforces afterwards costs context on every turn and buys
nothing — `dops verify` is its enforcement. This script separates the two
mechanically and emits one small card:

  1. numbers needed while writing  (from .agents/knowledge-sync/constraints/)
  2. generative invariants         (from AGENTS.md x tools/rules-taxonomy.json)
  3. ban-list, one line per ban    (from visual-director/references/ban-list.md)
  4. what the machine enforces     (from tools/floor-registry.json)

Generated, never hand-edited: every number traces to one source file, so the
card cannot drift away from the constraints the checkers read.

Usage:
  python3 tools/dops_card.py [--out .agents/RULES.card.md] [--stdout]
                             [--budget-tokens 2000] [--audit] [--self-test]

Exit: 0 ok, 1 over budget / audit failure, 2 io.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
CONSTRAINTS = os.path.join(PKG, ".agents", "knowledge-sync", "constraints")
PIN = os.path.join(PKG, ".agents", "knowledge-sync", "PIN.json")
AGENTS = os.path.join(PKG, "AGENTS.md")
BANLIST = os.path.join(PKG, ".agents", "skills", "visual-director",
                       "references", "ban-list.md")
TAXONOMY = os.path.join(HERE, "rules-taxonomy.json")
REGISTRY = os.path.join(HERE, "floor-registry.json")
DEFAULT_OUT = os.path.join(PKG, ".agents", "RULES.card.md")

# What a writer actually needs at generation time, pulled from the frozen
# constraints by dotted path. Anything not listed is a number the checker
# owns — it does not belong on the card.
WANTED = [
    ("Contrast", "a11y", [
        ("text (normal / large)", "contrast.text-normal-aa.value",
         "contrast.text-large-aa.value", "%s:1 / %s:1"),
        ("non-text + focus ring", "contrast.non-text-aa.value", None, "%s:1"),
    ]),
    ("Targets", "a11y", [
        ("tap target min / comfort", "target-size.min-css-px.value",
         "target-size.comfort-apple-pt.value", "%s px / %s px"),
        ("focus outline", "focus.outline-min-px", None, ">= %s px, never removed"),
        ("text scaling", "text-scaling.max-percent.value", None,
         "layout holds at %s%%"),
    ]),
    ("Type", "typography", [
        ("base / absolute min", "sizes-px.body-min.value",
         "sizes-px.absolute-min.value", "%s px / %s px"),
        ("scale ratio", "scale.recommended", None, "%s"),
        ("families max (+1 mono)", "fonts.max-families.value", None, "%s"),
        ("line-height body / headings", "line-height.body",
         "line-height.headings", "%s / %s"),
        ("measure", "measure-ch.optimal", None, "%s ch"),
        ("unit", "units", None, "%s"),
    ]),
    ("Grid", "spacing", [
        ("base step (micro)", "grid.base-px.value", "grid.micro-step-px.value",
         "%s px (%s px only where 8 is too coarse)"),
        ("rule", "rule", None, "%s"),
        ("sections / blocks / elements", "ladder-px.between-sections",
         "ladder-px.between-elements", "%s / %s px"),
    ]),
    ("Motion", "motion", [
        ("micro / standard / page", "duration-ms.micro",
         "duration-ms.standard", "%s / %s ms"),
        ("response starts before", "doherty-threshold-ms.value", None, "%s ms"),
        ("animate only", "performance.animated-properties", None, "%s"),
        ("never animate", "performance.forbidden-properties", None, "%s"),
        ("easing", "easing.entrance", "easing.linear", "in %s / out ease-in; linear %s"),
    ]),
    ("Colour", "color", [
        ("proportion", "proportion-60-30-10.dominant",
         "proportion-60-30-10.accent", "%s / 30 / %s"),
        ("text tiers", "text.steps-percent", None, "%s %% lightness"),
        ("pure #000 text", "text.not-pure-black", None,
         "forbidden — softened near-black"),
    ]),
    ("Dark theme", "dark-theme", [
        ("base surface", "background.base", "background.pure-black", "%s; #000 %s"),
        ("elevation", "elevation.method", None, "%s"),
        ("text opacity", "text-opacity-percent.primary",
         "text-opacity-percent.secondary", "%s / %s %%"),
    ]),
    ("Performance", "performance", [
        ("LCP / INP / CLS", "core-web-vitals.lcp-s.good.value",
         "core-web-vitals.inp-ms.good.value", "%s s / %s ms / 0.1"),
        ("budgets", "budget.js-max-kb.value", "budget.page-max-mb.value",
         "JS <= %s KB, page <= %s MB"),
    ]),
    ("Responsive", "responsive", [
        ("breakpoints", "breakpoints-px", None, "%s px"),
        ("images", "images.explicit-dimensions", None,
         "width/height declared (CLS)"),
    ]),
]


# ------------------------------------------------------------------ tiny yaml
SCALAR_RE = re.compile(r"^(\s*)([A-Za-z0-9_.\-]+):\s*(.*)$")


def strip_comment(value):
    """`base: "#121212"  # Material` — the hex is data, the tail is a comment."""
    out, quote = [], None
    for i, ch in enumerate(value):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def parse_yaml(text):
    """Enough YAML for these constraint files: nested maps, inline maps,
    inline lists, scalars. Stdlib only — PyYAML is optional in this repo."""
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.lstrip().startswith("- "):
            indent = len(raw) - len(raw.lstrip())
            while stack and stack[-1][0] >= indent:
                stack.pop()
            continue                      # list-of-notes: not used by the card
        m = SCALAR_RE.match(raw)
        if not m:
            continue
        indent, key = len(m.group(1)), m.group(2)
        value = strip_comment(m.group(3))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            node = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = parse_value(value)
    return root


def parse_value(v):
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        out = {}
        for part in split_top(v[1:-1]):
            if ":" in part:
                k, val = part.split(":", 1)
                out[k.strip()] = parse_value(val)
        return out
    if v.startswith("[") and v.endswith("]"):
        return [parse_value(p) for p in split_top(v[1:-1]) if p.strip()]
    if v and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def split_top(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def dig(data, dotted):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def show(value):
    """A two-number list is a range (16-24); anything else is a plain list."""
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            return "%s-%s" % (value[0], value[1])
        return " / ".join(show(v) for v in value)
    return str(value)


# ------------------------------------------------------------------- sections
def load_constraints():
    out = {}
    if not os.path.isdir(CONSTRAINTS):
        return out
    for fn in sorted(os.listdir(CONSTRAINTS)):
        if fn.endswith(".yaml"):
            with open(os.path.join(CONSTRAINTS, fn), encoding="utf-8") as f:
                out[fn[:-5]] = parse_yaml(f.read())
    return out


def level_of(data, *paths):
    """RFC-2119 level as the constraints declare it: `{value: 24, level: MUST}`.
    A number without a level is context, not a requirement — and the reader
    must be able to tell which is which."""
    levels = set()
    for path in paths:
        if not path or not path.endswith(".value"):
            continue
        lv = dig(data, path[: -len(".value")] + ".level")
        if lv:
            levels.add(str(lv))
    if "MUST" in levels:
        return "MUST"
    if "SHOULD" in levels:
        return "SHOULD"
    return ""


def numbers_section(constraints, missing):
    lines = ["| Topic | Rule | Level |", "| :-- | :-- | :-- |"]
    for group, source, rows in WANTED:
        data = constraints.get(source)
        if data is None:
            missing.append("constraints/%s.yaml absent" % source)
            continue
        for label, path_a, path_b, fmt in rows:
            a = dig(data, path_a)
            b = dig(data, path_b) if path_b else None
            if a is None or (path_b and b is None):
                missing.append("%s: %s" % (source, path_b if a is not None else path_a))
                continue
            args = (show(a),) if path_b is None else (show(a), show(b))
            rule = fmt % args if "%s" in fmt else fmt
            # some constraints ARE the level ("explicit-dimensions: MUST") —
            # that belongs in the Level column, not inside the rule text
            level = str(a) if str(a) in ("MUST", "SHOULD") \
                else level_of(data, path_a, path_b)
            lines.append("| %s — %s | %s | %s |" % (group, label, rule, level))
    return "\n".join(lines)


def invariants_section(taxonomy, agents_text, missing):
    declared = set(re.findall(r"\*\*\[(A\.\d+)\]\*\*", agents_text))
    known = set(taxonomy["invariants"])
    for aid in sorted(declared - known, key=sort_key):
        missing.append("%s declared in AGENTS.md but unclassified" % aid)
    for aid in sorted(known - declared, key=sort_key):
        missing.append("%s classified but no longer in AGENTS.md" % aid)

    lines = []
    for aid in sorted(known, key=sort_key):
        rule = taxonomy["invariants"][aid]
        if rule["class"] not in ("generative", "generative_and_verified"):
            continue
        mark = "" if rule["class"] == "generative" \
            else "  _(also checked: %s)_" % ", ".join(rule["enforced_by"])
        lines.append("- **[%s]** %s%s" % (aid, rule["line"], mark))
    return "\n".join(lines)


def sort_key(aid):
    return int(aid.split(".")[1])


def banlist_section(missing):
    if not os.path.isfile(BANLIST):
        missing.append("ban-list.md absent")
        return ""
    with open(BANLIST, encoding="utf-8") as f:
        text = f.read()
    # Only the numbered ban sections; the tiering spec at the end lists
    # severities, not bans, and must not leak in as one.
    body = re.split(r"^## v7\.0", text, maxsplit=1, flags=re.M)[0]
    bans = []
    for m in re.finditer(r"^- \*\*(.+?)\*\*", body, re.M):
        ban = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(":")
        bans.append(ban)
    if not bans:
        missing.append("ban-list.md: no bans parsed")
    return "\n".join("- %s" % b for b in bans)


def enforced_section(registry, taxonomy):
    ids = []
    for check in registry["checks"]:
        ids.extend(check.get("covers") or [check["id"]])
    verified = [aid for aid, r in taxonomy["invariants"].items()
                if r["class"] == "verified"]
    return ("`dops verify` runs %d checks covering %s. Invariants %s are fully "
            "machine-enforced — they are deliberately absent above."
            % (len(registry["checks"]), ", ".join(sorted(set(ids), key=did_key)),
               ", ".join(sorted(verified, key=sort_key))))


def did_key(did):
    m = re.match(r"D\.?(\d+)", did)
    return int(m.group(1)) if m else 999


def build(missing):
    constraints = load_constraints()
    with open(AGENTS, encoding="utf-8") as f:
        agents_text = f.read()
    with open(TAXONOMY, encoding="utf-8") as f:
        taxonomy = json.load(f)
    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)
    pin = {}
    if os.path.isfile(PIN):
        with open(PIN, encoding="utf-8") as f:
            pin = json.load(f)
    provenance = (pin.get("sources", {}).get("ux_wiki", {}) or {})

    return """# RULES.card — the resident rule set

GENERATED by `tools/dops_card.py` — do not edit by hand; edit the sources
(`.agents/knowledge-sync/constraints/*.yaml`, `AGENTS.md`,
`tools/rules-taxonomy.json`, `ban-list.md`) and regenerate.

This card is what stays in context for a whole run. Everything else loads on
demand. Rules a checker enforces are deliberately NOT here: `dops verify`
catches them in one command, so keeping them resident would cost context on
every turn and buy nothing.

Constraints snapshot: ux-wiki `%s` (%s), sha256 `%s`. Frozen by design —
the runtime never reads a live wiki.

## 1. Numbers to write correctly the first time

Level is the constraints' own RFC-2119 marking: MUST = a violation is a
defect; SHOULD = a deviation needs a recorded reason; blank = context, not a
requirement.

%s

## 2. Generative rules

%s

## 3. Ban-list (defaults that read as "AI made this")

Each needs a written, direction-level justification to be used at all.

%s

## 4. Enforced by the machine — do not re-read

%s

Fix routing: read `failures[]` from `artifacts/audit/floor.json`; each entry
carries the failing output and a fix hint. The prose registry
(`quality-guardian/references/deterministic-floor.md`) is for debugging a
single check, not for a run.
""" % (provenance.get("commit", "unpinned")[:12],
       provenance.get("vendored_at", "n/a"),
       provenance.get("sha256", "n/a")[:16],
       numbers_section(constraints, missing),
       invariants_section(taxonomy, agents_text, missing),
       banlist_section(missing),
       enforced_section(registry, taxonomy))


def self_test():
    problems = []
    missing = []
    try:
        card = build(missing)
    except (OSError, ValueError) as exc:
        print("self-test FAIL: dops-card: cannot build: %s" % exc)
        return 1
    if missing:
        problems += ["source drift: %s" % m for m in missing]
    approx = len(card) // 4
    if approx > 2000:
        problems.append("card is ~%d tokens, budget 2000" % approx)
    for probe in ("4.5:1", "24 px", "16 px", "rem", "transform"):
        if probe not in card:
            problems.append("a generation-time number is missing: %s" % probe)
    # a verified-only rule must NOT be resident
    if "corporate slop" in card or "[A.22]" in card:
        problems.append("a machine-verified rule leaked onto the card")
    # source prose is Russian in places; the card is authored English only —
    # a Cyrillic character means raw prose leaked in instead of a number
    stray = re.search(r"[Ѐ-ӿ]", card)
    if stray:
        line = card[:stray.start()].count("\n") + 1
        problems.append("untranslated source prose leaked onto the card "
                        "(line %d)" % line)
    # tiny YAML parser must read the real files
    c = load_constraints()
    if dig(c.get("a11y", {}), "contrast.text-normal-aa.value") != 4.5:
        problems.append("constraint parser did not read a11y contrast")
    if dig(c.get("spacing", {}), "grid.base-px.value") != 8:
        problems.append("constraint parser did not read the spacing grid")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-card: %s" % p)
        return 1
    print("OK: dops-card self-test (~%d tokens, sources aligned, "
          "verified rules stay off the card)" % approx)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--budget-tokens", type=int, default=2000)
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    missing = []
    card = build(missing)
    approx = len(card) // 4

    if args.audit:
        for m in missing:
            print("audit FAIL: %s" % m)
        print("card: ~%d tokens (budget %d), %d source problem(s)"
              % (approx, args.budget_tokens, len(missing)))
        return 1 if missing or approx > args.budget_tokens else 0

    if args.stdout:
        print(card)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(card)
        print("card written → %s (~%d tokens, budget %d)"
              % (args.out, approx, args.budget_tokens))
    for m in missing:
        print("  source problem: %s" % m)
    return 1 if approx > args.budget_tokens or missing else 0


if __name__ == "__main__":
    sys.exit(main())
