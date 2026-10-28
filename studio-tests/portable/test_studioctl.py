"""Offline contract tests for the portable studio generator.

Run: python -m unittest discover -s studio-tests/portable -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import tomllib
import unittest

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "studioctl.py"


class PortableStudioTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=REPO, check=False
        )

    def test_registry_valid(self) -> None:
        result = self.run_cli("validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["roles"], 4)

    def test_native_generation_and_drift_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli("generate", "--output-root", directory, "--write")
            self.assertEqual(result.returncode, 0, result.stderr)
            root = Path(directory)
            codex_agent = root / ".codex/agents/ccgs-gameplay-programmer.toml"
            opencode_agent = root / ".opencode/agents/ccgs-qa-tester.md"
            claude_agent = root / ".claude/agents/ccgs-producer.md"
            portable_skill = root / ".agents/skills/ccgs-adopt-project/SKILL.md"
            self.assertTrue(all(path.is_file() for path in (codex_agent, opencode_agent, claude_agent, portable_skill)))
            self.assertEqual(tomllib.loads(codex_agent.read_text())["name"], "ccgs-gameplay-programmer")
            self.assertIn("edit: deny", opencode_agent.read_text())
            self.assertTrue(portable_skill.read_text().startswith("---\nname: ccgs-adopt-project"))
            self.assertEqual(self.run_cli("generate", "--output-root", directory, "--check").returncode, 0)
            original = codex_agent.read_text()
            self.assertEqual(self.run_cli("generate", "--output-root", directory, "--write").returncode, 0)
            self.assertEqual(original, codex_agent.read_text())
            codex_agent.write_text(original + "\n# changed by hand")
            self.assertEqual(self.run_cli("generate", "--output-root", directory, "--check").returncode, 1)

    def test_does_not_overwrite_existing_user_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".claude/agents/ccgs-producer.md"
            path.parent.mkdir(parents=True)
            path.write_text("user authored definition")
            result = self.run_cli("generate", "--output-root", directory, "--write")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_text(), "user authored definition")
            self.assertFalse((Path(directory) / ".codex").exists())

    def test_explicit_godot_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "game").mkdir()
            (root / "tests").mkdir()
            (root / "project.godot").write_text("config_version=5")
            (root / "studio-layout.json").write_text(json.dumps({
                "schema_version": 1, "engine": "godot", "code_root": "game", "test_root": "tests"
            }))
            response = self.run_cli("doctor", "--runtime", "codex", "--project-root", directory)
            self.assertEqual(response.returncode, 0, response.stderr)
            report = json.loads(response.stdout)
            self.assertEqual(report["source_root"], "game")
            self.assertTrue(report["engine_project_detected"])

    def test_ambiguous_godot_layout_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "src").mkdir()
            (Path(directory) / "game").mkdir()
            response = self.run_cli("doctor", "--runtime", "codex", "--project-root", directory)
            self.assertEqual(response.returncode, 2)
            self.assertIsNone(json.loads(response.stdout)["source_root"])


if __name__ == "__main__":
    unittest.main()
