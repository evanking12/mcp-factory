# Tranche 002 Checkpoint: Native Windows DCOM Setup

## Tranche

`002-same-subnet-remote-dcom-proof`

## Evidence

- Focused workflow run: `24576877981`
- Result: failed during Remote DCOM proof after same-subnet client VM creation.
- Cleanup verification:
  - temporary client VM absent
  - temporary client NIC absent
  - temporary client OS disk absent
- Artifact inspected: `ci_artifacts/demo/windows/dcom/remote-activation-transcript.json`

## Finding

The scheduled-task path was reached, but the artifact showed two Windows-native setup issues:

- The server-side PowerShell registry provider reported unauthorized access creating the policy path.
- `schtasks.exe` could not resolve `.\\mcpdcom` to a SID on the client.

## Fix

- Server DCOM toggles now use `reg.exe add` for:
  - `EnableDCOM`
  - `LocalAccountTokenFilterPolicy`
- Client scheduled task now uses `$env:COMPUTERNAME\\$username` instead of `.\\$username`.
- The DCOM wrapper scripts continue after native command errors so they can emit JSON diagnostics.

## Local Gates

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`: pass
- `python -m pytest -q`: `40 passed, 5 skipped`

## Next Prompt

Commit and push, rerun `Sponsor Remote DCOM Runtime Proof`, and inspect the parsed client proof. If DCOM activation itself fails after these native setup fixes, collect the exact COM/DCOM error and add launch/access permission hardening or event-log artifacts.
