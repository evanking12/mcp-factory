# Tranche 005: Final Sponsor E2E

Class: `authoritative_validation`

Primary question: does a new full Sponsor Demo E2E artifact prove the full
non-Ghidra stretch claim?

Actions:

- Run full Sponsor Demo E2E.
- Download and parse `sponsor-demo-e2e`.
- Verify final summary, GPT matrix, Windows proof, repo proof, LDAP, CORBA
  ORB/IIOP, MSRPC, and DCOM artifacts.

Passing criteria:

- `final-summary.json` has `passed=true`.
- GPT matrix is green.
- Repo proof and Windows proof are green.
- `remote_dcom_runtime=passed`.
- No required proof is missing, blocked, provider-required, or local-only.
