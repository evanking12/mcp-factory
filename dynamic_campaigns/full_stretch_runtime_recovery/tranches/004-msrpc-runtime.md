# 004 MSRPC / Windows RPC Runtime

Class: `bounded_fix`

Status: pending.

Goal: replace XML-RPC stretch proof with controlled Windows RPC or DCE/MSRPC
proof.

Required artifacts:
- `ci_artifacts/demo/legacy/msrpc/contoso_rpc.idl`
- generated stubs metadata
- `ci_artifacts/demo/legacy/msrpc/endpoint-registration.json`
- server logs
- `ci_artifacts/demo/legacy/msrpc/client-invocation.json`
- `ci_artifacts/demo/gpt-format-matrix/rpc_idl_contract/transcript.json`

Gate:
- GPT calls a generated RPC tool.
- Backend returns a tool result from controlled RPC runtime.
- Final summary reports `runtime_mode=msrpc_runtime`.
- If native Windows RPC cannot be made stable, write a blocker and do not
  downgrade to XML-RPC.

