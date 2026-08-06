#!/usr/bin/env python3
"""dops_verify.py — the single entry point of the deterministic floor.

Replaces ~25 separate script invocations (one agent turn each) with ONE
command that returns ONE JSON. The agent reads the FAILURES, not the
registry: the canonical prose registry
(.agents/skills/quality-guardian/references/deterministic-floor.md) stays
documentation for humans.

Usage:
  python3 tools/dops_verify.py [--root DIR] [--profile quick|standard|full]
                               [--url URL] [--routes /,/pricing]
                               [--build-cmd "npm run build"]
                               [--json] [--audit-registry] [--self-test]

Exit codes: 0 = verdict ready | ready_with_caveats, 1 = not_ready,
2 = usage / registry error.

Design notes:
- stdlib only (PyYAML is optional and may be missing — see `dops doctor`);
- fs checks run in parallel, browser checks run sequentially in their own
  lane (one browser at a time);
- a missing capability is an explicit `unavailable` status with a reason,
  never a silent pass [A.6];
- statuses come from the closed taxonomy [A.11]: pass / fail / skip /
  unavailable / warn.
"""
import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
REGISTRY = os.path.join(HERE, "floor-registry.json")

STATUS_PASS, STATUS_FAIL = "pass", "fail"
STATUS_SKIP, STATUS_UNAVAIL, STATUS_WARN = "skip", "unavailable", "warn"


# ---------------------------------------------------------------- capabilities
def detect_capabilities(root, url, build_cmd):
    """What this environment can actually do. Honest, cached once per run."""
    caps = {}
    caps["python3"] = True
    try:
        import yaml  # noqa: F401
        caps["pyyaml"] = True
    except ImportError:
        caps["pyyaml"] = False
    caps["node"] = shutil.which("node") is not None
    caps["curl"] = shutil.which("curl") is not None
    caps["url"] = bool(url)
    caps["build_cmd"] = bool(build_cmd)

    # playwright may live in the project OR in the vendored toolkit — a project
    # that installs the package does not automatically npm-install it too.
    # Resolve once, then hand the absolute path to every browser check.
    caps["playwright"] = False
    caps["_playwright_path"] = ""
    if caps["node"]:
        for where in (root, PKG_ROOT):
            probe = subprocess.run(
                ["node", "-e", "console.log(require.resolve('playwright'))"],
                cwd=where, capture_output=True, text=True)
            if probe.returncode == 0:
                caps["playwright"] = True
                caps["_playwright_path"] = probe.stdout.strip()
                break
    return caps


# ------------------------------------------------------------- contract facts
def _contract_scalar(text, section, key):
    """Minimal single-level lookup: `section:` block, two-space `key:`.

    Deliberately tiny — used only for routing decisions (which checks apply).
    Anything that must be authoritative goes through contract-read.py.
    """
    m = re.search(r"^%s:\s*$" % re.escape(section), text, re.M)
    if not m:
        return None
    tail = text[m.end():]
    stop = re.search(r"^\S", tail, re.M)
    block = tail[:stop.start()] if stop else tail
    km = re.search(r"^\s{2}%s:\s*(.+?)\s*$" % re.escape(key), block, re.M)
    if not km:
        return None
    return km.group(1).strip().strip('"').strip("'")


def read_contract_facts(contract_path):
    facts = {"mode": "standard", "profile": "site",
             "gate2": "deferred", "base_skin_applied": False}
    if not os.path.isfile(contract_path):
        return facts
    with open(contract_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    facts["mode"] = _contract_scalar(text, "meta", "mode") or facts["mode"]
    facts["profile"] = (_contract_scalar(text, "meta", "artifact_profile")
                        or facts["profile"])
    facts["gate2"] = _contract_scalar(text, "gates", "gate2") or facts["gate2"]
    facts["base_skin_applied"] = (
        _contract_scalar(text, "status", "base_skin_applied") == "true")
    return facts


# ------------------------------------------------------------------ resolving
def first_existing(root, candidates):
    for rel in candidates:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            return p
    return None


def build_context(args, facts, caps):
    root = args.root
    ctx = {
        "root": root,
        "python": sys.executable or "python3",
        "tools": HERE,
        "skills": os.path.join(PKG_ROOT, ".agents", "skills"),
        "packs": os.path.join(PKG_ROOT, "packs"),
        "contract": os.path.join(root, "artifacts", "design-contract.yaml"),
        "mode": facts["mode"],
        "url": args.url or "",
        "routes": args.routes,
        "routes_space": args.routes.replace(",", " "),
        "shots": os.path.join(root, "artifacts", "audit", "screenshots"),
        "shots_baseline": os.path.join(root, "artifacts", "audit", "shots"),
        "paths_json": args.paths_json or "",
        "build_cmd": args.build_cmd or "",
        "assets": os.path.join(root, "assets"),
    }
    ctx["tokens_css"] = first_existing(root, [
        "artifacts/visual/tokens.css", "assets/tokens.css", "tokens.css"]) or ""
    ctx["tokens_json"] = first_existing(root, [
        "artifacts/visual/tokens.json", "assets/tokens.json",
        "tokens.json"]) or ""
    # D.41 compares both emitted files; the tailwind bridge sits beside the CSS
    ctx["tokens_theme_css"] = (
        os.path.join(os.path.dirname(ctx["tokens_css"]), "tokens.theme.css")
        if ctx["tokens_css"] else "")
    ctx["experience_model"] = first_existing(root, [
        "artifacts/ux/experience-model.yaml"]) or ""
    ctx["src"] = root
    return ctx


def resolve(token, ctx):
    def sub(m):
        key = m.group(1)
        if key not in ctx:
            raise KeyError("unknown placeholder {%s}" % key)
        return str(ctx[key])
    return re.sub(r"\{([a-z_]+)\}", sub, token)


# ------------------------------------------------------------------ execution
def applicable(check, profile_groups, caps, ctx, facts):
    """Return (run: bool, status, reason) without executing anything."""
    if check["group"] not in profile_groups:
        return False, STATUS_SKIP, "not in profile"

    if check.get("skip_when") == "k2b_not_run" and facts["gate2"] == "deferred":
        return False, STATUS_SKIP, "K2B deferred — no directions to compare"

    for need in check.get("needs", []):
        if need in caps and not caps[need]:
            return False, STATUS_UNAVAIL, "%s not available" % need
        if need in ctx and not ctx[need]:
            return False, STATUS_UNAVAIL, "%s not produced yet" % need
    return True, None, None


def run_check(check, ctx, timeout, env_extra=None):
    started = time.time()
    env = dict(os.environ)
    if env_extra:
        env.update({k: v for k, v in env_extra.items() if v})
    try:
        cmd = [resolve(part, ctx) for part in check["cmd"]]
    except KeyError as exc:
        return dict(status=STATUS_UNAVAIL, exit_code=None, duration_ms=0,
                    output="registry error: %s" % exc)
    try:
        if check.get("shell"):
            proc = subprocess.run(" ".join(cmd), shell=True, cwd=ctx["root"],
                                  capture_output=True, text=True,
                                  timeout=timeout, env=env)
        else:
            proc = subprocess.run(cmd, cwd=ctx["root"], capture_output=True,
                                  text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return dict(status=STATUS_UNAVAIL, exit_code=None,
                    duration_ms=int((time.time() - started) * 1000),
                    output="timeout after %ss" % timeout)
    except (OSError, ValueError) as exc:
        return dict(status=STATUS_UNAVAIL, exit_code=None,
                    duration_ms=int((time.time() - started) * 1000),
                    output="cannot execute: %s" % exc)

    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode == 0:
        status = STATUS_WARN if not check.get("blocking") and "warn" in out.lower() \
            else STATUS_PASS
    elif proc.returncode == 2 or re.search(r"^unavailable\b", out, re.M | re.I):
        status = STATUS_UNAVAIL
    else:
        status = STATUS_FAIL if check.get("blocking") or check.get("cap_only") \
            else STATUS_WARN
    return dict(status=status, exit_code=proc.returncode,
                duration_ms=int((time.time() - started) * 1000), output=out)


# The first output line is often a `pass[...]` of a sub-check; the reason must
# name what actually went wrong, or the summary misleads.
REASON_RE = re.compile(r"^(?:FAIL|BAN\[|WARN|unavailable|OVER)\b.*$", re.M | re.I)


def pick_reason(output):
    if not output:
        return ""
    if "Traceback (most recent call last)" in output:
        # a crashed check is a defect of the check — surface the exception,
        # not the first frame
        lines = [l for l in output.splitlines() if l.strip()]
        return "crashed: " + lines[-1].strip()
    m = REASON_RE.search(output)
    return (m.group(0) if m else output.splitlines()[0]).strip()


# -------------------------------------------------------------------- verdict
def compute_verdict(results):
    blockers, caps_reasons = [], []
    for r in results:
        if r["blocking"] and r["status"] == STATUS_FAIL:
            blockers.append("%s failed" % r["id"])
        elif r["blocking"] and r["status"] == STATUS_UNAVAIL:
            caps_reasons.append("%s unavailable (%s)" % (r["id"], r["reason"]))
        elif r.get("cap_only") and r["status"] in (STATUS_FAIL, STATUS_UNAVAIL):
            caps_reasons.append("%s %s" % (r["id"], r["status"]))
        elif r["status"] == STATUS_WARN:
            caps_reasons.append("%s advisory findings" % r["id"])
    if blockers:
        return "not_ready", blockers
    if caps_reasons:
        return "ready_with_caveats", caps_reasons
    return "ready", []


# ---------------------------------------------------------------------- audit
def audit_registry(registry):
    """Every registry id must appear in the canonical prose floor, and vice
    versa. Drift between the executable registry and its documentation is a
    defect — this is the mechanical guard against it."""
    doc = os.path.join(PKG_ROOT, ".agents", "skills", "quality-guardian",
                       "references", "deterministic-floor.md")
    if not os.path.isfile(doc):
        print("audit: canonical floor doc not found at %s" % doc)
        return 2
    with open(doc, encoding="utf-8") as f:
        text = f.read()
    documented = set(re.findall(r"\bD\.?\d{1,2}\b", text))
    covered = set()
    for check in registry["checks"]:
        covered.update(check.get("covers") or [check["id"]])
    missing = sorted(documented - covered - {"D2", "D26"})
    extra = sorted(covered - documented)
    ok = True
    if extra:
        print("audit FAIL: in registry but not documented: %s" % ", ".join(extra))
        ok = False
    if missing:
        print("audit: documented but not executed here: %s" % ", ".join(missing))
    print("audit: %d checks, %d D-ids covered" % (len(registry["checks"]), len(covered)))
    return 0 if ok else 1


def self_test():
    """Acceptance probe wired into eval/selftest/run-self-test.sh."""
    with open(REGISTRY, encoding="utf-8") as f:
        registry = json.load(f)
    problems = []
    ids = [c["id"] for c in registry["checks"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate check ids")
    for check in registry["checks"]:
        for key in ("id", "title", "group", "lane", "cmd"):
            if key not in check:
                problems.append("%s: missing %s" % (check.get("id"), key))
        if check.get("group") not in ("core", "browser", "tier1", "tier2"):
            problems.append("%s: unknown group" % check["id"])
        if check.get("lane") not in ("fs", "browser"):
            problems.append("%s: unknown lane" % check["id"])
    for prof, groups in registry["profiles"].items():
        if "core" not in groups:
            problems.append("profile %s drops the core group [E.4]" % prof)
    # verdict logic must not upgrade a blocker
    v, _ = compute_verdict([
        dict(id="D3", blocking=True, status=STATUS_FAIL, reason=""),
        dict(id="D9", blocking=True, status=STATUS_PASS, reason=""),
    ])
    if v != "not_ready":
        problems.append("verdict: an open blocker did not produce not_ready")
    v, _ = compute_verdict([
        dict(id="D3", blocking=True, status=STATUS_UNAVAIL, reason="no tool")])
    if v != "ready_with_caveats":
        problems.append("verdict: blocking unavailable did not cap the verdict")
    v, _ = compute_verdict([
        dict(id="D3", blocking=True, status=STATUS_PASS, reason="")])
    if v != "ready":
        problems.append("verdict: an all-green floor did not produce ready")
    if problems:
        for p in problems:
            print("self-test FAIL: dops-verify: %s" % p)
        return 1
    print("OK: dops-verify self-test (registry shape, profile floors, verdict rules)")
    return 0


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--profile", default=None,
                    choices=["quick", "standard", "full"])
    ap.add_argument("--url", default=None)
    ap.add_argument("--routes", default="/")
    ap.add_argument("--paths-json", dest="paths_json", default=None)
    ap.add_argument("--build-cmd", dest="build_cmd", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--audit-registry", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        with open(REGISTRY, encoding="utf-8") as f:
            registry = json.load(f)
    except (OSError, ValueError) as exc:
        print("dops verify: cannot read registry: %s" % exc)
        return 2

    if args.audit_registry:
        return audit_registry(registry)

    args.root = os.path.abspath(args.root)
    contract = os.path.join(args.root, "artifacts", "design-contract.yaml")
    facts = read_contract_facts(contract)
    profile = args.profile or facts["mode"]
    if profile not in registry["profiles"]:
        profile = "standard"
    groups = registry["profiles"][profile]

    caps = detect_capabilities(args.root, args.url, args.build_cmd)
    ctx = build_context(args, facts, caps)
    out_path = args.out or os.path.join(args.root, "artifacts", "audit",
                                        "floor.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    started = time.time()
    planned, results = [], []
    for check in registry["checks"]:
        run, status, reason = applicable(check, groups, caps, ctx, facts)
        base = dict(id=check["id"], title=check["title"],
                    group=check["group"], lane=check["lane"],
                    blocking=bool(check.get("blocking")),
                    cap_only=bool(check.get("cap_only")),
                    covers=check.get("covers") or [check["id"]],
                    executor="script",
                    fix_hint=check.get("fix_hint", ""))
        if not run:
            base.update(status=status, reason=reason, duration_ms=0,
                        exit_code=None, output="")
            results.append(base)
        else:
            planned.append((check, base))

    fs_jobs = [(c, b) for c, b in planned if c["lane"] == "fs"]
    br_jobs = [(c, b) for c, b in planned if c["lane"] == "browser"]
    workers = args.jobs or min(8, (os.cpu_count() or 4))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        env_extra = {"DOPS_PLAYWRIGHT": caps.get("_playwright_path", "")}
        futures = {pool.submit(run_check, c, ctx, args.timeout, env_extra): b
                   for c, b in fs_jobs}
        for check, base in br_jobs:          # browser lane: strictly serial
            outcome = run_check(check, ctx, args.timeout, env_extra)
            base.update(outcome, reason=pick_reason(outcome["output"]))
            results.append(base)
        for fut in concurrent.futures.as_completed(futures):
            base = futures[fut]
            outcome = fut.result()
            base.update(outcome, reason=pick_reason(outcome["output"]))
            results.append(base)

    order = {c["id"]: i for i, c in enumerate(registry["checks"])}
    results.sort(key=lambda r: order.get(r["id"], 99))
    verdict, reasons = compute_verdict(results)

    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    report = {
        "schema": "dops-floor/1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": args.root,
        "profile": profile,
        "contract_facts": facts,
        "capabilities": {k: v for k, v in caps.items()
                         if not k.startswith("_")},
        "duration_ms": int((time.time() - started) * 1000),
        "verdict": verdict,
        "verdict_reasons": reasons,
        "summary": summary,
        "checks": [{k: v for k, v in r.items() if k != "output"}
                   for r in results],
        "failures": [
            {"id": r["id"], "title": r["title"], "status": r["status"],
             "blocking": r["blocking"], "fix_hint": r["fix_hint"],
             "output": r["output"][-4000:]}
            for r in results if r["status"] in (STATUS_FAIL, STATUS_WARN)
            or (r["status"] == STATUS_UNAVAIL and r["blocking"])],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("floor %s | profile %s | %d checks in %.1fs"
              % (verdict.upper(), profile, len(results),
                 report["duration_ms"] / 1000.0))
        counts = " ".join("%s=%d" % (k, v) for k, v in sorted(summary.items()))
        print("  " + counts)
        for r in results:
            if r["status"] in (STATUS_PASS, STATUS_SKIP):
                continue
            print("  %-9s %-22s %s" % (r["status"], r["id"], r["reason"][:90]))
        label = "blocker" if verdict == "not_ready" else "cap"
        for reason in reasons:
            print("  %s: %s" % (label, reason))
        print("  full report: %s" % out_path)
    return 1 if verdict == "not_ready" else 0


if __name__ == "__main__":
    sys.exit(main())
