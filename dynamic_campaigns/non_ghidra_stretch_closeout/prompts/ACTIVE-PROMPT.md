# Active Prompt

Implement the non-Ghidra stretch closeout campaign sequentially.

Baseline canonical green Sponsor Demo E2E run is
`24568108685`. Preserve it as fallback until a newer full run passes.

Current frontier:

- Focused runs `24575880821` and `24576385559` proved Azure same-subnet client
  VM creation and cleanup are working.
- Run `24576385559` preserved Run Command output and exposed Windows-side
  setup problems: server registry setup and denied `Start-Process -Credential`.
- Commit the scheduled-task credential execution fix, rerun focused Remote
  DCOM, then promote only if the parsed artifact proves `remote_dcom_runtime`.

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
