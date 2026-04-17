# Legacy Infrastructure Showcase Closeout

Status: closed with green canonical proof.

## Canonical Proof

- Full Sponsor Demo E2E: https://github.com/evanking12/mcp-factory/actions/runs/24568108685
- Artifact name: `sponsor-demo-e2e`
- Commit under test: `997bf417d51c7bf0005106ab3d3b7db68e93d06a`

## Evidence Contract

- `final-summary.json` reports `passed=true`.
- GPT format matrix: `13/13` required cases passed.
- Required provider-required cases: `0`.
- Runtime modes: `real_runtime`, `validated_runtime`, `local_runtime`,
  `ldap_jndi_runtime`, `xmlrpc_runtime`, and `corba_idl_runtime`.
- Adapter-backed required cases: none.
- Windows GPT proof matrix: `5/5` tool-result-observed proofs passed.
- Repo ingestion GPT proof passed.
- Windows COM runtime proof passed with `runtime_mode=com_runtime` and
  `dcom_surface=local_com_automation`.

## Focused Workflow Proof

- CORBA IDL one-case GPT proof: https://github.com/evanking12/mcp-factory/actions/runs/24567618169
- JNDI/LDAP one-case GPT proof: https://github.com/evanking12/mcp-factory/actions/runs/24567618200
- RPC XML-RPC one-case GPT proof: https://github.com/evanking12/mcp-factory/actions/runs/24567911113
- Windows COM runtime proof: https://github.com/evanking12/mcp-factory/actions/runs/24568018914

## Claim Boundary

The video demo can claim runtime-backed JSON-RPC, SOAP, SQL, route-validated
REST, LDAP/JNDI-shaped lookup runtime, XML-RPC RPC proof, CORBA IDL
runtime-shaped dispatch, COM/TLB discovery, local COM automation, Windows GPT
tool-result-observed proof, and repo ingestion proof.

The demo should still not claim production CORBA ORB/IIOP, DCE/MSRPC, enterprise
LDAP/JNDI infrastructure, remote DCOM activation, or arbitrary closed-source
binary semantic recovery.

## Remaining Risk

The only notable CI warning is GitHub's Node.js 20 action deprecation notice for
third-party Actions. It does not affect the current proof result, but the
workflow should be revisited before GitHub removes Node.js 20 support.
