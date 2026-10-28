# CCGS portable studio — Codex and compatible coding agents

This repository includes an existing Claude-native studio and a **new,
prefixed portable pilot**. Do not replace or reformat legacy `.claude/` role
and workflow files without a deliberate migration.

Read `studio/README.md` and `studio/policies/autonomy.md` when using portable
roles. `studio/manifest.json` lists their canonical source definitions.

- Portable roles: `ccgs-producer`, `ccgs-gameplay-programmer`,
  `ccgs-godot-specialist`, `ccgs-qa-tester`.
- Portable workflows: `ccgs-adopt-project`, `ccgs-implement-story`,
  `ccgs-verify-story`.
- Native Codex roles: `.codex/agents/ccgs-*.toml`.
- Native Agent Skills: `.agents/skills/ccgs-*/SKILL.md`.

Implement changes in bounded, authorized paths. Prefer the existing game
repository's real design and test authorities over new process documents.
Report missing runtime evidence as NOT RUN, not PASS.

Never auto-merge, force-push, release, expose credentials or bypass runtime
permissions because a portable studio policy says autonomous.

