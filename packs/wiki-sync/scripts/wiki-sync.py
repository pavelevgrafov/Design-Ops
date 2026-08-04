#!/usr/bin/env python3
"""wiki-sync.py — knowledge provenance: pin, drift check, controlled update.

Implements the TRIZ resolution from the v7.0 meta-analysis (ТП-1):
knowledge must stay fresh AND reproducible — so it is FROZEN during work
and SYNCED at version boundaries, never fetched live at runtime.

Model:
- The project pins its knowledge source in the contract:
  knowledge.sources_pin.ux_wiki = {tag, sha256} where sha256 is the hash
  of the vendored constraints snapshot (.agents/knowledge-sync/constraints/).
- `--check`: verifies the vendored snapshot matches the pin (integrity),
  and reports drift when the wiki source moved ahead (needs --wiki-path
  pointing at a local ux-wiki clone; without it, drift = explicit
  `unavailable`, integrity still verified).
- `--update --wiki-path <clone> [--tag <tag>]`: re-vendors constraints,
  recomputes the hash, updates the pin + contract changelog. One command,
  recorded — no silent drift [A.10].

Usage:
  python3 wiki-sync.py --contract artifacts/design-contract.yaml --check [--wiki-path P]
  python3 wiki-sync.py --contract artifacts/design-contract.yaml --update --wiki-path P [--tag T]
  python3 wiki-sync.py --self-test
Exit: 0 ok, 1 drift/integrity failure, 2 usage/io.
"""
import argparse, datetime, hashlib, os, subprocess, sys

try:
    import yaml
except ImportError:
    print("wiki-sync: PyYAML required", file=sys.stderr)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VENDOR_DIR = os.path.join(".agents", "knowledge-sync", "constraints")
WIKI_CONSTRAINTS = "constraints"  # inside the ux-wiki clone


def sha_dir(path):
    h = hashlib.sha256()
    if not os.path.isdir(path):
        return None
    for dirpath, _d, files in sorted(os.walk(path)):
        for fn in sorted(files):
            if not fn.endswith(".yaml"):
                continue
            fp = os.path.join(dirpath, fn)
            h.update(os.path.relpath(fp, path).encode())
            with open(fp, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def load_contract(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"wiki-sync: cannot read contract: {e}", file=sys.stderr)
        sys.exit(2)


def git_rev(path, ref="HEAD"):
    try:
        r = subprocess.run(["git", "-C", path, "rev-parse", "--short", ref],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def cmd_check(contract_path, wiki_path):
    c = load_contract(contract_path)
    pin = ((c.get("knowledge") or {}).get("sources_pin") or {}).get("ux_wiki") or {}
    pinned_sha, pinned_tag = pin.get("sha256"), pin.get("tag")
    problems = []

    vendor = os.path.join(os.path.dirname(os.path.abspath(contract_path)), "..", VENDOR_DIR)
    vendor = os.path.normpath(vendor)
    actual_sha = sha_dir(vendor)
    if not pinned_sha:
        problems.append("no pin recorded (knowledge.sources_pin.ux_wiki.sha256 empty) "
                        "— run --update to establish provenance")
    elif actual_sha is None:
        problems.append(f"vendored constraints missing at {vendor} — run --update")
    elif actual_sha != pinned_sha:
        problems.append("vendored constraints diverge from the pin (silent drift!) "
                        "— run --update or restore the pinned snapshot [A.10]")
    else:
        print(f"integrity OK: vendored constraints match pin {pinned_sha[:12]}")

    if wiki_path:
        head = git_rev(wiki_path)
        if head is None:
            print("drift check: unavailable (not a git repo)")
        elif pinned_tag and head != pinned_tag and not head.startswith(str(pinned_tag)):
            print(f"drift: wiki HEAD is {head}, project pinned at {pinned_tag} "
                  f"— consider --update at the next version boundary")
        else:
            print(f"drift: none (wiki at pinned revision {head})")
    else:
        print("drift check: unavailable (no --wiki-path; offline mode, integrity only)")

    for p in problems:
        print(f"FAIL: {p}")
    return 1 if problems else 0


def cmd_update(contract_path, wiki_path, tag):
    if not wiki_path or not os.path.isdir(os.path.join(wiki_path, WIKI_CONSTRAINTS)):
        print("wiki-sync: --update needs --wiki-path pointing at a ux-wiki clone "
              f"(with {WIKI_CONSTRAINTS}/)", file=sys.stderr)
        return 2
    src = os.path.join(wiki_path, WIKI_CONSTRAINTS)
    rev = tag or git_rev(wiki_path) or "unknown"
    vendor = os.path.join(os.path.dirname(os.path.abspath(contract_path)), "..", VENDOR_DIR)
    vendor = os.path.normpath(vendor)
    os.makedirs(vendor, exist_ok=True)
    import shutil
    for fn in os.listdir(vendor):
        if fn.endswith(".yaml"):
            os.remove(os.path.join(vendor, fn))
    n = 0
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".yaml"):
            shutil.copy2(os.path.join(src, fn), os.path.join(vendor, fn))
            n += 1
    sha = sha_dir(vendor)

    c = load_contract(contract_path)
    know = c.setdefault("knowledge", {})
    pin = know.setdefault("sources_pin", {}).setdefault("ux_wiki", {})
    old = {"tag": pin.get("tag"), "sha256": pin.get("sha256")}
    pin["tag"], pin["sha256"] = rev, sha
    now = datetime.datetime.now().isoformat(timespec="seconds")
    c.setdefault("meta", {})["updated_at"] = now
    c.setdefault("changelog", []).append({
        "at": now, "author": "agent", "field": "knowledge.sources_pin.ux_wiki",
        "from": f"{old['tag']}:{str(old['sha256'])[:12]}",
        "to": f"{rev}:{sha[:12]}",
        "reason": f"wiki-sync update: re-vendored {n} constraints files",
    })
    with open(contract_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(c, f, allow_unicode=True, sort_keys=False)
    print(f"OK: vendored {n} constraints files, pin -> {rev}:{sha[:12]} (changelog recorded)")
    return 0


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # fake wiki clone
        wiki = os.path.join(td, "ux-wiki")
        os.makedirs(os.path.join(wiki, WIKI_CONSTRAINTS))
        with open(os.path.join(wiki, WIKI_CONSTRAINTS, "a11y.yaml"), "w") as f:
            f.write("contrast:\n  text-normal-aa: {value: 4.5}\n")
        # fake project
        proj = os.path.join(td, "proj")
        os.makedirs(os.path.join(proj, "artifacts"))
        contract = os.path.join(proj, "artifacts", "design-contract.yaml")
        with open(contract, "w") as f:
            yaml.safe_dump({"meta": {"schema_version": "7.0"},
                            "knowledge": {"sources_pin": {"ux_wiki": {"tag": "", "sha256": ""}}}}, f)
        # 1. check without pin -> fail
        if cmd_check(contract, None) == 0:
            print("self-test FAIL: unpinned project passed check")
            return 1
        # 2. update -> ok
        if cmd_update(contract, wiki, "v1-test") != 0:
            print("self-test FAIL: update failed")
            return 1
        # 3. check -> ok
        if cmd_check(contract, None) != 0:
            print("self-test FAIL: pinned project failed check")
            return 1
        # 4. tamper the vendored file -> integrity fail
        vendor = os.path.join(proj, VENDOR_DIR)
        with open(os.path.join(vendor, "a11y.yaml"), "a") as f:
            f.write("# tampered\n")
        if cmd_check(contract, None) == 0:
            print("self-test FAIL: tampered snapshot not detected")
            return 1
        # 5. changelog recorded
        c = load_contract(contract)
        if not any("sources_pin" in str(e.get("field")) for e in c.get("changelog", [])):
            print("self-test FAIL: no changelog entry for update")
            return 1
    print("OK: wiki-sync self-test (pin -> check -> tamper-detect cycle)")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", default=os.path.join("artifacts", "design-contract.yaml"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--wiki-path", default=None)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    if args.update:
        return cmd_update(args.contract, args.wiki_path, args.tag)
    return cmd_check(args.contract, args.wiki_path)


if __name__ == "__main__":
    sys.exit(main())
