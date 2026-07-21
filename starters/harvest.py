#!/usr/bin/env python3
"""harvest.py — turn a finished project into a starter candidate (the flywheel).

Requires the owner's explicit permission flag in the project contract
(`starters.harvest_allowed: true`). Strips injected content back to slots,
runs the static floor, and writes starters/_candidates/<id>/ for review —
a candidate never becomes active without a human promote + recheck.

Usage: python3 harvest.py <project_root> <new_starter_id>
Exit: 0 candidate written, 1 usage, 2 no permission flag, 3 floor red.
"""
import json, os, re, shutil, subprocess, sys, datetime

try:
    import yaml
except ImportError:
    print("harvest: PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)

def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    project, new_id = sys.argv[1], sys.argv[2]

    cpath = os.path.join(project, "artifacts", "design-contract.yaml")
    contract = {}
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as f:
            contract = yaml.safe_load(f) or {}
    if not (contract.get("starters") or {}).get("harvest_allowed"):
        print("FAIL: starters.harvest_allowed is not true in the project "
              "contract — explicit owner permission required")
        return 2

    out = os.path.join(ROOT, "_candidates", new_id)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    src = os.path.join(project, "src")
    skel_src = src if os.path.isdir(src) else project
    shutil.copytree(skel_src, os.path.join(out, "skeleton"),
                    ignore=shutil.ignore_patterns(
                        "node_modules", ".git", "dist", "build", "*.png",
                        "*.jpg", "*.jpeg", "*.webp", ".pack-cache"))

    # strip content back to slots: replace text of elements carrying
    # data-slot with the slot default marker
    skel = os.path.join(out, "skeleton")
    n = 0
    for dirpath, _, files in os.walk(skel):
        for fn in files:
            if not fn.endswith((".html", ".tsx", ".jsx")):
                continue
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8") as f:
                t = f.read()
            t2 = re.sub(r'(data-slot="[^"]+"[^>]*>)[^<]+', r"\1", t)
            if t2 != t:
                n += 1
                with open(p, "w", encoding="utf-8") as f:
                    f.write(t2)

    qg = os.path.join(REPO, ".agents", "skills", "quality-guardian", "scripts")
    vd = os.path.join(REPO, ".agents", "skills", "visual-director", "scripts")
    for script in (os.path.join(qg, "check-placeholders.sh"),
                   os.path.join(qg, "check-token-usage.sh"),
                   os.path.join(vd, "lint-ban-list.sh")):
        r = subprocess.run(["bash", script, skel], capture_output=True)
        if r.returncode != 0:
            print(f"FAIL: static floor red: {os.path.basename(script)}")
            print(r.stdout.decode()[-500:])
            return 3

    today = datetime.date.today().isoformat()
    with open(os.path.join(out, "starter.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump({
            "id": new_id,
            "profile": (contract.get("meta") or {}).get("artifact_profile") or "site",
            "category": (contract.get("product") or {}).get("category") or "",
            "pattern": (contract.get("content_model") or {}).get("pattern") or "",
            "description": "harvested candidate — review before promoting",
            "verified_at": today,
            "floor_verdict": "candidate (static floor green; full floor on review)",
        }, f, allow_unicode=True, sort_keys=False)
    print(f"OK: candidate at starters/_candidates/{new_id} "
          f"({n} files stripped to slots); review + recheck to promote")
    return 0

if __name__ == "__main__":
    sys.exit(main())
