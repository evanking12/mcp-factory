# Tranche 001 - Provider Router And Executor

## Goal

Host deterministic REST/OpenAPI, JSON-RPC, SOAP, SQL, CORBA, RPC, and JNDI
providers inside the pipeline API, then route generated tools to those providers
when no explicit provider URL is present.

## Evidence To Write

- Provider route tests pass.
- Executor routing tests pass.
- `python -m py_compile api/main.py api/executor.py api/legacy_provider.py`

## Local Evidence

- Added `api/legacy_provider.py` and mounted it from `api/main.py`.
- Added default executor routing through `LEGACY_PROVIDER_BASE_URL`.
- Added provider/executor coverage in `tests/test_legacy_provider_executor.py`.
- Passing:
  - `python -m py_compile scripts/ci_verify.py scripts/gui_bridge.py api/main.py api/executor.py api/legacy_provider.py ui/main.py`
  - `python -m pytest tests/test_legacy_provider_executor.py tests/test_ci_verify_sponsor_summary.py -q`

## Status

Complete locally; CI/deploy verification pending.
