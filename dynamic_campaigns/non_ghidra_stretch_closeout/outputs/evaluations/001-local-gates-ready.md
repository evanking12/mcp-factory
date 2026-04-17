# Workflow Quality Evaluation: Local Gates Ready

- `gm_control_quality`: `3`
  - Evidence: the canonical full run now has a Remote DCOM required gate.
  - Strongest risk: Azure permission failures will stop before DCOM.
  - Next correction: record exact failed Azure operation and role scope.
- `context_pressure_result`: `3`
  - Evidence: no Ghidra scope was added.
  - Strongest risk: full-stretch language could leak into final claim.
  - Next correction: final claim remains non-Ghidra only.
- `delegation_effectiveness`: `2`
  - Evidence: no subagents were authorized.
  - Strongest risk: CI logs may need a second reviewer later.
  - Next correction: request authorization only if diagnosis becomes ambiguous.
- `operator_reviewability`: `3`
  - Evidence: local tests cover workflow mode and summary Remote DCOM gating.
  - Strongest risk: focused DCOM artifact still not generated.
  - Next correction: dispatch focused workflow after push.
