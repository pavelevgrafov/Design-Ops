#!/usr/bin/env python3
"""contract-migrate.py — upgrade a design contract 5.1 -> 6.0 -> 7.0 (idempotent).

Adds new sections with defaults; never touches existing values; appends one
changelog entry per hop. Reads/writes artifacts/design-contract.yaml by
default. Chained: a 5.1 contract lands on 7.0 in one run.

Usage: python3 contract-migrate.py [contract_path]
Exit: 0 migrated (or already 7.0), 1 error, 2 file missing, 3 yaml error,
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

V7_DEFAULTS = {
    ("product", "job_hypothesis"): {"statement": "", "confidence": "",
                                    "source": ""},
    ("experience", "assumptions"): [],
    ("visual", "design_review"): "",
    ("knowledge", "sources_pin"): {"ux_wiki": {"tag": "", "sha256": ""},
                                   "design_ops": {"tag": ""}},
    # v7.2 — process control (У-2/У-3), overtaking (A.25), announcements (A.26).
    # Defaults keep an existing contract behaving exactly as before: gates stay
    # blocking, nothing is provisional, no depth target is claimed.
    ("meta", "autonomous_granted_by"): "",
    ("meta", "target_lod"): 200,
    ("meta", "lod_overrides"): [],
    ("meta", "run_plan"): [],
    ("meta", "paused"): False,
    ("meta", "pause_after"): "",
    ("gates", "provisional_since"): "",
    ("gates", "provisional_scope"): [],
    ("gates", "provisional_plateau"): "",
    ("status", "deliverable_blocked"): False,
    ("status", "lod"): 0,
    ("scope", "exclusions"): [],
    # AC-23: the quick-mode ceiling limits PRODUCTION, not inheritance. An
    # artifact that arrived from a Verified Starter cost this run zero turns,
    # and forbidding it would mean starter_first must throw away the most
    # valuable thing it carries. `origin` is what tells the two apart — absent
    # or `produced` still violates the ceiling.
    ("artifacts", "ux"): {"origin": "", "source_starter": ""},
    ("process",): {"checkpoints_log": "artifacts/checkpoints.jsonl",
                   "control_queue_log": "artifacts/control-queue.jsonl",
                   "announcements_log": "artifacts/announcements.jsonl"},
}

HOPS = [("5.1", "6.0", V6_DEFAULTS), ("6.0", "7.0", V7_DEFAULTS)]


def apply_defaults(c, defaults):
    added = []
    for keys, default in defaults.items():
        node = c
        for k in keys[:-1]:
            node = node.setdefault(k, {})
            if not isinstance(node, dict):
                node = {}
        if node.get(keys[-1]) is None:
            node[keys[-1]] = default
            added.append(".".join(keys))
    return added


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
    if ver == "7.0":
        print("OK: already 7.0, nothing to do")
        return 0

    hops_done = []
    for from_ver, to_ver, defaults in HOPS:
        if ver != from_ver:
            continue
        added = apply_defaults(c, defaults)
        meta["schema_version"] = to_ver
        now = datetime.datetime.now().isoformat(timespec="seconds")
        meta["updated_at"] = now
        c.setdefault("changelog", []).append({
            "at": now, "author": "agent",
            "field": "meta.schema_version", "from": from_ver, "to": to_ver,
            "reason": f"migration {from_ver} -> {to_ver} (sections added with defaults)",
        })
        hops_done.append(f"{from_ver}->{to_ver} ({len(added)} fields)")
        ver = to_ver

    if not hops_done:
        print(f"FAIL: unsupported schema_version '{meta.get('schema_version')}' "
              "(supported chain: 5.1 -> 6.0 -> 7.0)")
        return 5

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(c, f, allow_unicode=True, sort_keys=False)
    print(f"OK: migrated to 7.0 [{'; '.join(hops_done)}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
