import json
import subprocess
from typing import Any

REPOSITORY = "hariscats/agentic-sdlc-governance"


def pull_requests(state: str) -> list[dict[str, Any]]:
    if state not in {"all", "merged"}:
        raise ValueError("Unsupported PR sample state")
    numbers = json.loads(
        subprocess.check_output(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPOSITORY,
                "--state",
                state,
                "--limit",
                "100",
                "--json",
                "number",
            ],
            text=True,
        )
    )
    result: list[dict[str, Any]] = []
    for item in numbers:
        number = int(item["number"])
        # Fetch nested connections separately to stay below GraphQL's node limit.
        result.append(
            json.loads(
                subprocess.check_output(
                    [
                        "gh",
                        "pr",
                        "view",
                        str(number),
                        "--repo",
                        REPOSITORY,
                        "--json",
                        "number,title,url,mergedAt,mergeCommit,headRefOid,createdAt,author,labels,"
                        "reviews,statusCheckRollup,commits",
                    ],
                    text=True,
                )
            )
        )
    return result
