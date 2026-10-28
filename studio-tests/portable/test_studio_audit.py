"""Preserve coverage truth for original legacy CCGS roles and skills."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import studio_audit as AUDIT


class InventoryTests(unittest.TestCase):
    def test_inventory_counts_legacy_without_prefixed_pilot(self):
        inventory = AUDIT.inspect()
        self.assertEqual(inventory["legacy_roles"], 49)
        self.assertEqual(inventory["legacy_skills"], 74)
        self.assertEqual(inventory["portable_pilot_roles"], 4)
        self.assertEqual(inventory["portable_pilot_skills"], 3)
        self.assertEqual(len(inventory["records"]), 123)

    def test_skill_tool_coupling_is_visible(self):
        inventory = AUDIT.inspect()
        self.assertGreater(inventory["coupling_signal_counts"]["claude_specific_path"], 0)
        self.assertTrue(any(
            row["name"] == "team-combat"
            and "claude_agent_tool" in row["claude_specific_signals"]
            for row in inventory["records"]
        ))


if __name__ == "__main__":
    unittest.main()
