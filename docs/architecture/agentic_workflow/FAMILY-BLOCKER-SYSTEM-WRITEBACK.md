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

