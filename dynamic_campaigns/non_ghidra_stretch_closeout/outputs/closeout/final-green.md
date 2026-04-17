# Non-Ghidra Stretch Closeout

## Canonical Run

- Full Sponsor Demo E2E: `24578415657`
- URL: https://github.com/evanking12/mcp-factory/actions/runs/24578415657
- Artifact: `sponsor-demo-e2e`
- Focused Remote DCOM source proof: `24577926238`

## What Passed

- Non-VM sponsor formats: pass
- GPT format matrix: `13/13` real execution/tool-call proofs
- Windows discovery targets: pass
- Windows GPT proof matrix: `5/5`
- Repo ingestion proof: pass
- Local COM automation: pass
- Remote DCOM runtime: pass, WMI over DCOM, same-subnet Azure client VM
- LDAP/JNDI runtime: pass
- CORBA ORB/IIOP runtime: pass
- MSRPC runtime: pass
- Bridge VM deallocation: pass

## Truthful Final Claim

We prove controlled runtime-backed support for JSON-RPC, SOAP, SQL, REST, LDAP/JNDI, CORBA ORB/IIOP, MSRPC, and remote DCOM, plus Windows binary/metadata discovery and GPT-callable MCP generation.

## Boundaries

- This campaign did not touch Ghidra.
- It does not claim perfect arbitrary closed-source binary semantic recovery.
- It does not claim arbitrary enterprise DCOM/CORBA/RPC/LDAP estate migration.
- Remote DCOM is a controlled same-subnet fixture proof through WMI over DCOM.
