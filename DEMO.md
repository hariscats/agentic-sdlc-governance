# Presenter script (10 minutes)

## Setup: two minutes before, while online

```bash
uv sync --frozen
make reset && uv run --frozen python -m demo.run --scene 3   # fetch and verify the signed artifact now
make demo                                                    # opens http://127.0.0.1:8001
```

## Scenes

| Scene | Click | Say | If it breaks |
|---|---|---|---|
| **1. The agent can't go rogue** (3 min) | **Scene 1**, then type `rm -rf src/` into *Try a command* | "Shell is an allowlist, not a denylist. Every decision is audited, with arguments hashed, never stored." | Run `uv run --frozen python -m demo.run --scene 1` in a terminal. |
| **2. Gates catch what slips through** (3 min) | **Scene 2** | "The seeded SQL injection fails CI, and an oversized agent PR with no spec link is blocked by the same gate code that judges every PR, from `main`. A PR can't rewrite its own gate." | Run `uv run --frozen python -m demo.run --scene 2` in a terminal. |
| **3. Proof, not promises** (2.5 min) | **Scene 3**, then **Verify tampered** | "The release workflow signed this build on `main`. Change one byte and verification fails." | Offline, the console shows the comparison labelled **checksum, not signature**. |
| **Close** (30 s) | Point at the counters | "One policy for local and cloud agents, gates that run from `main`, and proof anyone can verify." | — |

Optional live agent: in a folder Copilot CLI trusts, run `copilot` and ask it to edit
`.github/workflows/ci.yml`. Its hook decisions appear on the console as they happen.

If the artifact download fails, its 90-day retention may have expired. Run
`gh workflow run release.yml --ref main`, wait for the run to finish, then repeat setup.

## What this does not show

- The hook is a policy check on tool calls, not an OS sandbox.
- No human approval or production release is claimed, so the **Human** node stays grey.
- The offline fallback compares a checksum, which is not a signature.
