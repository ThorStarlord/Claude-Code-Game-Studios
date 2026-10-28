# Portable studio authority policy

This policy is provider-neutral guidance for studio tasks. It is **not** an OS sandbox, credential boundary or automatic GitHub publication authorization. Native runtime permissions remain controlling.

## Modes
- `collaborative`: ask before consequential design choices and writes.
- `guided`: proceed on ordinary scoped implementation, ask on material scope change.
- `autonomous`: proceed on ordinary authorized repository construction and record decisions; stop at protected actions.

## Allowed within a bounded delegated task
Read project sources; create/edit files inside declared allowed paths; run local non-destructive checks; document decisions and observed results.

## Protected boundaries
Credentials and secret files; destructive operations; external financial or production changes; irreversible world/save schema migration; publication or release; unauthorized repository or branch changes; files outside declared scope; changes to the game's canonical thesis. These require independent authorization or narrowly scoped policies, regardless of mode.

## Least privilege and honesty
- Enforce actual sandbox and tool permissions; prompts are not security barriers.
- Run implementation in an isolated branch/worktree where possible.
- Do not infer success from empty output, missing tests, or provider errors.
- Never reuse another runtime's approval as an automatic grant.
- Do not route a blocked privileged action to another provider to bypass protection.
- Separate task execution from merge, deploy and release.

