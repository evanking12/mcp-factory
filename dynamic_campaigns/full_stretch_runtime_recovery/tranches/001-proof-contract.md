# 001 Proof Contract

Class: `trust_or_setup`

Status: complete.

Goal: extend the final report schema before hard runtime work starts.

Gate:
- Existing sponsor contract still passes.
- Report-only summary can render stretch sections from current artifacts.
- Missing hard stretch artifacts are recorded as `not_yet_run`, not silently
  passed.

Expected artifacts:
- `final-summary.json` includes `stretch_goals_passed`,
  `runtime_mode_matrix`, `legacy_runtime_matrix`, `ghidra_binary_recovery`,
  `remote_dcom`, `corba_orb`, `ldap_runtime`, and `msrpc_runtime`.
- `final-summary.md` includes Stretch Goal Proof Matrix, Hard Legacy Runtime
  Proofs, Undocumented Binary Recovery Proof, and Remaining Truthful Boundaries.

Validation:
- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`
- `python -m pytest -q`
- Report-only render against canonical run `24568108685`:
  - existing sponsor gate: `passed=true`
  - stretch matrix: `5/11`
  - hard stretch proofs not yet run: `ldap_runtime`, `corba_orb_runtime`,
    `msrpc_runtime`, `remote_dcom_runtime`,
    `evidence_ranked_binary_recovery`, `windows_runtime_fixture`
