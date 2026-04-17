# Tranche 002 Checkpoint: Windows Credential Execution Fix

## Tranche

`002-same-subnet-remote-dcom-proof`

## Evidence

- Focused workflow run: `24576385559`
- Result: failed during Remote DCOM proof after same-subnet client VM creation.
- Cleanup verification:
  - temporary client VM absent
  - temporary client NIC absent
  - temporary client OS disk absent
- Artifact inspected: `ci_artifacts/demo/windows/dcom/remote-activation-transcript.json`

## Finding

The Run Command payload parser fix worked: the artifact now preserves PowerShell messages. The next blockers were Windows setup issues:

- Server setup treated `New-Item HKLM:\SOFTWARE\Microsoft\Ole -Force` as fatal on an existing registry surface.
- Client proof attempted `Start-Process -Credential` under Azure Run Command and received `Access is denied`.

These are runtime setup issues, not Azure OIDC permission failures.

## Fix

- Server setup now checks `Test-Path` before creating the Microsoft Ole registry key.
- Client proof now executes as the matching local DCOM user through a one-shot scheduled task, then polls the proof JSON file.
- Regression coverage asserts the scheduled-task path is used and the old `Start-Process -Credential` path is not.

## Local Gates

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`: pass
- `python -m pytest -q`: `40 passed, 5 skipped`
- YAML parse for changed workflows: pass from previous checkpoint; workflow files unchanged in this fix.

## Next Prompt

Commit and push the Windows credential execution fix, rerun `Sponsor Remote DCOM Runtime Proof`, and classify the next artifact. If the scheduled task produces a parsed client proof, use the result to decide whether DCOM permissions/firewall need further hardening or whether the proof can be promoted.
