"""PR gates: one CLI for CI and the demo.

    python3 -m guardrails.gates {spec-link,size} --metadata PR.json --candidate DIR \\
        --base SHA --head SHA

.github/workflows/gates.yml runs this from the default branch on pull_request_target.
PR commits are read as Git objects only: never checked out, imported or executed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from guardrails.policy import EDITABLE, protected

MAX_AGENT_LINES = 400
SPEC = re.compile(r"\bspec:(\d{3})\b")
SPEC_FILE = re.compile(r"specs/(\d{3})-[^/]+\.md")
# gh reports app authors as "app/<slug>"; REST reports the cloud agent as "Copilot".
AGENT_LOGINS = {"copilot", "copilot-swe-agent"}
AGENT_EMAIL = re.compile(r"\d+\+copilot@users\.noreply\.github\.com", re.IGNORECASE)
AGENT_TRAILER = re.compile(
    r"(?im)^Co-authored-by:\s*(?:Copilot\b|.*<\d+\+Copilot@users\.noreply\.github\.com>)"
)


@dataclass
class PullRequest:
    author: str
    title: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    changed_lines: int = 0
    commits: list[str] = field(default_factory=list)
    # Commit author/committer names and emails.
    identities: list[str] = field(default_factory=list)


def normalize_login(login: str) -> str:
    return login.strip().casefold().removeprefix("app/").removesuffix("[bot]")


def agent_identity(value: str) -> bool:
    value = value.strip()
    return normalize_login(value) in AGENT_LOGINS or bool(AGENT_EMAIL.fullmatch(value))


def is_agent(pr: PullRequest) -> bool:
    return (
        agent_identity(pr.author)
        or "agent-authored" in pr.labels
        or any(agent_identity(identity) for identity in pr.identities)
        or any(AGENT_TRAILER.search(message) for message in pr.commits)
    )


def spec_link(pr: PullRequest, specs: set[str]) -> list[str]:
    """Source changes must link a spec that already exists on the base branch."""
    if not any(path.startswith("src/") for path in pr.paths):
        return []
    refs = set(SPEC.findall(pr.title + "\n" + pr.body))
    if not refs:
        return ["Source changes must reference spec:NNN"]
    return [f"Unknown spec:{ref}" for ref in sorted(refs) if ref not in specs]


def size(pr: PullRequest, max_lines: int = MAX_AGENT_LINES) -> list[str]:
    """Agent PRs stay small and inside the same allowlist the hook enforces."""
    if not is_agent(pr):
        return []
    errors: list[str] = []
    if pr.changed_lines > max_lines:
        errors.append(f"Agent diff exceeds {max_lines} changed lines ({pr.changed_lines})")
    forbidden = [path for path in pr.paths if protected(path)]
    if forbidden:
        errors.append("Agent changed protected paths: " + ", ".join(forbidden))
    outside = [p for p in pr.paths if not protected(p) and not p.startswith(EDITABLE)]
    if outside:
        errors.append("Agent changed paths outside src/, tests/, specs/: " + ", ".join(outside))
    return errors


def git(candidate: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=candidate, text=True)


def load(
    metadata: dict[str, Any], candidate: Path, base: str, head: str
) -> tuple[PullRequest, set[str]]:
    if not all(re.fullmatch(r"[a-f0-9]{40}", sha) for sha in (base, head)):
        raise ValueError("Expected exact Git commit SHAs")
    if metadata["headRefOid"] != head:
        raise ValueError("PR head changed during evaluation; rerun required")
    names = git(candidate, "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}")
    changed = 0
    numstat = git(candidate, "diff", "--numstat", "--no-renames", f"{base}...{head}")
    for line in numstat.splitlines():
        added, deleted, _ = line.split("\t", 2)
        changed += sum(int(count) for count in (added, deleted) if count != "-")
    identities = git(
        candidate, "log", "--format=%an%x00%ae%x00%cn%x00%ce%x00", f"{base}..{head}"
    ).split("\0")
    pr = PullRequest(
        author=metadata["author"]["login"],
        title=metadata["title"],
        body=metadata["body"] or "",
        labels=[entry["name"] for entry in metadata["labels"]],
        paths=[path for path in names.split("\0") if path],
        changed_lines=changed,
        commits=[git(candidate, "log", "--format=%B", f"{base}..{head}")],
        identities=[value.strip() for value in identities if value.strip()],
    )
    # Specs come from the base: a spec must exist before the change that cites it.
    specs: set[str] = set()
    listing = git(candidate, "ls-tree", "-r", "--name-only", base, "--", "specs")
    for path in listing.splitlines():
        match = SPEC_FILE.fullmatch(path)
        if match:
            if match[1] in specs:
                raise ValueError("Ambiguous duplicate spec number")
            specs.add(match[1])
    return pr, specs


def evaluate(
    gate: str, metadata: dict[str, Any], candidate: Path, base: str, head: str
) -> list[str]:
    pr, specs = load(metadata, candidate, base, head)
    return spec_link(pr, specs) if gate == "spec-link" else size(pr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python3 -m guardrails.gates")
    parser.add_argument("gate", choices=["spec-link", "size"])
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    metadata = json.loads(args.metadata.read_text())
    errors = evaluate(args.gate, metadata, args.candidate, args.base, args.head)
    status = "fail" if errors else "pass"
    report = {"gate": args.gate, "status": status, "errors": errors, "head": args.head}
    print(json.dumps(report, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as stream:
            stream.write(f"### {args.gate}: {status}\n\n")
            stream.write("\n".join("- " + error.replace("<", "&lt;") for error in errors) + "\n")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
