"""Offline contract tests for sequential multi-provider studio handoffs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import studio_sequence as SEQ
import studio_run as RUN


class SequenceTests(unittest.TestCase):
    def sample(self, **overrides) -> dict:
        data = {
            "schema_version": 1,
            "task_id": "atlas-pilot-implement",
            "role": "ccgs-gameplay-programmer",
            "runtime": "codex",
            "objective": "Implement a bounded guest presentation feature",
            "repository": "atlas-midgard",
            "allowed_paths": ["game", "tests"]
        }
        data.update(overrides)
        return data

    def write_sequence(self, root: Path, second: bool = True) -> Path:
        (root / "impl.json").write_text(json.dumps(self.sample()))
        steps = [{"task": "impl.json"}]
        if second:
            (root / "review.json").write_text(json.dumps(self.sample(
                task_id="atlas-pilot-review", runtime="opencode",
                role="ccgs-godot-specialist", read_only=True
            )))
            steps.append({"task": "review.json"})
        manifest = root / "sequence.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "sequence_id": "atlas-pilot", "steps": steps
        }))
        return manifest

    def test_loads_ordered_normalized_roles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sequence(Path(directory))
            identifier, steps = SEQ.sequence_manifest(path)
            self.assertEqual(identifier, "atlas-pilot")
            self.assertEqual([step["runtime"] for _, step in steps], ["codex", "opencode"])
            self.assertTrue(steps[1][1]["read_only"])

    def test_stops_at_failed_step(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sequence(Path(directory))
            with mock.patch.object(SEQ, "run", side_effect=[{
                "status": "blocked", "reason": "provider not installed",
                "changed_files": [], "output_path": None
            }]) as execute:
                report = SEQ.perform(path, Path(directory), True, Path(directory), 10)
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["executed_steps"], 1)
            self.assertEqual(execute.call_count, 1)

    def test_successful_sequential_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sequence(Path(directory))
            def fake_run(task, *_args):
                return {"status": "completed", "changed_files": ["game/proxy.gd"], "output_path": "private"}
            with mock.patch.object(SEQ, "run", side_effect=fake_run) as execute:
                report = SEQ.perform(path, Path(directory), True, Path(directory), 10)
            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["executed_steps"], 2)
            self.assertEqual(execute.call_count, 2)

    def test_duplicate_ids_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_sequence(root)
            task = self.sample(runtime="opencode", role="ccgs-qa-tester")
            (root / "review.json").write_text(json.dumps(task))
            with self.assertRaises(RUN.RunnerError):
                SEQ.sequence_manifest(path)

    def test_exec_requires_private_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sequence(Path(directory))
            with self.assertRaises(RUN.RunnerError):
                SEQ.perform(path, Path(directory), True, None, 10)

    def test_dryrun_is_not_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_sequence(Path(directory), second=False)
            with mock.patch.object(SEQ, "run", return_value={
                "status": "not_run", "reason": "dry run", "changed_files": [], "output_path": None
            }):
                report = SEQ.perform(path, Path(directory), False, None, 10)
            self.assertEqual(report["status"], "not_run")
            self.assertEqual(report["executed_steps"], 0)


if __name__ == "__main__":
    unittest.main()
