import json
import re
from pathlib import Path
from typing import Any

from governance.gates.policy import PullRequest, is_agent
from scripts.github_data import pull_requests


def project(pr: dict[str, Any]) -> dict[str, Any]:
    """Keep only audit facts; drop review bodies, commit messages and author emails."""
    commits = pr.get("commits") or []
    return {
        "number": pr["number"],
        "title": pr["title"],
        "url": pr.get("url"),
        "mergedAt": pr.get("mergedAt"),
        "mergeCommit": (pr.get("mergeCommit") or {}).get("oid"),
        "headRefOid": pr.get("headRefOid"),
        "author": pr["author"]["login"],
        "labels": [label["name"] for label in pr.get("labels") or []],
        "agent_authored": is_agent(
            PullRequest(
                author=pr["author"]["login"],
                labels=[label["name"] for label in pr.get("labels") or []],
                commits=[c.get("messageBody") or "" for c in commits],
                identities=[
                    value
                    for c in commits
                    for a in c.get("authors") or []
                    for value in (a.get("login"), a.get("email"), a.get("name"))
                    if value
                ],
            )
        ),
        "reviews": [
            {
                "author": (r.get("author") or {}).get("login"),
                "state": r.get("state"),
                "submittedAt": r.get("submittedAt"),
            }
            for r in pr.get("reviews") or []
        ],
        "checks": [
            {
                "name": c.get("name") or c.get("context"),
                "conclusion": c.get("conclusion") or c.get("state"),
                "completedAt": c.get("completedAt"),
            }
            for c in pr.get("statusCheckRollup") or []
        ],
        "commits": [c.get("oid") for c in commits],
    }


def main() -> None:
    prs = pull_requests("merged")
    if len(prs) == 100:
        raise ValueError("Evidence limit reached; implement pagination before releasing")
    evidence = [project(pr) for pr in prs]
    Path(".demo-state").mkdir(exist_ok=True)
    Path(".demo-state/pr-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    groups: dict[str, list[str]] = {}
    for pr in evidence:
        refs = re.findall(r"\bspec:\d{3}\b", pr["title"])
        for ref in refs or ["governance"]:
            groups.setdefault(ref, []).append(f"- PR #{pr['number']}: {pr['title']}")
    Path(".demo-state/release-notes.md").write_text(
        "# Governed demo release\n\n"
        + "\n\n".join(f"## {key}\n" + "\n".join(value) for key, value in sorted(groups.items()))
    )


if __name__ == "__main__":
    main()
