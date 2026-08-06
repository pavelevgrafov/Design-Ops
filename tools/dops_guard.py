#!/usr/bin/env python3
"""dops_guard.py — pre-edit sentinels for verified rules (A.22, A.24).

The guard runs ONLY the checks that are local and cheap, blocking the edit
before it becomes a floor defect.  This is the "sentinel" move: the model
never learns the rule, it learns that the edit is refused.

Usage:
  python3 dops_guard.py <file> [...]          # guard specific files
  python3 dops_guard.py --diff                # guard files from git diff
  python3 dops_guard.py --staged              # guard git staged files
  python3 dops_guard.py --since <ref>         # guard files changed since ref
  python3 dops_guard.py --self-test

Exit: 0 pass, 1 blocked (edit would violate a verified rule), 2 usage.
"""
import os, re, subprocess, sys

# Map rule -> (checker_script, file_extensions, strict_always)
# strict_always=True means the guard always blocks; False would allow warnings.
SENTINELS = [
    {
        "rule": "A.22",
        "check": "packs/copy-linter/scripts/lint-copy.py",
        "exts": {".html", ".md", ".txt"},
        "label": "corporate-slop",
    },
    {
        "rule": "A.24",
        "check": "packs/ai-look-detector/scripts/scan.py",
        "exts": {".css", ".html", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"},
        "label": "AI-look",
    },
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", ROOT] + list(args),
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError:
        return ""


def files_from_diff():
    out = _git("diff", "--name-only", "HEAD")
    return [os.path.join(ROOT, p) for p in out.strip().split("\n") if p]


def files_from_staged():
    out = _git("diff", "--cached", "--name-only")
    return [os.path.join(ROOT, p) for p in out.strip().split("\n") if p]


def files_since(ref):
    out = _git("diff", "--name-only", ref, "HEAD")
    return [os.path.join(ROOT, p) for p in out.strip().split("\n") if p]


def _relevant(sentinel, paths):
    """Return the subset of paths this sentinel cares about."""
    exts = sentinel["exts"]
    return [p for p in paths if os.path.splitext(p)[1] in exts]


def _run(checker, paths):
    """Run a checker with --strict on the given paths.  Return (rc, stdout)."""
    cmd = [sys.executable, os.path.join(ROOT, checker), "--strict"] + paths
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output


def guard(paths):
    """Run all sentinels over the relevant subset of paths.

    Returns a list of violation dicts.
    """
    violations = []
    for s in SENTINELS:
        relevant = _relevant(s, paths)
        if not relevant:
            continue
        rc, out = _run(s["check"], relevant)
        if rc != 0:
            violations.append({
                "rule": s["rule"],
                "label": s["label"],
                "files": relevant,
                "output": out.strip(),
            })
    return violations


def self_test():
    import tempfile
    td = tempfile.mkdtemp()
    # A.22 trap
    slop = os.path.join(td, "slop.md")
    with open(slop, "w") as f:
        f.write("Unlock your potential with our seamless platform.")
    # A.24 trap
    tail = os.path.join(td, "tail.css")
    with open(tail, "w") as f:
        f.write(".x{color:#6366f1}")
    # Clean file
    clean = os.path.join(td, "clean.html")
    with open(clean, "w") as f:
        f.write("<p>Pricing starts at 12 dollars.</p>")

    # 1. Both traps caught
    v = guard([slop, tail, clean])
    if len(v) != 2:
        print(f"self-test FAIL: expected 2 violations, got {len(v)}")
        return 1
    rules = {x["rule"] for x in v}
    if rules != {"A.22", "A.24"}:
        print(f"self-test FAIL: expected A.22+A.24, got {rules}")
        return 1

    # 2. Clean file alone passes
    v = guard([clean])
    if v:
        print(f"self-test FAIL: clean file flagged: {v}")
        return 1

    # 3. Empty path list passes
    v = guard([])
    if v:
        print(f"self-test FAIL: empty guard flagged: {v}")
        return 1

    print("OK: dops_guard self-test (traps caught, clean passes, empty passes)")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()

    paths = []
    if "--diff" in sys.argv:
        paths = files_from_diff()
    elif "--staged" in sys.argv:
        paths = files_from_staged()
    elif "--since" in sys.argv:
        idx = sys.argv.index("--since")
        if idx + 1 >= len(sys.argv):
            print("Usage: --since <git-ref>", file=sys.stderr)
            return 2
        paths = files_since(sys.argv[idx + 1])
    else:
        paths = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not paths:
        print(__doc__, file=sys.stderr)
        return 2

    # Only check files that exist
    paths = [p for p in paths if os.path.exists(p)]

    violations = guard(paths)
    if violations:
        print("GUARD BLOCKED: verified-rule violations detected on changed files.")
        print("The model is not told these rules; the edit is refused instead.\n")
        for v in violations:
            print(f"--- {v['rule']} ({v['label']}) ---")
            print(v["output"])
            print()
        return 1

    # Report what was checked, even on green.
    checked = set()
    for s in SENTINELS:
        checked.update(_relevant(s, paths))
    print(f"OK: guard clear ({len(checked)} file(s) checked, 0 violations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
