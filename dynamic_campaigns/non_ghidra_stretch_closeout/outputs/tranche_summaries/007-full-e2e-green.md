# Tranche 005 Complete: Full Sponsor Demo E2E Green

## Tranche

`005-final-sponsor-e2e`

## Full Run

- Run: `24578415657`
- URL: `https://github.com/evanking12/mcp-factory/actions/runs/24578415657`
- Artifact: `sponsor-demo-e2e`
- Imported Remote DCOM source run: `24577926238`
- Report-only reproducibility run: `24579153369`

## Final Summary Gate

`final-summary.json` reports:

- `passed=true`
- `remote_dcom_runtime_proof_passed=true`
- `required_remote_dcom=true`
- `gpt_format_matrix_passed=true`
- `windows_gpt_tool_matrix_passed=true`
- `repo_ingestion_proof_passed=true`
- `windows_com_runtime_proof_passed=true`
- `vm_deallocation_completed=true`
- report-only re-render from uploaded JSON: pass

Runtime proof highlights:

- GPT matrix: `13/13` real execution/tool-call proofs
- Windows GPT: `5/5`
- Repo ingestion: pass
- LDAP/JNDI: `ldap_runtime`
- CORBA: `corba_orb_runtime`
- RPC: `msrpc_runtime`
- Remote DCOM: `remote_dcom_runtime` through WMI over DCOM

## Claim Boundary

Allowed non-Ghidra stretch claim:

> We prove controlled runtime-backed support for JSON-RPC, SOAP, SQL, REST, LDAP/JNDI, CORBA ORB/IIOP, MSRPC, and remote DCOM, plus Windows binary/metadata discovery and GPT-callable MCP generation.

Still out of scope:

- Ghidra and undocumented binary recovery
- perfect arbitrary closed-source binary semantic recovery
- arbitrary enterprise DCOM/CORBA/RPC/LDAP estate migration

## Next Prompt

Non-Ghidra stretch closeout is complete. Keep `24578415657` as the canonical proof bundle and `24579153369` as the report-only reproducibility check.
