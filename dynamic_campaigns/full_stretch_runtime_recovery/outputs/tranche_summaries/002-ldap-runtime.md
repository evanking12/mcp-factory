# Tranche 002 Summary

Status: local implementation complete; focused workflow evidence pending after
deploy.

Scope:
- Added a controlled LDAPv3-compatible TCP runtime in `api/ldap_runtime.py`.
- Routed `/api/legacy/jndi/bind`, `/api/legacy/jndi/search`, and
  `/api/legacy/jndi/lookup` through LDAP wire roundtrips.
- Changed JNDI runtime mode from `ldap_jndi_runtime` to `ldap_runtime`.
- Added `ldap-runtime-proof` to write `legacy/jndi_ldap/*` artifacts and update
  `legacy-runtime-matrix/summary.json`.
- Added focused workflow `Sponsor LDAP Runtime Proof`.
- Added full Sponsor Demo E2E LDAP runtime proof step before the GPT JNDI case.

Local validation:
- `python -m py_compile scripts/ci_verify.py api/main.py api/executor.py api/legacy_provider.py api/ldap_runtime.py ui/main.py`
- `python -m pytest -q` passed: `36 passed, 5 skipped`.
- `python scripts/ci_verify.py run-sponsor-contract --out <temp>` passed all
  13 sponsor non-VM cases.
- Local API proof passed:
  `python scripts/ci_verify.py ldap-runtime-proof --base-url http://127.0.0.1:8765 ...`

Focused workflow gate:
- Pending until this branch is committed, pushed, deployed, and
  `sponsor-ldap-runtime.yml` passes against the pipeline ACA.
- The campaign must not advance to `003-corba-orb-runtime` until that focused
  workflow evidence is recorded here.

Truthful claim after focused workflow passes:
- JNDI/LDAP has a controlled LDAPv3-compatible runtime proof for deterministic
  Contoso bind/search/lookup.
- This is not an enterprise directory migration claim.
