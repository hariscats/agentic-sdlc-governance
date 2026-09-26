#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/agent-run.sh {implementer|spec-author|security-reviewer|release-manager} PROMPT" >&2
  exit 2
fi
case "$1" in
  implementer|spec-author|security-reviewer|release-manager) ;;
  *) echo "Unknown agent" >&2; exit 2 ;;
esac
unset COPILOT_ALLOW_ALL
if [[ "$1" == security-reviewer || "$1" == release-manager ]]; then
  exec copilot --agent "$1" -p "$2" --disable-builtin-mcps \
    --deny-tool='shell' --deny-tool='write' --disallow-temp-dir
fi
# Shell remains disabled even if a hook times out. Run tests outside this wrapper.
allowed=()
if [[ "$1" == spec-author ]]; then
  for file in specs/00[12]-*/*.md; do
    allowed+=("--allow-tool=write($PWD/$file)")
  done
else
  allowed+=("--allow-tool=write($PWD/src/app.py)" "--allow-tool=write($PWD/tests/test_app.py)")
  allowed+=("--allow-tool=write($PWD/specs/002-permit-review/tasks.md)")
fi
exec copilot --agent "$1" -p "$2" --disable-builtin-mcps \
  "${allowed[@]}" --deny-tool='shell' --disallow-temp-dir
