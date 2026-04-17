# Tranche 005 Summary

Status: blocked.

Scope:
- Added `windows-remote-dcom-runtime-proof`, which configures a controlled
  WScript.Shell DCOM proof user on the bridge VM, invokes that COM object from
  a distinct Windows client context, records the remote activation transcript,
  and cleans proof-only server artifacts.
- Added focused workflow `Sponsor Remote DCOM Runtime Proof`, which runs from a
  distinct GitHub-hosted Windows client context against the bridge VM public
  endpoint, uploads artifacts, and relies on the proof command to clean the
  proof-only server user/firewall/registry artifacts.
- The proof fails closed. It does not claim remote DCOM if activation does not
  occur from a distinct client context or if the remote sentinel read fails.

Local validation before push:
- `python -m py_compile scripts/ci_verify.py`
- `python scripts/ci_verify.py windows-remote-dcom-runtime-proof --help`
- `python -m pytest -q` passed: `36 passed, 5 skipped`.

First focused workflow attempt:
- Run `24572666172` failed before DCOM activation. The OIDC identity could not
  read the bridge VM NIC, so the workflow could not provision a temporary
  same-subnet client VM. The approach was changed to use a GitHub-hosted Windows
  client as the distinct remote context.

Subsequent focused attempts:
- Run `24572807634` reached the proof command but failed on local Windows runner
  mechanics: Python could not find `az`, and Windows PowerShell inherited a bad
  module path for `ConvertTo-SecureString`.
- Run `24572987800` fixed those runner issues enough to reach client execution,
  but the credentialed client process launch was malformed.
- Run `24573214799` reached real remote COM activation from a distinct
  GitHub-hosted Windows client. The activation failed with `0x800706ba`
  (`RPC server unavailable`) for remote CLSID
  `{72C24DD5-D70A-438B-8A42-98424B88AFB8}` against `20.124.33.45`.

Focused workflow gate:
- Failed and stopped by campaign law. The tranche is not complete until the
  focused workflow proves:
  - `ci_artifacts/demo/windows/dcom/dcom.summary.json` has `passed=true`.
  - `runtime_mode=remote_dcom_runtime`.
  - `remote_dcom_activation_claimed=true`.
  - The transcript shows distinct client and remote server computer names.
  - The remote COM object reads the deterministic sentinel from the server.
  - GPT calls the generated `remote_dcom_activation_result` tool and receives a
    backend `tool_result`.

Truthful claim after focused workflow passes:
- Remote DCOM activation/invocation is proven for a controlled WScript.Shell
  COM fixture between distinct Windows contexts.
- This is not arbitrary enterprise DCOM estate discovery or migration.

Blocker and next bounded move:
- Current Azure permissions do not allow reading the bridge VM NIC, so the
  workflow cannot create a same-subnet Windows client VM.
- Public DCOM/RPC activation from GitHub-hosted Windows to the bridge VM reaches
  COM activation but fails at RPC transport with `0x800706ba`.
- Grant the GitHub OIDC identity enough network read/create permission to create
  a temporary same-subnet Windows client VM, or provide a pre-existing Windows
  client VM in the bridge VM VNet. Then rerun the same proof command using
  `--client-mode azure-vm`.
- Do not downgrade this tranche to local COM automation.
