import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from governance.gates.policy import protected

ROOT = Path(__file__).resolve().parents[1]
SAFE_COMMANDS = {
    "git status --short",
    "git diff",
    "git diff --stat",
    "git log -5 --oneline",
    "uv run --frozen pytest",
    "uv run --frozen pytest tests",
    "uv run --frozen ruff check src tests",
    "uv run --frozen mypy src",
}


def decision(tool: str, args: dict[str, Any], root: Path = ROOT) -> tuple[str, str]:
    if tool in {"bash", "powershell", "shell", "Bash"}:
        command = args.get("command", "")
        if command not in SAFE_COMMANDS:
            return "deny", "Only fixed read-only git and test commands are permitted"
        return "allow", "Approved bounded command; tests still require an isolated runner"
    if tool in {"task", "agent", "web_fetch", "web_search"} or "mcp" in tool.lower():
        return "deny", "Delegation and external tools require a separately reviewed policy"
    edits = {"create", "edit", "write", "str_replace", "str_replace_editor", "Write", "Edit"}
    reads = {"view", "read", "glob", "grep", "rg", "Read", "Glob", "Grep"}
    if tool in edits | reads:
        values = args.get("paths", args.get("path", args.get("file_path")))
        if values is None and tool in reads:
            values = "."
        if not isinstance(values, (str, list)):
            return "deny", "Missing or unsupported path argument"
        for value in [values] if isinstance(values, str) else values:
            if not isinstance(value, str):
                return "deny", "Invalid path"
            resolved = (root / value).resolve()
            if not resolved.is_relative_to(root.resolve()):
                return "deny", "Access outside the repository is prohibited"
            relative = resolved.relative_to(root.resolve()).as_posix()
            if any(
                part in {".git", ".agent-audit"} or part.startswith(".env")
                for part in resolved.parts
            ):
                return "deny", "Credential, audit, and git metadata access is prohibited"
            if tool in edits and protected(relative):
                return "deny", "Protected path requires human platform/security review"
        return "allow", "Repository-scoped path"
    if tool in {"ask_user", "update_todo", "report_progress", "task_complete"}:
        return "allow", "Non-executing collaboration tool"
    return "deny", "Unknown tool or patch format; use a reviewed path-scoped edit tool"


def handle(event: str, payload: dict[str, Any], root: Path = ROOT) -> dict[str, str]:
    args = payload.get("toolArgs", {})
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict):
        raise ValueError("toolArgs must be an object")
    tool = str(payload.get("toolName", ""))
    outcome, reason = decision(tool, args, root) if event == "preToolUse" else ("observed", "")
    audit = root / ".agent-audit"
    if audit.is_symlink():
        raise ValueError("Audit directory must not be a symlink")
    audit.mkdir(mode=0o700, exist_ok=True)
    session = hashlib.sha256(str(payload.get("sessionId", "unknown")).encode()).hexdigest()[:20]
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session": session,
        "event": event,
        "tool": re.sub(r"[^a-zA-Z0-9_.-]", "_", tool)[:100],
        "args_sha256": hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest(),
        "decision": outcome,
    }
    log = audit / f"{session}.jsonl"
    if log.is_symlink():
        raise ValueError("Audit file must not be a symlink")
    fd = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(record) + "\n").encode())
    finally:
        os.close(fd)
    return (
        {"permissionDecision": outcome, "permissionDecisionReason": reason}
        if event == "preToolUse"
        else {}
    )


def main() -> None:
    try:
        result = handle(sys.argv[1], json.load(sys.stdin))
    except (ValueError, OSError, IndexError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Governance hook failed: {type(exc).__name__}",
                }
            )
        )
        raise SystemExit(1) from exc
    print(json.dumps(result))


if __name__ == "__main__":
    main()
