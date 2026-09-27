# Manual setup, prerequisites, and remaining acceptance

## Current profile

`hariscats/agentic-sdlc-governance` is **public**, explicitly approved by the user.
The earlier private-plan limitations in BUILD-LOG are historical, not current
limitations on CodeQL, dependency review, environments, or attestations.
Organization/enterprise telemetry remains inapplicable: usage fixtures are labelled.

## Human decisions that automation must not fabricate

1. **Bootstrap the trust root (done 2026-09-27).** The trace and agent gates run on
   `pull_request_target`, which uses the workflow and gate code from the default
   branch, so they could never report on the PR that installs them. That PR also
   intentionally violated the 400-line/agent path policy. The owner therefore
   squash-merged PR #6 through a temporary *Repository admin* bypass in
   "For pull requests only" mode. GitHub logged it as rule suite `4243669608` and
   signed the squash commit `e2b02b3`. `scripts/apply-rulesets.sh` then restored zero
   bypass actors (verified via the API). It did not merge through the normal task
   gates. Record any future bypass the same way.
2. **Add an independent reviewer with write access.** Replace/extend the personal
   CODEOWNERS entries so the PR author is not the only authorized reviewer.
   All three initial roles are `hariscats`, not separation of duties. Until this is
   done, every PR the owner authors, including agent-coauthored maintenance PRs,
   needs the same logged bypass; Dependabot and other bot PRs can be approved.
3. **Disable production administrator bypass (done).** The API now reports
   `can_admins_bypass=false`, with required reviewer `hariscats`,
   `prevent_self_review=true` and a main-only deployment policy.
4. **Resolve cloud-agent drift (done).** Automations are disabled, and
   `scripts/audit-cloud-agent-config.sh` reports `pass`. The endpoint supports GET
   only, and per its docs accepts OAuth app tokens or classic PATs with `repo` scope.
   The release workflow's `GITHUB_TOKEN` gets HTTP 403, so the evidence pack records
   this audit as missing. Run it locally rather than storing a broad classic PAT as a
   secret. Never turn off the firewall to make setup easier.
5. **Configure the custom secret pattern** `DEMOSECRET_[A-Z0-9]{24}` and enable
   push protection for that pattern. Provider push protection is not evidence that
   this custom pattern is active. Generate examples at runtime, never commit them.
6. **Cloud delegation is now possible.** Hooks and setup steps are on `main`, and
   Copilot Setup Steps passed there. Confirm personal Copilot entitlement and
   selected-repository access.
   Assign one spec-002 task only during the live demo.
7. **Rehearse an approved native release.** The first `main` dispatch (run
   `36282787385`) passed build, attest and staging and verified both attestations
   as `main` provenance, then failed at the cloud-agent audit (item 4; fixed after
   bootstrap). A different authorized actor must approve production under the
   self-review restriction. No production approval or published release is claimed.
8. **Use verified signed commits for acceptance.** Local setup commits are unsigned.
   Keep the signed-commit rule enabled; the independent bootstrap procedure must
   account for signing (for example, an authorized GitHub-signed squash once all
   other prerequisites are satisfied). No unverified signing identity was installed.
   https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
9. **Trust the repository folder in Copilot CLI once.** Repository hooks
   (`.github/hooks/governance.json`) load only from a trusted folder, including in
   `copilot -p` mode. Launch `copilot` interactively in the clone and accept the
   folder trust prompt; it is stored as `trustedFolders` in `~/.copilot/config.json`
   (`copilot help config`). Never set `COPILOT_ALLOW_ALL=true` to get this effect;
   `scripts/agent-run.sh` unsets it. Custom agents (`--agent`) load either way.

## Verified references

| Topic | Current documentation |
|---|---|
| Rulesets | https://docs.github.com/en/rest/repos/rules |
| CODEOWNERS | https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners |
| Environment approval and bypass | https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments |
| Environment API | https://docs.github.com/en/rest/deployments/environments |
| Cloud-agent GET configuration | https://docs.github.com/en/rest/copilot/copilot-cloud-agent-management |
| Personal Copilot policy | https://docs.github.com/en/copilot/how-tos/manage-your-account/managing-copilot-policies-as-an-individual-subscriber |
| Custom secret patterns | https://docs.github.com/en/code-security/how-tos/secure-your-secrets/customize-leak-detection/define-custom-patterns |
| Hook payloads and timeout behavior | https://docs.github.com/en/copilot/reference/hooks-reference |
| `pull_request_target` uses the default branch | https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/ |
| Artifact attestations | https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations |
| Metrics schemas | https://docs.github.com/en/rest/copilot/copilot-usage-metrics |
| Cloud-agent protections | https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent |

## Explicit limitations and TODO(verify)

- **TODO(verify):** The cloud-agent requester approval restriction must be demonstrated
  against an actual cloud-created PR. `require_last_push_approval` is not a substitute
  for a requester-identity rule; do not claim equivalence.
- **TODO(verify):** PowerShell hook wrapper on Windows; only the shared Python policy
  and Bash wrapper are exercised on this macOS host.
- **Verified (CLI 1.0.88):** repository hooks load in `copilot -p` mode only when the
  folder is trusted (prerequisite 9). In an untrusted disposable clone no audit was
  written; after trusting it, the CLI printed "Denied by preToolUse hook" for a
  `.git/config` read and the full JSONL lifecycle was recorded. The explicit tool
  restrictions in `scripts/agent-run.sh` apply either way. A live hook denial of a
  protected *edit* was not observed because the model refused before calling the
  tool; `scripts.rehearse` exercises that path through the real wrapper.
- Agent identity signals were verified on public cloud-agent PRs (`gh`:
  `app/copilot-swe-agent`; REST: `Copilot`; commits: `copilot-swe-agent[bot]` with a
  `+Copilot@users.noreply.github.com` email). The `agent-authored` label and Copilot
  co-author trailers cover local CLI contributions. An actor who strips all
  provenance cannot be identified infallibly by metadata.
- **TODO(verify):** CI, CodeQL and Dependency Review run PR-controlled workflow YAML
  on `pull_request`, so a PR could edit them or add a job with a required check's
  name. CODEOWNERS review of `.github/`, the agent gate's path allowlist and the
  validator's duplicate-name rule reduce this risk. How GitHub resolves two
  same-named check runs is not verified. Organization-level required workflows are
  not configured for this personal repository.
- The gates fetch `refs/pull/N/head` anonymously because the repository is public.
  A private copy fails closed until the fetch is given a read-only credential.
- Hooks are defense in depth. Command-hook timeouts fail open per current docs;
  arbitrary test code is executable. Use isolated runners and do not expose secrets
  to agent-controlled tests. The local wrapper denies shell and only grants specific
  source/test/spec files; no `--allow-all-tools`. Hook edits are limited to exact-case
  `src/`, `tests/` and `specs/`, and the hook interpreter runs with `-I -S`.
- Spec author path scope is instructional outside the local wrapper; custom-agent
  tool aliases do not express a directory sandbox.
- Local audit JSONL is not automatically uploaded: raw prompts/arguments are never
  stored. Cloud sandbox files are ephemeral; external export needs a reviewed destination.
- Optional Copilot CLI advisory CI is not enabled. `copilot login --help` documents
  Copilot Requests fine-grained tokens / supported OAuth tokens, not classic PATs.
  Do not put an interactive local token into CI merely to enable this optional gate.
- Usage fixtures have a **demo-owned schema**, not an invented GitHub NDJSON schema.
  No organization endpoints or `COPILOT_METRICS_TOKEN` are configured. A future
  organization adapter must validate the live documented report fields before use.
- Flow metrics use the latest 100 PRs. Failure rates describe latest completed
  checks, not every retry. Historical converge-loop/Autofix attribution is unavailable.
  Alert-state counts are not a time series; missing permissions produce null plus a reason.
- SPDX is a complete **lockfile inventory including dev dependencies**, not a
  claim of installed-image dependency completeness. Unknown licenses are NOASSERTION.
- `attest-sbom` v4.1.0 currently emits a deprecation warning. Its pinned, verified
  interface is used until a separately reviewed migration to `actions/attest`.
- gh-aw and Copilot automations are deliberately excluded. Azure deployment is simulated.
- The exact-version typing-extensions license metadata exception is proposed in
  the bootstrap PR, with source-license evidence in BUILD-LOG. The compliance
  owner must approve this policy correction before production use.
