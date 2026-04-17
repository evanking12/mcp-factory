# Tranche 003: SQL Runtime

## Objective

Promote SQL from provider adapter to SQLite-backed deterministic runtime proof.

## Required Work

- Seed deterministic Contoso customer/order/ticket data in an in-memory SQLite
  runtime.
- Dispatch known SQL fixture operations.
- Return deterministic query/procedure-style results and sentinel proof.

## Passing Criteria

- Provider tests prove `GetCustomerInfo` and `CreateSupportTicket`.
- GPT matrix `sql` case observes GPT `tool_call`, backend `tool_result`, and
  sentinel.
- Final report classifies SQL as `real_runtime`.

## Writeback

Status: local gate passed.

- `api/legacy_provider.py` now seeds deterministic in-memory SQLite Contoso
  customer/order/ticket data for SQL proof operations.
- Tests cover `GetCustomerInfo`, `CreateSupportTicket`, `database=sqlite`,
  `runtime_mode=real_runtime`, and sentinel proof text.
- Final summary requirement notes now frame SQL as SQLite-backed runtime proof.
