from __future__ import annotations

import hashlib
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from demo import run
from demo.console import server
from guardrails.policy import evaluate


class ConsoleTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.root = self.tmp / "repo"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src/app.py").write_text("app = 1\n")
        self.console = server.create_server(self.root, port=0)
        threading.Thread(target=self.console.serve_forever, args=(0.05,), daemon=True).start()
        self.addCleanup(self.console.server_close)
        self.addCleanup(self.console.shutdown)
        self.port = self.console.server_address[1]

    def request(
        self, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, str], str]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        sent = {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json"}
        sent.update(headers or {})
        payload = body if isinstance(body, str) or body is None else json.dumps(body)
        connection.request(method, path, payload, sent)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        connection.close()
        return result

    def post(self, path: str, body: Any) -> tuple[int, Any]:
        status, _, text = self.request("POST", path, body)
        return status, json.loads(text)

    def test_index_is_self_contained(self) -> None:
        status, headers, text = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("<script src", text)
        self.assertNotIn("<link", text)
        for label in ["Agent", "Hook", "PR gates", "Human", "Release", "Evidence"]:
            self.assertIn(f"<h2>{label}</h2>", text)

    def test_try_rm_rf_is_denied_and_executes_nothing(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("the console executed a command"))
        patches = [mock.patch.object(subprocess, name, forbidden) for name in
                   ["Popen", "run", "call", "check_call", "check_output"]]
        patches += [mock.patch.object(os, name, forbidden) for name in
                    ["system", "posix_spawn", "posix_spawnp", "execv", "execvp", "execve"]
                    if hasattr(os, name)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        status, result = self.post("/try", {"command": "rm -rf src/"})
        self.assertEqual((status, result["decision"]), (200, "deny"))
        self.assertEqual((self.root / "src/app.py").read_text(), "app = 1\n")
        audit = (self.root / ".agent-audit/session.jsonl").read_text()
        self.assertEqual(json.loads(audit)["decision"], "deny")
        self.assertNotIn("rm -rf", audit)
        forbidden.assert_not_called()

    def test_try_allows_an_allowlisted_command(self) -> None:
        self.assertEqual(self.post("/try", {"command": "git status --short"})[1]["decision"], "allow")

    def test_try_validates_input(self) -> None:
        for body in [{}, {"command": ""}, {"command": "x" * 501}, {"command": 7},
                     {"command": "ls", "extra": 1}, ["ls"], "{not json"]:
            with self.subTest(body=body):
                status, _, _ = self.request("POST", "/try", body)
                self.assertEqual(status, 422)

    def test_scene_runs_the_fixed_command_in_the_background(self) -> None:
        launched: list[tuple[list[str], Path]] = []

        class Running:
            def __init__(self, command: list[str], cwd: Path) -> None:
                launched.append((command, cwd))

            def poll(self) -> None:
                return None

        with mock.patch.object(server.subprocess, "Popen", Running):
            self.assertEqual(self.post("/scene/4", {})[0], 404)
            self.assertEqual(self.post("/scene/x", {})[0], 404)
            self.assertEqual(self.post("/scene/1", {}), (200, {"scene": 1}))
            self.assertEqual(self.post("/scene/2", {})[0], 409)
        command = [sys.executable, "-m", "demo.run", "--scene", "1", "--pace", "2"]
        self.assertEqual(launched, [(command, self.root)])

    def test_localhost_guards(self) -> None:
        self.assertEqual(self.request("GET", "/", headers={"Host": "attacker.example:8001"})[0], 403)
        form = {"Content-Type": "application/x-www-form-urlencoded"}
        self.assertEqual(self.request("POST", "/try", "command=ls", headers=form)[0], 415)
        self.assertEqual(self.request("POST", "/scene/1", "", headers={"Content-Type": ""})[0], 415)
        self.assertEqual(self.request("GET", "/nowhere")[0], 404)

    def test_verify_offline_falls_back_to_a_labelled_checksum(self) -> None:
        proof = self.tmp / "proof"
        proof.mkdir()
        (proof / "permit-intake.zip").write_bytes(b"signed bytes")
        digest = hashlib.sha256(b"signed bytes").hexdigest()
        (proof / "checksums.json").write_text(json.dumps({"permit-intake.zip": digest}))
        with mock.patch.object(run, "PROOF", proof), mock.patch.object(run, "gh_online", lambda: False):
            _, real = self.post("/verify", {"tampered": False})
            _, tampered = self.post("/verify", {"tampered": True})
        self.assertEqual((real["status"], real["mode"]), ("passed", "checksum"))
        self.assertEqual((tampered["status"], tampered["mode"]), ("failed", "checksum"))
        for result in (real, tampered):
            self.assertIn("checksum, not signature", result["detail"])
        lines = (self.root / "demo/events.jsonl").read_text().splitlines()
        steps = [(e["scene"], e["stage"], e["status"]) for e in map(json.loads, lines)]
        self.assertEqual(steps, [(3, "release", "passed"), (3, "evidence", "failed")])
        self.assertEqual(self.post("/verify", {"tampered": "yes"})[0], 422)


class StreamTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.files = server.sources(self.root)

    def test_poll_streams_complete_new_lines(self) -> None:
        files = self.files
        offsets = server.positions(files)
        self.assertEqual(server.poll(files, offsets), [])
        evaluate("rg", {}, self.root)
        files["demo"].parent.mkdir(parents=True)
        files["demo"].write_text('{"scene": 1, "status": "denied"}\n{"partial": ')
        batch = server.poll(files, offsets)
        self.assertEqual([event["source"] for event in batch], ["audit", "demo"])
        self.assertEqual(batch[1], {"source": "demo", "scene": 1, "status": "denied"})
        with files["demo"].open("a") as stream:
            stream.write("1}\nnot json\n")
        self.assertEqual(server.poll(files, offsets), [{"source": "demo", "partial": 1}])
        files["demo"].unlink()  # make reset
        self.assertEqual(server.poll(files, offsets), [])
        files["demo"].write_text('{"scene": 2}\n')
        self.assertEqual(server.poll(files, offsets), [{"source": "demo", "scene": 2}])

    def test_stream_replays_only_events_since_start(self) -> None:
        self.files["demo"].parent.mkdir(parents=True)
        self.files["demo"].write_text('{"scene": 0}\n')
        offsets = server.positions(self.files)
        self.files["demo"].write_text('{"scene": 0}\n{"scene": 1}\n')
        messages = server.stream(self.files, offsets, interval=1, heartbeat=1, sleep=lambda _: None)
        self.assertEqual(next(messages), 'data: {"source": "demo", "scene": 1}\n\n')
        self.assertEqual(next(messages), ": keep-alive\n\n")

    def test_event_stream_endpoint(self) -> None:
        console = server.create_server(self.root, port=0)
        threading.Thread(target=console.serve_forever, args=(0.05,), daemon=True).start()
        self.addCleanup(console.server_close)
        self.addCleanup(console.shutdown)
        port = console.server_address[1]
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request("GET", "/events", headers={"Host": f"127.0.0.1:{port}"})
        response = connection.getresponse()
        self.assertEqual(response.getheader("Content-Type"), "text/event-stream")
        evaluate("rg", {}, self.root)
        line = response.fp.readline().decode()
        self.assertTrue(line.startswith("data: "), line)
        self.assertEqual(json.loads(line[len("data: "):])["source"], "audit")
        connection.close()


if __name__ == "__main__":
    unittest.main()
