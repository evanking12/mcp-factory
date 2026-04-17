# Sponsor Demo Caveats

This page is the sponsor-facing boundary for what the proof claims and what it
does not claim.

## Legacy Runtime Scope

- JSON-RPC is hosted as a JSON-RPC 2.0 service in the pipeline API. The runtime
  validates the JSON-RPC version, dispatches named methods, and returns standard
  `result` or `error` envelopes.
- SOAP, CORBA IDL, RPC IDL, and JNDI are deterministic hosted adapters. They
  prove discovery, schema generation, GPT tool-call selection, and a real hosted
  tool result. They are not production SOAP middleware, CORBA ORB/IIOP, RPC
  runtime, LDAP, or JNDI infrastructure.
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

The current baseline green contract remains run
[24542583216](https://github.com/evanking12/mcp-factory/actions/runs/24542583216)
until this hardening campaign produces a newer full green run.
