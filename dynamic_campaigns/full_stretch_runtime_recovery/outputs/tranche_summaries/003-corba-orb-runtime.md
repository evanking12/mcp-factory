# Tranche 003 Summary

Status: local implementation complete; focused workflow evidence pending after
deploy.

Scope:
- Added Linux-only `jeteve-omniorb` dependency for the pipeline API image.
- Added `api/corba_runtime.py`, which generates Contoso IDL Python stubs with
  `omniidl`, starts an OmniORB servant, registers object references, and invokes
  the generated client stub.
- Upgraded the CORBA provider to `corba_orb_runtime` when OmniORB is available.
- Added `corba-orb-runtime-proof` to write `legacy/corba_orb/*` artifacts and
  update `legacy-runtime-matrix/summary.json`.
- Added focused workflow `Sponsor CORBA ORB Runtime Proof`.
- Added full Sponsor Demo E2E CORBA runtime proof step before the GPT CORBA
  matrix case.

Local validation:
- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py api/ldap_runtime.py api/corba_runtime.py ui/main.py`
- `python -m pytest -q` passed: `36 passed, 5 skipped`.
- `python scripts/ci_verify.py run-sponsor-contract --out <temp>` passed all
  13 sponsor non-VM cases.
- `python scripts/ci_verify.py corba-orb-runtime-proof --help` passed.

Focused workflow gate:
- Pending until this branch is committed, pushed, deployed, and
  `sponsor-corba-orb.yml` passes against the pipeline ACA.
- The campaign must not advance to `004-msrpc-runtime` until the focused CORBA
  ORB workflow and focused CORBA GPT matrix evidence are recorded here.

Truthful claim after focused workflow passes:
- CORBA IDL has a controlled OmniORB/IIOP runtime proof for deterministic
  Contoso IDL, including IDL, IOR object reference, server log, client
  invocation result, GPT `tool_call`, and backend `tool_result`.
- This is not generalized CORBA estate migration.
