import json
import re
from pathlib import Path

import yaml


def check(root: Path = Path(".")) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    for path in (root / ".github/workflows").glob("*.yml"):
        data = yaml.safe_load(path.read_text())
        if data.get("permissions") not in ({}, {"contents": "read"}):
            errors.append(f"{path}: broad top-level permissions")
        for job in data["jobs"].values():
            names.add(job.get("name", ""))
            for step in job.get("steps", []):
                action = step.get("uses", "")
                if action and not re.fullmatch(r"[\w./-]+@[a-f0-9]{40}", action):
                    errors.append(f"{path}: unpinned action {action}")
    rules = json.loads((root / "governance/rulesets/main-protection.json").read_text())
    for rule in rules["rules"]:
        if rule["type"] == "required_status_checks":
            for item in rule["parameters"]["required_status_checks"]:
                if item["context"] not in names:
                    errors.append(f"Missing job: {item['context']}")
    hooks = json.loads((root / ".github/hooks/governance.json").read_text())
    if hooks["version"] != 1 or "preToolUse" not in hooks["hooks"]:
        errors.append("Invalid hook configuration")
    for path in (root / ".github/agents").glob("*.agent.md"):
        front = yaml.safe_load(path.read_text().split("---")[1])
        if not front.get("description") or not isinstance(front.get("tools"), list):
            errors.append(f"Invalid agent frontmatter: {path}")
    return errors


if __name__ == "__main__":
    failures = check()
    print("\n".join(failures) if failures else "Repository configuration PASS")
    raise SystemExit(1 if failures else 0)
