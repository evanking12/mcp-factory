# 002 XML-RPC

Status: implemented.

Gate:
- RPC IDL provider accepts XML-RPC `methodCall`.
- Known RPC IDL methods return XML-RPC `methodResponse`.
- Unknown RPC methods return XML-RPC `fault`.
- Executor `rpc_call` routes through XML-RPC wire payloads.

