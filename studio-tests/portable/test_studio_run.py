"""Offline tests of portable runtime task preparation and execution boundaries."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("studio_run", ROOT / "scripts/studio_run.py")
assert SPEC and SPEC.loader
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


def sample(**overrides):
    value = {
        "schema_version": 1, "task_id": "atlas-client-proxies",
        "role": "ccgs-gameplay-programmer", "runtime": "codex",
        "objective": "Implement client-side presentation proxies",
        "repository": "atlas-midgard", "allowed_paths": ["game", "tests"]
    }
    value.update(overrides)
    return value


class RunnerTests(unittest.TestCase):
    def test_commands_are_specific_to_runtime(self):
        self.assertEqual(RUN.native_command(sample(), "hello")[:4],
                         ["codex", "exec", "--sandbox", "workspace-write"])
        self.assertEqual(RUN.native_command(sample(runtime="opencode"), "hello")[:3],
                         ["opencode", "run", "--format"])
        self.assertEqual(RUN.native_command(sample(runtime="claude"), "hello")[:2],
                         ["claude", "-p"])

    def test_readonly_codex_sandbox(self):
        self.assertIn("read-only", RUN.native_command(sample(read_only=True), "hello"))
        self.assertFalse(RUN.within_scope("docs/secret.txt", ["game", "tests"]))

    def test_path_rejects_escape(self):
        for path in ("../game", "/game", "C:/game", "game/../docs", "game\\file"):
            with self.subTest(path=path), self.assertRaises(RUN.RunnerError):
                RUN.safe_path(path)

    def test_review_roles_cannot_request_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "task.json"
            filename.write_text(json.dumps(sample(role="ccgs-qa-tester", read_only=False)))
            self.assertTrue(RUN.load_task(filename)["read_only"])

    def create_repo(self, directory, branch):
        root = Path(directory)
        subprocess.run(["git", "init", "-q", "-b", branch, str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        (root / "README.md").write_text("Test")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
        return root

    def test_dry_run_does_not_contact_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.create_repo(directory, "ccgs-pilot")
            with mock.patch.object(RUN.shutil, "which", side_effect=AssertionError("Provider invoked")):
                result = RUN.run(sample(), root, False, None, 3)
            self.assertEqual(result["status"], "not_run")

    def test_main_execution_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.create_repo(directory, "main")
            with self.assertRaises(RUN.RunnerError):
                RUN.run(sample(), root, True, None, 3)


if __name__ == "__main__":
    unittest.main()
