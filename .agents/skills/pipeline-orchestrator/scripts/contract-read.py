#!/usr/bin/env python3
"""contract-read.py — the ONLY supported way for shell scripts to read
design-contract.yaml (v5.2, fixes defect A2: sed/awk scraping swallowed the
`scenarios:` block and checked scenario IDs as screens).

Atomic queries print machine-readable values to stdout; shell callers use
capture-then-test. No sed/awk parsing of the contract anywhere else.

Usage:
  python3 contract-read.py <contract.yaml> <query> [arg]

Queries:
  key_screens        ids of experience.key_screens, one per line
  scenarios          ids of experience.scenarios, one per line
  functional_paths   acceptance.functional_paths as compact JSON
  mode               meta.mode (quick|standard|full)
  interaction_mode   meta.interaction_mode
  verdict            status.verdict
  schema_version     meta.schema_version
  get <dotted.path>  generic lookup, e.g. get acceptance.target_viewports

Exit codes: 0 = ok (empty stdout = key absent/empty); 1 = bad usage;
2 = contract file missing/unreadable; 3 = YAML parse error;
4 = PyYAML missing (install: pip install pyyaml).
"""
import json
import sys

try:
    import yaml
except ImportError:
    print("contract-read: PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(4)


def _ids(items):
    """Accept a list of dicts ({id: ...}) or plain strings; yield ids."""
    out = []
    for it in items or []:
        if isinstance(it, dict):
            v = it.get("id")
        else:
            v = it
        if v is not None and str(v) != "":
            out.append(str(v))
    return out


def _dig(c, dotted):
    cur = c
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1
    path, query = sys.argv[1], sys.argv[2]

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"contract-read: cannot read {path}: {e}", file=sys.stderr)
        return 2
    try:
        c = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        print(f"contract-read: YAML parse error in {path}: {e}", file=sys.stderr)
        return 3

    if query == "key_screens":
        print("\n".join(_ids((c.get("experience") or {}).get("key_screens"))))
    elif query == "scenarios":
        print("\n".join(_ids((c.get("experience") or {}).get("scenarios"))))
    elif query == "functional_paths":
        fp = (c.get("acceptance") or {}).get("functional_paths")
        if fp:
            print(json.dumps(fp, ensure_ascii=False))
    elif query == "mode":
        print((c.get("meta") or {}).get("mode") or "")
    elif query == "interaction_mode":
        print((c.get("meta") or {}).get("interaction_mode") or "")
    elif query == "verdict":
        print((c.get("status") or {}).get("verdict") or "")
    elif query == "schema_version":
        print((c.get("meta") or {}).get("schema_version") or "")
    elif query == "get":
        if len(sys.argv) < 4:
            print("contract-read: get requires a dotted path", file=sys.stderr)
            return 1
        v = _dig(c, sys.argv[3])
        if v is None:
            pass
        elif isinstance(v, (dict, list)):
            print(json.dumps(v, ensure_ascii=False))
        else:
            print(v)
    else:
        print(f"contract-read: unknown query '{query}'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
