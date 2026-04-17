# Runtime Proof Expansion Closeout

## Canonical Green Proof

- Full Sponsor Demo E2E: https://github.com/evanking12/mcp-factory/actions/runs/24547284139
- Commit: `44d40bd`
- Artifact name: `sponsor-demo-e2e`
- Final report files:
  - `final-summary.md`
  - `final-summary.json`
  - `sponsor-report.html`

## Verified Artifact Results

- Overall final summary: PASS.
- GPT format matrix: `13/13` real execution proofs.
- Provider-required required cases: `0`.
- Runtime modes:
  - `real_runtime`: `jsonrpc`, `soap_wsdl`, `sql`
  - `validated_runtime`: `openapi`
  - `lookup_runtime`: `jndi`
  - `xmlrpc_runtime`: `rpc_idl_contract`
  - `adapter_backed`: `corba_idl`
  - `local_runtime`: `python`, `javascript`, `ruby`, `php`, `powershell`, `cmd`
- Windows GPT proof: `5/5` tool-result-observed proofs.
- Repo ingestion proof: PASS, selected tool `repo_echo_sentinel`.
- Windows required bridge targets: `6/6`.
- Optional Windows diagnostic targets: `1/1`.
- VM deallocation: attempted and completed.

## Focused Workflow Gates

- Contract CI on implementation commit: https://github.com/evanking12/mcp-factory/actions/runs/24547107875
- Deploy Pipeline for SQL fix: https://github.com/evanking12/mcp-factory/actions/runs/24547107871
- Repo ingestion focused proof: https://github.com/evanking12/mcp-factory/actions/runs/24546660542
- Windows GPT focused proof: https://github.com/evanking12/mcp-factory/actions/runs/24546660554
- SOAP one-case GPT proof: https://github.com/evanking12/mcp-factory/actions/runs/24546660545
- SQL one-case GPT proof after coercion fix: https://github.com/evanking12/mcp-factory/actions/runs/24547182990

## Bugs Found And Fixed

- SQL runtime initially failed full E2E because GPT used the sentinel as a
  string `customer_id`; the provider cast it directly to `int` and returned
  `Internal Server Error`.
- Fix: SQL provider now uses safe numeric coercion with deterministic fallback
  IDs while preserving the sentinel in the proof output.

## Remaining Caveats

- CORBA is adapter-backed, not a production CORBA ORB/IIOP runtime.
- COM/TLB discovery is proven; remote DCOM activation is not claimed.
- Windows GPT proofs are `tool_result_observed`; they prove generated tools can
  return recorded discovery proof, not arbitrary semantic execution of Windows
  system binaries.
- Ghidra/deep stripped-binary semantic recovery remains out of capstone scope.

