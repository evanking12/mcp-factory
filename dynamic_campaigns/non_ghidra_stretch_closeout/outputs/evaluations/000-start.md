# Workflow Quality Evaluation: Campaign Start

- `gm_control_quality`: `3`
  - Evidence: the campaign isolates the only remaining non-Ghidra hard stretch
    blocker: same-subnet remote DCOM.
  - Strongest risk: Azure role assignment remains insufficient.
  - Next correction: stop with exact failed Azure operation and role scope.
- `context_pressure_result`: `3`
  - Evidence: Ghidra and undocumented binary recovery are explicitly out of
    scope.
  - Strongest risk: older full-stretch surfaces still mention Ghidra.
  - Next correction: use this campaign as the canonical non-Ghidra closeout
    surface.
- `delegation_effectiveness`: `2`
  - Evidence: no subagents were authorized or needed for initialization.
  - Strongest risk: Azure proof review may benefit from a second pass later.
  - Next correction: dispatch only if user explicitly authorizes it.
- `operator_reviewability`: `3`
  - Evidence: each tranche has one gate, exact workflow names, and exact
    artifact paths.
  - Strongest risk: Azure cleanup could be overlooked.
  - Next correction: require cleanup artifacts in the DCOM focused workflow.
