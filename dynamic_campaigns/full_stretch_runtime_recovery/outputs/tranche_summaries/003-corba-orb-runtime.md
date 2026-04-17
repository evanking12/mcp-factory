# Tranche 003 Summary

Status: complete.

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
- Contract CI initially failed on run `24571122121` because the ORB thread
  started during Linux unit tests and aborted on process teardown after tests
  passed.
- Fix: ORB startup is now gated by `ENABLE_CORBA_ORB_RUNTIME=true`; Contract CI
  validates fallback wiring and the deployed ACA enables the real ORB runtime.
- Contract CI passed after the fix:
  https://github.com/evanking12/mcp-factory/actions/runs/24571268064
- Deploy Pipeline passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24571268046
- Focused CORBA ORB proof passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24571375852
- Focused CORBA GPT proof passed:
  https://github.com/evanking12/mcp-factory/actions/runs/24571403523

Downloaded artifact checks from run `24571403523`:
- `legacy-runtime-matrix/summary.json` has
  `corba_orb_runtime.passed=true`.
- `legacy-runtime-matrix/summary.json` has
  `corba_orb_runtime.runtime_mode=corba_orb_runtime`.
- `legacy-runtime-matrix/summary.json` has
  `corba_orb_runtime.wire_protocol=IIOP`.
- `legacy-runtime-matrix/summary.json` checks confirm the Contoso IDL, IOR
  object reference, server registration log, client invocation, and sentinel.
- `gpt-format-matrix/corba_idl/summary.json` has `passed=true`,
  `tool_call_seen=true`, `tool_result_seen=true`, `sentinel_seen=true`, and
  `downloaded_schema_exists=true`.

Truthful claim after focused workflow passes:
- CORBA IDL has a controlled OmniORB/IIOP runtime proof for deterministic
  Contoso IDL, including IDL, IOR object reference, server log, client
  invocation result, GPT `tool_call`, and backend `tool_result`.
- This is not generalized CORBA estate migration.

Next tranche: `004-msrpc-runtime`.
