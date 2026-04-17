# Tranche 002: SOAP Runtime

## Objective

Promote SOAP from adapter-style proof to SOAP envelope/runtime proof.

## Required Work

- Validate SOAP XML and require a SOAP `Envelope` and `Body`.
- Dispatch WSDL-named operations.
- Return SOAP XML success responses containing the sentinel.
- Return SOAP fault XML for invalid envelopes or unknown operations.

## Passing Criteria

- Provider tests cover valid envelope, invalid envelope, unknown operation, and
  sentinel response.
- GPT matrix `soap_wsdl` case still observes GPT `tool_call`, backend
  `tool_result`, and sentinel.
- Final report classifies SOAP as `real_runtime`.

## Writeback

Status: local gate passed.

- `api/legacy_provider.py` now validates SOAP XML, requires `Envelope` and
  `Body`, dispatches WSDL-named operations, returns SOAP success XML, and
  returns SOAP faults for invalid/unknown requests.
- `tests/test_legacy_provider_executor.py` covers valid SOAP runtime response,
  invalid envelope, unknown operation, runtime mode, and sentinel propagation.
- Final summary semantics now report SOAP as `real_runtime`.
