import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from demo import run

ROOT = Path(__file__).resolve().parents[1]


def steps(events: Path) -> list[tuple[str, str]]:
    return [(e["stage"], e["status"]) for e in map(json.loads, events.read_text().splitlines())]


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(ROOT / "guardrails", tmp_path / "guardrails", ignore=ignore)
    return tmp_path


def test_scene1_sends_attempts_through_the_real_hook(copy: Path) -> None:
    assert run.run_scene(1, root=copy) == 0
    assert steps(copy / "demo/events.jsonl") == [("agent", "denied")] * 4 + [("agent", "allowed")]
    lines = (copy / ".agent-audit/session.jsonl").read_text().splitlines()
    assert [json.loads(line)["decision"] for line in lines] == ["deny"] * 4 + ["allow"]


def test_scene1_fails_loudly_on_an_unexpected_decision(
    copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = ("Turn off CI", "edit", {"path": ".github/workflows/ci.yml"}, "allowed")
    monkeypatch.setattr(run, "ATTEMPTS", [attempt])
    assert run.run_scene(1, root=copy) == 1
    assert steps(copy / "demo/events.jsonl") == [("agent", "failed")]


def test_scene2_fails_blocks_then_passes(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    assert run.run_scene(2, events=events) == 0
    assert steps(events) == [
        ("gates", "failed"),
        ("gates", "blocked"),
        ("gates", "blocked"),
        ("gates", "passed"),
    ]
    details = [json.loads(line)["detail"] for line in events.read_text().splitlines()]
    assert "Source changes must reference spec:NNN" in details[1]
    assert "Agent diff exceeds 400 changed lines" in details[2]


def make_proof(proof: Path) -> None:
    proof.mkdir(parents=True, exist_ok=True)
    (proof / "permit-intake.zip").write_bytes(b"signed bytes")
    digest = hashlib.sha256(b"signed bytes").hexdigest()
    (proof / "checksums.json").write_text(json.dumps({"permit-intake.zip": digest}))


def test_scene3_offline_uses_the_labelled_checksum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_proof(tmp_path / "proof")
    monkeypatch.setattr(run, "PROOF", tmp_path / "proof")
    monkeypatch.setattr(run, "gh_online", lambda: False)
    events = tmp_path / "events.jsonl"
    assert run.run_scene(3, events=events) == 0
    assert steps(events) == [("release", "passed"), ("release", "passed"), ("evidence", "failed")]
    assert "checksum, not signature" in events.read_text()


def test_scene3_without_an_artifact_or_network_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "PROOF", tmp_path / "proof")
    monkeypatch.setattr(run, "gh_online", lambda: False)
    events = tmp_path / "events.jsonl"
    assert run.run_scene(3, events=events) == 1
    assert steps(events) == [("release", "failed")]


def test_download_picks_the_newest_main_run_with_a_successful_attest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_gh(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("run", "list"):
            runs = [{"databaseId": 3, "headSha": "c" * 40}, {"databaseId": 2, "headSha": "b" * 40}]
            return subprocess.CompletedProcess(args, 0, json.dumps(runs), "")
        if args[:2] == ("run", "view"):
            conclusion = "success" if args[2] == "2" else "failure"
            jobs = {"jobs": [{"name": "attest", "conclusion": conclusion}]}
            return subprocess.CompletedProcess(args, 0, json.dumps(jobs), "")
        if args[:2] == ("run", "download"):
            make_proof(Path(args[args.index("--dir") + 1]))
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(args)

    monkeypatch.setattr(run, "PROOF", tmp_path / "proof")
    monkeypatch.setattr(run, "gh_online", lambda: True)
    monkeypatch.setattr(run, "gh", fake_gh)
    downloaded = run.ensure_artifact()
    assert downloaded == f"Downloaded release-candidate from main release run 2 @ {'b' * 7}"
    assert [call[2] for call in calls if call[:2] == ("run", "download")] == ["2"]
    assert (tmp_path / "proof/permit-intake.zip").read_bytes() == b"signed bytes"
    assert run.ensure_artifact() == f"Using release run 2 @ {'b' * 7} (downloaded earlier)"


def test_signature_failure_is_reported_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_proof(tmp_path / "proof")
    monkeypatch.setattr(run, "PROOF", tmp_path / "proof")
    monkeypatch.setattr(run, "gh_online", lambda: True)

    def fake_gh(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "Error: HTTP 404: Not Found (attestations)")

    monkeypatch.setattr(run, "gh", fake_gh)
    result = run.verify_artifact(tampered=True)
    assert result["mode"] == "signature"
    assert (result["stage"], result["status"]) == ("evidence", "failed")
    assert "no signed attestation matches its digest" in result["detail"]
