#!/bin/sh
# packs/recheck.sh — scheduled contract test: re-run acceptance for every
# active pack; a red test flips the pack to unavailable until triage.
# Usage: sh packs/recheck.sh [pack_id]
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RESOLVER="$ROOT/.agents/skills/pipeline-orchestrator/scripts/pack-resolve.py"
if [ $# -ge 1 ]; then
  python3 "$RESOLVER" "$ROOT/packs" "$1" --ttl-hours 0
else
  python3 "$RESOLVER" "$ROOT/packs" --all --ttl-hours 0
fi
