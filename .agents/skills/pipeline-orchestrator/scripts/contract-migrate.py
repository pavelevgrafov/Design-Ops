#!/usr/bin/env python3
"""contract-migrate.py — upgrade a design contract 5.1 -> 6.0 (idempotent).

Adds v6 sections with defaults; never touches existing values; appends a
changelog entry. Reads/writes artifacts/design-contract.yaml by default.

Usage: python3 contract-migrate.py [contract_path]
Exit: 0 migrated (or already 6.0), 1 error, 2 file missing, 3 yaml error,
      4 pyyaml missing, 5 unsupported source version.
"""
import os, sys, datetime

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML required (pip install pyyaml)")
    sys.exit(4)

V6_DEFAULTS = {
    ("meta", "artifact_profile"): "",
    ("domain_model",): {},
    ("roles_permissions",): {},
    ("user_flows",): [],
    ("screen_modules",): [],
    ("state_matrix",): [],
    ("api_contract",): {},
    ("starters",): {"route": "", "chosen": "", "skin_diverged": False},
    ("visual", "base_skin"): "",
    ("gates", "mode"): "",
    ("gates", "gate2_deferred"): False,
    ("gates", "gate3"): "",
    ("gates", "delegated"): [],
    ("integrations",): [],
    ("deploy",): {"previews": [], "prod": {"confirmed_by": "", "at": "",
                                           "rollback_tested": False}},
    ("knowledge",): {"vault_path": "knowledge/", "index_kb": 0},
    ("cost",): {"estimate": "", "actual": ""},
    ("acceptance", "functional_paths_matrix"): [],
    ("status", "base_skin_applied"): False,
}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "artifacts", "design-contract.yaml")
    if not os.path.exists(path):
        print(f"FAIL: contract not found: {path}")
        return 2
    try:
        with open(path, encoding="utf-8") as f:
            c = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"FAIL: yaml error: {e}")
        return 3

    meta = c.setdefault("meta", {})
    ver = str(meta.get("schema_version"))
    if ver == "6.0":
        print("OK: already 6.0, nothing to do")
        return 0
    if ver != "5.1":
        print(f"FAIL: unsupported schema_version '{ver}' (migrate 5.0 -> 5.1 first)")
        return 5

    added = []
    for keys, default in V6_DEFAULTS.items():
        node = c
        for k in keys[:-1]:
            node = node.setdefault(k, {})
            if not isinstance(node, dict):
                node = {}
        if node.get(keys[-1]) is None:
            node[keys[-1]] = default
            added.append(".".join(keys))
    meta["schema_version"] = "6.0"

    now = datetime.datetime.now().isoformat(timespec="seconds")
    meta["updated_at"] = now
    c.setdefault("changelog", []).append({
        "at": now, "author": "agent",
        "field": "meta.schema_version", "from": "5.1", "to": "6.0",
        "reason": "migration 5.1 -> 6.0 (sections added with defaults)",
    })

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(c, f, allow_unicode=True, sort_keys=False)
    print(f"OK: migrated to 6.0 ({len(added)} sections/fields defaulted)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
