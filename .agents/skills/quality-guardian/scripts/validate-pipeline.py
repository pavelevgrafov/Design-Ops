#!/usr/bin/env python3
"""validate-pipeline.py — D19: gate/order integrity + report<->contract consistency.

Checks (from artifacts/design-contract.yaml + artifacts/audit/quality-report.md
+ artifacts/decision-log.md + the artifact tree):
  1. Contract is schema v5.1 with required keys (v5.0 → migration error).
  2. Gate order: gate1 passed BEFORE visual work; gate2 result BEFORE scaled
     (A.1/A.2 — via changelog timestamps).
  3. Quick-mode ceiling (AC-23): only whitelisted artifacts exist.
  4. Verdicts: ready-family only; report verdict == contract verdict;
     not_ready never lowered without a fix+retest entry [A.8].
  5. Every model_judged claim in the report carries 'provisional'.
  6. Autonomous gate2 honesty: 'passed' requires human chosen/merged.
  7. Decision-log mandatory sections (AC-25) + conditional sections.
  8. Realized == confirmed: final_direction non-empty when gate2 passed;
     gate2_result ids exist in directions.
  9. Distinctive assets appear beyond a single screen; all_local truthful.

Usage: python3 validate-pipeline.py [project_root]
Exit 0 = integrity ok, 1 = violations.
"""
import os, re, sys

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML required (pip install pyyaml)")
    sys.exit(1)

G1_OK = {"passed", "autonomous_passed"}
G2_OK = {"passed", "provisional_ai", "regenerated"}
VERDICTS = {"ready", "ready_with_caveats", "not_ready"}
OLD_VERDICTS = {"pass", "conditional_pass", "fail"}
QUICK_FORBIDDEN = [
    os.path.join("artifacts", "brief.md"),
    os.path.join("artifacts", "ux"),
    os.path.join("artifacts", "visual", "style-calibration.md"),
    os.path.join("artifacts", "visual", "asset-manifest.yaml"),
    # legacy v5.0 root locations
    "brief.md", "ux", "style-calibration.md", "asset-manifest.yaml",
]
LOG_REQUIRED = ["## Classification", "## Clarification", "## Gate 1",
                "## Taste calibration", "## Direction seeds", "## Gate 2", "## Verdict"]

def find(root, *candidates):
    for rel in candidates:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            return p
    return None

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems, warnings = [], []

    cpath = find(root, os.path.join("artifacts", "design-contract.yaml"), "design-contract.yaml")
    if not cpath:
        print("FAIL: design-contract.yaml not found (artifacts/ or root)")
        return 1
    if "artifacts" not in cpath:
        warnings.append("contract at root (v5.0 layout) — migrate to artifacts/design-contract.yaml")
    with open(cpath, encoding="utf-8") as f:
        c = yaml.safe_load(f) or {}

    meta = c.get("meta") or {}
    ver = str(meta.get("schema_version"))
    if ver == "5.0":
        problems.append("contract is schema 5.0 — run the 5.1 migration first "
                        "(move to artifacts/, schema_version 5.1, verdict mapping)")
    elif ver != "5.1":
        problems.append(f"meta.schema_version is '{ver}', expected '5.1'")
    for key in ("product", "experience", "content_model", "visual", "gates", "status", "acceptance"):
        if key not in c:
            problems.append(f"missing contract section: {key}")

    gates = c.get("gates") or {}
    status = c.get("status") or {}
    visual = c.get("visual") or {}
    assets = c.get("assets") or {}
    changelog = c.get("changelog") or []

    # --- 2. gate order via changelog ------------------------------------------
    def first_time(pred):
        for e in changelog:
            if pred(e or {}):
                return str((e or {}).get("at", ""))
        return None

    g1_pass = first_time(lambda e: e.get("field") == "gates.gate1" and e.get("to") in G1_OK)
    visual_start = first_time(lambda e: str(e.get("field", "")).startswith("visual.directions"))
    scaled_t = first_time(lambda e: e.get("field") == "status.scaled" and e.get("to") is True)
    g2_t = first_time(lambda e: e.get("field") in ("gates.gate2", "visual.gate2_result"))

    if status.get("skeleton_approved") and gates.get("gate1") not in G1_OK:
        problems.append(f"skeleton_approved=true but gates.gate1='{gates.get('gate1')}'")
    if visual_start and g1_pass and visual_start < g1_pass:
        problems.append(f"A.1 violated: visual work at {visual_start} before gate1 passed at {g1_pass}")
    if visual_start and not g1_pass:
        problems.append("A.1 suspect: visual work recorded but no gate1 pass in changelog")
    if status.get("scaled") and gates.get("gate2") not in G2_OK:
        problems.append(f"A.2 violated: scaled=true but gates.gate2='{gates.get('gate2')}'")
    if scaled_t and g2_t and scaled_t < g2_t:
        problems.append(f"A.2 violated: scaled at {scaled_t} before gate2 result at {g2_t}")

    # --- 4. verdicts ------------------------------------------------------------
    verdict = str(status.get("verdict") or "")
    if verdict in OLD_VERDICTS:
        problems.append(f"old verdict '{verdict}' — 5.1 uses ready|ready_with_caveats|not_ready "
                        f"(pass→ready, conditional_pass→ready_with_caveats, fail→not_ready)")
    elif verdict and verdict not in VERDICTS:
        problems.append(f"unknown verdict '{verdict}'")

    # not_ready never lowered without fix+retest [A.8]
    if verdict in ("ready", "ready_with_caveats"):
        last_nr = -1
        for i, e in enumerate(changelog):
            if (e or {}).get("field") == "status.verdict" and (e or {}).get("to") == "not_ready":
                last_nr = i
        if last_nr >= 0:
            fixed = any(
                (re.search(r"fix|retest|qa_cycles", str((e or {}).get("field", "")), re.I)
                 or re.search(r"fix|retest", str((e or {}).get("reason", "")), re.I))
                for e in changelog[last_nr + 1:])
            if not fixed:
                problems.append("verdict lowered from not_ready without a fix+retest changelog entry [A.8]")

    # --- 5/6. report consistency -------------------------------------------------
    rpath = find(root, os.path.join("artifacts", "audit", "quality-report.md"), "quality-report.md")
    if rpath:
        with open(rpath, encoding="utf-8") as f:
            report = f.read()
        m = re.search(r"## Verdict:\s*(\w+)", report)
        if m:
            rv = m.group(1).strip()
            if rv in OLD_VERDICTS:
                problems.append(f"report uses old verdict '{rv}' — migrate to ready-family")
            elif verdict and rv != verdict:
                problems.append(f"verdict mismatch: report='{rv}' contract='{verdict}'")
        elif verdict:
            problems.append("quality-report.md has no '## Verdict:' line")
        for line in report.splitlines():
            if "model_judged" in line and "provisional" not in line:
                problems.append(f"model_judged without provisional: {line.strip()[:100]}")
    elif verdict:
        problems.append("contract has a verdict but quality-report.md is missing")

    g2res = str(visual.get("gate2_result") or "")
    if gates.get("gate2") == "provisional_ai" and not g2res.startswith("provisional_ai"):
        problems.append("gates.gate2=provisional_ai but gate2_result lacks provisional_ai marking")
    if (meta.get("interaction_mode") == "autonomous" and gates.get("gate2") == "passed"
            and not g2res.startswith(("chosen", "merged"))):
        problems.append("autonomous mode: gate2 'passed' requires human chosen/merged (else provisional_ai)")

    # --- 3. quick ceiling ----------------------------------------------------------
    mode = meta.get("mode")
    if mode == "quick":
        for rel in QUICK_FORBIDDEN:
            if os.path.exists(os.path.join(root, rel)):
                problems.append(f"quick-mode ceiling violated: forbidden artifact exists: {rel}")
        if len(visual.get("directions") or []) > 2:
            problems.append(f"quick mode: {len(visual['directions'])} directions (max 2)")
    elif mode not in ("standard", "full"):
        problems.append(f"meta.mode '{mode}' not in quick|standard|full")

    # --- 7. decision log (AC-25) -----------------------------------------------------
    lpath = find(root, os.path.join("artifacts", "decision-log.md"), "decision-log.md")
    if lpath:
        with open(lpath, encoding="utf-8") as f:
            log = f.read()
        for marker in LOG_REQUIRED:
            if marker not in log:
                problems.append(f"decision-log missing mandatory section: '{marker}'")
        if g2res.startswith("regenerated") and "## Regenerations" not in log:
            problems.append("gate2 regenerated but no '## Regenerations' with a failure hypothesis")
        if (visual.get("post_scale") or {}).get("used", 0) and "## Regenerations" not in log:
            problems.append("post_scale budget used but no hypothesis recorded in '## Regenerations'")
        if verdict == "ready_with_caveats" and "## Accepted limitations" not in log:
            problems.append("ready_with_caveats but no '## Accepted limitations' (risk owner required)")
    else:
        if verdict:
            problems.append("decision-log.md missing (mandatory in all modes, AC-25)")

    # --- 8. realized == confirmed -----------------------------------------------------
    if gates.get("gate2") in ("passed", "provisional_ai"):
        if not visual.get("final_direction"):
            problems.append("gate2 passed but visual.final_direction is empty (realized != confirmed)")
        ids = {d.get("id") for d in (visual.get("directions") or [])}
        m = re.search(r"\(([A-Za-z])", g2res)
        if m and ids and m.group(1) not in ids:
            problems.append(f"gate2_result references unknown direction '{m.group(1)}'")

    # --- 9. assets truthfulness ---------------------------------------------------------
    slots = assets.get("slots") or []
    distinctive = [s for s in slots if (s or {}).get("role") == "distinctive"]
    if visual.get("distinctive_assets") and distinctive:
        screens = {str((s or {}).get("screen", "")) for s in distinctive}
        if len(screens) == 1:
            problems.append(f"distinctive assets only on one screen ({screens}) — must appear beyond the hero")
    if assets.get("all_local"):
        for s in slots:
            fpath = (s or {}).get("file") or ""
            if not fpath:
                problems.append(f"all_local=true but slot '{(s or {}).get('id','?')}' has no file")
                continue
            if not (os.path.exists(os.path.join(root, fpath)) or
                    os.path.exists(os.path.join(root, "artifacts", fpath))):
                problems.append(f"all_local=true but file missing: {fpath}")

    for w in warnings:
        print(f"warning: {w}")
    for p in problems:
        print(f"FAIL: {p}")
    if problems:
        print(f"\n{len(problems)} integrity problem(s)")
        return 1
    print("OK: pipeline integrity verified (D19: gates order, ceiling, verdicts, decision log, consistency)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
