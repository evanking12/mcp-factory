# Tranche 004: Proof Semantics

Status: local gate passed

## Blocker

The report must not imply that provider-backed protocols such as OpenAPI, JSON-RPC, SOAP, CORBA, RPC IDL, JNDI, or SQL were locally live-executed. The acceptable proof is that the system considers the format, discovers/generates a tool schema, the LLM selects the generated tool, and the tool result correctly reports that a provider is required.

## Fix Intent

Make the distinction between `live_execution` and `provider_required` visible in the manifest, GPT matrix summary, final report, and README Sponsor Demo section.

## Evidence To Fill

- Test results:
  - `python -m py_compile scripts\ci_verify.py scripts\gui_bridge.py` passed.
  - `python -m pytest tests\test_ci_verify_sponsor_summary.py tests\test_ci_verify_bridge_cache.py -q` passed: 13 tests.
  - `tests/fixtures/sponsor/sponsor-binary-manifest.json` parses as JSON.
- README update: Sponsor Demo E2E section now states live-execution cases, provider-required cases, and the `cmd_exe` optional diagnostic role.
- Final report sections:
  - `proof_semantics` in `final-summary.json`.
  - `## Proof Semantics` in `final-summary.md`.
- Status: local gate passed; final Actions artifact verification will occur on the next Sponsor Demo E2E rerun.
