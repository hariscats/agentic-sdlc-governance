#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .demo-state
gh api --method GET repos/hariscats/agentic-sdlc-governance/copilot/cloud-agent/configuration \
  > .demo-state/cloud-agent-actual.json
python3 -m governance.audit_config
