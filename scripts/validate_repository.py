import json
import re
from collections import Counter
from pathlib import Path

import yaml

TRUSTED_GATES = {"Spec Traceability Gate", "Agent PR Policy Gate"}
# Commands that would materialize PR content in a pull_request_target workspace.
WORKTREE = re.compile(
    r"\bgit\s+(checkout|switch|worktree|restore|reset|merge|pull|cherry-pick|rebase|am|apply|stash)\b"
)


def check(root: Path = Path(".")) -> list[str]:
    errors: list[str] = []
    names: Counter[str] = Counter()
    trusted: set[str] = set()
    workflows = root / ".github/workflows"
    for path in sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")]):
        data = yaml.safe_load(path.read_text())
        # YAML 1.1 parses the bare key "on" as boolean True.
        triggers = data.get("on", data.get(True)) or {}
        events = {triggers} if isinstance(triggers, str) else set(triggers)
        target = "pull_request_target" in events
        if data.get("permissions") not in ({}, {"contents": "read"}):
            errors.append(f"{path}: broad top-level permissions")
        for job in data["jobs"].values():
            name = job.get("name", "")
            names[name] += 1
            if events == {"pull_request_target"}:
                trusted.add(name)
            signing = (job.get("permissions") or {}).get("id-token") == "write"
            steps = job.get("steps", [])
            if signing and any(
                "run" in s or s.get("uses", "").startswith("actions/checkout@") for s in steps
            ):
                errors.append(f"{path}: id-token job must not check out or run repository code")
            for step in job.get("steps", []):
                for line in step.get("run", "").splitlines():
                    command = line.split("|", 1)[0]
                    if "gh api" in command and "--slurp" in command and "--jq" in command:
                        errors.append(f"{path}: incompatible gh pagination flags")
                    if target and WORKTREE.search(line):
                        errors.append(f"{path}: pull_request_target must not materialize PR code")
                action = step.get("uses", "")
                if action and not re.fullmatch(r"[\w./-]+@[a-f0-9]{40}", action):
                    errors.append(f"{path}: unpinned action {action}")
                if target and action.startswith("actions/checkout@"):
                    inputs = step.get("with") or {}
                    if "ref" in inputs or "repository" in inputs:
                        errors.append(f"{path}: pull_request_target must check out the base only")
                    if inputs.get("persist-credentials") is not False:
                        errors.append(f"{path}: checkout must set persist-credentials: false")
    rules = json.loads((root / "governance/rulesets/main-protection.json").read_text())
    for rule in rules["rules"]:
        if rule["type"] == "required_status_checks":
            for item in rule["parameters"]["required_status_checks"]:
                context = item["context"]
                if names[context] == 0:
                    errors.append(f"Missing job: {context}")
                elif names[context] > 1:
                    errors.append(f"Duplicate job name for required check: {context}")
        if rule["type"] == "pull_request":
            params = rule["parameters"]
            for key in ["require_code_owner_review", "dismiss_stale_reviews_on_push"]:
                if params.get(key) is not True:
                    errors.append(f"Ruleset must set {key}")
    for gate in TRUSTED_GATES - trusted:
        errors.append(f"{gate} must run only on pull_request_target")
    config = json.loads((root / "governance/config.json").read_text())
    security = {"@" + owner for owner in config["security_owners"]}
    owners = {
        line.split()[0]: set(line.split()[1:])
        for line in (root / ".github/CODEOWNERS").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    for pattern in ["/.github/", "/governance/", "/scripts/"]:
        if not security & owners.get(pattern, set()):
            errors.append(f"CODEOWNERS must assign {pattern} to a security owner")
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
