# Build log

## 2026-09-26: scope and preflight

User selected personal account `hariscats`, explicitly excluding company organizations,
and requested execution through all phases. Target created private:
https://github.com/hariscats/agentic-sdlc-governance.
GitHub-created README is the only bootstrap main commit. All subsequent work uses PR branches.

Tools: git 2.39.3, gh 2.92.0, shell Copilot CLI 1.0.88, uv 0.11.14.
`gh auth status` confirms the selected personal account. No credentials are recorded.
Python 3.12 and Specify were missing. Installations are scoped to tools/project dependencies.

Personal-private mode cannot provide the full enterprise acceptance criteria.
No organization data is included in the demo. Usage data is explicitly synthetic.
No approval, CodeQL, push protection, attestation, or cloud-agent execution will be
claimed merely because a workflow file exists.

## Verified references before implementation

| Surface | Reference / evidence |
|---|---|
| Repository / PR commands | `gh repo create --help`, `gh pr create --help`, `gh pr merge --help`; https://cli.github.com/manual/ |
| Ruleset create/list/schema | https://docs.github.com/en/rest/repos/rules |
| Cloud-agent configuration GET | https://docs.github.com/en/rest/copilot/copilot-cloud-agent-management |
| Copilot usage report endpoints | https://docs.github.com/en/rest/copilot/copilot-usage-metrics |
| Hook JSON/events/decisions | https://docs.github.com/en/copilot/reference/hooks-reference |
| Custom-agent frontmatter/tools | https://docs.github.com/en/copilot/reference/custom-agents-configuration |
| Workflow syntax | https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax |
| Setup steps | https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-development-environment |
| Spec Kit installation | https://github.github.com/spec-kit/installation.html |
| Private security limits | https://docs.github.com/en/code-security/getting-started/github-security-features |
| Environment approval limits | https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments |
| Individual CODEOWNERS | https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners |

Action SHA provenance: `git ls-remote --tags --refs` against each official action
repository before using the refs. Exact SHA/tag pairs are recorded beside each workflow action.
No enterprise policy endpoints are used by this project.

## Public profile approved

The user explicitly requested public visibility after the personal-private ruleset API
returned 403 (upgrade or make public). `gh repo edit --help` verified the visibility flags.
Visibility changed to PUBLIC. A transient "Repository has been locked" response during
the transition cleared on retry. Rulesets 24054367 and 24054368 were created active,
with no bypass actors. GET rules/branches/main confirms all seven main rule types.
No direct push to main has occurred.

Staging and production environments created via documented
https://docs.github.com/en/rest/deployments/environments and
https://docs.github.com/en/rest/deployments/branch-policies.
Both are restricted to branch main. Production requires hariscats and prevents self-review.
The response exposes can_admins_bypass=true; disabling it remains manual because the
documented PUT schema reviewed did not include that input.

Cloud-agent GET succeeds. Firewall and all review tools are enabled and workflow approval
is required. Audit finds is_automations_enabled=true versus the expected false; this remains
an explicit release blocker, not silently accepted.

Spec Kit 1.0.9 initialized with the bundled Git extension 1.0.0. It installed skills mode:
`/speckit-<command>`. Artifacts were authored following that lifecycle; independent
slash-command execution transcripts are not claimed. Python 3.12.13 installed by uv.

Action inputs verified against action.yml in each pinned action repository, including
checkout, setup-python, upload/download-artifact, dependency-review, CodeQL init/analyze,
attest-build-provenance and attest-sbom. CodeQL v4.38.2 is an annotated tag:
the dereferenced commit is 2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2.
attest-sbom v4.1.0 is deprecated but still functional; replacement requires reviewed
action migration. SPDX document fields: https://spdx.github.io/spdx-spec/v2.3/document-creation-information/.
PR evidence/review fields: https://docs.github.com/en/rest/pulls/reviews and `gh pr view --help`.
Release and verification commands: `gh release create --help`, `gh attestation verify --help`.

## Local verification and publication

- `uv run --frozen ruff check src tests governance metrics scripts` and strict
  `mypy` pass. `pytest --cov --cov-report=xml --junitxml=junit.xml`: 47 tests pass,
  95.11% application/governance coverage against the unchanged 80% threshold.
- Repository configuration validation passes. The temporary-copy SQL injection
  patch makes the expected regression test fail; the working application stays safe.
  Hook policy negatives, trace/agent negatives and local release integrity pass.
  These are not claims of native CodeQL or push-protection enforcement.
- Live flow collection works after replacing a nested GraphQL query with bounded
  per-PR queries and handling the documented CLI's paginated error envelope.
  Code scanning currently returns 404 and is explicitly unavailable; usage remains
  labelled synthetic. Alert references:
  https://docs.github.com/en/rest/code-scanning/code-scanning and
  https://docs.github.com/en/rest/dependabot/alerts.
- Reset applied twice to issues #1-#4, in 6.4 and 5.7 seconds. No demo PRs existed
  during this initial reset exercise.
- Noninteractive CLI read-only smoke returned the Feature 002 title but produced
  no session audit record. Repository hooks are therefore **not verified as loaded**
  on this installed invocation; the wrapper's explicit shell/write restrictions
  remain mandatory. Policy unit tests are not evidence of CLI hook loading.
- Specification PR: https://github.com/hariscats/agentic-sdlc-governance/pull/5.
  GitHub reports `BLOCKED`, `REVIEW_REQUIRED`, with no checks installed on main.
  This is spec-first publication, not a completed spec-first merge.
- Release workflow includes an explicitly scoped build-branch attestation rehearsal.
  It cannot enter staging/production and must reject branch provenance as main.
  Only a main dispatch can follow the production path. This does not bypass approvals.
  Native rehearsal results are recorded separately after execution.
