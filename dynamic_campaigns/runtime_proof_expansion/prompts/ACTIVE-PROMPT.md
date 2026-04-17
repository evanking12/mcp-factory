# Active Prompt

Implement the dynamic campaign `dynamic_campaigns/runtime_proof_expansion/`
exactly as planned.

Operate sequentially by tranche. Do not advance to the next tranche until the
current tranche has tests, artifacts, and campaign writeback proving it passed.
The current baseline is commit `73c8b80`; first verify or rerun full Sponsor
Demo E2E and record the result.

Campaign goals:

1. Establish the newest green Sponsor Demo E2E run as canonical.
2. Promote SOAP to stricter SOAP envelope/runtime proof.
3. Promote SQL to real SQLite-backed deterministic execution proof.
4. Tighten OpenAPI/REST route validation.
5. Add JNDI lookup runtime proof and optional XML-RPC/gRPC-style RPC runtime
   proof if low-risk.
6. Keep CORBA adapter-backed unless a small emulator can be added safely; do
   not claim production CORBA ORB.
7. Add UI sponsor demo mode with visible `tool_call` and `tool_result`
   transcript.
8. Update final summaries, sponsor report, proof index, README, and caveats.
9. Run focused workflows, then full Sponsor Demo E2E.
10. Write campaign closeout with canonical green run URL, artifact paths,
    runtime-backed provider list, adapter-backed provider list, remaining
    caveats, and known risks.

Hard constraints:

- Do not work on Ghidra stripped-binary recovery.
- Do not claim arbitrary closed-source DLL/EXE semantic recovery.
- Do not claim remote DCOM activation.
- Do not claim production CORBA/RPC/JNDI infrastructure unless actually
  implemented and verified.
- Every required green proof must include GPT `tool_call` and backend
  `tool_result`.
- CI artifacts, not chat memory, determine progress.

Passing criteria:

- Full Sponsor Demo E2E green.
- GPT matrix remains `13/13`.
- Repo ingestion proof passes.
- Windows GPT proof passes `5/5`.
- SOAP and SQL are reported as runtime-backed.
- Final report clearly separates runtime-backed, adapter-backed, and
  observed-result proofs.
- UI demo path reflects the same backend behavior as CI.
- Worktree is clean after commit and push.

