# 005 Operational Resilience

- Class: `bounded_fix`
- Primary question: can the readiness pipeline explain infra state and failure
  class without requiring raw log spelunking?
- Gate:
  - `azure-operational-proof` records VM, ACA, storage, and temporary DCOM
    client state.
  - Failure paths upload `failure-diagnosis.json`.

