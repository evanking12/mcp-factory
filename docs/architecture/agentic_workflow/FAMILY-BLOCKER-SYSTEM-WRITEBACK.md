# Family Blocker And Missing System Writeback

Use this when a repeated issue is larger than one local bug.

## Classification

Choose exactly one:

- `local_bug`
- `family_blocker`
- `missing_system`

## Entry

- id: `[stable id]`
- title: `[short title]`
- class: `[local_bug | family_blocker | missing_system]`
- status: `[active | narrowed | superseded | resolved | deferred]`
- origin_surface: `[where discovered]`
- symptom_family: `[recurring observable pattern]`
- evidence:
  - `[file/run/test/review/artifact]`
- why_this_is_a_family:
  - `[why it recurs beyond one bug]`
- current_trust_impact:
  - `[what decision or proof remains untrustworthy]`
- current_iteration_cost:
  - `[how this wastes time]`
- affected_surfaces:
  - `[module/folder/system/check]`
- next_bounded_move:
  - `[single next action]`
- do_not_do_yet:
  - `[premature action]`

## Additional Fields For `missing_system`

- system_name: `[name]`
- system_goal: `[goal]`
- why_existing_systems_are_insufficient:
  - `[reason]`
- minimum_useful_scope:
  - `[scope]`
- non_goals:
  - `[non-goal]`
- required_inputs:
  - `[input]`
- required_outputs:
  - `[output]`
- contract_or_schema_implications:
  - `[contract]`
- observability_or_artifact_requirements:
  - `[artifact/log/status]`
- acceptance_criteria:
  - `[criterion]`
- proof_of_value:
  - `[what improves if built]`
- unlock_target:
  - `[target]`
- stop_if:
  - `[evidence that this is wrong]`

---

## Entry

- id: `remote-dcom-same-subnet-client-required`
- title: `Remote DCOM proof needs same-subnet Windows client permissions`
- class: `family_blocker`
- status: `active`
- origin_surface: `dynamic_campaigns/full_stretch_runtime_recovery tranche 005`
- symptom_family: `Remote DCOM cannot be truthfully promoted from local COM without a distinct routable Windows client context.`
- evidence:
  - `https://github.com/evanking12/mcp-factory/actions/runs/24572666172`
  - `https://github.com/evanking12/mcp-factory/actions/runs/24573214799`
  - `ci_artifacts/demo/windows/dcom/remote-activation-transcript.json`
- why_this_is_a_family:
  - `The blocker is not a single Python bug. It spans Azure identity permissions, VNet placement, public DCOM/RPC routing, and Windows DCOM authentication.`
- current_trust_impact:
  - `The project cannot truthfully claim remote DCOM activation/invocation until a distinct Windows client can reach the bridge VM over DCOM/RPC.`
- current_iteration_cost:
  - `Each attempt requires a focused workflow and proof cleanup; public DCOM attempts fail only after Azure Run Command and remote client setup.`
- affected_surfaces:
  - `.github/workflows/sponsor-remote-dcom-runtime.yml`
  - `scripts/ci_verify.py windows-remote-dcom-runtime-proof`
  - `dynamic_campaigns/full_stretch_runtime_recovery/tranches/005-remote-dcom-runtime.md`
- next_bounded_move:
  - `Grant the GitHub OIDC identity network read/create permissions for a temporary same-subnet Windows client VM, or provide a pre-existing Windows client VM in the bridge VNet, then rerun with --client-mode azure-vm.`
- do_not_do_yet:
  - `Do not relabel local COM automation as remote DCOM.`
  - `Do not claim arbitrary enterprise DCOM support from the current artifacts.`
