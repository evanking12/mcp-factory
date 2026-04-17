# Tranche 004 Summary

Status: complete.

Scope:
- Added `api/msrpc_runtime.py`, a controlled DCE/RPC-compatible runtime proof
  using Impacket's DCE/RPC stack over `ncacn_ip_tcp`.
- Added a deterministic Contoso RPC IDL surface with `RpcCreateTicket`,
  `RpcGetTicketStatus`, and `RpcCloseTicket`.
- Upgraded the RPC provider to `msrpc_runtime` when
  `ENABLE_MSRPC_RUNTIME=true`; local fallback remains XML-RPC only when the
  stretch runtime is disabled.
- Added `msrpc-runtime-proof` to write `legacy/msrpc/*` artifacts and update
  `legacy-runtime-matrix/summary.json`.
- Added focused workflow `Sponsor MSRPC Runtime Proof`.
- Added full Sponsor Demo E2E MSRPC runtime proof step before the GPT
  `rpc_idl_contract` matrix case.

Local validation before push:
- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py api/ldap_runtime.py api/corba_runtime.py api/msrpc_runtime.py ui/main.py`
- `python -m pytest -q` passed: `36 passed, 5 skipped`.
- `python scripts/ci_verify.py run-sponsor-contract --out <temp>` passed all
  13 sponsor non-VM cases.
- `python scripts/ci_verify.py msrpc-runtime-proof --help` passed.

Focused workflow gate:
- Contract CI passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24572015457
- Deploy Pipeline passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24572015464
- Deploy UI passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24572015516
- Focused MSRPC runtime proof passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24572152040
- Focused RPC IDL GPT proof passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24572186312

Downloaded artifact checks:
- Focused runtime run `24572152040`:
  - `legacy-runtime-matrix/summary.json` has
    `msrpc_runtime.passed=true`.
  - `legacy-runtime-matrix/summary.json` has
    `msrpc_runtime.runtime_mode=msrpc_runtime`.
  - `legacy/msrpc/summary.json` records
    `wire_protocol=DCE/RPC v5 over ncacn_ip_tcp`.
  - Runtime checks confirm provider mode, IDL interface, `ncacn_ip_tcp`
    binding, DCE/RPC protocol, server registration, sentinel result, and
    provider result mode.
- Focused GPT run `24572186312`:
  - `gpt-format-matrix/rpc_idl_contract/summary.json` has `passed=true`.
  - `tool_call_seen=true`.
  - `tool_result_seen=true`.
  - `sentinel_seen=true`.
  - `downloaded_schema_exists=true`.
  - `runtime_mode=msrpc_runtime`.

Truthful claim after focused workflow passes:
- RPC IDL has a controlled DCE/RPC-compatible runtime proof for deterministic
  Contoso RPC IDL, including IDL text, endpoint registration, server log,
  client invocation result, GPT `tool_call`, and backend `tool_result`.
- This is not arbitrary enterprise MSRPC estate support.

Next tranche: `005-remote-dcom-runtime`.
