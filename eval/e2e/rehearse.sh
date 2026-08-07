#!/usr/bin/env bash
# rehearse.sh — the end-to-end rehearsal, defined exactly once.
#
# Amendment 07 §2 of the bridge protocol: a rehearsal must be the thing it
# rehearses. Before this script the end-to-end job lived as inline steps in
# `.github/workflows/design-ops.yml`, and anyone checking a change locally
# retyped those steps from memory. On 2026-08-06 that retyping was one `cp`
# more generous than the real job — three token files instead of two — and the
# difference hid a D.41 defect until it turned `main` red.
#
# So: the workflow no longer contains the rehearsal. It installs an
# environment and calls this file. Whatever CI does, this does, because it is
# the same bytes. A self-test probe fails the build if the steps ever leak
# back into the workflow.
#
# Usage:
#   eval/e2e/rehearse.sh [--root DIR] [--port N] [--profile P]
#                        [--starter NAME] [--skin NAME] [--out FILE] [--keep]
#
# Exit: 0 the floor came back ready (or ready_with_caveats), 1 it did not,
#       2 the rehearsal could not be set up at all.
#
# bash 3.2 / BSD-safe: no GNU-only flags. The old inline version used
# `sed -i 's|...|...|'`, which is GNU syntax and fails on macOS — proof that
# nobody had ever run the "same" steps on the machine where they were written.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
WORK=""
PORT=8901
PROFILE=standard
STARTER=landing-event
SKIN=base-site
OUT=""
KEEP=0

while [ $# -gt 0 ]; do
  case "$1" in
    --root)    WORK="$2"; shift 2 ;;
    --port)    PORT="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --starter) STARTER="$2"; shift 2 ;;
    --skin)    SKIN="$2"; shift 2 ;;
    --out)     OUT="$2"; shift 2 ;;
    --keep)    KEEP=1; shift ;;
    -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'rehearse: unknown argument %s\n' "$1" >&2; exit 2 ;;
  esac
done

[ -n "$WORK" ] || WORK="$(mktemp -d 2>/dev/null || mktemp -d -t dops-e2e)"
[ -n "$OUT" ] || OUT="$WORK/floor.json"
PY="${PYTHON:-python3}"
[ -x "$ROOT_DIR/.venv/bin/python" ] && PY="$ROOT_DIR/.venv/bin/python"

SERVER_PID=""
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  if [ "$KEEP" -eq 0 ] && [ -n "$WORK" ] && [ -d "$WORK" ]; then
    case "$WORK" in
      /|/home|/Users|"$ROOT_DIR") ;;            # never, under any argument
      *) rm -rf "$WORK" ;;
    esac
  fi
}
trap cleanup EXIT INT TERM

step() { printf '\n== %s\n' "$1"; }
die()  { printf 'rehearse: %s\n' "$1" >&2; exit "${2:-2}"; }

cd "$ROOT_DIR" || die "cannot enter the package root"

# --------------------------------------------------------------------------
step "environment capabilities"
# Honest degradation [A.6]: the rehearsal runs without playwright, the browser
# lane reports `unavailable`, and this line says so out loud rather than
# letting a thinner run pass for a full one.
bash tools/dops doctor || die "doctor refused to run"
PW=""
if command -v node >/dev/null 2>&1; then
  PW="$(node -e "console.log(require.resolve('playwright'))" 2>/dev/null || true)"
fi
[ -n "$PW" ] || printf '\nnote: playwright not resolvable — the browser lane will report\n      unavailable, and this rehearsal is therefore NOT the full CI run.\n'

# --------------------------------------------------------------------------
step "materialise a project from starter $STARTER"
mkdir -p "$WORK/artifacts/ux" "$WORK/artifacts/visual" || die "cannot create $WORK"

# Fill every copy slot with its own name: content is irrelevant here, coverage
# is what the injector asserts.
"$PY" - "$STARTER" "$WORK" <<'PYEOF' || die "cannot build values.yaml (pyyaml missing?)"
import sys, yaml
starter, work = sys.argv[1], sys.argv[2]
cmap = yaml.safe_load(open("starters/%s/copy-map.yaml" % starter))
yaml.safe_dump({k: "CI %s" % k.replace("_", " ") for k in cmap},
               open(work + "/values.yaml", "w"), allow_unicode=True, sort_keys=False)
PYEOF

# The contract goes first so the injector can stamp the model's origin into
# it. AC-23: the quick-mode ceiling limits what a run PRODUCES, not what a
# Verified Starter carries in — this rehearsal stays in that case and
# exercises the exemption end to end.
cp "starters/$STARTER/contract.yaml" "$WORK/artifacts/design-contract.yaml"
"$PY" starters/inject.py "starters/$STARTER" "$WORK/values.yaml" \
  --out "$WORK/site" --ux-out "$WORK/artifacts/ux" \
  --contract "$WORK/artifacts/design-contract.yaml" || die "injection failed" 1
grep -q "origin: inherited" "$WORK/artifacts/design-contract.yaml" \
  || die "the injector did not stamp origin: inherited [AC-23]" 1

# All three files a real K2A leaves behind, not two of them: a materialisation
# thinner than the real thing makes the floor measure a project that never
# exists. This exact line is why the script exists (D.41, 2026-08-06).
cp "skins/$SKIN/tokens.json" "skins/$SKIN/tokens.css" \
   "skins/$SKIN/tokens.theme.css" "$WORK/artifacts/visual/"
cp "skins/$SKIN/tokens.css" "$WORK/site/tokens.css"
"$PY" - "$WORK/site/index.html" "$SKIN" <<'PYEOF' || die "cannot repoint the stylesheet" 1
import sys
path, skin = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
old = "../../../skins/%s/tokens.css" % skin
if old not in text:
    raise SystemExit("the skeleton does not link %s" % old)
open(path, "w", encoding="utf-8").write(text.replace(old, "tokens.css"))
PYEOF

# --------------------------------------------------------------------------
step "self-service panel on the real build"
"$PY" tools/dops_panel.py emit --skin "$SKIN" --artifact "$WORK/site/index.html" \
  || die "panel emit failed" 1
# A config with no knobs means the emitter found nothing the artefact uses —
# silently useless, so the count is asserted rather than printed.
"$PY" - "$WORK/site/panel-config.js" <<'PYEOF' || die "the panel emitted no knobs" 1
import json, sys
s = open(sys.argv[1], encoding="utf-8").read()
cfg = json.loads(s[s.index("{"):s.rstrip().rstrip(";").rindex("}") + 1])
print("knobs:", len(cfg["knobs"]))
sys.exit(0 if cfg["knobs"] else 1)
PYEOF

# --------------------------------------------------------------------------
step "serve the build on :$PORT"
( cd "$WORK/site" && exec "$PY" -m http.server "$PORT" >/dev/null 2>&1 ) &
SERVER_PID=$!
URL="http://localhost:$PORT"
UP=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if curl -sf "$URL/" >/dev/null 2>&1; then UP=1; break; fi
  sleep 0.5
done
[ "$UP" -eq 1 ] || die "the build never came up on $URL" 1

# --------------------------------------------------------------------------
if [ -n "$PW" ]; then
  step "record the visual-regression baseline"
  DOPS_PLAYWRIGHT="$PW" sh .agents/skills/quality-guardian/scripts/visual-regression.sh \
    reference "$URL" "$WORK/artifacts/audit/shots" "/" || die "baseline failed" 1
fi

# --------------------------------------------------------------------------
step "the floor, profile $PROFILE"
RC=0
"$PY" tools/dops_verify.py --root "$WORK" --profile "$PROFILE" \
  --url "$URL" --routes / --out "$OUT" || RC=1

step "shot budget for diagnostics"
"$PY" tools/dops_shots.py --root "$WORK" --budget 6 || true

printf '\nrehearse: floor report at %s\n' "$OUT"
[ "$KEEP" -eq 1 ] && printf 'rehearse: work tree kept at %s\n' "$WORK"
exit "$RC"
