import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO = "hariscats/agentic-sdlc-governance"
DEMO_BRANCH = re.compile(r"demo/[a-z0-9][a-z0-9-]*")


def command(*args: str) -> str:
    return subprocess.check_output(["gh", *args, "--repo", REPO], text=True)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)


def local_demo_branches() -> tuple[list[str], str]:
    names = git("for-each-ref", "--format=%(refname:short)", "refs/heads/demo/").split()
    return [name for name in names if DEMO_BRANCH.fullmatch(name)], git(
        "branch", "--show-current"
    ).strip()


def plan(prs: list[dict[str, Any]], issues: list[dict[str, Any]]) -> list[list[str]]:
    actions: list[list[str]] = []
    for pr in prs:
        if (
            pr["state"] == "OPEN"
            and not pr["isCrossRepository"]
            and DEMO_BRANCH.fullmatch(pr["headRefName"])
        ):
            actions.append(["pr", "close", str(pr["number"]), "--delete-branch"])
    for issue in issues:
        if issue["state"] == "CLOSED":
            actions.append(["issue", "reopen", str(issue["number"])])
        actions.append(["issue", "edit", str(issue["number"]), "--add-label", "agent-ready"])
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run by default; only labelled demo resources")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    # Validate local cleanup targets before any remote mutation.
    state = Path(".demo-state")
    database = state / "permits.db"
    if args.apply and (state.is_symlink() or database.is_symlink()):
        raise ValueError("Refusing symlinked .demo-state cleanup")
    # `gh pr close --repo --delete-branch` removes only the remote branch.
    branches, current = local_demo_branches()
    if args.apply and current in branches:
        raise ValueError(f"Switch off {current} before reset; local demo branches are deleted")
    prs = json.loads(
        command(
            "pr",
            "list",
            "--state",
            "open",
            "--label",
            "demo",
            "--limit",
            "100",
            "--json",
            "number,state,headRefName,isCrossRepository",
        )
    )
    issues = json.loads(
        command(
            "issue",
            "list",
            "--state",
            "all",
            "--label",
            "spec:002",
            "--label",
            "demo",
            "--limit",
            "100",
            "--json",
            "number,state",
        )
    )
    if len(prs) == 100 or len(issues) == 100:
        raise RuntimeError("Reset resource limit reached; refusing a potentially partial reset")
    actions = plan(prs, issues)
    local = [["branch", "-D", name] for name in branches]
    print(json.dumps({"apply": args.apply, "actions": actions, "local": local}, indent=2))
    if args.apply:
        for action in actions:
            command(*action)
        for action in local:
            git(*action)
        # Only the known demo database is removed; no wildcard or repository cleanup.
        if database.exists():
            database.unlink()


if __name__ == "__main__":
    main()
