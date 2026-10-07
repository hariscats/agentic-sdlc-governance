"""Copilot CLI preToolUse hook, configured in .github/hooks/governance.json.

Copilot runs ``python3 -I -S guardrails/hook.py preToolUse`` outside the project venv,
so this file and policy.py use only the stdlib and stay Python 3.9-compatible.
Any error fails closed with a deny.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if not __package__:
    # -I keeps the script directory off sys.path and -S skips site-packages. Append the
    # repository last, after the stdlib, so agent-created json.py/hashlib.py can't shadow it.
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from guardrails.policy import ROOT, evaluate  # noqa: E402


def handle(event: str, payload: Any, root: Path = ROOT) -> dict[str, str]:
    if event != "preToolUse":
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Hook payload must be an object")
    args = payload.get("toolArgs", {})
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict):
        raise ValueError("toolArgs must be an object")
    decision = evaluate(str(payload.get("toolName", "")), args, root)
    return {"permissionDecision": decision.decision, "permissionDecisionReason": decision.reason}


def main() -> None:
    try:
        result = handle(sys.argv[1], json.load(sys.stdin))
    except (ValueError, OSError, IndexError, TypeError) as exc:
        failure = f"Guardrails hook failed: {type(exc).__name__}"
        print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": failure}))
        raise SystemExit(1) from exc
    print(json.dumps(result))


if __name__ == "__main__":
    main()
