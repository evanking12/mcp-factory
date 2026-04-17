# Tranche 004: REST Validation

## Objective

Tighten REST/OpenAPI proof so generated REST tools call declared paths and
methods.

## Required Work

- Validate REST provider requests against the declared OpenAPI fixture routes.
- Reject mismatched method/path combinations.
- Preserve sentinel echo for valid declared routes.

## Passing Criteria

- Provider tests prove valid route success and invalid route rejection.
- GPT matrix `openapi` case observes GPT `tool_call`, backend `tool_result`, and
  sentinel.
- Final report classifies REST as `validated_runtime`.

## Writeback

Status: local gate passed.

- REST provider now validates method/path against declared OpenAPI fixture
  routes before returning a tool result.
- Tests prove valid route success and invalid route rejection with
  `runtime_mode=validated_runtime`.
- GPT format summaries now carry runtime mode fields for the REST/OpenAPI case.
