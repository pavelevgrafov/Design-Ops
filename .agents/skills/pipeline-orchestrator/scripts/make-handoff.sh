#!/usr/bin/env bash
# make-handoff.sh — assemble the handoff package (v6.0, TZ-11).
#
# Usage: bash make-handoff.sh <project-root> <out-dir> [--stack "React+TS"]
# Copies code (no node_modules/.git), tokens, contract export and the
# quality report into <out-dir>/handoff/, renders README from the template,
# then verifies every relative link in README resolves.
# Exit: 0 ok, 1 verification failed, 2 usage/io.
set -euo pipefail

ROOT="${1:?usage: make-handoff.sh <project-root> <out-dir> [--stack S]}"
OUT="${2:?usage: make-handoff.sh <project-root> <out-dir> [--stack S]}"
STACK="single-file HTML (no build)"
[ "${3:-}" = "--stack" ] && STACK="${4:-$STACK}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$HERE/../assets/handoff-readme-template.md"
CONTRACT="$ROOT/artifacts/design-contract.yaml"
[ -f "$CONTRACT" ] || CONTRACT="$ROOT/design-contract.yaml"
[ -f "$CONTRACT" ] || CONTRACT="$ROOT/contract.yaml"
[ -f "$CONTRACT" ] || { echo "fail: design-contract.yaml not found in $ROOT" >&2; exit 2; }

READ="$HERE/contract-read.py"
get() { python3 "$READ" "$CONTRACT" "$1" 2>/dev/null || true; }
NAME=$(python3 - "$CONTRACT" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print((c.get("product") or {}).get("name") or "project")
PY
)
PROFILE=$(get profile); PROFILE=${PROFILE:-site}
MODE=$(get mode); MODE=${MODE:-quick}
VERDICT=$(get verdict); VERDICT=${VERDICT:-unknown}

H="$OUT/handoff"
rm -rf "$H"; mkdir -p "$H/src"

# code, minus heavy/ephemeral dirs
( cd "$ROOT" && find . -type d \( -name node_modules -o -name .git -o -name dist -o -name .pack-cache \) -prune -o -type f -print \
  | grep -vE '^\./(artifacts|knowledge|handoff)/' \
  | grep -vE '^\./design-contract.yaml$' \
  | while read -r f; do mkdir -p "$H/src/$(dirname "$f")"; cp "$f" "$H/src/$f"; done )

cp "$CONTRACT" "$H/design-contract.yaml"
for f in artifacts/audit/quality-report.md report.md; do
  if [ -f "$ROOT/$f" ]; then cp "$ROOT/$f" "$H/quality-report.md"; break; fi
done
[ -f "$ROOT/tokens.css" ] && cp "$ROOT/tokens.css" "$H/tokens.css"
[ -f "$H/quality-report.md" ] || echo "(no quality report found at handoff time)" > "$H/quality-report.md"

INDEX=$(cd "$ROOT" && find . -name node_modules -prune -o -name index.html -print 2>/dev/null | head -1 | sed 's#^\./##')
COMMANDS="open src/${INDEX:-index.html} in a browser"
[ -f "$ROOT/package.json" ] && COMMANDS="npm install && npm run dev"
TEST_MAP="- рестайл: сверить diff только с tokens.css (skin property)
- состояния: переключить [data-state] на экране и пройти loading/empty/error
- полный флор: .agents/skills/quality-guardian/scripts/ (D1–D24)"
UNVERIFIED="$(grep -E 'unavailable|skip' "$H/quality-report.md" | head -10 || true)"
[ -n "$UNVERIFIED" ] || UNVERIFIED="- всё проверено либо ограничения приняты с владельцем риска"

sed -e "s/{project_name}/$NAME/g" -e "s/{date}/$(date +%F)/" \
    -e "s/{verdict}/$VERDICT/g" -e "s/{profile}/$PROFILE/g" -e "s/{mode}/$MODE/g" \
    -e "s|{stack}|$STACK|g" -e "s|{commands}|$COMMANDS|g" \
    "$TEMPLATE" > "$H/README.md"
PYRC=0
python3 - "$H/README.md" "$TEST_MAP" "$UNVERIFIED" "$H" <<'PY' || PYRC=$?
import os, re, sys
p, tm, uv, h = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
s = open(p, encoding="utf-8").read()
s = s.replace("{test_map}", tm).replace("{unverified}", uv)
if not os.path.exists(os.path.join(h, "tokens.css")):
    s = s.replace(
        "- `tokens.css` — скомпилированные дизайн-токены (семантический слой).",
        "- токены подключены извне (ссылка на skins/ в HTML), в пакет не входят.")
open(p, "w", encoding="utf-8").write(s)

# link check: backticked paths in the "Что в пакете" section must resolve
sec = s.split("## Что в пакете", 1)[-1].split("\n## ", 1)[0]
missing = []
for tok in re.findall(r"`([a-zA-Z0-9_./-]+)`", sec):
    if "/" not in tok and "." not in tok:
        continue
    if tok.startswith(("http", "npm")) or tok.endswith((".sh/",)):
        continue
    if not os.path.exists(os.path.join(h, tok)):
        missing.append(tok)
for m in missing:
    print(f"fail: README links missing file: {m}", file=sys.stderr)
sys.exit(1 if missing else 0)
PY
[ "$PYRC" -eq 0 ] || { echo "fail: broken link(s) in handoff README" >&2; exit 1; }
echo "OK: handoff assembled at $H (links verified, verdict $VERDICT)"
