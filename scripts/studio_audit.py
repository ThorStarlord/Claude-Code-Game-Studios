#!/usr/bin/env python3
"""Read-only portability inventory of the legacy CCGS 1.2.0 role/skill corpus.

This is a migration coverage map, not proof of behavioral equivalence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COUPLING = {
    "claude_agent_tool": re.compile(r"\bAgent\b|\bsubagent_type\b"),
    "claude_question_tool": re.compile(r"\bAskUserQuestion\b"),
    "claude_skill_injection": re.compile(r"!\x60"),
    "claude_model_pins": re.compile(r"(?m)^model:\s*(opus|sonnet|haiku|inherit)\s*$"),
    "claude_specific_path": re.compile(r"\.claude/|CLAUDE_PROJECT_DIR|CLAUDE_SKILL_DIR"),
    "godot_src_path_assumption": re.compile(r"(?:src/|source root.*src/)"),
    "claude_tool_grant": re.compile(r"(?m)^(?:allowed-tools|tools):"),
}


def inspect() -> dict:
    legacy_agents = sorted(path for path in (ROOT / ".claude/agents").glob("*.md")
                           if not path.name.startswith("ccgs-"))
    legacy_skills = sorted(path for path in (ROOT / ".claude/skills").glob("*/SKILL.md")
                           if not path.parent.name.startswith("ccgs-"))
    registry = json.loads((ROOT / "studio/manifest.json").read_text(encoding="utf-8"))
    records = []
    for kind, paths in (("role", legacy_agents), ("workflow", legacy_skills)):
        for path in paths:
            content = path.read_text(encoding="utf-8")
            signals = [label for label, pattern in COUPLING.items() if pattern.search(content)]
            records.append({
                "kind": kind,
                "name": path.parent.name if kind == "workflow" else path.stem,
                "source": path.relative_to(ROOT).as_posix(),
                "claude_specific_signals": signals,
                "review_required": bool(signals),
                "migration_status": "legacy-unreviewed"
            })
    counts = {label: sum(1 for r in records if label in r["claude_specific_signals"])
              for label in COUPLING}
    return {
        "schema_version": 1,
        "baseline_version": "1.2.0",
        "legacy_roles": len(legacy_agents),
        "legacy_skills": len(legacy_skills),
        "portable_pilot_roles": len(registry["roles"]),
        "portable_pilot_skills": len(registry["workflows"]),
        "coupling_signal_counts": counts,
        "notes": [
            "Pilot roles/skills are new prefixed integrations, not proof of parity with the 49/74 legacy corpus.",
            "Lexical coupling signals need manual context review; zero signals does not imply portability.",
            "Existing .claude files remain unchanged by this inventory.",
        ],
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory legacy Claude-specific CCGS dependencies")
    parser.add_argument("--summary", action="store_true", help="Omit per-file records")
    parser.add_argument("--expect-baseline", action="store_true", help="Fail if source is not the documented 49/74 baseline")
    args = parser.parse_args()
    report = inspect()
    if args.summary:
        report.pop("records")
    print(json.dumps(report, indent=2))
    if args.expect_baseline and (report["legacy_roles"], report["legacy_skills"]) != (49, 74):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
