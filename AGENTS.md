# Agent boundaries

This is a fictional, localhost-only permit API. Never use real PII or secrets.
Every source change must trace to an existing task in specs/NNN-*/tasks.md.
Commit form: `feat(T012): description [spec:001]`.
PRs must include spec:NNN and task IDs; agent PRs also need a linked issue and spec label.

Agents must not edit .github/, governance/, scripts/, .specify/, AGENTS.md,
pyproject.toml, or uv.lock; repository hooks allow edits only under src/, tests/ and specs/.
Platform changes are proposed for independent human review.
Never bypass a rule, approval, scanner, test, or audit log. Never force-push or
direct-push main. Do not mark unavailable controls successful.

Feature 001 is the setup feature. Feature 002 stays unimplemented until the live demo.
Use Python 3.12, parameterized SQL, explicit validation, tests before code,
and `uv run --frozen pytest`. CLI wrapper shell restrictions are deliberate.
Hooks and instructions are defense in depth, not an OS-level sandbox.
