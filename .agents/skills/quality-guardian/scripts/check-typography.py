#!/usr/bin/env python3
"""check-typography.py — D4–D8: typography floor (granular per-check output).

  D4  body/base text >= 16px
  D5  measure 45–75ch (run on BOTH language variants when localization_risk —
      pass each variant's stylesheet/dir as a separate argument)
  D6  body line-height 1.4–1.7
  D7  modular scale ratio 1.2–1.333 (from emitted --font-scale-stepN)
  D8  <=2 proportional families (+1 mono); generic fallback last in every
      stack; font-display: swap on every @font-face; ban-list first position

Usage: python3 check-typography.py [css_root_or_file ...]
Exit 0 = all pass, 1 = any violation. Stdlib only.
"""
import glob, os, re, sys

BANNED_FIRST = {"inter", "roboto", "arial", "space grotesk", "space-grotesk", "spacegrotesk"}
# v5.2 [TZ-2.4]: max-width: Nch counts as D5 evidence ONLY on text selectors
# (same set as D4/D6). Headings are display type — their ch is ignored, not
# flagged. Primary evidence remains the --measure-* token.
TEXT_SEL = r"\b(body|p|prose|article|li)\b"
HEADING_SEL = r"\bh[1-6]\b"
GENERIC = {"system-ui", "sans-serif", "serif", "monospace", "ui-sans-serif",
           "ui-monospace", "ui-serif", "ui-rounded", "cursive", "fantasy", "emoji",
           "math", "fangsong"}

def collect_css(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += glob.glob(os.path.join(p, "**", "*.css"), recursive=True)
        elif os.path.isfile(p):
            files.append(p)
    return [f for f in files if "node_modules" not in f]

def main():
    paths = sys.argv[1:] or ["."]
    # buckets: check_id -> list of problems
    res = {"D4": [], "D5": [], "D6": [], "D7": [], "D8": []}
    notes = []

    body_sizes, body_lhs, measures, families = [], [], [], []
    scale_steps = []

    for f in collect_css(paths):
        with open(f, encoding="utf-8", errors="ignore") as fh:
            css = fh.read()

        for m in re.finditer(r"@font-face\s*\{([^}]*)\}", css, re.S):
            if not re.search(r"font-display\s*:\s*swap", m.group(1)):
                res["D8"].append(f"{f}: @font-face without font-display: swap")

        for m in re.finditer(r"--font-scale-step(-?\d+)\s*:\s*([0-9.]+)rem", css):
            scale_steps.append((int(m.group(1)), float(m.group(2))))

        # measure tokens (--measure-*: Nch) count as D5 evidence
        for m in re.finditer(r"--measure-[a-z-]*\s*:\s*([0-9.]+)ch", css):
            measures.append((f, float(m.group(1))))

        for sel, block in re.findall(r"([^{}]+)\{([^}]*)\}", css):
            sel_l = sel.lower()
            fs = re.search(r"font-size\s*:\s*([0-9.]+)(px|rem)", block)
            lh = re.search(r"line-height\s*:\s*([0-9.]+)", block)
            mw = re.search(r"max-width\s*:\s*([0-9.]+)ch", block)
            ff = re.search(r"font-family\s*:\s*([^;}]+)", block)
            if fs and re.search(r"\b(body|p|:root|html)\b", sel_l):
                px = float(fs.group(1)) * (16 if fs.group(2) == "rem" else 1)
                body_sizes.append((f, px))
            if lh and re.search(r"\b(body|p)\b", sel_l):
                body_lhs.append((f, float(lh.group(1))))
            if mw:
                if re.search(TEXT_SEL, sel_l):
                    measures.append((f, float(mw.group(1))))
                elif re.search(HEADING_SEL, sel_l):
                    notes.append(
                        f"D5: heading measure {mw.group(1)}ch in {f} ignored "
                        "(display type is not body measure)")
                # other selectors (e.g. .container): not D5 evidence either
            if ff:
                stack = [x.strip().strip("\"'") for x in ff.group(1).split(",")]
                families.append((f, stack))

    # D4
    for f, px in body_sizes:
        if px < 16:
            res["D4"].append(f"{f}: body font-size {px}px < 16px")
    if not body_sizes:
        notes.append("D4: no explicit body font-size found (browser default 16px assumed — verify)")

    # D5
    for f, ch in measures:
        if not (45 <= ch <= 75):
            res["D5"].append(f"{f}: measure {ch}ch outside 45–75ch")
    if not measures:
        notes.append("D5: no ch-based max-width found (verify measure manually)")

    # D6
    for f, v in body_lhs:
        if not (1.4 <= v <= 1.7):
            res["D6"].append(f"{f}: body line-height {v} outside 1.4–1.7")

    # D7
    steps = sorted(set(scale_steps))
    positive = [(n, v) for n, v in steps if n >= 0]
    if len(positive) >= 3:
        ratios = [round(positive[i+1][1] / positive[i][1], 3)
                  for i in range(len(positive)-1) if positive[i][1] > 0]
        bad = [r for r in ratios if not (1.19 <= r <= 1.34)]
        if bad:
            res["D7"].append(f"type scale ratios {bad} outside 1.2–1.333")

    # D8
    prop_first = set()
    for f, stack in families:
        if not stack:
            continue
        first = stack[0].lower()
        last = stack[-1].lower()
        if last not in GENERIC and not last.startswith("var("):
            res["D8"].append(f"{f}: font stack '{stack[0]}, …' lacks a generic fallback last")
        if first.replace(" ", "") in {b.replace(" ", "") for b in BANNED_FIRST}:
            res["D8"].append(f"{f}: banned font '{stack[0]}' in first position")
        mono = "mono" in first
        if first not in GENERIC and not mono and not first.startswith("var("):
            prop_first.add(stack[0])
    if len(prop_first) > 2:
        res["D8"].append(f"{len(prop_first)} proportional families in use {sorted(prop_first)} — max 2")

    # granular output [D.3]
    problems_total = 0
    for cid in ("D4", "D5", "D6", "D7", "D8"):
        if res[cid]:
            problems_total += len(res[cid])
            for p in res[cid]:
                print(f"FAIL[{cid}]: {p}")
        else:
            print(f"pass[{cid}]")
    for n in notes:
        print(f"note: {n}")
    if problems_total:
        print(f"\n{problems_total} typography problem(s)")
        return 1
    print("OK: typography floor met (D4–D8)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
