# Active Prompt

Implement the non-Ghidra stretch closeout campaign sequentially.

Baseline canonical green Sponsor Demo E2E run is
`24568108685`. Preserve it as fallback until a newer full run passes.

Current frontier:

- Focused run `24577926238` passed Remote DCOM through a controlled
  same-subnet Azure client VM using WMI over DCOM.
- The focused artifact proves `remote_dcom_runtime`, distinct client/server
  context, sentinel match, GPT `tool_call`, backend `tool_result`, and cleanup.
- Next gate: run full Sponsor Demo E2E with `remote_dcom_run_id=24577926238`
  and promote docs/UI canonical links only after that full run is green.

Campaign goals:

1. Verify GitHub OIDC can read the bridge VM NIC/subnet and create/delete a
   temporary same-subnet Windows client VM in `mcp-factory-rg`.
2. Run `sponsor-remote-dcom-runtime.yml` through
   `windows-remote-dcom-runtime-proof --client-mode azure-vm`.
3. Require remote activation transcript, method/result output, generated schema,
   GPT `tool_call`, backend `tool_result`, and
   `ci_artifacts/demo/windows/dcom/dcom.summary.json`.
4. Promote `remote_dcom_runtime` from blocked to passed only after focused
   proof passes.
5. Run full Sponsor Demo E2E and verify final artifact includes GPT matrix,
   repo proof, Windows proof, LDAP, CORBA ORB/IIOP, MSRPC, and DCOM artifacts.
6. Polish the UI hard legacy proof panel for the video demo.
7. Write closeout with the canonical run, artifact paths, and truthful claim.

Hard constraints:

- No Ghidra work.
- No undocumented binary recovery expansion.
- No public-client DCOM passing proof.
- No local-only COM downgrade.
- No claim of arbitrary enterprise DCOM estate migration.
- Delete temporary Azure resources after use and record cleanup.
- Stop with a blocker if OIDC permissions or Azure networking prevent truthful
  same-subnet remote DCOM.

Allowed final claim after a full green artifact proves it:

> We prove controlled runtime-backed support for JSON-RPC, SOAP, SQL, REST,
> LDAP/JNDI, CORBA ORB/IIOP, MSRPC, and remote DCOM, plus Windows
> binary/metadata discovery and GPT-callable MCP generation.
