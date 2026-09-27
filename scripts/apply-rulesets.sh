#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
repo=hariscats/agentic-sdlc-governance
for file in governance/rulesets/*.json; do
  name=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$file")
  id=$(gh api --method GET "repos/$repo/rulesets?includes_parents=false&per_page=100" \
    --paginate --jq ".[] | select(.name == \"$name\") | .id")
  if [[ -n "$id" ]]; then
    gh api --method PUT "repos/$repo/rulesets/$id" --input "$file"
  else
    gh api --method POST "repos/$repo/rulesets" --input "$file"
  fi
done
