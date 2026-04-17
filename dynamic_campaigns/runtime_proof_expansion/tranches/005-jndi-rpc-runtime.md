# Tranche 005: JNDI And RPC Runtime

## Objective

Add lightweight runtime-shaped JNDI lookup and XML-RPC-style RPC proof while
keeping CORBA honestly adapter-backed.

## Required Work

- JNDI provider returns deterministic binding lookup results.
- RPC provider returns XML-RPC-style response structure.
- CORBA remains `adapter_backed` unless a verified emulator is added.

## Passing Criteria

- Provider tests prove JNDI binding lookup and RPC runtime mode.
- GPT matrix `jndi` and `rpc_idl_contract` cases observe GPT `tool_call`,
  backend `tool_result`, and sentinel.
- Final report lists CORBA under adapter-backed cases.

## Writeback

Status: local gate passed.

- JNDI provider now reports deterministic binding lookup results with
  `runtime_mode=lookup_runtime`.
- RPC provider returns XML-RPC-style response structure with
  `runtime_mode=xmlrpc_runtime`.
- CORBA remains explicitly `adapter_backed` in provider health, manifest,
  summary semantics, README, proof index, and caveats.
