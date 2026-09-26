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

## Hosted verification

- Implementation PR: https://github.com/hariscats/agentic-sdlc-governance/pull/6.
  Hosted CI https://github.com/hariscats/agentic-sdlc-governance/actions/runs/36277828152
  and CodeQL https://github.com/hariscats/agentic-sdlc-governance/actions/runs/36277828210
  passed. Trusted-base gates failed closed because main has no governance module.
- Metrics https://github.com/hariscats/agentic-sdlc-governance/actions/runs/36277826077
  passed and uploaded the static dashboard and summary.
- Native branch rehearsal
  https://github.com/hariscats/agentic-sdlc-governance/actions/runs/36277826177
  passed: source ZIP provenance and SPDX attestations verified, main provenance
  rejected, staging/production skipped. Downloaded SPDX also passed exact signed
  predicate comparison using `scripts.verify_sbom`. This is not a production release.
- Dependency Review caught a real policy negative (run 36277828263):
  missing Python-2.0.1 and 0BSD identifiers, plus a GPL classification for
  typing-extensions 4.16.0. The upstream version's LICENSE explicitly says Python
  is not distributed under GPL; GPL appears in historical compatibility wording.
  Proposed correction adds the two Python/BSD identifiers and an **exact-version**
  `pkg:pypi/typing-extensions@4.16.0` license exception, not a general GPL allowance.
  Vulnerability checks remain enabled. This bootstrap policy change still requires
  independent review; future versions do not inherit the exception.
  Sources:
  https://raw.githubusercontent.com/python/typing_extensions/4.16.0/LICENSE,
  https://spdx.org/licenses/Python-2.0.1.html,
  https://raw.githubusercontent.com/actions/dependency-review-action/a1d282b36b6f3519aa1f3fc636f609c47dddb294/action.yml,
  https://raw.githubusercontent.com/actions/dependency-review-action/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/licenses.ts.

- Hosted negative PR #7 (base: build branch, never main) exposed incompatible
  `gh api --slurp --jq` flags. Corrected to pipe JSON to `jq`, matching
  `gh api --help` pagination examples at https://cli.github.com/manual/gh_api.
  Added repository-validation regression coverage. This initial failure was a CLI
  wiring defect, not a successful agent-policy denial.
- Dependency Review correction passed in run 36277906687. Spec Traceability
  rejected PR #7 for the intended missing spec/task/test references in run
  36277906902.

## Native negative rehearsal and final acceptance boundaries

- PR #7 targets the unmerged build branch so trusted policy can execute without
  weakening main. After the pagination fix, Agent PR Policy run 36277953954
  reports the intended missing issue and spec label; CI rejects the unsafe code.
- The original one-line fixture was caught by pytest but not CodeQL. The revised
  fixture exposes the SQLite connection directly, with explicit try/finally cleanup,
  rather than through `contextlib.closing`. Native CodeQL run 36278010553 produced
  alert #1: `py/sql-injection`, **high**, `src/app.py`. This fixes the demonstration,
  not a production app defect. Safe application code remains parameterized.
  Source/alert API reference:
  https://docs.github.com/en/rest/code-scanning/code-scanning#list-code-scanning-alerts-for-a-repository.
- The fixture was reversed with a new commit, not rewritten history. This is a
  presenter-applied fix, **not a claimed Copilot Autofix**. The negative PR does
  not establish successful installation of main's trusted gate code.
- Native branch proof now also compares the downloaded SPDX document with the
  verified signed predicate inside Actions. Branch proof never enters environments.
- Upstream Spec Kit MIT notice retained in `.specify/LICENSE`, covering generated
  Spec Kit assets: https://raw.githubusercontent.com/github/spec-kit/v1.0.9/LICENSE.
- 47 tests, 95.11% coverage, strict types, lint and configuration validation pass
  after hosted-feedback fixes. Initial commits are unsigned (`git log %G?` = N);
  signature enforcement was not disabled.
- Main acceptance is still blocked by independent bootstrap approval, unavailable
  independent reviewer, and trust-root installation. Custom-pattern push rejection,
  cloud delegation/requester approval, and production release remain unverified.
  Cloud automations drift and production administrator bypass require manual action.
