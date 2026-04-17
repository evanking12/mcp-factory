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
- JNDI uses deterministic binding lookup semantics and RPC uses an XML-RPC-style
  deterministic runtime proof. They are runtime-shaped proofs, not production
  LDAP/JNDI or DCE/MSRPC infrastructure.
- CORBA remains a deterministic hosted adapter. It proves discovery, schema
  generation, GPT tool-call selection, and a real hosted tool result, but it is
  not a production CORBA ORB/IIOP deployment.
- COM/TLB discovery is proven through the Windows bridge. Remote DCOM activation
  and remote DCOM invocation are not deeply proven by the sponsor demo.

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
[24547629781](https://github.com/evanking12/mcp-factory/actions/runs/24547629781).
Run [24547284139](https://github.com/evanking12/mcp-factory/actions/runs/24547284139)
is the previous runtime-expansion green run, and run
[24542583216](https://github.com/evanking12/mcp-factory/actions/runs/24542583216)
remains a historical fallback before the runtime expansion campaign.
