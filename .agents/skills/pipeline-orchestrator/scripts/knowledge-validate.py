#!/usr/bin/env python3
"""knowledge-validate.py — vault discipline check (v6.0, TZ-10).

Checks, in order:
  1. frontmatter schema of every knowledge/sources/*.md note
     (id, title, url, evidence_level, verified_at, tags, thesis);
  2. id == filename stem; evidence_level in the 3-level scale;
     url is http(s) or internal:;
  3. verified_at parseable; older than 12 months -> stale warning;
  4. link integrity: every `knowledge/<id>` reference found in rule
     files (.agents/skills/**/*.md, eval/*.md) must resolve to a note;
  5. orphan discipline: every note must be referenced by >=1 rule file
     ("правило без заметки не существует; заметка-сирота удаляется");
  6. index.yaml sync: the index is generated from notes, never
     hand-edited; --write-index regenerates it; index must stay <=4 KB.

Usage:
  python3 knowledge-validate.py [repo-root] [--write-index]

Exit: 0 ok (warnings allowed), 1 errors, 2 usage.
"""
import datetime
import os
import re
import sys

LEVELS = {"research", "industry-standard", "curated"}
REQUIRED = ["id", "title", "url", "evidence_level", "verified_at", "tags", "thesis"]
RESERVED = {"sources", "decisions", "gates", "briefs", "index", "readme"}
INDEX_LIMIT = 4096
STALE_DAYS = 365
REF_RE = re.compile(r"knowledge/([a-z0-9][a-z0-9-]*)")
SCAN_GLOBS = [(".agents/skills", ".md"), ("eval", ".md")]

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def parse_frontmatter(path):
    """Tiny YAML-frontmatter reader for the flat note schema
    (no nesting; tags may be [a, b] inline list). Returns dict."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.startswith(" "):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        elif len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1]
        fm[key] = val
    return fm


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write_index = "--write-index" in sys.argv
    root = args[0] if args else "."
    kdir = os.path.join(root, "knowledge")
    sdir = os.path.join(kdir, "sources")
    if not os.path.isdir(sdir):
        print(f"error: {sdir} not found", file=sys.stderr)
        return 2

    notes = {}
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".md"):
            continue
        stem = fn[:-3]
        path = os.path.join(sdir, fn)
        fm = parse_frontmatter(path)
        if fm is None:
            err(f"{fn}: missing or malformed frontmatter")
            continue
        for field in REQUIRED:
            if field not in fm or fm[field] in ("", []):
                err(f"{fn}: required field '{field}' missing/empty")
        if "id" in fm and fm["id"] != stem:
            err(f"{fn}: id '{fm.get('id')}' != filename stem '{stem}'")
        if fm.get("evidence_level") not in LEVELS:
            err(f"{fn}: evidence_level '{fm.get('evidence_level')}' not in {sorted(LEVELS)}")
        url = fm.get("url", "")
        if url and not (url.startswith("http://") or url.startswith("https://")
                        or url.startswith("internal:")):
            err(f"{fn}: url must be http(s):// or internal:, got '{url}'")
        va = fm.get("verified_at", "")
        try:
            d = datetime.date.fromisoformat(str(va))
            age = (datetime.date.today() - d).days
            if age > STALE_DAYS:
                warn(f"{fn}: verified_at {va} is {age}d old (> {STALE_DAYS}d) — re-verify")
        except ValueError:
            err(f"{fn}: verified_at '{va}' is not an ISO date")
        if isinstance(fm.get("tags"), str):
            err(f"{fn}: tags must be an inline list [a, b]")
        notes[stem] = fm

    # --- reference scan -------------------------------------------------
    referenced = {}
    for sub, ext in SCAN_GLOBS:
        base = os.path.join(root, sub)
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(ext):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8", errors="replace") as f:
                    for m in REF_RE.finditer(f.read()):
                        slug = m.group(1).rstrip("-")
                        if slug in RESERVED:
                            continue
                        referenced.setdefault(slug, []).append(
                            os.path.relpath(p, root))
    for slug, where in sorted(referenced.items()):
        if slug not in notes:
            err(f"dangling reference knowledge/{slug} in {where[0]}"
                + (f" (+{len(where)-1} more)" if len(where) > 1 else ""))
    for stem in sorted(notes):
        if stem not in referenced:
            err(f"orphan note knowledge/{stem}: no rule file references it — "
                "cite it or delete it")

    # --- index sync ------------------------------------------------------
    index_path = os.path.join(kdir, "index.yaml")
    lines = ["# GENERATED by knowledge-validate.py --write-index — do not edit by hand.",
             f"generated_at: {datetime.date.today().isoformat()}",
             "notes:"]
    for stem in sorted(notes):
        fm = notes[stem]
        thesis = str(fm.get("thesis", "")).replace('"', "'")
        lines.append(f"  - id: {stem}")
        lines.append(f"    level: {fm.get('evidence_level', '')}")
        lines.append(f"    thesis: \"{thesis}\"")
        lines.append(f"    tags: [{', '.join(fm.get('tags', []))}]")
    generated = "\n".join(lines) + "\n"

    if write_index:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(generated)
    else:
        if not os.path.exists(index_path):
            err("index.yaml missing — run with --write-index")
        else:
            with open(index_path, encoding="utf-8") as f:
                current = f.read()
            cur_norm = re.sub(r"generated_at: .*", "generated_at: -", current)
            gen_norm = re.sub(r"generated_at: .*", "generated_at: -", generated)
            if cur_norm != gen_norm:
                err("index.yaml is out of sync with sources/ — regenerate "
                    "(--write-index); never hand-edit the index")
    size = len(generated.encode("utf-8"))
    if size > INDEX_LIMIT:
        err(f"index.yaml would be {size} B > {INDEX_LIMIT} B limit — shorten theses")

    # --- report ----------------------------------------------------------
    for w in warnings:
        print(f"warn {w}")
    for e in errors:
        print(f"fail {e}")
    status = "FAIL" if errors else "OK"
    print(f"{status}: {len(notes)} note(s), {len(referenced)} id(s) referenced, "
          f"index {size} B, {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
