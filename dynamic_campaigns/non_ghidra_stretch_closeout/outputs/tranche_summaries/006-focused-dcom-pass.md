# Tranche 002 Complete: Focused Remote DCOM Passed

## Tranche

`002-same-subnet-remote-dcom-proof`

## Focused Run

- Run: `24577926238`
- URL: `https://github.com/evanking12/mcp-factory/actions/runs/24577926238`
- Artifact: `sponsor-remote-dcom-runtime`

## Passing Evidence

`ci_artifacts/demo/windows/dcom/dcom.summary.json` reports:

- `passed=true`
- `runtime_mode=remote_dcom_runtime`
- `remote_dcom_activation_claimed=true`
- `client_mode=azure-vm`
- `prog_id=WMI.StdRegProv`
- `com_transport=WMI over DCOM`
- `checks.server_setup_ok=true`
- `checks.client_invocation_ok=true`
- `checks.client_proof_passed=true`
- `checks.distinct_remote_context=true`
- `checks.remote_sentinel_matches=true`
- `gpt_tool_proof.tool_call_seen=true`
- `gpt_tool_proof.tool_result_seen=true`

Cleanup verification after the run:

- temporary client VM absent
- temporary client NIC absent
- temporary client OS disk absent

## Claim Boundary

This proves a controlled same-subnet remote DCOM fixture through WMI over DCOM. It does not claim arbitrary enterprise DCOM estate migration.

## Next Prompt

Run full `Sponsor Demo E2E` with `remote_dcom_run_id=24577926238`. The full run must import this focused artifact and fail if Remote DCOM is missing, blocked, local-only, or lacks GPT tool-call/tool-result proof.
