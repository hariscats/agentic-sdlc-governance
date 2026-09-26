import json
import re
import subprocess
from pathlib import Path

REPO = "hariscats/agentic-sdlc-governance"


def main() -> None:
    existing = json.loads(
        subprocess.check_output(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                REPO,
                "--state",
                "all",
                "--label",
                "spec:002",
                "--limit",
                "100",
                "--json",
                "number,title",
            ],
            text=True,
        )
    )
    if len(existing) == 100:
        raise RuntimeError("Issue seed limit reached")
    known = {issue["title"] for issue in existing}
    tasks = Path("specs/002-permit-review/tasks.md").read_text()
    for task, description in re.findall(r"- \[ \] (T\d{3,}) (.+)", tasks):
        title = f"[spec:002] {task}: {description}"
        if title in known:
            continue
        body = (
            f"Task {task}, spec:002. Read specs/002-permit-review/spec.md, plan.md, "
            "and tasks.md before implementation. Do not start until the presenter delegates "
            "this live-demo task after architecture approval. Keep the PR at most 400 changed "
            "lines, include matching tests, and do not edit protected paths."
        )
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                REPO,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "spec:002",
                "--label",
                "agent-ready",
                "--label",
                "demo",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
