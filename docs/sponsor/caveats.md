# Sponsor Demo Caveats

This page is the sponsor-facing boundary for what the proof claims and what it
does not claim.

## Legacy Runtime Scope

- JSON-RPC is hosted as a JSON-RPC 2.0 service in the pipeline API. The runtime
  validates the JSON-RPC version, dispatches named methods, and returns standard
  `result` or `error` envelopes.
- SOAP is now runtime-backed in the pipeline API as a SOAP envelope validator
  and dispatcher for WSDL-named Contoso operations. It returns SOAP XML
  responses and SOAP faults, but it is not production enterprise SOAP
  middleware.
- SQL is now SQLite-backed with deterministic Contoso data. It proves generated
  SQL tools can execute against a real database runtime in CI without requiring
  SQL Server infrastructure.
- REST/OpenAPI is route-validated against declared paths and methods before the
  provider returns a tool result.
- JNDI is runtime-backed through a controlled LDAPv3-compatible bind, search,
  and lookup runtime. It proves directory-style lookup behavior over an LDAP
  wire roundtrip, not production enterprise LDAP operations, identity
  infrastructure, or directory migration.
- RPC IDL is runtime-backed through a controlled DCE/RPC-compatible
  `ncacn_ip_tcp` proof service for deterministic Contoso RPC IDL. It is not
  arbitrary enterprise MSRPC estate support.
- CORBA IDL is runtime-backed through a controlled OmniORB/IIOP proof service
  for deterministic Contoso IDL. It proves ORB object registration, IOR object
  references, and client invocation for the fixture, but it is not generalized
  CORBA estate migration.
- COM/TLB discovery and local COM automation are proven through the Windows
  bridge. Remote DCOM activation and remote DCOM invocation are not claimed by
  the sponsor demo.

## Binary Recovery Scope

The system performs best-effort profiling of existing targets. It can inspect
exports, imports, CLI/help behavior, GUI affordances, COM/TLB metadata, registry
inventory, installed directories, and known contract/source formats. It does not
guarantee perfect semantic recovery for arbitrary closed-source DLL or EXE
files.

## Windows Proof Scope

Windows target categories have required bridge discovery proof. The hardening
campaign adds targeted GPT tool-call proof against generated tools derived from
the Windows discovery summaries. Those Windows GPT proofs are classified as
`tool_result_observed`; they show that generated tools can be called and return
the recorded proof artifact, not that arbitrary Windows system binaries were
semantically executed by GPT.

## Current Required Green Contract

The current canonical green contract is run
[24568108685](https://github.com/evanking12/mcp-factory/actions/runs/24568108685).
Run [24547629781](https://github.com/evanking12/mcp-factory/actions/runs/24547629781)
is the previous runtime-expansion green run, and run
[24542583216](https://github.com/evanking12/mcp-factory/actions/runs/24542583216)
remains a historical fallback before the runtime expansion campaign.
