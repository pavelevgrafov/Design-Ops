#!/usr/bin/env python3
"""dops_lod.py — the depth ladder and its transitions (У-5).

Design: Kimi, `Most/tasks/2026-08-06-kimi-u5-u6-lod-runplan-spec.md` block 2.

`meta.target_lod`, `meta.lod_overrides` and `status.lod` have been fields in
the contract since v7.2 with nothing behind them. The consequence was not a
missing feature but a missing CHOICE: a run either stopped at whatever depth
it happened to reach and said nothing, or it polished past what was asked
and billed the owner for the difference. Both are decisions taken without
the person paying for them.

Three rules carry this file:

  1. **Depth is declared, never measured.** No formula over the artifact
     ("components per screen") can say how finished something is; it can only
     fabricate a number that looks like it can. So each stage declares what
     depth it PRODUCES (`produces_lod` in stages.json) and `status.lod` is
     the highest any closed stage produced. A stage that adds no depth — K0
     discovery, K3 verification — declares none, and that is the honest
     answer rather than a zero.
  2. **A transition carries its price or it is not published.** "Deepen?"
     without "+20 min / +30k tokens" is a status line, which is the illusion
     of control. The price comes from `cost-table.json`, which starts as
     estimates that say so and retrains on the project's own measurements.
  3. **Depth changes only on the owner's command.** Reaching less than the
     target without a command is under-delivery; reaching more without a
     command is overspend. Both are the same defect — the plan changed and
     nobody was asked — and both are reported as `lod_mismatch`.

Usage:
  dops lod status [--root DIR] [--json]      where the run is on the ladder
  dops lod price --from 200 --to 300 [--scope section]
  dops lod check [--root DIR]                the mismatch defect (§2.5)
  dops lod done [--root DIR]                 close the open deepening with a fact
  dops lod retrain [--write]                 estimates → medians, once there are 3
  dops lod --self-test

Exit: 0 ok, 1 refused / defect found, 2 usage.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dops_trace                        # noqa: E402  (owner of the stage history)
import dops_plan                         # noqa: E402  (owner of the flow-split)
import dops_checkpoint                   # noqa: E402  (owner of the checkpoint log)
import dops_hash                         # noqa: E402  (owner of the derivation graph)

STAGES = os.path.join(HERE, "stages.json")
COST_TABLE = os.path.join(HERE, "cost-table.json")
CONTRACT = os.path.join("artifacts", "design-contract.yaml")
LOG = os.path.join("artifacts", "lod-log.jsonl")

DEFAULT_TARGET = 200
LADDER = [100, 200, 300, 400]
MIN_SAMPLES = 3          # below this a median is a coincidence, not a measurement

# An owner command that explains why the run stopped short of its target.
# `defer` on the directions checkpoint is the same statement made at a
# checkpoint instead of in the queue, so it counts too. `deepen_lod` is in
# this list because a SCOPED deepening is an answer to the transition that
# deliberately leaves the rest of the product where it is: the owner was
# asked, looked at the price, and bought part of it. The defect this metric
# hunts is "nobody was asked", not "the answer was not the maximum".
EXPLAINS_GAP = {"enough", "speed_up", "stop_after_checkpoint", "skip_scope",
                "deepen_lod"}
# ...and what explains landing ABOVE the target: the owner asked for the
# deeper work, at the queue or at the gate-2 checkpoint.
EXPLAINS_OVERSHOOT_CHECKPOINTS = {"directions", "merge"}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# --------------------------------------------------------------------------
# the declarations
# --------------------------------------------------------------------------
def stage_levels():
    """{stage: depth it produces}. Stages that add no depth are absent, not
    zero — K3 verifies what exists and K0 has no artifact yet."""
    doc = read_json(STAGES) or {}
    out = {}
    for name, spec in (doc.get("stages") or {}).items():
        lod = spec.get("produces_lod")
        if isinstance(lod, int):
            out[name] = lod
    return out


def stage_order():
    doc = read_json(STAGES) or {}
    return list((doc.get("stages") or {}).keys())


def step_keys(frm, to):
    """The single ladder steps a jump crosses. 100→300 is 100→200 plus
    200→300: the same work, done in one go."""
    if frm >= to:
        return []
    rungs = [r for r in LADDER if frm <= r <= to]
    return ["%d->%d" % (a, b) for a, b in zip(rungs, rungs[1:])]


def price(frm, to, scope_kind="global"):
    """{eta_min, tokens, source, samples} for a jump, or None if the table
    does not declare one of the steps it crosses.

    A sum that crosses even one estimated step is an estimate. Reporting it
    as measured because three of its four terms were measured is exactly the
    silent upgrade `source` exists to prevent."""
    table = read_json(COST_TABLE) or {}
    steps = table.get("lod_steps") or {}
    keys = step_keys(frm, to)
    if not keys:
        return None
    eta, tokens, sources, samples = 0.0, 0, [], []
    for key in keys:
        row = (steps.get(key) or {}).get(scope_kind)
        if row is None:
            return None
        eta += row.get("eta_min") or 0
        tokens += row.get("tokens") or 0
        sources.append(row.get("source") or "estimate")
        if row.get("samples"):
            samples.append(row["samples"])
    measured = all(s == "measured" for s in sources)
    out = {"eta_min": round(eta, 1), "tokens": tokens,
           "source": "measured" if measured else "estimate",
           "steps": keys, "scope_kind": scope_kind}
    if measured and samples:
        out["samples"] = min(samples)
    return out


def price_note(frm, to, scope_kind="global"):
    """The owner-facing half of a transition. In the owner's language, because
    it is handed over verbatim."""
    p = price(frm, to, scope_kind)
    if not p:
        return None
    tail = ("замер: %d прогон(ов)" % p["samples"]) if p["source"] == "measured" \
        else "оценка"
    return "+%g мин / +%dk токенов (%s)" % (p["eta_min"],
                                            round(p["tokens"] / 1000.0), tail)


# --------------------------------------------------------------------------
# reading the contract
# --------------------------------------------------------------------------
def contract_path(root):
    return os.path.join(root, CONTRACT)


def contract_doc(root):
    """The parsed contract, or None. PyYAML absent is reported by the caller
    rather than swallowed [A.6] — a depth check that silently passes because
    it could not read anything is worse than one that says it could not run."""
    path = contract_path(root)
    if not os.path.isfile(path):
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, ValueError):
        return None


def target_lod(doc):
    meta = (doc or {}).get("meta") or {}
    value = meta.get("target_lod")
    return value if isinstance(value, int) and value in LADDER else DEFAULT_TARGET


def overrides(doc):
    meta = (doc or {}).get("meta") or {}
    got = meta.get("lod_overrides")
    return got if isinstance(got, list) else []


def closed_stages(root):
    """Stages that finished cleanly, in the order they finished. A failed
    stage measures the failure, not the work — same rule as the run plan's."""
    summary = dops_trace.summarize(root)
    if not summary:
        return []
    return [row["stage"] for row in (summary.get("stages") or [])
            if row.get("status") in (None, "ok")]


def current_lod(root):
    """The depth actually reached: the highest any closed stage produced.

    `max` is why ending the same stage twice cannot double-count — the
    idempotence is in the shape of the answer, not in a guard that has to be
    remembered."""
    levels = stage_levels()
    reached = [levels[s] for s in closed_stages(root) if s in levels]
    return max(reached) if reached else 0


def ladder_ends_after(root, stage):
    """Is there anything still ahead that would deepen the product?

    The run plan (У-6) is the authority when there is one: it names the
    stages this run will actually pass. Without a plan the declaration order
    in stages.json is the honest fallback, and it is a fallback, not a
    guess — the file declares the pipeline's own order."""
    levels = stage_levels()
    reached = current_lod(root)
    doc = contract_doc(root)
    plan = ((doc or {}).get("meta") or {}).get("run_plan")
    ahead = []
    if isinstance(plan, list) and plan:
        stages = [step.get("stage") for step in plan if isinstance(step, dict)]
        if stage in stages:
            last = len(stages) - 1 - stages[::-1].index(stage)
            ahead = stages[last + 1:]
    if not ahead:
        order = stage_order()
        if stage in order:
            ahead = order[order.index(stage) + 1:]
    return not any(levels.get(s, 0) > reached for s in ahead)


# --------------------------------------------------------------------------
# writing into a contract that has comments in it
# --------------------------------------------------------------------------
# The same reasoning as `dops_plan.patch_contract` and `dops_harvest.decide`:
# a load-and-dump deletes every comment, and the comments are where the
# reasoning lives. This pair is the generic form of what those two do for one
# key each; folding all three onto it is a refactor of its own, noted in the
# move report rather than smuggled in here.
def expand_flow(text, section):
    """`meta: {a: 1, b: 2}` cannot hold a nested list — expand exactly that one
    line into block style, key order preserved, rest of the file untouched."""
    m = re.search(r"^%s:[ \t]*\{(.*)\}[ \t]*$" % re.escape(section), text, re.M)
    if not m:
        return text
    pairs = [p.strip() for p in dops_plan.split_top(m.group(1)) if p.strip()]
    lines = ["%s:" % section] + ["  %s" % p for p in pairs]
    return text[:m.start()] + "\n".join(lines) + text[m.end():]


def section_span(text, section):
    m = re.search(r"^%s:[ \t]*$" % re.escape(section), text, re.M)
    if not m:
        return None, None
    start = m.end()
    end = len(text)
    for nxt in re.finditer(r"^\S", text[start:], re.M):
        end = start + nxt.start()
        break
    return start, end


def set_scalar(text, section, key, value):
    text = expand_flow(text, section)
    start, end = section_span(text, section)
    if start is None:
        return None
    body = text[start:end]
    line = "  %s: %s" % (key, value)
    existing = re.search(r"^[ ]{2}%s:.*$" % re.escape(key), body, re.M)
    if existing:
        body = body[:existing.start()] + line + body[existing.end():]
    else:
        body = body.rstrip("\n") + "\n" + line + "\n"
    return text[:start] + body + text[end:]


def set_list(text, section, key, rendered):
    """`rendered` is the whole block, already indented, including its key."""
    text = expand_flow(text, section)
    start, end = section_span(text, section)
    if start is None:
        return None
    body = text[start:end]
    existing = re.search(r"^[ ]{2}%s:.*?(?=^[ ]{0,2}\S|\Z)" % re.escape(key),
                         body, re.M | re.S)
    if existing:
        body = body[:existing.start()] + rendered + "\n" + body[existing.end():]
    else:
        body = body.rstrip("\n") + "\n" + rendered + "\n"
    return text[:start] + body + text[end:]


def render_overrides(rows):
    if not rows:
        return "  lod_overrides: []"
    lines = ["  lod_overrides:"]
    for r in rows:
        lines.append('    - {scope: "%s", target_lod: %d, status: %s}'
                     % (r["scope"], r["target_lod"], r.get("status", "requested")))
    return "\n".join(lines)


def write_contract(root, mutate):
    """Apply `mutate(text) -> text|None` to the contract. Returns (ok, why)."""
    path = contract_path(root)
    if not os.path.isfile(path):
        return False, "no contract at %s" % path
    with open(path, encoding="utf-8") as f:
        text = f.read()
    patched = mutate(text)
    if patched is None:
        return False, "could not find the section to patch in %s" % path
    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    return True, path


# --------------------------------------------------------------------------
# the deepening log
# --------------------------------------------------------------------------
def log_append(root, record):
    path = os.path.join(root, LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_events(root):
    path = os.path.join(root, LOG)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def open_deepening(root):
    """The most recent deepening that has not been closed by a fact."""
    events = log_events(root)
    closed = {e.get("ref") for e in events if e.get("event") == "done"}
    opened = [e for e in events
              if e.get("event") == "deepen" and e.get("id") not in closed]
    return opened[-1] if opened else None


# --------------------------------------------------------------------------
# what the stage boundary does
# --------------------------------------------------------------------------
def on_stage_end(root, stage):
    """Called by `dops stage end`. Returns a short note for the caller's line,
    or None when there was nothing to say.

    Two jobs, in this order: record the depth that was reached, and — only if
    the ladder has run out of stages that would climb further — publish the
    transition that lets the owner buy the rest."""
    if not os.path.isfile(contract_path(root)):
        return None            # no contract: no target to miss, nothing to write
    reached = current_lod(root)
    if not reached:
        return None
    ok, why = write_contract(root, lambda t: set_scalar(t, "status", "lod", reached))
    if not ok:
        return "status.lod not written: %s" % why

    doc = contract_doc(root)
    if doc is None:
        return "status.lod = %d (target unread: PyYAML absent)" % reached
    target = target_lod(doc)
    if reached >= target or not ladder_ends_after(root, stage):
        return None
    existing = dops_checkpoint.state(root).get("lod-transition")
    if existing and existing.get("status") == dops_checkpoint.PUBLISHED:
        return None            # already asked; asking twice is not asking better
    note = price_note(reached, target)
    if not note:
        return ("LOD %d < цель %d, но цена перехода не объявлена в cost-table — "
                "причал не опубликован: причал без цены есть статус-строка"
                % (reached, target))
    dops_checkpoint.publish(
        root, "lod-transition", "current build", False,
        "готов LOD-%d, цель — LOD-%d. Углубить? %s" % (reached, target, note))
    return None


# --------------------------------------------------------------------------
# what the control point does
# --------------------------------------------------------------------------
def apply_deepen(root, lod, scope):
    """[§2.4] The owner said yes. Record it, invalidate what it invalidates,
    and announce it with its price — a plan that changed is a plan that is
    announced."""
    if lod not in LADDER:
        return False, "deepen_lod needs {lod: 100|200|300|400}"
    doc = contract_doc(root)
    if doc is None and os.path.isfile(contract_path(root)):
        return False, "cannot read the contract (PyYAML absent) [A.6]"
    if doc is None:
        return False, "no contract to deepen"
    reached = current_lod(root)
    frm = reached or target_lod(doc)
    if lod <= frm:
        return False, ("already at LOD %d — deepening to %d would be a step "
                       "backwards, and the ladder only climbs" % (frm, lod))
    kind = "section" if scope else "global"
    p = price(frm, lod, kind)
    if not p:
        return False, ("cost-table declares no price for %d->%d (%s) — a "
                       "deepening without a price is a bill nobody agreed to"
                       % (frm, lod, kind))

    # 2. invalidation, honestly scoped
    manifest = dops_hash.load_manifest(root)
    if scope and not manifest.get("artifacts"):
        return False, ("hash-graph unavailable (no artifacts/hashes.json) — a "
                       "scoped deepening cannot be cheap without it; run "
                       "`dops hash record` during the run, or deepen globally "
                       "and pay for the full recompute")
    graph = dops_hash.load_graph()
    recompute = dops_hash.downstream(graph, "artifacts/visual/tokens.json")
    dropped = []
    for name in recompute:
        if manifest.get("artifacts", {}).pop(name, None) is not None:
            dropped.append(name)
    if dropped:
        dops_hash.save_manifest(root, manifest)

    # 1. record it where the rest of the depth lives
    if scope:
        rows = [dict(r) for r in overrides(doc) if r.get("scope") != scope]
        rows.append({"scope": scope, "target_lod": lod, "status": "requested"})
        ok, why = write_contract(
            root, lambda t: set_list(t, "meta", "lod_overrides",
                                     render_overrides(rows)))
    else:
        ok, why = write_contract(
            root, lambda t: set_scalar(t, "meta", "target_lod", lod))
    if not ok:
        return False, "the deepening was not recorded: %s" % why

    log_append(root, {"event": "deepen", "at": now(), "at_epoch": time.time(),
                      "id": "lod-%03d" % (len([e for e in log_events(root)
                                               if e.get("event") == "deepen"]) + 1),
                      "from": frm, "to": lod, "scope": scope or "global",
                      "scope_kind": kind, "steps": p["steps"],
                      "eta_min": p["eta_min"], "tokens": p["tokens"],
                      "source": p["source"],
                      "tokens_at": (dops_trace.tokens_read(root) or (None, 0))[0]})

    # 3. the announcement, in the moment. Not routed through `dops announce`:
    # that declares a MACHINE decision with a rollback, and this is the
    # owner's own decision being confirmed back to them.
    where = scope if scope else "весь продукт"
    scope_line = ("пересчёт только %s" % scope) if scope else "полный пересчёт ниже по графу"
    return True, ("принято: %s → LOD-%d, %s, %s (%s)"
                  % (where, lod, price_note(frm, lod, kind), scope_line,
                     ", ".join(dropped) if dropped else "нечего пересчитывать"))


def apply_enough(root):
    """[§2.2] The owner looked at the price and declined. The ladder closes,
    and the gap stops being a defect — it became a decision."""
    doc = contract_doc(root)
    reached = current_lod(root)
    target = target_lod(doc) if doc is not None else DEFAULT_TARGET
    log_append(root, {"event": "enough", "at": now(), "lod": reached,
                      "target": target})
    if reached < target:
        return True, ("ладдер закрыт на LOD-%d при цели %d — это решение "
                      "владельца, а не недоделка" % (reached, target))
    return True, "ладдер закрыт на LOD-%d" % reached


# --------------------------------------------------------------------------
# the metric
# --------------------------------------------------------------------------
def explanations(root):
    """Owner commands that account for a depth that differs from the target."""
    import dops_control
    applied = {c["command"] for c in dops_control.state(root).values()
               if c.get("status") == "applied"}
    # The depth log is this file's own record that a command was carried out,
    # and it is the authority: the control queue is one way in, but the
    # orchestrator may call `apply_deepen` at a control point directly, and an
    # answer the owner gave should not depend on which door it came through.
    for e in log_events(root):
        if e.get("event") == "enough":
            applied.add("enough")
        elif e.get("event") == "deepen":
            applied.add("deepen_lod")
    decided = {cid: (c.get("decision") or {}).get("action")
               for cid, c in dops_checkpoint.state(root).items()
               if c.get("status") == dops_checkpoint.ACTED}
    return applied, decided


def mismatch(root):
    """(kind, message) or (None, message). §2.5 — both directions."""
    doc = contract_doc(root)
    if doc is None:
        return None, ("no readable contract — nothing to check (PyYAML absent "
                      "or no contract at all)")
    reached = current_lod(root)
    if not reached:
        return None, "no stage has produced a depth yet — nothing to check"
    target = target_lod(doc)
    applied, decided = explanations(root)

    if reached < target:
        if applied & EXPLAINS_GAP:
            return None, ("LOD %d < цель %d, объяснено командой владельца: %s"
                          % (reached, target,
                             ", ".join(sorted(applied & EXPLAINS_GAP))))
        if decided.get("directions") == "defer":
            return None, ("LOD %d < цель %d, объяснено отложенным K2B "
                          "(directions: defer)" % (reached, target))
        return "gap", ("lod_mismatch: готов LOD-%d при цели LOD-%d, и ни одна "
                       "команда владельца этого не объясняет — недопоставка, о "
                       "которой его не спросили" % (reached, target))

    if reached > target:
        if "deepen_lod" in applied:
            return None, ("LOD %d > цель %d, объяснено командой deepen_lod"
                          % (reached, target))
        if set(decided) & EXPLAINS_OVERSHOOT_CHECKPOINTS:
            return None, ("LOD %d > цель %d, объяснено решением владельца на "
                          "причале %s" % (reached, target,
                                          ", ".join(sorted(set(decided) &
                                                    EXPLAINS_OVERSHOOT_CHECKPOINTS))))
        return "overshoot", ("lod_mismatch: достигнут LOD-%d при цели LOD-%d "
                             "без команды владельца — перерасход, а не "
                             "инициатива" % (reached, target))

    return None, "LOD %d = цель %d" % (reached, target)


def metrics(root):
    """The §5 numbers, for the delivery report and `dops report`."""
    kind, message = mismatch(root)
    events = log_events(root)
    offered = sum(1 for c in dops_checkpoint.events(root)
                  if c.get("event") == "publish" and c.get("id") == "lod-transition")
    accepted = sum(1 for e in events if e.get("event") == "deepen")
    return {
        "lod": current_lod(root),
        "lod_mismatch": kind,
        "lod_mismatch_note": message,
        "deepen_offered": offered,
        "deepen_accepted": accepted,
        "deepen_accept_rate": (round(100.0 * accepted / offered, 1)
                               if offered else None),
        "targets": {"lod_mismatch": "null",
                    "deepen_accept_rate": "low with a good default target; "
                                          "high means the default is set too shallow"},
    }


# --------------------------------------------------------------------------
# measuring, and retraining on the measurements
# --------------------------------------------------------------------------
def done(root):
    open_one = open_deepening(root)
    if not open_one:
        print("lod: no open deepening to close")
        return 1
    started = open_one.get("at_epoch") or time.time()
    fact_min = round(max(0.0, (time.time() - started) / 60.0), 2)
    before = open_one.get("tokens_at")
    after = (dops_trace.tokens_read(root) or (None, 0))[0]
    fact_tokens = (after - before) if (before is not None and after is not None) else None
    log_append(root, {"event": "done", "at": now(), "ref": open_one.get("id"),
                      "steps": open_one.get("steps"),
                      "scope_kind": open_one.get("scope_kind"),
                      "fact_min": fact_min, "fact_tokens": fact_tokens})

    # a scope override that was carried out says so where it lives, so the
    # open ones and the closed ones stay in one place [A.10] rather than in
    # the contract and the log respectively
    scope = open_one.get("scope")
    if scope and scope != "global":
        doc = contract_doc(root)
        if doc is not None:
            rows = [dict(r) for r in overrides(doc)]
            for r in rows:
                if r.get("scope") == scope:
                    r["status"] = "done"
            write_contract(root, lambda t: set_list(t, "meta", "lod_overrides",
                                                    render_overrides(rows)))
    print("lod: %s closed — %.2f min%s (estimate was %s min)"
          % (open_one.get("id"), fact_min,
             ", %d tokens" % fact_tokens if fact_tokens is not None
             else ", tokens not logged",
             open_one.get("eta_min")))
    return 0


def retrain(root, write, check_only):
    table = read_json(COST_TABLE)
    if not table:
        print("lod: cannot read %s" % COST_TABLE)
        return 2
    steps = table.get("lod_steps") or {}

    if check_only:
        bad = []
        for key, row in steps.items():
            for kind, entry in row.items():
                if entry.get("source") == "measured" \
                        and (entry.get("samples") or 0) < MIN_SAMPLES:
                    bad.append("%s/%s claims `measured` with %s sample(s)"
                               % (key, kind, entry.get("samples") or 0))
        if bad:
            for b in bad:
                print("cost-table FAIL: %s" % b)
            print("Only `dops lod retrain --write` may write a measured value; "
                  "a hand-edited one is an estimate wearing a fact's label.")
            return 1
        print("cost-table pass: every measured entry carries %d+ samples"
              % MIN_SAMPLES)
        return 0

    # one measurement can only train the single step it crossed: a fact about
    # a two-step jump says nothing about how the two halves split
    buckets = {}
    for e in log_events(root):
        if e.get("event") != "done" or not e.get("steps"):
            continue
        if len(e["steps"]) != 1:
            continue
        buckets.setdefault((e["steps"][0], e.get("scope_kind") or "global"),
                           []).append(e)

    changes = []
    for (key, kind), rows in sorted(buckets.items()):
        if len(rows) < MIN_SAMPLES or key not in steps or kind not in steps[key]:
            continue
        eta = dops_plan.median([r["fact_min"] for r in rows])
        toks = [r["fact_tokens"] for r in rows if r.get("fact_tokens") is not None]
        entry = dict(steps[key][kind])
        entry["eta_min"] = round(eta, 1)
        if len(toks) >= MIN_SAMPLES:
            entry["tokens"] = int(dops_plan.median(toks))
        entry["source"] = "measured"
        entry["samples"] = len(rows)
        changes.append((key, kind, steps[key][kind], entry))

    if not changes:
        print("lod: nothing to retrain — no step has %d single-step "
              "measurements yet" % MIN_SAMPLES)
        return 0
    for key, kind, was, now_ in changes:
        print("  %-10s %-8s %s min (%s) → %s min (measured, n=%d)"
              % (key, kind, was.get("eta_min"), was.get("source"),
                 now_["eta_min"], now_["samples"]))
    if not write:
        print("(add --write to record this into %s)" % COST_TABLE)
        return 0
    for key, kind, _was, now_ in changes:
        steps[key][kind] = now_
    with open(COST_TABLE, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("cost-table retrained → %s" % COST_TABLE)
    return 0


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def status_cmd(root, as_json):
    doc = contract_doc(root)
    reached = current_lod(root)
    target = target_lod(doc) if doc is not None else DEFAULT_TARGET
    rows = overrides(doc) if doc is not None else []
    kind, message = mismatch(root)
    if as_json:
        print(json.dumps({"lod": reached, "target_lod": target,
                          "lod_overrides": rows, "mismatch": kind,
                          "note": message,
                          "price_to_target": price(reached, target)
                          if reached < target else None},
                         ensure_ascii=False, indent=2))
        return 0
    print("lod %s / target %s%s"
          % (reached or "—", target,
             ("  — %s" % price_note(reached, target)) if reached < target
             and price_note(reached, target) else ""))
    for r in rows:
        print("  scope %-18s → LOD-%s  %s" % (r.get("scope"),
                                              r.get("target_lod"),
                                              r.get("status", "requested")))
    print("  %s" % message)
    return 0


def check_cmd(root):
    kind, message = mismatch(root)
    if kind:
        print("lod FAIL: %s" % message)
        return 1
    print("lod pass: %s" % message)
    return 0


# --------------------------------------------------------------------------
def self_test():
    import shutil
    import tempfile
    import dops_control

    problems = []
    levels = stage_levels()

    # The mechanism is only alive if a default run can actually reach a gap.
    # K3 declaring a depth would mean every verified run claims the top of the
    # ladder and `lod-transition` could never fire — the check is here so that
    # the assignment cannot drift back without CI noticing.
    if "K3" in levels:
        problems.append("K3 declares produces_lod — verification adds no depth, "
                        "and a K3 that claims one makes the gap unreachable")
    if levels.get("K1") != 100 or levels.get("K2A") != 200 or levels.get("K2B") != 300:
        problems.append("stage depths are not K1=100 / K2A=200 / K2B=300: %r" % levels)

    # price composition
    if step_keys(100, 300) != ["100->200", "200->300"]:
        problems.append("a two-step jump was not decomposed into its steps")
    p = price(200, 300, "global")
    if not p or p["source"] != "estimate":
        problems.append("a seeded price did not report itself as an estimate")
    if price(300, 200) is not None:
        problems.append("a downward 'deepening' was priced")

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))
        contract = os.path.join(tmp, CONTRACT)
        shutil.copy(os.path.join(os.path.dirname(HERE), "starters",
                                 "landing-event", "contract.yaml"), contract)

        # 3. `stage end` writes status.lod, and a repeat does not double-count
        dops_trace.append(tmp, {"stage": "K1", "kind": "start"})
        dops_trace.append(tmp, {"stage": "K1", "kind": "end", "status": "ok"})
        on_stage_end(tmp, "K1")
        doc = contract_doc(tmp)
        if ((doc or {}).get("status") or {}).get("lod") != 100:
            problems.append("K1 finishing did not write status.lod = 100")
        dops_trace.append(tmp, {"stage": "K1", "kind": "start"})
        dops_trace.append(tmp, {"stage": "K1", "kind": "end", "status": "ok"})
        on_stage_end(tmp, "K1")
        if current_lod(tmp) != 100:
            problems.append("ending the same stage twice moved the depth")
        if "mode: quick" not in open(contract, encoding="utf-8").read():
            problems.append("writing status.lod damaged the rest of the contract")

        # 4. the gap publishes a transition, and the price is IN the message.
        #    The run plan (У-6) is what says K2A is the last stage that climbs:
        #    on `starter_first` there is no K2B ahead, so the ladder ends here
        #    even though stages.json declares a deeper stage further down.
        if ladder_ends_after(tmp, "K1"):
            problems.append("without a plan the ladder closed at K1, though "
                            "stages.json declares deeper stages after it")
        dops_plan.quiet(dops_plan.emit, tmp, "starter_first", False, False, False)
        ok, _ = write_contract(tmp, lambda t: set_scalar(t, "meta", "target_lod", 300))
        if not ok:
            problems.append("target_lod could not be written")
        if not ladder_ends_after(tmp, "K2A"):
            problems.append("the run plan says K2A is the last stage that "
                            "climbs, and the ladder stayed open anyway")
        dops_trace.append(tmp, {"stage": "K2A", "kind": "start"})
        dops_trace.append(tmp, {"stage": "K2A", "kind": "end", "status": "ok"})
        on_stage_end(tmp, "K2A")
        cps = dops_checkpoint.state(tmp)
        cp = cps.get("lod-transition")
        if not cp:
            problems.append("a run ending below its target published no "
                            "lod-transition")
        else:
            published = [e for e in dops_checkpoint.events(tmp)
                         if e.get("event") == "publish" and e["id"] == "lod-transition"]
            note = (published[-1].get("note") or "") if published else ""
            if "мин" not in note or "токен" not in note:
                problems.append("the transition carried no price: %r" % note)
            on_stage_end(tmp, "K2A")
            again = [e for e in dops_checkpoint.events(tmp)
                     if e.get("event") == "publish" and e["id"] == "lod-transition"]
            if len(again) != 1:
                problems.append("the same transition was published twice")

        # 7a. the gap with nothing explaining it is a defect
        kind, _msg = mismatch(tmp)
        if kind != "gap":
            problems.append("a run stopping below target without a command was "
                            "not reported as lod_mismatch (%r)" % kind)

        # 6. `enough` closes the ladder and the gap stops being a defect
        apply_enough(tmp)
        kind, _msg = mismatch(tmp)
        if kind is not None:
            problems.append("`enough` did not close the ladder (%r)" % kind)

    # 5. a scoped deepening records the override, invalidates the visual chain
    #    and leaves the structure alone
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts", "visual"))
        shutil.copy(os.path.join(os.path.dirname(HERE), "starters",
                                 "landing-event", "contract.yaml"),
                    os.path.join(tmp, CONTRACT))
        dops_trace.append(tmp, {"stage": "K2A", "kind": "start"})
        dops_trace.append(tmp, {"stage": "K2A", "kind": "end", "status": "ok"})

        # 9. without a hash graph a scoped deepening is refused, not faked
        ok, why = apply_deepen(tmp, 300, "section:hero")
        if ok or "hash-graph unavailable" not in why:
            problems.append("a scoped deepening without hashes was not refused "
                            "[A.6]: %s" % why)
        ok, _why = apply_deepen(tmp, 300, None)
        if not ok:
            problems.append("a global deepening was refused when it should not "
                            "need the hash graph")

        # now with hashes, and back down to a scoped one
        for rel, body in (("skeleton.html", "<h1>x</h1>"),
                          ("artifacts/visual/tokens.json", "{}"),
                          ("artifacts/visual/tokens.css", ":root{}")):
            with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                f.write(body)
        manifest = dops_hash.load_manifest(tmp)
        dops_hash.record(tmp, dops_hash.load_graph(), manifest)
        dops_hash.save_manifest(tmp, manifest)
        write_contract(tmp, lambda t: set_scalar(t, "meta", "target_lod", 200))

        ok, message = apply_deepen(tmp, 300, "section:hero")
        if not ok:
            problems.append("a scoped deepening with hashes was refused: %s" % message)
        else:
            if "мин" not in message or "токен" not in message:
                problems.append("the deepening was announced without its price")
            rows = overrides(contract_doc(tmp))
            if not any(r.get("scope") == "section:hero" for r in rows):
                problems.append("the scope override was not recorded in the contract")
            after = dops_hash.load_manifest(tmp)["artifacts"]
            if "artifacts/visual/tokens.css" in after:
                problems.append("the scope's own chain was not invalidated")
            if "skeleton.html" not in after:
                problems.append("a deepening invalidated the structure — a "
                                "restyle never rebuilds structure [A.7]")

        # 8. a fact closes the deepening and feeds the table. Two were accepted
        #    above (a global one and a scoped one), so both must close — and
        #    then there must be nothing left to close.
        opened = len([e for e in log_events(tmp) if e.get("event") == "deepen"])
        for _ in range(opened):
            if done(tmp) != 0:
                problems.append("an open deepening could not be closed with a fact")
        facts = [e for e in log_events(tmp) if e.get("event") == "done"]
        if len(facts) != opened:
            problems.append("%d deepening(s) accepted, %d closed with a fact"
                            % (opened, len(facts)))
        if any(f.get("fact_min") is None for f in facts):
            problems.append("closing a deepening recorded no measured minutes")
        if done(tmp) != 1:
            problems.append("`done` closed a deepening that was not open")

        # a carried-out override says so where the open ones live, or the
        # contract keeps advertising work that already happened
        rows = overrides(contract_doc(tmp))
        hero = next((r for r in rows if r.get("scope") == "section:hero"), None)
        if not hero or hero.get("status") != "done":
            problems.append("a carried-out scope override still reads as "
                            "requested: %r" % (hero,))

        # Found by running the real thing, not by this file: after the owner
        # accepted a SCOPED deepening, the global depth is still below the
        # global target — and that is their answer, not a defect. The metric
        # hunts "nobody was asked", not "the answer was not the maximum".
        write_contract(tmp, lambda t: set_scalar(t, "meta", "target_lod", 300))
        kind, _msg = mismatch(tmp)
        if kind is not None:
            problems.append("an accepted scoped deepening was still reported "
                            "as under-delivery (%r)" % kind)

    # 7b. landing ABOVE the target with nothing explaining it is a defect too.
    #     Its own project: any applied depth command would explain it away,
    #     which is exactly what this case must not have.
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "artifacts"))
        shutil.copy(os.path.join(os.path.dirname(HERE), "starters",
                                 "landing-event", "contract.yaml"),
                    os.path.join(tmp, CONTRACT))
        write_contract(tmp, lambda t: set_scalar(t, "meta", "target_lod", 200))
        for stage in ("K2A", "K2B"):
            dops_trace.append(tmp, {"stage": stage, "kind": "start"})
            dops_trace.append(tmp, {"stage": stage, "kind": "end", "status": "ok"})
        kind, _msg = mismatch(tmp)
        if kind != "overshoot":
            problems.append("overshooting the target without a command was not "
                            "reported as a mismatch (%r)" % kind)
        dops_checkpoint.publish(tmp, "directions",
                                "artifacts/visual/contact-sheet.html", False, "")
        dops_checkpoint.decide(tmp, "directions", "choose", None, None, "owner", False)
        kind, _msg = mismatch(tmp)
        if kind is not None:
            problems.append("an owner decision at gate 2 did not explain the "
                            "deeper result (%r)" % kind)

    # the table's own rule: only a retrain may write `measured`
    if retrain(".", False, True) != 0:
        problems.append("the shipped cost-table has a hand-written measurement")

    if problems:
        for p in problems:
            print("self-test FAIL: dops-lod: %s" % p)
        return 1
    print("OK: dops-lod self-test (depth declared not measured, the gap "
          "reachable by construction, a transition always carries its price, "
          "scoped deepening refuses without hashes [A.6] and never rebuilds "
          "structure [A.7], mismatch in both directions)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dops lod")
    sub = ap.add_subparsers(dest="cmd")
    st = sub.add_parser("status", help="where the run is on the ladder")
    st.add_argument("--root", default=".")
    st.add_argument("--json", action="store_true")
    pr = sub.add_parser("price", help="what a jump costs")
    pr.add_argument("--from", dest="frm", type=int, required=True)
    pr.add_argument("--to", dest="to", type=int, required=True)
    pr.add_argument("--scope", default="global", choices=["global", "section"])
    ck = sub.add_parser("check", help="the lod_mismatch defect (§2.5)")
    ck.add_argument("--root", default=".")
    dn = sub.add_parser("done", help="close the open deepening with a measured fact")
    dn.add_argument("--root", default=".")
    rt = sub.add_parser("retrain", help="estimates become medians once there are 3")
    rt.add_argument("--root", default=".")
    rt.add_argument("--write", action="store_true")
    rt.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.cmd == "status":
        return status_cmd(os.path.abspath(args.root), args.json)
    if args.cmd == "price":
        p = price(args.frm, args.to, args.scope)
        if not p:
            print("lod: no price declared for %d->%d (%s)"
                  % (args.frm, args.to, args.scope))
            return 1
        print(json.dumps(p, ensure_ascii=False, indent=2))
        print(price_note(args.frm, args.to, args.scope))
        return 0
    if args.cmd == "check":
        return check_cmd(os.path.abspath(args.root))
    if args.cmd == "done":
        return done(os.path.abspath(args.root))
    if args.cmd == "retrain":
        return retrain(os.path.abspath(args.root), args.write, args.check)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
