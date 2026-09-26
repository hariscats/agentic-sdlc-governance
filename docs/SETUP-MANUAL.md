# Manual setup, prerequisites, and remaining acceptance

## Current profile

`hariscats/agentic-sdlc-governance` is **public**, explicitly approved by the user.
The earlier private-plan limitations in BUILD-LOG are historical, not current
limitations on CodeQL, dependency review, environments, or attestations.
Organization/enterprise telemetry remains inapplicable: usage fixtures are labelled.

## Human decisions that automation must not fabricate

1. **Bootstrap the trust root with independent approval.** The initial main contains
   only the GitHub-created README. The trace and agent gates run on
   `pull_request_target`, which uses the workflow and gate code from the default
   branch and never PR-controlled Python. Until they exist on main, those two
   required checks never report on the installation PR, so it stays blocked (fail closed). An independently
   reviewed platform bootstrap procedure is required before normal task PRs can
   pass. The initial large, agent-coauthored governance PR also intentionally
   violates the ordinary 400-line/protected-path policy. Do not silently relabel
   it human, bypass rules, or claim it merged through the normal task gates.
   Decide and record an explicit bootstrap exception outside the normal live-demo
   path, or have a platform owner install the trust root before enabling the final
   required check set. **No exception was exercised by this build.**
2. **Add an independent reviewer with write access.** Replace/extend the personal
   CODEOWNERS entries so the PR author is not the only authorized reviewer.
   All three initial roles are `hariscats`, not separation of duties.
3. **Disable production administrator bypass in the UI.** Environments were created
   with required reviewer `hariscats`, `prevent_self_review=true` and main-only
   deployment policies. The observed default `can_admins_bypass=true` needs
   manual hardening; the reviewed PUT documentation omitted that setting.
4. **Resolve cloud-agent drift.** The baseline expects automations disabled.
   The live API reported `is_automations_enabled=true`; disable automations in
   personal/repository cloud-agent settings and rerun the audit. The published
   configuration endpoint reviewed supports GET, not a verified update operation.
   Never turn off the firewall to make setup easier.
5. **Configure the custom secret pattern** `DEMOSECRET_[A-Z0-9]{24}` and enable
   push protection for that pattern. Provider push protection is not evidence that
   this custom pattern is active. Generate examples at runtime, never commit them.
6. **Perform cloud delegation only after bootstrap.** Confirm personal Copilot
   entitlement and selected-repository access. Hooks/setup must be on main first.
   Assign one spec-002 task only during the live demo.
7. **Rehearse an approved native release.** Trigger release.yml on main after
   merged checks are green. A different authorized actor must initiate/approve
   production under the configured self-review restriction. The local rehearsal
   does not claim native attestation or production approval.
8. **Use verified signed commits for acceptance.** Local setup commits are unsigned.
   Keep the signed-commit rule enabled; the independent bootstrap procedure must
   account for signing (for example, an authorized GitHub-signed squash once all
   other prerequisites are satisfied). No unverified signing identity was installed.
   https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification

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
- **TODO(verify):** Installed CLI 1.0.88 noninteractive smoke produced no hook audit
  record. Do not claim repository hooks loaded. Use the explicit tool restrictions
  in `scripts/agent-run.sh`; demonstrate policy decisions directly until actual
  CLI hook loading is confirmed.
- Agent identity signals were verified on public cloud-agent PRs (`gh`:
  `app/copilot-swe-agent`; REST: `Copilot`; commits: `copilot-swe-agent[bot]` with a
  `+Copilot@users.noreply.github.com` email). The `agent-authored` label and Copilot
  co-author trailers cover local CLI contributions. An actor who strips all
  provenance cannot be identified infallibly by metadata.
- **TODO(verify):** CI, CodeQL and Dependency Review run PR-controlled workflow YAML
  on `pull_request`, so a PR could edit them or add a job with a required check's
  name. CODEOWNERS review of `.github/`, the agent gate's protected-path rule and the
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
