from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from demo import run

ROOT = Path(__file__).resolve().parents[1]


def steps(events: Path) -> list[tuple[str, str]]:
    return [(e["stage"], e["status"]) for e in map(json.loads, events.read_text().splitlines())]


def make_proof(proof: Path) -> None:
    proof.mkdir(parents=True, exist_ok=True)
    (proof / "permit-intake.zip").write_bytes(b"signed bytes")
    digest = hashlib.sha256(b"signed bytes").hexdigest()
    (proof / "checksums.json").write_text(json.dumps({"permit-intake.zip": digest}))


class SceneTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.events = self.tmp / "events.jsonl"
        # Scene output is printed for the presenter; keep test output quiet.
        quiet = contextlib.ExitStack()
        quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.addCleanup(quiet.close)

    def copy_guardrails(self) -> Path:
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(ROOT / "guardrails", self.tmp / "guardrails", ignore=ignore)
        return self.tmp

    def patch(self, name: str, value: object) -> None:
        patcher = mock.patch.object(run, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_scene1_sends_attempts_through_the_real_hook(self) -> None:
        root = self.copy_guardrails()
        self.assertEqual(run.run_scene(1, root=root), 0)
        expected = [("agent", "denied")] * 4 + [("agent", "allowed")]
        self.assertEqual(steps(root / "demo/events.jsonl"), expected)
        lines = (root / ".agent-audit/session.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(line)["decision"] for line in lines], ["deny"] * 4 + ["allow"])

    def test_scene1_fails_loudly_on_an_unexpected_decision(self) -> None:
        root = self.copy_guardrails()
        self.patch("ATTEMPTS", [("Turn off CI", "edit", {"path": ".github/workflows/ci.yml"}, "allowed")])
        self.assertEqual(run.run_scene(1, root=root), 1)
        self.assertEqual(steps(root / "demo/events.jsonl"), [("agent", "failed")])

    def test_scene2_fails_blocks_then_passes(self) -> None:
        self.assertEqual(run.run_scene(2, events=self.events), 0)
        self.assertEqual(
            steps(self.events),
            [("gates", "failed"), ("gates", "blocked"), ("gates", "blocked"), ("gates", "passed")],
        )
        details = [json.loads(line)["detail"] for line in self.events.read_text().splitlines()]
        self.assertIn("FAILED (failures=1)", details[0])
        self.assertIn("Source changes must reference spec:NNN", details[1])
        self.assertIn("Agent diff exceeds 400 changed lines", details[2])
        self.assertIn(": OK", details[3])

    def test_scene3_offline_uses_the_labelled_checksum(self) -> None:
        make_proof(self.tmp / "proof")
        self.patch("PROOF", self.tmp / "proof")
        self.patch("gh_online", lambda: False)
        self.assertEqual(run.run_scene(3, events=self.events), 0)
        self.assertEqual(
            steps(self.events), [("release", "passed"), ("release", "passed"), ("evidence", "failed")]
        )
        self.assertIn("checksum, not signature", self.events.read_text())

    def test_scene3_without_an_artifact_or_network_fails_loudly(self) -> None:
        self.patch("PROOF", self.tmp / "proof")
        self.patch("gh_online", lambda: False)
        self.assertEqual(run.run_scene(3, events=self.events), 1)
        self.assertEqual(steps(self.events), [("release", "failed")])

    def test_download_picks_the_newest_main_run_with_a_successful_attest(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_gh(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
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

        self.patch("PROOF", self.tmp / "proof")
        self.patch("gh_online", lambda: True)
        self.patch("gh", fake_gh)
        downloaded = run.ensure_artifact()
        self.assertEqual(downloaded, f"Downloaded release-candidate from main release run 2 @ {'b' * 7}")
        self.assertEqual([c[2] for c in calls if c[:2] == ("run", "download")], ["2"])
        self.assertEqual((self.tmp / "proof/permit-intake.zip").read_bytes(), b"signed bytes")
        self.assertEqual(run.ensure_artifact(), f"Using release run 2 @ {'b' * 7} (downloaded earlier)")

    def test_signature_failure_is_reported_as_failed(self) -> None:
        make_proof(self.tmp / "proof")
        self.patch("PROOF", self.tmp / "proof")
        self.patch("gh_online", lambda: True)
        failure = subprocess.CompletedProcess([], 1, "", "Error: HTTP 404: Not Found (attestations)")
        self.patch("gh", lambda *args, timeout=60: failure)
        result = run.verify_artifact(tampered=True)
        self.assertEqual(result["mode"], "signature")
        self.assertEqual((result["stage"], result["status"]), ("evidence", "failed"))
        self.assertIn("no signed attestation matches its digest", result["detail"])


if __name__ == "__main__":
    unittest.main()
