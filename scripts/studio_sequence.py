#!/usr/bin/env python3
"""Sequential, opt-in cross-runtime studio handoffs (no daemon, no auto-merge).

Each step references a versioned task JSON file. Runtime model execution is
explicitly opt-in; dry runs resolve and validate the entire plan.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from studio_run import RunnerError, load_task, run

IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")


def sequence_manifest(path: Path) -> tuple[str, list[tuple[str, dict]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RunnerError("Unknown sequence manifest schema")
    identifier = payload.get("sequence_id", "")
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise RunnerError("Invalid sequence ID")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= 12:
        raise RunnerError("Sequence requires between 1 and 12 steps")
    resolved: list[tuple[str, dict]] = []
    for item in raw_steps:
        if not isinstance(item, dict) or set(item) != {"task"}:
            raise RunnerError("Every sequence step must contain only a task path")
        relative = item["task"]
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise RunnerError("Invalid step task path")
        taskfile = (path.parent / relative).resolve()
        if not taskfile.is_relative_to(path.parent.resolve()) or not taskfile.is_file():
            raise RunnerError(f"Missing or escaped sequence task: {relative}")
        task = load_task(taskfile)
        if any(previous[1]["task_id"] == task["task_id"] for previous in resolved):
            raise RunnerError(f"Duplicate task ID: {task['task_id']}")
        resolved.append((str(taskfile), task))
    return identifier, resolved


def perform(manifest_path: Path, worktree: Path, execute: bool, receipt_dir: Path | None, timeout: int) -> dict:
    name, steps = sequence_manifest(manifest_path)
    if execute and receipt_dir is None:
        raise RunnerError("Execution requires --receipt-dir for a durable private task audit")
    results: list[dict] = []
    for location, task in steps:
        result = run(task, worktree, execute, receipt_dir, timeout)
        results.append({
            "step": len(results) + 1,
            "task_file": location,
            "task_id": task["task_id"],
            "runtime": task["runtime"],
            "status": result["status"],
            "changed_files": result.get("changed_files", []),
            "reason": result.get("reason"),
            "receipt_path": result.get("output_path"),
        })
        if execute and result["status"] != "completed":
            break
    all_completed = len(results) == len(steps) and all(x["status"] == "completed" for x in results)
    return {
        "schema_version": 1,
        "sequence_id": name,
        "status": "completed" if all_completed else ("not_run" if not execute else "blocked"),
        "planned_steps": len(steps),
        "executed_steps": len(results) if execute else 0,
        "steps": results,
        "note": (
            "Provider process exits are not proof of feature acceptance. No Git merge or release was performed."
            if execute else "Dry run only. No provider CLI was invoked."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sequential portable-studio plan (dry run by default)")
    parser.add_argument("--sequence", required=True, help="JSON task-sequence manifest")
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 86400:
            raise RunnerError("Timeout must be in 1..86400")
        result = perform(
            Path(args.sequence).resolve(), Path(args.worktree).resolve(), args.execute,
            Path(args.receipt_dir).resolve() if args.receipt_dir else None, args.timeout
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in ("completed", "not_run") else 2
    except (RunnerError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"STUDIO_SEQUENCE_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
