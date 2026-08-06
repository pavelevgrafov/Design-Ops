#!/usr/bin/env python3
"""dops_pins_check.py — the checker at the door (П-3).

Design: Kimi, `Most/tasks/2026-08-06-kimi-p3-checker-spec-and-decisions.md` §1.
Position in the conveyor:

    pin new → classify (П-2) → CHECK (this file) → execute (A/B)
                                               | wait (C/D)
                                               | rejected, with alternatives

The principle is negotiation at the cheapest possible moment: before a single
second of execution has been spent. A pin that cannot be applied, breaks a
norm, or contradicts a decision already made is caught at the door — not
discovered by the floor after the work is done (that would be K3, not П-3).

Four questions, in a fixed order, cheap before expensive:

  1. feasible    does the pin's selector still resolve in the current build?
  2. norms       lane A: is the proposed value inside the declared ranges
                 (type scale, 8pt ladder, contrast pairs at 4.5:1)?
                 lane A/B: does the pin ask for a tier-1 banned pattern?
  3. conflict    does it contradict scope.exclusions or the decision log?
  4. duplicate   has the owner already said this?

Ranges are never hardcoded here. The type scale, the spacing ladder and the
contrast pairs are read from the skin's `tokens.json` — `$meta.contrastPairs`
is the declared geometry (move 8), and a second copy of it in this file would
be exactly the silent drift [A.10] forbids. The WCAG maths is imported from
`check-contrast.py` rather than re-typed, for the same reason.

Cost discipline: lanes A and B are decided by script alone, zero model calls —
a checker that is not cheaper than the work it routes has no reason to exist.
A small model may be consulted for two things only: question 1 on a pin whose
wording has no resolvable target, and question 3 on a semantic conflict. It is
plugged in through $DOPS_SMALL_MODEL (a command reading one JSON object on
stdin, printing one JSON verdict on stdout). With no such command in the
environment the script lane still runs and the judgement pins go to the owner
as `clarify` marked `checker_unavailable` — honest degradation [A.6], not a
fabricated pass.

Usage:
  dops pins check   [--root DIR] [--pin ID] [--build DIR] [--json]
  dops pins answer  --pin ID --text "..."      the owner replies inside the pin
  dops pins metrics [--root DIR] [--json]

Exit: 0 all pins pass, 1 something needs the owner (clarify/rejected/duplicate),
      2 usage / nothing classified.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
PINS = os.path.join("artifacts", "pins.json")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")
DECISION_LOG = os.path.join("artifacts", "decision-log.md")

VERDICTS = ("pass", "clarify", "rejected", "duplicate")
NORMAL_TEXT_MIN = 4.5      # WCAG 2.x normal text; large text/UI is 3:1

# Words that point at something without naming it. A pin made of these alone
# has no machine-resolvable target: the owner was looking at the screen.
DEICTIC = re.compile(
    r"\b(это|этот|эту|эта|тут|здесь|там|вот|оно|такое|this|that|here|there|it)\b",
    re.I)

# Tier-1 ban list (visual-director/references/ban-list.md §1, §2, §7). Only the
# blocking tier: a checker that argues about tier-2 warnings stops being cheap.
BANNED = [
    (re.compile(r"градиент\w*.*(индиго|фиолетов)|(индиго|фиолетов).*градиент\w*", re.I),
     "the indigo→purple gradient is the single most recognisable AI-look marker "
     "(ban-list tier 1, §2)",
     ["a flat surface in the direction's own accent",
      "a two-stop gradient inside one hue, under 20° apart",
      "keep the gradient but write the justification into the direction doc "
      "(ALLOW: protocol)"]),
    (re.compile(r"\b(indigo|purple)\b.*\bgradient\b|\bgradient\b.*\b(indigo|purple)\b", re.I),
     "the indigo→purple gradient is the single most recognisable AI-look marker "
     "(ban-list tier 1, §2)",
     ["a flat surface in the direction's own accent",
      "a two-stop gradient inside one hue, under 20° apart",
      "keep it and write the justification into the direction doc (ALLOW:)"]),
    (re.compile(r"\b(inter|roboto|arial|space\s?grotesk)\b", re.I),
     "that font in first position is a tier-1 default (ban-list §1)",
     ["the skin's display family for headings",
      "the skin's text family for body",
      "name a specific family the direction argues for, not a system default"]),
    (re.compile(r"(таймер|обратн\w* отсч|countdown|осталось всего|только \d+ (мест|билет)|only \d+ left)", re.I),
     "a countdown or scarcity counter that is not inventory-driven is a dark "
     "pattern — banned outright, no justification available (ban-list §7)",
     ["show the real deadline as a date, once",
      "show real remaining inventory if the number comes from a system",
      "state the benefit instead of the pressure"]),
    (re.compile(r"(карточк\w* (внутри|в) карточк|cards? (inside|within) cards?)", re.I),
     "cards inside cards is a tier-1 default: the frame stops meaning anything "
     "(ban-list tier 1)",
     ["group with spacing instead of a second frame",
      "keep the outer card, drop the inner border",
      "make the inner items a list"]),
]

# Words that flip a decision-log line from "mentions the subject" to "decided
# against the subject". Without one of these a co-occurrence is just a topic.
NEGATIVE = re.compile(
    r"(отказ\w*|решено не|не делаем|не будем|исключ\w*|отклон\w*|вместо|"
    r"rejected|declined|dropped|out of scope|instead of)", re.I)

STOPWORDS = set("""это этот эта эту так там где чтобы если надо нужно можно ещё
еще они она оно как что при для над под без про the and for with that this from
into over under make made please""".split())


# --------------------------------------------------------------------------
# shared maths: imported, never re-typed
# --------------------------------------------------------------------------
def _contrast_module():
    """D3's own WCAG implementation. Importing it keeps one source of truth for
    the ratio: if the floor's maths changes, the checker changes with it."""
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


def contrast_ratio(a, b):
    if not _CC:
        return None
    ra, rb = _CC.to_rgb(a), _CC.to_rgb(b)
    if ra is None or rb is None:
        return None
    return _CC.ratio(ra, rb)


# --------------------------------------------------------------------------
# the declared ranges: read from the skin, not from this file
# --------------------------------------------------------------------------
class Norms(object):
    """Everything question 2 is allowed to measure against, loaded from data."""

    def __init__(self, doc):
        self.doc = doc or {}
        self.pairs = [(p.get("foreground"), p.get("background"))
                      for p in self.doc.get("$meta", {}).get("contrastPairs", [])
                      if p.get("foreground") and p.get("background")]
        self.type_steps = self._dims(("primitive", "font", "scale"))
        self.space_steps = self._dims(("primitive", "space"))
        self.available = bool(self.doc)

    def _node(self, path):
        node = self.doc
        for k in path:
            if not isinstance(node, dict):
                return {}
            node = node.get(k, {})
        return node if isinstance(node, dict) else {}

    def _dims(self, path):
        out = []
        for key, val in self._node(path).items():
            if isinstance(val, dict) and val.get("$type") == "dimension":
                px = to_px(val.get("$value"))
                if px is not None:
                    out.append((key, px))
        return sorted(out, key=lambda kv: kv[1])

    def resolve_color(self, name):
        """semantic.color.<name>, following {primitive....} references."""
        node = self._node(("semantic", "color")).get(name)
        val = node.get("$value") if isinstance(node, dict) else None
        seen = 0
        while isinstance(val, str) and val.startswith("{") and seen < 8:
            ref = val.strip("{}").split(".")
            node = self._node(tuple(ref))
            val = node.get("$value") if isinstance(node, dict) else None
            seen += 1
        return val if isinstance(val, str) else None

    def gray_ramp(self):
        ramp = []
        for key, val in self._node(("primitive", "color", "gray")).items():
            if isinstance(val, dict) and isinstance(val.get("$value"), str):
                try:
                    ramp.append((int(key), val["$value"]))
                except ValueError:
                    pass
        return sorted(ramp)


def to_px(value):
    if value is None:
        return None
    s = str(value).strip()
    m = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(px|rem|em)?", s)
    if not m:
        return None
    n = float(m.group(1))
    return round(n * 16, 3) if m.group(2) in ("rem", "em") else round(n, 3)


def load_skin(root, skin_name):
    for cand in (os.path.join(root, "skins", skin_name, "tokens.json"),
                 os.path.join(PKG_ROOT, "skins", skin_name, "tokens.json"),
                 os.path.join(root, "tokens.json")):
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as f:
                    return json.load(f), cand
            except (OSError, json.JSONDecodeError):
                continue
    return None, ""


def read_contract(root):
    """The two fields question 3 needs, without importing a YAML parser: the
    checker must run on a machine where the floor's own dependencies are not
    installed yet, and a full parse buys nothing here."""
    path = os.path.join(root, CONTRACT)
    out = {"base_skin": "base-site", "exclusions": []}
    if not os.path.isfile(path):
        return out
    text = open(path, encoding="utf-8").read()
    m = re.search(r"base_skin:\s*([A-Za-z0-9_-]+)", text)
    if m:
        out["base_skin"] = m.group(1)
    m = re.search(r"^\s*exclusions:\s*\[(.*?)\]", text, re.M | re.S)
    if m:
        out["exclusions"] = [x.strip().strip("\"'") for x in m.group(1).split(",")
                             if x.strip()]
    else:
        m = re.search(r"^\s*exclusions:\s*\n((?:\s+-\s*.*\n)+)", text, re.M)
        if m:
            out["exclusions"] = [l.strip()[1:].strip().strip("\"'")
                                 for l in m.group(1).splitlines() if l.strip()]
    return out


def find_build(root, explicit):
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(root, explicit)
    for cand in ("site", "_injected", "build", "dist", "."):
        d = os.path.join(root, cand)
        if os.path.isdir(d) and any(f.endswith(".html") for f in os.listdir(d)):
            return d
    return ""


def build_markup(build_dir):
    if not build_dir or not os.path.isdir(build_dir):
        return None
    chunks = []
    for base, dirs, files in os.walk(build_dir):
        dirs[:] = [d for d in dirs if d not in
                   ("node_modules", ".git", "__pycache__", ".venv")]
        for fn in files:
            if fn.endswith((".html", ".htm")):
                try:
                    chunks.append(open(os.path.join(base, fn),
                                       encoding="utf-8", errors="replace").read())
                except OSError:
                    pass
    return "\n".join(chunks) if chunks else None


def selector_resolves(selector, markup):
    """A deliberate approximation of CSS matching: the most specific simple
    part of the selector is looked up in the markup as text. Real matching
    needs a browser, and the checker is not allowed to cost one. False
    positives here are harmless (the pin proceeds and the floor catches it);
    a false negative would be a wrong `clarify`, so the rule stays generous."""
    if not selector or markup is None:
        return None
    last = re.split(r"\s*>\s*|\s+", selector.strip())[-1]
    last = re.sub(r":nth-of-type\(\d+\)", "", last)
    m = re.match(r"#([A-Za-z0-9_-]+)", last)
    if m:
        return re.search(r'id\s*=\s*["\']%s["\']' % re.escape(m.group(1)),
                         markup) is not None
    classes = re.findall(r"\.([A-Za-z0-9_-]+)", last)
    if classes:
        return all(re.search(r'class\s*=\s*["\'][^"\']*\b%s\b' % re.escape(c), markup)
                   for c in classes)
    tag = re.match(r"([a-zA-Z][a-zA-Z0-9]*)", last)
    if tag:
        return re.search(r"<%s\b" % re.escape(tag.group(1)), markup) is not None
    return None


# --------------------------------------------------------------------------
# the small-model boundary
# --------------------------------------------------------------------------
def small_model_available():
    return bool(os.environ.get("DOPS_SMALL_MODEL"))


def ask_small_model(question, pin, context):
    """One JSON object in on stdin, one JSON verdict out on stdout. Anything
    else — a missing command, a crash, unparseable output — is not an error to
    hide but a capability that is absent: the caller degrades."""
    cmd = os.environ.get("DOPS_SMALL_MODEL")
    if not cmd:
        return None
    payload = json.dumps({"question": question, "pin": pin, "context": context},
                         ensure_ascii=False)
    try:
        proc = subprocess.run(cmd, shell=True, input=payload, capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(out, dict) or out.get("verdict") not in VERDICTS:
        return None
    return out


# --------------------------------------------------------------------------
# the four questions
# --------------------------------------------------------------------------
def q1_feasible(pin, markup):
    """Does the pin point at something that still exists?"""
    text = str(pin.get("text") or "")
    selector = pin.get("selector") or pin.get("target_selector") or ""
    resolved = selector_resolves(selector, markup)
    if resolved is False:
        return {
            "verdict": "clarify",
            "checker": "script",
            "question": ("this pin points at `%s`, and that element is not in "
                         "the current build any more — which element did you "
                         "mean?" % selector),
        }
    if not selector and DEICTIC.search(text) and not re.search(
            r"[a-zа-я]{5,}", re.sub(DEICTIC, " ", text.lower())):
        return {"verdict": "needs_model", "question_kind": "feasible"}
    return None


def q2_norms(pin, lane, norms):
    """Only lanes A and B are measured: C changes the structure and D has not
    named a value yet, so there is nothing to hold against a range."""
    if lane not in ("A", "B"):
        return None
    text = str(pin.get("text") or "")

    for pattern, reason, alternatives in BANNED:
        if pattern.search(text):
            return {"verdict": "rejected", "checker": "script",
                    "reason": reason, "alternatives": alternatives}

    if lane == "B":
        # Block passports are specified but not yet a produced artifact, so the
        # seam invariants cannot be measured. Saying so beats a silent pass.
        return {"verdict": "pass", "checker": "script",
                "unmeasured": ["block passport: no passports are produced yet — "
                               "seam invariants unchecked"]}

    hit = check_color(text, norms)
    if hit:
        return hit
    hit = check_dimension(text, norms)
    if hit:
        return hit
    return None


def check_color(text, norms):
    if not norms.available or not norms.pairs:
        return None
    m = re.search(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", text)
    wants_fg = re.search(r"\b(текст|шрифт|заголов\w*|подпис\w*|ink|text|label|"
                         r"headline)\b", text, re.I)
    wants_bg = re.search(r"\b(фон|подлож\w*|canvas|background)\b", text, re.I)

    if m:
        proposed = "#" + m.group(1)
        worst = None
        for fg, bg in norms.pairs:
            fgv, bgv = norms.resolve_color(fg), norms.resolve_color(bg)
            if not fgv or not bgv:
                continue
            if wants_bg and not wants_fg:
                r = contrast_ratio(fgv, proposed)
                against = "%s on the new background" % fg
            elif wants_fg or not wants_bg:
                r = contrast_ratio(proposed, bgv)
                against = "the new colour on %s" % bg
            else:
                continue
            if r is not None and (worst is None or r < worst[0]):
                worst = (r, against, fg, bg, fgv, bgv)
        if worst and worst[0] < NORMAL_TEXT_MIN:
            r, against, fg, bg, fgv, bgv = worst
            return {"verdict": "rejected", "checker": "script",
                    "reason": ("%s falls to %.2f:1 against a %.1f:1 floor (%s) — "
                               "the text stops being readable for part of your "
                               "visitors" % (proposed, r, NORMAL_TEXT_MIN, against)),
                    "alternatives": color_alternatives(proposed, fg, bg, fgv,
                                                       bgv, norms)}
        return None

    # No value named, only a direction. Probe whether one step that way still
    # clears the floor — that is the honest version of "make it lighter".
    direction = None
    if re.search(r"\b(светлее|бледнее|приглуш\w*|lighter|paler|softer)\b", text, re.I):
        direction = "lighter"
    elif re.search(r"\b(темнее|darker)\b", text, re.I):
        direction = "darker"
    if not direction or not (wants_fg or wants_bg):
        return None
    ramp = norms.gray_ramp()
    if not ramp:
        return None
    for fg, bg in norms.pairs:
        fgv, bgv = norms.resolve_color(fg), norms.resolve_color(bg)
        if not fgv or not bgv:
            continue
        moving = fgv if wants_fg else bgv
        idx = next((i for i, (_k, v) in enumerate(ramp)
                    if v.lower() == str(moving).lower()), None)
        if idx is None:
            continue
        step = idx - 1 if direction == "lighter" else idx + 1
        if not 0 <= step < len(ramp):
            continue
        cand = ramp[step][1]
        r = contrast_ratio(cand, bgv) if wants_fg else contrast_ratio(fgv, cand)
        if r is not None and r < NORMAL_TEXT_MIN:
            return {"verdict": "rejected", "checker": "script",
                    "reason": ("one step %s puts %s/%s at %.2f:1 against a %.1f:1 "
                               "floor — there is no room left in that direction"
                               % (direction, fg, bg, r, NORMAL_TEXT_MIN)),
                    "alternatives": color_alternatives(cand, fg, bg, fgv, bgv, norms)}
    return None


def color_alternatives(proposed, fg, bg, fgv, bgv, norms):
    """A refusal without an alternative is a wall, not a negotiation."""
    out = []
    ramp = norms.gray_ramp()
    for _k, v in ramp:
        r = contrast_ratio(v, bgv)
        if r is not None and r >= NORMAL_TEXT_MIN:
            out.append("use %s on %s (%.2f:1) — the nearest tone on the ramp "
                       "that still clears the floor" % (v, bg, r))
            break
    for _k, v in reversed(ramp):
        r = contrast_ratio(fgv, v)
        if r is not None and r >= NORMAL_TEXT_MIN:
            out.append("keep %s and darken the background to %s (%.2f:1)"
                       % (fg, v, r))
            break
    out.append("keep %s as it is and carry the emphasis with weight or size "
               "instead of tone" % fg)
    return out[:3]


def check_dimension(text, norms):
    kind = None
    if re.search(r"\b(шрифт\w*|кегл\w*|font|type size|text size)\b", text, re.I):
        kind = "type"
    elif re.search(r"\b(отступ\w*|поля|padding|margin|spacing|gap)\b", text, re.I):
        kind = "space"
    if not kind:
        return None
    m = re.search(r"\b([0-9]*\.?[0-9]+)\s*(px|rem)\b", text, re.I)
    if not m:
        return None
    want = to_px(m.group(0))
    steps = norms.type_steps if kind == "type" else norms.space_steps
    if want is None or not steps:
        return None
    if any(abs(want - px) < 0.51 for _k, px in steps):
        return None
    near = sorted(steps, key=lambda kv: abs(kv[1] - want))[:2]
    ladder = "type scale" if kind == "type" else "8pt spacing ladder"
    return {
        "verdict": "rejected", "checker": "script",
        "reason": ("%s is not a step on the %s — an off-ladder value is how a "
                   "scale quietly stops being one" % (m.group(0), ladder)),
        "alternatives": ["%s (%s, %gpx)" % (k, ladder, px) for k, px in near] +
                        ["add the step to the skin's scale if the design "
                         "genuinely needs it — one decision, recorded"],
    }


def q3_conflict(pin, contract, log_text):
    text = str(pin.get("text") or "")
    low = text.lower()
    for excl in contract.get("exclusions") or []:
        if excl and excl.lower() in low:
            return {"verdict": "rejected", "checker": "script",
                    "reason": ("`%s` is listed in scope.exclusions — this was "
                               "put outside the project on purpose" % excl),
                    "alternatives": ["take it out of scope.exclusions first, "
                                     "as an explicit decision",
                                     "achieve the same thing inside the current "
                                     "scope",
                                     "park it for the next run"],
                    "conflict_ref": "contract: scope.exclusions"}
    if not log_text:
        return None
    words = {w for w in re.findall(r"[A-Za-zА-Яа-яёЁ]{5,}", low)
             if w not in STOPWORDS}
    if len(words) < 2:
        return None
    for line in log_text.splitlines():
        ll = line.lower()
        if not NEGATIVE.search(ll):
            continue
        if len({w for w in words if w in ll}) >= 2:
            return {"verdict": "needs_model", "question_kind": "conflict",
                    "conflict_ref": line.strip()[:180]}
    return None


def q4_duplicate(pin, seen_hashes):
    text = " ".join(str(pin.get("text") or "").lower().split())
    if not text:
        return None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest in seen_hashes:
        other = seen_hashes[digest]
        return {"verdict": "duplicate", "checker": "script",
                "question": ("word for word the same as pin %s — merge them, or "
                             "did you mean two different elements?" % other)}
    seen_hashes[digest] = pin.get("id") or "?"
    if pin.get("duplicate_of"):
        return {"verdict": "duplicate", "checker": "script",
                "question": ("this looks like pin %s said differently — merge "
                             "with it, or keep both?" % pin["duplicate_of"])}
    return None


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------
def check_pin(pin, markup, norms, contract, log_text, seen_hashes, allow_model):
    unmeasured = []
    for probe in (lambda: q1_feasible(pin, markup),
                  lambda: q2_norms(pin, pin.get("lane"), norms),
                  lambda: q3_conflict(pin, contract, log_text),
                  lambda: q4_duplicate(pin, seen_hashes)):
        res = probe()
        if not res:
            continue
        unmeasured.extend(res.pop("unmeasured", []))
        if res["verdict"] == "pass":
            continue
        if res["verdict"] == "needs_model":
            res = escalate(pin, res, allow_model)
        return finish(res, unmeasured)
    return finish({"verdict": "pass", "checker": "script"}, unmeasured)


def escalate(pin, res, allow_model):
    """The two places judgement is allowed to cost something. Without a small
    model the pin is not guessed at — it goes to the owner, marked."""
    kind = res.get("question_kind")
    if allow_model:
        answer = ask_small_model(kind, pin, {"conflict_ref": res.get("conflict_ref")})
        if answer:
            answer.setdefault("checker", "model")
            if res.get("conflict_ref"):
                answer.setdefault("conflict_ref", res["conflict_ref"])
            return answer
    if kind == "conflict":
        return {"verdict": "clarify", "checker": "script",
                "checker_unavailable": True,
                "conflict_ref": res.get("conflict_ref"),
                "question": ("this may contradict a decision already recorded: "
                             "%s — apply it anyway, or keep the earlier decision?"
                             % (res.get("conflict_ref") or "see the decision log"))}
    return {"verdict": "clarify", "checker": "script", "checker_unavailable": True,
            "question": ("this pin has no element it can be tied to — which "
                         "element on the screen do you mean?")}


def finish(res, unmeasured):
    out = {
        "verdict": res["verdict"],
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checker": res.get("checker", "script"),
        "reason": res.get("reason"),
        "alternatives": res.get("alternatives") or [],
        "question": res.get("question"),
        "conflict_ref": res.get("conflict_ref"),
    }
    if res.get("checker_unavailable"):
        out["checker_unavailable"] = True
    if unmeasured:
        out["unmeasured"] = unmeasured
    return out


STATUS_OF = {"pass": "checked", "clarify": "clarify", "rejected": "rejected",
             "duplicate": "duplicate"}


def check(root, pin_id, build, as_json):
    path = os.path.join(root, PINS)
    if not os.path.isfile(path):
        print("pins: nothing classified yet — run `dops pins classify` first")
        return 2
    with open(path, encoding="utf-8") as f:
        report = json.load(f)

    contract = read_contract(root)
    skin_doc, skin_path = load_skin(root, contract["base_skin"])
    norms = Norms(skin_doc)
    build_dir = find_build(root, build)
    markup = build_markup(build_dir)
    log_path = os.path.join(root, DECISION_LOG)
    log_text = open(log_path, encoding="utf-8").read() if os.path.isfile(log_path) else ""
    allow_model = small_model_available()

    seen_hashes, checked = {}, 0
    for pin in report.get("pins", []):
        if pin_id and pin.get("id") != pin_id:
            continue
        pin["check"] = check_pin(pin, markup, norms, contract, log_text,
                                 seen_hashes, allow_model)
        pin["status"] = STATUS_OF[pin["check"]["verdict"]]
        checked += 1

    report["checked"] = checked
    report["check_env"] = {
        "skin": skin_path or "none",
        "build": build_dir or "none",
        "decision_log": bool(log_text),
        "small_model": bool(allow_model),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    rows = [p for p in report["pins"] if not pin_id or p.get("id") == pin_id]
    if as_json:
        print(json.dumps({"checked": checked, "env": report["check_env"],
                          "pins": rows}, ensure_ascii=False, indent=2))
    else:
        print_report(rows, report["check_env"])
    return 0 if all(p["check"]["verdict"] == "pass" for p in rows) else 1


MARK = {"pass": "ok", "clarify": "ask", "rejected": "no", "duplicate": "dup"}


def print_report(rows, env):
    for p in rows:
        c = p.get("check") or {}
        print("  [%s] %-8s %s  %s" % (c.get("verdict", "?"), MARK.get(c.get("verdict"), "?"),
                                      p.get("id") or "—", (p.get("text") or "")[:56]))
        if c.get("reason"):
            print("        why: %s" % c["reason"])
        for a in c.get("alternatives") or []:
            print("        or:  %s" % a)
        if c.get("question"):
            print("        ask: %s" % c["question"])
        if c.get("conflict_ref"):
            print("        ref: %s" % c["conflict_ref"])
        for u in c.get("unmeasured") or []:
            print("        n/a: %s" % u)
    tally = {}
    for p in rows:
        v = (p.get("check") or {}).get("verdict", "?")
        tally[v] = tally.get(v, 0) + 1
    print("  checked %d: %s" % (len(rows), ", ".join(
        "%s %d" % (k, tally[k]) for k in sorted(tally))))
    scripted = sum(1 for p in rows if (p.get("check") or {}).get("checker") == "script")
    if rows:
        print("  %d of %d (%.0f%%) decided by script alone, no model call"
              % (scripted, len(rows), 100.0 * scripted / len(rows)))
    if not env.get("small_model"):
        print("  note: no small model in the environment ($DOPS_SMALL_MODEL) — "
              "judgement pins went to you rather than being guessed at")
    if env.get("build") == "none":
        print("  note: no build found — question 1 could not be measured")


def answer(root, pin_id, text):
    """The owner replies inside the pin, not in chat: the answer belongs where
    the question was asked. The old wording is kept, never overwritten."""
    path = os.path.join(root, PINS)
    if not os.path.isfile(path):
        print("pins: nothing classified yet")
        return 2
    with open(path, encoding="utf-8") as f:
        report = json.load(f)
    for pin in report.get("pins", []):
        if pin.get("id") != pin_id:
            continue
        pin["supersedes"] = pin.get("text")
        pin["text"] = text
        pin["status"] = "new"
        pin["answered_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        pin.pop("check", None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("pin %s updated and sent back to classify (was: %s)"
              % (pin_id, (pin["supersedes"] or "")[:60]))
        return 0
    print("pins: no pin %s" % pin_id)
    return 2


def metrics(root, as_json):
    """§5 of the conveyor spec. Every number here is counted, not estimated."""
    path = os.path.join(root, PINS)
    if not os.path.isfile(path):
        print("pins: nothing classified yet")
        return 2
    with open(path, encoding="utf-8") as f:
        report = json.load(f)
    pins = report.get("pins", [])
    checked = [p for p in pins if p.get("check")]
    lat = []
    for p in checked:
        born, done = p.get("created_at"), p["check"].get("checked_at")
        if born and done:
            try:
                b = time.mktime(time.strptime(born[:19], "%Y-%m-%dT%H:%M:%S"))
                d = time.mktime(time.strptime(done[:19], "%Y-%m-%dT%H:%M:%S"))
                lat.append(max(0.0, d - b))
            except ValueError:
                pass
    ab = [p for p in checked if p.get("lane") in ("A", "B")]
    ab_script = [p for p in ab if p["check"].get("checker") == "script"]
    out = {
        "pins_total": len(pins),
        "pins_checked": len(checked),
        "revision_latency_seconds_median": round(sorted(lat)[len(lat) // 2], 1) if lat else None,
        "rejected_share": pct(checked, lambda p: p["check"]["verdict"] == "rejected"),
        "clarify_share": pct(checked, lambda p: p["check"]["verdict"] == "clarify"),
        "script_only_share": pct(checked, lambda p: p["check"].get("checker") == "script"),
        "lane_ab_script_only_share": pct(ab, lambda p: True) and
                                     round(100.0 * len(ab_script) / len(ab), 1) if ab else None,
        "alternatives_offered": sum(1 for p in checked if p["check"].get("alternatives")),
        "alternatives_accepted": sum(1 for p in checked if p.get("accepted_alternative")),
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for k, v in out.items():
            print("  %-38s %s" % (k, "—" if v is None else v))
    return 0


def pct(rows, pred):
    if not rows:
        return None
    return round(100.0 * sum(1 for r in rows if pred(r)) / len(rows), 1)


# --------------------------------------------------------------------------
# acceptance probes
# --------------------------------------------------------------------------
FAKE_MODEL = r"""#!/usr/bin/env python3
import json, sys
req = json.load(sys.stdin)
print(json.dumps({"verdict": "rejected", "checker": "model",
                  "reason": "the recorded decision still stands",
                  "alternatives": ["keep the earlier decision",
                                   "reopen it as a new decision"]}))
"""


def _fixture(tmp, pins, log=None, markup=None):
    import shutil
    os.makedirs(os.path.join(tmp, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "site"), exist_ok=True)
    with open(os.path.join(tmp, "site", "index.html"), "w", encoding="utf-8") as f:
        f.write(markup if markup is not None else
                '<main id="hero"><h1 class="title">x</h1><section class="prog">p</section></main>')
    with open(os.path.join(tmp, "artifacts", "design-contract.yaml"), "w",
              encoding="utf-8") as f:
        f.write("visual: {base_skin: base-site}\nscope:\n  exclusions:\n"
                "    - \"личный кабинет\"\n")
    if log is not None:
        with open(os.path.join(tmp, "artifacts", "decision-log.md"), "w",
                  encoding="utf-8") as f:
            f.write(log)
    rows = []
    for i, p in enumerate(pins, start=1):
        rows.append(dict({"id": "a-%04d" % i, "selector": "#hero",
                          "lane": "A", "kind": "visual", "status": "triaged",
                          "created_at": "2026-08-06T01:00:00"}, **p))
    with open(os.path.join(tmp, PINS), "w", encoding="utf-8") as f:
        json.dump({"schema": "dops-pins/1", "count": len(rows), "pins": rows}, f,
                  ensure_ascii=False)
    shutil.copy2  # keep the import meaningful for readers
    return os.path.join(tmp, PINS)


def _verdicts(tmp):
    with open(os.path.join(tmp, PINS), encoding="utf-8") as f:
        return [(p["id"], p["check"]) for p in json.load(f)["pins"]]


def self_test():
    import tempfile
    problems = []
    quiet = open(os.devnull, "w")
    real_stdout = sys.stdout

    def run(tmp, **kw):
        sys.stdout = quiet
        try:
            return check(tmp, kw.get("pin"), kw.get("build"), False)
        finally:
            sys.stdout = real_stdout

    # 1. a well-formed lane-A pin on an element that exists passes
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "заголовок тонет, сделать крупнее"}])
        rc = run(tmp)
        v = _verdicts(tmp)[0][1]
        if rc != 0 or v["verdict"] != "pass":
            problems.append("a valid lane-A pin did not pass: %r" % v)
        if v["checker"] != "script":
            problems.append("a valid lane-A pin cost a model call")

    # 2. a contrast violation is refused WITH alternatives
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "сделай текст заголовка #cccccc"}])
        rc = run(tmp)
        v = _verdicts(tmp)[0][1]
        if v["verdict"] != "rejected":
            problems.append("a 1.6:1 text colour was not refused: %r" % v)
        elif not v["alternatives"] or not v["reason"]:
            problems.append("a refusal arrived without reason/alternatives — a wall")

    # 3. a selector that no longer resolves asks instead of guessing
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "поправь отступ", "selector": "#gone"}])
        run(tmp)
        v = _verdicts(tmp)[0][1]
        if v["verdict"] != "clarify" or not v["question"]:
            problems.append("a dead selector did not become a question: %r" % v)

    # 4. a conflict with the decision log surfaces BEFORE the work
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "добавь таймер обратного отсчёта до концерта"}],
                 log="## Verdict\n- отказ: таймер обратного отсчёта не ставим\n")
        run(tmp)
        v = _verdicts(tmp)[0][1]
        # the ban list catches this one first; either route is a refusal, and a
        # refusal from the cheaper check is the better outcome
        if v["verdict"] != "rejected":
            problems.append("a banned/decided-against request was not refused: %r" % v)

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "сделать программу вертикальной лентой"}],
                 log="## Verdict\n- решено не делать программу вертикальной лентой\n")
        run(tmp)
        v = _verdicts(tmp)[0][1]
        if v["verdict"] != "clarify" or not v.get("conflict_ref"):
            problems.append("a decision-log conflict did not reach the owner: %r" % v)
        if not v.get("checker_unavailable"):
            problems.append("a judgement pin was not marked as un-adjudicated")

    # 5. an exact duplicate is questioned, never silently merged
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "опечатка в подписи"}, {"text": "опечатка в подписи"}])
        run(tmp)
        vs = _verdicts(tmp)
        if vs[0][1]["verdict"] != "pass" or vs[1][1]["verdict"] != "duplicate":
            problems.append("the duplicate pair was handled as %r"
                            % [v["verdict"] for _i, v in vs])
        elif not vs[1][1]["question"]:
            problems.append("a duplicate was flagged without asking the owner")

    # 6. scope.exclusions is a refusal with a reference, not a surprise later
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "сделай личный кабинет для покупателей", "lane": "C"}])
        run(tmp)
        v = _verdicts(tmp)[0][1]
        if v["verdict"] != "rejected" or "exclusions" not in (v.get("conflict_ref") or ""):
            problems.append("an excluded request was not refused with a reference: %r" % v)

    # 7. an off-ladder value is refused with the nearest steps
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "поставь отступ 13px между блоками"}])
        run(tmp)
        v = _verdicts(tmp)[0][1]
        if v["verdict"] != "rejected" or len(v["alternatives"]) < 2:
            problems.append("an off-ladder spacing value was not refused: %r" % v)

    # 8. ten lane-A pins, zero model calls — the checker stays cheaper than
    #    the work it routes
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "поправь формулировку %d" % i} for i in range(10)])
        run(tmp)
        vs = _verdicts(tmp)
        if any(v["checker"] != "script" for _i, v in vs):
            problems.append("a lane-A batch was not decided by script alone")
        if sum(1 for _i, v in vs if v["verdict"] == "pass") < 1:
            problems.append("a batch of ordinary copy edits produced no passes")

    # 9. with a small model plugged in, the judgement pin is adjudicated
    with tempfile.TemporaryDirectory() as tmp:
        fake = os.path.join(tmp, "fake-model.py")
        with open(fake, "w", encoding="utf-8") as f:
            f.write(FAKE_MODEL)
        _fixture(tmp, [{"text": "сделать программу вертикальной лентой"}],
                 log="## Verdict\n- решено не делать программу вертикальной лентой\n")
        # $DOPS_SMALL_MODEL is a shell command, so the fixture quotes its own
        # paths — this checkout lives under a directory with a space in it,
        # and an unquoted interpreter path silently produced "no model".
        import shlex
        os.environ["DOPS_SMALL_MODEL"] = "%s %s" % (shlex.quote(sys.executable),
                                                    shlex.quote(fake))
        try:
            run(tmp)
        finally:
            os.environ.pop("DOPS_SMALL_MODEL", None)
        v = _verdicts(tmp)[0][1]
        if v["checker"] != "model" or v["verdict"] != "rejected":
            problems.append("the small-model boundary was not used when present: %r" % v)
        if v.get("checker_unavailable"):
            problems.append("an adjudicated pin was still marked unavailable")

    # 10. the owner's answer returns to the pin and keeps the old wording
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, [{"text": "поправь это", "selector": ""}])
        run(tmp)
        sys.stdout = quiet
        try:
            answer(tmp, "a-0001", "увеличить заголовок дня до step3")
        finally:
            sys.stdout = real_stdout
        with open(os.path.join(tmp, PINS), encoding="utf-8") as f:
            p = json.load(f)["pins"][0]
        if p.get("supersedes") != "поправь это" or p["status"] != "new" or "check" in p:
            problems.append("an answered pin did not go back to classify: %r" % p)

    quiet.close()
    if problems:
        for p in problems:
            print("self-test FAIL: dops-pins-check: %s" % p)
        return 1
    print("OK: dops-pins-check self-test (10 probes: refusals carry alternatives, "
          "dead selectors ask, duplicates are questioned not dropped, lane A is "
          "script-only, the model boundary degrades honestly)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", default="check",
                    choices=["check", "answer", "metrics"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--pin", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--build", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.command == "answer":
        if not args.pin or args.text is None:
            print("usage: dops pins answer --pin ID --text \"...\"", file=sys.stderr)
            return 2
        return answer(root, args.pin, args.text)
    if args.command == "metrics":
        return metrics(root, args.json)
    return check(root, args.pin, args.build, args.json)


if __name__ == "__main__":
    sys.exit(main())
