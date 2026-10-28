# CCGS portability audit — October 2026 baseline

Source: Claude Code Game Studios 1.2.0, upstream commit
`05ad7c8a5b8aa2aa86bbd3439ae7cf7295cac418`.

## Observed coupling

| Surface | Observed mechanism | Migration status |
|---|---|---|
| 49 role definitions | `.claude/agents/*.md`, Claude tool/model metadata | First 4 portable; 45 pending |
| 74 skills | `.claude/skills/*/SKILL.md` | First 3 portable; 71 pending |
| Orchestration | Claude `Agent` and `AskUserQuestion` | Portable workflow guidance; automatic native delegation unverified |
| Runtime configuration | `project.yaml` and Claude `yaml-helper.sh` | Portable pilot uses independent manifest and explicit game layout |
| Hooks | `.claude/settings.json` and shell hooks | Claude legacy retained; shared enforcement not yet implemented |
| Verification | `studio-tests/` prompt/spec tests | First portable generator/runner unit tests added |
| Game layout | Code-root resolver assumes Godot `src/` | Portable doctor accepts explicit `game/` path |
| Session checkpoint | `production/session-state/active.md` | Runner returns local results; crash-safe resume pending |

The portability pilot deliberately uses **prefixed** native files so that it
cannot silently overwrite or disrupt the current Claude-native workflow.

## Technical decisions

1. The studio's role expertise and gameplay responsibility contracts must not
   contain provider-specific tool names.
2. Generate native formats deterministically with a Python standard-library
   command rather than three manually maintained copies.
3. Allow explicit, validated brownfield code/test paths; no implicit rewrite
   of existing game repositories.
4. Separate process exit status from user-experience or Godot verification.
5. Use native CLI tools for a first sequential mixed-runtime handoff; do not
   claim resilient scheduling, parallel writes or session migration.
6. Preserve host sandbox authority, isolated branches and no silent publication.

## Known risk and next migrations

- The original 45 remaining Claude roles include substantial engine-specific
  instructions, approval behaviors and skills references. They cannot be
  considered cross-runtime simply by converting frontmatter.
- The 71 remaining skills contain Claude-specific command injection, tools
  and missing portable equivalents. Convert by capability group.
- This pilot does not override existing Claude permissions; it cannot ensure
  unattended operation in every vendor CLI configuration.
- Actual native skill discovery and role invocation have not been executed in
  authenticated Claude/Codex/OpenCode sessions by this commit.
- Generation + offline tests are necessary but not sufficient evidence for
  feature development or provider compatibility.

## First product-construction experiment

Atlas Midgard: implement **Client Replica Presentation Proxies** under its
current Package 35 guest replica state without changing host authority.
Keep all CCGS framework source changes in this repository; use a distinct Atlas
branch for its game integration and preserve the solo First Journey release.

