# Sponsor Demo Closeout Campaign

This campaign is the repo-local evidence workflow for getting the sponsor demo to a stable green, diagnosable state.

The campaign follows the doctrine imported in `AGENTS.md` and `docs/architecture/agentic_workflow/prompts/templates/`. It may operate only on repo files, CI artifacts, and explicit user-provided paths.

Primary stop gate: one canonical green Sponsor Demo E2E run with `ci_artifacts/demo/final-summary.md`, `ci_artifacts/demo/final-summary.json`, per-target Windows summaries, GPT matrix artifacts, and UI/backend alignment evidence.

Active prompt: `prompts/ACTIVE-PROMPT.md`

Tranche summaries: `outputs/tranche_summaries/`

Closeout: `outputs/closeout/CLOSEOUT.md`
