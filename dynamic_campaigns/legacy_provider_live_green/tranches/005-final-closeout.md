# Tranche 005 - Final Closeout

## Goal

Record the canonical green Sponsor Demo E2E run, artifact paths, remaining
risks, and iteration shortcuts.

## Green Run

- Workflow: Sponsor Demo E2E
- Run: https://github.com/evanking12/mcp-factory/actions/runs/24542583216
- Artifact: `sponsor-demo-e2e`
- Commit: `6c60c51`

## Verified Artifact Facts

- `final-summary.json` has `passed=true`.
- GPT format matrix: `13/13` live execution proofs.
- Required provider-required cases: `0`.
- Windows required targets: `6/6`.
- `sponsor-report.html` is present in the artifact.
- Slow targets recorded by diagnostics: `kernel32_dll`, `notepad_exe`.

## Iteration Shortcuts Proven

- Sponsor Demo Report Only passed against run `24541068734`.
- Sponsor Report Fixture passed.
- Sponsor Demo E2E with `skip_windows_targets=true` and `only_gpt_case=jsonrpc` passed in about 3 minutes and produced GPT `tool_call`, `tool_result`, and sentinel output from the hosted JSON-RPC adapter.

## Known Risks

- The CORBA, RPC IDL, and JNDI providers are deterministic adapters, not production ORB/RPC/JNDI runtimes. This is intentional for sponsor-demonstrable live tool-call behavior.
- Windows bridge runs still depend on Session 1 and Azure Run Command availability.
- `cmd_exe` remains optional diagnostic; deterministic `.cmd` is the required CMD/BAT evidence.

## Status

Complete.
