# Guardrails-as-Code: Governed Permit Intake

> [!WARNING]
> **Strictly for demo purposes.** This repository is a reference demonstration for
> education and presentations. It is **not** production software, **not** an
> authorized or accredited system, and **not** evidence of compliance with NIST
> SP 800-53, FedRAMP or any other framework. Permit data and Copilot usage metrics
> are synthetic, the control mapping is illustrative, and deployments are simulated.
> Never add real personal information, credentials or agency data. It is provided
> as is, without warranty. Anyone adapting it must have their own security and
> compliance owners review it first.

A reference demo of **intent -> bounded agents -> automated gates -> human approval
-> governed release -> audit evidence and outcomes**, owned by
[`hariscats`](https://github.com/hariscats/agentic-sdlc-governance).

The application is deliberately small. The governance system is the product.
Feature 001 submits and retrieves fictional permits. Feature 002 is specified and
reserved for the live demo. No real personal information or credentials belong here.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync --frozen
uv run --frozen pytest --cov --cov-report=xml --junitxml=junit.xml
uv run --frozen uvicorn src.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000/docs. Submit a category (`building`, `event`,
`environmental`) and a synthetic description of 10-500 printable characters.
The API is **unauthenticated and loopback-only**, not a production agency service.

## Rerun the demo end to end

The three scenes take about 10 minutes, need only a terminal and a browser, and
change nothing on GitHub. The prep and reset steps do change GitHub: they close
labelled demo PRs, delete `demo/*` branches and relabel the spec-002 issues.
[DEMO.md](DEMO.md) has the full talk track, fallbacks and an extended 30-minute
runbook with live agents, approvals and a new release.

### 1. Prepare (about 10 minutes before)

```bash
git switch main && git pull --ff-only
uv sync --frozen
bash scripts/reset-demo.sh           # dry run: lists what would be closed or deleted
bash scripts/reset-demo.sh --apply   # changes GitHub: closes demo PRs, deletes demo branches
uv run --frozen python -m metrics.collector --live-flow   # refresh dashboard flow metrics
# Download the newest release candidate from a main run whose verify job passed.
# (The artifact is uploaded during build, before it is attested and verified.)
rm -rf /tmp/proof
for run in $(gh run list --repo hariscats/agentic-sdlc-governance --workflow release.yml \
  --branch main --limit 10 --json databaseId --jq '.[].databaseId'); do
  [ "$(gh run view "$run" --repo hariscats/agentic-sdlc-governance --json jobs \
    --jq '.jobs[] | select(.name=="verify") | .conclusion')" = success ] || continue
  gh run download "$run" --repo hariscats/agentic-sdlc-governance -n release-candidate \
    -D /tmp/proof 2>/dev/null && echo "verified release candidate from run $run" && break
done
```

If the loop prints nothing, no recent `main` run both passed `verify` and still has
its artifact (artifacts expire). Start a new release with
`gh workflow run release.yml --repo hariscats/agentic-sdlc-governance --ref main -f version=v0.1.1`
and rerun the loop once `verify` passes (about 3 minutes). The run then waits at
production approval, which is itself something to show.

For the extended live-agent scenes only, start `copilot` in the repository once and
trust the folder. The Copilot CLI loads repository hooks only in trusted folders.

### 2. Open these tabs

| Show | Where | What the audience sees |
|---|---|---|
| Outcomes dashboard | `open dashboard/index.html` | Live flow metrics: agent and other merges, lead time, time to first review, latest result per gate, Dependabot time to fix. The usage panel is labelled **SYNTHETIC DATA**. |
| Branch ruleset | [main-protection](https://github.com/hariscats/agentic-sdlc-governance/rules/24054367) | Five required checks, code-owner review, approval of the latest push, signed commits, CodeQL blocking and **no bypass actors** |
| Gates catching problems | [PR #7 checks](https://github.com/hariscats/agentic-sdlc-governance/pull/7/checks) | Failing custom gates and a real CodeQL high alert (`py/sql-injection`) |
| Agent boundary on a real PR | [PR #10 checks](https://github.com/hariscats/agentic-sdlc-governance/pull/10/checks) | The Agent PR Policy Gate failing on an agent-coauthored PR that changed workflow and governance files |
| A normal gated merge | [PR #9](https://github.com/hariscats/agentic-sdlc-governance/pull/9) | A Dependabot fix that passed all five checks before it merged |
| Release chain | [Release runs](https://github.com/hariscats/agentic-sdlc-governance/actions/workflows/release.yml) | build → attest → staging → verify, then **waiting** for production approval |
| Human approval | [Environments](https://github.com/hariscats/agentic-sdlc-governance/settings/environments) (admin only) | Production requires a reviewer, prevents self-review and deploys from `main` only |

Two terminal views help too:

```bash
tail -n 3 .agent-audit/*.jsonl   # agent audit trail, after scene 1
gh api "repos/hariscats/agentic-sdlc-governance/rulesets/rule-suites?ref=refs/heads/main&time_period=month" \
  --jq '.[] | select(.result=="bypass") | [.actor_name, .pushed_at, .after_sha[0:7]] | @tsv'   # every exception, logged
```

### 3. Run the three scenes

```bash
uv run --frozen python -m scripts.rehearse --pause   # press Enter between beats
```

1. **The agent can't go rogue (3 min).** The real hook wrapper denies disabling CI,
   pipe-to-shell, reading `~/.ssh` and a stdlib-shadowing bypass, and allows only the
   in-scope edit. Show the audit trail.
   *Say:* "Shell is an allow list, not a deny list. Every decision is audited, with
   arguments hashed rather than stored."
2. **Gates catch what slips through (4 min).** A 401-line cloud-agent PR with no
   spec, task or issue is blocked by both custom gates, and the seeded SQL-injection
   patch fails CI (in a temporary copy only). Switch to the PR #7, PR #10 and ruleset tabs.
   *Say:* "Humans and agents face the same gates. The gates run from `main`, so a
   PR can't rewrite its own gate. Even exceptions are on the record."
3. **Proof, not promises (3 min).** The rehearsal builds a source ZIP, SPDX
   inventory, checksums and an evidence pack in `dist/v0.1.0-demo/`. Local checksums
   are **not signed attestations**, so verify the real build from `main`, then a
   copy with one byte appended:

   ```bash
   gh attestation verify /tmp/proof/permit-intake.zip --repo hariscats/agentic-sdlc-governance \
     --signer-workflow hariscats/agentic-sdlc-governance/.github/workflows/release.yml \
     --source-ref refs/heads/main
   cp /tmp/proof/permit-intake.zip /tmp/proof/tampered.zip && printf x >> /tmp/proof/tampered.zip
   gh attestation verify /tmp/proof/tampered.zip --repo hariscats/agentic-sdlc-governance   # fails
   ```

   Finish on the dashboard and the release run waiting at production.
   *Say:* "Provenance is signed by the release workflow, not asserted in a slide.
   Nobody can approve their own release."

### 4. Explain the security and governance benefits

| Control | Security benefit | Governance benefit | NIST SP 800-53 (illustrative) |
|---|---|---|---|
| Spec and task traceability | No unplanned code reaches `main` | Every change maps to approved intent | CM-3, SA-15 |
| Agent hooks with an allow list and audit trail | Agents can't edit workflows, read credentials or pipe installs to a shell | Every tool decision is recorded | AC-5, AU-2, AU-12 |
| Gates that run from `main`, not the PR | A PR can't weaken its own checks | People and agents meet the same rules | CM-5, SA-11 |
| CodeQL, dependency review and signed commits | Vulnerable code and risky dependencies are blocked before merge | Policy enforces it, not reviewer memory | RA-5, SI-2, SR-4 |
| No bypass actors; exceptions logged | No silent overrides | Each exception records who, when and which commit | CM-5, AU-12 |
| Provenance and SBOM attestations | Tampering is detected | You can prove what shipped and where it came from | SI-7, SR-4 |
| Production approval with self-review prevented | Nobody ships their own change alone | Separation of duties | AC-5, CM-3 |

The message: **agents are fast, the guardrails are code, and the gates don't care
who wrote the change.** [CONTROL-MAPPING](docs/CONTROL-MAPPING.md) has the full,
illustrative mapping, which a compliance owner must validate.

### 5. Be upfront about the limits

- Copilot usage metrics are synthetic; flow metrics come from this repository.
- The hooks are a policy layer, not an operating-system sandbox.
- Production can't be approved until a second reviewer exists, which is by design.
- Push protection for the custom `DEMOSECRET_` pattern and Copilot Autofix aren't
  shown until they are configured ([SETUP-MANUAL](docs/SETUP-MANUAL.md)).

### 6. Reset

```bash
bash scripts/reset-demo.sh --apply   # closes labelled demo PRs and deletes demo/* branches
rm -rf /tmp/proof dist/v0.1.0-demo
git restore dashboard/index.html     # the refresh rewrites the committed dashboard
```

To clear a release run left waiting at production, run `gh run cancel <run-id>`.
Its artifact stays downloadable.

## Governance

| Surface | Implementation |
|---|---|
| Intent | Versioned constitution; two specs, clarifications, plans, checklists and tasks |
| Agents | Spec author, implementer, read-only reviewer and release-note drafter |
| Tool boundary | Repository hooks plus conservative CLI allowlists; not an OS sandbox |
| PR gates | CI, CodeQL, dependency review, spec trace and agent policy |
| Human boundary | CODEOWNERS, approval of latest push, production self-review prevention |
| Release | Main-only production path; isolated build-branch attestation rehearsal; SPDX and evidence |
| Evidence | Per-file hashes, specs/tasks, available PR approvals/checks and config drift report |
| Reset | Dry-run by default; only labelled demo PRs on `demo/*` and demo spec-002 issues |

The repository was made **public with explicit approval** to enable native GitHub
governance features. Company organizations, company telemetry and Azure are not used.
Rulesets have no bypass actors. A second independent reviewer and the custom demo
secret pattern are still tracked in [SETUP-MANUAL](docs/SETUP-MANUAL.md). Code and local tests are not proof that a
release or human approval has occurred.

The implementation merged to `main` in [PR #6](https://github.com/hariscats/agentic-sdlc-governance/pull/6).
The specification was first proposed in [PR #5](https://github.com/hariscats/agentic-sdlc-governance/pull/5),
closed as superseded. The first merge could not pass gates that run from `main`, and
the sole code owner cannot approve their own PR. So the owner's PRs, starting with
#6 and #10, merge through a logged, PR-only bypass, and the ruleset is restored to
zero bypass actors each time (see [BUILD-LOG](docs/BUILD-LOG.md)). This lasts until
a second reviewer exists. Hosted CI, CodeQL, dependency review, metrics, and native
provenance/SPDX verification of a `main` build have run successfully.
The original Spec Kit generated assets in `.specify/` and `.github/skills/`
are covered by the upstream [MIT notice](.specify/LICENSE).

Start with [the demo runbook](DEMO.md), [architecture](docs/ARCHITECTURE.md),
[control mapping](docs/CONTROL-MAPPING.md), and [build evidence](docs/BUILD-LOG.md).
