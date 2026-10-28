# Portable execution: bounded CLI handoffs

This is an opt-in execution pilot, **not** a credential broker, sandbox,
autonomous daemon or verified full multi-provider scheduler. The adapter calls
the supported CLI of each installed coding agent. The host agent and OS own
actual permissions. Code review of a generated file does not prove runtime
discovery or model execution.

## Single-task workflow

Write a task JSON following `studio/schemas/task.schema.json`. The Atlas
example is `docs/examples/atlas-client-proxies.task.json`.

Preview:

    python scripts/studio_run.py --task docs/examples/atlas-client-proxies.task.json --worktree ../atlas-midgard-ccgs

Execute only after preparing a clean non-main branch and authenticating the
chosen provider:

    python scripts/studio_run.py --task docs/examples/atlas-client-proxies.task.json --worktree ../atlas-midgard-ccgs --execute --receipt-dir ../private-studio-receipts

CLI strategies:
- Claude: `claude -p --output-format json --agent ccgs-<role>`.
- Codex: `codex exec --sandbox workspace-write --json` with the role in
  the task prompt; this does **not** prove a named custom subagent ran.
- OpenCode: `opencode run --format json --agent ccgs-<role>`.

Read-only tasks use the Codex read-only sandbox and review-role instructions.
No provider's bypass-permission option is passed. Automatic approval is not
granted by setting task autonomy to autonomous.

The runner rejects writes on a dirty checkout, execution on main/master,
incorrect base commit, unsafe allowed path, and unknown role. After execution,
it checks for changed files outside the declared scope and reports a BLOCKED
result. This post-run detection **does not prevent or revert a filesystem write**.

An exit code of zero is process success, not behavioral qualification. The
verification receipt remains empty until evidence is independently obtained.

## Private evidence

Pass `--receipt-dir` to save the run receipt and raw stdout/stderr with file
mode 0600. Provider output may contain proprietary information or secrets;
choose an ignored location outside Git. Never upload raw provider logs.
Parallel writes and retries are not automatically coordinated.

## Future continuation

The pilot's first mixed-provider flow is sequential: Codex implements, OpenCode
performs an independent read-only review of the dirty worktree, and a producer
reconciles. Native installed-provider execution is still unverified here. Add
crash-safe resumability and concurrent worktree orchestration only after real
usage demonstrates the need.

