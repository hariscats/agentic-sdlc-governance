import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from governance.gates.policy import Change, PullRequest, agent_policy, risk, trace


def git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True)


def evaluate(
    mode: str, metadata: dict[str, Any], candidate: Path, base: str, head: str
) -> tuple[list[str], str]:
    if not all(re.fullmatch(r"[a-f0-9]{40}", sha) for sha in (base, head)):
        raise ValueError("Expected exact Git commit SHAs")
    if metadata["headRefOid"] != head:
        raise ValueError("PR head changed during evaluation; rerun required")
    names = git("diff", "--name-only", "--no-renames", "-z", f"{base}...{head}", cwd=candidate)
    pr = PullRequest(
        author=metadata["author"]["login"],
        title=metadata["title"],
        body=metadata["body"] or "",
        labels=[entry["name"] for entry in metadata["labels"]],
        files=[Change(p) for p in names.split("\0") if p],
        additions=metadata["additions"],
        deletions=metadata["deletions"],
        linked_issues=[entry["number"] for entry in metadata["closingIssuesReferences"]],
        commits=[git("log", "--format=%B", f"{base}..{head}", cwd=candidate)],
    )
    specs: dict[str, str] = {}
    for path in git(
        "ls-tree", "-r", "--name-only", head, "--", "specs", cwd=candidate
    ).splitlines():
        match = re.fullmatch(r"specs/(\d{3})-[^/]+/tasks\.md", path)
        if match:
            if match[1] in specs:
                raise ValueError("Ambiguous duplicate spec number")
            specs[match[1]] = git("show", f"{head}:{path}", cwd=candidate)
    errors = trace(pr, specs) if mode == "trace" else agent_policy(pr)
    computed = risk(pr)
    if mode == "agent" and computed == "high":
        config = json.loads(Path("governance/config.json").read_text())
        latest = {
            review["user"]["login"]: review
            for review in metadata.get("_reviews", [])
            if review.get("user") and review["state"] != "PENDING"
        }
        approvals = {
            login
            for login, review in latest.items()
            if review["state"] == "APPROVED" and review["commit_id"] == head and login != pr.author
        }
        if not approvals.intersection(config["security_owners"]):
            errors.append("High risk requires an independent SECURITY owner approval")
    return errors, computed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["trace", "agent"])
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    if args.reviews:
        metadata["_reviews"] = json.loads(args.reviews.read_text())
    errors, computed = evaluate(args.mode, metadata, args.candidate, args.base, args.head)
    report = {
        "gate": args.mode,
        "risk": computed,
        "status": "fail" if errors else "pass",
        "errors": errors,
        "head": args.head,
    }
    print(json.dumps(report, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as stream:
            stream.write(f"### {args.mode}: {report['status']}\n\n")
            stream.write("Risk: " + computed + "\n\n")
            stream.write("\n".join("- " + e.replace("<", "&lt;") for e in errors) + "\n")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
