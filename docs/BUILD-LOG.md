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

## Final recorded results

| Check / scene | Result and evidence |
|---|---|
| Hosted CI | PASS, run 36278130782; 47 tests and 95.11% coverage |
| Dependency Review | PASS after the documented license correction, run 36278130786 |
| Metrics | PASS, run 36278128092; synthetic usage explicitly labelled, live personal-repository flow |
| Scene 4: SQL negative/fix | PARTIAL: high SQL alert #1 in run 36278010553, then `fixed` after reversal in run 36278097138; CI also returns green in run 36278097133 |
| Scene 4: other gates | Native trace/agent denials and dependency license negative demonstrated; custom-pattern push rejection and Autofix not demonstrated |
| Scene 6: cryptographic verification | PASS for branch-only rehearsal, run 36278128120: provenance, SPDX, exact predicate binding, wrong-main rejection |
| Scene 6: approved release | BLOCKED: staging/production deliberately skipped on build branch; no published production release |
| Reset | PASS: actual demo PR #7 closed and remote branch deleted in 7.6 seconds; repeat completed in 5.6 seconds; four Feature 002 issues remain open/agent-ready |
| Main enforcement | PR #6 remains BLOCKED; no direct main push, bypass actor, self-approval or merge |

Run links use
`https://github.com/hariscats/agentic-sdlc-governance/actions/runs/<run-id>`.
Local `dist/v0.1.0-demo/evidence-v0.1.0-demo.zip` contains downloaded native
**branch** artifacts and verified predicates, the post-reset PR inventory, specs,
and the explicit configuration drift report. It does not assert production
approval or export private hook logs. Native workflow artifacts are downloadable
from run 36278128120. The dashboard was refreshed after reset.

Optional gh-aw/automations were not enabled. The project is implemented and
published for independent review, **not fully accepted end-to-end**. Remaining
human/platform prerequisites are enumerated in SETUP-MANUAL rather than hidden
behind fabricated success or weakened rules.

## Code review fixes and quick demo

A `/review` pass reported five issues. Each fix below was verified locally.

| # | Finding | Fix | Evidence |
|---|---|---|---|
| 1 | Agent gate missed cloud-agent PRs (`gh` reports `app/copilot-swe-agent`; trailers name the human) | `policy.normalize_login` strips `app/` and `[bot]`; commit author/committer names and emails are checked, including `NNN+Copilot@users.noreply.github.com`; metrics reuse the same `is_agent` | Identities observed on public cloud-agent PRs via `gh pr view --json author,commits` and REST `pulls/N`; parametrized tests plus a git-fixture test using a `copilot-swe-agent[bot]` commit |
| 2 | Repo-root `json.py`/`hashlib.py` could shadow stdlib and force "allow" | Wrappers run `python3 -I -S -c ...` and append the repository after the stdlib; hook edits are allowlisted to exact-case `src/`, `tests/`, `specs/` | Reproduced: the old wrapper returned `allow` with a shadow `json.py`, while the new one returned `deny` and wrote audit JSONL. The regression test fails against the old wrapper. |
| 3 | Case-insensitive filesystems bypassed path checks | `protected()` casefolds; hook metadata checks use casefolded relative parts; risk labeller casefolds | Tests for `GOVERNANCE/`, `.GITHUB/`, `Scripts/`, `agents.md`, `.GIT/config`, `.ENV`, `SRC/` |
| 4 | A later COMMENTED review superseded an approval | Review-history logic removed. The native ruleset (`require_code_owner_review`, stale dismissal, last-push approval) and CODEOWNERS enforce security approval; GitHub ignores comment-only reviews | Validator requires those ruleset settings and security owners for `/.github/`, `/governance/`, `/scripts/` |
| 5 | Gate YAML was PR-controlled on `pull_request` | Spec Traceability and Agent PR Policy moved to `pull_request_target`; they check out the default branch only, fetch `refs/pull/N/head` as objects, and never check out PR code | Changelog: https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/ (workflow, `GITHUB_SHA` and `GITHUB_REF` come from the default branch). Validator rejects head `ref`, credential persistence, git worktree commands and duplicate required-check job names |

Consequences recorded in SETUP-MANUAL:
- The two trusted gates no longer report on PR #6 until they exist on `main`, so it stays blocked (fail closed).
- The PR-into-build-branch technique used for PR #7 no longer exercises them.
- Other required checks still run PR-controlled YAML; same-name check semantics remain TODO(verify).

The quick demo is `python -m scripts.rehearse [--pause]`. It is three narrated beats:
the real hook wrapper, both gates plus the seeded SQL-injection test, then the evidence
pack and dashboard. A local run completed in about 1 second. The live proof step
downloads `release-candidate` from the latest successful build-branch release run.

`gh attestation verify` with `--signer-workflow` passed; the provenance ref was
`refs/heads/build/governance-reference` at `806c430`. A copy with one appended byte
failed with HTTP 404 because no attestation matches its digest. `gh` prints nothing
on success without a TTY, so scripted checks use `--format json`.

## End-to-end demo test

Every scene was run against the live repository, or recorded as BLOCKED with the
reason. Nothing was bypassed, and no approval was faked.

| Scene | Result | Evidence |
|---|---|---|
| Quick demo, pre-demo block | PASS | uv sync, live metrics refresh, `release-candidate` download to `/tmp/proof` in 5.1 s |
| Quick demo, beats 1–3 (`rehearse --pause`) | PASS | Real hook wrapper: 4 DENY, 1 ALLOW; both gates BLOCK the 401-line `app/copilot-swe-agent` PR; the seeded patch fails its test; evidence pack built. About 1 s of runtime. |
| Quick demo, scene 3 (attestation) | PASS | `gh attestation verify` printed "✓ Verification succeeded!" (7 attestations for reproducible digest `450b29…`); a copy with one appended byte failed with HTTP 404 |
| 1. Governed intent | PASS (blocked as designed) | Spec PR #5 is `OPEN` / `BLOCKED` pending independent architecture review |
| 2. Bounded local agent (live CLI 1.0.88) | PASS, with one limit | `--deny-tool=shell` stopped shell use, and the agent declined to edit `ci.yml`. In a trusted disposable clone: "Denied by preToolUse hook" for `.git/config` and a full JSONL lifecycle. The T020 proposal took 21 s. No live protected-*edit* denial: the model refused first. |
| 3. Cloud agent | BLOCKED | Hooks and setup steps must be on `main` first (SETUP-MANUAL 6) |
| 4. Negative gates (live PR #8) | PASS | CI failed (runs 36280914503, 36280916892); CodeQL alert #1 `py/sql-injection` (high) at `src/app.py:88`; self-approval rejected with "Can not approve your own pull request". The state is `UNSTABLE`, not `BLOCKED`, because the build branch is outside `main-protection`. |
| 4. Secret push protection | NOT RUN | Custom pattern not configured (SETUP-MANUAL 5) |
| 5. Humans decide | PASS (config) | Production: required reviewer, `prevent_self_review=true`, `main` only; `can_admins_bypass=true` still needs the manual fix |
| 6. Provable release on `main` | BLOCKED | Dispatch returns HTTP 422 because `main` has no workflows before bootstrap; build-branch chain `build → attest → branch-proof` passed |
| 7. Outcomes and reset | PASS | Dashboard has no external references, a SYNTHETIC banner and live flow data. Config audit reports only drift `is_automations_enabled`. Reset `--apply` took 8 s: PR #8 closed, its branches deleted, issues #1–#4 relabelled. A second apply was idempotent. |

Hardening from this test and the automatic Copilot reviews:

- `release.yml` is split so only the no-checkout `attest` job holds `id-token: write`. The validator rejects signing jobs that check out or run code.
- PR evidence keeps only audit facts: reviewer logins and states, check conclusions, commit SHAs and an agent flag. Review bodies, commit messages and emails are dropped.
- Reset now validates local paths before any remote action, deletes local `demo/*` branches (`gh pr close --repo` removes only the remote one), and refuses to run while you are on a demo branch.
- The Agent PR Policy Gate now enforces the hooks' `src/`, `tests/` and `specs/` allowlist (`policy.EDITABLE`), so local and cloud agents share one boundary.
- Other fixes:
  - hooks deny empty paths;
  - task IDs match `T\d{3,}` and are read from the base branch;
  - descriptions must be printable;
  - metrics count only the latest result per check.

Declined, with reasons:

- `gh pr list --state merged` is valid (gh 2.92 help; live call).
- The rehearsal shows a simulated command on screen, but the audit log stores only hashes.
- CodeQL keeps `security-events: write` on `pull_request`. This is GitHub's documented setup: Python `build-mode: none` executes no PR code, and fork PRs get a read-only token.
- The validator already scans the full `run` line for worktree commands. A regression test covers `printf x | git checkout`.
- Three `tasks.md` formatting findings were docs-only.

## Bootstrap merge and first `main` release

The trusted gates run from `main`, so they could not check the PR that installs them.
The owner therefore merged PR #6 through a single, logged exception:

| Step | Evidence |
|---|---|
| Temporary bypass: *Repository admin*, "For pull requests only" | Documented option: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository#granting-bypass-permissions-for-your-branch-or-tag-ruleset |
| Squash merge of PR #6 by `hariscats` at 2026-09-27T00:24:05Z | Commit `e2b02b3`, signed by GitHub (`verified: true`); rule suite `4243669608`, result `bypass` |
| Bypass removed with `bash scripts/apply-rulesets.sh` | `main-protection` and `release-tags` both `active` with 0 bypass actors and all five required checks |
| PR #5 closed as superseded | All 72 files identical in PR #6 (`git diff`) |
| Owner hardening | Production `can_admins_bypass=false`; cloud-agent config audit `pass` |
| Runs on `main` | CI 36282381641, CodeQL 36282381544, Metrics 36282381670 and Copilot Setup Steps 36282381647 all succeeded |
| First PR checked by trusted gates from `main` | Dependabot PR #9: Spec Traceability Gate, Agent PR Policy Gate, CI, CodeQL and Dependency Review passed; `BLOCKED` only on code-owner review |

First `main` release dispatch (`v0.1.0`, run 36282787385):

- **Passed:** build → attest → staging (simulated).
- **Verified:** `verify` checked provenance and the SPDX attestation with `--source-ref refs/heads/main --source-digest e2b02b3`. Local `gh attestation verify` confirmed the certificate's `sourceRepositoryRef` is `refs/heads/main` and its digest is `e2b02b3`. A copy with one appended byte failed.
- **Failed:** the same `verify` job then hit `gh: Resource not accessible by integration (HTTP 403)` from `scripts/audit-cloud-agent-config.sh`. The preview endpoint documents OAuth app and classic PAT (`repo`) tokens only. Build-branch runs skip `verify`, so only a `main` release could reveal this.
- **Fix:** `verify` no longer calls the endpoint. The evidence pack names the audit as missing with the reason, and the job summary tells the production approver to run it and see `pass` before approving. A regression test pins this. A broad classic PAT secret was rejected on least-privilege grounds.
- **Not reached:** production was skipped, so no release or tag was published.

## Post-bootstrap release and README rerun guide

| Step | Evidence |
|---|---|
| PR #10 merged by `hariscats` at 2026-09-27T00:57:31Z through a logged, PR-only bypass | Commit `c5fb609`; rule suite `4243839155`, result `bypass`. The sole code owner cannot approve their own PR. |
| Bypass removed with `bash scripts/apply-rulesets.sh` | `main-protection`: `enforcement: active`, 0 bypass actors |
| Quick demo rerun from `main` | `uv run --frozen python -m scripts.rehearse`: all 3 beats passed |
| Release `v0.1.0` dispatched on `main` (run 36284728209) | build, attest, staging and verify succeeded; production is waiting. `pending_deployments` reports `current_user_can_approve: false` for the dispatcher. |
| Artifact from a run waiting at production | `gh run download -n release-candidate` succeeded. This settles the earlier open question. |
| Local verification | `gh attestation verify --source-ref refs/heads/main`: `sourceRepositoryRef` is `refs/heads/main`, digest `c5fb609`. A copy with one appended byte was rejected. |
| README | Added a strictly-for-demo disclaimer and the end-to-end rerun guide (prep, tabs, scenes, benefits, limits, reset). Ruleset and PR URLs returned HTTP 200. |
