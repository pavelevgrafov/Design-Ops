#!/usr/bin/env python3
"""check-divergence.py — D17: verify constructed divergence between directions.

Reads artifacts/design-contract.yaml (visual.directions) and enforces:
  - every direction has all 7 axes specified (non-empty);
  - every direction has a seed: persona + >=3 domains;
  - no domain appears in two directions' seeds;
  - every PAIR differs on >=3 axes, including composition or type_voice;
  - differs_by claims are consistent with declared axes;
  - 1..2 bold moves per direction.
Warnings (non-blocking):
  - all boldness_points coincide [K2.4.2];
  - standard/full mode with empty blind_test fields (CR-13 pending).

Usage: python3 check-divergence.py [path-to-design-contract.yaml]
       (default: artifacts/design-contract.yaml, fallback: design-contract.yaml)
Exit 0 = divergent, 1 = violations printed.
"""
import os, sys

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML required (pip install pyyaml)")
    sys.exit(1)

AXES = ["composition", "type_voice", "color", "surface", "shape", "imagery", "motion"]
KEY_AXES = {"composition", "type_voice"}

def norm(v):
    return " ".join(str(v or "").lower().split())

def find_contract(argv):
    if len(argv) > 1:
        return argv[1]
    for p in (os.path.join("artifacts", "design-contract.yaml"), "design-contract.yaml"):
        if os.path.exists(p):
            return p
    return os.path.join("artifacts", "design-contract.yaml")

def main():
    path = find_contract(sys.argv)
    try:
        with open(path, encoding="utf-8") as f:
            c = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"FAIL: contract not found: {path}")
        return 1
    except yaml.YAMLError as e:
        print(f"FAIL: YAML parse error: {e}")
        return 1

    c = c or {}
    mode = str(((c.get("meta") or {}).get("mode")) or "")
    directions = ((c.get("visual") or {}).get("directions")) or []
    problems, warnings = [], []

    if len(directions) < 2:
        problems.append(f"need >=2 directions, found {len(directions)}")

    by_id, seen_domains, bold_points = {}, {}, []
    for d in directions:
        did = d.get("id") or "<no-id>"
        if did in by_id:
            problems.append(f"duplicate direction id: {did}")
        by_id[did] = d

        axes = d.get("axes") or {}
        for a in AXES:
            if not norm(axes.get(a)):
                problems.append(f"direction {did}: axis '{a}' empty")

        seed = d.get("seed") or {}
        if not norm(seed.get("persona")):
            problems.append(f"direction {did}: seed.persona empty")
        domains = [norm(x) for x in (seed.get("domains") or []) if norm(x)]
        if len(domains) < 3:
            problems.append(f"direction {did}: need >=3 seed domains, found {len(domains)}")
        for dom in domains:
            if dom in seen_domains:
                problems.append(f"domain '{dom}' shared by {seen_domains[dom]} and {did} (fixation risk)")
            seen_domains[dom] = did

        bp = norm(seed.get("boldness_point"))
        if not bp:
            problems.append(f"direction {did}: seed.boldness_point empty (need safer|middle|bolder spread)")
        else:
            bold_points.append((did, bp))

        moves = d.get("bold_moves") or []
        if not (1 <= len(moves) <= 2):
            problems.append(f"direction {did}: bold_moves must be 1-2, found {len(moves)}")

        if not norm(d.get("concept")):
            problems.append(f"direction {did}: concept empty (blind-description test)")

        if mode in ("standard", "full") and not norm(d.get("blind_test")):
            warnings.append(f"direction {did}: blind_test empty (CR-13 external test pending, model_judged)")

    # Boldness spread [K2.4.2]
    if len(bold_points) >= 2 and len({bp for _, bp in bold_points}) == 1:
        warnings.append(f"all boldness_points coincide ('{bold_points[0][1]}') — "
                        f"spread across the band [K2.4.1]: safer/middle/bolder")

    ids = list(by_id.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a_id, b_id = ids[i], ids[j]
            A, B = by_id[a_id], by_id[b_id]
            ax_a, ax_b = A.get("axes") or {}, B.get("axes") or {}
            truly_diff = [ax for ax in AXES if norm(ax_a.get(ax)) and norm(ax_b.get(ax))
                          and norm(ax_a.get(ax)) != norm(ax_b.get(ax))]
            claimed = set((A.get("differs_by") or {}).get(b_id) or [])
            for ax in claimed:
                if ax not in truly_diff:
                    problems.append(f"{a_id}.differs_by.{b_id}: '{ax}' claimed but axes are identical or empty")
            if len(truly_diff) < 3:
                problems.append(f"pair {a_id}/{b_id}: only {len(truly_diff)} differing axes ({truly_diff}), need >=3")
            if not (KEY_AXES & set(truly_diff)):
                problems.append(f"pair {a_id}/{b_id}: neither composition nor type_voice differs "
                                f"— recolor detected, redesign one direction")

    for w in warnings:
        print(f"warning: {w}")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} divergence problem(s). Redesign axes, do not recolor.")
        return 1
    print(f"OK: {len(directions)} directions, all pairs differ on >=3 axes incl. composition/type_voice")
    return 0

if __name__ == "__main__":
    sys.exit(main())
