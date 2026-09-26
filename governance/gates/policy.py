import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

PROTECTED = (
    ".github/",
    "governance/",
    ".specify/",
    "scripts/",
    "AGENTS.md",
    "pyproject.toml",
    "uv.lock",
)
TASK = re.compile(r"\bT\d{3}\b")
SPEC = re.compile(r"\bspec:(\d{3})\b")


@dataclass(frozen=True)
class Change:
    path: str
    previous_path: str = ""


@dataclass
class PullRequest:
    author: str
    title: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    files: list[Change] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    commits: list[str] = field(default_factory=list)
    linked_issues: list[int] = field(default_factory=list)


def protected(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in PROTECTED)


def paths(pr: PullRequest) -> list[str]:
    return [p for change in pr.files for p in (change.path, change.previous_path) if p]


def trace(pr: PullRequest, specs: dict[str, str]) -> list[str]:
    source = [p for p in paths(pr) if p.startswith("src/") and p.endswith(".py")]
    if not source:
        return []
    errors: list[str] = []
    refs = set(SPEC.findall(pr.title + "\n" + pr.body))
    tasks = set(TASK.findall(pr.title + "\n" + pr.body))
    if not refs:
        errors.append("Source changes must reference spec:NNN")
    if not tasks:
        errors.append("Source changes must reference at least one task ID")
    for ref in refs:
        if ref not in specs:
            errors.append(f"Unknown spec:{ref}")
        elif not tasks.intersection(TASK.findall(specs[ref])):
            errors.append(f"No referenced task exists in spec:{ref}")
    valid_tasks = {task for ref in refs for task in TASK.findall(specs.get(ref, ""))}
    for task in tasks - valid_tasks:
        errors.append(f"Unknown task: {task}")
    for path in source:
        stem = PurePosixPath(path).stem
        if stem == "__init__":
            continue
        expected = f"tests/test_{stem}.py"
        if expected not in paths(pr):
            errors.append(f"{path} requires corresponding test change: {expected}")
    return errors


def is_agent(pr: PullRequest) -> bool:
    return (
        pr.author.lower() in {"copilot", "copilot[bot]", "copilot-swe-agent[bot]"}
        or "agent-authored" in pr.labels
        or any(re.search(r"(?im)^Co-authored-by:\s*Copilot\b", c) for c in pr.commits)
    )


def risk(pr: PullRequest) -> str:
    if any(protected(p) or re.search(r"(^|/)(auth|crypto)(/|\.|$)", p) for p in paths(pr)):
        return "high"
    return "medium" if any(p.startswith("src/") for p in paths(pr)) else "low"


def agent_policy(pr: PullRequest, max_lines: int = 400) -> list[str]:
    errors: list[str] = []
    if not is_agent(pr):
        return errors
    if not pr.linked_issues:
        errors.append("Agent PR requires a linked issue")
    if not any(re.fullmatch(r"spec:\d{3}", label) for label in pr.labels):
        errors.append("Agent PR requires a spec:NNN label")
    if pr.additions + pr.deletions > max_lines:
        errors.append(f"Agent diff exceeds {max_lines} changed lines")
    forbidden = [p for p in paths(pr) if protected(p)]
    if forbidden:
        errors.append("Agent changed protected paths: " + ", ".join(forbidden))
    return errors
