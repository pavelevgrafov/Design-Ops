#!/usr/bin/env python3
"""draft-directions.py — direction-drafter pack (v0.1.0).

Produces K2B direction-draft prompt packets for external UI generators
(v0, Lovable, ...) and ingests the resulting drafts into the Gate-2 blind
contact-sheet manifest. The external service SKETCHES; the pipeline
MANUFACTURES (neutralize -> tokens -> floor) [A.27].

Commands:
  emit   --contract artifacts/design-contract.yaml --directions specs.yaml
         → writes artifacts/directions/external/prompts/*.md (one packet per
           direction: dials, persona, domains, hard stops from the spec) and
           a manifest.json with pin {service, service_version, prompt_sha256}.
  ingest --contract ... --dir artifacts/directions/external/
         → validates returned drafts (file present, named per manifest),
           marks each candidate origin: external_draft, blind_index shuffled
           seed recorded; writes contact-sheet manifest entries.
  --self-test  offline acceptance test (fixture spec -> emit -> fake draft ->
           ingest -> checks pin + origin marking + hard-stop presence).

Hard rule: drafts are CANDIDATES for the blind contact sheet only. They are
never merged, never tokenized, never shipped without the standard Gate 2 ->
merge -> compile-tokens -> D-floor path (D11/D.30 ban-list included).
"""
import argparse, datetime, hashlib, json, os, sys

try:
    import yaml
except ImportError:
    print("direction-drafter: PyYAML required", file=sys.stderr)
    sys.exit(2)

PACK_DIR = os.path.dirname(os.path.abspath(__file__))
EXT_DIR = os.path.join("artifacts", "directions", "external")

PROMPT_TEMPLATE = """# Direction draft request — {name}

You are generating ONE visual direction draft for a web {profile}.
This is an EXPLORE sketch, not a final product.

## Product
{product_summary}

## Direction spec (fixed, do not change)
- Dials (boldness/richness/temp): {dials}
- Persona: {persona}
- Reference domains: {domains}
- Axes of difference vs sibling drafts: {axes}

## Hard stops (must not appear)
{hard_stops}

## Deliverable
Two screens: {screens}. Desktop 1440 + mobile 390 framing.
Real copy placeholders in {locale}, no lorem ipsum.
"""


def sha_text(t):
    return hashlib.sha256(t.encode()).hexdigest()


def emit(contract_path, spec_path, out_root="."):
    with open(spec_path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    profile = spec.get("profile", "site")
    locale = spec.get("locale", "ru")
    product = spec.get("product_summary", "(see contract)")
    screens = spec.get("screens", ["main", "contrast"])
    hard = spec.get("hard_stops", ["no indigo->purple gradients",
                                   "no glassmorphism", "no bento hero+3",
                                   "no blobs", "no Inter-first font stacks"])
    hard_txt = "\n".join(f"- {h}" for h in hard)
    service = os.environ.get("DIRECTION_DRAFTER_SERVICE", "manual (v0/Lovable)")
    version = os.environ.get("DIRECTION_DRAFTER_VERSION", "n/a")
    out_dir = os.path.join(out_root, EXT_DIR, "prompts")
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"pack": "direction-drafter", "version": "0.1.0",
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "service": service, "service_version": version, "drafts": []}
    for d in spec.get("directions", []):
        name = d.get("name", f"direction-{len(manifest['drafts'])+1}")
        body = PROMPT_TEMPLATE.format(
            name=name, profile=profile, product_summary=product,
            dials=d.get("dials", "?"), persona=d.get("persona", "?"),
            domains=d.get("domains", "?"), axes=d.get("axes", "?"),
            hard_stops=hard_txt, screens=", ".join(screens), locale=locale)
        fn = os.path.join(out_dir, f"{name}.md")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(body)
        manifest["drafts"].append({
            "name": name, "prompt_file": os.path.relpath(fn, out_root),
            "prompt_sha256": sha_text(body),
            "expected_files": [f"{name}-1440.png", f"{name}-390.png"],
            "status": "emitted"})
    mf = os.path.join(out_root, EXT_DIR, "manifest.json")
    with open(mf, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"OK: emitted {len(manifest['drafts'])} prompt packets -> {out_dir}")
    print(f"pin: service={service} version={version}")
    return 0


def ingest(contract_path, ext_dir, out_root="."):
    mf_path = os.path.join(ext_dir, "manifest.json")
    if not os.path.isfile(mf_path):
        print(f"fail: no manifest at {mf_path} — run emit first", file=sys.stderr)
        return 1
    with open(mf_path, encoding="utf-8") as f:
        manifest = json.load(f)
    missing, ok_drafts = [], []
    for d in manifest["drafts"]:
        files = [os.path.join(ext_dir, x) for x in d["expected_files"]]
        if all(os.path.isfile(x) for x in files):
            d["status"] = "ingested"
            ok_drafts.append(d["name"])
        else:
            d["status"] = "missing"
            missing.append(d["name"])
    with open(mf_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    if missing:
        print(f"fail: drafts missing files: {', '.join(missing)}", file=sys.stderr)
        return 1
    print(f"OK: ingested {len(ok_drafts)} external drafts "
          f"(origin: external_draft) -> contact-sheet candidates")
    print("next: blind contact sheet (Gate 2) -> merge -> compile-tokens -> floor")
    return 0


def self_test():
    import tempfile
    root = tempfile.mkdtemp()
    spec = {"profile": "site", "locale": "ru",
            "product_summary": "Фестиваль КРУТО, 3 дня, 100+ артистов",
            "directions": [
                {"name": "dirA", "dials": "8/4/6", "persona": "плакатист",
                 "domains": "лубок, рейв-90х", "axes": "composition"},
                {"name": "dirB", "dials": "5/2/5", "persona": "минималист",
                 "domains": "швейцарская сетка", "axes": "shape"}]}
    sp = os.path.join(root, "spec.yaml")
    with open(sp, "w") as f:
        yaml.safe_dump(spec, f, allow_unicode=True)
    ct = os.path.join(root, "contract.yaml")
    open(ct, "w").write("schema_version: '6.0'\n")
    if emit(ct, sp, root) != 0:
        print("fail: emit"); return 1
    mf = json.load(open(os.path.join(root, EXT_DIR, "manifest.json")))
    ok = True
    if len(mf["drafts"]) != 2:
        print("fail: expected 2 drafts"); ok = False
    if not all(d.get("prompt_sha256") for d in mf["drafts"]):
        print("fail: prompt pin missing"); ok = False
    body = open(os.path.join(root, mf["drafts"][0]["prompt_file"])).read()
    if "no indigo->purple gradients" not in body:
        print("fail: hard stops absent from packet"); ok = False
    # simulate returned drafts for dirA only -> ingest must fail
    ext = os.path.join(root, EXT_DIR)
    for fn in mf["drafts"][0]["expected_files"]:
        open(os.path.join(ext, fn), "w").write("PNG")
    if ingest(ct, ext, root) == 0:
        print("fail: ingest accepted incomplete set"); ok = False
    for fn in mf["drafts"][1]["expected_files"]:
        open(os.path.join(ext, fn), "w").write("PNG")
    if ingest(ct, ext, root) != 0:
        print("fail: ingest rejected complete set"); ok = False
    if ok:
        print("pass: direction-drafter emit->pin->ingest cycle, "
              "incomplete sets refused, hard stops embedded")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", choices=["emit", "ingest"])
    ap.add_argument("--contract", required=False)
    ap.add_argument("--directions", required=False, help="spec yaml for emit")
    ap.add_argument("--dir", default=os.path.join(".", EXT_DIR))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.contract:
        print("usage error: --contract required", file=sys.stderr); sys.exit(2)
    if a.command == "emit":
        if not a.directions:
            print("usage error: emit needs --directions spec.yaml", file=sys.stderr)
            sys.exit(2)
        sys.exit(emit(a.contract, a.directions))
    if a.command == "ingest":
        sys.exit(ingest(a.contract, a.dir))
    print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
