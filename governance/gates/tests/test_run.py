import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from governance.audit_config import main as audit_main
from governance.gates.run import evaluate, main


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=root,
        text=True,
    ).strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str, dict[str, Any]]:
    git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_text("fixture")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    for name in ["src/app.py", "tests/test_app.py", "specs/001-demo/tasks.md"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("T012")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "feat(T012): demo [spec:001]")
    head = git(tmp_path, "rev-parse", "HEAD")
    data = {
        "headRefOid": head,
        "author": {"login": "human"},
        "title": "spec:001 T012",
        "body": "",
        "labels": [],
        "additions": 3,
        "deletions": 0,
        "closingIssuesReferences": [],
        "latestReviews": [],
    }
    return tmp_path, base, head, data


def test_runner_and_race(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, head, data = repository
    assert evaluate("trace", data, root, base, head) == ([], "medium")
    assert evaluate("agent", data, root, base, head) == ([], "medium")
    with pytest.raises(ValueError, match="SHAs"):
        evaluate("trace", data, root, "main", head)
    data["headRefOid"] = base
    with pytest.raises(ValueError, match="changed"):
        evaluate("trace", data, root, base, head)


def test_duplicate_spec(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, _, data = repository
    (root / "specs/001-other").mkdir()
    (root / "specs/001-other/tasks.md").write_text("T012")
    git(root, "add", ".")
    git(root, "commit", "-qm", "duplicate")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="duplicate"):
        evaluate("trace", data, root, base, head)


def test_current_head_security_approval(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, _, data = repository
    (root / "governance").mkdir()
    (root / "governance/example.json").write_text("{}")
    git(root, "add", ".")
    git(root, "commit", "-qm", "protected")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    assert evaluate("agent", data, root, base, head)[0]
    data["_reviews"] = [{"user": {"login": "hariscats"}, "state": "APPROVED", "commit_id": base}]
    assert evaluate("agent", data, root, base, head)[0]
    data["_reviews"][0]["commit_id"] = head
    assert evaluate("agent", data, root, base, head) == ([], "high")


def test_runner_cli(
    repository: tuple[Path, str, str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root, base, head, data = repository
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps(data))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        "sys.argv",
        [
            "run",
            "trace",
            "--metadata",
            str(metadata),
            "--candidate",
            str(root),
            "--base",
            base,
            "--head",
            head,
        ],
    )
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 0
    assert "pass" in summary.read_text()


def test_audit_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "governance").mkdir()
    (tmp_path / ".demo-state").mkdir()
    (tmp_path / "governance/expected-agent-config.json").write_text('{"firewall":true}')
    (tmp_path / ".demo-state/cloud-agent-actual.json").write_text('{"firewall":false}')
    with pytest.raises(SystemExit) as result:
        audit_main()
    assert result.value.code == 1
    assert (
        json.loads((tmp_path / ".demo-state/cloud-agent-audit.json").read_text())["status"]
        == "drift"
    )
