# Tranche 002 Checkpoint: Run Command Payload Preservation

## Tranche

`002-same-subnet-remote-dcom-proof`

## Evidence

- Focused workflow run: `24575880821`
- Result: failed during `Run same-subnet remote DCOM runtime proof`
- Azure status: same-subnet temporary Windows client VM created successfully; bridge VM started; cleanup completed.
- Artifact inspected: `ci_artifacts/demo/windows/dcom/dcom.summary.json`

## Finding

This was not an Azure permission or cleanup failure. The server setup and client invocation Run Command calls both returned `returncode=0`, but the proof parser saw blank stdout because it selected only `value[0].message` from Azure Run Command output.

That dropped later message entries containing the JSON proof payload, so the checks could not prove:

- `server_setup_ok`
- `client_proof_passed`
- `distinct_remote_context`
- `remote_sentinel_matches`

## Fix

`scripts/ci_verify.py` now queries `value[].message` as JSON and scans all message lines in reverse until it finds the emitted JSON proof object.

Regression coverage added:

- `test_vm_powershell_json_parses_later_run_command_messages`

## Local Gates

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`: pass
- `python -m pytest -q`: `40 passed, 5 skipped`
- YAML parse for `sponsor-remote-dcom-runtime.yml` and `sponsor-demo-e2e.yml`: pass

## Next Prompt

Commit and push the parser fix, then rerun `Sponsor Remote DCOM Runtime Proof`. If the focused proof passes, promote Remote DCOM into the full Sponsor Demo E2E. If it fails with parsed client/server payloads, classify the next blocker from the transcript instead of treating it as permissions.
