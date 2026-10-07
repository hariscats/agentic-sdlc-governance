import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from guardrails import gates
from guardrails.gates import PullRequest, is_agent, size, spec_link


def agent_pr(**changes: Any) -> PullRequest:
    pr = PullRequest(
        author="app/copilot-swe-agent",
        title="feat: intake [spec:001]",
        paths=["src/app.py", "tests/test_app.py"],
        changed_lines=399,
    )
    for name, value in changes.items():
        setattr(pr, name, value)
    return pr


def test_positive_boundary() -> None:
    assert size(agent_pr(changed_lines=400)) == []
    assert spec_link(agent_pr(), {"001"}) == []


def test_size_limit() -> None:
    assert size(agent_pr(changed_lines=401)) == ["Agent diff exceeds 400 changed lines (401)"]


@pytest.mark.parametrize(
    "paths,message",
    [
        ([".github/workflows/ci.yml"], "protected"),
        ([".GITHUB/workflows/ci.yml"], "protected"),
        (["GUARDRAILS/policy.py"], "protected"),
        (["demo/run.py"], "protected"),
        (["Makefile"], "protected"),
        (["uv.lock"], "protected"),
        (["README.md"], "outside"),
        (["SRC/app.py"], "outside"),
        (["metrics/collector.py"], "outside"),
    ],
)
def test_agent_path_allowlist(paths: list[str], message: str) -> None:
    assert any(message in error for error in size(agent_pr(paths=paths)))


@pytest.mark.parametrize(
    "title,specs,expected",
    [
        ("Add bulk export", {"001"}, ["Source changes must reference spec:NNN"]),
        ("feat: export [spec:999]", {"001"}, ["Unknown spec:999"]),
        ("feat: export [spec:001]", set(), ["Unknown spec:001"]),
    ],
)
def test_spec_link_negative(title: str, specs: set[str], expected: list[str]) -> None:
    pr = PullRequest(author="human", title=title, paths=["src/app.py"])
    assert spec_link(pr, specs) == expected


def test_spec_link_scope() -> None:
    assert spec_link(PullRequest(author="human", paths=["README.md"]), set()) == []
    body = PullRequest(author="human", body="Implements spec:001", paths=["src/app.py"])
    assert spec_link(body, {"001"}) == []


@pytest.mark.parametrize(
    "pr",
    [
        # Verified on public cloud-agent PRs: gh reports "app/copilot-swe-agent",
        # REST "Copilot"; commits use copilot-swe-agent[bot] and a Copilot noreply email.
        PullRequest(author="app/copilot-swe-agent"),
        PullRequest(author="Copilot"),
        PullRequest(author="human", identities=["copilot-swe-agent[bot]"]),
        PullRequest(author="human", identities=["198982749+Copilot@users.noreply.github.com"]),
        PullRequest(author="human", labels=["agent-authored"]),
        PullRequest(
            author="human",
            commits=["x\n\nCo-authored-by: bot <198982749+Copilot@users.noreply.github.com>"],
        ),
        PullRequest(author="human", commits=["x\n\nCo-authored-by: Copilot <x@example.invalid>"]),
    ],
)
def test_agent_signals(pr: PullRequest) -> None:
    assert is_agent(pr)


def test_human_prs_are_not_size_limited() -> None:
    pr = PullRequest(
        author="hariscats",
        identities=["hariscats", "123+hariscats@users.noreply.github.com", "GitHub"],
        commits=["Co-authored-by: Hariscats <123+hariscats@users.noreply.github.com>"],
        paths=[".github/workflows/ci.yml"],
        changed_lines=5000,
    )
    assert not is_agent(pr)
    assert size(pr) == []


def git(root: Path, *args: str) -> str:
    command = ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
    command += ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args]
    return subprocess.check_output(command, cwd=root, text=True).strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str, dict[str, Any]]:
    root = tmp_path / "repo"
    (root / "specs").mkdir(parents=True)
    git(root, "init", "-q")
    (root / "README.md").write_text("fixture")
    (root / "specs/001-demo.md").write_text("# spec:001")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    for name in ["src/app.py", "tests/test_app.py"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "feat: demo [spec:001]")
    head = git(root, "rev-parse", "HEAD")
    metadata = {
        "headRefOid": head,
        "author": {"login": "human"},
        "title": "feat: demo [spec:001]",
        "body": None,
        "labels": [],
    }
    return root, base, head, metadata


def test_runner_and_race(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, head, data = repository
    assert gates.evaluate("spec-link", data, root, base, head) == []
    assert gates.evaluate("size", data, root, base, head) == []
    with pytest.raises(ValueError, match="SHAs"):
        gates.evaluate("spec-link", data, root, "main", head)
    data["headRefOid"] = base
    with pytest.raises(ValueError, match="changed"):
        gates.evaluate("spec-link", data, root, base, head)


def test_spec_must_exist_on_base(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, _, data = repository
    (root / "specs/042-sneak.md").write_text("# spec:042")
    (root / "src/app.py").write_text("x = 2\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "add the spec and the code together")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    data["title"] = "feat: sneak [spec:042]"
    assert gates.evaluate("spec-link", data, root, base, head) == ["Unknown spec:042"]


def test_duplicate_spec_number(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, _, _, data = repository
    (root / "specs/001-other.md").write_text("# spec:001 again")
    git(root, "add", ".")
    git(root, "commit", "-qm", "duplicate")
    base = git(root, "rev-parse", "HEAD")
    (root / "src/app.py").write_text("x = 3\n")
    git(root, "commit", "-qam", "change")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="duplicate"):
        gates.evaluate("spec-link", data, root, base, head)


def test_size_counts_lines_from_git_and_agent_commits(
    repository: tuple[Path, str, str, dict[str, Any]],
) -> None:
    root, base, _, data = repository
    (root / "src/big.py").write_text("x = 1\n" * 401)
    git(root, "add", ".")
    agent = ["-c", "user.name=copilot-swe-agent[bot]"]
    agent += ["-c", "user.email=198982749+Copilot@users.noreply.github.com"]
    git(root, *agent, "commit", "-qm", "Add a big module")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    assert gates.evaluate("size", data, root, base, head) == [
        "Agent diff exceeds 400 changed lines (403)"
    ]


def test_agent_label_and_protected_paths(repository: tuple[Path, str, str, dict[str, Any]]) -> None:
    root, base, _, data = repository
    (root / "GUARDRAILS").mkdir()
    (root / "GUARDRAILS/example.json").write_text("{}")
    git(root, "add", ".")
    git(root, "commit", "-qm", "protected")
    head = data["headRefOid"] = git(root, "rev-parse", "HEAD")
    data["labels"] = [{"name": "agent-authored"}]
    errors = gates.evaluate("size", data, root, base, head)
    assert errors == ["Agent changed protected paths: GUARDRAILS/example.json"]


def test_cli_report_and_step_summary(
    repository: tuple[Path, str, str, dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base, head, data = repository
    data["title"] = "Add bulk export"
    metadata = tmp_path / "pr.json"
    metadata.write_text(json.dumps(data))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    arguments = ["--metadata", str(metadata), "--candidate", str(root)]
    arguments += ["--base", base, "--head", head]
    with pytest.raises(SystemExit) as failed:
        gates.main(["spec-link", *arguments])
    assert failed.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] == ["Source changes must reference spec:NNN"]
    assert "spec-link: fail" in summary.read_text()
    with pytest.raises(SystemExit) as passed:
        gates.main(["size", *arguments])
    assert passed.value.code == 0
