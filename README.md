# Guardrails-as-Code: Governed Permit Intake

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

## Demo in 10 minutes

```bash
uv sync --frozen
uv run --frozen python -m scripts.rehearse --pause
```

This runs three beats in about a second and changes nothing on GitHub:

1. **The agent can't go rogue.** The real hook wrapper denies disabling CI, pipe-to-shell,
   reading `~/.ssh` and a stdlib-shadowing bypass, and allows the in-scope edit.
   Every decision is audited in `.agent-audit/`.
2. **Gates catch what slips through.** A 401-line cloud-agent PR with no spec, task
   or issue is blocked by both custom gates, and the actual seeded SQL-injection
   patch fails CI. This runs in a temporary copy only.
3. **Proof, not promises.** The rehearsal builds a source ZIP, SPDX inventory,
   checksums and an evidence pack in `dist/v0.1.0-demo/`. Refresh the dashboard with
   `uv run --frozen python -m metrics.collector --live-flow`, then open
   `dashboard/index.html`. The dashboard's Copilot usage is labelled
   **SYNTHETIC DATA**, and local checksums are **not signed attestations**.
   [DEMO.md](DEMO.md) shows live `gh attestation verify` against the signed build.

[DEMO.md](DEMO.md) has the talk track and fallbacks, plus an extended 30-minute runbook.

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
closed as superseded. The first merge could not pass gates that run from `main`, so
it went through a single logged, PR-only bypass. The ruleset was then restored to
zero bypass actors (see [BUILD-LOG](docs/BUILD-LOG.md)). Hosted CI, CodeQL, dependency
review, metrics, and native provenance/SPDX verification of a `main` build have run
successfully.
The original Spec Kit generated assets in `.specify/` and `.github/skills/`
are covered by the upstream [MIT notice](.specify/LICENSE).

Start with [the demo runbook](DEMO.md), [architecture](docs/ARCHITECTURE.md),
[control mapping](docs/CONTROL-MAPPING.md), and [build evidence](docs/BUILD-LOG.md).
