from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

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


class RuleTest(unittest.TestCase):
    def test_positive_boundary(self) -> None:
        self.assertEqual(size(agent_pr(changed_lines=400)), [])
        self.assertEqual(spec_link(agent_pr(), {"001"}), [])

    def test_size_limit(self) -> None:
        self.assertEqual(
            size(agent_pr(changed_lines=401)), ["Agent diff exceeds 400 changed lines (401)"]
        )

    def test_agent_path_allowlist(self) -> None:
        for paths, message in [
            ([".github/workflows/ci.yml"], "protected"),
            ([".GITHUB/workflows/ci.yml"], "protected"),
            (["GUARDRAILS/policy.py"], "protected"),
            (["demo/run.py"], "protected"),
            (["Makefile"], "protected"),
            (["pyproject.toml"], "protected"),
            (["README.md"], "outside"),
            (["SRC/app.py"], "outside"),
            (["metrics/collector.py"], "outside"),
        ]:
            with self.subTest(paths=paths):
                errors = size(agent_pr(paths=paths))
                self.assertTrue(any(message in error for error in errors), errors)

    def test_spec_link_negative(self) -> None:
        for title, specs, expected in [
            ("Add bulk export", {"001"}, ["Source changes must reference spec:NNN"]),
            ("feat: export [spec:999]", {"001"}, ["Unknown spec:999"]),
            ("feat: export [spec:001]", set(), ["Unknown spec:001"]),
        ]:
            with self.subTest(title=title):
                pr = PullRequest(author="human", title=title, paths=["src/app.py"])
                self.assertEqual(spec_link(pr, specs), expected)

    def test_spec_link_scope(self) -> None:
        self.assertEqual(spec_link(PullRequest(author="human", paths=["README.md"]), set()), [])
        body = PullRequest(author="human", body="Implements spec:001", paths=["src/app.py"])
        self.assertEqual(spec_link(body, {"001"}), [])

    def test_agent_signals(self) -> None:
        # Verified on public cloud-agent PRs: gh reports "app/copilot-swe-agent",
        # REST "Copilot"; commits use copilot-swe-agent[bot] and a Copilot noreply email.
        for pr in [
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
        ]:
            with self.subTest(pr=pr):
                self.assertTrue(is_agent(pr))

    def test_human_prs_are_not_size_limited(self) -> None:
        pr = PullRequest(
            author="hariscats",
            identities=["hariscats", "123+hariscats@users.noreply.github.com", "GitHub"],
            commits=["Co-authored-by: Hariscats <123+hariscats@users.noreply.github.com>"],
            paths=[".github/workflows/ci.yml"],
            changed_lines=5000,
        )
        self.assertFalse(is_agent(pr))
        self.assertEqual(size(pr), [])


def git(root: Path, *args: str) -> str:
    command = ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
    command += ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args]
    return subprocess.check_output(command, cwd=root, text=True).strip()


class RunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
        self.root = root = self.tmp / "repo"
        (root / "specs").mkdir(parents=True)
        git(root, "init", "-q")
        (root / "README.md").write_text("fixture")
        (root / "specs/001-demo.md").write_text("# spec:001")
        git(root, "add", ".")
        git(root, "commit", "-qm", "base")
        self.base = git(root, "rev-parse", "HEAD")
        for name in ["src/app.py", "tests/test_app.py"]:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x = 1\n")
        git(root, "add", ".")
        git(root, "commit", "-qm", "feat: demo [spec:001]")
        self.head = git(root, "rev-parse", "HEAD")
        self.data: dict[str, Any] = {
            "headRefOid": self.head,
            "author": {"login": "human"},
            "title": "feat: demo [spec:001]",
            "body": None,
            "labels": [],
        }

    def commit(self, message: str, *identity: str) -> str:
        git(self.root, "add", ".")
        git(self.root, *identity, "commit", "-qm", message)
        self.data["headRefOid"] = git(self.root, "rev-parse", "HEAD")
        return self.data["headRefOid"]

    def test_runner_and_race(self) -> None:
        self.assertEqual(gates.evaluate("spec-link", self.data, self.root, self.base, self.head), [])
        self.assertEqual(gates.evaluate("size", self.data, self.root, self.base, self.head), [])
        with self.assertRaisesRegex(ValueError, "SHAs"):
            gates.evaluate("spec-link", self.data, self.root, "main", self.head)
        self.data["headRefOid"] = self.base
        with self.assertRaisesRegex(ValueError, "changed"):
            gates.evaluate("spec-link", self.data, self.root, self.base, self.head)

    def test_spec_must_exist_on_base(self) -> None:
        (self.root / "specs/042-sneak.md").write_text("# spec:042")
        (self.root / "src/app.py").write_text("x = 2\n")
        head = self.commit("add the spec and the code together")
        self.data["title"] = "feat: sneak [spec:042]"
        errors = gates.evaluate("spec-link", self.data, self.root, self.base, head)
        self.assertEqual(errors, ["Unknown spec:042"])

    def test_duplicate_spec_number(self) -> None:
        (self.root / "specs/001-other.md").write_text("# spec:001 again")
        base = self.commit("duplicate")
        (self.root / "src/app.py").write_text("x = 3\n")
        head = self.commit("change")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            gates.evaluate("spec-link", self.data, self.root, base, head)

    def test_size_counts_lines_from_git_and_agent_commits(self) -> None:
        (self.root / "src/big.py").write_text("x = 1\n" * 401)
        agent = ("-c", "user.name=copilot-swe-agent[bot]")
        agent += ("-c", "user.email=198982749+Copilot@users.noreply.github.com")
        head = self.commit("Add a big module", *agent)
        errors = gates.evaluate("size", self.data, self.root, self.base, head)
        self.assertEqual(errors, ["Agent diff exceeds 400 changed lines (403)"])

    def test_agent_label_and_protected_paths(self) -> None:
        (self.root / "GUARDRAILS").mkdir()
        (self.root / "GUARDRAILS/example.json").write_text("{}")
        head = self.commit("protected")
        self.data["labels"] = [{"name": "agent-authored"}]
        errors = gates.evaluate("size", self.data, self.root, self.base, head)
        self.assertEqual(errors, ["Agent changed protected paths: GUARDRAILS/example.json"])

    def test_cli_report_and_step_summary(self) -> None:
        self.data["title"] = "Add bulk export"
        metadata = self.tmp / "pr.json"
        metadata.write_text(json.dumps(self.data))
        summary = self.tmp / "summary.md"
        arguments = ["--metadata", str(metadata), "--candidate", str(self.root)]
        arguments += ["--base", self.base, "--head", self.head]
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as failed:
                gates.main(["spec-link", *arguments])
            self.assertEqual(failed.exception.code, 1)
            report = json.loads(output.getvalue())
            self.assertEqual(report["errors"], ["Source changes must reference spec:NNN"])
            self.assertIn("spec-link: fail", summary.read_text())
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as passed:
                gates.main(["size", *arguments])
            self.assertEqual(passed.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
