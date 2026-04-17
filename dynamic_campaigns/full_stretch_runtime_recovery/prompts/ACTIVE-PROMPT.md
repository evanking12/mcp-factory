# Active Prompt

Implement the full stretch runtime and binary recovery campaign sequentially.

Current baseline is canonical green Sponsor Demo E2E run `24568108685`. Preserve
it as the fallback until a newer full stretch run passes.

Current frontier: `003-corba-orb-runtime`.

Do not advance until the current tranche has tests, artifacts, campaign
writeback, and focused workflow evidence. If a hard runtime cannot be made
truthful, stop at that tranche and write a blocker instead of downgrading the
claim.

Goals:
1. Extend the proof/report contract for stretch runtime modes.
2. Replace LDAP/JNDI-shaped proof with a real LDAP-compatible runtime proof.
3. Replace CORBA IDL runtime-shaped proof with a real ORB/IIOP controlled proof.
4. Replace XML-RPC stretch proof with controlled MSRPC/Windows RPC proof.
5. Replace local-only COM proof with controlled remote DCOM activation and
   invocation proof.
6. Add evidence-ranked Ghidra plus dynamic tracing proof for undocumented
   compiled fixtures.
7. Expand repo and Windows runtime fixture proofs.
8. Add UI video proof mode for SOAP, CORBA ORB, LDAP/JNDI, DCOM, and
   undocumented binary recovery.
9. Run focused workflows, then full Sponsor Demo E2E.
10. Update README, proof index, caveats, UI canonical link, and campaign
    closeout.

Hard constraints:
- Every required stretch proof must include generated schema, GPT `tool_call`,
  backend `tool_result`, transcript, and artifact path.
- Do not claim arbitrary enterprise estate support.
- Do not claim perfect arbitrary closed-source binary semantic recovery.
- Do not silently downgrade MSRPC, CORBA ORB, LDAP, or remote DCOM to prior
  runtime-shaped proofs.
- CI artifacts, not chat memory, determine progress.
- Deallocate or delete temporary Azure resources after use.

Final claim allowed only if the final green artifact proves it:

> The project supports files, installed paths, directories, repos, scripts,
> Windows binaries, contracts, SQL, JSON-RPC, SOAP, REST, LDAP/JNDI, CORBA
> ORB/IIOP, RPC, controlled remote DCOM, and evidence-ranked undocumented binary
> recovery. Every required proof produces a generated schema, GPT tool call,
> backend tool result, transcript, and downloadable artifact.
