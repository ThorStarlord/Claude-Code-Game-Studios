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


## Ordered mixed-runtime review

The following dry run validates a pair of read-only Atlas handoffs without
contacting OpenCode or Claude:

    python scripts/studio_sequence.py --sequence docs/examples/atlas-client-proxies-review.sequence.json --worktree ../atlas-midgard-ccgs

To execute the actual providers, authenticate them on the workstation and add
`--execute --receipt-dir ../private-studio-receipts`. The sequence stops when
a provider fails or reports blocked, and never auto-merges.

The CLI runner includes full canonical role instructions in each task prompt.
This matters for Codex: `codex exec` is a top-level run and does not by itself
prove that a separately configured custom subagent was spawned.

A read-only review of an already-dirty worktree now fingerprints changed files
before and after the provider runs, to detect same-status edits. Git working
tree checks do not detect every possible write to ignored files or outside the
repository; native sandbox permissions remain the security boundary.

The sequence is intentionally not a workflow engine with restart/retry
semantics. User-facing documents must distinguish an interrupted handoff from
a verified completed feature.

## Repository identity check

Before actual execution, the runner verifies the task's declared repository
against the checkout's `origin` remote (GitHub SSH/HTTPS and equivalent
network URLs). A local checkout without a recognizable origin fails closed
instead of silently applying an Atlas task to another repository. Dry runs
do not require remote credentials.

This remains a correctness check, not an authorization to modify someone
else's repository. Native permissions and owner scope still govern.
