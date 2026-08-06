#!/usr/bin/env python3
"""dops_panel.py — the self-service panel (П-4): emit the safe domain, apply the delta.

Design: Kimi, `Most/tasks/2026-08-06-kimi-p4-panel-spec.md`.

The owner turns knobs on the live artefact — palette, type scale, dark theme —
and sees the result in the same second, with no assistant, no model and no dev
server in the loop. "Doing it" becomes "saw it and kept it". This file is the
two ends of that: `emit` computes what the knobs are allowed to offer, `apply`
is the only door back into `tokens.json`.

The load-bearing decision is that **the safe domain is baked at build time, not
computed in the browser**:

  1. WCAG maths in JS would be a second copy of the formula in
     `check-contrast.py` — the drift [A.10] forbids. Here the formula is
     imported, exactly as `dops_pins_check.py` imports it.
  2. Artefacts open from `file://`, where `fetch` of tokens.json is blocked; a
     config attached as a <script> always works.
  3. Poka-yoke: an unsafe value is not "warned about", it is *unrepresentable*
     — it never appears among the options, even if the JS has a bug.

A knob is emitted only for a variable the artefact actually uses. A knob that
turns nothing is not cosmetic: the owner concludes "this thing does not react"
and stops trusting the whole panel.

Usage:
  dops panel emit  --skin NAME --artifact page.html [--out panel-config.js]
  dops panel apply token-delta.json [--root DIR]
  dops panel metrics [--root DIR] [--json]

Exit: 0 ok, 1 refused (nothing written), 2 usage/io.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dops_pins_check as pins_check   # noqa: E402  (skin resolution + WCAG maths)

PANEL_VERSION = 1
COMPILE = os.path.join(PKG_ROOT, ".agents", "skills", "visual-director",
                       "scripts", "compile-tokens.py")
CONTRAST = os.path.join(PKG_ROOT, ".agents", "skills", "quality-guardian",
                        "scripts", "check-contrast.py")
DECISION_LOG = os.path.join("artifacts", "decision-log.md")
METRICS = os.path.join("artifacts", "panel-metrics.jsonl")

# Whole-scale variants. Individual sizes are deliberately not knobs: moving one
# step breaks the hierarchy the scale exists to hold. Switching the ratio moves
# every step at once, so the hierarchy survives by construction.
SCALE_RATIOS = [1.2, 1.25, 1.333]
SCALE_STEPS = ["step-1", "step0", "step1", "step2", "step3", "step4", "step5"]
MEASURE_OPTIONS = ["60ch", "65ch", "70ch"]

# Rule 2 of the spec: the accent tokens answer to their own floors rather than
# to the generic text pair.
ACCENT_RULES = {
    "actionPrimary": [("canvas", 3.0), ("actionPrimaryText", 4.5)],
    "focusRing": [("canvas", 3.0)],
}


# --------------------------------------------------------------------------
# thresholds: taken from D3, never restated
# --------------------------------------------------------------------------
def gate_thresholds():
    """{(fg_token, bg_token): minimum} straight out of check-contrast.py.

    D3 is where the floors were decided (including the tertiary tier at 3:1,
    ruled UI chrome on 2026-08-06). A second table here would drift from it,
    and the panel would then offer values the floor rejects."""
    cc = pins_check._CC
    if not cc:
        return {}
    out = {}
    for fg_css, bg_css, _label, minimum in cc.PAIRS:
        out[(uncamel(fg_css), uncamel(bg_css))] = minimum
    return out


def uncamel(css_var):
    """`--action-primary-text` -> `actionPrimaryText`."""
    parts = css_var.lstrip("-").split("-")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def css_var_for(path):
    """Mirror of compile-tokens.css_name_for for the semantic layer."""
    parts = path.split(".")
    if parts[0] == "semantic":
        parts = parts[1:]
    if parts and parts[0] == "color":
        parts = parts[1:]
    return "--" + "-".join(kebab(p) for p in parts)


def kebab(s):
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s).replace("_", "-").lower()


# --------------------------------------------------------------------------
# reading the skin
# --------------------------------------------------------------------------
def node_at(doc, path):
    node = doc
    for key in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def raw_value(doc, path):
    node = node_at(doc, path)
    return node.get("$value") if isinstance(node, dict) else None


def ramp_of(value):
    """`{primitive.color.gray.900}` -> `primitive.color.gray`. A literal value
    has no declared ramp, so it has no alternatives — and a knob invented for
    it would be the emitter making up design decisions."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"\{(primitive\.color\.[A-Za-z0-9_]+)\.[A-Za-z0-9_-]+\}",
                     value.strip())
    return m.group(1) if m else None


def ramp_steps(doc, ramp_path):
    node = node_at(doc, ramp_path) or {}
    out = []
    for key, val in node.items():
        if isinstance(val, dict) and isinstance(val.get("$value"), str):
            out.append(("{%s.%s}" % (ramp_path, key), val["$value"], key))
    return out


def resolved_colors(doc, theme):
    """Every semantic colour token resolved to a literal, for one theme."""
    base = node_at(doc, "semantic.color") or {}
    out = {}
    for name in base:
        val = pins_check.Norms(doc).resolve_color(name)
        if isinstance(val, str):
            out[name] = val
    if theme == "dark":
        dark = node_at(doc, "semantic.dark.color") or {}
        for name, spec in dark.items():
            if isinstance(spec, dict) and isinstance(spec.get("$value"), str):
                out[name] = spec["$value"]
    return out


def used_vars(artifact):
    """Which CSS variables the artefact actually consumes. The artefact plus
    every stylesheet sitting beside it — a knob for a variable nobody reads is
    a knob that turns nothing."""
    if not artifact or not os.path.isfile(artifact):
        return None
    texts, seen = [], set()
    base = os.path.dirname(os.path.abspath(artifact))
    for path in [artifact] + [os.path.join(base, f) for f in sorted(os.listdir(base))
                              if f.endswith(".css")]:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        try:
            texts.append(open(path, encoding="utf-8", errors="replace").read())
        except OSError:
            pass
    blob = "\n".join(texts)
    return set(re.findall(r"var\(\s*(--[A-Za-z0-9_-]+)", blob))


# --------------------------------------------------------------------------
# the knobs
# --------------------------------------------------------------------------
def colour_knobs(doc, theme, used, thresholds):
    knobs, skipped = [], []
    pairs = [(p.get("foreground"), p.get("background"))
             for p in (doc.get("$meta") or {}).get("contrastPairs", [])
             if p.get("foreground") and p.get("background")]
    resolved = resolved_colors(doc, theme)
    prefix = "semantic.dark.color." if theme == "dark" else "semantic.color."

    names = []
    for fg, bg in pairs:
        for n in (fg, bg):
            if n not in names:
                names.append(n)
    for n in ACCENT_RULES:
        if n not in names and n in resolved:
            names.append(n)

    for name in names:
        path = prefix + name
        declared = raw_value(doc, path)
        ramp = ramp_of(declared)
        if ramp is None:
            # No declared ramp to draw from. In the dark theme every colour is
            # authored as a literal by design ("dark is a separate design, not
            # an inversion"), so it has no alternatives the emitter may invent.
            skipped.append({"path": path, "why": "value is a literal — no declared "
                                                 "ramp of alternatives"})
            continue
        var = css_var_for("semantic.color." + name)
        if used is not None and var not in used:
            skipped.append({"path": path, "why": "%s is not used by the artefact" % var})
            continue
        options = []
        for ref, literal, step in ramp_steps(doc, ramp):
            ok, worst = candidate_passes(name, literal, resolved, pairs, thresholds)
            if not ok:
                continue
            options.append({"value": ref, "label": "%s · %s" % (step, literal),
                            "literal": literal,
                            "contrast": ("%.2f:1" % worst) if worst else ""})
        if len(options) < 2:
            skipped.append({"path": path, "why": "fewer than two safe tones on %s"
                                                 % ramp})
            continue
        knobs.append({
            "id": "color-%s-%s" % (kebab(name), theme),
            "label": name,
            "path": path,
            "css_var": var,
            "kind": "color",
            "theme": theme,
            "current": declared,
            "options": options,
        })
    return knobs, skipped


def candidate_passes(name, literal, resolved, pairs, thresholds):
    """A tone survives only if EVERY pair the token takes part in still clears
    its own floor — and the accent rules on top, where they apply."""
    trial = dict(resolved)
    trial[name] = literal
    worst = None
    for fg, bg in pairs:
        if name not in (fg, bg):
            continue
        a, b = trial.get(fg), trial.get(bg)
        if not a or not b:
            continue
        r = pins_check.contrast_ratio(a, b)
        if r is None:
            continue
        need = thresholds.get((fg, bg), 4.5)
        if r < need:
            return False, None
        worst = r if worst is None else min(worst, r)
    for other, need in ACCENT_RULES.get(name, []):
        a, b = trial.get(name), trial.get(other)
        if not a or not b:
            continue
        r = pins_check.contrast_ratio(a, b)
        if r is None or r < need:
            return False, None
        worst = r if worst is None else min(worst, r)
    return True, worst


def scale_knob(doc, used):
    node = node_at(doc, "primitive.font.scale") or {}
    base = pins_check.to_px(node.get("step0", {}).get("$value")) or 16.0
    vars_moved = ["--font-scale-%s" % kebab(s) for s in SCALE_STEPS]
    if used is not None and not any(v in used for v in vars_moved):
        return None, {"path": "primitive.font.scale",
                      "why": "no --font-scale-* variable is used by the artefact"}
    current = node.get("ratio", {}).get("$value")
    options = []
    for ratio in SCALE_RATIOS:
        steps = {}
        for i, step in enumerate(SCALE_STEPS, start=-1):
            steps[step] = "%grem" % round(base * (ratio ** i) / 16.0, 3)
        options.append({"value": {"ratio": ratio, "steps": steps},
                        "label": "%s×" % ratio,
                        "css": {"--font-scale-%s" % kebab(k): v
                                for k, v in steps.items()}})
    return {
        "id": "type-scale", "label": "Типографическая шкала",
        "path": "primitive.font.scale", "css_var": vars_moved[0],
        "kind": "scale-variant", "theme": "both",
        "current": {"ratio": current},
        "options": options,
    }, None


def enum_knob(doc, path, label, options, used, kind="enum"):
    if node_at(doc, path) is None:
        return None, {"path": path, "why": "token absent from the skin"}
    var = css_var_for(path)
    if used is not None and var not in used:
        return None, {"path": path, "why": "%s is not used by the artefact" % var}
    if len(options) < 2:
        return None, {"path": path, "why": "fewer than two options"}
    return {"id": kebab(path.replace(".", "-")), "label": label, "path": path,
            "css_var": var, "kind": kind, "theme": "both",
            "current": raw_value(doc, path), "options": options}, None


def taste_knobs(doc, used, group, label_prefix):
    """Radii and shadows: pure taste, no norm to violate, so every declared
    primitive step is allowed."""
    knobs, skipped = [], []
    node = node_at(doc, "semantic." + group) or {}
    prim = node_at(doc, "primitive." + group) or {}
    # `literal` is what the preview writes into the CSS variable: a browser
    # cannot resolve `{primitive.radius.md}`, only the value behind it.
    options = [{"value": "{primitive.%s.%s}" % (group, k),
                "label": "%s · %s" % (k, v["$value"]), "literal": v["$value"]}
               for k, v in prim.items()
               if isinstance(v, dict) and isinstance(v.get("$value"), str)]
    for name in node:
        knob, why = enum_knob(doc, "semantic.%s.%s" % (group, name),
                              "%s %s" % (label_prefix, name), options, used)
        (knobs if knob else skipped).append(knob or why)
    return knobs, skipped


def build_config(doc, skin, artifact, sha):
    used = used_vars(artifact)
    thresholds = gate_thresholds()
    knobs, skipped = [], []

    for theme in ("light", "dark"):
        if theme == "dark" and not node_at(doc, "semantic.dark"):
            continue
        k, s = colour_knobs(doc, theme, used, thresholds)
        knobs += k
        skipped += s

    knob, why = scale_knob(doc, used)
    (knobs.append(knob) if knob else skipped.append(why))

    knob, why = enum_knob(doc, "semantic.measure.body", "Длина строки",
                          [{"value": v, "label": v, "literal": v}
                           for v in MEASURE_OPTIONS], used)
    (knobs.append(knob) if knob else skipped.append(why))

    for group, label in (("radius", "Скругление"), ("shadow", "Тень")):
        k, s = taste_knobs(doc, used, group, label)
        knobs += k
        skipped += s

    if node_at(doc, "semantic.dark"):
        knobs.append({"id": "theme", "label": "Тёмная тема", "path": "",
                      "css_var": "", "kind": "theme-toggle", "theme": "both",
                      "current": "light",
                      "options": [{"value": "light", "label": "Светлая"},
                                  {"value": "dark", "label": "Тёмная"}]})

    return {
        "panel_version": PANEL_VERSION,
        "skin": skin,
        "tokens_sha256": sha,
        "emitted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "artifact_scanned": bool(used is not None),
        "knobs": knobs,
        "skipped": skipped,
    }


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tokens(root, skin):
    doc, path = pins_check.load_skin(root, skin)
    if not doc:
        return None, ""
    return doc, path


def emit(root, skin, artifact, out_path, as_json):
    doc, tokens_path = load_tokens(root, skin)
    if not doc:
        print("panel: no tokens.json for skin %r" % skin)
        return 2
    cfg = build_config(doc, skin, artifact, sha256_of(tokens_path))
    if out_path is None:
        out_path = (os.path.join(os.path.dirname(os.path.abspath(artifact)),
                                 "panel-config.js") if artifact
                    else os.path.join(root, "panel-config.js"))
    body = ("/* GENERATED by `dops panel emit` — do not edit by hand.\n"
            " * The safe domain of every knob is computed here, from the skin,\n"
            " * so the browser never does contrast maths and an unsafe value is\n"
            " * simply not among the options. */\n"
            "window.DOPS_PANEL_CONFIG = %s;\n"
            % json.dumps(cfg, ensure_ascii=False, indent=2))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)

    if as_json:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return 0
    print("panel: %d knob(s) -> %s" % (len(cfg["knobs"]), out_path))
    for k in cfg["knobs"]:
        print("  %-22s %-14s %d option(s)%s"
              % (k["id"], k["kind"], len(k["options"]),
                 "" if k["theme"] == "both" else "  [%s]" % k["theme"]))
    for s in cfg["skipped"]:
        print("  — no knob for %-28s %s" % (s["path"], s["why"]))
    if not cfg["artifact_scanned"]:
        print("  note: no artefact given — knobs were not filtered by actual use")
    return 0


# --------------------------------------------------------------------------
# the pointed patch
# --------------------------------------------------------------------------
def span_of_key(text, key, start, end):
    """Find `"key":` at the top level of the object spanning [start, end) and
    return the span of its value. A plain search would hit the same name
    nested deeper (`ink` lives in semantic.color AND semantic.dark.color), so
    this walks with a depth counter instead of trusting uniqueness."""
    i, depth, in_str, esc = start, 0, False, False
    target = '"%s"' % key
    while i < end:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            if depth == 1 and text.startswith(target, i):
                j = i + len(target)
                while j < end and text[j] in " \t\r\n":
                    j += 1
                if j < end and text[j] == ":":
                    j += 1
                    while j < end and text[j] in " \t\r\n":
                        j += 1
                    return j, end_of_value(text, j, end)
            in_str = True
            i += 1
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return None
        i += 1
    return None


def end_of_value(text, start, end):
    c = text[start]
    if c in "{[":
        close = "}" if c == "{" else "]"
        depth, i, in_str, esc = 0, start, False, False
        while i < end:
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == c:
                depth += 1
            elif ch == close:
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return end
    if c == '"':
        i, esc = start + 1, False
        while i < end:
            if esc:
                esc = False
            elif text[i] == "\\":
                esc = True
            elif text[i] == '"':
                return i + 1
            i += 1
        return end
    i = start
    while i < end and text[i] not in ",}\n":
        i += 1
    return i


def locate(text, dotted):
    """Span of the value at a dotted path, walking key by key."""
    start, end = 0, len(text)
    # the document itself is one object: descend into it first
    while start < end and text[start] in " \t\r\n":
        start += 1
    for key in dotted.split("."):
        span = span_of_key(text, key, start, end)
        if span is None:
            return None
        start, end = span
    return start, end


def patch_value(text, dotted, new_json):
    """Replace one value in place. A load-and-dump would rewrite the whole
    document and flatten the hand-set formatting and the `"comment"` entries
    that carry the reasoning — the same damage `inject.py` avoids."""
    span = locate(text, dotted)
    if span is None:
        return None
    start, end = span
    return text[:start] + new_json + text[end:]


def set_token(text, path, value):
    """A knob writes the token's `$value`; the scale variant replaces the whole
    scale object, so its steps can never be half-written."""
    if path == "primitive.font.scale":
        node = {"ratio": {"$value": value["ratio"], "$type": "number"}}
        for step, dim in value["steps"].items():
            node[step] = {"$value": dim, "$type": "dimension"}
        return patch_value(text, path, json.dumps(node, ensure_ascii=False, indent=6))
    return patch_value(text, path + ".$value", json.dumps(value, ensure_ascii=False))


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------
def refuse(msg, action):
    print("panel: refused — %s" % msg)
    print("       %s" % action)
    return 1


def apply_delta(root, delta_path, log_it=True):
    try:
        with open(delta_path, encoding="utf-8") as f:
            delta = json.load(f)
    except (OSError, ValueError) as exc:
        print("panel: cannot read %s: %s" % (delta_path, exc))
        return 2
    skin = delta.get("skin") or ""
    doc, tokens_path = load_tokens(root, skin)
    if not doc:
        print("panel: no tokens.json for skin %r" % skin)
        return 2

    # 1. freshness — applying over someone else's edits silently is the same
    #    class of defect as a verdict on top of a check that never ran.
    current_sha = sha256_of(tokens_path)
    if delta.get("tokens_sha256") != current_sha:
        return refuse("the panel is stale: the skin changed since it was emitted",
                      "re-emit and turn the knobs again: dops panel emit --skin %s "
                      "--artifact <page.html>" % skin)

    # 2. whitelist — recomputed from the CURRENT skin, so the boundary of what
    #    the panel may write is mechanical rather than conventional.
    fresh = build_config(doc, skin, None, current_sha)
    by_path = {k["path"]: k for k in fresh["knobs"] if k["path"]}
    changes = delta.get("changes") or []
    if not changes:
        print("panel: the delta is empty — nothing to apply")
        return 0
    for i, ch in enumerate(changes):
        path, to = ch.get("path"), ch.get("to")
        knob = by_path.get(path)
        if knob is None:
            return refuse("change %d writes %r, which no knob offers" % (i + 1, path),
                          "the delta was edited by hand, or the skin moved — re-emit.")
        if not any(opt["value"] == to for opt in knob["options"]):
            return refuse("change %d sets %r to a value outside the knob's options"
                          % (i + 1, path),
                          "only values the emitter computed as safe can be applied.")

    # 3. pointed patch, on a copy first
    backup = tokens_path + ".panel-backup"
    shutil.copy2(tokens_path, backup)
    try:
        text = open(tokens_path, encoding="utf-8").read()
        for ch in changes:
            patched = set_token(text, ch["path"], ch["to"])
            if patched is None:
                raise ValueError("cannot locate %s in the tokens file" % ch["path"])
            text = patched
        json.loads(text)                      # the file must still be JSON
        with open(tokens_path, "w", encoding="utf-8") as f:
            f.write(text)

        # 4. re-verify the norms. "Cannot happen" can: the skin may have moved
        #    between emit and apply, and defence in depth is cheaper than an
        #    investigation.
        ok, why = verify_tokens(tokens_path)
        if not ok:
            raise ValueError(why)
    except Exception as exc:                  # noqa: BLE001 — any failure rolls back
        shutil.copy2(backup, tokens_path)
        os.remove(backup)
        return refuse("%s" % exc, "tokens.json was rolled back in full; nothing "
                                  "was applied.")
    os.remove(backup)

    # 5. hash graph — a changed input invalidates what stands on it [E.3], and
    #    without this step the owner's veto cost stops being honest.
    hashed = record_hash(root, tokens_path)

    # 6. the record
    line = ("- %s · owner-panel: %s · dops panel apply · delta %s"
            % (time.strftime("%Y-%m-%dT%H:%M"),
               "; ".join(summarise(ch) for ch in changes),
               os.path.basename(delta_path)))
    if log_it:
        write_log(root, line)
    write_metric(root, {"event": "panel_apply", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "skin": skin, "changes": len(changes),
                        "paths": [c["path"] for c in changes], "hashes": hashed})
    print("applied %d change(s), contrast re-verified, hashes %s"
          % (len(changes), "recorded" if hashed else "not recorded (no graph)"))
    print(line)
    return 0


def summarise(ch):
    if ch["path"] == "primitive.font.scale":
        return "type scale %s→%s" % ((ch.get("from") or {}).get("ratio", "?"),
                                     (ch.get("to") or {}).get("ratio", "?"))
    short = lambda v: str(v).strip("{}").replace("primitive.color.", "")
    return "%s %s→%s" % (ch["path"].split(".")[-1], short(ch.get("from")),
                         short(ch.get("to")))


def verify_tokens(tokens_path):
    """The same two gates the floor runs: the compiler and D3."""
    work = tokens_path + ".panel-check"
    css, tw = work + ".css", work + ".theme.css"
    try:
        r = subprocess.run([sys.executable, COMPILE, tokens_path,
                            "--out-css", css, "--out-tailwind", tw],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False, "compile-tokens rejected the result: %s" % last_fail(r.stdout)
        r = subprocess.run([sys.executable, CONTRAST, css, "--tokens", tokens_path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False, "D3 contrast rejected the result: %s" % last_fail(r.stdout)
        return True, ""
    finally:
        for p in (css, tw):
            if os.path.exists(p):
                os.remove(p)


def last_fail(out):
    fails = [l for l in (out or "").splitlines() if l.startswith("FAIL")]
    return fails[-1] if fails else (out or "").strip()[:160]


def record_hash(root, tokens_path):
    script = os.path.join(HERE, "dops_hash.py")
    if not os.path.isfile(script):
        return False
    r = subprocess.run([sys.executable, script, "record", tokens_path,
                        "--root", root], capture_output=True, text=True)
    return r.returncode == 0


def write_log(root, line):
    path = os.path.join(root, DECISION_LOG)
    if not os.path.isfile(path):
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_metric(root, row):
    path = os.path.join(root, METRICS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def metrics(root, as_json):
    path = os.path.join(root, METRICS)
    rows = []
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    applies = [r for r in rows if r.get("event") == "panel_apply"]
    stale = [r for r in rows if r.get("event") == "panel_stale_reject"]
    usage = {}
    for r in applies:
        for p in r.get("paths") or []:
            usage[p] = usage.get(p, 0) + 1
    out = {
        "panel_applies": len(applies),
        "panel_changes_applied": sum(r.get("changes", 0) for r in applies),
        "panel_stale_rejects": len(stale),
        "panel_knob_usage": usage,
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for k, v in out.items():
            print("  %-26s %s" % (k, v if v != {} else "—"))
    return 0


# --------------------------------------------------------------------------
# acceptance probes
# --------------------------------------------------------------------------
def _skin_copy(tmp, skin="base-site"):
    dst = os.path.join(tmp, "skins", skin)
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(os.path.join(PKG_ROOT, "skins", skin, "tokens.json"),
                 os.path.join(dst, "tokens.json"))
    return os.path.join(dst, "tokens.json")


def _artifact(tmp, vars_used):
    path = os.path.join(tmp, "page.html")
    body = "\n".join("  .x%d { color: var(%s); }" % (i, v)
                     for i, v in enumerate(vars_used))
    with open(path, "w", encoding="utf-8") as f:
        f.write("<style>\n%s\n</style>\n<main>x</main>\n" % body)
    return path


def _cfg(tmp, skin="base-site", artifact=None):
    doc, tokens = load_tokens(tmp, skin)
    return build_config(doc, skin, artifact, sha256_of(tokens)), tokens


def _delta(tmp, tokens, skin, changes):
    path = os.path.join(tmp, "token-delta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"panel_version": PANEL_VERSION, "skin": skin,
                   "tokens_sha256": sha256_of(tokens), "changes": changes},
                  f, ensure_ascii=False)
    return path


ALL_VARS = ["--ink", "--canvas", "--ink-muted", "--action-primary",
            "--action-primary-text", "--focus-ring", "--text-primary",
            "--text-secondary", "--text-tertiary", "--canvas-raised",
            "--surface-dark", "--ink-on-dark", "--measure-body",
            "--font-scale-step1", "--radius-card", "--shadow-raised"]


def self_test():
    import tempfile
    problems = []
    quiet = open(os.devnull, "w")
    real = sys.stdout

    def hush(fn, *a, **kw):
        sys.stdout = quiet
        try:
            return fn(*a, **kw)
        finally:
            sys.stdout = real

    # 1. property test on the asset itself: every offered tone clears the floor
    with tempfile.TemporaryDirectory() as tmp:
        _skin_copy(tmp)
        cfg, _tokens = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS))
        doc, _ = load_tokens(tmp, "base-site")
        thresholds = gate_thresholds()
        pairs = [(p["foreground"], p["background"])
                 for p in doc["$meta"]["contrastPairs"]]
        colour = [k for k in cfg["knobs"] if k["kind"] == "color"]
        if not colour:
            problems.append("no colour knob was emitted at all")
        for knob in colour:
            name = knob["label"]
            resolved = resolved_colors(doc, knob["theme"])
            for opt in knob["options"]:
                trial = dict(resolved, **{name: opt["literal"]})
                for fg, bg in pairs:
                    if name not in (fg, bg):
                        continue
                    a, b = trial.get(fg), trial.get(bg)
                    if not a or not b:
                        continue
                    r = pins_check.contrast_ratio(a, b)
                    need = thresholds.get((fg, bg), 4.5)
                    if r is not None and r < need:
                        problems.append(
                            "%s offers %s, which puts %s/%s at %.2f:1 (need %.1f)"
                            % (knob["id"], opt["literal"], fg, bg, r, need))
                for other, need in ACCENT_RULES.get(name, []):
                    a, b = trial.get(name), trial.get(other)
                    r = pins_check.contrast_ratio(a, b) if a and b else None
                    if r is not None and r < need:
                        problems.append("%s offers %s, %.2f:1 against %s (need %.1f)"
                                        % (knob["id"], opt["literal"], r, other, need))

    # 2. a knob exists only for a variable the artefact uses
    with tempfile.TemporaryDirectory() as tmp:
        _skin_copy(tmp)
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ["--canvas", "--measure-body"]))
        ids = {k["id"] for k in cfg["knobs"]}
        if any(i.startswith("color-ink-") for i in ids):
            problems.append("a knob was emitted for --ink, which the artefact never uses")
        if "semantic-measure-body" not in ids:
            problems.append("no knob for --measure-body, which the artefact does use")

    # 3. a token with no verifiable constraint gets no knob — honest absence
    with tempfile.TemporaryDirectory() as tmp:
        _skin_copy(tmp)
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS + ["--border-subtle"]))
        if any(k["label"] == "borderSubtle" for k in cfg["knobs"]):
            problems.append("borderSubtle got a knob without a floor to verify it")
        # The dark layer is authored as literals on purpose ("dark is a separate
        # design, not an inversion"), so its text colours have no declared ramp
        # and get no knob. The few dark tokens that DO reference a ramp
        # (focusRing -> accent) are a different case and may have one.
        dark = {k["label"]: k for k in cfg["knobs"]
                if k["kind"] == "color" and k["theme"] == "dark"}
        invented = [n for n in dark if n in ("ink", "canvas", "inkMuted",
                                             "textPrimary", "textSecondary",
                                             "textTertiary", "canvasRaised")]
        if invented:
            problems.append("dark knobs invented for literal-valued tokens: %r"
                            % invented)
        if "focusRing" not in dark:
            problems.append("no dark knob for focusRing, which does declare a ramp")
        if not any(k["kind"] == "theme-toggle" for k in cfg["knobs"]):
            problems.append("the skin has a dark layer but no theme toggle")

    # 4. round-trip: emit -> change -> apply; only declared paths move, and the
    #    reasoning stored in `comment` entries survives
    with tempfile.TemporaryDirectory() as tmp:
        tokens = _skin_copy(tmp)
        before = open(tokens, encoding="utf-8").read()
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS))
        ink = next(k for k in cfg["knobs"] if k["id"] == "color-ink-light")
        pick = next(o for o in ink["options"] if o["value"] != ink["current"])
        d = _delta(tmp, tokens, "base-site",
                   [{"path": "semantic.color.ink", "from": ink["current"],
                     "to": pick["value"], "theme": "light", "at": "now"}])
        if hush(apply_delta, tmp, d, log_it=False) != 0:
            problems.append("a well-formed delta was refused")
        after = open(tokens, encoding="utf-8").read()
        b, a = json.loads(before), json.loads(after)
        moved = [p for p in ("semantic.color.ink", "semantic.color.inkMuted",
                             "semantic.color.canvas")
                 if raw_value(b, p) != raw_value(a, p)]
        if moved != ["semantic.color.ink"]:
            problems.append("apply moved %r, expected only semantic.color.ink" % moved)
        if before.count('"comment"') != after.count('"comment"'):
            problems.append("apply destroyed a `comment` entry — the reasoning "
                            "stored in the file")
        if raw_value(a, "semantic.color.ink") != pick["value"]:
            problems.append("apply did not write the chosen value")

    # 5. a stale panel is refused and touches nothing
    with tempfile.TemporaryDirectory() as tmp:
        tokens = _skin_copy(tmp)
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS))
        ink = next(k for k in cfg["knobs"] if k["id"] == "color-ink-light")
        pick = next(o for o in ink["options"] if o["value"] != ink["current"])
        d = _delta(tmp, tokens, "base-site",
                   [{"path": "semantic.color.ink", "from": ink["current"],
                     "to": pick["value"], "theme": "light", "at": "now"}])
        with open(d, encoding="utf-8") as f:
            payload = json.load(f)
        payload["tokens_sha256"] = "0" * 64
        with open(d, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        snapshot = open(tokens, encoding="utf-8").read()
        if hush(apply_delta, tmp, d) != 1:
            problems.append("a stale delta was not refused")
        if open(tokens, encoding="utf-8").read() != snapshot:
            problems.append("a refused apply still modified tokens.json")

    # 6. a value outside the knob's options is refused by the whitelist
    with tempfile.TemporaryDirectory() as tmp:
        tokens = _skin_copy(tmp)
        snapshot = open(tokens, encoding="utf-8").read()
        d = _delta(tmp, tokens, "base-site",
                   [{"path": "semantic.color.ink", "from": "x",
                     "to": "#cccccc", "theme": "light", "at": "now"}])
        if hush(apply_delta, tmp, d) != 1:
            problems.append("a hand-edited value outside the options was applied")
        if open(tokens, encoding="utf-8").read() != snapshot:
            problems.append("a whitelist refusal still modified tokens.json")
        d = _delta(tmp, tokens, "base-site",
                   [{"path": "component.button.primaryBg", "from": "x",
                     "to": "{semantic.color.ink}", "theme": "light", "at": "now"}])
        if hush(apply_delta, tmp, d) != 1:
            problems.append("the panel wrote to a path no knob offers")

    # 7. a result the floor rejects is rolled back in full
    with tempfile.TemporaryDirectory() as tmp:
        tokens = _skin_copy(tmp)
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS))
        ink = next(k for k in cfg["knobs"] if k["id"] == "color-ink-light")
        pick = next(o for o in ink["options"] if o["value"] != ink["current"])
        d = _delta(tmp, tokens, "base-site",
                   [{"path": "semantic.color.ink", "from": ink["current"],
                     "to": pick["value"], "theme": "light", "at": "now"}])
        # the skin moves under the panel: canvas is darkened by hand, so the
        # whitelisted tone now fails D3. The sha check would normally catch
        # this, so the probe rewrites the delta's sha to reach step 4.
        raw = open(tokens, encoding="utf-8").read()
        raw = patch_value(raw, "semantic.color.canvas.$value", '"#3a3a3a"')
        with open(tokens, "w", encoding="utf-8") as f:
            f.write(raw)
        with open(d, encoding="utf-8") as f:
            payload = json.load(f)
        payload["tokens_sha256"] = sha256_of(tokens)
        with open(d, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        snapshot = open(tokens, encoding="utf-8").read()
        rc = hush(apply_delta, tmp, d)
        if rc != 1:
            problems.append("a result failing the floor was accepted (rc=%s)" % rc)
        if open(tokens, encoding="utf-8").read() != snapshot:
            problems.append("a failed apply left the file changed — no full rollback")
        if os.path.exists(tokens + ".panel-backup"):
            problems.append("the rollback left its backup behind")

    # 8. the whole scale moves atomically
    with tempfile.TemporaryDirectory() as tmp:
        tokens = _skin_copy(tmp)
        cfg, _ = _cfg(tmp, artifact=_artifact(tmp, ALL_VARS))
        scale = next((k for k in cfg["knobs"] if k["id"] == "type-scale"), None)
        if not scale:
            problems.append("no type-scale knob was emitted")
        else:
            pick = next(o for o in scale["options"] if o["value"]["ratio"] == 1.333)
            d = _delta(tmp, tokens, "base-site",
                       [{"path": "primitive.font.scale",
                         "from": {"ratio": 1.25}, "to": pick["value"],
                         "theme": "both", "at": "now"}])
            if hush(apply_delta, tmp, d, log_it=False) != 0:
                problems.append("a scale variant was refused")
            doc = json.loads(open(tokens, encoding="utf-8").read())
            node = node_at(doc, "primitive.font.scale") or {}
            if node.get("ratio", {}).get("$value") != 1.333:
                problems.append("the scale ratio did not move")
            missing = [s for s in SCALE_STEPS if s not in node]
            if missing:
                problems.append("scale switch left steps missing: %r" % missing)
            if any(node[s]["$value"] != pick["value"]["steps"][s] for s in SCALE_STEPS):
                problems.append("a scale step was not rewritten with the variant")

    quiet.close()
    if problems:
        for p in problems:
            print("self-test FAIL: dops-panel: %s" % p)
        return 1
    print("OK: dops-panel self-test (8 probes: every offered tone clears D3, knobs "
          "only for used variables, honest absence, round-trip keeps comments, "
          "stale/whitelist/floor failures all refuse and roll back)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", default="emit",
                    choices=["emit", "apply", "metrics"])
    ap.add_argument("delta", nargs="?", default=None)
    ap.add_argument("--root", default=".")
    ap.add_argument("--skin", default=None)
    ap.add_argument("--artifact", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)

    if args.command == "metrics":
        return metrics(root, args.json)
    if args.command == "apply":
        if not args.delta:
            print("usage: dops panel apply token-delta.json", file=sys.stderr)
            return 2
        return apply_delta(root, args.delta)

    skin = args.skin or pins_check.read_contract(root)["base_skin"]
    return emit(root, skin, args.artifact, args.out, args.json)


if __name__ == "__main__":
    sys.exit(main())
