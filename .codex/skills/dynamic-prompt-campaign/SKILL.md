# Dynamic Prompt Campaign

Use this skill when working on sponsor-demo closeout, CI stabilization, UI/backend evidence alignment, or any task where progress must be gated by repo artifacts rather than chat memory.

## Governing Contract

- Operate only on repository files, CI artifacts, and explicit user-provided paths.
- Treat `AGENTS.md` and `docs/architecture/agentic_workflow/prompts/templates/` as the local doctrine source for dynamic campaign execution.
- Keep campaign state under `dynamic_campaigns/<campaign_name>/`.
- Each tranche must have a prompt, evidence, tests or artifact checks, and a writeback summary before advancing.
- Do not claim a tranche is complete unless its passing criteria are met by files, tests, GitHub Actions artifacts, or a clearly named manual verification note.

## Sponsor Demo Closeout Campaign

The active campaign lives at `dynamic_campaigns/sponsor_demo_closeout/`.

Execution order:

1. Stabilize the final sponsor report gate.
2. Add diagnosable target timing and recovery details.
3. Generate a requirement-to-proof matrix.
4. Clarify live-execution versus provider-required proof semantics.
5. Present installed-path/directory support consistently.
6. Present the MCP generation and LLM invocation story as one canonical flow.
7. Audit and align UI/backend labels, routes, and download behavior.
8. Write final closeout and durable blocker notes.

## Required Writeback

For every tranche, write or update:

- `dynamic_campaigns/sponsor_demo_closeout/prompts/ACTIVE-PROMPT.md`
- `dynamic_campaigns/sponsor_demo_closeout/outputs/tranche_summaries/<tranche>.md`
- Any evidence files needed under `dynamic_campaigns/sponsor_demo_closeout/outputs/evaluations/`

Closeout belongs in `dynamic_campaigns/sponsor_demo_closeout/outputs/closeout/CLOSEOUT.md`.
