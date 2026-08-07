#!/usr/bin/env python3
"""dops_pins_sweep.py — streaming intake and machine execution (П-5).

Design: Kimi, `Most/tasks/2026-08-06-kimi-p5-stream-intake-spec.md`.

What this fixes: the revision conveyor worked, but it walked. The owner
pressed Export, the file landed in ~/Downloads, somebody moved it into the
project, and the pins waited for the assistant to have a session. The reaction
to a pin was tied to the executor's schedule rather than to the moment the pin
was written.

  sweep   one intake pass: take only the NEW pins, classify (П-2) and check
          (П-3) them in birth order, write the store, record the latencies,
          print one line.
  apply   execute the pins whose plan is machine-executable, one transaction
          per pin, with the same safety chain the panel uses.

Two commands rather than "the watcher calls classify, then check": two
external calls mean two reads and two writes of the store and a split
atomicity. The lesson of the kruto run — a floor made of many invocations can
be passed halfway — applies to intake as well.

The honest premise: **no executor for lanes A/B exists yet.** Only pins whose
plan carries complete, extracted parameters are applied; everything else waits
for the assistant. Marking a prose plan `machine: true` would fabricate
executability, which is worse than an honest wait [A.6] — so the share of
machine plans is a measurement, never a target.

Usage:
  dops pins sweep [--root DIR] [--in FILE] [--adopt FILE] [--json]
  dops pins apply [--root DIR] [--machine-only] [--json]

Exit: 0 ok, 1 something needs the owner, 2 usage/io.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dops_pins as pins            # noqa: E402  (classification, one shape)
import dops_pins_check as check     # noqa: E402  (the checker, skin resolution)
import dops_panel as panel          # noqa: E402  (pointed patch + verify chain)
import dops_dom as dom              # noqa: E402  (Ф-1: the selector's subtree)

STORE = os.path.join("artifacts", "pins.json")
ANNOTATIONS = os.path.join("artifacts", "annotations.json")
DECISION_LOG = os.path.join("artifacts", "decision-log.md")
COPY_LINTER = os.path.join(PKG_ROOT, "packs", "copy-linter", "scripts", "lint-copy.py")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def read_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# adoption: the browser exports to ~/Downloads, not into the project
# --------------------------------------------------------------------------
def adopt(root, candidate):
    """Take a foreign annotations file into the project — but only if it is
    plausibly OURS. A file of the same name from another project must never
    overwrite this one's pins, and a mismatch is a skip with a logged line,
    not silence and not an error."""
    canonical = os.path.join(root, ANNOTATIONS)
    incoming = read_json(candidate)
    if not isinstance(incoming, list):
        return False, "%s is not a list of pins — not adopted" % candidate
    mine = read_json(canonical)
    if isinstance(mine, list) and mine:
        theirs = {p.get("id") for p in incoming if isinstance(p, dict) and p.get("id")}
        ours = {p.get("id") for p in mine if isinstance(p, dict) and p.get("id")}
        if not (theirs & ours):
            return False, ("%s shares no pin id with this project's "
                           "annotations — not adopted" % candidate)
    os.makedirs(os.path.dirname(canonical), exist_ok=True)
    shutil.copy2(candidate, canonical)
    return True, "adopted %s" % candidate


# --------------------------------------------------------------------------
# sweep
# --------------------------------------------------------------------------
def is_new(stored, incoming):
    """A pin is new when the store has never seen it, or when the owner's own
    answer sent it back round (П-3 sets `new` on answer)."""
    if stored is None:
        return str(incoming.get("status") or "new") in ("", "new")
    return str(stored.get("status") or "") == "new"


def sweep(root, in_path, adopt_path, as_json):
    notes = []
    if adopt_path:
        ok, why = adopt(root, adopt_path)
        notes.append(why)
        if not ok:
            print("sweep: %s" % why)

    src = in_path if os.path.isabs(in_path) else os.path.join(root, in_path)
    incoming = read_json(src)
    if not isinstance(incoming, list):
        print("sweep: no annotations at %s — export them from the artefact first"
              % src)
        return 2

    store = read_json(os.path.join(root, STORE)) or {
        "schema": "dops-pins/1", "source": src, "count": 0, "lanes": {}, "pins": []}
    by_id = {p.get("id"): p for p in store.get("pins", []) if p.get("id")}

    fresh = pins.dedupe([p for p in incoming if isinstance(p, dict)])
    todo = [p for p in fresh if is_new(by_id.get(p.get("id")), p)]
    todo.sort(key=lambda p: str(p.get("created_at") or p.get("at") or ""))

    if not todo:
        write_json(os.path.join(root, STORE), store)
        print("sweep: 0 new")
        return 0

    for p in todo:
        row = pins.row_for(p)
        prior = by_id.get(row["id"])
        if prior:
            # an answered pin keeps its history: the wording it superseded and
            # the moment the owner wrote it
            row["supersedes"] = prior.get("supersedes")
            row["answered_at"] = prior.get("answered_at")
        by_id[row["id"]] = row

    store["pins"] = [by_id[i] for i in
                     sorted(by_id, key=lambda i: str(by_id[i].get("created_at") or ""))]
    store["count"] = len(store["pins"])
    store["lanes"] = pins.tally(store["pins"])
    store["source"] = src
    write_json(os.path.join(root, STORE), store)

    # The check runs over the whole store but only the fresh pins lack a
    # verdict; running it once keeps intake atomic — the kruto lesson.
    ids = {p["id"] for p in [by_id[p.get("id")] for p in todo if p.get("id")]}
    quiet = open(os.devnull, "w")
    real, sys.stdout = sys.stdout, quiet
    try:
        check.check(root, None, None, False, only=ids)
    finally:
        sys.stdout = real
        quiet.close()

    store = read_json(os.path.join(root, STORE))
    done = [p for p in store["pins"] if p.get("id") in ids]
    tally = {}
    for p in done:
        v = (p.get("check") or {}).get("verdict", "?")
        tally[v] = tally.get(v, 0) + 1
    summary = {
        "new": len(done),
        "checked": tally.get("pass", 0),
        "clarify": tally.get("clarify", 0),
        "rejected": tally.get("rejected", 0),
        "duplicate": tally.get("duplicate", 0),
        "machine": sum(1 for p in done if (p.get("plan") or {}).get("machine")),
        "notes": notes,
    }
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("sweep: %d new → %d checked, %d clarify, %d rejected, %d duplicate "
              "(%d machine-executable)"
              % (summary["new"], summary["checked"], summary["clarify"],
                 summary["rejected"], summary["duplicate"], summary["machine"]))
    return 0 if not (summary["clarify"] or summary["duplicate"]) else 1


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------
def target_of(pin):
    """What two pins have to share to be in conflict."""
    plan = pin.get("plan") or {}
    params = plan.get("params") or {}
    if plan.get("action") == "set_token":
        return ("set_token", params.get("path"))
    if plan.get("action") == "set_text":
        return ("set_text", params.get("selector"), params.get("find"))
    return None


def apply_pins(root, machine_only, as_json):
    store_path = os.path.join(root, STORE)
    store = read_json(store_path)
    if not store:
        print("pins: nothing swept yet — run `dops pins sweep`")
        return 2

    ready = [p for p in store["pins"]
             if p.get("status") == "checked"
             and (p.get("check") or {}).get("verdict") == "pass"]
    machine = [p for p in ready if (p.get("plan") or {}).get("machine")]
    manual = [p for p in ready if not (p.get("plan") or {}).get("machine")]

    # The owner's LAST explicit instruction wins, as in the control queue.
    # Applying both and letting the second overwrite the first without a trace
    # is the failure this rule exists to prevent.
    latest, superseded = {}, []
    for p in sorted(machine, key=lambda p: str(p.get("created_at") or "")):
        key = target_of(p)
        if key in latest:
            older = latest[key]
            older["status"] = "superseded"
            older["superseded_by"] = p.get("id")
            older["superseded_why"] = (
                "pin %s asks for the same change later; your last instruction "
                "wins, and this one was kept rather than silently overwritten"
                % p.get("id"))
            superseded.append(older)
        latest[key] = p
    todo = [latest[k] for k in latest]
    todo.sort(key=lambda p: str(p.get("created_at") or ""))

    applied, failed = [], []
    for pin in todo:
        ok, note = run_one(root, pin)
        if ok:
            pin["status"] = "applied"
            pin["applied_at"] = now()
            pin["applied_note"] = note
            pin.pop("apply_error", None)
            applied.append(pin)
            write_log(root, "- %s · owner-pin %s: %s · dops pins apply"
                      % (time.strftime("%Y-%m-%dT%H:%M"), pin.get("id"), note))
        else:
            pin["status"] = "checked"
            pin["apply_error"] = note
            failed.append(pin)

    write_json(store_path, store)
    summary = {
        "processed": len(todo),
        "applied": len(applied),
        "superseded": len(superseded),
        "failed": len(failed),
        "waiting_on_owner": sum(1 for p in store["pins"]
                                if (p.get("check") or {}).get("verdict")
                                in ("clarify", "duplicate")),
        "waiting_on_assistant": len(manual),
    }
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if not failed else 1

    print("apply: %d applied, %d superseded, %d failed" %
          (len(applied), len(superseded), len(failed)))
    for p in applied:
        print("  ok   %s  %s" % (p.get("id"), p.get("applied_note")))
    for p in superseded:
        print("  sup  %s  superseded by %s" % (p.get("id"), p.get("superseded_by")))
    for p in failed:
        print("  err  %s  %s" % (p.get("id"), p.get("apply_error")))
    if manual and not machine_only:
        print("  %d pin(s) passed the checker but have no machine plan — "
              "they are the assistant's work:" % len(manual))
        for p in manual:
            print("    %s  %s" % (p.get("id"), (p.get("text") or "")[:60]))
    elif manual:
        print("  %d pin(s) skipped: no machine plan (--machine-only)" % len(manual))
    if summary["waiting_on_owner"]:
        print("  %d pin(s) waiting on the owner" % summary["waiting_on_owner"])
    return 0 if not failed else 1


def run_one(root, pin):
    plan = pin.get("plan") or {}
    action = plan.get("action")
    params = plan.get("params") or {}
    if action == "set_token":
        return set_token(root, params)
    if action == "set_text":
        return set_text(root, params)
    return False, "unknown action %r" % action


def set_token(root, params):
    """The same technique the panel uses: a pointed text patch, then the
    compiler and D3, then a full rollback if either refuses. The pin was
    checked against the skin's ranges, but the skin may have moved since —
    verifying again is cheaper than an investigation."""
    skin = check.read_contract(root)["base_skin"]
    doc, tokens_path = panel.load_tokens(root, skin)
    if not doc:
        return False, "no tokens.json for skin %r" % skin
    path, to = params.get("path"), params.get("to")
    if not path or to is None:
        return False, "incomplete set_token parameters"
    if panel.raw_value(doc, path) is None:
        return False, "%s does not exist in skin %s" % (path, skin)

    backup = tokens_path + ".pin-backup"
    shutil.copy2(tokens_path, backup)
    try:
        text = open(tokens_path, encoding="utf-8").read()
        patched = panel.set_token(text, path, to)
        if patched is None:
            raise ValueError("cannot locate %s in the tokens file" % path)
        json.loads(patched)
        with open(tokens_path, "w", encoding="utf-8") as f:
            f.write(patched)
        ok, why = panel.verify_tokens(tokens_path)
        if not ok:
            raise ValueError(why)
    except Exception as exc:                      # noqa: BLE001 — all roll back
        shutil.copy2(backup, tokens_path)
        os.remove(backup)
        return False, "%s (rolled back, nothing written)" % exc
    os.remove(backup)
    panel.record_hash(root, tokens_path)
    return True, "%s → %s" % (path, to)


def html_files(build):
    for base, dirs, files in os.walk(build):
        dirs[:] = [d for d in dirs if d not in
                   ("node_modules", ".git", "__pycache__", ".venv")]
        for fn in sorted(files):
            if fn.endswith((".html", ".htm")):
                yield os.path.join(base, fn)


def set_text(root, params):
    """A copy edit in the artefact source.

    Without a selector the string must occur exactly once in the whole build:
    two matches mean the pin does not identify what to change, and guessing
    which one the owner meant is the cheap-wrong-lane mistake again. With a
    selector (Ф-1) the same rule is applied INSIDE that element's subtree —
    strictness unchanged, scope narrowed to what the pin actually knows."""
    find, repl = params.get("find"), params.get("replace")
    selector = (params.get("selector") or "").strip()
    if not find or repl is None:
        return False, "incomplete set_text parameters"
    build = check.find_build(root, None)
    if not build:
        return False, "no build to edit"

    scoped, hits, out_of_grammar = bool(selector), [], False
    for p in html_files(build):
        try:
            body = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if scoped:
            found = dom.scoped_hits(body, find, selector)
            if found is None:
                out_of_grammar = True
                break
            for span in found:
                hits.append((p, body, span))
        else:
            at = 0
            while True:
                i = body.find(find, at)
                if i < 0:
                    break
                hits.append((p, body, (i, i + len(find))))
                at = i + len(find)

    if out_of_grammar:
        # honest degradation [A.6]: an unsupported selector falls back to the
        # whole-build rule and SAYS so, rather than matching approximately
        scoped, hits = False, []
        for p in html_files(build):
            try:
                body = open(p, encoding="utf-8").read()
            except OSError:
                continue
            at = 0
            while True:
                i = body.find(find, at)
                if i < 0:
                    break
                hits.append((p, body, (i, i + len(find))))
                at = i + len(find)

    where = ("inside `%s`" % selector[:48]) if scoped else "in the build"
    if not hits:
        return False, ("the string %r is not %s any more" % (find[:40], where))
    if len(hits) > 1:
        return False, ("the string %r occurs %d times %s — the pin does not "
                       "say which one" % (find[:40], len(hits), where))

    path, body, (start, end) = hits[0]
    backup = path + ".pin-backup"
    shutil.copy2(path, backup)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body[:start] + repl + body[end:])
        ok, why = verify_copy(path)
        if not ok:
            raise ValueError(why)
    except Exception as exc:                      # noqa: BLE001
        shutil.copy2(backup, path)
        os.remove(backup)
        return False, "%s (rolled back, nothing written)" % exc
    os.remove(backup)
    return True, "%r → %r in %s%s" % (
        find[:32], repl[:32], os.path.basename(path),
        (" (scoped to `%s`)" % selector[:40]) if scoped else "")


def verify_copy(path):
    """Re-run the check that owns copy quality. Absent pack = honest note, not
    a fabricated pass."""
    if not os.path.isfile(COPY_LINTER):
        return True, "copy-linter absent — text not re-verified"
    r = subprocess.run([sys.executable, COPY_LINTER, path],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return True, ""
    fails = [l for l in (r.stdout or "").splitlines() if "FAIL" in l or "slop" in l]
    return False, "copy-linter refused the new text: %s" % (
        fails[-1] if fails else (r.stdout or "").strip()[:120])


def write_log(root, line):
    path = os.path.join(root, DECISION_LOG)
    if not os.path.isfile(path):
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# --------------------------------------------------------------------------
# acceptance probes
# --------------------------------------------------------------------------
IMPORT_FIELDS = ["id", "lane", "plan", "status"]     # what gate-annotate merges


def _project(tmp, annotations, with_skin=True, markup=None):
    os.makedirs(os.path.join(tmp, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "site"), exist_ok=True)
    with open(os.path.join(tmp, "site", "index.html"), "w", encoding="utf-8") as f:
        f.write(markup if markup is not None else
                '<main id="hero"><h1 class="title">Полярная сцена</h1>'
                '<p class="note">три дня музыки</p></main>')
    with open(os.path.join(tmp, "artifacts", "design-contract.yaml"), "w",
              encoding="utf-8") as f:
        f.write("visual: {base_skin: base-site}\n")
    with open(os.path.join(tmp, "artifacts", "decision-log.md"), "w",
              encoding="utf-8") as f:
        f.write("# Decision log\n")
    if with_skin:
        dst = os.path.join(tmp, "skins", "base-site")
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(os.path.join(PKG_ROOT, "skins", "base-site", "tokens.json"),
                     os.path.join(dst, "tokens.json"))
    write_json(os.path.join(tmp, ANNOTATIONS), annotations)
    return tmp


def _pin(i, text, selector="#hero", created="2026-08-06T09:0%d:00"):
    return {"id": "a-%04d" % i, "selector": selector, "target_selector": selector,
            "viewport": 1440, "x": 1, "y": 2, "kind": "copy", "text": text,
            "created_at": created % i, "at": created % i, "status": "new"}


def _sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _store(tmp):
    return read_json(os.path.join(tmp, STORE))


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

    # 1. idempotent: a second pass with nothing new changes nothing
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "опечатка в подписи")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        before = _sha(os.path.join(tmp, STORE))
        sys.stdout = quiet
        try:
            rc = sweep(tmp, ANNOTATIONS, None, False)
        finally:
            sys.stdout = real
        after = _sha(os.path.join(tmp, STORE))
        if before != after:
            problems.append("a second sweep with no new pins rewrote the store")
        if rc != 0:
            problems.append("an empty sweep did not exit quietly (rc=%s)" % rc)

    # 2. an answered pin comes round again
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "поправь это", selector="")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        hush(check.answer, tmp, "a-0001", "заголовок дня сделать крупнее")
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        if row.get("status") == "new" or not row.get("check"):
            problems.append("an answered pin was not re-checked by the sweep")
        if row.get("supersedes") != "поправь это":
            problems.append("the sweep lost the wording the owner superseded")

    # 3. the store stays importable by gate-annotate
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "опечатка в подписи")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        for row in _store(tmp)["pins"]:
            missing = [f for f in IMPORT_FIELDS if f not in row]
            if missing:
                problems.append("a swept pin lacks %r, which Import merges" % missing)

    # 4. a machine set_token plan lands, with the whole safety chain
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "ink -> gray.700")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        if not (row.get("plan") or {}).get("machine"):
            problems.append("an explicit token instruction was not machine-planned")
        tokens = os.path.join(tmp, "skins", "base-site", "tokens.json")
        comments = open(tokens, encoding="utf-8").read().count('"comment"')
        rc = hush(apply_pins, tmp, True, False)
        doc = json.loads(open(tokens, encoding="utf-8").read())
        if panel.raw_value(doc, "semantic.color.ink") != "{primitive.color.gray.700}":
            problems.append("the token was not written (rc=%s)" % rc)
        if panel.raw_value(doc, "semantic.color.inkMuted") != "{primitive.color.gray.600}":
            problems.append("apply moved a token the pin never named")
        if open(tokens, encoding="utf-8").read().count('"comment"') != comments:
            problems.append("apply destroyed a comment in the tokens file")
        if _store(tmp)["pins"][0]["status"] != "applied":
            problems.append("an applied pin did not become `applied`")
        log = open(os.path.join(tmp, DECISION_LOG), encoding="utf-8").read()
        if "owner-pin a-0001" not in log:
            problems.append("an applied pin left no line in the decision log")

    # 5. a prose plan is skipped, not failed
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "кнопка бледная, сделай фон темнее")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        if (_store(tmp)["pins"][0].get("plan") or {}).get("machine"):
            problems.append("a prose plan was marked machine-executable")
        rc = hush(apply_pins, tmp, True, False)
        if rc != 0:
            problems.append("a prose-only pin made apply fail instead of skip")
        if _store(tmp)["pins"][0]["status"] == "applied":
            problems.append("a prose plan was somehow applied")

    # 6. two instructions on one token: the last one wins, visibly
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "ink -> gray.600"), _pin(2, "ink -> gray.700")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        hush(apply_pins, tmp, True, False)
        rows = {p["id"]: p for p in _store(tmp)["pins"]}
        if rows["a-0002"]["status"] != "applied":
            problems.append("the later instruction was not the one applied")
        if rows["a-0001"]["status"] != "superseded":
            problems.append("the earlier instruction was overwritten without a trace")
        elif rows["a-0001"].get("superseded_by") != "a-0002" or \
                not rows["a-0001"].get("superseded_why"):
            problems.append("a superseded pin carries no explanation")
        doc = json.loads(open(os.path.join(tmp, "skins", "base-site",
                                           "tokens.json"), encoding="utf-8").read())
        if panel.raw_value(doc, "semantic.color.ink") != "{primitive.color.gray.700}":
            problems.append("the conflicting pair left the wrong value behind")

    # 7. a value the floor refuses rolls back, and its neighbours still land
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "ink -> gray.100"),
                       _pin(2, "actionPrimary -> accent.700")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        tokens = os.path.join(tmp, "skins", "base-site", "tokens.json")
        rc = hush(apply_pins, tmp, True, False)
        rows = {p["id"]: p for p in _store(tmp)["pins"]}
        doc = json.loads(open(tokens, encoding="utf-8").read())
        if rows["a-0001"]["status"] != "checked" or not rows["a-0001"].get("apply_error"):
            problems.append("a refused transaction did not report apply_error")
        if panel.raw_value(doc, "semantic.color.ink") == "{primitive.color.gray.100}":
            problems.append("an unreadable colour was written despite the floor")
        if rows["a-0002"]["status"] != "applied":
            problems.append("one failed pin took its neighbour down with it")
        if rc != 1:
            problems.append("apply hid a failed transaction in its exit code")
        if os.path.exists(tokens + ".pin-backup"):
            problems.append("a rollback left its backup behind")

    # [Ф-1] the form's round trip: a pin born with its plan reaches the source
    TWO_SECTIONS = ('<main id="tickets"><p class="note">Билеты в продаже</p></main>'
                    '<footer id="foot"><p class="note">Билеты в продаже</p></footer>')

    def _form_pin(i, selector, find, repl, created="2026-08-07T09:0%d:00"):
        return {"id": "a-%04d" % i, "selector": selector,
                "target_selector": selector, "viewport": 1440, "x": 1, "y": 2,
                "kind": "copy", "status": "new", "lane": "A",
                "text": "правка на месте: «%s» → «%s»" % (find, repl),
                "created_at": created % i, "at": created % i,
                "plan": {"machine": True, "action": "set_text",
                         "params": {"selector": selector, "find": find,
                                    "replace": repl}}}

    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_form_pin(1, "#tickets > p.note", "Билеты в продаже",
                                 "Билеты уже в продаже")],
                 markup=TWO_SECTIONS)
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        plan = row.get("plan") or {}
        if not plan.get("machine") or plan.get("action") != "set_text":
            problems.append("a pin born with a machine plan lost it in intake")
        if (plan.get("params") or {}).get("find") != "Билеты в продаже":
            problems.append("the form's verbatim `find` was re-derived instead "
                            "of honoured: %r" % (plan.get("params"),))
        if row.get("lane") != "A":
            problems.append("a born machine plan did not force lane A")
        rc = hush(apply_pins, tmp, True, False)
        page = open(os.path.join(tmp, "site", "index.html"), encoding="utf-8").read()
        if "<main id=\"tickets\"><p class=\"note\">Билеты уже в продаже</p>" not in page:
            problems.append("the scoped edit did not land in its own section "
                            "(rc=%s)" % rc)
        if page.count("Билеты в продаже") != 1:
            problems.append("the edit escaped its scope and touched the footer")
        if _store(tmp)["pins"][0]["status"] != "applied":
            problems.append("an applied form pin did not become `applied`")
        log = open(os.path.join(tmp, DECISION_LOG), encoding="utf-8").read()
        if "owner-pin a-0001" not in log:
            problems.append("a form edit left no line in the decision log")

    # ...and without the scope the very same edit is refused, which is what
    # the scope is FOR: the duplicate string used to block both edits
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_form_pin(1, "", "Билеты в продаже", "Билеты уже в продаже")],
                 markup=TWO_SECTIONS)
        hush(sweep, tmp, ANNOTATIONS, None, False)
        hush(apply_pins, tmp, True, False)
        row = _store(tmp)["pins"][0]
        if row.get("status") == "applied":
            problems.append("an unscoped edit with two candidates was applied "
                            "— one of them was a guess")

    # a scope with no match and a scope with two are both refused with a reason
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_form_pin(1, "#tickets > p.note", "Нет такого текста", "X")],
                 markup=TWO_SECTIONS)
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        if (row.get("check") or {}).get("verdict") != "clarify":
            problems.append("an edit whose text is gone from its scope was not "
                            "sent back to the owner: %r" % (row.get("check"),))

    with tempfile.TemporaryDirectory() as tmp:
        twice = ('<main id="tickets"><p class="a">Билеты</p>'
                 '<p class="b">Билеты</p></main>')
        _project(tmp, [_form_pin(1, "#tickets", "Билеты", "Проходки")],
                 markup=twice)
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        if (row.get("check") or {}).get("verdict") != "clarify":
            problems.append("two matches inside one scope did not become a "
                            "question: %r" % (row.get("check"),))

    # a forged plan is dropped back to prose rather than trusted: `machine`
    # is a promise the executor acts on, so it is validated, not believed
    with tempfile.TemporaryDirectory() as tmp:
        forged = _form_pin(1, "#tickets > p.note", "Билеты в продаже", "X")
        forged["plan"]["params"].pop("replace")
        # prose the extractor cannot rescue, so this probe measures the
        # validation of the BORN plan and nothing else
        forged["text"] = "поправил подпись"
        _project(tmp, [forged], markup=TWO_SECTIONS)
        hush(sweep, tmp, ANNOTATIONS, None, False)
        if (_store(tmp)["pins"][0].get("plan") or {}).get("machine"):
            problems.append("an incomplete plan claiming `machine: true` was "
                            "taken at its word")

    # [Ф-1 §4] questions 3 and 4 are NEVER skipped for a form pin
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_form_pin(1, "#tickets > p.note", "Билеты в продаже",
                                 "Билеты уже в продаже")],
                 markup=TWO_SECTIONS)
        with open(os.path.join(tmp, "artifacts", "decision-log.md"), "a",
                  encoding="utf-8") as f:
            f.write("- 2026-08-07 · решено не менять формулировку «Билеты в "
                    "продаже» до старта продаж\n")
        hush(sweep, tmp, ANNOTATIONS, None, False)
        verdict = (_store(tmp)["pins"][0].get("check") or {}).get("verdict")
        if verdict == "pass":
            problems.append("a form edit contradicting the decision log passed "
                            "silently — question 3 must never be skipped")

    # 8. adoption refuses a stranger's file of the same name
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "опечатка в подписи")])
        foreign = os.path.join(tmp, "downloads-annotations.json")
        write_json(foreign, [{"id": "z-9999", "selector": "#x", "text": "чужое",
                              "created_at": "2026-08-06T09:00:00", "status": "new"}])
        canonical = os.path.join(tmp, ANNOTATIONS)
        before = _sha(canonical)
        ok, why = adopt(tmp, foreign)
        if ok or "shares no pin id" not in why:
            problems.append("a stranger's annotations file was adopted: %s" % why)
        if _sha(canonical) != before:
            problems.append("a refused adoption still overwrote the canonical file")
        # the same file gains one shared id and becomes ours
        write_json(foreign, [_pin(1, "опечатка в подписи"), {"id": "z-9999",
                   "selector": "#x", "text": "новое", "created_at": "2026-08-06T09:05:00",
                   "status": "new"}])
        ok, _why = adopt(tmp, foreign)
        if not ok:
            problems.append("a file sharing a pin id was not adopted")

    # 9. the latencies intake is measured by are actually recorded
    with tempfile.TemporaryDirectory() as tmp:
        _project(tmp, [_pin(1, "опечатка в подписи")])
        hush(sweep, tmp, ANNOTATIONS, None, False)
        row = _store(tmp)["pins"][0]
        if not row.get("classified_at") or not (row.get("check") or {}).get("checked_at"):
            problems.append("a swept pin has no classified_at/checked_at to measure")
        m = hush(check.metrics, tmp, False)
        if m != 0:
            problems.append("metrics could not read the swept store")

    quiet.close()
    if problems:
        for p in problems:
            print("self-test FAIL: dops-pins-sweep: %s" % p)
        return 1
    print("OK: dops-pins-sweep self-test (15 probes: idempotent intake, answered "
          "pins come round, a plan born in the form is honoured not re-derived, "
          "an edit lands only inside its own selector, last instruction "
          "wins visibly, failed transactions roll back alone, no stranger adopted)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", default="sweep", choices=["sweep", "apply"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--in", dest="in_path", default=ANNOTATIONS)
    ap.add_argument("--adopt", default=None)
    ap.add_argument("--machine-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    root = os.path.abspath(args.root)
    if args.command == "apply":
        return apply_pins(root, args.machine_only, args.json)
    return sweep(root, args.in_path, args.adopt, args.json)


if __name__ == "__main__":
    sys.exit(main())
