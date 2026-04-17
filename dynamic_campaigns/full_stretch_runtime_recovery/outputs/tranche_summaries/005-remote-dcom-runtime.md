# Tranche 005 Summary

Status: implementation ready for authoritative workflow validation.

Scope:
- Added `windows-remote-dcom-runtime-proof`, which configures a controlled
  WScript.Shell DCOM proof user on the bridge VM, invokes that COM object from
  a distinct temporary Azure Windows client VM, records the remote activation
  transcript, and cleans proof-only server artifacts.
- Added focused workflow `Sponsor Remote DCOM Runtime Proof`, which provisions
  a temporary Windows client VM in the bridge VM subnet, runs the proof, uploads
  artifacts, and deletes the temporary VM, disk, and NIC in an `always()` step.
- The proof fails closed. It does not claim remote DCOM if activation does not
  occur from a distinct client context or if the remote sentinel read fails.

Local validation before push:
- `python -m py_compile scripts/ci_verify.py`
- `python scripts/ci_verify.py windows-remote-dcom-runtime-proof --help`
- `python -m pytest -q` passed: `36 passed, 5 skipped`.

Focused workflow gate:
- Pending. The tranche is not complete until the focused workflow proves:
  - `ci_artifacts/demo/windows/dcom/dcom.summary.json` has `passed=true`.
  - `runtime_mode=remote_dcom_runtime`.
  - `remote_dcom_activation_claimed=true`.
  - The transcript shows distinct client and remote server computer names.
  - The remote COM object reads the deterministic sentinel from the server.
  - GPT calls the generated `remote_dcom_activation_result` tool and receives a
    backend `tool_result`.

Truthful claim after focused workflow passes:
- Remote DCOM activation/invocation is proven for a controlled WScript.Shell
  COM fixture between Azure Windows VM contexts.
- This is not arbitrary enterprise DCOM estate discovery or migration.

If the focused workflow fails due Azure networking, DCOM permissions, or VM
quota, this tranche must stop and write a blocker instead of downgrading to
local COM automation.
