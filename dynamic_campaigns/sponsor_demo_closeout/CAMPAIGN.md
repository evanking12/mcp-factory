# Dynamic Campaign: Sponsor Demo Closeout

## Objective

Make the sponsor-facing GitHub Actions report green, observable, analytical, and diagnosable, while ensuring the web UI reflects the Azure backend behavior and proof semantics.

## Gates

1. Final sponsor demo artifact is green with `cmd_exe` as optional diagnostic and deterministic CMD/BAT proof required.
2. Slow and failed targets explain analyzer time, bridge guard time, retry/restart time, VM restart time, post-grace health, and failure class.
3. Final report includes a requirement-to-proof matrix.
4. Final report and docs distinguish live-execution proofs from provider-required proofs.
5. Installed path and directory support is explicitly mapped and presented.
6. MCP generation and LLM invocation proof is one coherent story.
7. UI/backend route and label alignment is verified.
8. Closeout records green run, artifact paths, known risks, optional diagnostics, and durable family-blocker writebacks.

## Current Canonical Evidence

- Latest parsed failing run before this campaign: `https://github.com/evanking12/mcp-factory/actions/runs/24538695310`
- Failure reason: final summary failed because `cmd_exe` was required and produced no matching invocables after bridge recovery churn.
- Replacement proof: deterministic CMD/BAT fixture in the GPT format matrix remains required and proves live command-script execution.
