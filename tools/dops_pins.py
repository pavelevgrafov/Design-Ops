#!/usr/bin/env python3
"""dops_pins.py — the sorting station for owner edits (П-2).

Design: Kimi, `Most/tasks/2026-08-04-kimi-revision-conveyor.md` §3, move П-2.

The problem it solves: every edit used to cost the same. "Make the button
darker" and "add a booking flow" both went through the full cycle — read the
context, write the contract, route through S0, apply, re-verify, report. The
price of a change had nothing to do with its size, and the big model met all
of them.

So each pin is classified BEFORE the model sees it:

  A  token / copy   colour, a step on the scale, spacing, text, visibility
                    → a script edits a token or a string; seconds, no model
  B  block          swap a section, reorder, another variant of a block
                    → block swap against its passport; seconds to minutes
  C  structure      a new page, flow, role; the sitemap changes
                    → narrow K1 + a targeted gate; minutes
  D  taste          "not quite right", "make it fancier"
                    → 2-3 options or one clarifying question; waits for the owner

The classifier is a dictionary, not a model: it must be cheaper than the work
it routes. Where the words are genuinely ambiguous it says so and routes to D
— a wrong cheap lane costs more than an honest "I need one word from you".

Usage:
  dops pins classify [--root DIR] [--in annotations.json] [--json]
  dops pins list [--root DIR] [--lane A|B|C|D]
  dops pins stats [--root DIR]
  dops pins --self-test

Exit: 0 ok, 1 nothing classified / ambiguous pins need the owner, 2 usage.
"""
import argparse
import json
import os
import re
import sys

DEFAULT_IN = os.path.join("artifacts", "annotations.json")
OUT = os.path.join("artifacts", "pins.json")

LANES = {
    "A": "token/copy — a script applies it, seconds, no model",
    "B": "block — swap or reorder a section against its passport",
    "C": "structure — narrow K1 and a targeted gate",
    "D": "taste or ambiguous — options or one question, waits for the owner",
}

# Word lists, deliberately boring. Each entry is (pattern, lane, plan template).
# Order matters: the first match wins, so the specific rules come first.
RULES = [
    # --- C: structure. Checked FIRST: "add a page about prices" mentions a
    # price, but it is a new page, and mis-routing it to A would silently
    # produce a token edit for a request that needed a gate.
    (r"\b(нов(ая|ую|ый)|добав(ь|ить)|заведи|создай)\b.*\b(страниц\w*|раздел\w*|экран\w*|флоу|поток|роль|роли)\b",
     "C", "new screen or flow: narrow K1 on the delta, then a targeted Gate 1"),
    (r"\b(new|add)\b.*\b(page|screen|flow|role|section of the site)\b",
     "C", "new screen or flow: narrow K1 on the delta, then a targeted Gate 1"),
    (r"\b(удали|убер(и|ать))\b.*\b(страниц\w*|экран\w*|раздел\w*)\b",
     "C", "screen removed: contract delta, sitemap re-render, targeted Gate 1"),
    (r"\b(sitemap|карт[аеу] сайта|структур\w*|навигаци\w*)\b",
     "C", "structure change: contract delta first, then a targeted gate"),

    # --- B: block-level. Moving, swapping, reordering whole sections.
    (r"\b(помен(яй|ять)|поменя\w*|перенеси|подним(и|ать)|опусти|вверх|вниз|выше|ниже|порядок|местами)\b.*\b(секц\w*|блок\w*|раздел\w*)\b",
     "B", "reorder sections: block swap, then seam checks"),
    (r"\b(секци\w*|блок\w*)\b.*\b(замен(и|ить)|другой|другую|вариант)\b",
     "B", "replace the block with another variant carrying a passport"),
    (r"\b(swap|reorder|move)\b.*\b(section|block)\b",
     "B", "reorder or swap a section, then seam checks"),

    # --- A: token and copy. The bulk of real revisions.
    (r"\b(цвет|покрас|темнее|светлее|ярче|приглуш\w*|контраст\w*|фон)\b",
     "A", "semantic colour token, then compile-tokens.py and D3/D.25"),
    (r"\b(colou?r|darker|lighter|background|contrast)\b",
     "A", "semantic colour token, then compile-tokens.py and D3/D.25"),
    (r"\b(крупнее|мельче|больше шрифт\w*|меньше шрифт\w*|размер шрифт\w*|кегл\w*|шрифт)\b",
     "A", "type scale step, then compile-tokens.py and D4-D8"),
    (r"\b(font|type size|bigger text|smaller text)\b",
     "A", "type scale step, then compile-tokens.py and D4-D8"),
    (r"\b(отступ\w*|поля|padding|margin|воздух\w*|плотн\w*|разреж\w*)\b",
     "A", "spacing token on the 8pt ladder, then D9"),
    (r"\b(spacing|padding|margin|tighter|looser)\b",
     "A", "spacing token on the 8pt ladder, then D9"),
    (r"\b(текст|заголов\w*|подпис\w*|формулиров\w*|опечатк\w*|слово|фраз\w*|копи)\b",
     "A", "copy slot edit, then D10 and the copy-linter"),
    (r"\b(copy|wording|typo|headline|label|text)\b",
     "A", "copy slot edit, then D10 and the copy-linter"),
    (r"\b(скр(ой|ыть)|спрячь|показ(ать|ывать)|видим\w*)\b",
     "A", "visibility toggle on the element, then D12 spot-check"),
    (r"\b(hide|show|visibility)\b",
     "A", "visibility toggle on the element, then D12 spot-check"),

    # --- D: taste, explicitly. Named so it lands here rather than nowhere.
    (r"\b(не то|не нрав\w*|как-то|наряднее|скучн\w*|дорог\w* смотр\w*|солиднее|живее|красив\w*)\b",
     "D", "taste: prepare 2-3 options on a two-screen slice, or ask one question"),
    (r"\b(not quite|feels off|fancier|nicer|more premium)\b",
     "D", "taste: prepare 2-3 options on a two-screen slice, or ask one question"),
]

# The owner's own `kind` is a prior, not a verdict: it decides only when the
# words carry no signal at all.
KIND_FALLBACK = {"copy": "A", "visual": "D", "structure": "C", "question": "D"}


def classify_one(pin):
    text = " ".join(str(pin.get("text") or "").lower().split())
    if not text:
        return "D", "empty comment — ask what the pin means", "no text"
    for pattern, lane, plan in RULES:
        if re.search(pattern, text):
            return lane, plan, "matched: %s" % pattern[:48]
    kind = str(pin.get("kind") or "").lower()
    lane = KIND_FALLBACK.get(kind, "D")
    if lane == "D":
        return "D", ("no rule matched and the wording is open — one clarifying "
                     "question is cheaper than guessing"), "fallback on kind=%s" % (kind or "none")
    return lane, LANES[lane], "fallback on kind=%s" % kind


def load_pins(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("annotations.json must be a list of pins")
    return data


def dedupe(pins):
    """Two pins on the same element saying the same thing are one edit. The
    duplicate is kept and marked, never deleted: the owner wrote it twice for
    a reason, and silently dropping their words is its own defect."""
    seen, out = {}, []
    for p in pins:
        key = (p.get("selector") or p.get("target_selector") or "",
               " ".join(str(p.get("text") or "").lower().split()))
        if key in seen and key[1]:
            p = dict(p, duplicate_of=seen[key])
        else:
            seen[key] = p.get("id") or ""
        out.append(p)
    return out


def classify(root, in_path, as_json):
    path = in_path if os.path.isabs(in_path) else os.path.join(root, in_path)
    if not os.path.isfile(path):
        print("pins: no annotations at %s — export them from the artifact "
              "first (the Comment button)" % path)
        return 1
    try:
        pins = dedupe(load_pins(path))
    except (ValueError, json.JSONDecodeError) as exc:
        print("pins: cannot read %s: %s" % (path, exc))
        return 2

    rows = []
    for p in pins:
        lane, plan, why = classify_one(p)
        rows.append({
            "id": p.get("id") or "",
            "selector": p.get("selector") or p.get("target_selector") or "",
            "viewport": p.get("viewport"),
            "kind": p.get("kind") or "",
            "text": p.get("text") or "",
            "lane": lane,
            "lane_meaning": LANES[lane],
            "plan": plan,
            "why": why,
            "status": "triaged",
            "duplicate_of": p.get("duplicate_of"),
        })

    out_path = os.path.join(root, OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    report = {"schema": "dops-pins/1", "source": path, "count": len(rows),
              "lanes": tally(rows), "pins": rows}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("pins: %d classified → %s" % (len(rows), out_path))
    show(rows)
    cheap = sum(1 for r in rows if r["lane"] in ("A", "B"))
    if rows:
        print("  %d of %d (%.0f%%) never reach the big model"
              % (cheap, len(rows), 100.0 * cheap / len(rows)))
    waiting = [r for r in rows if r["lane"] == "D"]
    if waiting:
        print("  %d pin(s) need one word from the owner before anything is done"
              % len(waiting))
    return 0


def tally(rows):
    out = {}
    for r in rows:
        out[r["lane"]] = out.get(r["lane"], 0) + 1
    return out


def show(rows, lane=None):
    for r in rows:
        if lane and r["lane"] != lane:
            continue
        dup = "  (duplicate of %s)" % r["duplicate_of"] if r.get("duplicate_of") else ""
        print("  %-7s %s  %-28s %s%s"
              % (r["lane"], r["id"] or "—", (r["selector"] or "")[:28],
                 r["text"][:52], dup))
        print("          → %s" % r["plan"])


def read_report(root):
    path = os.path.join(root, OUT)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def self_test():
    import tempfile
    problems = []
    cases = [
        ({"text": "заголовок дня тонет, сделать крупнее", "kind": "visual"}, "A"),
        ({"text": "make the CTA darker", "kind": "visual"}, "A"),
        ({"text": "опечатка в подписи к билету", "kind": "copy"}, "A"),
        ({"text": "поменяй местами секции программы и билетов", "kind": "structure"}, "B"),
        ({"text": "добавь новую страницу для партнёров", "kind": "structure"}, "C"),
        ({"text": "add a new page for partners", "kind": "structure"}, "C"),
        ({"text": "как-то не то, сделай наряднее", "kind": "visual"}, "D"),
        ({"text": "", "kind": "visual"}, "D"),
    ]
    for pin, expected in cases:
        lane, _plan, _why = classify_one(pin)
        if lane != expected:
            problems.append("%r → lane %s, expected %s" % (pin["text"][:40], lane, expected))

    # a structural request that mentions a token word must NOT go to lane A
    lane, _, _ = classify_one({"text": "добавь новый экран с ценами", "kind": "visual"})
    if lane != "C":
        problems.append("a new screen mentioning prices was routed to %s, not C" % lane)

    # an unlabelled visual comment is ambiguous — D is the honest answer
    lane, _, _ = classify_one({"text": "hmm", "kind": "visual"})
    if lane != "D":
        problems.append("an opaque comment was routed to %s instead of asking" % lane)

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))
        src = os.path.join(tmp, "artifacts", "annotations.json")
        pins = [dict(p, id="a-000%d" % i, selector="#s%d" % i)
                for i, (p, _e) in enumerate(cases, start=1)]
        pins.append(dict(pins[0], id="a-0009"))          # exact duplicate
        with open(src, "w", encoding="utf-8") as f:
            json.dump(pins, f, ensure_ascii=False)
        if classify(tmp, "artifacts/annotations.json", False) != 0:
            problems.append("classify failed on a well-formed file")
        rep = read_report(tmp)
        if not rep or rep["count"] != len(pins):
            problems.append("the report lost pins")
        dups = [p for p in (rep or {}).get("pins", []) if p.get("duplicate_of")]
        if len(dups) != 1:
            problems.append("the duplicate pin was not marked (found %d)" % len(dups))
        if any(p["status"] != "triaged" for p in rep["pins"]):
            problems.append("a classified pin did not become `triaged`")

    if problems:
        for p in problems:
            print("self-test FAIL: dops-pins: %s" % p)
        return 1
    print("OK: dops-pins self-test (4 lanes, structure beats token words, "
          "ambiguity routed to the owner, duplicates marked not dropped)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", choices=["classify", "list", "stats"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--in", dest="in_path", default=DEFAULT_IN)
    ap.add_argument("--lane", default=None, choices=list(LANES))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)

    if args.command == "classify":
        return classify(root, args.in_path, args.json)

    rep = read_report(root)
    if not rep:
        print("pins: nothing classified yet — run `dops pins classify`")
        return 1
    if args.command == "stats" or not args.command:
        print("pins: %d total" % rep["count"])
        for lane in sorted(LANES):
            n = rep["lanes"].get(lane, 0)
            print("  %s  %-3d %s" % (lane, n, LANES[lane]))
        return 0
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    show(rep["pins"], args.lane)
    return 0


if __name__ == "__main__":
    sys.exit(main())
