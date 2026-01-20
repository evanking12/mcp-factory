# Contributing

## Workflow
- Create an Issue before major work.
- Create a branch from `main`: `feat/<short-name>` or `fix/<short-name>`.
- Open a Pull Request (PR) and link the Issue (e.g., "Closes #12").

## Commit style
- Keep commits small and descriptive.
- Example: `Add dumpbin exports parser` / `Update inventory schema v0`.

## Code expectations
- Prefer deterministic outputs (write artifacts to `artifacts/<target>/`).
- Do not commit proprietary binaries unless licensing allows.
- Add/extend tests for parsing logic when possible.
