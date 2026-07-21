#!/usr/bin/env python3
"""render-sitemap.py — Gate 1 approvable artifact from the contract (v6.0, TZ-5).

Reads experience.key_screens + experience.scenarios from design-contract.yaml
and emits:
  artifacts/skeleton/sitemap.mmd   — Mermaid flowchart (for mermaid-aware tools)
  artifacts/skeleton/sitemap.html  — self-contained approval sheet: one card per
                                     screen (id, purpose, priority), grouped by
                                     scenario flow. No external deps, no CDN.

Deterministic cross-check (fails the run, exit 1):
  - every key_screen id appears in the diagram;
  - every scenario step references an existing key_screen id;
  - every key_screen has a non-empty purpose.

Usage: python3 render-sitemap.py <contract.yaml> [--out-dir artifacts/skeleton]
Exit: 0 ok, 1 contract/diagram mismatch, 2 usage.
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = "artifacts/skeleton"
    if "--out-dir" in sys.argv:
        i = sys.argv.index("--out-dir")
        out_dir = sys.argv[i + 1]
    if not args:
        print("usage: render-sitemap.py <contract.yaml> [--out-dir DIR]",
              file=sys.stderr)
        return 2
    with open(args[0], encoding="utf-8") as f:
        c = yaml.safe_load(f)
    exp = c.get("experience") or {}
    screens = exp.get("key_screens") or []
    scenarios = exp.get("scenarios") or []
    if not screens:
        print("fail: experience.key_screens is empty", file=sys.stderr)
        return 1

    problems = []
    ids = []
    for s in screens:
        sid = (s or {}).get("id")
        if not sid:
            problems.append("a key_screen without id")
            continue
        ids.append(sid)
        if not (s.get("purpose") or "").strip():
            problems.append(f"{sid}: empty purpose")
    prio_of = {s.get("id"): (s.get("priority") or "") for s in screens if s.get("id")}
    title_of = {s.get("id"): (s.get("name") or s.get("id")) for s in screens if s.get("id")}

    # Flows come from experience.scenarios (site) and top-level user_flows
    # (app). A scenario with an explicit `screens: [ids]` list is strictly
    # validated (deterministic id cross-check); free-form `steps` render as-is.
    flows = []  # (flow_id, [step labels], strict_seq)
    for sc in list(scenarios) + list(c.get("user_flows") or []):
        scid = (sc or {}).get("id", "flow")
        explicit = sc.get("screens")
        steps = explicit or sc.get("steps") or []
        if isinstance(steps, str):
            steps = [x.strip() for x in re.split(r"->|→", steps) if x.strip()]
        seq, labels = [], []
        for st in steps:
            st = str(st).strip()
            labels.append(title_of.get(st, st))
            if explicit:
                if st not in ids:
                    problems.append(f"{scid}: step '{st}' is not a key_screen id")
                else:
                    seq.append(st)
            elif st in ids:
                seq.append(st)
        flows.append((scid, labels, seq))

    if problems:
        for p in problems:
            print(f"fail {p}")
        return 1

    # --- Mermaid ---------------------------------------------------------
    mmd = ["flowchart LR"]
    for _scid, _labels, seq in flows:
        for a, b in zip(seq, seq[1:]):
            mmd.append(f"  {a} --> {b}")
    for sid in ids:  # declare all (unlinked screens still appear)
        label = sid.replace('"', "'")
        mmd.append(f'  {sid}["{label}"]')
    mmd_src = "\n".join(mmd) + "\n"

    # --- HTML approval sheet ----------------------------------------------
    cards = []
    for s in screens:
        sid = s.get("id")
        cards.append(
            f'<div class="card" data-screen="{esc(sid}">'
            f'<div class="sid">{esc(title_of.get(sid, sid))} <span class="idtag">{esc(sid)}</span></div>'
            f'<div class="purpose">{esc(s.get("purpose"))}</div>'
            f'<div class="prio">{esc(prio_of.get(sid) or "—")}</div>'
            f"</div>")
    flow_html = []
    for scid, labels, _seq in flows:
        flow_html.append(
            f'<div class="flow"><span class="fname">{esc(scid)}</span> '
            + " <span class='arrow'>→</span> ".join(f"<b>{esc(x)}</b>" for x in labels)
            + "</div>")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Sitemap — Gate 1 artifact</title>
<style>
body{{font:14px/1.5 system-ui,sans-serif;background:#f5f5f4;color:#1c1917;margin:2rem}}
h1{{font-size:1.1rem}} .flows{{margin:1rem 0 2rem}}
.flow{{padding:.4rem .6rem;background:#fff;border:1px solid #d6d3d1;border-radius:.4rem;margin:.3rem 0}}
.fname{{color:#78716c;margin-right:.5rem}} .arrow{{color:#a8a29e;padding:0 .3rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:.8rem}}
.card{{background:#fff;border:1px solid #d6d3d1;border-radius:.5rem;padding:.8rem}}
.sid{{font-weight:600}} .purpose{{color:#44403c;min-height:2.5em}}
.prio{{color:#78716c;font-size:.8rem;margin-top:.4rem}}
.idtag{{color:#a8a29e;font-weight:400;font-size:.75rem}}
.note{{color:#78716c;font-size:.85rem;margin-top:2rem}}
</style></head><body>
<h1>Sitemap — structure approval (Gate 1)</h1>
<div class="flows">{''.join(flow_html)}</div>
<div class="grid">{''.join(cards)}</div>
<p class="note">Generated by render-sitemap.py from design-contract.yaml —
{len(ids)} screen(s), {len(flows)} flow(s). Visual design is not evaluated here.</p>
</body></html>
"""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "sitemap.mmd"), "w", encoding="utf-8") as f:
        f.write(mmd_src)
    with open(os.path.join(out_dir, "sitemap.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"OK: sitemap.mmd + sitemap.html — {len(ids)} screen(s), "
          f"{len(flows)} flow(s) -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
