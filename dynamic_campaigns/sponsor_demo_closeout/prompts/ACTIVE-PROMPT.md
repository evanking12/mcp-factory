# Active Prompt: 001-stabilize-sponsor-report

Fix the sponsor final summary gate before moving to diagnostics.

## Required Work

- Import dynamic campaign doctrine locally.
- Mark broad `cmd.exe` scanning as optional diagnostic in Sponsor Demo E2E.
- Preserve deterministic `.cmd` fixture and GPT CMD proof as required CMD/BAT evidence.
- Make Windows summary and final sponsor summary distinguish required failures from optional diagnostic failures.
- Add focused tests proving optional `cmd_exe` failure does not fail the final sponsor report and required failures still do.

## Passing Criteria

- `python -m py_compile scripts/ci_verify.py scripts/gui_bridge.py`
- focused tests pass.
- Sponsor Demo E2E rerun reaches green final summary.
- Tranche summary records the run URL, artifact path, and reason this fixes the blocker.
