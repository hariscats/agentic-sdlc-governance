import json
import shutil
import subprocess
from pathlib import Path

import pytest

from metrics.collector import alerts, security_metrics
from scripts.validate_repository import check
from scripts.verify_sbom import bound


def test_workflow_ruleset_contract_and_negative(tmp_path: Path) -> None:
    assert check() == []
    shutil.copytree(".github", tmp_path / ".github")
    shutil.copytree("governance/rulesets", tmp_path / "governance/rulesets")
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.write_text(
        workflow.read_text()
        .replace("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7")
        .replace("  contents: read", "  contents: write")
    )
    errors = check(tmp_path)
    assert any("unpinned" in item for item in errors)
    assert any("permissions" in item for item in errors)


def test_signed_sbom_binding() -> None:
    sbom = {"name": "actual"}
    proof = [{"verificationResult": {"statement": {"predicate": sbom}}}]
    assert bound(sbom, proof)
    assert not bound({"name": "tampered"}, proof)
    assert not bound(sbom, [])


def test_alert_permission_and_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def response(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 1, '{"status":"403"}', "forbidden")

    monkeypatch.setattr(subprocess, "run", response)
    assert alerts("code-scanning")[0] is None
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 1, '[{"status":"404"}]', "not found"),
    )
    assert alerts("code-scanning")[0] is None
    with pytest.raises(ValueError):
        alerts("organization")
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "network error")
    )
    with pytest.raises(RuntimeError):
        alerts("dependabot")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 1, '{"status":"401"}', "unauthorized"),
    )
    with pytest.raises(RuntimeError):
        alerts("dependabot")


def test_security_aggregation(monkeypatch: pytest.MonkeyPatch) -> None:
    data = [
        [
            {
                "state": "fixed",
                "created_at": "2026-01-01T00:00:00Z",
                "fixed_at": "2026-01-02T00:00:00Z",
            }
        ]
    ]
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, json.dumps(data), "")
    )
    summary = security_metrics()
    assert summary["dependabot_remediation_hours"] == 24
    assert summary["code_scanning_alerts"] == {"fixed": 1}
