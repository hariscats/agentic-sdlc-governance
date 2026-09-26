import json
from pathlib import Path

from scripts.github_data import pull_requests


def main() -> None:
    prs = pull_requests("merged")
    if len(prs) == 100:
        raise ValueError("Evidence limit reached; implement pagination before releasing")
    Path(".demo-state").mkdir(exist_ok=True)
    Path(".demo-state/pr-evidence.json").write_text(json.dumps(prs, indent=2) + "\n")
    groups: dict[str, list[str]] = {}
    import re

    for pr in prs:
        refs = re.findall(r"\bspec:\d{3}\b", pr["title"])
        for ref in refs or ["governance"]:
            groups.setdefault(ref, []).append(f"- PR #{pr['number']}: {pr['title']}")
    Path(".demo-state/release-notes.md").write_text(
        "# Governed demo release\n\n"
        + "\n\n".join(f"## {key}\n" + "\n".join(value) for key, value in sorted(groups.items()))
    )


if __name__ == "__main__":
    main()
