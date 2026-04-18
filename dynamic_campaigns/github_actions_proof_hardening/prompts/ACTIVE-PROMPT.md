# Active Prompt

Implement the GitHub Actions proof hardening campaign sequentially.

Current baseline:

- Fallback canonical green Sponsor Demo E2E run: `24568108685`
- Stronger full proof referenced by current campaign state: `24613173130`
- Hardening integrity proof for that full artifact: `24613434034`

Goals:

1. Add deployed UI SOAP smoke verification.
2. Add deployed pipeline provider matrix smoke verification.
3. Add demo-readiness workflow for video recording confidence.
4. Add final-summary JSON Schema validation.
5. Add sponsor artifact completeness validation.
6. Add GPT transcript integrity validation.
7. Add runtime-mode downgrade guard.
8. Add caveat consistency guard.
9. Add Azure operational proof and failure classification artifacts.
10. Run focused workflows, then full Sponsor Demo E2E, then integrity
    validation against the full run.

Hard constraints:

- Do not touch Ghidra or binary recovery.
- Do not weaken current sponsor proof semantics.
- Do not silently downgrade runtime modes.
- Do not claim Remote DCOM, CORBA ORB, MSRPC, or enterprise migration unless
  the artifact proves it.
- CI artifacts, not chat memory, determine progress.
- Keep new workflows light unless explicitly running full Sponsor Demo E2E.
- Every tranche must update campaign writeback before commit/push.

Current frontier:

- Local verifier implementation and workflow definitions are being validated.
- Next external evidence is focused GitHub Actions dispatch for readiness,
  provider smoke, proof integrity, and report-only integrity.
