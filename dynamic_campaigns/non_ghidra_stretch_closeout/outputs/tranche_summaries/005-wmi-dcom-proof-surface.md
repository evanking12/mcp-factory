# Tranche 002 Checkpoint: WMI/DCOM Proof Surface

## Tranche

`002-same-subnet-remote-dcom-proof`

## Evidence

- Focused workflow run: `24577375644`
- Result: server setup passed; client scheduled task ran; remote activation of `WScript.Shell` failed with `80040154`.
- Cleanup verification:
  - temporary client VM absent
  - temporary client NIC absent
  - temporary client OS disk absent

## Finding

`WScript.Shell` is not a valid controlled remote activation surface in this environment. The server reported the CLSID, but remote activation from the same-subnet client failed before method invocation:

`Retrieving the COM class factory for remote component with CLSID {72C24DD5-D70A-438B-8A42-98424B88AFB8} from machine 10.1.0.4 failed ... 80040154`

This is a DCOM surface selection problem, not Azure provisioning or cleanup.

## Fix

The proof now uses classic WMI over DCOM:

- server enables WMI firewall group and DCOM/RPC services
- client invokes `Win32_ComputerSystem` and `StdRegProv`
- proof reads the deterministic sentinel from `HKLM\SOFTWARE\MCPFactory\DCOM`
- runtime mode remains `remote_dcom_runtime`

This is still a controlled remote DCOM proof and still does not claim arbitrary enterprise DCOM estate migration.

## Local Gates

- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`: pass
- `python -m pytest -q`: `40 passed, 5 skipped`

## Next Prompt

Commit and push the WMI/DCOM proof surface change, rerun `Sponsor Remote DCOM Runtime Proof`, and inspect whether the same-subnet client can read the server sentinel through WMI/DCOM.
