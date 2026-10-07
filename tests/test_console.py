import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from demo import run
from demo.console import server
from guardrails.policy import evaluate


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text("app = 1\n")
    return tmp_path


def console(root: Path) -> TestClient:
    return TestClient(server.create_app(root), base_url="http://127.0.0.1:8001")


def test_index_is_self_contained(root: Path) -> None:
    response = console(root).get("/")
    assert response.status_code == 200
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "<script src" not in response.text and "<link" not in response.text
    for label in ["Agent", "Hook", "PR gates", "Human", "Release", "Evidence"]:
        assert f"<h2>{label}</h2>" in response.text


def test_try_rm_rf_is_denied_and_executes_nothing(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("the console executed a command")

    for name in ["Popen", "run", "call", "check_call", "check_output"]:
        monkeypatch.setattr(subprocess, name, forbidden)
    for name in ["system", "posix_spawn", "posix_spawnp", "execv", "execvp", "execve"]:
        monkeypatch.setattr(os, name, forbidden, raising=False)
    response = console(root).post("/try", json={"command": "rm -rf src/"})
    assert response.status_code == 200
    assert response.json()["decision"] == "deny"
    assert (root / "src/app.py").read_text() == "app = 1\n"
    audit = (root / ".agent-audit/session.jsonl").read_text()
    assert json.loads(audit)["decision"] == "deny"
    assert "rm -rf" not in audit


def test_try_allows_an_allowlisted_command(root: Path) -> None:
    response = console(root).post("/try", json={"command": "git status --short"})
    assert response.json()["decision"] == "allow"


@pytest.mark.parametrize(
    "body", [{}, {"command": ""}, {"command": "x" * 501}, {"command": "ls", "extra": 1}]
)
def test_try_validates_input(root: Path, body: dict[str, object]) -> None:
    assert console(root).post("/try", json=body).status_code == 422


def test_scene_runs_the_fixed_command_in_the_background(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched: list[tuple[list[str], Path]] = []

    class Running:
        def __init__(self, command: list[str], cwd: Path) -> None:
            launched.append((command, cwd))

        def poll(self) -> None:
            return None

    monkeypatch.setattr(server.subprocess, "Popen", Running)
    client = console(root)
    assert client.post("/scene/4", json={}).status_code == 404
    assert client.post("/scene/x", json={}).status_code == 422
    assert client.post("/scene/1", json={}).json() == {"scene": 1}
    assert launched == [([sys.executable, "-m", "demo.run", "--scene", "1", "--pace", "2"], root)]
    assert client.post("/scene/2", json={}).status_code == 409


def test_localhost_guards(root: Path) -> None:
    rebound = TestClient(server.create_app(root), base_url="http://attacker.example:8001")
    assert rebound.get("/").status_code == 403
    client = console(root)
    form = {"content-type": "application/x-www-form-urlencoded"}
    assert client.post("/try", content="command=ls", headers=form).status_code == 415
    assert client.post("/scene/1").status_code == 415


def test_verify_offline_falls_back_to_a_labelled_checksum(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "permit-intake.zip").write_bytes(b"signed bytes")
    digest = hashlib.sha256(b"signed bytes").hexdigest()
    (proof / "checksums.json").write_text(json.dumps({"permit-intake.zip": digest}))
    monkeypatch.setattr(run, "PROOF", proof)
    monkeypatch.setattr(run, "gh_online", lambda: False)
    client = console(root)
    real = client.post("/verify", json={"tampered": False}).json()
    tampered = client.post("/verify", json={"tampered": True}).json()
    assert (real["status"], real["mode"]) == ("passed", "checksum")
    assert (tampered["status"], tampered["mode"]) == ("failed", "checksum")
    assert all("checksum, not signature" in r["detail"] for r in (real, tampered))
    lines = (root / "demo/events.jsonl").read_text().splitlines()
    steps = [(e["scene"], e["stage"], e["status"]) for e in map(json.loads, lines)]
    assert steps == [(3, "release", "passed"), (3, "evidence", "failed")]


def test_poll_streams_complete_new_lines(root: Path) -> None:
    files = server.sources(root)
    offsets = server.positions(files)
    assert server.poll(files, offsets) == []
    evaluate("rg", {}, root)
    files["demo"].parent.mkdir(parents=True)
    files["demo"].write_text('{"scene": 1, "status": "denied"}\n{"partial": ')
    batch = server.poll(files, offsets)
    assert [event["source"] for event in batch] == ["audit", "demo"]
    assert batch[1] == {"source": "demo", "scene": 1, "status": "denied"}
    with files["demo"].open("a") as stream:
        stream.write("1}\nnot json\n")
    assert server.poll(files, offsets) == [{"source": "demo", "partial": 1}]
    files["demo"].unlink()  # make reset
    assert server.poll(files, offsets) == []
    files["demo"].write_text('{"scene": 2}\n')
    assert server.poll(files, offsets) == [{"source": "demo", "scene": 2}]


def test_stream_replays_only_events_since_start(root: Path) -> None:
    files = server.sources(root)
    files["demo"].parent.mkdir(parents=True)
    files["demo"].write_text('{"scene": 0}\n')
    offsets = server.positions(files)
    files["demo"].write_text('{"scene": 0}\n{"scene": 1}\n')

    async def first() -> str:
        return await anext(server.stream(files, offsets, interval=0.01))

    assert asyncio.run(first()) == 'data: {"source": "demo", "scene": 1}\n\n'
