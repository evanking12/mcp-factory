# Legacy Infrastructure Showcase

## Goal

Produce a video-friendly proof path that starts with SOAP/WSDL and then shows a
GitHub Actions-backed legacy protocol matrix. The proof matrix should include
runtime-backed JSON-RPC, SOAP, SQL, route-validated REST, LDAP/JNDI-shaped JNDI,
XML-RPC RPC, CORBA IDL runtime-shaped dispatch, Windows COM/TLB discovery, local
COM automation, Windows GPT proof, and repo ingestion.

## Tranches

1. `001-baseline`: verify current canonical green run and record the stable
   fallback.
2. `002-xml-rpc`: make RPC IDL use real XML-RPC request/response/fault
   envelopes.
3. `003-ldap-jndi`: promote JNDI to deterministic LDAP/JNDI bind, search, and
   lookup semantics.
4. `004-corba-idl-runtime`: replace adapter-backed CORBA with IDL object
   registry, repository ID, object reference, and operation allowlist proof.
5. `005-com-surface`: add Windows VM local COM automation proof while keeping
   remote DCOM out of scope.
6. `006-ui-proof-matrix`: add a guided SOAP showcase and proof matrix to the UI.
7. `007-closeout`: run focused workflows, then full Sponsor Demo E2E, then write
   closeout with the new canonical run.

## Gates

- Provider tests prove XML-RPC, LDAP/JNDI, and CORBA runtime-shaped behavior.
- Manifest validation rejects stale CORBA `adapter_backed` as the required path.
- Final summary reports new runtime modes and COM runtime proof.
- UI shows the canonical proof bundle and capability matrix.
- Full Sponsor Demo E2E is green before `CLOSEOUT.md` is written.

