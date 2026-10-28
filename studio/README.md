# Portable CCGS Studio — first production increment

This directory is the **provider-neutral core pilot**; it does not replace the
existing 49 Claude Code roles or 74 skills. Those stay active and unchanged until
their behavior has been ported and qualified. No unsupported equivalence claim is
made between the legacy skills and these three portable workflows.

## What is implemented

- Four canonical roles in `studio/roles`.
- Three Agent Skills in `studio/workflows`.
- `studio/manifest.json` as the role/workflow registry.
- Task and result JSON schemas.
- Deterministic standard-library Python compiler for Claude, Codex and OpenCode.
- Read-only doctor for existing project code/test roots.
- Offline generator tests.

## Commands

From the CCGS repository:

`python scripts/studioctl.py validate`

`python scripts/studioctl.py generate --runtime all`
shows what would be written and makes no changes.

`python scripts/studioctl.py generate --runtime all --write`
writes generated agent and skill files; it refuses to overwrite pre-existing
user-authored definitions. To check reproducibility:

`python scripts/studioctl.py generate --runtime all --check`

Before adopting an existing Godot project:

`python scripts/studioctl.py doctor --runtime codex --project-root /path/to/atlas`

Set an explicit `studio-layout.json` in Atlas (see `studio/project-layout.example.json`)
to specify `code_root: game`. Never assume all Godot code lives in `src/`.

## Supported runtime outputs

- Claude: `.claude/agents/ccgs-*.md` and `.claude/skills/ccgs-*/SKILL.md`.
- Codex: `.codex/agents/ccgs-*.toml` and `.agents/skills/ccgs-*/SKILL.md`.
- OpenCode: `.opencode/agents/ccgs-*.md` plus the same shared Agent Skills.

All generated names are prefixed, so the legacy Claude agents and skills remain
intact. Native file format compatibility is supported for these four roles and
three workflows. Runtime discovery, actual model execution, external permissions
and semantic parity require execution in each installed agent. Generation alone
does not establish any of those claims.

## Authority boundaries

Read `studio/policies/autonomy.md`. The policies in prompts are
guidance, not a security boundary. Host sandbox, source control and credentials
remain authoritative. Do not infer GitHub merge, publishing or deployment
permission from an autonomous studio task.

## Deliberate migration boundary

Port the remaining roles/workflows incrementally with source-of-truth ownership
and behavioral parity checks. Do not naïvely copy Claude's `Agent` or
`AskUserQuestion` instructions into another runtime and call it portable.
