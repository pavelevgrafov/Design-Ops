#!/usr/bin/env python3
"""check-packs.py — D24: service-pack acceptance block of the quality report.

Reads integrations[] from the contract, resolves each pack through
pack-resolve.py, and prints one report line per pack. Exit non-zero when a
CORE pack is unavailable (caps the verdict); peripheral unavailability is a
line, never a cap.

Usage: python3 check-packs.py <contract.yaml> <packs_dir>
Exit: 0 = no core cap, 1 = core pack unavailable, 2 = usage/io error.
"""
import json, os, subprocess, sys

try:
    import yaml
except ImportError:
    print("check-packs: PyYAML required", file=sys.stderr)
    sys.exit(2)

def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    contract, packs_dir = sys.argv[1], sys.argv[2]
    resolver = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "pipeline-orchestrator", "scripts",
                            "pack-resolve.py")
    try:
        with open(contract, encoding="utf-8") as f:
            c = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"check-packs: cannot read contract: {e}", file=sys.stderr)
        return 2

    integrations = c.get("integrations") or []
    if not integrations:
        print("pass D24: no active packs declared (integrations[] empty)")
        return 0

    core_bad = 0
    for it in integrations:
        pack = (it or {}).get("pack")
        if not pack:
            continue
        r = subprocess.run(
            ["python3", resolver, packs_dir, pack, "--json"],
            capture_output=True, text=True)
        try:
            res = json.loads(r.stdout)
        except json.JSONDecodeError:
            res = {"status": "unavailable", "reason": "resolver error",
                   "class": (it or {}).get("class", "peripheral")}
        cls = res.get("class") or (it or {}).get("class", "peripheral")
        status = res.get("status", "unavailable")
        reason = res.get("reason", "")
        cap = ""
        if status != "active" and cls == "core":
            core_bad += 1
            cap = " — CAPS verdict at ready_with_caveats"
        print(f"{status} D24 {pack} (class={cls})"
              + (f" — {reason}" if reason else "") + cap)
    return 1 if core_bad else 0

if __name__ == "__main__":
    sys.exit(main())
