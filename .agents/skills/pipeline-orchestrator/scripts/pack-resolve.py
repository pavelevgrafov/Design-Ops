#!/usr/bin/env python3
"""pack-resolve.py — service-pack resolver for the v6 pack bus.

A pack is ACTIVE only if (a) every requires_env var is present in the
environment and (b) its acceptance command is green right now or was green
within the cache TTL. Otherwise the pack is `unavailable(reason)` and the
conveyor continues (honest degradation).

Verdict impact is the pack's `class`: core unavailable caps the verdict at
ready_with_caveats; peripheral unavailable is a report line only.

Usage:
  python3 pack-resolve.py <packs_dir> <pack_id> [--ttl-hours N] [--json]
  python3 pack-resolve.py <packs_dir> --all [--ttl-hours N] [--json]
Exit: 0 = every queried pack active; 1 = usage error or any pack
unavailable (status lines name the reason); 2 = PyYAML missing.
Packs whose id starts with "_" are fixtures and excluded from --all.
Cache: <packs_dir>/.pack-cache/<id>.json
"""
import json, os, subprocess, sys, time

try:
    import yaml
except ImportError:
    print("pack-resolve: PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

def load_manifest(packs_dir, pack_id):
    p = os.path.join(packs_dir, pack_id, "pack.yaml")
    if not os.path.exists(p):
        return None, f"manifest not found: {p}"
    try:
        with open(p, encoding="utf-8") as f:
            m = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return None, f"manifest yaml error: {e}"
    return m, None

def resolve(packs_dir, pack_id, ttl_hours):
    m, err = load_manifest(packs_dir, pack_id)
    if err:
        return {"pack": pack_id, "status": "unavailable", "reason": err}
    cls = m.get("class", "peripheral")
    out = {"pack": pack_id, "class": cls, "version": str(m.get("version", ""))}

    if m.get("disabled"):
        out.update(status="unavailable", reason="disabled in manifest")
        return out

    missing = [v for v in (m.get("requires_env") or []) if not os.environ.get(v)]
    if missing:
        out.update(status="unavailable",
                   reason=f"missing env: {', '.join(missing)}")
        return out

    cache = os.path.join(packs_dir, ".pack-cache", f"{pack_id}.json")
    ttl = ttl_hours * 3600
    if os.path.exists(cache) and (time.time() - os.path.getmtime(cache)) < ttl:
        try:
            with open(cache, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("acceptance") == "pass":
                out.update(status="active", acceptance="pass",
                           cached=True, verified_at=c.get("at"))
                return out
        except (json.JSONDecodeError, OSError):
            pass

    cmd = m.get("acceptance_test")
    if not cmd:
        out.update(status="unavailable", reason="no acceptance_test in manifest")
        return out
    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
    ok = r.returncode == 0
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"pack": pack_id, "acceptance": "pass" if ok else "fail",
                   "at": int(time.time())}, f)
    if ok:
        out.update(status="active", acceptance="pass", cached=False,
                   verified_at=int(time.time()))
    else:
        tail = (r.stderr or r.stdout).decode("utf-8", "replace").strip()[-200:]
        out.update(status="unavailable", acceptance="fail",
                   reason=f"acceptance failed: {tail}")
    return out

def main():
    args, opts = [], {}
    it = iter(sys.argv[1:])
    for a in it:
        if a.startswith("--"):
            if "=" in a:
                k, v = a.split("=", 1)
                opts[k] = v
            elif a == "--ttl-hours":
                opts[a] = next(it, None)
            else:
                opts[a] = True
        else:
            args.append(a)
    if len(args) < 1 or (len(args) < 2 and "--all" not in opts):
        print(__doc__, file=sys.stderr)
        return 1
    packs_dir = args[0]
    ttl = int(opts.get("--ttl-hours", 24))
    as_json = "--json" in opts

    if "--all" in opts:
        # convention: leading "_" = private/test fixture, never scheduled
        ids = sorted(d for d in os.listdir(packs_dir)
                     if os.path.isdir(os.path.join(packs_dir, d))
                     and not d.startswith(".") and not d.startswith("_"))
    else:
        ids = [args[1]]

    results = [resolve(packs_dir, i, ttl) for i in ids]
    if as_json:
        print(json.dumps(results if len(results) > 1 else results[0],
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            line = f"{r['status']} {r['pack']} (class={r.get('class')})"
            if r.get("reason"):
                line += f" — {r['reason']}"
            print(line)
    return 0 if all(r["status"] == "active" for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
