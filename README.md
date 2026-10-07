# Guardrails-as-Code: live governance demo

> [!WARNING]
> **Demo only.** This repository is for teaching and presentations. It is not production
> software, not an accredited system and not evidence of compliance with any framework.
> Permit data is fictional. Never add real personal information, credentials or agency data.

An AI agent tries to ship a change, and a live console shows guardrails stopping it in real
time. The permit API in `src/app.py` is deliberately tiny: it is only the agent's edit target.

## What the demo proves

1. **Hook:** every agent tool call is allowed or denied by policy, and audited with hashed arguments.
2. **Gates:** a bad PR (no spec link, too large, SQL injection) is blocked.
3. **Proof:** a signed release artifact verifies, and a tampered copy fails.

## Quickstart

```bash
uv sync --frozen
make demo      # opens the console on http://127.0.0.1:8001
```

`make test` runs the tests and `make reset` clears local demo state.
[DEMO.md](DEMO.md) is the presenter script.

## How it fits together

| Path | Role |
|---|---|
| `guardrails/policy.py` | Allowlist and protected paths: the single source of truth |
| `guardrails/hook.py` | Copilot CLI hook, loaded from `.github/hooks/governance.json` |
| `guardrails/gates.py` | `spec-link` and `size` gates, run from `main` by `.github/workflows/gates.yml` |
| `demo/run.py` | The three scenes; every step is a real decision, test, gate run or verification |
| `demo/console/` | FastAPI and server-sent events console; plain HTML, works offline |

The full reference implementation (Spec Kit, metrics, evidence packs and docs) is preserved
at the [`full-reference`](https://github.com/hariscats/agentic-sdlc-governance/tree/full-reference) tag.
