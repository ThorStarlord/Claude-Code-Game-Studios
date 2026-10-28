#!/usr/bin/env python3
"""Opt-in cross-runtime task runner: dry-run by default, never auto-merges.

Provider CLIs and their sandboxes remain the actual security boundary.
Git diff validation is a postcondition, not preventative containment.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path, PurePosixPath
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = ("claude", "codex", "opencode")
REQUIRED = ("schema_version", "task_id", "role", "runtime", "objective", "repository", "allowed_paths")


class RunnerError(Exception):
    pass


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or value.startswith("/"):
        raise RunnerError(f"Unsafe relative path: {value!r}")
    parts = value.strip("/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RunnerError(f"Unsafe relative path: {value!r}")
    return PurePosixPath(*parts).as_posix()


def load_task(filename: Path) -> dict:
    task = json.loads(filename.read_text(encoding="utf-8"))
    if not isinstance(task, dict) or any(key not in task for key in REQUIRED):
        raise RunnerError("Missing required portable task fields")
    if not isinstance(task["repository"], str) or not task["repository"].strip():
        raise RunnerError("Task repository must identify a destination")
    if task["schema_version"] != 1 or task["runtime"] not in RUNTIMES:
        raise RunnerError("Unsupported task schema/runtime")
    if not isinstance(task["task_id"], str) or not task["task_id"].replace("-", "").isalnum():
        raise RunnerError("Invalid task ID")
    if not isinstance(task["objective"], str) or len(task["objective"].strip()) < 10:
        raise RunnerError("Task objective is too short")
    if not isinstance(task["allowed_paths"], list) or not task["allowed_paths"]:
        raise RunnerError("Task requires allowed_paths")
    task["allowed_paths"] = [safe_path(path) for path in task["allowed_paths"]]
    roles = {r["id"]: r for r in json.loads((ROOT / "studio/manifest.json").read_text())["roles"]}
    if task["role"] not in roles:
        raise RunnerError(f"Unknown portable role: {task['role']}")
    task["read_only"] = roles[task["role"]]["kind"] == "review" or bool(task.get("read_only", False))
    if task.get("model") is not None:
        if not isinstance(task["model"], str) or not task["model"] or task["model"].startswith("-"):
            raise RunnerError("Invalid model override")
    return task


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RunnerError(f"Git error in {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def checkout_state(root: Path, execute: bool, read_only: bool) -> tuple[str, str, str]:
    if not root.is_dir() or Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise RunnerError("Expected the exact repository checkout root")
    branch = git(root, "branch", "--show-current")
    sha = git(root, "rev-parse", "HEAD")
    baseline = git(root, "status", "--porcelain", "-uall")
    if execute and branch in ("", "main", "master"):
        raise RunnerError("Execution requires a named non-main feature branch")
    if execute and baseline and not read_only:
        raise RunnerError("Mutating tasks require a clean checkout; isolate/commit prior work")
    return branch, sha, baseline


def verify_repo_identity(root: Path, expected: str) -> str:
    """Fail closed when a provider task targets the wrong Git repository.

    Accept normal GitHub HTTPS or SSH origin URLs and an exact owner/repo
    selector, or a repository-name-only selector for portable task examples.
    """
    remote = git(root, "remote", "get-url", "origin")
    value = remote.removesuffix(".git").rstrip("/")
    if "://" in value:
        # https://github.com/owner/name or ssh://git@github.com/owner/name
        parts = value.split("/")
        if len(parts) < 2:
            raise RunnerError("Unrecognizable origin remote URL")
        actual = "/".join(parts[-2:])
    elif ":" in value:
        # git@github.com:owner/name
        actual = value.rsplit(":", 1)[-1]
    else:
        raise RunnerError("Unsupported non-network origin remote; refusing execution")
    if "/" not in actual or actual.startswith("/"):
        raise RunnerError("Cannot identify owner/repository from origin")
    requested = expected.strip().lower().removesuffix(".git")
    actual = actual.strip().lower()
    if requested != actual and requested != actual.rsplit("/", 1)[-1]:
        raise RunnerError(f"Task targets {expected!r}, but checkout origin is {actual!r}")
    return actual


def changed_paths(root: Path) -> list[str]:
    tracked = git(root, "diff", "--name-only", "HEAD").splitlines()
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p.replace("\\", "/") for p in (*tracked, *untracked) if p})


def within_scope(path: str, allowed: list[str]) -> bool:
    return any(path == base or path.startswith(base + "/") for base in allowed)


def make_prompt(task: dict, sha: str) -> str:
    lines = [
        "CCGS PORTABLE TASK",
        f"Task ID: {task['task_id']}",
        f"Studio role: {task['role']}",
        f"Objective: {task['objective']}",
        f"Candidate commit: {sha}",
        f"Allowed edit roots: {', '.join(task['allowed_paths'])}",
        "Use the target game's own canonical architecture, product thesis and test policy.",
        "Do not modify any file outside the allowed roots or weaken persistence, game-authority or networking boundaries.",
        "Do not publish or merge. Host permissions always override instructions.",
        "Return changed files, observed checks, unverified claims and blockers.",
    ]
    for criterion in task.get("acceptance_criteria", []):
        lines.append(f"Acceptance criterion: {criterion}")
    if task.get("read_only", False):
        lines.append("This is READ ONLY. Make no file, Git or project state changes.")
    lines.extend([
        "",
        "Required specialist behavior (canonical portable role instructions):",
        canonical_role_instructions(task),
    ])
    return "\n".join(lines)


def working_fingerprint(root: Path) -> dict[str, str]:
    """Detect in-place changes to dirty worktrees during read-only reviews.

    Git status alone cannot detect an edit whose modified/untracked status
    remains the same. This is not a security sandbox: processes may touch
    ignored files or paths outside the repository.
    """
    result: dict[str, str] = {}
    for name in changed_paths(root):
        path = root / name
        if not path.is_file():
            result[name] = "<non-file>"
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        result[name] = digest.hexdigest()
    return result


def canonical_role_instructions(task: dict) -> str:
    """Inject the role regardless of native subagent availability.

    Codex exec is a top-level process; native custom agents do not
    automatically run just because a role name appears in a prompt.
    """
    manifest = json.loads((ROOT / "studio/manifest.json").read_text(encoding="utf-8"))
    role = next((item for item in manifest["roles"] if item["id"] == task["role"]), None)
    if role is None:
        raise RunnerError(f"Unknown role: {task['role']}")
    source = (ROOT / role["source"]).resolve()
    if not source.is_relative_to((ROOT / "studio").resolve()):
        raise RunnerError("Role source escapes portable studio")
    content = source.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3 or not parts[2].strip():
        raise RunnerError("Role source is missing its instruction body")
    return parts[2].strip()


def native_command(task: dict, prompt: str) -> list[str]:
    runtime = task["runtime"]
    if runtime == "claude":
        result = ["claude", "-p", "--output-format", "json", "--agent", task["role"]]
        # Provider-native permissions remain active. No bypassPermissions.
        if task.get("model"):
            result += ["--model", task["model"]]
    elif runtime == "codex":
        result = ["codex", "exec", "--sandbox",
                  "read-only" if task.get("read_only", False) else "workspace-write", "--json"]
        if task.get("model"):
            result += ["-m", task["model"]]
        # codex exec is a top-level agent. Prompting a role does not prove
        # that a named custom Codex subagent was actually spawned.
    else:
        result = ["opencode", "run", "--format", "json", "--agent", task["role"]]
        if task.get("model"):
            result += ["--model", task["model"]]
        # Explicitly avoid OpenCode --auto unless separately authorized.
    return [*result, prompt]


def private_save(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(content)


def run(task: dict, root: Path, execute: bool, receipts: Path | None, timeout: int) -> dict:
    branch, sha, before = checkout_state(root, execute, task.get("read_only", False))
    if execute:
        verify_repo_identity(root, task["repository"])
    if task.get("base_commit") and task["base_commit"] != sha:
        raise RunnerError(f"Base SHA mismatch; expected {task['base_commit']}, found {sha}")
    command = native_command(task, make_prompt(task, sha))
    readonly_fingerprint = working_fingerprint(root) if task.get("read_only", False) else None
    record = {
        "schema_version": 1, "task_id": task["task_id"], "runtime": task["runtime"],
        "status": "not_run", "base_commit": sha, "worktree": str(root),
        "changed_files": [], "verification": [], "exit_code": None,
        "reason": "Dry run only; no provider invoked", "output_path": None,
    }
    if not execute:
        record["command_preview"] = command[:-1] + ["<task-prompt>"]
        record["branch"] = branch
        return record
    if shutil.which(command[0]) is None:
        record.update(status="blocked", reason=f"Provider not installed: {command[0]}")
        return record
    stdout, stderr, code = "", "", None
    timed_out = False
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
    changes = changed_paths(root)
    record.update(changed_files=changes, exit_code=code)
    unexpected = [p for p in changes if not within_scope(p, task["allowed_paths"])]
    if task.get("read_only", False) and (
        git(root, "status", "--porcelain", "-uall") != before
        or working_fingerprint(root) != readonly_fingerprint
    ):
        record.update(status="blocked", reason="Read-only task changed Git working state")
    elif unexpected:
        record.update(status="blocked", reason=f"Out-of-scope changes detected (not reverted): {unexpected}")
    elif timed_out:
        record.update(status="interrupted", reason=f"Provider timed out after {timeout} seconds")
    elif code:
        record.update(status="failed", reason=f"Provider exited nonzero: {code}")
    else:
        record.update(status="completed",
                      reason="Provider process exited zero; acceptance criteria still require independent verification")
    if receipts:
        label = f"{task['task_id']}-{task['runtime']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
        stdout_path = receipts / f"{label}.stdout.txt"
        private_save(stdout_path, stdout)
        private_save(receipts / f"{label}.stderr.txt", stderr)
        record["output_path"] = str(stdout_path)
        private_save(receipts / f"{label}.json", json.dumps(record, indent=2) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Opt-in CCGS CLI handoff; dry-run unless --execute")
    parser.add_argument("--task", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--receipt-dir", help="Local private logs; use a gitignored/outside-repo directory")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 86400:
            raise RunnerError("Timeout must be 1..86400 seconds")
        task = load_task(Path(args.task))
        record = run(task, Path(args.worktree).resolve(), args.execute,
                     Path(args.receipt_dir).resolve() if args.receipt_dir else None, args.timeout)
        print(json.dumps(record, indent=2))
        return 0 if record["status"] in ("completed", "not_run") else 2
    except (RunnerError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"STUDIO_RUN_ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
