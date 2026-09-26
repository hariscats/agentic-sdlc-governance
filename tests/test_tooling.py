import json
import zipfile
from pathlib import Path

import pytest

from metrics.collector import flow, hours, render, usage
from scripts.release_bundle import build, evidence, verify
from scripts.reset_demo import main as reset_main
from scripts.reset_demo import plan


def test_usage_and_html() -> None:
    rows = [
        {
            "schema": "demo.usage.v1",
            "synthetic": True,
            "user": "fake",
            "engaged": True,
            "features": ["cli", "cli"],
        }
    ]
    result = usage(rows)
    assert result["feature_users"]["cli"] == 1
    assert result["active_users"] == 1
    page = render({"usage": result, "flow_source": "<script>bad</script>"})
    assert "SYNTHETIC DATA" in page
    assert "<script>" not in page
    with pytest.raises(ValueError):
        usage([{"synthetic": False}])


def test_flow() -> None:
    pr = {
        "mergedAt": "2026-01-02T00:00:00Z",
        "createdAt": "2026-01-01T00:00:00Z",
        "author": {"login": "app/copilot-swe-agent"},
        "labels": [],
        "commits": [{}, {}],
        "reviews": [{"author": {"login": "human"}, "submittedAt": "2026-01-01T02:00:00Z"}],
        "statusCheckRollup": [{"name": "CI", "conclusion": "FAILURE"}],
    }
    delegated = {
        **pr,
        "author": {"login": "human"},
        "commits": [
            {"authors": [{"email": "198982749+Copilot@users.noreply.github.com", "name": "x"}]}
        ],
    }
    human = {**pr, "author": {"login": "human"}, "commits": [{"messageBody": "fix"}]}
    human["statusCheckRollup"] = [
        {"name": "CI", "conclusion": "FAILURE", "completedAt": "2026-01-01T01:00:00Z"},
        {"name": "CI", "conclusion": "SUCCESS", "completedAt": "2026-01-01T02:00:00Z"},
        {"name": "CI", "conclusion": "", "completedAt": "2026-01-01T03:00:00Z"},
    ]
    result = flow([pr, delegated, human])
    assert result["gate_latest_conclusions"]["CI"] == {"failure": 2, "success": 1}
    assert result["median_lead_hours"] == 24
    assert result["median_first_review_hours"] == 2
    assert result["merged_agent"] == 2
    assert result["merged_other"] == 1
    assert flow([])["median_lead_hours"] is None
    with pytest.raises(ValueError):
        hours("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z")


def test_bundle_and_tamper(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("app = 1\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n")
    (tmp_path / "uv.lock").write_text('[[package]]\nname="demo"\nversion="1.0"\n')
    (tmp_path / ".specify/memory").mkdir(parents=True)
    (tmp_path / ".specify/memory/constitution.md").write_text("Version 1")
    out = build("v0.1.0-demo", tmp_path)
    original = (out / "permit-intake.zip").read_bytes()
    assert (build("v0.1.0-demo", tmp_path) / "permit-intake.zip").read_bytes() == original
    verify(out)
    sbom = json.loads((out / "sbom.spdx.json").read_text())
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert len(sbom["relationships"]) == len(sbom["packages"])
    with zipfile.ZipFile(evidence(out, tmp_path)) as archive:
        status = json.loads(archive.read("evidence/status.json"))
        assert "attestation-verification.json" in status["missing_evidence"]
    (out / "permit-intake.zip").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Digest mismatch"):
        verify(out)
    with pytest.raises(ValueError):
        build("../../escape", tmp_path)


def test_reset_scope() -> None:
    prs = [
        {"number": 1, "state": "OPEN", "headRefName": "main", "isCrossRepository": False},
        {"number": 2, "state": "OPEN", "headRefName": "demo/rehearsal", "isCrossRepository": False},
        {"number": 3, "state": "OPEN", "headRefName": "demo/fork", "isCrossRepository": True},
    ]
    actions = plan(prs, [{"number": 4, "state": "CLOSED"}])
    assert actions == [
        ["pr", "close", "2", "--delete-branch"],
        ["issue", "reopen", "4"],
        ["issue", "edit", "4", "--add-label", "agent-ready"],
    ]


def test_reset_refuses_symlinked_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "permits.db").write_text("keep")
    work = tmp_path / "work"
    work.mkdir()
    (work / ".demo-state").symlink_to(outside)
    monkeypatch.chdir(work)
    calls: list[tuple[str, ...]] = []

    def command(*args: str) -> str:
        calls.append(args)
        return "[]"

    monkeypatch.setattr("scripts.reset_demo.command", command)
    monkeypatch.setattr("sys.argv", ["reset", "--apply"])
    with pytest.raises(ValueError, match="symlinked"):
        reset_main()
    assert calls == []
    assert (outside / "permits.db").read_text() == "keep"


def test_pr_evidence_is_minimized() -> None:
    from scripts.pr_evidence import project

    pr = {
        "number": 9,
        "title": "feat(T020): decisions [spec:002]",
        "author": {"login": "app/copilot-swe-agent"},
        "labels": [{"name": "spec:002"}],
        "reviews": [{"author": {"login": "arch"}, "state": "APPROVED", "body": "secret note"}],
        "commits": [
            {
                "oid": "a" * 40,
                "messageBody": "private message",
                "authors": [{"email": "person@example.invalid", "name": "Person"}],
            }
        ],
        "statusCheckRollup": [{"name": "CI", "conclusion": "SUCCESS"}],
    }
    evidence = project(pr)
    text = json.dumps(evidence)
    assert evidence["agent_authored"] is True
    assert evidence["reviews"][0]["state"] == "APPROVED"
    for leaked in ["secret note", "private message", "person@example.invalid"]:
        assert leaked not in text
