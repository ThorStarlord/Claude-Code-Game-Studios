---
name: ccgs-verify-story
description: Reconcile an implemented game story against acceptance criteria and observed execution, without fabricated passes.
---
# Verify and Reconcile Story

1. Read the story objective, actual candidate SHA, changed-file list and relevant acceptance criteria.
2. Confirm paths and source ownership; detect unrelated modifications or authority boundary changes.
3. Review implementation risks. Run changed-behavior checks and canonical repository verification only when available and proportionate.
4. For player-visible claims, seek rendered observation; distinguish visual appearance from gameplay feel.
5. Record each criterion as executed-pass, executed-fail, not-run or not-assessed, with source or command.
6. Report remaining defects and the smallest appropriate continuation. Do not automatically merge, release or alter tests to manufacture a PASS.

