# Architect Brief: 004 MSRPC Runtime

Decision:
- Use Impacket's DCE/RPC runtime in the Linux pipeline API container for a
  controlled `ncacn_ip_tcp` RPC proof.

Why:
- The tranche requires something stronger than the existing XML-RPC fallback.
  A controlled DCE/RPC-compatible server/client can prove IDL-bound RPC
  invocation, endpoint registration, and a backend tool result without creating
  a broad enterprise MSRPC estate claim.
- Native Windows RPC/MIDL compilation would add Windows SDK setup risk and
  slow the campaign. If the Impacket route cannot pass a focused deployed proof,
  the campaign must stop at this tranche and write a blocker rather than
  relabel XML-RPC.

Trust boundary:
- Allowed claim after workflow proof: controlled DCE/RPC-compatible runtime
  proof for deterministic Contoso RPC IDL over `ncacn_ip_tcp`.
- Disallowed claim: arbitrary MSRPC estate discovery, production Windows RPC
  infrastructure, or generalized RPC modernization.

Next blocker:
- Validate that the deployed ACA imports Impacket, exposes
  `provider_modes.rpc=msrpc_runtime`, starts the controlled endpoint, records
  endpoint/client artifacts, and returns a GPT-observed sentinel before moving
  to remote DCOM.
