#!/usr/bin/env python3
"""dops_doctor.py — environment bootstrap check (P0).

Every capability the floor needs, checked once, reported as a table. Without
this the pipeline discovers missing tooling check by check, degrades every
run to ready_with_caveats, and burns agent turns on honest-but-avoidable
`unavailable` bookkeeping.

Usage:
  python3 tools/dops_doctor.py [--root DIR] [--json] [--fix]

`--fix` INSTALLS things (pip install pyyaml; npm i -D playwright axe-core;
npx playwright install chromium). It is never implied — the default run only
reports and prints the commands.

Exit: 0 all core capabilities present, 1 something core missing, 2 usage.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

CORE = "core"
OPTIONAL = "optional"


def probe(cmd, cwd=None, timeout=60):
    """Detection is quick; installs are not. `npm i -D playwright` alone runs
    past a minute on a cold cache, and reporting that as "failed" sends the
    user chasing a problem that does not exist."""
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


INSTALL_TIMEOUT = 900


def check_all(root):
    items = []

    items.append(dict(
        id="python3", klass=CORE, ok=sys.version_info >= (3, 8),
        detail="%d.%d.%d" % sys.version_info[:3],
        fix="install Python 3.8+"))

    try:
        import yaml
        ok, detail = True, getattr(yaml, "__version__", "installed")
    except ImportError:
        ok, detail = False, "missing"
    items.append(dict(id="pyyaml", klass=CORE, ok=ok, detail=detail,
                      fix="python3 -m pip install pyyaml"))

    node = shutil.which("node")
    ver = probe(["node", "--version"]) if node else None
    items.append(dict(id="node", klass=CORE, ok=bool(node),
                      detail=(ver.stdout.strip() if ver else "missing"),
                      fix="install Node.js 18+"))

    pw = probe(["node", "-e", "console.log(require('playwright/package.json').version)"],
               cwd=root) if node else None
    pw_ok = bool(pw and pw.returncode == 0)
    items.append(dict(id="playwright", klass=CORE, ok=pw_ok,
                      detail=(pw.stdout.strip() if pw_ok else "not resolvable"),
                      fix="npm i -D playwright && npx playwright install chromium"))

    chromium_ok = False
    if pw_ok:
        c = probe(["node", "-e",
                   "const{chromium}=require('playwright');"
                   "console.log(require('fs').existsSync(chromium.executablePath()))"],
                  cwd=root)
        chromium_ok = bool(c and "true" in (c.stdout or "").lower())
    items.append(dict(id="chromium", klass=CORE, ok=chromium_ok,
                      detail="installed" if chromium_ok else "browser binary missing",
                      fix="npx playwright install chromium"))

    axe = probe(["node", "-e", "require.resolve('axe-core')"], cwd=root) if node else None
    items.append(dict(id="axe-core", klass=CORE,
                      ok=bool(axe and axe.returncode == 0),
                      detail="installed" if axe and axe.returncode == 0 else "missing",
                      fix="npm i -D axe-core"))

    for tool, klass in (("curl", OPTIONAL), ("git", OPTIONAL)):
        items.append(dict(id=tool, klass=klass, ok=shutil.which(tool) is not None,
                          detail=shutil.which(tool) or "missing",
                          fix="install %s" % tool))
    return items


FIXES = [
    ("playwright", ["npm", "i", "-D", "playwright"]),
    ("axe-core", ["npm", "i", "-D", "axe-core"]),
    ("chromium", ["npx", "playwright", "install", "chromium"]),
]

VENV = ".venv"


def venv_python(root):
    p = os.path.join(root, VENV, "bin", "python")
    return p if os.path.isfile(p) else None


def fix_pyyaml(root):
    """Modern macOS/Homebrew Pythons are externally managed (PEP 668): a plain
    `pip install` is refused, and forcing it with --break-system-packages is
    exactly what the name says. Put the dependency in a project venv instead —
    `dops` prefers `.venv/bin/python` when it exists."""
    proc = probe([sys.executable, "-m", "pip", "install", "pyyaml"], cwd=root,
                 timeout=INSTALL_TIMEOUT)
    if proc is not None and proc.returncode == 0:
        print("  ok (system interpreter)")
        return 0
    managed = proc is not None and "externally-managed" in (proc.stderr or "")
    if managed:
        print("  system interpreter is externally managed (PEP 668) — "
              "creating a project venv instead of forcing it")
    vp = venv_python(root)
    if not vp:
        mk = probe([sys.executable, "-m", "venv", os.path.join(root, VENV)],
                   cwd=root)
        if mk is None or mk.returncode != 0:
            print("  failed to create %s/%s" % (root, VENV))
            return 1
        vp = venv_python(root)
    inst = probe([vp, "-m", "pip", "install", "--quiet", "pyyaml"], cwd=root,
                 timeout=INSTALL_TIMEOUT)
    if inst is None or inst.returncode != 0:
        print("  venv created but pyyaml install failed")
        return 1
    print("  ok (%s/%s) — `dops` will use this interpreter automatically" % (root, VENV))
    return 0


def apply_fixes(items, root):
    missing = {i["id"] for i in items if not i["ok"]}
    rc = 0
    if "pyyaml" in missing:
        print("→ pyyaml")
        rc |= fix_pyyaml(root)
    for key, cmd in FIXES:
        if key not in missing:
            continue
        print("→ %s" % " ".join(cmd))
        proc = probe(cmd, cwd=root, timeout=INSTALL_TIMEOUT)
        if proc is None or proc.returncode != 0:
            print("  failed%s" % (": " + proc.stderr.strip()[:200] if proc else ""))
            rc = 1
        else:
            print("  ok")
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    items = check_all(root)
    if args.fix:
        apply_fixes(items, root)
        items = check_all(root)

    core_missing = [i for i in items if i["klass"] == CORE and not i["ok"]]

    if args.json:
        print(json.dumps({"root": root, "capabilities": items,
                          "core_missing": [i["id"] for i in core_missing]},
                         ensure_ascii=False, indent=2))
    else:
        print("dops doctor — %s" % root)
        for i in items:
            print("  %-4s %-11s %-8s %s"
                  % ("ok" if i["ok"] else "MISS", i["id"], i["klass"], i["detail"]))
        if core_missing:
            print("\ncore capabilities missing — the floor will report "
                  "`unavailable` and cap the verdict at ready_with_caveats [A.6]:")
            for i in core_missing:
                print("  %-11s %s" % (i["id"], i["fix"]))
            print("\nrun `dops doctor --fix` to install (it will run these commands).")
        else:
            print("\nall core capabilities present — the floor can run unblocked.")
    return 1 if core_missing else 0


if __name__ == "__main__":
    sys.exit(main())
