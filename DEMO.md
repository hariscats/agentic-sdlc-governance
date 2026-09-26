# Presenter runbook

**Start with the 10-minute demo.** It needs only a terminal and a browser, changes
nothing on GitHub, and takes about 1 second to run. The
[extended 30-minute runbook](#extended-30-minute-runbook) adds live agents,
approvals and a real release.

## 10-minute demo: three scenes

**Two minutes before you start:**

```bash
uv sync --frozen
uv run --frozen python -m metrics.collector --live-flow   # refresh dashboard flow metrics
run=$(gh run list --repo hariscats/agentic-sdlc-governance --workflow release.yml \
  --branch build/governance-reference --status success --limit 1 --json databaseId --jq '.[0].databaseId')
gh run download "$run" --repo hariscats/agentic-sdlc-governance -n release-candidate -D /tmp/proof
```

Open two browser tabs: [PR #7's checks](https://github.com/hariscats/agentic-sdlc-governance/pull/7/checks)
and the [`main-protection` ruleset](https://github.com/hariscats/agentic-sdlc-governance/rules).

Then run the demo, pressing Enter between beats:

```bash
uv run --frozen python -m scripts.rehearse --pause
```

| Scene | Min | What happens | Talk track |
|---|---:|---|---|
| **1. The agent can't go rogue** | 3 | Beat 1: an agent tries to turn off CI, pipe a script to a shell, read an SSH key and plant `json.py` to trick the hook. All four are **DENIED** by the real hook wrapper; only the in-scope `src/app.py` edit is **ALLOWED**. Then run `tail -n 3 .agent-audit/*.jsonl`. | "The same hook file the Copilot CLI loads makes these decisions. Shell is an allow list, not a deny list. Every decision is audited, with arguments hashed rather than stored." |
| **2. Gates catch what slips through** | 4 | Beat 2: a 401-line cloud-agent PR with no spec, task, issue or tests is **BLOCKED** by both custom gates, and the seeded SQL-injection patch fails CI. Switch to PR #7's checks for the real CodeQL high alert and gate failures, then to the ruleset: required checks, code-owner review, signed commits, **no bypass actors**. | "Humans and agents face the same gates. The trusted gates run from `main`, so a PR cannot rewrite its own gate. Even this demo's own build PR (#6) is waiting for an independent reviewer." |
| **3. Proof, not promises** | 3 | Beat 3 builds the evidence pack. Then run the two verify commands below: the real build passes and one appended byte fails. Finally run `open dashboard/index.html`. | "Provenance is signed by the release workflow, not asserted in a slide. The usage panel is clearly labelled SYNTHETIC; flow metrics can be live." |

Scene 3 commands:

```bash
gh attestation verify /tmp/proof/permit-intake.zip --repo hariscats/agentic-sdlc-governance \
  --signer-workflow hariscats/agentic-sdlc-governance/.github/workflows/release.yml
cp /tmp/proof/permit-intake.zip /tmp/proof/tampered.zip && printf x >> /tmp/proof/tampered.zip
gh attestation verify /tmp/proof/tampered.zip --repo hariscats/agentic-sdlc-governance   # fails
```

**If something is slow:**
- If Wi-Fi fails, run scenes 1–3 locally without the browser tabs.
- If the artifact download fails, skip the verify commands and open the evidence pack in `dist/v0.1.0-demo/`.
- The rehearsal fails loudly if any control stops working. Never paper over that.

**Be precise about what this shows.**
- Scene 1 is the hook policy, not an OS sandbox.
- The signed artifact comes from the build-branch rehearsal, not an approved `main` release.
- Push protection for the custom `DEMOSECRET_` pattern and Copilot Autofix are not shown until they are configured. See docs/SETUP-MANUAL.md.

Reset: `rm -rf /tmp/proof`. The quick demo creates nothing on GitHub.

## Extended 30-minute runbook

### Before presenting

Read docs/SETUP-MANUAL.md. Do not present a pending control as working.
The bootstrap PR must be independently accepted and the trust root installed on main
before scenes involving normal gated PRs, cloud setup, or releases.
Resolve cloud-agent audit drift and configure the custom secret pattern.
Use two independent authorized humans for approvals.

```bash
uv sync --frozen
uv run --frozen pytest --cov
uv run --frozen python -m scripts.rehearse
bash scripts/audit-cloud-agent-config.sh
```

| Scene | Minutes | Exact actions / expected result / fallback |
|---|---:|---|
| 1. Governed intent | 4 | Open `.specify/memory/constitution.md`, `specs/002-permit-review/analysis.md` and tasks.md. Show required architecture approval in the PR UI. Talk track: an agent executes approved intent, not its own scope. If bootstrap is pending, label the scene BLOCKED. |
| 2. Bounded local agent | 5 | Use the commands below; show scoped edits and JSONL decisions. Talk track: CLI permissions plus hooks, backed by PR checks. If CLI is slow, use the deterministic hook rehearsal and say it is a policy-unit demonstration. |
| 3. Cloud agent, same gates | 4 | Choose one `spec:002`, `agent-ready` issue in GitHub; assign Copilot. Approve its workflow run after inspecting it. Show session link and verified signature badges. Do not claim a session ran unless the UI shows it. Slow fallback: retain the assigned issue and show the setup/config audit instead. |
| 4. Negative gates | 6 | Apply the seeded patch on a throwaway demo branch, show test failure and CodeQL finding; use Autofix only when actually offered. Show missing spec/task and oversized-agent failures. Custom secret exercise below requires verified pattern setup. Fallback: local rehearsal demonstrates tests/policies, not native CodeQL/push protection. |
| 5. Humans decide | 3 | Independent codeowner reviews latest push. Demonstrate that PR author and cloud requester cannot supply required self-approval. Inspect production environment prevention. A blocked PR is the correct result without a reviewer. |
| 6. Provable release | 5 | Dispatch release.yml on main. Inspect staging, native verification, then obtain independent production approval. Download release SPDX and evidence ZIP. Slow fallback: local bundle is explicitly unsigned and not a successful native release. |
| 7. Outcomes and reset | 3 | Open the static dashboard; point at SYNTHETIC DATA versus live flow. Run config audit, then preview and apply scoped reset. |

### Scene 2 commands

```bash
git switch -c demo/local-task
bash scripts/agent-run.sh implementer \
  'Read spec:002 and propose the T020 test change only. Do not implement the decision endpoint.'
uv run --frozen pytest
```

Use `uv run --frozen python -m scripts.rehearse` to exercise denied protected edits and
pipe-to-shell commands through the real hook wrapper without executing either. Inspect `.agent-audit/*.jsonl` locally;
do not publish the whole directory. The wrapper denies shell even when execute is in
the agent profile; the presenter runs tests.

### Scene 4 commands

On a clean demo branch **after the base project is installed**:

```bash
git switch -c demo/seeded-vuln
git apply demo/patches/seeded-vuln.patch
uv run --frozen pytest tests/test_app.py
```

Expected: the injection assertion fails. Do not deploy the vulnerable application.
Create a labelled `demo` PR with an actual linked issue, spec:001 and T012.
Commit/push only the deliberately vulnerable source change, never secrets.
In CodeQL, inspect the tainted SQL finding and request Autofix if available.
Revert the patch with `git apply -R demo/patches/seeded-vuln.patch`, rerun tests,
and submit a new commit rather than rewriting history.

For the secret scene, use `python3 scripts/demo-secret.py` to generate a value at runtime.
Use a **disposable demo worktree/branch** and a temporary file. A GitHub administrator
must first verify that the custom pattern is active. Attempt the push; expect rejection.
Never bypass protection. A local secret detector is not proof of server rejection.
Do not run this exercise until that manual prerequisite is confirmed, and never put
a real-provider token into the demo.

### Scene 6 commands

```bash
gh workflow run release.yml --repo hariscats/agentic-sdlc-governance --ref main -f version=v0.1.0
gh run list --repo hariscats/agentic-sdlc-governance --workflow release.yml --limit 5
```

The run must stop at production approval. The user who starts it cannot also approve it.
Verification in the workflow checks both SLSA provenance and SPDX predicate.
After downloading the artifact, the equivalent provenance check is:

```bash
gh attestation verify permit-intake.zip --repo hariscats/agentic-sdlc-governance \
  --signer-workflow hariscats/agentic-sdlc-governance/.github/workflows/release.yml \
  --source-ref refs/heads/main --deny-self-hosted-runners
```

The build-branch rehearsal verifies real attestations and intentionally rejects
them as main provenance, without entering either environment. It is evidence for
the cryptographic portion only, not a replacement for this approved-release scene.

### Recorded setup rehearsal

See BUILD-LOG for run URLs and reset results. PR #7, targeting the unmerged build
branch, demonstrated a high CodeQL SQL injection alert, the failing regression test,
and trace/agent policy denials. The unsafe patch was reversed manually; no Autofix
or custom-pattern push rejection is claimed. The trace and agent gates now run on
`pull_request_target` from `main`, so after the bootstrap merge they evaluate PRs
into `main` only; a PR into the build branch no longer exercises them.

### Scene 7 and reset

```bash
uv run --frozen python -m metrics.collector --live-flow
bash scripts/reset-demo.sh
bash scripts/reset-demo.sh --apply
```

Reset closes only labelled demo PRs whose same-repository branch matches `demo/*`,
deletes those PR branches, and reopens labelled demo spec-002 issues. It does not
delete releases, rewrite main, uncheck approved tasks, or revert merged Feature 002.
Keep live feature branches unmerged if a five-minute reset is required; reverting
a merged feature must go through an ordinary reviewed PR.
