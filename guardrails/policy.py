"""Single source of truth for what an agent may touch. Nothing here executes a command.

The hook runs this under the system ``python3 -I -S`` (no venv, stdlib only), so it must
stay compatible with Python 3.9.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Agent edit allowlist shared by the hook and the Agent PR Policy Gate. Exact case on
# purpose: anything else (root modules, .venv, conftest.py, SRC/) is denied.
EDITABLE = ("src/", "tests/", "specs/")
# Platform paths, matched case-insensitively: macOS/Windows resolve GUARDRAILS/ too.
PROTECTED = (".github/", "guardrails/", "demo/", "Makefile", "pyproject.toml", "uv.lock")
SAFE_COMMANDS = frozenset(
    {
        "git status --short",
        "git diff",
        "git diff --stat",
        "git log -5 --oneline",
        "uv run --frozen pytest",
        "uv run --frozen pytest tests",
        "uv run --frozen ruff check src tests",
    }
)
SHELL_TOOLS = {"bash", "powershell", "shell", "Bash"}
EDIT_TOOLS = {"create", "edit", "write", "str_replace", "str_replace_editor", "Write", "Edit"}
READ_TOOLS = {"view", "read", "glob", "grep", "rg", "Read", "Glob", "Grep"}
COLLABORATION_TOOLS = {"ask_user", "update_todo", "report_progress", "task_complete"}


@dataclass(frozen=True)
class Decision:
    tool: str
    target: str  # sha256 of the arguments; raw arguments are never stored
    decision: str  # "allow" or "deny"
    reason: str


def protected(path: str) -> bool:
    folded = path.casefold()
    return any(folded.startswith(prefix.casefold()) for prefix in PROTECTED)


def _verdict(tool: str, args: dict[str, Any], root: Path) -> tuple[str, str]:
    if tool in SHELL_TOOLS:
        command = args.get("command")
        if not isinstance(command, str) or command not in SAFE_COMMANDS:
            return "deny", "Only fixed read-only git and test commands are permitted"
        return "allow", "Approved bounded command; tests still require an isolated runner"
    if tool in {"task", "agent", "web_fetch", "web_search"} or "mcp" in tool.lower():
        return "deny", "Delegation and external tools require a separately reviewed policy"
    if tool in EDIT_TOOLS | READ_TOOLS:
        values = args.get("paths", args.get("path", args.get("file_path")))
        if values is None and tool in READ_TOOLS:
            values = "."
        if not isinstance(values, (str, list)) or not values:
            return "deny", "Missing or unsupported path argument"
        for value in [values] if isinstance(values, str) else values:
            if not isinstance(value, str) or not value.strip():
                return "deny", "Invalid path"
            resolved = (root / value).resolve()
            if not resolved.is_relative_to(root.resolve()):
                return "deny", "Access outside the repository is prohibited"
            relative = resolved.relative_to(root.resolve()).as_posix()
            parts = [part.casefold() for part in PurePosixPath(relative).parts]
            if any(p in {".git", ".agent-audit"} or p.startswith(".env") for p in parts):
                return "deny", "Credential, audit, and git metadata access is prohibited"
            if tool in EDIT_TOOLS and protected(relative):
                return "deny", "Protected path requires human platform/security review"
            if tool in EDIT_TOOLS and not relative.startswith(EDITABLE):
                return "deny", "Agents may edit only src/, tests/ and specs/"
        return "allow", "Repository-scoped path"
    if tool in COLLABORATION_TOOLS:
        return "allow", "Non-executing collaboration tool"
    return "deny", "Unknown tool or patch format; use a reviewed path-scoped edit tool"


def decide(tool: str, args: dict[str, Any], root: Path = ROOT) -> Decision:
    """Pure policy decision for one tool call."""
    outcome, reason = _verdict(tool, args, root)
    digest = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", tool)[:100]
    return Decision(name, "sha256:" + digest, outcome, reason)


def audit(decision: Decision, root: Path = ROOT) -> None:
    """Append one JSON line per decision to .agent-audit/session.jsonl."""
    directory = root / ".agent-audit"
    if directory.is_symlink():
        raise ValueError("Audit directory must not be a symlink")
    directory.mkdir(mode=0o700, exist_ok=True)
    log = directory / "session.jsonl"
    if log.is_symlink():
        raise ValueError("Audit file must not be a symlink")
    record = {
        # timezone.utc, not datetime.UTC: the hook may run on a pre-3.11 system python3.
        "ts": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "tool": decision.tool,
        "target": decision.target,
        "decision": decision.decision,
        "reason": decision.reason,
    }
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(log, flags, 0o600)
    try:
        os.write(fd, (json.dumps(record) + "\n").encode())
    finally:
        os.close(fd)


def evaluate(tool: str, args: dict[str, Any], root: Path = ROOT) -> Decision:
    """Decide and audit one tool call. Never executes anything."""
    decision = decide(tool, args, root)
    audit(decision, root)
    return decision
