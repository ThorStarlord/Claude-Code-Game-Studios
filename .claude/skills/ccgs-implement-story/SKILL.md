---
name: ccgs-implement-story
description: Implement a bounded game story using a specialist role, existing architecture and proportional changed-behavior checks.
---

<!-- @generated CCGS portable studio -->

# Implement One Story

1. Obtain a specific objective, task ID, allowed paths, existing architecture authority and acceptance criteria.
2. Check that the goal fits the current game roadmap. Missing prerequisite or out-of-scope changes must be reported, not invented.
3. Select the appropriate implementation specialist by responsibility, independent of which runtime hosts it.
4. Implement directly in the project's actual source root; preserve gameplay, persistence and engine boundaries.
5. Add focused checks to the existing verification mechanism and run the available tests.
6. Return changed paths and explicit executed/not-run evidence, with a durable handoff to review.

Do not demand a new CCGS GDD or sprint process when the game already has canonical decisions. Autonomy follows studio/policies/autonomy.md; it cannot override host permissions.
